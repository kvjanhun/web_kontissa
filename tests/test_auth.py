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

    def test_invalid_login_logs_hashed_email_only(self, client, monkeypatch):
        from app import auth as auth_module

        records = []

        class CaptureLogger:
            def warning(self, event, **kwargs):
                records.append((event, kwargs))

        monkeypatch.setattr(auth_module, "logger", CaptureLogger())

        email = "Somebody@Test.com"
        res = client.post("/api/login", json={"email": email, "password": "wrong"})

        assert res.status_code == 401
        assert len(records) == 1
        assert records[0][0] == "login_failed"
        payload = records[0][1]
        assert payload["reason"] == "invalid credentials"
        assert "email" not in payload
        assert len(payload["email_hash"]) == 64
        assert email not in str(records)

    def test_login_email_hash_is_normalized_and_deterministic(self, client, monkeypatch):
        from app import auth as auth_module

        records = []

        class CaptureLogger:
            def warning(self, event, **kwargs):
                records.append(kwargs)

        monkeypatch.setattr(auth_module, "logger", CaptureLogger())

        client.post("/api/login", json={"email": "Somebody@Test.com", "password": "wrong"})
        client.post("/api/login", json={"email": " somebody@test.com ", "password": "wrong"})

        assert records[0]["email_hash"] == records[1]["email_hash"]

    def test_successful_login_logs_hashed_email_only(self, client, admin_user, monkeypatch):
        from app import auth as auth_module

        records = []

        class CaptureLogger:
            def info(self, event, **kwargs):
                records.append((event, kwargs))

        monkeypatch.setattr(auth_module, "logger", CaptureLogger())

        res = client.post("/api/login", json={
            "email": admin_user["email"],
            "password": admin_user["password"],
        })

        assert res.status_code == 200
        assert records[0][0] == "login_success"
        payload = records[0][1]
        assert payload["user_id"] == admin_user["id"]
        assert "email" not in payload
        assert len(payload["email_hash"]) == 64
        assert admin_user["email"] not in str(records)


class TestLogout:
    def test_logout_when_logged_in(self, logged_in_admin):
        res = logged_in_admin.post("/api/logout")
        assert res.status_code == 200
        assert res.get_json()["message"] == "Logged out"

    def test_logout_when_not_logged_in(self, client, app):
        res = client.post("/api/logout")
        assert res.status_code == 401


class TestRateLimit:
    def test_login_rate_limited(self, app, client):
        from app import limiter
        limiter.enabled = True
        try:
            for _ in range(3):
                client.post("/api/login", json={"email": "x@x.com", "password": "x"})
            res = client.post("/api/login", json={"email": "x@x.com", "password": "x"})
            assert res.status_code == 429
        finally:
            limiter.enabled = False
            limiter.reset()


class TestMe:
    def test_me_authenticated(self, logged_in_admin, admin_user):
        res = logged_in_admin.get("/api/me")
        assert res.status_code == 200
        assert res.get_json()["email"] == admin_user["email"]

    def test_me_not_authenticated(self, client, app):
        res = client.get("/api/me")
        assert res.status_code == 200
        assert res.get_json() is None
