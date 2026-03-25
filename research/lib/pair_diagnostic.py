"""Machine-only Pair Diagnostic Harness (Layer A).

Automates all mechanical pair-review computation into a single entry point
that produces machine-readable output and an auto-filled markdown review
template. The harness has ZERO decision authority.

Design contract (Report 22B):
  - PairDiagnosticResult has NO decision/promote/reject/verdict field
  - All pair classification uses tolerance-based metrics (no raw float ==)
  - Suggested review routes are non-binding labels
  - The markdown template leaves the human judgment section blank

Usage
-----
    from research.lib.pair_diagnostic import run_pair_diagnostic, render_review_template

    result = run_pair_diagnostic(equity_a, equity_b, "VTREND_A0", "VCUSUM")
    template = render_review_template(result)
"""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from typing import Any

import numpy as np

from research.lib.dsr import compute_dsr
from v10.research.bootstrap import (
    PairedBootstrapResult,
    calc_sharpe,
    paired_block_bootstrap,
)
from v10.research.subsampling import (
    paired_block_subsampling,
    summarize_block_grid,
)

# ── Tolerance constants (configurable via function parameters) ──
# These are defaults, NOT hardcoded magic numbers scattered through code.
DEFAULT_TOL_EXACT: float = 1e-10   # machine epsilon (for "exact" match audit)
DEFAULT_TOL_1BP: float = 1e-4      # 1 basis point per bar
DEFAULT_TOL_10BP: float = 1e-3     # 10 basis points per bar

# ── Classification thresholds ──
CLASSIFY_1BP_NEAR_IDENTICAL: float = 0.95
CLASSIFY_CORR_NEAR_IDENTICAL: float = 0.97
CLASSIFY_1BP_BORDERLINE: float = 0.80
CLASSIFY_CORR_BORDERLINE: float = 0.90

# ── Subsampling reliability threshold ──
SUBSAMPLING_RELIABILITY_1BP_MAX: float = 0.80

# ── Review route constants ──
ROUTE_NO_ACTION = "no_action_default"
ROUTE_INCONCLUSIVE = "inconclusive_default"
ROUTE_ESCALATE_EVENT = "escalate_event_review"
ROUTE_ESCALATE_FULL = "escalate_full_manual_review"

# ── Consensus threshold ──
CONSENSUS_GAP_MAX_PP: float = 5.0  # percentage points

# ── Route anomaly threshold ──
ROUTE_BOOT_P_ANOMALY_THRESHOLD: float = 0.15  # deviation from 0.5


@dataclass(frozen=True)
class PairProfile:
    """Tolerance-based pair properties. No raw float equality."""

    n_bars: int
    # ── Tolerance-based equality rates ──
    equal_rate_tol: float           # |r_a - r_b| < tol_exact
    near_equal_1bp_rate: float      # |r_a - r_b| < tol_1bp
    near_equal_10bp_rate: float     # |r_a - r_b| < tol_10bp
    # ── Directional agreement ──
    same_direction_rate: float      # sgn(r_a) == sgn(r_b) (both zero counts as same)
    # ── Linear dependence ──
    return_correlation: float       # Pearson rho of bar returns
    # ── Exposure overlap ──
    exposure_agreement_rate: float  # both in or both out (NaN if not provided)


@dataclass(frozen=True)
class PairClassification:
    """Three-tier pair classification from tolerance-based metrics."""

    pair_class: str                 # "near_identical" | "borderline" | "materially_different"
    subsampling_reliable: bool      # False if near_equal_1bp_rate > 0.80
    primary_reason: str             # human-readable explanation


@dataclass(frozen=True)
class PairDiagnosticResult:
    """Machine-only pair diagnostic. NO decision authority.

    This object contains ONLY computed values and caveats.
    It does NOT and MUST NOT contain any promote/reject field.
    The human review note (Layer B) is a separate artifact.
    """

    # ── Pair identification ──
    label_a: str
    label_b: str

    # ── Tolerance-based profile ──
    profile: PairProfile

    # ── Classification ──
    classification: PairClassification

    # ── Bootstrap diagnostic (Sharpe statistic) ──
    boot_sharpe_p: float            # directional resampling score (NOT a p-value)
    boot_sharpe_ci_lower: float
    boot_sharpe_ci_upper: float
    boot_sharpe_ci_width: float
    boot_sharpe_observed_delta: float

    # ── Bootstrap diagnostic (geo-growth statistic, for consensus) ──
    boot_geo_p: float
    boot_geo_ci_lower: float
    boot_geo_ci_upper: float

    # ── Subsampling diagnostic (geo-growth statistic) ──
    sub_p: float                    # directional score (NOT a posterior probability)
    sub_ci_lower: float
    sub_ci_upper: float
    sub_support: float              # support ratio across block sizes

    # ── Cross-method consensus ──
    consensus_gap_pp: float         # |boot_geo_p - sub_p| in percentage points
    consensus_ok: bool              # gap < 5pp

    # ── DSR per-strategy (advisory) ──
    dsr_a: dict                     # {27: pvalue, 54: pvalue, ...}
    dsr_b: dict                     # {27: pvalue, 54: pvalue, ...}

    # ── Caveats (auto-generated list of warnings) ──
    caveats: list

    # ── Suggested review route (non-binding) ──
    suggested_route: str
    route_reason: str

    # ── Metadata ──
    bootstrap_config: dict          # {n_bootstrap, block_sizes, seed}
    timestamp_utc: str              # ISO 8601


def compute_pair_profile(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    *,
    exposure_a: np.ndarray | None = None,
    exposure_b: np.ndarray | None = None,
    tol_exact: float = DEFAULT_TOL_EXACT,
    tol_1bp: float = DEFAULT_TOL_1BP,
    tol_10bp: float = DEFAULT_TOL_10BP,
) -> PairProfile:
    """Compute tolerance-based pair profile. No raw float ==."""
    if len(returns_a) != len(returns_b):
        raise ValueError(
            f"Return arrays must have same length "
            f"({len(returns_a)} vs {len(returns_b)})"
        )
    n = len(returns_a)
    if n < 2:
        raise ValueError(f"Need at least 2 return observations, got {n}")

    diff = np.abs(returns_a - returns_b)

    equal_rate_tol = float(np.mean(diff < tol_exact))
    near_equal_1bp_rate = float(np.mean(diff < tol_1bp))
    near_equal_10bp_rate = float(np.mean(diff < tol_10bp))

    # Directional agreement: sgn(a) == sgn(b), treating zero as its own sign
    sign_a = np.sign(returns_a)
    sign_b = np.sign(returns_b)
    same_direction_rate = float(np.mean(sign_a == sign_b))

    # Pearson correlation
    if np.std(returns_a) < 1e-15 or np.std(returns_b) < 1e-15:
        return_correlation = 1.0 if np.allclose(returns_a, returns_b, atol=tol_exact) else 0.0
    else:
        return_correlation = float(np.corrcoef(returns_a, returns_b)[0, 1])

    # Exposure agreement
    if exposure_a is not None and exposure_b is not None:
        both_in = (exposure_a > 0) & (exposure_b > 0)
        both_out = (exposure_a <= 0) & (exposure_b <= 0)
        exposure_agreement_rate = float(np.mean(both_in | both_out))
    else:
        exposure_agreement_rate = float("nan")

    return PairProfile(
        n_bars=n,
        equal_rate_tol=equal_rate_tol,
        near_equal_1bp_rate=near_equal_1bp_rate,
        near_equal_10bp_rate=near_equal_10bp_rate,
        same_direction_rate=same_direction_rate,
        return_correlation=return_correlation,
        exposure_agreement_rate=exposure_agreement_rate,
    )


def classify_pair(
    profile: PairProfile,
    *,
    threshold_1bp_near_identical: float = CLASSIFY_1BP_NEAR_IDENTICAL,
    threshold_corr_near_identical: float = CLASSIFY_CORR_NEAR_IDENTICAL,
    threshold_1bp_borderline: float = CLASSIFY_1BP_BORDERLINE,
    threshold_corr_borderline: float = CLASSIFY_CORR_BORDERLINE,
    threshold_sub_reliable: float = SUBSAMPLING_RELIABILITY_1BP_MAX,
) -> PairClassification:
    """Three-tier classification from tolerance-based metrics.

    Rules (order matters — first match wins):
      near_identical:       1bp_rate > 0.95 AND corr > 0.97
      borderline:           1bp_rate > 0.80 OR  corr > 0.90
      materially_different: everything else

    Subsampling reliability threshold: 1bp_rate <= 0.80.
    Above this, block means become degenerate (Report 19, section 4).
    """
    sub_reliable = profile.near_equal_1bp_rate <= threshold_sub_reliable

    reason = (
        f"near_equal_1bp={profile.near_equal_1bp_rate:.1%}, "
        f"corr={profile.return_correlation:.3f}"
    )

    if (profile.near_equal_1bp_rate > threshold_1bp_near_identical
            and profile.return_correlation > threshold_corr_near_identical):
        return PairClassification(
            pair_class="near_identical",
            subsampling_reliable=False,
            primary_reason=reason,
        )
    if (profile.near_equal_1bp_rate > threshold_1bp_borderline
            or profile.return_correlation > threshold_corr_borderline):
        return PairClassification(
            pair_class="borderline",
            subsampling_reliable=sub_reliable,
            primary_reason=reason,
        )
    return PairClassification(
        pair_class="materially_different",
        subsampling_reliable=True,
        primary_reason=reason,
    )


def suggest_review_route(
    classification: PairClassification,
    boot_sharpe_p: float,
    consensus_ok: bool,
    caveats: list[str],
    *,
    boot_p_anomaly_threshold: float = ROUTE_BOOT_P_ANOMALY_THRESHOLD,
) -> tuple[str, str]:
    """Non-binding review route suggestion.

    Returns (route, reason). The route is a label, not a decision.
    """
    if classification.pair_class == "near_identical":
        if abs(boot_sharpe_p - 0.5) > boot_p_anomaly_threshold:
            return (
                ROUTE_ESCALATE_EVENT,
                f"near_identical pair with unexpected directional "
                f"signal (boot_p={boot_sharpe_p:.3f}, expected ~0.50)"
            )
        return (
            ROUTE_NO_ACTION,
            "near_identical pair, no anomalous signal"
        )

    if classification.pair_class == "borderline":
        return (
            ROUTE_ESCALATE_FULL,
            "borderline classification — manual review required "
            "to determine if differential series is informative"
        )

    # materially_different
    if not consensus_ok:
        return (
            ROUTE_ESCALATE_EVENT,
            "method consensus failed — investigate "
            "statistic mismatch or data issue"
        )
    if len(caveats) > 2:
        return (
            ROUTE_ESCALATE_FULL,
            f"{len(caveats)} caveats flagged — manual review recommended"
        )
    return (
        ROUTE_INCONCLUSIVE,
        "materially_different pair, diagnostics consistent, "
        "power limitation applies"
    )


def _mean_log_return(returns: np.ndarray) -> float:
    """Mean of log(1+r) — geometric growth proxy for bootstrap metric_fn."""
    log_rets = np.log1p(returns)
    return float(np.mean(log_rets))


def _extract_returns(equity: Sequence[Any]) -> np.ndarray:
    """Extract percentage returns from equity curve."""
    navs = np.array([e.nav_mid for e in equity], dtype=np.float64)
    return np.diff(navs) / navs[:-1]


def _extract_exposure(equity: Sequence[Any]) -> np.ndarray:
    """Extract exposure array from equity curve (bar-level)."""
    return np.array([e.exposure for e in equity[1:]], dtype=np.float64)


def _build_caveats(
    profile: PairProfile,
    classification: PairClassification,
    boot_sharpe_ci_width: float,
    sub_support: float,
) -> list[str]:
    """Auto-generate caveat list from diagnostic values."""
    caveats: list[str] = []

    if not classification.subsampling_reliable:
        caveats.append(
            f"Subsampling unreliable: near_equal_1bp_rate="
            f"{profile.near_equal_1bp_rate:.1%} > 80% threshold"
        )

    if boot_sharpe_ci_width > 1.0:
        caveats.append(
            f"Bootstrap Sharpe CI width={boot_sharpe_ci_width:.3f} "
            f"(wide — low discriminative power)"
        )

    if sub_support < 0.01:
        caveats.append(
            f"Subsampling support={sub_support:.2f} "
            f"(expected for available effect sizes)"
        )

    if profile.return_correlation > 0.95:
        caveats.append(
            f"Very high return correlation ({profile.return_correlation:.3f}) — "
            f"strategies may be near-equivalent"
        )

    return caveats


def run_pair_diagnostic(
    equity_a: Sequence[Any],
    equity_b: Sequence[Any],
    label_a: str,
    label_b: str,
    *,
    block_sizes: tuple[int, ...] = (10, 20, 40),
    n_bootstrap: int = 2000,
    seed: int = 1337,
    tol_exact: float = DEFAULT_TOL_EXACT,
    tol_1bp: float = DEFAULT_TOL_1BP,
    tol_10bp: float = DEFAULT_TOL_10BP,
    dsr_trial_levels: tuple[int, ...] = (27, 54, 100, 200, 500, 700),
    consensus_gap_max_pp: float = CONSENSUS_GAP_MAX_PP,
) -> PairDiagnosticResult:
    """Run ALL single-timescale diagnostics on a strategy pair.

    Returns a machine-only PairDiagnosticResult (Layer A).
    NO decision, NO decision_reasoning, NO promote/reject.
    The human writes their review note separately (Layer B).
    """
    # 1. Extract returns from equity curves
    returns_a = _extract_returns(equity_a)
    returns_b = _extract_returns(equity_b)
    exposure_a = _extract_exposure(equity_a)
    exposure_b = _extract_exposure(equity_b)

    # 2. Compute tolerance-based pair profile
    profile = compute_pair_profile(
        returns_a, returns_b,
        exposure_a=exposure_a,
        exposure_b=exposure_b,
        tol_exact=tol_exact,
        tol_1bp=tol_1bp,
        tol_10bp=tol_10bp,
    )

    # 3. Classify pair (3-tier)
    classification = classify_pair(profile)

    # 4. Bootstrap (Sharpe statistic)
    boot_sharpe = paired_block_bootstrap(
        equity_a=list(equity_a),
        equity_b=list(equity_b),
        metric_fn=calc_sharpe,
        metric_name="sharpe",
        n_bootstrap=n_bootstrap,
        block_size=block_sizes[0],
        seed=seed,
    )

    # 5. Bootstrap (geo-growth statistic, for consensus)
    boot_geo = paired_block_bootstrap(
        equity_a=list(equity_a),
        equity_b=list(equity_b),
        metric_fn=_mean_log_return,
        metric_name="mean_log_return",
        n_bootstrap=n_bootstrap,
        block_size=block_sizes[0],
        seed=seed,
    )

    # 6. Subsampling across block sizes
    sub_results = []
    for bs in block_sizes:
        try:
            sub_result = paired_block_subsampling(
                equity_a=list(equity_a),
                equity_b=list(equity_b),
                block_size=bs,
            )
            sub_results.append(sub_result)
        except ValueError:
            continue

    if sub_results:
        sub_summary = summarize_block_grid(sub_results)
        sub_p = sub_summary.median_p_a_better
        sub_ci_lower = sub_summary.median_ci_lower
        sub_ci_upper = sub_summary.median_ci_upper
        sub_support = sub_summary.support_ratio
    else:
        sub_p = float("nan")
        sub_ci_lower = float("nan")
        sub_ci_upper = float("nan")
        sub_support = float("nan")

    # 7. Consensus check: |boot_geo_p - sub_p|
    if math.isnan(sub_p) or math.isnan(boot_geo.p_a_better):
        consensus_gap_pp = float("nan")
        consensus_ok = False
    else:
        consensus_gap_pp = abs(boot_geo.p_a_better - sub_p) * 100.0
        consensus_ok = consensus_gap_pp < consensus_gap_max_pp

    # 8. DSR per strategy (advisory)
    dsr_a: dict[int, float] = {}
    dsr_b: dict[int, float] = {}
    for trials in dsr_trial_levels:
        res_a = compute_dsr(returns_a, num_trials=trials)
        dsr_a[trials] = res_a["dsr_pvalue"]
        res_b = compute_dsr(returns_b, num_trials=trials)
        dsr_b[trials] = res_b["dsr_pvalue"]

    # 9. Build caveats
    boot_sharpe_ci_width = boot_sharpe.ci_upper - boot_sharpe.ci_lower
    caveats = _build_caveats(profile, classification, boot_sharpe_ci_width, sub_support)

    # 10. Suggest review route (non-binding)
    suggested_route, route_reason = suggest_review_route(
        classification, boot_sharpe.p_a_better, consensus_ok, caveats,
    )

    # 11. Assemble result
    return PairDiagnosticResult(
        label_a=label_a,
        label_b=label_b,
        profile=profile,
        classification=classification,
        boot_sharpe_p=boot_sharpe.p_a_better,
        boot_sharpe_ci_lower=boot_sharpe.ci_lower,
        boot_sharpe_ci_upper=boot_sharpe.ci_upper,
        boot_sharpe_ci_width=boot_sharpe_ci_width,
        boot_sharpe_observed_delta=boot_sharpe.observed_delta,
        boot_geo_p=boot_geo.p_a_better,
        boot_geo_ci_lower=boot_geo.ci_lower,
        boot_geo_ci_upper=boot_geo.ci_upper,
        sub_p=sub_p,
        sub_ci_lower=sub_ci_lower,
        sub_ci_upper=sub_ci_upper,
        sub_support=sub_support,
        consensus_gap_pp=consensus_gap_pp,
        consensus_ok=consensus_ok,
        dsr_a=dsr_a,
        dsr_b=dsr_b,
        caveats=caveats,
        suggested_route=suggested_route,
        route_reason=route_reason,
        bootstrap_config={
            "n_bootstrap": n_bootstrap,
            "block_sizes": list(block_sizes),
            "seed": seed,
        },
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def render_review_template(diag: PairDiagnosticResult) -> str:
    """Generate markdown review template from machine diagnostic.

    The template has two sections:
      Section 1 (auto-filled): all diagnostic values, caveats, route
      Section 2 (blank): human review note
    """
    lines: list[str] = []
    lines.append(f"# Pair Diagnostic: {diag.label_a} vs {diag.label_b}")
    lines.append("")
    lines.append("## Section 1: Machine Diagnostic (auto-filled)")
    lines.append("")

    # Classification
    c = diag.classification
    lines.append(f"**Classification**: {c.pair_class}")
    lines.append(f"  {c.primary_reason}")
    lines.append(f"  subsampling_reliable={c.subsampling_reliable}")
    lines.append("")

    # Profile summary
    p = diag.profile
    lines.append(f"**Pair Profile** (n_bars={p.n_bars}):")
    lines.append(f"  equal_rate_tol={p.equal_rate_tol:.1%}")
    lines.append(f"  near_equal_1bp={p.near_equal_1bp_rate:.1%}")
    lines.append(f"  near_equal_10bp={p.near_equal_10bp_rate:.1%}")
    lines.append(f"  same_direction={p.same_direction_rate:.1%}")
    lines.append(f"  return_correlation={p.return_correlation:.3f}")
    if not math.isnan(p.exposure_agreement_rate):
        lines.append(f"  exposure_agreement={p.exposure_agreement_rate:.1%}")
    lines.append("")

    # Bootstrap (Sharpe)
    lines.append(
        f"**Bootstrap (Sharpe)**: p={diag.boot_sharpe_p:.3f}, "
        f"CI=[{diag.boot_sharpe_ci_lower:+.3f}, {diag.boot_sharpe_ci_upper:+.3f}], "
        f"width={diag.boot_sharpe_ci_width:.3f}"
    )
    lines.append(
        f"**Bootstrap (geo growth)**: p={diag.boot_geo_p:.3f}, "
        f"CI=[{diag.boot_geo_ci_lower:+.6f}, {diag.boot_geo_ci_upper:+.6f}]"
    )

    # Subsampling
    if math.isnan(diag.sub_p):
        lines.append("**Subsampling**: not available (all block sizes failed)")
    else:
        lines.append(
            f"**Subsampling**: p={diag.sub_p:.3f}, "
            f"CI=[{diag.sub_ci_lower:+.3f}, {diag.sub_ci_upper:+.3f}], "
            f"support={diag.sub_support:.2f}"
        )

    # Consensus
    if math.isnan(diag.consensus_gap_pp):
        lines.append("**Consensus**: not available")
    else:
        ok_str = "OK" if diag.consensus_ok else "FAILED"
        lines.append(f"**Consensus**: gap={diag.consensus_gap_pp:.1f}pp — {ok_str}")
    lines.append("")

    # DSR
    dsr_a_str = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(diag.dsr_a.items()))
    dsr_b_str = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(diag.dsr_b.items()))
    lines.append(f"**DSR ({diag.label_a})**: {{{dsr_a_str}}}  (advisory only)")
    lines.append(f"**DSR ({diag.label_b})**: {{{dsr_b_str}}}  (advisory only)")
    lines.append("")

    # Caveats
    if diag.caveats:
        lines.append("**Caveats**:")
        for caveat in diag.caveats:
            lines.append(f"  - {caveat}")
    else:
        lines.append("**Caveats**: none")
    lines.append("")

    # Suggested route
    lines.append(f"**Suggested route**: {diag.suggested_route}")
    lines.append(f"  Reason: {diag.route_reason}")
    lines.append("")

    # Metadata
    lines.append(f"**Generated**: {diag.timestamp_utc}")
    lines.append(f"**Bootstrap config**: {diag.bootstrap_config}")
    lines.append("")

    # ── Section 2: blank human section ──
    lines.append("---")
    lines.append("")
    lines.append("## Section 2: Human Review Note (researcher fills in)")
    lines.append("")
    lines.append("**Decision**: _______________")
    lines.append("  Options: NO_ACTION | INCONCLUSIVE | PROMOTE | REJECT")
    lines.append("")
    lines.append("**Reasoning**:")
    lines.append("  [Explain which diagnostics support this decision and which are")
    lines.append("  inconclusive. Cite specific values from Section 1.]")
    lines.append("")
    lines.append("**Tradeoff summary**:")
    lines.append("  [If the pair involves a Sharpe/MDD tradeoff, describe it here.]")
    lines.append("")
    lines.append("**Unresolved concerns**:")
    lines.append("  [List anything that cannot be resolved with current data.]")
    lines.append("")

    return "\n".join(lines)
