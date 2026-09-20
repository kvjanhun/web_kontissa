import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import finals
from .finals import parse_reg_id as _parse_reg_id  # noqa: F401 (re-exported)
from .config import (
    FINNISH_MONTHS, RESULT_CACHE_LIVE_TTL,
    RESULT_CACHE_RESCUE_TTL, RESULT_LOCAL_TIMEZONE,
    RESULT_PAUSE_EVENING_HOUR, RESULT_PAUSE_STALL_SECONDS,
    RESULT_SETTLE_DEADLINE_DAYS, RESULT_SHOW_EVENING_HOUR, RESULT_SHOW_MORNING_HOUR,
    SHOW_RECENT_FUTURE_DAYS, SHOW_RECENT_PAST_DAYS,
)

try:
    _LOCAL_TZ = ZoneInfo(RESULT_LOCAL_TIMEZONE)
except (ZoneInfoNotFoundError, ValueError):
    _LOCAL_TZ = None


def _local_now():
    """Current Finnish wall-clock time as a naive datetime.

    Show dates are Finnish local dates and the fetch window (08:00-21:00) is
    Finnish local hours. The container runs in UTC, so derive local time
    explicitly rather than trusting the process timezone. Falls back to the
    process clock if tzdata is missing.
    """
    if _LOCAL_TZ is None:
        return datetime.datetime.now()
    return datetime.datetime.now(_LOCAL_TZ).replace(tzinfo=None)

def _local_dt(now=None):
    """Finnish wall-clock datetime for a unix timestamp (or now if None).

    Same timezone handling as _local_now(), but for an explicit timestamp: the
    fetch window is Finnish local hours and must be evaluated as such regardless
    of the container's UTC clock.
    """
    if now is None:
        return _local_now()
    if _LOCAL_TZ is None:
        return datetime.datetime.fromtimestamp(now)
    return datetime.datetime.fromtimestamp(now, _LOCAL_TZ).replace(tzinfo=None)

def _show_is_recent(show, today=None):
    """Whether the show's date range sits inside the "recent" window — the shows
    whose data still changes: entry counts and result flags of upcoming shows,
    and the results of just-run ones. Gates the crawler's re-index candidates and
    the stale-flag re-probes. Unknown dates count as recent (fail open, like the
    old month-label heuristic this replaced)."""
    today = today or _local_now().date()
    start_date, end_date = _parse_show_date_range(show, today=today)
    if not start_date or not end_date:
        # No parseable day range; a month label alone still bounds the show.
        month, year = _month_year_from_label((show or {}).get("month", ""))
        if not month or not year:
            return True
        start_date = datetime.date(year, month, 1)
        end_date = (start_date + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    return (
        end_date >= today - datetime.timedelta(days=SHOW_RECENT_PAST_DAYS)
        and start_date <= today + datetime.timedelta(days=SHOW_RECENT_FUTURE_DAYS)
    )

def _utc_iso(ts):
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def _clean_judge_name(value):
    """Normalize Showlink judge labels such as 'TuomariTarja Kolkka'."""
    if not value:
        return ""
    text = " ".join(str(value).split())
    return re.sub(r"^tuomari\s*", "", text, flags=re.IGNORECASE).strip()

def _clean_breed_data(breed):
    item = dict(breed or {})
    if "judge" in item:
        judge = _clean_judge_name(item.get("judge"))
        if judge:
            item["judge"] = judge
        else:
            item.pop("judge", None)
    return item

def _clean_breed_list(breeds):
    return [_clean_breed_data(breed) for breed in (breeds or [])]

def _clean_all_result_item(result):
    item = dict(result or {})
    breed_obj = item.get("breedObj")
    if isinstance(breed_obj, dict):
        item["breedObj"] = _clean_breed_data(breed_obj)
    return item

def _clean_all_results(results):
    return [_clean_all_result_item(result) for result in (results or [])]

def _entry_count_from_breeds(breeds):
    """Total catalog entries across a breed list, or None when unknowable."""
    entry_count = 0
    entry_count_known = False
    for breed in breeds or []:
        try:
            entry_count += int(breed.get("count"))
            entry_count_known = True
        except (TypeError, ValueError):
            continue
    return entry_count if entry_count_known else None

def _result_doc_entries_complete(doc, entry_count):
    """True once the doc holds a result row for every catalog entry.

    Absentees mean the row count can legitimately stay below the catalog total,
    so this only fires when the show has no absentees — an optimistic same-day
    settle signal for finals-less shows, never the sole settle gate (the show
    date passing settles them regardless)."""
    if not isinstance(entry_count, int) or entry_count <= 0:
        return False
    try:
        return len(doc.get("results") or []) >= entry_count
    except (AttributeError, TypeError):
        return False

def _nothing_left_to_judge(doc, indexed_breeds):
    """Every breed the show lists has been judged and captured to the end.

    Ladder rung 2, and the one a lunch break cannot fake: mid-show there are
    always breeds unstarted or mid-ring, so an hour of silence does not satisfy
    it. A breed with no check icon leaves it unsatisfied, as does one whose
    capture is still *partial* — a slice of a ring being judged.

    A **provisional** capture counts as judged. It holds every entered dog and is
    only waiting for a second fetch to agree before it counts as final, which is
    a question about our confidence, not about the ring: the tiering keeps
    re-reading it, and quiescence still has to pass. Requiring finality here
    instead left a show that had genuinely finished unable to settle, because the
    breeds that never get an honour roll at all — the single-entry ones — had
    nothing left to promote them.

    Unknowable — no indexed breeds — is not "done": returns False.
    """
    breeds = [breed for breed in indexed_breeds or [] if breed.get("group") and breed.get("breed_id")]
    if not breeds:
        return False
    completed = (doc or {}).get("completed_breeds") or {}
    for breed in breeds:
        if not breed.get("has_results"):
            return False
        entry = completed.get(f"{breed.get('group')}:{breed.get('breed_id')}")
        if not entry:
            return False
        if finals._breed_capture_is_partial(entry, breed):
            return False
    return True


def _terminal_status(doc, indexed_breeds):
    """Where the show stands on the settle ladder, unified across show types.

    Both the live plan and the crawler's confirmation marker read this, so they
    never diverge. The rungs, in order:

    1. **Finals in** — every final the show owes has landed on its breed's rows
       (`finals.analyze`). Where the `R=BIS` / `R=RYP` pages hold placements they
       settle it outright, naming each winner; where they are empty they say
       nothing either way, because a show may publish its finals only as tokens
       on the winners' breed rows, and the award structure decides instead.
    2. **Nothing left to judge** — every listed breed is checked and its capture
       is no longer mid-ring. Carries a show that awards no finals at all, on its
       own.
    3. **Quiescence confirms** — neither rung is enough on its own: the caller
       requires the signature to come back unchanged on a later pass
       (`_mark_terminal_confirmation`), so a late row or correction resets it.
    4. The deadline in `_result_live_plan` backstops all of it.

    No rung asks what *kind* of show this is — combined `FCI 5/6` rings,
    group-only shows, puppy shows and single-breed specialties are all decided by
    what the source has actually awarded against what its entries oblige it to
    award, never by a show-type guess.

    `signature` is a stable string of the terminal-relevant state, and folds in
    the row count so a late row anywhere resets the confirmation.
    """
    analysis = finals.analyze(doc, indexed_breeds)
    probe = analysis["probe"]
    entry_count = _entry_count_from_breeds(indexed_breeds)
    entries_complete = _result_doc_entries_complete(doc, entry_count)
    try:
        row_count = len(doc.get("results") or [])
    except (AttributeError, TypeError):
        row_count = 0

    finals_published = bool(probe["seen"] and probe["published"] and not probe["missing_keys"])
    judging_finished = _nothing_left_to_judge(doc, indexed_breeds)

    if probe["published"] or (probe["seen"] and analysis["finals_observed"]):
        # This show awards finals, either because its pages name winners or
        # because its captured rows already carry RYP or BIS tokens — some shows
        # publish them only there. Either way the structure decides, against what
        # the entries oblige the show to award. Reading empty pages as "awards no
        # finals" settles an all-breed show the moment its last ring lands and
        # loses every final it had left.
        target_met = judging_finished and analysis["target_met"]
    elif probe["seen"]:
        # Pages read, nothing on them, no finals token anywhere: awards none.
        target_met = judging_finished
    elif analysis["expects_main_bis"]:
        # No probe (an old cache, or the pages have not been read yet): fall back
        # to the award-structure inference.
        target_met = analysis["target_met"]
    else:
        target_met = entries_complete

    signature = "|".join([
        f"rows:{row_count}",
        f"judged:{int(judging_finished)}",
        f"probe:{probe['placements']}:{len(probe['missing_keys'])}",
        finals.fingerprint_token(analysis),
    ])
    return {
        "analysis": analysis,
        "probe": probe,
        "expects_finals": analysis["expects_finals"],
        "expects_main_bis": analysis["expects_main_bis"],
        "entries_complete": entries_complete,
        "finals_published": finals_published,
        "judging_finished": judging_finished,
        "target_met": target_met,
        "signature": signature,
    }

def _in_fetch_window(
    hour,
    morning_hour=RESULT_SHOW_MORNING_HOUR,
    evening_hour=RESULT_SHOW_EVENING_HOUR,
):
    """Whether anything may reach Showlink at this Finnish local hour.

    The one window every fetching path shares: the result plan, the crawler's
    index pass and the show-list refresh. No dog show runs outside 08:00-21:00,
    so a request made then buys nothing. Keep this the single definition — the
    same hours expressed separately per path is how the index pass ended up
    with no check at all."""
    return morning_hour <= hour < evening_hour


def _fetch_window_open(now=None):
    """_in_fetch_window against Finnish local time, for callers holding a unix
    timestamp (or nothing) rather than an hour."""
    return _in_fetch_window(_local_dt(now).hour)

def _result_live_plan(
    show,
    doc,
    indexed_breeds,
    now=None,
    morning_hour=RESULT_SHOW_MORNING_HOUR,
    evening_hour=RESULT_SHOW_EVENING_HOUR,
    deadline_days=RESULT_SETTLE_DEADLINE_DAYS,
):
    """The single live/settle decision for a show's whole-show result cache.

    Pure given (show, doc, indexed_breeds, now): both the result-cache TTL path
    and the show-stats "is this still live?" path derive their answer here, so
    the two ends never disagree about when a show is finished.

    The terminal is the show's award structure, not a clock:

    - a show that expects finals (multi-group, or finals tokens already present)
      is not done until its terminal target is captured *and* confirmed stable —
      every result-bearing group has RYP-1 and the main BIS-1 has landed (a
      specialty cluster with no group stage settles on BIS-1 alone);
    - a finals-less show is done on entry completion / its date passing.

    Phases: `live` (normal cadence), `rescue` (past date but within the deadline,
    finals still owed), `settled` / `settled_incomplete` (leave fast-polling).
    `can_fetch` folds in the shared Finnish-local fetch window, which every phase
    obeys — a show still owing its finals at 21:00 waits for the morning.
    """
    if now is None:
        localnow = _local_now()
    elif isinstance(now, (int, float)):
        localnow = _local_dt(now)
    elif isinstance(now, datetime.date) and not isinstance(now, datetime.datetime):
        localnow = datetime.datetime.combine(now, datetime.time(hour=12))
    else:
        localnow = now

    today = localnow.date()
    hour = localnow.hour
    start_date, end_date = _parse_show_date_range(show, today=today)
    availability = _show_result_availability(
        show, now=localnow, morning_hour=morning_hour, evening_hour=evening_hour
    )
    state = availability.get("show_state")
    morning_hour = availability.get("morning_hour", morning_hour)
    evening_hour = availability.get("evening_hour", evening_hour)

    status = _terminal_status(doc, indexed_breeds)
    analysis = status["analysis"]
    expects_finals = status["expects_finals"]
    expects_main_bis = status["expects_main_bis"]
    target_met = status["target_met"]
    # Both finals and finals-less shows require a confirming pass (the crawler's
    # `_mark_terminal_confirmation`) before settling, so a live show never flips
    # to "done" the instant its last result row lands.
    confirmed = bool((doc or {}).get("terminal_confirmed"))
    settle_by_target = target_met and confirmed

    is_final_day = end_date is None or today >= end_date
    deadline_date = end_date + datetime.timedelta(days=deadline_days) if end_date else None
    deadline_passed = bool(deadline_date) and today > deadline_date

    def _plan(phase, ttl, can_fetch):
        return {
            "phase": phase,
            "ttl": ttl,
            "can_fetch": can_fetch,
            "show_state": state,
            "expects_finals": expects_finals,
            "expects_main_bis": expects_main_bis,
            "target_met": target_met,
            "confirmed": confirmed,
            "settle_by_target": settle_by_target,
            "is_final_day": is_final_day,
            "missing_ryp_groups": sorted(analysis["missing_ryp_groups"]),
            "has_bis1": analysis["has_bis1"],
            "analysis": analysis,
        }

    if state == "upcoming":
        return _plan("upcoming", None, False)

    if deadline_passed:
        return _plan("settled" if settle_by_target else "settled_incomplete", None, False)

    if settle_by_target and is_final_day:
        return _plan("settled", None, False)

    # Rescue exists only to catch a **main BIS** and its group RYPs, which publish
    # after the breed rings on a multi-group show. A single-group show
    # (breed/group specialty) crowns no main BIS, so it never enters rescue — it
    # settles when its date passes, like a finals-less show, having captured its
    # side BIS / group RYP during the live day. This also stops a group-10-only
    # show (junior/veteran/utility BIS, no `BIS-1`) from being rescue-polled for
    # two days every time.
    if not expects_main_bis and state == "past":
        return _plan("settled", None, False)

    in_day = _in_fetch_window(hour, morning_hour, evening_hour)

    if state == "live":
        return _plan("live", RESULT_CACHE_LIVE_TTL, in_day)

    # state == "past", within the deadline, a multi-group show still owing its
    # main BIS: rescue. Finals typed in after the evening cutoff are picked up by
    # the next morning's rescue pass, inside the deadline.
    return _plan("rescue", RESULT_CACHE_RESCUE_TTL, in_day)

def _result_doc_last_result_at(doc):
    """Unix timestamp of the most recent breed that actually produced results.

    Each completed breed records the fetch time on `completed_breeds[*].updated_at`;
    already-completed breeds are not re-fetched on live passes and re-probed
    no-result breeds keep `result_count: 0`, so the max over result-bearing breeds
    is the time new results were last available. Returns None when unknown."""
    if not isinstance(doc, dict):
        return None

    latest = None
    for entry in (doc.get("completed_breeds") or {}).values():
        if not isinstance(entry, dict):
            continue
        try:
            if int(entry.get("result_count") or 0) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        ts = entry.get("updated_at")
        if isinstance(ts, (int, float)) and (latest is None or ts > latest):
            latest = ts
    return latest

def _month_year_from_label(month_str):
    if not month_str:
        return None, None

    parts = month_str.lower().strip().split()
    if len(parts) < 2:
        return None, None

    try:
        month = FINNISH_MONTHS.index(parts[0]) + 1
        year = int(parts[1])
        return month, year
    except (ValueError, IndexError):
        return None, None

def _show_year_from_month_label(show):
    _month_from_label, year_from_label = _month_year_from_label(show.get("month", ""))
    return year_from_label

def _infer_show_year_from_date_month(month, today=None):
    if not month:
        return None

    today = today or _local_now().date()
    year = today.year

    # Showlink's relative sections ("Tänään", "Huomenna") omit the year.
    # Keep dates near new year on the intuitive side of the calendar.
    if month < today.month - 6:
        year += 1
    elif month > today.month + 6:
        year -= 1
    return year

def _show_year_for_date_month(show, month, today=None):
    return _show_year_from_month_label(show) or _infer_show_year_from_date_month(month, today=today)

def _date_from_parts(year, month, day):
    try:
        return datetime.date(year, month, day)
    except (TypeError, ValueError):
        return None

def _parse_show_date_range(show, today=None):
    """Parse Showlink list date ranges such as '14.06.' or '14.-15.06.'."""
    if not show:
        return None, None

    date_str = str(show.get("date") or "").strip()
    if not date_str:
        return None, None

    # Cross-month range: 31.05.-01.06.
    match = re.search(
        r"(\d{1,2})\.(\d{1,2})\.\s*-\s*(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?",
        date_str,
    )
    if match:
        start_day, start_month, end_day, end_month, year_str = match.groups()
        end_month = int(end_month)
        year = int(year_str) if year_str else _show_year_for_date_month(show, end_month, today=today)
        if year is None:
            return None, None
        start_month = int(start_month)
        start_year = year - 1 if start_month > end_month else year
        return (
            _date_from_parts(start_year, start_month, int(start_day)),
            _date_from_parts(year, end_month, int(end_day)),
        )

    # Same-month range: 14.-15.06.
    match = re.search(r"(\d{1,2})\.\s*-\s*(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?", date_str)
    if match:
        start_day, end_day, month_str, year_str = match.groups()
        month = int(month_str)
        year = int(year_str) if year_str else _show_year_for_date_month(show, month, today=today)
        if year is None:
            return None, None
        return (
            _date_from_parts(year, month, int(start_day)),
            _date_from_parts(year, month, int(end_day)),
        )

    # Single date: 14.06.
    match = re.search(r"(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?", date_str)
    if not match:
        return None, None

    day_str, month_str, year_str = match.groups()
    month = int(month_str)
    year = int(year_str) if year_str else _show_year_for_date_month(show, month, today=today)
    if year is None:
        return None, None

    date = _date_from_parts(year, month, int(day_str))
    return date, date

def _parse_show_date(show, today=None):
    _start_date, end_date = _parse_show_date_range(show, today=today)
    return end_date

def _show_date_state(show, today=None):
    """Whether a show is upcoming, live or past, on the Finnish calendar.

    The date must come from the same clock as everything else: the containers run
    in UTC, so between 21:00 UTC and midnight the system date is still yesterday
    in Helsinki terms. A show that ended that evening then reads as live here
    while `_result_live_plan` — which has always used Finnish local time — reads
    it as past, and the two disagree for three hours every night."""
    today = today or _local_now().date()
    start_date, end_date = _parse_show_date_range(show, today=today)
    if not start_date or not end_date:
        return "unknown"

    if start_date <= today <= end_date:
        return "live"
    if end_date < today:
        return "past"
    return "upcoming"

def _show_age_days(show, today=None):
    today = today or _local_now().date()
    show_date = _parse_show_date(show, today=today)
    if not show_date:
        return None
    return (today - show_date).days

def _local_iso(dt):
    return dt.isoformat(timespec="seconds") if dt else None

def _show_result_availability(
    show,
    now=None,
    morning_hour=RESULT_SHOW_MORNING_HOUR,
    evening_hour=RESULT_SHOW_EVENING_HOUR,
):
    """Decide whether result pages are worth checking for a show."""
    now = now or _local_now()
    if isinstance(now, datetime.date) and not isinstance(now, datetime.datetime):
        now = datetime.datetime.combine(now, datetime.time())

    today = now.date()
    # The shared fetch window applies to every show state, not just a live one:
    # a past show still owing its finals, and a show whose date could not be
    # parsed, are both waiting for the morning like everything else.
    in_window = _in_fetch_window(now.hour, morning_hour, evening_hour)

    start_date, end_date = _parse_show_date_range(show, today=today)
    if not start_date or not end_date:
        return {
            "can_fetch": in_window,
            "show_state": "unknown",
            "reason": "unknown_date" if in_window else "show_night",
            "morning_hour": morning_hour,
            "evening_hour": evening_hour,
        }

    available_from = datetime.datetime.combine(start_date, datetime.time(hour=morning_hour))

    base = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "available_from_iso": _local_iso(available_from),
        "morning_hour": morning_hour,
        "evening_hour": evening_hour,
    }

    if today < start_date:
        return {
            **base,
            "can_fetch": False,
            "show_state": "upcoming",
            "reason": "future_show",
        }

    # Live date range. Results are only worth checking during the day: not
    # before the morning hour and not after the evening hour. This holds on
    # every day of a multi-day show, so a live show goes quiet overnight
    # (21:00–08:00) instead of polling Showlink between show days.
    if start_date <= today <= end_date:
        if now.hour < morning_hour:
            return {
                **base,
                "can_fetch": False,
                "show_state": "live",
                "reason": "show_morning",
            }
        if now.hour >= evening_hour:
            return {
                **base,
                "can_fetch": False,
                "show_state": "live",
                "reason": "show_night",
            }
        return {
            **base,
            "can_fetch": True,
            "show_state": "live",
            "reason": "show_day",
        }

    return {
        **base,
        "can_fetch": in_window,
        "show_state": "past",
        "reason": "past_show" if in_window else "show_night",
    }

def _show_live_phase(
    show,
    now=None,
    availability=None,
    last_result_at=None,
    stall_seconds=RESULT_PAUSE_STALL_SECONDS,
    stall_from_hour=RESULT_PAUSE_EVENING_HOUR,
):
    """For a show whose date-state is already "live", classify the moment as
    "active" (Käynnissä) or "paused" (Jatkuu).

    "paused" is any hold the show has not concluded from: the 21:00–08:00 quiet
    window on any day of the show, or a long result stall during the evening
    wind-down before another show day. A show reaching its date-state "past"
    (`_result_live_plan` settling it) is what removes the badge entirely — so a
    show still owing its finals at 21:00 reads as continuing, not as finished.
    Leaving it badge-less there made "stopped for the night" indistinguishable
    from settled history.

    The first day's pre-dawn stays "active": nothing has happened yet to
    continue from."""
    now = now or _local_now()
    if isinstance(now, datetime.date) and not isinstance(now, datetime.datetime):
        now = datetime.datetime.combine(now, datetime.time(hour=12))

    today = now.date()
    start_date, end_date = _parse_show_date_range(show, today=today)
    if not start_date or not end_date:
        return "active"

    availability = availability or _show_result_availability(show, now=now)
    morning_hour = availability.get("morning_hour", RESULT_SHOW_MORNING_HOUR)
    evening_hour = availability.get("evening_hour", RESULT_SHOW_EVENING_HOUR)

    if now.hour < morning_hour:
        # Overnight / early morning: the next active period is later today.
        next_active_date = today
        in_lull = True
    elif now.hour >= evening_hour:
        # Evening / overnight: the next active period is tomorrow.
        next_active_date = today + datetime.timedelta(days=1)
        in_lull = True
    else:
        # Daytime. Treat a long result stall in the evening wind-down as the day
        # ending early; the next active period is then the following day.
        next_active_date = today + datetime.timedelta(days=1)
        in_lull = (
            now.hour >= stall_from_hour
            and last_result_at is not None
            and (now.timestamp() - last_result_at) >= stall_seconds
        )

    if not in_lull:
        return "active"

    # The first morning before the show opens has nothing to continue from.
    if next_active_date <= start_date:
        return "active"

    # A stall inside the fetch window only counts as a pause when another show
    # day actually follows; outside the window the show is held for the night
    # whether or not it will resume, and saying so beats saying nothing.
    if next_active_date <= end_date:
        return "paused"
    return "paused" if not _in_fetch_window(now.hour, morning_hour, evening_hour) else "active"
