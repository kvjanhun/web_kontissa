#!/usr/bin/env python3
"""One-off sweep: fold captured judges and result flags into the breed index.

Until the 2026-07 SQL-first rewrite, per-breed judges and has_results flags were
healed *lazily* — a GET on a show detail, breed result, or search would copy them
from the whole-show result cache into the breed index on the fly. Those read-path
write-backs are gone (GETs are read-only now; the crawler folds judges in at
capture time), so any gap the lazy healing never got around to would stay a gap.
This closes them all once:

- `dog_breed.judge` filled from `dog_result.breed_judge` (the result rows carry
  the judge parsed from the breed's result page), and from `completed_breeds`
  cache meta for judged breeds that produced zero result rows;
- `dog_breed.has_results` flagged wherever captured result rows exist.

Existing judges are never overwritten. Idempotent; run once against the host
./app/data after deploying the rewrite:

    SECRET_KEY=dev python3 scripts/dog_sweep_breed_judges.py --dry-run
    SECRET_KEY=dev python3 scripts/dog_sweep_breed_judges.py
"""

import argparse
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("SECRET_KEY", "dog-sweep-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")  # in-memory; sweep only touches dog.db

import structlog  # noqa: E402

from app.dog_show import db as dog_db, sqlstore  # noqa: E402

logger = structlog.get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Fold captured judges/result flags into the dog breed index")
    parser.add_argument("--dry-run", action="store_true", help="Count the updates without committing them")
    args = parser.parse_args()

    dog_db.init_db()

    def _sweep(session):
        counts = {
            "judges_from_results": sqlstore.sweep_breed_judges_from_results(session),
            "judges_from_cache_meta": sqlstore.sweep_breed_judges_from_cache_meta(session),
            "result_flags": sqlstore.sweep_breed_result_flags(session),
        }
        if args.dry_run:
            session.rollback()
        return counts

    counts = dog_db.run_write(_sweep, op="breed_judge_sweep")

    prefix = "Would update" if args.dry_run else "Updated"
    print(f"{prefix} {counts['judges_from_results']} breed judges from result rows,")
    print(f"{prefix.lower()} {counts['judges_from_cache_meta']} from zero-result cache meta,")
    print(f"and {counts['result_flags']} has_results flags.")
    logger.info("dog_breed_sweep_done", dry_run=args.dry_run, **counts)


if __name__ == "__main__":
    main()
