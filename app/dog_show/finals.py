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
breed rows, so the terminal is inferred from the awards in the result doc.
"""


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

    expects_finals = len(result_groups) >= 2 or ryp_stage or has_bis1 or has_side_bis
    missing_ryp_groups = (result_groups - ryp1_groups) if ryp_stage else set()

    if ryp_stage:
        target_met = has_bis1 and not missing_ryp_groups
    else:
        # No group stage observed. A multi-group specialty cluster crowns BIS-1
        # directly; anything else with finals tokens but no BIS yet keeps polling.
        target_met = has_bis1

    return {
        "expects_finals": expects_finals,
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
    """Ordered breed keys worth re-fetching to capture missing or late finals.

    Structural, not a blind rotation:

    - groups still missing their RYP-1 -> re-check those groups' ROP winners
      (RYP lands on a breed ROP dog's row);
    - all RYP-1 present but no BIS-1 -> re-check exactly the RYP-1 winners'
      breeds (the main BIS finalists are the group winners);
    - a specialty cluster with no group stage -> re-check the breed ROP winners
      (BIS is chosen among them);
    - terminal reached -> re-check the finals-carrying breeds once so a late
      BIS-2..4 or a correction is caught before settling.

    Returns [] when the show expects no finals at all.
    """
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
