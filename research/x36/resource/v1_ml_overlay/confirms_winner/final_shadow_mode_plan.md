# Final Shadow / Paper-Trading Plan

## 1. Mode

No direct live-capital cutover is authorized.
Implementation may begin only through:
1. deterministic replay / acceptance tests
2. shadow mode / paper trading

## 2. Winner frozen for shadow mode

- candidate_id = `delay_H16_p70`
- family = `DelayExit_H`
- H = 16
- threshold_percentile = 70
- deployment_threshold_value = `0.7576656445740457`

## 3. Duration recommendation

Shadow mode should continue until **both** conditions are satisfied:
1. at least `12` first-trail-stop decision events have been observed
2. at least `1` continued trade has completed via `forced_expiry`

Reason:
- `12` is the smallest validated fold OOS decision-event count for the winner candidate
- the validated winner produced continuation end-reason mix:
  - forced_expiry share = `1.0`
  - trend_exit_during_continuation share = `0.0`

There is **no automatic cutover to live capital** after the duration condition. Cutover remains manual-review only.

## 4. Per-trade logging fields

### 4.1 Decision log
- trade_id
- decision_signal_bar_index
- decision_signal_timestamp_utc
- decision_open_bar_index
- decision_open_timestamp_utc
- threshold_value
- score
- decision (`CONTINUE` / `EXIT_BASELINE`)
- full_entry_fill_bar_index
- full_entry_fill_price
- live_peak_close
- d1_regime_strength
- ema_gap_pct
- holding_bars_to_exit_signal
- return_from_entry_to_signal
- peak_runup_from_entry
- atr_percentile_100
- per-feature support-breach flags
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
- equity_after_fill
- position_fraction_after

## 5. Daily monitoring metrics

Daily report must include:
- first-trail-stop decision count
- `CONTINUE` count
- `EXIT_BASELINE` count
- active continuation count
- forced_expiry count
- trend_exit_during_continuation count
- score min / median / max for first decisions
- threshold_value in force
- any_feature_oos event count
- noncomputable_live_score_event count
- recursive_rescore_count
- negative_cash_flag
- state_machine_error_flag
- position_bounds_violation_flag
- cumulative average exposure since shadow start

## 6. Weekly drift review

Weekly review must include:
- cumulative first-decision score median
- cumulative first-decision score p95
- cumulative first-decision any-feature OOD rate
- cumulative average exposure
- cumulative first-decision count
- cumulative continuation count
- continuation end-reason mix
- realized continuation utility statistics for matured continuations

## 7. Frozen reference bands for review

These are **review bands**, not new research thresholds.

### 7.1 Score distribution bands from validated winner folds
- score median band: [`0.559829`, `0.669778`]
- score p95 band: [`0.771043`, `0.897831`]

### 7.2 Decision frequency band
Once at least `1000` shadow H4 bars have accrued, compare:
- first-decision rate per 1000 H4 bars
- validated winner fold band: [`8.230453`, `11.882998`]

### 7.3 Exposure band
- cumulative average exposure review band: [`0.274348`, `0.544180`]

### 7.4 Continuation end-reason expectations
Validated winner fold ranges:
- forced_expiry share: [`1.000000`, `1.000000`]
- trend_exit_during_continuation share: [`0.000000`, `0.000000`]

### 7.5 Full-178 feature support ranges for OOD monitoring
| feature | min | max |
|---|---:|---:|
| d1_regime_strength | -0.041675 | 0.251805 |
| ema_gap_pct | -0.000510 | 0.195354 |
| holding_bars_to_exit_signal | 3 | 212 |
| return_from_entry_to_signal | -0.124649 | 0.634514 |
| peak_runup_from_entry | 0.000000 | 0.831725 |
| atr_percentile_100 | 0.01 | 1.00 |

## 8. Hard kill-switch rules

Immediate disable / stop-shadow-and-review if any of the following occurs:
1. `recursive_rescore_count > 0`
2. any `noncomputable_live_score_event`
3. any `negative_cash_flag == true`
4. any `state_machine_error_flag == true`
5. any `position_bounds_violation_flag == true`
6. any continuation end-reason outside:
   - `forced_expiry`
   - `trend_exit_during_continuation`
7. replay / acceptance test mismatch versus frozen score or frozen threshold

## 9. Review-required triggers

These do **not** automatically disable the strategy, but they require formal review before progressing beyond shadow mode:

1. any first-decision event with `any_feature_oos_flag == 1`
2. after at least `10` first-decision events, cumulative score median leaves the validated band
3. after at least `10` first-decision events, cumulative score p95 leaves the validated band
4. after at least `1000` shadow H4 bars, decision rate per 1000 bars leaves the validated band
5. cumulative average exposure leaves the validated band
6. any `trend_exit_during_continuation` event occurs
7. continuation end-reason mix diverges from the validated expectation (`forced_expiry = 1.0`, `trend_exit_during_continuation = 0.0`)
8. realized continuation utility stats become materially adverse; because no clean numeric validation band is frozen for this metric, this remains manual-review only

## 10. No automatic live-capital promotion

Passing shadow mode does not create an automatic live-trading promotion.
A separate implementation sign-off must confirm:
- all acceptance tests pass
- no hard kill-switch event occurred
- all review-required items have documented disposition
