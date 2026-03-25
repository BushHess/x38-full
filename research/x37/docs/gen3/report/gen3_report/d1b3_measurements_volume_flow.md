# D1b3 — Volume, Order Flow, and Calendar Measurements

Saved under frozen constitution. Warmup was used for calibration only. Measurement used discovery only. Holdout and reserve were not touched. Historical snapshot remains candidate-mining-only; no clean external OOS claim is made here.

## Measurement setup

- Volume state: `z_N(log(1 + volume))` with warmup-calibrated outer-state thresholds.
- Taker imbalance: `imbalance = 2 * (taker_buy_base_vol / volume) - 1`.
  - Raw sign state: `mean_N(imbalance) > 0` vs `< 0`.
  - Extreme standardized state: `z_N(mean_N(imbalance))`, warmup-calibrated outer states.
- Trade-density beyond volume: `z_N(log(1 + num_trades / volume))`.
- Calendar effect: discovery intrabar return `close / open - 1` by UTC weekday and UTC time bucket.

## 1. Volume & Flow Channels

### Volume clustering, regime persistence, and predictive content

| timeframe   |   vol acf(1) |   vol acf(ref lag) |   vol acf(ref) | best directional state          | best magnitude state               | spike lead/lag                                                        | state persistence                                                       |
|:------------|-------------:|-------------------:|---------------:|:--------------------------------|:-----------------------------------|:----------------------------------------------------------------------|:------------------------------------------------------------------------|
| 15m         |        0.871 |                 96 |          0.643 | N=24, H=24, Δ=7.3 bps, t=4.29   | N=168, H=1, Δabs=14.6 bps, t=43.61 | N=168, H=1, future vs all +13.8 bps (t=28.05), future-past -17.4 bps  | N=168: P(high→high) 59.9% vs base 20.6%; P(low→low) 55.4% vs base 20.5% |
| 1h          |        0.853 |                 24 |          0.693 | N=84, H=24, Δ=21.2 bps, t=3.28  | N=168, H=1, Δabs=28.2 bps, t=23.53 | N=168, H=1, future vs all +24.2 bps (t=13.88), future-past -48.1 bps  | N=168: P(high→high) 55.8% vs base 20.3%; P(low→low) 56.5% vs base 20.5% |
| 4h          |        0.828 |                  6 |          0.755 | N=12, H=6, Δ=18.1 bps, t=1.43   | N=168, H=1, Δabs=60.5 bps, t=12.60 | N=168, H=1, future vs all +48.7 bps (t=7.21), future-past -89.8 bps   | N=168: P(high→high) 47.9% vs base 17.6%; P(low→low) 56.8% vs base 23.3% |
| 1d          |        0.859 |                  7 |          0.803 | N=84, H=48, Δ=606.7 bps, t=2.04 | N=168, H=3, Δabs=183.2 bps, t=4.81 | N=168, H=3, future vs all +136.8 bps (t=2.80), future-past -353.2 bps | N=168: P(high→high) 63.8% vs base 22.1%; P(low→low) 69.4% vs base 30.2% |

Interpretation:
- Volume clustering is strong on every timeframe: lag-1 log-volume autocorrelation stays in the **0.83–0.87** range.
- High/low standardized volume states persist far above unconditional frequency. Example: on 15m with `N=168`, `P(high→high)=59.9%` versus a base high-state frequency of `20.6%`; on 1d with `N=168`, `P(low→low)=69.4%` versus a base low-state frequency of `30.2%`.
- High relative volume is primarily a **magnitude** channel. Directional content is material on **15m** and modest on **1h**; it is weak/noisy on **4h** and **1d**.
- Volume spikes mostly **follow** price moves rather than lead them (`future-past` is negative on every timeframe), but they still leave a measurable **aftershock** in future return magnitude.

### Taker flow and participation

| timeframe   |   imbalance acf(1) | raw sign state                               | extreme standardized state               | participation context                                 |
|:------------|-------------------:|:---------------------------------------------|:-----------------------------------------|:------------------------------------------------------|
| 15m         |              0.143 | N=168, H=48, buy<sell, Δ=-10.9 bps, t=-5.99  | N=24, H=12, hi<lo, Δ=-4.7 bps, t=-3.83   | mid_vol, N=168, H=48, buy<sell, Δ=-13.9 bps, t=-5.92  |
| 1h          |              0.194 | N=168, H=48, buy<sell, Δ=-58.9 bps, t=-6.99  | N=168, H=48, hi>lo, Δ=102.8 bps, t=10.84 | low_vol, N=168, H=48, buy<sell, Δ=-70.8 bps, t=-4.82  |
| 4h          |              0.206 | N=24, H=48, buy<sell, Δ=-266.6 bps, t=-8.69  | N=24, H=24, hi>lo, Δ=187.3 bps, t=7.15   | mid_vol, N=84, H=48, buy<sell, Δ=-301.1 bps, t=-6.63  |
| 1d          |              0.222 | N=42, H=48, buy<sell, Δ=-2088.9 bps, t=-8.38 | N=84, H=12, hi>lo, Δ=633.1 bps, t=5.29   | mid_vol, N=84, H=48, buy<sell, Δ=-2831.3 bps, t=-9.14 |

Interpretation:
- Raw imbalance itself is only modestly persistent (`acf(1)` roughly **0.14–0.22**).
- Raw buy-dominant vs sell-dominant state is **not** a simple continuation cue. At longer horizons it is often **contrarian**, especially on **1h/4h/1d**.
- The cleaner directional signal is **extreme standardized imbalance**:
  - **1h**: `N=168, H=48`, high vs low extreme flow `+102.8 bps`, `t=10.84`.
  - **4h**: `N=24, H=24`, high vs low extreme flow `+187.4 bps`, `t=7.15`.
  - **1d**: `N=84, H=12`, high vs low extreme flow `+633.1 bps`, `t=5.29`.
- Participation context is **not breakout-like**. Ordinary buy-dominance under low/mid volume usually does **not** improve; on longer horizons it often underperforms sell-dominance. The exception is **15m low-volume** context at `H=12–48`, where buy-dominance is modestly better than sell-dominance.

### Trade count beyond volume

| timeframe   |   trade-density acf(1) | best directional                        | best magnitude                              |
|:------------|-----------------------:|:----------------------------------------|:--------------------------------------------|
| 15m         |                  0.887 | N=168, H=24, hi<lo, Δ=-6.3 bps, t=-3.87 | N=168, H=1, hi<lo, Δabs=-10.1 bps, t=-31.76 |
| 1h          |                  0.892 | N=84, H=24, hi<lo, Δ=-29.6 bps, t=-4.53 | N=168, H=1, hi<lo, Δabs=-22.6 bps, t=-17.81 |
| 4h          |                  0.92  | N=24, H=48, hi<lo, Δ=-86.2 bps, t=-2.38 | N=168, H=1, hi<lo, Δabs=-45.7 bps, t=-9.75  |
| 1d          |                  0.944 | N=42, H=24, hi>lo, Δ=667.7 bps, t=3.99  | N=168, H=48, hi>lo, Δabs=786.3 bps, t=4.53  |

Interpretation:
- Trade-density (`num_trades / volume`) is highly persistent.
- On **15m / 1h / 4h**, high trade-density is mostly a **compression** state: it predicts **lower future magnitude**, and on 15m/1h also weaker medium-horizon returns.
  - 15m: `N=168, H=1`, high trade-density lowers future magnitude by **10.1 bps**, `t=-31.76`.
  - 1h: `N=168, H=1`, lowers future magnitude by **22.6 bps**, `t=-17.81`.
  - 4h: `N=168, H=1`, lowers future magnitude by **45.7 bps**, `t=-9.75`.
- On **1d**, the sign flips: high trade-density predicts **stronger** 24–48 day continuation and higher future magnitude.
  - 1d directional: `N=42, H=24`, `+667.7 bps`, `t=3.99`.
  - 1d magnitude: `N=168, H=48`, `+786.3 bps`, `t=4.53`.

## 2. Calendar Effects

| timeframe   | day-of-week                 | time-of-day / session                   | weekend effect                     |
|:------------|:----------------------------|:----------------------------------------|:-----------------------------------|
| 15m         | Wed>Thu, Δ=0.6 bps, t=1.26  | 21:00 UTC>23:00 UTC, Δ=2.2 bps, t=2.84  | weekend-weekday -0.2 bps, t=-0.77  |
| 1h          | Wed>Thu, Δ=2.3 bps, t=1.30  | 21:00 UTC>02:00 UTC, Δ=8.9 bps, t=2.77  | weekend-weekday -0.7 bps, t=-0.78  |
| 4h          | Wed>Thu, Δ=9.1 bps, t=1.35  | 20:00 UTC>00:00 UTC, Δ=12.5 bps, t=2.10 | weekend-weekday -2.8 bps, t=-0.83  |
| 1d          | Wed>Thu, Δ=50.7 bps, t=1.10 | n/a                                     | weekend-weekday -18.9 bps, t=-1.00 |

Interpretation:
- Calendar effects are **secondary**, not primary.
- The day-of-week pattern is directionally consistent but weak: **Wednesday > Thursday** on all four timeframes, with low significance (`t ≈ 1.1–1.35`).
- Weekend underperforms weekday on average, but the effect is weak and not significant.
- Intraday time-of-day shows the only meaningful calendar structure:
  - **15m / 1h**: strongest positive bars cluster around **21:00 UTC** and **13:00 UTC**; weakest around **23:00 UTC** and **02:00 UTC**.
  - **4h**: **20:00 UTC** and **12:00 UTC** sessions outperform **00:00 UTC**.

## 3. Volume/Flow Channel Summary

### Strongest directional signals (robust outer states, roughly balanced support)

| timeframe   | channel       |   N |   H | signal              |   spread (bps) |     t |
|:------------|:--------------|----:|----:|:--------------------|---------------:|------:|
| 1h          | flow_extreme  | 168 |  48 | flow hi>lo          |          102.8 | 10.84 |
| 4h          | flow_extreme  |  24 |  24 | flow hi>lo          |          187.3 |  7.15 |
| 1d          | flow_extreme  |  84 |  12 | flow hi>lo          |          633.1 |  5.29 |
| 1h          | trade_density |  84 |  24 | trade-density hi<lo |          -29.6 | -4.53 |
| 15m         | volume_state  |  24 |  24 | volume high>low     |            7.3 |  4.29 |
| 1d          | trade_density |  42 |  24 | trade-density hi>lo |          667.7 |  3.99 |
| 15m         | trade_density | 168 |  24 | trade-density hi<lo |           -6.3 | -3.87 |
| 15m         | flow_extreme  |  24 |  12 | flow hi<lo          |           -4.7 | -3.83 |
| 1h          | volume_state  |  84 |  24 | volume high>low     |           21.2 |  3.28 |
| 4h          | trade_density |  24 |  48 | trade-density hi<lo |          -86.2 | -2.38 |

### Strongest magnitude / state-conditioning signals

| timeframe   | channel           |   N |   H | signal                  |   Δabs (bps) |      t |
|:------------|:------------------|----:|----:|:------------------------|-------------:|-------:|
| 15m         | volume_state_mag  | 168 |   1 | higher future magnitude |         14.6 |  43.61 |
| 15m         | trade_density_mag | 168 |   1 | lower future magnitude  |        -10.1 | -31.76 |
| 1h          | volume_state_mag  | 168 |   1 | higher future magnitude |         28.2 |  23.53 |
| 1h          | trade_density_mag | 168 |   1 | lower future magnitude  |        -22.6 | -17.81 |
| 4h          | volume_state_mag  | 168 |   1 | higher future magnitude |         60.5 |  12.6  |
| 4h          | trade_density_mag | 168 |   1 | lower future magnitude  |        -45.7 |  -9.75 |
| 1d          | volume_state_mag  | 168 |   3 | higher future magnitude |        183.2 |   4.81 |
| 1d          | trade_density_mag | 168 |  48 | higher future magnitude |        786.3 |   4.53 |

### What looks real

- **Volume level → future magnitude** is the cleanest channel in this pass.
- **Extreme standardized taker imbalance** is the cleanest directional order-flow channel, especially on **1h** and **4h**, and still material on **1d**.
- **Trade-density** adds information beyond volume:
  - intraday: mostly a **compression / lower-future-magnitude** proxy;
  - daily: a **stronger-participation continuation** proxy.

### What looks weak or noisy

- Raw volume level as a **direction-only** predictor is weak above 1h.
- Raw sign of imbalance is unstable and often contrarian at longer horizons.
- Day-of-week and weekend effects are weak.
- Calendar by itself is not a dominant explanatory axis in discovery.

