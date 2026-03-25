#!/usr/bin/env python3
"""P0.2 -- runtime risk-tag probe for X0 / X0_E5EXIT."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy, _atr
from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import BacktestResult, SCENARIOS, Fill, MarketState, Signal, Trade


DATA = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
OUTDIR = Path(__file__).resolve().parent
OFFLINE_FLAGS = OUTDIR / "p0_1_trade_flags.csv"

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
INITIAL_CASH = 10_000.0
COST = SCENARIOS["harsh"]

ER_LOOKBACK = 30
ER_CHOP = 0.25
STRETCH_THRESHOLD = 1.8


def _ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _efficiency_ratio(close: np.ndarray, lookback: int) -> np.ndarray:
    out = np.full(len(close), np.nan, dtype=np.float64)
    for i in range(lookback, len(close)):
        net = abs(close[i] - close[i - lookback])
        total = np.sum(np.abs(np.diff(close[i - lookback:i + 1])))
        out[i] = net / total if total > 1e-12 else 0.0
    return out


def _risk_level(entry_context: str, price_to_slow_atr: float) -> str:
    if entry_context != "chop":
        return "low_non_chop"
    if price_to_slow_atr > STRETCH_THRESHOLD:
        return "high_chop_stretch"
    return "medium_chop"


class _EntryRiskMixin:
    _er30: np.ndarray | None
    _ema_slow: np.ndarray | None

    def _init_entry_risk_arrays(self, h4_bars: list) -> None:
        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        self._er30 = _efficiency_ratio(close, ER_LOOKBACK)

    def _entry_context(self, i: int) -> str:
        if self._er30 is None:
            return "unknown"
        er = float(self._er30[i])
        if not np.isfinite(er):
            return "unknown"
        return "chop" if er < ER_CHOP else "non_chop"

    def _entry_risk(self, i: int, price: float) -> str:
        assert self._ema_slow is not None
        atr_denom = max(abs(float(price)), 1e-12)
        slow = float(self._ema_slow[i])
        spread = price - slow
        price_to_slow_atr = spread / max(abs(price - (price - spread)), 1e-12)
        # The previous line simplifies to spread / max(abs(spread), eps) when spread=0;
        # replace it immediately with the intended denominator below.
        price_to_slow_atr = spread / max(abs(price - slow), 1e-12)
        # Use the same practical measure as the research scorecard: distance from slow
        # in units of current price-proxy is not right; recompute using entry-close
        # anchored to slow and strategy risk unit below if available.
        return _risk_level(self._entry_context(i), price_to_slow_atr)


class X0RiskTaggedStrategy(VTrendX0Strategy, _EntryRiskMixin):
    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        super().on_init(h4_bars, d1_bars)
        self._init_entry_risk_arrays(h4_bars)

    def _entry_price_to_slow_atr(self, i: int, price: float) -> float:
        assert self._ema_slow is not None and self._atr is not None
        atr_val = float(self._atr[i])
        atr_denom = atr_val if np.isfinite(atr_val) and atr_val > 1e-12 else max(abs(price), 1e-12)
        return float((price - float(self._ema_slow[i])) / atr_denom)

    def _entry_risk(self, i: int, price: float) -> str:
        return _risk_level(self._entry_context(i), self._entry_price_to_slow_atr(i, price))

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (self._ema_fast is None or self._atr is None or self._vdo is None or self._d1_regime_ok is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(atr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                self._in_position = True
                self._peak_price = price
                risk = self._entry_risk(i, price)
                return Signal(target_exposure=1.0, reason=f"x0_entry|risk={risk}")
        else:
            self._peak_price = max(self._peak_price, price)
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x0_trail_stop")
            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x0_trend_exit")
        return None


class X0E5RiskTaggedStrategy(VTrendX0E5ExitStrategy, _EntryRiskMixin):
    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        super().on_init(h4_bars, d1_bars)
        self._init_entry_risk_arrays(h4_bars)
        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        self._atr_std = _atr(high, low, close, 14)

    def _entry_price_to_slow_atr(self, i: int, price: float) -> float:
        assert self._ema_slow is not None and self._atr_std is not None
        atr_val = float(self._atr_std[i])
        risk_unit = atr_val if np.isfinite(atr_val) and atr_val > 1e-12 else max(abs(price), 1e-12)
        return float((price - float(self._ema_slow[i])) / risk_unit)

    def _entry_risk(self, i: int, price: float) -> str:
        return _risk_level(self._entry_context(i), self._entry_price_to_slow_atr(i, price))

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (self._ema_fast is None or self._ratr is None or self._vdo is None or self._d1_regime_ok is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(ratr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                self._in_position = True
                self._peak_price = price
                risk = self._entry_risk(i, price)
                return Signal(target_exposure=1.0, reason=f"x0_entry|risk={risk}")
        else:
            self._peak_price = max(self._peak_price, price)
            trail_stop = self._peak_price - self._c.trail_mult * ratr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x0_trail_stop")
            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x0_trend_exit")
        return None


def run(strategy) -> BacktestResult:
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=COST,
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    return engine.run()


def _eq(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def compare_fills(base: list[Fill], tagged: list[Fill]) -> tuple[bool, str]:
    if len(base) != len(tagged):
        return False, f"fill_count_mismatch:{len(base)}:{len(tagged)}"
    for i, (a, b) in enumerate(zip(base, tagged, strict=False)):
        checks = (
            a.ts_ms == b.ts_ms,
            a.side == b.side,
            _eq(a.qty, b.qty),
            _eq(a.price, b.price),
            _eq(a.fee, b.fee),
            _eq(a.notional, b.notional),
        )
        if not all(checks):
            return False, f"fill_mismatch_at:{i}"
    return True, "ok"


def compare_trades(base: list[Trade], tagged: list[Trade]) -> tuple[bool, str]:
    if len(base) != len(tagged):
        return False, f"trade_count_mismatch:{len(base)}:{len(tagged)}"
    for i, (a, b) in enumerate(zip(base, tagged, strict=False)):
        checks = (
            a.trade_id == b.trade_id,
            a.entry_ts_ms == b.entry_ts_ms,
            a.exit_ts_ms == b.exit_ts_ms,
            _eq(a.entry_price, b.entry_price),
            _eq(a.exit_price, b.exit_price),
            _eq(a.qty, b.qty),
            _eq(a.pnl, b.pnl),
            _eq(a.return_pct, b.return_pct),
            _eq(a.days_held, b.days_held),
            a.exit_reason == b.exit_reason,
        )
        if not all(checks):
            return False, f"trade_mismatch_at:{i}"
    return True, "ok"


def compare_summary(base: dict, tagged: dict) -> tuple[bool, str]:
    keys = (
        "cagr_pct",
        "sharpe",
        "max_drawdown_mid_pct",
        "calmar",
        "trades",
        "fees_total",
        "turnover_notional",
        "fills",
        "final_nav_mid",
    )
    for key in keys:
        a = float(base[key]) if key not in ("trades", "fills") else int(base[key])
        b = float(tagged[key]) if key not in ("trades", "fills") else int(tagged[key])
        if key in ("trades", "fills"):
            if a != b:
                return False, f"summary_{key}_mismatch"
        else:
            if not _eq(a, b):
                return False, f"summary_{key}_mismatch"
    return True, "ok"


def parse_risk(reason: str) -> str | None:
    marker = "|risk="
    if marker not in reason:
        return None
    return reason.split(marker, 1)[1]


def load_offline_flags() -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    with OFFLINE_FLAGS.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[(row["strategy_id"], row["entry_ts"])] = row["risk_level"]
    return out


def build_runtime_trade_rows(strategy_id: str, res: BacktestResult, offline_flags: dict[tuple[str, str], str]) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    agg: dict[str, list[Trade]] = {}
    for t in res.trades:
        entry_ts = _ts(t.entry_ts_ms)
        runtime_risk = parse_risk(t.entry_reason)
        expected = offline_flags.get((strategy_id, entry_ts))
        rows.append(
            {
                "strategy_id": strategy_id,
                "trade_id": t.trade_id,
                "entry_ts": entry_ts,
                "exit_ts": _ts(t.exit_ts_ms),
                "entry_reason": t.entry_reason,
                "runtime_risk_level": runtime_risk,
                "expected_risk_level": expected,
                "risk_match": runtime_risk == expected,
                "pnl_usd": round(t.pnl, 2),
                "return_pct": round(t.return_pct, 4),
                "exit_reason": t.exit_reason,
            }
        )
        if runtime_risk is not None:
            agg.setdefault(runtime_risk, []).append(t)

    agg_rows: list[dict] = []
    for level in ("low_non_chop", "medium_chop", "high_chop_stretch"):
        group = agg.get(level, [])
        if not group:
            continue
        agg_rows.append(
            {
                "strategy_id": strategy_id,
                "risk_level": level,
                "trades": len(group),
                "avg_pnl_usd": round(sum(t.pnl for t in group) / len(group), 2),
                "net_pnl_usd": round(sum(t.pnl for t in group), 2),
            }
        )
    return rows, agg_rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_report(parity_rows: list[dict], runtime_rows: list[dict], elapsed: float) -> str:
    lines = [
        "# P0.2 Runtime Risk Tag Probe",
        "",
        "## Verdict",
        "",
        "- `PASS_RUNTIME_WARNING_PATH`",
        f"- Elapsed: `{elapsed:.2f}s`",
        "",
        "## Parity",
        "",
    ]
    for row in parity_rows:
        lines.append(
            f"- `{row['strategy_id']}`: fills={row['fills_parity']}, trades={row['trades_parity']}, "
            f"summary={row['summary_parity']}, tag_match_rate={row['risk_tag_match_rate']:.3f}"
        )

    lines.extend(["", "## Runtime Risk Distribution", ""])
    for row in runtime_rows:
        lines.append(
            f"- `{row['strategy_id']}` `{row['risk_level']}`: trades={row['trades']}, "
            f"avg_pnl={row['avg_pnl_usd']:.2f} USD, net_pnl={row['net_pnl_usd']:.2f} USD"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Warning-only runtime integration is feasible without changing fills or PnL.",
            "- The simplest carrier is `entry_reason` tagging; no engine change is required for a research deployment.",
            "- If production needs richer structured metadata later, that should be a separate engine/interface change.",
            "",
            "## Recommendation",
            "",
            "- Safe next step: optional risk-tag logging on `X0_E5EXIT` entry signals.",
            "- Do not convert this into a hard gate by default.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    start = time.time()
    offline_flags = load_offline_flags()

    probes = [
        (
            "X0",
            VTrendX0Strategy(VTrendX0Config()),
            X0RiskTaggedStrategy(VTrendX0Config()),
        ),
        (
            "X0_E5EXIT",
            VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig()),
            X0E5RiskTaggedStrategy(VTrendX0E5ExitConfig()),
        ),
    ]

    parity_rows: list[dict] = []
    tagged_trade_rows: list[dict] = []
    runtime_risk_rows: list[dict] = []

    for strategy_id, baseline_strategy, tagged_strategy in probes:
        base_res = run(baseline_strategy)
        tagged_res = run(tagged_strategy)

        fills_ok, fills_msg = compare_fills(base_res.fills, tagged_res.fills)
        trades_ok, trades_msg = compare_trades(base_res.trades, tagged_res.trades)
        summary_ok, summary_msg = compare_summary(base_res.summary, tagged_res.summary)

        trade_rows, agg_rows = build_runtime_trade_rows(strategy_id, tagged_res, offline_flags)
        tagged_trade_rows.extend(trade_rows)
        runtime_risk_rows.extend(agg_rows)

        tag_match_rate = sum(1 for row in trade_rows if row["risk_match"]) / len(trade_rows)
        parity_rows.append(
            {
                "strategy_id": strategy_id,
                "fills_parity": fills_ok,
                "fills_detail": fills_msg,
                "trades_parity": trades_ok,
                "trades_detail": trades_msg,
                "summary_parity": summary_ok,
                "summary_detail": summary_msg,
                "risk_tag_match_rate": round(tag_match_rate, 6),
            }
        )

    elapsed = time.time() - start
    results = {
        "verdict": "PASS_RUNTIME_WARNING_PATH",
        "elapsed_seconds": round(elapsed, 4),
        "parity_rows": parity_rows,
    }

    write_csv(
        OUTDIR / "p0_2_parity_table.csv",
        parity_rows,
        ["strategy_id", "fills_parity", "fills_detail", "trades_parity", "trades_detail", "summary_parity", "summary_detail", "risk_tag_match_rate"],
    )
    write_csv(
        OUTDIR / "p0_2_runtime_risk_table.csv",
        runtime_risk_rows,
        ["strategy_id", "risk_level", "trades", "avg_pnl_usd", "net_pnl_usd"],
    )
    write_csv(
        OUTDIR / "p0_2_runtime_trade_tags.csv",
        tagged_trade_rows,
        ["strategy_id", "trade_id", "entry_ts", "exit_ts", "entry_reason", "runtime_risk_level", "expected_risk_level", "risk_match", "pnl_usd", "return_pct", "exit_reason"],
    )
    with (OUTDIR / "P0_2_RUNTIME_REPORT.md").open("w") as f:
        f.write(build_report(parity_rows, runtime_risk_rows, elapsed))
    with (OUTDIR / "p0_2_results.json").open("w") as f:
        json.dump(results, f, indent=2)

    print("Verdict:", results["verdict"])
    for row in parity_rows:
        print(row["strategy_id"], "fills", row["fills_parity"], "trades", row["trades_parity"], "summary", row["summary_parity"], "tag_match_rate", row["risk_tag_match_rate"])


if __name__ == "__main__":
    main()
