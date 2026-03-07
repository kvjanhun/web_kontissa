# docs-keeper memory — web_kontissa (erez.ac)

## Project Identity
- Personal portfolio for Konsta Janhunen at erez.ac
- Vue 3 SPA + Flask JSON API + SQLite, Docker-deployed on RHEL/Intel NUC

## Key Files to Watch
- `app/api/kenno.py` — Sanakenno game API; all puzzles in KennoPuzzle DB table (no hardcoded data in app code)
- `app/__init__.py` — Flask app factory: LoginManager + Flask-Limiter (30 req/min)
- `frontend/src/router.js` — authoritative route list (currently 11 routes)
- `requirements.txt` — authoritative Python dep list
- `tests/` — pytest suite; conftest.py uses in-memory SQLite, disables rate limiter

## Confirmed Patterns
- Port 5001 everywhere (run.py, vite.config.js proxy) — macOS AirPlay blocks 5000
- Puzzle cache in kenno.py is lazy (on first access), not eager at startup
- `/api/kenno` returns: center, letters, words, max_score, puzzle_number, total_puzzles
- `POST /api/kenno/block` (admin) — blocks a word; stored in `blocked_words` table (BlockedWord model); clears _PUZZLE_CACHE
- `scripts/process_kotus.py` is a one-time data generation script, not part of app runtime
- Tech stack includes Flask-Limiter — must appear in requirements.txt comment and tech table
- Sanakenno route is `/sanakenno` (component `SanakennoPage.vue`); old name `BeeGamePage.vue` / `/bee` is retired
- Sanakenno localStorage: `sanakenno_state` = {puzzleNumber, foundWords[], score, hintsUnlocked[], startedAt (epoch ms)}; `sanakenno_admin_puzzle` key is retired (admin puzzle selection now session-local in AdminKennoPuzzleTool.vue)
- Sanakenno hint IDs + icons: `summary` 📊 "Yleiskuva", `letters` 🔤 "Alkukirjaimet", `distribution` 📏 "Pituusjakauma", `pairs` 🔠 "Alkuparit"; each unlocked hint header is individually collapsible (▼/▲); `hintsCollapsed` ref (session-only Set, not persisted to localStorage)
- Sanakenno ranks (7 levels): Etsi sanoja!(0%), Hyvä alku(2%), Nyt mennään!(10%), Onnistuja(20%), Sanavalmis(40%), Ällistyttävä(70%), Täysi kenno(100%); authoritative list is VALID_RANKS constant in kenno.py
- Sanakenno achievement tracking: POST /api/kenno/achievement (public, rate-limited, session-deduped via session["achieved_ranks"] storing "puzzle:rank" keys); GET /api/kenno/achievements (admin, days param 1-90, default 30 on server); AdminKennoStats.vue default period is 7d (not 30d); AdminPageViews.vue also defaults to 7d
- Sanakenno puzzle count: 41 (was 50); rotation: `(START_INDEX + days_since ROTATION_START(2026-02-24)) % 41`, START_INDEX=1
- Sanakenno: /sanakenno Flask route patches OG meta tags in routes.py; SanakennoPage swaps favicon to orange hex SVG on mount
- Sanakenno timer: tracks startedAt + totalPausedMs via visibilitychange + blur + pagehide
- models.py now has BlockedWord + KennoConfig (key-value store) + KennoAchievement (anonymous rank milestone records: puzzle_number, rank, score, max_score, words_found, elapsed_ms, achieved_at)
- Sanakenno UI features: progress bar (`progressToNextRank`), shake on invalid (`word-shake` 0.4s), rank-up toast 3s ("Uusi taso: …!"), orange re-submit flash (`lastResubmittedWord` ref, 1.5s), all-found banner (`allFound` computed)
- Share button label: "Jaa tulos" (was "Kopioi tila"); shows preview toast after copying
- Sanakenno state restore filters foundWords against current puzzle word list (removes blocked/stale words)
- Sanakenno browser title: "Sanakenno — #N" (N = puzzle number)
- Sanakenno SVG hexagons: role="button" + aria-label on each for screen reader access
- `useNavLinks.js` composable: shared nav link list consumed by AppHeader + AppFooter
- recipes.py: `_validate_recipe_data()` shared helper for create+update; `_parse_ingredients()` validates isinstance(item, dict)
- SECRET_KEY dev fallback: fixed string (not os.urandom) so sessions survive Flask restarts in dev
- Logout (useAuth.js): awaits server response before clearing client state; button uses @click.prevent + manual navigation
- Section model: `section_type` column (String, default 'text', valid: 'text'|'pills'). POST sets it (default 'text' if omitted); PUT patches it only when present. Invalid value returns 400. Included in all GET responses.
- SectionBlock.vue: card-style article (rounded-lg, bg-secondary, border) for all section types. 'text' type renders via v-html with `.section-content :deep(p + p)` margin. 'pills' type splits content on commas and renders each as a badge span (no v-html). `pills` computed strips whitespace and filters empty values.
- AdminSections.vue: create + edit forms have a `<select>` for section_type (Text/Pills). Content textarea placeholder switches dynamically based on selected type.
- AdminPage.vue tabs (6): Sections, Analytics, Recipes, Health, Sanakenno, Kennotyökalu
- AdminKennoPuzzleTool.vue: puzzle number input (1-indexed), variations grid, full word list (multi-column, 10/col), per-word block button; defaults to today's puzzle_number from GET /api/kenno
- SanakennoPage.vue layout: title in top bar row (no separate section); sticky score+progress+hints-toggle/share row; admin controls removed entirely
- Found words in SanakennoPage: compact (last 6, no-wrap) vs expanded (full multi-column alphabetical); "Kaikki ▼" / "Vähemmän ▲" toggle

## Structure Notes
- `scripts/` and `tests/` are top-level siblings of `app/` and `frontend/`
- Tree in CLAUDE.md must show `app/` as `├──` (not `└──`) since scripts/tests follow it
