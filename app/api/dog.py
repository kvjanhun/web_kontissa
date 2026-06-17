import datetime
import time

import requests
import structlog
from flask import Blueprint, jsonify, request as flask_request

from app import limiter
from app.dog_show import crawler, result_cache, store
from app.dog_show.config import (
    BASE_URL, BREED_RESULT_TTL, REQUEST_HEADERS, REQUEST_TIMEOUT, RESULT_CACHE_VERSION,
    RESULT_RETRY_AFTER_SECONDS, SHOW_DETAIL_TTL, SHOW_LIST_TTL,
)
from app.dog_show.crawler import crawl_empty_index_once, crawl_index_once
from app.dog_show.indexing import (
    _cached_show_detail, _enrich_breeds_with_cached_result_judges,
    _enrich_breeds_with_index_judges, _is_show_recent_by_id, _persist_show_detail_to_index,
    _show_detail_from_index, _show_stats_from_index, _shows_with_cached_stats,
    _update_index_breed_judge,
)
from app.dog_show.parsers import _parse_breed_results, _parse_show_detail
from app.dog_show.result_cache import (
    _breed_results_from_all_results_cache, _cached_all_results_response,
    _result_cache_progress, _start_result_cache_warmup, crawl_result_cache_for_show,
    crawl_result_cache_once,
)
from app.dog_show.search import search_shows_data
from app.dog_show.showlink import _fetch_page, _source_url
from app.dog_show.shows import _get_show_list
from app.dog_show.store import (
    INDEX_PATH, RESULT_CACHE_DIR, RESULT_JOBS_PATH, _breed_result_cache, _index_summary,
    _load_index, _load_result_cache_doc, _load_result_jobs, _queue_result_cache_job,
    _remove_result_cache_job, _save_index, _save_result_cache_doc, _save_result_jobs,
    _show_all_results_cache, _show_detail_cache, _show_index, _show_list_cache,
)
from app.dog_show.utils import _clean_breed_list, _clean_judge_name, _utc_iso

logger = structlog.get_logger(__name__)

dog_bp = Blueprint('dog', __name__)


@dog_bp.route("/api/dog/shows")
@limiter.limit("30/minute")
def show_list():
    try:
        shows = _get_show_list()
        _load_index()
        return jsonify({
            "shows": _shows_with_cached_stats(shows),
            "index": _index_summary(total_show_count=len(shows)),
        })
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="shows", exc_info=True)
        if _show_list_cache["data"]:
            shows = _show_list_cache["data"]
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
    try:
        cached = _cached_show_detail(show_id)
        if cached:
            data = dict(cached)
            data["breeds"] = _clean_breed_list(data.get("breeds", []))
            updated_from_index = _enrich_breeds_with_index_judges(show_id, data["breeds"])
            updated_from_results = _enrich_breeds_with_cached_result_judges(show_id, data["breeds"])
            if updated_from_index or updated_from_results:
                existing_cache = _show_detail_cache.get(show_id) or {}
                _show_detail_cache[show_id] = {
                    "data": data,
                    "ts": existing_cache.get("ts", time.time()),
                }
            return jsonify(data)

        indexed = _show_detail_from_index(show_id)
        if indexed:
            _show_detail_cache[show_id] = {"data": indexed, "ts": time.time()}
            return jsonify(indexed)

        url = _source_url(show_id)
        soup = _fetch_page(url)
        data = _parse_show_detail(soup, show_id)
        fetched_at = time.time()
        data["fetched_at"] = fetched_at
        data["fetched_at_iso"] = _utc_iso(fetched_at)

        _enrich_breeds_with_index_judges(show_id, data.get("breeds", []))
        _enrich_breeds_with_cached_result_judges(show_id, data.get("breeds", []))

        try:
            _persist_show_detail_to_index(show_id, data, fetched_at)
        except Exception as e:
            logger.warning("dog_detail_index_persist_failed", show_id=show_id, error=str(e))

        _show_detail_cache[show_id] = {"data": data, "ts": fetched_at}
        return jsonify(data)
    except requests.RequestException as exc:
        logger.warning("showlink_fetch_failed", endpoint="show_detail", show_id=show_id, exc_info=True)
        stale = _cached_show_detail(show_id, allow_stale=True)
        if stale:
            return jsonify(stale)
        return jsonify({"error": "Failed to fetch show detail", "detail": str(exc)}), 502
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

    cache_key = (show_id, group, breed)
    now = time.time()
    is_recent = _is_show_recent_by_id(show_id)

    try:
        if cache_key in _breed_result_cache:
            cached = _breed_result_cache[cache_key]
            if not is_recent or (now - cached["ts"]) < BREED_RESULT_TTL:
                return jsonify(cached["data"])

        persisted = _breed_results_from_all_results_cache(show_id, group, breed)
        if persisted:
            _breed_result_cache[cache_key] = {"data": persisted, "ts": now}
            return jsonify(persisted)

        url = _source_url(show_id, group, breed)
        soup = _fetch_page(url)
        data = _parse_breed_results(soup, show_id)
        data["source_url"] = url
        data["fetched_at"] = now
        data["fetched_at_iso"] = _utc_iso(now)

        try:
            _load_index()
            sid_str = str(show_id)
            if sid_str in _show_index["shows"]:
                updated_index = False
                for b_data in _show_index["shows"][sid_str].get("breeds", []):
                    if str(b_data.get("group")) == str(group) and str(b_data.get("breed_id")) == str(breed):
                        judge = _clean_judge_name(data.get("judge"))
                        if b_data.get("judge") != judge:
                            b_data["judge"] = judge
                            updated_index = True
                if updated_index:
                    _save_index()
        except Exception as e:
            logger.warning("dog_index_judge_update_failed", show_id=show_id, error=str(e))

        _breed_result_cache[cache_key] = {"data": data, "ts": now}
        return jsonify(data)
    except requests.RequestException as exc:
        logger.warning(
            "showlink_fetch_failed", endpoint="breed_results",
            show_id=show_id, group=group, breed=breed, exc_info=True,
        )
        if cache_key in _breed_result_cache:
            return jsonify(_breed_result_cache[cache_key]["data"])
        return jsonify({"error": "Failed to fetch breed results", "detail": str(exc)}), 502
    except Exception:
        logger.exception("breed_results_error", show_id=show_id, group=group, breed=breed)
        return jsonify({"error": "Internal server error"}), 500


@dog_bp.route("/api/dog/shows/<int:show_id>/all-results")
@limiter.limit("20/minute")
def show_all_results(show_id):
    try:
        cached = _cached_all_results_response(show_id, allow_stale=True)
        if cached:
            if cached.get("cache", {}).get("stale"):
                _queue_result_cache_job(show_id, reason="stale-refresh")
            return jsonify(cached)

        job = _queue_result_cache_job(show_id, reason="user")
        started = _start_result_cache_warmup(show_id, reason="user-immediate")
        doc = _load_result_cache_doc(show_id)
        if started:
            job = _load_result_jobs().get("jobs", {}).get(str(int(show_id)), job)
        return jsonify({
            "show_id": show_id,
            "status": "warming",
            "message": "Whole-show result cache is being prepared.",
            "retry_after": RESULT_RETRY_AFTER_SECONDS,
            "progress": _result_cache_progress(show_id, doc=doc, job=job),
            "started": started,
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
