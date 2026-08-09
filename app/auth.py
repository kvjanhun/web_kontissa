import hashlib
import hmac

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from .models import db, User
from . import limiter
import structlog

auth_bp = Blueprint('auth', __name__)
logger = structlog.get_logger(__name__)

# Verified against on the miss path so a nonexistent email costs the same scrypt work
# as a real one. Without it, response latency cleanly separates valid from invalid
# emails — the 3/minute limiter slows enumeration but doesn't close the oracle.
_DUMMY_PASSWORD_HASH = generate_password_hash("dummy-password-for-constant-time-login")


def _email_log_hash(email):
    normalized = (email or "").strip().lower()
    secret = (current_app.secret_key or "").encode("utf-8")
    return hmac.new(secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


@auth_bp.route("/api/login", methods=["POST"])
@limiter.limit("3/minute")
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        logger.warning("login_failed", reason="missing credentials")
        return jsonify({"error": "Email and password are required"}), 400

    # Case-insensitive on both sides rather than lowercasing the input: rows may
    # already store mixed-case addresses, and normalising only the query would lock
    # those accounts out.
    user = User.query.filter(func.lower(User.email) == email.lower()).first()
    if user is None:
        check_password_hash(_DUMMY_PASSWORD_HASH, password)
        logger.warning("login_failed", reason="invalid credentials", email_hash=_email_log_hash(email))
        return jsonify({"error": "Invalid email or password"}), 401
    if not user.check_password(password):
        logger.warning("login_failed", reason="invalid credentials", email_hash=_email_log_hash(email))
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(user)
    logger.info("login_success", email_hash=_email_log_hash(email), user_id=user.id)
    return jsonify(user.to_dict())


@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify(current_user.to_dict())
    return jsonify(None)
