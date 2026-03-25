# PROMPT D1b1 - Price & Momentum Channels (Use this after D1a in the same chat)

You have completed D1a.

**Guard**: If D1a Data Quality Verdict was **FAIL**, stop here and report: "D1a FAIL — cannot proceed to measurement. Fix data issues or re-run D1a first." Do not continue.

Data is loaded and validated. Use the dataframes loaded in D1a. If they are no longer in memory, reload from the raw CSV files.

Your job in this turn is **only** to measure price and momentum channels.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Research philosophy (from constitution v3.0)

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

### 2. Structural features

- Rolling quantile/percentile rank: does the rank of a feature (e.g., return, vol) have cleaner signal than the raw value?
- Expanding vs trailing calibration: do adaptive thresholds (e.g., yearly expanding quantile) improve stationarity?
- Hysteresis: if you set entry threshold ≠ hold threshold, does it reduce whipsaw?
- Range position: `(close - rolling_low_N) / (rolling_high_N - rolling_low_N)` — signal content?
- Drawdown from rolling high: depth distribution, recovery patterns

### 3. Mean-reversion and gap behavior

- Mean-reversion: do returns at any horizon show statistically significant reversal?
- Gap behavior: do opening gaps from D1 close predict intraday direction?

### 4. Save results

Save a summary file `d1b1_measurements_price_momentum.md` containing:
- key statistics per channel per timeframe
- which channels show measurable exploitable signal
- which channels are noise
- strongest price/momentum signals ranked by predictive content

## Handling execution limits

If you approach execution time limits:
1. Save all measurements computed so far to `d1b1_measurements_price_momentum.md`.
2. Report which channels/timeframes are completed and which remain.
3. State clearly: "D1b1 PARTIAL — N of M channels completed. Continue with the next prompt re-send."
4. The user will re-send this same prompt to continue from where you stopped.

## Required output sections
1. `Return & Momentum Channels` — predictive content per timeframe per lookback
2. `Structural Features` — quantile rank, adaptive thresholds, hysteresis, range position
3. `Mean-Reversion & Gaps` — reversal signal, gap predictiveness
4. `Price/Momentum Channel Summary` — strongest signals ranked

## What not to do
- Do not name strategies or propose trading rules.
- Do not run backtests.
- Do not propose parameter values for strategies.
- Do not use holdout or reserve_internal data for measurement.
- Do not pre-filter channels by mechanism family or named indicator vocabulary.
- Do not modify the constitution.
- Do not measure volatility, volume, or cross-timeframe channels — those are D1b2/D1b3/D1b4.
