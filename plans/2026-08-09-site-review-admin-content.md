# Site review — admin panel content edits (manual)

Status: draft
Date: 2026-08-09

## Objective

The content findings from the 2026-08-09 site review that live in the database and must be edited by hand in the admin panel. Companion plan: `plans/2026-08-09-site-review-code-fixes.md` (everything an agent can do in the repo).

## Why these are separate

All home-page copy — hero, stack, footer, and the projects collection — is served from the `home_content` and `project` tables via `/api/home-content`. `frontend/locales/home-content.snapshot.json` looks editable but is a **generated build cache**: `server/deploy-site.sh` overwrites it from the live DB on every deploy by running `scripts/export_home_content.py`. Editing that file by hand gets silently reverted at the next deploy, so these changes have to come from the admin.

## Where to go

`https://erez.ac/admin` → sidebar:

- **Home content** — the fixed text blocks, grouped into **Hero** / **Stack** / **Footer** (collapsed by default). The **English / Suomi** toggle sits at the top right and switches which locale you are editing. Edits go live immediately on save.
- **Projects** — the project collection. Click a project to open the editor drawer; it has its own locale toggle, and the fields are Name, Kind, Tagline, Description, Screenshot caption, Tech (comma-separated) and Links.

Both locales need editing separately for every item below except where noted.

## What "live" means here

Two different surfaces update on different schedules:

- **Immediately** — the running page re-fetches `/api/home-content` on load, so a refresh of erez.ac shows your change right away.
- **At the next deploy** — the prerendered HTML (what a visitor sees on first paint before JS runs, and what Google and LinkedIn's scraper read) comes from the baked snapshot. It catches up automatically the next time anything is pushed to main. No action needed; just don't be surprised if a "view source" or a link preview lags until then.

---

## 1. Sanakenno's tech tags claim Nuxt — it doesn't use Nuxt

**Highest priority.** On a portfolio, a wrong stack claim on your flagship project is exactly what a technical interviewer notices.

`packages/web/package.json` in sanakenno is React 19 + Vite + Zustand + Tailwind + `vite-plugin-pwa`, and the backend is Hono. There is no Nuxt anywhere in that repo — the tag most likely got copied across from the erez.ac project entry.

**Projects → Sanakenno → Tech**, both locales (they currently hold the same list):

| | Value |
|---|---|
| Now | `React, Nuxt, SQLite, PWA, CI/CD` |
| Change to | `React, Vite, Hono, SQLite, PWA, CI/CD` |

That drops the wrong one and adds the two that actually carry the project. Six tags still fits the row.

**While you're in there:** the *Sanakenno Admin tools* entry tags `GPT` — worth a glance to confirm that still matches whichever model the suggestion pipeline calls today. I didn't verify it.

---

## 2. The L1 stack layer undersells the security story

**Home content → Stack → Layers → L1 (Hardware / Rauta) → detail field.**

The current wording says the network exposes "only HTTP", which reads as a weakness. The actual setup — 443 open with TLS, 80 only redirecting and serving ACME, SSH restricted to LAN — is a *strength*, and it's one of the better details on the page.

**English:**

| | Value |
|---|---|
| Now | `Intel NUC mini-PC at home; home network exposing only HTTP to internet, SSH locked to LAN.` |
| Change to | `Intel NUC mini-PC at home; only HTTPS (443) open to the internet, SSH locked to the LAN.` |

**Suomi:**

| | Value |
|---|---|
| Now | `Intel NUC -minitietokone kotona; kotiverkko avaa vain HTTP:n internetiin, SSH lukittu lähiverkkoon.` |
| Change to | `Intel NUC -minitietokone kotona; internetiin avattuna vain HTTPS (443), SSH lukittu lähiverkkoon.` |

---

## 3. Trailing space in the Finnish `/dog` description

**Projects → /dog → Suomi → Description.**

The value ends `…haettu Showlink-palvelusta. ` with a trailing space. Harmless, but it round-trips into the snapshot and the diff. Put the cursor at the very end and delete one character.

English is fine.

---

## 4. Copyright year — do this one *after* the code ships

⚠️ **Sequencing matters.** The companion plan (Phase 3.6) changes `HomeFooter` to interpolate a `{year}` placeholder from the system clock. **Wait until that is deployed**, then make this edit. Doing it first puts a literal `{year}` on the live footer.

**Home content → Footer → Copyright line**, both locales (identical value today):

| | Value |
|---|---|
| Now | `© 2026 Konsta Janhunen` |
| Change to | `© {year} Konsta Janhunen` |

After this the year advances on its own and the field never needs touching again.

Check the footer renders `© 2026 Konsta Janhunen` after saving — if you see a literal `{year}`, the code change hasn't deployed yet; revert to the plain value and retry once it has.

---

## 5. Decide which LinkedIn URL is canonical — needed by the agent

The terminal's `about` command links `https://linkedin.com/in/kvjanhun`; the footer links `https://www.linkedin.com/in/konsta-janhunen-263832165`. These are different URLs and one of them is presumably dead.

Open both, then:

- **If the footer's is the live one** — nothing to do here. Tell the agent, which will fix the terminal string (companion plan, Phase 1.2) and use it in the JSON-LD `sameAs` (Phase 1.5).
- **If the vanity `kvjanhun` one is live** — update **Home content → Footer → Connect links → LinkedIn → href** in *both* locales to match, and tell the agent to use that one.

Either way the agent is blocked on this answer, so it's worth doing early.

---

## 6. ~~Optional — the site doesn't say what you want~~ — dropped

The review suggested an availability line in the hero or footer blurb, plus a CV link in the footer's site links.

**Rejected 2026-08-09.** Konsta is not open for work and is not publishing a CV on the site. Both suggestions existed only to serve a job hunt, so there is nothing left of this item.

The `/about` and `/contact` redirects the review cited as supporting evidence (`nuxt.config.ts:28-29`) stay as they are — they point at `/`, which is correct behaviour for a bookmarked URL.

---

## Checklist

- [ ] 1. Sanakenno tech tags — EN
- [ ] 1. Sanakenno tech tags — FI
- [ ] 1. (optional) sanity-check the `GPT` tag on Sanakenno Admin tools
- [ ] 2. Stack L1 detail — EN
- [ ] 2. Stack L1 detail — FI
- [ ] 3. `/dog` description trailing space — FI
- [ ] 5. Confirm the canonical LinkedIn URL, and relay it to the agent
- [ ] 5. (only if the vanity URL wins) Footer connect link — EN + FI
- [ ] — *wait for the footer-year code change to deploy* —
- [ ] 4. Copyright line — EN
- [ ] 4. Copyright line — FI
- [ ] 4. Verify the rendered footer shows the current year, not `{year}`
- [x] ~~6. (optional) availability line and/or CV link~~ — dropped, not applicable

## Verification

After the batch, load erez.ac in both languages and check the hero, the stack table's bottom row, the expanded Sanakenno card, and the footer. The **Home content** editor also flags unsaved fields per group, so an untouched-looking group with a badge on it means something didn't save.

No tests to run — none of this touches code. The next push to main refreshes the baked snapshot automatically.
