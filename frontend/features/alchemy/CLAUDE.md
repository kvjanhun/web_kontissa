# Alchemy Feature - Agent Guide

This directory owns the `/alchemy` frontend feature: a Kingdom Come: Deliverance II
recipe reference and an ingredient matcher. Read this first when changing alchemy
UI, route state, the matching rules, or the recipe dataset.

## Fast Map

| Need | Start here |
|------|------------|
| Route metadata, standalone layout, head tags | `../../pages/alchemy.vue` |
| View composition and prop/event wiring | `AlchemyBrowser.vue` |
| Route query sync, localStorage, view transitions | `useAlchemyBrowser.js` |
| Search, matching, and dataset validation | `alchemyRecipes.js` |
| Alchemy-only styling | `alchemy.css` |
| The dataset and its provenance | `data/recipes.json`, `data/ingredients.json`, `README.md` |
| Unit tests for pure helpers | `../../tests/unit/alchemyRecipes.test.js` |
| E2E coverage | `../../e2e/alchemy.spec.js` |

## Architecture

- `pages/alchemy.vue` stays thin: page metadata plus `<AlchemyBrowser />`.
- `AlchemyBrowser.vue` stays declarative — it calls `useAlchemyBrowser()`, passes state down, and turns child events into composable actions.
- `useAlchemyBrowser.js` is the stateful boundary: route query reads/writes, `localStorage`, and view transitions.
- `alchemyRecipes.js` is the pure boundary. It imports nothing from Vue and is where search, matching, and validation live. Cover changes here with Vitest.
- Components under `components/` take props and emit events; they do not read the router.
- `alchemy.css` is local to this feature and imported by `AlchemyBrowser.vue`. Do not spread `.al-*` selectors into global CSS.

## The Page Is Unlisted

Nothing links to `/alchemy`. It is absent from `useNavLinks.js`, from the homepage
footer's DB-backed `siteLinks`, and from `generate_sitemap()` in `app/routes.py`,
and it sets `robots: noindex`. It is still in `SPA_ROUTE_PREFIXES` (`app/utils.py`)
because `/api/pageview` rejects any path outside that allow-list with a 400.

There is deliberately **no** `Disallow: /alchemy` in `robots.txt`: a Disallow line
publishes the path to anyone reading the file and stops crawlers fetching the page
at all, so they would never see the `noindex` that does the actual work.

Linking the page from anywhere is a decision for the user, not a detail of a change.

## Data Contract

The dataset is bundled JSON, imported at build time — there is no API and nothing
to fetch on mount. Keep it that way unless the dataset outgrows the route chunk.

- `base` is one of `water`, `wine`, `oil`, `spiritus`.
- `ingredients` is `{ id, qty }`, where `id` must exist in `ingredients.json`.
- A step's `text` is the display truth, written as prose. `uses` / `turns` /
  `grind` / `bellows` / `finish` are rendering and validation hints, **not** a step
  DSL — Decoction of St. Roch (raise the cauldron, add chamomile, lower it without
  flipping the timer, pull the bellows twice) is why.
- Each step's `uses` ids must be **named exactly once** in that step's prose. The
  inline highlighter matches on the ingredient's name, and a dataset-wide test
  asserts the highlight count equals the `uses` count for every step — so a step
  that says "add them" without naming, or names one twice, fails the suite.
- `dlc` is the DLC name for non-base-game recipes, and renders a badge. Absent
  means base game.
- `verified` means two independent sources agree on **base, ingredients and
  steps**. It says nothing about `effect` text, which is separately sourced and
  absent for most recipes. It is false until confirmed, and a false value renders
  a visible "unverified" marker. Never flip it to true to quiet the marker;
  confirm the recipe against a second source instead, and update `README.md`.
- Prefer no `effect` over a guessed one. Most recipes have none on purpose.

`validateDataset()` enforces referential integrity — unknown ingredient ids, a
step naming something the recipe does not list, a listed ingredient no step uses,
bad quantities, a missing finishing step. `alchemyRecipes.test.js` asserts it
returns nothing for the shipped data, so a transcription typo fails the suite.

## Behavior To Preserve

- Matching is **presence only**: holding nettle at all satisfies a recipe calling
  for two. Quantities are displayed but never gate a match — counting inventory is
  the tedium the page exists to remove.
- Base liquids are assumed available and are not pickable. The base chip row is a
  **toggle group**: every base starts included, clicking one drops it out (it does
  not narrow to that base alone), and "All" is the reset that restores the full set.
  `searchRecipes` takes `{ bases }` — the set to include, never a single value.
- An empty selection returns two empty lists, not every recipe.
- `oneShort` is recipes missing exactly one distinct ingredient, and carries which.
- Ingredient search normalises punctuation, so `st johns wort` finds
  `St. John's Wort`. Apostrophes are deleted rather than turned into spaces —
  spacing them splits the word and makes that exact search miss.
- The page renders the plain recipe list until `onMounted` sets `ready`. The route
  is pre-rendered without a query string, so painting a `?recipe=` or `?have=` view
  on the server would disagree with the client and break hydration.
- Selection changes use `router.replace` (ticking a dozen herbs must not bury the
  previous page under a dozen history entries); view changes use `push`.
- English only, and one locked dark theme with no `.dark` variant.

## Colour Axes

Three independent axes, each a class that sets one CSS custom property. Markup
names the meaning; `alchemy.css` owns the palette. Helpers live in
`alchemyRecipes.js` (`categoryClass`, `baseClass`, `itemCategoryClass`).

| Axis | Property | Class | Applies to |
|------|----------|-------|------------|
| Solution medium | `--al-media` | `al-base-<base>` | base badges, base filter chips |
| Ingredient category | `--al-cat` | `al-cat-<category>` | ingredient name **and** its type label, everywhere either appears |
| Brewing operation | `--al-op` | `al-op-<operation>` | step tags — grind, bellows, turns, pour, distil, decant |

Rules for changing this:

- **Never let hues collide within one axis** — that is the axis's whole job.
  Collisions *across* axes are accepted: 14 values do not fit in one wheel, and
  the three read in different roles. The one exception is grind vs. the spiritus
  base, deliberately pulled apart because spiritus recipes are the grind-heavy
  ones and the two land on the same screen.
- An ingredient's colour comes from its category and must be the same in the
  picker, the cards, and the recipe detail. Set the class on the row and let the
  name and the label both read `var(--al-cat)`.
- Colour is always redundant with a text label (`HERB`, `WATER`, `GRIND`), never
  the sole carrier of meaning.
- Every colour must clear roughly 7:1 on the `--al-surface` ground. Minerals are
  the dullest of the categories on purpose — they are the inert ingredients.
- `--al-media` is read as `var(--al-media, var(--al-accent))` on shared elements
  like `.al-chip`, so a base class supplies the hue regardless of source order
  and the "All" chip falls back to the page accent.

## Styling Traps

- The ground colour is painted at full bleed by `.alchemy-page`, not inherited
  from `body`. Because the page ignores the site's `.dark` class, a centred
  `max-width` wrapper would sit as a dark slab on a white gutter in light mode.
- `color-scheme: dark` on that wrapper keeps native checkboxes and inputs dark.
- `.al-card` is a flex column: a `<button>` centres its content box vertically, so
  a card whose title row wraps sits lower than its neighbours under `display: block`.
- No new font files. Body and headings are DM Sans, already loaded site-wide;
  `app/routes.py` serves `fonts/` as `immutable` with un-hashed filenames, so
  adding a face means picking a new filename forever.

## Useful Commands

From the repo root:

```bash
cd frontend && npm run test -- alchemy
cd frontend && CI=1 npm run test:e2e -- alchemy.spec.js
cd frontend && npm run build
.venv/bin/python -m pytest tests/test_core_routes.py
```
