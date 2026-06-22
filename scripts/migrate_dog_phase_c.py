#!/usr/bin/env python3
"""Phase C schema migration for an existing dog.db.

Adds the fields the full-data backfill captures, on a database that already
holds Phase B data:

  - dog_result.competitive_placement  (new nullable column; ALTER TABLE)
  - dog_breed_award                    (new table; created by create_all)

Idempotent and additive: it never drops or rewrites existing rows, only adds the
missing column/table. Safe to run repeatedly. Pre-Phase-C rows simply have NULL
competitive_placement and no honor-roll rows until those shows are (re)crawled.

    SECRET_KEY=dev python3 scripts/migrate_dog_phase_c.py            # default dog.db
    DOG_DATABASE_URI=... SECRET_KEY=dev python3 scripts/migrate_dog_phase_c.py

On the NUC, run it the same way as the Phase B migration — in a one-off
container against the bind mount, e.g.:

    docker compose run --rm web python scripts/migrate_dog_phase_c.py
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("DOG_NO_CRAWLER", "true")
os.environ.setdefault("SECRET_KEY", "dog-migrate-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")  # in-memory; only dog.db is touched

import structlog  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from app.dog_show import config, db as dog_db  # noqa: E402

logger = structlog.get_logger(__name__)


def migrate():
    # init_db creates any missing tables (incl. the new dog_breed_award) and binds
    # the engine; it never alters existing tables.
    dog_db.init_db()
    engine = dog_db.get_engine()
    insp = inspect(engine)

    actions = []

    cols = {c["name"] for c in insp.get_columns("dog_result")}
    if "competitive_placement" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE dog_result ADD COLUMN competitive_placement TEXT"))
        actions.append("added dog_result.competitive_placement")
    else:
        actions.append("dog_result.competitive_placement already present")

    if insp.has_table("dog_breed_award"):
        actions.append("dog_breed_award table present")
    else:  # create_all in init_db should have made it; surface if not
        actions.append("WARNING: dog_breed_award table missing after init_db")

    logger.info("dog_migrate_phase_c_done", uri=config.DOG_DATABASE_URI, actions=actions)
    for a in actions:
        print(f"  {a}")
    print("OK: dog.db Phase C schema is up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(migrate())
