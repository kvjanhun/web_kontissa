# Live-show observation run

Status: shipped
Date: 2026-09-06

## Objective

Measure how Showlink actually behaves during a live show day, so the crawler
rework in [2026-09-06-live-crawl-judge-queues.md](2026-09-06-live-crawl-judge-queues.md)
is built on observation rather than on guessed cadences. Ships and runs first.

## Context

That plan's numbers — a ~15-minute quiescence window, per-tier fetch budgets, the
provisional window before a breed counts as complete — are all guesses. So is its
load-bearing assumption that Showlink hides the `R=RYP` / `R=BIS` nav links until
those finals exist.

Shows vary: organisers are volunteers working to their own plans, with Showlink as
the only common constraint, and results are entered by club secretaries who may
register a row well after its ring finished. Nothing measured on one show can be
assumed to generalise.

## Approach

A standalone read-only observer, run from the laptop, writing timestamped JSONL.
It never touches `dog.db` and is not part of the crawler loop.

Three sources per observed show:

- **Cheap Showlink pages** every 2 minutes: landing, each group breed list,
  `R=RYP`, `R=BIS`. High resolution is needed here because question 1 is about
  *when* a link first appears.
- **A rotating sample of breed pages** every 10 minutes: row counts and honour
  roll, to catch publication lag and late rows.
- **`erez.ac/api/dog/shows/<id>`** every 2 minutes: our own capture-side view,
  free and no Showlink load.

Same user-agent and request delay as the result crawler. Across all observed
shows this is roughly one extra crawler's worth of traffic.

Run against **at least three shows on the same day**, chosen for different shapes:
an all-breed national or KV, a group combo, and a single-breed specialty — plus a
puppy show if one runs. Question 7 is the whole point of running more than one.

## What to measure

| # | Question | Decides |
|---|---|---|
| 1 | Do the `R=RYP` / `R=BIS` nav links appear before their content exists? Record first appearance of each link vs. first non-empty section. | Whether link appearance is a terminal signal (settle ladder step 1) or the page must be polled for content. |
| 2 | How long between a breed's last class row and its `ROP`? | The provisional window in `_breed_capture_is_settled` — the bug that froze 29 breeds on show 14014. |
| 3 | Are a judge's breeds strictly sequential *in the data*, given late entry? | Whether judge-queue ordering is usable, or only the "~1 active breed per judge" bound. |
| 4 | Distribution of mid-show quiet gaps — how long is a lunch break really? | The ~15-minute confirming window. |
| 5 | Do rows ever appear after a breed looked complete, or after its judge advanced? | How slow the cool sweep can safely be. |
| 6 | Does the check icon ever appear late or retract? | Whether the cheap gate is trustworthy. |
| 7 | How much do concurrent shows differ on 1–6? | Which behaviours are universal and which need per-show handling. |

## Files to touch

- `scripts/dog_observe_live.py` — new. One-off ops tool, in the same family as
  `dog_rescue_finals.py` / `dog_heal_partial_breeds.py`; documented as not part of
  the crawler loop.
- `docs/dog-show-browser.md` — one line pointing at the tool.

## API / data shape

None. Read-only; output is JSONL on the laptop, nothing enters `dog.db`.

## Tests

Light — this is a throwaway measurement tool, not production behaviour. Parsing
helpers it shares with `parsers.py` are covered there. A dry-run mode that hits
each page type once and prints what it extracted is worth more than unit tests
here.

## Security considerations

- **New input vector?** No. Read-only fetches of the same Showlink pages the
  crawler already reads, plus our own public API. Output is a local file.
- **Exposes internal state?** No. Runs on the laptop, writes locally, publishes
  nothing.
- **Weakens the network boundary?** No. No host change, no new port or origin,
  nothing installed on the NUC.

## Out of scope

Any crawler behaviour change — that is the other plan, and it waits on these
results.

## Open questions

Whether one show day is enough, or whether question 3 (judge sequencing under
late entry) needs a second weekend to see a rarer failure. Decide after the run.
