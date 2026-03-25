"""ValidationConfig and suite resolution for the unified validation CLI."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

SUITE_GROUPS: dict[str, list[str]] = {
    "basic": [
        "lookahead",
        "backtest",
        "regime",
        "wfo",
    ],
    "full": [
        "lookahead",
        "backtest",
        "regime",
        "wfo",
        "bootstrap",
        "subsampling",
        "sensitivity",
        "holdout",
        "selection_bias",
    ],
    "trade": [
        "lookahead",
        "backtest",
        "trade_level",
    ],
    "dd": [
        "lookahead",
        "backtest",
        "dd_episodes",
    ],
    "overlay": [
        "lookahead",
        "backtest",
        "overlay",
    ],
    "all": [
        "lookahead",
        "backtest",
        "data_integrity",
        "cost_sweep",
        "invariants",
        "churn_metrics",
        "regime",
        "wfo",
        "bootstrap",
        "subsampling",
        "sensitivity",
        "holdout",
        "selection_bias",
        "regression_guard",
        "trade_level",
        "dd_episodes",
        "overlay",
    ],
}

SUITE_ORDER: list[str] = [
    "lookahead",
    "data_integrity",
    "backtest",
    "cost_sweep",
    "invariants",
    "churn_metrics",
    "regime",
    "wfo",
    "bootstrap",
    "subsampling",
    "sensitivity",
    "holdout",
    "selection_bias",
    "regression_guard",
    "trade_level",
    "dd_episodes",
    "overlay",
]


@dataclass
class ValidationConfig:
    # Required
    strategy_name: str
    baseline_name: str
    config_path: Path
    baseline_config_path: Path
    outdir: Path

    # Data
    dataset: Path
    dataset_id: str | None = None
    start: str = "2019-01-01"
    end: str = "2026-02-20"
    warmup_days: int = 365
    initial_cash: float = 10_000.0

    # Scenario / suite controls
    suite: str = "full"
    scenarios: list[str] = field(default_factory=lambda: ["smart", "base", "harsh"])
    harsh_cost_bps: float = 50.0

    # Reproducibility / execution
    seed: int = 1337
    command: list[str] = field(default_factory=list)
    force: bool = False
    force_holdout: bool = False

    # Bootstrap
    bootstrap: int = 2000
    bootstrap_block_sizes: list[int] = field(default_factory=lambda: [10, 20, 40])

    # Subsampling (Politis, Romano & Wolf, 1999)
    subsampling: bool = True
    subsampling_max_blocks: int = 0  # 0 = use all overlapping blocks
    subsampling_ci_level: float = 0.95
    subsampling_p_threshold: float = 0.80
    subsampling_ci_lower_threshold: float = 0.0
    subsampling_support_ratio_threshold: float = 0.60

    # WFO
    wfo_windows: int | None = None
    wfo_mode: str = "rolling"  # rolling | fixed
    wfo_train_months: int = 24
    wfo_test_months: int = 6
    wfo_slide_months: int = 6
    low_trade_threshold: int = 5
    min_trades_for_power: int = 5

    # Holdout
    holdout_frac: float = 0.2
    holdout_start: str | None = None
    holdout_end: str | None = None

    # Sensitivity
    sensitivity_grid: bool = False
    grid_aggr: list[float] = field(default_factory=lambda: [0.85, 0.90, 0.95])
    grid_trail: list[float] = field(default_factory=lambda: [2.7, 3.0, 3.3])
    grid_cap: list[float] = field(default_factory=lambda: [0.75, 0.90, 0.95])

    # Optional analysis modes
    selection_bias: str = "deflated"  # none | pbo | deflated
    lookahead_check: bool = True
    trade_level: bool = False
    dd_episodes: bool = False
    overlay_test: bool = False

    # Quality checks — None = follow suite group, True = force add, False = force remove
    data_integrity_check: bool | None = None
    # Provenance: unproven (Report 32 H35). No documentation for 0.5%.
    data_integrity_missing_bars_fail_pct: float = 0.5
    # Provenance: unproven (Report 32 H37). Standard outlier detection multiplier.
    data_integrity_gap_multiplier: float = 1.5
    # Provenance: unproven (Report 32 H36). No documentation for 50%.
    data_integrity_warmup_fail_coverage_pct: float = 50.0
    data_integrity_issues_limit: int = 200
    cost_sweep_bps: list[float] = field(default_factory=lambda: [0.0, 10.0, 25.0, 50.0, 75.0, 100.0])
    cost_sweep_mode: str = "quick"  # quick | full
    invariant_check: bool | None = None
    regression_guard: bool = False
    golden_path: Path | None = None
    churn_metrics: bool | None = None
    churn_warning_fee_drag_pct: float = 20.0
    churn_warning_cascade_leq3_pct: float = 30.0
    churn_warning_cascade_leq6_pct: float = 50.0

    auto_trade_level: bool = False


def resolve_suites(config: ValidationConfig) -> list[str]:
    """Resolve suite group + explicit toggles into execution order.

    Design rule: SUITE_GROUPS defines membership.  Toggles whose defaults are
    True/truthy (data_integrity, cost_sweep, invariants, churn_metrics) can
    only *remove* a suite already present in the group — they never *add*
    suites beyond the group definition.  Toggles whose defaults are False
    (trade_level, dd_episodes, overlay, regression_guard) are explicit opt-ins
    and *can* add suites.
    """
    suites = set(SUITE_GROUPS.get(config.suite, SUITE_GROUPS["full"]))

    # --- Removals: toggles can remove suites already in the group ---

    if not config.lookahead_check:
        suites.discard("lookahead")

    if config.bootstrap <= 0:
        suites.discard("bootstrap")

    if not config.subsampling:
        suites.discard("subsampling")

    if not config.sensitivity_grid:
        suites.discard("sensitivity")

    if config.selection_bias == "none":
        suites.discard("selection_bias")

    # Quality suites: tri-state (None=follow group, True=force add, False=force remove).
    # None preserves whatever the suite group defined.  Only explicit True/False overrides.
    if config.data_integrity_check is True:
        suites.add("data_integrity")
    elif config.data_integrity_check is False:
        suites.discard("data_integrity")

    if not config.cost_sweep_bps:
        suites.discard("cost_sweep")

    if config.invariant_check is True:
        suites.add("invariants")
    elif config.invariant_check is False:
        suites.discard("invariants")

    if config.churn_metrics is True:
        suites.add("churn_metrics")
    elif config.churn_metrics is False:
        suites.discard("churn_metrics")

    if not config.regression_guard:
        suites.discard("regression_guard")

    # --- Explicit opt-ins (default-False): can add beyond group ---

    if config.trade_level:
        suites.add("trade_level")
        suites.add("backtest")

    if config.dd_episodes:
        suites.add("dd_episodes")
        suites.add("backtest")

    if config.overlay_test:
        suites.add("overlay")
        suites.add("backtest")

    if config.regression_guard:
        suites.add("regression_guard")

    return [name for name in SUITE_ORDER if name in suites]
