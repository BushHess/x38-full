# D1b4 Measurements — Cross-Timeframe, Redundancy & Channel Ranking

Scope: warmup used only for calibration; discovery (2020-01-01 to 2023-06-30 UTC) used for measurement. Holdout and reserve_internal were not used. Historical snapshot remains candidate-mining-only; no clean external OOS claim is made here.

Method notes:
- Cross-timeframe mapping is causal. Slower-timeframe states are projected onto faster bars using the **last fully closed slower bar** only.
- Slow-state conditioning uses `ret > 0` for slower return momentum and the warmup median split for slower range-position unless otherwise stated.
- Faster-channel spreads use warmup-calibrated outer states (20th/80th percentiles) with the favorable side oriented to the previously measured directional sign.
- Redundancy analysis uses a common **15m discovery grid**, causal as-of projection for slower states, and **Spearman** correlation on 22 representative signal carriers from D1b1–D1b3.
- Sparse derivative labels (crisis/euphoric/tail events) are discussed qualitatively as derived projections of return/volatility states; they are not used as primary continuous carriers in the linear redundancy matrix.

## 1. Cross-Timeframe Conditioning

### Strongest measured conditioning relationships

| pair     | slow_state                      | fast_channel                   |   H_fast |   direct_delta_bps |   direct_t |   overall_spread_bps |   cond_pos_bps |   cond_neg_bps |   permission_bps |   permission_t |   year_sign_share |
|:---------|:--------------------------------|:-------------------------------|---------:|-------------------:|-----------:|---------------------:|---------------:|---------------:|-----------------:|---------------:|------------------:|
| D1 → 4h  | 1d range_24 above warmup median | 4h flow_extreme_24 (fav=high)  |       24 |             71.152 |      4.242 |              187.492 |        314.219 |         33.371 |          282.167 |          8.05  |              0.75 |
| D1 → 4h  | 1d ret_24 > 0                   | 4h flow_extreme_24 (fav=high)  |       24 |            134.877 |      8.09  |              187.492 |        239.395 |        135.196 |          236.737 |          6.671 |              0.75 |
| 4h → 1h  | 4h ret_168 > 0                  | 1h flow_extreme_168 (fav=high) |       48 |             80.026 |     13.495 |              102.872 |        139.589 |         48.847 |          147.684 |         11.173 |              1    |
| 4h → 1h  | 4h ret_168 > 0                  | 1h zret_12 (fav=high)          |       12 |             27.567 |      9.391 |               36.965 |         44.583 |         17.807 |           46.119 |          7.344 |              1    |
| 1h → 15m | 1h ret_12 > 0                   | 15m range_42 (fav=high)        |       48 |             14.38  |      9.91  |               22.464 |          4.123 |         18.287 |           10.413 |          2.375 |              0.5  |

Interpretation:
- **D1 → 4h**: daily trend state improves unconditional 4h forward drift, but its cleanest incremental value is **not** in 4h trend-on-trend stacking. It shows up by **conditioning 4h order flow**. Daily range and daily return both lift 4h flow quality materially.
- **4h → 1h**: this is the strongest cross-timeframe structure measured. Positive 4h long-memory trend materially improves both **1h flow** and **1h vol-normalized continuation**.
- **1h → 15m**: slower 1h trend state lifts unconditional 15m forward returns, but it only **modestly** improves the already-fast 15m continuation channel. Incremental permission is weak and year-unstable relative to the slower-pair results.

### What did *not* add much incremental value
- **D1 price → 4h price** is mostly redundant. Daily price states already overlap heavily with 4h price extremes, so incremental permission on 4h price-on-price is limited and sometimes undefined because the “daily negative + 4h extreme positive” cell is sparse.
- **1h price → 15m price** is weaker than expected. 15m fast-trend extremes are often already “too extended”; 1h positivity lifts baseline drift but does not reliably improve those fast extremes.

## 2. Redundancy Map

### Top redundant pairs among representative carriers

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

### Most independent carriers among signal-bearing representatives

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

### Redundancy clusters
1. **Fast trend cluster**: `15m_range42`, `15m_zret42`, `1h_range12`, `1h_zret12`  
   These are strongly collinear (`ρ ≈ 0.79–0.83`). They are multiple views of the same fast continuation state.

2. **Fast volatility cluster**: `15m_rv42`, `1h_rv24`  
   Strong overlap (`ρ = 0.849`).

3. **Slow trend cluster**: `4h_ret168`, `1d_range24`  
   Strong overlap (`ρ = 0.756`). Daily slow-trend information is partly absorbed by 4h long-memory price state.

4. **Slow volatility cluster**: `4h_rv84`, `1d_rv24`  
   Strong overlap (`ρ = 0.855`).

5. **Order-flow states remain unusually independent across scales**:  
   `ρ(15m_flow24, 1h_flow168) = -0.025`, `ρ(1h_flow168, 4h_flow24) = 0.352`, `ρ(4h_flow24, 1d_flow84) = -0.011`.  
   This is the main reason cross-timeframe **trend × flow** interactions survive consolidation.

6. **Participation / compression states are mixed rather than collinear**:  
   `ρ(1h_vol84, 1h_trade84) = -0.716`, but higher-timeframe compression-duration states are only moderately linked (`ρ(4h_comp12, 1d_comp24) = 0.456`).

### Independence takeaways
- The **most redundant** carriers are neighboring-timeframe price and volatility channels.
- The **most independent** carriers are order-flow states, especially `1h_flow168`, `4h_flow24`, and `15m_flow24`.
- Cross-timeframe gains appear when combining **weakly correlated clusters** rather than stacking within the same cluster.

## 3. Channel Ranking

The ranking below is ordered by measured strength, incremental independence, cost sensitivity, and regime robustness. It is a ranking of **channels**, not strategy rules.

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

Ranking notes:
- `15m zret_42` is the single strongest raw directional carrier, but it sits inside a heavily redundant fast-trend cluster and is cost-sensitive.
- `1h flow_extreme_168` is weaker in raw t-stat than `15m zret_42` but far more independent, and it combines exceptionally well with slower-trend permission.
- The two strongest interaction channels are **4h trend → 1h flow** and **D1 trend → 4h flow**; both work because their component carriers are nearly orthogonal in the redundancy map.
- Daily slow-trend and daily volatility channels remain usable but are less attractive after consolidation because of either redundancy (`1d_range24`, `1d_rv24`) or weaker stationarity (`1d_flow84`).

## 4. Consolidation Read

Net result of D1b4:
- The snapshot does **not** support a large menu of independent edges. It supports a **small number of clusters**:
  - fast continuation cluster
  - slow continuation cluster
  - volatility state cluster
  - order-flow cluster
  - participation/compression cluster
  - sparse contrarian tail/rebound cluster
- The cleanest incremental information after redundancy control comes from **order flow** and from **cross-timeframe trend × flow conditioning**.
- The weakest incremental area is **trend-on-trend stacking across adjacent timeframes**; most of that is redundant.