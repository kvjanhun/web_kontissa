"""Tests for the Sanakenno (Spelling Bee) API endpoint."""

import hashlib
import pytest
from app.api.kenno import _score_word


# ---------------------------------------------------------------------------
# Scoring logic — tested against the real _score_word function
# ---------------------------------------------------------------------------

class TestScoringFunction:
    """Test the _score_word function from kenno.py directly."""

    def test_four_letter_word_scores_one(self):
        all_letters = frozenset("aklsunt")
        assert _score_word("kala", all_letters) == 1

    def test_five_letter_word_scores_length(self):
        all_letters = frozenset("aklsunt")
        assert _score_word("lasku", all_letters) == 5

    def test_six_letter_word_scores_length(self):
        all_letters = frozenset("aklsunt")
        # "sultan" uses s,u,l,t,a,n — 6 letters, not all 7 (missing k)
        assert _score_word("sultan", all_letters) == 6

    def test_long_non_pangram_scores_length(self):
        # "auttava" has 7 chars but uses only a, u, t, v — misses k, l, s, n
        all_letters = frozenset("aklsunt")
        assert _score_word("auttava", all_letters) == 7

    def test_pangram_scores_length_plus_seven(self):
        # "alkusanat" uses a,l,k,u,s,n,t — all 7 letters in the set
        all_letters = frozenset("aklsunt")
        word = "alkusanat"
        assert _score_word(word, all_letters) == len(word) + 7

    def test_four_letter_pangram_scores_one_plus_seven(self):
        # Construct a minimal pangram: if all_letters has exactly 4 chars,
        # a 4-letter word using all of them is both short and a pangram.
        all_letters = frozenset("abcd")
        assert _score_word("abcd", all_letters) == 1 + 7

    def test_non_pangram_no_bonus(self):
        all_letters = frozenset("aklsunt")
        # "kala" uses k, a, l — not all 7
        assert _score_word("kala", all_letters) == 1

    def test_word_repeated_letter_does_not_give_pangram_bonus(self):
        # "aaaa" uses only 'a'; can only be a pangram if all_letters == {'a'}
        all_letters = frozenset("aklsunt")
        assert _score_word("aaaa", all_letters) == 1  # not a pangram, 4 letters → 1


# ---------------------------------------------------------------------------
# API endpoint — shape and invariants
# ---------------------------------------------------------------------------

class TestKennoEndpoint:
    def test_returns_200_with_json(self, client):
        resp = client.get("/api/kenno")
        assert resp.status_code == 200
        assert resp.content_type.startswith("application/json")

    def test_response_has_required_fields(self, client):
        data = client.get("/api/kenno").get_json()
        assert "center" in data
        assert "letters" in data
        assert "word_hashes" in data
        assert "hint_data" in data
        assert "max_score" in data
        assert "puzzle_number" in data

    def test_no_words_for_non_admin(self, client):
        data = client.get("/api/kenno").get_json()
        assert "words" not in data

    def test_admin_gets_words(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno").get_json()
        assert "words" in data
        assert isinstance(data["words"], list)
        assert len(data["words"]) > 0

    def test_center_is_single_lowercase_letter(self, client):
        data = client.get("/api/kenno").get_json()
        assert isinstance(data["center"], str)
        assert len(data["center"]) == 1
        assert data["center"] == data["center"].lower()

    def test_letters_has_six_entries(self, client):
        data = client.get("/api/kenno").get_json()
        assert isinstance(data["letters"], list)
        assert len(data["letters"]) == 6

    def test_letters_are_all_distinct(self, client):
        data = client.get("/api/kenno").get_json()
        assert len(set(data["letters"])) == 6, "Outer letters must all be distinct"

    def test_center_not_in_outer_letters(self, client):
        data = client.get("/api/kenno").get_json()
        assert data["center"] not in data["letters"], (
            f"Center '{data['center']}' must not appear in outer letters"
        )

    def test_word_hashes_is_nonempty_list(self, client):
        data = client.get("/api/kenno").get_json()
        assert isinstance(data["word_hashes"], list)
        assert len(data["word_hashes"]) > 0

    def test_word_hashes_are_sha256_hex(self, client):
        data = client.get("/api/kenno").get_json()
        for h in data["word_hashes"]:
            assert isinstance(h, str)
            assert len(h) == 64  # SHA-256 hex digest length

    def test_word_hashes_match_words_for_admin(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno").get_json()
        for word, h in zip(data["words"], data["word_hashes"]):
            assert hashlib.sha256(word.encode()).hexdigest() == h

    def test_word_hashes_have_no_duplicates(self, client):
        data = client.get("/api/kenno").get_json()
        assert len(data["word_hashes"]) == len(set(data["word_hashes"])), "Word hashes must not contain duplicates"

    def test_hint_data_has_required_fields(self, client):
        data = client.get("/api/kenno").get_json()
        hd = data["hint_data"]
        assert "word_count" in hd
        assert "pangram_count" in hd
        assert "by_letter" in hd
        assert "by_length" in hd
        assert "by_pair" in hd

    def test_hint_data_word_count_matches_hashes(self, client):
        data = client.get("/api/kenno").get_json()
        assert data["hint_data"]["word_count"] == len(data["word_hashes"])

    def test_hint_data_by_letter_sums_to_word_count(self, client):
        data = client.get("/api/kenno").get_json()
        hd = data["hint_data"]
        assert sum(hd["by_letter"].values()) == hd["word_count"]

    def test_hint_data_by_length_sums_to_word_count(self, client):
        data = client.get("/api/kenno").get_json()
        hd = data["hint_data"]
        assert sum(hd["by_length"].values()) == hd["word_count"]

    def test_hint_data_by_pair_sums_to_word_count(self, client):
        data = client.get("/api/kenno").get_json()
        hd = data["hint_data"]
        assert sum(hd["by_pair"].values()) == hd["word_count"]

    def test_max_score_is_positive_int(self, client):
        data = client.get("/api/kenno").get_json()
        assert isinstance(data["max_score"], int)
        assert data["max_score"] > 0

    def test_puzzle_number_is_non_negative_int_within_range(self, client):
        data = client.get("/api/kenno").get_json()
        assert isinstance(data["puzzle_number"], int)
        assert 0 <= data["puzzle_number"] < data["total_puzzles"]

    def test_no_auth_required(self, client):
        """Kenno endpoint is public — no login needed."""
        resp = client.get("/api/kenno")
        assert resp.status_code == 200

    def test_max_score_equals_sum_of_word_scores(self, logged_in_admin):
        """max_score returned by API must match manual scoring of the word list."""
        data = logged_in_admin.get("/api/kenno").get_json()
        all_letters = frozenset(data["letters"] + [data["center"]])
        expected = sum(_score_word(w, all_letters) for w in data["words"])
        assert data["max_score"] == expected


# ---------------------------------------------------------------------------
# Puzzle schedule — randomized per-date assignment
# ---------------------------------------------------------------------------

class TestPuzzleSchedule:
    """Verify that each date gets a consistent, valid puzzle from the schedule."""

    def test_same_day_returns_same_puzzle(self, client):
        """Two requests on the same day always return the same puzzle."""
        data1 = client.get("/api/kenno").get_json()
        data2 = client.get("/api/kenno").get_json()
        assert data1["puzzle_number"] == data2["puzzle_number"]

    def test_puzzle_number_in_valid_range(self, client):
        data = client.get("/api/kenno").get_json()
        assert 0 <= data["puzzle_number"] < data["total_puzzles"]


# ---------------------------------------------------------------------------
# Known-puzzle integration test — uses admin override
# ---------------------------------------------------------------------------

class TestKnownPuzzle:
    """Run the API against a specific pinned puzzle via admin override so that
    assertions are independent of which puzzle today happens to be assigned."""

    PUZZLE_IDX = 0

    def test_known_puzzle_has_valid_center(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        assert len(data["center"]) == 1
        assert data["center"] not in data["letters"]

    def test_known_puzzle_has_seven_total_letters(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        all_letters = set(data["letters"] + [data["center"]])
        assert len(all_letters) == 7

    def test_known_puzzle_words_contain_center(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        center = data["center"]
        for word in data["words"]:
            assert center in word

    def test_known_puzzle_max_score_correct(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        all_letters = frozenset(data["letters"] + [data["center"]])
        expected = sum(_score_word(w, all_letters) for w in data["words"])
        assert data["max_score"] == expected

    def test_known_puzzle_number_is_zero(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        assert data["puzzle_number"] == self.PUZZLE_IDX


# ---------------------------------------------------------------------------
# total_puzzles field
# ---------------------------------------------------------------------------

class TestTotalPuzzlesField:
    """Verify total_puzzles is always returned."""

    def test_total_puzzles_present_and_positive(self, client):
        data = client.get("/api/kenno").get_json()
        assert "total_puzzles" in data
        assert isinstance(data["total_puzzles"], int)
        assert data["total_puzzles"] > 0


# ---------------------------------------------------------------------------
# Admin puzzle override via ?puzzle=N
# ---------------------------------------------------------------------------

class TestPuzzleOverride:
    """Admin users can override the daily puzzle via ?puzzle=N query param."""

    def test_admin_can_override_puzzle(self, logged_in_admin):
        target = 7
        data = logged_in_admin.get(f"/api/kenno?puzzle={target}").get_json()
        assert data["puzzle_number"] == target

    def test_admin_override_wraps_around(self, logged_in_admin):
        total = logged_in_admin.get("/api/kenno").get_json()["total_puzzles"]
        target = total + 3
        data = logged_in_admin.get(f"/api/kenno?puzzle={target}").get_json()
        assert data["puzzle_number"] == 3

    def test_non_admin_override_ignored(self, logged_in_user):
        """Regular users cannot override the puzzle — param is silently ignored."""
        data_with_param = logged_in_user.get("/api/kenno?puzzle=7").get_json()
        data_without = logged_in_user.get("/api/kenno").get_json()
        assert data_with_param["puzzle_number"] == data_without["puzzle_number"]

    def test_unauthenticated_override_ignored(self, client):
        """Anonymous users cannot override the puzzle."""
        data_with_param = client.get("/api/kenno?puzzle=7").get_json()
        data_without = client.get("/api/kenno").get_json()
        assert data_with_param["puzzle_number"] == data_without["puzzle_number"]

    def test_admin_override_returns_correct_words(self, logged_in_admin):
        """Overridden puzzle returns the right word set."""
        target = 2
        data = logged_in_admin.get(f"/api/kenno?puzzle={target}").get_json()
        all_letters = frozenset(data["letters"] + [data["center"]])
        expected_score = sum(_score_word(w, all_letters) for w in data["words"])
        assert data["max_score"] == expected_score


# ---------------------------------------------------------------------------
# Admin word blocking
# ---------------------------------------------------------------------------

class TestBlockWord:
    """Admin can permanently remove a word from the puzzle pool."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Ensure a clean puzzle cache for each test."""
        from app.api.kenno import _PUZZLE_CACHE
        _PUZZLE_CACHE.clear()
        yield
        _PUZZLE_CACHE.clear()

    def test_admin_can_block_word(self, logged_in_admin):
        words_before = logged_in_admin.get("/api/kenno").get_json()["words"]
        assert len(words_before) > 0
        word = words_before[0]

        res = logged_in_admin.post("/api/kenno/block", json={"word": word})
        assert res.status_code == 200
        data = res.get_json()
        assert data["blocked"] is True
        assert data["word"] == word

        words_after = logged_in_admin.get("/api/kenno").get_json()["words"]
        assert word not in words_after
        assert len(words_after) == len(words_before) - 1

    def test_blocking_reduces_max_score(self, logged_in_admin):
        puzzle_data = logged_in_admin.get("/api/kenno").get_json()
        word = puzzle_data["words"][0]
        score_before = puzzle_data["max_score"]

        logged_in_admin.post("/api/kenno/block", json={"word": word})

        score_after = logged_in_admin.get("/api/kenno").get_json()["max_score"]
        assert score_after < score_before

    def test_blocking_same_word_twice_is_idempotent(self, logged_in_admin):
        word = logged_in_admin.get("/api/kenno").get_json()["words"][0]
        logged_in_admin.post("/api/kenno/block", json={"word": word})
        res = logged_in_admin.post("/api/kenno/block", json={"word": word})
        assert res.status_code == 200

    def test_non_admin_cannot_block(self, logged_in_user):
        res = logged_in_user.post("/api/kenno/block", json={"word": "test"})
        assert res.status_code == 403

    def test_unauthenticated_cannot_block(self, client):
        res = client.post("/api/kenno/block", json={"word": "test"})
        assert res.status_code == 401

    def test_missing_word_field_returns_400(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/block", json={})
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Center-letter variations endpoint
# ---------------------------------------------------------------------------

class TestVariationsEndpoint:
    """GET /api/kenno/variations returns all 7 center-letter options for a puzzle."""

    def test_returns_seven_variations(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        assert len(data["variations"]) == 7

    def test_variation_has_required_fields(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        for v in data["variations"]:
            assert "center" in v
            assert "word_count" in v
            assert "max_score" in v
            assert "pangram_count" in v
            assert "is_active" in v

    def test_exactly_one_is_active(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        active = [v for v in data["variations"] if v["is_active"]]
        assert len(active) == 1

    def test_active_matches_current_center(self, logged_in_admin):
        puzzle_data = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        var_data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        active = [v for v in var_data["variations"] if v["is_active"]][0]
        assert active["center"] == puzzle_data["center"]

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.get("/api/kenno/variations?puzzle=0")
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.get("/api/kenno/variations?puzzle=0")
        assert res.status_code == 401

    def test_requires_puzzle_param(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/variations")
        assert res.status_code == 400

    def test_word_counts_are_positive(self, logged_in_admin):
        """At least the active center should have words."""
        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        active = [v for v in data["variations"] if v["is_active"]][0]
        assert active["word_count"] > 0
        assert active["max_score"] > 0


# ---------------------------------------------------------------------------
# Set center letter endpoint
# ---------------------------------------------------------------------------

class TestSetCenter:
    """POST /api/kenno/center changes the center letter for a puzzle."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from app.api.kenno import _PUZZLE_CACHE
        _PUZZLE_CACHE.clear()
        yield
        _PUZZLE_CACHE.clear()

    def test_changes_center(self, logged_in_admin):
        # Get puzzle 0's current state from the API
        puzzle = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        all_letters = puzzle["letters"] + [puzzle["center"]]
        new_center = [l for l in all_letters if l != puzzle["center"]][0]

        res = logged_in_admin.post("/api/kenno/center", json={"puzzle": 0, "center": new_center})
        assert res.status_code == 200
        assert res.get_json()["center"] == new_center

        # Verify the puzzle now uses the new center
        data = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        assert data["center"] == new_center

    def test_invalid_letter_rejected(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/center", json={"puzzle": 0, "center": "z"})
        assert res.status_code == 400

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.post("/api/kenno/center", json={"puzzle": 0, "center": "r"})
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.post("/api/kenno/center", json={"puzzle": 0, "center": "r"})
        assert res.status_code == 401

    def test_requires_puzzle_param(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/center", json={"center": "r"})
        assert res.status_code == 400

    def test_persists_across_cache_clear(self, logged_in_admin):
        from app.api.kenno import _PUZZLE_CACHE
        puzzle = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        all_letters = puzzle["letters"] + [puzzle["center"]]
        new_center = [l for l in all_letters if l != puzzle["center"]][0]

        logged_in_admin.post("/api/kenno/center", json={"puzzle": 0, "center": new_center})
        _PUZZLE_CACHE.clear()

        data = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        assert data["center"] == new_center

    def test_variations_reflect_new_active(self, logged_in_admin):
        puzzle = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        all_letters = puzzle["letters"] + [puzzle["center"]]
        new_center = [l for l in all_letters if l != puzzle["center"]][0]

        logged_in_admin.post("/api/kenno/center", json={"puzzle": 0, "center": new_center})

        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        active = [v for v in data["variations"] if v["is_active"]][0]
        assert active["center"] == new_center


# ---------------------------------------------------------------------------
# Rank achievement tracking
# ---------------------------------------------------------------------------

class TestKennoAchievements:
    """POST /api/kenno/achievement and GET /api/kenno/achievements."""

    VALID_ACHIEVEMENT = {
        "puzzle_number": 0,
        "rank": "Hyvä alku",
        "score": 5,
        "max_score": 100,
        "words_found": 3,
        "elapsed_ms": 60000,
    }

    def test_post_valid_achievement(self, client):
        res = client.post("/api/kenno/achievement", json=self.VALID_ACHIEVEMENT)
        assert res.status_code == 201
        assert res.get_json()["status"] == "recorded"

    def test_post_rejects_unknown_rank(self, client):
        data = {**self.VALID_ACHIEVEMENT, "rank": "Mega Master"}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 400

    def test_post_rejects_invalid_puzzle_number(self, client):
        data = {**self.VALID_ACHIEVEMENT, "puzzle_number": 9999}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 400

    def test_post_rejects_negative_puzzle_number(self, client):
        data = {**self.VALID_ACHIEVEMENT, "puzzle_number": -1}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 400

    def test_post_rejects_string_puzzle_number(self, client):
        data = {**self.VALID_ACHIEVEMENT, "puzzle_number": "abc"}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 400

    def test_post_rejects_negative_score(self, client):
        data = {**self.VALID_ACHIEVEMENT, "score": -5}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 400

    def test_post_rejects_zero_max_score(self, client):
        data = {**self.VALID_ACHIEVEMENT, "max_score": 0}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 400

    def test_session_dedup_same_puzzle_rank(self, client):
        """Same puzzle+rank in same session should only record once."""
        res1 = client.post("/api/kenno/achievement", json=self.VALID_ACHIEVEMENT)
        assert res1.status_code == 201

        res2 = client.post("/api/kenno/achievement", json=self.VALID_ACHIEVEMENT)
        assert res2.status_code == 200
        assert res2.get_json()["status"] == "already_recorded"

    def test_different_ranks_same_puzzle_both_recorded(self, client):
        """Different ranks for the same puzzle should both be recorded."""
        res1 = client.post("/api/kenno/achievement", json=self.VALID_ACHIEVEMENT)
        assert res1.status_code == 201

        data2 = {**self.VALID_ACHIEVEMENT, "rank": "Nyt mennään!", "score": 15}
        res2 = client.post("/api/kenno/achievement", json=data2)
        assert res2.status_code == 201

    def test_different_puzzles_same_rank_both_recorded(self, client):
        """Same rank on different puzzles should both be recorded."""
        res1 = client.post("/api/kenno/achievement", json=self.VALID_ACHIEVEMENT)
        assert res1.status_code == 201

        data2 = {**self.VALID_ACHIEVEMENT, "puzzle_number": 1}
        res2 = client.post("/api/kenno/achievement", json=data2)
        assert res2.status_code == 201

    def test_elapsed_ms_optional(self, client):
        data = {k: v for k, v in self.VALID_ACHIEVEMENT.items() if k != "elapsed_ms"}
        res = client.post("/api/kenno/achievement", json=data)
        assert res.status_code == 201

    def test_get_requires_admin(self, logged_in_user):
        res = logged_in_user.get("/api/kenno/achievements")
        assert res.status_code == 403

    def test_get_requires_auth(self, client):
        res = client.get("/api/kenno/achievements")
        assert res.status_code == 401

    def test_get_returns_daily_counts(self, client, logged_in_admin):
        # Post some achievements as anonymous client
        client.post("/api/kenno/achievement", json=self.VALID_ACHIEVEMENT)
        data2 = {**self.VALID_ACHIEVEMENT, "rank": "Sanavalmis", "score": 40}
        client.post("/api/kenno/achievement", json=data2)

        # Fetch as admin
        res = logged_in_admin.get("/api/kenno/achievements?days=7")
        assert res.status_code == 200
        data = res.get_json()
        assert data["days"] == 7
        assert len(data["daily"]) == 7
        assert "totals" in data

        # Today's entry should have the counts
        today = data["daily"][-1]
        assert today["counts"]["Hyvä alku"] >= 1
        assert today["counts"]["Sanavalmis"] >= 1
        assert today["total"] >= 2

    def test_get_days_clamped_to_max_90(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/achievements?days=200")
        data = res.get_json()
        assert data["days"] == 90

    def test_get_days_clamped_to_min_1(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/achievements?days=0")
        data = res.get_json()
        assert data["days"] == 1

    def test_get_all_ranks_present_in_totals(self, logged_in_admin):
        from app.api.kenno import VALID_RANKS
        res = logged_in_admin.get("/api/kenno/achievements")
        data = res.get_json()
        for rank in VALID_RANKS:
            assert rank in data["totals"]


# ---------------------------------------------------------------------------
# Preview endpoint
# ---------------------------------------------------------------------------

class TestPreviewEndpoint:
    """POST /api/kenno/preview returns variations for arbitrary letters."""

    VALID_LETTERS = ["a", "e", "k", "l", "n", "s", "ö"]

    def test_returns_seven_variations(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": self.VALID_LETTERS})
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["variations"]) == 7
        assert data["letters"] == sorted(self.VALID_LETTERS)

    def test_variation_has_required_fields(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": self.VALID_LETTERS})
        data = res.get_json()
        for v in data["variations"]:
            assert "center" in v
            assert "word_count" in v
            assert "max_score" in v
            assert "pangram_count" in v

    def test_fewer_than_7_letters_rejected(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": ["a", "b", "c"]})
        assert res.status_code == 400

    def test_duplicate_letters_rejected(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": ["a", "a", "b", "c", "d", "e", "f"]})
        assert res.status_code == 400

    def test_invalid_chars_rejected(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": ["a", "b", "c", "d", "e", "f", "1"]})
        assert res.status_code == 400

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.post("/api/kenno/preview", json={"letters": self.VALID_LETTERS})
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.post("/api/kenno/preview", json={"letters": self.VALID_LETTERS})
        assert res.status_code == 401

    def test_more_than_7_letters_rejected(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": ["a", "b", "c", "d", "e", "f", "g", "h"]})
        assert res.status_code == 400

    def test_finnish_special_chars_accepted(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/preview", json={"letters": ["a", "b", "c", "d", "e", "ä", "ö"]})
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# Save puzzle endpoint
# ---------------------------------------------------------------------------

class TestSavePuzzleEndpoint:
    """POST /api/kenno/puzzle creates or updates custom puzzles."""

    VALID_LETTERS = ["a", "e", "k", "l", "n", "s", "ö"]

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from app.api.kenno import _PUZZLE_CACHE
        _PUZZLE_CACHE.clear()
        yield
        _PUZZLE_CACHE.clear()

    def _safe_slot(self):
        """Return a slot that is NOT today's live puzzle."""
        from app.api.kenno import _get_puzzle_for_date, _HELSINKI
        from datetime import datetime
        today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
        slot = 5
        if slot == today_slot:
            slot = 6
        return slot

    def test_saves_to_slot(self, logged_in_admin):
        slot = self._safe_slot()
        res = logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": self.VALID_LETTERS, "center": "e",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["slot"] == slot
        assert data["center"] == "e"
        assert data["letters"] == sorted(self.VALID_LETTERS)

    def test_saved_puzzle_served_by_api(self, logged_in_admin):
        slot = self._safe_slot()
        logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": self.VALID_LETTERS, "center": "e",
        })
        data = logged_in_admin.get(f"/api/kenno?puzzle={slot}").get_json()
        assert data["center"] == "e"
        all_api_letters = set(data["letters"] + [data["center"]])
        assert all_api_letters == set(self.VALID_LETTERS)

    def test_rejects_live_slot(self, logged_in_admin):
        from app.api.kenno import _get_puzzle_for_date, _HELSINKI
        from datetime import datetime
        today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
        res = logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": today_slot, "letters": self.VALID_LETTERS, "center": "e",
        })
        assert res.status_code == 409

    def test_sets_center(self, logged_in_admin):
        slot = self._safe_slot()
        logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": self.VALID_LETTERS, "center": "k",
        })
        data = logged_in_admin.get(f"/api/kenno?puzzle={slot}").get_json()
        assert data["center"] == "k"

    def test_new_slot_extends_total_puzzles(self, logged_in_admin):
        new_slot = 50
        res = logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": new_slot, "letters": self.VALID_LETTERS, "center": "e",
        })
        assert res.status_code == 200
        assert res.get_json()["is_new_slot"] is True

        stats = logged_in_admin.get("/api/kenno/stats").get_json()
        assert stats["total_puzzles"] == 51

    def test_overwrite_existing_slot(self, logged_in_admin):
        slot = self._safe_slot()
        logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": self.VALID_LETTERS, "center": "e",
        })
        new_letters = ["b", "d", "h", "i", "m", "o", "u"]
        logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": new_letters, "center": "h",
        })
        data = logged_in_admin.get(f"/api/kenno?puzzle={slot}").get_json()
        assert data["center"] == "h"
        all_letters = set(data["letters"] + [data["center"]])
        assert all_letters == set(new_letters)

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.post("/api/kenno/puzzle", json={
            "slot": 5, "letters": self.VALID_LETTERS, "center": "e",
        })
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.post("/api/kenno/puzzle", json={
            "slot": 5, "letters": self.VALID_LETTERS, "center": "e",
        })
        assert res.status_code == 401

    def test_rejects_negative_slot(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": -1, "letters": self.VALID_LETTERS, "center": "e",
        })
        assert res.status_code == 400

    def test_rejects_invalid_center(self, logged_in_admin):
        slot = self._safe_slot()
        res = logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": self.VALID_LETTERS, "center": "z",
        })
        assert res.status_code == 400

    def test_returns_next_play_date(self, logged_in_admin):
        slot = self._safe_slot()
        res = logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": slot, "letters": self.VALID_LETTERS, "center": "e",
        })
        data = res.get_json()
        assert data["next_play_date"] is not None


# ---------------------------------------------------------------------------
# Schedule endpoint
# ---------------------------------------------------------------------------

class TestScheduleEndpoint:
    """GET /api/kenno/schedule returns upcoming puzzle rotation."""

    def test_returns_14_days_by_default(self, logged_in_admin):
        res = logged_in_admin.get("/api/kenno/schedule")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["schedule"]) == 14

    def test_first_entry_is_today(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/schedule").get_json()
        assert data["schedule"][0]["is_today"] is True

    def test_other_entries_are_not_today(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/schedule").get_json()
        for entry in data["schedule"][1:]:
            assert entry["is_today"] is False

    def test_custom_days_param(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/schedule?days=7").get_json()
        assert len(data["schedule"]) == 7

    def test_days_clamped_to_max_90(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/schedule?days=200").get_json()
        assert len(data["schedule"]) == 90

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.get("/api/kenno/schedule")
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.get("/api/kenno/schedule")
        assert res.status_code == 401

    def test_has_display_number(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/schedule").get_json()
        for entry in data["schedule"]:
            assert entry["display_number"] == entry["slot"] + 1


# ---------------------------------------------------------------------------
# Swap puzzles endpoint
# ---------------------------------------------------------------------------

class TestSwapPuzzlesEndpoint:
    """POST /api/kenno/puzzle/swap swaps two puzzle slots."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from app.api.kenno import _PUZZLE_CACHE
        _PUZZLE_CACHE.clear()
        yield
        _PUZZLE_CACHE.clear()

    def _two_safe_slots(self):
        """Return two slots that are NOT today's live puzzle."""
        from app.api.kenno import _get_puzzle_for_date, _HELSINKI
        from datetime import datetime
        today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
        slots = [s for s in [3, 4, 5, 6] if s != today_slot]
        return slots[0], slots[1]

    def test_swaps_puzzles(self, logged_in_admin):
        a, b = self._two_safe_slots()
        # Read original letters
        data_a = logged_in_admin.get(f"/api/kenno?puzzle={a}").get_json()
        data_b = logged_in_admin.get(f"/api/kenno?puzzle={b}").get_json()
        letters_a = set(data_a["letters"] + [data_a["center"]])
        letters_b = set(data_b["letters"] + [data_b["center"]])

        res = logged_in_admin.post("/api/kenno/puzzle/swap", json={"slot_a": a, "slot_b": b})
        assert res.status_code == 200
        assert res.get_json()["swapped"] is True

        # After swap, slot a should have slot b's letters and vice versa
        new_a = logged_in_admin.get(f"/api/kenno?puzzle={a}").get_json()
        new_b = logged_in_admin.get(f"/api/kenno?puzzle={b}").get_json()
        assert set(new_a["letters"] + [new_a["center"]]) == letters_b
        assert set(new_b["letters"] + [new_b["center"]]) == letters_a

    def test_rejects_live_slot(self, logged_in_admin):
        from app.api.kenno import _get_puzzle_for_date, _HELSINKI
        from datetime import datetime
        today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
        other = 3 if today_slot != 3 else 4
        res = logged_in_admin.post("/api/kenno/puzzle/swap", json={"slot_a": today_slot, "slot_b": other})
        assert res.status_code == 409

    def test_rejects_same_slot(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/puzzle/swap", json={"slot_a": 3, "slot_b": 3})
        assert res.status_code == 400

    def test_rejects_negative_slot(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/puzzle/swap", json={"slot_a": -1, "slot_b": 3})
        assert res.status_code == 400

    def test_rejects_out_of_range(self, logged_in_admin):
        res = logged_in_admin.post("/api/kenno/puzzle/swap", json={"slot_a": 0, "slot_b": 999})
        assert res.status_code == 400

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.post("/api/kenno/puzzle/swap", json={"slot_a": 0, "slot_b": 1})
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.post("/api/kenno/puzzle/swap", json={"slot_a": 0, "slot_b": 1})
        assert res.status_code == 401

    def test_swaps_centers_too(self, logged_in_admin):
        a, b = self._two_safe_slots()
        data_a = logged_in_admin.get(f"/api/kenno?puzzle={a}").get_json()
        data_b = logged_in_admin.get(f"/api/kenno?puzzle={b}").get_json()
        center_a = data_a["center"]
        center_b = data_b["center"]

        logged_in_admin.post("/api/kenno/puzzle/swap", json={"slot_a": a, "slot_b": b})

        new_a = logged_in_admin.get(f"/api/kenno?puzzle={a}").get_json()
        new_b = logged_in_admin.get(f"/api/kenno?puzzle={b}").get_json()
        assert new_a["center"] == center_b
        assert new_b["center"] == center_a


# ---------------------------------------------------------------------------
# Delete puzzle endpoint
# ---------------------------------------------------------------------------

class TestDeletePuzzleEndpoint:
    """DELETE /api/kenno/puzzle/<slot> removes a custom puzzle."""

    VALID_LETTERS = ["a", "e", "k", "l", "n", "s", "ö"]

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from app.api.kenno import _PUZZLE_CACHE
        _PUZZLE_CACHE.clear()
        yield
        _PUZZLE_CACHE.clear()

    def _safe_slot(self):
        from app.api.kenno import _get_puzzle_for_date, _HELSINKI
        from datetime import datetime
        today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
        slot = 5
        if slot == today_slot:
            slot = 6
        return slot

    def test_deletes_puzzle(self, logged_in_admin):
        slot = self._safe_slot()
        # Verify it exists
        data = logged_in_admin.get(f"/api/kenno?puzzle={slot}").get_json()
        assert "center" in data

        # Delete it
        res = logged_in_admin.delete(f"/api/kenno/puzzle/{slot}")
        assert res.status_code == 200
        assert res.get_json()["deleted"] is True

    def test_rejects_live_slot(self, logged_in_admin):
        from app.api.kenno import _get_puzzle_for_date, _HELSINKI
        from datetime import datetime
        today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
        res = logged_in_admin.delete(f"/api/kenno/puzzle/{today_slot}")
        assert res.status_code == 409

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.delete("/api/kenno/puzzle/5")
        assert res.status_code == 403

    def test_requires_auth(self, client):
        res = client.delete("/api/kenno/puzzle/5")
        assert res.status_code == 401

    def test_delete_extended_slot_shrinks_total(self, logged_in_admin):
        """Deleting a slot beyond 41 that was the highest should shrink total_puzzles."""
        # Save to slot 50
        logged_in_admin.post("/api/kenno/puzzle", json={
            "slot": 50, "letters": self.VALID_LETTERS, "center": "e",
        })
        stats = logged_in_admin.get("/api/kenno/stats").get_json()
        assert stats["total_puzzles"] == 51

        # Delete it
        logged_in_admin.delete("/api/kenno/puzzle/50")
        stats2 = logged_in_admin.get("/api/kenno/stats").get_json()
        assert stats2["total_puzzles"] == 41
