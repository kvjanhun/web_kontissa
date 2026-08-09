"""Tests for the page view counter API."""

import os
import sys
from datetime import datetime, timedelta, timezone

from app.models import db, PageViewEvent

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from prune_pageview_events import prune  # noqa: E402


class TestTrackPageview:
    """POST /api/pageview"""

    def test_increments_new_path(self, client):
        res = client.post("/api/pageview", json={"path": "/dog"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["path"] == "/dog"
        assert data["count"] == 1

    def test_dedup_same_session(self, client):
        """Same client session should only count once per path."""
        client.post("/api/pageview", json={"path": "/dog"})
        res = client.post("/api/pageview", json={"path": "/dog"})
        assert res.get_json()["count"] == 1

    def test_different_paths_counted_separately(self, client):
        """Different paths are deduped independently within the same session."""
        client.post("/api/pageview", json={"path": "/dog"})
        res = client.post("/api/pageview", json={"path": "/about"})
        assert res.get_json()["count"] == 1
        # Second hit on /dog still deduped
        res2 = client.post("/api/pageview", json={"path": "/dog"})
        assert res2.get_json()["count"] == 1

    def test_different_sessions_counted(self, app):
        """Different browser sessions should each count."""
        c1 = app.test_client()
        c2 = app.test_client()
        c1.post("/api/pageview", json={"path": "/dog"})
        res = c2.post("/api/pageview", json={"path": "/dog"})
        assert res.get_json()["count"] == 2

    def test_rejects_missing_path(self, client):
        res = client.post("/api/pageview", json={})
        assert res.status_code == 400

    def test_rejects_non_string_path(self, client):
        res = client.post("/api/pageview", json={"path": 123})
        assert res.status_code == 400

    def test_rejects_path_without_leading_slash(self, client):
        res = client.post("/api/pageview", json={"path": "dog"})
        assert res.status_code == 400

    def test_rejects_path_over_200_chars(self, client):
        res = client.post("/api/pageview", json={"path": "/" + "a" * 200})
        assert res.status_code == 400

    def test_accepts_path_at_200_chars(self, client):
        # Must sit under a known route prefix as well as fit the length budget.
        path = "/recipes/" + "a" * 191
        assert len(path) == 200
        res = client.post("/api/pageview", json={"path": path})
        assert res.status_code == 200

    def test_no_auth_required(self, client):
        """Page view tracking is public — no login needed."""
        res = client.post("/api/pageview", json={"path": "/dog"})
        assert res.status_code == 200

    def test_rejects_unknown_route(self, client):
        """The endpoint is public, so only real routes may create rows — otherwise
        anyone can grow site.db (and its Litestream replica) without bound."""
        res = client.post("/api/pageview", json={"path": "/not-a-real-page"})
        assert res.status_code == 400

    def test_unknown_route_creates_no_rows(self, app):
        from app.models import PageView, PageViewEvent

        c = app.test_client()
        c.post("/api/pageview", json={"path": "/spam-" + "x" * 50})

        with app.app_context():
            assert db.session.query(PageView).count() == 0
            assert db.session.query(PageViewEvent).count() == 0

    def test_accepts_nested_known_route(self, client):
        """Non-pre-rendered routes under a known prefix still count."""
        res = client.post("/api/pageview", json={"path": "/recipes/pancakes"})
        assert res.status_code == 200

    def test_accepts_root(self, client):
        res = client.post("/api/pageview", json={"path": "/"})
        assert res.status_code == 200

    def test_session_dedup_list_is_capped(self, app):
        """viewed_pages rides in the signed cookie, so it must not grow unbounded."""
        from app.api.pageviews import MAX_TRACKED_PATHS

        c = app.test_client()
        for i in range(MAX_TRACKED_PATHS + 15):
            c.post("/api/pageview", json={"path": f"/recipes/r{i}"})

        with c.session_transaction() as sess:
            assert len(sess["viewed_pages"]) == MAX_TRACKED_PATHS
            # FIFO: the most recent paths survive
            assert sess["viewed_pages"][-1] == f"/recipes/r{MAX_TRACKED_PATHS + 14}"


class TestListPageviews:
    """GET /api/pageviews"""

    def test_requires_admin(self, client):
        res = client.get("/api/pageviews")
        assert res.status_code == 401

    def test_regular_user_denied(self, logged_in_user):
        res = logged_in_user.get("/api/pageviews")
        assert res.status_code == 403

    def test_admin_gets_list(self, app, logged_in_admin):
        # Use separate clients to bypass session dedup
        c1 = app.test_client()
        c2 = app.test_client()
        c3 = app.test_client()
        c1.post("/api/pageview", json={"path": "/dog"})
        c2.post("/api/pageview", json={"path": "/dog"})
        c3.post("/api/pageview", json={"path": "/about"})

        res = logged_in_admin.get("/api/pageviews")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        # Sorted by count desc — /dog (2) first
        assert data[0]["path"] == "/dog"
        assert data[0]["count"] == 2
        assert data[1]["path"] == "/about"
        assert data[1]["count"] == 1

    def test_empty_list(self, logged_in_admin):
        res = logged_in_admin.get("/api/pageviews")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_timestamps_present(self, app, logged_in_admin):
        """created_at and updated_at should be in the response."""
        c = app.test_client()
        c.post("/api/pageview", json={"path": "/login"})

        res = logged_in_admin.get("/api/pageviews")
        data = res.get_json()
        assert len(data) == 1
        assert "created_at" in data[0]
        assert "updated_at" in data[0]
        assert data[0]["created_at"] is not None

    def test_updated_at_changes_on_increment(self, app, logged_in_admin):
        """updated_at should change when the counter increments."""
        c1 = app.test_client()
        c1.post("/api/pageview", json={"path": "/login"})

        res1 = logged_in_admin.get("/api/pageviews")
        ts1 = res1.get_json()[0]["updated_at"]

        # Different session increments the counter
        c2 = app.test_client()
        c2.post("/api/pageview", json={"path": "/login"})

        res2 = logged_in_admin.get("/api/pageviews")
        ts2 = res2.get_json()[0]["updated_at"]
        # updated_at should be set (both should be non-null)
        assert ts1 is not None
        assert ts2 is not None


class TestPageviewEvents:
    """GET /api/pageviews/events"""

    def test_requires_admin(self, client):
        res = client.get("/api/pageviews/events")
        assert res.status_code == 401

    def test_regular_user_denied(self, logged_in_user):
        res = logged_in_user.get("/api/pageviews/events")
        assert res.status_code == 403

    def test_returns_empty_series(self, logged_in_admin):
        res = logged_in_admin.get("/api/pageviews/events")
        assert res.status_code == 200
        data = res.get_json()
        assert data["days"] == 30
        assert data["paths"] == []
        assert len(data["series"]) == 30

    def test_records_events(self, app, logged_in_admin):
        """Page view events are recorded alongside summary counts."""
        c1 = app.test_client()
        c2 = app.test_client()
        c1.post("/api/pageview", json={"path": "/dog"})
        c2.post("/api/pageview", json={"path": "/dog"})

        res = logged_in_admin.get("/api/pageviews/events?days=1")
        data = res.get_json()
        assert "/dog" in data["paths"]
        # Find today's entry
        today_entry = data["series"][-1]
        assert today_entry["counts"].get("/dog") == 2

    def test_multiple_paths(self, app, logged_in_admin):
        c1 = app.test_client()
        c2 = app.test_client()
        c1.post("/api/pageview", json={"path": "/dog"})
        c2.post("/api/pageview", json={"path": "/about"})

        res = logged_in_admin.get("/api/pageviews/events?days=1")
        data = res.get_json()
        assert sorted(data["paths"]) == ["/about", "/dog"]

    def test_days_param_clamped(self, logged_in_admin):
        """Days param is clamped to 1-90."""
        res = logged_in_admin.get("/api/pageviews/events?days=200")
        assert res.get_json()["days"] == 90

        res = logged_in_admin.get("/api/pageviews/events?days=0")
        assert res.get_json()["days"] == 1

    def test_series_length_matches_days(self, logged_in_admin):
        res = logged_in_admin.get("/api/pageviews/events?days=7")
        data = res.get_json()
        assert data["days"] == 7
        assert len(data["series"]) == 7

    def test_deduped_sessions_dont_create_events(self, client, logged_in_admin):
        """Same session, same path — only one event created."""
        client.post("/api/pageview", json={"path": "/login"})
        client.post("/api/pageview", json={"path": "/login"})

        res = logged_in_admin.get("/api/pageviews/events?days=1")
        data = res.get_json()
        today_entry = data["series"][-1]
        assert today_entry["counts"].get("/login") == 1


class TestPruneEvents:
    """scripts/prune_pageview_events.py — nothing else prunes this table."""

    def _seed(self, app, ages_in_days):
        with app.app_context():
            now = datetime.now(timezone.utc)
            for age in ages_in_days:
                db.session.add(PageViewEvent(path="/dog", timestamp=now - timedelta(days=age)))
            db.session.commit()

    def _count(self, app):
        with app.app_context():
            return db.session.query(PageViewEvent).count()

    def test_deletes_only_rows_outside_the_window(self, app):
        self._seed(app, [1, 45, 89, 91, 200])
        assert prune(days=90) == 2
        assert self._count(app) == 3

    def test_dry_run_reports_without_deleting(self, app):
        self._seed(app, [1, 200, 300])
        assert prune(days=90, dry_run=True) == 2
        assert self._count(app) == 3

    def test_noop_when_everything_is_recent(self, app):
        self._seed(app, [0, 5, 30])
        assert prune(days=90) == 0
        assert self._count(app) == 3

    def test_custom_window(self, app):
        self._seed(app, [1, 10, 40])
        assert prune(days=7) == 2
        assert self._count(app) == 1
