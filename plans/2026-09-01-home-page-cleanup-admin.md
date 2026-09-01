# Home page cleanup — admin panel edits

Status: approved
Date: 2026-09-01

Companion to `plans/2026-09-01-home-page-cleanup.md` (the code side). This file is
everything that lives in the database and must be typed into `/admin` by hand.

It **supersedes `plans/2026-08-09-site-review-admin-content.md`** — every unfinished
item from that plan is folded in below, re-verified, and in two cases corrected.
Work from this file; that one is closed.

## Why these can't be committed

`frontend/locales/home-content.snapshot.json` looks editable but is a generated
build cache — `server/deploy-site.sh:56` overwrites it from the live DB on every
deploy. Hand-edits there are silently reverted.

## Where to go

`https://erez.ac/admin` → **Home content** (Hero / Stack / Footer groups, EN/FI
toggle top right) and **Projects** (drawer per project, own locale toggle).

Edits are live on the next page load. The prerendered HTML that crawlers and
link-preview scrapers read catches up at the next push to main.

---

# Part 1 — Factual corrections

Four claims on the page are wrong. These are the priority; a portfolio whose pitch
is precision about infrastructure cannot misdescribe its own infrastructure.

## 1.1 Sanakenno's tech tags claim Nuxt — it does not use Nuxt

**Projects → Sanakenno → Tech** (both locales; they hold the same list today).

Verified against `~/Projects/sanakenno`: `packages/web/package.json` is React 19 +
Vite + Zustand + Tailwind + `vite-plugin-pwa`, and the root `package.json` backend
is Hono + better-sqlite3 + argon2. There is no Nuxt anywhere in that repo — the tag
was copied across from the erez.ac entry.

| | Value |
|---|---|
| Now | `React, Nuxt, SQLite, PWA, CI/CD` |
| Change to | `React, Vite, Hono, SQLite, PWA, CI/CD` |

## 1.2 L6 claims an auth mechanism that does not exist

**Home content → Stack → Layers → L6 (Application / Sovellus) → detail.**

"auth with key-based sessions" describes nothing in the codebase. `app/auth.py`
uses Flask-Login session cookies with werkzeug scrypt password hashing; there is no
key-based or token auth anywhere in the Flask app.

The rewrite below also puts **Litestream** on the page for the first time —
continuous off-site SQLite replication to Backblaze B2 is one of the better things
in this stack and the page has never mentioned it.

**English**

| | Value |
|---|---|
| Now | `Flask/Python APIs, SQLite, auth with key-based sessions, content + analytics.` |
| Change to | `Flask APIs, session-cookie auth with scrypt hashes, SQLite replicated off-site by Litestream.` |

**Suomi**

| | Value |
|---|---|
| Now | `Flask/Python-rajapinnat, SQLite, avainpohjaiset istunnot, sisältö + analytiikka.` |
| Change to | `Flask-rajapinnat, evästeistunnot scrypt-tiivisteillä, SQLite varmuuskopioituu jatkuvasti ulos Litestreamilla.` |

## 1.3 L3 implies fail2ban alerts to Telegram — it doesn't

**Home content → Stack → Layers → L3 (Operations / Operointi) → detail.**

"Fail2Ban for additional security. Alerts live to Telegram." reads as one claim.
Per `~/Projects/nuc`, bans surface in **Grafana only, deliberately no Telegram**;
what actually pages you is `health-alert.sh` (container health, every 5 min) and the
deploy script. Both true, but the sentence order welds them into a false one.

**English**

| | Value |
|---|---|
| Now | `Full metrics and logging with Loki, Prometheus and Grafana. Fail2Ban for additional security. Alerts live to Telegram.` |
| Change to | `Logs and metrics through Loki, Prometheus and Grafana; fail2ban bans scanners on sight. Health alerts reach me on Telegram.` |

**Suomi**

| | Value |
|---|---|
| Now | `Täysi monitorointi ja lokitus Lokin, Prometheusin ja Grafanan voimin. Fail2Ban lisäämässä tietoturvaa. Hälytykset suoraan Telegramiin.` |
| Change to | `Lokit ja metriikat Lokilla, Prometheuksella ja Grafanalla; fail2ban bannaa skannerit saman tien. Terveyshälytykset tulevat Telegramiin.` |

## 1.4 Sanakenno's reach — players, not plays

**Projects → Sanakenno → Description**, last sentence, both locales.

"Thousands of plays" is true but reads as a traffic boast; dozens of *players* is
the more honest and better-sounding figure. It is a cumulative total, not a daily
one, so the wording has to say so — "dozens of players" unqualified reads as daily.

**English**

| | Value |
|---|---|
| Now (last sentence) | `Live at sanakenno.fi with thousands of plays.` |
| Change to | `Live at sanakenno.fi, played by dozens of people so far.` |

**Suomi**

| | Value |
|---|---|
| Now (last sentence) | `Käytössä osoitteessa sanakenno.fi, tuhansia pelikertoja.` |
| Change to | `Käytössä osoitteessa sanakenno.fi, kymmeniä pelaajia tähän mennessä.` |

Leave the rest of the description as it is; only the final sentence changes.

## 1.5 L1 gets the firewall backwards

**Home content → Stack → Layers → L1 (Hardware / Rauta) → detail.**

"exposing only HTTP to internet" reads as a weakness and is wrong — 443 carries
TLS, 80 exists only to redirect and to serve ACME challenges, SSH is LAN-only.

⚠️ The superseded 2026-08-09 plan proposed `only HTTPS (443) open to the internet`.
**Do not use that wording** — port 80 *is* open, it just redirects, so that fix
trades one inaccuracy for another. Use this instead:

**English**

| | Value |
|---|---|
| Now | `Intel NUC mini-PC at home; home network exposing only HTTP to internet, SSH locked to LAN.` |
| Change to | `Intel NUC at home. Only 80 and 443 reach the internet, and 80 only redirects; SSH is LAN-only.` |

**Suomi**

| | Value |
|---|---|
| Now | `Intel NUC -minitietokone kotona; kotiverkko avaa vain HTTP:n internetiin, SSH lukittu lähiverkkoon.` |
| Change to | `Intel NUC kotona. Internetiin näkyy vain 80 ja 443, ja 80 vain ohjaa eteenpäin; SSH pelkästään lähiverkosta.` |

---

# Part 2 — Cut the filler

The rule: the voice stays, but every line has to carry a fact too. Nothing here is
cut for being playful — only for saying nothing.

## 2.1 `stack.intro` — stop restating the hero

**Home content → Stack → Intro.** Currently the fourth restatement of "I build
every layer myself". Keep the two things in it that *are* content: the reading
direction, and the managed-platform contrast.

**English**

| | Value |
|---|---|
| Now | `Instead of reaching for a managed platform, I built the whole pipeline myself — everything a professional production environment has, running on a mini-PC in my living room. Read it bottom to top.` |
| Change to | `No managed platform, no cloud console — every layer below is one I set up myself and keep running, on a mini-PC under the TV. Read it bottom to top.` |

**Suomi**

| | Value |
|---|---|
| Now | `Hallinnoidun pilvialustan sijaan rakensin myös alustani itse — kaiken, mitä ammattimaisessa tuotantoympäristössä on, pyörimään mini-PC:llä oman TV-tasoni alla. Lue alhaalta ylös.` |
| Change to | `Ei hallinnoitua pilvialustaa, ei pilvikonsolia — jokainen alla oleva kerros on itse pystytetty ja itse ylläpidetty, TV-tason alla nököttävällä mini-PC:llä. Lue alhaalta ylös.` |

## 2.2 `stack.footnote` — 45 words down to one line

**Home content → Stack → Footnote.** The idea inside it is real and worth keeping:
self-hosting raises the stakes, which is *why* the choices are what they are. It
just doesn't need a paragraph, and it shouldn't restate the intro directly above it.

Drop the `//` prefix. It was one of two on the page; the other one is being deleted
in code, and one left alone reads as a tic rather than a convention.

**English**

| | Value |
|---|---|
| Now | `// Because everything runs on my own machine, in my own home network, it has been even more important to understand what I am doing and why. This has guided me to make efficient and secure choices that do not depend on external services.` |
| Change to | `Running it at home means every mistake is mine to fix at 2am — which is exactly why every choice up there is one I can explain.` |

**Suomi**

| | Value |
|---|---|
| Now | `// Koska kaikki pyörii omalla koneella, omassa kotiverkossa, on ollut entistä tärkeämpää ymmärtää mitä teen ja miksi. Tämä on ohjannut tekemään tehokkaita ja tietoturvallisia ratkaisuja, jotka eivät ole riippuvaisia ulkoisista palveluista.` |
| Change to | `Kun kaikki pyörii kotona, jokainen virhe on oma korjattava kello kahdelta yöllä — juuri siksi jokainen ylläolevista valinnoista on sellainen, jonka osaan perustella.` |

## 2.3 `footer.blurb` — give it its own job

**Home content → Footer → Blurb.** Today it is a near-verbatim copy of
`home.metaDescription` and the sixth restatement of the hero thesis. Let it place
you geographically and land the one fact the rest of the page only asserts.

**English**

| | Value |
|---|---|
| Now | `Konsta Janhunen — full-stack & integration developer who likes to know how things work. From the bottom to the top of the stack.` |
| Change to | `Konsta Janhunen — full-stack & integration developer in Vantaa, Finland. Everything you just scrolled through is served from a mini-PC in my living room.` |

**Suomi**

| | Value |
|---|---|
| Now | `Konsta Janhunen — full-stack- ja integraatiokehittäjä, joka haluaa tietää miten asiat toimivat. Pinon pohjalta aina sen huipulle asti.` |
| Change to | `Konsta Janhunen — full-stack- ja integraatiokehittäjä Vantaalta. Kaiken minkä juuri selasit tarjoilee olohuoneen mini-PC.` |

## 2.4 Not touched, deliberately

- **`hero.taglines`** — the page's personality, and not the problem. Untouched.
- **`footer.nuc`** ("All fine and dandy." / "Tässähän tää menettellööpi.") — string
  stays exactly as it is. It gets a live uptime figure attached next to it in code
  (companion plan, workstream D), which turns the joke into the only *demonstrated*
  claim on the page instead of the only empty one.
- **`hero.eyebrow`**, **`hero.titleLine2`**, **`hero.body`** — the thesis is
  allowed to live here. It's the four *other* copies of it that go.

---

# Part 3 — Shorten the remaining stack rows

Same section, purely for height. Each of these is currently two lines at desktop
width and becomes one. No factual change — L1, L3 and L6 are handled in Part 1.

**L7 — Käyttöliittymä / Frontend**

| | Value |
|---|---|
| Now (EN) | `Nuxt 3 SSG/SPA, i18n, dark/light, accessibility baked in — what you are looking at.` |
| Now (FI) | `Nuxt 3 SSG/SPA, monikielisyys, tumma/vaalea, saavutettavuus sisäänrakennettuna — tämä, mitä luet ja näet.` |
| Change to (EN) | `Nuxt 3 static build, EN/FI, dark/light, accessible — this page.` |
| Change to (FI) | `Nuxt 3 -staattinen build, EN/FI, tumma/vaalea, saavutettava — tämä sivu.` |

**L5 — Toimitus / CI/CD**

| | Value |
|---|---|
| Now (EN) | `Automatic build, test and deploy pipeline — push to live only with the full suite green.` |
| Now (FI) | `Automaattinen käännös-, testaus- ja julkaisuputki — tuotantoon sysäys vain, kun koko testipatteri on vihreä.` |
| Change to (EN) | `Push to main → CI in parallel → webhook deploy. Red suite, no deploy.` |
| Change to (FI) | `Push mainiin → CI rinnakkain → webhook julkaisee. Punainen testisarja, ei julkaisua.` |

**L4 — Laatu / Testisarja**

| | Value |
|---|---|
| Now (EN) | `Unit, integration and end-to-end (Playwright) coverage across every level.` |
| Now (FI) | `Yksikkö-, integraatio- ja end-to-end-kattavuus (Playwright) joka tasolla.` |
| Change to (EN) | `pytest, Vitest and Playwright — unit, integration and end-to-end.` |
| Change to (FI) | `pytest, Vitest ja Playwright — yksikkö-, integraatio- ja end-to-end-testit.` |

**L2 — Alusta / Reititys & kontit**

| | Value |
|---|---|
| Now (EN) | `Nginx reverse proxy, multi-container setup, iptables firewall on Red Hat Linux.` |
| Now (FI) | `Nginx-käänteisproxy, monen kontin kokoonpano, iptables-palomuuri Red Hat Linuxilla.` |
| Change to (EN) | `nginx reverse proxy and TLS, a container per service, iptables firewall on RHEL 9.` |
| Change to (FI) | `nginx käänteisproxynä ja TLS, kontti per palvelu, iptables-palomuuri RHEL 9:llä.` |

> **No counts.** Earlier drafts said "seven containers" and gave test totals. Both
> rot the moment a service or a suite is added, and this repo has already had to
> strip rotting counts out of its docs once. Keep these qualitative.

---

# Part 4 — Small stuff

## 4.1 Trailing space in the Finnish `/dog` description

**Projects → /dog → Suomi → Description.** Ends `…haettu Showlink-palvelusta. `
with a trailing space. Cursor to the very end, delete one character. English is fine.

## 4.2 Copyright year — now unblocked

**Home content → Footer → Copyright line**, both locales.

The code half shipped: `HomeFooter.vue` already interpolates `{ year }`. The
2026-08-09 plan's warning to wait no longer applies.

| | Value |
|---|---|
| Now | `© 2026 Konsta Janhunen` |
| Change to | `© {year} Konsta Janhunen` |

After saving, confirm the footer shows `© 2026 Konsta Janhunen` and not a literal
`{year}`. Then the field never needs touching again.

---

# Part 5 — Project layer chips (new field)

Each project now carries the stack layers it touches, shown as `L1`–`L7` chips in
the expanded card that link down to the stack table. **Projects → any project →
Stack layers**, a row of toggle buttons above the Hidden checkbox. Language-
independent, so there is one setting per project and no locale toggle.

They ship pre-filled with these, so there is nothing you *must* do here — adjust
only if you disagree:

| Project | Layers | Reasoning |
|---|---|---|
| Sanakenno | L4 L5 L6 L7 | App, its tests and its pipeline; it does not own the box |
| Sanakenno Admin tools | L6 L7 | A UI over the same backend |
| erez.ac | L1–L7 | Spans the whole table by design — that is the point of it |
| /dog | L6 L7 | Nuxt front, Flask/SQLite behind |

The spread is what makes the legend say something: if everything claimed every
layer, the chips would carry no information.

⚠️ These only appear once the schema change has been applied to the production
database — see the "Production procedure" in the companion plan. Until then the
field is absent and the chips do not render.

# Resolved — no edit needed

1. **LinkedIn URL** — `linkedin.com/in/konsta-janhunen-263832165` confirmed correct
   (2026-09-01). The footer connect link, the terminal's `about` and the JSON-LD
   `sameAs` all already use it. Nothing to change; the 2026-08-09 question is closed.
2. **`GPT` tag on Sanakenno Admin tools** — verified accurate. `scripts/pangram-review.ts`
   calls the OpenAI batch API with `gpt-5.4`. Flagging only because the 2026-08-09
   plan left it unchecked.

# Checklist

- [ ] 1.1 Sanakenno tech tags — EN
- [ ] 1.1 Sanakenno tech tags — FI
- [ ] 1.2 Stack L6 detail — EN
- [ ] 1.2 Stack L6 detail — FI
- [ ] 1.3 Stack L3 detail — EN
- [ ] 1.3 Stack L3 detail — FI
- [ ] 1.4 Sanakenno description, last sentence — EN
- [ ] 1.4 Sanakenno description, last sentence — FI
- [ ] 1.5 Stack L1 detail — EN
- [ ] 1.5 Stack L1 detail — FI
- [ ] 2.1 Stack intro — EN + FI
- [ ] 2.2 Stack footnote — EN + FI
- [ ] 2.3 Footer blurb — EN + FI
- [ ] 3 Stack L7, L5, L4, L2 details — EN + FI
- [ ] 4.1 `/dog` FI description trailing space
- [ ] 4.2 Copyright line — EN + FI, then verify the rendered year
- [ ] 5 Project layer chips — see Part 5 (no locale toggle needed)

# Verification

Load erez.ac in both languages and check the stack table top to bottom, the
expanded Sanakenno card, and the footer. The Home content editor badges unsaved
fields per group — a badge on a group you thought you finished means a field
didn't save.

No tests to run; none of this touches code. The next push to main bakes it into
the prerendered HTML.
