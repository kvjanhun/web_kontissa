# Dog Frontend Module Refactor

Status: approved
Date: 2026-06-16

## Objective
Make `/dog` cleaner to maintain as its own frontend project inside erez.ac without changing its public route, API behavior, or visible browser experience.

## Context
The dog show browser has grown into a substantial standalone workflow under one Nuxt page. It now has dog-specific route state, whole-show cache polling, filters, result rendering, and a scoped design system that are not shared with the rest of the portfolio site.

## Approach
Refactor the frontend into a self-contained `frontend/features/dog/` module. Keep `frontend/pages/dog.vue` as the route entry with only layout/head metadata and a feature component. Move behavior into a `useDogBrowser.js` composable, pure formatting/filtering/grouping helpers into `dogResults.js`, reusable UI into dog-only components, and the existing `dog-*` style system into a dog feature stylesheet. Preserve query params, backend endpoint contracts, polling behavior, and the current UI as closely as possible.

## Files to touch
- `frontend/pages/dog.vue` - reduce to route metadata and `<DogBrowser />`.
- `frontend/features/dog/` - new dog feature module with components, composable, helpers, and CSS.
- `frontend/tests/unit/dogResults.test.js` - coverage for extracted pure helper contracts.
- `frontend/CLAUDE.md` and `docs/dog-show-browser.md` - document the new frontend module location.

## API / data shape
No backend API, route, database, or cache file shape changes. Existing `/api/dog/*` response contracts remain unchanged.

## Tests
- Backend: `python3 -m pytest tests/test_dog.py` as a safety check.
- Frontend unit: `cd frontend && npm run test`, including the new pure helper tests.
- E2E: `cd frontend && CI=1 npm run test:e2e -- dog.spec.js` for existing `/dog` flows.

## Security considerations
This refactor does not introduce a new input vector, expose internal state, weaken network boundaries, add a new origin, or relax CSP/CORS. User-visible inputs continue to be client-side filters or existing API query params handled by the current backend.

## Out of scope
Backend dog blueprint reorganization, separate domain/app deployment, visual redesign, and new dog browser features.

## Open questions
None; the user approved the frontend-module scope and requested no intentional browser redesign.
