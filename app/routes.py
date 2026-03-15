import os
from flask import Blueprint, jsonify, redirect, request, url_for, Response, send_from_directory
from flask_login import current_user
from .models import db, Section
from .utils import get_latest_commit_date
from .decorators import admin_required
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

VALID_SECTION_TYPES = ("text", "pills", "quote", "currently", "intro", "project")

@core_bp.route("/api/sections")
def api_sections():
    locale = request.args.get("locale", "en").strip()
    query = Section.query
    if locale:
        query = query.filter_by(locale=locale)
    sections = query.order_by(Section.position.asc(), Section.id.asc()).all()
    return jsonify([s.to_dict() for s in sections])

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
        {"loc": "https://erez.ac/sanakenno", "lastmod": lastmod, "changefreq": "daily", "priority": "0.9"},
        {"loc": "https://erez.ac/about", "lastmod": lastmod, "changefreq": "monthly", "priority": "0.8"},
        {"loc": "https://erez.ac/contact", "lastmod": lastmod, "changefreq": "monthly", "priority": "0.5"},
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

@core_bp.route("/api/sections", methods=["POST"])
@admin_required
def api_create_section():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    title = data.get("title", "").strip()
    slug = data.get("slug", "").strip()
    content = data.get("content", "").strip()

    section_type = data.get("section_type", "text").strip()
    locale = data.get("locale", "en").strip()

    if not title or not slug or not content:
        return jsonify({"error": "title, slug, and content are required"}), 400

    if section_type not in VALID_SECTION_TYPES:
        return jsonify({"error": f"section_type must be one of: {', '.join(VALID_SECTION_TYPES)}"}), 400

    if locale not in ("en", "fi"):
        return jsonify({"error": "locale must be 'en' or 'fi'"}), 400

    if Section.query.filter_by(slug=slug, locale=locale).first():
        return jsonify({"error": "A section with this slug and locale already exists"}), 409

    position = data.get("position")
    if position is not None:
        if not isinstance(position, int) or position < 0 or position > 29:
            return jsonify({"error": "position must be an integer 0–29"}), 400

    collapsible = bool(data.get("collapsible", False))

    section = Section(title=title, slug=slug, content=content, section_type=section_type, locale=locale, collapsible=collapsible)
    if position is not None:
        section.position = position
    db.session.add(section)
    db.session.commit()
    return jsonify(section.to_dict()), 201


@core_bp.route("/api/sections/<int:section_id>", methods=["PUT"])
@admin_required
def api_update_section(section_id):
    section = db.session.get(Section, section_id)
    if not section:
        return jsonify({"error": "Section not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    if "title" in data:
        section.title = data["title"].strip()
    if "slug" in data:
        section.slug = data["slug"].strip()
    if "content" in data:
        section.content = data["content"].strip()
    if "section_type" in data:
        section_type = data["section_type"].strip()
        if section_type not in VALID_SECTION_TYPES:
            return jsonify({"error": f"section_type must be one of: {', '.join(VALID_SECTION_TYPES)}"}), 400
        section.section_type = section_type
    if "locale" in data:
        locale = data["locale"].strip()
        if locale not in ("en", "fi"):
            return jsonify({"error": "locale must be 'en' or 'fi'"}), 400
        section.locale = locale
    if "collapsible" in data:
        section.collapsible = bool(data["collapsible"])
    if "position" in data:
        position = data["position"]
        if not isinstance(position, int) or position < 0 or position > 29:
            return jsonify({"error": "position must be an integer 0–29"}), 400
        section.position = position

    db.session.commit()
    return jsonify(section.to_dict())


@core_bp.route("/api/sections/<int:section_id>", methods=["DELETE"])
@admin_required
def api_delete_section(section_id):
    section = db.session.get(Section, section_id)
    if not section:
        return jsonify({"error": "Section not found"}), 404

    db.session.delete(section)
    db.session.commit()
    return jsonify({"message": "Section deleted"})


@core_bp.route("/api/sections/reorder", methods=["PUT"])
@admin_required
def api_reorder_sections():
    data = request.get_json()
    if not data or not isinstance(data.get("order"), list):
        return jsonify({"error": "order (list of section IDs) required"}), 400

    order = data["order"]
    if not all(isinstance(i, int) for i in order):
        return jsonify({"error": "order must be a list of integers"}), 400

    locale = data.get("locale", "en")
    sections = Section.query.filter_by(locale=locale).all()
    section_map = {s.id: s for s in sections}

    for sid in order:
        if sid not in section_map:
            return jsonify({"error": f"Section {sid} not found"}), 404

    for position, sid in enumerate(order):
        section_map[sid].position = position

    db.session.commit()
    return jsonify({"message": "Sections reordered"})


@core_bp.route("/<path:path>")
@limiter.exempt
def catch_all(path):
    """Serve static file from dist/ if it exists, otherwise fall back to SPA shell for client-side routing."""
    file_path = os.path.join(DIST_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(DIST_DIR, path)
    index_path = os.path.join(DIST_DIR, path, "index.html")
    if os.path.isfile(index_path):
        return send_from_directory(os.path.join(DIST_DIR, path), "index.html")
    # SPA fallback: 200.html is a generic Nuxt shell (not pre-rendered for any specific route)
    return send_from_directory(DIST_DIR, "200.html")
