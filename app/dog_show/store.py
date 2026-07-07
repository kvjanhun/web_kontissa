import time

import structlog

from . import config
from . import db as dog_db
from . import sqlstore
from .utils import _utc_iso

logger = structlog.get_logger(__name__)

INDEX_DIR = config.INDEX_DIR
RESULT_JOB_STALE_SECONDS = config.RESULT_JOB_STALE_SECONDS
RESULT_JOB_BACKOFF_SECONDS = config.RESULT_JOB_BACKOFF_SECONDS

# The only in-memory cache left: the 30-minute Showlink show-list fetch gate
# (see shows._get_show_list). Everything else is read from dog.db per request.
_show_list_cache = {"data": None, "ts": 0}


# ---------------------------------------------------------------------------
# Breed index  (dog_show + dog_breed + dog_meta)
# ---------------------------------------------------------------------------

def _indexed_show(show_id):
    """One show's full index entry (metadata + breeds) or None."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_show(session, show_id)
    except (TypeError, ValueError):
        return None
    except Exception:
        logger.exception("dog_indexed_show_read_failed", show_id=show_id)
        return None


def _indexed_show_meta(show_id):
    """One show's index metadata (no breeds) or None."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_show_meta(session, show_id)
    except (TypeError, ValueError):
        return None
    except Exception:
        logger.exception("dog_indexed_show_meta_read_failed", show_id=show_id)
        return None


def _indexed_shows(show_ids):
    """Bulk read of full index entries: {str(show_id): entry}."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_shows(session, show_ids)
    except Exception:
        logger.exception("dog_indexed_shows_read_failed")
        return {}


def _indexed_show_metas(show_ids):
    """Bulk read of index metadata (no breeds): {str(show_id): meta}."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_shows_meta(session, show_ids)
    except Exception:
        logger.exception("dog_indexed_show_metas_read_failed")
        return {}


def _index_states():
    """Crawler candidate selection: per-show breed counts + empty-confirmed flags."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.index_states(session)
    except Exception:
        logger.exception("dog_index_states_read_failed")
        return {}


def _write_index_show(show_id, entry):
    """Persist one show's index entry (metadata + wholesale breed list) and
    advance the index-wide last_updated stamp."""
    def _write(session):
        sqlstore.write_show(session, show_id, entry)
        current = sqlstore.get_meta_number(session, "last_updated", 0)
        sqlstore.set_meta(session, "last_updated", max(current, entry.get("updated_at") or time.time()))

    dog_db.run_write(_write, op="index_show")


def _update_index_breed_judge(show_id, group, breed_id, judge):
    """Store a freshly-captured judge on the breed's index row. True if changed."""
    try:
        return dog_db.run_write(
            lambda session: sqlstore.set_breed_judge(session, show_id, group, breed_id, judge),
            op="breed_judge",
        ) > 0
    except Exception:
        logger.exception("dog_breed_judge_update_failed", show_id=show_id)
        return False


def _update_index_breed_result_flag(show_id, group, breed_id):
    """Flag the breed's index row as having results. True if changed."""
    try:
        return dog_db.run_write(
            lambda session: sqlstore.set_breed_has_results(session, show_id, group, breed_id),
            op="breed_result_flag",
        ) > 0
    except Exception:
        logger.exception("dog_breed_flag_update_failed", show_id=show_id)
        return False


def _search_index_breeds(variants):
    """Breed-name matches over the whole index: [(show_id, breed_dict)]."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_breeds_by_name(session, variants)
    except Exception:
        logger.exception("dog_search_breeds_failed")
        return []


def _search_index_judges(variants):
    """Judge matches (excluding breed-name matches): [(show_id, breed_dict)]."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_breeds_by_judge(session, variants)
    except Exception:
        logger.exception("dog_search_judges_failed")
        return []


def _search_index_show_ids(variants):
    """Ids of indexed shows whose name/title/date/month text matches."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_show_ids(session, variants)
    except Exception:
        logger.exception("dog_search_show_ids_failed")
        return []


def _indexed_ids_among(show_ids):
    """Which of the given ids are in the index, as a set of ints."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.indexed_show_ids(session, show_ids)
    except Exception:
        logger.exception("dog_indexed_ids_failed")
        return set()


def _index_summary(total_show_count=None):
    indexed_count = 0
    updated = 0
    try:
        with dog_db.session_scope() as session:
            indexed_count = sqlstore.count_shows(session)
            updated = sqlstore.get_meta_number(session, "last_updated", 0)
    except Exception:
        logger.exception("dog_index_summary_failed")
    return {
        "last_updated": updated or None,
        "last_updated_iso": _utc_iso(updated),
        "indexed_show_count": indexed_count,
        "total_show_count": total_show_count,
    }


# ---------------------------------------------------------------------------
# Whole-show result doc  (dog_result_cache + dog_result)
# ---------------------------------------------------------------------------

def _load_result_cache_doc(show_id):
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_result_doc(session, show_id)
    except Exception:
        logger.exception("dog_result_cache_load_failed", show_id=show_id)
        return None


def _save_result_cache_doc(show_id, doc):
    """Full rewrite of a whole-show result doc (final complete save)."""
    dog_db.run_write(
        lambda session: sqlstore.write_result_doc(session, show_id, doc),
        op="result_cache_doc",
    )


def _save_result_cache_header(show_id, doc):
    """Update only the cache header/meta row, leaving result rows untouched. Used
    on breed failure and on resume, where the rows are already persisted."""
    dog_db.run_write(
        lambda session: sqlstore.write_result_cache_header(session, show_id, doc),
        op="result_cache_header",
    )


def _append_result_breed(show_id, doc, group, breed_id, results):
    """Incrementally persist one freshly-completed breed's rows + awards and refresh
    the cache header — the per-breed progress save (replaces whole-show rewrite)."""
    dog_db.run_write(
        lambda session: sqlstore.append_result_breed(session, show_id, doc, group, breed_id, results),
        op="result_breed_append",
    )


def _complete_result_cache_show_ids():
    """Set of show ids with a complete result cache (one status-column scan).
    Used by the operational finals-rescue tool (scripts/dog_rescue_finals.py)."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.complete_result_cache_show_ids(session)
    except Exception:
        logger.exception("dog_complete_result_cache_ids_failed")
        return set()


def _dog_results_by_reg_id(reg_id):
    """Every captured result row for one registered dog, newest show first (see
    sqlstore.read_results_by_reg_id). Read-only; returns [] on any failure."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_results_by_reg_id(session, reg_id)
    except Exception:
        logger.exception("dog_results_by_reg_id_failed")
        return []


def _breed_awards_for_shows(show_ids):
    """Honor-roll award rows for a set of shows (see
    sqlstore.read_breed_awards_for_shows). Read-only; returns [] on any failure."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_breed_awards_for_shows(session, show_ids)
    except Exception:
        logger.exception("dog_breed_awards_read_failed")
        return []


def _search_dogs_by_name(query, limit=20):
    """Cross-show dog search aggregated by reg_id: one entry per distinct dog,
    newest-first (see sqlstore.search_dogs_by_name). Read-only; [] on error."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_dogs_by_name(session, query, limit=limit)
    except Exception:
        logger.exception("dog_search_dogs_failed")
        return []


def _search_dog_results_by_name(query, limit=20):
    """Per-show dog-name search over reg_id-less rows: [{show_id, name, count}]
    newest-first (see sqlstore.search_dog_results_by_name). Read-only; [] on error."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_dog_results_by_name(session, query, limit=limit)
    except Exception:
        logger.exception("dog_search_dog_names_failed")
        return []


def _search_breed_award_owners(query, limit=20):
    """Cross-show owner search over the honor roll, one hit per breed:
    [{show_id, fci_group, breed_id, owner, winner, count}] newest-first (see
    sqlstore.search_breed_award_owners). Read-only; [] on error."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_breed_award_owners(session, query, limit=limit)
    except Exception:
        logger.exception("dog_search_owners_failed")
        return []


def _search_breeder_awards(query, limit=20):
    """Cross-show kennel search over breeder awards, one hit per breed:
    [{show_id, fci_group, breed_id, kennel, owner, count}] newest-first (see
    sqlstore.search_breeder_awards). Read-only; [] on error."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.search_breeder_awards(session, query, limit=limit)
    except Exception:
        logger.exception("dog_search_breeders_failed")
        return []


# ---------------------------------------------------------------------------
# Result jobs  (dog_result_job)
# ---------------------------------------------------------------------------

def _load_result_jobs():
    try:
        with dog_db.session_scope() as session:
            return sqlstore.read_jobs(session)
    except Exception:
        logger.exception("dog_result_jobs_load_failed")
        return {"jobs": {}, "updated_at": 0}


def _save_result_jobs(data):
    dog_db.run_write(
        lambda session: sqlstore.write_jobs(session, data),
        op="result_jobs",
    )


def _queue_result_cache_job(show_id, reason="user"):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid, {})

    is_running = job.get("state") == "running"
    if not is_running:
        job["state"] = "queued"
    job["show_id"] = int(show_id)
    job["reason"] = reason
    job.setdefault("created_at", now)
    job.setdefault("attempts", 0)
    job["requested_at"] = now
    if not is_running:
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


def _heartbeat_result_cache_job(show_id, min_interval=15):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid)
    if not job or job.get("state") != "running":
        return False

    if (now - (job.get("updated_at") or 0)) < max(0, int(min_interval or 0)):
        return False

    job["updated_at"] = now
    jobs_doc["updated_at"] = now
    _save_result_jobs(jobs_doc)
    return True


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


def _result_job_due(job, now=None, stale_seconds=None):
    now = now or time.time()
    stale_seconds = RESULT_JOB_STALE_SECONDS if stale_seconds is None else max(1, int(stale_seconds))
    if job.get("state") == "running":
        updated_at = job.get("updated_at") or 0
        if (now - updated_at) < stale_seconds:
            return False
    return (job.get("next_attempt_at") or 0) <= now
