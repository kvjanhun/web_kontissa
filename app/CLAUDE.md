# Backend — Flask

## Key Patterns

- Flask app in `app/__init__.py`, imported by all modules
- **Blueprints**: All routes use blueprints (`core_bp`, `auth_bp`, `recipes_bp`, etc.) registered in `__init__.py`. No URL prefixes — paths stay identical.
- **Auth**: `@admin_required` decorator in `app/decorators.py` (wraps `@login_required` + role check). Recipe endpoints use `@login_required` (shared cookbook — any user can CRUD).
- All API endpoints return JSON
- `catch_all` route serves static files from `dist/`, pre-rendered `index.html` per route, or `200.html` SPA fallback for client-side routing
- GitHub API responses cached 6 hours (`utils.py`). FMI weather cached 10 minutes with stale fallback (`api/weather.py`).
- Showlink dog show data is scraped server-side (`api/dog.py` route facade, `dog_show/` implementation). Breed indexing runs from `scripts/dog_crawl.py` as a separate process, not from Flask/Gunicorn workers.

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/sections` | Public | List sections (ordered by position) |
| POST/PUT/DELETE | `/api/sections[/<id>]` | Admin | CRUD sections |
| PUT | `/api/sections/reorder` | Admin | Reorder (`{"order": [id, ...]}`) |
| POST | `/api/login` | Public | Authenticate |
| POST | `/api/logout` | Login | End session |
| GET | `/api/me` | Public | Current user or 401 |
| GET | `/api/meta` | Public | Site metadata |
| GET | `/api/project-stats` | Public | GitHub repo stats (commits, size, languages; cached 6h) |
| GET | `/api/recipes` | Login | List (optional `?q=&category=`) |
| GET/POST/PUT/DELETE | `/api/recipes[/<slug\|id>]` | Login | CRUD recipes |
| GET | `/api/recipes/categories` | Login | Category list |
| POST | `/api/pageview` | Public | Track page view (session-deduped) |
| GET | `/api/pageviews` | Admin | All page views (aggregated counts) |
| GET | `/api/pageviews/events` | Admin | Time-series events (days param 1–90) |
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

`User`, `Section` (with `section_type`: text/pills/quote/currently/intro/project/git_stats/timeline), `Recipe`, `Ingredient`, `Step`, `PageView`, `PageViewEvent`

## Dog Shows Backend (`api/dog.py`, `dog_show/`)

Public Showlink browser. Start with `dog_show/AGENTS.md` for the backend file map. `api/dog.py` owns Flask routes, request validation, rate limits, and compatibility exports; `dog_show/` owns config, Showlink fetching, parsers, JSON persistence, indexing, search, crawler passes, and whole-show result cache orchestration.

`/api/dog/shows` fetches the current show list with a 30-minute cache. Show detail and breed result caches are short-lived for current/previous-month shows and effectively stable for old shows; `/api/dog/shows/<id>` serves `dog_show_index.json` directly when a persisted breed list exists. `scripts/dog_crawl.py --loop` owns persisted crawler state: `dog_show_index.json` for breed search and `dog_result_cache/<show_id>.json` for whole-show result filters. Missing `/all-results` caches are queued in `dog_result_jobs.json`; the API also starts one bounded immediate warmup per web worker so user-triggered caches do not wait for the crawler poll. In production the crawler checks queued result jobs every 30 seconds, auto-warms up to two result caches for shows from the last 7 days every 2 minutes, fetches result pages with 3 workers and 0.4s staggered starts, and keeps slower breed-index maintenance at 15 minutes. Docker sets `DOG_INDEX_DIR=/app/data` so web and crawler containers share the mounted data volume. The web process reloads the breed index when it changes and serves whole-show result caches directly from disk; individual breed result endpoints can reuse a complete whole-show cache.

Keep detailed dog-show operations and tuning guidance in `../docs/dog-show-browser.md`; keep this section as the backend quick reference.
