import os
from flask import Blueprint, jsonify, redirect, url_for, Response, send_from_directory
from .utils import get_latest_commit_date, is_known_route
from datetime import datetime
from . import limiter

core_bp = Blueprint('core', __name__)

DIST_DIR = os.path.join(os.path.dirname(__file__), "static", "dist")

@core_bp.route("/")
@limiter.exempt
def index():
    return send_from_directory(DIST_DIR, "index.html")

@core_bp.route("/index.html")
def legacy_index():
    return redirect(url_for("core.index"), code=301)

@core_bp.route("/api/meta")
def api_meta():
    last_updated = get_latest_commit_date()
    update_date = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).strftime("%Y-%m-%d") if last_updated else "2025"
    return jsonify({
        "site_name": "erez.ac",
        "author": "Konsta Janhunen",
        "update_date": update_date
    })

@core_bp.route("/sitemap.xml")
def generate_sitemap():
    commit_date = get_latest_commit_date()
    lastmod = commit_date[:10] if commit_date else "2026-03-01"
    pages = [
        {"loc": "https://erez.ac/", "lastmod": lastmod, "changefreq": "monthly", "priority": "1.0"},
        # Both are pre-rendered and linked from the home footer. /dog/about-crawler
        # exists so crawler operators can identify the bot without guessing the URL,
        # which only works if it's discoverable.
        {"loc": "https://erez.ac/dog", "lastmod": lastmod, "changefreq": "daily", "priority": "0.8"},
        {"loc": "https://erez.ac/dog/about-crawler", "lastmod": lastmod, "changefreq": "yearly", "priority": "0.3"},
    ]

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    for page in pages:
        xml_parts.append("<url>")
        for key, value in page.items():
            xml_parts.append(f"<{key}>{value}</{key}>")
        xml_parts.append("</url>")

    xml_parts.append("</urlset>")
    xml = "\n".join(xml_parts)

    return Response(xml, mimetype="application/xml")

# Filenames under _nuxt/ carry a content hash, so a given URL's bytes never
# change and it can be cached indefinitely. Font filenames are stable rather than
# hashed, so cache them the same way but rename the file when replacing one —
# cached clients will not re-fetch a name they already hold. Everything else (the
# prerendered HTML, the SPA shell, robots.txt) keeps Flask's revalidate-always
# default so a deploy reaches visitors immediately.
CACHE_FOREVER = 31536000
_CACHED_PREFIXES = ("_nuxt/", "fonts/")


def _send_dist_file(directory, filename):
    """Serve a file from dist/, caching the fingerprinted assets hard."""
    cached = filename.startswith(_CACHED_PREFIXES)
    response = send_from_directory(
        directory, filename, max_age=CACHE_FOREVER if cached else None
    )
    if cached:
        # `immutable` is the half that matters for a reload: plain max-age still
        # lets the browser send a conditional request on F5, which is what made
        # the webfonts re-swap on every refresh.
        response.headers["Cache-Control"] = f"public, max-age={CACHE_FOREVER}, immutable"
    return response


def _resolve_within_dist(path):
    """Resolve `path` against the dist root, returning (dist_root, real_path).

    `real_path` is None when the request escapes dist via traversal. The second
    branch of catch_all passes a path-derived value as the *directory* argument to
    send_from_directory, which only guards its filename argument — so we contain
    the resolved path here instead of trusting that call.
    """
    dist_root = os.path.realpath(DIST_DIR)
    requested = os.path.realpath(os.path.join(dist_root, path))
    if requested == dist_root or requested.startswith(dist_root + os.sep):
        return dist_root, requested
    return dist_root, None


@core_bp.route("/<path:path>")
@limiter.exempt
def catch_all(path):
    """Serve static file from dist/ if it exists, otherwise fall back to SPA shell for client-side routing."""
    dist_root, requested = _resolve_within_dist(path)
    if requested is not None:
        if os.path.isfile(requested):
            return _send_dist_file(dist_root, os.path.relpath(requested, dist_root))
        index_path = os.path.join(requested, "index.html")
        if os.path.isfile(index_path):
            return send_from_directory(requested, "index.html")
    # SPA fallback: 200.html is a generic Nuxt shell (not pre-rendered for any specific route)
    response = send_from_directory(dist_root, "200.html")
    if not is_known_route(path):
        # Serve the same shell — the client router renders the styled 404 page — but
        # with the honest status. Previously every unknown URL was a soft 404 returning
        # 200, so search engines indexed junk paths as real pages.
        response.status_code = 404
    return response
