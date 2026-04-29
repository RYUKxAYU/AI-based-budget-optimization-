"""
shared/db/models.py
====================
All ORM models for the AI Budget Optimizer microservices platform.

Design constraints (as per architecture spec):
  - UUID primary keys stored as String(36) — compatible with both SQLite and PostgreSQL
  - JSON columns use SQLAlchemy's generic JSON type — no SQLite-specific hacks
  - All datetime columns use timezone-naive UTC (switch to timezone=True for PG)
  - Foreign keys are enforced at ORM level; SQLite FK enforcement needs PRAGMA

Services that own each model:
  User         ← auth-service
  Budget       ← auth-service / frontend write, all services read
  Dataset      ← data-service
  Prediction   ← model-service
  Optimization ← optimization-service
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.types import JSON

from .base import Base


def _uuid() -> str:
    """Generate a new UUID4 as a string (primary key factory)."""
    return str(uuid.uuid4())


def _now() -> datetime:
    """Return current UTC datetime (timezone-naive for SQLite compat)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─── User ─────────────────────────────────────────────────────────────────────
class User(Base):
    """
    Represents a registered user.
    Owned by: auth-service
    """
    __tablename__ = "users"

    id           = Column(String(36), primary_key=True, default=_uuid)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at   = Column(DateTime, default=_now, nullable=False)

    __table_args__ = (
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


# ─── Budget ───────────────────────────────────────────────────────────────────
class Budget(Base):
    """
    A budget submission by a user.

    income    : Monthly income (float)
    expenses  : Dict of category → amount  e.g. {"Rent": 15000, "Food": 5000}
    goals     : Dict of goal name → value  e.g. {"SaveForCar": 100000}

    Owned by: frontend-service (write), all services (read)
    """
    __tablename__ = "budgets"

    id         = Column(String(36), primary_key=True, default=_uuid)
    user_id    = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    income     = Column(Float, nullable=False)
    expenses   = Column(JSON, nullable=False, default=dict)   # category → amount dict
    goals      = Column(JSON, nullable=False, default=dict)   # goal → value dict
    created_at = Column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Budget id={self.id} user_id={self.user_id} income={self.income}>"


# ─── Dataset ──────────────────────────────────────────────────────────────────
class Dataset(Base):
    """
    A dataset used for model training or evaluation.

    source_type : "synthetic" | "uploaded" | "scraped"
    file_path   : Absolute or relative path to the CSV/Parquet file on disk

    Owned by: data-service
    """
    __tablename__ = "datasets"

    id          = Column(String(36), primary_key=True, default=_uuid)
    source_type = Column(String(50), nullable=False)   # synthetic | uploaded | scraped
    file_path   = Column(String(512), nullable=False)
    created_at  = Column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} source={self.source_type}>"


# ─── Prediction ───────────────────────────────────────────────────────────────
class Prediction(Base):
    """
    An AQI / budget prediction produced by the ML model.

    predicted_allocation : Dict of category → allocated amount
                           e.g. {"EV_Adoption": 400, "Renewable_Energy": 200}
    confidence_score     : Model confidence (R² or probability-derived, 0–1)

    Owned by: model-service
    """
    __tablename__ = "predictions"

    id                   = Column(String(36), primary_key=True, default=_uuid)
    user_id              = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    budget_id            = Column(String(36), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_allocation = Column(JSON, nullable=False, default=dict)
    confidence_score     = Column(Float, nullable=False, default=0.0)
    created_at           = Column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Prediction id={self.id} confidence={self.confidence_score}>"


# ─── Optimization ─────────────────────────────────────────────────────────────
class Optimization(Base):
    """
    The output of the greedy budget optimization algorithm.

    optimized_budget      : Dict of policy → allocated ₹ Crore
                            e.g. {"EV_Adoption": 400, "Waste_Management": 100}
    constraints_applied   : Dict of constraint name → value used during run
                            e.g. {"total_budget_crore": 1000, "n_policies": 5}
    improvement_score     : Expected AQI reduction (float, in AQI units)

    Owned by: optimization-service
    """
    __tablename__ = "optimizations"

    id                  = Column(String(36), primary_key=True, default=_uuid)
    prediction_id       = Column(String(36), ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True)
    optimized_budget    = Column(JSON, nullable=False, default=dict)
    constraints_applied = Column(JSON, nullable=False, default=dict)
    improvement_score   = Column(Float, nullable=False, default=0.0)
    created_at          = Column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Optimization id={self.id} improvement={self.improvement_score}>"
