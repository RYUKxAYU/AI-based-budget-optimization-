"""
config.py
=========
Central configuration for the AI Based Green Budget Optimizer.
All tunable parameters are defined here for easy experimentation.
"""

import os
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── Data Generation ─────────────────────────────────────────────────────────
CITIES = ["Delhi", "Mumbai", "Kolkata", "Chennai", "Hyderabad"]
N_SAMPLES_PER_CITY = 2000          # 5 cities × 2000 = 10,000 total
START_DATE = "2018-01-01"
END_DATE = "2023-06-30"
RANDOM_SEED = 42

# ─── Feature Engineering ─────────────────────────────────────────────────────
LAG_PERIODS = [1, 2, 3, 6]         # AQI lag features
ROLLING_WINDOWS = [7, 30]          # Rolling mean/std windows (days)
FORECAST_HORIZON = 24              # Predict AQI 24 days ahead

# ─── Model ───────────────────────────────────────────────────────────────────
RF_PARAMS = {
    "n_estimators": 200,
    "max_depth": 15,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": RANDOM_SEED,
    "n_jobs": -1,
}

# GridSearchCV hyperparameter grid
RF_GRID = {
    "n_estimators": [100, 200, 300],
    "max_depth": [10, 15, 20, None],
    "min_samples_split": [2, 5, 10],
}

# ─── Validation ──────────────────────────────────────────────────────────────
N_CV_SPLITS = 5                    # TimeSeriesSplit folds
N_RFE_FEATURES = 15                # Top features to select via RFE

# ─── Budget Optimization ─────────────────────────────────────────────────────
TOTAL_BUDGET_CRORE = 1000          # Total green budget in ₹ Crore

# Policy levers: name → (max_budget_crore, emission_reduction_factor, cost_per_unit)
POLICY_LEVERS = {
    "EV_Adoption":            {"max_budget": 400, "emission_factor": 0.20, "cost_per_unit": 50},
    "Industrial_Regulation":  {"max_budget": 300, "emission_factor": 0.15, "cost_per_unit": 40},
    "Renewable_Energy":       {"max_budget": 200, "emission_factor": 0.18, "cost_per_unit": 60},
    "Waste_Management":       {"max_budget": 100, "emission_factor": 0.08, "cost_per_unit": 20},
    "Green_Public_Transport": {"max_budget": 150, "emission_factor": 0.12, "cost_per_unit": 35},
}

# ─── Web Scraper ─────────────────────────────────────────────────────────────
OPENAQ_API_URL = "https://api.openaq.org/v2/measurements"
OPENAQ_CITIES = ["Delhi", "Mumbai", "Kolkata"]
OPENAQ_PARAMETERS = ["pm25", "pm10", "co", "no2", "o3"]
SCRAPER_RATE_LIMIT_SEC = 1.0       # Seconds between API calls
SCRAPER_MAX_RETRIES = 3

# ─── Visualization ───────────────────────────────────────────────────────────
PLOT_STYLE = "seaborn-v0_8-darkgrid"
FIGURE_DPI = 150
COLOR_PALETTE = ["#2ECC71", "#3498DB", "#E74C3C", "#F39C12", "#9B59B6"]
