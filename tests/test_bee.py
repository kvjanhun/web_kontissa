"""Tests for the Sanakenno (Spelling Bee) API endpoint."""

import pytest
from unittest.mock import patch
from app.api.bee import PUZZLES, _score_word, _compute_puzzle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_letters_for(puzzle):
    """Return the full frozenset of 7 letters for a puzzle dict."""
    return frozenset([puzzle["center"]] + puzzle["outer"])


# ---------------------------------------------------------------------------
# Puzzle catalogue sanity checks (static, no HTTP)
# ---------------------------------------------------------------------------

class TestPuzzleCatalogue:
    """Validate the PUZZLES list itself — catches misconfigured entries before
    they ever reach a player."""

    def test_has_fifty_puzzles(self):
        assert len(PUZZLES) == 50

    def test_every_puzzle_has_center(self):
        for i, p in enumerate(PUZZLES):
            assert "center" in p, f"Puzzle {i} missing 'center'"
            assert isinstance(p["center"], str) and len(p["center"]) == 1, (
                f"Puzzle {i} center must be a single character, got {p['center']!r}"
            )

    def test_every_puzzle_has_six_outer_letters(self):
        for i, p in enumerate(PUZZLES):
            assert "outer" in p, f"Puzzle {i} missing 'outer'"
            assert len(p["outer"]) == 6, (
                f"Puzzle {i} outer must have exactly 6 letters, got {len(p['outer'])}"
            )

    def test_no_puzzle_has_duplicate_letters(self):
        """Center + all outer letters must all be distinct — duplicates would
        confuse the pangram check and break the honeycomb display."""
        for i, p in enumerate(PUZZLES):
            all_letters = [p["center"]] + p["outer"]
            assert len(set(all_letters)) == 7, (
                f"Puzzle {i} has duplicate letters: {all_letters}"
            )

    def test_center_not_in_outer(self):
        """Center letter must not appear in the outer ring."""
        for i, p in enumerate(PUZZLES):
            assert p["center"] not in p["outer"], (
                f"Puzzle {i} center '{p['center']}' appears in outer letters"
            )

    def test_all_letters_are_lowercase_strings(self):
        for i, p in enumerate(PUZZLES):
            for letter in [p["center"]] + p["outer"]:
                assert letter == letter.lower(), (
                    f"Puzzle {i} letter {letter!r} is not lowercase"
                )
                assert isinstance(letter, str) and len(letter) == 1, (
                    f"Puzzle {i} letter {letter!r} is not a single character"
                )

    def test_every_puzzle_has_at_least_one_word(self):
        """A puzzle with zero valid words in the word list is unplayable."""
        for i, p in enumerate(PUZZLES):
            words, _ = _compute_puzzle(p)
            assert len(words) > 0, (
                f"Puzzle {i} (center={p['center']!r}, outer={p['outer']}) "
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

class TestBeeEndpoint:
    def test_returns_200_with_json(self, client):
        resp = client.get("/api/bee")
        assert resp.status_code == 200
        assert resp.content_type.startswith("application/json")

    def test_response_has_required_fields(self, client):
        data = client.get("/api/bee").get_json()
        assert "center" in data
        assert "letters" in data
        assert "words" in data
        assert "max_score" in data
        assert "puzzle_number" in data

    def test_center_is_single_lowercase_letter(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["center"], str)
        assert len(data["center"]) == 1
        assert data["center"] == data["center"].lower()

    def test_letters_has_six_entries(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["letters"], list)
        assert len(data["letters"]) == 6

    def test_letters_are_all_distinct(self, client):
        data = client.get("/api/bee").get_json()
        assert len(set(data["letters"])) == 6, "Outer letters must all be distinct"

    def test_center_not_in_outer_letters(self, client):
        data = client.get("/api/bee").get_json()
        assert data["center"] not in data["letters"], (
            f"Center '{data['center']}' must not appear in outer letters"
        )

    def test_words_is_nonempty_list(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["words"], list)
        assert len(data["words"]) > 0

    def test_words_are_sorted_alphabetically(self, client):
        data = client.get("/api/bee").get_json()
        assert data["words"] == sorted(data["words"])

    def test_words_have_no_duplicates(self, client):
        data = client.get("/api/bee").get_json()
        assert len(data["words"]) == len(set(data["words"])), "Word list must not contain duplicates"

    def test_all_words_contain_center(self, client):
        data = client.get("/api/bee").get_json()
        center = data["center"]
        for word in data["words"]:
            assert center in word, f"Word '{word}' missing center letter '{center}'"

    def test_all_words_at_least_four_letters(self, client):
        data = client.get("/api/bee").get_json()
        for word in data["words"]:
            assert len(word) >= 4, f"Word '{word}' is shorter than 4 letters"

    def test_all_words_use_only_valid_letters(self, client):
        data = client.get("/api/bee").get_json()
        valid = set(data["letters"]) | {data["center"]}
        for word in data["words"]:
            for ch in word:
                assert ch in valid, f"Word '{word}' contains invalid letter '{ch}'"

    def test_max_score_is_positive_int(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["max_score"], int)
        assert data["max_score"] > 0

    def test_puzzle_number_is_non_negative_int_within_range(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["puzzle_number"], int)
        assert 0 <= data["puzzle_number"] < len(PUZZLES), (
            f"puzzle_number {data['puzzle_number']} is out of range [0, {len(PUZZLES)})"
        )

    def test_no_auth_required(self, client):
        """Bee endpoint is public — no login needed."""
        resp = client.get("/api/bee")
        assert resp.status_code == 200

    def test_max_score_equals_sum_of_word_scores(self, client):
        """max_score returned by API must match manual scoring of the word list."""
        data = client.get("/api/bee").get_json()
        all_letters = frozenset(data["letters"] + [data["center"]])
        expected = sum(_score_word(w, all_letters) for w in data["words"])
        assert data["max_score"] == expected


# ---------------------------------------------------------------------------
# Puzzle rotation — deterministic via date mock
# ---------------------------------------------------------------------------

class TestPuzzleRotation:
    """Verify that the puzzle rotates daily using toordinal() % len(PUZZLES)."""

    def test_puzzle_number_is_ordinal_mod_puzzle_count(self, client):
        """Mocking date.today() lets us assert the exact puzzle_number returned."""
        from datetime import date

        # Pick an ordinal that gives a known remainder
        target_idx = 17
        # Find an ordinal whose remainder equals target_idx
        # date.min.toordinal() == 1
        ordinal = target_idx  # 17 % 50 == 17, assuming len(PUZZLES)==50
        fake_date = date.fromordinal(ordinal)

        with patch("app.api.bee.date") as mock_date:
            mock_date.today.return_value = fake_date
            data = client.get("/api/bee").get_json()

        assert data["puzzle_number"] == target_idx

    def test_puzzle_wraps_around_after_50_days(self, client):
        """After 50 days the same puzzle repeats (cycle length == number of puzzles)."""
        from datetime import date, timedelta

        base = date(2025, 1, 1)
        cycle = len(PUZZLES)  # 50

        with patch("app.api.bee.date") as mock_date:
            mock_date.today.return_value = base
            data_day0 = client.get("/api/bee").get_json()

        with patch("app.api.bee.date") as mock_date:
            mock_date.today.return_value = base + timedelta(days=cycle)
            data_day50 = client.get("/api/bee").get_json()

        assert data_day0["puzzle_number"] == data_day50["puzzle_number"]
        assert data_day0["center"] == data_day50["center"]
        assert data_day0["letters"] == data_day50["letters"]

    def test_adjacent_days_give_different_puzzles(self, client):
        """Consecutive days should (almost always) serve a different puzzle.
        We check at a point where the boundary is known."""
        from datetime import date, timedelta

        # Use day 0 of a cycle and day 1; they are guaranteed to differ
        # because puzzle 0 and puzzle 1 have different center letters.
        cycle_start_ordinal = len(PUZZLES)  # ordinal % 50 == 0
        day0 = date.fromordinal(cycle_start_ordinal)
        day1 = date.fromordinal(cycle_start_ordinal + 1)

        with patch("app.api.bee.date") as mock_date:
            mock_date.today.return_value = day0
            data0 = client.get("/api/bee").get_json()

        with patch("app.api.bee.date") as mock_date:
            mock_date.today.return_value = day1
            data1 = client.get("/api/bee").get_json()

        assert data0["puzzle_number"] != data1["puzzle_number"]


# ---------------------------------------------------------------------------
# Known-puzzle integration test (deterministic)
# ---------------------------------------------------------------------------

class TestKnownPuzzle:
    """Run the API against a specific pinned puzzle so that assertions are
    independent of which puzzle today happens to rotate to."""

    # Puzzle index 0: center='r', outer=['e','n','p','s','y','ä']
    PUZZLE_IDX = 0
    PUZZLE = PUZZLES[0]

    @pytest.fixture
    def pinned_client(self, client):
        """Client that always serves puzzle index 0."""
        from datetime import date
        # ordinal 0 % 50 == 0 — but ordinal 0 is invalid; use 50 instead (50 % 50 == 0)
        with patch("app.api.bee.date") as mock_date:
            mock_date.today.return_value = date.fromordinal(len(PUZZLES))
            yield client

    def test_known_puzzle_center(self, pinned_client):
        data = pinned_client.get("/api/bee").get_json()
        assert data["center"] == self.PUZZLE["center"]

    def test_known_puzzle_letters(self, pinned_client):
        data = pinned_client.get("/api/bee").get_json()
        assert set(data["letters"]) == set(self.PUZZLE["outer"])

    def test_known_puzzle_words_contain_center(self, pinned_client):
        data = pinned_client.get("/api/bee").get_json()
        center = data["center"]
        for word in data["words"]:
            assert center in word

    def test_known_puzzle_max_score_correct(self, pinned_client):
        data = pinned_client.get("/api/bee").get_json()
        all_letters = frozenset(data["letters"] + [data["center"]])
        expected = sum(_score_word(w, all_letters) for w in data["words"])
        assert data["max_score"] == expected

    def test_known_puzzle_number_is_zero(self, pinned_client):
        data = pinned_client.get("/api/bee").get_json()
        assert data["puzzle_number"] == self.PUZZLE_IDX


# ---------------------------------------------------------------------------
# total_puzzles field
# ---------------------------------------------------------------------------

class TestTotalPuzzlesField:
    """Verify total_puzzles is always returned."""

    def test_total_puzzles_present_and_correct(self, client):
        data = client.get("/api/bee").get_json()
        assert "total_puzzles" in data
        assert data["total_puzzles"] == len(PUZZLES)


# ---------------------------------------------------------------------------
# Admin puzzle override via ?puzzle=N
# ---------------------------------------------------------------------------

class TestPuzzleOverride:
    """Admin users can override the daily puzzle via ?puzzle=N query param."""

    def test_admin_can_override_puzzle(self, logged_in_admin):
        target = 7
        data = logged_in_admin.get(f"/api/bee?puzzle={target}").get_json()
        assert data["puzzle_number"] == target
        assert data["center"] == PUZZLES[target]["center"]

    def test_admin_override_wraps_around(self, logged_in_admin):
        # Requesting puzzle index beyond range wraps via modulo
        target = len(PUZZLES) + 3
        data = logged_in_admin.get(f"/api/bee?puzzle={target}").get_json()
        assert data["puzzle_number"] == 3

    def test_non_admin_override_ignored(self, logged_in_user):
        """Regular users cannot override the puzzle — param is silently ignored."""
        data_with_param = logged_in_user.get("/api/bee?puzzle=7").get_json()
        data_without = logged_in_user.get("/api/bee").get_json()
        assert data_with_param["puzzle_number"] == data_without["puzzle_number"]

    def test_unauthenticated_override_ignored(self, client):
        """Anonymous users cannot override the puzzle."""
        data_with_param = client.get("/api/bee?puzzle=7").get_json()
        data_without = client.get("/api/bee").get_json()
        assert data_with_param["puzzle_number"] == data_without["puzzle_number"]

    def test_admin_override_returns_correct_words(self, logged_in_admin):
        """Overridden puzzle returns the right word set."""
        target = 2
        data = logged_in_admin.get(f"/api/bee?puzzle={target}").get_json()
        p = PUZZLES[target]
        all_letters = frozenset([p["center"]] + p["outer"])
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
        words_before = logged_in_admin.get("/api/bee").get_json()["words"]
        assert len(words_before) > 0
        word = words_before[0]

        res = logged_in_admin.post("/api/bee/block", json={"word": word})
        assert res.status_code == 200
        data = res.get_json()
        assert data["blocked"] is True
        assert data["word"] == word

        words_after = logged_in_admin.get("/api/bee").get_json()["words"]
        assert word not in words_after
        assert len(words_after) == len(words_before) - 1

    def test_blocking_reduces_max_score(self, logged_in_admin):
        puzzle_data = logged_in_admin.get("/api/bee").get_json()
        word = puzzle_data["words"][0]
        score_before = puzzle_data["max_score"]

        logged_in_admin.post("/api/bee/block", json={"word": word})

        score_after = logged_in_admin.get("/api/bee").get_json()["max_score"]
        assert score_after < score_before

    def test_blocking_same_word_twice_is_idempotent(self, logged_in_admin):
        word = logged_in_admin.get("/api/bee").get_json()["words"][0]
        logged_in_admin.post("/api/bee/block", json={"word": word})
        res = logged_in_admin.post("/api/bee/block", json={"word": word})
        assert res.status_code == 200

    def test_non_admin_cannot_block(self, logged_in_user):
        res = logged_in_user.post("/api/bee/block", json={"word": "test"})
        assert res.status_code == 403

    def test_unauthenticated_cannot_block(self, client):
        res = client.post("/api/bee/block", json={"word": "test"})
        assert res.status_code == 401

    def test_missing_word_field_returns_400(self, logged_in_admin):
        res = logged_in_admin.post("/api/bee/block", json={})
        assert res.status_code == 400
