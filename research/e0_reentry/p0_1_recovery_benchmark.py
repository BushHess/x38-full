#!/usr/bin/env python3
"""P0.1 -- Stretch-recovery benchmark on X0E5 family."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from strategies.vtrend_x0.strategy import _atr, _ema, _vdo
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
    _robust_atr,
)
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import Bar, Fill, MarketState, SCENARIOS, Signal
from v10.strategies.base import Strategy


DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
OUTDIR = Path(__file__).resolve().parent

START = "2019-01-01"
END = "2026-02-20"
HOLDOUT_START = "2024-01-01"
WARMUP = 365
INITIAL_CASH = 10_000.0

SLOW = 120
ATR_P = 14
VDO_FAST = 12
VDO_SLOW = 28
D1_EMA = 21

RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20
TRAIL = 3.0

ER_LOOKBACK = 30
ER_CHOP = 0.25


@dataclass
class RecoveryConfig:
    strategy_id: str
    block_stretch: float = 1.8
    use_override: bool = False
    override_min_vdo: float | None = None
    override_min_pts: float | None = None
    override_max_pts: float | None = None
    use_recovery: bool = False
    recovery_wait_bars: int = 6
    recovery_min_vdo: float | None = None
    recovery_min_pts: float | None = None
    recovery_max_pts: float | None = None


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    label: str
    factory: callable


def _efficiency_ratio(close: np.ndarray, lookback: int) -> np.ndarray:
    out = np.full(len(close), np.nan, dtype=np.float64)
    for i in range(lookback, len(close)):
        net = abs(close[i] - close[i - lookback])
        total = np.sum(np.abs(np.diff(close[i - lookback:i + 1])))
        out[i] = net / total if total > 1e-12 else 0.0
    return out


def _d1_regime_map(h4_bars: list[Bar], d1_bars: list[Bar], d1_ema_period: int = D1_EMA) -> np.ndarray:
    regime_ok = np.zeros(len(h4_bars), dtype=np.bool_)
    if not d1_bars:
        return regime_ok
    d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
    d1_ema = _ema(d1_close, d1_ema_period)
    d1_close_times = [b.close_time for b in d1_bars]
    d1_regime = d1_close > d1_ema
    d1_idx = 0
    n_d1 = len(d1_bars)
    for i, bar in enumerate(h4_bars):
        h4_ct = bar.close_time
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_ct:
            regime_ok[i] = d1_regime[d1_idx]
    return regime_ok


class StretchRecoveryStrategy(Strategy):
    def __init__(self, config: RecoveryConfig) -> None:
        self._c = config
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._ratr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None
        self._er30: np.ndarray | None = None
        self._d1_regime_ok: np.ndarray | None = None
        self._in_position = False
        self._peak_price = 0.0

        self._blocked_bar = -1
        self._blocked_close = math.nan

        self._stats = {
            "blocked_entries": 0,
            "override_entries": 0,
            "recovery_entries": 0,
        }

    def name(self) -> str:
        return self._c.strategy_id

    def on_init(self, h4_bars: list[Bar], d1_bars: list[Bar]) -> None:
        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)

        self._ema_fast = _ema(close, max(5, SLOW // 4))
        self._ema_slow = _ema(close, SLOW)
        self._atr = _atr(high, low, close, ATR_P)
        self._ratr = _robust_atr(high, low, close, cap_q=RATR_CAP_Q, cap_lb=RATR_CAP_LB, period=RATR_PERIOD)
        self._vdo = _vdo(close, high, low, volume, taker, VDO_FAST, VDO_SLOW)
        self._er30 = _efficiency_ratio(close, ER_LOOKBACK)
        self._d1_regime_ok = _d1_regime_map(h4_bars, d1_bars, D1_EMA)

    def _reset_block(self) -> None:
        self._blocked_bar = -1
        self._blocked_close = math.nan

    def _allow_override(self, pts: float, vdo_val: float) -> bool:
        if not self._c.use_override or self._c.override_min_vdo is None:
            return False
        if vdo_val < self._c.override_min_vdo:
            return False
        if self._c.override_min_pts is not None and pts < self._c.override_min_pts:
            return False
        if self._c.override_max_pts is not None and pts >= self._c.override_max_pts:
            return False
        return True

    def _allow_recovery(self, i: int, price: float, pts: float, vdo_val: float) -> bool:
        if not self._c.use_recovery or self._blocked_bar < 0 or i <= self._blocked_bar:
            return False
        if i - self._blocked_bar > self._c.recovery_wait_bars:
            return False
        if self._c.recovery_min_vdo is not None and vdo_val < self._c.recovery_min_vdo:
            return False
        if self._c.recovery_min_pts is not None and pts < self._c.recovery_min_pts:
            return False
        if self._c.recovery_max_pts is not None and pts >= self._c.recovery_max_pts:
            return False
        if not np.isfinite(self._blocked_close) or price <= self._blocked_close:
            return False
        return True

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (
            self._ema_fast is None or self._ema_slow is None or self._atr is None
            or self._ratr is None or self._vdo is None or self._er30 is None
            or self._d1_regime_ok is None or i < 1
        ):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        er_val = self._er30[i]
        price = state.bar.close
        if any(math.isnan(x) for x in (ema_f, ema_s, atr_val, ratr_val, vdo_val)) or atr_val <= 1e-12:
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if not regime_ok or not trend_up or vdo_val <= 0.0:
                if not regime_ok or trend_down:
                    self._reset_block()
                return None

            pts = (price - ema_s) / atr_val
            chop = np.isfinite(er_val) and er_val < ER_CHOP
            stretched = chop and pts > self._c.block_stretch

            if stretched:
                if self._allow_override(pts, vdo_val):
                    self._stats["override_entries"] += 1
                    self._in_position = True
                    self._peak_price = price
                    self._reset_block()
                    return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_override_entry")

                if self._allow_recovery(i, price, pts, vdo_val):
                    self._stats["recovery_entries"] += 1
                    self._in_position = True
                    self._peak_price = price
                    self._reset_block()
                    return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_recovery_entry")

                self._blocked_bar = i
                self._blocked_close = price
                self._stats["blocked_entries"] += 1
                return None

            self._in_position = True
            self._peak_price = price
            self._reset_block()
            return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_entry")

        self._peak_price = max(self._peak_price, price)
        trail_stop = self._peak_price - TRAIL * ratr_val
        if price < trail_stop:
            self._in_position = False
            self._peak_price = 0.0
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trail_stop")
        if trend_down:
            self._in_position = False
            self._peak_price = 0.0
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trend_exit")
        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass

    def get_gate_stats(self) -> dict[str, int]:
        return dict(self._stats)


def make_specs() -> list[StrategySpec]:
    return [
        StrategySpec("X0_E5EXIT", "X0_E5EXIT", lambda: VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())),
        StrategySpec(
            "X0E5_CHOP_STRETCH18",
            "Stretch gate baseline",
            lambda: StretchRecoveryStrategy(RecoveryConfig(strategy_id="x0e5_chop_stretch18")),
        ),
        StrategySpec(
            "X0E5_OVR_BROAD",
            "Immediate override broad",
            lambda: StretchRecoveryStrategy(
                RecoveryConfig(
                    strategy_id="x0e5_ovr_broad",
                    use_override=True,
                    override_min_vdo=0.005,
                    override_max_pts=3.0,
                )
            ),
        ),
        StrategySpec(
            "X0E5_OVR_NARROW",
            "Immediate override narrow",
            lambda: StretchRecoveryStrategy(
                RecoveryConfig(
                    strategy_id="x0e5_ovr_narrow",
                    use_override=True,
                    override_min_vdo=0.005,
                    override_min_pts=2.5,
                    override_max_pts=3.0,
                )
            ),
        ),
        StrategySpec(
            "X0E5_RE6_IMPULSE",
            "Delayed impulse recovery",
            lambda: StretchRecoveryStrategy(
                RecoveryConfig(
                    strategy_id="x0e5_re6_impulse",
                    use_recovery=True,
                    recovery_wait_bars=6,
                    recovery_min_vdo=0.008,
                    recovery_min_pts=1.8,
                    recovery_max_pts=3.0,
                )
            ),
        ),
        StrategySpec(
            "X0E5_OVR_NARROW_RE6",
            "Narrow override + delayed impulse",
            lambda: StretchRecoveryStrategy(
                RecoveryConfig(
                    strategy_id="x0e5_ovr_narrow_re6",
                    use_override=True,
                    override_min_vdo=0.005,
                    override_min_pts=2.5,
                    override_max_pts=3.0,
                    use_recovery=True,
                    recovery_wait_bars=6,
                    recovery_min_vdo=0.008,
                    recovery_min_pts=1.8,
                    recovery_max_pts=3.0,
                )
            ),
        ),
    ]


def run_suite(start: str, end: str, scenarios=("smart", "base", "harsh")) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    raw: dict[str, dict] = {}
    for spec in make_specs():
        raw[spec.strategy_id] = {}
        for scenario in scenarios:
            feed = DataFeed(DATA, start=start, end=end, warmup_days=WARMUP)
            strategy = spec.factory()
            engine = BacktestEngine(
                feed=feed,
                strategy=strategy,
                cost=SCENARIOS[scenario],
                initial_cash=INITIAL_CASH,
                warmup_days=WARMUP,
                warmup_mode="no_trade",
            )
            res = engine.run()
            raw[spec.strategy_id][scenario] = {"summary": res.summary, "strategy": strategy}
            s = res.summary
            rows.append({
                "window": f"{start}->{end}",
                "strategy_id": spec.strategy_id,
                "scenario": scenario,
                "sharpe": s["sharpe"],
                "cagr_pct": s["cagr_pct"],
                "mdd_pct": s["max_drawdown_mid_pct"],
                "calmar": s["calmar"],
                "trades": s["trades"],
                "win_rate_pct": s["win_rate_pct"],
                "profit_factor": s["profit_factor"],
                "avg_exposure": s["avg_exposure"],
                "total_return_pct": s["total_return_pct"],
            })
    return rows, raw


def build_delta_rows(rows: list[dict], baseline_id: str) -> list[dict]:
    out: list[dict] = []
    by_key = {(r["window"], r["scenario"], r["strategy_id"]): r for r in rows}
    for r in rows:
        base = by_key[(r["window"], r["scenario"], baseline_id)]
        out.append({
            "window": r["window"],
            "strategy_id": r["strategy_id"],
            "baseline": baseline_id,
            "scenario": r["scenario"],
            "d_sharpe": round((r["sharpe"] or 0.0) - (base["sharpe"] or 0.0), 4),
            "d_cagr_pct": round((r["cagr_pct"] or 0.0) - (base["cagr_pct"] or 0.0), 2),
            "d_mdd_pct": round((r["mdd_pct"] or 0.0) - (base["mdd_pct"] or 0.0), 2),
            "d_calmar": round((r["calmar"] or 0.0) - (base["calmar"] or 0.0), 4),
            "d_trades": int(r["trades"] - base["trades"]),
        })
    return out


def collect_gate_stats(raw: dict[str, dict], scenario: str) -> list[dict]:
    rows: list[dict] = []
    for strategy_id, scenarios in raw.items():
        getter = getattr(scenarios[scenario]["strategy"], "get_gate_stats", None)
        if callable(getter):
            stats = getter()
            stats["strategy_id"] = strategy_id
            rows.append(stats)
    return rows


def build_report(full_rows: list[dict], holdout_rows: list[dict], full_delta: list[dict], holdout_delta: list[dict]) -> str:
    full_harsh = {r["strategy_id"]: r for r in full_rows if r["scenario"] == "harsh"}
    hold_harsh = {r["strategy_id"]: r for r in holdout_rows if r["scenario"] == "harsh"}
    full_d = {r["strategy_id"]: r for r in full_delta if r["scenario"] == "harsh"}
    hold_d = {r["strategy_id"]: r for r in holdout_delta if r["scenario"] == "harsh"}

    candidate_ids = [sid for sid in full_harsh if sid not in {"X0_E5EXIT", "X0E5_CHOP_STRETCH18"}]
    survivors = []
    for sid in candidate_ids:
        if (
            (full_d[sid]["d_calmar"] >= 0.05 or full_d[sid]["d_sharpe"] >= 0.03)
            and full_d[sid]["d_mdd_pct"] <= 0.5
            and (hold_d[sid]["d_calmar"] >= 0.0 or hold_d[sid]["d_sharpe"] >= 0.0)
            and hold_d[sid]["d_mdd_pct"] <= 1.0
        ):
            survivors.append(sid)
    verdict = "PROMOTE_TO_VALIDATION" if survivors else "KILL_RECOVERY_MECHANICS"

    lines = [
        "# P0.1 Stretch-Recovery Benchmark Report",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        "",
        "## Full Period (harsh) vs Stretch Baseline",
        "",
    ]
    for sid in ["X0_E5EXIT", "X0E5_CHOP_STRETCH18", *candidate_ids]:
        row = full_harsh[sid]
        lines.append(
            f"- `{sid}`: Sharpe={row['sharpe']:.4f}, CAGR={row['cagr_pct']:.2f}%, MDD={row['mdd_pct']:.2f}%, Calmar={row['calmar']:.4f}, Trades={row['trades']}"
        )

    lines.extend(["", "## Candidate Deltas vs Stretch Baseline (harsh)", ""])
    for sid in candidate_ids:
        fd = full_d[sid]
        hd = hold_d[sid]
        lines.append(
            f"- `{sid}`: full dSharpe={fd['d_sharpe']:+.4f}, dCAGR={fd['d_cagr_pct']:+.2f}pp, dMDD={fd['d_mdd_pct']:+.2f}pp, dCalmar={fd['d_calmar']:+.4f}; "
            f"holdout dSharpe={hd['d_sharpe']:+.4f}, dCAGR={hd['d_cagr_pct']:+.2f}pp, dMDD={hd['d_mdd_pct']:+.2f}pp, dCalmar={hd['d_calmar']:+.4f}"
        )

    lines.extend(["", "## Interpretation", ""])
    if survivors:
        lines.append(f"- Survivors: {', '.join(f'`{sid}`' for sid in survivors)}")
        lines.append("- Next step is a full validation pass against `X0E5_CHOP_STRETCH18` and `X0_E5EXIT`.")
    else:
        lines.append("- None of the recovery mechanisms improved the stretch baseline cleanly on both full-period and recent holdout.")
        lines.append("- Current evidence favors keeping the stretch gate simple, or abandoning this family refinement entirely.")

    return "\n".join(lines) + "\n"


def save_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    t0 = time.time()
    full_rows, full_raw = run_suite(START, END)
    holdout_rows, holdout_raw = run_suite(HOLDOUT_START, END, scenarios=("harsh",))

    full_delta = build_delta_rows(full_rows, "X0E5_CHOP_STRETCH18")
    holdout_delta = build_delta_rows(holdout_rows, "X0E5_CHOP_STRETCH18")
    full_gate_stats = collect_gate_stats(full_raw, "harsh")
    holdout_gate_stats = collect_gate_stats(holdout_raw, "harsh")
    report = build_report(full_rows, holdout_rows, full_delta, holdout_delta)

    payload = {
        "settings": {
            "data": DATA,
            "start": START,
            "end": END,
            "holdout_start": HOLDOUT_START,
            "warmup_days": WARMUP,
        },
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    with (OUTDIR / "p0_1_results.json").open("w") as f:
        json.dump(payload, f, indent=2)
    save_csv(
        OUTDIR / "p0_1_backtest_table.csv",
        full_rows,
        ["window", "strategy_id", "scenario", "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor", "avg_exposure", "total_return_pct"],
    )
    save_csv(
        OUTDIR / "p0_1_holdout_table.csv",
        holdout_rows,
        ["window", "strategy_id", "scenario", "sharpe", "cagr_pct", "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor", "avg_exposure", "total_return_pct"],
    )
    save_csv(
        OUTDIR / "p0_1_delta_table.csv",
        full_delta,
        ["window", "strategy_id", "baseline", "scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct", "d_calmar", "d_trades"],
    )
    save_csv(
        OUTDIR / "p0_1_holdout_delta_table.csv",
        holdout_delta,
        ["window", "strategy_id", "baseline", "scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct", "d_calmar", "d_trades"],
    )
    if full_gate_stats:
        save_csv(
            OUTDIR / "p0_1_gate_stats_full_harsh.csv",
            full_gate_stats,
            ["blocked_entries", "override_entries", "recovery_entries", "strategy_id"],
        )
    if holdout_gate_stats:
        save_csv(
            OUTDIR / "p0_1_gate_stats_holdout_harsh.csv",
            holdout_gate_stats,
            ["blocked_entries", "override_entries", "recovery_entries", "strategy_id"],
        )
    (OUTDIR / "P0_1_BENCHMARK_REPORT.md").write_text(report)
    print(f"Saved recovery benchmark artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
