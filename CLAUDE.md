# CLAUDE.md — web_kontissa (erez.ac)

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
| Observability | Loki + Promtail (logs), Prometheus + node_exporter (metrics), Grafana (dashboards) |
| Deployment | GitHub webhook → deploy script → docker compose up --build |

## Project Structure

```
web_kontissa/
├── Dockerfile              # Multi-stage: node:22-alpine → python:3.13-alpine
├── docker-compose.yml      # Volume for /app/data, port 127.0.0.1:8080:80
├── .github/workflows/test.yml  # CI: pytest, vitest, playwright on push/PR
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
│   ├── e2e/                # Playwright E2E tests (28 tests)
│   └── tests/unit/         # Vitest unit tests (89 tests)
├── app/                    # Flask backend (see app/CLAUDE.md)
│   ├── __init__.py         # App factory, LoginManager, Limiter
│   ├── routes.py           # Sections CRUD, meta, sitemap, static serving
│   ├── auth.py, recipes.py # Auth + recipe endpoints
│   ├── api/                # kenno, cowsay, weather, health, pageviews
│   ├── models.py           # All SQLAlchemy models
│   └── wordlists/          # kotus_words.txt (101k Finnish words)
├── tests/                  # Backend pytest (297 tests)
├── scripts/                # seed_puzzles.py, seed_e2e.py, etc.
└── server/                 # deploy-site.sh, health-alert.sh
    └── observability/      # Loki, Promtail, Prometheus, Grafana configs (see server/observability/CLAUDE.md)
```

## Development

```bash
# Terminal 1 — Flask API
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 run.py

# Terminal 2 — Nuxt dev server
cd frontend && npm run dev
```

Nuxt at http://localhost:3000, proxies `/api/*` to Flask at :5001 via `routeRules`.

```bash
# Tests
pytest tests/                          # Backend (in-memory SQLite)
cd frontend && npm run test            # Vitest unit tests
cd frontend && npm run test:e2e        # Playwright E2E (auto-starts servers)

# Build
cd frontend && npm run build           # nuxt generate → .output/public/

# Docker
docker compose up --build -d
```

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
- **Webhook**: Token-validated, runs as unprivileged user.

When making changes: Does this introduce a new input vector? Does this expose internal state? Does this weaken the network boundary?

## Important Notes

- SQLite database persisted via Docker volume (`./app/data:/app/data`). Never delete.
- `app/static/dist/` is gitignored — generated by `nuxt generate`, copied from `.output/public/` during Docker build.
- `.env` is gitignored. Contains `SECRET_KEY` (required in production).
- Server is a low-power Intel NUC. Keep Docker images lean (alpine bases).
