# Non-ML hold/continuation replacement spec

## Selection result

Chosen policy: **stateful + fixed_natural + ema12_net_quote_norm_28**.

Reason:
1. It is one of only **3** simple non-ML policies with **4/4 positive folds vs base exit**.
2. Among those 4/4-consistent policies, it has the **highest aggregate WFO OOS Sharpe**: **1.1976153943477974**.
3. It uses a **fixed physical threshold of 0.0** with **no train-time threshold search**.
4. It is the **only** 4/4-consistent non-ML policy whose aggregate Sharpe is also **slightly above** the incumbent reconstructed ML overlay (**1.197615 > 1.194133**), though it is only **1/4 positive folds vs incumbent** and therefore does **not** robustly dominate the ML overlay.

Not chosen:
- `stateful + train_threshold + ema12_net_quote_norm_28` has higher aggregate Sharpe (**1.216250**) but only **3/4** positive folds vs base exit and adds fold-wise threshold tuning on a small sample.
- `stateful + fixed_natural + ema28_imbalance_ratio_base/quote` are also 4/4-consistent, but have lower aggregate Sharpe (**1.193480**).

## Ranking among 4/4-consistent non-ML policies

| signal                      | measurement           | operator   | role     | rule_type     |   aggregate_sharpe |   aggregate_mdd |   positive_folds_vs_price_model |   avg_cont_decisions |
|:----------------------------|:----------------------|:-----------|:---------|:--------------|-------------------:|----------------:|--------------------------------:|---------------------:|
| ema12_net_quote_norm_28     | net_quote_norm_28     | ema12      | stateful | fixed_natural |            1.19762 |       -0.342735 |                               1 |                 3.5  |
| ema28_imbalance_ratio_quote | imbalance_ratio_quote | ema28      | stateful | fixed_natural |            1.19348 |       -0.348281 |                               2 |                 3.75 |
| ema28_imbalance_ratio_base  | imbalance_ratio_base  | ema28      | stateful | fixed_natural |            1.19348 |       -0.348281 |                               2 |                 3.75 |

## Aggregate metrics

- Base exit baseline Sharpe: **1.1307597999722026**
- Incumbent reconstructed ML overlay Sharpe: **1.1941332450362936**
- Chosen non-ML overlay Sharpe: **1.1976153943477974**
- Delta vs base exit: **+0.06685559437559485**
- Delta vs incumbent ML overlay (aggregate only): **+0.0034821493115038**
- Positive folds vs base exit: **4/4**
- Positive folds vs incumbent ML overlay: **1/4**

## Fold-by-fold comparison

|   fold | direction   |   threshold |   cand_sharpe |   base_sharpe |   price_model_sharpe |   delta_sharpe_vs_base |   delta_sharpe_vs_price |   cand_cont_decisions |
|-------:|:------------|------------:|--------------:|--------------:|---------------------:|-----------------------:|------------------------:|----------------------:|
|      1 | ge          |           0 |      0.65981  |     0.606679  |             0.547148 |              0.0531306 |              0.112662   |                     3 |
|      2 | ge          |           0 |      1.62776  |     1.53751   |             1.70282  |              0.0902571 |             -0.0750622  |                     7 |
|      3 | ge          |           0 |      1.83464  |     1.81857   |             1.83658  |              0.0160665 |             -0.00193604 |                     3 |
|      4 | ge          |           0 |      0.110732 |    -0.0221573 |             0.227809 |              0.132889  |             -0.117077   |                     1 |

## Full algorithm spec

### Scope lock

Only replace the **ML overlay** that decides whether to continue past the first base trail-stop event.

Do **not** change:
- entry conditions,
- D1 regime filter,
- base EMA/VDO logic,
- robust ATR calculation,
- base costs/accounting,
- 100% notional sizing,
- forced-expiry horizon **H = 16 bars**.

### Data and timing

- Trading timeframe: **H4**.
- All indicators are computed **causally** from completed H4 bars only.
- Any action decided from bar `t` close is executed at bar `t+1` open.
- No partial exits. Position is always either **flat** or **100% long**.

### Unchanged base entry

At H4 close bar `t`, while flat, schedule a full long entry at open `t+1` if and only if all are true:
- `EMA30(close)_t > EMA120(close)_t`
- `VDO_t > 0`
- mapped completed D1 bar satisfies `regime_ok = (D1_close > D1_EMA21)`

### Unchanged base trail-stop reference

Maintain per-trade:
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`

At each H4 close `t` while long:
- `live_peak_close_t = max(live_peak_close_(t-1), close_t)`
- `trail_stop_t = live_peak_close_t - 3.0 * robust_ATR_t`

The `robust_ATR` definition remains unchanged from the frozen base spec:
1. `TR_t = max(high_t - low_t, abs(high_t - close_(t-1)), abs(low_t - close_(t-1)))`, with `TR_0 = high_0 - low_0`.
2. Cap each `TR_t` from `t >= 100` at the rolling 0.90 quantile of the prior 100 uncapped TR values.
3. Compute Wilder ATR of the capped TR with period 20.

### New non-ML overlay signal

For each completed H4 bar `t` compute:

1. **Quote-side net aggressive flow**
   - `net_quote_t = taker_buy_quote_vol_t - (quote_volume_t - taker_buy_quote_vol_t)`
   - equivalently: `net_quote_t = 2 * taker_buy_quote_vol_t - quote_volume_t`

2. **28-bar quote-volume EMA**
   - `ema28_quote_volume_t = EMA_28(quote_volume)_t`

3. **Normalized net quote flow**
   - `net_quote_norm_28_t = net_quote_t / ema28_quote_volume_t`

4. **Decision signal**
   - `hold_signal_t = EMA_12(net_quote_norm_28)_t`

EMA convention is fixed and causal:
- `alpha_p = 2 / (p + 1)`
- `EMA_p[x]_0 = x_0`
- `EMA_p[x]_t = alpha_p * x_t + (1 - alpha_p) * EMA_p[x]_(t-1)` for `t >= 1`

### Threshold

- Fixed natural threshold: **0.0**
- Supportive state: `hold_signal_t >= 0.0`
- Unsupportive state: `hold_signal_t < 0.0`

There is **no** fold-wise threshold optimization, percentile thresholding, standardization, or model fitting.

### State machine

Allowed states:
1. `FLAT`
2. `BASE_LONG` (long after entry, before first trail-stop continuation decision)
3. `CONTINUATION_LONG`

Required per-trade state variables:
- `cash`, `qty`, `position_fraction`
- `trade_id`
- `full_entry_fill_bar_index`
- `full_entry_fill_price`
- `live_peak_close`
- `continuation_active`
- `continuation_start_open_bar_index`
- `forced_expiry_open_bar_index`
- `later_trail_signal_count_during_continuation`
- `pending_order_type`
- `pending_order_reason`

### Event order on each H4 bar

#### 1) At bar open `t`
Execute any pending order scheduled from the previous bar close.

Open-time precedence:
1. `trend_exit_during_continuation`
2. `guard_exit`
3. `baseline trail-stop exit`
4. `forced_expiry`
5. `entry`

If multiple reasons target the same open, apply the highest-precedence reason only.

#### 2) At bar close `t`
Mark to market at `close_t` and then evaluate logic.

### Logic while `FLAT`

If all base entry conditions are true at close `t`, schedule `entry` at open `t+1`.

### Logic while `BASE_LONG`

1. Update `live_peak_close`.
2. Compute `trail_stop_t = live_peak_close_t - 3 * robust_ATR_t`.
3. If `close_t < trail_stop_t`, this is the **only** continuation decision point for the trade.
4. Compute `hold_signal_t = EMA12(net_quote_norm_28)_t`.
5. Decision:
   - If `hold_signal_t >= 0.0`: **CONTINUE**
   - If `hold_signal_t < 0.0`: **EXIT_BASELINE**
6. If `EXIT_BASELINE`, schedule full exit at open `t+1` with reason `trail_stop`.
7. If `CONTINUE`:
   - do **not** schedule a sell at open `t+1`
   - set `continuation_active = True`
   - set `continuation_start_open_bar_index = t + 1`
   - set `forced_expiry_open_bar_index = (t + 1) + 16`
   - reset `later_trail_signal_count_during_continuation = 0`
8. If `close_t >= trail_stop_t` and `EMA30_t < EMA120_t`, schedule `trend_exit` at open `t+1`.

Important precedence lock:
- If both `close_t < trail_stop_t` and `EMA30_t < EMA120_t` occur on the same bar while in `BASE_LONG`, the **trail-stop continuation decision has priority**, exactly as in the bounded actuator framework. Trend exit is **not** separately scheduled from that bar.

### Logic while `CONTINUATION_LONG`

1. Update `live_peak_close`.
2. Compute the reference `trail_stop_t = live_peak_close_t - 3 * robust_ATR_t` for logging only.
3. If `close_t < trail_stop_t`, increment `later_trail_signal_count_during_continuation` but take **no direct exit action** from the trail itself.
4. Compute `hold_signal_t = EMA12(net_quote_norm_28)_t`.
5. Apply close-time exit checks in this order:
   - If `EMA30_t < EMA120_t`: schedule `trend_exit_during_continuation` at open `t+1`.
   - Else if `hold_signal_t < 0.0`: schedule `guard_exit` at open `t+1`.
   - Else if `(t + 1) == forced_expiry_open_bar_index`: schedule `forced_expiry` at open `t+1`.
   - Else: remain in continuation.

### Continuation semantics

- Continuation always keeps **100%** of the existing long position.
- No recursive rescoring beyond the fixed signal rule above.
- Maximum continuation length is **16 H4 bars** after the scheduled baseline-exit open.
- Allowed continuation end reasons:
  - `guard_exit`
  - `trend_exit_during_continuation`
  - `forced_expiry`

### Accounting and execution

Use the unchanged accounting semantics from the base/winner freeze:
- per-side cost = **12.5 bps**
- full entry at next open: `qty = cash_before / (open_price * (1 + side_cost))`
- full exit at next open: `cash_after = cash_before + qty_before * open_price * (1 - side_cost)`
- no leverage, no partials, no pyramiding

### Summary in one line

This non-ML replacement says:
- **At the first trail-stop event, continue only if quote-side normalized net aggressive flow remains non-negative after EMA12 smoothing; once in continuation, keep holding only while that same smoothed flow stays non-negative, unless price trend exits earlier or the 16-bar horizon expires.**
