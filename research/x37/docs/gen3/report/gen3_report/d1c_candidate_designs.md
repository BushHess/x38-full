# D1c Candidate Designs & Config Matrix

Scope: candidate design only. No backtests, no scoring, no ranking selection. Designs are derived from D1b discovery measurements only. Holdout and reserve_internal are not used. Historical snapshot remains candidate-mining-only; no clean external OOS claim is made here.

## Candidate 1 — H4Trend_H1Flow

**D1b justification**

- D1b4 strongest cross-timeframe interaction: 4h ret_168 > 0 conditioning 1h extreme flow_168, permission lift +147.7 bps, t=11.17, 2020–2023 all positive.
- D1b3 strongest independent flow carrier on 1h: extreme standardized flow N=168 -> H=48, +102.8 bps, t=10.84.
- D1b4 redundancy map shows weak correlation between 4h trend and 1h flow (ρ≈0.089), so the interaction is not a duplicate of a single cluster.

**Mechanism description**: Exploit the measured tendency for strong 1h buy-side flow to continue only when the slower 4h state is already trend-positive. The slow trend bar acts as permission; the fast flow bar acts as the state trigger.

**What market behavior it exploits / why it may persist**: Higher-timeframe positive drift reflects persistent directional inventory pressure. Within that state, extreme 1h taker-buy participation is more likely to represent genuine initiative continuation rather than exhaustion.

**What should cause it to fail**: Fails if 1h flow extremes become exhaustion signals even inside positive 4h trend, or if 4h trend permission stops improving the base 1h flow channel.

**Observable falsification evidence**: Falsified if, in walk-forward, the conditional high-vs-low 1h flow spread inside positive 4h trend collapses toward zero/negative, or if ablation shows the 4h permission layer adds no material utility over standalone 1h flow after costs.

**Timeframes used**: 4h slow permission; 1h execution

**Feature formulas**
- On 1h bar \(u\), define the last admissible completed 4h bar as \(s(u)=\max\{j: close\_time^{4h}_j < close\_time^{1h}_u\}\).
- \(\text{trend4h}_{168}(s)=\frac{close^{4h}_s}{close^{4h}_{s-168}}-1\).
- \(\text{imb}^{1h}_u = 2\cdot \frac{taker\_buy\_base\_vol^{1h}_u}{volume^{1h}_u}-1\), with \(\text{imb}^{1h}_u = 0\) when \(volume^{1h}_u=0\).
- \(\text{flow1h}_{168}(u)=\frac{1}{168}\sum_{i=0}^{167}\text{imb}^{1h}_{u-i}\).
- \(\text{flowRank1h}(u)=\widehat F^{train}_{1h}(\text{flow1h}_{168}(u))\), the empirical percentile rank of the current 1h flow carrier against the fold training distribution only.

**Signal logic**
- Entry condition: at 1h bar close, go long for next 1h open if trend4h_168(s(u)) > 0 and flowRank1h(u) >= q_flow_entry.
- Hold condition: if already long, stay long while trend4h_168(s(u)) > 0 and flowRank1h(u) >= q_flow_hold.
- Exit condition: if long and either trend4h_168(s(u)) <= 0 or flowRank1h(u) < q_flow_hold, exit at next 1h open.
- Flat until all required lookback history exists.

**Calibration method**: Fold-static quantile calibration on the 1h flow carrier. In each quarterly-expanding walk-forward fold, estimate the empirical CDF of flow1h_168 from the fold training slice only. Use q_flow_entry and q_flow_hold as percentile cutoffs. The 4h trend threshold is fixed at zero and is not tuned.

**Tunable quantities**
| name | type | range | note |
|---|---|---|---|
| q_flow_entry | float | {0.80, 0.85, 0.90} | Entry percentile for 1h flowRank |
| q_flow_hold | float | {0.60, 0.70} | Lower hold percentile for hysteresis; must satisfy q_flow_hold < q_flow_entry |

**Fixed quantities**
| fixed quantity | value |
|---|---|
| slow trend lookback | 168 4h bars |
| fast flow lookback | 168 1h bars |
| slow threshold | 0.0 on trend4h_168 |
| position size | binary 0% / 100% |
| calendar / session filters | none |
| stop / target overlays | none |

**Layer count**: 2

**Execution semantics**: Evaluate on completed 1h bar close; fill at next 1h open; UTC only; no leverage; no pyramiding; no shorting; no use of incomplete 4h bars.

**Config count**: 6

---

## Candidate 2 — D1Range_H4Flow

**D1b justification**

- D1b4 second-strongest cross-timeframe interaction: daily range_24 state conditioning 4h extreme flow_24, permission lift +282.2 bps, t=8.05.
- D1b1 daily range position is cleaner than raw daily return; D1 best stationarity scheme was expanding calibration.
- D1b3 4h extreme flow N=24 -> H=24 is a strong directional carrier, +187.3 bps, t=7.15.

**Mechanism description**: Exploit the measured tendency for 4h positive order-flow extremes to work best when the daily market is already near the upper portion of its rolling range. The daily range state supplies low-frequency permission; the 4h flow extreme is the execution state.

**What market behavior it exploits / why it may persist**: Daily near-high positioning reflects broad market acceptance of higher prices. In that environment, 4h aggressive buy participation is more likely to represent continuation rather than failed breakout pressure.

**What should cause it to fail**: Fails if daily range position no longer improves 4h flow quality, or if daily near-high state starts marking exhaustion rather than continuation.

**Observable falsification evidence**: Falsified if daily-permitted 4h flow loses its conditional spread in walk-forward, or if ablation shows removing the daily permission leaves equal or better utility after costs.

**Timeframes used**: 1d slow permission; 4h execution

**Feature formulas**
- On 4h bar \(f\), define the last admissible completed daily bar as \(d(f)=\max\{j: close\_time^{1d}_j < close\_time^{4h}_f\}\).
- \(\text{rangePos1d}_{24}(d)=\frac{close^{1d}_d-\min(low^{1d}_{d-23:d})}{\max(high^{1d}_{d-23:d})-\min(low^{1d}_{d-23:d})}\), with value 0.5 if the denominator is 0.
- \(\text{rangeRank1d}(d)=\widehat F^{expand}_{1d}(\text{rangePos1d}_{24}(d))\), the expanding empirical percentile rank over prior completed daily bars only.
- \(\text{imb}^{4h}_f = 2\cdot \frac{taker\_buy\_base\_vol^{4h}_f}{volume^{4h}_f}-1\), with \(\text{imb}^{4h}_f = 0\) when \(volume^{4h}_f=0\).
- \(\text{flow4h}_{24}(f)=\frac{1}{24}\sum_{i=0}^{23}\text{imb}^{4h}_{f-i}\).
- \(\text{flowRank4h}(f)=\widehat F^{train}_{4h}(\text{flow4h}_{24}(f))\), the empirical percentile rank of the 4h flow carrier against the fold training distribution only.

**Signal logic**
- Entry condition: at 4h bar close, go long for next 4h open if rangeRank1d(d(f)) >= q_day_perm and flowRank4h(f) >= q_flow_entry.
- Hold condition: if already long, stay long while rangeRank1d(d(f)) >= q_day_perm and flowRank4h(f) >= q_flow_hold.
- Exit condition: if long and either rangeRank1d(d(f)) < q_day_perm or flowRank4h(f) < q_flow_hold, exit at next 4h open.
- Flat until all required lookback history exists.

**Calibration method**: Daily permission is calibrated with an expanding empirical CDF because D1b found expanding thresholds cleaner on the daily price/range surface. The 4h flow carrier uses fold-static quantile calibration on the current walk-forward training slice only. Hysteresis is implemented through q_flow_entry > q_flow_hold.

**Tunable quantities**
| name | type | range | note |
|---|---|---|---|
| q_day_perm | float | {0.50, 0.60} | Minimum expanding percentile rank on daily range position |
| q_flow_entry | float | {0.80, 0.90} | Entry percentile for 4h flowRank |
| q_flow_hold | float | {0.60, 0.70} | Lower hold percentile for hysteresis; must satisfy q_flow_hold < q_flow_entry |

**Fixed quantities**
| fixed quantity | value |
|---|---|
| daily range lookback | 24 daily bars |
| 4h flow lookback | 24 4h bars |
| position size | binary 0% / 100% |
| calendar / session filters | none |
| stop / target overlays | none |

**Layer count**: 2

**Execution semantics**: Evaluate on completed 4h bar close; fill at next 4h open; UTC only; no leverage; no pyramiding; no shorting; no use of incomplete daily bars.

**Config count**: 8

---

## Candidate 3 — M15ZRetTrail

**D1b justification**

- D1b2 strongest fast continuation carrier: 15m zret_42 -> H=48, +36.9 bps, t=15.40, 2020–2023 all positive.
- D1b1 on 15m the best stationarity scheme for the strongest price feature was trailing_365d, and hysteresis reduced flip rate by ~54.5%.
- D1b4 ranks fast vol-normalized continuation as the representative fast-trend carrier after redundancy discounting.

**Mechanism description**: Exploit persistent short-horizon continuation in volatility-normalized 15m returns. The carrier is a standardized multi-bar move; the trigger is an adaptive trailing rank with hysteresis to reduce churn.

**What market behavior it exploits / why it may persist**: BTC intraday continuation appears in bursts rather than through next-bar autocorrelation. Volatility normalization stabilizes the move size across heteroskedastic episodes, while trailing rank adapts to distribution drift.

**What should cause it to fail**: Fails if the fast continuation cluster becomes too cost-sensitive, or if vol-normalized extremes stop discriminating future returns after adaptive calibration.

**Observable falsification evidence**: Falsified if the high-vs-low trailing-ranked zret state loses positive spread in walk-forward, or if hysteresis no longer lowers churn without damaging utility at 20–50 bps costs.

**Timeframes used**: 15m only

**Feature formulas**
- \(\ell r^{15m}_t = \log(close^{15m}_t / close^{15m}_{t-1})\).
- \(\text{rv15m}_{42}(t)=\text{std}(\ell r^{15m}_{t-41:t})\).
- \(\text{zret15m}_{42}(t)=\frac{\log(close^{15m}_t/close^{15m}_{t-42})}{\text{rv15m}_{42}(t)\cdot \sqrt{42}}\), with value 0 when \(\text{rv15m}_{42}(t)=0\).
- \(\text{zRank15m}(t)=\widehat F^{trail365d}_{15m}(\text{zret15m}_{42}(t))\), the empirical percentile rank of the current zret against the prior 365 calendar days of completed 15m bars only.

**Signal logic**
- Entry condition: at 15m bar close, go long for next 15m open if zRank15m(t) >= q_zret_entry.
- Hold condition: if already long, stay long while zRank15m(t) >= q_zret_hold.
- Exit condition: if long and zRank15m(t) < q_zret_hold, exit at next 15m open.
- Flat until all required lookback and calibration history exists.

**Calibration method**: Trailing 365-day adaptive percentile calibration on the 15m zret carrier, using only prior completed 15m bars. Hysteresis is implemented through q_zret_entry > q_zret_hold, directly matching the D1b finding that adaptive thresholds and hysteresis materially stabilize the 15m fast-trend surface.

**Tunable quantities**
| name | type | range | note |
|---|---|---|---|
| q_zret_entry | float | {0.80, 0.85, 0.90} | Entry percentile for trailing zRank15m |
| q_zret_hold | float | {0.60, 0.70} | Lower hold percentile for hysteresis; must satisfy q_zret_hold < q_zret_entry |

**Fixed quantities**
| fixed quantity | value |
|---|---|
| zret lookback | 42 15m bars |
| trailing calibration window | 365 calendar days |
| position size | binary 0% / 100% |
| calendar / session filters | none |
| stop / target overlays | none |

**Layer count**: 1

**Execution semantics**: Evaluate on completed 15m bar close; fill at next 15m open; UTC only; no leverage; no pyramiding; no shorting.

**Config count**: 6

---

## Config Matrix Summary

| candidate_id | configs | logical_layers | tunables |
|---|---:|---:|---:|
| H4Trend_H1Flow | 6 | 2 | 2 |
| D1Range_H4Flow | 8 | 2 | 3 |
| M15ZRetTrail | 6 | 1 | 2 |
| **Total** | **20** |  |  |

## Hard Cap Compliance Check

| cap | result | detail |
|---|---|---|
| max candidates after seed ≤ 3 | PASS | 3 candidates designed |
| max challengers after seed ≤ 2 | PASS | design stage only; structure allows 1 champion + up to 2 challengers later |
| H4Trend_H1Flow: logical layers ≤ 3 | PASS | 2 layers |
| H4Trend_H1Flow: tunables ≤ 4 | PASS | 2 tunables |
| H4Trend_H1Flow: configs ≤ 20 | PASS | 6 configs |
| D1Range_H4Flow: logical layers ≤ 3 | PASS | 2 layers |
| D1Range_H4Flow: tunables ≤ 4 | PASS | 3 tunables |
| D1Range_H4Flow: configs ≤ 20 | PASS | 8 configs |
| M15ZRetTrail: logical layers ≤ 3 | PASS | 1 layer |
| M15ZRetTrail: tunables ≤ 4 | PASS | 2 tunables |
| M15ZRetTrail: configs ≤ 20 | PASS | 6 configs |
| total seed configs ≤ 60 | PASS | 20 total configs |
| position sizing binary 0% / 100% | PASS | all candidates are long-flat binary exposure only |
| leverage / pyramiding / discretionary overrides | PASS | none used |
| admitted data surface only | PASS | close, high, low, volume, taker_buy_base_vol only |
| no incomplete higher-timeframe lookahead | PASS | all slow permissions use latest closed slow bar with strict slow.close_time < fast.close_time |
| no use of holdout or reserve_internal | PASS | design sourced from D1b discovery measurements only |

## Design Rationale

1. The matrix is intentionally small. D1b already consumed broad search bandwidth; D1c therefore stays local around the strongest measured carriers instead of reopening a wide grid.
2. Two candidates are cross-timeframe **trend × flow** mechanisms because D1b4 showed that those interactions added the clearest incremental signal beyond single-cluster effects.
3. The third candidate is a single-timeframe **fast continuation** representative because D1b ranked the 15m vol-normalized continuation cluster as the strongest raw directional surface after consolidation.
4. Standalone versions of 1h flow-only, 4h long-memory trend-only, or daily volatility-only were not promoted to separate candidates because they would spend candidate slots on channels already embedded inside the chosen mechanisms or on surfaces with more visible drift / redundancy.
5. Hysteresis is included only where D1b gave a concrete reason to include it: it materially reduced flip rate on the fast price surface, and it is the smallest defensible way to keep the flow-triggered candidates from collapsing into one-bar threshold crossing logic.
6. No stops, targets, calendar filters, or additional volume filters were added because D1b did not show enough incremental evidence to justify another layer or another tunable quantity.

## Files

- `d1c_candidate_designs.md`
- `d1c_config_matrix.csv`
