# Backend — Flask

## Key Patterns

- Flask app in `app/__init__.py`, imported by all modules
- **Blueprints**: All routes use blueprints (`core_bp`, `auth_bp`, `recipes_bp`, etc.) registered in `__init__.py`. No URL prefixes — paths stay identical.
- **Auth**: `@admin_required` decorator in `app/decorators.py` (wraps `@login_required` + role check). Recipe endpoints use `@login_required` (shared cookbook — any user can CRUD).
- All API endpoints return JSON
- `catch_all` route serves static files from `dist/`, pre-rendered `index.html` per route, or `200.html` SPA fallback for client-side routing
- GitHub API responses cached 6 hours (`utils.py`). FMI weather cached 10 minutes with stale fallback (`api/weather.py`).
- Showlink dog show data is scraped server-side (`api/dog.py` route facade, `dog_show/` implementation). Breed indexing runs from `scripts/dog_crawl.py` as a separate process, not from Flask/Gunicorn workers.

## Schema Changes

Never run migrations from Flask startup, imports, or request handlers. `app/__init__.py` may create empty tables for fresh local/test databases, but it must not contain `ALTER TABLE`, table rebuilds, schema probes, or hidden migration helpers. Any schema change needs an explicit plan, tests, E2E seed updates, and a reviewed one-off production SQLite migration/restore procedure.

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/home-content?locale=` | Public | DB-backed home content overlay map (fixed text blocks + assembled `home.projects`); limiter-exempt |
| GET/PUT | `/api/admin/home-content` | Admin | List both locales / upsert one field (`{key, locale, value}`) |
| GET/POST | `/api/admin/projects` | Admin | List (incl. hidden) / create a project |
| PUT/DELETE | `/api/admin/projects/<id>` | Admin | Update (parent + translations) / delete |
| PUT | `/api/admin/projects/reorder` | Admin | Reorder (`{"order": [id, ...]}`) |
| POST | `/api/login` | Public | Authenticate |
| POST | `/api/logout` | Login | End session |
| GET | `/api/me` | Public | Current user or 401 |
| GET | `/api/meta` | Public | Site metadata |
| GET | `/api/recipes` | Login | List (optional `?q=&category=`) |
| GET/POST/PUT/DELETE | `/api/recipes[/<slug\|id>]` | Login | CRUD recipes |
| GET | `/api/recipes/categories` | Login | Category list |
| POST | `/api/pageview` | Public | Track page view (session-deduped) |
| GET | `/api/pageviews` | Admin | All page views (aggregated counts) |
| GET | `/api/pageviews/events` | Admin | Time-series events (days param 1–90) |
| GET | `/api/server-info` | Public | Intentional coarse terminal status; keep fields limited to the tested whitelist |
| GET | `/api/admin/health` | Admin | System health |
| GET | `/api/cowsay` | Public | ASCII cow art |
| GET | `/api/weather` | Public | FMI weather (Helsinki-Vantaa) |
| GET | `/api/dog/shows` | Public | Showlink dog show list |
| GET | `/api/dog/shows/<id>` | Public | Dog show breed list |
| GET | `/api/dog/shows/<id>/results?group=&breed=` | Public | Breed results |
| GET | `/api/dog/shows/<id>/all-results` | Public | Whole-show dog results from persisted cache; queues cache warming when missing |
| GET | `/api/dog/search?q=` | Public | Search shows and indexed breed names |
| GET | `/sitemap.xml` | Public | SEO sitemap |

## Models

`User`, `HomeContent` (editable home `home.*` text blocks; one row per `key`+`locale`, JSON-encoded `value`), `Project` + `ProjectTranslation` (the home "Selected projects" collection — language-independent `position`/`hidden`/`image` on the parent, translatable text per locale in the child), `Recipe`, `Ingredient`, `Step`, `PageView`, `PageViewEvent`.

Home content is served from the DB (`app/home_content.py`), not the locale files. `HOME_CONTENT_FIELDS` in that module is the allow-list of editable keys and their shapes (string / string[] / layer[] / link[]); the frontend admin editor mirrors it. New tables are created by the idempotent `db.create_all()`; initial data is loaded by `scripts/seed_home_content.py` (from the committed `frontend/locales/home-content.snapshot.json`).

## Dog Shows Backend (`api/dog.py`, `dog_show/`)

Public Showlink browser. Start with `dog_show/AGENTS.md` for the backend file map. `api/dog.py` owns Flask routes, request validation, rate limits, and compatibility exports; `dog_show/` owns config, Showlink fetching, parsers, SQL persistence, indexing, search, crawler passes, and whole-show result cache orchestration. Dog state lives in a dedicated SQLite database, `dog.db` (the `/dog`-only persistent store — separate from `site.db`, standalone SQLAlchemy engine, not Litestream-replicated). It is a permanent database, not a cache: historical rows are never evicted.

`/api/dog/shows` fetches the current show list with a 30-minute cache. Show detail and breed result caches are short-lived for current/previous-month shows and effectively stable for old shows; `/api/dog/shows/<id>` serves the persisted breed index from `dog.db` directly when a breed list exists. `scripts/dog_crawl.py --loop` owns persisted crawler state: the breed index (`dog_show`/`dog_breed`) for search and the result cache (`dog_result_cache`/`dog_result`) for whole-show result filters. Missing `/all-results` caches are queued in `dog_result_job`; the API also starts one bounded immediate warmup per web worker so user-triggered caches do not wait for the crawler poll. In production the crawler checks queued result jobs every 30 seconds, auto-warms up to two result caches for shows from the last 7 days every 2 minutes, fetches result pages with 3 workers and 0.4s staggered starts, and keeps slower breed-index maintenance at 15 minutes. Docker sets `DOG_INDEX_DIR=/app/data` (and so `dog.db` defaults there) so web and crawler containers share the mounted data volume. The web process keeps an in-memory `_show_index` mirror and reloads it from `dog.db` only when the index generation counter advances; individual breed result endpoints can reuse a complete whole-show cache.

Keep detailed dog-show operations and tuning guidance in `../docs/dog-show-browser.md`; keep this section as the backend quick reference.
