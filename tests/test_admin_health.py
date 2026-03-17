"""Tests for health/info endpoints."""


class TestServerInfo:
    """GET /api/server-info"""

    def test_public_no_auth_required(self, client):
        res = client.get("/api/server-info")
        assert res.status_code == 200

    def test_returns_expected_keys(self, client):
        data = client.get("/api/server-info").get_json()
        assert "uptime_seconds" in data
        assert "request_count" in data
        assert "disk_used_percent" in data
        assert "memory_total_mb" in data
        assert "memory_used_mb" in data

    def test_uptime_non_negative(self, client):
        data = client.get("/api/server-info").get_json()
        assert data["uptime_seconds"] >= 0

    def test_request_count_positive(self, client):
        data = client.get("/api/server-info").get_json()
        assert data["request_count"] > 0


class TestAdminHealth:
    """GET /api/admin/health"""

    def test_requires_auth(self, client):
        res = client.get("/api/admin/health")
        assert res.status_code == 401

    def test_requires_admin(self, logged_in_user):
        res = logged_in_user.get("/api/admin/health")
        assert res.status_code == 403

    def test_returns_expected_keys(self, logged_in_admin):
        res = logged_in_admin.get("/api/admin/health")
        assert res.status_code == 200
        data = res.get_json()
        assert "python_version" in data
        assert "db_size_bytes" in data
        assert "disk_total_bytes" in data
        assert "disk_free_bytes" in data
        assert "uptime_seconds" in data

    def test_uptime_positive(self, logged_in_admin):
        res = logged_in_admin.get("/api/admin/health")
        data = res.get_json()
        assert data["uptime_seconds"] >= 0

    def test_python_version_nonempty(self, logged_in_admin):
        res = logged_in_admin.get("/api/admin/health")
        data = res.get_json()
        assert len(data["python_version"]) > 0
