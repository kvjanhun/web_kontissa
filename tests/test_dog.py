import pytest
import json
from unittest.mock import patch, MagicMock
import requests
from app.api.dog import _show_list_cache, _show_detail_cache, _breed_result_cache, _show_all_results_cache
from app.api import dog as dog_module

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

@pytest.fixture(autouse=True)
def clear_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(dog_module, "INDEX_DIR", str(tmp_path))
    monkeypatch.setattr(dog_module, "INDEX_PATH", str(tmp_path / "dog_show_index.json"))
    monkeypatch.setattr(dog_module, "RESULT_CACHE_DIR", str(tmp_path / "dog_result_cache"))
    monkeypatch.setattr(dog_module, "RESULT_JOBS_PATH", str(tmp_path / "dog_result_jobs.json"))
    monkeypatch.setattr(dog_module, "RESULT_IMMEDIATE_WARMUP", False)
    _show_list_cache["data"] = None
    _show_list_cache["ts"] = 0
    _show_detail_cache.clear()
    _breed_result_cache.clear()
    _show_all_results_cache.clear()
    dog_module._immediate_warmups.clear()
    dog_module._show_index["shows"].clear()
    dog_module._show_index["last_updated"] = 0
    dog_module._show_index_mtime = 0

@patch("app.api.dog.requests.get")
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

@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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

@patch("app.api.dog.requests.get")
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

@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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

    with open(dog_module.RESULT_JOBS_PATH, encoding="utf-8") as f:
        jobs = json.load(f)
    assert jobs["jobs"]["14042"]["state"] == "queued"
    assert jobs["jobs"]["14042"]["reason"] == "user"


@patch("app.api.dog.requests.get")
def test_show_all_results_starts_immediate_warmup_when_enabled(mock_get, monkeypatch, client):
    dog_module._show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "month": "kesäkuu 2026",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True },
        ],
    }
    started = []
    monkeypatch.setattr(dog_module, "RESULT_IMMEDIATE_WARMUP", True)
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


@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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
    monkeypatch.setattr(dog_module.time, "sleep", lambda seconds: sleeps.append(seconds))
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
    assert doc["results"][0]["name"] == "Ajibu You Are My Thrill"
    assert doc["results"][0]["breedName"] == "basenji"

    mock_get.reset_mock()
    resp = client.get("/api/dog/shows/14042/all-results")
    assert resp.status_code == 200
    assert resp.get_json()["results"][0]["grade"] == "KP"
    mock_get.assert_not_called()


@patch("app.api.dog.requests.get")
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
    monkeypatch.setattr(dog_module, "_result_cache_doc_is_fresh", lambda show_id, doc, now=None: False)
    monkeypatch.setattr(dog_module.time, "sleep", lambda seconds: None)
    mock_get.side_effect = requests.RequestException("rate limited")

    summary = dog_module.crawl_result_cache_for_show(14042, delay=0.1, source="test")

    assert summary["status"] == "partial"
    doc = dog_module._load_result_cache_doc(14042)
    assert doc["status"] == "complete"
    assert doc["results"][0]["name"] == "Old Cached Dog"

@patch("app.api.dog.requests.get")
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

@patch("app.api.dog.requests.get")
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


@patch("app.api.dog.requests.get")
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

@patch("app.api.dog.requests.get")
def test_search_shows_by_judge(mock_get, client):
    mock_resp_list = MagicMock()
    mock_resp_list.text = SAMPLE_SHOW_LIST_HTML
    mock_resp_list.status_code = 200

    from app.api.dog import _show_index
    _show_index["shows"]["14042"] = {
        "title": "14.06.2026 Basenji",
        "breeds": [
            { "name": "basenji", "count": 78, "group": "5", "breed_id": "3", "has_results": True, "judge": "Paula Steele" }
        ]
    }

    mock_get.return_value = mock_resp_list

    resp = client.get("/api/dog/search?q=steele")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["query"] == "steele"
    assert len(data["results"]) == 1
    assert data["results"][0]["show"]["name"] == "Basenji"
    assert data["results"][0]["breed"]["judge"] == "Paula Steele"
    assert data["results"][0]["match"] == "breed"
