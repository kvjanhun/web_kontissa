import os
import re
from functools import wraps
from flask import jsonify, redirect, request, url_for, Response, send_from_directory
from flask_login import login_required, current_user
from .models import db, Section
from .utils import get_latest_commit_date
from datetime import datetime
from . import app, limiter


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
@limiter.exempt
def index():
    return send_from_directory(DIST_DIR, "index.html")

@app.route("/index.html")
def legacy_index():
    return redirect(url_for("index"), code=301)

@app.route("/api/sections")
def api_sections():
    sections = Section.query.order_by(Section.position.asc(), Section.id.asc()).all()
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

@app.route("/api/sections", methods=["POST"])
@admin_required
def api_create_section():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    title = data.get("title", "").strip()
    slug = data.get("slug", "").strip()
    content = data.get("content", "").strip()

    section_type = data.get("section_type", "text").strip()

    if not title or not slug or not content:
        return jsonify({"error": "title, slug, and content are required"}), 400

    if section_type not in ("text", "pills", "quote", "currently"):
        return jsonify({"error": "section_type must be 'text', 'pills', 'quote', or 'currently'"}), 400

    if Section.query.filter_by(slug=slug).first():
        return jsonify({"error": "A section with this slug already exists"}), 409

    section = Section(title=title, slug=slug, content=content, section_type=section_type)
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
    if "section_type" in data:
        section_type = data["section_type"].strip()
        if section_type not in ("text", "pills", "quote", "currently"):
            return jsonify({"error": "section_type must be 'text', 'pills', 'quote', or 'currently'"}), 400
        section.section_type = section_type

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


@app.route("/api/sections/reorder", methods=["PUT"])
@admin_required
def api_reorder_sections():
    data = request.get_json()
    if not data or not isinstance(data.get("order"), list):
        return jsonify({"error": "order (list of section IDs) required"}), 400

    order = data["order"]
    if not all(isinstance(i, int) for i in order):
        return jsonify({"error": "order must be a list of integers"}), 400

    sections = Section.query.all()
    section_map = {s.id: s for s in sections}

    for sid in order:
        if sid not in section_map:
            return jsonify({"error": f"Section {sid} not found"}), 404

    for position, sid in enumerate(order):
        section_map[sid].position = position

    db.session.commit()
    return jsonify({"message": "Sections reordered"})


@app.route("/sanakenno")
@limiter.exempt
def sanakenno_page():
    """Serve the Sanakenno game with game-specific OG meta tags for link previews."""
    index_path = os.path.join(DIST_DIR, "index.html")
    try:
        with open(index_path, encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        return send_from_directory(DIST_DIR, "index.html")

    DESC = "Löydä sanat seitsemästä kirjaimesta. Päivittäinen sanapeli."
    html = re.sub(r"<title>[^<]*</title>", "<title>Sanakenno \u2014 erez.ac</title>", html)
    html = re.sub(r'<meta name="description"[^>]*>', f'<meta name="description" content="{DESC}">', html)
    html = re.sub(r'<meta property="og:title"[^>]*>', '<meta property="og:title" content="Sanakenno \u2014 sanapeli">', html)
    html = re.sub(r'<meta property="og:description"[^>]*>', f'<meta property="og:description" content="{DESC}">', html)
    html = re.sub(r'<meta property="og:url"[^>]*>', '<meta property="og:url" content="https://erez.ac/sanakenno">', html)
    html = re.sub(r'<link rel="icon"[^>]*>', '<link rel="icon" type="image/png" href="/sanakenno-favicon.png">', html)
    return Response(html, mimetype="text/html")


@app.route("/<path:path>")
@limiter.exempt
def catch_all(path):
    """Serve static file from dist/ if it exists, otherwise fall back to index.html for Vue Router."""
    file_path = os.path.join(DIST_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(DIST_DIR, path)
    index_path = os.path.join(DIST_DIR, path, "index.html")
    if os.path.isfile(index_path):
        return send_from_directory(os.path.join(DIST_DIR, path), "index.html")
    return send_from_directory(DIST_DIR, "index.html")
