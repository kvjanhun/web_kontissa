# Dog API Split Refactor

Status: approved
Date: 2026-06-17

## Objective
Break the 2,255-line `app/api/dog.py` module into smaller, agent-discoverable backend modules without changing `/api/dog/*` behavior, cache file formats, crawler cadence, or frontend contracts.

## Context
`app/api/dog.py` currently owns the Flask blueprint, Showlink HTTP client, HTML parsers, date/stat helpers, in-memory TTL caches, persisted JSON index and result-cache storage, result job queue, crawler entrypoints, immediate warmup threading, and search assembly. The recent frontend refactor moved `/dog` into a feature module; the backend now has the same discoverability problem the frontend used to have.

The refactor should optimize for future agents finding the right code first, while keeping the existing operationally-sensitive dog show browser stable.

## Approach
Yes, `dog.py` should be split, but as a staged mechanical refactor rather than a rewrite.

Keep `app/api/dog.py` as the public compatibility facade at first: it should continue exporting `dog_bp`, crawler entrypoints, cache globals used by tests, and constants used by `scripts/dog_crawl.py`. Move implementation behind it into a dedicated backend package, likely `app/dog_show/`, so route registration stays unchanged while the large responsibilities become visible modules.

Suggested first split:

- `app/dog_show/config.py` for constants, environment-derived paths, TTLs, and `BASE_URL`.
- `app/dog_show/time_utils.py` for Finnish month/date parsing, `_utc_iso`, recency, and show date state.
- `app/dog_show/showlink.py` for `_source_url` and `_fetch_page`.
- `app/dog_show/parsers.py` for `_parse_show_list`, `_parse_show_detail`, breed-list target discovery, and `_parse_breed_results`.
- `app/dog_show/store.py` for atomic JSON writes, index loading/saving, result cache docs, result jobs, and in-memory cache objects.
- `app/dog_show/results.py` for whole-show result cache lifecycle, progress, single-breed extraction from all-results, and immediate warmup orchestration.
- `app/dog_show/crawler.py` for `crawl_index_once`, `crawl_empty_index_once`, and `crawl_result_cache_once`.
- `app/dog_show/search.py` for search normalization, indexed/cached judge merging, and response assembly.
- `app/api/dog.py` for Flask routes, request validation, JSON response adaptation, rate limits, and temporary compatibility re-exports.

Do the move in thin slices. First extract pure helpers and parsers with tests green. Then extract storage/job/result-cache code. Then extract crawler/search service functions. Only after tests target the new modules should `app/api/dog.py` be reduced to routes and documented compatibility exports.

Avoid changing function behavior during the split. Some names can stay private temporarily to reduce review risk; cleanup naming can be a follow-up once module boundaries are proven.

## Files to touch
- `app/api/dog.py` - shrink to routes plus compatibility exports.
- `app/dog_show/__init__.py` - package marker and possibly selected public exports.
- `app/dog_show/config.py` - constants and environment path configuration.
- `app/dog_show/time_utils.py` - date, recency, and timestamp helpers.
- `app/dog_show/showlink.py` - Showlink URL and HTTP fetch helpers.
- `app/dog_show/parsers.py` - BeautifulSoup parsers for show list, show detail, and breed results.
- `app/dog_show/store.py` - JSON persistence and shared in-memory caches.
- `app/dog_show/results.py` - result-cache response, progress, crawl-for-show, and warmup helpers.
- `app/dog_show/crawler.py` - crawler pass orchestration called by `scripts/dog_crawl.py`.
- `app/dog_show/search.py` - show/breed/judge search assembly.
- `scripts/dog_crawl.py` - optionally import crawler functions from the new package once compatibility is proven.
- `tests/test_dog.py` - update patch paths and add targeted tests for extracted modules where useful.
- `docs/dog-show-browser.md` - update backend fast path and entrypoint map.
- `app/CLAUDE.md` - update dog backend quick reference.

## API / data shape
No public API or data-shape changes are intended.

The following must remain stable:

- `GET /api/dog/shows`
- `GET /api/dog/shows/<show_id>`
- `GET /api/dog/shows/<show_id>/results?group=<group>&breed=<breed>`
- `GET /api/dog/shows/<show_id>/all-results`
- `GET /api/dog/search?q=<query>`
- `dog_show_index.json`
- `dog_result_cache/<show_id>.json`
- `dog_result_jobs.json`
- Environment variables documented in `docs/dog-show-browser.md`

## Tests
- Backend: run `python3 -m pytest tests/test_dog.py` after each extraction slice.
- Backend focused additions: add or preserve direct coverage for parsers, date helpers, job queue state transitions, result-cache freshness/progress, and route validation.
- E2E: run `cd frontend && CI=1 npm run test:e2e -- dog.spec.js` after the backend split is complete, because route behavior must remain identical for the refactored frontend.
- Build: `cd frontend && npm run build` should not be required for a backend-only split unless docs or frontend contracts change, but it is reasonable before merging if time allows.

## Security considerations
This refactor should introduce no new input vectors, expose no new internal state, and weaken no network boundary.

Risks to preserve explicitly:

- Keep `group` and `breed` numeric/range validation in the route layer.
- Keep Showlink fetching server-side only; do not expose raw fetch/proxy primitives.
- Keep rate limits on all public endpoints.
- Keep JSON persistence paths controlled by existing environment variables, not user input.
- Do not leak filesystem paths or cache internals in JSON errors beyond current behavior.
- Preserve bounded crawler concurrency, request delays, retry backoff, and immediate warmup limits.

## Out of scope
- Changing Showlink parsing behavior.
- Changing cache TTLs, crawler cadence, or job backoff.
- Changing frontend `/dog` behavior or UI.
- Reworking the JSON cache format or moving dog state into SQLite.
- Renaming public endpoints or changing response shapes.

## Open questions
- Should the new backend package be `app/dog_show/` to keep `app/api/dog.py` as a stable route facade, or should `app/api/dog.py` become an `app/api/dog/` package? I lean toward `app/dog_show/` for a lower-risk first refactor.
- How much backward compatibility should `app/api/dog.py` keep for private helper imports used by tests? I lean toward preserving crawler/cache globals for one refactor, then tightening tests in a follow-up.
