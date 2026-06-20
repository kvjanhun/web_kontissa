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
- Persistent dog state is JSON under `DOG_INDEX_DIR`, not SQLite. Do not delete `app/data`, `dog_show_index.json`, `dog_result_jobs.json`, or `dog_result_cache/` casually.
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
- `GET /api/dog/shows/<show_id>`: breed list for one show.
- `GET /api/dog/shows/<show_id>/results?group=<group>&breed=<breed>`: one breed result page. Missing result pages are not fetched before the show date at 06:00 local time.
- `GET /api/dog/shows/<show_id>/all-results`: complete show result cache used by whole-show filters. Missing whole-show caches return `425`/`not_ready` instead of queueing work before the show date at 06:00 local time.
- `GET /api/dog/search?q=<query>`: search shows and indexed breeds.

Rate limits are intentionally lower than internal crawler throughput:

- Most dog endpoints: `30/minute`.
- Whole-show cache endpoint: `20/minute`.

## Data Flow

1. The browser loads `/dog` and calls `/api/dog/shows`.
2. The show list is enriched from `dog_show_index.json` with breed count and entry count when a show is indexed. If the show date range includes today, the row also reads that show's whole-show result cache to expose `result_count/entry_count` progress without scanning historical result caches. When a live show's result cache is stale, this endpoint queues a bounded server-side refresh so front-page polling can move the number forward.
3. Opening a show calls `/api/dog/shows/<show_id>`.
4. If `dog_show_index.json` already contains the show and breed list, the backend serves that indexed copy without fetching Showlink.
5. Opening a single breed calls `/api/dog/shows/<show_id>/results`.
6. If a complete whole-show result cache exists, the single-breed endpoint extracts the breed from that cache instead of fetching Showlink.
7. Opening the whole-show filter calls `/api/dog/shows/<show_id>/all-results`.
8. If the show is still in the future, or it is the first show date before 06:00, the API returns `not_ready` and does not queue or fetch result pages.
9. If the whole-show cache is missing or stale after that threshold, the API queues a durable job and starts one bounded immediate background warmup in the web worker when allowed.
10. If the persisted breed index for a recent/live show is old and still has zero result-enabled breeds, the detail and whole-show result paths refresh the Showlink breed list before deciding what result pages exist.
11. The crawler service also processes queued jobs and proactively warms recent shows.
12. The frontend polls `/all-results` using `retry_after` while the cache is warming and shows progress from the persisted cache document.

## Persistent Files

All dog crawler state is JSON under `DOG_INDEX_DIR`. In Docker this is `/app/data`, backed by the host bind mount `./app/data:/app/data`.

- `dog_show_index.json`: show metadata, breed lists, and known breed judges for search and fast show-detail reads.
- `dog_result_cache/<show_id>.json`: whole-show result cache documents. These also carry breed-level judges; search can use this data and backfill missing judges into `dog_show_index.json`.
- `dog_result_jobs.json`: durable queue for missing or stale whole-show caches.

These files are not SQLite tables. Litestream currently replicates `/data/site.db` only, so these JSON files are persistent on disk but not covered by the Litestream database backup policy.

Do not delete `app/data` or the whole `dog_result_cache` directory casually. To repair one bad result cache, remove only `app/data/dog_result_cache/<show_id>.json`; the next read or crawler pass will rebuild it.
For recent/live shows, complete caches with zero result breeds are ignored and rebuilt when the index is stale or now shows result-enabled breeds.

## Freshness Policy

- Show list in-memory cache: 30 minutes.
- Show detail in-memory cache for recent or ongoing shows: 10 minutes.
- Breed result in-memory cache for recent or ongoing shows: 10 minutes.
- Showlink relative sections such as `Tänään` and `Huomenna` are treated as recent; the backend infers the year from the listed date so live-result availability still works.
- Whole-show result live TTL: 2 minutes by default.
- Whole-show result fallback TTL when the show date is unknown: 24 hours.
- Whole-show result active TTL for recent non-live shows: 6 hours by default.
- Whole-show result settled TTL: 7 days by default.
- A show is considered settled for result-cache TTL after 2 days by default.
- Automatic recent-show result warming scans shows from the last 7 days by default.
- Old shows are treated as stable once cached.
- Empty indexed breed lists without an `empty_breed_list_confirmed` marker are prioritized by the crawler. This self-heals older cache entries created before parser fixes.

## Showlink Page Shapes

Supported show-detail shapes:

- Specialty pages where the landing page already contains `table.rotulistatable`.
- Single-breed specialty pages where `table.rotulistatable` has no result checkmark but the direct breed URL can already contain results.
- General all-breed pages where the landing page links to numeric FCI groups (`R=1` ... `R=10`).
- Specialty pages where the landing page is BIS-focused and the real breed list is under `R=R` / `Rotujen tulokset`.

If `R=R` is present, the parser fetches that aggregate breed-list page instead of fetching numeric group pages.

Environment knobs:

- `DOG_INDEX_DIR`: base directory for dog JSON state.
- `DOG_RESULT_CACHE_DIR`: override whole-show result cache directory.
- `DOG_RESULT_JOBS_PATH`: override result job queue path.
- `DOG_RESULT_LIVE_TTL`: TTL for currently ongoing whole-show result caches, seconds.
- `DOG_RESULT_ACTIVE_TTL`: TTL for recent non-live whole-show caches, seconds.
- `DOG_RESULT_SETTLED_TTL`: TTL for settled recent whole-show caches, seconds.
- `DOG_RESULT_SETTLED_AFTER_DAYS`: days after show date before using settled TTL.
- `DOG_RESULT_AUTO_WINDOW_DAYS`: how many past days automatic warming covers.
- `DOG_RESULT_SHOW_MORNING_HOUR`: local hour when missing result pages may first be checked on the first show date; defaults to `6`.
- `DOG_RESULT_IMMEDIATE_WARMUP`: set to `false` to disable user-triggered immediate warmup in web workers.
- `DOG_RESULT_IMMEDIATE_MAX_ACTIVE`: max immediate warmups per web worker.

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
python scripts/dog_crawl.py --loop --interval 30 --maintenance-interval 900 --auto-results-interval 120 --empty-index-interval 30 --limit 6 --delay 2.0 --empty-index-limit 20 --empty-index-delay 0.5 --queued-result-limit 1 --auto-result-limit 2 --result-delay 0.4 --result-workers 3
```

This means:

- Every 30 seconds: repair up to 20 stale empty breed-index entries with 0.5 seconds between requests.
- Every 30 seconds: process queued whole-show result jobs.
- Every 15 minutes: update up to 6 show breed indexes with 2.0 seconds between show-detail requests.
- Every 2 minutes: automatically warm up to 2 recent whole-show result caches when no queued job is active. Ongoing show caches become stale after 2 minutes by default, so live shows are eligible on each automatic result pass.
- For one whole-show cache: fetch breed result pages with up to 3 workers and 0.4 seconds between request starts.

The web container is started with `DOG_NO_CRAWLER=true`; it does not run the long-lived crawler loop. It may still start an immediate bounded background warmup for a user-requested missing cache.

## Politeness And Failure Behavior

- Crawling is server-side; the frontend never fans out across all breed result pages.
- Whole-show result crawling saves progress after every breed, so partial work can resume.
- Queued jobs use durable JSON state so deploys and restarts do not lose user-requested cache work.
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
- Active show rows display `Käynnissä` and replace the signup pill with `n/N tulosta`; past and upcoming show rows show only the full signup count.
- The show detail page has `Rotuluettelo` and `Koirat & Tulokset` tabs.
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
