import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog

from . import config
from .indexing import (
    _cached_show_detail, _is_show_recent_by_id,
    _result_breeds_from_index, _result_breeds_with_results, _show_date_for_id,
    _update_index_breed_judge,
)
from .parsers import _parse_breed_results, _parse_show_detail
from .showlink import _fetch_page, _source_url
from .shows import _get_show_list
from .store import (
    _breed_result_cache, _claim_result_cache_job, _defer_result_cache_job,
    _indexed_show, _load_result_cache_doc, _load_result_jobs, _remove_result_cache_job, _result_job_due,
    _save_index, _save_result_cache_doc, _set_result_job_running,
    _show_all_results_cache, _show_detail_cache,
)
from .utils import (
    _clean_all_results, _clean_breed_data, _clean_breed_list, _clean_judge_name,
    _is_recent_show, _show_age_days, _utc_iso,
)

logger = structlog.get_logger(__name__)

SHOW_ALL_RESULTS_TTL = config.SHOW_ALL_RESULTS_TTL
RESULT_CACHE_ACTIVE_TTL = config.RESULT_CACHE_ACTIVE_TTL
RESULT_CACHE_SETTLED_TTL = config.RESULT_CACHE_SETTLED_TTL
RESULT_CACHE_SETTLED_AFTER_DAYS = config.RESULT_CACHE_SETTLED_AFTER_DAYS
RESULT_AUTO_WINDOW_DAYS = config.RESULT_AUTO_WINDOW_DAYS
RESULT_CACHE_VERSION = config.RESULT_CACHE_VERSION
RESULT_RETRY_AFTER_SECONDS = config.RESULT_RETRY_AFTER_SECONDS
RESULT_CRAWL_DEFAULT_DELAY = config.RESULT_CRAWL_DEFAULT_DELAY
RESULT_CRAWL_DEFAULT_WORKERS = config.RESULT_CRAWL_DEFAULT_WORKERS
RESULT_IMMEDIATE_WARMUP = config.RESULT_IMMEDIATE_WARMUP_DEFAULT

_immediate_warmups = set()
_immediate_warmups_lock = threading.Lock()
_immediate_warmup_slots = threading.BoundedSemaphore(max(1, config.RESULT_IMMEDIATE_MAX_ACTIVE))

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
    breed_obj = _clean_breed_data(breed_obj or {})
    if breed_obj.get("judge") and _update_index_breed_judge(show_id, group, breed, breed_obj.get("judge")):
        _save_index()

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

def _show_detail_for_result_cache(show_id):
    indexed_show = _indexed_show(show_id)
    if indexed_show and indexed_show.get("breeds"):
        return {
            "id": int(show_id),
            "title": indexed_show.get("title") or indexed_show.get("name", ""),
            "source_url": indexed_show.get("source_url") or _source_url(show_id),
            "breeds": _clean_breed_list(indexed_show.get("breeds", [])),
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
    judge = _clean_judge_name(item["breed_data"].get("judge"))

    _breed_result_cache[_breed_result_cache_key(show_id, group, breed_id)] = {
        "data": item["breed_data"],
        "ts": fetched_at,
    }

    doc.setdefault("results", []).extend(mapped_results)
    doc.setdefault("completed_breeds", {})[item["breed_key"]] = {
        "name": breed.get("name", ""),
        "result_count": len(mapped_results),
        "judge": judge,
        "updated_at": fetched_at,
        "updated_at_iso": _utc_iso(fetched_at),
    }
    doc.setdefault("failed_breeds", {}).pop(item["breed_key"], None)
    doc["updated_at"] = fetched_at
    _save_result_doc_progress(show_id, doc, preserve_existing_complete)
    if judge and _update_index_breed_judge(show_id, group, breed_id, judge):
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
