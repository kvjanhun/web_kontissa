"""Tests for blocked words list and unblock endpoints."""

from app.models import db, BlockedWord
from app.api.kenno import _PUZZLE_CACHE


class TestBlockedWordsList:
    """GET /api/kenno/blocked"""

    def test_requires_auth(self, client):
        res = client.get("/api/kenno/blocked")
        assert res.status_code == 401

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.get("/api/kenno/blocked")
        assert res.status_code == 403

    def test_returns_empty_list(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/blocked")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_returns_blocked_words_with_timestamps(self, app, logged_in_admin):
        with app.app_context():
            db.session.add(BlockedWord(word="testword"))
            db.session.commit()

        res = logged_in_admin.get("/api/kenno/blocked")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["word"] == "testword"
        assert data[0]["id"] is not None
        assert data[0]["blocked_at"] is not None

    def test_ordered_by_date_desc(self, app, logged_in_admin):
        with app.app_context():
            db.session.add(BlockedWord(word="first"))
            db.session.commit()
            db.session.add(BlockedWord(word="second"))
            db.session.commit()

        res = logged_in_admin.get("/api/kenno/blocked")
        data = res.get_json()
        assert len(data) == 2
        # Most recently blocked should be first
        assert data[0]["word"] == "second"
        assert data[1]["word"] == "first"


class TestUnblockWord:
    """DELETE /api/kenno/block/<id>"""

    def test_requires_auth(self, client):
        res = client.delete("/api/kenno/block/1")
        assert res.status_code == 401

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.delete("/api/kenno/block/1")
        assert res.status_code == 403

    def test_unblocks_word(self, app, logged_in_admin):
        with app.app_context():
            bw = BlockedWord(word="badword")
            db.session.add(bw)
            db.session.commit()
            word_id = bw.id

        res = logged_in_admin.delete(f"/api/kenno/block/{word_id}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["word"] == "badword"
        assert data["unblocked"] is True

        # Verify it's gone
        with app.app_context():
            assert BlockedWord.query.filter_by(word="badword").first() is None

    def test_clears_puzzle_cache(self, app, logged_in_admin):
        with app.app_context():
            bw = BlockedWord(word="cached")
            db.session.add(bw)
            db.session.commit()
            word_id = bw.id

        _PUZZLE_CACHE["dummy"] = "data"
        logged_in_admin.delete(f"/api/kenno/block/{word_id}")
        assert "dummy" not in _PUZZLE_CACHE

    def test_404_for_missing(self, logged_in_admin):
        res = logged_in_admin.delete("/api/kenno/block/9999")
        assert res.status_code == 404
