# [erez.ac](https://erez.ac)

Personal portfolio website by Konsta Janhunen.

## Stack

- **Frontend**: Vue 3 (Composition API, `<script setup>`) + Vite + Tailwind CSS 4
- **Backend**: Flask (Python) with JSON API endpoints
- **Database**: SQLite via Flask-SQLAlchemy
- **Auth**: Flask-Login with session cookies, scrypt password hashing
- **Server**: Gunicorn (production), Flask dev server (local)
- **Deployment**: Docker Compose (multi-stage build), auto-deployed via GitHub webhook

## Features

- Multi-page Vue SPA with client-side routing and static site generation (vite-ssg)
- Dark/light mode with warm stone-orange theme
- EN/FI language support via custom i18n composable
- Interactive terminal animation on the home page (cowsay, weather, etc.)
- Admin panel for managing content sections (tab-based dashboard)
- Shared recipe book with search, categories, cooking mode with wake lock
- [Sanakenno](https://erez.ac/sanakenno) — Finnish Spelling Bee word game with admin-managed puzzle rotation
- Real-time weather from the Finnish Meteorological Institute (FMI) API
- Accessibility: skip links, ARIA attributes, focus indicators, reduced-motion support

## Documentation

- [ADMIN_TOOLS.md](./ADMIN_TOOLS.md) — Admin dashboard guide: Kennotyökalu puzzle editor (with screenshot), Sanakenno stats, and security notes

## Background

Originally built with Flask + Jinja2 templates and vanilla JavaScript. In February 2026, the frontend was migrated to Vue 3 SFCs with Vite, the Jinja2 templates replaced by Vue components, and Flask routes converted to a JSON API. The site has since grown to include recipes, Sanakenno, i18n, and SSG — all developed with Claude (Anthropic), orchestrated by Konsta.

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

# Terminal 2 — Vite dev server with HMR
cd frontend && npm install && npm run dev
```

Then visit: [http://localhost:5173](http://localhost:5173)

Vite proxies `/api/*` requests to Flask on port 5001.

## Configuration

A `.env` file is required with at least `SECRET_KEY` for session signing. The SQLite database lives at `/app/data/site.db` (container path). For local development, set `DATABASE_URI` to point to the local database.

To create an admin user:
```bash
docker compose exec web python3 -c "from app.create_admin import create; create('username', 'email', 'password', 'admin')"
```

## Production Notes

- Multi-stage Docker build: Node builds the frontend, final image is Python-only
- Gunicorn as WSGI server, Nginx + Let's Encrypt for TLS termination (external)
- Auto-deploy via GitHub webhook — pushes to main go live immediately

## Author

Konsta Janhunen
[erez.ac](https://erez.ac)
