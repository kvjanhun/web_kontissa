import json
import os
import time

import structlog

from . import config
from .utils import _clean_judge_name, _utc_iso

logger = structlog.get_logger(__name__)

INDEX_DIR = config.INDEX_DIR
INDEX_PATH = config.INDEX_PATH
RESULT_CACHE_DIR = config.RESULT_CACHE_DIR
RESULT_JOBS_PATH = config.RESULT_JOBS_PATH
RESULT_JOB_STALE_SECONDS = config.RESULT_JOB_STALE_SECONDS
RESULT_JOB_BACKOFF_SECONDS = config.RESULT_JOB_BACKOFF_SECONDS

_show_list_cache = {"data": None, "ts": 0}
_show_detail_cache = {}
_breed_result_cache = {}
_show_all_results_cache = {}
_show_index = {"shows": {}, "last_updated": 0}
_show_index_mtime = 0

def _normalize_show_index_judges():
    changed = False
    for show in _show_index.get("shows", {}).values():
        for breed in show.get("breeds", []) or []:
            if "judge" not in breed:
                continue
            current = breed.get("judge")
            cleaned = _clean_judge_name(current)
            if cleaned != current:
                changed = True
                if cleaned:
                    breed["judge"] = cleaned
                else:
                    breed.pop("judge", None)
    return changed

def _load_index(force=False):
    """Load the persisted breed index when missing or changed on disk."""
    global _show_index_mtime

    try:
        mtime = os.path.getmtime(INDEX_PATH)
    except FileNotFoundError:
        if force:
            _show_index.clear()
            _show_index.update({"shows": {}, "last_updated": 0})
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
        _show_index.clear()
        _show_index.update({
            "shows": data.get("shows", {}),
            "last_updated": data.get("last_updated", 0),
        })
        _show_index_mtime = mtime
        if _normalize_show_index_judges():
            _save_index()
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

def _index_summary(total_show_count=None):
    updated = _show_index.get("last_updated") or 0
    return {
        "last_updated": updated or None,
        "last_updated_iso": _utc_iso(updated),
        "indexed_show_count": len(_show_index.get("shows", {})),
        "total_show_count": total_show_count,
    }
