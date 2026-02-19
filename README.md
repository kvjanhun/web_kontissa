# [erez.ac](https://erez.ac)

Personal portfolio website by Konsta Janhunen.

## Stack

- **Frontend**: Vue.js 3 SFCs + Vite + Tailwind CSS v4
- **Backend**: Flask (Python) with JSON API endpoints
- **Database**: SQLite via Flask-SQLAlchemy
- **Auth**: Flask-Login with session cookies
- **Server**: Gunicorn (production), Flask dev server (local)
- **Deployment**: Docker Compose (multi-stage build), auto-deployed via GitHub webhook

Multi-page Vue app with client-side routing, dark/light mode with warm stone-orange theme, EN/FI language support, and a terminal animation on the home page. Vue Router handles ten routes (`/`, `/about`, `/contact`, `/login`, `/admin`, `/recipes`, `/recipes/new`, `/recipes/:slug`, `/recipes/:slug/edit`, `404`). Data is fetched from Flask API endpoints. Session-based authentication via Flask-Login allows the admin to manage content sections through a protected admin panel, and authenticated users can manage a shared recipe book.

## History

The site was originally built with Flask + Jinja2 server-rendered templates + vanilla JavaScript, with ChatGPT 4o used for roadmap advice and templates.

In February 2026, the frontend was migrated to Vue.js 3 with a hybrid CDN/local approach. This migration was carried out by Claude (Anthropic), orchestrated by Konsta. The Jinja2 templates were replaced with Vue components, Flask routes were converted to JSON API endpoints, and the terminal animation was rewritten as a Vue component.

Later in February 2026, the frontend was migrated again to Vite + Vue Single File Components. The inline `<script>` with JS string templates was replaced by `.vue` SFCs with `<script setup>`, the Tailwind standalone CLI was replaced by the `@tailwindcss/vite` plugin, and the Dockerfile was rewritten as a multi-stage build (Node + Python).

The site was then reworked into a multi-page layout with Vue Router, dark/light mode toggle, and a warm stone-orange color palette. The terminal was simplified from Ubuntu window chrome to a plain dark terminal. New pages were added for About, Contact, and Login.

Session-based authentication was added with Flask-Login, along with an admin panel for managing database sections (add, edit, delete) through the website. The login page was wired to the backend and the header was made auth-aware.

A shared recipe book was added for authenticated users, with full CRUD, search, category filtering, slug-based URLs, and a cooking mode with screen wake lock and step checkboxes.

English/Finnish language support was added via a custom `useI18n` composable with JSON locale files. Language defaults to browser locale and persists in localStorage.

Accessibility improvements were added: skip-to-content link, keyboard focus indicators, ARIA attributes on interactive elements, screen reader announcements for route changes and dynamic content, and `prefers-reduced-motion` support.

Real-time weather data from the Finnish Meteorological Institute (FMI) open data API was added to the terminal animation. After the cowsay output, the terminal types a `weather` command and displays current temperature, wind chill, wind speed, and weather condition for Helsinki-Vantaa. The backend fetches from the FMI WFS API, parses the XML response, calculates wind chill, maps WMO wawa codes (table 4680) to human-readable conditions in English and Finnish, and caches results for 10 minutes.

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
│       ├── main.js         # App bootstrap, auth guards, i18n title updates
│       ├── router.js       # Vue Router: 10 routes with lazy loading
│       ├── style.css       # Tailwind CSS + warm stone theme + dark mode + a11y
│       ├── App.vue         # Root layout: header, router-view, footer, skip link, route announcer
│       ├── composables/
│       │   ├── useAuth.js       # Auth state, login/logout/checkAuth
│       │   ├── useDarkMode.js   # Shared dark mode state + localStorage
│       │   └── useI18n.js       # EN/FI i18n: locale ref, t() function, localStorage
│       ├── locales/
│       │   ├── en.json          # English translations (~90 keys)
│       │   └── fi.json          # Finnish translations
│       ├── components/
│       │   ├── AppHeader.vue       # Sticky nav, auth-aware links, LangToggle, mobile menu
│       │   ├── AppFooter.vue       # Footer with last-updated date + quick links
│       │   ├── ThemeToggle.vue     # Sun/moon dark mode toggle button
│       │   ├── LangToggle.vue      # EN/FI language toggle button
│       │   ├── TerminalWindow.vue  # Animated terminal with typing + cowsay + weather
│       │   └── SectionBlock.vue    # Renders one content section
│       └── views/
│           ├── HomePage.vue        # Hero: name, terminal, CTA buttons
│           ├── AboutPage.vue       # Sections fetched from API
│           ├── ContactPage.vue     # Email, GitHub, LinkedIn links
│           ├── LoginPage.vue       # Auth form, wired to backend
│           ├── AdminPage.vue       # Protected section CRUD
│           ├── RecipeListPage.vue  # Recipe cards with search + category filter
│           ├── RecipeDetailPage.vue # Single recipe with wake lock + step checkboxes
│           ├── RecipeFormPage.vue  # Create/edit recipe form
│           └── NotFound.vue        # 404 page
└── app/                    # Flask backend
    ├── __init__.py
    ├── routes.py           # Serves dist/ + API routes + section CRUD
    ├── auth.py             # Login/logout/me endpoints
    ├── recipes.py          # Recipe CRUD, search, category filter
    ├── models.py           # User, Section, Recipe, Ingredient, Step models
    ├── create_admin.py     # Utility to create admin user
    ├── utils.py            # GitHub API commit date with caching
    ├── api/
    │   ├── cowsay.py
    │   └── weather.py          # FMI weather data with caching
    ├── data/
    │   └── site.db
    └── static/
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
pip install flask flask-sqlalchemy flask-login cowsay requests
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
| `GET /<path>` | Catch-all: static file from dist/ or index.html for Vue Router |
| `GET /api/sections` | Returns all content sections as JSON |
| `POST /api/sections` | Create section (admin) |
| `PUT /api/sections/<id>` | Update section (admin) |
| `DELETE /api/sections/<id>` | Delete section (admin) |
| `POST /api/login` | Authenticate user, start session |
| `POST /api/logout` | End session |
| `GET /api/me` | Current user info (or 401) |
| `GET /api/meta` | Returns site metadata (update date, author) |
| `GET /api/recipes?q=&category=` | List recipes with optional search + category filter (auth) |
| `GET /api/recipes/<slug>` | Single recipe with ingredients + steps (auth) |
| `POST /api/recipes` | Create recipe (auth) |
| `PUT /api/recipes/<id>` | Update recipe (auth) |
| `DELETE /api/recipes/<id>` | Delete recipe (auth) |
| `GET /api/recipes/categories` | Valid category list (auth) |
| `GET /api/cowsay` | Returns cowsay ASCII art as JSON |
| `GET /api/weather` | Current weather from FMI (Helsinki-Vantaa), cached 10 min |
| `GET /sitemap.xml` | XML sitemap for SEO |

## Configuration

A `.env` file is required with at least `SECRET_KEY` for session signing. The SQLite database is at `/app/data/site.db` (container path). For local development, set the `DATABASE_URI` environment variable to point to the local database.

To create an admin user:
```bash
docker compose exec web python3 -c "from app.create_admin import create; create('username', 'email', 'password', 'admin')"
```

## Production Notes

- Multi-stage Docker build: Node builds the frontend, final image is Python-only
- Gunicorn is used as the WSGI server inside the container
- The Flask app binds to `0.0.0.0:80` in production
- Nginx and SSL termination (Let's Encrypt) are configured outside this repo
- Changes pushed to GitHub are automatically deployed via webhook

## Author

Konsta Janhunen
[erez.ac](https://erez.ac)
