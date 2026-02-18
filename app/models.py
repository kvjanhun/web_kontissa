from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
        }


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "content": self.content,
        }


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    author = db.relationship("User", backref="recipes")
    ingredients = db.relationship(
        "Ingredient", backref="recipe", cascade="all, delete-orphan",
        order_by="Ingredient.position"
    )
    steps = db.relationship(
        "Step", backref="recipe", cascade="all, delete-orphan",
        order_by="Step.position"
    )

    def to_dict(self, include_children=False):
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "category": self.category,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() + "Z",
        }
        if include_children:
            data["ingredients"] = [i.to_dict() for i in self.ingredients]
            data["steps"] = [s.to_dict() for s in self.steps]
        return data


class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    amount = db.Column(db.String(50), nullable=True)
    unit = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "unit": self.unit,
            "name": self.name,
            "position": self.position,
        }


class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipe.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    content = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "position": self.position,
            "content": self.content,
        }
