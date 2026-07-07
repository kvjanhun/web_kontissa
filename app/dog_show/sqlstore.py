"""Conversion between the dict shapes the package speaks and the dog.db ORM rows.

This is the single source of truth for how show/breed index entries, whole-show
result docs, and the result-job queue map onto SQL, plus the indexed queries the
read paths (show detail, stats, search) run directly against dog.db. Everything
goes through `store.py`, which wraps these helpers in sessions and error handling.
"""

import json

from sqlalchemy import delete, exists, func, or_, select, update

from .models import (
    DogBreed, DogBreedAward, DogMeta, DogResult, DogResultCache, DogResultJob, DogShow,
)
from .utils import _clean_judge_name, _parse_reg_id

# Whole-show result-doc top-level fields promoted to their own columns. Every
# other top-level key (completed_breeds, failed_breeds, live_* tracking) goes
# into the JSON `meta` blob; `results` is normalized into DogResult rows.
_RESULT_DOC_PROMOTED = (
    "version", "status", "source", "title", "source_url",
    "total_breeds", "started_at", "updated_at", "cached_at", "last_error",
)

_JOB_FIELDS = (
    "state", "reason", "attempts", "created_at", "updated_at",
    "requested_at", "next_attempt_at", "last_started_at", "last_error",
)


# ---------------------------------------------------------------------------
# Show index  (<-> dog_show_index.json)
# ---------------------------------------------------------------------------

def _breed_judge_for_storage(breed):
    judge = _clean_judge_name(breed.get("judge"))
    return judge or None


def write_show(session, show_id, show):
    """Replace one show's metadata + breed list. Returns nothing."""
    sid = int(show_id)
    session.execute(delete(DogBreed).where(DogBreed.show_id == sid))
    session.merge(DogShow(
        id=sid,
        name=show.get("name", "") or "",
        title=show.get("title", "") or "",
        date=show.get("date", "") or "",
        month=show.get("month", "") or "",
        source_url=show.get("source_url", "") or "",
        updated_at=show.get("updated_at") or 0.0,
        updated_at_iso=show.get("updated_at_iso"),
        empty_breed_list_confirmed=bool(show.get("empty_breed_list_confirmed")),
    ))
    session.flush()  # ensure the parent show row exists before its breed FKs
    for position, breed in enumerate(show.get("breeds") or []):
        session.add(DogBreed(
            show_id=sid,
            position=position,
            fci_group=str(breed.get("group", "") or ""),
            breed_id=str(breed.get("breed_id", "") or ""),
            name=breed.get("name", "") or "",
            entry_count=breed.get("count"),
            has_results=bool(breed.get("has_results")),
            judge=_breed_judge_for_storage(breed),
            source_url=breed.get("source_url", "") or "",
        ))


def _breed_to_dict(row):
    breed = {
        "name": row.name or "",
        "count": row.entry_count if row.entry_count is not None else 0,
        "group": row.fci_group or "",
        "breed_id": row.breed_id or "",
        "has_results": bool(row.has_results),
        "source_url": row.source_url or "",
    }
    if row.judge:
        breed["judge"] = row.judge
    return breed


def _show_to_dict(show_row, breed_rows):
    entry = {
        "title": show_row.title or "",
        "name": show_row.name or "",
        "date": show_row.date or "",
        "month": show_row.month or "",
        "source_url": show_row.source_url or "",
        "breeds": [_breed_to_dict(b) for b in breed_rows],
        "updated_at": show_row.updated_at or 0,
        "updated_at_iso": show_row.updated_at_iso,
    }
    if show_row.empty_breed_list_confirmed:
        entry["empty_breed_list_confirmed"] = True
    return entry


def _show_meta_dict(show_row):
    """A show's index entry without its breed list (the cheap metadata read)."""
    entry = {
        "title": show_row.title or "",
        "name": show_row.name or "",
        "date": show_row.date or "",
        "month": show_row.month or "",
        "source_url": show_row.source_url or "",
        "updated_at": show_row.updated_at or 0,
        "updated_at_iso": show_row.updated_at_iso,
    }
    if show_row.empty_breed_list_confirmed:
        entry["empty_breed_list_confirmed"] = True
    return entry


# Column select for breed reads: lightweight Row objects, accessed by name
# exactly like the ORM entities. Bulk reads touch tens of thousands of breed
# rows, where ORM instance hydration costs ~10x the raw fetch.
_BREED_COLUMNS = (
    DogBreed.show_id, DogBreed.name, DogBreed.entry_count, DogBreed.fci_group,
    DogBreed.breed_id, DogBreed.has_results, DogBreed.source_url, DogBreed.judge,
)


def _show_breed_rows(session, show_ids):
    """Breed rows for a set of shows, grouped by show id, in breed-list order."""
    if not show_ids:
        return {}
    breeds_by_show = {}
    rows = session.execute(
        select(*_BREED_COLUMNS)
        .where(DogBreed.show_id.in_(show_ids))
        .order_by(DogBreed.show_id, DogBreed.position)
    )
    for row in rows:
        breeds_by_show.setdefault(row.show_id, []).append(row)
    return breeds_by_show


def read_show(session, show_id):
    """One show's full index entry (metadata + breeds) or None."""
    show_row = session.get(DogShow, int(show_id))
    if show_row is None:
        return None
    return _show_to_dict(show_row, _show_breed_rows(session, [show_row.id]).get(show_row.id, []))


def read_show_meta(session, show_id):
    """One show's index metadata (no breeds) or None."""
    show_row = session.get(DogShow, int(show_id))
    if show_row is None:
        return None
    return _show_meta_dict(show_row)


def read_shows(session, show_ids):
    """Full index entries for a set of shows: {str(show_id): entry}. Two queries
    regardless of the number of ids — the bulk read behind list-page stats."""
    ids = []
    for sid in show_ids or []:
        try:
            ids.append(int(sid))
        except (TypeError, ValueError):
            continue
    if not ids:
        return {}
    breeds_by_show = _show_breed_rows(session, ids)
    shows = {}
    for show_row in session.execute(select(DogShow).where(DogShow.id.in_(ids))).scalars():
        shows[str(show_row.id)] = _show_to_dict(show_row, breeds_by_show.get(show_row.id, []))
    return shows


def count_shows(session):
    return session.execute(select(func.count()).select_from(DogShow)).scalar_one()


def index_states(session):
    """Per-show index state for crawler candidate selection:
    {str(show_id): {"breed_count": int, "empty_breed_list_confirmed": bool,
    "updated_at": float}}."""
    rows = session.execute(
        select(
            DogShow.id,
            DogShow.empty_breed_list_confirmed,
            DogShow.updated_at,
            func.count(DogBreed.id).label("breed_count"),
        )
        .outerjoin(DogBreed, DogBreed.show_id == DogShow.id)
        .group_by(DogShow.id)
    )
    return {
        str(row.id): {
            "breed_count": row.breed_count,
            "empty_breed_list_confirmed": bool(row.empty_breed_list_confirmed),
            "updated_at": row.updated_at or 0,
        }
        for row in rows
    }


def set_breed_judge(session, show_id, fci_group, breed_id, judge, only_missing=False):
    """Store the (cleaned) judge on a breed's index row. Returns rows changed;
    no-op when the cleaned judge is empty or already stored. `only_missing`
    restricts to breeds without a judge (the sweep must not overwrite newer
    crawler-written values)."""
    judge = _clean_judge_name(judge)
    if not judge:
        return 0
    stmt = (
        update(DogBreed)
        .where(
            DogBreed.show_id == int(show_id),
            DogBreed.fci_group == str(fci_group),
            DogBreed.breed_id == str(breed_id),
        )
        .values(judge=judge)
    )
    if only_missing:
        stmt = stmt.where(or_(DogBreed.judge.is_(None), DogBreed.judge == ""))
    else:
        stmt = stmt.where(or_(DogBreed.judge.is_(None), DogBreed.judge != judge))
    return session.execute(stmt).rowcount


def set_breed_has_results(session, show_id, fci_group, breed_id):
    """Flag a breed's index row as having results. Returns rows changed."""
    return session.execute(
        update(DogBreed)
        .where(
            DogBreed.show_id == int(show_id),
            DogBreed.fci_group == str(fci_group),
            DogBreed.breed_id == str(breed_id),
            DogBreed.has_results.is_(False),
        )
        .values(has_results=True)
    ).rowcount


# ---------------------------------------------------------------------------
# Whole-show result doc  (<-> dog_result_cache/<id>.json)
# ---------------------------------------------------------------------------

def _result_cache_meta_blob(doc):
    meta = {
        k: v for k, v in doc.items()
        if k not in _RESULT_DOC_PROMOTED and k not in ("results", "show_id")
    }
    return json.dumps(meta, ensure_ascii=False)


def _write_result_cache_header(session, sid, doc):
    session.merge(DogResultCache(
        show_id=sid,
        version=doc.get("version"),
        status=doc.get("status"),
        source=doc.get("source"),
        title=doc.get("title"),
        source_url=doc.get("source_url"),
        total_breeds=doc.get("total_breeds"),
        started_at=doc.get("started_at"),
        updated_at=doc.get("updated_at"),
        cached_at=doc.get("cached_at"),
        last_error=doc.get("last_error"),
        meta=_result_cache_meta_blob(doc),
    ))


def _insert_result_rows(session, sid, results, start_seq=0):
    for offset, result in enumerate(results or []):
        session.add(DogResult(
            show_id=sid,
            seq=start_seq + offset,
            fci_group=str(result.get("breedGroup", "") or ""),
            breed_id=str(result.get("breedId", "") or ""),
            breed_name=result.get("breedName", "") or "",
            number=result.get("number"),
            name=result.get("name", "") or "",
            reg_url=result.get("reg_url", "") or "",
            reg_id=_parse_reg_id(result.get("reg_url")) or None,
            breed_judge=(result.get("breedObj") or {}).get("judge") or None,
            grade=result.get("grade", "") or "",
            placement=result.get("placement"),
            competitive_placement=result.get("competitive_placement", "") or "",
            awards=result.get("awards", "") or "",
            critique=result.get("critique", "") or "",
            gender=result.get("gender", "") or "",
            class_name=result.get("class_name", "") or "",
        ))


# completed_breeds keys are "group:breed_id"; each value's "awards" list holds the
# breed honor-roll winners projected into the queryable DogBreedAward table.
def _insert_breed_award_rows(session, sid, group, breed_id, awards):
    for position, award in enumerate(awards or []):
        if not isinstance(award, dict):
            continue
        session.add(DogBreedAward(
            show_id=sid,
            fci_group=group,
            breed_id=breed_id,
            position=position,
            award_type=award.get("type", "") or "",
            name=award.get("name", "") or "",
            owner=award.get("owner", "") or "",
            text=award.get("text", "") or "",
        ))


def write_result_doc(session, show_id, doc):
    """Full delete-and-reinsert of a whole-show result doc.

    Reserved for the final status="complete" save and the one-off migration, where
    a single clean rewrite is correct (and renormalizes seq to 0..n-1). Per-breed
    progress saves go through append_result_breed instead, which avoids re-deleting
    and re-inserting the entire accumulated set on every breed."""
    sid = int(show_id)
    session.execute(delete(DogResult).where(DogResult.show_id == sid))
    session.execute(delete(DogBreedAward).where(DogBreedAward.show_id == sid))

    _write_result_cache_header(session, sid, doc)
    _insert_result_rows(session, sid, doc.get("results") or [], start_seq=0)
    for breed_key, breed_data in (doc.get("completed_breeds") or {}).items():
        if not isinstance(breed_data, dict):
            continue
        group, _, bid = str(breed_key).partition(":")
        _insert_breed_award_rows(session, sid, group, bid, breed_data.get("awards"))


def write_result_cache_header(session, show_id, doc):
    """Update only the per-show cache header/meta row (status, completed/failed
    breeds, live-tracking blob) without touching the normalized result rows.

    The progress path uses this for breed failures and on resume, where the result
    rows are already persisted and only the header needs refreshing."""
    _write_result_cache_header(session, int(show_id), doc)


def append_result_breed(session, show_id, doc, group, breed_id, results):
    """Incrementally persist one freshly-completed breed: append its result rows
    (seq continues monotonically after the show's current max) and its honor-roll
    awards, then refresh the cache header/meta from doc.

    Scoped-deletes the breed's existing result + award rows first so a resumed or
    retried breed stays idempotent (no duplicates). Each transaction writes a
    single breed's handful of rows instead of the whole accumulated set."""
    sid = int(show_id)
    group = str(group or "")
    breed_id = str(breed_id or "")

    session.execute(delete(DogResult).where(
        DogResult.show_id == sid,
        DogResult.fci_group == group,
        DogResult.breed_id == breed_id,
    ))
    session.execute(delete(DogBreedAward).where(
        DogBreedAward.show_id == sid,
        DogBreedAward.fci_group == group,
        DogBreedAward.breed_id == breed_id,
    ))

    next_seq = session.execute(
        select(func.coalesce(func.max(DogResult.seq), -1)).where(DogResult.show_id == sid)
    ).scalar_one() + 1
    _insert_result_rows(session, sid, results or [], start_seq=next_seq)

    breed_data = (doc.get("completed_breeds") or {}).get(f"{group}:{breed_id}") or {}
    _insert_breed_award_rows(session, sid, group, breed_id, breed_data.get("awards"))

    _write_result_cache_header(session, sid, doc)


def _breed_obj_for(breed_row, fallback_group, fallback_breed_id, fallback_name):
    if breed_row is not None:
        return _breed_to_dict(breed_row)
    return {"name": fallback_name or "", "group": fallback_group or "", "breed_id": fallback_breed_id or ""}


def read_result_doc(session, show_id):
    sid = int(show_id)
    cache = session.get(DogResultCache, sid)
    if cache is None:
        return None

    breed_lookup = {
        (b.fci_group or "", b.breed_id or ""): b
        for b in session.execute(
            select(DogBreed).where(DogBreed.show_id == sid)
        ).scalars()
    }

    doc = {"version": cache.version, "show_id": sid, "status": cache.status,
           "source": cache.source, "title": cache.title, "source_url": cache.source_url,
           "started_at": cache.started_at, "updated_at": cache.updated_at,
           "cached_at": cache.cached_at, "total_breeds": cache.total_breeds,
           "last_error": cache.last_error}
    if cache.meta:
        doc.update(json.loads(cache.meta))

    results = []
    for row in session.execute(
        select(DogResult).where(DogResult.show_id == sid).order_by(DogResult.seq)
    ).scalars():
        breed_row = breed_lookup.get((row.fci_group or "", row.breed_id or ""))
        breed_obj = _breed_obj_for(breed_row, row.fci_group, row.breed_id, row.breed_name)
        # The result row carries the breed's judge in its own right (the result
        # cache is the source of per-breed judges), so it survives even when the
        # index breed has not been enriched with it yet.
        if row.breed_judge:
            breed_obj["judge"] = row.breed_judge
        result = {
            "number": row.number,
            "name": row.name or "",
            "reg_url": row.reg_url or "",
            "grade": row.grade or "",
            "placement": row.placement,
            "awards": row.awards or "",
            "critique": row.critique or "",
            "gender": row.gender or "",
            "class_name": row.class_name or "",
            "breedName": row.breed_name or "",
            "breedGroup": row.fci_group or "",
            "breedId": row.breed_id or "",
            "breedObj": breed_obj,
        }
        # Only emit when present, mirroring the optional judge field — keeps the
        # pre-Phase-C migrated docs (which had no PU/PN data) round-tripping clean.
        if row.competitive_placement:
            result["competitive_placement"] = row.competitive_placement
        results.append(result)
    doc["results"] = results
    return doc


def complete_result_cache_show_ids(session):
    """Show ids with a fully-captured result cache (status='complete').

    A single status-column scan, used by the finals-rescue tool to find complete
    caches without reconstructing each whole-show doc."""
    return {
        row[0] for row in session.execute(
            select(DogResultCache.show_id).where(DogResultCache.status == "complete")
        ).all()
    }


# ---------------------------------------------------------------------------
# Cross-show entity search (dog names, owners) over the captured result rows
# ---------------------------------------------------------------------------
# SQLite LIKE is only ASCII case-insensitive, so a name stored as "Tähti" is not
# matched by "TÄHTI" and vice versa for the å/ä/ö range. We OR together the raw,
# Unicode-upper, and Unicode-lower forms of the query so either stored casing is
# found without a normalized column / migration. `%`/`_`/`\` in the query are
# escaped so a literal "100%" search can't turn into a wildcard.

def _like_patterns(query, min_length=3):
    """Escaped `%q%` LIKE patterns (raw + upper + lower) or [] if too short."""
    q = str(query or "").strip()
    if len(q) < min_length:
        return []
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    seen = []
    for variant in (escaped, escaped.upper(), escaped.lower()):
        if variant not in seen:
            seen.append(variant)
    return [f"%{variant}%" for variant in seen]


def search_dog_results_by_name(session, query, limit=20, min_length=3):
    """Shows that ran a dog whose name matches `query`, grouped by show.

    Returns `[{show_id, name, count}]` — one row per show, with a representative
    matching dog name and how many result rows in that show matched. Newest shows
    first, bounded by `limit`. Parameterized LIKE only (see `_like_patterns`)."""
    patterns = _like_patterns(query, min_length)
    if not patterns:
        return []
    condition = or_(*[DogResult.name.like(pattern, escape="\\") for pattern in patterns])
    rows = session.execute(
        select(
            DogResult.show_id,
            func.min(DogResult.name).label("name"),
            func.count().label("count"),
        )
        .where(condition)
        .group_by(DogResult.show_id)
        .order_by(DogResult.show_id.desc())
        .limit(limit)
    ).all()
    return [{"show_id": row[0], "name": row[1], "count": row[2]} for row in rows]


def search_breed_award_owners(session, query, limit=20, min_length=3):
    """Shows where an award-winning dog's owner matches `query`, grouped by show.

    Returns `[{show_id, owner, count}]` — a representative matching owner and the
    number of honor-roll placements owned by a match in that show. Owners come
    from the `dog_breed_award` honor roll (`Om.` field), so this surfaces the
    people/kennels behind the ROP/VSP/SERT winners, which no other column carries.
    Newest shows first, bounded by `limit`."""
    patterns = _like_patterns(query, min_length)
    if not patterns:
        return []
    condition = or_(*[DogBreedAward.owner.like(pattern, escape="\\") for pattern in patterns])
    rows = session.execute(
        select(
            DogBreedAward.show_id,
            func.min(DogBreedAward.owner).label("owner"),
            func.count().label("count"),
        )
        .where(condition)
        .group_by(DogBreedAward.show_id)
        .order_by(DogBreedAward.show_id.desc())
        .limit(limit)
    ).all()
    return [{"show_id": row[0], "owner": row[1], "count": row[2]} for row in rows]


# ---------------------------------------------------------------------------
# Show / breed / judge index search
# ---------------------------------------------------------------------------
# The /api/dog/search index scan, in SQL. `variants` are the raw query forms
# (the query itself plus its judge-label-stripped form); each is expanded into
# escaped raw/upper/lower LIKE patterns like the dog/owner search above. These
# are infix matches, so they scan the breed table — measured at a few ms for
# 50k rows, ~200ms for the broadest breed-name queries, on a rate-limited
# endpoint. No index helps a %substring% LIKE; revisit with FTS5 if it grows.

def _variant_like_patterns(variants, min_length=1):
    patterns = []
    for variant in variants or []:
        for pattern in _like_patterns(variant, min_length=min_length):
            if pattern not in patterns:
                patterns.append(pattern)
    return patterns


def _like_any(column, patterns):
    return or_(*[column.like(pattern, escape="\\") for pattern in patterns])


def search_breeds_by_name(session, variants):
    """Breeds whose name matches: [(show_id, breed_dict)], breed-list order."""
    patterns = _variant_like_patterns(variants)
    if not patterns:
        return []
    rows = session.execute(
        select(*_BREED_COLUMNS)
        .where(_like_any(DogBreed.name, patterns))
        .order_by(DogBreed.show_id, DogBreed.position)
    )
    return [(row.show_id, _breed_to_dict(row)) for row in rows]


def search_breeds_by_judge(session, variants):
    """Breeds whose judge matches and whose name does not: [(show_id, breed_dict)].

    The name exclusion mirrors the per-breed precedence in search assembly — a
    breed-name match outranks and swallows a judge match on the same breed."""
    patterns = _variant_like_patterns(variants)
    if not patterns:
        return []
    rows = session.execute(
        select(*_BREED_COLUMNS)
        .where(
            _like_any(DogBreed.judge, patterns),
            ~_like_any(DogBreed.name, patterns),
        )
        .order_by(DogBreed.show_id, DogBreed.position)
    )
    return [(row.show_id, _breed_to_dict(row)) for row in rows]


def search_show_ids(session, variants):
    """Ids of shows whose combined name/title/date/month text matches."""
    patterns = _variant_like_patterns(variants)
    if not patterns:
        return []
    show_text = (
        func.coalesce(DogShow.name, "") + " " + func.coalesce(DogShow.title, "")
        + " " + func.coalesce(DogShow.date, "") + " " + func.coalesce(DogShow.month, "")
    )
    rows = session.execute(select(DogShow.id).where(_like_any(show_text, patterns)))
    return [row[0] for row in rows]


def indexed_show_ids(session, show_ids):
    """Which of the given ids exist in the show index (as a set of ints)."""
    ids = []
    for sid in show_ids or []:
        try:
            ids.append(int(sid))
        except (TypeError, ValueError):
            continue
    if not ids:
        return set()
    return {row[0] for row in session.execute(select(DogShow.id).where(DogShow.id.in_(ids)))}


# ---------------------------------------------------------------------------
# One-off sweeps (scripts/dog_sweep_breed_judges.py)
# ---------------------------------------------------------------------------
# Fold result-capture state into the breed index wherever older code paths left
# gaps (judges and result flags used to be healed lazily during GETs; the read
# paths are now read-only, so the historical gaps are closed once by sweeping).

def _result_breed_correlation():
    return (
        (DogResult.show_id == DogBreed.show_id)
        & (DogResult.fci_group == DogBreed.fci_group)
        & (DogResult.breed_id == DogBreed.breed_id)
    )


def sweep_breed_judges_from_results(session):
    """Copy the judge from captured result rows onto index breeds missing one.
    Returns the number of breed rows updated."""
    judge_present = _result_breed_correlation() & DogResult.breed_judge.is_not(None) & (DogResult.breed_judge != "")
    judge_subq = (
        select(DogResult.breed_judge)
        .where(judge_present)
        .order_by(DogResult.seq.desc())
        .limit(1)
        .scalar_subquery()
    )
    return session.execute(
        update(DogBreed)
        .where(or_(DogBreed.judge.is_(None), DogBreed.judge == ""))
        .where(exists(select(DogResult.id).where(judge_present)))
        .values(judge=judge_subq)
    ).rowcount


def sweep_breed_judges_from_cache_meta(session):
    """Copy judges recorded only in completed_breeds cache meta (a zero-result
    breed has a judged page but no result rows) onto index breeds missing one.
    Returns the number of breed rows updated."""
    updated = 0
    for cache_row in session.execute(select(DogResultCache.show_id, DogResultCache.meta)):
        if not cache_row.meta:
            continue
        try:
            meta = json.loads(cache_row.meta)
        except (ValueError, TypeError):
            continue
        for key, breed_data in (meta.get("completed_breeds") or {}).items():
            if not isinstance(breed_data, dict) or ":" not in str(key):
                continue
            judge = breed_data.get("judge")
            if not judge:
                continue
            group, _, bid = str(key).partition(":")
            updated += set_breed_judge(
                session, cache_row.show_id, group, bid, judge, only_missing=True,
            )
    return updated


def sweep_breed_result_flags(session):
    """Flag index breeds that have captured result rows but has_results=False.
    Returns the number of breed rows updated."""
    return session.execute(
        update(DogBreed)
        .where(DogBreed.has_results.is_(False))
        .where(exists(select(DogResult.id).where(_result_breed_correlation())))
        .values(has_results=True)
    ).rowcount


# ---------------------------------------------------------------------------
# Result jobs  (<-> dog_result_jobs.json)
# ---------------------------------------------------------------------------

def write_jobs(session, jobs_doc):
    session.execute(delete(DogResultJob))
    for sid, job in (jobs_doc.get("jobs") or {}).items():
        session.merge(DogResultJob(
            show_id=int(sid),
            state=job.get("state"),
            reason=job.get("reason"),
            attempts=int(job.get("attempts") or 0),
            created_at=job.get("created_at"),
            updated_at=job.get("updated_at"),
            requested_at=job.get("requested_at"),
            next_attempt_at=job.get("next_attempt_at"),
            last_started_at=job.get("last_started_at"),
            last_error=job.get("last_error"),
        ))
    set_meta(session, "jobs_updated_at", jobs_doc.get("updated_at") or 0)


def _job_to_dict(row):
    job = {"show_id": row.show_id}
    for field in _JOB_FIELDS:
        value = getattr(row, field)
        if value is not None:
            job[field] = value
    return job


def read_jobs(session):
    jobs = {
        str(row.show_id): _job_to_dict(row)
        for row in session.execute(select(DogResultJob)).scalars()
    }
    return {"jobs": jobs, "updated_at": get_meta_number(session, "jobs_updated_at", 0)}


# ---------------------------------------------------------------------------
# Small key/value meta
# ---------------------------------------------------------------------------

def set_meta(session, key, value):
    session.merge(DogMeta(key=key, value=json.dumps(value)))


def get_meta_number(session, key, default=0):
    row = session.get(DogMeta, key)
    if row is None or row.value is None:
        return default
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return default
