"""
Phase 1: Data Audit for X27 research.
Loads all 4 BTCUSDT CSV files, checks quality, outputs tables and summary.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────
DATA_DIR = Path("/var/www/trading-bots/btc-spot-dev/data")
OUT_DIR = Path("/var/www/trading-bots/btc-spot-dev/research/x27")
TBL_DIR = OUT_DIR / "tables"
TBL_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "15m": DATA_DIR / "btcusdt_15m.csv",
    "1h":  DATA_DIR / "btcusdt_1h.csv",
    "4h":  DATA_DIR / "btcusdt_4h.csv",
    "1d":  DATA_DIR / "btcusdt_1d.csv",
}

BAR_MS = {
    "15m": 15 * 60 * 1000,
    "1h":  60 * 60 * 1000,
    "4h":  4 * 60 * 60 * 1000,
    "1d":  24 * 60 * 60 * 1000,
}

# Expected bars per gap threshold (>3 bars = gap)
GAP_THRESHOLD = 3

# ── Load all files ─────────────────────────────────────────────────────
dfs = {}
for label, path in FILES.items():
    df = pd.read_csv(path)
    df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    dfs[label] = df
    print(f"Loaded {label}: {len(df):,} rows, {df.columns.tolist()}")

# ── Helper: ms to date string ──────────────────────────────────────────
def ms_to_str(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

# ══════════════════════════════════════════════════════════════════════
# 1. SCHEMA & COVERAGE
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. SCHEMA & COVERAGE")
print("=" * 70)

schema_rows = []
for label, df in dfs.items():
    start = ms_to_str(df["open_time"].iloc[0])
    end = ms_to_str(df["open_time"].iloc[-1])
    days = (df["open_time"].iloc[-1] - df["open_time"].iloc[0]) / (86400 * 1000)
    schema_rows.append({
        "file": label,
        "rows": len(df),
        "columns": len(df.columns) - 1,  # exclude dt
        "start": start,
        "end": end,
        "duration_days": round(days, 1),
    })
    print(f"\n{label}:")
    print(f"  Rows: {len(df):,}")
    print(f"  Date range: {start} → {end} ({days:.0f} days)")
    print(f"  Dtypes: {dict(df.drop(columns='dt').dtypes)}")

schema_df = pd.DataFrame(schema_rows)
print(f"\n{schema_df.to_string(index=False)}")

# ── Duplicate timestamps ──────────────────────────────────────────────
print("\n--- Duplicate timestamps ---")
for label, df in dfs.items():
    dupes = df["open_time"].duplicated().sum()
    print(f"  {label}: {dupes} duplicates")

# ── Gaps > 3 bars ─────────────────────────────────────────────────────
print("\n--- Gaps > 3 consecutive bars ---")
gap_records = []
for label, df in dfs.items():
    bar_ms = BAR_MS[label]
    diffs = df["open_time"].diff().dropna()
    gaps = diffs[diffs > GAP_THRESHOLD * bar_ms]
    print(f"\n  {label}: {len(gaps)} gaps > {GAP_THRESHOLD} bars")
    for idx in gaps.index:
        gap_start = ms_to_str(df["open_time"].iloc[idx - 1])
        gap_end = ms_to_str(df["open_time"].iloc[idx])
        gap_bars = diffs.iloc[idx - 1 if idx > 0 else 0] / bar_ms  # use .loc for safety
        gap_bars_val = gaps.loc[idx] / bar_ms
        gap_hours = gaps.loc[idx] / (3600 * 1000)
        print(f"    {gap_start} → {gap_end} ({gap_bars_val:.0f} bars, {gap_hours:.1f}h)")
        gap_records.append({
            "file": label, "from": gap_start, "to": gap_end,
            "bars_missing": round(gap_bars_val), "hours": round(gap_hours, 1),
        })

# ══════════════════════════════════════════════════════════════════════
# 2. DATA QUALITY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("2. DATA QUALITY")
print("=" * 70)

quality_rows = []
for label, df in dfs.items():
    n = len(df)
    price_cols = ["open", "high", "low", "close"]
    vol_cols = ["volume", "quote_volume", "num_trades", "taker_buy_base_vol", "taker_buy_quote_vol"]
    all_cols = price_cols + vol_cols

    # Missing values
    missing = df[all_cols].isnull().sum()
    missing_total = missing.sum()

    # Zero volume
    zero_vol = (df["volume"] == 0).sum()

    # Price integrity
    close_gt_high = (df["close"] > df["high"]).sum()
    close_lt_low = (df["close"] < df["low"]).sum()
    open_le_zero = (df["open"] <= 0).sum()
    high_lt_low = (df["high"] < df["low"]).sum()

    # Extreme moves: |log_return| > 15%
    log_ret = np.log(df["close"] / df["close"].shift(1))
    extreme = log_ret.abs() > 0.15
    extreme_count = extreme.sum()
    extreme_dates = df.loc[extreme, "dt"].tolist()

    # taker_buy_base_vol
    tbv = df["taker_buy_base_vol"]
    tbv_missing = tbv.isnull().sum()
    tbv_zero = (tbv == 0).sum()
    tbv_ratio = (tbv / df["volume"].replace(0, np.nan)).dropna()
    tbv_ratio_mean = tbv_ratio.mean()

    row = {
        "file": label,
        "rows": n,
        "missing_total": missing_total,
        "zero_vol_bars": zero_vol,
        "close>high": close_gt_high,
        "close<low": close_lt_low,
        "open<=0": open_le_zero,
        "high<low": high_lt_low,
        "extreme_15pct": extreme_count,
        "tbv_missing": tbv_missing,
        "tbv_zero": tbv_zero,
        "tbv_ratio_mean": round(tbv_ratio_mean, 4),
    }
    quality_rows.append(row)

    print(f"\n{label}:")
    print(f"  Missing values total: {missing_total}")
    if missing_total > 0:
        for col in all_cols:
            if missing[col] > 0:
                print(f"    {col}: {missing[col]} ({missing[col]/n*100:.2f}%)")
    print(f"  Zero volume bars: {zero_vol}")
    print(f"  Price integrity: close>high={close_gt_high}, close<low={close_lt_low}, "
          f"open<=0={open_le_zero}, high<low={high_lt_low}")
    print(f"  Extreme moves (|log_ret|>15%): {extreme_count}")
    if extreme_count > 0:
        for d in extreme_dates[:10]:
            lr = log_ret.loc[df["dt"] == d]
            lr_val = lr.values[0] if len(lr) > 0 else float("nan")
            print(f"    {d}: log_ret={lr_val:.4f}")
    print(f"  taker_buy_base_vol: missing={tbv_missing}, zero={tbv_zero}, "
          f"mean_ratio={tbv_ratio_mean:.4f}")

quality_df = pd.DataFrame(quality_rows)
quality_df.to_csv(TBL_DIR / "Tbl03_data_quality.csv", index=False)
print(f"\nSaved: Tbl03_data_quality.csv")

# ── Zero volume by year ───────────────────────────────────────────────
print("\n--- Zero volume bars by year ---")
for label in ["4h", "1d"]:
    df = dfs[label]
    df_zv = df[df["volume"] == 0].copy()
    if len(df_zv) > 0:
        df_zv["year"] = df_zv["dt"].dt.year
        print(f"  {label}: {df_zv['year'].value_counts().sort_index().to_dict()}")
    else:
        print(f"  {label}: none")

# ── Extreme moves detail ─────────────────────────────────────────────
print("\n--- Extreme H4 moves (|log_ret| > 15%) detail ---")
df4 = dfs["4h"]
log_ret_4h = np.log(df4["close"] / df4["close"].shift(1))
extreme_mask = log_ret_4h.abs() > 0.15
if extreme_mask.sum() > 0:
    for idx in df4[extreme_mask].index:
        row = df4.iloc[idx]
        lr = log_ret_4h.iloc[idx]
        prev = df4.iloc[idx - 1] if idx > 0 else None
        prev_c = f"{prev['close']:.2f}" if prev is not None else "N/A"
        print(f"  {row['dt']}: close={row['close']:.2f}, prev_close={prev_c}, "
              f"log_ret={lr:.4f} ({lr*100:.1f}%), vol={row['volume']:.0f}")
else:
    print("  None found.")

# ══════════════════════════════════════════════════════════════════════
# 3. DESCRIPTIVE STATISTICS
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("3. DESCRIPTIVE STATISTICS")
print("=" * 70)

for label, tbl_name in [("4h", "Tbl01_h4_descriptive"), ("1d", "Tbl02_d1_descriptive")]:
    df = dfs[label]
    cols = ["open", "high", "low", "close", "volume", "quote_volume",
            "num_trades", "taker_buy_base_vol", "taker_buy_quote_vol"]
    desc = df[cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    desc = desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    desc.to_csv(TBL_DIR / f"{tbl_name}.csv")
    print(f"\n{label} descriptive stats:")
    print(desc.to_string())
    print(f"Saved: {tbl_name}.csv")

# Price range
for label in ["4h", "1d"]:
    df = dfs[label]
    lo = df["close"].min()
    hi = df["close"].max()
    print(f"\n{label} price range: lowest_close={lo:.2f}, highest_close={hi:.2f}, ratio={hi/lo:.1f}x")

# Bars per day (H4)
df4 = dfs["4h"]
bars_per_day = df4.groupby(df4["dt"].dt.date).size()
print(f"\nH4 bars per day: mean={bars_per_day.mean():.2f}, std={bars_per_day.std():.2f}, "
      f"min={bars_per_day.min()}, max={bars_per_day.max()}")

# ══════════════════════════════════════════════════════════════════════
# 4. TIME COVERAGE
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("4. TIME COVERAGE")
print("=" * 70)

for label in ["4h", "1d"]:
    df = dfs[label]
    yearly = df.groupby(df["dt"].dt.year).size()
    print(f"\n{label} year-by-year bar count:")
    for yr, cnt in yearly.items():
        print(f"  {yr}: {cnt}")

# Gaps > 12h for H4
print("\n--- H4 gaps > 12h ---")
df4 = dfs["4h"]
diffs_4h = df4["open_time"].diff().dropna()
gaps_12h = diffs_4h[diffs_4h > 12 * 3600 * 1000]
if len(gaps_12h) > 0:
    for idx in gaps_12h.index:
        gap_start = ms_to_str(df4["open_time"].iloc[idx - 1])
        gap_end = ms_to_str(df4["open_time"].iloc[idx])
        gap_hours = gaps_12h.loc[idx] / (3600 * 1000)
        print(f"  {gap_start} → {gap_end} ({gap_hours:.1f}h)")
else:
    print("  None found.")

# Gaps > 48h for D1
print("\n--- D1 gaps > 48h ---")
df1d = dfs["1d"]
diffs_1d = df1d["open_time"].diff().dropna()
gaps_48h = diffs_1d[diffs_1d > 48 * 3600 * 1000]
if len(gaps_48h) > 0:
    for idx in gaps_48h.index:
        gap_start = ms_to_str(df1d["open_time"].iloc[idx - 1])
        gap_end = ms_to_str(df1d["open_time"].iloc[idx])
        gap_hours = gaps_48h.loc[idx] / (3600 * 1000)
        print(f"  {gap_start} → {gap_end} ({gap_hours:.1f}h)")
else:
    print("  None found.")

# Sparse periods check: bars per month for H4
print("\n--- H4 bars per month (check for sparse periods) ---")
monthly = df4.groupby(df4["dt"].dt.to_period("M")).size()
expected_per_month = 6 * 30  # ~180 bars/month
sparse = monthly[monthly < expected_per_month * 0.8]
if len(sparse) > 0:
    print("  Months with <80% expected bars:")
    for m, cnt in sparse.items():
        print(f"    {m}: {cnt} bars (expected ~{expected_per_month})")
else:
    print("  No sparse months found.")

# Print full monthly counts for first and last few months
print("\n  First 3 months:")
for m, cnt in monthly.head(3).items():
    print(f"    {m}: {cnt}")
print("  Last 3 months:")
for m, cnt in monthly.tail(3).items():
    print(f"    {m}: {cnt}")

# ══════════════════════════════════════════════════════════════════════
# MANIFEST
# ══════════════════════════════════════════════════════════════════════
manifest = {
    "study": "X27",
    "phase": 1,
    "phase_name": "Data Audit",
    "date": "2026-03-11",
    "artifacts": {
        "report": "01_data_audit.md",
        "tables": [
            "tables/Tbl01_h4_descriptive.csv",
            "tables/Tbl02_d1_descriptive.csv",
            "tables/Tbl03_data_quality.csv",
        ],
        "code": [
            "code/phase1_audit.py",
        ],
        "figures": [],
    },
    "gate_status": None,  # set after review
}
with open(OUT_DIR / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
print(f"\nSaved: manifest.json")

print("\n" + "=" * 70)
print("PHASE 1 AUDIT COMPLETE")
print("=" * 70)
