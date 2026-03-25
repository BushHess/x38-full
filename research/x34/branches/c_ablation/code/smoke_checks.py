"""Branch-local smoke checks for X34 c_ablation strategies."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from v10.core.types import Bar, MarketState
from research.x34.branches.c_ablation.code.strategy_a3 import VTrendA3Config
from research.x34.branches.c_ablation.code.strategy_a3 import VTrendA3Strategy
from research.x34.branches.c_ablation.code.strategy_a5 import VTrendA5Config
from research.x34.branches.c_ablation.code.strategy_a5 import VTrendA5Strategy


@dataclass(frozen=True)
class SmokeCheckResult:
    name: str
    passed: bool
    detail: str


def _make_bar(
    close: float,
    *,
    open_time: int,
    close_time: int,
    volume: float = 100.0,
    taker_buy_base: float = 50.0,
    quote_volume: float = 10_000.0,
    taker_buy_quote: float = 5_000.0,
) -> Bar:
    return Bar(
        open_time=open_time,
        open=close - 0.1,
        high=close * 1.001,
        low=close * 0.999,
        close=close,
        volume=volume,
        close_time=close_time,
        taker_buy_base_vol=taker_buy_base,
        interval="4h",
        quote_volume=quote_volume,
        taker_buy_quote_vol=taker_buy_quote,
    )


def _make_state(bar: Bar, bars: list[Bar], index: int) -> MarketState:
    return MarketState(
        bar=bar,
        h4_bars=bars,
        d1_bars=[],
        bar_index=index,
        d1_index=-1,
        cash=10_000.0,
        btc_qty=0.0,
        nav=10_000.0,
        exposure=0.0,
        entry_price_avg=0.0,
        position_entry_nav=0.0,
    )


def _make_bars(
    n: int,
    *,
    step_index: int,
    base_frac: float,
    step_frac: float,
) -> list[Bar]:
    bars: list[Bar] = []
    for i in range(n):
        close = 100.0 + i * 0.5
        frac = base_frac if i < step_index else step_frac
        volume = 100.0
        quote_volume = 10_000.0
        bars.append(
            _make_bar(
                close,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
                volume=volume,
                taker_buy_base=volume * frac,
                quote_volume=quote_volume,
                taker_buy_quote=quote_volume * frac,
            )
        )
    return bars


def _first_entry_index(strategy, bars: list[Bar]) -> int | None:
    strategy.on_init(bars, [])
    for i, bar in enumerate(bars):
        signal = strategy.on_bar(_make_state(bar, bars, i))
        if signal is not None and signal.target_exposure == 1.0:
            return i
    return None


def run_smoke_checks() -> list[SmokeCheckResult]:
    results: list[SmokeCheckResult] = []

    bars = _make_bars(240, step_index=120, base_frac=0.5, step_frac=0.85)
    a5_index = _first_entry_index(
        VTrendA5Strategy(VTrendA5Config(slow_period=20, theta_k=1.0)),
        bars,
    )
    results.append(
        SmokeCheckResult(
            name="a5_step_response",
            passed=a5_index is not None and a5_index >= 120,
            detail=f"first_entry_index={a5_index}",
        )
    )

    a3_index = _first_entry_index(
        VTrendA3Strategy(VTrendA3Config(slow_period=20, qvdo_k=1.0)),
        bars,
    )
    results.append(
        SmokeCheckResult(
            name="a3_step_response",
            passed=a3_index is not None and a3_index >= 120,
            detail=f"first_entry_index={a3_index}",
        )
    )

    constant_bars = _make_bars(200, step_index=0, base_frac=0.8, step_frac=0.8)
    a5_constant_index = _first_entry_index(
        VTrendA5Strategy(VTrendA5Config(slow_period=20, theta_k=1.0)),
        constant_bars,
    )
    results.append(
        SmokeCheckResult(
            name="a5_constant_pressure_silent",
            passed=a5_constant_index is None,
            detail=f"first_entry_index={a5_constant_index}",
        )
    )

    a3_constant_index = _first_entry_index(
        VTrendA3Strategy(VTrendA3Config(slow_period=20, qvdo_k=1.0)),
        constant_bars,
    )
    results.append(
        SmokeCheckResult(
            name="a3_constant_pressure_silent",
            passed=a3_constant_index is None,
            detail=f"first_entry_index={a3_constant_index}",
        )
    )

    return results


def main() -> int:
    results = run_smoke_checks()
    failed = [result for result in results if not result.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
