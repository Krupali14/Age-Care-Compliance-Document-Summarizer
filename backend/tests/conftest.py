import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Auth rate limits are process-global, so one test's logins would otherwise
    count against the next test's."""
    from app.rate_limit import clear

    clear()
    yield
    clear()


@pytest.fixture()
def session_local():
    """Sessionmaker bound to a single in-memory SQLite engine, shared by every
    fixture in a test so the client's requests, background tasks, and direct
    db writes all see the same tables (StaticPool keeps one connection alive)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture()
def client(session_local):
    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(session_local):
    """A session bound to the SAME engine the `client` fixture's endpoints
    read/write through, so tests can seed/inspect rows without going through
    the production `app.database.SessionLocal`."""
    db = session_local()
    try:
        yield db
    finally:
        db.close()
