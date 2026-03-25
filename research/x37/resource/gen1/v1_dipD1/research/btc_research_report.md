# BTC Spot Long-Only Discovery Report

Prepared from the attached research protocol and BTC/USDT H4 + D1 data.

## Phase 0 — locked protocol

- Warmup only: 2017-08-17 to 2018-12-31.
- Development: 2019-01-01 to 2023-12-31.
- Final untouched holdout: 2024-01-01 to 2026-02-20.
- Extra data after 2026-02-20 was intentionally ignored.
- Walk-forward on development: six anchored folds with 6-month unseen test windows:
  1. 2021-H1
  2. 2021-H2
  3. 2022-H1
  4. 2022-H2
  5. 2023-H1
  6. 2023-H2
- Metrics: CAGR, Sharpe, MDD, Calmar, trades, exposure, win rate, profit factor, trade distribution.
- Bootstrap: circular daily block bootstrap with block sizes 10 / 20 / 40 days; block=20 primary.
- Plateau test: +/-20% perturbation on each tunable parameter around the selected setting.
- Complexity budget: max 4 tunables, no pyramiding, no partial sizing, no path-dependent stack of filters.

## Data quality

- D1: complete from 2017-08-17 to 2026-02-20.
- H4: 17 missing bars in the raw archive; most are pre-development, with a few gaps in 2019-2020. Data was kept as-is; no synthetic bars were inserted.

## Phase 1 — data decomposition

### Summary by information channel

| Channel                          | Measured OOS fact                                                                                                             | Decay / horizon                                | Cost sensitivity                               | Regime note                                              | Redundancy                                                       |
|:---------------------------------|:------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------|:-----------------------------------------------|:---------------------------------------------------------|:-----------------------------------------------------------------|
| Raw H4/D1 autocorrelation        | 1-bar autocorr near zero/negative; no stable simple autocorr edge                                                             | N/A                                            | N/A                                            | Not a standalone tradable edge                           | High with noise                                                  |
| H4 persistence / drift state     | dist_mean_48 and eff_24 work as selective long states; WFV Sharpe ~1.02-1.03 standalone                                       | ~12 H4 bars                                    | Moderate; survives 20 bps but turnover matters | Breaks in 2022                                           | Partly overlaps with daily drift                                 |
| Daily drift / trend state        | d1_dist_mean_21 standalone WFV Sharpe ~0.96; positive but regime-sensitive                                                    | Multi-day state                                | Good due lower turnover                        | Bear-rally vulnerability if used alone                   | Useful gate for lower-TF timing                                  |
| H4 pullback alone                | Bottom-quantile 24h pullback alone is not enough; negative CAGR when traded standalone                                        | Mean reversion over 12-24 H4 bars              | Poor alone because high exposure / churn       | Needs context                                            | Complementary only when conditioned on drift                     |
| Cross-timeframe drift + pullback | Strongest composite: d1 trend high AND h4 pullback low -> +2.46% 24-bar conditional edge vs unconditional, 5/6 positive folds | Best around 18-29 H4 bars, center chosen at 24 | Strong; remains positive at 40 bps RT          | Flat rather than collapsing in 2022; positive in holdout | Non-redundant interaction; gate and timing both earn their place |
| Volatility level / expansion     | High ATR / RV sometimes helps, but unstable as standalone filter                                                              | Longer horizons (12-24 H4 bars)                | Mixed                                          | Acts more like horizon modulator than primary driver     | Largely absorbed by pullback timing                              |
| Volume / order-flow              | Flow spikes show sparse conditional edge, but adding flow filters usually reduces robustness                                  | Sparse 12-24 H4 effects                        | Fragile because sample is thin                 | Unstable across folds                                    | Mostly redundant/noisy after price state                         |
| Seasonality                      | Hour/day/month effects are weak or spurious OOS                                                                               | N/A                                            | N/A                                            | Not reliable                                             | Not useful                                                       |

## Phase 2 — candidate hypotheses

| Hypothesis                          | What it exploits                                                                                        | Why it may persist                                                                        | Failure mode                                                     | Falsification                                                                                          |
|:------------------------------------|:--------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------|:-----------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------|
| Persistence state continuation      | Directional follow-through when the H4 path is efficient and far enough above its recent mean           | Crypto trend bursts can persist when order flow stays one-sided                           | Choppy bear / reflexive mean reversion                           | If best state candidate goes materially negative in 2024-2026 or collapses under small lookback shifts |
| Trend-conditioned pullback re-entry | Short counter-trend weakness inside strong daily drift tends to mean-revert back into the dominant move | Trend participants re-add on dips; long-only spot avoids fighting structural upside drift | Gate becomes stale and pullbacks turn into genuine regime breaks | If pullback-alone is equally good, or if adding the gate does not improve OOS stability                |
| Breakout continuation               | Fresh local highs inside positive daily drift should continue                                           | Delayed participation and stop-driven continuation                                        | Exhaustion breakouts and crowded trend entries                   | If breakout family underperforms pullback family OOS or becomes highly cost-sensitive                  |
| Flow-backed thrust                  | Buy-imbalance and trade activity spikes should identify informed directional pressure                   | Large aggressive buyers can fragment entry over several bars                              | Noise spikes and news shocks                                     | If flow filters reduce OOS Sharpe / fold stability versus price-only rules                             |

## Phase 3 — minimal system designs evaluated

Serious candidate families taken to full development walk-forward and final holdout:

1. **A_persistence** — long while H4 efficiency + H4 distance-from-mean are both in favorable state.
2. **B2_pullback** — long on H4 pullback inside strong daily drift, then fixed-time exit.
3. **B4_sparse_pullback** — stricter daily-return gate plus local-range pullback, slower and sparser.
4. **D_breakout** — local breakout inside positive daily drift, fixed short hold.

## Development walk-forward comparison (unseen only)

| candidate          |   Sharpe |   CAGR |     MDD |   Trades |   WinRate |   ProfitFactor |   pos_fold_sharpe_frac |   pos_fold_cagr_frac |   worst_fold_sharpe |   worst_fold_cagr |
|:-------------------|---------:|-------:|--------:|---------:|----------:|---------------:|-----------------------:|---------------------:|--------------------:|------------------:|
| A_persistence      |   1.1233 | 0.2462 | -0.2105 |       70 |    0.3571 |         2.0106 |                 0.6667 |               0.6667 |             -1.8771 |           -0.2139 |
| B2_pullback        |   1.171  | 0.2754 | -0.1994 |       29 |    0.7241 |         2.9953 |                 0.8333 |               0.6667 |             -0.092  |           -0.0088 |
| B4_sparse_pullback |   0.8512 | 0.1782 | -0.2663 |       28 |    0.5357 |         2.3594 |                 0.8333 |               0.8333 |              0.1158 |            0      |
| D_breakout         |   1.0894 | 0.1702 | -0.1723 |       44 |    0.5    |         2.052  |                 0.6667 |               0.6667 |             -1.446  |           -0.0422 |

### Walk-forward fold details for B2

|   fold | test_start   | test_end   |        CAGR |     Sharpe |        MDD |   TradesEst |   Exposure |
|-------:|:-------------|:-----------|------------:|-----------:|-----------:|------------:|-----------:|
|      1 | 2021-01-01   | 2021-06-30 |  0.195628   |  0.626468  | -0.199436  |         7.5 |  0.156682  |
|      2 | 2021-07-01   | 2021-12-31 |  1.09412    |  3.02443   | -0.0589939 |         8   |  0.174071  |
|      3 | 2022-01-01   | 2022-06-30 | -0.00875129 | -0.0920242 | -0.0450498 |         2   |  0.0442396 |
|      4 | 2022-07-01   | 2022-12-31 | -0.0025229  |  0.0400087 | -0.0813398 |         2   |  0.0435177 |
|      5 | 2023-01-01   | 2023-06-30 |  0.636491   |  2.313     | -0.0422956 |         6   |  0.132719  |
|      6 | 2023-07-01   | 2023-12-31 |  0.0614083  |  0.925556  | -0.030886  |         3   |  0.0652765 |

## Why B2 was selected before touching holdout

- It was the strongest trade-off between growth and regime hardness.
- The worst unseen fold was nearly flat rather than a clear collapse.
- Pullback-alone failed; gate-alone worked but was materially weaker in 2022; the interaction was the edge.
- H4-only gate variants were weaker than daily-gate variants, which showed the higher-timeframe information was not redundant.

## Phase 4 — plateau and sensitivity

### +/-20% parameter plateau around B2 center

Chosen center:
- Daily gate lookback = 21
- Pullback lookback = 6
- Hold = 24 bars

Plateau summary:

|                         |    value |
|:------------------------|---------:|
| center_sharpe           | 1.17098  |
| center_cagr             | 0.275438 |
| median_neighbor_sharpe  | 0.996605 |
| median_neighbor_cagr    | 0.256413 |
| all_27_positive_overall | 1        |

Quantile sensitivity around the center (not used for selection, only robustness stress test):

|   q_gate |   q_pull |   Sharpe |      CAGR |   worst_fold_cagr |
|---------:|---------:|---------:|----------:|------------------:|
|     0.8  |     0.85 | 1.30456  | 0.310929  |       -0.140633   |
|     0.85 |     0.85 | 1.22809  | 0.273539  |       -0.061299   |
|     0.8  |     0.8  | 1.17098  | 0.275438  |       -0.00875129 |
|     0.85 |     0.75 | 1.03088  | 0.228728  |       -0.0814449  |
|     0.85 |     0.8  | 1.01268  | 0.214441  |       -0.0814449  |
|     0.8  |     0.75 | 0.891416 | 0.215666  |       -0.134322   |
|     0.75 |     0.85 | 0.867389 | 0.194666  |       -0.203209   |
|     0.75 |     0.8  | 0.561661 | 0.116169  |       -0.341903   |
|     0.75 |     0.75 | 0.482257 | 0.0980012 |       -0.241754   |

Interpretation:
- The region is broad, not a sharp spike.
- Nearby 19/24/29-bar holds remain positive overall.
- `q=0.80 / 0.80` was not the top-return setting, but it was the most balanced on fold stability.

## Phase 5 — frozen final specification

**Final selected candidate (frozen before holdout): B2_pullback**

- Primary execution timeframe: H4.
- Higher-timeframe gate: latest completed D1 `dist_mean_21 = close / SMA21 - 1`.
- Gate threshold: top 20% of **development-period** distribution, fixed before holdout.
  - Frozen numeric threshold: `d1_dist_mean_21 >= 0.078973`.
- Pullback trigger: H4 6-bar return `ret_6 = close / close.shift(6) - 1`.
- Pullback threshold: bottom 20% of **development-period** distribution, fixed before holdout.
  - Frozen numeric threshold: `ret_6 <= -0.018024`.
- Entry: if flat and both gate + pullback are true at H4 close, enter long at next H4 open.
- Exit: fixed time stop after 24 H4 bars (4 days). No overlapping positions.
- No gate-persistence requirement after entry.
- Position sizing: 100% long / 0% flat.
- Trading cost: 10 bps per side, 20 bps round-trip.
- Warmup: 365 days, no trading before live evaluation.
- Data after 2026-02-20 was quarantined and not used.

## Final untouched holdout results

| candidate          |   Sharpe |   CAGR |     MDD |   Trades |   WinRate |   ProfitFactor |   Exposure |   MedianHoldDays |
|:-------------------|---------:|-------:|--------:|---------:|----------:|---------------:|-----------:|-----------------:|
| A_persistence      |   0.5562 | 0.0857 | -0.2301 |       53 |    0.2642 |         1.5895 |     0.1006 |           0.5    |
| B2_pullback        |   1.2717 | 0.1639 | -0.0861 |       14 |    0.7857 |         5.5417 |     0.0716 |           4.1667 |
| B4_sparse_pullback |   0.8028 | 0.1095 | -0.2001 |       13 |    0.3846 |         2.2282 |     0.0569 |           3.1667 |
| D_breakout         |   0.4602 | 0.0478 | -0.1072 |       29 |    0.4483 |         1.4541 |     0.0371 |           1.1667 |

## Full-sample descriptive context (2019-2026, fixed thresholds)

| candidate          |   Sharpe |   CAGR |     MDD |   Trades |   WinRate |   ProfitFactor |   Exposure |   MedianHoldDays |
|:-------------------|---------:|-------:|--------:|---------:|----------:|---------------:|-----------:|-----------------:|
| A_persistence      |   0.8747 | 0.2169 | -0.3358 |      211 |    0.2701 |         1.7758 |     0.1328 |           0.6667 |
| B2_pullback        |   1.3447 | 0.3606 | -0.3527 |       87 |    0.6897 |         3.1874 |     0.1335 |           4.1667 |
| B4_sparse_pullback |   0.9626 | 0.2108 | -0.2967 |       79 |    0.557  |         2.4739 |     0.1068 |           4.1667 |
| D_breakout         |   0.3556 | 0.0475 | -0.346  |      143 |    0.4615 |         1.2341 |     0.0549 |           1.1667 |

## Ablation — does each module earn its place?

| variant            |    CAGR |   Sharpe |     MDD |   Exposure |   TradesEst |
|:-------------------|--------:|---------:|--------:|-----------:|------------:|
| Full B2            |  0.2754 |   1.171  | -0.1994 |     0.1027 |        28.5 |
| Gate only state    |  0.252  |   0.9569 | -0.224  |     0.137  |        24.5 |
| Pullback only      | -0.0449 |   0.1845 | -0.6209 |     0.6249 |       171.5 |
| H4 gate + pullback |  0.1417 |   0.7098 | -0.251  |     0.0698 |        19.5 |
| Breakout alt       |  0.1702 |   1.0894 | -0.1723 |     0.0402 |        44   |

Interpretation:
- **Pullback-only** is not a valid system. It overtrades and loses regime discipline.
- **Gate-only** has real edge, but it takes too much 2022 pain.
- **B2 full interaction** improves both Sharpe and regime stability versus gate-only.
- **H4 gate + pullback** is inferior to **daily gate + pullback**.
- **Breakout** is tradable, but weaker and less consistent than pullback timing.

## Bootstrap robustness

B2 bootstrap summaries (daily block bootstrap, 2000 resamples):

### Walk-forward development (concatenated unseen)
- Block 10: median Sharpe 1.189, median CAGR 0.272, P(Sharpe>0) 0.982
- Block 20: median Sharpe 1.167, median CAGR 0.268, P(Sharpe>0) 0.985
- Block 40: median Sharpe 1.179, median CAGR 0.268, P(Sharpe>0) 0.995

### Full sample (descriptive)
- Block 10: median Sharpe 1.356, median CAGR 0.364, P(Sharpe>0) 1.000
- Block 20: median Sharpe 1.343, median CAGR 0.357, P(Sharpe>0) 1.000
- Block 40: median Sharpe 1.343, median CAGR 0.353, P(Sharpe>0) 1.000

### Holdout only
- Block 10: median Sharpe 1.269, median CAGR 0.156, P(Sharpe>0) 0.976
- Block 20: median Sharpe 1.247, median CAGR 0.150, P(Sharpe>0) 0.981
- Block 40: median Sharpe 1.246, median CAGR 0.148, P(Sharpe>0) 0.989

## Regime breakdown

| epoch        |        CAGR |       Sharpe |        MDD |   Trades |
|:-------------|------------:|-------------:|-----------:|---------:|
| 2019-2020    |  0.718005   |   1.78748    | -0.267622  |       38 |
| 2021         |  0.623925   |   1.40918    | -0.352743  |       21 |
| 2022         | -0.00561638 |  -0.00655173 | -0.0813398 |        4 |
| 2023         |  0.366339   |   1.95971    | -0.0422956 |       11 |
| 2024-2026-02 |  0.163903   |   1.27168    | -0.08612   |       14 |
| 2024         |  0.301849   |   1.56111    | -0.08612   |       10 |
| 2025         |  0.0625522  |   1.60286    | -0.0175291 |        4 |
| 2026-YTD     |  0          | nan          |  0         |        0 |

Key point: B2 did **not** show a major historical collapse. 2022 was roughly flat rather than catastrophic, and the final holdout stayed clearly positive.

## Cost sensitivity for B2

| scope   |   roundtrip_bps |     CAGR |   Sharpe |        MDD |   Trades |
|:--------|----------------:|---------:|---------:|-----------:|---------:|
| full    |               0 | 0.394178 |  1.44087 | -0.346877  |       87 |
| holdout |               0 | 0.179194 |  1.3697  | -0.0852835 |       14 |
| full    |              10 | 0.377305 |  1.39285 | -0.349816  |       87 |
| holdout |              10 | 0.171526 |  1.32095 | -0.0852835 |       14 |
| full    |              20 | 0.360628 |  1.34468 | -0.352743  |       87 |
| holdout |              20 | 0.163903 |  1.27168 | -0.08612   |       14 |
| full    |              30 | 0.344145 |  1.29637 | -0.355658  |       87 |
| holdout |              30 | 0.156327 |  1.22193 | -0.0870358 |       14 |
| full    |              40 | 0.327853 |  1.24794 | -0.358561  |       87 |
| holdout |              40 | 0.148796 |  1.17171 | -0.0879512 |       14 |

The edge remains positive even at 40 bps round-trip.

## Benchmark comparison

| System                   | Scope                            |   Sharpe |   CAGR |     MDD |   Trades |   Bootstrap_median_Sharpe |   Bootstrap_median_CAGR |   P_Sharpe_gt_0 | Notes                                                             |
|:-------------------------|:---------------------------------|---------:|-------:|--------:|---------:|--------------------------:|------------------------:|----------------:|:------------------------------------------------------------------|
| E5+EMA21D1               | Provided benchmark               |   1.638  | 0.728  | -0.385  |      186 |                   0.766   |                0.244    |           0.968 | Robustness leader in prompt context                               |
| V4                       | Provided benchmark               |   1.83   | 0.804  | -0.336  |      196 |                   0.733   |                0.217    |           0.966 | Best full-sample variant; fragile in 2025+ per prompt             |
| V3                       | Provided comparator              |   1.533  | 0.578  | -0.373  |      211 |                   0.516   |                0.122    |           0.894 | Diagnostic comparator only                                        |
| B2 pullback (this study) | Fixed-rule full sample 2019-2026 |   1.3447 | 0.3606 | -0.3527 |       87 |                   1.34311 |                0.356792 |           1     | Daily-block bootstrap; method may differ from benchmark bootstrap |

Important note:
- The benchmark bootstrap numbers were provided as headlines only.
- My bootstrap protocol was locked independently and may not be identical to the undisclosed benchmark bootstrap construction.
- Therefore bootstrap comparison is **directionally informative**, not a perfect apples-to-apples contest.

## Verdict

**COMPETITIVE**

Reason:
- B2 passes the hard acceptance criteria under the locked protocol.
- It is strong on unseen development walk-forward and positive on the untouched holdout.
- It is regime-hardened relative to the pure persistence and breakout families.
- It is simpler and more cost-resilient than the weaker alternatives tested here.
- However, it does **not** clearly beat the frontier benchmarks on full-sample Sharpe or CAGR, and the benchmark bootstrap method is not fully specified. That is not enough to justify `SUPERIOR`.

## Files produced

- Charts:
  - `b2_equity_full.png`
  - `b2_drawdown_full.png`
  - `b2_walkforward_dev.png`
  - `b2_bootstrap_sharpe_full.png`
  - `regime_breakdown_candidates.png`
  - `cost_sensitivity_candidates.png`
  - `b2_plateau_hold.png`
  - `b2_fold_cagr.png`
- Tables:
  - `dev_candidate_comparison.csv`
  - `holdout_candidate_results.csv`
  - `fullsample_candidate_results.csv`
  - `benchmark_comparison.csv`
  - `b2_wfv_folds.csv`
  - `b2_plateau_grid.csv`
  - `b2_cost_sensitivity.csv`
  - `regime_breakdown.csv`
  - `bootstrap_summary.csv`
