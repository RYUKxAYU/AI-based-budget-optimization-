"""
models/feature_selection.py
============================
Recursive Feature Elimination (RFE) for identifying the most
predictive features for AQI forecasting.
"""

import pandas as pd
import numpy as np
from sklearn.feature_selection import RFE
from sklearn.ensemble import RandomForestRegressor
from pathlib import Path
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RF_PARAMS, N_RFE_FEATURES, RANDOM_SEED

logger = logging.getLogger(__name__)


def select_features_rfe(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_features: int = N_RFE_FEATURES,
) -> tuple:
    """
    Use Recursive Feature Elimination to select the top N features.

    Parameters
    ----------
    X_train    : Training feature matrix
    y_train    : Training target
    n_features : Number of features to select

    Returns
    -------
    Tuple of:
      - selected_features (List[str])
      - rfe_support_df (pd.DataFrame): All features with selected flag + ranking
    """
    logger.info(f"[RFE] Running feature selection: top {n_features} from {X_train.shape[1]} features…")

    estimator = RandomForestRegressor(
        n_estimators=50,           # Fast estimator for RFE
        max_depth=10,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    rfe = RFE(estimator=estimator, n_features_to_select=n_features, step=3)
    rfe.fit(X_train, y_train)

    support_df = pd.DataFrame({
        "feature":  X_train.columns,
        "selected": rfe.support_,
        "ranking":  rfe.ranking_,
    }).sort_values("ranking")

    selected = support_df[support_df["selected"]]["feature"].tolist()
    logger.info(f"[RFE] Selected features: {selected}")

    return selected, support_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.data_loader import load_data
    from preprocessing.feature_engineering import engineer_features

    df = load_data()
    df_fe, target, features = engineer_features(df)
    X = df_fe[features]
    y = df_fe[target]

    selected, report = select_features_rfe(X, y)
    print(f"\nTop {N_RFE_FEATURES} selected features:")
    print(report[report["selected"]])
