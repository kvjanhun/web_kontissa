"""Tests for SQLAlchemy model constraints, defaults, relationships, and serialization."""

import json
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from app.models import (
    BlockedWord,
    Ingredient,
    KennoCombination,
    PageViewEvent,
    Recipe,
    Section,
    Step,
    User,
    db,
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

# The test environment runs Python 3.9 which lacks hashlib.scrypt.
# Use pbkdf2:sha256 explicitly throughout, matching the conftest pattern.
_HASH = generate_password_hash("testpw", method="pbkdf2:sha256")


class TestUser:
    def test_check_password_correct(self, app):
        with app.app_context():
            user = User(username="alice", email="alice@example.com")
            user.password_hash = generate_password_hash("correct", method="pbkdf2:sha256")
            assert user.check_password("correct") is True
            assert user.check_password("wrong") is False

    def test_password_hash_is_not_plaintext(self, app):
        with app.app_context():
            user = User(username="bob", email="bob@example.com")
            user.password_hash = generate_password_hash("s3cr3t", method="pbkdf2:sha256")
            assert "s3cr3t" not in user.password_hash

    def test_default_role_is_user(self, app):
        with app.app_context():
            user = User(username="carol", email="carol@example.com", password_hash=_HASH)
            db.session.add(user)
            db.session.commit()
            assert user.role == "user"

    def test_to_dict_excludes_password_hash(self, app):
        with app.app_context():
            user = User(username="dave", email="dave@example.com", role="admin", password_hash=_HASH)
            db.session.add(user)
            db.session.commit()
            d = user.to_dict()
            assert "password_hash" not in d
            assert d["username"] == "dave"
            assert d["email"] == "dave@example.com"
            assert d["role"] == "admin"
            assert "id" in d

    def test_username_must_be_unique(self, app, admin_user):
        with app.app_context():
            duplicate = User(username="admin", email="other@example.com", password_hash=_HASH)
            db.session.add(duplicate)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_email_must_be_unique(self, app, admin_user):
        with app.app_context():
            duplicate = User(username="different_name", email="admin@test.com", password_hash=_HASH)
            db.session.add(duplicate)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class TestSection:
    def test_defaults(self, app):
        with app.app_context():
            s = Section(slug="intro", title="Intro", content="Hello")
            db.session.add(s)
            db.session.commit()
            assert s.section_type == "text"
            assert s.position == 0
            assert s.collapsible is False
            assert s.locale == "en"
            assert s.hidden is False

    def test_slug_locale_unique_constraint(self, app):
        with app.app_context():
            s1 = Section(slug="about", title="About", content="c", locale="en")
            db.session.add(s1)
            db.session.commit()

            s2 = Section(slug="about", title="About EN dup", content="c", locale="en")
            db.session.add(s2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_same_slug_different_locale_is_allowed(self, app):
        with app.app_context():
            s_en = Section(slug="about", title="About", content="c", locale="en")
            s_fi = Section(slug="about", title="Tietoa", content="c", locale="fi")
            db.session.add_all([s_en, s_fi])
            db.session.commit()
            assert s_en.id != s_fi.id

    def test_to_dict_returns_all_fields(self, app):
        with app.app_context():
            s = Section(
                slug="work",
                title="Work",
                content="content body",
                section_type="pills",
                position=5,
                collapsible=True,
                locale="fi",
                hidden=True,
            )
            db.session.add(s)
            db.session.commit()
            d = s.to_dict()
            assert d["slug"] == "work"
            assert d["title"] == "Work"
            assert d["content"] == "content body"
            assert d["section_type"] == "pills"
            assert d["position"] == 5
            assert d["collapsible"] is True
            assert d["locale"] == "fi"
            assert d["hidden"] is True
            assert "id" in d


# ---------------------------------------------------------------------------
# Recipe — cascade deletes, unique slug, timestamps, serialization
# ---------------------------------------------------------------------------

class TestRecipe:
    def _create_recipe_with_children(self, app, admin_user, slug="test-recipe"):
        with app.app_context():
            recipe = Recipe(title="Test Recipe", slug=slug, created_by=admin_user["id"])
            db.session.add(recipe)
            db.session.flush()
            for i in range(3):
                db.session.add(Ingredient(recipe_id=recipe.id, name=f"Ingredient {i}", position=i))
            for i in range(2):
                db.session.add(Step(recipe_id=recipe.id, content=f"Step {i}", position=i))
            db.session.commit()
            return recipe.id

    def test_delete_cascades_to_ingredients(self, app, admin_user):
        rid = self._create_recipe_with_children(app, admin_user)
        with app.app_context():
            recipe = db.session.get(Recipe, rid)
            db.session.delete(recipe)
            db.session.commit()
            assert db.session.query(Ingredient).filter_by(recipe_id=rid).count() == 0

    def test_delete_cascades_to_steps(self, app, admin_user):
        rid = self._create_recipe_with_children(app, admin_user)
        with app.app_context():
            recipe = db.session.get(Recipe, rid)
            db.session.delete(recipe)
            db.session.commit()
            assert db.session.query(Step).filter_by(recipe_id=rid).count() == 0

    def test_slug_must_be_unique(self, app, admin_user):
        with app.app_context():
            r1 = Recipe(title="Soup", slug="dup-slug", created_by=admin_user["id"])
            db.session.add(r1)
            db.session.commit()

            r2 = Recipe(title="Salad", slug="dup-slug", created_by=admin_user["id"])
            db.session.add(r2)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_created_at_defaults_to_utc_now(self, app, admin_user):
        with app.app_context():
            recipe = Recipe(title="Timed", slug="timed-recipe", created_by=admin_user["id"])
            db.session.add(recipe)
            db.session.commit()
            assert isinstance(recipe.created_at, datetime)

    def test_to_dict_without_children_omits_ingredients_and_steps(self, app, admin_user):
        with app.app_context():
            recipe = Recipe(title="Simple", slug="simple-recipe", created_by=admin_user["id"])
            db.session.add(recipe)
            db.session.commit()
            d = recipe.to_dict()
            assert "ingredients" not in d
            assert "steps" not in d
            assert d["title"] == "Simple"
            assert "created_at" in d

    def test_to_dict_with_children_includes_ingredients_and_steps(self, app, admin_user):
        rid = self._create_recipe_with_children(app, admin_user)
        with app.app_context():
            recipe = db.session.get(Recipe, rid)
            d = recipe.to_dict(include_children=True)
            assert len(d["ingredients"]) == 3
            assert len(d["steps"]) == 2

    def test_ingredients_ordered_by_position(self, app, admin_user):
        with app.app_context():
            recipe = Recipe(title="Ordered", slug="ordered-recipe", created_by=admin_user["id"])
            db.session.add(recipe)
            db.session.flush()
            db.session.add(Ingredient(recipe_id=recipe.id, name="C", position=2))
            db.session.add(Ingredient(recipe_id=recipe.id, name="A", position=0))
            db.session.add(Ingredient(recipe_id=recipe.id, name="B", position=1))
            db.session.commit()
            names = [i.name for i in recipe.ingredients]
            assert names == ["A", "B", "C"]

    def test_steps_ordered_by_position(self, app, admin_user):
        with app.app_context():
            recipe = Recipe(title="Steps", slug="steps-recipe", created_by=admin_user["id"])
            db.session.add(recipe)
            db.session.flush()
            db.session.add(Step(recipe_id=recipe.id, content="Last", position=2))
            db.session.add(Step(recipe_id=recipe.id, content="First", position=0))
            db.session.add(Step(recipe_id=recipe.id, content="Middle", position=1))
            db.session.commit()
            contents = [s.content for s in recipe.steps]
            assert contents == ["First", "Middle", "Last"]


# ---------------------------------------------------------------------------
# BlockedWord
# ---------------------------------------------------------------------------

class TestBlockedWord:
    def test_word_must_be_unique(self, app):
        with app.app_context():
            db.session.add(BlockedWord(word="kissa"))
            db.session.commit()

            db.session.add(BlockedWord(word="kissa"))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_blocked_at_defaults_to_now(self, app):
        with app.app_context():
            bw = BlockedWord(word="koira")
            db.session.add(bw)
            db.session.commit()
            assert isinstance(bw.blocked_at, datetime)


# ---------------------------------------------------------------------------
# PageViewEvent
# ---------------------------------------------------------------------------

class TestPageViewEvent:
    def test_timestamp_defaults_to_utc_now(self, app):
        with app.app_context():
            event = PageViewEvent(path="/about")
            db.session.add(event)
            db.session.commit()
            assert isinstance(event.timestamp, datetime)

    def test_multiple_events_for_same_path(self, app):
        with app.app_context():
            for _ in range(5):
                db.session.add(PageViewEvent(path="/about"))
            db.session.commit()
            count = db.session.query(PageViewEvent).filter_by(path="/about").count()
            assert count == 5


# ---------------------------------------------------------------------------
# KennoCombination
# ---------------------------------------------------------------------------

class TestKennoCombination:
    def _make_combo(self, app, letters="aeklnst"):
        variations = [{"center": c, "word_count": 10 + i} for i, c in enumerate(letters)]
        combo = KennoCombination(
            letters=letters,
            total_pangrams=2,
            min_word_count=50,
            max_word_count=80,
            min_max_score=100,
            max_max_score=200,
            variations=json.dumps(variations),
            in_rotation=False,
        )
        with app.app_context():
            db.session.add(combo)
            db.session.commit()
        return letters

    def test_to_dict_deserializes_variations_from_json(self, app):
        letters = self._make_combo(app)
        with app.app_context():
            combo = db.session.get(KennoCombination, letters)
            d = combo.to_dict()
            assert isinstance(d["variations"], list)
            assert len(d["variations"]) == 7
            assert d["variations"][0]["center"] == letters[0]

    def test_to_dict_includes_all_fields(self, app):
        letters = self._make_combo(app)
        with app.app_context():
            combo = db.session.get(KennoCombination, letters)
            d = combo.to_dict()
            assert d["letters"] == letters
            assert d["total_pangrams"] == 2
            assert d["min_word_count"] == 50
            assert d["max_word_count"] == 80
            assert d["min_max_score"] == 100
            assert d["max_max_score"] == 200
            assert d["in_rotation"] is False

    def test_in_rotation_flag_persists(self, app):
        letters = self._make_combo(app)
        with app.app_context():
            combo = db.session.get(KennoCombination, letters)
            combo.in_rotation = True
            db.session.commit()
            refreshed = db.session.get(KennoCombination, letters)
            assert refreshed.in_rotation is True
