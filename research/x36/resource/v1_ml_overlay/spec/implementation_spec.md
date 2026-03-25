# Implementation Spec

**Classification:** AUTHORITATIVE  
**Deployable winner:** `delay_H16_p70`

## 1. Scope

This specification defines the exact deployable strategy semantics for the promoted bounded branch winner:
- family = `DelayExit_H`
- `H = 16`
- threshold percentile = `70`
- deployment threshold numeric value = `0.7576656445740457`

No other candidate, family, threshold, model, feature subset, or decision direction is admissible.

## 2. Runtime dependencies

Required runtime inputs:
- Raw H4 data stream / historical replay with fields: open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol
- Raw D1 data stream / historical replay with fields: open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol
- Frozen deployment parameters from `deployment_freeze_spec.json`

## 3. Persistent system state

Maintain the following state variables:
- `cash`
- `qty`
- `position_fraction`
- `in_position`
- `current_trade_id`
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`
- `continuation_active`
- `continuation_start_open_bar_index`
- `forced_expiry_open_bar_index`
- `later_trail_signal_count_during_continuation`
- `pending_order_type`
- `pending_order_reason`

Required invariants:
- `cash >= 0`
- `qty >= 0`
- `position_fraction in {0,1}`
- `no new entry while qty > 0`
- `recursive_rescore_count == 0`

## 4. Base indicator computations

### 4.1 EMA fast / slow
- `EMA_slow = EMA(close_h4, 120)`
- `EMA_fast = EMA(close_h4, 30)`

### 4.2 Robust ATR
1. `TR[i] = max(high-low, abs(high-close_prev), abs(low-close_prev))`
2. For each bar with sufficient history:
   - `q = percentile(TR[i-100:i], 90)`
   - `TR_capped[i] = min(TR[i], q)`
3. `rATR[119] = mean(TR_capped[100:120])`
4. `rATR[i] = (rATR[i-1] * 19 + TR_capped[i]) / 20`

### 4.3 VDO
- `taker_sell = volume - taker_buy_base_vol`
- `vdr = (taker_buy_base_vol - taker_sell) / volume`
- `VDO = EMA(vdr, 12) - EMA(vdr, 28)`

### 4.4 D1 regime mapping
- `d1_ema21 = EMA(d1_close, 21)`
- `regime_ok = d1_close > d1_ema21`
- map to H4 using latest completed D1 with `d1_close_time < h4_close_time`

## 5. Base entry / exit semantics

### 5.1 Entry
If flat and all are true on H4 close `i`:
- `ema_fast > ema_slow`
- `VDO > 0`
- mapped `regime_ok == True`

Then schedule full long entry at H4 open `i+1`.

### 5.2 Base exit
If in position and continuation is not yet active, evaluate in order at H4 close `i`:
1. update `live_peak_close = max(live_peak_close, close_i)`
2. compute `trail_stop_i = live_peak_close - 3.0 * robust_atr_i`
3. if `close_i < trail_stop_i`, this is a trail-stop fire
4. else if `ema_fast_i < ema_slow_i`, schedule full trend exit at H4 open `i+1`

## 6. Winner overlay semantics

### 6.1 Decision-time trigger
A score may be generated **only** if:
- a trail-stop fires at H4 close `i`
- the current trade has not previously consumed its first trail-stop decision

Decision point definition:
- first trail-stop signal close since the most recent full entry fill

### 6.2 Six live features
The score input vector must be exactly:
1. `d1_regime_strength`
2. `ema_gap_pct`
3. `holding_bars_to_exit_signal`
4. `return_from_entry_to_signal`
5. `peak_runup_from_entry`
6. `atr_percentile_100`

### 6.3 Exact live feature formulas
- `d1_regime_strength = (mapped_completed_D1_close - mapped_completed_D1_EMA21) / mapped_completed_D1_close`
- `ema_gap_pct = (ema_fast_30_H4_t - ema_slow_120_H4_t) / ema_slow_120_H4_t`
- `holding_bars_to_exit_signal = decision_signal_bar_index - full_entry_fill_bar_index + 1`
- `return_from_entry_to_signal = decision_signal_close / full_entry_fill_price - 1`
- `peak_runup_from_entry = live_trade_peak_close_through_decision_signal_bar / full_entry_fill_price - 1`
- `atr_percentile_100 = percentile_rank(robust_atr_t within trailing 100 observed H4 bars ending at t)`

### 6.4 Undefined handling
If any of the six features is undefined:
- raise `automatic_fail_incomplete_live_scoring`
- do not impute
- do not fallback
- do not continue

## 7. Score generation semantics

### 7.1 Standardization
For each feature `x_i`:
- `z_i = (x_i - mean_i) / scale_i`

Use the frozen means and scales from `deployment_freeze_spec.json`.

### 7.2 Linear score
Compute:
- `logit = intercept + sum_i coef_i * z_i`
- `score = sigmoid(logit)`

### 7.3 Frozen action direction
- `score >= 0.7576656445740457` → `CONTINUE`
- `score < 0.7576656445740457` → `EXIT_BASELINE`

This direction is frozen and may not be reversed.

## 8. Continuation lifecycle

### 8.1 EXIT_BASELINE path
If decision = `EXIT_BASELINE`:
- schedule the frozen baseline full trail-stop exit at open `j`
- set no continuation state
- trade becomes flat at that fill
- do not allow a second decision for that trade

### 8.2 CONTINUE path
If decision = `CONTINUE`:
- do **not** execute a sell at continuation start open `j`
- keep `100%` notional
- set:
  - `continuation_active = True`
  - `continuation_start_open_bar_index = j`
  - `forced_expiry_open_bar_index = j + 16`

### 8.3 During continuation
At each subsequent H4 close while continuation is active:
- update `live_peak_close` for logging continuity
- if the reference trailing stop fires again, only log it
- do not score again
- do not create a new decision point
- if trend reversal condition (`ema_fast < ema_slow`) occurs, schedule full exit at next open with reason `trend_exit_during_continuation`

### 8.4 Continuation end rules
A continuation may end only by:
- `forced_expiry`
- `trend_exit_during_continuation`

### 8.5 Forced expiry
If continuation is still open and no earlier trend-exit fill occurs:
- exit full remaining notional at open of bar `forced_expiry_open_bar_index`

## 9. Cost and accounting semantics

### 9.1 Cost model
- round-trip evaluation cost = `25 bps`
- side cost = `12.5 bps` applied to transacted notional on each fill

### 9.2 Winner continuation accounting
Because the winner is `DelayExit_H`, there is:
- no sell fill at continuation start
- one full exit later, either:
  - trend exit during continuation
  - forced expiry

### 9.3 Accounting updates
On every fill:
- `fee = transacted_notional * 0.00125`
- for buy fills:
  - `cash_after = cash_before - transacted_notional - fee`
  - `qty_after = qty_before + transacted_qty`
- for sell fills:
  - `cash_after = cash_before + transacted_notional - fee`
  - `qty_after = qty_before - transacted_qty`

## 10. Logging schema

### 10.1 Decision log (mandatory)
- trade_id
- decision_signal_bar_index
- decision_signal_timestamp_utc
- scheduled_baseline_exit_open_bar_index
- scheduled_baseline_exit_open_timestamp_utc
- score
- threshold_value
- decision
- six live features
- any_feature_oos_flag
- per-feature OOS flags

### 10.2 Continuation log (mandatory)
- trade_id
- continuation_start_open_timestamp_utc
- forced_expiry_open_timestamp_utc
- continuation_end_open_timestamp_utc
- continuation_end_reason
- later_trail_signal_count_during_continuation

### 10.3 Fill log (mandatory)
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

## 11. Pseudocode

### 11.1 Base + winner event loop
```text
for each observed H4 bar t in chronological order:

    # OPEN EVENT
    if pending_order exists for open t:
        execute pending order
        update cash, qty, equity, logs

    # CLOSE EVENT
    update mark-to-market equity at close t

    if trade_eligible is false:
        continue

    if qty == 0:
        if base entry conditions are true at close t:
            schedule full entry at open t+1
        continue

    # qty > 0
    update live_peak_close = max(live_peak_close, close_t)
    compute trail_stop_t = live_peak_close - 3.0 * robust_atr_t

    if continuation_active is false:
        if close_t < trail_stop_t:
            # first and only scored decision point
            recompute the 6 live features causally
            if any feature undefined:
                raise deployment error
            score = frozen elastic-net score(feature_vector)
            if score >= threshold:
                continuation_active = true
                continuation_start_open_bar_index = t+1
                forced_expiry_open_bar_index = t+1+16
                log CONTINUE decision
            else:
                schedule full baseline trail-stop exit at open t+1
                log EXIT_BASELINE decision
        else if ema_fast_t < ema_slow_t:
            schedule full trend_exit at open t+1

    else:
        if close_t < trail_stop_t:
            log later_trail_signal_during_continuation only
        if ema_fast_t < ema_slow_t:
            schedule full trend_exit_during_continuation at open t+1
        else if open index of t+1 == forced_expiry_open_bar_index:
            schedule full forced_expiry exit at open t+1
```

### 11.2 Score generation
```text
feature_vector = [
    d1_regime_strength,
    ema_gap_pct,
    holding_bars_to_exit_signal,
    return_from_entry_to_signal,
    peak_runup_from_entry,
    atr_percentile_100
]

z_i = (x_i - mean_i) / scale_i
logit = intercept + sum_i coef_i * z_i
score = 1 / (1 + exp(-logit))
```

### 11.3 Decision logic
```text
if score >= threshold_value:
    decision = CONTINUE
else:
    decision = EXIT_BASELINE
```

### 11.4 Exit handling
```text
if continuation_active and trend_exit fill open <= forced_expiry open:
    exit reason = trend_exit_during_continuation
else if continuation_active and current open == forced_expiry open:
    exit reason = forced_expiry
else if not continuation_active and baseline trail-stop decision = EXIT_BASELINE:
    exit reason = trail_stop
else if not continuation_active and base trend reversal occurs:
    exit reason = trend_exit
```
