"""
policy/policy_simulator.py
============================
3-Layer Policy Simulation Architecture for AQI forecasting.

Architecture (aligned with the research paper):
  Layer 1 — Predict   : Get baseline AQI from trained model
  Layer 2 — Simulate  : Apply policy lever to modify input features
  Layer 3 — Evaluate  : Re-predict AQI and compute improvement

Supported Policies (from config.POLICY_LEVERS):
  - EV_Adoption
  - Industrial_Regulation
  - Renewable_Energy
  - Waste_Management
  - Green_Public_Transport
  - Combined_All (applies all policies simultaneously)
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from pathlib import Path
import sys
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import POLICY_LEVERS

logger = logging.getLogger(__name__)


# ── Feature perturbation map ──────────────────────────────────────────────────
# Maps each policy to a dict of {feature_substring: delta_fraction}
# delta_fraction: fractional change applied to features whose name contains
# the given substring. Negative = reduction, Positive = increase.
POLICY_FEATURE_DELTAS: Dict[str, Dict[str, float]] = {
    "EV_Adoption": {
        "vehicle_density":      -0.20,   # 20% fewer vehicles
        "no2":                  -0.12,   # lower NOx from EVs
        "co":                   -0.10,   # lower CO from EVs
    },
    "Industrial_Regulation": {
        "industrial_emission":  -0.15,   # stricter cap on industrial output
        "pm25":                 -0.08,
        "pm10":                 -0.06,
        "so2":                  -0.10,
    },
    "Renewable_Energy": {
        "coal_usage":           -0.18,   # shift away from coal
        "pm25":                 -0.05,
        "co2":                  -0.15,
    },
    "Waste_Management": {
        "waste_burning":        -0.08,   # less open burning
        "pm10":                 -0.04,
        "pm25":                 -0.03,
    },
    "Green_Public_Transport": {
        "vehicle_density":      -0.12,   # fewer private vehicles
        "no2":                  -0.08,
        "co":                   -0.06,
    },
}


class PolicySimulator:
    """
    3-Layer policy simulation engine.

    Parameters
    ----------
    model    : Fitted AQIForestModel instance
    X_ref    : Reference feature DataFrame (training set) used as simulation baseline

    Usage
    -----
    >>> simulator = PolicySimulator(model, X_train)
    >>> result = simulator.simulate_policy("EV_Adoption", intensity=1.0)
    >>> all_results = simulator.simulate_all_policies(intensity=1.0)
    """

    def __init__(self, model, X_ref: pd.DataFrame):
        if not model.is_fitted:
            raise RuntimeError("PolicySimulator requires a fitted AQIForestModel.")
        self.model = model
        self.X_ref = X_ref.copy()
        self.features = list(X_ref.columns)

        # Layer 1: compute baseline AQI once (mean over reference set)
        baseline_preds = self.model.predict(self.X_ref)
        self.baseline_aqi = float(np.mean(baseline_preds))
        logger.info(
            f"[PolicySimulator] Baseline AQI (mean over {len(X_ref):,} samples): "
            f"{self.baseline_aqi:.2f}"
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _apply_perturbation(
        self,
        X: pd.DataFrame,
        feature_deltas: Dict[str, float],
        intensity: float,
    ) -> pd.DataFrame:
        """
        Layer 2: Apply policy feature perturbations.

        For each (substring, delta_fraction) pair:
          - Find all columns whose name contains `substring`
          - Multiply those columns by (1 + delta_fraction * intensity)

        Parameters
        ----------
        X              : Feature DataFrame (copy is made internally)
        feature_deltas : {feature_substring: delta_fraction}
        intensity      : Scaling factor 0–1 (1.0 = full policy, 0.5 = half strength)

        Returns
        -------
        Perturbed copy of X
        """
        X_sim = X.copy()
        for substring, delta in feature_deltas.items():
            matching_cols = [c for c in X_sim.columns if substring.lower() in c.lower()]
            if matching_cols:
                multiplier = 1.0 + (delta * intensity)
                X_sim[matching_cols] = X_sim[matching_cols] * multiplier
                logger.debug(
                    f"  Applied Δ={delta*intensity:+.3f} to {matching_cols} "
                    f"(intensity={intensity:.2f})"
                )
            else:
                # No directly named feature — apply a proxy AQI shift via lag features
                lag_cols = [c for c in X_sim.columns if "aqi_lag" in c or "rolling_mean" in c]
                if lag_cols:
                    proxy_shift = delta * intensity * self.baseline_aqi * 0.5
                    X_sim[lag_cols] = X_sim[lag_cols] + proxy_shift
        return X_sim

    # ── Public API ────────────────────────────────────────────────────────────

    def simulate_policy(self, policy_name: str, intensity: float = 1.0) -> dict:
        """
        Simulate a single policy and return its AQI impact.

        Parameters
        ----------
        policy_name : Name of the policy (must be in POLICY_LEVERS or 'Combined_All')
        intensity   : 0.0–1.0 fraction of full policy strength

        Returns
        -------
        dict with keys:
          policy, description, baseline_aqi, simulated_aqi,
          aqi_delta, pct_improvement
        """
        intensity = float(np.clip(intensity, 0.0, 1.0))

        if policy_name == "Combined_All":
            # Merge all policy deltas
            combined_deltas: Dict[str, float] = {}
            for p_deltas in POLICY_FEATURE_DELTAS.values():
                for k, v in p_deltas.items():
                    combined_deltas[k] = combined_deltas.get(k, 0.0) + v
            feature_deltas = combined_deltas
            description = "All policies applied simultaneously"
        elif policy_name in POLICY_FEATURE_DELTAS:
            feature_deltas = POLICY_FEATURE_DELTAS[policy_name]
            lever = POLICY_LEVERS.get(policy_name, {})
            description = (
                f"emission_factor={lever.get('emission_factor', 'N/A')}, "
                f"max_budget=₹{lever.get('max_budget', 'N/A')}Cr"
            )
        else:
            raise ValueError(
                f"Unknown policy: '{policy_name}'. "
                f"Valid options: {list(POLICY_FEATURE_DELTAS.keys()) + ['Combined_All']}"
            )

        # Layer 2: perturb features
        X_sim = self._apply_perturbation(self.X_ref, feature_deltas, intensity)

        # Layer 3: re-predict
        sim_preds = self.model.predict(X_sim)
        simulated_aqi = float(np.mean(sim_preds))

        aqi_delta = self.baseline_aqi - simulated_aqi          # positive = improvement
        pct_improvement = (aqi_delta / self.baseline_aqi) * 100 if self.baseline_aqi > 0 else 0.0

        return {
            "policy":          policy_name,
            "description":     description,
            "baseline_aqi":    round(self.baseline_aqi, 2),
            "simulated_aqi":   round(simulated_aqi, 2),
            "aqi_delta":       round(aqi_delta, 2),
            "pct_improvement": round(pct_improvement, 3),
        }

    def simulate_all_policies(self, intensity: float = 1.0) -> pd.DataFrame:
        """
        Simulate all policies (including Combined_All) and return results as DataFrame.

        Parameters
        ----------
        intensity : Policy intensity (0–1)

        Returns
        -------
        pd.DataFrame with one row per policy, sorted by aqi_delta descending
        """
        all_policies = list(POLICY_FEATURE_DELTAS.keys()) + ["Combined_All"]
        records = []
        for policy in all_policies:
            result = self.simulate_policy(policy, intensity=intensity)
            records.append(result)
            logger.info(
                f"[PolicySimulator] {policy}: "
                f"AQI {result['baseline_aqi']:.1f} → {result['simulated_aqi']:.1f} "
                f"({result['pct_improvement']:+.2f}%)"
            )

        df = pd.DataFrame(records)
        df.sort_values("aqi_delta", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def __repr__(self) -> str:
        return (
            f"PolicySimulator("
            f"baseline_aqi={self.baseline_aqi:.2f}, "
            f"ref_samples={len(self.X_ref):,}, "
            f"policies={list(POLICY_FEATURE_DELTAS.keys())})"
        )


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from data.data_loader import load_data
    from preprocessing.feature_engineering import engineer_features
    from models.random_forest_model import AQIForestModel
    from models.feature_selection import select_features_rfe

    print("Loading data…")
    df = load_data()
    df_fe, target, features = engineer_features(df)
    X = df_fe[features]
    y = df_fe[target]

    selected, _ = select_features_rfe(X, y)
    X_sel = X[selected]

    split = int(len(X_sel) * 0.8)
    X_train, y_train = X_sel.iloc[:split], y.iloc[:split]

    print("Training model…")
    model = AQIForestModel()
    model.fit(X_train, y_train)

    print("\nRunning policy simulation…")
    sim = PolicySimulator(model, X_train)
    results = sim.simulate_all_policies(intensity=1.0)
    print(results.to_string(index=False))
