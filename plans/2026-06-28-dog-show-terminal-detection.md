# Plan: robust "show is finished" detection for live dog shows

Status: **investigation-first, awaiting sign-off**
Date: 2026-06-28
Owner: Konsta

## Why this plan exists

The live result cache must stop fast-polling a show *soon after the show truly
ends* — but not one second before. Two approaches have already failed:

1. **Inactivity timeout (the original).** Closed shows too early. Real shows have
   long lulls — between breed rings, and especially the gap between the last
   breed being judged and the **finals** (group/BIS) being published. A timeout
   fires in that gap and strands the finals.
2. **Wait for Best in Show.** A single-breed **specialty** show has *no* BIS at
   all — its top award is BOB/ROP. "Wait for BIS" never fires for those, so they
   poll forever.

Showlink exposes **no field** that says "this show will / will not crown a Best
in Show," or "results are final." So the current code *infers* the show's
terminal level. That inference is necessary, not idle guessing. This plan does
**not** throw it away — it tries to make it more reliable and the capture
afterwards less fragile.

## Hard invariant (must hold for every candidate design)

> A show is never allowed to settle (leave fast-polling) before its **terminal
> award for its show type** is captured, and the finals below that terminal have
> stopped changing.

Settling early = lost results = the failure we are fixing. Polling a finished
show a bit too long is cheap and acceptable. When in doubt, keep polling.

## What the code does today (so we change it with eyes open)

- `indexing._show_expects_main_bis(show_id, doc)` — decides a show will crown a
  main BIS if its indexed breeds span **≥2 FCI groups**, OR the cache already
  shows show-wide finals tokens (`RYP`, `BIS JUN`, `BIS VET`, `BIS PEN`).
- `utils._result_doc_has_main_bis(doc)` — true once a `BIS-1` award token exists.
- Settle gates (`result_cache._result_cache_ttl_for_show`,
  `indexing._compute_show_stats_from_index`):
  - all-breed (expects BIS): stay live until `BIS-1` captured + grace.
  - specialty (no BIS expected): settle on **entry completion** (all breeds
    judged) + grace.
- Finals capture (`result_cache._finals_resweep_breeds` +
  `finals_post_bis_sweep_remaining`): after `BIS-1` lands, re-check a rotating
  chunk of already-captured winning breeds for **exactly one more full rotation**,
  then settle.

### Known failure modes of the current code (to reproduce and then beat)

- **Fixed "one rotation after BIS" budget is too rigid.** BIS-1..4 and a late
  `RYP` sit on *different* winning breeds' rows; one rotation can miss the ones
  it hasn't reached (documented: "Turku KV captured only 3 of 4 BIS").
- **Multi-day shows.** A later-day BIS published after the budget is spent is
  missed until a forced/backfill re-crawl (documented caveat).
- **The ≥2-FCI-group heuristic is unverified against real data** — we don't
  actually know its false-positive / false-negative rate across show types.

## Phase 0 — Ground truth from `dog.db` (no new crawling)

`dog.db` is a permanent store already holding **full historical results for
every show type**. The ground truth is sitting in it. Write a read-only analysis
script (`scripts/dog_analyze_terminals.py`, one-off, not in the crawler loop)
that, for every **complete** result doc, reports:

- show id, date, breed count, **distinct FCI groups** present;
- the full set of show-wide finals tokens actually present at the end
  (`BIS-1..4`, `RYP-1..`, `BIS JUN`, `BIS VET`, `BIS PEN`, and per-breed
  `ROP`/`VSP`/`BOB`);
- a derived **show-type class**: all-breed (multi-group), group show
  (single group, multiple breeds), single-breed specialty, specialty cluster.

Deliverable: a table answering empirically —

1. Does "≥2 FCI groups" cleanly predict "ends in `BIS-1`"? What are the misses?
2. What is the **actual terminal award** for each class? (Confirm specialties top
   out at `ROP`/`VSP` and never produce `BIS-1`; check whether single-group shows
   top out at `RYP`/`BIG` rather than `BIS`.)
3. Are there show types we haven't accounted for at all?

This phase is cheap, offline, and decides whether the inference needs replacing
or only strengthening. **No production behavior changes in Phase 0.**

## Phase 1 — Evaluate candidate signals against the Phase 0 data

Score each candidate on the Phase 0 corpus (and a handful of live shows):

- **C1 — Per-show terminal target.** From the (validated) show type, define the
  award set the show must reach before it may settle: all-breed → `BIS-1`;
  group → `RYP-1`/`BIG-1`; specialty → every indexed breed has its `ROP`. Settle
  only when the target set is present.
- **C2 — Page-shape signal instead of (or alongside) FCI-group counting.** The
  landing page already distinguishes shapes the parser handles (numeric `R=1..10`
  group links → all-breed; `R=R` aggregate; bare `rotulistatable` → specialty).
  This may classify the show **earlier and more reliably** than counting indexed
  breeds, which are incomplete early in the day. Measure agreement with C1's
  ground-truth class.
- **C3 — "Sweep winners until stable" replaces the fixed one-rotation budget.**
  After the terminal award appears, keep re-checking captured winning breeds each
  pass; reset a quiet-timer whenever a sweep adds/changes a finals row; settle
  only after a **full rotation adds nothing new** AND the show is past its final
  day. This directly removes the BIS-4-missed and multi-day holes without
  reintroducing early-close, because the terminal-captured gate (C1) still holds.
- **C4 — Showlink-native completion marker (low confidence).** While gathering
  ground truth, check whether any page text/state means "results final / show
  ended." If one exists and is reliable, it dominates everything above. If not,
  drop this.

## Phase 2 — Design + implement the chosen approach (separate sign-off)

Likely shape, pending Phase 0/1 results: **keep the show-type inference but base
it on the best signal (C1 + maybe C2), and replace the rigid finals budget with
"capture until stable after the terminal" (C3).** Collapse the BIS-grace and
entry-completion-grace timers into the single terminal-captured-and-stable gate.
This is also where **#5** lands: extract the frontend `useDogBrowser.js`
live/settled predicates and URL-state sync into a small unit-tested helper, since
the meaning of "live" changes on both ends.

### Test matrix (must pass before merge)

Build fixtures from real Phase 0 shows:

- single-breed specialty (no BIS) — settles after its `ROP`, not before, not
  "never";
- all-breed single-day — does not settle until `BIS-1` + finals stable;
- all-breed multi-day — stays live across the nightly gap; each day's finals are
  captured; settles only after the final day;
- a show that publishes `BIS-4`/late `RYP` minutes after `BIS-1` — all captured
  (the current Turku-KV failure);
- a long mid-show lull — does **not** settle early (the original-timeout
  failure);
- overnight quiet window — served stale, not settled.

## Decision gates

- After **Phase 0**: confirm whether the ≥2-group heuristic survives or must be
  replaced; pick the signal. (Sign-off.)
- After **Phase 1**: lock the candidate design. (Sign-off.)
- **Phase 2** implements behind the test matrix; ships to `main` only with the
  full gauntlet green (auto-deploy).

## Out of scope

- Changing how individual breed results are fetched/parsed.
- Any retention/eviction of historical rows (permanent store — never evict).
