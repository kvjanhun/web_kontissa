"""Conversion between the legacy JSON shapes and the dog.db ORM rows.

This is the single source of truth for how `_show_index`, whole-show result
docs, and the result-job queue map onto SQL. The migration script and (after the
store rewrite) `store.py` both go through these helpers, so the round-trip stays
byte-for-byte faithful to what the rest of the package and `/api/dog/*` expect.
"""

import json

from sqlalchemy import delete, select

from .models import DogBreed, DogMeta, DogResult, DogResultCache, DogResultJob, DogShow
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


def write_index(session, index):
    """Replace the entire index (used by the one-off migration)."""
    session.execute(delete(DogBreed))
    session.execute(delete(DogShow))
    for sid, show in (index.get("shows") or {}).items():
        write_show(session, sid, show)
    set_meta(session, "last_updated", index.get("last_updated") or 0)


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


def read_index(session):
    """Rebuild the `{"shows": {...}, "last_updated": ts}` index dict.

    Uses Core column selects (lightweight Row objects, accessed by name exactly
    like the ORM entities) rather than full ORM instances — at ~47k breed rows
    the ORM hydration cost dominates, and this keeps the full reload close to the
    old whole-file JSON parse it replaces.
    """
    breeds_by_show = {}
    breed_cols = session.execute(
        select(
            DogBreed.show_id, DogBreed.name, DogBreed.entry_count, DogBreed.fci_group,
            DogBreed.breed_id, DogBreed.has_results, DogBreed.source_url, DogBreed.judge,
        ).order_by(DogBreed.show_id, DogBreed.position)
    )
    for row in breed_cols:
        breeds_by_show.setdefault(row.show_id, []).append(row)

    shows = {}
    show_cols = session.execute(
        select(
            DogShow.id, DogShow.title, DogShow.name, DogShow.date, DogShow.month,
            DogShow.source_url, DogShow.updated_at, DogShow.updated_at_iso,
            DogShow.empty_breed_list_confirmed,
        )
    )
    for show_row in show_cols:
        shows[str(show_row.id)] = _show_to_dict(show_row, breeds_by_show.get(show_row.id, []))

    return {"shows": shows, "last_updated": get_meta_number(session, "last_updated", 0)}


# ---------------------------------------------------------------------------
# Whole-show result doc  (<-> dog_result_cache/<id>.json)
# ---------------------------------------------------------------------------

def write_result_doc(session, show_id, doc):
    sid = int(show_id)
    session.execute(delete(DogResult).where(DogResult.show_id == sid))

    meta = {
        k: v for k, v in doc.items()
        if k not in _RESULT_DOC_PROMOTED and k not in ("results", "show_id")
    }
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
        meta=json.dumps(meta, ensure_ascii=False),
    ))

    for seq, result in enumerate(doc.get("results") or []):
        session.add(DogResult(
            show_id=sid,
            seq=seq,
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
            awards=result.get("awards", "") or "",
            critique=result.get("critique", "") or "",
            gender=result.get("gender", "") or "",
            class_name=result.get("class_name", "") or "",
        ))


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
        results.append({
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
        })
    doc["results"] = results
    return doc


def all_result_cache_show_ids(session):
    return [row[0] for row in session.execute(select(DogResultCache.show_id)).all()]


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


# ---------------------------------------------------------------------------
# Index generation counter
# ---------------------------------------------------------------------------
# A monotonic integer bumped on every index write. Each process records the
# generation it last loaded into its in-memory mirror; when the stored value
# advances (because this process or the crawler wrote), the mirror reloads. This
# replaces the file-mtime check the JSON store used for cross-process freshness.

def get_index_generation(session):
    return int(get_meta_number(session, "index_generation", 0))


def bump_index_generation(session):
    new_value = get_index_generation(session) + 1
    set_meta(session, "index_generation", new_value)
    return new_value
