from collections import Counter
from datetime import date, datetime, timedelta, timezone
import zoneinfo
from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required
import hashlib
import os

from app import limiter
from app.models import db, BlockedWord, KennoCombination, KennoConfig, KennoAchievement, KennoPuzzle, PageView
from app.decorators import admin_required
import structlog

kenno_bp = Blueprint('kenno', __name__)
logger = structlog.get_logger(__name__)

_WORDLIST_PATH = os.path.join(os.path.dirname(__file__), '..', 'wordlists', 'kotus_words.txt')
try:
    with open(_WORDLIST_PATH, encoding='utf-8') as _f:
        # Normalise hyphenated compounds (e.g. lähi-itä → lähiitä) so they are
        # valid puzzle words; the frozenset also deduplicates any collisions.
        _ALL_WORDS = frozenset(line.strip().replace('-', '') for line in _f if line.strip())
except FileNotFoundError:
    _ALL_WORDS = frozenset()

def _get_puzzle_letters(idx):
    """Return the 7 letters for puzzle *idx* from the DB."""
    row = KennoPuzzle.query.filter_by(slot=idx).first()
    if row:
        return row.letters.split(",")
    return None


def _total_puzzles():
    """Return the total number of puzzle slots in the DB."""
    highest = db.session.query(db.func.max(KennoPuzzle.slot)).scalar()
    return (highest + 1) if highest is not None else 0


def _get_center(idx):
    """Read the chosen center letter for puzzle *idx* from KennoConfig."""
    row = KennoConfig.query.filter_by(key=f"center_{idx}").first()
    if row:
        return row.value
    # Fallback: first letter alphabetically
    letters = _get_puzzle_letters(idx)
    if letters:
        return sorted(letters)[0]
    return None


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
        logger.error("blocked_words_query_failed", exc_info=True)
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
        logger.error("blocked_words_query_failed", exc_info=True)
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


@kenno_bp.route("/api/kenno")
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


@kenno_bp.route("/api/kenno/block", methods=["POST"])
@admin_required
def kenno_block_word():
    data = request.get_json() or {}
    word = data.get("word", "").strip().lower()
    if not word:
        return jsonify({"error": "word required"}), 400

    if not BlockedWord.query.filter_by(word=word).first():
        db.session.add(BlockedWord(word=word))
        db.session.commit()
        _PUZZLE_CACHE.clear()
        logger.info("word_blocked", word=word, admin_id=current_user.id, admin_email=current_user.email)

    return jsonify({"word": word, "blocked": True})


@kenno_bp.route("/api/kenno/variations")
@admin_required
def kenno_variations():
    """Return all 7 center-letter variations for a puzzle (admin only)."""
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


@kenno_bp.route("/api/kenno/center", methods=["POST"])
@admin_required
def kenno_set_center():
    """Set the center letter for a puzzle (admin only)."""
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


@kenno_bp.route("/api/kenno/stats")
@admin_required
def kenno_stats():
    """Sanakenno overview stats (admin only)."""
    sanakenno_pv = db.session.query(PageView).filter_by(path="/sanakenno").first()
    page_views = sanakenno_pv.count if sanakenno_pv else 0
    blocked_words_count = db.session.query(BlockedWord).count()
    total_puzzles = _total_puzzles()

    return jsonify({
        "page_views": page_views,
        "blocked_words_count": blocked_words_count,
        "total_puzzles": total_puzzles,
    })


@kenno_bp.route("/api/kenno/blocked")
@admin_required
def kenno_blocked_list():
    """List all blocked words with timestamps (admin only)."""
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


@kenno_bp.route("/api/kenno/achievement", methods=["POST"])
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


@kenno_bp.route("/api/kenno/achievements")
@admin_required
def kenno_achievements():
    """Daily achievement summary (admin only)."""
    days = request.args.get("days", 30, type=int)
    days = max(1, min(90, days))

    now = datetime.now(_HELSINKI)
    today = now.date()
    # Convert Helsinki date range to UTC for the DB query
    start_date = today - timedelta(days=days - 1)
    # Helsinki midnight → UTC for query boundary
    start_utc = datetime(start_date.year, start_date.month, start_date.day,
                         tzinfo=_HELSINKI).astimezone(timezone.utc)

    achievements = (
        KennoAchievement.query
        .filter(KennoAchievement.achieved_at >= start_utc)
        .all()
    )

    # Group by Helsinki date (not UTC date)
    lookup = {}
    for a in achievements:
        # achieved_at is stored as UTC — convert to Helsinki for grouping
        if a.achieved_at.tzinfo is None:
            helsinki_dt = a.achieved_at.replace(tzinfo=timezone.utc).astimezone(_HELSINKI)
        else:
            helsinki_dt = a.achieved_at.astimezone(_HELSINKI)
        d = helsinki_dt.date().isoformat()
        lookup.setdefault(d, {})
        lookup[d][a.rank] = lookup[d].get(a.rank, 0) + 1

    # Fill all dates in range
    daily = []
    totals = {r: 0 for r in VALID_RANKS}
    for i in range(days):
        d = (start_date + timedelta(days=i)).isoformat()
        day_counts = {r: lookup.get(d, {}).get(r, 0) for r in VALID_RANKS}
        day_total = sum(day_counts.values())
        daily.append({"date": d, "counts": day_counts, "total": day_total})
        for r in VALID_RANKS:
            totals[r] += day_counts[r]

    return jsonify({"days": days, "daily": daily, "totals": totals})


@kenno_bp.route("/api/kenno/block/<int:word_id>", methods=["DELETE"])
@admin_required
def kenno_unblock_word(word_id):
    """Unblock a word by ID (admin only)."""
    bw = db.session.get(BlockedWord, word_id)
    if not bw:
        return jsonify({"error": "Blocked word not found"}), 404

    word = bw.word
    db.session.delete(bw)
    db.session.commit()
    _PUZZLE_CACHE.clear()
    logger.info("word_unblocked", word=word, word_id=word_id, admin_id=current_user.id, admin_email=current_user.email)

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


@kenno_bp.route("/api/kenno/preview", methods=["POST"])
@admin_required
@limiter.limit("20/minute")
def kenno_preview():
    """Preview all 7 center-letter variations for arbitrary letters (admin only)."""
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


@kenno_bp.route("/api/kenno/puzzle", methods=["POST"])
@admin_required
def kenno_save_puzzle():
    """Create or update a custom puzzle in a slot (admin only)."""
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

    force = data.get("force", False)

    # Safety: reject writes to today's live slot unless forced
    today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
    if slot == today_slot and not force:
        return jsonify({"error": "Cannot modify today's live puzzle"}), 409

    # Upsert KennoPuzzle row
    now = datetime.now(timezone.utc)
    row = db.session.get(KennoPuzzle, slot)
    is_new_slot = row is None
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


@kenno_bp.route("/api/kenno/schedule")
@admin_required
def kenno_schedule():
    """Return upcoming puzzle rotation schedule (admin only)."""
    days = request.args.get("days", 14, type=int)
    days = max(1, min(90, days))

    today = datetime.now(_HELSINKI).date()
    today_slot = _get_puzzle_for_date(today)
    total = _total_puzzles()

    schedule = []
    for i in range(days):
        d = today + timedelta(days=i)
        slot = _get_puzzle_for_date(d)
        schedule.append({
            "date": d.isoformat(),
            "slot": slot,
            "display_number": slot + 1,
            "is_today": (i == 0),
        })

    return jsonify({
        "schedule": schedule,
        "total_puzzles": total,
    })


@kenno_bp.route("/api/kenno/puzzle/swap", methods=["POST"])
@admin_required
def kenno_swap_puzzles():
    """Swap two puzzle slots (admin only). Swaps both letters and center."""
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

    force = data.get("force", False)

    today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
    if (slot_a == today_slot or slot_b == today_slot) and not force:
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


@kenno_bp.route("/api/kenno/puzzle/<int:slot>", methods=["DELETE"])
@admin_required
def kenno_delete_puzzle(slot):
    """Delete a puzzle slot (admin only)."""
    force = request.args.get("force", "false").lower() == "true"
    today_slot = _get_puzzle_for_date(datetime.now(_HELSINKI).date())
    if slot == today_slot and not force:
        return jsonify({"error": "Cannot modify today's live puzzle"}), 409

    row = db.session.get(KennoPuzzle, slot)
    if not row:
        return jsonify({"error": "No puzzle in this slot"}), 404

    db.session.delete(row)
    config_row = KennoConfig.query.filter_by(key=f"center_{slot}").first()
    if config_row:
        db.session.delete(config_row)
    db.session.commit()
    _PUZZLE_CACHE.pop(slot, None)
    return jsonify({"slot": slot, "deleted": True})


@kenno_bp.route("/api/kenno/combinations")
@admin_required
def kenno_combinations():
    """Browse pre-computed 7-letter combinations (admin only).

    Query params:
      requires     — comma-separated letters that MUST appear (e.g. "a,ö")
      excludes     — comma-separated letters that MUST NOT appear
      min_pangrams — minimum total pangrams (default: 1)
      max_pangrams — maximum total pangrams
      min_words    — minimum max-center word count
      max_words    — maximum max-center word count
      min_words_min — minimum min-center word count (worst center has at least N)
      max_words_min — maximum min-center word count
      in_rotation  — "true"/"false" to filter by rotation membership
      sort         — column to sort by (default: "pangrams")
      order        — "asc" or "desc" (default: "desc")
      page         — 1-indexed page (default: 1)
      per_page     — results per page (default: 50, max 200)
    """
    q = KennoCombination.query

    # Letter filters
    requires = request.args.get("requires", "").strip()
    if requires:
        for letter in requires.split(","):
            letter = letter.strip().lower()
            if letter:
                q = q.filter(KennoCombination.letters.contains(letter))

    excludes = request.args.get("excludes", "").strip()
    if excludes:
        for letter in excludes.split(","):
            letter = letter.strip().lower()
            if letter:
                q = q.filter(~KennoCombination.letters.contains(letter))

    # Numeric filters
    min_pangrams = request.args.get("min_pangrams", 1, type=int)
    q = q.filter(KennoCombination.total_pangrams >= min_pangrams)

    max_pangrams = request.args.get("max_pangrams", type=int)
    if max_pangrams is not None:
        q = q.filter(KennoCombination.total_pangrams <= max_pangrams)

    # Word count filters (max center = best case)
    min_words = request.args.get("min_words", type=int)
    if min_words is not None:
        q = q.filter(KennoCombination.max_word_count >= min_words)

    max_words = request.args.get("max_words", type=int)
    if max_words is not None:
        q = q.filter(KennoCombination.max_word_count <= max_words)

    # Word count filters (min center = worst case)
    min_words_min = request.args.get("min_words_min", type=int)
    if min_words_min is not None:
        q = q.filter(KennoCombination.min_word_count >= min_words_min)

    max_words_min = request.args.get("max_words_min", type=int)
    if max_words_min is not None:
        q = q.filter(KennoCombination.min_word_count <= max_words_min)

    # Rotation filter
    in_rotation = request.args.get("in_rotation")
    if in_rotation == "true":
        q = q.filter(KennoCombination.in_rotation == True)  # noqa: E712
    elif in_rotation == "false":
        q = q.filter(KennoCombination.in_rotation == False)  # noqa: E712

    # Sorting
    sort_col = request.args.get("sort", "pangrams")
    sort_order = request.args.get("order", "desc")

    col_map = {
        "pangrams": KennoCombination.total_pangrams,
        "words_max": KennoCombination.max_word_count,
        "words_min": KennoCombination.min_word_count,
        "score_max": KennoCombination.max_max_score,
        "score_min": KennoCombination.min_max_score,
        "letters": KennoCombination.letters,
    }
    col = col_map.get(sort_col, KennoCombination.total_pangrams)
    if sort_order == "asc":
        q = q.order_by(col.asc())
    else:
        q = q.order_by(col.desc())

    # Pagination
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(200, max(1, request.args.get("per_page", 50, type=int)))

    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "combinations": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    })
