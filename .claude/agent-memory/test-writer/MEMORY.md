# Test Writer Memory — web_kontissa

## Framework & Tooling
- **Test runner**: pytest (pytest-8.4.2)
- **Python**: 3.9.6 (system Python on macOS, `/Applications/Xcode.app/...`)
- **Run command**: `python3 -m pytest tests/ -v` from `/Users/erezac/Projects/web_kontissa`
- **Config**: no pytest.ini; rootdir is `/Users/erezac/Projects/web_kontissa`

## Test File Locations
- `tests/conftest.py` — shared fixtures
- `tests/test_auth.py` — auth endpoint tests
- `tests/test_kenno.py` — Sanakenno spelling bee tests (39 tests)
- `tests/test_recipes.py` — recipe CRUD tests
- `tests/test_sections.py` — sections CRUD tests
- `tests/test_weather.py` — weather endpoint + helper function tests

## Fixtures (conftest.py)
- `app(tmp_path)` — Flask test app with isolated SQLite DB, rate limiting disabled
- `client(app)` — Flask test client
- `admin_user(app)` — creates admin in DB, returns dict with id/email/password
- `regular_user(app)` — creates regular user in DB
- `logged_in_admin(client, admin_user)` — client pre-authenticated as admin
- `logged_in_user(client, regular_user)` — client pre-authenticated as regular user
- `sample_section(app)` — creates a test section
- `sample_recipe(app, regular_user)` — creates a test recipe with ingredients/steps

## Conventions
- Class-based test organisation: `class TestFeature` with method-per-scenario
- No `unittest.TestCase` — plain classes with pytest fixtures as method params
- Assert-style assertions (no `self.assert*`)
- Descriptive names: `test_<behaviour>_when_<condition>` or `test_<field>_<property>`
- Rate limiting disabled globally in tests via `limiter.enabled = False` in app fixture

## Mocking Patterns
- Use `unittest.mock.patch` as context manager for time-based tests
- `patch("app.api.kenno.date")` to control `date.today()` for puzzle rotation tests
- Prefer narrow patches (module path, not stdlib path) to avoid leaking into other tests

## Import Paths for Internal Functions
- `from app.api.kenno import _score_word, _compute_puzzle` — all importable
- Seed data loaded from `scripts/initial_puzzles.json` in tests as `_SEED_DATA`
- `from app import app as flask_app, limiter` — app and limiter importable directly

## Known Patterns / Pitfalls
- `_PUZZLE_CACHE` in kenno.py is module-level; tests may see cached results across
  test runs within the same process — this is fine because compute is deterministic
- Puzzles are DB-backed; conftest seeds from `scripts/initial_puzzles.json` for tests
- Rotation formula: `(START_INDEX + days_since_ROTATION_START) % _total_puzzles()`
- The `_score_word` function signature is `_score_word(word, all_letters_frozenset)`;
  pass a `frozenset`, not a `set`

## Test Count Baseline
- Total: 304 tests, all passing (as of 2026-03-07)
- Kenno tests: 128
