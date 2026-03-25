# BTC/USDT Spot Long-Only V6 Research Report

## Protocol
This run followed the V6 protocol from the supplied prompt and raw data only. No prior reports, prior frozen systems, or prior result tables were consulted before freeze. The raw audit found a small number of H4 timing anomalies and one duplicate H4 close_time caused by a zero-duration zero-activity row; all were retained and logged.

## Final internal judgment
- **Frozen winner before reserve/internal:** `S3_H4_RET168_Z0`
- **Evidence label:** `INTERNAL ROBUST CANDIDATE`
- **Benchmark comparison:** not performed (no benchmark specs supplied after reserve)

## Why the frozen winner was selected
- Discovery + holdout: strong positive edge after 20 bps cost.
- Broad local plateau around the chosen H4 lookback.
- The nearest more complex rival (`L2_D1RET40_Z0_AND_H4RET168_Z0`) did not show a meaningful paired-bootstrap advantage over the simpler winner.
- The nearest serious simple slower rival (`S1_D1_RET40_Z0`) stayed alive into the frozen comparison set, but pre-reserve the H4 trend frontier had slightly stronger risk-adjusted performance and lower drawdown.

## Major caveat from reserve/internal
Reserve/internal materially weakened the frozen winner. The reserve CAGR for `S3_H4_RET168_Z0` was -5.754%, versus 11.873% for `S1_D1_RET40_Z0`. On full internal data, the frozen winner became sign-reversed in the bear regime. That does **not** retroactively permit redesign under V6, but it does lower confidence and makes appended future data the decisive next test.

## Key files
- `data_audit_report.md`
- `phase1_data_decomposition.md`
- `frozen_system_specification.md`
- `frozen_system.json`
- `tables/validation_summary.csv`
- `tables/selection_judgment.csv`
- `tables/reserve_internal_evaluation.csv`
- `provenance_declaration.json`
