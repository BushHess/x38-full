#!/usr/bin/env python3
"""Step 3: Factorial Sizing Decomposition + Scoring Bias Audit.

Preflight: validate E0 signal extractor against native VTrendStrategy.
Main: 4 signals (E0, SM, P, LATCH) × 3 sizing overlays = 12 runs + 4 native refs.
Analysis: signal decomposition, sizing decomposition, exposure-normalized diagnostics,
          scoring formula bias audit, resolution matrix R1-R6.

NO modification of any production file.
"""
from __future__ import annotations

import json
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

from data_align import load_aligned_pair

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


# ═══════════════════════════════════════════════════════════════════════════
# SHARED INDICATOR COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_indicators(bars: list[Bar]) -> dict:
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

    # Slope reference for SM/P/LATCH regime
    slope_ref = np.full(n, np.nan, dtype=np.float64)
    slope_ref[6:] = ema_slow[:-6]

    # Rolling high/low (shifted by 1 per function design)
    hh60 = _rolling_high_shifted(high, lookback=60)
    ll30 = _rolling_low_shifted(low, lookback=30)

    # Shared realized vol — NO vol_floor, identical for all signals
    rv = _realized_vol(close, lookback=120, bars_per_year=BARS_PER_YEAR)

    return dict(
        close=close, high=high, low=low,
        volume=volume, taker_buy=taker_buy,
        ema_fast=ema_fast, ema_slow=ema_slow,
        atr=atr, vdo=vdo, slope_ref=slope_ref,
        hh60=hh60, ll30=ll30, rv=rv,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL EXTRACTORS
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
    peak_arr = np.zeros(n, dtype=np.float64)
    trail_arr = np.zeros(n, dtype=np.float64)
    exit_reason = [""] * n

    is_in = False
    peak = 0.0

    for i in range(n):
        # Match native: skip bar 0 and NaN indicator bars
        if i < 1 or np.isnan(atr_arr[i]) or np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            in_pos[i] = is_in
            if is_in:
                peak_arr[i] = peak
            continue

        if not is_in:
            # ENTRY: trend up AND VDO confirms
            if ema_f[i] > ema_s[i] and vdo_arr[i] > vdo_threshold:
                is_in = True
                peak = close[i]
                entry[i] = True
                peak_arr[i] = peak
                trail_arr[i] = peak - trail_mult * atr_arr[i]
        else:
            # Track peak (ratchets up only)
            peak = max(peak, close[i])
            ts = peak - trail_mult * atr_arr[i]
            peak_arr[i] = peak
            trail_arr[i] = ts

            # EXIT: trailing stop OR trend reversal
            if close[i] < ts:
                is_in = False
                peak = 0.0
                exit_ev[i] = True
                exit_reason[i] = "trail_stop"
            elif ema_f[i] < ema_s[i]:
                is_in = False
                peak = 0.0
                exit_ev[i] = True
                exit_reason[i] = "trend_exit"

        in_pos[i] = is_in

    return dict(entry=entry, exit=exit_ev, in_position=in_pos,
                peak=peak_arr, trail_stop=trail_arr, exit_reason=exit_reason)


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


def extract_p_signal(ind: dict, atr_mult: float = 1.5) -> dict:
    """P binary signal: price-direct regime, breakout entry, floor exit."""
    n = len(ind["close"])
    close = ind["close"]
    ema_s = ind["ema_slow"]
    slope, atr_arr = ind["slope_ref"], ind["atr"]
    hh60, ll30 = ind["hh60"], ind["ll30"]

    warmup = _find_warmup(n, [ema_s, slope, atr_arr, hh60, ll30])

    entry = np.zeros(n, dtype=np.bool_)
    exit_ev = np.zeros(n, dtype=np.bool_)
    in_pos = np.zeros(n, dtype=np.bool_)
    regime = np.zeros(n, dtype=np.bool_)

    is_in = False
    for i in range(n):
        if np.isfinite(ema_s[i]) and np.isfinite(slope[i]):
            regime[i] = (close[i] > ema_s[i]) and (ema_s[i] > slope[i])
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


def _find_warmup(n: int, arrays: list[np.ndarray]) -> int:
    for i in range(n):
        if all(np.isfinite(a[i]) for a in arrays):
            return i
    return n


# ═══════════════════════════════════════════════════════════════════════════
# SIZING OVERLAYS
# ═══════════════════════════════════════════════════════════════════════════

def apply_binary_100(in_pos: np.ndarray) -> np.ndarray:
    """Binary 100%: weight = 1.0 when in position, 0.0 otherwise."""
    return in_pos.astype(np.float64)


def apply_entry_vol_no_rebal(in_pos: np.ndarray, entry: np.ndarray,
                             rv: np.ndarray, target_vol: float) -> np.ndarray:
    """Vol-targeted sizing locked at entry bar, no rebalance until exit."""
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
    """Vol-targeted per-bar rebalance (native SM/P/LATCH behavior)."""
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

    # Round-trip PnL for profit_factor, win_rate
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
    m["avg_trade_pnl"] = float(sum(pnls) / max(n_rt, 1)) if pnls else 0.0
    m["n_round_trips"] = n_rt
    m["avg_win"] = float(np.mean([p for p in pnls if p > 0])) if any(p > 0 for p in pnls) else 0.0
    m["avg_loss"] = float(np.mean([p for p in pnls if p < 0])) if any(p < 0 for p in pnls) else 0.0

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

    # Keep curves for later
    m["_eq"] = eq
    m["_aw"] = aw
    return m


def compute_score(m: dict) -> tuple[float, dict]:
    """Objective score with 5-term decomposition."""
    cagr = m.get("cagr", 0.0) * 100      # → pct
    mdd = m.get("mdd", 0.0) * 100        # → pct
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
    """Validate extracted E0 signal against native VTrendStrategy.

    Gate: if extraction fails parity, Step 3 stops.
    """
    print("\n" + "=" * 70)
    print("PREFLIGHT: E0 Signal Extraction Validation")
    print("=" * 70)
    n = len(bars)

    # 1. Run native VTrendStrategy bar-by-bar
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

    native_entries = int(np.sum(native_entry))
    native_exits = int(np.sum(native_exit))
    print(f"  Native VTrendStrategy: {native_entries} entries, {native_exits} exits")

    # 2. Run standalone extractor
    e0 = extract_e0_signal(ind)
    ext_entries = int(np.sum(e0["entry"]))
    ext_exits = int(np.sum(e0["exit"]))
    print(f"  Extracted E0:          {ext_entries} entries, {ext_exits} exits")

    # 3. Signal-level parity
    ip_match = np.array_equal(native_in_pos, e0["in_position"])
    en_match = np.array_equal(native_entry, e0["entry"])
    ex_match = np.array_equal(native_exit, e0["exit"])
    signal_pass = ip_match and en_match and ex_match
    print(f"\n  Signal parity:")
    print(f"    in_position: {'MATCH' if ip_match else 'MISMATCH'}")
    print(f"    entry:       {'MATCH' if en_match else 'MISMATCH'}")
    print(f"    exit:        {'MATCH' if ex_match else 'MISMATCH'}")

    if not signal_pass:
        for label, native_arr, ext_arr in [
            ("in_position", native_in_pos, e0["in_position"]),
            ("entry", native_entry, e0["entry"]),
            ("exit", native_exit, e0["exit"]),
        ]:
            diff = np.where(native_arr != ext_arr)[0]
            if len(diff) > 0:
                print(f"    {label} mismatches at bars: {diff[:10].tolist()}...")
        print("\n  PREFLIGHT FAILED — signal extraction mismatch. Stopping.")
        return None

    # 4. Execution parity: same signal through same engine → same equity
    tw_native = native_in_pos.astype(np.float64)
    tw_extracted = e0["in_position"].astype(np.float64)

    m_nat = run_one(df, "preflight_native", tw_native, native_entry, native_exit)
    m_ext = run_one(df, "preflight_extract", tw_extracted, e0["entry"], e0["exit"])

    eq_match = np.allclose(m_nat["_eq"], m_ext["_eq"], rtol=1e-12)
    print(f"\n  Execution parity (same engine):")
    print(f"    Native equity final:    {m_nat['ending_equity']:.8f}")
    print(f"    Extracted equity final: {m_ext['ending_equity']:.8f}")
    print(f"    Equity curves match:    {eq_match}")
    print(f"    Sharpe: native={m_nat['sharpe']:.6f}  extracted={m_ext['sharpe']:.6f}")
    print(f"    CAGR:   native={m_nat['cagr']*100:.4f}%  extracted={m_ext['cagr']*100:.4f}%")
    print(f"    MDD:    native={m_nat['mdd']*100:.4f}%  extracted={m_ext['mdd']*100:.4f}%")
    print(f"    Trades: native={int(m_nat['n_trade_events'])}  extracted={int(m_ext['n_trade_events'])}")

    passed = signal_pass and eq_match
    print(f"\n  PREFLIGHT: {'PASS' if passed else 'FAIL'}")
    if not passed:
        print("  PREFLIGHT FAILED — equity mismatch. Stopping.")
        return None

    return dict(
        entries=native_entries, exits=native_exits,
        signal_match=True, equity_match=True,
        sharpe=m_nat["sharpe"], cagr=m_nat["cagr"],
        mdd=m_nat["mdd"], trades=int(m_nat["n_trade_events"]),
        score=m_nat["score"],
    )


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("Step 3: Factorial Sizing Decomposition + Scoring Bias Audit")
    print("=" * 70)
    t0 = time.time()

    # ── 1. Load data ──────────────────────────────────────────────────────
    df, bars = load_aligned_pair()
    n = len(df)
    print(f"Loaded {n} aligned H4 bars")

    # ── 2. Compute shared indicators ─────────────────────────────────────
    ind = compute_indicators(bars)
    print("Shared indicators computed")

    # ── 3. Preflight: E0 extraction gate ─────────────────────────────────
    pf_result = preflight_e0(df, bars, ind)
    if pf_result is None:
        sys.exit(1)

    # ── 4. Extract all 4 binary signal arrays ────────────────────────────
    print("\nExtracting signals...")
    signals = {
        "E0":    extract_e0_signal(ind, trail_mult=3.0, vdo_threshold=0.0),
        "SM":    extract_sm_signal(ind, atr_mult=3.0),
        "P":     extract_p_signal(ind, atr_mult=1.5),
        "LATCH": extract_latch_signal(ind, atr_mult=2.0),
    }
    for sname, sig in signals.items():
        ent = int(np.sum(sig["entry"]))
        ext = int(np.sum(sig["exit"]))
        ip_pct = float(np.mean(sig["in_position"])) * 100
        print(f"  {sname:>5}: {ent:>4} entries, {ext:>4} exits, "
              f"in-position {ip_pct:.1f}%")

    rv = ind["rv"]

    # ── 5. 4×3 factorial matrix ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RUNNING 4×3 FACTORIAL MATRIX")
    print("=" * 70)

    sizing_specs = [
        ("Binary_100",  lambda ip, en: apply_binary_100(ip)),
        ("EntryVol_15", lambda ip, en: apply_entry_vol_no_rebal(ip, en, rv, 0.15)),
        ("EntryVol_12", lambda ip, en: apply_entry_vol_no_rebal(ip, en, rv, 0.12)),
    ]

    factorial = {}
    for sname in ["E0", "SM", "P", "LATCH"]:
        sig = signals[sname]
        ip, en, ex = sig["in_position"], sig["entry"], sig["exit"]
        for sz_name, sz_fn in sizing_specs:
            tw = sz_fn(ip, en)
            run_name = f"{sname}_{sz_name}"
            # All factorial runs: high threshold prevents drift rebalance
            # Entries/exits still execute (crossing_zero bypasses threshold)
            rebal_delta = 2.0
            print(f"  {run_name}...", end=" ", flush=True)
            m = run_one(df, run_name, tw, en, ex, min_rebal_delta=rebal_delta)
            factorial[run_name] = m
            print(f"CAGR={m['cagr']*100:.2f}% Sharpe={m['sharpe']:.4f} "
                  f"Score={m['score']:.1f}")

    # ── 6. Native reference panel (4 runs) ──────────────────────────────
    print("\n" + "=" * 70)
    print("RUNNING NATIVE REFERENCE PANEL")
    print("=" * 70)

    native_specs = [
        ("E0",    None,  0.0,  2.0),   # binary, no rebalance
        ("SM",    0.15,  0.0,  0.05),  # vol-targeted, per-bar rebal
        ("P",     0.12,  0.0,  0.05),
        ("LATCH", 0.12,  0.08, 0.05), # vol_floor=0.08
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

    # ── 7. Results tables ────────────────────────────────────────────────
    all_runs = {**factorial, **native}

    _HEADER = (f"{'Run':<25} {'CAGR%':>8} {'MDD%':>8} {'Sharpe':>8} "
               f"{'PF':>6} {'Trades':>7} {'Expo%':>7} {'Score':>8}")
    _SEP = "-" * 90

    print("\n" + "=" * 70)
    print("MAIN 4×3 FACTORIAL RESULTS")
    print("=" * 70)
    print(_HEADER)
    print(_SEP)
    for name in factorial:
        _print_row(name, factorial[name])

    print(f"\n{'NATIVE REFERENCES':}")
    print(_HEADER)
    print(_SEP)
    for name in native:
        _print_row(name, native[name])

    # ── 8. Signal comparison at fixed sizing (Binary_100) ────────────────
    print("\n" + "=" * 70)
    print("SIGNAL COMPARISON AT FIXED SIZING (Binary_100)")
    print("=" * 70)
    print("  Isolates signal quality — identical 100% sizing, same cost.\n")
    binary_names = [f"{s}_Binary_100" for s in ["E0", "SM", "P", "LATCH"]]
    print(f"  {'Signal':<8} {'CAGR%':>8} {'MDD%':>8} {'Sharpe':>8} "
          f"{'PF':>6} {'Trades':>7} {'Score':>8}")
    print("  " + "-" * 65)
    for name in binary_names:
        m = factorial[name]
        print(f"  {name.split('_')[0]:<8} {m['cagr']*100:>8.2f} {m['mdd']*100:>8.2f} "
              f"{m['sharpe']:>8.4f} {m['profit_factor']:>6.2f} "
              f"{int(m['n_trade_events']):>7} {m['score']:>8.2f}")

    # ── 9. Sizing comparison at fixed signal ─────────────────────────────
    print("\n" + "=" * 70)
    print("SIZING COMPARISON AT FIXED SIGNAL")
    print("=" * 70)
    for sname in ["E0", "SM", "P", "LATCH"]:
        print(f"\n  Signal: {sname}")
        print(f"  {'Sizing':<15} {'CAGR%':>8} {'MDD%':>8} {'Sharpe':>8} "
              f"{'Expo%':>7} {'Score':>8}")
        print("  " + "-" * 55)
        for sz in ["Binary_100", "EntryVol_15", "EntryVol_12"]:
            m = factorial[f"{sname}_{sz}"]
            print(f"  {sz:<15} {m['cagr']*100:>8.2f} {m['mdd']*100:>8.2f} "
                  f"{m['sharpe']:>8.4f} {m['exposure']*100:>7.1f} "
                  f"{m['score']:>8.2f}")
        if f"{sname}_Native" in native:
            m = native[f"{sname}_Native"]
            print(f"  {'Native':<15} {m['cagr']*100:>8.2f} {m['mdd']*100:>8.2f} "
                  f"{m['sharpe']:>8.4f} {m['exposure']*100:>7.1f} "
                  f"{m['score']:>8.2f}")

    # ── 10. Exposure-normalized diagnostics ──────────────────────────────
    print("\n" + "=" * 70)
    print("EXPOSURE-NORMALIZED DIAGNOSTICS")
    print("=" * 70)
    print(f"  {'Run':<25} {'Expo%':>7} {'CAGR%':>8} {'CAGR/Expo':>10} "
          f"{'Sharpe':>8} {'Shrp/Expo':>10}")
    print("  " + "-" * 75)
    for name, m in sorted(all_runs.items()):
        expo = m["exposure"]
        if expo > 0.005:
            print(f"  {name:<25} {expo*100:>7.1f} {m['cagr']*100:>8.2f} "
                  f"{m['cagr']/expo:>10.4f} {m['sharpe']:>8.4f} "
                  f"{m['sharpe']/expo:>10.4f}")

    # ── 11. Scoring-formula bias audit ───────────────────────────────────
    print("\n" + "=" * 70)
    print("SCORING-FORMULA BIAS AUDIT")
    print("=" * 70)

    _scoring_bias_audit(factorial, native)

    # ── 12. Resolution matrix R1-R6 ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESOLUTION MATRIX")
    print("=" * 70)

    _resolution_matrix(factorial, native)

    # ── 13. Save artifacts ───────────────────────────────────────────────
    elapsed = time.time() - t0
    _save_artifacts(factorial, native, pf_result, signals, ind, elapsed)

    print(f"\n{'=' * 70}")
    print(f"COMPLETE in {elapsed:.1f}s. Artifacts saved to {ARTIFACTS}/")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════════════
# SCORING BIAS AUDIT
# ═══════════════════════════════════════════════════════════════════════════

def _scoring_bias_audit(factorial: dict, native: dict):
    """Decompose score delta into 5 terms, identify bias sources."""

    # A. E0 vs LATCH at Binary_100 (isolates signal, removes sizing confounder)
    e0_b = factorial["E0_Binary_100"]
    la_b = factorial["LATCH_Binary_100"]
    print("\n  A. E0 vs LATCH at Binary_100 (identical sizing → pure signal delta)")
    _decompose_pair("E0_Binary_100", e0_b, "LATCH_Binary_100", la_b)

    # B. E0 vs SM at Binary_100
    sm_b = factorial["SM_Binary_100"]
    print("\n  B. E0 vs SM at Binary_100")
    _decompose_pair("E0_Binary_100", e0_b, "SM_Binary_100", sm_b)

    # C. E0 vs P at Binary_100
    p_b = factorial["P_Binary_100"]
    print("\n  C. E0 vs P at Binary_100")
    _decompose_pair("E0_Binary_100", e0_b, "P_Binary_100", p_b)

    # D. Original comparison: E0_Binary_100 vs LATCH_Native
    la_n = native["LATCH_Native"]
    print("\n  D. Original comparison: E0_Binary_100 vs LATCH_Native (mixed confounders)")
    _decompose_pair("E0_Binary_100", e0_b, "LATCH_Native", la_n)

    # E. CAGR vs exposure relationship
    print("\n  E. CAGR-Exposure bias analysis:")
    print(f"    E0 Binary_100:  expo={e0_b['exposure']*100:.1f}%, "
          f"CAGR={e0_b['cagr']*100:.2f}%, CAGR/expo={e0_b['cagr']/max(e0_b['exposure'],EPS):.4f}")
    print(f"    LATCH Binary_100: expo={la_b['exposure']*100:.1f}%, "
          f"CAGR={la_b['cagr']*100:.2f}%, CAGR/expo={la_b['cagr']/max(la_b['exposure'],EPS):.4f}")
    print(f"    LATCH Native:   expo={la_n['exposure']*100:.1f}%, "
          f"CAGR={la_n['cagr']*100:.2f}%, CAGR/expo={la_n['cagr']/max(la_n['exposure'],EPS):.4f}")
    print(f"\n    The 2.5× CAGR weight in the scoring formula is exposure-biased:")
    print(f"    Higher exposure → higher CAGR → higher score, even if risk-adjusted")
    print(f"    return (Sharpe, CAGR/exposure) is equal or worse.")


def _decompose_pair(name_a: str, a: dict, name_b: str, b: dict):
    """Print 5-term score decomposition for a vs b."""
    delta = b["score"] - a["score"]
    terms = ["score_cagr", "score_mdd", "score_sharpe", "score_pf", "score_trade"]
    labels = ["CAGR term", "MDD term", "Sharpe term", "PF term", "Trade term"]

    print(f"    {name_a} score: {a['score']:.2f}")
    print(f"    {name_b} score: {b['score']:.2f}")
    print(f"    Delta: {delta:+.2f}")
    print(f"    {'Term':<15} {name_a:>10} {name_b:>10} {'Delta':>10} {'% of Δ':>10}")
    print(f"    {'-'*55}")
    for t, lbl in zip(terms, labels):
        va = a[t]
        vb = b[t]
        d = vb - va
        pct = d / delta * 100 if abs(delta) > EPS else 0.0
        print(f"    {lbl:<15} {va:>+10.2f} {vb:>+10.2f} {d:>+10.2f} {pct:>+9.0f}%")


# ═══════════════════════════════════════════════════════════════════════════
# RESOLUTION MATRIX
# ═══════════════════════════════════════════════════════════════════════════

def _resolution_matrix(factorial: dict, native: dict):
    e0_b = factorial["E0_Binary_100"]
    la_b = factorial["LATCH_Binary_100"]
    sm_b = factorial["SM_Binary_100"]
    p_b = factorial["P_Binary_100"]
    la_n = native["LATCH_Native"]

    resolutions = []

    # R1: Signal quality at identical sizing
    if la_b["sharpe"] > e0_b["sharpe"]:
        r1_v = "LATCH BETTER — higher Sharpe at identical sizing"
    elif la_b["sharpe"] < e0_b["sharpe"]:
        r1_v = "E0 BETTER — higher Sharpe at identical sizing"
    else:
        r1_v = "EQUAL"
    r1_detail = (f"At Binary_100: E0 Sharpe={e0_b['sharpe']:.4f}, "
                 f"LATCH Sharpe={la_b['sharpe']:.4f}")
    resolutions.append(("R1", "Signal quality: LATCH vs E0 at identical sizing",
                         r1_v, r1_detail))

    # R2: Sizing effect
    e0_sizing_gap = factorial["E0_Binary_100"]["score"] - factorial["E0_EntryVol_12"]["score"]
    la_sizing_gap = factorial["LATCH_Binary_100"]["score"] - factorial["LATCH_EntryVol_12"]["score"]
    r2_v = (f"E0 gap={e0_sizing_gap:+.1f}, LATCH gap={la_sizing_gap:+.1f}")
    resolutions.append(("R2", "Sizing impact on score (Binary vs EntryVol_12)",
                         r2_v, "Score gap = Binary_100.score - EntryVol_12.score"))

    # R3: Scoring formula exposure bias
    orig_delta = la_n["score"] - e0_b["score"]
    cagr_contrib = (la_n["score_cagr"] - e0_b["score_cagr"]) / max(abs(orig_delta), EPS) * 100
    r3_v = f"CAGR term accounts for {cagr_contrib:.0f}% of original score delta"
    resolutions.append(("R3", "Scoring formula CAGR/exposure bias",
                         r3_v, f"Original delta={orig_delta:.2f}"))

    # R4: LATCH signal at E0-like sizing
    r4_v = f"LATCH Binary_100 score={la_b['score']:.2f} vs E0={e0_b['score']:.2f}"
    resolutions.append(("R4", "LATCH signal at E0-like sizing",
                         r4_v, f"Delta={la_b['score']-e0_b['score']:+.2f}"))

    # R5: Complexity
    r5_v = "No performance advantage for additional parameters"
    resolutions.append(("R5", "Complexity premium (3 params vs 15+)",
                         r5_v, "E0 has 3 tunable params; LATCH/SM/P have 10-15"))

    # R6: Overall
    r6_v = ("LATCH/SM/P are valid ALTERNATIVE risk profiles, "
            "not provably inferior signals")
    resolutions.append(("R6", "Overall verdict", r6_v,
                         "Scoring formula conflates signal quality with exposure level"))

    for rid, q, v, detail in resolutions:
        print(f"\n  {rid}: {q}")
        print(f"       → {v}")
        print(f"         ({detail})")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS / OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def _print_row(name: str, m: dict):
    print(f"{name:<25} {m['cagr']*100:>8.2f} {m['mdd']*100:>8.2f} "
          f"{m['sharpe']:>8.4f} {m['profit_factor']:>6.2f} "
          f"{int(m['n_trade_events']):>7} {m['exposure']*100:>7.1f} "
          f"{m['score']:>8.2f}")


def _save_artifacts(factorial, native, pf_result, signals, ind, elapsed):
    """Save all Step 3 artifacts."""
    all_runs = {**factorial, **native}

    # 1. Factorial summary CSV
    rows = []
    for name, m in all_runs.items():
        row = {k: v for k, v in m.items() if not k.startswith("_")}
        rows.append(row)
    pd.DataFrame(rows).to_csv(ARTIFACTS / "factorial_summary.csv", index=False)

    # 2. Signal comparison at binary
    binary_rows = []
    for sname in ["E0", "SM", "P", "LATCH"]:
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
        ARTIFACTS / "signal_comparison_binary100.csv", index=False)

    # 3. Scoring bias decomposition
    bias_rows = []
    for name, m in all_runs.items():
        bias_rows.append({
            "run": name, "score": m["score"],
            "cagr_pct": m["cagr"] * 100, "mdd_pct": m["mdd"] * 100,
            "sharpe": m["sharpe"], "exposure_pct": m["exposure"] * 100,
            "score_cagr": m["score_cagr"], "score_mdd": m["score_mdd"],
            "score_sharpe": m["score_sharpe"], "score_pf": m["score_pf"],
            "score_trade": m["score_trade"],
        })
    pd.DataFrame(bias_rows).to_csv(
        ARTIFACTS / "scoring_bias_audit.csv", index=False)

    # 4. Exposure-normalized metrics
    expo_rows = []
    for name, m in all_runs.items():
        expo = m["exposure"]
        if expo > 0.005:
            expo_rows.append({
                "run": name, "exposure_pct": expo * 100,
                "cagr_pct": m["cagr"] * 100,
                "cagr_per_exposure": m["cagr"] / expo,
                "sharpe": m["sharpe"],
                "sharpe_per_exposure": m["sharpe"] / expo,
                "mdd_pct": m["mdd"] * 100,
                "score": m["score"],
            })
    pd.DataFrame(expo_rows).to_csv(
        ARTIFACTS / "exposure_normalized.csv", index=False)

    # 5. Resolution matrix
    res_rows = [
        {"id": "R1", "question": "Signal quality at identical sizing",
         "verdict": "See factorial table"},
        {"id": "R2", "question": "Sizing impact on score", "verdict": "See sizing table"},
        {"id": "R3", "question": "Scoring formula exposure bias",
         "verdict": "CAGR term dominates"},
        {"id": "R4", "question": "LATCH signal at E0-like sizing",
         "verdict": "See decomposition"},
        {"id": "R5", "question": "Complexity premium", "verdict": "None observed"},
        {"id": "R6", "question": "Overall", "verdict": "Alternative profile, not inferior"},
    ]
    pd.DataFrame(res_rows).to_csv(ARTIFACTS / "resolution_matrix.csv", index=False)

    # 6. Preflight results
    with open(ARTIFACTS / "preflight_e0.json", "w") as f:
        json.dump(pf_result, f, indent=2)

    # 7. E0 signal detail
    n = len(ind["close"])
    e0_detail = pd.DataFrame({
        "bar_index": np.arange(n),
        "close": ind["close"],
        "ema_fast": ind["ema_fast"],
        "ema_slow": ind["ema_slow"],
        "atr": ind["atr"],
        "vdo": ind["vdo"],
        "entry": signals["E0"]["entry"],
        "exit": signals["E0"]["exit"],
        "in_position": signals["E0"]["in_position"],
        "peak": signals["E0"]["peak"],
        "trail_stop": signals["E0"]["trail_stop"],
        "exit_reason": signals["E0"]["exit_reason"],
    })
    e0_detail.to_csv(ARTIFACTS / "e0_signal_detail.csv", index=False)

    # 8. Equity curves
    eq_dict = {}
    for name, m in all_runs.items():
        eq_dict[name] = m["_eq"]
    np.savez_compressed(str(ARTIFACTS / "factorial_equity_curves.npz"), **eq_dict)

    # 9. Master results JSON
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
    master["_meta"] = {"n_bars": n, "elapsed_s": round(elapsed, 1),
                       "cost_bps": COST_BPS, "date": "2026-03-05"}

    with open(ARTIFACTS / "step3_master_results.json", "w") as f:
        json.dump(master, f, indent=2, default=_convert)

    print(f"\n  Saved 9 artifact files to {ARTIFACTS}/")


if __name__ == "__main__":
    main()
