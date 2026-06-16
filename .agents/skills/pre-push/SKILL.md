---
name: pre-push
description: Run the full local test gauntlet (pytest + vitest + playwright + nuxt generate) before pushing to main. Strict mode — reports failures, never auto-fixes. Use when the user is about to push, when they ask "is this ready to push", or after a non-trivial change before committing.
---

# /pre-push

Push to `main` triggers an automatic deploy to erez.ac. A red CI run breaks the live site. This skill mirrors the GitHub Actions workflow locally so failures surface here, not in production.

## Strict mode

**Never auto-fix.** A previously-green test going red is a regression signal — investigate the underlying code change before touching the test. If a fixture or snapshot is genuinely stale, say so explicitly and wait for the user before regenerating.

This applies to all four suites. Report what failed, show the relevant excerpt, stop.

## What to run

Run these in order. Stop at the first failure and report — do not continue past a red suite (faster feedback for the user, and later suites often depend on the build state earlier ones leave behind).

1. **Pre-flight: kill stray Flask on :5001.** The Playwright config has `reuseExistingServer: !CI`, so any dev Flask listening on :5001 with `site.db` will hijack the test run. Check with `lsof -ti:5001`. If something is listening, ask the user before killing it (it might be their active dev server).

2. **Backend — pytest:**
   ```bash
   pytest tests/
   ```

3. **Frontend unit — vitest:**
   ```bash
   cd frontend && npm run test
   ```

4. **E2E — playwright with `CI=1`:**
   ```bash
   cd frontend && CI=1 npm run test:e2e
   ```
   Playwright spawns its own Flask (test-e2e.db) and Nuxt preview. If the seed is missing or stale, run `python3 scripts/seed_e2e.py` from the repo root first.

5. **Production build — nuxt generate** (matches the Docker prod build):
   ```bash
   cd frontend && npm run build
   ```
   This is `nuxt generate` and is what actually runs in the Docker image. A green dev server doesn't prove a clean SSG build.

## Reporting

On success, one line: `pre-push: pytest ✓  vitest ✓  playwright ✓  build ✓ — safe to push`.

On failure, report:
- which suite failed,
- the failing test name(s) or build error,
- a short excerpt of the actual error (not the whole log),
- a one-sentence read on whether the failure looks like a real regression or a stale test/fixture.

Do not propose a fix until the user asks. Do not run the suite again with `--update-snapshots` or similar without explicit permission.

## Notes

- Don't run `security-review` here — it is on-demand only.
- If the working tree is dirty, mention it but don't block; the user may want to test before committing.
- If the user has already pushed, switch to `/deploy-watch` instead.
