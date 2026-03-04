from collections import Counter
from datetime import date, datetime, timedelta, timezone
from flask import jsonify, request, session
from flask_login import current_user, login_required
import hashlib
import os

from app import app
from app.models import db, BlockedWord, BeeConfig, BeeAchievement, PageView

_WORDLIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'kotus_words.txt')
try:
    with open(_WORDLIST_PATH, encoding='utf-8') as _f:
        # Normalise hyphenated compounds (e.g. lähi-itä → lähiitä) so they are
        # valid puzzle words; the frozenset also deduplicates any collisions.
        _ALL_WORDS = frozenset(line.strip().replace('-', '') for line in _f if line.strip())
except FileNotFoundError:
    _ALL_WORDS = frozenset()

# Each puzzle is a flat set of 7 letters (sorted).  The center letter for each
# puzzle is stored in the BeeConfig table (key = "center_{idx}").
PUZZLES = [
    {"letters": ["e", "n", "p", "r", "s", "y", "ä"]},       # 1
    {"letters": ["d", "e", "h", "l", "r", "s", "ä"]},       # 2
    {"letters": ["j", "k", "n", "o", "p", "r", "u"]},       # 3
    {"letters": ["e", "h", "i", "m", "n", "y", "ä"]},       # 4
    {"letters": ["e", "l", "m", "n", "o", "s", "u"]},       # 5
    {"letters": ["k", "l", "o", "s", "u", "y", "ä"]},       # 6
    {"letters": ["d", "e", "h", "p", "s", "u", "ä"]},       # 7
    {"letters": ["a", "h", "k", "l", "m", "n", "s"]},       # 8
    {"letters": ["a", "d", "e", "g", "i", "o", "p"]},       # 9
    {"letters": ["e", "i", "l", "m", "n", "r", "v"]},       # 10
    {"letters": ["e", "h", "k", "r", "s", "t", "u"]},       # 11
    {"letters": ["d", "e", "h", "k", "l", "t", "ä"]},       # 12
    {"letters": ["a", "p", "r", "u", "y", "ä", "ö"]},       # 13
    {"letters": ["a", "d", "i", "n", "o", "t", "u"]},       # 14
    {"letters": ["j", "k", "n", "s", "t", "ä", "ö"]},       # 15
    {"letters": ["e", "h", "i", "l", "m", "s", "y"]},       # 16
    {"letters": ["a", "e", "h", "i", "r", "u", "v"]},       # 17
    {"letters": ["d", "e", "i", "l", "n", "s", "v"]},       # 18
    {"letters": ["e", "h", "i", "n", "t", "y", "ö"]},       # 19
    {"letters": ["a", "d", "h", "i", "m", "o", "u"]},       # 20
    {"letters": ["a", "d", "e", "i", "l", "n", "u"]},       # 21
    {"letters": ["d", "h", "j", "r", "s", "y", "ä"]},       # 22
    {"letters": ["a", "e", "h", "l", "s", "t", "v"]},       # 23
    {"letters": ["e", "i", "k", "l", "t", "v", "y"]},       # 24
    {"letters": ["e", "h", "m", "n", "o", "p", "r"]},       # 25
    {"letters": ["a", "e", "j", "o", "t", "u", "ä"]},       # 26
    {"letters": ["a", "e", "j", "l", "n", "o", "u"]},       # 27
    {"letters": ["e", "k", "l", "n", "s", "ä", "ö"]},       # 28
    {"letters": ["e", "i", "l", "m", "p", "u", "ä"]},       # 29
    {"letters": ["i", "l", "p", "s", "v", "y", "ä"]},       # 30
    {"letters": ["h", "i", "r", "s", "t", "v", "ä"]},       # 31
    {"letters": ["i", "k", "t", "v", "y", "ä", "ö"]},       # 32
    {"letters": ["i", "m", "n", "t", "y", "ä", "ö"]},       # 33
    {"letters": ["a", "d", "h", "m", "n", "o", "t"]},       # 34
    {"letters": ["a", "h", "i", "n", "r", "u", "ä"]},       # 35
    {"letters": ["m", "n", "o", "s", "t", "u", "ä"]},       # 36
    {"letters": ["a", "b", "d", "i", "k", "o", "r"]},       # 37
    {"letters": ["h", "i", "k", "m", "s", "v", "y"]},       # 38
    {"letters": ["a", "e", "g", "h", "r", "t", "y"]},       # 39
    {"letters": ["a", "d", "h", "i", "j", "o", "p"]},       # 40
    {"letters": ["e", "i", "l", "n", "v", "y", "ö"]},       # 41
]

# Original center letters from the old format — used to seed BeeConfig on first run.
_DEFAULT_CENTERS = [
    "r", "ä", "n", "n", "l", "y", "h", "h", "p", "v",
    "s", "h", "p", "d", "j", "y", "u", "d", "n", "o",
    "d", "y", "h", "y", "e", "e", "u", "s", "u", "p",
    "v", "i", "m", "t", "i", "s", "o", "i", "t", "o",
    "n",
]


def _seed_centers():
    """Seed BeeConfig with default center letters if not yet migrated."""
    if BeeConfig.query.filter_by(key="center_0").first():
        return  # already seeded
    for idx, center in enumerate(_DEFAULT_CENTERS):
        db.session.add(BeeConfig(key=f"center_{idx}", value=center))
    db.session.commit()


def _get_center(idx):
    """Read the chosen center letter for puzzle *idx* from BeeConfig."""
    row = BeeConfig.query.filter_by(key=f"center_{idx}").first()
    if row:
        return row.value
    # Fallback: first letter alphabetically
    return sorted(PUZZLES[idx]["letters"])[0]


def _get_puzzle_dict(idx):
    """Build a classic {center, outer} dict for puzzle *idx*."""
    letters = PUZZLES[idx]["letters"]
    center = _get_center(idx)
    outer = [l for l in letters if l != center]
    return {"center": center, "outer": outer}


def _score_word(word, all_letters_frozenset):
    pts = 1 if len(word) == 4 else len(word)
    if all_letters_frozenset.issubset(set(word)):
        pts += 7
    return pts


def _hash_word(word):
    return hashlib.sha256(word.encode()).hexdigest()


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
    pangram_count = 0
    by_letter = Counter()
    by_length = Counter()
    by_pair = Counter()
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
            if letter_frozenset.issubset(set(word)):
                pangram_count += 1
            by_letter[word[0]] += 1
            by_length[len(word)] += 1
            by_pair[word[:2]] += 1

    sorted_words = sorted(words)
    word_hashes = [_hash_word(w) for w in sorted_words]
    hint_data = {
        "word_count": len(sorted_words),
        "pangram_count": pangram_count,
        "by_letter": dict(by_letter),
        "by_length": {str(k): v for k, v in by_length.items()},
        "by_pair": dict(by_pair),
    }

    return sorted_words, max_score, word_hashes, hint_data


_PUZZLE_CACHE: dict = {}  # Cleared on container restart or when words are blocked


def _get_puzzle_data(idx):
    if idx not in _PUZZLE_CACHE:
        _PUZZLE_CACHE[idx] = _compute_puzzle(_get_puzzle_dict(idx))
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


def _compute_variation(letters, center_letter):
    """Compute stats for a single center-letter variation (no DB access for blocked words)."""
    all_letters = set(letters)
    letter_frozenset = frozenset(all_letters)

    try:
        blocked = frozenset(bw.word for bw in BlockedWord.query.all())
    except Exception:
        blocked = frozenset()

    words = []
    max_score = 0
    pangram_count = 0
    for word in _ALL_WORDS:
        if word in blocked:
            continue
        if (
            len(word) >= 4
            and center_letter in word
            and all(c in all_letters for c in word)
        ):
            words.append(word)
            word_score = _score_word(word, letter_frozenset)
            max_score += word_score
            if letter_frozenset.issubset(set(word)):
                pangram_count += 1

    return {
        "center": center_letter,
        "word_count": len(words),
        "max_score": max_score,
        "pangram_count": pangram_count,
    }


@app.route("/api/kenno")
def kenno():
    puzzle_number = _get_puzzle_for_date(date.today())

    is_admin = (
        current_user.is_authenticated
        and getattr(current_user, "role", None) == "admin"
    )

    override = request.args.get("puzzle", type=int)
    if override is not None and is_admin:
        puzzle_number = override % len(PUZZLES)

    puzzle = _get_puzzle_dict(puzzle_number)
    words, max_score, word_hashes, hint_data = _get_puzzle_data(puzzle_number)

    result = {
        "center": puzzle["center"],
        "letters": puzzle["outer"],
        "word_hashes": word_hashes,
        "hint_data": hint_data,
        "max_score": max_score,
        "puzzle_number": puzzle_number,
        "total_puzzles": len(PUZZLES),
    }

    if is_admin:
        result["words"] = words

    return jsonify(result)


@app.route("/api/kenno/block", methods=["POST"])
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


@app.route("/api/kenno/variations")
@login_required
def bee_variations():
    """Return all 7 center-letter variations for a puzzle (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    puzzle_idx = request.args.get("puzzle", type=int)
    if puzzle_idx is None:
        return jsonify({"error": "puzzle parameter required"}), 400
    puzzle_idx = puzzle_idx % len(PUZZLES)

    letters = PUZZLES[puzzle_idx]["letters"]
    active_center = _get_center(puzzle_idx)

    variations = []
    for letter in sorted(letters):
        stats = _compute_variation(letters, letter)
        stats["is_active"] = (letter == active_center)
        variations.append(stats)

    return jsonify({
        "puzzle": puzzle_idx,
        "variations": variations,
    })


@app.route("/api/kenno/center", methods=["POST"])
@login_required
def bee_set_center():
    """Set the center letter for a puzzle (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    puzzle_idx = data.get("puzzle")
    center = data.get("center", "").strip().lower()

    if puzzle_idx is None or not isinstance(puzzle_idx, int):
        return jsonify({"error": "puzzle (int) required"}), 400
    puzzle_idx = puzzle_idx % len(PUZZLES)

    letters = PUZZLES[puzzle_idx]["letters"]
    if center not in letters:
        return jsonify({"error": f"'{center}' is not one of the 7 letters"}), 400

    key = f"center_{puzzle_idx}"
    row = BeeConfig.query.filter_by(key=key).first()
    if row:
        row.value = center
    else:
        db.session.add(BeeConfig(key=key, value=center))
    db.session.commit()

    # Clear cached data for this puzzle so the next request uses the new center
    _PUZZLE_CACHE.pop(puzzle_idx, None)

    return jsonify({"puzzle": puzzle_idx, "center": center})


@app.route("/api/kenno/stats")
@login_required
def bee_stats():
    """Sanakenno overview stats (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    sanakenno_pv = db.session.query(PageView).filter_by(path="/sanakenno").first()
    page_views = sanakenno_pv.count if sanakenno_pv else 0
    blocked_words_count = db.session.query(BlockedWord).count()
    total_puzzles = len(PUZZLES)

    return jsonify({
        "page_views": page_views,
        "blocked_words_count": blocked_words_count,
        "total_puzzles": total_puzzles,
    })


@app.route("/api/kenno/blocked")
@login_required
def bee_blocked_list():
    """List all blocked words with timestamps (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    words = db.session.query(BlockedWord).order_by(BlockedWord.blocked_at.desc()).all()
    return jsonify([
        {
            "id": bw.id,
            "word": bw.word,
            "blocked_at": bw.blocked_at.isoformat() + "Z" if bw.blocked_at else None,
        }
        for bw in words
    ])


VALID_RANKS = [
    "Etsi sanoja!", "Hyvä alku", "Nyt mennään!",
    "Onnistuja", "Sanavalmis", "Ällistyttävä", "Täysi kenno",
]


@app.route("/api/kenno/achievement", methods=["POST"])
def bee_achievement():
    """Record an anonymous rank achievement (session-deduped)."""
    data = request.get_json() or {}

    rank = data.get("rank")
    if rank not in VALID_RANKS:
        return jsonify({"error": "Invalid rank"}), 400

    puzzle_number = data.get("puzzle_number")
    if not isinstance(puzzle_number, int) or puzzle_number < 0 or puzzle_number >= len(PUZZLES):
        return jsonify({"error": "Invalid puzzle_number"}), 400

    score_val = data.get("score")
    max_score_val = data.get("max_score")
    words_found = data.get("words_found")
    if (
        not isinstance(score_val, int) or score_val < 0
        or not isinstance(max_score_val, int) or max_score_val <= 0
        or not isinstance(words_found, int) or words_found < 0
    ):
        return jsonify({"error": "Invalid score, max_score, or words_found"}), 400

    elapsed_ms = data.get("elapsed_ms")
    if elapsed_ms is not None and (not isinstance(elapsed_ms, int) or elapsed_ms < 0):
        return jsonify({"error": "Invalid elapsed_ms"}), 400

    # Session dedup: one record per puzzle+rank per session
    achieved_key = f"{puzzle_number}:{rank}"
    achieved_ranks = session.get("achieved_ranks", [])
    if achieved_key in achieved_ranks:
        return jsonify({"status": "already_recorded"}), 200

    achievement = BeeAchievement(
        puzzle_number=puzzle_number,
        rank=rank,
        score=score_val,
        max_score=max_score_val,
        words_found=words_found,
        elapsed_ms=elapsed_ms,
    )
    db.session.add(achievement)
    db.session.commit()

    achieved_ranks.append(achieved_key)
    session["achieved_ranks"] = achieved_ranks

    return jsonify({"status": "recorded"}), 201


@app.route("/api/kenno/achievements")
@login_required
def bee_achievements():
    """Daily achievement summary (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    days = request.args.get("days", 30, type=int)
    days = max(1, min(90, days))

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    rows = (
        db.session.query(
            db.func.date(BeeAchievement.achieved_at),
            BeeAchievement.rank,
            db.func.count(),
        )
        .filter(BeeAchievement.achieved_at >= start)
        .group_by(db.func.date(BeeAchievement.achieved_at), BeeAchievement.rank)
        .all()
    )

    # Build lookup: date_str -> rank -> count
    lookup = {}
    for date_str, rank, count in rows:
        lookup.setdefault(str(date_str), {})[rank] = count

    # Fill all dates in range
    daily = []
    totals = {r: 0 for r in VALID_RANKS}
    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        day_counts = {r: lookup.get(d, {}).get(r, 0) for r in VALID_RANKS}
        day_total = sum(day_counts.values())
        daily.append({"date": d, "counts": day_counts, "total": day_total})
        for r in VALID_RANKS:
            totals[r] += day_counts[r]

    return jsonify({"days": days, "daily": daily, "totals": totals})


@app.route("/api/kenno/block/<int:word_id>", methods=["DELETE"])
@login_required
def bee_unblock_word(word_id):
    """Unblock a word by ID (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    bw = db.session.get(BlockedWord, word_id)
    if not bw:
        return jsonify({"error": "Blocked word not found"}), 404

    word = bw.word
    db.session.delete(bw)
    db.session.commit()
    _PUZZLE_CACHE.clear()

    return jsonify({"word": word, "unblocked": True})
