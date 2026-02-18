class TestLogin:
    def test_login_success(self, client, admin_user):
        res = client.post("/api/login", json={
            "email": admin_user["email"],
            "password": admin_user["password"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["email"] == admin_user["email"]
        assert data["role"] == "admin"
        assert "password" not in data
        assert "password_hash" not in data

    def test_login_wrong_password(self, client, admin_user):
        res = client.post("/api/login", json={
            "email": admin_user["email"],
            "password": "wrong",
        })
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client, app):
        res = client.post("/api/login", json={
            "email": "nobody@test.com",
            "password": "whatever",
        })
        assert res.status_code == 401

    def test_login_missing_body(self, client, app):
        res = client.post("/api/login", content_type="application/json")
        assert res.status_code == 400

    def test_login_missing_fields(self, client, app):
        res = client.post("/api/login", json={"email": "a@b.com"})
        assert res.status_code == 400

    def test_login_empty_fields(self, client, app):
        res = client.post("/api/login", json={"email": "", "password": ""})
        assert res.status_code == 400


class TestLogout:
    def test_logout_when_logged_in(self, logged_in_admin):
        res = logged_in_admin.post("/api/logout")
        assert res.status_code == 200
        assert res.get_json()["message"] == "Logged out"

    def test_logout_when_not_logged_in(self, client, app):
        res = client.post("/api/logout")
        assert res.status_code == 401


class TestMe:
    def test_me_authenticated(self, logged_in_admin, admin_user):
        res = logged_in_admin.get("/api/me")
        assert res.status_code == 200
        assert res.get_json()["email"] == admin_user["email"]

    def test_me_not_authenticated(self, client, app):
        res = client.get("/api/me")
        assert res.status_code == 401
