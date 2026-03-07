#!/usr/bin/env python3
"""Show all 7 center-letter variations for a Sanakenno puzzle.

Usage:
    python3 scripts/puzzle_variations.py [N]

N is 1-indexed (matches the admin UI "Peli N/41").  If omitted, shows all puzzles.
"""
import os
import sys

# Ensure the project root is on the path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URI", f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'app', 'data', 'site.db')}")

from app import app
from app.api.kenno import PUZZLES, _get_center, _compute_variation


def show_puzzle(idx):
    """Print a variation table for puzzle *idx* (0-indexed)."""
    letters = PUZZLES[idx]["letters"]
    active_center = _get_center(idx)

    variations = []
    for letter in letters:
        stats = _compute_variation(letters, letter)
        variations.append(stats)

    # Sort by max_score descending
    variations.sort(key=lambda v: v["max_score"], reverse=True)

    print(f"\n--- Puzzle {idx + 1}/{len(PUZZLES)} --- letters: {' '.join(sorted(letters))}")
    print(f"{'Center':>8}  {'Words':>6}  {'Score':>6}  {'Pangrams':>8}  ")
    print(f"{'------':>8}  {'-----':>6}  {'-----':>6}  {'--------':>8}  ")
    for v in variations:
        marker = " <--" if v["center"] == active_center else ""
        print(
            f"{v['center'].upper():>8}  "
            f"{v['word_count']:>6}  "
            f"{v['max_score']:>6}  "
            f"{v['pangram_count']:>8}  "
            f"{marker}"
        )


def main():
    with app.app_context():
        if len(sys.argv) > 1:
            try:
                display_num = int(sys.argv[1])
            except ValueError:
                print(f"Error: '{sys.argv[1]}' is not a valid puzzle number", file=sys.stderr)
                sys.exit(1)
            if display_num < 1 or display_num > len(PUZZLES):
                print(f"Error: puzzle number must be between 1 and {len(PUZZLES)}", file=sys.stderr)
                sys.exit(1)
            show_puzzle(display_num - 1)
        else:
            for idx in range(len(PUZZLES)):
                show_puzzle(idx)


if __name__ == "__main__":
    main()
