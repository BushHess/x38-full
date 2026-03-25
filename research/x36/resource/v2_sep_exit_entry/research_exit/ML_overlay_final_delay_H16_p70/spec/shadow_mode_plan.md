# Shadow / Paper-Trading Plan

**Classification:** AUTHORITATIVE  
No direct live-capital cutover is authorized.

## 1. Pre-live prerequisite checklist
All of the following must be complete before shadow mode starts:
- acceptance tests AT-001 through AT-011 all pass
- deployment threshold replay matches `0.7576656445740457`
- deployment score source replay on 178 authoritative episodes passes
- no implementation ambiguity remains in the event loop
- frozen winner id remains `delay_H16_p70`

## 2. Replay-before-shadow checklist
Before each shadow release:
- replay the 178 authoritative score-source episodes
- replay the frozen p70 threshold
- run one-shot integrity replay
- verify no recursive rescoring
- verify no negative cash / bounds / state-machine issues
- verify decision direction still maps `score >= threshold` to `CONTINUE`

## 3. Shadow duration recommendation
Shadow mode should continue until both are true:
1. at least `12` first-trail-stop decision events have been observed
2. at least `1` continuation has completed via `forced_expiry`

This is a **minimum** review horizon, not an auto-promotion trigger.

## 4. Required per-event logging
### 4.1 Decision log
- trade_id
- decision_signal_timestamp_utc
- scheduled_baseline_exit_open_timestamp_utc
- score
- threshold_value
- decision
- d1_regime_strength
- ema_gap_pct
- holding_bars_to_exit_signal
- return_from_entry_to_signal
- peak_runup_from_entry
- atr_percentile_100
- per-feature OOD flags
- any_feature_oos_flag

### 4.2 Continuation log
- trade_id
- continuation_start_open_timestamp_utc
- forced_expiry_open_timestamp_utc
- continuation_end_open_timestamp_utc
- continuation_end_reason
- later_trail_signal_count_during_continuation

### 4.3 Fill / accounting log
- event_id
- trade_id
- fill_timestamp_utc
- event_type
- reason
- fill_price
- qty_before
- qty_after
- cash_before
- cash_after
- fee_usdt
- position_fraction_after

## 5. Daily monitoring metrics
Daily monitoring must include:
- first-trail decision count
- continue count
- exit-baseline count
- active continuation count
- forced_expiry count
- trend_exit_during_continuation count
- score min / median / max
- threshold in force
- any-feature OOD count
- noncomputable feature count
- recursive_rescore_count
- negative_cash_flag
- state_machine_error_flag
- position_bounds_violation_flag
- average exposure since shadow start

## 6. Weekly review metrics
Weekly review must include:
- cumulative score median
- cumulative score p95
- cumulative any-feature OOD rate
- cumulative average exposure
- cumulative first-decision count
- cumulative continuation count
- continuation end-reason mix
- realized continuation utility for matured continuations

## 7. Frozen reference bands
These are **review bands**, not new optimization targets.

### 7.1 Score distribution review bands
Derived from validated winner fold ranges:
- score median review band: [`0.559829`, `0.669778`]
- score p95 review band: [`0.771043`, `0.897831`]

### 7.2 Decision-frequency review band
After at least `1000` shadow H4 bars:
- first-decision rate per 1000 bars review band: [`8.230453`, `11.882998`]

### 7.3 Exposure review band
- aggregate average exposure review band: [`0.274348`, `0.544180`]

### 7.4 Continuation end-reason expectation
Validated winner fold range:
- forced_expiry share: [`1.000000`, `1.000000`]
- trend_exit_during_continuation share: [`0.000000`, `0.000000`]

### 7.5 OOD support ranges
Use the full-178 support ranges from `deployment_freeze_spec.json` for:
- `d1_regime_strength`
- `ema_gap_pct`
- `holding_bars_to_exit_signal`
- `return_from_entry_to_signal`
- `peak_runup_from_entry`
- `atr_percentile_100`

## 8. Hard kill-switch rules
Immediate disable and investigation if any of the following occurs:
- any recursive rescoring
- any noncomputable live feature event
- any negative cash
- any state-machine error
- any position-fraction bounds violation
- any continuation end reason outside:
  - `forced_expiry`
  - `trend_exit_during_continuation`
- replay mismatch vs frozen score source or frozen threshold

## 9. Review-required triggers
The following are not auto-disable rules, but they require formal review before advancing beyond shadow mode:
- any first decision with `any_feature_oos_flag = 1`
- after at least 10 first decisions, cumulative score median leaves the validated band
- after at least 10 first decisions, cumulative score p95 leaves the validated band
- after at least 1000 shadow H4 bars, decision rate leaves the validated band
- aggregate average exposure leaves the validated band
- any `trend_exit_during_continuation` event occurs
- continuation end-reason mix diverges from the validated expectation
- realized continuation utility becomes materially adverse; because no clean frozen numeric deployment band exists for this metric, this remains `review_required` rather than an invented hard threshold

## 10. No automatic live-capital promotion
Research is complete, but deployment promotion is not automatic.
Production capital should only be considered after:
- replay tests pass
- shadow mode completes
- no hard kill-switch event occurs
- all review-required items are resolved
