# AI Based Green Budget Optimizer

> A production-grade Python ML system that predicts Air Quality Index (AQI), simulates environmental policy interventions, and optimally allocates a green budget across Indian cities.

Based on the research paper: **"AI Based Green Budget Optimizer"**

---

## 🌿 Project Structure

```
AI based budget optimization using AI/
│
├── green_budget_optimizer/          ← Main ML pipeline (run this)
│   ├── main.py                      ← End-to-end 10-step pipeline runner
│   ├── config.py                    ← All tunable parameters
│   ├── requirements.txt
│   ├── .env                         ← API keys & feature flags
│   │
│   ├── data/                        ← Data generation & loading
│   │   ├── synthetic_generator.py
│   │   ├── web_scraper.py           ← OpenAQ API scraper (optional)
│   │   └── data_loader.py
│   │
│   ├── preprocessing/
│   │   └── feature_engineering.py  ← Lag, rolling, cyclic features
│   │
│   ├── models/
│   │   ├── random_forest_model.py  ← AQIForestModel class
│   │   ├── feature_selection.py    ← RFE feature selection
│   │   └── hyperparameter_tuning.py
│   │
│   ├── policy/                      ← ✅ 3-layer policy simulation
│   │   └── policy_simulator.py
│   │
│   ├── optimization/
│   │   └── budget_optimizer.py     ← Greedy budget allocation
│   │
│   ├── validation/
│   │   └── time_series_cv.py       ← TimeSeriesSplit CV
│   │
│   └── visualization/
│       └── plots.py                ← 5 publication-quality charts
│
├── shared/                          ← Phase 2: Microservices DB layer
│   └── db/
│       ├── base.py                  ← SQLAlchemy declarative base
│       └── models.py                ← ORM models (User, Budget, etc.)
│
├── tests/                           ← Unit tests
│   ├── test_feature_engineering.py
│   ├── test_budget_optimizer.py
│   └── test_policy_simulator.py
│
├── data/                            ← Root data directory
├── .env                             ← Root environment variables
└── verify_db.py                     ← DB verification script
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
cd green_budget_optimizer
pip install -r requirements.txt
```

### 2. Configure environment
Edit `green_budget_optimizer/.env`:
```
DATA_SOURCE=synthetic         # or 'real' to use OpenAQ scraping
OPENAQ_API_KEY=your_key_here  # get free key at https://openaq.org/register
ENABLE_SHAP=false
ENABLE_BAYESIAN_OPT=false
```

### 3. Run the full pipeline
```bash
cd green_budget_optimizer
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

## 📊 Pipeline Steps

| Step | Description |
|------|-------------|
| 1 | Synthetic data generation (~10,000 rows, 5 cities) |
| 2 | Data loading & cleaning |
| 3 | Feature engineering (lag, rolling, cyclic, volatility) |
| 4 | Feature selection via RFE (top 15 features) |
| 5 | Hyperparameter tuning (optional GridSearchCV / BayesSearchCV) |
| 6 | Train final RandomForest model |
| 7 | Time-series cross-validation (5-fold, no data leakage) |
| 8 | Policy simulation (6 scenarios, 3-layer architecture) |
| 9 | Green budget optimization (greedy allocation) |
| 10 | Generate all visualizations |

---

## 🌆 Cities Modeled

Delhi · Mumbai · Kolkata · Chennai · Hyderabad

---

## 🧪 Running Tests
```bash
cd "AI based budget optimization using AI"
python -m pytest tests/ -v
```

---

## 📜 Policy Scenarios

| Policy | AQI Mechanism |
|--------|---------------|
| EV_Adoption | Reduce vehicle density & NOx |
| Industrial_Regulation | Stricter emission caps |
| Renewable_Energy | Coal → renewables transition |
| Waste_Management | Reduce open burning |
| Green_Public_Transport | Metro/BRT expansion |
| Combined_All | All policies simultaneously |

---

## ⚙️ Tech Stack

`Python 3.9+` · `pandas` · `numpy` · `scikit-learn` · `matplotlib` · `requests` · `python-dotenv` · `SQLAlchemy` (Phase 2)

---

## 📁 Outputs

After running `main.py`, all outputs are saved to `green_budget_optimizer/outputs/`:

| File | Description |
|------|-------------|
| `aqi_predictions.png` | Actual vs predicted AQI |
| `cv_scores.png` | R² per CV fold |
| `feature_importance.png` | Top 15 features |
| `policy_comparison.png` | AQI improvement per policy |
| `budget_allocation.png` | Optimal budget distribution |
| `aqi_forest_model.pkl` | Saved trained model |
