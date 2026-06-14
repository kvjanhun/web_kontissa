import re
import time
import os
import json
import datetime

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

_show_detail_cache = {}   # {show_id: {"data": data, "ts": timestamp}}
SHOW_DETAIL_TTL = 600     # 10 minutes for recent/ongoing shows

_breed_result_cache = {}  # {(show_id, group, breed): {"data": data, "ts": timestamp}}
BREED_RESULT_TTL = 600    # 10 minutes (for recent/ongoing shows)

_show_all_results_cache = {} # {show_id: {"data": data, "ts": timestamp}}
SHOW_ALL_RESULTS_TTL = 86400  # 24 hours

INDEX_DIR = os.environ.get("DOG_INDEX_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
INDEX_PATH = os.path.join(INDEX_DIR, "dog_show_index.json")

# In-memory index representation
_show_index = {
    "shows": {},       # show_id (str) -> { "title": "...", "month": "...", "breeds": [...] }
    "last_updated": 0
}
_show_index_mtime = 0


def _is_recent_show(month_str):
    """Check if the show month is the current or previous month."""
    if not month_str:
        return True  # Default to recent if unknown

    FINNISH_MONTHS = [
        "tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu",
        "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"
    ]
    try:
        now = datetime.datetime.now()
        cur_year = now.year
        cur_month = now.month

        prev_month = cur_month - 1 if cur_month > 1 else 12
        prev_year = cur_year if cur_month > 1 else cur_year - 1

        cur_str = f"{FINNISH_MONTHS[cur_month - 1]} {cur_year}".lower()
        prev_str = f"{FINNISH_MONTHS[prev_month - 1]} {prev_year}".lower()

        m_lower = month_str.lower().strip()
        return m_lower == cur_str or m_lower == prev_str
    except Exception:
        return True


def _source_url(show_id, group="", breed=""):
    url = f"{BASE_URL}?Id={show_id}"
    if group:
        url += f"&R={group}"
    if breed:
        url += f"&RO={breed}"
    return url


def _utc_iso(ts):
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _index_summary(total_show_count=None):
    updated = _show_index.get("last_updated") or 0
    return {
        "last_updated": updated or None,
        "last_updated_iso": _utc_iso(updated),
        "indexed_show_count": len(_show_index.get("shows", {})),
        "total_show_count": total_show_count,
    }


def _load_index(force=False):
    """Load the persisted breed index when missing or changed on disk."""
    global _show_index, _show_index_mtime

    try:
        mtime = os.path.getmtime(INDEX_PATH)
    except FileNotFoundError:
        if force:
            _show_index = {"shows": {}, "last_updated": 0}
            _show_index_mtime = 0
        return False

    if not force and _show_index_mtime == mtime:
        return False

    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "shows" not in data:
            logger.warning("dog_index_invalid_shape")
            return False
        _show_index = {
            "shows": data.get("shows", {}),
            "last_updated": data.get("last_updated", 0),
        }
        _show_index_mtime = mtime
        logger.info("dog_index_loaded", count=len(_show_index["shows"]))
        return True
    except Exception:
        logger.exception("dog_index_load_failed")
        return False


def _save_index():
    global _show_index_mtime

    tmp_path = f"{INDEX_PATH}.{os.getpid()}.tmp"
    try:
        os.makedirs(INDEX_DIR, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_show_index, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, INDEX_PATH)
        _show_index_mtime = os.path.getmtime(INDEX_PATH)
    except Exception:
        logger.exception("dog_index_save_failed")
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


def _fetch_page(url):
    """Fetch a page from Showlink with timeout and logging."""
    logger.info("showlink_request", url=url)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _show_month_for_id(show_id):
    _load_index()

    sid = str(show_id)
    indexed_show = _show_index.get("shows", {}).get(sid)
    if indexed_show:
        return indexed_show.get("month", "")

    for show in _show_list_cache.get("data") or []:
        if str(show.get("id")) == sid:
            return show.get("month", "")

    return ""


def _is_show_recent_by_id(show_id):
    return _is_recent_show(_show_month_for_id(show_id))


def _cached_show_detail(show_id, allow_stale=False):
    cached = _show_detail_cache.get(show_id)
    if not cached:
        return None

    if "data" not in cached:
        return cached if allow_stale else None

    if allow_stale:
        return cached["data"]

    age = time.time() - cached["ts"]
    if not _is_show_recent_by_id(show_id) or age < SHOW_DETAIL_TTL:
        return cached["data"]

    return None


def crawl_index_once(limit=None, delay=1.5):
    """Refresh missing and recent show breed indexes once.

    This is intentionally called by a standalone process, not by Flask workers.
    """
    _load_index()
    shows_list = _get_show_list()
    if not shows_list:
        return {"total": 0, "updated": 0, "skipped": 0}

    missing = []
    recent = []
    for show in shows_list:
        sid = str(show["id"])
        if sid not in _show_index["shows"]:
            missing.append(show)
        elif _is_recent_show(show.get("month")):
            recent.append(show)

    to_update = missing + recent

    if limit is not None:
        to_update = to_update[:limit]

    updated = 0
    logger.info(
        "dog_crawler_updating_shows",
        count=len(to_update),
        missing=len(missing),
        recent=len(recent),
        total=len(shows_list),
    )

    for idx, show in enumerate(to_update):
        sid = show["id"]
        try:
            soup = _fetch_page(_source_url(sid))
            detail = _parse_show_detail(soup, sid)
            show_updated = time.time()

            _show_index["shows"][str(sid)] = {
                "title": detail["title"],
                "name": show.get("name", ""),
                "date": show.get("date", ""),
                "month": show.get("month", ""),
                "source_url": detail["source_url"],
                "breeds": detail["breeds"],
                "updated_at": show_updated,
                "updated_at_iso": _utc_iso(show_updated),
            }
            _show_index["last_updated"] = show_updated
            _save_index()
            _show_detail_cache.pop(sid, None)
            updated += 1

            logger.info("dog_crawler_indexed_show", show_id=sid, breed_count=len(detail["breeds"]))
        except Exception as e:
            logger.warning("dog_crawler_show_failed", show_id=sid, error=str(e))

        if delay and idx < len(to_update) - 1:
            time.sleep(delay)

    return {
        "total": len(shows_list),
        "updated": updated,
        "skipped": len(shows_list) - len(to_update),
        "index": _index_summary(total_show_count=len(shows_list)),
    }


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

        show_id = int(match.group(1))
        shows.append({
            "id": show_id,
            "date": link.get_text(strip=True),
            "name": name_link.get_text(strip=True),
            "month": current_month,
            "source_url": _source_url(show_id),
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
        _load_index()
        return jsonify({"shows": shows, "index": _index_summary(total_show_count=len(shows))})
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="shows", exc_info=True)
        if _show_list_cache["data"]:
            shows = _show_list_cache["data"]
            return jsonify({"shows": shows, "index": _index_summary(total_show_count=len(shows))})
        return jsonify({"error": "Failed to fetch show list", "detail": str(exc)}), 502
    except Exception:
        logger.exception("show_list_error")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# GET /api/dog/shows/<show_id> — show detail with breed list
# ---------------------------------------------------------------------------

def _parse_breeds_from_soup(soup, show_id=None):
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
        id_match = re.search(r"Id=(\d+)", href)
        linked_show_id = show_id or (id_match.group(1) if id_match else "")
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
            "source_url": _source_url(linked_show_id, group, breed_id) if linked_show_id and group and breed_id else "",
        })
    return breeds


def _parse_show_detail(soup, show_id):
    """Parse the show detail page: title and breed list."""
    title_el = soup.select_one("#divOtsikko h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # 1. Parse breeds on the landing page (for specialty shows)
    breeds = _parse_breeds_from_soup(soup, show_id)

    # 2. If no breeds found, look for group links (FCI groups R=1..10)
    if not breeds:
        group_links = []
        content = soup.find(id="divContent") or soup.find(id="content") or soup
        for a in content.find_all("a"):
            href = a.get("href", "")
            match = re.search(r"R=(\d+)", href)
            # Only match groups 1-10
            if match:
                group_num = match.group(1)
                if group_num.isdigit() and 1 <= int(group_num) <= 10:
                    group_links.append((group_num, href))

        # Remove duplicate group numbers
        seen_groups = set()
        unique_groups = []
        for g, href in group_links:
            if g not in seen_groups:
                seen_groups.add(g)
                unique_groups.append((g, href))

        if unique_groups:
            logger.info("dog_show_groups_found", show_id=show_id, groups=[g[0] for g in unique_groups])
            for g_num, href in unique_groups:
                url = f"{BASE_URL}?Id={show_id}&R={g_num}"
                try:
                    # Sleep 0.5s to be polite during nested crawls
                    time.sleep(0.5)
                    group_soup = _fetch_page(url)
                    group_breeds = _parse_breeds_from_soup(group_soup, show_id)
                    breeds.extend(group_breeds)
                except Exception as e:
                    logger.warning("dog_show_group_fetch_failed", show_id=show_id, group=g_num, error=str(e))

    return {
        "id": show_id,
        "title": title,
        "breeds": breeds,
        "source_url": _source_url(show_id),
    }


@dog_bp.route("/api/dog/shows/<int:show_id>")
@limiter.limit("30/minute")
def show_detail(show_id):
    try:
        cached = _cached_show_detail(show_id)
        if cached:
            return jsonify(cached)

        url = _source_url(show_id)
        soup = _fetch_page(url)
        data = _parse_show_detail(soup, show_id)
        fetched_at = time.time()
        data["fetched_at"] = fetched_at
        data["fetched_at_iso"] = _utc_iso(fetched_at)

        # Enrich breeds with judge info from the index if available
        try:
            _load_index()
            sid_str = str(show_id)
            if sid_str in _show_index["shows"]:
                idx_show = _show_index["shows"][sid_str]
                idx_breeds = { (str(b.get("group")), str(b.get("breed_id"))): b.get("judge") for b in idx_show.get("breeds", []) if b.get("judge") }
                for breed_data in data.get("breeds", []):
                    key = (str(breed_data.get("group")), str(breed_data.get("breed_id")))
                    if key in idx_breeds:
                        breed_data["judge"] = idx_breeds[key]
        except Exception as e:
            logger.warning("dog_detail_judge_enrich_failed", show_id=show_id, error=str(e))

        _show_detail_cache[show_id] = {"data": data, "ts": fetched_at}
        return jsonify(data)
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="show_detail", show_id=show_id, exc_info=True)
        stale = _cached_show_detail(show_id, allow_stale=True)
        if stale:
            return jsonify(stale)
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

    group_num = int(group)
    breed_num = int(breed)
    if group_num < 1 or group_num > 10 or breed_num < 1:
        return jsonify({"error": "Parameters group and breed are outside the supported range"}), 400

    cache_key = (show_id, group, breed)
    now = time.time()

    # Check if the show is recent/ongoing
    is_recent = _is_show_recent_by_id(show_id)

    try:
        if cache_key in _breed_result_cache:
            cached = _breed_result_cache[cache_key]
            if not is_recent or (now - cached["ts"]) < BREED_RESULT_TTL:
                return jsonify(cached["data"])

        url = _source_url(show_id, group, breed)
        soup = _fetch_page(url)
        data = _parse_breed_results(soup, show_id)
        data["source_url"] = url
        data["fetched_at"] = now
        data["fetched_at_iso"] = _utc_iso(now)

        # Update show index with judge name if we fetched it
        try:
            _load_index()
            sid_str = str(show_id)
            if sid_str in _show_index["shows"]:
                show_data = _show_index["shows"][sid_str]
                updated_index = False
                for b_data in show_data.get("breeds", []):
                    if str(b_data.get("group")) == str(group) and str(b_data.get("breed_id")) == str(breed):
                        if b_data.get("judge") != data.get("judge"):
                            b_data["judge"] = data.get("judge")
                            updated_index = True
                if updated_index:
                    _save_index()
        except Exception as e:
            logger.warning("dog_index_judge_update_failed", show_id=show_id, error=str(e))

        _breed_result_cache[cache_key] = {"data": data, "ts": now}
        return jsonify(data)
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="breed_results",
                       show_id=show_id, group=group, breed=breed, exc_info=True)
        if cache_key in _breed_result_cache:
            return jsonify(_breed_result_cache[cache_key]["data"])
        return jsonify({"error": "Failed to fetch breed results", "detail": str(exc)}), 502
    except Exception:
        logger.exception("breed_results_error", show_id=show_id, group=group, breed=breed)
        return jsonify({"error": "Internal server error"}), 500


@dog_bp.route("/api/dog/shows/<int:show_id>/all-results")
@limiter.limit("10/minute")
def show_all_results(show_id):
    now = time.time()
    is_recent = _is_show_recent_by_id(show_id)

    if show_id in _show_all_results_cache:
        cached = _show_all_results_cache[show_id]
        if not is_recent or (now - cached["ts"]) < SHOW_ALL_RESULTS_TTL:
            return jsonify(cached["data"])

    try:
        show_detail_data = _cached_show_detail(show_id)
        if not show_detail_data:
            url = _source_url(show_id)
            soup = _fetch_page(url)
            show_detail_data = _parse_show_detail(soup, show_id)
            show_detail_data["fetched_at"] = now
            show_detail_data["fetched_at_iso"] = _utc_iso(now)
            _show_detail_cache[show_id] = {"data": show_detail_data, "ts": now}

        breeds_with_results = [b for b in show_detail_data.get("breeds", []) if b.get("has_results")]

        all_results = []
        for breed in breeds_with_results:
            group = breed.get("group", "")
            breed_id = breed.get("breed_id", "")
            if not group or not breed_id:
                continue

            cache_key = (show_id, str(group), str(breed_id))
            breed_data = None
            if cache_key in _breed_result_cache:
                cached_breed = _breed_result_cache[cache_key]
                if not is_recent or (now - cached_breed["ts"]) < BREED_RESULT_TTL:
                    breed_data = cached_breed["data"]

            if not breed_data:
                # Polite delay to prevent rate limits or IP bans from external server
                time.sleep(0.3)
                breed_url = _source_url(show_id, group, breed_id)
                breed_soup = _fetch_page(breed_url)
                breed_data = _parse_breed_results(breed_soup, show_id)
                breed_data["source_url"] = breed_url
                breed_data["fetched_at"] = now
                breed_data["fetched_at_iso"] = _utc_iso(now)
                _breed_result_cache[cache_key] = {"data": breed_data, "ts": now}

            # Map dogs
            for dog in breed_data.get("results", []):
                all_results.append({
                    "number": dog.get("number"),
                    "name": dog.get("name"),
                    "reg_url": dog.get("reg_url"),
                    "grade": dog.get("grade"),
                    "placement": dog.get("placement"),
                    "awards": dog.get("awards"),
                    "critique": dog.get("critique"),
                    "gender": dog.get("gender"),
                    "class_name": dog.get("class_name"),
                    "breedName": breed.get("name"),
                    "breedGroup": group,
                    "breedId": breed_id,
                    "breedObj": breed
                })

        response_data = {
            "show_id": show_id,
            "results": all_results,
            "fetched_at": now,
            "fetched_at_iso": _utc_iso(now)
        }
        _show_all_results_cache[show_id] = {"data": response_data, "ts": now}
        return jsonify(response_data)
    except Exception as e:
        logger.exception("show_all_results_error", show_id=show_id)
        return jsonify({"error": "Failed to fetch show all results", "detail": str(e)}), 500


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
        _load_index()

        shows = _get_show_list()
        results = []

        for show in shows:
            sid = str(show["id"])
            show_text = " ".join([
                show.get("name", ""),
                show.get("date", ""),
                show.get("month", ""),
            ]).lower()
            show_matches = q_lower in show_text

            indexed_show = _show_index["shows"].get(sid)
            breed_matches = []
            if indexed_show:
                for breed_data in indexed_show.get("breeds", []):
                    breed_name = breed_data.get("name", "").lower()
                    judge_name = breed_data.get("judge", "").lower()
                    if q_lower in breed_name or q_lower in judge_name:
                        breed_matches.append(breed_data)

            if breed_matches:
                for breed_data in breed_matches:
                    results.append({
                        "show": show,
                        "breed": breed_data,
                        "match": "breed",
                    })
            elif show_matches:
                results.append({
                    "show": show,
                    "breed": None,
                    "match": "show",
                })

        return jsonify({
            "query": query,
            "results": results,
            "index": _index_summary(total_show_count=len(shows)),
        })
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="search", exc_info=True)
        return jsonify({"error": "Failed to fetch show list for search", "detail": str(exc)}), 502
    except Exception:
        logger.exception("search_error")
        return jsonify({"error": "Internal server error"}), 500
