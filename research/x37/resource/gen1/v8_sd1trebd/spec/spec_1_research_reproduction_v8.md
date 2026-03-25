# Spec 1 — Research Reproduction Spec (Full research process)

## 1. Purpose and admissible inputs

This document defines the full V8 same-file BTC/USDT research protocol, from raw CSV files to the frozen winner `S_D1_TREND`. The document is self-contained. An engineer who has only this document plus the two raw input files can rebuild the full pipeline, rerun the search, regenerate the frozen comparison set, and reproduce the final winner.

Only three pre-freeze inputs are admissible:

1. The protocol text file `RESEARCH_PROMPT_V8.md`.
2. The raw native H4 CSV.
3. The raw native D1 CSV.

No prior reports, prior session outputs, prior shortlist tables, prior frozen candidates, benchmark specifications, or any precomputed artifacts from earlier sessions may be consulted before the freeze point.

### Expected raw file schema

Both raw CSV files use the same 13-column schema, in this exact column order:

1. `symbol`
2. `interval`
3. `open_time`
4. `close_time`
5. `open`
6. `high`
7. `low`
8. `close`
9. `volume`
10. `quote_volume`
11. `num_trades`
12. `taker_buy_base_vol`
13. `taker_buy_quote_vol`

Field rules:

- `open_time` and `close_time` are integer milliseconds since Unix epoch.
- Interpret all timestamps as UTC.
- `interval` identifies the timeframe. The D1 file contains `1d`. The H4 file contains `4h`.
- The V8 run expects native raw bars only. No synthetic resampling is allowed.

### Artifact-grounded notes that control this specification

This specification follows the frozen artifacts, not memory or prose summaries.

1. The frozen `shortlist_ledger.csv` contains **29** candidate rows, not 30.
2. The frozen three-layer shortlist contains **6** candidates built as **3 two-layer cores × 2 entry-only confirmation filters**, not 2 cores × 3 filters.
3. The frozen validation and reserve tables expose a legacy field name `trade_count_entries`. In the frozen artifacts this field is **not** completed round trips. It is the count of segment-local state transitions at execution opens, defined as the number of times `position_i != position_(i-1)` within the segment or fold, where the first bar of the segment is compared against the immediately preceding bar from prior history. Operationally this is `entries + exits` that occur inside the segment. For `S_D1_TREND`, the serialized values `61`, `34`, and `35` are exactly this state-transition count on discovery, holdout, and reserve. Completed trade-quality statistics are separate and are computed from completed round trips only.

## 2. Fixed execution model and lock items

### Input
The two raw CSV files and the V8 protocol text.

### Logic
Before any discovery work, freeze the execution model, data splits, fold architecture, feature-library manifest, bootstrap method, random seed, plateau rule, complexity budget, promotion gates, evidence labels, daily-return alignment convention, and deterministic tie-break rule.

### Output
A locked protocol object equivalent to `locked_protocol_settings.json`, containing:

- market: BTC/USDT spot
- directionality: long-only
- signal timing: signal computed at bar close
- fill model: execute at next bar open
- cost: 10 bps per side, 20 bps round-trip
- warmup: no live trading before 2020-01-01
- timestamps: UTC
- native bars only
- no synthetic missing-bar imputation
- position sizing: 100% long when active, 0% when inactive
- leverage: 0
- pyramiding: false
- discretionary overrides: false

### Decision rule
If any locked item changes after results are seen, the research is restarted and all prior same-session candidate results are discarded.

## 3. Data pipeline and anomaly handling

### Step 3.1 — Parse and sort

#### Input
Raw native D1 CSV and raw native H4 CSV.

#### Logic
Process rows in this exact order:

1. Parse `open_time` and `close_time` as timezone-aware UTC timestamps.
2. Sort each timeframe independently by ascending `open_time`.
3. Check duplicates, nulls, malformed rows, impossible OHLC, nonstandard durations, irregular `open_time` gaps, and zero-activity rows.
4. Apply the deterministic H4 scoring-frame drop rule.
5. Reconcile native D1 versus day-aggregated native H4 on overlapping UTC dates.
6. Write the anomaly-disposition register.

#### Output
- one audited native D1 frame,
- one audited native H4 raw frame,
- one native H4 scoring frame after the deterministic drop,
- one written anomaly register,
- one machine-readable audit summary equivalent to `data_audit_summary.json`.

#### Decision rule
Discovery may proceed only if no structural defect breaks the execution assumptions. V8 found no such blocker.

### Step 3.2 — Deterministic drop rule

#### Input
The sorted raw H4 frame.

#### Logic
Drop from the **H4 scoring frame only** any row satisfying all of the following conditions:

- `volume == 0`
- `quote_volume == 0`
- `num_trades == 0`
- `taker_buy_base_vol == 0`
- `taker_buy_quote_vol == 0`
- `open == high == low == close`
- `close_time <= open_time`

The raw audit frame still logs the row. The scoring frame excludes it.

This rule selects exactly one row:

- `open_time = 1504713600000`
- `close_time = 1504713600000`
- `open = high = low = close = 4619.43`

#### Output
- raw H4 rows: 18,791
- H4 scoring rows: 18,790
- deterministic drop count: 1

#### Decision rule
No other row removal is allowed anywhere in the pipeline.

### Step 3.3 — Anomaly disposition register

| Anomaly class | Observed count / details | Disposition | Operational note |
| --- | --- | --- | --- |
| Native D1 raw file | 3,134 rows, 2017-08-17 to 2026-03-16, zero duplicate `open_time`, zero duplicate `close_time`, zero nulls, zero malformed rows, zero nonstandard durations, zero irregular gaps, zero zero-activity rows, zero impossible OHLC | Retain all rows exactly as supplied | Clean file; no row removal or repair. |
| Native H4 nonstandard-duration rows | 20 rows with duration != 14,400,000 ms; durations include 7,200,000 ms (9), 10,800,000 ms (2), and several unique anomalous values | Retain exactly as supplied | `close_time` governs slower-feature visibility and as-of joins. |
| Native H4 irregular open gaps | 8 rows preceded by `open_time` gaps > 14,400,000 ms; gaps are 28,800,000 ms (5), 43,200,000 ms (2), 115,200,000 ms (1) | Retain exactly as supplied | No synthetic bars; execution uses the next available native open after the gap. |
| Native H4 duplicate `close_time` pair | 1 duplicated `close_time` pair | Retain in raw audit because `open_time` values are unique | The pair contains the only malformed zero-activity row. The valid row stays in both audit and scoring. The malformed row stays in audit and is excluded from scoring by the deterministic drop rule. |
| Native H4 malformed row | 1 row: `open_time = close_time = 1504713600000`, `open = high = low = close = 4619.43`, zero volume, zero quote volume, zero trades, zero taker-buy volumes | Retain in audit; exclude from scoring | This is the only row excluded from scoring. |
| Native H4 zero-activity row | Exactly the same malformed row listed immediately above | Deterministically drop from the scoring frame only | This produces 18,790 H4 scoring bars from 18,791 raw rows. |
| D1 vs H4 reconciliation | 3,134 overlapping UTC dates, 11 dates with non-6 H4 bars, zero material OHLC mismatches, max absolute OHLC difference 0.0, max volume absolute diff 1.1641532182693481e-10, max volume pct diff 2.201042380231135e-16 | Retain both files exactly as supplied | Reconciliation is an audit check only; it never rewrites either raw file. |

### Step 3.4 — D1/H4 reconciliation

#### Input
The clean native D1 frame and the H4 scoring frame.

#### Logic
Aggregate H4 bars by UTC date of `open_time`:

- D1 open = first H4 open of the UTC date
- D1 high = maximum H4 high of the UTC date
- D1 low = minimum H4 low of the UTC date
- D1 close = last H4 close of the UTC date
- D1 volumes = sums across the UTC date

Compare the resulting day-aggregated H4 bars against native D1 bars on every overlapping UTC date.

#### Output
- overlap days: 3,134
- material OHLC mismatches: 0
- max absolute OHLC difference: 0.0
- max volume absolute difference: 1.1641532182693481e-10
- max volume percentage difference: 2.201042380231135e-16
- non-6-H4-bar days: 11 dates
- the 11 dates are `2017-08-17 (5)`, `2017-09-06 (5)`, `2018-02-08 (1)`, `2018-02-09 (4)`, `2018-06-26 (4)`, `2018-07-04 (5)`, `2018-11-14 (5)`, `2019-03-12 (5)`, `2019-05-15 (4)`, `2019-08-15 (5)`, `2020-02-19 (5)`

#### Decision rule
Reconciliation is audit-only. A mismatch logs an anomaly. A mismatch does not rewrite either raw file.

## 4. Data splits and discovery folds

### Input
The audited D1 frame and H4 scoring frame.

### Logic
Apply strict chronological partitions:

- context / warmup: 2017-08-17 to 2019-12-31
- discovery: 2020-01-01 to 2023-06-30
- candidate-selection holdout: 2023-07-01 to 2024-09-30
- reserve/internal: 2024-10-01 to dataset end

The discovery window is evaluated with 14 non-overlapping unseen quarterly folds and expanding historical train/calibration windows. Every fold recalibrates all `train_quantile` thresholds using training data strictly earlier than the fold.

| Fold | Train ends (exclusive) | Test start | Test end |
| --- | --- | --- | --- |
| 1 | 2020-01-01 | 2020-01-01 | 2020-03-31 |
| 2 | 2020-04-01 | 2020-04-01 | 2020-06-30 |
| 3 | 2020-07-01 | 2020-07-01 | 2020-09-30 |
| 4 | 2020-10-01 | 2020-10-01 | 2020-12-31 |
| 5 | 2021-01-01 | 2021-01-01 | 2021-03-31 |
| 6 | 2021-04-01 | 2021-04-01 | 2021-06-30 |
| 7 | 2021-07-01 | 2021-07-01 | 2021-09-30 |
| 8 | 2021-10-01 | 2021-10-01 | 2021-12-31 |
| 9 | 2022-01-01 | 2022-01-01 | 2022-03-31 |
| 10 | 2022-04-01 | 2022-04-01 | 2022-06-30 |
| 11 | 2022-07-01 | 2022-07-01 | 2022-09-30 |
| 12 | 2022-10-01 | 2022-10-01 | 2022-12-31 |
| 13 | 2023-01-01 | 2023-01-01 | 2023-03-31 |
| 14 | 2023-04-01 | 2023-04-01 | 2023-06-30 |

### Output
One split architecture with sealed holdout and sealed reserve until the exact required freeze points.

### Decision rule
- Discovery is the only zone allowed to generate ideas, refine candidates, or promote families.
- Holdout stays sealed until the comparison set is frozen from discovery only.
- Reserve stays sealed until the exact frozen leader and exact frozen comparison set are recorded.
- Reserve remains internal only because discovery, holdout, and reserve all come from the same historical file pair.

## 5. Feature engineering library

### Input
The locked feature manifest format and the audited raw data.

### Logic
Freeze the full Stage 1 library **before** inspecting any Stage 1 results. The library contains 29 feature families across 4 buckets and expands to 1,234 feature-parameter-threshold configurations.

Universal feature-construction rules:

- All rolling windows are trailing windows that include the current completed bar and require the full lookback length; before the window fills, the feature is undefined.
- `high` tail means long when `feature > threshold`.
- `low` tail means long when `feature < threshold`.
- `categorical` means long when the current category matches the declared category value.
- `log_return = ln(close_t / close_(t-1))`.
- `rolling_std` uses sample standard deviation with `ddof = 1`.
- `ATR_n` uses true range `TR_t = max(high_t - low_t, abs(high_t - close_(t-1)), abs(low_t - close_(t-1)))` and `ATR_n = rolling_mean(TR, n)`.
- `EMA_n` uses the standard recursive EMA with `alpha = 2 / (n + 1)`, `adjust = False`, and initialization at the first available close.
- When a denominator is zero, the feature is undefined on that bar and that bar cannot generate a signal for that feature.
- When a slower D1 feature is joined onto H4, use backward as-of alignment on D1 `close_time`. Only a completed slower bar is visible.

### Native D1 bucket — 369 scanned configs, 221 promoted

| Feature ID | Family | Formula | Parameters | Tails | Threshold modes |
| --- | --- | --- | --- | --- | --- |
| `D1_MOM_RET` | directional_persistence | `close_t / close_{t-n} - 1` | `n ∈ {3, 5, 10, 20, 40, 80}` | `high`, `low` | `sign`, `train_quantile` |
| `D1_UP_FRAC` | directional_persistence | rolling mean over `n` of `1(close_t > close_{t-1})` | `n ∈ {3, 5, 10, 20, 40}` | `high`, `low` | `structural_level`, `train_quantile` |
| `D1_TREND_QUAL` | trend_quality | `(close_t / close_{t-n} - 1) / (rolling_std(log_return, n) * sqrt(n))` | `n ∈ {5, 10, 20, 40, 80}` | `high`, `low` | `sign`, `train_quantile` |
| `D1_RANGE_POS` | location_within_range | `(close - rolling_low_n) / (rolling_high_n - rolling_low_n)` | `n ∈ {5, 10, 20, 40, 80}` | `high`, `low` | `structural_level`, `train_quantile` |
| `D1_DRAWDOWN` | drawdown_pullback_state | `close / rolling_high_n - 1` | `n ∈ {5, 10, 20, 40, 80}` | `high`, `low` | `train_quantile` |
| `D1_ATR_PCT` | volatility_level | `ATR_n / close` | `n ∈ {5, 10, 20, 40}` | `high`, `low` | `train_quantile` |
| `D1_VOL_RATIO` | volatility_clustering | `ATR_short / ATR_long` | `(short,long) ∈ {(5,20), (10,40), (20,80)}` | `high`, `low` | `train_quantile` |
| `D1_VOL_Z` | participation_flow | `(ln(volume) - rolling_mean(ln(volume), n)) / rolling_std(ln(volume), n)` | `n ∈ {5, 10, 20, 40}` | `high`, `low` | `sign`, `train_quantile` |
| `D1_BUY_RATIO` | participation_flow | rolling mean over `n` of `taker_buy_quote_vol / quote_volume` | `n ∈ {3, 5, 10, 20}` | `high`, `low` | `structural_level`, `train_quantile` |
| `D1_BODY_FRAC` | candle_structure | rolling mean over `n` of `abs(close-open)/(high-low)` | `n ∈ {3, 5, 10, 20}` | `high`, `low` | `train_quantile` |
| `D1_CLV_MEAN` | candle_structure | rolling mean over `n` of `((close-low)/(high-low) - 0.5)` | `n ∈ {3, 5, 10, 20}` | `high`, `low` | `sign`, `train_quantile` |
| `D1_DOW` | calendar_effect | UTC day-of-week of current D1 bar open | `{0,1,2,3,4,5,6,weekday,weekend}` | `categorical` | `categorical` |

### Native H4 bucket — 368 scanned configs, 131 promoted

| Feature ID | Family | Formula | Parameters | Tails | Threshold modes |
| --- | --- | --- | --- | --- | --- |
| `H4_MOM_RET` | directional_persistence | `close_t / close_{t-n} - 1` | `n ∈ {6, 12, 24, 48, 96, 168}` | `high`, `low` | `sign`, `train_quantile` |
| `H4_UP_FRAC` | directional_persistence | rolling mean over `n` of `1(close_t > close_{t-1})` | `n ∈ {6, 12, 24, 48, 96}` | `high`, `low` | `structural_level`, `train_quantile` |
| `H4_TREND_QUAL` | trend_quality | `(close_t / close_{t-n} - 1) / (rolling_std(log_return, n) * sqrt(n))` | `n ∈ {12, 24, 48, 96, 168}` | `high`, `low` | `sign`, `train_quantile` |
| `H4_RANGE_POS` | location_within_range | `(close - rolling_low_n) / (rolling_high_n - rolling_low_n)` | `n ∈ {12, 24, 48, 96, 168}` | `high`, `low` | `structural_level`, `train_quantile` |
| `H4_DRAWDOWN` | drawdown_pullback_state | `close / rolling_high_n - 1` | `n ∈ {12, 24, 48, 96, 168}` | `high`, `low` | `train_quantile` |
| `H4_ATR_PCT` | volatility_level | `ATR_n / close` | `n ∈ {12, 24, 48, 96}` | `high`, `low` | `train_quantile` |
| `H4_VOL_RATIO` | volatility_clustering | `ATR_short / ATR_long` | `(short,long) ∈ {(12,48), (24,96), (48,168)}` | `high`, `low` | `train_quantile` |
| `H4_VOL_Z` | participation_flow | `(ln(volume) - rolling_mean(ln(volume), n)) / rolling_std(ln(volume), n)` | `n ∈ {12, 24, 48, 96}` | `high`, `low` | `sign`, `train_quantile` |
| `H4_BUY_RATIO` | participation_flow | rolling mean over `n` of `taker_buy_quote_vol / quote_volume` | `n ∈ {6, 12, 24, 48}` | `high`, `low` | `structural_level`, `train_quantile` |
| `H4_BODY_FRAC` | candle_structure | rolling mean over `n` of `abs(close-open)/(high-low)` | `n ∈ {6, 12, 24, 48}` | `high`, `low` | `train_quantile` |
| `H4_CLV_MEAN` | candle_structure | rolling mean over `n` of `((close-low)/(high-low) - 0.5)` | `n ∈ {6, 12, 24, 48}` | `high`, `low` | `sign`, `train_quantile` |
| `H4_OPEN_HOUR` | calendar_effect | UTC hour of current H4 bar open | `{0,4,8,12,16,20,weekday,weekend}` | `categorical` | `categorical` |

### Cross-timeframe bucket — 128 scanned configs, 53 promoted

| Feature ID | Formula | Parameters | Tails | Threshold modes |
| --- | --- | --- | --- | --- |
| `XR_CLOSE_VS_D1_EMA` | `H4 close / latest completed D1 EMA_n - 1` | `n ∈ {5, 10, 20, 40}` | `high`, `low` | `sign`, `train_quantile` |
| `XR_POS_IN_PREV_D1_RANGE` | `(H4 close - latest completed D1 low) / (latest completed D1 high - latest completed D1 low) - 0.5` | `context = latest completed D1 bar` | `high`, `low` | `sign`, `train_quantile` |
| `XR_CLOSE_VS_D1_ROLLHIGH` | `H4 close / latest completed D1 rolling_high_n - 1` | `n ∈ {5, 10, 20, 40}` | `high`, `low` | `train_quantile` |
| `XR_MOM_ALIGNMENT` | `H4 n-bar return * latest completed D1 m-bar return` | `(d1,h4) ∈ {(5,6), (10,24), (20,48), (40,96)}` | `high`, `low` | `sign`, `train_quantile` |
| `XR_H4_RETURN_OVER_D1_ATR` | `H4 n-bar return / (latest completed D1 ATR_m / close)` | `(d1,h4) ∈ {(5,6), (10,24), (20,48), (40,96)}` | `high`, `low` | `sign`, `train_quantile` |

### Transported D1-on-H4 bucket — 369 scanned configs, 226 promoted

- Transported D1-on-H4 bucket: all 12 D1 feature families, with the same parameter ladders, tails, threshold modes, and threshold labels as native D1, but evaluated as H4-executed clones by transporting the latest completed D1 signal onto H4 via backward as-of on D1 `close_time`. Count: 369 scanned configs, 226 promoted.

### Threshold calibration modes

1. `sign`
   - threshold label set: `0.0`
   - high tail condition: `feature > 0.0`
   - low tail condition: `feature < 0.0`
   - no training calibration

2. `train_quantile`
   - threshold labels: `(0.6, 0.7, 0.8)`
   - high tail threshold for label `q`: empirical training quantile at percentile `q`
   - low tail threshold for label `q`: empirical training quantile at percentile `1 - q`
   - quantile interpolation: standard linear interpolation on the expanding training distribution
   - recalibrated independently for every discovery fold

3. `structural_level`
   - `range_pos`: high threshold `0.8`, low threshold `0.2`
   - `up_frac`: high threshold `0.6`, low threshold `0.4`
   - `buy_ratio`: high threshold `0.55`, low threshold `0.45`
   - no training calibration

4. `categorical`
   - no calibration
   - long when the categorical condition matches the declared category

### Output
A frozen manifest equivalent to `frozen_stage1_feature_manifest.csv` and a full Stage 1 result table equivalent to `stage1_feature_registry.csv`.

### Decision rule
No feature family, parameter ladder, threshold mode, transport rule, or calibration mode may be added after Stage 1 results are seen.

## 6. Stage 1 scan: executable single-feature state systems

### Input
The frozen feature library and discovery fold architecture.

### Logic
For every configuration:

1. Compute the feature on its native bar set.
2. Convert the feature into a long/flat executable state system.
3. Evaluate on unseen discovery folds only.
4. Deduct 20 bps round-trip trading cost under the exact next-open execution model.
5. Record fold thresholds, fold net returns, fold CAGRs, fold trade-count field values, aggregate discovery Sharpe, aggregate discovery CAGR, aggregate max drawdown, aggregate net return, positive fold share, worst-fold CAGR, mean exposure, and isolated-quarter concentration.

Exact definition of the frozen `trade_count_entries` field:
- on any segment or fold, count the number of execution-open state transitions `position_i != position_(i-1)`;
- for the first bar inside the segment or fold, compare its position against the immediately preceding bar from prior history;
- this field therefore counts `entries + exits` that occur inside the segment or fold;
- it does **not** count completed round trips only.

Execution conversion rules by bucket:

- native D1: compute signal on completed D1 bar, execute at next D1 open.
- native H4: compute signal on completed H4 bar, execute at next H4 open.
- cross-timeframe: compute the H4 feature at H4 close using only the latest completed D1 context available by D1 `close_time`, execute at next H4 open.
- transported D1-on-H4: compute the D1 feature on completed D1 bars, backward as-of join the completed D1 state to H4 by D1 `close_time`, evaluate as an H4-executed clone.

### Output
A Stage 1 registry with exactly 1,234 rows and the following bucket counts:

- native D1: 369
- native H4: 368
- cross-timeframe: 128
- transported D1-on-H4: 369

### Decision rule
Promotion to Stage 2 is allowed only if **all** Stage 1 gate conditions are satisfied.

## 7. Stage 1 promotion gate

### Input
The complete Stage 1 registry.

### Logic
A configuration is promoted only if all of the following are true:

1. positive edge after 20 bps round-trip cost on aggregate discovery walk-forward;
2. at least 20 `trade_count_entries` units across discovery folds, where one unit is one execution-open state transition;
3. at least 50% of 14 folds nonnegative after cost;
4. no isolated-quarter dependence, defined as:
   - at least 3 positive folds, and
   - largest positive fold net return divided by the sum of all positive fold net returns <= 0.65;
5. no unresolved leakage or anomaly-handling ambiguity.

No sparse-design exception was used in the frozen V8 artifact set.

### Output
631 promoted configurations:

- native D1: 221
- native H4: 131
- cross-timeframe: 53
- transported D1-on-H4: 226

### Decision rule
Promoted configurations become eligible for orthogonal shortlist formation. Non-promoted configurations stop.

## 8. Stage 2 shortlist formation

### Input
The 631 promoted Stage 1 configurations.

### Logic
Form an orthogonal shortlist by role rather than by raw metric rank alone. Keep the strongest representative from each serious failure-mode cluster, preserve the simplest viable frontier candidate in every strong family, keep at least one credible layered alternative, and keep a transport control only for redundancy audit.

The Stage 2 candidate identities used in the frozen run are:

| Internal candidate ID | Underlying Stage 1 config | Status of identity |
| --- | --- | --- |
| S_D1_TREND | `D1_MOM_RET|n=40|high|sign|thr=0.0` | Exact; serialized in `frozen_system.json` and matched in Stage 1 registry. |
| S_D1_VOLHIGH | `D1_ATR_PCT|n=10|high|train_quantile|thr=0.6` | Exact; uniquely identified by the layered gate threshold 0.05194939327093149 on full pre-reserve data and by Stage 1 ranking. |
| S_D1_CLV | `D1_CLV_MEAN|n=10|high|train_quantile|thr=0.8` | Most plausible Stage 2 identity; top native D1 CLV representative in the Stage 1 registry. This candidate was dropped before the frozen comparison set. |
| S_H4_TREND | `H4_MOM_RET|n=168|high|sign|thr=0.0` | Exact; uniquely paired with `S_H4_TREND_Q` in the frozen comparison cluster. `H4_TREND_QUAL|n=168|high|sign|thr=0.0` is state-equivalent under sign threshold because volatility is positive. |
| S_H4_TREND_Q | `H4_MOM_RET|n=168|high|train_quantile|thr=0.6` | Exact; uniquely matched from validation results to the Stage 1 registry. |
| S_H4_PULLBACK | `H4_UP_FRAC|n=48|low|structural_level|thr=0.4` | Exact; uniquely identified by the layered controller threshold 0.4 and by the Stage 1 cluster winner. |
| S_H4_VOLQUIET | `H4_VOL_RATIO|short_long=48x168|low|train_quantile|thr=0.6` | Exact; uniquely identified by the layered controller threshold 0.9031397567935835, which is the 40th percentile of the feature on full pre-reserve data. |
| S_H4_CANDLE | `H4_CLV_MEAN|n=48|low|sign|thr=0.0` | Best reconstructed simplest strong H4 candle-structure representative. The frozen artifact set does not serialize a standalone formula field for this internal-only helper; all systems using it were dropped before the frozen comparison set. |
| S_XR_D1EMA | `XR_CLOSE_VS_D1_EMA|n=40|high|sign|thr=0.0` | Exact; uniquely matched from validation results to the Stage 1 registry. |
| S_XR_D1ROLL | `XR_CLOSE_VS_D1_ROLLHIGH|n=40|high|train_quantile|thr=0.7` | Exact; uniquely matched from validation results to the Stage 1 registry. |
| S_D1_TREND_TRANSPORT | `D1_MOM_RET|n=40|high|sign|thr=0.0|TRANSPORT_TO_H4` | Exact; explicit in the Stage 1 registry as the transported control for `S_D1_TREND`. |
| H4_BODYCONF | `H4_BODY_FRAC|n=48|high|train_quantile|thr=0.7` | Best reconstructed H4 body-based entry-only confirmation filter from the promoted H4 body-fraction cluster; used only in dropped three-layer tests. |
| H4_BUYCONF | `H4_BUY_RATIO|n=12|high|train_quantile|thr=0.7` | Best reconstructed H4 buy-pressure entry-only confirmation filter from the promoted H4 buy-ratio cluster; used only in dropped three-layer tests. |

### Output
The frozen shortlist ledger contains 29 candidate rows:

- 11 single-feature systems,
- 12 two-layer systems,
- 6 three-layer systems.

The keep/drop ledger content is:

#### Kept at Stage 2 or Stage 5A for later comparison
- `S_D1_TREND` — comparison_set — strong native D1 trend frontier; simplest slow-trend representative.
- `S_D1_VOLHIGH` — layering_only — useful orthogonal slower volatility context for layering search.
- `S_H4_TREND` — comparison_set — strongest simple native H4 trend representative.
- `S_H4_TREND_Q` — comparison_set — nearest calibrated nonlinear rival in the H4 trend cluster.
- `S_H4_PULLBACK` — layering_only — very consistent controller candidate with low drawdown.
- `S_H4_VOLQUIET` — layering_only — most useful native H4 volatility controller candidate.
- `S_H4_CANDLE` — layering_only — optional entry/confirmation hypothesis.
- `S_XR_D1EMA` — comparison_set — strong simple cross-timeframe candidate with broad plateau.
- `S_XR_D1ROLL` — comparison_set — nearest nonlinear cross-timeframe rival.
- `L2_D1_TREND_AND_H4_VOLQUIET` — comparison_set — best two-layer defensive alternative.
- `L2_D1_VOLHIGH_AND_H4_PULLBACK` — comparison_set — backup layered alternative with a different permission gate.

#### Audit-only transport control
- `S_D1_TREND_TRANSPORT` — audit_only — retained only for transport-vs-native redundancy audit; not eligible as an independent frontier.

#### Dropped at Stage 2
- `S_D1_CLV` — dropped_stage2 — positive, but weaker and less orthogonal than the retained slow-trend and slow-volatility representatives.

#### Dropped at Stage 5A — two-layer candidates
- `L2_H4_TREND_AND_H4_VOLQUIET`
- `L2_XR_D1EMA_AND_H4_VOLQUIET`
- `L2_D1_TREND_AND_H4_PULLBACK`
- `L2_D1_VOLHIGH_AND_H4_CANDLE`
- `L2_H4_TREND_AND_H4_PULLBACK`
- `L2_XR_D1EMA_AND_H4_PULLBACK`
- `L2_D1_VOLHIGH_AND_H4_VOLQUIET`
- `L2_D1_TREND_AND_H4_CANDLE`
- `L2_H4_TREND_AND_H4_CANDLE`
- `L2_XR_D1EMA_AND_H4_CANDLE`

All ten were discovery-positive or at least serious enough to test, but all were inferior to the retained layered alternatives on the frozen discovery-only comparison logic.

#### Dropped at Stage 5A — three-layer candidates
- `L3_D1_TREND_AND_H4_VOLQUIET_ENTRY_H4_BODYCONF`
- `L3_D1_TREND_AND_H4_VOLQUIET_ENTRY_H4_BUYCONF`
- `L3_D1_VOLHIGH_AND_H4_PULLBACK_ENTRY_H4_BODYCONF`
- `L3_D1_VOLHIGH_AND_H4_PULLBACK_ENTRY_H4_BUYCONF`
- `L3_H4_TREND_AND_H4_VOLQUIET_ENTRY_H4_BODYCONF`
- `L3_H4_TREND_AND_H4_VOLQUIET_ENTRY_H4_BUYCONF`

Every three-layer candidate was dropped because the third layer failed to beat the simpler two-layer core and reduced trade count.

### Decision rule
- One primary and one backup representative per closely related family cluster is the default cap.
- A transported clone cannot survive as an independent frontier unless it adds incremental value over both the native slower system and the best genuine native faster candidate in the same role.
- More complex candidates do not displace simpler nearby rivals without clear evidence.

## 9. Stage 3 layered architectures

### Input
The Stage 2 single-feature representatives.

### Logic
Construct layered systems in increasing complexity.

#### Two-layer systems
Create 12 gate-controller systems from 4 gates × 3 controllers.

Gates:
- `S_D1_TREND`
- `S_D1_VOLHIGH`
- `S_H4_TREND`
- `S_XR_D1EMA`

Controllers:
- `S_H4_PULLBACK`
- `S_H4_VOLQUIET`
- `S_H4_CANDLE`

Two-layer logic:
- execution timeframe is H4;
- compute gate and controller states on the completed H4 bar;
- a D1 gate is transported to H4 by backward as-of on D1 `close_time`;
- target state is `LONG` if `gate_state == 1` and `controller_state == 1`, else `FLAT`;
- execute the target state at the next H4 open.

#### Three-layer systems
Create 6 three-layer systems using 3 retained two-layer cores × 2 entry-only confirmation filters.

Two-layer cores:
- `D1_TREND_AND_H4_VOLQUIET`
- `D1_VOLHIGH_AND_H4_PULLBACK`
- `H4_TREND_AND_H4_VOLQUIET`

Entry-only confirmation filters:
- `H4_BODYCONF`
- `H4_BUYCONF`

Three-layer logic:
- core state is the two-layer gate-controller state;
- if already long, hold while the core stays long;
- if flat and the core turns long, entry is allowed only if the entry filter is also long on that completed H4 bar;
- the entry-only filter does not control hold or exit once a position has already been opened.

### Output
12 two-layer candidates and 6 three-layer candidates appended to the shortlist ledger.

### Decision rule
Layering is a hypothesis, not a default. A third layer is not retained unless it improves the two-layer core after accounting for trade shrinkage. None did.

## 10. Stage 4 local refinement and plateau analysis

### Input
Serious candidates from Stage 1 through Stage 3.

### Logic
Search coarse grids first. Refine only around stable regions already supported by discovery. Evaluate plateau breadth by perturbing every tunable quantity by at least ±20% or the nearest admissible grid equivalent.

For the eventual winner `S_D1_TREND`:

- family: native D1 momentum
- winning config: `D1_MOM_RET|n=40|high|sign|thr=0.0`
- lookback ladder: `{3, 5, 10, 20, 40, 80}`
- nearest admissible perturbations around `n = 40`: `n = 20` and `n = 80`

Discovery Sharpe results for the sign-threshold high-tail D1 momentum family are:

- `n=3`: 0.733676
- `n=5`: 0.544680
- `n=10`: 1.045942
- `n=20`: 1.174171
- `n=40`: 1.694137
- `n=80`: 0.690839

Additional local-family support around `n = 40`:

- `D1_MOM_RET|n=40|high|train_quantile|thr=0.6`: discovery Sharpe 1.550948
- `D1_MOM_RET|n=40|high|train_quantile|thr=0.7`: discovery Sharpe 1.593578

Strict plateau score for the winner:
- 80% retention target of winner Sharpe: `0.8 × 1.694137 = 1.355310`
- `n = 20`: 1.174171 → below threshold
- `n = 80`: 0.690839 → below threshold
- strict plateau score: `0 / 2 = 0.00`

### Output
A plateau assessment that says the chosen point is a genuine family peak inside a directionally robust family, not a random one-cell spike, even though the strict ±20% nearest-grid plateau score is low.

### Decision rule
A low strict plateau score does not automatically disqualify the winner if the surrounding family remains directionally positive, nearby calibrated variants remain strong, and later reserve evidence corroborates the choice.

## 11. Stage 5A — discovery-only freeze of the comparison set

### Input
The Stage 2 and Stage 3 serious candidates and discovery-only evidence.

### Logic
Freeze the comparison set **before** opening holdout. Keep the simplest viable representative from each surviving family cluster, the nearest serious internal rivals, and at least one layered alternative with a materially different failure mode.

The frozen comparison set contains 7 candidates:

| Freeze order | Candidate ID | Comparison role | Why included |
| --- | --- | --- | --- |
| 1 | `S_D1_TREND` | `primary_simple` | Native D1 single-feature leader; simplest viable slow-trend representative. |
| 2 | `S_H4_TREND` | `primary_simple` | Simple native H4 trend frontier. |
| 3 | `S_H4_TREND_Q` | `nearest_rival` | Nearest calibrated nonlinear rival inside the H4 trend cluster. |
| 4 | `S_XR_D1EMA` | `primary_simple` | Simple cross-timeframe rival with broad plateau. |
| 5 | `S_XR_D1ROLL` | `nearest_rival` | Nearest nonlinear cross-timeframe rival. |
| 6 | `L2_D1_TREND_AND_H4_VOLQUIET` | `layered_alternative` | Best layered defensive alternative from discovery-only freeze. |
| 7 | `L2_D1_VOLHIGH_AND_H4_PULLBACK` | `layered_backup` | Backup layered alternative with materially different permission gate. |

Transport-vs-native redundancy result:

- transported clone: `D1_MOM_RET|n=40|high|sign|thr=0.0|TRANSPORT_TO_H4`
- native source: `D1_MOM_RET|n=40|high|sign|thr=0.0`
- discovery Sharpe: 1.715755 (transport) vs 1.694137 (native)
- discovery trade-count field: 61 for both
- fold structure: near-identical
- pre-reserve common daily-return correlation between native and transported versions: `ρ = 1.000000`

### Output
A frozen comparison set ledger equivalent to `frozen_comparison_set_ledger.csv`.

### Decision rule
A transported slower-state clone is not admissible as an independent frontier candidate unless it proves incremental value beyond both the native slower system and the best genuine native faster candidate. `S_D1_TREND_TRANSPORT` did not.

## 12. Stage 5B — candidate-selection holdout ranking

### Input
The frozen comparison set and the sealed holdout window `2023-07-01` to `2024-09-30`.

### Logic
Open holdout only after the comparison set is frozen. Evaluate **only** the seven frozen candidates. No new candidate, no new feature, no new threshold mode, no new layer, and no neighborhood reopening is allowed.

### Output
Holdout scores for the comparison set, including:

- `S_D1_TREND`: Sharpe 1.0819, CAGR 40.8%, max DD −43.4%, trade-count field 34
- `S_H4_TREND`: Sharpe 0.7133, CAGR 22.3%, max DD −43.1%, trade-count field 90
- `S_H4_TREND_Q`: Sharpe 1.0314, CAGR 32.9%, max DD −29.0%, trade-count field 58
- `S_XR_D1EMA`: Sharpe 1.1336, CAGR 44.1%, max DD −28.1%, trade-count field 90
- `S_XR_D1ROLL`: Sharpe 1.3635, CAGR 49.0%, max DD −28.3%, trade-count field 48
- `L2_D1_TREND_AND_H4_VOLQUIET`: Sharpe 0.1519, CAGR 1.1%, max DD −19.9%, trade-count field 55
- `L2_D1_VOLHIGH_AND_H4_PULLBACK`: Sharpe 1.1872, CAGR 3.1%, max DD −0.7%, trade-count field 12

### Decision rule
Holdout ranks frozen candidates. Holdout does not permit redesign.

## 13. Stage 5C — pre-reserve leader declaration

### Input
- discovery walk-forward results,
- holdout results,
- pre-reserve daily paired comparisons on the common daily UTC domain,
- plateau breadth,
- cost resilience,
- trade-quality diagnostics,
- simplicity.

### Logic
Aggregate all pre-reserve evidence from `2020-01-01` through `2024-09-30`. Build paired daily-return comparisons on the common daily domain of 1,735 UTC dates.

#### Paired bootstrap configuration

- method: moving block bootstrap on daily UTC returns
- block sizes: 5, 10, 20 days
- resamples per block size: 3,000
- seed: 20260318
- common resampled indices for both candidates in every paired bootstrap draw
- pooled resamples: combine the 9,000 mean-difference draws from all three block sizes

Meaningful paired advantage for candidate A over candidate B requires:

1. point estimate of mean daily return difference `>= 5e-5`,
2. pooled `P(mean_daily_return_diff > 0) >= 0.95`,
3. and the same directional probability threshold is met on at least 2 of the 3 block sizes.

If the condition fails, the pair is indeterminate and the simpler candidate wins if complexity differs.

#### Elimination steps

1. **H4 trend cluster reduction**
   - compare `S_H4_TREND` vs `S_H4_TREND_Q`
   - point mean daily return difference: `0.000043`
   - pooled `P(mean_diff > 0)`: `0.560444`
   - result: indeterminate
   - winner of the cluster: `S_H4_TREND` because the more complex calibrated rival failed to show a meaningful paired advantage.

2. **Cross-timeframe cluster reduction**
   - compare `S_XR_D1EMA` vs `S_XR_D1ROLL`
   - point mean daily return difference: `0.000149`
   - pooled `P(mean_diff > 0)`: `0.682556`
   - result: indeterminate
   - winner of the cluster: `S_XR_D1EMA` because the more complex nonlinear rival failed to show a meaningful paired advantage.

3. **Layered elimination**
   - `S_D1_TREND` vs `L2_D1_TREND_AND_H4_VOLQUIET`
     - point diff: `0.001140` per day
     - pooled `P(mean_diff > 0)`: `0.984889`
     - result: meaningful paired advantage for `S_D1_TREND`
   - `S_D1_TREND` vs `L2_D1_VOLHIGH_AND_H4_PULLBACK`
     - point diff: `0.001493` per day
     - pooled `P(mean_diff > 0)`: `0.990111`
     - result: meaningful paired advantage for `S_D1_TREND`
   - both layered candidates are eliminated.

4. **Final choice among surviving cluster winners**
   - `S_D1_TREND` vs `S_H4_TREND`
     - point diff: `0.000026`
     - pooled `P(mean_diff > 0)`: `0.518444`
     - result: indeterminate
   - `S_D1_TREND` vs `S_XR_D1EMA`
     - point diff: `0.000112`
     - pooled `P(mean_diff > 0)`: `0.671444`
     - result: indeterminate
   - final pre-reserve leader: `S_D1_TREND`

Reasons for the final choice:

- simplest native single-timeframe leader: 1 layer, D1 execution, no cross-timeframe dependence;
- highest pre-reserve mean daily return among the surviving cluster winners;
- strongest cost resilience:
  - `S_D1_TREND` discovery CAGR falls from 101.2% at 20 bps RT to 96.0% at 50 bps RT,
  - `S_XR_D1EMA` discovery CAGR falls from 90.1% at 20 bps RT to 77.4% at 50 bps RT.

Deterministic tie-break order, if still needed after paired indeterminacy:
1. broader plateau,
2. lower pre-reserve drawdown at comparable pre-reserve growth,
3. stronger fold consistency,
4. higher trade count,
5. lower cross-timeframe dependence,
6. fixed lexical order of candidate ID.

### Output
The pre-reserve frozen leader `S_D1_TREND` and the pairwise comparison matrix equivalent to `pre_reserve_pairwise_matrix_long.csv`.

### Decision rule
Reserve must still remain sealed at this point.

## 14. Stage 6 — freeze before reserve

### Input
The declared pre-reserve leader, the frozen comparison set, and all frozen selection tables.

### Logic
Freeze all of the following before reserve is touched:

- exact features,
- exact lookbacks,
- exact thresholds,
- exact state machine,
- exact position sizing,
- exact evaluation code path,
- exact comparison set,
- anomaly-disposition register,
- pairwise matrix,
- stochastic settings,
- daily-return alignment rule.

### Output
Pre-reserve frozen artifacts equivalent to:

- `frozen_system.json`
- `frozen_system_spec.md`
- `frozen_comparison_set_ledger.csv`
- `pre_reserve_pairwise_matrix_long.csv`
- `locked_protocol_settings.json`
- `frozen_stage1_feature_manifest.csv`
- `stage1_feature_registry.csv`
- `shortlist_ledger.csv`
- `provenance_declaration.json`

### Decision rule
No redesign, no retuning, and no leader substitution are allowed after reserve is opened.

## 15. Stage 7 — reserve/internal evaluation

### Input
The frozen winner and the frozen comparison set. Reserve window: `2024-10-01` to dataset end.

### Logic
Evaluate the frozen winner and every frozen comparison-set rival exactly once on reserve/internal. Report reserve separately from discovery and holdout. Do not reopen the search.

Reserve winner metrics at 20 bps round-trip cost:

- Sharpe: 0.873430172877608
- CAGR: 0.24164202060490902
- max drawdown: −0.24006039611162733
- trade-count field: 35
- exposure: 0.5357142857142857
- win rate: 0.47058823529411764
- mean trade return: 0.028326253857519936
- median trade return: −0.009932977384205066
- mean holding period: 16.647058823529413 bars
- median holding period: 7 bars
- top-5 winner concentration: 0.951833824623945

Reserve comparison-set summary at 20 bps:

| Candidate | Reserve Sharpe (20 bps RT) | Reserve CAGR (20 bps RT) | Reserve max DD (20 bps RT) | Reserve trade-count field |
| --- | --- | --- | --- | --- |
| `S_D1_TREND` | 0.8734 | 24.2% | −24.0% | 35 |
| `S_H4_TREND` | 0.6518 | 16.4% | −29.6% | 120 |
| `S_H4_TREND_Q` | 0.7716 | 16.4% | −22.5% | 72 |
| `S_XR_D1EMA` | 0.4552 | 9.6% | −32.9% | 108 |
| `S_XR_D1ROLL` | 0.8141 | 19.6% | −18.9% | 104 |
| `L2_D1_TREND_AND_H4_VOLQUIET` | 0.6445 | 8.6% | −14.2% | 47 |
| `L2_D1_VOLHIGH_AND_H4_PULLBACK` | 0.4394 | 5.5% | −13.3% | 24 |

Cost stress at 50 bps round-trip cost:

- `S_D1_TREND`: CAGR 19.8%, Sharpe 0.7518
- `S_H4_TREND`: CAGR 2.9%, Sharpe 0.2447
- `S_H4_TREND_Q`: CAGR 8.1%, Sharpe 0.4473
- `S_XR_D1EMA`: CAGR −1.9%, Sharpe 0.0885
- `S_XR_D1ROLL`: CAGR 7.5%, Sharpe 0.4018
- `L2_D1_TREND_AND_H4_VOLQUIET`: CAGR 3.5%, Sharpe 0.3071
- `L2_D1_VOLHIGH_AND_H4_PULLBACK`: CAGR 2.9%, Sharpe 0.2705

### Output
A reserve report equivalent to `reserve_internal_summary.csv` and the reserve rows in `validation_results.csv`.

### Decision rule
Reserve may corroborate or weaken confidence in the frozen leader. Reserve may **not** retroactively promote a different winner. V8 therefore does not permit any redesign after reserve is observed.

## 16. Evidence label hierarchy

### Input
The frozen pre-reserve selection process and reserve/internal results.

### Logic
Assign one label from the three-level hierarchy:

1. `CLEAN OOS CONFIRMED`
   - requires globally independent out-of-sample data not contained in the current source file pair.

2. `INTERNAL ROBUST CANDIDATE`
   - requires procedurally independent within-session selection,
   - positive reserve/internal confirmation,
   - but discovery, holdout, and reserve still all come from the same historical file pair.

3. `NO ROBUST IMPROVEMENT`
   - used when no candidate survives the freeze with credible evidence.

### Output
Winner evidence label: `INTERNAL ROBUST CANDIDATE`.

### Decision rule
The current BTC/USDT file pair cannot produce `CLEAN OOS CONFIRMED` because discovery, holdout, and reserve are all slices of the same file pair.

## 17. Provenance and independence claims

### Input
The actual artifacts consulted before freeze.

### Logic
Declare both independence claims separately.

- Procedural independence before freeze: **YES**
  - before freeze, no prior reports, prior logs, prior shortlist tables, prior frozen candidates, prior JSON outputs, prior system specifications, or benchmark specifications were consulted.
  - only admissible raw inputs were consulted before freeze.

- Global cross-session split independence: **NO**
  - discovery, holdout, and reserve are all from the same historical file pair.
  - reserve is internal only, not clean OOS.

### Output
A provenance declaration equivalent to `provenance_declaration.json`.

### Decision rule
Never conflate within-session procedural separation with genuinely independent out-of-sample evidence.

## 18. Complexity budget and finality

### Input
The locked search discipline.

### Logic
Apply the hard complexity budget:

- max 3 logical layers,
- max 1 slower contextual layer,
- max 1 faster state layer,
- max 1 optional entry-only confirmation layer,
- max 6 tunable quantities in the final frozen candidate,
- no regime-specific parameter sets.

After reserve/internal is reported, same-file prompt iteration stops.

### Output
- final same-file audit statement:
  - “This V8 run is the final same-file audit on the current BTC/USDT file pair.”
- stop condition:
  - “After reserve/internal evaluation is reported, same-file prompt iteration stops; stronger claims require appended future data.”

### Decision rule
Any stronger claim now requires appended future data, not more same-file protocol iteration.
