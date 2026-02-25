import os
import sys
import time

from flask import jsonify
from flask_login import login_required, current_user

from app import app

_START_TIME = time.time()


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

    return jsonify({
        "python_version": sys.version,
        "db_size_bytes": db_size,
        "disk_total_bytes": disk_total,
        "disk_free_bytes": disk_free,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    })
