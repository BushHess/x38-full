#!/usr/bin/env python3
"""Step 1: Export V10 baseline trade-level + event-level CSVs.

Runs V10 backtest (harsh scenario), then exports:
  - v10_baseline_trades_harsh.csv  (closed trades with regime labels)
  - v10_baseline_events_harsh.csv  (bar-by-bar event log for churn analysis)

The event log captures every signal decision and fill, enabling measurement
of the stop-out → re-enter → stop-out cycle and fee drag.

Usage:
    python experiments/overlayA/step1_export.py
"""

from __future__ import annotations

import bisect
import csv
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Bar, Fill, MarketState, Side, Signal, Trade
from v10.research.regime import AnalyticalRegime, classify_d1_regimes
from v10.strategies.v8_apex import Regime, V8ApexConfig, V8ApexStrategy

# ── constants ─────────────────────────────────────────────────────────────
DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
OUTDIR = PROJECT_ROOT / "out/v10_fix_loop"

REGIME_RANK = {
    "SHOCK": 0, "BEAR": 1, "CHOP": 2,
    "TOPPING": 3, "NEUTRAL": 4, "BULL": 5,
}

TRADE_COLUMNS = [
    "trade_id", "entry_ts", "exit_ts", "entry_price", "exit_price",
    "qty", "notional", "gross_pnl", "net_pnl", "fees_total", "return_pct",
    "bars_held", "days_held", "mfe_pct", "mae_pct",
    "entry_reason", "exit_reason",
    "exposure_at_entry", "exposure_at_exit",
    "regime_at_entry", "regime_at_exit", "holding_regime_mode", "worst_regime",
    "n_buy_fills", "n_sell_fills",
]

EVENT_COLUMNS = [
    "ts", "bar_index", "event_type", "reason",
    "price", "nav", "exposure_before", "exposure_after",
    "notional_before", "notional_after",
    "regime_label", "regime_d1_analytical",
    "fill_qty", "fill_fee", "trade_id_ref",
]


# ── Instrumented Strategy ─────────────────────────────────────────────────

class InstrumentedV8Apex(V8ApexStrategy):
    """V8ApexStrategy with bar-by-bar event logging."""

    def __init__(self, cfg: V8ApexConfig) -> None:
        super().__init__(cfg)
        self.signal_log: list[dict] = []

    def on_bar(self, state: MarketState) -> Signal | None:
        idx = state.bar_index
        mid = state.bar.close
        in_pos = state.btc_qty > 1e-8
        exposure = state.exposure

        # Resolve D1 regime (same logic as parent)
        d1i = state.d1_index
        regime = (
            self._d1_regime[d1i]
            if 0 <= d1i < len(self._d1_regime)
            else Regime.RISK_OFF
        )

        # Call parent for actual signal
        signal = super().on_bar(state)

        # Classify event
        if signal is not None and signal.target_exposure == 0.0:
            event_type = "exit_signal"
            reason = signal.reason
        elif signal is not None and not in_pos:
            event_type = "entry_signal"
            reason = signal.reason
        elif signal is not None:
            event_type = "add_signal"
            reason = signal.reason
        elif not in_pos:
            event_type = "entry_blocked"
            reason = self._diagnose_block(state, idx, mid, regime)
        else:
            # In position, no exit signal → hold (skip logging)
            return signal

        self.signal_log.append({
            "bar_ts_ms": state.bar.close_time,
            "bar_index": idx,
            "event_type": event_type,
            "reason": reason,
            "price": mid,
            "nav": round(state.nav, 2),
            "exposure": round(exposure, 4),
            "regime": regime.value,
            "in_position": in_pos,
            "target_exposure": (
                round(signal.target_exposure, 4)
                if signal is not None and signal.target_exposure is not None
                else None
            ),
        })

        return signal

    def _diagnose_block(
        self, state: MarketState, idx: int, mid: float, regime: Regime,
    ) -> str:
        """Determine which gate blocked entry. Returns first blocking reason."""
        c = self.cfg

        # Gate 0: Overlay A
        if self._emergency_dd_cooldown_remaining > 0:
            if self.cfg.escalating_cooldown and self._active_cooldown_type:
                return self._active_cooldown_type
            return "cooldown_after_emergency_dd"

        if regime == Regime.RISK_OFF:
            return "regime_off"
        if idx - self._last_add_idx < c.entry_cooldown_bars:
            return "cooldown_add"
        if idx - self._last_exit_idx < c.exit_cooldown_bars:
            return "cooldown_exit"

        vdo = self._h4_vdo[idx] if idx < len(self._h4_vdo) else 0.0
        if vdo <= c.vdo_entry_threshold:
            return "vdo_below_threshold"

        hma_v = self._h4_hma[idx] if idx < len(self._h4_hma) else mid
        rsi_v = self._h4_rsi[idx] if idx < len(self._h4_rsi) else 50.0
        above_hma = not np.isnan(hma_v) and mid > hma_v
        oversold = rsi_v < c.rsi_oversold
        if not above_hma and not oversold:
            return "trend_not_confirmed"

        # Exposure gap check
        d1i = state.d1_index
        va = (
            self._d1_vol_ann[d1i]
            if 0 <= d1i < len(self._d1_vol_ann)
            else 1.0
        )
        base = min(c.max_total_exposure, c.target_vol_annual / va)
        if regime == Regime.CAUTION:
            base *= c.caution_mult
        base = min(base, c.max_total_exposure)
        gap = base - state.exposure
        if gap < c.min_target_to_add:
            return "exposure_gap_small"

        return "size_below_min"


# ── Helpers ───────────────────────────────────────────────────────────────

def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _find_regime_at_ts(
    ts_ms: int,
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
) -> str:
    idx = bisect.bisect_left(d1_close_times, ts_ms) - 1
    if idx >= 0:
        return regimes[idx].value
    return "NEUTRAL"


def _compute_trade_regimes(
    trade: Trade,
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
) -> dict:
    entry_regime = _find_regime_at_ts(trade.entry_ts_ms, d1_close_times, regimes)
    exit_regime = _find_regime_at_ts(trade.exit_ts_ms, d1_close_times, regimes)

    i_start = max(bisect.bisect_left(d1_close_times, trade.entry_ts_ms) - 1, 0)
    i_end = bisect.bisect_left(d1_close_times, trade.exit_ts_ms)
    holding = [regimes[i].value for i in range(i_start, min(i_end, len(regimes)))]
    if not holding:
        holding = [entry_regime]

    mode = Counter(holding).most_common(1)[0][0]
    worst = min(holding, key=lambda r: REGIME_RANK.get(r, 5))

    return {
        "regime_at_entry": entry_regime,
        "regime_at_exit": exit_regime,
        "holding_regime_mode": mode,
        "worst_regime": worst,
    }


def _compute_mfe_mae(
    trade: Trade, h4_bars: list[Bar], h4_open_times: np.ndarray,
) -> tuple[float, float]:
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


def _match_fills(trade: Trade, fills: list[Fill]) -> list[Fill]:
    return [f for f in fills if trade.entry_ts_ms <= f.ts_ms <= trade.exit_ts_ms]


def _find_exposure_at_ts(ts_ms: int, equity_snaps) -> float:
    """Find exposure from equity snapshots at the bar closest to ts_ms."""
    if not equity_snaps:
        return 0.0
    # Binary search for snap with close_time <= ts_ms
    lo, hi = 0, len(equity_snaps) - 1
    while lo < hi:
        m = (lo + hi + 1) // 2
        if equity_snaps[m].close_time <= ts_ms:
            lo = m
        else:
            hi = m - 1
    return round(equity_snaps[lo].exposure, 4)


# ── Trade CSV ─────────────────────────────────────────────────────────────

def build_trades_csv(
    trades: list[Trade],
    fills: list[Fill],
    equity_snaps,
    h4_bars: list[Bar],
    h4_open_times: np.ndarray,
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
) -> list[dict]:
    rows = []
    for trade in trades:
        regime_info = _compute_trade_regimes(trade, d1_close_times, regimes)
        mfe, mae = _compute_mfe_mae(trade, h4_bars, h4_open_times)
        matched = _match_fills(trade, fills)
        fees_total = sum(f.fee for f in matched)
        n_buy = sum(1 for f in matched if f.side == Side.BUY)
        n_sell = sum(1 for f in matched if f.side == Side.SELL)

        # Bars held
        i_s = bisect.bisect_left(h4_open_times, trade.entry_ts_ms)
        i_e = bisect.bisect_right(h4_open_times, trade.exit_ts_ms)
        bars_held = max(0, i_e - i_s)

        net_pnl = trade.pnl
        gross_pnl = net_pnl + fees_total

        # Exposure: find equity snap just before entry (pre-fill) and at exit
        # Entry fill happens at bar open; equity snap is at bar close.
        # Use snap BEFORE entry bar for exposure_at_entry.
        exposure_at_entry = _find_exposure_at_ts(trade.entry_ts_ms - 1, equity_snaps)
        exposure_at_exit = _find_exposure_at_ts(trade.exit_ts_ms, equity_snaps)

        rows.append({
            "trade_id": trade.trade_id,
            "entry_ts": _ms_to_iso(trade.entry_ts_ms),
            "exit_ts": _ms_to_iso(trade.exit_ts_ms),
            "entry_price": round(trade.entry_price, 2),
            "exit_price": round(trade.exit_price, 2),
            "qty": round(trade.qty, 8),
            "notional": round(trade.qty * trade.entry_price, 2),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "fees_total": round(fees_total, 2),
            "return_pct": round(trade.return_pct, 4),
            "bars_held": bars_held,
            "days_held": round(trade.days_held, 2),
            "mfe_pct": mfe,
            "mae_pct": mae,
            "entry_reason": trade.entry_reason,
            "exit_reason": trade.exit_reason,
            "exposure_at_entry": exposure_at_entry,
            "exposure_at_exit": exposure_at_exit,
            **regime_info,
            "n_buy_fills": n_buy,
            "n_sell_fills": n_sell,
        })
    return rows


# ── Event CSV ─────────────────────────────────────────────────────────────

def build_events_csv(
    signal_log: list[dict],
    fills: list[Fill],
    trades: list[Trade],
    d1_close_times: list[int],
    regimes: list[AnalyticalRegime],
    equity_snaps,
    report_start_ms: int = 0,
) -> list[dict]:
    """Build unified event log from signal decisions + fills.

    Event types:
      - entry_signal:  strategy decided to enter/add (at bar close)
      - exit_signal:   strategy decided to exit (at bar close)
      - add_signal:    strategy decided to add to position (at bar close)
      - entry_blocked: strategy was flat but entry gates blocked (at bar close)
      - entry_fill:    buy fill executed (at next bar open)
      - exit_fill:     sell fill executed (at next bar open)
    """
    events: list[dict] = []

    # 1. Signal events (from instrumented strategy, reporting period only)
    for sig in signal_log:
        if sig["bar_ts_ms"] < report_start_ms:
            continue
        analytical = _find_regime_at_ts(sig["bar_ts_ms"], d1_close_times, regimes)
        events.append({
            "ts": _ms_to_iso(sig["bar_ts_ms"]),
            "bar_index": sig["bar_index"],
            "event_type": sig["event_type"],
            "reason": sig["reason"],
            "price": round(sig["price"], 2),
            "nav": sig["nav"],
            "exposure_before": sig["exposure"],
            "exposure_after": sig["exposure"],  # same — fill hasn't happened yet
            "notional_before": round(sig["nav"] * sig["exposure"], 2),
            "notional_after": round(sig["nav"] * sig["exposure"], 2),
            "regime_label": sig["regime"],
            "regime_d1_analytical": analytical,
            "fill_qty": "",
            "fill_fee": "",
            "trade_id_ref": "",
        })

    # 2. Fill events (from backtest result)
    for fill in fills:
        # Find which trade this fill belongs to
        trade_ref = ""
        for t in trades:
            if t.entry_ts_ms <= fill.ts_ms <= t.exit_ts_ms:
                trade_ref = str(t.trade_id)
                break

        event_type = "entry_fill" if fill.side == Side.BUY else "exit_fill"
        analytical = _find_regime_at_ts(fill.ts_ms, d1_close_times, regimes)

        # Get exposure before/after from equity snaps
        exp_before = _find_exposure_at_ts(fill.ts_ms - 1, equity_snaps)
        exp_after = _find_exposure_at_ts(fill.ts_ms, equity_snaps)

        events.append({
            "ts": _ms_to_iso(fill.ts_ms),
            "bar_index": "",
            "event_type": event_type,
            "reason": fill.reason,
            "price": round(fill.price, 2),
            "nav": "",
            "exposure_before": exp_before,
            "exposure_after": exp_after,
            "notional_before": round(fill.notional if fill.side == Side.BUY else 0.0, 2),
            "notional_after": round(fill.notional if fill.side == Side.SELL else 0.0, 2),
            "regime_label": "",
            "regime_d1_analytical": analytical,
            "fill_qty": round(fill.qty, 8),
            "fill_fee": round(fill.fee, 2),
            "trade_id_ref": trade_ref,
        })

    # Sort by timestamp
    events.sort(key=lambda e: e["ts"])
    return events


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    scenario = "harsh"

    print("Loading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    h4_bars = feed.h4_bars
    d1_bars = feed.d1_bars

    print("Classifying D1 regimes...")
    regimes = classify_d1_regimes(d1_bars)
    d1_close_times = [b.close_time for b in d1_bars]
    h4_open_times = np.array([b.open_time for b in h4_bars], dtype=np.int64)

    print(f"Running V10 backtest ({scenario})...")
    strategy = InstrumentedV8Apex(V8ApexConfig())
    cost = SCENARIOS[scenario]
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=cost,
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP_DAYS,
    )
    result = engine.run()

    trades = result.trades
    fills = result.fills
    equity = result.equity

    print(f"  Trades: {len(trades)}")
    print(f"  Fills:  {len(fills)}")
    print(f"  Signal log entries: {len(strategy.signal_log)}")
    print(f"  Equity snaps: {len(equity)}")

    # ── Trades CSV ──
    print("\nBuilding trades CSV...")
    trade_rows = build_trades_csv(
        trades, fills, equity,
        h4_bars, h4_open_times,
        d1_close_times, regimes,
    )

    trades_path = OUTDIR / f"v10_baseline_trades_{scenario}.csv"
    with open(trades_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRADE_COLUMNS)
        writer.writeheader()
        writer.writerows(trade_rows)
    print(f"  Written: {trades_path.name} ({len(trade_rows)} rows)")

    # ── Events CSV ──
    print("Building events CSV...")
    report_start_ms = getattr(feed, "report_start_ms", 0) or 0
    event_rows = build_events_csv(
        strategy.signal_log, fills, trades,
        d1_close_times, regimes, equity,
        report_start_ms=report_start_ms,
    )

    events_path = OUTDIR / f"v10_baseline_events_{scenario}.csv"
    with open(events_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EVENT_COLUMNS)
        writer.writeheader()
        writer.writerows(event_rows)
    print(f"  Written: {events_path.name} ({len(event_rows)} rows)")

    # ── Verification ──
    print("\n── Verification ──")
    expected_harsh = 103
    actual = len(trade_rows)
    status = "PASS" if actual == expected_harsh else "FAIL"
    print(f"  Trade count: {actual} (expected {expected_harsh}) → {status}")

    # Event type breakdown
    from collections import Counter as C
    evt_counts = C(e["event_type"] for e in event_rows)
    print(f"  Event breakdown: {dict(evt_counts)}")

    # Block reason breakdown (entry_blocked only)
    block_counts = C(
        e["reason"] for e in event_rows if e["event_type"] == "entry_blocked"
    )
    print(f"  Block reasons: {dict(block_counts)}")

    # Exit reason breakdown from trades
    exit_counts = C(t["exit_reason"] for t in trade_rows)
    print(f"  Exit reasons: {dict(exit_counts)}")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Status: {status}")


if __name__ == "__main__":
    main()
