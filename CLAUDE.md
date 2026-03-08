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
| Build | Vite 6, vite-ssg (static site generation for SEO) |
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
├── docker-compose.yml          # Service config: env_file, volume for /app/data, port 127.0.0.1:8080:80, healthcheck on /api/meta every 30s
├── .github/
│   └── workflows/
│       └── test.yml            # CI: runs pytest + Playwright on push/PR to main; uploads playwright-report on failure
├── run.py                      # Flask dev entry point (port 5001, debug=True)
├── requirements.txt            # Python deps (Flask, flask-sqlalchemy, flask-login, flask-limiter, gunicorn, cowsay, requests)
├── ADMIN_TOOLS.md              # Admin tool documentation with screenshots (Kennotyökalu, Kenno Stats)
├── .env                        # SECRET_KEY (gitignored, required in production)
├── frontend/
│   ├── package.json            # Vue 3, Vue Router 4, Vite 6, Tailwind 4; devDeps include @playwright/test; scripts: test:e2e, test:e2e:ui
│   ├── playwright.config.js    # Playwright config: dual webServer (Flask :5001, Vite :5173), Chromium only
│   ├── e2e/
│   │   ├── fixtures/
│   │   │   └── auth.js         # Playwright fixtures: authenticatedPage (regular user), adminPage (admin user); login via form
│   │   ├── homepage.spec.js    # 3 tests: heading, nav links, title
│   │   ├── navigation.spec.js  # 3 tests: route transitions, auth redirects
│   │   ├── auth.spec.js        # 4 tests: form, invalid creds, login redirect, logout
│   │   ├── sanakenno.spec.js   # 7 tests: game load, keyboard input, hints, share, rules modal
│   │   ├── recipes.spec.js     # 4 tests: auth redirect, list, detail, new form
│   │   ├── admin.spec.js       # 5 tests: non-admin blocked, admin access, tabs, sections, tab switching
│   │   └── not-found.spec.js   # 2 tests: 404 page, home link
│   ├── vite.config.js          # Vue+Tailwind plugins, /api proxy to :5001, output to ../app/static/dist, ssgOptions for static pre-rendering
│   ├── index.html              # Dark mode flash prevention script, Schema.org JSON-LD
│   ├── public/
│   │   ├── favicon.ico             # Default site favicon
│   │   └── sanakenno-favicon.png   # 64x64 orange pointy-top hexagon PNG; swapped in by useFaviconSwap on /sanakenno
│   └── src/
│       ├── main.js             # ViteSSG entry: createApp with SSG, router guards, i18n title updates
│       ├── router.js           # 11 routes, lazy loading, admin + auth guards via beforeEach
│       ├── style.css           # Tailwind import, CSS custom properties theme, dark mode, DM Sans + Ubuntu Mono
│       ├── App.vue             # Layout shell: AppHeader, router-view, AppFooter. Calls checkAuth() on mount
│       ├── composables/
│       │   ├── useAuth.js      # Shared reactive auth state (user, isAdmin, isAuthenticated, login, logout, checkAuth)
│       │   ├── useDarkMode.js  # localStorage-backed dark mode with system preference fallback
│       │   ├── useFaviconSwap.js  # Swaps page favicon on mount (URL string), restores on unmount. Uses element replacement. Safari covered server-side via routes.py.
│       │   ├── useGameTimer.js    # Sanakenno elapsed-time tracking with pause/resume on tab visibility. Exposes startedAt, totalPausedMs, start(), getElapsedMs(), reset().
│       │   ├── useHintData.js     # Pure computed derivations for Sanakenno hint panels (letterMap, unfoundLengths, pangramStats, lengthDistribution, pairMap). Takes puzzle, foundWords, outerLetters, center refs.
│       │   ├── useI18n.js      # EN/FI i18n: locale ref, t(key, params) function, localStorage persistence
│       │   ├── useNavLinks.js  # Shared nav link list used by AppHeader and AppFooter
│       │   ├── usePageView.js  # trackPageView(path) — fire-and-forget POST /api/pageview
│       │   ├── useTerminal.js  # Interactive shell logic: boot sequence (skip on re-mount), command handlers, history navigation
│       │   └── useThemeColor.js   # Manages <meta name="theme-color"> and html background to match --color-bg-primary. Observes dark/light class changes via MutationObserver. Restores on unmount.
│       ├── locales/
│       │   ├── en.json         # English translations (~90 keys); includes admin.tab.kennotyokalu = "Kenno Tool"
│       │   └── fi.json         # Finnish translations; includes admin.tab.kennotyokalu = "Kennotyökalu"
│       ├── components/
│       │   ├── AppHeader.vue   # Sticky nav, always-hamburger menu, auth-aware links, LangToggle
│       │   ├── AppFooter.vue   # Full auth-aware nav links + last updated date from /api/meta
│       │   ├── ThemeToggle.vue # Sun/moon toggle button
│       │   ├── LangToggle.vue  # EN/FI language toggle button
│       │   ├── TerminalWindow.vue  # Interactive shell with boot sequence, commands: help, about, skills, fetch, weather, cowsay, cowthink, echo, date, clear; fuzzy "Did you mean:" suggestions via Levenshtein distance ≤ 2
│       │   ├── weatherIcons.js    # Inline SVG weather icons + wawaToIcon(code) mapper
│       │   ├── SectionBlock.vue    # Section renderer with 4 types: 'quote' (decorative centered blockquote, no card), 'currently' (card with accent-bordered label:value items), 'pills' (card with 3-col grid of flat accent-bordered items), 'text' (card with v-html content). All card types have orange accent bar under title.
│       │   └── admin/
│       │       ├── AdminSections.vue     # Sections CRUD + reorder (up/down arrows); type selector dropdown (Text/Pills/Quote/Currently) in create and edit forms; placeholder text is dynamic based on selected type
│       │       ├── AdminPageViews.vue    # Page views table with timestamps
│       │       ├── AdminRecipes.vue      # Recipe table with edit/delete
│       │       ├── AdminHealth.vue       # System health key-value display
│       │       ├── AdminKennoStats.vue     # Sanakenno stats (page views, blocked words, puzzles) + daily achievements table (7d/30d/90d period selector, all 7 rank columns, totals row)
│       │       ├── AdminKennoPuzzleTool.vue # Kennotyökalu tab: unified single-editor. Left column: scrollable all-puzzles slot list with dates + custom/today badges. Right column: compact toolbar (slot number, letters input, swap, delete/revert) + KennoVariationsGrid + KennoWordList. Clean state: view/switch center. Dirty state: preview letters → select center → save.
│       │       ├── AdminBlockedWords.vue # Blocked words table with unblock
│       │       ├── KennoVariationsGrid.vue # 7-column center letter selector grid. Props: variations, activeCenter, disabled, showTarget. Emits: select.
│       │       └── KennoWordList.vue    # Sorted multi-column word list with pangram highlighting (orange accent + semibold) and per-word block buttons. Props: words, letters, loading, error, emptyMessage. Emits: block.
│       └── views/
│           ├── HomePage.vue    # Hero with terminal animation
│           ├── AboutPage.vue   # Fetches and renders /api/sections; groups compact types (currently, pills) into side-by-side pairs on md+ screens; no h1 heading (quote section serves as intro)
│           ├── ContactPage.vue # Static contact links (email, GitHub, LinkedIn)
│           ├── LoginPage.vue   # Auth form or logged-in state with logout
│           ├── AdminPage.vue   # Protected admin dashboard, flat tab bar (Sections, Analytics, Recipes, Health, Sanakenno, Kennotyökalu) with lazy-mounted panels
│           ├── RecipeListPage.vue    # Recipe cards with search + category filter
│           ├── RecipeDetailPage.vue  # Single recipe view with wake lock + step checkboxes
│           ├── RecipeFormPage.vue    # Create/edit recipe form with dynamic rows
│           ├── SanakennoPage.vue    # Sanakenno (Finnish Spelling Bee) game. Title in top bar row alongside navigation. Sticky score/progress/hints-toggle/share row. Admin controls removed (puzzle switcher + center variations now in AdminKennoPuzzleTool.vue).
│           └── NotFound.vue    # 404
├── app/
│   ├── __init__.py             # Flask app, SECRET_KEY from env, LoginManager + Limiter setup
│   ├── models.py               # User, Section (with section_type), Recipe, Ingredient, Step, BlockedWord, KennoConfig, KennoPuzzle, KennoAchievement, PageView models
│   ├── routes.py               # Static file serving, /api/sections CRUD (admin_required), /api/meta, sitemap.xml
│   ├── auth.py                 # /api/login, /api/logout, /api/me
│   ├── recipes.py              # /api/recipes CRUD (login_required), search, category filter, slug generation
│   ├── utils.py                # GitHub API commit date with 6-hour cache
│   ├── create_user.py          # One-time utility: create users (admin or regular) with db.create_all()
│   ├── api/
│   │   ├── kenno.py              # GET /api/kenno + POST /api/kenno/block + GET /api/kenno/stats + GET /api/kenno/blocked + DELETE /api/kenno/block/<id> + POST /api/kenno/achievement + GET /api/kenno/achievements + POST /api/kenno/preview + POST /api/kenno/puzzle + GET /api/kenno/schedule + POST /api/kenno/puzzle/swap + DELETE /api/kenno/puzzle/<slot>; defines VALID_RANKS constant
│   │   ├── cowsay.py           # GET /api/cowsay (character, think params) + GET /api/cowsay/characters
│   │   ├── health.py           # GET /api/admin/health (system health stats)
│   │   ├── pageviews.py        # POST /api/pageview (public) + GET /api/pageviews (admin, with timestamps)
│   │   └── weather.py          # GET /api/weather (FMI open data, 10-min cache)
│   ├── wordlists/
│   │   └── kotus_words.txt     # Filtered Kotus Finnish word list (101k words, ≥4 chars)
│   └── data/
│       └── site.db             # SQLite database (Docker volume mounted)
├── scripts/
│   ├── process_kotus.py        # One-time script: downloads and filters Kotus word list → kotus_words.txt
│   ├── puzzle_variations.py    # CLI: show all 7 center-letter variations for a puzzle (python3 scripts/puzzle_variations.py [N])
│   ├── seed_puzzles.py         # One-time: populate KennoPuzzle DB from initial_puzzles.json
│   ├── seed_e2e.py             # E2E seed: creates app/data/ if missing, populates test-e2e.db with admin + regular users, 3 sections, 1 recipe, 41 puzzles
│   └── initial_puzzles.json    # Seed data: 41 puzzles with letters and centers
├── docs/
│   └── kenno-tool-screenshot.png  # Kennotyökalu screenshot for ADMIN_TOOLS.md
└── tests/
    ├── conftest.py             # pytest fixtures (app, client, admin_user, regular_user, logged_in_*)
    ├── test_admin_health.py    # Admin health endpoint tests
    ├── test_auth.py            # Auth endpoint tests
    ├── test_kenno.py             # Sanakenno endpoint + scoring + variations + achievement + custom puzzle tests (130 tests)
    ├── test_kenno_stats.py       # Sanakenno stats endpoint tests
    ├── test_blocked_words.py   # Blocked words list + unblock endpoint tests
    ├── test_cowsay.py           # Cowsay endpoint tests (default, custom message, truncation, special chars, character, think, characters list)
    ├── test_pageviews.py       # Page view counter API tests (with timestamp tests)
    ├── test_recipes.py         # Recipe CRUD tests
    ├── test_sections.py        # Sections CRUD + reorder tests
    └── test_weather.py         # Weather endpoint tests
```

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/sections` | Public | List all sections (ordered by position) |
| POST | `/api/sections` | Admin | Create section |
| PUT | `/api/sections/<id>` | Admin | Update section |
| DELETE | `/api/sections/<id>` | Admin | Delete section |
| PUT | `/api/sections/reorder` | Admin | Reorder sections (`{"order": [id, ...]}`) |
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
| GET | `/api/kenno` | Public | Sanakenno daily puzzle (center, letters, word_hashes, hint_data, max_score, puzzle_number, total_puzzles; admin also gets words) |
| POST | `/api/kenno/block` | Admin | Permanently remove a word from all puzzles (stored in blocked_words table) |
| GET | `/api/kenno/blocked` | Admin | List all blocked words with timestamps |
| DELETE | `/api/kenno/block/<id>` | Admin | Unblock a word by ID |
| GET | `/api/kenno/stats` | Admin | Sanakenno stats (page views, blocked count, total puzzles) |
| GET | `/api/kenno/variations?puzzle=N` | Admin | All 7 center-letter variations with stats (word_count, max_score, pangram_count, is_active) |
| POST | `/api/kenno/center` | Admin | Set center letter for a puzzle (`{puzzle: int, center: str}`) |
| POST | `/api/kenno/preview` | Admin | Preview 7 center-letter variations for arbitrary letters (rate-limited 20/min); optionally include `center` in body to also return word list |
| POST | `/api/kenno/puzzle` | Admin | Create or update a custom puzzle in a slot (`{slot, letters, center}`); rejects today's live slot (409) |
| GET | `/api/kenno/schedule?days=N` | Admin | Upcoming rotation schedule (default 14 days, clamped 1–90); returns dates, slots, display numbers, custom/today flags |
| POST | `/api/kenno/puzzle/swap` | Admin | Swap two puzzle slots (`{slot_a, slot_b}`); swaps both letters and center; rejects today's live slot (409) |
| DELETE | `/api/kenno/puzzle/<slot>` | Admin | Revert or remove a puzzle slot; base puzzles (0–40) revert to initial seed state, extension puzzles (41+) are deleted entirely; rejects today's live slot (409) |
| POST | `/api/kenno/achievement` | Public | Record anonymous rank achievement (session-deduped; validates rank against `VALID_RANKS`, puzzle_number, and numeric fields) |
| GET | `/api/kenno/achievements` | Admin | Daily achievement counts grouped by rank; query param `days` (default 30, clamped 1–90); returns `{days, daily: [{date, counts: {rank: N}, total}], totals: {rank: N}}` |
| POST | `/api/pageview` | Public | Increment page view counter for a path (`{"path": "/sanakenno"}`) |
| GET | `/api/pageviews` | Admin | All page view counts with timestamps, sorted by count desc |
| GET | `/api/admin/health` | Admin | System health (Python version, DB size, disk, uptime) |
| GET | `/api/cowsay?message=&character=&think=` | Public | ASCII cow art (optional message/character/think params, max 200 chars, default "moo") |
| GET | `/api/cowsay/characters` | Public | List available cowsay characters |
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

**Backend (pytest)**

```bash
pytest tests/
```

Uses an in-memory SQLite database. No server running required. Rate limiting is disabled in tests via the `TESTING` env var (`limiter.enabled = not os.environ.get("TESTING")`).

**E2E (Playwright)**

```bash
cd frontend && npm run test:e2e          # Headless Chromium
cd frontend && npm run test:e2e:ui       # Interactive UI mode
```

Playwright spins up both servers automatically (Flask on :5001, Vite on :5173). Uses a file-based SQLite DB at `app/data/test-e2e.db` seeded by `scripts/seed_e2e.py`. Rate limiting is disabled via `TESTING=1`. Test credentials: `admin@test.com` / `adminpass123` and `user@test.com` / `userpass123`. 28 tests across 7 spec files; runs in ~7s locally, ~55s in CI.

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
- **CI**: GitHub Actions (`.github/workflows/test.yml`) runs pytest and Playwright on every push and PR to main. Playwright report is uploaded as an artifact on failure.
- **Deployment**: Push to GitHub main → webhook (token-authenticated) → `deploy-site.sh` (git pull, docker compose up --build, systemctl restart).
- **Services**: `web-kontissa.service` (Docker Compose app, runs as kvjanhun), `webhook.service` (deploy listener, runs as kvjanhun). The old `site-container.service` (static HTML site) has been disabled.

## Key Patterns & Conventions

### Backend
- Flask app object lives in `app/__init__.py`, imported by modules
- Routes use `@app.route()` directly on the app (no blueprints)
- Admin protection via `@admin_required` decorator (wraps `@login_required` + role check)
- Recipe endpoints use `@login_required` — any authenticated user can CRUD any recipe (shared cookbook)
- Recipe create/update share a `_validate_recipe_data()` helper in `recipes.py` that validates the payload and returns `(data, error)`. `_parse_ingredients()` and `_parse_steps()` both validate that each item is a `dict`.
- `Section` model has a `section_type` column (`String`, default `'text'`). Valid values are `'text'`, `'pills'`, `'quote'`, and `'currently'`. POST validates and sets it; PUT only updates it when the field is present in the request body. Invalid values return 400. The field is included in all GET responses.
- All API endpoints return JSON
- `catch_all` route at the bottom of `routes.py` serves Vue SPA for client-side routing
- GitHub API responses cached for 6 hours in `utils.py`
- FMI weather data cached for 10 minutes in `api/weather.py`, with stale-cache fallback on API errors

### Frontend
- Composition API with `<script setup>` exclusively — no Options API
- Composables for shared state (`useAuth`, `useDarkMode`, `useI18n`) — module-level refs for singleton pattern. `useNavLinks` provides the shared navigation link list consumed by both `AppHeader` and `AppFooter`.
- **Static site generation (SSG)**: `vite-ssg` pre-renders `/`, `/about`, `/contact`, `/login` at build time into static HTML with real content (SEO-friendly). Vue hydrates on top in the browser for interactivity. `main.js` exports `createApp` via `ViteSSG()` instead of the standard `createApp()`. Protected and dynamic routes (`/admin`, `/recipes/*`, `/sanakenno`) are not pre-rendered.
- Lazy-loaded routes (all except HomePage)
- Styling via Tailwind utility classes + CSS custom properties for theme colors
- Inline `:style` bindings for theme-aware dynamic colors
- `v-html` used for section content of type `'text'` (admin-authored, trusted). Other section types use `{{ }}` text interpolation — no `v-html` involved.
- `SectionBlock.vue` renders 4 section types: `'quote'` (decorative centered blockquote with large opening quote mark, no card wrapper), `'currently'` (card with line-separated `label: value` items rendered as accent-bordered rows), `'pills'` (card with comma-separated items in a 3-column grid of accent-bordered flat items), `'text'` (card with `v-html` content). All card types (currently, pills, text) have an orange accent bar under the title. Paragraph spacing (`p + p` margin) is applied via a scoped deep selector on `.section-content`. Supports a `compact` prop to suppress bottom margin when used in paired grid layout.
- `AboutPage.vue` groups adjacent compact section types (`currently`, `pills`) into side-by-side two-column grid pairs on `md+` screens. The "About" h1 heading is removed — the quote section serves as the page intro.
- Recipe content uses `{{ }}` only — no `v-html`, all user content auto-escaped
- `requiresAuth` route meta guard redirects unauthenticated users to `/login`. The `router.beforeEach` hook is `async` and `await`s `checkAuth()` before evaluating guards — this ensures auth state is populated on direct URL navigation to protected routes (e.g. `/admin`, `/recipes`). Omitting the `await` causes a race condition where the guard fires before the `/api/me` response arrives.
- Logout (`useAuth.js`) waits for the server response before clearing client auth state. The logout button uses `@click.prevent` and navigates manually after the logout call completes, preventing race conditions with the router guard.
- i18n via custom `useI18n` composable — no external dependency. All UI strings in `locales/en.json` and `locales/fi.json`. Use `t('key')` for translation, `t('key', { param: value })` for interpolation. Fallback chain: current locale → English → raw key. Route titles use `titleKey` meta resolved in `main.js` afterEach. Language persists in localStorage, defaults to browser locale. Terminal prompt, brand names, API content, and Schema.org JSON-LD are NOT translated.
- Accessibility: skip-to-content link, `:focus-visible` ring on all interactive elements, `aria-expanded` on mobile menu with Escape-to-close, `aria-live` route announcer in App.vue, `role="alert"` on error messages, `role="status"` on loading/success states, `aria-hidden="true"` on decorative SVGs, `aria-label` on icon-only buttons, `prefers-reduced-motion` respected via CSS. Sanakenno honeycomb SVG hexagons have `role="button"` and `aria-label` (letter name) for screen reader access.

### Design
- Warm stone-grey palette with orange accent (#ff643e)
- Dark/light mode via `.dark` class on `<html>` with CSS custom property overrides
- Fonts: DM Sans (body), Ubuntu Mono (terminal)
- Mobile-first responsive: always-hamburger nav (no inline desktop nav)

## Sanakenno (Finnish Spelling Bee)

Public word game at `/sanakenno` (component `SanakennoPage.vue`). NYT Spelling Bee rules with a Finnish word list. Nav shows "Sanakenno" in both languages. Backend API at `GET /api/kenno`.

- **Word list**: `app/wordlists/kotus_words.txt` — 101k words from Kotus (Institute for the Languages of Finland), filtered to ≥4 chars, lowercase, Finnish alphabet only. Generated one-time by `scripts/process_kotus.py`.
- **Puzzles**: All puzzles are stored in the `KennoPuzzle` database table. Center letters are stored in `KennoConfig` (key `center_{idx}`). The total puzzle count (`_total_puzzles()`) equals the highest `KennoPuzzle.slot + 1`. Rotation is deterministic: `(START_INDEX + days_since_ROTATION_START) % total_puzzles`. `ROTATION_START = date(2026, 2, 24)`, `START_INDEX = 1`. Valid words and max_score are computed lazily and cached in `_PUZZLE_CACHE`. All mutating endpoints enforce live-slot protection (409) so today's puzzle can never be edited. A one-time seed script (`scripts/seed_puzzles.py` + `scripts/initial_puzzles.json`) exists for fresh deployments.
- **Scoring**: 4-letter word = 1pt; 5+ letters = length in pts; pangram (uses all 7 letters) = +7 bonus.
- **Ranks**: 7 Finnish rank levels based on % of max_score: Etsi sanoja! (0%), Hyvä alku (2%), Nyt mennään! (10%), Onnistuja (20%), Sanavalmis (40%), Ällistyttävä (70%), Täysi kenno (100%).
- **Word hiding**: The API sends SHA-256 hashes of valid words (`word_hashes`) instead of plaintext. The frontend hashes user input via `crypto.subtle.digest` and checks against the hash set. Admin requests also receive the plaintext `words` array, used by `AdminKennoPuzzleTool.vue` for the word list display and blocking feature. Pre-computed `hint_data` (word_count, pangram_count, by_letter, by_length, by_pair) powers all four hint panels without exposing the word list.
- **Frontend**: `SanakennoPage.vue` — SVG honeycomb, keyboard input (letters/Backspace/Enter), client-side validation via SHA-256 hash comparison. All game UI strings are Finnish-only regardless of site language setting. The browser tab title shows `"Sanakenno — #N"` where N is the current puzzle number. The title is displayed inline in the top bar row alongside the back link, "?" help button, and theme toggle — there is no separate title section. Score, progress bar, and the hints-toggle/share button row are in a `position: sticky; top: 0` section that remains visible while scrolling. Rank thresholds and the hints panel are outside the sticky section (they expand/collapse). All admin controls (puzzle switcher, center variations, remaining words, block word) have been removed from `SanakennoPage.vue`; they live in `AdminKennoPuzzleTool.vue`.
- **Touch zoom prevention**: `touch-action: manipulation` on the root game div prevents double-tap zoom on iOS Safari. The honeycomb SVG element has `touch-action: none` scoped to prevent mobile browsers from interpreting hexagon taps as scroll gestures — the rest of the page scrolls normally.
- **State persistence**: Found words and score are saved to `localStorage` under key `sanakenno_state` as `{puzzleNumber, foundWords[], score, hintsUnlocked[], startedAt}`. Restored on page load when the stored puzzle number matches the current puzzle. On restore, `foundWords` is filtered against the current puzzle's word list to discard any stale entries (e.g. from a blocked word). Prevents progress loss on refresh or navigation.
- **Admin puzzle tool** (`AdminKennoPuzzleTool.vue`, "Kennotyökalu" tab): Unified single-editor layout. Left column: scrollable slot list for all puzzles (1–N), auto-scrolls to today's slot on load, shows play dates, "today" badge, and "custom" badge for DB-overridden puzzles. Right column top: compact toolbar with slot number display, letters text input (dirty state), swap-slot input, and delete/revert button. Right column main: `KennoVariationsGrid.vue` (7-column grid, word_count/max_score/pangram_count per letter; active center highlighted). Below grid: `KennoWordList.vue` (sorted multi-column word list, pangrams highlighted in orange accent + semibold, per-word block buttons). Clean state: view current puzzle, click a variation column to switch center via `POST /api/kenno/center`. Dirty state: edit letters → Enter to preview via `POST /api/kenno/preview` → select center from results → save via `POST /api/kenno/puzzle`. Reset button discards unsaved letter changes. Puzzle selection is session-local (not persisted to localStorage). Regular users always see the daily rotation.
- **Found words**: Compact view shows the last 6 found words in a single no-wrap overflow-hidden row. "Kaikki ▼" expands to a full alphabetical multi-column list; "Vähemmän ▲" collapses back. Sort order: alphabetical with word length (shortest first) as a tiebreaker.
- **Animations**: Invalid submission triggers a shake animation (`word-shake`, 0.4s) on the input row. Honeycomb hexagons scale down on `pointerdown` for press feedback. A rank-up notification ("Uusi taso: …!") is shown for 3 seconds when score crosses a rank threshold (except for the two celebration milestones).
- **Level system**: Täysi kenno (100%) is hidden from the rank threshold display — players see Ällistyttävä (70%) as the visible goal. Täysi kenno appears as a surprise reveal when reached.
- **Celebrations**: Two milestone celebrations triggered via a modal overlay (`celebration` ref). Reaching Ällistyttävä shows a banner with a glow animation (5s auto-dismiss). Reaching Täysi kenno shows a flashier celebration with an intense golden glow (8s auto-dismiss). Both can be dismissed by clicking/tapping. Other rank-ups use the standard "Uusi taso" message.
- **Progress bar**: A thin bar below the score/rank row shows progress toward the next rank (`progressToNextRank` computed, animates via CSS transition).
- **Re-submit highlight**: When a player submits an already-found word, that word flashes orange in the found words list for 1.5 s (`lastResubmittedWord` ref), alongside the "Löysit jo tämän!" message.
- **All-found banner**: When `allFound` computed is true (all words discovered), a "Kaikki N sanaa löydetty!" banner appears above the found words list.
- **Avut (hints panel)**: Collapsible section visible to all players. Contains four individually activatable hints, identified by string IDs — once unlocked they persist in `hintsUnlocked` (Set) in `sanakenno_state` localStorage across sessions. Each unlocked hint header is also individually clickable to collapse or expand its content (▼/▲ indicator); this per-hint collapsed state lives in a `hintsCollapsed` ref (a `Set`) that is session-only and not persisted to localStorage. Each hint has a unique icon (SVG in UI, emoji in share text):
  1. **`summary`** 📊 (magnifying glass) — "Yleiskuva": two-line summary. Line 1: remaining/total word count + percentage + remaining/total pangram count. Line 2: number of distinct word lengths + length of the longest word in the puzzle.
  2. **`letters`** 🔤 (letter A) — "Alkukirjaimet": remaining unfound words grouped by starting letter (all puzzle letters shown; fully-found letters displayed muted at 0).
  3. **`distribution`** 📏 (ruler) — "Pituusjakauma": word count per length (e.g. "4: 12  5: 8  6: 3"), showing remaining per length; fully-found lengths are muted.
  4. **`pairs`** 🔠 (Aa) — "Alkuparit": remaining unfound words grouped by first two letters, formatted like Alkukirjaimet; fully-found pairs displayed muted at 0.
  - UI icons use a `HINT_SVG` object with inline SVG paths (lightbulb for toggle, magnifying glass, A, ruler, Aa), each sized ~1em and styled with `currentColor` to inherit theme colors. Share text uses the emoji from `HINT_ICONS` object.
  - Admin puzzle switches reset hint state together with game progress.
- **Jaa tulos (share)**: Button rendered next to the Avut toggle. Uses `navigator.clipboard.writeText` to copy a plain-text summary: puzzle number, current rank, score/max_score, and hint icons (📊🔤📏🔠) for any activated hints. After copying, a brief "Kopioitu leikepöydälle!" confirmation is shown.
- **OG meta tags**: The `/sanakenno` Flask route in `routes.py` reads `index.html` and patches `<title>`, `description`, `og:title`, `og:description`, `og:url`, and `<link rel="icon">` (to `/sanakenno-favicon.png`) for link preview cards and Safari favicon on hard navigation.
- **Favicon swap**: `useFaviconSwap.js` (called by `SanakennoPage.vue`) swaps the favicon to `frontend/public/sanakenno-favicon.png` on mount via element replacement, and restores the original on unmount. Safari does not reliably support dynamic favicon changes; `routes.py` patches `<link rel="icon">` in the served HTML to cover Safari on hard navigation.
- **Word blocking**: Admins can permanently remove a word via `POST /api/kenno/block`. Blocked words are stored in the `blocked_words` table (`BlockedWord` model). Blocking clears `_PUZZLE_CACHE` so the next request recomputes. After blocking, `AdminKennoPuzzleTool.vue` refetches the word list to reflect the removal.
- **Timer**: Elapsed play time is managed by `useGameTimer.js`. Tab visibility is monitored via `visibilitychange`, `blur`, and `pagehide` events to accumulate paused time. Exposes `startedAt`, `totalPausedMs`, `start()`, `getElapsedMs()`, `reset()`.
- **No auth required**: Public endpoint, no database usage for normal play.
- **Achievement tracking**: On each rank transition (when `rankAfter !== rankBefore`), `SanakennoPage.vue` fires a fire-and-forget `POST /api/kenno/achievement` with `{puzzle_number, rank, score, max_score, words_found, elapsed_ms}`. The server deduplicates per session via `session["achieved_ranks"]` (a list of `"puzzle:rank"` strings) so each rank is recorded at most once per browser session. Achievements are stored in the `KennoAchievement` model. The admin `GET /api/kenno/achievements` endpoint returns daily counts by rank for the chosen period. Default period is 7 days in `AdminKennoStats.vue`.
- **Center variation selector**: The 7-column grid (word count, max score, pangram count per center letter; active center highlighted) is rendered by `KennoVariationsGrid.vue` inside `AdminKennoPuzzleTool.vue`. Clicking a non-active letter in clean state calls `POST /api/kenno/center` and refreshes the display.
- **Adding puzzles**: Via admin UI: use the Kennotyökalu editor (enter letters, preview, select center, save to any non-live slot). All puzzles live in the `KennoPuzzle` DB table. Word filtering and scoring are automatic on first access. Cycle length equals `_total_puzzles()` (currently at minimum 41). For a fresh DB, run `scripts/seed_puzzles.py` to populate the initial 41 puzzles.

## Security Considerations

- **Session signing**: `SECRET_KEY` from `.env` — fixed dev-only string fallback in `app/__init__.py` (keeps sessions alive across restarts during local development). Production MUST set a proper secret via `.env`.
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
