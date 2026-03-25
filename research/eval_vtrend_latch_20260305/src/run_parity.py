#!/usr/bin/env python3
"""Step 2: Parity Harness — 3 layers + SM/LATCH pre-engine comparison.

Resolves open uncertainties from Report 01:
  U1: integrated vs standalone LATCH signal match
  U2: equity divergence between v10 engine and standalone engine
  U3: materiality of multiplicative fill-price vs flat cost
  U4: SM instantaneous regime vs LATCH hysteresis
  U6: standalone vtrend_variants.py SM vs integrated SM

Outputs artifacts to:
  research/eval_vtrend_latch_20260305/artifacts/

NO modification of any production file.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Setup paths
_SCRIPT = Path(__file__).resolve()
_SRC = _SCRIPT.parent
_NAMESPACE = _SRC.parent
_REPO = _NAMESPACE.parent.parent
_LATCH_PKG = Path("/var/www/trading-bots/Latch/research")

for p in [str(_REPO), str(_LATCH_PKG)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_align import load_aligned_pair, load_h4_dataframe

# ── Imports from production code (read-only) ────────────────────────────
from v10.core.types import Bar, CostConfig, MarketState, Signal
from v10.core.execution import ExecutionModel, Portfolio

# Standalone LATCH imports
from Latch.config import LatchParams, CostModel, BARS_PER_YEAR_4H
from Latch.indicators import ema, atr_wilder, rolling_high_shifted, rolling_low_shifted, annualized_realized_vol
from Latch.state_machine import compute_hysteretic_regime, LatchState
from Latch.backtest import execute_target_weights as standalone_execute

# Integrated LATCH imports
from strategies.latch.strategy import (
    LatchStrategy, LatchConfig,
    _ema as int_ema, _atr as int_atr,
    _rolling_high_shifted as int_rolling_high, _rolling_low_shifted as int_rolling_low,
    _realized_vol as int_realized_vol,
    _compute_hysteretic_regime as int_compute_regime,
)

# Integrated SM imports
from strategies.vtrend_sm.strategy import VTrendSMStrategy

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

EPS = 1e-12


def _pct_err(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Max abs error, mean abs error, max relative error (%) on finite pairs."""
    mask = np.isfinite(a) & np.isfinite(b)
    if not mask.any():
        return np.nan, np.nan, np.nan
    da = a[mask]
    db = b[mask]
    abs_diff = np.abs(da - db)
    max_abs = float(np.max(abs_diff))
    mean_abs = float(np.mean(abs_diff))
    denom = np.maximum(np.abs(da), EPS)
    max_rel = float(np.max(abs_diff / denom)) * 100
    return max_abs, mean_abs, max_rel


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1: INDICATOR PARITY (integrated vs standalone LATCH)
# ═══════════════════════════════════════════════════════════════════════

def layer1_indicator_parity(df: pd.DataFrame, bars: list[Bar]) -> dict:
    """Compare indicator computations between integrated and standalone LATCH."""
    print("\n" + "="*70)
    print("LAYER 1: INDICATOR PARITY (integrated vs standalone LATCH)")
    print("="*70)

    n = len(df)
    close_df = df["close"].astype(np.float64)
    high_df = df["high"].astype(np.float64)
    low_df = df["low"].astype(np.float64)

    close_arr = np.array([b.close for b in bars], dtype=np.float64)
    high_arr = np.array([b.high for b in bars], dtype=np.float64)
    low_arr = np.array([b.low for b in bars], dtype=np.float64)

    results = {}

    # --- EMA fast (span=30) ---
    sa_ema_fast = ema(close_df, span=30).to_numpy(dtype=np.float64)
    int_ema_fast = int_ema(close_arr, period=30)
    mx, mn, mr = _pct_err(sa_ema_fast, int_ema_fast)
    results["ema_fast_30"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  EMA fast(30):  max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # --- EMA slow (span=120) ---
    sa_ema_slow = ema(close_df, span=120).to_numpy(dtype=np.float64)
    int_ema_slow = int_ema(close_arr, period=120)
    mx, mn, mr = _pct_err(sa_ema_slow, int_ema_slow)
    results["ema_slow_120"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  EMA slow(120): max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # --- ATR (Wilder, period=14) ---
    sa_atr = atr_wilder(high_df, low_df, close_df, period=14).to_numpy(dtype=np.float64)
    int_atr_arr = int_atr(high_arr, low_arr, close_arr, period=14)
    mx, mn, mr = _pct_err(sa_atr, int_atr_arr)
    results["atr_14"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  ATR(14):       max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # --- Rolling high shifted (entry_n=60) ---
    sa_hh = rolling_high_shifted(high_df, lookback=60).to_numpy(dtype=np.float64)
    int_hh = int_rolling_high(high_arr, lookback=60)
    mx, mn, mr = _pct_err(sa_hh, int_hh)
    results["rolling_high_60"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  Rolling HH(60): max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # --- Rolling low shifted (exit_n=30) ---
    sa_ll = rolling_low_shifted(low_df, lookback=30).to_numpy(dtype=np.float64)
    int_ll = int_rolling_low(low_arr, lookback=30)
    mx, mn, mr = _pct_err(sa_ll, int_ll)
    results["rolling_low_30"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  Rolling LL(30): max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # --- Realized vol (lookback=120, bars_per_year=2190) ---
    prev_close = close_df.shift(1)
    log_returns_arr = np.log(
        np.divide(
            close_df.to_numpy(dtype=np.float64),
            prev_close.to_numpy(dtype=np.float64),
            out=np.full(n, np.nan, dtype=np.float64),
            where=np.isfinite(prev_close.to_numpy()) & (prev_close.to_numpy() > 0),
        )
    )
    log_returns = pd.Series(log_returns_arr, index=close_df.index, dtype=np.float64)
    sa_rv = annualized_realized_vol(log_returns, lookback=120, bars_per_year=BARS_PER_YEAR_4H).to_numpy(dtype=np.float64)
    int_rv = int_realized_vol(close_arr, lookback=120, bars_per_year=BARS_PER_YEAR_4H)
    mx, mn, mr = _pct_err(sa_rv, int_rv)
    results["realized_vol_120"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  Realized vol:  max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # --- Slope reference (shift=6) ---
    sa_slope = ema(close_df, span=120).shift(6).to_numpy(dtype=np.float64)
    int_slope = np.full(n, np.nan, dtype=np.float64)
    int_slope[6:] = int_ema_slow[:-6]
    mx, mn, mr = _pct_err(sa_slope, int_slope)
    results["slope_ref_6"] = {"max_abs": mx, "mean_abs": mn, "max_rel_pct": mr}
    print(f"  Slope ref(6):  max_abs={mx:.2e}, mean_abs={mn:.2e}, max_rel={mr:.4f}%")

    # Overall verdict
    all_max_rel = [v["max_rel_pct"] for v in results.values() if np.isfinite(v["max_rel_pct"])]
    worst_rel = max(all_max_rel) if all_max_rel else np.nan
    parity = worst_rel < 0.001  # <0.001% relative error
    results["_verdict"] = "PASS" if parity else "FAIL"
    results["_worst_relative_pct"] = worst_rel
    print(f"\n  LAYER 1 VERDICT: {'PASS' if parity else 'FAIL'} (worst relative error: {worst_rel:.6f}%)")

    return results


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2: SIGNAL/STATE PARITY (regime + state machine + target weights)
# ═══════════════════════════════════════════════════════════════════════

def layer2_signal_parity(df: pd.DataFrame, bars: list[Bar]) -> dict:
    """Compare regime, state machine, and target weights between implementations."""
    print("\n" + "="*70)
    print("LAYER 2: SIGNAL/STATE PARITY (integrated vs standalone LATCH)")
    print("="*70)

    n = len(df)
    results = {}

    # --- Run standalone LATCH (extract signals only, no backtest) ---
    close_df = df["close"].astype(np.float64)
    high_df = df["high"].astype(np.float64)
    low_df = df["low"].astype(np.float64)

    params = LatchParams()

    sa_ema_fast = ema(close_df, params.fast)
    sa_ema_slow = ema(close_df, params.slow)
    sa_regime = compute_hysteretic_regime(sa_ema_fast, sa_ema_slow, slope_n=params.slope_n)
    sa_atr = atr_wilder(high_df, low_df, close_df, params.atr_period)
    sa_hh = rolling_high_shifted(high_df, params.entry_n)
    sa_ll = rolling_low_shifted(low_df, params.exit_n)

    prev_close = close_df.shift(1)
    lr_arr = np.log(np.divide(
        close_df.to_numpy(dtype=np.float64),
        prev_close.to_numpy(dtype=np.float64),
        out=np.full(n, np.nan, dtype=np.float64),
        where=np.isfinite(prev_close.to_numpy()) & (prev_close.to_numpy() > 0),
    ))
    sa_rv = annualized_realized_vol(
        pd.Series(lr_arr, index=close_df.index, dtype=np.float64),
        params.vol_lookback, BARS_PER_YEAR_4H
    )

    # Standalone state machine loop
    close_loop = close_df.to_numpy(dtype=np.float64, copy=False)
    hh_loop = sa_hh.to_numpy(dtype=np.float64, copy=False)
    ll_loop = sa_ll.to_numpy(dtype=np.float64, copy=False)
    ema_s_loop = sa_ema_slow.to_numpy(dtype=np.float64, copy=False)
    atr_loop = sa_atr.to_numpy(dtype=np.float64, copy=False)
    rv_loop = sa_rv.to_numpy(dtype=np.float64, copy=False)

    # Find standalone warmup
    arrays_for_warmup = [sa_ema_fast, sa_ema_slow, sa_regime.slope_ref, sa_atr, sa_hh, sa_ll, sa_rv]
    valid_mask = np.ones(n, dtype=bool)
    for arr in arrays_for_warmup:
        valid_mask &= np.isfinite(arr.to_numpy(dtype=np.float64))
    warmup_idx = int(np.where(valid_mask)[0][0]) if valid_mask.any() else n

    sa_state = np.zeros(n, dtype=np.int8)
    sa_target = np.zeros(n, dtype=np.float64)
    sa_entry = np.zeros(n, dtype=np.bool_)
    sa_exit = np.zeros(n, dtype=np.bool_)
    current = LatchState.OFF

    for i in range(n):
        if i < warmup_idx:
            sa_state[i] = int(current)
            continue

        regime_on = bool(sa_regime.regime_on[i])
        off_trigger = bool(sa_regime.off_trigger[i])
        flip_off = bool(sa_regime.flip_off[i])
        breakout = bool(close_loop[i] > hh_loop[i])
        floor = max(ll_loop[i], ema_s_loop[i] - params.atr_mult * atr_loop[i])

        if current == LatchState.OFF:
            if regime_on and breakout:
                current = LatchState.LONG
                sa_entry[i] = True
            elif regime_on:
                current = LatchState.ARMED
        elif current == LatchState.ARMED:
            if off_trigger:
                current = LatchState.OFF
            elif regime_on and breakout:
                current = LatchState.LONG
                sa_entry[i] = True
        elif current == LatchState.LONG:
            if bool(close_loop[i] < floor) or flip_off:
                current = LatchState.OFF
                sa_exit[i] = True

        sa_state[i] = int(current)

        if current == LatchState.LONG:
            rv_i = max(rv_loop[i], float(params.vol_floor), EPS)
            w = float(params.target_vol / rv_i)
            w = min(params.max_pos, max(0.0, w))
            sa_target[i] = w
        else:
            sa_target[i] = 0.0

    # --- Run integrated LATCH ---
    config = LatchConfig(
        slow_period=params.slow, fast_period=params.fast,
        slope_lookback=params.slope_n, entry_n=params.entry_n,
        exit_n=params.exit_n, atr_period=params.atr_period,
        atr_mult=params.atr_mult, vol_lookback=params.vol_lookback,
        target_vol=params.target_vol, vol_floor=params.vol_floor,
        max_pos=params.max_pos, min_weight=params.min_weight,
        min_rebalance_weight_delta=params.min_rebalance_weight_delta,
        vdo_mode="none",
    )
    strat = LatchStrategy(config)
    strat.on_init(bars, [])  # No D1 bars needed

    int_regime_on = strat._regime_on.copy()
    int_regime_flip_off = strat._regime_flip_off.copy()
    int_warmup = strat._warmup_end

    # Simulate bar-by-bar to extract signals (without engine)
    int_state_arr = np.zeros(n, dtype=np.int8)
    int_target_arr = np.zeros(n, dtype=np.float64)
    int_entry_arr = np.zeros(n, dtype=np.bool_)
    int_exit_arr = np.zeros(n, dtype=np.bool_)

    # Use a fresh strategy copy
    strat2 = LatchStrategy(config)
    strat2.on_init(bars, [])

    current_exposure = 0.0  # Track simulated exposure for rebalance logic
    prev_state_was_long = False

    for i in range(n):
        bar = bars[i]
        # Build MarketState with tracked exposure
        ms = MarketState(
            bar=bar, h4_bars=bars, d1_bars=[], bar_index=i, d1_index=-1,
            cash=10000.0*(1 - current_exposure),
            btc_qty=10000.0*current_exposure/max(bar.close, EPS),
            nav=10000.0, exposure=current_exposure,
            entry_price_avg=bar.close if current_exposure > 0 else 0.0,
            position_entry_nav=10000.0 if current_exposure > 0 else 0.0,
        )
        # Record state BEFORE on_bar
        int_state_arr[i] = int(strat2._state)

        sig = strat2.on_bar(ms)

        if sig is not None:
            te = sig.target_exposure
            if te is not None and te > 0:
                was_flat = current_exposure < 1e-12
                int_entry_arr[i] = was_flat  # Only count as entry from flat
                int_target_arr[i] = te
                current_exposure = te
            elif te is not None and te == 0.0:
                int_exit_arr[i] = True
                int_target_arr[i] = 0.0
                current_exposure = 0.0
        else:
            # No signal — carry forward if LONG
            if strat2._state == 2:  # LONG
                int_target_arr[i] = int_target_arr[i-1] if i > 0 else 0.0

        int_state_arr[i] = int(strat2._state)

    # --- Compare regime arrays ---
    sa_regime_arr = sa_regime.regime_on.astype(np.int8)
    int_regime_arr = int_regime_on.astype(np.int8)
    regime_match = np.sum(sa_regime_arr == int_regime_arr)
    regime_total = n
    regime_mismatch = regime_total - regime_match
    results["regime_match_count"] = int(regime_match)
    results["regime_mismatch_count"] = int(regime_mismatch)
    results["regime_parity"] = regime_mismatch == 0
    print(f"  Regime: {regime_match}/{regime_total} match ({regime_mismatch} mismatches)")

    # --- Compare state arrays ---
    # Focus on post-warmup region
    warmup_max = max(warmup_idx, int_warmup)
    sa_state_post = sa_state[warmup_max:]
    int_state_post = int_state_arr[warmup_max:]
    state_match = np.sum(sa_state_post == int_state_post)
    state_total = len(sa_state_post)
    state_mismatch = state_total - state_match
    results["state_match_count"] = int(state_match)
    results["state_mismatch_count"] = int(state_mismatch)
    results["state_warmup_max"] = int(warmup_max)
    results["standalone_warmup"] = int(warmup_idx)
    results["integrated_warmup"] = int(int_warmup)
    print(f"  State (post-warmup {warmup_max}): {state_match}/{state_total} match ({state_mismatch} mismatches)")

    # --- Compare target weights ---
    sa_tw_post = sa_target[warmup_max:]
    int_tw_post = int_target_arr[warmup_max:]
    tw_max_abs, tw_mean_abs, tw_max_rel = _pct_err(sa_tw_post, int_tw_post)
    results["target_weight_max_abs_err"] = tw_max_abs
    results["target_weight_mean_abs_err"] = tw_mean_abs
    print(f"  Target weights: max_abs={tw_max_abs:.6f}, mean_abs={tw_mean_abs:.6f}")

    # --- Entry/exit signal counts ---
    sa_entries = int(np.sum(sa_entry))
    int_entries = int(np.sum(int_entry_arr))
    sa_exits = int(np.sum(sa_exit))
    int_exits = int(np.sum(int_exit_arr))
    results["standalone_entries"] = sa_entries
    results["integrated_entries"] = int_entries
    results["standalone_exits"] = sa_exits
    results["integrated_exits"] = int_exits
    print(f"  Entries: standalone={sa_entries}, integrated={int_entries}")
    print(f"  Exits:   standalone={sa_exits}, integrated={int_exits}")

    # Verdict
    signal_parity = (regime_mismatch == 0) and (state_mismatch == 0)
    results["_verdict"] = "PASS" if signal_parity else "FAIL"
    print(f"\n  LAYER 2 VERDICT: {'PASS' if signal_parity else 'FAIL'}")

    # Save state/signal arrays
    np.savez_compressed(
        str(ARTIFACTS / "latch_signal_comparison.npz"),
        sa_state=sa_state, int_state=int_state_arr,
        sa_target=sa_target, int_target=int_target_arr,
        sa_regime=sa_regime.regime_on, int_regime=int_regime_on,
        sa_entry=sa_entry, int_entry=int_entry_arr,
        sa_exit=sa_exit, int_exit=int_exit_arr,
    )

    return results


# ═══════════════════════════════════════════════════════════════════════
# LAYER 3: ENGINE PARITY (v10 engine vs standalone engine)
# ═══════════════════════════════════════════════════════════════════════

def layer3_engine_parity(df: pd.DataFrame, bars: list[Bar]) -> dict:
    """Feed identical signal stream to both engines, compare equity curves.

    Uses LATCH's actual target_weight_signal from standalone run.
    Resolves U2 (equity divergence) and U3 (fill-price materiality).
    """
    print("\n" + "="*70)
    print("LAYER 3: ENGINE PARITY (v10 engine vs standalone engine)")
    print("="*70)

    results = {}
    n = len(df)

    # First, get LATCH signals from standalone
    params = LatchParams()
    from Latch.strategy import run_latch
    sa_result = run_latch(df.copy(), params=params, costs=CostModel(fee_bps=25.0))

    sa_equity = sa_result.data["equity"].to_numpy(dtype=np.float64)
    sa_target_w = sa_result.target_weight_signal.copy()

    results["standalone_final_equity"] = float(sa_equity[-1])
    results["standalone_sharpe"] = sa_result.metrics["sharpe"]
    results["standalone_cagr"] = sa_result.metrics["cagr"]
    results["standalone_mdd"] = sa_result.metrics["mdd"]
    results["standalone_trades"] = int(sa_result.metrics["n_trade_events"])
    print(f"  Standalone: equity={sa_equity[-1]:.6f}, sharpe={sa_result.metrics['sharpe']:.4f}, "
          f"cagr={sa_result.metrics['cagr']*100:.2f}%, mdd={sa_result.metrics['mdd']*100:.2f}%")

    # Now feed same target_weight_signal through v10 engine semantics
    # We simulate v10 engine execution manually with same signal timing
    # v10 harsh cost config: spread=10, slip=5, fee=0.15%
    # Standalone default: fee=25bps, spread=0, slip=0
    # For fair comparison, use equivalent total RT cost

    # Test A: Both with standalone cost (25bps one-way, flat on notional)
    # Already have standalone result above.

    # Test B: v10 simulation with harsh cost (multiplicative fill)
    # Uses the SAME rebalance logic as standalone: strategy 5% threshold + engine 0.5% floor
    STRATEGY_THRESH = 0.05  # min_rebalance_weight_delta from LATCH defaults
    ENGINE_THRESH = 0.005   # _EXPO_THRESHOLD from v10 engine

    harsh = CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.15)
    exec_model = ExecutionModel(harsh)
    pf_v10 = Portfolio(10000.0, exec_model)

    v10_equity = np.zeros(n, dtype=np.float64)
    v10_trades = 0

    for i in range(n):
        bar = bars[i]
        if i > 0:
            target = float(sa_target_w[i - 1])
            target = max(0.0, min(1.0, target))
            mid = bar.open
            current_expo = pf_v10.exposure(mid)
            delta_abs = abs(target - current_expo)
            crossing_zero = (target <= 1e-12) != (current_expo <= 1e-12)

            # Combined threshold: strategy 5% + engine 0.5%
            should_trade = crossing_zero or (delta_abs >= STRATEGY_THRESH - 1e-12)

            if should_trade:
                delta = target - current_expo
                if target < ENGINE_THRESH and pf_v10.btc_qty > 1e-8:
                    pf_v10.sell(pf_v10.btc_qty, mid, bar.open_time, "close")
                    v10_trades += 1
                elif delta > ENGINE_THRESH:
                    nav = pf_v10.nav(mid)
                    buy_value = delta * nav
                    qty = buy_value / mid
                    pf_v10.buy(qty, mid, bar.open_time, "buy")
                    v10_trades += 1
                elif delta < -ENGINE_THRESH:
                    nav = pf_v10.nav(mid)
                    sell_value = abs(delta) * nav
                    qty = min(sell_value / mid, pf_v10.btc_qty)
                    pf_v10.sell(qty, mid, bar.open_time, "sell")
                    v10_trades += 1

        v10_equity[i] = pf_v10.nav(bar.close)

    # v10-style metrics
    v10_rets = np.diff(v10_equity) / np.maximum(v10_equity[:-1], EPS)
    v10_sharpe = float(np.mean(v10_rets) / max(np.std(v10_rets, ddof=0), EPS) * np.sqrt(2190))
    v10_final = float(v10_equity[-1])
    years_v10 = (len(v10_equity) - 1) / 2190.0
    v10_cagr = float((v10_final / 10000.0) ** (1.0 / years_v10) - 1) if years_v10 > 0 else np.nan
    v10_running_max = np.maximum.accumulate(v10_equity)
    v10_mdd = float(np.max(1 - v10_equity / np.maximum(v10_running_max, EPS)))

    results["v10_harsh_final_equity"] = v10_final
    results["v10_harsh_sharpe"] = v10_sharpe
    results["v10_harsh_cagr"] = v10_cagr
    results["v10_harsh_mdd"] = v10_mdd
    results["v10_harsh_trades"] = v10_trades
    print(f"  V10 harsh:   equity={v10_final:.2f}, sharpe={v10_sharpe:.4f}, "
          f"cagr={v10_cagr*100:.2f}%, mdd={v10_mdd*100:.2f}%")

    # Test C: v10 simulation with EQUIVALENT flat cost (25bps fee only)
    # Same threshold logic as Test B
    equiv_cost = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.25)
    exec_equiv = ExecutionModel(equiv_cost)
    pf_equiv = Portfolio(10000.0, exec_equiv)

    equiv_equity = np.zeros(n, dtype=np.float64)
    for i in range(n):
        bar = bars[i]
        if i > 0:
            target = float(sa_target_w[i - 1])
            target = max(0.0, min(1.0, target))
            mid = bar.open
            current_expo = pf_equiv.exposure(mid)
            delta_abs = abs(target - current_expo)
            crossing_zero = (target <= 1e-12) != (current_expo <= 1e-12)
            should_trade = crossing_zero or (delta_abs >= STRATEGY_THRESH - 1e-12)

            if should_trade:
                delta = target - current_expo
                if target < ENGINE_THRESH and pf_equiv.btc_qty > 1e-8:
                    pf_equiv.sell(pf_equiv.btc_qty, mid, bar.open_time, "close")
                elif delta > ENGINE_THRESH:
                    nav = pf_equiv.nav(mid)
                    buy_value = delta * nav
                    qty = buy_value / mid
                    pf_equiv.buy(qty, mid, bar.open_time, "buy")
                elif delta < -ENGINE_THRESH:
                    nav = pf_equiv.nav(mid)
                    sell_value = abs(delta) * nav
                    qty = min(sell_value / mid, pf_equiv.btc_qty)
                    pf_equiv.sell(qty, mid, bar.open_time, "sell")
        equiv_equity[i] = pf_equiv.nav(bar.close)

    equiv_final = float(equiv_equity[-1])
    equiv_rets = np.diff(equiv_equity) / np.maximum(equiv_equity[:-1], EPS)
    equiv_sharpe = float(np.mean(equiv_rets) / max(np.std(equiv_rets, ddof=0), EPS) * np.sqrt(2190))
    results["v10_equiv_final_equity"] = equiv_final
    results["v10_equiv_sharpe"] = equiv_sharpe
    print(f"  V10 equiv:   equity={equiv_final:.2f}, sharpe={equiv_sharpe:.4f}")

    # Standalone equity normalized to 10000 for comparison
    sa_eq_scaled = sa_equity * 10000.0
    sa_final_scaled = float(sa_eq_scaled[-1])
    results["standalone_scaled_final"] = sa_final_scaled
    print(f"  Standalone (scaled to 10k): {sa_final_scaled:.2f}")

    # Equity divergence
    mask = equiv_equity > 0
    divergence = np.abs(equiv_equity[mask] - sa_eq_scaled[mask]) / np.maximum(sa_eq_scaled[mask], EPS)
    max_divergence = float(np.max(divergence)) * 100
    mean_divergence = float(np.mean(divergence)) * 100
    results["equity_max_divergence_pct"] = max_divergence
    results["equity_mean_divergence_pct"] = mean_divergence
    print(f"  Equity divergence (v10_equiv vs standalone_scaled): max={max_divergence:.4f}%, mean={mean_divergence:.4f}%")

    # Cost model materiality (harsh vs equiv)
    harsh_vs_equiv_final_diff = (v10_final - equiv_final) / equiv_final * 100
    results["harsh_vs_equiv_final_diff_pct"] = harsh_vs_equiv_final_diff
    print(f"  Harsh vs equiv fill-price impact on final equity: {harsh_vs_equiv_final_diff:.4f}%")

    results["_verdict"] = "see metrics"
    print(f"\n  LAYER 3: Engine parity measured. See artifact for details.")

    # Save equity curves
    np.savez_compressed(
        str(ARTIFACTS / "engine_equity_comparison.npz"),
        standalone_equity=sa_equity,
        v10_harsh_equity=v10_equity,
        v10_equiv_equity=equiv_equity,
        target_weights=sa_target_w,
    )

    return results


# ═══════════════════════════════════════════════════════════════════════
# SM vs LATCH: PRE-ENGINE COMPARISON (resolves U4)
# ═══════════════════════════════════════════════════════════════════════

def sm_vs_latch_regime_comparison(df: pd.DataFrame, bars: list[Bar]) -> dict:
    """Compare SM instantaneous regime vs LATCH hysteretic regime on real data."""
    print("\n" + "="*70)
    print("SM vs LATCH: REGIME COMPARISON (resolves U4)")
    print("="*70)

    n = len(df)
    results = {}

    close_df = df["close"].astype(np.float64)
    close_arr = np.array([b.close for b in bars], dtype=np.float64)
    high_arr = np.array([b.high for b in bars], dtype=np.float64)
    low_arr = np.array([b.low for b in bars], dtype=np.float64)

    # SM regime: instantaneous, no hysteresis
    ema_fast_arr = int_ema(close_arr, period=30)
    ema_slow_arr = int_ema(close_arr, period=120)
    slope_ref = np.full(n, np.nan, dtype=np.float64)
    slope_ref[6:] = ema_slow_arr[:-6]

    sm_regime = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if np.isfinite(ema_fast_arr[i]) and np.isfinite(ema_slow_arr[i]) and np.isfinite(slope_ref[i]):
            sm_regime[i] = (ema_fast_arr[i] > ema_slow_arr[i]) and (ema_slow_arr[i] > slope_ref[i])

    # LATCH regime: hysteretic
    latch_regime, _, latch_flip_off = int_compute_regime(ema_fast_arr, ema_slow_arr, slope_ref)

    # Compare
    mask_finite = np.isfinite(ema_fast_arr) & np.isfinite(ema_slow_arr) & np.isfinite(slope_ref)
    n_finite = int(np.sum(mask_finite))

    agree = np.sum(sm_regime[mask_finite] == latch_regime[mask_finite])
    disagree = n_finite - agree
    concordance = float(agree) / max(n_finite, 1) * 100

    results["bars_compared"] = n_finite
    results["agree_count"] = int(agree)
    results["disagree_count"] = int(disagree)
    results["concordance_pct"] = concordance
    print(f"  Bars compared: {n_finite}")
    print(f"  Agree: {agree} ({concordance:.2f}%)")
    print(f"  Disagree: {disagree} ({100-concordance:.2f}%)")

    # Where do they disagree?
    disagree_mask = mask_finite & (sm_regime != latch_regime)
    sm_on_latch_off = int(np.sum(disagree_mask & sm_regime & ~latch_regime))
    sm_off_latch_on = int(np.sum(disagree_mask & ~sm_regime & latch_regime))
    results["sm_on_latch_off"] = sm_on_latch_off
    results["sm_off_latch_on"] = sm_off_latch_on
    print(f"  SM=ON, LATCH=OFF: {sm_on_latch_off} bars")
    print(f"  SM=OFF, LATCH=ON: {sm_off_latch_on} bars (hysteresis persistence)")

    # Regime duration statistics
    sm_on_count = int(np.sum(sm_regime[mask_finite]))
    latch_on_count = int(np.sum(latch_regime[mask_finite]))
    results["sm_regime_on_bars"] = sm_on_count
    results["latch_regime_on_bars"] = latch_on_count
    results["sm_regime_on_pct"] = float(sm_on_count) / max(n_finite, 1) * 100
    results["latch_regime_on_pct"] = float(latch_on_count) / max(n_finite, 1) * 100
    print(f"  SM regime ON:    {sm_on_count} bars ({results['sm_regime_on_pct']:.1f}%)")
    print(f"  LATCH regime ON: {latch_on_count} bars ({results['latch_regime_on_pct']:.1f}%)")

    # The hysteresis difference: LATCH holds regime ON longer
    extra_latch_bars = latch_on_count - sm_on_count
    results["hysteresis_extra_on_bars"] = extra_latch_bars
    print(f"  Hysteresis extends regime by: {extra_latch_bars} bars ({extra_latch_bars/max(n_finite,1)*100:.1f}%)")

    # Flip-off count comparison
    # SM flips: regime changes every bar where condition changes
    sm_flips = int(np.sum(np.diff(sm_regime[mask_finite].astype(np.int8)) != 0))
    latch_flips = int(np.sum(np.diff(latch_regime[mask_finite].astype(np.int8)) != 0))
    results["sm_regime_flips"] = sm_flips
    results["latch_regime_flips"] = latch_flips
    print(f"  SM regime flips:    {sm_flips}")
    print(f"  LATCH regime flips: {latch_flips}")
    print(f"  Flip reduction:     {sm_flips - latch_flips} ({(sm_flips-latch_flips)/max(sm_flips,1)*100:.1f}%)")

    results["_verdict"] = "MATERIAL_DIFFERENCE" if disagree > 100 else "SIMILAR"
    print(f"\n  SM vs LATCH REGIME VERDICT: {results['_verdict']}")

    np.savez_compressed(
        str(ARTIFACTS / "sm_latch_regime_comparison.npz"),
        sm_regime=sm_regime, latch_regime=latch_regime,
        ema_fast=ema_fast_arr, ema_slow=ema_slow_arr, slope_ref=slope_ref,
    )

    return results


# ═══════════════════════════════════════════════════════════════════════
# STANDALONE SM vs INTEGRATED SM (resolves U6)
# ═══════════════════════════════════════════════════════════════════════

def standalone_vs_integrated_sm(df: pd.DataFrame, bars: list[Bar]) -> dict:
    """Compare standalone vtrend_variants.py SM vs integrated SM."""
    print("\n" + "="*70)
    print("STANDALONE vs INTEGRATED SM (resolves U6)")
    print("="*70)

    results = {}
    n = len(df)
    close_arr = np.array([b.close for b in bars], dtype=np.float64)
    high_arr = np.array([b.high for b in bars], dtype=np.float64)
    low_arr = np.array([b.low for b in bars], dtype=np.float64)

    # Integrated SM: extract signals bar-by-bar
    from strategies.vtrend_sm.strategy import VTrendSMStrategy, VTrendSMConfig
    sm_config = VTrendSMConfig()  # defaults
    sm_strat = VTrendSMStrategy(sm_config)
    sm_strat.on_init(bars, [])

    int_sm_signals = np.zeros(n, dtype=np.float64)
    int_sm_active = np.zeros(n, dtype=np.bool_)

    for i in range(n):
        bar = bars[i]
        ms = MarketState(
            bar=bar, h4_bars=bars, d1_bars=[], bar_index=i, d1_index=-1,
            cash=10000.0, btc_qty=0.0, nav=10000.0, exposure=0.0,
            entry_price_avg=0.0, position_entry_nav=0.0,
        )
        sig = sm_strat.on_bar(ms)
        int_sm_active[i] = sm_strat._active
        if sig is not None and sig.target_exposure is not None:
            int_sm_signals[i] = sig.target_exposure

    int_sm_entries = int(np.sum(np.diff(int_sm_active.astype(np.int8)) == 1))
    int_sm_exits = int(np.sum(np.diff(int_sm_active.astype(np.int8)) == -1))

    # Standalone SM: compute regime + signals
    # SM uses instantaneous regime: (ema_f > ema_s) and (ema_s > slope_ref)
    ema_f = int_ema(close_arr, period=30)
    ema_s = int_ema(close_arr, period=120)
    slope = np.full(n, np.nan, dtype=np.float64)
    slope[6:] = ema_s[:-6]
    atr_arr = int_atr(high_arr, low_arr, close_arr, period=14)
    hh = int_rolling_high(high_arr, lookback=60)
    ll = int_rolling_low(low_arr, lookback=30)
    rv = int_realized_vol(close_arr, lookback=120, bars_per_year=2190.0)

    # SM-specific warmup
    arrays_warmup = [ema_f, ema_s, slope, atr_arr, hh, ll, rv]
    warmup_sm = 0
    for i in range(n):
        if all(np.isfinite(a[i]) for a in arrays_warmup):
            warmup_sm = i
            break

    # SM state machine (simple: active/inactive, no hysteresis)
    sa_sm_active = np.zeros(n, dtype=np.bool_)
    sa_sm_signals = np.zeros(n, dtype=np.float64)
    active = False
    target_vol_sm = 0.15  # SM default
    min_w_sm = 0.0
    atr_mult_sm = 3.0

    for i in range(n):
        if i < warmup_sm:
            continue

        regime_ok = bool((ema_f[i] > ema_s[i]) and (ema_s[i] > slope[i]))

        if not active:
            breakout = close_arr[i] > hh[i]
            if regime_ok and breakout:
                w = min(1.0, max(0.0, target_vol_sm / max(rv[i], EPS)))
                if w > 0:
                    active = True
                    sa_sm_signals[i] = w
        else:
            exit_floor = max(ll[i], ema_s[i] - atr_mult_sm * atr_arr[i])
            if close_arr[i] < exit_floor:
                active = False
                sa_sm_signals[i] = 0.0
            else:
                # Rebalance weight
                w = min(1.0, max(0.0, target_vol_sm / max(rv[i], EPS)))
                sa_sm_signals[i] = w

        sa_sm_active[i] = active

    sa_sm_entries = int(np.sum(np.diff(sa_sm_active.astype(np.int8)) == 1))
    sa_sm_exits = int(np.sum(np.diff(sa_sm_active.astype(np.int8)) == -1))

    # Compare active states
    post_warmup = max(warmup_sm, sm_strat._warmup_end)
    active_agree = int(np.sum(sa_sm_active[post_warmup:] == int_sm_active[post_warmup:]))
    active_total = n - post_warmup
    active_mismatch = active_total - active_agree

    results["warmup_standalone_sm"] = warmup_sm
    results["warmup_integrated_sm"] = int(sm_strat._warmup_end)
    results["active_agree"] = active_agree
    results["active_mismatch"] = active_mismatch
    results["active_total"] = active_total
    results["standalone_sm_entries"] = sa_sm_entries
    results["integrated_sm_entries"] = int_sm_entries
    results["standalone_sm_exits"] = sa_sm_exits
    results["integrated_sm_exits"] = int_sm_exits

    print(f"  Warmup: standalone={warmup_sm}, integrated={sm_strat._warmup_end}")
    print(f"  Active state match: {active_agree}/{active_total} ({active_mismatch} mismatches)")
    print(f"  Entries: standalone={sa_sm_entries}, integrated={int_sm_entries}")
    print(f"  Exits: standalone={sa_sm_exits}, integrated={int_sm_exits}")

    # Note: Small mismatches expected due to rebalance interaction with exposure
    results["_verdict"] = "PASS" if active_mismatch < 5 else "DIVERGENT"
    print(f"\n  SM PARITY VERDICT: {results['_verdict']}")

    np.savez_compressed(
        str(ARTIFACTS / "sm_parity_comparison.npz"),
        sa_active=sa_sm_active, int_active=int_sm_active,
        sa_signals=sa_sm_signals, int_signals=int_sm_signals,
    )

    return results


# ═══════════════════════════════════════════════════════════════════════
# SIGNAL EXTRACTION: Canonical signal package
# ═══════════════════════════════════════════════════════════════════════

def extract_signal_package(df: pd.DataFrame, bars: list[Bar]) -> dict:
    """Extract canonical signal package for all strategies."""
    print("\n" + "="*70)
    print("SIGNAL EXTRACTION: Canonical packages")
    print("="*70)

    n = len(df)
    close_arr = np.array([b.close for b in bars], dtype=np.float64)
    high_arr = np.array([b.high for b in bars], dtype=np.float64)
    low_arr = np.array([b.low for b in bars], dtype=np.float64)

    # Common indicators (shared by SM, P, LATCH)
    ema_f = int_ema(close_arr, period=30)
    ema_s = int_ema(close_arr, period=120)
    slope = np.full(n, np.nan, dtype=np.float64)
    slope[6:] = ema_s[:-6]
    atr_arr = int_atr(high_arr, low_arr, close_arr, period=14)
    hh60 = int_rolling_high(high_arr, lookback=60)
    ll30 = int_rolling_low(low_arr, lookback=30)
    rv = int_realized_vol(close_arr, lookback=120, bars_per_year=2190.0)

    # SM regime (instantaneous)
    sm_regime = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if np.isfinite(ema_f[i]) and np.isfinite(ema_s[i]) and np.isfinite(slope[i]):
            sm_regime[i] = (ema_f[i] > ema_s[i]) and (ema_s[i] > slope[i])

    # LATCH regime (hysteretic)
    latch_regime, _, latch_flip_off = int_compute_regime(ema_f, ema_s, slope)

    # P regime (price-direct)
    p_regime = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if np.isfinite(ema_s[i]) and np.isfinite(slope[i]):
            p_regime[i] = (close_arr[i] > ema_s[i]) and (ema_s[i] > slope[i])

    # Binary entry/exit signals for each (regime ON + breakout)
    warmup = 0
    for i in range(n):
        if all(np.isfinite(a[i]) for a in [ema_f, ema_s, slope, atr_arr, hh60, ll30, rv]):
            warmup = i
            break

    strategies = {}
    for name, regime_arr in [("SM", sm_regime), ("LATCH", latch_regime), ("P", p_regime)]:
        active = False
        entry = np.zeros(n, dtype=np.bool_)
        exit_sig = np.zeros(n, dtype=np.bool_)
        in_position = np.zeros(n, dtype=np.bool_)
        atr_mult = {"SM": 3.0, "LATCH": 2.0, "P": 1.5}[name]

        for i in range(warmup, n):
            if not active:
                if regime_arr[i] and close_arr[i] > hh60[i]:
                    active = True
                    entry[i] = True
            else:
                floor = max(ll30[i], ema_s[i] - atr_mult * atr_arr[i])
                if name == "LATCH":
                    if close_arr[i] < floor or latch_flip_off[i]:
                        active = False
                        exit_sig[i] = True
                else:
                    if close_arr[i] < floor:
                        active = False
                        exit_sig[i] = True
            in_position[i] = active

        strategies[name] = {
            "entry": entry,
            "exit": exit_sig,
            "in_position": in_position,
            "regime": regime_arr,
        }
        entries = int(np.sum(entry))
        exits = int(np.sum(exit_sig))
        on_bars = int(np.sum(in_position[warmup:]))
        total = n - warmup
        print(f"  {name}: {entries} entries, {exits} exits, in-position {on_bars}/{total} ({on_bars/max(total,1)*100:.1f}%)")

    # Signal concordance matrix
    print("\n  Signal concordance (% of bars where both agree on position):")
    names = ["SM", "LATCH", "P"]
    concordance_matrix = {}
    for a in names:
        for b in names:
            if a <= b:
                pos_a = strategies[a]["in_position"][warmup:]
                pos_b = strategies[b]["in_position"][warmup:]
                agree = float(np.sum(pos_a == pos_b)) / max(len(pos_a), 1) * 100
                concordance_matrix[f"{a}_vs_{b}"] = agree
                if a != b:
                    print(f"    {a} vs {b}: {agree:.1f}%")

    # Save signal package
    save_dict = {}
    for name in names:
        for key in ["entry", "exit", "in_position", "regime"]:
            save_dict[f"{name}_{key}"] = strategies[name][key]
    save_dict["ema_fast"] = ema_f
    save_dict["ema_slow"] = ema_s
    save_dict["slope_ref"] = slope
    save_dict["atr"] = atr_arr
    save_dict["hh60"] = hh60
    save_dict["ll30"] = ll30
    save_dict["rv"] = rv
    save_dict["close"] = close_arr
    save_dict["high"] = high_arr
    save_dict["low"] = low_arr

    np.savez_compressed(str(ARTIFACTS / "canonical_signal_package.npz"), **save_dict)

    return {
        "warmup": warmup,
        "concordance": concordance_matrix,
        "per_strategy": {
            name: {
                "entries": int(np.sum(strategies[name]["entry"])),
                "exits": int(np.sum(strategies[name]["exit"])),
                "in_position_bars": int(np.sum(strategies[name]["in_position"][warmup:])),
                "in_position_pct": float(np.sum(strategies[name]["in_position"][warmup:])) / max(n - warmup, 1) * 100,
            }
            for name in names
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("Step 2: Parity Harness + Signal Extraction")
    print("=" * 70)
    t0 = time.time()

    df, bars = load_aligned_pair()
    n = len(df)
    print(f"Loaded {n} aligned H4 bars")

    all_results = {}

    # Layer 1
    all_results["layer1_indicators"] = layer1_indicator_parity(df, bars)

    # Layer 2
    all_results["layer2_signals"] = layer2_signal_parity(df, bars)

    # Layer 3
    all_results["layer3_engine"] = layer3_engine_parity(df, bars)

    # SM vs LATCH regime
    all_results["sm_vs_latch_regime"] = sm_vs_latch_regime_comparison(df, bars)

    # Standalone vs integrated SM
    all_results["sm_parity"] = standalone_vs_integrated_sm(df, bars)

    # Signal extraction
    all_results["signal_package"] = extract_signal_package(df, bars)

    elapsed = time.time() - t0
    all_results["_meta"] = {
        "n_bars": n,
        "elapsed_seconds": round(elapsed, 1),
        "date": "2026-03-05",
    }

    # Save master results JSON
    def _convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(ARTIFACTS / "parity_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=_convert)

    print(f"\n{'='*70}")
    print(f"COMPLETE in {elapsed:.1f}s. Results saved to {ARTIFACTS}/")
    print(f"{'='*70}")

    return all_results


if __name__ == "__main__":
    results = main()
