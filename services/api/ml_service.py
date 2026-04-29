"""
services/api/ml_service.py
===========================
ML model loading & inference service layer.
Loads the trained AQIForestModel once at startup (singleton pattern).
All routes call functions here — no ML code inside route handlers.
"""

import sys
from pathlib import Path
from functools import lru_cache

# Make green_budget_optimizer importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "green_budget_optimizer"))

from services.api.logger import get_logger
from services.api.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def get_model():
    """
    Load and cache the trained AQIForestModel.
    Uses lru_cache so the model is only loaded once per process.
    """
    from models.random_forest_model import AQIForestModel

    model_path = settings.model_path_resolved
    if not model_path.exists():
        # Try default output path
        model_path = PROJECT_ROOT / "green_budget_optimizer" / "outputs" / "aqi_forest_model.pkl"

    if not model_path.exists():
        logger.warning(f"[MLService] Model file not found at {model_path}. "
                       "Run the training pipeline first: python green_budget_optimizer/main.py")
        return None

    try:
        model = AQIForestModel.load(model_path.name)
        logger.info(f"[MLService] Model loaded from {model_path} "
                    f"(features: {len(model.features)})")
        return model
    except Exception as e:
        logger.error(f"[MLService] Failed to load model: {e}")
        return None


@lru_cache(maxsize=1)
def get_reference_data():
    """
    Load the processed training dataset (used for policy simulation baseline).
    Cached after first load.
    """
    import pandas as pd

    data_path = PROJECT_ROOT / "green_budget_optimizer" / "data" / "processed_dataset.csv"
    if not data_path.exists():
        data_path = PROJECT_ROOT / "green_budget_optimizer" / "data" / "synthetic_dataset.csv"

    if not data_path.exists():
        logger.warning("[MLService] No dataset found. Run main.py to generate data first.")
        return None

    try:
        from data.data_loader import load_data
        from preprocessing.feature_engineering import engineer_features
        from models.feature_selection import select_features_rfe

        df = load_data()
        df_fe, target_col, feature_cols = engineer_features(df)

        X = df_fe[feature_cols]
        y = df_fe[target_col]

        # Use same feature set as the saved model
        model = get_model()
        if model and model.features:
            # Filter to only features the model knows
            available = [f for f in model.features if f in X.columns]
            X = X[available]

        split = int(len(X) * 0.8)
        X_train = X.iloc[:split]
        y_train = y.iloc[:split]
        X_test  = X.iloc[split:]
        y_test  = y.iloc[split:]

        logger.info(f"[MLService] Reference data loaded: {X_train.shape}")
        return {
            "X_train": X_train,
            "y_train": y_train,
            "X_test":  X_test,
            "y_test":  y_test,
            "feature_cols": list(X_train.columns),
        }
    except Exception as e:
        logger.error(f"[MLService] Failed to load reference data: {e}")
        return None
