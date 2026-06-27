"""Database-backed home-page content (Stage 2).

The public home page reads every `home.*` content key through this blueprint
instead of the bundled locale files. Fixed text blocks live in `HomeContent`
(one row per key+locale); the projects collection lives in `Project` +
`ProjectTranslation` and is surfaced under the synthetic `home.projects` key.

Conventions mirror app/routes.py (sections) and app/recipes.py: JSON only,
`@admin_required` on mutations, 400/403/404/409 status codes.
"""
import json

from flask import Blueprint, request, jsonify
from .models import db, HomeContent, Project, ProjectTranslation
from .decorators import admin_required
from . import limiter

home_content_bp = Blueprint("home_content", __name__)

LOCALES = ("en", "fi")

# Editable home.* keys → expected value shape. Keep in sync with the field groups
# in frontend/components/admin/AdminHomeContent.vue.
FIELD_STRING = "string"
FIELD_STRING_LIST = "string[]"      # taglines
FIELD_LAYER_LIST = "layer[]"        # [{z, layer, title, detail}]
FIELD_LINK_LIST = "link[]"          # [{label, href}]

HOME_CONTENT_FIELDS = {
    "home.hero.eyebrow": FIELD_STRING,
    "home.hero.taglines": FIELD_STRING_LIST,
    "home.hero.titleLine2": FIELD_STRING,
    "home.hero.body": FIELD_STRING,
    "home.hero.ctaPrimary": FIELD_STRING,
    "home.hero.ctaSecondary": FIELD_STRING,
    "home.stack.label": FIELD_STRING,
    "home.stack.tag": FIELD_STRING,
    "home.stack.intro": FIELD_STRING,
    "home.stack.footnote": FIELD_STRING,
    "home.stack.layers": FIELD_LAYER_LIST,
    "home.footer.blurb": FIELD_STRING,
    "home.footer.nuc": FIELD_STRING,
    "home.footer.copyright": FIELD_STRING,
    "home.footer.connectLinks": FIELD_LINK_LIST,
    "home.footer.siteLinks": FIELD_LINK_LIST,
}

MAX_PROJECTS = 50
MAX_TECH = 30
MAX_LINKS = 10


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def _validate_field_value(kind, value):
    """Validate a HomeContent value against its declared shape. Returns
    (clean_value, error_string)."""
    if kind == FIELD_STRING:
        if not isinstance(value, str):
            return None, "value must be a string"
        return value, None

    if kind == FIELD_STRING_LIST:
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            return None, "value must be a list of strings"
        cleaned = [v.strip() for v in value if v.strip()]
        if not cleaned:
            return None, "value must contain at least one non-empty string"
        return cleaned, None

    if kind == FIELD_LAYER_LIST:
        if not isinstance(value, list):
            return None, "value must be a list of layers"
        cleaned = []
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                return None, f"layer {i} is not an object"
            row = {f: (item.get(f) or "") for f in ("z", "layer", "title", "detail")}
            if not all(isinstance(v, str) for v in row.values()):
                return None, f"layer {i} fields must be strings"
            cleaned.append(row)
        return cleaned, None

    if kind == FIELD_LINK_LIST:
        cleaned, err = _validate_links(value)
        if err:
            return None, err
        return cleaned, None

    return None, "unknown field type"


def _validate_links(value):
    if not isinstance(value, list):
        return None, "links must be a list"
    if len(value) > MAX_LINKS:
        return None, f"too many links (max {MAX_LINKS})"
    cleaned = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            return None, f"link {i} is not an object"
        label = (item.get("label") or "").strip()
        href = (item.get("href") or "").strip()
        if not label or not href:
            return None, f"link {i} needs a label and href"
        cleaned.append({"label": label, "href": href})
    return cleaned, None


def _validate_tech(value):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return None, "tech must be a list of strings"
    if len(value) > MAX_TECH:
        return None, f"too many tech tags (max {MAX_TECH})"
    return [v.strip() for v in value if v.strip()], None


def _apply_translation(trans, data):
    """Validate and copy a translation payload onto a ProjectTranslation. Returns
    an error string or None."""
    name = (data.get("name") or "").strip()
    if not name:
        return "each translation needs a name"

    tech, err = _validate_tech(data.get("tech", []))
    if err:
        return err
    links, err = _validate_links(data.get("links", []))
    if err:
        return err

    trans.name = name
    trans.kind = (data.get("kind") or "").strip() or None
    trans.tagline = (data.get("tagline") or "").strip() or None
    trans.description = (data.get("description") or "").strip() or None
    trans.shot = (data.get("shot") or "").strip() or None
    trans.tech = json.dumps(tech)
    trans.links = json.dumps(links)
    return None


def _home_content_map(locale):
    """Assemble the full overlay map the frontend merges over its bundled
    fallbacks: every stored HomeContent key plus the assembled project list."""
    rows = HomeContent.query.filter(HomeContent.locale == locale).all()
    out = {r.key: json.loads(r.value) for r in rows}
    projects = (
        Project.query.filter_by(hidden=False)
        .order_by(Project.position.asc(), Project.id.asc())
        .all()
    )
    out["home.projects"] = [p.to_public_dict(locale) for p in projects]
    return out


# --------------------------------------------------------------------------- #
# Public
# --------------------------------------------------------------------------- #
@home_content_bp.route("/api/home-content")
@limiter.exempt
def api_home_content():
    """Public overlay map for the landing page. Exempt from the limiter because
    the home page depends on it for every visit (like `/` and the catch-all)."""
    locale = request.args.get("locale", "en").strip()
    if locale not in LOCALES:
        locale = "en"
    return jsonify(_home_content_map(locale))


# --------------------------------------------------------------------------- #
# Admin — fixed text blocks
# --------------------------------------------------------------------------- #
@home_content_bp.route("/api/admin/home-content")
@admin_required
def api_admin_home_content():
    """All editable fields for both locales, for the editor."""
    out = {loc: {} for loc in LOCALES}
    for row in HomeContent.query.all():
        if row.locale in out and row.key in HOME_CONTENT_FIELDS:
            out[row.locale][row.key] = json.loads(row.value)
    return jsonify(out)


@home_content_bp.route("/api/admin/home-content", methods=["PUT"])
@admin_required
def api_update_home_content():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    key = (data.get("key") or "").strip()
    locale = (data.get("locale") or "").strip()
    if key not in HOME_CONTENT_FIELDS:
        return jsonify({"error": "Unknown content key"}), 400
    if locale not in LOCALES:
        return jsonify({"error": "locale must be 'en' or 'fi'"}), 400
    if "value" not in data:
        return jsonify({"error": "value is required"}), 400

    clean, err = _validate_field_value(HOME_CONTENT_FIELDS[key], data["value"])
    if err:
        return jsonify({"error": err}), 400

    row = HomeContent.query.filter_by(key=key, locale=locale).first()
    if row is None:
        row = HomeContent(key=key, locale=locale, value=json.dumps(clean))
        db.session.add(row)
    else:
        row.value = json.dumps(clean)
    db.session.commit()
    return jsonify(row.to_dict())


# --------------------------------------------------------------------------- #
# Admin — projects collection
# --------------------------------------------------------------------------- #
@home_content_bp.route("/api/admin/projects")
@admin_required
def api_list_projects():
    projects = Project.query.order_by(Project.position.asc(), Project.id.asc()).all()
    return jsonify([p.to_admin_dict() for p in projects])


@home_content_bp.route("/api/admin/projects", methods=["POST"])
@admin_required
def api_create_project():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    if Project.query.count() >= MAX_PROJECTS:
        return jsonify({"error": f"Too many projects (max {MAX_PROJECTS})"}), 400

    translations = data.get("translations") or {}
    if not isinstance(translations, dict) or "en" not in translations:
        return jsonify({"error": "translations.en is required"}), 400

    max_pos = db.session.query(db.func.max(Project.position)).scalar()
    project = Project(
        position=(max_pos + 1) if max_pos is not None else 0,
        hidden=bool(data.get("hidden", False)),
        image=(data.get("image") or "").strip() or None,
    )
    for locale in LOCALES:
        if locale in translations:
            trans = ProjectTranslation(locale=locale)
            err = _apply_translation(trans, translations[locale])
            if err:
                return jsonify({"error": f"{locale}: {err}"}), 400
            project.translations.append(trans)

    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_admin_dict()), 201


@home_content_bp.route("/api/admin/projects/<int:project_id>", methods=["PUT"])
@admin_required
def api_update_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    if "image" in data:
        project.image = (data["image"] or "").strip() or None
    if "hidden" in data:
        project.hidden = bool(data["hidden"])
    if "position" in data:
        if not isinstance(data["position"], int) or data["position"] < 0:
            return jsonify({"error": "position must be a non-negative integer"}), 400
        project.position = data["position"]

    translations = data.get("translations")
    if translations is not None:
        if not isinstance(translations, dict):
            return jsonify({"error": "translations must be an object"}), 400
        existing = {t.locale: t for t in project.translations}
        for locale, payload in translations.items():
            if locale not in LOCALES:
                return jsonify({"error": f"unknown locale '{locale}'"}), 400
            trans = existing.get(locale)
            if trans is None:
                trans = ProjectTranslation(locale=locale)
                project.translations.append(trans)
            err = _apply_translation(trans, payload)
            if err:
                return jsonify({"error": f"{locale}: {err}"}), 400

    db.session.commit()
    return jsonify(project.to_admin_dict())


@home_content_bp.route("/api/admin/projects/<int:project_id>", methods=["DELETE"])
@admin_required
def api_delete_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"})


@home_content_bp.route("/api/admin/projects/reorder", methods=["PUT"])
@admin_required
def api_reorder_projects():
    data = request.get_json()
    if not data or not isinstance(data.get("order"), list):
        return jsonify({"error": "order (list of project IDs) required"}), 400

    order = data["order"]
    if not all(isinstance(i, int) for i in order):
        return jsonify({"error": "order must be a list of integers"}), 400

    projects = Project.query.all()
    project_map = {p.id: p for p in projects}
    for pid in order:
        if pid not in project_map:
            return jsonify({"error": f"Project {pid} not found"}), 404

    for position, pid in enumerate(order):
        project_map[pid].position = position
    db.session.commit()
    return jsonify({"message": "Projects reordered"})
