"""
services/api/schemas.py
========================
Pydantic request/response schemas for all API endpoints.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    version: str = Field(..., example="1.0.0")
    database: str = Field(..., example="connected")
    model_loaded: bool = Field(..., example=True)
    environment: str = Field(..., example="production")


# ─── Policy Simulation ────────────────────────────────────────────────────────

class PolicySimulationRequest(BaseModel):
    policy: str = Field(
        ...,
        example="EV_Adoption",
        description="Policy name. Options: EV_Adoption, Industrial_Regulation, "
                    "Renewable_Energy, Waste_Management, Green_Public_Transport, Combined_All"
    )
    intensity: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        example=1.0,
        description="Policy strength from 0.0 (no effect) to 1.0 (full effect)"
    )


class PolicySimulationResult(BaseModel):
    policy: str
    description: str
    baseline_aqi: float
    simulated_aqi: float
    aqi_delta: float
    pct_improvement: float


class SimulateAllResponse(BaseModel):
    results: List[PolicySimulationResult]
    total_policies: int


# ─── Budget Optimization ──────────────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    total_budget_crore: float = Field(
        default=1000.0,
        gt=0,
        example=1000.0,
        description="Total green budget available in Indian Rupees Crore"
    )
    intensity: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        example=1.0,
        description="Policy simulation intensity"
    )


class AllocationItem(BaseModel):
    rank: int
    policy: str
    allocated_crore: float
    aqi_improvement: float
    efficiency: float
    pct_of_budget: float


class OptimizeResponse(BaseModel):
    total_budget_crore: float
    total_aqi_improvement: float
    remaining_budget: float
    allocation: List[AllocationItem]
    message: str = "Budget optimization complete"


# ─── AQI Prediction ───────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    city: Optional[str] = Field(
        default=None,
        example="Delhi",
        description="Filter predictions to a specific city. Leave null for all cities."
    )


class PredictResponse(BaseModel):
    city: str
    mean_predicted_aqi: float
    test_r2: float
    test_mae: float
    test_rmse: float
    model_version: str


# ─── Error ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int
