import requests
import structlog

from .indexing import _show_from_index_for_search, _show_stats_from_index
from .shows import _get_show_list
from .store import (
    _index_summary, _indexed_ids_among, _indexed_show, _indexed_shows,
    _search_breed_award_owners, _search_dog_results_by_name,
    _search_index_breeds, _search_index_judges, _search_index_show_ids,
    _show_list_cache,
)
from .utils import _clean_judge_name

logger = structlog.get_logger(__name__)

# Dog-name / owner search scans the whole result history in SQL, so it only kicks
# in for queries of at least this length (the show/breed/judge index search keeps
# its 2-char minimum) and is bounded to this many shows per entity type.
SEARCH_ENTITY_MIN_LENGTH = 3
SEARCH_ENTITY_SHOW_LIMIT = 20

def _search_query_variants(query):
    variants = []
    for value in (query, _clean_judge_name(query)):
        q = value.lower().strip()
        if q and q not in variants:
            variants.append(q)
    return variants

def _text_matches_query_variants(text, variants):
    haystack = str(text or "").lower()
    return any(query in haystack for query in variants)

def _list_show_text(show):
    return " ".join([
        show.get("name", ""),
        show.get("title", ""),
        show.get("date", ""),
        show.get("month", ""),
    ])


def search_shows_data(query):
    """Assemble /api/dog/search results from SQL index scans.

    The index queries (breed name, judge, show text) run against dog.db; this
    function only groups the matches by show and ranks them: per show a breed
    match outranks a judge match outranks a show-text match, and shows from the
    current Showlink list come first (in list order), then indexed-only shows
    newest-first. Cross-show dog/owner matches are appended last.
    """
    query_variants = _search_query_variants(query)

    try:
        shows = _get_show_list()
    except requests.RequestException:
        logger.warning("showlink_fetch_failed", endpoint="search", exc_info=True)
        shows = _show_list_cache["data"] or []

    list_shows_by_id = {str(show["id"]): show for show in shows}

    breed_matches = {}
    for show_id, breed in _search_index_breeds(query_variants):
        breed_matches.setdefault(str(show_id), []).append(breed)

    judge_matches = {}
    for show_id, breed in _search_index_judges(query_variants):
        judge_matches.setdefault(str(show_id), []).append(breed)

    show_matches = {str(show_id) for show_id in _search_index_show_ids(query_variants)}
    # The live list can carry shows (or list-only wording) not indexed yet.
    show_matches.update(
        sid for sid, show in list_shows_by_id.items()
        if _text_matches_query_variants(_list_show_text(show), query_variants)
    )

    matched_ids = set(breed_matches) | set(judge_matches) | show_matches
    ordered_ids = [sid for sid in list_shows_by_id if sid in matched_ids]
    ordered_ids += sorted(
        (sid for sid in matched_ids if sid not in list_shows_by_id),
        key=lambda sid: int(sid),
        reverse=True,
    )

    # A broad breed query can match hundreds of shows; load their index entries
    # in one bulk read instead of one query per matched show.
    matched_index_entries = _indexed_shows(sorted(matched_ids)) if matched_ids else {}

    show_payloads = {}

    def _show_payload(sid):
        if sid in show_payloads:
            return show_payloads[sid]
        indexed_entry = matched_index_entries.get(sid)
        if indexed_entry is None and sid not in matched_ids:
            indexed_entry = _indexed_show(sid)
        list_show = list_shows_by_id.get(sid)
        if list_show:
            payload = dict(list_show)
            stats = _show_stats_from_index(sid, show=list_show, indexed_show=indexed_entry)
            if stats:
                payload["stats"] = stats
        else:
            payload = (
                _show_from_index_for_search(sid, indexed_entry, indexed_show=indexed_entry)
                if indexed_entry else None
            )
        show_payloads[sid] = payload
        return payload

    results = []
    for sid in ordered_ids:
        show = _show_payload(sid)
        if not show:
            continue

        if sid in breed_matches:
            for breed_data in breed_matches[sid]:
                results.append({
                    "show": show,
                    "breed": breed_data,
                    "match": "breed",
                })
        elif sid in judge_matches:
            judges = []
            for breed_data in judge_matches[sid]:
                judge = _clean_judge_name(breed_data.get("judge"))
                if judge and judge not in judges:
                    judges.append(judge)
            results.append({
                "show": show,
                "breed": None,
                "match": "judge",
                "judge": ", ".join(judges),
                "judge_match_count": len(judge_matches[sid]),
            })
        else:
            results.append({
                "show": show,
                "breed": None,
                "match": "show",
            })

    _append_entity_matches(results, _show_payload, query)

    list_only_count = len(set(list_shows_by_id) - {
        str(sid) for sid in _indexed_ids_among(list(list_shows_by_id))
    })
    summary = _index_summary()
    summary["total_show_count"] = summary["indexed_show_count"] + list_only_count

    return {
        "query": query,
        "results": results,
        "index": summary,
    }


def _append_entity_matches(results, show_payload, query):
    """Append cross-show dog-name and owner matches after the show/breed/judge
    results, so those keep ranking first. Each hit is one result per show carrying
    a `match` type ("dog"/"owner") and a representative name + count. Skips shows
    without a resolvable payload (defensive — every captured show is indexed)."""
    if len(str(query or "").strip()) < SEARCH_ENTITY_MIN_LENGTH:
        return

    for hit in _search_dog_results_by_name(query, limit=SEARCH_ENTITY_SHOW_LIMIT):
        show = show_payload(str(hit["show_id"]))
        if not show:
            continue
        results.append({
            "show": show,
            "breed": None,
            "match": "dog",
            "dog": hit["name"],
            "dog_match_count": hit["count"],
        })

    for hit in _search_breed_award_owners(query, limit=SEARCH_ENTITY_SHOW_LIMIT):
        show = show_payload(str(hit["show_id"]))
        if not show:
            continue
        results.append({
            "show": show,
            "breed": None,
            "match": "owner",
            "owner": hit["owner"],
            "owner_match_count": hit["count"],
        })
