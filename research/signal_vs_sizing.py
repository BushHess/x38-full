#!/usr/bin/env python3
"""Factorial experiment: Signal quality vs Sizing method.

Separates two confounded variables:
  - Signal: entry/exit logic (E0, SM, P, LATCH)
  - Sizing: position sizing method (binary f=1.0, vol-target 15%, vol-target 12%)

Design: 5 signals x 3 sizings = 15 combinations.

For each combination, we run a full backtest on real H4 data with harsh cost (50 bps RT)
and report: CAGR, MDD, Sharpe, Sortino, Calmar, trades, avg_exposure.

Key question:  Do SM/P/LATCH signals produce better Sharpe than E0 signal
               when sizing is held constant?

All tests: harsh cost (50 bps RT), 2019-01-01 to 2026-02-20, warmup=365 days.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

# ── Constants ─────────────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

ANN    = math.sqrt(6.0 * 365.25)  # annualization for H4 bars
BPY    = 6.0 * 365.25             # bars per year H4

# ── Indicator helpers (copied from strategies, frozen) ────────────────────

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _vdo(close, high, low, volume, taker_buy, fast, slow):
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


def _rolling_high_shifted(high: np.ndarray, lookback: int) -> np.ndarray:
    n = len(high)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.max(high[i - lookback:i])
    return out


def _rolling_low_shifted(low: np.ndarray, lookback: int) -> np.ndarray:
    n = len(low)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.min(low[i - lookback:i])
    return out


def _rolling_vol(close: np.ndarray, window: int) -> np.ndarray:
    """Annualized rolling vol from H4 log returns."""
    n = len(close)
    lr = np.diff(np.log(close))
    cum = np.cumsum(np.concatenate([[0.0], lr]))
    cumsq = np.cumsum(np.concatenate([[0.0], lr ** 2]))
    vol = np.full(n, np.nan)
    if n > window:
        idx = np.arange(window, n)
        s = cum[idx] - cum[idx - window]
        sq = cumsq[idx] - cumsq[idx - window]
        var = sq / window - (s / window) ** 2
        np.maximum(var, 0, out=var)
        vol[window:] = np.sqrt(var) * ANN
    return vol


def _compute_hysteretic_regime(ema_fast, ema_slow, slope_ref):
    """LATCH hysteretic regime: ON trigger, OFF trigger, flip OFF."""
    n = len(ema_fast)
    regime_on = np.zeros(n, dtype=np.bool_)
    off_trigger = np.zeros(n, dtype=np.bool_)
    flip_off = np.zeros(n, dtype=np.bool_)
    active = False
    for i in range(n):
        fi, si, ri = ema_fast[i], ema_slow[i], slope_ref[i]
        if not (np.isfinite(fi) and np.isfinite(si) and np.isfinite(ri)):
            regime_on[i] = active
            continue
        on = bool((fi > si) and (si > ri))
        off = bool((fi < si) and (si < ri))
        off_trigger[i] = off
        prev = active
        if (not active) and on:
            active = True
        elif active and off:
            active = False
        regime_on[i] = active
        flip_off[i] = bool(prev and (not active))
    return regime_on, off_trigger, flip_off


# ── Data loading ──────────────────────────────────────────────────────────

def load_arrays():
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
    return cl, hi, lo, vo, tb, wi, n


# ══════════════════════════════════════════════════════════════════════════
# SIGNAL GENERATORS
# Each returns (entry_signal, exit_signal) boolean arrays of length n.
# entry_signal[i] = True means "enter at next bar open"
# exit_signal[i]  = True means "exit at next bar open"
# Only one can be True at a time. No rebalance — pure entry/exit.
# ══════════════════════════════════════════════════════════════════════════

def signal_e0(cl, hi, lo, vo, tb, wi, n):
    """E0: EMA crossover entry + ATR trail & EMA cross-down exit."""
    SLOW, FAST, TRAIL, VDO_T, ATR_P = 120, 30, 3.0, 0.0, 14

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, 12, 28)

    entry = np.zeros(n, dtype=np.bool_)
    exit_ = np.zeros(n, dtype=np.bool_)

    inp = False
    pk = 0.0

    for i in range(n):
        p = cl[i]
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if i >= wi and ef[i] > es[i] and vd[i] > VDO_T:
                entry[i] = True
                inp = True
                pk = p
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                exit_[i] = True
                inp = False
                pk = 0.0
            elif ef[i] < es[i]:
                exit_[i] = True
                inp = False
                pk = 0.0

    return entry, exit_


def signal_e0_regime(cl, hi, lo, vo, tb, wi, n):
    """E0 + EMA(21d) regime filter: entry only when close > EMA(126 H4 bars).

    EMA(126 H4) ≈ EMA(21 D1). Proven p=1.5e-5, 16/16 timescales ALL metrics.
    Same exit logic as E0. Only entry is gated.
    """
    SLOW, FAST, TRAIL, VDO_T, ATR_P = 120, 30, 3.0, 0.0, 14
    EMA_REGIME_PERIOD = 126  # 21 days * 6 bars/day

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, 12, 28)
    ema_regime = _ema(cl, EMA_REGIME_PERIOD)

    entry = np.zeros(n, dtype=np.bool_)
    exit_ = np.zeros(n, dtype=np.bool_)

    inp = False
    pk = 0.0

    for i in range(n):
        p = cl[i]
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if (i >= wi and ef[i] > es[i] and vd[i] > VDO_T
                    and p > ema_regime[i]):
                entry[i] = True
                inp = True
                pk = p
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                exit_[i] = True
                inp = False
                pk = 0.0
            elif ef[i] < es[i]:
                exit_[i] = True
                inp = False
                pk = 0.0

    return entry, exit_


def signal_sm(cl, hi, lo, vo, tb, wi, n):
    """SM: Regime(fast>slow+slope) AND breakout entry + adaptive floor exit."""
    SLOW = 120
    FAST = max(5, SLOW // 4)   # 30
    SLOPE_LB = 6
    ATR_P = 14
    ATR_MULT = 3.0
    ENTRY_N = max(24, SLOW // 2)  # 60
    EXIT_N = max(12, SLOW // 4)   # 30

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    hh = _rolling_high_shifted(hi, ENTRY_N)
    ll = _rolling_low_shifted(lo, EXIT_N)

    # Slope reference
    slope_ref = np.full(n, np.nan, dtype=np.float64)
    if SLOPE_LB < n:
        slope_ref[SLOPE_LB:] = es[:-SLOPE_LB]

    entry = np.zeros(n, dtype=np.bool_)
    exit_ = np.zeros(n, dtype=np.bool_)

    inp = False

    for i in range(n):
        p = cl[i]
        if not (np.isfinite(ef[i]) and np.isfinite(es[i])
                and np.isfinite(slope_ref[i]) and np.isfinite(at[i])
                and np.isfinite(hh[i]) and np.isfinite(ll[i])):
            continue

        regime_ok = (ef[i] > es[i]) and (es[i] > slope_ref[i])

        if not inp:
            if i >= wi and regime_ok and (p > hh[i]):
                entry[i] = True
                inp = True
        else:
            exit_floor = max(ll[i], es[i] - ATR_MULT * at[i])
            if p < exit_floor:
                exit_[i] = True
                inp = False

    return entry, exit_


def signal_p(cl, hi, lo, vo, tb, wi, n):
    """P: Price-first entry (close>ema_slow+slope+breakout) + adaptive floor exit."""
    SLOW = 120
    SLOPE_LB = 6
    ATR_P = 14
    ATR_MULT = 1.5
    ENTRY_N = max(24, SLOW // 2)  # 60
    EXIT_N = max(12, SLOW // 4)   # 30

    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    hh = _rolling_high_shifted(hi, ENTRY_N)
    ll = _rolling_low_shifted(lo, EXIT_N)

    slope_ref = np.full(n, np.nan, dtype=np.float64)
    if SLOPE_LB < n:
        slope_ref[SLOPE_LB:] = es[:-SLOPE_LB]

    entry = np.zeros(n, dtype=np.bool_)
    exit_ = np.zeros(n, dtype=np.bool_)

    inp = False

    for i in range(n):
        p = cl[i]
        if not (np.isfinite(es[i]) and np.isfinite(slope_ref[i])
                and np.isfinite(at[i]) and np.isfinite(hh[i])
                and np.isfinite(ll[i])):
            continue

        if not inp:
            regime_ok = (p > es[i]) and (es[i] > slope_ref[i])
            breakout_ok = p > hh[i]
            if i >= wi and regime_ok and breakout_ok:
                entry[i] = True
                inp = True
        else:
            exit_floor = max(ll[i], es[i] - ATR_MULT * at[i])
            if p < exit_floor:
                exit_[i] = True
                inp = False

    return entry, exit_


def signal_latch(cl, hi, lo, vo, tb, wi, n):
    """LATCH: Hysteretic 3-state machine entry + adaptive floor / regime-flip exit."""
    SLOW = 120
    FAST = 30
    SLOPE_LB = 6
    ATR_P = 14
    ATR_MULT = 2.0
    ENTRY_N = 60
    EXIT_N = 30

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    hh = _rolling_high_shifted(hi, ENTRY_N)
    ll = _rolling_low_shifted(lo, EXIT_N)

    slope_ref = np.full(n, np.nan, dtype=np.float64)
    if SLOPE_LB < n:
        slope_ref[SLOPE_LB:] = es[:-SLOPE_LB]

    regime_on, off_trigger, flip_off = _compute_hysteretic_regime(
        ef, es, slope_ref
    )

    entry = np.zeros(n, dtype=np.bool_)
    exit_ = np.zeros(n, dtype=np.bool_)

    # 3-state machine: OFF=0, ARMED=1, LONG=2
    state = 0

    for i in range(n):
        p = cl[i]
        if not (np.isfinite(es[i]) and np.isfinite(at[i])
                and np.isfinite(hh[i]) and np.isfinite(ll[i])):
            continue

        if state == 0:  # OFF
            if regime_on[i]:
                if p > hh[i] and i >= wi:
                    entry[i] = True
                    state = 2  # LONG
                else:
                    state = 1  # ARMED

        elif state == 1:  # ARMED
            if off_trigger[i]:
                state = 0  # OFF
            elif regime_on[i] and (p > hh[i]) and i >= wi:
                entry[i] = True
                state = 2  # LONG

        elif state == 2:  # LONG
            adaptive_floor = max(ll[i], es[i] - ATR_MULT * at[i])
            if p < adaptive_floor or flip_off[i]:
                exit_[i] = True
                state = 0  # OFF

    return entry, exit_


# ══════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE (signal-agnostic, sizing-agnostic)
# ══════════════════════════════════════════════════════════════════════════

def run_backtest(cl, entry_sig, exit_sig, wi, n,
                 frac=1.0, vol_target=None, rvol=None):
    """Run backtest with given entry/exit signals and sizing method.

    Sizing methods:
      frac: fixed fraction of NAV (frac=1.0 = binary all-in)
      vol_target + rvol: dynamic sizing = min(1.0, vol_target / rvol[i])

    Entry/exit signals are boolean arrays. Entry at signal bar → fill at next bar.
    No rebalance in any mode (pure entry/exit comparison).
    """
    cash = CASH
    bq = 0.0       # btc qty
    inp = False
    pe = False      # pending entry
    px = False      # pending exit
    nt = 0
    entry_f = frac
    entry_bar = -1

    navs = []
    exposure_bars = 0

    for i in range(n):
        p = cl[i]

        # Fill pending orders at this bar's close (= next bar's proxy)
        if i > 0:
            fp = cl[i - 1]  # fill price is previous close
            if pe:
                pe = False
                # Determine sizing
                if vol_target is not None and rvol is not None:
                    rv = rvol[i - 1]  # no lookahead: use signal-time vol
                    if math.isnan(rv) or rv < 1e-8:
                        pass  # skip entry if vol unknown
                    else:
                        entry_f = min(1.0, vol_target / rv)
                else:
                    entry_f = frac

                nav_now = cash
                invest = entry_f * nav_now
                if invest >= 1.0 and nav_now >= 1.0:
                    bq = invest / (fp * (1.0 + CPS))
                    cash -= invest
                    inp = True
                    entry_bar = i

            elif px:
                px = False
                if inp and bq > 0:
                    cash += bq * fp * (1.0 - CPS)
                    bq = 0.0
                    inp = False
                    nt += 1

        # Track NAV (post-warmup)
        if i >= wi:
            nav = cash + bq * p if bq > 0 else cash
            navs.append(nav)
            if inp:
                exposure_bars += 1

        # Generate signals
        if entry_sig[i] and not inp and not pe:
            pe = True
        elif exit_sig[i] and inp and not px:
            px = True

    # Force close at end
    if inp and bq > 0:
        cash += bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1

    navs_arr = np.array(navs, dtype=np.float64)
    return compute_metrics(navs_arr, nt, exposure_bars, len(navs))


def compute_metrics(navs, n_trades, exposure_bars, total_bars):
    """Compute standard metrics from equity curve."""
    if len(navs) < 2 or navs[0] <= 0:
        return {
            "cagr": 0.0, "mdd": 0.0, "sharpe": 0.0, "sortino": 0.0,
            "calmar": 0.0, "trades": 0, "avg_exposure": 0.0,
            "total_return": 0.0,
        }

    # Returns
    rets = np.diff(navs) / navs[:-1]
    n_bars = len(rets)

    # CAGR
    total_ret = navs[-1] / navs[0]
    years = n_bars / BPY
    cagr = (total_ret ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0

    # MDD
    peak = np.maximum.accumulate(navs)
    dd = (peak - navs) / peak
    mdd = float(np.max(dd)) * 100.0

    # Sharpe (population std)
    mu = float(np.mean(rets))
    sigma = float(np.std(rets, ddof=0))
    sharpe = (mu / sigma * ANN) if sigma > 1e-12 else 0.0

    # Sortino
    neg = rets[rets < 0]
    ds = float(np.sqrt(np.mean(neg ** 2))) if len(neg) > 0 else 1e-12
    sortino = (mu / ds * ANN) if ds > 1e-12 else 0.0

    # Calmar
    calmar = (cagr / mdd) if mdd > 0.01 else 0.0

    avg_exp = exposure_bars / total_bars if total_bars > 0 else 0.0

    return {
        "cagr": round(cagr, 2),
        "mdd": round(mdd, 2),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "calmar": round(calmar, 4),
        "trades": n_trades,
        "avg_exposure": round(avg_exp * 100, 1),
        "total_return": round((total_ret - 1) * 100, 2),
    }


# ══════════════════════════════════════════════════════════════════════════
# MAIN: FACTORIAL EXPERIMENT
# ══════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    print("=" * 80)
    print("FACTORIAL EXPERIMENT: Signal Quality vs Sizing Method")
    print("=" * 80)
    print(f"Data: {START} to {END}, warmup={WARMUP}d, cost={COST.per_side_bps*2} bps RT")
    print()

    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"Loaded {n} H4 bars, report starts at index {wi}")

    # Compute rolling vol (shared across all vol-target runs)
    rvol = _rolling_vol(cl, 120)  # same lookback as strategies

    # ── Generate signals ──────────────────────────────────────────────
    print("\nGenerating signals...")
    signals = {
        "E0":      signal_e0(cl, hi, lo, vo, tb, wi, n),
        "E0+R21":  signal_e0_regime(cl, hi, lo, vo, tb, wi, n),
        "SM":      signal_sm(cl, hi, lo, vo, tb, wi, n),
        "P":       signal_p(cl, hi, lo, vo, tb, wi, n),
        "LATCH":   signal_latch(cl, hi, lo, vo, tb, wi, n),
    }

    for name, (ent, ext) in signals.items():
        n_ent = int(np.sum(ent))
        n_ext = int(np.sum(ext))
        print(f"  {name:6s}: {n_ent:4d} entries, {n_ext:4d} exits")

    # ── Sizing methods ────────────────────────────────────────────────
    sizing_methods = [
        ("binary_1.0",    {"frac": 1.0}),
        ("vol_target_15", {"vol_target": 0.15, "rvol": rvol}),
        ("vol_target_12", {"vol_target": 0.12, "rvol": rvol}),
    ]

    # ── Run all 4 x 3 = 12 combinations ──────────────────────────────
    print("\n" + "=" * 80)
    print("RESULTS: 5 signals x 3 sizings = 15 combinations")
    print("=" * 80)

    results = {}

    for sizing_name, sizing_kwargs in sizing_methods:
        print(f"\n{'─' * 80}")
        print(f"SIZING: {sizing_name}")
        print(f"{'─' * 80}")
        print(f"  {'Signal':8s} {'Sharpe':>8s} {'Sortino':>8s} {'CAGR%':>8s} "
              f"{'MDD%':>8s} {'Calmar':>8s} {'Trades':>7s} {'AvgExp%':>8s} "
              f"{'TotRet%':>10s}")
        print(f"  {'-'*8:8s} {'-'*8:>8s} {'-'*8:>8s} {'-'*8:>8s} "
              f"{'-'*8:>8s} {'-'*8:>8s} {'-'*7:>7s} {'-'*8:>8s} "
              f"{'-'*10:>10s}")

        for sig_name, (ent, ext) in signals.items():
            m = run_backtest(cl, ent, ext, wi, n, **sizing_kwargs)
            key = f"{sig_name}_{sizing_name}"
            results[key] = {"signal": sig_name, "sizing": sizing_name, **m}

            print(f"  {sig_name:8s} {m['sharpe']:8.4f} {m['sortino']:8.4f} "
                  f"{m['cagr']:8.2f} {m['mdd']:8.2f} {m['calmar']:8.4f} "
                  f"{m['trades']:7d} {m['avg_exposure']:8.1f} "
                  f"{m['total_return']:10.2f}")

    # ── Cross-comparison tables ───────────────────────────────────────
    print("\n" + "=" * 80)
    print("CROSS-COMPARISON: Sharpe by Signal x Sizing")
    print("=" * 80)
    print(f"  {'Signal':8s}", end="")
    for sn, _ in sizing_methods:
        print(f" {sn:>16s}", end="")
    print()
    print(f"  {'─'*8:8s}", end="")
    for _ in sizing_methods:
        print(f" {'─'*16:>16s}", end="")
    print()
    for sig_name in signals:
        print(f"  {sig_name:8s}", end="")
        for sn, _ in sizing_methods:
            key = f"{sig_name}_{sn}"
            sh = results[key]["sharpe"]
            print(f" {sh:16.4f}", end="")
        print()

    print(f"\n{'=' * 80}")
    print("CROSS-COMPARISON: CAGR% by Signal x Sizing")
    print("=" * 80)
    print(f"  {'Signal':8s}", end="")
    for sn, _ in sizing_methods:
        print(f" {sn:>16s}", end="")
    print()
    for sig_name in signals:
        print(f"  {sig_name:8s}", end="")
        for sn, _ in sizing_methods:
            key = f"{sig_name}_{sn}"
            print(f" {results[key]['cagr']:16.2f}", end="")
        print()

    print(f"\n{'=' * 80}")
    print("CROSS-COMPARISON: MDD% by Signal x Sizing")
    print("=" * 80)
    print(f"  {'Signal':8s}", end="")
    for sn, _ in sizing_methods:
        print(f" {sn:>16s}", end="")
    print()
    for sig_name in signals:
        print(f"  {sig_name:8s}", end="")
        for sn, _ in sizing_methods:
            key = f"{sig_name}_{sn}"
            print(f" {results[key]['mdd']:16.2f}", end="")
        print()

    # ── Sharpe ranking (same sizing) ──────────────────────────────────
    print(f"\n{'=' * 80}")
    print("SIGNAL QUALITY RANKING (holding sizing constant)")
    print("=" * 80)
    for sn, _ in sizing_methods:
        ranked = sorted(
            [(sig, results[f"{sig}_{sn}"]["sharpe"]) for sig in signals],
            key=lambda x: -x[1]
        )
        print(f"\n  {sn}:")
        for rank, (sig, sh) in enumerate(ranked, 1):
            delta = sh - ranked[0][1]
            delta_str = f"  ({delta:+.4f})" if rank > 1 else "  (BEST)"
            print(f"    #{rank}: {sig:8s} Sharpe={sh:.4f}{delta_str}")

    # ── Conclusion ────────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("CONCLUSION")
    print("=" * 80)

    # Check if E0 signal wins on all sizing methods
    e0_wins_all = True
    for sn, _ in sizing_methods:
        e0_sh = results[f"E0_{sn}"]["sharpe"]
        for sig in ["SM", "P", "LATCH"]:
            if results[f"{sig}_{sn}"]["sharpe"] > e0_sh + 0.01:
                e0_wins_all = False

    if e0_wins_all:
        print("  E0 signal has highest Sharpe across ALL sizing methods.")
        print("  SM/P/LATCH Sharpe advantage over E0 was ENTIRELY due to")
        print("  vol-targeted sizing, NOT signal quality.")
    else:
        print("  Signal quality differs across algorithms.")
        print("  The Sharpe difference is NOT purely from sizing.")

    # Check Sharpe invariance within fixed fraction
    print(f"\n  Sharpe spread (binary f=1.0):")
    binary_sharpes = [results[f"{s}_binary_1.0"]["sharpe"] for s in signals]
    print(f"    Range: {min(binary_sharpes):.4f} – {max(binary_sharpes):.4f}")
    print(f"    Spread: {max(binary_sharpes) - min(binary_sharpes):.4f}")

    print(f"\n  Sharpe spread (vol_target_15):")
    vt15_sharpes = [results[f"{s}_vol_target_15"]["sharpe"] for s in signals]
    print(f"    Range: {min(vt15_sharpes):.4f} – {max(vt15_sharpes):.4f}")
    print(f"    Spread: {max(vt15_sharpes) - min(vt15_sharpes):.4f}")

    # ── Save results ──────────────────────────────────────────────────
    outdir = ROOT / "research" / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / "signal_vs_sizing.json"
    with open(outfile, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {outfile}")

    elapsed = time.time() - t0
    print(f"\n  Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
