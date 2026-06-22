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
| JSON-shape ↔ row conversion (single source of truth) | `sqlstore.py` |
| Persistence facade, in-memory `_show_index` mirror, result jobs | `store.py` |
| Indexed show stats, judge enrichment, show-detail cache helpers | `indexing.py` |
| Show-list cache refresh | `shows.py` |
| Breed-index crawler passes | `crawler.py` |
| Whole-show result cache, progress, warmup threads | `result_cache.py` |
| Show/breed/judge search assembly | `search.py` |
| CLI crawler process | `../../scripts/dog_crawl.py` |
| Backend tests | `../../tests/test_dog.py` |

## Boundaries

- Keep public endpoint behavior in `app/api/dog.py`.
- Keep Showlink fetching in `showlink.py`; frontend code must not scrape or fan out over breed pages.
- Keep all dog.db reads/writes behind `store.py`; the JSON↔row mapping lives only in `sqlstore.py` and the schema only in `models.py`. Do not open the dog database directly from routes, indexing, or the crawler.
- Keep parser changes in `parsers.py` and cover Showlink page-shape changes in `tests/test_dog.py`.
- Keep result-cache orchestration in `result_cache.py`; this is where concurrency, backoff, stale-cache handling, and immediate warmup limits live.
- Keep crawler loop orchestration in `scripts/dog_crawl.py`; reusable crawler pass functions live in `crawler.py` and `result_cache.py`.

## Compatibility Notes

`app/api/dog.py` intentionally re-exports several private helpers and cache objects while the test suite and crawler migrate to the package modules. Do not remove those exports casually; first update `tests/test_dog.py`, `scripts/dog_crawl.py`, and any docs that still point at the facade.

The shared `_show_index` object is mutated in place by `store._load_index()` so imports from `store.py`, `indexing.py`, and `app/api/dog.py` continue seeing the same dictionary. It is now a SQL-backed mirror: `_load_index()` reloads it from `dog.db` only when the `dog_meta.index_generation` counter advances, and code that mutates a show in place must mark it dirty (`store._mark_index_dirty(sid)`) before `_save_index()` so the per-show flush persists it.

## dog.db (the persistent store)

- Dog state lives in its own SQLite database, `dog.db` (`DOG_DATABASE_URI`), separate from `site.db` and not Litestream-replicated. It uses a standalone SQLAlchemy engine (`db.py`), **not** the Flask-SQLAlchemy `db`, because dog writes happen in background threads and the crawler process with no Flask app context.
- It is a **permanent database, not a cache**: never add row-deleting retention/eviction for historical shows. TTLs govern only re-fetching of live/recent shows.
- No referential or identity constraints are enforced (no `PRAGMA foreign_keys`, no breed `UniqueConstraint`) — the legacy JSON store had none and several paths depend on that permissiveness. Per-breed judges are stored on both `dog_breed.judge` and `dog_result.breed_judge` (the result cache is the source of judges).

## Change Checklist

- Preserve all `/api/dog/*` response shapes unless the frontend and E2E tests are changed deliberately.
- Preserve the dict shapes `store.py` exposes (`_show_index` entries, whole-show result docs, the result-jobs doc) — `sqlstore.py` round-trips them and `tests/test_dog.py` locks them in.
- No live migrations at import/startup. `db.init_db()` only creates missing tables; any column/table change needs an explicit plan, tests, and a reviewed one-off prod migration (see `scripts/migrate_dog_to_sql.py`).
- Keep `group` and `breed` validation in the route layer.
- Keep crawler request volume bounded: respect worker limits, request delay, retry backoff, and `retry_after`.
- Run `python3 -m pytest tests/test_dog.py` after backend behavior changes when the app test harness is healthy.
