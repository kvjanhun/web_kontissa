# /dog Browser — Review Findings & Follow-ups

**Date:** 2026-06-21 (revised 2026-06-22 after Phases C + D shipped)
**Context:** Functionality + UX review of the `/dog` Showlink browser (frontend `frontend/features/dog/`, backend `app/dog_show/` + `app/api/dog.py`). The scraping is polite and sound. This file records what shipped, the agreed direction, and the design detail for the next phases.

**Status at a glance:** Phases A–D shipped. Phase C's off-peak backfill is now running nightly on the NUC and historical data is filling in oldest-first; Phase D's judge views light up across shows as that data lands. Phase E (cross-entity dog/judge/kennel profiles) is the remaining roadmap item and depends on the backfill having indexable history.

---

## Investigation: where does judge data actually live? (2026-06-21)

We checked the assumption that the "basic scrape" already has judges for every show. **It does not.** Findings from the cached data and a few live Showlink probes:

- The index (`dog_show_index.json`) holds breed lists for **662 shows**, but only **16 shows** have any breed judge stored — and those 16 line up almost exactly with the shows we have fetched results for (13 have a full result cache; 3 have exactly one judged breed from a single breed-page click).
- A fully-indexed past show like `12805` (228 breeds, `has_results: true` on all) stores only `name / count / group / breed_id / has_results / source_url` per breed. **No judge field.**
- On Showlink, the breed-list / group pages (`?Id=X` and `?Id=X&R=n`) list breed names + entry counts only. The single "Tuomari …" on a group page is the **group-final (RYP) judge**, not the per-breed judges.
- The per-breed judge appears **only on each individual breed result page** (`Tuomari X` in the result header → `_parse_breed_results`).

**Consequence:** there is no cheap judges-listing shortcut. Getting judges for all shows means fetching the same breed-result pages the whole-show result crawl already fetches — so we may as well **keep all the data** (judges, grades, awards, dogs, critiques) rather than fetch the full page and discard most of it.

**Cost model (confirmed):** ~1 request per breed-with-results → **~10k–20k requests per year of history**, dominated by a handful of 200+ breed all-breed shows. Off-peak at a polite rate this is a few nights to seed full history, then incremental for new shows. Crawling is the cheap part; storage + data model are the real work.

---

## Agreed direction (2026-06-21)

> Take all the data, use all the data. Full results, not judge-only. **SQL migration must land before the all-shows backfill** (100k+ result rows do not belong in JSON). The dog store becomes a **separate, permanent `dog.db` database — not a cache**: a dedicated SQLite file for `/dog` only, no Litestream replication (Konsta backs it up manually), and historical data is kept forever. Drop the original "judges on list cards" idea; instead make the **show detail page groupable**.

Phases below are ordered by dependency.

### Phase A — Bound `queue_background_indexing` in web workers  ✅ DONE (this session)

The only under-bounded scraping path. `crawler.py:queue_background_indexing()` iterated **all** missing/empty shows per call (each a detail fetch that can fan out to group pages), with a per-process dedup set, so one cold-index `/api/dog/shows` hit could spawn hundreds of Showlink requests per worker.

**Shipped:** cap the batch per invocation via `BACKGROUND_INDEX_MAX_PER_CALL` (default 5, env `DOG_BACKGROUND_INDEX_MAX_PER_CALL`) in `config.py`; `crawler.py` truncates `to_index` and logs `dog_background_indexing_capped`. The remaining shows are picked up on the next `/api/dog/shows` hit or by the `dog-crawler` service's 15-min `crawl_index_once`. 64/64 `tests/test_dog.py` pass.

### Phase B — SQL migration (prerequisite for the backfill)  ✅ DONE (this session)

Moved dog persistence from JSON files to SQLite so the full-data backfill has somewhere to scale. Shipped in two commits on `dog-sql-migration`: B.1 (SQL foundation + validated one-off migration) and B.2 (cutover of `store.py`). 65 dog tests + 288 backend tests green; read parity + performance verified against the real 662-show / 4.9k-result dataset.

**Decided (2026-06-21) and as built:**
- **Separate `app/data/dog.db`, used only by `/dog`.** Built on a **standalone SQLAlchemy engine + thread-local scoped session** (`app/dog_show/db.py`), **not** a Flask-SQLAlchemy bind — dog writes happen in background warmup threads and the separate `scripts/dog_crawl.py` process, neither of which has a Flask app context, so `db.session` would not work there. Keeps the heavy `/dog` crawl data out of the low-write `site.db`. URL is `DOG_DATABASE_URI` (default `dog.db` inside `DOG_INDEX_DIR`).
- **Not replicated to Litestream.** Once fetched, the data is effectively static; Konsta handles backups of `dog.db` manually. So no change to `server/observability/litestream.yml`. Otherwise `dog.db` is a normal SQLite database in the `./app/data` bind mount.
- **No referential/identity constraints** (`PRAGMA foreign_keys` off, no breed `UniqueConstraint`): the legacy JSON store enforced none and several paths rely on that permissiveness. Per-breed judges are stored on both `dog_breed.judge` and `dog_result.breed_judge` (the result cache is the source of judges, so a judge survives a round-trip even before the index breed has it).
- **`_show_index` stays the shared in-memory mirror**, reloaded from `dog.db` only when a `dog_meta.index_generation` counter advances; `_save_index()` flushes only dirty shows. Generation-gated no-op load ≈ 0.3 ms; full reload ≈ 0.25 s (gated, rare).

**This store is a persistent database, not a cache (key design constraint).**
- Old shows' data is **permanent** — never evict or delete settled/historical rows. Retention/TTL logic governs only *when to re-fetch* live or recent shows; it must never *delete* captured data.
- Audit the migration so none of the current JSON-cache retention/eviction semantics carry over as row deletion. When in doubt, keep the data.
- Treat `dog.db` as the system of record for historical results, not a disposable cache layer.

**Phase B starts by migrating what we already have and proving parity.**
1. Migrate all currently-JSON'd state into `dog.db`: `dog_show_index.json` (662 shows), the 15 `dog_result_cache/*.json` docs, and `dog_result_jobs.json`. Idempotent one-off script, reviewed, run once against prod (per the `CLAUDE.md` schema-change policy: explicit plan + tests + reviewed manual prod procedure).
2. **Verify every current `/dog` feature still works and performs** on the SQL backing before adding anything new — show list, show detail (all enrichment paths), breed results, whole-show all-results, search, live progress, crawler passes. Response shapes must stay byte-identical so the frontend + E2E don't move. Check read latency on the 662-show / full-results dataset.

**Schema sketch (dog.db):**
- `show` — id, name, title, date, month, source_url, breed/entry counts, updated_at, state flags.
- `breed` — show_id, group, breed_id, name, entry_count, has_results, judge, result_updated_at. (Carries the per-breed judge; this is what the detail page + search read.)
- `result` — show_id, group, breed_id, catalog number, dog name, reg_url, **reg_id** (parsed from reg_url — the cross-show anchor), grade, placement, awards, gender, class_name, critique.
- `result_cache_meta` / `result_job` — replace `dog_result_cache/<id>.json` headers and `dog_result_jobs.json` (status, progress, probe cursor, backoff, heartbeat). Job rows are transient; result rows are permanent.

**Work:**
1. Define models (new module, e.g. `app/dog_show/models.py`, bind key `dog`) + create tables for fresh/test DBs (no live migrations at import/startup — per `CLAUDE.md`).
2. Rewrite `store.py` read/write helpers to hit SQL instead of JSON, **preserving the in-memory cache objects and `_show_index`-shaped dict the rest of the package and `app/api/dog.py` re-exports depend on** (see `dog_show/CLAUDE.md` compatibility notes). This is the bulk of the work — `indexing.py`, `result_cache.py`, `search.py`, `crawler.py` all read those structures.
3. The migration script + parity verification from "Phase B starts by…" above.
4. Tests: port `tests/test_dog.py` fixtures to SQL (it currently builds `_show_index` dicts directly — these become DB rows). Keep response shapes identical.
5. Update `docs/dog-show-browser.md` "Persistent Files" + `app/CLAUDE.md` + `dog_show/CLAUDE.md` to describe SQL storage and the permanent-database (non-cache) retention model.

**Risk:** this is the large piece. `tests/test_dog.py` leans heavily on the JSON `_show_index` shape; budget time for the test port. Preserve all `/api/dog/*` response shapes.

### Phase C — All-shows full-data off-peak backfill  ✅ DONE (shipped 2026-06-22)

**Shipped in `3730b06b` (feature) + `3229709d` (compose wiring).** Captures everything a result page offers in one pass, plus a polite off-peak crawler mode that backfills historical shows oldest-first before they age off Showlink's rolling window.

- **Full-data capture:** parsers now extract per-dog competitive placement (PU/PN, `cells[4]`, previously dropped) and split the breed honor-roll into `{type, text, name, owner}`. Schema: new `DogResult.competitive_placement` column + new `DogBreedAward` table (ROP/VSP/SERT/veteran/junior/breeder winners with owner/kennel). `result_cache.py` threads the new fields through; `sqlstore.py` reads/writes them (omitting `competitive_placement` when empty so the pre-Phase-C migrated docs round-trip clean).
- **Backfill mode** (`result_cache.crawl_backfill_once`, wired into `scripts/dog_crawl.py --backfill`, enabled permanently in the `dog-crawler` compose service): Finnish 00:00–06:00 window (tz-correct via `utils._local_dt`; container is UTC), oldest-first selection of not-yet-captured result-bearing shows, single worker + `DOG_BACKFILL_DELAY` (2 s spacing) so it is never bursty, and it yields while any user/live result job is queued or running. Captured shows are permanent and never re-crawled; goes idle when the window is fully backfilled. New `DOG_BACKFILL_*` config knobs.
- **Migration:** `scripts/migrate_dog_phase_c.py` — idempotent additive `ALTER` for the new column + `create_all` for the new table; preserves existing rows.
- **Tests:** 8 new (parser values, owner split, window/wrap-around gating, jobs-yield, oldest-first + skip-captured + skip-resultless selection, end-to-end persistence). 73 dog + 296 backend green. Validated on real data (PU1–PU4 + honor-roll owner splits, doc round-trips, an aged-out June-2024 show handled as complete/0-results).
- **Feasibility unknowns:** confirmed enough to ship — Showlink exposes a crawlable rolling history window and `reg_id` from `reg_url` is the cross-show anchor for Phase E. Depth of history is now being measured empirically as the nightly backfill walks oldest-first.

*Original design intent (for reference):* A crawler mode that backfills full results for shows beyond the live/7-day window.

- **Quiet-hours gate:** only run between **00:00–06:00 Europe/Helsinki** (`DOG_RESULT_TIMEZONE`). New knobs analogous to the existing `DOG_RESULT_SHOW_MORNING_HOUR` window.
- **Strictly polite, never bursty — this is a hard rule, even at 3am.** Steady, paced request flow with a low ceiling; no concurrency spikes, no firing a whole show's breeds back-to-back. Pace it so we make measured progress over many nights rather than hammering Showlink — but not so slow it would take a decade. Tune the per-request delay / nightly cap to a deliberate middle ground (e.g. a fixed inter-request spacing and a nightly request budget), and prefer raising the delay over raising concurrency if Showlink ever slows.
- **Order: current → old (newest first).** Most-relevant history fills in first; deep history trickles in over subsequent nights.
- Only runs when no live show and no user-queued result job is pending. Reuses the job queue + `crawl_result_cache_for_show` (now writing SQL); resumable per breed (already supported); persists progress so deploys/restarts don't lose work.
- Once a settled/old show is fully captured it is **done permanently** — not re-crawled on later nights (it's a persistent record now, not a refreshing cache). The backfill only ever advances into not-yet-captured history.
- **Verify two feasibility unknowns FIRST (cheap probes):**
  - Does Showlink's show list expose **multi-year history** in a crawlable way, or only a rolling window? *Biggest unknown — determines how far back we can go.*
  - How **stable is the dog id** in `reg_url` (`jalostus.kennelliitto.fi`)? It's the cross-show anchor for Phase E.
- **Storage budget:** ~1–5 GB for a few years — fine on the NUC.

### Phase D — Show detail grouping UI + front-page judge search  ✅ grouping UI DONE (shipped 2026-06-22, `836eda44`); judge-search lighting up as backfill data lands

Frontend-first; degrades gracefully as data fills (FCI grouping works today from group numbers; judge views light up as judges land via the now-live Phase C backfill).

**Shipped (grouping UI), `836eda44`:** breed-list mode tabs (`Ryhmä` / `Tuomari` / `Aakkoset`, default FCI) in `DogShowDetailView.vue`. Pure partition `groupShowBreedGroups()` + `fciGroupLabel()` + `FCI_GROUP_NAMES` in `dogResults.js` (preserves breed order within a section; orders FCI sections numerically with unknown last, judge sections alphabetically with "Tuomari ei tiedossa" last). Tabs only render at ≥2 breeds; below that the list falls back to flat. **Collapsible accordion sections** — per-section disclosure header (WAI-ARIA `<h2>`-wraps-`<button>` so heading + button roles coexist) starting expanded, plus a `Sulje kaikki` / `Avaa kaikki` toggle; collapsed state (`collapsedBreedSections`) resets per show. `showGroupMode` is a sticky in-memory preference in `useDogBrowser.js`, not route state. Unit tests in `dogResults.test.js` (36 dogResults / 151 vitest) + grouping E2E in `dog.spec.js` (6 dog E2E).

**Judge search (verified, no code change):** `search.py` already matches judges from both index breeds and cached result breeds and back-fills index judges; `DogShowListView.vue` renders judge matches with a "Tuomari" tag + names. This lights up across all shows as the now-running Phase C backfill populates per-breed judges. Deferred: surface `judge_match_count` ("N rotua") and revisit ranking once enough real judge data has landed.

- **Show detail page grouping** (`frontend/features/dog/components/DogShowDetailView.vue` + helpers): three modes, **default = FCI group**.
  - **FCI group (default):** group breeds under FCI ryhmä 1–10 with proper Finnish group names (add the 10-name map).
  - **By judge:** group breeds under each judge.
  - **Alphabetical:** current ordering, **with the judge shown in each breed row**.
- **Front-page judge search** across all shows comes mostly for free: `search.py` already matches index/breed judges; once every show has judges in SQL, judge queries find all shows. Verify after Phase C and adjust ranking/labels.
- **Dropped:** judges on the front-page list cards (original request #2). An all-breed show has 15–20+ judges; grouping on the detail page is the chosen home for this data instead.

### Phase E — Deep cross-entity index + dog/judge/kennel profiles  (the big feature; later)

- Secondary index keyed by **dog reg_id**, **judge**, **kennel** (zero extra Showlink load — post-process the SQL `result` rows).
- "Dog profile" / "judge profile" views: every result across shows, reachable from the reg link already on each result card.
- ~2–4 dev-days; data model + UI are the real cost.

---

## Minor scraping notes (acceptable as-is)

- No `requests.Session` keep-alive (efficiency, not politeness) — could add a shared session in `showlink.py` (worth doing alongside Phase C's larger crawl volume).
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
- Phase A closed the last under-bounded path (`queue_background_indexing`).
