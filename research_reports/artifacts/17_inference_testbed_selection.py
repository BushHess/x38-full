#!/usr/bin/env python3
"""17 — Inference Testbed Selection: Pair Diagnostics.

Simulate all available strategy families on real data at matched settings,
then compute pair-level diagnostics for inference-method evaluation.

Strategies:
  VTREND_A0: EMA cross + ATR(14) trail + VDO  [baseline]
  VTREND_A1: EMA cross + ATR(20) trail + VDO  [period variant]
  VBREAK:    Donchian breakout + ATR trail + VDO
  VCUSUM:    CUSUM change-point + ATR trail + VDO
  VTWIN:     EMA + Donchian dual-confirm + ATR trail + VDO
  BUY_HOLD:  100% exposure from warmup start

Diagnostics per pair:
  - Return correlation (Pearson)
  - Same-direction rate (both positive or both negative)
  - Exact-return-equality rate (|diff| < 1e-12)
  - Within-1bp rate (|diff| < 0.0001)
  - Within-10bp rate (|diff| < 0.001)
  - Exposure-agreement rate (both in or both out)
  - Sharpe difference, CAGR difference
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ───────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0
ANN    = math.sqrt(6.0 * 365.25)

SP     = 120
TRAIL  = 3.0
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28

OUTDIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════════
# Indicator helpers (not imported from strategies to avoid import chains)
# ═══════════════════════════════════════════════════════════════════

def _highest_high(high, n):
    out = np.full(len(high), np.nan)
    if n <= 0 or n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out

def _lowest_low(low, m):
    out = np.full(len(low), np.nan)
    if m <= 0 or m >= len(low):
        return out
    windows = sliding_window_view(low, m)
    out[m:] = np.min(windows[:len(low) - m], axis=1)
    return out

def _log_returns(close):
    r = np.zeros(len(close), dtype=np.float64)
    r[1:] = np.log(close[1:] / close[:-1])
    return r

def _rolling_zscore(returns, window):
    n = len(returns)
    z = np.zeros(n, dtype=np.float64)
    for i in range(window, n):
        ref = returns[i - window:i]
        mu = np.mean(ref)
        sigma = np.std(ref, ddof=1)
        if sigma > 1e-12:
            z[i] = (returns[i] - mu) / sigma
    return z

def _cusum(z, k):
    n = len(z)
    cup = np.zeros(n)
    cdn = np.zeros(n)
    for i in range(1, n):
        cup[i] = max(0, cup[i-1] + z[i] - k)
        cdn[i] = max(0, cdn[i-1] - z[i] - k)
    return cup, cdn

def _atr_p(hi, lo, cl, period):
    """Standard ATR with arbitrary period (not imported, self-contained)."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


# ═══════════════════════════════════════════════════════════════════
# Generic simulation engine
# ═══════════════════════════════════════════════════════════════════

def simulate(cl, entry_signal, exit_signal, exit_atr, trail_mult, wi):
    """Generic sim: entry_signal[i]=True triggers buy, exit_signal[i]=True
    triggers sell.  Also exits on ATR trailing stop using exit_atr.
    Returns bar-level NAV array and exposure array."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    nav_arr = np.zeros(n)
    exp_arr = np.zeros(n)

    for i in range(n):
        p = cl[i]

        # Fill pending
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        nav_arr[i] = nav
        exp_arr[i] = 1.0 if inp else 0.0

        # Skip signal gen before warmup or if indicators not ready
        ea = exit_atr[i]
        if math.isnan(ea):
            continue

        if not inp:
            if entry_signal[i]:
                pe = True
        else:
            pk = max(pk, p)
            trail = pk - trail_mult * ea
            if p < trail:
                px = True
            elif exit_signal[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nav_arr[-1] = cash
        exp_arr[-1] = 0.0

    return nav_arr, exp_arr


# ═══════════════════════════════════════════════════════════════════
# Strategy-specific signal builders
# ═══════════════════════════════════════════════════════════════════

def build_vtrend_a0(cl, hi, lo, vo, tb, wi):
    """VTREND with ATR(14), sp=120."""
    fp = max(5, SP // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, SP)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)

    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at[i]):
            continue
        if ef[i] > es[i] and vd[i] > 0.0:
            entry[i] = True
        if ef[i] < es[i]:
            exit_s[i] = True

    return entry, exit_s, at, "VTREND_A0"


def build_vtrend_a1(cl, hi, lo, vo, tb, wi):
    """VTREND with ATR(20), sp=120."""
    fp = max(5, SP // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, SP)
    at14 = _atr(hi, lo, cl, ATR_P)  # for NaN gating
    at20 = _atr_p(hi, lo, cl, 20)   # for trailing stop
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)

    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at14[i]) or math.isnan(at20[i]):
            continue
        if ef[i] > es[i] and vd[i] > 0.0:
            entry[i] = True
        if ef[i] < es[i]:
            exit_s[i] = True

    return entry, exit_s, at20, "VTREND_A1"


def build_vbreak(cl, hi, lo, vo, tb, wi):
    """VBREAK with entry_lookback=120, exit_lookback=40."""
    hh = _highest_high(hi, SP)
    ll = _lowest_low(lo, 40)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)

    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(hh[i]) or math.isnan(ll[i]) or math.isnan(at[i]):
            continue
        if cl[i] > hh[i] and vd[i] > 0.0:
            entry[i] = True
        if cl[i] < ll[i]:
            exit_s[i] = True

    return entry, exit_s, at, "VBREAK"


def build_vcusum(cl, hi, lo, vo, tb, wi):
    """VCUSUM with ref_window=120, threshold=4.0."""
    log_ret = _log_returns(cl)
    z = _rolling_zscore(log_ret, SP)
    cup, cdn = _cusum(z, 0.5)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)

    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(at[i]):
            continue
        if cup[i] > 4.0 and vd[i] > 0.0:
            entry[i] = True
        if cdn[i] > 4.0:
            exit_s[i] = True

    return entry, exit_s, at, "VCUSUM"


def build_vtwin(cl, hi, lo, vo, tb, wi):
    """VTWIN with slow_period=120."""
    fp = max(5, SP // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, SP)
    hh = _highest_high(hi, SP)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)

    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(hh[i]) or math.isnan(at[i]):
            continue
        if ef[i] > es[i] and cl[i] > hh[i] and vd[i] > 0.0:
            entry[i] = True
        if ef[i] < es[i]:
            exit_s[i] = True

    return entry, exit_s, at, "VTWIN"


def build_buy_hold(cl, hi, lo, vo, tb, wi):
    """Buy and hold from warmup end."""
    n = len(cl)
    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    entry[wi] = True  # enter at warmup end
    at = _atr(hi, lo, cl, ATR_P)
    # Use huge trail_mult effectively (never triggers)
    return entry, exit_s, at, "BUY_HOLD"


# ═══════════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════════

def compute_metrics(nav, wi):
    """Sharpe, CAGR, MDD, trade count from NAV array."""
    post = nav[wi:]
    n = len(post)
    if n < 2 or post[0] <= 0:
        return {"sharpe": 0, "cagr": -100, "mdd": 100}

    rets = np.diff(post) / post[:-1]
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    tr = post[-1] / post[0] - 1.0
    yrs = (n - 1) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

    peak = np.maximum.accumulate(post)
    dd = 1.0 - post / peak
    mdd = float(np.max(dd)) * 100

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


def pair_diagnostics(nav_a, nav_b, exp_a, exp_b, wi):
    """Compute all pair-level diagnostics on post-warmup bars."""
    post_a = nav_a[wi:]
    post_b = nav_b[wi:]
    exp_pa = exp_a[wi:]
    exp_pb = exp_b[wi:]

    ret_a = np.diff(post_a) / post_a[:-1]
    ret_b = np.diff(post_b) / post_b[:-1]

    n = len(ret_a)

    # Correlation
    corr = float(np.corrcoef(ret_a, ret_b)[0, 1])

    # Same direction
    same_dir = float(np.mean((ret_a > 0) == (ret_b > 0)))

    # Exact equality
    diff = np.abs(ret_a - ret_b)
    exact_eq = float(np.mean(diff < 1e-12))

    # Within thresholds
    within_1bp = float(np.mean(diff < 0.0001))
    within_10bp = float(np.mean(diff < 0.001))
    within_50bp = float(np.mean(diff < 0.005))

    # Exposure agreement (bars where both agree on in/out)
    exp_agree = float(np.mean(exp_pa[1:] == exp_pb[1:]))

    # Both-in rate (fraction of bars where both are in position)
    both_in = float(np.mean((exp_pa[1:] == 1.0) & (exp_pb[1:] == 1.0)))

    # Sharpe difference
    met_a = compute_metrics(nav_a, wi)
    met_b = compute_metrics(nav_b, wi)
    d_sharpe = met_a["sharpe"] - met_b["sharpe"]
    d_cagr = met_a["cagr"] - met_b["cagr"]
    d_mdd = met_a["mdd"] - met_b["mdd"]

    return {
        "corr": corr,
        "same_dir_rate": same_dir,
        "exact_eq_rate": exact_eq,
        "within_1bp_rate": within_1bp,
        "within_10bp_rate": within_10bp,
        "within_50bp_rate": within_50bp,
        "exposure_agree_rate": exp_agree,
        "both_in_rate": both_in,
        "d_sharpe": d_sharpe,
        "d_cagr": d_cagr,
        "d_mdd": d_mdd,
        "metrics_a": met_a,
        "metrics_b": met_b,
    }


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    print("=" * 70)
    print("17 — INFERENCE TESTBED SELECTION: PAIR DIAGNOSTICS")
    print("=" * 70)

    # Load data
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    print(f"  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")
    print(f"  sp={SP}, trail={TRAIL}, ATR_P={ATR_P}, cost={COST.round_trip_bps}bps RT")

    # Build all strategies
    builders = [
        build_vtrend_a0,
        build_vtrend_a1,
        build_vbreak,
        build_vcusum,
        build_vtwin,
        build_buy_hold,
    ]

    strategies = {}
    for builder in builders:
        entry, exit_s, exit_atr, name = builder(cl, hi, lo, vo, tb, wi)
        # Buy-and-hold uses huge trail to never trigger
        tm = 999.0 if name == "BUY_HOLD" else TRAIL
        nav, exp = simulate(cl, entry, exit_s, exit_atr, tm, wi)
        met = compute_metrics(nav, wi)
        strategies[name] = {"nav": nav, "exp": exp, "metrics": met}

        # Count trades (exposure transitions from 0->1)
        exp_post = exp[wi:]
        n_trades = int(np.sum((exp_post[1:] == 1.0) & (exp_post[:-1] == 0.0)))
        in_rate = float(np.mean(exp_post))

        print(f"\n  {name}:")
        print(f"    Sharpe={met['sharpe']:.3f}  CAGR={met['cagr']:+.1f}%  "
              f"MDD={met['mdd']:.1f}%  trades~{n_trades}  in_rate={in_rate:.1%}")

    # Compute all pairs
    names = list(strategies.keys())
    n_strats = len(names)

    print("\n" + "=" * 70)
    print("PAIR DIAGNOSTICS")
    print("=" * 70)

    header = (f"  {'pair':<28}  {'corr':>6}  {'same_d':>6}  {'exact':>6}  "
              f"{'<1bp':>6}  {'<10bp':>6}  {'<50bp':>6}  {'exp_ag':>6}  "
              f"{'both_in':>7}  {'ΔSh':>7}  {'ΔCAGR':>7}")
    print(header)
    print("  " + "-" * 115)

    pair_results = {}
    for i in range(n_strats):
        for j in range(i + 1, n_strats):
            a_name = names[i]
            b_name = names[j]
            pair_key = f"{a_name} vs {b_name}"

            diag = pair_diagnostics(
                strategies[a_name]["nav"], strategies[b_name]["nav"],
                strategies[a_name]["exp"], strategies[b_name]["exp"],
                wi)

            pair_results[pair_key] = diag

            print(f"  {pair_key:<28}  {diag['corr']:6.4f}  "
                  f"{diag['same_dir_rate']:5.1%}  {diag['exact_eq_rate']:5.1%}  "
                  f"{diag['within_1bp_rate']:5.1%}  {diag['within_10bp_rate']:5.1%}  "
                  f"{diag['within_50bp_rate']:5.1%}  {diag['exposure_agree_rate']:5.1%}  "
                  f"{diag['both_in_rate']:6.1%}  {diag['d_sharpe']:+7.3f}  "
                  f"{diag['d_cagr']:+6.1f}%")

    # Classification
    print("\n" + "=" * 70)
    print("PAIR CLASSIFICATION")
    print("=" * 70)

    for pair_key, diag in pair_results.items():
        corr = diag["corr"]
        exact = diag["exact_eq_rate"]
        exp_ag = diag["exposure_agree_rate"]
        d_sh = abs(diag["d_sharpe"])

        if exact > 0.80:
            cat = "TOO IDENTICAL"
        elif corr > 0.995 and exp_ag > 0.95:
            cat = "NEAR-NULL / NEGATIVE CONTROL"
        elif corr > 0.98 and d_sh < 0.10:
            cat = "NEAR-NULL / NEGATIVE CONTROL"
        elif corr < 0.90 or d_sh > 0.30:
            cat = "POSITIVE CONTROL"
        elif corr < 0.95 or d_sh > 0.15:
            cat = "PLAUSIBLE MAIN TESTBED"
        else:
            cat = "WEAK DIFFERENTIATOR"

        # Determine difference type
        if "A0 vs VTREND_A1" in pair_key:
            diff_type = "parameter tweak (ATR period 14→20)"
        elif "BUY_HOLD" in pair_key:
            diff_type = "genuinely different architecture (active vs passive)"
        elif "VTREND" in pair_key.split(" vs ")[0] and pair_key.split(" vs ")[1] in ("VBREAK", "VCUSUM", "VTWIN"):
            diff_type = "different entry architecture, shared exit framework"
        elif pair_key.split(" vs ")[0] in ("VBREAK", "VCUSUM", "VTWIN") and pair_key.split(" vs ")[1] in ("VBREAK", "VCUSUM", "VTWIN"):
            diff_type = "different entry architecture, shared exit framework"
        elif "BUY_HOLD" not in pair_key and "A1" not in pair_key:
            diff_type = "different entry architecture, shared exit framework"
        else:
            diff_type = "mixed"

        print(f"  {pair_key:<28}  {cat:<30}  [{diff_type}]")

    # Save
    print("\n" + "=" * 70)
    print("SAVING")
    print("=" * 70)

    output = {
        "config": {
            "sp": SP, "trail": TRAIL, "atr_period": ATR_P,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup_days": WARMUP,
            "n_bars": n, "warmup_idx": wi,
        },
        "strategy_metrics": {},
        "pair_diagnostics": {},
    }

    for name, s in strategies.items():
        exp_post = s["exp"][wi:]
        n_trades = int(np.sum((exp_post[1:] == 1.0) & (exp_post[:-1] == 0.0)))
        output["strategy_metrics"][name] = {
            **{k: round(v, 6) for k, v in s["metrics"].items()},
            "approx_trades": n_trades,
            "in_position_rate": round(float(np.mean(exp_post)), 4),
        }

    for pair_key, diag in pair_results.items():
        output["pair_diagnostics"][pair_key] = {
            k: round(v, 6) if isinstance(v, float) else v
            for k, v in diag.items()
            if k not in ("metrics_a", "metrics_b")
        }

    out_path = OUTDIR / "17_inference_testbed_selection.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {out_path}")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
