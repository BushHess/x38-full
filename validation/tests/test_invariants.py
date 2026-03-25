"""Unit tests for invariants suite and decision integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from v10.core.config import load_config
from v10.core.types import Bar
from v10.core.types import MarketState
from v10.core.types import Signal
from v10.strategies.base import Strategy
from v10.strategies.buy_and_hold import BuyAndHold
from validation.config import ValidationConfig
from validation.decision import evaluate_decision
from validation.suites.base import SuiteContext
from validation.suites.invariants import InvariantsSuite

ROOT = Path(__file__).resolve().parents[2]
BASELINE_CFG = ROOT / "v10" / "configs" / "baseline_legacy.live.yaml"

_H4_MS = 14_400_000
_D1_MS = 86_400_000


def _h4_bar(idx: int, price: float = 50_000.0) -> Bar:
    open_time = idx * _H4_MS
    return Bar(
        open_time=open_time,
        open=price,
        high=price * 1.002,
        low=price * 0.998,
        close=price,
        volume=100.0,
        close_time=open_time + _H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


def _d1_bar(day_idx: int, price: float = 50_000.0) -> Bar:
    open_time = day_idx * _D1_MS
    return Bar(
        open_time=open_time,
        open=price * 0.99,
        high=price * 1.01,
        low=price * 0.98,
        close=price,
        volume=600.0,
        close_time=open_time + _D1_MS - 1,
        taker_buy_base_vol=300.0,
        interval="1d",
    )


class _FakeFeed:
    def __init__(self, h4_bars: list[Bar], d1_bars: list[Bar]):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars
        self.report_start_ms: int | None = None


@dataclass
class _BadCfg:
    max_total_exposure: float = 1.0
    max_add_per_bar: float = 0.10
    cooldown_after_emergency_dd_bars: int = 0
    escalating_cooldown: bool = False


class _BadAddStrategy(Strategy):
    """Always requests +50% exposure per bar (violates max_add_per_bar=10%)."""

    def __init__(self) -> None:
        self.cfg = _BadCfg()

    def on_bar(self, state: MarketState) -> Signal | None:
        return Signal(target_exposure=min(float(state.exposure) + 0.5, 1.0), reason="bad_add")


def _build_ctx(
    tmp_path: Path,
    *,
    candidate_factory,
    baseline_factory,
) -> SuiteContext:
    outdir = tmp_path / "out"
    results_dir = outdir / "results"
    reports_dir = outdir / "reports"
    results_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    cfg = ValidationConfig(
        strategy_name="candidate",
        baseline_name="baseline",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=outdir,
        dataset=ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv",
        suite="basic",
        scenarios=["base"],
        lookahead_check=False,
        bootstrap=0,
        invariant_check=True,
    )
    live_cfg = load_config(str(BASELINE_CFG))
    feed = _FakeFeed(
        h4_bars=[_h4_bar(i) for i in range(12)],
        d1_bars=[_d1_bar(0), _d1_bar(1)],
    )

    return SuiteContext(
        feed=feed,
        data_path=cfg.dataset,
        project_root=ROOT,
        candidate_factory=candidate_factory,
        baseline_factory=baseline_factory,
        candidate_live_config=live_cfg,
        baseline_live_config=live_cfg,
        candidate_config_obj=None,
        baseline_config_obj=None,
        validation_config=cfg,
        resolved_suites=["invariants"],
        outdir=outdir,
        results_dir=results_dir,
        reports_dir=reports_dir,
    )


def test_invariants_pass_for_simple_baseline(tmp_path: Path) -> None:
    ctx = _build_ctx(
        tmp_path,
        candidate_factory=lambda: BuyAndHold(target=1.0),
        baseline_factory=lambda: BuyAndHold(target=1.0),
    )

    result = InvariantsSuite().run(ctx)
    assert result.status == "pass"
    assert int(result.data.get("n_violations", -1)) == 0
    assert (ctx.results_dir / "invariant_violations.csv").exists()


def test_invariants_fail_and_decision_exit3_on_violation(tmp_path: Path) -> None:
    ctx = _build_ctx(
        tmp_path,
        candidate_factory=_BadAddStrategy,
        baseline_factory=lambda: BuyAndHold(target=1.0),
    )

    result = InvariantsSuite().run(ctx)
    assert result.status == "fail"
    assert int(result.data.get("n_violations", 0)) > 0
    counts = dict(result.data.get("counts_by_invariant", {}))
    assert "max_add_per_bar_exceeded" in counts

    csv_text = (ctx.results_dir / "invariant_violations.csv").read_text()
    assert "max_add_per_bar_exceeded" in csv_text

    verdict = evaluate_decision({"invariants": result})
    assert verdict.tag == "ERROR"
    assert verdict.exit_code == 3
    assert any(str(item).startswith("max_add_per_bar_exceeded") for item in verdict.errors)
