"""Tests for app/utils.py — GitHub API with cache and stale fallback."""

import time
from unittest.mock import MagicMock, patch

import pytest

import app.utils as utils_module
from app.utils import CACHE_TTL, get_latest_commit_date


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear module-level caches before and after every test."""
    utils_module._cached_commit_time = None
    utils_module._cached_commit_timestamp = 0
    yield
    utils_module._cached_commit_time = None
    utils_module._cached_commit_timestamp = 0


# ---------------------------------------------------------------------------
# get_latest_commit_date
# ---------------------------------------------------------------------------

class TestGetLatestCommitDate:
    def _mock_commit_response(self, date="2026-03-01T10:00:00Z"):
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        mock.json.return_value = {"commit": {"author": {"date": date}}}
        return mock

    def test_returns_commit_date_string(self):
        with patch("app.utils.requests.get", return_value=self._mock_commit_response("2026-03-01T10:00:00Z")):
            result = get_latest_commit_date()
        assert result == "2026-03-01T10:00:00Z"

    def test_cache_hit_avoids_network_call(self):
        with patch("app.utils.requests.get", return_value=self._mock_commit_response()):
            first = get_latest_commit_date()

        with patch("app.utils.requests.get", side_effect=Exception("must not call network")) as mock_get:
            second = get_latest_commit_date()
            mock_get.assert_not_called()

        assert first == second

    def test_cache_expires_after_ttl(self):
        with patch("app.utils.requests.get", return_value=self._mock_commit_response("2026-01-01T00:00:00Z")):
            get_latest_commit_date()

        utils_module._cached_commit_timestamp = time.time() - CACHE_TTL - 1

        with patch("app.utils.requests.get", return_value=self._mock_commit_response("2026-03-20T00:00:00Z")):
            result = get_latest_commit_date()

        assert result == "2026-03-20T00:00:00Z"

    def test_stale_fallback_on_network_error(self):
        with patch("app.utils.requests.get", return_value=self._mock_commit_response("2026-01-15T00:00:00Z")):
            get_latest_commit_date()

        utils_module._cached_commit_timestamp = 0  # expire cache

        with patch("app.utils.requests.get", side_effect=Exception("network error")):
            result = get_latest_commit_date()

        assert result == "2026-01-15T00:00:00Z"

    def test_returns_none_when_no_cache_and_network_fails(self):
        with patch("app.utils.requests.get", side_effect=Exception("network error")):
            result = get_latest_commit_date()
        assert result is None

    def test_fresh_fetch_populates_cache(self):
        with patch("app.utils.requests.get", return_value=self._mock_commit_response("2026-03-01T00:00:00Z")):
            get_latest_commit_date()
        assert utils_module._cached_commit_time == "2026-03-01T00:00:00Z"
        assert utils_module._cached_commit_timestamp > 0

    def test_failed_fetch_does_not_advance_cache_timestamp(self):
        with patch("app.utils.requests.get", return_value=self._mock_commit_response()):
            get_latest_commit_date()
        stale_ts = utils_module._cached_commit_timestamp - 1
        utils_module._cached_commit_timestamp = stale_ts

        with patch("app.utils.requests.get", side_effect=Exception("error")):
            get_latest_commit_date()

        assert utils_module._cached_commit_timestamp == stale_ts
