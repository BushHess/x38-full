# D1b3 Measurements — Volume, Order Flow, and Calendar Channels

Historical snapshot usage: candidate-mining-only. No clean external OOS claim.  
Data source: admitted raw BTCUSDT snapshot from the fixed workspace under `/mnt/data/seed_discovery_workspace/raw`.  
Computation policy: no synthetic repair; all rolling, lagged, and forward calculations are blocked across detected time gaps.

## Method

- Calibration window: first available bar -> 2019-12-31 UTC
- Measurement window: 2020-01-01 -> 2023-06-30 UTC
- Timeframes: 15m, 1h, 4h, 1d
- Rolling windows tested: 6, 12, 24, 42, 84, 168 bars
- Forward horizons tested: 1, 3, 6, 12, 24, 42, 84, 168 bars
- Relative volume: `volume / trailing_mean(volume, W)`
- Taker imbalance: `2 * rolling_sum(taker_buy_base_vol, W) / rolling_sum(volume, W) - 1`
- Trade-count-beyond-volume base model: warmup OLS on `log1p(num_trades) ~ log1p(volume)`
- Excess trade surprise for forward tests: raw trade residual minus trailing mean residual over window `W`
- State tests:
  - volume regime: warmup 20/80 quantile split
  - volume spike: warmup 90th percentile vs rest
  - taker imbalance and trade surprise: positive vs negative sign split
- Reported spreads are in basis points of arithmetic forward return or forward absolute return.

## 1. Volume & Flow Channels

### 1.1 Clustering and persistence

| timeframe   |   logvol_acf_lag1 |   logvol_acf_lag6 |   logvol_acf_lag24 |   imbalance_acf_lag1 |   imbalance_acf_lag24 |   raw_trade_resid_mean_disc |
|:------------|------------------:|------------------:|-------------------:|---------------------:|----------------------:|----------------------------:|
| 15m         |             0.871 |             0.737 |              0.64  |                0.143 |                 0.021 |                       1.07  |
| 1h          |             0.853 |             0.692 |              0.693 |                0.194 |                 0.043 |                       1.064 |
| 4h          |             0.828 |             0.755 |              0.668 |                0.206 |                 0.071 |                       1.049 |
| 1d          |             0.859 |             0.767 |              0.576 |                0.222 |                 0.158 |                       1.029 |

Readout:
- Log-volume clustering is strong in every timeframe. Lag-1 ACF is 0.83 to 0.87; lag-24 ACF is still 0.58 to 0.69.
- Taker imbalance is much less persistent. Lag-1 ACF is only 0.14 to 0.22 and decays quickly.
- Raw trade residual level is not stationary in discovery: the discovery mean residual is about +1.03 to +1.07 log-units in every timeframe, so raw residual level is dominated by market-structure drift. Forward tests therefore use the de-drifted residual surprise, not the raw residual level.

### 1.2 Relative volume as a predictive state

| timeframe   |   dir_W |   dir_H |   dir_t |   dir_spread_bp |   mag_W |   mag_H |   mag_t |   mag_spread_bp |
|:------------|--------:|--------:|--------:|----------------:|--------:|--------:|--------:|----------------:|
| 15m         |     168 |      84 |    7.44 |           23.39 |     168 |       1 |   43.17 |           15.11 |
| 1h          |      84 |      24 |    4.34 |           28.84 |     168 |       1 |   22.33 |           28.65 |
| 4h          |      12 |       6 |    2.36 |           28    |     168 |       1 |   13.07 |           59.01 |
| 1d          |     168 |      84 |    2.03 |          817.13 |     168 |       3 |    4.99 |          205.38 |

Readout:
- Relative volume is first a **magnitude** channel, only secondarily a **direction** channel.
- Strongest directional effects:
  - 15m: W=168, H=84, t=7.44, spread=+23.39 bp
  - 1h: W=84, H=24, t=4.34, spread=+28.84 bp
  - 4h and 1d directional effects exist but are much weaker.
- Strongest magnitude effects are immediate or near-immediate:
  - 15m: W=168, H=1, t=43.17
  - 1h: W=168, H=1, t=22.33
  - 4h: W=168, H=1, t=13.07
  - 1d: W=168, H=3, t=4.99

### 1.3 Taker flow / order-flow imbalance

| timeframe   |   cont_W |   cont_H |   cont_t |   cont_spread_bp |   rev_W |   rev_H |   rev_t |   rev_spread_bp |   mag_W |   mag_H |   mag_t |   mag_spread_bp |   corr_W |   corr_H |   corr |
|:------------|---------:|---------:|---------:|-----------------:|--------:|--------:|--------:|----------------:|--------:|--------:|--------:|----------------:|---------:|---------:|-------:|
| 15m         |       84 |       12 |     4.1  |             3.2  |     168 |     168 |   -9.97 |          -31.16 |     168 |       1 |   -8.11 |           -1.51 |       42 |       42 |   0.03 |
| 1h          |       84 |       84 |     5.19 |            50.94 |      84 |     168 |   -9.01 |         -117.69 |     168 |     168 |  -10.85 |          -90.56 |      168 |      168 |  -0.09 |
| 4h          |       84 |       24 |     2.7  |            54.67 |     168 |     168 |  -11.86 |         -667.63 |      84 |     168 |  -20.44 |         -694.63 |       42 |       42 |  -0.09 |
| 1d          |       12 |        6 |     1.56 |            93.5  |      12 |     168 |  -15.85 |        -5805.02 |      42 |     168 |  -20.61 |        -5939.65 |       84 |      168 |  -0.6  |

Interpretation:
- `cont_*` = strongest **continuation** pocket where positive imbalance outperforms negative imbalance.
- `rev_*` = strongest **reversal** pocket where positive imbalance underperforms negative imbalance.
- `mag_*` = strongest forward **magnitude** split for positive vs negative imbalance.

Readout:
- Taker flow is **not** a simple momentum channel.
- 15m and 1h have a real continuation pocket:
  - 15m: W=84, H=12, t=4.10, spread=+3.20 bp
  - 1h: W=84, H=84, t=5.19, spread=+50.94 bp
- The dominant effect, however, is **long-horizon reversal**:
  - 15m: W=168, H=168, t=-9.97, spread=-31.16 bp
  - 1h: W=84, H=168, t=-9.01, spread=-117.69 bp
  - 4h: W=168, H=168, t=-11.86, spread=-667.63 bp
  - 1d: W=12, H=168, t=-15.85, spread=-5805.02 bp
- On 4h and 1d, the continuation side is weak; the usable structure is overwhelmingly contrarian at long horizons.
- Strongest linear association is also long-horizon and mostly negative, especially on 1d (`corr=-0.597` at W=84, H=168).

### 1.4 Volume spikes: do they lead moves or follow them?

| timeframe   |   future_W |   future_H |   future_t |   future_spread_bp |   past_W |   past_H |   past_t |   past_spread_bp |   past_to_future_abs_t_ratio |
|:------------|-----------:|-----------:|-----------:|-------------------:|---------:|---------:|---------:|-----------------:|-----------------------------:|
| 15m         |        168 |          1 |      31.68 |              17.22 |      168 |        3 |    71.86 |            72.77 |                         2.27 |
| 1h          |        168 |          1 |      14.88 |              28.95 |       84 |        3 |    39.14 |           132.42 |                         2.63 |
| 4h          |        168 |          1 |       8.74 |              52.92 |      168 |        3 |    21.24 |           239.49 |                         2.43 |
| 1d          |        168 |        168 |      -5    |           -2660.93 |       42 |        3 |     9.73 |           831.96 |                         1.95 |

Readout:
- Volume spikes mostly **follow** price moves rather than cleanly lead them.
- The backward-looking magnitude link is about 1.95x to 2.63x stronger than the forward-looking magnitude link in every timeframe.
- Intraday frames still show a real future-magnitude effect right after spikes:
  - 15m: W=168, H=1, t=31.68, spread=+17.22 bp
  - 1h: W=168, H=1, t=14.88, spread=+28.95 bp
  - 4h: W=168, H=1, t=8.74, spread=+52.92 bp
- Daily is different: the strongest forward effect is **negative** (`W=168, H=168, t=-5.00`), so large daily volume spikes behave more like late-event exhaustion than future expansion.

### 1.5 Does `num_trades` carry information beyond volume?

| timeframe   |   warmup_beta |   warmup_corr_lv_lt |   dir_W |   dir_H |   dir_t |   dir_spread_bp |   mag_W |   mag_H |   mag_t |   mag_spread_bp |
|:------------|--------------:|--------------------:|--------:|--------:|--------:|----------------:|--------:|--------:|--------:|----------------:|
| 15m         |          0.95 |                0.95 |     168 |      84 |   -7.8  |          -15.43 |     168 |       1 |  -31.52 |           -5.81 |
| 1h          |          0.95 |                0.96 |     168 |     168 |   -7.49 |          -84.24 |     168 |       1 |  -16.88 |          -12.27 |
| 4h          |          0.96 |                0.97 |     168 |     168 |    4.41 |          219.95 |     168 |       1 |   -8.91 |          -22.58 |
| 1d          |          0.98 |                0.97 |     168 |     168 |    9.14 |         4724.41 |     168 |     168 |    7.67 |         3419.05 |

Readout:
- In warmup, `num_trades` is already almost fully explained by `volume`:
  - slope ≈ 0.95 to 0.98
  - correlation ≈ 0.95 to 0.97
- Raw residual level drifts hard in discovery and is not a clean state variable.
- After de-drifting, excess trade surprise is measurable:
  - 15m and 1h: contrarian at medium/long horizons, strongest at W=168
    - 15m: H=84, t=-7.80, spread=-15.43 bp
    - 1h: H=168, t=-7.49, spread=-84.24 bp
  - 4h and 1d: continuation at long horizon
    - 4h: W=168, H=168, t=4.41, spread=+219.95 bp
    - 1d: W=168, H=168, t=9.14, spread=+4724.41 bp
- For immediate magnitude, excess trade surprise is negative on intraday frames:
  - 15m: W=168, H=1, t=-31.52
  - 1h: W=168, H=1, t=-16.88
  - 4h: W=168, H=1, t=-8.91

## 2. Calendar Effects

Warmup-selected best/worst buckets evaluated on discovery, UTC calendar.

| timeframe   | weekday_dir   |   weekday_dir_t |   weekday_dir_spread_bp | weekday_mag   |   weekday_mag_t |   weekday_mag_spread_bp | hour_dir     | hour_dir_t   | hour_dir_spread_bp   | hour_mag     | hour_mag_t   | hour_mag_spread_bp   |
|:------------|:--------------|----------------:|------------------------:|:--------------|----------------:|------------------------:|:-------------|:-------------|:---------------------|:-------------|:-------------|:---------------------|
| 15m         | Fri vs Thu    |            0.69 |                    0.33 | Fri vs Sat    |           17.01 |                    5.97 | 21 vs 02 UTC | 2.21         | 1.93                 | 15 vs 03 UTC | 11.23        | 6.85                 |
| 1h          | Fri vs Thu    |            1.38 |                    2.51 | Fri vs Sat    |           10.94 |                   13.97 | 21 vs 02 UTC | 1.75         | 4.82                 | 23 vs 17 UTC | 4.70         | 11.07                |
| 4h          | Fri vs Sat    |            0.93 |                    5.32 | Fri vs Sat    |            6.32 |                   28.26 | 12 vs 20 UTC | 0.64         | 3.68                 | 08 vs 00 UTC | 7.53         | 33.62                |
| 1d          | Thu vs Wed    |            0.46 |                   20.96 | Wed vs Fri    |            4.61 |                  142.26 | NA           | NA           | NA                   | NA           | NA           | NA                   |

Readout:
- **Directional** calendar effects are mostly weak/noisy.
  - Weekday direction t-stats are 0.46 to 1.38 across 1h/4h/1d, and only 2.21 at best on 15m hour-of-day.
  - There is no strong stand-alone weekday direction edge here.
- **Magnitude** seasonality is persistent:
  - 15m weekday magnitude: Fri vs Sat, t=17.01
  - 15m hour magnitude: 15 vs 03 UTC, t=11.23
  - 1h weekday magnitude: Fri vs Sat, t=10.94
  - 4h hour magnitude: 08 vs 00 UTC, t=7.53
  - 1d weekday magnitude: Wed vs Fri, t=4.61
- Bottom line: UTC calendar structure is much more useful for expected **activity / magnitude** than for signed return direction.

## 3. Volume/Flow Channel Summary

### Strongest forward **directional** signals

| channel             | timeframe   |   window |   horizon |      t |   spread_bp | interpretation                             |
|:--------------------|:------------|---------:|----------:|-------:|------------:|:-------------------------------------------|
| taker_flow_negative | 1d          |       12 |       168 | -15.85 |    -5805.02 | pos imbalance vs neg imbalance             |
| taker_flow_negative | 4h          |      168 |       168 | -11.86 |     -667.63 | pos imbalance vs neg imbalance             |
| taker_flow_negative | 15m         |      168 |       168 |  -9.97 |      -31.16 | pos imbalance vs neg imbalance             |
| trade_surprise      | 1d          |      168 |       168 |   9.14 |     4724.41 | positive vs negative excess-trade residual |
| taker_flow_negative | 1h          |       84 |       168 |  -9.01 |     -117.69 | pos imbalance vs neg imbalance             |
| trade_surprise      | 15m         |      168 |        84 |  -7.8  |      -15.43 | positive vs negative excess-trade residual |
| trade_surprise      | 1h          |      168 |       168 |  -7.49 |      -84.24 | positive vs negative excess-trade residual |
| volume_regime       | 15m         |      168 |        84 |   7.44 |       23.39 | high rel volume vs low rel volume          |
| taker_flow_positive | 1h          |       84 |        84 |   5.19 |       50.94 | pos imbalance vs neg imbalance             |
| trade_surprise      | 4h          |      168 |       168 |   4.41 |      219.95 | positive vs negative excess-trade residual |
| volume_regime       | 1h          |       84 |        24 |   4.34 |       28.84 | high rel volume vs low rel volume          |
| taker_flow_positive | 15m         |       84 |        12 |   4.1  |        3.2  | pos imbalance vs neg imbalance             |

### Strongest forward **magnitude** signals

| channel                 | timeframe   |   window |   horizon |      t |   spread_bp | interpretation                             |
|:------------------------|:------------|---------:|----------:|-------:|------------:|:-------------------------------------------|
| volume_regime           | 15m         |      168 |         1 |  43.17 |       15.11 | high rel volume vs low rel volume          |
| volume_spike_future_mag | 15m         |      168 |         1 |  31.68 |       17.22 | spike vs rest future magnitude             |
| trade_surprise          | 15m         |      168 |         1 | -31.52 |       -5.81 | positive vs negative excess-trade residual |
| volume_regime           | 1h          |      168 |         1 |  22.33 |       28.65 | high rel volume vs low rel volume          |
| taker_flow_mag          | 1d          |       42 |       168 | -20.61 |    -5939.65 | pos imbalance vs neg imbalance             |
| taker_flow_mag          | 4h          |       84 |       168 | -20.44 |     -694.63 | pos imbalance vs neg imbalance             |
| calendar_weekday_mag    | 15m         |        1 |         1 |  17.01 |        5.97 | best warmup weekday vs worst               |
| trade_surprise          | 1h          |      168 |         1 | -16.88 |      -12.27 | positive vs negative excess-trade residual |
| volume_spike_future_mag | 1h          |      168 |         1 |  14.88 |       28.95 | spike vs rest future magnitude             |
| volume_regime           | 4h          |      168 |         1 |  13.07 |       59.01 | high rel volume vs low rel volume          |
| calendar_hour_mag       | 15m         |        1 |         1 |  11.23 |        6.85 | best warmup UTC hour vs worst              |
| calendar_weekday_mag    | 1h          |        1 |         1 |  10.94 |       13.97 | best warmup weekday vs worst               |

## Bottom line

Channels with measurable exploitable signal:
- **Relative volume**: strong and stable for future magnitude; moderate positive direction on 15m/1h.
- **Taker imbalance**: mixed continuation at 15m/1h, but the dominant effect is long-horizon reversal, especially on 4h/1d.
- **Volume spikes**: useful for near-term future magnitude, but they react even more strongly to already-realized past moves.
- **Excess trade surprise beyond volume**: only usable after de-drifting; contrarian on 15m/1h, continuation on 4h/1d.
- **Calendar**: mostly a magnitude channel, not a direction channel.

Channels that are mostly noise or unstable:
- Raw trade residual level without de-drifting.
- Stand-alone weekday/time-of-day direction buckets.
- Any claim that taker flow is a universal continuation signal across horizons.
- Any claim that volume spikes generically lead breakouts more than they follow realized moves.
