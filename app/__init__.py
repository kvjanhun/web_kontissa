import os
import time
from flask import Flask
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .models import db, User

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI", "sqlite:////app/data/site.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-not-for-production")

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

limiter = Limiter(
    get_remote_address, app=app, storage_uri="memory://",
    default_limits=["30/minute"],
    enabled=not os.environ.get("TESTING"),
)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    from flask import jsonify
    return jsonify({"error": "Authentication required"}), 401


def _run_migrations():
    """Add columns to existing tables that db.create_all() won't add to SQLite."""
    migrations = [
        "ALTER TABLE blocked_words ADD COLUMN blocked_at DATETIME",
        "ALTER TABLE page_views ADD COLUMN created_at DATETIME",
        "ALTER TABLE page_views ADD COLUMN updated_at DATETIME",
        "ALTER TABLE section ADD COLUMN position INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()


with app.app_context():
    db.create_all()
    _run_migrations()

# App-wide request counter (used by AdminHealth)
_stats = {"requests": 0, "start_time": time.time()}


@app.before_request
def _count_requests():
    _stats["requests"] += 1


from .routes import core_bp
from .auth import auth_bp
from .recipes import recipes_bp
from .api.cowsay import cowsay_bp
from .api.weather import weather_bp
from .api.kenno import kenno_bp
from .api.pageviews import pageviews_bp
from .api.health import health_bp

app.register_blueprint(auth_bp)
app.register_blueprint(recipes_bp)
app.register_blueprint(cowsay_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(kenno_bp)
app.register_blueprint(pageviews_bp)
app.register_blueprint(health_bp)
app.register_blueprint(core_bp)  # last — has catch-all route
