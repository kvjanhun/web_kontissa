import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import finals
from .config import (
    FINNISH_MONTHS, RESULT_CACHE_LIVE_TTL, RESULT_CACHE_OVERTIME_TTL,
    RESULT_CACHE_RESCUE_TTL, RESULT_FINALS_NIGHT_STOP_HOUR, RESULT_LOCAL_TIMEZONE,
    RESULT_PAUSE_EVENING_HOUR, RESULT_PAUSE_STALL_SECONDS,
    RESULT_SETTLE_DEADLINE_DAYS, RESULT_SHOW_EVENING_HOUR, RESULT_SHOW_MORNING_HOUR,
)

RELATIVE_RECENT_LABELS = {"tänään", "huomenna", "today", "tomorrow"}

try:
    _LOCAL_TZ = ZoneInfo(RESULT_LOCAL_TIMEZONE)
except (ZoneInfoNotFoundError, ValueError):
    _LOCAL_TZ = None


def _local_now():
    """Current Finnish wall-clock time as a naive datetime.

    Show dates are Finnish local dates and the result-fetch windows
    (06:00 morning, 21:00 evening) are Finnish local hours. The container
    runs in UTC, so derive local time explicitly rather than trusting the
    process timezone. Falls back to the process clock if tzdata is missing.
    """
    if _LOCAL_TZ is None:
        return datetime.datetime.now()
    return datetime.datetime.now(_LOCAL_TZ).replace(tzinfo=None)

def _local_dt(now=None):
    """Finnish wall-clock datetime for a unix timestamp (or now if None).

    Same timezone handling as _local_now(), but for an explicit timestamp — used
    by the backfill off-peak window check, which must evaluate Finnish local
    hours regardless of the container's UTC clock.
    """
    if now is None:
        return _local_now()
    if _LOCAL_TZ is None:
        return datetime.datetime.fromtimestamp(now)
    return datetime.datetime.fromtimestamp(now, _LOCAL_TZ).replace(tzinfo=None)

def _is_recent_show(month_str):
    """Check if the show month is the current or previous month."""
    if not month_str:
        return True  # Default to recent if unknown

    try:
        m_lower = month_str.lower().strip()
        if m_lower in RELATIVE_RECENT_LABELS:
            return True

        now = datetime.datetime.now()
        cur_year = now.year
        cur_month = now.month

        prev_month = cur_month - 1 if cur_month > 1 else 12
        prev_year = cur_year if cur_month > 1 else cur_year - 1

        cur_str = f"{FINNISH_MONTHS[cur_month - 1]} {cur_year}".lower()
        prev_str = f"{FINNISH_MONTHS[prev_month - 1]} {prev_year}".lower()

        return m_lower == cur_str or m_lower == prev_str
    except Exception:
        return True

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

def _parse_reg_id(reg_url):
    """Extract the dog registration number from a jalostus.kennelliitto.fi link.

    e.g. '.../frmKoira.aspx?RekNo=FI44694%2F25' -> 'FI44694/25'. This reg id is
    the cross-show anchor for a dog; it must survive URL-encoding of the slash.
    """
    if not reg_url:
        return ""
    match = re.search(r"[?&]RekNo=([^&#]+)", str(reg_url), flags=re.IGNORECASE)
    if not match:
        return ""
    from urllib.parse import unquote
    return unquote(match.group(1)).strip()

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

def _terminal_status(doc, indexed_breeds):
    """The show's terminal award state, unified across show types.

    Both the live plan and the crawler's confirmation marker read the terminal
    from here so they never diverge:

    - a show that expects finals is done when `finals.analyze` says the target
      is met (main BIS + every group's RYP, or BIS-1 for a specialty cluster);
    - a finals-less show is done on entry completion.

    `signature` is a stable string of the terminal-relevant state; when it stops
    changing across a pass the terminal is confirmed stable and may settle."""
    analysis = finals.analyze(doc, indexed_breeds)
    entry_count = _entry_count_from_breeds(indexed_breeds)
    entries_complete = _result_doc_entries_complete(doc, entry_count)
    try:
        row_count = len(doc.get("results") or [])
    except (AttributeError, TypeError):
        row_count = 0
    if analysis["expects_main_bis"]:
        # Multi-group show: the terminal is the main BIS-1 (+ every group's RYP-1).
        target_met = analysis["target_met"]
        signature = finals.fingerprint_token(analysis)
    else:
        # Single-group or finals-less show: no main BIS to wait for. Settle on
        # entry completion; any group RYP / side BIS is captured opportunistically
        # by the finals sweep and folded into the signature so a late one resets
        # the confirmation.
        target_met = entries_complete
        signature = f"entries:{row_count}|{finals.fingerprint_token(analysis)}"
    return {
        "analysis": analysis,
        "expects_finals": analysis["expects_finals"],
        "expects_main_bis": analysis["expects_main_bis"],
        "entries_complete": entries_complete,
        "target_met": target_met,
        "signature": signature,
    }

def _in_finals_fetch_window(hour, morning_hour, evening_hour, night_stop_hour):
    """Whether a finals-owed show may be fetched at this Finnish local hour.

    Extends past the normal evening cutoff into a nightly overtime tail so the
    finals (published ~21:00–23:30) are captured, then hard-stops overnight
    (night_stop..morning) to stay polite. Fetch allowed 06:00–01:00 by default."""
    if morning_hour <= hour < evening_hour:
        return True
    if hour >= evening_hour:
        return True
    return hour < night_stop_hour

def _result_live_plan(
    show,
    doc,
    indexed_breeds,
    now=None,
    morning_hour=RESULT_SHOW_MORNING_HOUR,
    evening_hour=RESULT_SHOW_EVENING_HOUR,
    night_stop_hour=RESULT_FINALS_NIGHT_STOP_HOUR,
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

    Phases: `live` (normal cadence), `overtime` (final-day evening tail, finals
    still owed), `rescue` (past date but within the deadline, finals still owed),
    `settled` / `settled_incomplete` (leave fast-polling). `can_fetch` folds in
    the Finnish-local fetch window, extended for finals-owed shows.
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

    # Overtime and rescue exist only to catch a **main BIS** and its group RYPs,
    # which publish after the breed rings on a multi-group show. A single-group
    # show (breed/group specialty) crowns no main BIS, so it never enters overtime
    # or rescue — it settles when its date passes, like a finals-less show, having
    # captured its side BIS / group RYP during the live day. This also stops a
    # group-10-only show (junior/veteran/utility BIS, no `BIS-1`) from being
    # rescue-polled for two days every time.
    if not expects_main_bis and state == "past":
        return _plan("settled", None, False)

    in_day = morning_hour <= hour < evening_hour

    if state == "live":
        if in_day:
            return _plan("live", RESULT_CACHE_LIVE_TTL, True)
        # Outside day hours on a live date-range. Only a multi-group final day's
        # finals earn an evening/night overtime tail; earlier days and single-group
        # shows keep the polite overnight lull between show days.
        if (
            is_final_day
            and expects_main_bis
            and not settle_by_target
            and (hour >= evening_hour or hour < night_stop_hour)
        ):
            return _plan("overtime", RESULT_CACHE_OVERTIME_TTL, True)
        return _plan("live", RESULT_CACHE_LIVE_TTL, False)

    # state == "past", within the deadline, a multi-group show still owing its
    # main BIS: rescue.
    can_fetch = _in_finals_fetch_window(hour, morning_hour, evening_hour, night_stop_hour)
    return _plan("rescue", RESULT_CACHE_RESCUE_TTL, can_fetch)

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

    today = today or datetime.date.today()
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
    today = today or datetime.date.today()
    start_date, end_date = _parse_show_date_range(show, today=today)
    if not start_date or not end_date:
        return "unknown"

    if start_date <= today <= end_date:
        return "live"
    if end_date < today:
        return "past"
    return "upcoming"

def _show_age_days(show, today=None):
    today = today or datetime.date.today()
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
    start_date, end_date = _parse_show_date_range(show, today=today)
    if not start_date or not end_date:
        return {
            "can_fetch": True,
            "show_state": "unknown",
            "reason": "unknown_date",
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
    # (e.g. 21:00–06:00) instead of polling Showlink between show days.
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
        "can_fetch": True,
        "show_state": "past",
        "reason": "past_show",
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

    "paused" is the multi-day nightly/evening lull *before another show day*: the
    21:00–06:00 quiet window, or a long result stall during the evening wind-down.
    The first day's pre-dawn and the final day's wind-down stay "active" so the
    show only reads as "continuing" when judging genuinely resumes later."""
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

    # Only a lull that another in-range show day follows is "Jatkuu". Excludes the
    # pre-show first morning (next_active_date == start_date) and the final day's
    # wind-down (next_active_date past end_date).
    if start_date < next_active_date <= end_date:
        return "paused"
    return "active"
