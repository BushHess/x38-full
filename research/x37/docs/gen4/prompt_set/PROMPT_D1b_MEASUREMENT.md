# PROMPT D1b - Data Decomposition & Signal Measurement (DEPRECATED — use D1b1–D1b4)

> **Note**: This monolithic prompt has been split into 4 sub-prompts for better per-turn execution:
> - `PROMPT_D1b1_PRICE_MOMENTUM.md` — return, momentum, structural features, mean-reversion, gaps
> - `PROMPT_D1b2_VOLATILITY_REGIME.md` — volatility channels, regime structure, distribution tails
> - `PROMPT_D1b3_VOLUME_FLOW.md` — volume, order flow, calendar effects
> - `PROMPT_D1b4_CROSS_TF_RANKING.md` — cross-timeframe, redundancy analysis, integrated channel ranking
>
> Use the split version. This file is retained for reference only.

You have completed D1a.

**Guard**: If D1a Data Quality Verdict was **FAIL**, stop here and report: "D1a FAIL — cannot proceed to measurement. Fix data issues or re-run D1a first." Do not continue.

Data is loaded and validated. Use the dataframes loaded in D1a. If they are no longer in memory, reload from the raw CSV files.

Your job in this turn is **only** to measure what exploitable structure exists in the data.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Research philosophy (from constitution v4.0)

Start from raw data. Measure what exploitable information exists before choosing any mechanism family. Do not pre-filter by named indicator vocabulary (EMA, ATR, RSI, etc.). Let the measurements determine which channels carry real edge.

Any mathematical function of the admitted data surface is a valid measurement target.

## What to do

Using the **warmup period** (→ 2019-12-31) for calibration and the **discovery period** (2020-01-01 → 2023-06-30) for measurement:

### 1. Return and momentum channels (all timeframes)

For each timeframe (15m, 1h, 4h, 1d), measure:
- Return over various lookbacks N: `close_t / close_(t-N) - 1`
  - Suggested N: 6, 12, 24, 42, 84, 168 bars (adapt to timeframe)
- Autocorrelation of returns at various lags
- Persistence: probability that sign(return_N) persists to next period
- Decay: at what horizon does predictive content disappear?
- Forward return conditional on sign(return_N): is there continuation or reversal?

### 2. Volatility channels (all timeframes)

- Realized volatility: rolling std of log returns at various windows
- Volatility clustering: autocorrelation of absolute returns or realized vol
- Volatility-normalized returns: `return_N / (rolling_std * sqrt(N))`
  - Does normalization improve signal stability?
- Range-based volatility: (high - low) / close, rolling stats
- Compression: frequency and duration of low-volatility episodes
- Does volatility level predict forward return magnitude or direction?

### 3. Volume and order flow channels (all timeframes)

- Volume patterns: autocorrelation, regime changes
- Taker buy ratio: `taker_buy_base_vol / volume` over rolling windows
- Does taker imbalance predict forward returns? At what horizon?
- Volume-participation metrics: do volume spikes precede or follow price moves?
- `num_trades` patterns: does trade count carry information beyond volume?

### 4. Cross-timeframe relationships

- Alignment: when slower TF momentum is positive, does faster TF entry quality improve?
- Conditioning: forward returns on faster TF conditional on slower TF state
- Timing: does slower TF provide useful permission/filter for faster TF signals?
- Measure at least D1→H4, H4→1h, and 1h→15m relationships

### 5. Structural features

- Rolling quantile/percentile rank: does the rank of a feature (e.g., return, vol) have cleaner signal than the raw value?
- Expanding vs trailing calibration: do adaptive thresholds (e.g., yearly expanding quantile) improve stationarity?
- Hysteresis: if you set entry threshold ≠ hold threshold, does it reduce whipsaw?
- Range position: `(close - rolling_low_N) / (rolling_high_N - rolling_low_N)` — signal content?
- Drawdown from rolling high: depth distribution, recovery patterns

### 6. Additional channels

- Mean-reversion: do returns at any horizon show statistically significant reversal?
- Regime structure: are there identifiable regimes (trend/chop/crisis) with different statistical properties?
- Distribution tails: do extreme returns predict subsequent behavior?
- Calendar/time-of-week effects: any systematic patterns by day of week or time of day?
- Gap behavior: do opening gaps from D1 close predict intraday direction?

### 7. Redundancy analysis

- For channels that show signal, measure pairwise correlation
- Identify independent vs redundant channels
- Rank channels by: predictive content, cost sensitivity, regime robustness

### 8. Save results

Save a summary file `d1b_measurements.md` containing:
- key statistics per channel per timeframe
- which channels show measurable exploitable signal
- which channels are noise
- redundancy map between channels
- strongest independent signals ranked

## Handling execution limits

If you approach execution time limits:
1. Save all measurements computed so far to `d1b_measurements.md`.
2. Report which channels/timeframes are completed and which remain.
3. State clearly: "D1b PARTIAL — N of M channels completed. Continue with the next prompt re-send."
4. The user will re-send this same prompt to continue from where you stopped.

## Required output sections
1. `Return & Momentum Channels` — predictive content per timeframe per lookback
2. `Volatility Channels` — clustering, normalization benefit, compression signal
3. `Volume & Flow Channels` — taker flow, participation, predictive content
4. `Cross-Timeframe Conditioning` — alignment lift, conditional performance
5. `Structural Features` — quantile rank, adaptive thresholds, hysteresis, range position
6. `Additional Channels` — mean-reversion, regime, tails, calendar, gaps
7. `Redundancy Map` — which channels are independent vs correlated
8. `Channel Ranking` — strongest independent exploitable signals, ordered by strength

## What not to do
- Do not name strategies or propose trading rules.
- Do not run backtests.
- Do not propose parameter values for strategies.
- Do not use holdout or reserve_internal data for measurement.
- Do not pre-filter channels by mechanism family or named indicator vocabulary.
- Do not modify the constitution.
