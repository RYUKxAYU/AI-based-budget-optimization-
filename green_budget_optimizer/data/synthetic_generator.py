"""
data/synthetic_generator.py
============================
Generates a realistic synthetic environmental dataset aligned with
the research paper's methodology.

Features generated:
  - AQI (time-series per city with seasonal patterns)
  - CO2, Methane emissions
  - Vehicle density, industrial activity, waste metrics
  - Policy indicators (EV subsidies, emission caps)

Correlations enforced:
  - Higher emissions → Higher AQI
  - Winter months (Nov–Feb): AQI spike
  - Gaussian noise for real-world variability
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Allow running standalone
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CITIES, N_SAMPLES_PER_CITY, START_DATE, END_DATE,
    RANDOM_SEED, DATA_DIR
)


# ─── City-specific pollution baselines ───────────────────────────────────────
CITY_PROFILES = {
    "Delhi":     {"aqi_base": 220, "co2_base": 3.8, "vehicle_base": 0.85, "industrial_base": 0.75},
    "Mumbai":    {"aqi_base": 145, "co2_base": 2.9, "vehicle_base": 0.78, "industrial_base": 0.70},
    "Kolkata":   {"aqi_base": 160, "co2_base": 3.1, "vehicle_base": 0.65, "industrial_base": 0.80},
    "Chennai":   {"aqi_base": 115, "co2_base": 2.5, "vehicle_base": 0.60, "industrial_base": 0.65},
    "Hyderabad": {"aqi_base": 130, "co2_base": 2.7, "vehicle_base": 0.62, "industrial_base": 0.68},
}


def _seasonal_multiplier(month: int) -> float:
    """Return a pollution multiplier based on month. Winter months peak."""
    # Nov=11, Dec=12, Jan=1, Feb=2 → high pollution
    winter_months = {11: 1.45, 12: 1.60, 1: 1.55, 2: 1.40}
    # Oct and Mar are transition months
    transition = {10: 1.20, 3: 1.15}
    # Monsoon months clean air
    monsoon = {6: 0.80, 7: 0.75, 8: 0.78, 9: 0.82}
    return winter_months.get(month, transition.get(month, monsoon.get(month, 1.0)))


def generate_city_data(city: str, n_samples: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate a synthetic time-series dataset for one city.

    Parameters
    ----------
    city     : Name of the city
    n_samples: Number of daily observations to generate
    rng      : NumPy random generator for reproducibility

    Returns
    -------
    pd.DataFrame with columns: date, city, aqi, co2_emissions,
        methane_emissions, vehicle_density, industrial_activity,
        waste_index, ev_subsidy_level, emission_cap_strength,
        pm25_proxy, pm10_proxy, temperature, humidity, wind_speed
    """
    profile = CITY_PROFILES[city]

    # Generate date range
    dates = pd.date_range(start=START_DATE, periods=n_samples, freq="D")

    # ── Seasonal multipliers per date ────────────────────────────────────
    seasonal = np.array([_seasonal_multiplier(d.month) for d in dates])

    # ── Policy indicators (0–1 scale, slowly improving over years) ───────
    years_elapsed = (dates - pd.Timestamp(START_DATE)).days / 365.0
    ev_subsidy = np.clip(0.2 + 0.08 * years_elapsed + rng.normal(0, 0.03, n_samples), 0, 1)
    emission_cap = np.clip(0.3 + 0.06 * years_elapsed + rng.normal(0, 0.02, n_samples), 0, 1)

    # ── Industrial & vehicle activity ────────────────────────────────────
    industrial = (profile["industrial_base"]
                  - 0.05 * years_elapsed                           # slow improvement
                  + 0.08 * seasonal                                # winter: more industry
                  - 0.10 * emission_cap                            # caps reduce activity
                  + rng.normal(0, 0.05, n_samples))
    industrial = np.clip(industrial, 0.1, 1.0)

    vehicle = (profile["vehicle_base"]
               + 0.02 * years_elapsed                              # rising urbanisation
               - 0.12 * ev_subsidy                                 # EVs reduce vehicles
               + 0.05 * seasonal                                   # festival use spikes
               + rng.normal(0, 0.04, n_samples))
    vehicle = np.clip(vehicle, 0.1, 1.0)

    # ── Emissions (correlated with industrial & vehicle density) ─────────
    co2 = (profile["co2_base"]
           + 0.8 * industrial
           + 0.5 * vehicle
           - 0.3 * ev_subsidy
           + 0.4 * seasonal
           + rng.normal(0, 0.15, n_samples))
    co2 = np.clip(co2, 0.5, 8.0)

    methane = (0.45 * co2
               + 0.2 * industrial
               + rng.normal(0, 0.08, n_samples))
    methane = np.clip(methane, 0.1, 4.0)

    # ── Waste index ──────────────────────────────────────────────────────
    waste = (0.5
             + 0.15 * industrial
             + 0.12 * vehicle
             - 0.08 * emission_cap
             + rng.normal(0, 0.07, n_samples))
    waste = np.clip(waste, 0.0, 1.0)

    # ── Meteorological variables ─────────────────────────────────────────
    # Temperature: seasonal (summer peaks in Apr–Jun)
    temp_base = 20 + 15 * np.sin(2 * np.pi * (dates.dayofyear - 80) / 365)
    temperature = temp_base + rng.normal(0, 3, n_samples)

    # Humidity: higher in monsoon, lower in winter
    humidity_base = 55 + 30 * np.sin(2 * np.pi * (dates.dayofyear - 200) / 365)
    humidity = np.clip(humidity_base + rng.normal(0, 8, n_samples), 10, 100)

    # Wind speed: lower in winter → traps pollution
    wind_base = 12 - 5 * (seasonal - 1)  # winter has lower wind
    wind_speed = np.clip(wind_base + rng.normal(0, 2.5, n_samples), 0.5, 40)

    # ── AQI (main target variable) ───────────────────────────────────────
    # AQI is a function of all pollution sources + weather
    aqi = (profile["aqi_base"]
           + 45 * co2
           + 30 * methane
           + 25 * industrial
           + 20 * vehicle
           + 15 * waste
           + 60 * seasonal
           - 20 * ev_subsidy
           - 15 * emission_cap
           - 1.5 * wind_speed          # wind disperses pollution
           + 0.5 * humidity            # humidity traps particles
           + rng.normal(0, 20, n_samples))  # real-world noise
    aqi = np.clip(aqi, 20, 500)

    # ── PM2.5 / PM10 proxies ─────────────────────────────────────────────
    pm25 = np.clip(0.45 * aqi + rng.normal(0, 8, n_samples), 5, 250)
    pm10 = np.clip(0.75 * aqi + rng.normal(0, 12, n_samples), 10, 400)

    return pd.DataFrame({
        "date":              dates,
        "city":              city,
        "aqi":               np.round(aqi, 2),
        "co2_emissions":     np.round(co2, 3),
        "methane_emissions": np.round(methane, 3),
        "vehicle_density":   np.round(vehicle, 3),
        "industrial_activity": np.round(industrial, 3),
        "waste_index":       np.round(waste, 3),
        "ev_subsidy_level":  np.round(ev_subsidy, 3),
        "emission_cap_strength": np.round(emission_cap, 3),
        "pm25_proxy":        np.round(pm25, 2),
        "pm10_proxy":        np.round(pm10, 2),
        "temperature":       np.round(temperature, 1),
        "humidity":          np.round(humidity, 1),
        "wind_speed":        np.round(wind_speed, 1),
        "month":             dates.month,
        "day_of_year":       dates.dayofyear,
        "year":              dates.year,
    })


def generate_full_dataset(save: bool = True) -> pd.DataFrame:
    """
    Generate synthetic data for all configured cities and merge into one DataFrame.

    Parameters
    ----------
    save : If True, saves the raw synthetic dataset to data/synthetic_dataset.csv

    Returns
    -------
    pd.DataFrame with ~10,000 rows (N_SAMPLES_PER_CITY × len(CITIES))
    """
    rng = np.random.default_rng(RANDOM_SEED)
    frames = []

    print(f"[SyntheticGenerator] Generating data for {len(CITIES)} cities "
          f"({N_SAMPLES_PER_CITY} samples each)…")

    for city in CITIES:
        df_city = generate_city_data(city, N_SAMPLES_PER_CITY, rng)
        frames.append(df_city)
        print(f"  ✓ {city}: {len(df_city):,} rows  | AQI range: "
              f"[{df_city['aqi'].min():.0f}, {df_city['aqi'].max():.0f}]")

    df = pd.concat(frames, ignore_index=True)
    df.sort_values(["city", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    if save:
        output_path = DATA_DIR / "synthetic_dataset.csv"
        df.to_csv(output_path, index=False)
        print(f"\n[SyntheticGenerator] Dataset saved → {output_path}")
        print(f"  Total rows: {len(df):,}  |  Columns: {list(df.columns)}")

    return df


if __name__ == "__main__":
    df = generate_full_dataset(save=True)
    print("\nSample (head 5):")
    print(df.head())
    print("\nDescriptive stats (AQI per city):")
    print(df.groupby("city")["aqi"].describe().round(1))
