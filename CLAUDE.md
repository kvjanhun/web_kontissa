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
├── docs/                   # architecture.md (app + auth diagrams), dog-show-browser.md, home-content-migration.md
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
│   ├── routes.py           # meta, sitemap, static serving (catch-all)
│   ├── auth.py, recipes.py # Auth + recipe endpoints
│   ├── home_content.py     # DB-backed home content: /api/home-content + admin home-content/projects
│   ├── api/                # cowsay, weather, health, pageviews, dog
│   └── models.py           # All SQLAlchemy models
├── tests/                  # Backend pytest
├── scripts/                # seed_e2e.py, seed_home_content.py, export_home_content.py, dog_crawl.py, prune_pageview_events.py, etc.
└── server/                 # deploy-site.sh (app deploy) + observability/
    └── observability/      # Loki, Alloy, Prometheus, Grafana, Litestream configs (see server/observability/CLAUDE.md)
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

**Database schema changes**: Never run a schema change from Flask startup, import time, or request handling. In particular, do not add `ALTER TABLE`, table rebuilds, or schema probes to `app/__init__.py` — it may create empty tables for fresh databases and nothing more. A schema change is planned explicitly, covered by tests and seed data updates, and applied to the production SQLite file by hand after review, with a backup taken first. The `schema-change` skill carries the procedure.

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
- **XSS**: Vue auto-escapes `{{ }}`. DB-backed home content (text blocks + projects) renders through `{{ }}`/`tm()`, never `v-html`.
- **CSRF**: Mutation endpoints accept JSON only (`request.get_json()`).
- **Network**: Container port 8080 on localhost only. Nginx handles TLS.
- **Proxy trust / rate limiting**: Flask sits behind exactly one trusted proxy (nginx), so `app.wsgi_app` is wrapped in `ProxyFix(x_for=1, x_proto=1)` in `app/__init__.py`. Without it `request.remote_addr` is the Docker bridge gateway and Flask-Limiter buckets every visitor together. nginx overwrites `X-Forwarded-For` with `$proxy_add_x_forwarded_for`, so the single rightmost hop is the real client and is not client-spoofable.
- **HTTP headers**: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy enforced in nginx (`~/Projects/nuc/nginx/erez.ac.conf`). The Content-Security-Policy is **enforcing** (`Content-Security-Policy`, not Report-Only). Its value is chosen per-path by the `$content_security_policy` map: the public app/admin/`/dog` get a strict policy whose `script-src` is `'self' 'unsafe-inline'` (no eval; `'unsafe-inline'` covers Nuxt's inline `window.__NUXT__` payload + Tailwind), while `/logs` (Grafana) gets its own value adding `'unsafe-eval'` (+ `blob:` for workers/styles) because bundled Grafana drilldown plugins call `eval` at init. The map keeps all `add_header` directives at the server level so the other security headers keep inheriting into every location (nginx drops the whole inherited set from any location with its own `add_header`).
- **Webhook**: Token-validated, runs as unprivileged user.
- **Intrusion response**: host fail2ban service bans scanners / auth-brute-force / 429 abusers (across both vhosts) in the iptables `INPUT` chain and reports them to AbuseIPDB; a daily cron consumes AbuseIPDB's blocklist into an ipset for pre-emptive drops. Bans surface in Grafana (no Telegram). Config + runbook: `~/Projects/nuc/fail2ban/` and `~/Projects/nuc/scripts/abuseipdb-blocklist.sh`.

When making changes: Does this introduce a new input vector? Does this expose internal state? Does this weaken the network boundary?

## Important Notes

- SQLite database persisted via Docker volume (`./app/data:/app/data`). Never delete. Litestream sidecar container continuously replicates `site.db` to Backblaze B2 (`erezac-db-backup`, `eu-central-003`); config at `server/observability/litestream.yml`; credentials (`B2_KEY_ID`, `B2_APP_KEY`) in `.env` on the NUC; 60s sync interval, 72h WAL retention.
- **Three repos share this machine.** `~/Projects/nuc` owns host configuration (nginx vhosts for both domains, fail2ban, the deploy webhook, systemd units, cron jobs, and the health monitor covering both sites) — its README is the map of what runs where. `~/Projects/sanakenno` owns sanakenno.fi. This repo owns erez.ac, plus two things that are host-level in spirit but still wired here: the Sanakenno Grafana dashboard and Litestream replication of `/home/kvjanhun/Projects/sanakenno/server/data/sanakenno.db`, both because the observability containers are defined in this repo's `docker-compose.yml`. That seam is documented in `~/Projects/nuc/README.md`.
- Dog show data lives in its own SQLite database, `dog.db` (the `/dog`-only persistent store), under `./app/data` via `DOG_DATABASE_URI` (defaults to `dog.db` inside `DOG_INDEX_DIR=/app/data`). Separate from `site.db`, its own standalone SQLAlchemy engine, and **not** covered by Litestream replication (Konsta backs it up manually). It is a permanent database, not a cache: historical rows are never evicted, and every Showlink-reachable show's results are already captured. Full operations notes: `docs/dog-show-browser.md`.
- `app/static/dist/` is gitignored — generated by `nuxt generate`, copied from `.output/public/` during Docker build.
- `.env` is gitignored. Contains `SECRET_KEY` (required in production).
- Server is a low-power Intel NUC. Keep Docker images lean (alpine bases).

## Documentation Upkeep

**Every fact lives in exactly one file. Link to it; never copy it.** Duplicated
facts drift apart — each file has one job:

| File | Owns |
| --- | --- |
| `CLAUDE.md` (= `AGENTS.md`, `GEMINI.md`) | How to work here: stack, commands, gates, security rules, conventions |
| `docs/architecture.md` | How this app fits together: request lifecycle and auth diagrams |
| `docs/dog-show-browser.md` | The `/dog` subsystem end to end |
| `server/README.md` | Deploying this app, and database backup/restore |
| `server/observability/CLAUDE.md` | The observability stack's own rules |
| `plans/` | Design plans for work not yet done (dated; delete once shipped) |
| `~/Projects/nuc/README.md` | **Host-level architecture** — nginx, firewall, webhook, cron, who owns what on the machine |

Before finishing a change, update the **one** file that owns each changed fact.
If a fact is host-level rather than app-level, it belongs in the `nuc` repo,
not here.

### Documentation is not a journal

**Docs state what is true now.** They are not a changelog, a migration diary,
or a record of what a previous version did. Git history is where change lives.

Never write:

- "used to", "no longer", "previously", "we moved", "this was renamed"
- rationale that only parses if you watched the change happen
- reassurances answering a question someone asked once ("note: this does not
  need X") — just state the requirement
- status narration ("now owns", "has since grown", "was left there on purpose")

Always keep:

- **rules with reasons**, when the reason constrains a future decision —
  "secrets go in an EnvironmentFile because unit files are copied into the
  backup" tells the next person what not to do
- warnings about traps that are still there

The test: **would this sentence make sense to someone who has never seen the
previous version of this file?** If not, delete it. If the history genuinely
matters, it belongs in the commit message that made the change.
