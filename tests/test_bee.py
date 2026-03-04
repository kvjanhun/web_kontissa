"""Tests for the Sanakenno (Spelling Bee) API endpoint."""

import hashlib
import pytest
from unittest.mock import patch
from app.api.bee import PUZZLES, _DEFAULT_CENTERS, _score_word, _compute_puzzle, _get_puzzle_dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_letters_for(puzzle_idx):
    """Return the full frozenset of 7 letters for a puzzle index."""
    return frozenset(PUZZLES[puzzle_idx]["letters"])


# ---------------------------------------------------------------------------
# Puzzle catalogue sanity checks (static, no HTTP)
# ---------------------------------------------------------------------------

class TestPuzzleCatalogue:
    """Validate the PUZZLES list itself — catches misconfigured entries before
    they ever reach a player."""

    def test_has_41_puzzles(self):
        assert len(PUZZLES) == 41

    def test_default_centers_matches_puzzles_count(self):
        assert len(_DEFAULT_CENTERS) == len(PUZZLES)

    def test_every_puzzle_has_seven_letters(self):
        for i, p in enumerate(PUZZLES):
            assert "letters" in p, f"Puzzle {i} missing 'letters'"
            assert len(p["letters"]) == 7, (
                f"Puzzle {i} must have exactly 7 letters, got {len(p['letters'])}"
            )

    def test_no_puzzle_has_duplicate_letters(self):
        """All 7 letters must be distinct — duplicates would confuse the
        pangram check and break the honeycomb display."""
        for i, p in enumerate(PUZZLES):
            assert len(set(p["letters"])) == 7, (
                f"Puzzle {i} has duplicate letters: {p['letters']}"
            )

    def test_all_letters_are_lowercase_strings(self):
        for i, p in enumerate(PUZZLES):
            for letter in p["letters"]:
                assert letter == letter.lower(), (
                    f"Puzzle {i} letter {letter!r} is not lowercase"
                )
                assert isinstance(letter, str) and len(letter) == 1, (
                    f"Puzzle {i} letter {letter!r} is not a single character"
                )

    def test_default_center_is_one_of_the_letters(self):
        for i, center in enumerate(_DEFAULT_CENTERS):
            assert center in PUZZLES[i]["letters"], (
                f"Puzzle {i} default center '{center}' not in letters {PUZZLES[i]['letters']}"
            )

    def test_every_puzzle_has_at_least_one_word(self, app):
        """A puzzle with zero valid words in the word list is unplayable."""
        for i in range(len(PUZZLES)):
            puzzle_dict = _get_puzzle_dict(i)
            words, _, _, _ = _compute_puzzle(puzzle_dict)
            assert len(words) > 0, (
                f"Puzzle {i} (letters={PUZZLES[i]['letters']}) "
                f"yielded no valid words — word list may be missing or puzzle "
                f"letters may be wrong"
            )


# ---------------------------------------------------------------------------
# Scoring logic — tested against the real _score_word function
# ---------------------------------------------------------------------------

class TestScoringFunction:
    """Test the _score_word function from bee.py directly."""

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
        assert 0 <= data["puzzle_number"] < len(PUZZLES), (
            f"puzzle_number {data['puzzle_number']} is out of range [0, {len(PUZZLES)})"
        )

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
        assert 0 <= data["puzzle_number"] < len(PUZZLES)


# ---------------------------------------------------------------------------
# Known-puzzle integration test — uses admin override
# ---------------------------------------------------------------------------

class TestKnownPuzzle:
    """Run the API against a specific pinned puzzle via admin override so that
    assertions are independent of which puzzle today happens to be assigned."""

    PUZZLE_IDX = 0

    def test_known_puzzle_center(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        assert data["center"] == _DEFAULT_CENTERS[self.PUZZLE_IDX]

    def test_known_puzzle_letters(self, logged_in_admin):
        data = logged_in_admin.get(f"/api/kenno?puzzle={self.PUZZLE_IDX}").get_json()
        expected_outer = [l for l in PUZZLES[self.PUZZLE_IDX]["letters"]
                          if l != _DEFAULT_CENTERS[self.PUZZLE_IDX]]
        assert set(data["letters"]) == set(expected_outer)

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

    def test_total_puzzles_present_and_correct(self, client):
        data = client.get("/api/kenno").get_json()
        assert "total_puzzles" in data
        assert data["total_puzzles"] == len(PUZZLES)


# ---------------------------------------------------------------------------
# Admin puzzle override via ?puzzle=N
# ---------------------------------------------------------------------------

class TestPuzzleOverride:
    """Admin users can override the daily puzzle via ?puzzle=N query param."""

    def test_admin_can_override_puzzle(self, logged_in_admin):
        target = 7
        data = logged_in_admin.get(f"/api/kenno?puzzle={target}").get_json()
        assert data["puzzle_number"] == target
        assert data["center"] == _DEFAULT_CENTERS[target]

    def test_admin_override_wraps_around(self, logged_in_admin):
        # Requesting puzzle index beyond range wraps via modulo
        target = len(PUZZLES) + 3
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
        from app.api.bee import _PUZZLE_CACHE
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

    def test_active_matches_default_center(self, logged_in_admin):
        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        active = [v for v in data["variations"] if v["is_active"]][0]
        assert active["center"] == _DEFAULT_CENTERS[0]

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
        from app.api.bee import _PUZZLE_CACHE
        _PUZZLE_CACHE.clear()
        yield
        _PUZZLE_CACHE.clear()

    def test_changes_center(self, logged_in_admin):
        # Pick a letter that is NOT the default center for puzzle 0
        letters = PUZZLES[0]["letters"]
        new_center = [l for l in letters if l != _DEFAULT_CENTERS[0]][0]

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
        from app.api.bee import _PUZZLE_CACHE
        letters = PUZZLES[0]["letters"]
        new_center = [l for l in letters if l != _DEFAULT_CENTERS[0]][0]

        logged_in_admin.post("/api/kenno/center", json={"puzzle": 0, "center": new_center})
        _PUZZLE_CACHE.clear()

        data = logged_in_admin.get("/api/kenno?puzzle=0").get_json()
        assert data["center"] == new_center

    def test_variations_reflect_new_active(self, logged_in_admin):
        letters = PUZZLES[0]["letters"]
        new_center = [l for l in letters if l != _DEFAULT_CENTERS[0]][0]

        logged_in_admin.post("/api/kenno/center", json={"puzzle": 0, "center": new_center})

        data = logged_in_admin.get("/api/kenno/variations?puzzle=0").get_json()
        active = [v for v in data["variations"] if v["is_active"]][0]
        assert active["center"] == new_center
