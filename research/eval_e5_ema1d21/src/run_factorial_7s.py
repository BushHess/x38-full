#!/usr/bin/env python3
"""7-Strategy Factorial: E0, E5, SM, LATCH, E0_plus_EMA1D21, E5_plus_EMA1D21.

Extends run_factorial_6s.py by adding E5_plus_EMA1D21:
  - E0:       EMA crossover + VDO + ATR trail + EMA cross-down exit
  - E5:       same as E0 but uses Robust ATR (capped TR) for trailing stop
  - SM:       instantaneous regime (EMA_f > EMA_s > slope), breakout entry, floor exit
  - LATCH:    hysteretic regime, breakout entry, floor + flip_off exit
  - E0_plus_EMA1D21: E0 + close_d1 > EMA(21, D1) regime filter mapped to H4
  - E5_plus_EMA1D21: E5 + close_d1 > EMA(21, D1) regime filter mapped to H4

Pipeline:
  1. Preflight: validate E0 signal extractor against VTrendStrategy
  2. Extract 6 binary signal arrays
  3. 6x3 factorial matrix (signal x sizing)
  4. 6 native reference runs
  5. Signal concordance matrix (6x6)
  6. Scoring bias audit
  7. Save artifacts (npz, csv, json)

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
_LATCH_PKG = Path("/var/www/trading-bots/Latch/research")

for p in [str(_SRC), str(_REPO), str(_LATCH_PKG)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_align_6s import load_all

# Production imports (read-only)
from v10.core.types import Bar, MarketState
from strategies.vtrend.strategy import VTrendStrategy, VTrendConfig
from strategies.vtrend.strategy import _ema, _atr, _vdo
from strategies.latch.strategy import (
    _compute_hysteretic_regime,
    _rolling_high_shifted, _rolling_low_shifted,
    _realized_vol,
)

# Standalone execution engine (proven equivalent in Step 2)
from Latch.config import CostModel, BARS_PER_YEAR_4H
from Latch.backtest import execute_target_weights

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

EPS = 1e-12
BARS_PER_YEAR = 2190.0
COST_BPS = 25.0  # 25 bps one-way, all runs

STRATEGY_NAMES = ["E0", "E5", "SM", "LATCH", "E0_plus_EMA1D21", "E5_plus_EMA1D21"]


# ═══════════════════════════════════════════════════════════════════════════
# ROBUST ATR (for E5) — from parity_eval.py
# ═══════════════════════════════════════════════════════════════════════════

def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100, period: int = 20) -> np.ndarray:
    """Robust ATR — capped TR + Wilder EMA."""
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
        for i in range(s + period, n):
            if np.isfinite(tr_cap[i]):
                ratr[i] = alpha * tr_cap[i] + (1 - alpha) * ratr[i - 1]
            else:
                ratr[i] = ratr[i - 1]
    return ratr


# ═══════════════════════════════════════════════════════════════════════════
# SHARED INDICATOR COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_indicators(bars: list[Bar], d1_data: dict | None = None,
                       h4_close_times: np.ndarray | None = None) -> dict:
    """Compute shared indicators from bar data."""
    n = len(bars)
    close = np.array([b.close for b in bars], dtype=np.float64)
    high = np.array([b.high for b in bars], dtype=np.float64)
    low = np.array([b.low for b in bars], dtype=np.float64)
    volume = np.array([b.volume for b in bars], dtype=np.float64)
    taker_buy = np.array([b.taker_buy_base_vol for b in bars], dtype=np.float64)

    ema_fast = _ema(close, 30)        # slow_period // 4
    ema_slow = _ema(close, 120)       # slow_period
    atr = _atr(high, low, close, 14)  # Wilder ATR
    vdo = _vdo(close, high, low, volume, taker_buy, 12, 28)

    # Slope reference for SM/LATCH regime
    slope_ref = np.full(n, np.nan, dtype=np.float64)
    slope_ref[6:] = ema_slow[:-6]

    # Rolling high/low (shifted by 1 per function design)
    hh60 = _rolling_high_shifted(high, lookback=60)
    ll30 = _rolling_low_shifted(low, lookback=30)

    # Shared realized vol
    rv = _realized_vol(close, lookback=120, bars_per_year=BARS_PER_YEAR)

    # Robust ATR for E5
    robust_atr = _robust_atr(high, low, close)

    result = dict(
        close=close, high=high, low=low,
        volume=volume, taker_buy=taker_buy,
        ema_fast=ema_fast, ema_slow=ema_slow,
        atr=atr, vdo=vdo, slope_ref=slope_ref,
        hh60=hh60, ll30=ll30, rv=rv,
        robust_atr=robust_atr,
    )

    # D1 regime for E0_plus_EMA1D21 and E5_plus_EMA1D21
    if d1_data is not None and h4_close_times is not None:
        d1_close = d1_data["close"]
        d1_ct = d1_data["close_time"]
        d1_ema = _ema(d1_close, 21)
        d1_regime = d1_close > d1_ema

        # Map D1 regime → H4 bars
        regime_h4_d1 = np.zeros(n, dtype=np.bool_)
        d1_idx = 0
        n_d1 = len(d1_close)
        for i in range(n):
            while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_close_times[i]:
                d1_idx += 1
            if d1_ct[d1_idx] < h4_close_times[i]:
                regime_h4_d1[i] = d1_regime[d1_idx]

        result["d1_regime_h4"] = regime_h4_d1
        result["d1_ema"] = d1_ema
        result["d1_close"] = d1_close

    return result


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL EXTRACTORS (6 strategies)
# ═══════════════════════════════════════════════════════════════════════════

def extract_e0_signal(ind: dict, trail_mult: float = 3.0,
                      vdo_threshold: float = 0.0) -> dict:
    """E0 binary signal: VDO gate + peak-tracking ATR trail + EMA flip exit."""
    n = len(ind["close"])
    close = ind["close"]
    ema_f, ema_s = ind["ema_fast"], ind["ema_slow"]
    atr_arr, vdo_arr = ind["atr"], ind["vdo"]

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)

    is_in = False
    peak = 0.0

    for i in range(n):
        if i < 1 or np.isnan(atr_arr[i]) or np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            in_pos[i] = is_in
            continue

        if not is_in:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > vdo_threshold:
                is_in = True
                peak = close[i]
                entry[i] = True
        else:
            peak = max(peak, close[i])
            ts = peak - trail_mult * atr_arr[i]
            if close[i] < ts:
                is_in = False
                peak = 0.0
                exit_ev[i] = True
            elif ema_f[i] < ema_s[i]:
                is_in = False
                peak = 0.0
                exit_ev[i] = True

        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos)


def extract_e5_signal(ind: dict, trail_mult: float = 3.0,
                      vdo_threshold: float = 0.0) -> dict:
    """E5 binary signal: same as E0 but uses Robust ATR for trail stop."""
    n = len(ind["close"])
    close = ind["close"]
    ema_f, ema_s = ind["ema_fast"], ind["ema_slow"]
    ratr = ind["robust_atr"]
    vdo_arr = ind["vdo"]

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)

    is_in = False
    peak = 0.0

    for i in range(n):
        if i < 1 or np.isnan(ema_f[i]) or np.isnan(ema_s[i]) or np.isnan(ratr[i]):
            in_pos[i] = is_in
            continue

        if not is_in:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > vdo_threshold:
                is_in = True
                peak = close[i]
                entry[i] = True
        else:
            peak = max(peak, close[i])
            ts = peak - trail_mult * ratr[i]
            if close[i] < ts:
                is_in = False
                peak = 0.0
                exit_ev[i] = True
            elif ema_f[i] < ema_s[i]:
                is_in = False
                peak = 0.0
                exit_ev[i] = True

        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos)


def extract_sm_signal(ind: dict, atr_mult: float = 3.0) -> dict:
    """SM binary signal: instantaneous regime, breakout entry, floor exit."""
    n = len(ind["close"])
    close = ind["close"]
    ema_f, ema_s = ind["ema_fast"], ind["ema_slow"]
    slope, atr_arr = ind["slope_ref"], ind["atr"]
    hh60, ll30 = ind["hh60"], ind["ll30"]

    warmup = _find_warmup(n, [ema_f, ema_s, slope, atr_arr, hh60, ll30])

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)
    regime = np.zeros(n, dtype=np.bool_)

    is_in = False
    for i in range(n):
        if np.isfinite(ema_f[i]) and np.isfinite(ema_s[i]) and np.isfinite(slope[i]):
            regime[i] = (ema_f[i] > ema_s[i]) and (ema_s[i] > slope[i])
        if i < warmup:
            continue
        if not is_in:
            if regime[i] and close[i] > hh60[i]:
                is_in = True
                entry[i] = True
        else:
            floor = max(ll30[i], ema_s[i] - atr_mult * atr_arr[i])
            if close[i] < floor:
                is_in = False
                exit_ev[i] = True
        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos, regime=regime)


def extract_latch_signal(ind: dict, atr_mult: float = 2.0) -> dict:
    """LATCH binary signal: hysteretic regime, breakout entry, floor+flip_off exit."""
    n = len(ind["close"])
    close = ind["close"]
    ema_f, ema_s = ind["ema_fast"], ind["ema_slow"]
    slope, atr_arr = ind["slope_ref"], ind["atr"]
    hh60, ll30 = ind["hh60"], ind["ll30"]

    latch_regime, _, latch_flip_off = _compute_hysteretic_regime(ema_f, ema_s, slope)
    warmup = _find_warmup(n, [ema_f, ema_s, slope, atr_arr, hh60, ll30])

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)

    is_in = False
    for i in range(n):
        if i < warmup:
            continue
        if not is_in:
            if latch_regime[i] and close[i] > hh60[i]:
                is_in = True
                entry[i] = True
        else:
            floor = max(ll30[i], ema_s[i] - atr_mult * atr_arr[i])
            if close[i] < floor or latch_flip_off[i]:
                is_in = False
                exit_ev[i] = True
        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos,
                regime=latch_regime, flip_off=latch_flip_off)


def extract_e0_plus_ema1d21_signal(ind: dict, trail_mult: float = 3.0,
                             vdo_threshold: float = 0.0) -> dict:
    """E0_plus_EMA1D21 binary signal: E0 + D1 regime filter (close_d1 > EMA(21, D1))."""
    n = len(ind["close"])
    close = ind["close"]
    ema_f, ema_s = ind["ema_fast"], ind["ema_slow"]
    atr_arr, vdo_arr = ind["atr"], ind["vdo"]
    d1_regime = ind["d1_regime_h4"]

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)

    is_in = False
    peak = 0.0

    for i in range(n):
        if i < 1 or np.isnan(atr_arr[i]) or np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            in_pos[i] = is_in
            continue

        if not is_in:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > vdo_threshold and d1_regime[i]:
                is_in = True
                peak = close[i]
                entry[i] = True
        else:
            peak = max(peak, close[i])
            ts = peak - trail_mult * atr_arr[i]
            if close[i] < ts:
                is_in = False
                peak = 0.0
                exit_ev[i] = True
            elif ema_f[i] < ema_s[i]:
                is_in = False
                peak = 0.0
                exit_ev[i] = True

        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos)


def extract_e5_plus_ema1d21_signal(ind: dict, trail_mult: float = 3.0,
                                    vdo_threshold: float = 0.0) -> dict:
    """E5_plus_EMA1D21 binary signal: E5 (robust ATR trail) + D1 regime filter."""
    n = len(ind["close"])
    close = ind["close"]
    ema_f, ema_s = ind["ema_fast"], ind["ema_slow"]
    ratr = ind["robust_atr"]
    vdo_arr = ind["vdo"]
    d1_regime = ind["d1_regime_h4"]

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)

    is_in = False
    peak = 0.0

    for i in range(n):
        if i < 1 or np.isnan(ema_f[i]) or np.isnan(ema_s[i]) or np.isnan(ratr[i]):
            in_pos[i] = is_in
            continue

        if not is_in:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > vdo_threshold and d1_regime[i]:
                is_in = True
                peak = close[i]
                entry[i] = True
        else:
            peak = max(peak, close[i])
            ts = peak - trail_mult * ratr[i]
            if close[i] < ts:
                is_in = False
                peak = 0.0
                exit_ev[i] = True
            elif ema_f[i] < ema_s[i]:
                is_in = False
                peak = 0.0
                exit_ev[i] = True

        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos)


def _find_warmup(n: int, arrays: list[np.ndarray]) -> int:
    for i in range(n):
        if all(np.isfinite(a[i]) for a in arrays):
            return i
    return n


# ═══════════════════════════════════════════════════════════════════════════
# SIZING OVERLAYS
# ═══════════════════════════════════════════════════════════════════════════

def apply_binary_100(in_pos: np.ndarray) -> np.ndarray:
    return in_pos.astype(np.float64)


def apply_entry_vol_no_rebal(in_pos: np.ndarray, entry: np.ndarray,
                             rv: np.ndarray, target_vol: float) -> np.ndarray:
    n = len(in_pos)
    tw = np.zeros(n, dtype=np.float64)
    current_w = 0.0
    for i in range(n):
        if entry[i]:
            rv_i = rv[i] if np.isfinite(rv[i]) else 1.0
            current_w = min(1.0, target_vol / max(rv_i, EPS))
        if in_pos[i]:
            tw[i] = current_w
        else:
            tw[i] = 0.0
            current_w = 0.0
    return tw


def apply_native_vol_rebal(in_pos: np.ndarray, rv: np.ndarray,
                           target_vol: float,
                           vol_floor: float = 0.0) -> np.ndarray:
    n = len(in_pos)
    tw = np.zeros(n, dtype=np.float64)
    for i in range(n):
        if in_pos[i]:
            rv_i = max(rv[i] if np.isfinite(rv[i]) else 1.0, vol_floor, EPS)
            tw[i] = min(1.0, target_vol / rv_i)
    return tw


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED EXECUTION + METRICS
# ═══════════════════════════════════════════════════════════════════════════

def run_one(df: pd.DataFrame, name: str, tw_signal: np.ndarray,
            entry_arr: np.ndarray, exit_arr: np.ndarray,
            min_rebal_delta: float = 0.0) -> dict:
    """Execute a single run through the standalone engine and compute all metrics."""
    n = len(df)
    dummy_bool = np.zeros(n, dtype=np.bool_)
    dummy_int = np.zeros(n, dtype=np.int8)

    result = execute_target_weights(
        df=df, strategy_name=name,
        state=dummy_int, regime_on=dummy_bool,
        target_weight_signal=tw_signal,
        entry_signal=entry_arr.astype(np.bool_),
        exit_signal=exit_arr.astype(np.bool_),
        regime_on_trigger=dummy_bool, regime_off_trigger=dummy_bool,
        regime_flip_on=dummy_bool, regime_flip_off=dummy_bool,
        costs=CostModel(fee_bps=COST_BPS),
        min_rebalance_weight_delta=min_rebal_delta,
        bars_per_year=BARS_PER_YEAR,
    )

    m = dict(result.metrics)
    m["name"] = name

    # Round-trip PnL
    trades = result.trades
    buys = [t for t in trades if t.side == "BUY"]
    sells = [t for t in trades if t.side == "SELL"]
    n_rt = min(len(buys), len(sells))

    pnls = []
    for j in range(n_rt):
        pnl = sells[j].equity_after - buys[j].equity_before
        pnls.append(pnl)

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    m["profit_factor"] = float(gross_profit / max(gross_loss, EPS)) if n_rt > 0 else 0.0
    m["win_rate"] = float(sum(1 for p in pnls if p > 0) / max(n_rt, 1)) * 100
    m["n_round_trips"] = n_rt

    eq = result.data["equity"].to_numpy(dtype=np.float64)
    aw = result.data["actual_weight"].to_numpy(dtype=np.float64)
    m["time_in_market_pct"] = float(np.mean(aw > 0.01)) * 100

    # Sortino
    rets = np.diff(eq) / np.maximum(eq[:-1], EPS)
    down = rets[rets < 0]
    if len(down) > 0:
        ds = float(np.std(down, ddof=0))
        m["sortino"] = float(np.mean(rets) / max(ds, EPS) * np.sqrt(BARS_PER_YEAR)) if ds > EPS else np.nan
    else:
        m["sortino"] = np.nan

    m["total_cost"] = float(result.data["cost_paid"].sum())
    m["total_turnover"] = float(result.data["turnover_notional"].sum())

    # Scoring formula
    score, terms = compute_score(m)
    m["score"] = score
    m.update(terms)

    m["_eq"] = eq
    m["_aw"] = aw
    return m


def compute_score(m: dict) -> tuple[float, dict]:
    cagr = m.get("cagr", 0.0) * 100
    mdd = m.get("mdd", 0.0) * 100
    sharpe = m.get("sharpe", 0.0) or 0.0
    pf = m.get("profit_factor", 0.0) or 0.0
    n_trades = int(m.get("n_trade_events", 0))

    t_cagr = 2.5 * cagr
    t_mdd = -0.60 * mdd
    t_sharpe = 8.0 * max(0.0, sharpe)
    t_pf = 5.0 * max(0.0, min(pf, 3.0) - 1.0)
    t_trade = min(n_trades / 50.0, 1.0) * 5.0

    score = t_cagr + t_mdd + t_sharpe + t_pf + t_trade
    terms = dict(score_cagr=t_cagr, score_mdd=t_mdd, score_sharpe=t_sharpe,
                 score_pf=t_pf, score_trade=t_trade)
    return score, terms


# ═══════════════════════════════════════════════════════════════════════════
# PREFLIGHT: E0 SIGNAL EXTRACTION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def preflight_e0(df: pd.DataFrame, bars: list[Bar], ind: dict) -> dict | None:
    """Validate extracted E0 signal against native VTrendStrategy."""
    print("\n" + "=" * 70)
    print("PREFLIGHT: E0 Signal Extraction Validation")
    print("=" * 70)
    n = len(bars)

    strat = VTrendStrategy(VTrendConfig())
    strat.on_init(bars, [])

    native_entry = np.zeros(n, dtype=np.bool_)
    native_exit = np.zeros(n, dtype=np.bool_)
    native_in_pos = np.zeros(n, dtype=np.bool_)

    for i in range(n):
        ms = MarketState(
            bar=bars[i], h4_bars=bars, d1_bars=[], bar_index=i, d1_index=-1,
            cash=10000.0, btc_qty=0.0, nav=10000.0, exposure=0.0,
            entry_price_avg=0.0, position_entry_nav=0.0,
        )
        sig = strat.on_bar(ms)
        native_in_pos[i] = strat._in_position
        if sig is not None:
            if sig.target_exposure == 1.0:
                native_entry[i] = True
            elif sig.target_exposure == 0.0:
                native_exit[i] = True

    e0 = extract_e0_signal(ind)
    ip_match = np.array_equal(native_in_pos, e0["in_position"])
    en_match = np.array_equal(native_entry, e0["entry"])
    ex_match = np.array_equal(native_exit, e0["exit"])
    signal_pass = ip_match and en_match and ex_match
    print(f"  Signal parity: in_pos={'MATCH' if ip_match else 'MISMATCH'}, "
          f"entry={'MATCH' if en_match else 'MISMATCH'}, "
          f"exit={'MATCH' if ex_match else 'MISMATCH'}")

    if not signal_pass:
        print("  PREFLIGHT FAILED")
        return None

    tw = native_in_pos.astype(np.float64)
    m = run_one(df, "preflight_e0", tw, native_entry, native_exit)
    print(f"  Sharpe={m['sharpe']:.4f}  CAGR={m['cagr']*100:.2f}%  "
          f"MDD={m['mdd']*100:.2f}%  Trades={int(m['n_trade_events'])}")
    print("  PREFLIGHT: PASS")

    return dict(sharpe=m["sharpe"], cagr=m["cagr"], mdd=m["mdd"],
                trades=int(m["n_trade_events"]), score=m["score"])


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL CONCORDANCE MATRIX
# ═══════════════════════════════════════════════════════════════════════════

def signal_concordance(signals: dict[str, dict]) -> pd.DataFrame:
    """Compute NxN concordance matrix (% bars agreeing on position)."""
    names = list(signals.keys())
    n_names = len(names)
    matrix = np.zeros((n_names, n_names), dtype=np.float64)

    for i, a in enumerate(names):
        for j, b in enumerate(names):
            pos_a = signals[a]["in_position"]
            pos_b = signals[b]["in_position"]
            agree = float(np.sum(pos_a == pos_b)) / max(len(pos_a), 1) * 100
            matrix[i, j] = agree

    return pd.DataFrame(matrix, index=names, columns=names)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("6-Strategy Factorial: E0, E5, SM, LATCH, E0_plus_EMA1D21, E5_plus_EMA1D21")
    print("=" * 70)
    t0 = time.time()

    # ── 1. Load data ──────────────────────────────────────────────────────
    data = load_all()
    df, bars = data["df"], data["bars"]
    n = len(df)
    print(f"Loaded {n} H4 bars, {data['n_d1']} D1 bars")

    # ── 2. Compute indicators ────────────────────────────────────────────
    ind = compute_indicators(bars, data["d1"], data["h4_close_times"])
    print("Indicators computed (including robust ATR, D1 regime)")

    # ── 3. Preflight E0 ──────────────────────────────────────────────────
    pf = preflight_e0(df, bars, ind)
    if pf is None:
        sys.exit(1)

    # ── 4. Extract 6 binary signals ──────────────────────────────────────
    print("\nExtracting signals...")
    signals = {
        "E0":                extract_e0_signal(ind),
        "E5":                extract_e5_signal(ind),
        "SM":                extract_sm_signal(ind),
        "LATCH":             extract_latch_signal(ind),
        "E0_plus_EMA1D21":   extract_e0_plus_ema1d21_signal(ind),
        "E5_plus_EMA1D21":   extract_e5_plus_ema1d21_signal(ind),
    }
    for sname, sig in signals.items():
        ent = int(np.sum(sig["entry"]))
        ext = int(np.sum(sig["exit"]))
        ip_pct = float(np.mean(sig["in_position"])) * 100
        print(f"  {sname:>20}: {ent:>4} entries, {ext:>4} exits, in-pos {ip_pct:.1f}%")

    rv = ind["rv"]

    # ── 5. Signal concordance ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SIGNAL CONCORDANCE MATRIX (% bars agreeing on position)")
    print("=" * 70)
    conc = signal_concordance(signals)
    print(conc.to_string(float_format=lambda x: f"{x:.1f}"))
    conc.to_csv(ARTIFACTS / "concordance_7s.csv")

    # ── 6. 6×3 factorial matrix ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RUNNING 6x3 FACTORIAL MATRIX")
    print("=" * 70)

    sizing_specs = [
        ("Binary_100",  lambda ip, en: apply_binary_100(ip)),
        ("EntryVol_15", lambda ip, en: apply_entry_vol_no_rebal(ip, en, rv, 0.15)),
        ("EntryVol_12", lambda ip, en: apply_entry_vol_no_rebal(ip, en, rv, 0.12)),
    ]

    factorial = {}
    for sname in STRATEGY_NAMES:
        sig = signals[sname]
        ip, en, ex = sig["in_position"], sig["entry"], sig["exit"]
        for sz_name, sz_fn in sizing_specs:
            tw = sz_fn(ip, en)
            run_name = f"{sname}_{sz_name}"
            rebal_delta = 2.0
            print(f"  {run_name}...", end=" ", flush=True)
            m = run_one(df, run_name, tw, en, ex, min_rebal_delta=rebal_delta)
            factorial[run_name] = m
            print(f"CAGR={m['cagr']*100:.2f}% Sharpe={m['sharpe']:.4f} "
                  f"Score={m['score']:.1f}")

    # ── 7. Native reference panel (6 runs) ───────────────────────────────
    print("\n" + "=" * 70)
    print("RUNNING NATIVE REFERENCE PANEL")
    print("=" * 70)

    native_specs = [
        ("E0",                None,  0.0,  2.0),
        ("E5",                None,  0.0,  2.0),
        ("SM",                0.15,  0.0,  0.05),
        ("LATCH",             0.12,  0.08, 0.05),
        ("E0_plus_EMA1D21",   None,  0.0,  2.0),
        ("E5_plus_EMA1D21",   None,  0.0,  2.0),
    ]
    native = {}
    for sname, tv, vf, rebal in native_specs:
        sig = signals[sname]
        ip, en, ex = sig["in_position"], sig["entry"], sig["exit"]
        if tv is None:
            tw = apply_binary_100(ip)
        else:
            tw = apply_native_vol_rebal(ip, rv, tv, vf)
        run_name = f"{sname}_Native"
        print(f"  {run_name}...", end=" ", flush=True)
        m = run_one(df, run_name, tw, en, ex, min_rebal_delta=rebal)
        native[run_name] = m
        print(f"CAGR={m['cagr']*100:.2f}% Sharpe={m['sharpe']:.4f} "
              f"Expo={m['exposure']*100:.1f}% Score={m['score']:.1f}")

    # ── 8. Results tables ────────────────────────────────────────────────
    all_runs = {**factorial, **native}

    print("\n" + "=" * 70)
    print("SIGNAL COMPARISON AT FIXED SIZING (Binary_100)")
    print("=" * 70)
    print(f"  {'Signal':<20} {'CAGR%':>8} {'MDD%':>8} {'Sharpe':>8} "
          f"{'PF':>6} {'Trades':>7} {'Score':>8}")
    print("  " + "-" * 73)
    for sname in STRATEGY_NAMES:
        m = factorial[f"{sname}_Binary_100"]
        print(f"  {sname:<20} {m['cagr']*100:>8.2f} {m['mdd']*100:>8.2f} "
              f"{m['sharpe']:>8.4f} {m['profit_factor']:>6.2f} "
              f"{int(m['n_trade_events']):>7} {m['score']:>8.2f}")

    print(f"\n{'NATIVE REFERENCES':}")
    print(f"  {'Strategy':<20} {'CAGR%':>8} {'MDD%':>8} {'Sharpe':>8} "
          f"{'PF':>6} {'Trades':>7} {'Expo%':>7} {'Score':>8}")
    print("  " + "-" * 83)
    for sname in STRATEGY_NAMES:
        m = native[f"{sname}_Native"]
        print(f"  {sname:<20} {m['cagr']*100:>8.2f} {m['mdd']*100:>8.2f} "
              f"{m['sharpe']:>8.4f} {m['profit_factor']:>6.2f} "
              f"{int(m['n_trade_events']):>7} {m['exposure']*100:>7.1f} "
              f"{m['score']:>8.2f}")

    # ── 9. Pairwise signal comparison at Binary_100 ──────────────────────
    print("\n" + "=" * 70)
    print("PAIRWISE SHARPE DIFFERENCES AT BINARY_100")
    print("=" * 70)
    binary_sharpes = {}
    for sname in STRATEGY_NAMES:
        binary_sharpes[sname] = factorial[f"{sname}_Binary_100"]["sharpe"]
    ref = "E0"
    for sname in STRATEGY_NAMES:
        if sname == ref:
            continue
        delta = binary_sharpes[sname] - binary_sharpes[ref]
        print(f"  {sname} vs {ref}: dSharpe = {delta:+.4f}")

    # ── 10. Save artifacts ───────────────────────────────────────────────
    elapsed = time.time() - t0
    _save_artifacts(factorial, native, pf, signals, ind, elapsed, conc)

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s. Artifacts saved to {ARTIFACTS}/")
    print(f"{'=' * 70}")


def _save_artifacts(factorial, native, pf_result, signals, ind, elapsed, conc):
    all_runs = {**factorial, **native}

    # 1. Factorial summary CSV
    rows = []
    for name, m in all_runs.items():
        row = {k: v for k, v in m.items() if not k.startswith("_")}
        rows.append(row)
    pd.DataFrame(rows).to_csv(ARTIFACTS / "factorial_7s_summary.csv", index=False)

    # 2. Signal comparison at binary
    binary_rows = []
    for sname in STRATEGY_NAMES:
        m = factorial[f"{sname}_Binary_100"]
        binary_rows.append({
            "signal": sname, "cagr_pct": m["cagr"] * 100,
            "mdd_pct": m["mdd"] * 100, "sharpe": m["sharpe"],
            "profit_factor": m["profit_factor"],
            "trades": int(m["n_trade_events"]),
            "exposure_pct": m["exposure"] * 100,
            "score": m["score"],
        })
    pd.DataFrame(binary_rows).to_csv(
        ARTIFACTS / "signal_comparison_7s_binary100.csv", index=False)

    # 3. Equity curves (npz)
    eq_dict = {}
    for name, m in all_runs.items():
        eq_dict[name] = m["_eq"]
    np.savez_compressed(str(ARTIFACTS / "factorial_7s_equity_curves.npz"), **eq_dict)

    # 4. Master results JSON
    def _convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
            return obj
        raise TypeError(f"Not serializable: {type(obj)}")

    master = {}
    for name, m in all_runs.items():
        master[name] = {k: v for k, v in m.items() if not k.startswith("_")}
    master["_preflight"] = pf_result
    master["_concordance"] = conc.to_dict()
    master["_meta"] = {"n_bars": len(ind["close"]), "elapsed_s": round(elapsed, 1),
                       "cost_bps": COST_BPS, "date": "2026-03-06",
                       "strategies": STRATEGY_NAMES}

    with open(ARTIFACTS / "step3_7s_master_results.json", "w") as f:
        json.dump(master, f, indent=2, default=_convert)

    print(f"\n  Saved 4 artifact files to {ARTIFACTS}/")


if __name__ == "__main__":
    main()
