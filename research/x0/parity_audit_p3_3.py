"""P3.3 Parity Audit: X0 Phase 3 timing verification + exposure audit.

Four-layer audit:
  A. Raw rule parity: entry/exit conditions identical to Phase 2
  B. Trade timestamp parity: entry_ts, exit_ts, trade count
  C. Exposure distribution: weight stats across all entries
  D. Cost/engine audit: fractional fill correctness

Phase 3 changes ONLY entry exposure (weight < 1.0 when rv > target_vol).
Entry/exit TIMING must be identical to Phase 2.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, MarketState

from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy,
    _ema as p2_ema, _robust_atr as p2_ratr, _vdo as p2_vdo,
)
from strategies.vtrend_x0_volsize.strategy import (
    BARS_PER_YEAR_4H,
    VTrendX0VolsizeConfig, VTrendX0VolsizeStrategy,
    _ema as p3_ema, _realized_vol as p3_realized_vol,
    _robust_atr as p3_ratr, _vdo as p3_vdo,
)

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
COST = SCENARIOS["base"]
INITIAL_CASH = 10_000.0
DEBUG_WINDOW = 500


def run_backtest(strategy, feed):
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=COST,
        initial_cash=INITIAL_CASH, warmup_mode="no_trade",
    )
    return engine.run()


# =========================================================================
# LAYER A: Raw rule parity (indicator-level, state-free)
# =========================================================================

def layer_a_raw_rule_parity(feed):
    """Compare precomputed indicators between Phase 2 and Phase 3."""
    print("=" * 70)
    print("LAYER A: RAW RULE PARITY (X0 Phase 3 vs X0 Phase 2)")
    print("=" * 70)

    h4 = feed.h4_bars
    d1 = feed.d1_bars
    n = len(h4)

    close = np.array([b.close for b in h4], dtype=np.float64)
    high = np.array([b.high for b in h4], dtype=np.float64)
    low = np.array([b.low for b in h4], dtype=np.float64)
    volume = np.array([b.volume for b in h4], dtype=np.float64)
    taker_buy = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)

    # Entry-side indicators (standalone)
    checks_standalone = [
        ("ema_fast (standalone)", p2_ema(close, 30), p3_ema(close, 30)),
        ("ema_slow (standalone)", p2_ema(close, 120), p3_ema(close, 120)),
        ("vdo (standalone)", p2_vdo(close, high, low, volume, taker_buy, 12, 28),
                             p3_vdo(close, high, low, volume, taker_buy, 12, 28)),
        ("ratr (standalone)", p2_ratr(high, low, close, 0.90, 100, 20),
                              p3_ratr(high, low, close, 0.90, 100, 20)),
    ]

    # Strategy-level indicators
    p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p3_strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())
    p2_strat.on_init(h4, d1)
    p3_strat.on_init(h4, d1)

    checks_strategy = [
        ("ema_fast (strategy)", p2_strat._ema_fast, p3_strat._ema_fast),
        ("ema_slow (strategy)", p2_strat._ema_slow, p3_strat._ema_slow),
        ("ratr (strategy)", p2_strat._ratr, p3_strat._ratr),
        ("vdo (strategy)", p2_strat._vdo, p3_strat._vdo),
        ("d1_regime_ok", p2_strat._d1_regime_ok, p3_strat._d1_regime_ok),
    ]

    all_identical = True
    entry_parity = True
    exit_parity = True

    print("\n  --- Entry-side indicators (standalone) ---")
    for name, a, b in checks_standalone:
        result = _compare_arrays(name, a, b)
        if not result:
            all_identical = False
            entry_parity = False

    print("\n  --- Strategy-level indicators ---")
    for name, a, b in checks_strategy:
        result = _compare_arrays(name, a, b)
        if not result:
            all_identical = False
            if "regime" in name or "ema" in name or "vdo" in name:
                entry_parity = False
            if "ratr" in name:
                exit_parity = False

    # Verify Phase 3 has _rv (new indicator)
    print(f"\n  --- Phase 3 new indicator ---")
    assert p3_strat._rv is not None, "Phase 3 must have _rv"
    rv = p3_strat._rv
    n_valid_rv = np.sum(~np.isnan(rv))
    n_nan_rv = np.sum(np.isnan(rv))
    valid_rv = rv[~np.isnan(rv)]
    print(f"  realized_vol: {n} values, {n_valid_rv} valid, {n_nan_rv} NaN")
    if n_valid_rv > 0:
        print(f"    min={np.min(valid_rv):.6f}, median={np.median(valid_rv):.6f}, "
              f"max={np.max(valid_rv):.6f}")
        print(f"    First valid at index {np.argmax(~np.isnan(rv))}")

    print(f"\n  >> RAW ENTRY PARITY: {'CLEAN' if entry_parity else 'ISSUE'}")
    print(f"  >> RAW EXIT PARITY: {'CLEAN' if exit_parity else 'ISSUE'}")

    return entry_parity, exit_parity, p2_strat, p3_strat


def _compare_arrays(name, a, b):
    if a is None or b is None:
        print(f"  {name}: one is None!")
        return False
    nan_a = np.isnan(a.astype(float))
    nan_b = np.isnan(b.astype(float))
    if np.any(nan_a != nan_b):
        print(f"  {name}: NaN mismatch at {np.sum(nan_a != nan_b)} positions")
        return False
    valid = ~nan_a
    if np.allclose(a[valid], b[valid], atol=0, rtol=0):
        print(f"  {name}: BIT-IDENTICAL ({len(a)} values)")
        return True
    else:
        max_diff = np.max(np.abs(a[valid].astype(float) - b[valid].astype(float)))
        print(f"  {name}: DIFFERS (max diff = {max_diff})")
        return False


# =========================================================================
# LAYER B: Trade timestamp parity
# =========================================================================

def layer_b_trade_timestamp_parity(feed):
    """Compare entry/exit timestamps between Phase 2 and Phase 3."""
    print("\n" + "=" * 70)
    print("LAYER B: TRADE TIMESTAMP PARITY (Phase 3 vs Phase 2)")
    print("=" * 70)

    h4 = feed.h4_bars
    d1 = feed.d1_bars

    # --- B.1: Signal-level debug window ---
    print(f"\n  --- B.1: Signal debug window (first {DEBUG_WINDOW} bars) ---")

    p2 = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p3 = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())
    p2.on_init(h4, d1)
    p3.on_init(h4, d1)

    signal_diffs = []
    timing_diffs = []  # only timing differences (ignoring exposure value)
    for i in range(min(len(h4), DEBUG_WINDOW)):
        bar = h4[i]
        state = MarketState(
            bar=bar, h4_bars=h4, d1_bars=d1,
            bar_index=i, d1_index=-1,
            cash=10_000.0, btc_qty=0.0, nav=10_000.0,
            exposure=0.0, entry_price_avg=0.0, position_entry_nav=0.0,
        )
        sig_p2 = p2.on_bar(state)
        sig_p3 = p3.on_bar(state)

        p2_exp = sig_p2.target_exposure if sig_p2 else None
        p3_exp = sig_p3.target_exposure if sig_p3 else None
        p2_reason = sig_p2.reason if sig_p2 else None
        p3_reason = sig_p3.reason if sig_p3 else None

        # Check timing parity: same reason, same timing (ignoring exposure value)
        p2_has_signal = sig_p2 is not None
        p3_has_signal = sig_p3 is not None

        if p2_has_signal != p3_has_signal or p2_reason != p3_reason:
            timing_diffs.append({
                "bar_index": i,
                "p2": f"{p2_reason}({p2_exp})" if sig_p2 else "None",
                "p3": f"{p3_reason}({p3_exp})" if sig_p3 else "None",
            })

        if p2_exp != p3_exp or p2_reason != p3_reason:
            signal_diffs.append({
                "bar_index": i,
                "p2": f"{p2_reason}({p2_exp})" if sig_p2 else "None",
                "p3": f"{p3_reason}({p3_exp})" if sig_p3 else "None",
            })

    print(f"  Total signal diffs (timing+value): {len(signal_diffs)}")
    print(f"  TIMING-ONLY diffs (different bar or reason): {len(timing_diffs)}")

    if timing_diffs:
        print(f"\n  TIMING DIFFS (first 20):")
        for d in timing_diffs[:20]:
            print(f"    bar[{d['bar_index']}]: P2={d['p2']} vs P3={d['p3']}")
    else:
        print(f"  No timing diffs in debug window — signal timing is parity-clean")

    if signal_diffs:
        # Show a few exposure-only diffs (expected)
        expo_only = [d for d in signal_diffs if d not in timing_diffs]
        print(f"\n  Exposure-only diffs (expected, first 10):")
        for d in expo_only[:10]:
            print(f"    bar[{d['bar_index']}]: P2={d['p2']} vs P3={d['p3']}")

    # --- B.2: Full backtest comparison ---
    print(f"\n  --- B.2: Full backtest comparison ---")

    p2_result = run_backtest(VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig()), feed)
    p3_result = run_backtest(VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig()), feed)

    n_p2 = len(p2_result.trades)
    n_p3 = len(p3_result.trades)
    print(f"  Trade count: P2={n_p2}, P3={n_p3} "
          f"{'IDENTICAL' if n_p2 == n_p3 else f'DIFFER (delta={n_p3 - n_p2})'}")

    f_p2 = len(p2_result.fills)
    f_p3 = len(p3_result.fills)
    print(f"  Fill count:  P2={f_p2}, P3={f_p3} "
          f"{'IDENTICAL' if f_p2 == f_p3 else f'DIFFER (delta={f_p3 - f_p2})'}")

    # Compare entry/exit timestamps trade-by-trade
    entry_ts_match = 0
    exit_ts_match = 0
    entry_ts_diffs = []
    exit_ts_diffs = []
    reason_match = 0
    n_compare = min(n_p2, n_p3)

    for idx in range(n_compare):
        tp2 = p2_result.trades[idx]
        tp3 = p3_result.trades[idx]

        if tp2.entry_ts_ms == tp3.entry_ts_ms:
            entry_ts_match += 1
        else:
            entry_ts_diffs.append({
                "trade_idx": idx,
                "p2_entry_ts": tp2.entry_ts_ms,
                "p3_entry_ts": tp3.entry_ts_ms,
                "p2_reason": tp2.entry_reason,
                "p3_reason": tp3.entry_reason,
            })

        if tp2.exit_ts_ms == tp3.exit_ts_ms:
            exit_ts_match += 1
        else:
            exit_ts_diffs.append({
                "trade_idx": idx,
                "p2_exit_ts": tp2.exit_ts_ms,
                "p3_exit_ts": tp3.exit_ts_ms,
                "p2_exit_reason": tp2.exit_reason,
                "p3_exit_reason": tp3.exit_reason,
            })

        if tp2.entry_reason == tp3.entry_reason and tp2.exit_reason == tp3.exit_reason:
            reason_match += 1

    print(f"\n  Entry timestamp match: {entry_ts_match}/{n_compare} "
          f"({'ALL MATCH' if entry_ts_match == n_compare else 'MISMATCH'})")
    print(f"  Exit timestamp match:  {exit_ts_match}/{n_compare} "
          f"({'ALL MATCH' if exit_ts_match == n_compare else 'MISMATCH'})")
    print(f"  Reason match:          {reason_match}/{n_compare}")

    if entry_ts_diffs:
        print(f"\n  ENTRY TIMESTAMP DIFFS (first 20):")
        for d in entry_ts_diffs[:20]:
            print(f"    Trade #{d['trade_idx']}: P2={d['p2_entry_ts']} vs P3={d['p3_entry_ts']} "
                  f"(P2={d['p2_reason']}, P3={d['p3_reason']})")

    if exit_ts_diffs:
        print(f"\n  EXIT TIMESTAMP DIFFS (first 20):")
        for d in exit_ts_diffs[:20]:
            print(f"    Trade #{d['trade_idx']}: P2={d['p2_exit_ts']} vs P3={d['p3_exit_ts']} "
                  f"(P2={d['p2_exit_reason']}, P3={d['p3_exit_reason']})")

    # Extra trades check
    if n_p2 != n_p3:
        extra_label = "P3" if n_p3 > n_p2 else "P2"
        extra_count = abs(n_p3 - n_p2)
        print(f"\n  {extra_label} has {extra_count} extra trade(s)")
        if n_p3 > n_p2:
            for idx in range(n_p2, n_p3):
                t = p3_result.trades[idx]
                print(f"    P3 trade #{idx}: entry={t.entry_ts_ms}, exit={t.exit_ts_ms}, "
                      f"reason={t.entry_reason}/{t.exit_reason}")
        else:
            for idx in range(n_p3, n_p2):
                t = p2_result.trades[idx]
                print(f"    P2 trade #{idx}: entry={t.entry_ts_ms}, exit={t.exit_ts_ms}, "
                      f"reason={t.entry_reason}/{t.exit_reason}")

    # Metrics comparison
    s_p2 = p2_result.summary
    s_p3 = p3_result.summary
    metrics = [
        "cagr_pct", "sharpe", "sortino", "calmar",
        "max_drawdown_mid_pct", "trades", "win_rate_pct",
        "profit_factor", "avg_trade_pnl", "avg_exposure",
        "fees_total", "total_return_pct", "turnover_per_year",
    ]

    print(f"\n  --- Metrics comparison ---")
    print(f"  {'Metric':30s} {'P2 (E5exit)':>15s} {'P3 (volsize)':>15s} {'Delta':>12s}")
    print(f"  {'-'*72}")
    for m in metrics:
        v2 = s_p2.get(m, "N/A")
        v3 = s_p3.get(m, "N/A")
        if isinstance(v2, (int, float)) and isinstance(v3, (int, float)):
            delta = v3 - v2
            print(f"  {m:30s} {v2:>15.4f} {v3:>15.4f} {delta:>+12.4f}")
        else:
            print(f"  {m:30s} {str(v2):>15s} {str(v3):>15s}")

    timing_clean = (
        entry_ts_match == n_compare and
        exit_ts_match == n_compare and
        n_p2 == n_p3 and
        len(timing_diffs) == 0
    )

    return p2_result, p3_result, timing_clean, entry_ts_diffs, exit_ts_diffs


# =========================================================================
# LAYER C: Exposure distribution
# =========================================================================

def layer_c_exposure_distribution(p2_result, p3_result, p3_strat):
    """Analyze entry exposure distribution across all Phase 3 trades."""
    print("\n" + "=" * 70)
    print("LAYER C: EXPOSURE DISTRIBUTION")
    print("=" * 70)

    p3_trades = p3_result.trades
    p2_trades = p2_result.trades

    # Extract entry fills (BUY fills only, first fill per trade)
    p2_entry_fills = [f for f in p2_result.fills if f.side.value == "BUY"]
    p3_entry_fills = [f for f in p3_result.fills if f.side.value == "BUY"]

    print(f"  P2 entry fills: {len(p2_entry_fills)}")
    print(f"  P3 entry fills: {len(p3_entry_fills)}")

    # Compare qty ratios (Phase 3 qty / Phase 2 qty) as proxy for weight
    n_compare = min(len(p2_entry_fills), len(p3_entry_fills))
    weights = []
    for i in range(n_compare):
        if p2_entry_fills[i].qty > 1e-12:
            w = p3_entry_fills[i].qty / p2_entry_fills[i].qty
            weights.append(w)

    if weights:
        w_arr = np.array(weights)
        print(f"\n  Entry weight distribution (P3_qty / P2_qty proxy):")
        print(f"    n         = {len(w_arr)}")
        print(f"    min       = {np.min(w_arr):.6f}")
        print(f"    p10       = {np.percentile(w_arr, 10):.6f}")
        print(f"    median    = {np.median(w_arr):.6f}")
        print(f"    mean      = {np.mean(w_arr):.6f}")
        print(f"    p90       = {np.percentile(w_arr, 90):.6f}")
        print(f"    max       = {np.max(w_arr):.6f}")

        at_cap = np.sum(w_arr >= 0.999)
        at_floor = np.sum(w_arr <= 0.001)
        fractional = np.sum((w_arr > 0.001) & (w_arr < 0.999))
        print(f"\n    At cap (w>=0.999):       {at_cap} trades ({100*at_cap/len(w_arr):.1f}%)")
        print(f"    Fractional (0<w<1):      {fractional} trades ({100*fractional/len(w_arr):.1f}%)")
        print(f"    At floor (w<=0.001):     {at_floor} trades ({100*at_floor/len(w_arr):.1f}%)")

    # Theoretical weight formula
    target_vol = p3_strat._c.target_vol
    vol_floor = p3_strat._c.vol_floor
    print(f"\n  Theoretical weight formula: target_vol={target_vol} / max(rv, vol_floor={vol_floor})")
    print(f"  Max theoretical weight before clip = {target_vol / vol_floor:.4f}")
    print(f"  After clip to [0,1] → max = 1.0")
    if p3_strat._rv is not None:
        rv = p3_strat._rv
        valid_rv = rv[~np.isnan(rv)]
        rv_below_target = np.sum(valid_rv < target_vol)
        print(f"  Bars where rv < target_vol ({target_vol}): {rv_below_target}/{len(valid_rv)} "
              f"({100*rv_below_target/len(valid_rv):.1f}%)")
        print(f"  → These bars would have weight > 1.0 (clipped to 1.0)")

    # PnL comparison
    print(f"\n  --- PnL impact ---")
    n_compare_trades = min(len(p2_trades), len(p3_trades))
    pnl_diffs = []
    for i in range(n_compare_trades):
        t2 = p2_trades[i]
        t3 = p3_trades[i]
        pnl_diffs.append({
            "p2_pnl": t2.pnl,
            "p3_pnl": t3.pnl,
            "delta": t3.pnl - t2.pnl,
            "p2_ret": t2.return_pct,
            "p3_ret": t3.return_pct,
            "p2_qty": t2.qty,
            "p3_qty": t3.qty,
        })

    if pnl_diffs:
        pnl_d = np.array([d["delta"] for d in pnl_diffs])
        print(f"  PnL delta (P3 - P2): mean={np.mean(pnl_d):+.2f}, "
              f"median={np.median(pnl_d):+.2f}, "
              f"sum={np.sum(pnl_d):+.2f}")
        print(f"  P2 total PnL: {sum(d['p2_pnl'] for d in pnl_diffs):+.2f}")
        print(f"  P3 total PnL: {sum(d['p3_pnl'] for d in pnl_diffs):+.2f}")

        # Verify: when weight ~= 1.0, PnL should be similar
        similar_pnl = sum(1 for w, d in zip(weights[:n_compare_trades], pnl_diffs)
                         if abs(w - 1.0) < 0.01 and abs(d["delta"]) < 1.0)
        full_weight_trades = sum(1 for w in weights[:n_compare_trades] if abs(w - 1.0) < 0.01)
        if full_weight_trades > 0:
            print(f"\n  Full-weight trades (w~1.0): {full_weight_trades}")
            print(f"    PnL ~identical (<$1 diff): {similar_pnl}/{full_weight_trades}")

    return weights


# =========================================================================
# LAYER D: Cost/engine audit
# =========================================================================

def layer_d_cost_engine_audit(p2_result, p3_result):
    """Verify fees/slippage/trade logging with fractional exposure."""
    print("\n" + "=" * 70)
    print("LAYER D: COST/ENGINE AUDIT (fractional exposure)")
    print("=" * 70)

    p2_fills = p2_result.fills
    p3_fills = p3_result.fills

    # Fee proportionality check
    print(f"\n  --- Fee proportionality ---")
    n_compare = min(len(p2_fills), len(p3_fills))

    fee_checks_pass = 0
    fee_checks_fail = 0
    fee_details = []

    for i in range(n_compare):
        f2 = p2_fills[i]
        f3 = p3_fills[i]

        # Fee should be proportional to notional
        # fee = qty * fill_px * fee_rate
        # So fee_ratio should equal notional_ratio (= qty_ratio approximately)
        if f2.notional > 1e-8 and f3.notional > 1e-8:
            notional_ratio = f3.notional / f2.notional
            fee_ratio = f3.fee / f2.fee if f2.fee > 1e-12 else float('nan')

            if not math.isnan(fee_ratio) and abs(fee_ratio - notional_ratio) < 1e-8:
                fee_checks_pass += 1
            else:
                fee_checks_fail += 1
                if len(fee_details) < 5:
                    fee_details.append(
                        f"  Fill #{i}: notional_ratio={notional_ratio:.6f}, "
                        f"fee_ratio={fee_ratio:.6f}, "
                        f"diff={abs(fee_ratio - notional_ratio):.2e}")

    print(f"  Fee proportionality: {fee_checks_pass}/{n_compare} pass, "
          f"{fee_checks_fail} fail")
    for d in fee_details:
        print(d)

    # Fill price parity (same fill price for same bar)
    print(f"\n  --- Fill price parity ---")
    price_match = 0
    price_diffs = []
    for i in range(n_compare):
        f2 = p2_fills[i]
        f3 = p3_fills[i]

        if abs(f2.price - f3.price) < 1e-10:
            price_match += 1
        else:
            price_diffs.append({
                "fill_idx": i,
                "p2_price": f2.price,
                "p3_price": f3.price,
                "diff": abs(f2.price - f3.price),
            })

    print(f"  Fill price match: {price_match}/{n_compare} "
          f"({'ALL MATCH' if price_match == n_compare else 'MISMATCH'})")
    if price_diffs:
        print(f"  Price diffs (first 10):")
        for d in price_diffs[:10]:
            print(f"    Fill #{d['fill_idx']}: P2={d['p2_price']:.6f} vs P3={d['p3_price']:.6f}")

    # Fill timestamp parity
    print(f"\n  --- Fill timestamp parity ---")
    ts_match = 0
    ts_diffs = []
    for i in range(n_compare):
        f2 = p2_fills[i]
        f3 = p3_fills[i]
        if f2.ts_ms == f3.ts_ms:
            ts_match += 1
        else:
            ts_diffs.append({"fill_idx": i, "p2_ts": f2.ts_ms, "p3_ts": f3.ts_ms})

    print(f"  Fill timestamp match: {ts_match}/{n_compare} "
          f"({'ALL MATCH' if ts_match == n_compare else 'MISMATCH'})")
    if ts_diffs:
        for d in ts_diffs[:10]:
            print(f"    Fill #{d['fill_idx']}: P2={d['p2_ts']} vs P3={d['p3_ts']}")

    # Reason parity
    print(f"\n  --- Fill reason parity ---")
    reason_match = 0
    for i in range(n_compare):
        if p2_fills[i].reason == p3_fills[i].reason:
            reason_match += 1
    print(f"  Fill reason match: {reason_match}/{n_compare} "
          f"({'ALL MATCH' if reason_match == n_compare else 'MISMATCH'})")

    # Side parity
    side_match = sum(1 for i in range(n_compare) if p2_fills[i].side == p3_fills[i].side)
    print(f"  Fill side match:   {side_match}/{n_compare} "
          f"({'ALL MATCH' if side_match == n_compare else 'MISMATCH'})")

    # Summary fees
    p2_total_fees = sum(f.fee for f in p2_fills)
    p3_total_fees = sum(f.fee for f in p3_fills)
    print(f"\n  Total fees: P2=${p2_total_fees:.2f}, P3=${p3_total_fees:.2f}")
    print(f"  Fee delta: ${p3_total_fees - p2_total_fees:+.2f} "
          f"({'lower' if p3_total_fees < p2_total_fees else 'higher'} — "
          f"{'expected' if p3_total_fees <= p2_total_fees else 'check'} "
          f"with fractional exposure)")

    cost_clean = (
        fee_checks_fail == 0 and
        price_match == n_compare and
        ts_match == n_compare and
        reason_match == n_compare and
        side_match == n_compare
    )

    return cost_clean


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("P3.3 Parity Audit: X0 Phase 3 Timing Verification + Exposure Audit")
    print("=" * 70)
    print("Loading data...")
    feed = DataFeed(DATA_PATH, warmup_days=365)
    print(f"  {feed}")
    print(f"  H4 bars: {len(feed.h4_bars)}, D1 bars: {len(feed.d1_bars)}")

    # Layer A
    entry_parity, exit_parity, p2_strat, p3_strat = layer_a_raw_rule_parity(feed)

    # Layer B
    p2_result, p3_result, timing_clean, entry_diffs, exit_diffs = \
        layer_b_trade_timestamp_parity(feed)

    # Layer C
    weights = layer_c_exposure_distribution(p2_result, p3_result, p3_strat)

    # Layer D
    cost_clean = layer_d_cost_engine_audit(p2_result, p3_result)

    # Final verdict
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)

    verdicts = {
        "Layer A — Raw entry parity": entry_parity,
        "Layer A — Raw exit parity": exit_parity,
        "Layer B — Trade timestamp parity": timing_clean,
        "Layer D — Cost/engine correctness": cost_clean,
    }

    for name, ok in verdicts.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")

    all_timing_pass = entry_parity and exit_parity and timing_clean

    if all_timing_pass:
        print(f"\n  >> Signal and trade timestamps are parity-clean against X0 Phase 2;")
        print(f"     Phase 3 changes economic exposure only.")
    else:
        print(f"\n  >> TIMING PARITY ISSUE DETECTED — see details above")

    all_pass = all(verdicts.values())
    print(f"\n  Overall: {'ALL CHECKS PASS' if all_pass else 'ISSUES FOUND'}")
    print("=" * 70)

    # Save results
    out = {
        "layer_a_entry_parity": entry_parity,
        "layer_a_exit_parity": exit_parity,
        "layer_b_timing_clean": timing_clean,
        "layer_b_entry_ts_diffs": len(entry_diffs),
        "layer_b_exit_ts_diffs": len(exit_diffs),
        "layer_b_p2_trades": len(p2_result.trades),
        "layer_b_p3_trades": len(p3_result.trades),
        "layer_b_p2_fills": len(p2_result.fills),
        "layer_b_p3_fills": len(p3_result.fills),
        "layer_c_weight_count": len(weights) if weights else 0,
        "layer_c_weight_min": float(np.min(weights)) if weights else None,
        "layer_c_weight_median": float(np.median(weights)) if weights else None,
        "layer_c_weight_mean": float(np.mean(weights)) if weights else None,
        "layer_c_weight_max": float(np.max(weights)) if weights else None,
        "layer_d_cost_clean": cost_clean,
        "all_pass": all_pass,
        "p2_summary": p2_result.summary,
        "p3_summary": p3_result.summary,
    }
    outpath = Path(__file__).parent / "p3_3_results.json"
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nResults saved to {outpath}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
