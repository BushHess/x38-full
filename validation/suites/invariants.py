"""Invariant checks for backtest safety and logic consistency."""

from __future__ import annotations

import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

from v10.core.execution import ExecutionModel
from v10.core.execution import Portfolio
from v10.core.types import MarketState
from v10.core.types import SCENARIOS
from v10.core.types import Side
from v10.core.types import Signal
from validation.output import write_csv
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import ensure_backtest
from validation.suites.common import scenario_costs

_EPS = 1e-9
_EXPO_THRESHOLD = 0.005
_MS_PER_DAY = 86_400_000
_DEFAULT_MAX_VIOLATIONS = 200


class _ViolationBuffer:
    def __init__(self, limit: int = _DEFAULT_MAX_VIOLATIONS) -> None:
        self.limit = max(1, int(limit))
        self.rows: list[dict[str, Any]] = []
        self.counts: Counter[str] = Counter()
        self.limit_reached = False

    def add(self, ts: int, invariant_name: str, details: str, strategy_id: str) -> None:
        if self.limit_reached:
            return
        if len(self.rows) >= self.limit:
            self.limit_reached = True
            return

        self.rows.append(
            {
                "ts": int(ts),
                "invariant_name": str(invariant_name),
                "details": str(details),
                "strategy_id": str(strategy_id),
            }
        )
        self.counts[str(invariant_name)] += 1
        if len(self.rows) >= self.limit:
            self.limit_reached = True


def _as_float(value: Any) -> float:
    try:
        if value is None:
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _is_finite(value: Any) -> bool:
    return math.isfinite(_as_float(value))


def _fmt(value: Any, digits: int = 6) -> str:
    num = _as_float(value)
    if not math.isfinite(num):
        return str(value)
    return f"{num:.{digits}f}"


def _clamp_target_exposure(value: Any) -> float | None:
    target = _as_float(value)
    if not math.isfinite(target):
        return None
    return max(0.0, min(1.0, target))


def _data_time_bounds_ms(ctx: SuiteContext) -> tuple[int, int]:
    h4 = ctx.feed.h4_bars
    if not h4:
        return 0, 0
    return int(h4[0].open_time), int(h4[-1].close_time)


def _report_start_ms(ctx: SuiteContext) -> int | None:
    report_start_ms = getattr(ctx.feed, "report_start_ms", None)
    if report_start_ms is not None:
        return int(report_start_ms)
    if ctx.feed.h4_bars and int(ctx.validation_config.warmup_days) > 0:
        return int(ctx.feed.h4_bars[0].open_time) + int(ctx.validation_config.warmup_days) * _MS_PER_DAY
    return None


def _config_obj_for_label(ctx: SuiteContext, label: str) -> Any:
    return ctx.candidate_config_obj if label == "candidate" else ctx.baseline_config_obj


def _live_config_for_label(ctx: SuiteContext, label: str) -> Any:
    return ctx.candidate_live_config if label == "candidate" else ctx.baseline_live_config


def _max_total_exposure(ctx: SuiteContext, label: str, strategy: object) -> float:
    live_cfg = _live_config_for_label(ctx, label)
    risk_cap = _as_float(getattr(getattr(live_cfg, "risk", None), "max_total_exposure", 1.0))
    if not math.isfinite(risk_cap) or risk_cap <= 0:
        risk_cap = 1.0

    caps = [risk_cap]
    strategy_cfg = getattr(strategy, "cfg", None)
    if strategy_cfg is not None and hasattr(strategy_cfg, "max_total_exposure"):
        strategy_cap = _as_float(getattr(strategy_cfg, "max_total_exposure"))
        if math.isfinite(strategy_cap) and strategy_cap > 0:
            caps.append(strategy_cap)

    cfg_obj = _config_obj_for_label(ctx, label)
    if cfg_obj is not None and hasattr(cfg_obj, "max_total_exposure"):
        cfg_cap = _as_float(getattr(cfg_obj, "max_total_exposure"))
        if math.isfinite(cfg_cap) and cfg_cap > 0:
            caps.append(cfg_cap)

    cap = min(caps) if caps else 1.0
    return max(0.0, min(1.0, cap))


def _max_add_per_bar(ctx: SuiteContext, label: str, strategy: object) -> float | None:
    strategy_cfg = getattr(strategy, "cfg", None)
    if strategy_cfg is not None and hasattr(strategy_cfg, "max_add_per_bar"):
        value = _as_float(getattr(strategy_cfg, "max_add_per_bar"))
        if math.isfinite(value) and value > 0:
            return float(value)

    cfg_obj = _config_obj_for_label(ctx, label)
    if cfg_obj is not None and hasattr(cfg_obj, "max_add_per_bar"):
        value = _as_float(getattr(cfg_obj, "max_add_per_bar"))
        if math.isfinite(value) and value > 0:
            return float(value)

    return None


def _overlay_cooldown_enabled(strategy: object) -> bool:
    if not hasattr(strategy, "_emergency_dd_cooldown_remaining"):
        return False
    strategy_cfg = getattr(strategy, "cfg", None)
    if strategy_cfg is None:
        return False

    if bool(getattr(strategy_cfg, "escalating_cooldown", False)):
        return True
    cooldown_bars = _as_float(getattr(strategy_cfg, "cooldown_after_emergency_dd_bars", 0))
    return math.isfinite(cooldown_bars) and cooldown_bars > 0


def _has_htf_features(strategy: object) -> bool:
    htf_fields = [
        "_d1_regime",
        "_d1_vol_ann",
        "_d1_cycle_phase",
        "_d1_rsi",
        "_d1_adx",
    ]
    return any(hasattr(strategy, field) for field in htf_fields)


def _is_entry_signal(signal: Signal, state: MarketState) -> bool:
    if signal.orders:
        for order in signal.orders:
            side = getattr(order, "side", None)
            qty = _as_float(getattr(order, "qty", None))
            if side == Side.BUY and math.isfinite(qty) and qty > _EPS:
                return True

    if signal.target_exposure is None:
        return False
    target = _clamp_target_exposure(signal.target_exposure)
    current = _as_float(state.exposure)
    if target is None or not math.isfinite(current):
        return False
    return target > current + _EXPO_THRESHOLD


def _check_exposure(
    buffer: _ViolationBuffer,
    *,
    ts: int,
    strategy_id: str,
    scenario: str,
    exposure: float,
    max_exposure: float,
    phase: str,
) -> None:
    if not math.isfinite(exposure):
        buffer.add(
            ts=ts,
            invariant_name="exposure_finite",
            details=f"scenario={scenario}; phase={phase}; exposure={exposure}",
            strategy_id=strategy_id,
        )
        return

    if exposure < -_EPS:
        buffer.add(
            ts=ts,
            invariant_name="exposure_non_negative",
            details=f"scenario={scenario}; phase={phase}; exposure={_fmt(exposure)}",
            strategy_id=strategy_id,
        )
    if exposure > max_exposure + _EPS:
        buffer.add(
            ts=ts,
            invariant_name="exposure_within_max_total",
            details=(
                f"scenario={scenario}; phase={phase}; exposure={_fmt(exposure)}; "
                f"max_total_exposure={_fmt(max_exposure)}"
            ),
            strategy_id=strategy_id,
        )


def _check_nav(
    buffer: _ViolationBuffer,
    *,
    ts: int,
    strategy_id: str,
    scenario: str,
    nav_mid: float,
    nav_liq: float,
    phase: str,
) -> None:
    if not math.isfinite(nav_mid):
        buffer.add(
            ts=ts,
            invariant_name="nav_mid_finite",
            details=f"scenario={scenario}; phase={phase}; nav_mid={nav_mid}",
            strategy_id=strategy_id,
        )
    elif nav_mid < -_EPS:
        buffer.add(
            ts=ts,
            invariant_name="nav_mid_non_negative",
            details=f"scenario={scenario}; phase={phase}; nav_mid={_fmt(nav_mid)}",
            strategy_id=strategy_id,
        )

    if not math.isfinite(nav_liq):
        buffer.add(
            ts=ts,
            invariant_name="nav_liq_finite",
            details=f"scenario={scenario}; phase={phase}; nav_liq={nav_liq}",
            strategy_id=strategy_id,
        )
    elif nav_liq < -_EPS:
        buffer.add(
            ts=ts,
            invariant_name="nav_liq_non_negative",
            details=f"scenario={scenario}; phase={phase}; nav_liq={_fmt(nav_liq)}",
            strategy_id=strategy_id,
        )


def _check_signal_constraints(
    buffer: _ViolationBuffer,
    *,
    ts: int,
    strategy_id: str,
    scenario: str,
    strategy: object,
    signal: Signal,
    state: MarketState,
    max_add_per_bar: float | None,
    cooldown_enabled: bool,
) -> None:
    if signal.target_exposure is not None:
        target = _clamp_target_exposure(signal.target_exposure)
        if target is None:
            buffer.add(
                ts=ts,
                invariant_name="target_exposure_finite",
                details=f"scenario={scenario}; target_exposure={signal.target_exposure}",
                strategy_id=strategy_id,
            )
        elif max_add_per_bar is not None and _is_finite(state.exposure):
            delta = target - float(state.exposure)
            if delta > max_add_per_bar + _EPS:
                buffer.add(
                    ts=ts,
                    invariant_name="max_add_per_bar_exceeded",
                    details=(
                        f"scenario={scenario}; target={_fmt(target)}; current={_fmt(state.exposure)}; "
                        f"delta={_fmt(delta)}; max_add_per_bar={_fmt(max_add_per_bar)}"
                    ),
                    strategy_id=strategy_id,
                )

    if signal.orders:
        for idx, order in enumerate(signal.orders):
            qty = _as_float(getattr(order, "qty", None))
            if not math.isfinite(qty):
                buffer.add(
                    ts=ts,
                    invariant_name="order_qty_finite",
                    details=f"scenario={scenario}; order_index={idx}; qty={getattr(order, 'qty', None)}",
                    strategy_id=strategy_id,
                )

    if cooldown_enabled:
        cooldown_remaining = _as_float(getattr(strategy, "_emergency_dd_cooldown_remaining", None))
        if math.isfinite(cooldown_remaining) and cooldown_remaining > 0 and _is_entry_signal(signal, state):
            buffer.add(
                ts=ts,
                invariant_name="entry_during_cooldown",
                details=(
                    f"scenario={scenario}; cooldown_remaining={int(cooldown_remaining)}; "
                    f"state_exposure={_fmt(state.exposure)}; signal_reason={signal.reason}"
                ),
                strategy_id=strategy_id,
            )


def _execute_orders(pf: Portfolio, signal: Signal, mid: float, ts_ms: int) -> None:
    fallback_reason = signal.reason
    for order in signal.orders or []:
        reason = getattr(order, "reason", "") or fallback_reason
        side = getattr(order, "side", None)
        qty = _as_float(getattr(order, "qty", 0.0))
        if not math.isfinite(qty):
            continue
        if side == Side.BUY:
            pf.buy(qty, mid, ts_ms, reason)
        elif side == Side.SELL:
            pf.sell(qty, mid, ts_ms, reason)


def _apply_target_exposure(pf: Portfolio, signal: Signal, mid: float, ts_ms: int) -> None:
    target = _clamp_target_exposure(signal.target_exposure)
    if target is None:
        return

    current = pf.exposure(mid)
    delta = target - current

    if target < _EXPO_THRESHOLD and pf.btc_qty > 1e-8:
        pf.sell(pf.btc_qty, mid, ts_ms, signal.reason)
    elif delta > _EXPO_THRESHOLD:
        nav = pf.nav(mid)
        qty = (delta * nav / mid) if mid > _EPS else 0.0
        pf.buy(qty, mid, ts_ms, signal.reason)
    elif delta < -_EXPO_THRESHOLD:
        nav = pf.nav(mid)
        qty = min(abs(delta) * nav / mid, pf.btc_qty) if mid > _EPS else pf.btc_qty
        pf.sell(qty, mid, ts_ms, signal.reason)


def _apply_signal(pf: Portfolio, signal: Signal, mid: float, ts_ms: int) -> None:
    if signal.orders:
        _execute_orders(pf, signal, mid, ts_ms)
        return
    if signal.target_exposure is not None:
        _apply_target_exposure(pf, signal, mid, ts_ms)


def _check_result_level_invariants(
    result: object,
    *,
    strategy_id: str,
    scenario: str,
    max_exposure: float,
    min_ts: int,
    max_ts: int,
    buffer: _ViolationBuffer,
) -> None:
    for snap in list(getattr(result, "equity", []) or []):
        if buffer.limit_reached:
            return
        ts = int(getattr(snap, "close_time", 0))
        nav_mid = _as_float(getattr(snap, "nav_mid", None))
        nav_liq = _as_float(getattr(snap, "nav_liq", None))
        exposure = _as_float(getattr(snap, "exposure", None))

        _check_nav(
            buffer,
            ts=ts,
            strategy_id=strategy_id,
            scenario=scenario,
            nav_mid=nav_mid,
            nav_liq=nav_liq,
            phase="close",
        )
        _check_exposure(
            buffer,
            ts=ts,
            strategy_id=strategy_id,
            scenario=scenario,
            exposure=exposure,
            max_exposure=max_exposure,
            phase="close",
        )

    for idx, fill in enumerate(list(getattr(result, "fills", []) or [])):
        if buffer.limit_reached:
            return
        ts = int(getattr(fill, "ts_ms", 0))
        qty = _as_float(getattr(fill, "qty", None))
        notional = _as_float(getattr(fill, "notional", None))

        if not math.isfinite(qty):
            buffer.add(
                ts=ts,
                invariant_name="fill_qty_finite",
                details=f"scenario={scenario}; fill_index={idx}; qty={getattr(fill, 'qty', None)}",
                strategy_id=strategy_id,
            )
        if not math.isfinite(notional):
            buffer.add(
                ts=ts,
                invariant_name="fill_notional_finite",
                details=f"scenario={scenario}; fill_index={idx}; notional={getattr(fill, 'notional', None)}",
                strategy_id=strategy_id,
            )

    trades = list(getattr(result, "trades", []) or [])
    trades_sorted = sorted(
        trades,
        key=lambda tr: (int(getattr(tr, "entry_ts_ms", 0)), int(getattr(tr, "exit_ts_ms", 0))),
    )

    prev_exit: int | None = None
    for idx, trade in enumerate(trades_sorted):
        if buffer.limit_reached:
            return
        entry_ts = int(getattr(trade, "entry_ts_ms", 0))
        exit_ts = int(getattr(trade, "exit_ts_ms", 0))
        qty = _as_float(getattr(trade, "qty", None))

        if entry_ts > exit_ts:
            buffer.add(
                ts=entry_ts,
                invariant_name="trade_entry_before_exit",
                details=f"scenario={scenario}; entry_ts={entry_ts}; exit_ts={exit_ts}",
                strategy_id=strategy_id,
            )

        in_range = (
            min_ts <= entry_ts <= max_ts
            and min_ts <= exit_ts <= max_ts
        )
        if not in_range:
            buffer.add(
                ts=entry_ts,
                invariant_name="trade_timestamps_in_range",
                details=(
                    f"scenario={scenario}; trade_index={idx}; entry_ts={entry_ts}; "
                    f"exit_ts={exit_ts}; range=[{min_ts},{max_ts}]"
                ),
                strategy_id=strategy_id,
            )

        if not math.isfinite(qty):
            buffer.add(
                ts=entry_ts,
                invariant_name="trade_qty_finite",
                details=f"scenario={scenario}; trade_index={idx}; qty={getattr(trade, 'qty', None)}",
                strategy_id=strategy_id,
            )

        if prev_exit is not None and entry_ts < prev_exit:
            buffer.add(
                ts=entry_ts,
                invariant_name="no_overlapping_positions",
                details=(
                    f"scenario={scenario}; trade_index={idx}; prev_exit={prev_exit}; "
                    f"entry_ts={entry_ts}"
                ),
                strategy_id=strategy_id,
            )
        prev_exit = exit_ts if prev_exit is None else max(prev_exit, exit_ts)


def _check_event_loop_invariants(
    ctx: SuiteContext,
    *,
    strategy_id: str,
    scenario: str,
    strategy: object,
    cost: object,
    max_exposure: float,
    max_add_per_bar: float | None,
    cooldown_enabled: bool,
    htf_check: bool,
    buffer: _ViolationBuffer,
) -> None:
    h4 = ctx.feed.h4_bars
    d1 = ctx.feed.d1_bars
    if not h4:
        return

    strategy.on_init(h4, d1)
    report_start_ms = _report_start_ms(ctx)
    no_trade_warmup = True  # BacktestEngine default used by validation suites.

    pf = Portfolio(
        initial_cash=ctx.validation_config.initial_cash,
        exec_model=ExecutionModel(cost),
        entry_nav_pre_cost=True,
    )

    pending: Signal | None = None
    d1_idx = -1

    for i, bar in enumerate(h4):
        if buffer.limit_reached:
            return

        while d1_idx + 1 < len(d1) and d1[d1_idx + 1].close_time < bar.close_time:
            d1_idx += 1

        if htf_check and d1_idx >= 0:
            d1_ct = int(d1[d1_idx].close_time)
            if d1_ct >= int(bar.close_time):
                buffer.add(
                    ts=int(bar.close_time),
                    invariant_name="htf_last_completed_only",
                    details=(
                        f"scenario={scenario}; bar_index={i}; "
                        f"d1_close={d1_ct}; h4_close={int(bar.close_time)}"
                    ),
                    strategy_id=strategy_id,
                )

        is_warmup = report_start_ms is not None and int(bar.close_time) < int(report_start_ms)

        if pending is not None:
            _apply_signal(pf, pending, float(bar.open), int(bar.open_time))
            pending = None

            open_exposure = _as_float(pf.exposure(float(bar.open)))
            open_nav_mid = _as_float(pf.nav(float(bar.open)))
            open_nav_liq = _as_float(pf.nav_liq(float(bar.open)))

            _check_exposure(
                buffer,
                ts=int(bar.open_time),
                strategy_id=strategy_id,
                scenario=scenario,
                exposure=open_exposure,
                max_exposure=max_exposure,
                phase="open_after_fill",
            )
            _check_nav(
                buffer,
                ts=int(bar.open_time),
                strategy_id=strategy_id,
                scenario=scenario,
                nav_mid=open_nav_mid,
                nav_liq=open_nav_liq,
                phase="open_after_fill",
            )

        state = MarketState(
            bar=bar,
            h4_bars=h4,
            d1_bars=d1,
            bar_index=i,
            d1_index=d1_idx,
            cash=pf.cash,
            btc_qty=pf.btc_qty,
            nav=pf.nav(float(bar.close)),
            exposure=pf.exposure(float(bar.close)),
            entry_price_avg=pf.entry_price_avg,
            position_entry_nav=pf.position_entry_nav,
        )

        signal = strategy.on_bar(state)
        if signal is not None:
            _check_signal_constraints(
                buffer,
                ts=int(bar.close_time),
                strategy_id=strategy_id,
                scenario=scenario,
                strategy=strategy,
                signal=signal,
                state=state,
                max_add_per_bar=max_add_per_bar,
                cooldown_enabled=cooldown_enabled,
            )
            if no_trade_warmup and is_warmup:
                continue
            pending = signal


class InvariantsSuite(BaseSuite):
    def name(self) -> str:
        return "invariants"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if ctx.validation_config.invariant_check is False:
            return "invariant check disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        min_ts, max_ts = _data_time_bounds_ms(ctx)
        violations = _ViolationBuffer(limit=_DEFAULT_MAX_VIOLATIONS)

        costs = scenario_costs(ctx)
        scenarios_to_check = list(cfg.scenarios)

        for scenario in scenarios_to_check:
            cost = costs.get(scenario)
            if cost is None:
                continue

            for strategy_id, factory in [
                ("candidate", ctx.candidate_factory),
                ("baseline", ctx.baseline_factory),
            ]:
                strategy = factory()
                max_exposure = _max_total_exposure(ctx, strategy_id, strategy)
                max_add_per_bar = _max_add_per_bar(ctx, strategy_id, strategy)
                cooldown_enabled = _overlay_cooldown_enabled(strategy)
                htf_check = bool(ctx.feed.d1_bars) and _has_htf_features(strategy)

                result = ensure_backtest(ctx, strategy_id, scenario)
                _check_result_level_invariants(
                    result,
                    strategy_id=strategy_id,
                    scenario=scenario,
                    max_exposure=max_exposure,
                    min_ts=min_ts,
                    max_ts=max_ts,
                    buffer=violations,
                )
                if violations.limit_reached:
                    break

                _check_event_loop_invariants(
                    ctx,
                    strategy_id=strategy_id,
                    scenario=scenario,
                    strategy=strategy,
                    cost=cost,
                    max_exposure=max_exposure,
                    max_add_per_bar=max_add_per_bar,
                    cooldown_enabled=cooldown_enabled,
                    htf_check=htf_check,
                    buffer=violations,
                )
                if violations.limit_reached:
                    break

            if violations.limit_reached:
                break

        csv_path = write_csv(
            violations.rows,
            ctx.results_dir / "invariant_violations.csv",
            fieldnames=["ts", "invariant_name", "details", "strategy_id"],
        )
        artifacts.append(csv_path)

        status = "pass" if not violations.rows else "fail"
        counts_by_invariant = dict(sorted(violations.counts.items()))
        return SuiteResult(
            name=self.name(),
            status=status,
            data={
                "scenarios_checked": scenarios_to_check,
                "n_violations": len(violations.rows),
                "violation_limit": violations.limit,
                "limit_reached": violations.limit_reached,
                "counts_by_invariant": counts_by_invariant,
            },
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
