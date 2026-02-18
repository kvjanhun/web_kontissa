import re
from flask import request, jsonify
from flask_login import login_required, current_user
from .models import db, Recipe, Ingredient, Step
from . import app

VALID_CATEGORIES = [
    "Breakfast", "Lunch", "Dinner", "Dessert",
    "Snack", "Baking", "Drinks", "Other",
]

MAX_INGREDIENTS = 100
MAX_STEPS = 200


def slugify(text):
    """Convert text to URL-friendly slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


def unique_slug(title):
    """Generate a unique slug, appending -2, -3, etc. if needed."""
    base = slugify(title)
    if not base:
        base = "recipe"
    slug = base
    counter = 2
    while Recipe.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _parse_ingredients(items):
    """Validate and parse ingredient dicts."""
    ingredients = []
    for i, item in enumerate(items):
        name = (item.get("name") or "").strip()
        if not name:
            return None, f"Ingredient at position {i} is missing a name"
        ingredients.append(Ingredient(
            amount=(item.get("amount") or "").strip() or None,
            unit=(item.get("unit") or "").strip() or None,
            name=name,
            position=i,
        ))
    return ingredients, None


def _parse_steps(items):
    """Validate and parse step dicts."""
    steps = []
    for i, item in enumerate(items):
        content = (item.get("content") or "").strip() if isinstance(item, dict) else (item or "").strip()
        if not content:
            return None, f"Step at position {i} is empty"
        steps.append(Step(
            position=i,
            content=content,
        ))
    return steps, None


@app.route("/api/recipes/categories")
@login_required
def api_recipe_categories():
    return jsonify(VALID_CATEGORIES)


@app.route("/api/recipes")
@login_required
def api_list_recipes():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = Recipe.query

    if category:
        query = query.filter(Recipe.category == category)

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Recipe.title.ilike(pattern),
                Recipe.ingredients.any(Ingredient.name.ilike(pattern)),
            )
        )

    recipes = query.order_by(Recipe.created_at.desc()).all()
    return jsonify([r.to_dict() for r in recipes])


@app.route("/api/recipes/<slug>")
@login_required
def api_get_recipe(slug):
    recipe = Recipe.query.filter_by(slug=slug).first()
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404
    return jsonify(recipe.to_dict(include_children=True))


@app.route("/api/recipes", methods=["POST"])
@login_required
def api_create_recipe():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    category = (data.get("category") or "").strip() or None
    if category and category not in VALID_CATEGORIES:
        return jsonify({"error": f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"}), 400

    raw_ingredients = data.get("ingredients", [])
    if not raw_ingredients:
        return jsonify({"error": "At least one ingredient is required"}), 400
    if len(raw_ingredients) > MAX_INGREDIENTS:
        return jsonify({"error": f"Too many ingredients (max {MAX_INGREDIENTS})"}), 400

    raw_steps = data.get("steps", [])
    if not raw_steps:
        return jsonify({"error": "At least one step is required"}), 400
    if len(raw_steps) > MAX_STEPS:
        return jsonify({"error": f"Too many steps (max {MAX_STEPS})"}), 400

    ingredients, err = _parse_ingredients(raw_ingredients)
    if err:
        return jsonify({"error": err}), 400

    steps, err = _parse_steps(raw_steps)
    if err:
        return jsonify({"error": err}), 400

    recipe = Recipe(
        title=title,
        slug=unique_slug(title),
        category=category,
        created_by=current_user.id,
    )
    recipe.ingredients = ingredients
    recipe.steps = steps

    db.session.add(recipe)
    db.session.commit()
    return jsonify(recipe.to_dict(include_children=True)), 201


@app.route("/api/recipes/<int:recipe_id>", methods=["PUT"])
@login_required
def api_update_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    category = (data.get("category") or "").strip() or None
    if category and category not in VALID_CATEGORIES:
        return jsonify({"error": f"Invalid category. Must be one of: {', '.join(VALID_CATEGORIES)}"}), 400

    raw_ingredients = data.get("ingredients", [])
    if not raw_ingredients:
        return jsonify({"error": "At least one ingredient is required"}), 400
    if len(raw_ingredients) > MAX_INGREDIENTS:
        return jsonify({"error": f"Too many ingredients (max {MAX_INGREDIENTS})"}), 400

    raw_steps = data.get("steps", [])
    if not raw_steps:
        return jsonify({"error": "At least one step is required"}), 400
    if len(raw_steps) > MAX_STEPS:
        return jsonify({"error": f"Too many steps (max {MAX_STEPS})"}), 400

    ingredients, err = _parse_ingredients(raw_ingredients)
    if err:
        return jsonify({"error": err}), 400

    steps, err = _parse_steps(raw_steps)
    if err:
        return jsonify({"error": err}), 400

    # Regenerate slug if title changed
    if title != recipe.title:
        recipe.slug = unique_slug(title)
    recipe.title = title
    recipe.category = category

    # Replace all ingredients and steps
    recipe.ingredients = ingredients
    recipe.steps = steps

    db.session.commit()
    return jsonify(recipe.to_dict(include_children=True))


@app.route("/api/recipes/<int:recipe_id>", methods=["DELETE"])
@login_required
def api_delete_recipe(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    db.session.delete(recipe)
    db.session.commit()
    return jsonify({"message": "Recipe deleted"})
