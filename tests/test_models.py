"""Tests for SQLAlchemy model constraints, defaults, relationships, and serialization."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from app.models import (
    HomeContent,
    Ingredient,
    PageViewEvent,
    Project,
    ProjectTranslation,
    Recipe,
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
# HomeContent
# ---------------------------------------------------------------------------

class TestHomeContent:
    def test_key_locale_unique_constraint(self, app):
        with app.app_context():
            db.session.add(HomeContent(key="home.hero.body", locale="en", value='"a"'))
            db.session.commit()
            db.session.add(HomeContent(key="home.hero.body", locale="en", value='"b"'))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_same_key_different_locale_allowed(self, app):
        with app.app_context():
            en = HomeContent(key="home.hero.body", locale="en", value='"hi"')
            fi = HomeContent(key="home.hero.body", locale="fi", value='"hei"')
            db.session.add_all([en, fi])
            db.session.commit()
            assert en.id != fi.id

    def test_to_dict_parses_json_value(self, app):
        with app.app_context():
            row = HomeContent(key="home.hero.taglines", locale="en", value='["a", "b"]')
            db.session.add(row)
            db.session.commit()
            d = row.to_dict()
            assert d["key"] == "home.hero.taglines"
            assert d["locale"] == "en"
            assert d["value"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Project + ProjectTranslation
# ---------------------------------------------------------------------------

class TestProject:
    def _project(self, **kwargs):
        p = Project(position=kwargs.get("position", 0), hidden=kwargs.get("hidden", False),
                    image=kwargs.get("image", "/x.webp"))
        p.translations.append(ProjectTranslation(
            locale="en", name="Sanakenno", kind="product", tagline="t", description="d",
            shot="s", tech='["React"]', links='[{"label": "site", "href": "https://x"}]',
        ))
        p.translations.append(ProjectTranslation(locale="fi", name="Sanakenno", kind="tuote"))
        return p

    def test_defaults(self, app):
        with app.app_context():
            p = Project()
            db.session.add(p)
            db.session.commit()
            assert p.position == 0
            assert p.hidden is False

    def test_translation_unique_per_locale(self, app):
        with app.app_context():
            p = Project()
            p.translations.append(ProjectTranslation(locale="en", name="A"))
            p.translations.append(ProjectTranslation(locale="en", name="B"))
            db.session.add(p)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_delete_cascades_to_translations(self, app):
        with app.app_context():
            p = self._project()
            db.session.add(p)
            db.session.commit()
            pid = p.id
            db.session.delete(p)
            db.session.commit()
            assert db.session.query(ProjectTranslation).filter_by(project_id=pid).count() == 0

    def test_to_public_dict_matches_home_shape(self, app):
        with app.app_context():
            p = self._project()
            db.session.add(p)
            db.session.commit()
            d = p.to_public_dict("en")
            assert d["name"] == "Sanakenno"
            assert d["kind"] == "product"
            assert d["tech"] == ["React"]
            assert d["links"] == [{"label": "site", "href": "https://x"}]
            assert d["image"] == "/x.webp"

    def test_to_public_dict_falls_back_to_en(self, app):
        with app.app_context():
            p = Project(image="/x.webp")
            p.translations.append(ProjectTranslation(locale="en", name="Only EN"))
            db.session.add(p)
            db.session.commit()
            # No 'fi' translation -> falls back to en
            assert p.to_public_dict("fi")["name"] == "Only EN"

    def test_to_admin_dict_includes_both_translations(self, app):
        with app.app_context():
            p = self._project()
            db.session.add(p)
            db.session.commit()
            d = p.to_admin_dict()
            assert set(d["translations"].keys()) == {"en", "fi"}
            assert d["image"] == "/x.webp"


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
