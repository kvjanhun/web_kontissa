import requests
import structlog

from .indexing import (
    _cached_result_breed_map, _show_from_index_for_search, _shows_with_cached_stats,
    _update_index_breed_judges,
)
from .shows import _get_show_list
from .store import _index_summary, _load_index, _show_index, _show_list_cache
from .utils import _clean_breed_data, _clean_judge_name

logger = structlog.get_logger(__name__)

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


def search_shows_data(query):
    query_variants = _search_query_variants(query)

    _load_index()

    try:
        shows = _get_show_list()
    except requests.RequestException:
        logger.warning("showlink_fetch_failed", endpoint="search", exc_info=True)
        shows = _show_list_cache["data"] or []

    enriched_shows = _shows_with_cached_stats(shows)
    searchable_shows = {str(show["id"]): show for show in enriched_shows}
    for sid, indexed_show in _show_index.get("shows", {}).items():
        if sid in searchable_shows:
            continue
        show = _show_from_index_for_search(sid, indexed_show)
        if show:
            searchable_shows[sid] = show

    results = []

    for sid, show in searchable_shows.items():
        sid = str(show["id"])
        show_text = " ".join([
            show.get("name", ""),
            show.get("title", ""),
            show.get("date", ""),
            show.get("month", ""),
        ]).lower()
        show_matches = any(q in show_text for q in query_variants)

        indexed_show = _show_index["shows"].get(sid)
        breed_matches = []
        judge_matches = []
        seen_breed_keys = set()
        indexed_breeds = {}
        if indexed_show:
            for breed_data in indexed_show.get("breeds", []):
                cleaned_breed = _clean_breed_data(breed_data)
                key = (str(cleaned_breed.get("group")), str(cleaned_breed.get("breed_id")))
                indexed_breeds[key] = cleaned_breed
                breed_name = cleaned_breed.get("name", "")
                judge_name = cleaned_breed.get("judge", "")
                if _text_matches_query_variants(breed_name, query_variants):
                    breed_matches.append(cleaned_breed)
                    seen_breed_keys.add(key)
                elif _text_matches_query_variants(judge_name, query_variants):
                    judge_matches.append(cleaned_breed)
                    seen_breed_keys.add(key)

        if not breed_matches:
            cached_breed_map = _cached_result_breed_map(sid)
            cached_judge_matches = []
            for key, cached_breed in cached_breed_map.items():
                merged_breed = dict(indexed_breeds.get(key) or {})
                merged_breed.update({k: v for k, v in cached_breed.items() if v not in ("", None)})
                if (
                    key not in seen_breed_keys
                    and _text_matches_query_variants(merged_breed.get("judge", ""), query_variants)
                ):
                    cached_judge_matches.append(merged_breed)
                    seen_breed_keys.add(key)
            if cached_judge_matches:
                judge_matches.extend(cached_judge_matches)
                _update_index_breed_judges(sid, cached_breed_map)

        if breed_matches:
            for breed_data in breed_matches:
                results.append({
                    "show": show,
                    "breed": breed_data,
                    "match": "breed",
                })
        elif judge_matches:
            judges = []
            for breed_data in judge_matches:
                judge = _clean_judge_name(breed_data.get("judge"))
                if judge and judge not in judges:
                    judges.append(judge)
            results.append({
                "show": show,
                "breed": None,
                "match": "judge",
                "judge": ", ".join(judges),
                "judge_match_count": len(judge_matches),
            })
        elif show_matches:
            results.append({
                "show": show,
                "breed": None,
                "match": "show",
            })

    return {
        "query": query,
        "results": results,
        "index": _index_summary(total_show_count=len(searchable_shows)),
    }
