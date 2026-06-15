import re
import time
import os
import json
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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
SHOW_ALL_RESULTS_TTL = 86400  # 24 hours fallback when show date is unknown
RESULT_CACHE_ACTIVE_TTL = int(os.environ.get("DOG_RESULT_ACTIVE_TTL", "21600"))  # 6 hours
RESULT_CACHE_SETTLED_TTL = int(os.environ.get("DOG_RESULT_SETTLED_TTL", "604800"))  # 7 days
RESULT_CACHE_SETTLED_AFTER_DAYS = int(os.environ.get("DOG_RESULT_SETTLED_AFTER_DAYS", "2"))
RESULT_AUTO_WINDOW_DAYS = int(os.environ.get("DOG_RESULT_AUTO_WINDOW_DAYS", "7"))

INDEX_DIR = os.environ.get("DOG_INDEX_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
INDEX_PATH = os.path.join(INDEX_DIR, "dog_show_index.json")
RESULT_CACHE_DIR = os.environ.get("DOG_RESULT_CACHE_DIR", os.path.join(INDEX_DIR, "dog_result_cache"))
RESULT_JOBS_PATH = os.environ.get("DOG_RESULT_JOBS_PATH", os.path.join(INDEX_DIR, "dog_result_jobs.json"))
RESULT_CACHE_VERSION = 1
RESULT_RETRY_AFTER_SECONDS = 2
RESULT_JOB_STALE_SECONDS = 1800
RESULT_JOB_BACKOFF_SECONDS = 300
RESULT_CRAWL_DEFAULT_DELAY = 0.4
RESULT_CRAWL_DEFAULT_WORKERS = 3
RESULT_IMMEDIATE_WARMUP = os.environ.get("DOG_RESULT_IMMEDIATE_WARMUP", "true").lower() != "false"
RESULT_IMMEDIATE_MAX_ACTIVE = int(os.environ.get("DOG_RESULT_IMMEDIATE_MAX_ACTIVE", "1"))

FINNISH_MONTHS = [
    "tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu",
    "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"
]

# In-memory index representation
_show_index = {
    "shows": {},       # show_id (str) -> { "title": "...", "month": "...", "breeds": [...] }
    "last_updated": 0
}
_show_index_mtime = 0
_immediate_warmups = set()
_immediate_warmups_lock = threading.Lock()
_immediate_warmup_slots = threading.BoundedSemaphore(max(1, RESULT_IMMEDIATE_MAX_ACTIVE))


def _is_recent_show(month_str):
    """Check if the show month is the current or previous month."""
    if not month_str:
        return True  # Default to recent if unknown

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


def _month_year_from_label(month_str):
    if not month_str:
        return None, None

    parts = month_str.lower().strip().split()
    if len(parts) < 2:
        return None, None

    try:
        month = FINNISH_MONTHS.index(parts[0]) + 1
        year = int(parts[1])
        return month, year
    except (ValueError, IndexError):
        return None, None


def _parse_show_date(show):
    """Parse Showlink list dates such as '14.06.' or '14.-15.06.'."""
    if not show:
        return None

    date_str = str(show.get("date") or "").strip()
    if not date_str:
        return None

    matches = re.findall(r"(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?", date_str)
    if not matches:
        return None

    day_str, month_str, year_str = matches[-1]
    month = int(month_str)
    year = int(year_str) if year_str else None
    if year is None:
        month_from_label, year_from_label = _month_year_from_label(show.get("month", ""))
        year = year_from_label
        if month_from_label:
            month = month_from_label
    if year is None:
        return None

    try:
        return datetime.date(year, month, int(day_str))
    except ValueError:
        return None


def _show_list_item_for_id(show_id):
    sid = str(show_id)
    for show in _show_list_cache.get("data") or []:
        if str(show.get("id")) == sid:
            return show
    return None


def _indexed_show_as_list_item(show_id):
    indexed_show = _indexed_show(show_id)
    if not indexed_show:
        return None
    return {
        "id": int(show_id),
        "date": indexed_show.get("date", ""),
        "month": indexed_show.get("month", ""),
    }


def _show_date_for_id(show_id):
    return _parse_show_date(_show_list_item_for_id(show_id) or _indexed_show_as_list_item(show_id))


def _show_age_days(show, today=None):
    show_date = _parse_show_date(show)
    if not show_date:
        return None
    today = today or datetime.date.today()
    return (today - show_date).days


def _index_summary(total_show_count=None):
    updated = _show_index.get("last_updated") or 0
    return {
        "last_updated": updated or None,
        "last_updated_iso": _utc_iso(updated),
        "indexed_show_count": len(_show_index.get("shows", {})),
        "total_show_count": total_show_count,
    }


def _show_stats_from_index(show_id):
    indexed_show = _show_index.get("shows", {}).get(str(show_id))
    if not indexed_show:
        return None

    breeds = indexed_show.get("breeds") or []
    if not breeds:
        return None

    entry_count = 0
    entry_count_known = False
    result_breed_count = 0

    for breed in breeds:
        if breed.get("has_results"):
            result_breed_count += 1

        try:
            entry_count += int(breed.get("count"))
            entry_count_known = True
        except (TypeError, ValueError):
            continue

    updated = indexed_show.get("updated_at") or _show_index.get("last_updated") or 0
    return {
        "indexed": True,
        "breed_count": len(breeds),
        "entry_count": entry_count if entry_count_known else None,
        "result_breed_count": result_breed_count,
        "updated_at": updated or None,
        "updated_at_iso": _utc_iso(updated),
    }


def _shows_with_cached_stats(shows):
    enriched = []
    for show in shows:
        item = dict(show)
        stats = _show_stats_from_index(show.get("id"))
        if stats:
            item["stats"] = stats
        enriched.append(item)
    return enriched


def _persist_show_detail_to_index(show_id, detail, updated_at):
    breeds = detail.get("breeds") or []
    if not breeds:
        return

    _load_index()
    sid = str(int(show_id))
    existing = _show_index.get("shows", {}).get(sid) or {}
    list_item = _show_list_item_for_id(show_id) or {}

    _show_index.setdefault("shows", {})[sid] = {
        "title": detail.get("title") or existing.get("title", ""),
        "name": list_item.get("name") or existing.get("name") or detail.get("title", ""),
        "date": list_item.get("date") or existing.get("date", ""),
        "month": list_item.get("month") or existing.get("month", ""),
        "source_url": detail.get("source_url") or existing.get("source_url") or _source_url(show_id),
        "breeds": breeds,
        "updated_at": updated_at,
        "updated_at_iso": _utc_iso(updated_at),
    }
    _show_index["last_updated"] = updated_at
    _save_index()


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


def _atomic_write_json(path, data):
    tmp_path = f"{path}.{os.getpid()}.tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        logger.exception("dog_json_save_failed", path=path)
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _result_cache_path(show_id):
    return os.path.join(RESULT_CACHE_DIR, f"{int(show_id)}.json")


def _load_result_cache_doc(show_id):
    try:
        with open(_result_cache_path(show_id), "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        logger.exception("dog_result_cache_load_failed", show_id=show_id)
        return None

    if not isinstance(data, dict):
        logger.warning("dog_result_cache_invalid_shape", show_id=show_id)
        return None
    return data


def _save_result_cache_doc(show_id, doc):
    _atomic_write_json(_result_cache_path(show_id), doc)


def _load_result_jobs():
    try:
        with open(RESULT_JOBS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"jobs": {}, "updated_at": 0}
    except Exception:
        logger.exception("dog_result_jobs_load_failed")
        return {"jobs": {}, "updated_at": 0}

    if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
        logger.warning("dog_result_jobs_invalid_shape")
        return {"jobs": {}, "updated_at": 0}
    return data


def _save_result_jobs(data):
    _atomic_write_json(RESULT_JOBS_PATH, data)


def _queue_result_cache_job(show_id, reason="user"):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid, {})

    if job.get("state") != "running":
        job["state"] = "queued"
    job["show_id"] = int(show_id)
    job["reason"] = reason
    job.setdefault("created_at", now)
    job.setdefault("attempts", 0)
    job["requested_at"] = now
    job["updated_at"] = now
    job.setdefault("next_attempt_at", now)
    jobs[sid] = job
    jobs_doc["updated_at"] = now
    _save_result_jobs(jobs_doc)
    return job


def _set_result_job_running(show_id):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid, {"show_id": int(show_id), "created_at": now, "attempts": 0})
    job["state"] = "running"
    job["updated_at"] = now
    job["last_started_at"] = now
    jobs[sid] = job
    jobs_doc["updated_at"] = now
    _save_result_jobs(jobs_doc)
    return job


def _claim_result_cache_job(show_id, reason="user-immediate"):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid, {"show_id": int(show_id), "created_at": now, "attempts": 0})

    if job.get("state") == "running" and not _result_job_due(job, now=now):
        return None

    job["state"] = "running"
    job["show_id"] = int(show_id)
    job["reason"] = reason
    job.setdefault("created_at", now)
    job.setdefault("attempts", 0)
    job["requested_at"] = now
    job["updated_at"] = now
    job["last_started_at"] = now
    jobs[sid] = job
    jobs_doc["updated_at"] = now
    _save_result_jobs(jobs_doc)
    return job


def _remove_result_cache_job(show_id):
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    if sid in jobs:
        jobs.pop(sid, None)
        jobs_doc["updated_at"] = time.time()
        _save_result_jobs(jobs_doc)


def _defer_result_cache_job(show_id, error):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid, {"show_id": int(show_id), "created_at": now})
    attempts = int(job.get("attempts") or 0) + 1
    backoff = min(3600, RESULT_JOB_BACKOFF_SECONDS * attempts)
    job.update({
        "state": "queued",
        "attempts": attempts,
        "last_error": str(error)[:500],
        "next_attempt_at": now + backoff,
        "updated_at": now,
    })
    jobs[sid] = job
    jobs_doc["updated_at"] = now
    _save_result_jobs(jobs_doc)
    return job


def _result_job_due(job, now=None):
    now = now or time.time()
    if job.get("state") == "running":
        updated_at = job.get("updated_at") or 0
        if (now - updated_at) < RESULT_JOB_STALE_SECONDS:
            return False
    return (job.get("next_attempt_at") or 0) <= now


def _indexed_show(show_id):
    _load_index()
    return _show_index.get("shows", {}).get(str(show_id))


def _result_breeds_from_index(show_id):
    indexed_show = _indexed_show(show_id)
    if not indexed_show:
        return []
    return [dict(breed) for breed in indexed_show.get("breeds", [])]


def _result_breeds_with_results(breeds):
    return [
        breed for breed in breeds
        if breed.get("has_results") and breed.get("group") and breed.get("breed_id")
    ]


def _result_cache_doc_is_complete(doc):
    return bool(doc and doc.get("status") == "complete")


def _result_cache_doc_is_fresh(show_id, doc, now=None):
    if not _result_cache_doc_is_complete(doc):
        return False

    cached_at = doc.get("cached_at") or doc.get("updated_at") or 0
    if not cached_at:
        return False

    now = now or time.time()
    if not _is_show_recent_by_id(show_id):
        return True

    show_date = _show_date_for_id(show_id)
    if show_date:
        today = datetime.datetime.fromtimestamp(now).date()
        age_days = (today - show_date).days
        if age_days > RESULT_AUTO_WINDOW_DAYS:
            return True
        ttl = RESULT_CACHE_ACTIVE_TTL if age_days <= RESULT_CACHE_SETTLED_AFTER_DAYS else RESULT_CACHE_SETTLED_TTL
        return (now - cached_at) < ttl

    return (now - cached_at) < SHOW_ALL_RESULTS_TTL


def _result_cache_due(show_id, now=None):
    doc = _load_result_cache_doc(show_id)
    if not doc:
        return True
    return not _result_cache_doc_is_fresh(show_id, doc, now=now)


def _result_cache_progress(show_id, doc=None, job=None):
    doc = doc or _load_result_cache_doc(show_id) or {}
    job = job or _load_result_jobs().get("jobs", {}).get(str(int(show_id)), {})

    completed_breeds = doc.get("completed_breeds") or {}
    failed_breeds = doc.get("failed_breeds") or {}
    total_breeds = doc.get("total_breeds")
    if total_breeds is None:
        total_breeds = len(_result_breeds_with_results(_result_breeds_from_index(show_id)))
        if total_breeds == 0:
            total_breeds = None

    fetched_breeds = len(completed_breeds)
    percent = None
    if total_breeds:
        percent = min(100, round((fetched_breeds / total_breeds) * 100))
    elif doc.get("status") == "complete":
        percent = 100

    state = job.get("state") or doc.get("status") or "queued"
    return {
        "state": state,
        "total_breeds": total_breeds,
        "fetched_breeds": fetched_breeds,
        "failed_breeds": len(failed_breeds),
        "total_dogs": len(doc.get("results") or []),
        "percent": percent,
        "started_at": doc.get("started_at") or job.get("last_started_at"),
        "started_at_iso": _utc_iso(doc.get("started_at") or job.get("last_started_at")),
        "updated_at": doc.get("updated_at") or job.get("updated_at"),
        "updated_at_iso": _utc_iso(doc.get("updated_at") or job.get("updated_at")),
        "next_attempt_at": job.get("next_attempt_at"),
        "next_attempt_at_iso": _utc_iso(job.get("next_attempt_at")),
        "last_error": doc.get("last_error") or job.get("last_error"),
    }


def _result_response_from_doc(show_id, doc, stale=False):
    fetched_at = doc.get("cached_at") or doc.get("updated_at") or time.time()
    progress = _result_cache_progress(show_id, doc=doc)
    return {
        "show_id": int(show_id),
        "title": doc.get("title", ""),
        "source_url": doc.get("source_url") or _source_url(show_id),
        "results": doc.get("results") or [],
        "fetched_at": fetched_at,
        "fetched_at_iso": _utc_iso(fetched_at),
        "cache": {
            "status": "stale" if stale else "complete",
            "stale": stale,
            "total_breeds": progress["total_breeds"],
            "fetched_breeds": progress["fetched_breeds"],
            "failed_breeds": progress["failed_breeds"],
            "total_dogs": progress["total_dogs"],
            "percent": progress["percent"],
            "cached_at": doc.get("cached_at"),
            "cached_at_iso": _utc_iso(doc.get("cached_at")),
        },
    }


def _cached_all_results_response(show_id, allow_stale=False):
    now = time.time()

    cached = _show_all_results_cache.get(int(show_id))
    if cached and cached.get("data"):
        stale = _is_show_recent_by_id(show_id) and (now - (cached.get("ts") or 0)) >= SHOW_ALL_RESULTS_TTL
        if not stale or allow_stale:
            data = dict(cached["data"])
            if data.get("cache"):
                data["cache"] = dict(data["cache"])
                data["cache"]["status"] = "stale" if stale else "complete"
                data["cache"]["stale"] = stale
            return data

    doc = _load_result_cache_doc(show_id)
    if not _result_cache_doc_is_complete(doc):
        return None

    stale = not _result_cache_doc_is_fresh(show_id, doc, now=now)
    if stale and not allow_stale:
        return None

    response = _result_response_from_doc(show_id, doc, stale=stale)
    _show_all_results_cache[int(show_id)] = {
        "data": response,
        "ts": doc.get("cached_at") or doc.get("updated_at") or now,
    }
    return response


def _breed_results_from_all_results_cache(show_id, group, breed):
    doc = _load_result_cache_doc(show_id)
    if not _result_cache_doc_is_complete(doc):
        return None

    group = str(group)
    breed = str(breed)
    breed_key = f"{group}:{breed}"
    completed_breeds = doc.get("completed_breeds") or {}
    if breed_key not in completed_breeds:
        return None

    matched = [
        dog for dog in doc.get("results", [])
        if str(dog.get("breedGroup")) == group and str(dog.get("breedId")) == breed
    ]

    breed_obj = None
    if matched:
        breed_obj = matched[0].get("breedObj") or {}
    else:
        indexed_show = _indexed_show(show_id) or {}
        for item in indexed_show.get("breeds", []):
            if str(item.get("group")) == group and str(item.get("breed_id")) == breed:
                breed_obj = item
                break
    breed_obj = breed_obj or {}

    fetched_at = doc.get("cached_at") or doc.get("updated_at") or time.time()
    return {
        "show_id": int(show_id),
        "title": doc.get("title", ""),
        "breed": breed_obj.get("name", ""),
        "judge": breed_obj.get("judge", ""),
        "awards": [],
        "results": [
            {
                "number": dog.get("number"),
                "name": dog.get("name"),
                "reg_url": dog.get("reg_url"),
                "grade": dog.get("grade"),
                "placement": dog.get("placement"),
                "awards": dog.get("awards"),
                "critique": dog.get("critique"),
                "gender": dog.get("gender"),
                "class_name": dog.get("class_name"),
            }
            for dog in matched
        ],
        "source_url": _source_url(show_id, group, breed),
        "fetched_at": fetched_at,
        "fetched_at_iso": _utc_iso(fetched_at),
        "cache": {
            "status": "show_all_results",
            "cached_at": doc.get("cached_at"),
            "cached_at_iso": _utc_iso(doc.get("cached_at")),
        },
    }


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
    empty_indexed = []
    recent = []
    for show in shows_list:
        sid = str(show["id"])
        indexed_show = _show_index["shows"].get(sid)
        if not indexed_show:
            missing.append(show)
        elif not indexed_show.get("breeds") and not indexed_show.get("empty_breed_list_confirmed"):
            empty_indexed.append(show)
        elif _is_recent_show(show.get("month")):
            recent.append(show)

    to_update = empty_indexed + missing + recent

    if limit is not None:
        to_update = to_update[:limit]

    updated = 0
    logger.info(
        "dog_crawler_updating_shows",
        count=len(to_update),
        missing=len(missing),
        empty_indexed=len(empty_indexed),
        recent=len(recent),
        total=len(shows_list),
    )

    for idx, show in enumerate(to_update):
        sid = show["id"]
        try:
            soup = _fetch_page(_source_url(sid))
            detail = _parse_show_detail(soup, sid)
            show_updated = time.time()

            indexed_entry = {
                "title": detail["title"],
                "name": show.get("name", ""),
                "date": show.get("date", ""),
                "month": show.get("month", ""),
                "source_url": detail["source_url"],
                "breeds": detail["breeds"],
                "updated_at": show_updated,
                "updated_at_iso": _utc_iso(show_updated),
            }
            if not detail["breeds"]:
                indexed_entry["empty_breed_list_confirmed"] = True

            _show_index["shows"][str(sid)] = indexed_entry
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


def _show_detail_for_result_cache(show_id):
    indexed_show = _indexed_show(show_id)
    if indexed_show and indexed_show.get("breeds"):
        return {
            "id": int(show_id),
            "title": indexed_show.get("title") or indexed_show.get("name", ""),
            "source_url": indexed_show.get("source_url") or _source_url(show_id),
            "breeds": [dict(breed) for breed in indexed_show.get("breeds", [])],
        }

    cached = _cached_show_detail(show_id, allow_stale=True)
    if cached and cached.get("breeds"):
        return cached

    soup = _fetch_page(_source_url(show_id))
    detail = _parse_show_detail(soup, show_id)
    fetched_at = time.time()
    detail["fetched_at"] = fetched_at
    detail["fetched_at_iso"] = _utc_iso(fetched_at)
    _show_detail_cache[int(show_id)] = {"data": detail, "ts": fetched_at}
    return detail


def _show_detail_from_index(show_id):
    indexed_show = _indexed_show(show_id)
    if not indexed_show or not indexed_show.get("breeds"):
        return None

    updated_at = indexed_show.get("updated_at") or _show_index.get("last_updated") or time.time()
    return {
        "id": int(show_id),
        "title": indexed_show.get("title") or indexed_show.get("name", ""),
        "breeds": [dict(breed) for breed in indexed_show.get("breeds", [])],
        "source_url": indexed_show.get("source_url") or _source_url(show_id),
        "fetched_at": updated_at,
        "fetched_at_iso": _utc_iso(updated_at),
        "cache": {
            "status": "indexed",
            "source": "dog_show_index",
            "updated_at": updated_at,
            "updated_at_iso": _utc_iso(updated_at),
        },
    }


def _all_results_doc_base(show_id, source, existing=None):
    now = time.time()
    existing = existing if isinstance(existing, dict) else {}
    return {
        "version": RESULT_CACHE_VERSION,
        "show_id": int(show_id),
        "status": "running",
        "source": source,
        "title": existing.get("title", ""),
        "source_url": existing.get("source_url") or _source_url(show_id),
        "started_at": existing.get("started_at") or now,
        "updated_at": now,
        "cached_at": None,
        "total_breeds": existing.get("total_breeds"),
        "completed_breeds": existing.get("completed_breeds") or {},
        "failed_breeds": existing.get("failed_breeds") or {},
        "results": existing.get("results") or [],
    }


def _breed_result_cache_key(show_id, group, breed_id):
    return (int(show_id), str(group), str(breed_id))


def _map_breed_results_to_all_results(show_id, breed, breed_data):
    group = str(breed.get("group", ""))
    breed_id = str(breed.get("breed_id", ""))
    breed_obj = dict(breed)
    if breed_data.get("judge"):
        breed_obj["judge"] = breed_data.get("judge")

    mapped = []
    for dog in breed_data.get("results", []):
        mapped.append({
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
            "breedObj": breed_obj,
        })
    return mapped


def _breed_cache_key_from_breed(breed):
    return f"{breed.get('group', '')}:{breed.get('breed_id', '')}"


def _fetch_breed_results_for_show_cache(show_id, breed):
    group = str(breed.get("group", ""))
    breed_id = str(breed.get("breed_id", ""))
    breed_url = _source_url(show_id, group, breed_id)
    breed_soup = _fetch_page(breed_url)
    breed_data = _parse_breed_results(breed_soup, show_id)
    fetched_at = time.time()
    breed_data["source_url"] = breed_url
    breed_data["fetched_at"] = fetched_at
    breed_data["fetched_at_iso"] = _utc_iso(fetched_at)
    mapped_results = _map_breed_results_to_all_results(show_id, breed, breed_data)
    return {
        "breed": breed,
        "breed_key": _breed_cache_key_from_breed(breed),
        "breed_data": breed_data,
        "mapped_results": mapped_results,
        "fetched_at": fetched_at,
    }


def _save_result_doc_progress(show_id, doc, preserve_existing_complete):
    if not preserve_existing_complete:
        _save_result_cache_doc(show_id, doc)


def _record_result_breed_failure(show_id, doc, breed, exc, preserve_existing_complete):
    breed_key = _breed_cache_key_from_breed(breed)
    now = time.time()
    failed_breeds = doc.setdefault("failed_breeds", {})
    failed_breeds[breed_key] = {
        "name": breed.get("name", ""),
        "error": str(exc)[:500],
        "updated_at": now,
        "updated_at_iso": _utc_iso(now),
    }
    doc["status"] = "partial"
    doc["last_error"] = str(exc)
    doc["updated_at"] = now
    _save_result_doc_progress(show_id, doc, preserve_existing_complete)
    logger.warning(
        "dog_result_cache_breed_failed",
        show_id=show_id,
        group=breed.get("group", ""),
        breed=breed.get("breed_id", ""),
        error=str(exc),
    )
    return {
        "show_id": show_id,
        "status": "partial",
        "error": str(exc),
        "progress": _result_cache_progress(show_id, doc=doc),
    }


def _record_result_breed_success(show_id, doc, item, preserve_existing_complete):
    breed = item["breed"]
    group = str(breed.get("group", ""))
    breed_id = str(breed.get("breed_id", ""))
    fetched_at = item["fetched_at"]
    mapped_results = item["mapped_results"]

    _breed_result_cache[_breed_result_cache_key(show_id, group, breed_id)] = {
        "data": item["breed_data"],
        "ts": fetched_at,
    }

    doc.setdefault("results", []).extend(mapped_results)
    doc.setdefault("completed_breeds", {})[item["breed_key"]] = {
        "name": breed.get("name", ""),
        "result_count": len(mapped_results),
        "updated_at": fetched_at,
        "updated_at_iso": _utc_iso(fetched_at),
    }
    doc.setdefault("failed_breeds", {}).pop(item["breed_key"], None)
    doc["updated_at"] = fetched_at
    _save_result_doc_progress(show_id, doc, preserve_existing_complete)


def _crawl_missing_breed_results(show_id, pending_breeds, doc, delay, workers, preserve_existing_complete):
    workers = max(1, int(workers or 1))
    if workers == 1:
        for breed in pending_breeds:
            if delay:
                time.sleep(delay)
            try:
                item = _fetch_breed_results_for_show_cache(show_id, breed)
            except Exception as exc:
                return _record_result_breed_failure(show_id, doc, breed, exc, preserve_existing_complete)
            _record_result_breed_success(show_id, doc, item, preserve_existing_complete)
        return None

    breed_iter = iter(pending_breeds)
    futures = {}

    def submit_next(executor):
        try:
            breed = next(breed_iter)
        except StopIteration:
            return False
        if delay:
            time.sleep(delay)
        futures[executor.submit(_fetch_breed_results_for_show_cache, show_id, breed)] = breed
        return True

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for _ in range(min(workers, len(pending_breeds))):
            submit_next(executor)

        while futures:
            for future in as_completed(list(futures.keys())):
                breed = futures.pop(future)
                try:
                    item = future.result()
                except Exception as exc:
                    for pending in futures:
                        pending.cancel()
                    return _record_result_breed_failure(show_id, doc, breed, exc, preserve_existing_complete)
                _record_result_breed_success(show_id, doc, item, preserve_existing_complete)
                submit_next(executor)
                break

    return None


def crawl_result_cache_for_show(show_id, delay=RESULT_CRAWL_DEFAULT_DELAY, force=False, source="manual", workers=RESULT_CRAWL_DEFAULT_WORKERS):
    """Build or resume the persisted whole-show results cache for one show."""
    show_id = int(show_id)
    now = time.time()
    existing = _load_result_cache_doc(show_id)
    if not force and _result_cache_doc_is_fresh(show_id, existing, now=now):
        return {
            "show_id": show_id,
            "status": "skipped",
            "reason": "fresh",
            "progress": _result_cache_progress(show_id, doc=existing),
        }

    preserve_existing_complete = (
        _result_cache_doc_is_complete(existing)
        and not _result_cache_doc_is_fresh(show_id, existing, now=now)
        and not force
    )
    resumable = (
        isinstance(existing, dict)
        and existing.get("status") in {"running", "partial", "failed"}
        and not force
    )
    doc = _all_results_doc_base(show_id, source, existing=existing if resumable else None)
    if not preserve_existing_complete:
        _save_result_cache_doc(show_id, doc)

    try:
        show_detail_data = _show_detail_for_result_cache(show_id)
    except Exception as exc:
        doc["status"] = "failed"
        doc["last_error"] = str(exc)
        doc["updated_at"] = time.time()
        if not preserve_existing_complete:
            _save_result_cache_doc(show_id, doc)
        logger.warning("dog_result_cache_detail_failed", show_id=show_id, error=str(exc))
        return {
            "show_id": show_id,
            "status": "failed",
            "error": str(exc),
            "progress": _result_cache_progress(show_id, doc=doc),
        }

    breeds_with_results = _result_breeds_with_results(show_detail_data.get("breeds", []))
    doc["title"] = show_detail_data.get("title", "")
    doc["source_url"] = show_detail_data.get("source_url") or _source_url(show_id)
    doc["total_breeds"] = len(breeds_with_results)
    doc["updated_at"] = time.time()
    if not preserve_existing_complete:
        _save_result_cache_doc(show_id, doc)

    completed_breeds = doc.setdefault("completed_breeds", {})
    doc.setdefault("failed_breeds", {})
    doc.setdefault("results", [])
    pending_breeds = [
        breed for breed in breeds_with_results
        if _breed_cache_key_from_breed(breed) not in completed_breeds
    ]
    failure = _crawl_missing_breed_results(
        show_id,
        pending_breeds,
        doc,
        delay=delay,
        workers=workers,
        preserve_existing_complete=preserve_existing_complete,
    )
    if failure:
        return failure

    cached_at = time.time()
    doc["status"] = "complete"
    doc["cached_at"] = cached_at
    doc["updated_at"] = cached_at
    doc["last_error"] = None
    _save_result_cache_doc(show_id, doc)

    response = _result_response_from_doc(show_id, doc)
    _show_all_results_cache[show_id] = {"data": response, "ts": cached_at}
    logger.info(
        "dog_result_cache_complete",
        show_id=show_id,
        breed_count=len(completed_breeds),
        result_count=len(doc.get("results", [])),
    )
    return {
        "show_id": show_id,
        "status": "complete",
        "progress": _result_cache_progress(show_id, doc=doc),
    }


def _queued_result_cache_candidates(now):
    jobs_doc = _load_result_jobs()
    candidates = []
    stale_complete_jobs = []
    for sid, job in sorted(
        jobs_doc.get("jobs", {}).items(),
        key=lambda item: item[1].get("requested_at") or item[1].get("created_at") or 0,
    ):
        try:
            show_id = int(sid)
        except (TypeError, ValueError):
            continue

        if not _result_cache_due(show_id, now=now):
            stale_complete_jobs.append(show_id)
            continue

        if _result_job_due(job, now=now):
            candidates.append({"show_id": show_id, "source": "queued", "job": job})

    for show_id in stale_complete_jobs:
        _remove_result_cache_job(show_id)
    return candidates


def _auto_result_cache_candidates(now):
    candidates = []
    try:
        shows_list = _get_show_list()
    except Exception:
        logger.warning("dog_result_cache_auto_show_list_failed", exc_info=True)
        return candidates

    today = datetime.datetime.fromtimestamp(now).date()
    for show in shows_list:
        show_id = int(show["id"])
        age_days = _show_age_days(show, today=today)
        if age_days is not None:
            if age_days < 0 or age_days > RESULT_AUTO_WINDOW_DAYS:
                continue
            recency_rank = age_days
        elif _is_recent_show(show.get("month")):
            recency_rank = RESULT_AUTO_WINDOW_DAYS + 1
        else:
            continue

        if not _result_cache_due(show_id, now=now):
            continue

        indexed_show = _indexed_show(show_id)
        indexed_breeds = indexed_show.get("breeds", []) if indexed_show else []
        if indexed_breeds and not _result_breeds_with_results(indexed_breeds):
            continue

        doc = _load_result_cache_doc(show_id)
        cache_rank = 0 if not doc else 1
        candidates.append({
            "show_id": show_id,
            "source": "auto",
            "job": None,
            "rank": (cache_rank, recency_rank, show_id),
        })

    candidates.sort(key=lambda item: item.get("rank", (99, 99, 0)))
    for candidate in candidates:
        candidate.pop("rank", None)
    return candidates


def crawl_result_cache_once(limit=1, delay=RESULT_CRAWL_DEFAULT_DELAY, auto_recent=True, workers=RESULT_CRAWL_DEFAULT_WORKERS):
    """Warm whole-show result caches without doing that work in web requests."""
    now = time.time()
    candidates = _queued_result_cache_candidates(now)
    queued_count = len(candidates)

    if auto_recent:
        queued_ids = {candidate["show_id"] for candidate in candidates}
        for candidate in _auto_result_cache_candidates(now):
            if candidate["show_id"] not in queued_ids:
                candidates.append(candidate)

    if limit is not None:
        candidates = candidates[:max(0, limit)]

    attempted = []
    completed = 0
    failed = 0
    skipped = 0

    for candidate in candidates:
        show_id = candidate["show_id"]
        source = candidate["source"]
        if source == "queued":
            _set_result_job_running(show_id)

        summary = crawl_result_cache_for_show(show_id, delay=delay, source=source, workers=workers)
        attempted.append(summary)

        if summary.get("status") == "complete":
            completed += 1
            _remove_result_cache_job(show_id)
        elif summary.get("status") == "skipped":
            skipped += 1
            _remove_result_cache_job(show_id)
        else:
            failed += 1
            if source == "queued":
                _defer_result_cache_job(show_id, summary.get("error") or summary.get("status"))

    return {
        "attempted": len(attempted),
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "queued_candidates": queued_count,
        "auto_recent": bool(auto_recent),
        "items": attempted,
    }


def _finish_immediate_warmup(show_id):
    with _immediate_warmups_lock:
        _immediate_warmups.discard(int(show_id))
    _immediate_warmup_slots.release()


def _run_immediate_result_cache_warmup(show_id):
    try:
        summary = crawl_result_cache_for_show(
            show_id,
            delay=RESULT_CRAWL_DEFAULT_DELAY,
            source="user-immediate",
            workers=RESULT_CRAWL_DEFAULT_WORKERS,
        )
        status = summary.get("status")
        if status in {"complete", "skipped"}:
            _remove_result_cache_job(show_id)
        else:
            _defer_result_cache_job(show_id, summary.get("error") or status)
    except Exception as exc:
        logger.exception("dog_immediate_result_warmup_failed", show_id=show_id)
        _defer_result_cache_job(show_id, exc)
    finally:
        _finish_immediate_warmup(show_id)


def _start_result_cache_warmup(show_id, reason="user-immediate"):
    if not RESULT_IMMEDIATE_WARMUP or not _result_cache_due(show_id):
        return False

    show_id = int(show_id)
    with _immediate_warmups_lock:
        if show_id in _immediate_warmups:
            return False
        _immediate_warmups.add(show_id)

    if not _immediate_warmup_slots.acquire(blocking=False):
        with _immediate_warmups_lock:
            _immediate_warmups.discard(show_id)
        return False

    claimed = _claim_result_cache_job(show_id, reason=reason)
    if not claimed:
        _finish_immediate_warmup(show_id)
        return False

    thread = threading.Thread(
        target=_run_immediate_result_cache_warmup,
        args=(show_id,),
        name=f"dog-result-warmup-{show_id}",
        daemon=True,
    )
    thread.start()
    return True


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
        return jsonify({
            "shows": _shows_with_cached_stats(shows),
            "index": _index_summary(total_show_count=len(shows)),
        })
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="shows", exc_info=True)
        if _show_list_cache["data"]:
            shows = _show_list_cache["data"]
            return jsonify({
                "shows": _shows_with_cached_stats(shows),
                "index": _index_summary(total_show_count=len(shows)),
            })
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


def _breed_list_targets_from_soup(soup, show_id):
    content = soup.find(id="divContent") or soup.find(id="content") or soup
    aggregate_targets = []
    group_targets = []

    for a in content.find_all("a"):
        href = a.get("href", "")
        r_match = re.search(r"(?:[?&]|&amp;)R=([^&#]+)", href)
        if not r_match:
            continue

        id_match = re.search(r"(?:[?&]|&amp;)Id=(\d+)", href)
        if id_match and str(id_match.group(1)) != str(show_id):
            continue

        group_value = r_match.group(1)
        if group_value.upper() == "R":
            aggregate_targets.append(group_value)
            continue

        if group_value.isdigit() and 1 <= int(group_value) <= 10:
            group_targets.append(group_value)

    # Some specialty shows expose every breed under R=R and keep BIS on the
    # landing page. Prefer the aggregate page to avoid duplicate group fetches.
    selected_targets = aggregate_targets or group_targets
    unique_targets = []
    seen = set()
    for target in selected_targets:
        if target in seen:
            continue
        seen.add(target)
        unique_targets.append(target)
    return unique_targets


def _parse_show_detail(soup, show_id):
    """Parse the show detail page: title and breed list."""
    title_el = soup.select_one("#divOtsikko h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # 1. Parse breeds on the landing page (for specialty shows)
    breeds = _parse_breeds_from_soup(soup, show_id)

    # 2. If no breeds found, look for breed-list links (R=R or FCI groups R=1..10)
    if not breeds:
        breed_list_targets = _breed_list_targets_from_soup(soup, show_id)

        if breed_list_targets:
            logger.info("dog_show_groups_found", show_id=show_id, groups=breed_list_targets)
            for target in breed_list_targets:
                url = f"{BASE_URL}?Id={show_id}&R={target}"
                try:
                    # Sleep 0.5s to be polite during nested crawls
                    time.sleep(0.5)
                    group_soup = _fetch_page(url)
                    group_breeds = _parse_breeds_from_soup(group_soup, show_id)
                    breeds.extend(group_breeds)
                except Exception as e:
                    logger.warning("dog_show_group_fetch_failed", show_id=show_id, group=target, error=str(e))

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

        indexed = _show_detail_from_index(show_id)
        if indexed:
            _show_detail_cache[show_id] = {"data": indexed, "ts": time.time()}
            return jsonify(indexed)

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

        try:
            _persist_show_detail_to_index(show_id, data, fetched_at)
        except Exception as e:
            logger.warning("dog_detail_index_persist_failed", show_id=show_id, error=str(e))

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

        persisted = _breed_results_from_all_results_cache(show_id, group, breed)
        if persisted:
            _breed_result_cache[cache_key] = {"data": persisted, "ts": now}
            return jsonify(persisted)

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
@limiter.limit("20/minute")
def show_all_results(show_id):
    try:
        cached = _cached_all_results_response(show_id, allow_stale=True)
        if cached:
            if cached.get("cache", {}).get("stale"):
                _queue_result_cache_job(show_id, reason="stale-refresh")
            return jsonify(cached)

        job = _queue_result_cache_job(show_id, reason="user")
        started = _start_result_cache_warmup(show_id, reason="user-immediate")
        doc = _load_result_cache_doc(show_id)
        if started:
            job = _load_result_jobs().get("jobs", {}).get(str(int(show_id)), job)
        return jsonify({
            "show_id": show_id,
            "status": "warming",
            "message": "Whole-show result cache is being prepared.",
            "retry_after": RESULT_RETRY_AFTER_SECONDS,
            "progress": _result_cache_progress(show_id, doc=doc, job=job),
            "started": started,
        }), 202
    except Exception as e:
        logger.exception("show_all_results_error", show_id=show_id)
        return jsonify({"error": "Failed to load show all results cache", "detail": str(e)}), 500


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
        enriched_shows = _shows_with_cached_stats(shows)
        results = []

        for show in enriched_shows:
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
            "index": _index_summary(total_show_count=len(enriched_shows)),
        })
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="search", exc_info=True)
        return jsonify({"error": "Failed to fetch show list for search", "detail": str(exc)}), 502
    except Exception:
        logger.exception("search_error")
        return jsonify({"error": "Internal server error"}), 500
