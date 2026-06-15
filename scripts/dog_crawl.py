#!/usr/bin/env python3
"""Refresh the persisted Showlink breed index.

Run once by default. Use --loop for the production crawler service.
"""

import argparse
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("DOG_NO_CRAWLER", "true")
os.environ.setdefault("SECRET_KEY", "dog-crawler-local-only")

from app.api.dog import INDEX_PATH, RESULT_CACHE_DIR, crawl_index_once, crawl_result_cache_once  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Refresh dog show breed index")
    parser.add_argument("--loop", action="store_true", help="Run forever")
    parser.add_argument("--interval", type=int, default=3600, help="Seconds between loop runs")
    parser.add_argument("--maintenance-interval", type=int, default=None, help="Seconds between index and auto-result maintenance runs")
    parser.add_argument("--auto-results-interval", type=int, default=None, help="Seconds between automatic recent-show result cache runs")
    parser.add_argument("--limit", type=int, default=None, help="Maximum shows to update per run")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between Showlink show requests")
    parser.add_argument("--no-results", action="store_true", help="Skip whole-show result cache warming")
    parser.add_argument("--no-auto-results", action="store_true", help="Only process queued result cache jobs")
    parser.add_argument("--result-limit", type=int, default=1, help="Maximum whole-show result caches to update per run")
    parser.add_argument("--queued-result-limit", type=int, default=None, help="Maximum queued result cache jobs to update per run")
    parser.add_argument("--auto-result-limit", type=int, default=None, help="Maximum automatic result caches to update per run")
    parser.add_argument("--result-delay", type=float, default=0.4, help="Seconds between result page request starts")
    parser.add_argument("--result-workers", type=int, default=3, help="Maximum concurrent result page requests for one show")
    args = parser.parse_args()

    print({
        "event": "dog_crawler_boot",
        "index_path": INDEX_PATH,
        "result_cache_dir": RESULT_CACHE_DIR,
    }, flush=True)

    maintenance_interval = args.maintenance_interval if args.maintenance_interval is not None else args.interval
    auto_results_interval = args.auto_results_interval if args.auto_results_interval is not None else maintenance_interval
    queued_result_limit = args.queued_result_limit if args.queued_result_limit is not None else args.result_limit
    auto_result_limit = args.auto_result_limit if args.auto_result_limit is not None else args.result_limit
    next_maintenance_at = 0
    next_auto_results_at = 0

    while True:
        now = time.time()
        run_maintenance = now >= next_maintenance_at
        run_auto_results = now >= next_auto_results_at
        summary = {}
        queued_attempted = 0

        if not args.no_results:
            summary["queued_results"] = crawl_result_cache_once(
                limit=queued_result_limit,
                delay=args.result_delay,
                auto_recent=False,
                workers=args.result_workers,
            )
            queued_attempted = summary["queued_results"].get("attempted", 0)

        if run_maintenance:
            index_summary = crawl_index_once(limit=args.limit, delay=args.delay)
            summary["index"] = index_summary
            next_maintenance_at = time.time() + maintenance_interval

        else:
            summary["next_maintenance_in"] = max(0, round(next_maintenance_at - now))

        if run_auto_results and not args.no_results and not args.no_auto_results:
            if queued_attempted:
                summary["auto_results"] = {"attempted": 0, "skipped": 1, "reason": "queued_job_active"}
            else:
                summary["auto_results"] = crawl_result_cache_once(
                    limit=auto_result_limit,
                    delay=args.result_delay,
                    auto_recent=True,
                    workers=args.result_workers,
                )
            next_auto_results_at = time.time() + auto_results_interval
        else:
            summary["next_auto_results_in"] = max(0, round(next_auto_results_at - now))

        print(summary, flush=True)

        if not args.loop:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
