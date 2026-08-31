---
name: add-page
description: Add a Nuxt page the way this repo does one — file-based route, layout choice, auth meta, en/fi title and copy keys, the Flask SPA allow-list, and the SSG constraint. Use when adding a route or page under frontend/pages/.
paths:
  - frontend/pages/**
  - frontend/layouts/**
  - frontend/middleware/**
  - app/utils.py
---

# Add Page

A page is not finished when it renders in `npm run dev`. It is finished when it
survives `nuxt generate` and Flask serves it at its real URL.

## 1. Route file

`frontend/pages/`, file-based. `<script setup>` and the Composition API only —
no Options API. Vue APIs, Nuxt composables, components, stores, and composables
are all auto-imported; do not write import lines for them.

Nested dynamic routes are `[slug]/index.vue` + `[slug]/edit.vue`. **Not**
`[slug].vue` + `[slug]/edit.vue` — Nuxt reads that as a parent/child layout and
the page will not render as you expect.

## 2. `definePageMeta`

- `layout` — `default` (header/footer, calls `checkAuth` on mount) or
  `standalone` (bare; what `/dog` and the homepage use).
- `requiresAuth` / `requiresAdmin` — read by `middleware/auth.global.js`. That
  guard skips server-side, since session cookies are not available during SSR,
  so it is a UX guard only. **The endpoint behind the page still needs its own
  decorator** — never let the page meta be the only thing standing between a
  user and admin data.
- `titleKey` — resolved by `middleware/pageview.global.js` for the route title.

## 3. Both locales

Every user-visible string is a `t('key')` with an entry in **both**
`frontend/locales/en.json` and `fi.json`. The fallback is locale → English →
raw key, so a missing Finnish key ships English copy silently rather than
failing. Do not machine-translate — add the English, list the keys that need
Finnish, and leave those to the user. Run `/i18n-check` before finishing.

## 4. Tell Flask the route exists

`SPA_ROUTE_PREFIXES` in `app/utils.py` is the allow-list behind
`utils.is_known_route()`. A path outside it is still served the `200.html` body —
so the client router paints the page and it looks right — but with a **404
status**, which is what stops crawlers indexing junk URLs as real pages. Add the
new route there, and keep it in sync with any redirect `routeRules` in
`nuxt.config.ts`.

Skipping this does not break the page; it makes a real page answer 404 to
anything reading the status code, search engines included.

## 5. Pre-render or fall back

`nuxt generate` pre-renders whatever is in `nitro.prerender.routes`. Anything
else is served through the `200.html` SPA fallback by the Flask catch-all. Decide
which one this page is; add it to `nitro.prerender.routes` if it should be static.

## 6. Verify against the real build

```bash
cd frontend && npm run build     # nuxt generate — what Docker actually runs
```

A working dev server does not prove a clean SSG build. If the page reads from an
API on mount, confirm it also paints something sensible before that fetch lands —
the homepage does this with a committed snapshot overlay.

Then E2E if the page has a flow worth pinning: `frontend/e2e/`, and `/e2e` to run it.

**If this goes wrong:** running the real build in step 6 is what catches an SSG
failure before it ships, since a green dev server does not prove one. Reverting
is a `git revert`; nothing here touches the host.
