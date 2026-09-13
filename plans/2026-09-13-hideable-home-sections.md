# Hideable home-page sections

Status: shipped
Date: 2026-09-13

## Objective

An admin can hide any of the landing page's content bands — **Projects**,
**Stack**, **Terminal** — from the admin panel, without a deploy. The immediate
want is Stack and possibly Terminal; the mechanism covers all three so the next
one is a checkbox, not a code change. Hero and footer are page chrome and are
not hideable.

## Context

`home.*` copy and the projects collection are already DB-backed and editable at
**Admin → Home content** / **Projects** (`app/home_content.py`). Visibility is the
one axis still hard-coded: [index.vue](frontend/pages/index.vue#L44-L49) renders
`HomeHero / HomeWork / HomeStack / HomeTerminal` unconditionally and
[HomeHeader.vue](frontend/components/home/HomeHeader.vue#L15-L19) hard-codes the
three nav anchors. Hiding Stack today means editing a template and redeploying.

`Project.hidden` already establishes the pattern for per-item visibility; this is
the same idea one level up.

## Approach

A new **`home_section`** table, one row per band, holding `key` + `hidden`.
Visibility is language-independent — an English-only Stack section would be a bug,
not a feature — so it must not go in `home_content`, which is keyed `(key, locale)`
and whose values are per-locale JSON. A separate table keeps the two concerns from
being confused, and a brand-new table is the cheapest schema change this repo
allows: `db.create_all()` creates it and nothing needs `ALTER TABLE`
(`schema-change-kontissa`, step 2).

The section list is a **fixed allow-list in code** (`HOME_SECTIONS = ("work",
"stack", "terminal")`), mirroring `HOME_CONTENT_FIELDS`. Bands are components,
not data — an admin cannot invent a fourth one — so the API accepts only these
keys and `PUT` only flips `hidden`. Hero and footer are deliberately absent: a
page with no header block and no footer is a broken page, not a configuration.
Rows are created lazily on first write; a missing row reads as visible, so a
fresh or un-seeded DB renders exactly what it renders today.

`work` is the Projects band — the component is `HomeWork.vue` and its anchor is
`#work`, while the heading reads "Selected projects" and the nav link reads
"projects". The DB key matches the anchor; the admin panel shows **Projects**.

The public side rides the existing overlay rather than a second fetch:
`_home_content_map()` gains a synthetic `home.hiddenSections` key (a list of
hidden keys), so it flows through `/api/home-content`, through
`export_home_content.py` into the build snapshot, and into the store's
`homeContent` — meaning the statically-generated first paint is already correct
and there is no flash of a section that should be hidden. `tm()` returns
`undefined` for the key against an older snapshot, which the frontend reads as
"nothing hidden".

Two knock-on details that are easy to miss and are part of this plan:

- **Nav anchors.** `HomeHeader` filters `navLinks` by the same set, and so does
  the mobile drawer; a `#stack` link to a section that is not in the DOM is a
  dead click.
- **Hero CTAs.** `home.hero.ctaPrimary` scrolls to `#work` and `ctaSecondary` to
  `#stack`. The hero itself always renders, but each button is hidden when its
  own target is — a CTA that scrolls nowhere is worse than one fewer button.

Alternative considered and rejected: a `home.sections.hidden` key inside
`home_content`. It needs no new table, but it would be stored per-locale, which
makes "hidden in Finnish only" representable — an invalid state the DB should not
be able to hold.

## Files to touch

- `app/models.py` — new `HomeSection` model (`key` unique, `hidden` bool).
- `app/home_content.py` — `HOME_SECTIONS`, `home.hiddenSections` in
  `_home_content_map()`, `GET`/`PUT /api/admin/sections`.
- `frontend/pages/index.vue` — `v-if` per band off a `hiddenSections` set.
- `frontend/components/home/HomeHeader.vue` — filter nav links + drawer links.
- `frontend/components/home/HomeHero.vue` — hide a CTA whose target is hidden.
- `frontend/components/admin/AdminHomeContent.vue` — "Sections" panel above the
  copy groups: one toggle per band (Projects / Stack / Terminal), saving
  immediately like the field editors do.
- `frontend/stores/i18n.js` — nothing structural; `home.hiddenSections` merges in
  with the rest of the overlay.
- `scripts/seed_home_content.py`, `scripts/seed_e2e.py` — seed all three rows
  visible.
- `tests/test_home_content.py`, `frontend/tests/unit/`, `frontend/e2e/` — below.

## API / data shape

New table `home_section` (site.db):

| column | type | notes |
| --- | --- | --- |
| `id` | int PK | |
| `key` | str(32), unique, not null | one of `HOME_SECTIONS` (`work`, `stack`, `terminal`) |
| `hidden` | bool, not null, default `false` | |

New table only — `db.create_all()` creates it on the next container start, no
`ALTER TABLE`, no one-off script, nothing to do to existing rows. Follow
`schema-change-kontissa` for the seed/test/production steps.

- `GET /api/admin/sections` → `[{"key": "work", "label": "Projects", "hidden": false}, …]`
  in page order, `@admin_required`. All three allow-listed keys are returned
  whether or not they have a row.
- `PUT /api/admin/sections` `{"key": "stack", "hidden": true}` → the updated row.
  400 on an unknown key or a non-boolean `hidden`. Upserts.
- `GET /api/home-content?locale=…` gains `"home.hiddenSections": ["stack"]` —
  same value in both locales.

Production: no migration command. Deploy, confirm the table exists, toggle from
the admin panel. Rollback is toggling back, or `DELETE FROM home_section;` which
restores "everything visible" — the table is additive and nothing else reads it.

## Tests

- **pytest** (`tests/`): `GET /api/admin/sections` requires admin and lists all
  three keys with no rows present; `PUT` upserts and flips; `PUT` with an unknown
  key and with a non-boolean `hidden` → 400; `/api/home-content` carries
  `home.hiddenSections` for both locales and reflects a flip.
- **vitest** (`frontend/tests/unit/`): the page renders all bands with an empty
  hidden set; with `["stack"]`, `#stack` is absent and the `#stack` nav link and
  the secondary hero CTA are gone; an overlay with no `home.hiddenSections` key
  renders everything (old-snapshot fallback).
- **Playwright** (`frontend/e2e/`): admin toggles Stack off, reloads the home
  page, `#stack` is gone. Needs the seed updated first (skill step 4).

Write the endpoint tests before the endpoints — the contract is fixed and small.

## Security considerations

- **New input vector?** One: `PUT /api/admin/sections`, `@admin_required` and
  rate-limited like its neighbours. `key` is checked against a fixed in-code
  tuple, `hidden` is coerced to bool. Neither value is ever rendered as markup or
  interpolated into a query — `key` only ever selects a component that already
  exists in the bundle. No `href`, so none of the `_is_safe_href` surface applies.
- **Exposes internal state?** No. `home.hiddenSections` is a list of the site's
  own section names, all of which are already in the public HTML as anchor ids.
- **Weakens the network boundary?** No. No new port, origin, CORS rule, or CSP
  change. It reuses `/api/home-content`, which is already public and
  limiter-exempt.

## Out of scope

- Reordering sections. Bands have bespoke layout and background treatment; order
  is not a toggle.
- Per-locale visibility — deliberately not representable, see Approach.
- Hiding sub-parts of a band (a single stack layer, one footer column).
- Hiding the hero or the footer — page chrome, see Approach.
- Scheduled or time-boxed visibility.
- Sections on any page other than `/`.

## Open questions

- Hiding **Projects** leaves the admin's Projects editor with nothing on the
  public page to show for it. Worth a note in that panel while the band is
  hidden, or leave it silent?

## Revision — 2026-09-13 (implementation)

Three departures from the plan above, all found while building it:

- **A third source of dead anchors.** `HomeWork`'s project "reach" chips (`L1–L7`)
  link to `#stack` as a legend reference — the plan only named the header nav and
  the hero CTAs. With the stack table hidden they now render as plain `<span>`s:
  the depth is still worth stating, the jump is not.
- **The section panel is its own component**, `AdminHomeSections.vue`, mounted at
  the top of `AdminHomeContent.vue`. Visibility has no EN/FI split and saves per
  toggle, so it shares none of that editor's draft/dirty/batched-save machinery.
- **The E2E tests stub the API instead of toggling the real database.** Playwright
  runs spec files in parallel against one shared `test-e2e.db`, so a test that
  actually hid a band failed `homepage.spec.js` whenever the two overlapped. The
  admin panel's spec stubs `/api/admin/sections`; the home page's stubs
  `home.hiddenSections` into the overlay. Persistence is covered by pytest, which
  is where it belongs. The plan's component-rendering vitest cases moved to
  `useHomeSections` for the same reason the repo has no component tests today —
  there is no `@vue/test-utils`.
