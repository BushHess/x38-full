# D1b1 Measurements — Price & Momentum Channels

Scope: warmup used only for calibration; discovery (2020-01-01 to 2023-06-30 UTC) used for measurement. Holdout and reserve_internal were not used. Historical snapshot remains candidate-mining-only; no clean external OOS claim is made here.

Definitions used here:

- `return_N = close_t / close_(t-N) - 1`

- persistence = `P(sign(return_N) = sign(next 1-bar return))`

- `onset_H` = first forward horizon with `|t| >= 2` for the sign-split conditional return test

- `decay_H` = last consecutive measured horizon retaining the same sign and `|t| >= 2`

- range position = `(close - rolling_low_N) / (rolling_high_N - rolling_low_N)`

- drawdown depth compares deepest 20% vs shallowest 20% states relative to rolling high; positive delta = mean reversion, negative delta = trend persistence.


## 1. Return & Momentum Channels

### Return autocorrelation of 1-bar returns (discovery only)

| timeframe   |    lag1 |    lag2 |    lag3 |    lag6 |   lag12 |   lag24 |
|:------------|--------:|--------:|--------:|--------:|--------:|--------:|
| 15m         |  0.001  | -0.0528 |  0.0092 | -0.0077 |  0.0009 | -0.0068 |
| 1d          | -0.0806 |  0.0477 | -0.0208 |  0.0272 | -0.0147 |  0.0744 |
| 1h          | -0.0234 | -0.0184 |  0.0003 | -0.0043 |  0.0142 | -0.0336 |
| 4h          | -0.0347 |  0.0055 |  0.0619 | -0.0632 | -0.0113 | -0.0059 |


Interpretation: 1-bar autocorrelation is weak overall. The clearest short-horizon reversal shows up at 15m lag-2 and at 1h lag-1/2/24, but the absolute magnitudes are small. Measurable edge is carried much more by multi-bar state than by raw 1-bar autocorrelation.

### 15m return/momentum summary

|   N |   persist_prob_h1 |   delta_h1_bps |   t_h1 |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | best_direction   |
|----:|------------------:|---------------:|-------:|----------:|----------:|---------:|-----------------:|---------:|:-----------------|
|   6 |             0.467 |         -0.191 | -0.834 |         3 |        12 |        6 |           -1.846 |   -3.419 | reversal         |
|  12 |             0.473 |         -0.023 | -0.1   |        12 |        12 |       48 |            6.574 |    4.523 | continuation     |
|  24 |             0.479 |         -0.24  | -1.045 |        12 |        12 |       48 |           10.341 |    7.106 | continuation     |
|  42 |             0.487 |         -0.055 | -0.237 |        12 |        48 |       48 |           15.034 |   10.319 | continuation     |
|  84 |             0.492 |          0.162 |  0.699 |         6 |        48 |       12 |            5.142 |    6.802 | continuation     |
| 168 |             0.497 |          0.301 |  1.284 |         3 |        96 |       24 |            7.214 |    6.793 | continuation     |


### 1h return/momentum summary

|   N |   persist_prob_h1 |   delta_h1_bps |   t_h1 |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | best_direction   |
|----:|------------------:|---------------:|-------:|----------:|----------:|---------:|-----------------:|---------:|:-----------------|
|   6 |             0.464 |         -0.909 | -1.027 |        12 |        12 |       12 |            9.462 |    3.248 | continuation     |
|  12 |             0.476 |          0.493 |  0.556 |         6 |        12 |       12 |           14.994 |    5.137 | continuation     |
|  24 |             0.478 |          0.23  |  0.257 |       nan |       nan |       24 |           -4.158 |   -0.975 | reversal         |
|  42 |             0.491 |          1.143 |  1.266 |         3 |        12 |        6 |            6.698 |    3.152 | continuation     |
|  84 |             0.496 |          1.186 |  1.294 |         6 |        48 |       48 |           24.062 |    3.967 | continuation     |
| 168 |             0.5   |          0.57  |  0.608 |       nan |       nan |       24 |            8.371 |    1.889 | continuation     |


### 4h return/momentum summary

|   N |   persist_prob_h1 |   delta_h1_bps |   t_h1 |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | best_direction   |
|----:|------------------:|---------------:|-------:|----------:|----------:|---------:|-----------------:|---------:|:-----------------|
|   6 |             0.465 |         -2.675 | -0.781 |       nan |       nan |        6 |          -13.425 |   -1.601 | reversal         |
|  12 |             0.481 |          0.676 |  0.196 |        24 |        24 |       24 |           41.02  |    2.458 | continuation     |
|  24 |             0.493 |          2.881 |  0.832 |        24 |        24 |       24 |           49.026 |    2.949 | continuation     |
|  42 |             0.499 |          3.073 |  0.885 |        24 |        24 |       24 |           37.72  |    2.265 | continuation     |
|  84 |             0.503 |          4.884 |  1.377 |         3 |        24 |       12 |           53.568 |    4.49  | continuation     |
| 168 |             0.513 |          9.115 |  2.72  |         1 |        24 |       24 |          144.07  |    9.009 | continuation     |


### 1d return/momentum summary

|   N |   persist_prob_h1 |   delta_h1_bps |   t_h1 |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | best_direction   |
|----:|------------------:|---------------:|-------:|----------:|----------:|---------:|-----------------:|---------:|:-----------------|
|   6 |             0.469 |          0.831 |  0.039 |        12 |        12 |       12 |          150.308 |    2.037 | continuation     |
|  12 |             0.492 |         18.11  |  0.842 |       nan |       nan |        3 |           61.756 |    1.736 | continuation     |
|  24 |             0.491 |         27.162 |  1.267 |         3 |        24 |       24 |          506.511 |    4.558 | continuation     |
|  42 |             0.504 |         25.831 |  1.22  |         3 |        12 |        3 |           78.933 |    2.234 | continuation     |
|  84 |             0.507 |          1.915 |  0.09  |       nan |       nan |       24 |          182.47  |    1.665 | continuation     |
| 168 |             0.495 |          0.477 |  0.023 |        24 |        24 |       24 |          248.709 |    2.225 | continuation     |


Key findings:

- **15m**: very short lookback (`N=6`) is a short-horizon reversal channel; medium/long lookbacks (`N=42,84,168`) become strong continuation channels, with the strongest measurement at `N=42 -> H=48` (+15.034 bps, `t=10.319`).

- **1h**: the cleanest price continuation sits at `N=12 -> H=12` (+14.994 bps, `t=5.137`). `N=24` and `N=168` are mostly noise in this sample.

- **4h**: continuation is long-memory. `N=168 -> H=24` is the strongest raw momentum measurement (+144.070 bps, `t=9.009`), with onset already visible from `H=1` and persisting through `H=24`.

- **1d**: daily continuation is present but slower. `N=24 -> H=24` is strongest (+506.511 bps, `t=4.558`); onset begins at `H=3` and persists through `H=24`.

- Next-bar persistence itself is weak: `persist_prob_h1` sits near 0.47–0.51 for most lookbacks. The signal generally **does not monetize at the next bar**; it emerges over multi-bar forward horizons.


## 2. Structural Features

### Range-position channel summary

#### 15m

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction    |
|----:|----------:|----------:|---------:|-----------------:|---------:|:-------------|
|   6 |         3 |         6 |        3 |           -1.697 |   -3.43  | reversal     |
|  12 |        48 |        96 |       48 |            8.416 |    4.189 | continuation |
|  24 |        48 |        96 |       48 |           16.064 |    7.364 | continuation |
|  42 |        24 |        96 |       48 |           25.702 |   11.242 | continuation |
|  84 |         6 |        96 |       48 |           23.493 |   10.075 | continuation |
| 168 |         6 |        96 |       48 |           22.58  |    9.629 | continuation |


#### 1h

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction    |
|----:|----------:|----------:|---------:|-----------------:|---------:|:-------------|
|   6 |        12 |        12 |       12 |           12.216 |    3.281 | continuation |
|  12 |         6 |        12 |       12 |           23.156 |    5.681 | continuation |
|  24 |         3 |        12 |       12 |           17.349 |    4.072 | continuation |
|  42 |         3 |        12 |       12 |           20.605 |    4.688 | continuation |
|  84 |         6 |        12 |       12 |           12.717 |    2.835 | continuation |
| 168 |       nan |       nan |       48 |           17.123 |    1.889 | continuation |


#### 4h

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction    |
|----:|----------:|----------:|---------:|-----------------:|---------:|:-------------|
|   6 |       nan |       nan |        3 |           11.372 |    1.595 | continuation |
|  12 |        24 |        24 |       24 |           55.903 |    2.502 | continuation |
|  24 |       nan |       nan |       24 |           43.105 |    1.835 | continuation |
|  42 |        24 |        24 |       24 |           67.826 |    2.705 | continuation |
|  84 |        12 |        24 |       24 |           79.888 |    3.47  | continuation |
| 168 |         6 |        24 |       24 |          120.682 |    5.525 | continuation |


#### 1d

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction    |
|----:|----------:|----------:|---------:|-----------------:|---------:|:-------------|
|   6 |        24 |        24 |       24 |          277.739 |    2.062 | continuation |
|  12 |        24 |        24 |       24 |          372.934 |    2.562 | continuation |
|  24 |         3 |        24 |       24 |          639.97  |    4.627 | continuation |
|  42 |         3 |        24 |       24 |          577.085 |    4.279 | continuation |
|  84 |        12 |        24 |       24 |          318.84  |    2.274 | continuation |
| 168 |        12 |        24 |       24 |          483.054 |    3.48  | continuation |


Range-position result: close location inside the recent high-low range is consistently informative, and in most cases cleaner than raw signed momentum. The strongest range-position measurements are `15m N=42 -> H=48` (+25.702 bps, `t=11.242`), `1h N=12 -> H=12` (+23.156 bps, `t=5.681`), `4h N=168 -> H=24` (+120.682 bps, `t=5.525`), and `1d N=24 -> H=24` (+639.970 bps, `t=4.627`).


### Drawdown-from-rolling-high summary

#### 15m

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction         |
|----:|----------:|----------:|---------:|-----------------:|---------:|:------------------|
|   6 |         1 |        12 |        3 |            3.155 |    4.139 | mean_reversion    |
|  12 |        48 |        48 |       48 |           -8.564 |   -3.246 | trend_persistence |
|  24 |        12 |        12 |       48 |          -11.317 |   -4.293 | trend_persistence |
|  42 |        24 |        48 |       48 |          -16.029 |   -6.072 | trend_persistence |
|  84 |        12 |        48 |       48 |          -10.592 |   -4.011 | trend_persistence |
| 168 |        24 |        48 |       48 |          -12.707 |   -4.785 | trend_persistence |


#### 1h

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction         |
|----:|----------:|----------:|---------:|-----------------:|---------:|:------------------|
|   6 |       nan |       nan |        3 |            4.493 |    1.584 | mean_reversion    |
|  12 |        12 |        12 |       12 |          -12.225 |   -2.269 | trend_persistence |
|  24 |       nan |       nan |       12 |           -4.546 |   -0.851 | trend_persistence |
|  42 |        12 |        12 |       12 |          -13.571 |   -2.532 | trend_persistence |
|  84 |         6 |        12 |        6 |          -10.303 |   -2.531 | trend_persistence |
| 168 |        48 |        48 |       48 |           28.139 |    2.673 | mean_reversion    |


#### 4h

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction         |
|----:|----------:|----------:|---------:|-----------------:|---------:|:------------------|
|   6 |       nan |       nan |        6 |           21.548 |    1.475 | mean_reversion    |
|  12 |       nan |       nan |        3 |          -17.306 |   -1.654 | trend_persistence |
|  24 |       nan |       nan |       24 |          -53.918 |   -1.799 | trend_persistence |
|  42 |       nan |       nan |       24 |          -47.712 |   -1.585 | trend_persistence |
|  84 |       nan |       nan |       24 |          -29.058 |   -1.1   | trend_persistence |
| 168 |       nan |       nan |       24 |          -50.53  |   -1.973 | trend_persistence |


#### 1d

|   N |   onset_H |   decay_H |   best_H |   best_delta_bps |   best_t | direction         |
|----:|----------:|----------:|---------:|-----------------:|---------:|:------------------|
|   6 |       nan |       nan |       12 |         -224.122 |   -1.949 | trend_persistence |
|  12 |        12 |        12 |       12 |         -254.816 |   -2.077 | trend_persistence |
|  24 |       nan |       nan |       24 |         -300.534 |   -1.723 | trend_persistence |
|  42 |         3 |        24 |       24 |         -525.945 |   -3.067 | trend_persistence |
|  84 |        24 |        24 |       24 |         -352.328 |   -2.027 | trend_persistence |
| 168 |        24 |        24 |       24 |         -437.703 |   -2.621 | trend_persistence |


Drawdown result: **mean-reversion is not the dominant drawdown behavior**. Outside a narrow short-horizon intraday bounce (`15m N=6`) and a weaker long-window hourly bounce (`1h N=168`), deeper drawdowns mostly underperform shallow states, i.e. drawdown depth behaves more like **trend persistence** than reversal. On `4h`, drawdown depth is effectively noise across the measured horizons.


### Depth distribution and recovery patterns (best drawdown window per timeframe)

| timeframe   |   N |   depth_p80_pct |   depth_p95_pct |   deep_rec_N_pct |   shallow_rec_N_pct |   deep_rec_2N_pct |   shallow_rec_2N_pct |   deep_fwd_N_bps |   shallow_fwd_N_bps |
|:------------|----:|----------------:|----------------:|-----------------:|--------------------:|------------------:|---------------------:|-----------------:|--------------------:|
| 15m         |  42 |           1.98  |           4.298 |           15.313 |              80.946 |            27.891 |               87.689 |            1.386 |              16.044 |
| 1h          | 168 |           8.682 |          15.539 |           19.615 |              87.899 |            25.768 |               91.746 |          162.862 |             125.711 |
| 4h          | 168 |          16.965 |          28.018 |           15.621 |              92.945 |            26.057 |               94.848 |          155.464 |             924.675 |
| 1d          |  42 |          20.713 |          36.185 |           11.719 |              92.969 |            23.047 |               95.703 |          248.251 |             934.888 |


Recovery interpretation: shallow states near rolling highs recover / make new highs far more often than deep drawdowns. Example: `15m N=42` deep drawdowns recover the prior 42-bar high within 42 bars only **15.3%** of the time versus **80.9%** for shallow states; `1d N=42` deep drawdowns recover within 42 days only **11.7%** of the time versus **92.9%** for shallow states.


### Percentile rank, adaptive thresholds, and hysteresis on the strongest return feature per timeframe

| timeframe   |   feature_N |   eval_H |   raw_sign_delta_bps |   raw_sign_t |   rank_outer_delta_bps |   rank_outer_t | best_t_scheme   |   best_t_scheme_delta_bps |   best_t_scheme_t | best_stationarity_scheme   |   stationarity_dispersion_bps |   stationarity_sign_consistency |   hysteresis_flip_reduction_pct |   hysteresis_hit_delta_pp |   hysteresis_signed_return_delta_bps |
|:------------|------------:|---------:|---------------------:|-------------:|-----------------------:|---------------:|:----------------|--------------------------:|------------------:|:---------------------------|------------------------------:|--------------------------------:|--------------------------------:|--------------------------:|-------------------------------------:|
| 15m         |          42 |       48 |               15.034 |       10.319 |                 31.665 |         10.76  | trailing_365d   |                    31.24  |            11.342 | trailing_365d              |                        21.816 |                             1   |                          54.484 |                    -0.49  |                               -3.316 |
| 1h          |          12 |       12 |               14.994 |        5.137 |                 32.19  |          5.457 | trailing_365d   |                    36.221 |             6.558 | trailing_365d              |                        21.893 |                             1   |                          35.468 |                    -0.462 |                               -3.779 |
| 4h          |         168 |       24 |              144.07  |        9.009 |                140.97  |          4.793 | expanding       |                   174.371 |             6.133 | expanding                  |                       183.007 |                             0.5 |                          76.446 |                     1.239 |                               23.401 |
| 1d          |          24 |       24 |              506.511 |        4.558 |                866.581 |          4.885 | expanding       |                   994.113 |             5.882 | expanding                  |                       158.483 |                             1   |                          53.39  |                    -4.009 |                              -15.918 |


Structural conclusions:

- **Percentile-ranked outer states are cleaner than raw sign splits** on `15m`, `1h`, and `1d`; the spread roughly doubles in those cases. On `4h`, rank improves linearity (`IC`) but the raw and ranked spreads are of similar order.

- **Adaptive thresholds improve stationarity** relative to static warmup thresholds. Best choice is not universal: `trailing_365d` is the most stable scheme on `15m` and `1h`; `expanding` is the cleaner scheme on `4h` and `1d`.

- **Hysteresis materially reduces whipsaw** in every timeframe (flip-rate reduction: `15m -54.5%`, `1h -35.5%`, `4h -76.4%`, `1d -53.4%`). It clearly helps on the slower `4h` channel; on `15m`, `1h`, and `1d` it reduces churn but also dilutes the average signed return of the raw state.


## 3. Mean-Reversion & Gaps

### Strongest reversal / mean-reversion measurements

| channel         | timeframe   |   lookback_N |   best_H |   delta_bps |      t | direction      |
|:----------------|:------------|-------------:|---------:|------------:|-------:|:---------------|
| drawdown_depth  | 15m         |            6 |        3 |       3.155 |  4.139 | mean_reversion |
| range_position  | 15m         |            6 |        3 |      -1.697 | -3.43  | reversal       |
| return_momentum | 15m         |            6 |        6 |      -1.846 | -3.419 | reversal       |
| drawdown_depth  | 1h          |          168 |       48 |      28.139 |  2.673 | mean_reversion |


Reversal result: clean reversal is limited and localized. The clearest cases are `15m return_N=6` (short-horizon return reversal), `15m range_position N=6` (near-range-edge snapback), and `15m drawdown N=6` (brief bounce after local drawdown). Broader multi-timeframe structure is dominated by continuation, not reversal.


### D1 opening-gap predictiveness into intraday direction

Gap size in BTCUSDT spot is tiny at UTC day boundaries: median absolute D1 gap = **0.003 bps**, 95th percentile = **1.304 bps**, and **38.8%** of discovery days have exactly zero gap.

| target     |   n_nonzero_gaps |   pearson_corr |   pos_gap_mean_bps |   neg_gap_mean_bps |   delta_bps |   t_stat |   continuation_hit_rate |   signed_mean_bps |
|:-----------|-----------------:|---------------:|-------------------:|-------------------:|------------:|---------:|------------------------:|------------------:|
| ret_15m    |              782 |          0.146 |              3.847 |             -0.196 |       4.043 |    1.14  |                   0.527 |             1.942 |
| ret_1h     |              781 |          0.064 |              4.94  |             -3.112 |       8.052 |    1.299 |                   0.512 |             3.985 |
| ret_4h     |              782 |         -0.022 |              3.388 |            -15.542 |      18.931 |    1.789 |                   0.554 |             9.73  |
| day_oc_ret |              782 |          0.012 |             18.268 |              6.153 |      12.115 |    0.445 |                   0.509 |             5.527 |


Gap result: daily session-boundary gaps are effectively **noise** in continuous BTC spot. Across first `15m`, first `1h`, first `4h`, and full-day open-to-close returns, all gap tests remain weak (`|t| < 1.8`, correlations near zero).


## 4. Price/Momentum Channel Summary

### Strongest measured signals ranked by predictive content

| channel         | timeframe   |   lookback_N |   best_H |   delta_bps |      t | direction         |
|:----------------|:------------|-------------:|---------:|------------:|-------:|:------------------|
| range_position  | 15m         |           42 |       48 |      25.702 | 11.242 | continuation      |
| return_momentum | 15m         |           42 |       48 |      15.034 | 10.319 | continuation      |
| return_momentum | 4h          |          168 |       24 |     144.07  |  9.009 | continuation      |
| drawdown_depth  | 15m         |           42 |       48 |     -16.029 | -6.072 | trend_persistence |
| range_position  | 1h          |           12 |       12 |      23.156 |  5.681 | continuation      |
| range_position  | 4h          |          168 |       24 |     120.682 |  5.525 | continuation      |
| return_momentum | 1h          |           12 |       12 |      14.994 |  5.137 | continuation      |
| range_position  | 1d          |           24 |       24 |     639.97  |  4.627 | continuation      |
| return_momentum | 1d          |           24 |       24 |     506.511 |  4.558 | continuation      |
| drawdown_depth  | 1d          |           42 |       24 |    -525.945 | -3.067 | trend_persistence |
| drawdown_depth  | 1h          |          168 |       48 |      28.139 |  2.673 | mean_reversion    |
| drawdown_depth  | 4h          |          168 |       24 |     -50.53  | -1.973 | trend_persistence |


Summary judgment:

- Dominant structure is **continuation after multi-bar accumulation**, not next-bar drift.

- The cleanest price channels are **range position** and **medium/long-horizon momentum**, especially on `15m` and `4h`.

- **Short-horizon mean reversion exists**, but it is mostly confined to `15m` microstructure and does not generalize cleanly to higher timeframes.

- **Drawdown depth is mostly not a buy-the-dip channel** in discovery; deep drawdowns usually recover less often and underperform shallow near-high states, especially beyond the shortest intraday window.

- **Daily opening gaps are too small and too noisy** to matter as a primary price channel in 24/7 BTC spot.

- Channels that look materially noisy: `1h return N=24,168`; `4h return N=6`; `4h range position N=6,24`; `4h drawdown depth all measured N`; `1d return N=12,84`; `1d drawdown N=6,24`.
