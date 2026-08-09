"""Delete PageViewEvent rows older than the analytics window.

`/api/pageviews/events` caps its query at 90 days (`days` is clamped to 1–90 in
app/api/pageviews.py), so anything older is written, replicated to Backblaze by
Litestream, and never read again. Nothing pruned them before this script.

Deliberately a standalone script rather than a hook in app startup or a request
handler — same reasoning as scripts/dog_crawl.py: the web tier stays read-mostly and
predictable, and retention runs on a schedule the operator controls.

Usage:
    python3 scripts/prune_pageview_events.py [--days 90] [--dry-run]

On the NUC, run it inside the web container so it picks up the mounted data volume:
    docker exec <web-container> python scripts/prune_pageview_events.py
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URI", f"sqlite:///{os.path.join(ROOT, 'app', 'data', 'site.db')}")

from app import app  # noqa: E402
from app.models import db, PageViewEvent  # noqa: E402

# Matches the maximum window /api/pageviews/events will serve.
DEFAULT_RETENTION_DAYS = 90


def prune(days=DEFAULT_RETENTION_DAYS, dry_run=False):
    """Delete events older than `days`. Returns the number of rows affected."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    with app.app_context():
        query = db.session.query(PageViewEvent).filter(PageViewEvent.timestamp < cutoff)
        count = query.count()

        if dry_run:
            print(f"[dry-run] {count} event(s) older than {cutoff.isoformat()} would be deleted.")
            return count

        query.delete(synchronize_session=False)
        db.session.commit()
        print(f"Deleted {count} event(s) older than {cutoff.isoformat()}.")
        return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days", type=int, default=DEFAULT_RETENTION_DAYS,
        help=f"retention window in days (default {DEFAULT_RETENTION_DAYS})",
    )
    parser.add_argument("--dry-run", action="store_true", help="report without deleting")
    args = parser.parse_args()

    if args.days < 1:
        parser.error("--days must be at least 1")

    prune(days=args.days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
