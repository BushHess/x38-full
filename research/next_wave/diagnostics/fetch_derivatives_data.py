#!/usr/bin/env python3
"""Fetch minimum viable derivatives data for D1.3 diagnostics.

Fetches from Binance Futures public API (no auth):
  1. Funding rates (8h intervals)
  2. Open interest history (H4)
  3. Perp H4 klines (for basis = perp_close - spot_close)

Output: derivatives_btcusdt.csv
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

SYMBOL = "BTCUSDT"
OUTDIR = Path(__file__).resolve().parent / "artifacts"

# Start from Sep 2019 (Binance Futures launch was ~Sep 2019)
START_MS = int(datetime(2019, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
END_MS = int(datetime(2026, 2, 21, tzinfo=timezone.utc).timestamp() * 1000)


def fetch_funding_rates() -> pd.DataFrame:
    """Fetch all BTCUSDT funding rates from Binance Futures API."""
    print("  Fetching funding rates...")
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    all_rows = []
    cursor = START_MS

    while cursor < END_MS:
        params = {
            "symbol": SYMBOL,
            "startTime": cursor,
            "endTime": END_MS,
            "limit": 1000,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        all_rows.extend(data)
        # Advance past last received timestamp
        cursor = data[-1]["fundingTime"] + 1
        if len(data) < 1000:
            break
        time.sleep(0.2)

    df = pd.DataFrame(all_rows)
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df["fundingTime"] = df["fundingTime"].astype(int)
    df["markPrice"] = pd.to_numeric(df["markPrice"], errors="coerce")
    print(f"    Got {len(df)} funding rate records")
    print(f"    Range: {pd.to_datetime(df['fundingTime'].min(), unit='ms')} "
          f"to {pd.to_datetime(df['fundingTime'].max(), unit='ms')}")
    return df


def fetch_oi_history() -> pd.DataFrame:
    """Fetch BTCUSDT open interest history.

    NOTE: Binance openInterestHist endpoint only returns ~30 days of data.
    Paginate backward from endTime to get what's available.
    """
    print("  Fetching open interest history...")
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    all_rows = []
    end_cursor = END_MS

    for batch in range(200):
        params = {
            "symbol": SYMBOL,
            "period": "4h",
            "endTime": end_cursor,
            "limit": 500,
        }
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429:
            print("    Rate limited, waiting 60s...")
            time.sleep(60)
            continue
        if r.status_code != 200:
            print(f"    OI endpoint returned {r.status_code}, stopping")
            break
        data = r.json()
        if not data:
            break
        all_rows.extend(data)
        earliest = min(d["timestamp"] for d in data)
        end_cursor = earliest - 1
        if len(data) < 500:
            break
        time.sleep(0.5)

    if not all_rows:
        print("    No OI data returned (endpoint likely limited to recent data)")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["timestamp"] = df["timestamp"].astype(int)
    df["sumOpenInterest"] = pd.to_numeric(df["sumOpenInterest"], errors="coerce")
    df["sumOpenInterestValue"] = pd.to_numeric(df["sumOpenInterestValue"], errors="coerce")
    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    print(f"    Got {len(df)} OI records")
    print(f"    Range: {pd.to_datetime(df['timestamp'].min(), unit='ms')} "
          f"to {pd.to_datetime(df['timestamp'].max(), unit='ms')}")
    print(f"    WARNING: OI data only covers recent period, NOT full diagnostic window")
    return df


def fetch_perp_klines() -> pd.DataFrame:
    """Fetch BTCUSDT perpetual H4 klines for basis computation."""
    print("  Fetching perp H4 klines...")
    url = "https://fapi.binance.com/fapi/v1/klines"
    all_rows = []
    cursor = START_MS

    while cursor < END_MS:
        params = {
            "symbol": SYMBOL,
            "interval": "4h",
            "startTime": cursor,
            "endTime": END_MS,
            "limit": 1500,
        }
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429:
            print("    Rate limited, waiting 60s...")
            time.sleep(60)
            continue
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        for row in data:
            all_rows.append({
                "open_time": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "close_time": int(row[6]),
            })
        cursor = data[-1][6] + 1  # close_time + 1
        if len(data) < 1500:
            break
        time.sleep(0.2)

    df = pd.DataFrame(all_rows)
    print(f"    Got {len(df)} perp H4 bars")
    if len(df) > 0:
        print(f"    Range: {pd.to_datetime(df['open_time'].min(), unit='ms')} "
              f"to {pd.to_datetime(df['open_time'].max(), unit='ms')}")
    return df


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Fetching BTCUSDT derivatives data")
    print("=" * 60)

    funding = fetch_funding_rates()
    oi = fetch_oi_history()
    perp = fetch_perp_klines()

    # Save raw data
    funding.to_csv(OUTDIR / "funding_btcusdt.csv", index=False)
    if len(oi) > 0:
        oi.to_csv(OUTDIR / "oi_btcusdt.csv", index=False)
    if len(perp) > 0:
        perp.to_csv(OUTDIR / "perp_klines_btcusdt_4h.csv", index=False)

    print(f"\nSaved to {OUTDIR}/")
    print(f"  funding_btcusdt.csv: {len(funding)} rows")
    print(f"  oi_btcusdt.csv: {len(oi)} rows")
    print(f"  perp_klines_btcusdt_4h.csv: {len(perp)} rows")


if __name__ == "__main__":
    main()
