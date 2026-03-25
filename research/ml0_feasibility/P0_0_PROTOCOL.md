# ML0 Feasibility Protocol

This research branch answers one question before any XGBoost work starts:

`Does the current VTrend/E0 state contain enough incremental information and effective sample size to justify an ML overlay at all?`

The branch is intentionally conservative. It does not train tree models. It runs a 4-step gate:

1. Information ceiling
   Measure how much out-of-sample predictive signal is available from a very small set of E0-state features.

2. Minimum baseline to beat
   Establish the strongest compact baseline that any future ML model must beat.

3. ESS and event-cluster accounting
   Estimate how much bar-level sample inflation remains after thinning and clustering.

4. Kill criteria
   Convert the above into a hard decision:
   - `KILL_STACK`
   - `PROCEED_SMALL_ONLY`
   - `ALLOW_TREE_BENCHMARK`

## Scope

- Asset: BTCUSDT
- Timeframe: H4
- Data file: `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- Reporting window: `2019-01-01` to `2026-02-20`
- Warmup: `365` days
- Base strategy context: E0-style trend state

## Labeling

Origins are selected only in `near-peak` bars inside an EMA-up regime.

Definitions at origin bar `t`:

- `watermark_t`: max close since the start of the current EMA-up segment
- `dd_now_t`: drawdown from watermark at `t`
- `ATR_t`: standard ATR(14)

Origin filter:

- `ema_fast > ema_slow`
- `dd_now_t <= max(ATR_t / close_t, 1%)`

Future barriers over horizon `H = 24` bars:

- `DD1 = max(2.5 * ATR_t / close_t, 2%)`
- `DD2 = max(5.0 * ATR_t / close_t, 4%)`
- `UP  = max(1.5 * ATR_t / close_t, 1.5%)`

Targets:

- `soft`: downside barrier `DD1` before upside barrier `UP`
- `hard`: downside barrier `DD2` before upside barrier `UP`

If neither side is hit within `H`, the sample is marked `censored` and excluded from compact-model fitting.

## Compact baselines

The benchmark compares four deliberately small probabilistic baselines:

- `PRIOR`
- `DD_ONLY`
- `CORE4`
- `EXPANDED7`

All fitted models are L2-regularized logistic regression implemented locally in NumPy.

## Sample-control rules

- `stride=3` training/evaluation subset for the model benchmark
- cluster accounting on contiguous near-peak bars
- no full-tree or multi-head model allowed at this stage

## Success criteria

The protocol is designed to reject ML stacks quickly when evidence is weak.

- If compact models barely improve over the prior and ESS is low, the verdict is `KILL_STACK`.
- If only one target has enough information/support, the verdict is `PROCEED_SMALL_ONLY`.
- Only if the compact baseline shows clear OOS edge with adequate ESS may a tree benchmark be justified.
