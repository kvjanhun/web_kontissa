import time

from .config import BASE_URL, SHOW_LIST_TTL
from .parsers import _parse_show_list
from .showlink import _fetch_page
from .store import _show_list_cache
from .utils import _fetch_window_open

def _get_show_list():
    """Return cached show list, refreshing if stale.

    Gated here rather than at the call sites so request paths are covered too:
    a visitor at 02:00 must not trigger a Showlink fetch. Outside the fetch
    window the cached list is served however stale it is — the show list only
    changes when a new show is announced, which never needs to be known within
    the hour, let alone overnight.

    A cold cache is the one exception: a process that starts outside the window
    has nothing to serve, so it populates once. That is a single request per
    process start, not polling.
    """
    now = time.time()
    cached = _show_list_cache["data"]
    if cached and (now - _show_list_cache["ts"]) < SHOW_LIST_TTL:
        return cached
    if cached and not _fetch_window_open(now):
        return cached

    soup = _fetch_page(BASE_URL)
    shows = _parse_show_list(soup)

    _show_list_cache["data"] = shows
    _show_list_cache["ts"] = now
    return shows
