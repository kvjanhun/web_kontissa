"""Award-structure analysis for live dog-show terminal detection.

Pure functions over a whole-show result doc plus the indexed breed list. No I/O
and no clock: given the awards captured so far, decide whether the show has
reached its terminal award, and if not, which already-captured breed pages could
carry the missing finals so the crawler can re-check *those* instead of blindly
rotating over every breed.

Finnish show structure (the model this encodes):

- Dogs are graded breed by breed inside each FCI group. Every breed crowns a
  breed winner ``ROP``.
- When all breeds in a group are judged, the group winners ``RYP-1..4`` are
  chosen from that group's ``ROP`` dogs — no new written grades.
- After every group has its winners, the main ``BIS-1..4`` is chosen from the
  ``RYP-1`` group winners.
- Juniors/veterans have no group stage; their ``BIS JUN`` / ``BIS VET`` finals
  land on class winners' rows independently.

Showlink appends these finals tokens onto the *winning dogs'* already-captured
breed rows, so the awards in the result doc are where a captured final shows up.

The show's *own* finals pages (``R=RYP`` and ``R=BIS``) are the authority on what
that structure actually is, and the crawler stores what it saw of them under
``doc["finals_probe"]``. They name every winner with their breed, and their
section headings expose the real rings — a show that judges FCI 5 and 6 in one
ring writes one ``FCI 5/6`` section with one RYP-1, which cannot be derived from
the breed index at all. Where the probe is present it wins; where it has not been
fetched yet, the index-derived expectation below is the fallback.
"""

import re
from urllib.parse import unquote


def parse_reg_id(reg_url):
    """Extract the dog registration number from a jalostus.kennelliitto.fi link.

    e.g. '.../frmKoira.aspx?RekNo=FI44694%2F25' -> 'FI44694/25'. This reg id is
    the cross-show anchor for a dog; it must survive URL-encoding of the slash.
    It lives in this leaf module because both the finals reconciliation here and
    `utils` need it, and utils imports finals.
    """
    if not reg_url:
        return ""
    match = re.search(r"[?&]RekNo=([^&#]+)", str(reg_url), flags=re.IGNORECASE)
    if not match:
        return ""
    return unquote(match.group(1)).strip()


def _tokens(awards):
    return [token.strip().upper() for token in str(awards or "").split(",") if token.strip()]


def _is_group_final(token):
    """Group Best in Show placement (RYP-1..4)."""
    return token.startswith("RYP")


def _is_main_bis(token):
    """Main Best in Show placement (BIS-1..4), not the junior/veteran/puppy BIS."""
    return token == "BIS" or token.startswith("BIS-")


def _is_side_bis(token):
    """Junior / veteran / puppy Best in Show (no group stage feeds these)."""
    return token.startswith(("BIS JUN", "BIS VET", "BIS PEN"))


def _is_any_final(token):
    return _is_group_final(token) or _is_main_bis(token) or _is_side_bis(token)


def _row_group(row):
    return str(row.get("breedGroup") or (row.get("breedObj") or {}).get("group") or "").strip()


def _row_breed_id(row):
    return str(row.get("breedId") or (row.get("breedObj") or {}).get("breed_id") or "").strip()


def _row_key(row):
    """Breed cache key `group:breed_id`, matching `_breed_cache_key_from_breed`."""
    return f"{_row_group(row)}:{_row_breed_id(row)}"


def _expected_result_groups(indexed_breeds):
    """FCI groups (digit labels) that have entries, so should crown an RYP.

    Derived from the index, not from captured results, so an all-breed show is
    known to owe every group's RYP even before those rings are judged. Breeds
    with an explicit zero entry count are excluded; unknown counts are kept
    (poll rather than settle early)."""
    groups = set()
    for breed in indexed_breeds or []:
        group = str(breed.get("group") or "").strip()
        if not group.isdigit():
            continue
        count = breed.get("count")
        try:
            if count is not None and int(count) <= 0:
                continue
        except (TypeError, ValueError):
            pass
        groups.add(group)
    return groups


# ---------------------------------------------------------------------------
# Is one breed's ring finished?
#
# Pure predicates over a captured breed entry plus its index row. They live here
# rather than in the crawler because `utils._nothing_left_to_judge` — rung 2 of
# the settle ladder — needs them, and utils imports this module.
# ---------------------------------------------------------------------------

def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _breed_bob_awarded(awards):
    """True if a breed's honour roll crowns ROP — Best of Breed, the last award a
    breed ring hands out, and therefore the source's own "this ring is finished".

    Match the bare token: "ROP juniori" / "ROP pentu" / "ROP kasvattaja" are class
    and breeder titles that can land long before the breed itself is crowned, while
    a championship suffix ("ROP, V-24") is still the breed's own ROP."""
    for award in awards or []:
        label = str((award or {}).get("type") or "").split(",")[0].strip().upper()
        if label == "ROP":
            return True
    return False

def _breed_capture_has_full_rows(entry, breed):
    """Every entered dog has a row (absentees are listed with grade `poissa`, so
    the entry count is reachable)."""
    result_count = _safe_int((entry or {}).get("result_count")) or 0
    entry_count = _safe_int((breed or {}).get("count")) or 0
    return bool(entry_count) and result_count >= entry_count


def _breed_capture_is_provisional(entry, breed):
    """Full rows but no ROP yet: complete enough to stop fast-polling, not final.

    Showlink publishes the class rows before the honour roll, so a full-looking
    page can still be a ring mid-judging. Treating that as final froze 29 of show
    14014's 96 breeds without a ROP — two of them the group winners its finals
    were waiting on. The arm cannot simply be deleted either: a single-entry breed
    genuinely gets no honour roll, so full rows must eventually mean something."""
    if not isinstance(entry, dict):
        return False
    if _breed_bob_awarded(entry.get("awards")):
        return False
    return _breed_capture_has_full_rows(entry, breed)


def _breed_capture_is_settled(entry, breed):
    """Whether a captured breed's rows can be treated as the breed's final result.

    Final on the source's own statement that the ring ended — the honour roll
    crowns ROP — or on full rows that came back unchanged on a later fetch
    (`rows_confirmed_at`), which is what a breed with no honour roll can offer.
    A first sighting of full rows is provisional: it stops the breed being
    fast-polled, and leaves it eligible for the slower re-check that catches a
    ROP, or a row, arriving after the ring appeared done."""
    if not isinstance(entry, dict):
        return False
    result_count = _safe_int(entry.get("result_count")) or 0
    if result_count <= 0:
        return False
    if _breed_bob_awarded(entry.get("awards")):
        return True
    return bool(entry.get("rows_confirmed_at")) and _breed_capture_has_full_rows(entry, breed)

def _placement_token_family(page, heading):
    """Which award token a placement on this finals section should produce.

    Derived from the token grammar the breed rows actually use (see
    `_is_group_final` / `_is_main_bis` / `_is_side_bis`), not from a table of
    invented strings: an RYP section produces `RYP-<place>`, the main Best in
    show section produces `BIS-<place>`, and every other section on the BIS page
    is a side final whose token starts with `BIS ` (BIS JUN / BIS VET / BIS PEN).
    """
    if page == "RYP":
        return "RYP"
    if "BEST IN SHOW" in (heading or "").upper():
        return "BIS"
    return "SIDE_BIS"


def _token_satisfies(token, family, place):
    """Whether a captured award token is the one a finals placement promised."""
    suffix = f"-{place}"
    if family == "RYP":
        return token.startswith("RYP") and token.endswith(suffix)
    if family == "BIS":
        return _is_main_bis(token) and (token.endswith(suffix) or (place == 1 and token == "BIS"))
    if family == "SIDE_BIS":
        return _is_side_bis(token) and token.endswith(suffix)
    return _is_any_final(token) and token.endswith(suffix)


def _probe_sections(doc):
    """The finals-page sections the crawler last saw, as (page, section) pairs."""
    probe = (doc or {}).get("finals_probe") or {}
    pages = probe.get("pages") or {}
    for page in ("RYP", "BIS"):
        entry = pages.get(page) or {}
        for section in entry.get("sections") or []:
            yield page, section


def _breed_key_index(indexed_breeds):
    """Breed name (casefolded) -> `group:breed_id`, for reconciling the finals
    pages' winners to breed pages. The finals pages name the breed but not its
    id, so the index is the only bridge."""
    index = {}
    for breed in indexed_breeds or []:
        name = str(breed.get("name") or "").strip().casefold()
        group = str(breed.get("group") or "").strip()
        breed_id = str(breed.get("breed_id") or "").strip()
        if name and group and breed_id:
            index.setdefault(name, f"{group}:{breed_id}")
    return index


def _captured_tokens_by_key(results):
    """`group:breed_id` -> the award tokens captured on that breed's rows, and
    the same keyed by registration id where the source gave one."""
    by_key = {}
    by_reg = {}
    for row in results or []:
        tokens = _tokens(row.get("awards"))
        if not tokens:
            continue
        by_key.setdefault(_row_key(row), set()).update(tokens)
        reg_id = parse_reg_id(row.get("reg_url"))
        if reg_id:
            by_reg.setdefault(reg_id, set()).update(tokens)
    return by_key, by_reg


def probe_state(doc, indexed_breeds):
    """What the finals pages say, reconciled against what we have captured.

    Returns the pieces the ladder and the targeted re-fetch need:

    - `seen`: the probe has run at least once (absent on an old cache);
    - `published`: a finals page holds at least one placement — the source's own
      statement that the finals exist, which no amount of breed-page reading can
      give;
    - `expected_ryp_rings` / `ryp_rings_awarded`: rings as the RYP page groups
      them, so a combined `FCI 5/6` ring counts once and not twice;
    - `missing_keys`: exactly the breed pages whose captured rows are missing a
      token the finals pages have already promised. This is the re-fetch list —
      the whole of it.
    """
    probe = (doc or {}).get("finals_probe") or {}
    # `seen` means a finals page was actually read, not merely attempted. A probe
    # whose fetches all failed carries no pages, and must fall back to the
    # structural rules rather than read as "this show awards no finals" — the
    # difference between "the source says there are none" and "we could not ask".
    if not (probe.get("pages") or {}):
        return {
            "seen": False, "published": False, "advertised": [],
            "expected_ryp_rings": 0, "ryp_rings_awarded": 0,
            "ryp_ring_groups": [], "missing_keys": [], "placements": 0,
            "unmatched_breeds": [],
        }

    key_by_name = _breed_key_index(indexed_breeds)
    tokens_by_key, tokens_by_reg = _captured_tokens_by_key((doc or {}).get("results"))

    missing = []
    unmatched = []
    placements = 0
    ryp_ring_groups = []
    ryp_rings_awarded = 0

    for page, section in _probe_sections(doc):
        heading = section.get("heading") or ""
        family = _placement_token_family(page, heading)
        section_placements = section.get("placements") or []
        if page == "RYP":
            ryp_ring_groups.append(section.get("fci_groups") or [])
            if section_placements:
                ryp_rings_awarded += 1
        for placement in section_placements:
            placements += 1
            place = placement.get("place")
            breed_name = str(placement.get("breed_name") or "").strip().casefold()
            key = key_by_name.get(breed_name)
            if not key:
                # The finals page names a breed the index does not carry. Record
                # it rather than dropping it: it means the index is incomplete,
                # which is a fetch the crawler should make, not a fact to hide.
                unmatched.append(placement.get("breed_name") or "")
                continue
            reg_id = str(placement.get("reg_id") or "").strip()
            if not reg_id:
                # No dog link: the breeder-group final places a *kennel*, and no
                # breed row will ever carry a token for it. Demanding one would
                # re-fetch that breed for the life of the show. It still counts
                # as a published placement — the finals exist — just not as an
                # obligation.
                continue
            captured = set(tokens_by_reg.get(reg_id) or tokens_by_key.get(key) or ())
            if not any(_token_satisfies(token, family, place) for token in captured):
                if key not in missing:
                    missing.append(key)

    pages = probe.get("pages") or {}
    return {
        "seen": True,
        "published": placements > 0,
        "advertised": list(probe.get("advertised") or []),
        "expected_ryp_rings": len((pages.get("RYP") or {}).get("sections") or []),
        "ryp_rings_awarded": ryp_rings_awarded,
        "ryp_ring_groups": ryp_ring_groups,
        "missing_keys": missing,
        "placements": placements,
        "unmatched_breeds": unmatched,
    }


def analyze(doc, indexed_breeds):
    """Structural read of the finals captured so far.

    Returns a dict with the show-type inference (`expects_finals`), the terminal
    decision (`target_met`), the pieces the crawler needs to target the missing
    finals, and a `fingerprint` of every finals token for stability confirmation.
    """
    results = (doc or {}).get("results") or []
    result_groups = _expected_result_groups(indexed_breeds)

    ryp1_groups = set()
    ryp_stage = False
    has_bis1 = False
    has_side_bis = False
    finals_keys = set()
    ryp1_winner_keys = set()
    rop_keys_by_group = {}
    fingerprint = set()

    for row in results:
        tokens = _tokens(row.get("awards"))
        if not tokens:
            continue
        key = _row_key(row)
        group = _row_group(row)
        row_has_final = False
        for token in tokens:
            if _is_group_final(token):
                ryp_stage = True
                row_has_final = True
                fingerprint.add((key, token))
                if token == "RYP-1":
                    ryp1_winner_keys.add(key)
                    if group.isdigit():
                        ryp1_groups.add(group)
            elif _is_main_bis(token):
                row_has_final = True
                fingerprint.add((key, token))
                if token == "BIS-1":
                    has_bis1 = True
            elif _is_side_bis(token):
                has_side_bis = True
                row_has_final = True
                fingerprint.add((key, token))
            elif token == "ROP":
                rop_keys_by_group.setdefault(group, set()).add(key)
        if row_has_final:
            finals_keys.add(key)

    # Only a MULTI-group show crowns a main Best in Show. A single-group show —
    # a breed or group specialty — tops out at its group RYP-1 (if it runs a
    # group ring) plus junior/veteran/utility BIS on the breed rows, and awards
    # no `BIS-1`. Requiring `BIS-1` from those (they exist — e.g. a group-10-only
    # show with only junior/veteran/utility BIS) would keep polling them forever.
    expects_main_bis = len(result_groups) >= 2
    expects_finals = expects_main_bis or ryp_stage or has_bis1 or has_side_bis
    missing_ryp_groups = (result_groups - ryp1_groups) if ryp_stage else set()

    probe = probe_state(doc, indexed_breeds)

    if probe["seen"]:
        # The finals pages are the source's own statement of what it has awarded,
        # so once they have been read there is nothing left to infer: the target
        # is met when they hold placements and every one of those placements has
        # landed on its breed's rows. This is what makes a combined `FCI 5/6`
        # ring, a group-only show and a specialty cluster stop being special
        # cases — none of them can produce an expectation the pages contradict.
        target_met = probe["published"] and not probe["missing_keys"]
    elif ryp_stage:
        target_met = has_bis1 and not missing_ryp_groups
    else:
        # No probe yet and no group stage observed. A multi-group specialty
        # cluster crowns BIS-1 directly; anything else with finals tokens but no
        # BIS yet keeps polling.
        target_met = has_bis1

    return {
        "probe": probe,
        "expects_finals": expects_finals,
        "expects_main_bis": expects_main_bis,
        "result_groups": result_groups,
        "ryp_stage": ryp_stage,
        "ryp1_groups": ryp1_groups,
        "missing_ryp_groups": missing_ryp_groups,
        "has_bis1": has_bis1,
        "has_side_bis": has_side_bis,
        "target_met": target_met,
        "finals_keys": finals_keys,
        "ryp1_winner_keys": ryp1_winner_keys,
        "rop_keys_by_group": rop_keys_by_group,
        "fingerprint": frozenset(fingerprint),
    }


def candidate_breed_keys(analysis):
    """Breed keys worth re-fetching to capture missing or late finals.

    With the finals probe this is an exact list, not a guess: the pages name
    every winner with their breed, so the breeds needing a re-read are precisely
    those whose captured rows lack a token the pages have already promised. An
    empty list then means there is nothing outstanding — including the case where
    the pages hold no finals at all, which is a real answer and not a reason to
    keep sweeping.

    Without a probe (an old cache, or the pages never fetched) it falls back to
    the structural guesses that were the only option before: groups still missing
    their RYP-1 -> those groups' ROP winners; all RYP-1 present but no BIS-1 ->
    the RYP-1 winners' breeds; a specialty cluster with no group stage -> the
    breed ROP winners; terminal reached -> the finals-carrying breeds once, for a
    late BIS-2..4.

    Returns [] when the show expects no finals at all.
    """
    probe = analysis.get("probe") or {}
    if probe.get("seen"):
        return list(probe.get("missing_keys") or [])

    if not analysis.get("expects_finals"):
        return []

    rop_by_group = analysis.get("rop_keys_by_group") or {}

    if analysis.get("ryp_stage") and analysis.get("missing_ryp_groups"):
        keys = set()
        for group in analysis["missing_ryp_groups"]:
            keys |= rop_by_group.get(group, set())
        return sorted(keys)

    if not analysis.get("has_bis1"):
        if analysis.get("ryp_stage"):
            return sorted(analysis.get("ryp1_winner_keys") or set())
        keys = set()
        for group_keys in rop_by_group.values():
            keys |= group_keys
        return sorted(keys)

    return sorted(analysis.get("finals_keys") or set())


def fingerprint_token(analysis):
    """Stable, comparable string of every captured finals token.

    Stored in the cache doc; when it stops changing between finals passes the
    terminal is confirmed stable and the show may settle."""
    return "|".join(f"{key}={token}" for key, token in sorted(analysis.get("fingerprint") or frozenset()))
