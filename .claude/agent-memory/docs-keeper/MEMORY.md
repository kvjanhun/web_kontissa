# docs-keeper memory — web_kontissa (erez.ac)

## Project Identity
- Personal portfolio for Konsta Janhunen at erez.ac
- Vue 3 SPA + Flask JSON API + SQLite, Docker-deployed on RHEL/Intel NUC

## Key Files to Watch
- `app/api/bee.py` — PUZZLES list drives the Sanakenno game (count = cycle length)
- `app/__init__.py` — Flask app factory: LoginManager + Flask-Limiter (30 req/min)
- `frontend/src/router.js` — authoritative route list (currently 11 routes)
- `requirements.txt` — authoritative Python dep list
- `tests/` — pytest suite; conftest.py uses in-memory SQLite, disables rate limiter

## Confirmed Patterns
- Port 5001 everywhere (run.py, vite.config.js proxy) — macOS AirPlay blocks 5000
- Puzzle cache in bee.py is lazy (on first access), not eager at startup
- `/api/bee` returns: center, letters, words, max_score, puzzle_number, total_puzzles
- `POST /api/bee/block` (admin) — blocks a word; stored in `blocked_words` table (BlockedWord model); clears _PUZZLE_CACHE
- `scripts/process_kotus.py` is a one-time data generation script, not part of app runtime
- Tech stack includes Flask-Limiter — must appear in requirements.txt comment and tech table
- Sanakenno route is `/sanakenno` (component `SanakennoPage.vue`); old name `BeeGamePage.vue` / `/bee` is retired
- Sanakenno localStorage: `sanakenno_state` = {puzzleNumber, foundWords[], score, hintsUnlocked[], startedAt (epoch ms)}; `sanakenno_admin_puzzle` = admin's selected puzzle index
- Sanakenno hint IDs + icons: `summary` 📊 "Yleiskuva" (line 1: X/Y sanaa jäljellä + % + pangrams; line 2: distinct word lengths + longest word length), `letters` 🔤 "Alkukirjaimet" (remaining per starting letter), `distribution` 📏 "Pituusjakauma" (count per word length)
- Sanakenno ranks (7 levels): Etsi sanoja!(0%), Hyvä alku(2%), Nyt mennään!(10%), Onnistuja(20%), Sanavalmis(40%), Ällistyttävä(70%), Täysi kenno(100%)
- Sanakenno puzzle count: 41 (was 50); rotation: `(START_INDEX + days_since ROTATION_START(2026-02-24)) % 41`, START_INDEX=1
- Sanakenno: /sanakenno Flask route patches OG meta tags in routes.py; SanakennoPage swaps favicon to orange hex SVG on mount
- Sanakenno timer: tracks startedAt + totalPausedMs via visibilitychange + blur + pagehide
- models.py now has BlockedWord + BeeConfig (key-value store for future use)
- Sanakenno UI features: progress bar (`progressToNextRank`), shake on invalid (`word-shake` 0.4s), rank-up toast 3s ("Uusi taso: …!"), orange re-submit flash (`lastResubmittedWord` ref, 1.5s), all-found banner (`allFound` computed)
- Share button label: "Jaa tulos" (was "Kopioi tila"); shows preview toast after copying
- Sanakenno state restore filters foundWords against current puzzle word list (removes blocked/stale words)
- Sanakenno browser title: "Sanakenno — #N" (N = puzzle number)
- Sanakenno SVG hexagons: role="button" + aria-label on each for screen reader access
- `useNavLinks.js` composable: shared nav link list consumed by AppHeader + AppFooter
- recipes.py: `_validate_recipe_data()` shared helper for create+update; `_parse_ingredients()` validates isinstance(item, dict)
- SECRET_KEY dev fallback: fixed string (not os.urandom) so sessions survive Flask restarts in dev
- Logout (useAuth.js): awaits server response before clearing client state; button uses @click.prevent + manual navigation

## Structure Notes
- `scripts/` and `tests/` are top-level siblings of `app/` and `frontend/`
- Tree in CLAUDE.md must show `app/` as `├──` (not `└──`) since scripts/tests follow it
