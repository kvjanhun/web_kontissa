# Plan: robust "show is finished" detection for live dog shows

Status: **IMPLEMENTED 2026-07-05** (award-structure terminal target + targeted
finals capture + overtime/rescue windows + scheduler & timezone fixes). Shipped
in `app/dog_show/finals.py` + `utils._result_live_plan` + `result_cache.py` +
`indexing.py` + `scripts/dog_crawl.py`, with the one-off recovery script
`scripts/dog_rescue_finals.py`. Backend + frontend suites green. The redesign
below is the as-built description.
Date: 2026-06-28, rewritten 2026-07-05 after the Oulu KV post-mortem
Owner: Konsta

## Why this plan exists

The live result cache must stop fast-polling a show *soon after the show truly
ends* — but not one second before. Two approaches have already failed:

1. **Inactivity timeout (the original).** Closed shows too early. Real shows have
   long lulls — between breed rings, and especially the gap between the last
   breed being judged and the **finals** (group/BIS) being published.
2. **Wait for Best in Show.** A single-breed **specialty** show has *no* BIS at
   all — its top award is BOB/ROP. "Wait for BIS" never fires for those.

Showlink exposes **no field** that says "results are final". The show's terminal
level must be inferred. The domain model (per Konsta, 2026-07-05):

> Dogs are graded breed by breed within each FCI group. When every breed in a
> group is judged, the **group winners (RYP)** are decided — no new written
> grades. After **all** groups have their winners, the **BIS** is chosen.
> Juniors and veterans usually have no separate group stage. **The show must
> not be concluded before ALL awards have been given.**

## Hard invariant (unchanged)

> A show is never allowed to settle (leave fast-polling) before its **terminal
> award for its show type** is captured, and the finals below that terminal have
> stopped changing.

Settling early = lost results. Polling a finished show a bit too long is cheap
and acceptable. When in doubt, keep polling — but always with a hard deadline
(see below), because the source data itself is sometimes incomplete.

---

## Post-mortem: Oulun Iloisen koiran KV (show 13786, 2026-07-04)

Single-day international all-breed show: 260 breeds, 1,987 result rows, all 10
FCI groups. Settled `complete` with **only group 9's finals**: `RYP-1..4` (group
9), `BIS JUN-1`, `BIS VET-3` — all on group-9 breeds' rows. Missing: 9 groups'
RYP, the entire main `BIS-1..4`, the rest of BIS JUN/VET. Evidence from the
prod `dog.db` copy (2026-07-05):

- Breed fetch timeline (`completed_breeds[*].updated_at`, EEST): 19 breeds at
  10–11, **207 breeds in the 15:00 hour**, 1 at 16, 3 at 20, then **exactly one
  30-breed finals sweep at 22:01:05–22:01:10** — and nothing ever again.
  The multi-hour gaps on a live show day (11→15, 16→20) show the crawler was
  not giving this show passes even while it was due every 120 s.
- `bis_detected_at = None`, `finals_post_bis_sweep_remaining = None`,
  `finals_sweep_cursor = 245/260`. The gates (`_show_expects_main_bis` → True,
  "keep polling until BIS-1") were all **correct** — the show never wrongly
  settled by TTL logic. It starved: no pass ran after 22:01 EEST, and the
  finals were published on Showlink after that.
- The next-day rescue (`_post_show_final_due_at`) never ran either (row
  `updated_at` unchanged through 13:54 EEST on 07-05).

### Why no passes ran when it mattered

Four interacting defects, all confirmed in code:

- **D1 — scheduler starvation by the queued-job interlock.**
  `scripts/dog_crawl.py:118`: if the queued-jobs pass attempted *any* job this
  cycle, the auto-recent pass (the only path that refreshes live shows' caches
  and runs finals sweeps) is skipped wholesale (`queued_job_active`). The web
  layer queues `live-list-refresh` jobs (limit 2, first-listed live shows)
  whenever users browse, so on busy weekends the auto pass is starved for
  hours. This matches 13786's fetch gaps.
- **D2 — rescue candidates rank last and the rescue is one-shot.**
  `_auto_result_cache_candidates` ranks live shows (`recency_rank -1`) above
  every past show; with `limit=2` a day-old show owing finals never gets a
  slot on a Sunday full of live shows. Worse, the rescue window
  (`_post_show_final_due_at`) is only *armed* on `show_date + 1`; if it fires
  it re-sweeps just 30 of 260 breeds, then advances `cached_at` past the due
  line and **disarms itself forever**. From `show_date + 2` nothing will ever
  re-fetch the show (the backfill, which would have, is archived).
- **D3 — blind finals sweep.** The 30-breed rotating sweep treats all 260
  breeds as equally likely to carry finals tokens. But the token-bearing rows
  are structurally identifiable: RYP tokens land on ROP dogs' rows within the
  group; `BIS-1..4` land **only on the ≤10 RYP-1 winners' breed pages**. The
  rotation spends its budget on pages that cannot contain what it's looking
  for. (This same defect, post-BIS, produced the earlier "Turku KV captured
  3 of 4 BIS" bug and the 9-of-10-RYP wounds below.)
- **D4 — timezone drift.** `_show_result_availability` is defined in Finnish
  wall-clock (default `_local_now()`), but the crawler paths pass
  `datetime.datetime.fromtimestamp(...)` — **UTC-naive in the container** — so
  the 06–21 window is evaluated as 06–21 UTC = 09:00–24:00 EEST there, while
  API paths evaluate it in EEST. The effective evening cutoff is accidental.
  (Ironically the +3 h drift is the only reason the 22:01 EEST sweep — which
  captured group 9 — ran at all.) `_post_show_final_due_at`'s "next day"
  likewise flips at 03:00 EEST.

### Damage measured across the whole store (Phase 0, executed 2026-07-05)

Query over all 674 `complete` caches: multi-group shows missing `RYP-1` in some
result-bearing group and/or missing `BIS-1`:

- **648 / 674 shows are structurally complete** — full RYP coverage + BIS-1
  (or single-group/specialty shapes that don't call for them).
- **15 multi-group specialty clusters** (erikoisnäyttelyt, WDS-circuit club
  shows, palveluskoiratapahtumat) have **BIS-1 with zero RYP tokens** — a real
  show type that crowns BIS directly with **no group stage**. Any design
  requiring RYP-per-group unconditionally would poll these forever.
- **6 shows have BIS-1 but one group's RYP-1 missing** (12786 Sawo 2024, 13386,
  13395, 13519, 13648, 13828) — the fixed one-rotation-after-BIS budget hole.
  Note 12786 was **backfilled from final pages**, so at least one of these is
  missing at the *source* — "all groups have RYP-1" can be unsatisfiable, which
  is why a hard deadline must exist.
- **Missing BIS-1 entirely:** 13786 (this post-mortem) and 13293 (Kokkola
  4-group part-show, 3/4 RYP, possibly source-incomplete). 13507 / 13758
  (multi-day, day 2 = 2026-07-05) and 13787 (single-day 2026-07-05) were
  **live during measurement** — not wounded yet, but they face the same
  evening-cutoff risk on 2026-07-05 night.

---

## The redesign: award-structure end decision + targeted finals capture

Replace the wall-clock end with a per-show **terminal target** derived from the
award structure, plus scheduler fixes so the gates actually receive fetches.

### 1. Terminal target per show class (adaptive, not guessed up front)

Evaluated continuously from the captured rows:

- **Base target for any multi-group show:** `BIS-1` captured.
- **Group-stage requirement activates on evidence:** once *any* RYP token is
  observed, additionally require `RYP-1` for **every FCI group that has
  result-bearing breeds**. (RYP precedes BIS in show order, so by the time BIS
  could appear, the presence/absence of a group stage is known. Specialty
  clusters — BIS with no RYP stage — never activate this and settle on BIS-1.)
- **Single-group shows:** same rule; Phase 0 data shows part-shows ("osa",
  FCI-subset) with a group stage do crown BIS-1, so the base target holds.
- **Single-breed specialties / no-finals shows:** terminal = entry completion
  (every result-bearing breed judged) — current behavior, unchanged.
- **Multi-day shows:** the target is evaluated show-wide; it can only be *met*
  on or after the final day (day-1 evenings keep the current overnight lull).

### 2. Stability confirmation (replaces the fixed one-rotation budget)

After the terminal target is met, run one full rotation over captured
result-bearing breeds; **any pass that adds or changes a finals row resets the
rotation**. Settle only when a full rotation adds nothing (and the show is past
its final day). This closes the BIS-4/late-RYP hole without reintroducing
early-close, because the terminal-target gate still holds underneath.

### 3. Targeted finals fetching (replaces the blind 30-breed rotation)

While the target is unmet, fetch only pages that can carry the missing tokens:

- **Missing-group RYP:** rotate only over breeds of groups still lacking
  `RYP-1`. The candidate set shrinks as each group's finals land (vs. 260
  static candidates today).
- **BIS-1..4:** once every expected group has `RYP-1`, fetch exactly the
  RYP-1 winners' breed pages (≤10, known precisely — BIS finalists are the
  group winners). For specialty clusters (no RYP), fall back to rotating over
  ROP-bearing breeds.
- **BIS JUN / BIS VET / BIS PEN:** not targetable a priori (candidates are
  every breed's class winners) — covered by the stability rotation in §2.

### 4. Polling schedule: overtime instead of cutoff

- 06:00 morning start unchanged; normal live cadence (120 s) unchanged.
- At 21:00 Finnish local, a show with an **unmet terminal target** enters
  **finals overtime**: passes continue at a reduced cadence (~10 min),
  fetching only the targeted sets from §3 (a handful of pages per pass, not
  breed crawling). Hard nightly stop at 01:00.
- **Rescue mode (day+1 and day+2):** while the target is unmet, the show stays
  *due* at a moderate cadence (~15 min) during fetch hours. Re-arming is
  driven by **target-unmet**, not by the current `cached_at < midnight`
  bookkeeping — a header write can no longer disarm it, and it isn't one-shot.
- **Hard deadline:** end of `show_date + 2` (Finnish). Past it, settle as
  `settled_incomplete` with a structured log
  (`dog_show_settled_incomplete`, show_id, missing groups, missing BIS) so it
  surfaces in Grafana instead of silently freezing. Needed because the source
  itself is sometimes incomplete (12786, 13293).

### 5. Scheduler fixes (without these, gates never get fetches)

- **S1:** stop skipping the auto pass when queued jobs ran
  (`dog_crawl.py:118`); share the per-cycle budget instead (queued first, auto
  fills the remaining limit).
- **S2:** rank finals-owing shows (overtime/rescue, target unmet) at least
  equal to live shows in `_auto_result_cache_candidates`, so a Sunday's live
  load can't starve Saturday's rescue. Their per-pass cost is tiny (§3).
- **S3:** all availability/deadline call sites pass Finnish-local datetimes
  (route through one `_local_now`-based helper); kill the UTC/EEST split.
- **S4 (hygiene):** non-live queued jobs stuck in `running` currently never go
  stale (`_result_job_stale_seconds_for_show` → None); give them a stale
  timeout so they can't linger.

### 6. Frontend

The meaning of "live" barely changes (overtime shows still read `Käynnissä` /
`Jatkuu`), but extract the `useDogBrowser.js` live/settled predicates into a
small unit-tested helper while touching this (carried over from the old plan's
Phase 2 / #5).

### Request-volume accounting (the point of the exercise)

For a 260-breed KV: breed capture is unchanged (~260 fetches). Finals capture
becomes *smaller and better aimed*: per-group sweeps shrink as groups land, the
BIS set is ≤10 exact pages, and overtime runs at 10-minute cadence with only
those sets. Small shows and specialties settle on structure — often *earlier*
than the current wall clock. Big KVs poll a bit later into the evening, which
is exactly the trade the invariant demands.

---

## Immediate mitigations (before the redesign ships)

1. **This weekend's finals are recoverable now.** Showlink already serves the
   full finals for 13786; 13507 / 13758 / 13787 conclude 2026-07-05 evening and
   will be missing their finals by morning for the same reason. A targeted
   `crawl_result_cache_for_show(show_id, force=True)` per show (pattern:
   `scripts/dog_recrawl_pre_phase_c.py`, including its "only force if Showlink
   still serves result-bearing breeds" guard) re-captures everything.
2. **One-off wounded-shows rescue script** for the older damage-table entries
   (12786, 13293, 13386, 13395, 13519, 13648, 13828): force re-crawl where
   Showlink still serves the show; shows whose source genuinely lacks a token
   simply come back unchanged. Not part of the crawler loop.

## Test matrix (must pass before merge)

Build fixtures from real Phase 0 shows:

- single-breed specialty (no BIS) — settles after its `ROP`s, not before, not
  "never";
- **specialty cluster (multi-group, no RYP stage)** — settles on `BIS-1`
  without waiting for RYP (new, from Phase 0);
- all-breed single-day — does not settle until every result-bearing group has
  `RYP-1`, then `BIS-1`, then a clean stability rotation;
- **the 13786 scenario** — finals published 22:00–23:30 local with one group
  captured before 21:00: overtime captures the rest the same evening; if the
  crawler is down all evening, rescue mode captures them next morning; a
  header-only write does not disarm rescue (new);
- a show that publishes `BIS-4`/late `RYP` minutes after `BIS-1` — stability
  rotation resets and captures all (the Turku-KV failure);
- all-breed multi-day — stays live across the nightly gap; day-1 finals are
  captured; target only satisfiable after the final day;
- a long mid-show lull — does **not** settle early;
- **source-incomplete show** — one group's RYP never appears: settles
  `settled_incomplete` at the deadline with the structured log (new);
- **scheduler** — auto pass still refreshes a finals-owing show in a cycle
  where queued jobs ran; a rescue candidate is not starved by two live shows
  (new).

## Decision gates

- **Sign-off on this redesign** (this document) — then implement behind the
  test matrix; ships to `main` only with the full gauntlet green (auto-deploy).
- The immediate mitigations (§ above) can run independently of sign-off; the
  weekend shows should be rescued before Showlink ages them out.

## Out of scope

- Changing how individual breed results are fetched/parsed.
- Any retention/eviction of historical rows (permanent store — never evict).
- Re-instating the archived `--backfill` (the rescue script is separate and
  targeted).
