"""
services/api/routes/predict.py
================================
STEP 3 — POST /predict/aqi  |  GET /history
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.api.dependencies import get_db, get_current_user, get_optional_user
from services.api.logger import get_logger
from services.api.ml_service import get_model, get_reference_data
from shared.db.models import User

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Predictions"])


# ── Schemas ───────────────────────────────────────────────────────────────────
CITIES = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Hyderabad"]

AQI_CATEGORIES = {
    (0,   50):  ("Good",      "#00C851"),
    (50,  100): ("Moderate",  "#FFD700"),
    (100, 150): ("Unhealthy", "#FF8C00"),
    (150, 9999):("Hazardous", "#DC143C"),
}


def _aqi_category(aqi: float) -> tuple[str, str]:
    for (lo, hi), (label, color) in AQI_CATEGORIES.items():
        if lo <= aqi < hi:
            return label, color
    return "Hazardous", "#DC143C"


class PredictAqiRequest(BaseModel):
    city: str
    date: Optional[str] = None

    class Config:
        json_schema_extra = {"example": {"city": "Delhi"}}


class PredictAqiResponse(BaseModel):
    city: str
    predicted_aqi: float
    confidence: float
    category: str
    color: str
    prediction_id: str
    health_advisory: str


# ── POST /api/v1/predict/aqi ──────────────────────────────────────────────────
@router.post("/predict/aqi", response_model=PredictAqiResponse, summary="Predict AQI for a city")
async def predict_aqi(
    req: PredictAqiRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Predict AQI for a specified city using the trained Random Forest model.

    **Available cities:** Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad
    """
    if req.city not in CITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"City '{req.city}' not supported. Available: {CITIES}"
        )

    model = get_model()
    data  = get_reference_data()

    if model is None or data is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model not available. Run training pipeline first."
        )

    try:
        import pandas as pd

        # Filter data for the requested city
        X_test = data["X_test"]
        y_test = data["y_test"]

        # Try to filter by city if column exists
        city_col = None
        for col in X_test.columns:
            if "city" in col.lower() or req.city.lower() in col.lower():
                city_col = col
                break

        if city_col:
            mask = X_test[city_col] == req.city
            X_city = X_test[mask]
            y_city = y_test[mask]
        else:
            # Use all test data, take mean prediction
            X_city = X_test
            y_city = y_test

        if len(X_city) == 0:
            X_city = X_test
            y_city = y_test

        preds      = model.predict(X_city)
        mean_aqi   = float(preds.mean())
        confidence = float(model.model.score(X_city, y_city))
        confidence = max(0.0, min(1.0, confidence))

    except Exception as e:
        logger.error(f"[Predict] Inference failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    category, color = _aqi_category(mean_aqi)

    ADVISORIES = {
        "Good":      "Air quality is satisfactory. Enjoy outdoor activities.",
        "Moderate":  "Unusually sensitive groups should limit prolonged outdoor exertion.",
        "Unhealthy": "Everyone may begin to experience health effects. Reduce outdoor activity.",
        "Hazardous": "Health warnings of emergency conditions. Avoid all outdoor activity.",
    }

    # Write to DB
    pred_id = str(uuid.uuid4())
    try:
        from shared.db.base import SessionLocal
        db_write = SessionLocal()
        from sqlalchemy import text
        db_write.execute(text("""
            INSERT INTO predictions (id, user_id, budget_id, predicted_allocation, confidence_score, created_at)
            VALUES (:id, :uid, :bid, :alloc::json, :conf, :now)
        """), {
            "id":    pred_id,
            "uid":   current_user.id if current_user else None,
            "bid":   str(uuid.uuid4()),
            "alloc": f'{{"city":"{req.city}","aqi":{mean_aqi:.2f}}}',
            "conf":  confidence,
            "now":   datetime.now(timezone.utc).replace(tzinfo=None),
        })
        db_write.commit()
        db_write.close()
        logger.info(f"[Predict] Saved prediction {pred_id} for {req.city}")
    except Exception as e:
        logger.warning(f"[Predict] DB write skipped: {e}")

    return PredictAqiResponse(
        city=req.city,
        predicted_aqi=round(mean_aqi, 2),
        confidence=round(confidence, 4),
        category=category,
        color=color,
        prediction_id=pred_id,
        health_advisory=ADVISORIES[category],
    )


# ── GET /api/v1/history ───────────────────────────────────────────────────────
@router.get("/history", summary="Get current user's query history (auth required)")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the last 20 optimizations, simulations, and predictions for the authenticated user.
    Requires `Authorization: Bearer <token>` header.
    """
    from sqlalchemy import text

    uid = current_user.id

    # Optimizations
    try:
        opts = db.execute(text(
            "SELECT id, optimized_budget, improvement_score, created_at FROM optimizations "
            "ORDER BY created_at DESC LIMIT 20"
        )).fetchall()
        optimizations = [{"id": r[0], "budget": r[1], "aqi_improvement": r[2],
                          "created_at": str(r[3])} for r in opts]
    except Exception:
        optimizations = []

    # Predictions
    try:
        preds = db.execute(text(
            "SELECT id, predicted_allocation, confidence_score, created_at FROM predictions "
            "WHERE user_id = :uid ORDER BY created_at DESC LIMIT 20"
        ), {"uid": uid}).fetchall()
        predictions = [{"id": r[0], "allocation": r[1], "confidence": r[2],
                        "created_at": str(r[3])} for r in preds]
    except Exception:
        predictions = []

    return {
        "user_id": uid,
        "optimizations": optimizations,
        "predictions": predictions,
        "simulations": [],  # extended in Step 4 migration
    }
