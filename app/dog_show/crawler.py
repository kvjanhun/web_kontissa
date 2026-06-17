import time

import structlog

from .indexing import _index_entry_from_detail
from .parsers import _parse_show_detail
from .showlink import _fetch_page, _source_url
from .shows import _get_show_list
from .store import _index_summary, _load_index, _save_index, _show_detail_cache, _show_index
from .utils import _is_recent_show

logger = structlog.get_logger(__name__)

def _update_index_show(show):
    sid = show["id"]
    soup = _fetch_page(_source_url(sid))
    detail = _parse_show_detail(soup, sid)
    show_updated = time.time()

    _show_index["shows"][str(sid)] = _index_entry_from_detail(sid, show, detail, show_updated)
    _show_index["last_updated"] = show_updated
    _save_index()
    _show_detail_cache.pop(sid, None)

    logger.info("dog_crawler_indexed_show", show_id=sid, breed_count=len(detail["breeds"]))
    return detail

def _crawl_index_candidates(candidates, total_count, delay=1.5, reason="maintenance"):
    updated = 0
    failed = 0

    for idx, show in enumerate(candidates):
        sid = show["id"]
        try:
            _update_index_show(show)
            updated += 1
        except Exception as e:
            failed += 1
            logger.warning("dog_crawler_show_failed", show_id=sid, reason=reason, error=str(e))

        if delay and idx < len(candidates) - 1:
            time.sleep(delay)

    return {
        "total": total_count,
        "updated": updated,
        "failed": failed,
        "skipped": total_count - len(candidates),
        "index": _index_summary(total_show_count=total_count),
    }

def crawl_index_once(limit=None, delay=1.5):
    """Refresh missing and recent show breed indexes once.

    This is intentionally called by a standalone process, not by Flask workers.
    """
    _load_index()
    shows_list = _get_show_list()
    if not shows_list:
        return {"total": 0, "updated": 0, "skipped": 0}

    missing = []
    empty_indexed = []
    recent = []
    for show in shows_list:
        sid = str(show["id"])
        indexed_show = _show_index["shows"].get(sid)
        if not indexed_show:
            missing.append(show)
        elif not indexed_show.get("breeds") and not indexed_show.get("empty_breed_list_confirmed"):
            empty_indexed.append(show)
        elif _is_recent_show(show.get("month")):
            recent.append(show)

    to_update = empty_indexed + missing + recent

    if limit is not None:
        to_update = to_update[:limit]

    logger.info(
        "dog_crawler_updating_shows",
        count=len(to_update),
        missing=len(missing),
        empty_indexed=len(empty_indexed),
        recent=len(recent),
        total=len(shows_list),
    )

    summary = _crawl_index_candidates(to_update, len(shows_list), delay=delay, reason="maintenance")
    summary["missing_candidates"] = len(missing)
    summary["empty_candidates"] = len(empty_indexed)
    summary["recent_candidates"] = len(recent)
    return summary

def crawl_empty_index_once(limit=20, delay=0.5):
    """Repair stale empty breed indexes created by older parser versions."""
    _load_index()
    shows_list = _get_show_list()
    if not shows_list:
        return {"total": 0, "updated": 0, "failed": 0, "skipped": 0, "empty_candidates": 0}

    candidates = []
    for show in shows_list:
        indexed_show = _show_index["shows"].get(str(show["id"]))
        if indexed_show and not indexed_show.get("breeds") and not indexed_show.get("empty_breed_list_confirmed"):
            candidates.append(show)

    to_update = candidates
    if limit is not None:
        to_update = to_update[:limit]

    logger.info(
        "dog_crawler_repairing_empty_indexes",
        count=len(to_update),
        empty_candidates=len(candidates),
        total=len(shows_list),
    )

    summary = _crawl_index_candidates(to_update, len(shows_list), delay=delay, reason="empty_index_repair")
    summary["empty_candidates"] = len(candidates)
    return summary
