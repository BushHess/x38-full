"""Single source of truth for authority-bearing decision thresholds.

Provenance classifications (Threshold Governance Policy, 2026-03-08):
  STAT                -- statistical derivation with simulation or analytical formula
  LIT                 -- literature reference (published paper or industry standard)
  CONV                -- convention with documented sensitivity range
  CONV:UNCALIBRATED   -- convention without sensitivity analysis (requires calibration)
  UNPROVEN            -- no provenance at all (requires immediate remediation)

Legacy provenance labels (Report 32, 2026-03-04) are retained in comments for traceability.

These constants are shared between suite producers and the decision consumer.
Changing a value here affects both producer status and consumer gate evaluation.

See: docs/validation/THRESHOLD_GOVERNANCE_POLICY.md
See: research_reports/32_threshold_provenance_heuristic_governance_audit.md
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Decision gate thresholds
# ---------------------------------------------------------------------------

# T01/T02: Backtest & holdout harsh score tolerance (delta >= -TOLERANCE).
# Classification: CONV:UNCALIBRATED
# Legacy provenance: documented but weak (Report 32 H01/H02).
# Allows up to 20% relative score degradation as noise margin.
# No statistical calibration exists; design choice endorsed by Report 27.
# Calibration needed: bootstrap score under H0, set tolerance = 95th pct + margin.
HARSH_SCORE_TOLERANCE: float = 0.2

# T03: WFO win-rate threshold (win_rate >= THRESHOLD when n_windows > SMALL_SAMPLE_CUTOFF).
# Classification: UNPROVEN
# Legacy provenance: unproven (Report 32 H04).
# 60% does not correspond to a standard significance level for typical window counts.
# For N=8: P(>=5/8|H0)=0.363 — not any standard alpha.
# Calibration needed: binomial exact test inversion, N-dependent cutoff at chosen alpha.
WFO_WIN_RATE_THRESHOLD: float = 0.60

# T04: WFO small-sample branching cutoff (n_windows <= CUTOFF -> require N-1 positive).
# Classification: UNPROVEN
# Legacy provenance: unproven (Report 32 H05).
# No calibration for why 5 is the branching point.
# Calibration needed: eliminate by adopting continuous binomial inversion from T03.
WFO_SMALL_SAMPLE_CUTOFF: int = 5

# ---------------------------------------------------------------------------
# WFO statistical gate thresholds (replace binary win-rate as binding gates)
# ---------------------------------------------------------------------------

# T05: Wilcoxon signed-rank one-sided p-value threshold for WFO gate (binding).
# Classification: STAT
# Exact Wilcoxon signed-rank test on WFO window deltas, H_a: median(delta) > 0.
# α=0.10 chosen for small N (typical N=8): at N=8 the minimum achievable
# p-value is 1/256 ≈ 0.004, and power at α=0.05 is poor for moderate effects.
# At N=8, rejection requires sum-of-positive-ranks ≥ 28/36
# (P(W+ ≥ 28) = 25/256 ≈ 0.0977; W+ ≥ 30 would be α ≈ 0.055).
WFO_WILCOXON_ALPHA: float = 0.10

# T06: Bootstrap CI resamples for WFO mean delta gate.
# Classification: STAT
# Percentile bootstrap on mean(delta). PASS iff 95% CI lower bound > 0.
# 10_000 resamples standard per Efron & Tibshirani (1993).
WFO_BOOTSTRAP_N_RESAMPLES: int = 10_000
WFO_BOOTSTRAP_CI_ALPHA: float = 0.05

# ---------------------------------------------------------------------------
# Selection-bias gate thresholds
# ---------------------------------------------------------------------------

# T07: Probabilistic Sharpe Ratio threshold (diagnostic, no longer binding).
# Classification: LIT
# Bailey & López de Prado (2012) "The Sharpe Ratio Efficient Frontier."
# PSR(SR*) = P(true SR_candidate > SR_baseline) — relative test.
#
# DEMOTED from binding gate to diagnostic (2026-03-16):
# PSR treats sr_benchmark as a known constant, ignoring the baseline's
# estimation error and the covariance between candidate/baseline returns.
# For 2-strategy comparison this is anti-conservative (underestimates total
# uncertainty in the SR difference).  Paired evidence for "candidate beats
# baseline" is provided by WFO Wilcoxon + Bootstrap CI (wfo_robustness gate).
#
# PSR is now reported with advisory levels:
#   >= 0.95: strong support
#   0.90-0.95: moderate support
#   < 0.90: warning
# PSR alone does NOT gate PROMOTE/HOLD.  See decision.py, decision_policy.md.
PSR_THRESHOLD: float = 0.95

# T08: DSR absolute p-value threshold (advisory, no longer binding).
# Classification: LIT
# Bailey & López de Prado (2014) "The Deflated Sharpe Ratio."
# DSR tests whether observed Sharpe exceeds noise-floor from multiple testing.
# Retained as diagnostic; trivially satisfied for high-Sharpe strategies.
DSR_THRESHOLD: float = 0.95
