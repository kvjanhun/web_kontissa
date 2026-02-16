from flask import render_template, jsonify, redirect, url_for, Response
from .models import Section
from .utils import get_latest_commit_date
from datetime import datetime
from . import app

@app.route("/")
def index():
    return render_template("index.html")

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

@app.route("/<path:path>")
def catch_all(path):
    """Let Vue Router handle client-side routing (including 404s)."""
    return render_template("index.html")

@app.route("/sitemap.xml")
def generate_sitemap():
    pages = [
        {
            "loc": "https://erez.ac/",
            "lastmod": get_latest_commit_date()[:10],
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
