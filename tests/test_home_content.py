"""Tests for the database-backed home content (fixed text blocks)."""


class TestPublicHomeContent:
    def test_empty_returns_projects_key(self, client, app):
        res = client.get("/api/home-content")
        assert res.status_code == 200
        data = res.get_json()
        assert data["home.projects"] == []

    def test_locale_param(self, client, app):
        assert client.get("/api/home-content?locale=fi").status_code == 200
        # Unknown locale falls back to en (still 200)
        assert client.get("/api/home-content?locale=zz").status_code == 200

    def test_reflects_saved_fields(self, client, logged_in_admin):
        logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "en", "value": "Hello world",
        })
        data = client.get("/api/home-content?locale=en").get_json()
        assert data["home.hero.body"] == "Hello world"
        # The fi map should not carry the en-only value
        assert "home.hero.body" not in client.get("/api/home-content?locale=fi").get_json()


class TestUpdateHomeContent:
    def test_requires_auth(self, client, app):
        res = client.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "en", "value": "x",
        })
        assert res.status_code == 401

    def test_forbidden_for_regular_user(self, client, regular_user):
        client.post("/api/login", json={"email": regular_user["email"], "password": regular_user["password"]})
        res = client.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "en", "value": "x",
        })
        assert res.status_code == 403

    def test_unknown_key_rejected(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.not.a.field", "locale": "en", "value": "x",
        })
        assert res.status_code == 400

    def test_bad_locale_rejected(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "de", "value": "x",
        })
        assert res.status_code == 400

    def test_missing_value_rejected(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "en",
        })
        assert res.status_code == 400

    def test_string_field_upsert(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.titleLine2", "locale": "en", "value": "From the silicon up.",
        })
        assert res.status_code == 200
        assert res.get_json()["value"] == "From the silicon up."
        # Update again -> still one row, new value
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.titleLine2", "locale": "en", "value": "Changed.",
        })
        assert res.get_json()["value"] == "Changed."

    def test_string_field_rejects_non_string(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "en", "value": ["not", "a", "string"],
        })
        assert res.status_code == 400

    def test_taglines_list(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.taglines", "locale": "en", "value": ["I make web.", "Code."],
        })
        assert res.status_code == 200
        assert res.get_json()["value"] == ["I make web.", "Code."]

    def test_taglines_rejects_non_list(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.taglines", "locale": "en", "value": "one string",
        })
        assert res.status_code == 400

    def test_layers_list(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.stack.layers", "locale": "en",
            "value": [{"z": "L7", "layer": "Interface", "title": "Frontend", "detail": "Nuxt"}],
        })
        assert res.status_code == 200
        assert res.get_json()["value"][0]["title"] == "Frontend"

    def test_links_list(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.footer.connectLinks", "locale": "en",
            "value": [{"label": "GitHub", "href": "https://github.com/x"}],
        })
        assert res.status_code == 200

    def test_links_require_label_and_href(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.footer.connectLinks", "locale": "en",
            "value": [{"label": "GitHub"}],
        })
        assert res.status_code == 400


class TestAdminHomeContentList:
    def test_returns_both_locales(self, logged_in_admin):
        logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "en", "value": "en body",
        })
        logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.hero.body", "locale": "fi", "value": "fi body",
        })
        data = logged_in_admin.get("/api/admin/home-content").get_json()
        assert data["en"]["home.hero.body"] == "en body"
        assert data["fi"]["home.hero.body"] == "fi body"

    def test_requires_admin(self, client, app):
        assert client.get("/api/admin/home-content").status_code == 401
