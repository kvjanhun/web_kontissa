"""Tests for the Sanakenno (Spelling Bee) API endpoint."""


class TestBeeEndpoint:
    def test_returns_json(self, client):
        resp = client.get("/api/bee")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "center" in data
        assert "letters" in data
        assert "words" in data
        assert "max_score" in data
        assert "puzzle_number" in data

    def test_center_is_single_letter(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["center"], str)
        assert len(data["center"]) == 1

    def test_letters_has_six_entries(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["letters"], list)
        assert len(data["letters"]) == 6

    def test_words_is_nonempty_list(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["words"], list)
        assert len(data["words"]) > 0

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
        valid = set(data["letters"] + [data["center"]])
        for word in data["words"]:
            for ch in word:
                assert ch in valid, f"Word '{word}' contains invalid letter '{ch}'"

    def test_max_score_is_positive(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["max_score"], int)
        assert data["max_score"] > 0

    def test_words_are_sorted(self, client):
        data = client.get("/api/bee").get_json()
        assert data["words"] == sorted(data["words"])

    def test_puzzle_number_is_int(self, client):
        data = client.get("/api/bee").get_json()
        assert isinstance(data["puzzle_number"], int)

    def test_no_auth_required(self, client):
        """Bee endpoint is public — no login needed."""
        resp = client.get("/api/bee")
        assert resp.status_code == 200


class TestBeeScoring:
    """Verify the scoring logic matches the spec."""

    def _score(self, word, all_letters):
        pts = 1 if len(word) == 4 else len(word)
        if frozenset(all_letters).issubset(set(word)):
            pts += 7
        return pts

    def test_four_letter_word_scores_one(self):
        assert self._score("kala", set("aklsunt")) == 1

    def test_five_letter_word_scores_length(self):
        assert self._score("lasku", set("aklsunt")) == 5

    def test_long_word_scores_length(self):
        # "auttava" has 7 chars, uses only a/u/t/v — but not all of "aklsunt"
        assert self._score("auttava", set("aklsunt")) == 7

    def test_pangram_bonus(self):
        # A word using all 7 letters gets length + 7
        all_letters = set("aklsunt")
        word = "alkusanat"  # uses a, l, k, u, s, n, t — all 7
        score = self._score(word, all_letters)
        assert score == len(word) + 7

    def test_non_pangram_no_bonus(self):
        all_letters = set("aklsunt")
        word = "kala"  # only uses k, a, l — not all 7
        assert self._score(word, all_letters) == 1

    def test_max_score_consistent(self, client):
        """Max score returned by API should match manual calculation."""
        data = client.get("/api/bee").get_json()
        all_letters = set(data["letters"] + [data["center"]])
        expected = sum(self._score(w, all_letters) for w in data["words"])
        assert data["max_score"] == expected
