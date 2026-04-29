"""
models/random_forest_model.py
==============================
RandomForestRegressor wrapper for AQI prediction.

Designed for:
  - Time-series safe training (no data leakage)
  - Feature importance extraction
  - Serialization via joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from pathlib import Path
import joblib
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RF_PARAMS, OUTPUT_DIR

logger = logging.getLogger(__name__)


class AQIForestModel:
    """
    Wrapper around RandomForestRegressor for AQI prediction.

    Attributes
    ----------
    model    : Underlying RandomForestRegressor instance
    features : List of feature column names (set after fit)
    is_fitted: Whether the model has been trained
    """

    def __init__(self, params: dict = None):
        """
        Initialize the model.

        Parameters
        ----------
        params : RF hyperparameters dict. Defaults to config.RF_PARAMS.
        """
        self.params = params or RF_PARAMS
        self.model = RandomForestRegressor(**self.params)
        self.features: list = []
        self.is_fitted: bool = False

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> "AQIForestModel":
        """
        Train the Random Forest on the given data.

        Parameters
        ----------
        X_train : Feature matrix
        y_train : Target AQI values

        Returns
        -------
        self (for chaining)
        """
        self.features = list(X_train.columns)
        logger.info(f"[AQIForestModel] Training on {len(X_train):,} samples "
                    f"with {len(self.features)} features…")
        self.model.fit(X_train, y_train)
        self.is_fitted = True
        logger.info("[AQIForestModel] Training complete.")
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Generate AQI predictions.

        Parameters
        ----------
        X : Feature matrix (must match training columns)

        Returns
        -------
        np.ndarray of predicted AQI values
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict().")
        # Ensure column alignment
        X_aligned = X[self.features]
        return self.model.predict(X_aligned)

    def evaluate(self, X: pd.DataFrame, y_true: pd.Series) -> dict:
        """
        Evaluate model and return metrics dict.

        Returns
        -------
        dict with keys: r2, mae, rmse
        """
        y_pred = self.predict(X)
        return {
            "r2":   round(r2_score(y_true, y_pred), 4),
            "mae":  round(mean_absolute_error(y_true, y_pred), 2),
            "rmse": round(np.sqrt(mean_squared_error(y_true, y_pred)), 2),
        }

    def get_feature_importances(self, top_n: int = 20) -> pd.DataFrame:
        """
        Return sorted feature importances.

        Parameters
        ----------
        top_n : Number of top features to return

        Returns
        -------
        pd.DataFrame with columns ['feature', 'importance']
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first.")
        importances = self.model.feature_importances_
        df = pd.DataFrame({
            "feature":    self.features,
            "importance": importances,
        }).sort_values("importance", ascending=False).head(top_n)
        df.reset_index(drop=True, inplace=True)
        return df

    def save(self, filename: str = "aqi_forest_model.pkl") -> Path:
        """Save model to outputs directory using joblib."""
        path = OUTPUT_DIR / filename
        joblib.dump(self, path)
        logger.info(f"[AQIForestModel] Model saved → {path}")
        return path

    @classmethod
    def load(cls, filename: str = "aqi_forest_model.pkl") -> "AQIForestModel":
        """Load a saved model from outputs directory."""
        path = OUTPUT_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"No saved model found at {path}")
        instance = joblib.load(path)
        logger.info(f"[AQIForestModel] Model loaded ← {path}")
        return instance

    def __repr__(self):
        status = "fitted" if self.is_fitted else "not fitted"
        return f"AQIForestModel(n_estimators={self.params.get('n_estimators')}, status={status})"
