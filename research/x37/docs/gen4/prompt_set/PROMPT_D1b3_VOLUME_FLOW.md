# PROMPT D1b3 - Volume & Order Flow Channels (Use this after D1b2 in the same chat)

You have completed D1b2. Volatility and regime measurements are saved in `d1b2_measurements_volatility_regime.md`.

**Guard**: If D1b2 reported PARTIAL, stop here and report: "D1b2 incomplete — re-send D1b2 to finish remaining channels before continuing." Do not continue.

Your job in this turn is **only** to measure volume, order flow, and calendar channels.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Research philosophy (from constitution v4.0)

Start from raw data. Measure what exploitable information exists before choosing any mechanism family. Do not pre-filter by named indicator vocabulary (EMA, ATR, RSI, etc.). Let the measurements determine which channels carry real edge.

Any mathematical function of the admitted data surface is a valid measurement target.

## What to do

Using the **warmup period** (→ 2019-12-31) for calibration and the **discovery period** (2020-01-01 → 2023-06-30) for measurement:

### 1. Volume and order flow channels (all timeframes)

For each timeframe (15m, 1h, 4h, 1d), measure:
- Volume patterns: autocorrelation, regime changes
- Taker buy ratio: `taker_buy_base_vol / volume` over rolling windows
- Does taker imbalance predict forward returns? At what horizon?
- Volume-participation metrics: do volume spikes precede or follow price moves?
- `num_trades` patterns: does trade count carry information beyond volume?

### 2. Calendar and time effects

- Calendar/time-of-week effects: any systematic patterns by day of week or time of day?

### 3. Save results

Save a summary file `d1b3_measurements_volume_flow.md` containing:
- key statistics per channel per timeframe
- which channels show measurable exploitable signal
- which channels are noise
- strongest volume/flow signals ranked by predictive content

## Handling execution limits

If you approach execution time limits:
1. Save all measurements computed so far to `d1b3_measurements_volume_flow.md`.
2. Report which channels/timeframes are completed and which remain.
3. State clearly: "D1b3 PARTIAL — N of M channels completed. Continue with the next prompt re-send."
4. The user will re-send this same prompt to continue from where you stopped.

## Required output sections
1. `Volume & Flow Channels` — taker flow, participation, predictive content
2. `Calendar Effects` — day-of-week, time-of-day patterns
3. `Volume/Flow Channel Summary` — strongest signals ranked

## What not to do
- Do not name strategies or propose trading rules.
- Do not run backtests.
- Do not propose parameter values for strategies.
- Do not use holdout or reserve_internal data for measurement.
- Do not pre-filter channels by mechanism family or named indicator vocabulary.
- Do not modify the constitution.
- Do not re-measure price/momentum or volatility/regime channels — those are in D1b1/D1b2.
- Do not measure cross-timeframe relationships — that is D1b4.
