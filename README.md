### 📄 `README.md`

# [erez.ac](https://erez.ac)

**Personal portfolio website powered by Flask, Gunicorn, and SQLite**, containerized using Docker and orchestrated with Docker Compose.

This README.md has been automatically generated by ChatGPT and has been curated by myself. ChatGPT 4o has been used to advise in parts of the project.

---

## 🚀 Features

- Flask web app with Jinja2 templates
- Styled terminal-style intro with cowsay integration
- SQLite database backend (pre-built and included)
- Lightweight, production-ready Docker setup using Gunicorn

---

## 📁 Project Structure

```
web_kontissa/
├── app/
│   ├── data/
│   │   └── site.db             # Prebuilt SQLite database
│   ├── main.py                 # Flask application entry point
│   ├── models.py               # SQLAlchemy models
│   ├── templates/
│   │   ├── index.html          # Main HTML template
│   │   └── ...                 # Other layout or partials
│   └── static/
│       ├── assets/style.css    # Custom styles
│       └── script/terminal.js  # Terminal animation script
├── Dockerfile                  # Image definition
├── docker-compose.yml          # App service configuration
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 🐳 Running Locally (with Docker)

```bash
docker compose up --build
```

Then visit: [http://localhost:8080](http://localhost:8080)

To rebuild without cache (e.g. after changing dependencies or database):

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## ⚙️ Configuration

No external `.env` file required. Flask loads the pre-built SQLite database from:

```
/app/data/site.db
```

You'll need to generate the database manually:

```bash
sqlite3 app/data/site.db < schema.sql
```

> Note: You can also generate the schema using SQLAlchemy if needed. For production, the database is prebuilt.

---

## 📦 Production Notes

- Gunicorn is used as the WSGI server inside the container
- The Flask app binds to `0.0.0.0:80`
- External services like Nginx and SSL termination (e.g. Let's Encrypt) are configured outside the scope of this repo
- Deployments pull this repo, rebuild using Docker Compose, and restart the container

---

## Author

Konsta Janhunen  
[erez.ac](https://erez.ac)
