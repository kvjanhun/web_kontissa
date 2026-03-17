import os
import time
import structlog
import logging
from flask import Flask, request
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .models import db, User

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI", "sqlite:////app/data/site.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SECURE"] = not os.environ.get("FLASK_DEBUG")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
import sys as _sys
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    if "pytest" in _sys.modules:
        app.secret_key = "dev-only-not-for-production"
    else:
        raise ValueError("SECRET_KEY environment variable is required. Set it in .env.")

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


# def _run_migrations():
#     """Add columns to existing tables that db.create_all() won't add to SQLite."""
#     migrations = [
#         "ALTER TABLE blocked_words ADD COLUMN blocked_at DATETIME",
#         "ALTER TABLE page_views ADD COLUMN created_at DATETIME",
#         "ALTER TABLE page_views ADD COLUMN updated_at DATETIME",
#         "ALTER TABLE section ADD COLUMN position INTEGER DEFAULT 0",
#     ]
#     for sql in migrations:
#         try:
#             db.session.execute(db.text(sql))
#             db.session.commit()
#         except Exception:
#             db.session.rollback()


def _run_migrations():
    """Add columns to existing tables that db.create_all() won't add to SQLite."""
    migrations = [
        "ALTER TABLE section ADD COLUMN locale VARCHAR(5) NOT NULL DEFAULT 'en'",
        "ALTER TABLE section ADD COLUMN collapsible BOOLEAN NOT NULL DEFAULT 0",
    ]
    for sql in migrations:
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()

    # SQLite can't ALTER constraints. Recreate the section table to replace
    # the old unique(slug) with unique(slug, locale).
    try:
        # Check if locale column is missing (means table needs migration)
        columns = [row[1] for row in db.session.execute(db.text("PRAGMA table_info(section)")).fetchall()]
        if 'locale' not in columns:
            db.session.execute(db.text("""
                CREATE TABLE section_new (
                    id INTEGER PRIMARY KEY,
                    slug VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    section_type VARCHAR NOT NULL DEFAULT 'text',
                    position INTEGER DEFAULT 0,
                    collapsible BOOLEAN NOT NULL DEFAULT 0,
                    locale VARCHAR(5) NOT NULL DEFAULT 'en',
                    UNIQUE(slug, locale)
                )
            """))
            db.session.execute(db.text(
                "INSERT INTO section_new (id, slug, title, content, section_type, position, locale) "
                "SELECT id, slug, title, content, section_type, position, locale FROM section"
            ))
            db.session.execute(db.text("DROP TABLE section"))
            db.session.execute(db.text("ALTER TABLE section_new RENAME TO section"))
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
    request._start_time = time.time()

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        path=request.path,
        method=request.method,
        ip=request.headers.get("X-Forwarded-For", request.remote_addr)
    )


@app.after_request
def _log_request(response):
    duration_ms = round((time.time() - getattr(request, '_start_time', time.time())) * 1000)
    log = structlog.get_logger()
    log.info("request", status=response.status_code, duration_ms=duration_ms)
    return response


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
