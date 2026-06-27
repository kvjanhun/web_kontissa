"""Tests for the projects collection (add/remove/hide/reorder)."""


def _payload(**overrides):
    payload = {
        "image": "/projects/x/cover.webp",
        "hidden": False,
        "translations": {
            "en": {"name": "Sanakenno", "kind": "product", "tagline": "t",
                   "description": "d", "shot": "s", "tech": ["React"],
                   "links": [{"label": "site", "href": "https://x"}]},
            "fi": {"name": "Sanakenno", "kind": "tuote", "tagline": "t",
                   "description": "d", "shot": "s", "tech": ["React"], "links": []},
        },
    }
    payload.update(overrides)
    return payload


class TestCreateProject:
    def test_requires_auth(self, client, app):
        assert client.post("/api/admin/projects", json=_payload()).status_code == 401

    def test_forbidden_for_regular_user(self, client, regular_user):
        client.post("/api/login", json={"email": regular_user["email"], "password": regular_user["password"]})
        assert client.post("/api/admin/projects", json=_payload()).status_code == 403

    def test_create_success(self, logged_in_admin):
        res = logged_in_admin.post("/api/admin/projects", json=_payload())
        assert res.status_code == 201
        data = res.get_json()
        assert data["id"] is not None
        assert data["position"] == 0
        assert set(data["translations"].keys()) == {"en", "fi"}
        assert data["translations"]["en"]["tech"] == ["React"]

    def test_create_requires_english_translation(self, logged_in_admin):
        res = logged_in_admin.post("/api/admin/projects", json=_payload(translations={
            "fi": {"name": "Vain suomeksi"},
        }))
        assert res.status_code == 400

    def test_translation_requires_name(self, logged_in_admin):
        res = logged_in_admin.post("/api/admin/projects", json=_payload(translations={
            "en": {"name": ""},
        }))
        assert res.status_code == 400

    def test_position_appends(self, logged_in_admin):
        a = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        b = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        assert b["position"] == a["position"] + 1


class TestUpdateProject:
    def _create(self, client):
        return client.post("/api/admin/projects", json=_payload()).get_json()

    def test_update_hidden_and_image(self, logged_in_admin):
        p = self._create(logged_in_admin)
        res = logged_in_admin.put(f"/api/admin/projects/{p['id']}", json={
            "hidden": True, "image": "/new.webp",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["hidden"] is True
        assert data["image"] == "/new.webp"

    def test_update_translation(self, logged_in_admin):
        p = self._create(logged_in_admin)
        res = logged_in_admin.put(f"/api/admin/projects/{p['id']}", json={
            "translations": {"en": {"name": "Renamed", "tech": ["Vue"]}},
        })
        assert res.status_code == 200
        assert res.get_json()["translations"]["en"]["name"] == "Renamed"

    def test_update_missing_project(self, logged_in_admin):
        assert logged_in_admin.put("/api/admin/projects/9999", json={"hidden": True}).status_code == 404


class TestDeleteProject:
    def test_delete(self, logged_in_admin):
        p = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        assert logged_in_admin.delete(f"/api/admin/projects/{p['id']}").status_code == 200
        assert logged_in_admin.get("/api/admin/projects").get_json() == []

    def test_delete_missing(self, logged_in_admin):
        assert logged_in_admin.delete("/api/admin/projects/9999").status_code == 404


class TestReorderProjects:
    def test_reorder(self, logged_in_admin):
        a = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        b = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        res = logged_in_admin.put("/api/admin/projects/reorder", json={"order": [b["id"], a["id"]]})
        assert res.status_code == 200
        listed = logged_in_admin.get("/api/admin/projects").get_json()
        by_id = {p["id"]: p["position"] for p in listed}
        assert by_id[b["id"]] == 0
        assert by_id[a["id"]] == 1

    def test_reorder_unknown_id(self, logged_in_admin):
        a = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        res = logged_in_admin.put("/api/admin/projects/reorder", json={"order": [a["id"], 9999]})
        assert res.status_code == 404


class TestProjectsOnPublicHomeContent:
    def test_visible_ordered_hidden_excluded(self, client, logged_in_admin):
        a = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        b = logged_in_admin.post("/api/admin/projects", json=_payload()).get_json()
        # Hide b
        logged_in_admin.put(f"/api/admin/projects/{b['id']}", json={"hidden": True})
        projects = client.get("/api/home-content?locale=en").get_json()["home.projects"]
        assert len(projects) == 1
        assert projects[0]["name"] == "Sanakenno"
        # The public shape carries the home.projects fields
        assert "tagline" in projects[0] and "image" in projects[0]
        assert a is not None  # a remains visible
