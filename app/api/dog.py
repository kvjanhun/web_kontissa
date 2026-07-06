import requests
import structlog
from flask import Blueprint, jsonify, request as flask_request

from app import limiter
from app.dog_show.config import RESULT_RETRY_AFTER_SECONDS
from app.dog_show.indexing import (
    _show_detail_from_index, _show_result_availability_for_id,
    _show_stats_from_index, _shows_with_cached_stats,
)
from app.dog_show.result_cache import (
    _all_results_response, _breed_results_from_all_results_cache,
    _enrich_breeds_with_result_progress, _queue_live_result_cache_refresh,
    _queue_live_result_cache_refreshes, _result_cache_progress,
)
from app.dog_show.search import search_shows_data
from app.dog_show.shows import _get_show_list
from app.dog_show.store import (
    _index_summary, _load_result_cache_doc, _queue_result_cache_job, _show_list_cache,
)

logger = structlog.get_logger(__name__)

dog_bp = Blueprint('dog', __name__)

def _results_not_ready_response(show_id, availability, reason=None):
    reason_messages = {
        "future_show": "Tuloksia ei haeta vielä ennen näyttelypäivän aamua.",
        "show_morning": "Tuloksia ei haeta vielä ennen näyttelypäivän klo 6:ta.",
        "show_night": "Tuloksia ei päivitetä yöaikaan (klo 21–6). Aiemmin haetut tulokset näkyvät yhä.",
        "cache_warming": "Tuloksia haetaan parhaillaan taustalla. Yritä hetken kuluttua uudelleen.",
    }
    reason = reason or availability.get("reason")
    return {
        "show_id": int(show_id),
        "status": "not_ready",
        "reason": reason,
        "message": reason_messages.get(
            reason,
            "Tuloksia ei haeta vielä tälle näyttelylle.",
        ),
        "availability": availability,
    }

def _attach_show_detail_stats(show_id, data):
    stats = _show_stats_from_index(show_id)
    if stats:
        data["stats"] = stats


@dog_bp.route("/api/dog/shows")
@limiter.limit("30/minute")
def show_list():
    try:
        shows = _get_show_list()
        _queue_live_result_cache_refreshes(shows)
        return jsonify({
            "shows": _shows_with_cached_stats(shows),
            "index": _index_summary(total_show_count=len(shows)),
        })
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="shows", exc_info=True)
        if _show_list_cache["data"]:
            shows = _show_list_cache["data"]
            _queue_live_result_cache_refreshes(shows)
            return jsonify({
                "shows": _shows_with_cached_stats(shows),
                "index": _index_summary(total_show_count=len(shows)),
            })
        return jsonify({"error": "Failed to fetch show list", "detail": str(exc)}), 502
    except Exception:
        logger.exception("show_list_error")
        return jsonify({"error": "Internal server error"}), 500


@dog_bp.route("/api/dog/shows/<int:show_id>")
@limiter.limit("30/minute")
def show_detail(show_id):
    # Served from the persisted breed index (dog.db) only. The web tier never
    # fetches Showlink pages for detail; a show missing from the index (a brand
    # new listing) is picked up by the crawler's index pass within minutes.
    try:
        indexed = _show_detail_from_index(show_id)
        if indexed:
            _enrich_breeds_with_result_progress(show_id, indexed.get("breeds", []))
            _queue_live_result_cache_refresh(show_id)
            _attach_show_detail_stats(show_id, indexed)
            return jsonify(indexed)

        return jsonify({
            "show_id": int(show_id),
            "status": "not_indexed",
            "message": "Näyttelyn tietoja ei ole vielä haettu. Yritä hetken kuluttua uudelleen.",
        }), 425
    except Exception:
        logger.exception("show_detail_error", show_id=show_id)
        return jsonify({"error": "Internal server error"}), 500


@dog_bp.route("/api/dog/shows/<int:show_id>/results")
@limiter.limit("30/minute")
def breed_results(show_id):
    group = flask_request.args.get("group", "")
    breed = flask_request.args.get("breed", "")

    if not group or not breed:
        return jsonify({"error": "Missing required query parameters: group, breed"}), 400

    if not group.isdigit() or not breed.isdigit():
        return jsonify({"error": "Parameters group and breed must be numeric integers"}), 400

    group_num = int(group)
    breed_num = int(breed)
    if group_num < 1 or group_num > 10 or breed_num < 1:
        return jsonify({"error": "Parameters group and breed are outside the supported range"}), 400

    try:
        persisted = _breed_results_from_all_results_cache(show_id, group, breed)
        if persisted:
            return jsonify(persisted)

        # Not in the whole-show cache. The web tier does not fetch Showlink result
        # pages itself; outside the fetch window this is a plain "not ready", and
        # inside it the queued job lets the crawler capture the breed shortly.
        availability = _show_result_availability_for_id(show_id)
        if not availability.get("can_fetch", True):
            return jsonify(_results_not_ready_response(show_id, availability)), 425

        _queue_result_cache_job(show_id, reason="breed-request")
        return jsonify(_results_not_ready_response(
            show_id, availability, reason="cache_warming",
        )), 425
    except Exception:
        logger.exception("breed_results_error", show_id=show_id, group=group, breed=breed)
        return jsonify({"error": "Internal server error"}), 500


@dog_bp.route("/api/dog/shows/<int:show_id>/all-results")
@limiter.limit("20/minute")
def show_all_results(show_id):
    try:
        availability = _show_result_availability_for_id(show_id)
        cached = _all_results_response(show_id, allow_stale=True)
        if cached:
            cached["availability"] = availability
            if cached.get("cache", {}).get("stale") and availability.get("can_fetch", True):
                _queue_result_cache_job(show_id, reason="stale-refresh")
            return jsonify(cached)

        if not availability.get("can_fetch", True):
            return jsonify(_results_not_ready_response(show_id, availability)), 425

        job = _queue_result_cache_job(show_id, reason="user")
        doc = _load_result_cache_doc(show_id)
        return jsonify({
            "show_id": show_id,
            "status": "warming",
            "message": "Whole-show result cache is being prepared.",
            "retry_after": RESULT_RETRY_AFTER_SECONDS,
            "progress": _result_cache_progress(show_id, doc=doc, job=job),
            "availability": availability,
        }), 202
    except Exception as e:
        logger.exception("show_all_results_error", show_id=show_id)
        return jsonify({"error": "Failed to load show all results cache", "detail": str(e)}), 500


@dog_bp.route("/api/dog/search")
@limiter.limit("30/minute")
def search_shows():
    query = flask_request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing required query parameter: q"}), 400

    try:
        return jsonify(search_shows_data(query))
    except Exception:
        logger.exception("search_error")
        return jsonify({"error": "Internal server error"}), 500
