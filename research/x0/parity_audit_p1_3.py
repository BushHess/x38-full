"""P1.3 Parity Audit: X0 Phase 1 vs E0+EMA21 (vtrend_ema21_d1).

Runs both strategies through the same engine on real data and compares:
  1. Bar-by-bar signals (short debug window)
  2. Trade-by-trade matching (full sample)
  3. Summary metrics (full sample)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS

from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Config, VTrendEma21D1Strategy
from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy


DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
COST = SCENARIOS["base"]
INITIAL_CASH = 10_000.0


def run_backtest(strategy, feed):
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=COST,
        initial_cash=INITIAL_CASH,
        warmup_mode="no_trade",
    )
    return engine.run()


def compare_signals_debug(feed, n_bars=200):
    """Compare bar-by-bar signals on first n_bars after warmup."""
    from v10.core.types import MarketState

    h4 = feed.h4_bars
    d1 = feed.d1_bars

    x0 = VTrendX0Strategy(VTrendX0Config())
    e0e = VTrendEma21D1Strategy(VTrendEma21D1Config())

    x0.on_init(h4, d1)
    e0e.on_init(h4, d1)

    # Compare precomputed indicators
    print("=" * 70)
    print("INDICATOR PARITY CHECK")
    print("=" * 70)

    checks = [
        ("ema_fast", x0._ema_fast, e0e._ema_fast),
        ("ema_slow", x0._ema_slow, e0e._ema_slow),
        ("atr", x0._atr, e0e._atr),
        ("vdo", x0._vdo, e0e._vdo),
        ("d1_regime_ok", x0._d1_regime_ok, e0e._d1_regime_ok),
    ]
    import numpy as np
    all_identical = True
    for name, a, b in checks:
        if a is None or b is None:
            print(f"  {name}: one is None!")
            all_identical = False
            continue
        # Handle NaN comparison
        nan_mask = np.isnan(a) & np.isnan(b)
        valid_mask = ~np.isnan(a) & ~np.isnan(b)
        mismatched_nan = np.isnan(a) != np.isnan(b)
        if np.any(mismatched_nan):
            print(f"  {name}: NaN mismatch at {np.sum(mismatched_nan)} positions")
            all_identical = False
        elif np.allclose(a[valid_mask], b[valid_mask], atol=0, rtol=0):
            print(f"  {name}: BIT-IDENTICAL ({len(a)} values)")
        else:
            max_diff = np.max(np.abs(a[valid_mask] - b[valid_mask]))
            print(f"  {name}: DIFFERS (max diff = {max_diff})")
            all_identical = False

    print(f"\n  Overall: {'ALL IDENTICAL' if all_identical else 'DIFFERENCES FOUND'}\n")

    # Now compare bar-by-bar signals
    print("=" * 70)
    print(f"SIGNAL DEBUG WINDOW (first {n_bars} bars)")
    print("=" * 70)

    diffs = []
    for i in range(min(len(h4), n_bars)):
        bar = h4[i]
        state = MarketState(
            bar=bar, h4_bars=h4, d1_bars=d1,
            bar_index=i, d1_index=-1,
            cash=10_000.0, btc_qty=0.0, nav=10_000.0,
            exposure=0.0, entry_price_avg=0.0, position_entry_nav=0.0,
        )
        sig_x0 = x0.on_bar(state)
        sig_e0e = e0e.on_bar(state)

        # Normalize: both None => match; both have signal => compare exposure
        x0_exp = sig_x0.target_exposure if sig_x0 else None
        e0e_exp = sig_e0e.target_exposure if sig_e0e else None

        if x0_exp != e0e_exp:
            diffs.append({
                "bar_index": i,
                "close_time": bar.close_time,
                "x0_signal": f"{sig_x0.reason}({x0_exp})" if sig_x0 else "None",
                "e0e_signal": f"{sig_e0e.reason}({e0e_exp})" if sig_e0e else "None",
            })

    if not diffs:
        print(f"  No signal differences in first {n_bars} bars.")
    else:
        print(f"  {len(diffs)} signal differences found:")
        for d in diffs[:20]:
            print(f"    bar[{d['bar_index']}] ct={d['close_time']}: "
                  f"X0={d['x0_signal']} vs E0E={d['e0e_signal']}")

    return all_identical, diffs


def compare_full_backtest(feed):
    """Run both through the engine and compare trades + metrics."""
    print("\n" + "=" * 70)
    print("FULL BACKTEST PARITY (via BacktestEngine)")
    print("=" * 70)

    x0_strat = VTrendX0Strategy(VTrendX0Config())
    e0e_strat = VTrendEma21D1Strategy(VTrendEma21D1Config())

    x0_result = run_backtest(x0_strat, feed)
    e0e_result = run_backtest(e0e_strat, feed)

    # Compare trade count
    n_x0 = len(x0_result.trades)
    n_e0e = len(e0e_result.trades)
    print(f"\n  Trade count: X0={n_x0}, E0E={n_e0e} "
          f"{'MATCH' if n_x0 == n_e0e else 'DIFFER'}")

    # Compare fill count
    f_x0 = len(x0_result.fills)
    f_e0e = len(e0e_result.fills)
    print(f"  Fill count:  X0={f_x0}, E0E={f_e0e} "
          f"{'MATCH' if f_x0 == f_e0e else 'DIFFER'}")

    # Compare equity length
    eq_x0 = len(x0_result.equity)
    eq_e0e = len(e0e_result.equity)
    print(f"  Equity pts:  X0={eq_x0}, E0E={eq_e0e} "
          f"{'MATCH' if eq_x0 == eq_e0e else 'DIFFER'}")

    # Trade-by-trade comparison
    print(f"\n  --- Trade-by-trade comparison ---")
    trade_diffs = []
    for idx in range(min(n_x0, n_e0e)):
        tx = x0_result.trades[idx]
        te = e0e_result.trades[idx]
        mismatches = []
        if tx.entry_ts_ms != te.entry_ts_ms:
            mismatches.append(f"entry_ts: {tx.entry_ts_ms} vs {te.entry_ts_ms}")
        if tx.exit_ts_ms != te.exit_ts_ms:
            mismatches.append(f"exit_ts: {tx.exit_ts_ms} vs {te.exit_ts_ms}")
        if abs(tx.entry_price - te.entry_price) > 1e-10:
            mismatches.append(f"entry_px: {tx.entry_price} vs {te.entry_price}")
        if abs(tx.exit_price - te.exit_price) > 1e-10:
            mismatches.append(f"exit_px: {tx.exit_price} vs {te.exit_price}")
        if abs(tx.qty - te.qty) > 1e-10:
            mismatches.append(f"qty: {tx.qty} vs {te.qty}")
        if abs(tx.pnl - te.pnl) > 1e-6:
            mismatches.append(f"pnl: {tx.pnl} vs {te.pnl}")
        if mismatches:
            trade_diffs.append((idx, mismatches))

    if not trade_diffs:
        print(f"  All {min(n_x0, n_e0e)} trades BIT-IDENTICAL "
              f"(entry_ts, exit_ts, entry_px, exit_px, qty, pnl)")
    else:
        print(f"  {len(trade_diffs)} trade differences found:")
        for idx, mm in trade_diffs[:20]:
            print(f"    Trade #{idx}: {'; '.join(mm)}")

    # Equity curve comparison
    print(f"\n  --- Equity curve comparison ---")
    import numpy as np
    if eq_x0 == eq_e0e and eq_x0 > 0:
        x0_nav = np.array([e.nav_mid for e in x0_result.equity])
        e0e_nav = np.array([e.nav_mid for e in e0e_result.equity])
        max_nav_diff = np.max(np.abs(x0_nav - e0e_nav))
        print(f"  Max NAV diff: {max_nav_diff:.10f} "
              f"{'BIT-IDENTICAL' if max_nav_diff == 0 else 'NEAR-IDENTICAL' if max_nav_diff < 0.01 else 'DIFFERS'}")

    # Summary metrics comparison
    print(f"\n  --- Summary metrics comparison ---")
    s_x0 = x0_result.summary
    s_e0e = e0e_result.summary

    metrics_to_compare = [
        "cagr_pct", "sharpe", "sortino", "calmar",
        "max_drawdown_mid_pct", "trades", "win_rate_pct",
        "profit_factor", "avg_trade_pnl", "avg_exposure",
        "time_in_market_pct", "fees_total", "total_return_pct",
        "fee_drag_pct_per_year", "turnover_per_year",
    ]

    all_match = True
    for m in metrics_to_compare:
        v_x0 = s_x0.get(m)
        v_e0e = s_e0e.get(m)
        if isinstance(v_x0, (int, float)) and isinstance(v_e0e, (int, float)):
            diff = abs(v_x0 - v_e0e)
            match = diff < 1e-6
            status = "MATCH" if match else f"DIFF={diff:.6f}"
        elif v_x0 == v_e0e:
            match = True
            status = "MATCH"
        else:
            match = False
            status = f"X0={v_x0} vs E0E={v_e0e}"
        if not match:
            all_match = False
        print(f"  {m:30s}: X0={v_x0!s:>15s}  E0E={v_e0e!s:>15s}  {status}")

    print(f"\n  Overall metrics: {'ALL IDENTICAL' if all_match else 'DIFFERENCES FOUND'}")

    return trade_diffs, all_match, s_x0, s_e0e


def main():
    print("Loading data...")
    feed = DataFeed(DATA_PATH, warmup_days=365)
    print(f"  {feed}")

    # Part 1: Indicator + signal debug window
    indicators_ok, signal_diffs = compare_signals_debug(feed, n_bars=500)

    # Part 2: Full backtest parity
    trade_diffs, metrics_ok, s_x0, s_e0e = compare_full_backtest(feed)

    # Final verdict
    print("\n" + "=" * 70)
    print("PARITY VERDICT")
    print("=" * 70)

    is_clean = indicators_ok and len(signal_diffs) == 0 and len(trade_diffs) == 0 and metrics_ok

    if is_clean:
        print("  Phase 1 is parity-clean against vtrend_ema21_d1 within tested scope.")
        print("  BIT-IDENTICAL: indicators, signals, trades, equity, metrics.")
    else:
        issues = []
        if not indicators_ok:
            issues.append("indicators differ")
        if signal_diffs:
            issues.append(f"{len(signal_diffs)} signal diffs")
        if trade_diffs:
            issues.append(f"{len(trade_diffs)} trade diffs")
        if not metrics_ok:
            issues.append("metrics differ")
        print(f"  PARITY ISSUES: {', '.join(issues)}")

    print("=" * 70)
    return 0 if is_clean else 1


if __name__ == "__main__":
    sys.exit(main())
