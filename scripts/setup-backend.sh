#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

choose_python() {
    if [[ -n "${PYTHON:-}" ]]; then
        printf '%s\n' "$PYTHON"
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

"$PYTHON_BIN" - <<'PY'
import hashlib
import ssl
import sys

if sys.version_info < (3, 13):
    print(f"Python 3.13+ is required for local backend setup; found {sys.version.split()[0]}", file=sys.stderr)
    raise SystemExit(1)

if not hasattr(hashlib, "scrypt"):
    print("This Python cannot verify Werkzeug scrypt password hashes.", file=sys.stderr)
    print(f"Python: {sys.version.split()[0]}", file=sys.stderr)
    print(f"SSL: {ssl.OPENSSL_VERSION}", file=sys.stderr)
    print("Install a Python build linked against OpenSSL, for example: brew install python3", file=sys.stderr)
    raise SystemExit(1)

print(f"Using backend Python: {sys.executable} ({sys.version.split()[0]}, {ssl.OPENSSL_VERSION})")
PY

REQUIREMENTS_FILE="requirements.txt"
if [[ "${1:-}" == "--dev" ]]; then
    REQUIREMENTS_FILE="requirements-dev.txt"
fi

if [[ -d "$ROOT_DIR/.venv" ]]; then
    "$PYTHON_BIN" -m venv --upgrade "$ROOT_DIR/.venv"
else
    "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
fi

"$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip
"$ROOT_DIR/.venv/bin/python" -m pip install -r "$REQUIREMENTS_FILE"
