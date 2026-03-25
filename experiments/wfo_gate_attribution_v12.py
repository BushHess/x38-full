from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from strategies.v12_emdd_ref_fix.strategy import Regime
from strategies.v12_emdd_ref_fix.strategy import V12EMDDRefFixStrategy
from v10.core.config import load_config
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.wfo import WFOWindowSpec
from v10.research.wfo import generate_windows
from validation.strategy_factory import make_factory


@dataclass
class WindowDiagnostic:
    window_id: int
    test_start: str
    test_end: str
    trades: int
    score: float
    cagr_pct: float
    max_drawdown_mid_pct: float
    sharpe: float
    entry_checks: int
    entry_signals_emitted: int
    blocked_total: int
    blocked_ratio: float
    gate_overlay_cooldown: int
    gate_regime_off: int
    gate_entry_cooldown: int
    gate_exit_cooldown: int
    gate_vdo_threshold: int
    gate_trend_filter: int
    gate_min_target_to_add: int
    gate_size_floor: int
    gate_unknown: int


class GateAuditV12Strategy(V12EMDDRefFixStrategy):
    def __init__(self, cfg=None) -> None:
        super().__init__(cfg)
        self.audit_blocked_counts: Counter[str] = Counter()
        self.audit_entry_checks: int = 0
        self.audit_entry_signals_emitted: int = 0
        self.audit_unknown_count: int = 0

    def _first_block_reason(self, state, idx: int, mid: float, regime: Regime) -> str | None:
        c = self.cfg

        if self._emergency_dd_cooldown_remaining > 0:
            return "gate_overlay_cooldown"

        if regime == Regime.RISK_OFF:
            return "gate_regime_off"

        if idx - self._last_add_idx < c.entry_cooldown_bars:
            return "gate_entry_cooldown"

        if idx - self._last_exit_idx < c.exit_cooldown_bars:
            return "gate_exit_cooldown"

        vdo = self._h4_vdo[idx] if idx < len(self._h4_vdo) else 0.0
        if vdo <= c.vdo_entry_threshold:
            return "gate_vdo_threshold"

        hma_v = self._h4_hma[idx] if idx < len(self._h4_hma) else mid
        rsi_v = self._h4_rsi[idx] if idx < len(self._h4_rsi) else 50.0
        above_hma = not np.isnan(hma_v) and mid > hma_v
        oversold = rsi_v < c.rsi_oversold
        if not above_hma and not oversold:
            return "gate_trend_filter"

        d1i = state.d1_index
        va = self._d1_vol_ann[d1i] if 0 <= d1i < len(self._d1_vol_ann) else 1.0
        base = min(c.max_total_exposure, c.target_vol_annual / va)
        if regime == Regime.CAUTION:
            base *= c.caution_mult

        if c.enable_vol_brake and mid > 0:
            atr_f = self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
            if atr_f / mid > c.vol_brake_atr_ratio:
                base *= c.vol_brake_mult

        if c.enable_dd_adaptive and self._equity_peak > 0 and state.nav < self._equity_peak:
            dd = 1.0 - state.nav / self._equity_peak
            if dd > c.dd_adaptive_start:
                prog = min(
                    (dd - c.dd_adaptive_start) / max(c.emergency_dd_pct - c.dd_adaptive_start, 0.01),
                    1.0,
                )
                base *= 1.0 - prog * (1.0 - c.dd_adaptive_floor)

        base = min(base, c.max_total_exposure)
        gap = base - state.exposure
        if gap < c.min_target_to_add:
            return "gate_min_target_to_add"

        vc = max(0.3, min(2.0, vdo / max(c.vdo_scale, 0.001)))
        sz = gap * c.entry_aggression * vc

        accel = self._h4_accel[idx] if idx < len(self._h4_accel) else 0.0
        if accel >= 0.0:
            sz *= 1.15

        atr_f = self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
        atr_s = self._h4_atr_s[idx] if idx < len(self._h4_atr_s) else mid * 0.02
        is_comp = atr_s > 0 and (atr_f / atr_s) < c.compression_ratio
        if is_comp:
            sz *= c.compression_boost

        if rsi_v > c.rsi_overbought:
            sz *= 0.50
        elif oversold:
            sz *= 1.30
        if regime == Regime.CAUTION:
            sz *= c.caution_mult

        sz = min(sz, c.max_add_per_bar, gap)
        if sz < 0.01:
            return "gate_size_floor"

        return None

    def _check_entry(self, state, idx: int, mid: float, regime: Regime):
        self.audit_entry_checks += 1
        block = self._first_block_reason(state, idx, mid, regime)
        if block is not None:
            self.audit_blocked_counts[block] += 1

        signal = super()._check_entry(state, idx, mid, regime)

        if signal is not None:
            self.audit_entry_signals_emitted += 1
        elif block is None:
            self.audit_unknown_count += 1
            self.audit_blocked_counts["gate_unknown"] += 1

        return signal


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WFO gate-by-gate entry attribution for v12_emdd_ref_fix")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--start", type=str, default="2019-01-01")
    p.add_argument("--end", type=str, default="2026-02-20")
    p.add_argument("--warmup-days", type=int, default=365)
    p.add_argument("--initial-cash", type=float, default=10_000.0)
    p.add_argument("--wfo-train-months", type=int, default=24)
    p.add_argument("--wfo-test-months", type=int, default=6)
    p.add_argument("--wfo-slide-months", type=int, default=6)
    p.add_argument("--wfo-windows", type=int, default=8)
    p.add_argument("--scenario", choices=sorted(SCENARIOS.keys()), default="harsh")
    return p.parse_args()


def _build_windows(args: argparse.Namespace) -> list[WFOWindowSpec]:
    windows = generate_windows(
        args.start,
        args.end,
        train_months=args.wfo_train_months,
        test_months=args.wfo_test_months,
        slide_months=args.wfo_slide_months,
    )
    if args.wfo_windows > 0 and len(windows) > args.wfo_windows:
        windows = windows[-args.wfo_windows :]
    return windows


def _run_window(
    args: argparse.Namespace,
    window: WFOWindowSpec,
    display_window_id: int,
    base_factory,
) -> WindowDiagnostic:
    feed = DataFeed(
        str(args.dataset),
        start=window.test_start,
        end=window.test_end,
        warmup_days=args.warmup_days,
    )

    seed_strategy = base_factory()
    if not isinstance(seed_strategy, V12EMDDRefFixStrategy):
        raise TypeError(
            "Configured strategy is not v12_emdd_ref_fix. "
            "This diagnostic script is specific to V12 entry gates."
        )

    strategy = GateAuditV12Strategy(seed_strategy.cfg)
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=SCENARIOS[args.scenario],
        initial_cash=args.initial_cash,
        warmup_days=args.warmup_days,
    )
    result = engine.run()
    summary = result.summary

    blocked_total = int(sum(strategy.audit_blocked_counts.values()))
    entry_checks = int(strategy.audit_entry_checks)
    blocked_ratio = (blocked_total / entry_checks) if entry_checks > 0 else 0.0

    return WindowDiagnostic(
        window_id=display_window_id,
        test_start=window.test_start,
        test_end=window.test_end,
        trades=int(summary.get("trades", 0)),
        score=float(compute_objective(summary)),
        cagr_pct=float(summary.get("cagr_pct", 0.0)),
        max_drawdown_mid_pct=float(summary.get("max_drawdown_mid_pct", 0.0)),
        sharpe=float(summary.get("sharpe") or 0.0),
        entry_checks=entry_checks,
        entry_signals_emitted=int(strategy.audit_entry_signals_emitted),
        blocked_total=blocked_total,
        blocked_ratio=blocked_ratio,
        gate_overlay_cooldown=int(strategy.audit_blocked_counts.get("gate_overlay_cooldown", 0)),
        gate_regime_off=int(strategy.audit_blocked_counts.get("gate_regime_off", 0)),
        gate_entry_cooldown=int(strategy.audit_blocked_counts.get("gate_entry_cooldown", 0)),
        gate_exit_cooldown=int(strategy.audit_blocked_counts.get("gate_exit_cooldown", 0)),
        gate_vdo_threshold=int(strategy.audit_blocked_counts.get("gate_vdo_threshold", 0)),
        gate_trend_filter=int(strategy.audit_blocked_counts.get("gate_trend_filter", 0)),
        gate_min_target_to_add=int(strategy.audit_blocked_counts.get("gate_min_target_to_add", 0)),
        gate_size_floor=int(strategy.audit_blocked_counts.get("gate_size_floor", 0)),
        gate_unknown=int(strategy.audit_blocked_counts.get("gate_unknown", 0)),
    )


def _write_outputs(out_dir: Path, rows: list[WindowDiagnostic], args: argparse.Namespace) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "wfo_gate_attribution_per_window.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()) if rows else [])
        if rows:
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))

    totals = Counter()
    total_checks = 0
    total_signals = 0
    for row in rows:
        data = asdict(row)
        total_checks += int(data["entry_checks"])
        total_signals += int(data["entry_signals_emitted"])
        for k, v in data.items():
            if k.startswith("gate_"):
                totals[k] += int(v)

    summary = {
        "params": {
            "config": str(args.config),
            "dataset": str(args.dataset),
            "start": args.start,
            "end": args.end,
            "scenario": args.scenario,
            "wfo_train_months": args.wfo_train_months,
            "wfo_test_months": args.wfo_test_months,
            "wfo_slide_months": args.wfo_slide_months,
            "wfo_windows": args.wfo_windows,
            "warmup_days": args.warmup_days,
        },
        "n_windows": len(rows),
        "total_entry_checks": total_checks,
        "total_entry_signals_emitted": total_signals,
        "entry_signal_rate": (total_signals / total_checks) if total_checks > 0 else 0.0,
        "gate_totals": dict(sorted(totals.items())),
        "gate_ratios": {
            k: (v / total_checks if total_checks > 0 else 0.0)
            for k, v in sorted(totals.items())
        },
    }

    with open(out_dir / "wfo_gate_attribution_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def main() -> None:
    args = _parse_args()

    live_cfg = load_config(str(args.config))
    base_factory = make_factory(live_cfg)

    windows = _build_windows(args)
    rows: list[WindowDiagnostic] = []
    for idx, window in enumerate(windows):
        rows.append(_run_window(args, window, idx, base_factory))

    _write_outputs(args.out, rows, args)
    print(f"Wrote diagnostics to: {args.out}")


if __name__ == "__main__":
    main()
