---
name: e2e
description: Run the Playwright E2E suite locally with the documented gotchas handled — kill stray Flask on :5001, seed test-e2e.db if needed, and run with CI=1. Use when the user wants only the E2E suite (not the full /pre-push gauntlet) or is debugging a single E2E failure.
---

# /e2e

Standalone Playwright runner. Handles the recurring footgun documented in `AGENTS.md`: `playwright.config.js` has `reuseExistingServer: !process.env.CI`, so any dev Flask listening on :5001 with `site.db` will be reused instead of the test-configured Flask, and DB-backed specs (auth, admin, recipes) will silently fail.

## Process

1. **Check for stray Flask on :5001.**
   ```bash
   lsof -ti:5001
   ```
   If something is listening, ask the user before killing it — it could be their active dev server, in which case offer to either kill it or run with `CI=1` (which forces Playwright to spawn its own Flask anyway).

2. **Check the test DB.** Path: `app/data/test-e2e.db`. If missing, or if the schema may have changed since the last seed, run:
   ```bash
   python3 scripts/seed_e2e.py
   ```
   The script wipes and rebuilds the DB, so it's safe to re-run anytime.

3. **Run the suite with `CI=1`** (forces fresh server spawn regardless of any stray dev server):
   ```bash
   cd frontend && CI=1 npm run test:e2e
   ```

4. **For a single spec or test pattern,** pass through to playwright:
   ```bash
   cd frontend && CI=1 npx playwright test e2e/auth.spec.js
   cd frontend && CI=1 npx playwright test -g "admin can edit"
   ```

5. **For interactive debugging,** offer the UI mode:
   ```bash
   cd frontend && npm run test:e2e:ui
   ```
   (UI mode opens an interactive runner; the user drives it.)

## Reporting

On failure: name the failing spec, the assertion that failed, and a short excerpt. Do **not** edit the test to make it pass — apply the test-respect rule. A previously-green spec going red is a regression signal; investigate the underlying code change first.

## Notes

- If the failure mentions hydration timing or stale DOM, check that `e2e/fixtures/base.js` is being used (it wraps `page.goto()` with `waitForLoadState('networkidle')`).
- 30 tests across 7 spec files is the current baseline. If the count drops, ask why before proceeding.
