from pathlib import Path


def test_flask_startup_does_not_run_live_migrations():
    source = Path("app/__init__.py").read_text()

    forbidden = [
        "ALTER TABLE",
        "PRAGMA table_info",
        "_run_migrations",
        "DROP TABLE",
        "CREATE TABLE",
    ]

    for pattern in forbidden:
        assert pattern not in source
