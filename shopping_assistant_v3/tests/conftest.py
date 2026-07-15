"""Shared test fixtures — temp SQLite database, FastAPI TestClient."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.schema import Base


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Redirect every test to a fresh temp SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_v3_")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Rebuild engine and session factory for the temp db.
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Override the get_db dependency so all endpoints use the test session.
    from backend.api import main as api_main
    from backend.database import session as db_session

    def _test_get_db() -> Generator[Session, None, None]:
        session = TestSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Patch the FastAPI dependency override.
    api_main.app.dependency_overrides[db_session.get_db] = _test_get_db

    # Also patch the singleton engine so repository tests use test db.
    db_session._engine = engine
    db_session._SessionLocal = TestSession

    yield

    api_main.app.dependency_overrides.clear()
    Path(path).unlink(missing_ok=True)
    db_session._engine = None
    db_session._SessionLocal = None


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient pointing at the isolated test app."""
    from backend.api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Direct database session for repository-level tests."""
    from backend.database.session import get_session_factory

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
