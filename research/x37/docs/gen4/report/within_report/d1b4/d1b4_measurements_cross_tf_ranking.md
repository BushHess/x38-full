## Scope

- Data source: admitted historical snapshot only.
- Calibration: warmup through 2019-12-31 UTC.
- Measurement window: discovery 2020-01-01 through 2023-06-30 UTC.
- Holdout and reserve_internal were not used.
- Snapshot remains candidate-mining-only; no clean external OOS claim is made here.
- Gap policy unchanged: rolling and forward calculations were blocked across detected raw-data gaps; no fill or repair was performed.
- Cross-timeframe alignment was causal: slower-TF state was only made available to faster bars after the slower bar had completed.

## 1. Cross-Timeframe Conditioning

Method:
- Representative signal-bearing channels from D1b1–D1b3 were converted into oriented scores, where higher score means more favorable future outcome for that channel's primary role.
- Slower-TF state was standardized on warmup and aligned to faster-TF discovery bars by last completed slower bar.
- Conditioning was measured on faster-TF forward returns using both oriented high-vs-low spread and score-vs-forward-return Spearman correlation.

### 1.1 Adjacent-TF permission / filter effects

| slow_state             | fast_channel        |   all_spread_bp |   slow+_spread_bp |   slow-_spread_bp |   all_t |   slow+_t |   slow-_t |   all_rho |   slow+_rho |   slow-_rho | readout                                                                             |
|:-----------------------|:--------------------|----------------:|------------------:|------------------:|--------:|----------:|----------:|----------:|------------:|------------:|:------------------------------------------------------------------------------------|
| D1 anti-vol            | 4h ret_168          |           613.3 |             901.1 |             309.6 |   12.45 |     12.59 |      4.6  |     0.177 |       0.268 |       0.101 | Daily low-vol state materially strengthens 4h trend.                                |
| D1 trend               | 4h ret_168          |           613.3 |             690.6 |            -168.9 |   12.45 |     11.24 |     -1.84 |     0.177 |       0.188 |       0.003 | Positive D1 trend is a real permission state for 4h trend; low D1 trend kills it.   |
| D1 trend               | 4h rangepos_168     |           400.6 |             481.1 |            -473.5 |    8    |      7.28 |     -5.44 |     0.125 |       0.127 |       0.002 | Same result on range-position proxy; low D1 trend flips the fast edge negative.     |
| 4h trend               | 1h ret_12           |            11.4 |              15.1 |               3.8 |    4.01 |      4.24 |      0.79 |     0.008 |       0.022 |      -0.016 | Positive 4h trend improves 1h fast continuation.                                    |
| 4h trend               | 1h ret_168 reversal |            48.7 |             101.4 |              30.9 |    4.35 |      6.15 |      1.6  |     0.033 |       0.043 |       0.054 | Positive 4h trend also improves the 1h pullback/recovery channel.                   |
| 4h high-vol            | 1h ret_12           |            13.3 |               7.5 |              16.1 |    4.54 |      1.2  |      5.29 |     0.01  |       0     |       0.016 | 4h high-vol is not a permission state for 1h ret_12; low-vol 4h backdrop is better. |
| 1h trend               | 15m ret_42          |            11.6 |               1.4 |               9.4 |    8.56 |      0.61 |      3.84 |     0.008 |       0.01  |       0.004 | Same-direction stacking from 1h into 15m is mostly exhausted.                       |
| 1h long reversal state | 15m ret_42          |            10.1 |              13.3 |               6.1 |    7.16 |      6.24 |      3.28 |     0.005 |       0.008 |       0.002 | 15m continuation works better when 1h is in a recovery/oversold state.              |

Readout:
- **D1 -> 4h**
  - Daily **anti-vol** is the cleanest permission state for 4h trend. The 4h `ret_168` spread improves from **613.3 bp** unconditional to **901.1 bp** when the D1 anti-vol state is favorable, with correlation improving from **0.177** to **0.268**.
  - Daily **trend** is a real directional permission/filter, not cosmetic overlap. Under favorable D1 trend, 4h `ret_168` stays strongly positive (**690.6 bp**, `t=11.24`); under unfavorable D1 trend it flips negative (**-168.9 bp**, `t=-1.84`). The same sign flip appears on 4h `rangepos_168`.
- **4h -> 1h**
  - Positive 4h trend improves 1h fast continuation: `1h ret_12` spread rises from **11.4 bp** to **15.1 bp**, and weakens to **3.8 bp** in unfavorable 4h trend.
  - Positive 4h trend also improves the 1h pullback/recovery channel: `1h ret_168` reversal spread rises from **48.7 bp** to **101.4 bp**.
  - 4h **high-vol** is **not** a generic permission state for faster momentum. On `1h ret_12`, favorable high-vol 4h background weakens the edge to **7.5 bp** vs **16.1 bp** in low-vol 4h background.
- **1h -> 15m**
  - Positive 1h trend does **not** improve `15m ret_42`. The edge drops from **11.6 bp** unconditional to **1.4 bp** in positive 1h trend. Same-direction stacking is mostly exhausted by the time it reaches 15m.
  - `15m ret_42` works better when the 1h backdrop is in a **long-reversal / recovery** state: spread improves from **10.1 bp** to **13.3 bp**.

### 1.2 Flow-channel conditioning (correlation view)

The taker-flow exhaustion family drifted into a mostly one-sided favorable state during discovery relative to warmup calibration, so binary high/low split conditioning is weak. Correlation conditioning is still informative:

| slow_state   | fast_channel        |   all_rho |   slow+_rho |   slow-_rho | readout                                                                                                               |
|:-------------|:--------------------|----------:|------------:|------------:|:----------------------------------------------------------------------------------------------------------------------|
| 4h trend     | 1h flow exhaustion  |     0.07  |       0.118 |       0.003 | 1h flow-exhaustion correlation improves under positive 4h trend and nearly disappears in negative 4h trend.           |
| 1h trend     | 15m flow exhaustion |     0.012 |       0.041 |      -0.019 | 15m flow-exhaustion correlation is usable mainly when 1h trend is positive; it turns adverse under negative 1h trend. |

One-sidedness of the flow-exhaustion block relative to warmup median:

| channel             | tf   |   discovery_pct_above_warmup_median |
|:--------------------|:-----|------------------------------------:|
| D1 flow exhaustion  | 1d   |                              100    |
| 4h flow exhaustion  | 4h   |                              100    |
| 1h flow exhaustion  | 1h   |                               99.57 |
| 15m flow exhaustion | 15m  |                               99.68 |

Interpretation:
- The flow-exhaustion family is a **persistent background block** during discovery, not a clean binary regime switch.
- Lower-TF flow variants mostly behave as descendants of the same slow exhaustion state rather than independent permission filters.

## 2. Redundancy Map

Redundancy was measured two ways:
- **Native-timeframe Spearman correlation** for channels on the same TF.
- **Daily-end aligned Spearman correlation** for cross-TF comparisons.

### 2.1 Highest-redundancy pairs

| channel_a            | channel_b               |   rho | why                                     |
|:---------------------|:------------------------|------:|:----------------------------------------|
| 1h fast continuation | 15m medium continuation | 0.908 | Fast continuation cross-scale duplicate |
| D1 flow exhaustion   | 4h flow exhaustion      | 0.87  | Flow exhaustion cross-scale duplicate   |
| 1h flow exhaustion   | 15m flow exhaustion     | 0.856 | Flow exhaustion cross-scale duplicate   |
| 4h trend             | 4h ret trend            | 0.828 | Same latent 4h trend block              |
| 1h trade surprise    | 15m trade surprise      | 0.704 | Trade surprise / activity overlap       |
| 15m activity         | 1h activity             | 0.645 | Activity cross-scale duplicate          |

### 2.2 Low-overlap pairs among strong channels

| channel_a               | channel_b          |    rho |
|:------------------------|:-------------------|-------:|
| D1 anti-vol             | D1 flow exhaustion | -0.039 |
| D1 anti-vol             | D1 trade surprise  | -0.038 |
| 4h trend                | 4h flow exhaustion | -0.103 |
| 15m medium continuation | 15m activity       | -0.021 |
| D1 trend                | D1 flow exhaustion |  0.156 |
| 4h pro-vol              | 4h trend           | -0.016 |

### 2.3 Family-level redundancy clusters

| cluster                  | representative   | redundant_or_related                          | key_corr                                                                                                                                                   | takeaway                                                                                                                     |
|:-------------------------|:-----------------|:----------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------|
| Slow trend               | h4_trend         | d1_trend, h4_ret                              | rho(h4_trend,h4_ret)=0.828 native 4h; rho(d1_trend,h4_trend)=0.592 daily                                                                                   | Moderate redundancy. Use 4h trend as mid-frequency representative; D1 trend remains useful as slower permission.             |
| Flow exhaustion          | d1_flow          | h4_flow, h1_flow, m15_flow                    | rho(d1_flow,h4_flow)=0.870; rho(h1_flow,m15_flow)=0.856; rho(d1_flow,m15_flow)=0.665 daily                                                                 | High redundancy across scales. One slow representative is enough; lower-TF variants are descendants, not independent blocks. |
| Activity / participation | m15_activity     | h1_activity, h4_activity, h1_trade, m15_trade | rho(m15_activity,h1_activity)=0.645; rho(h1_activity,h4_activity)=0.619; rho(h1_trade,m15_trade)=0.704 daily; rho(m15_trade,m15_activity)=0.664 native 15m | High redundancy inside activity/tape-intensity family. Relative volume is the cleanest representative.                       |
| Fast continuation        | m15_fast         | h1_fast                                       | rho(h1_fast,m15_fast)=0.908 daily                                                                                                                          | Very high redundancy. Keep one representative only.                                                                          |
| Pullback / recovery      | h1_reversal      | m15_rebound                                   | rho(h1_reversal,m15_rebound)=0.180 daily; rho(m15_fast,m15_rebound)=-0.627 native 15m                                                                      | Not redundant with fast continuation; behaves as a complementary phase channel.                                              |
| Trade surprise (slow)    | d1_trade         | h4_trade                                      | rho(d1_trade,h4_trade)=0.540 daily; rho(h4_trade,h1_trade)=-0.639 daily                                                                                    | Slow trade surprise is only moderately redundant and does not collapse cleanly into intraday activity.                       |
| Volatility state         | d1_antivol       | h4_antivol                                    | rho(d1_antivol,h4_antivol)=-0.735 daily                                                                                                                    | Scale-dependent sign flip. Daily low-vol bullish and 4h high-vol bullish are not the same directional block.                 |

Key takeaways:
- **Slow trend** and **flow exhaustion** are two different slow blocks. They are not the same factor.
- **Activity / participation** and **intraday trade surprise** substantially overlap; calendar magnitude mostly sits inside this same activity block rather than forming a separate independent channel.
- **Fast continuation** is a single block across 1h and 15m. Keeping both as independent inputs would double-count the same information.
- **Volatility state changes sign by scale**. Daily anti-vol and 4h pro-vol should not be collapsed into one “volatility channel”; they are scale-specific states with opposite directional meaning.

## 3. Channel Ranking

Ranking criterion:
- predictive content from D1b1–D1b3,
- incremental independence from the redundancy audit,
- cross-timeframe usefulness from this D1b4 conditioning step,
- cost sensitivity proxied by sign-state flips per discovery-year.

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

Interpretation:
- **Most valuable slow directional blocks:** `D1 anti-vol`, `D1 flow exhaustion`, `4h trend`, then `D1 trend`.
- **Most valuable timing / magnitude block:** `15m activity`.
- **Most valuable fast directional block:** `15m ret_42`, but it is phase-sensitive and should not be treated as an always-on continuation channel.
- **Most valuable pullback block:** `1h long reversal`, which strengthens the 15m continuation leg rather than duplicating it.

## 4. Consolidated Summary

This turn changes the integrated picture in four important ways:

1. **The hierarchy is not monotone.**
   - `D1 -> 4h` and `4h -> 1h` show genuine permission/filter effects.
   - `1h -> 15m` does **not** support naive same-direction stacking.

2. **Flow exhaustion is a real slow block, but mostly one-sided during discovery.**
   - It is strong as a standalone state.
   - It is weak as a binary discovery-period regime gate because discovery spent nearly the whole period in the favorable side relative to warmup.

3. **The best independent channel set is smaller than the raw leaderboard.**
   - Many top-t channels are duplicates of the same latent block at different scales.

4. **Magnitude channels and directional channels should not be conflated.**
   - Relative volume / activity is an exceptional timing-magnitude channel.
   - It is not the same object as the slow directional trend, anti-vol, or flow-exhaustion blocks.

No strategies, no backtests, and no candidate proposals were produced in this step.
