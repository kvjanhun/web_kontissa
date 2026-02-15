# How erez.ac Works — A Walkthrough

This document walks through the entire request lifecycle of erez.ac,
from a visitor opening the site to content appearing on screen.

---

## The Big Picture

```
Browser                         Server (Flask)                  Database
  |                                 |                              |
  |  GET /                          |                              |
  |------------------------------->|                              |
  |  <-- index.html (Vue app)      |                              |
  |                                 |                              |
  |  Load vue.global.js            |                              |
  |  (local static file)           |                              |
  |                                 |                              |
  |  Vue mounts, fires API calls:  |                              |
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
1. **Server sends the HTML shell** — a mostly empty page with Vue.js
2. **Vue takes over in the browser** — fetches data via API, renders everything

---

## File by File

### `run.py` — Entry Point

The simplest file. Just starts the Flask app on port 80.
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

Five routes:

| Route | What it does |
|---|---|
| `GET /` | Returns `index.html` (the Vue app). No data passed — Vue fetches everything. |
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

## The Frontend (index.html)

This is where most of the action happens. The file is a single HTML page
that contains the entire Vue 3 application inline.

### Structure

```
index.html
├── <head>          Meta tags, CSS, JSON-LD schema
├── <div id="app">  Empty mount point for Vue
├── <script>        vue.global.js (Vue 3 runtime, served locally)
└── <script>        The Vue app code:
    ├── AppHeader       — top bar with site name + nav links
    ├── TerminalWindow  — animated terminal with cowsay
    ├── SectionBlock    — renders one content section
    ├── AppFooter       — bottom bar with last updated date
    └── Root app        — ties components together, fetches API data
```

### How Vue Renders the Page

1. Browser loads `index.html` — sees only `<div id="app"></div>` (empty)
2. Vue.js loads from `/static/script/vue.global.js`
3. The inline `<script>` defines 4 components and creates the app
4. `app.mount('#app')` — Vue takes over the empty div
5. The root app's `setup()` runs `onMounted`:
   - Fetches `/api/sections` and `/api/meta` in parallel
   - Stores results in reactive `ref()` variables
   - Vue automatically re-renders when these change
6. Components render:
   - **AppHeader** also fetches `/api/sections` to build nav links
   - **TerminalWindow** waits 3 seconds, then "types" `cowsay moo` character by character, fetches `/api/cowsay`, and displays the output
   - **SectionBlock** renders each section's title + HTML content
   - **AppFooter** shows the last updated date from metadata

### Jinja2 Escaping

Since Flask still processes the HTML through Jinja2, Vue's `{{ }}` syntax
would conflict. The template uses `{% raw %}...{% endraw %}` around Vue
mustache expressions so Jinja passes them through untouched.

### Component Templates

Each component's HTML template is defined as a JavaScript string (using
`.join('\n')` on an array of lines). This avoids in-DOM template parsing
issues across browsers (notably Safari) and keeps all rendering logic in JS.

---

## Styling (style.css)

The CSS defines the visual layout:

- **Fonts**: DM Sans (body), Ubuntu Mono (terminal)
- **Layout**: Flexbox column — `.top` (header), `.mid` (content), `.bottom` (footer)
- **Colors**: Dark header/footer (#333), white content, orange accent (rgb(255, 100, 62))
- **Terminal**: Dark purple background, green username, blue directory path, blinking cursor
- **Responsive**: Hides subtitle on narrow screens (<600px), centers content on wide screens (>960px)
- **Transitions**: Fade-in animation for sections loading from API

---

## Docker Setup

### Dockerfile

```
python:3.13-alpine  →  install build deps  →  pip install  →  gunicorn
```

Lightweight Alpine image. Gunicorn runs 2 workers on port 80.

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

## Request Examples

**Homepage visit:**
```
GET / → 200 (index.html, ~5KB)
GET /static/script/vue.global.js → 200 (158KB, cached by browser)
GET /static/assets/style.css → 200 (cached)
GET /api/sections → 200 (JSON, ~1KB)
GET /api/meta → 200 (JSON, ~80 bytes)
GET /api/cowsay → 200 (JSON, ~200 bytes, after 3s delay)
```

**Search engine crawler:**
```
GET /sitemap.xml → 200 (XML with lastmod date)
GET / → 200 (index.html — note: crawlers may not execute JS)
```

---

## Key Design Decisions

1. **Vue via local file, no build step** — keeps deployment simple (no Node.js needed), Dockerfile stays minimal
2. **Templates in JavaScript strings** — avoids browser HTML parser mangling custom elements (Safari issue)
3. **Jinja2 `{% raw %}` blocks** — prevents conflict between Jinja's `{{ }}` and Vue's `{{ }}`
4. **DATABASE_URI env var** — allows local development without Docker by pointing to the local DB file
5. **Parallel API fetches** — sections and metadata load simultaneously for faster page render
6. **GitHub API caching** — 6-hour TTL avoids rate limiting while keeping the "last updated" reasonably fresh
