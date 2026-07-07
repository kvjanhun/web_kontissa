# Lean dog crawler: date-first candidate gating, retire healing passes

Status: shipped
Date: 2026-07-07

## Objective
Cut the crawler container's ~15% idle CPU baseline to near zero by making candidate
selection date-first, and align the loop with the actual data premises: crawl to
discover shows, crawl live shows for results, allow ~1 week of post-show corrections,
and never churn over settled history.

## Context
The crawler process sits at ~15% CPU with no live shows. Measured cause: the
auto-results pass (`--auto-results-interval 120`) calls
`_auto_result_cache_candidates`, which iterates every show on Showlink's Tulokset
list — currently **630 shows, all past** (the page lists the whole season) — and for
each one loads the full whole-show result doc (~566 ORM-hydrated rows on average,
~382k rows total per pass) plus the indexed breed list and a finals analysis,
*before* any date check. One selection pass measures **7.3s CPU on an M-series Mac**
(so plausibly 25–40s per 120s on the NUC), to yield ~3 candidates. 617 of the 630
shows are older than the 7-day auto window and can never be candidates; their doc
loads are pure waste. (`_index_states`, blamed earlier, measures 6ms — that's why
raising `--empty-index-interval` to 28800 changed nothing.)

Secondary churn found while auditing the loop:

- **Empty-index repair pass** (`crawl_empty_index_once`): a healing remnant for
  "stale empty breed indexes created by older parser versions". Zero candidates in
  the current DB, and the maintenance pass already puts empty-indexed shows first in
  its own candidate list, so the dedicated pass is fully redundant.
- **Maintenance starvation**: `crawl_index_once` builds
  `empty_indexed + missing + recent` in Showlink page order and takes the first
  `--limit 6` — no staleness ordering — so with >6 "recent" shows it re-fetches the
  *same* 6 shows every 15 minutes and never reaches the rest.
- **Recent window too wide**: `SHOW_RECENT_PAST_DAYS=45` keeps six-week-old shows in
  the re-index rotation, though results are immutable well before that.

## Approach

1. **Date-first gate in `_auto_result_cache_candidates`** (the CPU fix). Before any
   DB access, parse the show's date from the list dict (pure string work,
   microseconds) and skip when the show is `upcoming`, or `past` with
   `age_days > max(RESULT_AUTO_WINDOW_DAYS, RESULT_SETTLE_DEADLINE_DAYS)` (= 7 days
   at defaults, covering the rescue/overtime/recent-warming classes, all of which
   require ≤7 days). Unparseable dates fail open (load the doc, as today). Only the
   surviving handful get the doc load + live plan. With no live/recent shows the
   pass touches zero docs; during a show weekend it loads only the window's shows.
   Note: today's upcoming-skip reads the *indexed* date via the plan; the gate reads
   the *list* date — same origin data, and the parity is locked in by tests.

2. **Delete the empty-index repair pass**: remove `crawl_empty_index_once`, its
   `--empty-index-*` / `--no-empty-index-repair` CLI flags, its slot in the loop,
   and its test. The maintenance pass keeps healing empty-indexed shows (they stay
   first in its candidate ordering), so the capability survives; only the dedicated
   churn pass goes.

3. **Shrink `SHOW_RECENT_PAST_DAYS` default 45 → 7** (env override stays). This is
   the deliberate premise change: after a week, a show's index and results are
   settled history. Effects: the maintenance pass stops re-indexing 1–6-week-old
   shows, and `_result_cache_doc_is_fresh` treats their complete caches as
   permanently fresh (no re-crawl). User-queued jobs on old shows with *incomplete*
   caches still crawl (completeness is checked before recency).

4. **Staleness-ordered maintenance candidates**: extend `sqlstore.index_states`
   with the show's `updated_at`, and have `crawl_index_once` sort the `recent`
   bucket stalest-first (empty/missing keep priority). The `--limit 6` budget then
   round-robins the window instead of hammering the same 6 shows.

5. **Compose command shrink**: drop the retired flags from `docker-compose.yml`;
   keep `--interval 30` (the queued-jobs poll is user-facing and cheap: the jobs
   table is empty or tiny).

Docs: update `docs/dog-show-browser.md` (crawler passes + tuning) and the crawler
paragraph in `app/CLAUDE.md`.

## Files to touch
- `app/dog_show/result_cache.py` — date-first gate in `_auto_result_cache_candidates`
- `app/dog_show/crawler.py` — delete `crawl_empty_index_once`; staleness-sort recent candidates
- `app/dog_show/sqlstore.py` — `index_states` returns `updated_at` per show
- `app/dog_show/config.py` — `SHOW_RECENT_PAST_DAYS` default 45 → 7
- `scripts/dog_crawl.py` — remove empty-index pass + flags from the loop
- `docker-compose.yml` — trim crawler command
- `tests/test_dog.py` — see Tests
- `docs/dog-show-browser.md`, `app/CLAUDE.md` — ops notes

## API / data shape
None. No schema change (`index_states` reads an existing column), no endpoint change.

## Tests
- Backend (pytest, `tests/test_dog.py`):
  - New: auto-candidates with old past shows performs **zero** result-doc loads
    (monkeypatched counter on `_load_result_cache_doc`); live / rescue /
    recent-past-warming / unknown-date shows still produce candidates (existing
    tests at the current behavior stay green — their fixtures sit inside the window).
  - New: `crawl_index_once` with limit < recent-count picks stalest-first and a
    second pass reaches the next shows.
  - Updated: `test_show_is_recent_date_window` for the 7-day default.
  - Removed with the feature: `test_crawl_empty_index_once_repairs_only_empty_entries`
    (deliberate retirement, not a silenced regression).
- Frontend unit / E2E: none — no web-tier behavior changes.

## Security considerations
- New input vector: no — this only removes fetch volume and reorders existing work.
- Exposes internal state: no.
- Network boundary: no; outbound request volume to Showlink strictly decreases.

## Out of scope
- The queued-jobs pass and its 30s cadence (user-facing warm-up latency).
- Web-tier `/api/dog/*` read paths and the 20s stats cache.
- Any dog.db schema or retention change (permanent store stays permanent).
- Litestream / backup posture for dog.db.

## Open questions
- None blocking. Recommendation embedded above: delete `crawl_empty_index_once`
  outright rather than keeping a dead one-off (the maintenance pass retains the
  healing behavior).
