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
- `GET /api/dog/shows/<show_id>`: breed list for one show, served from the persisted index only (a show the crawler has not indexed yet returns `425`/`not_indexed`). Live/recent detail responses enrich breeds with compact result progress from the whole-show cache when available.
- `GET /api/dog/shows/<show_id>/results?group=<group>&breed=<breed>`: one breed result page, extracted from the whole-show cache. A breed the cache has not captured yet returns `425`/`not_ready` (queueing a crawler job when inside the fetch window); the web tier never fetches result pages itself.
- `GET /api/dog/shows/<show_id>/all-results`: complete show result cache used by whole-show filters. Missing whole-show caches return `425`/`not_ready` instead of queueing work before the show date at 06:00 local time. The payload also carries `breed_awards` (`{"<group>:<breed_id>": [{type, name, owner, text}]}`) — each captured breed's honor roll, so the whole-show view can render ROP/VSP/SERT winners with owners without opening breed pages.
- `GET /api/dog/search?q=<query>`: search shows, breeds, and judges (SQL scans over the index), plus dogs, owners, and breeder-award kennels (`q` ≥ 3).
- `GET /api/dog/dogs?reg=<reg_id>`: cross-show dog profile — every captured result row anchored to one Kennelliitto registration number, grouped per show and sorted newest first, with owner enrichment from the honor-roll rows. `reg_id` contains a slash (`FI44694/25`) so it travels as a query parameter, never a path segment (nginx normalizes `%2F` in paths). Unknown reg → `404`; assembled read-only from `dog.db` (`app/dog_show/profile.py`), no Showlink fetching.

Rate limits are intentionally lower than internal crawler throughput:

- Most dog endpoints: `30/minute`.
- Whole-show cache endpoint: `20/minute`.

## Data Flow

1. The browser loads `/dog` and calls `/api/dog/shows`.
2. The show list is enriched from the breed index in `dog.db` (`dog_show`/`dog_breed`) with breed count and entry count when a show is indexed. If the show date range includes today, the row also reads that show's whole-show result cache to expose `result_count/entry_count` progress without scanning historical result caches. When a live show's result cache is stale, this endpoint queues a bounded server-side refresh so front-page polling can move the number forward.
3. Opening a show calls `/api/dog/shows/<show_id>`.
4. The backend serves the indexed copy from `dog.db`; the web tier never fetches Showlink detail pages (a not-yet-indexed show returns `425` until the crawler's index pass picks it up).
5. For live shows, the detail response also reads the show's result cache (`dog_result_cache`/`dog_result`) and adds per-breed `result_count`, `result_total_count`, `result_updated_at`, and `result_progress` fields when the cache has seen that breed.
6. If a live show's result cache is stale, the detail endpoint queues the same crawler job the show list queues. The open detail page polls the detail endpoint every 2 minutes.
7. Opening a single breed calls `/api/dog/shows/<show_id>/results`.
8. The single-breed endpoint extracts the breed from the complete whole-show cache; a not-yet-captured breed queues a crawler job and returns `425`.
9. Opening the whole-show filter calls `/api/dog/shows/<show_id>/all-results`.
10. If the show is still in the future, or it is the first show date before 06:00, the API returns `not_ready` and does not queue or fetch result pages.
11. If the whole-show cache is missing or stale after that threshold, the API queues a durable job for the crawler (which checks the queue every 30 seconds); web workers never fetch result pages themselves.
12. If the persisted breed index for a recent/live show is old and still has zero result-enabled breeds, the crawler's result path refreshes the Showlink breed list before deciding what result pages exist.
13. Live whole-show result refreshes also probe a bounded rotating set of unchecked breeds, because a direct breed result page can contain rows before its group-list checkmark appears. When a probe finds rows, the breed is marked `has_results` in the breed index.
14. The crawler service also processes queued jobs and proactively warms recent shows.
15. The frontend polls `/all-results` using `retry_after` while the cache is warming and shows progress from the persisted cache document.

## Persistent Storage (dog.db)

All dog state lives in a dedicated SQLite database, `dog.db`, the `/dog`-only store. Its path is `DOG_DATABASE_URI` (default: `dog.db` inside `DOG_INDEX_DIR`). In Docker that is `/app/data/dog.db`, backed by the host bind mount `./app/data:/app/data`. It uses its own standalone SQLAlchemy engine (`app/dog_show/db.py`), **not** the Flask-SQLAlchemy `db` object, because dog writes happen in background warmup threads and the separate `scripts/dog_crawl.py` process, neither of which has a Flask app context. WAL + `busy_timeout` let the web process read while the crawler writes.

This is a **permanent database, not a cache**: old shows' data is kept forever and never evicted. Retention/TTL logic governs only *when to re-fetch* live or recent shows — it must never delete captured rows.

Tables (see `app/dog_show/models.py`):

- `dog_show` + `dog_breed`: show metadata and breed lists (with per-breed judges) for search and fast show-detail reads. Global `last_updated` lives in `dog_meta`.
- `dog_result_cache` + `dog_result`: whole-show result cache documents. `dog_result_cache` holds the doc header + a JSON `meta` blob (completed/failed breeds + live-tracking fields); `dog_result` is one normalized row per dog result. Each result row also carries `breed_judge` (so a breed's judge survives independently of `dog_breed`) and `competitive_placement` (the PU/PN best-of-sex ranking). Replaces `dog_result_cache/<show_id>.json`.
- `dog_breed_award`: breed honor-roll winners (ROP/VSP/SERT/veteran/junior/breeder) with `name` + `owner`, parsed from each result page's award table. A queryable projection of the awards also kept in the result doc's `completed_breeds` blob; rewritten per show alongside `dog_result`. Powers Phase E "wins by dog/kennel" queries.
- `dog_result_job`: durable queue for missing or stale whole-show caches. Replaces `dog_result_jobs.json`. Job rows are transient; result rows are permanent.

`dog.db` is **not** replicated to Litestream (which covers `site.db` only) — once fetched the data is effectively static and Konsta backs it up manually.

**Reads are direct queries** (2026-07 SQL-first rewrite): every request-path read — show detail, list stats, search — queries `dog.db` through `store.py`/`sqlstore.py`. There is no in-memory index mirror, no generation counter, and no per-response cache beyond the 20s stats cache and the 30-minute show-list fetch gate; cross-process freshness is just "SQLite is the truth". GET handlers are strictly read-only: judges and result flags are folded into `dog_breed` at capture time by the crawler (`_record_result_breed_success`, and the re-index merge in `crawler._update_index_show`), not healed lazily during reads. Bulk reads use Core column selects because ORM hydration dominates at tens of thousands of breed rows. Measured on production-size data (679 shows / 49k breeds / 382k results, NUC-class hardware ballpark): show detail ~5 ms, whole-show doc reconstruct ~3–15 ms, list poll ~30 ms cold / ~3 ms warm, search 80–500 ms with the broadest breed queries at the top of that range (infix `LIKE` can't use B-tree indexes; FTS5 is the escape hatch if this ever grows). For recent/live shows, complete caches with zero result breeds are still ignored and rebuilt when the index is stale or now shows result-enabled breeds.

## Freshness Policy

- Show list in-memory cache: 30 minutes. (The only fetch-gating in-memory cache left; show detail and breed results are read from `dog.db` per request.)
- A show is **recent** (`utils._show_is_recent`) when its date range falls within `DOG_SHOW_RECENT_PAST_DAYS` (7) back / `DOG_SHOW_RECENT_FUTURE_DAYS` (31) ahead — one date-based recency system for the crawler's re-index candidates, stale-flag re-probes, and result-cache freshness. The past window is the source-correction window: Showlink results are effectively immutable about a week after the show, so everything older is settled history and is never re-fetched. Month labels are the fallback when a day range is unparseable; truly unknown dates fail open as recent. Showlink relative sections such as `Tänään` and `Huomenna` work because the backend infers the year from the listed date.
- Whole-show result live TTL: 2 minutes by default while a show is still actively filling in.
- **Incremental live refresh.** A captured breed ring's results are immutable, so a live refresh of a *complete* cache re-fetches **only** breeds that newly gained results (per the show-detail checkmark) plus the bounded unchecked-breed probe — it does not re-crawl already-captured breeds. The working doc is seeded from the existing cache (`crawl_result_cache_for_show`, `seed_from_existing`) and stays `status="complete"` throughout, so an interrupted refresh never demotes a good cache. When the refresh fetches nothing new, only the header/meta is rewritten (`_save_result_cache_header`), never the thousands of result rows. `force=True` still does a deliberate full re-crawl. This replaced an earlier behavior that rebuilt the doc from empty and re-fetched every breed on every live pass — a 200+ page burst that starved the web workers on deploy/cold-start.

### Terminal detection: when a live show is "finished"

The whole redesign (2026-07) centers on one decision: stop fast-polling a show soon after it truly ends, but never before its finals are captured. Both the result-cache TTL and the front-page `is_live` badge derive their answer from a single pure function, `utils._result_live_plan(show, doc, indexed_breeds, now)`, so the crawler and the badge never disagree. The award-structure analysis it leans on lives in `finals.py` (`analyze` / `candidate_breed_keys` / `fingerprint_token`).

- **Show structure.** Dogs are graded breed by breed inside each FCI group (each breed crowns a `ROP`). When every breed in a group is judged, the group winners `RYP-1..4` are chosen from that group's `ROP` dogs — no new written grades. After **every** group has its winners, the main `BIS-1..4` is chosen from the `RYP-1` group winners. Juniors/veterans have no group stage (their `BIS JUN`/`BIS VET` land independently). Showlink appends these finals tokens onto the *winning dogs'* already-captured rows.
- **Terminal target (`finals.analyze`).** Only a **multi-group** show (indexed breeds spanning ≥2 FCI groups → `expects_main_bis`) crowns a main Best in Show. Its target is met when (a) `BIS-1` is captured **and** (b) — only once any `RYP` token has appeared — every result-bearing group has its `RYP-1`. A **multi-group specialty cluster** (erikoisnäyttely, WDS-circuit club show, palveluskoiratapahtuma) crowns `BIS-1` with **no** group stage, so it settles on `BIS-1` alone (the RYP-per-group requirement activates only on evidence of an RYP stage). A **single-group show** (breed or group specialty, e.g. a group-10-only show that awards only junior/veteran/utility BIS) crowns **no** main `BIS-1`, so its terminal is entry completion — it never enters overtime/rescue waiting for a `BIS-1` that will not come; its side BIS / group RYP are captured during the live day by the finals sweep. A finals-less show (single-breed specialty) likewise settles on entry completion / its date passing.
- **Stability confirmation.** Reaching the target is not enough to settle: the following pass must re-check the finals and produce the same `terminal_fingerprint`. A late `BIS-4` or a correction changes the fingerprint and resets `terminal_confirmed`, so nothing settles while results still move. This replaced a fixed "one rotation after BIS-1" budget that stranded `BIS-2..4` / late `RYP` (e.g. Turku KV capturing only 3 of 4 `BIS`).
- **Targeted finals fetching.** While finals are owed, the refresh re-checks only the breeds that can *structurally* carry the missing tokens (`finals.candidate_breed_keys`): groups still missing `RYP-1` → those groups' `ROP` winners; then, once every group has `RYP-1`, exactly the `RYP-1` winners' pages for the main `BIS` (≤10, known precisely); a specialty cluster → the breed `ROP` winners. Bounded per pass (`DOG_RESULT_FINALS_SWEEP_BREED_LIMIT`, default 30) and rotated via `finals_sweep_cursor`. This replaced a blind rotation over *all* captured breeds. Re-fetched rows replace the breed's old rows (no duplication).
- **Overtime, not a hard cutoff.** On a show's **final day**, a show still owing finals keeps fetching past the 21:00 evening cutoff at a slower cadence (`DOG_RESULT_OVERTIME_TTL`, 600s) until a hard nightly stop (`DOG_RESULT_FINALS_NIGHT_STOP_HOUR`, 01:00), because Showlink publishes the finals in the 21:00–23:30 window — exactly where the old cutoff silently stranded them. Earlier days of a multi-day show keep the polite 21:00–06:00 overnight lull (their per-day junior/veteran finals are picked up when judging resumes).
- **Rescue.** A show that ended with finals still owed (the crawler was down when they published) stays a fast-poll rescue candidate the next day at `DOG_RESULT_RESCUE_TTL` (900s) during fetch hours (06:00–01:00), until it is confirmed or the hard deadline. Re-arming is driven by *target-unmet*, not cache bookkeeping, so a header-only write can't disarm it. Rescue-owing shows are prioritised in `_auto_result_cache_candidates` so a busy weekend of live shows can't starve them (their per-pass cost is a handful of targeted pages).
- **Hard deadline.** `DOG_RESULT_SETTLE_DEADLINE_DAYS` (2) days after the final day, a show settles even if its terminal never appeared — logged as `settled_incomplete` (Grafana-visible), not silently frozen. This is required because the **source itself is sometimes incomplete**: a few historical shows never published a group's `RYP` or their `BIS-1`.
- **Timezone.** The morning/evening/night-stop hours and the settle deadline are all evaluated in `DOG_RESULT_TIMEZONE` (Europe/Helsinki) via `_local_dt`, never the UTC container clock. (A prior bug evaluated the crawler's fetch window in UTC while the API evaluated it in Helsinki, so the effective evening cutoff was three hours off — the accidental reason some finals were captured at all.)
- Overnight quiet hours: a live show is not checked against Showlink between `DOG_RESULT_SHOW_EVENING_HOUR` (21:00) and `DOG_RESULT_SHOW_MORNING_HOUR` (06:00) local time, on every day of a multi-day show **except** the final-day finals overtime described above. Previously-fetched results stay visible; the cache is served stale until the morning.
- Front-page display state (`stats.is_live` / `stats.is_paused`, `_show_live_phase` in `utils.py`): a live show reads as **`Käynnissä`** while judging is active, and as **`Jatkuu`** (paused) during its multi-day nightly/evening lull — the overnight quiet window, or a result stall of `DOG_RESULT_PAUSE_STALL_SECONDS` (2h) once past `DOG_RESULT_PAUSE_EVENING_HOUR` (17:00) — but only when another in-range show day still follows. The first day's pre-dawn and the final day's wind-down stay `Käynnissä`; the show flips to past only when `_result_live_plan` reports `settled`/`settled_incomplete` (terminal captured + confirmed, or the deadline hit), so an all-breed show keeps reading `Käynnissä`/`Jatkuu` through its finals instead of flipping to `done` the moment every breed ring is judged. `Jatkuu` rows keep showing today's `n/N tulosta`. This is a display distinction only; the Showlink fetch gate is unchanged.
- **Live-show serving cost.** While any list row reads `is_live`, the `/dog` page polls `/api/dog/shows` every 15s (per open client), and computing a live show's stats reconstructs its whole-show result doc from SQLite. `_show_stats_from_index` loads that doc at most once per compute and caches the result per process for `DOG_SHOW_STATS_CACHE_TTL` (20s), so poll volume and viewer count don't translate into per-request whole-show reads. This is the web-side counterpart to the crawler's incremental refresh — both keep a live show from doing work proportional to anything other than actual new data.
- **Scheduler.** `scripts/dog_crawl.py` no longer skips the auto-recent result pass when queued jobs ran in the same cycle — that starvation (web browsing keeps queueing `live-list-refresh` jobs) is what stopped a live show's finals from being fetched. The auto pass shares the budget; a show a queued job just refreshed is deduped out by the candidates' own freshness check.
- **Date-first candidate selection (2026-07 lean-up).** `_auto_result_cache_candidates` decides from the list row's parsed date alone before touching `dog.db`: upcoming shows and past shows older than `max(DOG_RESULT_AUTO_WINDOW_DAYS, DOG_RESULT_SETTLE_DEADLINE_DAYS)` (7 days at defaults) are skipped outright, since no candidate class (live refresh, overtime, rescue, recent-past warming) can reach them. Only the survivors pay for the whole-show doc load and finals analysis. Before this gate the pass hydrated every listed show's full result doc every 2 minutes — the Tulokset page lists the whole season (~600+ settled shows, ~380k result rows), which was the crawler's ~15% idle CPU baseline on the NUC.
- **One-off index sweep.** `scripts/dog_sweep_breed_judges.py` folds judges and result flags captured in the result cache into `dog_breed` wherever the retired lazy read-path healing had left gaps (914 judges + 2 flags on the 2026-07 run). Idempotent, fill-only (never overwrites); re-runnable safely but not needed in the loop — the crawler now folds these in at capture time.
- **Rescuing shows that already lost their finals.** `scripts/dog_rescue_finals.py` is a one-off operational tool (not in the crawler loop) that finds complete caches which structurally owe finals (via `finals.analyze`) and force re-crawls them oldest-first, guarded so it only forces shows Showlink still serves result-bearing breeds for. Use `--dry-run` to list, `--show <id>` to target specific shows. Shows whose source never published the tokens come back unchanged.
- Whole-show result fallback TTL when the show date is unknown: 24 hours.
- Whole-show result settled TTL: 7 days by default.
- A show is considered settled for result-cache TTL after 2 days by default.
- Automatic recent-show result warming scans shows from the last 7 days by default.
- Old shows are treated as stable once cached.
- Empty indexed breed lists without an `empty_breed_list_confirmed` marker are put first in the maintenance pass's candidate list. (The dedicated empty-index repair pass — a self-healing remnant for entries created before parser fixes — was retired in the 2026-07 lean-up once zero candidates remained; the maintenance pass retains the behavior.)
- Maintenance re-index candidates in the recent bucket are processed stalest-first (`dog_show.updated_at` ascending), so the bounded `--limit` budget round-robins the whole recent window across passes instead of re-fetching the same first-N list rows every 15 minutes.

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
- `DOG_RESULT_LIVE_PROBE_BREED_LIMIT`: max unchecked breeds to probe during one live whole-show refresh; defaults to `64`.
- `DOG_RESULT_FINALS_SWEEP_BREED_LIMIT`: max already-captured breeds re-checked per pass for finals (`RYP`/`BIS`) once all breeds are judged but `BIS-1` is still missing; defaults to `30`. Bounds the end-of-show finals sweep so it never re-crawls the whole show at once.
- `DOG_SHOW_RECENT_PAST_DAYS` / `DOG_SHOW_RECENT_FUTURE_DAYS`: the date window that makes a show "recent" (re-indexed by the crawler's maintenance pass, eligible for stale-flag re-probes); default `7` / `31` days. The past default matches the source-correction window — results older than a week are immutable.
- `DOG_SHOW_STATS_CACHE_TTL`: seconds to cache a show's computed list stats per web process; defaults to `20`. The `/dog` page polls `/api/dog/shows` every 15s while any show reads `is_live`, and a live show's stats reconstruct its whole-show result doc (thousands of rows) from SQLite. Caching the stats this long decouples that cost from the poll rate and the number of viewers. Bypassed when an explicit `today` is passed (tests).
- `DOG_RESULT_LIVE_JOB_STALE_SECONDS`: seconds before a non-heartbeating live result job can be claimed again; defaults to `DOG_RESULT_LIVE_TTL`.
- `DOG_RESULT_SETTLED_TTL`: TTL for settled recent whole-show caches, seconds.
- `DOG_RESULT_SETTLED_AFTER_DAYS`: days after show date before using settled TTL.
- `DOG_RESULT_AUTO_WINDOW_DAYS`: how many past days automatic warming covers.
- `DOG_RESULT_SHOW_MORNING_HOUR`: local hour before which result pages are not checked on a show day; defaults to `6`.
- `DOG_RESULT_SHOW_EVENING_HOUR`: local hour after which live result pages are no longer checked on a show day; defaults to `21`. Together with the morning hour this is the overnight quiet window for live shows.
- `DOG_RESULT_PAUSE_STALL_SECONDS`: result-stall length that flips a non-final multi-day show to the `Jatkuu` display state during the evening wind-down; defaults to `7200` (2h). Display only — does not affect fetching.
- `DOG_RESULT_PAUSE_EVENING_HOUR`: earliest local hour the stall trigger may apply, so a slow midday breed ring or crawler lag can't fake `Jatkuu`; defaults to `17`.
- `DOG_RESULT_TIMEZONE`: IANA timezone used to evaluate show dates and the morning/evening result windows; defaults to `Europe/Helsinki`. The crawler/web containers run in UTC, so this is resolved explicitly via `tzdata` rather than the process clock.

## Historical Completeness

Every dog show still reachable on Showlink is captured with `status='complete'` in `dog_result_cache` (the Phase C backfill, completed and removed 2026-07 — see git history for the off-peak backfill machinery). Showlink keeps a **rolling ~24-month window** and silently drops older shows; captured history in `dog.db` is permanent and survives that. New and recent shows get complete caches via the auto-warm (7-day window), queued-job, and live-refresh paths, so the database stays complete going forward without any backfill.

Every result fetch captures the full data the page offers in one pass: per-dog `competitive_placement` (PU/PN) and the breed honor-roll (`dog_breed_award`: ROP/VSP/SERT/veteran/junior/breeder winners with owner/kennel), in addition to grades, awards, critiques, and judges.

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
python scripts/dog_crawl.py --loop --interval 30 --maintenance-interval 900 --auto-results-interval 120 --limit 6 --delay 2.0 --queued-result-limit 1 --auto-result-limit 2 --result-delay 0.4 --result-workers 3
```

This means:

- Every 30 seconds: process queued whole-show result jobs.
- Every 15 minutes: update up to 6 show breed indexes (missing, unconfirmed-empty, and recent shows stalest-first) with 2.0 seconds between show-detail requests.
- Every 2 minutes: automatically warm up to 2 recent whole-show result caches when no queued job is active. Candidate selection is date-gated to the last 7 days plus live/upcoming-window shows, so with no recent shows the pass costs ~nothing. Ongoing show caches become stale after 2 minutes by default, so live shows are eligible on each automatic result pass.
- For one whole-show cache: fetch breed result pages with up to 3 workers and 0.4 seconds between request starts.
- During a live whole-show refresh, fetch all known result breeds plus up to 64 unchecked probe breeds by default. The probe cursor is persisted in the result cache, so repeated passes sweep through unchecked breeds instead of retrying the same first rows.

The web container never talks to Showlink except for the 30-minute show-list refresh: show detail is served from the persisted index only, breed results only from the whole-show cache, and missing/stale caches are queued as `dog_result_job` rows for the crawler. All page fetching (indexing, result crawling, live refreshes) happens in the `dog-crawler` service.

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
- `?dog=<reg_id>` opens the cross-show dog profile (one `GET /api/dog/dogs` request; entries grouped by show, newest first; the show header and per-entry breed line deep-link back into the show/breed views).

Important UI behavior:

- The list page has one search field. Empty input browses shows by month; two or more characters search shows, breeds, and judges through the indexed cache. Show/breed/judge search runs as SQL `LIKE` scans over `dog_show`/`dog_breed` (`sqlstore.search_breeds_by_name` / `search_breeds_by_judge` / `search_show_ids`), assembled and ordered in `search.py` (per show: breed match > judge match > show-text match; the final list is sorted by show date, newest first, across every match type — parsed from the show's `date`, its title, or the month label, with show id breaking ties). Queries of three or more characters additionally match cross-show entities via SQL (`app/dog_show/sqlstore.py`, behind `store.py`), interleaved into the same newest-first date order: **dogs** (`search_dogs_by_name` — one hit per distinct registered dog, aggregated by `dog_result.reg_id` with the newest-show name/`reg_id`/career counts, anchored to the newest show for date sorting; the ~3% of rows without a reg_id fall back to per-show hits via `search_dog_results_by_name`, capped at 10), **owners** (`search_breed_award_owners` — one hit per breed honor roll with `group`/`breed_id`/`breed_name`/`winner` so the client deep-links the breed result page), and **kennels** (`search_breeder_awards` — breeder-award `kasvattaja` rows, whose `name` column holds the kennel; same per-breed deep-link fields, `match: "kennel"`). Registered-dog/owner/kennel matches are bounded to 20 each. Case-insensitivity for å/ä/ö is handled by OR-ing raw/upper/lower LIKE patterns (no normalized column/migration); `%`/`_` are escaped so a literal `100%` search can't wildcard.
- Active show rows display `Käynnissä` and replace the signup pill with `n/N tulosta`; a multi-day show paused for the night/evening shows `Jatkuu` instead (still with `n/N tulosta`); past and upcoming show rows show only the full signup count. Multi-day rows show a date range (`13–14`) in the calendar box.
- The show detail page is a single screen: the breed list (groupable by FCI group / judge / alphabetically) plus a whole-show filter panel. There are no `Koirat & Tulokset` content tabs; breed rows expand in place to show their dogs once the whole-show cache is loaded.
- On live show detail pages, `Tuloksia saaneet` is on by default. Breed rows with cached progress show `n/N` judged dogs and, when the toggle is active, breeds with the freshest result progress sort first.
- If the toggle is turned off during a live show, unchecked breeds remain openable so a direct breed page can be tried even before Showlink's group-list checkmark catches up.
- Whole-show results auto-load when a show detail opens — every reachable show is permanently cached, so a complete `/all-results` cache fills the filters instantly with no load button. Before show-day 06:00 (`upcoming`/`show_morning`), nothing is fetched: the UI keeps the breed list searchable and explains that whole-show results are not checked yet, and a one-shot timer auto-loads them the moment the 06:00 window opens.
- On the show date after 06:00, whole-show data auto-loads but the UI warns that classes and results can fill in gradually as the day progresses.
- While `/all-results` is warming (live or still-crawling shows), the page shows an animated progress card and polls the API using `retry_after`.
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
`dog_result_cache_pass_complete`, `dog_result_cache_job_complete`,
and `dog_result_cache_complete`.

Run one crawler pass locally:

```bash
SECRET_KEY=dev python3 scripts/dog_crawl.py --limit 2 --result-limit 1 --result-workers 3 --result-delay 0.4
```

Process queued result jobs without automatic recent warming:

```bash
SECRET_KEY=dev python3 scripts/dog_crawl.py --no-auto-results --result-limit 1 --result-workers 3 --result-delay 0.4
```

Refresh breed indexes (missing / unconfirmed-empty / recent) without warming result caches:

```bash
SECRET_KEY=dev DOG_INDEX_DIR="$(pwd)/app/data" python3 scripts/dog_crawl.py --no-results --limit 6 --delay 2.0
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
