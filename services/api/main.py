"""
services/api/main.py
=====================
FastAPI application entry point — AI Based Green Budget Optimizer API.

Architecture: Hybrid (CLI pipeline + REST API)
  - CLI: python green_budget_optimizer/main.py  (training + batch)
  - API: uvicorn services.api.main:app          (inference + optimization)

Endpoints:
  GET  /health              — Liveness + readiness probe
  GET  /api/v1/optimize     — Run optimization (default budget)
  POST /api/v1/optimize     — Run optimization (custom budget)
  POST /api/v1/simulate     — Simulate single policy
  GET  /api/v1/simulate/all — Simulate all policies
  GET  /docs                — Interactive Swagger UI
  GET  /redoc               — ReDoc documentation
"""

import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ─── Path setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "green_budget_optimizer"))

from services.api.config import get_settings
from services.api.logger import get_logger
from services.api.routes import health, optimize

settings = get_settings()
logger   = get_logger(__name__)


# ─── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: pre-load the ML model into memory (warm cache).
    Shutdown: log graceful stop.
    """
    logger.info("=" * 60)
    logger.info("  AI Green Budget Optimizer API — Starting up")
    logger.info(f"  Environment : {settings.app_env}")
    logger.info(f"  DB          : {settings.database_url[:40]}...")
    logger.info("=" * 60)

    # Pre-load model on startup so first request isn't slow
    try:
        from services.api.ml_service import get_model, get_reference_data
        model = get_model()
        data  = get_reference_data()
        if model:
            logger.info(f"[Startup] Model loaded — {len(model.features)} features")
        else:
            logger.warning("[Startup] Model not found. Run training pipeline first.")
        if data:
            logger.info(f"[Startup] Reference data ready — {data['X_train'].shape[0]:,} training rows")
    except Exception as e:
        logger.warning(f"[Startup] Could not pre-load model: {e}")

    logger.info("[Startup] API ready to serve requests")
    yield

    logger.info("[Shutdown] AI Green Budget Optimizer API stopped gracefully")


# ─── App factory ──────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Based Green Budget Optimizer",
        description=(
            "REST API for AQI forecasting, environmental policy simulation, "
            "and AI-driven green budget optimization across Indian cities.\n\n"
            "**Research paper:** AI Based Green Budget Optimizer\n\n"
            "**Tech stack:** FastAPI · scikit-learn · PostgreSQL · SQLAlchemy · Docker"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    origins = ["*"] if not settings.is_production else [
        "https://your-frontend-domain.com"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timing middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def add_process_time(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} ({elapsed:.1f}ms)"
        )
        return response

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc), "status_code": 500},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(optimize.router)

    # ── Root redirect ─────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "AI Green Budget Optimizer API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()


# ─── Dev server ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )
