from flask import request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from .models import db, User
from . import app, limiter


@app.route("/api/login", methods=["POST"])
@limiter.limit("5/minute")
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    login_user(user)
    return jsonify(user.to_dict())


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"message": "Logged out"})


@app.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify(current_user.to_dict())
    return jsonify({"error": "Not authenticated"}), 401
