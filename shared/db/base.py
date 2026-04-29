"""
shared/db/base.py
==================
SQLAlchemy engine + session factory.

Uses SQLite for Phase 1.  To migrate to PostgreSQL later, change only
DATABASE_URL in the .env file — no code changes required.

NEVER call Base.metadata.create_all() — use Alembic migrations instead.
"""

import os
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Database URL ─────────────────────────────────────────────────────────────
# Default: SQLite file at project-root/data/app.db
_default_url = "sqlite:///" + str(
    Path(__file__).parent.parent.parent / "data" / "app.db"
)
DATABASE_URL = os.getenv("DATABASE_URL", _default_url)

logger.info(f"[DB] Connecting to: {DATABASE_URL}")

# ─── Engine ───────────────────────────────────────────────────────────────────
# connect_args only needed for SQLite (thread-safety workaround)
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,          # Set True to log all SQL statements during debugging
)

# ─── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ─── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    All ORM models inherit from this Base.
    Written to be 100% PostgreSQL-compatible:
      - UUIDs stored as String(36)
      - JSON columns use SQLAlchemy's JSON type (supported by both SQLite & PG)
      - No SQLite-specific type hacks
    """
    pass


# ─── FastAPI dependency helper ────────────────────────────────────────────────
def get_db():
    """
    Yield a SQLAlchemy session and close it after the request.
    Use as a FastAPI dependency: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
