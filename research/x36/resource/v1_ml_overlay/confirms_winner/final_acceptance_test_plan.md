# Final Acceptance Test Plan

All tests below are deterministic replay / implementation-conformance tests only. No new research or validation is authorized.

## Test inventory

| test_id | purpose | input scope | exact pass condition | fail interpretation |
|---|---|---|---|---|
| AT-001 | Replay the 178 authoritative score-source episodes and recompute the 6 live features | `step4_feature_matrix_primary.csv` + raw H4/D1 replay | For each of the 6 features on all 178 episodes, `max_abs_diff <= 1e-12` versus frozen authoritative values | Feature implementation drift; deployment freeze is invalid until fixed |
| AT-002 | Verify full-178 deployment-freeze refit replay scores | Same 178 episodes, fixed 6 features, frozen hyperparameters, StandardScaler | Replayed score vector SHA256 on round-15 float64 bytes equals `ee95d13885df31ddbd19972cb58e068286e5138eae20eaf19f470e63d262cb2e` | Model/scaler drift or library/runtime mismatch |
| AT-003 | Verify frozen threshold value | Replayed 178-score vector | `numpy.quantile(scores, 0.70, method="linear") == 0.7576656445740457` within absolute tolerance `1e-15` and matches frozen B3 p70 exactly | Threshold freeze mismatch; do not deploy |
| AT-004 | Verify one-shot decision uniqueness | Internal event-driven replay on frozen historical data | `decision_count_first_trail_stop <= 1` for every trade ID | Recursive decision bug |
| AT-005 | Verify recursive rescoring forbidden | Internal replay | `recursive_rescore_count == 0` globally and per trade | One-shot rule broken |
| AT-006 | Verify continuation expiry semantics | Internal replay of winner candidate | Every continuation closes on or before forced expiry open; allowed close reasons are exactly `forced_expiry` or `trend_exit_during_continuation` | Continuation state machine bug |
| AT-007 | Verify accounting invariants | Internal replay of winner candidate | `cash >= 0` always; `position_fraction in {0,1}`; no state-machine error flags | Accounting or position-state bug |
| AT-008 | Verify DelayExit_H continuation start semantics | Internal replay of winner candidate | At continuation start open there is no sell fill; continued notional remains 100% | Winner family semantics drift |
| AT-009 | Verify cost application semantics | Internal replay of winner candidate | Every fill applies side cost = `0.00125` on transacted notional; no missing or extra fee charges | Cost application bug |
| AT-010 | Verify no-entry-while-notional-open | Internal replay of winner candidate | No new entry signal/fill is executed while any notional remains open | Position-management bug |
| AT-011 | Verify deployment decision direction | Internal replay of winner candidate on frozen first decisions | `score >= 0.7576656445740457` always maps to `CONTINUE`; `score < 0.7576656445740457` always maps to `EXIT_BASELINE` | Score-to-action semantics reversed or drifted |
| AT-012 | Optional semantic regression against frozen B3 exploratory winner | Internal backtester replay only | Replayed `delay_H16_p70` exploratory metrics match frozen B3 semantics within tolerance: Sharpe `1.581340 ± 1e-6`, MDD `-0.358168 ± 1e-6`, one-shot integrity clean | Backtester semantics do not match promoted branch |
| AT-013 | Optional semantic regression against frozen B4 validation winner | Internal validation harness replay only | Replayed aggregate WFO OOS Sharpe `1.1853946679308718 ± 1e-6`, aggregate OOS MDD `-0.3581683945426433 ± 1e-6`, WFO positive folds `3`, bootstrap pass `true`, cost gate `9/9`, exposure trap `true`, added-value gate `true` | Validation harness does not match frozen winner evidence |

## Notes

- AT-001 through AT-011 are deployment-gating acceptance tests.
- AT-012 and AT-013 are regression / parity tests for teams that maintain an internal replay or validation harness. They are not new research.
- Any failure in AT-001 through AT-011 blocks deployment and forces implementation review.
