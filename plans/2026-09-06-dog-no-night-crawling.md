# No dog crawling at night

Status: shipped
Date: 2026-09-06

## Objective

Nothing fetches Showlink outside **08:00–21:00 Finnish local**. No dog show runs
at night, so every request made then is waste.

## Context

Three paths currently reach Showlink outside show hours.

**Finals overtime, 21:00–01:00.** Deliberate: `RESULT_FINALS_NIGHT_STOP_HOUR = 1`,
and `_in_finals_fetch_window` returns True for everything from the evening cutoff
to 01:00. It was added because finals publish roughly 21:00–23:30 and the old
21:00 cutoff stranded them.

**Index maintenance, 24/7.** Not deliberate: `crawl_index_once` has no clock check
at all, so the crawler re-indexes shows every 15 minutes right through the night.

**Show-list refresh, on request.** `_get_show_list` refreshes on a 30-minute TTL
and is reachable from `search.py`, so a visitor at 02:00 can trigger a fetch. The
web tier's `_show_list_cache` is per-process and separate from the crawler's.

Morning also opens at 06:00 (`RESULT_SHOW_MORNING_HOUR`), earlier than any show
starts.

This is independent of the crawler rework in
[2026-09-06-live-crawl-judge-queues.md](2026-09-06-live-crawl-judge-queues.md) and
needs no measurement, so it ships first.

## Approach

One window, applied everywhere: `08:00–21:00` Finnish local.

- `RESULT_SHOW_MORNING_HOUR` 6 → 8.
- Drop the overtime tail — remove `RESULT_FINALS_NIGHT_STOP_HOUR` and the
  after-hours branches of `_in_finals_fetch_window`, leaving one window that both
  the base availability check and the finals plan share.
- Gate `crawl_index_once` on the same window.
- Gate the Showlink refresh inside `_get_show_list`, not the call sites, so every
  caller including request paths is covered.

The window lives in one place and every path reads it from there. Today the same
hours are expressed three different ways, which is how the index pass ended up
with no check at all.

**Accepted cost.** Finals typed in at 21:30 are captured at 08:00 the next
morning instead of that night, so the /dog page shows a show without its BIS
overnight. That is display latency, not lost data: the next morning's pass is a
`rescue` pass, still inside the 2-day deadline, and it picks them up. A quiet
night is worth more than same-night finals.

**Known wart, resolved by the other plan.** A show that stops for the night still
owing its finals reads as concluded, because `is_live` is `availability.can_fetch`
and no badge is indistinguishable from settled history. That is already true today
at 21:00; this plan does not make it worse, and fixing it properly needs the settle
ladder. Not in scope here.

## Files to touch

- `app/dog_show/config.py` — morning hour 6 → 8; remove the night-stop constant.
- `app/dog_show/utils.py` — single shared fetch window;
  `_in_finals_fetch_window` collapses into it.
- `app/dog_show/crawler.py` — `crawl_index_once` returns early outside the window.
- `app/dog_show/shows.py` — `_get_show_list` refreshes from Showlink only inside
  the window.
- `docs/dog-show-browser.md`, `frontend/pages/dog/about-crawler.vue` — the public
  crawler description states 21:00–06:00; it becomes 21:00–08:00, and the
  overtime behaviour it describes goes away.
- `tests/test_dog.py` — see below.

## API / data shape

None. No schema change, no response shape change.

## Tests

- No path fetches outside 08:00–21:00: parametrise over the boundary hours
  (07:59, 08:00, 20:59, 21:00, 00:30, 03:00) for the result plan, the index pass
  and the show-list refresh.
- A show still owing finals at 21:00 stops fetching, and resumes on the next
  morning's rescue pass rather than being settled overnight.
- The existing overtime tests are removed with the behaviour, not adapted.

## Security considerations

- **New input vector?** No. This only removes fetches.
- **Exposes internal state?** No.
- **Weakens the network boundary?** No. Strictly less outbound traffic.

## Out of scope

- The settle ladder, judge queues, tiering and the finals probe — the other plan.
- The badge reading as concluded overnight (see above).
- Cadence changes inside the window; only the window itself moves here.

## Open questions

`_get_show_list` gated at night means a web process that restarts overnight has an
empty `_show_list_cache` and no way to fill it. `/dog` must still render — the
fallback should be the persisted shows in `dog.db` rather than a Showlink fetch.
Confirm during implementation that the read path can be served entirely from the
database.

## Revision 2026-09-06 — implemented

The open question is resolved: `_get_show_list` serves whatever it has cached,
however stale, outside the window, and falls back to **one** Showlink fetch when
the cache is empty. A web process that restarts overnight can still render
`/dog`; one request per process start is not polling. No dog.db read path was
needed.

Two things the plan implied but did not spell out, both now done:

- `_show_result_availability` applies the window to **past** shows too, not only
  live ones. Its live branch already folded the window in; leaving past shows
  open meant a visitor at 02:00 opening an uncached show queued a job the crawler
  then ran, which is the same night traffic by another route.
- The `overtime` phase went with the tail. It was reachable only after the
  evening cutoff, so keeping it would have left dead code and a dead TTL.

`tests/test_dog.py` gained an autouse `_dog_daytime_clock` fixture. Without it
every crawl test fails after 21:00, since past-show availability is now
clock-dependent — a suite that only passes before nine is not a suite. Tests that
are *about* the window take the `real_fetch_window` fixture to opt out.
