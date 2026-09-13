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

    def test_rejects_protocol_relative_href(self, logged_in_admin):
        """'//evil.com' resolves to an external host but reads as an internal path."""
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.footer.connectLinks", "locale": "en",
            "value": [{"label": "Totally internal", "href": "//evil.com/phish"}],
        })
        assert res.status_code == 400

    def test_still_accepts_site_relative_href(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/home-content", json={
            "key": "home.footer.siteLinks", "locale": "en",
            "value": [{"label": "/dog", "href": "/dog"}],
        })
        assert res.status_code == 200


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


class TestSectionVisibility:
    """Admin-toggled visibility of the home page's content bands."""

    def test_lists_every_section_with_no_rows(self, logged_in_admin):
        res = logged_in_admin.get("/api/admin/sections")
        assert res.status_code == 200
        data = res.get_json()
        # All bands are listed in page order even though nothing has been saved.
        assert [s["key"] for s in data] == ["work", "stack", "terminal"]
        assert all(s["hidden"] is False for s in data)
        assert data[0]["label"] == "Projects"

    def test_requires_auth(self, client, app):
        assert client.get("/api/admin/sections").status_code == 401
        assert client.put("/api/admin/sections", json={"key": "stack", "hidden": True}).status_code == 401

    def test_forbidden_for_regular_user(self, client, regular_user):
        client.post("/api/login", json={"email": regular_user["email"], "password": regular_user["password"]})
        assert client.get("/api/admin/sections").status_code == 403
        res = client.put("/api/admin/sections", json={"key": "stack", "hidden": True})
        assert res.status_code == 403

    def test_unknown_key_rejected(self, logged_in_admin):
        for key in ("hero", "footer", "", "not-a-section"):
            res = logged_in_admin.put("/api/admin/sections", json={"key": key, "hidden": True})
            assert res.status_code == 400, key

    def test_non_boolean_hidden_rejected(self, logged_in_admin):
        # "false" and 0 are the mistakes a caller actually makes here; coercing them
        # would store the opposite of the intent.
        for value in ("true", "false", 0, 1, None):
            res = logged_in_admin.put("/api/admin/sections", json={"key": "stack", "hidden": value})
            assert res.status_code == 400, repr(value)

    def test_toggle_upserts_and_flips_back(self, logged_in_admin):
        res = logged_in_admin.put("/api/admin/sections", json={"key": "stack", "hidden": True})
        assert res.status_code == 200
        assert res.get_json() == {"key": "stack", "hidden": True}

        listed = logged_in_admin.get("/api/admin/sections").get_json()
        assert [s["hidden"] for s in listed] == [False, True, False]

        # Second write updates the same row rather than adding another.
        res = logged_in_admin.put("/api/admin/sections", json={"key": "stack", "hidden": False})
        assert res.get_json()["hidden"] is False
        listed = logged_in_admin.get("/api/admin/sections").get_json()
        assert all(s["hidden"] is False for s in listed)

    def test_public_map_carries_hidden_sections(self, client, logged_in_admin):
        # Nothing hidden: the key is present and empty, not absent.
        assert client.get("/api/home-content").get_json()["home.hiddenSections"] == []

        logged_in_admin.put("/api/admin/sections", json={"key": "stack", "hidden": True})
        logged_in_admin.put("/api/admin/sections", json={"key": "terminal", "hidden": True})

        for locale in ("en", "fi"):
            data = client.get(f"/api/home-content?locale={locale}").get_json()
            # Page order, and the same value in both locales — visibility is
            # language-independent.
            assert data["home.hiddenSections"] == ["stack", "terminal"], locale
