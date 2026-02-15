# [erez.ac](https://erez.ac)

Personal portfolio website by Konsta Janhunen.

## Stack

- **Frontend**: Vue.js 3 (served locally, no build step)
- **Backend**: Flask (Python) with JSON API endpoints
- **Database**: SQLite via Flask-SQLAlchemy
- **Server**: Gunicorn (production), Flask dev server (local)
- **Deployment**: Docker Compose, auto-deployed via GitHub webhook

Vue 3 handles all rendering and interactivity in the browser, fetching data from Flask API endpoints (`/api/sections`, `/api/meta`, `/api/cowsay`). Flask serves a single HTML page that mounts the Vue app — no Node.js build tooling required.

## History

The site was originally built with Flask + Jinja2 server-rendered templates + vanilla JavaScript, with ChatGPT 4o used for roadmap advice and templates.

In February 2026, the frontend was migrated to Vue.js 3 with a hybrid CDN/local approach. This migration was carried out by Claude (Anthropic), orchestrated by Konsta. The Jinja2 templates were replaced with Vue components, Flask routes were converted to JSON API endpoints, and the terminal animation was rewritten as a Vue component.

## Project Structure

```
web_kontissa/
├── Dockerfile
├── README.md
├── docker-compose.yml
├── requirements.txt
├── run.py
└── app/
    ├── __init__.py
    ├── routes.py
    ├── models.py
    ├── utils.py
    ├── api/
    │   ├── __init__.py
    │   └── cowsay.py
    ├── data/
    │   └── site.db
    ├── templates/
    │   └── index.html          # Vue 3 app (single page)
    └── static/
        ├── favicon.ico
        ├── assets/
        │   └── style.css
        └── script/
            └── vue.global.js   # Vue 3 runtime (local)
```

## Running Locally

### With Docker

```bash
docker compose up --build -d
```

Then visit: [http://localhost:8080](http://localhost:8080)

### Without Docker

```bash
pip install flask flask-sqlalchemy cowsay requests
DATABASE_URI="sqlite:///$(pwd)/app/data/site.db" python3 -c "
from app import app
app.run(host='127.0.0.1', port=5555)
"
```

Then visit: [http://localhost:5555](http://localhost:5555)

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Serves the Vue app |
| `GET /api/sections` | Returns all content sections as JSON |
| `GET /api/meta` | Returns site metadata (update date, author) |
| `GET /api/cowsay` | Returns cowsay ASCII art as JSON |
| `GET /sitemap.xml` | XML sitemap for SEO |
| `GET /index.html` | 301 redirect to `/` |

## Configuration

No external `.env` file required. The SQLite database is at `/app/data/site.db` (container path). For local development, set the `DATABASE_URI` environment variable to point to the local database.

## Production Notes

- Gunicorn is used as the WSGI server inside the container
- The Flask app binds to `0.0.0.0:80`
- Nginx and SSL termination (Let's Encrypt) are configured outside this repo
- Changes pushed to GitHub are automatically deployed via webhook

## Author

Konsta Janhunen
[erez.ac](https://erez.ac)
