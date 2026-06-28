import time

import structlog

from . import config
from . import db as dog_db
from . import sqlstore
from .utils import _utc_iso

logger = structlog.get_logger(__name__)

# Legacy JSON locations. Storage now lives in dog.db (see db.py / sqlstore.py),
# but these constants are still re-exported (api/dog.py, scripts/dog_crawl.py)
# and describe where the one-off migration reads its source from.
INDEX_DIR = config.INDEX_DIR
INDEX_PATH = config.INDEX_PATH
RESULT_CACHE_DIR = config.RESULT_CACHE_DIR
RESULT_JOBS_PATH = config.RESULT_JOBS_PATH
RESULT_JOB_STALE_SECONDS = config.RESULT_JOB_STALE_SECONDS
RESULT_JOB_BACKOFF_SECONDS = config.RESULT_JOB_BACKOFF_SECONDS

# In-memory working caches. `_show_index` stays the shared, mutated-in-place
# mirror of the breed index that indexing.py, search.py, crawler.py, and
# app/api/dog.py all read; only its backing store changed (dog.db, not JSON).
_show_list_cache = {"data": None, "ts": 0}
_show_detail_cache = {}
_breed_result_cache = {}
_show_all_results_cache = {}
_show_index = {"shows": {}, "last_updated": 0}

# Cross-process freshness: the index generation we last loaded into _show_index.
# None means "never loaded" so the first _load_index() always reads. Bumped in
# the DB on every write; when the stored value moves ahead of this, we reload.
_index_generation = None

# Wall-clock of the last generation check, to throttle rebuilds (see _load_index).
_last_index_check_ts = 0.0

# Show ids whose mirror entry changed since the last flush. _save_index() writes
# only these (one show = a handful of rows) instead of rewriting all ~47k breed
# rows every time a single judge or result flag is folded in.
_dirty_index_show_ids = set()


def _mark_index_dirty(show_id):
    """Record that _show_index["shows"][show_id] changed and needs flushing."""
    _dirty_index_show_ids.add(str(int(show_id)))


# ---------------------------------------------------------------------------
# Breed index  (dog_show + dog_breed + dog_meta)
# ---------------------------------------------------------------------------

def _load_index(force=False):
    """Refresh the in-memory mirror when the DB generation has advanced.

    Cheap generation check on every call (a single keyed lookup), full rebuild
    only when something actually changed — mirroring the old mtime-gated JSON
    reload. Returns True when the mirror was reloaded.

    Throttle: once the mirror exists, skip the check entirely for
    INDEX_RELOAD_MIN_INTERVAL seconds. A single request re-enters this several
    times (once per live show, via _result_cache_due), and a busy live show makes
    the crawler bump the generation often, so without a floor each call did a full
    read_index rebuild and starved the workers. force=True (used after our own
    writes) always bypasses the throttle.
    """
    global _index_generation, _last_index_check_ts

    now = time.time()
    if (
        not force
        and _index_generation is not None
        and (now - _last_index_check_ts) < config.INDEX_RELOAD_MIN_INTERVAL
    ):
        return False

    try:
        with dog_db.session_scope() as session:
            generation = sqlstore.get_index_generation(session)
            _last_index_check_ts = now
            if not force and _index_generation is not None and generation == _index_generation:
                return False
            new_index = sqlstore.read_index(session)
    except Exception:
        logger.exception("dog_index_load_failed")
        return False

    _show_index.clear()
    _show_index.update(new_index)
    _index_generation = generation
    _dirty_index_show_ids.clear()
    logger.info("dog_index_loaded", count=len(_show_index.get("shows", {})))
    return True


def _save_index():
    """Flush dirty mirror shows to dog.db and bump the index generation.

    Every mutation path calls _load_index() before mutating, so the mirror is
    the current DB state plus our one-show change; we therefore adopt the bumped
    generation as our own (like the JSON store recorded the new file mtime) and
    skip reloading our own write. Other processes still see the bump and reload.
    Writes are per-show, so two processes editing different shows never clobber
    each other the way the old whole-file JSON write could.
    """
    global _index_generation

    dirty = list(_dirty_index_show_ids)
    if not dirty:
        return

    def _write(session):
        for sid in dirty:
            show = _show_index.get("shows", {}).get(sid)
            if show is None:
                continue
            sqlstore.write_show(session, sid, show)
        sqlstore.set_meta(session, "last_updated", _show_index.get("last_updated") or 0)
        return sqlstore.bump_index_generation(session)

    try:
        new_generation = dog_db.run_write(_write, op="index_save")
    except Exception:
        logger.exception("dog_index_save_failed")
        return

    _dirty_index_show_ids.clear()
    _index_generation = new_generation


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
    """Full rewrite of a whole-show result doc (final complete save / migration)."""
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
    """Set of show ids with a complete result cache (for the backfill skip check)."""
    try:
        with dog_db.session_scope() as session:
            return sqlstore.complete_result_cache_show_ids(session)
    except Exception:
        logger.exception("dog_complete_result_cache_ids_failed")
        return set()


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


def _claim_result_cache_job(show_id, reason="user-immediate", stale_seconds=None):
    now = time.time()
    jobs_doc = _load_result_jobs()
    jobs = jobs_doc.setdefault("jobs", {})
    sid = str(int(show_id))
    job = jobs.get(sid, {"show_id": int(show_id), "created_at": now, "attempts": 0})

    if job.get("state") == "running" and not _result_job_due(job, now=now, stale_seconds=stale_seconds):
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


# ---------------------------------------------------------------------------
# Small read helpers used across the package
# ---------------------------------------------------------------------------

def _indexed_show(show_id):
    _load_index()
    return _show_index.get("shows", {}).get(str(show_id))


def _index_summary(total_show_count=None):
    updated = _show_index.get("last_updated") or 0
    return {
        "last_updated": updated or None,
        "last_updated_iso": _utc_iso(updated),
        "indexed_show_count": len(_show_index.get("shows", {})),
        "total_show_count": total_show_count,
    }
