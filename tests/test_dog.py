import datetime
import json
import time

import pytest
from unittest.mock import patch, MagicMock
import requests
from app.api import dog as dog_module
from app.dog_show.store import _show_list_cache
from app.dog_show import crawler as dog_crawler
from app.dog_show import finals as dog_finals
from app.dog_show import indexing as dog_indexing
from app.dog_show import result_cache as dog_result_cache
from app.dog_show import showlink as dog_showlink
from app.dog_show import sqlstore as dog_sqlstore
from app.dog_show import store as dog_store
from app.dog_show import db as dog_db
from app.dog_show.utils import (
    _result_doc_last_result_at, _result_live_plan, _show_is_recent, _show_live_phase,
    _show_result_availability, _utc_iso,
)

SAMPLE_SHOW_LIST_HTML = """
<table id="Nayttelylista">
    <tr class="nayttely">
        <td colspan="2" class="valiotsikko">kesäkuu 2026</td>
    </tr>
    <tr class="nayttely">
        <td><a href="/nayttelyt/Tulokset?Id=14042">14.06.</a></td>
        <td><a href="/nayttelyt/Tulokset?Id=14042">Basenji</a></td>
    </tr>
    <tr class="nayttely">
        <td><a href="/nayttelyt/Tulokset?Id=14043">15.06.</a></td>
        <td><a href="/nayttelyt/Tulokset?Id=14043">Villakoira erikoisnäyttely</a></td>
    </tr>
</table>
"""

SAMPLE_SHOW_DETAIL_HTML = """
<div id="divOtsikko">
    <h1>14.06.2026 Basenji</h1>
</div>
<table class="rotulistatable">
    <tr class="rotuluettelo">
        <td><a href="/nayttelyt/Tulokset?Id=14042&R=5&RO=3">basenji</a></td>
        <td class="right">78</td>
        <td class="right"><i class="fa fa-check"></i></td>
    </tr>
    <tr class="rotuluettelo">
        <td><a href="/nayttelyt/Tulokset?Id=14042&R=5&RO=4">ibizanpodenco</a></td>
        <td class="right">12</td>
        <td class="right"></td>
    </tr>
</table>
"""

SAMPLE_BREED_RESULTS_HTML = """
<div id="divOtsikko">
    <h1>14.06.2026 Basenji</h1>
</div>
<table>
    <tr class="ropotsikko">
        <td>
            <span class="left">basenji</span>
            <div class="floatright">
                <span>Tuomari Paula Steele</span>
            </div>
        </td>
    </tr>
</table>
<table class="roptulostaulukko">
    <tr class="roptulos">
        <td>ROP</td>
        <td>Wazazi Tempting Fate, Om. Kortelainen Sanna</td>
    </tr>
</table>
<table class="roduntulokset">
    <tr class="sukupuoli">
        <td colspan="6">Urokset</td>
    </tr>
    <tr class="luokka">
        <td colspan="6"><span class="left">Pentuluokka 5-7 kk</span></td>
    </tr>
    <tr class="tulos">
        <td>1</td>
        <td><a href="/frmKoira.aspx?RekNo=FI13442%2F26">Ajibu You Are My Thrill</a></td>
        <td>KP</td>
        <td>1</td>
        <td></td>
        <td>ROP-pentu</td>
    </tr>
    <tr class="arvostelu">
        <td></td>
        <td>5 months old, clearly needs time...</td>
    </tr>
</table>
"""

SAMPLE_BREED_RESULTS_GLUE_JUDGE_HTML = """
<div id="divOtsikko">
    <h1>18.-19.04.2026 Vaasa KV</h1>
</div>
<table>
    <tr class="ropotsikko">
        <td>
            <span class="left">sileäkarvainen noutaja</span>
            <div class="floatright">
                <span>Tuomari<span>Tarja Kolkka</span></span>
            </div>
        </td>
    </tr>
</table>
<table class="roduntulokset">
    <tr class="sukupuoli">
        <td colspan="6">Nartut</td>
    </tr>
    <tr class="luokka">
        <td colspan="6"><span class="left">Avoin luokka</span></td>
    </tr>
    <tr class="tulos">
        <td>1</td>
        <td>Test Dog</td>
        <td>ERI</td>
        <td>1</td>
        <td></td>
        <td>SA</td>
    </tr>
</table>
"""

SAMPLE_BREED_RESULTS_FLOATLEFT_HTML = """
<div id="divOtsikko">
    <h1>20.-21.06.2026 Jyväskylä KV</h1>
</div>
<table class="roptulostaulukko">
    <tr class="ropotsikko">
        <td colspan="2">
            <div class="floatleft">sileäkarvainen noutaja</div>
            <div class="floatright">
                <span><span class="tuomariotsikko">Tuomari </span>Pietro Marino</span>
            </div>
        </td>
    </tr>
    <tr class="roptulos">
        <td>CACIB uros</td>
        <td>Calzeat Causin Heads To Turn, Om. Nyberg Tiia</td>
    </tr>
</table>
<table class="roduntulokset">
    <tr class="sukupuoli">
        <td colspan="7">Urokset</td>
    </tr>
    <tr class="luokka">
        <td colspan="7"><span class="left">Avoin luokka</span></td>
    </tr>
    <tr class="tulos">
        <td>776</td>
        <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=SE10567%2F2024">Almanza Blast From The Past</a></td>
        <td>ERI</td>
        <td>1</td>
        <td>PU3</td>
        <td>SA</td>
        <td></td>
    </tr>
</table>
"""

@pytest.fixture(autouse=True)
def clear_caches(monkeypatch, tmp_path):
    # Each test gets a fresh, isolated dog.db file with empty tables.
    dog_db_uri = "sqlite:///" + str(tmp_path / "dog.db")
    dog_db.configure(dog_db_uri)
    dog_db.init_db(dog_db_uri)

    _show_list_cache["data"] = None
    _show_list_cache["ts"] = 0
    dog_indexing._show_stats_cache.clear()
    yield
    # Release the per-test database file so its WAL handles don't leak.
    dog_db.configure("sqlite://")


def _current_month_label():
    """Finnish month label for the current month, so recency checks hold whenever
    the suite runs."""
    from app.dog_show.config import FINNISH_MONTHS
    now = datetime.datetime.now()
    return f"{FINNISH_MONTHS[now.month - 1]} {now.year}"


def seed_index_show(show_id, show):
    """Seed one show into the dog index the way the app's writers do — one
    wholesale row write through the store facade, read back per request."""
    dog_store._write_index_show(show_id, show)

@patch("app.dog_show.showlink._SESSION.get")
def test_fetch_page_advertises_crawler_identity(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = "<html><body>ok</body></html>"
    mock_get.return_value = mock_resp

    dog_showlink._fetch_page("https://example.test/showlink")

    assert mock_get.call_args.kwargs["headers"]["User-Agent"] == (
        "erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)"
    )

@patch("app.dog_show.showlink._SESSION.get")
def test_get_shows(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_LIST_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "shows" in data
    assert len(data["shows"]) == 2
    assert data["shows"][0]["id"] == 14042
    assert data["shows"][0]["name"] == "Basenji"
    assert data["shows"][0]["month"] == "kesäkuu 2026"
    assert data["shows"][0]["source_url"].endswith("Id=14042")
    assert data["shows"][1]["id"] == 14043
    assert data["shows"][1]["name"] == "Villakoira erikoisnäyttely"
    assert data["index"]["total_show_count"] == 2


@patch("app.dog_show.showlink._SESSION.get")
def test_get_shows_enriches_cached_index_stats(mock_get, client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "updated_at": 1781431200,
        "breeds": [
            {"name": "basenji", "count": 78, "has_results": True},
            {"name": "ibizanpodenco", "count": 12, "has_results": False},
        ],
    })
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_LIST_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows")

    assert resp.status_code == 200
    data = resp.get_json()
    stats = data["shows"][0]["stats"]
    assert stats["indexed"] is True
    assert stats["breed_count"] == 2
    assert stats["entry_count"] == 90
    assert stats["result_breed_count"] == 1
    assert stats["updated_at_iso"] == "2026-06-14T10:00:00Z"
    assert "stats" not in data["shows"][1]


def test_show_stats_include_live_result_progress(client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "has_results": True},
            {"name": "ibizanpodenco", "count": 1, "has_results": True},
        ],
    })
    dog_store._save_result_cache_doc(14042, {
        "status": "running",
        "results": [{}, {}, {}, {}],
    })

    live_stats = dog_indexing._show_stats_from_index(
        14042,
        show={"id": 14042, "date": "14.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 14),
    )
    past_stats = dog_indexing._show_stats_from_index(
        14042,
        show={"id": 14042, "date": "14.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 15),
    )

    assert live_stats["show_state"] == "live"
    assert live_stats["is_live"] is True
    assert live_stats["entry_count"] == 3
    assert live_stats["result_count"] == 3
    assert past_stats["show_state"] == "past"
    assert past_stats["is_live"] is False
    assert "result_count" not in past_stats

    seed_index_show("14043", {
        "title": "14.06.2026 Villakoira",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "villakoira", "count": 4, "has_results": True},
        ],
    })
    uncached_live_stats = dog_indexing._show_stats_from_index(
        14043,
        show={"id": 14043, "date": "14.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 14),
    )
    assert uncached_live_stats["is_live"] is True
    assert "result_count" not in uncached_live_stats


def _dt(year, month, day, hour, minute=0):
    return datetime.datetime(year, month, day, hour, minute)


def test_show_live_phase_multiday_nightly_hiatus():
    # Two-day show: Saturday 27th (start) → Sunday 28th (end, final day).
    show = {"date": "27.-28.06.", "month": "kesäkuu 2026"}

    # Active during each day's judging window.
    assert _show_live_phase(show, now=_dt(2026, 6, 27, 12)) == "active"
    assert _show_live_phase(show, now=_dt(2026, 6, 28, 12)) == "active"

    # Paused through the Saturday→Sunday lull (evening, overnight, and the early
    # Sunday morning that rolls past midnight before judging resumes).
    assert _show_live_phase(show, now=_dt(2026, 6, 27, 22)) == "paused"
    assert _show_live_phase(show, now=_dt(2026, 6, 28, 3)) == "paused"

    # The first day's pre-dawn (show not started) and the final day's wind-down
    # (no following day) both stay active rather than reading as "continues".
    assert _show_live_phase(show, now=_dt(2026, 6, 27, 5)) == "active"
    assert _show_live_phase(show, now=_dt(2026, 6, 28, 22)) == "active"


def test_show_live_phase_evening_stall_only_on_non_final_day():
    show = {"date": "27.-28.06.", "month": "kesäkuu 2026"}

    # Saturday evening (>= 17:00) with no new results for over two hours: the day
    # has wound down early and Sunday follows, so it reads as "paused".
    stalled = _dt(2026, 6, 27, 18)
    assert _show_live_phase(
        show, now=stalled, last_result_at=_dt(2026, 6, 27, 15).timestamp()
    ) == "paused"

    # A fresh result keeps it active.
    assert _show_live_phase(
        show, now=stalled, last_result_at=_dt(2026, 6, 27, 17, 40).timestamp()
    ) == "active"

    # Midday stalls (before the evening floor) never flip — a slow big-breed ring
    # or crawler lag must not fake a pause during active judging.
    assert _show_live_phase(
        show, now=_dt(2026, 6, 27, 13), last_result_at=_dt(2026, 6, 27, 9).timestamp()
    ) == "active"

    # On the final day an evening stall stays active (the show is wrapping up, not
    # continuing); completion is handled separately by the live-finish grace.
    assert _show_live_phase(
        show, now=_dt(2026, 6, 28, 18), last_result_at=_dt(2026, 6, 28, 15).timestamp()
    ) == "active"


def test_show_live_phase_three_day_and_single_day():
    three_day = {"date": "26.-28.06.", "month": "kesäkuu 2026"}  # Fri→Sun
    assert _show_live_phase(three_day, now=_dt(2026, 6, 26, 22)) == "paused"  # Fri night
    assert _show_live_phase(three_day, now=_dt(2026, 6, 27, 22)) == "paused"  # Sat night
    assert _show_live_phase(three_day, now=_dt(2026, 6, 28, 22)) == "active"  # Sun (final)

    single = {"date": "28.06.", "month": "kesäkuu 2026"}
    assert _show_live_phase(single, now=_dt(2026, 6, 28, 22)) == "active"
    assert _show_live_phase(single, now=_dt(2026, 6, 28, 3)) == "active"


def test_result_doc_last_result_at_uses_result_bearing_breeds():
    doc = {
        "completed_breeds": {
            "5:3": {"result_count": 5, "updated_at": 1000.0},
            "5:4": {"result_count": 0, "updated_at": 9000.0},  # probed, no results
            "9:296": {"result_count": 2, "updated_at": 1500.0},
        },
    }
    assert _result_doc_last_result_at(doc) == 1500.0
    assert _result_doc_last_result_at({}) is None
    assert _result_doc_last_result_at({"completed_breeds": {"5:4": {"result_count": 0}}}) is None


def test_show_stats_multiday_night_reads_as_paused(monkeypatch, client):
    seed_index_show("13762", {
        "title": "27.-28.06.2026 Turku KV",
        "name": "Turku KV",
        "date": "27.-28.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "villakoira", "count": 1, "group": "9", "breed_id": "296", "has_results": True},
        ],
    })
    dog_store._save_result_cache_doc(13762, {
        "status": "running",
        "results": [{}, {}],
        "completed_breeds": {"5:3": {"result_count": 2, "updated_at": 1000.0}},
    })

    # Saturday night, with Sunday still to come: nightly hiatus, not "Käynnissä".
    night = _dt(2026, 6, 27, 22)
    monkeypatch.setattr(dog_indexing, "_stats_now_for_today", lambda today: night)

    stats = dog_indexing._show_stats_from_index(
        13762,
        show={"id": 13762, "date": "27.-28.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 27),
    )

    assert stats["show_state"] == "live"
    assert stats["is_live"] is False
    assert stats["is_paused"] is True
    # Today's results are still reported overnight so the row keeps "n/N tulosta".
    assert stats["entry_count"] == 3
    assert stats["result_count"] == 2


def test_show_stats_ignore_empty_single_breed_specialty_cache(client):
    seed_index_show("14079", {
        "title": "20.06.2026 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(14079),
        "breeds": [
            {
                "name": "bostoninterrieri",
                "count": 26,
                "group": "9",
                "breed_id": "296",
                "has_results": False,
            },
        ],
    })
    dog_store._save_result_cache_doc(14079, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 14079,
        "status": "complete",
        "title": "20.06.2026 Bostoninterrieri",
        "source_url": dog_showlink._source_url(14079),
        "started_at": 1000,
        "updated_at": 1001,
        "cached_at": 1001,
        "total_breeds": 0,
        "completed_breeds": {},
        "failed_breeds": {},
        "results": [],
    })

    stats = dog_indexing._show_stats_from_index(
        14079,
        show={"id": 14079, "date": "20.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 20),
    )

    assert stats["is_live"] is True
    assert stats["entry_count"] == 26
    assert stats["result_breed_count"] == 1
    assert "result_count" not in stats


def test_get_shows_queues_stale_live_result_refresh(monkeypatch, client):
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    show = {
        "id": 13771,
        "date": "20.-21.06.",
        "name": "Jyväskylä KV",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
    }
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
        "updated_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "breeds": [
            { "name": "basenji", "count": 2066, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })
    dog_store._save_result_cache_doc(13771, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_showlink._source_url(13771),
        "started_at": now - 200,
        "updated_at": now - 180,
        "cached_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 106}},
        "failed_breeds": {},
        "results": [{"name": f"Dog {idx}", "breedName": "basenji"} for idx in range(106)],
    })
    monkeypatch.setattr(dog_module, "_get_show_list", lambda: [show])
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)

    resp = client.get("/api/dog/shows")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["shows"][0]["stats"]["result_count"] == 106
    jobs = dog_store._load_result_jobs()["jobs"]
    assert jobs["13771"]["state"] == "queued"
    assert jobs["13771"]["reason"] == "live-list-refresh"


def test_show_result_availability_waits_until_show_morning():
    show = {"date": "20.06.", "month": "kesäkuu 2026"}

    future = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 17, 12, 0),
    )
    early_morning = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 5, 59),
    )
    show_day = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 6, 0),
    )
    evening = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 21, 0),
    )

    assert future["can_fetch"] is False
    assert future["reason"] == "future_show"
    assert future["available_from_iso"] == "2026-06-20T06:00:00"
    assert early_morning["can_fetch"] is False
    assert early_morning["reason"] == "show_morning"
    assert show_day["can_fetch"] is True
    assert show_day["reason"] == "show_day"
    assert evening["can_fetch"] is False
    assert evening["reason"] == "show_night"
    assert evening["show_state"] == "live"


def test_show_result_availability_pauses_between_show_days():
    """A multi-day live show goes quiet overnight (21:00–06:00) between days."""
    show = {"date": "20.-21.06.", "month": "kesäkuu 2026"}

    night = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 23, 30),
    )
    next_morning_early = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 21, 5, 0),
    )
    next_day = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 21, 9, 0),
    )

    assert night["can_fetch"] is False
    assert night["reason"] == "show_night"
    assert night["show_state"] == "live"
    assert next_morning_early["can_fetch"] is False
    assert next_morning_early["reason"] == "show_morning"
    assert next_morning_early["show_state"] == "live"
    assert next_day["can_fetch"] is True
    assert next_day["reason"] == "show_day"

def test_show_result_availability_handles_showlink_today_section():
    show = {"date": "20.-21.06.", "month": "Tänään"}

    availability = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 12, 0),
    )

    assert _show_is_recent(show, today=datetime.date(2026, 6, 20)) is True
    assert availability["can_fetch"] is True
    assert availability["show_state"] == "live"
    assert availability["start_date"] == "2026-06-20"
    assert availability["end_date"] == "2026-06-21"


@patch("app.dog_show.showlink._SESSION.get")
def test_get_shows_does_not_show_stats_for_empty_index_entries(mock_get, client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "updated_at": 1781431200,
        "breeds": [],
    })
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_LIST_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "stats" not in data["shows"][0]


@patch("app.dog_show.showlink._SESSION.get")
def test_get_show_detail(mock_get, client):
    """The crawler indexes a specialty detail page; the endpoint serves the
    indexed copy (the web tier itself never fetches Showlink detail pages)."""
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    dog_crawler._update_index_show({"id": 14042, "name": "Basenji", "month": "kes\u00e4kuu 2026"})
    mock_get.reset_mock()

    resp = client.get("/api/dog/shows/14042")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == 14042
    assert data["title"] == "14.06.2026 Basenji"
    assert len(data["breeds"]) == 2
    assert data["breeds"][0]["name"] == "basenji"
    assert data["breeds"][0]["count"] == 78
    assert data["breeds"][0]["group"] == "5"
    assert data["breeds"][0]["breed_id"] == "3"
    assert data["breeds"][0]["has_results"] is True
    assert data["breeds"][0]["source_url"].endswith("Id=14042&R=5&RO=3")
    assert data["breeds"][1]["has_results"] is False
    assert data["source_url"].endswith("Id=14042")
    assert data["fetched_at_iso"]
    mock_get.assert_not_called()


def test_show_detail_not_indexed_returns_not_ready(client):
    resp = client.get("/api/dog/shows/14042")
    assert resp.status_code == 425
    data = resp.get_json()
    assert data["status"] == "not_indexed"
    assert data["message"]


@patch("app.dog_show.showlink._SESSION.get")
def test_show_detail_uses_persisted_index_without_fetching(mock_get, client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(14042),
        "updated_at": 1781431200,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" },
        ],
    })

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "14.06.2026 Basenji"
    assert data["breeds"][0]["name"] == "basenji"
    assert data["breeds"][0]["judge"] == "Paula Steele"
    assert data["cache"]["status"] == "indexed"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_show_detail_includes_live_breed_result_progress_and_queues_refresh(mock_get, monkeypatch, client):
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
        "updated_at": now,
        "breeds": [
            { "name": "basenji", "count": 26, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": True },
        ],
    })
    dog_store._save_result_cache_doc(13771, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_showlink._source_url(13771),
        "started_at": now - 240,
        "updated_at": now - 180,
        "cached_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 2,
        "completed_breeds": {
            "5:3": {"name": "basenji", "result_count": 5, "updated_at": now - 30},
            "5:4": {"name": "ibizanpodenco", "result_count": 0, "updated_at": now - 60},
        },
        "failed_breeds": {},
        "results": [
            {"name": f"Basenji {idx}", "breedName": "basenji", "breedGroup": "5", "breedId": "3"}
            for idx in range(5)
        ],
    })
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)

    resp = client.get("/api/dog/shows/13771")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breeds"][0]["result_count"] == 5
    assert data["breeds"][0]["result_total_count"] == 26
    assert data["breeds"][0]["result_progress"]["rated_count"] == 5
    assert data["breeds"][0]["result_updated_at_iso"] == _utc_iso(now - 30)
    assert data["breeds"][1]["result_count"] == 0
    assert data["breeds"][1]["result_total_count"] == 12
    jobs = dog_store._load_result_jobs()["jobs"]
    assert jobs["13771"]["state"] == "queued"
    assert jobs["13771"]["reason"] == "live-detail-refresh"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_show_detail_serves_stale_flagless_index_without_fetching(mock_get, monkeypatch, client):
    """A stale live index with no result flags is still served as-is by the web
    tier; refreshing the breed list against Showlink is the crawler's job
    (see test_crawl_result_cache_refreshes_stale_recent_index_before_fetching_results)."""
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(14042),
        "updated_at": 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": False },
        ],
    })
    monkeypatch.setattr(dog_indexing, "_is_show_recent_by_id", lambda show_id: True)
    monkeypatch.setattr(
        dog_indexing,
        "_show_result_availability_for_id",
        lambda show_id, now=None: {"can_fetch": True, "show_state": "live"},
    )

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["cache"]["status"] == "indexed"
    # Single-breed show inside the fetch window stays openable via the probe mark.
    assert data["breeds"][0]["has_results"] is True
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_show_detail_marks_single_breed_specialty_as_result_fetchable(mock_get, client):
    seed_index_show("14079", {
        "title": "20.06.2000 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2000",
        "source_url": dog_showlink._source_url(14079),
        "updated_at": 1781952360,
        "breeds": [
            {
                "name": "bostoninterrieri",
                "count": 26,
                "group": "9",
                "breed_id": "296",
                "has_results": False,
            },
        ],
    })

    resp = client.get("/api/dog/shows/14079")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breeds"][0]["has_results"] is True
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_judge_sweep_folds_zero_result_cache_judges_into_index(mock_get, client):
    """A judged breed that produced no result rows carries its judge only in the
    completed_breeds cache meta; the one-off sweep folds it into the index, and
    the read-only detail endpoint then serves it."""
    seed_index_show("13992", {
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "name": "Pertunmaa Pentunäyttely",
        "month": "heinäkuu 2025",
        "source_url": dog_showlink._source_url(13992),
        "updated_at": 1781431200,
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 1,
                "group": "8",
                "breed_id": "124",
                "has_results": True,
            },
        ],
    })
    dog_store._save_result_cache_doc(13992, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_showlink._source_url(13992),
        "cached_at": 1001,
        "completed_breeds": {
            "8:124": {
                "name": "sileäkarvainen noutaja",
                "result_count": 1,
                "judge": "Tarja Kolkka",
            },
        },
        "failed_breeds": {},
        "results": [],
    })

    with dog_db.session_scope() as session:
        assert dog_sqlstore.sweep_breed_judges_from_cache_meta(session) == 1

    resp = client.get("/api/dog/shows/13992")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breeds"][0]["judge"] == "Tarja Kolkka"
    assert dog_store._indexed_show("13992")["breeds"][0]["judge"] == "Tarja Kolkka"
    mock_get.assert_not_called()


def test_persist_show_detail_preserves_cached_result_flags(client):
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 26,
                "group": "8",
                "breed_id": "124",
                "has_results": False,
            },
        ],
    })
    dog_store._save_result_cache_doc(13771, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_showlink._source_url(13771),
        "started_at": 1,
        "updated_at": 2,
        "cached_at": 2,
        "total_breeds": 1,
        "completed_breeds": {
            "8:124": {
                "name": "sileäkarvainen noutaja",
                "result_count": 18,
                "judge": "Pietro Marino",
            },
        },
        "failed_breeds": {},
        "results": [],
    })

    dog_indexing._persist_show_detail_to_index(13771, {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_showlink._source_url(13771),
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 26,
                "group": "8",
                "breed_id": "124",
                "has_results": False,
            },
        ],
    }, 3)

    breed = dog_store._indexed_show("13771")["breeds"][0]
    assert breed["has_results"] is True
    assert breed["judge"] == "Pietro Marino"


@patch("app.dog_show.showlink._SESSION.get")
def test_crawler_reindex_preserves_captured_judges(mock_get, client):
    """A maintenance re-index parses the detail page, which never carries judges.
    The wholesale row replacement must fold the already-captured judges back in
    instead of wiping them until the next result crawl."""
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 78, "group": "5", "breed_id": "3",
             "has_results": True, "judge": "Paula Steele"},
        ],
    })
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    dog_crawler._update_index_show({"id": 14042, "name": "Basenji", "date": "14.06.", "month": "kesäkuu 2026"})

    breeds = dog_store._indexed_show("14042")["breeds"]
    assert breeds[0]["name"] == "basenji"
    assert breeds[0]["judge"] == "Paula Steele"
    assert breeds[0]["has_results"] is True


SAMPLE_GENERAL_SHOW_MAIN_HTML = """
<div id="divOtsikko">
    <h1>10.05.2026 Kouvola</h1>
</div>
<div id="divContent">
    <a href="/nayttelyt/Tulokset?Id=14025&R=3">FCI 3</a>
    <a href="/nayttelyt/Tulokset?Id=14025&R=5">FCI 5</a>
</div>
"""

SAMPLE_GENERAL_SHOW_GROUP_3_HTML = """
<div id="divOtsikko">
    <h1>10.05.2026 Kouvola</h1>
</div>
<table class="rotulistatable">
    <tr class="rotuluettelo">
        <td><a href="/nayttelyt/Tulokset?Id=14025&R=3&RO=166">australianterrieri</a></td>
        <td class="right">11</td>
        <td class="right"><i class="fa fa-check"></i></td>
    </tr>
</table>
"""

SAMPLE_GENERAL_SHOW_GROUP_5_HTML = """
<div id="divOtsikko">
    <h1>10.05.2026 Kouvola</h1>
</div>
<table class="rotulistatable">
    <tr class="rotuluettelo">
        <td><a href="/nayttelyt/Tulokset?Id=14025&R=5&RO=3">basenji</a></td>
        <td class="right">5</td>
        <td class="right"></td>
    </tr>
</table>
"""


SAMPLE_AGGREGATE_SHOW_MAIN_HTML = """
<div id="divOtsikko">
    <h1>14.06.2026 Kanakoirakerho</h1>
</div>
<div id="divContent">
    <div class="roturyhmatvalikko">
        <a href="/nayttelyt/Tulokset?Id=13934&R=R">Rotujen tulokset</a>
    </div>
    <div class="roturyhmatvalikko">
        <a href="/nayttelyt/Tulokset?Id=13934&R=BIS">BIS-tulokset</a>
    </div>
    <table class="tulostaulukko">
        <tr class="otsikko"><td colspan="3">Best in show</td></tr>
        <tr><td>1.</td><td>pointteri</td><td>Riekkokirhveen Hg Edda</td></tr>
    </table>
</div>
"""

SAMPLE_AGGREGATE_SHOW_BREEDS_HTML = """
<div id="divOtsikko">
    <h1>14.06.2026 Kanakoirakerho</h1>
</div>
<table class="rotulistatable">
    <tr class="rotuluettelo">
        <td><a href="/nayttelyt/Tulokset?Id=13934&R=7&RO=88">englanninsetteri</a></td>
        <td class="right">48</td>
        <td class="right"><i class="fa-solid fa-check"></i></td>
    </tr>
    <tr class="rotuluettelo">
        <td><a href="/nayttelyt/Tulokset?Id=13934&R=7&RO=90">gordoninsetteri</a></td>
        <td class="right">31</td>
        <td class="right"><i class="fa-solid fa-check"></i></td>
    </tr>
</table>
"""


@patch("app.dog_show.showlink._SESSION.get")
def test_get_show_detail_general(mock_get, client):
    """General all-breed pages link numeric FCI groups (R=1..10); the crawler
    walks them when indexing, and the endpoint serves the indexed breeds."""
    mock_resp_main = MagicMock()
    mock_resp_main.text = SAMPLE_GENERAL_SHOW_MAIN_HTML
    mock_resp_main.status_code = 200

    mock_resp_g3 = MagicMock()
    mock_resp_g3.text = SAMPLE_GENERAL_SHOW_GROUP_3_HTML
    mock_resp_g3.status_code = 200

    mock_resp_g5 = MagicMock()
    mock_resp_g5.text = SAMPLE_GENERAL_SHOW_GROUP_5_HTML
    mock_resp_g5.status_code = 200

    mock_get.side_effect = [mock_resp_main, mock_resp_g3, mock_resp_g5]

    dog_crawler._update_index_show({"id": 14025, "name": "Kouvola", "month": "toukokuu 2026"})
    mock_get.reset_mock()
    mock_get.side_effect = None

    resp = client.get("/api/dog/shows/14025")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == 14025
    assert data["title"] == "10.05.2026 Kouvola"
    assert len(data["breeds"]) == 2

    assert data["breeds"][0]["name"] == "australianterrieri"
    assert data["breeds"][0]["count"] == 11
    assert data["breeds"][0]["group"] == "3"
    assert data["breeds"][0]["breed_id"] == "166"
    assert data["breeds"][0]["has_results"] is True

    assert data["breeds"][1]["name"] == "basenji"
    assert data["breeds"][1]["count"] == 5
    assert data["breeds"][1]["group"] == "5"
    assert data["breeds"][1]["breed_id"] == "3"
    assert data["breeds"][1]["has_results"] is False
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_index_uses_aggregate_breed_results_link(mock_get, client):
    """BIS-focused specialty landing pages carry the real breed list under R=R;
    the crawler indexes through it and replaces a stale empty index entry."""
    seed_index_show("13934", {
        "title": "stale empty index",
        "name": "Kanakoirakerho",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [],
    })
    mock_resp_main = MagicMock()
    mock_resp_main.text = SAMPLE_AGGREGATE_SHOW_MAIN_HTML
    mock_resp_main.status_code = 200

    mock_resp_breeds = MagicMock()
    mock_resp_breeds.text = SAMPLE_AGGREGATE_SHOW_BREEDS_HTML
    mock_resp_breeds.status_code = 200

    mock_get.side_effect = [mock_resp_main, mock_resp_breeds]

    dog_crawler._update_index_show({"id": 13934, "name": "Kanakoirakerho", "date": "14.06.", "month": "kesäkuu 2026"})
    assert mock_get.call_args_list[1].args[0].endswith("Id=13934&R=R")
    mock_get.reset_mock()
    mock_get.side_effect = None

    resp = client.get("/api/dog/shows/13934")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "14.06.2026 Kanakoirakerho"
    assert len(data["breeds"]) == 2
    assert data["breeds"][0]["name"] == "englanninsetteri"
    assert data["breeds"][0]["count"] == 48
    assert data["breeds"][0]["group"] == "7"
    assert data["breeds"][0]["breed_id"] == "88"
    assert data["breeds"][0]["has_results"] is True
    assert data["breeds"][1]["name"] == "gordoninsetteri"
    assert len(dog_store._indexed_show("13934")["breeds"]) == 2
    assert "empty_breed_list_confirmed" not in dog_store._indexed_show("13934")
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_index_refreshes_unconfirmed_empty_index_entries(mock_get, monkeypatch):
    seed_index_show("14042", {
        "title": "stale empty index",
        "name": "Basenji",
        "date": "14.06.",
        "month": "tammikuu 2000",
        "breeds": [],
    })
    seed_index_show("14043", {
        "title": "already indexed",
        "name": "Villakoira erikoisnäyttely",
        "date": "15.06.",
        "month": "tammikuu 2000",
        "breeds": [
            {"name": "villakoira", "count": 1, "group": "9", "breed_id": "172", "has_results": True},
        ],
    })
    monkeypatch.setattr(dog_crawler.time, "sleep", lambda seconds: None)

    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    mock_resp_detail = MagicMock()
    mock_resp_detail.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp_detail.status_code = 200

    mock_get.side_effect = [mock_resp_list, mock_resp_detail]

    summary = dog_crawler.crawl_index_once(limit=1, delay=0)

    assert summary["updated"] == 1
    assert len(dog_store._indexed_show("14042")["breeds"]) == 2
    assert dog_store._indexed_show("14042")["breeds"][0]["name"] == "basenji"
    assert mock_get.call_args_list[1].args[0].endswith("Id=14042")


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_empty_index_once_repairs_only_empty_entries(mock_get, monkeypatch):
    seed_index_show("14042", {
        "title": "stale empty index",
        "name": "Basenji",
        "date": "14.06.",
        "month": "tammikuu 2000",
        "breeds": [],
    })
    seed_index_show("14043", {
        "title": "already indexed",
        "name": "Villakoira erikoisnäyttely",
        "date": "15.06.",
        "month": "tammikuu 2000",
        "breeds": [
            {"name": "villakoira", "count": 1, "group": "9", "breed_id": "172", "has_results": True},
        ],
    })
    monkeypatch.setattr(dog_crawler.time, "sleep", lambda seconds: None)

    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    mock_resp_detail = MagicMock()
    mock_resp_detail.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp_detail.status_code = 200

    mock_get.side_effect = [mock_resp_list, mock_resp_detail]

    summary = dog_crawler.crawl_empty_index_once(limit=10, delay=0)

    assert summary["updated"] == 1
    assert summary["empty_candidates"] == 1
    assert len(dog_store._indexed_show("14042")["breeds"]) == 2
    assert len(dog_store._indexed_show("14043")["breeds"]) == 1
    assert len(mock_get.call_args_list) == 2
    assert mock_get.call_args_list[1].args[0].endswith("Id=14042")


@patch("app.dog_show.showlink._SESSION.get")
def test_get_breed_results_from_whole_show_cache(mock_get, monkeypatch, client):
    """The breed endpoint serves from the crawled whole-show cache; the web tier
    never fetches Showlink result pages itself."""
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)
    seed_index_show("14042", {
        "title": "14.06.2024 Basenji", "name": "Basenji",
        "date": "14.06.", "month": "kesäkuu 2024",
        "source_url": dog_showlink._source_url(14042),
        "breeds": [
            {"name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True},
        ],
    })
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    summary = dog_result_cache.crawl_result_cache_for_show(14042, delay=0, source="test", workers=1)
    assert summary["status"] == "complete"
    mock_get.reset_mock()

    resp = client.get("/api/dog/shows/14042/results?group=5&breed=3")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["show_id"] == 14042
    assert data["breed"] == "basenji"
    assert data["judge"] == "Paula Steele"
    assert len(data["awards"]) == 1
    assert data["awards"][0]["type"] == "ROP"
    assert "Wazazi Tempting Fate" in data["awards"][0]["text"]

    assert len(data["results"]) == 1
    res = data["results"][0]
    assert res["number"] == 1
    assert res["name"] == "Ajibu You Are My Thrill"
    assert res["reg_url"] == "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI13442%2F26"
    assert res["grade"] == "KP"
    assert res["placement"] == 1
    assert res["awards"] == "ROP-pentu"
    assert res["critique"] == "5 months old, clearly needs time..."
    assert res["gender"] == "Urokset"
    assert res["class_name"] == "Pentuluokka 5-7 kk"
    assert data["source_url"].endswith("Id=14042&R=5&RO=3")
    assert data["fetched_at_iso"]
    assert data["cache"]["status"] == "show_all_results"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_uncached_breed_results_queue_job_and_return_not_ready(mock_get, monkeypatch, client):
    """A breed missing from the whole-show cache inside the fetch window queues a
    crawler job instead of fetching Showlink from the web worker."""
    seed_index_show("13763", {
        "title": "18.-19.04.2026 Vaasa KV", "name": "Vaasa KV",
        "date": "18.-19.04.", "month": "huhtikuu 2026",
        "breeds": [
            {"name": "sileäkarvainen noutaja", "count": 28, "group": "8", "breed_id": "124", "has_results": True},
        ],
    })

    resp = client.get("/api/dog/shows/13763/results?group=8&breed=124")

    assert resp.status_code == 425
    data = resp.get_json()
    assert data["status"] == "not_ready"
    assert data["reason"] == "cache_warming"
    assert data["message"]
    jobs = dog_store._load_result_jobs()["jobs"]
    assert jobs["13763"]["reason"] == "breed-request"
    mock_get.assert_not_called()


def test_parse_breed_results_strips_glued_judge_label():
    from bs4 import BeautifulSoup
    from app.dog_show.parsers import _parse_breed_results
    data = _parse_breed_results(
        BeautifulSoup(SAMPLE_BREED_RESULTS_GLUE_JUDGE_HTML, "html.parser"), 13763
    )
    assert data["judge"] == "Tarja Kolkka"


@patch("app.dog_show.showlink._SESSION.get")
def test_result_crawl_reads_floatleft_breed_header_and_backfills_index(mock_get, monkeypatch, client):
    """Floatleft-header breed pages parse via the crawl path; the capture folds
    the judge and result flag back into the breed index."""
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)
    seed_index_show("13771", {
        "title": "20.-21.06.2024 Jyväskylä KV", "name": "Jyväskylä KV",
        "date": "20.-21.06.", "month": "kesäkuu 2024",
        "source_url": dog_showlink._source_url(13771),
        "breeds": [
            {"name": "sileäkarvainen noutaja", "count": 26, "group": "8", "breed_id": "124", "has_results": True},
        ],
    })
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_FLOATLEFT_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    summary = dog_result_cache.crawl_result_cache_for_show(13771, delay=0, source="test", workers=1)
    assert summary["status"] == "complete"

    resp = client.get("/api/dog/shows/13771/results?group=8&breed=124")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breed"] == "sileäkarvainen noutaja"
    assert data["judge"] == "Pietro Marino"
    assert data["results"][0]["name"] == "Almanza Blast From The Past"
    assert dog_store._indexed_show("13771")["breeds"][0]["judge"] == "Pietro Marino"


@patch("app.dog_show.showlink._SESSION.get")
def test_future_breed_results_return_not_ready_without_fetching(mock_get, client):
    seed_index_show("15001", {
        "title": "20.06.2999 Future Show",
        "date": "20.06.",
        "month": "kesäkuu 2999",
        "breeds": [
            { "name": "basenji", "count": 4, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })

    resp = client.get("/api/dog/shows/15001/results?group=5&breed=3")

    assert resp.status_code == 425
    data = resp.get_json()
    assert data["status"] == "not_ready"
    assert data["reason"] == "future_show"
    assert data["availability"]["can_fetch"] is False
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_future_show_all_results_return_not_ready_without_queueing(mock_get, client):
    seed_index_show("15001", {
        "title": "20.06.2999 Future Show",
        "date": "20.06.",
        "month": "kesäkuu 2999",
        "breeds": [
            { "name": "basenji", "count": 4, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })

    resp = client.get("/api/dog/shows/15001/all-results")

    assert resp.status_code == 425
    data = resp.get_json()
    assert data["status"] == "not_ready"
    assert data["reason"] == "future_show"
    assert data["availability"]["can_fetch"] is False
    assert dog_store._load_result_jobs()["jobs"] == {}
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_show_all_results_missing_cache_queues_without_fetching(mock_get, client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": False },
        ],
    })

    resp = client.get("/api/dog/shows/14042/all-results")

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "warming"
    assert data["retry_after"] == dog_result_cache.RESULT_RETRY_AFTER_SECONDS
    assert data["progress"]["state"] == "queued"
    assert data["progress"]["total_breeds"] == 1
    assert "started" not in data  # web workers no longer warm caches themselves
    mock_get.assert_not_called()

    jobs = dog_store._load_result_jobs()
    assert jobs["jobs"]["14042"]["state"] == "queued"
    assert jobs["jobs"]["14042"]["reason"] == "user"


@patch("app.dog_show.showlink._SESSION.get")
def test_show_all_results_poll_does_not_refresh_running_job_clock(mock_get, monkeypatch, client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })
    old_updated_at = 100
    dog_store._save_result_jobs({
        "jobs": {
            "14042": {
                "show_id": 14042,
                "state": "running",
                "created_at": old_updated_at,
                "requested_at": old_updated_at,
                "updated_at": old_updated_at,
                "last_started_at": old_updated_at,
                "attempts": 1,
            },
        },
        "updated_at": old_updated_at,
    })
    monkeypatch.setattr(dog_store.time, "time", lambda: 1000)

    resp = client.get("/api/dog/shows/14042/all-results")

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "warming"
    assert data["progress"]["state"] == "running"
    jobs = dog_store._load_result_jobs()["jobs"]
    assert jobs["14042"]["state"] == "running"
    assert jobs["14042"]["requested_at"] == 1000
    assert jobs["14042"]["updated_at"] == old_updated_at
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_show_all_results_serves_persisted_cache_without_fetching(mock_get, client):
    seed_index_show("14042", {
        "title": "14.06.2000 Basenji",
        "month": "tammikuu 2000",
        "breeds": [
            { "name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })
    dog_store._save_result_cache_doc(14042, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "14.06.2000 Basenji",
        "source_url": dog_showlink._source_url(14042),
        "started_at": 1000,
        "updated_at": 1001,
        "cached_at": 1001,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "failed_breeds": {},
        "results": [
            {
                "number": 1,
                "name": "Ajibu You Are My Thrill",
                "grade": "KP",
                "breedName": "basenji",
                "breedGroup": "5",
                "breedId": "3",
                "breedObj": { "name": "basenji", "group": "5", "breed_id": "3" },
            },
        ],
    })

    resp = client.get("/api/dog/shows/14042/all-results")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["results"][0]["name"] == "Ajibu You Are My Thrill"
    assert data["cache"]["status"] == "complete"
    assert data["cache"]["total_breeds"] == 1
    mock_get.assert_not_called()


def test_live_result_cache_becomes_stale_after_two_minutes(monkeypatch, client):
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

    fresh_doc = {
        "status": "complete",
        "cached_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL + 1,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "results": [{"name": "Fresh Dog"}],
    }
    stale_doc = dict(fresh_doc, cached_at=now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1)

    assert dog_result_cache._result_cache_doc_is_fresh(13771, fresh_doc, now=now) is True
    assert dog_result_cache._result_cache_doc_is_fresh(13771, stale_doc, now=now) is False


def test_live_result_cache_settles_when_terminal_confirmed(monkeypatch, client):
    """A live all-breed show keeps polling until its terminal award (every
    group's RYP-1 + the main BIS-1) is captured AND confirmed stable by a
    following pass; only then does the cache stop fast-polling."""
    now = _hel_timestamp(2026, 6, 20, 18)
    seed_index_show("13771", {
        "title": "20.06.2026 Jyväskylä KV",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
        ],
    })
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

    base_doc = {
        "status": "complete",
        "cached_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 2,
        "completed_breeds": {"5:3": {"result_count": 1}, "10:7": {"result_count": 1}},
        "results": [
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1, BIS-1"},
            {"breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
        ],
    }
    # Terminal captured but not yet confirmed stable → keep polling.
    still_confirming = dict(base_doc)
    # Confirmed by a following pass → settle.
    confirmed = dict(base_doc, terminal_target_met=True, terminal_confirmed=True)

    assert dog_result_cache._result_cache_doc_is_fresh(13771, still_confirming, now=now) is False
    assert dog_result_cache._result_cache_doc_is_fresh(13771, confirmed, now=now) is True


def test_live_result_cache_keeps_polling_while_a_group_ryp_missing(monkeypatch, client):
    """BIS-1 captured but one result-bearing group has no RYP-1 yet — the
    finals aren't fully published, so the cache must keep polling."""
    now = _hel_timestamp(2026, 6, 20, 18)
    seed_index_show("13771", {
        "title": "20.06.2026 Jyväskylä KV",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
        ],
    })
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)
    doc = {
        "status": "complete",
        "cached_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 2,
        "completed_breeds": {"5:3": {"result_count": 1}, "10:7": {"result_count": 1}},
        # group 5 has RYP-1 and BIS-1, group 10 has only ROP — its RYP is pending.
        "results": [
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1, BIS-1"},
            {"breedGroup": "10", "breedId": "7", "awards": "SA, ROP"},
        ],
        "terminal_confirmed": True,  # even a stale confirmation can't settle it
    }
    assert dog_result_cache._result_cache_doc_is_fresh(13771, doc, now=now) is False


def test_live_show_stats_flip_past_when_terminal_confirmed(client):
    noon = _hel_timestamp(2026, 6, 20, 12)
    seed_index_show("13771", {
        "title": "20.06.2026 Jyväskylä KV",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
        ],
    })
    dog_store._save_result_cache_doc(13771, {
        "status": "complete",
        "cached_at": noon - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 2,
        "completed_breeds": {"5:3": {"result_count": 1}, "10:7": {"result_count": 1}},
        "results": [
            {"name": "BIS Dog", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1, BIS-1"},
            {"name": "Group10", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
        ],
        "terminal_target_met": True,
        "terminal_confirmed": True,
    })

    stats = dog_indexing._show_stats_from_index(
        13771,
        show={"id": 13771, "date": "20.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 20),
    )

    assert stats["show_state"] == "past"
    assert stats["is_live"] is False
    assert stats["live_finished_by"] == "bis"
    assert "result_count" not in stats


def test_live_show_stats_flip_past_on_confirmed_entry_completion(client):
    """A finals-less show (single breed, no BIS) settles on entry completion,
    once the following pass confirms the results stopped changing."""
    noon = _hel_timestamp(2026, 6, 20, 12)
    seed_index_show("14079", {
        "title": "20.06.2026 Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "bostoninterrieri", "count": 26, "group": "9", "breed_id": "296", "has_results": True},
        ],
    })
    dog_store._save_result_cache_doc(14079, {
        "status": "complete",
        "cached_at": noon - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 1,
        "completed_breeds": {"9:296": {"name": "bostoninterrieri", "result_count": 26}},
        "results": [{"name": f"Boston {idx}", "breedGroup": "9", "breedId": "296",
                     "breedName": "bostoninterrieri"} for idx in range(26)],
        "terminal_target_met": True,
        "terminal_confirmed": True,
    })

    stats = dog_indexing._show_stats_from_index(
        14079,
        show={"id": 14079, "date": "20.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 20),
    )

    assert stats["show_state"] == "past"
    assert stats["is_live"] is False
    assert stats["live_finished_by"] == "entries"
    assert "result_count" not in stats
    assert dog_result_cache._result_cache_doc_is_fresh(14079, dog_store._load_result_cache_doc(14079), now=noon) is True


def test_live_show_stats_stay_live_until_main_bis(client):
    """An all-breed show crowns junior/veteran/group finals and the main Best in
    Show after every breed ring is judged. Entry completion alone (with BIS-1
    still pending) must not flip the stats to "done" — that shut shows like
    Turku KV / Rovaniemi KV down while only BIS JUN/VET had happened."""
    noon = _hel_timestamp(2026, 6, 20, 12)
    seed_index_show("13762", {
        "title": "20.06.2026 Turku KV",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "afgaaninvinttikoira", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
        ],
    })
    dog_store._save_result_cache_doc(13762, {
        "status": "complete",
        "cached_at": noon - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 2,
        "completed_breeds": {
            "5:3": {"name": "basenji", "result_count": 2},
            "10:7": {"name": "afgaaninvinttikoira", "result_count": 2},
        },
        # Only junior/veteran BIS so far — the group RYP and main BIS-1 are still
        # to come, so even a (stale) confirmation flag can't settle it.
        "results": [
            {"name": "Junior", "breedGroup": "10", "breedId": "7", "awards": "SA, JUN ROP, BIS JUN-1"},
            {"name": "Veteran", "breedGroup": "5", "breedId": "3", "awards": "SA, VET ROP, BIS VET-1"},
            {"name": "C", "breedGroup": "5", "breedId": "3", "awards": "SA"},
            {"name": "D", "breedGroup": "10", "breedId": "7", "awards": "EH"},
        ],
        "terminal_confirmed": True,
    })

    stats = dog_indexing._show_stats_from_index(
        13762,
        show={"id": 13762, "date": "20.06.", "month": "kesäkuu 2026"},
        today=datetime.date(2026, 6, 20),
    )

    assert stats["show_state"] == "live"
    assert stats["is_live"] is True
    assert "live_finished_by" not in stats


def test_all_breed_cache_keeps_polling_until_main_bis(monkeypatch, client):
    """All-breed shows decide group finals + Best in Show after every breed ring
    is judged, so entry completion must not settle the cache before BIS-1 and
    every group's RYP-1 are captured and confirmed."""
    noon = _hel_timestamp(2026, 6, 20, 14)
    # Breeds span two FCI groups -> an all-breed show that crowns a main BIS.
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "afgaaninvinttikoira", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
        ],
    })
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

    # Every breed ring is judged, but the only finals so far are junior/group
    # placements -- no main BIS, and group 10 has no RYP-1 yet.
    no_main_bis = {
        "status": "complete",
        "cached_at": noon - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 2,
        "completed_breeds": {
            "5:3": {"name": "basenji", "result_count": 2},
            "10:7": {"name": "afgaaninvinttikoira", "result_count": 2},
        },
        "results": [
            {"name": "Junior", "breedGroup": "10", "breedId": "7", "awards": "SA, JUN ROP, BIS JUN-1"},
            {"name": "Group", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1"},
            {"name": "C", "breedGroup": "5", "breedId": "3", "awards": "SA"},
            {"name": "D", "breedGroup": "10", "breedId": "7", "awards": "EH"},
        ],
    }
    # For a multi-day show, the terminal can only be met on the final day.
    with_main_bis = dict(
        no_main_bis,
        cached_at=_hel_timestamp(2026, 6, 21, 14) - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        terminal_target_met=True,
        terminal_confirmed=True,
        results=[
            dict(no_main_bis["results"][0]),
            dict(no_main_bis["results"][1], awards="SA, ROP, RYP-1, BIS-1"),
            {"name": "G10", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
            *no_main_bis["results"][2:],
        ],
    )

    indexed_breeds = dog_store._indexed_show("13771")["breeds"]
    assert dog_finals.analyze(no_main_bis, indexed_breeds)["expects_finals"] is True
    # Entry completion alone must not settle an all-breed show without BIS-1.
    assert dog_result_cache._result_cache_doc_is_fresh(13771, no_main_bis, now=noon) is False
    # Once BIS-1 + every group's RYP-1 land and are confirmed on the final day,
    # the cache settles.
    assert dog_result_cache._result_cache_doc_is_fresh(
        13771, with_main_bis, now=_hel_timestamp(2026, 6, 21, 14)
    ) is True


def test_show_stats_cache_decouples_polling_from_result_doc_reads(monkeypatch, client):
    """A live show's stats reconstruct its whole-show result doc from SQLite. The
    stats path must load it at most once per compute, and the short-lived cache
    must serve repeat polls without touching SQLite again."""
    breeds = [
        {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
    ]
    seed_index_show("13950", {
        "title": "28.06.2026 Show", "date": "28.06.", "month": "kesäkuu 2026", "breeds": breeds,
    })
    dog_store._save_result_cache_doc(13950, {
        "version": dog_result_cache.RESULT_CACHE_VERSION, "show_id": 13950, "status": "complete",
        "cached_at": 1, "updated_at": 1, "total_breeds": 2,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1},
                             "10:7": {"name": "afgaani", "result_count": 1}},
        "failed_breeds": {},
        "results": [
            {"name": "A", "breedGroup": "5", "breedId": "3", "awards": "SA"},
            {"name": "B", "breedGroup": "10", "breedId": "7", "awards": "SA"},
        ],
    })
    monkeypatch.setattr(dog_indexing, "_show_date_state", lambda show, today=None: "live")
    monkeypatch.setattr(dog_indexing, "_show_live_phase", lambda *a, **k: "active")
    monkeypatch.setattr(dog_indexing, "_show_result_availability",
                        lambda show, now=None: {"show_state": "live", "can_fetch": True,
                                                "morning_hour": 6, "evening_hour": 21})
    # The live/settle decision now runs through _result_live_plan; keep this show
    # live so the test exercises the stats cache, not the terminal logic.
    monkeypatch.setattr(dog_indexing, "_result_live_plan",
                        lambda *a, **k: {"phase": "live", "expects_finals": True})
    calls = {"n": 0}
    real_load = dog_indexing._load_result_cache_doc
    monkeypatch.setattr(dog_indexing, "_load_result_cache_doc",
                        lambda sid: (calls.__setitem__("n", calls["n"] + 1), real_load(sid))[1])

    # First production poll: computes, loading the result doc exactly once (the
    # redundant second load via _result_count_from_cache_doc is gone).
    s1 = dog_indexing._show_stats_from_index(13950)
    assert s1 is not None and s1["is_live"] is True and s1["result_count"] == 2
    assert calls["n"] == 1

    # Repeat poll within TTL: served from cache, no further SQLite read.
    s2 = dog_indexing._show_stats_from_index(13950)
    assert s2 is s1
    assert calls["n"] == 1

    # An explicit `today` (tests / deterministic callers) bypasses the cache.
    dog_indexing._show_stats_from_index(13950, today=datetime.date(2026, 6, 28))
    assert calls["n"] == 2


def test_finals_resweep_targets_missing_ryp_groups_then_bis_finalists():
    """The re-sweep is structural, not a blind rotation: while a group still
    lacks RYP-1 it re-checks that group's ROP winners; once every group has
    RYP-1 but the main BIS is missing, it re-checks exactly the RYP-1 winners
    (the BIS finalists)."""
    breeds = [
        {"name": "a", "group": "5", "breed_id": "3"},
        {"name": "b", "group": "6", "breed_id": "9"},
        {"name": "c", "group": "7", "breed_id": "1"},
    ]
    completed = {"5:3": {}, "6:9": {}, "7:1": {}}

    def keys(selected):
        return sorted((b["group"], b["breed_id"]) for b in selected)

    # Group 5 has its RYP-1; groups 6 and 7 have ROP but no RYP-1 yet.
    doc = {"results": [
        {"breedGroup": "5", "breedId": "3", "awards": "ROP, RYP-1"},
        {"breedGroup": "6", "breedId": "9", "awards": "ROP"},
        {"breedGroup": "7", "breedId": "1", "awards": "ROP"},
    ]}
    analysis = dog_finals.analyze(doc, [dict(b, count=2) for b in breeds])
    # Only the missing-RYP groups' ROP breeds are candidates (5 already has RYP-1).
    assert keys(dog_result_cache._finals_resweep_breeds(breeds, completed, doc, analysis)) == [("6", "9"), ("7", "1")]

    # Every group now has RYP-1 but the main BIS-1 is still missing → re-check the
    # RYP-1 winners (the finalists), not every breed.
    doc2 = {"results": [
        {"breedGroup": "5", "breedId": "3", "awards": "ROP, RYP-1"},
        {"breedGroup": "6", "breedId": "9", "awards": "ROP, RYP-1"},
        {"breedGroup": "7", "breedId": "1", "awards": "ROP, RYP-1"},
    ]}
    analysis2 = dog_finals.analyze(doc2, [dict(b, count=2) for b in breeds])
    assert keys(dog_result_cache._finals_resweep_breeds(breeds, completed, doc2, analysis2)) == [("5", "3"), ("6", "9"), ("7", "1")]


def _seed_live_two_breed_show(show_id, *, captured, results, extra_breeds=None):
    """Index a live two-FCI-group show and persist a complete result cache that
    captured `captured` breed keys with `results` rows. Returns the breed list."""
    breeds = [
        {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
    ] + (extra_breeds or [])
    seed_index_show(str(show_id), {
        "title": f"28.06.2026 Show {show_id}",
        "date": "28.06.",
        "month": "kesäkuu 2026",
        "breeds": breeds,
    })
    dog_store._save_result_cache_doc(show_id, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": show_id,
        "status": "complete",
        "title": f"Show {show_id}",
        "source_url": dog_showlink._source_url(show_id),
        "started_at": 1,
        "updated_at": 1,
        "cached_at": 1,
        "total_breeds": len(breeds),
        "completed_breeds": {key: {"name": key, "result_count": 1} for key in captured},
        "failed_breeds": {},
        "results": results,
    })
    return breeds


def _patch_live_refresh(monkeypatch, show_id, detail_breeds, fetcher):
    live = {"show_state": "live", "can_fetch": True, "morning_hour": 6, "evening_hour": 21}
    monkeypatch.setattr(dog_result_cache, "_show_result_availability_for_id", lambda sid, now=None: live)
    # The crawl's fetch window / finals-hunt gating reads the live plan; force it
    # live so these fixed-date fixtures behave as an in-progress show.
    monkeypatch.setattr(dog_result_cache, "_result_live_plan_for_id",
                        lambda sid, doc=None, now=None: {
                            "phase": "live", "can_fetch": True,
                            "ttl": dog_result_cache.RESULT_CACHE_LIVE_TTL})
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda sid: True)
    monkeypatch.setattr(dog_result_cache, "_show_detail_for_result_cache", lambda sid: {
        "id": show_id,
        "title": f"Show {show_id}",
        "source_url": dog_showlink._source_url(show_id),
        "breeds": detail_breeds,
    })
    monkeypatch.setattr(dog_result_cache, "_fetch_breed_results_for_show_cache", fetcher)


def test_live_refresh_fetches_only_newly_judged_breeds(monkeypatch, client):
    """Captured breeds are immutable, so a live refresh re-fetches only the breed
    that newly gained results — not the whole show."""
    breeds = _seed_live_two_breed_show(
        13900,
        captured=["5:3"],
        results=[{"name": "Basenji Dog", "breedName": "basenji", "breedGroup": "5", "breedId": "3"}],
    )
    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        return {
            "breed": breed,
            "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}], "awards": []},
            "mapped_results": [{
                "name": f"Dog-{key}", "breedName": breed["name"],
                "breedGroup": breed["group"], "breedId": breed["breed_id"], "awards": "SA",
            }],
            "fetched_at": 2.0,
        }

    _patch_live_refresh(monkeypatch, 13900, breeds, fake_fetch)

    summary = dog_result_cache.crawl_result_cache_for_show(13900, source="test", workers=1)

    assert summary["status"] == "complete"
    assert fetched == ["10:7"]  # only the uncaptured breed, not basenji
    doc = dog_store._load_result_cache_doc(13900)
    assert {r["name"] for r in doc["results"]} == {"Basenji Dog", "Dog-10:7"}


def test_live_refresh_with_all_breeds_captured_skips_fetch_and_row_rewrite(monkeypatch, client):
    """When nothing new is judged and no main BIS is owed (single-group show), a
    live refresh fetches no breed pages and only rewrites the header — never the
    result rows."""
    breeds = [
        {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
    ]
    seed_index_show("13901", {
        "title": "28.06.2026 Basenji", "date": "28.06.", "month": "kesäkuu 2026", "breeds": breeds,
    })
    dog_store._save_result_cache_doc(13901, {
        "version": dog_result_cache.RESULT_CACHE_VERSION, "show_id": 13901, "status": "complete",
        "title": "Basenji", "source_url": dog_showlink._source_url(13901),
        "started_at": 1, "updated_at": 1, "cached_at": 1, "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "failed_breeds": {},
        "results": [{"name": "Basenji Dog", "breedName": "basenji", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP"}],
    })
    fetched = []
    _patch_live_refresh(monkeypatch, 13901, breeds, lambda sid, breed: fetched.append(breed))

    calls = {"doc": 0, "header": 0}
    monkeypatch.setattr(dog_result_cache, "_save_result_cache_doc", lambda sid, doc: calls.__setitem__("doc", calls["doc"] + 1))
    monkeypatch.setattr(dog_result_cache, "_save_result_cache_header", lambda sid, doc: calls.__setitem__("header", calls["header"] + 1))

    summary = dog_result_cache.crawl_result_cache_for_show(13901, source="test", workers=1)

    assert summary["status"] == "complete"
    assert fetched == []          # no breed pages fetched
    assert calls["doc"] == 0      # result rows were NOT rewritten
    assert calls["header"] == 1   # only the header/meta was refreshed


def test_finals_resweep_recaptures_ryp1_winners_until_main_bis(monkeypatch, client):
    """All breeds captured with their group RYP-1 but no BIS-1 yet: the refresh
    re-checks exactly the RYP-1 winners (the BIS finalists) and one of them gains
    BIS-1 — without duplicating rows."""
    breeds = _seed_live_two_breed_show(
        13902,
        captured=["5:3", "10:7"],
        results=[
            {"name": "Afgaani", "breedName": "afgaani", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
            {"name": "Basenji", "breedName": "basenji", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1"},
        ],
    )
    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        awards = "SA, ROP, RYP-1, BIS-1" if key == "5:3" else "SA, ROP, RYP-1"
        return {
            "breed": breed,
            "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}], "awards": []},
            "mapped_results": [{
                "name": f"Winner-{key}", "breedName": breed["name"],
                "breedGroup": breed["group"], "breedId": breed["breed_id"], "awards": awards,
            }],
            "fetched_at": 2.0,
        }

    _patch_live_refresh(monkeypatch, 13902, breeds, fake_fetch)

    summary = dog_result_cache.crawl_result_cache_for_show(13902, source="test", workers=1)

    assert summary["status"] == "complete"
    assert set(fetched) == {"5:3", "10:7"}  # both RYP-1 winners re-checked for the BIS
    doc = dog_store._load_result_cache_doc(13902)
    # Rows were replaced, not duplicated: still one row per breed.
    assert len(doc["results"]) == 2
    assert dog_finals.analyze(doc, breeds)["has_bis1"] is True


def test_finals_settles_only_after_terminal_confirmed_stable(monkeypatch, client):
    """After the terminal (all RYP-1 + BIS-1) is captured, the show is not
    confirmed until a following pass re-checks the finals-carrying breeds and
    nothing changes. A late BIS-4 landing on the confirm pass resets it; the pass
    after that confirms."""
    breeds = _seed_live_two_breed_show(
        13903,
        captured=["5:3", "10:7", "6:1", "7:2"],
        results=[
            {"name": "Basenji", "breedName": "basenji", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1"},
            {"name": "Afgaani", "breedName": "afgaani", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
            {"name": "Beagle", "breedName": "beagle", "breedGroup": "6", "breedId": "1", "awards": "SA, ROP, RYP-1"},
            {"name": "Collie", "breedName": "collie", "breedGroup": "7", "breedId": "2", "awards": "SA, ROP, RYP-1"},
        ],
        extra_breeds=[
            {"name": "beagle", "count": 2, "group": "6", "breed_id": "1", "has_results": True},
            {"name": "collie", "count": 2, "group": "7", "breed_id": "2", "has_results": True},
        ],
    )
    # BIS-1 is on 5:3 from the first pass; BIS-4 lands on 7:2 only from the 2nd
    # re-fetch of that breed (a late finals placement).
    fetch_counts = {}

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetch_counts[key] = fetch_counts.get(key, 0) + 1
        awards = "SA, ROP, RYP-1"
        if key == "5:3":
            awards = "SA, ROP, RYP-1, BIS-1"
        elif key == "7:2" and fetch_counts[key] >= 2:
            awards = "SA, ROP, RYP-1, BIS-4"
        return {
            "breed": breed,
            "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}], "awards": []},
            "mapped_results": [{
                "name": f"Winner-{key}", "breedName": breed["name"],
                "breedGroup": breed["group"], "breedId": breed["breed_id"], "awards": awards,
            }],
            "fetched_at": 2.0,
        }

    _patch_live_refresh(monkeypatch, 13903, breeds, fake_fetch)
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda *a, **k: False)

    def tokens():
        doc = dog_store._load_result_cache_doc(13903)
        return {t.strip().upper() for r in doc["results"]
                for t in str(r.get("awards") or "").split(",") if t.strip()}

    # Pass 1: BIS-1 lands; terminal met but not yet confirmed.
    dog_result_cache.crawl_result_cache_for_show(13903, source="test", workers=1)
    assert "BIS-1" in tokens()
    assert dog_store._load_result_cache_doc(13903).get("terminal_confirmed") is False

    # Pass 2: re-checks the finals breeds; the late BIS-4 lands and resets confirmation.
    dog_result_cache.crawl_result_cache_for_show(13903, source="test", workers=1)
    assert "BIS-4" in tokens()
    assert dog_store._load_result_cache_doc(13903).get("terminal_confirmed") is False

    # Pass 3: nothing changes → confirmed stable.
    dog_result_cache.crawl_result_cache_for_show(13903, source="test", workers=1)
    doc = dog_store._load_result_cache_doc(13903)
    assert {"BIS-1", "BIS-4"} <= tokens()
    assert doc.get("terminal_confirmed") is True
    assert len(doc["results"]) == 4  # rows replaced in place, never duplicated


def test_past_show_owing_finals_is_rescued_until_confirmed(monkeypatch, client):
    """A show that ended with its finals still unpublished (crawler was down when
    they landed) stays a fast-poll rescue candidate the day after — until its
    terminal is captured and confirmed, then it settles."""
    show = {"id": 13771, "date": "20.06.", "name": "Jyväskylä KV", "month": "kesäkuu 2026"}
    seed_index_show("13771", {
        "title": "20.06.2026 Jyväskylä KV",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
            {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
        ],
    })
    monkeypatch.setattr(dog_result_cache, "_get_show_list", lambda: [show])
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

    now = _hel_timestamp(2026, 6, 21, 10)  # day after the show, within the deadline
    # Both groups have RYP-1 but the main BIS-1 never landed — finals still owed.
    owing = {
        "status": "complete",
        "cached_at": now - 100000,
        "total_breeds": 2,
        "completed_breeds": {"5:3": {"result_count": 1}, "10:7": {"result_count": 1}},
        "results": [
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1"},
            {"breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
        ],
    }
    assert dog_result_cache._result_cache_doc_is_fresh(13771, owing, now=now) is False
    dog_store._save_result_cache_doc(13771, owing)
    assert [c["show_id"] for c in dog_result_cache._auto_result_cache_candidates(now)] == [13771]

    # Terminal captured and confirmed → the cache settles and drops out of rescue.
    confirmed = dict(
        owing,
        results=[
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1, BIS-1"},
            {"breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1"},
        ],
        terminal_target_met=True,
        terminal_confirmed=True,
    )
    assert dog_result_cache._result_cache_doc_is_fresh(13771, confirmed, now=now) is True
    dog_store._save_result_cache_doc(13771, confirmed)
    assert dog_result_cache._auto_result_cache_candidates(now) == []

    # Past the settle deadline, an unconfirmed show stops being rescued (it settles
    # incomplete — the finals were never published at the source).
    past_deadline = _hel_timestamp(2026, 6, 23, 10)
    assert dog_result_cache._result_cache_doc_is_fresh(13771, owing, now=past_deadline) is True


def _all_breed_breeds():
    """Ten one-breed FCI groups → an all-breed show that crowns a main BIS."""
    return [{"group": str(g), "breed_id": str(g), "count": 2, "has_results": True}
            for g in range(1, 11)]


def _live_plan_doc(*, ryp1_groups=(), bis1=False, **extra):
    rows = []
    for g in range(1, 11):
        awards = "SA, ROP"
        if g in ryp1_groups:
            awards += ", RYP-1"
        if bis1 and g == 1:
            awards += ", BIS-1"
        rows.append({"breedGroup": str(g), "breedId": str(g), "awards": awards})
    return {"status": "complete", "results": rows, **extra}


def test_live_plan_final_day_evening_owing_finals_goes_overtime():
    """The Oulu KV failure: an all-breed final day where only one group's RYP has
    landed by 21:00. Instead of going quiet at the evening cutoff, the show enters
    finals overtime and keeps fetching so the rest of the finals are captured."""
    show = {"id": 13786, "date": "04.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))  # only group 9 has RYP-1, no BIS-1
    plan = _result_live_plan(show, doc, _all_breed_breeds(), now=_hel_timestamp(2026, 7, 4, 22))
    assert plan["phase"] == "overtime"
    assert plan["can_fetch"] is True
    assert plan["expects_finals"] is True
    assert plan["target_met"] is False


def test_live_plan_specialty_cluster_settles_on_bis_without_ryp():
    """A multi-group specialty cluster crowns BIS-1 with no group stage at all
    (15 such shows in the historical data). It must settle on BIS-1 and never wait
    for RYP that will never come."""
    show = {"id": 13093, "date": "14.09.", "month": "syyskuu 2026"}
    doc = _live_plan_doc(bis1=True, terminal_target_met=True, terminal_confirmed=True)  # BIS-1, zero RYP
    plan = _result_live_plan(show, doc, _all_breed_breeds(), now=_hel_timestamp(2026, 9, 14, 20))
    assert plan["expects_finals"] is True
    assert plan["target_met"] is True
    assert plan["phase"] == "settled"


def test_live_plan_non_final_night_stays_quiet_no_overtime():
    """A multi-day show's first-night lull is not overtime — the finals overtime
    tail is only for the final day, so earlier nights keep the polite 21:00–06:00
    quiet window."""
    show = {"id": 13500, "date": "04.-05.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))
    plan = _result_live_plan(show, doc, _all_breed_breeds(), now=_hel_timestamp(2026, 7, 4, 22))
    assert plan["phase"] == "live"
    assert plan["is_final_day"] is False
    assert plan["can_fetch"] is False


def test_live_plan_rescue_hard_stops_overnight():
    """Post-show rescue keeps fetching the owed finals during the day, but hard
    stops between 01:00 and the morning hour."""
    show = {"id": 13786, "date": "04.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))
    breeds = _all_breed_breeds()
    day = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 7, 5, 10))
    night = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 7, 5, 3))
    assert day["phase"] == "rescue" and day["can_fetch"] is True
    assert night["phase"] == "rescue" and night["can_fetch"] is False


def test_live_plan_single_group_show_does_not_rescue():
    """A single-FCI-group show (e.g. group 10 only) crowns junior/veteran/utility
    BIS but no main BIS-1. It must settle when its date passes — not enter overtime
    or rescue-poll for two days waiting for a BIS-1 that never comes (show 13664)."""
    show = {"id": 13664, "date": "12.04.", "month": "huhtikuu 2026"}
    breeds = [{"group": "10", "breed_id": str(b), "count": 2, "has_results": True}
              for b in range(1, 5)]
    doc = {"status": "complete", "results": [
        {"breedGroup": "10", "breedId": "1", "awards": "SA, ROP, JUN ROP, BIS JUN-1"},
        {"breedGroup": "10", "breedId": "2", "awards": "SA, ROP, VET ROP, BIS VET-1"},
    ]}
    # Live day: still fetching (runs the finals sweep to catch side BIS), not settled.
    live = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 4, 12, 14))
    assert live["expects_main_bis"] is False
    assert live["expects_finals"] is True
    assert live["phase"] == "live"
    # Day after: a multi-group show would be in rescue; this one settles instead.
    after = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 4, 13, 10))
    assert after["phase"] == "settled"


def test_live_plan_settles_incomplete_past_deadline():
    """Past the 2-day deadline an owed-but-never-published finals settles as
    settled_incomplete (the source itself is sometimes incomplete)."""
    show = {"id": 13786, "date": "04.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))
    plan = _result_live_plan(show, doc, _all_breed_breeds(), now=_hel_timestamp(2026, 7, 7, 10))
    assert plan["phase"] == "settled_incomplete"
    assert plan["can_fetch"] is False


def test_all_results_response_marks_stale_live_cache(monkeypatch, client):
    """The /all-results payload is built straight from the persisted doc: fresh
    within the live TTL, and served-but-flagged stale (allow_stale) once past it."""
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)
    cached_at = now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1
    dog_store._save_result_cache_doc(13771, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "persisted cache",
        "source_url": dog_showlink._source_url(13771),
        "started_at": cached_at - 20,
        "updated_at": cached_at,
        "cached_at": cached_at,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 2}},
        "failed_breeds": {},
        "results": [
            {"name": "Disk Dog 1", "breedName": "basenji"},
            {"name": "Disk Dog 2", "breedName": "basenji"},
        ],
    })

    assert dog_result_cache._all_results_response(13771, allow_stale=False) is None

    data = dog_result_cache._all_results_response(13771, allow_stale=True)
    assert [dog["name"] for dog in data["results"]] == ["Disk Dog 1", "Disk Dog 2"]
    assert data["cache"]["stale"] is True


def test_auto_result_cache_candidates_include_live_multi_day_show(monkeypatch, client):
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    show = {
        "id": 13771,
        "date": "20.-21.06.",
        "name": "Jyväskylä KV",
        "month": "kesäkuu 2026",
    }
    monkeypatch.setattr(dog_result_cache, "_get_show_list", lambda: [show])
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True },
        ],
    })
    dog_store._save_result_cache_doc(13771, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_showlink._source_url(13771),
        "started_at": now - 200,
        "updated_at": now - 180,
        "cached_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "failed_breeds": {},
        "results": [{"name": "Old Dog", "breedName": "basenji"}],
    })

    candidates = dog_result_cache._auto_result_cache_candidates(now)

    assert [candidate["show_id"] for candidate in candidates] == [13771]


@patch("app.dog_show.showlink._SESSION.get")
def test_show_all_results_rebuilds_empty_cache_when_recent_index_has_stale_result_flags(mock_get, monkeypatch, client):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(14042),
        "updated_at": 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": False },
        ],
    })
    dog_store._save_result_cache_doc(14042, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "14.06.2026 Basenji",
        "source_url": dog_showlink._source_url(14042),
        "started_at": 1000,
        "updated_at": 1001,
        "cached_at": 1001,
        "total_breeds": 0,
        "completed_breeds": {},
        "failed_breeds": {},
        "results": [],
    })
    monkeypatch.setattr(
        dog_module,
        "_show_result_availability_for_id",
        lambda show_id, now=None: {"can_fetch": True, "show_state": "live"},
    )
    monkeypatch.setattr(
        dog_result_cache,
        "_indexed_result_flags_need_refresh",
        lambda show_id, indexed_show=None, now=None: True,
    )

    resp = client.get("/api/dog/shows/14042/all-results")

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "warming"
    assert data["progress"]["state"] == "queued"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_show_all_results_rebuilds_empty_single_breed_specialty_cache(mock_get, client):
    seed_index_show("14079", {
        "title": "20.06.2000 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2000",
        "source_url": dog_showlink._source_url(14079),
        "updated_at": 1000,
        "breeds": [
            {
                "name": "bostoninterrieri",
                "count": 26,
                "group": "9",
                "breed_id": "296",
                "has_results": False,
            },
        ],
    })
    dog_store._save_result_cache_doc(14079, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 14079,
        "status": "complete",
        "title": "20.06.2000 Bostoninterrieri",
        "source_url": dog_showlink._source_url(14079),
        "started_at": 1000,
        "updated_at": 1001,
        "cached_at": 1001,
        "total_breeds": 0,
        "completed_breeds": {},
        "failed_breeds": {},
        "results": [],
    })

    resp = client.get("/api/dog/shows/14079/all-results")

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "warming"
    assert data["progress"]["state"] == "queued"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_breed_results_reuses_persisted_whole_show_cache(mock_get, client):
    seed_index_show("14042", {
        "title": "14.06.2000 Basenji",
        "month": "tammikuu 2000",
        "breeds": [
            { "name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" },
        ],
    })
    dog_store._save_result_cache_doc(14042, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "14.06.2000 Basenji",
        "source_url": dog_showlink._source_url(14042),
        "started_at": 1000,
        "updated_at": 1001,
        "cached_at": 1001,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "failed_breeds": {},
        "results": [
            {
                "number": 1,
                "name": "Ajibu You Are My Thrill",
                "grade": "ERI",
                "breedName": "basenji",
                "breedGroup": "5",
                "breedId": "3",
                "breedObj": { "name": "basenji", "group": "5", "breed_id": "3", "judge": "Paula Steele" },
            },
        ],
    })

    resp = client.get("/api/dog/shows/14042/results?group=5&breed=3")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breed"] == "basenji"
    assert data["judge"] == "Paula Steele"
    assert data["results"][0]["name"] == "Ajibu You Are My Thrill"
    assert data["results"][0]["grade"] == "ERI"
    assert data["cache"]["status"] == "show_all_results"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_breed_results_surface_judge_from_result_rows(mock_get, client):
    """When the index row has no judge yet, the breed-results payload still
    carries the judge preserved on the captured result rows (read-only — the
    one-off sweep, not the GET, is what folds it into the index)."""
    seed_index_show("13992", {
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "name": "Pertunmaa Pentunäyttely",
        "month": "heinäkuu 2025",
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 1,
                "group": "8",
                "breed_id": "124",
                "has_results": True,
            },
        ],
    })
    dog_store._save_result_cache_doc(13992, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_showlink._source_url(13992),
        "cached_at": 1001,
        "completed_breeds": {"8:124": {"name": "sileäkarvainen noutaja", "result_count": 1}},
        "results": [
            {
                "number": 1,
                "name": "Test Retriever",
                "grade": "ERI",
                "breedName": "sileäkarvainen noutaja",
                "breedGroup": "8",
                "breedId": "124",
                "breedObj": {
                    "name": "sileäkarvainen noutaja",
                    "group": "8",
                    "breed_id": "124",
                    "judge": "Tarja Kolkka",
                },
            },
        ],
    })

    resp = client.get("/api/dog/shows/13992/results?group=8&breed=124")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["judge"] == "Tarja Kolkka"
    # The GET is read-only; the index row stays judgeless until swept/crawled.
    assert "judge" not in dog_store._indexed_show("13992")["breeds"][0]
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_for_show_persists_results_with_delay(mock_get, monkeypatch, client):
    seed_index_show("14042", {
        "title": "14.06.2000 Basenji",
        "month": "tammikuu 2000",
        "source_url": dog_showlink._source_url(14042),
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": False },
        ],
    })
    sleeps = []
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: sleeps.append(seconds))
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    summary = dog_result_cache.crawl_result_cache_for_show(14042, delay=0.25, source="test")

    assert summary["status"] == "complete"
    assert sleeps == [0.25]
    mock_get.assert_called_once()
    doc = dog_store._load_result_cache_doc(14042)
    assert doc["status"] == "complete"
    assert doc["total_breeds"] == 1
    assert doc["completed_breeds"]["5:3"]["result_count"] == 1
    assert doc["completed_breeds"]["5:3"]["judge"] == "Paula Steele"
    assert doc["results"][0]["name"] == "Ajibu You Are My Thrill"
    assert doc["results"][0]["breedName"] == "basenji"

    mock_get.reset_mock()
    resp = client.get("/api/dog/shows/14042/all-results")
    assert resp.status_code == 200
    assert resp.get_json()["results"][0]["grade"] == "KP"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_refreshes_stale_recent_index_before_fetching_results(mock_get, monkeypatch):
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(14042),
        "updated_at": 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": False },
        ],
    })
    monkeypatch.setattr(dog_result_cache, "_indexed_result_flags_need_refresh", lambda show_id, indexed_show=None, now=None: True)
    monkeypatch.setattr(
        dog_result_cache,
        "_show_result_availability_for_id",
        lambda show_id, now=None: {"can_fetch": True, "show_state": "live"},
    )
    monkeypatch.setattr(dog_result_cache, "RESULT_LIVE_PROBE_BREED_LIMIT", 0)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    detail_resp = MagicMock()
    detail_resp.text = SAMPLE_SHOW_DETAIL_HTML
    detail_resp.status_code = 200
    result_resp = MagicMock()
    result_resp.text = SAMPLE_BREED_RESULTS_HTML
    result_resp.status_code = 200
    mock_get.side_effect = [detail_resp, result_resp]

    summary = dog_result_cache.crawl_result_cache_for_show(14042, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 2
    assert dog_store._indexed_show("14042")["breeds"][0]["has_results"] is True
    doc = dog_store._load_result_cache_doc(14042)
    assert doc["total_breeds"] == 1
    assert doc["completed_breeds"]["5:3"]["result_count"] == 1
    assert doc["results"][0]["name"] == "Ajibu You Are My Thrill"


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_refreshes_live_index_with_partial_result_flags(mock_get, monkeypatch):
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
        "updated_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": False },
        ],
    })
    live_detail_html = """
    <div id="divOtsikko">
        <h1>20.-21.06.2026 Jyväskylä KV</h1>
    </div>
    <table class="rotulistatable">
        <tr class="rotuluettelo">
            <td><a href="/nayttelyt/Tulokset?Id=13771&R=5&RO=3">basenji</a></td>
            <td class="right">78</td>
            <td class="right"><i class="fa fa-check"></i></td>
        </tr>
        <tr class="rotuluettelo">
            <td><a href="/nayttelyt/Tulokset?Id=13771&R=5&RO=4">ibizanpodenco</a></td>
            <td class="right">12</td>
            <td class="right"><i class="fa fa-check"></i></td>
        </tr>
    </table>
    """
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    detail_resp = MagicMock()
    detail_resp.text = live_detail_html
    detail_resp.status_code = 200
    first_result_resp = MagicMock()
    first_result_resp.text = SAMPLE_BREED_RESULTS_HTML
    first_result_resp.status_code = 200
    second_result_resp = MagicMock()
    second_result_resp.text = SAMPLE_BREED_RESULTS_HTML
    second_result_resp.status_code = 200
    mock_get.side_effect = [detail_resp, first_result_resp, second_result_resp]

    summary = dog_result_cache.crawl_result_cache_for_show(13771, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 3
    indexed_breeds = dog_store._indexed_show("13771")["breeds"]
    assert [breed["has_results"] for breed in indexed_breeds] == [True, True]
    doc = dog_store._load_result_cache_doc(13771)
    assert doc["total_breeds"] == 2
    assert set(doc["completed_breeds"]) == {"5:3", "5:4"}


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_probes_unchecked_live_breeds(mock_get, monkeypatch):
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
        "updated_at": now,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "sileäkarvainen noutaja", "count": 26, "group": "8", "breed_id": "124", "has_results": False },
            { "name": "barbet", "count": 7, "group": "8", "breed_id": "293", "has_results": False },
        ],
    })
    monkeypatch.setattr(
        dog_result_cache,
        "_show_result_availability_for_id",
        lambda show_id, now=None: {"can_fetch": True, "show_state": "live", "reason": "show_day"},
    )
    monkeypatch.setattr(dog_result_cache, "RESULT_LIVE_PROBE_BREED_LIMIT", 1)
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    first_result_resp = MagicMock()
    first_result_resp.text = SAMPLE_BREED_RESULTS_HTML
    first_result_resp.status_code = 200
    probed_result_resp = MagicMock()
    probed_result_resp.text = SAMPLE_BREED_RESULTS_FLOATLEFT_HTML
    probed_result_resp.status_code = 200
    mock_get.side_effect = [first_result_resp, probed_result_resp]

    summary = dog_result_cache.crawl_result_cache_for_show(13771, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    requested_urls = [call.args[0] for call in mock_get.call_args_list]
    assert requested_urls[0].endswith("Id=13771&R=5&RO=3")
    assert requested_urls[1].endswith("Id=13771&R=8&RO=124")
    indexed_breeds = dog_store._indexed_show("13771")["breeds"]
    assert [breed["has_results"] for breed in indexed_breeds] == [True, True, False]
    doc = dog_store._load_result_cache_doc(13771)
    assert doc["total_breeds"] == 2
    assert doc["completed_breeds"]["8:124"]["result_count"] == 1
    assert doc["completed_breeds"]["8:124"]["judge"] == "Pietro Marino"
    assert doc["live_probe_cursor"] == 1


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_refetches_live_breeds_captured_with_zero_results(mock_get, monkeypatch):
    # A live-show pass that runs before any ring has published results records
    # every breed in completed_breeds with result_count 0 and marks the cache
    # complete. Those empty captures must stay re-fetchable while the show is
    # live — otherwise the show is frozen at 0 dogs for good (show 14085).
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13771", {
        "title": "20.06.2026 Colliet",
        "name": "Colliet",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13771),
        "updated_at": now,
        "breeds": [
            { "name": "pitkäkarvainen collie", "count": 125, "group": "1", "breed_id": "139", "has_results": True },
            { "name": "sileäkarvainen collie", "count": 80, "group": "1", "breed_id": "150", "has_results": False },
        ],
    })
    early_capture_at = now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1
    dog_store._save_result_cache_doc(13771, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.06.2026 Colliet",
        "source_url": dog_showlink._source_url(13771),
        "started_at": early_capture_at,
        "updated_at": early_capture_at,
        "cached_at": early_capture_at,
        "total_breeds": 2,
        "completed_breeds": {
            "1:139": {"name": "pitkäkarvainen collie", "result_count": 0, "updated_at": early_capture_at},
            "1:150": {"name": "sileäkarvainen collie", "result_count": 0, "updated_at": early_capture_at},
        },
        "failed_breeds": {},
        "results": [],
    })
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    flagged_result_resp = MagicMock()
    flagged_result_resp.text = SAMPLE_BREED_RESULTS_HTML
    flagged_result_resp.status_code = 200
    probed_result_resp = MagicMock()
    probed_result_resp.text = SAMPLE_BREED_RESULTS_FLOATLEFT_HTML
    probed_result_resp.status_code = 200
    mock_get.side_effect = [flagged_result_resp, probed_result_resp]

    summary = dog_result_cache.crawl_result_cache_for_show(13771, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    requested_urls = [call.args[0] for call in mock_get.call_args_list]
    assert requested_urls[0].endswith("Id=13771&R=1&RO=139")
    assert requested_urls[1].endswith("Id=13771&R=1&RO=150")
    doc = dog_store._load_result_cache_doc(13771)
    assert doc["status"] == "complete"
    assert doc["completed_breeds"]["1:139"]["result_count"] == 1
    assert doc["completed_breeds"]["1:150"]["result_count"] == 1
    assert len(doc["results"]) == 2


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_keeps_zero_result_captures_settled_after_show(mock_get, monkeypatch):
    # Outside the live window (and past the post-show morning check) an empty
    # capture is a real capture — a settled old show with a no-show breed must
    # not be re-crawled on every stale refresh.
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    seed_index_show("13772", {
        "title": "10.06.2026 Colliet",
        "name": "Colliet",
        "date": "10.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(13772),
        "updated_at": now,
        "breeds": [
            { "name": "pitkäkarvainen collie", "count": 5, "group": "1", "breed_id": "139", "has_results": True },
        ],
    })
    dog_store._save_result_cache_doc(13772, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13772,
        "status": "complete",
        "title": "10.06.2026 Colliet",
        "source_url": dog_showlink._source_url(13772),
        "started_at": 1,
        "updated_at": 2,
        "cached_at": 2,
        "total_breeds": 1,
        "completed_breeds": {
            "1:139": {"name": "pitkäkarvainen collie", "result_count": 0, "updated_at": 2},
        },
        "failed_breeds": {},
        "results": [],
    })
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda show_id, doc, now=None: False)
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    summary = dog_result_cache.crawl_result_cache_for_show(13772, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 0


@patch("app.dog_show.showlink._SESSION.get")
def test_crawl_result_cache_fetches_single_breed_specialty_without_result_flag(mock_get, monkeypatch):
    seed_index_show("14079", {
        "title": "20.06.2000 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2000",
        "source_url": dog_showlink._source_url(14079),
        "updated_at": 1000,
        "breeds": [
            {
                "name": "bostoninterrieri",
                "count": 26,
                "group": "9",
                "breed_id": "296",
                "has_results": False,
            },
        ],
    })
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    summary = dog_result_cache.crawl_result_cache_for_show(14079, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 1
    assert "Id=14079" in mock_get.call_args.args[0]
    assert "R=9" in mock_get.call_args.args[0]
    assert "RO=296" in mock_get.call_args.args[0]
    doc = dog_store._load_result_cache_doc(14079)
    assert doc["total_breeds"] == 1
    assert doc["completed_breeds"]["9:296"]["result_count"] == 1
    assert doc["results"][0]["breedName"] == "bostoninterrieri"
    assert doc["results"][0]["name"] == "Ajibu You Are My Thrill"


@patch("app.dog_show.showlink._SESSION.get")
def test_stale_result_cache_is_preserved_when_refresh_fails(mock_get, monkeypatch):
    # Two indexed breeds, only one captured. A stale refresh now fetches just the
    # uncaptured breed (incremental); when that Showlink fetch fails the existing
    # complete cache must stay intact rather than being clobbered with a partial.
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "source_url": dog_showlink._source_url(14042),
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "beagle", "count": 12, "group": "6", "breed_id": "9", "has_results": True },
        ],
    })
    dog_store._save_result_cache_doc(14042, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "old cache",
        "source_url": dog_showlink._source_url(14042),
        "started_at": 1,
        "updated_at": 2,
        "cached_at": 2,
        "total_breeds": 2,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "failed_breeds": {},
        "results": [{"name": "Old Cached Dog", "breedName": "basenji", "breedGroup": "5", "breedId": "3"}],
    })
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda show_id, doc, now=None: False)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)
    mock_get.side_effect = requests.RequestException("rate limited")

    summary = dog_result_cache.crawl_result_cache_for_show(14042, delay=0.1, source="test")

    assert summary["status"] == "partial"
    doc = dog_store._load_result_cache_doc(14042)
    assert doc["status"] == "complete"
    assert doc["results"][0]["name"] == "Old Cached Dog"

@patch("app.dog_show.showlink._SESSION.get")
def test_search_shows(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_LIST_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/search?q=villa")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["query"] == "villa"
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["name"] == "Villakoira erikoisnäyttely"
    assert data["results"][0]["breed"] is None
    assert data["results"][0]["match"] == "show"

@patch("app.dog_show.showlink._SESSION.get")
def test_search_shows_by_breed(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True }
        ]
    })

    mock_get.return_value = mock_resp_list

    resp = client.get("/api/dog/search?q=base")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["query"] == "base"
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["name"] == "Basenji"
    assert data["results"][0]["breed"]["name"] == "basenji"
    assert data["results"][0]["breed"]["breed_id"] == "3"
    assert data["results"][0]["match"] == "breed"


@patch("app.dog_show.showlink._SESSION.get")
def test_search_indexed_show_name_without_breed_match(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200
    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": True }
        ]
    })
    mock_get.return_value = mock_resp_list

    resp = client.get("/api/dog/search?q=base")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["name"] == "Basenji"
    assert data["results"][0]["breed"] is None
    assert data["results"][0]["match"] == "show"

def test_search_shows_missing_query(client):
    resp = client.get("/api/dog/search?q=")
    assert resp.status_code == 400

def test_breed_results_missing_params(client):
    resp = client.get("/api/dog/shows/14042/results")
    assert resp.status_code == 400

    resp = client.get("/api/dog/shows/14042/results?group=5")
    assert resp.status_code == 400

def test_breed_results_invalid_params(client):
    resp = client.get("/api/dog/shows/14042/results?group=abc&breed=3")
    assert resp.status_code == 400

    resp = client.get("/api/dog/shows/14042/results?group=11&breed=3")
    assert resp.status_code == 400

    resp = client.get("/api/dog/shows/14042/results?group=5&breed=0")
    assert resp.status_code == 400

@patch("app.dog_show.showlink._SESSION.get")
def test_search_shows_by_judge(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    seed_index_show("14042", {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": True, "judge": "Paula Steele" },
        ]
    })

    mock_get.return_value = mock_resp_list

    resp = client.get("/api/dog/search?q=steele")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["query"] == "steele"
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["name"] == "Basenji"
    assert data["results"][0]["breed"] is None
    assert data["results"][0]["judge"] == "Paula Steele"
    assert data["results"][0]["judge_match_count"] == 2
    assert data["results"][0]["match"] == "judge"


@patch("app.dog_show.showlink._SESSION.get")
def test_search_finds_indexed_only_show_by_cleaned_judge(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200
    seed_index_show("13763", {
        "title": "18.-19.04.2026 Vaasa KV",
        "name": "Vaasa KV",
        "date": "18.-19.04.",
        "month": "huhtikuu 2026",
        "source_url": dog_showlink._source_url(13763),
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 28,
                "group": "8",
                "breed_id": "124",
                "has_results": True,
                "judge": "TuomariTarja Kolkka",
            }
        ],
    })
    mock_get.return_value = mock_resp_list

    resp = client.get("/api/dog/search?q=tuomari%20tarja")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["query"] == "tuomari tarja"
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["id"] == 13763
    assert data["results"][0]["show"]["name"] == "Vaasa KV"
    assert data["results"][0]["breed"] is None
    assert data["results"][0]["judge"] == "Tarja Kolkka"
    assert data["results"][0]["judge_match_count"] == 1
    assert data["results"][0]["match"] == "judge"


@patch("app.dog_show.showlink._SESSION.get")
def test_judge_sweep_makes_result_row_judges_searchable(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200
    seed_index_show("13992", {
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "name": "Pertunmaa Pentunäyttely",
        "date": "27.07.",
        "month": "heinäkuu 2025",
        "source_url": dog_showlink._source_url(13992),
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 1,
                "group": "8",
                "breed_id": "124",
                "has_results": True,
            }
        ],
    })
    dog_store._save_result_cache_doc(13992, {
        "version": dog_result_cache.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_showlink._source_url(13992),
        "cached_at": 1001,
        "completed_breeds": {"8:124": {"name": "sileäkarvainen noutaja", "result_count": 1}},
        "results": [
            {
                "number": 1,
                "name": "Test Retriever",
                "grade": "ERI",
                "breedName": "sileäkarvainen noutaja",
                "breedGroup": "8",
                "breedId": "124",
                "breedObj": {
                    "name": "sileäkarvainen noutaja",
                    "count": 1,
                    "group": "8",
                    "breed_id": "124",
                    "has_results": True,
                    "judge": "Tarja Kolkka",
                },
            },
        ],
    })
    mock_get.return_value = mock_resp_list

    # Judge search reads the breed index only; the one-off sweep is what folds a
    # judge captured on result rows into the index for a pre-rewrite show.
    resp = client.get("/api/dog/search?q=kolkka")
    assert resp.status_code == 200
    assert resp.get_json()["results"] == []

    with dog_db.session_scope() as session:
        assert dog_sqlstore.sweep_breed_judges_from_results(session) == 1

    resp = client.get("/api/dog/search?q=kolkka")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["id"] == 13992
    assert data["results"][0]["breed"] is None
    assert data["results"][0]["judge"] == "Tarja Kolkka"
    assert data["results"][0]["judge_match_count"] == 1
    assert data["results"][0]["match"] == "judge"
    assert dog_store._indexed_show("13992")["breeds"][0]["judge"] == "Tarja Kolkka"


# --- Cross-show dog-name / owner search (Phase E workstream 2) ---

def _search_result_row(number, name, group="5", breed="3", comp=""):
    return {
        "number": number, "name": name, "reg_url": "", "grade": "ERI",
        "placement": number, "competitive_placement": comp, "awards": "", "critique": "",
        "gender": "uros", "class_name": "AVO", "breedName": f"breed-{breed}",
        "breedGroup": group, "breedId": breed,
        "breedObj": {"name": f"breed-{breed}", "group": group, "breed_id": breed, "judge": "J"},
    }


def _seed_search_doc(show_id, results, completed_breeds=None):
    """Persist a complete result doc (DogResult rows + optional DogBreedAward rows)
    into dog.db, plus an index entry so the show is in the searchable set."""
    from app.dog_show import sqlstore
    seed_index_show(str(show_id), {
        "title": f"14.06.2026 Show {show_id}",
        "breeds": [{"name": "breed-3", "count": len(results), "group": "5", "breed_id": "3", "has_results": True}],
    })
    doc = {
        "version": 1, "status": "complete", "source": "t", "title": f"14.06.2026 Show {show_id}",
        "source_url": "u", "total_breeds": 1, "started_at": 1.0, "updated_at": 9.0,
        "cached_at": 9.0, "last_error": None,
        "completed_breeds": completed_breeds or {}, "failed_breeds": {},
        "results": results,
    }
    with dog_db.session_scope() as session:
        sqlstore.write_result_doc(session, int(show_id), doc)


@patch("app.dog_show.showlink._SESSION.get")
def test_search_finds_dog_by_name(mock_get, client):
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(14042, [
        _search_result_row(1, "Aamun Tähti", comp="PU1"),
        _search_result_row(2, "Iltatähti"),
    ])

    resp = client.get("/api/dog/search?q=tähti")
    assert resp.status_code == 200
    dog_results = [r for r in resp.get_json()["results"] if r["match"] == "dog"]
    assert len(dog_results) == 1
    assert dog_results[0]["show"]["id"] == 14042
    assert dog_results[0]["breed"] is None
    assert dog_results[0]["dog_match_count"] == 2  # both names contain "tähti"
    assert "tähti" in dog_results[0]["dog"].lower()


@patch("app.dog_show.showlink._SESSION.get")
def test_search_dog_name_unicode_case(mock_get, client):
    """A fully-uppercase stored name with ä must be found by a lowercase query —
    SQLite LIKE is only ASCII case-insensitive, so the helper ORs cased variants."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(14043, [_search_result_row(1, "AAMUN TÄHTI")])

    resp = client.get("/api/dog/search?q=tähti")
    assert resp.status_code == 200
    dog_shows = {r["show"]["id"] for r in resp.get_json()["results"] if r["match"] == "dog"}
    assert 14043 in dog_shows


@patch("app.dog_show.showlink._SESSION.get")
def test_search_finds_owner_from_breed_awards(mock_get, client):
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(
        14044,
        [_search_result_row(1, "Some Winner Dog")],
        completed_breeds={"5:3": {"name": "breed-3", "result_count": 1, "judge": "J", "awards": [
            {"type": "ROP", "name": "Some Winner Dog", "owner": "Virtanen Sirja", "text": "Some Winner Dog, Om. Virtanen Sirja"},
        ]}},
    )

    resp = client.get("/api/dog/search?q=virtanen")
    assert resp.status_code == 200
    owner_results = [r for r in resp.get_json()["results"] if r["match"] == "owner"]
    assert len(owner_results) == 1
    assert owner_results[0]["show"]["id"] == 14044
    assert "virtanen" in owner_results[0]["owner"].lower()
    assert owner_results[0]["owner_match_count"] == 1


@patch("app.dog_show.showlink._SESSION.get")
def test_search_dog_matches_bounded(mock_get, client):
    """Dog-name matches are capped at SEARCH_ENTITY_SHOW_LIMIT shows so a common
    substring can't return the whole database."""
    from app.dog_show import search as dog_search
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    for i in range(dog_search.SEARCH_ENTITY_SHOW_LIMIT + 5):
        _seed_search_doc(15000 + i, [_search_result_row(1, "Tähti Dog")])

    resp = client.get("/api/dog/search?q=tähti")
    assert resp.status_code == 200
    dog_results = [r for r in resp.get_json()["results"] if r["match"] == "dog"]
    assert len(dog_results) == dog_search.SEARCH_ENTITY_SHOW_LIMIT


@patch("app.dog_show.showlink._SESSION.get")
def test_search_short_query_skips_dog_scan(mock_get, client):
    """Under 3 chars only the show/breed/judge index search runs; the SQL dog/owner
    scan is skipped so a 2-char query stays cheap."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(14045, [_search_result_row(1, "Tähti Dog")])

    resp = client.get("/api/dog/search?q=tä")
    assert resp.status_code == 200
    assert not [r for r in resp.get_json()["results"] if r["match"] in ("dog", "owner")]


@patch("app.dog_show.showlink._SESSION.get")
def test_search_dog_name_escapes_like_wildcards(mock_get, client):
    """A literal '%' in the query must not act as a LIKE wildcard."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(14046, [
        _search_result_row(1, "Sata 100% Varma"),
        _search_result_row(2, "Tuhat 1000 Tahti"),
    ])

    resp = client.get("/api/dog/search?q=100%25")  # "100%" URL-encoded
    assert resp.status_code == 200
    dog_results = [r for r in resp.get_json()["results"] if r["match"] == "dog" and r["show"]["id"] == 14046]
    assert len(dog_results) == 1
    # Only "Sata 100% Varma" matches literally; "1000" is not a wildcard hit.
    assert dog_results[0]["dog_match_count"] == 1
    assert "100%" in dog_results[0]["dog"]


def test_parse_show_meta_from_title():
    from app.dog_show.indexing import _parse_show_meta_from_title
    # Single date
    meta1 = _parse_show_meta_from_title("21.06.2026 Amerikancockerspanieli")
    assert meta1 == {
        "name": "Amerikancockerspanieli",
        "date": "21.06.",
        "month": "kesäkuu 2026"
    }

    # Same-month range
    meta2 = _parse_show_meta_from_title("20.-21.06.2026 Jyväskylä KV")
    assert meta2 == {
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026"
    }

    # Cross-month range
    meta3 = _parse_show_meta_from_title("31.05.-01.06.2026 Specialty Show")
    assert meta3 == {
        "name": "Specialty Show",
        "date": "31.05.-01.06.",
        "month": "kesäkuu 2026"
    }

    # Invalid title
    assert _parse_show_meta_from_title("Invalid Title Format") == {}


def test_show_stats_is_live_only_when_results_fetchable(client):
    seed_index_show("14021", {
        "title": "21.06.2026 Amerikancockerspanieli",
        "name": "Amerikancockerspanieli",
        "date": "21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "amerikancockerspanieli", "count": 21, "group": "8", "breed_id": "117"},
        ],
    })

    with patch("app.dog_show.indexing._show_result_availability") as mock_avail:
        mock_avail.return_value = {"can_fetch": False}
        stats = dog_indexing._show_stats_from_index(
            14021,
            today=datetime.date(2026, 6, 21)
        )
        assert stats["is_live"] is False

    with patch("app.dog_show.indexing._show_result_availability") as mock_avail:
        mock_avail.return_value = {"can_fetch": True}
        stats = dog_indexing._show_stats_from_index(
            14021,
            today=datetime.date(2026, 6, 21)
        )
        assert stats["is_live"] is True



# ---------------------------------------------------------------------------
# Phase C: full-data capture extensions (competitive placement + honor roll)
# ---------------------------------------------------------------------------

def _hel_timestamp(year, month, day, hour):
    from zoneinfo import ZoneInfo
    import datetime as _dt
    return _dt.datetime(year, month, day, hour, 0, tzinfo=ZoneInfo("Europe/Helsinki")).timestamp()


def test_parse_breed_results_captures_competitive_placement():
    from bs4 import BeautifulSoup
    from app.dog_show.parsers import _parse_breed_results
    data = _parse_breed_results(BeautifulSoup(SAMPLE_BREED_RESULTS_FLOATLEFT_HTML, "html.parser"), 13771)
    # cells[4] (PU/PN competitive ranking) was previously dropped.
    assert data["results"][0]["competitive_placement"] == "PU3"
    assert data["results"][0]["placement"] == 1  # class placement still distinct


def test_parse_breed_results_honor_roll_splits_owner():
    from bs4 import BeautifulSoup
    from app.dog_show.parsers import _parse_breed_results
    data = _parse_breed_results(BeautifulSoup(SAMPLE_BREED_RESULTS_HTML, "html.parser"), 14042)
    award = data["awards"][0]
    assert award["type"] == "ROP"
    assert award["text"] == "Wazazi Tempting Fate, Om. Kortelainen Sanna"  # back-compat shape kept
    assert award["name"] == "Wazazi Tempting Fate"
    assert award["owner"] == "Kortelainen Sanna"


def test_split_award_name_owner():
    from app.dog_show.parsers import _split_award_name_owner
    assert _split_award_name_owner("Heinäkengän, Om. Hytönen Leena") == ("Heinäkengän", "Hytönen Leena")
    assert _split_award_name_owner("Kennel Only") == ("Kennel Only", "")
    assert _split_award_name_owner("") == ("", "")


@patch("app.dog_show.showlink._SESSION.get")
def test_result_crawl_persists_phase_c_fields(mock_get, monkeypatch):
    """A whole-show result crawl captures the Phase C full-data fields: per-dog
    competitive placement (PU/PN) and the breed honor-roll award rows."""
    from sqlalchemy import select
    from app.dog_show import db as _dog_db
    from app.dog_show.models import DogResult, DogBreedAward
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    seed_index_show("12754", {
        "title": "15.06.2024 Old Retriever Show", "name": "Old Retriever Show",
        "date": "15.06.", "month": "kes\u00e4kuu 2024", "source_url": dog_showlink._source_url(12754),
        "breeds": [{"name": "sile\u00e4karvainen noutaja", "count": 5, "group": "8", "breed_id": "124", "has_results": True}],
    })

    resp = MagicMock()
    resp.text = SAMPLE_BREED_RESULTS_FLOATLEFT_HTML
    resp.status_code = 200
    mock_get.return_value = resp

    summary = dog_result_cache.crawl_result_cache_for_show(12754, delay=0, source="test", workers=1)
    assert summary["status"] == "complete"

    # saves to database: the per-dog field and the honor-roll table
    with _dog_db.session_scope() as session:
        results = session.execute(select(DogResult).where(DogResult.show_id == 12754)).scalars().all()
        awards = session.execute(select(DogBreedAward).where(DogBreedAward.show_id == 12754)).scalars().all()

    assert any(r.competitive_placement == "PU3" for r in results)
    cacib = next(a for a in awards if a.award_type == "CACIB uros")
    assert cacib.name == "Calzeat Causin Heads To Turn"
    assert cacib.owner == "Nyberg Tiia"
    assert cacib.breed_id == "124"


# ---------------------------------------------------------------------------
# Post-Phase-C review follow-ups: incremental per-breed writes
# ---------------------------------------------------------------------------

def _dog_row_count(model, show_id):
    from sqlalchemy import func, select
    with dog_db.session_scope() as session:
        return session.execute(
            select(func.count()).select_from(model).where(model.show_id == show_id)
        ).scalar_one()


def _phase_c_result(group, breed, number, comp="", judge="J"):
    return {
        "number": number, "name": f"Dog {number}", "reg_url": "", "grade": "ERI",
        "placement": number, "competitive_placement": comp, "awards": "", "critique": "c",
        "gender": "uros", "class_name": "AVO", "breedName": f"breed-{breed}",
        "breedGroup": group, "breedId": breed,
        "breedObj": {"name": f"breed-{breed}", "group": group, "breed_id": breed, "judge": judge},
    }


def test_append_result_breed_matches_full_rewrite():
    """Incremental per-breed appends reconstruct a doc byte-identical to a single
    full rewrite of the same final doc, with identical row counts."""
    import copy
    from app.dog_show import sqlstore
    from app.dog_show.models import DogBreedAward, DogResult

    final_doc = {
        "version": 1, "status": "complete", "source": "test", "title": "T",
        "source_url": "u", "total_breeds": 2, "started_at": 1.0, "updated_at": 9.0,
        "cached_at": 9.0, "last_error": None,
        "completed_breeds": {
            "5:3": {"name": "breed-3", "result_count": 2, "judge": "J",
                    "awards": [{"type": "ROP", "name": "A", "owner": "OA", "text": "A, Om. OA"}]},
            "8:124": {"name": "breed-124", "result_count": 1, "judge": "J",
                      "awards": [{"type": "CACIB uros", "name": "B", "owner": "OB", "text": "B, Om. OB"}]},
        },
        "failed_breeds": {},
        "results": [
            _phase_c_result("5", "3", 1, comp="PU1"),
            _phase_c_result("5", "3", 2, comp=""),
            _phase_c_result("8", "124", 1, comp="PN1"),
        ],
    }

    # Reference: one clean full rewrite into show 9001.
    with dog_db.session_scope() as session:
        sqlstore.write_result_doc(session, 9001, final_doc)
    with dog_db.session_scope() as session:
        ref_doc = sqlstore.read_result_doc(session, 9001)

    # Incremental: progressive per-breed appends into show 9002, mirroring the crawl.
    building = copy.deepcopy(final_doc)
    building["status"] = "running"
    building["results"] = []
    building["completed_breeds"] = {}
    with dog_db.session_scope() as session:
        sqlstore.write_result_cache_header(session, 9002, building)

    b1 = [r for r in final_doc["results"] if r["breedId"] == "3"]
    building["results"].extend(b1)
    building["completed_breeds"]["5:3"] = final_doc["completed_breeds"]["5:3"]
    with dog_db.session_scope() as session:
        sqlstore.append_result_breed(session, 9002, building, "5", "3", b1)

    b2 = [r for r in final_doc["results"] if r["breedId"] == "124"]
    building["results"].extend(b2)
    building["completed_breeds"]["8:124"] = final_doc["completed_breeds"]["8:124"]
    building["status"] = "complete"
    with dog_db.session_scope() as session:
        sqlstore.append_result_breed(session, 9002, building, "8", "124", b2)

    with dog_db.session_scope() as session:
        inc_doc = sqlstore.read_result_doc(session, 9002)

    ref_doc.pop("show_id")
    inc_doc.pop("show_id")
    assert inc_doc == ref_doc  # byte-identical reconstruction
    assert _dog_row_count(DogResult, 9001) == _dog_row_count(DogResult, 9002) == 3
    assert _dog_row_count(DogBreedAward, 9001) == _dog_row_count(DogBreedAward, 9002) == 2


def test_append_result_breed_idempotent_on_resave():
    """Re-appending the same breed (resume/retry) replaces its rows rather than
    duplicating result or award rows."""
    from app.dog_show import sqlstore
    from app.dog_show.models import DogBreedAward, DogResult

    rows = [_phase_c_result("5", "3", 1, comp="PU1"), _phase_c_result("5", "3", 2)]
    doc = {
        "version": 1, "status": "running", "source": "t", "title": "T", "source_url": "u",
        "total_breeds": 1, "results": list(rows),
        "completed_breeds": {"5:3": {"name": "breed-3", "result_count": 2, "judge": "J",
            "awards": [{"type": "ROP", "name": "X", "owner": "Y", "text": "X, Om. Y"}]}},
    }

    with dog_db.session_scope() as session:
        sqlstore.append_result_breed(session, 9100, doc, "5", "3", rows)
    assert (_dog_row_count(DogResult, 9100), _dog_row_count(DogBreedAward, 9100)) == (2, 1)

    with dog_db.session_scope() as session:
        sqlstore.append_result_breed(session, 9100, doc, "5", "3", rows)
    assert (_dog_row_count(DogResult, 9100), _dog_row_count(DogBreedAward, 9100)) == (2, 1)




# ---------------------------------------------------------------------------
# SQL-first read paths: sqlstore query functions, sweeps, recency window
# ---------------------------------------------------------------------------

def _seed_two_shows():
    seed_index_show("9200", {
        "title": "14.06.2026 Vaasa KV", "name": "Vaasa KV", "date": "14.06.",
        "month": "kesäkuu 2026", "source_url": "u1", "updated_at": 100.0,
        "breeds": [
            {"name": "basenji", "count": 78, "group": "5", "breed_id": "3",
             "has_results": True, "judge": "Paula Steele"},
            {"name": "beagle", "count": 12, "group": "6", "breed_id": "9", "has_results": False},
        ],
    })
    seed_index_show("9201", {
        "title": "empty show", "name": "Empty", "date": "15.06.",
        "month": "kesäkuu 2026", "source_url": "u2", "updated_at": 50.0,
        "breeds": [], "empty_breed_list_confirmed": True,
    })


def test_sqlstore_read_show_and_meta():
    _seed_two_shows()
    with dog_db.session_scope() as session:
        show = dog_sqlstore.read_show(session, 9200)
        assert show["title"] == "14.06.2026 Vaasa KV"
        assert [b["name"] for b in show["breeds"]] == ["basenji", "beagle"]
        assert show["breeds"][0]["judge"] == "Paula Steele"
        assert "judge" not in show["breeds"][1]

        meta = dog_sqlstore.read_show_meta(session, 9201)
        assert meta["name"] == "Empty"
        assert meta["empty_breed_list_confirmed"] is True
        assert "breeds" not in meta

        assert dog_sqlstore.read_show(session, 424242) is None
        assert dog_sqlstore.read_show_meta(session, 424242) is None


def test_sqlstore_read_shows_bulk_and_index_states():
    _seed_two_shows()
    with dog_db.session_scope() as session:
        shows = dog_sqlstore.read_shows(session, [9200, "9201", 424242, "junk"])
        assert sorted(shows) == ["9200", "9201"]
        assert len(shows["9200"]["breeds"]) == 2

        assert dog_sqlstore.count_shows(session) == 2
        states = dog_sqlstore.index_states(session)
        assert states["9200"] == {"breed_count": 2, "empty_breed_list_confirmed": False}
        assert states["9201"] == {"breed_count": 0, "empty_breed_list_confirmed": True}


def test_sqlstore_set_breed_judge_semantics():
    _seed_two_shows()

    def _judges():
        show = dog_store._indexed_show("9200")
        return [b.get("judge") for b in show["breeds"]]

    with dog_db.session_scope() as session:
        # Cleans the Showlink label and writes where missing.
        assert dog_sqlstore.set_breed_judge(session, 9200, "6", "9", "TuomariTarja Kolkka") == 1
        # Same cleaned judge again is a no-op.
        assert dog_sqlstore.set_breed_judge(session, 9200, "6", "9", "Tarja Kolkka") == 0
        # Empty/whitespace judge is a no-op.
        assert dog_sqlstore.set_breed_judge(session, 9200, "5", "3", "  ") == 0
        # only_missing never overwrites an existing judge.
        assert dog_sqlstore.set_breed_judge(session, 9200, "5", "3", "Other Judge", only_missing=True) == 0
        # The default write path does replace a changed judge.
        assert dog_sqlstore.set_breed_judge(session, 9200, "5", "3", "Other Judge") == 1
    assert _judges() == ["Other Judge", "Tarja Kolkka"]


def test_sqlstore_search_precedence_and_unicode_case():
    seed_index_show("9300", {
        "title": "14.06.2026 Näyttely", "name": "Näyttely", "date": "14.06.",
        "month": "kesäkuu 2026", "source_url": "u", "updated_at": 1.0,
        "breeds": [
            {"name": "SILEÄKARVAINEN NOUTAJA", "count": 5, "group": "8", "breed_id": "124",
             "has_results": True, "judge": "Tarja Kolkka"},
            {"name": "kolkkaterrieri", "count": 2, "group": "6", "breed_id": "9",
             "has_results": True, "judge": "Kolkka Tarja"},
        ],
    })
    with dog_db.session_scope() as session:
        # Unicode-uppercase stored name found by a lowercase query.
        names = dog_sqlstore.search_breeds_by_name(session, ["sileäkarvainen"])
        assert [(sid, b["breed_id"]) for sid, b in names] == [(9300, "124")]

        # A judge match on a name-matched breed is swallowed by the breed match:
        # "kolkka" matches breed 9 by name and both judges, so only breed 124
        # surfaces as a judge hit.
        judges = dog_sqlstore.search_breeds_by_judge(session, ["kolkka"])
        assert [(sid, b["breed_id"]) for sid, b in judges] == [(9300, "124")]
        assert dog_sqlstore.search_breeds_by_judge(session, ["sileäkarvainen"]) == []

        # Show text matches on the combined name/title/date/month string.
        assert dog_sqlstore.search_show_ids(session, ["näyttely"]) == [9300]
        assert dog_sqlstore.search_show_ids(session, ["kesäkuu 2026"]) == [9300]
        assert dog_sqlstore.search_show_ids(session, ["nomatch"]) == []

        assert dog_sqlstore.indexed_show_ids(session, [9300, 424242, "junk"]) == {9300}


def test_sweep_folds_result_rows_into_index_flags_and_judges():
    seed_index_show("9400", {
        "title": "14.06.2024 Sweep Show", "name": "Sweep", "date": "14.06.",
        "month": "kesäkuu 2024", "source_url": "u", "updated_at": 1.0,
        "breeds": [
            {"name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": False},
        ],
    })
    with dog_db.session_scope() as session:
        dog_sqlstore.write_result_doc(session, 9400, {
            "version": 1, "status": "complete", "source": "t", "title": "T", "source_url": "u",
            "total_breeds": 1, "started_at": 1.0, "updated_at": 2.0, "cached_at": 2.0,
            "last_error": None, "failed_breeds": {},
            "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1, "judge": "Paula Steele"}},
            "results": [{"number": 1, "name": "Dog", "breedGroup": "5", "breedId": "3",
                         "breedName": "basenji", "breedObj": {"judge": "Paula Steele"}}],
        })

    with dog_db.session_scope() as session:
        assert dog_sqlstore.sweep_breed_judges_from_results(session) == 1
        assert dog_sqlstore.sweep_breed_result_flags(session) == 1
        # Idempotent.
        assert dog_sqlstore.sweep_breed_judges_from_results(session) == 0
        assert dog_sqlstore.sweep_breed_judges_from_cache_meta(session) == 0
        assert dog_sqlstore.sweep_breed_result_flags(session) == 0

    breed = dog_store._indexed_show("9400")["breeds"][0]
    assert breed["judge"] == "Paula Steele"
    assert breed["has_results"] is True


def test_show_is_recent_date_window():
    today = datetime.date(2026, 7, 6)
    def recent(show):
        return _show_is_recent(show, today=today)

    assert recent({"date": "05.07.", "month": "heinäkuu 2026"}) is True
    assert recent({"date": "20.06.2026", "month": "kesäkuu 2026"}) is True
    # 45 days back inclusive, then out of the window.
    assert recent({"date": "22.05.2026", "month": "toukokuu 2026"}) is True
    assert recent({"date": "21.05.2026", "month": "toukokuu 2026"}) is False
    # 31 days ahead inclusive, then out.
    assert recent({"date": "06.08.2026", "month": "elokuu 2026"}) is True
    assert recent({"date": "07.08.2026", "month": "elokuu 2026"}) is False
    # Month-label fallback when the day range is unparseable.
    assert recent({"date": "", "month": "heinäkuu 2026"}) is True
    assert recent({"date": "", "month": "tammikuu 2000"}) is False
    # Truly unknown dates fail open.
    assert recent({"date": "", "month": ""}) is True
    assert recent(None) is True
