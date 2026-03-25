# D1b2 Measurements — Volatility & Regime Channels
Scope: warmup (`first available bar -> 2019-12-31 UTC`) used only for calibration; discovery (`2020-01-01 -> 2023-06-30 UTC`) used for measurement. Holdout and reserve_internal were not used. Historical snapshot remains candidate-mining-only; no clean external OOS claim is made here.
Definitions used here:
- `rv_N = rolling_std(log(close_t / close_{t-1}), N)`
- `range_vol_N = rolling_mean((high - low) / close, N)`
- `zret_N = log(close_t / close_{t-N}) / (rv_N * sqrt(N))`
- `compression` = joint low-vol state where both `rv_N` and `range_vol_N` are below their warmup 20th percentiles; episode stats are reported at `N=24`, while the strongest long-vs-short compression signal is searched across all tested `N` and forward horizons.
- `efficiency_24 = abs(log(close_t / close_{t-24})) / rolling_sum(abs(log_ret_1), 24)`
- Regime labels are measurement-only labels: `crisis` = high `rv_24` (warmup top decile) + deep negative `ret_24` (warmup bottom decile); `euphoric` = high `rv_24` + deep positive `ret_24`; `trend` = high `efficiency_24` excluding crisis/euphoric; `chop` = low `efficiency_24` excluding crisis/euphoric; `neutral` = remainder.
- Tail thresholds use the most extreme warmup quantile in `{1%, 2%, 2.5%, 5%}` that still leaves at least 20 discovery events on each side.

## 1. Volatility Channels
### 1.1 Volatility clustering
| timeframe   |   absret_ac_lag1 |   absret_ac_lag24 |   rv24_ac_lag1 |   rv24_ac_lag24 | rv24_half_life_lt_0_5   | read                                |
|:------------|-----------------:|------------------:|---------------:|----------------:|:------------------------|:------------------------------------|
| 15m         |            0.374 |             0.198 |          0.991 |           0.605 | >48                     | very persistent intraday clustering |
| 1h          |            0.281 |             0.161 |          0.989 |           0.575 | 48                      | persistent clustering               |
| 4h          |            0.216 |             0.148 |          0.988 |           0.576 | 48                      | persistent clustering               |
| 1d          |            0.13  |             0.051 |          0.977 |           0.19  | 24                      | clustering present but faster decay |

Interpretation:
- Volatility clustering is strong on every timeframe.
- Absolute one-bar returns cluster materially even at lag 24 on intraday frames.
- Realized volatility itself is much more persistent than absolute returns; `rv_24` remains above 0.5 autocorrelation through 48 bars on 15m/1h/4h, and through 24 bars on 1d.

### 1.2 Volatility-normalized returns (`zret_N`)
| timeframe   |   N |   H |   norm_delta_bps |   norm_t |   norm_valid_years |   norm_sign_share |   raw_delta_bps_same_NH |   raw_t_same_NH |   raw_valid_years |   raw_sign_share |
|:------------|----:|----:|-----------------:|---------:|-------------------:|------------------:|------------------------:|----------------:|------------------:|-----------------:|
| 15m         |  42 |  48 |           36.896 |   15.399 |                  4 |               1   |                  30.626 |          10.486 |                 4 |                1 |
| 1h          |  12 |  12 |           36.915 |    7.777 |                  4 |               1   |                  31.043 |           5.313 |                 4 |                1 |
| 4h          | 168 |  48 |          310.762 |    8.406 |                  4 |               0.5 |                 305.14  |           7.05  |                 2 |                1 |
| 1d          |  12 |  48 |         1454.61  |    5.036 |                  4 |               0.5 |                1944.28  |           5.877 |                 2 |                1 |

Normalization verdict:
- **15m, 1h**: clear improvement. Normalization raises pooled discovery t-stat and keeps full 4-year sign consistency.
- **4h**: normalization improves pooled discrimination and year coverage versus raw same-`N/H` states, but the strongest extreme-state measurements still show sign drift across 2022-2023. This is usable as pooled discovery signal, not as a stationarity fix.
- **1d**: normalization broadens coverage, but it does **not** stabilize direction across years. Daily extreme normalized states remain nonstationary.

### 1.3 Realized-vol and range-vol predictive content
| timeframe   |   rv_dir_N |   rv_dir_H |   rv_dir_delta_bps |   rv_dir_t |   rg_dir_N |   rg_dir_H |   rg_dir_delta_bps |   rg_dir_t |   rv_mag_N |   rv_mag_H |   rv_mag_delta_abs_bps |   rv_mag_t |   rg_mag_N |   rg_mag_H |   rg_mag_delta_abs_bps |   rg_mag_t | rv_long_horizon_inversion              | read                                                                              |
|:------------|-----------:|-----------:|-------------------:|-----------:|-----------:|-----------:|-------------------:|-----------:|-----------:|-----------:|-----------------------:|-----------:|-----------:|-----------:|-----------------------:|-----------:|:---------------------------------------|:----------------------------------------------------------------------------------|
| 15m         |         42 |         48 |             20.841 |      4.852 |         42 |         48 |             15.38  |      3.66  |         84 |         12 |                139.576 |     74.157 |          6 |         12 |                127.87  |     78.932 |                                        | high vol lifts short-horizon magnitude; direction appears only multi-bar          |
| 1h          |         24 |         24 |             55.214 |      4.949 |         24 |         48 |             60.827 |      4.304 |         24 |          3 |                126.957 |     35.454 |         24 |          3 |                139.052 |     40.116 |                                        | high vol lifts short-horizon magnitude; direction appears only multi-bar          |
| 4h          |         84 |         48 |            449.113 |      7.915 |         84 |         48 |            254.529 |      4.375 |         24 |          1 |                128.555 |     18.497 |          6 |          1 |                140.583 |     20.271 |                                        | high vol aligns with stronger medium-term up move                                 |
| 1d          |         24 |         48 |           2208.56  |      6.926 |         42 |         48 |           1636.15  |      6.173 |         24 |          1 |                192.785 |      5.675 |         42 |          3 |                280.98  |      6.71  | N=168, H=48, Δabs=-1616.4 bps, t=-9.34 | short-horizon high vol lifts magnitude; low-vol states dominate very long horizon |

Read:
- High current volatility strongly predicts **future magnitude** on short/medium horizons in every timeframe.
- Directional content exists too, but it is multi-bar rather than next-bar. High-vol states skew to higher forward returns, strongest on 4h/1d, consistent with post-shock rebound and trend-expansion states rather than a pure volatility premium.
- Daily exception: very long-horizon magnitude inverts. Low-vol daily states eventually exceed high-vol daily states in future magnitude (`rv_168 -> H48`), which overlaps with the compression result below.

### 1.4 Compression
| timeframe   |   joint_comp_share_pct_N24 |   episodes_N24 |   median_len_N24 |   p95_len_N24 |   max_len_N24 |   best_signal_N |   best_signal_H |   delta_abs_bps_long_vs_short |       t | read                                                     |
|:------------|---------------------------:|---------------:|-----------------:|--------------:|--------------:|----------------:|----------------:|------------------------------:|--------:|:---------------------------------------------------------|
| 15m         |                     17.725 |            832 |              9   |        102.8  |           483 |               6 |               1 |                        -5.709 | -22.296 | longer compression suppresses near-term future magnitude |
| 1h          |                     15.762 |            210 |              9.5 |         77.3  |           525 |              42 |              12 |                       -63.439 | -12.639 | longer compression suppresses near-term future magnitude |
| 4h          |                     16.721 |             67 |              6   |         95.4  |           168 |              12 |              48 |                      1014.92  |  12.239 | longer compression precedes magnitude expansion          |
| 1d          |                     21.848 |             18 |              7   |         41.85 |            58 |              24 |              12 |                       847.026 |   8.155 | longer compression precedes magnitude expansion          |

Compression verdict:
- **15m, 1h**: longer compression does **not** precede expansion. It suppresses near-term future magnitude further. Intraday quiet tends to stay quiet.
- **4h, 1d**: longer compression **does** precede larger future absolute moves. This is the clean compression/expansion behavior in the snapshot.
- A simple first-bar-after-compression-release test was weak to negative across frames. The usable information is in **compression duration**, not in the first release bar itself.

## 2. Regime Structure
### 2.1 Regime identification and regime spreads
| timeframe   |   trend_share_pct |   chop_share_pct |   crisis_share_pct |   euphoric_share_pct |   trend_vs_chop_H |   trend_vs_chop_delta_bps |   trend_vs_chop_t |   crisis_H | crisis_delta_bps   | crisis_t   |   euphoric_H | euphoric_delta_bps   | euphoric_t   | read                                                                     |
|:------------|------------------:|-----------------:|-------------------:|---------------------:|------------------:|--------------------------:|------------------:|-----------:|:-------------------|:-----------|-------------:|:---------------------|:-------------|:-------------------------------------------------------------------------|
| 15m         |            32.738 |           32.206 |              1.427 |                1.039 |                12 |                     4.3   |             4.82  |         24 | 58.663             | 5.719      |           12 | -45.004              | -6.159       | trend beats chop; crisis rebounds; euphoric states fade                  |
| 1h          |            31.77  |           33.811 |              1.215 |                0.722 |                12 |                     5.901 |             1.701 |         24 | 194.357            | 5.410      |           24 | -147.712             | -4.687       | trend/chop weak; crisis rebounds; euphoric states fade                   |
| 4h          |            29.174 |           35.27  |              1.149 |                0.6   |                24 |                   -19.669 |            -0.926 |         48 | 304.661            | 2.308      |           24 | 394.854              | 4.304        | trend/chop weak; crisis sparse but rebounds later; euphoric mixed/sparse |
| 1d          |            27.408 |           36.335 |              1.488 |                0     |                12 |                   123.539 |             1.386 |        nan |                    |            |          nan |                      |              | trend/chop weak; crisis/euphoric too sparse for reliable direction       |

Regime verdict:
- **15m**: trend beats chop; crisis states bounce; euphoric states fade. This is the cleanest regime surface in the set.
- **1h**: crisis/euphoric regimes remain informative, but trend-vs-chop is weak.
- **4h**: trend-vs-chop is weak; crisis and euphoric states exist but are sparse and mixed. Directional inference is less robust than on intraday frames.
- **1d**: crisis/euphoric counts are too sparse for reliable directional conclusions.

### 2.2 Tail behavior
| timeframe   | tail_quantile_used   | dir_event   |   dir_H |   dir_delta_bps |   dir_t | dir_read                                 | abs_event    |   abs_H |   abs_delta_bps |   abs_t |
|:------------|:---------------------|:------------|--------:|----------------:|--------:|:-----------------------------------------|:-------------|--------:|----------------:|--------:|
| 15m         | 1%                   | neg_tail    |      24 |         153.925 |   7.057 | downside tail rebound                    | neg_tail_abs |       1 |          88.243 |  13.822 |
| 1h          | 1%                   | neg_tail    |      24 |         256.414 |   3.873 | downside tail rebound                    | neg_tail_abs |       1 |         131.228 |   6.643 |
| 4h          | 1%                   | neg_tail    |       6 |         281.485 |   2.744 | downside tail rebound                    | neg_tail_abs |       1 |         134.459 |   4.026 |
| 1d          | 5%                   | pos_vs_neg  |       3 |        -264.972 |  -1.966 | negative tails outperform positive tails | neg_tail_abs |       1 |         159.514 |   2.106 |

Tail verdict:
- The consistent directional tail event is **downside tail rebound**, not upside tail continuation.
- 15m and 1h downside tails show the clearest forward recovery. 4h still shows it, but weaker.
- Daily directional tail behavior is weak/noisy even after relaxing to 5% tails. What remains measurable on 1d is mainly the **magnitude lift** after downside tails.

### 2.3 Which channels are signal vs noise
| channel                                  | 15m                          | 1h                               | 4h                             | 1d                             |
|:-----------------------------------------|:-----------------------------|:---------------------------------|:-------------------------------|:-------------------------------|
| volatility clustering                    | strong                       | strong                           | strong                         | present                        |
| vol-normalized return state              | strong                       | strong                           | mixed                          | mixed/nonstationary            |
| vol/range-vol -> direction               | strong                       | strong                           | strong                         | strong, but long-horizon drift |
| compression duration -> future magnitude | strong, but dampening        | strong, but dampening            | strong expansion               | strong expansion               |
| trend/chop regime                        | measurable                   | weak/noise                       | weak/noise                     | weak/noise                     |
| crisis/euphoric tail regimes             | strong                       | strong                           | mixed, sparse                  | too sparse                     |
| one-bar tail direction                   | strong downside-tail rebound | measurable downside-tail rebound | moderate downside-tail rebound | weak/noise                     |


## 3. Volatility/Regime Channel Summary
### 3.1 Strongest directional signals (pooled discovery ranking)
|   rank | timeframe   | channel                         |   N |   H |   delta_bps |      t | note                        |
|-------:|:------------|:--------------------------------|----:|----:|------------:|-------:|:----------------------------|
|      1 | 15m         | vol-normalized return state     |  42 |  48 |      36.896 | 15.399 |                             |
|      2 | 1d          | vol-normalized return state     | 168 |  48 |    3072.15  | 10.929 | pooled strong; yearly drift |
|      3 | 4h          | vol-normalized return state     | 168 |  48 |     310.762 |  8.406 | pooled strong; yearly drift |
|      4 | 4h          | realized-vol level -> direction |  84 |  48 |     449.113 |  7.915 |                             |
|      5 | 1h          | vol-normalized return state     |  12 |  12 |      36.915 |  7.777 |                             |
|      6 | 15m         | tail event direction            | nan |  24 |     153.925 |  7.057 |                             |
|      7 | 1d          | realized-vol level -> direction |  24 |  48 |    2208.56  |  6.926 |                             |
|      8 | 1d          | range-vol level -> direction    |  42 |  48 |    1636.15  |  6.173 |                             |
|      9 | 15m         | euphoric vs neutral regime      | nan |  12 |     -45.004 | -6.159 |                             |
|     10 | 15m         | crisis vs neutral regime        | nan |  24 |      58.663 |  5.719 |                             |
|     11 | 1h          | crisis vs neutral regime        | nan |  24 |     194.357 |  5.41  |                             |
|     12 | 1h          | realized-vol level -> direction |  24 |  24 |      55.214 |  4.949 |                             |

### 3.2 Strongest magnitude/state signals (pooled discovery ranking)
|   rank | timeframe   | channel                         |   N |   H |   delta_abs_bps |       t | note   |
|-------:|:------------|:--------------------------------|----:|----:|----------------:|--------:|:-------|
|      1 | 15m         | range-vol level -> magnitude    |   6 |  12 |         127.87  |  78.932 |        |
|      2 | 15m         | realized-vol level -> magnitude |  84 |  12 |         139.576 |  74.157 |        |
|      3 | 1h          | range-vol level -> magnitude    |  24 |   3 |         139.052 |  40.116 |        |
|      4 | 1h          | realized-vol level -> magnitude |  24 |   3 |         126.957 |  35.454 |        |
|      5 | 15m         | crisis vs neutral magnitude     | nan |  12 |         169.772 |  26.192 |        |
|      6 | 15m         | long vs short compression       |   6 |   1 |          -5.709 | -22.296 |        |
|      7 | 4h          | range-vol level -> magnitude    |   6 |   1 |         140.583 |  20.271 |        |
|      8 | 4h          | realized-vol level -> magnitude |  24 |   1 |         128.555 |  18.497 |        |
|      9 | 15m         | tail event magnitude            | nan |   1 |          88.243 |  13.822 |        |
|     10 | 1h          | long vs short compression       |  42 |  12 |         -63.439 | -12.639 |        |
|     11 | 1h          | crisis vs neutral magnitude     | nan |   3 |         186.783 |  12.438 |        |
|     12 | 4h          | long vs short compression       |  12 |  48 |        1014.92  |  12.239 |        |

Summary judgment:
- The volatility surface carries **very strong state information about future magnitude** on every timeframe. That is the cleanest result in D1b2.
- The cleanest **directional** volatility/regime signals are: 15m/1h vol-normalized return states; 4h realized-vol direction; 15m/1h crisis rebound; and 15m downside-tail rebound.
- Intraday compression is not a breakout state here. Higher-timeframe compression is.
- Trend/chop as a standalone regime discriminator is mostly weak outside 15m.
- Daily extreme-state measurements are the least stationary part of this pass; they can look strong in pooled discovery but drift materially across years.
