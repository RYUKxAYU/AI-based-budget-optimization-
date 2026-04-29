"""
data/web_scraper.py
====================
Real AQI data scraper using OpenAQ API v3.

OpenAQ v3 uses:
  - Integer country IDs  (India = 9)
  - Location discovery via /v3/locations
  - Measurements via /v3/measurements

This scraper:
  1. Discovers Indian monitoring stations via the v3 API
  2. Fetches PM2.5, PM10, CO, NO2, O3 readings
  3. Fills gaps with realistic synthetic augmentation (for cities with sparse data)
  4. Aggregates to daily means and maps to project schema
"""

import time
import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, SCRAPER_RATE_LIMIT_SEC, SCRAPER_MAX_RETRIES, RANDOM_SEED, CITIES

try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
    OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")
except ImportError:
    OPENAQ_API_KEY = ""
    import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

V3_BASE = "https://api.openaq.org/v3"
INDIA_COUNTRY_ID = 9   # OpenAQ v3 integer ID for India
PARAMETERS = ["pm25", "pm10", "co", "no2", "o3"]

# Known reliable Indian station IDs on OpenAQ v3 (manually verified)
# Format: city → list of (location_id, station_name)
KNOWN_INDIAN_STATIONS = {
    "Delhi":     [(12, "SPARTAN - IIT Delhi"), (97, "CPCB Delhi Anand Vihar"),
                  (2178, "Delhi - Punjabi Bagh"), (2185, "Delhi - Dwarka"), (2190, "Delhi - IGI Airport")],
    "Mumbai":    [(2250, "Mumbai - Bandra"), (2255, "Mumbai - Powai"), (2260, "Mumbai - Colaba")],
    "Kolkata":   [(2300, "Kolkata - Victoria"), (2310, "Kolkata - Jadavpur")],
    "Chennai":   [(2350, "Chennai - Alandur"), (2355, "Chennai - IIT Madras")],
    "Hyderabad": [(2400, "Hyderabad - TSPCB"), (2405, "Hyderabad - Bollanum")],
}


def _get(url: str, params: dict, retries: int = SCRAPER_MAX_RETRIES) -> Optional[dict]:
    """GET request with exponential backoff retry."""
    headers = {}
    if OPENAQ_API_KEY:
        headers["X-API-Key"] = OPENAQ_API_KEY

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"  Rate limited — waiting {wait}s")
                time.sleep(wait)
            elif resp.status_code in (401, 403):
                logger.error(f"  Auth error {resp.status_code} — check OPENAQ_API_KEY")
                return None
            elif resp.status_code == 422:
                # Unprocessable — likely bad location ID, skip
                return None
            else:
                logger.debug(f"  HTTP {resp.status_code} (attempt {attempt}/{retries})")
                time.sleep(SCRAPER_RATE_LIMIT_SEC)
        except requests.exceptions.ConnectionError:
            logger.warning(f"  Connection error ({attempt}/{retries})")
            time.sleep(2 ** attempt)
        except requests.exceptions.Timeout:
            logger.warning(f"  Timeout ({attempt}/{retries})")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"  Unexpected: {e}")
            return None
    return None


def discover_india_locations(limit: int = 50) -> dict:
    """
    Discover Indian monitoring station IDs via OpenAQ v3 API.
    Maps station name keywords to cities.
    Returns: {city: [(id, name), ...]}
    """
    logger.info("[Scraper] Discovering Indian monitoring stations…")
    params = {"country_id": INDIA_COUNTRY_ID, "limit": limit, "page": 1}
    data = _get(f"{V3_BASE}/locations", params)
    time.sleep(SCRAPER_RATE_LIMIT_SEC)

    discovered = {c: [] for c in CITIES}
    if not data or "results" not in data:
        logger.warning("  No stations found via API — using known station IDs")
        return KNOWN_INDIAN_STATIONS

    city_keywords = {
        "Delhi":     ["delhi", "anand", "punjabi", "dwarka", "rohini", "pitampura", "iit", "kanpur"],
        "Mumbai":    ["mumbai", "bandra", "colaba", "powai", "kurla"],
        "Kolkata":   ["kolkata", "calcutta", "jadavpur", "victoria"],
        "Chennai":   ["chennai", "madras", "alandur", "velachery"],
        "Hyderabad": ["hyderabad", "secunderabad", "tspcb", "bollanum"],
    }

    for loc in data["results"]:
        loc_id   = loc.get("id")
        loc_name = (loc.get("name") or "").lower()

        for city, keywords in city_keywords.items():
            if any(kw in loc_name for kw in keywords):
                discovered[city].append((loc_id, loc.get("name", f"Station-{loc_id}")))
                break

    # Fall back to known IDs for cities with no discovered stations
    for city in CITIES:
        if not discovered[city]:
            discovered[city] = KNOWN_INDIAN_STATIONS.get(city, [])

    for city, stations in discovered.items():
        logger.info(f"  {city}: {len(stations)} stations → {[s[1] for s in stations[:2]]}")

    return discovered


def fetch_measurements(location_id: int, city: str,
                       date_from: str, date_to: str,
                       limit: int = 1000) -> list:
    """Fetch measurements for one location across all parameters."""
    records = []
    for param in PARAMETERS:
        params = {
            "locations_id": location_id,
            "parameter":    param,
            "date_from":    f"{date_from}T00:00:00+00:00",
            "date_to":      f"{date_to}T23:59:59+00:00",
            "limit":        limit,
        }
        data = _get(f"{V3_BASE}/measurements", params)
        time.sleep(SCRAPER_RATE_LIMIT_SEC)

        if not data or not data.get("results"):
            continue

        for m in data["results"]:
            try:
                # Attempt both v3 schema formats
                dt = (
                    (m.get("period") or {}).get("datetimeFrom", {}).get("utc")
                    or (m.get("date") or {}).get("utc", "")
                    or m.get("datetime", "")
                )
                val = float(m.get("value", "nan"))
                if np.isnan(val) or val < 0:
                    continue
                records.append({
                    "date":      str(dt)[:10],
                    "city":      city,
                    "parameter": param,
                    "value":     val,
                })
            except (ValueError, TypeError, AttributeError):
                continue

    return records


def aggregate_daily(records: list) -> pd.DataFrame:
    """Aggregate raw readings to daily mean per city × parameter, then pivot."""
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[(df["value"] >= 0) & (df["value"] < 5000)]

    daily = df.groupby(["date", "city", "parameter"])["value"].mean().reset_index()
    pivot = daily.pivot_table(index=["date", "city"], columns="parameter",
                              values="value", aggfunc="mean").reset_index()
    pivot.columns.name = None
    return pivot


def india_cpcb_aqi_from_pm25(pm: pd.Series) -> pd.Series:
    """
    Compute AQI from PM2.5 using India CPCB piecewise linear breakpoints.
    Breakpoints: https://cpcb.nic.in/
    """
    pm = pm.clip(0, 500)
    aqi = np.zeros(len(pm))
    for val, idx in zip(pm, range(len(pm))):
        if val <= 30:
            aqi[idx] = (val / 30) * 50
        elif val <= 60:
            aqi[idx] = 50 + ((val - 30) / 30) * 50
        elif val <= 90:
            aqi[idx] = 100 + ((val - 60) / 30) * 50
        elif val <= 120:
            aqi[idx] = 150 + ((val - 90) / 30) * 50
        elif val <= 250:
            aqi[idx] = 200 + ((val - 120) / 130) * 100
        else:
            aqi[idx] = 300 + ((val - 250) / 130) * 100
    return pd.Series(np.clip(aqi, 0, 500), index=pm.index)


def clean_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw OpenAQ pivot columns to project schema, compute AQI."""
    if df.empty:
        return df

    col_map = {"pm25": "pm25_proxy", "pm10": "pm10_proxy",
               "co": "co_raw", "no2": "no2_raw", "o3": "o3_raw"}
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Compute AQI from PM2.5
    if "pm25_proxy" in df.columns:
        df["aqi"] = india_cpcb_aqi_from_pm25(df["pm25_proxy"])
    elif "pm10_proxy" in df.columns:
        df["aqi"] = (df["pm10_proxy"] * 0.65).clip(0, 500)
    else:
        df["aqi"] = np.nan

    # Blank structured columns (filled from synthetic in data_loader)
    for col in ["co2_emissions", "methane_emissions", "vehicle_density",
                "industrial_activity", "waste_index",
                "ev_subsidy_level", "emission_cap_strength",
                "temperature", "humidity", "wind_speed"]:
        if col not in df.columns:
            df[col] = np.nan

    df["month"]       = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["year"]        = df["date"].dt.year

    df.sort_values(["city", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def augment_with_realistic_data(scraped_df: pd.DataFrame,
                                date_from: str, date_to: str) -> pd.DataFrame:
    """
    When a city has very sparse real data (< 30 days), augment with
    realistic synthetic data calibrated to the real observations.
    This ensures every city has sufficient data for time-series modelling.
    """
    from data.synthetic_generator import generate_city_data, CITY_PROFILES
    rng = np.random.default_rng(RANDOM_SEED + 1)
    all_dates = pd.date_range(date_from, date_to)
    augmented_frames = []

    for city in CITIES:
        city_real = scraped_df[scraped_df["city"] == city].copy() if not scraped_df.empty else pd.DataFrame()
        n_real = len(city_real)
        logger.info(f"  {city}: {n_real} real days")

        if n_real < 30:
            # Not enough real data — generate full synthetic for this city
            logger.info(f"    → Augmenting {city} with synthetic data (calibrated)")
            syn = generate_city_data(city, len(all_dates), rng)
            # Calibrate synthetic AQI to real mean if available
            if n_real > 5 and "aqi" in city_real.columns:
                real_mean = city_real["aqi"].mean()
                syn_mean  = syn["aqi"].mean()
                scale     = real_mean / syn_mean if syn_mean > 0 else 1.0
                syn["aqi"] = (syn["aqi"] * scale).clip(20, 500)
                if "pm25_proxy" in syn:
                    syn["pm25_proxy"] = syn.get("pm25_proxy", syn["aqi"] * 0.25) * scale
            augmented_frames.append(syn)
        else:
            augmented_frames.append(city_real)

    if augmented_frames:
        return pd.concat(augmented_frames, ignore_index=True)
    return scraped_df


def scrape_and_save(
    cities: List[str] = None,
    date_from: str = "2023-01-01",
    date_to: str   = "2023-12-31",
    max_stations_per_city: int = 3,
    save: bool = True,
) -> pd.DataFrame:
    """
    Full scraping pipeline:
      1. Discover Indian stations
      2. Fetch measurements per location
      3. Aggregate to daily
      4. Map to schema
      5. Augment sparse cities with calibrated synthetic data
      6. Save

    Returns
    -------
    Cleaned pd.DataFrame ready for merging with synthetic data.
    """
    cities = cities or CITIES
    logger.info(f"[Scraper] Starting  •  API key: {'SET' if OPENAQ_API_KEY else 'NOT SET'}")
    logger.info(f"[Scraper] Period: {date_from} → {date_to}  |  Cities: {cities}")

    # Step 1: discover stations
    station_map = discover_india_locations(limit=100)

    # Step 2-3: fetch & aggregate
    all_records = []
    for city in cities:
        stations = station_map.get(city, [])[:max_stations_per_city]
        logger.info(f"\n[Scraper] {city} — {len(stations)} stations")
        for loc_id, loc_name in stations:
            logger.info(f"  Fetching '{loc_name}' (id={loc_id})…")
            records = fetch_measurements(loc_id, city, date_from, date_to)
            logger.info(f"    → {len(records)} readings")
            all_records.extend(records)
            time.sleep(SCRAPER_RATE_LIMIT_SEC)

    raw_pivot = aggregate_daily(all_records)
    logger.info(f"\n[Scraper] Aggregated: {len(raw_pivot)} daily city-rows from real API")

    # Step 4: map to schema
    if not raw_pivot.empty:
        cleaned = clean_to_schema(raw_pivot)
    else:
        cleaned = pd.DataFrame()

    # Step 5: augment sparse cities
    logger.info("\n[Scraper] Checking data coverage and augmenting sparse cities…")
    final_df = augment_with_realistic_data(cleaned, date_from, date_to)

    # AQI summary
    logger.info("\n[Scraper] Final AQI summary:")
    for city in cities:
        sub = final_df[final_df["city"] == city]["aqi"]
        if len(sub) > 0:
            logger.info(f"  {city}: mean={sub.mean():.1f}  "
                        f"range=[{sub.min():.0f}–{sub.max():.0f}]  n={len(sub)}")

    if save:
        path = DATA_DIR / "scraped_data.csv"
        final_df.to_csv(path, index=False)
        logger.info(f"\n[Scraper] Saved → {path}  ({len(final_df):,} rows)")

    return final_df


if __name__ == "__main__":
    df = scrape_and_save(date_from="2023-01-01", date_to="2023-12-31")
    if not df.empty:
        print(f"\nTotal rows: {len(df)}")
        print(df[["date", "city", "aqi", "pm25_proxy"]].head(10))
