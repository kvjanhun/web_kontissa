import datetime
import re
import time

import structlog

from .config import SHOW_DETAIL_TTL, FINNISH_MONTHS, SHOW_STATS_CACHE_TTL
from .store import (
    _indexed_show, _indexed_show_meta, _indexed_shows, _load_result_cache_doc,
    _show_list_cache, _write_index_show,
)
from .showlink import _source_url
from .utils import (
    _clean_breed_data, _clean_breed_list, _clean_judge_name,
    _parse_show_date,
    _result_doc_last_result_at, _result_live_plan, _show_age_days,
    _show_date_state, _show_is_recent, _show_live_phase, _show_result_availability, _utc_iso,
)

logger = structlog.get_logger(__name__)

def _show_list_item_for_id(show_id):
    sid = str(show_id)
    for show in _show_list_cache.get("data") or []:
        if str(show.get("id")) == sid:
            return show
    return None

def _indexed_show_as_list_item(show_id):
    meta = _indexed_show_meta(show_id)
    if not meta:
        return None
    return {
        "id": int(show_id),
        "date": meta.get("date", ""),
        "month": meta.get("month", ""),
    }

def _show_date_for_id(show_id):
    return _parse_show_date(_show_list_item_for_id(show_id) or _indexed_show_as_list_item(show_id))

def _show_result_availability_for_id(show_id, now=None):
    return _show_result_availability(
        _show_list_item_for_id(show_id) or _indexed_show_as_list_item(show_id),
        now=now,
    )

def _result_cache_doc_is_empty_result_cache(doc):
    if not doc or doc.get("status") != "complete":
        return False

    try:
        total_breeds = int(doc.get("total_breeds") or 0)
    except (TypeError, ValueError):
        total_breeds = 0

    return (
        total_breeds == 0
        and not doc.get("results")
        and not doc.get("completed_breeds")
    )

def _result_cache_doc_needs_result_refresh(show_id, doc, now=None):
    if not _result_cache_doc_is_empty_result_cache(doc):
        return False

    indexed_show = _indexed_show(show_id)
    indexed_breeds = indexed_show.get("breeds", []) if indexed_show else []
    return (
        bool(_result_breeds_for_cache(show_id, indexed_breeds, now=now))
        or _indexed_result_flags_need_refresh(show_id, indexed_show, now=now)
    )

def _stats_now_for_today(today):
    if not today:
        return None
    return datetime.datetime.combine(today, datetime.time(hour=12))

def _stats_timestamp_for_today(today):
    return _stats_now_for_today(today).timestamp() if today else time.time()

def _result_count_from_cache_doc(show_id, entry_count=None, today=None, doc=None):
    # Callers that already hold the result doc (e.g. _show_stats_from_index) pass
    # it in so we don't reconstruct the whole-show doc from SQLite a second time.
    doc = doc if doc is not None else _load_result_cache_doc(show_id)
    if not doc:
        return None

    now = _stats_now_for_today(today)
    if _result_cache_doc_needs_result_refresh(show_id, doc, now=now):
        return None

    try:
        count = len(doc.get("results") or [])
    except TypeError:
        return None

    if isinstance(entry_count, int):
        return min(count, entry_count)
    return count

def _show_item_for_stats(show_id, show=None, indexed_show=None):
    if show:
        return show

    if indexed_show:
        return {
            "id": int(show_id),
            "date": indexed_show.get("date", ""),
            "month": indexed_show.get("month", ""),
        }
    return _show_list_item_for_id(show_id)

def _compute_show_stats(show_id, indexed_show, show=None, today=None):
    if not indexed_show:
        return None

    breeds = indexed_show.get("breeds") or []
    if not breeds:
        return None

    entry_count = 0
    entry_count_known = False
    result_breed_count = 0

    for breed in breeds:
        try:
            entry_count += int(breed.get("count"))
            entry_count_known = True
        except (TypeError, ValueError):
            continue

    show_item = _show_item_for_stats(show_id, show=show, indexed_show=indexed_show)
    show_state = _show_date_state(show_item, today=today)
    live_finished_by = None
    result_doc = None
    if show_state == "live":
        result_doc = _load_result_cache_doc(show_id)
        # Same terminal decision the result-cache TTL uses, so the "still live?"
        # badge and the crawler never disagree. A live show flips to "past" once
        # its terminal award is captured and confirmed stable (main BIS + every
        # group's RYP, or entry completion for a finals-less show) — never on
        # breed completion alone while the finals are still to come.
        plan = _result_live_plan(
            show_item, result_doc, breeds, now=_stats_timestamp_for_today(today)
        )
        if plan["phase"] in ("settled", "settled_incomplete"):
            live_finished_by = "incomplete" if plan["phase"] == "settled_incomplete" else (
                "bis" if plan["expects_main_bis"] else "entries"
            )
            show_state = "past"
    result_breeds_for_cache = _result_breeds_for_cache(
        show_id,
        breeds,
        now=_stats_now_for_today(today),
    ) if show_state == "live" else _result_breeds_with_results(breeds)
    result_breed_keys = {
        (str(breed.get("group")), str(breed.get("breed_id")))
        for breed in result_breeds_for_cache
    }

    for breed in breeds:
        if breed.get("has_results"):
            result_breed_count += 1
        elif (str(breed.get("group")), str(breed.get("breed_id"))) in result_breed_keys:
            result_breed_count += 1

    updated = indexed_show.get("updated_at") or 0
    availability = _show_result_availability(
        show_item,
        now=_stats_now_for_today(today) if today else None,
    )
    is_live = False
    is_paused = False
    if show_state == "live":
        # result_doc is loaded above whenever the date-state is live; a live show
        # in its multi-day nightly/evening lull reads as "paused" (Jatkuu) rather
        # than actively "Käynnissä".
        phase = _show_live_phase(
            show_item,
            now=_stats_now_for_today(today) if today else None,
            availability=availability,
            last_result_at=_result_doc_last_result_at(result_doc),
        )
        if phase == "paused":
            is_paused = True
        else:
            is_live = availability.get("can_fetch", True)
    stats = {
        "indexed": True,
        "breed_count": len(breeds),
        "entry_count": entry_count if entry_count_known else None,
        "result_breed_count": result_breed_count,
        "show_state": show_state,
        "is_live": is_live,
        "is_paused": is_paused,
        "updated_at": updated or None,
        "updated_at_iso": _utc_iso(updated),
    }
    if live_finished_by:
        stats["live_finished_by"] = live_finished_by
    if show_state == "live":
        result_count = _result_count_from_cache_doc(
            show_id,
            entry_count=entry_count if entry_count_known else None,
            today=today,
            doc=result_doc,
        )
        if result_count is not None:
            stats["result_count"] = result_count
    return stats

# Per-show stats cache. `/api/dog/shows` is polled every 15s by every open /dog
# client whenever a live show is present, and computing a live show's stats
# reconstructs its whole-show result doc (thousands of rows) from SQLite. Caching
# the computed stats briefly decouples that cost from the poll rate. Bypassed when
# an explicit `today` is passed (tests), and cleared per-test in the suite.
_show_stats_cache = {}

def _show_stats_from_index(show_id, show=None, today=None, indexed_show=None):
    if today is not None:
        return _compute_show_stats(
            show_id, indexed_show or _indexed_show(show_id), show=show, today=today,
        )

    try:
        key = int(show_id)
    except (TypeError, ValueError):
        return None

    now = time.time()
    cached = _show_stats_cache.get(key)
    if cached and (now - cached["ts"]) < SHOW_STATS_CACHE_TTL:
        return cached["stats"]

    stats = _compute_show_stats(
        show_id, indexed_show if indexed_show is not None else _indexed_show(show_id), show=show,
    )
    _show_stats_cache[key] = {"stats": stats, "ts": now}
    return stats

def _shows_with_cached_stats(shows):
    # Bulk-load the index entries the stats cache doesn't already cover, so a
    # 15s list poll costs two queries instead of one per show.
    now = time.time()
    uncached_ids = [
        show.get("id") for show in shows
        if not (
            (cached := _show_stats_cache.get(show.get("id")))
            and (now - cached["ts"]) < SHOW_STATS_CACHE_TTL
        )
    ]
    indexed = _indexed_shows(uncached_ids) if uncached_ids else {}

    enriched = []
    for show in shows:
        item = dict(show)
        stats = _show_stats_from_index(
            show.get("id"), show=show,
            indexed_show=indexed.get(str(show.get("id"))),
        )
        if stats:
            item["stats"] = stats
        enriched.append(item)
    return enriched

def _show_from_index_for_search(show_id, indexed_meta, indexed_show=None):
    try:
        sid = int(show_id)
    except (TypeError, ValueError):
        return None

    title = indexed_meta.get("title", "")
    show = {
        "id": sid,
        "date": indexed_meta.get("date", ""),
        "name": indexed_meta.get("name") or title,
        "title": title,
        "month": indexed_meta.get("month", ""),
        "source_url": indexed_meta.get("source_url") or _source_url(sid),
    }
    stats = _show_stats_from_index(sid, show=show, indexed_show=indexed_show)
    if stats:
        show["stats"] = stats
    return show

def _breed_identity_from_result(result):
    breed_obj = result.get("breedObj") or {}
    group = result.get("breedGroup") or breed_obj.get("group")
    breed_id = result.get("breedId") or breed_obj.get("breed_id")
    if not group or not breed_id:
        return None
    return str(group), str(breed_id)

def _cached_result_breed_state(show_id):
    doc = _load_result_cache_doc(show_id)
    if not doc:
        return {}

    state = {}
    for key, breed_data in (doc.get("completed_breeds") or {}).items():
        if not isinstance(breed_data, dict) or ":" not in str(key):
            continue
        group, breed_id = str(key).split(":", 1)
        try:
            result_count = int(breed_data.get("result_count") or 0)
        except (TypeError, ValueError):
            result_count = 0
        state[(group, breed_id)] = {
            "has_results": result_count > 0,
            "judge": _clean_judge_name(breed_data.get("judge")),
        }

    for result in doc.get("results") or []:
        key = _breed_identity_from_result(result)
        if not key:
            continue
        breed_obj = _clean_breed_data(result.get("breedObj") or {})
        item = state.setdefault(key, {})
        item["has_results"] = True
        if breed_obj.get("judge"):
            item["judge"] = breed_obj.get("judge")
    return state

def _merge_persisted_result_state_into_breeds(show_id, breeds):
    """Fold already-captured judges and result flags into a freshly-parsed breed
    list before it replaces the show's index rows — a detail page never carries
    judges, so a re-index without this merge would wipe them."""
    state = {}
    existing = _indexed_show(show_id) or {}
    for breed in existing.get("breeds", []) or []:
        group = breed.get("group")
        breed_id = breed.get("breed_id")
        if not group or not breed_id:
            continue
        key = (str(group), str(breed_id))
        state[key] = {
            "has_results": breed.get("has_results") is True,
            "judge": _clean_judge_name(breed.get("judge")),
        }

    for key, cached_state in _cached_result_breed_state(show_id).items():
        item = state.setdefault(key, {})
        if cached_state.get("has_results"):
            item["has_results"] = True
        if cached_state.get("judge"):
            item["judge"] = cached_state.get("judge")

    if not state:
        return breeds

    merged = []
    for breed in breeds or []:
        item = dict(breed)
        key = (str(item.get("group")), str(item.get("breed_id")))
        persisted = state.get(key)
        if persisted:
            if persisted.get("has_results"):
                item["has_results"] = True
            if persisted.get("judge"):
                item["judge"] = persisted.get("judge")
        merged.append(item)
    return merged

def _parse_show_meta_from_title(title):
    if not title:
        return {}
    # Matches ranges like 20.-21.06.2026 or 31.05.-01.06.2026
    match = re.match(r"^(\d{1,2}(?:\.\d{1,2})?\.?\s*-\s*\d{1,2}\.(\d{1,2})\.(\d{4}))\s+(.+)$", title.strip())
    if not match:
        # Matches single date like 21.06.2026
        match = re.match(r"^(\d{1,2}\.(\d{1,2})\.(\d{4}))\s+(.+)$", title.strip())

    if match:
        full_date_str, month_str, year_str, name = match.groups()
        date_part = full_date_str.replace(f".{year_str}", "")
        if not date_part.endswith("."):
            date_part += "."

        month_idx = int(month_str) - 1
        if 0 <= month_idx < 12:
            month = f"{FINNISH_MONTHS[month_idx]} {year_str}"
        else:
            month = ""

        return {
            "name": name.strip(),
            "date": date_part,
            "month": month
        }
    return {}

def _persist_show_detail_to_index(show_id, detail, updated_at):
    breeds = detail.get("breeds") or []
    if not breeds:
        return

    existing = _indexed_show_meta(show_id) or {}
    list_item = _show_list_item_for_id(show_id) or {}
    meta = _parse_show_meta_from_title(detail.get("title", ""))

    entry = _index_entry_from_detail(
        show_id,
        {
            "name": list_item.get("name") or existing.get("name") or meta.get("name") or detail.get("title", ""),
            "date": list_item.get("date") or existing.get("date") or meta.get("date") or "",
            "month": list_item.get("month") or existing.get("month") or meta.get("month") or "",
        },
        {
            **detail,
            "breeds": _merge_persisted_result_state_into_breeds(show_id, breeds),
        },
        updated_at,
    )
    _write_index_show(show_id, entry)

def _index_entry_from_detail(show_id, show, detail, updated_at):
    entry = {
        "title": detail.get("title") or show.get("title", "") or show.get("name", ""),
        "name": show.get("name", ""),
        "date": show.get("date", ""),
        "month": show.get("month", ""),
        "source_url": detail.get("source_url") or _source_url(show_id),
        "breeds": detail.get("breeds") or [],
        "updated_at": updated_at,
        "updated_at_iso": _utc_iso(updated_at),
    }
    if not entry["breeds"]:
        entry["empty_breed_list_confirmed"] = True
    return entry

def _result_breeds_from_index(show_id):
    indexed_show = _indexed_show(show_id)
    if not indexed_show:
        return []
    return _clean_breed_list(indexed_show.get("breeds", []))

def _result_breeds_with_results(breeds):
    return [
        breed for breed in breeds
        if breed.get("has_results") and breed.get("group") and breed.get("breed_id")
    ]

def _single_breed_result_probe_candidates(show_id, breeds, now=None):
    candidates = [
        breed for breed in _clean_breed_list(breeds)
        if breed.get("group") and breed.get("breed_id")
    ]
    if len(candidates) != 1:
        return []

    availability = _show_result_availability_for_id(show_id, now=now)
    if not availability.get("can_fetch", True):
        return []
    return candidates

def _result_breeds_for_cache(show_id, breeds, now=None):
    result_breeds = _result_breeds_with_results(breeds)
    if result_breeds:
        return result_breeds
    return _single_breed_result_probe_candidates(show_id, breeds, now=now)

def _mark_single_probe_breed_result_available(show_id, breeds, now=None):
    cleaned = _clean_breed_list(breeds)
    if _result_breeds_with_results(cleaned):
        return cleaned

    candidates = _single_breed_result_probe_candidates(show_id, cleaned, now=now)
    if not candidates:
        return cleaned

    candidate = candidates[0]
    for breed in cleaned:
        if (
            str(breed.get("group")) == str(candidate.get("group"))
            and str(breed.get("breed_id")) == str(candidate.get("breed_id"))
        ):
            breed["has_results"] = True
    return cleaned

def _indexed_result_flags_need_refresh(show_id, indexed_show=None, now=None):
    indexed_show = indexed_show or _indexed_show(show_id)
    if not indexed_show:
        return False

    breeds = indexed_show.get("breeds") or []
    if not breeds or _result_breeds_with_results(breeds):
        return False

    if not _is_show_recent_by_id(show_id):
        return False

    updated = indexed_show.get("updated_at") or 0
    if updated and (time.time() - updated) < SHOW_DETAIL_TTL:
        return False

    availability = _show_result_availability_for_id(show_id, now=now)
    return availability.get("can_fetch", True)

def _is_show_recent_by_id(show_id):
    return _show_is_recent(_show_list_item_for_id(show_id) or _indexed_show_as_list_item(show_id))

def _show_detail_from_index(show_id):
    indexed_show = _indexed_show(show_id)
    if not indexed_show or not indexed_show.get("breeds"):
        return None

    updated_at = indexed_show.get("updated_at") or time.time()
    breeds = _mark_single_probe_breed_result_available(show_id, indexed_show.get("breeds", []))
    return {
        "id": int(show_id),
        "title": indexed_show.get("title") or indexed_show.get("name", ""),
        "date": indexed_show.get("date", ""),
        "month": indexed_show.get("month", ""),
        "breeds": breeds,
        "source_url": indexed_show.get("source_url") or _source_url(show_id),
        "fetched_at": updated_at,
        "fetched_at_iso": _utc_iso(updated_at),
        "cache": {
            "status": "indexed",
            "source": "dog_show_index",
            "updated_at": updated_at,
            "updated_at_iso": _utc_iso(updated_at),
        },
    }
