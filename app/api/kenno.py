from collections import Counter
from datetime import date, datetime, timedelta, timezone
import zoneinfo
from flask import jsonify, request, session
from flask_login import current_user, login_required
import hashlib
import os

from app import app, limiter
from app.models import db, BlockedWord, KennoConfig, KennoAchievement, KennoPuzzle, PageView

_WORDLIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'kotus_words.txt')
try:
    with open(_WORDLIST_PATH, encoding='utf-8') as _f:
        # Normalise hyphenated compounds (e.g. lähi-itä → lähiitä) so they are
        # valid puzzle words; the frozenset also deduplicates any collisions.
        _ALL_WORDS = frozenset(line.strip().replace('-', '') for line in _f if line.strip())
except FileNotFoundError:
    _ALL_WORDS = frozenset()

# Each puzzle is a flat set of 7 letters (sorted).  The center letter for each
# puzzle is stored in the KennoConfig table (key = "center_{idx}").
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

# Original center letters from the old format — used to seed KennoConfig on first run.
_DEFAULT_CENTERS = [
    "r", "ä", "n", "n", "l", "y", "h", "h", "p", "v",
    "s", "h", "p", "d", "j", "y", "u", "d", "n", "o",
    "d", "y", "h", "y", "e", "e", "u", "s", "u", "p",
    "v", "i", "m", "t", "i", "s", "o", "i", "t", "o",
    "n",
]


def _seed_centers():
    """Seed KennoConfig with default center letters if not yet migrated."""
    if KennoConfig.query.filter_by(key="center_0").first():
        return  # already seeded
    for idx, center in enumerate(_DEFAULT_CENTERS):
        db.session.add(KennoConfig(key=f"center_{idx}", value=center))
    db.session.commit()


def _get_puzzle_letters(idx):
    """Return the 7 letters for puzzle *idx*, checking DB first, then PUZZLES."""
    row = KennoPuzzle.query.filter_by(slot=idx).first()
    if row:
        return row.letters.split(",")
    if 0 <= idx < len(PUZZLES):
        return PUZZLES[idx]["letters"]
    return None


def _total_puzzles():
    """Return the total number of puzzle slots (hardcoded + any DB extensions)."""
    highest_db = db.session.query(db.func.max(KennoPuzzle.slot)).scalar()
    if highest_db is not None:
        return max(len(PUZZLES), highest_db + 1)
    return len(PUZZLES)


def _get_center(idx):
    """Read the chosen center letter for puzzle *idx* from KennoConfig."""
    row = KennoConfig.query.filter_by(key=f"center_{idx}").first()
    if row:
        return row.value
    # Fallback: first letter alphabetically
    letters = _get_puzzle_letters(idx)
    if letters:
        return sorted(letters)[0]
    return sorted(PUZZLES[idx]["letters"])[0]


def _get_puzzle_dict(idx):
    """Build a classic {center, outer} dict for puzzle *idx*."""
    letters = _get_puzzle_letters(idx)
    if letters is None:
        return None
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
    return (START_INDEX + days_since_start) % _total_puzzles()


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


_HELSINKI = zoneinfo.ZoneInfo("Europe/Helsinki")


@app.route("/api/kenno")
def kenno():
    puzzle_number = _get_puzzle_for_date(datetime.now(_HELSINKI).date())

    is_admin = (
        current_user.is_authenticated
        and getattr(current_user, "role", None) == "admin"
    )

    override = request.args.get("puzzle", type=int)
    if override is not None and is_admin:
        puzzle_number = override % _total_puzzles()

    puzzle = _get_puzzle_dict(puzzle_number)
    words, max_score, word_hashes, hint_data = _get_puzzle_data(puzzle_number)

    result = {
        "center": puzzle["center"],
        "letters": puzzle["outer"],
        "word_hashes": word_hashes,
        "hint_data": hint_data,
        "max_score": max_score,
        "puzzle_number": puzzle_number,
        "total_puzzles": _total_puzzles(),
    }

    if is_admin:
        result["words"] = words

    return jsonify(result)


@app.route("/api/kenno/block", methods=["POST"])
@login_required
def kenno_block_word():
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
def kenno_variations():
    """Return all 7 center-letter variations for a puzzle (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    puzzle_idx = request.args.get("puzzle", type=int)
    if puzzle_idx is None:
        return jsonify({"error": "puzzle parameter required"}), 400
    puzzle_idx = puzzle_idx % _total_puzzles()

    letters = _get_puzzle_letters(puzzle_idx)
    if letters is None:
        return jsonify({"error": "Puzzle not found"}), 404
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
def kenno_set_center():
    """Set the center letter for a puzzle (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    puzzle_idx = data.get("puzzle")
    center = data.get("center", "").strip().lower()

    if puzzle_idx is None or not isinstance(puzzle_idx, int):
        return jsonify({"error": "puzzle (int) required"}), 400
    puzzle_idx = puzzle_idx % _total_puzzles()

    letters = _get_puzzle_letters(puzzle_idx)
    if letters is None:
        return jsonify({"error": "Puzzle not found"}), 404
    if center not in letters:
        return jsonify({"error": f"'{center}' is not one of the 7 letters"}), 400

    key = f"center_{puzzle_idx}"
    row = KennoConfig.query.filter_by(key=key).first()
    if row:
        row.value = center
    else:
        db.session.add(KennoConfig(key=key, value=center))
    db.session.commit()

    # Clear cached data for this puzzle so the next request uses the new center
    _PUZZLE_CACHE.pop(puzzle_idx, None)

    return jsonify({"puzzle": puzzle_idx, "center": center})


@app.route("/api/kenno/stats")
@login_required
def kenno_stats():
    """Sanakenno overview stats (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    sanakenno_pv = db.session.query(PageView).filter_by(path="/sanakenno").first()
    page_views = sanakenno_pv.count if sanakenno_pv else 0
    blocked_words_count = db.session.query(BlockedWord).count()
    total_puzzles = _total_puzzles()

    return jsonify({
        "page_views": page_views,
        "blocked_words_count": blocked_words_count,
        "total_puzzles": total_puzzles,
    })


@app.route("/api/kenno/blocked")
@login_required
def kenno_blocked_list():
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
@limiter.limit("10/minute")
def kenno_achievement():
    """Record an anonymous rank achievement (session-deduped)."""
    data = request.get_json() or {}

    rank = data.get("rank")
    if rank not in VALID_RANKS:
        return jsonify({"error": "Invalid rank"}), 400

    puzzle_number = data.get("puzzle_number")
    if not isinstance(puzzle_number, int) or puzzle_number < 0 or puzzle_number >= _total_puzzles():
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

    achievement = KennoAchievement(
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
def kenno_achievements():
    """Daily achievement summary (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    days = request.args.get("days", 30, type=int)
    days = max(1, min(90, days))

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    rows = (
        db.session.query(
            db.func.date(KennoAchievement.achieved_at),
            KennoAchievement.rank,
            db.func.count(),
        )
        .filter(KennoAchievement.achieved_at >= start)
        .group_by(db.func.date(KennoAchievement.achieved_at), KennoAchievement.rank)
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
def kenno_unblock_word(word_id):
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


# Valid Finnish alphabet letters for puzzle creation
_FINNISH_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyzäö")


def _validate_puzzle_letters(letters):
    """Validate a list of 7 puzzle letters. Returns (cleaned list, error string or None)."""
    if not isinstance(letters, list) or len(letters) != 7:
        return None, "Exactly 7 letters required"
    cleaned = [l.strip().lower() for l in letters if isinstance(l, str)]
    if len(cleaned) != 7:
        return None, "All letters must be strings"
    if len(set(cleaned)) != 7:
        return None, "All 7 letters must be distinct"
    for l in cleaned:
        if len(l) != 1 or l not in _FINNISH_LETTERS:
            return None, f"Invalid letter: '{l}'"
    return sorted(cleaned), None


@app.route("/api/kenno/preview", methods=["POST"])
@login_required
@limiter.limit("20/minute")
def kenno_preview():
    """Preview all 7 center-letter variations for arbitrary letters (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    letters, err = _validate_puzzle_letters(data.get("letters", []))
    if err:
        return jsonify({"error": err}), 400

    variations = []
    for letter in letters:
        stats = _compute_variation(letters, letter)
        variations.append(stats)

    result = {"letters": letters, "variations": variations}

    # If a center letter is specified, also return the word list for that variation
    center = data.get("center", "").strip().lower()
    if center and center in letters:
        puzzle = {"center": center, "outer": [l for l in letters if l != center]}
        words, max_score, _hashes, _hints = _compute_puzzle(puzzle)
        result["words"] = words
        result["center"] = center

    return jsonify(result)


@app.route("/api/kenno/puzzle", methods=["POST"])
@login_required
def kenno_save_puzzle():
    """Create or update a custom puzzle in a slot (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}

    slot = data.get("slot")
    if not isinstance(slot, int) or slot < 0:
        return jsonify({"error": "slot must be a non-negative integer"}), 400

    letters, err = _validate_puzzle_letters(data.get("letters", []))
    if err:
        return jsonify({"error": err}), 400

    center = data.get("center", "").strip().lower()
    if center not in letters:
        return jsonify({"error": f"center '{center}' must be one of the 7 letters"}), 400

    # Safety: reject writes to today's live slot
    today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
    if slot == today_slot:
        return jsonify({"error": "Cannot modify today's live puzzle"}), 409

    # Upsert KennoPuzzle row
    now = datetime.now(timezone.utc)
    row = db.session.get(KennoPuzzle, slot)
    is_new_slot = row is None and slot >= len(PUZZLES)
    if row:
        row.letters = ",".join(letters)
        row.updated_at = now
    else:
        row = KennoPuzzle(slot=slot, letters=",".join(letters), created_at=now, updated_at=now)
        db.session.add(row)

    # Upsert KennoConfig center entry
    key = f"center_{slot}"
    config_row = KennoConfig.query.filter_by(key=key).first()
    if config_row:
        config_row.value = center
    else:
        db.session.add(KennoConfig(key=key, value=center))

    db.session.commit()
    _PUZZLE_CACHE.pop(slot, None)

    # Compute next play date for this slot
    next_play_date = _next_play_date_for_slot(slot)

    return jsonify({
        "slot": slot,
        "letters": letters,
        "center": center,
        "is_new_slot": is_new_slot,
        "next_play_date": next_play_date.isoformat() if next_play_date else None,
    })


def _next_play_date_for_slot(slot):
    """Find the next date (from tomorrow onward) when the given slot will be live."""
    today = datetime.now(_HELSINKI).date()
    total = _total_puzzles()
    if total == 0:
        return None
    for day_offset in range(1, total + 1):
        d = today + timedelta(days=day_offset)
        if _get_puzzle_for_date(d) == slot:
            return d
    return None


@app.route("/api/kenno/schedule")
@login_required
def kenno_schedule():
    """Return upcoming puzzle rotation schedule (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    days = request.args.get("days", 14, type=int)
    days = max(1, min(90, days))

    today = datetime.now(_HELSINKI).date()
    today_slot = _get_puzzle_for_date(today)
    total = _total_puzzles()

    schedule = []
    for i in range(days):
        d = today + timedelta(days=i)
        slot = _get_puzzle_for_date(d)
        is_custom = KennoPuzzle.query.filter_by(slot=slot).first() is not None
        schedule.append({
            "date": d.isoformat(),
            "slot": slot,
            "display_number": slot + 1,
            "is_custom": is_custom,
            "is_today": (i == 0),
        })

    return jsonify({
        "schedule": schedule,
        "total_puzzles": total,
    })


@app.route("/api/kenno/puzzle/swap", methods=["POST"])
@login_required
def kenno_swap_puzzles():
    """Swap two puzzle slots (admin only). Swaps both letters and center."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json() or {}
    slot_a = data.get("slot_a")
    slot_b = data.get("slot_b")

    if not isinstance(slot_a, int) or not isinstance(slot_b, int):
        return jsonify({"error": "slot_a and slot_b must be integers"}), 400
    if slot_a < 0 or slot_b < 0:
        return jsonify({"error": "Slots must be non-negative"}), 400
    if slot_a == slot_b:
        return jsonify({"error": "Slots must be different"}), 400

    total = _total_puzzles()
    if slot_a >= total or slot_b >= total:
        return jsonify({"error": "Slot out of range"}), 400

    today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
    if slot_a == today_slot or slot_b == today_slot:
        return jsonify({"error": "Cannot swap today's live puzzle"}), 409

    # Read current state for both slots
    letters_a = _get_puzzle_letters(slot_a)
    letters_b = _get_puzzle_letters(slot_b)
    center_a = _get_center(slot_a)
    center_b = _get_center(slot_b)

    now = datetime.now(timezone.utc)

    # Write slot_a ← old slot_b data
    _upsert_puzzle_slot(slot_a, letters_b, center_b, now)
    # Write slot_b ← old slot_a data
    _upsert_puzzle_slot(slot_b, letters_a, center_a, now)

    db.session.commit()
    _PUZZLE_CACHE.pop(slot_a, None)
    _PUZZLE_CACHE.pop(slot_b, None)

    return jsonify({"slot_a": slot_a, "slot_b": slot_b, "swapped": True})


def _upsert_puzzle_slot(slot, letters, center, now):
    """Write letters and center for a slot (KennoPuzzle + KennoConfig)."""
    row = db.session.get(KennoPuzzle, slot)
    letters_csv = ",".join(letters)
    if row:
        row.letters = letters_csv
        row.updated_at = now
    else:
        db.session.add(KennoPuzzle(slot=slot, letters=letters_csv, created_at=now, updated_at=now))

    key = f"center_{slot}"
    config_row = KennoConfig.query.filter_by(key=key).first()
    if config_row:
        config_row.value = center
    else:
        db.session.add(KennoConfig(key=key, value=center))


@app.route("/api/kenno/puzzle/<int:slot>", methods=["DELETE"])
@login_required
def kenno_delete_puzzle(slot):
    """Delete a custom puzzle, reverting to hardcoded if available (admin only)."""
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403

    today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
    if slot == today_slot:
        return jsonify({"error": "Cannot delete today's live puzzle"}), 409

    row = db.session.get(KennoPuzzle, slot)
    if not row:
        return jsonify({"error": "No custom puzzle in this slot"}), 404

    has_hardcoded = 0 <= slot < len(PUZZLES)
    db.session.delete(row)

    config_row = KennoConfig.query.filter_by(key=f"center_{slot}").first()
    if has_hardcoded:
        # Reset center to the seeded default for the hardcoded puzzle
        default_center = _DEFAULT_CENTERS[slot] if slot < len(_DEFAULT_CENTERS) else sorted(PUZZLES[slot]["letters"])[0]
        if config_row:
            config_row.value = default_center
        else:
            db.session.add(KennoConfig(key=f"center_{slot}", value=default_center))
    else:
        # Beyond hardcoded range — clean up the center config entirely
        if config_row:
            db.session.delete(config_row)

    db.session.commit()
    _PUZZLE_CACHE.pop(slot, None)

    return jsonify({
        "slot": slot,
        "deleted": True,
        "reverted_to_hardcoded": has_hardcoded,
    })
