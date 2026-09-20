import datetime
import json
import pathlib
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
from app.dog_show import shows as dog_shows
from app.dog_show import utils as dog_utils
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

from app.dog_show.utils import (
    _in_fetch_window, _result_doc_last_result_at, _result_live_plan, _show_is_recent,
    _show_live_phase, _show_result_availability, _utc_iso,
)

# Modules that hold their own reference to the shared fetch-window helpers.
_FETCH_WINDOW_MODULES = (dog_crawler, dog_result_cache, dog_shows)


@pytest.fixture(autouse=True)
def _dog_daytime_clock(monkeypatch):
    """Hold the shared fetch window open for tests that read the wall clock.

    Nothing outside the window reaches Showlink, so a crawl test run at 22:00
    would otherwise skip and fail. Tests that are *about* the window pass an
    explicit `now`/hour, or restore the real helpers via `real_fetch_window`."""
    for module in _FETCH_WINDOW_MODULES:
        monkeypatch.setattr(module, "_fetch_window_open", lambda now=None: True)
    monkeypatch.setattr(
        dog_result_cache,
        "_local_dt",
        lambda now=None: dog_utils._local_dt(now).replace(hour=12, minute=0, second=0),
    )
    monkeypatch.setattr(
        dog_utils,
        "_local_now",
        lambda: dog_utils._local_dt(time.time()).replace(hour=12, minute=0, second=0),
    )


@pytest.fixture
def real_fetch_window(monkeypatch):
    """Undo `_dog_daytime_clock`'s window override for tests that exercise it."""
    for module in _FETCH_WINDOW_MODULES:
        monkeypatch.setattr(module, "_fetch_window_open", dog_utils._fetch_window_open)

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

# The finals pages (R=RYP / R=BIS), trimmed from show 14014's real markup. The
# RYP section headings are the only place a show's actual rings are visible: this
# show judged FCI 5 and 6 in one ring, so it has four sections for five groups
# and exactly one RYP-1 between them.
SAMPLE_RYP_PAGE_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">FCI  3 - Terrierit</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Igoris Zizevskis</span></div>
</td></tr>
<tr><td>1.</td><td>amerikanstaffordshirenterrieri</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23">Mama Mia</a> Om. Lapuerta Katharina</td></tr>
<tr><td>2.</td><td>skotlanninterrieri</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI24070%2F26">Piccola Strega</a> Om. - -</td></tr>
<tr class="spacer"><td colspan="3"></td></tr>
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">FCI  5/6 - Pystykorvat ja alkukantaiset koirat - Ajavat ja jäljestävät koirat</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Sakari Poti</span></div>
</td></tr>
<tr><td>1.</td><td>harmaa norjanhirvikoira</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI45451%2F25">Geisterjäger</a> Om. Tolonen Mika</td></tr>
<tr class="spacer"><td colspan="3"></td></tr>
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">FCI  8 - Noutajat, ylösajavat koirat ja vesikoirat</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Ramune Kazlauskaite</span></div>
</td></tr>
<tr><td>1.</td><td>fieldspanieli</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17">Field Of Dreams</a> Om. Omistaja F</td></tr>
</table>
</div>
"""

SAMPLE_BIS_PAGE_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">Best in show</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Ramune Kazlauskaite</span></div>
</td></tr>
<tr><td>1.</td><td>fieldspanieli</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17">Noblefield's Gossip On Lips</a> Om.Väisänen Minna</td></tr>
<tr class="spacer"><td colspan="3"></td></tr>
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">Paras kasvattajaryhmä</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Ramune Kazlauskaite</span></div>
</td></tr>
<tr><td>1.</td><td>walesinspringerspanieli</td><td>Sunnystorm Om.Vainikainen Noora</td></tr>
</table>
</div>
"""

# The same page before any final has been judged: the table scaffold is there,
# the sections are not. "The page exists but is empty" and "the show awards no
# finals" look identical here and are told apart by the ladder, not the parser.
# A group-only show (e.g. group 10 alone): its RYP page crowns the one group it
# ran, and it awards no main BIS at all, so its BIS page stays empty.
SAMPLE_SINGLE_GROUP_RYP_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">FCI 10 - Vinttikoirat</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Sakari Poti</span></div>
</td></tr>
<tr><td>1.</td><td>afgaani</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI11111%2F20">Afgaani Yksi</a> Om. Omistaja A</td></tr>
</table>
</div>
"""

# A multi-group specialty cluster: it crowns BIS-1 directly, with no group stage
# at all, so there is a BIS page and the RYP page is empty.
SAMPLE_SPECIALTY_BIS_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">Best in show</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Carol Mulcahy</span></div>
</td></tr>
<tr><td>1.</td><td>basenji</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI22222%2F21">Basenji Yksi</a> Om. Omistaja B</td></tr>
</table>
</div>
"""

# Both groups crowned, and a BIS page holding only the junior final — day one
# of a two-day show, with the main Best in show still a day away.
SAMPLE_TWO_GROUP_RYP_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3"><div class="floatleft">FCI 5 - Pystykorvat</div></td></tr>
<tr><td>1.</td><td>basenji</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI11111%2F20">Basenji Yksi</a> Om. Omistaja A</td></tr>
<tr class="spacer"><td colspan="3"></td></tr>
<tr class="otsikko"><td colspan="3"><div class="floatleft">FCI 10 - Vinttikoirat</div></td></tr>
<tr><td>1.</td><td>afgaani</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI22222%2F21">Afgaani Yksi</a> Om. Omistaja B</td></tr>
</table>
</div>
"""

SAMPLE_SIDE_BIS_ONLY_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3"><div class="floatleft">Paras juniori</div></td></tr>
<tr><td>1.</td><td>basenji</td>
  <td><a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI11111%2F20">Basenji Yksi</a> Om. Omistaja A</td></tr>
</table>
</div>
"""

# The same ring after its photos are uploaded. Showlink swaps the placement rows
# for a captioned gallery and every show does it, within hours of the ring — the
# markup below is show 13780's `R=RYP` as served at 18:24 on 2026-09-20, trimmed
# to two placements. The caption carries place, breed, dog and owner in the same
# order the rows did.
SAMPLE_GALLERY_RYP_PAGE_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3">
  <div class="floatleft">FCI  3 - Terrierit</div>
  <div class="floatright"><span><span class="tuomariotsikko">Tuomari </span>Igoris Zizevskis</span></div>
</td></tr>
<tr class="gallery"><td colspan="3">
<div class="kuvaRivi">
<div class="kuvaLeft"><div class="kuvaDiv">
  <a class="kuvalinkki" href="https://kuvat.kennelliitto.fi/showimages/13780/GROUP_1410.jpg"><img class="pikkukuva"/></a>
</div>
<div class="kuvaTeksti">
  1. amerikanstaffordshirenterrieri<br/>
  <a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23" target="_blank">Mama Mia</a><br/>
  Om. Lapuerta Katharina
</div></div>
<div class="kuvaRight"><div class="kuvaDiv">
  <a class="kuvalinkki" href="https://kuvat.kennelliitto.fi/showimages/13780/GROUP_1171.jpg"><img class="pikkukuva"/></a>
</div>
<div class="kuvaTeksti">
  2. skotlanninterrieri<br/>
  <a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI24070%2F26" target="_blank">Piccola Strega</a><br/>
  Om. - -
</div></div>
</div>
</td></tr>
</table>
</div>
"""

# A gallery whose final places a *kennel* — the breeder group has no registered
# dog and so no link, in this rendering as in the row one.
SAMPLE_GALLERY_BIS_PAGE_HTML = """
<div id="divContent">
<table class="tulostaulukko">
<tr class="otsikko"><td colspan="3"><div class="floatleft">Best in show</div></td></tr>
<tr class="gallery"><td colspan="3">
<div class="kuvaRivi"><div class="kuvaLeft"><div class="kuvaDiv">
  <a class="kuvalinkki" href="https://kuvat.kennelliitto.fi/showimages/13780/BIS_1.jpg"><img class="pikkukuva"/></a>
</div>
<div class="kuvaTeksti">
  1. fieldspanieli<br/>
  <a href="https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17" target="_blank">Field Of Dreams</a><br/>
  Om. Omistaja F
</div></div></div>
</td></tr>
<tr class="otsikko"><td colspan="3"><div class="floatleft">Paras kasvattajaryhmä</div></td></tr>
<tr class="gallery"><td colspan="3">
<div class="kuvaRivi"><div class="kuvaLeft"><div class="kuvaDiv">
  <a class="kuvalinkki" href="https://kuvat.kennelliitto.fi/showimages/13780/BREEDER_1.jpg"><img class="pikkukuva"/></a>
</div>
<div class="kuvaTeksti">
  1. walesinspringerspanieli<br/>
  Sunnystorm<br/>
  Om. Vainikainen Noora
</div></div></div>
</td></tr>
</table>
</div>
"""

SAMPLE_EMPTY_FINALS_PAGE_HTML = """
<div id="divContent">
<table class="tulostaulukko"></table>
</div>
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

    # The first day's pre-dawn stays active: nothing has happened to continue
    # from. The final day's evening does not — the show has stopped for the night
    # without concluding, and no badge at all would read as finished.
    assert _show_live_phase(show, now=_dt(2026, 6, 27, 5)) == "active"
    assert _show_live_phase(show, now=_dt(2026, 6, 28, 22)) == "paused"


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
    assert _show_live_phase(three_day, now=_dt(2026, 6, 28, 22)) == "paused"  # Sun night

    single = {"date": "28.06.", "month": "kesäkuu 2026"}
    assert _show_live_phase(single, now=_dt(2026, 6, 28, 22)) == "paused"
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
    # The fixture's `now` is fixed but recency reads the real clock; pin it so the
    # test doesn't rot as the fixture date ages out of the recent window.
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

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
        now=datetime.datetime(2026, 6, 20, 7, 59),
    )
    show_day = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 8, 0),
    )
    evening = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 21, 0),
    )

    assert future["can_fetch"] is False
    assert future["reason"] == "future_show"
    assert future["available_from_iso"] == "2026-06-20T08:00:00"
    assert early_morning["can_fetch"] is False
    assert early_morning["reason"] == "show_morning"
    assert show_day["can_fetch"] is True
    assert show_day["reason"] == "show_day"
    assert evening["can_fetch"] is False
    assert evening["reason"] == "show_night"
    assert evening["show_state"] == "live"


def test_show_result_availability_pauses_between_show_days():
    """A multi-day live show goes quiet overnight (21:00–08:00) between days."""
    show = {"date": "20.-21.06.", "month": "kesäkuu 2026"}

    night = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 20, 23, 30),
    )
    next_morning_early = _show_result_availability(
        show,
        now=datetime.datetime(2026, 6, 21, 7, 0),
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
    # The fixture's `now` is fixed but recency reads the real clock; pin it so the
    # test doesn't rot as the fixture date ages out of the recent window.
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

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
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1, "awards": [
            {"type": "ROP", "name": "Ajibu You Are My Thrill", "owner": "Omistaja Testi",
             "text": "Ajibu You Are My Thrill, Om. Omistaja Testi"},
        ]}},
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
    # Per-breed honor rolls ride along for the whole-show view's expanded rows.
    assert data["breed_awards"]["5:3"][0]["type"] == "ROP"
    assert data["breed_awards"]["5:3"][0]["owner"] == "Omistaja Testi"
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


def _seed_live_two_breed_show(show_id, *, captured, results, extra_breeds=None, unsettled=()):
    """Index a live two-FCI-group show and persist a complete result cache that
    captured `captured` breed keys with `results` rows. Returns the breed list.

    Captured breeds are settled by default — their honour roll crowns ROP, so the
    crawler treats their rows as the breed's final result. Keys listed in
    `unsettled` are captured mid-ring instead (no ROP, fewer rows than entered),
    which is what a breed page looks like while its ring is still being judged."""
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
        "completed_breeds": {
            key: (
                {"name": key, "result_count": 1}
                if key in unsettled
                else {"name": key, "result_count": 1, "awards": [{"type": "ROP", "name": key}]}
            )
            for key in captured
        },
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
    # No finals pages unless a test supplies them: these fixtures exercise the
    # structural fallback, and an unstubbed probe would reach Showlink.
    monkeypatch.setattr(dog_result_cache, "_probe_finals_pages",
                        lambda sid, doc, delay=0.0: doc.get("finals_probe") or {})


def test_live_refresh_fetches_only_newly_judged_breeds(monkeypatch, client):
    """A settled capture is final, so a live refresh re-fetches only the breed that
    newly gained results — not the whole show."""
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
        "completed_breeds": {"5:3": {
            "name": "basenji", "result_count": 1,
            "awards": [{"type": "ROP", "name": "Basenji Dog"}],
        }},
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


def test_breed_capture_is_settled_reads_the_sources_own_ring_end():
    """A capture is final on the source's own statement that the ring ended — the
    honour roll crowns ROP. Class titles are not the breed's ROP; a championship
    suffix on it still is."""
    settled = dog_result_cache._breed_capture_is_settled
    breed = {"count": 8}

    assert settled({"result_count": 2, "awards": [{"type": "ROP"}]}, breed) is True
    assert settled({"result_count": 2, "awards": [{"type": "ROP, V-24"}]}, breed) is True

    # Mid-ring: the junior/puppy/breeder titles land before the breed is crowned.
    assert settled({"result_count": 2, "awards": [{"type": "ROP juniori"}]}, breed) is False
    assert settled({"result_count": 2, "awards": [{"type": "ROP pentu"}]}, breed) is False
    assert settled({"result_count": 2, "awards": []}, breed) is False
    # Nothing captured yet, and an entry count the index never learned.
    assert settled({"result_count": 0, "awards": [{"type": "ROP"}]}, breed) is False
    assert settled({"result_count": 2}, {"count": 0}) is False
    assert settled(None, breed) is False


def test_partial_is_mid_ring_only_not_merely_unconfirmed():
    """Three states, and conflating two of them broke a live show and the heal.

    *Partial* is a ring read while it was still being judged — worth re-fetching
    anywhere, including in settled history. *Provisional* holds every entered dog
    and is only waiting for a second fetch to agree. Treating provisional as
    "not finished" left shows 14014 and 13768 unable to settle (their single-entry
    breeds never get an honour roll, so nothing could promote them) and made the
    heal pass select most of the database."""
    partial = dog_result_cache._breed_capture_is_partial
    breed = {"count": 8}

    assert partial({"result_count": 2}, breed) is True              # 2 of 8: mid-ring
    assert partial({"result_count": 0}, breed) is True              # nothing captured
    assert partial(None, breed) is True                             # never captured
    assert partial({"result_count": 2}, {"count": 0}) is True       # entry count unknown

    assert partial({"result_count": 8}, breed) is False             # provisional, not partial
    assert partial({"result_count": 2, "awards": [{"type": "ROP"}]}, breed) is False
    assert partial({"result_count": 1}, {"count": 1}) is False      # the single-entry breed


def test_a_provisional_capture_does_not_stop_a_show_finishing():
    """Shows 14014 and 13768 read `Jatkuu` after concluding with every result in
    hand: ten and twenty-nine of their breeds held the whole entry with no honour
    roll, and requiring finality on rung 2 meant a show could never be done."""
    breeds = [
        {"name": "basenji", "count": 2, "group": "5", "breed_id": "3", "has_results": True},
        # The shape that broke it: one entry, one row, no honour roll, ever.
        {"name": "kerrynterrieri", "count": 1, "group": "3", "breed_id": "180", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP"},
            {"breedGroup": "3", "breedId": "180", "awards": "SA"},
        ],
        "completed_breeds": {
            "5:3": {"result_count": 2, "awards": [{"type": "ROP"}]},
            "3:180": {"result_count": 1},  # provisional: full rows, no ROP, unconfirmed
        },
    }

    assert dog_result_cache._breed_capture_is_provisional(doc["completed_breeds"]["3:180"], breeds[1]) is True
    assert dog_result_cache._breed_capture_is_settled(doc["completed_breeds"]["3:180"], breeds[1]) is False
    assert dog_utils._nothing_left_to_judge(doc, breeds) is True

    # A ring genuinely still in progress does stop it.
    doc["completed_breeds"]["5:3"] = {"result_count": 1}
    assert dog_utils._nothing_left_to_judge(doc, breeds) is False


def test_heal_selects_mid_ring_captures_not_provisional_ones():
    """The heal pass repairs history; a provisional capture has nothing to
    repair. Selecting on "not final" instead re-crawled most of the database on
    every run, because full rows with no honour roll are only ever promoted by a
    live re-fetch that settled history will never get."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dog_heal_partial_breeds", REPO_ROOT / "scripts" / "dog_heal_partial_breeds.py",
    )
    heal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(heal)

    breed = {"name": "basenji", "count": 8, "group": "5", "breed_id": "3", "has_results": True}
    single = {"name": "kerrynterrieri", "count": 1, "group": "3", "breed_id": "180", "has_results": True}

    assert heal._breed_capture_is_partial({"result_count": 2}, breed) is True
    assert heal._breed_capture_is_partial({"result_count": 8}, breed) is False
    assert heal._breed_capture_is_partial({"result_count": 1}, single) is False


def test_full_rows_without_rop_are_provisional_until_a_second_fetch_agrees():
    """Show 14014 froze 29 of 96 breeds — two of them the group winners its finals
    were waiting on — because full-looking rows were taken as final while the ring
    was still being judged. Full rows now stop the fast polling but stay eligible
    for re-check until a later fetch brings back the same rows."""
    settled = dog_result_cache._breed_capture_is_settled
    provisional = dog_result_cache._breed_capture_is_provisional
    breed = {"count": 8}

    first = {"result_count": 8}
    assert provisional(first, breed) is True
    assert settled(first, breed) is False

    confirmed = {"result_count": 8, "rows_confirmed_at": 1000.0}
    assert settled(confirmed, breed) is True
    assert settled({"result_count": 9, "rows_confirmed_at": 1000.0}, breed) is True

    # A single-entry breed genuinely has no honour roll, so full rows must still
    # be able to settle it — one confirming fetch, and it is done.
    assert settled({"result_count": 1, "rows_confirmed_at": 1000.0}, {"count": 1}) is True

    # ROP short-circuits the confirmation: the source has said the ring ended.
    assert provisional({"result_count": 8, "awards": [{"type": "ROP"}]}, breed) is False


def test_live_refresh_refetches_a_breed_captured_mid_ring(monkeypatch, client):
    """The regression this fixes: Showlink flags a breed as having results the
    moment its first class is judged, so a live pass captures a fraction of the
    ring. That capture is re-fetched until the ring ends, and the fuller page
    replaces the snapshot instead of duplicating it."""
    breeds = _seed_live_two_breed_show(
        13906,
        captured=["5:3", "10:7"],
        unsettled=["5:3"],
        results=[
            {"name": "Basenji Dog", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            {"name": "Afgaani Dog", "breedName": "afgaani", "breedGroup": "10", "breedId": "7"},
        ],
    )
    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        return {
            "breed": breed,
            "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}, {}], "awards": [{"type": "ROP"}]},
            "mapped_results": [
                {"name": "Basenji Dog", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
                {"name": "Basenji Bitch", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            ],
            "fetched_at": 2.0,
        }

    _patch_live_refresh(monkeypatch, 13906, breeds, fake_fetch)

    summary = dog_result_cache.crawl_result_cache_for_show(13906, source="test", workers=1)

    assert summary["status"] == "complete"
    assert fetched == ["5:3"]  # only the mid-ring breed; the settled one is left alone
    doc = dog_store._load_result_cache_doc(13906)
    assert {r["name"] for r in doc["results"]} == {"Basenji Dog", "Basenji Bitch", "Afgaani Dog"}
    # The ring is over now, so the next pass has nothing left to re-check.
    assert doc["completed_breeds"]["5:3"]["result_count"] == 2
    assert dog_result_cache._breed_capture_is_settled(doc["completed_breeds"]["5:3"], breeds[0]) is True


def test_unsettled_recheck_is_bounded_and_rotates(monkeypatch):
    """A big show can have more rings in flight than one pass should re-fetch, so
    the re-checks are capped and the cursor carries the rest to the next pass."""
    breeds = [
        {"name": f"breed-{i}", "count": 4, "group": "1", "breed_id": str(i), "has_results": True}
        for i in range(5)
    ]
    completed = {f"1:{i}": {"name": f"breed-{i}", "result_count": 1} for i in range(5)}
    doc = {}

    first = dog_result_cache._unsettled_capture_breeds(breeds, completed, doc, limit=2)
    assert [b["breed_id"] for b in first] == ["0", "1"]
    assert doc["unsettled_breed_count"] == 5

    second = dog_result_cache._unsettled_capture_breeds(breeds, completed, doc, limit=2)
    assert [b["breed_id"] for b in second] == ["2", "3"]

    # No limit (the heal pass) takes every unsettled capture in one go.
    assert len(dog_result_cache._unsettled_capture_breeds(breeds, completed, doc, limit=None)) == 5

    # Settled captures never make the list: one crowned with ROP, one whose full
    # rows a later fetch confirmed. A first sighting of full rows is provisional
    # and stays on the list.
    completed["1:0"]["awards"] = [{"type": "ROP"}]
    completed["1:1"].update({"result_count": 4, "rows_confirmed_at": 1000.0})
    completed["1:2"]["result_count"] = 4  # full rows, first sighting
    dog_result_cache._unsettled_capture_breeds(breeds, completed, doc, limit=None)
    assert doc["unsettled_breed_count"] == 3


def test_heal_crawl_leaves_provisional_captures_alone(monkeypatch, client):
    """The heal *crawl* re-selects breeds itself, so narrowing only the script's
    show list was not enough. A capture holding every entered dog with no honour
    roll has nothing to repair in settled history — the second fetch that would
    promote it only ever comes from a live crawl the show will never get again."""
    breeds = [
        {"name": "basenji", "count": 8, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "kerrynterrieri", "count": 1, "group": "3", "breed_id": "180", "has_results": True},
    ]
    seed_index_show("13918", {
        "title": "05.07.2026 Show", "date": "05.07.", "month": "heinäkuu 2026", "breeds": breeds,
    })
    dog_store._save_result_cache_doc(13918, {
        "version": dog_result_cache.RESULT_CACHE_VERSION, "show_id": 13918, "status": "complete",
        "title": "Show", "source_url": dog_showlink._source_url(13918),
        "started_at": 1, "updated_at": 1, "cached_at": 1, "total_breeds": 2,
        "completed_breeds": {
            "5:3": {"name": "basenji", "result_count": 2},          # 2 of 8: mid-ring
            "3:180": {"name": "kerrynterrieri", "result_count": 1},  # 1 of 1: provisional
        },
        "failed_breeds": {},
        "results": [
            {"name": "Basenji A", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            {"name": "Basenji B", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            {"name": "Kerry A", "breedName": "kerrynterrieri", "breedGroup": "3", "breedId": "180"},
        ],
    })

    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        return {
            "breed": breed, "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}] * 8, "awards": [{"type": "ROP"}]},
            "mapped_results": [
                {"name": f"Basenji {n}", "breedName": "basenji", "breedGroup": "5", "breedId": "3"}
                for n in "ABCDEFGH"
            ],
            "fetched_at": 2.0,
        }

    monkeypatch.setattr(dog_result_cache, "_show_detail_for_result_cache", lambda sid: {
        "id": sid, "title": "Show", "source_url": dog_showlink._source_url(sid), "breeds": breeds,
    })
    monkeypatch.setattr(dog_result_cache, "_fetch_breed_results_for_show_cache", fake_fetch)

    dog_result_cache.crawl_result_cache_for_show(13918, source="test", workers=1, heal=True)

    assert fetched == ["5:3"]  # the mid-ring ring only, never the single-entry breed


def test_heal_refetches_partial_breeds_on_a_settled_show(monkeypatch, client):
    """Healing history: a past show whose cache is complete and fresh is normally
    left alone entirely. `heal=True` reopens it and re-fetches only the breeds
    that never reached the end of their ring."""
    breeds = [
        {"name": "basenji", "count": 8, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "afgaani", "count": 2, "group": "10", "breed_id": "7", "has_results": True},
    ]
    seed_index_show("13907", {
        "title": "05.07.2026 Show", "date": "05.07.", "month": "heinäkuu 2026", "breeds": breeds,
    })
    dog_store._save_result_cache_doc(13907, {
        "version": dog_result_cache.RESULT_CACHE_VERSION, "show_id": 13907, "status": "complete",
        "title": "Show", "source_url": dog_showlink._source_url(13907),
        "started_at": 1, "updated_at": 1, "cached_at": 1, "total_breeds": 2,
        "completed_breeds": {
            "5:3": {"name": "basenji", "result_count": 2},
            "10:7": {"name": "afgaani", "result_count": 2, "awards": [{"type": "ROP"}]},
        },
        "failed_breeds": {},
        "results": [
            {"name": "Basenji A", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            {"name": "Basenji B", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            {"name": "Afgaani A", "breedName": "afgaani", "breedGroup": "10", "breedId": "7"},
            {"name": "Afgaani B", "breedName": "afgaani", "breedGroup": "10", "breedId": "7"},
        ],
    })

    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        return {
            "breed": breed,
            "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}] * 8, "awards": [{"type": "ROP"}]},
            "mapped_results": [
                {"name": f"Basenji {n}", "breedName": "basenji", "breedGroup": "5", "breedId": "3"}
                for n in "ABCDEFGH"
            ],
            "fetched_at": 2.0,
        }

    monkeypatch.setattr(dog_result_cache, "_show_detail_for_result_cache", lambda sid: {
        "id": sid, "title": "Show", "source_url": dog_showlink._source_url(sid), "breeds": breeds,
    })
    monkeypatch.setattr(dog_result_cache, "_fetch_breed_results_for_show_cache", fake_fetch)

    # Without heal the show is settled history and nothing is fetched at all.
    skipped = dog_result_cache.crawl_result_cache_for_show(13907, source="test", workers=1)
    assert skipped["status"] == "skipped"
    assert fetched == []

    summary = dog_result_cache.crawl_result_cache_for_show(13907, source="test", workers=1, heal=True)

    assert summary["status"] == "complete"
    assert fetched == ["5:3"]  # the settled afgaani ring is not re-fetched
    doc = dog_store._load_result_cache_doc(13907)
    assert len([r for r in doc["results"] if r["breedGroup"] == "5"]) == 8
    assert len([r for r in doc["results"] if r["breedGroup"] == "10"]) == 2


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
    after that confirms.

    The quiescence *window* is zeroed here so the subject is the signature
    changing, not the clock; the window itself is covered separately."""
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
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_SECONDS", 0)

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


def _finals_probe(ryp_html=None, bis_html=None, show_id=14014):
    """A `finals_probe` blob as the crawler stores it, parsed from page markup."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _parse_finals_page

    pages = {}
    for target, html in (("RYP", ryp_html), ("BIS", bis_html)):
        if html is None:
            continue
        pages[target] = {
            "sections": _parse_finals_page(BeautifulSoup(html, "html.parser"), show_id)["sections"],
        }
    return {"checked_at": 1000.0, "pages": pages}


def test_parse_finals_page_reads_a_final_rendered_as_a_photo_gallery():
    """A final is rendered two ways and the second one is the lasting one.

    Showlink swaps a final's placement rows for a captioned photo gallery once
    the pictures are uploaded, which happens within hours of the ring. Reading
    only the row form makes every show's finals pages go blank to us shortly
    after it ends: show 13780's `R=RYP` parsed as zero sections at 18:24 on
    2026-09-20 while holding all ten groups, four placements each."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _parse_finals_page

    parsed = _parse_finals_page(
        BeautifulSoup(SAMPLE_GALLERY_RYP_PAGE_HTML, "html.parser"), 13780)
    assert len(parsed["sections"]) == 1
    section = parsed["sections"][0]
    assert section["heading"] == "FCI 3 - Terrierit"
    assert section["fci_groups"] == ["3"]
    assert section["judge"] == "Igoris Zizevskis"
    # The caption gives the same four facts the row form did, reg id included —
    # which is the identity a winner is reconciled to a captured row by.
    assert [(p["place"], p["breed_name"], p["name"], p["reg_id"]) for p in section["placements"]] == [
        (1, "amerikanstaffordshirenterrieri", "Mama Mia", "FI48866/23"),
        (2, "skotlanninterrieri", "Piccola Strega", "FI24070/26"),
    ]
    assert section["placements"][0]["owner"] == "Lapuerta Katharina"
    # Which rendering served the section is recorded, because a final changing
    # shape is the failure this parser has been blind to once already.
    assert section["rendering"] == "gallery"


def test_a_gallery_breeder_group_places_a_kennel_with_no_registration():
    """The breeder-group final places a kennel in either rendering, so it carries
    no dog link and no reg id — and must still count as a published placement,
    because the finals plainly exist, while never becoming an obligation on a
    breed row that can never hold it."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _parse_finals_page

    sections = _parse_finals_page(
        BeautifulSoup(SAMPLE_GALLERY_BIS_PAGE_HTML, "html.parser"), 13780)["sections"]
    assert [s["heading"] for s in sections] == ["Best in show", "Paras kasvattajaryhmä"]
    kennel = sections[1]["placements"][0]
    assert (kennel["name"], kennel["reg_id"]) == ("Sunnystorm", "")


def test_a_show_whose_finals_went_to_photos_still_reaches_its_terminal():
    """End to end on the shape that matters: once the photos are up, the pages
    are the *only* record still being served, so a show settles off the gallery
    or not at all."""
    breeds = [
        {"name": "amerikanstaffordshirenterrieri", "count": 1, "group": "3", "breed_id": "192", "has_results": True},
        {"name": "skotlanninterrieri", "count": 1, "group": "3", "breed_id": "191", "has_results": True},
        {"name": "fieldspanieli", "count": 1, "group": "8", "breed_id": "121", "has_results": True},
        {"name": "walesinspringerspanieli", "count": 1, "group": "8", "breed_id": "130", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "3", "breedId": "192", "awards": "SA, ROP, RYP-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23"},
            {"breedGroup": "3", "breedId": "191", "awards": "SA, ROP, RYP-2",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI24070%2F26"},
            {"breedGroup": "8", "breedId": "121", "awards": "SA, ROP, RYP-1, BIS-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17"},
        ],
        "finals_probe": _finals_probe(SAMPLE_GALLERY_RYP_PAGE_HTML, SAMPLE_GALLERY_BIS_PAGE_HTML, show_id=13780),
    }
    analysis = dog_finals.analyze(doc, breeds)
    assert analysis["probe_authoritative"] is True
    assert analysis["probe"]["main_bis_awarded"] is True
    assert analysis["probe"]["missing_keys"] == []
    assert analysis["target_met"] is True


def test_a_group_crowned_only_on_a_breed_row_still_counts_as_crowned():
    """Crowned groups are unioned from the page and from the rows.

    Each is a partial view: a combined `FCI 5/6` ring is visible only on the
    page, and a show that leaves its pages empty says it only on the rows. The
    check is suspended just for the show that crowns no group anywhere — and
    suspending it whenever the *page* named none would settle an all-breed show
    the moment its BIS page published."""
    breeds = [
        {"name": "fieldspanieli", "count": 1, "group": "8", "breed_id": "121", "has_results": True},
        {"name": "venäjänajokoira", "count": 1, "group": "6", "breed_id": "64", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "8", "breedId": "121", "awards": "SA, ROP, RYP-1, BIS-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17"},
            {"breedGroup": "6", "breedId": "64", "awards": "SA, ROP"},
        ],
        # The BIS page has published; the RYP page holds nothing.
        "finals_probe": _finals_probe(SAMPLE_EMPTY_FINALS_PAGE_HTML, SAMPLE_GALLERY_BIS_PAGE_HTML, show_id=13780),
    }
    analysis = dog_finals.analyze(doc, breeds)
    assert analysis["probe"]["main_bis_awarded"] is True
    assert analysis["target_met"] is False, "group 6 is crowned nowhere"


def test_parse_finals_page_reads_rings_winners_and_reg_ids():
    """Page-shape regression for `R=RYP`. The section heading is the only place a
    combined ring is visible, and the dog link's registration number is what lets
    a winner be reconciled to a captured row without matching on names."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _parse_finals_page

    parsed = _parse_finals_page(BeautifulSoup(SAMPLE_RYP_PAGE_HTML, "html.parser"), 14014)
    sections = parsed["sections"]

    assert [section["heading"] for section in sections] == [
        "FCI 3 - Terrierit",
        "FCI 5/6 - Pystykorvat ja alkukantaiset koirat - Ajavat ja jäljestävät koirat",
        "FCI 8 - Noutajat, ylösajavat koirat ja vesikoirat",
    ]
    assert [section["fci_groups"] for section in sections] == [["3"], ["5", "6"], ["8"]]
    assert sections[0]["judge"] == "Igoris Zizevskis"
    assert sections[0]["rendering"] == "rows"
    assert sections[0]["placements"][0] == {
        "place": 1,
        "breed_name": "amerikanstaffordshirenterrieri",
        "name": "Mama Mia",
        "owner": "Lapuerta Katharina",
        "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23",
        "reg_id": "FI48866/23",
    }


def test_parse_finals_page_reads_bis_and_the_unlinked_breeder_group():
    """Page-shape regression for `R=BIS`. The breeder-group final names a kennel
    rather than a registered dog, so it carries no link and no reg id."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _parse_finals_page

    sections = _parse_finals_page(BeautifulSoup(SAMPLE_BIS_PAGE_HTML, "html.parser"), 14014)["sections"]
    assert [section["heading"] for section in sections] == ["Best in show", "Paras kasvattajaryhmä"]
    assert sections[0]["fci_groups"] == []
    assert sections[0]["placements"][0]["breed_name"] == "fieldspanieli"
    assert sections[0]["placements"][0]["reg_id"] == "FI49208/17"

    breeder = sections[1]["placements"][0]
    assert breeder["name"] == "Sunnystorm"
    assert breeder["owner"] == "Vainikainen Noora"
    assert breeder["reg_id"] == ""


def test_empty_finals_page_parses_as_no_sections():
    """An empty page is a real answer — "nothing awarded yet" — and must not be
    confused with a fetch that failed."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _parse_finals_page

    parsed = _parse_finals_page(BeautifulSoup(SAMPLE_EMPTY_FINALS_PAGE_HTML, "html.parser"), 14014)
    assert parsed["sections"] == []


def test_finals_targets_are_read_from_the_nav():
    """`_breed_list_targets_from_soup` drops R=RYP and R=BIS on purpose; the
    finals probe needs them, so it asks separately."""
    from bs4 import BeautifulSoup

    from app.dog_show.parsers import _breed_list_targets_from_soup, _finals_targets_from_soup

    html = """
    <div id="divContent">
      <a href="?Id=14014&R=3">FCI 3</a>
      <a href="?Id=14014&R=RYP">Ryhmien voittajat</a>
      <a href="?Id=14014&R=BIS">BIS</a>
      <a href="?Id=99999&R=BIS">another show</a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    assert _finals_targets_from_soup(soup, 14014) == ["RYP", "BIS"]
    assert _breed_list_targets_from_soup(soup, 14014) == ["3"]


def test_probe_finds_the_combined_ring_and_the_exact_missing_breed():
    """Show 14014's two failures, in one assertion each.

    Its BIS-1 landed on `8:121` (fieldspanieli), which the structural candidate
    rule never selected because it only ever looked at groups missing an RYP-1.
    And group 6 could not have an RYP-1 at all — the show ran a combined FCI 5/6
    ring — so the target was unreachable by construction. The finals pages say
    both things outright."""
    breeds = [
        {"name": "amerikanstaffordshirenterrieri", "count": 4, "group": "3", "breed_id": "192", "has_results": True},
        {"name": "skotlanninterrieri", "count": 2, "group": "3", "breed_id": "191", "has_results": True},
        {"name": "harmaa norjanhirvikoira", "count": 3, "group": "5", "breed_id": "6", "has_results": True},
        {"name": "venäjänajokoira", "count": 2, "group": "6", "breed_id": "64", "has_results": True},
        {"name": "fieldspanieli", "count": 2, "group": "8", "breed_id": "121", "has_results": True},
        {"name": "walesinspringerspanieli", "count": 2, "group": "8", "breed_id": "130", "has_results": True},
    ]
    doc = {
        "results": [
            # The RYP-1 winner already carries its group placement...
            {"breedGroup": "3", "breedId": "192", "awards": "SA, ROP, RYP-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23"},
            # ...and the eventual BIS-1 winner carries only its ROP: this is the
            # row the missing BIS-1 belongs on.
            {"breedGroup": "8", "breedId": "121", "awards": "SA, ROP",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17"},
        ],
        "finals_probe": _finals_probe(SAMPLE_RYP_PAGE_HTML, SAMPLE_BIS_PAGE_HTML),
    }

    analysis = dog_finals.analyze(doc, breeds)
    probe = analysis["probe"]

    # The rings as the show actually ran them: four groups, three sections.
    assert probe["ryp_ring_groups"] == [["3"], ["5", "6"], ["8"]]
    assert probe["expected_ryp_rings"] == 3
    # Three rings cover four groups, so no group is left uncrowned and nothing
    # waits for an RYP-1 that the combined ring already awarded.
    assert probe["ryp_groups_awarded"] == ["3", "5", "6", "8"]

    candidates = dog_finals.candidate_breed_keys(analysis)
    assert "8:121" in candidates                      # where BIS-1 actually is
    assert "3:192" not in candidates                  # already has its RYP-1
    # Exact, not a rotation: only breeds the pages name and our rows lack. The
    # breeder-group kennel (8:130) is not among them — no row can carry it.
    assert set(candidates) == {"3:191", "5:6", "8:121"}


def test_probe_settles_a_show_whose_group_can_never_win_a_ryp():
    """The combined-ring show settles once the pages' placements have all landed,
    with no expectation that group 6 produce an RYP-1 of its own."""
    breeds = [
        {"name": "amerikanstaffordshirenterrieri", "count": 1, "group": "3", "breed_id": "192", "has_results": True},
        {"name": "skotlanninterrieri", "count": 1, "group": "3", "breed_id": "191", "has_results": True},
        {"name": "harmaa norjanhirvikoira", "count": 1, "group": "5", "breed_id": "6", "has_results": True},
        {"name": "venäjänajokoira", "count": 1, "group": "6", "breed_id": "64", "has_results": True},
        {"name": "fieldspanieli", "count": 1, "group": "8", "breed_id": "121", "has_results": True},
        {"name": "walesinspringerspanieli", "count": 1, "group": "8", "breed_id": "130", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "3", "breedId": "192", "awards": "SA, ROP, RYP-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23"},
            {"breedGroup": "3", "breedId": "191", "awards": "SA, ROP, RYP-2",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI24070%2F26"},
            {"breedGroup": "5", "breedId": "6", "awards": "SA, ROP, RYP-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI45451%2F25"},
            {"breedGroup": "6", "breedId": "64", "awards": "SA, ROP"},
            {"breedGroup": "8", "breedId": "121", "awards": "SA, ROP, RYP-1, BIS-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17"},
            # The breeder-group winner is a kennel with no registration of its
            # own, so no row token exists for it and none is demanded.
            {"breedGroup": "8", "breedId": "130", "awards": "SA, ROP"},
        ],
        "completed_breeds": {
            f"{b['group']}:{b['breed_id']}": {"result_count": 1, "awards": [{"type": "ROP"}]}
            for b in breeds
        },
        "finals_probe": _finals_probe(SAMPLE_RYP_PAGE_HTML, SAMPLE_BIS_PAGE_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)
    assert status["probe"]["missing_keys"] == []
    assert status["finals_published"] is True
    assert status["judging_finished"] is True
    assert status["target_met"] is True

    # Group 6 never crowns anything, and that is no longer an obstacle.
    assert "6" in status["analysis"]["missing_ryp_groups"]


def test_show_awarding_no_finals_settles_on_judging_alone():
    """Show 13914's shape: a single-breed specialty that advertises no finals and
    awards none. Its finals pages are empty, and rung 2 carries it — no
    assumption about groups, BIS or show type is involved."""
    breeds = [{"name": "pyreneittenmastiffi", "count": 6, "group": "2", "breed_id": "92", "has_results": True}]
    doc = {
        "results": [{"breedGroup": "2", "breedId": "92", "awards": "SA, ROP"}],
        "completed_breeds": {"2:92": {"result_count": 6, "awards": [{"type": "ROP"}]}},
        "finals_probe": _finals_probe(SAMPLE_EMPTY_FINALS_PAGE_HTML, SAMPLE_EMPTY_FINALS_PAGE_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)
    assert status["probe"]["published"] is False
    assert status["finals_published"] is False
    assert status["target_met"] is True  # rung 2 alone


def test_show_with_finals_pending_does_not_settle_on_judging_alone():
    """The other half of that rule: rings finished but the pages already showing a
    placement we have not captured means the show is not done."""
    breeds = [
        {"name": "fieldspanieli", "count": 1, "group": "8", "breed_id": "121", "has_results": True},
        {"name": "walesinspringerspanieli", "count": 1, "group": "8", "breed_id": "130", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "8", "breedId": "121", "awards": "SA, ROP"},
            {"breedGroup": "8", "breedId": "130", "awards": "SA, ROP"},
        ],
        "completed_breeds": {
            "8:121": {"result_count": 1, "awards": [{"type": "ROP"}]},
            "8:130": {"result_count": 1, "awards": [{"type": "ROP"}]},
        },
        "finals_probe": _finals_probe(bis_html=SAMPLE_BIS_PAGE_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)
    assert status["judging_finished"] is True
    assert status["probe"]["missing_keys"] == ["8:121"]
    assert status["target_met"] is False


def test_group_only_show_settles_on_its_group_ryp_without_a_main_bis():
    """A group-only show (group 10 alone) crowns its group's RYP and no main
    BIS, so its BIS page stays empty. The pages say so outright, and nothing
    waits for a `BIS-1` that is never coming."""
    breeds = [{"name": "afgaani", "count": 1, "group": "10", "breed_id": "7", "has_results": True}]
    doc = {
        "results": [{"breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1",
                     "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI11111%2F20"}],
        "completed_breeds": {"10:7": {"result_count": 1, "awards": [{"type": "ROP"}]}},
        "finals_probe": _finals_probe(SAMPLE_SINGLE_GROUP_RYP_HTML, SAMPLE_EMPTY_FINALS_PAGE_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)
    assert status["probe"]["ryp_ring_groups"] == [["10"]]
    assert status["probe"]["missing_keys"] == []
    assert status["finals_published"] is True
    assert status["target_met"] is True
    assert status["analysis"]["has_bis1"] is False  # and that is fine


def test_specialty_cluster_settles_on_bis_with_an_empty_ryp_page():
    """A multi-group specialty cluster crowns BIS-1 with no group stage at all,
    so its RYP page is empty. An empty RYP page is not an outstanding
    obligation."""
    breeds = [
        {"name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "afgaani", "count": 1, "group": "10", "breed_id": "7", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP, BIS-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI22222%2F21"},
            {"breedGroup": "10", "breedId": "7", "awards": "SA, ROP"},
        ],
        "completed_breeds": {
            "5:3": {"result_count": 1, "awards": [{"type": "ROP"}]},
            "10:7": {"result_count": 1, "awards": [{"type": "ROP"}]},
        },
        "finals_probe": _finals_probe(SAMPLE_EMPTY_FINALS_PAGE_HTML, SAMPLE_SPECIALTY_BIS_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)
    assert status["probe"]["expected_ryp_rings"] == 0
    assert status["probe"]["missing_keys"] == []
    assert status["target_met"] is True


def test_empty_finals_pages_do_not_settle_a_show_that_is_awarding_finals():
    """Show 13564 (Killerin NORD, 271 breeds, 10 groups) settled with no BIS and
    only half its groups crowned.

    Its `R=RYP` and `R=BIS` pages are empty — this show never populates them and
    publishes its finals only as tokens appended to the winners' breed rows. The
    ladder read empty pages as "this show awards no finals" and settled the
    moment the last ring was captured, so the remaining group winners and the
    BIS were never fetched. The rows themselves said otherwise: RYP-1..4 for five
    groups and BIS JUN / BIS VET were already in the cache."""
    breeds = [
        {"name": f"breed-{g}", "count": 1, "group": str(g), "breed_id": str(g), "has_results": True}
        for g in range(1, 11)
    ]
    # Five groups crowned, junior and veteran BIS in, main BIS and five groups
    # still to come — exactly where 13564 was when it settled.
    results = []
    for g in range(1, 11):
        awards = "SA, ROP"
        if g in (3, 5, 7, 9, 10):
            awards += ", RYP-1"
        if g == 3:
            awards += ", BIS JUN-1"
        if g == 5:
            awards += ", BIS VET-1"
        results.append({"breedGroup": str(g), "breedId": str(g), "awards": awards})
    doc = {
        "results": results,
        "completed_breeds": {
            f"{g}:{g}": {"result_count": 1, "awards": [{"type": "ROP"}]} for g in range(1, 11)
        },
        "finals_probe": _finals_probe(SAMPLE_EMPTY_FINALS_PAGE_HTML, SAMPLE_EMPTY_FINALS_PAGE_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)

    # Every ring is captured, and that is not the same as the show being over.
    assert status["judging_finished"] is True
    assert status["probe"]["seen"] is True
    assert status["probe"]["published"] is False
    assert status["analysis"]["finals_observed"] is True
    assert status["target_met"] is False

    # And the finals hunt has somewhere to look: empty pages promise nothing, so
    # it falls back to the groups whose RYP-1 is still missing.
    candidates = dog_finals.candidate_breed_keys(status["analysis"])
    assert set(candidates) == {"1:1", "2:2", "4:4", "6:6", "8:8"}

    # Once the rest land, including the main BIS, it settles.
    for row in results:
        if "RYP-1" not in row["awards"]:
            row["awards"] += ", RYP-1"
    results[0]["awards"] += ", BIS-1"
    assert dog_utils._terminal_status(doc, breeds)["target_met"] is True


def test_side_bis_alone_is_not_the_main_bis_on_a_finals_page():
    """A two-day show's junior and veteran BIS land a day before the main one,
    and they sit in their own sections of the same `R=BIS` page. Counting any
    placement there as "the finals are in" settles the show a day early."""
    breeds = [
        {"name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "afgaani", "count": 1, "group": "10", "breed_id": "7", "has_results": True},
    ]
    doc = {
        "results": [
            {"breedGroup": "5", "breedId": "3", "awards": "SA, ROP, RYP-1, BIS JUN-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI11111%2F20"},
            {"breedGroup": "10", "breedId": "7", "awards": "SA, ROP, RYP-1",
             "reg_url": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI22222%2F21"},
        ],
        "completed_breeds": {
            "5:3": {"result_count": 1, "awards": [{"type": "ROP"}]},
            "10:7": {"result_count": 1, "awards": [{"type": "ROP"}]},
        },
        "finals_probe": _finals_probe(SAMPLE_TWO_GROUP_RYP_HTML, SAMPLE_SIDE_BIS_ONLY_HTML),
    }

    status = dog_utils._terminal_status(doc, breeds)
    probe = status["probe"]

    assert probe["published"] is True          # the page does hold placements
    assert probe["ryp_groups_awarded"] == ["5", "10"]
    assert probe["missing_keys"] == []         # and all of them have landed
    assert probe["main_bis_awarded"] is False  # but none of them is the main BIS
    assert status["target_met"] is False


def test_a_failed_probe_never_reads_as_no_finals():
    """A probe whose fetches all failed carries no pages. That must fall back to
    the structural rules, not settle the show — the difference between "the
    source says there are none" and "we could not ask"."""
    breeds = [
        {"name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True},
        {"name": "afgaani", "count": 1, "group": "10", "breed_id": "7", "has_results": True},
    ]
    doc = {
        "results": [{"breedGroup": "5", "breedId": "3", "awards": "SA, ROP"}],
        "completed_breeds": {
            "5:3": {"result_count": 1, "awards": [{"type": "ROP"}]},
            "10:7": {"result_count": 1, "awards": [{"type": "ROP"}]},
        },
        "finals_probe": {"checked_at": 1000.0, "pages": {}, "errors": {"RYP": "Timeout"}},
    }

    status = dog_utils._terminal_status(doc, breeds)
    assert status["probe"]["seen"] is False
    assert status["target_met"] is False  # multi-group show, no BIS-1 captured


def _tier_breeds(count=6, judges=("A", "B"), captured_count=1, entry_count=4):
    breeds = [
        {"name": f"breed-{i}", "count": entry_count, "group": "1", "breed_id": str(i),
         "has_results": True, "judge": judges[i % len(judges)]}
        for i in range(count)
    ]
    completed = {
        f"1:{i}": {"name": f"breed-{i}", "result_count": captured_count, "judge": judges[i % len(judges)]}
        for i in range(count)
    }
    return breeds, completed


def test_hot_tier_is_one_ring_per_judge():
    """A judge judges one breed, finishes it, and moves on, so at most one ring
    per judge can be moving. Two judges over six unfinished breeds means two hot
    pages, not six — the whole point of the partition."""
    breeds, completed = _tier_breeds(count=6, judges=("A", "B"))
    doc = {}

    tiers = dog_result_cache._live_tier_breeds(breeds, completed, doc, warm_limit=0, cool_limit=0)

    assert [b["breed_id"] for b in tiers["hot"]] == ["0", "1"]  # each judge's first
    assert doc["unsettled_breed_count"] == 6
    assert doc["hot_breed_count"] == 2


def test_static_breed_cools_off_without_any_judge_information():
    """The fallback wherever the queue misfires: a breed whose rows keep coming
    back unchanged leaves the hot tier on its own evidence. It needs no judge and
    no schedule, which is what makes it safe when the queue is wrong."""
    breeds, completed = _tier_breeds(count=4, judges=("A",))
    limit = dog_result_cache.RESULT_BREED_STATIC_FETCH_LIMIT
    completed["1:0"]["static_fetches"] = limit

    tiers = dog_result_cache._live_tier_breeds(breeds, completed, {}, warm_limit=10, cool_limit=0)

    # Judge A's first breed has gone quiet, so nothing is hot for them this pass
    # (breed 0 still holds the queue position — the ring may simply be slow).
    assert tiers["hot"] == []
    assert {b["breed_id"] for b in tiers["warm"]} == {"0", "1", "2", "3"}


def test_cool_sweep_rotates_over_finished_breeds():
    """Goal 2's protection: breeds that look finished keep being re-read while the
    show is live, because a club secretary can register a row long after its ring
    ended. Bounded per pass and rotating, so a 96-breed show costs a handful of
    requests a minute and still comes round within the hour."""
    breeds, completed = _tier_breeds(count=4, judges=("A",))
    for key in completed:
        completed[key]["awards"] = [{"type": "ROP"}]  # all finished
    doc = {}

    first = dog_result_cache._live_tier_breeds(breeds, completed, doc, cool_limit=2)
    second = dog_result_cache._live_tier_breeds(breeds, completed, doc, cool_limit=2)

    assert [b["breed_id"] for b in first["cool"]] == ["0", "1"]
    assert [b["breed_id"] for b in second["cool"]] == ["2", "3"]
    assert first["hot"] == [] and first["warm"] == []
    assert doc["cool_breed_count"] == 4


def test_late_row_on_a_finished_breed_is_captured_and_resets_quiescence(monkeypatch, client):
    """Goal 2, end to end. A breed is crowned ROP and its judge moves on; a row is
    then registered against it anyway. The cool sweep re-reads it, the row lands,
    and the show's quiescence window restarts instead of settling."""
    breeds = _seed_live_two_breed_show(
        13911,
        captured=["5:3", "10:7"],
        results=[
            {"name": "Basenji", "breedName": "basenji", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP"},
            {"name": "Afgaani", "breedName": "afgaani", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP"},
        ],
    )
    # Both breeds read as finished: crowned, and their judges have moved on.
    doc = dog_store._load_result_cache_doc(13911)
    for key in ("5:3", "10:7"):
        doc["completed_breeds"][key]["awards"] = [{"type": "ROP"}]
    doc["terminal_stable_seconds"] = 600.0
    doc["terminal_fingerprint"] = "stale"
    dog_store._save_result_cache_doc(13911, doc)

    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        rows = [{"name": f"Winner-{key}", "breedName": breed["name"], "breedGroup": breed["group"],
                 "breedId": breed["breed_id"], "awards": "SA, ROP"}]
        if key == "5:3":
            # The late entry: a row registered after the ring was over.
            rows.append({"name": "Latecomer", "breedName": breed["name"], "breedGroup": breed["group"],
                         "breedId": breed["breed_id"], "awards": "EH"})
        return {
            "breed": breed, "breed_key": key,
            "breed_data": {"judge": "Judge", "results": rows, "awards": [{"type": "ROP"}]},
            "mapped_results": rows,
            "fetched_at": 3.0,
        }

    _patch_live_refresh(monkeypatch, 13911, breeds, fake_fetch)
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda *a, **k: False)

    dog_result_cache.crawl_result_cache_for_show(13911, source="test", workers=1)

    assert "5:3" in fetched  # a finished breed was read again
    doc = dog_store._load_result_cache_doc(13911)
    assert any(row["name"] == "Latecomer" for row in doc["results"])
    # The row changed the signature, so the settle window starts over.
    assert doc["terminal_stable_seconds"] == 0.0
    assert doc.get("terminal_confirmed") is False


def test_show_14014_replay_lands_bis_on_the_right_breed_and_settles(monkeypatch, client):
    """The failure this rework exists for, replayed end to end.

    Show 14014 ran a combined FCI 5/6 ring, so group 6 could never crown an
    RYP-1 and the old target was unreachable by construction. Its `BIS-1` landed
    on `8:121` (fieldspanieli), a breed the structural candidate rule never
    selected because it only ever looked at groups missing an RYP-1. The show
    polled 30 wrong pages every two minutes for two days and settled
    `settled_incomplete` with a permanently wrong cache.

    With the finals pages read, the re-fetch list is exact and the show settles
    correctly."""
    breeds = [
        {"name": "amerikanstaffordshirenterrieri", "count": 1, "group": "3", "breed_id": "192", "has_results": True},
        {"name": "skotlanninterrieri", "count": 1, "group": "3", "breed_id": "191", "has_results": True},
        {"name": "harmaa norjanhirvikoira", "count": 1, "group": "5", "breed_id": "6", "has_results": True},
        {"name": "venäjänajokoira", "count": 1, "group": "6", "breed_id": "64", "has_results": True},
        {"name": "fieldspanieli", "count": 1, "group": "8", "breed_id": "121", "has_results": True},
    ]
    seed_index_show("14014", {
        "title": "06.09.2026 Suhmuran Santra", "date": "06.09.", "month": "syyskuu 2026",
        "breeds": breeds,
    })
    # Every ring captured and crowned, no finals token anywhere: the state the
    # show was actually stuck in.
    reg_by_key = {
        "3:192": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI48866%2F23",
        "3:191": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI24070%2F26",
        "5:6": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI45451%2F25",
        "8:121": "https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI49208%2F17",
        "6:64": "",
    }
    dog_store._save_result_cache_doc(14014, {
        "version": dog_result_cache.RESULT_CACHE_VERSION, "show_id": 14014,
        "status": "complete", "title": "Suhmuran Santra",
        "source_url": dog_showlink._source_url(14014),
        "started_at": 1, "updated_at": 1, "cached_at": 1, "total_breeds": len(breeds),
        "completed_breeds": {
            f"{b['group']}:{b['breed_id']}": {
                "name": b["name"], "result_count": 1, "judge": "Judge",
                "awards": [{"type": "ROP", "name": b["name"]}],
            }
            for b in breeds
        },
        "failed_breeds": {},
        "results": [
            {"name": f"Dog-{b['group']}:{b['breed_id']}", "breedName": b["name"],
             "breedGroup": b["group"], "breedId": b["breed_id"], "awards": "SA, ROP",
             "reg_url": reg_by_key[f"{b['group']}:{b['breed_id']}"]}
            for b in breeds
        ],
    })

    # The finals published while we were not looking. Re-fetching a named breed
    # now returns its row with the promised token appended, as Showlink does.
    tokens = {"3:192": "RYP-1", "3:191": "RYP-2", "5:6": "RYP-1",
              "8:121": "RYP-1, BIS-1"}
    fetched = []

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        awards = "SA, ROP" + (f", {tokens[key]}" if key in tokens else "")
        return {
            "breed": breed, "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}], "awards": [{"type": "ROP"}]},
            "mapped_results": [{
                "name": f"Dog-{key}", "breedName": breed["name"], "breedGroup": breed["group"],
                "breedId": breed["breed_id"], "awards": awards, "reg_url": reg_by_key[key],
            }],
            "fetched_at": 5.0,
        }

    _patch_live_refresh(monkeypatch, 14014, breeds, fake_fetch)
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda *a, **k: False)
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_SECONDS", 0)
    probe = _finals_probe(SAMPLE_RYP_PAGE_HTML, SAMPLE_BIS_PAGE_HTML)
    monkeypatch.setattr(
        dog_result_cache, "_probe_finals_pages",
        lambda sid, doc, delay=0.0: doc.__setitem__("finals_probe", probe) or probe,
    )

    dog_result_cache.crawl_result_cache_for_show(14014, source="test", workers=1)

    # Exactly the breeds the finals pages name — and 6:64, whose group cannot
    # crown anything, was never fetched.
    assert set(fetched) == {"3:192", "3:191", "5:6", "8:121"}

    doc = dog_store._load_result_cache_doc(14014)
    by_key = {f'{r["breedGroup"]}:{r["breedId"]}': r["awards"] for r in doc["results"]}
    assert "BIS-1" in by_key["8:121"]
    assert len(doc["results"]) == len(breeds)  # replaced in place, not duplicated

    status = dog_utils._terminal_status(doc, breeds)
    assert status["probe"]["missing_keys"] == []
    assert status["finals_published"] is True
    assert status["target_met"] is True

    # A second pass with nothing new confirms it, and the plan settles the show.
    dog_result_cache.crawl_result_cache_for_show(14014, source="test", workers=1)
    doc = dog_store._load_result_cache_doc(14014)
    assert doc["terminal_confirmed"] is True
    plan = _result_live_plan(
        {"id": 14014, "date": "06.09.", "month": "syyskuu 2026"}, doc, breeds,
        now=_hel_timestamp(2026, 9, 6, 20),
    )
    assert plan["phase"] == "settled"


def test_provisional_capture_is_promoted_by_a_second_agreeing_fetch(monkeypatch, client):
    """The integration half of the provisional rule: a breed with full rows and no
    honour roll is re-fetched, and the fetch that brings back the same rows both
    marks it final and stops it being re-fetched again."""
    breeds = _seed_live_two_breed_show(
        13916,
        captured=["5:3", "10:7"],
        unsettled=["5:3", "10:7"],
        results=[
            {"name": "Basenji", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
            {"name": "Afgaani", "breedName": "afgaani", "breedGroup": "10", "breedId": "7"},
        ],
    )
    # Both breeds have every entered dog on the page (count is 2) and no ROP —
    # what a small breed with no honour roll looks like.
    rows = {
        "5:3": [{"name": "B1", "breedName": "basenji", "breedGroup": "5", "breedId": "3"},
                {"name": "B2", "breedName": "basenji", "breedGroup": "5", "breedId": "3"}],
        "10:7": [{"name": "A1", "breedName": "afgaani", "breedGroup": "10", "breedId": "7"},
                 {"name": "A2", "breedName": "afgaani", "breedGroup": "10", "breedId": "7"}],
    }
    fetched = []
    clock = [10.0]

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        fetched.append(key)
        # Must advance across passes, not restart: a capture carrying the same
        # `fetched_at` as the previous one is the same fetch, not a confirming one.
        clock[0] += 1
        return {
            "breed": breed, "breed_key": key,
            "breed_data": {"judge": "Judge", "results": rows[key], "awards": []},
            "mapped_results": rows[key],
            "fetched_at": clock[0],
        }

    _patch_live_refresh(monkeypatch, 13916, breeds, fake_fetch)
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda *a, **k: False)

    # Pass 1: full rows arrive, but a first sighting is only provisional.
    dog_result_cache.crawl_result_cache_for_show(13916, source="test", workers=1)
    doc = dog_store._load_result_cache_doc(13916)
    entry = doc["completed_breeds"]["5:3"]
    assert entry["result_count"] == 2
    assert "rows_confirmed_at" not in entry
    assert dog_result_cache._breed_capture_is_provisional(entry, breeds[0]) is True
    assert dog_result_cache._breed_capture_is_settled(entry, breeds[0]) is False

    # Pass 2: the same rows come back, which is the confirmation.
    fetched.clear()
    dog_result_cache.crawl_result_cache_for_show(13916, source="test", workers=1)
    doc = dog_store._load_result_cache_doc(13916)
    entry = doc["completed_breeds"]["5:3"]
    assert entry["rows_confirmed_at"]
    assert dog_result_cache._breed_capture_is_settled(entry, breeds[0]) is True
    assert set(fetched) == {"5:3", "10:7"}  # it took a re-fetch to learn that

    # Pass 3: nothing unsettled is left, so neither breed is re-read for that
    # reason — only the slow cool sweep may still touch them.
    fetched.clear()
    dog_result_cache.crawl_result_cache_for_show(13916, source="test", workers=1)
    doc = dog_store._load_result_cache_doc(13916)
    assert doc["unsettled_breed_count"] == 0
    assert len(doc["results"]) == 4  # replaced in place across all three passes


def test_finals_less_show_settles_without_any_finals_ever_publishing(monkeypatch, client):
    """Quiescence settling, end to end: a show that awards no finals at all has
    nothing to wait for, and reaching `settled` must not depend on a token that
    is never coming."""
    breeds = _seed_live_two_breed_show(
        13917,
        captured=["5:3", "10:7"],
        results=[
            {"name": "Basenji", "breedName": "basenji", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP"},
            {"name": "Afgaani", "breedName": "afgaani", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP"},
        ],
    )

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        return {
            "breed": breed, "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}], "awards": [{"type": "ROP"}]},
            "mapped_results": [{
                "name": f"Dog-{key}", "breedName": breed["name"], "breedGroup": breed["group"],
                "breedId": breed["breed_id"], "awards": "SA, ROP",
            }],
            "fetched_at": 9.0,
        }

    _patch_live_refresh(monkeypatch, 13917, breeds, fake_fetch)
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda *a, **k: False)
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_SECONDS", 0)
    empty = _finals_probe(SAMPLE_EMPTY_FINALS_PAGE_HTML, SAMPLE_EMPTY_FINALS_PAGE_HTML)
    monkeypatch.setattr(
        dog_result_cache, "_probe_finals_pages",
        lambda sid, doc, delay=0.0: doc.__setitem__("finals_probe", empty) or empty,
    )

    for _ in range(3):
        dog_result_cache.crawl_result_cache_for_show(13917, source="test", workers=1)

    doc = dog_store._load_result_cache_doc(13917)
    assert doc["terminal_confirmed"] is True
    plan = _result_live_plan(
        {"id": 13917, "date": "28.06.", "month": "kesäkuu 2026"}, doc, breeds,
        now=_hel_timestamp(2026, 6, 28, 19),
    )
    assert plan["phase"] == "settled"


def test_live_state_survives_the_doc_rebuild_between_passes(monkeypatch, client):
    """Every pass rebuilds the working doc from the cache, so anything the settle
    machinery accumulates has to be carried across explicitly.

    Dropping the quiescence accumulator would restart the settle window on every
    pass and a show could never settle on stability at all; dropping the finals
    probe would make each pass start blind to finals it had already read."""
    breeds = _seed_live_two_breed_show(
        13915,
        captured=["5:3", "10:7"],
        results=[
            {"name": "Basenji", "breedName": "basenji", "breedGroup": "5", "breedId": "3", "awards": "SA, ROP"},
            {"name": "Afgaani", "breedName": "afgaani", "breedGroup": "10", "breedId": "7", "awards": "SA, ROP"},
        ],
    )

    def fake_fetch(sid, breed):
        key = f'{breed["group"]}:{breed["breed_id"]}'
        return {
            "breed": breed, "breed_key": key,
            "breed_data": {"judge": "Judge", "results": [{}], "awards": [{"type": "ROP"}]},
            "mapped_results": [{
                "name": f"Dog-{key}", "breedName": breed["name"], "breedGroup": breed["group"],
                "breedId": breed["breed_id"], "awards": "SA, ROP",
            }],
            "fetched_at": 7.0,
        }

    _patch_live_refresh(monkeypatch, 13915, breeds, fake_fetch)
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda *a, **k: False)
    probe = _finals_probe(SAMPLE_EMPTY_FINALS_PAGE_HTML, SAMPLE_EMPTY_FINALS_PAGE_HTML)
    monkeypatch.setattr(
        dog_result_cache, "_probe_finals_pages",
        lambda sid, doc, delay=0.0: doc.__setitem__("finals_probe", probe) or probe,
    )

    clock = [1000.0]
    monkeypatch.setattr(dog_result_cache, "_mark_terminal_confirmation", (
        lambda doc, indexed, now=None, _real=dog_result_cache._mark_terminal_confirmation:
        _real(doc, indexed, now=clock[0])
    ))

    dog_result_cache.crawl_result_cache_for_show(13915, source="test", workers=1)
    clock[0] += 120
    dog_result_cache.crawl_result_cache_for_show(13915, source="test", workers=1)
    clock[0] += 120
    dog_result_cache.crawl_result_cache_for_show(13915, source="test", workers=1)

    doc = dog_store._load_result_cache_doc(13915)
    assert doc["terminal_stable_seconds"] == 240.0   # accumulated across passes
    assert doc["finals_probe"]["pages"]              # the probe survived too


def test_quiescence_counts_only_observed_time(monkeypatch):
    """A show settles on stability it actually watched accumulate.

    Two traps this closes: the overnight gap must not count (the crawler was not
    looking, so the silence is not evidence), and a lunch break must not be able
    to settle a show whose rings are still unjudged — which is why the target has
    to be met as well as the window filled."""
def test_the_default_quiescence_window_outlasts_a_real_mid_show_lull(monkeypatch):
    """The window has to be longer than a show goes quiet while still judging.

    Measured on two NORD shows on 2026-09-19: gaps of 18, 14, 12, 12 and 10
    minutes between result rows during active judging. At the old 900s a
    mid-afternoon lull filled the window on its own, leaving only `target_met`
    between a half-judged show and settling."""
    mark = dog_result_cache._mark_terminal_confirmation
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_MAX_GAP", 360)

    breeds = [{"name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True}]
    doc = {
        "results": [{"breedGroup": "5", "breedId": "3", "awards": "SA, ROP"}],
        "completed_breeds": {"5:3": {"result_count": 1, "awards": [{"type": "ROP"}]}},
        "finals_probe": {"pages": {"RYP": {"sections": []}, "BIS": {"sections": []}}},
    }

    # 18 minutes of silence, watched in passes no wider than the max gap. This is
    # the longest lull actually measured, and it used to be enough on its own.
    for offset in (0, 300, 600, 900, 1080):
        mark(doc, breeds, now=1_000_000 + offset)
    assert 1080 > 900, "the old window was inside the measured noise"
    assert doc["terminal_confirmed"] is False

    # Carried out to 35 minutes, it does settle.
    for offset in (1380, 1680, 1980, 2100):
        mark(doc, breeds, now=1_000_000 + offset)
    assert doc["terminal_confirmed"] is True


    mark = dog_result_cache._mark_terminal_confirmation
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_SECONDS", 900)
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_MAX_GAP", 360)

    breeds = [{"name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True}]
    doc = {
        "results": [{"breedGroup": "5", "breedId": "3", "awards": "SA, ROP"}],
        "completed_breeds": {"5:3": {"result_count": 1, "awards": [{"type": "ROP"}]}},
        "finals_probe": {"pages": {"RYP": {"sections": []}, "BIS": {"sections": []}}},
    }

    # Four passes two minutes apart: 6 minutes of watched stability, not 15.
    for offset in range(4):
        mark(doc, breeds, now=1000.0 + offset * 120)
    assert doc["terminal_stable_seconds"] == 360.0
    assert doc["terminal_confirmed"] is False

    # The night: one pass at 20:58 and the next at 08:00. The gap is longer than
    # any pass interval, so it contributes nothing at all.
    mark(doc, breeds, now=1000.0 + 40000)
    assert doc["terminal_stable_seconds"] == 360.0
    assert doc["terminal_confirmed"] is False

    # Watched stability resumes and completes the window.
    now = 1000.0 + 40000
    for _ in range(5):
        now += 120
        mark(doc, breeds, now=now)
    assert doc["terminal_stable_seconds"] == 960.0
    assert doc["terminal_confirmed"] is True

    # A late row restarts the window — goal 2, in one assertion.
    doc["results"].append({"breedGroup": "5", "breedId": "3", "awards": "EH"})
    mark(doc, breeds, now=now + 120)
    assert doc["terminal_stable_seconds"] == 0.0
    assert doc["terminal_confirmed"] is False


def test_quiescence_accumulates_before_the_target_is_met(monkeypatch):
    """Stability must accumulate whether or not the target is met.

    The previous version reset the counter on every pass where it was not, so a
    show with an unreachable terminal — a combined `FCI 5/6` ring, a show that
    awards no BIS — could never build evidence that it had simply stopped, and
    polled to the two-day deadline instead."""
    mark = dog_result_cache._mark_terminal_confirmation
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_SECONDS", 300)
    monkeypatch.setattr(dog_result_cache, "RESULT_QUIESCENCE_MAX_GAP", 360)

    # A breed still mid-ring: the target cannot be met.
    breeds = [{"name": "basenji", "count": 8, "group": "5", "breed_id": "3", "has_results": True}]
    doc = {
        "results": [{"breedGroup": "5", "breedId": "3", "awards": "EH"}],
        "completed_breeds": {"5:3": {"result_count": 2}},
    }
    for offset in range(4):
        mark(doc, breeds, now=1000.0 + offset * 120)

    assert doc["terminal_target_met"] is False
    assert doc["terminal_stable_seconds"] == 360.0  # accumulated regardless
    assert doc["terminal_confirmed"] is False       # but never confirms on its own


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


@pytest.mark.parametrize("hour,open_window", [
    (0, False), (3, False), (7, False), (8, True), (12, True), (20, True), (21, False), (23, False),
])
def test_live_plan_obeys_the_fetch_window_on_the_final_day(hour, open_window):
    """A final day still owing its finals stops at 21:00 like everything else.

    No dog show runs at night, so the finals typed in after the cutoff are worth
    less than a quiet night; the next morning's rescue pass collects them, well
    inside the settle deadline."""
    show = {"id": 13786, "date": "04.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))  # only group 9 has RYP-1, no BIS-1
    plan = _result_live_plan(show, doc, _all_breed_breeds(), now=_hel_timestamp(2026, 7, 4, hour))
    assert plan["phase"] == "live"
    assert plan["can_fetch"] is open_window
    assert plan["expects_finals"] is True
    assert plan["target_met"] is False


def test_live_plan_finals_owed_at_night_resumes_next_morning_unsettled():
    """The accepted cost of the night stop: a show that ended still owing its
    finals must wait, not settle. It stays a fetchable rescue candidate when the
    window reopens."""
    show = {"id": 13786, "date": "04.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))
    breeds = _all_breed_breeds()

    night = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 7, 4, 22))
    morning = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 7, 5, 8))

    assert night["can_fetch"] is False
    assert night["phase"] == "live"
    assert morning["phase"] == "rescue"
    assert morning["can_fetch"] is True


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


def test_live_plan_non_final_night_stays_quiet():
    """A multi-day show's first-night lull: quiet until the morning, still live."""
    show = {"id": 13500, "date": "04.-05.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))
    plan = _result_live_plan(show, doc, _all_breed_breeds(), now=_hel_timestamp(2026, 7, 4, 22))
    assert plan["phase"] == "live"
    assert plan["is_final_day"] is False
    assert plan["can_fetch"] is False


def test_live_plan_rescue_hard_stops_overnight():
    """Post-show rescue keeps fetching the owed finals during the day and stops
    overnight, on the same window as everything else."""
    show = {"id": 13786, "date": "04.07.", "month": "heinäkuu 2026"}
    doc = _live_plan_doc(ryp1_groups=(9,))
    breeds = _all_breed_breeds()
    day = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 7, 5, 10))
    night = _result_live_plan(show, doc, breeds, now=_hel_timestamp(2026, 7, 5, 3))
    assert day["phase"] == "rescue" and day["can_fetch"] is True
    assert night["phase"] == "rescue" and night["can_fetch"] is False


def test_live_plan_single_group_show_does_not_rescue():
    """A single-FCI-group show (e.g. group 10 only) crowns junior/veteran/utility
    BIS but no main BIS-1. It must settle when its date passes — not rescue-poll
    for two days waiting for a BIS-1 that never comes (show 13664)."""
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


def test_auto_result_cache_candidates_decide_settled_shows_from_dates_alone(monkeypatch, client):
    """The Tulokset list carries the whole season (hundreds of settled shows), and
    only shows inside the auto window can ever become candidates. The selection
    must gate on the list row's date alone — a settled or upcoming show costs no
    result-doc load (the doc hydration was the crawler's idle CPU baseline)."""
    now = datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    shows = [
        {"id": 13001, "date": "10.01.", "name": "Talvinäyttely", "month": "tammikuu 2026"},
        {"id": 13002, "date": "15.08.", "name": "Syysnäyttely", "month": "elokuu 2026"},
        {"id": 13771, "date": "20.-21.06.", "name": "Jyväskylä KV", "month": "kesäkuu 2026"},
    ]
    monkeypatch.setattr(dog_result_cache, "_get_show_list", lambda: shows)
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)
    seed_index_show("13771", {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True},
        ],
    })

    loaded = []
    real_load = dog_result_cache._load_result_cache_doc
    def counting_load(show_id):
        loaded.append(int(show_id))
        return real_load(show_id)
    monkeypatch.setattr(dog_result_cache, "_load_result_cache_doc", counting_load)

    candidates = dog_result_cache._auto_result_cache_candidates(now)

    assert [candidate["show_id"] for candidate in candidates] == [13771]
    assert set(loaded) == {13771}


@pytest.mark.parametrize("hour,open_window", [
    (0, False), (3, False), (7, False), (8, True), (12, True), (20, True), (21, False), (23, False),
])
def test_in_fetch_window_boundaries(hour, open_window):
    """The one window every fetching path shares: 08:00–21:00 Finnish local."""
    assert _in_fetch_window(hour) is open_window


def test_index_pass_splits_discovery_live_and_recent_cadences(monkeypatch):
    """Three jobs on one budget meant the slowest set the rate for all of them.

    Discovery is never rate-limited — a show absent from the index has no page at
    all. A show being judged today is the cheap tier the result crawler steers
    by, so it is re-read in minutes. Everything else in the recent window drifts
    over weeks and must not eat the budget."""
    now = 10_000_000.0
    shows = [
        {"id": 14060, "date": "06.09.", "month": "syyskuu 2026", "name": "live-fresh"},
        {"id": 14061, "date": "06.09.", "month": "syyskuu 2026", "name": "live-stale"},
        {"id": 14062, "date": "20.09.", "month": "syyskuu 2026", "name": "recent-fresh"},
        {"id": 14063, "date": "20.09.", "month": "syyskuu 2026", "name": "recent-stale"},
        {"id": 14064, "date": "20.09.", "month": "syyskuu 2026", "name": "never-indexed"},
    ]
    ages = {
        14060: dog_crawler.INDEX_LIVE_TTL - 60,      # judged today, just read
        14061: dog_crawler.INDEX_LIVE_TTL + 60,      # judged today, due
        14062: dog_crawler.INDEX_RECENT_TTL - 3600,  # upcoming, recently read
        14063: dog_crawler.INDEX_RECENT_TTL + 3600,  # upcoming, due
    }
    for sid, age in ages.items():
        seed_index_show(str(sid), {
            "title": f"show {sid}", "date": "", "month": "", "updated_at": now - age,
            "breeds": [{"name": "basenji", "count": 1, "group": "5", "breed_id": "3"}],
        })

    monkeypatch.setattr(dog_crawler, "_get_show_list", lambda: shows)
    monkeypatch.setattr(dog_crawler.time, "time", lambda: now)
    monkeypatch.setattr(dog_crawler, "_show_date_state",
                        lambda show, today=None: "live" if show["date"] == "06.09." else "upcoming")
    monkeypatch.setattr(dog_crawler, "_show_is_recent", lambda show, today=None: True)

    updated = []
    monkeypatch.setattr(dog_crawler, "_update_index_show", lambda show: updated.append(show["id"]))

    summary = dog_crawler.crawl_index_once(delay=0)

    # Never-indexed first, then today's stale show, then the slow drift.
    assert updated == [14064, 14061, 14063]
    assert summary["missing_candidates"] == 1
    assert summary["live_candidates"] == 1
    assert summary["recent_candidates"] == 1


# The window's edges, and the two hours that used to be inside it: 06:00 (the old
# morning) and 23:00 (the old finals overtime tail).
_WINDOW_BOUNDARY_HOURS = [
    ((0, 30), False), ((3, 0), False), ((6, 0), False), ((7, 59), False),
    ((8, 0), True), ((12, 0), True), ((20, 59), True),
    ((21, 0), False), ((23, 0), False),
]


@pytest.mark.parametrize("clock,open_window", _WINDOW_BOUNDARY_HOURS)
def test_index_pass_fetches_only_inside_the_window(monkeypatch, real_fetch_window, clock, open_window):
    """The index pass had no clock check at all and re-indexed shows all night.
    Outside the window it must not even reach the show list."""
    hour, minute = clock
    fetched = []
    monkeypatch.setattr(dog_crawler, "_get_show_list", lambda: fetched.append("list") or [])
    monkeypatch.setattr(dog_utils, "_local_now",
                        lambda: datetime.datetime(2026, 9, 6, hour, minute))

    summary = dog_crawler.crawl_index_once(limit=2, delay=0)

    assert (fetched == ["list"]) is open_window
    assert (summary.get("reason") == "outside_fetch_window") is not open_window


@pytest.mark.parametrize("clock,open_window", _WINDOW_BOUNDARY_HOURS)
def test_show_list_refresh_is_gated_by_the_window(monkeypatch, real_fetch_window, clock, open_window):
    """`_get_show_list` is reachable from request paths, so the gate lives inside
    it rather than at the call sites: a visitor at 02:00 gets the cached list,
    never a Showlink fetch."""
    hour, minute = clock
    fetched = []

    def _fake_fetch(url):
        fetched.append(url)
        from bs4 import BeautifulSoup
        return BeautifulSoup(SAMPLE_SHOW_LIST_HTML, "html.parser")

    monkeypatch.setattr(dog_shows, "_fetch_page", _fake_fetch)
    # `_get_show_list` evaluates the window against an explicit timestamp, so the
    # clock has to be pinned at `_local_dt`, not `_local_now`.
    monkeypatch.setattr(dog_utils, "_local_dt",
                        lambda now=None: datetime.datetime(2026, 9, 6, hour, minute))
    cached = [{"id": 14042, "date": "14.06.", "month": "kesäkuu 2026"}]
    _show_list_cache["data"] = list(cached)
    _show_list_cache["ts"] = 0  # stale: only the window can hold it shut

    shows = dog_shows._get_show_list()

    assert (len(fetched) == 1) is open_window
    # Outside the window the stale cache is served rather than nothing: the show
    # list only changes when a new show is announced.
    if not open_window:
        assert shows == cached


def test_show_list_cold_cache_populates_once_outside_the_window(monkeypatch, real_fetch_window):
    """A process that starts at night has nothing to serve, so it populates once.
    One request per process start is not polling — and /dog has to render."""
    calls = []

    def _fake_fetch(url):
        calls.append(url)
        from bs4 import BeautifulSoup
        return BeautifulSoup(SAMPLE_SHOW_LIST_HTML, "html.parser")

    monkeypatch.setattr(dog_shows, "_fetch_page", _fake_fetch)
    # Pin at `_local_dt`: `_get_show_list` evaluates the window against an
    # explicit timestamp, so patching `_local_now` alone leaves it on the real
    # clock and the test passes or fails by the time of day.
    monkeypatch.setattr(dog_utils, "_local_dt",
                        lambda now=None: datetime.datetime(2026, 9, 6, 2, 0))
    _show_list_cache["data"] = None
    _show_list_cache["ts"] = 0

    first = dog_shows._get_show_list()
    _show_list_cache["ts"] = 0  # expire the TTL; the window must still hold it shut
    second = dog_shows._get_show_list()

    assert len(first) == 2
    assert second == first
    assert len(calls) == 1


def test_crawl_index_once_updates_stalest_recent_shows_first(monkeypatch):
    """A bounded maintenance pass must round-robin the recent window across passes
    (stalest first), not re-fetch the same first-N list rows forever."""
    shows = [
        {"id": 14051, "date": "", "month": "", "name": "A"},
        {"id": 14052, "date": "", "month": "", "name": "B"},
        {"id": 14053, "date": "", "month": "", "name": "C"},
    ]
    for sid, updated_at in ((14051, 300), (14052, 100), (14053, 200)):
        seed_index_show(str(sid), {
            "title": f"show {sid}",
            "updated_at": updated_at,
            "breeds": [
                {"name": "basenji", "count": 1, "group": "5", "breed_id": "3"},
            ],
        })
    monkeypatch.setattr(dog_crawler, "_get_show_list", lambda: shows)

    updated_order = []
    monkeypatch.setattr(
        dog_crawler, "_update_index_show",
        lambda show: updated_order.append(show["id"]),
    )

    summary = dog_crawler.crawl_index_once(limit=2, delay=0)

    assert updated_order == [14052, 14053]
    assert summary["updated"] == 2


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
    # The fixture's `now` is fixed but recency reads the real clock; pin it so the
    # test doesn't rot as the fixture date ages out of the recent window.
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)

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

def _search_result_row(number, name, group="5", breed="3", comp="", reg_url=""):
    return {
        "number": number, "name": name, "reg_url": reg_url, "grade": "ERI",
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
    """Dog matches are capped per entity type — registered dogs at
    SEARCH_ENTITY_SHOW_LIMIT distinct dogs, reg-less per-show fallback hits at
    SEARCH_UNREGISTERED_SHOW_LIMIT — so a common substring can't return the
    whole database."""
    from app.dog_show import search as dog_search
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    for i in range(dog_search.SEARCH_ENTITY_SHOW_LIMIT + 5):
        _seed_search_doc(15000 + i, [
            _search_result_row(1, "Tähti Dog", reg_url=f"https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo=FI{i:05d}%2F20"),
            _search_result_row(2, "Tähti Kennelitön"),
        ])

    resp = client.get("/api/dog/search?q=tähti")
    assert resp.status_code == 200
    dog_results = [r for r in resp.get_json()["results"] if r["match"] == "dog"]
    registered = [r for r in dog_results if r.get("reg_id")]
    fallback = [r for r in dog_results if not r.get("reg_id")]
    assert len(registered) == dog_search.SEARCH_ENTITY_SHOW_LIMIT
    assert len(fallback) == dog_search.SEARCH_UNREGISTERED_SHOW_LIMIT


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


@patch("app.dog_show.showlink._SESSION.get")
def test_search_results_ordered_by_show_date_newest_first(mock_get, client):
    """Show date is the primary ordering across every match type: newest show
    first, with dog/owner matches interleaved by date instead of appended last
    and id order only breaking date ties."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    # Two indexed-only breed matches whose id order contradicts their date order,
    # plus a dog-name match in the newest show (dated via its title, like real
    # index entries — 14.06.2026 from _seed_search_doc's title).
    seed_index_show("13001", {
        "title": "10.05.2026 Keväthaku", "name": "Keväthaku", "date": "10.05.2026",
        "month": "toukokuu 2026",
        "breeds": [{"name": "hakubasenji", "count": 5, "group": "5", "breed_id": "3", "has_results": True}],
    })
    seed_index_show("13002", {
        "title": "20.03.2026 Talvihaku", "name": "Talvihaku", "date": "20.03.2026",
        "month": "maaliskuu 2026",
        "breeds": [{"name": "hakubasenji", "count": 5, "group": "5", "breed_id": "3", "has_results": True}],
    })
    _seed_search_doc(13003, [_search_result_row(1, "Hakubasenji Superstar")])

    resp = client.get("/api/dog/search?q=hakubasenji")

    assert resp.status_code == 200
    ordered = [(r["show"]["id"], r["match"]) for r in resp.get_json()["results"]]
    assert ordered == [
        (13003, "dog"),      # 14.06.2026
        (13001, "breed"),    # 10.05.2026
        (13002, "breed"),    # 20.03.2026
    ]


# --- Dog profile + reg_id aggregation + owner/kennel deep links (Phase E) ---

def _reg_url(reg_no):
    return f"https://jalostus.kennelliitto.fi/frmKoira.aspx?RekNo={reg_no.replace('/', '%2F')}"


@patch("app.dog_show.showlink._SESSION.get")
def test_search_aggregates_dog_hits_by_reg_id(mock_get, client):
    """A registered dog appearing in several shows is one search hit: aggregated
    by reg_id, anchored to its newest show, named by its newest-show spelling."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(16001, [_search_result_row(1, "AAMUN TÄHTI", reg_url=_reg_url("FI11111/20"))])
    _seed_search_doc(16002, [_search_result_row(1, "Aamun Tähti", reg_url=_reg_url("FI11111/20"))])
    seed_index_show("16001", {"title": "10.05.2026 Vanha Show", "date": "10.05.2026", "month": "toukokuu 2026",
                              "breeds": [{"name": "breed-3", "count": 1, "group": "5", "breed_id": "3", "has_results": True}]})
    seed_index_show("16002", {"title": "14.06.2026 Uusi Show", "date": "14.06.2026", "month": "kesäkuu 2026",
                              "breeds": [{"name": "breed-3", "count": 1, "group": "5", "breed_id": "3", "has_results": True}]})

    resp = client.get("/api/dog/search?q=aamun")
    assert resp.status_code == 200
    dog_results = [r for r in resp.get_json()["results"] if r["match"] == "dog"]
    assert len(dog_results) == 1
    hit = dog_results[0]
    assert hit["reg_id"] == "FI11111/20"
    assert hit["dog"] == "Aamun Tähti"          # newest-show spelling
    assert hit["show"]["id"] == 16002            # anchored to the newest show
    assert hit["show_count"] == 2
    assert hit["dog_match_count"] == 2


@patch("app.dog_show.showlink._SESSION.get")
def test_search_owner_hits_carry_breed_coordinates_and_winner(mock_get, client):
    """Owner hits deep-link: one hit per breed honor roll with group/breed_id,
    the winning dog, and the breed name so the client can open the breed page."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(
        16011,
        [_search_result_row(1, "Voittaja Koira")],
        completed_breeds={"5:3": {"name": "breed-3", "result_count": 1, "judge": "J", "awards": [
            {"type": "ROP", "name": "Voittaja Koira", "owner": "Mäkelä Maija", "text": "Voittaja Koira, Om. Mäkelä Maija"},
        ]}},
    )

    resp = client.get("/api/dog/search?q=mäkelä")
    assert resp.status_code == 200
    owner_results = [r for r in resp.get_json()["results"] if r["match"] == "owner"]
    assert len(owner_results) == 1
    hit = owner_results[0]
    assert hit["show"]["id"] == 16011
    assert hit["owner"] == "Mäkelä Maija"
    assert hit["winner"] == "Voittaja Koira"
    assert hit["group"] == "5"
    assert hit["breed_id"] == "3"
    assert hit["breed_name"] == "breed-3"
    assert hit["owner_match_count"] == 1


@patch("app.dog_show.showlink._SESSION.get")
def test_search_finds_kennel_from_breeder_awards(mock_get, client):
    """Breeder-award kennels are searchable as their own match type, restricted
    to kasvattaja award rows (a plain ROP winner named like the query is not a
    kennel hit), and carry the breed coordinates for deep-linking."""
    mock_resp = MagicMock(); mock_resp.text = SAMPLE_SHOW_LIST_HTML; mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    _seed_search_doc(
        16021,
        [_search_result_row(1, "Bluemeadow's Hero")],
        completed_breeds={"5:3": {"name": "breed-3", "result_count": 1, "judge": "J", "awards": [
            {"type": "ROP", "name": "Bluemeadow's Hero", "owner": "Kattainen Kirsi", "text": "Bluemeadow's Hero, Om. Kattainen Kirsi"},
            {"type": "ROP kasvattaja", "name": "Bluemeadow's", "owner": "Kattainen Kirsi", "text": "Bluemeadow's, Om. Kattainen Kirsi"},
        ]}},
    )

    resp = client.get("/api/dog/search?q=bluemeadow")
    assert resp.status_code == 200
    kennel_results = [r for r in resp.get_json()["results"] if r["match"] == "kennel"]
    assert len(kennel_results) == 1
    hit = kennel_results[0]
    assert hit["show"]["id"] == 16021
    assert hit["kennel"] == "Bluemeadow's"
    assert hit["group"] == "5"
    assert hit["breed_id"] == "3"
    assert hit["breed_name"] == "breed-3"
    assert hit["kennel_match_count"] == 1


def test_dog_profile_returns_results_across_shows_newest_first(client):
    """The profile aggregates every captured result row for one reg_id, sorted
    by show date (newest first) even when show ids contradict date order, with
    identity taken from the newest entry."""
    _seed_search_doc(16032, [_search_result_row(1, "VANHA NIMI", comp="PN2", reg_url=_reg_url("FI22222/19"))])
    _seed_search_doc(16031, [_search_result_row(1, "Uusi Nimi", comp="PN1", reg_url=_reg_url("FI22222/19"))])
    # Lower id 16031 carries the *newer* date.
    seed_index_show("16032", {"title": "10.05.2026 Vanha Show", "name": "Vanha Show", "date": "10.05.2026",
                              "month": "toukokuu 2026",
                              "breeds": [{"name": "breed-3", "count": 1, "group": "5", "breed_id": "3", "has_results": True}]})
    seed_index_show("16031", {"title": "14.06.2026 Uusi Show", "name": "Uusi Show", "date": "14.06.2026",
                              "month": "kesäkuu 2026",
                              "breeds": [{"name": "breed-3", "count": 1, "group": "5", "breed_id": "3", "has_results": True}]})

    resp = client.get("/api/dog/dogs", query_string={"reg": "FI22222/19"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["reg_id"] == "FI22222/19"
    assert data["name"] == "Uusi Nimi"
    assert data["show_count"] == 2
    assert data["result_count"] == 2
    assert [e["show"]["id"] for e in data["entries"]] == [16031, 16032]
    assert data["entries"][0]["competitive_placement"] == "PN1"
    assert data["entries"][0]["grade"] == "ERI"
    assert data["entries"][0]["show"]["name"] == "Uusi Show"


def test_dog_profile_owner_from_breed_awards(client):
    """Header owner comes from the newest honor-roll row matching the dog by
    (show, breed, name) — award rows carry no reg_id."""
    _seed_search_doc(
        16041,
        [_search_result_row(1, "Palkittu Koira", reg_url=_reg_url("FI33333/21"))],
        completed_breeds={"5:3": {"name": "breed-3", "result_count": 1, "judge": "J", "awards": [
            {"type": "ROP", "name": "PALKITTU KOIRA", "owner": "Nieminen Noora", "text": "Palkittu Koira, Om. Nieminen Noora"},
        ]}},
    )

    resp = client.get("/api/dog/dogs", query_string={"reg": "FI33333/21"})
    assert resp.status_code == 200
    assert resp.get_json()["owner"] == "Nieminen Noora"


def test_dog_profile_unknown_reg_returns_404(client):
    resp = client.get("/api/dog/dogs", query_string={"reg": "FI00000/00"})
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_dog_profile_missing_or_long_reg_returns_400(client):
    assert client.get("/api/dog/dogs").status_code == 400
    assert client.get("/api/dog/dogs", query_string={"reg": "  "}).status_code == 400
    assert client.get("/api/dog/dogs", query_string={"reg": "X" * 41}).status_code == 400


def test_sqlstore_results_by_reg_id(client):
    """Direct sqlstore read: exact reg_id equality (no LIKE), newest show first,
    seq order within a show, reg-less rows never returned."""
    _seed_search_doc(16051, [
        _search_result_row(1, "Rekisteröity", reg_url=_reg_url("FI44444/22")),
        _search_result_row(2, "Rekisteritön"),
    ])
    _seed_search_doc(16052, [_search_result_row(1, "Rekisteröity", reg_url=_reg_url("FI44444/22"))])

    with dog_db.session_scope() as session:
        rows = dog_sqlstore.read_results_by_reg_id(session, "FI44444/22")
        assert [r["show_id"] for r in rows] == [16052, 16051]
        assert all(r["name"] == "Rekisteröity" for r in rows)
        assert dog_sqlstore.read_results_by_reg_id(session, "") == []
        # A partial reg is not a match — equality, not LIKE.
        assert dog_sqlstore.read_results_by_reg_id(session, "FI44444") == []


def test_sqlstore_search_dogs_by_name_groups_and_orders(client):
    """Direct sqlstore aggregation: unicode-cased matches group under one reg_id,
    ordered newest-show-first, wildcards escaped, reg-less rows excluded."""
    _seed_search_doc(16061, [
        _search_result_row(1, "TÄHTI TAIVAALLA", reg_url=_reg_url("FI55555/23")),
        _search_result_row(2, "Tähti Kennelitön"),
    ])
    _seed_search_doc(16062, [_search_result_row(1, "Tähti Taivaalla", reg_url=_reg_url("FI55555/23"))])
    _seed_search_doc(16063, [_search_result_row(1, "Toinen Tähti", reg_url=_reg_url("FI66666/24"))])

    with dog_db.session_scope() as session:
        dogs = dog_sqlstore.search_dogs_by_name(session, "tähti")
        assert [d["reg_id"] for d in dogs] == ["FI66666/24", "FI55555/23"]
        aggregated = dogs[1]
        assert aggregated["name"] == "Tähti Taivaalla"   # newest-show spelling
        assert aggregated["show_id"] == 16062
        assert aggregated["show_count"] == 2
        assert aggregated["result_count"] == 2
        # Escaped wildcard: no dog named with a literal '%'.
        assert dog_sqlstore.search_dogs_by_name(session, "täh%ti") == []


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


@pytest.mark.parametrize("hour,expect_live,expect_paused", [
    (12, True, False),   # judging
    (20, True, False),   # still inside the window
    (21, False, True),   # the fetch window just closed — held, not finished
    (23, False, True),
    # A single-day show's pre-dawn is the documented exception: the show has not
    # started, so there is nothing to continue from.
    (3, True, False),
])
def test_show_stats_night_hold_reads_as_paused_not_finished(client, monkeypatch, hour,
                                                            expect_live, expect_paused):
    """Observed on show 14014: the badge disappeared at 21:00 while the crawler
    was still hunting the finals, so a show that had merely stopped for the night
    read as concluded — and no badge is indistinguishable from settled history.
    An unsettled show always carries a badge: `Käynnissä` while judging, `Jatkuu`
    while held.

    Driven off the real clock rather than a mocked phase, because the 21:00 flip
    is the whole subject."""
    # Pin the whole clock, then seed the show from it. Deriving the show date
    # from `date.today()` while the stats path reads Finnish local time made this
    # depend on the runner's timezone: between 21:00 UTC and midnight the two are
    # a day apart, and the show read as past on a UTC runner.
    pinned = datetime.datetime(2026, 9, 6, hour, 0)
    monkeypatch.setattr(dog_utils, "_local_now", lambda: pinned)
    monkeypatch.setattr(dog_utils, "_local_dt", lambda now=None: pinned)
    dog_indexing._show_stats_cache.clear()

    seed_index_show("14021", {
        "title": "Amerikancockerspanieli",
        "name": "Amerikancockerspanieli",
        "date": "06.09.",
        "month": "syyskuu 2026",
        "breeds": [
            {"name": "amerikancockerspanieli", "count": 21, "group": "8", "breed_id": "117"},
        ],
    })

    stats = dog_indexing._show_stats_from_index(14021)

    assert stats["show_state"] == "live"
    assert stats["is_live"] is expect_live
    assert stats["is_paused"] is expect_paused
    # Whatever the hour, the show is never badge-less while it is unsettled.
    assert stats["is_live"] or stats["is_paused"]



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
        assert states["9200"] == {"breed_count": 2, "empty_breed_list_confirmed": False, "updated_at": 100.0}
        assert states["9201"] == {"breed_count": 0, "empty_breed_list_confirmed": True, "updated_at": 50.0}


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
    # 7 days back inclusive (the post-show correction window), then settled.
    assert recent({"date": "29.06.2026", "month": "kesäkuu 2026"}) is True
    assert recent({"date": "28.06.2026", "month": "kesäkuu 2026"}) is False
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
