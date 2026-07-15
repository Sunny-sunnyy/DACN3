"""SQLAlchemy engine and session factory.

Provides a FastAPI-compatible get_db dependency.
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.shared.config import DATABASE_URL

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _build_engine() -> Engine:
    connect_args: dict[str, str | bool] = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(DATABASE_URL, connect_args=connect_args)


def get_engine() -> Engine:
    """Return the singleton SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the singleton session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def init_db() -> None:
    """Create all tables if they do not exist (SQLAlchemy create_all)."""
    from backend.database.schema import Base

    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it after use."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
