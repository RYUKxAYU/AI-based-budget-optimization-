"""
services/api/routes/optimize.py
================================
Budget optimization endpoints.

GET  /optimize          — Run full optimization with default settings
POST /optimize          — Run optimization with custom budget/intensity
POST /simulate          — Simulate a specific policy
GET  /simulate/all      — Simulate all policies
"""

from fastapi import APIRouter, HTTPException, status
from services.api.schemas import (
    OptimizeRequest, OptimizeResponse, AllocationItem,
    PolicySimulationRequest, PolicySimulationResult, SimulateAllResponse,
    ErrorResponse,
)
from services.api.logger import get_logger
from services.api.ml_service import get_model, get_reference_data

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Optimization"])


def _get_model_and_data():
    """Shared guard: ensure model + data are loaded before any ML call."""
    model = get_model()
    data  = get_reference_data()

    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model not loaded. Run the training pipeline first: "
                   "cd green_budget_optimizer && python main.py"
        )
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reference dataset not available. Run the training pipeline first."
        )
    return model, data


# ── POST /api/v1/optimize ─────────────────────────────────────────────────────

@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Run greedy budget optimization",
    responses={503: {"model": ErrorResponse}},
)
async def optimize_budget(req: OptimizeRequest):
    """
    Run the greedy budget optimization algorithm.

    - Simulates all policy scenarios at the given `intensity`
    - Ranks policies by AQI improvement per ₹ Crore
    - Greedily allocates `total_budget_crore` to maximize AQI improvement

    Returns the optimal allocation with per-policy breakdown.
    """
    logger.info(f"[Optimize] budget={req.total_budget_crore}Cr intensity={req.intensity}")

    try:
        model, data = _get_model_and_data()
        X_train = data["X_train"]

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "green_budget_optimizer"))

        from policy.policy_simulator import PolicySimulator
        from optimization.budget_optimizer import compute_policy_rankings, greedy_budget_allocation

        simulator = PolicySimulator(model, X_train)
        rankings   = compute_policy_rankings(simulator, total_budget=req.total_budget_crore)
        result     = greedy_budget_allocation(rankings, total_budget=req.total_budget_crore)

        allocation = [
            AllocationItem(**row.to_dict())
            for _, row in result["allocation_df"].iterrows()
        ]

        logger.info(f"[Optimize] Total AQI improvement: {result['total_aqi_improvement']}")

        return OptimizeResponse(
            total_budget_crore=result["total_budget"],
            total_aqi_improvement=result["total_aqi_improvement"],
            remaining_budget=result["remaining_budget"],
            allocation=allocation,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Optimize] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )


# ── GET /api/v1/optimize ──────────────────────────────────────────────────────

@router.get(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Run optimization with default settings (1000 Cr budget)",
)
async def optimize_budget_default():
    """Quick optimization with default budget (₹1000 Crore, full intensity)."""
    return await optimize_budget(OptimizeRequest())


# ── POST /api/v1/simulate ─────────────────────────────────────────────────────

@router.post(
    "/simulate",
    response_model=PolicySimulationResult,
    summary="Simulate a single policy scenario",
)
async def simulate_policy(req: PolicySimulationRequest):
    """
    Simulate the AQI impact of a single policy.

    **Available policies:**
    - `EV_Adoption`
    - `Industrial_Regulation`
    - `Renewable_Energy`
    - `Waste_Management`
    - `Green_Public_Transport`
    - `Combined_All`
    """
    logger.info(f"[Simulate] policy={req.policy} intensity={req.intensity}")

    try:
        model, data = _get_model_and_data()

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "green_budget_optimizer"))

        from policy.policy_simulator import PolicySimulator

        simulator = PolicySimulator(model, data["X_train"])
        result    = simulator.simulate_policy(req.policy, intensity=req.intensity)

        logger.info(f"[Simulate] {req.policy}: AQI delta = {result['aqi_delta']:.2f}")
        return PolicySimulationResult(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[Simulate] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/v1/simulate/all ──────────────────────────────────────────────────

@router.get(
    "/simulate/all",
    response_model=SimulateAllResponse,
    summary="Simulate all policy scenarios",
)
async def simulate_all_policies():
    """Run all 6 policy scenarios and return ranked results."""
    logger.info("[Simulate] Running all policies")

    try:
        model, data = _get_model_and_data()

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "green_budget_optimizer"))

        from policy.policy_simulator import PolicySimulator

        simulator = PolicySimulator(model, data["X_train"])
        df        = simulator.simulate_all_policies(intensity=1.0)

        results = [
            PolicySimulationResult(**row.to_dict())
            for _, row in df.iterrows()
        ]

        return SimulateAllResponse(results=results, total_policies=len(results))

    except Exception as e:
        logger.exception(f"[Simulate/All] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
