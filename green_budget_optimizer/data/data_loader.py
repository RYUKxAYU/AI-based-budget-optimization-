"""
data/data_loader.py
====================
Unified data loading, merging and cleaning pipeline.

Handles:
  - Loading synthetic dataset
  - Optionally merging with scraped real data
  - Missing value imputation
  - Exports processed_dataset.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
    DATA_SOURCE = os.getenv("DATA_SOURCE", "synthetic")
except ImportError:
    DATA_SOURCE = "synthetic"


def load_synthetic() -> pd.DataFrame:
    """Load the pre-generated synthetic dataset."""
    path = DATA_DIR / "synthetic_dataset.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Synthetic dataset not found at {path}.\n"
            "Run: python data/synthetic_generator.py"
        )
    df = pd.read_csv(path, parse_dates=["date"])
    logger.info(f"[DataLoader] Loaded synthetic data: {len(df):,} rows")
    return df


def load_scraped() -> pd.DataFrame:
    """Load the scraped real dataset — run scraper if CSV doesn't exist."""
    path = DATA_DIR / "scraped_data.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=["date"])
        logger.info(f"[DataLoader] Loaded scraped data: {len(df):,} rows")
        return df
    logger.info("[DataLoader] No scraped CSV found — running scraper now…")
    try:
        from data.web_scraper import scrape_and_save
        df = scrape_and_save(save=True)
        logger.info(f"[DataLoader] Scraper returned {len(df):,} rows")
        return df
    except Exception as e:
        logger.warning(f"[DataLoader] Scraper failed ({e}) — falling back to synthetic only")
        return pd.DataFrame()



def _impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values using city-specific forward-fill + linear interpolation.
    Remaining NaNs filled with column median.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Per-city forward fill (handles gaps in time-series)
    df = df.sort_values(["city", "date"])
    df[numeric_cols] = (
        df.groupby("city")[numeric_cols]
        .transform(lambda x: x.ffill().bfill())
    )

    # Linear interpolation for remaining gaps
    df[numeric_cols] = df[numeric_cols].interpolate(method="linear", limit_direction="both")

    # Fill any remaining NaN with column median
    for col in numeric_cols:
        if df[col].isna().any():
            df[col].fillna(df[col].median(), inplace=True)

    return df


def merge_datasets(synthetic: pd.DataFrame, real: pd.DataFrame) -> pd.DataFrame:
    """
    Merge synthetic and real datasets. Real data overrides synthetic where available.

    Strategy:
    - For cities present in real data: use real values for key columns
    - Remaining missing values filled from synthetic baselines
    """
    if real.empty:
        logger.info("[DataLoader] Using synthetic data only.")
        return synthetic.copy()

    # Identify overlapping date-city combinations
    real_keys = set(zip(real["city"], real["date"].dt.date))
    syn_mask = synthetic.apply(
        lambda r: (r["city"], r["date"].date()) in real_keys, axis=1
    )
    logger.info(f"[DataLoader] Real data covers {syn_mask.sum()} synthetic rows — merging.")

    # Merge on date + city, prefer real values
    merged = pd.merge(
        synthetic,
        real[["date", "city", "aqi", "pm25_proxy", "pm10_proxy"]],
        on=["date", "city"],
        how="left",
        suffixes=("_syn", "_real")
    )

    # Prefer real AQI where available
    for col in ["aqi", "pm25_proxy", "pm10_proxy"]:
        real_col = f"{col}_real"
        syn_col = f"{col}_syn"
        if real_col in merged.columns:
            merged[col] = merged[real_col].fillna(merged[syn_col])
            merged.drop(columns=[real_col, syn_col], errors="ignore", inplace=True)

    return merged


def load_data(use_real: bool = None) -> pd.DataFrame:
    """
    Main data loading function.

    Parameters
    ----------
    use_real : If True, attempt to merge scraped real data.
               If None, reads from DATA_SOURCE env variable.

    Returns
    -------
    Cleaned, merged pd.DataFrame ready for feature engineering
    """
    if use_real is None:
        use_real = (DATA_SOURCE == "real")

    synthetic = load_synthetic()
    real = load_scraped() if use_real else pd.DataFrame()

    df = merge_datasets(synthetic, real)
    df = _impute_missing(df)

    # Ensure correct dtypes
    df["date"] = pd.to_datetime(df["date"])
    df["city"] = df["city"].astype("category")
    df["month"] = df["month"].astype(int)
    df["year"] = df["year"].astype(int)

    # Save processed dataset
    out_path = DATA_DIR / "processed_dataset.csv"
    df.to_csv(out_path, index=False)
    logger.info(f"[DataLoader] Processed dataset saved → {out_path}  ({len(df):,} rows)")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    df = load_data()
    print(f"\nProcessed dataset shape: {df.shape}")
    print(df.dtypes)
    print(df.head(3))
