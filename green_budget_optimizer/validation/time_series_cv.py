"""
validation/time_series_cv.py
==============================
Time-series safe cross-validation using TimeSeriesSplit.

Key design:
  - Splits respect temporal order (future data never leaks into training)
  - Reports per-fold R², MAE, RMSE
  - Summary stats: mean, std, min, max R²
  - Instability detection for high-variance folds
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from pathlib import Path
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import N_CV_SPLITS, RF_PARAMS

logger = logging.getLogger(__name__)


def run_time_series_cv(
    X: pd.DataFrame,
    y: pd.Series,
    model_params: dict = None,
    n_splits: int = N_CV_SPLITS,
    verbose: bool = True,
) -> dict:
    """
    Perform TimeSeriesSplit cross-validation on AQI prediction.

    Parameters
    ----------
    X           : Feature matrix (already ordered by time)
    y           : Target AQI vector
    model_params: RF parameter dict (defaults to config.RF_PARAMS)
    n_splits    : Number of CV folds
    verbose     : Print per-fold results

    Returns
    -------
    dict with keys:
      - fold_results (pd.DataFrame): per-fold metrics
      - mean_r2, std_r2, min_r2, max_r2 (float)
      - instability_flag (bool): True if std_r2 > 0.10
    """
    params = model_params or RF_PARAMS
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_records = []

    if verbose:
        print(f"\n[TimeSeriesCV] Running {n_splits}-fold cross-validation…")
        print(f"  Dataset size: {len(X):,} samples | Features: {X.shape[1]}")
        print("  " + "─" * 60)

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X), start=1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model = RandomForestRegressor(**params)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)

        r2   = r2_score(y_val, y_pred)
        mae  = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))

        fold_records.append({
            "fold":          fold_idx,
            "train_samples": len(train_idx),
            "val_samples":   len(val_idx),
            "r2":            round(r2, 4),
            "mae":           round(mae, 2),
            "rmse":          round(rmse, 2),
        })

        if verbose:
            bar = "█" * int(max(r2, 0) * 20)
            print(f"  Fold {fold_idx}: R²={r2:+.4f}  MAE={mae:.1f}  RMSE={rmse:.1f}"
                  f"  [train={len(train_idx):,} / val={len(val_idx):,}]  {bar}")

    fold_df = pd.DataFrame(fold_records)
    r2_scores = fold_df["r2"].values

    summary = {
        "fold_results":      fold_df,
        "mean_r2":           round(float(np.mean(r2_scores)), 4),
        "std_r2":            round(float(np.std(r2_scores)), 4),
        "min_r2":            round(float(np.min(r2_scores)), 4),
        "max_r2":            round(float(np.max(r2_scores)), 4),
        "instability_flag":  bool(np.std(r2_scores) > 0.10),
    }

    if verbose:
        print("  " + "─" * 60)
        print(f"  CV Summary: Mean R²={summary['mean_r2']:.4f} "
              f"± {summary['std_r2']:.4f}  "
              f"[Min={summary['min_r2']:.4f}, Max={summary['max_r2']:.4f}]")
        if summary["instability_flag"]:
            print("  ⚠ HIGH INSTABILITY DETECTED (std > 0.10) — "
                  "typical during winter pollution spikes. Consistent with paper findings.")

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.data_loader import load_data
    from preprocessing.feature_engineering import engineer_features
    from models.feature_selection import select_features_rfe

    df = load_data()
    df_fe, target, features = engineer_features(df)
    X = df_fe[features]
    y = df_fe[target]

    selected, _ = select_features_rfe(X, y)
    cv_results = run_time_series_cv(X[selected], y)
    print(f"\nFold results:\n{cv_results['fold_results']}")
