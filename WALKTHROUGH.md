# How erez.ac Works — A Walkthrough

This document walks through the entire request lifecycle of erez.ac,
from a visitor opening the site to content appearing on screen.

---

## The Big Picture

```
Browser                         Vite / Flask                    Database
  |                                 |                              |
  GET /                             |                              |
  |------------------------------->|                              |
  |  <-- index.html + JS bundle   |                              |
  |  (Vite build output)          |                              |
  |                                 |                              |
  |  Vue + Router mount            |                              |
  |  Dark mode applied from        |                              |
  |  localStorage / system pref    |                              |
  |  Language set from             |                              |
  |  localStorage / browser locale |                              |
  |                                 |                              |
  |  GET /api/meta --------------->|  fetch GitHub API (cached)   |
  |  <-- JSON {update_date, ...}   |                              |
  |                                 |                              |
  |  POST /api/pageview ----------->|  upsert page_views row       |
  |  <-- JSON {path, count}        |<-----------------------------|
  |                                 |                              |
  |  GET /api/cowsay -------------->|  cowsay.get_output_string()  |
  |  <-- JSON {output: "..."}      |                              |
  |                                 |                              |
  |  GET /api/weather ------------->|  FMI API (cached 10 min)     |
  |  <-- JSON {temp, wind, ...}    |                              |
  |                                 |                              |
  |  Navigate to /about:           |                              |
  |  GET /api/sections ----------->|  SELECT * FROM section       |
  |  <-- JSON [{slug, title, ...}] |<-----------------------------|
  |                                 |                              |
  |  Navigate to /sanakenno:       |                              |
  |  GET /api/bee ---------------->|  compute puzzle (cached)     |
  |  <-- JSON {center, letters,    |  SELECT FROM bee_config      |
  |            words, max_score,   |<-----------------------------|
  |            puzzle_number, ...} |                              |
  |                                 |                              |
  |  Navigate to /recipes:         |                              |
  |  GET /api/recipes ------------>|  SELECT * FROM recipe        |
  |  <-- JSON [{title, slug, ...}] |<-----------------------------|
  |                                 |                              |
  |  Vue renders everything        |                              |
```

There are two phases:
1. **Server sends the built app** — Vite-compiled HTML, JS bundle, and CSS
2. **Vue takes over in the browser** — Vue Router handles navigation, fetches data via API, renders everything

---

## File by File

### `run.py` — Entry Point

Starts the Flask app on port 5001 (for local dev with Vite proxy).
Used by Gunicorn in production: `gunicorn -w 2 -b 0.0.0.0:80 run:app`

> Port 5001 is used because macOS AirPlay Receiver occupies port 5000.

### `app/__init__.py` — App Factory

Creates the Flask app and wires everything together:

```python
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI", "sqlite:////app/data/site.db"
)
```

- Default DB path is `/app/data/site.db` (inside the Docker container)
- For local dev, override with the `DATABASE_URI` env var
- Sets up Flask-Login (session management) and Flask-Limiter (30 req/min default, in-memory storage)
- `SECRET_KEY` comes from the `.env` file; falls back to a fixed dev string so sessions survive Flask restarts locally
- Runs `db.create_all()` and `_run_migrations()` on startup (adds columns to existing SQLite tables that `create_all` won't add)
- Imports `routes`, `auth`, `recipes`, `api.cowsay`, `api.weather`, `api.bee`, `api.pageviews`, and `api.health` at the bottom, which registers all URL routes
- After registering routes, calls `bee._seed_centers()` to populate default puzzle center letters if the `BeeConfig` table is empty

### `app/models.py` — Database Models

Eight models:

```python
class User(db.Model):        # username, email, password_hash, role
class Section(db.Model):     # slug, title, content, section_type, position
class Recipe(db.Model):      # title, slug, category, created_by, created_at
class Ingredient(db.Model):  # recipe_id, name, amount, unit, position
class Step(db.Model):        # recipe_id, content, position
class BlockedWord(db.Model): # word, blocked_at — admin-curated exclusion list for Sanakenno
class PageView(db.Model):    # path, count, created_at, updated_at — one row per path, upserted
class BeeConfig(db.Model):   # key, value — key-value store; currently holds center_{idx} entries
```

Each model (except `BeeConfig`) has a `to_dict()` method for JSON serialization. `Recipe.to_dict()` accepts `include_children=True` to nest ingredients and steps. `Section.to_dict()` includes `section_type` in its output.

### `app/routes.py` — Core Routes

| Route | What it does |
|---|---|
| `GET /` | Serves `index.html` from the Vite build output (`app/static/dist/`). |
| `GET /sanakenno` | Reads `index.html`, patches `<title>` and OG meta tags for link previews, then serves the modified HTML. |
| `GET /<path>` | Catch-all — serves static file from `dist/` if it exists, otherwise `index.html` for Vue Router. |
| `GET /api/sections` | Queries all Sections from SQLite ordered by position, returns JSON array. |
| `POST /api/sections` | Admin-only. Creates a section; validates `section_type` (`text`, `pills`, `quote`, `currently`). |
| `PUT /api/sections/<id>` | Admin-only. Updates section fields present in the request body; validates `section_type` if provided. |
| `DELETE /api/sections/<id>` | Admin-only. Deletes a section. |
| `PUT /api/sections/reorder` | Admin-only. Accepts `{"order": [id, ...]}` and sets `position` on each section. |
| `GET /api/meta` | Fetches last commit date from GitHub API, returns site metadata JSON. |
| `GET /sitemap.xml` | Dynamically generates XML sitemap for search engines. |

The `admin_required` decorator is defined here and wraps `@login_required` with a role check.

### `app/auth.py` — Authentication

| Route | What it does |
|---|---|
| `POST /api/login` | Validates email/password, starts Flask-Login session. |
| `POST /api/logout` | Ends session. |
| `GET /api/me` | Returns current user info or 401. |

Passwords are hashed with werkzeug scrypt. The `@admin_required` decorator (defined in `routes.py`) wraps `@login_required` with a role check.

### `app/recipes.py` — Recipe CRUD

| Route | What it does |
|---|---|
| `GET /api/recipes` | List recipes with optional `?q=` search and `?category=` filter. |
| `GET /api/recipes/<slug>` | Single recipe with nested ingredients and steps. |
| `POST /api/recipes` | Create recipe with nested ingredients/steps arrays. |
| `PUT /api/recipes/<id>` | Update recipe (replaces all ingredients/steps). |
| `DELETE /api/recipes/<id>` | Delete recipe (cascades to ingredients/steps). |
| `GET /api/recipes/categories` | Returns list of valid categories. |

All recipe endpoints require `@login_required`. Any authenticated user can CRUD any recipe (shared cookbook model). Create and update share a `_validate_recipe_data()` helper that validates the payload and returns `(data, error)`.

### `app/utils.py` — GitHub Commit Date

Fetches the latest commit date from `github.com/kvjanhun/web_kontissa`:

- Calls the GitHub API once, then **caches the result for 6 hours**
- Used by `/api/meta` to show "Last updated: YYYY-MM-DD" in the footer
- Falls back to cached value if the API call fails

### `app/api/cowsay.py` — Cowsay Endpoint

```
GET /api/cowsay?message=&character=&think= → {"output": "  ___\n| moo |\n ..."}
GET /api/cowsay/characters → ["cow", "tux", ...]
```

Uses the Python `cowsay` library to generate ASCII art. Optional params: `message` (max 200 chars, default `"moo"`), `character`, `think` (boolean, uses thought bubbles instead of speech). The terminal animation in the browser fetches this after typing the command.

### `app/api/weather.py` — Weather Endpoint

```
GET /api/weather → {"temperature": -12.4, "feels_like": -18.2, "wind_speed": 2.7, "condition": "Snow", ...}
```

Fetches real-time weather observations from the Finnish Meteorological Institute (FMI) open data WFS API for Helsinki-Vantaa airport (FMISID 100968):

- **XML parsing**: Extracts the latest non-NaN measurement for each parameter (`t2m`, `ws_10min`, `wawa`) from `omso:PointTimeSeriesObservation` elements
- **Wind chill**: Calculated server-side using the Environment Canada / NWS formula (applies when T ≤ 10°C and wind > 4.8 km/h)
- **Condition mapping**: WMO code table 4680 (automatic weather station present weather codes) mapped to human-readable strings in both English and Finnish
- **Caching**: Results cached for 10 minutes (matching FMI's update interval). Falls back to cached data if the API is down

### `app/api/bee.py` — Sanakenno Game API

```
GET  /api/bee                      → {center, letters, words[], max_score, puzzle_number, total_puzzles}
POST /api/bee/block                → blocks a word (admin)
GET  /api/bee/blocked              → list blocked words with timestamps (admin)
DELETE /api/bee/block/<id>         → unblock a word by ID (admin)
GET  /api/bee/stats                → {page_views, blocked_words_count, total_puzzles} (admin)
GET  /api/bee/variations?puzzle=N  → all 7 center-letter variations with stats (admin)
POST /api/bee/center               → set center letter for a puzzle (admin)
```

Key implementation details:

- **Word list**: `app/wordlists/kotus_words.txt` — 101k Finnish words, loaded at startup into `_ALL_WORDS` (a `frozenset`). Hyphenated compounds are normalised by stripping the hyphen.
- **Puzzles**: 41 curated letter sets in `PUZZLES`. Each entry is `{"letters": [7 sorted letters]}`. The center letter for each puzzle is stored in `BeeConfig` (key `center_{idx}`), seeded from `_DEFAULT_CENTERS` on first startup by `_seed_centers()`.
- **Rotation**: Today's puzzle index = `(START_INDEX + days_since_ROTATION_START) % 41`. `ROTATION_START = date(2026, 2, 24)`, `START_INDEX = 1`.
- **Scoring**: 4-letter word = 1 pt; 5+ letters = length in pts; pangram (uses all 7 letters) = +7 bonus.
- **Cache**: Valid words and max_score are computed lazily on first access and stored in `_PUZZLE_CACHE` (dict keyed by puzzle index). Blocking or unblocking a word clears the entire cache. Admin override (`?puzzle=N`) is accepted when the request comes from an authenticated admin.
- **Admin tools**: `GET /api/bee/variations` computes stats for all 7 possible center letters of a puzzle. `POST /api/bee/center` switches the active center and clears that puzzle's cache entry.

### `app/api/pageviews.py` — Page View Tracking

```
POST /api/pageview  → {path, count}   (public, 60 req/min limit)
GET  /api/pageviews → [{path, count, created_at, updated_at}, ...] sorted by count desc (admin)
```

- `POST /api/pageview` accepts `{"path": "/some-path"}`. Path must start with `/` and be ≤ 200 chars.
- **Session-based dedup**: each path is counted only once per browser session (stored in `session["viewed_pages"]`). Repeat visits within the same session do not increment the counter.
- One `PageView` row per path; `count` is incremented on each unique session hit.

### `app/api/health.py` — System Health

```
GET /api/admin/health → {python_version, db_size_bytes, disk_total_bytes, disk_free_bytes, uptime_seconds}
```

Admin-only. Reports Python version, SQLite DB file size, disk usage (via `os.statvfs`), and process uptime since module import.

---

## The Frontend (`frontend/`)

The frontend is a Vite + Vue 3 project using Single File Components (SFCs), with multi-page routing, dark/light mode, and EN/FI language support.

### Structure

```
frontend/
├── index.html              Vite entry point + dark mode flash prevention script + Schema.org JSON-LD
├── package.json            Dependencies: vue, vue-router, vite, tailwindcss, vite-ssg
├── vite.config.js          Vite config with Vue plugin, Tailwind, Flask proxy to :5001, SSG options
├── public/
│   └── favicon.ico         Static assets copied as-is
└── src/
    ├── main.js             ViteSSG entry point: createApp with SSG, router guards, i18n title updates
    ├── router.js           Vue Router: 11 routes with lazy loading + titleKey meta
    ├── style.css           Tailwind CSS + theme tokens + dark mode + focus styles + reduced motion
    ├── App.vue             Root layout: header, router-view, footer, skip link, route announcer. Calls checkAuth() on mount.
    ├── composables/
    │   ├── useAuth.js      Shared auth state (user, isAdmin, isAuthenticated, login, logout, checkAuth)
    │   ├── useDarkMode.js  Shared dark mode state + localStorage persistence
    │   ├── useI18n.js      EN/FI i18n: locale ref, t(key, params), localStorage persistence
    │   ├── useNavLinks.js  Shared nav link list consumed by AppHeader and AppFooter
    │   ├── usePageView.js  trackPageView(path) — fire-and-forget POST /api/pageview
    │   └── useTerminal.js  Interactive shell logic: boot sequence (skipped on re-mount), command handlers, history navigation
    ├── locales/
    │   ├── en.json         English translations (~90 keys)
    │   └── fi.json         Finnish translations
    ├── components/
    │   ├── AppHeader.vue       Sticky header, always-hamburger menu, auth-aware nav, LangToggle, ThemeToggle
    │   ├── AppFooter.vue       Full auth-aware nav links + last-updated date from /api/meta
    │   ├── ThemeToggle.vue     Sun/moon SVG button using useDarkMode composable
    │   ├── LangToggle.vue      EN/FI toggle button using useI18n composable
    │   ├── TerminalWindow.vue  Interactive shell with boot sequence + commands: help, about, skills, fetch, weather, cowsay, cowthink, uptime, date, time, whoami, clear
    │   ├── weatherIcons.js     Inline SVG weather icons + wawaToIcon(code) mapper
    │   ├── SectionBlock.vue    Section renderer: 4 types — see below
    │   └── admin/
    │       ├── AdminSections.vue     Sections CRUD + reorder (up/down arrows); type selector dropdown in forms
    │       ├── AdminPageViews.vue    Page views table with timestamps
    │       ├── AdminRecipes.vue      Recipe table with edit/delete links
    │       ├── AdminHealth.vue       System health key-value display
    │       ├── AdminBeeStats.vue     Sanakenno overview stats (page views, blocked words, puzzles)
    │       └── AdminBlockedWords.vue Blocked words table with unblock button
    └── views/
        ├── HomePage.vue          Hero layout: name, subtitle, terminal, CTA buttons
        ├── AboutPage.vue         Fetches /api/sections, renders SectionBlocks; groups compact types into two-column pairs on md+; no h1 heading
        ├── ContactPage.vue       Static contact links: email, GitHub, LinkedIn
        ├── LoginPage.vue         Auth form wired to backend, or logged-in state
        ├── AdminPage.vue         Two-level collapsible dashboard (Site Admin, Sanakenno Admin) with 6 panel components
        ├── RecipeListPage.vue    Recipe cards with search + category filter
        ├── RecipeDetailPage.vue  Single recipe with wake lock + step checkboxes
        ├── RecipeFormPage.vue    Create/edit recipe with dynamic ingredient/step rows
        ├── SanakennoPage.vue     Finnish Spelling Bee game (SVG honeycomb, full game UI)
        └── NotFound.vue          404 page with accent styling
```

### Routing

Vue Router manages eleven routes with lazy loading for non-home views:

| Route | View | Content |
|-------|------|---------|
| `/` | HomePage | Hero with terminal animation + CTA buttons |
| `/about` | AboutPage | Sections fetched from `/api/sections` |
| `/contact` | ContactPage | Static email, GitHub, LinkedIn links |
| `/login` | LoginPage | Auth form or logged-in state with logout |
| `/admin` | AdminPage | Protected admin dashboard (requires admin) |
| `/recipes` | RecipeListPage | Recipe cards with search + filter (requires auth) |
| `/recipes/new` | RecipeFormPage | Create new recipe (requires auth) |
| `/recipes/:slug` | RecipeDetailPage | Single recipe view (requires auth) |
| `/recipes/:slug/edit` | RecipeFormPage | Edit existing recipe (requires auth) |
| `/sanakenno` | SanakennoPage | Finnish Spelling Bee game (public) |
| `*` | NotFound | 404 with accent styling |

Routes use `titleKey` meta (e.g., `'title.about'`) resolved via `t()` in `main.js` `afterEach`, so page titles update with the current language. Auth guards in `beforeEach` redirect unauthenticated users to `/login`.

### Static Site Generation (vite-ssg)

The build step doesn't just bundle JS — it **pre-renders pages into static HTML**.

`main.js` uses `ViteSSG()` instead of Vue's standard `createApp()`. At build time (`vite-ssg build`), this:

1. Boots the Vue app in a Node.js environment (no browser)
2. Visits each route listed in `ssgOptions.includedRoutes`: `/`, `/about`, `/contact`, `/login`
3. Renders the component tree to HTML and writes it to `dist/` as nested `index.html` files (e.g., `dist/about/index.html`)

The result is that crawlers and users get real HTML content on first load — not an empty `<div id="app">`. Vue then **hydrates** on top: it attaches event listeners and reactivity to the existing HTML without re-rendering it.

Routes that require auth or are dynamic (`/admin`, `/recipes/*`, `/sanakenno`) are **not pre-rendered** — they fall back to the standard SPA behavior (empty shell → client-side render).

### How Vue Renders the Page

1. Browser loads pre-rendered HTML (real content already visible) or falls back to the SPA shell for non-SSG routes
2. An inline `<script>` in `<head>` synchronously sets `.dark` on `<html>` based on localStorage or system preference (prevents flash of wrong theme)
3. Vite-bundled JS loads (includes Vue, Vue Router, all components)
4. `main.js` hydrates the pre-rendered HTML (or mounts fresh for non-SSG routes), registers the router, and activates reactivity
5. The root `App.vue` runs `onMounted`:
   - Calls `checkAuth()` to restore session state
   - Fetches `/api/meta` for footer update date
   - Vue automatically re-renders when data arrives
6. Vue Router matches the current URL and renders the corresponding view
7. Components render:
   - **AppHeader** — sticky nav with auth-aware links, LangToggle (EN/FI), ThemeToggle (sun/moon), mobile hamburger with Escape-to-close
   - **HomePage** — hero layout with name/subtitle, TerminalWindow (typing animation + cowsay + weather), and CTA buttons
   - **AboutPage** — fetches `/api/sections`, shows loading skeleton or error state, then renders SectionBlocks. Adjacent compact section types (`currently`, `pills`) are grouped into side-by-side two-column pairs on `md+` screens. No `<h1>` heading — the quote section serves as the page intro.
   - **ContactPage** — static links to email, GitHub, LinkedIn
   - **LoginPage** — email/password form wired to `/api/login`, or logged-in state with logout button
   - **AdminPage** — two-level collapsible dashboard: "Site Admin" (AdminSections, AdminPageViews, AdminRecipes, AdminHealth) and "Sanakenno Admin" (AdminBeeStats, AdminBlockedWords)
   - **RecipeListPage** — recipe cards with debounced search and category filter
   - **RecipeDetailPage** — single recipe with ingredients, interactive step checkboxes, screen wake lock
   - **RecipeFormPage** — create/edit form with dynamic ingredient and step rows
   - **SanakennoPage** — full Sanakenno game (see Sanakenno section below)
   - **AppFooter** — last-updated date + nav links (shared link list from `useNavLinks`)

### SectionBlock.vue — Section Types

`SectionBlock.vue` renders one of four section types based on the `section_type` field:

| Type | Rendering |
|------|-----------|
| `quote` | Decorative centered blockquote with large opening quote mark. No card wrapper. Used as the About page intro. |
| `currently` | Card with an orange accent bar under the title. Content split on newlines into `label: value` pairs, each rendered as an accent-bordered row. |
| `pills` | Card with an orange accent bar under the title. Content split on commas into items, rendered in a 3-column grid of flat accent-bordered badges. Whitespace stripped, empty items filtered. |
| `text` | Card with an orange accent bar under the title. Content rendered via `v-html` (admin-authored, trusted). Paragraph spacing applied via a scoped deep selector on `.section-content`. |

All card types (`currently`, `pills`, `text`) accept a `compact` prop to suppress bottom margin when used in a paired two-column grid on the About page.

### Dark Mode

Dark mode uses a class-based approach:

1. **Flash prevention**: inline `<script>` in `index.html` `<head>` checks localStorage then `prefers-color-scheme` and sets `.dark` on `<html>` synchronously before CSS loads
2. **Composable** (`useDarkMode.js`): shared reactive `isDark` ref, persists to localStorage, toggles `.dark` class on `<html>`
3. **CSS custom properties**: `:root` and `.dark` blocks in `style.css` define all theme tokens
4. **`@variant dark`**: Tailwind v4 directive enables `dark:` variant based on `.dark` class
5. **ThemeToggle.vue**: sun/moon SVG button that calls `toggleDark()` from the composable

### Internationalization (i18n)

EN/FI language support via a custom composable — no external dependencies:

1. **Composable** (`useI18n.js`): singleton `locale` ref, `t(key, params)` function, `setLocale()` with localStorage persistence
2. **Locale files** (`locales/en.json`, `locales/fi.json`): ~90 flat translation keys
3. **Detection**: localStorage → `navigator.language` → `'en'` fallback
4. **Fallback chain**: current locale → English → raw key (never breaks)
5. **LangToggle.vue**: shows the *other* language (FI when English, EN when Finnish)
6. **Route titles**: `titleKey` meta on routes, resolved via `t()` in `afterEach`
7. **Not translated**: terminal prompt, brand names (`erez.ac`), API content, Schema.org JSON-LD, all Sanakenno game UI (Finnish-only regardless of site language setting)

### Accessibility

Key accessibility features:

- **Skip-to-content link**: visually hidden, becomes visible on Tab focus, jumps to `<main>`
- **Focus indicators**: `:focus-visible` orange ring on interactive elements (a, button, input, select, textarea), scoped to avoid iOS Safari quirks
- **Route announcer**: `aria-live="polite"` region in App.vue announces page titles on navigation
- **Mobile menu**: `aria-expanded` on hamburger, `Escape` key to close
- **ARIA roles**: `role="alert"` on error messages, `role="status"` on loading/success states
- **Decorative SVGs**: `aria-hidden="true"` on all icon SVGs
- **Icon buttons**: `aria-label` on ThemeToggle, LangToggle, and hamburger
- **Form errors**: `aria-invalid` and `aria-describedby` linking errors to inputs
- **Sanakenno hexagons**: `role="button"` and `aria-label` (letter name) on each SVG hexagon
- **Reduced motion**: `prefers-reduced-motion` media query disables all animations and transitions
- **Color contrast**: all text meets WCAG AA (4.5:1 minimum)

### Loading & Error States

Views that fetch data track their own loading and error state:
- `loading` (boolean) — `true` while the API request is in-flight, with `role="status"` for screen readers
- `error` (string/object) — set if the fetch fails, with `role="alert"` for screen readers

AboutPage shows pulsing skeleton placeholders while loading. Recipe pages show text loading indicators. Error states show red-tinted messages.

---

## Sanakenno (Finnish Spelling Bee)

Public word game at `/sanakenno`. NYT Spelling Bee rules with a Finnish word list. Nav shows "Sanakenno" in both languages.

### Game Rules

Find words using the 7 displayed letters. Every word must contain the center letter. Letters may be reused. Words must be ≥ 4 characters and exist in the Finnish word list.

**Scoring**: 4-letter word = 1 pt; 5+ letters = word length in pts; pangram (uses all 7 letters) = +7 bonus.

**Ranks** (7 levels, based on % of max_score):

| Rank | Threshold |
|------|-----------|
| Etsi sanoja! | 0% |
| Hyvä alku | 2% |
| Nyt mennään! | 10% |
| Onnistuja | 20% |
| Sanavalmis | 40% |
| Ällistyttävä | 70% |
| Täysi kenno | 100% |

### How the API Works

`GET /api/bee` returns the full puzzle for the day: `center`, `letters` (the other 6), `words` (complete valid word list), `max_score`, `puzzle_number` (0-indexed internally), and `total_puzzles` (41). The entire word list is sent to the browser — validation is client-side, so there are no per-word round-trips.

Puzzle rotation: `(START_INDEX + days_since_ROTATION_START) % 41`. `ROTATION_START = date(2026, 2, 24)`, `START_INDEX = 1`. The valid word list and max_score are computed lazily on first access and cached in `_PUZZLE_CACHE`. Blocking a word clears this cache and the word is excluded on the next compute.

### Frontend (SanakennoPage.vue)

- SVG honeycomb of 7 hexagons; keyboard input (letters / Backspace / Enter); click or tap to enter letters
- Browser tab title: `"Sanakenno — #N"` where N is the 1-indexed puzzle number
- Favicon swapped to an orange pointy-top hexagon SVG on mount; restored on unmount
- Touch zoom prevented: `touch-action: manipulation` on the root div; `touch-action: none` on the SVG to prevent scroll interpretation of hexagon taps

**State persistence**: `localStorage` key `sanakenno_state` stores `{puzzleNumber, foundWords[], score, hintsUnlocked[], startedAt}`. Restored on page load when puzzle numbers match. On restore, `foundWords` is filtered against the current puzzle's word list to discard blocked or stale words.

**Timer**: Tracks `startedAt` (epoch ms) plus `totalPausedMs` accumulated via `visibilitychange`, `blur`, and `pagehide` events.

**Animations**:
- Invalid submission triggers `word-shake` animation (0.4 s) on the input row
- Hexagons scale down on `pointerdown` for press feedback
- Rank-up notification ("Uusi taso: …!") shown for 3 seconds when score crosses a rank threshold
- Re-submit: already-found word flashes orange in the found words list for 1.5 s (`lastResubmittedWord` ref) alongside "Löysit jo tämän!"

**Progress bar**: Thin bar below the score/rank row; shows progress toward the next rank (`progressToNextRank` computed, animates via CSS transition).

**All-found banner**: When all words are found (`allFound` computed is true), "Kaikki N sanaa löydetty!" banner appears above the found words list.

### Hints (Avut)

Collapsible panel visible to all players. Four individually activatable hints; once unlocked they persist in `hintsUnlocked` in localStorage across sessions.

| ID | Icon | Label | Content |
|----|------|-------|---------|
| `summary` | 📊 | Yleiskuva | Line 1: remaining/total word count + % + remaining/total pangrams. Line 2: number of distinct word lengths + length of longest word. |
| `letters` | 🔤 | Alkukirjaimet | Remaining unfound words grouped by starting letter; fully-found letters shown muted at 0. |
| `distribution` | 📏 | Pituusjakauma | Word count per word length; remaining per length; fully-found lengths shown muted. |
| `pairs` | 🔠 | Alkuparit | Remaining unfound words grouped by first two letters; same muted display for fully-found pairs. |

### Share (Jaa tulos)

Button next to the Avut toggle. Copies a plain-text summary to the clipboard: puzzle number, current rank, score/max_score, and emoji icons for any activated hints. Shows "Kopioitu leikepöydälle!" confirmation briefly after copying.

### Admin Features

- **Puzzle switcher**: Admins see a 1-indexed number input and "Satunnainen" (random) button. Selected puzzle persists in `localStorage` under `sanakenno_admin_puzzle`. Confirmation requested only if there is existing progress to lose.
- **Center variation selector**: 7-column grid showing word count, max score, and pangram count for each possible center letter. Active center highlighted with accent color. Clicking a letter calls `POST /api/bee/center`.
- **Word blocking**: `AdminBlockedWords.vue` shows blocked words with timestamps and an unblock button. New words blocked via `AdminBeeStats.vue` form which calls `POST /api/bee/block`.

### OG Meta Tags

The `/sanakenno` Flask route in `routes.py` reads `index.html` and patches `<title>`, `description`, `og:title`, `og:description`, and `og:url` before serving, so link previews show a Finnish game description.

---

## Styling (Tailwind CSS v4)

CSS is built by the **`@tailwindcss/vite` plugin** — integrated into the Vite build pipeline.

### Build Pipeline

- **Input**: `frontend/src/style.css` (Tailwind directives + custom theme)
- **Output**: Bundled and minified CSS in `app/static/dist/` (via Vite build)
- **Dev**: Tailwind processes classes on-the-fly with HMR

### What's in `style.css`

- `@import "tailwindcss"` directive
- `@variant dark` directive for class-based dark mode
- `@theme` block with accent color, terminal colors, fonts
- `:root` and `.dark` blocks with warm stone color palette (CSS custom properties)
- Base layer: html/body styling with theme transitions
- Focus-visible styles scoped to interactive elements
- Skip-link utility (hidden until focused)
- `prefers-reduced-motion` media query
- Custom utility: `cursor-blink` animation for terminal cursor

### Color Palette

Warm stone greys that complement the orange accent:

| Token | Light | Dark |
|-------|-------|------|
| `--color-bg-page` | `#e7e5e4` | `#0c0a09` |
| `--color-bg-primary` | `#fafaf9` | `#1c1917` |
| `--color-bg-secondary` | `#f5f5f4` | `#292524` |
| `--color-bg-tertiary` | `#e7e5e4` | `#3a3632` |
| `--color-text-primary` | `#292524` | `#e7e5e4` |
| `--color-text-secondary` | `#78716c` | `#a8a29e` |
| `--color-text-tertiary` | `#a8a29e` | `#78716c` |
| `--color-border` | `#d6d3d1` | `#44403c` |

Shared across modes: accent `#ff643e`, terminal bg `#0a0a0a`, terminal user `#7eda28`, terminal dir `#6294cd`.

The `html` element uses `--color-bg-page` (a darker shade) while the `body` (max-width 960px centered) uses `--color-bg-primary`, creating a visual card effect.

### Design Tokens

Defined in `@theme` block:
- **Fonts**: DM Sans (body), Ubuntu Mono (terminal)
- **Colors**: `accent` (#ff643e), `term-bg`, `term-user`, `term-dir`
- **Layout**: max-width 960px, flexbox column

---

## Docker Setup

### Dockerfile (Multi-Stage Build)

```
Stage 1 (node:22-alpine):
  Copy frontend/ → npm ci → vite-ssg build → pre-rendered HTML + JS/CSS in app/static/dist/

Stage 2 (python:3.13-alpine):
  Install system deps → pip install → copy app + run.py
  Copy dist/ from Stage 1
  → gunicorn serves everything
```

The final image has no Node.js — only Python, the Flask app, and the pre-built frontend assets.

### docker-compose.yml

```yaml
services:
  web:
    build: .
    ports:
      - "127.0.0.1:8080:80"    # only accessible locally
    volumes:
      - ./app/data:/app/data    # SQLite DB persists on host
    restart: unless-stopped
```

- Port 8080 on localhost maps to port 80 in the container
- The `app/data` directory is mounted so the SQLite DB survives container rebuilds
- Nginx (outside this repo) reverse-proxies to port 8080 and handles SSL

---

## Development Workflow

```bash
# Terminal 1 — Flask API (port 5001)
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 run.py

# Terminal 2 — Vite dev server with HMR (port 5173)
cd frontend && npm run dev

# Open http://localhost:5173
```

Vite proxies `/api/*` and `/sitemap.xml` requests to Flask on port 5001.
Editing `.vue` files triggers instant Hot Module Replacement in the browser.

To build for production:
```bash
cd frontend && npm run build
# Output: app/static/dist/
```

To run tests:
```bash
python3 -m pytest tests/ -v
```

Tests use an in-memory SQLite database and disable rate limiting (`limiter.enabled = False`). No server required.

---

## Request Examples

**Homepage visit:**
```
GET / → 200 (index.html from dist/, ~1KB)
GET /assets/index-[hash].js → 200 (Vue app bundle, cached)
GET /assets/index-[hash].css → 200 (Tailwind compiled, cached)
GET /api/meta → 200 (JSON, ~80 bytes)
POST /api/pageview {"path": "/"} → 200 (JSON, count)
GET /api/cowsay → 200 (JSON, ~200 bytes, after 3s delay)
GET /api/weather → 200 (JSON, ~200 bytes, after cowsay completes)
```

**Navigate to /about (client-side):**
```
No page reload — Vue Router swaps the view
GET /api/sections → 200 (JSON, ~1KB)
```

**Navigate to /sanakenno (client-side):**
```
No page reload — Vue Router swaps the view
GET /api/bee → 200 (JSON with full word list, ~50KB)
POST /api/pageview {"path": "/sanakenno"} → 200
```

**Direct visit to /sanakenno:**
```
GET /sanakenno → 200 (index.html with patched OG meta tags)
GET /api/bee → 200
POST /api/pageview {"path": "/sanakenno"} → 200
```

**Navigate to /recipes (client-side, authenticated):**
```
No page reload — Vue Router swaps the view
GET /api/recipes → 200 (JSON array of recipes)
GET /api/recipes/categories → 200 (JSON array of strings)
```

**Direct visit to /about:**
```
GET /about → 200 (index.html — Flask catch-all, Vue Router renders AboutPage)
GET /api/meta → 200
GET /api/sections → 200
```

**Unknown page (e.g. /nonexistent):**
```
GET /nonexistent → 200 (index.html — Vue Router shows 404 component)
```

**Search engine crawler:**
```
GET /sitemap.xml → 200 (XML with lastmod date)
GET / → 200 (index.html — note: crawlers may not execute JS)
```

---

## Key Design Decisions

1. **Vite + vite-ssg** — Static site generation pre-renders public pages (`/`, `/about`, `/contact`, `/login`) at build time for SEO and fast first paint. Vue hydrates on top for interactivity. Protected/dynamic routes fall back to standard SPA client-side rendering.
2. **Vue SFCs** — Single File Components with `<script setup>`, scoped styles, and HMR for a modern dev experience
3. **Multi-page routing** — Vue Router with lazy-loaded views and `titleKey` meta resolved via i18n
4. **Class-based dark mode** — `.dark` on `<html>` with CSS custom properties, inline flash prevention script, localStorage persistence with system preference fallback
5. **Warm stone palette** — Tailwind stone greys with orange accent for a cohesive, non-stark color scheme
6. **Composables** — `useAuth`, `useDarkMode`, `useI18n`, `useNavLinks`, `usePageView`, `useTerminal` extract shared reactive state and logic as singletons, reusable across components
7. **Custom i18n** — Lightweight `useI18n` composable with JSON locale files (~90 keys) instead of vue-i18n (45KB+ for features not needed here)
8. **`@tailwindcss/vite` plugin** — CSS processing integrated into Vite, no standalone CLI needed
9. **Multi-stage Docker build** — Node runs `vite-ssg build` (pre-renders + bundles), final image is Python-only (no Node.js in production)
10. **Vue Router with catch-all Flask route** — client-side routing with clean URLs, Flask serves pre-rendered HTML or dist files, or falls back to `index.html` for non-SSG routes
11. **Loading/error states** — pulsing skeleton placeholders while fetching, error message if API fails, ARIA roles for screen readers
12. **DATABASE_URI env var** — allows local development without Docker by pointing to the local DB file
13. **GitHub API caching** — 6-hour TTL avoids rate limiting while keeping the "last updated" reasonably fresh
14. **Vite dev proxy** — Vite dev server proxies API requests to Flask at port 5001, enabling HMR during development
15. **Accessibility-first** — skip link, focus indicators, ARIA attributes, route announcer, reduced motion support
16. **Sanakenno: public, no auth** — the game is fully public; the word list is sent in full to the client; all validation is client-side. No per-guess API calls means no server load during gameplay.
17. **Section type system** — four types (`text`, `pills`, `quote`, `currently`) validated server-side, rendered client-side by `SectionBlock.vue`. Adding a new type requires changes in `routes.py` (validation), `SectionBlock.vue` (rendering), and `AdminSections.vue` (form dropdown).
18. **Page view dedup via session** — `POST /api/pageview` counts each path at most once per browser session, avoiding inflation from refreshes. The `PageView` table has one row per path; `count` is the total unique-session hit count.
19. **OG meta patching for Sanakenno** — the `/sanakenno` Flask route is a special case that reads and regex-patches `index.html` before serving, giving the game page distinct social link previews without a separate HTML template.
