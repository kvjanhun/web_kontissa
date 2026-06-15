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
    parser.add_argument("--limit", type=int, default=None, help="Maximum shows to update per run")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between Showlink show requests")
    parser.add_argument("--no-results", action="store_true", help="Skip whole-show result cache warming")
    parser.add_argument("--no-auto-results", action="store_true", help="Only process queued result cache jobs")
    parser.add_argument("--result-limit", type=int, default=1, help="Maximum whole-show result caches to update per run")
    parser.add_argument("--result-delay", type=float, default=2.0, help="Seconds between result page requests")
    args = parser.parse_args()

    print({
        "event": "dog_crawler_boot",
        "index_path": INDEX_PATH,
        "result_cache_dir": RESULT_CACHE_DIR,
    }, flush=True)

    while True:
        index_summary = crawl_index_once(limit=args.limit, delay=args.delay)
        summary = {"index": index_summary}

        if not args.no_results:
            summary["results"] = crawl_result_cache_once(
                limit=args.result_limit,
                delay=args.result_delay,
                auto_recent=not args.no_auto_results,
            )

        print(summary, flush=True)

        if not args.loop:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
