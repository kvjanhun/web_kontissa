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
- [Sanakenno](https://erez.ac/sanakenno) — Finnish word game with a full admin panel. Inspired by [NYT Spelling Bee](https://www.nytimes.com/puzzles/spelling-bee)
- Real-time weather from the Finnish Meteorological Institute (FMI) API
- Accessibility: skip links, ARIA attributes, focus indicators, reduced-motion support

## Documentation
Here's some documentation on the parts of the stack that are not available for non-authenticated visitors or which are actually used server-side.
### Features for logged in users
The site has some features that are available only for logged in users. Some of the features are demonstrated below.

- [Sanakenno puzzle editor](./ADMIN_TOOLS.md) — Tool to create, modify and schedule Sanakenno puzzles.
- [Observability stack](./server/observability) - Live logging with Grafana, Loki, Promtail, Prometheus.

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
# Terminal 1 — Flask API
pip install -r requirements.txt
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 run.py

# Terminal 2 — Nuxt dev server with HMR
cd frontend && npm install && npm run dev
```

Then visit: [http://localhost:3000](http://localhost:3000)

Nuxt proxies `/api/*` requests to Flask on port 5001 via `routeRules` in `nuxt.config.ts`.

## Configuration

A `.env` file is required with at least `SECRET_KEY` for session signing. The SQLite database lives at `/app/data/site.db` (container path). For local development, set `DATABASE_URI` to point to a database on local drive.

To create an admin user (admin tools, recipes):
```bash
docker compose exec web python3 -c "from app.create_user import create; create('username', 'email', 'password', role='admin')"
```

Or a regular user (recipes only):
```bash
docker compose exec web python3 -c "from app.create_user import create; create('username', 'email', 'password', role='user')"
```

## Production Notes

- Multi-stage Docker build: Node builds the frontend (`nuxt generate`), final image is Python-only
- Gunicorn as WSGI server, Nginx + Let's Encrypt for TLS termination (external)
- Auto-deploy via GitHub Actions + webhook — pushes to main go live if test suite passes.
- Litestream sidecar container continuously replicates `site.db` to Backblaze B2 (`erezac-db-backup`, `eu-central-003`). Config: `server/observability/litestream.yml`. Credentials (`B2_KEY_ID`, `B2_APP_KEY`) in `.env` on the NUC.

## Author

Konsta Janhunen
[erez.ac](https://erez.ac)
