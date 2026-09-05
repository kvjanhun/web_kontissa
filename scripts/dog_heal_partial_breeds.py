#!/usr/bin/env python3
"""One-off heal of dog shows whose breeds were captured mid-ring.

Showlink flags a breed as having results the moment its first class is judged and
fills the rest of the page as the ring proceeds, so a live crawl that read the
page at that moment holds a slice of the entry — two of eight flat-coats. Shows
that settled around such a snapshot keep it, because a settled show is never
re-fetched. This re-fetches exactly those breeds.

Selection is automatic and structural, using the same rule the crawler now
applies (`result_cache._breed_capture_is_settled`): a captured breed is final
once its honour roll crowns ROP or every entered dog has a row. Anything else was
read mid-ring and is re-fetched.

Showlink serves roughly a season, and a show past that answers every breed page
with an empty result table. Each show is probed with up to three of its own
mid-ring breed pages first, so an aged-out show costs three requests and is
reported as unavailable instead of re-reading its whole breed list every run.

Polite and safe:
- same request rate as the live result crawl (3 workers, 0.4s between starts),
  tunable via --workers / --delay; oldest-first;
- only the unsettled breeds are fetched, not the whole show, and settled captures
  are never re-read;
- nothing is deleted: a failed pass leaves the existing rows untouched, and a
  re-fetch replaces one breed's rows in place.

Idempotent: a breed that comes back complete stops matching. A breed the source
itself left short keeps matching, so use --since / --limit to bound a run. Aim it
at settled history — shows inside the crawler's auto window are re-checked by its
own live/overtime/rescue passes.
One-off operational tool; run against the host ./app/data; NOT part of the
crawler loop.

    SECRET_KEY=dev python3 scripts/dog_heal_partial_breeds.py --dry-run
    SECRET_KEY=dev python3 scripts/dog_heal_partial_breeds.py --since 2026-07-01
    SECRET_KEY=dev python3 scripts/dog_heal_partial_breeds.py --show 13777 --show 13775
"""

import argparse
import datetime
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("SECRET_KEY", "dog-heal-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")  # in-memory; healing only touches dog.db

import structlog  # noqa: E402

from app.dog_show import config, db as dog_db  # noqa: E402
from app.dog_show.indexing import _show_date_for_id  # noqa: E402
from app.dog_show.result_cache import (  # noqa: E402
    _breed_cache_key_from_breed, _breed_capture_is_settled,
    _fetch_breed_results_for_show_cache, crawl_result_cache_for_show,
)
from app.dog_show.store import _complete_cache_captures, _indexed_shows  # noqa: E402

logger = structlog.get_logger(__name__)

SCAN_CHUNK = 200
PROBE_BREEDS = 3


def _unsettled_breeds(captures):
    """{show_id: (breeds, missing_rows)} for every show holding at least one
    mid-ring capture. `missing_rows` is how many entered dogs those breeds are
    short of — an estimate for the printout, since absentees still get a row."""
    found = {}
    show_ids = sorted(captures)
    for start in range(0, len(show_ids), SCAN_CHUNK):
        chunk = show_ids[start:start + SCAN_CHUNK]
        for sid_str, entry in (_indexed_shows(chunk) or {}).items():
            sid = int(sid_str)
            completed = captures.get(sid) or {}
            breeds = []
            missing = 0
            for breed in entry.get("breeds") or []:
                if not breed.get("has_results"):
                    continue
                capture = completed.get(_breed_cache_key_from_breed(breed))
                if capture is None or _breed_capture_is_settled(capture, breed):
                    continue
                breeds.append(breed)
                missing += max(0, int(breed.get("count") or 0) - int(capture.get("result_count") or 0))
            if breeds:
                found[sid] = (breeds, missing)
    return found


def _source_still_serves(show_id, breeds):
    """Whether Showlink still has results for this show, probed with up to three of
    its own mid-ring breed pages. True/False, or None when a request failed.

    The show detail path answers from the persisted breed list without touching
    the network, so an aged-out show still looks like hundreds of result-bearing
    breeds; only the breed pages themselves say otherwise. Probing a page we were
    going to re-fetch anyway costs a healthy show one request, and needing all
    three probes empty keeps a single genuinely resultless breed from writing off
    the whole show."""
    for breed in breeds[:PROBE_BREEDS]:
        try:
            item = _fetch_breed_results_for_show_cache(show_id, breed)
        except Exception as exc:
            logger.warning("dog_heal_probe_failed", show_id=show_id, error=str(exc))
            return None
        if item["mapped_results"]:
            return True
    return False


def _ordered_oldest_first(ids):
    return sorted(ids, key=lambda sid: (_show_date_for_id(sid) or datetime.date.max, sid))


def _parse_since(value):
    if not value:
        return None
    return datetime.date.fromisoformat(value)


def main():
    parser = argparse.ArgumentParser(description="Re-fetch dog show breeds whose results were captured mid-ring")
    parser.add_argument("--since", type=str, default=None, help="Only heal shows held on or after this date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=None, help="Heal only the oldest N matching shows")
    parser.add_argument("--show", type=int, action="append", dest="shows", help="Heal only these show ids (repeatable); bypasses the automatic selector")
    parser.add_argument("--delay", type=float, default=config.RESULT_CRAWL_DEFAULT_DELAY, help="Seconds between breed-result request starts (default matches the live result crawl)")
    parser.add_argument("--workers", type=int, default=config.RESULT_CRAWL_DEFAULT_WORKERS, help="Concurrent breed-result requests per show (default matches the live result crawl)")
    parser.add_argument("--dry-run", action="store_true", help="List the selected shows and breed counts without fetching")
    args = parser.parse_args()

    dog_db.init_db()

    unsettled = _unsettled_breeds(_complete_cache_captures())
    since = _parse_since(args.since)

    ordered = _ordered_oldest_first(args.shows if args.shows else unsettled)
    if since:
        ordered = [sid for sid in ordered if (_show_date_for_id(sid) or datetime.date.max) >= since]
    if args.limit is not None:
        ordered = ordered[:max(0, args.limit)]

    def _counts(sid):
        breeds, missing = unsettled.get(sid, ([], 0))
        return len(breeds), missing

    total_breeds = sum(_counts(sid)[0] for sid in ordered)
    total_missing = sum(_counts(sid)[1] for sid in ordered)
    logger.info("dog_heal_selected", shows=len(ordered), breeds=total_breeds, missing_rows=total_missing)
    print(f"Selected {len(ordered)} show(s), {total_breeds} mid-ring breed(s), ~{total_missing} missing row(s) (oldest first):")
    for sid in ordered:
        breeds, missing = _counts(sid)
        show_date = _show_date_for_id(sid)
        print(f"  {sid}  {show_date.isoformat() if show_date else '(no date)'}  breeds={breeds} missing~{missing}")

    if args.dry_run:
        print("Dry run — nothing fetched.")
        return

    if not ordered:
        print("Nothing to heal.")
        return

    healed = unavailable = failed = 0
    for sid in ordered:
        before, _missing = _counts(sid)
        probe_breeds = unsettled.get(sid, ([], 0))[0]
        serves = _source_still_serves(sid, probe_breeds) if probe_breeds else True
        if serves is None:
            print(f"  FAILED {sid}: probe request failed — captured rows left intact")
            failed += 1
            continue
        if not serves:
            print(f"  UNAVAILABLE {sid}: Showlink serves no results for these {before} breed(s) — captured rows left intact")
            logger.info("dog_heal_show_unavailable", show_id=sid, unsettled_breeds=before)
            unavailable += 1
            continue

        summary = crawl_result_cache_for_show(
            sid, delay=args.delay, source="heal", workers=args.workers, heal=True,
        )
        status = summary.get("status")
        progress = summary.get("progress") or {}
        if status != "complete":
            print(f"  FAILED {sid}: {summary.get('error') or summary.get('reason')} — captured rows left intact")
            logger.warning("dog_heal_show_failed", show_id=sid, status=status, error=summary.get("error"))
            failed += 1
            continue
        crawled = summary.get("crawled_breeds") or 0
        print(f"  HEALED {sid}: refetched={crawled} breeds — dogs={progress.get('total_dogs')}")
        logger.info("dog_heal_show_complete", show_id=sid, refetched=crawled, total_dogs=progress.get("total_dogs"))
        healed += 1

    print(f"Done. healed={healed} unavailable={unavailable} failed={failed}")
    logger.info("dog_heal_done", healed=healed, unavailable=unavailable, failed=failed)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("dog_heal_shutdown", reason="keyboard_interrupt")
    except Exception:
        logger.exception("dog_heal_fatal")
        raise
