#!/usr/bin/env python3
"""P0.1 -- Event scan for gated floor exits."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.e0_exit_floor.p0_1_exit_floor_benchmark import (
    ATR_P,
    D1_EMA,
    END,
    ER_LOOKBACK,
    EXIT_N,
    INITIAL_CASH,
    RATR_CAP_LB,
    RATR_CAP_Q,
    RATR_PERIOD,
    START,
    SLOW,
    TRAIL,
    VDO_FAST,
    VDO_SLOW,
    VDO_THR,
    WARMUP,
    ExitFloorConfig,
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
    X0ExitFloorStrategy,
    _atr,
    _context_from_er,
    _d1_regime_map,
    _efficiency_ratio,
    _ema,
    _rolling_low_shifted,
    _ts,
    _vdo,
)
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import Fill, MarketState, SCENARIOS, Signal, Side


OUTDIR = Path(__file__).resolve().parent
DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    description: str
    predicate: callable


class LoggingFloorStrategy(X0ExitFloorStrategy):
    def __init__(self, config: ExitFloorConfig) -> None:
        super().__init__(config)
        self._close: np.ndarray | None = None
        self._high: np.ndarray | None = None
        self._low: np.ndarray | None = None
        self._er30: np.ndarray | None = None
        self._open_index: dict[int, int] = {}
        self._entry_ts_ms: int | None = None
        self._entry_idx: int | None = None
        self._entry_price: float = 0.0
        self._entry_atr: float = math.nan
        self._peak_idx: int | None = None
        self._event_id = 0
        self._events: list[dict] = []

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        super().on_init(h4_bars, d1_bars)
        self._close = np.array([b.close for b in h4_bars], dtype=np.float64)
        self._high = np.array([b.high for b in h4_bars], dtype=np.float64)
        self._low = np.array([b.low for b in h4_bars], dtype=np.float64)
        self._er30 = _efficiency_ratio(self._close, ER_LOOKBACK)
        self._open_index = {int(b.open_time): i for i, b in enumerate(h4_bars)}

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (
            self._ema_fast is None
            or self._ema_slow is None
            or self._atr is None
            or self._ratr is None
            or self._vdo is None
            or self._ll_exit is None
            or self._d1_regime_ok is None
            or self._close is None
            or self._er30 is None
            or i < 1
        ):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if any(math.isnan(x) for x in (ema_f, ema_s, atr_val, ratr_val, vdo_val)):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if regime_ok and trend_up and vdo_val > self._c.vdo_threshold:
                self._in_position = True
                self._peak_price = price
                self._peak_idx = i
                return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_entry")
            return None

        if price >= self._peak_price:
            self._peak_price = price
            self._peak_idx = i

        floor_stop = self._floor_stop(i) if self._c.floor_mode != "none" else math.nan
        trail_stop = self._peak_price - self._c.trail_mult * ratr_val
        floor_hit = bool(np.isfinite(floor_stop) and price < floor_stop)
        trail_hit = bool(price < trail_stop)

        if floor_hit:
            event = self._build_event(
                state=state,
                i=i,
                price=price,
                atr_val=atr_val,
                ratr_val=ratr_val,
                ema_f=ema_f,
                ema_s=ema_s,
                vdo_val=vdo_val,
                floor_stop=floor_stop,
                trail_stop=trail_stop,
                trend_down=trend_down,
                trail_hit=trail_hit,
            )
            self._events.append(event)
            self._in_position = False
            self._peak_price = 0.0
            self._peak_idx = None
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_floor_exit")

        if trail_hit:
            self._in_position = False
            self._peak_price = 0.0
            self._peak_idx = None
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trail_stop")

        if trend_down:
            self._in_position = False
            self._peak_price = 0.0
            self._peak_idx = None
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        if fill.side == Side.BUY:
            self._entry_ts_ms = int(fill.ts_ms)
            self._entry_idx = self._open_index.get(int(fill.ts_ms))
            self._entry_price = float(fill.price)
            if self._entry_idx is not None and self._atr is not None:
                sig_idx = max(0, self._entry_idx - 1)
                self._entry_atr = float(self._atr[sig_idx]) if np.isfinite(self._atr[sig_idx]) else math.nan
            else:
                self._entry_atr = math.nan
            self._peak_price = float(fill.price)
            self._peak_idx = self._entry_idx
        elif fill.side == Side.SELL:
            self._entry_ts_ms = None
            self._entry_idx = None
            self._entry_price = 0.0
            self._entry_atr = math.nan
            self._peak_idx = None

    def _build_event(
        self,
        state: MarketState,
        i: int,
        price: float,
        atr_val: float,
        ratr_val: float,
        ema_f: float,
        ema_s: float,
        vdo_val: float,
        floor_stop: float,
        trail_stop: float,
        trend_down: bool,
        trail_hit: bool,
    ) -> dict:
        entry_idx = self._entry_idx if self._entry_idx is not None else i
        peak_idx = self._peak_idx if self._peak_idx is not None else i
        entry_atr = self._entry_atr if np.isfinite(self._entry_atr) and self._entry_atr > 1e-12 else max(atr_val, 1e-12)
        peak_price = float(self._peak_price)
        floor_driver = "ll"
        if self._c.floor_mode == "floor":
            ema_floor = ema_s - float(self._c.floor_atr_mult) * ratr_val
            floor_driver = "ll" if floor_stop == self._ll_exit[i] else "ema_floor"
        else:
            ema_floor = math.nan

        event = {
            "event_id": self._event_id,
            "strategy_id": self._c.strategy_id.upper(),
            "event_ts": _ts(state.bar.close_time),
            "event_close_time_ms": int(state.bar.close_time),
            "event_bar_index": int(i),
            "entry_ts": _ts(self._entry_ts_ms) if self._entry_ts_ms is not None else "",
            "entry_ts_ms": int(self._entry_ts_ms) if self._entry_ts_ms is not None else -1,
            "entry_bar_index": int(entry_idx),
            "bars_since_entry": int(i - entry_idx),
            "bars_since_peak": int(i - peak_idx),
            "entry_price": float(self._entry_price),
            "current_close": float(price),
            "peak_close": float(peak_price),
            "entry_atr": float(entry_atr),
            "current_atr": float(atr_val),
            "current_ratr": float(ratr_val),
            "mfe_r_to_date": float((peak_price - self._entry_price) / entry_atr) if self._entry_price > 0 else math.nan,
            "giveback_from_peak_r": float((peak_price - price) / entry_atr) if self._entry_price > 0 else math.nan,
            "realized_if_close_r": float((price - self._entry_price) / entry_atr) if self._entry_price > 0 else math.nan,
            "er30_now": float(self._er30[i]) if self._er30 is not None else math.nan,
            "event_context": _context_from_er(float(self._er30[i])) if self._er30 is not None else "unknown",
            "vdo_now": float(vdo_val),
            "ema_fast": float(ema_f),
            "ema_slow": float(ema_s),
            "ema_spread_atr": float((ema_f - ema_s) / max(atr_val, 1e-12)),
            "price_to_slow_atr": float((price - ema_s) / max(atr_val, 1e-12)),
            "floor_stop": float(floor_stop),
            "trail_stop": float(trail_stop),
            "ll30": float(self._ll_exit[i]) if self._ll_exit is not None else math.nan,
            "ema_floor": float(ema_floor),
            "floor_driver": floor_driver,
            "price_minus_floor_atr": float((price - floor_stop) / max(atr_val, 1e-12)),
            "price_minus_trail_atr": float((price - trail_stop) / max(atr_val, 1e-12)),
            "floor_hit": True,
            "trail_hit_same_bar": bool(trail_hit),
            "trend_down_same_bar": bool(trend_down),
            "actionable_event": bool((not trail_hit) and (not trend_down)),
            "d1_regime_on": bool(self._d1_regime_ok[i]) if self._d1_regime_ok is not None else False,
        }
        self._event_id += 1
        return event

    def get_floor_events(self) -> list[dict]:
        return list(self._events)


def _make_reference():
    return VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())


def _make_logging_candidate():
    return LoggingFloorStrategy(
        ExitFloorConfig(
            strategy_id="x0e5_floor_latch",
            floor_mode="floor",
            floor_atr_mult=2.0,
        )
    )


def _trades_to_df(trades, strategy_id: str) -> pd.DataFrame:
    rows = []
    for t in trades:
        rows.append({
            "strategy_id": strategy_id,
            "trade_id": int(t.trade_id),
            "entry_ts": _ts(t.entry_ts_ms),
            "exit_ts": _ts(t.exit_ts_ms),
            "entry_ts_ms": int(t.entry_ts_ms),
            "exit_ts_ms": int(t.exit_ts_ms),
            "pnl_usd": float(t.pnl),
            "return_pct": float(t.return_pct),
            "days_held": float(t.days_held),
            "entry_reason": t.entry_reason,
            "exit_reason": t.exit_reason,
        })
    return pd.DataFrame(rows)


def _rule_specs() -> list[RuleSpec]:
    return [
        RuleSpec("er20", "ER30 <= 0.20", lambda r: r["er30_now"] <= 0.20),
        RuleSpec("er15", "ER30 <= 0.15", lambda r: r["er30_now"] <= 0.15),
        RuleSpec("vdo_le_0", "VDO <= 0.0", lambda r: r["vdo_now"] <= 0.0),
        RuleSpec("below_slow", "close <= ema_slow", lambda r: r["price_to_slow_atr"] <= 0.0),
        RuleSpec("spread_le_050", "EMA spread <= 0.50 ATR", lambda r: r["ema_spread_atr"] <= 0.50),
        RuleSpec("spread_le_100", "EMA spread <= 1.00 ATR", lambda r: r["ema_spread_atr"] <= 1.00),
        RuleSpec("giveback_ge_075", "giveback >= 0.75R", lambda r: r["giveback_from_peak_r"] >= 0.75),
        RuleSpec("giveback_ge_125", "giveback >= 1.25R", lambda r: r["giveback_from_peak_r"] >= 1.25),
        RuleSpec("peak_age_ge_3", "bars_since_peak >= 3", lambda r: r["bars_since_peak"] >= 3),
        RuleSpec("peak_age_ge_6", "bars_since_peak >= 6", lambda r: r["bars_since_peak"] >= 6),
        RuleSpec(
            "combo_weak1",
            "ER30 <= 0.20 and giveback >= 0.75R",
            lambda r: r["er30_now"] <= 0.20 and r["giveback_from_peak_r"] >= 0.75,
        ),
        RuleSpec(
            "combo_weak2",
            "close <= ema_slow and giveback >= 0.75R",
            lambda r: r["price_to_slow_atr"] <= 0.0 and r["giveback_from_peak_r"] >= 0.75,
        ),
        RuleSpec(
            "combo_weak3",
            "ER30 <= 0.20 and close <= ema_slow",
            lambda r: r["er30_now"] <= 0.20 and r["price_to_slow_atr"] <= 0.0,
        ),
    ]


def _score_rules(actionable: pd.DataFrame) -> list[dict]:
    good_total = int((actionable["event_label"] == "good_exit").sum())
    bad_total = int((actionable["event_label"] == "bad_exit").sum())
    baseline_net = float(actionable["delta_pnl_usd"].sum())
    rows: list[dict] = []

    for spec in _rule_specs():
        mask = actionable.apply(spec.predicate, axis=1)
        accepted = actionable[mask].copy()
        rejected = actionable[~mask].copy()
        good = int((accepted["event_label"] == "good_exit").sum())
        bad = int((accepted["event_label"] == "bad_exit").sum())
        neutral = int((accepted["event_label"] == "neutral").sum())
        net = float(accepted["delta_pnl_usd"].sum()) if not accepted.empty else 0.0
        avg = float(accepted["delta_pnl_usd"].mean()) if not accepted.empty else 0.0
        good_capture = good / good_total * 100.0 if good_total else 0.0
        bad_capture = bad / bad_total * 100.0 if bad_total else 0.0
        precision = good / (good + bad) * 100.0 if (good + bad) else 0.0
        rows.append({
            "rule_id": spec.rule_id,
            "description": spec.description,
            "accepted_events": int(len(accepted)),
            "rejected_events": int(len(rejected)),
            "accepted_good": good,
            "accepted_bad": bad,
            "accepted_neutral": neutral,
            "accepted_net_delta_usd": round(net, 2),
            "accepted_avg_delta_usd": round(avg, 2),
            "good_capture_pct": round(good_capture, 2),
            "bad_capture_pct": round(bad_capture, 2),
            "precision_good_pct": round(precision, 2),
            "baseline_net_delta_usd": round(baseline_net, 2),
        })
    rows.sort(key=lambda r: (r["accepted_net_delta_usd"], r["precision_good_pct"], -r["bad_capture_pct"]), reverse=True)
    return rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _build_report(summary: dict, rule_rows: list[dict]) -> str:
    lines = [
        "# P0.1 Exit-Event Scan Report",
        "",
        "## Scope",
        "",
        "- Reference: `X0_E5EXIT`",
        "- Candidate event source: `X0E5_FLOOR_LATCH`",
        "- Scenario: `harsh`",
        f"- Period: `{START}` to `{END}`",
        "",
        "## Event Summary",
        "",
        f"- total floor events: `{summary['total_floor_events']}`",
        f"- actionable floor events: `{summary['actionable_floor_events']}`",
        f"- actionable matched events: `{summary['actionable_matched_events']}`",
        f"- good / bad / neutral actionable matched events: `{summary['good_events']}` / `{summary['bad_events']}` / `{summary['neutral_events']}`",
        f"- actionable matched net delta: `{summary['actionable_net_delta_usd']:+.2f} USD`",
        "",
        "## Top Rules",
        "",
    ]
    for row in rule_rows[:5]:
        lines.append(
            f"- `{row['rule_id']}`: accepted={row['accepted_events']}, good={row['accepted_good']}, bad={row['accepted_bad']}, "
            f"net={row['accepted_net_delta_usd']:+.2f} USD, precision={row['precision_good_pct']:.2f}%, "
            f"good_capture={row['good_capture_pct']:.2f}%, bad_capture={row['bad_capture_pct']:.2f}%"
        )

    lines.extend(["", "## Interpretation", ""])
    if not rule_rows or rule_rows[0]["accepted_events"] < 4 or rule_rows[0]["accepted_net_delta_usd"] <= 0:
        lines.append("- No simple event rule produced a convincing positive separation. The branch should be killed without benchmarking.")
    else:
        lines.append("- There is at least one simple event rule worth benchmarking.")
        lines.append(f"- Recommended first benchmark candidate: `{rule_rows[0]['rule_id']}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    ref_engine = BacktestEngine(
        feed=feed,
        strategy=_make_reference(),
        cost=SCENARIOS["harsh"],
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    ref_result = ref_engine.run()

    cand_strategy = _make_logging_candidate()
    cand_engine = BacktestEngine(
        feed=feed,
        strategy=cand_strategy,
        cost=SCENARIOS["harsh"],
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    cand_result = cand_engine.run()

    events = pd.DataFrame(cand_strategy.get_floor_events())
    cand_trades = _trades_to_df(cand_result.trades, "X0E5_FLOOR_LATCH")
    ref_trades = _trades_to_df(ref_result.trades, "X0_E5EXIT")

    merged = events.merge(
        cand_trades.add_prefix("cand_"),
        left_on="entry_ts_ms",
        right_on="cand_entry_ts_ms",
        how="left",
    )
    merged = merged.merge(
        ref_trades.add_prefix("ref_"),
        left_on="entry_ts_ms",
        right_on="ref_entry_ts_ms",
        how="left",
    )
    merged["matched_reference"] = merged["ref_entry_ts_ms"].notna()
    merged["delta_pnl_usd"] = merged["cand_pnl_usd"] - merged["ref_pnl_usd"]
    merged["delta_return_pct"] = merged["cand_return_pct"] - merged["ref_return_pct"]
    merged["candidate_earlier"] = merged["cand_exit_ts_ms"] < merged["ref_exit_ts_ms"]
    merged["event_label"] = np.where(
        ~merged["matched_reference"],
        "unmatched",
        np.where(
            merged["delta_pnl_usd"] > 0.0,
            "good_exit",
            np.where(merged["delta_pnl_usd"] < 0.0, "bad_exit", "neutral"),
        ),
    )

    actionable = merged[(merged["actionable_event"]) & (merged["matched_reference"])].copy()
    rule_rows = _score_rules(actionable) if not actionable.empty else []

    summary = {
        "total_floor_events": int(len(merged)),
        "actionable_floor_events": int(merged["actionable_event"].sum()),
        "actionable_matched_events": int(len(actionable)),
        "good_events": int((actionable["event_label"] == "good_exit").sum()) if not actionable.empty else 0,
        "bad_events": int((actionable["event_label"] == "bad_exit").sum()) if not actionable.empty else 0,
        "neutral_events": int((actionable["event_label"] == "neutral").sum()) if not actionable.empty else 0,
        "actionable_net_delta_usd": float(actionable["delta_pnl_usd"].sum()) if not actionable.empty else 0.0,
        "runtime_seconds": round(time.time() - t0, 2),
    }

    event_rows = merged.copy()
    event_rows["matched_reference"] = event_rows["matched_reference"].astype(bool)
    event_rows["candidate_earlier"] = event_rows["candidate_earlier"].fillna(False).astype(bool)
    event_rows["d1_regime_on"] = event_rows["d1_regime_on"].astype(bool)
    event_rows["actionable_event"] = event_rows["actionable_event"].astype(bool)
    event_csv_rows = event_rows.to_dict(orient="records")
    actionable_rows = actionable.to_dict(orient="records")

    _write_csv(OUTDIR / "p0_1_event_table.csv", event_csv_rows)
    _write_csv(OUTDIR / "p0_1_actionable_event_table.csv", actionable_rows)
    _write_csv(OUTDIR / "p0_1_rule_score_table.csv", rule_rows)
    with (OUTDIR / "p0_1_results.json").open("w") as f:
        json.dump({"summary": summary, "top_rule": rule_rows[0] if rule_rows else None}, f, indent=2)
    (OUTDIR / "P0_1_EVENT_SCAN_REPORT.md").write_text(_build_report(summary, rule_rows))

    print(f"Saved event scan artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
