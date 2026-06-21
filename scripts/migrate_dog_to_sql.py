#!/usr/bin/env python3
"""One-off migration: dog JSON caches -> dog.db (Phase B).

Loads the current `dog_show_index.json`, every `dog_result_cache/<id>.json`, and
`dog_result_jobs.json` into the new SQLite dog database, then validates that each
record round-trips back to the exact structure the rest of the package and
`/api/dog/*` consume. Idempotent: it replaces all dog rows each run.

    SECRET_KEY=dev python3 scripts/migrate_dog_to_sql.py            # default paths
    SECRET_KEY=dev python3 scripts/migrate_dog_to_sql.py --validate-only

Source dir is DOG_INDEX_DIR (default ./app/data); target is DOG_DATABASE_URI
(default dog.db inside that dir).
"""

import argparse
import glob
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("DOG_NO_CRAWLER", "true")
os.environ.setdefault("SECRET_KEY", "dog-migrate-local-only")

import structlog  # noqa: E402

from app.dog_show import db as dog_db  # noqa: E402
from app.dog_show import indexing, sqlstore, store  # noqa: E402

logger = structlog.get_logger(__name__)


def _diff(a, b, path="$"):
    """Return a human description of the first structural difference, or None."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            only_a = set(a) - set(b)
            only_b = set(b) - set(a)
            return f"{path}: key mismatch (only_source={sorted(only_a)} only_sql={sorted(only_b)})"
        for k in a:
            d = _diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} != {b!r}"
    return None


def migrate(validate_only=False):
    dog_db.init_db()

    store._load_index(force=True)
    source_index = store._show_index
    result_ids = sorted(
        int(os.path.basename(p)[:-5])
        for p in glob.glob(os.path.join(store.RESULT_CACHE_DIR, "*.json"))
        if os.path.basename(p)[:-5].isdigit()
    )
    source_docs = {sid: store._load_result_cache_doc(sid) for sid in result_ids}
    source_jobs = store._load_result_jobs()

    # Consolidate: fold judges that only live in a result cache back into the
    # breed list, exactly as the running app does lazily on detail/search. This
    # makes the breed table the single source of truth for per-breed judges, so
    # reconstructed result breedObjs match and judge search covers these shows.
    backfilled = 0
    for sid, doc in source_docs.items():
        show = source_index.get("shows", {}).get(str(sid))
        if not show:
            continue
        breed_map = indexing._cached_result_breed_map(sid)
        if indexing._merge_breed_map_judges_into_breeds(show.get("breeds", []), breed_map):
            backfilled += 1
    if backfilled:
        logger.info("dog_migrate_judge_backfill", shows=backfilled)

    if not validate_only:
        with dog_db.session_scope() as session:
            sqlstore.write_index(session, source_index)
            for sid, doc in source_docs.items():
                if doc is not None:
                    sqlstore.write_result_doc(session, sid, doc)
            sqlstore.write_jobs(session, source_jobs)
        logger.info(
            "dog_migrate_written",
            shows=len(source_index.get("shows", {})),
            result_caches=len(source_docs),
            jobs=len(source_jobs.get("jobs", {})),
        )

    # ---- validate round-trip parity ----
    problems = []
    with dog_db.session_scope() as session:
        sql_index = sqlstore.read_index(session)
        d = _diff(source_index.get("shows", {}), sql_index.get("shows", {}), "$.shows")
        if d:
            problems.append(("index", d))
        if (source_index.get("last_updated") or 0) != (sql_index.get("last_updated") or 0):
            problems.append(("index.last_updated", f"{source_index.get('last_updated')} != {sql_index.get('last_updated')}"))

        breedobj_mismatches = 0
        for sid, doc in source_docs.items():
            if doc is None:
                continue
            sql_doc = sqlstore.read_result_doc(session, sid)
            d = _diff(doc, sql_doc, f"$.result[{sid}]")
            if d:
                problems.append((f"result_cache/{sid}", d))
                if "breedObj" in d:
                    breedobj_mismatches += 1

        sql_jobs = sqlstore.read_jobs(session)
        d = _diff(source_jobs.get("jobs", {}), sql_jobs.get("jobs", {}), "$.jobs")
        if d:
            problems.append(("jobs", d))

    if problems:
        logger.warning("dog_migrate_parity_problems", count=len(problems))
        for where, detail in problems[:25]:
            print(f"  PARITY DIFF [{where}]: {detail}")
        if breedobj_mismatches:
            print(f"  ({breedobj_mismatches} of the result diffs are breedObj reconstruction mismatches)")
        return 1

    print(
        f"OK: {len(source_index.get('shows', {}))} shows, "
        f"{len(source_docs)} result caches, "
        f"{len(source_jobs.get('jobs', {}))} jobs round-trip identically."
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Migrate dog JSON caches into dog.db")
    parser.add_argument("--validate-only", action="store_true",
                        help="Do not write; only re-validate the existing dog.db against the JSON.")
    args = parser.parse_args()
    sys.exit(migrate(validate_only=args.validate_only))


if __name__ == "__main__":
    main()
