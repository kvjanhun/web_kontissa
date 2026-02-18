import os
from functools import wraps
from flask import jsonify, redirect, request, url_for, Response, send_from_directory
from flask_login import login_required, current_user
from .models import db, Section
from .utils import get_latest_commit_date
from datetime import datetime
from . import app


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

DIST_DIR = os.path.join(os.path.dirname(__file__), "static", "dist")

@app.route("/")
def index():
    return send_from_directory(DIST_DIR, "index.html")

@app.route("/index.html")
def legacy_index():
    return redirect(url_for("index"), code=301)

@app.route("/api/sections")
def api_sections():
    sections = Section.query.all()
    return jsonify([s.to_dict() for s in sections])

@app.route("/api/meta")
def api_meta():
    last_updated = get_latest_commit_date()
    update_date = datetime.fromisoformat(last_updated.replace("Z", "+00:00")).strftime("%Y-%m-%d") if last_updated else "2025"
    return jsonify({
        "site_name": "erez.ac",
        "author": "Konsta Janhunen",
        "update_date": update_date
    })

@app.route("/sitemap.xml")
def generate_sitemap():
    commit_date = get_latest_commit_date()
    lastmod = commit_date[:10] if commit_date else "2025-01-01"
    pages = [
        {
            "loc": "https://erez.ac/",
            "lastmod": lastmod,
            "changefreq": "monthly",
            "priority": "1.0"
        }
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

@app.route("/api/sections", methods=["POST"])
@admin_required
def api_create_section():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    title = data.get("title", "").strip()
    slug = data.get("slug", "").strip()
    content = data.get("content", "").strip()

    if not title or not slug or not content:
        return jsonify({"error": "title, slug, and content are required"}), 400

    if Section.query.filter_by(slug=slug).first():
        return jsonify({"error": "A section with this slug already exists"}), 409

    section = Section(title=title, slug=slug, content=content)
    db.session.add(section)
    db.session.commit()
    return jsonify(section.to_dict()), 201


@app.route("/api/sections/<int:section_id>", methods=["PUT"])
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

    db.session.commit()
    return jsonify(section.to_dict())


@app.route("/api/sections/<int:section_id>", methods=["DELETE"])
@admin_required
def api_delete_section(section_id):
    section = db.session.get(Section, section_id)
    if not section:
        return jsonify({"error": "Section not found"}), 404

    db.session.delete(section)
    db.session.commit()
    return jsonify({"message": "Section deleted"})


@app.route("/<path:path>")
def catch_all(path):
    """Serve static file from dist/ if it exists, otherwise fall back to index.html for Vue Router."""
    file_path = os.path.join(DIST_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(DIST_DIR, path)
    index_path = os.path.join(DIST_DIR, path, "index.html")
    if os.path.isfile(index_path):
        return send_from_directory(os.path.join(DIST_DIR, path), "index.html")
    return send_from_directory(DIST_DIR, "index.html")
