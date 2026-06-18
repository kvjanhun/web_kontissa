# [erez.ac](https://erez.ac)

Personal portfolio website by Konsta Janhunen.

## Stack

- **Frontend**: Nuxt 3 (Vue 3, Composition API) + Tailwind CSS 4
- **Backend**: Flask (Python) with JSON API endpoints
- **Database**: SQLite via Flask-SQLAlchemy
- **Auth**: Flask-Login with session cookies, scrypt password hashing
- **State**: Pinia stores via `@pinia/nuxt`
- **Server**: Gunicorn (production), Flask dev server (local)
- **Deployment**: Docker Compose (multi-stage build), auto-deployed via GitHub webhook
- **CI**: GitHub Actions — pytest, Vitest, Playwright on every push

## Features

- Nuxt 3 with static site generation (`nuxt generate`) and file-based routing
- Dark/light mode with warm stone-orange theme
- EN/FI language support via custom Pinia i18n store
- Interactive terminal animation on the home page (cowsay, weather, etc.)
- Admin panel for managing content sections (tab-based dashboard)
- Shared recipe book with search, categories, cooking mode with wake lock (for logged in users only)
- [Dog show browser](https://erez.ac/dog) — Showlink show and result browser with server-side crawling and persistent result caches
- Real-time weather from the Finnish Meteorological Institute (FMI) API
- Accessibility: skip links, ARIA attributes, focus indicators, reduced-motion support

## Documentation
Here's some documentation on the parts of the stack that are not available for non-authenticated visitors or which are actually used server-side.
### Feature and operations docs
These docs cover stateful features, server-side integrations, and operational tooling that are not obvious from the public static pages.

- [Dog show browser](./frontend/features/dog/README.md) — Human overview of the `/dog` frontend.
- [Dog show browser operations](./docs/dog-show-browser.md) — Showlink crawling, caching, whole-show filtering, and operations.
- [Observability stack](./server/observability) - Live logging with Grafana, Loki, Alloy, Prometheus.

### Server configuration
Documented [here](./server). Running on a small mini-PC.

## Background

The site was originally built with Flask + Jinja2 templates and vanilla JavaScript. In February 2026, the frontend was migrated to Vue 3 SFCs with Vite, the Jinja2 templates replaced by Vue components, and Flask routes converted to a JSON API. In March 2026, the frontend was migrated from Vite + vite-ssg to Nuxt 3 with Pinia for state management.

## Running Locally

### With Docker

```bash
docker compose up --build -d
```

Then visit: [http://localhost:8080](http://localhost:8080)

### Without Docker (development)

```bash
# Install once
npm run setup

# Start Flask + Nuxt
npm run dev
```

Then visit: [http://localhost:3000](http://localhost:3000)

The root dev scripts are:

```bash
npm run setup         # Create .venv and install backend/frontend dev deps
npm run dev           # Flask API + Nuxt dev server
npm run dev:backend   # Flask API only, http://127.0.0.1:5001
npm run dev:frontend  # Nuxt only, http://localhost:3000
```

The backend setup/dev launchers prefer `.venv/bin/python`, then `python3.14`, then `python3.13`, then `python3`. They refuse to use a Python that cannot verify Werkzeug `scrypt` password hashes, which avoids local login failures caused by Apple Python builds linked against LibreSSL.

Nuxt proxies `/api/*` requests to Flask on port 5001 via `routeRules` in `nuxt.config.ts`.

### Running tests

```bash
pytest tests/                         # Backend (in-memory SQLite)
cd frontend && npm run test           # Vitest unit tests

# E2E uses its own DB at app/data/test-e2e.db — independent of dev site.db.
python3 scripts/seed_e2e.py           # Seed users, sections, and recipes
cd frontend && npm run test:e2e       # Playwright starts Flask (:5001, test-e2e.db) + Nuxt preview (:3000)
```

Playwright locally reuses any server already on :5001 — stop the dev Flask first (or run with `CI=1`), otherwise DB-backed specs pick up the wrong database and fail.

## Configuration

A `.env` file is required with at least `SECRET_KEY` for session signing. The SQLite database lives at `/app/data/site.db` (container path). For local development, set `DATABASE_URI` to point to a database on local drive.

To create or reset a local user:

```bash
npm run user:create -- konsta konsta@example.com --role admin
npm run user:reset -- konsta@example.com
```

Both commands use the local dev database by default (`app/data/site.db`) and prompt for the password.

To create an admin user in production:
```bash
docker compose exec web python3 -m app.create_user create username email@example.com --role admin
```

Or reset a production user password:
```bash
docker compose exec web python3 -m app.create_user reset-password email@example.com
```

## Production Notes

- Multi-stage Docker build: Node builds the frontend (`nuxt generate`), final image is Python-only
- Gunicorn as WSGI server, Nginx + Let's Encrypt for TLS termination (external)
- Auto-deploy via GitHub Actions + webhook — pushes to main go live if test suite passes.
- Litestream sidecar container continuously replicates `site.db` to Backblaze B2 (`erezac-db-backup`, `eu-central-003`). It also backs up the separate Sanakenno database from `~/Projects/sanakenno/server/data`. Config: `server/observability/litestream.yml`. Credentials (`B2_KEY_ID`, `B2_APP_KEY`) in `.env` on the NUC.

## Author

Konsta Janhunen
[erez.ac](https://erez.ac)
