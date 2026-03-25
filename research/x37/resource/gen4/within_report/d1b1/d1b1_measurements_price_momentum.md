## Scope

- Data source: admitted historical snapshot only.
- Calibration: warmup through 2019-12-31 UTC.
- Measurement window: discovery 2020-01-01 through 2023-06-30 UTC.
- Holdout and reserve_internal were not used.
- Snapshot remains candidate-mining-only; no clean external OOS claim is made here.

## Return & Momentum Channels

### Return-channel summary

| Timeframe   |   Lookback_N |   NextBarPersist_% |   BestFwd_H |   BestSpread_bp |   Best_t |   BestCorr |   BestPersist_% | Direction    | DecayComment            |
|:------------|-------------:|-------------------:|------------:|----------------:|---------:|-----------:|----------------:|:-------------|:------------------------|
| 15m         |            6 |              46.69 |          84 |            8.87 |     4.52 |    -0.0008 |           49.26 | continuation | persists through scan   |
| 15m         |           12 |              47.32 |          84 |           14.55 |     7.41 |     0.0063 |           49.61 | continuation | persists through scan   |
| 15m         |           24 |              47.91 |          84 |           11.74 |     5.98 |     0.0023 |           48.86 | continuation | persists through scan   |
| 15m         |           42 |              48.75 |          42 |           12.57 |     9.23 |     0.0457 |           48.93 | continuation | persists through scan   |
| 15m         |           84 |              49.22 |          12 |            5.14 |     6.8  |     0.0064 |           48.37 | continuation | persists through scan   |
| 15m         |          168 |              49.74 |          42 |           10.12 |     7.32 |     0.0078 |           49.06 | continuation | persists through scan   |
| 1d          |            6 |              46.91 |          84 |          823.45 |     2.9  |     0.0995 |           51.61 | continuation | persists through scan   |
| 1d          |           12 |              49.18 |          84 |         1256.63 |     4.57 |     0.1401 |           51.37 | continuation | persists through scan   |
| 1d          |           24 |              49.1  |          84 |         1603.22 |     5.89 |     0.1807 |           53.95 | continuation | persists through scan   |
| 1d          |           42 |              50.43 |          84 |          825.41 |     2.95 |     0.2187 |           53.41 | continuation | below |t|<1 after H=168 |
| 1d          |           84 |              50.67 |         168 |         5196    |    10.2  |     0.0058 |           50.04 | continuation | persists through scan   |
| 1d          |          168 |              49.49 |         168 |         5798.6  |    10.77 |    -0.008  |           55.44 | continuation | persists through scan   |
| 1h          |            6 |              46.37 |          12 |            9.46 |     3.25 |     0.0233 |           48.99 | continuation | persists through scan   |
| 1h          |           12 |              47.57 |          12 |           14.99 |     5.14 |     0.0499 |           49.24 | continuation | persists through scan   |
| 1h          |           24 |              47.79 |         168 |           51.63 |     4.46 |     0.0176 |           48.96 | continuation | persists through scan   |
| 1h          |           42 |              49.14 |          84 |           36.97 |     4.63 |     0.0328 |           48.64 | continuation | persists through scan   |
| 1h          |           84 |              49.61 |          84 |           38.46 |     4.79 |     0.0544 |           48.45 | continuation | below |t|<1 after H=168 |
| 1h          |          168 |              50.03 |         168 |          -64.3  |    -5.65 |    -0.0511 |           46.58 | reversal     | persists through scan   |
| 4h          |            6 |              46.54 |         168 |          184.76 |     3.7  |     0.0304 |           52.49 | continuation | persists through scan   |
| 4h          |           12 |              48.14 |          84 |          167.1  |     5.04 |     0.0513 |           51.73 | continuation | persists through scan   |
| 4h          |           24 |              49.29 |          84 |          134.5  |     4.06 |     0.0729 |           50.96 | continuation | persists through scan   |
| 4h          |           42 |              49.86 |         168 |          159.4  |     3.17 |     0.0811 |           53.5  | continuation | persists through scan   |
| 4h          |           84 |              50.26 |         168 |          307.16 |     6.17 |     0.1113 |           53.68 | continuation | persists through scan   |
| 4h          |          168 |              51.3  |         168 |          615.2  |    12.5  |     0.1769 |           52.66 | continuation | persists through scan   |

### Return autocorrelation of 1-bar returns (discovery only)

| Timeframe   |   MaxAbsLag |   Autocorr |     Lag1 |     Lag2 |     Lag3 |     Lag6 |    Lag12 |    Lag24 |    Lag42 |
|:------------|------------:|-----------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| 15m         |           2 |   -0.05273 |  0.00094 | -0.05273 |  0.00913 | -0.00743 |  0.00097 | -0.00645 |  0.00231 |
| 1h          |          24 |   -0.0362  | -0.02335 | -0.01879 |  0.00081 | -0.00494 |  0.01614 | -0.0362  |  0.00098 |
| 4h          |           6 |   -0.06409 | -0.03434 |  0.00505 |  0.06215 | -0.06409 | -0.01138 | -0.00539 | -0.00207 |
| 1d          |           1 |   -0.08063 | -0.08063 |  0.04773 | -0.02078 |  0.02719 | -0.01473 |  0.07443 | -0.00701 |

### Interpretation

- **15m**: short-horizon reversal exists at N=6–24 against H=2–12, then flips into stronger continuation at medium horizons. Strongest raw channel is `ret_42 -> fwd_42` (t=9.23, +12.57 bp spread) with additional continuation at `ret_12/24 -> fwd_84`.
- **1h**: mixed structure. `ret_12 -> fwd_12` is the clean continuation leg (t=5.14, +14.99 bp). A distinct long-horizon reversal appears at `ret_168 -> fwd_168` (t=-5.65, -64.30 bp), indicating non-monotone structure rather than one clean momentum curve.
- **4h**: strong monotone continuation. Signal strength generally increases with forward horizon and is strongest at `ret_168 -> fwd_168` (t=12.50, +615.20 bp).
- **1d**: strongest measured raw channel is long-horizon continuation. `ret_168 -> fwd_168` (t=10.77, +5798.60 bp) and `ret_84 -> fwd_168` (t=10.20, +5196.00 bp) dominate. Predictive content is weak at H<=12 and ramps sharply from H≈42 onward.

## Structural Features

### Return-rank / adaptive-threshold comparison on dominant raw-return channels

| Timeframe   |   Feature_N |   Measure_H |   RawPearson |   RawSpearman |   StaticSpread_bp |   Static_t |   TrailingRankPearson |   TrailingRankSpread_bp |   TrailingRank_t |   ExpandingRankPearson |   ExpandingRankSpread_bp |   ExpandingRank_t |
|:------------|------------:|------------:|-------------:|--------------:|------------------:|-----------:|----------------------:|------------------------:|-----------------:|-----------------------:|-------------------------:|------------------:|
| 15m         |          42 |          42 |       0.0978 |        0.0459 |            111.56 |       6.32 |                0.102  |                  103.8  |             7.65 |                 0.1034 |                   112.03 |              6.91 |
| 1d          |         168 |         168 |      -0.008  |        0.1497 |          -1637.35 |      -5.23 |                0.361  |                 7172.39 |            10.62 |                 0.2807 |                  -540.97 |             -1.78 |
| 1h          |          12 |          12 |       0.1384 |        0.0765 |            157.94 |       3.81 |                0.1327 |                  143.98 |             4.67 |                 0.136  |                   161.68 |              4.31 |
| 1h          |         168 |         168 |       0.0477 |        0.0633 |           1024.61 |      25.63 |               -0.0212 |                 -113.03 |            -1.03 |                 0.0077 |                   905.61 |             14.11 |
| 4h          |         168 |         168 |       0.055  |        0.07   |            472.71 |       5.58 |                0.0755 |                  766.06 |             9.89 |                 0.0688 |                   537.09 |              7.15 |

### Structural feature interpretation

- **Percentile rank vs raw value**
  - 15m `ret_42`: trailing rank is modestly cleaner than raw value (raw Pearson 0.0978 vs trailing-rank Pearson 0.1020; extreme-spread t rises from 6.32 static to 7.65 trailing).
  - 1h `ret_12`: rank transforms are roughly neutral; raw and ranked versions carry similar information.
  - 4h `ret_168`: trailing rank materially cleans the channel (raw Pearson 0.0550 -> trailing-rank Pearson 0.0755; t 5.58 static -> 9.89 trailing).
  - 1d `ret_168`: raw linear relation is weak/nonlinear (raw Pearson -0.0080, raw Spearman 0.1497). Trailing rank exposes the channel strongly (Pearson 0.3610, t=10.62), while fixed warmup thresholds and expanding thresholds both mis-handle drift and can flip sign.
- **Expanding vs trailing calibration**
  - No universal winner.
  - Trailing calibration is clearly superior on drifting long-horizon trend channels (`4h ret_168`, `1d ret_168`).
  - Expanding calibration is acceptable on 15m/1h shorter channels, but becomes stale on strongly drifting daily channels.
  - The 1h `ret_168` channel is structurally unstable: raw sign-split is reversal, trailing-rank extremes weaken materially, while expanding/static extremes flip positive. This is measurable but not a clean monotone state variable.

### Hysteresis test (entry 80th/20th percentile, hold 60th/40th percentile on the better side of trailing-rank state)

| Timeframe   |   Feature_N |   Measure_H | Side   |   NoH_Flips |   Hys_Flips |   FlipReduction_% |   NoH_MedianSpell |   Hys_MedianSpell |   NoH_Spread_bp |   Hys_Spread_bp |   SpreadRetention_% |   NoH_t |   Hys_t |
|:------------|------------:|------------:|:-------|------------:|------------:|------------------:|------------------:|------------------:|----------------:|----------------:|--------------------:|--------:|--------:|
| 15m         |          42 |          42 | upper  |         476 |         238 |              50   |                 3 |                27 |           39.83 |           40.7  |               102.2 |    8.7  |   10.6  |
| 1d          |         168 |         168 | upper  |          15 |           3 |              80   |                 5 |               242 |         6301.33 |         7087.58 |               112.5 |    8.66 |   10.68 |
| 1h          |          12 |          12 | upper  |         221 |         149 |              32.6 |                 4 |                12 |           59.49 |           46.4  |                78   |    6.26 |    5.83 |
| 1h          |         168 |         168 | lower  |          32 |          12 |              62.5 |                 6 |               121 |          538.62 |          363.66 |                67.5 |    8    |    7.56 |
| 4h          |         168 |         168 | upper  |         101 |          24 |              76.2 |                 3 |                95 |          -64.09 |          -17.28 |                27   |   -1.39 |   -0.37 |

- **15m `ret_42`**: hysteresis is useful. Flips fall 50.0%, median active spell rises 3 -> 27 bars, and spread is preserved/slightly improved (102.2% retention).
- **1h `ret_12`**: useful but with some cost. Flips fall 32.6%; spread retention 78.0%.
- **1h `ret_168`**: strong whipsaw reduction (62.5%) but only 67.5% of spread retained.
- **4h `ret_168`**: hysteresis is not helpful in this simple state construction; active-vs-inactive spread is weak/negative.
- **1d `ret_168`**: hysteresis is strongly beneficial. Flips fall 80.0%; median active spell rises 5 -> 242 days; spread improves (112.5% retention).

### Range position

| Timeframe   |   Window_N |   BestFwd_H |   SpreadHighLow_bp |     t |   Corr | Interpretation             |
|:------------|-----------:|------------:|-------------------:|------:|-------:|:---------------------------|
| 15m         |         24 |          84 |              18.06 |  4.53 | 0.0158 | high-in-range continuation |
| 15m         |         42 |          42 |              18.11 |  6.51 | 0.025  | high-in-range continuation |
| 15m         |         84 |          42 |              19.24 |  7.05 | 0.0275 | high-in-range continuation |
| 15m         |        168 |          42 |              19.26 |  7.43 | 0.0222 | high-in-range continuation |
| 1d          |         24 |          84 |            2795.66 |  6.59 | 0.1853 | high-in-range continuation |
| 1d          |         42 |          84 |            2424.32 |  6.05 | 0.1752 | high-in-range continuation |
| 1d          |         84 |         168 |            3544.09 |  6.26 | 0.1327 | high-in-range continuation |
| 1d          |        168 |         168 |            6269.54 | 10.41 | 0.3016 | high-in-range continuation |
| 1h          |         24 |         168 |              69.31 |  3.22 | 0.0268 | high-in-range continuation |
| 1h          |         42 |          84 |              65.85 |  4.52 | 0.0225 | high-in-range continuation |
| 1h          |         84 |          84 |              70.98 |  4.75 | 0.016  | high-in-range continuation |
| 1h          |        168 |           6 |              10.05 |  2.39 | 0.0103 | high-in-range continuation |
| 4h          |         24 |         168 |             470.78 |  5.95 | 0.0576 | high-in-range continuation |
| 4h          |         42 |         168 |             495.94 |  6.35 | 0.0767 | high-in-range continuation |
| 4h          |         84 |         168 |             639.53 |  8.52 | 0.0904 | high-in-range continuation |
| 4h          |        168 |         168 |             909.13 | 12.54 | 0.126  | high-in-range continuation |

- Range position is one of the cleanest structural channels in this snapshot. Across all four timeframes, being near the rolling high outperforms being near the rolling low.
- Strongest range-position channels: `4h rangepos_168 -> fwd_168` (t=12.54), `1d rangepos_168 -> fwd_168` (t=10.41), `15m rangepos_168 -> fwd_42` (t=7.43).

### Drawdown from rolling high

| Timeframe   |   Window_N |   Warmup_q10_dd |   Warmup_q90_dd |   BestFwd_H |   DeepMinusShallow_bp |      t | Interpretation         |   DeepRecWithinN_% |   DeepRecWithin2N_% |
|:------------|-----------:|----------------:|----------------:|------------:|----------------------:|-------:|:-----------------------|-------------------:|--------------------:|
| 15m         |         42 |         -0.0437 |         -0.0033 |         168 |                 32.62 |   3.81 | deep-drawdown rebound  |               14.8 |                23.4 |
| 15m         |         84 |         -0.0616 |         -0.0048 |          84 |                 36.22 |   5.45 | deep-drawdown rebound  |               12   |                20.6 |
| 15m         |        168 |         -0.0888 |         -0.0065 |          84 |                 22.72 |   3.23 | deep-drawdown rebound  |               17.9 |                28.8 |
| 1d          |         42 |         -0.3662 |         -0.0335 |         168 |              -2146.38 |  -2.28 | near-high continuation |                1.4 |                66.2 |
| 1d          |         84 |         -0.4914 |         -0.0469 |         168 |              -5751.83 |  -5.66 | near-high continuation |               21.4 |                 9.5 |
| 1d          |        168 |         -0.5894 |         -0.1771 |           1 |                nan    | nan    | noise                  |                0   |               100   |
| 1h          |         42 |         -0.0889 |         -0.0065 |          24 |                 36.32 |   2.49 | deep-drawdown rebound  |               17.5 |                26.7 |
| 1h          |         84 |         -0.1231 |         -0.0084 |          84 |               -127.43 |  -4.28 | near-high continuation |                9.3 |                16.8 |
| 1h          |        168 |         -0.1673 |         -0.0112 |           6 |                -10.3  |  -0.87 | near-high continuation |                4.5 |                13   |
| 4h          |         42 |         -0.1671 |         -0.0115 |         168 |               -378.05 |  -2.97 | near-high continuation |                6.3 |                17.5 |
| 4h          |         84 |         -0.2268 |         -0.0168 |         168 |               -336.59 |  -2.72 | near-high continuation |                5.6 |                30   |
| 4h          |        168 |         -0.2875 |         -0.0262 |         168 |               -501.87 |  -5.88 | near-high continuation |               10.1 |                17.6 |

- **15m**: deep drawdowns tend to rebound over the next 84–168 bars; this is the clearest mean-reversion structural channel in the entire scan.
- **1h**: mixed. Shorter drawdown windows (`dd_42`) rebound modestly, but larger windows (`dd_84`) favor staying near highs instead.
- **4h and 1d**: drawdowns generally do **not** mean-revert cleanly. Near-high states outperform deep drawdowns, reinforcing the broader trend-continuation picture.

## Mean-Reversion & Gaps

### Strongest measured reversal channels

| Timeframe   |   Past_N |   Forward_H |   Spread_bp |     t |    Corr |   SignPersistence_% |
|:------------|---------:|------------:|------------:|------:|--------:|--------------------:|
| 1h          |      168 |         168 |      -64.3  | -5.65 | -0.0511 |               46.58 |
| 15m         |        6 |           6 |       -1.85 | -3.42 | -0.0354 |               46.79 |
| 15m         |        6 |           3 |       -1.2  | -3.07 | -0.0393 |               46.57 |
| 15m         |       12 |          12 |       -1.91 | -2.54 | -0.0324 |               46.56 |
| 15m         |        6 |           2 |       -0.82 | -2.54 | -0.041  |               46.51 |
| 15m         |        6 |          12 |       -1.87 | -2.5  | -0.0291 |               47.18 |
| 15m         |       24 |          12 |       -1.82 | -2.42 | -0.0387 |               46.26 |

- The dominant measured reversal is `1h ret_168 -> fwd_168`.
- A secondary micro-reversion pocket exists on **15m**: `ret_6` and `ret_12` reverse over H=2–12 before medium-horizon continuation takes over.
- Outside those pockets, the snapshot is more continuation-heavy than reversal-heavy.

### Daily gap behavior (D1 open vs prior D1 close)

| Metric                                  |     Value |
|:----------------------------------------|----------:|
| Observations                            | 1277      |
| Mean gap (bp)                           |   -0.046  |
| Median gap (bp)                         |    0      |
| Max abs gap (bp)                        |   18.974  |
| Non-zero gaps                           |  782      |
| |gap| > 1 bp                            |   90      |
| Corr(gap, same-day return)              |    0.0105 |
| Corr(gap, next-day return)              |   -0.0137 |
| Same-day spread: pos gap - neg gap (bp) |   12.12   |
| Same-day spread t-stat                  |    0.44   |
| Next-day spread: pos gap - neg gap (bp) |  -17.62   |
| Next-day spread t-stat                  |   -0.63   |

- Gap predictiveness is effectively **noise** in discovery. Same-day and next-day gap-conditioned spreads are small and statistically weak (|t| < 1).
- This is consistent with 24/7 BTC trading: daily opens are not a distinct information arrival event in the way they are for session-based assets.

## Price/Momentum Channel Summary

### Strongest robust channels ranked by absolute predictive content

| Channel        | Timeframe   | Feature                | Measure                |        t |   Spread_bp | Direction                  |   N_obs |
|:---------------|:------------|:-----------------------|:-----------------------|---------:|------------:|:---------------------------|--------:|
| range_position | 4h          | rangepos_168           | 80/20 split -> fwd_168 | 12.5422  |    909.129  | high-in-range continuation |    3181 |
| return_sign    | 4h          | ret_168                | sign split -> fwd_168  | 12.4978  |    615.205  | continuation               |    7325 |
| return_sign    | 1d          | ret_168                | sign split -> fwd_168  | 10.7732  |   5798.6    | continuation               |    1277 |
| return_rank    | 1d          | ret_168_trailing_rank  | extremes -> fwd_168    | 10.615   |   7172.39   | upper>lower                |     593 |
| range_position | 1d          | rangepos_168           | 80/20 split -> fwd_168 | 10.4068  |   6269.54   | high-in-range continuation |     741 |
| return_sign    | 1d          | ret_84                 | sign split -> fwd_168  | 10.2023  |   5196      | continuation               |    1277 |
| return_rank    | 4h          | ret_168_trailing_rank  | extremes -> fwd_168    |  9.89488 |    766.065  | upper>lower                |     969 |
| return_sign    | 15m         | ret_42                 | sign split -> fwd_42   |  9.23402 |     12.566  | continuation               |  121177 |
| range_position | 4h          | rangepos_84            | 80/20 split -> fwd_168 |  8.52418 |    639.531  | high-in-range continuation |    3021 |
| return_rank    | 15m         | ret_42_trailing_rank   | extremes -> fwd_42     |  7.6506  |    103.798  | upper>lower                |    1962 |
| range_position | 15m         | rangepos_168           | 80/20 split -> fwd_42  |  7.43277 |     19.2607 | high-in-range continuation |   42102 |
| return_sign    | 15m         | ret_12                 | sign split -> fwd_84   |  7.41197 |     14.548  | continuation               |  120996 |
| return_sign    | 15m         | ret_168                | sign split -> fwd_42   |  7.32366 |     10.1199 | continuation               |  119290 |
| return_rank    | 4h          | ret_168_expanding_rank | extremes -> fwd_168    |  7.15168 |    537.089  | upper>lower                |     755 |
| range_position | 15m         | rangepos_84            | 80/20 split -> fwd_42  |  7.04913 |     19.236  | high-in-range continuation |   39671 |

### Concise takeaways

- **Cleanest long-horizon continuation**: `4h ret_168`, `4h rangepos_168`, `1d ret_168`, `1d rangepos_168`.
- **Cleanest medium-horizon continuation**: `15m ret_42`, `15m rangepos_84/168`, `1h ret_12`.
- **Cleanest mean-reversion**: `1h ret_168 -> fwd_168` and `15m` deep-drawdown rebound / short return reversal pockets.
- **Noise / weak channels**: D1 gap behavior; 4h hysteresis on return-rank state; any claim that 1h long-horizon return is a simple monotone momentum feature.

D1b1 complete. No strategies, no backtests, no candidate proposals were produced.