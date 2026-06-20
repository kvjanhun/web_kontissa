import datetime
import re

from .config import FINNISH_MONTHS, RESULT_SHOW_MORNING_HOUR

RELATIVE_RECENT_LABELS = {"tänään", "huomenna", "today", "tomorrow"}

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

def _show_result_availability(show, now=None, morning_hour=RESULT_SHOW_MORNING_HOUR):
    """Decide whether result pages are worth checking for a show."""
    now = now or datetime.datetime.now()
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
        }

    available_from = datetime.datetime.combine(start_date, datetime.time(hour=morning_hour))

    base = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "available_from_iso": _local_iso(available_from),
        "morning_hour": morning_hour,
    }

    if today < start_date:
        return {
            **base,
            "can_fetch": False,
            "show_state": "upcoming",
            "reason": "future_show",
        }

    if today == start_date and now < available_from:
        return {
            **base,
            "can_fetch": False,
            "show_state": "live",
            "reason": "show_morning",
        }

    if start_date <= today <= end_date:
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
