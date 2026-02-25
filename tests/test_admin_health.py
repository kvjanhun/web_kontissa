"""Tests for the admin health endpoint."""


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
