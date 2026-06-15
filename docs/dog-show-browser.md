# Dog Show Browser

## Purpose

The dog show browser powers `/dog` and the `/api/dog/*` endpoints. It reads public Showlink result pages server-side, normalizes them, and caches the expensive whole-show result data so UI filtering does not create hundreds of browser or API requests.

The design goal is fast reads for users and polite, bounded crawling toward Showlink.

## Entry Points

- Frontend page: `frontend/pages/dog.vue`
- Flask blueprint: `app/api/dog.py`
- Crawler process: `scripts/dog_crawl.py`
- Production service: `dog-crawler` in `docker-compose.yml`

## Public API

- `GET /api/dog/shows`: current Showlink show list plus index status and compact cached row stats when indexed.
- `GET /api/dog/shows/<show_id>`: breed list for one show.
- `GET /api/dog/shows/<show_id>/results?group=<group>&breed=<breed>`: one breed result page.
- `GET /api/dog/shows/<show_id>/all-results`: complete show result cache used by whole-show filters.
- `GET /api/dog/search?q=<query>`: search shows and indexed breeds.

Rate limits are intentionally lower than internal crawler throughput:

- Most dog endpoints: `30/minute`.
- Whole-show cache endpoint: `20/minute`.

## Data Flow

1. The browser loads `/dog` and calls `/api/dog/shows`.
2. The show list is enriched from `dog_show_index.json` with breed count, entry count, and result-breed count when a show is indexed.
3. Opening a show calls `/api/dog/shows/<show_id>`.
4. If `dog_show_index.json` already contains the show and breed list, the backend serves that indexed copy without fetching Showlink.
5. Opening a single breed calls `/api/dog/shows/<show_id>/results`.
6. If a complete whole-show result cache exists, the single-breed endpoint extracts the breed from that cache instead of fetching Showlink.
7. Opening the `Koirat & Tulokset` tab calls `/api/dog/shows/<show_id>/all-results`.
8. If the whole-show cache is missing or stale, the API queues a durable job and starts one bounded immediate background warmup in the web worker when allowed.
9. The crawler service also processes queued jobs and proactively warms recent shows.
10. The frontend polls `/all-results` using `retry_after` while the cache is warming and shows progress from the persisted cache document.

## Persistent Files

All dog crawler state is JSON under `DOG_INDEX_DIR`. In Docker this is `/app/data`, backed by the host bind mount `./app/data:/app/data`.

- `dog_show_index.json`: show metadata and breed lists for search and fast show-detail reads.
- `dog_result_cache/<show_id>.json`: whole-show result cache documents.
- `dog_result_jobs.json`: durable queue for missing or stale whole-show caches.

These files are not SQLite tables. Litestream currently replicates `/data/site.db` only, so these JSON files are persistent on disk but not covered by the Litestream database backup policy.

Do not delete `app/data` or the whole `dog_result_cache` directory casually. To repair one bad result cache, remove only `app/data/dog_result_cache/<show_id>.json`; the next read or crawler pass will rebuild it.

## Freshness Policy

- Show list in-memory cache: 30 minutes.
- Show detail in-memory cache for recent or ongoing shows: 10 minutes.
- Breed result in-memory cache for recent or ongoing shows: 10 minutes.
- Whole-show result fallback TTL when the show date is unknown: 24 hours.
- Whole-show result active TTL: 6 hours by default.
- Whole-show result settled TTL: 7 days by default.
- A show is considered settled for result-cache TTL after 2 days by default.
- Automatic recent-show result warming scans shows from the last 7 days by default.
- Old shows are treated as stable once cached.
- Empty indexed breed lists without an `empty_breed_list_confirmed` marker are prioritized by the crawler. This self-heals older cache entries created before parser fixes.

## Showlink Page Shapes

Supported show-detail shapes:

- Specialty pages where the landing page already contains `table.rotulistatable`.
- General all-breed pages where the landing page links to numeric FCI groups (`R=1` ... `R=10`).
- Specialty pages where the landing page is BIS-focused and the real breed list is under `R=R` / `Rotujen tulokset`.

If `R=R` is present, the parser fetches that aggregate breed-list page instead of fetching numeric group pages.

Environment knobs:

- `DOG_INDEX_DIR`: base directory for dog JSON state.
- `DOG_RESULT_CACHE_DIR`: override whole-show result cache directory.
- `DOG_RESULT_JOBS_PATH`: override result job queue path.
- `DOG_RESULT_ACTIVE_TTL`: TTL for active recent whole-show caches, seconds.
- `DOG_RESULT_SETTLED_TTL`: TTL for settled recent whole-show caches, seconds.
- `DOG_RESULT_SETTLED_AFTER_DAYS`: days after show date before using settled TTL.
- `DOG_RESULT_AUTO_WINDOW_DAYS`: how many past days automatic warming covers.
- `DOG_RESULT_IMMEDIATE_WARMUP`: set to `false` to disable user-triggered immediate warmup in web workers.
- `DOG_RESULT_IMMEDIATE_MAX_ACTIVE`: max immediate warmups per web worker.

## Production Crawler Cadence

Current `docker-compose.yml` command:

```bash
python scripts/dog_crawl.py --loop --interval 30 --maintenance-interval 900 --auto-results-interval 120 --limit 6 --delay 2.0 --queued-result-limit 1 --auto-result-limit 2 --result-delay 0.4 --result-workers 3
```

This means:

- Every 30 seconds: process queued whole-show result jobs.
- Every 15 minutes: update up to 6 show breed indexes with 2.0 seconds between show-detail requests.
- Every 2 minutes: automatically warm up to 2 recent whole-show result caches when no queued job is active.
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

The `/dog` page is a standalone Nuxt page. URL state is kept in query params:

- `?show=<show_id>` opens a show.
- `?show=<show_id>&group=<group>&breed=<breed>` opens a breed result page.

Important UI behavior:

- The list page has show browsing and indexed breed search tabs.
- The show detail page has `Rotuluettelo` and `Koirat & Tulokset` tabs.
- Whole-show filters run only against the persisted `/all-results` cache.
- While `/all-results` is warming, the page shows an animated progress card and polls the API.
- Grade filtering keeps `HYL`, `EVA`, and `POISSA` separate.

## Operational Commands

Check crawler logs:

```bash
docker compose logs -f dog-crawler
```

Run one crawler pass locally:

```bash
SECRET_KEY=dev python3 scripts/dog_crawl.py --limit 2 --result-limit 1 --result-workers 3 --result-delay 0.4
```

Process queued result jobs without automatic recent warming:

```bash
SECRET_KEY=dev python3 scripts/dog_crawl.py --no-auto-results --result-limit 1 --result-workers 3 --result-delay 0.4
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
