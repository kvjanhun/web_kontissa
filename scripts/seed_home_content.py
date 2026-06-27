"""Populate the database-backed home content from the committed snapshot.

The snapshot (`frontend/locales/home-content.snapshot.json`) is the seed source of
record: it holds, per locale, every editable `home.*` field plus the assembled
`home.projects` list. This script writes those into the `home_content`,
`project`, and `project_translation` tables.

Used for:
  * local dev — point DATABASE_URI at app/data/site.db and run once
  * the production one-off migration (Stage 1 -> Stage 2)

By default it only seeds when the tables are empty. Pass --force to wipe the
home-content / project tables and reseed.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 scripts/seed_home_content.py [--force]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(ROOT, "frontend", "locales", "home-content.snapshot.json")

# Default to the dev site.db unless the caller overrides DATABASE_URI.
os.environ.setdefault("DATABASE_URI", f"sqlite:///{os.path.join(ROOT, 'app', 'data', 'site.db')}")

from app import app  # noqa: E402
from app.models import db, HomeContent, Project, ProjectTranslation  # noqa: E402
from app.home_content import HOME_CONTENT_FIELDS, LOCALES  # noqa: E402


def _load_snapshot():
    with open(SNAPSHOT_PATH, encoding="utf-8") as f:
        return json.load(f)


def _seed_fixed_blocks(snapshot):
    count = 0
    for locale in LOCALES:
        overlay = snapshot.get(locale, {})
        for key in HOME_CONTENT_FIELDS:
            if key not in overlay:
                continue
            db.session.add(HomeContent(key=key, locale=locale, value=json.dumps(overlay[key])))
            count += 1
    return count


def _seed_projects(snapshot):
    # The per-locale project lists are parallel (same order, same projects), so
    # zip them by index into one parent row + a translation per locale.
    per_locale = {loc: snapshot.get(loc, {}).get("home.projects", []) for loc in LOCALES}
    n = max((len(v) for v in per_locale.values()), default=0)
    for i in range(n):
        first = next((per_locale[loc][i] for loc in LOCALES if i < len(per_locale[loc])), {})
        project = Project(position=i, hidden=False, image=first.get("image") or None)
        for loc in LOCALES:
            items = per_locale[loc]
            if i >= len(items):
                continue
            p = items[i]
            project.translations.append(ProjectTranslation(
                locale=loc,
                name=p.get("name") or "",
                kind=(p.get("kind") or "") or None,
                tagline=(p.get("tagline") or "") or None,
                description=(p.get("description") or "") or None,
                shot=(p.get("shot") or "") or None,
                tech=json.dumps(p.get("tech") or []),
                links=json.dumps(p.get("links") or []),
            ))
        db.session.add(project)
    return n


def seed(force=False):
    snapshot = _load_snapshot()
    with app.app_context():
        db.engine.dispose()
        db.create_all()

        existing = HomeContent.query.count() + Project.query.count()
        if existing and not force:
            print(f"Home content already present ({existing} rows). Use --force to reseed. Skipping.")
            return

        if force:
            ProjectTranslation.query.delete()
            Project.query.delete()
            HomeContent.query.delete()

        blocks = _seed_fixed_blocks(snapshot)
        projects = _seed_projects(snapshot)
        db.session.commit()
        print(f"Seeded home content: {blocks} fixed fields, {projects} projects "
              f"(DB: {app.config['SQLALCHEMY_DATABASE_URI']})")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
