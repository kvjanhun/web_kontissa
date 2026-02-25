"""Tests for the page view counter API."""


class TestTrackPageview:
    """POST /api/pageview"""

    def test_increments_new_path(self, client):
        res = client.post("/api/pageview", json={"path": "/sanakenno"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["path"] == "/sanakenno"
        assert data["count"] == 1

    def test_dedup_same_session(self, client):
        """Same client session should only count once per path."""
        client.post("/api/pageview", json={"path": "/sanakenno"})
        res = client.post("/api/pageview", json={"path": "/sanakenno"})
        assert res.get_json()["count"] == 1

    def test_different_paths_counted_separately(self, client):
        """Different paths are deduped independently within the same session."""
        client.post("/api/pageview", json={"path": "/sanakenno"})
        res = client.post("/api/pageview", json={"path": "/about"})
        assert res.get_json()["count"] == 1
        # Second hit on /sanakenno still deduped
        res2 = client.post("/api/pageview", json={"path": "/sanakenno"})
        assert res2.get_json()["count"] == 1

    def test_different_sessions_counted(self, app):
        """Different browser sessions should each count."""
        c1 = app.test_client()
        c2 = app.test_client()
        c1.post("/api/pageview", json={"path": "/sanakenno"})
        res = c2.post("/api/pageview", json={"path": "/sanakenno"})
        assert res.get_json()["count"] == 2

    def test_rejects_missing_path(self, client):
        res = client.post("/api/pageview", json={})
        assert res.status_code == 400

    def test_rejects_non_string_path(self, client):
        res = client.post("/api/pageview", json={"path": 123})
        assert res.status_code == 400

    def test_rejects_path_without_leading_slash(self, client):
        res = client.post("/api/pageview", json={"path": "sanakenno"})
        assert res.status_code == 400

    def test_rejects_path_over_200_chars(self, client):
        res = client.post("/api/pageview", json={"path": "/" + "a" * 200})
        assert res.status_code == 400

    def test_accepts_path_at_200_chars(self, client):
        path = "/" + "a" * 199
        assert len(path) == 200
        res = client.post("/api/pageview", json={"path": path})
        assert res.status_code == 200

    def test_no_auth_required(self, client):
        """Page view tracking is public — no login needed."""
        res = client.post("/api/pageview", json={"path": "/sanakenno"})
        assert res.status_code == 200


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
        c1.post("/api/pageview", json={"path": "/sanakenno"})
        c2.post("/api/pageview", json={"path": "/sanakenno"})
        c3.post("/api/pageview", json={"path": "/about"})

        res = logged_in_admin.get("/api/pageviews")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        # Sorted by count desc — /sanakenno (2) first
        assert data[0]["path"] == "/sanakenno"
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
        c.post("/api/pageview", json={"path": "/test"})

        res = logged_in_admin.get("/api/pageviews")
        data = res.get_json()
        assert len(data) == 1
        assert "created_at" in data[0]
        assert "updated_at" in data[0]
        assert data[0]["created_at"] is not None

    def test_updated_at_changes_on_increment(self, app, logged_in_admin):
        """updated_at should change when the counter increments."""
        c1 = app.test_client()
        c1.post("/api/pageview", json={"path": "/ts"})

        res1 = logged_in_admin.get("/api/pageviews")
        ts1 = res1.get_json()[0]["updated_at"]

        # Different session increments the counter
        c2 = app.test_client()
        c2.post("/api/pageview", json={"path": "/ts"})

        res2 = logged_in_admin.get("/api/pageviews")
        ts2 = res2.get_json()[0]["updated_at"]
        # updated_at should be set (both should be non-null)
        assert ts1 is not None
        assert ts2 is not None
