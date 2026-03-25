#!/usr/bin/env python3
"""Step 5: Statistical Robustness + Temporal Stability Audit.

Circular block bootstrap for primary hypotheses H1-H4,
start-date sensitivity, rolling-window stability, calendar slices,
complexity-premium decision test.

NO modification of any production file.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup ─────────────────────────────────────────────────────────────
_SCRIPT = Path(__file__).resolve()
_SRC = _SCRIPT.parent
_NAMESPACE = _SRC.parent
_REPO = _NAMESPACE.parent.parent

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_align import load_h4_dataframe

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

EPS = 1e-12
BARS_PER_YEAR = 2190.0
ANN_FACTOR = math.sqrt(BARS_PER_YEAR)
SEED = 20260305
N_BOOT = 5000
BLOCK_LENGTHS = [42, 126, 252]

# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_equity_curves() -> dict[str, np.ndarray]:
    npz = np.load(str(ARTIFACTS / "factorial_equity_curves.npz"))
    return {k: npz[k] for k in npz.files}


def equity_to_returns(eq: np.ndarray) -> np.ndarray:
    r = np.zeros_like(eq)
    r[1:] = eq[1:] / np.maximum(eq[:-1], EPS) - 1.0
    return r


def load_bar_timestamps() -> np.ndarray:
    df = load_h4_dataframe()
    return df.index.to_numpy(dtype=np.int64)


# ═══════════════════════════════════════════════════════════════════════════
# METRIC HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def sharpe_from_returns(r: np.ndarray) -> float:
    core = r[1:] if len(r) > 1 else r
    if len(core) < 2:
        return 0.0
    s = float(np.std(core, ddof=0))
    if s < EPS:
        return 0.0
    return float(np.mean(core) / s * ANN_FACTOR)


def cagr_from_returns(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    terminal = eq[-1]
    years = max((len(r) - 1) / BARS_PER_YEAR, EPS)
    if terminal <= 0:
        return -1.0
    return float(terminal ** (1.0 / years) - 1.0)


def mdd_from_returns(r: np.ndarray) -> float:
    eq = np.cumprod(1.0 + r)
    rm = np.maximum.accumulate(eq)
    dd = 1.0 - eq / np.maximum(rm, EPS)
    return float(np.max(dd))


def calmar_from_returns(r: np.ndarray) -> float:
    c = cagr_from_returns(r)
    m = mdd_from_returns(r)
    return float(c / max(m, EPS)) if m > EPS else 0.0


def find_k_for_mdd(r_native: np.ndarray, target_mdd: float,
                   tol: float = 0.001) -> float:
    """Binary search for k that produces target MDD from native returns."""
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        rs = mid * r_native
        mdd = mdd_from_returns(rs)
        if mdd < target_mdd - tol:
            lo = mid
        elif mdd > target_mdd + tol:
            hi = mid
        else:
            return mid
    return (lo + hi) / 2.0


# ═══════════════════════════════════════════════════════════════════════════
# CIRCULAR BLOCK BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════

def circular_block_bootstrap_indices(n: int, block_len: int,
                                     rng: np.random.Generator) -> np.ndarray:
    """Generate one bootstrap sample of indices using circular block bootstrap."""
    n_blocks = int(np.ceil(n / block_len))
    starts = rng.integers(0, n, size=n_blocks)
    indices = np.empty(n_blocks * block_len, dtype=np.int64)
    for i, s in enumerate(starts):
        indices[i * block_len:(i + 1) * block_len] = np.arange(s, s + block_len) % n
    return indices[:n]


def bootstrap_paired_returns(r_a: np.ndarray, r_b: np.ndarray,
                             block_len: int, n_boot: int,
                             seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap paired return streams (same indices for both).

    Returns (boot_a, boot_b) each of shape (n_boot, n).
    Operates on core returns (r[1:]) to avoid the leading zero.
    """
    core_a = r_a[1:]
    core_b = r_b[1:]
    n = len(core_a)
    rng = np.random.default_rng(seed)
    boot_a = np.empty((n_boot, n + 1), dtype=np.float64)
    boot_b = np.empty((n_boot, n + 1), dtype=np.float64)
    boot_a[:, 0] = 0.0
    boot_b[:, 0] = 0.0
    for i in range(n_boot):
        idx = circular_block_bootstrap_indices(n, block_len, rng)
        boot_a[i, 1:] = core_a[idx]
        boot_b[i, 1:] = core_b[idx]
    return boot_a, boot_b


# ═══════════════════════════════════════════════════════════════════════════
# PRIMARY HYPOTHESIS TESTS
# ═══════════════════════════════════════════════════════════════════════════

def bootstrap_sharpe_diff(r_a: np.ndarray, r_b: np.ndarray,
                          block_len: int, n_boot: int,
                          seed: int) -> dict:
    """Bootstrap Sharpe(A) - Sharpe(B)."""
    ba, bb = bootstrap_paired_returns(r_a, r_b, block_len, n_boot, seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = sharpe_from_returns(ba[i]) - sharpe_from_returns(bb[i])
    return _summarize_diffs(diffs, "sharpe_diff")


def bootstrap_matched_mdd_cagr_diff(r_a: np.ndarray, r_b: np.ndarray,
                                     target_mdd: float,
                                     block_len: int, n_boot: int,
                                     seed: int) -> dict:
    """Bootstrap CAGR(B at target MDD) - CAGR(A at target MDD).

    For each bootstrap sample, recompute k for each strategy.
    """
    ba, bb = bootstrap_paired_returns(r_a, r_b, block_len, n_boot, seed)
    diffs = np.empty(n_boot)
    sat_a = 0
    sat_b = 0
    for i in range(n_boot):
        ra_boot = ba[i]
        rb_boot = bb[i]

        mdd_a = mdd_from_returns(ra_boot)
        mdd_b = mdd_from_returns(rb_boot)

        # Find k for each strategy in this bootstrap sample
        if mdd_a >= target_mdd:
            ka = find_k_for_mdd(ra_boot, target_mdd)
        else:
            ka = 1.0
            sat_a += 1

        if mdd_b >= target_mdd:
            kb = find_k_for_mdd(rb_boot, target_mdd)
        else:
            kb = 1.0
            sat_b += 1

        cagr_a = cagr_from_returns(ka * ra_boot)
        cagr_b = cagr_from_returns(kb * rb_boot)
        diffs[i] = cagr_b - cagr_a  # B minus A

    result = _summarize_diffs(diffs, "cagr_diff_matched_mdd")
    result["target_mdd"] = target_mdd
    result["saturation_a_pct"] = sat_a / n_boot * 100
    result["saturation_b_pct"] = sat_b / n_boot * 100
    return result


def _summarize_diffs(diffs: np.ndarray, label: str) -> dict:
    ci_lo = float(np.percentile(diffs, 2.5))
    ci_hi = float(np.percentile(diffs, 97.5))
    sign_prob = float(np.mean(diffs > 0))
    return {
        "metric": label,
        "mean": float(np.mean(diffs)),
        "median": float(np.median(diffs)),
        "ci_lo_95": ci_lo,
        "ci_hi_95": ci_hi,
        "sign_probability": sign_prob,
        "n_boot": len(diffs),
        "ci_excludes_zero": (ci_lo > 0) or (ci_hi < 0),
        "_diffs": diffs,
    }


def holm_adjust(raw_pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment."""
    n = len(raw_pvals)
    indexed = sorted(enumerate(raw_pvals), key=lambda x: x[1])
    adjusted = [0.0] * n
    cum_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adj = min(p * (n - rank), 1.0)
        cum_max = max(cum_max, adj)
        adjusted[orig_idx] = cum_max
    return adjusted


# ═══════════════════════════════════════════════════════════════════════════
# TEMPORAL ANALYSES
# ═══════════════════════════════════════════════════════════════════════════

def start_date_sensitivity(curves: dict[str, np.ndarray],
                           timestamps: np.ndarray) -> list[dict]:
    """Recompute key metrics for different start dates."""
    start_dates_ms = {
        "2017-08": int(pd.Timestamp("2017-08-01").timestamp() * 1000),
        "2019-01": int(pd.Timestamp("2019-01-01").timestamp() * 1000),
        "2020-01": int(pd.Timestamp("2020-01-01").timestamp() * 1000),
    }

    rows = []
    for label, start_ms in start_dates_ms.items():
        mask = timestamps >= start_ms
        if mask.sum() < 500:
            continue
        idx = np.where(mask)[0]
        start_idx = idx[0]

        row = {"start_date": label, "n_bars": int(mask.sum())}

        for name in ["E0_Native", "SM_Native", "LATCH_Native",
                     "E0_EntryVol_12", "LATCH_EntryVol_12"]:
            eq = curves[name]
            eq_sub = eq[start_idx:]
            eq_norm = eq_sub / eq_sub[0]
            r = np.zeros_like(eq_norm)
            r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0

            sh = sharpe_from_returns(r)
            c = cagr_from_returns(r)
            m = mdd_from_returns(r)

            short = name.replace("_Native", "").replace("_EntryVol_12", "_EV12")
            row[f"{short}_sharpe"] = sh
            row[f"{short}_cagr"] = c
            row[f"{short}_mdd"] = m

        # Matched 5% and 10% MDD winners
        for budget in [0.05, 0.10]:
            for sname in ["E0", "LATCH"]:
                key = f"{sname}_Native"
                eq = curves[key]
                eq_sub = eq[start_idx:]
                eq_norm = eq_sub / eq_sub[0]
                r = np.zeros_like(eq_norm)
                r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
                native_mdd = mdd_from_returns(r)
                if native_mdd >= budget:
                    k = find_k_for_mdd(r, budget)
                else:
                    k = 1.0
                cagr_at_budget = cagr_from_returns(k * r)
                short = sname
                row[f"{short}_cagr_at_{int(budget*100)}pct_mdd"] = cagr_at_budget

        # Winner at matched budgets
        for budget in [5, 10]:
            e0_c = row.get(f"E0_cagr_at_{budget}pct_mdd", 0)
            la_c = row.get(f"LATCH_cagr_at_{budget}pct_mdd", 0)
            row[f"winner_{budget}pct_mdd"] = "LATCH" if la_c > e0_c else "E0"

        # Equal-sizing Sharpe edge
        e0_ev = row.get("E0_EV12_sharpe", 0)
        la_ev = row.get("LATCH_EV12_sharpe", 0)
        row["equal_sizing_sharpe_edge"] = e0_ev - la_ev

        rows.append(row)

    return rows


def rolling_window_analysis(curves: dict[str, np.ndarray],
                            timestamps: np.ndarray,
                            btc_close: np.ndarray) -> list[dict]:
    """Rolling-window stability analysis."""
    bars_per_month = int(round(BARS_PER_YEAR / 12))
    step_bars = 6 * bars_per_month  # 6-month step
    n = len(timestamps)

    rows = []
    for window_months in [24, 36]:
        window_bars = window_months * bars_per_month
        if window_bars > n:
            continue

        start = 0
        while start + window_bars <= n:
            end = start + window_bars
            ts_start = timestamps[start]
            ts_end = timestamps[end - 1]
            date_start = str(pd.Timestamp(ts_start, unit="ms").date())
            date_end = str(pd.Timestamp(ts_end, unit="ms").date())

            row = {
                "window_months": window_months,
                "start_bar": start,
                "end_bar": end,
                "date_start": date_start,
                "date_end": date_end,
                "n_bars": end - start,
            }

            # BTC buy-and-hold
            btc_sub = btc_close[start:end]
            btc_ret = btc_sub[-1] / btc_sub[0] - 1
            row["btc_return"] = float(btc_ret)

            for name in ["E0_Native", "SM_Native", "LATCH_Native"]:
                eq = curves[name]
                eq_sub = eq[start:end]
                eq_norm = eq_sub / eq_sub[0]
                r = np.zeros_like(eq_norm)
                r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0

                short = name.replace("_Native", "")
                row[f"{short}_sharpe"] = sharpe_from_returns(r)
                row[f"{short}_cagr"] = cagr_from_returns(r)
                row[f"{short}_mdd"] = mdd_from_returns(r)

            # Matched 5% and 10% winners
            for budget in [0.05, 0.10]:
                for sname in ["E0", "LATCH"]:
                    key = f"{sname}_Native"
                    eq = curves[key]
                    eq_sub = eq[start:end]
                    eq_norm = eq_sub / eq_sub[0]
                    r = np.zeros_like(eq_norm)
                    r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
                    native_mdd = mdd_from_returns(r)
                    if native_mdd >= budget:
                        k = find_k_for_mdd(r, budget)
                    else:
                        k = 1.0
                    cagr_at = cagr_from_returns(k * r)
                    row[f"{sname}_cagr_at_{int(budget*100)}pct"] = cagr_at

                e0_c = row.get(f"E0_cagr_at_{int(budget*100)}pct", 0)
                la_c = row.get(f"LATCH_cagr_at_{int(budget*100)}pct", 0)
                row[f"winner_{int(budget*100)}pct"] = "LATCH" if la_c > e0_c else "E0"

            # SM vs LATCH Sharpe diff
            row["latch_minus_sm_sharpe"] = row["LATCH_sharpe"] - row["SM_sharpe"]

            # E0 equal-sizing edge (not available in rolling — use native Sharpe gap as proxy)
            row["e0_native_sharpe_edge"] = row["E0_sharpe"] - row["LATCH_sharpe"]

            # Crossover budget estimate
            e0_mdd = row.get("E0_mdd", 0)
            la_mdd = row.get("LATCH_mdd", 0)
            if e0_mdd > la_mdd and la_mdd > 0.01:
                # LATCH ceiling is la_mdd; E0 can go higher
                # Crossover: where CAGR(E0 at budget) ≈ CAGR(LATCH at k=1)
                eq_la = curves["LATCH_Native"][start:end]
                eq_la_n = eq_la / eq_la[0]
                r_la = np.zeros_like(eq_la_n)
                r_la[1:] = eq_la_n[1:] / np.maximum(eq_la_n[:-1], EPS) - 1.0
                latch_max_cagr = cagr_from_returns(r_la)

                eq_e0 = curves["E0_Native"][start:end]
                eq_e0_n = eq_e0 / eq_e0[0]
                r_e0 = np.zeros_like(eq_e0_n)
                r_e0[1:] = eq_e0_n[1:] / np.maximum(eq_e0_n[:-1], EPS) - 1.0

                # Search for crossover MDD budget
                crossover = None
                for test_mdd in np.arange(0.01, min(e0_mdd, 0.70), 0.005):
                    k_e0 = find_k_for_mdd(r_e0, test_mdd)
                    e0_cagr_at = cagr_from_returns(k_e0 * r_e0)
                    if e0_cagr_at >= latch_max_cagr:
                        crossover = test_mdd
                        break
                row["crossover_mdd"] = crossover if crossover else None
            else:
                row["crossover_mdd"] = None

            rows.append(row)
            start += step_bars

    return rows


def calendar_slice_analysis(curves: dict[str, np.ndarray],
                            timestamps: np.ndarray,
                            btc_close: np.ndarray) -> list[dict]:
    """Calendar-year slice diagnostics."""
    dates = pd.to_datetime(timestamps, unit="ms")
    years = sorted(set(dates.year))

    rows = []
    for yr in years:
        mask = dates.year == yr
        if mask.sum() < 100:
            continue
        idx = np.where(mask)[0]
        s, e = idx[0], idx[-1] + 1

        row = {"year": yr, "n_bars": e - s}

        # BTC
        btc_sub = btc_close[s:e]
        row["btc_return"] = float(btc_sub[-1] / btc_sub[0] - 1)

        for name in ["E0_Native", "SM_Native", "LATCH_Native"]:
            eq = curves[name]
            eq_sub = eq[s:e]
            eq_norm = eq_sub / eq_sub[0]
            r = np.zeros_like(eq_norm)
            r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0

            short = name.replace("_Native", "")
            row[f"{short}_sharpe"] = sharpe_from_returns(r)
            row[f"{short}_cagr"] = cagr_from_returns(r)
            row[f"{short}_mdd"] = mdd_from_returns(r)

        # Matched 10% MDD winner
        for sname in ["E0", "LATCH"]:
            key = f"{sname}_Native"
            eq = curves[key]
            eq_sub = eq[s:e]
            eq_norm = eq_sub / eq_sub[0]
            r = np.zeros_like(eq_norm)
            r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
            native_mdd = mdd_from_returns(r)
            if native_mdd >= 0.10:
                k = find_k_for_mdd(r, 0.10)
            else:
                k = 1.0
            row[f"{sname}_cagr_at_10pct"] = cagr_from_returns(k * r)

        e0_c = row.get("E0_cagr_at_10pct", 0)
        la_c = row.get("LATCH_cagr_at_10pct", 0)
        row["winner_10pct"] = "LATCH" if la_c > e0_c else "E0"

        # Equal-sizing edge (proxy: use native Sharpe difference — actual
        # equal-sizing comparison would require full signal re-extraction)
        for name in ["E0_EntryVol_12", "LATCH_EntryVol_12"]:
            eq = curves[name]
            eq_sub = eq[s:e]
            eq_norm = eq_sub / eq_sub[0]
            r = np.zeros_like(eq_norm)
            r[1:] = eq_norm[1:] / np.maximum(eq_norm[:-1], EPS) - 1.0
            short = name.replace("_EntryVol_12", "_EV12")
            row[f"{short}_sharpe"] = sharpe_from_returns(r)

        row["e0_equal_sizing_edge"] = (row.get("E0_EV12_sharpe", 0) -
                                       row.get("LATCH_EV12_sharpe", 0))

        rows.append(row)

    return rows


# ═══════════════════════════════════════════════════════════════════════════
# RESOLUTION MATRIX
# ═══════════════════════════════════════════════════════════════════════════

def classify_evidence(ci_excludes_zero: bool, sign_prob: float,
                      block_sensitivity: list[bool]) -> str:
    """Classify evidence as ROBUST / TENTATIVE / UNSUPPORTED."""
    # Block sensitivity: list of ci_excludes_zero for each block length
    all_exclude = all(block_sensitivity)
    any_exclude = any(block_sensitivity)
    direction_consistent = sign_prob > 0.80 or sign_prob < 0.20

    if all_exclude and direction_consistent:
        return "ROBUST"
    elif any_exclude and direction_consistent:
        return "TENTATIVE"
    elif direction_consistent and not any_exclude:
        return "TENTATIVE"
    else:
        return "UNSUPPORTED"


# ═══════════════════════════════════════════════════════════════════════════
# ARTIFACT SAVING
# ═══════════════════════════════════════════════════════════════════════════

def _safe(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if v is None:
        return None
    return v


def _clean_row(d: dict) -> dict:
    return {k: _safe(v) for k, v in d.items() if not k.startswith("_")}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("Step 5: Statistical Robustness + Temporal Stability Audit")
    print("=" * 70)
    t0 = time.time()

    # ── 1. Load data ──────────────────────────────────────────────────────
    curves = load_equity_curves()
    timestamps = load_bar_timestamps()
    df_h4 = load_h4_dataframe()
    btc_close = df_h4["close"].to_numpy(dtype=np.float64)
    n = len(timestamps)
    print(f"Loaded {len(curves)} equity curves, {n} bars")

    # Extract return streams
    returns = {}
    for name in curves:
        returns[name] = equity_to_returns(curves[name])

    # ══════════════════════════════════════════════════════════════════════
    # SECTION A: BOOTSTRAP PRIMARY HYPOTHESES
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("BOOTSTRAP PRIMARY HYPOTHESES (5000 reps × 3 block lengths)")
    print("=" * 70)

    primary_results = []
    method_sensitivity = []

    # H1: Sharpe(E0_EV12) - Sharpe(LATCH_EV12) > 0
    print("\n  H1: E0 equal-sizing Sharpe edge over LATCH")
    h1_by_block = {}
    for bl in BLOCK_LENGTHS:
        res = bootstrap_sharpe_diff(
            returns["E0_EntryVol_12"], returns["LATCH_EntryVol_12"],
            bl, N_BOOT, SEED)
        res["hypothesis"] = "H1"
        res["block_length"] = bl
        res["comparison"] = "E0_EV12 - LATCH_EV12"
        h1_by_block[bl] = res
        print(f"    block={bl:>3}: mean={res['mean']:+.4f}  "
              f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
              f"P(>0)={res['sign_probability']:.3f}  "
              f"CI excl 0={res['ci_excludes_zero']}")
        primary_results.append(_clean_row(res))
        method_sensitivity.append({
            "hypothesis": "H1", "block_length": bl,
            "ci_excludes_zero": res["ci_excludes_zero"],
            "sign_prob": res["sign_probability"],
            "mean": res["mean"], "ci_lo": res["ci_lo_95"], "ci_hi": res["ci_hi_95"],
        })

    # H2: CAGR(LATCH at 5% MDD) - CAGR(E0 at 5% MDD) > 0
    print("\n  H2: LATCH CAGR advantage at matched 5% MDD")
    h2_by_block = {}
    matched_budget_rows = []
    for bl in BLOCK_LENGTHS:
        res = bootstrap_matched_mdd_cagr_diff(
            returns["E0_Native"], returns["LATCH_Native"],
            0.05, bl, N_BOOT, SEED)
        res["hypothesis"] = "H2"
        res["block_length"] = bl
        res["comparison"] = "LATCH_5pct - E0_5pct"
        h2_by_block[bl] = res
        print(f"    block={bl:>3}: mean={res['mean']:+.4f}  "
              f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
              f"P(>0)={res['sign_probability']:.3f}  "
              f"sat_E0={res['saturation_a_pct']:.1f}%  "
              f"sat_LA={res['saturation_b_pct']:.1f}%")
        primary_results.append(_clean_row(res))
        matched_budget_rows.append(_clean_row(res))
        method_sensitivity.append({
            "hypothesis": "H2", "block_length": bl,
            "ci_excludes_zero": res["ci_excludes_zero"],
            "sign_prob": res["sign_probability"],
            "mean": res["mean"], "ci_lo": res["ci_lo_95"], "ci_hi": res["ci_hi_95"],
        })

    # H3: CAGR(LATCH at 10% MDD) - CAGR(E0 at 10% MDD) > 0
    print("\n  H3: LATCH CAGR advantage at matched 10% MDD")
    h3_by_block = {}
    for bl in BLOCK_LENGTHS:
        res = bootstrap_matched_mdd_cagr_diff(
            returns["E0_Native"], returns["LATCH_Native"],
            0.10, bl, N_BOOT, SEED)
        res["hypothesis"] = "H3"
        res["block_length"] = bl
        res["comparison"] = "LATCH_10pct - E0_10pct"
        h3_by_block[bl] = res
        print(f"    block={bl:>3}: mean={res['mean']:+.4f}  "
              f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
              f"P(>0)={res['sign_probability']:.3f}  "
              f"sat_E0={res['saturation_a_pct']:.1f}%  "
              f"sat_LA={res['saturation_b_pct']:.1f}%")
        primary_results.append(_clean_row(res))
        matched_budget_rows.append(_clean_row(res))
        method_sensitivity.append({
            "hypothesis": "H3", "block_length": bl,
            "ci_excludes_zero": res["ci_excludes_zero"],
            "sign_prob": res["sign_probability"],
            "mean": res["mean"], "ci_lo": res["ci_lo_95"], "ci_hi": res["ci_hi_95"],
        })

    # H4: Sharpe(LATCH_native) - Sharpe(SM_native) ≈ 0
    print("\n  H4: LATCH vs SM complexity premium")
    h4_by_block = {}
    complexity_rows = []
    for bl in BLOCK_LENGTHS:
        res = bootstrap_sharpe_diff(
            returns["LATCH_Native"], returns["SM_Native"],
            bl, N_BOOT, SEED)
        res["hypothesis"] = "H4"
        res["block_length"] = bl
        res["comparison"] = "LATCH_native - SM_native"
        h4_by_block[bl] = res
        print(f"    block={bl:>3}: mean={res['mean']:+.4f}  "
              f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
              f"P(>0)={res['sign_probability']:.3f}  "
              f"CI excl 0={res['ci_excludes_zero']}")
        primary_results.append(_clean_row(res))
        complexity_rows.append(_clean_row(res))
        method_sensitivity.append({
            "hypothesis": "H4", "block_length": bl,
            "ci_excludes_zero": res["ci_excludes_zero"],
            "sign_prob": res["sign_probability"],
            "mean": res["mean"], "ci_lo": res["ci_lo_95"], "ci_hi": res["ci_hi_95"],
        })

    # Also bootstrap matched-budget LATCH vs SM
    print("\n  H4 secondary: LATCH vs SM at matched 5% and 10% MDD")
    for target_mdd in [0.05, 0.10]:
        bl = 126  # reference block
        res = bootstrap_matched_mdd_cagr_diff(
            returns["SM_Native"], returns["LATCH_Native"],
            target_mdd, bl, N_BOOT, SEED)
        res["hypothesis"] = "H4_secondary"
        res["block_length"] = bl
        res["comparison"] = f"LATCH_{int(target_mdd*100)}pct - SM_{int(target_mdd*100)}pct"
        print(f"    MDD={target_mdd:.0%} block={bl}: mean={res['mean']:+.4f}  "
              f"CI=[{res['ci_lo_95']:+.4f}, {res['ci_hi_95']:+.4f}]  "
              f"P(>0)={res['sign_probability']:.3f}")
        complexity_rows.append(_clean_row(res))

    # ── Holm adjustment for primary hypotheses ─────────────────────────
    # Use reference block (126) for p-value computation
    print("\n  Holm-adjusted p-values (block=126):")
    ref_block = 126
    raw_pvals = []
    for hyp, by_block in [("H1", h1_by_block), ("H2", h2_by_block),
                           ("H3", h3_by_block), ("H4", h4_by_block)]:
        res = by_block[ref_block]
        # Two-sided p-value from sign probability
        sp = res["sign_probability"]
        raw_p = 2 * min(sp, 1 - sp)
        raw_pvals.append(raw_p)

    adjusted = holm_adjust(raw_pvals)
    for i, hyp in enumerate(["H1", "H2", "H3", "H4"]):
        print(f"    {hyp}: raw_p={raw_pvals[i]:.4f}  holm_p={adjusted[i]:.4f}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION B: START-DATE SENSITIVITY
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("START-DATE SENSITIVITY")
    print("=" * 70)
    sds = start_date_sensitivity(curves, timestamps)
    for row in sds:
        print(f"\n  Start={row['start_date']} ({row['n_bars']} bars)")
        for s in ["E0", "SM", "LATCH"]:
            sh = row.get(f"{s}_sharpe", 0)
            print(f"    {s:>5} native Sharpe={sh:.4f}")
        for b in [5, 10]:
            w = row.get(f"winner_{b}pct_mdd", "?")
            print(f"    Winner at {b}% MDD: {w}")
        edge = row.get("equal_sizing_sharpe_edge", 0)
        print(f"    Equal-sizing Sharpe edge (E0-LATCH): {edge:+.4f}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION C: ROLLING-WINDOW STABILITY
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("ROLLING-WINDOW STABILITY")
    print("=" * 70)
    rw = rolling_window_analysis(curves, timestamps, btc_close)

    # Summarize
    for wm in [24, 36]:
        subset = [r for r in rw if r["window_months"] == wm]
        if not subset:
            continue
        n_win = len(subset)
        latch_5 = sum(1 for r in subset if r.get("winner_5pct") == "LATCH")
        latch_10 = sum(1 for r in subset if r.get("winner_10pct") == "LATCH")
        la_beats_sm = sum(1 for r in subset
                         if r.get("latch_minus_sm_sharpe", 0) > 0)
        crossovers = [r["crossover_mdd"] for r in subset if r.get("crossover_mdd") is not None]

        print(f"\n  {wm}-month windows ({n_win} windows):")
        print(f"    LATCH wins at 5% MDD:  {latch_5}/{n_win} ({latch_5/n_win*100:.0f}%)")
        print(f"    LATCH wins at 10% MDD: {latch_10}/{n_win} ({latch_10/n_win*100:.0f}%)")
        print(f"    LATCH beats SM Sharpe: {la_beats_sm}/{n_win} ({la_beats_sm/n_win*100:.0f}%)")
        if crossovers:
            print(f"    Crossover MDD: median={np.median(crossovers):.1%}  "
                  f"range=[{min(crossovers):.1%}, {max(crossovers):.1%}]  "
                  f"({len(crossovers)}/{n_win} windows identifiable)")
        else:
            print(f"    Crossover MDD: not identifiable in any window")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION D: CALENDAR-SLICE DIAGNOSTICS
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("CALENDAR-SLICE DIAGNOSTICS")
    print("=" * 70)
    cal = calendar_slice_analysis(curves, timestamps, btc_close)
    print(f"\n  {'Year':>6} {'BTC':>8} {'E0_Sh':>7} {'SM_Sh':>7} {'LA_Sh':>7} "
          f"{'Win10%':>7} {'EV12Δ':>7}")
    for row in cal:
        print(f"  {row['year']:>6} {row['btc_return']:>+8.1%} "
              f"{row.get('E0_sharpe',0):>7.3f} "
              f"{row.get('SM_sharpe',0):>7.3f} "
              f"{row.get('LATCH_sharpe',0):>7.3f} "
              f"{row.get('winner_10pct','?'):>7} "
              f"{row.get('e0_equal_sizing_edge',0):>+7.3f}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION E: RESOLUTION MATRIX S1-S7
    # ══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("RESOLUTION MATRIX S1-S7")
    print("=" * 70)

    # Classify evidence
    h1_excl = [h1_by_block[bl]["ci_excludes_zero"] for bl in BLOCK_LENGTHS]
    h1_sp = h1_by_block[126]["sign_probability"]
    s1_status = classify_evidence(all(h1_excl), h1_sp, h1_excl)

    h2_excl = [h2_by_block[bl]["ci_excludes_zero"] for bl in BLOCK_LENGTHS]
    h2_sp = h2_by_block[126]["sign_probability"]
    s2_status = classify_evidence(all(h2_excl), h2_sp, h2_excl)

    h3_excl = [h3_by_block[bl]["ci_excludes_zero"] for bl in BLOCK_LENGTHS]
    h3_sp = h3_by_block[126]["sign_probability"]
    s3_status = classify_evidence(all(h3_excl), h3_sp, h3_excl)

    # S4: temporal stability — check rolling window consistency
    rw_24 = [r for r in rw if r["window_months"] == 24]
    if rw_24:
        latch_5_pct = sum(1 for r in rw_24 if r.get("winner_5pct") == "LATCH") / len(rw_24)
        latch_10_pct = sum(1 for r in rw_24 if r.get("winner_10pct") == "LATCH") / len(rw_24)
        s4_stable = latch_5_pct > 0.60 and latch_10_pct > 0.60
        s4_status = "ROBUST" if s4_stable else ("TENTATIVE" if latch_5_pct > 0.50 else "UNSUPPORTED")
    else:
        s4_status = "UNSUPPORTED"

    # S5: start-date sensitivity — check if conclusions change
    sd_consistent = True
    for row in sds:
        if row.get("winner_10pct_mdd") != "LATCH":
            sd_consistent = False
    s5_status = "ROBUST" if sd_consistent else "TENTATIVE"

    # S6: LATCH vs SM complexity premium
    h4_excl = [h4_by_block[bl]["ci_excludes_zero"] for bl in BLOCK_LENGTHS]
    h4_sp = h4_by_block[126]["sign_probability"]
    h4_mean = h4_by_block[126]["mean"]
    # Need BOTH statistical support AND practical materiality (>0.05 Sharpe)
    if all(h4_excl) and abs(h4_mean) > 0.05:
        s6_status = "ROBUST"
    elif any(h4_excl) and abs(h4_mean) > 0.03:
        s6_status = "TENTATIVE"
    else:
        s6_status = "UNSUPPORTED"

    # S7: overall evidence quality
    critical_ok = s1_status in ("ROBUST", "TENTATIVE") and \
                  s2_status in ("ROBUST", "TENTATIVE") and \
                  s3_status in ("ROBUST", "TENTATIVE")
    s7_status = "ROBUST" if critical_ok else "TENTATIVE"

    resolutions = [
        {"id": "S1",
         "question": "Is E0's equal-sizing Sharpe edge over LATCH statistically supported?",
         "status": s1_status,
         "evidence": f"Bootstrap CI=[{h1_by_block[126]['ci_lo_95']:+.4f}, {h1_by_block[126]['ci_hi_95']:+.4f}], P(>0)={h1_sp:.3f}",
         "conclusion": f"{'Yes' if s1_status == 'ROBUST' else 'Partially' if s1_status == 'TENTATIVE' else 'No'} — E0 signal-quality edge {s1_status}",
         "next_action": "None" if s1_status == "ROBUST" else "More data or bootstrap with longer series"},
        {"id": "S2",
         "question": "Is LATCH's low-risk matched-MDD CAGR advantage over E0 statistically supported at 5% budget?",
         "status": s2_status,
         "evidence": f"Bootstrap CI=[{h2_by_block[126]['ci_lo_95']:+.4f}, {h2_by_block[126]['ci_hi_95']:+.4f}], P(>0)={h2_sp:.3f}",
         "conclusion": f"LATCH low-risk advantage {s2_status}",
         "next_action": "None" if s2_status == "ROBUST" else "More data"},
        {"id": "S3",
         "question": "Is LATCH's low-risk matched-MDD CAGR advantage over E0 statistically supported at 10% budget?",
         "status": s3_status,
         "evidence": f"Bootstrap CI=[{h3_by_block[126]['ci_lo_95']:+.4f}, {h3_by_block[126]['ci_hi_95']:+.4f}], P(>0)={h3_sp:.3f}",
         "conclusion": f"LATCH low-risk advantage {s3_status}",
         "next_action": "None" if s3_status == "ROBUST" else "More data"},
        {"id": "S4",
         "question": "Is the approximate low-risk / high-risk two-regime model temporally stable?",
         "status": s4_status,
         "evidence": f"LATCH wins at 5% MDD in {latch_5_pct*100:.0f}% of 24-month windows, 10% in {latch_10_pct*100:.0f}%",
         "conclusion": f"Two-regime model {s4_status}",
         "next_action": "None" if s4_status == "ROBUST" else "Investigate unstable windows"},
        {"id": "S5",
         "question": "Do the main conclusions materially depend on starting the sample in 2017-08 instead of 2019-01?",
         "status": s5_status,
         "evidence": f"Conclusions {'consistent' if sd_consistent else 'vary'} across start dates",
         "conclusion": f"Start-date independence {s5_status}",
         "next_action": "None"},
        {"id": "S6",
         "question": "Is LATCH's edge over SM robust enough to justify its added complexity?",
         "status": s6_status,
         "evidence": f"Sharpe diff mean={h4_mean:+.4f}, CI excl 0 at all blocks={all(h4_excl)}",
         "conclusion": f"Complexity premium {'JUSTIFIED' if s6_status == 'ROBUST' else 'NOT_JUSTIFIED_BY_CURRENT_EVIDENCE'}",
         "next_action": "None" if s6_status == "ROBUST" else "Prefer SM over LATCH (fewer params, similar performance)"},
        {"id": "S7",
         "question": "Is the evidence base strong enough to proceed to the final synthesis memo without more technical work?",
         "status": s7_status,
         "evidence": f"S1={s1_status}, S2={s2_status}, S3={s3_status}, S4={s4_status}, S5={s5_status}, S6={s6_status}",
         "conclusion": f"Evidence base {s7_status} — {'proceed to final synthesis' if s7_status in ('ROBUST','TENTATIVE') else 'additional work needed'}",
         "next_action": "Write final synthesis memo"},
    ]

    for r in resolutions:
        print(f"\n  {r['id']}: {r['question']}")
        print(f"       Status: {r['status']}")
        print(f"       → {r['conclusion']}")

    # ══════════════════════════════════════════════════════════════════════
    # SAVE ARTIFACTS
    # ══════════════════════════════════════════════════════════════════════
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("SAVING ARTIFACTS")
    print("=" * 70)

    # 1. Primary bootstrap tests
    pd.DataFrame(primary_results).to_csv(
        ARTIFACTS / "bootstrap_primary_tests.csv", index=False)
    print("  bootstrap_primary_tests.csv")

    # 2. Method sensitivity
    pd.DataFrame(method_sensitivity).to_csv(
        ARTIFACTS / "bootstrap_method_sensitivity.csv", index=False)
    print("  bootstrap_method_sensitivity.csv")

    # 3. Matched-budget bootstrap diffs
    pd.DataFrame(matched_budget_rows).to_csv(
        ARTIFACTS / "bootstrap_matched_budget_diffs.csv", index=False)
    print("  bootstrap_matched_budget_diffs.csv")

    # 4. SM vs LATCH complexity bootstrap
    pd.DataFrame(complexity_rows).to_csv(
        ARTIFACTS / "bootstrap_sm_latch_complexity.csv", index=False)
    print("  bootstrap_sm_latch_complexity.csv")

    # 5. Start-date sensitivity
    pd.DataFrame([_clean_row(r) for r in sds]).to_csv(
        ARTIFACTS / "start_date_sensitivity.csv", index=False)
    print("  start_date_sensitivity.csv")

    # 6. Rolling-window summary
    rw_summary = []
    for wm in [24, 36]:
        subset = [r for r in rw if r["window_months"] == wm]
        if not subset:
            continue
        n_w = len(subset)
        l5 = sum(1 for r in subset if r.get("winner_5pct") == "LATCH")
        l10 = sum(1 for r in subset if r.get("winner_10pct") == "LATCH")
        la_sm = sum(1 for r in subset if r.get("latch_minus_sm_sharpe", 0) > 0)
        xo = [r["crossover_mdd"] for r in subset if r.get("crossover_mdd") is not None]
        rw_summary.append({
            "window_months": wm, "n_windows": n_w,
            "latch_wins_5pct": l5, "latch_wins_5pct_frac": l5/n_w,
            "latch_wins_10pct": l10, "latch_wins_10pct_frac": l10/n_w,
            "latch_beats_sm": la_sm, "latch_beats_sm_frac": la_sm/n_w,
            "crossover_median": float(np.median(xo)) if xo else None,
            "crossover_min": float(min(xo)) if xo else None,
            "crossover_max": float(max(xo)) if xo else None,
            "crossover_identifiable": len(xo),
        })
    pd.DataFrame(rw_summary).to_csv(
        ARTIFACTS / "rolling_window_summary.csv", index=False)
    print("  rolling_window_summary.csv")

    # 7. Rolling-window details
    pd.DataFrame([_clean_row(r) for r in rw]).to_csv(
        ARTIFACTS / "rolling_window_details.csv", index=False)
    print("  rolling_window_details.csv")

    # 8. Calendar-slice metrics
    pd.DataFrame([_clean_row(r) for r in cal]).to_csv(
        ARTIFACTS / "calendar_slice_metrics.csv", index=False)
    print("  calendar_slice_metrics.csv")

    # 9. Crossover stability
    crossover_rows = []
    for r in rw:
        if r.get("crossover_mdd") is not None:
            crossover_rows.append({
                "window_months": r["window_months"],
                "date_start": r["date_start"],
                "date_end": r["date_end"],
                "crossover_mdd": r["crossover_mdd"],
            })
    pd.DataFrame(crossover_rows).to_csv(
        ARTIFACTS / "crossover_stability.csv", index=False)
    print("  crossover_stability.csv")

    # 10. Resolution matrix
    pd.DataFrame(resolutions).to_csv(
        ARTIFACTS / "step5_resolution_matrix.csv", index=False)
    print("  step5_resolution_matrix.csv")

    # 11. Bootstrap replications (parquet)
    boot_reps = {}
    for hyp, by_block in [("H1", h1_by_block), ("H2", h2_by_block),
                           ("H3", h3_by_block), ("H4", h4_by_block)]:
        for bl in BLOCK_LENGTHS:
            col = f"{hyp}_bl{bl}"
            boot_reps[col] = by_block[bl]["_diffs"]
    np.savez_compressed(str(ARTIFACTS / "bootstrap_replications.npz"), **boot_reps)
    print("  bootstrap_replications.npz")

    # 12. Holm-adjusted p-values
    holm_results = []
    for i, hyp in enumerate(["H1", "H2", "H3", "H4"]):
        holm_results.append({
            "hypothesis": hyp, "raw_p": raw_pvals[i],
            "holm_p": adjusted[i], "block_length": ref_block,
        })
    with open(ARTIFACTS / "holm_pvalues.json", "w") as f:
        json.dump(holm_results, f, indent=2)
    print("  holm_pvalues.json")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
