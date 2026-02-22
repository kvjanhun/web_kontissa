# docs-keeper memory — web_kontissa (erez.ac)

## Project Identity
- Personal portfolio for Konsta Janhunen at erez.ac
- Vue 3 SPA + Flask JSON API + SQLite, Docker-deployed on RHEL/Intel NUC

## Key Files to Watch
- `app/api/bee.py` — PUZZLES list drives the Sanakenno game (count = cycle length)
- `app/__init__.py` — Flask app factory: LoginManager + Flask-Limiter (30 req/min)
- `frontend/src/router.js` — authoritative route list (currently 11 routes)
- `requirements.txt` — authoritative Python dep list
- `tests/` — pytest suite; conftest.py uses in-memory SQLite, disables rate limiter

## Confirmed Patterns
- Port 5001 everywhere (run.py, vite.config.js proxy) — macOS AirPlay blocks 5000
- Puzzle cache in bee.py is lazy (on first access), not eager at startup
- `/api/bee` returns: center, letters, words, max_score, puzzle_number
- `scripts/process_kotus.py` is a one-time data generation script, not part of app runtime
- Tech stack includes Flask-Limiter — must appear in requirements.txt comment and tech table

## Structure Notes
- `scripts/` and `tests/` are top-level siblings of `app/` and `frontend/`
- Tree in CLAUDE.md must show `app/` as `├──` (not `└──`) since scripts/tests follow it
