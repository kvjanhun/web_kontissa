"""Verify ProxyFix is wired so the rate limiter sees the real client IP."""

from werkzeug.middleware.proxy_fix import ProxyFix

from app import app


def test_wsgi_app_is_wrapped_in_proxy_fix():
    """app.wsgi_app should be a ProxyFix instance configured for one hop."""
    assert isinstance(app.wsgi_app, ProxyFix)
    assert app.wsgi_app.x_for == 1
    assert app.wsgi_app.x_proto == 1
    # x_host and x_prefix stay at 0 — bumping them silently lets clients spoof
    # the Host header / URL prefix Flask sees.
    assert app.wsgi_app.x_host == 0
    assert app.wsgi_app.x_prefix == 0


def test_proxy_fix_translates_forwarded_headers():
    """A request with X-Forwarded-For should produce the original IP in environ."""
    captured = {}

    def app_callable(environ, start_response):
        captured["REMOTE_ADDR"] = environ["REMOTE_ADDR"]
        captured["wsgi.url_scheme"] = environ["wsgi.url_scheme"]
        start_response("200 OK", [])
        return [b""]

    middleware = ProxyFix(app_callable, x_for=1, x_proto=1, x_host=0, x_prefix=0)
    environ = {
        "REMOTE_ADDR": "127.0.0.1",
        "wsgi.url_scheme": "http",
        "HTTP_X_FORWARDED_FOR": "203.0.113.42",
        "HTTP_X_FORWARDED_PROTO": "https",
    }
    middleware(environ, lambda *args, **kwargs: None)

    assert captured["REMOTE_ADDR"] == "203.0.113.42"
    assert captured["wsgi.url_scheme"] == "https"
