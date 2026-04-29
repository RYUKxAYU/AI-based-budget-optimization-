"""
main.py
========
End-to-end pipeline runner for the AI Based Green Budget Optimizer.

Pipeline Steps:
  1. Generate synthetic data (or load real scraped data)
  2. Load & preprocess the dataset
  3. Feature engineering
  4. Feature selection (RFE)
  5. Hyperparameter tuning (optional)
  6. Train final RandomForest model
  7. Time-series cross-validation
  8. Policy simulation (all 6 policy scenarios)
  9. Green budget optimization
 10. Generate all visualizations

Run:
  python main.py
  python main.py --tune       (run hyperparameter search)
  python main.py --skip-gen  (skip data generation if CSV exists)
"""

import argparse
import logging
import time
from pathlib import Path

# ─── Load .env if present ────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Optional dependency guards ──────────────────────────────────────────────
import os
_ENABLE_SHAP = os.getenv("ENABLE_SHAP", "false").lower() == "true"
_ENABLE_BAYES = os.getenv("ENABLE_BAYESIAN_OPT", "false").lower() == "true"

if _ENABLE_SHAP:
    try:
        import shap  # noqa: F401
    except ImportError:
        raise ImportError(
            "ENABLE_SHAP=true requires the 'shap' package.\n"
            "Install it with: pip install shap>=0.41.0"
        )

if _ENABLE_BAYES:
    try:
        import skopt  # noqa: F401
    except ImportError:
        raise ImportError(
            "ENABLE_BAYESIAN_OPT=true requires the 'scikit-optimize' package.\n"
            "Install it with: pip install scikit-optimize>=0.9.0"
        )

# ─── Configure logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Imports ─────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from config import (
    CITIES, DATA_DIR, OUTPUT_DIR, RANDOM_SEED,
    FORECAST_HORIZON, N_CV_SPLITS, RF_PARAMS, N_RFE_FEATURES,
)

from data.synthetic_generator import generate_full_dataset
from data.data_loader import load_data
from preprocessing.feature_engineering import engineer_features
from models.random_forest_model import AQIForestModel
from models.feature_selection import select_features_rfe
from models.hyperparameter_tuning import auto_tune
from validation.time_series_cv import run_time_series_cv
from policy.policy_simulator import PolicySimulator
from optimization.budget_optimizer import (
    compute_policy_rankings, greedy_budget_allocation, print_optimization_report
)
from visualization.plots import plot_all


# ─── Banner ──────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        🌿 AI BASED GREEN BUDGET OPTIMIZER 🌿                ║
║   AQI Forecasting · Policy Simulation · Budget Optimization  ║
╚══════════════════════════════════════════════════════════════╝
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Based Green Budget Optimizer — End-to-End Pipeline"
    )
    parser.add_argument("--tune", action="store_true",
                        help="Run hyperparameter tuning before final training")
    parser.add_argument("--skip-gen", action="store_true",
                        help="Skip synthetic data generation if CSV already exists")
    parser.add_argument("--no-plots", action="store_true",
                        help="Skip visualization generation")
    parser.add_argument("--city", type=str, default=None,
                        help="Filter to a specific city for predictions")
    return parser.parse_args()


def step(title: str, step_num: int, total: int = 10):
    """Print a formatted step header."""
    print(f"\n{'─'*62}")
    print(f"  STEP {step_num}/{total} │ {title}")
    print(f"{'─'*62}")


def run_pipeline(args):
    print(BANNER)
    t_start = time.time()

    total_steps = 10

    # ── Step 1: Data Generation ───────────────────────────────────────────────
    step("Synthetic Data Generation", 1, total_steps)
    syn_path = DATA_DIR / "synthetic_dataset.csv"
    if args.skip_gen and syn_path.exists():
        print(f"  [skip] Synthetic dataset already exists: {syn_path}")
    else:
        generate_full_dataset(save=True)

    # ── Step 2: Data Loading ──────────────────────────────────────────────────
    step("Data Loading & Cleaning", 2, total_steps)
    df_raw = load_data(use_real=False)   # use_real=True to merge scraped data
    print(f"  Dataset shape: {df_raw.shape}")

    # ── Step 3: Feature Engineering ───────────────────────────────────────────
    step("Feature Engineering", 3, total_steps)
    df_fe, target_col, all_features = engineer_features(df_raw)

    # Optional: filter to single city
    if args.city:
        if args.city not in CITIES:
            print(f"  ⚠ City '{args.city}' not found. Using all cities.")
        else:
            df_fe = df_fe[df_fe["city"] == args.city].copy()
            print(f"  Filtered to {args.city}: {len(df_fe):,} rows")

    X_all = df_fe[all_features]
    y_all = df_fe[target_col]
    print(f"  X shape: {X_all.shape}  |  Target: '{target_col}'")

    # ── Step 4: Feature Selection (RFE) ──────────────────────────────────────
    step(f"Feature Selection (RFE — Top {N_RFE_FEATURES})", 4, total_steps)
    selected_features, rfe_report = select_features_rfe(X_all, y_all, n_features=N_RFE_FEATURES)
    X = X_all[selected_features]
    print(f"  Selected features: {selected_features}")

    # ── Step 5: Hyperparameter Tuning (optional) ──────────────────────────────
    step("Hyperparameter Tuning", 5, total_steps)
    final_params = RF_PARAMS.copy()
    if args.tune:
        print("  Running hyperparameter search (this may take several minutes)…")
        tune_result = auto_tune(X, y_all)
        final_params.update(tune_result["best_params"])
        print(f"  Best params found: {tune_result['best_params']}")
        print(f"  Best CV R²: {tune_result['best_score']:.4f}")
    else:
        print("  [skip] Using default parameters. Pass --tune to run search.")

    # ── Step 6: Train Final Model ─────────────────────────────────────────────
    step("Training Final AQI Model", 6, total_steps)
    # Use 80% of data for training, 20% for final evaluation
    split_idx = int(len(X) * 0.80)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y_all.iloc[:split_idx], y_all.iloc[split_idx:]

    model = AQIForestModel(params=final_params)
    model.fit(X_train, y_train)
    train_metrics = model.evaluate(X_train, y_train)
    test_metrics  = model.evaluate(X_test, y_test)

    print(f"\n  ┌─ Training Metrics ──────────────────────────────────┐")
    print(f"  │  R²={train_metrics['r2']:.4f}  MAE={train_metrics['mae']:.1f}  RMSE={train_metrics['rmse']:.1f}  │")
    print(f"  ├─ Test Metrics ──────────────────────────────────────┤")
    print(f"  │  R²={test_metrics['r2']:.4f}  MAE={test_metrics['mae']:.1f}  RMSE={test_metrics['rmse']:.1f}  │")
    print(f"  └─────────────────────────────────────────────────────┘")

    model.save("aqi_forest_model.pkl")

    # ── Step 7: Time-Series Cross-Validation ──────────────────────────────────
    step(f"Time-Series Cross-Validation ({N_CV_SPLITS} folds)", 7, total_steps)
    cv_summary = run_time_series_cv(X, y_all, model_params=final_params)

    # ── Step 8: Policy Simulation ─────────────────────────────────────────────
    step("Policy Simulation (3-Layer Architecture)", 8, total_steps)
    simulator = PolicySimulator(model, X_train)
    policy_results = simulator.simulate_all_policies(intensity=1.0)

    print("\n  Policy Simulation Results:")
    print("  " + "─" * 56)
    for _, row in policy_results.iterrows():
        direction = "↓" if row["aqi_delta"] > 0 else "↑"
        print(f"  {direction} {row['policy']:<25} "
              f"AQI: {row['baseline_aqi']:.1f} → {row['simulated_aqi']:.1f}  "
              f"({row['pct_improvement']:+.1f}%)")

    # ── Step 9: Green Budget Optimization ────────────────────────────────────
    step("Green Budget Optimization", 9, total_steps)
    rankings = compute_policy_rankings(simulator)
    allocation = greedy_budget_allocation(rankings)
    print_optimization_report(allocation)

    # ── Step 10: Visualization ────────────────────────────────────────────────
    step("Generating Visualizations", 10, total_steps)
    if not args.no_plots:
        y_pred_test = model.predict(X_test)
        importance_df = model.get_feature_importances(top_n=15)

        plot_all(
            y_true=y_test,
            y_pred=y_pred_test,
            fold_df=cv_summary["fold_results"],
            mean_r2=cv_summary["mean_r2"],
            std_r2=cv_summary["std_r2"],
            importance_df=importance_df,
            policy_results=policy_results,
            allocation_result=allocation,
        )
    else:
        print("  [skip] Visualization skipped (--no-plots flag).")

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n{'═'*62}")
    print(f"  ✅ PIPELINE COMPLETE  |  Time elapsed: {elapsed:.1f}s")
    print(f"{'═'*62}")
    print(f"  📁 Outputs saved to: {OUTPUT_DIR}")
    print(f"  📊 Test R²:          {test_metrics['r2']:.4f}")
    print(f"  📉 Mean CV R²:       {cv_summary['mean_r2']:.4f} ± {cv_summary['std_r2']:.4f}")
    print(f"  🌿 AQI Improvement:  {allocation['total_aqi_improvement']:.1f} units (optimized budget)")
    print(f"{'═'*62}\n")

    return {
        "model":       model,
        "cv_summary":  cv_summary,
        "policy_results": policy_results,
        "allocation":  allocation,
        "X_test":      X_test,
        "y_test":      y_test,
    }


if __name__ == "__main__":
    args = parse_args()
    results = run_pipeline(args)
