"""
optimization/budget_optimizer.py
==================================
Green Budget Optimization System.

Simulates investment vs AQI improvement, ranks policies by
impact-per-unit-cost, and outputs the optimal budget allocation.

Methodology (aligned with paper):
  1. For each policy lever, simulate AQI improvement at various spending levels
  2. Compute marginal AQI improvement per ₹ Crore invested
  3. Rank policies by efficiency (AQI_delta / cost)
  4. Allocate total budget greedily to maximize AQI improvement
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TOTAL_BUDGET_CRORE, POLICY_LEVERS


def simulate_investment_curve(
    policy_simulator,
    policy_name: str,
    max_budget: float,
    n_points: int = 10,
) -> pd.DataFrame:
    """
    Simulate AQI improvement at different investment levels for one policy.

    Parameters
    ----------
    policy_simulator : PolicySimulator instance
    policy_name      : Policy to simulate
    max_budget       : Maximum investment in ₹ Crore
    n_points         : Number of budget levels to simulate

    Returns
    -------
    pd.DataFrame with columns: budget_crore, aqi_improvement, marginal_efficiency
    """
    budget_levels = np.linspace(0, max_budget, n_points + 1)[1:]  # skip 0
    records = []

    for budget in budget_levels:
        # Intensity = fraction of max budget allocated
        intensity = budget / max_budget
        result = policy_simulator.simulate_policy(policy_name, intensity)
        records.append({
            "policy":       policy_name,
            "budget_crore": round(budget, 1),
            "aqi_improvement": result["aqi_delta"],
        })

    df = pd.DataFrame(records)
    # Compute marginal efficiency (AQI improvement per ₹ Crore)
    df["efficiency"] = (df["aqi_improvement"] / df["budget_crore"]).round(4)
    return df


def compute_policy_rankings(policy_simulator, total_budget: float = TOTAL_BUDGET_CRORE) -> pd.DataFrame:
    """
    Rank all policies by their cost-effectiveness at their recommended budget level.

    Parameters
    ----------
    policy_simulator : PolicySimulator instance
    total_budget     : Total available green budget in ₹ Crore

    Returns
    -------
    Ranked pd.DataFrame with columns:
      policy, recommended_budget, aqi_improvement, efficiency, cost_per_aqi_unit, rank
    """
    records = []

    for policy_name, lever in POLICY_LEVERS.items():
        max_b = lever["max_budget"]
        # Simulate at recommended (full) budget level
        result = policy_simulator.simulate_policy(policy_name, intensity=1.0)
        aqi_improvement = result["aqi_delta"]
        efficiency = aqi_improvement / max_b if max_b > 0 else 0
        cost_per_unit = max_b / aqi_improvement if aqi_improvement > 0 else float("inf")

        records.append({
            "policy":              policy_name,
            "description":         result["description"],
            "recommended_budget":  max_b,
            "aqi_improvement":     round(aqi_improvement, 2),
            "efficiency":          round(efficiency, 4),
            "cost_per_aqi_unit":   round(cost_per_unit, 2),
        })

    df = pd.DataFrame(records)
    df.sort_values("efficiency", ascending=False, inplace=True)
    df["rank"] = range(1, len(df) + 1)
    df.reset_index(drop=True, inplace=True)
    return df


def greedy_budget_allocation(
    rankings: pd.DataFrame,
    total_budget: float = TOTAL_BUDGET_CRORE,
) -> dict:
    """
    Allocate total_budget greedily across policies in efficiency rank order.

    The algorithm:
      1. Sort by efficiency (highest first)
      2. Allocate full recommended budget to each policy until budget runs out
      3. Partial allocation for the last policy if needed

    Parameters
    ----------
    rankings     : Output of compute_policy_rankings()
    total_budget : Total green budget in ₹ Crore

    Returns
    -------
    dict with:
      - allocation_df: DataFrame of allocations per policy
      - total_aqi_improvement: expected total AQI reduction
      - remaining_budget: unspent budget
    """
    remaining = total_budget
    allocation_records = []
    total_improvement = 0.0

    for _, row in rankings.iterrows():
        if remaining <= 0:
            break

        allocated = min(row["recommended_budget"], remaining)
        fraction = allocated / row["recommended_budget"]
        actual_improvement = row["aqi_improvement"] * fraction

        allocation_records.append({
            "rank":            int(row["rank"]),
            "policy":          row["policy"],
            "allocated_crore": round(allocated, 1),
            "aqi_improvement": round(actual_improvement, 2),
            "efficiency":      round(row["efficiency"], 4),
            "pct_of_budget":   round((allocated / total_budget) * 100, 1),
        })

        remaining -= allocated
        total_improvement += actual_improvement

    allocation_df = pd.DataFrame(allocation_records)
    return {
        "allocation_df":        allocation_df,
        "total_aqi_improvement": round(total_improvement, 2),
        "remaining_budget":      round(remaining, 1),
        "total_budget":          total_budget,
    }


def print_optimization_report(allocation_result: dict):
    """Print a formatted budget optimization report to console."""
    df = allocation_result["allocation_df"]
    print("\n" + "═" * 70)
    print("  🌿 GREEN BUDGET OPTIMIZATION REPORT")
    print("═" * 70)
    print(f"  Total Budget:          ₹ {allocation_result['total_budget']:,.0f} Crore")
    print(f"  Expected AQI Reduction: {allocation_result['total_aqi_improvement']:.1f} units")
    print(f"  Remaining Unspent:     ₹ {allocation_result['remaining_budget']:,.1f} Crore")
    print("─" * 70)
    print(f"  {'Rank':<5} {'Policy':<25} {'Budget (₹Cr)':<14} "
          f"{'AQI Improve':<14} {'% of Budget'}")
    print("─" * 70)
    for _, row in df.iterrows():
        print(f"  #{int(row['rank']):<4} {row['policy']:<25} "
              f"₹{row['allocated_crore']:<12,.0f} "
              f"{row['aqi_improvement']:<14.1f} "
              f"{row['pct_of_budget']:.1f}%")
    print("═" * 70)
