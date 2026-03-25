# D1c - Candidate Design & Config Matrix

Design only. No backtests, no scoring, no ranking, no champion/challenger selection.  
Inputs used: `research_constitution_v2.0.yaml` and `d1b_measurements.md`.  
Holdout and reserve_internal were not used. The historical snapshot remains candidate-mining-only.

## Design Gate from D1b

Only primitives with measured structure were promoted into designs:

- **Use**: D1 permission states (`close > EMA`, positive ROC, upper-range close position), H4 drawdown/pullback depth, H4 compression combo, 1h short-consolidation/range breakout, and 1h participation confirmation.
- **Do not promote as primary drivers**: standalone 1h reclaim-above-anchor and standalone taker-buy imbalance; D1b measured them as weak or inconsistent.
- **15m not used in seed candidates**: D1b did not justify elevating 15m beyond optional execution refinement, and the constitution places it outside the main decision hierarchy.

## Archetype A Candidates

### Candidate: `A_D1EMA_H4STATE_DD`

**Measured motivation from D1b**

- D1 `close > EMA50` showed the cleanest permission lift: about **+1.87pp** at 10D and **+3.21pp** at 20D versus off-state.
- D1 permissive state materially improved H4 alignment: `D1 close > EMA50` lifted `H4 close > EMA21` frequency by about **+24.29pp**.
- H4 drawdown recovery was strongly depth-dependent, so a drawdown cap is justified as a state-deterioration control.

**Archetype**

- `A_slow_trend_state`

**Layers**

1. **D1 permission layer**
   - `d1_perm_on(t) := D1_close(t*) > EMA(D1_close, d1_perm_ema_len)[t*]`
   - `t*` = most recent completed D1 bar available at the evaluation time.

2. **H4 state layer**
   - `h4_state_on(t) := H4_close(t) > EMA(H4_close, h4_state_ema_len)[t]`
   - `h4_dd_ok(t) := DD_rollhigh(t, h4_dd_ref_bars) >= -h4_max_dd_pct`
   - `DD_rollhigh(t, L) := H4_close(t) / max(H4_high[t-L+1:t]) - 1`

**Signal logic**

- **Entry**
  - Evaluate on each completed H4 bar close.
  - If flat and `d1_perm_on(t)` and `h4_state_on(t)` and `h4_dd_ok(t)`, signal long.
  - Fill at the **next H4 bar open**.

- **Exit**
  - Evaluate on each completed H4 bar close.
  - If long and any of the following is true, signal flat:
    - `d1_perm_on(t)` is false
    - `h4_state_on(t)` is false
    - `h4_dd_ok(t)` is false
  - Fill at the **next H4 bar open**.

**Tunable quantities**

| name | type | range |
|---|---|---|
| `d1_perm_ema_len` | integer | {50, 100} |
| `h4_state_ema_len` | integer | {21, 34} |
| `h4_dd_ref_bars` | integer | {42, 126} |
| `h4_max_dd_pct` | decimal | {0.08, 0.10} |

**Fixed quantities**

- Symbol: `BTCUSDT`
- Timezone: `UTC`
- Long-only, binary exposure: `0%` or `100%` notional
- No 1h entry layer for this candidate
- No leverage, no pyramiding, no discretionary overrides
- Higher-timeframe alignment always uses the latest **completed** D1 bar at each H4 decision point

**Execution semantics**

- Signal computed at **H4 bar close**
- Order assumed filled at **next H4 bar open**

**Config IDs**

- `A001` to `A016`

## Archetype B Candidates

### Candidate: `B_D1RNG_H4PB_1HBRK`

**Measured motivation from D1b**

- D1 upper-range state (`close_pos100_upper`) showed strong own-state lift, about **+2.08pp** at 10D and **+3.53pp** at 20D versus off-state.
- H4 pullback depth had clear structure: recovery time rose sharply once drawdown moved from shallow to moderate/deep buckets.
- 1h **short-consolidation breakout** had measurable follow-through; generic 1h reclaim-above-anchor was materially weaker.
- Participation confirmation improved breakout quality; standalone taker imbalance did not.

**Archetype**

- `B_pullback_continuation`

**Layers**

1. **D1 permission layer**
   - `d1_closepos100(t*) := (D1_close(t*) - rolling_low_100(t*)) / (rolling_high_100(t*) - rolling_low_100(t*))`
   - `d1_perm_on(t) := d1_closepos100(t*) >= d1_closepos100_thresh`

2. **H4 pullback layer**
   - `dd_h4(t, L) := H4_close(t) / max(H4_high[t-L+1:t]) - 1`
   - `h4_pullback_on(t) := -h4_pullback_max_pct <= dd_h4(t, h4_dd_ref_bars) <= -h4_pullback_min_pct`

3. **1h timing layer**
   - `breakout_level_1h(t) := max(H1_high[t-h1_breakout_lookback:t-1])`
   - `volume_ratio24(t) := H1_volume(t) / median(H1_volume[t-24:t-1])`
   - `trades_ratio24(t) := H1_num_trades(t) / median(H1_num_trades[t-24:t-1])`
   - `participation_on(t) := volume_ratio24(t) > warmup_q75(volume_ratio24) AND trades_ratio24(t) > warmup_q75(trades_ratio24)`
   - `h1_timing_on(t) := H1_close(t) > breakout_level_1h(t) AND participation_on(t)`

**Signal logic**

- **Entry**
  - Evaluate on each completed 1h bar close using the latest completed parent H4 bar and the latest completed D1 bar.
  - If flat and `d1_perm_on(t)` and `h4_pullback_on(parent_h4_t)` and `h1_timing_on(t)`, signal long.
  - Store `entry_breakout_level := breakout_level_1h(t)`.
  - Fill at the **next 1h bar open**.

- **Exit**
  - Evaluate on each completed 1h bar close.
  - If long and any of the following is true, signal flat:
    - `d1_perm_on(t)` is false
    - `dd_h4(parent_h4_t, h4_dd_ref_bars) < -(h4_pullback_max_pct + 0.02)`
    - `H1_close(t) < entry_breakout_level`
  - Fill at the **next 1h bar open**.

**Tunable quantities**

| name | type | range |
|---|---|---|
| `d1_closepos100_thresh` | decimal | {0.70, 0.80} |
| `h4_dd_ref_bars` | integer | {21, 42} |
| `h4_pullback_min_pct` | decimal | {0.02, 0.03} |
| `h4_pullback_max_pct` | decimal | {0.08, 0.10} |

**Fixed quantities**

- Symbol: `BTCUSDT`
- Timezone: `UTC`
- `h1_breakout_lookback = 8` completed 1h bars
- Participation threshold = warmup **75th percentile** on both `volume_ratio24` and `trades_ratio24`
- Pullback zone is defined from rolling H4 highs only; no synthetic bar repair, no intrabar lookahead
- No standalone taker-flow gate; D1b showed it was too weak as a primary directional signal

**Execution semantics**

- Signal computed at **1h bar close**
- Order assumed filled at **next 1h bar open**

**Config IDs**

- `B001` to `B016`

## Archetype C Candidates

### Candidate: `C_D1ROC_H4CMP_1HBRK`

**Measured motivation from D1b**

- Positive D1 ROC had measurable forward-return lift and improved H4 breakout quality.
- The strongest observed interaction in D1b was **H4 compression -> 1h breakout follow-through**.
  - Baseline 1h 24-bar breakout mean follow-through: about **0.34%** over the next 24h
  - After H4 compression combo: about **0.91%**
  - After H4 compression + high participation: about **0.97%**
- Taker flow alone was not strong enough to carry the entry layer, so participation is volume/trades based.

**Archetype**

- `C_compression_breakout`

**Layers**

1. **D1 permission layer**
   - `d1_perm_on(t) := ROC(D1_close, d1_roc_lookback_days)[t*] > 0`

2. **H4 compression layer**
   - `atr_rel(t) := ATR14(H4)[t] / H4_close(t)`
   - `range_comp12(t) := (max(H4_high[t-11:t]) - min(H4_low[t-11:t])) / H4_close(t)`
   - `body_comp12(t) := median(abs(H4_close - H4_open) / H4_close over bars t-11:t)`
   - `h4_compression_on(t) :=`
     - `atr_rel(t) <= warmup_quantile(atr_rel, h4_compression_q)` **and**
     - `range_comp12(t) <= warmup_quantile(range_comp12, h4_compression_q)` **and**
     - `body_comp12(t) <= warmup_quantile(body_comp12, h4_compression_q)`

3. **1h breakout layer**
   - `breakout_level_1h(t) := max(H1_high[t-24:t-1])`
   - `volume_ratio24(t) := H1_volume(t) / median(H1_volume[t-24:t-1])`
   - `trades_ratio24(t) := H1_num_trades(t) / median(H1_num_trades[t-24:t-1])`
   - `participation_on(t) := volume_ratio24(t) > warmup_quantile(volume_ratio24, h1_participation_q) AND trades_ratio24(t) > warmup_quantile(trades_ratio24, h1_participation_q)`
   - `h1_breakout_on(t) := H1_close(t) > breakout_level_1h(t) AND participation_on(t)`

**Signal logic**

- **Entry**
  - Evaluate on each completed 1h bar close using the latest completed parent H4 bar and the latest completed D1 bar.
  - If flat and `d1_perm_on(t)` and `h4_compression_on(parent_h4_t)` and `h1_breakout_on(t)`, signal long.
  - Store:
    - `entry_breakout_level := breakout_level_1h(t)`
    - `entry_h4_compression_floor := min(H4_low[parent_h4_t-11:parent_h4_t])`
  - Fill at the **next 1h bar open**.

- **Exit**
  - Evaluate on each completed 1h bar close.
  - If long and any of the following is true, signal flat:
    - `d1_perm_on(t)` is false
    - `H1_close(t) < entry_breakout_level`
    - latest completed `H4_close(parent_h4_t) < entry_h4_compression_floor`
  - Fill at the **next 1h bar open**.

**Tunable quantities**

| name | type | range |
|---|---|---|
| `d1_roc_lookback_days` | integer | {50, 100} |
| `h4_compression_q` | decimal quantile | {0.15, 0.20} |
| `h1_participation_q` | decimal quantile | {0.75, 0.85} |

**Fixed quantities**

- Symbol: `BTCUSDT`
- Timezone: `UTC`
- `H4` compression range/body window fixed at **12** bars, matching the D1b measurement proxy
- `H1` breakout lookback fixed at **24** completed 1h bars, matching the D1b measurement proxy
- ATR length fixed at **14**
- No taker-flow-only trigger
- No leverage, no pyramiding, no discretionary overrides

**Execution semantics**

- Signal computed at **1h bar close**
- Order assumed filled at **next 1h bar open**

**Config IDs**

- `C001` to `C008`

## Config Matrix Summary

| archetype   | candidate_id        |   configs |   layers |   tunables |
|:------------|:--------------------|----------:|---------:|-----------:|
| A           | A_D1EMA_H4STATE_DD  |        16 |        2 |          4 |
| B           | B_D1RNG_H4PB_1HBRK  |        16 |        3 |          4 |
| C           | C_D1ROC_H4CMP_1HBRK |         8 |        3 |          3 |

Total configs across all archetypes: **40**

## Hard Cap Compliance Check

| cap                                                    | observed                                          | status   |
|:-------------------------------------------------------|:--------------------------------------------------|:---------|
| max_candidates_after_seed <= 3                         | 3 designed                                        | PASS     |
| max_challengers_after_seed <= 2                        | not selected in D1c; design universe capped at 3  | PASS     |
| max_logical_layers_per_candidate <= 3                  | A=2, B=3, C=3                                     | PASS     |
| max_tunable_quantities_per_candidate <= 4              | A=4, B=4, C=3                                     | PASS     |
| max_discovery_configs_per_archetype <= 20              | A=16, B=16, C=8                                   | PASS     |
| max_total_seed_configs <= 60                           | 40                                                | PASS     |
| allowed primitives only                                | all layers mapped to admitted D1/H4/1h primitives | PASS     |
| execution = signal at bar close, fill at next bar open | used for all candidates                           | PASS     |
| UTC alignment / no lookahead                           | latest completed higher-timeframe bar only        | PASS     |
