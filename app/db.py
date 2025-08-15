import os
from typing import Optional
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.engine import Engine
from .config import settings

# Lazily create engine so that test environment variables are available
engine: Optional[Engine] = None
_initialized = False


def _compute_db_url() -> str:
    # Use a separate database for tests to avoid polluting local data
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("PYTEST") or os.getenv("TESTING") == "1":
        return "sqlite:///./app_test.db"
    return settings.database_url


def init_db():
    global _initialized
    global engine
    if engine is None:
        engine = create_engine(_compute_db_url(), echo=False)
    if not _initialized:
        SQLModel.metadata.create_all(engine)
        _initialized = True


def get_session():
    # lazy init in case app lifespan wasn't run (e.g., tests creating TestClient without context)
    init_db()
    assert engine is not None
    with Session(engine) as session:
        yield session
