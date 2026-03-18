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
    slug = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    section_type = db.Column(db.String, nullable=False, default='text')
    position = db.Column(db.Integer, nullable=True, default=0)
    collapsible = db.Column(db.Boolean, nullable=False, default=False)
    locale = db.Column(db.String(5), nullable=False, default='en')
    hidden = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint('slug', 'locale', name='uq_section_slug_locale'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "content": self.content,
            "section_type": self.section_type,
            "position": self.position,
            "collapsible": self.collapsible,
            "locale": self.locale,
            "hidden": self.hidden,
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


class BlockedWord(db.Model):
    """Admin-curated list of words excluded from all Sanakenno puzzles."""
    __tablename__ = 'blocked_words'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    blocked_at = db.Column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))


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


class KennoConfig(db.Model):
    """Key-value store for Sanakenno puzzle scheduling state."""
    __tablename__ = 'bee_config'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=False)


class KennoPuzzle(db.Model):
    """Sanakenno puzzle slots with 7 letters each."""
    __tablename__ = 'bee_puzzles'
    slot = db.Column(db.Integer, primary_key=True)
    letters = db.Column(db.String(50), nullable=False)  # comma-separated: "a,e,k,l,n,s,ö"
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class KennoCombination(db.Model):
    """Pre-computed 7-letter combinations that have at least one pangram."""
    __tablename__ = 'bee_combinations'
    # Sorted 7-char string, e.g. "aeklnös"
    letters = db.Column(db.String(7), primary_key=True)
    total_pangrams = db.Column(db.Integer, nullable=False, index=True)
    min_word_count = db.Column(db.Integer, nullable=False, index=True)
    max_word_count = db.Column(db.Integer, nullable=False, index=True)
    min_max_score = db.Column(db.Integer, nullable=False)
    max_max_score = db.Column(db.Integer, nullable=False)
    # Per-center variations stored as JSON array of 7 objects
    variations = db.Column(db.Text, nullable=False)
    # Whether this combination is already used in a KennoPuzzle slot
    in_rotation = db.Column(db.Boolean, nullable=False, default=False, index=True)

    def to_dict(self):
        import json
        return {
            "letters": self.letters,
            "total_pangrams": self.total_pangrams,
            "min_word_count": self.min_word_count,
            "max_word_count": self.max_word_count,
            "min_max_score": self.min_max_score,
            "max_max_score": self.max_max_score,
            "variations": json.loads(self.variations),
            "in_rotation": self.in_rotation,
        }


class KennoAchievement(db.Model):
    """Records when anonymous players reach rank milestones in Sanakenno."""
    __tablename__ = 'bee_achievements'
    id = db.Column(db.Integer, primary_key=True)
    puzzle_number = db.Column(db.Integer, nullable=False)
    rank = db.Column(db.String(50), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    words_found = db.Column(db.Integer, nullable=False)
    elapsed_ms = db.Column(db.Integer, nullable=True)
    achieved_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
