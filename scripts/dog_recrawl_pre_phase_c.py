#!/usr/bin/env python3
"""One-off re-crawl of pre-Phase-C captured dog shows.

Shows captured before the Phase C full-data change have result rows but no
per-dog `competitive_placement` (PU/PN) and no breed honor-roll awards. This forces
a fresh re-crawl of exactly those shows so they gain the new fields. Selection is
automatic: complete result caches that have result rows but zero non-empty
competitive_placement and zero `dog_breed_award` rows (the pre-Phase-C signature).

Polite and safe:
- single worker, BACKFILL_DELAY spacing, oldest-first (races Showlink's rolling
  window, securing the most at-risk history first);
- before forcing each show it fetches the live Showlink detail page and only
  re-crawls if the show still serves result-bearing breeds. A show that has aged
  out of Showlink's window is skipped and its captured data is left intact, rather
  than overwritten with an empty result set by the force re-crawl.

Idempotent: once a show has the new fields it no longer matches the selector. One
-off, run against the host ./app/data like the other migrations; NOT part of the
crawler loop.

    SECRET_KEY=dev python3 scripts/dog_recrawl_pre_phase_c.py --dry-run
    SECRET_KEY=dev python3 scripts/dog_recrawl_pre_phase_c.py            # re-crawl all
    SECRET_KEY=dev python3 scripts/dog_recrawl_pre_phase_c.py --limit 5  # oldest 5 only
"""

import argparse
import datetime
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("DOG_NO_CRAWLER", "true")
os.environ.setdefault("SECRET_KEY", "dog-recrawl-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")  # in-memory; re-crawl only touches dog.db

import structlog  # noqa: E402

from app.dog_show import config, db as dog_db, sqlstore  # noqa: E402
from app.dog_show.indexing import _result_breeds_with_results, _show_date_for_id  # noqa: E402
from app.dog_show.parsers import _parse_show_detail  # noqa: E402
from app.dog_show.result_cache import crawl_result_cache_for_show  # noqa: E402
from app.dog_show.showlink import _fetch_page, _source_url  # noqa: E402
from app.dog_show.store import _load_index  # noqa: E402

logger = structlog.get_logger(__name__)


def _candidate_ids():
    with dog_db.session_scope() as session:
        return sqlstore.pre_phase_c_result_cache_show_ids(session)


def _ordered_oldest_first(ids):
    return sorted(ids, key=lambda sid: (_show_date_for_id(sid) or datetime.date.max, sid))


def _still_serves_results(show_id):
    """True if the live Showlink detail page still lists result-bearing breeds.

    Guards against the force re-crawl wiping captured data for a show that has aged
    out of Showlink's rolling window (its page returns an empty shell)."""
    try:
        soup = _fetch_page(_source_url(show_id))
        detail = _parse_show_detail(soup, show_id)
    except Exception as exc:
        logger.warning("dog_recrawl_detail_check_failed", show_id=show_id, error=str(exc))
        return False
    return bool(_result_breeds_with_results(detail.get("breeds", [])))


def main():
    parser = argparse.ArgumentParser(description="Re-crawl pre-Phase-C dog shows for the new full-data fields")
    parser.add_argument("--limit", type=int, default=None, help="Re-crawl only the oldest N matching shows")
    parser.add_argument("--delay", type=float, default=config.BACKFILL_DELAY, help="Seconds between breed-result requests (default: config BACKFILL_DELAY)")
    parser.add_argument("--dry-run", action="store_true", help="List the selected shows without crawling")
    args = parser.parse_args()

    dog_db.init_db()
    _load_index()  # so _show_date_for_id can resolve show dates for ordering

    ordered = _ordered_oldest_first(_candidate_ids())
    if args.limit is not None:
        ordered = ordered[:max(0, args.limit)]

    logger.info("dog_recrawl_selected", count=len(ordered), show_ids=ordered)
    print(f"Selected {len(ordered)} pre-Phase-C show(s) to re-crawl (oldest first):")
    for sid in ordered:
        show_date = _show_date_for_id(sid)
        print(f"  {sid}  {show_date.isoformat() if show_date else '(no date)'}")

    if args.dry_run:
        print("Dry run — no crawling performed.")
        return

    if not ordered:
        print("Nothing to re-crawl.")
        return

    recrawled = skipped = failed = 0
    for sid in ordered:
        if not _still_serves_results(sid):
            print(f"  SKIP {sid}: no longer serves results on Showlink — captured data left intact")
            logger.info("dog_recrawl_skipped_aged_out", show_id=sid)
            skipped += 1
            continue

        summary = crawl_result_cache_for_show(sid, delay=args.delay, force=True, source="recrawl", workers=1)
        status = summary.get("status")
        progress = summary.get("progress") or {}
        print(f"  {str(status).upper()} {sid}: dogs={progress.get('total_dogs')} breeds={progress.get('fetched_breeds')}")
        logger.info("dog_recrawl_show_complete", show_id=sid, status=status, error=summary.get("error"))
        if status == "complete":
            recrawled += 1
        else:
            failed += 1

    print(f"Done. re-crawled={recrawled} skipped={skipped} failed={failed}")
    logger.info("dog_recrawl_done", recrawled=recrawled, skipped=skipped, failed=failed)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("dog_recrawl_shutdown", reason="keyboard_interrupt")
    except Exception:
        logger.exception("dog_recrawl_fatal")
        raise
