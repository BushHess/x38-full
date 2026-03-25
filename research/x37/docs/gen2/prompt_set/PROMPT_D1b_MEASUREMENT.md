# PROMPT D1b - Feature Measurement & Signal Analysis (Use this after D1a in the same chat)

You have completed D1a. Data is loaded and validated.

Use the dataframes loaded in D1a. If they are no longer in memory, reload from the raw CSV files.

Your job in this turn is **only** to measure what signals exist in the data.
Do **not** design strategies yet.
Do **not** run backtests.
Do **not** propose candidates.

## Context from the constitution

The constitution admits three archetypes, each built from specific primitives:

**Archetype A — Slow trend state:**
- D1 permission: momentum over rolling lookback, EMA slope/spread, close vs rolling anchor
- H4 state: trend persistence, drawdown/pullback depth, volatility quiet/expansion
- Exits: permission off, state deterioration, ATR-style trailing

**Archetype B — Pullback continuation:**
- D1 permission: same as A
- H4 pullback: drawdown from rolling high, distance from MA/anchor, range position
- 1h timing: reclaim above local anchor, break of short consolidation, participation confirmation

**Archetype C — Compression breakout:**
- D1 permission: non-bearish trend or neutral-positive filter
- H4 compression: ATR percentile low, range compression, body compression
- 1h breakout: breakout above local range, volume/taker-flow participation rise

## What to do

Using the **warmup period** (→ 2019-12-31) for calibration and the **discovery period** (2020-01-01 → 2023-06-30) for measurement:

### 1. D1 timeframe measurements
- EMA spreads at various lookbacks (e.g., 10, 21, 50, 100, 200 days): distribution, autocorrelation
- Momentum (ROC) at various lookbacks: distribution, persistence
- Close position relative to rolling high/low: distribution
- Trend persistence: fraction of time above/below key EMAs

### 2. H4 timeframe measurements
- Trend persistence metrics (consecutive same-direction bars, run lengths)
- ATR behavior: distribution, percentiles, regime changes
- Drawdown from rolling high: depth distribution, recovery time
- Volatility clustering: autocorrelation of ATR or absolute returns
- Range and body compression: frequency and duration of low-ATR episodes

### 3. 1h timeframe measurements
- Participation metrics: volume/num_trades around H4 breakout or reclaim events
- Taker flow: taker_buy_base_vol / volume ratio (VDO-like), distribution, signal properties
- Local range breakout frequency and follow-through

### 4. Cross-timeframe relationships
- D1 trend → H4 trend alignment frequency
- D1 permission on → H4 entry quality (do H4 entries during D1 uptrend perform better?)
- H4 compression → 1h breakout follow-through

### 5. Taker flow analysis (all timeframes)
- taker_buy_ratio = taker_buy_base_vol / volume
- Distribution, mean, stdev per timeframe
- Correlation with forward returns at various horizons
- Does taker imbalance have predictive signal?

### 6. Save results
Save a summary file `d1b_measurements.md` containing:
- key statistics per timeframe
- which primitives show measurable signal vs noise
- any notable anomalies or structural features

## Required output sections
1. `D1 Timeframe Summary` — key trend/momentum statistics
2. `H4 Timeframe Summary` — volatility, trend persistence, drawdown stats
3. `1h Timeframe Summary` — participation, taker flow, breakout stats
4. `Cross-Timeframe Relationships` — alignment and conditional performance
5. `Taker Flow Analysis` — signal quality assessment
6. `Primitives Signal Assessment` — for each archetype primitive, measurable signal (yes/weak/no)

## What not to do
- Do not design or name any strategy.
- Do not run backtests.
- Do not propose parameter values for strategies.
- Do not use holdout or reserve_internal data for measurement.
- Do not modify the constitution.
