# Acceptance Test Plan

**Classification:** AUTHORITATIVE  
These are deterministic replay / conformance tests only. No new research is authorized.

## 1. Deployment-gating tests

| test_id | purpose | inputs | procedure | pass condition | fail interpretation | severity |
|---|---|---|---|---|---|---|
| AT-001 | Replay the 178 authoritative score-source episodes and recompute the 6 live features | `step4_feature_matrix_primary.csv`, raw H4/D1, `deployment_freeze_spec.json` | Recompute each of the 6 features at the 178 authoritative episode anchors using live formulas | `max_abs_diff <= 1e-12` for every selected feature | Feature implementation drift | BLOCKER |
| AT-002 | Replay frozen full-178 scores | same as AT-001 | Fit frozen deployment score source on the 178 authoritative episodes and score them in authoritative row order | score summary and per-row values match replay tolerance; optional hash equals `b56b06459afc47c82d0726e03849bc9b425292e1f9a93746f34c89211b723c8d` if the same numeric pipeline is used | Model/scaler drift | BLOCKER |
| AT-003 | Verify p70 threshold replay | replayed 178 score vector | Compute `numpy.quantile(scores, 0.70, method="linear")` | absolute difference vs `0.7576656445740457` <= `1e-12` | Threshold freeze mismatch | BLOCKER |
| AT-004 | Verify one-shot decision uniqueness | historical replay of winner | Count scored first-trail-stop decisions per trade | every live trade has `decision_count_first_trail_stop <= 1` | Recursive or duplicate decision logic | BLOCKER |
| AT-005 | Verify recursive rescoring is impossible | historical replay of winner | Count scored trail-stop decisions after continuation starts | `recursive_rescore_count == 0` | One-shot rule broken | BLOCKER |
| AT-006 | Verify continuation expiry semantics | historical replay of winner | Trace every continuation lifecycle | every continuation closes on or before forced expiry open and close reason belongs to frozen set | Continuation state-machine drift | BLOCKER |
| AT-007 | Verify cost application semantics | historical replay of winner | Audit every fill's fee vs transacted notional | side fee = `0.00125 * transacted_notional` for every fill | Cost application bug | HIGH |
| AT-008 | Verify continuation start has no sell fill | historical replay of winner | Inspect fills at continuation-start open for continued trades | no sell fill occurs at continuation start for `delay_H16_p70` | Winner family semantics drift | BLOCKER |
| AT-009 | Verify accounting invariants | historical replay of winner | Audit all bar / fill states | `cash >= 0`, `position_fraction in {0,1}`, no state-machine errors | Accounting or bounds bug | BLOCKER |
| AT-010 | Verify no-entry-while-notional-open rule | historical replay of winner | Search for entries while qty > 0 | zero such events | Position-management bug | BLOCKER |
| AT-011 | Verify score-to-action direction | historical replay of winner at all first decisions | Compare score and decision outcome | every `score >= threshold` maps to `CONTINUE`; every `score < threshold` maps to `EXIT_BASELINE` | Direction inversion | BLOCKER |

## 2. Regression / parity tests

| test_id | purpose | inputs | procedure | pass condition | fail interpretation | severity |
|---|---|---|---|---|---|---|
| AT-012 | Replay B3 exploratory winner semantics | internal replay harness | Reconstruct `delay_H16_p70` exploratory run at 25 bps | semantics match frozen candidate identity, H, threshold percentile, one-shot behavior, and no recursive rescoring | Internal replay harness drift | MEDIUM |
| AT-013 | Replay B4 validation winner summary | internal validation harness | Reconstruct the fixed 4-fold validation for the winner | winner metrics match frozen validation summary within tolerance: Sharpe `1.1853946679308718`, MDD `-0.3581683945426433`, WFO wins `3`, bootstrap pass, cost gate pass, exposure trap pass, added-value pass | Validation harness drift | MEDIUM |

## 3. Artifact consistency tests

| test_id | purpose | inputs | procedure | pass condition | fail interpretation | severity |
|---|---|---|---|---|---|---|
| AT-014 | Verify authoritative artifact presence | artifact bundle | Check required files listed in master spec | all required files exist and are readable | Incomplete authoritative bundle | BLOCKER |
| AT-015 | Verify deployment freeze provenance | `phaseB3_thresholds.csv`, `phaseB4_final_verdict.json`, `deployment_freeze_spec.json` | Cross-check winner id, threshold value, validation summary | all frozen facts match within stated tolerance | Package inconsistency | BLOCKER |

## 4. Severity semantics
- **BLOCKER**: deployment and shadow mode may not proceed
- **HIGH**: implementation must be corrected before sign-off
- **MEDIUM**: replay parity issue; no new research implied
