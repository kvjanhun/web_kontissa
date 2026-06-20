# /dog Browser — Review Findings & Follow-ups

**Date:** 2026-06-21
**Context:** Functionality + UX review of the `/dog` Showlink browser (frontend `frontend/features/dog/`, backend `app/dog_show/` + `app/api/dog.py`). Overall the feature is well-built and the scraping is polite and sound. This file records what shipped, the open ideas we agreed to defer, and the backend scraping audit.

---

## Shipped this session (done)

Small UX/polish pass, all green (142 vitest + 5 dog E2E + clean `nuxt generate`):

1. **Deep-link document title** — `DogBrowser.vue` syncs `document.title` to the open show/breed (`<title> | erez.ac`); list view unchanged. SEO/OG deliberately left alone (the tool is intentionally hidden for now).
2. **Whole-show result count** — `DogShowDetailView.vue` shows "Löytyi N koiraa" once whole-show data is loaded, updating as filters narrow (parity with the breed view).
3. **Dynamic grade options** — new pure helper `availableGradesFromResults()` derives the grade dropdown from loaded results (whole-show + single-breed). Keeps `HYL`/`EVA`/`POISSA` distinct and always retains the currently-selected grade.
4. **Debounced in-show search** — input stays instant; the expensive whole-show regroup is debounced 200 ms (clearing applies immediately).
5. **Overnight quiet hours for live shows** (idea A below) — live result fetching is suppressed 21:00–06:00 Finnish local time, evaluated via `zoneinfo`/`tzdata` (the container runs UTC). Also fixed: show date/time logic now uses Europe/Helsinki instead of the UTC container clock.

Touched: `dogResults.js`, `useDogBrowser.js`, `DogBrowser.vue`, `DogShowDetailView.vue`, `DogShowTools.vue`, `DogBreedResultsView.vue`, `DogResultFilters.vue`, `tests/unit/dogResults.test.js` (items 1–4); `app/dog_show/config.py`, `app/dog_show/utils.py`, `app/api/dog.py`, `tests/test_dog.py`, `docs/dog-show-browser.md`, `frontend/pages/dog/about-crawler.vue` (item 5).

---

## Open ideas / follow-ups (not yet actioned)

### A. Overnight quiet hours for live result fetching  ✅ DONE 2026-06-21

> Implemented as described below. Live shows now go quiet 21:00–06:00 (Europe/Helsinki, resolved via `tzdata` since the container is UTC). Net effect: stale cache served overnight, zero Showlink requests, daytime resumes at 06:00 — and the day-2-at-05:00 gap is closed. Original sketch kept below for reference.
>
> **Frontend follow-up also done (2026-06-21):** the periodic *live* polls now pause overnight too. New pure helper `isOvernightResultWindow()` (`dogResults.js`) gates three loops in `useDogBrowser.js`: the detail live poll and the whole-show live re-poll skip the fetch and keep a slow ~15-min clock heartbeat (resume automatically at 06:00 if left open); the list-page index poll skips its fetch overnight unless it's still reflecting index-build progress. One-time loads, warming polls, and index-warming polling are all unaffected, so nothing is blocked from updating — only the pointless every-2-min live polling stops at night. Touched: `dogResults.js`, `useDogBrowser.js`, `tests/unit/dogResults.test.js`.


**Problem:** A multi-day live show keeps its result cache on the 2-minute live TTL across the whole date range, so the crawler/web keep re-checking Showlink overnight even though no results are produced. There is no need to fetch live results between roughly **21:00 and 06:00** local time.

**Approach (single chokepoint):** extend `_show_result_availability()` in `app/dog_show/utils.py`. Today the live branch is `start_date <= today <= end_date → can_fetch True`, with a `morning_hour` (06:00) gate applied **only** on `today == start_date`. Replace with a window gate that applies every day of the range:

```python
# config.py
RESULT_SHOW_EVENING_HOUR = int(os.environ.get("DOG_RESULT_SHOW_EVENING_HOUR", "21"))

# utils.py, inside the live-range branch
if start_date <= today <= end_date:
    if now.hour < morning_hour:
        return {**base, "can_fetch": False, "show_state": "live", "reason": "show_morning"}
    if now.hour >= evening_hour:
        return {**base, "can_fetch": False, "show_state": "live", "reason": "show_night"}
    return {**base, "can_fetch": True, "show_state": "live", "reason": "show_day"}
```

This subsumes the existing first-day morning check and also closes the day-2-at-05:00 gap (currently `today != start_date` falls through to `can_fetch True`).

**Why it's safe downstream** (all already honor `can_fetch`):
- `crawl_result_cache_for_show` → returns `skipped` for live shows during quiet hours.
- `_queue_live_result_cache_refresh(es)` → returns `None` (no queue, no immediate warmup).
- `/all-results` → serves the existing (stale) cache from disk **without** queueing a refresh; only returns 425 if there is no cache at all.
- TTL stays `RESULT_CACHE_LIVE_TTL` so the cache is *marked* stale, but the refresh is gated → **stale served, zero Showlink requests overnight.** Daytime resumes at 06:00.

**Loose ends to handle when implementing:**
- Add a `"show_night"` message in `_results_not_ready_response()` (`app/api/dog.py`), e.g. "Tuloksia ei haeta yöaikaan (klo 21–6)." Only surfaces if no cache exists yet during quiet hours (rare mid-range).
- **Timezone:** the gate uses server-local `datetime.now()`. The existing `morning_hour=6` already assumes server local == Europe/Helsinki, so this is consistent — but confirm the NUC's TZ. If the server isn't on Helsinki time, make the window TZ-aware.
- **Frontend (optional):** `getShowResultAvailability()` in `dogResults.js` computes phase from dates only, so the detail page would keep polling every 2 min overnight. Those hits only read erez.ac's own cache (no Showlink load), so it's harmless — but teaching the frontend the 21:00–06:00 window would also stop pointless overnight polling of our own server. Defer unless we care.
- **Single-day vs multi-day:** recommend applying the evening cutoff uniformly to all live shows (simpler; late-night fetching is pointless anyway, and the BIS / entry-completion settling grace already ends live TTL for finished single-day shows). Flagged in case we want to restrict it to multi-day only.
- Update `docs/dog-show-browser.md` (Freshness Policy + Environment knobs) and the public `frontend/pages/dog/about-crawler.vue` cadence copy (FI + EN) to mention the overnight pause. Add a `tests/test_dog.py` case for the night gate.

**Size:** small, well-scoped backend change + docs + 1 test.

---

### B. Bound `queue_background_indexing` in web workers  ← from scraping audit

The only under-bounded scraping path. `app/dog_show/crawler.py:queue_background_indexing()`:
- dedup set `_background_indexed_shows` is **per-process**, not cross-worker (multiple Gunicorn workers can overlap), and
- the worker thread iterates **all** missing/empty shows with no per-call cap (`for show in to_index:`), each doing a detail fetch that may itself fan out to group pages (with 0.5 s sleeps).

So on a cold/empty index, one `/api/dog/shows` hit can spawn a thread making *hundreds* of Showlink requests from the web container. It's bounded (1 s spacing, once per process) and the crawler would do the work anyway, but it's the least-contained path.

**Fix:** cap the batch per invocation (e.g. 3–5 shows) and/or gate it behind the shared job-file lock the result-cache path uses, and/or just lean on the `dog-crawler` service (which already runs `crawl_index_once` every 15 min). Cheap change.

---

### C. Cross-show / cross-dog tracking  ← the big feature; deferred

Track a dog / kennel / judge across all shows ("show me every result for this dog").

**Politeness math (reassuring):** ~300–500 Finnish KC shows/year; cost ≈ 1 page per breed-with-results → **~10k–20k requests to fully cache one year** (a few 250-breed all-breed shows dominate; most specialties are tiny). At the current polite rate that's ~20–50 min of pure request time per year if flat-out, but spread off-peak ≈ **a couple of nights per year of history**, linear across years. Far less than a season of live-show warming. **Crawling is the cheap part.**

**Approach (~2–4 dev-days; data model + UI are the real cost):**
1. **Backfill driver** — crawler mode that queues result-cache jobs for shows beyond the 7-day window, strictly rate-limited, only when no live/queued work pends. Reuses the existing job queue + `crawl_result_cache_for_show`.
2. **Deep index (zero extra Showlink load)** — post-process existing whole-show caches into a secondary index keyed by dog (reg id from `reg_url`), judge, kennel.
3. **Storage → SQLite for the index** — at ~100k+ dog-result rows JSON creaks; SQLite gives indexed lookups **and** free Litestream backup (the JSON caches currently aren't backed up). Whole-show caches stay JSON.
4. **Endpoints + "dog profile" view** — results across shows, reachable from the reg link already on every result card.

**Two feasibility unknowns to verify FIRST (cheap to probe):**
- Does Showlink's show list expose **multi-year history** in a crawlable way, or only a rolling window? If rolling-only, deep history needs another entry point. *Biggest unknown.*
- How **stable is the dog id** inside `reg_url` (jalostus.kennelliitto.fi)? That reg number is the anchor; without it cross-show linking degrades to fuzzy name + messy kennel-name parsing.

**Storage budget:** ~1–5 GB JSON for a few years of caches — fine on the NUC.

---

### D. Minor scraping notes (acceptable as-is)

- No `requests.Session` keep-alive (efficiency, not politeness) — could add a shared session in `showlink.py`.
- No explicit `Retry-After`/429 honoring — the job backoff covers it.
- No `robots.txt` check — fine for a low-volume, identified crawler with a public info page.

---

## Scraping audit verdict (reference)

**Sound.** No forever-loops, no needless re-scraping. Safeguards in place:
- All fetches centralized in `_fetch_page` (fixed UA, 10 s timeout, `raise_for_status`).
- Hard availability gate blocks result fetching before show-day 06:00; future shows never fetch.
- Layered TTL caching: settled/old shows effectively immutable (TTL → `None`); live shows use 2-min TTL that ends via BIS-grace or entry-completion grace.
- Bounded concurrency: ≤3 workers, 0.4 s between request starts, per show.
- Durable job queue with linear backoff capped at 1 h; `dog_result_jobs.json` acts as a cross-process lock so web + crawler don't double-warm.
- Atomic writes (temp + `os.replace`), resumable per-breed progress, persisted probe cursor.

Only genuinely under-bounded path = **B** above.
