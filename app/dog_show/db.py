"""Standalone SQLAlchemy engine + session for the /dog persistent database.

Dog data lives in its own SQLite file (`dog.db`), separate from the main
`site.db`. We deliberately do NOT use the Flask-SQLAlchemy `db` object here:
dog writes happen in background warmup threads and in the standalone
`scripts/dog_crawl.py` process, neither of which has a Flask app/request
context. A plain engine with a thread-local scoped session works identically in
web requests, worker threads, and the crawler process.

This is a permanent store, not a cache: historical rows are never evicted.
"""

import contextlib

import structlog
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .config import DOG_DATABASE_URI

logger = structlog.get_logger(__name__)

Base = declarative_base()

# Module-level engine/session, rebindable so tests can point at an isolated DB.
_engine = None
_Session = None
_current_uri = None


def _make_engine(uri):
    connect_args = {}
    if uri.startswith("sqlite"):
        # Sessions are used across threads (warmup workers, bg indexer), so the
        # single connection must not enforce same-thread access.
        connect_args["check_same_thread"] = False
    engine = create_engine(uri, future=True, connect_args=connect_args)

    if uri.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            # WAL lets the web process read while the crawler writes; a busy
            # timeout serializes the occasional concurrent writer politely.
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def configure(uri=None):
    """(Re)bind the engine/session to a database URL. Idempotent per URL."""
    global _engine, _Session, _current_uri
    uri = uri or DOG_DATABASE_URI
    if _engine is not None and uri == _current_uri:
        return _engine
    if _Session is not None:
        _Session.remove()
    if _engine is not None:
        _engine.dispose()
    _engine = _make_engine(uri)
    _Session = scoped_session(sessionmaker(bind=_engine, future=True, expire_on_commit=False))
    _current_uri = uri
    return _engine


def get_engine():
    if _engine is None:
        configure()
    return _engine


def get_session():
    """Thread-local session. Callers should use session_scope() for writes."""
    if _Session is None:
        configure()
    return _Session()


def init_db(uri=None):
    """Create dog tables if missing. Safe to call repeatedly; never drops."""
    configure(uri)
    # Import models for their side effect of registering on Base.metadata.
    from . import models  # noqa: F401
    Base.metadata.create_all(get_engine())
    logger.info("dog_db_initialized", uri=_current_uri)


@contextlib.contextmanager
def session_scope():
    """Transactional scope around a series of operations."""
    if _Session is None:
        configure()
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _Session.remove()
