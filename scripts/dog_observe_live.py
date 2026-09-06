#!/usr/bin/env python3
"""Read-only observer for a live dog show day.

Measures how Showlink actually behaves while a show is being judged, so the
crawler rework can be built on observation instead of guessed cadences. Writes
timestamped JSONL; analysis happens afterwards, off the recording.

The seven questions it exists to answer (see
plans/2026-09-06-dog-live-observation.md):

1. do the R=RYP / R=BIS nav links appear before their content exists?
2. how long between a breed's last class row and its ROP?
3. are a judge's breeds strictly sequential in the *data*, given late entry?
4. how long is a lunch break really?
5. do rows ever appear after a breed looked complete?
6. does the check icon ever appear late, or retract?
7. how much do concurrent shows differ on 1-6?

Question 7 is why it takes several --show ids: run it against shows of different
shapes (all-breed KV, group combo, single-breed specialty) on the same day.

Three sources per show, on independent cadences:

- cheap Showlink pages (landing, each FCI group breed list, R=RYP, R=BIS) every
  --cheap-interval, because question 1 is about *when* something first appears;
- a rotating sample of breed pages every --breed-interval, prioritising breeds
  that have started but shown no ROP yet (questions 2 and 5);
- our own erez.ac API every --cheap-interval, which is free and shows the
  capture side of the same moment.

Nothing here is part of the crawler loop. It runs from the laptop, never opens
dog.db, and only ever issues GETs. It uses the crawler's user-agent and request
delay so Showlink sees the same polite client it already knows.

    SECRET_KEY=dev python3 scripts/dog_observe_live.py --dry-run --show 14014
    SECRET_KEY=dev python3 scripts/dog_observe_live.py --list
    SECRET_KEY=dev python3 scripts/dog_observe_live.py \
        --show 14014 --show 13914 --show 14042 --out observations/2026-09-12.jsonl
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault("SECRET_KEY", "dog-observe-local-only")
os.environ.setdefault("DATABASE_URI", "sqlite://")
# Forced, not defaulted: this tool must never be able to reach the real dog.db,
# whatever the operator has exported. It reads Showlink and our public API only.
os.environ["DOG_DATABASE_URI"] = "sqlite://"

import requests  # noqa: E402

from app.dog_show.config import BASE_URL, REQUEST_HEADERS, REQUEST_TIMEOUT  # noqa: E402
from app.dog_show.parsers import (  # noqa: E402
    FINALS_TARGETS, _breed_list_targets_from_soup, _parse_breed_results,
    _parse_breeds_from_soup, _parse_finals_page, _parse_show_list,
)
# The crawler's own "is this ring finished?" rule. Imported rather than
# reimplemented: a measurement that disagreed with the code being measured would
# answer question 2 about the wrong thing.
from app.dog_show.result_cache import _breed_bob_awarded  # noqa: E402
from app.dog_show.showlink import _fetch_page, _source_url  # noqa: E402

DEFAULT_CHEAP_INTERVAL = 120
DEFAULT_BREED_INTERVAL = 600
DEFAULT_BREED_SAMPLE = 6
DEFAULT_REQUEST_DELAY = 0.4
DEFAULT_API_BASE = "https://erez.ac"
# Deliberately past the crawler's 21:00 cutoff: question 1 is partly *when* the
# finals publish, and the night-stop plan's accepted cost rests on the answer.
# One evening of measurement, from the laptop, not the crawler.
DEFAULT_UNTIL = "23:00"

# The finals pages are fetched every cheap tick whether or not the landing page
# advertises them — comparing "link present" against "page has content" is the
# whole of question 1, and only unconditional fetching can separate the two.

def _now():
    return time.time()


def _iso(ts):
    return datetime.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def _digest(text):
    return hashlib.sha256((text or "").encode("utf-8", "replace")).hexdigest()[:16]


class Recorder:
    """JSONL sink. One line per observation, flushed immediately so a run that
    is interrupted keeps everything it had already seen."""

    def __init__(self, path, html_dir=None, echo=True):
        self.path = path
        self.html_dir = html_dir
        self.echo = echo
        self._seen_html = set()
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")

    def record(self, kind, **fields):
        ts = _now()
        row = {"ts": round(ts, 3), "iso": _iso(ts), "kind": kind, **fields}
        self._fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._fh.flush()
        if self.echo:
            print(f"{row['iso']} {kind:<12} " + " ".join(
                f"{k}={v}" for k, v in fields.items()
                if k in ("show_id", "target", "breed", "rows", "note", "error")
            ))
        return row

    def save_html(self, show_id, label, html):
        """Snapshot a page whenever its content changes.

        The RYP and BIS page shapes have never been parsed, so plan 3's parser
        needs real fixtures — including the empty-before-finals version, which is
        the evidence for question 1.
        """
        if not self.html_dir or not html:
            return None
        digest = _digest(html)
        key = (show_id, label, digest)
        if key in self._seen_html:
            return None
        self._seen_html.add(key)
        directory = os.path.join(self.html_dir, str(show_id))
        os.makedirs(directory, exist_ok=True)
        name = f"{label}-{int(_now())}-{digest}.html"
        with open(os.path.join(directory, name), "w", encoding="utf-8") as fh:
            fh.write(html)
        return name

    def close(self):
        self._fh.close()


def _fetch(url):
    """Fetch and return (soup, html, error). Never raises: a run that loses the
    network for a minute must keep observing, and the gap is itself data."""
    try:
        soup = _fetch_page(url)
        return soup, str(soup), None
    except Exception as exc:  # noqa: BLE001 - any failure is recorded, not raised
        return None, None, f"{type(exc).__name__}: {exc}"


def _finals_page_signal(soup, show_id):
    """The state of a finals page at this moment.

    `sections: 0` on a page that fetched fine is the interesting case — the page
    exists but holds no finals yet — and it is a different fact from the landing
    nav not offering the page at all. Question 1 is exactly which of those two
    Showlink does before the finals are judged, so both are recorded separately.
    """
    if soup is None:
        return {}
    parsed = _parse_finals_page(soup, show_id)
    sections = parsed["sections"]
    return {
        "sections": len(sections),
        "placements": sum(len(section["placements"]) for section in sections),
        "headings": [section["heading"] for section in sections],
        "fci_groups": [group for section in sections for group in section["fci_groups"]],
        "winners": [
            {
                "heading": section["heading"],
                "place": placement["place"],
                "breed_name": placement["breed_name"],
                "reg_id": placement["reg_id"],
            }
            for section in sections for placement in section["placements"]
        ],
        "digest": _digest(soup.get_text(" ", strip=True)),
    }


class ShowObserver:
    def __init__(self, show_id, recorder, args):
        self.show_id = int(show_id)
        self.rec = recorder
        self.args = args
        self.groups = []
        self.breeds = {}          # "group:breed_id" -> last seen breed-list row
        self.breed_state = {}     # "group:breed_id" -> last seen breed-page state
        self.breed_sampled_at = {}
        self.nav_targets = set()
        self.next_cheap = 0.0
        self.next_breeds = 0.0

    # -- cheap tier ---------------------------------------------------------

    def cheap_pass(self):
        """Landing page, every group breed list, and both finals pages."""
        landing_url = _source_url(self.show_id)
        soup, html, error = _fetch(landing_url)
        if error:
            self.rec.record("cheap", show_id=self.show_id, target="landing", error=error)
        else:
            targets = _breed_list_targets_from_soup(soup, self.show_id)
            # Question 1: does the nav advertise RYP/BIS before they exist? The
            # index crawler discards anything that is not a digit group or R=R,
            # so this is the first time we look at what else is offered.
            nav = self._nav_targets(soup)
            self.nav_targets = nav
            landing_breeds = _parse_breeds_from_soup(soup, self.show_id)
            self.groups = [t for t in targets if t not in FINALS_TARGETS]
            self.rec.record(
                "cheap", show_id=self.show_id, target="landing",
                nav_targets=sorted(nav),
                nav_has_ryp="RYP" in nav, nav_has_bis="BIS" in nav,
                group_targets=self.groups,
                landing_breeds=len(landing_breeds),
            )
            if landing_breeds:
                self._record_breed_list("landing", landing_breeds)

        for group in self.groups:
            time.sleep(self.args.delay)
            url = _source_url(self.show_id, group)
            soup, html, error = _fetch(url)
            if error:
                self.rec.record("cheap", show_id=self.show_id, target=f"R={group}", error=error)
                continue
            self._record_breed_list(f"R={group}", _parse_breeds_from_soup(soup, self.show_id))

        for target in FINALS_TARGETS:
            time.sleep(self.args.delay)
            url = _source_url(self.show_id, target)
            soup, html, error = _fetch(url)
            if error:
                self.rec.record("finals", show_id=self.show_id, target=target, error=error)
                continue
            signal = _finals_page_signal(soup, self.show_id)
            saved = self.rec.save_html(self.show_id, target, html)
            self.rec.record(
                "finals", show_id=self.show_id, target=target,
                nav_advertised=target in self.nav_targets,
                html_snapshot=saved, **signal,
            )

    def _nav_targets(self, soup):
        content = soup.find(id="divContent") or soup.find(id="content") or soup
        found = set()
        for anchor in content.find_all("a"):
            href = anchor.get("href", "")
            id_match = re.search(r"(?:[?&]|&amp;)Id=(\d+)", href)
            if id_match and str(id_match.group(1)) != str(self.show_id):
                continue
            r_match = re.search(r"(?:[?&]|&amp;)R=([^&#]+)", href)
            if r_match:
                found.add(r_match.group(1).upper())
        return found

    def _record_breed_list(self, target, breeds):
        """Questions 6 and 3: per-breed check icon and entry count over time.

        Only changes are recorded — a 96-breed list re-logged every two minutes
        for thirteen hours would bury the transitions that matter.
        """
        changes = []
        for breed in breeds:
            key = f"{breed.get('group')}:{breed.get('breed_id')}"
            previous = self.breeds.get(key)
            row = {
                "name": breed.get("name"),
                "count": breed.get("count"),
                "has_results": bool(breed.get("has_results")),
            }
            if previous != row:
                changes.append({
                    "breed": key, **row,
                    "was_has_results": None if previous is None else previous["has_results"],
                    "was_count": None if previous is None else previous["count"],
                })
                self.breeds[key] = row
        self.rec.record(
            "breed_list", show_id=self.show_id, target=target,
            breeds=len(breeds),
            checked=sum(1 for b in breeds if b.get("has_results")),
            changes=changes,
        )

    # -- expensive tier -----------------------------------------------------

    def _sample_keys(self):
        """Which breed pages to open this tick.

        Priority is exactly what questions 2 and 5 need: breeds that have started
        but have not shown a bare ROP yet (the gap being measured), then the
        least-recently-sampled of the rest — including ones that already look
        complete, because whether rows arrive after that is question 5.
        """
        started = [key for key, row in self.breeds.items() if row["has_results"]]
        if not started:
            return []

        def sampled_at(key):
            return self.breed_sampled_at.get(key, 0.0)

        unfinished = [k for k in started if not self.breed_state.get(k, {}).get("has_rop")]
        finished = [k for k in started if self.breed_state.get(k, {}).get("has_rop")]
        unfinished.sort(key=sampled_at)
        finished.sort(key=sampled_at)
        # Keep at least one slot for a finished breed so late rows are visible
        # even on a show where everything is mid-ring.
        limit = self.args.breed_sample
        chosen = unfinished[: max(1, limit - 1)]
        chosen += finished[: limit - len(chosen)]
        return chosen

    def breed_pass(self):
        for key in self._sample_keys():
            group, _, breed_id = key.partition(":")
            time.sleep(self.args.delay)
            url = _source_url(self.show_id, group, breed_id)
            soup, html, error = _fetch(url)
            self.breed_sampled_at[key] = _now()
            if error:
                self.rec.record("breed", show_id=self.show_id, breed=key, error=error)
                continue

            parsed = _parse_breed_results(soup, self.show_id)
            awards = parsed.get("awards") or []
            state = {
                "rows": len(parsed.get("results") or []),
                "award_types": [a.get("type", "") for a in awards],
                "judge": parsed.get("judge") or "",
                "classes": sorted({
                    row.get("class_name", "") for row in (parsed.get("results") or [])
                }),
            }
            state["has_rop"] = _breed_bob_awarded(awards)
            previous = self.breed_state.get(key)
            self.breed_state[key] = state
            self.rec.record(
                "breed", show_id=self.show_id, breed=key,
                name=(self.breeds.get(key) or {}).get("name"),
                entry_count=(self.breeds.get(key) or {}).get("count"),
                rows=state["rows"],
                prev_rows=None if previous is None else previous["rows"],
                has_rop=state["has_rop"],
                gained_rop=bool(state["has_rop"] and previous and not previous["has_rop"]),
                # Question 5, the one that decides how slow the cool sweep can be.
                late_rows=bool(previous and previous["has_rop"] and state["rows"] > previous["rows"]),
                award_types=state["award_types"],
                judge=state["judge"],
                classes=state["classes"],
            )

    # -- our own capture side ----------------------------------------------

    def api_pass(self):
        url = f"{self.args.api_base.rstrip('/')}/api/dog/shows/{self.show_id}"
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            self.rec.record("api", show_id=self.show_id, error=f"{type(exc).__name__}: {exc}")
            return
        stats = payload.get("stats") or {}
        breeds = payload.get("breeds") or []
        self.rec.record(
            "api", show_id=self.show_id, status=payload.get("status"),
            breed_count=len(breeds),
            with_results=sum(1 for b in breeds if b.get("has_results")),
            is_live=stats.get("is_live"), is_paused=stats.get("is_paused"),
            show_state=stats.get("show_state"), result_count=stats.get("result_count"),
            result_breed_count=stats.get("result_breed_count"),
        )


def _parse_until(value):
    hour, _, minute = value.partition(":")
    end = datetime.datetime.now().replace(
        hour=int(hour), minute=int(minute or 0), second=0, microsecond=0
    )
    if end <= datetime.datetime.now():
        end += datetime.timedelta(days=1)
    return end.timestamp()


def _print_show_list():
    soup, _, error = _fetch(BASE_URL)
    if error:
        print(f"show list fetch failed: {error}")
        return 1
    today = datetime.date.today()
    label = f"{today.day:02d}.{today.month:02d}."
    for show in _parse_show_list(soup):
        marker = "*" if show["date"].startswith(label) or label in show["date"] else " "
        print(f"{marker} {show['id']:>6}  {show['date']:<14} {show['name']}")
    print("\n* = runs today. Pick shows of different shapes (question 7).")
    return 0


def _dry_run(show_ids, args):
    """One fetch of each page type per show, printing what was extracted.

    Worth more than unit tests here: it proves the selectors still match today's
    Showlink markup, which is the only way this tool can silently record nothing.
    """
    recorder = Recorder(args.out, html_dir=args.html_dir, echo=True)
    try:
        for show_id in show_ids:
            observer = ShowObserver(show_id, recorder, args)
            print(f"\n=== show {show_id}: cheap pass ===")
            observer.cheap_pass()
            print(f"=== show {show_id}: api ===")
            observer.api_pass()
            print(f"=== show {show_id}: breed sample ===")
            keys = observer._sample_keys()
            if not keys:
                print("  no breed has a check icon yet — nothing to sample")
            else:
                observer.breed_pass()
    finally:
        recorder.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--show", type=int, action="append", default=[],
                        help="Showlink show id to observe (repeatable).")
    parser.add_argument("--list", action="store_true",
                        help="Print the Showlink show list, marking today's shows, and exit.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch each page type once, print what was extracted, exit.")
    parser.add_argument("--out", default="observations/dog-live.jsonl",
                        help="JSONL output path (appended to).")
    parser.add_argument("--html-dir", default="observations/html",
                        help="Directory for RYP/BIS page snapshots; empty to disable.")
    parser.add_argument("--cheap-interval", type=int, default=DEFAULT_CHEAP_INTERVAL,
                        help="Seconds between cheap-page passes (default 120).")
    parser.add_argument("--breed-interval", type=int, default=DEFAULT_BREED_INTERVAL,
                        help="Seconds between breed-page samples (default 600).")
    parser.add_argument("--breed-sample", type=int, default=DEFAULT_BREED_SAMPLE,
                        help="Breed pages per sample, per show (default 6).")
    parser.add_argument("--delay", type=float, default=DEFAULT_REQUEST_DELAY,
                        help="Seconds between requests, as the result crawler (default 0.4).")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE,
                        help="Base URL of our own API (default https://erez.ac).")
    parser.add_argument("--until", default=DEFAULT_UNTIL,
                        help="Local HH:MM to stop at (default 23:00, past the crawler's cutoff).")
    args = parser.parse_args()

    if args.list:
        return _print_show_list()

    if not args.show:
        parser.error("give at least one --show id (or --list to find them)")

    if args.dry_run:
        return _dry_run(args.show, args)

    end_ts = _parse_until(args.until)
    recorder = Recorder(args.out, html_dir=args.html_dir or None, echo=True)
    observers = [ShowObserver(show_id, recorder, args) for show_id in args.show]
    recorder.record(
        "meta", note="run started", shows=args.show,
        cheap_interval=args.cheap_interval, breed_interval=args.breed_interval,
        breed_sample=args.breed_sample, delay=args.delay, until=_iso(end_ts),
    )

    try:
        while _now() < end_ts:
            for observer in observers:
                now = _now()
                if now >= observer.next_cheap:
                    observer.next_cheap = now + args.cheap_interval
                    observer.cheap_pass()
                    observer.api_pass()
                if now >= observer.next_breeds:
                    observer.next_breeds = now + args.breed_interval
                    observer.breed_pass()
            time.sleep(1)
    except KeyboardInterrupt:
        recorder.record("meta", note="interrupted")
    finally:
        recorder.record("meta", note="run finished")
        recorder.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
