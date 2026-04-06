"""
preprocessing/feature_engineering.py
======================================
Feature engineering for AQI time-series prediction.

Features created:
  - AQI lag features (lag 1, 2, 3, 6)
  - Rolling mean & std (7-day, 30-day windows)
  - Volatility indicator (rolling coefficient of variation)
  - Cyclic encoding of month & day_of_year (sin/cos)
  - AQI category (Good / Moderate / Unhealthy / etc.)

Target:
  - aqi_ahead_24: AQI shifted 24 days into the future (per city)
"""

import pandas as pd
import numpy as np
from typing import Tuple, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LAG_PERIODS, ROLLING_WINDOWS, FORECAST_HORIZON


def add_lag_features(df: pd.DataFrame, target_col: str = "aqi",
                     lags: List[int] = LAG_PERIODS) -> pd.DataFrame:
    """
    Add lag features for a given column, computed per city.

    Parameters
    ----------
    df         : DataFrame sorted by [city, date]
    target_col : Column to lag (default: 'aqi')
    lags       : List of lag periods in days

    Returns
    -------
    DataFrame with new columns: {target_col}_lag_{n} for each n in lags
    """
    df = df.copy()
    for lag in lags:
        col_name = f"{target_col}_lag_{lag}"
        df[col_name] = df.groupby("city")[target_col].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, target_col: str = "aqi",
                         windows: List[int] = ROLLING_WINDOWS) -> pd.DataFrame:
    """
    Add rolling mean and std features per city.

    Parameters
    ----------
    df         : DataFrame sorted by [city, date]
    target_col : Column to compute rolling stats on
    windows    : List of rolling window sizes in days

    Returns
    -------
    DataFrame with new columns:
      {target_col}_rolling_mean_{w}, {target_col}_rolling_std_{w}
    """
    df = df.copy()
    for w in windows:
        df[f"{target_col}_rolling_mean_{w}"] = (
            df.groupby("city")[target_col]
            .transform(lambda x: x.rolling(w, min_periods=1).mean())
        )
        df[f"{target_col}_rolling_std_{w}"] = (
            df.groupby("city")[target_col]
            .transform(lambda x: x.rolling(w, min_periods=1).std().fillna(0))
        )
    return df


def add_volatility_indicator(df: pd.DataFrame, target_col: str = "aqi",
                              window: int = 7) -> pd.DataFrame:
    """
    Add a volatility indicator: coefficient of variation (std / mean) per city.

    High volatility → pollution spike events are likely.
    """
    df = df.copy()
    rolling_mean = df.groupby("city")[target_col].transform(
        lambda x: x.rolling(window, min_periods=1).mean()
    )
    rolling_std = df.groupby("city")[target_col].transform(
        lambda x: x.rolling(window, min_periods=1).std().fillna(0)
    )
    df["aqi_volatility"] = (rolling_std / rolling_mean.replace(0, 1)).round(4)
    return df


def add_cyclic_encoding(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode month and day_of_year as cyclic sin/cos features.
    Prevents the model from treating Jan (1) and Dec (12) as distant.
    """
    df = df.copy()
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["day_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["day_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)
    return df


def add_aqi_category(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add CPCB AQI category as an ordinal integer feature.

    AQI Buckets (India CPCB standard):
      0–50:  Good (0)
      51–100: Satisfactory (1)
      101–200: Moderate (2)
      201–300: Poor (3)
      301–400: Very Poor (4)
      401+:  Severe (5)
    """
    df = df.copy()
    bins = [-1, 50, 100, 200, 300, 400, 501]
    labels = [0, 1, 2, 3, 4, 5]
    df["aqi_category"] = pd.cut(df["aqi"], bins=bins, labels=labels).astype(int)
    return df


def add_city_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """Add one-hot encoded city columns (drop first to avoid multicollinearity)."""
    df = df.copy()
    city_dummies = pd.get_dummies(df["city"], prefix="city", drop_first=True)
    df = pd.concat([df, city_dummies], axis=1)
    return df


def create_target(df: pd.DataFrame, target_col: str = "aqi",
                  horizon: int = FORECAST_HORIZON) -> pd.DataFrame:
    """
    Create the forecast target: AQI {horizon} days ahead, per city.

    Parameters
    ----------
    df         : DataFrame sorted by [city, date]
    target_col : Source column
    horizon    : Forecast horizon in days (default: 24)

    Returns
    -------
    DataFrame with new column: aqi_ahead_{horizon}
    """
    df = df.copy()
    target_name = f"aqi_ahead_{horizon}"
    df[target_name] = df.groupby("city")[target_col].shift(-horizon)
    return df, target_name


def engineer_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, str, List[str]]:
    """
    Full feature engineering pipeline.

    Parameters
    ----------
    df : Raw processed DataFrame from data_loader

    Returns
    -------
    Tuple of:
      - Feature-engineered DataFrame (NaN rows dropped)
      - Target column name (str)
      - List of feature column names
    """
    print("[FeatureEngineering] Starting feature engineering pipeline…")

    df = df.sort_values(["city", "date"]).copy()

    # Core feature engineering steps
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_volatility_indicator(df)
    df = add_cyclic_encoding(df)
    df = add_aqi_category(df)
    df = add_city_dummies(df)

    # Create forecast target
    df, target_col = create_target(df)

    # Drop rows where target or lag features are NaN
    df.dropna(subset=[target_col], inplace=True)

    # Feature columns: all numeric except original aqi & date columns
    exclude = {
        "date", "city", "aqi", target_col,
        "month", "day_of_year", "year"
    }
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c not in exclude]

    # Drop any remaining NaN rows in features
    df.dropna(subset=feature_cols, inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"  ✓ Total features: {len(feature_cols)}")
    print(f"  ✓ Dataset shape after engineering: {df.shape}")
    print(f"  ✓ Target column: '{target_col}'")

    return df, target_col, feature_cols


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.data_loader import load_data

    raw = load_data()
    df_fe, target, features = engineer_features(raw)
    print(f"\nTop 10 features: {features[:10]}")
    print(df_fe[[target] + features[:5]].describe().round(2))
