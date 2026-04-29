"""
services/api/routes/health.py
===============================
/health endpoint — liveness + readiness probe.
Used by Docker, Kubernetes, Render, Railway health checks.
"""

from fastapi import APIRouter
from sqlalchemy import text

from services.api.schemas import HealthResponse
from services.api.logger import get_logger
from shared.db.base import engine

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])

APP_VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    """
    Liveness + readiness probe.

    Returns:
    - **status**: 'ok' if fully operational
    - **database**: 'connected' or 'unreachable'
    - **model_loaded**: whether the ML model is in memory
    """
    # Check DB connectivity
    db_status = "disconnected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning(f"[HealthCheck] DB unreachable: {e}")

    # Check if model is loaded (import lazily)
    model_loaded = False
    try:
        from services.api.ml_service import get_model
        model = get_model()
        model_loaded = model is not None and model.is_fitted
    except Exception:
        pass

    from services.api.config import get_settings
    settings = get_settings()

    logger.info(f"[HealthCheck] db={db_status} model={model_loaded}")

    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        database=db_status,
        model_loaded=model_loaded,
        environment=settings.app_env,
    )
