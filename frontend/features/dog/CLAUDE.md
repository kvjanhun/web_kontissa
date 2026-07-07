# Dog Feature - Agent Guide

This directory owns the `/dog` frontend feature. Read this first when changing dog-show UI, route state, client-side filtering, or whole-show result loading.

For backend crawling, cache formats, Showlink parsing, and operational tuning, read `../../../docs/dog-show-browser.md`.

## Fast Map

| Need | Start here |
|------|------------|
| Route metadata, standalone layout, head tags | `../../pages/dog/index.vue` |
| View composition and prop/event wiring | `DogBrowser.vue` |
| Route query sync, API calls, polling, state transitions | `useDogBrowser.js` |
| Pure filtering, grouping, formatting, and URL helpers | `dogResults.js` |
| Dog-only styling | `dog.css` |
| List/search screen | `components/DogShowListView.vue` |
| Show-detail screen, breed-grouping tabs, and whole-show filters | `components/DogShowDetailView.vue` and `components/DogShowTools.vue` |
| Single-breed result screen | `components/DogBreedResultsView.vue` |
| Result card rendering | `components/DogResultCard.vue` |
| Shared loading/error/empty rows | `components/DogStateBlock.vue` |
| Unit tests for pure helpers | `../../tests/unit/dogResults.test.js` |
| E2E coverage | `../../e2e/dog.spec.js` |

## Architecture

- `pages/dog/index.vue` should stay thin: page metadata plus `<DogBrowser />`.
- `DogBrowser.vue` should stay mostly declarative. It imports `useDogBrowser()`, passes state down, and translates child events into composable actions.
- `useDogBrowser.js` is the stateful boundary. Put `$fetch`, route query reads/writes, timers, polling, and current-view transitions here.
- `dogResults.js` is the pure boundary. Put deterministic filtering, grouping, formatting, and query helpers here, then cover risky changes with Vitest.
- Components under `components/` should avoid direct API calls and router access. Prefer props and emits so the data flow remains visible from `DogBrowser.vue`.
- `dog.css` is intentionally local to this feature and imported by `DogBrowser.vue`; do not spread dog selectors into global shared CSS.

## Route And API Contracts

The public route is `/dog`.

Query state:

- No query opens the show list.
- `?show=<show_id>` opens one show.
- `?show=<show_id>&group=<group>&breed=<breed>` opens one breed result page.
- `?dog=<reg_id>` opens a cross-show dog profile (`DogProfileView.vue`, `currentView === 'dog'`). Reg ids contain a slash (`FI44694/25`), so the value stays a query param and is `encodeURIComponent`-ed when fetching.

Client API calls:

- `GET /api/dog/shows`: show list, index status, and compact row stats.
- `GET /api/dog/search?q=<query>`: indexed show, breed, and judge search (two-char minimum); three-plus-char queries also match dogs, owners, and breeder-award kennels across all captured shows. The backend orders results by show date, newest first, across every match type — render them in response order. Results carry a `match` type (`show`/`breed`/`judge`/`dog`/`owner`/`kennel`) that `DogShowListView.vue` renders as a tag. A `dog` hit with a `reg_id` opens the dog profile; a reg-less `dog` hit opens its show with the whole-show search pre-filled to the dog's name; `owner`/`kennel` hits carry `group`/`breed_id` and open that breed's result page, where the honor roll shows the match (`onSelectSearchResult`).
- `GET /api/dog/shows/<show_id>`: show detail and breed list.
- `GET /api/dog/shows/<show_id>/results?group=<group>&breed=<breed>`: one breed result page.
- `GET /api/dog/shows/<show_id>/all-results`: whole-show persisted cache. A warming response keeps the progress card visible and should be polled using `retry_after`.
- `GET /api/dog/dogs?reg=<reg_id>`: the dog profile — every captured result for one registration number, entries pre-sorted newest show first. One request per profile; no polling.

The frontend must not fan out across all breed result pages. Any full-show filtering must go through `/all-results`.

## Behavior To Preserve

- Empty list search browses by month; two or more characters uses backend indexed search (show/breed/judge), and three or more also returns cross-show matches tagged `Koira` / `Omistaja` / `Kasvattaja`. Registered-dog hits are one row per dog (career counts, opens the profile); reg-less dog rows keep the per-show open-and-prefill behavior.
- The dog profile (`?dog=`) groups entries by show, newest first; the show header opens the show and the breed line above each card opens that breed's result page. Loading/error/empty states go through `DogStateBlock`; the top bar shows the same `Näyttelyt` back link as the detail view.
- While indexing is incomplete, the list polls `/api/dog/shows` for index stats.
- Live rows display `Käynnissä` and result progress as `n/N tulosta` when available. A
  multi-day show in its nightly/evening lull (backend `stats.is_paused`) instead shows
  `Jatkuu` while keeping the `n/N tulosta` count; the final day's wind-down stays `Käynnissä`.
- The list calendar box shows a multi-day range (`13–14`) via `DogShowDateBadge.vue` /
  `showDateBadgeParts`, not just the first day.
- Opening a show resets whole-show result state and breed-result state.
- Whole-show results **auto-load** when a show detail opens — every reachable show is now permanently cached, so complete caches return instantly and there is no load button. The composable watches `[currentView, showDetail.id, allDogsAvailability.canLoad]` and calls `maybeAutoLoadAllResults()` (idempotent/gated). Live or still-warming shows stream in via the progress card + `retry_after` polling that `loadAllShowResults` drives; partial cache progress stays visible and resilient across deploys. The retry card (`retry-all-dogs` → `loadAllShowResults`) still handles a failed load.
- Before the show-day window opens (`availability.phase` `upcoming`/`show_morning`, `canLoad:false`) nothing is fetched — the info card explains, and `/all-results` is not called (the future-show E2E asserts this). For `show_morning`, a one-shot timer armed off `availability.availableFrom` bumps an availability clock tick at 06:00 so results auto-load the moment the window opens even if the page is untouched.
- Show-wide filters apply only after all-dogs data has loaded.
- An expanded breed row shows the breed's honor roll above its result cards (ROP/VSP/SERT winners with owners, incl. the breeder award — a kennel that appears on no dog card). The data is the `/all-results` `breed_awards` map (`"group:breed_id"` → award list), attached as `group.awards` by `createShowBreedGroups` and sorted with `sortBreedAwards`.
- The breed list (`Rotuluettelo`) can be grouped three ways via the mode tabs: by FCI group (default), by judge, or alphabetically (flat). Grouping is a pure partition in `dogResults.js` (`groupShowBreedGroups`) that preserves breed order within each section; the tabs only show when the show has two or more breeds. `showGroupMode` is a sticky view preference, not route state.
- Breed result filters and whole-show filters keep `HYL`, `EVA`, and `POISSA` separate.
- Both filter panels also offer **gender** (`Sukupuoli`: Urokset/Nartut) and **PU/PN best-of-sex placement** selects with counts. Stored gender is the raw Showlink heading (`Urokset`/`Nartut`, plural — note the gradation: uros → urokset, narttu → nartut); all gender display and filtering must go through `normalizeGender`/`genderSymbol` in `dogResults.js`, never string-compare `'uros'` directly (that bug made the card ♂/♀ chip invisible on real data). `dogMatchesShowFilters` and `filterDogResults` stay in lockstep for every filter.
- The `BIS` award view splits `BIS JUN` and `BIS VET` into per-show-day groups (`BIS JUN (1. päivä)` …) on multi-day shows, since each day runs its own junior/veteran Best in Show. The day count is inferred from repeated placement ranks; dogs are assigned to days by ordering *each placement's* winners by catalog number (lowest = day 1), comparing numbers only within a placement — never across placements, since one day's finalists span a wide range and the largest gap in the merged list often sits inside a day. Single-day shows are left ungrouped; main `BIS` and `RYP` are intentionally not split. Pure logic lives in `dogResults.js` (`splitPerDayFinals`/`clusterFinalsEntriesByDay`), covered in `dogResults.test.js`.
- The **show-winners summary** (`DogShowWinners.vue`, `buildShowWinnersGroups` in `dogResults.js`) renders at the top of the default detail view once the whole-show cache loads: the show finals (BIS / BIS JUN / BIS VET / BIS PEN, reusing the per-day BIS split above) as collapsible groups (`DogFinalsGroup.vue`) that **start collapsed** — a single row per group with the winner inline after the award title (`BIS  1. rotu Winner Dog #123`), expanding into full result cards for every placement. The FCI group placements are not in the summary: `rypWinnersByFciGroup` keys the RYP-1..4 placements by group, and the breed list's FCI grouping mode shows each group's RYP top-4 as full result cards (`.dog-ryp-winners`, no title of their own) at the top of that group's section — not collapsible itself; the section is the collapsible unit. Both are pure derivations of the already-loaded results (no backend change), gated on `allDogsLoaded && !showWideFiltersActive`, and absent for specialty shows that crown no show-wide finals.
- Result cards show a **best-of-sex rank chip** (`competitive_placement`: `PU1`–`PN4`) next to the grade/honour award chips, via `DogResultCard.vue` (class `dog-comp-placement`). The field is already in every backend result response (breed page and whole-show), so this is display-only.
- Back/forward navigation is source-of-truth route navigation, not private component state.
- Programmatic navigation scrolls `/dog` back to the top after link-style transitions.

## Change Checklist

- If you alter API shape or cache behavior, update `../../../docs/dog-show-browser.md` and backend tests in `../../../tests/test_dog.py`.
- If you alter pure result logic, update `../../tests/unit/dogResults.test.js`.
- If you alter user-visible navigation, loading, search, or filters, update `../../e2e/dog.spec.js` when behavior changes.
- Keep Showlink politeness in mind: no client-side request fan-out, no shorter polling loop than the backend asks for, and no new endpoint loops without rate-limit awareness.
- Keep text in Finnish unless the existing UI around it is technical/source-link copy.

## Useful Commands

From the repo root:

```bash
python3 -m pytest tests/test_dog.py
cd frontend && npm run test -- dogResults
cd frontend && CI=1 npm run test:e2e -- dog.spec.js
cd frontend && npm run build
```
