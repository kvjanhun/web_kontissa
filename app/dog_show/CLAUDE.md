# Dog Show Backend - Agent Guide

This package owns backend implementation for the `/dog` feature. The Flask route facade is still `app/api/dog.py`; most behavior lives here.

For frontend behavior, read `../../frontend/features/dog/AGENTS.md`. For operations and crawler tuning, read `../../docs/dog-show-browser.md`.

## Fast Map

| Need | Start here |
|------|------------|
| Flask routes, request validation, rate limits | `../api/dog.py` |
| Environment defaults and TTL constants | `config.py` |
| Date parsing, timestamp formatting, judge/breed normalization | `utils.py` |
| Showlink URL building and HTTP fetches | `showlink.py` |
| BeautifulSoup parsing for show lists, breed lists, breed results | `parsers.py` |
| Standalone dog.db engine + thread-local session | `db.py` |
| ORM models for dog.db | `models.py` |
| Dict-shape ↔ row conversion + all SQL queries (single source of truth) | `sqlstore.py` |
| Persistence facade (sessions, retries, error handling), result jobs | `store.py` |
| Award-structure terminal detection (is a live show finished?) | `finals.py` |
| Indexed show stats, show-detail assembly, breed-list helpers | `indexing.py` |
| Cross-show dog profile assembly (`/api/dog/dogs`, keyed on `dog_result.reg_id`) | `profile.py` |
| Show-list cache refresh | `shows.py` |
| Breed-index crawler passes | `crawler.py` |
| Whole-show result cache, progress, crawl passes | `result_cache.py` |
| Show/breed/judge search assembly | `search.py` |
| CLI crawler process | `../../scripts/dog_crawl.py` |
| One-off ops tools (finals rescue, judge/flag sweep) | `../../scripts/dog_rescue_finals.py`, `../../scripts/dog_sweep_breed_judges.py` |
| Backend tests | `../../tests/test_dog.py` |

## Boundaries

- Keep public endpoint behavior in `app/api/dog.py`.
- Keep Showlink fetching in `showlink.py`; frontend code must not scrape or fan out over breed pages.
- Keep all dog.db reads/writes behind `store.py`; the dict↔row mapping and SQL queries live only in `sqlstore.py` and the schema only in `models.py`. Do not open the dog database directly from routes, indexing, or the crawler.
- Keep GET handlers read-only. Judges and result flags are folded into `dog_breed` at capture time (result crawl success, re-index merge); never reintroduce write-backs into read paths.
- Keep parser changes in `parsers.py` and cover Showlink page-shape changes in `tests/test_dog.py`.
- Keep result-cache orchestration in `result_cache.py`; this is where concurrency, backoff, and stale-cache handling live.
- Keep crawler loop orchestration in `scripts/dog_crawl.py`; reusable crawler pass functions live in `crawler.py` and `result_cache.py`.

## Architecture Note

There is **no in-memory index mirror** (retired 2026-07): every read-path lookup — show detail, list stats, search — queries `dog.db` directly through `store.py`. The only in-memory state in the web tier is the 30-minute show-list fetch gate (`store._show_list_cache`) and the 20s per-show stats cache (`indexing._show_stats_cache`). Bulk breed reads use Core column selects (`sqlstore._BREED_COLUMNS`) because ORM hydration dominates at tens of thousands of rows.

## dog.db (the persistent store)

- Dog state lives in its own SQLite database, `dog.db` (`DOG_DATABASE_URI`), separate from `site.db` and not Litestream-replicated. It uses a standalone SQLAlchemy engine (`db.py`), **not** the Flask-SQLAlchemy `db`, because dog writes happen in the crawler process and one-off scripts with no Flask app context.
- It is a **permanent database, not a cache**: never add row-deleting retention/eviction for historical shows. TTLs govern only re-fetching of live/recent shows.
- No referential or identity constraints are enforced (no `PRAGMA foreign_keys`, no breed `UniqueConstraint`) — the legacy JSON store had none and several paths depend on that permissiveness. Per-breed judges are stored on both `dog_breed.judge` and `dog_result.breed_judge` (the result cache is the source of judges).

## Change Checklist

- Preserve all `/api/dog/*` response shapes unless the frontend and E2E tests are changed deliberately.
- Preserve the dict shapes `store.py` exposes (index show entries, whole-show result docs, the result-jobs doc) — `sqlstore.py` round-trips them and `tests/test_dog.py` locks them in.
- No schema changes at import/startup. `db.init_db()` only creates missing tables; any column/table change needs an explicit plan, tests, and a reviewed one-off procedure applied by hand. `dog.db` is not Litestream-replicated, so a destructive change here has no automatic restore path.
- Keep `group` and `breed` validation in the route layer.
- Keep crawler request volume bounded: respect worker limits, request delay, retry backoff, and `retry_after`.
- Run `python3 -m pytest tests/test_dog.py` after backend behavior changes when the app test harness is healthy.
