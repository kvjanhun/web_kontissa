---
name: add-endpoint
description: Add a Flask JSON API endpoint the way this repo does one — blueprint, auth decorator, parameterized query, pytest, and the Pinia store plus en/fi locale keys on the frontend. Use when adding or extending an API endpoint in app/, or when a feature needs a new backend route wired through to the UI.
paths:
  - app/**
  - tests/**
  - frontend/stores/**
  - frontend/composables/**
---

# Add Endpoint

The full path for one endpoint, backend to UI. Follow the order — the tests come
with the handler, not after it.

## 1. Decide the auth level first

It determines everything else.

| Level | Decorator | Used by |
| --- | --- | --- |
| Public | none | `/api/meta`, `/api/weather`, `/api/dog/*` |
| Login | `@login_required` | recipes (shared cookbook, any user CRUDs) |
| Admin | `@admin_required` (`app/decorators.py`) | `/api/admin/*` |

A public mutation endpoint needs an allow-list on whatever it writes — `/api/pageview`
rejects paths outside `is_known_route()` for exactly this reason, because the rows
land in the Litestream-replicated `site.db`.

## 2. Backend

- **Blueprint**, registered in `app/__init__.py`. No URL prefix — paths stay
  literal. Small domains go in `app/api/<name>.py`; the existing top-level
  modules (`auth.py`, `recipes.py`, `home_content.py`) are the pattern for larger ones.
- **Return JSON always.** Errors are `{"error": "..."}` with a real status code.
- **Mutations read `request.get_json()`** — JSON-only is what stands in for CSRF
  protection here. Do not accept form bodies on a mutation.
- **Queries go through SQLAlchemy** with bound parameters. Never interpolate
  user input into SQL.
- **Rate limiting** is Flask-Limiter, 30/min by default. Exempt only read-only
  endpoints that the page calls on every load, and say why in a comment.
- New model → `app/models.py`. New table is created by the idempotent
  `db.create_all()`; **a change to an existing table is not** — that is a schema
  change, so run `schema-change` instead of reaching for `ALTER TABLE`.

## 3. Tests — same commit

`tests/`, pytest, in-memory SQLite. Cover, at minimum:

- the success shape
- the auth boundary — 401/403 for the level below the one you chose
- input validation, including the rejection path
- whatever the endpoint refuses to do

## 4. Frontend wiring

Only if the UI consumes it:

- **Pinia store** in `frontend/stores/`, `defineStore` with a setup function.
  Auto-imported — no import line. `storeToRefs()` when destructuring reactive
  state; actions destructure directly.
- **Composable** in `frontend/composables/` if the logic is reused rather than
  owned by one store.
- **Locale keys in both `frontend/locales/en.json` and `fi.json`.** The fallback
  chain is locale → English → raw key, so a missing Finnish string silently ships
  English copy. Do not machine-translate: leave the Finnish to the user and say
  which keys need it. Run `/i18n-check` before you call this done.

## 5. Record it

Add the row to the API table in `app/CLAUDE.md` — method, endpoint, auth, purpose.
That table is the endpoint inventory and it is the one place it lives.

## Verify

```bash
pytest tests/
cd frontend && npm run test
```

Then `/verify-locally` if there is a UI surface.

**If this goes wrong:** an endpoint that leaks or over-permits is the real risk,
not a broken build. Before finishing, re-read the handler and answer: can it be
called without the auth you intended, and does its response carry any internal
path, secret, or id it should not? Reverting is a normal `git revert` — nothing
is applied to the host by this skill.
