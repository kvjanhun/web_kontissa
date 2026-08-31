# erez.ac architecture

How this application is put together. **Host-level architecture — nginx, TLS,
the firewall, the deploy webhook, and how erez.ac and sanakenno.fi share the
machine — lives in `~/Projects/nuc/README.md`** and is not repeated here.

## Request lifecycle

```mermaid
flowchart TD
    User(User browser)
    Nginx[nginx · TLS, security headers, CSP]

    subgraph Compose["Docker Compose (this repo)"]
        Gunicorn[Gunicorn :8080]
        Nuxt[Nuxt 3 static output]
        Flask[Flask 3.1 API]
        SiteDB[(site.db)]
        DogDB[(dog.db)]
        Litestream[Litestream]
        Flask -->|SQLAlchemy| SiteDB
        Flask -->|standalone engine| DogDB
        Gunicorn -->|/api/*| Flask
        Gunicorn -->|everything else| Nuxt
        Litestream -.->|continuous replication| SiteDB
    end

    User -->|HTTPS| Nginx
    Nginx -->|127.0.0.1:8080| Gunicorn
    Flask -.->|weather| FMI(FMI open data)
    Litestream -.->|B2| Backblaze[(Backblaze B2)]
```

Two databases, deliberately separate: `site.db` holds the site's own content
and users; `dog.db` is the dog-show browser's permanent store, has its own
SQLAlchemy engine, and is **not** covered by Litestream — it is backed up by
hand. See [dog-show-browser.md](dog-show-browser.md).

## Authentication

Session cookies via Flask-Login, with scrypt password hashing. There is no
self-registration — accounts are created with `app/create_user.py`.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Nuxt as Nuxt SPA (Pinia)
    participant Flask as Flask API
    participant DB as site.db

    Note over User,DB: Login
    User->>Nuxt: Submits credentials at /login
    Nuxt->>Flask: POST /api/login {email, password}
    Flask->>DB: Look up user by email
    DB-->>Flask: User record (scrypt hash)
    Flask->>Flask: Verify password hash
    Flask-->>Nuxt: 200 + Set-Cookie: session (HttpOnly, Secure, SameSite=Lax)
    Nuxt->>Nuxt: Auth store marks the session active
    Nuxt-->>User: Redirect to /admin

    Note over User,DB: Protected request
    User->>Nuxt: Navigates to an admin page
    Nuxt->>Nuxt: Global auth middleware allows the route
    Nuxt->>Flask: GET /api/... (browser attaches the session cookie)
    Flask->>Flask: Flask-Login resolves the session
    Flask-->>Nuxt: 200 with data, or 401 if the session is gone
    Nuxt-->>User: Renders, or bounces to /login on 401
```

The cookie is the only credential: there is no token in JavaScript-reachable
storage. Mutation endpoints accept JSON only, which is what stands in for CSRF
tokens here — a cross-origin form post cannot set `Content-Type:
application/json` without a preflight.

Rate limiting is per-client-IP via Flask-Limiter, which is why `ProxyFix` must
resolve the real client address; see the CLAUDE.md security notes.
