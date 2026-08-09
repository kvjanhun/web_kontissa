import time

import requests
import structlog

logger = structlog.get_logger(__name__)

_cached_commit_time = None
_cached_commit_timestamp = 0
_failed_attempt_timestamp = 0
CACHE_TTL = 60 * 60 * 6  # 6 hours
# Back off after a failure instead of retrying on every request. Without this a
# GitHub outage or rate-limit (unauthenticated = 60 req/h per IP) turns every
# /api/meta and /sitemap.xml hit into a fresh 5-second blocking call, so a crawler
# walking the sitemap can tie up a Gunicorn worker per request.
FAILURE_RETRY_TTL = 60 * 5  # 5 minutes


def get_latest_commit_date():
    """Return latest commit date (ISO string) with 6-hour cache and stale fallback."""
    global _cached_commit_time, _cached_commit_timestamp, _failed_attempt_timestamp
    now = time.time()

    if _cached_commit_time and now - _cached_commit_timestamp < CACHE_TTL:
        return _cached_commit_time

    # The last attempt failed and the backoff hasn't elapsed — serve the stale value
    # (or None) rather than re-dialling on every single request.
    if _failed_attempt_timestamp and now - _failed_attempt_timestamp < FAILURE_RETRY_TTL:
        return _cached_commit_time

    url = "https://api.github.com/repos/kvjanhun/web_kontissa/commits/main"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        commit_date = response.json()["commit"]["author"]["date"]
        _cached_commit_time = commit_date
        _cached_commit_timestamp = now
        _failed_attempt_timestamp = 0  # recovered — drop the backoff
        return commit_date
    except Exception:
        _failed_attempt_timestamp = now
        logger.warning("github_api_failed", exc_info=True, has_stale_cache=_cached_commit_time is not None)
        return _cached_commit_time


# Route prefixes owned by the Nuxt client router. Paths under these keep a 200 from
# the catch-all so client-side routing still works for routes that aren't
# pre-rendered (e.g. /recipes/<slug>); everything else is a genuine 404 rather than
# a soft one. Keep in sync with frontend/pages/ and the redirect routeRules in
# frontend/nuxt.config.ts.
SPA_ROUTE_PREFIXES = (
    "/login",
    "/admin",
    "/recipes",
    "/dog",
    "/about",    # routeRules redirect → /
    "/contact",  # routeRules redirect → /
)


def is_known_route(path):
    """True if `path` is the site root or sits under a known SPA route prefix.

    Accepts both the leading-slash form used by API payloads and the stripped form
    Flask hands to a `<path:path>` converter.
    """
    if not isinstance(path, str):
        return False
    trimmed = path.strip("/")
    if not trimmed:
        return True  # site root
    normalized = "/" + trimmed
    return any(
        normalized == prefix or normalized.startswith(prefix + "/")
        for prefix in SPA_ROUTE_PREFIXES
    )
