"""Tests for app/utils.py — GitHub API with cache and stale fallback."""

import time
from unittest.mock import MagicMock, patch

import pytest

import app.utils as utils_module
from app.utils import CACHE_TTL, get_latest_commit_date, get_project_stats


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear module-level caches before and after every test."""
    utils_module._stats_cache["data"] = None
    utils_module._stats_cache["timestamp"] = 0
    utils_module._cached_commit_time = None
    utils_module._cached_commit_timestamp = 0
    yield
    utils_module._stats_cache["data"] = None
    utils_module._stats_cache["timestamp"] = 0
    utils_module._cached_commit_time = None
    utils_module._cached_commit_timestamp = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo_response(size_kb=1024, created_at="2020-03-15T12:00:00Z"):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"size": size_kb, "created_at": created_at}
    return mock


def _make_commits_response(page_count=42):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    last_url = f"https://api.github.com/repos/kvjanhun/web_kontissa/commits?page={page_count}"
    mock.headers = {"Link": f'<{last_url}>; rel="last"'}
    return mock


def _make_langs_response(langs=None):
    if langs is None:
        langs = ["Python", "JavaScript", "CSS"]
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {lang: 1000 for lang in langs}
    return mock


def _make_stats_responses(commit_count=42, langs=None, size_kb=1024, created_at="2020-03-15T12:00:00Z"):
    return [
        _make_repo_response(size_kb=size_kb, created_at=created_at),
        _make_commits_response(page_count=commit_count),
        _make_langs_response(langs=langs),
    ]


# ---------------------------------------------------------------------------
# get_project_stats
# ---------------------------------------------------------------------------

class TestGetProjectStats:
    def test_returns_expected_shape(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses()):
            result = get_project_stats()
        assert set(result.keys()) == {"commits", "languages", "created_at", "size_kb"}

    def test_commit_count_parsed_from_link_header(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=137)):
            result = get_project_stats()
        assert result["commits"] == 137

    def test_languages_limited_to_five(self):
        langs = ["Python", "JavaScript", "CSS", "HTML", "Shell", "Dockerfile"]
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(langs=langs)):
            result = get_project_stats()
        assert result["languages"] == ["Python", "JavaScript", "CSS", "HTML", "Shell"]

    def test_created_at_truncated_to_date(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(created_at="2020-03-15T12:00:00Z")):
            result = get_project_stats()
        assert result["created_at"] == "2020-03-15"

    def test_size_kb_present(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(size_kb=2048)):
            result = get_project_stats()
        assert result["size_kb"] == 2048

    def test_single_commit_no_link_header(self):
        """When the repo has only one page of commits, Link header is absent — defaults to 1."""
        repo = _make_repo_response()
        commits = MagicMock()
        commits.raise_for_status = MagicMock()
        commits.headers = {}  # no Link header
        langs = _make_langs_response()
        with patch("app.utils.requests.get", side_effect=[repo, commits, langs]):
            result = get_project_stats()
        assert result["commits"] == 1

    def test_cache_hit_avoids_network_call(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=10)):
            first = get_project_stats()

        with patch("app.utils.requests.get", side_effect=Exception("must not call network")) as mock_get:
            second = get_project_stats()
            mock_get.assert_not_called()

        assert first == second

    def test_cache_expires_after_ttl(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=10)):
            get_project_stats()

        # Expire the cache
        utils_module._stats_cache["timestamp"] = time.time() - CACHE_TTL - 1

        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=99)):
            result = get_project_stats()

        assert result["commits"] == 99

    def test_stale_fallback_on_network_error(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=77)):
            get_project_stats()

        utils_module._stats_cache["timestamp"] = 0  # expire cache

        with patch("app.utils.requests.get", side_effect=Exception("network error")):
            result = get_project_stats()

        assert result is not None
        assert result["commits"] == 77

    def test_returns_none_when_no_cache_and_network_fails(self):
        with patch("app.utils.requests.get", side_effect=Exception("network error")):
            result = get_project_stats()
        assert result is None

    def test_fresh_fetch_populates_cache(self):
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=50)):
            get_project_stats()
        assert utils_module._stats_cache["data"] is not None
        assert utils_module._stats_cache["timestamp"] > 0

    def test_failed_fetch_does_not_overwrite_cache_timestamp(self):
        """A network error should not advance the cache timestamp (stale data stays stale)."""
        with patch("app.utils.requests.get", side_effect=_make_stats_responses(commit_count=5)):
            get_project_stats()
        stale_ts = utils_module._stats_cache["timestamp"] - 1
        utils_module._stats_cache["timestamp"] = stale_ts

        with patch("app.utils.requests.get", side_effect=Exception("error")):
            get_project_stats()

        assert utils_module._stats_cache["timestamp"] == stale_ts


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
