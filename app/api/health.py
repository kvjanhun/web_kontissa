import os
import sys
import time

from flask import jsonify
from flask_login import login_required, current_user

from app import app
from app.models import db, User, Recipe, Section, BlockedWord, PageViewEvent

_START_TIME = time.time()
_REQUEST_COUNT = 0


@app.before_request
def _count_requests():
    global _REQUEST_COUNT
    _REQUEST_COUNT += 1


def _read_os_info():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except (OSError, IOError):
        pass
    return None


def _read_vm_rss():
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    kb = int(parts[1])
                    return kb * 1024  # return bytes
    except (OSError, IOError, ValueError):
        pass
    return None


@app.route("/api/admin/health")
@login_required
def admin_health():
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    db_path = app.config["SQLALCHEMY_DATABASE_URI"]
    db_size = 0
    if db_path.startswith("sqlite:///"):
        file_path = db_path[len("sqlite:///"):]
        try:
            db_size = os.path.getsize(file_path)
        except OSError:
            pass

    disk_total = 0
    disk_free = 0
    try:
        stat = os.statvfs("/")
        disk_total = stat.f_frsize * stat.f_blocks
        disk_free = stat.f_frsize * stat.f_bavail
    except (OSError, AttributeError):
        pass

    # DB row counts
    table_counts = {}
    for name, model in [
        ("users", User),
        ("recipes", Recipe),
        ("sections", Section),
        ("blocked_words", BlockedWord),
        ("page_view_events", PageViewEvent),
    ]:
        try:
            table_counts[name] = db.session.query(model).count()
        except Exception:
            table_counts[name] = None

    return jsonify({
        "python_version": sys.version,
        "db_size_bytes": db_size,
        "disk_total_bytes": disk_total,
        "disk_free_bytes": disk_free,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "os_info": _read_os_info(),
        "memory_rss_bytes": _read_vm_rss(),
        "request_count": _REQUEST_COUNT,
        "table_counts": table_counts,
    })
