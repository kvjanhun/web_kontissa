import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import (
    FINNISH_MONTHS, RESULT_CACHE_BIS_FINAL_GRACE_SECONDS, RESULT_LOCAL_TIMEZONE,
    RESULT_PAUSE_EVENING_HOUR, RESULT_PAUSE_STALL_SECONDS,
    RESULT_SHOW_EVENING_HOUR, RESULT_SHOW_MORNING_HOUR,
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

def _split_award_tokens(value):
    return [item.strip().upper() for item in str(value or "").split(",") if item.strip()]

def _result_doc_has_main_bis(doc):
    if not isinstance(doc, dict):
        return False
    return any(
        "BIS-1" in _split_award_tokens(result.get("awards"))
        for result in doc.get("results") or []
    )

def _result_doc_has_show_finals(doc):
    """True when the cache already records show-wide finals placements: group
    (RYP), junior (BIS JUN), or veteran (BIS VET) Best in Show. Such shows crown
    a main Best in Show after the breed rings finish, so the whole-show cache
    must not settle on breed completion alone."""
    if not isinstance(doc, dict):
        return False
    for result in doc.get("results") or []:
        for token in _split_award_tokens(result.get("awards")):
            if token.startswith(("BIS JUN", "BIS VET", "BIS PEN", "RYP")):
                return True
    return False

def _result_doc_live_bis_grace_finished(doc, now):
    if not isinstance(doc, dict):
        return False

    detected_at = doc.get("bis_detected_at")
    if not detected_at and _result_doc_has_main_bis(doc):
        detected_at = doc.get("cached_at") or doc.get("updated_at")
    if not detected_at:
        return False

    return now >= detected_at + RESULT_CACHE_BIS_FINAL_GRACE_SECONDS

def _result_doc_live_entry_completion_grace_finished(doc, now, entry_count=None):
    if not isinstance(doc, dict):
        return False

    detected_at = doc.get("live_result_entry_completion_at")
    if not detected_at and isinstance(entry_count, int) and entry_count > 0:
        try:
            result_count = len(doc.get("results") or [])
        except TypeError:
            result_count = 0
        if result_count >= entry_count:
            detected_at = doc.get("cached_at") or doc.get("updated_at")
    if not detected_at:
        return False

    return now >= detected_at + RESULT_CACHE_BIS_FINAL_GRACE_SECONDS

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
