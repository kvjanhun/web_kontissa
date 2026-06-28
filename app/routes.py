import os
from flask import Blueprint, jsonify, redirect, url_for, Response, send_from_directory
from .utils import get_latest_commit_date
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
            return send_from_directory(dist_root, os.path.relpath(requested, dist_root))
        index_path = os.path.join(requested, "index.html")
        if os.path.isfile(index_path):
            return send_from_directory(requested, "index.html")
    # SPA fallback: 200.html is a generic Nuxt shell (not pre-rendered for any specific route)
    return send_from_directory(dist_root, "200.html")
