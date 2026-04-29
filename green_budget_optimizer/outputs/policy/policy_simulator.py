"""
policy/policy_simulator.py
============================
3-Layer Policy Simulation System (as described in the research paper):

  Layer A: Predictive Layer   — trained AQI model
  Layer B: Policy Simulation  — modify input features to simulate interventions
  Layer C: Scenario Evaluation — predict AQI under modified conditions & compute delta

Supported policy levers:
  - Reduce emissions (CO2, methane)
  - Increase EV adoption (→ reduce vehicle density + emissions)
  - Industrial regulation (→ reduce industrial activity)
  - Waste management improvement
  - Renewable energy adoption
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import POLICY_LEVERS


# ─── Layer B: Policy Definitions ─────────────────────────────────────────────

POLICY_EFFECTS = {
    "EV_Adoption": {
        "description": "Increase EV adoption → reduce vehicle density & emissions",
        "column_effects": {
            "vehicle_density":    -0.15,   # 15% reduction
            "co2_emissions":      -0.10,
            "methane_emissions":  -0.05,
            "ev_subsidy_level":   +0.20,
        },
    },
    "Industrial_Regulation": {
        "description": "Stricter emission caps on industries",
        "column_effects": {
            "industrial_activity":   -0.20,
            "co2_emissions":         -0.15,
            "methane_emissions":     -0.10,
            "emission_cap_strength": +0.25,
        },
    },
    "Renewable_Energy": {
        "description": "Shift from fossil fuels to renewable energy sources",
        "column_effects": {
            "co2_emissions":     -0.20,
            "methane_emissions": -0.12,
            "industrial_activity": -0.08,
        },
    },
    "Waste_Management": {
        "description": "Improved waste segregation and landfill management",
        "column_effects": {
            "waste_index":       -0.25,
            "methane_emissions": -0.08,
        },
    },
    "Green_Public_Transport": {
        "description": "Expand metro / BRT / electric bus networks",
        "column_effects": {
            "vehicle_density":   -0.18,
            "co2_emissions":     -0.08,
        },
    },
    "Combined_All": {
        "description": "Apply all policies simultaneously (optimistic scenario)",
        "column_effects": {
            "vehicle_density":    -0.25,
            "co2_emissions":      -0.30,
            "methane_emissions":  -0.20,
            "industrial_activity": -0.20,
            "waste_index":        -0.20,
            "ev_subsidy_level":   +0.25,
            "emission_cap_strength": +0.30,
        },
    },
}


class PolicySimulator:
    """
    3-Layer Policy Simulation System.

    Attributes
    ----------
    model   : Trained AQIForestModel instance
    baseline: Representative baseline feature row for simulation
    """

    def __init__(self, model, baseline_data: pd.DataFrame):
        """
        Parameters
        ----------
        model         : Fitted AQIForestModel
        baseline_data : Feature DataFrame — the simulator uses the median row
                        as the baseline for comparisons
        """
        self.model = model
        # Compute median baseline (ignoring non-numeric columns)
        numeric_cols = baseline_data.select_dtypes(include=[np.number]).columns
        self.baseline = baseline_data[numeric_cols].median().to_frame().T
        self.feature_cols = model.features
        self._align_baseline()

    def _align_baseline(self):
        """Ensure baseline has exactly the model's expected feature columns."""
        for col in self.feature_cols:
            if col not in self.baseline.columns:
                self.baseline[col] = 0.0
        self.baseline = self.baseline[self.feature_cols]

    def _apply_policy(self, policy_name: str, intensity: float = 1.0) -> pd.DataFrame:
        """
        Apply a named policy to the baseline features.

        Parameters
        ----------
        policy_name : Key in POLICY_EFFECTS dict
        intensity   : Scale factor (1.0 = full effect, 0.5 = half effect)

        Returns
        -------
        Modified feature DataFrame
        """
        if policy_name not in POLICY_EFFECTS:
            raise ValueError(f"Unknown policy: '{policy_name}'. "
                             f"Available: {list(POLICY_EFFECTS.keys())}")

        modified = self.baseline.copy()
        effects = POLICY_EFFECTS[policy_name]["column_effects"]

        for col, delta_pct in effects.items():
            if col in modified.columns:
                # Apply relative change, clamp to [0, 1] for ratio features
                new_val = modified[col].values[0] * (1 + delta_pct * intensity)
                # Clamp ratio-style columns
                if col in {"vehicle_density", "industrial_activity",
                           "ev_subsidy_level", "emission_cap_strength", "waste_index"}:
                    new_val = np.clip(new_val, 0.0, 1.0)
                else:
                    new_val = max(new_val, 0.0)
                modified[col] = new_val

        return modified

    def predict_baseline(self) -> float:
        """Return baseline AQI prediction."""
        return float(self.model.predict(self.baseline)[0])

    def simulate_policy(self, policy_name: str, intensity: float = 1.0) -> dict:
        """
        Simulate a single policy intervention.

        Parameters
        ----------
        policy_name : Policy name (see POLICY_EFFECTS keys)
        intensity   : Strength of intervention [0.0 – 2.0]

        Returns
        -------
        dict with:
          - policy: policy name
          - description: human-readable policy description
          - baseline_aqi: AQI before intervention
          - simulated_aqi: AQI after intervention
          - aqi_delta: improvement (positive = better air quality)
          - pct_improvement: percentage AQI reduction
          - intensity: applied intensity
        """
        baseline_aqi = self.predict_baseline()
        modified_features = self._apply_policy(policy_name, intensity)
        simulated_aqi = float(self.model.predict(modified_features)[0])

        delta = baseline_aqi - simulated_aqi  # positive = improvement
        pct_improvement = (delta / baseline_aqi) * 100 if baseline_aqi > 0 else 0.0

        return {
            "policy":          policy_name,
            "description":     POLICY_EFFECTS[policy_name]["description"],
            "baseline_aqi":    round(baseline_aqi, 2),
            "simulated_aqi":   round(simulated_aqi, 2),
            "aqi_delta":       round(delta, 2),
            "pct_improvement": round(pct_improvement, 2),
            "intensity":       intensity,
        }

    def simulate_all_policies(self, intensity: float = 1.0) -> pd.DataFrame:
        """
        Simulate all defined policies and return a ranked comparison DataFrame.

        Returns
        -------
        pd.DataFrame sorted by aqi_delta descending (best first)
        """
        results = []
        for policy_name in POLICY_EFFECTS:
            result = self.simulate_policy(policy_name, intensity)
            results.append(result)

        df = pd.DataFrame(results).sort_values("aqi_delta", ascending=False)
        df.reset_index(drop=True, inplace=True)
        return df

    def simulate_custom_scenario(self, modifications: dict) -> dict:
        """
        Simulate a completely custom policy scenario.

        Parameters
        ----------
        modifications : Dict of {column_name: absolute_new_value}
                        e.g., {"co2_emissions": 1.5, "ev_subsidy_level": 0.8}

        Returns
        -------
        dict with baseline_aqi, simulated_aqi, aqi_delta
        """
        baseline_aqi = self.predict_baseline()
        modified = self.baseline.copy()

        for col, new_val in modifications.items():
            if col in modified.columns:
                modified[col] = float(new_val)

        simulated_aqi = float(self.model.predict(modified)[0])
        delta = baseline_aqi - simulated_aqi

        return {
            "policy":          "Custom Scenario",
            "baseline_aqi":    round(baseline_aqi, 2),
            "simulated_aqi":   round(simulated_aqi, 2),
            "aqi_delta":       round(delta, 2),
            "pct_improvement": round((delta / baseline_aqi) * 100, 2),
        }
