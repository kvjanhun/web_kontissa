import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog

from . import config
from .indexing import (
    _cached_show_detail, _indexed_result_flags_need_refresh, _is_show_recent_by_id,
    _mark_single_probe_breed_result_available, _persist_show_detail_to_index,
    _result_cache_doc_needs_result_refresh,
    _result_breeds_for_cache, _result_breeds_from_index, _result_breeds_with_results,
    _show_date_for_id, _show_expects_main_bis, _show_result_availability_for_id,
    _update_index_breed_judge, _update_index_breed_result_flag,
)
from .parsers import _parse_breed_results, _parse_show_detail
from .showlink import _fetch_page, _source_url
from .shows import _get_show_list
from .store import (
    _append_result_breed, _breed_result_cache, _claim_result_cache_job,
    _complete_result_cache_show_ids, _defer_result_cache_job,
    _heartbeat_result_cache_job, _indexed_show, _load_index, _load_result_cache_doc,
    _load_result_jobs, _remove_result_cache_job, _result_job_due, _queue_result_cache_job,
    _save_index, _save_result_cache_doc, _save_result_cache_header, _set_result_job_running,
    _show_all_results_cache, _show_detail_cache, _show_index,
)
from .utils import (
    _clean_all_results, _clean_breed_data, _clean_judge_name,
    _is_recent_show, _local_dt, _result_doc_has_main_bis, _result_doc_has_show_finals,
    _result_doc_live_bis_grace_finished,
    _result_doc_live_entry_completion_grace_finished, _show_age_days,
    _show_result_availability, _utc_iso,
)

logger = structlog.get_logger(__name__)

SHOW_ALL_RESULTS_TTL = config.SHOW_ALL_RESULTS_TTL
RESULT_CACHE_LIVE_TTL = config.RESULT_CACHE_LIVE_TTL
RESULT_CACHE_ACTIVE_TTL = config.RESULT_CACHE_ACTIVE_TTL
RESULT_CACHE_SETTLED_TTL = config.RESULT_CACHE_SETTLED_TTL
RESULT_CACHE_SETTLED_AFTER_DAYS = config.RESULT_CACHE_SETTLED_AFTER_DAYS
RESULT_AUTO_WINDOW_DAYS = config.RESULT_AUTO_WINDOW_DAYS
RESULT_CACHE_VERSION = config.RESULT_CACHE_VERSION
RESULT_RETRY_AFTER_SECONDS = config.RESULT_RETRY_AFTER_SECONDS
RESULT_CRAWL_DEFAULT_DELAY = config.RESULT_CRAWL_DEFAULT_DELAY
RESULT_CRAWL_DEFAULT_WORKERS = config.RESULT_CRAWL_DEFAULT_WORKERS
RESULT_LIVE_PROBE_BREED_LIMIT = config.RESULT_LIVE_PROBE_BREED_LIMIT
RESULT_FINALS_SWEEP_BREED_LIMIT = config.RESULT_FINALS_SWEEP_BREED_LIMIT
RESULT_LIVE_JOB_STALE_SECONDS = config.RESULT_LIVE_JOB_STALE_SECONDS
RESULT_IMMEDIATE_WARMUP = config.RESULT_IMMEDIATE_WARMUP_DEFAULT
RESULT_CACHE_BIS_FINAL_GRACE_SECONDS = config.RESULT_CACHE_BIS_FINAL_GRACE_SECONDS

_immediate_warmups = set()
_immediate_warmups_lock = threading.Lock()
_immediate_warmup_slots = threading.BoundedSemaphore(max(1, config.RESULT_IMMEDIATE_MAX_ACTIVE))

def _result_cache_doc_is_complete(doc):
    return bool(doc and doc.get("status") == "complete")

def _empty_result_cache_needs_refresh(show_id, doc, now=None):
    availability_now = datetime.datetime.fromtimestamp(now) if isinstance(now, (int, float)) else now
    return _result_cache_doc_needs_result_refresh(show_id, doc, now=availability_now)

def _availability_now(now):
    return datetime.datetime.fromtimestamp(now) if isinstance(now, (int, float)) else now

def _mark_live_bis_state(doc, now):
    if not isinstance(doc, dict) or not _result_doc_has_main_bis(doc):
        return

    detected_at = doc.get("bis_detected_at") or now
    doc["bis_detected_at"] = detected_at
    doc["bis_detected_at_iso"] = _utc_iso(detected_at)
    grace_until = detected_at + RESULT_CACHE_BIS_FINAL_GRACE_SECONDS
    doc["live_result_grace_until"] = grace_until
    doc["live_result_grace_until_iso"] = _utc_iso(grace_until)

def _entry_count_from_breeds(breeds):
    entry_count = 0
    entry_count_known = False
    for breed in breeds or []:
        try:
            entry_count += int(breed.get("count"))
            entry_count_known = True
        except (TypeError, ValueError):
            continue
    return entry_count if entry_count_known else None

def _clear_live_entry_completion_state(doc):
    for key in (
        "live_result_entry_count",
        "live_result_entry_completion_at",
        "live_result_entry_completion_at_iso",
        "live_result_entry_grace_until",
        "live_result_entry_grace_until_iso",
    ):
        doc.pop(key, None)

def _mark_live_entry_completion_state(doc, entry_count, now, existing=None):
    if not isinstance(doc, dict) or not isinstance(entry_count, int) or entry_count <= 0:
        return

    result_count = len(doc.get("results") or [])
    if result_count < entry_count:
        _clear_live_entry_completion_state(doc)
        return

    detected_at = doc.get("live_result_entry_completion_at")
    if not detected_at and isinstance(existing, dict):
        try:
            existing_result_count = len(existing.get("results") or [])
        except TypeError:
            existing_result_count = 0
        if existing_result_count >= entry_count:
            detected_at = (
                existing.get("live_result_entry_completion_at")
                or existing.get("cached_at")
                or existing.get("updated_at")
            )

    detected_at = detected_at or now
    grace_until = detected_at + RESULT_CACHE_BIS_FINAL_GRACE_SECONDS
    doc["live_result_entry_count"] = entry_count
    doc["live_result_entry_completion_at"] = detected_at
    doc["live_result_entry_completion_at_iso"] = _utc_iso(detected_at)
    doc["live_result_entry_grace_until"] = grace_until
    doc["live_result_entry_grace_until_iso"] = _utc_iso(grace_until)

def _post_show_final_due_at(show_id, now):
    show_date = _show_date_for_id(show_id)
    if not show_date:
        return None

    now_dt = _availability_now(now)
    today = now_dt.date()
    if today != show_date + datetime.timedelta(days=1):
        return None

    final_due = datetime.datetime.combine(show_date + datetime.timedelta(days=1), datetime.time.min)
    return final_due.timestamp()

def _result_cache_doc_needs_post_show_final_refresh(show_id, doc, now):
    final_due_at = _post_show_final_due_at(show_id, now)
    if not final_due_at:
        return False

    cached_at = (doc or {}).get("cached_at") or (doc or {}).get("updated_at") or 0
    return cached_at < final_due_at

def _result_cache_ttl_for_show(show_id, now, doc=None):
    availability = _show_result_availability_for_id(show_id, now=_availability_now(now))
    if availability.get("show_state") == "live":
        entry_count = _entry_count_from_breeds(_result_breeds_from_index(show_id))
        if _result_doc_live_bis_grace_finished(doc, now):
            return None
        if _result_doc_live_entry_completion_grace_finished(doc, now, entry_count=entry_count):
            # Every breed ring is judged, but all-breed shows decide the group
            # finals and main Best in Show afterwards. Keep polling until BIS-1
            # is captured instead of freezing the cache right before the finals
            # publish RYP/BIS placements onto the winners' breed rows.
            if not _result_doc_has_main_bis(doc) and _show_expects_main_bis(show_id, doc):
                return RESULT_CACHE_LIVE_TTL
            return None
        return RESULT_CACHE_LIVE_TTL

    show_date = _show_date_for_id(show_id)
    if show_date:
        if _result_cache_doc_needs_post_show_final_refresh(show_id, doc, now):
            return 0
        today = datetime.datetime.fromtimestamp(now).date()
        age_days = (today - show_date).days
        if age_days > RESULT_AUTO_WINDOW_DAYS:
            return None
        return RESULT_CACHE_SETTLED_TTL

    return SHOW_ALL_RESULTS_TTL

def _live_index_result_flags_need_refresh(show_id, indexed_show=None, now=None):
    indexed_show = indexed_show or _indexed_show(show_id)
    if not indexed_show or not indexed_show.get("breeds"):
        return False

    now = now or time.time()
    availability = _show_result_availability_for_id(show_id, now=_availability_now(now))
    if availability.get("show_state") != "live":
        return False

    updated = indexed_show.get("updated_at") or _show_index.get("last_updated") or 0
    return not updated or (now - updated) >= RESULT_CACHE_LIVE_TTL

def _result_job_stale_seconds_for_show(show_id, now=None):
    availability = _show_result_availability_for_id(show_id, now=_availability_now(now or time.time()))
    if availability.get("show_state") == "live" and availability.get("can_fetch", True):
        return RESULT_LIVE_JOB_STALE_SECONDS
    return None

def _result_cache_doc_is_fresh(show_id, doc, now=None):
    if not _result_cache_doc_is_complete(doc):
        return False

    if _empty_result_cache_needs_refresh(show_id, doc, now=now):
        return False

    cached_at = doc.get("cached_at") or doc.get("updated_at") or 0
    if not cached_at:
        return False

    now = now or time.time()
    if not _is_show_recent_by_id(show_id):
        return True

    ttl = _result_cache_ttl_for_show(show_id, now, doc=doc)
    if ttl is None:
        return True
    return (now - cached_at) < ttl

def _cached_all_results_doc(cached):
    cached_data = cached.get("data") or {}
    cache_meta = cached_data.get("cache") or {}
    cached_at = cache_meta.get("cached_at") or cached.get("ts")
    return {
        "status": "complete",
        "total_breeds": cache_meta.get("total_breeds"),
        "completed_breeds": {},
        "results": cached_data.get("results") or [],
        "cached_at": cached_at,
        "updated_at": cached_at,
    }

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
        total_breeds = len(_result_breeds_for_cache(show_id, _result_breeds_from_index(show_id)))
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
        "results": _clean_all_results(doc.get("results") or []),
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
        cached_data = cached["data"]
        cached_doc = _cached_all_results_doc(cached)
        if _empty_result_cache_needs_refresh(show_id, cached_doc, now=now):
            _show_all_results_cache.pop(int(show_id), None)
        else:
            stale = not _result_cache_doc_is_fresh(show_id, cached_doc, now=now)
            if stale:
                _show_all_results_cache.pop(int(show_id), None)
            else:
                data = dict(cached_data)
                if data.get("cache"):
                    data["cache"] = dict(data["cache"])
                    data["cache"]["status"] = "complete"
                    data["cache"]["stale"] = False
                return data

    doc = _load_result_cache_doc(show_id)
    if not _result_cache_doc_is_complete(doc):
        return None

    if _empty_result_cache_needs_refresh(show_id, doc, now=now):
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
    breed_obj = _clean_breed_data(breed_obj or {})
    if breed_obj.get("judge") and _update_index_breed_judge(show_id, group, breed, breed_obj.get("judge")):
        _save_index()

    fetched_at = doc.get("cached_at") or doc.get("updated_at") or time.time()
    breed_completed = (doc.get("completed_breeds") or {}).get(f"{group}:{breed}") or {}
    return {
        "show_id": int(show_id),
        "title": doc.get("title", ""),
        "breed": breed_obj.get("name", ""),
        "judge": breed_obj.get("judge", ""),
        "awards": breed_completed.get("awards") or [],
        "results": [
            {
                "number": dog.get("number"),
                "name": dog.get("name"),
                "reg_url": dog.get("reg_url"),
                "grade": dog.get("grade"),
                "placement": dog.get("placement"),
                "competitive_placement": dog.get("competitive_placement"),
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

def _show_detail_for_result_cache(show_id):
    indexed_show = _indexed_show(show_id)
    now = time.time()
    indexed_needs_result_refresh = (
        _indexed_result_flags_need_refresh(show_id, indexed_show)
        or _live_index_result_flags_need_refresh(show_id, indexed_show, now=now)
    )
    if indexed_show and indexed_show.get("breeds"):
        if not indexed_needs_result_refresh:
            breeds = _mark_single_probe_breed_result_available(show_id, indexed_show.get("breeds", []))
            return {
                "id": int(show_id),
                "title": indexed_show.get("title") or indexed_show.get("name", ""),
                "source_url": indexed_show.get("source_url") or _source_url(show_id),
                "breeds": breeds,
            }

    cached = _cached_show_detail(show_id, allow_stale=True)
    if cached and cached.get("breeds"):
        cached_breeds = cached.get("breeds") or []
        if not indexed_needs_result_refresh:
            detail = dict(cached)
            detail["breeds"] = _mark_single_probe_breed_result_available(show_id, cached_breeds)
            return detail

    soup = _fetch_page(_source_url(show_id))
    detail = _parse_show_detail(soup, show_id)
    fetched_at = time.time()
    detail["fetched_at"] = fetched_at
    detail["fetched_at_iso"] = _utc_iso(fetched_at)
    detail["breeds"] = _mark_single_probe_breed_result_available(show_id, detail.get("breeds", []))
    try:
        _persist_show_detail_to_index(show_id, detail, fetched_at)
    except Exception as exc:
        logger.warning("dog_result_cache_detail_index_persist_failed", show_id=show_id, error=str(exc))
    _show_detail_cache[int(show_id)] = {"data": detail, "ts": fetched_at}
    return detail

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
        # Shallow-copy the mutable carry-overs so crawling this doc never mutates
        # the source `existing` in place — `_mark_live_entry_completion_state`
        # reads existing["results"] after the crawl to preserve the original
        # entry-completion time, which a shared (already-extended) list would skew.
        "completed_breeds": dict(existing.get("completed_breeds") or {}),
        "failed_breeds": dict(existing.get("failed_breeds") or {}),
        "results": list(existing.get("results") or []),
        "bis_detected_at": existing.get("bis_detected_at"),
        "bis_detected_at_iso": existing.get("bis_detected_at_iso"),
        "live_result_grace_until": existing.get("live_result_grace_until"),
        "live_result_grace_until_iso": existing.get("live_result_grace_until_iso"),
        "live_result_entry_count": existing.get("live_result_entry_count"),
        "live_result_entry_completion_at": existing.get("live_result_entry_completion_at"),
        "live_result_entry_completion_at_iso": existing.get("live_result_entry_completion_at_iso"),
        "live_result_entry_grace_until": existing.get("live_result_entry_grace_until"),
        "live_result_entry_grace_until_iso": existing.get("live_result_entry_grace_until_iso"),
        "live_probe_cursor": existing.get("live_probe_cursor", 0),
        "live_probe_breed_count": existing.get("live_probe_breed_count"),
        "live_probe_breed_limit": existing.get("live_probe_breed_limit"),
        "finals_sweep_cursor": existing.get("finals_sweep_cursor", 0),
        "finals_sweep_breed_count": existing.get("finals_sweep_breed_count"),
        "finals_sweep_breed_limit": existing.get("finals_sweep_breed_limit"),
    }

def _breed_result_cache_key(show_id, group, breed_id):
    return (int(show_id), str(group), str(breed_id))

def _map_breed_results_to_all_results(show_id, breed, breed_data):
    group = str(breed.get("group", ""))
    breed_id = str(breed.get("breed_id", ""))
    breed_obj = _clean_breed_data(breed)
    if breed_data.get("judge"):
        breed_obj["judge"] = _clean_judge_name(breed_data.get("judge"))

    mapped = []
    for dog in breed_data.get("results", []):
        mapped.append({
            "number": dog.get("number"),
            "name": dog.get("name"),
            "reg_url": dog.get("reg_url"),
            "grade": dog.get("grade"),
            "placement": dog.get("placement"),
            "competitive_placement": dog.get("competitive_placement"),
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

def _live_probe_cursor(doc):
    try:
        return max(0, int((doc or {}).get("live_probe_cursor") or 0))
    except (TypeError, ValueError):
        return 0

def _live_unchecked_probe_breeds(breeds, selected_breeds, doc, limit=None):
    if limit is None:
        limit = RESULT_LIVE_PROBE_BREED_LIMIT
    limit = max(0, int(limit or 0))
    if limit <= 0:
        return []

    selected_keys = {_breed_cache_key_from_breed(breed) for breed in selected_breeds or []}
    candidates = []
    seen = set(selected_keys)
    for breed in breeds or []:
        if not breed.get("group") or not breed.get("breed_id") or breed.get("has_results"):
            continue

        key = _breed_cache_key_from_breed(breed)
        if key in seen:
            continue

        seen.add(key)
        candidates.append(breed)

    doc["live_probe_breed_count"] = len(candidates)
    doc["live_probe_breed_limit"] = limit
    if not candidates:
        doc["live_probe_cursor"] = 0
        return []

    cursor = _live_probe_cursor(doc) % len(candidates)
    selected = []
    for offset in range(min(limit, len(candidates))):
        selected.append(candidates[(cursor + offset) % len(candidates)])

    doc["live_probe_cursor"] = (cursor + len(selected)) % len(candidates)
    doc["live_probe_selected_breeds"] = [_breed_cache_key_from_breed(breed) for breed in selected]
    return selected

def _result_breeds_for_live_cache(show_id, breeds, doc, availability, now=None):
    selected = _result_breeds_for_cache(show_id, breeds, now=_availability_now(now) if now else None)
    if availability.get("show_state") != "live" or not availability.get("can_fetch", True):
        return selected

    probes = _live_unchecked_probe_breeds(breeds, selected, doc)
    if not probes:
        return selected
    return selected + probes

def _finals_resweep_breeds(breeds, completed_breeds, doc, limit=None):
    """A bounded, rotating slice of already-captured breeds to re-fetch for finals.

    All-breed shows append RYP/BIS placements onto the winning breeds' rows after
    every ring is judged, so those rows do change once — unlike the rest, which are
    immutable after capture. Rather than re-crawl the whole show on every live pass,
    re-check a small rotating chunk (cycling via `finals_sweep_cursor`) so the
    finals land within a few passes without a burst. The caller only invokes this
    once a main BIS is expected and still missing, so the sweep stops as soon as
    BIS-1 is captured."""
    if limit is None:
        limit = RESULT_FINALS_SWEEP_BREED_LIMIT
    limit = max(0, int(limit or 0))
    if limit <= 0:
        return []

    candidates = [
        breed for breed in breeds or []
        if breed.get("group") and breed.get("breed_id")
        and _breed_cache_key_from_breed(breed) in completed_breeds
    ]
    doc["finals_sweep_breed_count"] = len(candidates)
    doc["finals_sweep_breed_limit"] = limit
    if not candidates:
        doc["finals_sweep_cursor"] = 0
        return []

    try:
        cursor = max(0, int(doc.get("finals_sweep_cursor") or 0)) % len(candidates)
    except (TypeError, ValueError):
        cursor = 0
    selected = [
        candidates[(cursor + offset) % len(candidates)]
        for offset in range(min(limit, len(candidates)))
    ]
    doc["finals_sweep_cursor"] = (cursor + len(selected)) % len(candidates)
    return selected

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _result_cache_breed_progress_map(show_id, doc=None):
    doc = doc if isinstance(doc, dict) else _load_result_cache_doc(show_id)
    if not isinstance(doc, dict):
        return {}

    progress = {}
    completed_breeds = doc.get("completed_breeds") or {}
    for key, breed_data in completed_breeds.items():
        if not isinstance(breed_data, dict) or ":" not in str(key):
            continue

        result_count = _safe_int(breed_data.get("result_count"))
        updated_at = breed_data.get("updated_at") or doc.get("updated_at") or doc.get("cached_at")
        progress[str(key)] = {
            "result_count": max(0, result_count or 0),
            "updated_at": updated_at,
            "updated_at_iso": _utc_iso(updated_at),
        }

    # Older or partially-written cache docs may have result rows before a
    # matching completed_breeds entry. Count them as a best-effort fallback.
    counted_results = {}
    for result in doc.get("results") or []:
        group = result.get("breedGroup") or (result.get("breedObj") or {}).get("group")
        breed_id = result.get("breedId") or (result.get("breedObj") or {}).get("breed_id")
        if not group or not breed_id:
            continue
        key = f"{group}:{breed_id}"
        counted_results[key] = counted_results.get(key, 0) + 1

    doc_updated_at = doc.get("updated_at") or doc.get("cached_at")
    for key, count in counted_results.items():
        if key in progress:
            progress[key]["result_count"] = max(progress[key]["result_count"], count)
            continue
        progress[key] = {
            "result_count": count,
            "updated_at": doc_updated_at,
            "updated_at_iso": _utc_iso(doc_updated_at),
        }

    return progress

def _enrich_breeds_with_result_progress(show_id, breeds, doc=None):
    progress_by_key = _result_cache_breed_progress_map(show_id, doc=doc)
    if not progress_by_key:
        return False

    updated = False
    for breed in breeds or []:
        group = breed.get("group")
        breed_id = breed.get("breed_id")
        if not group or not breed_id:
            continue

        progress = progress_by_key.get(f"{group}:{breed_id}")
        if not progress:
            continue

        total_count = _safe_int(breed.get("count"))
        result_count = progress["result_count"]
        if total_count is not None:
            result_count = min(result_count, max(0, total_count))

        breed["result_count"] = result_count
        breed["result_total_count"] = total_count
        breed["result_updated_at"] = progress.get("updated_at")
        breed["result_updated_at_iso"] = progress.get("updated_at_iso")
        breed["result_progress"] = {
            "rated_count": result_count,
            "total_count": total_count,
            "updated_at": progress.get("updated_at"),
            "updated_at_iso": progress.get("updated_at_iso"),
        }
        if result_count > 0:
            breed["has_results"] = True
        updated = True

    return updated

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
    """Header-only progress save (status / completed / failed breeds / live meta).

    Used where no new result rows were produced (breed failure, detail-fetch
    failure, bounded pause). The success path appends the breed's rows via
    _append_result_breed instead of rewriting the whole show."""
    if not preserve_existing_complete:
        _save_result_cache_header(show_id, doc)

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
    judge = _clean_judge_name(item["breed_data"].get("judge"))

    _breed_result_cache[_breed_result_cache_key(show_id, group, breed_id)] = {
        "data": item["breed_data"],
        "ts": fetched_at,
    }

    result_count = len(mapped_results)
    if result_count:
        breed["has_results"] = True

    # A finals re-sweep re-fetches an already-captured breed; drop its old rows so
    # the refreshed rows (now carrying RYP/BIS) replace them instead of duplicating.
    # New breeds aren't in completed_breeds yet, so this is a no-op for them.
    if item["breed_key"] in doc.get("completed_breeds", {}):
        doc["results"] = [
            row for row in doc.get("results", [])
            if not (str(row.get("breedGroup")) == group and str(row.get("breedId")) == breed_id)
        ]

    doc.setdefault("results", []).extend(mapped_results)
    completed_entry = {
        "name": breed.get("name", ""),
        "result_count": result_count,
        "judge": judge,
        "updated_at": fetched_at,
        "updated_at_iso": _utc_iso(fetched_at),
    }
    honor_roll = item["breed_data"].get("awards") or []
    if honor_roll:
        completed_entry["awards"] = honor_roll
    doc.setdefault("completed_breeds", {})[item["breed_key"]] = completed_entry
    doc.setdefault("failed_breeds", {}).pop(item["breed_key"], None)
    doc["updated_at"] = fetched_at
    if not preserve_existing_complete:
        _append_result_breed(show_id, doc, group, breed_id, mapped_results)
    _heartbeat_result_cache_job(show_id)
    updated_index = False
    if result_count and _update_index_breed_result_flag(show_id, group, breed_id):
        updated_index = True
    if judge and _update_index_breed_judge(show_id, group, breed_id, judge):
        updated_index = True
    if updated_index:
        _save_index()

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

def crawl_result_cache_for_show(show_id, delay=RESULT_CRAWL_DEFAULT_DELAY, force=False, source="manual", workers=RESULT_CRAWL_DEFAULT_WORKERS, max_breeds=None):
    """Build or resume the persisted whole-show results cache for one show.

    max_breeds caps how many not-yet-fetched breeds this call crawls before
    returning status="incomplete" (the show stays resumable, not marked complete).
    Used by the bounded off-peak backfill so a 200+ breed show is captured across
    several passes instead of holding the crawler loop for one long crawl. None =
    crawl all pending breeds in one call (the default for live/auto/queued work)."""
    show_id = int(show_id)
    now = time.time()
    availability = _show_result_availability_for_id(
        show_id,
        now=datetime.datetime.fromtimestamp(now),
    )
    if not force and not availability.get("can_fetch", True):
        logger.info(
            "dog_result_cache_skipped",
            show_id=show_id,
            source=source,
            reason=availability.get("reason"),
        )
        return {
            "show_id": show_id,
            "status": "skipped",
            "reason": availability.get("reason"),
            "availability": availability,
            "progress": _result_cache_progress(show_id),
        }

    existing = _load_result_cache_doc(show_id)
    if not force and _result_cache_doc_is_fresh(show_id, existing, now=now):
        progress = _result_cache_progress(show_id, doc=existing)
        logger.info(
            "dog_result_cache_skipped",
            show_id=show_id,
            source=source,
            reason="fresh",
            total_breeds=progress["total_breeds"],
            fetched_breeds=progress["fetched_breeds"],
            total_dogs=progress["total_dogs"],
        )
        return {
            "show_id": show_id,
            "status": "skipped",
            "reason": "fresh",
            "progress": progress,
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
    # Seed from the existing doc on a live refresh of a complete cache too, not
    # only on resume. Captured breed results are immutable, so carrying over
    # completed_breeds/results means this pass fetches only newly-judged breeds
    # (plus the bounded probe / finals re-sweep) instead of re-crawling the whole
    # show. force=True still rebuilds from empty (a deliberate full re-crawl).
    seed_from_existing = resumable or preserve_existing_complete
    doc = _all_results_doc_base(show_id, source, existing=existing if seed_from_existing else None)
    if isinstance(existing, dict):
        for key in (
            "bis_detected_at",
            "bis_detected_at_iso",
            "live_result_grace_until",
            "live_result_grace_until_iso",
            "live_result_entry_count",
            "live_result_entry_completion_at",
            "live_result_entry_completion_at_iso",
            "live_result_entry_grace_until",
            "live_result_entry_grace_until_iso",
            "live_probe_cursor",
            "live_probe_breed_count",
            "live_probe_breed_limit",
            "finals_sweep_cursor",
            "finals_sweep_breed_count",
            "finals_sweep_breed_limit",
        ):
            if existing.get(key):
                doc[key] = existing.get(key)
    # A complete cache we're refreshing in place stays "complete" throughout, so an
    # interrupted refresh never demotes a good cache to "running"; we only add rows.
    if preserve_existing_complete:
        doc["status"] = "complete"
    if not preserve_existing_complete:
        if resumable:
            # Already-completed breeds' rows are persisted; just refresh the header
            # so a resume pass doesn't rewrite the whole accumulated result set.
            _save_result_cache_header(show_id, doc)
        else:
            # Fresh crawl: clear any stale partial rows, write the empty baseline.
            _save_result_cache_doc(show_id, doc)

    try:
        show_detail_data = _show_detail_for_result_cache(show_id)
    except Exception as exc:
        doc["status"] = "failed"
        doc["last_error"] = str(exc)
        doc["updated_at"] = time.time()
        if not preserve_existing_complete:
            _save_result_cache_header(show_id, doc)
        logger.warning("dog_result_cache_detail_failed", show_id=show_id, source=source, error=str(exc))
        return {
            "show_id": show_id,
            "status": "failed",
            "error": str(exc),
            "progress": _result_cache_progress(show_id, doc=doc),
        }

    breeds_with_results = _result_breeds_for_live_cache(
        show_id,
        show_detail_data.get("breeds", []),
        doc,
        availability,
        now=now,
    )
    doc["title"] = show_detail_data.get("title", "")
    doc["source_url"] = show_detail_data.get("source_url") or _source_url(show_id)
    doc["total_breeds"] = len(breeds_with_results)
    doc["updated_at"] = time.time()
    if not preserve_existing_complete:
        _save_result_cache_header(show_id, doc)

    completed_breeds = doc.setdefault("completed_breeds", {})
    doc.setdefault("failed_breeds", {})
    doc.setdefault("results", [])
    pending_breeds = [
        breed for breed in breeds_with_results
        if _breed_cache_key_from_breed(breed) not in completed_breeds
    ]

    # Finals re-sweep: when every newly-judged breed is already captured but the
    # show still owes a main BIS (BIS-1 not recorded yet), re-check a bounded
    # rotating chunk of captured breeds so the RYP/BIS placements appended to the
    # winners' rows land — instead of re-crawling the whole show on every pass.
    # Fires while live, and once on the post-show morning check (to catch a BIS-1
    # published after the evening cutoff, which the live sweep can't see overnight).
    new_result_breeds = [
        breed for breed in breeds_with_results
        if breed.get("has_results")
        and _breed_cache_key_from_breed(breed) not in completed_breeds
    ]
    finals_due_window = (
        (availability.get("show_state") == "live" and availability.get("can_fetch", True))
        or _result_cache_doc_needs_post_show_final_refresh(show_id, doc, now)
    )
    finals_resweep = 0
    if (
        not new_result_breeds
        and finals_due_window
        and _show_expects_main_bis(show_id, doc)
        and not _result_doc_has_main_bis(doc)
    ):
        resweep_breeds = _finals_resweep_breeds(breeds_with_results, completed_breeds, doc)
        pending_breeds = pending_breeds + resweep_breeds
        finals_resweep = len(resweep_breeds)

    # Bounded pass: crawl at most max_breeds this call; the rest resume next pass.
    pending_before_budget = len(pending_breeds)
    bounded_incomplete = (
        max_breeds is not None and 0 <= max_breeds < pending_before_budget
    )
    if bounded_incomplete:
        pending_breeds = pending_breeds[:max_breeds]
    logger.info(
        "dog_result_cache_crawl_start",
        show_id=show_id,
        source=source,
        force=force,
        resumable=resumable,
        preserve_existing_complete=preserve_existing_complete,
        total_breeds=len(breeds_with_results),
        completed_breeds=len(completed_breeds),
        pending_breeds=len(pending_breeds),
        finals_resweep=finals_resweep,
        max_breeds=max_breeds,
        workers=max(1, int(workers or 1)),
        delay=delay,
    )
    failure = _crawl_missing_breed_results(
        show_id,
        pending_breeds,
        doc,
        delay=delay,
        workers=workers,
        preserve_existing_complete=preserve_existing_complete,
    )
    if failure:
        failure["crawled_breeds"] = len(pending_breeds)
        return failure

    if bounded_incomplete:
        # Budget reached with breeds still pending: persist progress (the crawled
        # breeds' rows were appended incrementally) and resume on the next pass.
        # The show is NOT marked complete, so it stays a backfill candidate.
        doc["updated_at"] = time.time()
        if not preserve_existing_complete:
            _save_result_cache_header(show_id, doc)
        logger.info(
            "dog_result_cache_bounded_pause",
            show_id=show_id,
            source=source,
            max_breeds=max_breeds,
            crawled_breeds=len(pending_breeds),
            pending_remaining=pending_before_budget - len(pending_breeds),
            completed_breeds=len(doc.get("completed_breeds", {})),
            total_breeds=len(breeds_with_results),
        )
        return {
            "show_id": show_id,
            "status": "incomplete",
            "crawled_breeds": len(pending_breeds),
            "progress": _result_cache_progress(show_id, doc=doc),
        }

    cached_at = time.time()
    _mark_live_entry_completion_state(
        doc,
        _entry_count_from_breeds(show_detail_data.get("breeds", [])),
        cached_at,
        existing=existing,
    )
    _mark_live_bis_state(doc, cached_at)
    doc["status"] = "complete"
    doc["cached_at"] = cached_at
    doc["updated_at"] = cached_at
    doc["last_error"] = None
    if preserve_existing_complete and not pending_breeds:
        # Live refresh that fetched nothing new: the complete result rows are
        # already on disk, so only refresh the header/meta (cached_at, live-state
        # blob). Avoids rewriting ~thousands of rows every couple of minutes.
        _save_result_cache_header(show_id, doc)
    else:
        _save_result_cache_doc(show_id, doc)

    response = _result_response_from_doc(show_id, doc)
    _show_all_results_cache[show_id] = {"data": response, "ts": cached_at}
    logger.info(
        "dog_result_cache_complete",
        show_id=show_id,
        source=source,
        breed_count=len(completed_breeds),
        result_count=len(doc.get("results", [])),
    )
    return {
        "show_id": show_id,
        "status": "complete",
        "crawled_breeds": len(pending_breeds),
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

        if _result_job_due(
            job,
            now=now,
            stale_seconds=_result_job_stale_seconds_for_show(show_id, now=now),
        ):
            candidates.append({"show_id": show_id, "source": "queued", "job": job})

    for show_id in stale_complete_jobs:
        _remove_result_cache_job(show_id)
    if stale_complete_jobs:
        logger.info(
            "dog_result_cache_removed_fresh_jobs",
            count=len(stale_complete_jobs),
            show_ids=stale_complete_jobs,
        )
    return candidates

def _auto_result_cache_candidates(now):
    candidates = []
    try:
        shows_list = _get_show_list()
    except Exception:
        logger.warning("dog_result_cache_auto_show_list_failed", exc_info=True)
        return candidates

    today = datetime.datetime.fromtimestamp(now).date()
    now_dt = datetime.datetime.fromtimestamp(now)
    for show in shows_list:
        show_id = int(show["id"])
        availability = _show_result_availability(show, now=now_dt)
        if not availability.get("can_fetch", True):
            continue

        if availability.get("show_state") == "live":
            recency_rank = -1
        else:
            age_days = _show_age_days(show, today=today)
            if age_days is None:
                if _is_recent_show(show.get("month")):
                    recency_rank = RESULT_AUTO_WINDOW_DAYS + 1
                else:
                    continue
            elif age_days < 0 or age_days > RESULT_AUTO_WINDOW_DAYS:
                continue
            else:
                recency_rank = age_days

        if not _result_cache_due(show_id, now=now):
            continue

        indexed_show = _indexed_show(show_id)
        indexed_breeds = indexed_show.get("breeds", []) if indexed_show else []
        if (
            indexed_breeds
            and not _result_breeds_for_cache(show_id, indexed_breeds)
            and not _indexed_result_flags_need_refresh(show_id, indexed_show)
        ):
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

def _queue_live_result_cache_refresh(show_id, show=None, reason="live-detail-refresh", immediate=True, now=None):
    now = now or time.time()
    availability = (
        _show_result_availability(show, now=_availability_now(now))
        if show
        else _show_result_availability_for_id(show_id, now=_availability_now(now))
    )
    if availability.get("show_state") != "live" or not availability.get("can_fetch", True):
        return None

    show_id = int(show_id)
    if not _result_cache_due(show_id, now=now):
        return None

    job = _queue_result_cache_job(show_id, reason=reason)
    started = _start_result_cache_warmup(show_id, reason=reason) if immediate else False
    queued = {
        "show_id": show_id,
        "started": started,
        "job_state": job.get("state"),
    }
    return queued

def _queue_live_result_cache_refreshes(shows, limit=2, immediate=True):
    now = time.time()
    queued = []
    for show in shows or []:
        if len(queued) >= max(0, int(limit or 0)):
            break

        try:
            show_id = int(show.get("id"))
        except (TypeError, ValueError, AttributeError):
            continue

        item = _queue_live_result_cache_refresh(
            show_id,
            show=show,
            reason="live-list-refresh",
            immediate=immediate,
            now=now,
        )
        if item:
            queued.append(item)

    if queued:
        logger.info("dog_live_result_refresh_queued", count=len(queued), shows=queued)
    return queued

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

    candidate_count = len(candidates)
    if limit is not None:
        candidates = candidates[:max(0, limit)]

    logger.info(
        "dog_result_cache_pass_start",
        selected=len(candidates),
        candidates=candidate_count,
        queued_candidates=queued_count,
        auto_recent=bool(auto_recent),
        limit=limit,
        workers=max(1, int(workers or 1)),
        delay=delay,
        show_ids=[candidate["show_id"] for candidate in candidates],
    )

    attempted = []
    completed = 0
    failed = 0
    skipped = 0

    for candidate in candidates:
        show_id = candidate["show_id"]
        source = candidate["source"]
        if source == "queued":
            _set_result_job_running(show_id)

        logger.info("dog_result_cache_job_start", show_id=show_id, source=source)
        summary = crawl_result_cache_for_show(show_id, delay=delay, source=source, workers=workers)
        attempted.append(summary)
        logger.info(
            "dog_result_cache_job_complete",
            show_id=show_id,
            source=source,
            status=summary.get("status"),
            reason=summary.get("reason"),
            error=summary.get("error"),
        )

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

    pass_summary = {
        "attempted": len(attempted),
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "queued_candidates": queued_count,
        "auto_recent": bool(auto_recent),
        "items": attempted,
    }
    logger.info(
        "dog_result_cache_pass_complete",
        attempted=pass_summary["attempted"],
        completed=completed,
        failed=failed,
        skipped=skipped,
        queued_candidates=queued_count,
        auto_recent=bool(auto_recent),
    )
    return pass_summary

def _within_backfill_window(now=None, start_hour=None, end_hour=None):
    """True when the Finnish local hour is inside the off-peak backfill window.

    Supports windows that wrap midnight (e.g. start 22, end 6)."""
    start_hour = config.BACKFILL_START_HOUR if start_hour is None else start_hour
    end_hour = config.BACKFILL_END_HOUR if end_hour is None else end_hour
    hour = _local_dt(now if now is not None else time.time()).hour
    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def _has_pending_result_jobs():
    """Any user/live result job queued or running — backfill yields to those."""
    jobs = _load_result_jobs().get("jobs", {})
    return any(job.get("state") in ("queued", "running") for job in jobs.values())


def _backfill_candidates(now, limit=1):
    """Oldest not-yet-captured shows that have result-bearing breeds.

    Oldest-first races Showlink's rolling window so the most at-risk history is
    secured first. A show is "captured" once it has a complete result cache; that
    is permanent and never re-crawled."""
    _load_index()
    # One status-column scan instead of fully reconstructing each complete doc
    # (all result rows + a breed-lookup join) just to read its status string.
    captured = _complete_result_cache_show_ids()
    candidates = []
    for sid_str, show in (_show_index.get("shows") or {}).items():
        if not _result_breeds_with_results(show.get("breeds") or []):
            continue  # no result pages to fetch (future show / no results)
        try:
            sid = int(sid_str)
        except (TypeError, ValueError):
            continue
        if sid in captured:
            continue  # already permanently captured
        show_date = _show_date_for_id(sid)
        candidates.append((show_date or datetime.date.max, sid))

    candidates.sort(key=lambda item: (item[0], item[1]))  # oldest date, then id
    limit = len(candidates) if limit is None else max(0, limit)
    return [sid for _, sid in candidates[:limit]]


def crawl_backfill_once(limit=None, delay=None, workers=None, now=None, force_window=False, breed_budget=None):
    """One polite, off-peak backfill step: capture full results for the oldest
    not-yet-captured show(s). Yields outside the window and while user/live result
    jobs are pending. Single worker + deliberate delay keep it non-bursty.

    breed_budget caps total breeds crawled this pass across all selected shows; a
    show larger than the remaining budget is crawled partially (status="incomplete")
    and resumes next pass, so one 200+ breed show never holds the loop for minutes.
    None disables the cap (whole shows per pass)."""
    now = now or time.time()
    limit = config.BACKFILL_SHOW_LIMIT if limit is None else limit
    delay = config.BACKFILL_DELAY if delay is None else delay
    workers = config.BACKFILL_WORKERS if workers is None else workers
    breed_budget = config.BACKFILL_BREED_BUDGET if breed_budget is None else breed_budget

    if not force_window and not _within_backfill_window(now):
        logger.info("dog_backfill_skipped", reason="outside_window")
        return {"status": "skipped", "reason": "outside_window", "attempted": 0}

    if _has_pending_result_jobs():
        logger.info("dog_backfill_skipped", reason="jobs_pending")
        return {"status": "skipped", "reason": "jobs_pending", "attempted": 0}

    candidates = _backfill_candidates(now, limit=limit)
    if not candidates:
        logger.info("dog_backfill_idle", reason="nothing_to_backfill")
        return {"status": "idle", "reason": "nothing_to_backfill", "attempted": 0}

    logger.info(
        "dog_backfill_pass_start",
        show_ids=candidates,
        delay=delay,
        workers=max(1, int(workers or 1)),
        limit=limit,
        breed_budget=breed_budget,
    )

    attempted = []
    completed = 0
    failed = 0
    in_progress = 0
    # None = unbounded; otherwise breeds we may still crawl this pass.
    remaining = None if breed_budget is None else max(0, int(breed_budget))
    for sid in candidates:
        if remaining is not None and remaining <= 0:
            break
        summary = crawl_result_cache_for_show(
            sid, delay=delay, source="backfill", workers=workers, max_breeds=remaining,
        )
        attempted.append(summary)
        logger.info(
            "dog_backfill_show_complete",
            show_id=sid,
            status=summary.get("status"),
            crawled_breeds=summary.get("crawled_breeds"),
            error=summary.get("error"),
        )
        status = summary.get("status")
        if remaining is not None:
            remaining = max(0, remaining - (summary.get("crawled_breeds") or 0))
        if status == "complete":
            completed += 1
        elif status == "incomplete":
            in_progress += 1
        elif status != "skipped":
            failed += 1

    pass_summary = {
        "status": "ok",
        "attempted": len(attempted),
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
        "show_ids": candidates,
        "items": attempted,
    }
    logger.info(
        "dog_backfill_pass_complete",
        attempted=pass_summary["attempted"],
        completed=completed,
        in_progress=in_progress,
        failed=failed,
    )
    return pass_summary


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
        logger.info(
            "dog_immediate_result_warmup_complete",
            show_id=show_id,
            status=status,
            reason=summary.get("reason"),
            error=summary.get("error"),
        )
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
        logger.info("dog_immediate_result_warmup_deferred", show_id=show_id, reason="no_slot")
        return False

    claimed = _claim_result_cache_job(
        show_id,
        reason=reason,
        stale_seconds=_result_job_stale_seconds_for_show(show_id),
    )
    if not claimed:
        _finish_immediate_warmup(show_id)
        logger.info("dog_immediate_result_warmup_deferred", show_id=show_id, reason="job_running")
        return False

    thread = threading.Thread(
        target=_run_immediate_result_cache_warmup,
        args=(show_id,),
        name=f"dog-result-warmup-{show_id}",
        daemon=True,
    )
    thread.start()
    logger.info("dog_immediate_result_warmup_started", show_id=show_id, reason=reason)
    return True
