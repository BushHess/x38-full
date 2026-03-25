"""Research utilities — candidate matrix, regime analysis, DD profiling, WFO."""

from v10.research.objective import compute_objective
from v10.research.drawdown import detect_drawdown_episodes, recovery_table, DrawdownEpisode
from v10.research.regime import AnalyticalRegime, classify_d1_regimes, compute_regime_returns
from v10.research.candidates import (
    CandidateSpec,
    CandidateResult,
    load_candidates,
    build_config,
    run_candidate_matrix,
    write_matrix_outputs,
)
from v10.research.decision import (
    DecisionResult,
    GateResult,
    evaluate,
    write_decision_report,
    write_decision_json,
)
from v10.research.scenario import run_scenarios, print_scenario_comparison
from v10.research.wfo import (
    WFOWindowSpec,
    WFOSurvivor,
    generate_windows,
    expand_param_grid,
    run_wfo,
)

__all__ = [
    "compute_objective",
    "detect_drawdown_episodes",
    "recovery_table",
    "DrawdownEpisode",
    "AnalyticalRegime",
    "classify_d1_regimes",
    "compute_regime_returns",
    "CandidateSpec",
    "CandidateResult",
    "load_candidates",
    "build_config",
    "run_candidate_matrix",
    "write_matrix_outputs",
    "DecisionResult",
    "GateResult",
    "evaluate",
    "write_decision_report",
    "write_decision_json",
    "run_scenarios",
    "print_scenario_comparison",
    "WFOWindowSpec",
    "WFOSurvivor",
    "generate_windows",
    "expand_param_grid",
    "run_wfo",
]
