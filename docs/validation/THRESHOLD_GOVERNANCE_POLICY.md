# Threshold Governance Policy

**Date**: 2026-03-08
**Scope**: Every numeric threshold in the validation pipeline that can influence verdict, gate status, or ERROR elevation.
**Predecessor**: Report 32 (threshold provenance audit, 2026-03-04)
**Status**: Active governance document

---

## 1. Policy Statement

Every threshold in the validation pipeline MUST have exactly one of three provenance classifications:

| Tag | Definition | Requirements |
|-----|-----------|--------------|
| **STAT** | Statistical derivation | Simulation, analytical formula, or published methodology with explicit alpha/power/sample-size linkage. Must cite the derivation (report, paper, or inline proof). |
| **LIT** | Literature reference | Published academic paper or industry standard. Must cite author, year, and the specific result. |
| **CONV** | Convention | Explicit design choice with no statistical basis. MUST document (a) the sensitivity range tested, and (b) the verdict-flip boundary (if any) within that range. If no sensitivity analysis exists, status is `CONV:UNCALIBRATED` and a calibration task is required. |

Thresholds without any of these tags are classified **UNPROVEN** and must be remediated.

### 1.1 Change Protocol

1. Any change to a STAT or LIT threshold requires re-running the underlying derivation/reference check.
2. Any change to a CONV threshold requires updating the sensitivity range.
3. New thresholds enter as `CONV:UNCALIBRATED` by default and must be calibrated within one release cycle.
4. `thresholds.py` is the single source of truth for decision-bearing constants. Suite-local hardcoded values that duplicate decision thresholds are prohibited (see H23/H24 in Report 32).

---

## 2. Complete Threshold Registry

### 2.1 Decision Gates (verdict-determining)

| ID | Constant | Value | File | Line | Gate | Severity | Provenance | Classification |
|----|----------|-------|------|------|------|----------|------------|----------------|
| T01 | `HARSH_SCORE_TOLERANCE` | 0.2 | thresholds.py | 31 | full_harsh_delta | Hard REJECT | Report 27 endorses, no statistical calibration | **CONV:UNCALIBRATED** |
| T02 | `HARSH_SCORE_TOLERANCE` (holdout) | 0.2 | thresholds.py | 31 | holdout_harsh_delta | Hard REJECT | Same constant reused; holdout has fewer trades | **CONV:UNCALIBRATED** |
| T03 | `WFO_WIN_RATE_THRESHOLD` | 0.60 | thresholds.py | 39 | wfo_robustness | Soft HOLD | No calibration. For N=8: P(>=5/8\|H0)=0.363, not any standard alpha | **UNPROVEN** |
| T04 | `WFO_SMALL_SAMPLE_CUTOFF` | 5 | thresholds.py | 46 | wfo_robustness | Route (soft) | No documentation for why 5 is the branching point | **UNPROVEN** |
| T05 | `power_windows < 3` | 3 | decision.py | 433 | wfo_low_power | Route | n=2 clearly insufficient; no formal power analysis for 3 vs 4 | **CONV:UNCALIBRATED** |
| T06 | `low_trade_ratio > 0.5` | 0.5 | decision.py | 433 | wfo_low_power | Route | Majority rule, documented in wfo_policy_low_trade.md but not calibrated | **CONV:UNCALIBRATED** |
| T07 | `SMALL_MEAN_IMPROVEMENT_THRESHOLD` | 0.0002 | trade_level.py | 33 | trade_level_bootstrap | Soft HOLD | Dimensional analysis in spec (0.0002/bar x 2190 = 44%/yr). Intentionally generous | **CONV** |
| T08 | DSR > 0.95 | 0.95 | selection_bias.py | 155 | selection_bias | Soft HOLD | Bailey & Lopez de Prado (2014): DSR>0.95 <=> z>1.645 <=> p<0.05 | **STAT** |
| T09 | PBO <= 0.5 | 0.5 | selection_bias.py | 263 | selection_bias | Soft HOLD | Bailey et al. (2015): theoretical breakeven | **LIT** |
| T10 | Lookahead status=pass | binary | decision.py | 338 | lookahead | Hard REJECT | Pytest exit code semantics; binary pass/fail | **STAT** |
| T11 | Selection-bias string match | "CAUTION"/"fallback" | decision.py | 720 | selection_bias (legacy path) | Soft HOLD | Free-text matching, documented in code. Since 2026-03-16 the primary fallback path uses method_fallback check (line ~689); T11 is the legacy no-PSR path only | **CONV** |

### 2.2 ERROR Elevation Thresholds (exit_code=3)

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T12 | `data_integrity_missing_bars_fail_pct` | 0.5 | config.py | 154 | >0.5% missing bars -> ERROR | Zero provenance (Report 32 H35) | **UNPROVEN** |
| T13 | `data_integrity_gap_multiplier` | 1.5 | config.py | 156 | Gap detection multiplier | Standard IQR outlier convention (1.5xIQR) | **LIT** |
| T14 | `data_integrity_warmup_fail_coverage_pct` | 50.0 | config.py | 158 | <50% warmup coverage -> ERROR | Zero provenance (Report 32 H36) | **UNPROVEN** |
| T15 | `data_integrity_issues_limit` | 200 | config.py | 159 | Log truncation | Display convenience only | **CONV** (no verdict impact) |
| T16 | Invariant `n_violations > 0` | 0 | decision.py | 259 | Any violation -> ERROR | Structural: any logic violation is fatal | **STAT** |

### 2.3 Objective Function Coefficients

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T17 | CAGR weight | 2.5 | objective.py | 65 | WFO score, backtest score | SPEC_METRICS design notes, no sensitivity analysis | **CONV:UNCALIBRATED** |
| T18 | MDD penalty | -0.60 | objective.py | 66 | WFO score, backtest score | SPEC_METRICS design notes, no sensitivity analysis | **CONV:UNCALIBRATED** |
| T19 | Sharpe weight | 8.0 | objective.py | 67 | WFO score, backtest score | SPEC_METRICS design notes, no sensitivity analysis | **CONV:UNCALIBRATED** |
| T20 | PF excess weight | 5.0 | objective.py | 68 | WFO score, backtest score | SPEC_METRICS design notes, no sensitivity analysis | **CONV:UNCALIBRATED** |
| T21 | Trade count weight | 5.0 | objective.py | 69 | WFO score, backtest score | SPEC_METRICS design notes, no sensitivity analysis | **CONV:UNCALIBRATED** |
| T22 | PF cap | 3.0 | objective.py | 62 | Caps infinite PF | SPEC_METRICS, qualitative intent only | **CONV:UNCALIBRATED** |
| T23 | Trade count normalizer | 50.0 | objective.py | 69 | min(n/50, 1.0) saturation | SPEC_METRICS, qualitative intent only | **CONV:UNCALIBRATED** |
| T24 | Rejection n_trades | 10 | objective.py | 73 | n_trades < 10 -> -1M score | No derivation for minimum viable trade count | **CONV:UNCALIBRATED** |

### 2.4 Bootstrap & Subsampling Configuration

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T25 | `bootstrap` (n_resamples) | 2000 | config.py | 113 | Portfolio-level bootstrap | Standard practice; 2000 sufficient for CI stability | **LIT** |
| T26 | `bootstrap_block_sizes` | [10, 20, 40] | config.py | 114 | Block lengths (bars) | Inferred from strategy autocorrelation structure, no formal ACF | **CONV:UNCALIBRATED** |
| T27 | `BOOTSTRAP_BLOCK_LENGTHS` | (42, 84, 168) | trade_level.py | 31 | Trade-level block lengths (days) | spec_trade_level_suite.md: 7d/14d/28d strategy cycle | **CONV** |
| T28 | `BOOTSTRAP_RESAMPLES` | 10,000 | trade_level.py | 32 | Trade-level resamples | Standard practice | **LIT** |
| T29 | `subsampling_ci_level` | 0.95 | config.py | 119 | Subsampling CI level | Standard 95% CI | **LIT** |
| T30 | `subsampling_p_threshold` | 0.80 | config.py | 120 | Subsampling directional p | No derivation for 80% threshold | **CONV:UNCALIBRATED** |
| T31 | `subsampling_ci_lower_threshold` | 0.0 | config.py | 121 | CI lower bound vs zero | Standard: CI entirely above 0 | **STAT** |
| T32 | `subsampling_support_ratio_threshold` | 0.60 | config.py | 122 | Support ratio cutoff | No derivation | **CONV:UNCALIBRATED** |

### 2.5 WFO Configuration

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T33 | `low_trade_threshold` | 5 | config.py | 130 | WFO low-trade window flag | Config default, no documentation (Report 32 H27) | **UNPROVEN** |
| T34 | `min_trades_for_power` | 5 | config.py | 131 | Statistical power minimum | Same as T33, no derivation | **UNPROVEN** |
| T35 | `holdout_frac` | 0.2 | config.py | 134 | 20% holdout split | Standard ML convention (80/20) | **LIT** |
| T36 | `wfo_train_months` | 24 | config.py | 127 | WFO train window | Design choice, no sensitivity | **CONV:UNCALIBRATED** |
| T37 | `wfo_test_months` | 6 | config.py | 128 | WFO test window | Design choice, no sensitivity | **CONV:UNCALIBRATED** |
| T38 | `harsh_cost_bps` | 50.0 | config.py | 104 | Harsh cost scenario | Deliberately above real-world (~20-30 bps) | **CONV** |

### 2.6 Churn Warning Thresholds

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T39 | `churn_warning_fee_drag_pct` | 20.0 | config.py | 166 | Fee drag >= 20% -> warn | No derivation | **CONV:UNCALIBRATED** |
| T40 | `churn_warning_cascade_leq3_pct` | 30.0 | config.py | 167 | Short cascade >= 30% -> warn | No derivation | **CONV:UNCALIBRATED** |
| T41 | `churn_warning_cascade_leq6_pct` | 50.0 | config.py | 168 | Medium cascade >= 50% -> warn | No derivation | **CONV:UNCALIBRATED** |

### 2.7 Invariant & Safety Constants

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T42 | `_EPS` | 1e-9 | invariants.py | 24 | Floating-point epsilon | IEEE 754 machine precision convention | **LIT** |
| T43 | `_EXPO_THRESHOLD` | 0.005 | invariants.py | 25 | 0.5% exposure tolerance | Mirrors engine dust-order filter | **CONV** |
| T44 | `_DEFAULT_MAX_VIOLATIONS` | 200 | invariants.py | 27 | Log truncation | Display convenience | **CONV** (no verdict impact) |
| T45 | Min daily samples for DSR | 30 | selection_bias.py | 118 | T < 30 -> fallback | Classical CLT rule of thumb; may be insufficient for BTC kurtosis | **LIT** |

### 2.8 Cost Sweep Constants

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T46 | `cost_sweep_bps` | [0, 10, 25, 50, 75, 100] | config.py | 160 | Sweep range | Design choice covering realistic to extreme | **CONV** |
| T47 | `_QUICK_REPORT_YEARS` | 3.0 | cost_sweep.py | 19 | Quick mode recent window | Design choice | **CONV** |
| T48 | `_QUICK_MIN_H4` | 800 | cost_sweep.py | 20 | Min bars for quick mode | ~4.9 months at H4; no derivation | **CONV:UNCALIBRATED** |
| T49 | `_QUICK_MIN_D1` | 120 | cost_sweep.py | 21 | Min D1 bars for quick mode | ~4 months; no derivation | **CONV:UNCALIBRATED** |

### 2.9 Sensitivity Grid

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T50 | `grid_aggr` | [0.85, 0.90, 0.95] | config.py | 140 | Aggression sensitivity | +/-5% and +/-10% perturbation; convention | **CONV** |
| T51 | `grid_trail` | [2.7, 3.0, 3.3] | config.py | 141 | Trail multiplier sensitivity | +/-10% perturbation; convention | **CONV** |
| T52 | `grid_cap` | [0.75, 0.90, 0.95] | config.py | 142 | Exposure cap sensitivity | Design choice | **CONV** |

### 2.10 Drawdown Episodes

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T53 | `min_dd_pct` | 5.0 | dd_episodes.py | 33 | Minimum drawdown to detect | Design choice; 5% filters noise | **CONV** |

### 2.11 Step 5 Live Sign-off (research, not pipeline)

| ID | Constant | Value | File | Line | Context | Provenance | Classification |
|----|----------|-------|------|------|---------|------------|----------------|
| T54 | GO `p95_delta_sharpe` | -0.15 | run_step5_live_signoff.py | 80 | Stochastic delay tolerance | Design choice for latency robustness | **CONV:UNCALIBRATED** |
| T55 | GO `p_cagr_le_0` | 0.10 | run_step5_live_signoff.py | 81 | P(CAGR<=0) under delays | 10% ruin probability cap | **CONV:UNCALIBRATED** |
| T56 | GO `p95_delta_mdd_frac` | 0.25 | run_step5_live_signoff.py | 82 | MDD fractional increase | 25% MDD increase at p95 | **CONV:UNCALIBRATED** |
| T57 | GO `worst_combo_delta_sharpe` | -0.20 | run_step5_live_signoff.py | 83 | Worst-case combined disruption | Design choice | **CONV:UNCALIBRATED** |
| T58 | GO_WITH_GUARDS `p95_delta_sharpe` | -0.30 | run_step5_live_signoff.py | 86 | Relaxed tier | Design choice | **CONV:UNCALIBRATED** |
| T59 | GO_WITH_GUARDS `p_cagr_le_0` | 0.20 | run_step5_live_signoff.py | 87 | Relaxed tier | Design choice | **CONV:UNCALIBRATED** |
| T60 | GO_WITH_GUARDS `p95_delta_mdd_frac` | 0.50 | run_step5_live_signoff.py | 88 | Relaxed tier | Design choice | **CONV:UNCALIBRATED** |
| T61 | GO_WITH_GUARDS `worst_combo_delta_sharpe` | -0.35 | run_step5_live_signoff.py | 89 | Relaxed tier | Design choice | **CONV:UNCALIBRATED** |

---

## 3. Classification Summary

| Classification | Count | IDs |
|---------------|-------|-----|
| **STAT** (statistical derivation) | 4 | T08, T10, T16, T31 |
| **LIT** (literature reference) | 7 | T09, T13, T25, T28, T29, T35, T42, T45 |
| **CONV** (convention, calibrated or low-impact) | 14 | T07, T11, T15, T27, T38, T43, T44, T46, T47, T50, T51, T52, T53, T26* |
| **CONV:UNCALIBRATED** (convention, needs sensitivity) | 24 | T01, T02, T05, T06, T17-T24, T26, T30, T32, T36, T37, T39-T41, T48, T49, T54-T61 |
| **UNPROVEN** (no provenance at all) | 5 | T03, T04, T12, T14, T33, T34 |

---

## 4. Remediation Plan: UNPROVEN Thresholds

### T03 — WFO Win Rate = 0.60 (UNPROVEN)

**Problem**: 60% does not map to any standard significance level. For N=8 windows, P(>=5/8|H0) = 0.363 (binomial). This is neither alpha=0.05 nor alpha=0.10.

**Calibration method**: Binomial exact test inversion.
1. For each plausible N (3..12 windows), compute the minimum k such that P(>=k/N | p=0.5) <= alpha for alpha in {0.05, 0.10, 0.20}.
2. Express as win_rate_threshold = f(N, alpha). For N=8, alpha=0.05 requires 7/8 (87.5%); alpha=0.10 requires 7/8; alpha=0.20 requires 6/8 (75%).
3. Alternatively: run bootstrap simulation over archived validation runs. Permute window labels (positive/negative) 10,000 times, measure empirical false-positive rate at each threshold.
4. **Recommendation**: Replace fixed 0.60 with N-dependent binomial cutoff at alpha=0.10, or adopt a WFO-specific permutation test. Document the chosen alpha.

### T04 — WFO Small-Sample Cutoff = 5 (UNPROVEN)

**Problem**: No justification for why N=5 is the branching point between "require N-1 positive" and "require win_rate >= 0.60".

**Calibration method**:
1. For N in {3..12}, compute the effective alpha under both branches: (a) "N-1 positive" branch gives P(>=N-1|p=0.5) = (N+1)/2^N. (b) "win_rate >= 0.60" branch gives P(>=ceil(0.6N)|p=0.5).
2. Find the N where both branches yield comparable alpha. If T03 is fixed to a binomial cutoff, T04 becomes unnecessary — the formula is continuous in N.
3. **Recommendation**: Eliminate T04 entirely by adopting the binomial inversion from T03 for all N.

### T12 — Missing Bars Fail Pct = 0.5% (UNPROVEN)

**Problem**: No documentation for why 0.5% missing bars triggers hard ERROR. At H4 over 4 years (~8760 bars), 0.5% = 44 missing bars.

**Calibration method**:
1. **Empirical impact study**: Deliberately drop 0.1%, 0.25%, 0.5%, 1.0%, 2.0%, 5.0% of bars (uniformly random, then clustered) from the canonical dataset. Run full backtest for each. Measure CAGR/Sharpe/MDD deviation from complete-data baseline.
2. Find the threshold above which metric deviation exceeds the score tolerance (T01 = 0.2).
3. Cross-check with exchange API actual missing-bar rates from historical data collection logs.
4. **Recommendation**: Set threshold at the 90th percentile of "metric deviation < 1% of score" boundary from the empirical sweep.

### T14 — Warmup Coverage Fail Pct = 50% (UNPROVEN)

**Problem**: No documentation for why 50% warmup coverage is the ERROR threshold.

**Calibration method**:
1. **Indicator convergence study**: For each indicator used (EMA, ATR, VDO), compute the number of bars needed for the indicator to converge within 1% of its asymptotic value. The worst-case (slowest) indicator sets the minimum required warmup.
2. Express as coverage_pct = bars_available / bars_required_for_convergence.
3. Run backtest with warmup coverage at 25%, 50%, 75%, 90%. Measure indicator initialization error and downstream metric deviation.
4. **Recommendation**: Set threshold at the coverage level where indicator convergence error < 0.1% of asymptotic value. Likely 70-80% for EMA(120).

### T33/T34 — Low Trade Threshold / Min Trades for Power = 5 (UNPROVEN)

**Problem**: Config default with no documentation. Controls which WFO windows are classified as statistically powered.

**Calibration method**:
1. **Power analysis**: For a two-sample t-test on trade returns with typical BTC effect size (Cohen's d ~ 0.3-0.5 from archived data), compute the minimum n for power >= 0.80.
2. For non-parametric (bootstrap) inference: simulate trade return series with known effect size, vary n from 3 to 30, measure power of the block bootstrap CI to exclude zero.
3. **Recommendation**: Result will likely be n >= 15-25 for adequate power. If so, 5 is far too low and serves only as a "non-zero activity" check, not a statistical power gate. Rename to `min_trades_for_activity` and add a separate `min_trades_for_power` at the derived value.

---

## 5. Remediation Plan: CONV:UNCALIBRATED Thresholds

### Priority 1 — High verdict impact

| ID | Threshold | Calibration Method |
|----|-----------|-------------------|
| T01/T02 | Score tolerance 0.2 | Bootstrap the score under H0 (same strategy, different cost noise). Compute the 95th percentile of |score_delta| under the null. Set tolerance = that value + 10% margin. Alternatively: compute score std from WFO window scores and set tolerance = 2 * sigma_score. |
| T05 | power_windows < 3 | See T33/T34 calibration; this becomes a function of the derived min_trades_for_power. |
| T06 | low_trade_ratio > 0.5 | Sensitivity sweep: vary from 0.3 to 0.7 in steps of 0.05 across all archived runs. Measure verdict stability. Choose the value with the largest gap between "clearly underpowered" and "marginal" runs. |

### Priority 2 — Objective function (affects all score-based gates)

| ID | Threshold | Calibration Method |
|----|-----------|-------------------|
| T17-T21 | Objective weights | **Factorial sensitivity analysis**: perturb each weight by +/-50% independently (3^5 = 243 combinations, or Latin hypercube sample). For each combination, re-run WFO and full backtest on 5+ strategies. Measure rank stability (Kendall's tau of strategy ordering). Choose the weight vector with the highest rank correlation to the desired preference ordering. Document the rank-stability surface. |
| T22 | PF cap 3.0 | Examine empirical PF distribution from all archived backtests. Set cap at the 99th percentile of observed PF values to prevent outlier domination. |
| T23 | Trade normalizer 50 | Compute the trade count at which marginal score contribution from additional trades < 0.01. Current: any n >= 50 saturates. Check if 50 is appropriate given typical trade counts (65-225 in VTREND). |
| T24 | Rejection n_trades < 10 | Minimum viable trade count for meaningful Sharpe: sqrt(n)*SR/sigma should exceed 1.645 (one-sided 5%). For typical SR ~ 1.0 and sigma ~ 1.0: n >= 3. So n=10 is conservative, which is fine — document as intentional. Reclassify to **CONV**. |

### Priority 3 — Advisory/diagnostic

| ID | Threshold | Calibration Method |
|----|-----------|-------------------|
| T26 | Bootstrap block sizes [10,20,40] | Formal ACF analysis on equity curve returns. Estimate autocorrelation decay length. Set block sizes to span {0.5x, 1x, 2x} the estimated decorrelation length. |
| T30 | Subsampling p_threshold 0.80 | Align with the standard for the methodology (Politis, Romano & Wolf 1999). If no standard exists, derive from simulation: compute false-positive rate under H0 at p=0.80 using permuted equity curves. |
| T32 | Support ratio 0.60 | Same simulation as T30. Measure the support ratio under H0 and set threshold at the 95th percentile. |
| T36/T37 | WFO train/test months | Robustness test: vary train in {12, 18, 24, 30, 36} and test in {3, 6, 9, 12}. Measure verdict stability across the grid. Document the stability region. |
| T39-T41 | Churn warning thresholds | Empirical calibration: compute fee_drag and cascade metrics for all strategies in the archived runs. Set warning thresholds at the 75th percentile of "healthy" strategies. |
| T48/T49 | Quick mode min bars | Determine the minimum bars needed for stable CAGR/Sharpe estimates (variance of rolling estimates converges). Likely ~2 years of H4 = ~4380 bars, making 800 too aggressive. |
| T54-T61 | Step 5 sign-off gates | Monte Carlo calibration: under the stochastic delay model, simulate 10,000 delay scenarios for the null hypothesis (strategy = baseline). Set GO thresholds at the 5th percentile of the null distribution. Set GO_WITH_GUARDS at the 10th percentile. |

---

## 6. Implementation Roadmap

### Phase 1 — Immediate (no code changes)
- [x] Create this governance document
- [ ] Add `CONV:UNCALIBRATED` provenance comments to all affected constants in source code
- [ ] Centralize T33/T34 into `thresholds.py` (currently only in config.py)

### Phase 2 — High-priority calibrations
- [ ] T03/T04: Binomial WFO gate (eliminates 2 UNPROVEN thresholds)
- [ ] T12/T14: Data integrity empirical sweep
- [ ] T01/T02: Score tolerance bootstrap derivation

### Phase 3 — Objective function audit
- [ ] T17-T23: Factorial weight sensitivity analysis
- [ ] T24: Document and reclassify to CONV

### Phase 4 — Full coverage
- [ ] All remaining CONV:UNCALIBRATED thresholds

---

## 7. Appendix: Cross-Reference to Report 32

| This Document | Report 32 ID | Notes |
|--------------|-------------|-------|
| T01 | H01 | Identical |
| T02 | H02 | Identical |
| T03 | H04 | Identical |
| T04 | H05 | Identical |
| T05 | H06 | Identical |
| T06 | H07 | Identical |
| T07 | H28 | Identical |
| T08 | H32 | Identical |
| T09 | H33 | Identical |
| T10 | H03 | Identical |
| T11 | H11 | Identical |
| T12 | H35 | Identical |
| T13 | H37 | New (Report 32 did not classify gap_multiplier separately) |
| T14 | H36 | Identical |
| T16 | H15 | Extended (invariant-specific) |
| T17-T23 | H26, H43, H45 | Expanded from Report 32's 3 entries to 7 |
| T33/T34 | H27 | Split into 2 entries |
| T45 | H34 | Identical |
| T54-T61 | (not in Report 32) | New: Step 5 sign-off gates |
