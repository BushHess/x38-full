# PROMPT D1b2 - Volatility & Regime Channels (Use this after D1b1 in the same chat)

You have completed D1b1. Price and momentum measurements are saved in `d1b1_measurements_price_momentum.md`.

**Guard**: If D1b1 reported PARTIAL, stop here and report: "D1b1 incomplete — re-send D1b1 to finish remaining channels before continuing." Do not continue.

Your job in this turn is **only** to measure volatility and regime channels.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Research philosophy (from constitution v4.0)

Start from raw data. Measure what exploitable information exists before choosing any mechanism family. Do not pre-filter by named indicator vocabulary (EMA, ATR, RSI, etc.). Let the measurements determine which channels carry real edge.

Any mathematical function of the admitted data surface is a valid measurement target.

## What to do

Using the **warmup period** (→ 2019-12-31) for calibration and the **discovery period** (2020-01-01 → 2023-06-30) for measurement:

### 1. Volatility channels (all timeframes)

For each timeframe (15m, 1h, 4h, 1d), measure:
- Realized volatility: rolling std of log returns at various windows
- Volatility clustering: autocorrelation of absolute returns or realized vol
- Volatility-normalized returns: `return_N / (rolling_std * sqrt(N))`
  - Does normalization improve signal stability?
- Range-based volatility: (high - low) / close, rolling stats
- Compression: frequency and duration of low-volatility episodes
- Does volatility level predict forward return magnitude or direction?

### 2. Regime structure

- Are there identifiable regimes (trend/chop/crisis) with different statistical properties?
- Distribution tails: do extreme returns predict subsequent behavior?

### 3. Save results

Save a summary file `d1b2_measurements_volatility_regime.md` containing:
- key statistics per channel per timeframe
- which channels show measurable exploitable signal
- which channels are noise
- strongest volatility/regime signals ranked by predictive content

## Handling execution limits

If you approach execution time limits:
1. Save all measurements computed so far to `d1b2_measurements_volatility_regime.md`.
2. Report which channels/timeframes are completed and which remain.
3. State clearly: "D1b2 PARTIAL — N of M channels completed. Continue with the next prompt re-send."
4. The user will re-send this same prompt to continue from where you stopped.

## Required output sections
1. `Volatility Channels` — clustering, normalization benefit, compression signal
2. `Regime Structure` — regime identification, tail behavior
3. `Volatility/Regime Channel Summary` — strongest signals ranked

## What not to do
- Do not name strategies or propose trading rules.
- Do not run backtests.
- Do not propose parameter values for strategies.
- Do not use holdout or reserve_internal data for measurement.
- Do not pre-filter channels by mechanism family or named indicator vocabulary.
- Do not modify the constitution.
- Do not re-measure price/momentum channels — those are in D1b1.
- Do not measure volume/order-flow or cross-timeframe channels — those are D1b3/D1b4.
