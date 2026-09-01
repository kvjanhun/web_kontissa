"""Add the `project.layers` column (one-off schema change).

`layers` holds a JSON array of stack-layer tokens ("L1".."L7") that a project
touches, rendered as chips linking to the home page's stack table. It is
language-independent, so it lives on `project` rather than `project_translation`.

This repo has no migration runner and `db.create_all()` does not alter existing
tables, so the column is added by hand — see `CLAUDE.md` and the `schema-change`
skill. Additive and defaulted, so code that predates the column keeps working
against the new schema; that is the rollback.

Re-runnable: checks the table first and exits cleanly if the column is present.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 scripts/add_project_layers_column.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dev-host fallback only — see scripts/prune_pageview_events.py for the full
# rationale. In the container the repo root *is* /app and the environment is
# already authoritative.
if not (ROOT == "/app" and os.path.isdir("/app/data")):
    os.environ.setdefault("DATABASE_URI", f"sqlite:///{os.path.join(ROOT, 'app', 'data', 'site.db')}")

from sqlalchemy import text  # noqa: E402

from app import app  # noqa: E402
from app.models import db  # noqa: E402


def main():
    with app.app_context():
        columns = {row[1] for row in db.session.execute(text("PRAGMA table_info(project)")).all()}
        if not columns:
            print("No `project` table in this database — deploy the app first.")
            return 1
        if "layers" in columns:
            print("Already applied: project.layers exists. Nothing to do.")
            return 0

        db.session.execute(
            text("ALTER TABLE project ADD COLUMN layers TEXT NOT NULL DEFAULT '[]'")
        )
        db.session.commit()

        rows = db.session.execute(text("SELECT COUNT(*) FROM project")).scalar()
        print(f"Added project.layers. {rows} existing project(s) defaulted to [].")
        return 0


if __name__ == "__main__":
    sys.exit(main())
