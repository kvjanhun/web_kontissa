"""Regression tests for cross-cutting hardening:

- the rate limiter must key on the real client IP (ProxyFix), not the proxy;
- the static catch-all must not serve files outside dist/ via path traversal;
- admin-authored links must reject script-bearing href schemes.
"""
import os

from flask import request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from app import app as flask_app
from app.routes import _resolve_within_dist, DIST_DIR
from app.home_content import _is_safe_href, _validate_links


# A stable probe route (registered once) that echoes the remote_addr Flask — and
# therefore the rate limiter — ends up seeing after the WSGI stack runs ProxyFix.
@flask_app.route("/__proxyfix_probe__")
def _proxyfix_probe():
    return jsonify(ip=request.remote_addr)


class TestProxyFix:
    def test_wsgi_app_is_wrapped_with_proxy_fix(self):
        # Without ProxyFix, request.remote_addr is the Docker gateway and every
        # visitor shares one rate-limit bucket. Guard against silent removal.
        assert isinstance(flask_app.wsgi_app, ProxyFix)

    def test_trusts_exactly_one_forwarded_hop(self):
        # x_for=1 takes the single nginx-added hop; a client-supplied
        # X-Forwarded-For entry must not be trusted.
        assert flask_app.wsgi_app.x_for == 1

    def test_resolves_real_client_ip_from_forwarded_header(self):
        # Drive the full WSGI stack so ProxyFix runs, and capture the
        # remote_addr Flask (and thus the limiter) ends up seeing. nginx appends
        # the real client last in the chain: "<spoof>, <real>".
        client = flask_app.test_client()
        resp = client.get(
            "/__proxyfix_probe__",
            headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7"},
            environ_overrides={"REMOTE_ADDR": "172.18.0.1"},
        )
        assert resp.get_json()["ip"] == "203.0.113.7"


class TestCatchAllContainment:
    def test_legitimate_nested_path_stays_inside_dist(self):
        dist_root, resolved = _resolve_within_dist("dog/index.html")
        assert resolved is not None
        assert resolved.startswith(dist_root + os.sep)

    def test_parent_traversal_is_rejected(self):
        _, resolved = _resolve_within_dist("../../etc/passwd")
        assert resolved is None

    def test_encoded_deep_traversal_is_rejected(self):
        _, resolved = _resolve_within_dist("../" * 10 + "etc/hosts")
        assert resolved is None

    def test_dist_root_itself_is_allowed(self):
        dist_root, resolved = _resolve_within_dist("")
        assert resolved == os.path.realpath(DIST_DIR)


class TestSafeHref:
    def test_allows_relative_and_anchor_and_known_schemes(self):
        for href in ("/recipes", "#work", "./x", "../y",
                     "https://github.com", "http://x.test",
                     "mailto:a@b.test", "tel:+358401234567",
                     "page/sub#frag"):
            assert _is_safe_href(href), href

    def test_rejects_script_and_data_schemes(self):
        for href in ("javascript:alert(1)", "JavaScript:alert(1)",
                     "java\tscript:alert(1)", " javascript:alert(1)",
                     "data:text/html,<script>", "vbscript:msgbox"):
            assert not _is_safe_href(href), href

    def test_validate_links_rejects_javascript_href(self):
        cleaned, err = _validate_links([{"label": "x", "href": "javascript:alert(1)"}])
        assert cleaned is None
        assert err is not None

    def test_validate_links_accepts_normal_href(self):
        cleaned, err = _validate_links([{"label": "GitHub", "href": "https://github.com"}])
        assert err is None
        assert cleaned == [{"label": "GitHub", "href": "https://github.com"}]
