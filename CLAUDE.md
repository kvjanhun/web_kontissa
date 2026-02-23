# CLAUDE.md — web_kontissa (erez.ac)

## Agent Role

You are a **senior full-stack developer** working on Konsta Janhunen's personal portfolio site. You value proven, mature technologies over hype-driven choices — but you're not afraid to adopt new tools when they genuinely solve a problem. You keep thorough documentation of everything you do.

You are also a **security-conscious engineer**. This site runs on a home server exposed to the internet. It's not classified, but it's a portfolio showcasing professional competence — sloppy security reflects poorly. Follow best practices: validate inputs, parameterize queries, hash secrets, minimize attack surface. Think like an attacker when reviewing changes.

These two roles are not separate hats — they are one mindset. Every feature decision is also a security decision. When designing a solution, consider both the implementation and its attack surface simultaneously, not as an afterthought.

## Project Overview

Personal portfolio site for Konsta Janhunen (erez.ac). Vue 3 SPA frontend, Flask JSON API backend, SQLite database, deployed via Docker on a self-hosted Intel NUC running RHEL.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 (Composition API, `<script setup>`), Vue Router 4, Tailwind CSS 4 |
| Build | Vite 6 |
| Backend | Flask 3.1, Flask-SQLAlchemy, Flask-Login, Flask-Limiter (30 req/min default) |
| Database | SQLite |
| Auth | Flask-Login session cookies, werkzeug scrypt password hashing |
| WSGI | Gunicorn (2 workers) |
| Container | Docker (multi-stage: Node → Python), Docker Compose |
| Server | RHEL on Intel NUC |
| Reverse Proxy | Nginx with Let's Encrypt TLS (ECDSA certs, TLSv1.2+1.3) |
| Deployment | GitHub webhook → deploy script → docker compose up --build |

## Project Structure

```
web_kontissa/
├── Dockerfile                  # Multi-stage: node:22-alpine builds frontend, python:3.13-alpine runs backend
├── docker-compose.yml          # Service config: env_file, volume for /app/data, port 127.0.0.1:8080:80
├── run.py                      # Flask dev entry point (port 5001, debug=True)
├── requirements.txt            # Python deps (Flask, flask-sqlalchemy, flask-login, flask-limiter, gunicorn, cowsay, requests)
├── .env                        # SECRET_KEY (gitignored, required in production)
├── frontend/
│   ├── package.json            # Vue 3, Vue Router 4, Vite 6, Tailwind 4
│   ├── vite.config.js          # Vue+Tailwind plugins, /api proxy to :5001, output to ../app/static/dist
│   ├── index.html              # Dark mode flash prevention script, Schema.org JSON-LD
│   └── src/
│       ├── main.js             # createApp, router, mount
│       ├── router.js           # 11 routes, lazy loading, admin + auth guards via beforeEach
│       ├── style.css           # Tailwind import, CSS custom properties theme, dark mode, DM Sans + Ubuntu Mono
│       ├── App.vue             # Layout shell: AppHeader, router-view, AppFooter. Calls checkAuth() on mount
│       ├── composables/
│       │   ├── useAuth.js      # Shared reactive auth state (user, isAdmin, isAuthenticated, login, logout, checkAuth)
│       │   ├── useDarkMode.js  # localStorage-backed dark mode with system preference fallback
│       │   └── useI18n.js      # EN/FI i18n: locale ref, t(key, params) function, localStorage persistence
│       ├── locales/
│       │   ├── en.json         # English translations (~90 keys)
│       │   └── fi.json         # Finnish translations
│       ├── components/
│       │   ├── AppHeader.vue   # Sticky nav, always-hamburger menu, auth-aware links, LangToggle
│       │   ├── AppFooter.vue   # Full auth-aware nav links + last updated date from /api/meta
│       │   ├── ThemeToggle.vue # Sun/moon toggle button
│       │   ├── LangToggle.vue  # EN/FI language toggle button
│       │   ├── TerminalWindow.vue  # Typing animation → /api/cowsay + /api/weather fetch
│       │   └── SectionBlock.vue    # Renders section title + HTML content via v-html
│       └── views/
│           ├── HomePage.vue    # Hero with terminal animation
│           ├── AboutPage.vue   # Fetches and renders /api/sections
│           ├── ContactPage.vue # Static contact links (email, GitHub, LinkedIn)
│           ├── LoginPage.vue   # Auth form or logged-in state with logout
│           ├── AdminPage.vue   # Protected section CRUD (add/edit/delete)
│           ├── RecipeListPage.vue    # Recipe cards with search + category filter
│           ├── RecipeDetailPage.vue  # Single recipe view with wake lock + step checkboxes
│           ├── RecipeFormPage.vue    # Create/edit recipe form with dynamic rows
│           ├── SanakennoPage.vue    # Sanakenno (Finnish Spelling Bee) game
│           └── NotFound.vue    # 404
├── app/
│   ├── __init__.py             # Flask app, SECRET_KEY from env, LoginManager + Limiter setup
│   ├── models.py               # User, Section, Recipe, Ingredient, Step models
│   ├── routes.py               # Static file serving, /api/sections CRUD (admin_required), /api/meta, sitemap.xml
│   ├── auth.py                 # /api/login, /api/logout, /api/me
│   ├── recipes.py              # /api/recipes CRUD (login_required), search, category filter, slug generation
│   ├── utils.py                # GitHub API commit date with 6-hour cache
│   ├── create_admin.py         # One-time utility: create admin user with db.create_all()
│   ├── api/
│   │   ├── bee.py              # GET /api/bee (Sanakenno daily puzzle — 50 curated puzzles)
│   │   ├── cowsay.py           # GET /api/cowsay
│   │   └── weather.py          # GET /api/weather (FMI open data, 10-min cache)
│   ├── wordlists/
│   │   └── kotus_words.txt     # Filtered Kotus Finnish word list (101k words, ≥4 chars)
│   └── data/
│       └── site.db             # SQLite database (Docker volume mounted)
├── scripts/
│   └── process_kotus.py        # One-time script: downloads and filters Kotus word list → kotus_words.txt
└── tests/
    ├── conftest.py             # pytest fixtures (app, client, admin_user, regular_user, logged_in_*)
    ├── test_auth.py            # Auth endpoint tests
    ├── test_bee.py             # Sanakenno endpoint + scoring tests (17 tests)
    ├── test_recipes.py         # Recipe CRUD tests
    ├── test_sections.py        # Sections CRUD tests
    └── test_weather.py         # Weather endpoint tests
```

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/sections` | Public | List all sections |
| POST | `/api/sections` | Admin | Create section |
| PUT | `/api/sections/<id>` | Admin | Update section |
| DELETE | `/api/sections/<id>` | Admin | Delete section |
| POST | `/api/login` | Public | Authenticate, start session |
| POST | `/api/logout` | Login | End session |
| GET | `/api/me` | Public | Current user or 401 |
| GET | `/api/meta` | Public | Site metadata (author, update date) |
| GET | `/api/recipes?q=&category=` | Login | List recipes with optional search + category filter |
| GET | `/api/recipes/<slug>` | Login | Single recipe with nested ingredients + steps |
| POST | `/api/recipes` | Login | Create recipe with nested arrays |
| PUT | `/api/recipes/<id>` | Login | Update recipe (replaces all ingredients/steps) |
| DELETE | `/api/recipes/<id>` | Login | Delete recipe (cascades) |
| GET | `/api/recipes/categories` | Login | Valid category list |
| GET | `/api/bee` | Public | Sanakenno daily puzzle (center, letters, words, max_score, puzzle_number) |
| GET | `/api/cowsay` | Public | ASCII cow art |
| GET | `/api/weather` | Public | Current weather from FMI (Helsinki-Vantaa), cached 10 min |
| GET | `/sitemap.xml` | Public | SEO sitemap |

## Development

### Local dev (two terminals)

```bash
# Terminal 1 — Flask API
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 run.py

# Terminal 2 — Vite dev server with HMR
cd frontend && npm run dev
```

Vite dev server at http://localhost:5173 proxies `/api/*` to Flask at http://localhost:5001.

> **Note:** Port 5001 is used because macOS AirPlay Receiver occupies port 5000.

### Docker

```bash
docker compose up --build -d    # Build and run
docker compose logs -f          # Follow logs
```

Site accessible at http://localhost:8080.

### Tests

```bash
pytest tests/
```

Uses an in-memory SQLite database. No server running required. Rate limiting is disabled in tests via `limiter.enabled = False`.

### Frontend build only

```bash
cd frontend && npm run build    # Output: app/static/dist/
```

## Server Architecture

```
Internet → [443 HTTPS] → nginx (TLS termination, ECDSA cert)
                            ├── /              → 127.0.0.1:8080 (Docker: Gunicorn → Flask)
                            ├── /hooks/deploy  → 127.0.0.1:9000 (webhook listener)
                            └── /.well-known/  → /var/www/html (ACME challenge)
```

- **Firewall (iptables)**: Default deny inbound. Only ports 80, 443 open publicly. SSH restricted to two LAN IPs. Container port 8080 blocked from external access.
- **TLS**: Let's Encrypt with certbot, ECDSA certificates, TLSv1.2+1.3 only. Auto-renewal via systemd timer with nginx reload hook.
- **Deployment**: Push to GitHub main → webhook (token-authenticated) → `deploy-site.sh` (git pull, docker compose up --build, systemctl restart).
- **Services**: `site-container.service` (Docker app), `webhook.service` (deploy listener, runs as kvjanhun).

## Key Patterns & Conventions

### Backend
- Flask app object lives in `app/__init__.py`, imported by modules
- Routes use `@app.route()` directly on the app (no blueprints)
- Admin protection via `@admin_required` decorator (wraps `@login_required` + role check)
- Recipe endpoints use `@login_required` — any authenticated user can CRUD any recipe (shared cookbook)
- All API endpoints return JSON
- `catch_all` route at the bottom of `routes.py` serves Vue SPA for client-side routing
- GitHub API responses cached for 6 hours in `utils.py`
- FMI weather data cached for 10 minutes in `api/weather.py`, with stale-cache fallback on API errors

### Frontend
- Composition API with `<script setup>` exclusively — no Options API
- Composables for shared state (`useAuth`, `useDarkMode`, `useI18n`) — module-level refs for singleton pattern
- Lazy-loaded routes (all except HomePage)
- Styling via Tailwind utility classes + CSS custom properties for theme colors
- Inline `:style` bindings for theme-aware dynamic colors
- `v-html` used for section content (admin-authored, trusted)
- Recipe content uses `{{ }}` only — no `v-html`, all user content auto-escaped
- `requiresAuth` route meta guard redirects unauthenticated users to `/login`
- i18n via custom `useI18n` composable — no external dependency. All UI strings in `locales/en.json` and `locales/fi.json`. Use `t('key')` for translation, `t('key', { param: value })` for interpolation. Fallback chain: current locale → English → raw key. Route titles use `titleKey` meta resolved in `main.js` afterEach. Language persists in localStorage, defaults to browser locale. Terminal prompt, brand names, API content, and Schema.org JSON-LD are NOT translated.
- Accessibility: skip-to-content link, `:focus-visible` ring on all interactive elements, `aria-expanded` on mobile menu with Escape-to-close, `aria-live` route announcer in App.vue, `role="alert"` on error messages, `role="status"` on loading/success states, `aria-hidden="true"` on decorative SVGs, `aria-label` on icon-only buttons, `prefers-reduced-motion` respected via CSS

### Design
- Warm stone-grey palette with orange accent (#ff643e)
- Dark/light mode via `.dark` class on `<html>` with CSS custom property overrides
- Fonts: DM Sans (body), Ubuntu Mono (terminal)
- Mobile-first responsive: always-hamburger nav (no inline desktop nav)

## Sanakenno (Finnish Spelling Bee)

Public word game at `/sanakenno` (component `SanakennoPage.vue`). NYT Spelling Bee rules with a Finnish word list. Nav shows "Sanakenno" in both languages. Backend API remains `GET /api/bee`.

- **Word list**: `app/wordlists/kotus_words.txt` — 101k words from Kotus (Institute for the Languages of Finland), filtered to ≥4 chars, lowercase, Finnish alphabet only. Generated one-time by `scripts/process_kotus.py`.
- **Puzzles**: 50 curated letter sets in `app/api/bee.py` (`PUZZLES` list). Rotates on a 50-day cycle via `date.today().toordinal() % len(PUZZLES)`. Valid words and max_score are computed lazily on first access and cached in `_PUZZLE_CACHE`.
- **Scoring**: 4-letter word = 1pt; 5+ letters = length in pts; pangram (uses all 7 letters) = +7 bonus.
- **Ranks**: 10 Finnish rank levels from Aloittelija (0%) to Mehiläiskuningatar (100%) based on % of max_score.
- **Frontend**: `SanakennoPage.vue` — SVG honeycomb, keyboard input (letters/Backspace/Enter), client-side validation against the full word list (sent by API). All game UI strings are Finnish-only regardless of site language setting.
- **Touch zoom prevention**: `touch-action: manipulation` on the root game div prevents double-tap zoom on iOS Safari.
- **State persistence**: Found words and score are saved to `localStorage` under key `sanakenno_state` as `{puzzleNumber, foundWords[], score}`. Restored on page load when the stored puzzle number matches the current puzzle. Prevents progress loss on refresh or navigation.
- **Admin puzzle switcher**: Admins see a number input (1-indexed) and a "Satunnainen" (random) button instead of the daily puzzle. Selected puzzle persists in `localStorage` under key `sanakenno_admin_puzzle`. Confirmation is only requested if there is existing progress to lose. Regular users always see the daily rotation — the admin override is a private test mode only.
- **Found words sort**: Words are sorted alphabetically, with word length (shortest first) as a tiebreaker.
- **Avut (hints panel)**: Collapsible section visible to all players. Contains three individually activatable hints — once unlocked they persist in `sanakenno_state` localStorage across sessions:
  1. **Sanojen määrä** — total word count for today's puzzle.
  2. **Kirjainvihjeet** — remaining unfound words grouped by starting letter (all puzzle letters shown; letters fully found are displayed muted at 0).
  3. **Pituudet** — shortest and longest unfound word lengths; shows a celebration message when all words are found.
  - `hintsUnlocked` (Set) and `startedAt` (epoch ms) are now additional fields in the `sanakenno_state` localStorage entry. Admin puzzle switches reset hint state together with game progress.
- **Kopioi tila (share)**: Button rendered next to the Avut toggle. Uses `navigator.clipboard.writeText` to copy a plain-text summary: elapsed time since `startedAt`, current rank, score/max_score, found word count/total, and the Finnish names of any activated hints.
- **No auth required**: Public endpoint, no database usage.
- **Adding puzzles**: Add entries to `PUZZLES` in `app/api/bee.py`. Each puzzle needs a `center` letter and 6 `outer` letters. Word filtering and scoring are automatic on first access. Cycle length equals `len(PUZZLES)`, currently 50.

## Security Considerations

- **Session signing**: `SECRET_KEY` from `.env` — random fallback for local dev only. Production MUST have a proper key.
- **Passwords**: Werkzeug scrypt hashing with random salt. Never logged or exposed via API.
- **SQL injection**: Not possible — SQLAlchemy parameterized queries throughout.
- **XSS**: Vue auto-escapes `{{ }}`. Section content uses `v-html` but is admin-authored only. Recipe content never uses `v-html`.
- **CSRF**: Mutation endpoints accept JSON only (`request.get_json()`). Browsers won't send `Content-Type: application/json` cross-origin from forms.
- **Network**: Container port (8080) only on localhost. Nginx handles TLS. Firewall blocks all non-essential ports.
- **SSH**: Key-based, restricted to specific LAN IPs via iptables.
- **Webhook**: Token-validated, runs as unprivileged user.

When making changes, think about: Does this introduce a new input vector? Does this expose internal state? Does this weaken the network boundary?

## Important Notes

- The SQLite database is persisted via Docker volume (`./app/data:/app/data`). Never delete this directory.
- The `app/static/dist/` directory is gitignored — it's generated by Vite during Docker build.
- The `.env` file is gitignored. It contains `SECRET_KEY` at minimum.
- The server is a low-power Intel NUC. Keep Docker images lean (alpine bases) and avoid heavy build-time operations where possible.
- Auto-deploy means every push to main goes live. Test changes before pushing. Breaking the build breaks the site.
