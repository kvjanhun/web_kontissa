# Backend — Flask

## Key Patterns

- Flask app in `app/__init__.py`, imported by all modules
- **Blueprints**: All routes use blueprints (`core_bp`, `auth_bp`, `recipes_bp`, etc.) registered in `__init__.py`. No URL prefixes — paths stay identical.
- **Auth**: `@admin_required` decorator in `app/decorators.py` (wraps `@login_required` + role check). Recipe endpoints use `@login_required` (shared cookbook — any user can CRUD).
- All API endpoints return JSON
- `catch_all` route serves static files from `dist/`, pre-rendered `index.html` per route, or `200.html` SPA fallback for client-side routing. Paths outside `utils.is_known_route()` get the same `200.html` body with a **404 status** (so the client router still renders the styled 404 page while crawlers stop indexing junk URLs as real pages). `SPA_ROUTE_PREFIXES` in `app/utils.py` is that allow-list — keep it in sync with `frontend/pages/` and the redirect `routeRules`.
- GitHub API responses cached 6 hours (`utils.py`), with a 5-minute failure backoff (`FAILURE_RETRY_TTL`) so an outage or rate-limit can't make every `/api/meta` and `/sitemap.xml` request retry a 5s blocking call. FMI weather cached 10 minutes with stale fallback (`api/weather.py`).
- `PageViewEvent` retention is **not** automatic — `scripts/prune_pageview_events.py` drops rows past the 90-day window `/api/pageviews/events` can serve. Run it on a schedule (`docker exec web_kontissa-web-1 python scripts/prune_pageview_events.py`); nothing in the request path prunes.
- **Scripts that import `app` must not guess the DB path.** `docker-compose.yml` sets `DATABASE_URI=sqlite:////app/data/site.db` on `web` and `dog-crawler` so the environment is authoritative. The repo-relative fallback in `scripts/*.py` is guarded to dev hosts only: in the container the repo root *is* `/app` and the volume is mounted at `/app/data`, so `<root>/app/data/site.db` resolves to the non-existent `/app/app/data/site.db` and fails as `sqlite3.OperationalError: unable to open database file` during import, before any of the script's own code runs.
- Showlink dog show data is scraped server-side (`api/dog.py` route facade, `dog_show/` implementation). Breed indexing runs from `scripts/dog_crawl.py` as a separate process, not from Flask/Gunicorn workers.

## Schema Changes

Never run a schema change from Flask startup, imports, or request handlers. `app/__init__.py` may create empty tables for fresh local/test databases, but it must not contain `ALTER TABLE`, table rebuilds, schema probes, or a hidden helper that performs any of them. A schema change needs an explicit plan, tests, E2E seed updates, and a reviewed one-off procedure applied to the production SQLite file by hand. See the `schema-change` skill.

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
| POST | `/api/pageview` | Public | Track page view (session-deduped). Rejects paths outside `is_known_route()` with 400 — the endpoint is public, so an allow-list is what stops arbitrary rows being inserted into the Litestream-replicated `site.db`. The per-session dedup list is capped at `MAX_TRACKED_PATHS` because it rides in the signed cookie. |
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
| GET | `/api/dog/search?q=` | Public | Search shows, breeds, judges (index), plus dogs (aggregated by reg_id), owners & breeder-award kennels across all captured shows (SQL, `q≥3`) |
| GET | `/api/dog/dogs?reg=` | Public | Cross-show dog profile for one Kennelliitto reg number (query param — reg ids contain `/`) |
| GET | `/sitemap.xml` | Public | SEO sitemap (`/`, `/dog`, `/dog/about-crawler`) |

## Models

`User`, `HomeContent` (editable home `home.*` text blocks; one row per `key`+`locale`, JSON-encoded `value`), `Project` + `ProjectTranslation` (the home "Selected projects" collection — language-independent `position`/`hidden`/`image` on the parent, translatable text per locale in the child), `Recipe`, `Ingredient`, `Step`, `PageView`, `PageViewEvent`.

Home content is served from the DB (`app/home_content.py`), not the locale files. `HOME_CONTENT_FIELDS` in that module is the allow-list of editable keys and their shapes (string / string[] / layer[] / link[]); the frontend admin editor mirrors it. New tables are created by the idempotent `db.create_all()`; initial data is loaded by `scripts/seed_home_content.py` (from the committed `frontend/locales/home-content.snapshot.json`).

## Dog Shows Backend (`api/dog.py`, `dog_show/`)

Public Showlink browser. Start with `dog_show/AGENTS.md` for the backend file map. `api/dog.py` owns Flask routes, request validation, rate limits, and compatibility exports; `dog_show/` owns config, Showlink fetching, parsers, SQL persistence, indexing, search, crawler passes, and whole-show result cache orchestration. Dog state lives in a dedicated SQLite database, `dog.db` (the `/dog`-only persistent store — separate from `site.db`, standalone SQLAlchemy engine, not Litestream-replicated). It is a permanent database, not a cache: historical rows are never evicted.

`/api/dog/shows` fetches the current show list with a 30-minute cache — the only fetch-gating in-memory cache in the web tier. Everything else is read from `dog.db` per request (SQL-first, no index mirror): `/api/dog/shows/<id>` serves the persisted breed index directly, breed result endpoints extract from the persisted whole-show cache, and search runs as SQL scans over the index plus dog-name/owner queries. GET handlers are read-only; the crawler folds judges and result flags into the index at capture time. `scripts/dog_crawl.py --loop` owns all Showlink fetching beyond the list refresh: the breed index (`dog_show`/`dog_breed`) and the result cache (`dog_result_cache`/`dog_result`). Missing `/all-results` caches are queued in `dog_result_job` for the crawler (30-second queue poll). In production the crawler checks queued result jobs every 30 seconds, auto-warms up to two result caches for shows from the last 7 days every 2 minutes, fetches result pages with 3 workers and 0.4s staggered starts, and keeps slower breed-index maintenance at 15 minutes. Docker sets `DOG_INDEX_DIR=/app/data` (and so `dog.db` defaults there) so web and crawler containers share the mounted data volume.

Keep detailed dog-show operations and tuning guidance in `../docs/dog-show-browser.md`; keep this section as the backend quick reference.
