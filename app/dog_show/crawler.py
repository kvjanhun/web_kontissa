import time

import structlog

from .indexing import _index_entry_from_detail, _merge_persisted_result_state_into_breeds
from .parsers import _parse_show_detail
from .showlink import _fetch_page, _source_url
from .shows import _get_show_list
from .store import _index_states, _index_summary, _write_index_show
from .utils import _show_is_recent

logger = structlog.get_logger(__name__)

def _update_index_show(show):
    sid = show["id"]
    soup = _fetch_page(_source_url(sid))
    detail = _parse_show_detail(soup, sid)
    show_updated = time.time()

    # Detail pages carry no judges, so a re-index must fold the already-captured
    # judges and result flags back in before the wholesale row replacement.
    merged_breeds = _merge_persisted_result_state_into_breeds(sid, detail.get("breeds") or [])
    entry = _index_entry_from_detail(sid, show, {**detail, "breeds": merged_breeds}, show_updated)
    _write_index_show(sid, entry)

    logger.info("dog_crawler_indexed_show", show_id=sid, breed_count=len(detail["breeds"]))
    return detail

def _crawl_index_candidates(candidates, total_count, delay=1.5, reason="maintenance"):
    updated = 0
    failed = 0

    for idx, show in enumerate(candidates):
        sid = show["id"]
        try:
            logger.info("dog_crawler_show_start", show_id=sid, reason=reason)
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
    shows_list = _get_show_list()
    if not shows_list:
        logger.info("dog_crawler_index_pass_complete", total=0, updated=0, failed=0, skipped=0)
        return {"total": 0, "updated": 0, "skipped": 0}

    index_states = _index_states()
    missing = []
    empty_indexed = []
    recent = []
    for show in shows_list:
        state = index_states.get(str(show["id"]))
        if not state:
            missing.append(show)
        elif not state["breed_count"] and not state["empty_breed_list_confirmed"]:
            empty_indexed.append(show)
        elif _show_is_recent(show):
            recent.append(show)

    # Stalest-first within the recent bucket, so a bounded pass round-robins the
    # whole window across passes instead of re-fetching the same first-N shows
    # (list order) every time. Empty/missing shows keep absolute priority.
    recent.sort(key=lambda show: index_states[str(show["id"])]["updated_at"])

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
    logger.info("dog_crawler_index_pass_complete", **summary)
    return summary


