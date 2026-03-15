class TestGetSections:
    def test_list_sections_empty(self, client, app):
        res = client.get("/api/sections")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_list_sections_with_data(self, client, sample_section):
        res = client.get("/api/sections")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["slug"] == "test"

    def test_list_sections_filters_by_locale(self, app, client):
        from app.models import db, Section
        with app.app_context():
            db.session.add(Section(title="EN", slug="intro", content="Hello", locale="en"))
            db.session.add(Section(title="FI", slug="intro", content="Hei", locale="fi"))
            db.session.commit()
        res = client.get("/api/sections?locale=fi")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "FI"
        assert data[0]["locale"] == "fi"

    def test_list_sections_defaults_to_en(self, app, client):
        from app.models import db, Section
        with app.app_context():
            db.session.add(Section(title="EN", slug="intro", content="Hello", locale="en"))
            db.session.add(Section(title="FI", slug="intro", content="Hei", locale="fi"))
            db.session.commit()
        res = client.get("/api/sections")
        data = res.get_json()
        assert len(data) == 1
        assert data[0]["locale"] == "en"


class TestCreateSection:
    def test_create_as_admin(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "New", "slug": "new", "content": "<p>New</p>",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["slug"] == "new"
        assert data["id"] is not None

    def test_create_unauthenticated(self, client, app):
        res = client.post("/api/sections", json={
            "title": "X", "slug": "x", "content": "x",
        })
        assert res.status_code == 401

    def test_create_as_regular_user(self, client, regular_user):
        client.post("/api/login", json={
            "email": regular_user["email"],
            "password": regular_user["password"],
        })
        res = client.post("/api/sections", json={
            "title": "X", "slug": "x", "content": "x",
        })
        assert res.status_code == 403

    def test_create_missing_fields(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={"title": "Only title"})
        assert res.status_code == 400

    def test_create_missing_body(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", content_type="application/json")
        assert res.status_code == 400

    def test_create_duplicate_slug(self, logged_in_admin, sample_section):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Another", "slug": "test", "content": "dup",
        })
        assert res.status_code == 409

    def test_create_same_slug_different_locale(self, logged_in_admin, sample_section):
        res = logged_in_admin.post("/api/sections", json={
            "title": "FI version", "slug": "test", "content": "Hei", "locale": "fi",
        })
        assert res.status_code == 201
        assert res.get_json()["locale"] == "fi"

    def test_create_with_locale(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "FI", "slug": "fi-only", "content": "Moi", "locale": "fi",
        })
        assert res.status_code == 201
        assert res.get_json()["locale"] == "fi"

    def test_create_invalid_locale(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "X", "slug": "x", "content": "x", "locale": "de",
        })
        assert res.status_code == 400


class TestUpdateSection:
    def test_update_as_admin(self, logged_in_admin, sample_section):
        res = logged_in_admin.put(f"/api/sections/{sample_section['id']}", json={
            "title": "Updated",
        })
        assert res.status_code == 200
        assert res.get_json()["title"] == "Updated"

    def test_update_unauthenticated(self, client, sample_section):
        res = client.put(f"/api/sections/{sample_section['id']}", json={
            "title": "Hacked",
        })
        assert res.status_code == 401

    def test_update_nonexistent(self, logged_in_admin):
        res = logged_in_admin.put("/api/sections/9999", json={"title": "X"})
        assert res.status_code == 404

    def test_update_missing_body(self, logged_in_admin, sample_section):
        res = logged_in_admin.put(
            f"/api/sections/{sample_section['id']}",
            content_type="application/json",
        )
        assert res.status_code == 400


class TestReorderSections:
    """PUT /api/sections/reorder"""

    def test_requires_auth(self, client):
        res = client.put("/api/sections/reorder", json={"order": []})
        assert res.status_code == 401

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.put("/api/sections/reorder", json={"order": []})
        assert res.status_code == 403

    def test_reorders_sections(self, app, logged_in_admin):
        from app.models import db, Section
        with app.app_context():
            s1 = Section(title="A", slug="a", content="a")
            s2 = Section(title="B", slug="b", content="b")
            db.session.add_all([s1, s2])
            db.session.commit()
            id1, id2 = s1.id, s2.id

        # Reverse order
        res = logged_in_admin.put("/api/sections/reorder", json={"order": [id2, id1]})
        assert res.status_code == 200

        # Verify order in GET
        res = logged_in_admin.get("/api/sections")
        data = res.get_json()
        assert data[0]["id"] == id2
        assert data[0]["position"] == 0
        assert data[1]["id"] == id1
        assert data[1]["position"] == 1

    def test_validates_ids(self, logged_in_admin):
        res = logged_in_admin.put("/api/sections/reorder", json={"order": [9999]})
        assert res.status_code == 404

    def test_rejects_missing_order(self, logged_in_admin):
        res = logged_in_admin.put("/api/sections/reorder", json={})
        assert res.status_code == 400

    def test_rejects_non_int_order(self, logged_in_admin):
        res = logged_in_admin.put("/api/sections/reorder", json={"order": ["a"]})
        assert res.status_code == 400

    def test_position_in_get_response(self, app, logged_in_admin):
        from app.models import db, Section
        with app.app_context():
            s = Section(title="X", slug="x", content="x")
            db.session.add(s)
            db.session.commit()

        res = logged_in_admin.get("/api/sections")
        data = res.get_json()
        assert "position" in data[0]


class TestSectionType:
    def test_default_section_type_is_text(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Plain", "slug": "plain", "content": "<p>Text</p>",
        })
        assert res.status_code == 201
        assert res.get_json()["section_type"] == "text"

    def test_create_pills_section(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Tech", "slug": "tech", "content": "Python, Flask, Vue.js",
            "section_type": "pills",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["section_type"] == "pills"
        assert data["content"] == "Python, Flask, Vue.js"

    def test_create_invalid_section_type(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Bad", "slug": "bad", "content": "x",
            "section_type": "invalid",
        })
        assert res.status_code == 400
        assert "section_type" in res.get_json()["error"].lower()

    def test_update_section_type(self, logged_in_admin, sample_section):
        res = logged_in_admin.put(f"/api/sections/{sample_section['id']}", json={
            "section_type": "pills", "content": "Python, Docker",
        })
        assert res.status_code == 200
        assert res.get_json()["section_type"] == "pills"

    def test_update_invalid_section_type(self, logged_in_admin, sample_section):
        res = logged_in_admin.put(f"/api/sections/{sample_section['id']}", json={
            "section_type": "bad",
        })
        assert res.status_code == 400

    def test_create_quote_section(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Tagline", "slug": "tagline", "content": "Human after all.",
            "section_type": "quote",
        })
        assert res.status_code == 201
        assert res.get_json()["section_type"] == "quote"

    def test_create_currently_section(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Currently", "slug": "currently", "content": "Playing: Elden Ring\nReading: SICP",
            "section_type": "currently",
        })
        assert res.status_code == 201
        assert res.get_json()["section_type"] == "currently"

    def test_update_to_quote_type(self, logged_in_admin, sample_section):
        res = logged_in_admin.put(f"/api/sections/{sample_section['id']}", json={
            "section_type": "quote", "content": "A quote.",
        })
        assert res.status_code == 200
        assert res.get_json()["section_type"] == "quote"

    def test_update_to_currently_type(self, logged_in_admin, sample_section):
        res = logged_in_admin.put(f"/api/sections/{sample_section['id']}", json={
            "section_type": "currently", "content": "Playing: Chess",
        })
        assert res.status_code == 200
        assert res.get_json()["section_type"] == "currently"

    def test_create_intro_section(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Intro", "slug": "intro", "content": "Hello world.",
            "section_type": "intro",
        })
        assert res.status_code == 201
        assert res.get_json()["section_type"] == "intro"

    def test_create_project_section(self, logged_in_admin):
        res = logged_in_admin.post("/api/sections", json={
            "title": "Projects", "slug": "projects",
            "content": "Sanakenno|/sanakenno|A word game",
            "section_type": "project",
        })
        assert res.status_code == 201
        assert res.get_json()["section_type"] == "project"

    def test_section_type_in_list_response(self, logged_in_admin):
        logged_in_admin.post("/api/sections", json={
            "title": "Tech", "slug": "tech", "content": "Python",
            "section_type": "pills",
        })
        res = logged_in_admin.get("/api/sections")
        data = res.get_json()
        assert any(s["section_type"] == "pills" for s in data)


class TestDeleteSection:
    def test_delete_as_admin(self, logged_in_admin, sample_section):
        res = logged_in_admin.delete(f"/api/sections/{sample_section['id']}")
        assert res.status_code == 200

        res = logged_in_admin.get("/api/sections")
        assert res.get_json() == []

    def test_delete_unauthenticated(self, client, sample_section):
        res = client.delete(f"/api/sections/{sample_section['id']}")
        assert res.status_code == 401

    def test_delete_nonexistent(self, logged_in_admin):
        res = logged_in_admin.delete("/api/sections/9999")
        assert res.status_code == 404
