#!/usr/bin/env python3
"""Step 5 — Live sign-off hardening.

Phases:
  B: Deterministic harness validation (baseline regress + 5 probe replays)
  C: Exit delay grid (5 candidates x 4 exit delay levels)
  D: Combined disruptions (entry delay + exit delay + worst-case miss)
  E: Stochastic delay Monte Carlo (5 candidates x 3 LT tiers x 1000 draws)
  F: Sign-off gate evaluation
  G: Artifact writing & figure generation

Extends Step 3 replay harness with exit_delay_bars support.
LATCH is dropped (Step 4: DROP_REDUNDANT). 5 candidates only.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path("/var/www/trading-bots/btc-spot-dev")
BAR_FILE = REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
STEP3_DIR = REPO / "research" / "fragility_audit_20260306" / "artifacts" / "step3"
ARTIFACT_DIR = REPO / "research" / "fragility_audit_20260306" / "artifacts" / "step5"
REPORT_DIR = REPO / "research" / "fragility_audit_20260306" / "reports"

# ---------------------------------------------------------------------------
# Constants (frozen from Steps 0-4)
# ---------------------------------------------------------------------------
NAV0 = 10_000.0
BACKTEST_YEARS = 6.5
FEE_RATE = 0.0015
BUY_ADJ = 1.00100025
SELL_ADJ = 0.99900025
EXPO_THRESHOLD = 0.005

PERIOD_START_MS = 1546300800000
PERIOD_END_MS = 1771545600000
WARMUP_DAYS = 365
BARS_PER_YEAR_4H = 365.0 * 6.0

SEED = 20260306

# Exit delay levels
EXIT_DELAY_BARS = [1, 2, 3, 4]
# Entry delay levels (reused from Step 3)
ENTRY_DELAY_BARS = [1, 2, 3, 4]

# Stochastic delay distributions per latency tier
# Format: {delay_bars: probability}
STOCHASTIC_ENTRY = {
    "LT1": {0: 0.80, 1: 0.15, 2: 0.05},
    "LT2": {0: 0.10, 1: 0.35, 2: 0.30, 3: 0.15, 4: 0.10},
    "LT3": {2: 0.10, 3: 0.20, 4: 0.30, 5: 0.25, 6: 0.15},
}
STOCHASTIC_EXIT = {
    "LT1": {0: 0.85, 1: 0.15},
    "LT2": {0: 0.25, 1: 0.45, 2: 0.20, 3: 0.10},
    "LT3": {1: 0.20, 2: 0.35, 3: 0.25, 4: 0.20},
}

N_STOCHASTIC_DRAWS = 1000

# 5-gate absolute comparative sign-off thresholds.
# Replaces: Step 5 delta-based SIGNOFF_GATES (CONV:UNCALIBRATED T54-T61)
# See: research/x6/X6_VS_X0_RESEARCH_DEPLOYMENT_SPEC.md §4
COMPARATIVE_GATE_THRESHOLDS = {
    "G2_state_dominance_min_ratio": 0.50,   # must win >50% of disruption scenarios
    "G3_fractional_loss_max": 0.35,         # max 35% of baseline Sharpe lost
    "G4_absolute_floor": 0.50,              # minimum absolute Sharpe under worst disruption
    "G5_infra_delta_threshold": -0.20,      # D1+D1 combined delta must exceed this
}

# Combined disruption scenarios
# Each scenario: (label, entry_delay, exit_delay, n_miss)
# Expanded for 5-gate comparative framework (9 deterministic + 3 stochastic = 12 total)
COMBINED_SCENARIOS = [
    ("baseline", 0, 0, 0),
    ("entry_only_D1", 1, 0, 0),
    ("entry_only_D2", 2, 0, 0),
    ("exit_only_D1", 0, 1, 0),
    ("exit_only_D2", 0, 2, 0),
    ("entry_D1_exit_D1", 1, 1, 0),
    ("entry_D1_exit_D2", 1, 2, 0),
    ("entry_D2_exit_D1", 2, 1, 0),
    ("entry_D2_exit_D2", 2, 2, 0),
    ("entry_D4_exit_D2", 4, 2, 0),
    ("full_LT2_sim", 2, 1, 1),  # entry D2 + exit D1 + 1 worst miss (excluded from G2)
]

# Tier-appropriate scenario filters: max (entry_delay, exit_delay) realistic per tier
TIER_MAX_DELAY = {
    "LT1": 2,   # LT1: at most D2 entry, D1 exit
    "LT2": 4,   # LT2: at most D4 entry, D3 exit — all scenarios apply
    "LT3": 99,  # LT3: all scenarios
}

# ---------------------------------------------------------------------------
# Candidate definitions (LATCH dropped per Step 4)
# ---------------------------------------------------------------------------
@dataclass
class CandidateDef:
    label: str
    trade_csv: str
    strategy_type: str
    variant: str
    expected_trade_count: int

CANDIDATES = [
    CandidateDef("E0", "results/parity_20260305/eval_e0_vs_e0/results/trades_candidate.csv",
                 "binary", "E0", 192),
    CandidateDef("E5", "results/parity_20260305/eval_e5_vs_e0/results/trades_candidate.csv",
                 "binary", "E5", 207),
    CandidateDef("SM", "results/parity_20260305/eval_sm_vs_e0/results/trades_candidate.csv",
                 "vol_target", "SM", 65),
    CandidateDef("E0_plus_EMA1D21", "results/parity_20260305/eval_ema21d1_vs_e0/results/trades_candidate.csv",
                 "binary", "E0_plus", 172),
    CandidateDef("E5_plus_EMA1D21", "results/parity_20260306/eval_e5_ema21d1_vs_e0/results/trades_candidate.csv",
                 "binary", "E5_plus", 186),
]

# Baseline metrics from Step 3/4 (for delta computation and MDD reference)
BASELINE_METRICS = {
    "E0": {"sharpe": 1.2653, "cagr": 0.5204, "mdd": 0.4161},
    "E5": {"sharpe": 1.3573, "cagr": 0.5662, "mdd": 0.4037},
    "SM": {"sharpe": 1.4437, "cagr": 0.1600, "mdd": 0.1509},
    "E0_plus_EMA1D21": {"sharpe": 1.3249, "cagr": 0.5470, "mdd": 0.4205},
    "E5_plus_EMA1D21": {"sharpe": 1.4300, "cagr": 0.5985, "mdd": 0.4164},
}

EPS = 1e-12

# ===================================================================
# INDICATOR FUNCTIONS (copied from Step 3 for self-containment)
# ===================================================================

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


def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100,
                period: int = 20) -> np.ndarray:
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


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


def _realized_vol(close: np.ndarray, lookback: int,
                  bars_per_year: float) -> np.ndarray:
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    lr[1:] = np.log(np.divide(
        close[1:], close[:-1],
        out=np.full(n - 1, np.nan, dtype=np.float64),
        where=close[:-1] > 0.0,
    ))
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out


def _compute_hysteretic_regime(ema_fast, ema_slow, slope_ref):
    n = len(ema_fast)
    regime_on = np.zeros(n, dtype=np.bool_)
    off_trigger = np.zeros(n, dtype=np.bool_)
    flip_off = np.zeros(n, dtype=np.bool_)
    active = False
    for i in range(n):
        fi = ema_fast[i]
        si = ema_slow[i]
        ri = slope_ref[i]
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


def _clip_weight_sm(weight: float, min_weight: float = 0.0) -> float:
    if not np.isfinite(weight):
        return 0.0
    w = min(1.0, max(0.0, float(weight)))
    if w < min_weight:
        return 0.0
    return w


# ===================================================================
# DATA LOADING
# ===================================================================

@dataclass
class BarData:
    open_time: np.ndarray
    close_time: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    taker_buy: np.ndarray


def load_bars():
    import pandas as pd
    df = pd.read_csv(BAR_FILE)
    h4 = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
    d1 = df[df["interval"] == "1d"].sort_values("open_time").reset_index(drop=True)
    warmup_start_ms = PERIOD_START_MS - WARMUP_DAYS * 86_400_000
    h4 = h4[h4["close_time"] >= warmup_start_ms].reset_index(drop=True)
    d1 = d1[d1["close_time"] >= warmup_start_ms].reset_index(drop=True)
    report_start_idx = int(np.searchsorted(h4["close_time"].values, PERIOD_START_MS))
    h4_data = BarData(
        open_time=h4["open_time"].values.astype(np.int64),
        close_time=h4["close_time"].values.astype(np.int64),
        open=h4["open"].values.astype(np.float64),
        high=h4["high"].values.astype(np.float64),
        low=h4["low"].values.astype(np.float64),
        close=h4["close"].values.astype(np.float64),
        volume=h4["volume"].values.astype(np.float64),
        taker_buy=h4["taker_buy_base_vol"].values.astype(np.float64),
    )
    d1_data = BarData(
        open_time=d1["open_time"].values.astype(np.int64),
        close_time=d1["close_time"].values.astype(np.int64),
        open=d1["open"].values.astype(np.float64),
        high=d1["high"].values.astype(np.float64),
        low=d1["low"].values.astype(np.float64),
        close=d1["close"].values.astype(np.float64),
        volume=d1["volume"].values.astype(np.float64),
        taker_buy=d1["taker_buy_base_vol"].values.astype(np.float64),
    )
    return h4_data, d1_data, report_start_idx


def load_canonical_trades(csv_path: str) -> list[dict]:
    path = REPO / csv_path
    trades = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append({
                "entry_ts_ms": int(row["entry_ts_ms"]),
                "exit_ts_ms": int(row["exit_ts_ms"]),
                "return_pct": float(row["return_pct"]),
                "pnl_usd": float(row["pnl_usd"]),
                "entry_price": float(row["entry_price"]),
                "exit_price": float(row["exit_price"]),
                "qty": float(row["qty"]),
                "entry_reason": row["entry_reason"],
                "exit_reason": row["exit_reason"],
            })
    return trades


# ===================================================================
# PRECOMPUTED INDICATORS (from Step 3)
# ===================================================================

@dataclass
class BinaryIndicators:
    ema_fast: np.ndarray
    ema_slow: np.ndarray
    trail_atr: np.ndarray
    vdo: np.ndarray
    d1_regime_ok: np.ndarray | None
    report_start_idx: int


@dataclass
class SMIndicators:
    ema_fast: np.ndarray
    ema_slow: np.ndarray
    ema_slow_slope_ref: np.ndarray
    atr_arr: np.ndarray
    hh_entry: np.ndarray
    ll_exit: np.ndarray
    rv: np.ndarray
    warmup_end: int
    report_start_idx: int
    target_vol: float
    min_weight: float
    min_rebalance_weight_delta: float
    atr_mult: float


def compute_d1_regime(h4_ct: np.ndarray, d1_data: BarData, d1_ema_period: int) -> np.ndarray:
    n_h4 = len(h4_ct)
    regime_ok = np.zeros(n_h4, dtype=np.bool_)
    if len(d1_data.close) == 0:
        return regime_ok
    d1_ema = _ema(d1_data.close, d1_ema_period)
    d1_regime = d1_data.close > d1_ema
    d1_ct = d1_data.close_time
    n_d1 = len(d1_ct)
    d1_idx = 0
    for i in range(n_h4):
        h4_ct_i = h4_ct[i]
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct_i:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct_i:
            regime_ok[i] = d1_regime[d1_idx]
    return regime_ok


def precompute_indicators(variant: str, h4: BarData, d1: BarData,
                          report_start_idx: int):
    close = h4.close
    high = h4.high
    low = h4.low

    if variant in ("E0", "E5", "E0_plus", "E5_plus"):
        slow_p = 120
        fast_p = max(5, slow_p // 4)
        ema_fast = _ema(close, fast_p)
        ema_slow = _ema(close, slow_p)
        vdo = _vdo(close, high, low, h4.volume, h4.taker_buy, 12, 28)
        if variant in ("E0", "E0_plus"):
            trail_atr = _atr(high, low, close, 14)
        else:
            trail_atr = _robust_atr(high, low, close, 0.90, 100, 20)
        d1_regime = None
        if variant in ("E0_plus", "E5_plus"):
            d1_regime = compute_d1_regime(h4.close_time, d1, 21)
        return BinaryIndicators(
            ema_fast=ema_fast, ema_slow=ema_slow,
            trail_atr=trail_atr, vdo=vdo,
            d1_regime_ok=d1_regime,
            report_start_idx=report_start_idx,
        )

    elif variant == "SM":
        slow_p = 120
        fast_p = max(5, slow_p // 4)
        entry_n = max(24, slow_p // 2)
        exit_n = max(12, slow_p // 4)
        vol_lookback = slow_p
        slope_lookback = 6
        ema_fast = _ema(close, fast_p)
        ema_slow = _ema(close, slow_p)
        n = len(close)
        slope_ref = np.full(n, np.nan, dtype=np.float64)
        if slope_lookback < n:
            slope_ref[slope_lookback:] = ema_slow[:-slope_lookback]
        atr_arr = _atr(high, low, close, 14)
        hh_entry = _rolling_high_shifted(high, entry_n)
        ll_exit = _rolling_low_shifted(low, exit_n)
        rv = _realized_vol(close, vol_lookback, BARS_PER_YEAR_4H)
        arrays = [ema_fast, ema_slow, slope_ref, atr_arr, hh_entry, ll_exit, rv]
        warmup_end = n
        for i in range(n):
            if all(np.isfinite(a[i]) for a in arrays):
                warmup_end = i
                break
        return SMIndicators(
            ema_fast=ema_fast, ema_slow=ema_slow,
            ema_slow_slope_ref=slope_ref, atr_arr=atr_arr,
            hh_entry=hh_entry, ll_exit=ll_exit, rv=rv,
            warmup_end=warmup_end, report_start_idx=report_start_idx,
            target_vol=0.15, min_weight=0.0,
            min_rebalance_weight_delta=0.05, atr_mult=3.0,
        )
    else:
        raise ValueError(f"Unknown variant: {variant}")


# ===================================================================
# REPLAY SIMULATORS — EXTENDED WITH EXIT DELAY
# ===================================================================

@dataclass
class Trade:
    entry_bar_idx: int
    entry_fill_bar_idx: int
    entry_fill_price: float
    exit_bar_idx: int
    exit_fill_bar_idx: int
    exit_fill_price: float
    qty: float
    return_pct: float
    pnl_usd: float
    entry_ts_ms: int
    exit_ts_ms: int


@dataclass
class ReplayResult:
    trades: list[Trade]
    native_terminal: float
    unit_terminal: float
    sharpe: float
    cagr_native: float
    cagr_unit: float
    mdd_native: float = 0.0
    suppressed_entries: int = 0


def compute_metrics(trades: list[Trade]) -> dict:
    if not trades:
        return {
            "n_trades": 0, "native_terminal": NAV0, "unit_terminal": NAV0,
            "sharpe": 0.0, "cagr_native": 0.0, "cagr_unit": 0.0, "mdd_native": 0.0,
        }
    returns = np.array([t.return_pct for t in trades])
    pnls = np.array([t.pnl_usd for t in trades])
    n = len(trades)

    # Native terminal & MDD
    cum_pnl = np.cumsum(pnls)
    nav_curve = NAV0 + cum_pnl
    native_terminal = float(nav_curve[-1])
    running_max = np.maximum.accumulate(nav_curve)
    dd = (running_max - nav_curve) / running_max
    mdd_native = float(np.max(dd)) if len(dd) > 0 else 0.0

    unit_terminal = NAV0 * np.prod(1 + returns / 100.0)
    trades_per_year = n / BACKTEST_YEARS
    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=0)
    sharpe = (mean_r / std_r * math.sqrt(trades_per_year)) if std_r > 0 else 0.0
    cagr_native = (native_terminal / NAV0) ** (1 / BACKTEST_YEARS) - 1 if native_terminal > 0 else -1.0
    cagr_unit = (unit_terminal / NAV0) ** (1 / BACKTEST_YEARS) - 1 if unit_terminal > 0 else -1.0

    return {
        "n_trades": n,
        "native_terminal": native_terminal,
        "unit_terminal": unit_terminal,
        "sharpe": sharpe,
        "cagr_native": cagr_native,
        "cagr_unit": cagr_unit,
        "mdd_native": mdd_native,
    }


def replay_binary(ind: BinaryIndicators, h4: BarData,
                   skip_entries: set[int] | None = None,
                   blackout_start_ms: int = 0, blackout_end_ms: int = 0,
                   entry_delay_bars: int = 0,
                   exit_delay_bars: int = 0) -> ReplayResult:
    """Replay binary strategy with entry AND exit delay support.

    Exit delay semantics (per spec Section 8.3.3):
    - When exit signal fires, defer execution by exit_delay_bars extra bars
    - Position remains open during delay (tracking peak/trail)
    - No new entry may open while position open
    - If new entry signal arrives before delayed exit executes: suppressed
    """
    n = len(h4.close)
    rsi = ind.report_start_idx
    trail_mult = 3.0
    vdo_threshold = 0.0

    in_position = False
    peak_price = 0.0
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    pending_entry = False
    pending_exit = False

    # Entry delay state
    pending_entry_delay_countdown = 0

    # Exit delay state
    exit_delay_countdown = 0
    exit_decided = False  # True when exit signal fired but delayed

    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0

    suppressed_entries = 0
    trades: list[Trade] = []

    if skip_entries is None:
        skip_entries = set()

    for i in range(n):
        close_val = h4.close[i]
        open_val = h4.open[i]
        close_time_ms = int(h4.close_time[i])

        # --- Fill pending signals at this bar's OPEN ---
        if pending_entry and i > 0:
            fill_px = open_val * BUY_ADJ
            fee_rate = FEE_RATE
            total_cost_per_unit = fill_px * (1 + fee_rate)
            qty = cash / total_cost_per_unit
            if qty > 0:
                fee = qty * fill_px * fee_rate
                cash -= qty * fill_px + fee
                btc_qty = qty
                entry_avg = fill_px
                entry_fill_bar_idx = i
                entry_fill_price = fill_px
            pending_entry = False

        if pending_exit and i > 0:
            fill_px = open_val * SELL_ADJ
            fee = btc_qty * fill_px * FEE_RATE
            rpnl = btc_qty * (fill_px - entry_avg) - fee
            ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
            cash += btc_qty * fill_px - fee
            trades.append(Trade(
                entry_bar_idx=entry_bar_idx,
                entry_fill_bar_idx=entry_fill_bar_idx,
                entry_fill_price=entry_fill_price,
                exit_bar_idx=i - 1,
                exit_fill_bar_idx=i,
                exit_fill_price=fill_px,
                qty=btc_qty,
                return_pct=ret_pct,
                pnl_usd=rpnl,
                entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
                exit_ts_ms=int(h4.open_time[i]),
            ))
            btc_qty = 0.0
            entry_avg = 0.0
            pending_exit = False
            exit_decided = False

        # --- Exit delay countdown ---
        if exit_delay_countdown > 0:
            exit_delay_countdown -= 1
            if exit_delay_countdown == 0:
                # Delayed exit fires now
                in_position = False
                peak_price = 0.0
                pending_exit = True
            # Position stays open during delay — keep tracking peak
            if in_position:
                peak_price = max(peak_price, close_val)

        # --- Entry delay countdown ---
        if pending_entry_delay_countdown > 0:
            pending_entry_delay_countdown -= 1
            if pending_entry_delay_countdown == 0:
                if not in_position and not exit_decided:
                    in_position = True
                    peak_price = close_val
                    entry_bar_idx = i
                    pending_entry = True
                else:
                    suppressed_entries += 1

        if i < rsi:
            continue

        ema_f = ind.ema_fast[i]
        ema_s = ind.ema_slow[i]
        trail_val = ind.trail_atr[i]
        vdo_val = ind.vdo[i]

        if math.isnan(trail_val) or math.isnan(ema_f) or math.isnan(ema_s):
            continue

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not in_position and not exit_decided:
            regime_ok = True
            if ind.d1_regime_ok is not None:
                regime_ok = bool(ind.d1_regime_ok[i])

            if trend_up and vdo_val > vdo_threshold and regime_ok:
                should_skip = False
                if i in skip_entries:
                    should_skip = True
                if blackout_start_ms > 0 and blackout_start_ms <= close_time_ms <= blackout_end_ms:
                    should_skip = True

                if entry_delay_bars > 0 and not should_skip:
                    pending_entry_delay_countdown = entry_delay_bars
                    continue
                if should_skip:
                    continue

                in_position = True
                peak_price = close_val
                entry_bar_idx = i
                pending_entry = True

        elif in_position and not exit_decided:
            peak_price = max(peak_price, close_val)
            trail_stop = peak_price - trail_mult * trail_val
            exit_signal = False

            if close_val < trail_stop:
                exit_signal = True
            elif trend_down:
                exit_signal = True

            if exit_signal:
                if exit_delay_bars > 0:
                    exit_decided = True
                    exit_delay_countdown = exit_delay_bars
                else:
                    in_position = False
                    peak_price = 0.0
                    pending_exit = True

    # Close any open position at last bar
    if btc_qty > 0:
        fill_px = h4.close[-1] * SELL_ADJ
        fee = btc_qty * fill_px * FEE_RATE
        rpnl = btc_qty * (fill_px - entry_avg) - fee
        ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
        cash += btc_qty * fill_px - fee
        trades.append(Trade(
            entry_bar_idx=entry_bar_idx,
            entry_fill_bar_idx=entry_fill_bar_idx,
            entry_fill_price=entry_fill_price,
            exit_bar_idx=len(h4.close) - 1,
            exit_fill_bar_idx=len(h4.close) - 1,
            exit_fill_price=fill_px,
            qty=btc_qty,
            return_pct=ret_pct,
            pnl_usd=rpnl,
            entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
            exit_ts_ms=int(h4.open_time[-1]),
        ))

    m = compute_metrics(trades)
    return ReplayResult(
        trades=trades,
        native_terminal=m["native_terminal"],
        unit_terminal=m["unit_terminal"],
        sharpe=m["sharpe"],
        cagr_native=m["cagr_native"],
        cagr_unit=m["cagr_unit"],
        mdd_native=m["mdd_native"],
        suppressed_entries=suppressed_entries,
    )


def replay_sm(ind: SMIndicators, h4: BarData,
              skip_entries: set[int] | None = None,
              blackout_start_ms: int = 0, blackout_end_ms: int = 0,
              entry_delay_bars: int = 0,
              exit_delay_bars: int = 0) -> ReplayResult:
    """Replay SM with entry AND exit delay support."""
    n = len(h4.close)
    rsi = ind.report_start_idx

    active = False
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    current_exposure = 0.0
    cum_rpnl = 0.0

    pending_signal = None
    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0
    pending_entry_delay_countdown = 0

    # Exit delay state
    exit_delay_countdown = 0
    exit_decided = False

    suppressed_entries = 0
    trades: list[Trade] = []

    if skip_entries is None:
        skip_entries = set()

    for i in range(n):
        close_val = h4.close[i]
        open_val = h4.open[i]
        close_time_ms = int(h4.close_time[i])
        mid = open_val

        # --- Fill pending signal ---
        if pending_signal is not None and i > 0:
            target_expo, reason = pending_signal
            pending_signal = None

            nav = cash + btc_qty * mid
            if nav <= 0:
                nav = 1.0

            current_exposure = (btc_qty * mid / nav) if (nav > 0 and btc_qty > 0) else 0.0

            if target_expo < EXPO_THRESHOLD and btc_qty > 0:
                fill_px = mid * SELL_ADJ
                fee = btc_qty * fill_px * FEE_RATE
                final_rpnl = btc_qty * (fill_px - entry_avg) - fee
                total_pnl = cum_rpnl + final_rpnl
                ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
                cash += btc_qty * fill_px - fee
                trades.append(Trade(
                    entry_bar_idx=entry_bar_idx,
                    entry_fill_bar_idx=entry_fill_bar_idx,
                    entry_fill_price=entry_fill_price,
                    exit_bar_idx=i - 1,
                    exit_fill_bar_idx=i,
                    exit_fill_price=fill_px,
                    qty=btc_qty,
                    return_pct=ret_pct,
                    pnl_usd=total_pnl,
                    entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
                    exit_ts_ms=int(h4.open_time[i]),
                ))
                btc_qty = 0.0
                entry_avg = 0.0
                current_exposure = 0.0
                cum_rpnl = 0.0
                exit_decided = False
            else:
                delta = target_expo - current_exposure
                if delta > EXPO_THRESHOLD:
                    buy_value = delta * nav
                    fill_px = mid * BUY_ADJ
                    qty_buy = buy_value / mid
                    total_cost = qty_buy * fill_px * (1 + FEE_RATE)
                    if total_cost > cash:
                        qty_buy = cash / (fill_px * (1 + FEE_RATE))
                    fee = qty_buy * fill_px * FEE_RATE
                    if btc_qty == 0:
                        entry_fill_bar_idx = i
                        entry_fill_price = fill_px
                        entry_avg = fill_px
                        cum_rpnl = 0.0
                    else:
                        entry_avg = (entry_avg * btc_qty + fill_px * qty_buy) / (btc_qty + qty_buy)
                    cash -= qty_buy * fill_px + fee
                    btc_qty += qty_buy
                elif delta < -EXPO_THRESHOLD:
                    sell_value = abs(delta) * nav
                    fill_px = mid * SELL_ADJ
                    qty_sell = min(sell_value / mid, btc_qty)
                    fee = qty_sell * fill_px * FEE_RATE
                    cum_rpnl += qty_sell * (fill_px - entry_avg) - fee
                    cash += qty_sell * fill_px - fee
                    btc_qty -= qty_sell

                nav_after = cash + btc_qty * mid
                current_exposure = (btc_qty * mid / nav_after) if nav_after > 0 else 0.0

        # --- Exit delay countdown ---
        if exit_delay_countdown > 0:
            exit_delay_countdown -= 1
            if exit_delay_countdown == 0:
                active = False
                pending_signal = (0.0, "vtrend_sm_delayed_exit")

        # --- Entry delay countdown ---
        if pending_entry_delay_countdown > 0:
            pending_entry_delay_countdown -= 1
            if pending_entry_delay_countdown == 0 and not active and not exit_decided:
                rv_val = ind.rv[i]
                if np.isfinite(rv_val):
                    weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                    if weight > 0.0:
                        active = True
                        entry_bar_idx = i
                        pending_signal = (weight, "vtrend_sm_entry")
                    # else: delay expired but weight zero — no entry
            elif active or exit_decided:
                suppressed_entries += 1

        if i < max(ind.warmup_end, rsi):
            continue

        ema_f = ind.ema_fast[i]
        ema_s = ind.ema_slow[i]
        ema_s_ref = ind.ema_slow_slope_ref[i]
        atr_val = ind.atr_arr[i]
        hh = ind.hh_entry[i]
        ll = ind.ll_exit[i]
        rv_val = ind.rv[i]

        if not (np.isfinite(ema_f) and np.isfinite(ema_s)
                and np.isfinite(ema_s_ref) and np.isfinite(atr_val)
                and np.isfinite(hh) and np.isfinite(ll) and np.isfinite(rv_val)):
            continue

        regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)

        if not active and not exit_decided:
            breakout_ok = close_val > hh
            if regime_ok and breakout_ok:
                should_skip = i in skip_entries
                if blackout_start_ms > 0 and blackout_start_ms <= close_time_ms <= blackout_end_ms:
                    should_skip = True
                if entry_delay_bars > 0 and not should_skip:
                    pending_entry_delay_countdown = entry_delay_bars
                    continue
                if should_skip:
                    continue
                weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                if weight > 0.0:
                    active = True
                    entry_bar_idx = i
                    pending_signal = (weight, "vtrend_sm_entry")
        elif active and not exit_decided:
            exit_floor = max(ll, ema_s - ind.atr_mult * atr_val)
            floor_break = close_val < exit_floor

            if floor_break:
                if exit_delay_bars > 0:
                    exit_decided = True
                    exit_delay_countdown = exit_delay_bars
                else:
                    active = False
                    pending_signal = (0.0, "vtrend_sm_floor_exit")
            else:
                new_weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                nav_now = cash + btc_qty * close_val
                expo_now = (btc_qty * close_val / nav_now) if nav_now > 0 else 0.0
                delta = abs(new_weight - expo_now)
                if delta >= ind.min_rebalance_weight_delta - 1e-12:
                    if not exit_decided:
                        pending_signal = (new_weight, "vtrend_sm_rebalance")

    # Close open position
    if btc_qty > 0:
        fill_px = h4.close[-1] * SELL_ADJ
        fee = btc_qty * fill_px * FEE_RATE
        final_rpnl = btc_qty * (fill_px - entry_avg) - fee
        total_pnl = cum_rpnl + final_rpnl
        ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
        cash += btc_qty * fill_px - fee
        trades.append(Trade(
            entry_bar_idx=entry_bar_idx,
            entry_fill_bar_idx=entry_fill_bar_idx,
            entry_fill_price=entry_fill_price,
            exit_bar_idx=len(h4.close) - 1,
            exit_fill_bar_idx=len(h4.close) - 1,
            exit_fill_price=fill_px,
            qty=btc_qty,
            return_pct=ret_pct,
            pnl_usd=total_pnl,
            entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
            exit_ts_ms=int(h4.open_time[-1]),
        ))

    m = compute_metrics(trades)
    return ReplayResult(
        trades=trades,
        native_terminal=m["native_terminal"],
        unit_terminal=m["unit_terminal"],
        sharpe=m["sharpe"],
        cagr_native=m["cagr_native"],
        cagr_unit=m["cagr_unit"],
        mdd_native=m["mdd_native"],
        suppressed_entries=suppressed_entries,
    )


def run_replay(cand: CandidateDef, indicators, h4: BarData, **kwargs) -> ReplayResult:
    if cand.variant in ("E0", "E5", "E0_plus", "E5_plus"):
        return replay_binary(indicators, h4, **kwargs)
    elif cand.variant == "SM":
        return replay_sm(indicators, h4, **kwargs)
    else:
        raise ValueError(f"Unknown variant: {cand.variant}")


# ===================================================================
# PHASE B: HARNESS VALIDATION
# ===================================================================

def phase_b_validation(cand: CandidateDef, indicators, h4: BarData,
                       canonical_trades: list[dict]) -> dict:
    """Validate replay harness: baseline + 5 probe replays."""
    # Baseline regression
    baseline = run_replay(cand, indicators, h4)
    is_vol_target = cand.strategy_type == "vol_target"
    checks = {}
    n_replay = len(baseline.trades)
    n_canonical = len(canonical_trades)
    checks["trade_count"] = n_replay == n_canonical
    checks["trade_count_detail"] = f"{n_replay} vs {n_canonical}"

    ts_match = True
    for j, (rt, ct) in enumerate(zip(baseline.trades, canonical_trades)):
        entry_ok = rt.entry_ts_ms == ct["entry_ts_ms"]
        exit_ok = rt.exit_ts_ms == ct["exit_ts_ms"]
        if not (entry_ok and exit_ok):
            ts_match = False
            break
    checks["entry_exit_timestamps"] = ts_match

    canon_native = NAV0 + sum(t["pnl_usd"] for t in canonical_trades)
    native_diff = abs(baseline.native_terminal - canon_native)
    checks["native_terminal_match"] = native_diff < 1.0
    checks["native_terminal_detail"] = f"replay={baseline.native_terminal:.2f} canonical={canon_native:.2f}"

    binding_keys = {"trade_count", "entry_exit_timestamps", "native_terminal_match"}
    all_pass = all(checks.get(k, False) for k in binding_keys)
    checks["all_pass"] = all_pass

    # 5 probe replays to verify exit_delay_bars=0 matches baseline
    probe_results = {}
    for d in [0, 1, 2]:
        r = run_replay(cand, indicators, h4, exit_delay_bars=d)
        probe_results[f"exit_delay_{d}"] = {
            "n_trades": len(r.trades),
            "sharpe": r.sharpe,
            "native_terminal": r.native_terminal,
        }
    # Verify exit_delay=0 matches baseline exactly
    probe_d0 = probe_results["exit_delay_0"]
    checks["exit_delay_0_matches_baseline"] = (
        probe_d0["n_trades"] == n_replay
        and abs(probe_d0["native_terminal"] - baseline.native_terminal) < 0.01
    )

    return {
        "regression": checks,
        "probe_results": probe_results,
        "baseline": baseline,
    }


# ===================================================================
# PHASE C: EXIT DELAY GRID
# ===================================================================

def phase_c_exit_delay(cand: CandidateDef, indicators, h4: BarData,
                       baseline: ReplayResult) -> dict:
    """Run exit-delay replay for {1,2,3,4} bars."""
    results = {}
    for D in EXIT_DELAY_BARS:
        r = run_replay(cand, indicators, h4, exit_delay_bars=D)
        results[D] = {
            "n_trades": len(r.trades),
            "native_terminal": r.native_terminal,
            "unit_terminal": r.unit_terminal,
            "sharpe": r.sharpe,
            "cagr_native": r.cagr_native,
            "mdd_native": r.mdd_native,
            "delta_sharpe": r.sharpe - baseline.sharpe,
            "delta_cagr_native": r.cagr_native - baseline.cagr_native,
            "delta_mdd_native": r.mdd_native - baseline.mdd_native,
            "delta_n_trades": len(r.trades) - len(baseline.trades),
            "suppressed_entries": r.suppressed_entries,
            "baseline_sharpe": baseline.sharpe,
            "baseline_cagr_native": baseline.cagr_native,
        }
    return results


# ===================================================================
# PHASE D: COMBINED DISRUPTIONS
# ===================================================================

def phase_d_combined(cand: CandidateDef, indicators, h4: BarData,
                     baseline: ReplayResult,
                     entry_indices: list[int]) -> dict:
    """Run combined disruption scenarios."""
    results = {}
    rng = np.random.RandomState(SEED + hash(cand.label) % 10000)

    for scenario_name, ed, xd, n_miss in COMBINED_SCENARIOS:
        skip_set = set()
        if n_miss > 0 and len(entry_indices) > 0:
            # Use worst-case miss: skip the single most impactful entry
            # We identify this by checking which entry, when missed, causes worst Sharpe
            # For efficiency, use random selection from Step 3 worst-case seed
            chosen = rng.choice(len(entry_indices), size=min(n_miss, len(entry_indices)), replace=False)
            skip_set = set(entry_indices[c] for c in chosen)

        r = run_replay(cand, indicators, h4,
                       entry_delay_bars=ed, exit_delay_bars=xd,
                       skip_entries=skip_set)
        results[scenario_name] = {
            "entry_delay": ed,
            "exit_delay": xd,
            "n_miss": n_miss,
            "n_trades": len(r.trades),
            "native_terminal": r.native_terminal,
            "sharpe": r.sharpe,
            "cagr_native": r.cagr_native,
            "mdd_native": r.mdd_native,
            "delta_sharpe": r.sharpe - baseline.sharpe,
            "delta_cagr_native": r.cagr_native - baseline.cagr_native,
            "delta_mdd_native": r.mdd_native - baseline.mdd_native,
            "suppressed_entries": r.suppressed_entries,
        }

    return results


# ===================================================================
# PHASE E: STOCHASTIC DELAY MC
# ===================================================================

def _draw_delay(dist: dict[int, float], rng: np.random.RandomState) -> int:
    """Draw a single delay value from a discrete distribution."""
    vals = list(dist.keys())
    probs = [dist[v] for v in vals]
    return int(rng.choice(vals, p=probs))


def replay_binary_stochastic(ind: BinaryIndicators, h4: BarData,
                              entry_dist: dict[int, float],
                              exit_dist: dict[int, float],
                              rng: np.random.RandomState) -> ReplayResult:
    """Replay binary strategy with per-event stochastic delays."""
    n = len(h4.close)
    rsi = ind.report_start_idx
    trail_mult = 3.0
    vdo_threshold = 0.0

    in_position = False
    peak_price = 0.0
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    pending_entry = False
    pending_exit = False
    pending_entry_delay_countdown = 0
    exit_delay_countdown = 0
    exit_decided = False
    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0
    suppressed_entries = 0
    trades: list[Trade] = []

    for i in range(n):
        close_val = h4.close[i]
        open_val = h4.open[i]

        if pending_entry and i > 0:
            fill_px = open_val * BUY_ADJ
            fee_rate = FEE_RATE
            qty = cash / (fill_px * (1 + fee_rate))
            if qty > 0:
                fee = qty * fill_px * fee_rate
                cash -= qty * fill_px + fee
                btc_qty = qty
                entry_avg = fill_px
                entry_fill_bar_idx = i
                entry_fill_price = fill_px
            pending_entry = False

        if pending_exit and i > 0:
            fill_px = open_val * SELL_ADJ
            fee = btc_qty * fill_px * FEE_RATE
            rpnl = btc_qty * (fill_px - entry_avg) - fee
            ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
            cash += btc_qty * fill_px - fee
            trades.append(Trade(
                entry_bar_idx=entry_bar_idx,
                entry_fill_bar_idx=entry_fill_bar_idx,
                entry_fill_price=entry_fill_price,
                exit_bar_idx=i - 1, exit_fill_bar_idx=i,
                exit_fill_price=fill_px, qty=btc_qty,
                return_pct=ret_pct, pnl_usd=rpnl,
                entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
                exit_ts_ms=int(h4.open_time[i]),
            ))
            btc_qty = 0.0
            entry_avg = 0.0
            pending_exit = False
            exit_decided = False

        if exit_delay_countdown > 0:
            exit_delay_countdown -= 1
            if exit_delay_countdown == 0:
                in_position = False
                peak_price = 0.0
                pending_exit = True
            if in_position:
                peak_price = max(peak_price, close_val)

        if pending_entry_delay_countdown > 0:
            pending_entry_delay_countdown -= 1
            if pending_entry_delay_countdown == 0:
                if not in_position and not exit_decided:
                    in_position = True
                    peak_price = close_val
                    entry_bar_idx = i
                    pending_entry = True
                else:
                    suppressed_entries += 1

        if i < rsi:
            continue

        ema_f = ind.ema_fast[i]
        ema_s = ind.ema_slow[i]
        trail_val = ind.trail_atr[i]
        vdo_val = ind.vdo[i]

        if math.isnan(trail_val) or math.isnan(ema_f) or math.isnan(ema_s):
            continue

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not in_position and not exit_decided:
            regime_ok = True
            if ind.d1_regime_ok is not None:
                regime_ok = bool(ind.d1_regime_ok[i])
            if trend_up and vdo_val > vdo_threshold and regime_ok:
                ed = _draw_delay(entry_dist, rng)
                if ed > 0:
                    pending_entry_delay_countdown = ed
                    continue
                in_position = True
                peak_price = close_val
                entry_bar_idx = i
                pending_entry = True

        elif in_position and not exit_decided:
            peak_price = max(peak_price, close_val)
            trail_stop = peak_price - trail_mult * trail_val
            exit_signal = close_val < trail_stop or trend_down

            if exit_signal:
                xd = _draw_delay(exit_dist, rng)
                if xd > 0:
                    exit_decided = True
                    exit_delay_countdown = xd
                else:
                    in_position = False
                    peak_price = 0.0
                    pending_exit = True

    if btc_qty > 0:
        fill_px = h4.close[-1] * SELL_ADJ
        fee = btc_qty * fill_px * FEE_RATE
        rpnl = btc_qty * (fill_px - entry_avg) - fee
        ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
        cash += btc_qty * fill_px - fee
        trades.append(Trade(
            entry_bar_idx=entry_bar_idx, entry_fill_bar_idx=entry_fill_bar_idx,
            entry_fill_price=entry_fill_price,
            exit_bar_idx=n - 1, exit_fill_bar_idx=n - 1,
            exit_fill_price=fill_px, qty=btc_qty,
            return_pct=ret_pct, pnl_usd=rpnl,
            entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
            exit_ts_ms=int(h4.open_time[-1]),
        ))

    m = compute_metrics(trades)
    return ReplayResult(
        trades=trades,
        native_terminal=m["native_terminal"],
        unit_terminal=m["unit_terminal"],
        sharpe=m["sharpe"],
        cagr_native=m["cagr_native"],
        cagr_unit=m["cagr_unit"],
        mdd_native=m["mdd_native"],
        suppressed_entries=suppressed_entries,
    )


def replay_sm_stochastic(ind: SMIndicators, h4: BarData,
                          entry_dist: dict[int, float],
                          exit_dist: dict[int, float],
                          rng: np.random.RandomState) -> ReplayResult:
    """Replay SM with per-event stochastic delays."""
    n = len(h4.close)
    rsi = ind.report_start_idx

    active = False
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    current_exposure = 0.0
    cum_rpnl = 0.0
    pending_signal = None
    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0
    pending_entry_delay_countdown = 0
    exit_delay_countdown = 0
    exit_decided = False
    suppressed_entries = 0
    trades: list[Trade] = []

    for i in range(n):
        close_val = h4.close[i]
        open_val = h4.open[i]
        mid = open_val

        if pending_signal is not None and i > 0:
            target_expo, reason = pending_signal
            pending_signal = None
            nav = cash + btc_qty * mid
            if nav <= 0:
                nav = 1.0
            current_exposure = (btc_qty * mid / nav) if (nav > 0 and btc_qty > 0) else 0.0

            if target_expo < EXPO_THRESHOLD and btc_qty > 0:
                fill_px = mid * SELL_ADJ
                fee = btc_qty * fill_px * FEE_RATE
                final_rpnl = btc_qty * (fill_px - entry_avg) - fee
                total_pnl = cum_rpnl + final_rpnl
                ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
                cash += btc_qty * fill_px - fee
                trades.append(Trade(
                    entry_bar_idx=entry_bar_idx,
                    entry_fill_bar_idx=entry_fill_bar_idx,
                    entry_fill_price=entry_fill_price,
                    exit_bar_idx=i - 1, exit_fill_bar_idx=i,
                    exit_fill_price=fill_px, qty=btc_qty,
                    return_pct=ret_pct, pnl_usd=total_pnl,
                    entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
                    exit_ts_ms=int(h4.open_time[i]),
                ))
                btc_qty = 0.0
                entry_avg = 0.0
                current_exposure = 0.0
                cum_rpnl = 0.0
                exit_decided = False
            else:
                delta = target_expo - current_exposure
                if delta > EXPO_THRESHOLD:
                    buy_value = delta * nav
                    fill_px = mid * BUY_ADJ
                    qty_buy = buy_value / mid
                    total_cost = qty_buy * fill_px * (1 + FEE_RATE)
                    if total_cost > cash:
                        qty_buy = cash / (fill_px * (1 + FEE_RATE))
                    fee = qty_buy * fill_px * FEE_RATE
                    if btc_qty == 0:
                        entry_fill_bar_idx = i
                        entry_fill_price = fill_px
                        entry_avg = fill_px
                        cum_rpnl = 0.0
                    else:
                        entry_avg = (entry_avg * btc_qty + fill_px * qty_buy) / (btc_qty + qty_buy)
                    cash -= qty_buy * fill_px + fee
                    btc_qty += qty_buy
                elif delta < -EXPO_THRESHOLD:
                    sell_value = abs(delta) * nav
                    fill_px = mid * SELL_ADJ
                    qty_sell = min(sell_value / mid, btc_qty)
                    fee = qty_sell * fill_px * FEE_RATE
                    cum_rpnl += qty_sell * (fill_px - entry_avg) - fee
                    cash += qty_sell * fill_px - fee
                    btc_qty -= qty_sell
                nav_after = cash + btc_qty * mid
                current_exposure = (btc_qty * mid / nav_after) if nav_after > 0 else 0.0

        if exit_delay_countdown > 0:
            exit_delay_countdown -= 1
            if exit_delay_countdown == 0:
                active = False
                pending_signal = (0.0, "vtrend_sm_delayed_exit")

        if pending_entry_delay_countdown > 0:
            pending_entry_delay_countdown -= 1
            if pending_entry_delay_countdown == 0 and not active and not exit_decided:
                rv_val = ind.rv[i]
                if np.isfinite(rv_val):
                    weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                    if weight > 0.0:
                        active = True
                        entry_bar_idx = i
                        pending_signal = (weight, "vtrend_sm_entry")
            elif active or exit_decided:
                suppressed_entries += 1

        if i < max(ind.warmup_end, rsi):
            continue

        ema_f = ind.ema_fast[i]
        ema_s = ind.ema_slow[i]
        ema_s_ref = ind.ema_slow_slope_ref[i]
        atr_val = ind.atr_arr[i]
        hh = ind.hh_entry[i]
        ll = ind.ll_exit[i]
        rv_val = ind.rv[i]

        if not (np.isfinite(ema_f) and np.isfinite(ema_s)
                and np.isfinite(ema_s_ref) and np.isfinite(atr_val)
                and np.isfinite(hh) and np.isfinite(ll) and np.isfinite(rv_val)):
            continue

        regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)

        if not active and not exit_decided:
            breakout_ok = close_val > hh
            if regime_ok and breakout_ok:
                ed = _draw_delay(entry_dist, rng)
                if ed > 0:
                    pending_entry_delay_countdown = ed
                    continue
                weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                if weight > 0.0:
                    active = True
                    entry_bar_idx = i
                    pending_signal = (weight, "vtrend_sm_entry")
        elif active and not exit_decided:
            exit_floor = max(ll, ema_s - ind.atr_mult * atr_val)
            floor_break = close_val < exit_floor

            if floor_break:
                xd = _draw_delay(exit_dist, rng)
                if xd > 0:
                    exit_decided = True
                    exit_delay_countdown = xd
                else:
                    active = False
                    pending_signal = (0.0, "vtrend_sm_floor_exit")
            else:
                new_weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                nav_now = cash + btc_qty * close_val
                expo_now = (btc_qty * close_val / nav_now) if nav_now > 0 else 0.0
                delta_w = abs(new_weight - expo_now)
                if delta_w >= ind.min_rebalance_weight_delta - 1e-12:
                    if not exit_decided:
                        pending_signal = (new_weight, "vtrend_sm_rebalance")

    if btc_qty > 0:
        fill_px = h4.close[-1] * SELL_ADJ
        fee = btc_qty * fill_px * FEE_RATE
        final_rpnl = btc_qty * (fill_px - entry_avg) - fee
        total_pnl = cum_rpnl + final_rpnl
        ret_pct = (fill_px / entry_avg - 1) * 100.0 if entry_avg > 0 else 0.0
        cash += btc_qty * fill_px - fee
        trades.append(Trade(
            entry_bar_idx=entry_bar_idx, entry_fill_bar_idx=entry_fill_bar_idx,
            entry_fill_price=entry_fill_price,
            exit_bar_idx=n - 1, exit_fill_bar_idx=n - 1,
            exit_fill_price=fill_px, qty=btc_qty,
            return_pct=ret_pct, pnl_usd=total_pnl,
            entry_ts_ms=int(h4.open_time[entry_fill_bar_idx]),
            exit_ts_ms=int(h4.open_time[-1]),
        ))

    m = compute_metrics(trades)
    return ReplayResult(
        trades=trades,
        native_terminal=m["native_terminal"],
        unit_terminal=m["unit_terminal"],
        sharpe=m["sharpe"],
        cagr_native=m["cagr_native"],
        cagr_unit=m["cagr_unit"],
        mdd_native=m["mdd_native"],
        suppressed_entries=suppressed_entries,
    )


def run_stochastic_replay(cand: CandidateDef, indicators, h4: BarData,
                           entry_dist: dict, exit_dist: dict,
                           rng: np.random.RandomState) -> ReplayResult:
    if cand.variant in ("E0", "E5", "E0_plus", "E5_plus"):
        return replay_binary_stochastic(indicators, h4, entry_dist, exit_dist, rng)
    elif cand.variant == "SM":
        return replay_sm_stochastic(indicators, h4, entry_dist, exit_dist, rng)
    else:
        raise ValueError(f"Unknown variant: {cand.variant}")


def phase_e_stochastic(cand: CandidateDef, indicators, h4: BarData,
                        baseline: ReplayResult) -> dict:
    """Run stochastic delay MC for 3 LT tiers x N draws."""
    results = {}

    for lt in ["LT1", "LT2", "LT3"]:
        entry_dist = STOCHASTIC_ENTRY[lt]
        exit_dist = STOCHASTIC_EXIT[lt]
        draws = []
        rng = np.random.RandomState(SEED + hash(lt) % 10000 + hash(cand.label) % 10000)

        for draw_idx in range(N_STOCHASTIC_DRAWS):
            r = run_stochastic_replay(cand, indicators, h4,
                                       entry_dist, exit_dist, rng)
            draws.append({
                "n_trades": len(r.trades),
                "sharpe": r.sharpe,
                "cagr_native": r.cagr_native,
                "mdd_native": r.mdd_native,
                "native_terminal": r.native_terminal,
                "suppressed_entries": r.suppressed_entries,
            })

        sharpes = np.array([d["sharpe"] for d in draws])
        cagrs = np.array([d["cagr_native"] for d in draws])
        mdds = np.array([d["mdd_native"] for d in draws])
        n_trades_arr = np.array([d["n_trades"] for d in draws])

        delta_sharpes = sharpes - baseline.sharpe
        delta_cagrs = cagrs - baseline.cagr_native
        baseline_mdd = BASELINE_METRICS[cand.label]["mdd"]
        delta_mdds = mdds - baseline_mdd

        results[lt] = {
            "n_draws": N_STOCHASTIC_DRAWS,
            "sharpe_mean": float(np.mean(sharpes)),
            "sharpe_std": float(np.std(sharpes, ddof=0)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p50": float(np.median(sharpes)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
            "cagr_mean": float(np.mean(cagrs)),
            "cagr_p5": float(np.percentile(cagrs, 5)),
            "cagr_p50": float(np.median(cagrs)),
            "mdd_mean": float(np.mean(mdds)),
            "mdd_p95": float(np.percentile(mdds, 95)),
            "delta_sharpe_mean": float(np.mean(delta_sharpes)),
            "delta_sharpe_p5": float(np.percentile(delta_sharpes, 5)),
            "delta_sharpe_p95": float(np.percentile(delta_sharpes, 95)),
            "delta_cagr_p5": float(np.percentile(delta_cagrs, 5)),
            "delta_mdd_p95": float(np.percentile(delta_mdds, 95)),
            "p_cagr_le_0": float(np.mean(cagrs <= 0)),
            "p_sharpe_positive": float(np.mean(sharpes > 0)),
            "n_trades_mean": float(np.mean(n_trades_arr)),
            "suppressed_mean": float(np.mean([d["suppressed_entries"] for d in draws])),
            "baseline_sharpe": baseline.sharpe,
            "baseline_cagr": baseline.cagr_native,
            "baseline_mdd": baseline_mdd,
        }

    return results


# ===================================================================
# PHASE F: 5-GATE COMPARATIVE SIGN-OFF
# ===================================================================
#
# Replaces: Step 5 delta-based SIGNOFF_GATES
# See: research/x6/X6_VS_X0_RESEARCH_DEPLOYMENT_SPEC.md §4
#
# Gates:
#   G1: Absolute dominance — worst-case Sharpe > alternative's worst
#   G2: State dominance — wins >50% of disruption scenarios
#   G3: Fractional loss — (baseline - worst) / baseline < 35%
#   G4: Absolute floor — worst-case Sharpe > 0.50
#   G5: Infra-conditioned — D1+D1 delta > -0.20

@dataclass
class DisruptionScenario:
    """A single disruption scenario with its observed Sharpe."""
    name: str
    sharpe: float
    entry_delay: int
    exit_delay: int
    has_miss: bool

    @property
    def max_delay(self) -> int:
        return max(self.entry_delay, self.exit_delay)


@dataclass
class CandidateProfile:
    """Aggregate disruption profile for comparative sign-off."""
    label: str
    baseline_sharpe: float
    scenarios: list[DisruptionScenario]
    stochastic_means: dict[str, float]   # lt_tier -> mean Sharpe
    d1_d1_sharpe: float                  # Sharpe at entry_D1 + exit_D1

    def worst_sharpe(self, max_delay: int = 99) -> float:
        """Worst Sharpe among tier-appropriate scenarios (excluding miss)."""
        eligible = [
            s.sharpe for s in self.scenarios
            if s.max_delay <= max_delay and not s.has_miss
        ]
        # Include stochastic means for tiers within max_delay scope
        for lt, max_d in [("LT1", 2), ("LT2", 4), ("LT3", 99)]:
            if max_d <= max_delay and lt in self.stochastic_means:
                eligible.append(self.stochastic_means[lt])
        return min(eligible) if eligible else 0.0

    @property
    def d1_d1_delta(self) -> float:
        return self.d1_d1_sharpe - self.baseline_sharpe

    def comparison_dict(self) -> dict[str, float]:
        """All scenarios for state comparison (G2), excluding miss scenarios."""
        d: dict[str, float] = {}
        for s in self.scenarios:
            if not s.has_miss:
                d[s.name] = s.sharpe
        for lt, val in self.stochastic_means.items():
            d[f"stochastic_{lt}_mean"] = val
        return d


@dataclass
class GateResult:
    gate: str
    passed: bool
    value: float
    threshold: float | None
    detail: str


@dataclass
class ComparativeVerdict:
    candidate: str
    alternative: str
    gates: list[GateResult]
    status: str   # "GO", "FALLBACK", "NO_GO"

    @property
    def all_pass(self) -> bool:
        return all(g.passed for g in self.gates)

    def to_dict(self) -> dict:
        return {
            "candidate": self.candidate,
            "alternative": self.alternative,
            "status": self.status,
            "all_pass": self.all_pass,
            "gates": [
                {
                    "gate": g.gate,
                    "passed": g.passed,
                    "value": round(g.value, 6) if isinstance(g.value, float) else g.value,
                    "threshold": (round(g.threshold, 6)
                                  if isinstance(g.threshold, float) else g.threshold),
                    "detail": g.detail,
                }
                for g in self.gates
            ],
        }


def evaluate_comparative_gates(
    candidate: CandidateProfile,
    alternative: CandidateProfile,
    max_delay: int = TIER_MAX_DELAY["LT1"],
) -> ComparativeVerdict:
    """Evaluate 5-gate absolute comparative sign-off.

    Args:
        candidate: The candidate being evaluated.
        alternative: The best alternative to compare against.
        max_delay: Maximum delay for tier-appropriate worst-case (default: LT1=2).
    """
    thresholds = COMPARATIVE_GATE_THRESHOLDS
    gates: list[GateResult] = []
    cand_worst = candidate.worst_sharpe(max_delay)
    alt_worst = alternative.worst_sharpe(max_delay)

    # G1: Absolute dominance under worst tier-appropriate disruption
    g1_pass = cand_worst > alt_worst
    gates.append(GateResult(
        gate="G1_absolute_dominance",
        passed=g1_pass,
        value=cand_worst,
        threshold=alt_worst,
        detail=(
            f"candidate_worst={cand_worst:.4f} "
            f"{'>' if g1_pass else '<='} "
            f"alternative_worst={alt_worst:.4f}"
        ),
    ))

    # G2: State-by-state dominance (ALL scenarios, not tier-filtered)
    cand_all = candidate.comparison_dict()
    alt_all = alternative.comparison_dict()
    common = sorted(set(cand_all) & set(alt_all))
    wins = sum(1 for s in common if cand_all[s] > alt_all[s])
    total = len(common)
    ratio = wins / total if total > 0 else 0.0
    min_ratio = thresholds["G2_state_dominance_min_ratio"]
    g2_pass = ratio > min_ratio
    gates.append(GateResult(
        gate="G2_state_dominance",
        passed=g2_pass,
        value=ratio,
        threshold=min_ratio,
        detail=f"wins={wins}/{total} ({ratio:.1%}), threshold>{min_ratio:.0%}",
    ))

    # G3: Fractional loss (tier-filtered worst)
    frac_loss_max = thresholds["G3_fractional_loss_max"]
    if candidate.baseline_sharpe > 0:
        frac_loss = (candidate.baseline_sharpe - cand_worst) / candidate.baseline_sharpe
    else:
        frac_loss = 1.0
    g3_pass = frac_loss < frac_loss_max
    gates.append(GateResult(
        gate="G3_fractional_loss",
        passed=g3_pass,
        value=frac_loss,
        threshold=frac_loss_max,
        detail=(
            f"loss={frac_loss:.1%} "
            f"(baseline={candidate.baseline_sharpe:.4f}, worst={cand_worst:.4f})"
        ),
    ))

    # G4: Absolute floor (tier-filtered worst)
    floor = thresholds["G4_absolute_floor"]
    g4_pass = cand_worst > floor
    gates.append(GateResult(
        gate="G4_absolute_floor",
        passed=g4_pass,
        value=cand_worst,
        threshold=floor,
        detail=f"worst_sharpe={cand_worst:.4f}, floor={floor:.2f}",
    ))

    # G5: Infrastructure-conditioned (D1+D1 delta)
    infra_threshold = thresholds["G5_infra_delta_threshold"]
    d1_d1_delta = candidate.d1_d1_delta
    g5_pass = d1_d1_delta > infra_threshold
    gates.append(GateResult(
        gate="G5_infra_conditioned",
        passed=g5_pass,
        value=d1_d1_delta,
        threshold=infra_threshold,
        detail=f"d1_d1_delta={d1_d1_delta:.4f}, threshold={infra_threshold:.2f}",
    ))

    # Determine status
    if all(g.passed for g in gates):
        status = "GO"
    elif gates[2].passed and gates[3].passed and gates[4].passed:
        # G3+G4+G5 pass but G1 or G2 fail → adequate but not dominant
        status = "FALLBACK"
    else:
        status = "NO_GO"

    return ComparativeVerdict(
        candidate=candidate.label,
        alternative=alternative.label,
        gates=gates,
        status=status,
    )


def build_candidate_profile(
    label: str,
    baseline: ReplayResult,
    combined_results: dict,
    stochastic_results: dict,
) -> CandidateProfile:
    """Build CandidateProfile from phase C/D/E outputs."""
    scenarios = []
    for sc_name, sc_data in combined_results.items():
        scenarios.append(DisruptionScenario(
            name=sc_name,
            sharpe=sc_data["sharpe"],
            entry_delay=sc_data.get("entry_delay", 0),
            exit_delay=sc_data.get("exit_delay", 0),
            has_miss=sc_data.get("n_miss", 0) > 0,
        ))

    stochastic_means: dict[str, float] = {}
    for lt in ["LT1", "LT2", "LT3"]:
        st = stochastic_results.get(lt, {})
        if "sharpe_mean" in st:
            stochastic_means[lt] = st["sharpe_mean"]

    d1_d1_data = combined_results.get("entry_D1_exit_D1", {})
    d1_d1_sharpe = d1_d1_data.get("sharpe", baseline.sharpe)

    return CandidateProfile(
        label=label,
        baseline_sharpe=baseline.sharpe,
        scenarios=scenarios,
        stochastic_means=stochastic_means,
        d1_d1_sharpe=d1_d1_sharpe,
    )


def phase_f_comparative(
    all_profiles: dict[str, CandidateProfile],
) -> dict[str, ComparativeVerdict]:
    """Evaluate 5-gate comparative sign-off for all candidates.

    Each candidate is compared against its best alternative (the other
    candidate with the highest tier-appropriate worst-case Sharpe).
    """
    verdicts: dict[str, ComparativeVerdict] = {}
    labels = list(all_profiles.keys())
    max_d = TIER_MAX_DELAY["LT1"]

    for label in labels:
        candidate = all_profiles[label]
        alternatives = {k: v for k, v in all_profiles.items() if k != label}
        if not alternatives:
            continue
        # Best alternative = highest worst-case Sharpe at LT1
        best_alt_label = max(
            alternatives,
            key=lambda k: alternatives[k].worst_sharpe(max_d),
        )
        alternative = alternatives[best_alt_label]
        verdicts[label] = evaluate_comparative_gates(
            candidate, alternative, max_delay=max_d,
        )

    return verdicts


# ===================================================================
# ARTIFACT WRITING
# ===================================================================

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def write_per_candidate_artifacts(cand: CandidateDef,
                                   baseline: ReplayResult,
                                   validation: dict,
                                   exit_delay_results: dict,
                                   combined_results: dict,
                                   stochastic_results: dict):
    """Write per-candidate artifacts (phases B-E).

    signoff_gates.json is written separately after comparative evaluation.
    """
    cdir = ARTIFACT_DIR / "candidates" / cand.label
    cdir.mkdir(parents=True, exist_ok=True)

    # 1. harness_validation.json
    val_out = {
        "regression": validation["regression"],
        "probe_results": validation["probe_results"],
    }
    write_json(cdir / "harness_validation.json", val_out)

    # 2. exit_delay_summary.json
    write_json(cdir / "exit_delay_summary.json", exit_delay_results)

    # 3. combined_disruption_summary.json
    write_json(cdir / "combined_disruption_summary.json", combined_results)

    # 4. stochastic_delay_summary.json (without raw draws)
    write_json(cdir / "stochastic_delay_summary.json", stochastic_results)


def write_root_artifacts(all_results: dict):
    """Write root-level cross-candidate artifacts."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. exit_delay_cross_summary.csv
    rows = []
    for label, data in all_results.items():
        bl = data["baseline"]
        for D, r in data["exit_delay"].items():
            rows.append({
                "candidate": label,
                "exit_delay_bars": D,
                "n_trades": r["n_trades"],
                "sharpe": f"{r['sharpe']:.4f}",
                "cagr_native": f"{r['cagr_native']:.4f}",
                "mdd_native": f"{r['mdd_native']:.4f}",
                "delta_sharpe": f"{r['delta_sharpe']:.4f}",
                "delta_cagr": f"{r['delta_cagr_native']:.4f}",
                "delta_mdd": f"{r['delta_mdd_native']:.4f}",
                "suppressed_entries": r.get("suppressed_entries", 0),
            })
    write_csv(ARTIFACT_DIR / "exit_delay_cross_summary.csv", rows)

    # 2. combined_disruption_cross_summary.csv
    rows = []
    for label, data in all_results.items():
        for sc_name, sc_data in data["combined"].items():
            rows.append({
                "candidate": label,
                "scenario": sc_name,
                "entry_delay": sc_data["entry_delay"],
                "exit_delay": sc_data["exit_delay"],
                "n_miss": sc_data["n_miss"],
                "n_trades": sc_data["n_trades"],
                "sharpe": f"{sc_data['sharpe']:.4f}",
                "delta_sharpe": f"{sc_data['delta_sharpe']:.4f}",
                "cagr_native": f"{sc_data['cagr_native']:.4f}",
                "mdd_native": f"{sc_data['mdd_native']:.4f}",
            })
    write_csv(ARTIFACT_DIR / "combined_disruption_cross_summary.csv", rows)

    # 3. stochastic_delay_cross_summary.csv
    rows = []
    for label, data in all_results.items():
        for lt, st in data["stochastic"].items():
            rows.append({
                "candidate": label,
                "latency_tier": lt,
                "sharpe_p50": f"{st['sharpe_p50']:.4f}",
                "sharpe_p5": f"{st['sharpe_p5']:.4f}",
                "sharpe_p95": f"{st['sharpe_p95']:.4f}",
                "cagr_p50": f"{st['cagr_p50']:.4f}",
                "cagr_p5": f"{st['cagr_p5']:.4f}",
                "mdd_p95": f"{st['mdd_p95']:.4f}",
                "delta_sharpe_p5": f"{st['delta_sharpe_p5']:.4f}",
                "delta_sharpe_p95": f"{st['delta_sharpe_p95']:.4f}",
                "p_cagr_le_0": f"{st['p_cagr_le_0']:.4f}",
                "p_sharpe_positive": f"{st['p_sharpe_positive']:.4f}",
                "n_draws": st["n_draws"],
            })
    write_csv(ARTIFACT_DIR / "stochastic_delay_cross_summary.csv", rows)

    # 4. signoff_matrix.csv (5-gate comparative framework)
    rows = []
    for label, data in all_results.items():
        verdict = data.get("signoff")
        if verdict is None:
            continue
        row: dict[str, Any] = {
            "candidate": label,
            "alternative": verdict.alternative,
            "status": verdict.status,
        }
        for g in verdict.gates:
            row[g.gate] = "PASS" if g.passed else "FAIL"
            row[f"{g.gate}_value"] = (
                f"{g.value:.4f}" if isinstance(g.value, float) else str(g.value)
            )
        rows.append(row)
    write_csv(ARTIFACT_DIR / "signoff_matrix.csv", rows)

    # 5. harness_validation_summary.csv
    rows = []
    for label, data in all_results.items():
        reg = data["validation"]["regression"]
        rows.append({
            "candidate": label,
            "trade_count_match": reg["trade_count"],
            "timestamps_match": reg["entry_exit_timestamps"],
            "native_terminal_match": reg["native_terminal_match"],
            "exit_d0_matches_baseline": reg.get("exit_delay_0_matches_baseline", "N/A"),
            "all_pass": reg["all_pass"],
        })
    write_csv(ARTIFACT_DIR / "harness_validation_summary.csv", rows)

    # 6. step5_summary.json
    summary = {
        "candidates_tested": [c.label for c in CANDIDATES],
        "latch_dropped": True,
        "phases_completed": ["B", "C", "D", "E", "F", "G"],
        "n_stochastic_draws": N_STOCHASTIC_DRAWS,
        "exit_delay_bars_tested": EXIT_DELAY_BARS,
        "combined_scenarios_tested": len(COMBINED_SCENARIOS),
        "signoff_matrix": {},
    }
    for label, data in all_results.items():
        verdict = data.get("signoff")
        if verdict:
            summary["signoff_matrix"][label] = {
                "status": verdict.status,
                "alternative": verdict.alternative,
                "gates": {g.gate: g.passed for g in verdict.gates},
            }
    write_json(ARTIFACT_DIR / "step5_summary.json", summary)


# ===================================================================
# FIGURE GENERATION
# ===================================================================

def generate_figures(all_results: dict):
    """Generate 4 PNG figures."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("WARNING: matplotlib not available, skipping figures")
        return

    fig_dir = ARTIFACT_DIR
    fig_dir.mkdir(parents=True, exist_ok=True)

    labels = list(all_results.keys())
    colors = {"E0": "#1f77b4", "E5": "#ff7f0e", "SM": "#2ca02c",
              "E0_plus_EMA1D21": "#d62728", "E5_plus_EMA1D21": "#9467bd"}

    # Figure 1: Exit delay delta Sharpe
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    for label in labels:
        delays = sorted(all_results[label]["exit_delay"].keys())
        deltas = [all_results[label]["exit_delay"][d]["delta_sharpe"] for d in delays]
        ax.plot(delays, deltas, "o-", label=label, color=colors.get(label, "gray"), linewidth=2)
    ax.axhline(0, color="black", linestyle="--", alpha=0.3)
    ax.set_xlabel("Exit Delay (H4 bars)")
    ax.set_ylabel("Delta Sharpe")
    ax.set_title("Exit Delay Sensitivity: Sharpe Degradation")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "exit_delay_delta_sharpe.png", dpi=150)
    plt.close(fig)

    # Figure 2: Combined disruption worst-case
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    scenarios = [s[0] for s in COMBINED_SCENARIOS]
    x = np.arange(len(scenarios))
    width = 0.15
    for j, label in enumerate(labels):
        deltas = [all_results[label]["combined"].get(s, {}).get("delta_sharpe", 0)
                  for s in scenarios]
        ax.bar(x + j * width, deltas, width, label=label, color=colors.get(label, "gray"))
    ax.axhline(0, color="black", linestyle="--", alpha=0.3)
    ax.axhline(-0.20, color="red", linestyle=":", alpha=0.5, label="GO threshold")
    ax.axhline(-0.35, color="orange", linestyle=":", alpha=0.5, label="GO_WITH_GUARDS threshold")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Delta Sharpe")
    ax.set_title("Combined Disruptions: Sharpe Impact")
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(scenarios, rotation=45, ha="right")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(fig_dir / "combined_disruption_worstcase.png", dpi=150)
    plt.close(fig)

    # Figure 3: Stochastic delay p5 Sharpe matrix
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))
    tiers = ["LT1", "LT2", "LT3"]
    matrix = np.zeros((len(labels), len(tiers)))
    for i, label in enumerate(labels):
        for j, lt in enumerate(tiers):
            st = all_results[label]["stochastic"].get(lt, {})
            matrix[i, j] = st.get("sharpe_p5", 0)
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(tiers)))
    ax.set_xticklabels(tiers)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(tiers)):
            ax.text(j, i, f"{matrix[i, j]:.3f}", ha="center", va="center",
                    fontsize=10, fontweight="bold")
    ax.set_title("Stochastic Delay: p5 Sharpe by Candidate x Latency Tier")
    fig.colorbar(im, ax=ax, label="Sharpe (p5)")
    fig.tight_layout()
    fig.savefig(fig_dir / "stochastic_delay_p95_matrix.png", dpi=150)
    plt.close(fig)

    # Figure 4: 5-gate comparative sign-off matrix
    gate_names = [
        "G1_absolute_dominance", "G2_state_dominance",
        "G3_fractional_loss", "G4_absolute_floor", "G5_infra_conditioned",
    ]
    gate_short = ["G1:Dom", "G2:State", "G3:Frac", "G4:Floor", "G5:Infra"]
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    matrix_gates = np.zeros((len(labels), len(gate_names)))
    for i, label in enumerate(labels):
        verdict = all_results[label].get("signoff")
        if verdict is None:
            continue
        for j, gname in enumerate(gate_names):
            for g in verdict.gates:
                if g.gate == gname:
                    matrix_gates[i, j] = 1.0 if g.passed else 0.0
                    break
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#d62728", "#2ca02c"])
    im = ax.imshow(matrix_gates, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(gate_names)))
    ax.set_xticklabels(gate_short)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i, label in enumerate(labels):
        verdict = all_results[label].get("signoff")
        if verdict is None:
            continue
        for j, gname in enumerate(gate_names):
            for g in verdict.gates:
                if g.gate == gname:
                    txt = "PASS" if g.passed else "FAIL"
                    ax.text(j, i, txt, ha="center", va="center",
                            fontsize=9, fontweight="bold", color="white")
                    break
        # Add overall status as annotation
        ax.text(len(gate_names) - 0.3, i, f"  {verdict.status}",
                ha="left", va="center", fontsize=9, fontweight="bold")
    ax.set_title("5-Gate Comparative Sign-Off: Candidate x Gate")
    fig.tight_layout()
    fig.savefig(fig_dir / "live_signoff_matrix.png", dpi=150)
    plt.close(fig)

    print(f"  Figures saved to {fig_dir}")


# ===================================================================
# MAIN
# ===================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("STEP 5 — Live Sign-Off Hardening")
    print("=" * 70)

    # --- Load data ---
    print("\n[1/7] Loading bar data...")
    h4, d1, report_start_idx = load_bars()
    print(f"  H4 bars: {len(h4.close)}, D1 bars: {len(d1.close)}")
    print(f"  Report start index: {report_start_idx}")

    all_results = {}

    for cand in CANDIDATES:
        tc = time.time()
        print(f"\n{'='*60}")
        print(f"  Candidate: {cand.label} ({cand.variant})")
        print(f"{'='*60}")

        # Precompute indicators
        print(f"  [B] Precomputing indicators...")
        indicators = precompute_indicators(cand.variant, h4, d1, report_start_idx)

        # Phase B: Harness validation
        print(f"  [B] Running harness validation...")
        canonical = load_canonical_trades(cand.trade_csv)
        validation = phase_b_validation(cand, indicators, h4, canonical)
        baseline = validation["baseline"]
        reg = validation["regression"]
        status = "PASS" if reg["all_pass"] else "FAIL"
        print(f"    REPLAY_REGRESS: {status}")
        print(f"    Trade count: {reg['trade_count_detail']}")
        print(f"    Baseline Sharpe: {baseline.sharpe:.4f}, CAGR: {baseline.cagr_native:.4f}")
        print(f"    Exit delay=0 matches baseline: {reg.get('exit_delay_0_matches_baseline', 'N/A')}")

        # Get entry bar indices for combined disruptions
        entry_indices = np.array([t.entry_bar_idx for t in baseline.trades])

        # Phase C: Exit delay grid
        print(f"  [C] Running exit delay grid (4 levels)...")
        exit_delay_results = phase_c_exit_delay(cand, indicators, h4, baseline)
        for D, r in sorted(exit_delay_results.items()):
            print(f"    D{D}: Sharpe={r['sharpe']:.4f} delta={r['delta_sharpe']:+.4f} "
                  f"MDD={r['mdd_native']:.4f} suppressed={r.get('suppressed_entries', 0)}")

        # Phase D: Combined disruptions
        print(f"  [D] Running combined disruptions ({len(COMBINED_SCENARIOS)} scenarios)...")
        combined_results = phase_d_combined(cand, indicators, h4, baseline, entry_indices)
        for sc_name, sc_data in combined_results.items():
            print(f"    {sc_name}: Sharpe={sc_data['sharpe']:.4f} delta={sc_data['delta_sharpe']:+.4f}")

        # Phase E: Stochastic MC
        print(f"  [E] Running stochastic delay MC ({N_STOCHASTIC_DRAWS} draws x 3 tiers)...")
        stochastic_results = phase_e_stochastic(cand, indicators, h4, baseline)
        for lt, st in stochastic_results.items():
            print(f"    {lt}: Sharpe p50={st['sharpe_p50']:.4f} p5={st['sharpe_p5']:.4f} "
                  f"P(CAGR<=0)={st['p_cagr_le_0']:.3f}")

        # Write per-candidate artifacts (phases B-E)
        write_per_candidate_artifacts(cand, baseline, validation,
                                      exit_delay_results, combined_results,
                                      stochastic_results)

        all_results[cand.label] = {
            "baseline": baseline,
            "validation": validation,
            "exit_delay": exit_delay_results,
            "combined": combined_results,
            "stochastic": stochastic_results,
        }

        elapsed = time.time() - tc
        print(f"  Candidate {cand.label} complete in {elapsed:.1f}s")

    # Phase F: 5-gate comparative sign-off (all candidates at once)
    print(f"\n[F] Evaluating 5-gate comparative sign-off...")
    profiles: dict[str, CandidateProfile] = {}
    for label, data in all_results.items():
        profiles[label] = build_candidate_profile(
            label, data["baseline"], data["combined"], data["stochastic"],
        )
    verdicts = phase_f_comparative(profiles)
    for label, verdict in verdicts.items():
        all_results[label]["signoff"] = verdict
        # Write per-candidate signoff artifact
        cdir = ARTIFACT_DIR / "candidates" / label
        cdir.mkdir(parents=True, exist_ok=True)
        write_json(cdir / "signoff_gates.json", verdict.to_dict())
        print(f"  {label} vs {verdict.alternative}: {verdict.status}")
        for g in verdict.gates:
            mark = "PASS" if g.passed else "FAIL"
            print(f"    {g.gate}: {mark} ({g.detail})")

    # Phase G: Root artifacts & figures
    print(f"\n[G] Writing root artifacts...")
    write_root_artifacts(all_results)

    print(f"\n[G] Generating figures...")
    generate_figures(all_results)

    # Print final sign-off matrix (5-gate comparative)
    print("\n" + "=" * 70)
    print("FINAL SIGN-OFF MATRIX (5-Gate Comparative)")
    print("=" * 70)
    print(f"{'Candidate':<25} {'vs Alternative':<25} {'G1':<6} {'G2':<6} {'G3':<6} {'G4':<6} {'G5':<6} {'Status':<12}")
    print("-" * 91)
    for label, data in all_results.items():
        verdict = data.get("signoff")
        if verdict is None:
            print(f"{label:<25} {'N/A':<25} {'?':<6} {'?':<6} {'?':<6} {'?':<6} {'?':<6} {'N/A':<12}")
            continue
        g_marks = []
        for g in verdict.gates:
            g_marks.append("PASS" if g.passed else "FAIL")
        while len(g_marks) < 5:
            g_marks.append("?")
        print(f"{label:<25} {verdict.alternative:<25} "
              f"{g_marks[0]:<6} {g_marks[1]:<6} {g_marks[2]:<6} {g_marks[3]:<6} {g_marks[4]:<6} "
              f"{verdict.status:<12}")

    elapsed_total = time.time() - t0
    print(f"\nTotal elapsed: {elapsed_total:.1f}s ({elapsed_total/60:.1f}min)")
    print("\nStep 5 complete. All artifacts written.")


if __name__ == "__main__":
    main()
