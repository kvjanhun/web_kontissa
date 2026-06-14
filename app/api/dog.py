import re
import time
import os
import json
import threading

import requests
import structlog
from bs4 import BeautifulSoup
from flask import Blueprint, jsonify, request as flask_request

from app import limiter

logger = structlog.get_logger(__name__)

dog_bp = Blueprint('dog', __name__)

BASE_URL = "https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset"
REQUEST_HEADERS = {"User-Agent": "erez.ac dog show browser"}
REQUEST_TIMEOUT = 10

# ---------------------------------------------------------------------------
# TTL cache & Breed Indexing persistence
# ---------------------------------------------------------------------------

_show_list_cache = {"data": None, "ts": 0}
SHOW_LIST_TTL = 1800  # 30 minutes

_show_detail_cache = {}   # {show_id: data}  — indefinite
_breed_result_cache = {}  # {(show_id, group, breed): data} — indefinite

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INDEX_PATH = os.path.join(INDEX_DIR, "dog_show_index.json")

# In-memory index representation
_show_index = {
    "shows": {},       # show_id (str) -> { "title": "...", "breeds": [...] }
    "last_updated": 0
}
_crawler_started = False
_crawler_lock = threading.Lock()

def _load_index():
    global _show_index
    if os.path.exists(INDEX_PATH):
        try:
            with open(INDEX_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "shows" in data:
                    _show_index = data
                    logger.info("dog_index_loaded", count=len(data["shows"]))
        except Exception:
            logger.exception("dog_index_load_failed")

def _save_index():
    try:
        os.makedirs(INDEX_DIR, exist_ok=True)
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(_show_index, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("dog_index_save_failed")

def _fetch_page(url):
    """Fetch a page from Showlink with timeout and logging."""
    logger.info("showlink_request", url=url)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def _background_crawler():
    logger.info("dog_crawler_started")
    while True:
        try:
            # 1. Fetch the show list (refreshing it if stale)
            shows_list = _get_show_list()
            if not shows_list:
                time.sleep(60)
                continue

            # 2. Find which shows are missing from the index
            missing = []
            for s in shows_list:
                sid = str(s["id"])
                if sid not in _show_index["shows"]:
                    missing.append(s)

            if missing:
                logger.info("dog_crawler_missing_shows", count=len(missing))
                # Crawl missing shows
                for s in missing:
                    sid = s["id"]
                    try:
                        url = f"{BASE_URL}?Id={sid}"
                        soup = _fetch_page(url)
                        detail = _parse_show_detail(soup, sid)
                        
                        # Add to index
                        _show_index["shows"][str(sid)] = {
                            "title": detail["title"],
                            "breeds": detail["breeds"]
                        }
                        _show_index["last_updated"] = time.time()
                        _save_index()
                        
                        logger.info("dog_crawler_indexed_show", show_id=sid, breed_count=len(detail["breeds"]))
                    except Exception as e:
                        logger.warning("dog_crawler_show_failed", show_id=sid, error=str(e))
                    
                    # Be very polite: sleep 1.5 seconds between requests
                    time.sleep(1.5)
            else:
                # Nothing missing, check again in 1 hour
                time.sleep(3600)
        except Exception:
            logger.exception("dog_crawler_loop_error")
            time.sleep(60)

@dog_bp.record
def on_blueprint_ready(state):
    app = state.app
    if not app.config.get("TESTING"):
        _load_index()
        global _crawler_started
        with _crawler_lock:
            if not _crawler_started:
                # Avoid starting background thread twice if in Flask reloader main process
                if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not os.environ.get("FLASK_DEBUG"):
                    t = threading.Thread(target=_background_crawler, daemon=True, name="DogShowCrawler")
                    t.start()
                    _crawler_started = True
                    logger.info("dog_crawler_thread_launched")


# ---------------------------------------------------------------------------
# GET /api/dog/shows — show listing
# ---------------------------------------------------------------------------

def _parse_show_list(soup):
    """Parse the sidebar show listing table."""
    shows = []
    current_month = ""

    table = soup.find("table", id="Nayttelylista")
    if not table:
        return shows

    for row in table.find_all("tr", class_="nayttely"):
        # Month header row
        header = row.find("td", class_="valiotsikko", colspan="2")
        if header:
            current_month = header.get_text(strip=True)
            continue

        # Show row — two <td> elements with <a> tags
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        link = cells[0].find("a")
        name_link = cells[1].find("a")
        if not link or not name_link:
            continue

        href = link.get("href", "")
        match = re.search(r"Id=(\d+)", href)
        if not match:
            continue

        shows.append({
            "id": int(match.group(1)),
            "date": link.get_text(strip=True),
            "name": name_link.get_text(strip=True),
            "month": current_month,
        })

    return shows


def _get_show_list():
    """Return cached show list, refreshing if stale."""
    now = time.time()
    if _show_list_cache["data"] and (now - _show_list_cache["ts"]) < SHOW_LIST_TTL:
        return _show_list_cache["data"]

    soup = _fetch_page(BASE_URL)
    shows = _parse_show_list(soup)

    _show_list_cache["data"] = shows
    _show_list_cache["ts"] = now
    return shows


@dog_bp.route("/api/dog/shows")
@limiter.limit("30/minute")
def show_list():
    try:
        shows = _get_show_list()
        return jsonify({"shows": shows})
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="shows", exc_info=True)
        if _show_list_cache["data"]:
            return jsonify({"shows": _show_list_cache["data"]})
        return jsonify({"error": "Failed to fetch show list", "detail": str(exc)}), 502
    except Exception:
        logger.exception("show_list_error")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# GET /api/dog/shows/<show_id> — show detail with breed list
# ---------------------------------------------------------------------------

def _parse_show_detail(soup, show_id):
    """Parse the show detail page: title and breed list."""
    title_el = soup.select_one("#divOtsikko h1")
    title = title_el.get_text(strip=True) if title_el else ""

    breeds = []
    for row in soup.select("table.rotulistatable tr.rotuluettelo"):
        cells = row.find_all("td")
        if not cells:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        name = link.get_text(strip=True)
        href = link.get("href", "")

        r_match = re.search(r"R=(\d+)", href)
        ro_match = re.search(r"RO=(\d+)", href)
        group = r_match.group(1) if r_match else ""
        breed_id = ro_match.group(1) if ro_match else ""

        count_cell = row.find("td", class_="right")
        count_text = count_cell.get_text(strip=True) if count_cell else "0"
        try:
            count = int(count_text)
        except ValueError:
            count = 0

        # Check for results icon (fa-check)
        has_results = bool(row.select_one("td.right i.fa-check"))

        breeds.append({
            "name": name,
            "count": count,
            "group": group,
            "breed_id": breed_id,
            "has_results": has_results,
        })

    return {
        "id": show_id,
        "title": title,
        "breeds": breeds,
    }


@dog_bp.route("/api/dog/shows/<int:show_id>")
@limiter.limit("30/minute")
def show_detail(show_id):
    try:
        if show_id in _show_detail_cache:
            return jsonify(_show_detail_cache[show_id])

        url = f"{BASE_URL}?Id={show_id}"
        soup = _fetch_page(url)
        data = _parse_show_detail(soup, show_id)

        _show_detail_cache[show_id] = data
        return jsonify(data)
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="show_detail", show_id=show_id, exc_info=True)
        return jsonify({"error": "Failed to fetch show detail", "detail": str(exc)}), 502
    except Exception:
        logger.exception("show_detail_error", show_id=show_id)
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# GET /api/dog/shows/<show_id>/results?group=<g>&breed=<b> — breed results
# ---------------------------------------------------------------------------

def _parse_breed_results(soup, show_id):
    """Parse individual breed results from a show page."""
    title_el = soup.select_one("#divOtsikko h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # Breed name: extract from the first breed header on the page
    breed = ""
    breed_header = soup.select_one("tr.ropotsikko td span.left")
    if breed_header:
        breed = breed_header.get_text(strip=True)

    # Judge
    judge = ""
    judge_el = soup.select_one("tr.ropotsikko div.floatright span")
    if judge_el:
        judge_text = judge_el.get_text(strip=True)
        # Strip "Tuomari " prefix
        if judge_text.startswith("Tuomari "):
            judge = judge_text[len("Tuomari "):]
        else:
            judge = judge_text

    # Awards (ROP table)
    awards = []
    for row in soup.select("table.roptulostaulukko tr.roptulos"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            awards.append({
                "type": cells[0].get_text(strip=True),
                "text": cells[1].get_text(strip=True),
            })

    # Individual results
    results = []
    current_gender = ""
    current_class = ""

    results_table = soup.select_one("table.roduntulokset")
    if results_table:
        for row in results_table.find_all("tr"):
            classes = row.get("class", [])

            if "sukupuoli" in classes:
                td = row.find("td")
                if td:
                    current_gender = td.get_text(strip=True)
                continue

            if "luokka" in classes:
                span = row.select_one("td span.left")
                if span:
                    current_class = span.get_text(strip=True)
                continue

            if "tulos" in classes:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue

                # Catalog number
                try:
                    number = int(cells[0].get_text(strip=True))
                except (ValueError, IndexError):
                    number = None

                # Dog name and registry URL
                dog_link = cells[1].find("a")
                dog_name = dog_link.get_text(strip=True) if dog_link else cells[1].get_text(strip=True)
                reg_url = dog_link.get("href", "") if dog_link else ""
                if reg_url and not reg_url.startswith("http"):
                    reg_url = "https://jalostus.kennelliitto.fi" + reg_url

                # Grade
                grade = cells[2].get_text(strip=True)

                # Placement
                placement_text = cells[3].get_text(strip=True)
                try:
                    placement = int(placement_text) if placement_text else None
                except ValueError:
                    placement = None

                # Awards
                awards_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""

                # Critique: look for the next sibling tr.arvostelu
                critique = ""
                next_row = row.find_next_sibling("tr")
                if next_row and "arvostelu" in next_row.get("class", []):
                    critique_cells = next_row.find_all("td")
                    if len(critique_cells) >= 2:
                        critique = critique_cells[1].get_text(strip=True)
                    elif critique_cells:
                        critique = critique_cells[0].get_text(strip=True)

                results.append({
                    "number": number,
                    "name": dog_name,
                    "reg_url": reg_url,
                    "grade": grade,
                    "placement": placement,
                    "awards": awards_text,
                    "critique": critique,
                    "gender": current_gender,
                    "class_name": current_class,
                })

    return {
        "show_id": show_id,
        "title": title,
        "breed": breed,
        "judge": judge,
        "awards": awards,
        "results": results,
    }


@dog_bp.route("/api/dog/shows/<int:show_id>/results")
@limiter.limit("30/minute")
def breed_results(show_id):
    group = flask_request.args.get("group", "")
    breed = flask_request.args.get("breed", "")

    if not group or not breed:
        return jsonify({"error": "Missing required query parameters: group, breed"}), 400

    # Validate that group and breed are numeric
    if not group.isdigit() or not breed.isdigit():
        return jsonify({"error": "Parameters group and breed must be numeric integers"}), 400

    cache_key = (show_id, group, breed)

    try:
        if cache_key in _breed_result_cache:
            return jsonify(_breed_result_cache[cache_key])

        url = f"{BASE_URL}?Id={show_id}&R={group}&RO={breed}"
        soup = _fetch_page(url)
        data = _parse_breed_results(soup, show_id)

        _breed_result_cache[cache_key] = data
        return jsonify(data)
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="breed_results",
                       show_id=show_id, group=group, breed=breed, exc_info=True)
        return jsonify({"error": "Failed to fetch breed results", "detail": str(exc)}), 502
    except Exception:
        logger.exception("breed_results_error", show_id=show_id, group=group, breed=breed)
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# GET /api/dog/search?q=<query> — search breeds or shows
# ---------------------------------------------------------------------------

@dog_bp.route("/api/dog/search")
@limiter.limit("30/minute")
def search_shows():
    query = flask_request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing required query parameter: q"}), 400

    q_lower = query.lower()

    try:
        # Load index first if it hasn't been loaded
        if not _show_index["shows"]:
            _load_index()

        shows = _get_show_list()
        results = []

        for s in shows:
            sid = str(s["id"])
            if sid in _show_index["shows"]:
                show_detail = _show_index["shows"][sid]
                # Check for matching breeds in this show
                for b in show_detail["breeds"]:
                    if q_lower in b["name"].lower():
                        results.append({
                            "show": s,
                            "breed": b
                        })
            else:
                # If show detail is not cached/indexed yet, match by show name as a fallback
                if q_lower in s["name"].lower():
                    results.append({
                        "show": s,
                        "breed": None
                    })

        return jsonify({"query": query, "results": results})
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="search", exc_info=True)
        return jsonify({"error": "Failed to fetch show list for search", "detail": str(exc)}), 502
    except Exception:
        logger.exception("search_error")
        return jsonify({"error": "Internal server error"}), 500
