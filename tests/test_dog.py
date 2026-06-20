import pytest
import json
from unittest.mock import patch, MagicMock
import requests
from app.api.dog import _show_list_cache, _show_detail_cache, _breed_result_cache, _show_all_results_cache
from app.api import dog as dog_module
from app.dog_show import crawler as dog_crawler
from app.dog_show import indexing as dog_indexing
from app.dog_show import result_cache as dog_result_cache
from app.dog_show import showlink as dog_showlink
from app.dog_show import store as dog_store
from app.dog_show.utils import _is_recent_show, _show_result_availability

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

@pytest.fixture(autouse=True)
def clear_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(dog_store, "INDEX_DIR", str(tmp_path))
    monkeypatch.setattr(dog_store, "INDEX_PATH", str(tmp_path / "dog_show_index.json"))
    monkeypatch.setattr(dog_store, "RESULT_CACHE_DIR", str(tmp_path / "dog_result_cache"))
    monkeypatch.setattr(dog_store, "RESULT_JOBS_PATH", str(tmp_path / "dog_result_jobs.json"))
    monkeypatch.setattr(dog_result_cache, "RESULT_IMMEDIATE_WARMUP", False)
    _show_list_cache["data"] = None
    _show_list_cache["ts"] = 0
    _show_detail_cache.clear()
    _breed_result_cache.clear()
    _show_all_results_cache.clear()
    dog_result_cache._immediate_warmups.clear()
    dog_module._show_index["shows"].clear()
    dog_module._show_index["last_updated"] = 0
    dog_store._show_index_mtime = 0

@patch("app.dog_show.showlink.requests.get")
def test_fetch_page_advertises_crawler_identity(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = "<html><body>ok</body></html>"
    mock_get.return_value = mock_resp

    dog_showlink._fetch_page("https://example.test/showlink")

    assert mock_get.call_args.kwargs["headers"]["User-Agent"] == (
        "erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)"
    )

@patch("app.dog_show.showlink.requests.get")
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


@patch("app.dog_show.showlink.requests.get")
def test_get_shows_enriches_cached_index_stats(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "updated_at": 1781431200,
        "breeds": [
            {"name": "basenji", "count": 78, "has_results": True},
            {"name": "ibizanpodenco", "count": 12, "has_results": False},
        ],
    }
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
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "basenji", "count": 2, "has_results": True},
            {"name": "ibizanpodenco", "count": 1, "has_results": True},
        ],
    }
    dog_module._save_result_cache_doc(14042, {
        "status": "running",
        "results": [{}, {}, {}, {}],
    })

    live_stats = dog_module._show_stats_from_index(
        14042,
        show={"id": 14042, "date": "14.06.", "month": "kesäkuu 2026"},
        today=dog_module.datetime.date(2026, 6, 14),
    )
    past_stats = dog_module._show_stats_from_index(
        14042,
        show={"id": 14042, "date": "14.06.", "month": "kesäkuu 2026"},
        today=dog_module.datetime.date(2026, 6, 15),
    )

    assert live_stats["show_state"] == "live"
    assert live_stats["is_live"] is True
    assert live_stats["entry_count"] == 3
    assert live_stats["result_count"] == 3
    assert past_stats["show_state"] == "past"
    assert past_stats["is_live"] is False
    assert "result_count" not in past_stats

    dog_module._show_index["shows"]["14043"] = {
        "title": "14.06.2026 Villakoira",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            {"name": "villakoira", "count": 4, "has_results": True},
        ],
    }
    uncached_live_stats = dog_module._show_stats_from_index(
        14043,
        show={"id": 14043, "date": "14.06.", "month": "kesäkuu 2026"},
        today=dog_module.datetime.date(2026, 6, 14),
    )
    assert uncached_live_stats["is_live"] is True
    assert "result_count" not in uncached_live_stats


def test_show_stats_ignore_empty_single_breed_specialty_cache(client):
    dog_module._show_index["shows"]["14079"] = {
        "title": "20.06.2026 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(14079),
        "breeds": [
            {
                "name": "bostoninterrieri",
                "count": 26,
                "group": "9",
                "breed_id": "296",
                "has_results": False,
            },
        ],
    }
    dog_module._save_result_cache_doc(14079, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 14079,
        "status": "complete",
        "title": "20.06.2026 Bostoninterrieri",
        "source_url": dog_module._source_url(14079),
        "started_at": 1000,
        "updated_at": 1001,
        "cached_at": 1001,
        "total_breeds": 0,
        "completed_breeds": {},
        "failed_breeds": {},
        "results": [],
    })

    stats = dog_module._show_stats_from_index(
        14079,
        show={"id": 14079, "date": "20.06.", "month": "kesäkuu 2026"},
        today=dog_module.datetime.date(2026, 6, 20),
    )

    assert stats["is_live"] is True
    assert stats["entry_count"] == 26
    assert stats["result_breed_count"] == 1
    assert "result_count" not in stats


def test_get_shows_queues_stale_live_result_refresh(monkeypatch, client):
    now = dog_module.datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    show = {
        "id": 13771,
        "date": "20.-21.06.",
        "name": "Jyväskylä KV",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(13771),
    }
    dog_module._show_index["shows"]["13771"] = {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(13771),
        "updated_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "breeds": [
            { "name": "basenji", "count": 2066, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    dog_module._save_result_cache_doc(13771, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_module._source_url(13771),
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
    jobs = dog_module._load_result_jobs()["jobs"]
    assert jobs["13771"]["state"] == "queued"
    assert jobs["13771"]["reason"] == "live-list-refresh"


def test_show_result_availability_waits_until_show_morning():
    show = {"date": "20.06.", "month": "kesäkuu 2026"}

    future = _show_result_availability(
        show,
        now=dog_module.datetime.datetime(2026, 6, 17, 12, 0),
    )
    early_morning = _show_result_availability(
        show,
        now=dog_module.datetime.datetime(2026, 6, 20, 5, 59),
    )
    show_day = _show_result_availability(
        show,
        now=dog_module.datetime.datetime(2026, 6, 20, 6, 0),
    )

    assert future["can_fetch"] is False
    assert future["reason"] == "future_show"
    assert future["available_from_iso"] == "2026-06-20T06:00:00"
    assert early_morning["can_fetch"] is False
    assert early_morning["reason"] == "show_morning"
    assert show_day["can_fetch"] is True
    assert show_day["reason"] == "show_day"

def test_show_result_availability_handles_showlink_today_section():
    show = {"date": "20.-21.06.", "month": "Tänään"}

    availability = _show_result_availability(
        show,
        now=dog_module.datetime.datetime(2026, 6, 20, 12, 0),
    )

    assert _is_recent_show("Tänään") is True
    assert availability["can_fetch"] is True
    assert availability["show_state"] == "live"
    assert availability["start_date"] == "2026-06-20"
    assert availability["end_date"] == "2026-06-21"


@patch("app.dog_show.showlink.requests.get")
def test_get_shows_does_not_show_stats_for_empty_index_entries(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "updated_at": 1781431200,
        "breeds": [],
    }
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_LIST_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "stats" not in data["shows"][0]


@patch("app.dog_show.showlink.requests.get")
def test_get_show_detail(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

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


@patch("app.dog_show.showlink.requests.get")
def test_recent_show_detail_cache_expires(mock_get, client):
    _show_detail_cache[14042] = {
        "data": {"id": 14042, "title": "stale", "breeds": []},
        "ts": 0,
    }
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    assert resp.get_json()["title"] == "14.06.2026 Basenji"
    mock_get.assert_called_once()


@patch("app.dog_show.showlink.requests.get")
def test_old_show_detail_cache_is_reused(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {"month": "tammikuu 2000", "breeds": []}
    _show_detail_cache[14042] = {
        "data": {"id": 14042, "title": "cached old show", "breeds": []},
        "ts": 0,
    }

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    assert resp.get_json()["title"] == "cached old show"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_show_detail_uses_persisted_index_without_fetching(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(14042),
        "updated_at": 1781431200,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" },
        ],
    }

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "14.06.2026 Basenji"
    assert data["breeds"][0]["name"] == "basenji"
    assert data["breeds"][0]["judge"] == "Paula Steele"
    assert data["cache"]["status"] == "indexed"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_show_detail_refreshes_stale_recent_index_without_result_flags(mock_get, monkeypatch, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(14042),
        "updated_at": 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": False },
        ],
    }
    monkeypatch.setattr(dog_indexing, "_is_show_recent_by_id", lambda show_id: True)
    monkeypatch.setattr(
        dog_indexing,
        "_show_result_availability_for_id",
        lambda show_id, now=None: {"can_fetch": True, "show_state": "live"},
    )
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breeds"][0]["has_results"] is True
    assert dog_module._show_index["shows"]["14042"]["breeds"][0]["has_results"] is True
    mock_get.assert_called_once()


@patch("app.dog_show.showlink.requests.get")
def test_show_detail_marks_single_breed_specialty_as_result_fetchable(mock_get, client):
    dog_module._show_index["shows"]["14079"] = {
        "title": "20.06.2000 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2000",
        "source_url": dog_module._source_url(14079),
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
    }

    resp = client.get("/api/dog/shows/14079")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breeds"][0]["has_results"] is True
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_show_detail_merges_cached_result_judges_without_fetching(mock_get, client):
    dog_module._show_index["shows"]["13992"] = {
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "name": "Pertunmaa Pentunäyttely",
        "month": "heinäkuu 2025",
        "source_url": dog_module._source_url(13992),
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
    }
    dog_module._save_result_cache_doc(13992, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_module._source_url(13992),
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

    resp = client.get("/api/dog/shows/13992")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breeds"][0]["judge"] == "Tarja Kolkka"
    assert dog_module._show_index["shows"]["13992"]["breeds"][0]["judge"] == "Tarja Kolkka"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_cached_show_detail_merges_cached_result_judges(mock_get, client):
    _show_detail_cache[13992] = {
        "data": {
            "id": 13992,
            "title": "27.07.2025 Pertunmaa Pentunäyttely",
            "breeds": [
                {
                    "name": "sileäkarvainen noutaja",
                    "count": 1,
                    "group": "8",
                    "breed_id": "124",
                    "has_results": True,
                },
            ],
            "source_url": dog_module._source_url(13992),
        },
        "ts": dog_module.time.time(),
    }
    dog_module._show_index["shows"]["13992"] = {
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
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
    }
    dog_module._save_result_cache_doc(13992, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_module._source_url(13992),
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

    resp = client.get("/api/dog/shows/13992")

    assert resp.status_code == 200
    assert resp.get_json()["breeds"][0]["judge"] == "Tarja Kolkka"
    assert _show_detail_cache[13992]["data"]["breeds"][0]["judge"] == "Tarja Kolkka"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_cached_show_detail_merges_index_judges(mock_get, client):
    _show_detail_cache[14042] = {
        "data": {
            "id": 14042,
            "title": "Basenji Show 2026",
            "breeds": [
                {
                    "name": "basenji",
                    "count": 3,
                    "group": "5",
                    "breed_id": "3",
                    "has_results": True,
                },
            ],
            "source_url": dog_module._source_url(14042),
        },
        "ts": dog_module.time.time(),
    }
    dog_module._show_index["shows"]["14042"] = {
        "title": "Basenji Show 2026",
        "source_url": dog_module._source_url(14042),
        "breeds": [
            {
                "name": "basenji",
                "count": 3,
                "group": "5",
                "breed_id": "3",
                "has_results": True,
                "judge": "Paula Steele",
            },
        ],
    }

    resp = client.get("/api/dog/shows/14042")

    assert resp.status_code == 200
    assert resp.get_json()["breeds"][0]["judge"] == "Paula Steele"
    assert _show_detail_cache[14042]["data"]["breeds"][0]["judge"] == "Paula Steele"
    mock_get.assert_not_called()


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


@patch("app.dog_show.showlink.requests.get")
def test_get_show_detail_general(mock_get, client):
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


@patch("app.dog_show.showlink.requests.get")
def test_get_show_detail_uses_aggregate_breed_results_link(mock_get, client):
    dog_module._show_index["shows"]["13934"] = {
        "title": "stale empty index",
        "name": "Kanakoirakerho",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "breeds": [],
    }
    mock_resp_main = MagicMock()
    mock_resp_main.text = SAMPLE_AGGREGATE_SHOW_MAIN_HTML
    mock_resp_main.status_code = 200

    mock_resp_breeds = MagicMock()
    mock_resp_breeds.text = SAMPLE_AGGREGATE_SHOW_BREEDS_HTML
    mock_resp_breeds.status_code = 200

    mock_get.side_effect = [mock_resp_main, mock_resp_breeds]

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
    assert mock_get.call_args_list[1].args[0].endswith("Id=13934&R=R")
    assert len(dog_module._show_index["shows"]["13934"]["breeds"]) == 2
    assert "empty_breed_list_confirmed" not in dog_module._show_index["shows"]["13934"]


@patch("app.dog_show.showlink.requests.get")
def test_crawl_index_refreshes_unconfirmed_empty_index_entries(mock_get, monkeypatch):
    dog_module._show_index["shows"]["14042"] = {
        "title": "stale empty index",
        "name": "Basenji",
        "date": "14.06.",
        "month": "tammikuu 2000",
        "breeds": [],
    }
    dog_module._show_index["shows"]["14043"] = {
        "title": "already indexed",
        "name": "Villakoira erikoisnäyttely",
        "date": "15.06.",
        "month": "tammikuu 2000",
        "breeds": [
            {"name": "villakoira", "count": 1, "group": "9", "breed_id": "172", "has_results": True},
        ],
    }
    monkeypatch.setattr(dog_crawler.time, "sleep", lambda seconds: None)

    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    mock_resp_detail = MagicMock()
    mock_resp_detail.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp_detail.status_code = 200

    mock_get.side_effect = [mock_resp_list, mock_resp_detail]

    summary = dog_module.crawl_index_once(limit=1, delay=0)

    assert summary["updated"] == 1
    assert len(dog_module._show_index["shows"]["14042"]["breeds"]) == 2
    assert dog_module._show_index["shows"]["14042"]["breeds"][0]["name"] == "basenji"
    assert mock_get.call_args_list[1].args[0].endswith("Id=14042")


@patch("app.dog_show.showlink.requests.get")
def test_crawl_empty_index_once_repairs_only_empty_entries(mock_get, monkeypatch):
    dog_module._show_index["shows"]["14042"] = {
        "title": "stale empty index",
        "name": "Basenji",
        "date": "14.06.",
        "month": "tammikuu 2000",
        "breeds": [],
    }
    dog_module._show_index["shows"]["14043"] = {
        "title": "already indexed",
        "name": "Villakoira erikoisnäyttely",
        "date": "15.06.",
        "month": "tammikuu 2000",
        "breeds": [
            {"name": "villakoira", "count": 1, "group": "9", "breed_id": "172", "has_results": True},
        ],
    }
    monkeypatch.setattr(dog_crawler.time, "sleep", lambda seconds: None)

    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    mock_resp_detail = MagicMock()
    mock_resp_detail.text = SAMPLE_SHOW_DETAIL_HTML
    mock_resp_detail.status_code = 200

    mock_get.side_effect = [mock_resp_list, mock_resp_detail]

    summary = dog_module.crawl_empty_index_once(limit=10, delay=0)

    assert summary["updated"] == 1
    assert summary["empty_candidates"] == 1
    assert len(dog_module._show_index["shows"]["14042"]["breeds"]) == 2
    assert len(dog_module._show_index["shows"]["14043"]["breeds"]) == 1
    assert len(mock_get.call_args_list) == 2
    assert mock_get.call_args_list[1].args[0].endswith("Id=14042")


@patch("app.dog_show.showlink.requests.get")
def test_get_breed_results(mock_get, client):
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

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


@patch("app.dog_show.showlink.requests.get")
def test_get_breed_results_strips_glued_judge_label(mock_get, client):
    dog_module._show_index["shows"]["13763"] = {
        "title": "18.-19.04.2026 Vaasa KV",
        "name": "Vaasa KV",
        "month": "huhtikuu 2026",
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
    }
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_GLUE_JUDGE_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    resp = client.get("/api/dog/shows/13763/results?group=8&breed=124")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["breed"] == "sileäkarvainen noutaja"
    assert data["judge"] == "Tarja Kolkka"
    assert dog_module._show_index["shows"]["13763"]["breeds"][0]["judge"] == "Tarja Kolkka"


@patch("app.dog_show.showlink.requests.get")
def test_future_breed_results_return_not_ready_without_fetching(mock_get, client):
    dog_module._show_index["shows"]["15001"] = {
        "title": "20.06.2999 Future Show",
        "date": "20.06.",
        "month": "kesäkuu 2999",
        "breeds": [
            { "name": "basenji", "count": 4, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }

    resp = client.get("/api/dog/shows/15001/results?group=5&breed=3")

    assert resp.status_code == 425
    data = resp.get_json()
    assert data["status"] == "not_ready"
    assert data["reason"] == "future_show"
    assert data["availability"]["can_fetch"] is False
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_future_show_all_results_return_not_ready_without_queueing(mock_get, client):
    dog_module._show_index["shows"]["15001"] = {
        "title": "20.06.2999 Future Show",
        "date": "20.06.",
        "month": "kesäkuu 2999",
        "breeds": [
            { "name": "basenji", "count": 4, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }

    resp = client.get("/api/dog/shows/15001/all-results")

    assert resp.status_code == 425
    data = resp.get_json()
    assert data["status"] == "not_ready"
    assert data["reason"] == "future_show"
    assert data["availability"]["can_fetch"] is False
    assert dog_module._load_result_jobs()["jobs"] == {}
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_show_all_results_missing_cache_queues_without_fetching(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": False },
        ],
    }

    resp = client.get("/api/dog/shows/14042/all-results")

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "warming"
    assert data["retry_after"] == dog_module.RESULT_RETRY_AFTER_SECONDS
    assert data["progress"]["state"] == "queued"
    assert data["progress"]["total_breeds"] == 1
    assert data["started"] is False
    mock_get.assert_not_called()

    with open(dog_store.RESULT_JOBS_PATH, encoding="utf-8") as f:
        jobs = json.load(f)
    assert jobs["jobs"]["14042"]["state"] == "queued"
    assert jobs["jobs"]["14042"]["reason"] == "user"


@patch("app.dog_show.showlink.requests.get")
def test_show_all_results_starts_immediate_warmup_when_enabled(mock_get, monkeypatch, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    started = []
    monkeypatch.setattr(
        dog_module,
        "_start_result_cache_warmup",
        lambda show_id, reason="user-immediate": started.append((show_id, reason)) or True,
    )

    resp = client.get("/api/dog/shows/14042/all-results")

    assert resp.status_code == 202
    assert resp.get_json()["started"] is True
    assert started == [(14042, "user-immediate")]
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_show_all_results_poll_does_not_refresh_running_job_clock(mock_get, monkeypatch, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    old_updated_at = 100
    dog_module._save_result_jobs({
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
    with open(dog_store.RESULT_JOBS_PATH, encoding="utf-8") as f:
        jobs = json.load(f)["jobs"]
    assert jobs["14042"]["state"] == "running"
    assert jobs["14042"]["requested_at"] == 1000
    assert jobs["14042"]["updated_at"] == old_updated_at
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_show_all_results_serves_persisted_cache_without_fetching(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2000 Basenji",
        "month": "tammikuu 2000",
        "breeds": [
            { "name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    dog_module._save_result_cache_doc(14042, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "14.06.2000 Basenji",
        "source_url": dog_module._source_url(14042),
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
    now = dog_module.datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    dog_module._show_index["shows"]["13771"] = {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
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


def test_stale_memory_cache_does_not_hide_refreshed_live_disk_cache(monkeypatch, client):
    now = dog_module.datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    dog_module._show_index["shows"]["13771"] = {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    monkeypatch.setattr(dog_result_cache.time, "time", lambda: now)
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)
    old_cached_at = now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1
    _show_all_results_cache[13771] = {
        "ts": old_cached_at,
        "data": {
            "show_id": 13771,
            "title": "old memory cache",
            "source_url": dog_module._source_url(13771),
            "results": [{"name": "Old Memory Dog", "breedName": "basenji"}],
            "cache": {
                "status": "complete",
                "stale": False,
                "total_breeds": 1,
                "cached_at": old_cached_at,
            },
        },
    }
    dog_module._save_result_cache_doc(13771, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "fresh disk cache",
        "source_url": dog_module._source_url(13771),
        "started_at": now - 20,
        "updated_at": now - 10,
        "cached_at": now - 10,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 2}},
        "failed_breeds": {},
        "results": [
            {"name": "Fresh Disk Dog 1", "breedName": "basenji"},
            {"name": "Fresh Disk Dog 2", "breedName": "basenji"},
        ],
    })

    data = dog_result_cache._cached_all_results_response(13771, allow_stale=True)

    assert [dog["name"] for dog in data["results"]] == ["Fresh Disk Dog 1", "Fresh Disk Dog 2"]
    assert data["cache"]["stale"] is False


def test_auto_result_cache_candidates_include_live_multi_day_show(monkeypatch, client):
    now = dog_module.datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    show = {
        "id": 13771,
        "date": "20.-21.06.",
        "name": "Jyväskylä KV",
        "month": "kesäkuu 2026",
    }
    monkeypatch.setattr(dog_result_cache, "_get_show_list", lambda: [show])
    monkeypatch.setattr(dog_result_cache, "_is_show_recent_by_id", lambda show_id: True)
    dog_module._show_index["shows"]["13771"] = {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 3, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    dog_module._save_result_cache_doc(13771, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13771,
        "status": "complete",
        "title": "20.-21.06.2026 Jyväskylä KV",
        "source_url": dog_module._source_url(13771),
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


@patch("app.dog_show.showlink.requests.get")
def test_show_all_results_rebuilds_empty_cache_when_recent_index_has_stale_result_flags(mock_get, monkeypatch, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(14042),
        "updated_at": 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": False },
        ],
    }
    dog_module._save_result_cache_doc(14042, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "14.06.2026 Basenji",
        "source_url": dog_module._source_url(14042),
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


@patch("app.dog_show.showlink.requests.get")
def test_show_all_results_rebuilds_empty_single_breed_specialty_cache(mock_get, client):
    dog_module._show_index["shows"]["14079"] = {
        "title": "20.06.2000 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2000",
        "source_url": dog_module._source_url(14079),
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
    }
    dog_module._save_result_cache_doc(14079, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 14079,
        "status": "complete",
        "title": "20.06.2000 Bostoninterrieri",
        "source_url": dog_module._source_url(14079),
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


@patch("app.dog_show.showlink.requests.get")
def test_breed_results_reuses_persisted_whole_show_cache(mock_get, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2000 Basenji",
        "month": "tammikuu 2000",
        "breeds": [
            { "name": "basenji", "count": 1, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" },
        ],
    }
    dog_module._save_result_cache_doc(14042, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "14.06.2000 Basenji",
        "source_url": dog_module._source_url(14042),
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


@patch("app.dog_show.showlink.requests.get")
def test_cached_breed_results_backfill_index_judge(mock_get, client):
    dog_module._show_index["shows"]["13992"] = {
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
    }
    dog_module._save_result_cache_doc(13992, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_module._source_url(13992),
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
    assert dog_module._show_index["shows"]["13992"]["breeds"][0]["judge"] == "Tarja Kolkka"
    mock_get.assert_not_called()


@patch("app.dog_show.showlink.requests.get")
def test_crawl_result_cache_for_show_persists_results_with_delay(mock_get, monkeypatch, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2000 Basenji",
        "month": "tammikuu 2000",
        "source_url": dog_module._source_url(14042),
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": False },
        ],
    }
    sleeps = []
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: sleeps.append(seconds))
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    summary = dog_module.crawl_result_cache_for_show(14042, delay=0.25, source="test")

    assert summary["status"] == "complete"
    assert sleeps == [0.25]
    mock_get.assert_called_once()
    doc = dog_module._load_result_cache_doc(14042)
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


@patch("app.dog_show.showlink.requests.get")
def test_crawl_result_cache_refreshes_stale_recent_index_before_fetching_results(mock_get, monkeypatch):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "name": "Basenji",
        "date": "14.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(14042),
        "updated_at": 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": False },
        ],
    }
    monkeypatch.setattr(dog_result_cache, "_indexed_result_flags_need_refresh", lambda show_id, indexed_show=None, now=None: True)
    monkeypatch.setattr(
        dog_result_cache,
        "_show_result_availability_for_id",
        lambda show_id, now=None: {"can_fetch": True, "show_state": "live"},
    )
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)

    detail_resp = MagicMock()
    detail_resp.text = SAMPLE_SHOW_DETAIL_HTML
    detail_resp.status_code = 200
    result_resp = MagicMock()
    result_resp.text = SAMPLE_BREED_RESULTS_HTML
    result_resp.status_code = 200
    mock_get.side_effect = [detail_resp, result_resp]

    summary = dog_module.crawl_result_cache_for_show(14042, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 2
    assert dog_module._show_index["shows"]["14042"]["breeds"][0]["has_results"] is True
    doc = dog_module._load_result_cache_doc(14042)
    assert doc["total_breeds"] == 1
    assert doc["completed_breeds"]["5:3"]["result_count"] == 1
    assert doc["results"][0]["name"] == "Ajibu You Are My Thrill"


@patch("app.dog_show.showlink.requests.get")
def test_crawl_result_cache_refreshes_live_index_with_partial_result_flags(mock_get, monkeypatch):
    now = dog_module.datetime.datetime(2026, 6, 20, 12, 0).timestamp()
    dog_module._show_index["shows"]["13771"] = {
        "title": "20.-21.06.2026 Jyväskylä KV",
        "name": "Jyväskylä KV",
        "date": "20.-21.06.",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(13771),
        "updated_at": now - dog_result_cache.RESULT_CACHE_LIVE_TTL - 1,
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": False },
        ],
    }
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

    summary = dog_module.crawl_result_cache_for_show(13771, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 3
    indexed_breeds = dog_module._show_index["shows"]["13771"]["breeds"]
    assert [breed["has_results"] for breed in indexed_breeds] == [True, True]
    doc = dog_module._load_result_cache_doc(13771)
    assert doc["total_breeds"] == 2
    assert set(doc["completed_breeds"]) == {"5:3", "5:4"}


@patch("app.dog_show.showlink.requests.get")
def test_crawl_result_cache_fetches_single_breed_specialty_without_result_flag(mock_get, monkeypatch):
    dog_module._show_index["shows"]["14079"] = {
        "title": "20.06.2000 Bostoninterrieri",
        "name": "Bostoninterrieri",
        "date": "20.06.",
        "month": "kesäkuu 2000",
        "source_url": dog_module._source_url(14079),
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
    }
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)
    mock_resp = MagicMock()
    mock_resp.text = SAMPLE_BREED_RESULTS_HTML
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    summary = dog_module.crawl_result_cache_for_show(14079, delay=0.1, source="test", workers=1)

    assert summary["status"] == "complete"
    assert mock_get.call_count == 1
    assert "Id=14079" in mock_get.call_args.args[0]
    assert "R=9" in mock_get.call_args.args[0]
    assert "RO=296" in mock_get.call_args.args[0]
    doc = dog_module._load_result_cache_doc(14079)
    assert doc["total_breeds"] == 1
    assert doc["completed_breeds"]["9:296"]["result_count"] == 1
    assert doc["results"][0]["breedName"] == "bostoninterrieri"
    assert doc["results"][0]["name"] == "Ajibu You Are My Thrill"


@patch("app.dog_show.showlink.requests.get")
def test_stale_result_cache_is_preserved_when_refresh_fails(mock_get, monkeypatch):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "source_url": dog_module._source_url(14042),
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    dog_module._save_result_cache_doc(14042, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 14042,
        "status": "complete",
        "title": "old cache",
        "source_url": dog_module._source_url(14042),
        "started_at": 1,
        "updated_at": 2,
        "cached_at": 2,
        "total_breeds": 1,
        "completed_breeds": {"5:3": {"name": "basenji", "result_count": 1}},
        "failed_breeds": {},
        "results": [{"name": "Old Cached Dog", "breedName": "basenji"}],
    })
    monkeypatch.setattr(dog_result_cache, "_result_cache_doc_is_fresh", lambda show_id, doc, now=None: False)
    monkeypatch.setattr(dog_result_cache.time, "sleep", lambda seconds: None)
    mock_get.side_effect = requests.RequestException("rate limited")

    summary = dog_module.crawl_result_cache_for_show(14042, delay=0.1, source="test")

    assert summary["status"] == "partial"
    doc = dog_module._load_result_cache_doc(14042)
    assert doc["status"] == "complete"
    assert doc["results"][0]["name"] == "Old Cached Dog"

@patch("app.dog_show.showlink.requests.get")
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

@patch("app.dog_show.showlink.requests.get")
def test_search_shows_by_breed(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    from app.api.dog import _show_index
    _show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True }
        ]
    }

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


@patch("app.dog_show.showlink.requests.get")
def test_search_indexed_show_name_without_breed_match(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": True }
        ]
    }
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

@patch("app.dog_show.showlink.requests.get")
def test_search_shows_by_judge(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    from app.api.dog import _show_index
    _show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" },
            { "name": "ibizanpodenco", "count": 12, "group": "5", "breed_id": "4", "has_results": True, "judge": "Paula Steele" },
        ]
    }

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


@patch("app.dog_show.showlink.requests.get")
def test_search_finds_indexed_only_show_by_cleaned_judge(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200
    dog_module._show_index["shows"]["13763"] = {
        "title": "18.-19.04.2026 Vaasa KV",
        "name": "Vaasa KV",
        "date": "18.-19.04.",
        "month": "huhtikuu 2026",
        "source_url": dog_module._source_url(13763),
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
    }
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


@patch("app.dog_show.showlink.requests.get")
def test_search_finds_judge_from_whole_show_result_cache(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200
    dog_module._show_index["shows"]["13992"] = {
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "name": "Pertunmaa Pentunäyttely",
        "date": "27.07.",
        "month": "heinäkuu 2025",
        "source_url": dog_module._source_url(13992),
        "breeds": [
            {
                "name": "sileäkarvainen noutaja",
                "count": 1,
                "group": "8",
                "breed_id": "124",
                "has_results": True,
            }
        ],
    }
    dog_module._save_result_cache_doc(13992, {
        "version": dog_module.RESULT_CACHE_VERSION,
        "show_id": 13992,
        "status": "complete",
        "title": "27.07.2025 Pertunmaa Pentunäyttely",
        "source_url": dog_module._source_url(13992),
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

    resp = client.get("/api/dog/search?q=kolkka")

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["id"] == 13992
    assert data["results"][0]["breed"] is None
    assert data["results"][0]["judge"] == "Tarja Kolkka"
    assert data["results"][0]["judge_match_count"] == 1
    assert data["results"][0]["match"] == "judge"
    assert dog_module._show_index["shows"]["13992"]["breeds"][0]["judge"] == "Tarja Kolkka"
