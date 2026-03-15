import time

import requests
import structlog

logger = structlog.get_logger(__name__)

_cached_commit_time = None
_cached_commit_timestamp = 0
CACHE_TTL = 60 * 60 * 6  # 6 hours

def get_latest_commit_date():
    """Return latest commit date (ISO string) with 6-hour cache and stale fallback."""
    global _cached_commit_time, _cached_commit_timestamp
    now = time.time()

    if _cached_commit_time and now - _cached_commit_timestamp < CACHE_TTL:
        return _cached_commit_time

    url = "https://api.github.com/repos/kvjanhun/web_kontissa/commits/main"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        commit_date = response.json()["commit"]["author"]["date"]
        _cached_commit_time = commit_date
        _cached_commit_timestamp = now
        return commit_date
    except Exception:
        logger.warning("github_api_failed", exc_info=True, has_stale_cache=_cached_commit_time is not None)
        return _cached_commit_time
