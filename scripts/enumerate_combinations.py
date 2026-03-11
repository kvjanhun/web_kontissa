#!/usr/bin/env python3
"""Enumerate all 7-letter combinations from the Kotus word list that have at
least one pangram, and seed them into the bee_combinations table.

For each combination, compute per-center stats: word_count, pangram_count,
max_score.  Also marks combinations that are already in the puzzle rotation.

Usage:
    DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 scripts/enumerate_combinations.py

Options:
    --wordlist PATH     Path to kotus_words.txt
                        (default: app/wordlists/kotus_words.txt)
    --json PATH         Also write a JSON file (optional, for debugging)
    --min-pangrams N    Only include combinations with >= N total pangrams (default: 1)
    --min-words N       Only include combinations whose best center has >= N words (default: 1)
    --quiet             Suppress progress output
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

DEFAULT_WORDLIST = os.path.join(REPO_ROOT, "app", "wordlists", "kotus_words.txt")

_db_candidates = [
    os.path.join(REPO_ROOT, "app", "data", "site.db"),  # local dev
    os.path.join(REPO_ROOT, "data", "site.db"),          # inside container (WORKDIR=/app)
]
_db_path = next((p for p in _db_candidates if os.path.exists(os.path.dirname(p))), _db_candidates[0])
os.environ.setdefault("DATABASE_URI", f"sqlite:///{_db_path}")


def load_words(path):
    """Load and normalise words (strip hyphens, same as kenno.py)."""
    with open(path, encoding="utf-8") as f:
        return frozenset(
            line.strip().replace("-", "")
            for line in f
            if line.strip()
        )


def score_word(word, letter_frozenset):
    """Scoring rule identical to kenno.py._score_word."""
    pts = 1 if len(word) == 4 else len(word)
    if letter_frozenset.issubset(set(word)):
        pts += 7
    return pts


def build_word_groups(words):
    """Group words by their frozenset of unique letters."""
    groups = defaultdict(list)
    for word in words:
        groups[frozenset(word)].append(word)
    return groups


def compute_variation(center, combination_fs, relevant_words):
    """Compute stats for one center-letter variation."""
    word_count = 0
    pangram_count = 0
    max_score = 0

    for word in relevant_words:
        if center not in word:
            continue
        word_count += 1
        pts = score_word(word, combination_fs)
        max_score += pts
        if combination_fs.issubset(set(word)):
            pangram_count += 1

    return {
        "center": center,
        "word_count": word_count,
        "pangram_count": pangram_count,
        "max_score": max_score,
    }


def enumerate_combinations(words, min_pangrams=1, min_words=1, quiet=False):
    """Return list of combination dicts."""
    t0 = time.time()

    if not quiet:
        print(f"Loaded {len(words):,} words.", flush=True)

    groups = build_word_groups(words)

    if not quiet:
        print(f"Distinct unique-letter sets: {len(groups):,}", flush=True)

    candidate_keys = [k for k in groups if len(k) == 7]

    if not quiet:
        print(f"Candidate 7-letter combinations: {len(candidate_keys):,}", flush=True)

    all_groups_items = list(groups.items())

    results = []
    for i, combo_fs in enumerate(candidate_keys):
        if not quiet and (i % 200 == 0 or i == len(candidate_keys) - 1):
            elapsed = time.time() - t0
            pct = (i + 1) / len(candidate_keys) * 100
            print(f"  [{pct:5.1f}%] {i+1}/{len(candidate_keys)}  ({elapsed:.1f}s)", flush=True)

        relevant_words = []
        for key, wlist in all_groups_items:
            if key <= combo_fs:
                relevant_words.extend(wlist)

        total_pangrams = len(groups[combo_fs])

        if total_pangrams < min_pangrams:
            continue

        letters_sorted = sorted(combo_fs)
        variations = [
            compute_variation(c, combo_fs, relevant_words)
            for c in letters_sorted
        ]

        word_counts = [v["word_count"] for v in variations]
        max_scores = [v["max_score"] for v in variations]
        max_word_count = max(word_counts)
        min_word_count = min(word_counts)

        if max_word_count < min_words:
            continue

        results.append({
            "letters": "".join(letters_sorted),
            "total_pangrams": total_pangrams,
            "min_word_count": min_word_count,
            "max_word_count": max_word_count,
            "min_max_score": min(max_scores),
            "max_max_score": max(max_scores),
            "variations": variations,
        })

    results.sort(key=lambda r: (-r["total_pangrams"], -r["max_word_count"]))
    return results


def seed_database(results):
    """Write combinations to the bee_combinations table."""
    from app import app
    from app.models import db, KennoCombination, KennoPuzzle

    with app.app_context():
        db.create_all()

        # Build set of letter combos currently in the puzzle rotation
        rotation_letters = set()
        for puzzle in KennoPuzzle.query.all():
            letters_sorted = "".join(sorted(puzzle.letters.split(",")))
            rotation_letters.add(letters_sorted)

        # Clear and re-seed (full replace is simpler and this runs rarely)
        KennoCombination.query.delete()

        batch = []
        for r in results:
            batch.append(KennoCombination(
                letters=r["letters"],
                total_pangrams=r["total_pangrams"],
                min_word_count=r["min_word_count"],
                max_word_count=r["max_word_count"],
                min_max_score=r["min_max_score"],
                max_max_score=r["max_max_score"],
                variations=json.dumps(r["variations"], ensure_ascii=False),
                in_rotation=r["letters"] in rotation_letters,
            ))

        db.session.add_all(batch)
        db.session.commit()

        in_rotation_count = sum(1 for r in results if r["letters"] in rotation_letters)
        print(f"\n  Seeded {len(batch):,} rows into bee_combinations.")
        print(f"  {in_rotation_count} marked as in_rotation (of {len(rotation_letters)} puzzle slots).")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wordlist", default=DEFAULT_WORDLIST,
                        help="Path to kotus_words.txt")
    parser.add_argument("--json", default=None, metavar="PATH",
                        help="Also write a JSON file (optional)")
    parser.add_argument("--min-pangrams", type=int, default=1, metavar="N",
                        help="Minimum total pangrams (default: 1)")
    parser.add_argument("--min-words", type=int, default=1, metavar="N",
                        help="Minimum best-center word count (default: 1)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress progress output")
    args = parser.parse_args()

    if not os.path.exists(args.wordlist):
        print(f"Error: word list not found at {args.wordlist}", file=sys.stderr)
        print("Run scripts/process_kotus.py first.", file=sys.stderr)
        sys.exit(1)

    words = load_words(args.wordlist)
    results = enumerate_combinations(
        words,
        min_pangrams=args.min_pangrams,
        min_words=args.min_words,
        quiet=args.quiet,
    )

    print(f"\nDone enumerating: {len(results):,} combinations found.")

    seed_database(results)

    if args.json:
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "word_list_size": len(words),
            "total_combinations": len(results),
            "combinations": results,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  JSON written to {args.json} ({os.path.getsize(args.json) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
