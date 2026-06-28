# Dog Show Browser

## Agent Fast Path

Read this section first when changing `/dog`.

| Task | First file to open |
|------|--------------------|
| Frontend route metadata or layout | `frontend/pages/dog/index.vue` |
| Frontend state, route query sync, API calls, polling | `frontend/features/dog/useDogBrowser.js` |
| Frontend view wiring | `frontend/features/dog/DogBrowser.vue` |
| Frontend list, search, detail, filters, result cards | `frontend/features/dog/components/` |
| Pure frontend result helpers | `frontend/features/dog/dogResults.js` |
| Dog frontend agent guide | `frontend/features/dog/AGENTS.md` |
| Backend route facade and request validation | `app/api/dog.py` |
| Backend implementation map | `app/dog_show/AGENTS.md` |
| Backend parsing, storage, result caches, crawler passes | `app/dog_show/` |
| Crawler process and CLI flags | `scripts/dog_crawl.py` |
| Backend tests | `tests/test_dog.py` |
| Frontend helper tests | `frontend/tests/unit/dogResults.test.js` |
| Browser-flow tests | `frontend/e2e/dog.spec.js` |

Important guardrails:

- The frontend must never fan out across all breed result pages; use `/api/dog/shows/<id>/all-results` for whole-show filtering.
- Persistent dog state is a dedicated SQLite database, `dog.db` (the `/dog`-only store, separate from `site.db`). It is a **permanent database, not a cache**: historical rows are never evicted. Do not delete `app/data` or `dog.db` casually. All reads/writes go through `app/dog_show/store.py`; the schema lives in `app/dog_show/models.py` and the JSON↔row conversion in `app/dog_show/sqlstore.py`.
- `pages/dog/index.vue` is intentionally thin after the frontend refactor; dog UI belongs in `frontend/features/dog/`.
- `app/api/dog.py` is intentionally a backend route facade; dog backend implementation belongs in `app/dog_show/`.
- Keep Showlink request volume bounded. Prefer crawler/job/cache changes over more client polling.

## Purpose

The dog show browser powers `/dog` and the `/api/dog/*` endpoints. It reads public Showlink result pages server-side, normalizes them, and caches the expensive whole-show result data so UI filtering does not create hundreds of browser or API requests.

The design goal is fast reads for users and polite, bounded crawling toward Showlink.

## Entry Points

- Frontend route entry: `frontend/pages/dog/index.vue`
- Frontend feature module: `frontend/features/dog/`
- Flask blueprint and route validation: `app/api/dog.py`
- Backend feature package: `app/dog_show/`
- Crawler process: `scripts/dog_crawl.py`
- Production service: `dog-crawler` in `docker-compose.yml`

## Public API

- `GET /api/dog/shows`: current Showlink show list plus index status and compact cached row stats when indexed. Active shows also include current result progress from the whole-show result cache.
- `GET /api/dog/shows/<show_id>`: breed list for one show. Live/recent detail responses enrich breeds with compact result progress from the whole-show cache when available.
- `GET /api/dog/shows/<show_id>/results?group=<group>&breed=<breed>`: one breed result page. Missing result pages are not fetched before the show date at 06:00 local time.
- `GET /api/dog/shows/<show_id>/all-results`: complete show result cache used by whole-show filters. Missing whole-show caches return `425`/`not_ready` instead of queueing work before the show date at 06:00 local time.
- `GET /api/dog/search?q=<query>`: search shows and indexed breeds.

Rate limits are intentionally lower than internal crawler throughput:

- Most dog endpoints: `30/minute`.
- Whole-show cache endpoint: `20/minute`.

## Data Flow

1. The browser loads `/dog` and calls `/api/dog/shows`.
2. The show list is enriched from the breed index in `dog.db` (`dog_show`/`dog_breed`) with breed count and entry count when a show is indexed. If the show date range includes today, the row also reads that show's whole-show result cache to expose `result_count/entry_count` progress without scanning historical result caches. When a live show's result cache is stale, this endpoint queues a bounded server-side refresh so front-page polling can move the number forward.
3. Opening a show calls `/api/dog/shows/<show_id>`.
4. If the breed index already contains the show and breed list, the backend serves that indexed copy without fetching Showlink.
5. For live shows, the detail response also reads the show's result cache (`dog_result_cache`/`dog_result`) and adds per-breed `result_count`, `result_total_count`, `result_updated_at`, and `result_progress` fields when the cache has seen that breed.
6. If a live show's result cache is stale, the detail endpoint queues the same bounded background refresh used by the show list. The open detail page polls the detail endpoint every 2 minutes.
7. Opening a single breed calls `/api/dog/shows/<show_id>/results`.
8. If a complete whole-show result cache exists, the single-breed endpoint extracts the breed from that cache instead of fetching Showlink.
9. Opening the whole-show filter calls `/api/dog/shows/<show_id>/all-results`.
10. If the show is still in the future, or it is the first show date before 06:00, the API returns `not_ready` and does not queue or fetch result pages.
11. If the whole-show cache is missing or stale after that threshold, the API queues a durable job and starts one bounded immediate background warmup in the web worker when allowed.
12. If the persisted breed index for a recent/live show is old and still has zero result-enabled breeds, the detail and whole-show result paths refresh the Showlink breed list before deciding what result pages exist.
13. Live whole-show result refreshes also probe a bounded rotating set of unchecked breeds, because a direct breed result page can contain rows before its group-list checkmark appears. When a probe finds rows, the breed is marked `has_results` in the breed index.
14. The crawler service also processes queued jobs and proactively warms recent shows.
15. The frontend polls `/all-results` using `retry_after` while the cache is warming and shows progress from the persisted cache document.

## Persistent Storage (dog.db)

All dog state lives in a dedicated SQLite database, `dog.db`, the `/dog`-only store. Its path is `DOG_DATABASE_URI` (default: `dog.db` inside `DOG_INDEX_DIR`). In Docker that is `/app/data/dog.db`, backed by the host bind mount `./app/data:/app/data`. It uses its own standalone SQLAlchemy engine (`app/dog_show/db.py`), **not** the Flask-SQLAlchemy `db` object, because dog writes happen in background warmup threads and the separate `scripts/dog_crawl.py` process, neither of which has a Flask app context. WAL + `busy_timeout` let the web process read while the crawler writes.

This is a **permanent database, not a cache**: old shows' data is kept forever and never evicted. Retention/TTL logic governs only *when to re-fetch* live or recent shows — it must never delete captured rows.

Tables (see `app/dog_show/models.py`):

- `dog_show` + `dog_breed`: show metadata and breed lists (with per-breed judges) for search and fast show-detail reads. Replaces the old `dog_show_index.json`. Global `last_updated` and an `index_generation` counter live in `dog_meta`.
- `dog_result_cache` + `dog_result`: whole-show result cache documents. `dog_result_cache` holds the doc header + a JSON `meta` blob (completed/failed breeds + live-tracking fields); `dog_result` is one normalized row per dog result. Each result row also carries `breed_judge` (so a breed's judge survives independently of `dog_breed`) and `competitive_placement` (the PU/PN best-of-sex ranking). Replaces `dog_result_cache/<show_id>.json`.
- `dog_breed_award`: breed honor-roll winners (ROP/VSP/SERT/veteran/junior/breeder) with `name` + `owner`, parsed from each result page's award table. A queryable projection of the awards also kept in the result doc's `completed_breeds` blob; rewritten per show alongside `dog_result`. Powers Phase E "wins by dog/kennel" queries.
- `dog_result_job`: durable queue for missing or stale whole-show caches. Replaces `dog_result_jobs.json`. Job rows are transient; result rows are permanent.

`dog.db` is **not** replicated to Litestream (which covers `site.db` only) — once fetched the data is effectively static and Konsta backs it up manually. The in-memory `_show_index` mirror (`store.py`) is reloaded only when `dog_meta.index_generation` advances, so cross-process freshness works without re-reading on every request.

`store.py` keeps the `_show_index` dict and all `/api/dog/*` response shapes byte-identical to the old JSON era; the one-off migration `scripts/migrate_dog_to_sql.py` loaded the legacy JSON files into `dog.db` with validated round-trip parity. For recent/live shows, complete caches with zero result breeds are still ignored and rebuilt when the index is stale or now shows result-enabled breeds.

## Freshness Policy

- Show list in-memory cache: 30 minutes.
- Show detail in-memory cache for recent or ongoing shows: 10 minutes.
- Breed result in-memory cache for recent or ongoing shows: 10 minutes.
- Showlink relative sections such as `Tänään` and `Huomenna` are treated as recent; the backend infers the year from the listed date so live-result availability still works.
- Whole-show result live TTL: 2 minutes by default while a show is still actively filling in.
- **Incremental live refresh.** A captured breed ring's results are immutable, so a live refresh of a *complete* cache re-fetches **only** breeds that newly gained results (per the show-detail checkmark) plus the bounded unchecked-breed probe — it does not re-crawl already-captured breeds. The working doc is seeded from the existing cache (`crawl_result_cache_for_show`, `seed_from_existing`) and stays `status="complete"` throughout, so an interrupted refresh never demotes a good cache. When the refresh fetches nothing new, only the header/meta is rewritten (`_save_result_cache_header`), never the thousands of result rows. `force=True` still does a deliberate full re-crawl. This replaced an earlier behavior that rebuilt the doc from empty and re-fetched every breed on every live pass — a 200+ page burst that starved the web workers on deploy/cold-start.
- **Finals re-sweep (the one exception to immutability).** Show finals (`RYP`/`BIS-1`/`BIS JUN`/`BIS VET`) are appended onto the *winners'* already-captured breed rows after every ring is judged. Once all judged breeds are captured but a main BIS is still expected and not yet recorded, the refresh re-checks a bounded, rotating chunk of captured breeds (`DOG_RESULT_FINALS_SWEEP_BREED_LIMIT`, default 30, cycling via `finals_sweep_cursor`) so the finals land within a few passes instead of a whole-show burst. Re-fetched rows replace the breed's old rows (no duplication). The sweep stops as soon as `BIS-1` is captured or the show drops out of its live date range.
- Overnight quiet hours: a live show is not checked against Showlink between `DOG_RESULT_SHOW_EVENING_HOUR` (21:00) and `DOG_RESULT_SHOW_MORNING_HOUR` (06:00) local time, on every day of a multi-day show. Previously-fetched results stay visible; the cache is simply served stale until the morning. Show date and these hours are evaluated in `DOG_RESULT_TIMEZONE` (Europe/Helsinki), not the UTC container clock.
- Front-page display state (`stats.is_live` / `stats.is_paused`, `_show_live_phase` in `utils.py`): a live show reads as **`Käynnissä`** while judging is active, and as **`Jatkuu`** (paused) during its multi-day nightly/evening lull — the overnight quiet window, or a result stall of `DOG_RESULT_PAUSE_STALL_SECONDS` (2h) once past `DOG_RESULT_PAUSE_EVENING_HOUR` (17:00) — but only when another in-range show day still follows. The first day's pre-dawn and the final day's wind-down stay `Käynnissä`; the final day settles to past via the BIS/entry-completion grace above, subject to the same main-BIS exception (a show still awaiting its `BIS-1` keeps reading `Käynnissä`/`Jatkuu` rather than going `done` the moment every breed ring is judged). `Jatkuu` rows keep showing today's `n/N tulosta`. The stall signal is the latest `completed_breeds[*].updated_at` among result-bearing breeds, so it never depends on a schema change. This is a display distinction only; the Showlink fetch gate is unchanged.
- Main `BIS-1` in cached awards starts a 30-minute live settling window by default. After that, the show stops using the 2-minute live TTL even if the calendar date has not changed.
- If a live cache has at least as many result rows as the indexed entry count, the same 30-minute settling window starts from that entry-completion point. This catches specialty and smaller shows whose cached breed rows may not include a main `BIS-1`.
- Exception: shows that still expect a main Best in Show do **not** settle on entry completion. All-breed shows decide the group finals and `BIS-1` *after* every breed ring is judged, so settling at entry completion would freeze the cache right before Showlink publishes `RYP-1`/`BIS-1` onto the winners' breed rows. A show is treated as expecting a main BIS when its indexed breeds span two or more FCI groups, or when the cache already records show-wide finals (`RYP`, `BIS JUN`, `BIS VET`). Such caches stay on the live TTL until `BIS-1` is captured, after which the normal 30-minute main-`BIS` settling window applies. The same exception governs the front-page display state (`_show_stats_from_index` shares `_show_expects_main_bis` with the TTL gate), so an all-breed show keeps reading `Käynnissä`/`Jatkuu` through its finals instead of flipping to `done` after the last breed ring.
- On the first calendar day after a show's final listed date, a cache last written before midnight is treated as stale once so the next crawler pass performs a final post-show check.
- Whole-show result fallback TTL when the show date is unknown: 24 hours.
- Whole-show result active TTL for recent non-live shows: replaced by the single final post-show check once a show date is known.
- Whole-show result settled TTL: 7 days by default.
- A show is considered settled for result-cache TTL after 2 days by default.
- Automatic recent-show result warming scans shows from the last 7 days by default.
- Old shows are treated as stable once cached.
- Empty indexed breed lists without an `empty_breed_list_confirmed` marker are prioritized by the crawler. This self-heals older cache entries created before parser fixes.

## Showlink Page Shapes

Supported show-detail shapes:

- Specialty pages where the landing page already contains `table.rotulistatable`.
- Single-breed specialty pages where `table.rotulistatable` has no result checkmark but the direct breed URL can already contain results.
- Live all-breed pages where a breed-list checkmark lags behind the direct breed result URL.
- General all-breed pages where the landing page links to numeric FCI groups (`R=1` ... `R=10`).
- Specialty pages where the landing page is BIS-focused and the real breed list is under `R=R` / `Rotujen tulokset`.

If `R=R` is present, the parser fetches that aggregate breed-list page instead of fetching numeric group pages.

Environment knobs:

- `DOG_INDEX_DIR`: base directory for dog state; also the default location of `dog.db`.
- `DOG_DATABASE_URI`: full SQLAlchemy URL for the `/dog` database; defaults to `dog.db` inside `DOG_INDEX_DIR`.
- `DOG_RESULT_LIVE_TTL`: TTL for currently ongoing whole-show result caches, seconds.
- `DOG_RESULT_BIS_FINAL_GRACE_SECONDS`: seconds to keep live polling after main BIS appears in cached awards; defaults to `1800`.
- `DOG_RESULT_LIVE_PROBE_BREED_LIMIT`: max unchecked breeds to probe during one live whole-show refresh; defaults to `64`.
- `DOG_RESULT_FINALS_SWEEP_BREED_LIMIT`: max already-captured breeds re-checked per pass for finals (`RYP`/`BIS`) once all breeds are judged but `BIS-1` is still missing; defaults to `30`. Bounds the end-of-show finals sweep so it never re-crawls the whole show at once.
- `DOG_INDEX_RELOAD_MIN_INTERVAL`: minimum seconds between full in-memory index rebuilds per process; defaults to `1.0`. The generation check is cheap, but a busy live show makes the crawler bump the generation often and one `/api/dog/shows` hit re-checks it several times — without this floor each did a full `read_index` rebuild and starved the request workers.
- `DOG_RESULT_LIVE_JOB_STALE_SECONDS`: seconds before a non-heartbeating live result job can be claimed again; defaults to `DOG_RESULT_LIVE_TTL`.
- `DOG_RESULT_ACTIVE_TTL`: legacy recent-show TTL setting; dated past shows now use the single final post-show check plus settled TTL.
- `DOG_RESULT_SETTLED_TTL`: TTL for settled recent whole-show caches, seconds.
- `DOG_RESULT_SETTLED_AFTER_DAYS`: days after show date before using settled TTL.
- `DOG_RESULT_AUTO_WINDOW_DAYS`: how many past days automatic warming covers.
- `DOG_RESULT_SHOW_MORNING_HOUR`: local hour before which result pages are not checked on a show day; defaults to `6`.
- `DOG_RESULT_SHOW_EVENING_HOUR`: local hour after which live result pages are no longer checked on a show day; defaults to `21`. Together with the morning hour this is the overnight quiet window for live shows.
- `DOG_RESULT_PAUSE_STALL_SECONDS`: result-stall length that flips a non-final multi-day show to the `Jatkuu` display state during the evening wind-down; defaults to `7200` (2h). Display only — does not affect fetching.
- `DOG_RESULT_PAUSE_EVENING_HOUR`: earliest local hour the stall trigger may apply, so a slow midday breed ring or crawler lag can't fake `Jatkuu`; defaults to `17`.
- `DOG_RESULT_TIMEZONE`: IANA timezone used to evaluate show dates and the morning/evening result windows; defaults to `Europe/Helsinki`. The crawler/web containers run in UTC, so this is resolved explicitly via `tzdata` rather than the process clock.
- `DOG_RESULT_IMMEDIATE_WARMUP`: set to `false` to disable user-triggered immediate warmup in web workers.
- `DOG_RESULT_IMMEDIATE_MAX_ACTIVE`: max immediate warmups per web worker.
- `DOG_BACKFILL_START_HOUR` / `DOG_BACKFILL_END_HOUR`: Finnish local off-peak window for the historical backfill; defaults to `0`–`6` (00:00–06:00). End is exclusive; the window may wrap midnight.
- `DOG_BACKFILL_DELAY`: seconds between backfill breed-result requests; defaults to `2.0`. Prefer raising this over adding workers if Showlink ever slows.
- `DOG_BACKFILL_WORKERS`: concurrent requests per backfill show; defaults to `1` (deliberately serial — the backfill must never be bursty).
- `DOG_BACKFILL_SHOW_LIMIT`: max shows to backfill per crawler pass; defaults to `1`.
- `DOG_BACKFILL_BREED_BUDGET`: max breeds crawled per backfill pass before the pass returns; defaults to `25` (≈50s at the 2s spacing). A show larger than the budget is crawled across several passes (resuming per-breed) instead of holding the crawler loop for one long crawl.

## Historical Backfill (Phase C)

`scripts/dog_crawl.py --backfill` enables an off-peak, oldest-first crawl that captures full results for shows beyond the live/auto window. It is a no-op outside the Finnish 00:00–06:00 window and while any user/live result job is queued or running, so it never competes with live work. It selects the **oldest not-yet-captured** show with result-bearing breeds, crawls it via the normal result-cache path (single worker, `DOG_BACKFILL_DELAY` between requests), and marks it complete. A complete show is **permanently captured and never re-crawled** — the backfill only advances into not-yet-captured history.

Oldest-first is deliberate: Showlink keeps a **rolling ~24-month window** and silently drops older shows (their pages return an empty shell, results gone for good). Oldest-first races that window so the most at-risk history is secured first; recent shows are already covered by the auto-warm and live-refresh paths. A show that has already aged out is recorded complete with zero results and not retried.

Each backfill fetch captures everything the result page offers in one pass: per-dog `competitive_placement` (PU/PN), and the breed honor-roll (`dog_breed_award`: ROP/VSP/SERT/veteran/junior/breeder winners with owner/kennel), in addition to the grades, awards, critiques, and judges already captured.

Backfill passes are **bounded by `DOG_BACKFILL_BREED_BUDGET`** (default 25 breeds): a 200+ breed historical show is crawled in chunks across consecutive passes rather than holding the loop for one ~7–8 minute crawl. The crawl is resumable per-breed, so each pass continues the same show (`status="incomplete"`) until the final pass marks it complete. This keeps the queued/auto/live passes responsive between backfill chunks.

### One-off re-crawl of pre-Phase-C shows

A handful of shows were captured between Phase B (SQL migration) and Phase C (full-data capture); their result rows lack `competitive_placement` and they have no `dog_breed_award` rows. `scripts/dog_recrawl_pre_phase_c.py` is a one-off that finds exactly those shows (complete caches with result rows but zero non-empty `competitive_placement` and zero awards) and force-re-crawls them oldest-first so they gain the new fields. It is **not** part of the crawler loop.

Before forcing each show it fetches the live Showlink detail page and only re-crawls if the show **still serves result-bearing breeds** — a show that has aged out of Showlink's window is skipped and its captured data is left intact (a force re-crawl would otherwise overwrite it with an empty result set). Run it against the host `./app/data` like the other one-off migrations:

```bash
SECRET_KEY=dev python3 scripts/dog_recrawl_pre_phase_c.py --dry-run   # list selected ids
SECRET_KEY=dev python3 scripts/dog_recrawl_pre_phase_c.py             # re-crawl all (oldest first)
SECRET_KEY=dev python3 scripts/dog_recrawl_pre_phase_c.py --limit 5   # oldest 5 only
```

Unlike the continuous `--backfill` (deliberately 1 worker / 2s for weeks-long unattended running), this watched one-off **defaults to the live result-crawl rate** (`--workers 3 --delay 0.4`, one request per breed) — the same rate Showlink already tolerates from this site and within the crawler's worker ceiling, so it stays polite without out-muscling the loop's other passes. Lower `--workers` / raise `--delay` to be gentler. It is idempotent: once a show has the new fields it no longer matches the selector.

## Public Crawler Identity

All outbound Showlink HTTP requests are centralized in `app/dog_show/showlink.py` and use the shared headers from `app/dog_show/config.py`.

Current `User-Agent`:

```text
erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)
```

The public info page at `/dog/about-crawler` explains in Finnish and English what the crawler fetches, why it exists, and how often it runs. Keep that page, this section, and `docker-compose.yml` crawler cadence in sync when crawler behavior changes.

## Production Crawler Cadence

Current `docker-compose.yml` command:

```bash
python scripts/dog_crawl.py --loop --interval 30 --maintenance-interval 900 --auto-results-interval 120 --empty-index-interval 30 --limit 6 --delay 2.0 --empty-index-limit 20 --empty-index-delay 0.5 --queued-result-limit 1 --auto-result-limit 2 --result-delay 0.4 --result-workers 3 --backfill
```

This means:

- Every 30 seconds: repair up to 20 stale empty breed-index entries with 0.5 seconds between requests.
- Every 30 seconds: process queued whole-show result jobs.
- Every 15 minutes: update up to 6 show breed indexes with 2.0 seconds between show-detail requests.
- Every 2 minutes: automatically warm up to 2 recent whole-show result caches when no queued job is active. Ongoing show caches become stale after 2 minutes by default, so live shows are eligible on each automatic result pass.
- For one whole-show cache: fetch breed result pages with up to 3 workers and 0.4 seconds between request starts.
- During a live whole-show refresh, fetch all known result breeds plus up to 64 unchecked probe breeds by default. The probe cursor is persisted in the result cache, so repeated passes sweep through unchecked breeds instead of retrying the same first rows.
- Every pass (lowest priority): one off-peak historical backfill step (`--backfill`), bounded to ~25 breeds (`DOG_BACKFILL_BREED_BUDGET`) so a large show is captured across passes. No-op outside the Finnish 00:00–06:00 window or while any user/live result job is pending. See [Historical Backfill](#historical-backfill-phase-c).

The web container is started with `DOG_NO_CRAWLER=true`; it does not run the long-lived crawler loop. It may still start an immediate bounded background warmup for a user-requested missing cache.

## Politeness And Failure Behavior

- Crawling is server-side; the frontend never fans out across all breed result pages.
- All Showlink fetches go through one shared keep-alive `requests.Session` (`showlink._SESSION`), so the many breed-page requests in a single show reuse one TCP + TLS connection instead of handshaking per request — lighter on the NUC and on Showlink, and gentler on the origin. The connection pool is sized above the result crawler's worker count.
- Whole-show result crawling saves progress after every breed, so partial work can resume.
- Queued jobs are persisted in `dog.db` (`dog_result_job`) so deploys and restarts do not lose user-requested cache work.
- Failed queued jobs are deferred with backoff, capped at 1 hour.
- A running job is considered stale after 30 minutes and can be retried.
- If a complete cache is stale, stale data can still be served while a refresh is queued.

If Showlink starts responding slowly or failing, reduce `--result-workers`, increase `--result-delay`, or lower `--auto-result-limit` before changing endpoint rate limits.

## Frontend Behavior

The `/dog` page is a standalone Nuxt page. The route file is intentionally thin; UI components, route/API orchestration, pure result helpers, and dog-only CSS live in `frontend/features/dog/`.

URL state is kept in query params:

- `?show=<show_id>` opens a show.
- `?show=<show_id>&group=<group>&breed=<breed>` opens a breed result page.

Important UI behavior:

- The list page has one search field. Empty input browses shows by month; two or more characters search shows, breeds, and judges through the indexed cache. If a judge is only present in a warmed whole-show result cache, search uses that cache and writes the judge back to the compact index.
- Active show rows display `Käynnissä` and replace the signup pill with `n/N tulosta`; a multi-day show paused for the night/evening shows `Jatkuu` instead (still with `n/N tulosta`); past and upcoming show rows show only the full signup count. Multi-day rows show a date range (`13–14`) in the calendar box.
- The show detail page has `Rotuluettelo` and `Koirat & Tulokset` tabs.
- On live show detail pages, `Tuloksia saaneet` is on by default. Breed rows with cached progress show `n/N` judged dogs and, when the toggle is active, breeds with the freshest result progress sort first.
- If the toggle is turned off during a live show, unchecked breeds remain openable so a direct breed page can be tried even before Showlink's group-list checkmark catches up.
- Whole-show filters run only against the persisted `/all-results` cache. Before show-day 06:00, the UI keeps the breed list searchable and explains that whole-show results are not checked yet.
- On the show date after 06:00, the UI allows checking whole-show data but warns that classes and results can fill in gradually as the day progresses.
- While `/all-results` is warming, the page shows an animated progress card and polls the API.
- Grade filtering keeps `HYL`, `EVA`, and `POISSA` separate.

## Operational Commands

Check crawler logs:

```bash
docker compose logs -f dog-crawler
```

Grafana also provisions a **Dog Show Logs** dashboard from
`server/observability/dashboards/dog.json`. It combines dog-crawler logs with
`/api/dog` and `/dog` request logs from the web container.

Crawler logs are structured JSON on stdout. Useful event names include
`dog_crawler_pass_complete`, `dog_crawler_index_pass_complete`,
`dog_crawler_empty_index_pass_complete`, `dog_result_cache_pass_complete`,
`dog_result_cache_job_complete`, and `dog_result_cache_complete`.

Run one crawler pass locally:

```bash
SECRET_KEY=dev python3 scripts/dog_crawl.py --limit 2 --result-limit 1 --result-workers 3 --result-delay 0.4
```

Process queued result jobs without automatic recent warming:

```bash
SECRET_KEY=dev python3 scripts/dog_crawl.py --no-auto-results --result-limit 1 --result-workers 3 --result-delay 0.4
```

Repair stale empty breed-index entries without warming result caches:

```bash
SECRET_KEY=dev DOG_INDEX_DIR="$(pwd)/app/data" python3 scripts/dog_crawl.py --no-results --no-index-maintenance --empty-index-limit 20 --empty-index-delay 0.5
```

Disable user-triggered immediate warmup for a test run:

```bash
DOG_RESULT_IMMEDIATE_WARMUP=false SECRET_KEY=dev python3 run.py
```

## One-off JSON → dog.db Migration

`scripts/migrate_dog_to_sql.py` is the reviewed one-off that loaded the legacy JSON caches (`dog_show_index.json`, `dog_result_cache/*.json`, `dog_result_jobs.json`) into `dog.db`. It reads the JSON files directly (decoupled from the now-SQL store), folds result-only judges into the breed list the way the app does lazily, writes the rows, then validates that every record round-trips back identically before reporting success. It is idempotent — it replaces all dog rows each run.

Validate-only (re-check an existing `dog.db` against the JSON, no writes):

```bash
SECRET_KEY=dev python3 scripts/migrate_dog_to_sql.py --validate-only
```

Run the migration (writes `DOG_DATABASE_URI`, default `app/data/dog.db`):

```bash
SECRET_KEY=dev python3 scripts/migrate_dog_to_sql.py
```

On the NUC, stop the web + crawler containers first, run the migration against the host `./app/data`, confirm it prints `OK: … round-trip identically`, then start the containers. `dog.db` is not Litestream-replicated; back it up manually.

## Phase C schema migration (existing dog.db)

`scripts/migrate_dog_phase_c.py` adds the Phase C capture fields to an existing `dog.db`: the `dog_result.competitive_placement` column (an additive `ALTER TABLE`) and the `dog_breed_award` table (`create_all`). It is idempotent and additive — it never drops or rewrites rows; pre-Phase-C rows simply have `NULL` competitive_placement and no honor-roll until those shows are (re)crawled. Run it once before enabling `--backfill` on the new image:

```bash
docker compose run --rm web python scripts/migrate_dog_phase_c.py   # prints what it changed
```

## Testing

Backend dog tests:

```bash
python3 -m pytest tests/test_dog.py
```

Frontend build:

```bash
cd frontend && npm run build
```

Targeted E2E spec:

```bash
cd frontend && npm run test:e2e -- dog.spec.js
```

Use `CI=1` or stop any local Flask process on port 5001 before Playwright if DB-backed specs are involved.
