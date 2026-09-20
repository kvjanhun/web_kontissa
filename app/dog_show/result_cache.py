import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import structlog

from . import config, finals
# The breed-ring predicates live in finals.py (utils needs them for the settle
# ladder, and utils imports finals). Re-exported here under the names the crawler
# and the ops scripts have always used.
from .finals import (  # noqa: F401
    _breed_bob_awarded, _breed_capture_has_full_rows, _breed_capture_is_partial,
    _breed_capture_is_provisional, _breed_capture_is_settled,
)
from .indexing import (
    _indexed_result_flags_need_refresh, _is_show_recent_by_id,
    _mark_single_probe_breed_result_available, _persist_show_detail_to_index,
    _result_cache_doc_needs_result_refresh,
    _result_breeds_for_cache, _result_breeds_from_index,
    _show_date_for_id, _show_result_availability_for_id,
)
from .parsers import (
    FINALS_TARGETS, _parse_breed_results, _parse_finals_page, _parse_show_detail,
)
from .showlink import _fetch_page, _source_url
from .shows import _get_show_list
from .store import (
    _append_result_breed,
    _defer_result_cache_job,
    _heartbeat_result_cache_job, _indexed_show, _load_result_cache_doc,
    _load_result_jobs, _remove_result_cache_job, _result_job_due, _queue_result_cache_job,
    _save_result_cache_doc, _save_result_cache_header, _set_result_job_running,
    _update_index_breed_judge, _update_index_breed_result_flag,
)
from .utils import (
    _clean_all_results, _clean_breed_data, _clean_judge_name,
    _fetch_window_open, _local_dt, _result_live_plan, _show_age_days,
    _show_date_state, _show_result_availability, _terminal_status, _utc_iso,
)

logger = structlog.get_logger(__name__)

SHOW_ALL_RESULTS_TTL = config.SHOW_ALL_RESULTS_TTL
RESULT_CACHE_LIVE_TTL = config.RESULT_CACHE_LIVE_TTL
RESULT_CACHE_SETTLED_TTL = config.RESULT_CACHE_SETTLED_TTL
RESULT_CACHE_SETTLED_AFTER_DAYS = config.RESULT_CACHE_SETTLED_AFTER_DAYS
RESULT_AUTO_WINDOW_DAYS = config.RESULT_AUTO_WINDOW_DAYS
RESULT_SETTLE_DEADLINE_DAYS = config.RESULT_SETTLE_DEADLINE_DAYS
RESULT_CACHE_VERSION = config.RESULT_CACHE_VERSION
RESULT_RETRY_AFTER_SECONDS = config.RESULT_RETRY_AFTER_SECONDS
RESULT_CRAWL_DEFAULT_DELAY = config.RESULT_CRAWL_DEFAULT_DELAY
RESULT_CRAWL_DEFAULT_WORKERS = config.RESULT_CRAWL_DEFAULT_WORKERS
RESULT_LIVE_PROBE_BREED_LIMIT = config.RESULT_LIVE_PROBE_BREED_LIMIT
RESULT_FINALS_SWEEP_BREED_LIMIT = config.RESULT_FINALS_SWEEP_BREED_LIMIT
RESULT_FINALS_PROBE_TTL = config.RESULT_FINALS_PROBE_TTL
RESULT_QUIESCENCE_SECONDS = config.RESULT_QUIESCENCE_SECONDS
RESULT_QUIESCENCE_MAX_GAP = config.RESULT_QUIESCENCE_MAX_GAP
RESULT_UNSETTLED_RECHECK_BREED_LIMIT = config.RESULT_UNSETTLED_RECHECK_BREED_LIMIT
RESULT_HOT_BREED_LIMIT = config.RESULT_HOT_BREED_LIMIT
RESULT_WARM_BREED_LIMIT = config.RESULT_WARM_BREED_LIMIT
RESULT_COOL_SWEEP_BREED_LIMIT = config.RESULT_COOL_SWEEP_BREED_LIMIT
RESULT_BREED_STATIC_FETCH_LIMIT = config.RESULT_BREED_STATIC_FETCH_LIMIT
RESULT_LIVE_JOB_STALE_SECONDS = config.RESULT_LIVE_JOB_STALE_SECONDS

def _result_cache_doc_is_complete(doc):
    return bool(doc and doc.get("status") == "complete")

def _empty_result_cache_needs_refresh(show_id, doc, now=None):
    availability_now = _local_dt(now) if isinstance(now, (int, float)) else now
    return _result_cache_doc_needs_result_refresh(show_id, doc, now=availability_now)

def _availability_now(now):
    # Absolute timestamps are converted to Finnish wall clock, never the
    # container's UTC clock — the fetch window and the settle deadlines are
    # Finnish local, and the crawler runs in UTC.
    return _local_dt(now) if isinstance(now, (int, float)) else now

def _show_dict_for_plan(show_id):
    """Minimal show dict (id/date/month) for the live-plan date parsing."""
    indexed = _indexed_show(show_id) or {}
    return {
        "id": int(show_id),
        "date": indexed.get("date", ""),
        "month": indexed.get("month", ""),
        "title": indexed.get("title", ""),
    }

def _result_live_plan_for_id(show_id, doc=None, now=None):
    doc = doc if doc is not None else _load_result_cache_doc(show_id)
    indexed = _indexed_show(show_id) or {}
    return _result_live_plan(
        _show_dict_for_plan(show_id),
        doc,
        indexed.get("breeds") or [],
        now=_availability_now(now if now is not None else time.time()),
    )

def _mark_terminal_confirmation(doc, indexed_breeds, now=None):
    """Accumulate observed quiescence, and confirm the terminal once it holds.

    Rung 3 of the settle ladder. The signature covers the row count, whether
    judging is finished and what the finals probe saw, so a late row, a late
    `BIS-4` or a correction changes it and the window restarts — which is the
    whole protection against terminating a show early.

    Stability accumulates whether or not the target is met, unlike the previous
    version, which reset the counter on every pass where it was not: a show could
    never build up evidence that it had stopped moving, only that it had reached
    a predicted award. That inversion is why a show with no reachable terminal
    (a combined `FCI 5/6` ring, a show awarding no BIS at all) polled until the
    two-day deadline.

    Only observed time counts. A gap longer than `RESULT_QUIESCENCE_MAX_GAP`
    means nobody was watching — the night stop, a restart, a run of failures —
    and adds nothing, so the overnight silence cannot settle a show at dawn."""
    if not isinstance(doc, dict):
        return
    now = now or time.time()
    status = _terminal_status(doc, indexed_breeds)
    signature = status["signature"]
    previous = doc.get("terminal_fingerprint")
    last_checked = doc.get("terminal_checked_at") or 0

    doc["terminal_fingerprint"] = signature
    doc["terminal_checked_at"] = now
    doc["terminal_target_met"] = bool(status["target_met"])

    if previous != signature:
        doc["terminal_stable_seconds"] = 0.0
        doc["terminal_confirmed"] = False
        return

    gap = now - last_checked if last_checked else 0.0
    if 0 < gap <= RESULT_QUIESCENCE_MAX_GAP:
        doc["terminal_stable_seconds"] = float(doc.get("terminal_stable_seconds") or 0.0) + gap

    doc["terminal_confirmed"] = bool(
        status["target_met"]
        and float(doc.get("terminal_stable_seconds") or 0.0) >= RESULT_QUIESCENCE_SECONDS
    )

def _result_cache_ttl_for_show(show_id, now, doc=None):
    plan = _result_live_plan_for_id(show_id, doc=doc, now=now)
    if plan["phase"] in ("live", "rescue"):
        return plan["ttl"]
    if plan["phase"] == "upcoming":
        # Not fetchable yet; fall through to the date-based settled TTL below.
        pass
    elif plan["phase"] in ("settled", "settled_incomplete"):
        # Terminal reached (or deadline hit): fall through to the long settled
        # TTL / permanent-cache handling below rather than fast-polling.
        pass

    show_date = _show_date_for_id(show_id)
    if show_date:
        today = _local_dt(now).date()
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

    updated = indexed_show.get("updated_at") or 0
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

def _breed_awards_from_doc(doc):
    """Per-breed honor rolls keyed "group:breed_id" — the ROP/VSP/SERT winner
    lists (with owners and the breeder award) each completed breed carries in
    the doc, so the whole-show view can render them without the breed pages."""
    breed_awards = {}
    for breed_key, breed_data in (doc.get("completed_breeds") or {}).items():
        if not isinstance(breed_data, dict):
            continue
        awards = breed_data.get("awards")
        if awards:
            breed_awards[str(breed_key)] = awards
    return breed_awards

def _result_response_from_doc(show_id, doc, stale=False):
    fetched_at = doc.get("cached_at") or doc.get("updated_at") or time.time()
    progress = _result_cache_progress(show_id, doc=doc)
    return {
        "show_id": int(show_id),
        "title": doc.get("title", ""),
        "source_url": doc.get("source_url") or _source_url(show_id),
        "results": _clean_all_results(doc.get("results") or []),
        "breed_awards": _breed_awards_from_doc(doc),
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

def _all_results_response(show_id, allow_stale=False):
    """The /all-results payload straight from the persisted doc, or None when
    the cache is missing, owed a rebuild, or (unless allowed) stale."""
    now = time.time()

    doc = _load_result_cache_doc(show_id)
    if not _result_cache_doc_is_complete(doc):
        return None

    if _empty_result_cache_needs_refresh(show_id, doc, now=now):
        return None

    stale = not _result_cache_doc_is_fresh(show_id, doc, now=now)
    if stale and not allow_stale:
        return None

    return _result_response_from_doc(show_id, doc, stale=stale)

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
        # the source `existing` in place (a shared, already-extended results list
        # would skew the finals fingerprint compared after the crawl).
        "completed_breeds": dict(existing.get("completed_breeds") or {}),
        "failed_breeds": dict(existing.get("failed_breeds") or {}),
        "results": list(existing.get("results") or []),
        "live_probe_cursor": existing.get("live_probe_cursor", 0),
        "live_probe_breed_count": existing.get("live_probe_breed_count"),
        "live_probe_breed_limit": existing.get("live_probe_breed_limit"),
        "finals_sweep_cursor": existing.get("finals_sweep_cursor", 0),
        "finals_sweep_breed_count": existing.get("finals_sweep_breed_count"),
        "finals_sweep_breed_limit": existing.get("finals_sweep_breed_limit"),
        "unsettled_recheck_cursor": existing.get("unsettled_recheck_cursor", 0),
        "unsettled_breed_count": existing.get("unsettled_breed_count"),
        "cool_sweep_cursor": existing.get("cool_sweep_cursor", 0),
        # What the last probe read. Carried, or every pass would start blind to
        # the finals it already knows about and re-derive structure it has been
        # told; it is refreshed in the pass, not trusted forever.
        "finals_probe": dict(existing.get("finals_probe") or {}),
        "terminal_target_met": existing.get("terminal_target_met"),
        "terminal_confirmed": existing.get("terminal_confirmed"),
        "terminal_fingerprint": existing.get("terminal_fingerprint"),
        # The quiescence accumulator. Dropping these would restart the settle
        # window on every pass, so a show could never accumulate the stability it
        # settles on — the same shape of bug as resetting it on unmet passes.
        "terminal_checked_at": existing.get("terminal_checked_at"),
        "terminal_stable_seconds": existing.get("terminal_stable_seconds") or 0.0,
    }

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

def _finals_probe_placements(doc):
    """How many placements the last probe saw across both finals pages."""
    pages = ((doc or {}).get("finals_probe") or {}).get("pages") or {}
    return sum(
        len(section.get("placements") or [])
        for page in pages.values()
        for section in (page.get("sections") or [])
    )


def _finals_probe_due(doc, has_captures, all_captured, now=None):
    """Whether to spend the two probe requests on this pass.

    Nothing can be awarded before something has been judged, and a show whose
    finals pages have been empty all morning does not need re-reading every two
    minutes. Once the pages show anything — or every ring is captured, which is
    when the finals are imminent — probe every pass: that is the window where
    being minutes late costs a whole night.
    """
    if not has_captures:
        return False
    probe = (doc or {}).get("finals_probe") or {}
    if not (probe.get("pages") or {}):
        return True
    if all_captured or _finals_probe_placements(doc):
        return True
    checked_at = probe.get("checked_at") or 0
    return ((now or time.time()) - checked_at) >= RESULT_FINALS_PROBE_TTL


def _probe_finals_pages(show_id, doc, delay=0.0):
    """Read the show's own `R=RYP` and `R=BIS` pages into `doc["finals_probe"]`.

    Two requests that answer directly what thirty breed re-reads could only
    guess at: whether the finals have been awarded, how the show actually
    partitions its rings (a combined `FCI 5/6` is one section, not two), and
    which dog won what. Everything downstream — the settle ladder, the targeted
    re-fetch — reads this rather than inferring structure from the breed index.

    Failures are recorded and left: a probe that could not be read this pass is
    not evidence that the finals do not exist, and must never be allowed to look
    like it."""
    probe = dict(doc.get("finals_probe") or {})
    pages = dict(probe.get("pages") or {})
    errors = {}
    for target in FINALS_TARGETS:
        if delay:
            time.sleep(delay)
        try:
            soup = _fetch_page(_source_url(show_id, target))
        except Exception as exc:  # noqa: BLE001 - recorded, never fatal to the pass
            errors[target] = f"{type(exc).__name__}: {exc}"
            logger.warning("dog_finals_probe_failed", show_id=show_id, target=target, error=errors[target])
            continue
        parsed = _parse_finals_page(soup, show_id)
        pages[target] = {"sections": parsed["sections"]}

    probe["pages"] = pages
    probe["checked_at"] = time.time()
    probe["errors"] = errors
    doc["finals_probe"] = probe
    return probe


def _finals_resweep_breeds(breeds, completed_breeds, doc, analysis, limit=None):
    """The breeds to re-fetch this pass so the finals land on their rows.

    With a probe this is exact — `finals.candidate_breed_keys` returns the breeds
    the finals pages name whose captured rows are still missing the promised
    token — so the limit almost never binds. Without one it falls back to the
    structural guesses, where it very much does. Bounded per pass and rotated via
    `finals_sweep_cursor` either way, so a big show cannot burst."""
    if limit is None:
        limit = RESULT_FINALS_SWEEP_BREED_LIMIT
    limit = max(0, int(limit or 0))
    if limit <= 0:
        return []

    candidate_keys = finals.candidate_breed_keys(analysis)
    by_key = {_breed_cache_key_from_breed(breed): breed for breed in breeds or []}
    candidates = [
        by_key[key] for key in candidate_keys
        if key in by_key and key in completed_breeds
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

def _unsettled_capture_breeds(breeds, completed_breeds, doc, limit=None, mid_ring_only=False):
    """The already-captured breeds whose rows aren't final yet, to re-fetch now.

    Bounded per pass and rotated via `unsettled_recheck_cursor`, so a 300-breed
    show re-checks a slice each pass instead of bursting over every ring still in
    progress. `limit=None` (the heal pass) takes them all.

    `mid_ring_only` narrows it to captures that are genuinely partial. The heal
    pass repairs settled history, where a provisional capture has nothing to
    repair: it already holds every entered dog, and the second fetch that would
    promote it only ever comes from a live crawl the show will never get again.
    Re-fetching those would re-crawl most of the database on every run."""
    candidates = []
    for breed in breeds or []:
        entry = (completed_breeds or {}).get(_breed_cache_key_from_breed(breed))
        if entry is None:
            continue
        if mid_ring_only:
            if not _breed_capture_is_partial(entry, breed):
                continue
        elif _breed_capture_is_settled(entry, breed):
            continue
        candidates.append(breed)

    doc["unsettled_breed_count"] = len(candidates)
    if not candidates:
        doc["unsettled_recheck_cursor"] = 0
        return []
    if limit is None:
        doc["unsettled_recheck_cursor"] = 0
        return candidates

    limit = max(0, int(limit or 0))
    if limit <= 0:
        return []
    try:
        cursor = max(0, int(doc.get("unsettled_recheck_cursor") or 0)) % len(candidates)
    except (TypeError, ValueError):
        cursor = 0
    selected = [
        candidates[(cursor + offset) % len(candidates)]
        for offset in range(min(limit, len(candidates)))
    ]
    doc["unsettled_recheck_cursor"] = (cursor + len(selected)) % len(candidates)
    return selected

def _rotating_slice(candidates, doc, cursor_key, limit):
    """Take `limit` breeds from `candidates`, resuming where the last pass left
    off. The cursor lives in the doc so a bounded pass round-robins the whole set
    across passes rather than re-fetching the same head every time."""
    if not candidates:
        doc[cursor_key] = 0
        return []
    limit = max(0, int(limit or 0))
    if limit <= 0:
        return []
    try:
        cursor = max(0, int(doc.get(cursor_key) or 0)) % len(candidates)
    except (TypeError, ValueError):
        cursor = 0
    selected = [
        candidates[(cursor + offset) % len(candidates)]
        for offset in range(min(limit, len(candidates)))
    ]
    doc[cursor_key] = (cursor + len(selected)) % len(candidates)
    return selected


def _breed_static_fetches(entry):
    return _safe_int((entry or {}).get("static_fetches")) or 0


def _judge_for_capture(entry, breed):
    """The judge assigned to a breed, from the capture or the index row."""
    return str((entry or {}).get("judge") or (breed or {}).get("judge") or "").strip()


def _live_tier_breeds(breeds, completed_breeds, doc, hot_limit=None, warm_limit=None, cool_limit=None):
    """Split the captured breeds into the three attention tiers.

    **Hot** is each judge's first ring that is not finished yet. A judge judges
    one breed, finishes it, and moves on, so at most one ring per judge can be
    moving — which turns "which of 96 pages might have changed" into "these ten".
    A breed whose rows have come back unchanged `RESULT_BREED_STATIC_FETCH_LIMIT`
    times drops out of hot even if it is still its judge's first: that is the
    fallback wherever the queue misfires, and it needs no judge at all.

    **Warm** is every other capture that is not final, rotating under a cap.

    **Cool** is the captures that look final. They are swept slowly for as long as
    the show is live, because a judge advancing is *not* evidence that the breed
    behind them is complete — a club secretary can register a row long after its
    ring ended, and nothing else in the design would ever look again.
    """
    hot_limit = RESULT_HOT_BREED_LIMIT if hot_limit is None else hot_limit
    warm_limit = RESULT_WARM_BREED_LIMIT if warm_limit is None else warm_limit
    cool_limit = RESULT_COOL_SWEEP_BREED_LIMIT if cool_limit is None else cool_limit

    unfinished = []
    finished = []
    for breed in breeds or []:
        entry = (completed_breeds or {}).get(_breed_cache_key_from_breed(breed))
        if entry is None:
            continue  # never captured: it is pending, not a re-check
        (finished if _breed_capture_is_settled(entry, breed) else unfinished).append((breed, entry))

    # Breed-list order is programme order, so a judge's first unfinished breed is
    # the ring they are most plausibly in.
    hot_keys = set()
    hot = []
    seen_judges = set()
    hot_limit = max(0, int(hot_limit or 0))
    for breed, entry in unfinished:
        if len(hot) >= hot_limit:
            break
        judge = _judge_for_capture(entry, breed)
        if not judge or judge in seen_judges:
            continue
        seen_judges.add(judge)
        if _breed_static_fetches(entry) >= RESULT_BREED_STATIC_FETCH_LIMIT:
            continue
        hot.append(breed)
        hot_keys.add(_breed_cache_key_from_breed(breed))

    warm_candidates = [
        breed for breed, _entry in unfinished
        if _breed_cache_key_from_breed(breed) not in hot_keys
    ]
    cool_candidates = [breed for breed, _entry in finished]

    doc["unsettled_breed_count"] = len(unfinished)
    doc["hot_breed_count"] = len(hot)
    doc["warm_breed_count"] = len(warm_candidates)
    doc["cool_breed_count"] = len(cool_candidates)

    return {
        "hot": hot,
        "warm": _rotating_slice(warm_candidates, doc, "unsettled_recheck_cursor", warm_limit),
        "cool": _rotating_slice(cool_candidates, doc, "cool_sweep_cursor", cool_limit),
    }


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
    # A breed with full rows and no honour roll is final only once a second fetch
    # brings back the same rows. Carry the confirmation across re-fetches so the
    # breed does not re-enter the provisional state every time it is re-read; a
    # fetch that brought *more* rows is new data and starts the count again.
    previous = (doc.get("completed_breeds") or {}).get(item["breed_key"]) or {}
    if previous and previous.get("updated_at") != fetched_at:
        if _safe_int(previous.get("result_count")) == result_count:
            completed_entry["rows_confirmed_at"] = previous.get("rows_confirmed_at") or fetched_at
            # Adaptive backoff: an unchanged re-fetch is evidence this ring is not
            # where the data is. Enough of them and the breed leaves the hot tier,
            # whether or not its judge queue says it should.
            completed_entry["static_fetches"] = _breed_static_fetches(previous) + 1
        # Rows grew: new data, so the breed is hot again and any confirmation of
        # "these rows are final" is void.
    elif previous:
        completed_entry["rows_confirmed_at"] = previous.get("rows_confirmed_at")
        completed_entry["static_fetches"] = _breed_static_fetches(previous)
    if not completed_entry.get("rows_confirmed_at"):
        completed_entry.pop("rows_confirmed_at", None)
    doc.setdefault("completed_breeds", {})[item["breed_key"]] = completed_entry
    doc.setdefault("failed_breeds", {}).pop(item["breed_key"], None)
    doc["updated_at"] = fetched_at
    if not preserve_existing_complete:
        _append_result_breed(show_id, doc, group, breed_id, mapped_results)
    _heartbeat_result_cache_job(show_id)
    # Fold the capture into the breed index at capture time — the index is the
    # only judge/result-flag source the read paths consult.
    if result_count:
        _update_index_breed_result_flag(show_id, group, breed_id)
    if judge:
        _update_index_breed_judge(show_id, group, breed_id, judge)

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

def crawl_result_cache_for_show(show_id, delay=RESULT_CRAWL_DEFAULT_DELAY, force=False, source="manual", workers=RESULT_CRAWL_DEFAULT_WORKERS, heal=False):
    """Build or resume the persisted whole-show results cache for one show.

    `force` rebuilds from empty — every breed re-fetched, the captured rows
    replaced wholesale. `heal` instead keeps the settled captures and re-fetches
    only the breeds whose rows never reached the end of their ring, ignoring the
    fetch window and the cache TTL that would otherwise leave settled history
    alone (scripts/dog_heal_partial_breeds.py)."""
    show_id = int(show_id)
    now = time.time()
    availability = _show_result_availability_for_id(show_id, now=_local_dt(now))
    existing_for_plan = _load_result_cache_doc(show_id)
    plan = _result_live_plan_for_id(show_id, doc=existing_for_plan, now=now)
    # Fetch permission is the base availability window OR the finals-aware plan:
    # both close outside the shared fetch window, so a pass reaching here at
    # night is skipped whatever queued it. The plan is still consulted because it
    # closes earlier than the base window for a show that has already settled.
    # `force`/`heal` (the one-off ops scripts) bypass both deliberately; when to
    # *invoke* a fetch is otherwise the scheduler's job (auto candidates / TTL).
    if not (force or heal) and not (availability.get("can_fetch", True) or plan.get("can_fetch", False)):
        logger.info(
            "dog_result_cache_skipped",
            show_id=show_id,
            source=source,
            reason=availability.get("reason"),
            plan_phase=plan.get("phase"),
        )
        return {
            "show_id": show_id,
            "status": "skipped",
            "reason": availability.get("reason"),
            "availability": availability,
            "progress": _result_cache_progress(show_id),
        }

    existing = _load_result_cache_doc(show_id)
    if not (force or heal) and _result_cache_doc_is_fresh(show_id, existing, now=now):
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

    # Anything still complete here is a cache we refresh in place: a non-forced
    # pass only reaches this point once the doc is stale (the freshness gate
    # above), or on a heal, which deliberately reopens settled history.
    preserve_existing_complete = _result_cache_doc_is_complete(existing) and not force
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
            "live_probe_cursor",
            "live_probe_breed_count",
            "live_probe_breed_limit",
            "finals_sweep_cursor",
            "finals_sweep_breed_count",
            "finals_sweep_breed_limit",
            "cool_sweep_cursor",
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

    # A breed page is only a result once its ring is finished. Showlink fills it
    # class by class while judging runs, and the breed list flags a breed as
    # having results the moment its first class appears, so a live pass captures
    # whatever was on the page at that second. Treating that as a permanent
    # capture froze breeds at a fraction of the entry — two of eight flat-coats —
    # and, for a breed captured before any class was judged, at zero dogs.
    # While fetching is permitted (live day, post-show rescue, or a heal pass) an
    # unsettled capture stays re-fetchable; after that the show settles with
    # whatever the source gave it.
    refetch_window = heal or plan.get("can_fetch", False)

    pending_breeds = [
        breed for breed in breeds_with_results
        if _breed_cache_key_from_breed(breed) not in completed_breeds
    ]
    # The heal pass re-fetches every unsettled capture in one go; a live pass
    # spends its budget across the three attention tiers instead. Outside the
    # fetch window nothing is selected, but the counts are still recorded, so a
    # pass reports what it is leaving behind rather than a stale number.
    cool_breeds = []
    if heal:
        recheck_breeds = _unsettled_capture_breeds(
            breeds_with_results, completed_breeds, doc, limit=None, mid_ring_only=True,
        )
    elif not refetch_window:
        recheck_breeds = _unsettled_capture_breeds(
            breeds_with_results, completed_breeds, doc, limit=0,
        )
    else:
        tiers = _live_tier_breeds(breeds_with_results, completed_breeds, doc)
        recheck_breeds = tiers["hot"] + tiers["warm"]
        # The cool sweep only runs while the show is still live: once it settles
        # there is nothing left to catch, and re-reading finished history is
        # exactly the traffic this redesign is removing.
        if plan.get("show_state") == "live":
            cool_breeds = tiers["cool"]

    # Targeted finals re-sweep: when nothing new is pending but the show still
    # owes its terminal award (or hasn't yet confirmed the finals are stable),
    # re-check only the breeds that can structurally carry the missing tokens —
    # groups still missing RYP-1, then the RYP-1 winners' pages for the main BIS,
    # then the finals-carrying breeds once for a late BIS-2..4. Showlink appends
    # these onto the winners' already-captured rows, so the re-fetch replaces
    # those rows in place (no duplication). This is scoped by finals.py, not a
    # blind rotation over every captured breed.
    new_result_breeds = [
        breed for breed in pending_breeds
        if breed.get("has_results")
    ]
    analysis = finals.analyze(doc, breeds_with_results)
    # Keep watching the finals until they are confirmed stable
    # (`_mark_terminal_confirmation` sets terminal_confirmed once the finals have
    # stopped changing across passes).
    finals_hunt_active = (
        analysis["expects_finals"] and not doc.get("terminal_confirmed")
    )
    finals_resweep = 0
    if refetch_window and finals_hunt_active:
        # The probe runs whether or not new breeds are pending: it is two
        # requests, it is the only direct view of the finals, and delaying it
        # until the breed rings go quiet is what stranded show 14014's BIS.
        if _finals_probe_due(
            doc,
            has_captures=bool(completed_breeds),
            all_captured=bool(breeds_with_results) and not pending_breeds and not recheck_breeds,
        ):
            _probe_finals_pages(show_id, doc, delay=delay)
            analysis = finals.analyze(doc, breeds_with_results)
        resweep_breeds = _finals_resweep_breeds(
            breeds_with_results, completed_breeds, doc, analysis
        )
        pending_breeds = pending_breeds + resweep_breeds
        finals_resweep = len(resweep_breeds)

    # Newly judged breeds first, mid-ring re-checks after: if the pass is cut
    # short by a failure, the breeds nobody has any rows for are the ones already
    # fetched. A breed appearing in both lists is impossible — the re-check set is
    # drawn from completed_breeds, which pending_breeds excludes — but the finals
    # re-sweep can overlap it, so drop the duplicate rather than fetch twice.
    seen_keys = {_breed_cache_key_from_breed(breed) for breed in pending_breeds}
    for extra in (recheck_breeds, cool_breeds):
        for breed in extra:
            key = _breed_cache_key_from_breed(breed)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            pending_breeds.append(breed)

    logger.info(
        "dog_result_cache_crawl_start",
        show_id=show_id,
        source=source,
        force=force,
        heal=heal,
        resumable=resumable,
        preserve_existing_complete=preserve_existing_complete,
        total_breeds=len(breeds_with_results),
        completed_breeds=len(completed_breeds),
        pending_breeds=len(pending_breeds),
        unsettled_breeds=doc.get("unsettled_breed_count"),
        recheck_breeds=len(recheck_breeds),
        hot_breeds=doc.get("hot_breed_count"),
        cool_sweep=len(cool_breeds),
        finals_resweep=finals_resweep,
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

    cached_at = time.time()
    # Confirm the terminal if this pass added nothing new to it — the stability
    # check that lets the show settle (see _result_live_plan).
    _mark_terminal_confirmation(doc, breeds_with_results)
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
    # Nothing this pass could schedule is fetchable outside the window, so stop
    # before the show list rather than selecting shows the crawl would skip.
    if not _fetch_window_open(now):
        return candidates
    try:
        shows_list = _get_show_list()
    except Exception:
        logger.warning("dog_result_cache_auto_show_list_failed", exc_info=True)
        return candidates

    now_local = _local_dt(now)
    today = now_local.date()
    # Only shows inside the auto window can ever become candidates: rescue ends
    # at the settle deadline, recent-past warming at the auto window.
    # The Tulokset list carries the whole season (hundreds of settled shows), so
    # decide from the list row's date alone before paying for the doc load and
    # finals analysis. Unparseable dates fall through open, as before.
    window_days = max(RESULT_AUTO_WINDOW_DAYS, RESULT_SETTLE_DEADLINE_DAYS)
    for show in shows_list:
        show_id = int(show["id"])
        state = _show_date_state(show, today=today)
        if state == "upcoming":
            continue

        age_days = _show_age_days(show, today=today)
        if state == "past" and age_days is not None and age_days > window_days:
            continue

        doc = _load_result_cache_doc(show_id)
        plan = _result_live_plan_for_id(show_id, doc=doc, now=now)
        phase = plan["phase"]
        if phase == "upcoming":
            continue

        fetchable = plan.get("can_fetch", False)
        # Recent-past initial warming: a show whose crawl never completed (missing
        # or partial cache) still gets warmed within the auto window even once it
        # is past its date and no longer finals-owed. A complete cache that merely
        # lacks its finals is left to the finals rescue (and the deadline), never
        # re-warmed here.
        recent_past_warming = (
            not fetchable
            and plan["show_state"] == "past"
            and age_days is not None
            and 0 <= age_days <= RESULT_AUTO_WINDOW_DAYS
            and not _result_cache_doc_is_complete(doc)
        )
        if not fetchable and not recent_past_warming:
            continue

        # Reuse the doc already loaded for the plan instead of reloading it.
        if _result_cache_doc_is_fresh(show_id, doc, now=now):
            continue

        indexed_show = _indexed_show(show_id)
        indexed_breeds = indexed_show.get("breeds", []) if indexed_show else []
        if (
            indexed_breeds
            and not _result_breeds_for_cache(show_id, indexed_breeds)
            and not _indexed_result_flags_need_refresh(show_id, indexed_show)
        ):
            continue

        # Priority classes so a busy weekend can't starve time-critical work:
        # 0 brand-new live show (nothing cached yet) -> warm first so the page
        #   shows something; 1 finals-owed (rescue) -> the failure this redesign
        #   fixes; 2 live refresh; 3 recent-past warming. Cheap per pass.
        if phase == "live":
            priority = 0 if not doc else 2
        elif phase == "rescue":
            priority = 1
        else:
            priority = 3
        if plan["show_state"] == "live":
            recency_rank = -1
        elif age_days is not None:
            recency_rank = age_days
        else:
            recency_rank = RESULT_AUTO_WINDOW_DAYS + 1
        candidates.append({
            "show_id": show_id,
            "source": "auto",
            "job": None,
            "rank": (priority, recency_rank, show_id),
        })

    candidates.sort(key=lambda item: item.get("rank", (99, 99, 0)))
    for candidate in candidates:
        candidate.pop("rank", None)
    return candidates

def _queue_live_result_cache_refresh(show_id, show=None, reason="live-detail-refresh", now=None):
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
    return {
        "show_id": show_id,
        "job_state": job.get("state"),
    }

def _queue_live_result_cache_refreshes(shows, limit=2):
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

