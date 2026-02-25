from datetime import datetime, timezone

from flask import jsonify, request, session
from app import app, limiter
from app.models import db, PageView
from app.routes import admin_required


@app.route("/api/pageview", methods=["POST"])
@limiter.limit("60/minute")
def track_pageview():
    data = request.get_json()
    if not data or not isinstance(data.get("path"), str):
        return jsonify({"error": "path is required"}), 400

    path = data["path"]
    if not path.startswith("/") or len(path) > 200:
        return jsonify({"error": "path must start with / and be at most 200 chars"}), 400

    # Session-based dedup: only count once per browser session per path
    viewed = session.get("viewed_pages", [])
    already_counted = path in viewed

    pv = db.session.query(PageView).filter_by(path=path).first()
    if not already_counted:
        if pv:
            pv.count += 1
            pv.updated_at = datetime.now(timezone.utc)
        else:
            pv = PageView(path=path, count=1)
            db.session.add(pv)
        db.session.commit()
        viewed.append(path)
        session["viewed_pages"] = viewed

    return jsonify({"path": pv.path if pv else path, "count": pv.count if pv else 0})


@app.route("/api/pageviews")
@admin_required
def list_pageviews():
    views = db.session.query(PageView).order_by(PageView.count.desc()).all()
    return jsonify([
        {
            "path": pv.path,
            "count": pv.count,
            "created_at": pv.created_at.isoformat() + "Z" if pv.created_at else None,
            "updated_at": pv.updated_at.isoformat() + "Z" if pv.updated_at else None,
        }
        for pv in views
    ])
