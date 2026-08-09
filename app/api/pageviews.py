from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func
from app import limiter
from app.models import db, PageView, PageViewEvent
from app.decorators import admin_required
from app.utils import is_known_route

pageviews_bp = Blueprint('pageviews', __name__)

# Cap on the per-session dedup list. It lives in the signed client-side cookie, so an
# uncapped list is re-sent on every request and eventually trips Werkzeug's 4 KB
# warning. The site has far fewer routes than this, so the cap only bites on abuse.
MAX_TRACKED_PATHS = 50


@pageviews_bp.route("/api/pageview", methods=["POST"])
@limiter.limit("60/minute")
def track_pageview():
    data = request.get_json()
    if not data or not isinstance(data.get("path"), str):
        return jsonify({"error": "path is required"}), 400

    path = data["path"]
    if not path.startswith("/") or len(path.encode("utf-8")) > 200:
        return jsonify({"error": "path must start with / and be at most 200 chars"}), 400

    # Only real routes get a row. The endpoint is public, so without this any client
    # can insert an unbounded number of PageView/PageViewEvent rows into site.db —
    # which Litestream then replicates off-site. 400 rather than a silent drop so a
    # genuine bug in usePageView surfaces instead of quietly losing analytics.
    if not is_known_route(path):
        return jsonify({"error": "unknown path"}), 400

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
        db.session.add(PageViewEvent(path=path))
        db.session.commit()
        viewed.append(path)
        # FIFO eviction keeps the session cookie from growing without bound.
        session["viewed_pages"] = viewed[-MAX_TRACKED_PATHS:]

    return jsonify({"path": pv.path if pv else path, "count": pv.count if pv else 0})


@pageviews_bp.route("/api/pageviews")
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


@pageviews_bp.route("/api/pageviews/events")
@admin_required
def pageview_events():
    days = request.args.get("days", 30, type=int)
    days = max(1, min(days, 90))

    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.session.query(
            func.date(PageViewEvent.timestamp).label("date"),
            PageViewEvent.path,
            func.count().label("cnt"),
        )
        .filter(PageViewEvent.timestamp >= since)
        .group_by(func.date(PageViewEvent.timestamp), PageViewEvent.path)
        .all()
    )

    # Build date→{path: count} mapping
    data = {}
    all_paths = set()
    for date_str, path, cnt in rows:
        date_key = str(date_str)
        data.setdefault(date_key, {})[path] = cnt
        all_paths.add(path)

    # Fill all dates in range
    series = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        if d in data:
            series.append({"date": d, "counts": data[d]})
        else:
            series.append({"date": d, "counts": {}})

    return jsonify({
        "days": days,
        "paths": sorted(all_paths),
        "series": series,
    })
