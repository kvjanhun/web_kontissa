from datetime import date
from flask import jsonify, request
from flask_login import current_user, login_required
import os

from app import app
from app.models import db, BlockedWord

_WORDLIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'kotus_words.txt')
try:
    with open(_WORDLIST_PATH, encoding='utf-8') as _f:
        # Normalise hyphenated compounds (e.g. lähi-itä → lähiitä) so they are
        # valid puzzle words; the frozenset also deduplicates any collisions.
        _ALL_WORDS = frozenset(line.strip().replace('-', '') for line in _f if line.strip())
except FileNotFoundError:
    _ALL_WORDS = frozenset()

PUZZLES = [
    {"center": "r", "outer": ["e", "n", "p", "s", "y", "ä"]},       # 54 words
    {"center": "ä", "outer": ["d", "e", "h", "l", "r", "s"]},       # 34 words
    {"center": "n", "outer": ["j", "k", "o", "p", "r", "u"]},       # 26 words
    {"center": "n", "outer": ["e", "h", "i", "m", "y", "ä"]},       # 62 words
    {"center": "l", "outer": ["e", "m", "n", "o", "s", "u"]},       # 53 words
    {"center": "y", "outer": ["k", "l", "o", "s", "u", "ä"]},       # 47 words
    {"center": "h", "outer": ["d", "e", "p", "s", "u", "ä"]},       # 20 words
    {"center": "h", "outer": ["a", "k", "l", "m", "n", "s"]},       # 32 words
    {"center": "p", "outer": ["a", "d", "e", "g", "i", "o"]},       # 27 words
    {"center": "v", "outer": ["e", "i", "l", "m", "n", "r"]},       # 50 words
    {"center": "s", "outer": ["e", "h", "k", "r", "t", "u"]},       # 65 words
    {"center": "h", "outer": ["d", "e", "k", "l", "t", "ä"]},       # 49 words
    {"center": "p", "outer": ["a", "r", "u", "y", "ä", "ö"]},       # 37 words
    {"center": "d", "outer": ["a", "i", "n", "o", "t", "u"]},       # 34 words
    {"center": "j", "outer": ["k", "n", "s", "t", "ä", "ö"]},       # 20 words
    {"center": "y", "outer": ["e", "h", "i", "l", "m", "s"]},       # 48 words
    {"center": "u", "outer": ["a", "e", "h", "i", "r", "v"]},       # 46 words
    {"center": "d", "outer": ["e", "i", "l", "n", "s", "v"]},       # 27 words
    {"center": "n", "outer": ["e", "h", "i", "t", "y", "ö"]},       # 63 words
    {"center": "o", "outer": ["a", "d", "h", "i", "m", "u"]},       # 30 words
    {"center": "d", "outer": ["a", "e", "i", "l", "n", "u"]},       # 36 words
    {"center": "y", "outer": ["d", "h", "j", "r", "s", "ä"]},       # 41 words
    {"center": "h", "outer": ["a", "e", "l", "s", "t", "v"]},       # 59 words
    {"center": "y", "outer": ["e", "i", "k", "l", "t", "v"]},       # 53 words
    {"center": "e", "outer": ["h", "m", "n", "o", "p", "r"]},       # 29 words
    {"center": "e", "outer": ["a", "j", "o", "t", "u", "ä"]},       # 24 words
    {"center": "u", "outer": ["a", "e", "j", "l", "n", "o"]},       # 53 words
    {"center": "s", "outer": ["e", "k", "l", "n", "ä", "ö"]},       # 53 words
    {"center": "u", "outer": ["e", "i", "l", "m", "p", "ä"]},       # 57 words
    {"center": "p", "outer": ["i", "l", "s", "v", "y", "ä"]},       # 77 words
    {"center": "v", "outer": ["h", "i", "r", "s", "t", "ä"]},       # 72 words
    {"center": "i", "outer": ["k", "t", "v", "y", "ä", "ö"]},       # 49 words
    {"center": "m", "outer": ["i", "n", "t", "y", "ä", "ö"]},       # 64 words
    {"center": "t", "outer": ["a", "d", "h", "m", "n", "o"]},       # 73 words
    {"center": "i", "outer": ["a", "h", "n", "r", "u", "ä"]},       # 65 words
    {"center": "s", "outer": ["m", "n", "o", "t", "u", "ä"]},       # 65 words
    {"center": "o", "outer": ["a", "b", "d", "i", "k", "r"]},       # 65 words
    {"center": "i", "outer": ["h", "k", "m", "s", "v", "y"]},       # 39 words
    {"center": "t", "outer": ["a", "e", "g", "h", "r", "y"]},       # 42 words
    {"center": "o", "outer": ["a", "d", "h", "i", "j", "p"]},       # 40 words
    {"center": "n", "outer": ["e", "i", "l", "v", "y", "ö"]},       # 41 words
]


def _score_word(word, all_letters_frozenset):
    pts = 1 if len(word) == 4 else len(word)
    if all_letters_frozenset.issubset(set(word)):
        pts += 7
    return pts


def _compute_puzzle(puzzle):
    center = puzzle["center"]
    outer = puzzle["outer"]
    all_letters = set([center] + outer)
    letter_frozenset = frozenset(all_letters)

    try:
        blocked = frozenset(bw.word for bw in BlockedWord.query.all())
    except Exception:
        blocked = frozenset()

    words = []
    max_score = 0
    for word in _ALL_WORDS:
        if word in blocked:
            continue
        if (
            len(word) >= 4
            and center in word
            and all(c in all_letters for c in word)
        ):
            words.append(word)
            max_score += _score_word(word, letter_frozenset)

    return sorted(words), max_score


_PUZZLE_CACHE: dict = {}  # Cleared on container restart or when words are blocked


def _get_puzzle_data(idx):
    if idx not in _PUZZLE_CACHE:
        _PUZZLE_CACHE[idx] = _compute_puzzle(PUZZLES[idx])
    return _PUZZLE_CACHE[idx]


def _get_puzzle_for_date(date_obj):
    """Return the puzzle index for a given date.

    Puzzles rotate sequentially: today (2026-02-24) is puzzle 2, tomorrow is 3,
    day after is 4, etc., cycling through all 41 puzzles.
    """
    ROTATION_START = date(2026, 2, 24)
    START_INDEX = 1  # Display: Peli 2/41 today, Peli 3/41 tomorrow, etc.
    days_since_start = (date_obj - ROTATION_START).days
    return (START_INDEX + days_since_start) % len(PUZZLES)


@app.route("/api/bee")
def bee():
    puzzle_number = _get_puzzle_for_date(date.today())

    override = request.args.get("puzzle", type=int)
    if (
        override is not None
        and current_user.is_authenticated
        and getattr(current_user, "role", None) == "admin"
    ):
        puzzle_number = override % len(PUZZLES)

    puzzle = PUZZLES[puzzle_number]
    words, max_score = _get_puzzle_data(puzzle_number)

    return jsonify(
        {
            "center": puzzle["center"],
            "letters": puzzle["outer"],
            "words": words,
            "max_score": max_score,
            "puzzle_number": puzzle_number,
            "total_puzzles": len(PUZZLES),
        }
    )


@app.route("/api/bee/block", methods=["POST"])
@login_required
def bee_block_word():
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    word = data.get("word", "").strip().lower()
    if not word:
        return jsonify({"error": "word required"}), 400

    if not BlockedWord.query.filter_by(word=word).first():
        db.session.add(BlockedWord(word=word))
        db.session.commit()
        _PUZZLE_CACHE.clear()

    return jsonify({"word": word, "blocked": True})
