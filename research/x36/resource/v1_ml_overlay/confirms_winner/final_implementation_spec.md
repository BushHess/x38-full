# Final Implementation Spec — Winner Deployment Freeze

## 1. Scope

This specification freezes the promoted bounded actuator branch winner exactly as validated:
- `winner_candidate_id = delay_H16_p70`
- `family = DelayExit_H`
- `H = 16`
- `threshold_percentile = 70`
- `deployment_threshold_value = 0.7576656445740457`

No other branch, family, parameter, threshold, model, feature subset, or score source is admissible.

## 2. Frozen score source

Model family:
- `elastic_net_logistic_regression`

Label:
- `churn_signal20`

Selected feature order:
1. `d1_regime_strength`
2. `ema_gap_pct`
3. `holding_bars_to_exit_signal`
4. `return_from_entry_to_signal`
5. `peak_runup_from_entry`
6. `atr_percentile_100`

Frozen hyperparameters:
- `C = 0.1`
- `l1_ratio = 0.25`
- `solver = saga`
- `penalty = elasticnet`
- `fit_intercept = True`
- `class_weight = None`
- `max_iter = 5000`
- `tol = 1e-6`
- `random_state = 20260312`

Runtime scoring SHALL use the frozen numeric parameters below.

### 2.1 StandardScaler parameters

| feature | mean | scale |
|---|---:|---:|
| d1_regime_strength | 0.0457445730276358 | 0.0478551934841530 |
| ema_gap_pct | 0.0397857126082230 | 0.0354669842373559 |
| holding_bars_to_exit_signal | 39.0449438202247165 | 32.6583988242058325 |
| return_from_entry_to_signal | 0.0300659297756260 | 0.1127158934280498 |
| peak_runup_from_entry | 0.0899427171290960 | 0.1279757010275843 |
| atr_percentile_100 | 0.5516853932584270 | 0.3432961048851847 |

### 2.2 Frozen linear score

For a live feature vector `x`, define standardized features:
- `z_i = (x_i - mean_i) / scale_i`

Define the logit:
- `logit = 0.9360343802382904`
- `+ 0.3979207016747118 * z(d1_regime_strength)`
- `+ 0.4229829207138279 * z(ema_gap_pct)`
- `+ 0.4228286835150665 * z(holding_bars_to_exit_signal)`
- `+ 0.1937573591700770 * z(return_from_entry_to_signal)`
- `+ 0.0000000000000000 * z(peak_runup_from_entry)`
- `+ 0.2089199971226009 * z(atr_percentile_100)`

Then:
- `score = 1 / (1 + exp(-logit))`

## 3. Deployment threshold freeze

- percentile method = `numpy.quantile(..., method="linear")`
- `p70 threshold = 0.7576656445740457`

Verification versus frozen Phase B3 artifact:
- recomputed `p70 = 0.7576656445740457`
- frozen Phase B3 `p70 = 0.7576656445740457`
- exact match within tolerance `<= 1e-15`: `True`

## 4. State machine

Allowed high-level states:
1. `FLAT`
2. `BASE_LONG`
3. `CONTINUATION_LONG`

Required state variables:
- `cash`
- `qty`
- `position_fraction`
- `in_position`
- `trade_id`
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`
- `continuation_active`
- `continuation_start_open_bar_index`
- `forced_expiry_open_bar_index`
- `pending_order_type`
- `pending_order_reason`

Invariant:
- `position_fraction ∈ {0, 1}`
- `qty >= 0`
- `cash >= 0`
- `no new entry while qty > 0`

## 5. Event order per H4 bar

For each observed H4 bar `t`:

### 5.1 At bar open `t`
Execute any pending order scheduled from the prior close:
- `entry`
- `baseline trail-stop exit`
- `trend_exit`
- `forced_expiry`

Open-time precedence:
1. pending `trend_exit_during_continuation`
2. pending `baseline trail-stop exit`
3. pending `forced_expiry`
4. pending `entry`

If a continuation trade has both:
- `forced_expiry_open_bar_index == t`
- and a pending `trend_exit_during_continuation` for the same open

then the executed reason SHALL be:
- `trend_exit_during_continuation`

### 5.2 At bar close `t`
Mark-to-market equity at close.

If `FLAT`:
- evaluate frozen Base entry conditions only
- if entry signal true, schedule full entry at open `t+1`

If `BASE_LONG` and `continuation_active == False`:
1. Update `live_peak_close = max(live_peak_close, close_t)`
2. Compute frozen base trail stop:
   - `trail_stop_t = live_peak_close - 3.0 * robust_atr_t`
3. If `close_t < trail_stop_t`, this is the **only scored decision point** for the current trade.
4. Recompute the 6 live features causally.
5. Compute frozen score.
6. Decision:
   - if `score >= threshold`: `CONTINUE`
   - if `score < threshold`: `EXIT_BASELINE`
7. If `EXIT_BASELINE`:
   - schedule full exit at open `t+1`
   - no continuation phase
8. If `CONTINUE`:
   - do **not** schedule a sell at open `t+1`
   - set:
     - `continuation_active = True`
     - `continuation_start_open_bar_index = t+1`
     - `forced_expiry_open_bar_index = (t+1) + 16`
9. If no trail-stop fire and `ema_fast_t < ema_slow_t`:
   - schedule full `trend_exit` at open `t+1`

If `CONTINUATION_LONG`:
1. Update `live_peak_close = max(live_peak_close, close_t)` for logging continuity.
2. Compute the reference trailing stop for logging only:
   - `trail_stop_t = live_peak_close - 3.0 * robust_atr_t`
3. If `close_t < trail_stop_t`:
   - increment/log `later_trail_signal_count_during_continuation`
   - take **no score and no action**
4. If `ema_fast_t < ema_slow_t`:
   - schedule full `trend_exit_during_continuation` at open `t+1`
5. No recursive rescoring is allowed.

## 6. Live decision semantics

Decision point:
- first trail-stop signal close since the most recent full entry fill

Action mapping:
- if `score >= 0.7576656445740457` → `CONTINUE`
- if `score < 0.7576656445740457` → `EXIT_BASELINE`

Meaning lock:
- higher score means stronger evidence for short-horizon rebound / delayed-exit utility
- this direction is frozen and may not be reversed

## 7. Continuation semantics for the winner

Winner family:
- `DelayExit_H`

Therefore:
- continuation keeps `100%` notional
- no sell fill at continuation start
- forced expiry occurs at open of bar index `continuation_start_open_bar_index + 16`
- trend exit may force earlier full exit
- allowed end reasons:
  - `forced_expiry`
  - `trend_exit_during_continuation`

## 8. Live feature formulas

### 8.1 `d1_regime_strength`
- map the latest completed D1 bar such that `d1_close_time < decision_signal_close_time`
- `d1_regime_strength = (mapped_completed_D1_close - mapped_completed_D1_EMA21) / mapped_completed_D1_close`

### 8.2 `ema_gap_pct`
- `ema_gap_pct = (ema_fast_30_H4_t - ema_slow_120_H4_t) / ema_slow_120_H4_t`

### 8.3 `holding_bars_to_exit_signal`
- `holding_bars_to_exit_signal = decision_signal_bar_index - full_entry_fill_bar_index + 1`

### 8.4 `return_from_entry_to_signal`
- `return_from_entry_to_signal = decision_signal_close / full_entry_fill_price - 1`

### 8.5 `peak_runup_from_entry`
- define `live_trade_peak_close_through_decision_signal_bar` as the maximum H4 close from the full-entry fill bar through the decision signal bar inclusive
- `peak_runup_from_entry = live_trade_peak_close_through_decision_signal_bar / full_entry_fill_price - 1`

### 8.6 `atr_percentile_100`
- take the trailing 100 observed H4 bars ending at the decision signal bar
- compute:
  - `atr_percentile_100 = count(robust_atr_k <= robust_atr_t) / 100`
- all 100 bars must be observed H4 bars from the raw supplied timeline
- no gap imputation
- this exact deterministic rule is the same rule that reproduced `step4_feature_matrix_primary.csv`

If any selected live feature is undefined:
- deployment MUST refuse to score the event
- event outcome = `noncomputable_live_score_event`
- this is a hard stop for shadow / live operation

## 9. Accounting semantics

Per-side cost:
- `side_cost = 25 bps RT / 2 = 12.5 bps = 0.00125`

### 9.1 Full entry fill at open
- `qty = cash_before / (open_price * (1 + side_cost))`
- `fee = qty * open_price * side_cost`
- `cash_after = 0`
- `position_fraction_after = 1`

### 9.2 Full exit fill at open
- `gross = qty_before * open_price`
- `fee = gross * side_cost`
- `cash_after = cash_before + gross * (1 - side_cost)`
- `qty_after = 0`
- `position_fraction_after = 0`

No partial exit is allowed for the winner.

## 10. Required logging schema

### 10.1 Decision log
Required fields:
- `candidate_id`
- `trade_id`
- `decision_signal_bar_index`
- `decision_signal_timestamp_utc`
- `decision_open_bar_index`
- `decision_open_timestamp_utc`
- `threshold_percentile`
- `threshold_value`
- `score`
- `decision`
- `entry_fill_bar_index`
- `entry_fill_price`
- `live_peak_close`
- six live feature values
- six per-feature out-of-support flags
- `any_feature_oos_flag`

### 10.2 Continuation log
Required fields:
- `candidate_id`
- `trade_id`
- `H`
- `decision_signal_bar_index`
- `continuation_start_open_bar_index`
- `continuation_start_open_timestamp_utc`
- `continuation_start_open_price`
- `forced_expiry_open_bar_index`
- `forced_expiry_open_timestamp_utc`
- `continuation_end_open_bar_index`
- `continuation_end_open_timestamp_utc`
- `continuation_end_open_price`
- `continuation_end_reason`
- `later_trail_signal_count_during_continuation`

### 10.3 Fill / accounting log
Required fields:
- `event_id`
- `trade_id`
- `fill_timestamp_utc`
- `event_type`
- `reason`
- `fill_price`
- `qty_before`
- `qty_after`
- `cash_before`
- `cash_after`
- `fee_usdt`
- `equity_after_fill`
- `position_fraction_after`

## 11. Deterministic replay targets

Authoritative replay targets on the 178 score-source episodes:
- `score_vector_sha256_round15_float64 = ee95d13885df31ddbd19972cb58e068286e5138eae20eaf19f470e63d262cb2e`
- `p70 threshold = 0.7576656445740457`

These are the deterministic acceptance anchors for the frozen winner deployment.
