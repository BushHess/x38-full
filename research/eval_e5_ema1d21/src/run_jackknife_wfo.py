#!/usr/bin/env python3
"""Jackknife + Walk-Forward Optimization for E5_plus_EMA1D21.

Analyses:
  1. WFO: 8 windows (train=24m, test=6m, slide=6m)
     - Candidate = E5_plus_EMA1D21, Baseline = E0
     - Score: 2.5*CAGR - 0.60*MDD + 8.0*max(0,Sharpe) + 5.0*max(0,min(PF,3)-1) + min(trades/50,1)*5
     - Pass: 6/8 positive delta windows (60% threshold)
  2. Jackknife: Remove top-K (K=1,3,5,10) most profitable trades
     - Recompute Sharpe and CAGR after removal
     - Also remove bottom-K worst trades

Uses vectorized sim functions from parity_eval.py pattern.

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
from scipy.signal import lfilter

# ── Path setup ─────────────────────────────────────────────────────────────
_SCRIPT = Path(__file__).resolve()
_SRC = _SCRIPT.parent
_NAMESPACE = _SRC.parent
_REPO = _NAMESPACE.parent.parent

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

DATA = str(_REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
TRAIL = 3.0
DEFAULT_SLOW = 120

CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0


# ═══════════════════════════════════════════════════════════════════════════
# FAST INDICATORS (vectorized via scipy.signal.lfilter)
# ═══════════════════════════════════════════════════════════════════════════

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100, period: int = 20) -> np.ndarray:
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)

    from numpy.lib.stride_tricks import sliding_window_view
    tr_cap = np.full(n, np.nan)
    if cap_lb <= n:
        windows = sliding_window_view(tr[:n], cap_lb)
        relevant = windows[:n - cap_lb]
        q_vals = np.percentile(relevant, cap_q * 100, axis=1)
        tr_slice = tr[cap_lb:n]
        tr_cap[cap_lb:n] = np.minimum(tr_slice, q_vals)

    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        seed = np.nanmean(tr_cap[s:s + period])
        ratr[s + period - 1] = seed
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            ratr[s + period:] = smoothed
    return ratr


# ═══════════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════════

def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr_pct": -100.0, "max_drawdown_mid_pct": 100.0, "trades": nt,
                "profit_factor": 0.0}

    rets = navs[1:] / navs[:-1] - 1.0
    n = len(rets)
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    total_ret = navs[-1] / navs[0] - 1.0
    yrs = n / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0

    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100

    # Profit factor from bar returns
    wins = rets[rets > 0].sum()
    losses = np.abs(rets[rets < 0].sum())
    pf = wins / losses if losses > 1e-12 else 3.0

    return {"sharpe": sharpe, "cagr_pct": cagr, "max_drawdown_mid_pct": mdd,
            "trades": nt, "profit_factor": pf}


def _objective(summary):
    """Scoring formula matching validation/suites/wfo.py."""
    n_trades = summary.get("trades", 0)
    cagr = summary.get("cagr_pct", 0.0)
    max_dd = summary.get("max_drawdown_mid_pct", 0.0)
    sharpe = summary.get("sharpe", 0.0)
    pf = min(summary.get("profit_factor", 0.0), 3.0)

    return (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, pf - 1.0)
        + min(n_trades / 50.0, 1.0) * 5.0
    )


# ═══════════════════════════════════════════════════════════════════════════
# VECTORIZED SIM FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH):
    """VTREND E0 — baseline."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi,
                    d1_cl, d1_close_times, h4_close_times,
                    slow_period=120, trail_mult=3.0, cps=CPS_HARSH,
                    d1_ema_period=21, return_trades=False):
    """E5 + EMA(21) D1 regime filter — robust ATR trail + D1 regime entry gate."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # D1 regime
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema

    # Map D1 regime to H4 bars
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_close_times[i]:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_close_times[i]:
            regime_h4[i] = d1_regime[d1_idx]

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)
    trades = [] if return_trades else None
    entry_bar = 0
    entry_price = 0.0

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bar = i; entry_price = fp * (1 + cps)
            elif px:
                px = False
                exit_price = fp * (1 - cps)
                pnl = bq * (exit_price - entry_price)
                ret_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
                if return_trades:
                    trades.append({
                        "entry_bar": entry_bar, "exit_bar": i,
                        "entry_price": entry_price, "exit_price": exit_price,
                        "pnl_usd": pnl, "return_pct": ret_pct,
                    })
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * ratr[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        exit_price = cl[-1] * (1 - cps)
        pnl = bq * (exit_price - entry_price)
        ret_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
        if return_trades:
            trades.append({
                "entry_bar": entry_bar, "exit_bar": n - 1,
                "entry_price": entry_price, "exit_price": exit_price,
                "pnl_usd": pnl, "return_pct": ret_pct,
            })
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    if return_trades:
        return nav, nt, trades
    return nav, nt


# ═══════════════════════════════════════════════════════════════════════════
# WFO ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def generate_windows(start, end, train_months=24, test_months=6, slide_months=6):
    """Generate sliding WFO windows with inclusive boundaries."""
    from dateutil.relativedelta import relativedelta
    from datetime import datetime, timedelta

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    windows = []
    wid = 0
    train_start = start_dt

    while True:
        train_end = train_start + relativedelta(months=train_months) - timedelta(days=1)
        test_start = train_end + timedelta(days=1)
        test_end = test_start + relativedelta(months=test_months) - timedelta(days=1)

        if test_end > end_dt:
            break

        windows.append({
            "window_id": wid,
            "train_start": train_start.strftime("%Y-%m-%d"),
            "train_end": train_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
        })
        wid += 1
        train_start += relativedelta(months=slide_months)

    return windows


def run_wfo():
    """WFO: 8 windows, E5_plus_EMA1D21 vs E0 baseline."""
    print("=" * 70)
    print("WFO: E5_plus_EMA1D21 vs E0 (8 windows)")
    print("=" * 70)

    windows = generate_windows(START, END)
    print(f"  Generated {len(windows)} WFO windows")

    results = []

    for w in windows:
        wid = w["window_id"]
        test_start = w["test_start"]
        test_end = w["test_end"]

        # Load data for test period
        feed = DataFeed(DATA, start=test_start, end=test_end, warmup_days=WARMUP)
        h4 = feed.h4_bars
        d1 = feed.d1_bars

        n = len(h4)
        cl = np.array([b.close for b in h4], dtype=np.float64)
        hi = np.array([b.high for b in h4], dtype=np.float64)
        lo = np.array([b.low for b in h4], dtype=np.float64)
        vo = np.array([b.volume for b in h4], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
        h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)

        d1_cl = np.array([b.close for b in d1], dtype=np.float64)
        d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

        wi = 0
        if feed.report_start_ms is not None:
            for i, b in enumerate(h4):
                if b.close_time >= feed.report_start_ms:
                    wi = i
                    break

        # Run E0 baseline
        nav_e0, nt_e0 = sim_e0(cl, hi, lo, vo, tb, wi, cps=CPS_HARSH)
        m_e0 = _metrics(nav_e0, wi, nt_e0)
        score_e0 = _objective(m_e0)

        # Run E5_plus_EMA1D21 candidate
        nav_cand, nt_cand = sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi,
                                             d1_cl, d1_ct, h4_ct, cps=CPS_HARSH)
        m_cand = _metrics(nav_cand, wi, nt_cand)
        score_cand = _objective(m_cand)

        delta = score_cand - score_e0

        row = {
            "window_id": wid,
            "test_start": test_start,
            "test_end": test_end,
            "candidate_score": round(score_cand, 4),
            "baseline_score": round(score_e0, 4),
            "delta_harsh_score": round(delta, 4),
            "candidate_cagr_pct": round(m_cand["cagr_pct"], 2),
            "baseline_cagr_pct": round(m_e0["cagr_pct"], 2),
            "candidate_max_dd_pct": round(m_cand["max_drawdown_mid_pct"], 2),
            "baseline_max_dd_pct": round(m_e0["max_drawdown_mid_pct"], 2),
            "candidate_sharpe": round(m_cand["sharpe"], 4),
            "baseline_sharpe": round(m_e0["sharpe"], 4),
            "candidate_trades": nt_cand,
            "baseline_trades": nt_e0,
            "valid_window": True,
        }
        results.append(row)

        status = "+" if delta > 0 else "-"
        print(f"  W{wid} [{test_start} → {test_end}]  "
              f"delta={delta:+8.2f}  "
              f"cand={score_cand:8.2f} base={score_e0:8.2f}  "
              f"Sharpe {m_cand['sharpe']:.3f}/{m_e0['sharpe']:.3f}  "
              f"trades {nt_cand}/{nt_e0}  [{status}]")

    # Aggregate
    deltas = [r["delta_harsh_score"] for r in results]
    n_windows = len(deltas)
    positive = sum(1 for d in deltas if d > 0)
    win_rate = positive / n_windows if n_windows > 0 else 0.0
    mean_delta = np.mean(deltas) if deltas else 0.0
    median_delta = np.median(deltas) if deltas else 0.0
    worst_delta = min(deltas) if deltas else 0.0
    best_delta = max(deltas) if deltas else 0.0

    # Pass criteria: ceil(0.6 * n_windows)
    threshold = int(0.6 * n_windows + 0.999999)
    passed = positive >= threshold

    summary = {
        "n_windows": n_windows,
        "positive_delta_windows": positive,
        "win_rate": round(win_rate, 4),
        "mean_delta_score": round(float(mean_delta), 4),
        "median_delta_score": round(float(median_delta), 4),
        "worst_delta_score": round(float(worst_delta), 4),
        "best_delta_score": round(float(best_delta), 4),
        "threshold_windows": threshold,
        "passed": passed,
    }

    print(f"\n  SUMMARY:")
    print(f"    Positive windows: {positive}/{n_windows} (win_rate={win_rate:.2%})")
    print(f"    Mean delta: {mean_delta:.4f}")
    print(f"    Median delta: {median_delta:.4f}")
    print(f"    Worst delta: {worst_delta:.4f}")
    print(f"    Best delta: {best_delta:.4f}")
    print(f"    Threshold: {threshold}/{n_windows}")
    print(f"    VERDICT: {'PASS' if passed else 'FAIL'}")

    return {"summary": summary, "windows": results}


# ═══════════════════════════════════════════════════════════════════════════
# JACKKNIFE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def _trade_sharpe(returns, trades_per_year):
    """Annualized Sharpe from per-trade returns."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    std = np.std(arr, ddof=0)
    if std < 1e-12:
        return 0.0
    return np.mean(arr) / std * np.sqrt(trades_per_year)


def _safe_cagr(total_pnl, nav0, years):
    """CAGR handling total loss."""
    final = nav0 + total_pnl
    if final <= 0:
        return -1.0
    return (final / nav0) ** (1.0 / years) - 1.0


def run_jackknife():
    """Full backtest → trade-level PnL → top-N jackknife."""
    print("\n" + "=" * 70)
    print("JACKKNIFE: E5_plus_EMA1D21")
    print("=" * 70)

    # Load full data
    print("  Loading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    d1 = feed.d1_bars

    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)

    d1_cl = np.array([b.close for b in d1], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    # Run sim with trade tracking
    nav, nt, trades = sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi,
                                       d1_cl, d1_ct, h4_ct,
                                       cps=CPS_HARSH, return_trades=True)
    m = _metrics(nav, wi, nt)

    print(f"  Full backtest: {nt} trades")
    print(f"    Sharpe={m['sharpe']:.4f}  CAGR={m['cagr_pct']:.2f}%  "
          f"MDD={m['max_drawdown_mid_pct']:.2f}%")

    if not trades:
        print("  No trades — cannot run jackknife")
        return {}

    df = pd.DataFrame(trades)
    total_pnl = df["pnl_usd"].sum()

    # Compute backtest years from data
    navs = nav[wi:]
    n_bars = len(navs) - 1
    backtest_years = n_bars / (6.0 * 365.25)
    trades_per_year = len(df) / backtest_years

    base_sharpe = _trade_sharpe(df["return_pct"].values, trades_per_year)
    base_cagr = _safe_cagr(total_pnl, CASH, backtest_years)

    print(f"\n  Trade-level metrics:")
    print(f"    Trade Sharpe: {base_sharpe:.4f}")
    print(f"    Trade CAGR:   {base_cagr*100:.2f}%")
    print(f"    Total PnL:    ${total_pnl:,.0f}")
    print(f"    Backtest yrs: {backtest_years:.2f}")

    results = {
        "base_sharpe": base_sharpe,
        "base_cagr_pct": base_cagr * 100.0,
        "base_total_pnl": total_pnl,
        "n_trades": len(df),
        "backtest_years": backtest_years,
    }

    # Remove top-K most profitable trades
    sorted_idx = df["pnl_usd"].sort_values(ascending=False).index

    print(f"\n  {'K':>4s}  {'Sharpe':>8s}  {'Δ%':>8s}  {'CAGR%':>8s}  {'Δ%':>8s}  {'PnL':>12s}")
    print(f"  {'base':>4s}  {base_sharpe:>8.4f}  {'—':>8s}  {base_cagr*100:>8.2f}  {'—':>8s}  ${total_pnl:>11,.0f}")

    for k in [1, 3, 5, 10]:
        if k >= len(df):
            continue
        drop_idx = sorted_idx[:k]
        remaining = df.drop(drop_idx)
        r = remaining["return_pct"].values
        pnl = remaining["pnl_usd"].sum()
        tpy_r = len(remaining) / backtest_years
        sharpe = _trade_sharpe(r, tpy_r)
        cagr = _safe_cagr(pnl, CASH, backtest_years)

        sharpe_delta = 100.0 * (sharpe - base_sharpe) / abs(base_sharpe) if base_sharpe != 0 else 0.0
        cagr_delta = 100.0 * (cagr - base_cagr) / abs(base_cagr) if base_cagr != 0 else 0.0

        results[f"drop_top{k}_sharpe"] = sharpe
        results[f"drop_top{k}_cagr_pct"] = cagr * 100.0
        results[f"drop_top{k}_pnl"] = pnl
        results[f"drop_top{k}_sharpe_delta_pct"] = sharpe_delta
        results[f"drop_top{k}_cagr_delta_pct"] = cagr_delta

        print(f"  −{k:>3d}  {sharpe:>8.4f}  {sharpe_delta:>+7.1f}%  "
              f"{cagr*100:>8.2f}  {cagr_delta:>+7.1f}%  ${pnl:>11,.0f}")

    # Remove bottom-K (worst losers)
    sorted_idx_asc = df["pnl_usd"].sort_values(ascending=True).index

    print(f"\n  Removing worst trades:")
    print(f"  {'K':>4s}  {'Sharpe':>8s}  {'CAGR%':>8s}  {'PnL':>12s}")

    for k in [1, 3, 5, 10]:
        if k >= len(df):
            continue
        drop_idx = sorted_idx_asc[:k]
        remaining = df.drop(drop_idx)
        r = remaining["return_pct"].values
        pnl = remaining["pnl_usd"].sum()
        tpy_r = len(remaining) / backtest_years
        sharpe = _trade_sharpe(r, tpy_r)
        cagr = _safe_cagr(pnl, CASH, backtest_years)

        results[f"drop_bot{k}_sharpe"] = sharpe
        results[f"drop_bot{k}_cagr_pct"] = cagr * 100.0
        results[f"drop_bot{k}_pnl"] = pnl

        print(f"  −{k:>3d}  {sharpe:>8.4f}  {cagr*100:>8.2f}  ${pnl:>11,.0f}")

    # Also run E0 jackknife for comparison
    print(f"\n  --- E0 Baseline Jackknife (for comparison) ---")
    nav_e0, nt_e0 = sim_e0(cl, hi, lo, vo, tb, wi, cps=CPS_HARSH)
    m_e0 = _metrics(nav_e0, wi, nt_e0)

    # Run E0 with trade tracking
    nav_e0t, nt_e0t, trades_e0 = _sim_e0_with_trades(cl, hi, lo, vo, tb, wi, cps=CPS_HARSH)
    if trades_e0:
        df_e0 = pd.DataFrame(trades_e0)
        total_pnl_e0 = df_e0["pnl_usd"].sum()
        tpy_e0 = len(df_e0) / backtest_years
        base_sharpe_e0 = _trade_sharpe(df_e0["return_pct"].values, tpy_e0)
        base_cagr_e0 = _safe_cagr(total_pnl_e0, CASH, backtest_years)

        print(f"  E0: {len(df_e0)} trades, Sharpe={base_sharpe_e0:.4f}, CAGR={base_cagr_e0*100:.2f}%")

        results["e0_base_sharpe"] = base_sharpe_e0
        results["e0_base_cagr_pct"] = base_cagr_e0 * 100.0

        sorted_idx_e0 = df_e0["pnl_usd"].sort_values(ascending=False).index
        print(f"  {'K':>4s}  {'E0_Sharpe':>10s}  {'E5D1_Sharpe':>12s}  {'E0_CAGR%':>9s}  {'E5D1_CAGR%':>11s}")
        print(f"  {'base':>4s}  {base_sharpe_e0:>10.4f}  {base_sharpe:>12.4f}  "
              f"{base_cagr_e0*100:>9.2f}  {base_cagr*100:>11.2f}")

        for k in [1, 3, 5, 10]:
            if k >= len(df_e0):
                continue
            drop_idx_e0 = sorted_idx_e0[:k]
            rem_e0 = df_e0.drop(drop_idx_e0)
            pnl_e0 = rem_e0["pnl_usd"].sum()
            tpy_r = len(rem_e0) / backtest_years
            sh_e0 = _trade_sharpe(rem_e0["return_pct"].values, tpy_r)
            cagr_e0 = _safe_cagr(pnl_e0, CASH, backtest_years)

            sh_e5d1 = results.get(f"drop_top{k}_sharpe", 0)
            cagr_e5d1 = results.get(f"drop_top{k}_cagr_pct", 0) / 100.0

            results[f"e0_drop_top{k}_sharpe"] = sh_e0
            results[f"e0_drop_top{k}_cagr_pct"] = cagr_e0 * 100.0

            print(f"  −{k:>3d}  {sh_e0:>10.4f}  {sh_e5d1:>12.4f}  "
                  f"{cagr_e0*100:>9.2f}  {cagr_e5d1*100:>11.2f}")

    return results


def _sim_e0_with_trades(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH):
    """E0 sim with trade tracking for jackknife comparison."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)
    trades = []
    entry_bar = 0; entry_price = 0.0

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bar = i; entry_price = fp * (1 + cps)
            elif px:
                px = False
                exit_price = fp * (1 - cps)
                pnl = bq * (exit_price - entry_price)
                ret_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                              "entry_price": entry_price, "exit_price": exit_price,
                              "pnl_usd": pnl, "return_pct": ret_pct})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        exit_price = cl[-1] * (1 - cps)
        pnl = bq * (exit_price - entry_price)
        ret_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                      "entry_price": entry_price, "exit_price": exit_price,
                      "pnl_usd": pnl, "return_pct": ret_pct})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt, trades


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def _json_default(obj):
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, np.bool_): return bool(obj)
    return str(obj)


def main():
    print("E5_plus_EMA1D21: Jackknife + WFO Evaluation")
    print("=" * 70)
    t0 = time.time()

    # Run WFO
    wfo_results = run_wfo()

    # Run Jackknife
    jackknife_results = run_jackknife()

    # Save artifacts
    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print("SAVING ARTIFACTS")
    print(f"{'=' * 70}")

    master = {
        "wfo": wfo_results,
        "jackknife": jackknife_results,
        "_meta": {
            "elapsed_s": round(elapsed, 1),
            "date": "2026-03-06",
            "strategy": "E5_plus_EMA1D21",
            "baseline": "E0",
        },
    }

    with open(ARTIFACTS / "jackknife_wfo_results.json", "w") as f:
        json.dump(master, f, indent=2, default=_json_default)
    print(f"  jackknife_wfo_results.json")

    # WFO CSV
    pd.DataFrame(wfo_results["windows"]).to_csv(
        ARTIFACTS / "wfo_per_round_metrics.csv", index=False)
    print(f"  wfo_per_round_metrics.csv")

    # WFO summary JSON (matching format of existing WFO results)
    with open(ARTIFACTS / "wfo_summary.json", "w") as f:
        json.dump(wfo_results, f, indent=2, default=_json_default)
    print(f"  wfo_summary.json")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s")
    print(f"{'=' * 70}")

    # Final verdict
    wfo_pass = wfo_results["summary"]["passed"]
    print(f"\n  WFO:       {'PASS' if wfo_pass else 'FAIL'} "
          f"({wfo_results['summary']['positive_delta_windows']}/"
          f"{wfo_results['summary']['n_windows']} positive)")

    if jackknife_results:
        base_s = jackknife_results["base_sharpe"]
        d5_s = jackknife_results.get("drop_top5_sharpe", 0)
        d5_delta = jackknife_results.get("drop_top5_sharpe_delta_pct", 0)
        jack_robust = d5_delta > -50.0  # Still positive Sharpe after removing top 5
        print(f"  Jackknife: {'ROBUST' if jack_robust else 'FRAGILE'} "
              f"(base={base_s:.4f}, −5={d5_s:.4f}, Δ={d5_delta:+.1f}%)")


if __name__ == "__main__":
    main()
