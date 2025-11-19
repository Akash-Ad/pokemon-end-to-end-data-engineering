"""
The database engine and session management are defined here, along with helpers to create or drop the schema.
"""
from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from .config import DB_URL


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def get_engine(echo: bool = False) -> Engine:
    """Return a SQLAlchemy engine configured for the project."""
    connect_args = {"check_same_thread": False} if _is_sqlite(DB_URL) else {}
    engine = create_engine(DB_URL, echo=echo, future=True, connect_args=connect_args)

    # Foreign key enforcement is enabled for SQLite connections.
    if _is_sqlite(DB_URL):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine

# A single session factory is prepared for general use.
SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)

@contextmanager
def session_scope() -> Iterator:
    """
    Context manager that manages a database session lifecycle.
    It commits on success and rolls back on failure.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def create_schema(echo: bool = False) -> None:
    """
    Create all tables defined in models if they do not exist.
    """
    from .models import Base
    engine = get_engine(echo=echo)
    Base.metadata.create_all(engine)


def drop_schema(echo: bool = False) -> None:
    """Drop all tables defined in models."""
    from .models import Base
    engine = get_engine(echo=echo)
    Base.metadata.drop_all(engine)