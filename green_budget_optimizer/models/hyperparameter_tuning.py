"""
models/hyperparameter_tuning.py
================================
Hyperparameter tuning for the AQI RandomForest model.

Supports:
  - GridSearchCV (default)
  - BayesSearchCV (optional, requires scikit-optimize)

Uses TimeSeriesSplit to prevent data leakage during search.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from pathlib import Path
import logging
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RF_GRID, N_CV_SPLITS, RANDOM_SEED

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
    ENABLE_BAYESIAN = os.getenv("ENABLE_BAYESIAN_OPT", "false").lower() == "true"
except ImportError:
    ENABLE_BAYESIAN = False

# Optional Bayesian import
try:
    from skopt import BayesSearchCV
    from skopt.space import Integer, Real
    BAYES_AVAILABLE = True
except ImportError:
    BAYES_AVAILABLE = False


def tune_with_gridsearch(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    param_grid: dict = RF_GRID,
    n_splits: int = N_CV_SPLITS,
    verbose: int = 1,
) -> dict:
    """
    Run GridSearchCV over RF parameters using TimeSeriesSplit.

    Parameters
    ----------
    X_train    : Training feature matrix
    y_train    : Training target
    param_grid : Dict of hyperparameter grids
    n_splits   : Number of TimeSeriesSplit folds
    verbose    : Verbosity level

    Returns
    -------
    dict with keys: best_params, best_score, cv_results_df
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    estimator = RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1)

    logger.info("[GridSearchCV] Starting hyperparameter search…")
    logger.info(f"  Grid size: {_grid_size(param_grid)} combinations × {n_splits} folds")

    grid_search = GridSearchCV(
        estimator=estimator,
        param_grid=param_grid,
        cv=tscv,
        scoring="r2",
        n_jobs=-1,
        verbose=verbose,
        return_train_score=True,
    )
    grid_search.fit(X_train, y_train)

    results_df = pd.DataFrame(grid_search.cv_results_).sort_values(
        "mean_test_score", ascending=False
    )

    logger.info(f"[GridSearchCV] Best R²: {grid_search.best_score_:.4f}")
    logger.info(f"[GridSearchCV] Best params: {grid_search.best_params_}")

    return {
        "best_params":    grid_search.best_params_,
        "best_score":     round(grid_search.best_score_, 4),
        "best_estimator": grid_search.best_estimator_,
        "cv_results_df":  results_df,
    }


def tune_with_bayesian(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_iter: int = 30,
    n_splits: int = N_CV_SPLITS,
) -> dict:
    """
    Run BayesSearchCV (requires scikit-optimize).

    Parameters
    ----------
    X_train  : Training feature matrix
    y_train  : Training target
    n_iter   : Number of Bayesian optimization iterations
    n_splits : Number of TimeSeriesSplit folds

    Returns
    -------
    dict with keys: best_params, best_score, best_estimator
    """
    if not BAYES_AVAILABLE:
        raise ImportError(
            "scikit-optimize is not installed.\n"
            "Run: pip install scikit-optimize\n"
            "Or set ENABLE_BAYESIAN_OPT=false in .env"
        )

    tscv = TimeSeriesSplit(n_splits=n_splits)
    search_space = {
        "n_estimators":     Integer(100, 400),
        "max_depth":        Integer(5, 25),
        "min_samples_split": Integer(2, 15),
        "min_samples_leaf":  Integer(1, 8),
    }

    estimator = RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1)
    logger.info(f"[BayesSearchCV] Running {n_iter} iterations × {n_splits} folds…")

    bayes_search = BayesSearchCV(
        estimator=estimator,
        search_spaces=search_space,
        n_iter=n_iter,
        cv=tscv,
        scoring="r2",
        n_jobs=-1,
        random_state=RANDOM_SEED,
        verbose=1,
    )
    bayes_search.fit(X_train, y_train)

    logger.info(f"[BayesSearchCV] Best R²: {bayes_search.best_score_:.4f}")
    logger.info(f"[BayesSearchCV] Best params: {bayes_search.best_params_}")

    return {
        "best_params":    dict(bayes_search.best_params_),
        "best_score":     round(bayes_search.best_score_, 4),
        "best_estimator": bayes_search.best_estimator_,
    }


def auto_tune(X_train: pd.DataFrame, y_train: pd.Series) -> dict:
    """
    Automatically select the best available tuning method.
    Uses Bayesian if enabled + available, else GridSearchCV.
    """
    if ENABLE_BAYESIAN and BAYES_AVAILABLE:
        logger.info("[AutoTune] Using Bayesian optimization.")
        return tune_with_bayesian(X_train, y_train)
    else:
        if ENABLE_BAYESIAN:
            logger.warning("[AutoTune] Bayesian requested but scikit-optimize not installed. Falling back to GridSearchCV.")
        return tune_with_gridsearch(X_train, y_train)


def _grid_size(param_grid: dict) -> int:
    """Calculate total number of hyperparameter combinations."""
    size = 1
    for v in param_grid.values():
        size *= len(v)
    return size
