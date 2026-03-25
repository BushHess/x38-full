#!/usr/bin/env python3
"""Trade-level dataset export for V10 + V11 with regime labels and MFE/MAE.

Runs full backtests for both strategies across harsh + base cost scenarios,
enriches each closed trade with:
  - 4 regime labels (entry, exit, holding mode, worst)
  - MFE / MAE (from H4 bar high/low)
  - Matched fill fees
  - Bars held, notional, buy/sell fill counts

Outputs:
  trades_v10_harsh.csv, trades_v10_base.csv
  trades_v11_harsh.csv, trades_v11_base.csv
  log_trade_export.txt
"""

import bisect
import csv
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, BacktestResult, Bar, Fill, Side, Trade
from v10.research.regime import AnalyticalRegime, classify_d1_regimes
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

# ── constants ──────────────────────────────────────────────────────────────
DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
OUTDIR = Path(__file__).resolve().parent
SYMBOL = "BTCUSDT"

SCENARIO_LIST = ["harsh", "base"]

# Regime rank: lower = worse (used for worst_regime)
REGIME_RANK = {
    "SHOCK": 0,
    "BEAR": 1,
    "CHOP": 2,
    "TOPPING": 3,
    "NEUTRAL": 4,
    "BULL": 5,
}

CSV_COLUMNS = [
    "trade_id", "strategy_id", "symbol", "scenario", "window_id",
    "entry_ts", "exit_ts", "entry_price", "exit_price",
    "side", "qty", "notional",
    "gross_pnl", "net_pnl", "fees_total", "return_pct",
    "bars_held", "days_held",
    "mfe_pct", "mae_pct",
    "entry_reason", "exit_reason",
    "entry_regime", "exit_regime", "holding_regime_mode", "worst_regime",
    "n_buy_fills", "n_sell_fills",
]


# ── helpers ────────────────────────────────────────────────────────────────

def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _make_v10():
    return V8ApexStrategy(V8ApexConfig())


def _make_v11():
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def _run_backtest(strategy, scenario_name: str, feed: DataFeed) -> BacktestResult:
    cost = SCENARIOS[scenario_name]
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=cost,
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP_DAYS,
    )
    return engine.run()


# ── regime helpers ─────────────────────────────────────────────────────────

def _find_regime_at_ts(
    ts_ms: int,
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
) -> str:
    """Find D1 regime at timestamp using strict < alignment."""
    idx = bisect.bisect_left(d1_close_times, ts_ms) - 1
    if idx >= 0:
        return regimes[idx].value
    return "NEUTRAL"


def _compute_trade_regimes(
    trade: Trade,
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
) -> dict:
    """Compute 4 regime labels for a trade."""
    entry_regime = _find_regime_at_ts(trade.entry_ts_ms, d1_close_times, regimes)
    exit_regime = _find_regime_at_ts(trade.exit_ts_ms, d1_close_times, regimes)

    # Holding period regimes: all D1 bars with close_time in [entry, exit)
    i_start = bisect.bisect_left(d1_close_times, trade.entry_ts_ms) - 1
    i_start = max(i_start, 0)
    i_end = bisect.bisect_left(d1_close_times, trade.exit_ts_ms)

    holding_regimes = [regimes[i].value for i in range(i_start, min(i_end, len(regimes)))]

    if not holding_regimes:
        holding_regimes = [entry_regime]

    # Mode (most common)
    counts = Counter(holding_regimes)
    holding_regime_mode = counts.most_common(1)[0][0]

    # Worst (lowest rank number)
    worst_regime = min(holding_regimes, key=lambda r: REGIME_RANK.get(r, 5))

    return {
        "entry_regime": entry_regime,
        "exit_regime": exit_regime,
        "holding_regime_mode": holding_regime_mode,
        "worst_regime": worst_regime,
    }


# ── MFE / MAE ─────────────────────────────────────────────────────────────

def _compute_mfe_mae(
    trade: Trade,
    h4_bars: list[Bar],
    h4_open_times: np.ndarray,
) -> tuple[float, float]:
    """Compute MFE/MAE from H4 bar highs/lows during holding period.

    MFE = (max_high - entry_price) / entry_price * 100
    MAE = (entry_price - min_low) / entry_price * 100
    Both clipped >= 0.
    """
    # Find H4 bars in [entry_ts, exit_ts] range
    i_start = bisect.bisect_left(h4_open_times, trade.entry_ts_ms)
    i_end = bisect.bisect_right(h4_open_times, trade.exit_ts_ms)

    if i_start >= i_end:
        return 0.0, 0.0

    max_high = max(h4_bars[i].high for i in range(i_start, min(i_end, len(h4_bars))))
    min_low = min(h4_bars[i].low for i in range(i_start, min(i_end, len(h4_bars))))

    entry = trade.entry_price
    if entry < 1e-12:
        return 0.0, 0.0

    mfe = max(0.0, (max_high - entry) / entry * 100.0)
    mae = max(0.0, (entry - min_low) / entry * 100.0)
    return round(mfe, 4), round(mae, 4)


# ── fill matching ──────────────────────────────────────────────────────────

def _match_fills(trade: Trade, fills: list[Fill]) -> list[Fill]:
    """Match fills belonging to this trade by timestamp range."""
    matched = []
    for f in fills:
        if f.ts_ms >= trade.entry_ts_ms and f.ts_ms <= trade.exit_ts_ms:
            matched.append(f)
    return matched


# ── enrich ─────────────────────────────────────────────────────────────────

def _enrich_trade(
    trade: Trade,
    h4_bars: list[Bar],
    h4_open_times: np.ndarray,
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
    fills: list[Fill],
    strategy_id: str,
    scenario: str,
    window_id: str = "FULL",
) -> dict:
    """Enrich a single Trade into a flat dict for CSV export."""
    # Regime labels
    regime_info = _compute_trade_regimes(trade, d1_close_times, regimes)

    # MFE / MAE
    mfe_pct, mae_pct = _compute_mfe_mae(trade, h4_bars, h4_open_times)

    # Match fills
    matched = _match_fills(trade, fills)
    fees_total = sum(f.fee for f in matched)
    n_buy = sum(1 for f in matched if f.side == Side.BUY)
    n_sell = sum(1 for f in matched if f.side == Side.SELL)

    # Bars held: count H4 bars in [entry, exit]
    i_start = bisect.bisect_left(h4_open_times, trade.entry_ts_ms)
    i_end = bisect.bisect_right(h4_open_times, trade.exit_ts_ms)
    bars_held = max(0, i_end - i_start)

    net_pnl = trade.pnl
    gross_pnl = net_pnl + fees_total

    tid = f"{strategy_id}_{scenario}_{trade.trade_id}"

    return {
        "trade_id": tid,
        "strategy_id": strategy_id,
        "symbol": SYMBOL,
        "scenario": scenario,
        "window_id": window_id,
        "entry_ts": _ms_to_iso(trade.entry_ts_ms),
        "exit_ts": _ms_to_iso(trade.exit_ts_ms),
        "entry_price": round(trade.entry_price, 2),
        "exit_price": round(trade.exit_price, 2),
        "side": "LONG",
        "qty": round(trade.qty, 8),
        "notional": round(trade.qty * trade.entry_price, 2),
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": round(net_pnl, 2),
        "fees_total": round(fees_total, 2),
        "return_pct": round(trade.return_pct, 4),
        "bars_held": bars_held,
        "days_held": round(trade.days_held, 2),
        "mfe_pct": mfe_pct,
        "mae_pct": mae_pct,
        "entry_reason": trade.entry_reason,
        "exit_reason": trade.exit_reason,
        **regime_info,
        "n_buy_fills": n_buy,
        "n_sell_fills": n_sell,
    }


# ── CSV writer ─────────────────────────────────────────────────────────────

def _write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ── main ───────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    log_lines: list[str] = []
    log_lines.append(f"Trade export started: {datetime.now(timezone.utc).isoformat()}")
    log_lines.append(f"Command: python {Path(__file__).name}")
    log_lines.append(f"Period: {START} → {END}, warmup={WARMUP_DAYS}d")
    log_lines.append(f"Scenarios: {SCENARIO_LIST}")
    log_lines.append("")

    # Load data once
    print("Loading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    h4_bars = feed.h4_bars
    d1_bars = feed.d1_bars

    # Pre-compute regime classification
    print("Classifying D1 regimes...")
    regimes = classify_d1_regimes(d1_bars)
    d1_close_times = [b.close_time for b in d1_bars]

    # Pre-compute H4 open_times array for bisect
    h4_open_times = np.array([b.open_time for b in h4_bars], dtype=np.int64)

    # Strategy factories
    strategies = {
        "V10": _make_v10,
        "V11": _make_v11,
    }

    all_pass = True

    for strategy_id, factory in strategies.items():
        for scenario in SCENARIO_LIST:
            label = f"{strategy_id}_{scenario}"
            print(f"\nRunning {label}...")

            # Fresh strategy + fresh feed for each run
            strat = factory()
            feed_run = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
            result = _run_backtest(strat, scenario, feed_run)

            expected_trades = result.summary.get("trades", 0)
            actual_trades = len(result.trades)

            print(f"  Trades: {actual_trades} (summary says {expected_trades})")

            # Enrich trades
            rows = []
            for trade in result.trades:
                row = _enrich_trade(
                    trade=trade,
                    h4_bars=h4_bars,
                    h4_open_times=h4_open_times,
                    d1_close_times=d1_close_times,
                    regimes=regimes,
                    fills=result.fills,
                    strategy_id=strategy_id,
                    scenario=scenario,
                )
                rows.append(row)

            # Write CSV
            csv_name = f"trades_{strategy_id.lower()}_{scenario}.csv"
            csv_path = OUTDIR / csv_name
            _write_csv(rows, csv_path)
            print(f"  Written: {csv_path.name} ({len(rows)} rows)")

            # Verification
            count_match = actual_trades == expected_trades
            regimes_ok = all(
                r["entry_regime"] and r["exit_regime"]
                and r["holding_regime_mode"] and r["worst_regime"]
                for r in rows
            )
            mfe_ok = all(r["mfe_pct"] >= 0 and r["mae_pct"] >= 0 for r in rows)

            # Net PnL sum vs final_nav - initial
            pnl_sum = sum(r["net_pnl"] for r in rows)
            final_nav = result.summary.get("final_nav_mid", 0.0)

            status = "PASS" if (count_match and regimes_ok and mfe_ok) else "FAIL"
            if not count_match:
                all_pass = False
            if not regimes_ok:
                all_pass = False
            if not mfe_ok:
                all_pass = False

            log_lines.append(f"── {label} ──")
            log_lines.append(f"  File:         {csv_name}")
            log_lines.append(f"  Rows:         {len(rows)}")
            log_lines.append(f"  Expected:     {expected_trades}")
            log_lines.append(f"  Count match:  {'YES' if count_match else 'NO'}")
            log_lines.append(f"  Regimes OK:   {'YES' if regimes_ok else 'NO'}")
            log_lines.append(f"  MFE/MAE OK:   {'YES' if mfe_ok else 'NO'}")
            log_lines.append(f"  Net PnL sum:  {pnl_sum:.2f}")
            log_lines.append(f"  Final NAV:    {final_nav:.2f}")
            log_lines.append(f"  Status:       {status}")
            log_lines.append("")

    elapsed = time.time() - t0
    verdict = "PASS" if all_pass else "FAIL"
    log_lines.append(f"Overall: {verdict}")
    log_lines.append(f"Elapsed: {elapsed:.1f}s")
    log_lines.append(f"Finished: {datetime.now(timezone.utc).isoformat()}")

    # Write log
    log_path = OUTDIR / "log_trade_export.txt"
    log_path.write_text("\n".join(log_lines))
    print(f"\nLog: {log_path.name}")
    print(f"Verdict: {verdict}")
    print(f"Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
