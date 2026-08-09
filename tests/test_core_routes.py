"""Tests for app/routes.py — sitemap and the SPA catch-all's status codes.

The catch-all tests write a throwaway dist/ so they don't depend on a real
`nuxt generate` having run (app/static/dist/ is gitignored).
"""
import os
import xml.etree.ElementTree as ET

import pytest

import app.routes as routes_module
from app.utils import is_known_route

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@pytest.fixture()
def fake_dist(tmp_path, monkeypatch):
    """Point the catch-all at a temporary dist/ containing the SPA shell."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "200.html").write_text("<!doctype html><div id=__nuxt></div>")
    (dist / "index.html").write_text("<!doctype html><h1>home</h1>")
    (dist / "favicon.ico").write_text("icon-bytes")
    monkeypatch.setattr(routes_module, "DIST_DIR", str(dist))
    return dist


# ---------------------------------------------------------------------------
# /sitemap.xml
# ---------------------------------------------------------------------------

class TestSitemap:
    def test_is_well_formed_xml(self, client):
        res = client.get("/sitemap.xml")
        assert res.status_code == 200
        assert res.mimetype == "application/xml"
        ET.fromstring(res.data)  # raises on malformed XML

    def test_lists_every_public_page(self, client):
        root = ET.fromstring(client.get("/sitemap.xml").data)
        locs = {el.text for el in root.findall(".//sm:loc", SITEMAP_NS)}
        assert locs == {
            "https://erez.ac/",
            "https://erez.ac/dog",
            "https://erez.ac/dog/about-crawler",
        }

    def test_every_url_has_lastmod(self, client):
        root = ET.fromstring(client.get("/sitemap.xml").data)
        urls = root.findall("sm:url", SITEMAP_NS)
        assert urls
        for url in urls:
            assert url.find("sm:lastmod", SITEMAP_NS) is not None


# ---------------------------------------------------------------------------
# is_known_route
# ---------------------------------------------------------------------------

class TestIsKnownRoute:
    @pytest.mark.parametrize("path", [
        "/", "", "/login", "/admin", "/recipes", "/dog",
        "/dog/about-crawler", "/recipes/pancakes", "/recipes/pancakes/edit",
        "/about", "/contact",
        "dog", "recipes/pancakes",       # Flask <path:path> form, no leading slash
        "/dog/", "/recipes/",            # trailing slash
    ])
    def test_known(self, path):
        assert is_known_route(path) is True

    @pytest.mark.parametrize("path", [
        "/nope", "/wp-admin", "/.env", "/doggy", "/recipesx",
        "/admin-panel", "/login.php",
    ])
    def test_unknown(self, path):
        assert is_known_route(path) is False

    def test_prefix_match_requires_a_boundary(self):
        """'/doggy' must not ride in on the '/dog' prefix."""
        assert is_known_route("/dog") is True
        assert is_known_route("/doggy") is False

    def test_non_string_is_not_a_route(self):
        assert is_known_route(None) is False
        assert is_known_route(123) is False


# ---------------------------------------------------------------------------
# Catch-all status codes
# ---------------------------------------------------------------------------

class TestCatchAll:
    def test_known_spa_route_returns_200(self, client, fake_dist):
        res = client.get("/recipes/pancakes")
        assert res.status_code == 200
        assert b"__nuxt" in res.data

    def test_unknown_path_returns_404(self, client, fake_dist):
        res = client.get("/definitely-not-a-page")
        assert res.status_code == 404

    def test_unknown_path_still_serves_the_spa_shell(self, client, fake_dist):
        """404 status, but the client router still renders the styled 404 page."""
        res = client.get("/definitely-not-a-page")
        assert b"__nuxt" in res.data

    def test_real_static_asset_is_unaffected(self, client, fake_dist):
        res = client.get("/favicon.ico")
        assert res.status_code == 200
        assert b"icon-bytes" in res.data

    def test_directory_index_is_unaffected(self, client, fake_dist):
        sub = fake_dist / "dog"
        sub.mkdir()
        (sub / "index.html").write_text("<h1>dog</h1>")
        res = client.get("/dog")
        assert res.status_code == 200
        assert b"<h1>dog</h1>" in res.data

    def test_traversal_outside_dist_returns_404(self, client, fake_dist):
        res = client.get("/../../etc/passwd")
        assert res.status_code == 404
        assert b"root:" not in res.data

    def test_root_is_not_a_404(self, client, fake_dist):
        res = client.get("/")
        assert res.status_code == 200
