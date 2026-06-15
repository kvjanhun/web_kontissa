# Backend — Flask

## Key Patterns

- Flask app in `app/__init__.py`, imported by all modules
- **Blueprints**: All routes use blueprints (`core_bp`, `auth_bp`, `recipes_bp`, `kenno_bp`, etc.) registered in `__init__.py`. No URL prefixes — paths stay identical.
- **Auth**: `@admin_required` decorator in `app/decorators.py` (wraps `@login_required` + role check). Recipe endpoints use `@login_required` (shared cookbook — any user can CRUD).
- All API endpoints return JSON
- `catch_all` route serves static files from `dist/`, pre-rendered `index.html` per route, or `200.html` SPA fallback for client-side routing
- GitHub API responses cached 6 hours (`utils.py`). FMI weather cached 10 minutes with stale fallback (`api/weather.py`).
- Showlink dog show data is scraped server-side (`api/dog.py`). Breed indexing runs from `scripts/dog_crawl.py` as a separate process, not from Flask/Gunicorn workers.

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
| GET | `/api/kenno` | Public | Daily puzzle (hashes, hint_data; admin also gets words) |
| POST | `/api/kenno/block` | Admin | Block a word |
| GET | `/api/kenno/blocked` | Admin | List blocked words |
| DELETE | `/api/kenno/block/<id>` | Admin | Unblock |
| GET | `/api/kenno/stats` | Admin | Puzzle stats |
| GET | `/api/kenno/variations` | Admin | 7 center-letter variations |
| POST | `/api/kenno/center` | Admin | Set center letter |
| POST | `/api/kenno/preview` | Admin | Preview variations for arbitrary letters |
| POST | `/api/kenno/puzzle` | Admin | Create/update puzzle slot |
| GET | `/api/kenno/schedule` | Admin | Upcoming rotation schedule |
| POST | `/api/kenno/puzzle/swap` | Admin | Swap two slots |
| DELETE | `/api/kenno/puzzle/<slot>` | Admin | Revert/remove slot |
| POST | `/api/kenno/achievement` | Public | Record rank achievement (session-deduped) |
| GET | `/api/kenno/achievements` | Admin | Daily achievement counts by rank |
| GET | `/api/kenno/combinations` | Admin | Browse bee_combinations (filterable, sortable, paginated) |
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

`User`, `Section` (with `section_type`: text/pills/quote/currently/intro/project/git_stats/timeline), `Recipe`, `Ingredient`, `Step`, `BlockedWord`, `KennoConfig`, `KennoPuzzle`, `KennoAchievement`, `KennoCombination`, `PageView`, `PageViewEvent`

## Dog Shows Backend (api/dog.py)

Public Showlink browser. `/api/dog/shows` fetches the current show list with a 30-minute cache. Show detail and breed result caches are short-lived for current/previous-month shows and effectively stable for old shows; `/api/dog/shows/<id>` serves `dog_show_index.json` directly when a persisted breed list exists. `scripts/dog_crawl.py --loop` owns persisted crawler state: `dog_show_index.json` for breed search and `dog_result_cache/<show_id>.json` for whole-show result filters. Missing `/all-results` caches are queued in `dog_result_jobs.json`; the API also starts one bounded immediate warmup per web worker so user-triggered caches do not wait for the crawler poll. In production the crawler checks queued result jobs every 30 seconds, auto-warms up to two result caches for shows from the last 7 days every 2 minutes, fetches result pages with 3 workers and 0.4s staggered starts, and keeps slower breed-index maintenance at 15 minutes. Docker sets `DOG_INDEX_DIR=/app/data` so web and crawler containers share the mounted data volume. The web process reloads the breed index when it changes and serves whole-show result caches directly from disk; individual breed result endpoints can reuse a complete whole-show cache.

Keep detailed dog-show operations and tuning guidance in `../docs/dog-show-browser.md`; keep this section as the backend quick reference.

## Sanakenno Backend (api/kenno.py)

Finnish Spelling Bee word game. Public endpoint, no auth for normal play.

- **Word list**: `wordlists/kotus_words.txt` — 101k words from Kotus, filtered ≥4 chars, lowercase, Finnish alphabet. Generated by `scripts/process_kotus.py`.
- **Puzzles**: Stored in `KennoPuzzle` table. Centers in `KennoConfig` (key `center_{idx}`). Total count = highest slot + 1.
- **Rotation**: Deterministic — `(START_INDEX + days_since_ROTATION_START) % total_puzzles`. `ROTATION_START = date(2026, 2, 24)`, `START_INDEX = 1`.
- **Cache**: Valid words and max_score computed lazily, cached in `_PUZZLE_CACHE`. Blocking a word clears cache.
- **Live-slot protection**: All mutating endpoints reject today's slot with 409.
- **Scoring**: 4-letter = 1pt; 5+ letters = length in pts; pangram = +7 bonus.
- **Ranks**: 7 levels (% of max_score): Etsi sanoja! (0%), Hyvä alku (2%), Nyt mennään! (10%), Onnistuja (20%), Sanavalmis (40%), Ällistyttävä (70%), Täysi kenno (100%).
- **Word hiding**: API sends SHA-256 hashes (`word_hashes`). Admin gets plaintext `words` array. Pre-computed `hint_data` powers hint panels without exposing words.
- **Achievement tracking**: `POST /api/kenno/achievement` — session-deduped via `session["achieved_ranks"]`. Stored in `KennoAchievement` model.
- **Seed**: `scripts/seed_puzzles.py` + `initial_puzzles.json` for fresh DB (41 initial puzzles).
