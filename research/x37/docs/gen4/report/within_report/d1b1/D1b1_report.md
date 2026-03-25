# D1b1 Report — Measurements: Price & Momentum

## 1. Return & Momentum Channels

Full per-timeframe, per-lookback tables are in the report. Headline measurements:

| Timeframe | Strongest raw return channel | Result |
|---|---|---|
| 15m | ret_42 → fwd_42 | continuation, t = 9.23, spread +12.57 bp |
| 1h | ret_12 → fwd_12 | continuation, t = 5.14, spread +14.99 bp |
| 1h | ret_168 → fwd_168 | reversal, t = -5.65, spread -64.30 bp |
| 4h | ret_168 → fwd_168 | continuation, t = 12.50, spread +615.20 bp |
| 1d | ret_168 → fwd_168 | continuation, t = 10.77, spread +5798.60 bp |

**What matters:**

- **15m** has a clear two-regime shape: short-horizon reversal first, then stronger medium-horizon continuation.
  - strongest reversal pocket: `ret_6 → fwd_6`, t = -3.42
  - strongest continuation pocket: `ret_42 → fwd_42`, t = 9.23
- **1h** is mixed, not cleanly monotone.
  - shorter channel: `ret_12 → fwd_12`, continuation
  - long channel: `ret_168 → fwd_168`, reversal
- **4h** is the cleanest raw momentum frame. Predictive content generally strengthens as forward horizon lengthens.
- **1d** is also strongly continuation-dominated, but the effect only becomes large at longer forward horizons; H≤12 is weak, H≈42–168 is where signal turns on.

**Return autocorrelation** of 1-bar returns is small overall, but the biggest negative pockets are:

- 15m lag 2: -0.0527
- 1h lag 24: -0.0362
- 4h lag 6: -0.0641
- 1d lag 1: -0.0806

That supports the short-horizon reversal pockets, but autocorrelation alone is weaker than the conditional forward-return measurements.

## 2. Structural Features

Strongest structural findings:

| Channel | Strongest measurement | Result |
|---|---|---|
| Range position | 4h rangepos_168 → fwd_168 | t = 12.54 |
| Range position | 1d rangepos_168 → fwd_168 | t = 10.41 |
| Return rank | 1d ret_168 trailing-rank extremes → fwd_168 | t = 10.62 |
| Drawdown | 15m dd_84 → fwd_84 | rebound, t = 5.45 |
| Drawdown | 4h dd_168 → fwd_168 | near-high continuation, t = -5.88 |

**Key readouts:**

- **Range position** is one of the cleanest channels in the whole scan. Across all four timeframes, being near the rolling high outperforms being near the rolling low.
- **Percentile rank** helps on drifting long-horizon channels.
  - 4h ret_168: raw Pearson 0.0550 → trailing-rank Pearson 0.0755
  - 1d ret_168: raw Pearson -0.0080 → trailing-rank Pearson 0.3610
- **Trailing vs expanding calibration** is mixed, not universal.
  - trailing is clearly better on 4h/1d long-horizon trend channels
  - expanding is acceptable on shorter 15m/1h channels
  - on 1h ret_168, structure is unstable: raw sign-split says reversal, but some ranked/extreme transforms flip sign. That is measurable, but not a clean monotone state variable
- **Hysteresis**
  - 15m ret_42: useful; flips cut 50.0%, spread retained 102.2%
  - 1h ret_12: useful but weaker; flips cut 32.6%, spread retained 78.0%
  - 1h ret_168: flips cut 62.5%, but spread retained only 67.5%
  - 4h ret_168: not useful in this construction
  - 1d ret_168: very useful; flips cut 80.0%, spread retained 112.5%

## 3. Mean-Reversion & Gaps

Strongest measured reversal channels:

| Timeframe | Past N | Forward H | Result |
|---|---|---|---|
| 1h | 168 | 168 | reversal, t = -5.65, spread -64.30 bp |
| 15m | 6 | 6 | reversal, t = -3.42 |
| 15m | 6 | 3 | reversal, t = -3.07 |
| 15m | 12 | 12 | reversal, t = -2.54 |
| 15m | 24 | 12 | reversal, t = -2.42 |

**Interpretation:**

- The dominant reversal channel is 1h same-horizon long-lookback reversal.
- There is a real micro-reversion pocket on 15m, mostly in N=6–24 feeding into H=2–12.
- Outside those pockets, the snapshot is more continuation-heavy than reversal-heavy.

**Daily gap behavior:**

- D1 gap mean: -0.046 bp
- median gap: 0.0 bp
- max absolute gap: 18.97 bp
- corr(gap, same-day return): 0.0105
- corr(gap, next-day return): -0.0137
- same-day positive-gap vs negative-gap spread: +12.12 bp, t = 0.44
- next-day spread: -17.62 bp, t = -0.63

**Verdict on gaps:** noise. BTC spot is 24/7; daily opens are not a meaningful session boundary here.

## 4. Price/Momentum Channel Summary

Strongest robust channels ranked by predictive content:

1. 4h rangepos_168 → fwd_168, t = 12.54
2. 4h ret_168 → fwd_168, t = 12.50
3. 1d ret_168 → fwd_168, t = 10.77
4. 1d ret_168 trailing-rank extremes → fwd_168, t = 10.62
5. 1d rangepos_168 → fwd_168, t = 10.41
6. 1d ret_84 → fwd_168, t = 10.20
7. 4h ret_168 trailing-rank extremes → fwd_168, t = 9.89
8. 15m ret_42 → fwd_42, t = 9.23
9. 4h rangepos_84 → fwd_168, t = 8.52
10. 15m ret_42 trailing-rank extremes → fwd_42, t = 7.65

**Bottom line:**

- **Cleanest long-horizon continuation:** 4h and 1d price channels, especially long-lookback returns and range position.
- **Cleanest medium-horizon continuation:** 15m ret_42 and 15m range position.
- **Cleanest mean-reversion:** 1h ret_168 → fwd_168, plus 15m short-horizon reversal / deep-drawdown rebound.
- **Noise / weak:** D1 gap behavior, 4h hysteresis in this construction, and any attempt to treat 1h ret_168 as a simple monotone momentum variable.

**Constraint reminder:** this remains candidate-mining-only measurement on the historical snapshot. No clean external OOS claim is made here.
