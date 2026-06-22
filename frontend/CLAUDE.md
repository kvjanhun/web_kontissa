# Frontend — Nuxt 3

## Key Patterns

- **Composition API with `<script setup>`** exclusively — no Options API
- **Auto-imports**: Vue APIs (`ref`, `computed`, `onMounted`), Nuxt composables (`useRoute`, `useHead`, `navigateTo`), components, stores, and composables are all auto-imported. No explicit imports needed in `<script setup>`.
- **File-based routing**: Pages in `pages/` define routes. Use `definePageMeta()` for route metadata. Nested dynamic routes use `[slug]/index.vue` + `[slug]/edit.vue` (NOT `[slug].vue` + `[slug]/edit.vue` — Nuxt treats the latter as parent/child layout).
- **Pinia stores**: Composition API style (`defineStore` with setup function). Use `storeToRefs()` for reactive refs/computeds when destructuring. Actions destructure directly.
- **SSG**: `nuxt generate` pre-renders routes in `nitro.prerender.routes`. Non-pre-rendered routes use `200.html` SPA fallback (served by Flask catch-all).
- **Auth guards**: `middleware/auth.global.js` checks `requiresAuth`/`requiresAdmin` page meta. Skips server-side (`import.meta.server`) since session cookies aren't available during SSR.
- **Layouts**: `default.vue` (header/footer, calls `checkAuth` on mount) and `standalone.vue` (bare, used by standalone tools like `/dog`).
- **i18n**: Pinia `useI18nStore` — `t('key')` / `t('key', { params })`. Fallback: locale → English → raw key. Route titles via `titleKey` page meta resolved in `middleware/pageview.global.js`.
- **Styling**: Tailwind utilities + CSS custom properties for theme colors. Inline `:style` bindings for dynamic theme-aware colors.
- **XSS safety**: `v-html` only on admin-authored section content (`type: 'text'`). All other content uses `{{ }}` auto-escaping.

## Components

- **SectionBlock.vue**: Handles `quote` (blockquote, no card), `currently` (label:value rows), `pills` (3-col grid), and a default `text` branch (v-html via `renderMarkdown`). Card types have orange accent bar. The current standalone home route handles `intro` and `project` sections directly in `pages/index.vue`.
- **AboutSectionCard.vue**: Used for `project` (name|url|description|icon lines), `currently`, `text`, and other card types in the about bento layout.
- **GitStatsSection.vue**: Fetches `/api/project-stats` (GitHub API, cached 6h in `utils.py`) and renders commit count, repo age, size, and languages.
- **TimelineSection.vue**: Parses `date|title|description` lines; auto-scrolling marquee animation.
- **TerminalWindow.vue**: Interactive shell with commands (help, about, fetch, weather, cowsay, etc.), fuzzy "Did you mean" suggestions. On first load it auto-runs a looping choreography (`help → about → weather → date | cowsay -f tux → clear`); any user keystroke aborts the loop via `stopChoreography()`.
- **admin/**: AdminSections, AdminPageViews, AdminRecipes, AdminHealth.

## Dog Show Frontend (`features/dog/`)

Standalone `/dog` browser for Showlink data. Read `features/dog/AGENTS.md` before changing this feature. The frontend must not fan out across all breed result pages; whole-show filtering uses `/api/dog/shows/<id>/all-results`, which is backed by the persisted server cache documented in `../docs/dog-show-browser.md`.

- **Route entry**: `pages/dog/index.vue` only sets page metadata/layout and renders `features/dog/DogBrowser.vue`.
- **Feature module**: Dog-specific components, `useDogBrowser.js`, `dogResults.js`, and `dog.css` live under `features/dog/`; do not move them into shared components unless another route genuinely reuses them.
- **Route state**: `?show=<id>` opens a show; `?show=<id>&group=<group>&breed=<breed>` opens a breed result page.
- **Show detail tabs**: `Rotuluettelo` lists breeds; `Koirat & Tulokset` loads the whole-show cache and filters all dogs. The breed list groups by FCI group (default), judge, or alphabetically via mode tabs.
- **Whole-show loading**: A `202` warming response keeps the animated progress card visible and polls using the backend `retry_after` value.
- **Filters**: Whole-show and breed result filters support text, grade, class, and awards. `HYL`, `EVA`, and `POISSA` are intentionally separate grade filters.
- **Search**: Breed search uses the backend persisted index and polls index stats while indexing is incomplete.

## Composables

All in `frontend/composables/` (auto-imported):

- `useGameTimer.js` — elapsed timer with pause/resume on `visibilitychange`/`blur`/`pagehide`
- `useHintData.js` — pure computeds for hint panels: `letterMap`, `unfoundLengths`, `pangramStats`, `lengthDistribution`, `pairMap`
- `useMarkdown.js` — wraps `marked` + isomorphic DOMPurify; exported as `renderMarkdown(source)`
- `useSafeHtml.js` — shared safe URL, HTML escaping, sanitization, and inline link helpers
- `useNavLinks.js` — shared nav link list consumed by `AppHeader` and `AppFooter`
- `usePageView.js` — fires `POST /api/pageview` on route change (used in `pageview.global.js`)
- `useTerminal.js` — terminal command registry and execution logic for `TerminalWindow.vue`
- `useThemeColor.js` — syncs `<meta name="theme-color">` and `<html>` background via `MutationObserver`

## E2E Testing

- **Config**: `playwright.config.js` — Flask on :5001, `nuxt build && nuxt preview` on :3000. Override with `PLAYWRIGHT_API_PORT` / `PLAYWRIGHT_WEB_PORT`; Nuxt receives matching `API_BASE_URL`.
- **Why `nuxt build`**: The node-server preset supports `routeRules` proxy. `nuxt generate` (static preset) uses `npx serve` which has no proxy.
- **Hydration fixture**: `e2e/fixtures/base.js` wraps `page.goto()` with `waitForLoadState('networkidle')` to ensure Vue hydration completes before interactions.
- **Separate test DB**: Playwright spawns Flask with `DATABASE_URI=sqlite:///app/data/test-e2e.db` — distinct from the dev `site.db`. Seed with `python3 scripts/seed_e2e.py` before first run and after any schema change.
- **Test credentials**: `admin@test.com` / `adminpass123`, `user@test.com` / `userpass123` (seeded by `scripts/seed_e2e.py`)
- **Local run gotcha**: `reuseExistingServer: !process.env.CI` — any Flask already listening on :5001 (e.g. your dev server pointed at `site.db`) is picked up instead of the properly-configured test one, and DB-backed specs (auth, admin, recipes) will fail. Stop the dev Flask before running locally, prefix with `CI=1`, or use alternate ports.
- E2E specs cover public pages, auth/admin flows, recipes, and the dog-show browser.

## Design

- Warm stone-grey palette with orange accent (#ff643e)
- Dark/light mode via `.dark` class on `<html>` with CSS custom property overrides
- Fonts: DM Sans (body), Commit Mono (terminal / all monospace)
- Mobile-first: always-hamburger nav
- Accessibility: skip-to-content, `:focus-visible` rings, `aria-expanded` menu, `aria-live` announcer, and `prefers-reduced-motion` respected
