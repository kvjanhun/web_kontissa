import json
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


class HomeContent(db.Model):
    """Editable home-page text block. One row per (key, locale).

    `value` holds a JSON-encoded scalar string or array, matching the shape the
    home components already expect for that `home.*` key (a plain string for the
    intro/taglines line, an array for taglines / stack layers / footer links).
    Pattern #1 (locale column on the same table): these are pure translatable
    values with no language-independent attributes, so a locale column is the
    right amount of structure.
    """
    __tablename__ = "home_content"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), nullable=False)
    locale = db.Column(db.String(5), nullable=False, default="en")
    value = db.Column(db.Text, nullable=False)  # JSON-encoded scalar or array

    __table_args__ = (
        db.UniqueConstraint("key", "locale", name="uq_home_content_key_locale"),
    )

    def to_dict(self):
        return {"key": self.key, "locale": self.locale, "value": json.loads(self.value)}


class Project(db.Model):
    """A portfolio project — the one home-content collection (add/remove/hide/reorder).

    Language-independent attributes (order, visibility, image path) live here so
    they are stored once and the EN/FI views can never drift. Translatable text
    lives in ProjectTranslation, one row per locale (pattern #2: translations table).
    """
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    hidden = db.Column(db.Boolean, nullable=False, default=False)
    image = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    translations = db.relationship(
        "ProjectTranslation", backref="project",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def _translation(self, locale):
        by_locale = {t.locale: t for t in self.translations}
        return by_locale.get(locale) or by_locale.get("en") or (self.translations[0] if self.translations else None)

    def to_public_dict(self, locale="en"):
        """The exact shape `home.projects` expects, for a single locale."""
        t = self._translation(locale)
        data = t.to_dict() if t else {
            "name": "", "kind": "", "tagline": "", "description": "", "shot": "", "tech": [], "links": [],
        }
        data["image"] = self.image
        return data

    def to_admin_dict(self):
        """Parent fields plus all translations keyed by locale, for the editor."""
        return {
            "id": self.id,
            "position": self.position,
            "hidden": self.hidden,
            "image": self.image,
            "translations": {t.locale: t.to_dict() for t in self.translations},
        }


class ProjectTranslation(db.Model):
    __tablename__ = "project_translation"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    locale = db.Column(db.String(5), nullable=False, default="en")
    name = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(120), nullable=True)
    tagline = db.Column(db.String, nullable=True)
    description = db.Column(db.Text, nullable=True)
    shot = db.Column(db.String, nullable=True)
    tech = db.Column(db.Text, nullable=False, default="[]")   # JSON array of strings
    links = db.Column(db.Text, nullable=False, default="[]")  # JSON array of {label, href}

    __table_args__ = (
        db.UniqueConstraint("project_id", "locale", name="uq_project_translation_locale"),
    )

    def to_dict(self):
        return {
            "name": self.name,
            "kind": self.kind or "",
            "tagline": self.tagline or "",
            "description": self.description or "",
            "shot": self.shot or "",
            "tech": json.loads(self.tech or "[]"),
            "links": json.loads(self.links or "[]"),
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


class PageView(db.Model):
    """Per-path page view counter. Single row per path, upserted on each hit."""
    __tablename__ = 'page_views'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(200), unique=True, nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))


class PageViewEvent(db.Model):
    """Individual page view event with timestamp for time-series analytics."""
    __tablename__ = 'page_view_events'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(200), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
