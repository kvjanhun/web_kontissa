import re
import time

import requests
import structlog

logger = structlog.get_logger(__name__)

_cached_commit_time = None
_cached_commit_timestamp = 0
CACHE_TTL = 60 * 60 * 6  # 6 hours

REPO = "kvjanhun/web_kontissa"
_stats_cache = {"data": None, "timestamp": 0}


def get_project_stats():
    """Fetch project stats from GitHub API with 6-hour cache and stale fallback."""
    now = time.time()
    if _stats_cache["data"] and now - _stats_cache["timestamp"] < CACHE_TTL:
        return _stats_cache["data"]

    base = f"https://api.github.com/repos/{REPO}"
    try:
        repo = requests.get(base, timeout=5)
        repo.raise_for_status()
        repo_data = repo.json()

        # Commit count: fetch 1 commit and read the last page from the Link header
        commits_res = requests.get(f"{base}/commits", params={"per_page": 1}, timeout=5)
        commits_res.raise_for_status()
        link = commits_res.headers.get("Link", "")
        match = re.search(r'page=(\d+)>; rel="last"', link)
        commit_count = int(match.group(1)) if match else 1

        langs_res = requests.get(f"{base}/languages", timeout=5)
        langs_res.raise_for_status()
        languages = list(langs_res.json().keys())  # already sorted by byte count desc

        data = {
            "commits": commit_count,
            "languages": languages[:5],
            "created_at": repo_data.get("created_at", "")[:10],
            "size_kb": repo_data.get("size", 0),
        }
        _stats_cache["data"] = data
        _stats_cache["timestamp"] = now
        return data
    except Exception:
        logger.warning("github_stats_failed", exc_info=True, has_stale=_stats_cache["data"] is not None)
        return _stats_cache["data"]

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
