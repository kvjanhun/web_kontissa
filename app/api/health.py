import os
import sys
import time
import urllib.request

import structlog
from flask import Blueprint, jsonify, current_app
from app.models import db, User, Recipe, Section, BlockedWord, PageViewEvent
from app.decorators import admin_required
from app import _stats

logger = structlog.get_logger(__name__)

health_bp = Blueprint('health', __name__)

_NODE_EXPORTER_URL = os.environ.get("NODE_EXPORTER_URL", "").rstrip("/")


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


def _query_node_exporter():
    """Fetch host-level stats from node_exporter /metrics. Returns dict or None."""
    if not _NODE_EXPORTER_URL:
        return None
    try:
        with urllib.request.urlopen(f"{_NODE_EXPORTER_URL}/metrics", timeout=2) as resp:
            text = resp.read().decode("utf-8")
    except Exception:
        logger.warning("node_exporter_unreachable", url=_NODE_EXPORTER_URL)
        return None

    result = {}
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        try:
            if line.startswith("node_boot_time_seconds "):
                result["boot_time"] = float(line.split()[1])
            elif line.startswith("node_memory_MemTotal_bytes "):
                result["mem_total"] = float(line.split()[1])
            elif line.startswith("node_memory_MemAvailable_bytes "):
                result["mem_available"] = float(line.split()[1])
            elif line.startswith("node_filesystem_size_bytes{") and 'mountpoint="/"' in line:
                result["fs_size"] = float(line.split()[-1])
            elif line.startswith("node_filesystem_avail_bytes{") and 'mountpoint="/"' in line:
                result["fs_avail"] = float(line.split()[-1])
            elif line.startswith("node_load1 "):
                result["load_1min"] = float(line.split()[1])
        except (IndexError, ValueError):
            pass

    return result or None


@health_bp.route("/api/server-info")
def server_info():
    node = _query_node_exporter()

    # Uptime: system boot time from node_exporter, else Flask process start
    if node and "boot_time" in node:
        uptime_seconds = round(time.time() - node["boot_time"], 1)
    else:
        uptime_seconds = round(time.time() - _stats["start_time"], 1)

    # Disk: host filesystem from node_exporter, else container statvfs
    disk_used_percent = None
    if node and "fs_size" in node and "fs_avail" in node and node["fs_size"] > 0:
        disk_used_percent = round((node["fs_size"] - node["fs_avail"]) / node["fs_size"] * 100, 1)
    else:
        try:
            stat = os.statvfs("/")
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            if total > 0:
                disk_used_percent = round((total - free) / total * 100, 1)
        except (OSError, AttributeError):
            pass

    # Memory: host total/used from node_exporter, else process RSS
    memory_total_mb = None
    memory_used_mb = None
    if node and "mem_total" in node:
        memory_total_mb = round(node["mem_total"] / (1024 * 1024))
        if "mem_available" in node:
            memory_used_mb = round((node["mem_total"] - node["mem_available"]) / (1024 * 1024))
    else:
        rss = _read_vm_rss()
        if rss is not None:
            memory_used_mb = round(rss / (1024 * 1024), 1)

    load_1min = None
    if node and "load_1min" in node:
        load_1min = round(node["load_1min"], 2)

    return jsonify({
        "uptime_seconds": uptime_seconds,
        "request_count": _stats["requests"],
        "disk_used_percent": disk_used_percent,
        "memory_total_mb": memory_total_mb,
        "memory_used_mb": memory_used_mb,
        "load_1min": load_1min,
    })


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
