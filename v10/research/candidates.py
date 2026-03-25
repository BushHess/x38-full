"""YAML candidate loader, config builder, and matrix runner.

Loads candidate specs from YAML, builds strategy-specific configs,
and runs each candidate across all cost scenarios.
"""

from __future__ import annotations

import csv
import dataclasses
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS, BacktestResult, CostConfig
from v10.core.engine import BacktestEngine
from v10.research.drawdown import detect_drawdown_episodes, recovery_table
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, compute_regime_returns
from v10.strategies.base import Strategy
from v10.strategies.buy_and_hold import BuyAndHold
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy
from strategies.v12_emdd_ref_fix.strategy import (
    V12EMDDRefFixConfig,
    V12EMDDRefFixStrategy,
)
from strategies.vtrend_sm.strategy import (
    VTrendSMConfig,
    VTrendSMStrategy,
)
from strategies.vtrend_p.strategy import (
    VTrendPConfig,
    VTrendPStrategy,
)
from strategies.latch.strategy import (
    LatchConfig,
    LatchStrategy,
)
from strategies.vtrend_x0.strategy import (
    VTrendX0Config,
    VTrendX0Strategy,
)
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
)
from strategies.vtrend_x0_volsize.strategy import (
    VTrendX0VolsizeConfig,
    VTrendX0VolsizeStrategy,
)
from strategies.vtrend_x2.strategy import (
    VTrendX2Config,
    VTrendX2Strategy,
)
from strategies.vtrend_x6.strategy import (
    VTrendX6Config,
    VTrendX6Strategy,
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class CandidateSpec:
    """A named candidate configuration for matrix/WFO testing."""
    name: str
    description: str = ""
    params: dict[str, Any] = dataclasses.field(default_factory=dict)
    param_ranges: dict[str, list] = dataclasses.field(default_factory=dict)
    strategy: str = "v8_apex"


@dataclass
class CandidateResult:
    """Result of running one candidate under one cost scenario."""
    candidate_name: str
    scenario: str
    result: BacktestResult
    score: float


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

_V8_FIELDS = {f.name for f in fields(V8ApexConfig)}
_V11_FIELDS = {f.name for f in fields(V11HybridConfig)}
_V12_FIELDS = {f.name for f in fields(V12EMDDRefFixConfig)}
_VTREND_SM_FIELDS = {f.name for f in fields(VTrendSMConfig)}
_VTREND_P_FIELDS = {f.name for f in fields(VTrendPConfig)}
_LATCH_FIELDS = {f.name for f in fields(LatchConfig)}
_VTREND_X0_FIELDS = {f.name for f in fields(VTrendX0Config)}
_VTREND_X0_E5EXIT_FIELDS = {f.name for f in fields(VTrendX0E5ExitConfig)}
_VTREND_X0_VOLSIZE_FIELDS = {f.name for f in fields(VTrendX0VolsizeConfig)}
_VTREND_X2_FIELDS = {f.name for f in fields(VTrendX2Config)}
_VTREND_X6_FIELDS = {f.name for f in fields(VTrendX6Config)}
_VALID_FIELDS = _V8_FIELDS  # backward compat alias


def load_candidates(path: str | Path) -> list[CandidateSpec]:
    """Load candidates from a YAML file.

    Validates:
      - All param names are valid fields for the selected strategy
      - param_ranges keys are valid fields for the selected strategy
      - param_ranges has ≤ 8 keys (WFO budget constraint)
    """
    with open(path) as f:
        data = yaml.safe_load(f)

    raw_list = data.get("candidates", [])
    if not raw_list:
        raise ValueError(f"No candidates found in {path}")

    specs: list[CandidateSpec] = []
    for item in raw_list:
        name = item.get("name")
        if not name:
            raise ValueError("Each candidate must have a 'name'")

        params = item.get("params", {})
        param_ranges = item.get("param_ranges", {})
        strategy = item.get("strategy", "v8_apex")

        # Select valid field set based on strategy
        if strategy == "v8_apex":
            valid_fields = _V8_FIELDS
        elif strategy == "v11_hybrid":
            valid_fields = _V11_FIELDS
        elif strategy == "v12_emdd_ref_fix":
            valid_fields = _V12_FIELDS
        elif strategy == "vtrend_sm":
            valid_fields = _VTREND_SM_FIELDS
        elif strategy == "vtrend_p":
            valid_fields = _VTREND_P_FIELDS
        elif strategy == "latch":
            valid_fields = _LATCH_FIELDS
        elif strategy == "vtrend_x0":
            valid_fields = _VTREND_X0_FIELDS
        elif strategy == "vtrend_x0_e5exit":
            valid_fields = _VTREND_X0_E5EXIT_FIELDS
        elif strategy == "vtrend_x0_volsize":
            valid_fields = _VTREND_X0_VOLSIZE_FIELDS
        elif strategy == "vtrend_x2":
            valid_fields = _VTREND_X2_FIELDS
        elif strategy == "vtrend_x6":
            valid_fields = _VTREND_X6_FIELDS
        elif strategy == "buy_and_hold":
            valid_fields = set()
        else:
            raise ValueError(
                f"Candidate '{name}': unknown strategy '{strategy}'. "
                "Allowed: v8_apex, v11_hybrid, v12_emdd_ref_fix, vtrend_sm, vtrend_p, latch, vtrend_x0, vtrend_x0_e5exit, vtrend_x0_volsize, vtrend_x2, vtrend_x6, buy_and_hold."
            )

        # Validate param names
        for key in params:
            if key not in valid_fields:
                raise ValueError(
                    f"Candidate '{name}': unknown param '{key}' for "
                    f"strategy '{strategy}'."
                )
        for key in param_ranges:
            if key not in valid_fields:
                raise ValueError(
                    f"Candidate '{name}': unknown param_range key '{key}' "
                    f"for strategy '{strategy}'."
                )

        if len(param_ranges) > 8:
            raise ValueError(
                f"Candidate '{name}': param_ranges has {len(param_ranges)} keys "
                f"(max 8 for WFO budget)"
            )

        specs.append(CandidateSpec(
            name=name,
            description=item.get("description", ""),
            params=params,
            param_ranges=param_ranges,
            strategy=strategy,
        ))

    return specs


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_config(overrides: dict[str, Any]) -> V8ApexConfig:
    """Build a V8ApexConfig with the given param overrides."""
    cfg = V8ApexConfig()
    for key, val in overrides.items():
        if not hasattr(cfg, key):
            raise ValueError(f"V8ApexConfig has no field '{key}'")
        setattr(cfg, key, val)
    return cfg


def build_strategy(spec: CandidateSpec) -> tuple[Strategy, Any]:
    """Build the correct strategy + config for a candidate spec."""
    if spec.strategy == "v11_hybrid":
        cfg = V11HybridConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"V11HybridConfig has no field '{k}'")
            setattr(cfg, k, v)
        return V11HybridStrategy(cfg), cfg
    if spec.strategy == "v8_apex":
        cfg = build_config(spec.params)
        return V8ApexStrategy(cfg), cfg
    if spec.strategy == "v12_emdd_ref_fix":
        cfg = V12EMDDRefFixConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"V12EMDDRefFixConfig has no field '{k}'")
            setattr(cfg, k, v)
        return V12EMDDRefFixStrategy(cfg), cfg
    if spec.strategy == "vtrend_sm":
        cfg = VTrendSMConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendSMConfig has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendSMStrategy(cfg), cfg
    if spec.strategy == "vtrend_p":
        cfg = VTrendPConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendPConfig has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendPStrategy(cfg), cfg
    if spec.strategy == "latch":
        cfg = LatchConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"LatchConfig has no field '{k}'")
            setattr(cfg, k, v)
        return LatchStrategy(cfg), cfg
    if spec.strategy == "vtrend_x0":
        cfg = VTrendX0Config()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendX0Config has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendX0Strategy(cfg), cfg
    if spec.strategy == "vtrend_x0_e5exit":
        cfg = VTrendX0E5ExitConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendX0E5ExitConfig has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendX0E5ExitStrategy(cfg), cfg
    if spec.strategy == "vtrend_x0_volsize":
        cfg = VTrendX0VolsizeConfig()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendX0VolsizeConfig has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendX0VolsizeStrategy(cfg), cfg
    if spec.strategy == "vtrend_x2":
        cfg = VTrendX2Config()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendX2Config has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendX2Strategy(cfg), cfg
    if spec.strategy == "vtrend_x6":
        cfg = VTrendX6Config()
        for k, v in spec.params.items():
            if not hasattr(cfg, k):
                raise ValueError(f"VTrendX6Config has no field '{k}'")
            setattr(cfg, k, v)
        return VTrendX6Strategy(cfg), cfg
    if spec.strategy == "buy_and_hold":
        return BuyAndHold(), None
    raise ValueError(
        f"Unknown strategy '{spec.strategy}'. "
        "Allowed: v8_apex, v11_hybrid, v12_emdd_ref_fix, vtrend_sm, vtrend_p, latch, vtrend_x0, vtrend_x0_e5exit, vtrend_x0_volsize, vtrend_x2, vtrend_x6, buy_and_hold."
    )


# ---------------------------------------------------------------------------
# Matrix runner
# ---------------------------------------------------------------------------

def run_candidate_matrix(
    candidates: list[CandidateSpec],
    feed: DataFeed,
    initial_cash: float = 10_000.0,
    scenarios: dict[str, CostConfig] | None = None,
    warmup_mode: str = "no_trade",
) -> list[CandidateResult]:
    """Run all candidates across all cost scenarios.

    Returns a flat list of CandidateResult (len = n_candidates * n_scenarios).
    """
    if scenarios is None:
        scenarios = SCENARIOS

    results: list[CandidateResult] = []

    for spec in candidates:
        for scenario_name, cost in scenarios.items():
            strategy, _ = build_strategy(spec)

            engine = BacktestEngine(
                feed=feed,
                strategy=strategy,
                cost=cost,
                initial_cash=initial_cash,
                warmup_mode=warmup_mode,
            )
            bt_result = engine.run()
            score = compute_objective(bt_result.summary)

            results.append(CandidateResult(
                candidate_name=spec.name,
                scenario=scenario_name,
                result=bt_result,
                score=score,
            ))

    return results


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def write_matrix_outputs(
    results: list[CandidateResult],
    d1_bars: list,
    outdir: str | Path,
) -> Path:
    """Write matrix results to disk.

    Layout:
      outdir/
        matrix_summary.json
        scenario_table.csv
        regime_returns_<candidate>.json
        dd_episodes_<candidate>.csv
        candidates/<name>/<scenario>/summary.json, equity.csv, trades.csv, fills.csv
        candidates/<name>/regime_returns.json
        candidates/<name>/dd_episodes.json
    """
    from v10.cli.backtest import _write_outputs

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    # Classify regimes once (shared across candidates)
    regimes = classify_d1_regimes(d1_bars) if d1_bars else []

    # Build matrix summary
    matrix: list[dict[str, Any]] = []
    candidates_seen: dict[str, list[CandidateResult]] = {}

    for cr in results:
        matrix.append({
            "candidate": cr.candidate_name,
            "scenario": cr.scenario,
            "score": round(cr.score, 2),
            **{k: v for k, v in cr.result.summary.items()},
        })
        candidates_seen.setdefault(cr.candidate_name, []).append(cr)

    with open(out / "matrix_summary.json", "w") as f:
        json.dump(matrix, f, indent=2, default=str)

    # Scenario table (long format: candidate x scenario rows)
    scenario_cols = [
        "candidate", "scenario", "score", "cagr_pct", "max_drawdown_mid_pct",
        "sharpe", "sortino", "profit_factor", "win_rate_pct", "avg_trade_pnl",
        "fees_total", "trades", "turnover_per_year", "fee_drag_pct_per_year",
    ]
    with open(out / "scenario_table.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=scenario_cols)
        writer.writeheader()
        for row in matrix:
            writer.writerow({k: row.get(k) for k in scenario_cols})

    # Per-candidate outputs
    for cand_name, cand_results in candidates_seen.items():
        cand_dir = out / "candidates" / cand_name

        for cr in cand_results:
            scenario_dir = cand_dir / cr.scenario
            _write_outputs(cr.result, str(scenario_dir))

        # Regime returns (using base scenario equity, or first available)
        base_cr = next((c for c in cand_results if c.scenario == "base"), cand_results[0])
        if regimes and base_cr.result.equity:
            regime_ret = compute_regime_returns(
                base_cr.result.equity, d1_bars, regimes,
            )
            with open(cand_dir / "regime_returns.json", "w") as f:
                json.dump(regime_ret, f, indent=2)
            with open(out / f"regime_returns_{cand_name}.json", "w") as f:
                json.dump(regime_ret, f, indent=2)

        # DD episodes
        if base_cr.result.equity:
            episodes = detect_drawdown_episodes(base_cr.result.equity, min_dd_pct=5.0)
            table = recovery_table(episodes)
            with open(cand_dir / "dd_episodes.json", "w") as f:
                json.dump(table, f, indent=2)
            fieldnames = [
                "peak_date",
                "peak_nav",
                "trough_date",
                "trough_nav",
                "recovery_date",
                "drawdown_pct",
                "bars_to_trough",
                "bars_to_recovery",
                "days_to_trough",
                "days_to_recovery",
            ]
            with open(out / f"dd_episodes_{cand_name}.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(table)

    return out
