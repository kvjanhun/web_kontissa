---
name: schema-change
description: Change the database schema for a feature — add or alter a column, table, or index in site.db or dog.db. Use whenever a feature needs the shape of the database to change. This repo has no migration runner, so the change is planned, tested, seeded, and applied to production by hand; the skill enforces that path and blocks the shortcuts CLAUDE.md forbids.
paths:
  - app/models.py
  - app/__init__.py
  - app/dog_show/**
  - scripts/**
  - tests/**
---

# Schema Change

A schema change is a feature's change to the shape of the database. **This repo
has no migration runner** — `db.create_all()` creates missing tables and does
nothing to existing ones. So a change to an existing table is a planned,
hand-applied operation, not something the app performs on itself.

## The hard rule

**Never run a schema change from Flask startup, imports, or request handlers.**
`app/__init__.py` may create empty tables for fresh local and test databases. It
must not contain `ALTER TABLE`, table rebuilds, schema probes, or a hidden helper
that does any of those.

The reason is that startup runs on every container boot, on a live database that
Litestream is replicating. A change that runs itself there will run again, or
half-run, with no record of either.

## Which database

- **`site.db`** — the main store, Litestream-replicated to Backblaze B2.
- **`dog.db`** — the `/dog`-only store, its own SQLAlchemy engine, **not
  replicated** (backed up by hand). A destructive change here has no restore path
  beyond the user's own copy. Say so before making one.

## The path

1. **Write it into a plan first.** Use `plan-feature`. A schema change is exactly
   the case its "API / data shape" section exists for. Name the table, the
   column, the type, the default, and what happens to rows that already exist.
2. **Model** — update `app/models.py`. A brand-new table needs nothing further;
   `db.create_all()` is idempotent and will create it.
3. **Existing table** — write the one-off script under `scripts/`, following the
   shape of the ones already there. It must be re-runnable without damage: check
   whether the change is already applied before applying it. Scripts that import
   `app` must not guess the DB path — `DATABASE_URI` from the environment is
   authoritative, and the repo-relative fallback is dev-only on purpose.
4. **Seed data** — update `scripts/seed_e2e.py`, and `scripts/seed_home_content.py`
   if home content is involved. E2E runs against `app/data/test-e2e.db`, which is
   rebuilt from the seed; a schema change that skips this leaves every DB-backed
   spec failing for a reason that looks unrelated.
5. **Tests** — pytest in `tests/`, covering the new shape and the behaviour it
   exists for.
6. **Production procedure** — write the exact commands into the plan file: back
   up first, apply, verify. It is reviewed before it runs, and the user runs it.
   Do not run it yourself.

## Verify

```bash
python3 scripts/seed_e2e.py
pytest tests/
cd frontend && CI=1 npm run test:e2e
```

Reseeding is safe to repeat — the script wipes and rebuilds the E2E database.

**If this goes wrong:** the failure mode that matters is a change applied to the
live `site.db` without a backup, or one applied twice. `site.db` restores from
the Litestream replica at Backblaze; `dog.db` does not restore from anything
automatic, so a destructive change there is permanent. Every production step
happens by hand, after review, with a backup taken first — which is the whole
reason this repo has no runner.
