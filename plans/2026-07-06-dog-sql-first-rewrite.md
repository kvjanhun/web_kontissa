# /dog SQL-first rewrite — retire the in-memory index mirror

Status: shipped
Date: 2026-07-06

## Objective

Make `dog.db` the single source of truth the backend queries directly. Remove the per-process `_show_index` in-memory mirror (generation counter, reload throttle, dirty-show tracking) and the "byte-identical to the JSON era" response-shape constraint, move search into SQL, retire the read-path index write-backs, and bound the remaining in-memory caches. No user-visible behavior change beyond faster/steadier memory use.

## Context

Follows the 2026-07-06 pre-release review and cleanup (backfill/migrations removed; web-tier crawling removed). The mirror was the deliberate bridge during the JSON→SQL migration: SQL emulating a JSON file so nothing else had to change. That constraint is retired. Costs today: every Gunicorn worker and the crawler hold the whole index (~47k breed rows, growing forever) in RAM, rebuild it wholesale on generation bumps, and `search.py` scans every show in Python per query. Konsta: rewrite to use only the SQL database; in-memory caching is probably not useful once the database is properly indexed.

## Approach

**Reads become queries.** Replace `_load_index()` + dict lookups with `sqlstore` query functions: one show + its breeds by id (show detail), show metadata for a set of ids (list-page stats enrichment), month/date lookups. The mirror, `_index_generation`, `_last_index_check_ts`, `_dirty_index_show_ids`, `_mark_index_dirty`, and `DOG_INDEX_RELOAD_MIN_INTERVAL` all go away. Writers (`crawler._update_index_show`, `_persist_show_detail_to_index`, judge/flag updates from result crawls) write rows directly through `sqlstore` in one transaction per show — no generation bump needed once nothing mirrors.

**Search becomes SQL.** Show/breed/judge search moves into `sqlstore` as indexed `LIKE` queries (same å/ä/ö raw/upper/lower OR-pattern + escaping already used by the dog-name/owner search). Plain B-tree/`COLLATE NOCASE` indexes on `dog_breed.name`, `dog_breed.judge`, `dog_show.title/name/date/month` first; FTS5 only if measured latency demands it (out of scope for this plan). Result assembly and ranking (breed > judge > show > dog > owner) stay in `search.py`; the response shape of `/api/dog/search` is preserved.

**Response shapes are pinned by tests, not by the JSON era.** `/api/dog/*` responses stay as-is (the frontend and E2E depend on them), but internal dict shapes (`_show_index` entries) stop being a contract. `sqlstore.read_index` survives only if a caller still needs a bulk read (likely none).

**Read-path write-backs retire.** `_enrich_breeds_with_cached_result_judges` → `_update_index_breed_judges` during GETs, the index save inside `_breed_results_from_all_results_cache`, and search's judge write-back all exist to heal judge gaps lazily. The crawler already folds judges/result flags in at capture time (`_record_result_breed_success`). Plan: one-time SQL sweep to fold any judges still only present in result rows into `dog_breed.judge` (an UPDATE-from-SELECT run via a short reviewed script or the crawler on first deploy), then delete the lazy write-backs. GET and search paths become read-only.

**Caches get bounded or dropped.**
- `_show_all_results_cache` (whole result sets per show, never evicted): drop or cap to a tiny LRU (~4 entries). Measure first: if serving `/all-results` straight from `sqlstore.read_result_doc` is fast enough (likely — single indexed show_id scan), drop it.
- `_breed_result_cache`, `_show_detail_cache`: drop; the DB read per request is one indexed query. `_cached_show_detail`/TTL logic goes with them.
- `_show_stats_cache` (20s TTL): **keep** — it exists to decouple live-show doc reconstruction from the 15s poll rate, which is still real.
- `_show_list_cache` (30-min Showlink list): **keep** — it's the fetch gate, not a DB cache.
- `_is_recent_show` month-label heuristic: replace remaining uses with the date-range logic (`_parse_show_date_range`/`_show_age_days`) so there is one recency system.

**Order of work** (each step green before the next): (1) add indexes + new `sqlstore` query functions with tests; (2) convert read paths (detail, stats, search) and delete the mirror; (3) judge sweep + delete write-backs; (4) drop/bound caches; (5) docs (`docs/dog-show-browser.md` storage/mirror sections, `app/dog_show/CLAUDE.md` compatibility notes).

Indexes are additive `CREATE INDEX IF NOT EXISTS` — allowed at `init_db()` table-creation time per the no-live-migrations rule only if we treat index creation as schema; otherwise ship as a reviewed one-off (`CREATE INDEX` on a 300 MB db is quick). Decide at review.

## Files to touch

- `app/dog_show/sqlstore.py` — new query functions (show detail by id, shows-by-ids metadata, search queries, judge sweep); indexes
- `app/dog_show/models.py` — `__table_args__` index definitions
- `app/dog_show/store.py` — delete mirror machinery; keep thin DB-facade functions
- `app/dog_show/indexing.py` — rewrite stats/detail helpers onto queries; drop enrichment write-backs; unify recency on dates
- `app/dog_show/search.py` — assemble results from SQL queries instead of scanning the mirror
- `app/dog_show/crawler.py`, `result_cache.py` — writers write rows directly; drop `_load_index()`/`_save_index()` calls
- `app/api/dog.py` — drop mirror-based branches/caches
- `app/dog_show/config.py` — remove `DOG_INDEX_RELOAD_MIN_INTERVAL`; add LRU size knob only if a cache survives
- `tests/test_dog.py` — `seed_index_show` writes via sqlstore; drop mirror-state assertions; add query-function tests
- `docs/dog-show-browser.md`, `app/dog_show/CLAUDE.md` — storage and boundary docs

## API / data shape

No `/api/dog/*` response changes. New SQLite indexes on `dog_breed(name)`, `dog_breed(judge)`, `dog_breed(show_id)` (if not already implied), `dog_show(month)`; plus whatever the query plans show missing (`EXPLAIN QUERY PLAN` against the production-size db in `app/data`).

## Tests

- Backend (pytest, `tests/test_dog.py`): existing endpoint/response-shape tests are the safety net and must stay green unchanged wherever possible. New unit tests for each `sqlstore` query function (TDD — contracts are clear), the judge sweep, and search parity (same fixtures, same ranked output as today). A perf smoke against a copy of the real `dog.db` (manual, not CI).
- Frontend unit / E2E: no changes expected; run the full gauntlet before push.

## Security considerations

- New input vector: no — same endpoints and validation; search input already goes through the escaped-LIKE builder, which the new queries reuse.
- Internal state exposure: no — response shapes unchanged.
- Network boundary: no — no new ports/origins; this reduces web-tier statefulness.

## Out of scope

- FTS5 search, dog/judge profile pages, any new UI.
- Litestream coverage for `dog.db`.
- Changing crawler cadence or the show-list fetch ownership (web tier keeps its 30-min list refresh for now).

## Open questions

1. Index creation path: allow `CREATE INDEX IF NOT EXISTS` in `db.init_db()` (arguably table-creation, not migration), or ship a reviewed one-off? My lean: `init_db()` — idempotent, additive, and fresh test DBs need them anyway.
2. Drop `_show_all_results_cache` outright, or keep a 4-entry LRU? My lean: drop, measure, add back only if `/all-results` p95 on the NUC says otherwise.
3. The judge sweep: one-off script vs. first-deploy crawler pass. My lean: one-off script (visible, reviewable, deletable after).

## Revision (2026-07-06, shipped)

Deviations from the plan as written:

- **No new SQL indexes.** Search is infix `%query%` LIKE, which B-tree indexes cannot serve; measured scans on the production-size db came in at 80–500 ms per search request (worst = broadest breed query) and single-digit ms for detail/all-results, so the existing indexes (`show_id` FKs, `ix_result_breed`, `ix_breed_judge`) are sufficient. Question 1 became moot. Bulk breed reads use Core column selects (`_BREED_COLUMNS`) — ORM hydration was 10x the fetch cost at ~40k rows.
- **All response caches dropped, none replaced** (question 2: drop, measured, no LRU needed). `_show_stats_cache` (20s) and `_show_list_cache` kept as planned.
- **Sweep** shipped as `scripts/dog_sweep_breed_judges.py` (question 3: one-off script). It also folds `has_results` flags and judges recorded only in zero-result `completed_breeds` meta. Local run healed 914 judges + 2 flags; needs one run on the NUC after deploy.
- **Extra fix surfaced by the rewrite:** `crawler._update_index_show` used to wipe judges on every recent-show re-index (detail pages carry no judges) and relied on the lazy read-path healing to restore them. It now merges persisted judges/result flags before the wholesale row replacement (`_merge_persisted_result_state_into_breeds`), so capture-time folding fully replaces the write-backs.
- **Recency unified** on `utils._show_is_recent` (date-range window, `DOG_SHOW_RECENT_PAST_DAYS`=45 / `DOG_SHOW_RECENT_FUTURE_DAYS`=31, month-label fallback, unknown fails open); `_is_recent_show` (month-label equality) deleted.
