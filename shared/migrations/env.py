"""
shared/migrations/env.py
=========================
Alembic environment file — runs on every 'alembic' CLI command.

Key behaviours:
  - DATABASE_URL is loaded from .env (never hardcoded)
  - All 5 ORM models are imported so autogenerate detects them
  - Works for both online (live DB) and offline (SQL script) modes
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ─── Make shared/ importable ──────────────────────────────────────────────────
# migrations/ is inside shared/migrations/, so shared/ is two levels up
SHARED_DIR = Path(__file__).parent.parent
PROJECT_ROOT = SHARED_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ─── Load .env ────────────────────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")

# ─── Import all ORM models so autogenerate can see them ──────────────────────
from shared.db.base import Base   # noqa: E402  (must be after sys.path insert)
import shared.db.models           # noqa: E402  (registers all table metadata)

# ─── Alembic Config object ───────────────────────────────────────────────────
config = context.config

# Inject DATABASE_URL from environment (overrides the blank value in alembic.ini)
_db_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + str(PROJECT_ROOT / "data" / "app.db"),
)
# configparser uses % as interpolation prefix — escape all % as %% to prevent crash
# e.g. Ayush%237897 → Ayush%%237897 (configparser reads it back as Ayush%237897)
_db_url_safe = _db_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", _db_url_safe)

# ─── Logging ─────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── Target metadata (for autogenerate) ──────────────────────────────────────
target_metadata = Base.metadata


# ─── Run migrations ───────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Outputs pure SQL that can be inspected or applied manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations against a live DB connection.
    This is the normal mode used during development and deployment.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
