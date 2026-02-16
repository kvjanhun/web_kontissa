# [erez.ac](https://erez.ac)

Personal portfolio website by Konsta Janhunen.

## Stack

- **Frontend**: Vue.js 3 SFCs + Vite + Tailwind CSS v4
- **Backend**: Flask (Python) with JSON API endpoints
- **Database**: SQLite via Flask-SQLAlchemy
- **Server**: Gunicorn (production), Flask dev server (local)
- **Deployment**: Docker Compose (multi-stage build), auto-deployed via GitHub webhook

Multi-page Vue app with client-side routing, dark/light mode with warm stone-orange theme, and a terminal animation on the home page. Vue Router handles five routes (`/`, `/about`, `/contact`, `/login`, `404`). Data is fetched from Flask API endpoints (`/api/sections`, `/api/meta`, `/api/cowsay`). Vite builds the frontend into static assets that Flask serves in production.

## History

The site was originally built with Flask + Jinja2 server-rendered templates + vanilla JavaScript, with ChatGPT 4o used for roadmap advice and templates.

In February 2026, the frontend was migrated to Vue.js 3 with a hybrid CDN/local approach. This migration was carried out by Claude (Anthropic), orchestrated by Konsta. The Jinja2 templates were replaced with Vue components, Flask routes were converted to JSON API endpoints, and the terminal animation was rewritten as a Vue component.

Later in February 2026, the frontend was migrated again to Vite + Vue Single File Components. The inline `<script>` with JS string templates was replaced by `.vue` SFCs with `<script setup>`, the Tailwind standalone CLI was replaced by the `@tailwindcss/vite` plugin, and the Dockerfile was rewritten as a multi-stage build (Node + Python).

The site was then reworked into a multi-page layout with Vue Router, dark/light mode toggle, and a warm stone-orange color palette. The terminal was simplified from Ubuntu window chrome to a plain dark terminal. New pages were added for About, Contact, and Login.

## Project Structure

```
web_kontissa/
├── Dockerfile              # Multi-stage: Node builds frontend, Python runs app
├── README.md
├── WALKTHROUGH.md
├── docker-compose.yml
├── requirements.txt
├── run.py                  # Flask entry point (port 5000 for dev)
├── frontend/               # Vite + Vue 3 SFC project
│   ├── index.html          # Vite entry point + dark mode flash prevention
│   ├── package.json
│   ├── vite.config.js      # Vue plugin, Tailwind, Flask proxy
│   ├── public/
│   │   └── favicon.ico
│   └── src/
│       ├── main.js         # App bootstrap
│       ├── router.js       # Vue Router: 5 routes with lazy loading
│       ├── style.css       # Tailwind CSS + warm stone theme + dark mode
│       ├── App.vue         # Root layout shell (header, router-view, footer)
│       ├── composables/
│       │   └── useDarkMode.js  # Shared dark mode state + localStorage
│       ├── components/
│       │   ├── AppHeader.vue       # Sticky nav, route links, theme toggle, mobile menu
│       │   ├── AppFooter.vue       # Footer with quick links
│       │   ├── ThemeToggle.vue     # Sun/moon dark mode toggle button
│       │   ├── TerminalWindow.vue  # Animated terminal with typing + cowsay
│       │   └── SectionBlock.vue    # Renders one content section
│       └── views/
│           ├── HomePage.vue    # Hero: name, terminal, CTA buttons
│           ├── AboutPage.vue   # Sections fetched from API
│           ├── ContactPage.vue # Email, GitHub, LinkedIn links
│           ├── LoginPage.vue   # Form UI (no backend)
│           └── NotFound.vue    # 404 page
└── app/                    # Flask backend
    ├── __init__.py
    ├── routes.py           # Serves dist/ + API routes
    ├── models.py
    ├── utils.py
    ├── api/
    │   ├── __init__.py
    │   └── cowsay.py
    ├── data/
    │   └── site.db
    └── static/
        ├── favicon.ico
        └── dist/           # Vite build output (gitignored)
```

## Running Locally

### With Docker

```bash
docker compose up --build -d
```

Then visit: [http://localhost:8080](http://localhost:8080)

### Without Docker (development)

```bash
# Terminal 1 — Flask API
cd web_kontissa
pip install flask flask-sqlalchemy cowsay requests
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 run.py

# Terminal 2 — Vite dev server with HMR
cd web_kontissa/frontend
npm install
npm run dev
```

Then visit: [http://localhost:5173](http://localhost:5173)

Vite proxies `/api/*` requests to Flask on port 5000.

### Production build (without Docker)

```bash
cd frontend && npm run build
# Output: app/static/dist/
# Then start Flask: python3 run.py (serves from dist/)
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Serves the Vue app (from `app/static/dist/`) |
| `GET /api/sections` | Returns all content sections as JSON |
| `GET /api/meta` | Returns site metadata (update date, author) |
| `GET /api/cowsay` | Returns cowsay ASCII art as JSON |
| `GET /sitemap.xml` | XML sitemap for SEO |
| `GET /index.html` | 301 redirect to `/` |

## Configuration

No external `.env` file required. The SQLite database is at `/app/data/site.db` (container path). For local development, set the `DATABASE_URI` environment variable to point to the local database.

## Production Notes

- Multi-stage Docker build: Node builds the frontend, final image is Python-only
- Gunicorn is used as the WSGI server inside the container
- The Flask app binds to `0.0.0.0:80` in production
- Nginx and SSL termination (Let's Encrypt) are configured outside this repo
- Changes pushed to GitHub are automatically deployed via webhook

## Author

Konsta Janhunen
[erez.ac](https://erez.ac)
