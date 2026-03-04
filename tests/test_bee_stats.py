"""Tests for the Sanakenno stats endpoint."""

from app.models import db, BlockedWord, PageView


class TestBeeStats:
    """GET /api/kenno/stats"""

    def test_requires_auth(self, client):
        res = client.get("/api/kenno/stats")
        assert res.status_code == 401

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.get("/api/kenno/stats")
        assert res.status_code == 403

    def test_returns_stats(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert "page_views" in data
        assert "blocked_words_count" in data
        assert "total_puzzles" in data

    def test_counts_reflect_data(self, app, logged_in_admin):
        with app.app_context():
            db.session.add(PageView(path="/sanakenno", count=42))
            db.session.add(BlockedWord(word="bad1"))
            db.session.add(BlockedWord(word="bad2"))
            db.session.commit()

        res = logged_in_admin.get("/api/kenno/stats")
        data = res.get_json()
        assert data["page_views"] == 42
        assert data["blocked_words_count"] == 2
        assert data["total_puzzles"] == 41

    def test_zero_page_views_when_no_sanakenno(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/stats")
        data = res.get_json()
        assert data["page_views"] == 0
