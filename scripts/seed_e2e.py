"""Seed a file-based SQLite database for E2E tests.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/test-e2e.db" python3 scripts/seed_e2e.py

Creates known users, home content (fixed blocks + projects), and a recipe.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "app", "data", "test-e2e.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.environ["DATABASE_URI"] = f"sqlite:///{DB_PATH}"

from werkzeug.security import generate_password_hash
from app import app
from app.models import db, User, Recipe, Ingredient, Step
from scripts.seed_home_content import _load_snapshot, _seed_fixed_blocks, _seed_projects

# Known test credentials (used by e2e/fixtures/auth.js)
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "adminpass123"
USER_EMAIL = "user@test.com"
USER_PASSWORD = "userpass123"


def seed():
    # Remove old DB if present
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed old {DB_PATH}")

    # Override the DB URI and rebind the engine (app/__init__.py already created
    # an engine for the default path at import time)
    db_uri = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

    with app.app_context():
        db.engine.dispose()
        db.create_all()

        # --- Users ---
        admin = User(username="admin", email=ADMIN_EMAIL, role="admin")
        admin.password_hash = generate_password_hash(ADMIN_PASSWORD, method="pbkdf2:sha256")
        db.session.add(admin)

        user = User(username="testuser", email=USER_EMAIL, role="user")
        user.password_hash = generate_password_hash(USER_PASSWORD, method="pbkdf2:sha256")
        db.session.add(user)

        # --- Home content (fixed text blocks + projects) ---
        snapshot = _load_snapshot()
        blocks = _seed_fixed_blocks(snapshot)
        projects = _seed_projects(snapshot)

        # --- Recipe ---
        recipe = Recipe(title="Test Pancakes", slug="test-pancakes",
                        category="Breakfast", created_by=1)
        recipe.ingredients = [
            Ingredient(name="Flour", amount="2", unit="cups", position=0),
            Ingredient(name="Eggs", amount="2", position=1),
        ]
        recipe.steps = [
            Step(content="Mix ingredients", position=0),
            Step(content="Cook on pan", position=1),
        ]
        db.session.add(recipe)

        db.session.commit()
        print(f"Seeded E2E database at {DB_PATH}")
        print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  User:  {USER_EMAIL} / {USER_PASSWORD}")
        print(f"  Home content: {blocks} fixed fields, {projects} projects")
        print(f"  Recipes: 1")


if __name__ == "__main__":
    seed()
