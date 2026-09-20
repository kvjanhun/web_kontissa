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
- `GET /api/dog/shows/<show_id>/all-results`: complete show result cache used by whole-show filters. Missing whole-show caches return `425`/`not_ready` instead of queueing work outside the fetch window (08:00–21:00 local). The payload also carries `breed_awards` (`{"<group>:<breed_id>": [{type, name, owner, text}]}`) — each captured breed's honor roll, so the whole-show view can render ROP/VSP/SERT winners with owners without opening breed pages.
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
10. If the show is still in the future, or the fetch window is closed (before 08:00, or from 21:00), the API returns `not_ready` and does not queue or fetch result pages.
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
- **When a breed capture is final (`_breed_capture_is_settled`).** Showlink flags a breed as having results the moment its **first class** is judged and fills the rest of the page as the ring proceeds, so a live pass reads whatever was published at that second. Three states, and conflating any two of them breaks something. A capture is **final** once the source says the ring ended — its honour roll crowns `ROP` (the bare token; `ROP juniori`/`ROP pentu`/`ROP kasvattaja` are class and breeder titles that land earlier, while a championship suffix like `ROP, V-24` is still the breed's own) — or once full rows come back unchanged on a later fetch (`rows_confirmed_at`), which is what a breed with no honour roll can offer. Full rows on their **first** sighting are **provisional** (`_breed_capture_is_provisional`): they stop the breed being fast-polled and leave it eligible for re-check, but the ring is finished, so a provisional capture never blocks the show from settling and is never worth healing. Only a **partial** capture (`_breed_capture_is_partial` — no `ROP` *and* fewer rows than entries) is a ring read mid-judging. Showlink publishes class rows before the honour roll, so treating a full-looking page as final froze 29 of show 14014's 96 breeds — two of them the group winners its finals were waiting on. The arm cannot simply be deleted either: a single-entry breed genuinely gets no honour roll, so full rows must eventually mean something.
- **Incremental live refresh.** A live refresh of a *complete* cache fetches only breeds that newly gained results (per the show-detail checkmark), the bounded unchecked-breed probe, and the breed attention tiers below. The working doc is seeded from the existing cache (`crawl_result_cache_for_show`, `seed_from_existing`) and stays `status="complete"` throughout, so an interrupted refresh never demotes a good cache. Keep it seeded: rebuilding the doc from empty on every live pass is a 200+ page burst that starves the web workers on deploy/cold-start. When the refresh fetches nothing new, only the header/meta is rewritten (`_save_result_cache_header`), never the thousands of result rows. `force=True` does a deliberate full re-crawl; `heal=True` re-fetches only the unsettled captures, ignoring the fetch window and cache TTL.
- **Re-checks end with the show.** An unsettled capture is re-fetchable only while the plan permits fetching (live day, post-show rescue), so a ring the source never finishes costs at most a bounded slice per pass until the show settles. The cool sweep likewise runs only while the show is live — re-reading finished history is exactly the traffic this design removes. The hard deadline below is what bounds it; a per-breed give-up counter would only duplicate that.

### Terminal detection: when a live show is "finished"

Two goals in tension: spend requests where data is actually changing, and never settle a show while the source is still moving — including a correction typed in after the ring has passed. Both the result-cache TTL and the front-page badge derive their answer from a single pure function, `utils._result_live_plan(show, doc, indexed_breeds, now)`, so the crawler and the badge never disagree. It reads the settle ladder in `utils._terminal_status`, which reads `finals.py` (`probe_state` / `analyze` / `candidate_breed_keys` / `fingerprint_token`) and the finals probe the crawler stores on the doc.

- **Show structure.** Dogs are graded breed by breed inside each FCI group (each breed crowns a `ROP`). When every breed in a group is judged, the group winners `RYP-1..4` are chosen from that group's `ROP` dogs — no new written grades. After **every** group has its winners, the main `BIS-1..4` is chosen from the `RYP-1` group winners. Juniors/veterans have no group stage (their `BIS JUN`/`BIS VET` land independently). Showlink appends these finals tokens onto the *winning dogs'* already-captured rows.
- **The finals probe.** A show's own `R=RYP` and `R=BIS` pages state what it has awarded, and `result_cache._probe_finals_pages` reads them into `doc["finals_probe"]`. They are the authority **when they hold placements**; empty ones are not evidence of anything, because many shows never populate them and append the finals to the winners' breed rows instead. Two requests answer directly what breed re-reads could only guess: whether the finals exist, how the show actually partitions its rings, and which dog won what. `parsers._parse_finals_page` returns one section per ring or final (heading, judge, up to four placements with the winner's breed and registration number). **A final is rendered two ways and both must be read:** placement rows until its photos are uploaded, then a `tr.gallery` of captioned photos that replaces them. Every show makes that swap, within hours of the ring, and the caption carries the same place / breed / dog / owner in the same order — so reading only the row form makes a show's finals pages go blank a few hours after it ends, which is indistinguishable from a source that never published them. **The section heading is the only place a combined ring is visible** — a show judging FCI 5 and 6 together writes one `FCI 5/6` section with one `RYP-1`, so deriving one expected `RYP-1` per indexed group makes such a show's terminal unreachable by construction. Cadence: nothing can be awarded before something has been judged, so the probe waits for the first capture, then runs at `DOG_RESULT_FINALS_PROBE_TTL` (600s) while the pages are empty, then every pass once they show anything or every ring is captured.
- **The settle ladder (`utils._terminal_status`).** In order: (1) **finals in** — every final the show owes has landed on its breed's rows; (2) **nothing left to judge** — every listed breed is checked and its capture is no longer mid-ring, which is what a lunch break cannot fake, since mid-show there are always breeds unstarted or mid-ring; (3) **quiescence confirms** — the signature must come back unchanged for `DOG_RESULT_QUIESCENCE_SECONDS` (1800s); (4) the hard deadline backstops. Rung 1 has two sources and needs both. Finals pages holding placements settle it outright, naming each winner — checked against the FCI groups the index says have entries, so a group with entries and no ring yet is still outstanding while a combined `FCI 5/6` ring covers both at once, and against the **main** Best in show section specifically, since a two-day show's junior and veteran BIS sit on the same page a day earlier. Crowned groups are unioned from the pages and from the `RYP-1` tokens on captured rows, each a partial view of the same fact: a combined ring is visible only on the page, and a show that never populates its pages says it only on the rows. The check is suspended only when that union is empty, which is the specialty cluster running no group stage at all — suspending it whenever the *pages* name no group hands a settle to any all-breed show the moment its BIS page publishes, every group unaccounted for. Where the pages are empty the award tokens already on the captured rows decide instead: a show holding `RYP` or `BIS` tokens plainly awards finals, whatever its pages say, and settles only when the structure is complete. Only a show with empty pages **and** no finals token anywhere awards none, and reaches the terminal on rung 2 alone. **No rung asks what kind of show this is**, which is what stops combined rings, group-only shows, puppy shows and single-breed specialties from being special cases. Where the probe has not been read at all (an old cache, or every fetch failed — the two are distinguished, a failed probe carries no pages and never reads as "no finals"), the award-structure inference in `finals.analyze` is the fallback.
- **Quiescence counts observed time only.** `_mark_terminal_confirmation` accumulates the gap between consecutive passes whose signature matched, and discards any gap longer than `DOG_RESULT_QUIESCENCE_MAX_GAP` (360s) — the night stop, a restart, a run of failures. Without that the overnight silence alone would settle every show at the morning re-open. Stability accumulates whether or not the target is met; resetting it on unmet passes meant a show with an unreachable terminal could never build evidence that it had simply stopped, and polled to the deadline instead.
- **Targeted finals fetching.** `finals.candidate_breed_keys` returns exactly the breeds the finals pages name whose captured rows lack the promised token — matched on the winner's registration id, the same identity `dog_result.reg_id` stores. A placement with no dog link is the breeder-group final, which places a *kennel*: no breed row will ever carry a token for it, so it counts as published but never as an obligation. Bounded per pass (`DOG_RESULT_FINALS_SWEEP_BREED_LIMIT`) and rotated via `finals_sweep_cursor`, though with a probe the limit almost never binds. Re-fetched rows replace the breed's old rows (no duplication).
- **Breed attention tiers (`_live_tier_breeds`).** One judge judges one breed, finishes it, and moves to the next, so a show has at most one ring per judge in flight — ten judges over ninety-six breeds. **Judge queues are a priority signal only, never evidence of completion:** results are entered by club secretaries who may register a row long after its ring finished. *Hot* is each judge's first unfinished ring (`DOG_RESULT_HOT_BREED_LIMIT`); *warm* is every other capture that is not final, rotating (`DOG_RESULT_WARM_BREED_LIMIT`, `unsettled_recheck_cursor`); *cool* is captures that look final, swept slowly while the show is live (`DOG_RESULT_COOL_SWEEP_BREED_LIMIT`, `cool_sweep_cursor`) — the cool sweep is what catches the late row, and nothing else in the design would look again. Where the queue misfires (judge unknown, a ring judged out of programme order), adaptive backoff is the fallback: a breed whose rows come back unchanged `DOG_RESULT_BREED_STATIC_FETCH_LIMIT` times leaves the hot tier on its own evidence, needing no judge and no schedule.
- **Rescue.** A show that ended with finals still owed (the crawler was down when they published) stays a fast-poll rescue candidate the next day at `DOG_RESULT_RESCUE_TTL` (900s) during fetch hours, until it is confirmed or the hard deadline. Re-arming is driven by *target-unmet*, not cache bookkeeping, so a header-only write can't disarm it. Rescue-owing shows are prioritised in `_auto_result_cache_candidates` so a busy weekend of live shows can't starve them (their per-pass cost is a handful of targeted pages).
- **Hard deadline.** `DOG_RESULT_SETTLE_DEADLINE_DAYS` (2) days after the final day, a show settles even if its terminal never appeared — logged as `settled_incomplete` (Grafana-visible), not silently frozen. This is required because the **source itself is sometimes incomplete**: a few historical shows never published a group's `RYP` or their `BIS-1`.
- **Timezone.** Every date and hour decision is evaluated in `DOG_RESULT_TIMEZONE` (Europe/Helsinki) via `_local_now` / `_local_dt`, never the UTC container clock — the fetch window, the settle deadline, and a show's date-state alike. Evaluating hours against the container's UTC clock puts the evening cutoff three hours off; evaluating the *date* against it splits the two apart for the three hours between 21:00 UTC and midnight, where a show that ended that evening reads as still live on one path and past on the other.
- **The fetch window.** Nothing in the package reaches Showlink outside `DOG_RESULT_SHOW_MORNING_HOUR` (08:00) to `DOG_RESULT_SHOW_EVENING_HOUR` (21:00) local time — the result plan, the crawler's index pass and the show-list refresh all read it from `utils._in_fetch_window`. No dog show runs outside those hours, so a request made then buys nothing. It applies on every day of a multi-day show and to a past show still owing its finals: finals typed in after 21:00 are captured by the next morning's rescue pass, inside the settle deadline. Previously-fetched results stay visible; the cache is served stale until the morning. Keep the window in that one function — the same hours expressed separately per path is how the index pass ran all night unnoticed.
- **Front-page display state** (`stats.is_live` / `stats.is_paused`, `_show_live_phase` in `utils.py`): a show that has not settled always carries a badge. **`Käynnissä`** while judging is active; **`Jatkuu`** (paused) through any hold it has not concluded from — the 21:00–08:00 quiet window on any day of the show, or a result stall of `DOG_RESULT_PAUSE_STALL_SECONDS` (2h) once past `DOG_RESULT_PAUSE_EVENING_HOUR` (17:00) before another show day. The badge disappears only when `_result_live_plan` reports `settled`/`settled_incomplete`, i.e. when the settle ladder says the show is done. Deriving `is_live` from the fetch window instead made the badge vanish at 21:00 on a show still owing its finals, and no badge is indistinguishable from settled history. The first day's pre-dawn stays `Käynnissä`: nothing has happened yet to continue from. `Jatkuu` rows keep showing today's `n/N tulosta`. This is a display distinction only; the Showlink fetch gate is separate.
- **Live-show serving cost.** While any list row reads `is_live`, the `/dog` page polls `/api/dog/shows` every 15s (per open client), and computing a live show's stats reconstructs its whole-show result doc from SQLite. `_show_stats_from_index` loads that doc at most once per compute and caches the result per process for `DOG_SHOW_STATS_CACHE_TTL` (20s), so poll volume and viewer count don't translate into per-request whole-show reads. This is the web-side counterpart to the crawler's incremental refresh — both keep a live show from doing work proportional to anything other than actual new data.
- **Scheduler.** `scripts/dog_crawl.py` runs the auto-recent result pass on every cycle, including cycles where queued jobs already ran; the two share the budget, and a show a queued job just refreshed is deduped out by the candidates' own freshness check. Do not make the auto pass conditional on the queue being idle: web browsing keeps queueing `live-list-refresh` jobs, so a busy cycle is the normal case, and skipping the pass there starves live shows of their finals.
- **Date-first candidate selection (2026-07 lean-up).** `_auto_result_cache_candidates` decides from the list row's parsed date alone before touching `dog.db`: upcoming shows and past shows older than `max(DOG_RESULT_AUTO_WINDOW_DAYS, DOG_RESULT_SETTLE_DEADLINE_DAYS)` (7 days at defaults) are skipped outright, since no candidate class (live refresh, rescue, recent-past warming) can reach them. Only the survivors pay for the whole-show doc load and finals analysis. Before this gate the pass hydrated every listed show's full result doc every 2 minutes — the Tulokset page lists the whole season (~600+ settled shows, ~380k result rows), which was the crawler's ~15% idle CPU baseline on the NUC.
- **One-off index sweep.** `scripts/dog_sweep_breed_judges.py` folds judges and result flags captured in the result cache into `dog_breed` wherever the retired lazy read-path healing had left gaps (914 judges + 2 flags on the 2026-07 run). Idempotent, fill-only (never overwrites); re-runnable safely but not needed in the loop — the crawler now folds these in at capture time.
- **Rescuing shows that already lost their finals.** `scripts/dog_rescue_finals.py` is a one-off operational tool (not in the crawler loop) that finds complete caches which structurally owe finals (via `finals.analyze`) and force re-crawls them oldest-first, guarded so it only forces shows Showlink still serves result-bearing breeds for. Use `--dry-run` to list, `--show <id>` to target specific shows. Shows whose source never published the tokens come back unchanged.
- **Observing a live show day.** `scripts/dog_observe_live.py` is a read-only measurement tool (not in the crawler loop) that records how Showlink behaves while a show is being judged: the cheap pages every 2 minutes, a rotating sample of breed pages every 10, and our own `/api/dog/shows/<id>` alongside. Output is timestamped JSONL plus HTML snapshots of the `R=RYP` / `R=BIS` pages each time their markup changes — the fixtures the finals parser is written against, and the only record of a rendering the parser cannot yet read. Each finals sample counts its sections by `rendering` (placement rows against photo gallery) so the swap between them is measured rather than inferred. A full show day is ~13 hours, so run it in the crawler container on the server rather than on a laptop; `--html-dir` defaults to an `html/` beside `--out`, so pointing `--out` at the bind mount places both. It never opens `dog.db` (`DOG_DATABASE_URI` is forced to an in-memory URL) and only issues GETs, at the result crawler's user-agent and request delay. `--list` prints today's shows, `--dry-run` fetches each page type once and prints what it extracted, which is how you check the selectors still match Showlink's markup. `--until` defaults past the crawler's 21:00 cutoff deliberately: when the finals publish is one of the things being measured.

```bash
SECRET_KEY=dev python3 scripts/dog_observe_live.py --list
SECRET_KEY=dev python3 scripts/dog_observe_live.py --dry-run --show 14014
SECRET_KEY=dev python3 scripts/dog_observe_live.py --show 14014 --show 13914 \
    --out observations/2026-09-12.jsonl
```

- **Healing shows captured mid-ring.** `scripts/dog_heal_partial_breeds.py` is a one-off operational tool (not in the crawler loop) that scans every complete cache for breeds failing `_breed_capture_is_partial` and re-fetches exactly those, oldest-first, at the live crawl's request rate. It reads capture state from the cache meta blob (`store._complete_cache_captures`) rather than hydrating each show's result rows, in batches of 50 shows so the run stays inside the crawler image's 256 MB cap; a full scan of the database is a couple of seconds and peaks around 210 MB. Before crawling a show it probes up to three of that show's own mid-ring breed pages: Showlink serves roughly a season and a show past that answers every breed page empty, so it is reported `UNAVAILABLE` for three requests instead of re-reading hundreds every run. `--dry-run` lists the shows and breed counts, `--since YYYY-MM-DD` bounds the window, `--show <id>` targets specific shows. Nothing is deleted — a failed pass leaves the captured rows untouched, and a re-fetch replaces one breed's rows in place. Aim it at settled history: shows inside the crawler's own auto window are re-checked by the live/rescue passes anyway, and healing one the crawler is mid-pass on just means it re-crawls next pass. Run it in the crawler image so it sees the same `dog.db`:

```bash
docker compose run --rm -e DATABASE_URI=sqlite://  dog-crawler \
  python scripts/dog_heal_partial_breeds.py --dry-run
```
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
- `DOG_RESULT_FINALS_SWEEP_BREED_LIMIT`: max breeds re-fetched per pass to land the finals on their rows; defaults to `30`. With the finals probe the list is exact and rarely near the cap; it binds on the structural fallback, where the candidates are guesses.
- `DOG_RESULT_FINALS_PROBE_TTL`: seconds between reads of the `R=RYP` / `R=BIS` pages while they are still empty; defaults to `600`. Once they show a placement, or every ring is captured, they are read every pass.
- `DOG_RESULT_UNSETTLED_RECHECK_BREED_LIMIT`: max mid-ring captures re-checked in one heal pass; defaults to `48`.
- `DOG_RESULT_HOT_BREED_LIMIT` / `DOG_RESULT_WARM_BREED_LIMIT` / `DOG_RESULT_COOL_SWEEP_BREED_LIMIT`: the per-pass breed budget across the three attention tiers; default `12` / `24` / `12`. Hot is each judge's first unfinished ring, warm the rest of the unfinished captures, cool the slow sweep over captures that look finished (which is what catches a row registered after its ring ended).
- `DOG_RESULT_BREED_STATIC_FETCH_LIMIT`: how many unchanged re-fetches drop a breed out of the hot tier; defaults to `3`. The adaptive fallback wherever the judge queue misfires — it needs no judge and no schedule.
- `DOG_RESULT_QUIESCENCE_SECONDS`: how long a show's terminal state must come back unchanged before it may settle; defaults to `1800`. It confirms a conclusion the settle ladder already reached, never reaches one itself. Two NORD shows observed on 2026-09-19 went 18, 14, 12, 12 and 10 minutes between result rows while judging was plainly still running, so a shorter window sits inside the normal noise of a show day; a lunch break is longer again.
- `DOG_RESULT_QUIESCENCE_MAX_GAP`: the longest gap between passes that still counts as observed time; defaults to `360`. A longer one means nobody was watching (the night stop, a restart, a run of failures) and contributes nothing, or the overnight silence alone would settle every show at dawn.
- `DOG_SHOW_RECENT_PAST_DAYS` / `DOG_SHOW_RECENT_FUTURE_DAYS`: the date window that makes a show "recent" (re-indexed by the crawler's maintenance pass, eligible for stale-flag re-probes); default `7` / `31` days. The past default matches the source-correction window — results older than a week are immutable.
- `DOG_INDEX_LIVE_TTL` / `DOG_INDEX_RECENT_TTL`: how often the index pass re-reads a show being judged today versus the rest of the recent window; default `300` / `21600` seconds. A show new to the index is never rate-limited by either — it has no page at all until the pass fetches one.
- `DOG_SHOW_STATS_CACHE_TTL`: seconds to cache a show's computed list stats per web process; defaults to `20`. The `/dog` page polls `/api/dog/shows` every 15s while any show reads `is_live`, and a live show's stats reconstruct its whole-show result doc (thousands of rows) from SQLite. Caching the stats this long decouples that cost from the poll rate and the number of viewers. Bypassed when an explicit `today` is passed (tests).
- `DOG_RESULT_LIVE_JOB_STALE_SECONDS`: seconds before a non-heartbeating live result job can be claimed again; defaults to `DOG_RESULT_LIVE_TTL`.
- `DOG_RESULT_SETTLED_TTL`: TTL for settled recent whole-show caches, seconds.
- `DOG_RESULT_SETTLED_AFTER_DAYS`: days after show date before using settled TTL.
- `DOG_RESULT_AUTO_WINDOW_DAYS`: how many past days automatic warming covers.
- `DOG_RESULT_SHOW_MORNING_HOUR` / `DOG_RESULT_SHOW_EVENING_HOUR`: the fetch window, in local hours; default `8` / `21`. Nothing in the package reaches Showlink outside it — not the result plan, not the index pass, not the show-list refresh.
- `DOG_RESULT_PAUSE_STALL_SECONDS`: result-stall length that flips a non-final multi-day show to the `Jatkuu` display state during the evening wind-down; defaults to `7200` (2h). Display only — does not affect fetching.
- `DOG_RESULT_PAUSE_EVENING_HOUR`: earliest local hour the stall trigger may apply, so a slow midday breed ring or crawler lag can't fake `Jatkuu`; defaults to `17`.
- `DOG_RESULT_TIMEZONE`: IANA timezone used to evaluate show dates and the fetch window; defaults to `Europe/Helsinki`. The crawler/web containers run in UTC, so this is resolved explicitly via `tzdata` rather than the process clock.

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

- The list page has one search field. Empty input browses shows by month; two or more characters search shows, breeds, and judges through the indexed cache. Show/breed/judge search runs as SQL `LIKE` scans over `dog_show`/`dog_breed` (`sqlstore.search_breeds_by_name` / `search_breeds_by_judge` / `search_show_ids`), assembled and ordered in `search.py` (per show: breed match > judge match > show-text match; the final list is sorted by show date, newest first, across every match type — parsed from the show's `date`, its title, or the month label, with show id breaking ties). Queries of three or more characters additionally match cross-show entities via SQL (`app/dog_show/sqlstore.py`, behind `store.py`), interleaved into the same newest-first date order: **dogs** (`search_dogs_by_name` — one hit per distinct registered dog, aggregated by `dog_result.reg_id` with the newest-show name/`reg_id`/career counts, anchored to the newest show for date sorting; the ~3% of rows without a reg_id fall back to per-show hits via `search_dog_results_by_name`, capped at 10), **owners** (`search_breed_award_owners` — one hit per breed honor roll with `group`/`breed_id`/`breed_name`/`winner` so the client deep-links the breed result page), and **kennels** (`search_breeder_awards` — breeder-award `kasvattaja` rows, whose `name` column holds the kennel; same per-breed deep-link fields, `match: "kennel"`). Registered-dog/owner/kennel matches are bounded to 20 each. Case-insensitivity for å/ä/ö is handled by OR-ing raw/upper/lower LIKE patterns (no normalized column, so no schema change); `%`/`_` are escaped so a literal `100%` search can't wildcard.
- Active show rows display `Käynnissä` and replace the signup pill with `n/N tulosta`; a multi-day show paused for the night/evening shows `Jatkuu` instead (still with `n/N tulosta`); past and upcoming show rows show only the full signup count. Multi-day rows show a date range (`13–14`) in the calendar box.
- The show detail page is a single screen: the breed list (groupable by FCI group / judge / alphabetically) plus a whole-show filter panel. There are no `Koirat & Tulokset` content tabs; breed rows expand in place to show their dogs once the whole-show cache is loaded. An expanded breed row also renders the breed's honor roll (ROP/VSP/SERT winners with owners, incl. the breeder award) from the `/all-results` `breed_awards` map, so owner and kennel information is visible without opening the breed page.
- On live show detail pages, `Tuloksia saaneet` is on by default. Breed rows with cached progress show `n/N` judged dogs and, when the toggle is active, breeds with the freshest result progress sort first.
- If the toggle is turned off during a live show, unchecked breeds remain openable so a direct breed page can be tried even before Showlink's group-list checkmark catches up.
- Whole-show results auto-load when a show detail opens — every reachable show is permanently cached, so a complete `/all-results` cache fills the filters instantly with no load button. Before show-day 08:00 (`upcoming`/`show_morning`), nothing is fetched: the UI keeps the breed list searchable and explains that whole-show results are not checked yet, and a one-shot timer auto-loads them the moment the 08:00 window opens.
- On the show date after 08:00, whole-show data auto-loads but the UI warns that classes and results can fill in gradually as the day progresses.
- While `/all-results` is warming (live or still-crawling shows), the page shows an animated progress card and polls the API using `retry_after`.
- Grade filtering keeps `HYL`, `EVA`, and `POISSA` separate.
- Both filter panels (whole-show and single-breed) also filter by gender (`Sukupuoli`) and PU/PN best-of-sex placement, with per-option counts. Stored gender values are the raw Showlink headings `Urokset`/`Nartut`; the frontend normalizes them (`normalizeGender` in `dogResults.js`) for display and filtering.

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
