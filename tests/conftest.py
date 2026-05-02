import os
import pytest

# Set test database URI before importing the app, so __init__.py picks it up
os.environ["DATABASE_URI"] = "sqlite://"  # in-memory, overridden per-test below


from app import app as flask_app, limiter
from app.models import db, User, Section, Recipe, Ingredient, Step
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "test.db"
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-secret",
    })
    limiter.enabled = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_user(app):
    with app.app_context():
        user = User(username="admin", email="admin@test.com", role="admin")
        user.password_hash = generate_password_hash("adminpass", method="pbkdf2:sha256")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "email": "admin@test.com", "password": "adminpass"}


@pytest.fixture()
def regular_user(app):
    with app.app_context():
        user = User(username="user", email="user@test.com", role="user")
        user.password_hash = generate_password_hash("userpass", method="pbkdf2:sha256")
        db.session.add(user)
        db.session.commit()
        return {"id": user.id, "email": "user@test.com", "password": "userpass"}


@pytest.fixture()
def logged_in_admin(client, admin_user):
    client.post("/api/login", json={
        "email": admin_user["email"],
        "password": admin_user["password"],
    })
    return client


@pytest.fixture()
def logged_in_user(client, regular_user):
    client.post("/api/login", json={
        "email": regular_user["email"],
        "password": regular_user["password"],
    })
    return client


@pytest.fixture()
def sample_section(app):
    with app.app_context():
        section = Section(title="Test Section", slug="test", content="<p>Hello</p>")
        db.session.add(section)
        db.session.commit()
        return {"id": section.id, "slug": "test"}


@pytest.fixture()
def sample_recipe(app, regular_user):
    with app.app_context():
        recipe = Recipe(
            title="Pancakes",
            slug="pancakes",
            category="Breakfast",
            created_by=regular_user["id"],
        )
        recipe.ingredients = [
            Ingredient(name="Flour", amount="2", unit="cups", position=0),
            Ingredient(name="Eggs", amount="2", unit=None, position=1),
            Ingredient(name="Milk", amount="1", unit="cup", position=2),
        ]
        recipe.steps = [
            Step(content="Mix dry ingredients", position=0),
            Step(content="Add wet ingredients and stir", position=1),
            Step(content="Cook on griddle until golden", position=2),
        ]
        db.session.add(recipe)
        db.session.commit()
        return {"id": recipe.id, "slug": "pancakes"}
