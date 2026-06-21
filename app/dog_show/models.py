"""ORM models for the /dog persistent database (dog.db).

Storage layout vs. the old JSON shapes:

- `dog_show_index.json` -> `DogShow` (per-show metadata) + `DogBreed` (breed list,
  carrying the per-breed judge that search and the detail page read). Global
  `last_updated` lives in `DogMeta`.
- `dog_result_cache/<id>.json` -> `DogResultCache` (one row per show holding the
  doc metadata + completed/failed breeds + live-tracking fields as a JSON blob)
  plus normalized `DogResult` rows (one per dog result — the part that scales to
  100k+ rows and powers cross-dog/judge queries later).
- `dog_result_jobs.json` -> `DogResultJob`.

Column names avoid SQL reserved words (`fci_group` not `group`); the store layer
maps these back to the dict keys the rest of the package expects.
"""

from sqlalchemy import (
    Boolean, Column, Float, ForeignKey, Index, Integer, Text, UniqueConstraint,
)

from .db import Base


class DogShow(Base):
    __tablename__ = "dog_show"

    id = Column(Integer, primary_key=True)  # Showlink show id (not autoincrement)
    name = Column(Text, default="")
    title = Column(Text, default="")
    date = Column(Text, default="")
    month = Column(Text, default="")
    source_url = Column(Text, default="")
    updated_at = Column(Float, default=0.0)
    updated_at_iso = Column(Text)
    empty_breed_list_confirmed = Column(Boolean, default=False, nullable=False)


class DogBreed(Base):
    __tablename__ = "dog_breed"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("dog_show.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, default=0, nullable=False)  # preserves breed-list order
    fci_group = Column(Text, default="")
    breed_id = Column(Text, default="")
    name = Column(Text, default="")
    entry_count = Column(Integer)
    has_results = Column(Boolean, default=False, nullable=False)
    judge = Column(Text)
    source_url = Column(Text, default="")

    __table_args__ = (
        UniqueConstraint("show_id", "fci_group", "breed_id", name="uq_breed_identity"),
        Index("ix_breed_judge", "judge"),
    )


class DogResult(Base):
    __tablename__ = "dog_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, ForeignKey("dog_show.id", ondelete="CASCADE"), nullable=False, index=True)
    seq = Column(Integer, default=0, nullable=False)  # preserves whole-show results order
    fci_group = Column(Text, default="")    # breedGroup
    breed_id = Column(Text, default="")     # breedId
    breed_name = Column(Text, default="")   # breedName
    number = Column(Integer)
    name = Column(Text, default="")
    reg_url = Column(Text, default="")
    reg_id = Column(Text, index=True)       # parsed from reg_url; cross-show anchor
    grade = Column(Text, default="")
    placement = Column(Integer)
    awards = Column(Text, default="")
    critique = Column(Text, default="")
    gender = Column(Text, default="")
    class_name = Column(Text, default="")

    __table_args__ = (
        Index("ix_result_breed", "show_id", "fci_group", "breed_id"),
    )


class DogResultCache(Base):
    __tablename__ = "dog_result_cache"

    show_id = Column(Integer, primary_key=True)
    version = Column(Integer)
    status = Column(Text, index=True)
    source = Column(Text)
    title = Column(Text)
    source_url = Column(Text)
    total_breeds = Column(Integer)
    started_at = Column(Float)
    updated_at = Column(Float, index=True)
    cached_at = Column(Float)
    last_error = Column(Text)
    # JSON blob: every top-level doc field except the promoted columns above and
    # `results` (which are normalized into DogResult). Holds completed_breeds,
    # failed_breeds, and all live_* tracking fields. Keeps the live-cache schema
    # free to evolve without migrations.
    meta = Column(Text)


class DogResultJob(Base):
    __tablename__ = "dog_result_job"

    show_id = Column(Integer, primary_key=True)
    state = Column(Text, index=True)
    reason = Column(Text)
    attempts = Column(Integer, default=0)
    created_at = Column(Float)
    updated_at = Column(Float)
    requested_at = Column(Float)
    next_attempt_at = Column(Float)
    last_started_at = Column(Float)
    last_error = Column(Text)


class DogMeta(Base):
    __tablename__ = "dog_meta"

    key = Column(Text, primary_key=True)
    value = Column(Text)
