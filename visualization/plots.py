"""
visualization/plots.py
========================
All visualization functions for the AI Based Green Budget Optimizer.

Plots generated:
  1. AQI Predictions vs Actual
  2. Cross-Validation R² per fold
  3. Feature Importance (top 15)
  4. Policy Scenario Comparison
  5. Budget Allocation (ranked bar + investment curves)
"""

from typing import List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # Non-interactive backend (safe for all environments)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, PLOT_STYLE, FIGURE_DPI, COLOR_PALETTE

# Apply style (graceful fallback)
try:
    plt.style.use(PLOT_STYLE)
except:
    plt.style.use("seaborn-v0_8")


def _save(fig, filename: str) -> Path:
    """Save figure to outputs directory."""
    path = OUTPUT_DIR / filename
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  📊 Saved: {path}")
    return path


# ─── 1. AQI Predictions vs Actual ────────────────────────────────────────────

def plot_aqi_predictions(
    y_true: pd.Series,
    y_pred: np.ndarray,
    city: str = "All Cities",
    n_show: int = 300,
) -> Path:
    """
    Plot actual vs predicted AQI time series.

    Parameters
    ----------
    y_true : True AQI values
    y_pred : Model predictions
    city   : Label for title
    n_show : Number of most recent points to display
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), facecolor="#0F1117")
    fig.suptitle(f"AQI Prediction vs Actual — {city}", fontsize=14,
                 color="white", fontweight="bold", y=1.01)

    # Limit to last n_show samples for readability
    y_t = y_true.values[-n_show:]
    y_p = y_pred[-n_show:]
    x = np.arange(len(y_t))

    # ── Time series subplot ──
    ax1 = axes[0]
    ax1.set_facecolor("#1A1D27")
    ax1.plot(x, y_t, color="#2ECC71", linewidth=1.2, label="Actual AQI", alpha=0.9)
    ax1.plot(x, y_p, color="#E74C3C", linewidth=1.0, linestyle="--",
             label="Predicted AQI", alpha=0.85)
    ax1.fill_between(x, y_t, y_p, alpha=0.15, color="#F39C12")
    ax1.set_ylabel("AQI", color="white")
    ax1.set_xlabel("Time step (days)", color="white")
    ax1.tick_params(colors="white")
    ax1.legend(facecolor="#1A1D27", labelcolor="white")
    ax1.spines["bottom"].set_color("#333")
    ax1.spines["left"].set_color("#333")
    for sp in ["top", "right"]:
        ax1.spines[sp].set_visible(False)

    # ── Scatter (actual vs predicted) subplot ──
    ax2 = axes[1]
    ax2.set_facecolor("#1A1D27")
    ax2.scatter(y_t, y_p, alpha=0.3, s=8, color="#3498DB")
    # Perfect prediction line
    lo, hi = min(y_t.min(), y_p.min()), max(y_t.max(), y_p.max())
    ax2.plot([lo, hi], [lo, hi], color="#F39C12", linewidth=1.5,
             linestyle="--", label="Perfect Prediction")
    from sklearn.metrics import r2_score
    r2 = r2_score(y_t, y_p)
    ax2.set_title(f"Scatter: Actual vs Predicted  (R²={r2:.3f})", color="white", fontsize=10)
    ax2.set_xlabel("Actual AQI", color="white")
    ax2.set_ylabel("Predicted AQI", color="white")
    ax2.tick_params(colors="white")
    ax2.legend(facecolor="#1A1D27", labelcolor="white")
    ax2.spines["bottom"].set_color("#333")
    ax2.spines["left"].set_color("#333")
    for sp in ["top", "right"]:
        ax2.spines[sp].set_visible(False)

    plt.tight_layout()
    return _save(fig, "aqi_predictions.png")


# ─── 2. Cross-Validation R² per fold ─────────────────────────────────────────

def plot_cv_scores(fold_df: pd.DataFrame, mean_r2: float, std_r2: float) -> Path:
    """
    Bar chart of R² score per CV fold, with mean ± std bands.

    Parameters
    ----------
    fold_df  : DataFrame with columns ['fold', 'r2']
    mean_r2  : Mean R² across folds
    std_r2   : Std deviation of R²
    """
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#0F1117")
    ax.set_facecolor("#1A1D27")

    folds = fold_df["fold"].values
    r2s = fold_df["r2"].values
    colors = [COLOR_PALETTE[i % len(COLOR_PALETTE)] for i in range(len(folds))]
    bars = ax.bar(folds, r2s, color=colors, alpha=0.85, width=0.6, edgecolor="#333")

    # Mean ± std band
    ax.axhline(mean_r2, color="#F39C12", linewidth=2, linestyle="--",
               label=f"Mean R² = {mean_r2:.4f}")
    ax.axhspan(mean_r2 - std_r2, mean_r2 + std_r2, alpha=0.15, color="#F39C12",
               label=f"±1 Std (σ={std_r2:.4f})")

    # Value labels on bars
    for bar, r2 in zip(bars, r2s):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{r2:.4f}", ha="center", va="bottom", color="white", fontsize=9)

    ax.set_title("Time-Series Cross-Validation — R² per Fold",
                 color="white", fontsize=13, fontweight="bold")
    ax.set_xlabel("CV Fold", color="white")
    ax.set_ylabel("R² Score", color="white")
    ax.set_xticks(folds)
    ax.set_xticklabels([f"Fold {f}" for f in folds])
    ax.tick_params(colors="white")
    ax.legend(facecolor="#1A1D27", labelcolor="white")
    ax.set_ylim(0, min(1.05, max(r2s) + 0.08))
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#333")
    ax.spines["left"].set_color("#333")

    plt.tight_layout()
    return _save(fig, "cv_scores.png")


# ─── 3. Feature Importance ────────────────────────────────────────────────────

def plot_feature_importance(importance_df: pd.DataFrame, top_n: int = 15) -> Path:
    """
    Horizontal bar chart of top N feature importances.

    Parameters
    ----------
    importance_df : DataFrame with columns ['feature', 'importance']
    top_n         : Number of top features to display
    """
    df = importance_df.head(top_n).copy()
    df.sort_values("importance", inplace=True)   # ascending for horizontal bar

    fig, ax = plt.subplots(figsize=(10, 7), facecolor="#0F1117")
    ax.set_facecolor("#1A1D27")

    # Color gradient: more important = brighter green
    norm = plt.Normalize(df["importance"].min(), df["importance"].max())
    cmap = plt.cm.YlGn
    colors = [cmap(norm(v)) for v in df["importance"].values]

    bars = ax.barh(df["feature"], df["importance"], color=colors, edgecolor="#333", height=0.65)

    # Value labels
    for bar, imp in zip(bars, df["importance"].values):
        ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height() / 2,
                f"{imp:.4f}", va="center", color="white", fontsize=8)

    ax.set_title(f"Top {top_n} Feature Importances (Random Forest)",
                 color="white", fontsize=13, fontweight="bold")
    ax.set_xlabel("Importance Score", color="white")
    ax.tick_params(colors="white", labelsize=9)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#333")
    ax.spines["left"].set_color("#333")

    plt.tight_layout()
    return _save(fig, "feature_importance.png")


# ─── 4. Policy Simulation Comparison ─────────────────────────────────────────

def plot_policy_comparison(policy_results: pd.DataFrame) -> Path:
    """
    Horizontal bar chart comparing AQI improvement per policy.

    Parameters
    ----------
    policy_results : Output of PolicySimulator.simulate_all_policies()
    """
    df = policy_results.sort_values("aqi_delta").copy()

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), facecolor="#0F1117")
    fig.suptitle("Policy Simulation — AQI Impact Comparison",
                 color="white", fontsize=14, fontweight="bold")

    # ── AQI Delta (improvement) ──
    ax1 = axes[0]
    ax1.set_facecolor("#1A1D27")
    colors = ["#E74C3C" if v < 0 else "#2ECC71" for v in df["aqi_delta"]]
    ax1.barh(df["policy"], df["aqi_delta"], color=colors, edgecolor="#333", height=0.6)
    ax1.axvline(0, color="#888", linewidth=0.8)
    ax1.set_title("AQI Reduction per Policy", color="white", fontsize=11)
    ax1.set_xlabel("AQI Units Reduced (higher = better)", color="white")
    ax1.tick_params(colors="white", labelsize=9)
    for sp in ["top", "right"]:
        ax1.spines[sp].set_visible(False)
    ax1.spines["bottom"].set_color("#333")
    ax1.spines["left"].set_color("#333")

    # ── % Improvement ──
    ax2 = axes[1]
    ax2.set_facecolor("#1A1D27")
    ax2.barh(df["policy"], df["pct_improvement"],
             color=COLOR_PALETTE[:len(df)], edgecolor="#333", height=0.6)
    ax2.set_title("% AQI Improvement per Policy", color="white", fontsize=11)
    ax2.set_xlabel("% Improvement", color="white")
    ax2.tick_params(colors="white", labelsize=9)
    for sp in ["top", "right"]:
        ax2.spines[sp].set_visible(False)
    ax2.spines["bottom"].set_color("#333")
    ax2.spines["left"].set_color("#333")

    # Baseline annotation
    baseline_aqi = df["baseline_aqi"].iloc[0]
    fig.text(0.5, -0.02, f"Baseline AQI: {baseline_aqi:.1f}", ha="center",
             color="#AAA", fontsize=10)

    plt.tight_layout()
    return _save(fig, "policy_comparison.png")


# ─── 5. Budget Allocation ─────────────────────────────────────────────────────

def plot_budget_allocation(allocation_result: dict) -> Path:
    """
    Visualize optimal budget allocation — ranked bar + pie chart.

    Parameters
    ----------
    allocation_result : Output of greedy_budget_allocation()
    """
    df = allocation_result["allocation_df"]
    total_improvement = allocation_result["total_aqi_improvement"]
    total_budget = allocation_result["total_budget"]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), facecolor="#0F1117")
    fig.suptitle(
        f"Green Budget Allocation — Total Budget: ₹{total_budget:,} Cr | "
        f"Expected AQI Improvement: {total_improvement:.1f} units",
        color="white", fontsize=12, fontweight="bold"
    )

    # ── Ranked bar chart ──
    ax1 = axes[0]
    ax1.set_facecolor("#1A1D27")
    palette = COLOR_PALETTE[:len(df)]
    bar_container = ax1.bar(
        df["policy"], df["allocated_crore"],
        color=palette, edgecolor="#333", alpha=0.9
    )
    # Secondary y-axis: AQI improvement
    ax1b = ax1.twinx()
    ax1b.plot(df["policy"], df["aqi_improvement"], color="#F39C12",
              marker="D", linewidth=2, markersize=7, label="AQI Improvement")
    ax1b.set_ylabel("AQI Units Reduced", color="#F39C12")
    ax1b.tick_params(colors="#F39C12")

    ax1.set_title("Budget Allocated vs AQI Improvement", color="white", fontsize=11)
    ax1.set_xlabel("Policy Lever", color="white")
    ax1.set_ylabel("₹ Crore Allocated", color="white")
    ax1.tick_params(colors="white", labelsize=8)
    plt.setp(ax1.get_xticklabels(), rotation=30, ha="right")
    for sp in ["top"]:
        ax1.spines[sp].set_visible(False)
    ax1.spines["bottom"].set_color("#333")
    ax1.spines["left"].set_color("#333")

    # ── Pie chart ──
    ax2 = axes[1]
    ax2.set_facecolor("#1A1D27")
    wedges, texts, autotexts = ax2.pie(
        df["allocated_crore"],
        labels=df["policy"],
        colors=palette,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.78,
        wedgeprops={"edgecolor": "#1A1D27", "linewidth": 2},
    )
    for t in texts:
        t.set_color("white")
        t.set_fontsize(8)
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(8)
    ax2.set_title("Budget Share per Policy", color="white", fontsize=11)

    plt.tight_layout()
    return _save(fig, "budget_allocation.png")


def plot_all(
    y_true, y_pred,
    fold_df, mean_r2, std_r2,
    importance_df,
    policy_results,
    allocation_result,
) -> List[Path]:
    """Convenience function to generate all plots. Returns list of saved paths."""
    print("\n[Visualization] Generating all plots…")
    paths = []
    paths.append(plot_aqi_predictions(y_true, y_pred))
    paths.append(plot_cv_scores(fold_df, mean_r2, std_r2))
    paths.append(plot_feature_importance(importance_df))
    paths.append(plot_policy_comparison(policy_results))
    paths.append(plot_budget_allocation(allocation_result))
    print(f"  ✓ {len(paths)} plots saved to {OUTPUT_DIR}")
    return paths
