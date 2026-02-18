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
