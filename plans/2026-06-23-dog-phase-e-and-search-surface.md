# /dog Browser — Phase E (cross-entity profiles) + search-surface expansion

**Status:** deferred — **do not start until the historical backfill is materially further along** (see "Readiness gate" below). This file supersedes the Phase E section of the now-deleted `2026-06-21-dog-browser-followups.md` and folds in a second workstream surfaced during the 2026-06-23 review: our search copy and our actual search index both still behave as if **breed (`rotu`)** is the only thing worth finding, even though Phase C now captures dogs, owners, kennels, awards, and placements.

**Date:** 2026-06-23
**Depends on:** Phases A–D + the 2026-06-22 hardening (all shipped). The off-peak `--backfill` crawler is live and walking history oldest-first; this plan consumes the rows it produces.

---

## Why this waits

Both workstreams read data that only exists once the backfill has covered enough shows:

- **Phase E** needs a meaningful population of `dog_result.reg_id` / `competitive_placement` and `dog_breed_award` rows across many shows before a "dog profile" or "kennel profile" is anything but a single-show stub.
- **Search expansion** is pointless to ship while only the most recent ~7-day window has dogs/awards — users would search a name and get one hit, reinforcing the impression that search is breed-only.

### Readiness gate (check before starting)

Pick a concrete threshold and verify it against `dog.db` first — do not start on vibes:

- A healthy share of **result-bearing shows are `status="complete"`** in `dog_result_cache` (e.g. ≥ 60–70%), not just the live window. Use `sqlstore.complete_result_cache_show_ids(session)` for the count.
- `dog_breed_award` and non-NULL `dog_result.competitive_placement` rows exist across **many distinct `show_id`s spanning multiple months/years**, not clustered in the last week.
- `dog_result.reg_id` is populated and stable enough that the same dog's `reg_id` recurs across shows (spot-check a few well-travelled dogs). This is the Phase E cross-show anchor; if `reg_id` turns out unstable, Phase E's data model changes and this plan must be revised first.

Record the actual numbers in this file when the gate is evaluated, then proceed.

---

## Workstream 1 — Phase E: cross-entity index + dog/judge/kennel profiles

The big feature. Zero additional Showlink load — it is a **post-process of rows already in `dog.db`**.

### Data already captured (the raw material)

- `dog_result` ([models.py:62](../app/dog_show/models.py)): `reg_id` (parsed from `reg_url`, indexed — the cross-show anchor), `competitive_placement` (PU/PN best-of-sex rank), `grade`, `placement`, `awards`, dog name, `breed_judge`, `critique`.
- `dog_breed_award` ([models.py:93](../app/dog_show/models.py)): `award_type` (ROP/VSP/`SERT uros`/`ROP veteraani`/…), `name` (winning dog, or kennel for the breeder award), `owner`. Indexed by `(show_id, fci_group, breed_id)` and by `name`. Written by Phase C, **read by nothing yet**.

### Build

1. **Secondary index / query layer** keyed by `reg_id` (dog), judge name, kennel, and owner. Derived from the `dog_result` + `dog_breed_award` rows — no schema migration if we can answer the profile queries with indexed `SELECT`s; add covering indexes only if profile reads are slow on the real dataset. Keep all reads behind `store.py` / `sqlstore.py` per the package boundary in `dog_show/CLAUDE.md` (no direct `dog.db` access from routes).
2. **Profile endpoints** (extend `app/api/dog.py`): e.g. `GET /api/dog/dogs/<reg_id>`, `GET /api/dog/judges/<name>`, `GET /api/dog/kennels/<name>` — every result for that entity across all shows, with show + date + breed + grade/placement/awards. Validate/normalize inputs in the route layer (judge/kennel names go through `_clean_judge_name`-style normalization; `reg_id` must be validated, never interpolated into SQL — parameterized queries only).
3. **Profile views** (frontend `frontend/features/dog/`): "dog profile" / "judge profile" / "kennel profile" pages reachable from the reg link already on each `DogResultCard.vue`, and from judge names already rendered on list + detail. New route(s) under the existing `/dog` page's query-param scheme or dedicated sub-routes.
4. Cost estimate from the old plan still holds: **~2–4 dev-days**, dominated by the data-access layer and the UI, not the crawl.

### Security

- New input vectors: `reg_id` / judge / kennel path params. Parameterize every query (SQLAlchemy core/ORM — no string interpolation), bound result sizes, keep the existing rate limits on the new endpoints.
- No new Showlink fetching, so no change to the crawl boundary.

---

## Workstream 2 — Search surface: stop pretending only `rotu` is searchable

Two halves: **(a) actually index the new entities for search**, and **(b) fix the copy that says "rotu"** so it matches what is findable. Do (a) before (b) — promising a search we don't serve is worse than under-promising.

### (a) What is searchable today vs. what we now have

Front-page search (`search_shows_data`, [search.py:27](../app/dog_show/search.py)) matches only:

- show text (name/title/date),
- **breed name** (`dog_breed.name` / cached result breed),
- **judge** (`dog_breed.judge` and cached `dog_result.breed_judge`, with index back-fill).

It does **not** search any Phase C / backfill data: dog names, `reg_id`, owners, kennels, or `dog_breed_award` winners (ROP/VSP/SERT). The within-show "koira" filter (`DogShowTools.vue` / `useDogBrowser.js`) is a **client-side filter over already-loaded all-results**, not `search.py`, so it only works once a show's full results are loaded and never spans shows.

**Plan:** extend `search.py` (and the index/query helpers it leans on) to also match — at minimum — **dog name** and **judge across all captured shows**, and consider **kennel/owner** and **award winners**. This dovetails with Workstream 1's cross-entity index: build the index once, let both search and profiles read it. Decide ranking: breed/show matches should probably still rank above a single dog-name hit; add a `match` type per entity (`breed` / `judge` / `dog` / `kennel`) so the frontend can tag results. Surface the deferred `judge_match_count` ("N rotua") at the same time (Phase D left it parked until real judge data landed — by this gate it has).

Keep `/api/dog/search` response-shape changes deliberate and covered by tests; the frontend renders `match` types in `DogShowListView.vue:160-180`.

### (b) Copy audit — every "rotu"-only string

Inventory of user-facing search/filter copy that under-describes the search surface (Finnish UI). Broaden each to match what (a) makes findable; keep them honest if a given surface stays narrower:

- [DogShowListView.vue:108](../frontend/features/dog/components/DogShowListView.vue) — front-page placeholder `"Hae näyttelyä, rotua tai tuomaria..."` (add dog/kennel once searchable).
- [DogShowListView.vue:173,177](../frontend/features/dog/components/DogShowListView.vue) — result match tags currently only `Tuomari` / breed; add tags for new `match` types.
- [DogShowTools.vue:101](../frontend/features/dog/components/DogShowTools.vue) — within-show search label `'Rotu, tuomari tai koira'` / `'Rotu tai tuomari'`.
- [DogShowTools.vue:129](../frontend/features/dog/components/DogShowTools.vue) — `Rotulista` filter label (fine as-is; note for completeness).
- [useDogBrowser.js:263-264](../frontend/features/dog/useDogBrowser.js) — `'Hae rotua, tuomaria tai koiraa...'` / `'Hae rotua tai tuomaria...'`.
- [useDogBrowser.js:699-700](../frontend/features/dog/useDogBrowser.js) — empty-state copy `'Ei rotuja...'` (reframe if results can be non-breed entities).

Run `/i18n-check` after copy edits if any of these move into the `frontend/locales` files. Update unit tests in `dogResults.test.js` and the search E2E in `dog.spec.js` for new tags/placeholders.

### Security

- Search input is already untrusted and handled; new fields are still substring matches over our own stored rows via parameterized queries. No new external fetch. Bound result counts so a broad query can't return the whole DB.

---

## Files likely to touch

- `app/dog_show/search.py` — match new entities; ranking + `match` types.
- `app/dog_show/sqlstore.py` / `store.py` / `indexing.py` — cross-entity index/query helpers (shared by search + profiles).
- `app/dog_show/models.py` — covering indexes only if profile/search reads are slow (any schema change = explicit migration per `CLAUDE.md`).
- `app/api/dog.py` — profile endpoints + validation; `/api/dog/search` shape.
- `frontend/features/dog/` — profile views; copy edits (files listed above); `DogResultCard.vue` / judge-name links into profiles.
- Tests: `tests/test_dog.py`, `frontend/.../dogResults.test.js`, `frontend/e2e/dog.spec.js`.
- Docs: `docs/dog-show-browser.md`, `app/CLAUDE.md`, `app/dog_show/CLAUDE.md`, `frontend/features/dog/CLAUDE.md`.

## Out of scope

- Any change to the crawler/backfill cadence or TTL/freshness semantics.
- Re-fetching Showlink for profile data — Phase E is strictly a read-side projection of `dog.db`.

## Open questions (resolve at start, against real data)

- Is `reg_id` stable enough across shows to anchor a dog profile? (Gate item — blocks Phase E's model if not.)
- Search ranking when an entity matches multiple ways (a name that is both a kennel and an owner) — single best `match` or multiple tags?
- Do kennel/owner get first-class profiles, or just searchability, in this pass? (Kennel/owner data quality from the award table is the deciding factor.)
