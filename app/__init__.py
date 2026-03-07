import os
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

from . import routes  # registers the routes with the app
from . import auth
from . import recipes
from .api import cowsay
from .api import weather
from .api import kenno
from .api import pageviews
from .api import health

