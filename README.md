# AI Based Green Budget Optimizer

> A modular, production-ready Python ML system that predicts AQI, simulates environmental policy interventions, and optimizes green budget allocation. Implements the full methodology from the research paper **"AI Based Green Budget Optimizer"**.

---

## 🌿 Overview

| Component | Description |
|-----------|-------------|
| **Data Pipeline** | Synthetic data generator (~10,000 samples, 5 cities) + OpenAQ web scraper |
| **Feature Engineering** | Lag features, rolling stats, cyclic encoding, volatility indicators |
| **ML Model** | `RandomForestRegressor` with `TimeSeriesSplit` CV (no data leakage) |
| **Validation** | 5-fold time-series CV with R², MAE, RMSE reporting |
| **Policy Simulation** | 3-layer architecture (Predict → Simulate → Evaluate) |
| **Budget Optimization** | Greedy allocation ranked by AQI improvement per ₹ Crore |
| **Visualization** | 5 publication-quality charts saved to `outputs/` |

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Edit `.env` and set your preferences:
```
DATA_SOURCE=synthetic         # or 'real' to use OpenAQ scraping
OPENAQ_API_KEY=your_key_here  # optional, for OpenAQ access
ENABLE_SHAP=false             # true requires: pip install shap
ENABLE_BAYESIAN_OPT=false     # true requires: pip install scikit-optimize
```

### 3. Run the full pipeline
```bash
python main.py
```

### Optional flags
```bash
python main.py --tune        # Run hyperparameter search (slower)
python main.py --skip-gen    # Skip data generation if CSV exists
python main.py --no-plots    # Skip visualization
python main.py --city Delhi  # Run for a single city only
```

---

## 📁 Project Structure

```
green_budget_optimizer/
├── main.py                     ← End-to-end pipeline runner
├── config.py                   ← All configurable parameters
├── requirements.txt
├── .env                        ← API keys and flags
│
├── data/
│   ├── synthetic_generator.py  ← Generates ~10,000 row dataset
│   ├── web_scraper.py          ← OpenAQ API scraper (optional)
│   └── data_loader.py          ← Merge + impute pipeline
│
├── preprocessing/
│   └── feature_engineering.py  ← Lag, rolling, cyclic, target creation
│
├── models/
│   ├── random_forest_model.py  ← AQIForestModel class
│   ├── feature_selection.py    ← RFE-based selection
│   └── hyperparameter_tuning.py← GridSearchCV / BayesSearchCV
│
├── validation/
│   └── time_series_cv.py       ← TimeSeriesSplit CV with metrics
│
├── policy/
│   └── policy_simulator.py     ← 3-layer policy simulation
│
├── optimization/
│   └── budget_optimizer.py     ← Greedy budget allocation
│
└── visualization/
    └── plots.py                ← All 5 chart generators
```

---

## 📊 Outputs

After running `main.py`, all outputs are saved to `outputs/`:

| File | Description |
|------|-------------|
| `aqi_predictions.png` | Actual vs predicted AQI time series + scatter |
| `cv_scores.png` | R² per CV fold with mean ± std band |
| `feature_importance.png` | Top 15 features by importance |
| `policy_comparison.png` | AQI improvement per policy scenario |
| `budget_allocation.png` | Optimal budget distribution |
| `aqi_forest_model.pkl` | Saved trained model |

---

## 🔬 Supported Policy Scenarios

| Policy | Description |
|--------|-------------|
| `EV_Adoption` | Increase EV adoption → reduce vehicle density |
| `Industrial_Regulation` | Stricter emission caps |
| `Renewable_Energy` | Fossil fuel → renewables transition |
| `Waste_Management` | Improved landfill/segregation |
| `Green_Public_Transport` | Metro / BRT expansion |
| `Combined_All` | All policies simultaneously |

---

## ⚙️ Key Configuration (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CITIES` | 5 Indian cities | Cities in synthetic dataset |
| `N_SAMPLES_PER_CITY` | 2000 | Daily records per city |
| `FORECAST_HORIZON` | 24 | Days ahead for AQI prediction |
| `N_CV_SPLITS` | 5 | TimeSeriesSplit folds |
| `TOTAL_BUDGET_CRORE` | 1000 | Green budget in ₹ Crore |

---

## 📜 Research Reference

Based on: *"AI Based Green Budget Optimizer"* — predictive modeling, causal policy simulation, and cost-benefit analysis for environmental budget allocation.

**Tech Stack:** `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `requests`, `beautifulsoup4`
