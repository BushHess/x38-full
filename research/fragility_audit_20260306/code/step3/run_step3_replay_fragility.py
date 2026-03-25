#!/usr/bin/env python3
"""Step 3 — Replay-dependent operational fragility audit.

Phases:
  A: Build standalone replay simulators, validate via REPLAY_REGRESS
  B: Random missed-entry Monte Carlo (K={1,2,3}, 2000 draws)
  C: Outage-window entry-blackout sweep ({24,72,168}h)
  D: Delayed-entry replay ({1,2,3,4} bars)
  E: Cross-strategy synthesis & pairwise judgments

All strategies run as standalone replay (not engine wrapper) for performance.
Indicators are precomputed once per candidate; replay iterates bar-by-bar.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path("/var/www/trading-bots/btc-spot-dev")
BAR_FILE = REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
ARTIFACT_DIR = REPO / "research" / "fragility_audit_20260306" / "artifacts" / "step3"
REPORT_DIR = REPO / "research" / "fragility_audit_20260306" / "reports"

# ---------------------------------------------------------------------------
# Constants (frozen from Steps 0-2)
# ---------------------------------------------------------------------------
NAV0 = 10_000.0
BACKTEST_YEARS = 6.5
FEE_RATE = 0.0015  # taker_fee_pct for harsh
BUY_ADJ = 1.00100025   # (1 + 10/20000) * (1 + 5/10000) — spread + slippage
SELL_ADJ = 0.99900025   # (1 - 10/20000) * (1 - 5/10000)
EXPO_THRESHOLD = 0.005

PERIOD_START_MS = 1546300800000  # 2019-01-01T00:00:00Z
PERIOD_END_MS = 1771545600000    # 2026-02-20T00:00:00Z
WARMUP_DAYS = 365
BARS_PER_YEAR_4H = 365.0 * 6.0   # 2190.0

SEED = 20260306
K_VALUES = [1, 2, 3]
N_DRAWS = 2000
OUTAGE_HOURS = [24, 72, 168]
DELAY_BARS = [1, 2, 3, 4]

# ---------------------------------------------------------------------------
# Candidate definitions
# ---------------------------------------------------------------------------
@dataclass
class CandidateDef:
    label: str
    trade_csv: str  # relative to REPO
    strategy_type: str  # "binary" or "vol_target"
    variant: str  # E0, E5, E0_plus, E5_plus, SM, LATCH
    expected_trade_count: int

CANDIDATES = [
    CandidateDef("E0", "results/parity_20260305/eval_e0_vs_e0/results/trades_candidate.csv",
                 "binary", "E0", 192),
    CandidateDef("E5", "results/parity_20260305/eval_e5_vs_e0/results/trades_candidate.csv",
                 "binary", "E5", 207),
    CandidateDef("SM", "results/parity_20260305/eval_sm_vs_e0/results/trades_candidate.csv",
                 "vol_target", "SM", 65),
    CandidateDef("LATCH", "results/parity_20260305/eval_latch_vs_e0/results/trades_candidate.csv",
                 "vol_target", "LATCH", 65),
    CandidateDef("E0_plus_EMA1D21", "results/parity_20260305/eval_ema21d1_vs_e0/results/trades_candidate.csv",
                 "binary", "E0_plus", 172),
    CandidateDef("E5_plus_EMA1D21", "results/parity_20260306/eval_e5_ema21d1_vs_e0/results/trades_candidate.csv",
                 "binary", "E5_plus", 186),
]

# ===================================================================
# INDICATOR FUNCTIONS (copied from strategy files for reproducibility)
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


EPS = 1e-12


def _clip_weight_sm(weight: float, min_weight: float = 0.0) -> float:
    if not np.isfinite(weight):
        return 0.0
    w = min(1.0, max(0.0, float(weight)))
    if w < min_weight:
        return 0.0
    return w


def _clip_weight_latch(weight: float, max_pos: float, min_weight: float = 0.0) -> float:
    if not np.isfinite(weight):
        return 0.0
    w = min(max_pos, max(0.0, float(weight)))
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
    """Load H4 and D1 bars for the full period including warmup."""
    import pandas as pd
    df = pd.read_csv(BAR_FILE)

    h4 = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
    d1 = df[df["interval"] == "1d"].sort_values("open_time").reset_index(drop=True)

    # Warmup start: 365 days before period start
    warmup_start_ms = PERIOD_START_MS - WARMUP_DAYS * 86_400_000

    h4 = h4[h4["close_time"] >= warmup_start_ms].reset_index(drop=True)
    d1 = d1[d1["close_time"] >= warmup_start_ms].reset_index(drop=True)

    # Find report_start index (first H4 bar with close_time >= PERIOD_START_MS)
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
    """Load canonical trade CSV and return list of trade dicts."""
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
# PRECOMPUTED INDICATORS PER CANDIDATE
# ===================================================================

@dataclass
class BinaryIndicators:
    """Precomputed indicators for E0/E5/E0_plus/E5_plus."""
    ema_fast: np.ndarray
    ema_slow: np.ndarray
    trail_atr: np.ndarray  # standard ATR for E0/E0_plus, robust ATR for E5/E5_plus
    vdo: np.ndarray
    d1_regime_ok: np.ndarray | None  # None for E0/E5, array for _plus variants
    report_start_idx: int


@dataclass
class SMIndicators:
    """Precomputed indicators for SM."""
    ema_fast: np.ndarray
    ema_slow: np.ndarray
    ema_slow_slope_ref: np.ndarray
    atr_arr: np.ndarray
    hh_entry: np.ndarray
    ll_exit: np.ndarray
    rv: np.ndarray
    warmup_end: int
    report_start_idx: int
    # Resolved params
    target_vol: float
    min_weight: float
    min_rebalance_weight_delta: float
    atr_mult: float


@dataclass
class LatchIndicators:
    """Precomputed indicators for LATCH."""
    ema_fast: np.ndarray
    ema_slow: np.ndarray
    slope_ref: np.ndarray
    atr_arr: np.ndarray
    hh_entry: np.ndarray
    ll_exit: np.ndarray
    rv: np.ndarray
    regime_on: np.ndarray
    off_trigger: np.ndarray
    flip_off: np.ndarray
    warmup_end: int
    report_start_idx: int
    # Resolved params
    target_vol: float
    vol_floor: float
    max_pos: float
    min_weight: float
    min_rebalance_weight_delta: float
    atr_mult: float


def compute_d1_regime(h4_ct: np.ndarray, d1_data: BarData, d1_ema_period: int) -> np.ndarray:
    """Compute D1 EMA regime and map to H4 bar indices."""
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
    """Precompute all indicators for a candidate variant."""
    close = h4.close
    high = h4.high
    low = h4.low

    if variant in ("E0", "E5", "E0_plus", "E5_plus"):
        slow_p = 120
        fast_p = max(5, slow_p // 4)  # 30
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
        fast_p = max(5, slow_p // 4)  # 30
        entry_n = max(24, slow_p // 2)  # 60
        exit_n = max(12, slow_p // 4)  # 30
        vol_lookback = slow_p  # 120
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

        # Compute warmup_end
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

    elif variant == "LATCH":
        slow_p = 120
        fast_p = 30
        entry_n = 60
        exit_n = 30
        vol_lookback = 120
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

        regime_on, off_trigger, flip_off = _compute_hysteretic_regime(
            ema_fast, ema_slow, slope_ref
        )

        arrays = [ema_fast, ema_slow, slope_ref, atr_arr, hh_entry, ll_exit, rv]
        warmup_end = n
        for i in range(n):
            if all(np.isfinite(a[i]) for a in arrays):
                warmup_end = i
                break

        return LatchIndicators(
            ema_fast=ema_fast, ema_slow=ema_slow, slope_ref=slope_ref,
            atr_arr=atr_arr, hh_entry=hh_entry, ll_exit=ll_exit, rv=rv,
            regime_on=regime_on, off_trigger=off_trigger, flip_off=flip_off,
            warmup_end=warmup_end, report_start_idx=report_start_idx,
            target_vol=0.12, vol_floor=0.08, max_pos=1.0,
            min_weight=0.0, min_rebalance_weight_delta=0.05, atr_mult=2.0,
        )
    else:
        raise ValueError(f"Unknown variant: {variant}")


# ===================================================================
# REPLAY SIMULATORS
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


def compute_metrics(trades: list[Trade]) -> dict:
    """Compute Sharpe, CAGR, terminal from trade list."""
    if not trades:
        return {
            "n_trades": 0, "native_terminal": NAV0, "unit_terminal": NAV0,
            "sharpe": 0.0, "cagr_native": 0.0, "cagr_unit": 0.0,
        }
    returns = np.array([t.return_pct for t in trades])
    pnls = np.array([t.pnl_usd for t in trades])
    n = len(trades)
    native_terminal = NAV0 + np.sum(pnls)
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
    }


def replay_binary(ind: BinaryIndicators, h4: BarData,
                   skip_entries: set[int] | None = None,
                   blackout_start_ms: int = 0, blackout_end_ms: int = 0,
                   delay_bars: int = 0) -> ReplayResult:
    """Replay E0/E5/E0_plus/E5_plus with optional entry perturbations.

    skip_entries: set of canonical baseline entry bar indices to skip
    blackout_start_ms/end_ms: time window where entries are blocked
    delay_bars: delay all entries by this many bars
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
    pending_delay_countdown = 0
    pending_delay_bar_idx = -1
    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0

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
                exit_bar_idx=i - 1,  # decision was at previous bar
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

        # --- Delayed entry handling ---
        if pending_delay_countdown > 0:
            pending_delay_countdown -= 1
            if pending_delay_countdown == 0:
                # Fire the delayed entry NOW (will fill next bar open)
                if not in_position:
                    in_position = True
                    peak_price = close_val
                    entry_bar_idx = i
                    pending_entry = True

        # --- Warmup: run indicator logic but discard signals ---
        if i < rsi:
            # Still track indicator state (position-independent, so nothing to do)
            continue

        # --- Skip if indicators not ready ---
        ema_f = ind.ema_fast[i]
        ema_s = ind.ema_slow[i]
        trail_val = ind.trail_atr[i]
        vdo_val = ind.vdo[i]

        if math.isnan(trail_val) or math.isnan(ema_f) or math.isnan(ema_s):
            continue

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not in_position:
            # Check D1 regime for _plus variants
            regime_ok = True
            if ind.d1_regime_ok is not None:
                regime_ok = bool(ind.d1_regime_ok[i])

            if trend_up and vdo_val > vdo_threshold and regime_ok:
                # This bar would trigger entry in baseline
                # Check perturbations
                should_skip = False

                # Random miss: skip if this bar is in the skip set
                if i in skip_entries:
                    should_skip = True

                # Outage: skip if decision time falls in blackout
                if blackout_start_ms > 0 and blackout_start_ms <= close_time_ms <= blackout_end_ms:
                    should_skip = True

                # Delay: don't skip, but delay the entry
                if delay_bars > 0 and not should_skip:
                    pending_delay_countdown = delay_bars
                    pending_delay_bar_idx = i
                    continue

                if should_skip:
                    # Don't enter — stay flat, strategy remains ready for next entry
                    continue

                in_position = True
                peak_price = close_val
                entry_bar_idx = i
                pending_entry = True
        else:
            peak_price = max(peak_price, close_val)
            trail_stop = peak_price - trail_mult * trail_val
            if close_val < trail_stop:
                in_position = False
                peak_price = 0.0
                pending_exit = True
            elif trend_down:
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
    )


def replay_sm(ind: SMIndicators, h4: BarData,
              skip_entries: set[int] | None = None,
              blackout_start_ms: int = 0, blackout_end_ms: int = 0,
              delay_bars: int = 0) -> ReplayResult:
    """Replay SM with optional entry perturbations."""
    n = len(h4.close)
    rsi = ind.report_start_idx

    active = False
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    current_exposure = 0.0
    cum_rpnl = 0.0  # cumulative rpnl within current trade (partial sells)

    pending_signal = None  # (target_exposure, reason)
    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0
    pending_delay_countdown = 0

    trades: list[Trade] = []

    if skip_entries is None:
        skip_entries = set()

    for i in range(n):
        close_val = h4.close[i]
        open_val = h4.open[i]
        close_time_ms = int(h4.close_time[i])
        mid = open_val  # fill at open

        # --- Fill pending signal ---
        if pending_signal is not None and i > 0:
            target_expo, reason = pending_signal
            pending_signal = None

            nav = cash + btc_qty * mid
            if nav <= 0:
                nav = 1.0

            # Recompute current exposure at fill bar's open (engine does this)
            current_exposure = (btc_qty * mid / nav) if (nav > 0 and btc_qty > 0) else 0.0

            if target_expo < EXPO_THRESHOLD and btc_qty > 0:
                # Close position — sell all
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
            else:
                delta = target_expo - current_exposure
                if delta > EXPO_THRESHOLD:
                    # Buy more
                    buy_value = delta * nav
                    fill_px = mid * BUY_ADJ
                    qty_buy = buy_value / mid  # engine uses mid for qty
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
                    # Sell some (partial rebalance)
                    sell_value = abs(delta) * nav
                    fill_px = mid * SELL_ADJ
                    qty_sell = min(sell_value / mid, btc_qty)  # engine uses mid
                    fee = qty_sell * fill_px * FEE_RATE
                    cum_rpnl += qty_sell * (fill_px - entry_avg) - fee
                    cash += qty_sell * fill_px - fee
                    btc_qty -= qty_sell

                nav_after = cash + btc_qty * mid
                current_exposure = (btc_qty * mid / nav_after) if nav_after > 0 else 0.0

        # --- Delayed entry ---
        if pending_delay_countdown > 0:
            pending_delay_countdown -= 1
            if pending_delay_countdown == 0 and not active:
                rv_val = ind.rv[i]
                if np.isfinite(rv_val):
                    weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                    if weight > 0.0:
                        active = True
                        entry_bar_idx = i
                        pending_signal = (weight, "vtrend_sm_entry")

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

        if not active:
            breakout_ok = close_val > hh
            if regime_ok and breakout_ok:
                should_skip = i in skip_entries
                if blackout_start_ms > 0 and blackout_start_ms <= close_time_ms <= blackout_end_ms:
                    should_skip = True
                if delay_bars > 0 and not should_skip:
                    pending_delay_countdown = delay_bars
                    continue
                if should_skip:
                    continue
                weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                if weight > 0.0:
                    active = True
                    entry_bar_idx = i
                    pending_signal = (weight, "vtrend_sm_entry")
        else:
            exit_floor = max(ll, ema_s - ind.atr_mult * atr_val)
            floor_break = close_val < exit_floor

            if floor_break:
                active = False
                pending_signal = (0.0, "vtrend_sm_floor_exit")
            else:
                new_weight = _clip_weight_sm(ind.target_vol / max(rv_val, EPS), ind.min_weight)
                # Engine computes exposure at bar close, not at fill time
                nav_now = cash + btc_qty * close_val
                expo_now = (btc_qty * close_val / nav_now) if nav_now > 0 else 0.0
                delta = abs(new_weight - expo_now)
                if delta >= ind.min_rebalance_weight_delta - 1e-12:
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
    )


def replay_latch(ind: LatchIndicators, h4: BarData,
                 skip_entries: set[int] | None = None,
                 blackout_start_ms: int = 0, blackout_end_ms: int = 0,
                 delay_bars: int = 0) -> ReplayResult:
    """Replay LATCH with optional entry perturbations."""
    n = len(h4.close)
    rsi = ind.report_start_idx

    # 3-state machine: 0=OFF, 1=ARMED, 2=LONG
    state = 0
    cash = NAV0
    btc_qty = 0.0
    entry_avg = 0.0
    current_exposure = 0.0
    cum_rpnl = 0.0

    pending_signal = None
    entry_bar_idx = -1
    entry_fill_bar_idx = -1
    entry_fill_price = 0.0
    pending_delay_countdown = 0

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

            # Recompute current exposure at fill bar's open
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
            else:
                delta = target_expo - current_exposure
                if delta > EXPO_THRESHOLD:
                    buy_value = delta * nav
                    fill_px = mid * BUY_ADJ
                    qty_buy = buy_value / mid  # engine uses mid
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
                    qty_sell = min(sell_value / mid, btc_qty)  # engine uses mid
                    fee = qty_sell * fill_px * FEE_RATE
                    cum_rpnl += qty_sell * (fill_px - entry_avg) - fee
                    cash += qty_sell * fill_px - fee
                    btc_qty -= qty_sell

                nav_after = cash + btc_qty * mid
                current_exposure = (btc_qty * mid / nav_after) if nav_after > 0 else 0.0

        # --- Delayed entry ---
        if pending_delay_countdown > 0:
            pending_delay_countdown -= 1
            if pending_delay_countdown == 0 and state != 2:
                rv_val = ind.rv[i]
                if np.isfinite(rv_val):
                    rv_i = max(rv_val, ind.vol_floor, EPS)
                    weight = _clip_weight_latch(ind.target_vol / rv_i, ind.max_pos, ind.min_weight)
                    if weight > 0.0:
                        state = 2  # LONG
                        entry_bar_idx = i
                        pending_signal = (weight, "latch_entry")

        if i < max(ind.warmup_end, rsi):
            continue

        ema_s = ind.ema_slow[i]
        atr_val = ind.atr_arr[i]
        hh = ind.hh_entry[i]
        ll = ind.ll_exit[i]
        rv_val = ind.rv[i]
        regime_on = bool(ind.regime_on[i])
        off_trig = bool(ind.off_trigger[i])
        flip_off_val = bool(ind.flip_off[i])

        if not (np.isfinite(ema_s) and np.isfinite(atr_val)
                and np.isfinite(hh) and np.isfinite(ll) and np.isfinite(rv_val)):
            continue

        if state == 0:  # OFF
            if regime_on:
                breakout_ok = close_val > hh
                if breakout_ok:
                    should_skip = i in skip_entries
                    if blackout_start_ms > 0 and blackout_start_ms <= close_time_ms <= blackout_end_ms:
                        should_skip = True
                    if delay_bars > 0 and not should_skip:
                        pending_delay_countdown = delay_bars
                        state = 1  # Stay ARMED while waiting
                        continue
                    if should_skip:
                        state = 1  # ARMED (regime on but entry skipped)
                        continue
                    rv_i = max(rv_val, ind.vol_floor, EPS)
                    weight = _clip_weight_latch(ind.target_vol / rv_i, ind.max_pos, ind.min_weight)
                    if weight > 0.0:
                        state = 2  # LONG
                        entry_bar_idx = i
                        pending_signal = (weight, "latch_entry")
                else:
                    state = 1  # ARMED

        elif state == 1:  # ARMED
            if off_trig:
                state = 0  # OFF
            elif regime_on and (close_val > hh):
                should_skip = i in skip_entries
                if blackout_start_ms > 0 and blackout_start_ms <= close_time_ms <= blackout_end_ms:
                    should_skip = True
                if delay_bars > 0 and not should_skip:
                    pending_delay_countdown = delay_bars
                    continue
                if should_skip:
                    continue
                rv_i = max(rv_val, ind.vol_floor, EPS)
                weight = _clip_weight_latch(ind.target_vol / rv_i, ind.max_pos, ind.min_weight)
                if weight > 0.0:
                    state = 2  # LONG
                    entry_bar_idx = i
                    pending_signal = (weight, "latch_entry")

        elif state == 2:  # LONG
            adaptive_floor = max(ll, ema_s - ind.atr_mult * atr_val)
            floor_break = close_val < adaptive_floor

            if floor_break or flip_off_val:
                state = 0  # OFF
                pending_signal = (0.0, "latch_floor_exit" if floor_break else "latch_regime_exit")
            else:
                rv_i = max(rv_val, ind.vol_floor, EPS)
                weight = _clip_weight_latch(ind.target_vol / rv_i, ind.max_pos, ind.min_weight)
                # Engine computes exposure at bar close
                nav_now = cash + btc_qty * close_val
                expo_now = (btc_qty * close_val / nav_now) if nav_now > 0 else 0.0
                delta_w = abs(weight - expo_now)
                if delta_w >= ind.min_rebalance_weight_delta - 1e-12:
                    pending_signal = (weight, "latch_rebalance")

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
    )


def run_replay(cand: CandidateDef, indicators, h4: BarData, **kwargs) -> ReplayResult:
    """Dispatch to the correct replay function."""
    if cand.variant in ("E0", "E5", "E0_plus", "E5_plus"):
        return replay_binary(indicators, h4, **kwargs)
    elif cand.variant == "SM":
        return replay_sm(indicators, h4, **kwargs)
    elif cand.variant == "LATCH":
        return replay_latch(indicators, h4, **kwargs)
    else:
        raise ValueError(f"Unknown variant: {cand.variant}")


# ===================================================================
# PHASE A: BASELINE REPLAY & REGRESSION
# ===================================================================

def find_entry_bar_indices(result: ReplayResult, h4: BarData) -> list[int]:
    """Extract the bar indices where entry decisions were made."""
    return [t.entry_bar_idx for t in result.trades]


def phase_a_regression(cand: CandidateDef, baseline: ReplayResult,
                       canonical_trades: list[dict],
                       h4: BarData) -> dict:
    """REPLAY_REGRESS: compare baseline replay to canonical trades."""
    is_vol_target = cand.strategy_type == "vol_target"
    checks = {}
    n_replay = len(baseline.trades)
    n_canonical = len(canonical_trades)
    checks["trade_count"] = n_replay == n_canonical
    checks["trade_count_detail"] = f"{n_replay} vs {n_canonical}"

    # Compare entry/exit timestamps
    ts_match = True
    first_mismatch = None
    for j, (rt, ct) in enumerate(zip(baseline.trades, canonical_trades)):
        entry_ok = rt.entry_ts_ms == ct["entry_ts_ms"]
        exit_ok = rt.exit_ts_ms == ct["exit_ts_ms"]
        if not (entry_ok and exit_ok):
            ts_match = False
            if first_mismatch is None:
                first_mismatch = (j, rt.entry_ts_ms, ct["entry_ts_ms"],
                                  rt.exit_ts_ms, ct["exit_ts_ms"])
    checks["entry_exit_timestamps"] = ts_match
    if first_mismatch:
        checks["first_ts_mismatch"] = str(first_mismatch)

    # Compare terminal NAV
    canon_native = NAV0 + sum(t["pnl_usd"] for t in canonical_trades)
    native_diff = abs(baseline.native_terminal - canon_native)
    checks["native_terminal_match"] = native_diff < 1.0  # $1 tolerance
    checks["native_terminal_detail"] = f"replay={baseline.native_terminal:.2f} canonical={canon_native:.2f} diff={native_diff:.2f}"

    canon_unit = NAV0 * np.prod([1 + t["return_pct"]/100 for t in canonical_trades])
    unit_diff = abs(baseline.unit_terminal - canon_unit)
    checks["unit_terminal_match"] = unit_diff < 1.0
    checks["unit_terminal_detail"] = f"replay={baseline.unit_terminal:.2f} canonical={canon_unit:.2f} diff={unit_diff:.2f}"

    # For vol-target strategies (SM/LATCH), unit_terminal per-trade VWAP splits
    # can differ while total cash flow is bit-identical. Native terminal is binding.
    binding_keys = {"trade_count", "entry_exit_timestamps", "native_terminal_match"}
    if not is_vol_target:
        binding_keys.add("unit_terminal_match")

    all_pass = all(
        checks.get(k, False) for k in binding_keys
    )
    checks["all_pass"] = all_pass
    if is_vol_target:
        checks["note"] = "vol_target: unit_terminal informational (per-trade VWAP splits differ for rebalancing trades)"
    return checks


# ===================================================================
# PHASE B: RANDOM MISSED-ENTRY MONTE CARLO
# ===================================================================

def phase_b_random_miss(cand: CandidateDef, indicators, h4: BarData,
                        baseline: ReplayResult, entry_indices: list[int]) -> dict:
    """Run random-miss Monte Carlo for K={1,2,3}, 2000 draws each."""
    rng = np.random.RandomState(SEED)
    n_entries = len(entry_indices)
    results = {}

    for K in K_VALUES:
        if K > n_entries:
            results[K] = {"skipped": True, "reason": f"K={K} > n_entries={n_entries}"}
            continue

        draws = []
        for draw_idx in range(N_DRAWS):
            chosen = rng.choice(n_entries, size=K, replace=False)
            skip_set = set(entry_indices[c] for c in chosen)
            r = run_replay(cand, indicators, h4, skip_entries=skip_set)
            draws.append({
                "n_trades": len(r.trades),
                "native_terminal": r.native_terminal,
                "unit_terminal": r.unit_terminal,
                "sharpe": r.sharpe,
                "cagr_native": r.cagr_native,
                "cagr_unit": r.cagr_unit,
                "skipped_indices": [int(entry_indices[c]) for c in chosen],
            })

        sharpes = np.array([d["sharpe"] for d in draws])
        cagrs_n = np.array([d["cagr_native"] for d in draws])
        cagrs_u = np.array([d["cagr_unit"] for d in draws])
        n_trades_arr = np.array([d["n_trades"] for d in draws])

        results[K] = {
            "n_draws": N_DRAWS,
            "n_entries": n_entries,
            "sharpe_mean": float(np.mean(sharpes)),
            "sharpe_std": float(np.std(sharpes, ddof=0)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p50": float(np.percentile(sharpes, 50)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
            "cagr_native_mean": float(np.mean(cagrs_n)),
            "cagr_native_p5": float(np.percentile(cagrs_n, 5)),
            "cagr_unit_mean": float(np.mean(cagrs_u)),
            "cagr_unit_p5": float(np.percentile(cagrs_u, 5)),
            "n_trades_mean": float(np.mean(n_trades_arr)),
            "n_trades_min": int(np.min(n_trades_arr)),
            "n_trades_max": int(np.max(n_trades_arr)),
            "pct_sharpe_positive": float(np.mean(sharpes > 0) * 100),
            "pct_cagr_native_positive": float(np.mean(cagrs_n > 0) * 100),
            "baseline_sharpe": baseline.sharpe,
            "baseline_cagr_native": baseline.cagr_native,
            "draws": draws,
        }

    return results


# ===================================================================
# PHASE C: OUTAGE-WINDOW ENTRY-BLACKOUT SWEEP
# ===================================================================

def phase_c_outage_sweep(cand: CandidateDef, indicators, h4: BarData,
                         baseline: ReplayResult,
                         entry_indices: list[int]) -> dict:
    """Sweep outage windows of {24,72,168}h, every H4 bar as start."""
    entry_close_times = set()
    for idx in entry_indices:
        entry_close_times.add(int(h4.close_time[idx]))

    results = {}
    rsi = baseline.trades[0].entry_bar_idx if baseline.trades else 0

    for W_hours in OUTAGE_HOURS:
        W_ms = W_hours * 3600_000
        window_results = []

        # Get all H4 bar close times in the report period
        report_cts = []
        for i in range(len(h4.close_time)):
            ct = int(h4.close_time[i])
            if ct >= PERIOD_START_MS and ct <= PERIOD_END_MS:
                report_cts.append((i, ct))

        # Optimization: only replay windows that overlap at least one entry
        for start_i, start_ct in report_cts:
            end_ct = start_ct + W_ms
            overlaps_entry = any(
                start_ct <= int(h4.close_time[idx]) <= end_ct
                for idx in entry_indices
            )
            if not overlaps_entry:
                continue

            r = run_replay(cand, indicators, h4,
                           blackout_start_ms=start_ct, blackout_end_ms=end_ct)
            window_results.append({
                "window_start_ms": start_ct,
                "window_end_ms": end_ct,
                "n_trades": len(r.trades),
                "native_terminal": r.native_terminal,
                "unit_terminal": r.unit_terminal,
                "sharpe": r.sharpe,
                "cagr_native": r.cagr_native,
                "cagr_unit": r.cagr_unit,
                "delta_sharpe": r.sharpe - baseline.sharpe,
                "delta_cagr_native": r.cagr_native - baseline.cagr_native,
                "n_entries_blocked": sum(
                    1 for idx in entry_indices
                    if start_ct <= int(h4.close_time[idx]) <= end_ct
                ),
            })

        # Sort by worst delta_sharpe
        window_results.sort(key=lambda x: x["delta_sharpe"])

        sharpes = np.array([w["sharpe"] for w in window_results]) if window_results else np.array([baseline.sharpe])
        cagrs = np.array([w["cagr_native"] for w in window_results]) if window_results else np.array([baseline.cagr_native])

        results[W_hours] = {
            "n_windows_tested": len(window_results),
            "sharpe_mean": float(np.mean(sharpes)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_worst": float(np.min(sharpes)),
            "cagr_native_mean": float(np.mean(cagrs)),
            "cagr_native_worst": float(np.min(cagrs)),
            "baseline_sharpe": baseline.sharpe,
            "baseline_cagr_native": baseline.cagr_native,
            "worst_20": window_results[:20],
        }

    return results


# ===================================================================
# PHASE D: DELAYED ENTRY
# ===================================================================

def phase_d_delayed_entry(cand: CandidateDef, indicators, h4: BarData,
                          baseline: ReplayResult) -> dict:
    """Run delayed-entry replay for {1,2,3,4} bars."""
    results = {}
    for D in DELAY_BARS:
        r = run_replay(cand, indicators, h4, delay_bars=D)
        results[D] = {
            "n_trades": len(r.trades),
            "native_terminal": r.native_terminal,
            "unit_terminal": r.unit_terminal,
            "sharpe": r.sharpe,
            "cagr_native": r.cagr_native,
            "cagr_unit": r.cagr_unit,
            "delta_sharpe": r.sharpe - baseline.sharpe,
            "delta_cagr_native": r.cagr_native - baseline.cagr_native,
            "delta_n_trades": len(r.trades) - len(baseline.trades),
            "baseline_sharpe": baseline.sharpe,
            "baseline_cagr_native": baseline.cagr_native,
        }
    return results


# ===================================================================
# PHASE E: SYNTHESIS
# ===================================================================

def compute_fragility_score(baseline: ReplayResult,
                            miss_results: dict,
                            outage_results: dict,
                            delay_results: dict) -> dict:
    """Compute composite fragility score for a candidate."""
    scores = {}

    # Miss fragility: how much does missing K=1 entry affect Sharpe?
    if 1 in miss_results and "sharpe_std" in miss_results[1]:
        scores["miss_k1_sharpe_cv"] = (
            miss_results[1]["sharpe_std"] / abs(baseline.sharpe)
            if baseline.sharpe != 0 else float("inf")
        )
        scores["miss_k1_sharpe_p5"] = miss_results[1]["sharpe_p5"]
        scores["miss_k1_sharpe_mean"] = miss_results[1]["sharpe_mean"]
    if 3 in miss_results and "sharpe_std" in miss_results[3]:
        scores["miss_k3_sharpe_p5"] = miss_results[3]["sharpe_p5"]

    # Outage fragility: worst-case 168h window
    if 168 in outage_results:
        scores["outage_168h_sharpe_worst"] = outage_results[168]["sharpe_worst"]
        scores["outage_168h_sharpe_p5"] = outage_results[168]["sharpe_p5"]

    # Delay fragility
    if 1 in delay_results:
        scores["delay_1_delta_sharpe"] = delay_results[1]["delta_sharpe"]
    if 4 in delay_results:
        scores["delay_4_delta_sharpe"] = delay_results[4]["delta_sharpe"]

    scores["baseline_sharpe"] = baseline.sharpe
    scores["baseline_cagr_native"] = baseline.cagr_native

    return scores


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
                                  regression: dict,
                                  miss_results: dict,
                                  outage_results: dict,
                                  delay_results: dict,
                                  fragility: dict):
    """Write 10 per-candidate artifacts."""
    cdir = ARTIFACT_DIR / cand.label
    cdir.mkdir(parents=True, exist_ok=True)

    # 1. replay_regress.json
    write_json(cdir / "replay_regress.json", regression)

    # 2. baseline_trades.csv
    rows = []
    for t in baseline.trades:
        rows.append({
            "entry_bar_idx": t.entry_bar_idx,
            "entry_fill_bar_idx": t.entry_fill_bar_idx,
            "entry_ts_ms": t.entry_ts_ms,
            "exit_ts_ms": t.exit_ts_ms,
            "entry_fill_price": f"{t.entry_fill_price:.6f}",
            "exit_fill_price": f"{t.exit_fill_price:.6f}",
            "qty": f"{t.qty:.8f}",
            "return_pct": f"{t.return_pct:.6f}",
            "pnl_usd": f"{t.pnl_usd:.6f}",
        })
    write_csv(cdir / "baseline_trades.csv", rows)

    # 3. random_miss_summary.json (without raw draws)
    miss_summary = {}
    for K in K_VALUES:
        if K in miss_results:
            d = {k: v for k, v in miss_results[K].items() if k != "draws"}
            miss_summary[str(K)] = d
    write_json(cdir / "random_miss_summary.json", miss_summary)

    # 4. random_miss_draws_k1.csv (top 20 worst + top 20 best by Sharpe)
    if 1 in miss_results and "draws" in miss_results[1]:
        draws = miss_results[1]["draws"]
        sorted_draws = sorted(draws, key=lambda x: x["sharpe"])
        worst20 = sorted_draws[:20]
        best20 = sorted_draws[-20:]
        rows_w = []
        for rank, d in enumerate(worst20):
            rows_w.append({
                "rank": rank + 1, "type": "worst",
                "n_trades": d["n_trades"],
                "sharpe": f"{d['sharpe']:.6f}",
                "cagr_native": f"{d['cagr_native']:.6f}",
                "skipped": str(d["skipped_indices"]),
            })
        for rank, d in enumerate(best20):
            rows_w.append({
                "rank": rank + 1, "type": "best",
                "n_trades": d["n_trades"],
                "sharpe": f"{d['sharpe']:.6f}",
                "cagr_native": f"{d['cagr_native']:.6f}",
                "skipped": str(d["skipped_indices"]),
            })
        write_csv(cdir / "random_miss_draws_k1.csv", rows_w)

    # 5. outage_summary.json
    outage_summary = {}
    for W in OUTAGE_HOURS:
        if W in outage_results:
            d = {k: v for k, v in outage_results[W].items() if k != "worst_20"}
            outage_summary[str(W)] = d
    write_json(cdir / "outage_summary.json", outage_summary)

    # 6. outage_worst20.csv (168h)
    if 168 in outage_results and outage_results[168].get("worst_20"):
        rows = []
        for rank, w in enumerate(outage_results[168]["worst_20"]):
            rows.append({
                "rank": rank + 1,
                "window_start_ms": w["window_start_ms"],
                "n_entries_blocked": w["n_entries_blocked"],
                "n_trades": w["n_trades"],
                "sharpe": f"{w['sharpe']:.6f}",
                "delta_sharpe": f"{w['delta_sharpe']:.6f}",
                "cagr_native": f"{w['cagr_native']:.6f}",
            })
        write_csv(cdir / "outage_worst20_168h.csv", rows)

    # 7. delay_summary.json
    write_json(cdir / "delay_summary.json", delay_results)

    # 8. fragility_scores.json
    write_json(cdir / "fragility_scores.json", fragility)


def write_cross_strategy_artifacts(all_results: dict):
    """Write root-level cross-strategy artifacts."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. replay_regress_summary.csv
    rows = []
    for label, r in all_results.items():
        reg = r["regression"]
        rows.append({
            "candidate": label,
            "trade_count_match": reg["trade_count"],
            "timestamps_match": reg["entry_exit_timestamps"],
            "native_terminal_match": reg["native_terminal_match"],
            "unit_terminal_match": reg["unit_terminal_match"],
            "all_pass": reg["all_pass"],
        })
    write_csv(ARTIFACT_DIR / "replay_regress_summary.csv", rows)

    # 2. random_miss_cross_summary.csv
    rows = []
    for label, r in all_results.items():
        for K in K_VALUES:
            miss = r["miss_results"].get(K, {})
            if "skipped" in miss:
                continue
            rows.append({
                "candidate": label,
                "K": K,
                "baseline_sharpe": f"{r['baseline'].sharpe:.6f}",
                "sharpe_mean": f"{miss.get('sharpe_mean', 0):.6f}",
                "sharpe_p5": f"{miss.get('sharpe_p5', 0):.6f}",
                "sharpe_p95": f"{miss.get('sharpe_p95', 0):.6f}",
                "cagr_native_mean": f"{miss.get('cagr_native_mean', 0):.6f}",
                "cagr_native_p5": f"{miss.get('cagr_native_p5', 0):.6f}",
                "pct_sharpe_positive": f"{miss.get('pct_sharpe_positive', 0):.1f}",
                "n_trades_mean": f"{miss.get('n_trades_mean', 0):.1f}",
            })
    write_csv(ARTIFACT_DIR / "random_miss_cross_summary.csv", rows)

    # 3. outage_cross_summary.csv
    rows = []
    for label, r in all_results.items():
        for W in OUTAGE_HOURS:
            out = r["outage_results"].get(W, {})
            rows.append({
                "candidate": label,
                "window_hours": W,
                "baseline_sharpe": f"{r['baseline'].sharpe:.6f}",
                "n_windows_tested": out.get("n_windows_tested", 0),
                "sharpe_mean": f"{out.get('sharpe_mean', 0):.6f}",
                "sharpe_p5": f"{out.get('sharpe_p5', 0):.6f}",
                "sharpe_worst": f"{out.get('sharpe_worst', 0):.6f}",
                "cagr_native_worst": f"{out.get('cagr_native_worst', 0):.6f}",
            })
    write_csv(ARTIFACT_DIR / "outage_cross_summary.csv", rows)

    # 4. delay_cross_summary.csv
    rows = []
    for label, r in all_results.items():
        for D in DELAY_BARS:
            dl = r["delay_results"].get(D, {})
            rows.append({
                "candidate": label,
                "delay_bars": D,
                "baseline_sharpe": f"{r['baseline'].sharpe:.6f}",
                "sharpe": f"{dl.get('sharpe', 0):.6f}",
                "delta_sharpe": f"{dl.get('delta_sharpe', 0):.6f}",
                "cagr_native": f"{dl.get('cagr_native', 0):.6f}",
                "delta_cagr_native": f"{dl.get('delta_cagr_native', 0):.6f}",
                "delta_n_trades": dl.get("delta_n_trades", 0),
            })
    write_csv(ARTIFACT_DIR / "delay_cross_summary.csv", rows)

    # 5. fragility_cross_summary.csv
    rows = []
    for label, r in all_results.items():
        frag = r["fragility"]
        row = {"candidate": label}
        for k, v in frag.items():
            row[k] = f"{v:.6f}" if isinstance(v, float) else v
        rows.append(row)
    write_csv(ARTIFACT_DIR / "fragility_cross_summary.csv", rows)

    # 6. step3_summary.json
    summary = {
        "step": 3,
        "phase": "replay_fragility",
        "seed": SEED,
        "n_draws": N_DRAWS,
        "K_values": K_VALUES,
        "outage_hours": OUTAGE_HOURS,
        "delay_bars": DELAY_BARS,
        "nav0": NAV0,
        "backtest_years": BACKTEST_YEARS,
        "fee_model": "harsh_50bps_rt",
        "period": f"{PERIOD_START_MS} to {PERIOD_END_MS}",
        "candidates": {},
    }
    for label, r in all_results.items():
        summary["candidates"][label] = {
            "replay_regress_pass": r["regression"]["all_pass"],
            "baseline_sharpe": r["baseline"].sharpe,
            "baseline_cagr_native": r["baseline"].cagr_native,
            "baseline_n_trades": len(r["baseline"].trades),
            "miss_k1_sharpe_p5": r["fragility"].get("miss_k1_sharpe_p5"),
            "outage_168h_sharpe_worst": r["fragility"].get("outage_168h_sharpe_worst"),
            "delay_4_delta_sharpe": r["fragility"].get("delay_4_delta_sharpe"),
        }
    write_json(ARTIFACT_DIR / "step3_summary.json", summary)


def write_pairwise_comparisons(all_results: dict):
    """Write pairwise replay comparison artifacts."""
    pairs = [
        ("SM", "LATCH"),
        ("E0", "E0_plus_EMA1D21"),
        ("E5", "E5_plus_EMA1D21"),
    ]
    rows = []
    for a_label, b_label in pairs:
        a = all_results.get(a_label, {})
        b = all_results.get(b_label, {})
        if not a or not b:
            continue

        fa = a["fragility"]
        fb = b["fragility"]

        row = {
            "pair": f"{a_label} vs {b_label}",
            "a_baseline_sharpe": f"{a['baseline'].sharpe:.6f}",
            "b_baseline_sharpe": f"{b['baseline'].sharpe:.6f}",
        }

        # Compare miss K=1 p5
        for metric in ["miss_k1_sharpe_p5", "miss_k1_sharpe_cv",
                        "outage_168h_sharpe_worst", "delay_4_delta_sharpe"]:
            va = fa.get(metric, float("nan"))
            vb = fb.get(metric, float("nan"))
            row[f"a_{metric}"] = f"{va:.6f}" if isinstance(va, float) else str(va)
            row[f"b_{metric}"] = f"{vb:.6f}" if isinstance(vb, float) else str(vb)

        rows.append(row)

    write_csv(ARTIFACT_DIR / "pairwise_replay_comparisons.csv", rows)


# ===================================================================
# PLOTTING
# ===================================================================

def write_plots(all_results: dict):
    """Write 4 PNG plots."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("WARNING: matplotlib not available, skipping plots")
        return

    labels = list(all_results.keys())
    n_cands = len(labels)

    # 1. Random miss K=1 Sharpe distribution
    fig, axes = plt.subplots(1, n_cands, figsize=(4 * n_cands, 4), sharey=True)
    if n_cands == 1:
        axes = [axes]
    for ax, label in zip(axes, labels):
        r = all_results[label]
        if 1 in r["miss_results"] and "draws" in r["miss_results"][1]:
            sharpes = [d["sharpe"] for d in r["miss_results"][1]["draws"]]
            ax.hist(sharpes, bins=50, alpha=0.7, color="steelblue")
            ax.axvline(r["baseline"].sharpe, color="red", linestyle="--", label="baseline")
            ax.set_title(label, fontsize=10)
            ax.set_xlabel("Sharpe")
    fig.suptitle("Random Miss K=1: Sharpe Distribution", fontsize=12)
    fig.tight_layout()
    fig.savefig(ARTIFACT_DIR / "random_miss_k1_sharpe_dist.png", dpi=150)
    plt.close(fig)

    # 2. Delay degradation
    fig, ax = plt.subplots(figsize=(8, 5))
    for label in labels:
        r = all_results[label]
        delays = sorted(r["delay_results"].keys())
        sharpes = [r["delay_results"][d]["sharpe"] for d in delays]
        ax.plot([0] + delays, [r["baseline"].sharpe] + sharpes, marker="o", label=label)
    ax.set_xlabel("Delay (bars)")
    ax.set_ylabel("Sharpe")
    ax.set_title("Delayed Entry: Sharpe Degradation")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(ARTIFACT_DIR / "delay_sharpe_degradation.png", dpi=150)
    plt.close(fig)

    # 3. Outage worst-case Sharpe by window size
    fig, ax = plt.subplots(figsize=(8, 5))
    for label in labels:
        r = all_results[label]
        ws = sorted(r["outage_results"].keys())
        worst_sharpes = [r["outage_results"][w]["sharpe_worst"] for w in ws]
        ax.plot(ws, worst_sharpes, marker="s", label=label)
    ax.set_xlabel("Outage Window (hours)")
    ax.set_ylabel("Worst-case Sharpe")
    ax.set_title("Outage Window: Worst-case Sharpe")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(ARTIFACT_DIR / "outage_worst_sharpe.png", dpi=150)
    plt.close(fig)

    # 4. Fragility spider/bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    metrics = ["miss_k1_sharpe_cv", "delay_4_delta_sharpe"]
    x = np.arange(len(labels))
    width = 0.35
    for j, metric in enumerate(metrics):
        vals = []
        for label in labels:
            v = all_results[label]["fragility"].get(metric, 0)
            vals.append(abs(v) if isinstance(v, float) else 0)
        ax.bar(x + j * width, vals, width, label=metric)
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Magnitude")
    ax.set_title("Fragility Indicators")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ARTIFACT_DIR / "fragility_indicators.png", dpi=150)
    plt.close(fig)


# ===================================================================
# MAIN
# ===================================================================

def main():
    t0 = time.time()
    print("=" * 60)
    print("STEP 3: Replay-Dependent Operational Fragility Audit")
    print("=" * 60)

    # --- Load data ---
    print("\nLoading bar data...")
    h4, d1, report_start_idx = load_bars()
    print(f"  H4 bars: {len(h4.close)}, D1 bars: {len(d1.close)}")
    print(f"  Report start index: {report_start_idx}")

    all_results = {}

    for cand in CANDIDATES:
        tc = time.time()
        print(f"\n{'─' * 50}")
        print(f"Candidate: {cand.label} (variant={cand.variant}, expected={cand.expected_trade_count} trades)")
        print(f"{'─' * 50}")

        # --- Precompute indicators ---
        print("  Precomputing indicators...")
        indicators = precompute_indicators(cand.variant, h4, d1, report_start_idx)

        # --- Load canonical trades ---
        canonical = load_canonical_trades(cand.trade_csv)
        print(f"  Canonical trades loaded: {len(canonical)}")

        # --- Phase A: Baseline ---
        print("  Phase A: Running baseline replay...")
        baseline = run_replay(cand, indicators, h4)
        print(f"    Baseline: {len(baseline.trades)} trades, Sharpe={baseline.sharpe:.4f}, "
              f"CAGR_native={baseline.cagr_native:.4f}")

        regression = phase_a_regression(cand, baseline, canonical, h4)
        regress_status = "PASS" if regression["all_pass"] else "FAIL"
        print(f"    REPLAY_REGRESS: {regress_status}")
        if not regression["all_pass"]:
            for k, v in regression.items():
                if isinstance(v, bool) and not v and not k.endswith("_detail"):
                    detail_key = k + "_detail"
                    detail = regression.get(detail_key, "")
                    print(f"      FAIL: {k} — {detail}")

        entry_indices = find_entry_bar_indices(baseline, h4)

        # --- Phase B: Random Miss ---
        print(f"  Phase B: Random miss Monte Carlo (K={K_VALUES}, {N_DRAWS} draws)...")
        miss_results = phase_b_random_miss(cand, indicators, h4, baseline, entry_indices)
        for K in K_VALUES:
            if K in miss_results and "sharpe_mean" in miss_results[K]:
                m = miss_results[K]
                print(f"    K={K}: Sharpe mean={m['sharpe_mean']:.4f}, "
                      f"p5={m['sharpe_p5']:.4f}, p95={m['sharpe_p95']:.4f}")

        # --- Phase C: Outage ---
        print(f"  Phase C: Outage sweep ({OUTAGE_HOURS}h)...")
        outage_results = phase_c_outage_sweep(cand, indicators, h4, baseline, entry_indices)
        for W in OUTAGE_HOURS:
            if W in outage_results:
                o = outage_results[W]
                print(f"    W={W}h: {o['n_windows_tested']} windows, "
                      f"Sharpe worst={o['sharpe_worst']:.4f}, mean={o['sharpe_mean']:.4f}")

        # --- Phase D: Delay ---
        print(f"  Phase D: Delayed entry ({DELAY_BARS} bars)...")
        delay_results = phase_d_delayed_entry(cand, indicators, h4, baseline)
        for D in DELAY_BARS:
            dl = delay_results[D]
            print(f"    D={D}: Sharpe={dl['sharpe']:.4f}, "
                  f"delta={dl['delta_sharpe']:.4f}, n_trades={dl['n_trades']}")

        # --- Fragility scores ---
        fragility = compute_fragility_score(baseline, miss_results, outage_results, delay_results)

        # --- Write per-candidate artifacts ---
        write_per_candidate_artifacts(cand, baseline, regression,
                                      miss_results, outage_results,
                                      delay_results, fragility)

        all_results[cand.label] = {
            "baseline": baseline,
            "regression": regression,
            "miss_results": miss_results,
            "outage_results": outage_results,
            "delay_results": delay_results,
            "fragility": fragility,
            "entry_indices": entry_indices,
        }

        elapsed = time.time() - tc
        print(f"  Candidate {cand.label} done in {elapsed:.1f}s")

    # --- Cross-strategy artifacts ---
    print(f"\n{'=' * 60}")
    print("Phase E: Cross-strategy synthesis")
    print(f"{'=' * 60}")

    write_cross_strategy_artifacts(all_results)
    write_pairwise_comparisons(all_results)
    write_plots(all_results)

    # --- Final summary ---
    total = time.time() - t0
    print(f"\nTotal elapsed: {total:.1f}s")
    print(f"\nArtifacts written to: {ARTIFACT_DIR}")

    # PASS/FAIL
    all_regress_pass = all(
        r["regression"]["all_pass"] for r in all_results.values()
    )
    print(f"\nREPLAY_REGRESS all candidates: {'PASS' if all_regress_pass else 'FAIL'}")

    print("\n" + "=" * 60)
    print("STOPPED AFTER STEP 3")
    print("=" * 60)

    return 0 if all_regress_pass else 1


if __name__ == "__main__":
    sys.exit(main())
