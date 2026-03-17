from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from .models import db, User
from . import limiter
import structlog

auth_bp = Blueprint('auth', __name__)
logger = structlog.get_logger(__name__)


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

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        logger.warning("login_failed", reason="invalid credentials", email=email)
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(user)
    logger.info("login_success", email=email, user_id=user.id)
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
