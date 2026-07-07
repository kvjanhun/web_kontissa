"""Cross-show dog profile assembly (the /api/dog/dogs endpoint).

Reads only captured rows from dog.db: every result row anchored to one
Kennelliitto registration number (`dog_result.reg_id`), each paired with its
show's index metadata and sorted newest show first, plus owner enrichment from
the honor-roll award rows (the only place the captured data ties an owner to a
dog). Read-only, one request per profile — no Showlink fetching, no caches.
"""

import datetime

import structlog

from .search import _show_start_date
from .showlink import _source_url
from .store import _breed_awards_for_shows, _dog_results_by_reg_id, _indexed_show_metas

logger = structlog.get_logger(__name__)


def _entry_recency_key(entry):
    """Newest-first ordering for profile entries: dated shows before undated,
    then start date, then show id — the same recency semantics search uses."""
    show = entry.get("show") or {}
    try:
        show_id = int(show.get("id"))
    except (TypeError, ValueError):
        show_id = 0
    start_date = _show_start_date(show)
    return (start_date is not None, start_date or datetime.date.min, show_id)


def _profile_owner(entries, awards):
    """The dog's owner as of its newest honor-roll appearance, or "".

    Award rows carry no reg_id, so the match is (show, breed, winner name);
    entries are scanned newest-first so an ownership change shows the current
    owner."""
    award_owners = {}
    for award in awards:
        if not award.get("owner"):
            continue
        key = (
            award.get("show_id"),
            award.get("fci_group") or "",
            award.get("breed_id") or "",
            str(award.get("name") or "").casefold(),
        )
        award_owners.setdefault(key, award["owner"])
    for entry in entries:
        key = (
            (entry.get("show") or {}).get("id"),
            entry.get("fci_group") or "",
            entry.get("breed_id") or "",
            str(entry.get("name") or "").casefold(),
        )
        owner = award_owners.get(key)
        if owner:
            return owner
    return ""


def dog_profile_data(reg_id):
    """Assemble the /api/dog/dogs payload for one registration number, or None
    when no captured result row carries it."""
    rows = _dog_results_by_reg_id(reg_id)
    if not rows:
        return None

    show_ids = []
    for row in rows:
        if row["show_id"] not in show_ids:
            show_ids.append(row["show_id"])
    metas = _indexed_show_metas(show_ids)

    entries = []
    for row in rows:
        sid = int(row["show_id"])
        meta = metas.get(str(sid)) or {}
        title = meta.get("title", "")
        entry = {key: value for key, value in row.items() if key != "show_id"}
        entry["show"] = {
            "id": sid,
            "name": meta.get("name") or title,
            "title": title,
            "date": meta.get("date", ""),
            "month": meta.get("month", ""),
            "source_url": meta.get("source_url") or _source_url(sid),
        }
        entries.append(entry)

    # Stable sort: entries within one show keep their captured (seq) order.
    entries.sort(key=_entry_recency_key, reverse=True)

    newest = entries[0]
    gender = next((e["gender"] for e in entries if e.get("gender")), "")
    owner = _profile_owner(entries, _breed_awards_for_shows(show_ids))

    return {
        "reg_id": str(reg_id).strip(),
        "name": newest.get("name", ""),
        "gender": gender,
        "reg_url": next((e["reg_url"] for e in entries if e.get("reg_url")), ""),
        "owner": owner or None,
        "show_count": len(show_ids),
        "result_count": len(entries),
        "entries": entries,
    }
