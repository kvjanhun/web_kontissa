"""Seed a file-based SQLite database for E2E tests.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/test-e2e.db" python3 scripts/seed_e2e.py

Creates known users, sections, a recipe, and puzzles from initial_puzzles.json.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "app", "data", "test-e2e.db")
os.environ["DATABASE_URI"] = f"sqlite:///{DB_PATH}"

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash
from app import app
from app.models import (db, User, Section, Recipe, Ingredient, Step,
                        KennoPuzzle, KennoConfig)

SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_puzzles.json")

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
        now = datetime.now(timezone.utc)

        # --- Users ---
        admin = User(username="admin", email=ADMIN_EMAIL, role="admin")
        admin.password_hash = generate_password_hash(ADMIN_PASSWORD, method="pbkdf2:sha256")
        db.session.add(admin)

        user = User(username="testuser", email=USER_EMAIL, role="user")
        user.password_hash = generate_password_hash(USER_PASSWORD, method="pbkdf2:sha256")
        db.session.add(user)

        # --- Sections ---
        sections = [
            Section(title="Welcome", slug="welcome", content="Hello world",
                    section_type="quote", position=0),
            Section(title="Currently", slug="currently",
                    content="Status: Testing\nMood: Focused",
                    section_type="currently", position=1),
            Section(title="Skills", slug="skills",
                    content="Python, JavaScript, Vue",
                    section_type="pills", position=2),
        ]
        db.session.add_all(sections)

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

        # --- Puzzles ---
        with open(SEED_PATH, encoding="utf-8") as f:
            seed_data = json.load(f)

        for idx, puzzle in enumerate(seed_data):
            db.session.add(KennoPuzzle(
                slot=idx, letters=",".join(puzzle["letters"]),
                created_at=now, updated_at=now))
            db.session.add(KennoConfig(
                key=f"center_{idx}", value=puzzle["center"]))

        db.session.commit()
        print(f"Seeded E2E database at {DB_PATH}")
        print(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"  User:  {USER_EMAIL} / {USER_PASSWORD}")
        print(f"  Sections: {len(sections)}")
        print(f"  Recipes: 1")
        print(f"  Puzzles: {len(seed_data)}")


if __name__ == "__main__":
    seed()
