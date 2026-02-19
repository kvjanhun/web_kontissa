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

Starts the Flask app on port 5000 (for local dev with Vite proxy).
Used by Gunicorn in production: `gunicorn -w 2 -b 0.0.0.0:80 run:app`

### `app/__init__.py` — App Factory

Creates the Flask app and wires everything together:

```python
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URI", "sqlite:////app/data/site.db"
)
```

- Default DB path is `/app/data/site.db` (inside the Docker container)
- For local dev, you override this with the `DATABASE_URI` env var
- Imports `routes`, `auth`, `recipes`, `api.cowsay`, and `api.weather` at the bottom, which registers all URL routes

### `app/models.py` — Database Models

Five models:

```python
class User(db.Model):     # username, email, password_hash, role
class Section(db.Model):  # slug, title, content (HTML), last_updated
class Recipe(db.Model):   # title, slug, category, created_by
class Ingredient(db.Model): # recipe_id, name, amount, unit, position
class Step(db.Model):      # recipe_id, content, position
```

Each model has a `to_dict()` method for JSON serialization. Recipe includes nested ingredients and steps.

### `app/routes.py` — Core Routes

| Route | What it does |
|---|---|
| `GET /` | Serves `index.html` from the Vite build output (`app/static/dist/`). |
| `GET /<path>` | Catch-all — serves static file from `dist/` if it exists, otherwise `index.html` for Vue Router. |
| `GET /api/sections` | Queries all Sections from SQLite, returns JSON array. |
| `POST/PUT/DELETE /api/sections` | Admin-only section CRUD. |
| `GET /api/meta` | Fetches last commit date from GitHub API, returns site metadata JSON. |
| `GET /sitemap.xml` | Dynamically generates XML sitemap for search engines. |

### `app/auth.py` — Authentication

| Route | What it does |
|---|---|
| `POST /api/login` | Validates email/password, starts Flask-Login session. |
| `POST /api/logout` | Ends session. |
| `GET /api/me` | Returns current user info or 401. |

Passwords are hashed with werkzeug scrypt. The `@admin_required` decorator wraps `@login_required` with a role check.

### `app/recipes.py` — Recipe CRUD

| Route | What it does |
|---|---|
| `GET /api/recipes` | List recipes with optional `?q=` search and `?category=` filter. |
| `GET /api/recipes/<slug>` | Single recipe with nested ingredients and steps. |
| `POST /api/recipes` | Create recipe with nested ingredients/steps arrays. |
| `PUT /api/recipes/<id>` | Update recipe (replaces all ingredients/steps). |
| `DELETE /api/recipes/<id>` | Delete recipe (cascades to ingredients/steps). |
| `GET /api/recipes/categories` | Returns list of valid categories. |

All recipe endpoints require `@login_required`. Any authenticated user can CRUD any recipe (shared cookbook model).

### `app/utils.py` — GitHub Commit Date

Fetches the latest commit date from `github.com/kvjanhun/web_kontissa`:

- Calls the GitHub API once, then **caches the result for 6 hours**
- Used by `/api/meta` to show "Last updated: YYYY-MM-DD" in the footer
- Falls back to cached value if the API call fails

### `app/api/cowsay.py` — Cowsay Endpoint

```
GET /api/cowsay → {"output": "  ___\n| moo |\n  ===\n   \\\n ..."}
```

Uses the Python `cowsay` library to generate ASCII art.
The terminal animation in the browser fetches this after "typing" the command.

### `app/api/weather.py` — Weather Endpoint

```
GET /api/weather → {"temperature": -12.4, "feels_like": -18.2, "wind_speed": 2.7, "condition": "Snow", ...}
```

Fetches real-time weather observations from the Finnish Meteorological Institute (FMI) open data WFS API for Helsinki-Vantaa airport (FMISID 100968):

- **XML parsing**: Extracts the latest non-NaN measurement for each parameter (`t2m`, `ws_10min`, `wawa`) from `omso:PointTimeSeriesObservation` elements
- **Wind chill**: Calculated server-side using the Environment Canada / NWS formula (applies when T ≤ 10°C and wind > 4.8 km/h)
- **Condition mapping**: WMO code table 4680 (automatic weather station present weather codes) mapped to human-readable strings in both English and Finnish
- **Caching**: Results cached for 10 minutes (matching FMI's update interval). Falls back to cached data if the API is down
- The terminal animation fetches this after the cowsay output, displaying temperature, wind chill, wind speed, and condition

---

## The Frontend (`frontend/`)

The frontend is a Vite + Vue 3 project using Single File Components (SFCs), with multi-page routing, dark/light mode, and EN/FI language support.

### Structure

```
frontend/
├── index.html              Vite entry point + dark mode flash prevention script
├── package.json            Dependencies: vue, vue-router, vite, tailwindcss
├── vite.config.js          Vite config with Vue plugin, Tailwind, Flask proxy
├── public/
│   └── favicon.ico         Static assets copied as-is
└── src/
    ├── main.js             App bootstrap: Vue app, router guards, i18n title updates
    ├── router.js           Vue Router: 10 routes with lazy loading + titleKey meta
    ├── style.css           Tailwind CSS + theme tokens + dark mode + focus styles + reduced motion
    ├── App.vue             Root layout: header, router-view, footer, skip link, route announcer
    ├── composables/
    │   ├── useAuth.js      Shared auth state (user, isAdmin, isAuthenticated, login, logout)
    │   ├── useDarkMode.js  Shared dark mode state + localStorage persistence
    │   └── useI18n.js      EN/FI i18n: locale ref, t(key, params), localStorage persistence
    ├── locales/
    │   ├── en.json         English translations (~90 keys)
    │   └── fi.json         Finnish translations
    ├── components/
    │   ├── AppHeader.vue       Sticky header, auth-aware nav, LangToggle, ThemeToggle, mobile menu
    │   ├── AppFooter.vue       Footer with last-updated date + quick links
    │   ├── ThemeToggle.vue     Sun/moon SVG button using useDarkMode composable
    │   ├── LangToggle.vue      EN/FI toggle button using useI18n composable
    │   ├── TerminalWindow.vue  Animated terminal with typing + cowsay + weather fetch
    │   └── SectionBlock.vue    Renders one content section (title + HTML body)
    └── views/
        ├── HomePage.vue        Hero layout: name, subtitle, terminal, CTA buttons
        ├── AboutPage.vue       Fetches /api/sections, renders SectionBlocks
        ├── ContactPage.vue     Static contact links: email, GitHub, LinkedIn
        ├── LoginPage.vue       Auth form wired to backend, or logged-in state
        ├── AdminPage.vue       Protected section CRUD (add/edit/delete)
        ├── RecipeListPage.vue  Recipe cards with search + category filter
        ├── RecipeDetailPage.vue Single recipe with wake lock + step checkboxes
        ├── RecipeFormPage.vue  Create/edit recipe with dynamic ingredient/step rows
        └── NotFound.vue        404 page with accent styling
```

### Routing

Vue Router manages ten routes with lazy loading for non-home views:

| Route | View | Content |
|-------|------|---------|
| `/` | HomePage | Hero with terminal animation + CTA buttons |
| `/about` | AboutPage | Sections fetched from `/api/sections` |
| `/contact` | ContactPage | Static email, GitHub, LinkedIn links |
| `/login` | LoginPage | Auth form or logged-in state with logout |
| `/admin` | AdminPage | Protected section CRUD (requires admin) |
| `/recipes` | RecipeListPage | Recipe cards with search + filter (requires auth) |
| `/recipes/new` | RecipeFormPage | Create new recipe (requires auth) |
| `/recipes/:slug` | RecipeDetailPage | Single recipe view (requires auth) |
| `/recipes/:slug/edit` | RecipeFormPage | Edit existing recipe (requires auth) |
| `*` | NotFound | 404 with accent styling |

Routes use `titleKey` meta (e.g., `'title.about'`) resolved via `t()` in `main.js` `afterEach`, so page titles update with the current language. Auth guards in `beforeEach` redirect unauthenticated users to `/login`.

### How Vue Renders the Page

1. Browser loads `index.html` — a minimal shell with `<div id="app">`
2. An inline `<script>` in `<head>` synchronously sets `.dark` on `<html>` based on localStorage or system preference (prevents flash of wrong theme)
3. Vite-bundled JS loads (includes Vue, Vue Router, all components)
4. `main.js` creates the app, registers the router, and mounts to `#app`
5. The root `App.vue` runs `onMounted`:
   - Calls `checkAuth()` to restore session state
   - Fetches `/api/meta` for footer update date
   - Vue automatically re-renders when data arrives
6. Vue Router matches the current URL and renders the corresponding view
7. Components render:
   - **AppHeader** — sticky nav with auth-aware links, LangToggle (EN/FI), ThemeToggle (sun/moon), mobile hamburger with Escape-to-close
   - **HomePage** — hero layout with name/subtitle, TerminalWindow (typing animation + cowsay + weather), and CTA buttons
   - **AboutPage** — fetches `/api/sections`, shows loading skeleton or error state, then renders SectionBlocks
   - **ContactPage** — static links to email, GitHub, LinkedIn
   - **LoginPage** — email/password form wired to `/api/login`, or logged-in state with logout button
   - **AdminPage** — section CRUD with add/edit/delete (admin only)
   - **RecipeListPage** — recipe cards with debounced search and category filter
   - **RecipeDetailPage** — single recipe with ingredients, interactive step checkboxes, screen wake lock
   - **RecipeFormPage** — create/edit form with dynamic ingredient and step rows
   - **AppFooter** — last-updated date + quick links to About and Contact

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
7. **Not translated**: terminal prompt, brand names (`erez.ac`), API content, Schema.org JSON-LD

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
- **Reduced motion**: `prefers-reduced-motion` media query disables all animations and transitions
- **Color contrast**: all text meets WCAG AA (4.5:1 minimum)

### Loading & Error States

Views that fetch data track their own loading and error state:
- `loading` (boolean) — `true` while the API request is in-flight, with `role="status"` for screen readers
- `error` (string/object) — set if the fetch fails, with `role="alert"` for screen readers

AboutPage shows pulsing skeleton placeholders while loading. Recipe pages show text loading indicators. Error states show red-tinted messages.

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
  Copy frontend/ → npm ci → npm run build → output in app/static/dist/

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
# Terminal 1 — Flask API (port 5000)
cd web_kontissa
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 run.py

# Terminal 2 — Vite dev server with HMR (port 5173)
cd web_kontissa/frontend
npm run dev

# Open http://localhost:5173
```

Vite proxies `/api/*` and `/sitemap.xml` requests to Flask on port 5000.
Editing `.vue` files triggers instant Hot Module Replacement in the browser.

To build for production:
```bash
cd frontend && npm run build
# Output: app/static/dist/
```

---

## Request Examples

**Homepage visit:**
```
GET / → 200 (index.html from dist/, ~1KB)
GET /assets/index-[hash].js → 200 (Vue app bundle, cached)
GET /assets/index-[hash].css → 200 (Tailwind compiled, cached)
GET /api/meta → 200 (JSON, ~80 bytes)
GET /api/cowsay → 200 (JSON, ~200 bytes, after 3s delay)
GET /api/weather → 200 (JSON, ~200 bytes, after cowsay completes)
```

**Navigate to /about (client-side):**
```
No page reload — Vue Router swaps the view
GET /api/sections → 200 (JSON, ~1KB)
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

1. **Vite + Vue SFCs** — Single File Components with `<script setup>`, scoped styles, and HMR for a modern dev experience
2. **Multi-page routing** — Vue Router with lazy-loaded views and `titleKey` meta resolved via i18n
3. **Class-based dark mode** — `.dark` on `<html>` with CSS custom properties, inline flash prevention script, localStorage persistence with system preference fallback
4. **Warm stone palette** — Tailwind stone greys with orange accent for a cohesive, non-stark color scheme
5. **Composables** — `useAuth`, `useDarkMode`, `useI18n` extract shared reactive state as singletons, reusable across components
6. **Custom i18n** — Lightweight `useI18n` composable with JSON locale files (~90 keys) instead of vue-i18n (45KB+ for features not needed)
7. **`@tailwindcss/vite` plugin** — CSS processing integrated into Vite, no standalone CLI needed
8. **Multi-stage Docker build** — Node builds the frontend, final image is Python-only (no Node.js in production)
9. **Vue Router with catch-all Flask route** — client-side routing with clean URLs, Flask serves dist files or falls back to index.html
10. **Loading/error states** — pulsing skeleton placeholders while fetching, error message if API fails, ARIA roles for screen readers
11. **DATABASE_URI env var** — allows local development without Docker by pointing to the local DB file
12. **GitHub API caching** — 6-hour TTL avoids rate limiting while keeping the "last updated" reasonably fresh
13. **Vite dev proxy** — Vite dev server proxies API requests to Flask, enabling HMR during development
14. **Accessibility-first** — skip link, focus indicators, ARIA attributes, route announcer, reduced motion support
