import os
import sys
import time

import structlog
from flask import Blueprint, jsonify, current_app
from app.models import db, User, Recipe, Section, BlockedWord, PageViewEvent
from app.decorators import admin_required
from app import _stats

logger = structlog.get_logger(__name__)

health_bp = Blueprint('health', __name__)


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


@health_bp.route("/api/admin/health")
@admin_required
def admin_health():
    db_path = current_app.config["SQLALCHEMY_DATABASE_URI"]
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
            logger.error("table_count_failed", table=name, exc_info=True)
            table_counts[name] = None

    return jsonify({
        "python_version": sys.version,
        "db_size_bytes": db_size,
        "disk_total_bytes": disk_total,
        "disk_free_bytes": disk_free,
        "uptime_seconds": round(time.time() - _stats["start_time"], 1),
        "os_info": _read_os_info(),
        "memory_rss_bytes": _read_vm_rss(),
        "request_count": _stats["requests"],
        "table_counts": table_counts,
    })
