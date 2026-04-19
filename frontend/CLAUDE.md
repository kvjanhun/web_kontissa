# Frontend — Nuxt 3

## Key Patterns

- **Composition API with `<script setup>`** exclusively — no Options API
- **Auto-imports**: Vue APIs (`ref`, `computed`, `onMounted`), Nuxt composables (`useRoute`, `useHead`, `navigateTo`), components, stores, and composables are all auto-imported. No explicit imports needed in `<script setup>`.
- **File-based routing**: Pages in `pages/` define routes. Use `definePageMeta()` for route metadata. Nested dynamic routes use `[slug]/index.vue` + `[slug]/edit.vue` (NOT `[slug].vue` + `[slug]/edit.vue` — Nuxt treats the latter as parent/child layout).
- **Pinia stores**: Composition API style (`defineStore` with setup function). Use `storeToRefs()` for reactive refs/computeds when destructuring. Actions destructure directly.
- **SSG**: `nuxt generate` pre-renders routes in `nitro.prerender.routes`. Non-pre-rendered routes use `200.html` SPA fallback (served by Flask catch-all). `/sanakenno` IS pre-rendered (has `useHead()` for OG tags).
- **Auth guards**: `middleware/auth.global.js` checks `requiresAuth`/`requiresAdmin` page meta. Skips server-side (`import.meta.server`) since session cookies aren't available during SSR.
- **Layouts**: `default.vue` (header/footer, calls `checkAuth` on mount) and `standalone.vue` (bare, used by sanakenno via `definePageMeta({ layout: 'standalone' })`).
- **i18n**: Pinia `useI18nStore` — `t('key')` / `t('key', { params })`. Fallback: locale → English → raw key. Route titles via `titleKey` page meta resolved in `middleware/pageview.global.js`.
- **Styling**: Tailwind utilities + CSS custom properties for theme colors. Inline `:style` bindings for dynamic theme-aware colors.
- **XSS safety**: `v-html` only on admin-authored section content (`type: 'text'`). All other content uses `{{ }}` auto-escaping.

## Components

- **SectionBlock.vue**: Handles `quote` (blockquote, no card), `currently` (label:value rows), `pills` (3-col grid), and a default `text` branch (v-html via `renderMarkdown`). Card types have orange accent bar. Not used for `intro`, `project`, `git_stats`, or `timeline` — those are dispatched in `pages/about.vue` to `AboutSectionCard`, `GitStatsSection`, and `TimelineSection`.
- **AboutSectionCard.vue**: Used for `project` (name|url|description|icon lines), `currently`, `text`, and other card types in the about bento layout.
- **GitStatsSection.vue**: Fetches `/api/project-stats` (GitHub API, cached 6h in `utils.py`) and renders commit count, repo age, size, and languages.
- **TimelineSection.vue**: Parses `date|title|description` lines; auto-scrolling marquee animation.
- **TerminalWindow.vue**: Interactive shell with commands (help, about, fetch, weather, cowsay, etc.), fuzzy "Did you mean" suggestions. On first load it auto-runs a looping choreography (`help → about → weather → date | cowsay -f tux → clear`); any user keystroke aborts the loop via `stopChoreography()`.
- **admin/**: AdminSections, AdminPageViews, AdminRecipes, AdminHealth, AdminKennoStats, AdminKennoPuzzleTool, AdminBlockedWords, KennoVariationsGrid, KennoWordList.

## Sanakenno Frontend (pages/sanakenno.vue)

SVG honeycomb, keyboard input (letters/Backspace/Enter), client-side word validation via SHA-256 hash comparison. Standalone layout. All game UI strings are Finnish-only.

- **Sticky bar**: Score, progress bar, hints toggle, and share button in `position: sticky` section. Spacer height is `3rem` (standalone layout has no padding wrapper).
- **State persistence**: `localStorage` key `sanakenno_state_{puzzleNumber}` with `{foundWords[], score, hintsUnlocked[], startedAt}`. Legacy migration from single-key format.
- **Hints (Avut)**: 4 individually unlockable hints: summary (📊), letters (🔤), distribution (📏), pairs (🔠). Unlock state persists in localStorage. Collapse state is session-only.
- **Celebrations**: Ällistyttävä (70%) → glow banner 5s. Täysi kenno (100%) → golden glow 8s. Both dismissible. Other rank-ups → "Uusi taso" message 3s.
- **Share (Jaa tulos)**: Copies puzzle number, rank, score/max, hint icons to clipboard.
- **Found words**: Last 6 visible, "Kaikki ▼" expands to full alphabetical list. Re-submit flashes orange 1.5s.
- **Touch**: `touch-action: manipulation` on root div. `touch-action: none` on honeycomb SVG.
- **OG meta**: Set via `useHead()` — baked into pre-rendered HTML. Flask `sanakenno_page()` route removed.
- **Favicon**: `useHead()` sets `/sanakenno-favicon-v2.png` as the icon. Nuxt's head manager swaps it in/out with the page lifecycle. `useFaviconSwap.js` no longer exists — the `useHead` approach is sufficient.
- **Timer**: `useGameTimer.js` tracks elapsed time with pause/resume on tab visibility.
- **Achievement tracking**: Fire-and-forget `POST /api/kenno/achievement` on each rank transition.

## Composables

All in `frontend/composables/` (auto-imported):

- `useGameTimer.js` — elapsed timer with pause/resume on `visibilitychange`/`blur`/`pagehide`
- `useHintData.js` — pure computeds for hint panels: `letterMap`, `unfoundLengths`, `pangramStats`, `lengthDistribution`, `pairMap`
- `useMarkdown.js` — wraps `marked` + `DOMPurify`; exported as `renderMarkdown(source)`
- `useNavLinks.js` — shared nav link list consumed by `AppHeader` and `AppFooter`
- `usePageView.js` — fires `POST /api/pageview` on route change (used in `pageview.global.js`)
- `useSanakennoLogic.js` — pure game logic: `recalcScore`, `rankForScore`, `rankThresholds`, `progressToNextRank`, `colorizeWord`, `toColumns`
- `useTerminal.js` — terminal command registry and execution logic for `TerminalWindow.vue`
- `useThemeColor.js` — syncs `<meta name="theme-color">` and `<html>` background via `MutationObserver`

## E2E Testing

- **Config**: `playwright.config.js` — Flask on :5001, `nuxt build && nuxt preview` on :3000
- **Why `nuxt build`**: The node-server preset supports `routeRules` proxy. `nuxt generate` (static preset) uses `npx serve` which has no proxy.
- **Hydration fixture**: `e2e/fixtures/base.js` wraps `page.goto()` with `waitForLoadState('networkidle')` to ensure Vue hydration completes before interactions.
- **Separate test DB**: Playwright spawns Flask with `DATABASE_URI=sqlite:///app/data/test-e2e.db` — distinct from the dev `site.db`. Seed with `python3 scripts/seed_e2e.py` before first run and after any schema change.
- **Test credentials**: `admin@test.com` / `adminpass123`, `user@test.com` / `userpass123` (seeded by `scripts/seed_e2e.py`)
- **Local run gotcha**: `reuseExistingServer: !process.env.CI` — any Flask already listening on :5001 (e.g. your dev server pointed at `site.db`) is picked up instead of the properly-configured test one, and DB-backed specs (auth, admin, recipes) will fail. Stop the dev Flask before running locally, or prefix with `CI=1`.
- 30 tests across 7 spec files.

## Design

- Warm stone-grey palette with orange accent (#ff643e)
- Dark/light mode via `.dark` class on `<html>` with CSS custom property overrides
- Fonts: DM Sans (body), Commit Mono (terminal / all monospace)
- Mobile-first: always-hamburger nav
- Accessibility: skip-to-content, `:focus-visible` rings, `aria-expanded` menu, `aria-live` announcer, `role="button"` + `aria-label` on honeycomb hexagons, `prefers-reduced-motion` respected
