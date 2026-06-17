import time

from .config import BASE_URL, SHOW_LIST_TTL
from .parsers import _parse_show_list
from .showlink import _fetch_page
from .store import _show_list_cache

def _get_show_list():
    """Return cached show list, refreshing if stale."""
    now = time.time()
    if _show_list_cache["data"] and (now - _show_list_cache["ts"]) < SHOW_LIST_TTL:
        return _show_list_cache["data"]

    soup = _fetch_page(BASE_URL)
    shows = _parse_show_list(soup)

    _show_list_cache["data"] = shows
    _show_list_cache["ts"] = now
    return shows
