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
- **Icons**: `@nuxt/icon` v1.x (the Nuxt 3-compatible line — **do not bump to v2, which requires Nuxt 4**) renders Iconify sets via `<Icon name="prefix:name" />`, sized by `font-size`/`1em` and inheriting `currentColor`. Monochrome **Solar** (`solar:*`, `@iconify-json/solar`) is the UI-chrome set (theme toggle, hamburger, chevrons); monochrome **Simple Icons** (`simple-icons:*`, `@iconify-json/simple-icons`) supplies brand logos (GitHub/LinkedIn) for footer & project links — chosen via the `useLinkIcon()` composable (href → icon: GitHub/LinkedIn logos, `solar:letter-bold` for `mailto:`, `solar:arrow-right-up-bold` otherwise); **Flat Color Icons** (`fc:*`, `@iconify-json/flat-color-icons`) is installed and reserved for the multicolor admin panel. Config in `nuxt.config.ts` uses `mode: 'css'` (mask + `background-color: currentColor`) — **not `mode: 'svg'`, which dropped the inlined paths on client hydration under SSG and left icons stuck black/invisible regardless of theme** — and bundles icons at build with `fallbackToApi: false` + `clientBundle` (explicit `icons` list for dynamically-named icons that `scan` can't see — toggle states and the `useLinkIcon()` results — plus `scan: true` for static names), so the SSG output makes **zero runtime requests to api.iconify.design** (mask data URIs are inlined). Terminal weather glyphs (`components/weatherIcons.js`) are Solar `*-bold` SVG bodies inlined as strings, since they're injected via `v-html` and can't use `<Icon>`.
- **XSS safety**: `v-html` only on admin-authored section content (`type: 'text'`). All other content uses `{{ }}` auto-escaping.

## Components

- **TerminalWindow.vue**: Interactive shell with commands (help, about, fetch, weather, cowsay, etc.), fuzzy "Did you mean" suggestions. On first load it auto-runs a looping choreography (`help → about → weather → date | cowsay -f tux → clear`); any user keystroke aborts the loop via `stopChoreography()`. Reused inside the homepage terminal frame.
- **home/**: Homepage redesign sections — see Homepage below.
- **admin/**: AdminSections, AdminPageViews, AdminRecipes, AdminHealth.

## Homepage (`pages/index.vue` + `components/home/`)

The main page (`/`) is a self-contained landing page (the only public page — `/about` and `/contact` `redirect: '/'`). It uses the `standalone` layout and its own header/footer, **not** `AppHeader`/`AppFooter`.

- **Content is locale-driven, not DB-driven (Stage 1).** All copy lives under the `home.*` keys in `locales/{en,fi}.json`. Scalars use `t('home.…')`; structured lists (`home.projects`, `home.stack.layers`, `home.footer.connectLinks`/`siteLinks`) use the i18n store's `tm()` raw accessor and are kept structurally identical across locales. Stage 2 will move this content into the database + admin editor.
- **Components** (in `components/home/`; names carry the `Home` directory prefix per Nuxt auto-import, like `admin/Admin*`): `HomeHeader` (sticky/blurred bar, `#work`/`#stack`/`#terminal` anchors, lang + theme toggles wired directly to `useI18nStore`/`useDarkModeStore`, mobile hamburger drawer), `HomeHero`, `HomeWork` (expandable project accordion via `grid-template-rows` 0fr→1fr), `HomeStack` (L1→L7 layer table), `HomeTerminal` (mac-frame around the reused `TerminalWindow`), `HomeFooter`.
- **Palette/fonts are scoped** to a `.home-dc` wrapper (see Design). The page does not call `/api/sections`.
- **Reveal-on-scroll**: `useScrollReveal()` returns a `v-reveal` directive (IntersectionObserver fade-up; skipped under `prefers-reduced-motion` / no-JS — content stays visible).

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
- `useMarkdown.js` — wraps `marked` + isomorphic DOMPurify; exported as `renderMarkdown(source)` (retained for Stage 2 admin-authored content rendering; no current caller)
- `useScrollReveal.js` — returns a `v-reveal` IntersectionObserver fade-up directive for the homepage (reduced-motion / no-JS safe)
- `useSafeHtml.js` — shared safe URL, HTML escaping, sanitization, and inline link helpers
- `useNavLinks.js` — shared nav link list consumed by `AppHeader` and `AppFooter`
- `useLinkIcon.js` — maps a link `href` to a leading icon (GitHub/LinkedIn brand logos, `mailto:` letter, diagonal go-arrow otherwise); used by `HomeFooter`/`HomeWork`
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

- **Site-wide**: warm stone-grey palette with orange accent (#ff643e); fonts DM Sans (body) + Commit Mono (monospace).
- **Homepage**: its own cooler near-black/cream palette + IBM Plex Sans/Mono typography, all **scoped to the `.home-dc` wrapper** in `assets/style.css` (`--bg`/`--panel`/`--line`/`--tx`/`--accent` etc.). IBM Plex woff2 (latin subset) is self-hosted in `public/fonts/`. The rest of the site is unaffected.
- **Texture + readability plate**: `.home-dc` paints a faint graph-paper grid (`--grid` linear-gradient lines) behind everything not on an opaque panel. Text that sits directly on that grid (hero eyebrow/title/body, section labels, project heads/details, stack intro/footnote) carries the `.home-plate` utility — a `::before` filled with `var(--bg)` (same colour as the page, so it only hides the local grid lines, never reads as a box) masked by the **intersection of a horizontal and a vertical linear gradient** (`mask-composite: intersect`, with `-webkit-mask-composite: source-in` fallback), so the fill feathers to transparent on every edge and the texture re-emerges around each block. Panels (stack table, terminal frame, screenshots) and the footer (`--bg-2`) are already opaque, so they don't need it. The **terminal footnote** deliberately omits the plate even though it's mono text: it sits inside the terminal frame's `box-shadow`, where a solid `--bg` plate would punch a bright rectangle through the shadow.
- Dark/light mode via `.dark` class on `<html>` with CSS custom property overrides (one toggle/store/flash-prevention drives both palettes)
- Mobile-first: always-hamburger nav
- Accessibility: skip-to-content, `:focus-visible` rings, `aria-expanded` menu, `aria-live` announcer, and `prefers-reduced-motion` respected
