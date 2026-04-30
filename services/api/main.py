"""
services/api/main.py
=====================
FastAPI application — AI Based Green Budget Optimizer API.
STEP 5: Security hardening added (CORS from env, security headers, rate limits).

Endpoints:
  GET  /health              — Liveness + readiness
  POST /register            — Create account
  POST /login               — Get JWT token
  GET  /me                  — Current user profile
  GET  /api/v1/optimize     — Run optimization (default)
  POST /api/v1/optimize     — Run optimization (custom)
  POST /api/v1/simulate     — Simulate single policy
  GET  /api/v1/simulate/all — Simulate all policies
  POST /api/v1/predict/aqi  — Predict AQI for a city
  GET  /api/v1/history      — User query history (auth required)
  GET  /docs                — Swagger UI
"""

import os
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
from services.api.routes import auth, predict

settings = get_settings()
logger   = get_logger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  AI Green Budget Optimizer API — Starting up")
    logger.info(f"  Environment : {settings.app_env}")
    logger.info(f"  DB          : {settings.database_url[:40]}...")
    logger.info("=" * 60)

    try:
        from services.api.ml_service import get_model, get_reference_data
        model = get_model()
        data  = get_reference_data()
        if model:
            logger.info(f"[Startup] Model loaded — {len(model.features)} features")
        else:
            logger.warning("[Startup] Model not found. Run training pipeline first.")
        if data:
            logger.info(f"[Startup] Reference data ready — {data['X_train'].shape[0]:,} rows")
    except Exception as e:
        logger.warning(f"[Startup] Could not pre-load model: {e}")

    logger.info("[Startup] API ready")
    yield
    logger.info("[Shutdown] API stopped gracefully")


# ─── App factory ──────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Based Green Budget Optimizer",
        description=(
            "REST API for AQI forecasting, environmental policy simulation, "
            "and AI-driven green budget optimization across Indian cities.\n\n"
            "**Auth:** Use `POST /login` → copy the `access_token` → click **Authorize** above.\n\n"
            "**Tech stack:** FastAPI · scikit-learn · PostgreSQL · SQLAlchemy · Docker · Render"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS — STEP 5 ─────────────────────────────────────────────────────────
    # Read allowed origins from env (comma-separated list)
    raw_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001"
    )
    if settings.is_production:
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    else:
        origins = ["*"]   # dev: allow all

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Security headers middleware — STEP 5 ──────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

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
    app.include_router(auth.router)          # POST /register, /login, GET /me
    app.include_router(optimize.router)      # POST /api/v1/optimize, /simulate
    app.include_router(predict.router)       # POST /api/v1/predict/aqi, GET /history

    # ── Root ─────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service":   "AI Green Budget Optimizer API",
            "version":   "1.0.0",
            "docs":      "/docs",
            "health":    "/health",
            "endpoints": [
                "POST /register", "POST /login", "GET /me",
                "GET|POST /api/v1/optimize",
                "POST /api/v1/simulate", "GET /api/v1/simulate/all",
                "POST /api/v1/predict/aqi", "GET /api/v1/history",
            ],
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
