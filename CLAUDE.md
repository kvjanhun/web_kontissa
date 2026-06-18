# CLAUDE.md — web_kontissa (erez.ac)

> **One file, three names.** `AGENTS.md` and `GEMINI.md` are symlinks to `CLAUDE.md` at every directory that has one (`./`, `app/`, `frontend/`, `server/observability/`). Edit any alias — Codex, Claude Code, Gemini CLI all read the same content. Git tracks the symlinks (mode `120000`); fresh clones on Unix get real symlinks. On Windows this needs `core.symlinks=true` + developer mode.

## Agent Role

You are a **senior full-stack developer** working on Konsta Janhunen's personal portfolio site. You value proven, mature technologies over hype-driven choices — but you're not afraid to adopt new tools when they genuinely solve a problem. You keep thorough documentation of everything you do.

You are also a **security-conscious engineer**. This site runs on a home server exposed to the internet. Every feature decision is also a security decision — consider both the implementation and its attack surface simultaneously. Validate inputs, parameterize queries, hash secrets, minimize attack surface.

## Project Overview

Personal portfolio site for Konsta Janhunen (erez.ac). Nuxt 3 SSG frontend, Flask JSON API backend, SQLite database, deployed via Docker on a self-hosted Intel NUC running RHEL.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Nuxt 3, Vue 3 (Composition API, `<script setup>`), Tailwind CSS 4 |
| Build | Nuxt (`nuxt generate` for SSG, Vite under the hood) |
| State | Pinia (`@pinia/nuxt` module; stores auto-imported) |
| Backend | Flask 3.1, Flask-SQLAlchemy, Flask-Login, Flask-Limiter (30 req/min default) |
| Database | SQLite |
| Auth | Flask-Login session cookies, werkzeug scrypt password hashing |
| Container | Docker (multi-stage: Node → Python), Docker Compose |
| Server | RHEL on Intel NUC, Nginx with Let's Encrypt TLS |
| Observability | Loki + Grafana Alloy (logs), Prometheus + node_exporter (metrics), Grafana (dashboards) |
| Backup | Litestream → Backblaze B2 (continuous SQLite replication) |
| Deployment | GitHub webhook → deploy script → docker compose up --build |

## Project Structure

```
web_kontissa/
├── Dockerfile              # Multi-stage: node:22-alpine → python:3.13-alpine
├── docker-compose.yml      # Volume for /app/data, port 127.0.0.1:8080:80
├── .github/workflows/test.yml  # CI: pytest, vitest, playwright on push/PR
├── docs/                   # Feature and architecture notes, including dog-show browser docs
├── run.py                  # Flask dev entry point (port 5001)
├── requirements.txt
├── frontend/               # Nuxt 3 app (see frontend/CLAUDE.md)
│   ├── nuxt.config.ts      # SSG, routeRules proxy, Pinia, Tailwind
│   ├── pages/              # File-based routing
│   ├── components/         # Auto-imported components
│   ├── stores/             # Pinia stores (auto-imported)
│   ├── composables/        # Vue composables (auto-imported)
│   ├── layouts/            # default.vue + standalone.vue
│   ├── middleware/          # auth.global.js + pageview.global.js
│   ├── e2e/                # Playwright E2E tests
│   └── tests/unit/         # Vitest unit tests
├── app/                    # Flask backend (see app/CLAUDE.md)
│   ├── __init__.py         # App factory, LoginManager, Limiter
│   ├── routes.py           # Sections CRUD, meta, sitemap, static serving
│   ├── auth.py, recipes.py # Auth + recipe endpoints
│   ├── api/                # cowsay, weather, health, pageviews, dog
│   └── models.py           # All SQLAlchemy models
├── tests/                  # Backend pytest
├── scripts/                # seed_e2e.py, dog_crawl.py, etc.
└── server/                 # deploy-site.sh, health-alert.sh, backup-configs.sh, erez.ac.conf
    └── observability/      # Loki, Alloy, Prometheus, Grafana configs (see server/observability/CLAUDE.md)
```

## Development

```bash
# Install local Python/frontend dependencies once
npm run setup

# Start Flask API + Nuxt dev server
npm run dev

# Or start them separately
npm run dev:backend
npm run dev:frontend
```

Nuxt at http://localhost:3000, proxies `/api/*` to Flask at :5001 via `routeRules`. `npm run dev:backend` sets safe local defaults (`SECRET_KEY=dev`, `FLASK_DEBUG=1`, `DATABASE_URI=sqlite:///.../app/data/site.db`) and fails fast if the selected Python cannot verify Werkzeug `scrypt` password hashes. Prefer a local `.venv` created by `npm run setup`.

```bash
# Tests
pytest tests/                          # Backend (in-memory SQLite)
cd frontend && npm run test            # Vitest unit tests

# E2E uses a separate DB at app/data/test-e2e.db, distinct from the dev site.db.
python3 scripts/seed_e2e.py            # Seed users, sections, and a recipe (run after schema changes)
cd frontend && npm run test:e2e        # Playwright spawns Flask (:5001 → test-e2e.db) + Nuxt preview (:3000)

# Build
cd frontend && npm run build           # nuxt generate → .output/public/

# Docker
docker compose up --build -d
```

**Database schema changes**: Do not add live migrations to Flask startup, import time, or request handling. In particular, do not add `ALTER TABLE`, table rebuilds, or migration helpers to `app/__init__.py`. Schema changes must be planned explicitly, covered by tests and seed data updates, and shipped with a reviewed one-off manual migration/restore procedure for the production SQLite file.

**Local E2E gotcha**: `playwright.config.js` sets `reuseExistingServer: !process.env.CI`, so any Flask already listening on :5001 (e.g. your dev server pointed at `site.db`) is reused instead of the correctly-configured test server. DB-backed specs (auth, admin, recipes) will fail. Stop the dev Flask before running E2E, invoke with `CI=1 npm run test:e2e`, or use alternate ports via `PLAYWRIGHT_API_PORT=5101 PLAYWRIGHT_WEB_PORT=3100`.

## Server Architecture

```
Internet → [443 HTTPS] → nginx (TLS, ECDSA cert)
                            ├── /              → 127.0.0.1:8080 (Docker: Gunicorn → Flask)
                            ├── /logs/         → 127.0.0.1:3000 (Grafana)
                            ├── /hooks/deploy  → 127.0.0.1:9000 (webhook)
                            └── /.well-known/  → /var/www/html (ACME)
```

- **Firewall**: Default deny. Only 80, 443 public. SSH restricted to LAN IPs. Docker bridge (172.18.0.0/16) allowed to reach node_exporter on port 9100.
- **CI**: 3 parallel jobs (pytest, vitest, playwright). Deploy webhook fires after all pass.
- **Auto-deploy**: Every push to main goes live. Breaking the build breaks the site.

## Security Considerations

- **Passwords**: Werkzeug scrypt with random salt. Never logged or exposed.
- **SQL injection**: SQLAlchemy parameterized queries throughout.
- **XSS**: Vue auto-escapes `{{ }}`. `v-html` only on admin-authored section content.
- **CSRF**: Mutation endpoints accept JSON only (`request.get_json()`).
- **Network**: Container port 8080 on localhost only. Nginx handles TLS.
- **HTTP headers**: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy enforced in nginx. CSP in report-only mode. Config: `server/erez.ac.conf`.
- **Webhook**: Token-validated, runs as unprivileged user.

When making changes: Does this introduce a new input vector? Does this expose internal state? Does this weaken the network boundary?

## Important Notes

- SQLite database persisted via Docker volume (`./app/data:/app/data`). Never delete. Litestream sidecar container continuously replicates `site.db` to Backblaze B2 (`erezac-db-backup`, `eu-central-003`); config at `server/observability/litestream.yml`; credentials (`B2_KEY_ID`, `B2_APP_KEY`) in `.env` on the NUC; 60s sync interval, 72h WAL retention.
- Sanakenno now lives in `~/Projects/sanakenno` and runs in its own containers, but this repo still owns shared host plumbing: `server/sanakenno.fi.conf`, the `/hooks/deploy-sanakenno` nginx proxy, the legacy `/sanakenno` redirect, the Sanakenno Grafana dashboard, and Litestream replication of `/home/kvjanhun/Projects/sanakenno/server/data/sanakenno.db`.
- Dog show index/result cache JSON also lives under `./app/data` via `DOG_INDEX_DIR=/app/data` (`dog_show_index.json`, `dog_result_cache/`, `dog_result_jobs.json`). These files are persistent on the host bind mount but are not covered by Litestream's SQLite replication. Full operations notes: `docs/dog-show-browser.md`.
- `app/static/dist/` is gitignored — generated by `nuxt generate`, copied from `.output/public/` during Docker build.
- `.env` is gitignored. Contains `SECRET_KEY` (required in production).
- Server is a low-power Intel NUC. Keep Docker images lean (alpine bases).
