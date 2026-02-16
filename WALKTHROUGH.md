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
  |                                 |                              |
  |  GET /api/meta --------------->|  fetch GitHub API (cached)   |
  |  <-- JSON {update_date, ...}   |                              |
  |                                 |                              |
  |  GET /api/cowsay -------------->|  cowsay.get_output_string()  |
  |  <-- JSON {output: "..."}      |                              |
  |                                 |                              |
  |  Navigate to /about:           |                              |
  |  GET /api/sections ----------->|  SELECT * FROM section       |
  |  <-- JSON [{slug, title, ...}] |<-----------------------------|
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
- Imports `routes` and `api.cowsay` at the bottom, which registers all URL routes

### `app/models.py` — Database Model

One model, one table:

```python
class Section(db.Model):
    id          # primary key
    slug        # URL-friendly name: "who", "what", "where"
    title       # display name: "Who", "What", "Where"
    content     # HTML content (rendered with v-html in Vue)
    last_updated
```

The `to_dict()` method converts a Section to a JSON-friendly dictionary.
This is what the `/api/sections` endpoint returns.

### `app/routes.py` — URL Routes

Six routes:

| Route | What it does |
|---|---|
| `GET /` | Serves `index.html` from the Vite build output (`app/static/dist/`). |
| `GET /<path>` | Catch-all — serves static file from `dist/` if it exists, otherwise `index.html` for Vue Router. |
| `GET /api/sections` | Queries all Sections from SQLite, returns JSON array via `to_dict()`. |
| `GET /api/meta` | Fetches last commit date from GitHub API, returns site metadata JSON. |
| `GET /index.html` | 301 redirect to `/` (legacy support). |
| `GET /sitemap.xml` | Dynamically generates XML sitemap for search engines. |

The cowsay route (`GET /api/cowsay`) lives separately in `app/api/cowsay.py`.

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

---

## The Frontend (`frontend/`)

The frontend is a Vite + Vue 3 project using Single File Components (SFCs), with multi-page routing and dark/light mode.

### Structure

```
frontend/
├── index.html              Vite entry point + dark mode flash prevention script
├── package.json            Dependencies: vue, vue-router, vite, tailwindcss
├── vite.config.js          Vite config with Vue plugin, Tailwind, Flask proxy
├── public/
│   └── favicon.ico         Static assets copied as-is
└── src/
    ├── main.js             App bootstrap: creates Vue app, adds router, mounts
    ├── router.js           Vue Router: 5 routes with lazy loading + title updates
    ├── style.css           Tailwind CSS + warm stone theme tokens + dark mode
    ├── App.vue             Root layout shell: header, router-view, footer
    ├── composables/
    │   └── useDarkMode.js  Shared reactive dark mode state + localStorage persistence
    ├── components/
    │   ├── AppHeader.vue       Sticky header with route links, ThemeToggle, mobile hamburger
    │   ├── AppFooter.vue       Footer with last-updated date + quick links
    │   ├── ThemeToggle.vue     Sun/moon SVG button using useDarkMode composable
    │   ├── TerminalWindow.vue  Animated terminal with typing + cowsay fetch
    │   └── SectionBlock.vue    Renders one content section (title + HTML body)
    └── views/
        ├── HomePage.vue    Hero layout: name, subtitle, centered terminal, CTA buttons
        ├── AboutPage.vue   Fetches /api/sections, renders SectionBlocks
        ├── ContactPage.vue Static contact links: email, GitHub, LinkedIn
        ├── LoginPage.vue   Form UI (email + password, no backend)
        └── NotFound.vue    404 page with accent styling
```

### Routing

Vue Router manages five routes with lazy loading for non-home views:

| Route | View | Content |
|-------|------|---------|
| `/` | HomePage | Hero with terminal animation + CTA buttons |
| `/about` | AboutPage | Sections fetched from `/api/sections` |
| `/contact` | ContactPage | Static email, GitHub, LinkedIn links |
| `/login` | LoginPage | Form UI (logs to console, no backend) |
| `*` | NotFound | 404 with accent styling |

`router.afterEach` updates `document.title` from route `meta.title`. `scrollBehavior` scrolls to top on navigation.

### How Vue Renders the Page

1. Browser loads `index.html` — a minimal shell with `<div id="app">`
2. An inline `<script>` in `<head>` synchronously sets `.dark` on `<html>` based on localStorage or system preference (prevents flash of wrong theme)
3. Vite-bundled JS loads (includes Vue, Vue Router, all components)
4. `main.js` creates the app, registers the router, and mounts to `#app`
5. The root `App.vue` runs `onMounted`:
   - Fetches `/api/meta` for footer update date
   - Vue automatically re-renders when data arrives
6. Vue Router matches the current URL and renders the corresponding view
7. Components render:
   - **AppHeader** — sticky nav with static route links, ThemeToggle button, mobile hamburger menu
   - **HomePage** — hero layout with name/subtitle, TerminalWindow (typing animation + cowsay), and CTA buttons
   - **AboutPage** — fetches `/api/sections`, shows loading skeleton or error state, then renders SectionBlocks
   - **ContactPage** — static links to email, GitHub, LinkedIn
   - **LoginPage** — email/password form (submit logs to console)
   - **AppFooter** — last-updated date + quick links to About and Contact

### Dark Mode

Dark mode uses a class-based approach:

1. **Flash prevention**: inline `<script>` in `index.html` `<head>` checks localStorage then `prefers-color-scheme` and sets `.dark` on `<html>` synchronously before CSS loads
2. **Composable** (`useDarkMode.js`): shared reactive `isDark` ref, persists to localStorage, toggles `.dark` class on `<html>`
3. **CSS custom properties**: `:root` and `.dark` blocks in `style.css` define all theme tokens
4. **`@variant dark`**: Tailwind v4 directive enables `dark:` variant based on `.dark` class
5. **ThemeToggle.vue**: sun/moon SVG button that calls `toggleDark()` from the composable

### Loading & Error States

The AboutPage tracks its own loading and error state:
- `loading` (boolean) — `true` while `/api/sections` is in-flight
- `error` (object) — set if the fetch fails

While loading, pulsing placeholder skeletons are shown. On error, a message box with "Failed to load content" appears.
The terminal component handles its own error state independently.

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
```

**Navigate to /about (client-side):**
```
No page reload — Vue Router swaps the view
GET /api/sections → 200 (JSON, ~1KB)
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
2. **Multi-page routing** — Vue Router with lazy-loaded views for About, Contact, Login; `afterEach` hook updates document title
3. **Class-based dark mode** — `.dark` on `<html>` with CSS custom properties, inline flash prevention script, localStorage persistence with system preference fallback
4. **Warm stone palette** — Tailwind stone greys with orange accent for a cohesive, non-stark color scheme
5. **Composables** — `useDarkMode` extracts shared reactive state, reusable across components
6. **`@tailwindcss/vite` plugin** — CSS processing integrated into Vite, no standalone CLI needed
7. **Multi-stage Docker build** — Node builds the frontend, final image is Python-only (no Node.js in production)
8. **Vue Router with catch-all Flask route** — client-side routing with clean URLs, Flask serves dist files or falls back to index.html
9. **Loading/error states** — pulsing skeleton placeholders while fetching, error message if API fails
10. **DATABASE_URI env var** — allows local development without Docker by pointing to the local DB file
11. **GitHub API caching** — 6-hour TTL avoids rate limiting while keeping the "last updated" reasonably fresh
12. **Vite dev proxy** — Vite dev server proxies API requests to Flask, enabling HMR during development
