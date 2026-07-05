#!/usr/bin/env python3
"""One-off rescue re-crawl of dog shows that settled missing their finals.

Some shows were captured completely at the breed level but lost their show-wide
finals — the group winners (RYP) and/or the main Best in Show (BIS) — because the
crawler stopped fetching before Showlink published them (the failure the
terminal-detection redesign fixes going forward). This forces a fresh re-crawl of
exactly those shows so the finals land on the winners' rows.

Selection is automatic and structural (via `finals.analyze`): complete result
caches that *expect* show-wide finals (multi-group, or finals tokens already
present) but whose terminal target is not met — a result-bearing FCI group with
no RYP-1, or no main BIS-1 on an all-breed show. A show whose source genuinely
never published those tokens simply comes back unchanged.

Polite and safe:
- same request rate as the live result crawl (3 workers, 0.4s between starts),
  tunable via --workers / --delay; oldest-first;
- before forcing each show it fetches the live Showlink detail page and only
  re-crawls if the show still serves result-bearing breeds, so a show that has
  aged out of Showlink's window is skipped and its captured data left intact.

Idempotent-ish: once a show gains its finals it no longer matches the selector.
A show whose finals were never published at the source will keep matching, so use
--limit / the printed list to avoid re-forcing known source-incomplete shows.
One-off operational tool; run against the host ./app/data; NOT part of the
crawler loop.

    SECRET_KEY=dev python3 scripts/dog_rescue_finals.py --dry-run
    SECRET_KEY=dev python3 scripts/dog_rescue_finals.py --limit 5
    SECRET_KEY=dev python3 scripts/dog_rescue_finals.py --show 13786 --show 13758
"""

import argparse
import datetime
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("SECRET_KEY", "dog-rescue-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")  # in-memory; rescue only touches dog.db

import structlog  # noqa: E402

from app.dog_show import config, db as dog_db, finals  # noqa: E402
from app.dog_show.indexing import _result_breeds_with_results, _show_date_for_id  # noqa: E402
from app.dog_show.parsers import _parse_show_detail  # noqa: E402
from app.dog_show.result_cache import crawl_result_cache_for_show  # noqa: E402
from app.dog_show.showlink import _fetch_page, _source_url  # noqa: E402
from app.dog_show.store import (  # noqa: E402
    _complete_result_cache_show_ids, _indexed_show, _load_index, _load_result_cache_doc,
)

logger = structlog.get_logger(__name__)


def _owes_finals(show_id):
    """True if a complete cache is a **multi-group** show (crowns a main BIS) that
    hasn't captured its terminal (a result-bearing group missing RYP-1, or no
    main BIS-1). Single-group shows crown no main BIS, so they never "owe" one and
    are not rescue candidates — matching the production live plan."""
    doc = _load_result_cache_doc(show_id)
    if not doc:
        return False
    breeds = (_indexed_show(show_id) or {}).get("breeds") or []
    analysis = finals.analyze(doc, breeds)
    return bool(analysis["expects_main_bis"] and not analysis["target_met"])


def _candidate_ids():
    ids = _complete_result_cache_show_ids()
    return [sid for sid in ids if _owes_finals(sid)]


def _ordered_oldest_first(ids):
    return sorted(ids, key=lambda sid: (_show_date_for_id(sid) or datetime.date.max, sid))


def _finals_summary(show_id):
    """Short human note on what the show is still missing, for the printout."""
    doc = _load_result_cache_doc(show_id) or {}
    breeds = (_indexed_show(show_id) or {}).get("breeds") or []
    analysis = finals.analyze(doc, breeds)
    bits = []
    if not analysis["has_bis1"]:
        bits.append("no BIS-1")
    if analysis["missing_ryp_groups"]:
        bits.append("RYP missing in groups " + ",".join(sorted(analysis["missing_ryp_groups"])))
    return "; ".join(bits) or "finals incomplete"


def _still_serves_results(show_id):
    """True if the live Showlink detail page still lists result-bearing breeds.

    Guards against the force re-crawl wiping captured data for a show that has aged
    out of Showlink's rolling window (its page returns an empty shell)."""
    try:
        soup = _fetch_page(_source_url(show_id))
        detail = _parse_show_detail(soup, show_id)
    except Exception as exc:
        logger.warning("dog_rescue_detail_check_failed", show_id=show_id, error=str(exc))
        return False
    return bool(_result_breeds_with_results(detail.get("breeds", [])))


def main():
    parser = argparse.ArgumentParser(description="Rescue re-crawl of dog shows that settled missing their finals")
    parser.add_argument("--limit", type=int, default=None, help="Re-crawl only the oldest N matching shows")
    parser.add_argument("--show", type=int, action="append", dest="shows", help="Re-crawl only these show ids (repeatable); bypasses the automatic selector")
    parser.add_argument("--delay", type=float, default=config.RESULT_CRAWL_DEFAULT_DELAY, help="Seconds between breed-result request starts (default matches the live result crawl)")
    parser.add_argument("--workers", type=int, default=config.RESULT_CRAWL_DEFAULT_WORKERS, help="Concurrent breed-result requests per show (default matches the live result crawl)")
    parser.add_argument("--dry-run", action="store_true", help="List the selected shows without crawling")
    args = parser.parse_args()

    dog_db.init_db()
    _load_index()  # so _indexed_show / _show_date_for_id resolve

    if args.shows:
        ordered = _ordered_oldest_first(args.shows)
    else:
        ordered = _ordered_oldest_first(_candidate_ids())
    if args.limit is not None:
        ordered = ordered[:max(0, args.limit)]

    logger.info("dog_rescue_selected", count=len(ordered), show_ids=ordered)
    print(f"Selected {len(ordered)} show(s) owing finals (oldest first):")
    for sid in ordered:
        show_date = _show_date_for_id(sid)
        print(f"  {sid}  {show_date.isoformat() if show_date else '(no date)'}  — {_finals_summary(sid)}")

    if args.dry_run:
        print("Dry run — no crawling performed.")
        return

    if not ordered:
        print("Nothing to rescue.")
        return

    rescued = skipped = failed = 0
    for sid in ordered:
        if not _still_serves_results(sid):
            print(f"  SKIP {sid}: no longer serves results on Showlink — captured data left intact")
            logger.info("dog_rescue_skipped_aged_out", show_id=sid)
            skipped += 1
            continue

        summary = crawl_result_cache_for_show(sid, delay=args.delay, force=True, source="rescue", workers=args.workers)
        status = summary.get("status")
        progress = summary.get("progress") or {}
        after = _finals_summary(sid)
        print(f"  {str(status).upper()} {sid}: dogs={progress.get('total_dogs')} breeds={progress.get('fetched_breeds')} — {after}")
        logger.info("dog_rescue_show_complete", show_id=sid, status=status, remaining=after, error=summary.get("error"))
        if status == "complete":
            rescued += 1
        else:
            failed += 1

    print(f"Done. rescued={rescued} skipped={skipped} failed={failed}")
    logger.info("dog_rescue_done", rescued=rescued, skipped=skipped, failed=failed)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("dog_rescue_shutdown", reason="keyboard_interrupt")
    except Exception:
        logger.exception("dog_rescue_fatal")
        raise
