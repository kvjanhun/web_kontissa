#!/usr/bin/env python3
"""One-off migration: dog JSON caches -> dog.db (Phase B).

Loads the current `dog_show_index.json`, every `dog_result_cache/<id>.json`, and
`dog_result_jobs.json` into the new SQLite dog database, then validates that each
record round-trips back to the exact structure the rest of the package and
`/api/dog/*` consume. Idempotent: it replaces all dog rows each run.

    SECRET_KEY=dev python3 scripts/migrate_dog_to_sql.py            # default paths
    SECRET_KEY=dev python3 scripts/migrate_dog_to_sql.py --validate-only

Source dir is DOG_INDEX_DIR (default ./app/data); target is DOG_DATABASE_URI
(default dog.db inside that dir). This script reads the legacy JSON directly so
it stays runnable after store.py has been cut over to SQL.
"""

import argparse
import glob
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("DOG_NO_CRAWLER", "true")
os.environ.setdefault("SECRET_KEY", "dog-migrate-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")  # in-memory; migration only touches dog.db

import structlog  # noqa: E402

from app.dog_show import config, db as dog_db, sqlstore  # noqa: E402
from app.dog_show.indexing import _breed_identity_from_result, _merge_breed_map_judges_into_breeds  # noqa: E402
from app.dog_show.utils import _clean_breed_data  # noqa: E402

logger = structlog.get_logger(__name__)


# ---- JSON source loaders (read the legacy files directly) ------------------

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception:
        logger.exception("dog_migrate_source_load_failed", path=path)
        return default


def _load_source_index():
    data = _load_json(config.INDEX_PATH, {"shows": {}, "last_updated": 0})
    if not isinstance(data, dict) or "shows" not in data:
        return {"shows": {}, "last_updated": 0}
    return {"shows": data.get("shows", {}), "last_updated": data.get("last_updated", 0)}


def _load_source_docs():
    docs = {}
    for path in glob.glob(os.path.join(config.RESULT_CACHE_DIR, "*.json")):
        stem = os.path.basename(path)[:-5]
        if not stem.isdigit():
            continue
        doc = _load_json(path, None)
        if isinstance(doc, dict):
            docs[int(stem)] = doc
    return dict(sorted(docs.items()))


def _load_source_jobs():
    data = _load_json(config.RESULT_JOBS_PATH, {"jobs": {}, "updated_at": 0})
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), dict):
        return {"jobs": {}, "updated_at": 0}
    return data


def _breed_map_from_doc(doc):
    """Per-breed judge map from one result doc — mirrors indexing._cached_result_breed_map,
    but takes the doc directly so it does not read through the (now SQL) store."""
    breeds = {}
    for key, breed_data in (doc.get("completed_breeds") or {}).items():
        if not isinstance(breed_data, dict) or ":" not in key:
            continue
        group, breed_id = key.split(":", 1)
        breed = _clean_breed_data({
            "name": breed_data.get("name", ""),
            "group": group,
            "breed_id": breed_id,
            "has_results": True,
            "judge": breed_data.get("judge", ""),
        })
        if breed.get("judge"):
            breeds[(group, breed_id)] = breed

    for result in doc.get("results") or []:
        key = _breed_identity_from_result(result)
        if not key:
            continue
        breed = _clean_breed_data(result.get("breedObj") or {})
        if breed.get("judge"):
            breed.setdefault("group", key[0])
            breed.setdefault("breed_id", key[1])
            breed.setdefault("has_results", True)
            breeds[key] = breed
    return breeds


# ---- parity comparator -----------------------------------------------------

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

    source_index = _load_source_index()
    source_docs = _load_source_docs()
    source_jobs = _load_source_jobs()

    # Consolidate: fold judges that only live in a result cache back into the
    # breed list, exactly as the running app does lazily on detail/search. This
    # makes the breed table the single source of truth for per-breed judges, so
    # reconstructed result breedObjs match and judge search covers these shows.
    backfilled = 0
    for sid, doc in source_docs.items():
        show = source_index.get("shows", {}).get(str(sid))
        if not show:
            continue
        if _merge_breed_map_judges_into_breeds(show.get("breeds", []), _breed_map_from_doc(doc)):
            backfilled += 1
    if backfilled:
        logger.info("dog_migrate_judge_backfill", shows=backfilled)

    if not validate_only:
        with dog_db.session_scope() as session:
            sqlstore.write_index(session, source_index)
            for sid, doc in source_docs.items():
                sqlstore.write_result_doc(session, sid, doc)
            sqlstore.write_jobs(session, source_jobs)
            sqlstore.bump_index_generation(session)
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
