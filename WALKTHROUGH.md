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
  |  Vue + Router mount, fires:    |                              |
  |                                 |                              |
  |  GET /api/sections ----------->|  SELECT * FROM section       |
  |  <-- JSON [{slug, title, ...}] |<-----------------------------|
  |                                 |                              |
  |  GET /api/meta --------------->|  fetch GitHub API (cached)   |
  |  <-- JSON {update_date, ...}   |                              |
  |                                 |                              |
  |  GET /api/cowsay -------------->|  cowsay.get_output_string()  |
  |  <-- JSON {output: "..."}      |                              |
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

The frontend is a Vite + Vue 3 project using Single File Components (SFCs).

### Structure

```
frontend/
├── index.html              Vite entry point (minimal HTML shell)
├── package.json            Dependencies: vue, vue-router, vite, tailwindcss
├── vite.config.js          Vite config with Vue plugin, Tailwind, Flask proxy
├── public/
│   └── favicon.ico         Static assets copied as-is
└── src/
    ├── main.js             App bootstrap: creates Vue app, adds router, mounts
    ├── router.js           Vue Router config: / → HomePage, * → NotFound
    ├── style.css           Tailwind CSS with custom theme and utilities
    ├── App.vue             Root layout: header, router-view, footer + data fetching
    ├── components/
    │   ├── AppHeader.vue   Top bar with site name + nav links (fetched from API)
    │   ├── AppFooter.vue   Bottom bar with last updated date
    │   ├── TerminalWindow.vue  Animated terminal with typing + cowsay
    │   └── SectionBlock.vue    Renders one content section
    └── views/
        ├── HomePage.vue    Home route: terminal + sections + loading/error states
        └── NotFound.vue    404 page for unknown routes
```

### How Vue Renders the Page

1. Browser loads `index.html` — a minimal shell with `<div id="app">`
2. Vite-bundled JS loads (includes Vue, Vue Router, all components)
3. `main.js` creates the app, registers the router, and mounts to `#app`
4. The root `App.vue`'s `setup()` runs `onMounted`:
   - Fetches `/api/sections` and `/api/meta` in parallel
   - On success: stores results in reactive `ref()` variables
   - On failure: sets `error` ref
   - Vue automatically re-renders when these change
5. Vue Router matches the current URL:
   - `/` → **HomePage** component (terminal + sections)
   - Any other path → **NotFound** component (404 page)
6. Components render:
   - **AppHeader** fetches `/api/sections` to build nav links
   - **HomePage** shows loading skeleton while data fetches, error state if it fails, or sections when ready
   - **TerminalWindow** waits 3 seconds, then "types" `cowsay moo` character by character, fetches `/api/cowsay`, and displays the output
   - **SectionBlock** renders each section's title + HTML content
   - **AppFooter** shows the last updated date from metadata

### Loading & Error States

The app tracks two reactive values:
- `loading` (boolean) — `true` while API calls are in-flight
- `error` (object) — set if `Promise.all` rejects

While loading, the HomePage shows pulsing placeholder skeletons (3 blocks).
On error, it shows a red-tinted message box: "Failed to load content. Please try refreshing."
The terminal component handles its own error state independently.

---

## Styling (Tailwind CSS)

CSS is built by the **`@tailwindcss/vite` plugin** — integrated into the Vite build pipeline.

### Build Pipeline

- **Input**: `frontend/src/style.css` (Tailwind directives + custom theme)
- **Output**: Bundled and minified CSS in `app/static/dist/` (via Vite build)
- **Dev**: Tailwind processes classes on-the-fly with HMR

### What's in `style.css`

- `@import "tailwindcss"` directive
- `@theme` block with custom colors, fonts
- Base layer: body font, link styles
- Custom utilities: terminal-specific CSS (window chrome, prompt colors, cursor blink animation)

### Design Tokens

Defined in `@theme` block in `style.css`:
- **Fonts**: DM Sans (body), Ubuntu Mono (terminal)
- **Colors**: `dark` (#333), `light` (#f9f9f9), `accent` (rgb(255, 100, 62))
- **Terminal**: `term-bg`, `term-user`, `term-dir`
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
GET /api/sections → 200 (JSON, ~1KB)
GET /api/meta → 200 (JSON, ~80 bytes)
GET /api/cowsay → 200 (JSON, ~200 bytes, after 3s delay)
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
2. **`@tailwindcss/vite` plugin** — CSS processing integrated into Vite, no standalone CLI needed
3. **Multi-stage Docker build** — Node builds the frontend, final image is Python-only (no Node.js in production)
4. **Vue Router with catch-all Flask route** — client-side routing with clean URLs, Flask serves dist files or falls back to index.html
5. **Loading/error states** — pulsing skeleton placeholders while fetching, error message if API fails
6. **DATABASE_URI env var** — allows local development without Docker by pointing to the local DB file
7. **Parallel API fetches** — sections and metadata load simultaneously for faster page render
8. **GitHub API caching** — 6-hour TTL avoids rate limiting while keeping the "last updated" reasonably fresh
9. **Vite dev proxy** — Vite dev server proxies API requests to Flask, enabling HMR during development
