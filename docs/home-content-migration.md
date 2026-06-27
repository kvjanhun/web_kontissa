# Home content: Stage 1 → Stage 2 migration (locale files → database)

The home page content (hero rolling phrases + line + intro, stack layers, footer
phrases, and the projects collection) moved from the bundled locale files into the
database, editable from the admin panel. This note is the one-off production
migration procedure. Per `CLAUDE.md`, schema changes are never run from Flask
startup — do this manually, once, with a backup.

## What changes

- **New tables** (`home_content`, `project`, `project_translation`) — created
  automatically by the idempotent `db.create_all()` on startup (additive; allowed).
- **Dropped table** `section` — the legacy CMS (`Section` model, `/api/sections*`,
  `AdminSections.vue`) is removed. Dropping the table is the only destructive step.

## Procedure (on the NUC, against the production `site.db`)

1. **Deploy the code first.** Push to main as usual. On deploy, `db.create_all()`
   creates the three new tables (empty). The old `section` table is left intact.
   The home page still renders correctly from the committed
   `frontend/locales/home-content.snapshot.json` (baked at build) until step 2.

2. **Back up the database.**
   ```bash
   cp app/data/site.db app/data/site.db.pre-homecontent.bak
   ```

3. **Seed the new tables** from the committed snapshot (run inside the web
   container, which has the deps + the mounted DB):
   ```bash
   docker exec web_kontissa-web-1 \
     env DATABASE_URI=sqlite:////app/data/site.db \
     python scripts/seed_home_content.py
   ```
   It only seeds when the tables are empty; pass `--force` to wipe + reseed.
   Verify: `curl -s localhost:8080/api/home-content | head` shows the projects and
   fields. From here, edits in the admin (`Home content` / `Projects`) are live.

4. **Drop the legacy table** once content is verified:
   ```bash
   docker exec web_kontissa-web-1 \
     sqlite3 /app/data/site.db "DROP TABLE IF EXISTS section;"
   ```

5. **Refresh the snapshot** (optional; the next deploy does this automatically via
   `server/deploy-site.sh`). To do it now:
   ```bash
   docker exec web_kontissa-web-1 \
     python scripts/export_home_content.py --out /app/data/home-content.snapshot.json
   mv app/data/home-content.snapshot.json frontend/locales/home-content.snapshot.json
   git add frontend/locales/home-content.snapshot.json && git commit -m "chore: refresh home-content snapshot"
   ```

## Notes

- `home_content` / `project*` live in `site.db`, so they are covered by Litestream
  replication (no config change needed — unlike `dog.db`).
- The snapshot is a build cache for first paint / SEO, not the source of truth. The
  client always re-fetches `/api/home-content` at runtime, so a slightly stale
  snapshot only affects the brief pre-hydration paint and crawlers.
- Rollback: restore `site.db.pre-homecontent.bak` and redeploy the previous commit.
