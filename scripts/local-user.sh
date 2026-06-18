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

export SECRET_KEY="${SECRET_KEY:-dev}"
export DATABASE_URI="${DATABASE_URI:-sqlite:///$ROOT_DIR/app/data/site.db}"

mkdir -p "$ROOT_DIR/app/data"
exec "$(choose_python)" -m app.create_user "$@"
