# Frozen System Spec — btcsd_20260318_c3_trade4h15m

## Version Identity
- system_version_id: `V1`
- parent_system_version_id: `null`
- freeze_cutoff_utc: `2026-03-18T23:59:59.999000+00:00`
- design_inputs_end_utc: `2026-03-18T23:59:59.999000+00:00`
- reason_for_freeze: Initial mainline seed freeze after seed discovery session session_20260319_seed_001 on snapshot_20260318; live lineup fixed after discovery WFO, holdout, reserve_internal, and bootstrap review under constitution v4.0.

## Candidate Identity
- candidate_id: `btcsd_20260318_c3_trade4h15m`
- mechanism_type: daily trade-surprise permission plus 4h range-position context plus 15m relative-volume timing, long-only
- role: `champion`

## Provenance
- session_id: `session_20260319_seed_001`
- snapshot_id: `snapshot_20260318`
- constitution_version: `4.0`

## Tunable Quantities (frozen values)
- `q_h4_rangepos_entry = 0.65`
- `q_h4_rangepos_hold = 0.35`
- `rho_m15_relvol_min = 1.10`

## Fixed Quantities
- `d1_trade_surprise_window = 168`
- `h4_rangepos_window = 168`
- `m15_relvol_window = 168`
- `d1_trade_model = log1p(num_trades) = alpha + beta * log1p(volume) + eps`
- decision timeframe = `15m`
- signal direction = `long-only`
- binary position sizing = `{0.0, 1.0}`

## Layer Count
- `3`

## Warmup Requirement
- `15m`: minimum `168` fully closed bars
- `4h`: minimum `168` fully closed bars
- `1d`: bounded feature minimum `168` fully closed bars for `d1_trade_surprise168`
- strict deterministic replay note: `alpha` and `beta` are fit on **all** fully closed D1 bars with `D1.close_time < evaluation_start_utc`; therefore deterministic replay for a new evaluation segment must include the entire prior D1 history back to the earliest available bar before that segment start, not merely the last `168` D1 bars

## Signal Logic (unambiguous pseudocode)
```text
INPUTS:
  D1 bars with canonical fields
  H4 bars with canonical fields
  M15 bars with canonical fields

HELPERS:
  segment_id(tf) = cumulative count of bars where open_time difference != interval_ms; first bar starts new segment
  gap_rolling_mean(x, w) = rolling mean over last w bars within same segment; NaN until w bars available
  gap_rolling_min(x, w) = rolling min over last w bars within same segment; NaN until w bars available
  gap_rolling_max(x, w) = rolling max over last w bars within same segment; NaN until w bars available

FIT DAILY TRADE MODEL:
  Given evaluation_start_utc:
    fit set = all D1 bars with D1.close_time < evaluation_start_utc
    if fit set has fewer than 2 bars:
      fit set = first min(max(2, len(D1)), 365) D1 bars
    x = log1p(volume) on fit set
    y = log1p(num_trades) on fit set
    x_mean = mean(x)
    y_mean = mean(y)
    x_var = mean((x - x_mean)^2)
    if x_var <= 0:
      beta = 0
    else:
      beta = mean((x - x_mean) * (y - y_mean)) / x_var
    alpha = y_mean - beta * x_mean

FEATURES ON D1:
  For every D1 bar t:
    eps[t] = log1p(num_trades[t]) - (alpha + beta * log1p(volume[t]))
    eps_mean168[t] = gap_rolling_mean(eps, 168)[t]
    d1_trade_surprise168[t] = eps[t] - eps_mean168[t]

FEATURES ON H4:
  h4_lo168[t] = gap_rolling_min(low, 168)[t]
  h4_hi168[t] = gap_rolling_max(high, 168)[t]
  if h4_hi168[t] - h4_lo168[t] <= 0 -> h4_rangepos168[t] = NaN
  else h4_rangepos168[t] = (close[t] - h4_lo168[t]) / (h4_hi168[t] - h4_lo168[t])

FEATURES ON M15:
  m15_vol_mean168[t] = gap_rolling_mean(volume, 168)[t]
  if m15_vol_mean168[t] == 0 or NaN -> m15_relvol168[t] = NaN
  else m15_relvol168[t] = volume[t] / m15_vol_mean168[t]

ALIGNMENT:
  For each M15 decision bar i:
    find latest fully closed D1 bar j with D1.close_time[j] <= M15.close_time[i]
    find latest fully closed H4 bar k with H4.close_time[k] <= M15.close_time[i]
    d1_permission_i = d1_trade_surprise168[j]
    h4_context_i    = h4_rangepos168[k]

ENTRY CONDITION ON M15 DECISION BAR i:
  entry_cond[i] =
    (d1_permission_i > 0.0) AND
    (h4_context_i    >= 0.65) AND
    (m15_relvol168[i] >= 1.10)

HOLD CONDITION ON M15 DECISION BAR i:
  hold_cond[i] =
    (d1_permission_i > 0.0) AND
    (h4_context_i    >= 0.35)

EXIT CONDITION ON M15 DECISION BAR i:
  exit_cond[i] = NOT hold_cond[i]
```

## Execution Logic (unambiguous pseudocode)
```text
STATE VARIABLES:
  current_pos ∈ {0, 1}
  current_entry_time_utc ∈ {timestamp, null}
  current_entry_price ∈ {float, null}

INITIAL STATE:
  if initial_state is null:
    current_pos = 0
    current_entry_time_utc = null
    current_entry_price = null
  else:
    current_pos = 1 iff initial_state.position_state == "long" AND initial_state.position_fraction > 0
    current_entry_time_utc = initial_state.entry_time_utc
    current_entry_price = initial_state.entry_price

DECISION / FILL TIMESTAMPS:
  For each M15 bar i except the last two bars:
    decision_time = M15.close_time[i]
    exec_time     = M15.open_time[i+1]
    exec_open     = M15.open[i+1]
    next_exec_open = M15.open[i+2]
    interval_return = next_exec_open / exec_open - 1

TRADING WINDOW:
  A bar is tradable iff exec_time is within [start_utc, end_utc], inclusive.
  start_utc and end_utc are interpreted in UTC.
  If a date-only string is used for end_utc, expand it to 23:59:59.999 UTC on that date.

TRANSITIONS ON TRADABLE BAR i:
  if current_pos == 0:
    if entry_cond[i] == TRUE:
      next_pos = 1
      trade_delta = +1
      current_entry_time_utc = exec_time
      current_entry_price = exec_open
    else:
      next_pos = 0
      trade_delta = 0

  else if current_pos == 1:
    if hold_cond[i] == FALSE:
      next_pos = 0
      trade_delta = -1
      current_entry_time_utc = null
      current_entry_price = null
    else:
      next_pos = 1
      trade_delta = 0

NON-TRADABLE BAR:
  next_pos = current_pos
  trade_delta = 0

PER-INTERVAL PNL:
  side_cost = cost_rt_bps / 20000.0
  gross_return = next_pos * interval_return
  net_return   = gross_return - abs(trade_delta) * side_cost

STATE UPDATE:
  current_pos = next_pos

DAILY RETURN AGGREGATION:
  Group interval returns by UTC calendar date of exec_time.
  For each UTC date d:
    gross_daily_return[d] = product(1 + gross_return_k over date d) - 1
    net_daily_return[d]   = product(1 + net_return_k   over date d) - 1

TRADE LOG:
  On each entry event, open a trade at exec_time / exec_open.
  On each exit event, close the open trade at exec_time / exec_open.
  trade_gross_return = exit_price / entry_price - 1
  trade_net_return   = trade_gross_return - 2 * side_cost
```

## Position Sizing (unambiguous pseudocode)
```text
if current_pos == 0:
  position_fraction = 0.0
if current_pos == 1:
  position_fraction = 1.0

No leverage.
No pyramiding.
No partial scaling.
Long-only; short position is never allowed.
```

## Exact Cost Model
```text
cost_rt_bps ∈ {20, 50}
side_cost = cost_rt_bps / 20000.0

If cost_rt_bps = 20:
  side_cost = 0.0010  # 10 bps per side

If cost_rt_bps = 50:
  side_cost = 0.0025  # 25 bps per side

Cost is applied only to net return / net metrics.
Signal generation, entry/exit decisions, and all path-dependent state are invariant to cost_rt_bps.
```

## Evidence Summary

### Discovery WFO aggregate
- representative_config_id: `cfg_025`
- Calmar_50bps: `1.039666`
- CAGR_50bps: `0.397348` (39.7348%)
- Sharpe_50bps: `1.010698`
- MDD_50bps: `0.382188` (38.2188%)
- total_entries: `65`
- avg_exposure: `0.370755` (37.0755%)

### Holdout
- 20bps: CAGR `0.448199` (44.8199%), Sharpe `1.331846`, MDD `0.277709` (27.7709%), entries `34`, exposure `0.444164` (44.4164%)
- 50bps: CAGR `0.336548` (33.6548%), Sharpe `1.075025`, MDD `0.296983` (29.6983%), entries `34`, exposure `0.444164` (44.4164%)
- holdout_hard_constraints_pass_50bps: `True`
- holdout_fail_reasons_50bps: `none`

### Reserve internal
- 20bps: CAGR `-0.044231` (-4.4231%), Sharpe `-0.051876`, MDD `0.378135` (37.8135%), entries `38`, exposure `0.319607` (31.9607%)
- 50bps: CAGR `-0.115998` (-11.5998%), Sharpe `-0.355020`, MDD `0.439382` (43.9382%), entries `38`, exposure `0.319607` (31.9607%)

### Bootstrap
- bootstrap_lb5_mean_daily_return: `0.000165030147`
- bootstrap_pass: `True`

### Complexity
- layers: `3`
- tunables: `3`
- complexity_penalty: `0.150000`
- adjusted_preference: `0.889666`
- ablation_review_flag: `True`
