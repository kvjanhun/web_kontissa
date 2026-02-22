from datetime import date
from flask import jsonify
import os

from app import app

_WORDLIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'kotus_words.txt')
try:
    with open(_WORDLIST_PATH, encoding='utf-8') as _f:
        _ALL_WORDS = frozenset(line.strip() for line in _f if line.strip())
except FileNotFoundError:
    _ALL_WORDS = frozenset()

PUZZLES = [
    {"center": "a", "outer": ["k", "l", "u", "s", "n", "t"]},
    {"center": "i", "outer": ["n", "e", "t", "a", "s", "o"]},
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

    words = []
    max_score = 0
    for word in _ALL_WORDS:
        if (
            len(word) >= 4
            and center in word
            and all(c in all_letters for c in word)
        ):
            words.append(word)
            max_score += _score_word(word, letter_frozenset)

    return sorted(words), max_score


_PUZZLE_CACHE: dict = {}


def _get_puzzle_data(idx):
    if idx not in _PUZZLE_CACHE:
        _PUZZLE_CACHE[idx] = _compute_puzzle(PUZZLES[idx])
    return _PUZZLE_CACHE[idx]


@app.route("/api/bee")
def bee():
    puzzle_number = date.today().toordinal() % len(PUZZLES)
    puzzle = PUZZLES[puzzle_number]
    words, max_score = _get_puzzle_data(puzzle_number)

    return jsonify(
        {
            "center": puzzle["center"],
            "letters": puzzle["outer"],
            "words": words,
            "max_score": max_score,
            "puzzle_number": puzzle_number,
        }
    )
