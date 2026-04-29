"""
tests/test_policy_simulator.py
================================
Unit tests for policy/policy_simulator.py
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent / "green_budget_optimizer"
sys.path.insert(0, str(ROOT))

from policy.policy_simulator import PolicySimulator, POLICY_FEATURE_DELTAS
from models.random_forest_model import AQIForestModel


@pytest.fixture
def fitted_model_and_data():
    """Create a small fitted AQIForestModel on synthetic data."""
    np.random.seed(42)
    n = 500
    feature_names = [
        "aqi_lag_1", "aqi_lag_2", "aqi_rolling_mean_7",
        "aqi_rolling_std_7", "month_sin", "month_cos",
        "pm25", "pm10", "no2", "vehicle_density",
        "industrial_emission", "coal_usage", "aqi_volatility",
        "aqi_category", "city_Mumbai"
    ]
    X = pd.DataFrame(
        np.random.uniform(10, 300, size=(n, len(feature_names))),
        columns=feature_names,
    )
    y = pd.Series(np.random.uniform(50, 300, n), name="aqi_ahead_24")

    model = AQIForestModel(params={
        "n_estimators": 10,
        "max_depth": 3,
        "random_state": 42,
        "n_jobs": 1,
    })
    model.fit(X, y)
    return model, X


class TestPolicySimulatorInit:
    def test_baseline_aqi_is_positive(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        assert sim.baseline_aqi > 0

    def test_unfitted_model_raises(self):
        model = AQIForestModel()   # not fitted
        X = pd.DataFrame({"a": [1, 2]})
        with pytest.raises(RuntimeError, match="fitted"):
            PolicySimulator(model, X)


class TestSimulatePolicy:
    def test_returns_required_keys(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        result = sim.simulate_policy("EV_Adoption")
        required = {"policy", "description", "baseline_aqi", "simulated_aqi",
                    "aqi_delta", "pct_improvement"}
        assert required.issubset(result.keys())

    def test_invalid_policy_raises(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        with pytest.raises(ValueError, match="Unknown policy"):
            sim.simulate_policy("FakePolicy123")

    def test_intensity_zero_has_no_effect(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        result = sim.simulate_policy("EV_Adoption", intensity=0.0)
        # At intensity=0 no perturbation → simulated ≈ baseline
        assert abs(result["aqi_delta"]) < 5.0  # small numerical tolerance

    def test_combined_all_works(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        result = sim.simulate_policy("Combined_All", intensity=1.0)
        assert result["policy"] == "Combined_All"
        assert isinstance(result["aqi_delta"], float)


class TestSimulateAllPolicies:
    def test_returns_dataframe(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        df = sim.simulate_all_policies()
        assert isinstance(df, pd.DataFrame)

    def test_includes_combined_all(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        df = sim.simulate_all_policies()
        assert "Combined_All" in df["policy"].values

    def test_row_count_matches_policy_count(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        df = sim.simulate_all_policies()
        expected_count = len(POLICY_FEATURE_DELTAS) + 1   # +1 for Combined_All
        assert len(df) == expected_count

    def test_sorted_by_aqi_delta_descending(self, fitted_model_and_data):
        model, X = fitted_model_and_data
        sim = PolicySimulator(model, X)
        df = sim.simulate_all_policies()
        deltas = df["aqi_delta"].values
        assert all(deltas[i] >= deltas[i + 1] for i in range(len(deltas) - 1))
