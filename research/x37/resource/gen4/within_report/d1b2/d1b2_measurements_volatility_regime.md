# D1b2 — Volatility & Regime Measurements

## Scope
- Data source: admitted historical snapshot only.
- Calibration: warmup through 2019-12-31 UTC.
- Measurement window: discovery 2020-01-01 through 2023-06-30 UTC.
- Holdout and reserve_internal were not used.
- Snapshot remains candidate-mining-only; no clean external OOS claim is made here.
- No strategy rules, backtests, or candidate proposals were produced.

## Volatility Channels

### Volatility clustering

`AbsRet_AC*` is autocorrelation of absolute 1-bar log returns. `RV42_AC*` is autocorrelation of 42-bar realized volatility (rolling std of 1-bar log returns). `RV42_AC1` is overlap-inflated; `RV42_AC42` is the cleaner persistence check.

| Timeframe   |   AbsRet_AC1 |   AbsRet_AC6 |   AbsRet_AC24 |   AbsRet_AC42 |   RV42_AC1 |   RV42_AC6 |   RV42_AC24 |   RV42_AC42 |
|:------------|-------------:|-------------:|--------------:|--------------:|-----------:|-----------:|------------:|------------:|
| 15m         |       0.374  |       0.2494 |        0.1982 |        0.1931 |     0.9961 |     0.964  |      0.8111 |      0.6615 |
| 1h          |       0.2812 |       0.1872 |        0.1612 |        0.1285 |     0.9951 |     0.9608 |      0.7752 |      0.5764 |
| 4h          |       0.2159 |       0.1577 |        0.148  |        0.1315 |     0.9948 |     0.9578 |      0.7807 |      0.5567 |
| 1d          |       0.1296 |       0.0804 |        0.0505 |        0.0402 |     0.9868 |     0.901  |      0.501  |      0.0854 |

### Realized-volatility level: strongest directional effect by timeframe

| Timeframe   |   W |   H |   Spread_bp |      t |    Corr | Interpretation                    |
|:------------|----:|----:|------------:|-------:|--------:|:----------------------------------|
| 15m         |  84 | 168 |       70.37 |  10.16 |  0.0226 | high-vol > low-vol forward return |
| 1d          |  84 | 168 |   -10092.4  | -11.51 | -0.273  | high-vol < low-vol forward return |
| 1h          |  24 |  24 |       53.25 |   4.66 |  0.0356 | high-vol > low-vol forward return |
| 4h          |  84 | 168 |     1007.42 |  10.07 |  0.0613 | high-vol > low-vol forward return |

### Realized-volatility level: strongest future-magnitude effect by timeframe

| Timeframe   |   W |   H |   Spread_bp |      t |    Corr | Interpretation                      |
|:------------|----:|----:|------------:|-------:|--------:|:------------------------------------|
| 15m         |  84 |  12 |      139.65 |  74.02 |  0.3847 | high-vol > low-vol future magnitude |
| 1d          |  42 | 168 |   -11142.5  | -12.52 | -0.2782 | high-vol < low-vol future magnitude |
| 1h          |  24 |   6 |      162.34 |  33.41 |  0.3528 | high-vol > low-vol future magnitude |
| 4h          |   6 |   6 |      218.55 |  16.73 |  0.211  | high-vol > low-vol future magnitude |

### Range-based volatility level: strongest directional effect by timeframe

| Timeframe   |   W |   H |   Spread_bp |      t |    Corr | Interpretation                           |
|:------------|----:|----:|------------:|-------:|--------:|:-----------------------------------------|
| 15m         |  24 |  84 |       34.29 |   6.58 |  0.0542 | wide-range > narrow-range forward return |
| 1d          |  84 | 168 |   -15338.3  | -18.06 | -0.4281 | wide-range < narrow-range forward return |
| 1h          |   6 | 168 |      121.92 |   5.2  |  0.057  | wide-range > narrow-range forward return |
| 4h          |  84 | 168 |      770.92 |   7.58 |  0.0674 | wide-range > narrow-range forward return |

### Range-based volatility level: strongest future-magnitude effect by timeframe

| Timeframe   |   W |   H |   Spread_bp |      t |    Corr | Interpretation                             |
|:------------|----:|----:|------------:|-------:|--------:|:-------------------------------------------|
| 15m         |   6 |  12 |      128.01 |  78.88 |  0.3861 | wide-range > narrow-range future magnitude |
| 1d          |  84 | 168 |   -14099    | -17.21 | -0.4883 | wide-range < narrow-range future magnitude |
| 1h          |  24 |   6 |      178.42 |  38.4  |  0.3642 | wide-range > narrow-range future magnitude |
| 4h          |  24 |   6 |      273.29 |  17.75 |  0.2853 | wide-range > narrow-range future magnitude |

### Volatility-normalized returns: best measured normalization benefit by timeframe

Normalization compares raw `N`-bar return vs `N`-bar return divided by `(rolling std of 1-bar log returns) * sqrt(N)` at the same forward horizon `H=N`. `BlockStd` and `SignCons` are computed on 7 half-year blocks inside discovery only.

| Timeframe   |   W |   RawCorr |   NormCorr |   CorrDelta |   Raw_t |   Norm_t |   tDelta |   RawBlockStd |   NormBlockStd |   RawSignCons |   NormSignCons | Take             |
|:------------|----:|----------:|-----------:|------------:|--------:|---------:|---------:|--------------:|---------------:|--------------:|---------------:|:-----------------|
| 15m         |  84 |   -0.0213 |     0.0228 |      0.0441 |    0.71 |     7.26 |     6.55 |        0.0622 |         0.0496 |         0.571 |          0.714 | best improvement |
| 1h          | 168 |   -0.0511 |    -0.0078 |      0.0433 |   -4.43 |    -0.56 |     3.87 |        0.1757 |         0.1264 |         0.714 |          0.714 | best improvement |
| 4h          | 168 |    0.1816 |     0.1731 |     -0.0086 |   19.51 |    22.43 |     2.92 |        0.2359 |         0.2064 |         0.286 |          0.286 | best improvement |
| 1d          | 168 |   -0.0076 |     0.0351 |      0.0427 |    0.9  |     5.87 |     4.98 |        0.4857 |         0.4845 |         0.667 |          0.333 | best improvement |

### Compression states

Compression uses the warmup 20th percentile of realized volatility for each `W`. `InCompAbs*` compares compression bars against non-compression bars. `ReleaseAbs*` measures the first bar after exiting compression.

| Timeframe   |   W |   CompShare_% |   Episodes |   MedianLen_bars |   MaxLen_bars |   InCompAbsSpread_bp |   InCompAbs_t |   ReleaseAbsSpread_bp |   ReleaseAbs_t | Interpretation                         |
|:------------|----:|--------------:|-----------:|-----------------:|--------------:|---------------------:|--------------:|----------------------:|---------------:|:---------------------------------------|
| 15m         |  12 |         20.37 |       2042 |                4 |           370 |               -48.82 |        -98.39 |                -16.52 |          -9.56 | compression -> lower future magnitude  |
| 1h          |   6 |         20.42 |       1146 |                3 |           112 |               -56.64 |        -38.48 |                -19.16 |          -5.98 | compression -> lower future magnitude  |
| 4h          |   6 |         17.43 |        290 |                2 |            98 |              -102    |        -16.24 |                -22.76 |          -1.57 | compression -> lower future magnitude  |
| 1d          | 168 |         23.81 |          8 |                3 |           137 |              8544.03 |          9    |                nan    |         nan    | compression -> higher future magnitude |

### Volatility-channel interpretation
- Volatility clustering is real in all four timeframes. `|r1|` lag-1 autocorrelation declines monotonically from `15m` to `1d`; `rv_42` remains persistent even at lag 42. Short-lag `rv_42` autocorrelation is mechanically inflated by overlap, so lag-42 is the cleaner persistence readout.
- Range-based volatility is at least as informative as realized-volatility for future magnitude in `15m/1h/4h`, and materially stronger on `1d` long horizons.
- Volatility is much cleaner as a **magnitude/regime** channel than as a universal directional channel.
- Intraday compression does **not** support a generic breakout-release claim here. In `15m/1h/4h`, compression states carry **lower** future magnitude, and release bars do not restore a strong positive expansion effect.

## Regime Structure

### Regime lens

Regime measurement uses a raw-data lens at `W=42` bars:
- `crisis`: realized volatility >= warmup 95th percentile
- `trend`: directional-efficiency >= warmup 80th percentile, not crisis
- `chop`: directional-efficiency <= warmup 20th percentile, not crisis
- `other`: all remaining states

### Regime state statistics

| Timeframe   | Regime   |   Share_% |   MeanEff42 |   MeanStd42 |   MeanFwd42_bp |   MeanAbsFwd42_bp |   CurrentTail95_% |
|:------------|:---------|----------:|------------:|------------:|---------------:|------------------:|------------------:|
| 15m         | trend    |     20.29 |        0.34 |        0    |           5.8  |            164.94 |              3.76 |
| 15m         | chop     |     19.52 |        0.02 |        0    |           9.13 |            141.93 |              1.13 |
| 15m         | crisis   |      1.54 |        0.17 |        0.01 |          22.86 |            421.76 |             30.3  |
| 15m         | other    |     58.65 |        0.13 |        0    |           6.54 |            147.96 |              1.67 |
| 1h          | trend    |     20.34 |        0.37 |        0.01 |          20.07 |            311.52 |              3.52 |
| 1h          | chop     |     19.2  |        0.02 |        0.01 |          23.24 |            319.13 |              1.12 |
| 1h          | crisis   |      1.18 |        0.15 |        0.03 |         -29.94 |            610.67 |             27.38 |
| 1h          | other    |     59.28 |        0.14 |        0.01 |          27.9  |            337.54 |              1.82 |
| 4h          | trend    |     16.68 |        0.4  |        0.01 |         315.06 |            781.73 |              4.46 |
| 4h          | chop     |     21.33 |        0.03 |        0.01 |          87.49 |            694.04 |              1.8  |
| 4h          | crisis   |      1.11 |        0.26 |        0.05 |         920.39 |           1193.66 |             26.19 |
| 4h          | other    |     60.88 |        0.17 |        0.01 |          89.92 |            692.19 |              2.29 |
| 1d          | trend    |     16.28 |        0.42 |        0.03 |        2119    |           3298.84 |              2.49 |
| 1d          | chop     |     14.41 |        0.03 |        0.03 |         395.4  |           2285.67 |              2.25 |
| 1d          | crisis   |      3.4  |        0.2  |        0.09 |        4002.94 |           4002.94 |              9.52 |
| 1d          | other    |     65.91 |        0.19 |        0.03 |         353.19 |           1981.18 |              2.21 |

### Pairwise regime spreads

`Dir_*` uses forward 42-bar signed return; `Abs_*` uses forward 42-bar absolute return.

| Timeframe   | Comparison      |   DirSpread_bp |   Dir_t |   AbsSpread_bp |   Abs_t |
|:------------|:----------------|---------------:|--------:|---------------:|--------:|
| 15m         | trend vs chop   |          -3.33 |   -1.57 |          23.01 |   14.48 |
| 15m         | crisis vs chop  |          13.73 |    1.01 |         279.83 |   29.55 |
| 15m         | crisis vs trend |          17.05 |    1.25 |         256.82 |   27.06 |
| 1h          | trend vs chop   |          -3.18 |   -0.37 |          -7.61 |   -1.21 |
| 1h          | crisis vs chop  |         -53.19 |   -1.28 |         291.54 |   11.6  |
| 1h          | crisis vs trend |         -50.01 |   -1.21 |         299.15 |   11.95 |
| 4h          | trend vs chop   |         227.57 |    6.08 |          87.69 |    3.31 |
| 4h          | crisis vs chop  |         832.9  |    6.14 |         499.62 |    4.74 |
| 4h          | crisis vs trend |         605.33 |    4.43 |         411.93 |    3.88 |
| 1d          | trend vs chop   |        1723.6  |    5.29 |        1013.17 |    4.75 |
| 1d          | crisis vs chop  |        3607.53 |   14.97 |        1717.26 |   10.01 |
| 1d          | crisis vs trend |        1883.94 |    6.49 |         704.09 |    3.08 |

### Distribution tails: extreme 1%/99% one-bar returns

`SignedEdge_bp` is the mean of `sign(current tail return) * forward return`; positive = continuation, negative = reversal. `UpTailMean_bp` / `DownTailMean_bp` are conditional forward means at the best `H`.

| Timeframe   |   BestH |   TailEvents |   SignedEdge_bp |   Signed_t |   UpTailMean_bp |   DownTailMean_bp |
|:------------|--------:|-------------:|----------------:|-----------:|----------------:|------------------:|
| 15m         |      24 |          937 |          -72.13 |      -5.15 |            3.69 |            157.4  |
| 1d          |       1 |           12 |         -424.86 |      -2.47 |         -106.54 |            652.23 |
| 1h          |       6 |          214 |          -65.47 |      -2.08 |           18.49 |            147.87 |
| 4h          |       6 |           61 |         -127.82 |      -1.68 |           86.84 |            298.29 |

### Distribution tails: extreme-tail future-magnitude effect

| Timeframe   |   BestH |   TailEvents |   TailMinusNonTailAbs_bp |   Abs_t |
|:------------|--------:|-------------:|-------------------------:|--------:|
| 15m         |      12 |          939 |                   156.87 |   17.43 |
| 1d          |       1 |           12 |                   265.88 |    1.79 |
| 1h          |       1 |          215 |                   116.24 |    9.23 |
| 4h          |       6 |           61 |                   230.48 |    4.85 |

### Distribution tails: 5%/95% robustness check for directional effect

| Timeframe   |   BestH_5pct |   TailEvents_5pct |   SignedEdge_bp_5pct |   Signed_t_5pct |
|:------------|-------------:|------------------:|---------------------:|----------------:|
| 15m         |           24 |              7180 |               -12.96 |           -3.54 |
| 1h          |            2 |              1759 |                -6.24 |           -1.3  |
| 4h          |           42 |               477 |                63.97 |            1.24 |
| 1d          |            3 |                75 |              -121.69 |           -1.84 |

### Regime interpretation
- `4h` and `1d` show the clearest directional regime structure; `1h` trend-vs-chop is mostly noise; `15m` crisis states matter mainly for magnitude.
- One-bar return tails mostly increase near-term future magnitude. Directionally, tails are reversal-biased on `15m`, weakly reversal-biased on `1h`, near-noise on `4h`, and underpowered on `1d`.

## Volatility/Regime Channel Summary

### Strongest directional signals ranked by absolute t-stat

| Channel           | Timeframe   | Feature         | Measure                |      t |   Spread_bp | Interpretation             |
|:------------------|:------------|:----------------|:-----------------------|-------:|------------:|:---------------------------|
| range_vol         | 1d          | range_W84       | high/low -> fwd_168    | -18.06 |   -15338.3  | wide range < narrow range  |
| regime            | 1d          | crisis_vs_chop  | state spread -> fwd_42 |  14.97 |     3607.53 | first state > second state |
| realized_vol      | 1d          | vol_W84         | high/low -> fwd_168    | -11.51 |   -10092.4  | high vol < low vol         |
| realized_vol      | 15m         | vol_W84         | high/low -> fwd_168    |  10.16 |       70.37 | high vol > low vol         |
| realized_vol      | 4h          | vol_W84         | high/low -> fwd_168    |  10.07 |     1007.42 | high vol > low vol         |
| range_vol         | 4h          | range_W84       | high/low -> fwd_168    |   7.58 |      770.92 | wide range > narrow range  |
| range_vol         | 15m         | range_W24       | high/low -> fwd_84     |   6.58 |       34.29 | wide range > narrow range  |
| regime            | 4h          | crisis_vs_chop  | state spread -> fwd_42 |   6.14 |      832.9  | first state > second state |
| range_vol         | 1h          | range_W6        | high/low -> fwd_168    |   5.2  |      121.92 | wide range > narrow range  |
| tail_extreme_1pct | 15m         | 1-bar tail sign | signed -> fwd_24       |  -5.15 |      -72.13 | reversal                   |
| realized_vol      | 1h          | vol_W24         | high/low -> fwd_24     |   4.66 |       53.25 | high vol > low vol         |
| tail_extreme_1pct | 1d          | 1-bar tail sign | signed -> fwd_1        |  -2.47 |     -424.86 | reversal                   |

### Strongest magnitude / regime signals ranked by absolute t-stat

| Channel           | Timeframe   | Feature        | Measure                  |      t |   Spread_bp | Interpretation                          |
|:------------------|:------------|:---------------|:-------------------------|-------:|------------:|:----------------------------------------|
| compression       | 15m         | comp_W12       | in-state -> |fwd_12|     | -98.39 |      -48.82 | compression < non-compression magnitude |
| range_vol         | 15m         | range_W6       | high/low -> |fwd_12|     |  78.88 |      128.01 | wide range > narrow range magnitude     |
| realized_vol      | 15m         | vol_W84        | high/low -> |fwd_12|     |  74.02 |      139.65 | high vol > low vol magnitude            |
| compression       | 1h          | comp_W6        | in-state -> |fwd_6|      | -38.48 |      -56.64 | compression < non-compression magnitude |
| range_vol         | 1h          | range_W24      | high/low -> |fwd_6|      |  38.4  |      178.42 | wide range > narrow range magnitude     |
| realized_vol      | 1h          | vol_W24        | high/low -> |fwd_6|      |  33.41 |      162.34 | high vol > low vol magnitude            |
| regime            | 15m         | crisis_vs_chop | state spread -> |fwd_42| |  29.55 |      279.83 | first state > second state magnitude    |
| range_vol         | 4h          | range_W24      | high/low -> |fwd_6|      |  17.75 |      273.29 | wide range > narrow range magnitude     |
| tail_extreme_1pct | 15m         | 1-bar tail     | tail -> |fwd_12|         |  17.43 |      156.87 | tail > non-tail magnitude               |
| range_vol         | 1d          | range_W84      | high/low -> |fwd_168|    | -17.21 |   -14099    | wide range < narrow range magnitude     |
| realized_vol      | 4h          | vol_W6         | high/low -> |fwd_6|      |  16.73 |      218.55 | high vol > low vol magnitude            |
| compression       | 4h          | comp_W6        | in-state -> |fwd_6|      | -16.24 |     -102    | compression < non-compression magnitude |

### Concise conclusions
- **Cleanest universal fact**: volatility clusters strongly across all frames.
- **Cleanest volatility use-case**: future-magnitude discrimination, not one universal directional bet.
- **Best directional regime frames**: `4h` and `1d`.
- **Best intraday magnitude filters**: `15m` and `1h` realized/range volatility; both are strong, with range-based volatility slightly stronger.
- **Compression verdict**: intraday compression is a low-magnitude state, not a clean breakout-launch state.
- **Tail verdict**: tails mostly raise subsequent magnitude; directional reversal is clearest on `15m`, weaker on `1h`, and not robust on `4h/1d`.
- **Noise / weak channels**: `1h` trend-vs-chop directional split, daily extreme-tail direction (sample too small), and any generic claim that compression-release reliably expands volatility immediately after the exit bar.

D1b2 complete. No strategies, no backtests, and no candidate proposals were produced.