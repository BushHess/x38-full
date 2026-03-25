"""
Phase 1 — Data Audit
X28 research: BTC spot H1+H4+D1

Produces:
  - tables/Tbl01_h4_descriptive.csv
  - tables/Tbl02_d1_descriptive.csv
  - tables/Tbl03_data_quality.csv
  - stdout report (piped to 01_data_audit.md)
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path("/var/www/trading-bots/btc-spot-dev/data")
OUT_DIR = Path("/var/www/trading-bots/btc-spot-dev/research/x28")
TBL_DIR = OUT_DIR / "tables"
TBL_DIR.mkdir(exist_ok=True)

EXPECTED_COLS = [
    "symbol", "interval", "open_time", "close_time",
    "open", "high", "low", "close",
    "volume", "quote_volume", "num_trades",
    "taker_buy_base_vol", "taker_buy_quote_vol",
]

FILES = {
    "15m": DATA_DIR / "btcusdt_15m.csv",
    "1h":  DATA_DIR / "btcusdt_1h.csv",
    "4h":  DATA_DIR / "btcusdt_4h.csv",
    "1d":  DATA_DIR / "btcusdt_1d.csv",
}

INTERVAL_MS = {
    "15m": 15 * 60 * 1000,
    "1h":  60 * 60 * 1000,
    "4h":  4 * 60 * 60 * 1000,
    "1d":  24 * 60 * 60 * 1000,
}

# Gap thresholds for flagging
GAP_THRESHOLD = {
    "15m": 2 * 15 * 60 * 1000,   # > 30 min
    "1h":  2 * 60 * 60 * 1000,   # > 2h
    "4h":  3 * 4 * 60 * 60 * 1000,  # > 12h (per spec)
    "1d":  2 * 24 * 60 * 60 * 1000,  # > 2d (per spec)
}

NUMERIC_COLS = ["open", "high", "low", "close", "volume",
                "quote_volume", "num_trades",
                "taker_buy_base_vol", "taker_buy_quote_vol"]

def df_to_md(df: pd.DataFrame) -> str:
    """Convert DataFrame to markdown table without tabulate."""
    cols = df.columns.tolist()
    idx_name = df.index.name or ""
    header = f"| {idx_name} | " + " | ".join(str(c) for c in cols) + " |"
    sep = "|" + "|".join(["---"] * (len(cols) + 1)) + "|"
    rows = []
    for idx, row in df.iterrows():
        vals = " | ".join(str(round(v, 4)) if isinstance(v, float) else str(v) for v in row)
        rows.append(f"| {idx} | {vals} |")
    return "\n".join([header, sep] + rows)

def load(tf: str) -> pd.DataFrame:
    df = pd.read_csv(FILES[tf])
    return df

def check_schema(df: pd.DataFrame, tf: str) -> dict:
    missing_cols = [c for c in EXPECTED_COLS if c not in df.columns]
    extra_cols = [c for c in df.columns if c not in EXPECTED_COLS]
    dtype_ok = {}
    for c in NUMERIC_COLS:
        if c in df.columns:
            dtype_ok[c] = pd.api.types.is_numeric_dtype(df[c])
    dt_start = pd.to_datetime(df["open_time"].iloc[0], unit="ms")
    dt_end = pd.to_datetime(df["open_time"].iloc[-1], unit="ms")
    return {
        "tf": tf,
        "rows": len(df),
        "cols_match": len(missing_cols) == 0 and len(extra_cols) == 0,
        "missing_cols": missing_cols,
        "extra_cols": extra_cols,
        "numeric_ok": all(dtype_ok.values()),
        "dtype_detail": dtype_ok,
        "date_start": str(dt_start),
        "date_end": str(dt_end),
    }

def check_quality(df: pd.DataFrame, tf: str) -> dict:
    # Missing values
    missing = df.isnull().sum()
    total_missing = int(missing.sum())

    # Duplicate timestamps
    dup_ts = int(df["open_time"].duplicated().sum())

    # Gaps
    diffs = df["open_time"].diff().dropna()
    expected = INTERVAL_MS[tf]
    threshold = GAP_THRESHOLD[tf]
    gap_mask = diffs > threshold
    n_gaps = int(gap_mask.sum())
    gap_details = []
    if n_gaps > 0:
        gap_idx = diffs[gap_mask].index
        for idx in gap_idx:
            t_before = pd.to_datetime(df.loc[idx - 1, "open_time"], unit="ms")
            t_after = pd.to_datetime(df.loc[idx, "open_time"], unit="ms")
            gap_h = diffs.loc[idx] / (3600 * 1000)
            gap_details.append({
                "from": str(t_before),
                "to": str(t_after),
                "gap_hours": round(float(gap_h), 2),
            })

    # Zero-volume bars
    zero_vol = int((df["volume"] == 0).sum())

    # Price integrity
    close_gt_high = int((df["close"] > df["high"]).sum())
    close_lt_low = int((df["close"] < df["low"]).sum())
    open_gt_high = int((df["open"] > df["high"]).sum())
    open_lt_low = int((df["open"] < df["low"]).sum())
    price_integrity_fails = close_gt_high + close_lt_low + open_gt_high + open_lt_low

    # Extreme moves
    log_ret = np.log(df["close"] / df["close"].shift(1)).dropna()
    extreme_mask = log_ret.abs() > 0.20
    n_extreme = int(extreme_mask.sum())
    extreme_details = []
    if n_extreme > 0:
        for idx in log_ret[extreme_mask].index:
            t = pd.to_datetime(df.loc[idx, "open_time"], unit="ms")
            extreme_details.append({
                "time": str(t),
                "log_return": round(float(log_ret.loc[idx]), 4),
                "close_before": float(df.loc[idx - 1, "close"]),
                "close_after": float(df.loc[idx, "close"]),
            })

    return {
        "tf": tf,
        "total_missing": total_missing,
        "missing_per_col": {k: int(v) for k, v in missing.items() if v > 0},
        "duplicate_timestamps": dup_ts,
        "gaps_above_threshold": n_gaps,
        "gap_details": gap_details,
        "zero_volume_bars": zero_vol,
        "price_integrity_fails": price_integrity_fails,
        "price_detail": {
            "close>high": close_gt_high,
            "close<low": close_lt_low,
            "open>high": open_gt_high,
            "open<low": open_lt_low,
        },
        "extreme_moves_gt_20pct": n_extreme,
        "extreme_details": extreme_details,
    }

def descriptive_stats(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    cols = ["open", "high", "low", "close", "volume"]
    desc = df[cols].describe().T
    desc.index.name = "field"
    desc = desc.round(4)

    # Taker buy ratio
    ratio = df["taker_buy_base_vol"] / df["volume"].replace(0, np.nan)
    ratio_stats = {
        "field": "taker_buy_ratio",
        "count": float(ratio.count()),
        "mean": round(float(ratio.mean()), 4),
        "std": round(float(ratio.std()), 4),
        "min": round(float(ratio.min()), 4),
        "25%": round(float(ratio.quantile(0.25)), 4),
        "50%": round(float(ratio.quantile(0.50)), 4),
        "75%": round(float(ratio.quantile(0.75)), 4),
        "max": round(float(ratio.max()), 4),
    }
    ratio_row = pd.DataFrame([ratio_stats]).set_index("field")
    return pd.concat([desc, ratio_row])

def time_coverage(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Year-by-year bar count."""
    ts = pd.to_datetime(df["open_time"], unit="ms")
    yearly = ts.dt.year.value_counts().sort_index()
    return yearly.rename("bar_count").to_frame()

# ======================================================================
# MAIN
# ======================================================================
def main():
    frames = {}
    schema_results = []
    quality_results = []

    for tf in ["15m", "1h", "4h", "1d"]:
        df = load(tf)
        frames[tf] = df
        schema_results.append(check_schema(df, tf))
        quality_results.append(check_quality(df, tf))

    # ── 1. SCHEMA CHECK ──
    print("# Phase 1 — Data Audit Report")
    print()
    print("## 1. Schema Check")
    print()
    print("| TF | Rows | Cols Match | Numeric OK | Date Range |")
    print("|----|------|------------|------------|------------|")
    for s in schema_results:
        print(f"| {s['tf']} | {s['rows']:,} | {s['cols_match']} | {s['numeric_ok']} | {s['date_start'][:10]} → {s['date_end'][:10]} |")
    print()
    for s in schema_results:
        if s["missing_cols"]:
            print(f"**{s['tf']}** missing columns: {s['missing_cols']}")
        if s["extra_cols"]:
            print(f"**{s['tf']}** extra columns: {s['extra_cols']}")
    print()

    # ── 2. DATA QUALITY ──
    print("## 2. Data Quality")
    print()
    print("| TF | Missing Values | Dup Timestamps | Gaps | Zero-Vol | Price Fails | Extreme (>20%) |")
    print("|----|---------------|----------------|------|----------|-------------|----------------|")
    for q in quality_results:
        print(f"| {q['tf']} | {q['total_missing']} | {q['duplicate_timestamps']} | "
              f"{q['gaps_above_threshold']} | {q['zero_volume_bars']} | "
              f"{q['price_integrity_fails']} | {q['extreme_moves_gt_20pct']} |")
    print()

    # Gap details
    for q in quality_results:
        if q["gap_details"]:
            print(f"### Gaps — {q['tf']}")
            print()
            print("| From | To | Gap (hours) |")
            print("|------|----|-------------|")
            for g in q["gap_details"]:
                print(f"| {g['from']} | {g['to']} | {g['gap_hours']} |")
            print()

    # Extreme moves
    for q in quality_results:
        if q["extreme_details"]:
            print(f"### Extreme Moves — {q['tf']}")
            print()
            print("| Time | Log Return | Close Before | Close After |")
            print("|------|------------|--------------|-------------|")
            for e in q["extreme_details"]:
                print(f"| {e['time']} | {e['log_return']:+.4f} | {e['close_before']:.2f} | {e['close_after']:.2f} |")
            print()

    # Price integrity details (if any)
    for q in quality_results:
        if q["price_integrity_fails"] > 0:
            print(f"### Price Integrity — {q['tf']}")
            print(f"  close>high: {q['price_detail']['close>high']}, "
                  f"close<low: {q['price_detail']['close<low']}, "
                  f"open>high: {q['price_detail']['open>high']}, "
                  f"open<low: {q['price_detail']['open<low']}")
            print()

    # ── 3. DESCRIPTIVE STATISTICS ──
    print("## 3. Descriptive Statistics")
    print()

    for tf in ["15m", "1h", "4h", "1d"]:
        desc = descriptive_stats(frames[tf], tf)
        tbl_name = {"4h": "Tbl01_h4_descriptive", "1d": "Tbl02_d1_descriptive"}.get(tf)
        if tbl_name:
            desc.to_csv(TBL_DIR / f"{tbl_name}.csv")
            print(f"*Saved: tables/{tbl_name}.csv*")
            print()

        print(f"### {tf}")
        print()
        print(df_to_md(desc))
        print()

    # ── 4. TIME COVERAGE ──
    print("## 4. Time Coverage")
    print()

    for tf in ["15m", "1h", "4h", "1d"]:
        cov = time_coverage(frames[tf], tf)
        print(f"### {tf} — Year-by-year")
        print()
        print(df_to_md(cov))
        print()

    # ── Tbl03 — Data Quality summary ──
    quality_df = pd.DataFrame([
        {
            "timeframe": q["tf"],
            "rows": schema_results[i]["rows"],
            "missing_values": q["total_missing"],
            "dup_timestamps": q["duplicate_timestamps"],
            "gaps": q["gaps_above_threshold"],
            "zero_volume": q["zero_volume_bars"],
            "price_integrity_fails": q["price_integrity_fails"],
            "extreme_moves": q["extreme_moves_gt_20pct"],
        }
        for i, q in enumerate(quality_results)
    ])
    quality_df.to_csv(TBL_DIR / "Tbl03_data_quality.csv", index=False)
    print("*Saved: tables/Tbl03_data_quality.csv*")
    print()

    # ── END-OF-PHASE CHECKLIST ──
    print("## End-of-Phase Checklist")
    print()
    print("### Files Created")
    print("- `01_data_audit.md` (this report)")
    print("- `code/phase1_audit.py`")
    print("- `tables/Tbl01_h4_descriptive.csv`")
    print("- `tables/Tbl02_d1_descriptive.csv`")
    print("- `tables/Tbl03_data_quality.csv`")
    print("- `manifest.json`")
    print()
    print("### Key Observations")

    all_pass = True
    for q in quality_results:
        if q["total_missing"] > 0 or q["duplicate_timestamps"] > 0 or q["price_integrity_fails"] > 0:
            all_pass = False
    for q in quality_results:
        if q["gaps_above_threshold"] > 0:
            print(f"- {q['tf']}: {q['gaps_above_threshold']} gap(s) above threshold")

    if all_pass:
        print("- All timeframes: zero missing values, zero duplicate timestamps, zero price integrity failures")
    print()
    print("### Blockers / Uncertainties")
    has_blockers = False
    for q in quality_results:
        if q["price_integrity_fails"] > 0:
            print(f"- **BLOCKER**: {q['tf']} has {q['price_integrity_fails']} price integrity failures")
            has_blockers = True
        if q["total_missing"] > 0:
            print(f"- **BLOCKER**: {q['tf']} has {q['total_missing']} missing values")
            has_blockers = True
    if not has_blockers:
        print("- None")
    print()
    print("### Gate Status")
    if has_blockers:
        print("**STOP_INCONCLUSIVE** — data quality issues must be resolved")
    else:
        print("**PASS_TO_NEXT_PHASE**")

    # ── manifest.json ──
    manifest = {
        "study": "X28",
        "research_question": "Long-only BTC spot algorithm maximizing Sharpe (MDD ≤ 60%)",
        "phases_completed": [1],
        "phase_1": {
            "status": "PASS_TO_NEXT_PHASE" if not has_blockers else "STOP_INCONCLUSIVE",
            "deliverables": [
                "01_data_audit.md",
                "code/phase1_audit.py",
                "tables/Tbl01_h4_descriptive.csv",
                "tables/Tbl02_d1_descriptive.csv",
                "tables/Tbl03_data_quality.csv",
            ],
            "data_files": {
                tf: {
                    "rows": schema_results[i]["rows"],
                    "date_range": f"{schema_results[i]['date_start'][:10]} → {schema_results[i]['date_end'][:10]}",
                }
                for i, tf in enumerate(["15m", "1h", "4h", "1d"])
            },
        },
    }
    with open(OUT_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    main()
