import os
import time
import structlog
import logging
from flask import Flask, request
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
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
# We sit behind exactly one trusted proxy (nginx), which overwrites
# X-Forwarded-For with `$proxy_add_x_forwarded_for` (real client appended last).
# Without this, request.remote_addr is the Docker bridge gateway, so the rate
# limiter keys every visitor into one shared bucket. x_for=1 takes the single
# rightmost (nginx-added) hop, so a client-supplied X-Forwarded-For can't spoof
# it. x_proto=1 lets Flask see the original https scheme.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config["TESTING"] = os.environ.get("TESTING") in {"1", "true", "True"}
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


with app.app_context():
    db.create_all()

# Create the /dog persistent database's tables (separate dog.db, standalone
# engine — see app/dog_show/db.py). Idempotent create-if-missing of empty
# tables, never drops or alters — the same "empty tables for fresh databases"
# allowance the line above uses for site.db.
from app.dog_show import db as dog_db  # noqa: E402
dog_db.init_db()

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
        # ProxyFix has already resolved this to the real client IP (the
        # nginx-added X-Forwarded-For hop), not the Docker bridge gateway.
        ip=request.remote_addr,
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
from .home_content import home_content_bp
from .api.cowsay import cowsay_bp
from .api.weather import weather_bp
from .api.pageviews import pageviews_bp
from .api.health import health_bp
from .api.dog import dog_bp

app.register_blueprint(auth_bp)
app.register_blueprint(recipes_bp)
app.register_blueprint(home_content_bp)
app.register_blueprint(cowsay_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(pageviews_bp)
app.register_blueprint(health_bp)
app.register_blueprint(dog_bp)
app.register_blueprint(core_bp)  # last — has catch-all route
