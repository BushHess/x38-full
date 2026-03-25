# D1b Measurements — Consolidated Summary for D1c Input

Scope: D1b1–D1b4 were measured under the frozen constitution using warmup for calibration and discovery (2020-01-01 to 2023-06-30 UTC) for measurement only. Holdout and reserve_internal were not used. Historical snapshot remains candidate-mining-only; no clean external OOS claim is made here.

## 1. Price / Momentum Summary

### Strongest measured price and structural channels

| tf   | channel              | spec                |   spread_bps |      t | read                     |
|:-----|:---------------------|:--------------------|-------------:|-------:|:-------------------------|
| 15m  | range_position       | N=42 -> H=48        |       25.702 | 11.242 | strong continuation      |
| 15m  | return_momentum      | N=42 -> H=48        |       15.034 | 10.319 | continuation             |
| 15m  | short mean-reversion | drawdown N=6 -> H=3 |        3.155 |  4.139 | local bounce only        |
| 1h   | range_position       | N=12 -> H=12        |       23.156 |  5.681 | continuation             |
| 1h   | return_momentum      | N=12 -> H=12        |       14.994 |  5.137 | continuation             |
| 4h   | return_momentum      | N=168 -> H=24       |      144.07  |  9.009 | long-memory continuation |
| 4h   | range_position       | N=168 -> H=24       |      120.682 |  5.525 | continuation             |
| 1d   | range_position       | N=24 -> H=24        |      639.97  |  4.627 | slow continuation        |
| 1d   | return_momentum      | N=24 -> H=24        |      506.511 |  4.558 | slow continuation        |

### Price / momentum read
- Dominant structure is **multi-bar continuation**, not next-bar persistence.
- **Range position** is generally cleaner than raw signed return.
- The main true mean-reversion signal is narrow: **15m short-horizon bounce**. Beyond that, drawdown depth mostly behaves as **trend persistence**.
- **Daily UTC-boundary gaps are noise**.

### Price / momentum channels that look weak or mostly noisy
- next-bar sign persistence across all timeframes
- D1 gap direction for intraday forecasting
- higher-timeframe drawdown depth as a generic buy-the-dip channel
- 1h `N=24` and 1h `N=168` raw momentum as standalone continuation cues

## 2. Volatility / Regime Summary

### Strongest measured volatility and regime channels

| tf   | channel                      | spec                            |   spread_bps |      t | read                        |
|:-----|:-----------------------------|:--------------------------------|-------------:|-------:|:----------------------------|
| 15m  | vol-normalized return        | zret_42 -> H=48                 |       36.896 | 15.399 | strong, 4y stable           |
| 15m  | neg-tail rebound             | 1% tail -> H=24                 |      153.925 |  7.057 | contrarian rebound          |
| 15m  | rv level -> direction        | rv_42 high vs low -> H=48       |       20.841 |  4.852 | multi-bar only              |
| 1h   | vol-normalized return        | zret_12 -> H=12                 |       36.915 |  7.777 | strong, 4y stable           |
| 1h   | rv level -> direction        | rv_24 high vs low -> H=24       |       55.214 |  4.949 | multi-bar only              |
| 1h   | crisis rebound               | crisis vs neutral -> H=24       |      194.357 |  5.41  | intraday regime bounce      |
| 4h   | vol-normalized return        | zret_168 -> H=48                |      310.762 |  8.406 | strong pooled; yearly drift |
| 4h   | rv level -> direction        | rv_84 high vs low -> H=48       |      449.113 |  7.915 | strong medium-term skew     |
| 4h   | compression -> magnitude     | compdur N=12 -> H=48            |     1014.92  | 12.239 | expansion state, magnitude  |
| 1d   | rv level -> direction        | rv_24 high vs low -> H=48       |     2208.56  |  6.926 | strong but slower           |
| 1d   | range-vol level -> direction | rangevol_42 high vs low -> H=48 |     1636.15  |  6.173 | strong but slower           |
| 1d   | compression -> magnitude     | compdur N=24 -> H=12            |      847.026 |  8.155 | expansion state, magnitude  |

### Volatility / regime read
- The cleanest result in D1b2 is **future-magnitude state information** from volatility.
- Clean directional volatility signals exist too, mainly on **15m / 1h zret**, **4h realized-vol direction**, and **intraday crisis / downside-tail rebound**.
- **Compression duration** splits the dataset cleanly:
  - `15m / 1h`: longer compression dampens near-term magnitude
  - `4h / 1d`: longer compression precedes magnitude expansion
- `trend vs chop` is weak outside 15m, and daily extreme-state regime labels are the least stationary part of the surface.

### Volatility / regime channels that look weak or mostly noisy
- trend/chop outside 15m
- daily crisis/euphoric labels due sparse coverage
- daily vol-normalized extreme states as a stationarity fix
- simple “first bar after compression release” timing

## 3. Volume / Flow Summary

### Strongest measured volume, flow, and participation channels

| tf   | channel       | spec                |   spread_bps |     t | read                                       |
|:-----|:--------------|:--------------------|-------------:|------:|:-------------------------------------------|
| 15m  | volume state  | zlogv N=24 -> H=24  |          7.3 |  4.29 | weak direction; mainly magnitude elsewhere |
| 15m  | extreme flow  | zflow N=24 -> H=12  |         -4.7 | -3.83 | contrarian intraday                        |
| 15m  | trade density | ztd N=168 -> H=24   |         -6.3 | -3.87 | compression / weaker returns               |
| 1h   | extreme flow  | zflow N=168 -> H=48 |        102.8 | 10.84 | clean directional flow                     |
| 1h   | trade density | ztd N=84 -> H=24    |        -29.6 | -4.53 | compression / weaker returns               |
| 1h   | volume state  | zlogv N=84 -> H=24  |         21.2 |  3.28 | secondary direction                        |
| 4h   | extreme flow  | zflow N=24 -> H=24  |        187.3 |  7.15 | clean directional flow                     |
| 4h   | trade density | ztd N=24 -> H=48    |        -86.2 | -2.38 | compression / weaker returns               |
| 1d   | extreme flow  | zflow N=84 -> H=12  |        633.1 |  5.29 | material but less stationary               |
| 1d   | trade density | ztd N=42 -> H=24    |        667.7 |  3.99 | daily participation continuation           |

### Volume / flow read
- **Volume level** is mainly a **future-magnitude** channel.
- **Extreme standardized taker imbalance** is the clean directional order-flow carrier, especially on **1h** and **4h**.
- **Trade density** is not redundant with volume:
  - intraday it behaves like **compression / weaker future returns or magnitude**
  - daily it flips into **stronger-participation continuation**
- Calendar effects are secondary. The only mild structure is **UTC session timing**.

### Volume / flow channels that look weak or mostly noisy
- raw volume as a direction-only predictor above 1h
- raw buy-dominant vs sell-dominant imbalance as a simple continuation rule
- day-of-week and weekend effects

## 4. Cross-Timeframe Conditioning

### Strongest measured cross-timeframe relationships

| pair     | slow_state                      | fast_channel                   |   permission_bps |   permission_t |   direct_delta_bps |   direct_t |   year_sign_share | read                                                                                            |
|:---------|:--------------------------------|:-------------------------------|-----------------:|---------------:|-------------------:|-----------:|------------------:|:------------------------------------------------------------------------------------------------|
| D1 → 4h  | 1d range_24 above warmup median | 4h flow_extreme_24 (fav=high)  |          282.167 |          8.05  |             71.152 |      4.242 |              0.75 | daily trend does not add much to 4h trend-on-trend, but strongly lifts 4h flow quality          |
| D1 → 4h  | 1d ret_24 > 0                   | 4h flow_extreme_24 (fav=high)  |          236.737 |          6.671 |            134.877 |      8.09  |              0.75 | same pattern as daily range; direct daily drift is real, incremental value appears through flow |
| 4h → 1h  | 4h ret_168 > 0                  | 1h flow_extreme_168 (fav=high) |          147.684 |         11.173 |             80.026 |     13.495 |              1    | strongest cross-TF permission measured; slow trend materially improves faster flow              |
| 4h → 1h  | 4h ret_168 > 0                  | 1h zret_12 (fav=high)          |           46.119 |          7.344 |             27.567 |      9.391 |              1    | slow trend improves normalized 1h continuation as well                                          |
| 1h → 15m | 1h ret_12 > 0                   | 15m range_42 (fav=high)        |           10.413 |          2.375 |             14.38  |      9.91  |              0.5  | 1h positive state lifts unconditional 15m drift, but only modestly improves 15m range timing    |

### Cross-timeframe read
- The cleanest slower→faster permission is **trend conditioning on faster order flow**, not trend conditioning on faster trend.
- **4h trend → 1h flow** is the strongest interaction measured.
- **D1 trend → 4h flow** is also strong and lower-cost.
- **1h trend → 15m** mainly shifts baseline drift; incremental permission on already-fast 15m continuation is modest.

## 5. Redundancy Map

### Highest-correlation pairs among representative carriers

| feature_a   | feature_b   |    rho |
|:------------|:------------|-------:|
| 4h_rv84     | 1d_rv24     |  0.855 |
| 15m_rv42    | 1h_rv24     |  0.849 |
| 15m_zret42  | 1h_zret12   |  0.827 |
| 15m_range42 | 1h_range12  |  0.817 |
| 15m_zret42  | 1h_range12  |  0.802 |
| 1h_range12  | 1h_zret12   |  0.797 |
| 15m_range42 | 15m_zret42  |  0.791 |
| 4h_ret168   | 1d_range24  |  0.756 |
| 1h_vol84    | 1h_trade84  | -0.716 |
| 1d_rv24     | 1d_comp24   | -0.699 |

### Independent carriers that survive consolidation best

| name         |      t |   year_sign_share |   max_abs_rho |
|:-------------|-------:|------------------:|--------------:|
| 15m flow24   |  3.832 |              0.75 |         0.212 |
| 1h flow168   | 10.839 |              1    |         0.352 |
| 4h flow24    |  7.148 |              1    |         0.352 |
| 1d trade42   |  3.985 |              0.75 |         0.425 |
| 1d flow84    |  5.284 |              0.5  |         0.487 |
| 4h trade24   |  2.389 |              1    |         0.497 |
| 15m trade168 |  3.862 |              0.75 |         0.603 |
| 1h trade84   |  4.536 |              1    |         0.716 |

### Redundancy conclusions
- **Neighboring-timeframe price and volatility channels are highly redundant.**
- **Order-flow states are unusually independent across timeframes.**
- The useful interaction terms in D1b4 survive precisely because they combine **weakly correlated** trend and flow clusters:
  - `ρ(4h_ret168, 1h_flow168) = 0.089`
  - `ρ(1d_range24, 4h_flow24) = 0.043`
  - `ρ(4h_ret168, 1h_zret12) = 0.112`
- Daily slow-trend state and 4h long-memory trend state overlap strongly (`ρ = 0.756`), so D1 price-on-4h price adds limited incremental value.
- 15m / 1h fast-trend carriers are strongly overlapping, so they should be treated as **one cluster**, not multiple independent discoveries.

## 6. Strongest Independent Signals Ranked

This is the integrated ranking after consolidating D1b1–D1b4 and discounting redundancy.

|   rank | channel                               | type                 | stat                           | independence                         | cost       | robustness                         |
|-------:|:--------------------------------------|:---------------------|:-------------------------------|:-------------------------------------|:-----------|:-----------------------------------|
|      1 | 4h trend → 1h flow permission         | cross-TF interaction | permission +147.7 bps, t=11.17 | high (ρ[4h_ret168,1h_flow168]=0.089) | medium     | 2020-2023 all positive             |
|      2 | 15m vol-normalized continuation       | base directional     | spread +36.9 bps, t=15.40      | low/moderate (fast trend cluster)    | high       | 2020-2023 all positive             |
|      3 | 1h extreme flow                       | base directional     | spread +102.8 bps, t=10.84     | high (max |ρ|=0.352)                 | medium     | 2020-2023 all positive             |
|      4 | D1 trend → 4h flow permission         | cross-TF interaction | permission +282.2 bps, t=8.05  | high (ρ[1d_range24,4h_flow24]=0.043) | low        | 3/4 years positive                 |
|      5 | 4h long-memory continuation           | base directional     | spread +144.1 bps, t=9.01      | moderate (slow trend cluster)        | low        | 2020-2023 positive                 |
|      6 | 4h trend → 1h normalized continuation | cross-TF interaction | permission +46.1 bps, t=7.34   | high (ρ[4h_ret168,1h_zret12]=0.112)  | medium     | 2020-2023 all positive             |
|      7 | 4h realized-vol directional skew      | base directional     | spread +449.1 bps, t=7.92      | low/moderate (slow vol cluster)      | low        | 2020-2022 positive, 2023 weaker    |
|      8 | 4h extreme flow                       | base directional     | spread +187.3 bps, t=7.15      | high (max |ρ|=0.352)                 | low/medium | 2020-2023 all positive             |
|      9 | 15m downside-tail rebound             | base contrarian      | spread +153.9 bps, t=7.06      | moderate (derived sparse regime)     | high       | 2020-2023 positive, 2023 near flat |
|     10 | 1d trade-density continuation         | base participation   | spread +667.7 bps, t=3.99      | moderate/high (max |ρ|=0.425)        | low        | 3/4 years positive                 |

Additional ranking notes:
- `1h zret_12` is a viable lower-cost proxy inside the same fast-trend cluster as `15m zret_42`, but it is not separately ranked because it does not add much independent information.
- `1d rv_24` and `1d range_24` both remain measurable, but they are demoted by either redundancy (`1d_range24` vs `4h_ret168`) or yearly drift risk (`1d rv_24`, `1d zret` family).
- `4h flow_24` and `1h flow_168` are both worth keeping because they remain relatively independent from price and volatility clusters.

## 7. Measurement Audit Trail

### Step totals

| step   |   raw_tests |
|:-------|------------:|
| D1b1   |         556 |
| D1b2   |        1144 |
| D1b3   |         974 |
| D1b4   |         261 |

### Fine-grained family audit (reconstructed lower-bound count)

| step   | family                   | lookback_or_bins                             |   raw_tests |
|:-------|:-------------------------|:---------------------------------------------|------------:|
| D1b1   | return_autocorr          | 6 lags                                       |          24 |
| D1b1   | return_momentum          | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b1   | range_position           | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b1   | drawdown_depth           | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b1   | rank/adaptive/hysteresis | strongest feature per TF; 4 schemes × 6 H    |          96 |
| D1b1   | gap_behavior             | D1 gap to 4 forward targets                  |           4 |
| D1b2   | vol_clustering           | 4 TF × 4 lag/half-life metrics               |          16 |
| D1b2   | vol_normalized_return    | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b2   | realized_vol_direction   | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b2   | range_vol_direction      | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b2   | realized_vol_magnitude   | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b2   | range_vol_magnitude      | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b2   | compression_duration     | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b2   | trend/chop               | 6 H × 4 TF                                   |          24 |
| D1b2   | crisis_regime            | 6 H × 4 TF                                   |          24 |
| D1b2   | euphoric_regime          | 6 H × 4 TF                                   |          24 |
| D1b2   | tail_direction           | 4 tail cuts × 6 H × 4 TF                     |          96 |
| D1b2   | tail_magnitude           | 4 tail cuts × 6 H × 4 TF                     |          96 |
| D1b3   | volume_direction         | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b3   | volume_magnitude         | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b3   | volume_lead_lag          | 6 lookbacks × 4 TF                           |          24 |
| D1b3   | raw_imbalance_direction  | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b3   | flow_extreme_direction   | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b3   | trade_density_direction  | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b3   | trade_density_magnitude  | 6 lookbacks × 6 H × 4 TF                     |         144 |
| D1b3   | calendar_day_of_week     | 7 bins × 4 TF                                |          28 |
| D1b3   | calendar_time_of_day     | 24/24/6 intraday bins                        |          54 |
| D1b3   | weekend_effect           | 4 TF                                         |           4 |
| D1b4   | cross_tf_permission      | 3 pairings × 2 slow states × 4 fast channels |          24 |
| D1b4   | cross_tf_direct_state    | 3 pairings × 2 slow states                   |           6 |
| D1b4   | redundancy_pairwise_corr | 22 representative carriers => C(22,2)        |         231 |

### Breadth / DOF summary
- Reconstructed **core edge-seeking tests** (D1b1–D1b4, excluding redundancy correlations): **2,704**
- Reconstructed **total statistical comparisons including redundancy correlations**: **2,935**
- Counted **fine-grained families / diagnostics**: **31**
- Representative signal-carrier matrix used for redundancy control: **22** carriers
- Estimated representative-state **effective test count** using an eigenvalue participation-ratio correction: **M_eff ≈ 10.05**

Interpretation:
- The raw search breadth is large.
- The effective dimensionality of the **signal-carrying representatives** is much smaller than the raw grid, but still nontrivial.
- `M_eff ≈ 10.05` should be treated as a **lower bound** on the true full-search DOF because it is based on representative carriers, not every lookback/horizon cell in the upstream grid.

## 8. Consolidated Read for D1c

What looks measurably real after consolidation:
1. **Fast continuation cluster** — strongest raw directional content, but internally redundant and cost-sensitive.
2. **Slow continuation cluster** — materially real, lower-cost, partly redundant with D1 slow trend.
3. **Order-flow cluster** — the cleanest independent directional family.
4. **Volatility state cluster** — strongest for magnitude; directional use survives mainly on 4h and on fast normalized-return states.
5. **Participation / compression cluster** — useful as a state axis; intraday and daily signs differ.
6. **Sparse tail / crisis rebound cluster** — real on intraday data, but event-driven and less frequent.
7. **Cross-timeframe trend × flow interactions** — the strongest incremental structure added by D1b4.

What should be discounted going into D1c:
- duplicate fast-trend proxies across 15m and 1h
- duplicate slow-trend proxies across 4h and 1d
- duplicate volatility proxies across adjacent timeframes
- daily extreme-state results with obvious yearly drift
- calendar effects as primary drivers