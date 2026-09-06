# Live crawl: judge-queue targeting and quiescence settling

Status: shipped
Date: 2026-09-06

## Objective

Two goals, in tension, and the current design serves neither well:

1. **Lighten the live probe load** — spend requests where data is actually
   changing, not on pages that cannot have changed.
2. **Never terminate a show too early** — no show settles while the source is
   still moving, including late corrections typed in after the ring has passed.

## Context

Show 14014 (06.09.2026 Suhmuran Santra, 96 breeds, 5 FCI groups) failed both goals
at once.

**Wrong data.** Its `BIS-1` was never fetched. `candidate_breed_keys` targets the
ROP pages of groups still missing an RYP-1, so it never re-read `8:121`
(fieldspanieli), where `BIS-1` actually landed. And group 6 *cannot* have an
RYP-1 — the show ran a combined **FCI 5/6** ring — so
`finals._expected_result_groups`, which derives one expected RYP-1 per FCI group
from the breed index, made `target_met` unreachable by construction. Separately,
29 of 96 breeds froze without a bare `ROP`, because `_breed_capture_is_settled`
accepts `result_count >= entry_count` as final and Showlink publishes class rows
before the honour roll. Two of those frozen pages were the missing RYP-1 winners.

**Wasted load.** `finals_hunt_active` stays true until the terminal is confirmed,
and each pass then re-fetches up to `RESULT_FINALS_SWEEP_BREED_LIMIT` (30) breed
pages every `RESULT_CACHE_LIVE_TTL` (120s) — for hours after judging ends, then
across two more days of rescue passes, all aimed at pages that structurally
cannot hold the answer.

The 2-day `RESULT_SETTLE_DEADLINE_DAYS` backstop still terminates the show, so
this is not a hang. It is wasted traffic plus a permanently wrong cache.

## Approach

Stop predicting the terminal award. Poll what is cheap, fetch what is likely to
have changed, and settle on observed quiescence.

### Two tiers

Detection and capture are currently the same operation — we learn whether
anything moved *by* re-fetching breed pages, which is why the two goals trade off
so badly. Split them:

- *Cheap tier, every pass:* the group breed-list pages (one per FCI group, or the
  `R=R` aggregate) and, when the nav advertises them, `R=RYP` and `R=BIS`. Cost
  scales with group count, not breed count.
- *Expensive tier, targeted:* breed pages, chosen from what the cheap tier says.

The breed-list row carries only name, entry count and a binary check icon, so it
cannot show progress inside a ring — but it is an exact gate for *which breeds
have started*, which is what bounds the expensive tier.

**The cheap tier already exists.** `crawl_index_once` fetches exactly these pages
— landing plus one per FCI group — to maintain the breed index, so this is not new
fetching machinery.

What it needs is separating the three jobs it currently runs on one budget
(`--limit 6` every 15 minutes) and one cadence:

- *Discovery* — new shows appearing in the list. Stays frequent; it is nearly
  free, since the list is one fetch and a genuinely new show is rare.
- *Recent refresh* — re-reading breed lists across the 38-day window. Can be
  slower; entry counts drift over weeks, not minutes.
- *Live cheap tier* — the same pages for a show happening today. Needs to be much
  faster than 15 minutes, which is the one thing the current flat cadence cannot
  give.

All three stop at night.

### Judge queues set priority — never completion

A judge judges one breed, finishes it, and moves to the next; there are no
exceptions in how shows actually run. We already store the assignment on
`dog_breed.judge`. 14014 had 96 breeds and **10 judges**, so at most ~10 breeds
can be moving at any moment. The partition costs nothing to build: a breed's judge
arrives on the fetch that captures it, which we had to make anyway.

The critical constraint: results are entered by club secretaries, so the *data*
does not always follow the ring. A row can be registered well after its breed's
ring finished. Therefore **a judge advancing to their next breed is a priority
signal only, and never evidence that the previous breed is complete.** Completion
stays a property of the breed's own page — honour roll, row count, stability.

That gives three tiers of attention, and nothing is ever sealed while the show is
live:

| Tier | Membership | Cadence |
|---|---|---|
| Hot | each judge's first incomplete breed (~1 per judge) | fast |
| Warm | started, captured, not yet provably complete | rotating |
| Cool | looks complete, show still live | slow full sweep |

The cool sweep is what protects goal 2 against late entry, and it is cheap: one
pass over every breed per hour is ~96 requests/hour here, ~275 for a national.

Where the queue misfires — judge not yet known, a ring out of programme order —
per-breed adaptive backoff is the fallback: a breed whose rows grew since last
fetch stays hot, one static across several fetches cools off. That needs no judge
and no schedule.

### The finals probe replaces the finals sweep

`R=RYP` and `R=BIS` are a direct view of the finals, name each winner with their
breed, and expose the real ring structure (`FCI 5/6` as a single heading). They
answer "have the finals landed" in 2 requests instead of 30 guesses, and turn
"which breed pages need re-reading" into an exact list — any breed named there
whose cached rows lack the matching token. This alone fixes the 14014 BIS loss and
the combined-ring case. Their absence is information too: 13914
(Pyreneittenmastiffi) advertises neither, because it awards no finals at all.

### Settle on structural completion, confirmed by quiescence

Quiescence cannot be the primary signal: shows take lunch breaks, and 30–60
minutes of silence mid-show is normal. So silence only ever *confirms* a
conclusion something else already reached. The settle ladder, in order:

1. **Finals published.** The `R=BIS` page exists and its Best-in-show section is
   filled. Assume the nav links appear only once the finals exist (see
   observation plan) — which makes the link's *appearance* a positive terminal
   signal rather than something to poll blindly, and its absence meaningful.
2. **Nothing left to judge.** Every breed carries a check icon and every checked
   breed is complete. This is what a lunch break fails: mid-show there are always
   breeds unstarted or mid-ring, so a quiet hour cannot satisfy it.
3. **Quiescence confirms.** ~15 minutes of an unchanged cheap-tier fingerprint on
   top of 1 or 2. A late row or correction changes the fingerprint and resets the
   window — goal 2. The window counts **observed** time only: minutes when we were
   not fetching are not evidence of anything, or the overnight gap would settle
   every show at the morning re-open.
4. **Deadline backstops.** The existing 2-day `settled_incomplete`, back to being
   a genuine backstop rather than the normal exit.

For a show that awards no finals at all (13914's shape), 2+3 carry it alone. No
assumption about groups, BIS, or show type survives, so combined rings,
group-only shows, puppy shows and single-breed specialties stop being special
cases.

The confirming machinery already exists (`terminal_fingerprint` /
`terminal_confirmed`) but `_mark_terminal_confirmation` resets it whenever
`target_met` is false, so observed stability can never accumulate on its own.
Ungate it and re-point it at the ladder above.

### Night stop (separate plan)

The fetch window moves to a hard 08:00–21:00 in
[2026-09-06-dog-no-night-crawling.md](2026-09-06-dog-no-night-crawling.md), which
ships first and independently. Two things here depend on it: the quiescence window
must count observed time (step 3 above), and the badge must stop reading
"concluded" for a show that merely stopped for the night.

### The badge follows the ladder, not the fetch window

`_compute_show_stats` sets `is_live` from `availability.can_fetch`, so the badge
disappears the moment the fetch window closes and the show reads as concluded.
Observed on 14014: badge gone at 21:00, crawl pass at 21:08 — the UI called it
finished while the crawler was still hunting.

With the night stop this stops being a disagreement and becomes a plain lie: at
21:00 a show still owing its finals is neither live nor concluded, and "no badge"
is indistinguishable from settled history. `is_live` should derive from the settle
ladder, and a show that has stopped for the night without concluding needs its own
state — the results on the page are real but not final, and the reader should be
told that rather than left to assume the show ended that way.

`is_paused` ("Jatkuu") already carries almost this meaning for the multi-day
nightly lull; the natural move is to widen it to cover any overnight hold rather
than invent a fourth state.

### Breed completeness becomes provisional

`result_count >= entry_count` without a bare `ROP` should mean "stop fast-polling,
stay eligible for re-check", not "never read again". The arm cannot simply be
deleted: all six single-entry breeds in 14014 genuinely have an empty honour roll.
Promote to final on `ROP`, or on full rows unchanged across two fetches.

### Where the load actually goes

Honest accounting, since the win is uneven. *Judging hours:* comparable budget,
far better aimed — up-to-48 blind re-checks per pass become ~10 hot fetches on
pages actually being judged, so the same money buys faster results. *After
judging:* the large saving — 30 pages every 120s for hours plus two days of
rescue becomes 2 probe pages per pass and an exact re-fetch list when the probe
moves. *After the show:* it ends minutes after it is genuinely over, not at a
2-day deadline.

### Alternatives rejected

Demand-driven refresh — the frontend fetches whole-show results, so per-breed
demand is not visible, and the goal is the whole show live anyway.
Schedule-driven priority — Showlink publishes no ring times. A cheap whole-show
change probe — no page exposes progress or an updated-at timestamp.

## Prerequisite: measure first

Every cadence number here is a guess, and shows vary too much to guess well. The
observation run in [2026-09-06-dog-live-observation.md](2026-09-06-dog-live-observation.md)
ships and runs first, next show weekend; its seven questions fix the windows,
budgets and the step-1 assumption below. Nothing in this plan starts before those
results are in.

## Files to touch

- `app/dog_show/finals.py` — read ring structure from the RYP page instead of
  deriving expected RYP-1s per group; reconcile winners to breed keys.
- `app/dog_show/parsers.py` — parse the `R=RYP` and `R=BIS` pages;
  `_breed_list_targets_from_soup` currently discards both link values.
- `app/dog_show/result_cache.py` — two-tier pass; judge queues, tiering and
  backoff replace `_finals_resweep_breeds`; provisional
  `_breed_capture_is_settled`.
- `app/dog_show/utils.py` — `_terminal_status` / `_result_live_plan` settle on
  the ladder, with `target_met` demoted to accelerator.
- `app/dog_show/indexing.py` — `is_live` from the plan phase, not
  `availability.can_fetch`; a distinct state for overtime/rescue.
- `app/dog_show/config.py` — probe cadence, tier budgets, backoff bounds,
  quiescence window.
- `app/dog_show/crawler.py` — split the index pass's three cadences (discovery,
  recent refresh, live cheap tier).
- `docs/dog-show-browser.md`, `frontend/pages/dog/about-crawler.vue` — the public
  crawler description changes materially.
- `tests/test_dog.py` — see below.

## API / data shape

No schema change. Per-breed tier/backoff state and probe fingerprints live in the
`dog_result_cache.meta` JSON blob, which exists precisely so live-cache fields can
evolve without migrations. `dog_breed.judge` already holds the partition. No
`/api/dog/*` response shape changes.

## Tests

- `finals.py` is pure — TDD it. Fixtures for a combined `FCI 5/6` ring, a
  group-only show with no BIS, a specialty with BIS but no RYP page, and a show
  with neither (13914's shape).
- Tier selection and adaptive backoff: pure selection functions over a synthetic
  doc, asserting the chosen breed set per pass and that a static breed cools off.
- **Late entry:** a row appearing on an already-complete breed after its judge has
  advanced is still captured, and resets quiescence. This is goal 2's regression
  test.
- `_breed_capture_is_settled`: full rows without `ROP` is provisional on the first
  observation and final on the second unchanged one; a single-entry breed still
  settles.
- Quiescence settling: a show whose finals never publish still settles; a late
  `BIS-2` resets the confirmation.
- Badge: a show still owing finals after 21:00 does not read as concluded.
- Night: a show does not settle at the morning re-open purely because the night
  was quiet (the window itself is covered by the night-stop plan).
- Page-shape regressions for the two new page types, per `app/dog_show/CLAUDE.md`.
- Replay 14014 as a fixture — it must end with `BIS-1` on `8:121` and settle.

## Security considerations

- **New input vector?** Two new Showlink page shapes parsed by BeautifulSoup, same
  trust boundary and same parsing path as the existing breed pages. Winner names
  are stored and rendered through the existing escaped result path; no new sink.
- **Exposes internal state?** No. No response shape changes; judge, tier and
  backoff state stay server-side in `meta`.
- **Weakens the network boundary?** No. Same host, same `_SESSION`, same
  `REQUEST_HEADERS`, no new port or origin.

## Out of scope

- Repairing already-settled historical shows. `scripts/dog_rescue_finals.py`
  covers that and should be run for 14014 once this ships — note it will need its
  selector updated, since the current `_owes_finals` inherits the same
  one-RYP-1-per-group assumption being removed here.
- Changing the `/dog` frontend beyond the crawler description.
- The `RESULT_SETTLE_DEADLINE_DAYS` backstop itself.

## Open questions

All of them are measurements, not design choices, and the observation plan
covers them.

The one assumption worth naming: the ladder's step 1 treats the `R=BIS` link's
appearance as meaningful, which is only sound if Showlink hides it until the
finals exist. That is question 1, and it is very likely why the current design
never used those pages. If it turns out false, step 1 degrades to polling the
page for content — slightly more traffic, no change to steps 2–4.

## Revision 2026-09-06 — implemented ahead of the measurement

Built at the user's instruction before the observation run, so **the cadence
numbers in it are still the guesses this plan said to measure first**: the
15-minute quiescence window, the tier budgets, the probe TTL, the static-fetch
backoff. All are single constants in `config.py` with environment overrides, so
next weekend's run retunes them without touching the design. Question 1 — whether
the nav advertises the finals pages before those finals exist — turned out not to
gate anything: the probe fetches both pages unconditionally, so link appearance
is never load-bearing. It stays worth measuring for the cadence, not the design.

What the real pages settled, verified against show 14014:

- **The page shape.** One `table.tulostaulukko`, `tr.otsikko` section headings
  carrying the ring and its judge, then up to four placement rows of
  `place | breed | dog`. The dog link carries the Kennelliitto registration
  number, so winners reconcile to captured rows by `reg_id` rather than by name.
- **The combined ring is visible and nothing else sees it.** 14014's RYP page has
  four sections for five groups — `FCI 5/6` is one heading with one RYP-1.
- **The breeder-group final places a kennel, not a dog.** It has no link, no
  registration, and no token on any breed row — confirmed against the show's
  whole captured cache, which carries `RYP-n`, `BIS JUN-n` and `BIS VET-n` and
  nothing else. A placement with no reg id therefore counts as published but
  never creates a re-fetch obligation; demanding a token for it would have
  re-fetched that breed for the life of the show.
- **The exact re-fetch list.** Against 14014's real cache the probe turns 43
  blindly-guessed breed pages — none of which could hold the answer — into 13,
  including `8:121`, where the lost `BIS-1` actually is.

Design points that firmed up while building:

- `finals.probe_state` distinguishes "the pages say there are no finals" from
  "we could not read the pages". Only a probe that actually returned a page
  counts as seen; a failed one falls back to the structural rules, because those
  two must never look alike.
- The breed-ring predicates (`_breed_capture_is_settled` and friends) and
  `parse_reg_id` moved into `finals.py`. Rung 2 of the ladder needs them from
  `utils`, and `utils` imports `finals`, so the leaf is the only place one copy
  can live. `result_cache` re-exports them under their existing names.
- The badge is derived from `show_state` plus `_show_live_phase` rather than a
  new fourth state: `show_state` is already the ladder's answer, so a show that
  has not settled always carries a badge, and `Jatkuu` widened to cover any hold
  it has not concluded from.

Still outstanding: `scripts/dog_rescue_finals.py`'s `_owes_finals` selector, as
the plan noted. It reads `finals.analyze`, which falls back to the old structural
rule for settled history (no probe stored), so it will keep re-selecting
combined-ring shows. Running it against 14014 needs that fixed first.

## Revision 2026-09-07 — provisional was too strong

Deployed, and two things broke, both from one error: the plan said full rows
without `ROP` should mean "stop fast-polling, stay eligible for re-check", and
the implementation made it mean "not finished". Those are not the same claim, and
the difference showed up in the two places that ask whether a *show* is done and
whether a *capture* is worth repairing.

- **Shows 14014 and 13768 read `Jatkuu` after concluding with every result in
  hand.** Ten of 14014's 96 breeds and 29 of 13768's 237 hold their whole entry
  with no honour roll — single-entry and tiny breeds genuinely never get one. Rung
  2 required every capture to be *final*, so nothing could promote them and the
  show could never settle.
- **The heal pass selected most of the database.** It selects breeds failing the
  settled test, which now included every full-rows capture in all of history —
  and in settled history nothing can ever promote them, because the second fetch
  that writes `rows_confirmed_at` only comes from a live crawl.

The fix is a third predicate rather than a weaker one. `_breed_capture_is_partial`
— no `ROP` *and* fewer rows than entries — is the only state that means a ring was
read mid-judging. Rung 2 and the heal pass both ask that instead. Provisional
stays exactly what it was for the live tiering: re-read once more while the show
runs, promoted by an agreeing fetch, and never a reason to call a finished show
unfinished or to re-crawl history.

`_unsettled_capture_breeds` gained `mid_ring_only` for the heal path — narrowing
only the ops script's show list was not enough, since the heal crawl re-selects
breeds itself.
