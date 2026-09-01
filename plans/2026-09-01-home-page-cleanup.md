# Home page cleanup — cut the filler, shrink the stack, tie the sections together

Status: approved
Date: 2026-09-01

## Objective

The home page says one thing six times and its largest section is the least
load-bearing one. Cut the lines that carry no fact, halve the stack section, and
give the projects and the stack a reason to reference each other.

## Context

Konsta's read: the page is "all over the place", too many commenty quips with no
content, and the stack section is too big.

The editorial rule for this plan, from that conversation: **the voice stays; every
line must also carry a fact.** The test is not "is this a joke" but "if I delete
this, does the reader lose information". The hero taglines are explicitly in
scope-of-keeping — they are the page's personality and are not the problem.

The problem is that the thesis *"I build every layer myself"* is asserted in
`hero.eyebrow`, `hero.titleLine2`, `hero.body`, `stack.intro`, `stack.footnote`
and `footer.blurb` — six times, in six registers — while the lines that exist only
to be charming (`terminal.footnote`, `footer.nuc`) sit where facts should be.

**Companion: `plans/2026-09-01-home-page-cleanup-admin.md`** — every DB-backed
string, in both locales, ready to type into `/admin`. Committing
`home-content.snapshot.json` is silently reverted at the next deploy
(`server/deploy-site.sh:56`), so that half of the work cannot be done from the repo.

The two 2026-08-09 site-review plans are closed out. Its code phases 1–4 shipped
(commits `2a2f090d`, `99c5ef93`, `00eb2db1`, `bf81fc62`); its admin items are folded
into the companion above, re-verified, with **two corrections** — its proposed L1
wording (`only HTTPS (443) open`) is itself inaccurate because port 80 is open and
redirecting, and its copyright-year item is now unblocked because the `{year}`
interpolation already shipped in `HomeFooter.vue`.

## Content audit (2026-09-01)

Every factual claim on the page was checked against `~/Projects/web_kontissa`,
`~/Projects/sanakenno` and `~/Projects/nuc`. Four are wrong:

- **Sanakenno's tech tags claim Nuxt.** That repo is React + Vite + Zustand +
  Tailwind on the front and Hono + better-sqlite3 + argon2 on the back. No Nuxt.
- **Stack L6 claims "auth with key-based sessions".** `app/auth.py` is Flask-Login
  session cookies with scrypt hashes. There is no key-based auth in the app.
- **Stack L3 welds two true facts into a false one.** fail2ban bans surface in
  Grafana with deliberately no Telegram; what pages to Telegram is `health-alert.sh`
  and the deploy script.
- **Stack L1 has the firewall backwards** — "only HTTP to internet" describes a
  weakness that isn't there.

Also found, and folded into the rewrites: **Litestream is absent from the page.**
Continuous off-site SQLite replication to B2 is one of the stronger things in this
stack and it has never been mentioned.

Verified correct, no action: the `GPT` tag (OpenAI `gpt-5.4` batch API in
sanakenno's `scripts/pangram-review.ts`), the erez.ac and `/dog` project entries,
L5, L7, and the whole hero.

## Approach

Four workstreams, ordered by cost. A and B are copy and CSS and can ship alone; C
carries a schema change and should be its own commit.

### A. Cut the filler (no new code)

| Line | Where | Verdict |
| --- | --- | --- |
| `home.terminal.footnote` | `frontend/locales/{en,fi}.json` | **Delete.** "Originally this site's main attraction…" is changelog voice aimed at a visitor who never saw the old site. `terminal.tag` ("try it · type help") already does the section's real work. |
| `home.stack.footnote` | DB | **Compress.** 45 words restating `stack.intro`. The idea inside it — self-hosting is *why* the security choices are what they are — is worth one line, in the same voice. |
| `home.stack.intro` | DB | **Cut to one line or delete.** Duplicates `hero.body`. If it goes, `stack.tag` ("self-hosted · self-built") carries the framing. |
| `home.footer.blurb` | DB | **Rewrite.** Currently a near-verbatim copy of `home.metaDescription` and a third restatement of the hero. Give it a different job or shorten it hard. |
| `home.hero.taglines` | DB | **Untouched.** |
| `home.footer.nuc` | DB | **String untouched** — it gets a fact attached instead (workstream D). |

Dropping `terminal.footnote` also removes the second of the two `//`-prefixed
lines; the surviving one in `stack.footnote` should lose the prefix so the tic
does not read as a convention.

### B. Shrink the stack

Keep all seven layers — L1→L7 is the site's spine and the anchor for workstream C.
The height comes from prose, not rows:

- delete the intro paragraph and the long footnote (workstream A) — ~5 lines
- rewrite each `layer.detail` to a terse fragment, one line at desktop width
  instead of two — ~7 lines
- tighten `.layer__name` / `.layer__detail` padding in `HomeStack.vue`

Roughly halves the section with no information lost and no code risk beyond CSS.

**Considered and rejected for now:** rendering `detail` as mono chips reusing
`.tech-tag` from `HomeWork.vue`. It would visually rhyme the stack with the
projects, but `FIELD_LAYER_LIST` validates `[{z, layer, title, detail}]`, so a real
array field means touching the validator, the admin editor and the snapshot shape;
and splitting the string on a separator in the component is invisible coupling that
breaks the first time someone types a `·` in the admin. Revisit after C lands.

### C. Layer tags on projects

Each project declares the stack layers it touches, rendered as small `L1`–`L7`
chips in the expanded project panel, linking to `#stack`. The stack table stops
being a parallel brag and becomes the legend for the work.

Language-independent, so it belongs on `Project` alongside `image`, not on
`ProjectTranslation`.

### D. The footer NUC line becomes true

`home.footer.nuc` ("All fine and dandy." / "Tässähän tää menettellööpi.") is the
one line on the page that means nothing. Keep it exactly and hang live uptime off
it, read from `/api/server-info` — already public, already whitelisted, already
feeding the terminal's `fetch`. The page's whole claim is that Konsta runs his own
production platform; this is the only place it is *demonstrated* rather than
asserted, and the joke lands better next to a real number.

Must degrade to the bare string with no layout shift when the fetch fails.

## Files to touch

- `frontend/locales/en.json`, `frontend/locales/fi.json` — delete `home.terminal.footnote`
- `frontend/components/home/HomeTerminal.vue` — drop the footnote element
- `frontend/components/home/HomeStack.vue` — tighter row padding; drop the intro/footnote nodes if those fields go empty
- `frontend/components/home/HomeWork.vue` — render the layer chips
- `frontend/components/home/HomeFooter.vue` — fetch `/api/server-info`, render uptime beside `footer.nuc`
- `app/models.py` — `Project.layers`
- `app/home_content.py` — validate `layers`; surface it in the public + admin dicts
- `frontend/components/admin/AdminProjects.vue` — layer picker in the project drawer
- `scripts/seed_home_content.py`, `scripts/export_home_content.py` — carry `layers` through the snapshot
- `frontend/locales/home-content.snapshot.json` — regenerated, not hand-edited
- `docs/architecture.md` — only if the project shape is documented there

## API / data shape

New column on `project`:

```
layers  TEXT  NOT NULL  DEFAULT '[]'   -- JSON array, e.g. ["L1","L2","L5"]
```

Validated against `^L[1-7]$` per entry, max 7, deduplicated. Deliberately *not*
validated against the `z` values in `home.stack.layers` — those live inside a
per-locale JSON blob, and a cross-field dependency there would make the stack
editor able to invalidate saved projects.

Surfaced in `Project.to_public_dict` (so it rides `/api/home-content` and the
snapshot) and `to_admin_dict`.

**This is a schema change.** `db.create_all()` does not add columns to an existing
table, so it is applied by hand — never from Flask startup.
`scripts/add_project_layers_column.py` performs it and is re-runnable: it checks
`PRAGMA table_info(project)` first and exits cleanly if the column is already there.

### Production procedure

Run **after** the code is deployed. Until it runs, `/api/home-content` raises on the
missing column, so do not leave a long gap between the deploy and step 3.

```bash
# 1. Back up first. Non-negotiable.
cp app/data/site.db app/data/site.db.pre-layers.bak

# 2. Confirm the column is absent (prints the current columns).
docker exec web_kontissa-web-1 \
  python -c "import sqlite3;print([r[1] for r in sqlite3.connect('/app/data/site.db').execute('PRAGMA table_info(project)')])"

# 3. Apply.
docker exec web_kontissa-web-1 python scripts/add_project_layers_column.py

# 4. Verify: every project reports layers, empty until set in the admin.
curl -s localhost:8080/api/home-content | python3 -m json.tool | grep -A3 '"layers"'
```

**Rollback:** restore `site.db.pre-layers.bak` and redeploy the previous commit. The
column is additive with a default, so the previous code also runs unharmed against
the new schema — rolling back only the app is safe and needs no DB action.

## Tests

- **pytest** — `layers` validation (valid list, bad token, non-list, over-long,
  duplicates); round-trip through `to_public_dict` / `to_admin_dict`; snapshot
  export/seed carries `layers`.
- **vitest** — `HomeWork` renders one chip per layer and none when the array is
  empty; `HomeFooter` renders the bare `footer.nuc` string when `/api/server-info`
  rejects, and adds uptime when it resolves.
- **Playwright** — home page renders with the stack section present and the
  terminal footnote gone.
- **`/i18n-check`** after the locale-key deletion, to confirm EN and FI dropped
  the same key and nothing still references it.

## Security considerations

- **New input vector?** Yes, one: the `layers` field. Admin-only (`@admin_required`),
  validated to `^L[1-7]$` per entry with a length cap, stored as JSON, rendered
  through `{{ }}` — never `v-html`. No new public write path.
- **Exposes internal state?** No. `/api/server-info` is already public and its
  response is a deliberately whitelisted coarse snapshot (see the comment at
  `app/api/health.py:79`); the terminal's `fetch` already displays exactly these
  fields. Workstream D adds a second consumer, not new data.
- **Weakens the network boundary?** No. No new port, origin, CORS rule or CSP
  relaxation. The footer fetch is same-origin.

## Out of scope

- The hero taglines and the carousel behaviour.
- The terminal's command set — `useTerminal.js` already implements `help`,
  `about`, `fetch`, `weather`, `cowsay`; nothing to add.
- Section order, the `#work` / "projects" / "Selected projects" naming
  inconsistency, and the `01/02/03` numbering missing from the nav. Real, small,
  and better as a follow-up than smuggled in here.
- Interactive stack→projects filtering (considered; not worth the interaction
  surface until the static chips prove the link is useful).

## Open questions

1. **Does the footer's LinkedIn URL resolve?** The code side has already
   standardised on `konsta-janhunen-263832165` (terminal `about` + JSON-LD
   `sameAs`), but nobody has confirmed it is the live profile. If the vanity
   `linkedin.com/in/kvjanhun` wins instead, it changes two places in code and one
   in the admin.
2. **Is "thousands of plays" still true?** It is the one number on the page and the
   only claim not verifiable from the repos.
3. **Uptime format for D** — `up 34 days` reads well and stays honest; a precise
   figure invites the question of what happened when it resets after a reboot.

Questions 1 and 2 of the original draft are resolved: the replacement strings are
written, in both locales, in the companion admin plan.
