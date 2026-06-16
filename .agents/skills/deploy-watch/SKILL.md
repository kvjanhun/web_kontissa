---
name: deploy-watch
description: After pushing to main, watch the GitHub Actions run and the live deploy webhook outcome, and report when erez.ac is actually serving the new commit. Use after `git push` to main, or when the user asks "is it deployed yet" / "did the deploy go through".
---

# /deploy-watch

Push to `main` runs CI (pytest + vitest + playwright in parallel), and on green CI a webhook redeploys the Docker container on the NUC. This skill follows that pipeline end-to-end and reports when the change is actually live.

## Process

1. **Confirm there is something to watch.** Run `git rev-parse HEAD` and `git log origin/main..HEAD --oneline` (or check that HEAD matches `origin/main`). If nothing has been pushed, say so and stop.

2. **Find the current run.**
   ```bash
   gh run list --branch main --limit 1 --json databaseId,headSha,status,conclusion,workflowName
   ```
   If `headSha` doesn't match the local HEAD, GHA may not have picked up the push yet — wait briefly (5–10s) and retry once.

3. **Watch the run.**
   ```bash
   gh run watch <runId> --exit-status
   ```
   This blocks until the run finishes and exits non-zero on failure.

4. **On CI success, verify the live site.** The healthcheck endpoint is `/api/meta`:
   ```bash
   curl -fsS https://erez.ac/api/meta
   ```
   Poll briefly (e.g. 6 attempts, 5s apart) — the deploy webhook + `docker compose up --build` takes a minute or two on the NUC. A 200 with valid JSON is the green signal. If `/api/meta` includes a build hash or version string, compare it against the pushed commit; otherwise a 200 is sufficient.

5. **Report.**
   - On full success: `deploy-watch: CI ✓  live ✓ — <short-sha> is serving on erez.ac`.
   - On CI failure: which job failed, with `gh run view <runId> --log-failed` excerpt. Stop — do not propose fixes unless the user asks.
   - On CI green but live check failing past the polling window: surface that explicitly. The webhook itself can fail even with a green CI (build error in Docker, disk pressure on the NUC, container crash on boot).

## Notes

- **Do not** retrigger CI, push --force, or revert without explicit user instruction. A failed deploy is a signal, not a problem to paper over.
- If the user wants to keep watching across longer windows, suggest `/loop` or `/schedule` rather than busy-waiting in this skill.
- The user may run this skill before pushing by mistake. If `git status` shows unpushed commits, offer to push first; otherwise note that there's nothing newer than `origin/main` to track.
