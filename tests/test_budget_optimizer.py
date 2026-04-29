"""
tests/test_budget_optimizer.py
================================
Unit tests for optimization/budget_optimizer.py
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

ROOT = Path(__file__).parent.parent / "green_budget_optimizer"
sys.path.insert(0, str(ROOT))

from optimization.budget_optimizer import greedy_budget_allocation


@pytest.fixture
def mock_rankings():
    """Fake rankings DataFrame simulating compute_policy_rankings() output."""
    return pd.DataFrame([
        {
            "policy": "EV_Adoption",
            "description": "EV policy",
            "recommended_budget": 400,
            "aqi_improvement": 8.0,
            "efficiency": 0.020,
            "cost_per_aqi_unit": 50.0,
            "rank": 1,
        },
        {
            "policy": "Renewable_Energy",
            "description": "Renewable policy",
            "recommended_budget": 200,
            "aqi_improvement": 5.0,
            "efficiency": 0.025,
            "cost_per_aqi_unit": 40.0,
            "rank": 2,
        },
        {
            "policy": "Waste_Management",
            "description": "Waste policy",
            "recommended_budget": 100,
            "aqi_improvement": 2.0,
            "efficiency": 0.020,
            "cost_per_aqi_unit": 50.0,
            "rank": 3,
        },
    ])


class TestGreedyBudgetAllocation:
    def test_returns_dict_with_required_keys(self, mock_rankings):
        result = greedy_budget_allocation(mock_rankings, total_budget=500)
        assert "allocation_df" in result
        assert "total_aqi_improvement" in result
        assert "remaining_budget" in result
        assert "total_budget" in result

    def test_total_allocated_does_not_exceed_budget(self, mock_rankings):
        total = 500
        result = greedy_budget_allocation(mock_rankings, total_budget=total)
        df = result["allocation_df"]
        assert df["allocated_crore"].sum() <= total + 1e-6   # float tolerance

    def test_aqi_improvement_is_positive(self, mock_rankings):
        result = greedy_budget_allocation(mock_rankings, total_budget=500)
        assert result["total_aqi_improvement"] > 0

    def test_remaining_budget_is_non_negative(self, mock_rankings):
        result = greedy_budget_allocation(mock_rankings, total_budget=1000)
        assert result["remaining_budget"] >= 0

    def test_zero_budget_returns_empty_allocation(self, mock_rankings):
        result = greedy_budget_allocation(mock_rankings, total_budget=0)
        assert result["allocation_df"].empty or result["total_aqi_improvement"] == 0.0

    def test_large_budget_allocates_all_policies(self, mock_rankings):
        result = greedy_budget_allocation(mock_rankings, total_budget=10_000)
        df = result["allocation_df"]
        # All 3 policies should be allocated
        assert len(df) == 3
