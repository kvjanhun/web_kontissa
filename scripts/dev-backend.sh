#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

choose_python() {
    if [[ -n "${PYTHON:-}" ]]; then
        printf '%s\n' "$PYTHON"
        return
    fi

    if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
        printf '%s\n' "$ROOT_DIR/.venv/bin/python"
        return
    fi

    if command -v python3.14 >/dev/null 2>&1; then
        printf '%s\n' "python3.14"
        return
    fi

    if command -v python3.13 >/dev/null 2>&1; then
        printf '%s\n' "python3.13"
        return
    fi

    printf '%s\n' "python3"
}

PYTHON_BIN="$(choose_python)"

export SECRET_KEY="${SECRET_KEY:-dev}"
export FLASK_DEBUG="${FLASK_DEBUG:-1}"
export FLASK_RUN_HOST="${FLASK_RUN_HOST:-127.0.0.1}"
export FLASK_RUN_PORT="${FLASK_RUN_PORT:-5001}"
export DATABASE_URI="${DATABASE_URI:-sqlite:///$ROOT_DIR/app/data/site.db}"

mkdir -p "$ROOT_DIR/app/data"

"$PYTHON_BIN" - <<'PY'
import hashlib
import importlib.util
import ssl
import sys

requirements = {
    "flask": "Flask",
    "flask_sqlalchemy": "flask-sqlalchemy",
    "flask_login": "flask-login",
    "flask_limiter": "flask-limiter",
    "requests": "requests",
    "structlog": "structlog",
    "bs4": "beautifulsoup4",
}

missing = [package for module, package in requirements.items() if importlib.util.find_spec(module) is None]
if missing:
    print("Missing backend Python packages:", ", ".join(missing), file=sys.stderr)
    print("Install them with: python -m pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

if not hasattr(hashlib, "scrypt"):
    print("This Python cannot verify Werkzeug scrypt password hashes.", file=sys.stderr)
    print(f"Python: {sys.version.split()[0]}", file=sys.stderr)
    print(f"SSL: {ssl.OPENSSL_VERSION}", file=sys.stderr)
    print("Use a Python build linked against OpenSSL, for example:", file=sys.stderr)
    print("  brew install python3", file=sys.stderr)
    print("  npm run setup", file=sys.stderr)
    raise SystemExit(1)

print(f"Backend Python: {sys.executable} ({sys.version.split()[0]}, {ssl.OPENSSL_VERSION})")
PY

if [[ "${1:-}" == "--check" ]]; then
    exit 0
fi

echo "Backend: http://${FLASK_RUN_HOST}:${FLASK_RUN_PORT}"
exec "$PYTHON_BIN" run.py
