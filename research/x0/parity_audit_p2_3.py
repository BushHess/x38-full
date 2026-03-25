"""P2.3 Parity Audit: X0 Phase 2 differential verification.

Three-layer audit:
  A. Raw entry rule parity: X0 Phase 2 vs X0 Phase 1 (indicator-level)
  B. Executed strategy delta: trade-by-trade comparison (debug + full)
  C. Exit-focused delta: matched-entry trades exit behavior comparison

Plus: E5 exit transplant validation (X0 Phase 2 vs E5+EMA21)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, MarketState

from strategies.vtrend_x0.strategy import (
    VTrendX0Config, VTrendX0Strategy,
    _ema as x0_ema, _atr as x0_atr, _vdo as x0_vdo,
)
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy,
    _ema as x0e5_ema, _robust_atr as x0e5_ratr, _vdo as x0e5_vdo,
)
from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config, VTrendE5Ema21D1Strategy,
    _robust_atr as e5ema_ratr,
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
# LAYER A: Raw entry rule parity (indicator-level, state-free)
# =========================================================================

def layer_a_raw_entry_parity(feed):
    """Compare precomputed entry-side indicators between Phase 1 and Phase 2."""
    print("=" * 70)
    print("LAYER A: RAW ENTRY PARITY (X0 Phase 2 vs X0 Phase 1)")
    print("=" * 70)

    h4 = feed.h4_bars
    d1 = feed.d1_bars
    n = len(h4)

    close = np.array([b.close for b in h4], dtype=np.float64)
    high = np.array([b.high for b in h4], dtype=np.float64)
    low = np.array([b.low for b in h4], dtype=np.float64)
    volume = np.array([b.volume for b in h4], dtype=np.float64)
    taker_buy = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)

    # Phase 1 indicators
    p1_ema_fast = x0_ema(close, 30)  # max(5, 120//4) = 30
    p1_ema_slow = x0_ema(close, 120)
    p1_vdo = x0_vdo(close, high, low, volume, taker_buy, 12, 28)

    # Phase 2 indicators
    p2_ema_fast = x0e5_ema(close, 30)
    p2_ema_slow = x0e5_ema(close, 120)
    p2_vdo = x0e5_vdo(close, high, low, volume, taker_buy, 12, 28)

    # Compare via strategy instances for D1 regime
    p1_strat = VTrendX0Strategy(VTrendX0Config())
    p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p1_strat.on_init(h4, d1)
    p2_strat.on_init(h4, d1)

    checks = [
        ("ema_fast (standalone)", p1_ema_fast, p2_ema_fast),
        ("ema_slow (standalone)", p1_ema_slow, p2_ema_slow),
        ("vdo (standalone)", p1_vdo, p2_vdo),
        ("ema_fast (strategy)", p1_strat._ema_fast, p2_strat._ema_fast),
        ("ema_slow (strategy)", p1_strat._ema_slow, p2_strat._ema_slow),
        ("vdo (strategy)", p1_strat._vdo, p2_strat._vdo),
        ("d1_regime_ok", p1_strat._d1_regime_ok, p2_strat._d1_regime_ok),
    ]

    all_identical = True
    for name, a, b in checks:
        if a is None or b is None:
            print(f"  {name}: one is None!")
            all_identical = False
            continue
        nan_a, nan_b = np.isnan(a.astype(float)), np.isnan(b.astype(float))
        mismatched_nan = nan_a != nan_b
        if np.any(mismatched_nan):
            print(f"  {name}: NaN mismatch at {np.sum(mismatched_nan)} positions")
            all_identical = False
        else:
            valid = ~nan_a
            if np.allclose(a[valid], b[valid], atol=0, rtol=0):
                print(f"  {name}: BIT-IDENTICAL ({len(a)} values)")
            else:
                max_diff = np.max(np.abs(a[valid].astype(float) - b[valid].astype(float)))
                print(f"  {name}: DIFFERS (max diff = {max_diff})")
                all_identical = False

    # Verify ATR vs rATR is DIFFERENT (expected)
    p1_atr = p1_strat._atr
    p2_ratr = p2_strat._ratr
    print(f"\n  --- ATR vs rATR (expected to DIFFER) ---")
    print(f"  Phase 1 uses _atr (standard ATR-14): shape={p1_atr.shape}")
    print(f"  Phase 2 uses _ratr (robust ATR-20): shape={p2_ratr.shape}")
    # Find valid overlap
    valid = ~np.isnan(p1_atr) & ~np.isnan(p2_ratr)
    n_valid = np.sum(valid)
    if n_valid > 0:
        diff = np.abs(p1_atr[valid] - p2_ratr[valid])
        max_d = np.max(diff)
        mean_d = np.mean(diff)
        same = np.sum(diff == 0)
        print(f"  Valid overlap: {n_valid} bars, max_diff={max_d:.4f}, "
              f"mean_diff={mean_d:.4f}, identical={same}")
        if max_d > 0:
            print(f"  CONFIRMED: ATR and rATR produce different values (expected)")
        else:
            print(f"  WARNING: ATR and rATR are identical — this is unexpected!")

    if all_identical:
        print(f"\n  >> Raw entry logic is parity-clean against X0 Phase 1")
    else:
        print(f"\n  >> ENTRY PARITY ISSUE DETECTED")

    return all_identical


# =========================================================================
# LAYER B: Executed strategy delta (trade-by-trade)
# =========================================================================

def extract_trades(result):
    """Extract trades directly from BacktestResult.trades."""
    return result.trades


def layer_b_executed_delta(feed):
    """Compare X0 Phase 1 vs Phase 2 at trade level."""
    print("\n" + "=" * 70)
    print("LAYER B: EXECUTED STRATEGY DELTA (trade-by-trade)")
    print("=" * 70)

    h4 = feed.h4_bars
    d1 = feed.d1_bars

    # --- B.1: Debug window (signal-by-signal) ---
    print(f"\n  --- B.1: Signal debug window (first {DEBUG_WINDOW} bars) ---")

    p1 = VTrendX0Strategy(VTrendX0Config())
    p2 = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p1.on_init(h4, d1)
    p2.on_init(h4, d1)

    signal_diffs = []
    for i in range(min(len(h4), DEBUG_WINDOW)):
        bar = h4[i]
        state = MarketState(
            bar=bar, h4_bars=h4, d1_bars=d1,
            bar_index=i, d1_index=-1,
            cash=10_000.0, btc_qty=0.0, nav=10_000.0,
            exposure=0.0, entry_price_avg=0.0, position_entry_nav=0.0,
        )
        sig_p1 = p1.on_bar(state)
        sig_p2 = p2.on_bar(state)

        p1_exp = sig_p1.target_exposure if sig_p1 else None
        p2_exp = sig_p2.target_exposure if sig_p2 else None
        p1_reason = sig_p1.reason if sig_p1 else None
        p2_reason = sig_p2.reason if sig_p2 else None

        if p1_exp != p2_exp or p1_reason != p2_reason:
            signal_diffs.append({
                "bar_index": i,
                "close_time": bar.close_time,
                "p1": f"{p1_reason}({p1_exp})" if sig_p1 else "None",
                "p2": f"{p2_reason}({p2_exp})" if sig_p2 else "None",
            })

    if not signal_diffs:
        print(f"  No signal differences in first {DEBUG_WINDOW} bars")
        print(f"  (Note: differences expected later when rATR diverges from ATR)")
    else:
        print(f"  {len(signal_diffs)} signal differences:")
        for d in signal_diffs[:20]:
            print(f"    bar[{d['bar_index']}]: P1={d['p1']} vs P2={d['p2']}")

    # --- B.2: Full backtest comparison ---
    print(f"\n  --- B.2: Full backtest comparison ---")

    p1_result = run_backtest(VTrendX0Strategy(VTrendX0Config()), feed)
    p2_result = run_backtest(VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig()), feed)

    n_p1 = len(p1_result.trades)
    n_p2 = len(p2_result.trades)
    print(f"  Trade count: P1={n_p1}, P2={n_p2} "
          f"{'SAME' if n_p1 == n_p2 else f'DIFFER (delta={n_p2 - n_p1})'}")

    f_p1 = len(p1_result.fills)
    f_p2 = len(p2_result.fills)
    print(f"  Fill count:  P1={f_p1}, P2={f_p2}")

    # Summary comparison
    s_p1 = p1_result.summary
    s_p2 = p2_result.summary
    metrics = [
        "cagr_pct", "sharpe", "sortino", "calmar",
        "max_drawdown_mid_pct", "trades", "win_rate_pct",
        "profit_factor", "avg_trade_pnl", "avg_exposure",
        "fees_total", "total_return_pct", "turnover_per_year",
    ]

    print(f"\n  --- Metrics comparison ---")
    print(f"  {'Metric':30s} {'P1 (X0)':>15s} {'P2 (X0-E5)':>15s} {'Delta':>12s}")
    print(f"  {'-'*72}")
    for m in metrics:
        v1 = s_p1.get(m, "N/A")
        v2 = s_p2.get(m, "N/A")
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            delta = v2 - v1
            print(f"  {m:30s} {v1:>15.4f} {v2:>15.4f} {delta:>+12.4f}")
        else:
            print(f"  {m:30s} {str(v1):>15s} {str(v2):>15s}")

    return p1_result, p2_result, signal_diffs


# =========================================================================
# LAYER C: Exit-focused delta on matched-entry trades
# =========================================================================

def layer_c_exit_delta(p1_result, p2_result):
    """Match trades by entry timestamp and compare exit behavior."""
    print("\n" + "=" * 70)
    print("LAYER C: EXIT-FOCUSED DELTA (matched-entry trades)")
    print("=" * 70)

    p1_trades = p1_result.trades
    p2_trades = p2_result.trades

    # Build lookup by entry_ts_ms
    p1_by_entry = {t.entry_ts_ms: t for t in p1_trades}
    p2_by_entry = {t.entry_ts_ms: t for t in p2_trades}

    matched_entries = set(p1_by_entry.keys()) & set(p2_by_entry.keys())
    p1_only = set(p1_by_entry.keys()) - set(p2_by_entry.keys())
    p2_only = set(p2_by_entry.keys()) - set(p1_by_entry.keys())

    print(f"  P1 trades: {len(p1_trades)}")
    print(f"  P2 trades: {len(p2_trades)}")
    print(f"  Matched entries: {len(matched_entries)}")
    print(f"  P1-only entries: {len(p1_only)}")
    print(f"  P2-only entries: {len(p2_only)}")

    if not matched_entries:
        print("  No matched entries to compare!")
        return [], p1_only, p2_only

    # Compare exit behavior on matched trades
    exit_diffs = []
    same_exit = 0
    print(f"\n  --- Matched-entry exit comparison (first 30 diffs) ---")
    print(f"  {'#':>4s} {'Entry_TS':>15s} {'P1_ExitTS':>15s} {'P2_ExitTS':>15s} "
          f"{'P1_Hold':>8s} {'P2_Hold':>8s} {'P1_Ret%':>10s} {'P2_Ret%':>10s} "
          f"{'P1_ExitReason':>20s} {'P2_ExitReason':>20s}")

    sorted_matched = sorted(matched_entries)
    rows_printed = 0
    for entry_ts in sorted_matched:
        t1 = p1_by_entry[entry_ts]
        t2 = p2_by_entry[entry_ts]

        hold_p1 = (t1.exit_ts_ms - t1.entry_ts_ms) / 3_600_000  # hours
        hold_p2 = (t2.exit_ts_ms - t2.entry_ts_ms) / 3_600_000
        ret_p1 = t1.return_pct
        ret_p2 = t2.return_pct

        is_same = (t1.exit_ts_ms == t2.exit_ts_ms)
        if is_same:
            same_exit += 1
        else:
            exit_diffs.append({
                "entry_ts": entry_ts,
                "p1_exit_ts": t1.exit_ts_ms,
                "p2_exit_ts": t2.exit_ts_ms,
                "p1_hold_h": hold_p1,
                "p2_hold_h": hold_p2,
                "p1_ret_pct": ret_p1,
                "p2_ret_pct": ret_p2,
                "p1_exit_reason": t1.exit_reason,
                "p2_exit_reason": t2.exit_reason,
                "hold_delta_h": hold_p2 - hold_p1,
                "ret_delta_pct": ret_p2 - ret_p1,
            })

        if rows_printed < 30 and not is_same:
            print(f"  {rows_printed:>4d} {entry_ts:>15d} {t1.exit_ts_ms:>15d} {t2.exit_ts_ms:>15d} "
                  f"{hold_p1:>8.0f}h {hold_p2:>8.0f}h {ret_p1:>+10.2f} {ret_p2:>+10.2f} "
                  f"{t1.exit_reason:>20s} {t2.exit_reason:>20s}")
            rows_printed += 1

    print(f"\n  Summary:")
    print(f"  Same exit timestamp: {same_exit}/{len(matched_entries)} "
          f"({100*same_exit/len(matched_entries):.1f}%)")
    print(f"  Different exit: {len(exit_diffs)}/{len(matched_entries)}")

    if exit_diffs:
        hold_deltas = [d["hold_delta_h"] for d in exit_diffs]
        ret_deltas = [d["ret_delta_pct"] for d in exit_diffs]
        print(f"\n  Exit diffs statistics (P2 - P1):")
        print(f"    Hold period delta: mean={np.mean(hold_deltas):+.1f}h, "
              f"median={np.median(hold_deltas):+.1f}h, "
              f"min={np.min(hold_deltas):+.1f}h, max={np.max(hold_deltas):+.1f}h")
        print(f"    Return delta:      mean={np.mean(ret_deltas):+.3f}%, "
              f"median={np.median(ret_deltas):+.3f}%, "
              f"min={np.min(ret_deltas):+.3f}%, max={np.max(ret_deltas):+.3f}%")

        # Exit reason breakdown
        p1_reasons = {}
        p2_reasons = {}
        for d in exit_diffs:
            p1_reasons[d["p1_exit_reason"]] = p1_reasons.get(d["p1_exit_reason"], 0) + 1
            p2_reasons[d["p2_exit_reason"]] = p2_reasons.get(d["p2_exit_reason"], 0) + 1
        print(f"\n  Exit reason breakdown (diffs only):")
        print(f"    P1: {dict(p1_reasons)}")
        print(f"    P2: {dict(p2_reasons)}")

    return exit_diffs, p1_only, p2_only


# =========================================================================
# E5 EXIT TRANSPLANT VALIDATION
# =========================================================================

def e5_exit_transplant_validation(feed, p2_result):
    """Validate X0 Phase 2 exit module matches E5+EMA21."""
    print("\n" + "=" * 70)
    print("E5 EXIT TRANSPLANT VALIDATION (X0 Phase 2 vs E5+EMA21)")
    print("=" * 70)

    h4 = feed.h4_bars
    d1 = feed.d1_bars

    # 1. Indicator-level: compare _robust_atr output
    close = np.array([b.close for b in h4], dtype=np.float64)
    high = np.array([b.high for b in h4], dtype=np.float64)
    low = np.array([b.low for b in h4], dtype=np.float64)

    ratr_x0e5 = x0e5_ratr(high, low, close, cap_q=0.90, cap_lb=100, period=20)
    ratr_e5ema = e5ema_ratr(high, low, close, cap_q=0.90, cap_lb=100, period=20)

    valid = ~np.isnan(ratr_x0e5) & ~np.isnan(ratr_e5ema)
    n_valid = np.sum(valid)
    if n_valid > 0 and np.allclose(ratr_x0e5[valid], ratr_e5ema[valid], atol=0, rtol=0):
        print(f"  _robust_atr output: BIT-IDENTICAL ({n_valid} valid values)")
        ratr_identical = True
    else:
        max_diff = np.max(np.abs(ratr_x0e5[valid] - ratr_e5ema[valid])) if n_valid > 0 else float("nan")
        print(f"  _robust_atr output: DIFFERS (max_diff={max_diff})")
        ratr_identical = False

    # 2. Strategy-level: compare indicators via strategy instances
    p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    e5ema_strat = VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config())
    p2_strat.on_init(h4, d1)
    e5ema_strat.on_init(h4, d1)

    strat_checks = [
        ("ema_fast", p2_strat._ema_fast, e5ema_strat._ema_fast),
        ("ema_slow", p2_strat._ema_slow, e5ema_strat._ema_slow),
        ("ratr", p2_strat._ratr, e5ema_strat._ratr),
        ("vdo", p2_strat._vdo, e5ema_strat._vdo),
        ("d1_regime_ok", p2_strat._d1_regime_ok, e5ema_strat._d1_regime_ok),
    ]

    print(f"\n  Strategy indicator comparison (X0-E5 vs E5+EMA21):")
    all_strat_identical = True
    for name, a, b in strat_checks:
        nan_a = np.isnan(a.astype(float))
        nan_b = np.isnan(b.astype(float))
        if np.any(nan_a != nan_b):
            print(f"    {name}: NaN mismatch")
            all_strat_identical = False
        else:
            v = ~nan_a
            if np.allclose(a[v], b[v], atol=0, rtol=0):
                print(f"    {name}: BIT-IDENTICAL")
            else:
                md = np.max(np.abs(a[v].astype(float) - b[v].astype(float)))
                print(f"    {name}: DIFFERS (max_diff={md})")
                all_strat_identical = False

    if all_strat_identical:
        print(f"\n  All indicators BIT-IDENTICAL → entry+exit inputs match E5+EMA21")

    # 3. Full backtest: X0 Phase 2 vs E5+EMA21
    e5ema_result = run_backtest(
        VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config()), feed)

    n_p2 = len(p2_result.trades)
    n_e5 = len(e5ema_result.trades)
    print(f"\n  Backtest trade count: X0-E5={n_p2}, E5+EMA21={n_e5} "
          f"{'SAME' if n_p2 == n_e5 else 'DIFFER'}")

    # Compare trade-by-trade
    trade_diffs = 0
    n_compare = min(n_p2, n_e5)
    first_diffs = []
    for idx in range(n_compare):
        tp = p2_result.trades[idx]
        te = e5ema_result.trades[idx]
        if (tp.entry_ts_ms != te.entry_ts_ms or
                tp.exit_ts_ms != te.exit_ts_ms or
                abs(tp.entry_price - te.entry_price) > 1e-10 or
                abs(tp.exit_price - te.exit_price) > 1e-10):
            trade_diffs += 1
            if len(first_diffs) < 5:
                first_diffs.append(f"  Trade #{idx}: "
                    f"entry_ts {tp.entry_ts_ms} vs {te.entry_ts_ms}, "
                    f"exit_ts {tp.exit_ts_ms} vs {te.exit_ts_ms}")

    if trade_diffs == 0:
        print(f"  All {n_compare} trades BIT-IDENTICAL")
        print(f"  >> X0 Phase 2 is parity-clean against E5+EMA21")
    else:
        print(f"  {trade_diffs}/{n_compare} trades differ")
        for d in first_diffs:
            print(d)

    # Metrics
    s_p2 = p2_result.summary
    s_e5 = e5ema_result.summary
    key_metrics = ["sharpe", "cagr_pct", "max_drawdown_mid_pct", "trades"]
    print(f"\n  Key metrics:")
    print(f"  {'Metric':30s} {'X0-E5':>12s} {'E5+EMA21':>12s} {'Match':>8s}")
    for m in key_metrics:
        v1 = s_p2.get(m)
        v2 = s_e5.get(m)
        match = "YES" if isinstance(v1, (int, float)) and abs(v1 - v2) < 1e-6 else "NO"
        print(f"  {m:30s} {str(v1):>12s} {str(v2):>12s} {match:>8s}")

    return ratr_identical, all_strat_identical, trade_diffs == 0


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("P2.3 Parity Audit: X0 Phase 2 Differential Verification")
    print("=" * 70)
    print("Loading data...")
    feed = DataFeed(DATA_PATH, warmup_days=365)
    print(f"  {feed}")
    print(f"  H4 bars: {len(feed.h4_bars)}, D1 bars: {len(feed.d1_bars)}")

    # Layer A
    entry_parity = layer_a_raw_entry_parity(feed)

    # Layer B
    p1_result, p2_result, signal_diffs = layer_b_executed_delta(feed)

    # Layer C
    exit_diffs, p1_only, p2_only = layer_c_exit_delta(p1_result, p2_result)

    # E5 transplant validation
    ratr_ok, indicators_ok, trades_ok = e5_exit_transplant_validation(feed, p2_result)

    # Final verdict
    print("\n" + "=" * 70)
    print("FINAL VERDICT")
    print("=" * 70)

    verdicts = {
        "Layer A (entry parity)": entry_parity,
        "E5 rATR function parity": ratr_ok,
        "E5 all indicators parity": indicators_ok,
        "E5 trade-level parity": trades_ok,
    }

    for name, ok in verdicts.items():
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")

    p1_entry_set = set(t.entry_ts_ms for t in p1_result.trades)
    p2_entry_set = set(t.entry_ts_ms for t in p2_result.trades)
    n_matched = len(p1_entry_set & p2_entry_set)

    print(f"\n  Entry parity: {'CLEAN' if entry_parity else 'ISSUE'}")
    print(f"  Exit delta: {len(exit_diffs)} trades differ on exit (expected — different ATR)")
    print(f"  E5 transplant: {'VALIDATED' if all(verdicts.values()) else 'ISSUE'}")

    all_pass = all(verdicts.values())
    print(f"\n  Overall: {'ALL CHECKS PASS' if all_pass else 'ISSUES FOUND'}")
    print("=" * 70)

    # Save results
    out = {
        "layer_a_entry_parity": entry_parity,
        "layer_b_signal_diffs_debug_window": len(signal_diffs),
        "layer_b_p1_trades": len(p1_result.trades),
        "layer_b_p2_trades": len(p2_result.trades),
        "layer_c_matched_entries_exit_diffs": len(exit_diffs),
        "layer_c_p1_only_entries": len(p1_only),
        "layer_c_p2_only_entries": len(p2_only),
        "e5_ratr_identical": ratr_ok,
        "e5_indicators_identical": indicators_ok,
        "e5_trades_identical": trades_ok,
        "p1_summary": p1_result.summary,
        "p2_summary": p2_result.summary,
    }
    outpath = Path(__file__).parent / "p2_3_results.json"
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nResults saved to {outpath}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
