# Backend — Flask

## Key Patterns

- Flask app in `app/__init__.py`, imported by all modules
- **Blueprints**: All routes use blueprints (`core_bp`, `auth_bp`, `recipes_bp`, `pageviews_bp`, etc.) registered in `__init__.py`. No URL prefixes — paths stay identical.
- **Auth**: `@admin_required` decorator in `app/decorators.py` (wraps `@login_required` + role check). Recipe endpoints use `@login_required` (shared cookbook — any user can CRUD).
- All API endpoints return JSON
- `catch_all` route serves static files from `dist/`, pre-rendered `index.html` per route, or `200.html` SPA fallback for client-side routing
- GitHub API responses cached 6 hours (`utils.py`). FMI weather cached 10 minutes with stale fallback (`api/weather.py`).

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
| GET | `/sitemap.xml` | Public | SEO sitemap |

## Models

`User`, `Section` (with `section_type`: text/pills/quote/currently/intro/project/git_stats/timeline), `Recipe`, `Ingredient`, `Step`, `PageView`, `PageViewEvent`
