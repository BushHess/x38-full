#!/usr/bin/env python3
"""
04 — OOS Paired Series Diagnostics
====================================
Reproduce the ACTUAL candidate (v12_emdd_ref_fix) and baseline (v8_apex)
equity curves from the canonical validation pipeline, then compute
comprehensive distributional diagnostics on each series and the paired
differential.

Canonical config (from out/validate/v12_vs_v10/2026-02-24/run_meta.json):
  - start:        2019-01-01
  - end:          2026-02-20
  - warmup:       365 days
  - initial_cash: 10,000
  - cost:         harsh (50 bps RT)
  - seed:         1337

Deliverables:
  research_reports/artifacts/04_actual_paired_oos_diagnostics.json
  research_reports/artifacts/04_paired_equity_curves.csv
  research_reports/04_actual_paired_oos_diagnostics.md  (written separately)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ── Project paths ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, EquitySnap
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from strategies.v12_emdd_ref_fix.strategy import (
    V12EMDDRefFixConfig,
    V12EMDDRefFixStrategy,
)
from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy

# ── Canonical config (from run_meta.json) ─────────────────────────────
DATA_PATH = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
COST = SCENARIOS["harsh"]

OUT_DIR = ROOT / "research_reports" / "artifacts"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: Reproduce equity curves
# ═══════════════════════════════════════════════════════════════════════

def run_backtest(strategy, label: str) -> list[EquitySnap]:
    """Run backtest and return equity curve."""
    feed = DataFeed(
        path=str(DATA_PATH),
        start=START,
        end=END,
        warmup_days=WARMUP_DAYS,
    )
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=COST,
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP_DAYS,
    )
    result = engine.run()
    s = result.summary
    print(f"  {label:20s}: Sharpe={s.get('sharpe', 0):.4f}  "
          f"CAGR={s.get('cagr_pct', 0):.2f}%  "
          f"MDD={s.get('max_drawdown_mid_pct', 0):.2f}%  "
          f"trades={s.get('trades', 0)}")
    return result.equity


def make_candidate():
    """v12_emdd_ref_fix with canonical params."""
    cfg = V12EMDDRefFixConfig()
    cfg.emdd_ref_mode = "fixed"
    cfg.emergency_dd_pct = 0.04
    cfg.rsi_method = "wilder"
    cfg.entry_cooldown_bars = 3
    return V12EMDDRefFixStrategy(cfg)


def make_baseline():
    """v8_apex baseline (frozen production config)."""
    cfg = V8ApexConfig()
    cfg.emergency_ref = "pre_cost_legacy"
    cfg.rsi_method = "wilder"
    cfg.entry_cooldown_bars = 3
    return V8ApexStrategy(cfg)


def make_vtrend():
    """VTREND — the proven 3-param algorithm."""
    cfg = VTrendConfig(slow_period=120.0, trail_mult=3.0, vdo_threshold=0.0)
    return VTrendStrategy(cfg)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: Statistical diagnostics
# ═══════════════════════════════════════════════════════════════════════

def pct_returns(navs: np.ndarray) -> np.ndarray:
    """H4-bar percentage returns: (nav[t] - nav[t-1]) / nav[t-1]."""
    return np.diff(navs) / navs[:-1]


def log_returns(navs: np.ndarray) -> np.ndarray:
    """H4-bar log returns."""
    return np.log(navs[1:] / navs[:-1])


def acf(x: np.ndarray, max_lag: int = 20) -> list[float]:
    """Sample autocorrelation at lags 1..max_lag."""
    n = len(x)
    mu = np.mean(x)
    var = np.var(x, ddof=0)
    if var == 0:
        return [0.0] * max_lag
    result = []
    for lag in range(1, max_lag + 1):
        cov = np.mean((x[:n - lag] - mu) * (x[lag:] - mu))
        result.append(float(cov / var))
    return result


def hill_estimator(x: np.ndarray, k_frac: float = 0.10) -> float:
    """Hill tail index estimator using top k_frac fraction of |x|.

    Returns alpha (tail exponent). Lower alpha = heavier tails.
    alpha > 2: finite variance; alpha > 4: finite kurtosis.
    """
    absvals = np.abs(x)
    absvals = absvals[absvals > 0]  # remove zeros
    absvals_sorted = np.sort(absvals)[::-1]
    k = max(2, int(len(absvals_sorted) * k_frac))
    top_k = absvals_sorted[:k]
    threshold = absvals_sorted[k - 1] if k < len(absvals_sorted) else absvals_sorted[-1]
    if threshold <= 0:
        return float("inf")
    log_ratio = np.log(top_k / threshold)
    alpha = 1.0 / (np.mean(log_ratio) + 1e-12)
    return float(alpha)


def rolling_vol(returns: np.ndarray, window: int = 20) -> np.ndarray:
    """Rolling standard deviation of returns."""
    n = len(returns)
    if n < window:
        return np.array([])
    out = np.empty(n - window + 1)
    for i in range(len(out)):
        out[i] = np.std(returns[i:i + window], ddof=0)
    return out


def drawdown_series(navs: np.ndarray) -> np.ndarray:
    """Drawdown at each point: (peak - nav) / peak."""
    running_max = np.maximum.accumulate(navs)
    dd = (running_max - navs) / running_max
    return dd


def drawdown_durations(navs: np.ndarray) -> list[int]:
    """List of drawdown episode durations (in bars)."""
    running_max = np.maximum.accumulate(navs)
    in_dd = navs < running_max
    durations = []
    current = 0
    for val in in_dd:
        if val:
            current += 1
        else:
            if current > 0:
                durations.append(current)
            current = 0
    if current > 0:
        durations.append(current)
    return durations


def compute_diagnostics(returns: np.ndarray, navs: np.ndarray,
                        label: str) -> dict:
    """Full diagnostic suite for a single return series."""
    n = len(returns)
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=0))
    skew = float(0.0)
    kurt = float(0.0)
    if sigma > 0:
        z = (returns - mu) / sigma
        skew = float(np.mean(z ** 3))
        kurt = float(np.mean(z ** 4) - 3.0)  # excess kurtosis

    # Annualized (H4: 6 * 365.25 = 2191.5 bars/year)
    bars_per_year = 6.0 * 365.25
    ann_return = float((1 + mu) ** bars_per_year - 1)
    ann_vol = float(sigma * np.sqrt(bars_per_year))
    sharpe = float(ann_return / ann_vol) if ann_vol > 0 else 0.0

    # Hill tail index
    hill_alpha = hill_estimator(returns, k_frac=0.10)

    # ACF (returns, squared, absolute)
    acf_ret = acf(returns, 20)
    acf_sq = acf(returns ** 2, 20)
    acf_abs = acf(np.abs(returns), 20)

    # Rolling vol persistence
    rvol_20 = rolling_vol(returns, 20)
    rvol_60 = rolling_vol(returns, 60)
    rvol_20_acf1 = float(acf(rvol_20, 1)[0]) if len(rvol_20) > 20 else 0.0
    rvol_60_acf1 = float(acf(rvol_60, 1)[0]) if len(rvol_60) > 60 else 0.0

    # Drawdown analysis
    dd = drawdown_series(navs)
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0
    dd_durs = drawdown_durations(navs)
    dd_dur_stats = {}
    if dd_durs:
        dd_durs_arr = np.array(dd_durs, dtype=float)
        dd_dur_stats = {
            "count": len(dd_durs),
            "mean": float(np.mean(dd_durs_arr)),
            "median": float(np.median(dd_durs_arr)),
            "max": int(np.max(dd_durs_arr)),
            "p90": float(np.percentile(dd_durs_arr, 90)),
            "p95": float(np.percentile(dd_durs_arr, 95)),
        }

    return {
        "label": label,
        "n_bars": n,
        "n_nav": len(navs),
        "summary": {
            "mean_per_bar": mu,
            "std_per_bar": sigma,
            "skewness": skew,
            "excess_kurtosis": kurt,
            "ann_return": ann_return,
            "ann_vol": ann_vol,
            "sharpe": sharpe,
        },
        "tail": {
            "hill_alpha_10pct": hill_alpha,
            "min_return": float(np.min(returns)),
            "max_return": float(np.max(returns)),
            "pct_1": float(np.percentile(returns, 1)),
            "pct_5": float(np.percentile(returns, 5)),
            "pct_95": float(np.percentile(returns, 95)),
            "pct_99": float(np.percentile(returns, 99)),
        },
        "acf_returns": acf_ret,
        "acf_squared": acf_sq,
        "acf_absolute": acf_abs,
        "rolling_vol": {
            "rvol_20_acf1": rvol_20_acf1,
            "rvol_60_acf1": rvol_60_acf1,
            "rvol_20_mean": float(np.mean(rvol_20)) if len(rvol_20) > 0 else 0.0,
            "rvol_60_mean": float(np.mean(rvol_60)) if len(rvol_60) > 0 else 0.0,
        },
        "drawdown": {
            "max_dd": max_dd,
            "duration_stats": dd_dur_stats,
        },
    }


def alignment_check(eq_a: list[EquitySnap], eq_b: list[EquitySnap],
                     label_a: str, label_b: str) -> dict:
    """Check timestamp alignment between two equity curves."""
    ts_a = [e.close_time for e in eq_a]
    ts_b = [e.close_time for e in eq_b]
    n_a, n_b = len(ts_a), len(ts_b)
    common = set(ts_a) & set(ts_b)
    only_a = set(ts_a) - set(ts_b)
    only_b = set(ts_b) - set(ts_a)

    aligned = (ts_a == ts_b)

    return {
        "n_a": n_a,
        "n_b": n_b,
        "n_common": len(common),
        "n_only_a": len(only_a),
        "n_only_b": len(only_b),
        "perfectly_aligned": aligned,
        "label_a": label_a,
        "label_b": label_b,
        "first_ts_a": ts_a[0] if ts_a else None,
        "first_ts_b": ts_b[0] if ts_b else None,
        "last_ts_a": ts_a[-1] if ts_a else None,
        "last_ts_b": ts_b[-1] if ts_b else None,
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: Raw BTC returns for comparison
# ═══════════════════════════════════════════════════════════════════════

def get_raw_btc_returns(eq_timestamps: list[int]) -> np.ndarray:
    """Load raw BTC H4 close prices aligned to equity timestamps.

    Uses the same DataFeed to get H4 bars, then aligns by close_time.
    Returns pct returns of BTC close prices.
    """
    feed = DataFeed(
        path=str(DATA_PATH),
        start=START,
        end=END,
        warmup_days=WARMUP_DAYS,
    )
    # Build close_time -> close map from H4 bars
    price_map = {b.close_time: b.close for b in feed.h4_bars}

    # Align to equity timestamps (reporting window only)
    prices = []
    for ts in eq_timestamps:
        if ts in price_map:
            prices.append(price_map[ts])
        else:
            # Should not happen if data is consistent
            prices.append(float("nan"))

    prices = np.array(prices, dtype=np.float64)
    return np.diff(prices) / prices[:-1]


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("04 — OOS PAIRED SERIES DIAGNOSTICS")
    print("=" * 72)
    print(f"  Data:    {DATA_PATH.name}")
    print(f"  Range:   {START} → {END}")
    print(f"  Warmup:  {WARMUP_DAYS}d")
    print(f"  Cost:    harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Cash:    ${INITIAL_CASH:,.0f}")
    print()

    # ── 1. Reproduce equity curves ────────────────────────────────────
    print("Reproducing equity curves...")
    eq_candidate = run_backtest(make_candidate(), "v12_emdd_ref_fix")
    eq_baseline = run_backtest(make_baseline(), "v8_apex_baseline")
    eq_vtrend = run_backtest(make_vtrend(), "vtrend")
    print()

    # ── 2. Timestamp alignment ────────────────────────────────────────
    print("Checking timestamp alignment...")
    align_cb = alignment_check(eq_candidate, eq_baseline,
                               "v12_candidate", "v8_baseline")
    align_cv = alignment_check(eq_candidate, eq_vtrend,
                               "v12_candidate", "vtrend")
    print(f"  candidate vs baseline: n={align_cb['n_a']}/{align_cb['n_b']}, "
          f"aligned={align_cb['perfectly_aligned']}")
    print(f"  candidate vs vtrend:   n={align_cv['n_a']}/{align_cv['n_b']}, "
          f"aligned={align_cv['perfectly_aligned']}")
    print()

    # ── 3. Extract NAV arrays and compute returns ─────────────────────
    navs_cand = np.array([e.nav_mid for e in eq_candidate], dtype=np.float64)
    navs_base = np.array([e.nav_mid for e in eq_baseline], dtype=np.float64)
    navs_vt = np.array([e.nav_mid for e in eq_vtrend], dtype=np.float64)
    ts_cand = [e.close_time for e in eq_candidate]

    ret_cand = pct_returns(navs_cand)
    ret_base = pct_returns(navs_base)
    ret_vt = pct_returns(navs_vt)

    # Paired differential (candidate - baseline)
    # Use aligned series — trim to min length
    min_n = min(len(ret_cand), len(ret_base))
    ret_diff_cb = ret_cand[:min_n] - ret_base[:min_n]

    # Paired differential (vtrend - baseline)
    min_n_vb = min(len(ret_vt), len(ret_base))
    ret_diff_vb = ret_vt[:min_n_vb] - ret_base[:min_n_vb]

    # Raw BTC returns aligned to equity timestamps
    print("Computing raw BTC returns...")
    ret_btc = get_raw_btc_returns(ts_cand)
    print(f"  BTC H4 returns: n={len(ret_btc)}, "
          f"NaN count={np.isnan(ret_btc).sum()}")
    print()

    # ── 4. Compute diagnostics ────────────────────────────────────────
    print("Computing diagnostics...")
    diag_cand = compute_diagnostics(ret_cand, navs_cand, "v12_candidate")
    diag_base = compute_diagnostics(ret_base, navs_base, "v8_baseline")
    diag_vt = compute_diagnostics(ret_vt, navs_vt, "vtrend")
    diag_diff_cb = compute_diagnostics(
        ret_diff_cb,
        # For differential: use cumulative product as "NAV"
        INITIAL_CASH * np.cumprod(1 + ret_diff_cb),
        "diff_candidate_minus_baseline",
    )
    diag_diff_vb = compute_diagnostics(
        ret_diff_vb,
        INITIAL_CASH * np.cumprod(1 + ret_diff_vb),
        "diff_vtrend_minus_baseline",
    )

    # BTC diagnostics (filter NaNs)
    ret_btc_clean = ret_btc[~np.isnan(ret_btc)]
    btc_nav = INITIAL_CASH * np.cumprod(1 + ret_btc_clean)
    btc_nav = np.concatenate([[INITIAL_CASH], btc_nav])
    diag_btc = compute_diagnostics(ret_btc_clean, btc_nav, "raw_btc")

    # ── 5. Cross-correlation: strategy returns vs BTC ─────────────────
    min_n_btc = min(len(ret_cand), len(ret_btc_clean))
    corr_cand_btc = float(np.corrcoef(
        ret_cand[:min_n_btc], ret_btc_clean[:min_n_btc])[0, 1])
    corr_base_btc = float(np.corrcoef(
        ret_base[:min_n_btc], ret_btc_clean[:min_n_btc])[0, 1])
    corr_vt_btc = float(np.corrcoef(
        ret_vt[:min_n_btc], ret_btc_clean[:min_n_btc])[0, 1])
    corr_cand_base = float(np.corrcoef(
        ret_cand[:min_n], ret_base[:min_n])[0, 1])
    corr_vt_base = float(np.corrcoef(
        ret_vt[:min_n_vb], ret_base[:min_n_vb])[0, 1])

    cross_corr = {
        "candidate_vs_btc": corr_cand_btc,
        "baseline_vs_btc": corr_base_btc,
        "vtrend_vs_btc": corr_vt_btc,
        "candidate_vs_baseline": corr_cand_base,
        "vtrend_vs_baseline": corr_vt_base,
    }

    # ── 6. Print summary table ────────────────────────────────────────
    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    header = f"{'Series':30s} {'Mean/bar':>10s} {'Std/bar':>10s} {'Skew':>8s} {'Kurt':>8s} {'Hill α':>8s} {'Sharpe':>8s}"
    print(header)
    print("-" * len(header))
    for d in [diag_cand, diag_base, diag_vt, diag_diff_cb, diag_diff_vb, diag_btc]:
        s = d["summary"]
        t = d["tail"]
        print(f"{d['label']:30s} {s['mean_per_bar']:10.6f} {s['std_per_bar']:10.6f} "
              f"{s['skewness']:8.3f} {s['excess_kurtosis']:8.3f} "
              f"{t['hill_alpha_10pct']:8.2f} {s['sharpe']:8.4f}")

    print()
    print("Cross-correlations:")
    for k, v in cross_corr.items():
        print(f"  {k:30s}: {v:.4f}")

    print()
    print("ACF(1) summary:")
    for d in [diag_cand, diag_base, diag_vt, diag_btc]:
        print(f"  {d['label']:30s}: ret={d['acf_returns'][0]:.4f}  "
              f"sq={d['acf_squared'][0]:.4f}  "
              f"abs={d['acf_absolute'][0]:.4f}")

    print()
    print("Rolling vol persistence (ACF1 of σ_rolling):")
    for d in [diag_cand, diag_base, diag_vt, diag_btc]:
        rv = d["rolling_vol"]
        print(f"  {d['label']:30s}: 20bar={rv['rvol_20_acf1']:.4f}  "
              f"60bar={rv['rvol_60_acf1']:.4f}")

    print()
    print("Drawdown duration stats:")
    for d in [diag_cand, diag_base, diag_vt, diag_btc]:
        dd = d["drawdown"]["duration_stats"]
        if dd:
            print(f"  {d['label']:30s}: count={dd['count']}  "
                  f"mean={dd['mean']:.0f}  median={dd['median']:.0f}  "
                  f"max={dd['max']}  p95={dd['p95']:.0f}")

    # ── 7. Save artifacts ─────────────────────────────────────────────
    # JSON artifact
    full_result = {
        "meta": {
            "script": "04_oos_paired_diagnostics.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "data_file": DATA_PATH.name,
            "start": START,
            "end": END,
            "warmup_days": WARMUP_DAYS,
            "initial_cash": INITIAL_CASH,
            "cost_scenario": "harsh",
            "cost_rt_bps": COST.round_trip_bps,
        },
        "alignment": {
            "candidate_vs_baseline": align_cb,
            "candidate_vs_vtrend": align_cv,
        },
        "diagnostics": {
            "v12_candidate": diag_cand,
            "v8_baseline": diag_base,
            "vtrend": diag_vt,
            "diff_candidate_minus_baseline": diag_diff_cb,
            "diff_vtrend_minus_baseline": diag_diff_vb,
            "raw_btc": diag_btc,
        },
        "cross_correlations": cross_corr,
    }

    json_path = OUT_DIR / "04_actual_paired_oos_diagnostics.json"
    with open(json_path, "w") as f:
        json.dump(full_result, f, indent=2, default=str)
    print(f"\nJSON artifact: {json_path}")

    # CSV: paired equity curves
    csv_path = OUT_DIR / "04_paired_equity_curves.csv"
    with open(csv_path, "w") as f:
        f.write("close_time,nav_candidate,nav_baseline,nav_vtrend,"
                "exposure_candidate,exposure_baseline,exposure_vtrend\n")
        max_len = max(len(eq_candidate), len(eq_baseline), len(eq_vtrend))
        for i in range(max_len):
            ec = eq_candidate[i] if i < len(eq_candidate) else None
            eb = eq_baseline[i] if i < len(eq_baseline) else None
            ev = eq_vtrend[i] if i < len(eq_vtrend) else None
            ts = (ec or eb or ev).close_time
            nc = ec.nav_mid if ec else ""
            nb = eb.nav_mid if eb else ""
            nv = ev.nav_mid if ev else ""
            xc = ec.exposure if ec else ""
            xb = eb.exposure if eb else ""
            xv = ev.exposure if ev else ""
            f.write(f"{ts},{nc},{nb},{nv},{xc},{xb},{xv}\n")
    print(f"CSV artifact:  {csv_path}")

    # Verify against existing validation output
    print()
    print("=" * 72)
    print("CROSS-CHECK vs existing validation output")
    print("=" * 72)
    existing_csv = (ROOT / "out" / "validate" / "v12_vs_v10" / "2026-02-24"
                    / "results" / "full_backtest_summary.csv")
    if existing_csv.exists():
        import csv
        with open(existing_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["label"] == "candidate" and row["scenario"] == "harsh":
                    print(f"  Existing candidate harsh: Sharpe={row['sharpe']}, "
                          f"CAGR={row['cagr_pct']}%, MDD={row['max_drawdown_mid_pct']}%")
                if row["label"] == "baseline" and row["scenario"] == "harsh":
                    print(f"  Existing baseline  harsh: Sharpe={row['sharpe']}, "
                          f"CAGR={row['cagr_pct']}%, MDD={row['max_drawdown_mid_pct']}%")
        print(f"  Reproduced candidate:    Sharpe={diag_cand['summary']['sharpe']:.4f}, "
              f"CAGR={diag_cand['summary']['ann_return']*100:.2f}%")
        print(f"  Reproduced baseline:     Sharpe={diag_base['summary']['sharpe']:.4f}, "
              f"CAGR={diag_base['summary']['ann_return']*100:.2f}%")
    else:
        print("  (existing validation CSV not found)")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
