# Report 32 — Threshold Provenance, Heuristic Governance, and Empirical Incidence Audit

**Date**: 2026-03-04
**Scope**: Every threshold, routing heuristic, and string-matching rule that can influence
the final decision verdict, plus empirical incidence on 40 archived validation runs
**Predecessor**: Reports 27–31 (gate/runner/orchestration/payload/shape audits)
**Status**: Complete — analysis only, no production code changes

---

## 1. Executive Summary

**47 decision-influencing heuristics** identified across decision.py, runner.py, and 11
suite producers. Of these:

| Provenance Class | Count | Examples |
|-----------------|-------|---------|
| **Proven** (statistically justified) | 9 | DSR>0.95, PBO<=0.5, bootstrap removal, payload contracts |
| **Documented but weak** (mentioned, not calibrated) | 8 | delta tolerance -0.2, WFO objective weights, SMALL_MEAN threshold |
| **Inferred** (reasonable from context) | 7 | power_windows<3, BOOTSTRAP_BLOCK_LENGTHS, _EXPO_THRESHOLD |
| **Unproven** (no documentation) | 8 | WFO win_rate=0.60, n_windows<=5, missing_bars_fail_pct, WFO scenario priority |

**Key finding**: The 3 unproven thresholds with the highest theoretical decision authority
(H04: WFO win_rate=0.60, H05: n_windows<=5 branching, H23/H24: producer -0.2 duplicate)
are **practically inert** on current archived runs. Zero verdict flips across 12
counterfactual scenarios tested. The validation pipeline's verdicts are dominated by
binary checks (lookahead pass/fail) and gross failures (deltas of -33 to -76 vs a -0.2
tolerance), not by marginal threshold decisions.

**What remains heuristic**: The WFO win-rate threshold (0.60), small-sample branching
(n_windows<=5), and selection-bias string matching are the three heuristics with no
statistical provenance and at least soft HOLD authority. None has fired on a real run
to date.

**What lacks provenance**: 8 thresholds have no documentation at all. Most are low-authority
(advisory, truncation limits, scenario ordering), but data_integrity missing_bars_fail_pct
(0.5%) and warmup_fail_coverage_pct (50%) feed into ERROR(3) elevation and have zero
provenance.

---

## 2. Complete Heuristic Inventory

See `32_heuristic_inventory.csv` for the full 47-row machine-readable table.

### 2.1 Decision Authority Summary

| Authority Class | Count | Heuristic IDs |
|----------------|-------|---------------|
| **Hard REJECT** (exit_code=2) | 3 | H01 (backtest delta), H02 (holdout delta), H03 (lookahead) |
| **Soft HOLD** (exit_code=1) | 6 | H04 (WFO win-rate), H08/H09 (trade_level_bootstrap), H10 (matched CI<0), H11 (selection_bias), H46 (low-power missing TL) |
| **Runner ERROR elevation** (exit_code=3) | 8 | H13-H15 (payload/suite errors), H18-H22 (quality/config/output policies) |
| **Route only** (changes path, not verdict) | 9 | H05-H07 (WFO branching), H16-H17 (runner routing), H23-H25 (producer status), H34, H39 |
| **Advisory only** (no verdict impact) | 21 | H12 (bootstrap), H26-H31 (trade_level/WFO internals), H36-H40, H43-H45, H47, etc. |

### 2.2 Provenance Summary

| ID | Threshold | Authority | Provenance | Key Gap |
|----|-----------|-----------|------------|---------|
| H01 | Backtest delta ≥ -0.2 | Hard REJECT | Documented but weak | No statistical calibration |
| H02 | Holdout delta ≥ -0.2 | Hard REJECT | Documented but weak | Same; holdout has fewer trades |
| H03 | Lookahead status=pass | Hard REJECT | Proven | Pytest semantics |
| H04 | WFO win_rate ≥ 0.60 | Soft HOLD | **Unproven** | 60% ≠ any standard significance level |
| H05 | n_windows ≤ 5 branching | Route only | **Unproven** | No calibration for cutoff |
| H06 | power_windows < 3 | Route only | Inferred | n=2 clearly insufficient; no formal analysis |
| H07 | low_trade_ratio > 0.5 | Route only | Documented but weak | Majority rule, not calibrated |
| H08 | TL bootstrap low-power HOLD | Soft HOLD | Inferred | Compound condition |
| H11 | Selection-bias string match | Soft HOLD | Documented but weak | Free-text matching on risk_statement |
| H23 | Producer backtest -0.2 | Suite status | **Unproven** | Duplicates H01 without shared constant |
| H24 | Producer holdout -0.2 | Suite status | **Unproven** | Duplicates H02 without shared constant |
| H25 | Producer WFO pass threshold | Suite status | **Unproven** | Mirrors H04/H05 in producer |
| H26 | WFO objective weights | Advisory | Documented but weak | No sensitivity analysis of weights |
| H27 | low_trade_threshold=5 | Route only | **Unproven** | Config default only |
| H28 | SMALL_MEAN=0.0002 | Soft HOLD | Documented but weak | Dimensional analysis but not calibrated |
| H32 | DSR > 0.95 | Soft HOLD | **Proven** | α=0.05 per Bailey & LdP 2014 |
| H33 | PBO ≤ 0.5 | Soft HOLD | **Proven** | Theoretical breakeven per Bailey 2015 |
| H35 | missing_bars_fail_pct=0.5% | ERROR elev. | **Unproven** | Zero provenance |
| H36 | warmup_fail_coverage=50% | ERROR elev. | **Unproven** | Zero provenance |

---

## 3. Provenance Findings

### 3.1 Proven Thresholds (9)

**H03 (lookahead)**: Pytest exit code semantics — binary pass/fail, no threshold to tune.

**H12 (bootstrap removal)**: The single most thoroughly justified threshold change.
Reports 02, 18, 19, 20, 21 provide control-pair testing, power analysis, and T_eff
estimation proving the original gate (p≥0.80, ci>-0.01) had no statistical power.
Retired to diagnostic in Reports 22B/24/24B/27.

**H13, H14 (payload contract)**: Report 30 FO1-FO7 — decisive field must be finite float.

**H15 (suite error)**: Structural — suite crash means results cannot be trusted.

**H31 (H4_BAR_MS)**: Physical constant — 4 hours = 14,400,000 ms exactly.

**H32 (DSR > 0.95)**: Maps to one-sided α=0.05 per Bailey & López de Prado (2014).
DSR = Φ(z), so DSR > 0.95 ⟺ z > 1.645 ⟺ p < 0.05.

**H33 (PBO ≤ 0.5)**: Theoretical breakeven per Bailey et al. (2015). PBO > 0.5 means
in-sample optimization performs worse than random selection out-of-sample.

**H41 (regression_guard tolerances)**: Per-metric tolerances defined in golden files.
The methodology is proven; specific tolerance values are per-deployment decisions.

### 3.2 Documented but Weak (8)

**H01, H02 (delta tolerance -0.2)**: Appears in `decision_policy.md` and Report 27
endorses it as "correct," but no study derives 0.2 from score variance, bootstrap CIs,
or empirical noise distributions. DecisionPolicy makes it configurable, which partially
mitigates the provenance gap.

**H07 (low_trade_ratio > 0.5)**: `wfo_policy_low_trade.md` states "majority underpowered
= noise-driven." The 50% cutoff is common-sense majority rule, not calibrated.

**H11 (selection_bias string matching)**: Matches "CAUTION" or "fallback" in free-text
`risk_statement`. Documented in code but no formal specification of trigger conditions.

**H26 (WFO objective weights)**: Extensively used across 10+ scripts and documented in
SPEC_METRICS.md with design notes, but the specific coefficients (2.5, 0.60, 8.0, 5.0,
5.0) have no derivation or sensitivity analysis.

**H28 (SMALL_MEAN_IMPROVEMENT_THRESHOLD=0.0002)**: spec_trade_level_suite.md provides
dimensional analysis (0.0002/bar × 2190 bars/year ≈ 44% annualized) and notes it is
"intentionally generous." The spec warns "do not tighten without recalibrating."

**H43, H45 (PF cap=3.0, n_trades/50 saturation)**: SPEC_METRICS.md explains qualitative
intent but not specific values.

### 3.3 Inferred (7)

**H06 (power_windows < 3)**: n=2 is clearly insufficient for any statistical test.
`wfo_policy_low_trade.md` says "n=2 looks perfect but is meaningless." No formal power
analysis justifies 3 vs 4 vs 5.

**H08 (compound low-power HOLD)**: Follows structurally from H06/H07/H28.

**H10 (CI upper < 0)**: Standard CI interpretation — entire CI negative means even the
best-case estimate favors the baseline.

**H29 (BOOTSTRAP_BLOCK_LENGTHS)**: spec_trade_level_suite.md ties each block length to
strategy autocorrelation structure (7d momentum clustering, 14d trade cycle, 28d regime
transitions). Well-reasoned but no formal ACF analysis performed.

**H30 (BOOTSTRAP_RESAMPLES=10000)**: Standard bootstrap practice.

**H34 (min samples=30)**: Classical CLT rule of thumb. Reasonable but may be insufficient
for BTC's heavy tails (kurtosis ~25).

**H39 (_EXPO_THRESHOLD=0.005)**: Mirrors engine.py dust-order filter. 0.5% of portfolio
avoids exchange minimum-notional violations.

### 3.4 Unproven (8)

**H04 (WFO win_rate=0.60)**: Bare default on DecisionPolicy. For N=8 windows, 60%
requires 5/8 positive. Under H₀ (fair coin), P(≥5/8) = 0.363 — this does NOT correspond
to any standard significance level.

**H05 (n_windows ≤ 5 branching)**: No documentation explains why 5 is the cutoff between
win-rate-based and positive-windows-based evaluation. For N=5, requiring 4/5 has
P(≥4/5|H₀) = 0.188. For N=3, requiring 2/3 has P(≥2/3|H₀) = 0.50.

**H23, H24 (producer -0.2)**: Duplicate the consumer threshold (H01, H02) but hardcoded
in the producer without sharing the constant. Creates a maintenance risk — if the
DecisionPolicy default changes, producers still emit pass/fail at -0.2.

**H25 (producer WFO pass threshold)**: Mirrors H04/H05 in the producer. Same duplication
risk as H23/H24.

**H27 (low_trade_threshold=5)**: Config default with no documentation. Controls which
WFO windows are classified as "power" windows.

**H35 (missing_bars_fail_pct=0.5%)**: Config default feeding into ERROR(3) elevation.
Zero provenance. At H4 resolution over 4 years (~8760 bars), 0.5% ≈ 44 missing bars.

**H36 (warmup_fail_coverage_pct=50%)**: Same — config default, zero provenance, feeds
ERROR(3) elevation.

**H44 (WFO scenario priority)**: Hardcoded `harsh → base → smart` fallback chain with no
documentation for why this ordering.

---

## 4. Historical Incidence Findings

### 4.1 Dataset

56 `decision.json` files found. 40 use the modern verdict+gates format (analyzed below).
14 use legacy candidate-selection format. 1 uses rules format. 1 is overlay-specific.

### 4.2 Verdict Distribution (40 new-format runs)

| Verdict | Count | Pct |
|---------|-------|-----|
| REJECT | 29 | 72.5% |
| HOLD | 6 | 15.0% |
| ERROR | 3 | 7.5% |
| PROMOTE | 2 | 5.0% |

### 4.3 Gate Firing Frequency

| Gate | Appeared | Failed | Fail Rate | Notes |
|------|----------|--------|-----------|-------|
| full_harsh_delta | 37 | 24 | 64.9% | Dominant hard gate |
| lookahead | 30 | 26 | 86.7% | Most frequent failure |
| trade_level_bootstrap | 22 | 1 | 4.5% | Very reliable |
| wfo_robustness | 16 | 13 | 81.2% | High fail rate when present |
| trade_level_matched_delta | 11 | 0 | 0% | Never fails |
| selection_bias | 8 | 0 | 0% | Never fails |
| bootstrap | 7 | 7 | 100% | Diagnostic only (no veto) |
| holdout_harsh_delta | 7 | 3 | 42.9% | |

### 4.4 Special Condition Incidence

| Condition | Count | Pct | Detail |
|-----------|-------|-----|--------|
| wfo_low_power=true | 2 | 5.0% | step3_trade_level_suite, v13_add_throttle_default_validate |
| trade_level auto-enabled | 6 | 15.0% | Via low-power WFO warning |
| selection_bias HOLD (any) | 0 | 0% | No archived run triggered CAUTION/fallback |
| selection_bias CAUTION | 0 | 0% | All 8 risk_statements = "PASS" |
| selection_bias fallback | 0 | 0% | |
| trade_level path → HOLD | 1 | 2.5% | trade_level_bootstrap_inconclusive |
| quality policy → ERROR | 2 | 5.0% | data_integrity, invariants |
| config usage → ERROR | 1 | 2.5% | unused_config:candidate:emdd_ref_mode |
| output contract → ERROR | 0 | 0% | |

### 4.5 Unique Failure Strings (13 total)

```
bootstrap_gate_failed
duplicate_timestamps
exposure_within_max_total:200
full_harsh_delta_below_tolerance
holdout_harsh_delta_below_tolerance
invariants:exposure_within_max_total:200
lookahead_check_failed
missing_bars_pct_exceeds_threshold
ohlc_invalid_rows
trade_level_bootstrap_inconclusive
unused_config:candidate:emdd_ref_mode
warmup_missing_severe
wfo_robustness_failed
```

### 4.6 Key Patterns

1. **v13_p1_grid dominates**: 18 of 40 runs (45%) are v13 parameter grid evaluations.
   All 18 are REJECT with identical failure pattern (lookahead + full_harsh_delta).

2. **Lookahead is the tightest constraint**: 26/30 appearances fail. This is binary
   (pytest exit 0 or not) and not threshold-tunable. Many runs fail lookahead before
   any other gate can discriminate.

3. **Selection bias never fires**: All 8 archived selection_bias runs produce "PASS"
   risk_statements. The string-matching heuristic (H11) has never been exercised on
   real data.

4. **Trade-level is rarely the binding constraint**: Only 1 run (step3_trade_level_suite)
   had trade_level_bootstrap_inconclusive as a failure. trade_level_matched_delta has
   never failed.

---

## 5. Counterfactual Sensitivity Findings

38 replayable runs analyzed (40 new-format minus 2 gateless ERROR runs). 12 counterfactual
scenarios tested.

### 5.1 Results Summary

**ZERO verdict flips across all 12 scenarios.**

| Group | Alternatives Tested | Verdict Flips | Gate-Only Changes |
|-------|--------------------|--------------:|------------------:|
| Delta tolerance | -0.15, -0.20, -0.25 | 0 | 0 |
| WFO win-rate | 0.55, 0.60, 0.65 | 0 | 0 |
| WFO power_windows cutoff | <2, <3, <4 | 0 | 0 |
| WFO low-trade ratio | >0.40, >0.50, >0.60 | 0 | 0 |

### 5.2 Why Zero Flips?

The failing runs are not marginal — they are gross failures:

- **Harsh delta failures**: Deltas range from -33 to -76 against a -0.2 tolerance.
  Moving the tolerance to -0.25 or even -1.0 would not rescue any run.

- **WFO failures**: Most failing runs have win_rate=0.000 (zero positive windows).
  Even a threshold of 0.01 would not help.

- **Low-power runs**: Only 2 runs trigger low_power. Both have other binding constraints
  (lookahead or harsh delta failures) that dominate.

### 5.3 Near-Boundary Runs

Only 2 runs have values anywhere near a threshold boundary:

| Run | Metric | Value | Threshold | Margin | Binding Constraint |
|-----|--------|-------|-----------|--------|-------------------|
| amt_validation | wfo_win_rate | 0.700 | 0.60 | +0.10 | lookahead REJECT |
| step2_effective_config_score_decomp | wfo_win_rate | 0.500 | 0.60 | -0.10 | lookahead+holdout REJECT |

Neither can flip because they are locked by hard gate failures.

### 5.4 Assessment

All tunable thresholds are **practically inert** on current archived runs. The validation
pipeline's verdicts are determined by binary checks (lookahead) and gross metric failures
(deltas 150x–380x the tolerance), not by marginal threshold decisions.

**Brittle**: None (on current data)
**Stable**: All 12 scenarios tested

**Caveat**: This stability may reflect the homogeneity of archived runs (mostly v13 grid
with identical failure patterns), not inherent threshold robustness. A diverse corpus of
"almost-passing" runs would provide a more informative sensitivity test.

---

## 6. Selection-Bias Fallback Analysis

### 6.1 Findings

- **9 selection_bias.json files** found in archived outputs
- **All 9** have risk_statement = "PASS" (either "deflated Sharpe robust across tested
  trials" or "Observed Sharpe survives DSR at all tested N")
- **0** contain "CAUTION", "fallback", or "insufficient"
- **DSR passed = True** in all 8 files with explicit field (1 older format missing field)
- **PBO proxy**: Not directly stored; computed from sub-objects

### 6.2 Impact on HOLD Incidence

The selection_bias string-matching heuristic (H11) has **never produced a HOLD** on any
archived run. The 6 HOLD verdicts in the archive are all caused by:
- wfo_robustness_failed (4 runs)
- trade_level_bootstrap_inconclusive (1 run)
- bootstrap_gate_failed (1 run, pre-Report-21 legacy)

### 6.3 Genuine Caution vs Fallback Decomposition

| Category | Count |
|----------|-------|
| Genuine CAUTION from evidence | 0 |
| CAUTION from insufficient data / fallback | 0 |
| PASS (no caution at all) | 9 |
| **Total selection_bias runs** | **9** |

The selection_bias gate has not been stress-tested by real data. All archived runs use
the VTREND strategy which has strong DSR characteristics — it consistently passes the
deflated Sharpe test. The string-matching heuristic remains untested in practice.

---

## 7. WFO Low-Power Governance Analysis

### 7.1 How Often Low-Power Triggers

| Metric | Value |
|--------|-------|
| Runs with WFO results | 16 |
| wfo_low_power = true | 2 (12.5%) |
| trade_level auto-enabled | 6 (37.5%) |

The 6 auto-enabled trade_level runs include 4 that were auto-enabled by WFO warnings
(not necessarily metadata.wfo_low_power=true — the runner warning mechanism is broader
than the decision metadata flag).

### 7.2 Does Trade-Level Resolve or Propagate HOLD?

Of the 2 runs with explicit wfo_low_power=true:

1. **step3_trade_level_suite**: trade_level_bootstrap appeared, passed=False →
   "trade_level_bootstrap_inconclusive" → HOLD. Trade-level **propagated** the
   uncertainty rather than resolving it.

2. **v13_add_throttle_default_validate**: Full details not available in standard
   decision.json, but the run was REJECT from harsh_delta, so trade_level was moot.

**Assessment**: On the (very sparse) evidence available, trade_level does not
meaningfully resolve WFO low-power uncertainty. It either confirms the uncertainty
(CI crosses zero, small improvement) or is overridden by hard gate failures. Sample
size is too small (n=2) to draw firm conclusions.

### 7.3 Low-Power Routing Design

The low-power routing chain is:

```
WFO → power_windows < 3 OR low_trade_ratio > 0.5
  → wfo_low_power = true
  → WFO gate always passes (severity="soft", passed=True)
  → runner auto-enables trade_level if not already queued
  → trade_level_bootstrap evaluated:
    → CI crosses zero AND mean_diff ≤ 0.0002 → soft HOLD
    → else → passed (evidence sufficient)
  → if no trade_level_bootstrap payload → soft HOLD ("missing evidence")
```

This is a well-structured evidence-substitution pattern. The concern is that
trade_level_bootstrap's inconclusive result under low-power conditions may be the
expected mode rather than the exception, effectively making low-power WFO → HOLD
a near-deterministic outcome.

---

## 8. Producer-Contract Reality Check

963 JSON files and 14 CSV files scanned under `out/`.

### 8.1 String Booleans

**0 real violations.** 82 raw hits are all `"0"` or `"1"` inside `argv[]` / `command[]`
arrays in run_meta.json (CLI arguments are strings by definition). Every actual data
field (`hard_fail`, `pass`, `passed`) uses native JSON `true`/`false`.

### 8.2 Non-Standard Statuses

**72 case-convention hits**: `"PASS"` / `"FAIL"` (uppercase) in config_unused_fields.json.
These use their own schema and are not consumed by any gate expecting lowercase.

**6 truly non-standard values**: All in `v10_fix_loop/step0_recomputed_stats.json` — a
one-off manual audit artifact (`"MATCH"`, `"CONFIRMED"`, discrepancy notes). No pipeline
code reads this file.

### 8.3 Malformed Fields

**0 violations** in data_integrity.json, wfo_summary.json, selection_bias.json,
regression_guard.json, and invariant_violations.csv files. All use correct native types.

### 8.4 NaN/Infinity

**10 values across 2 files**:
- `trade_analysis/wfo_window_detail.json`: 4 `inf` values (SE of mean with n=1 trade)
- `wfo_invalid_fix_sample/results/wfo_summary.json`: 6 `nan` in stats_power_only
  (0 power-qualified windows → 0/0 = NaN)

Both are mathematically correct edge cases in diagnostic (non-authority-bearing) fields.
Neither feeds any automated decision gate.

**Note**: Python's `json.dumps(allow_nan=True)` produces non-standard JSON. Strict
parsers (Go, JavaScript) will reject these files.

### 8.5 Conclusion

Report 31's shape-hardening has **effectively zero real-world impact** on existing
archived artifacts. All authority-bearing producers already emit correct native types.
The hardening guards against hypothetical future regressions, not existing defects.

---

## 9. Files Changed

**No production code changes.** This is an analysis-only report.

### New files:
- `research_reports/32_threshold_provenance_heuristic_governance_audit.md` (this report)
- `research_reports/32_heuristic_inventory.csv` (47 heuristics, machine-readable)
- `research_reports/32_historical_incidence.csv` (incidence counts)
- `research_reports/32_counterfactual_sensitivity.csv` (12 scenarios)

---

## 10. Behavior Changes

**No.** This is an audit report with no code modifications.

---

## 11. Recommendations

### 11.1 Immediate Documentation/Governance Actions

1. **Document H01/H02 tolerance rationale**: The -0.2 harsh delta tolerance should have
   a documented derivation or at minimum a statement that it is a design choice. Consider
   adding a comment in DecisionPolicy explaining the intent (e.g., "allows up to 20%
   relative score degradation as acceptable noise margin").

2. **Extract shared constants for H23/H24/H25**: Producer thresholds (backtest.py L192,
   holdout.py L167, wfo.py L524-527) duplicate consumer thresholds without sharing the
   constant. If DecisionPolicy defaults change, producers will silently diverge.
   Recommendation: producers should import from a shared constants module or accept the
   tolerance as a parameter.

3. **Document H35/H36**: missing_bars_fail_pct=0.5% and warmup_fail_coverage_pct=50%
   feed into ERROR(3) elevation but have zero provenance. Add inline documentation
   explaining the design intent.

4. **Add NaN/Inf serialization guard**: Two diagnostic files contain non-standard JSON
   (NaN/Infinity). Consider using `json.dumps(default=str)` or replacing with `null`
   for cross-language compatibility.

### 11.2 Candidate Future Retune Experiments

5. **Calibrate H04 (WFO win_rate=0.60)**: Run a simulation study with known-null and
   known-positive strategy pairs to determine what win_rate threshold corresponds to a
   meaningful significance level for typical WFO window counts (6-10 windows).

6. **Calibrate H05 (n_windows≤5 branching)**: The N-1 rule for small samples has
   different implied significance levels at each N. A formal power analysis could
   determine optimal branching point and required win count.

7. **Stress-test H11 (selection_bias string matching)**: The string-matching heuristic
   has never fired. Consider running a validation with a deliberately weak strategy
   to verify the CAUTION/fallback triggering path works as intended.

8. **Validate H35/H36 against real data quality**: Run data_integrity against datasets
   with known missing-bar profiles to verify the 0.5% and 50% thresholds are neither
   too strict nor too lax.

9. **Investigate trade_level low-power resolution rate**: With only n=2 low-power runs,
   it's unclear whether trade_level_bootstrap typically resolves uncertainty or just
   propagates HOLD. Need more diverse runs to assess.

### 11.3 No-Action-Needed Heuristics

10. **H03 (lookahead)**: Binary pytest gate. No threshold to tune.

11. **H12 (bootstrap diagnostic)**: Thoroughly justified removal (Reports 02/18-21/22B).

12. **H13-H15, H18-H22 (error/contract/policy)**: Structural correctness checks. Proven.

13. **H31, H38 (physical/epsilon constants)**: H4_BAR_MS and _EPS are fixed constants.

14. **H32, H33 (DSR>0.95, PBO≤0.5)**: Statistically proven thresholds from published
    methodology.

15. **H29, H30 (bootstrap block lengths, resamples)**: Standard practices. Well-reasoned
    if not formally optimized.

16. **H39 (_EXPO_THRESHOLD=0.005)**: Mirrors engine.py dust-order filter. Engineering
    constant, not a statistical threshold.

17. **H26, H43, H45 (objective formula, PF cap, trade saturation)**: Frozen research
    artifacts. Changing these would invalidate all prior research results.

---

## 12. Remaining Ambiguities

### RA1: Threshold Redundancy Between Producer and Consumer

Backtest (-0.2), holdout (-0.2), and WFO (win-rate/positive-windows) thresholds are
evaluated independently in both the suite producer (determining `status`) and the
decision consumer (determining gate pass/fail). If these diverge (e.g., producer uses
-0.2 but consumer uses -0.15), a suite could report `status="pass"` while the consumer
gate fails. Currently they are in sync, but the coupling is implicit.

### RA2: Counterfactual Corpus Limitation

The archived runs are dominated by v13 parameter grid evaluations (18/40) which all
fail identically. A more diverse corpus — including near-passing strategies with marginal
deltas — would provide a more informative sensitivity test. Current results show stability
but may overstate robustness due to corpus homogeneity.

### RA3: Selection-Bias Path Untested

The CAUTION/fallback string-matching heuristic has never been exercised on real data.
This means the entire selection_bias → HOLD pathway is untested in production, despite
being documented and test-covered in unit tests. The gap is not in code correctness
(unit tests pass) but in empirical validation of the trigger conditions.
