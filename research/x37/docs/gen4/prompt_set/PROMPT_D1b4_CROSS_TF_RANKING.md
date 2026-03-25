# PROMPT D1b4 - Cross-Timeframe, Redundancy & Channel Ranking (Use this after D1b3 in the same chat)

You have completed D1b1–D1b3. Per-channel measurements are saved in:
- `d1b1_measurements_price_momentum.md`
- `d1b2_measurements_volatility_regime.md`
- `d1b3_measurements_volume_flow.md`

**Guard**: If any of D1b1, D1b2, or D1b3 reported PARTIAL, stop here and report: "Upstream measurement step incomplete — re-send the incomplete step to finish before consolidating." Do not continue.

Your job in this turn is to measure cross-timeframe relationships, map redundancy across all channels measured so far, and produce the final integrated channel ranking.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Research philosophy (from constitution v4.0)

Start from raw data. Measure what exploitable information exists before choosing any mechanism family. Do not pre-filter by named indicator vocabulary (EMA, ATR, RSI, etc.). Let the measurements determine which channels carry real edge.

Any mathematical function of the admitted data surface is a valid measurement target.

## What to do

Using the **warmup period** (→ 2019-12-31) for calibration and the **discovery period** (2020-01-01 → 2023-06-30) for measurement:

### 1. Cross-timeframe relationships

- Alignment: when slower TF momentum is positive, does faster TF entry quality improve?
- Conditioning: forward returns on faster TF conditional on slower TF state
- Timing: does slower TF provide useful permission/filter for faster TF signals?
- Measure at least D1→H4, H4→1h, and 1h→15m relationships

### 2. Redundancy analysis (across ALL channels from D1b1–D1b3)

- For channels that show signal, measure pairwise correlation
- Identify independent vs redundant channels
- Rank channels by: predictive content, cost sensitivity, regime robustness

### 3. Integrated channel ranking

Combine findings from D1b1 (price/momentum), D1b2 (volatility/regime), D1b3 (volume/flow), and this turn's cross-timeframe measurements into a single ranked list of exploitable channels.

### 4. Save results

Save two files:
- `d1b4_measurements_cross_tf_ranking.md` — this turn's measurements and analysis
- `d1b_measurements.md` — **consolidated summary** integrating all D1b1–D1b4 results, containing:
  - key statistics per channel per timeframe
  - which channels show measurable exploitable signal
  - which channels are noise
  - redundancy map between channels
  - strongest independent signals ranked

The consolidated `d1b_measurements.md` is the input for D1c.

## Required output sections
1. `Cross-Timeframe Conditioning` — alignment lift, conditional performance
2. `Redundancy Map` — which channels are independent vs correlated (across all D1b1–D1b3 channels)
3. `Channel Ranking` — strongest independent exploitable signals, ordered by strength
4. `Consolidated Summary` — integrated view across all measurement turns

## Handling execution limits

If you approach execution time limits:
1. Save all cross-timeframe measurements computed so far to `d1b4_measurements_cross_tf_ranking.md` and update `d1b_measurements.md` with partial consolidation.
2. Report which cross-timeframe relationships and redundancy analyses are completed and which remain.
3. State clearly: "D1b4 PARTIAL — N of M analyses completed. Continue with the next prompt re-send."
4. The user will re-send this same prompt to continue from where you stopped.

## What not to do
- Do not name strategies or propose trading rules.
- Do not run backtests.
- Do not propose parameter values for strategies.
- Do not use holdout or reserve_internal data for measurement.
- Do not pre-filter channels by mechanism family or named indicator vocabulary.
- Do not modify the constitution.
- Do not re-measure price/momentum, volatility/regime, or volume/flow channels — those are in D1b1/D1b2/D1b3.
