## Scope

- Data source: admitted historical snapshot only.
- Calibration: warmup through 2019-12-31 UTC.
- Measurement window: discovery 2020-01-01 through 2023-06-30 UTC.
- Holdout and reserve_internal were not used.
- Snapshot remains candidate-mining-only; no clean external OOS claim is made here.
- D1b1 measured price/momentum.
- D1b2 measured volatility/regime.
- D1b3 measured volume/order-flow/calendar.
- D1b4 measured cross-timeframe conditioning, redundancy, and integrated ranking.

## 1. Key Statistics Per Channel Per Timeframe

### 1.1 Price / Momentum (D1b1)

| timeframe   | channel                                           | measurement                                                        |
|:------------|:--------------------------------------------------|:-------------------------------------------------------------------|
| 15m         | ret_42 -> fwd_42 continuation                     | t=9.23; medium-horizon continuation strongest raw 15m price signal |
| 15m         | drawdown_84 rebound                               | t=5.45; deep local drawdowns tend to recover                       |
| 1h          | ret_12 -> fwd_12 continuation                     | t=5.14; short/medium 1h continuation                               |
| 1h          | ret_168 -> fwd_168 reversal                       | t=-5.65; long 1h lookback is contrarian, not momentum              |
| 4h          | rangepos_168 / ret_168 continuation               | t=12.54 / 12.50; cleanest directional trend block                  |
| 1d          | ret_168 trailing-rank / rangepos_168 continuation | t=10.62 / 10.41; strongest slow trend block                        |

### 1.2 Volatility / Regime (D1b2)

| scope     | channel                                 | measurement                                                                                     |
|:----------|:----------------------------------------|:------------------------------------------------------------------------------------------------|
| All TFs   | volatility clustering                   | abs-return and realized-vol autocorrelation are real; volatility is a state variable            |
| 15m/1h/4h | high vol -> higher near-term magnitude  | magnitude channel dominates direction                                                           |
| 1d        | low daily vol bullish over long horizon | rangevol_84 -> fwd_168: t=-18.06; daily anti-vol is a major slow filter                         |
| 4h        | high 4h vol bullish over long horizon   | rangevol_84 -> fwd_168: t=7.58; sign flips by scale, so daily and 4h vol are not the same block |
| 15m/1h/4h | compression episodes                    | not a generic breakout-release signal; mostly lower immediate future magnitude                  |

### 1.3 Volume / Flow / Calendar (D1b3)

| scope        | channel                 | measurement                                                                            |
|:-------------|:------------------------|:---------------------------------------------------------------------------------------|
| 15m/1h/4h/1d | relative volume         | strong future-magnitude channel; moderate directional effect on 15m/1h                 |
| 1d           | taker_12 long reversal  | t=-15.85; positive taker imbalance is an exhaustion signal, not universal continuation |
| 4h           | taker_168 long reversal | t=-11.86; same exhaustion block as D1                                                  |
| 15m          | taker_168 long reversal | t=-9.97; lower-scale descendant of same flow block                                     |
| 1d           | trade_surprise_168      | t=9.14; slower participation surprise is bullish and partly independent                |
| Calendar     | weekday/hour magnitude  | real but weaker than activity state; mostly not a stand-alone direction edge           |

### 1.4 Cross-timeframe conditioning (D1b4)

| slow_state             | fast_channel        |   all_spread_bp |   slow+_spread_bp |   slow-_spread_bp |   all_t |   slow+_t |   slow-_t | readout                                                                             |
|:-----------------------|:--------------------|----------------:|------------------:|------------------:|--------:|----------:|----------:|:------------------------------------------------------------------------------------|
| D1 anti-vol            | 4h ret_168          |           613.3 |             901.1 |             309.6 |   12.45 |     12.59 |      4.6  | Daily low-vol state materially strengthens 4h trend.                                |
| D1 trend               | 4h ret_168          |           613.3 |             690.6 |            -168.9 |   12.45 |     11.24 |     -1.84 | Positive D1 trend is a real permission state for 4h trend; low D1 trend kills it.   |
| D1 trend               | 4h rangepos_168     |           400.6 |             481.1 |            -473.5 |    8    |      7.28 |     -5.44 | Same result on range-position proxy; low D1 trend flips the fast edge negative.     |
| 4h trend               | 1h ret_12           |            11.4 |              15.1 |               3.8 |    4.01 |      4.24 |      0.79 | Positive 4h trend improves 1h fast continuation.                                    |
| 4h trend               | 1h ret_168 reversal |            48.7 |             101.4 |              30.9 |    4.35 |      6.15 |      1.6  | Positive 4h trend also improves the 1h pullback/recovery channel.                   |
| 4h high-vol            | 1h ret_12           |            13.3 |               7.5 |              16.1 |    4.54 |      1.2  |      5.29 | 4h high-vol is not a permission state for 1h ret_12; low-vol 4h backdrop is better. |
| 1h trend               | 15m ret_42          |            11.6 |               1.4 |               9.4 |    8.56 |      0.61 |      3.84 | Same-direction stacking from 1h into 15m is mostly exhausted.                       |
| 1h long reversal state | 15m ret_42          |            10.1 |              13.3 |               6.1 |    7.16 |      6.24 |      3.28 | 15m continuation works better when 1h is in a recovery/oversold state.              |

## 2. Channels With Measurable Exploitable Signal

Primary signal-bearing families:

1. **Slow trend**
   - Daily long-horizon trend and 4h long-horizon trend are real.
   - 4h is the cleaner mid-frequency representative; D1 is the slower permission/filter.

2. **Slow anti-vol**
   - Daily low-vol state is one of the strongest directional filters in the whole session.
   - It materially strengthens 4h trend.

3. **Flow exhaustion**
   - Positive taker imbalance is not a universal continuation signal.
   - The dominant effect is long-horizon reversal / exhaustion.
   - Cross-scale variants are highly redundant.

4. **Fast continuation**
   - `15m ret_42` and `1h ret_12` both work, but they are highly redundant.
   - The 15m leg is stronger, but more cost-sensitive and phase-dependent.

5. **Pullback / recovery**
   - `1h ret_168` reversal and `15m drawdown` rebound form a complementary recovery block.
   - They are not duplicates of fast continuation.

6. **Activity / participation**
   - Relative volume is the strongest magnitude/timing channel.
   - Trade surprise overlaps with this block intraday, but daily trade surprise remains partly independent.

7. **Volatility state by scale**
   - Daily anti-vol and 4h pro-vol both have directional value, but they are not the same factor.
   - The sign changes by scale.

## 3. Channels That Are Mostly Noise or Low Increment

| item                                        | verdict                  | note                                                                                             |
|:--------------------------------------------|:-------------------------|:-------------------------------------------------------------------------------------------------|
| Daily gaps                                  | Noise                    | BTC spot 24/7; daily open gaps do not predict same-day or next-day direction                     |
| Calendar direction                          | Weak                     | hour/day-of-week direction is weak; magnitude seasonality is the only persistent calendar effect |
| Raw trade residual                          | Invalid without de-drift | must de-drift before measurement                                                                 |
| Universal taker continuation claim          | False                    | taker imbalance flips by horizon and is dominated by long-horizon reversal                       |
| Generic intraday compression breakout claim | False                    | compression mostly lowers immediate future magnitude rather than releasing it                    |
| Blind same-direction stacking 1h -> 15m     | Weak/negative            | positive 1h trend does not improve 15m ret_42; it usually worsens it                             |

Additional low-increment findings from D1b4:
- `1h fast continuation` adds little independent content beyond `15m ret_42` (`rho=0.908` daily-end aligned).
- `4h flow`, `1h flow`, and `15m flow` mostly duplicate the same slow flow-exhaustion block led by D1.
- `1h` and `15m` calendar **direction** is weak. Calendar **magnitude** mostly aliases the activity block:
  - 15m hour-of-day magnitude vs mean relative-volume score: Spearman `rho=0.677`
  - 1h day-of-week magnitude vs mean relative-volume score: Spearman `rho=0.786`

## 4. Redundancy Map Between Channels

### 4.1 Highest-redundancy pairs

| channel_a            | channel_b               |   rho | why                                     |
|:---------------------|:------------------------|------:|:----------------------------------------|
| 1h fast continuation | 15m medium continuation | 0.908 | Fast continuation cross-scale duplicate |
| D1 flow exhaustion   | 4h flow exhaustion      | 0.87  | Flow exhaustion cross-scale duplicate   |
| 1h flow exhaustion   | 15m flow exhaustion     | 0.856 | Flow exhaustion cross-scale duplicate   |
| 4h trend             | 4h ret trend            | 0.828 | Same latent 4h trend block              |
| 1h trade surprise    | 15m trade surprise      | 0.704 | Trade surprise / activity overlap       |
| 15m activity         | 1h activity             | 0.645 | Activity cross-scale duplicate          |

### 4.2 Family-level redundancy map

| cluster                  | representative   | redundant_or_related                          | key_corr                                                                                                                                                   | takeaway                                                                                                                     |
|:-------------------------|:-----------------|:----------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------|
| Slow trend               | h4_trend         | d1_trend, h4_ret                              | rho(h4_trend,h4_ret)=0.828 native 4h; rho(d1_trend,h4_trend)=0.592 daily                                                                                   | Moderate redundancy. Use 4h trend as mid-frequency representative; D1 trend remains useful as slower permission.             |
| Flow exhaustion          | d1_flow          | h4_flow, h1_flow, m15_flow                    | rho(d1_flow,h4_flow)=0.870; rho(h1_flow,m15_flow)=0.856; rho(d1_flow,m15_flow)=0.665 daily                                                                 | High redundancy across scales. One slow representative is enough; lower-TF variants are descendants, not independent blocks. |
| Activity / participation | m15_activity     | h1_activity, h4_activity, h1_trade, m15_trade | rho(m15_activity,h1_activity)=0.645; rho(h1_activity,h4_activity)=0.619; rho(h1_trade,m15_trade)=0.704 daily; rho(m15_trade,m15_activity)=0.664 native 15m | High redundancy inside activity/tape-intensity family. Relative volume is the cleanest representative.                       |
| Fast continuation        | m15_fast         | h1_fast                                       | rho(h1_fast,m15_fast)=0.908 daily                                                                                                                          | Very high redundancy. Keep one representative only.                                                                          |
| Pullback / recovery      | h1_reversal      | m15_rebound                                   | rho(h1_reversal,m15_rebound)=0.180 daily; rho(m15_fast,m15_rebound)=-0.627 native 15m                                                                      | Not redundant with fast continuation; behaves as a complementary phase channel.                                              |
| Trade surprise (slow)    | d1_trade         | h4_trade                                      | rho(d1_trade,h4_trade)=0.540 daily; rho(h4_trade,h1_trade)=-0.639 daily                                                                                    | Slow trade surprise is only moderately redundant and does not collapse cleanly into intraday activity.                       |
| Volatility state         | d1_antivol       | h4_antivol                                    | rho(d1_antivol,h4_antivol)=-0.735 daily                                                                                                                    | Scale-dependent sign flip. Daily low-vol bullish and 4h high-vol bullish are not the same directional block.                 |

### 4.3 Independent strong pairs

| channel_a               | channel_b          |    rho |
|:------------------------|:-------------------|-------:|
| D1 anti-vol             | D1 flow exhaustion | -0.039 |
| D1 anti-vol             | D1 trade surprise  | -0.038 |
| 4h trend                | 4h flow exhaustion | -0.103 |
| 15m medium continuation | 15m activity       | -0.021 |
| D1 trend                | D1 flow exhaustion |  0.156 |
| 4h pro-vol              | 4h trend           | -0.016 |

Integrated redundancy view:
- **Use one representative** for each of these blocks:
  - slow trend
  - flow exhaustion
  - fast continuation
  - activity / participation
- **Keep separate**:
  - daily anti-vol
  - daily trade surprise
  - 1h long reversal / 15m rebound recovery block
- **Treat 4h pro-vol as scale-specific**, not as a duplicate of daily anti-vol.

## 5. Strongest Independent Signals Ranked

|   rank | channel                                                                | role      |   best_t_from_D1b1_3 |   block_same_sign_% |   median_block_abs_rho |   sign_flip_yr | cost     | redundancy                   | cross_tf_note                                                                   |
|-------:|:-----------------------------------------------------------------------|:----------|---------------------:|--------------------:|-----------------------:|---------------:|:---------|:-----------------------------|:--------------------------------------------------------------------------------|
|      1 | D1 anti-vol (low daily range-vol bullish over 168d)                    | direction |                18.06 |                62.5 |                  0.515 |            6.3 | very_low | low                          | Strengthens 4h ret_168 from 613bp to 901bp spread.                              |
|      2 | D1 flow exhaustion (low taker buy ratio bullish over 168d)             | direction |                15.85 |                75   |                  0.565 |            0   | very_low | low                          | Standalone slow block; lower-TF flow signals are mostly descendants.            |
|      3 | 4h trend (rangepos_168 / ret_168 continuation)                         | direction |                12.54 |                87.5 |                  0.146 |           66.7 | low      | moderate                     | Improves 1h ret_12 and 1h long reversal when positive.                          |
|      4 | D1 trend (daily slow trend continuation)                               | direction |                10.62 |                75   |                  0.521 |            9.4 | very_low | moderate                     | Low D1 trend flips 4h trend negative.                                           |
|      5 | 15m activity state (relvol_168 -> next-bar magnitude)                  | magnitude |                43.17 |               100   |                  0.169 |         8695.3 | high     | high_within_activity_cluster | Primary timing/magnitude channel; calendar magnitude mostly aliases this block. |
|      6 | D1 trade surprise (excess trades bullish over 168d)                    | direction |                 9.14 |                62.5 |                  0.45  |           55.2 | low      | moderate                     | Slow participation-surprise block; only partial overlap with trend.             |
|      7 | 15m medium continuation (ret_42)                                       | direction |                 9.23 |                62.5 |                  0.026 |         2907.9 | high     | high_with_h1_fast_only       | Works best when 1h is not already positively extended.                          |
|      8 | 1h long reversal (ret_168 mean-reversion)                              | direction |                 5.65 |                87.5 |                  0.146 |          320.4 | medium   | low_to_moderate              | Strengthens 15m ret_42 when positive; also improved by positive 4h trend.       |
|      9 | 4h pro-vol directional state (high 4h range-vol bullish over 168 bars) | direction |                 7.58 |                75   |                  0.253 |           20.2 | low      | scale_specific               | Hurts 1h ret_12 when high; not a generic permission state for faster momentum.  |
|     10 | 15m deep-drawdown rebound                                              | direction |                 5.45 |                62.5 |                  0.054 |         1775.8 | high     | complementary_to_m15_fast    | Opposite-phase complement to 15m ret_42, not a duplicate.                       |

Practical readout from the ranking:
- The **core slow directional stack** is `D1 anti-vol` + `D1 flow exhaustion` + `4h trend`, with `D1 trend` as slower confirmation rather than a full duplicate.
- The **core fast directional block** is `15m ret_42`, but only with phase awareness; it is not improved by blindly stacking positive 1h trend above it.
- The **core pullback block** is `1h long reversal`, with `15m drawdown rebound` as a complementary lower-TF phase channel.
- The **core timing/magnitude block** is `15m activity`; higher-TF activity variants are mostly redundant.

## 6. Bottom Line For D1c Input

The best integrated measurement picture is:

- **Independent slow filters / states**
  - D1 anti-vol
  - D1 flow exhaustion
  - D1 trend (partially redundant with 4h trend, but still useful as the slower permission layer)

- **Independent directional engine blocks**
  - 4h trend continuation
  - 1h long reversal / recovery
  - 15m medium continuation

- **Independent timing / magnitude block**
  - 15m relative-activity state

- **Blocks to avoid double-counting**
  - multiple flow-exhaustion variants across scale
  - both 1h and 15m fast continuation together without consolidation
  - activity plus calendar magnitude as if they were independent

No strategies, no backtests, and no candidate proposals were produced in D1b.
