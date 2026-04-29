"""
tests/test_feature_engineering.py
===================================
Unit tests for preprocessing/feature_engineering.py
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Add green_budget_optimizer to path
ROOT = Path(__file__).parent.parent / "green_budget_optimizer"
sys.path.insert(0, str(ROOT))

from preprocessing.feature_engineering import (
    add_lag_features,
    add_rolling_features,
    add_volatility_indicator,
    add_cyclic_encoding,
    add_aqi_category,
    create_target,
    engineer_features,
)


@pytest.fixture
def sample_df():
    """Minimal synthetic DataFrame for testing feature engineering."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2020-01-01", periods=n)
    df = pd.DataFrame({
        "date":        dates,
        "city":        ["Delhi"] * n,
        "aqi":         np.random.uniform(50, 300, n),
        "pm25":        np.random.uniform(20, 150, n),
        "pm10":        np.random.uniform(30, 200, n),
        "no2":         np.random.uniform(10, 80, n),
        "co":          np.random.uniform(0.5, 5.0, n),
        "month":       dates.month,
        "day_of_year": dates.day_of_year,
        "year":        dates.year,
    })
    return df


class TestLagFeatures:
    def test_creates_lag_columns(self, sample_df):
        out = add_lag_features(sample_df, lags=[1, 3])
        assert "aqi_lag_1" in out.columns
        assert "aqi_lag_3" in out.columns

    def test_lag_1_is_shifted(self, sample_df):
        out = add_lag_features(sample_df, lags=[1])
        # Row 1 lag_1 == Row 0 aqi (within same city group)
        assert out["aqi_lag_1"].iloc[1] == pytest.approx(out["aqi"].iloc[0])

    def test_first_row_lag_is_nan(self, sample_df):
        out = add_lag_features(sample_df, lags=[1])
        assert pd.isna(out["aqi_lag_1"].iloc[0])


class TestRollingFeatures:
    def test_creates_rolling_columns(self, sample_df):
        out = add_rolling_features(sample_df, windows=[7])
        assert "aqi_rolling_mean_7" in out.columns
        assert "aqi_rolling_std_7" in out.columns

    def test_rolling_mean_not_null(self, sample_df):
        out = add_rolling_features(sample_df, windows=[7])
        # min_periods=1 so no NaN
        assert out["aqi_rolling_mean_7"].notna().all()


class TestVolatilityIndicator:
    def test_volatility_column_exists(self, sample_df):
        out = add_volatility_indicator(sample_df)
        assert "aqi_volatility" in out.columns

    def test_volatility_non_negative(self, sample_df):
        out = add_volatility_indicator(sample_df)
        assert (out["aqi_volatility"] >= 0).all()


class TestCyclicEncoding:
    def test_creates_sin_cos_columns(self, sample_df):
        out = add_cyclic_encoding(sample_df)
        for col in ["month_sin", "month_cos", "day_sin", "day_cos"]:
            assert col in out.columns

    def test_values_in_range(self, sample_df):
        out = add_cyclic_encoding(sample_df)
        for col in ["month_sin", "month_cos"]:
            assert out[col].between(-1, 1).all()


class TestAQICategory:
    def test_category_column_exists(self, sample_df):
        out = add_aqi_category(sample_df)
        assert "aqi_category" in out.columns

    def test_category_values_valid(self, sample_df):
        out = add_aqi_category(sample_df)
        assert out["aqi_category"].isin([0, 1, 2, 3, 4, 5]).all()


class TestCreateTarget:
    def test_target_column_created(self, sample_df):
        out, name = create_target(sample_df, horizon=5)
        assert name == "aqi_ahead_5"
        assert name in out.columns

    def test_target_has_trailing_nans(self, sample_df):
        out, name = create_target(sample_df, horizon=5)
        # Last 5 rows should be NaN (no future data)
        assert out[name].iloc[-1] is np.nan or pd.isna(out[name].iloc[-1])


class TestEngineerFeatures:
    def test_returns_three_items(self, sample_df):
        result = engineer_features(sample_df)
        assert len(result) == 3

    def test_no_nans_in_features(self, sample_df):
        df_fe, target_col, feature_cols = engineer_features(sample_df)
        assert df_fe[feature_cols].isna().sum().sum() == 0

    def test_target_col_in_dataframe(self, sample_df):
        df_fe, target_col, _ = engineer_features(sample_df)
        assert target_col in df_fe.columns

    def test_feature_list_nonempty(self, sample_df):
        _, _, feature_cols = engineer_features(sample_df)
        assert len(feature_cols) > 0
