# BTCUSDT V6 Research Reproduction Spec

## Document purpose

This document is a complete rebuild specification for the full V6 research process that started from two raw CSV files and ended with the frozen pre-reserve winner `S3_H4_RET168_Z0`. It is written so that an engineer can recreate the research without chat history, earlier code, or any other documentation.

The frozen winner chosen before reserve/internal was:

- candidate ID: `S3_H4_RET168_Z0`
- family: simple native H4 trend state
- rule: long when H4 168-bar return is positive at H4 close; otherwise flat
- execution: next H4 open
- evidence label after full run: `INTERNAL ROBUST CANDIDATE`

This document separates the research pipeline from the final frozen system. The final frozen system is specified again in a separate standalone document.

## Required input files

Exactly two input files are required.

### File 1: raw H4 file

- expected filename: any filename is acceptable
- required content: native BTC/USDT H4 bars
- expected row count in the supplied run: 18,791
- expected `interval` value in all rows: `4h`

### File 2: raw D1 file

- expected filename: any filename is acceptable
- required content: native BTC/USDT D1 bars
- expected row count in the supplied run: 3,134
- expected `interval` value in all rows: `1d`

### Required schema for both files

| column              | type    | required   | description                                                        |
|:--------------------|:--------|:-----------|:-------------------------------------------------------------------|
| symbol              | string  | yes        | instrument symbol; all rows in supplied files are BTCUSDT          |
| interval            | string  | yes        | bar interval literal; H4 file contains `4h`, D1 file contains `1d` |
| open_time           | int64   | yes        | UTC bar open timestamp in Unix epoch milliseconds                  |
| close_time          | int64   | yes        | UTC bar close timestamp in Unix epoch milliseconds                 |
| open                | float64 | yes        | bar open price                                                     |
| high                | float64 | yes        | bar high price                                                     |
| low                 | float64 | yes        | bar low price                                                      |
| close               | float64 | yes        | bar close price                                                    |
| volume              | float64 | yes        | base-asset traded volume during bar                                |
| quote_volume        | float64 | yes        | quote-asset traded volume during bar                               |
| num_trades          | int64   | yes        | trade count during bar                                             |
| taker_buy_base_vol  | float64 | yes        | base-asset volume of taker buys during bar                         |
| taker_buy_quote_vol | float64 | yes        | quote-asset volume of taker buys during bar                        |

### Required file format rules

- encoding: UTF-8 CSV
- timestamp units: Unix epoch milliseconds in UTC
- numeric parsing: parse all numeric fields as IEEE-754 double precision floats except `num_trades`, `open_time`, and `close_time`, which are integers
- no synthetic bars may be added
- no missing bars may be filled
- no resampling of raw OHLCV into alternative bar sizes is allowed

## Locked protocol and admissible inputs

### Admissible quantitative inputs before freeze

The only admissible inputs before freezing the winner and frozen comparison set are:

- `RESEARCH_PROMPT_V6.md`
- the raw H4 CSV
- the raw D1 CSV

Before freeze, the researcher may **not** consult prior reports, prior shortlist tables, prior frozen candidate tables, prior system JSON, benchmark specifications, or any artifact from an earlier session.

### Locked execution assumptions

- market: BTC/USDT spot
- direction: long-only
- signal timing: compute signal at bar close
- fill model: execute at next bar open
- base cost model: 10 bps per side, 20 bps round-trip
- stress cost model: 25 bps per side, 50 bps round-trip
- warmup: no live trading before `2020-01-01 00:00:00+00:00`
- cross-timeframe alignment: only the most recently completed slower bar is visible to a faster bar, using backward as-of alignment on slower `close_time`
- native bars only: no synthetic OHLCV resampling

### Complexity budget

- maximum logical layers in the final candidate: 3
- maximum slower contextual layers: 1
- maximum faster state layers: 1
- maximum optional entry-only confirmation layers: 1
- maximum tunable quantities in the frozen final candidate: 6
- no regime-specific parameter sets
- no leverage
- no pyramiding
- no discretionary overrides

## Deterministic preprocessing specification

Every reconstruction must apply the following preprocessing order exactly.

### Step 1 — Parse timestamps

**Input:** raw H4 CSV, raw D1 CSV.

**Logic:** parse `open_time` and `close_time` from epoch milliseconds into timezone-aware UTC datetimes called `open_dt` and `close_dt`.

**Output:** two parsed DataFrames, one H4 and one D1.

**Decision rule:** if any timestamp fails to parse, stop and report a fatal data error. The supplied run had no parse failures.

### Step 2 — Stable chronological sort

**Input:** parsed H4 and D1 DataFrames.

**Logic:** perform a stable ascending sort by `open_dt`, then by `close_dt`, then reset the integer index to zero-based contiguous row numbers.

**Output:** chronologically ordered H4 and D1 frames.

**Decision rule:** these sorted row numbers become the canonical row indices used in every later step. No later step may reorder rows.

### Step 3 — Audit structural anomalies

**Input:** sorted H4 and D1 frames.

**Logic:** audit duplicates, missing values, malformed rows, irregular gaps, nonstandard durations, and zero-activity rows.

Definitions used in the run:

- duplicate `open_time` row: another row shares the same raw `open_time`
- duplicate `close_time` row: another row shares the same raw `close_time`
- irregular gap row: gap between current `open_dt` and previous `open_dt` differs from the native interval
- nonstandard duration row: `close_dt - open_dt` differs from the native bar duration implied by the file
- zero-activity row: `volume == 0` or `num_trades == 0`

**Output:** written audit report and machine-readable audit tables.

**Decision rule:** if anomalies materially break the next-open execution assumption, stop before discovery. In the supplied run the anomalies were logged but not judged fatal, so research continued.

## Exact anomaly findings and handling

### H4 anomalies found in the supplied run

- 19 nonstandard-duration rows
- 8 irregular-gap rows
- 1 duplicate `close_time` row
- 1 zero-activity row
- 0 duplicate `open_time` rows
- 0 rows with any missing value

### D1 anomalies found in the supplied run

- 0 nonstandard-duration rows
- 0 irregular-gap rows
- 0 duplicate `open_time` rows
- 0 duplicate `close_time` rows
- 0 zero-activity rows
- 0 rows with any missing value

### Required handling of every anomaly type

#### 19 shortened H4 bars

**Input:** 19 H4 rows whose observed duration differs from the native 4-hour bar duration.

**Logic:** retain each shortened H4 row exactly as supplied. Do not expand, merge, drop, normalize, or fill time.

**Output:** the original rows remain in the canonical H4 frame.

**Decision rule:** retain unchanged. Rationale: the prompt forbids silent repair and the anomalies did not invalidate next-open execution. Retaining them preserves raw-feed fidelity and exact row-count-based feature alignment.

#### 8 H4 timing gaps

**Input:** 8 H4 rows whose `open_dt` is more than 4 hours after the previous `open_dt`.

**Logic:** retain the gap exactly as supplied. Do not invent intermediate bars.

**Output:** the next available raw H4 row remains the next executable bar.

**Decision rule:** retain unchanged. Rationale: native raw bars only; missing price bars may not be fabricated.

#### 1 duplicate `close_time` zero-duration row

**Input:** the H4 row at sorted raw row index 123:

- `open_dt = 2017-09-06 16:00:00+00:00`
- `close_dt = 2017-09-06 16:00:00+00:00`
- `open = high = low = close = 4619.43`
- `volume = 0`
- `num_trades = 0`

**Logic:** retain the row exactly as supplied. Do not de-duplicate.

**Output:** the row stays in the sorted H4 frame and contributes to row-count-based shifts.

**Decision rule:** retain unchanged. Rationale: the prompt forbids silent repair, the row lies in pre-live history, and deleting it would change every later `shift(168)` alignment relative to the original run.

### Consequence of anomaly retention

All `shift(L)` operations are row-count based on the fully retained sorted raw frame. The duplicate zero-duration row and every shortened or gapped row remain part of the row index. Any implementation that removes or repairs those rows will not reproduce the same features, signals, or trades.

## Exact data coverage

### H4 coverage in the supplied run

- first `open_dt`: `2017-08-17 04:00:00+00:00`
- last `open_dt`: `2026-03-17 12:00:00+00:00`
- first `close_dt`: `2017-08-17 07:59:59.999+00:00`
- last `close_dt`: `2026-03-17 15:59:59.999+00:00`

### D1 coverage in the supplied run

- first `open_dt`: `2017-08-17 00:00:00+00:00`
- last `open_dt`: `2026-03-16 00:00:00+00:00`
- first `close_dt`: `2017-08-17 23:59:59.999+00:00`
- last `close_dt`: `2026-03-16 23:59:59.999+00:00`

### Cross-timeframe raw-data reconciliation

Aggregate native H4 bars into UTC calendar days and compare day-level OHLC against the raw D1 file over overlapping dates. The supplied run reconciled exactly on overlapping days. That audit must pass before feature research proceeds.

## Exact data split architecture

Split assignment is done by **sorted-row `open_dt` date**, not by `close_dt`, and not by row-count slicing.

### Primary partitions

| timeframe   | partition                   | start_date_inclusive   | end_date_inclusive   |   start_row_index |   end_row_index |   row_count | share_of_live_rows   |
|:------------|:----------------------------|:-----------------------|:---------------------|------------------:|----------------:|------------:|:---------------------|
| H4          | context_warmup_only         | 2017-08-17             | 2019-12-31           |                 0 |            5185 |        5186 |                      |
| H4          | discovery                   | 2020-01-01             | 2022-12-31           |              5186 |           11760 |        6575 | 0.483278             |
| H4          | candidate_selection_holdout | 2023-01-01             | 2024-06-30           |             11761 |           15042 |        3282 | 0.241235             |
| H4          | reserve_internal            | 2024-07-01             | 2026-03-17           |             15043 |           18790 |        3748 | 0.275487             |
| D1          | context_warmup_only         | 2017-08-17             | 2019-12-31           |                 0 |             866 |         867 |                      |
| D1          | discovery                   | 2020-01-01             | 2022-12-31           |               867 |            1962 |        1096 | 0.483458             |
| D1          | candidate_selection_holdout | 2023-01-01             | 2024-06-30           |              1963 |            2509 |         547 | 0.241288             |
| D1          | reserve_internal            | 2024-07-01             | 2026-03-16           |              2510 |            3133 |         624 | 0.275254             |

### Live-row ratios in the supplied run

- H4 live rows: discovery 48.33%, holdout 24.12%, reserve/internal 27.55%
- D1 live rows: discovery 48.35%, holdout 24.13%, reserve/internal 27.53%

### Discovery walk-forward folds

Within the discovery window, use six semiannual non-overlapping unseen test folds. Calibration data is every row strictly earlier than the fold start.

| timeframe   |   fold_idx | test_start   | test_end   | train_end_exclusive   |   start_row_index |   end_row_index |   row_count |
|:------------|-----------:|:-------------|:-----------|:----------------------|------------------:|----------------:|------------:|
| H4          |          0 | 2020-01-01   | 2020-06-30 | 2020-01-01            |              5186 |            6276 |        1091 |
| H4          |          1 | 2020-07-01   | 2020-12-31 | 2020-07-01            |              6277 |            7380 |        1104 |
| H4          |          2 | 2021-01-01   | 2021-06-30 | 2021-01-01            |              7381 |            8466 |        1086 |
| H4          |          3 | 2021-07-01   | 2021-12-31 | 2021-07-01            |              8467 |            9570 |        1104 |
| H4          |          4 | 2022-01-01   | 2022-06-30 | 2022-01-01            |              9571 |           10656 |        1086 |
| H4          |          5 | 2022-07-01   | 2022-12-31 | 2022-07-01            |             10657 |           11760 |        1104 |
| D1          |          0 | 2020-01-01   | 2020-06-30 | 2020-01-01            |               867 |            1048 |         182 |
| D1          |          1 | 2020-07-01   | 2020-12-31 | 2020-07-01            |              1049 |            1232 |         184 |
| D1          |          2 | 2021-01-01   | 2021-06-30 | 2021-01-01            |              1233 |            1413 |         181 |
| D1          |          3 | 2021-07-01   | 2021-12-31 | 2021-07-01            |              1414 |            1597 |         184 |
| D1          |          4 | 2022-01-01   | 2022-06-30 | 2022-01-01            |              1598 |            1778 |         181 |
| D1          |          5 | 2022-07-01   | 2022-12-31 | 2022-07-01            |              1779 |            1962 |         184 |

### Meaning of the partitions

- `context_warmup_only`: historical context and calibration only, never scored for live performance
- `discovery`: the only zone allowed for Stage 1 measurement, hypothesis generation, coarse search, local refinement, and internal model comparison
- `candidate_selection_holdout`: sealed until discovery has produced a conceptually frozen winner and frozen comparison set
- `reserve_internal`: sealed until exact frozen system and exact frozen comparison set are exported; this period is internal only under V6 and is **not** eligible for a clean OOS label

## Feature-engineering primitives

All engineered features are built from the sorted native frames with the following helper quantities and conventions.

### Helper quantities

- `prev_close_t = close_(t-1)` on the same native frame
- `log_close_ret_t = ln(close_t / close_(t-1))`
- `taker_share_raw_t = taker_buy_base_vol_t / volume_t`; if `volume_t == 0`, set `taker_share_raw_t = NaN`
- `rolling_mean(x, L)`: simple arithmetic mean over the current row and previous `L-1` retained rows, with `min_periods = L`
- `rolling_std(x, L)`: sample standard deviation with `ddof = 1`, current row included, `min_periods = L`
- `rolling_max(close, L)`: rolling maximum of `close` over current and previous `L-1` rows
- `rolling_high(L)`: rolling maximum of `high` over current and previous `L-1` rows
- `rolling_low(L)`: rolling minimum of `low` over current and previous `L-1` rows
- `weekday`: integer weekday of `open_dt`, Monday `0` through Sunday `6`
- `slot_hour`: H4 `open_dt.hour`, so possible values in raw H4 are `0, 4, 8, 12, 16, 20`

### Zero-denominator and insufficient-history rule

If any feature formula requires division by zero or lacks enough history, the feature value is `NaN`. `NaN` feature values produce a flat signal.

### Cross-timeframe visibility rule

When a D1-derived feature is attached to H4 rows, it is aligned by backward as-of merge on `close_dt`. An H4 row at close time `t` may only see the most recent D1 row whose `close_dt <= t`.

## Full Stage 1 feature library

The run executed 2,219 single-feature long/flat configurations: 703 native D1, 731 native H4, and 785 H4 cross-timeframe configurations.

### Thresholding modes

- `fixed_zero`: threshold is exactly `0.0`
- `fixed_level`: threshold is the numeric `threshold_param`
- `train_quantile`: threshold for each discovery fold is the quantile of the feature values in the fold's calibration sample, using all rows with `open_dt < fold_start`
- `category`: signal is long if the bar's category equals the chosen scalar category or belongs to the chosen category set

### Tail semantics

- `upper`: long if `feature > threshold`
- `lower`: long if `feature < threshold`

### Native D1 feature manifest

| bucket    | timeframe   | feature_name   | family                  | formula                                                                       | params                      | tails        | calibration_modes           | threshold_params                             |
|:----------|:------------|:---------------|:------------------------|:------------------------------------------------------------------------------|:----------------------------|:-------------|:----------------------------|:---------------------------------------------|
| native_d1 | D1          | atr_pct        | volatility_level        | rolling_mean(true_range, L) / close                                           | 5, 10, 20, 40               | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| native_d1 | D1          | body_frac      | candle_structure        | rolling_mean(abs(close - open) / (high - low), L)                             | 1, 3, 5, 10                 | lower, upper | fixed_level                 | 0.2, 0.4, 0.6                                |
| native_d1 | D1          | close_in_bar   | candle_structure        | rolling_mean((close - low) / (high - low), L)                                 | 1, 3, 5, 10                 | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| native_d1 | D1          | dir_body       | candle_structure        | rolling_mean((close - open) / (high - low), L)                                | 1, 3, 5, 10                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| native_d1 | D1          | drawdown       | drawdown_pullback       | close / rolling_max(close, L) - 1                                             | 3, 5, 10, 20, 40, 80        | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| native_d1 | D1          | flow_impulse   | participation_flow      | rolling_mean((2*taker_share_raw - 1) * (volume / rolling_mean(volume, L)), L) | 5, 10, 20, 40               | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| native_d1 | D1          | ma_gap         | trend_quality           | close / rolling_mean(close, L) - 1                                            | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| native_d1 | D1          | range_loc      | location_within_range   | (close - rolling_low(L)) / (rolling_high(L) - rolling_low(L))                 | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| native_d1 | D1          | ret            | directional_persistence | close / close.shift(L) - 1                                                    | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| native_d1 | D1          | taker_share    | participation_flow      | rolling_mean(taker_buy_base_vol / volume, L)                                  | 5, 10, 20, 40               | lower, upper | fixed_level                 | 0.45, 0.5, 0.55, 0.6                         |
| native_d1 | D1          | trend_quality  | trend_quality           | (close / close.shift(L) - 1) / (rolling_std(log_close_ret, L) * sqrt(L))      | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| native_d1 | D1          | up_frac        | directional_persistence | rolling_mean(close.diff() > 0, L)                                             | 3, 5, 10, 20, 40            | lower, upper | fixed_level                 | 0.4, 0.5, 0.6, 0.7                           |
| native_d1 | D1          | vol_cluster    | volatility_clustering   | rolling_std(log_close_ret, short) / rolling_std(log_close_ret, long)          | (5, 20), (10, 40), (20, 80) | lower, upper | fixed_level, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5     |
| native_d1 | D1          | volume_ratio   | participation_flow      | volume / rolling_mean(volume, L)                                              | 5, 10, 20, 40               | lower, upper | fixed_level                 | 0.8, 1.0, 1.2, 1.5                           |
| native_d1 | D1          | weekday        | calendar_effect         | bar weekday category                                                          | None                        | category     | category                    | (0, 1, 2, 3, 4), 0, 1, 2, 3, 4, (5, 6), 5, 6 |

### Native H4 feature manifest

| bucket    | timeframe   | feature_name   | family                  | formula                                                                       | params                                 | tails        | calibration_modes           | threshold_params                                        |
|:----------|:------------|:---------------|:------------------------|:------------------------------------------------------------------------------|:---------------------------------------|:-------------|:----------------------------|:--------------------------------------------------------|
| native_h4 | H4          | atr_pct        | volatility_level        | rolling_mean(true_range, L) / close                                           | 12, 24, 48, 96                         | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| native_h4 | H4          | body_frac      | candle_structure        | rolling_mean(abs(close - open) / (high - low), L)                             | 1, 3, 6, 12                            | lower, upper | fixed_level                 | 0.2, 0.4, 0.6                                           |
| native_h4 | H4          | close_in_bar   | candle_structure        | rolling_mean((close - low) / (high - low), L)                                 | 1, 3, 6, 12                            | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| native_h4 | H4          | dir_body       | candle_structure        | rolling_mean((close - open) / (high - low), L)                                | 1, 3, 6, 12                            | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| native_h4 | H4          | drawdown       | drawdown_pullback       | close / rolling_max(close, L) - 1                                             | 6, 12, 24, 48, 96, 168                 | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| native_h4 | H4          | flow_impulse   | participation_flow      | rolling_mean((2*taker_share_raw - 1) * (volume / rolling_mean(volume, L)), L) | 12, 24, 48, 96                         | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| native_h4 | H4          | ma_gap         | trend_quality           | close / rolling_mean(close, L) - 1                                            | 6, 12, 24, 48, 96, 168                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| native_h4 | H4          | range_loc      | location_within_range   | (close - rolling_low(L)) / (rolling_high(L) - rolling_low(L))                 | 6, 12, 24, 48, 96, 168                 | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                               |
| native_h4 | H4          | ret            | directional_persistence | close / close.shift(L) - 1                                                    | 6, 12, 24, 48, 96, 168                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| native_h4 | H4          | slot_hour      | calendar_effect         | H4 bar open-hour slot category                                                | None                                   | category     | category                    | (0, 4), 0, 4, (8, 12), 8, 12, (16, 20), 16, (20, 0), 20 |
| native_h4 | H4          | taker_share    | participation_flow      | rolling_mean(taker_buy_base_vol / volume, L)                                  | 12, 24, 48, 96                         | lower, upper | fixed_level                 | 0.45, 0.5, 0.55, 0.6                                    |
| native_h4 | H4          | trend_quality  | trend_quality           | (close / close.shift(L) - 1) / (rolling_std(log_close_ret, L) * sqrt(L))      | 6, 12, 24, 48, 96, 168                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None                         |
| native_h4 | H4          | up_frac        | directional_persistence | rolling_mean(close.diff() > 0, L)                                             | 6, 12, 24, 48, 96                      | lower, upper | fixed_level                 | 0.4, 0.5, 0.6, 0.7                                      |
| native_h4 | H4          | vol_cluster    | volatility_clustering   | rolling_std(log_close_ret, short) / rolling_std(log_close_ret, long)          | (6, 24), (12, 48), (24, 96), (48, 168) | lower, upper | fixed_level, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5                |
| native_h4 | H4          | volume_ratio   | participation_flow      | volume / rolling_mean(volume, L)                                              | 12, 24, 48, 96                         | lower, upper | fixed_level                 | 0.8, 1.0, 1.2, 1.5                                      |
| native_h4 | H4          | weekday        | calendar_effect         | bar weekday category                                                          | None                                   | category     | category                    | (0, 1, 2, 3, 4), 0, 1, 2, 3, 4, (5, 6), 5, 6            |

### Cross-timeframe relationship feature manifest

| bucket       | timeframe   | feature_name   | family                       | formula                                                                               | params            | tails        | calibration_modes          | threshold_params                |
|:-------------|:------------|:---------------|:-----------------------------|:--------------------------------------------------------------------------------------|:------------------|:-------------|:---------------------------|:--------------------------------|
| xtf_relation | H4          | h4_in_d1_range | cross_timeframe_relationship | (H4 close - last_completed_D1_low) / (last_completed_D1_high - last_completed_D1_low) | None              | lower, upper | fixed_level                | 0.2, 0.35, 0.5, 0.65, 0.8       |
| xtf_relation | H4          | h4_vs_d1_close | cross_timeframe_relationship | H4 close / last_completed_D1_close - 1                                                | None              | lower, upper | fixed_zero, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, None |
| xtf_relation | H4          | h4_vs_d1_ma    | cross_timeframe_relationship | H4 close / last_completed_D1_MA(L) - 1                                                | 5, 10, 20, 40, 80 | lower, upper | fixed_zero, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, None |

### Transported completed-D1 feature manifest

| bucket        | timeframe   | feature_name   | family                  | formula                                                                                                                                         | params                      | tails        | calibration_modes           | threshold_params                             |
|:--------------|:------------|:---------------|:------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------|:-------------|:----------------------------|:---------------------------------------------|
| xtf_transport | H4          | atr_pct        | volatility_level        | transport(last_completed_D1 rolling_mean(true_range, L) / close) onto H4 by backward as-of close_time                                           | 5, 10, 20, 40               | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| xtf_transport | H4          | body_frac      | candle_structure        | transport(last_completed_D1 rolling_mean(abs(close - open) / (high - low), L)) onto H4 by backward as-of close_time                             | 1, 3, 5, 10                 | lower, upper | fixed_level                 | 0.2, 0.4, 0.6                                |
| xtf_transport | H4          | close_in_bar   | candle_structure        | transport(last_completed_D1 rolling_mean((close - low) / (high - low), L)) onto H4 by backward as-of close_time                                 | 1, 3, 5, 10                 | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| xtf_transport | H4          | dir_body       | candle_structure        | transport(last_completed_D1 rolling_mean((close - open) / (high - low), L)) onto H4 by backward as-of close_time                                | 1, 3, 5, 10                 | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| xtf_transport | H4          | drawdown       | drawdown_pullback       | transport(last_completed_D1 close / rolling_max(close, L) - 1) onto H4 by backward as-of close_time                                             | 3, 5, 10, 20, 40, 80        | lower, upper | train_quantile              | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| xtf_transport | H4          | flow_impulse   | participation_flow      | transport(last_completed_D1 rolling_mean((2*taker_share_raw - 1) * (volume / rolling_mean(volume, L)), L)) onto H4 by backward as-of close_time | 5, 10, 20, 40               | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| xtf_transport | H4          | ma_gap         | trend_quality           | transport(last_completed_D1 close / rolling_mean(close, L) - 1) onto H4 by backward as-of close_time                                            | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| xtf_transport | H4          | range_loc      | location_within_range   | transport(last_completed_D1 (close - rolling_low(L)) / (rolling_high(L) - rolling_low(L))) onto H4 by backward as-of close_time                 | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_level                 | 0.2, 0.35, 0.5, 0.65, 0.8                    |
| xtf_transport | H4          | ret            | directional_persistence | transport(last_completed_D1 close / close.shift(L) - 1) onto H4 by backward as-of close_time                                                    | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| xtf_transport | H4          | taker_share    | participation_flow      | transport(last_completed_D1 rolling_mean(taker_buy_base_vol / volume, L)) onto H4 by backward as-of close_time                                  | 5, 10, 20, 40               | lower, upper | fixed_level                 | 0.45, 0.5, 0.55, 0.6                         |
| xtf_transport | H4          | trend_quality  | trend_quality           | transport(last_completed_D1 (close / close.shift(L) - 1) / (rolling_std(log_close_ret, L) * sqrt(L))) onto H4 by backward as-of close_time      | 3, 5, 10, 20, 40, 80        | lower, upper | fixed_zero, train_quantile  | 0.2, 0.35, 0.5, 0.65, 0.8, None              |
| xtf_transport | H4          | up_frac        | directional_persistence | transport(last_completed_D1 rolling_mean(close.diff() > 0, L)) onto H4 by backward as-of close_time                                             | 3, 5, 10, 20, 40            | lower, upper | fixed_level                 | 0.4, 0.5, 0.6, 0.7                           |
| xtf_transport | H4          | vol_cluster    | volatility_clustering   | transport(last_completed_D1 rolling_std(log_close_ret, short) / rolling_std(log_close_ret, long)) onto H4 by backward as-of close_time          | (5, 20), (10, 40), (20, 80) | lower, upper | fixed_level, train_quantile | 0.2, 0.35, 0.5, 0.65, 0.8, 1.0, 1.2, 1.5     |
| xtf_transport | H4          | volume_ratio   | participation_flow      | transport(last_completed_D1 volume / rolling_mean(volume, L)) onto H4 by backward as-of close_time                                              | 5, 10, 20, 40               | lower, upper | fixed_level                 | 0.8, 1.0, 1.2, 1.5                           |
| xtf_transport | H4          | weekday        | calendar_effect         | transport(last_completed_D1 bar weekday category) onto H4 by backward as-of close_time                                                          | None                        | category     | category                    | (0, 1, 2, 3, 4), 0, 1, 2, 3, 4, (5, 6), 5, 6 |

## Stage 1 executable-state conversion

### Step 4 — Compute every manifest feature on its native frame

**Input:** sorted H4 and D1 frames.

**Logic:** compute every manifest feature exactly from the formulas and parameter grids above. For native D1 features, compute on D1. For native H4 features, compute on H4. For transported D1 features, compute the completed-D1 feature on D1 first, then attach it to H4 by backward as-of on D1 `close_dt`. For direct H4-vs-D1 relationship features, use only completed D1 information visible at each H4 `close_dt`.

**Output:** feature columns on D1 and H4.

**Decision rule:** feature values remain `NaN` until enough retained history exists. No forward fill beyond backward as-of transport of already completed D1 state.

### Step 5 — Convert every feature configuration into an executable long/flat state system

**Input:** feature columns, a tail rule, a thresholding mode, and a threshold parameter.

**Logic:** create a binary state at bar close on the feature's native execution frame.

- single native D1 config: state defined on D1 close, executed at next D1 open
- single native H4 config: state defined on H4 close, executed at next H4 open
- transported D1-on-H4 config: state defined on H4 close using transported completed-D1 feature value, executed at next H4 open
- H4-vs-D1 relation config: state defined on H4 close using only completed D1 information, executed at next H4 open

For `train_quantile` configurations in discovery, calibrate one threshold per fold using only the fold's calibration sample.

Examples from the supplied run:

- `D1_RET40_Z0`: long if `close_t / close_(t-40) - 1 > 0` on D1 close
- `H4_RET168_Z0`: long if `close_t / close_(t-168) - 1 > 0` on H4 close
- `D1_VCL5_20_LT1.0`: long if `rolling_std(log_close_ret,5) / rolling_std(log_close_ret,20) < 1.0` on D1 close
- `XTF_TRANS_RET40_Z0`: long if transported completed-D1 40-day return visible on H4 close is positive

**Output:** executable binary long/flat states.

**Decision rule:** any `NaN` feature or exact threshold equality produces flat, not long.

### Step 6 — Apply next-open execution and net trading cost

**Input:** executable long/flat state on the execution frame.

**Logic:** execute at the next bar open on the same frame.

- if state changes `0 -> 1` at bar `t` close, enter at bar `t+1` open
- if state changes `1 -> 0` at bar `t` close, exit at bar `t+1` open
- if state stays `1`, remain long
- if state stays `0`, remain flat

Base transaction cost is applied inside the execution engine, not as a post-hoc metric haircut.

- entry side cost: 10 bps at the entry open
- exit side cost: 10 bps at the exit open
- no cost on bars where the position does not change

For a completed trade entered at open price `E` and exited at open price `X`, the net trade return is:

`trade_return = X * (1 - 0.001) / (E * (1 + 0.001)) - 1`

For stress testing at 50 bps round-trip, repeat evaluation with 25 bps per side.

**Output:** realized per-trade returns, realized bar-interval returns, daily returns, and summary metrics net of cost.

**Decision rule:** every Stage 1 registry metric is net of the 20 bps round-trip model.

## Metric formulas used in discovery and validation

### Daily return aggregation

Aggregate realized execution-frame interval multipliers to UTC calendar-day returns.

- H4 systems: group by H4 row `open_dt.floor('D')`
- D1 systems: each D1 row contributes directly to its UTC day

For a day `D`, daily return is `product_of_interval_multipliers_on_D - 1`.

### Daily exposure aggregation

For a day `D`, daily exposure is the mean long/flat position over execution-frame rows whose `open_dt.floor('D') == D`.

### Core metrics

- daily-return Sharpe: `mean(daily_returns) / std(daily_returns, ddof=1) * sqrt(365)`
- CAGR: `(ending_equity_multiple) ** (365.25 / n_calendar_days) - 1`
- max drawdown: minimum of `equity / rolling_equity_peak - 1` on the daily equity curve
- trade count: number of **completed** trades
- open trade count: number of trades still open at dataset end
- exposure: mean bar-level position on the execution frame over the scored period
- win rate: fraction of completed trades with `trade_return > 0`
- mean and median trade return: computed on completed trades only
- mean and median holding period: computed from completed trades only
- top-winner concentration: sum of the five largest positive completed-trade returns divided by the sum of all positive completed-trade returns
- bottom-tail damage: descriptive diagnostic exported in the original run; it did not affect any keep/drop or final-selection decision. The artifact bundle preserves the numeric outputs but does not expose its generating code path separately.

## Stage 1 screening and seriousness filter

### Step 7 — Score every Stage 1 configuration on discovery only

**Input:** every Stage 1 executable configuration.

**Logic:** evaluate each configuration across the six discovery folds under the next-open execution model and 20 bps round-trip cost. For `train_quantile` configurations, use a fold-specific threshold computed only from calibration data earlier than that fold's test start.

For each configuration, export at least:

- `sharpe_daily`
- `cagr`
- `max_drawdown`
- `trade_count`
- `exposure`
- `net_return`
- `mean_hold_bars`
- `median_hold_bars`
- `positive_fold_share`
- `min_fold_cagr`

The supplied run exported the full machine-readable Stage 1 registry with 2,219 rows.

**Output:** `stage1_feature_registry_full.csv`.

**Decision rule:** none at this stage; this step is exhaustive measurement.

### Step 8 — Apply the Stage 1 seriousness filter

**Input:** full Stage 1 registry.

**Logic:** mark a Stage 1 configuration as serious enough for frontier consideration only if it clears the discovery-side hard gate that can be checked before holdout:

- positive edge after 20 bps on aggregate discovery walk-forward
- at least 20 completed trades across all six discovery folds

There was **no separate numeric minimum Sharpe threshold**. Configurations were then ranked by discovery daily-return Sharpe after those gates.

Evidence that this was the actual filter in the supplied run:

- the exported top-100-by-discovery-Sharpe table contains no configuration with fewer than 21 trades
- `D1_RET40` with `train_quantile q=0.65` had the highest discovery Sharpe in its family, but only 17 trades, so it was not allowed to lead the robust simple frontier
- the winning H4 family representative `H4_RET168_Z0` had 82 discovery trades and positive discovery CAGR after cost

**Output:** serious-candidate pool for Stage 2.

**Decision rule:** keep only configurations with positive discovery edge after cost and `trade_count >= 20` for serious frontier consideration.

## Stage 2 orthogonal shortlist formation

### Step 9 — Nominate the strongest serious representative of each family and bucket

**Input:** Stage 1 serious-candidate pool.

**Logic:** within each bucket/family cluster, identify the strongest or most interpretable serious representative, usually by highest discovery Sharpe subject to the 20-trade filter and simplicity preference.

Key Stage 1 family leaders in the supplied run were:

- native D1 slow trend frontier: `S1_D1_RET40_Z0`
- native D1 slow low-volatility regime: `S2_D1_VCL5_20_LT1.0`
- native H4 fast trend frontier: `S3_H4_RET168_Z0`
- native H4 sparse timing anomaly: `S4_H4_UPFR48_LT0.4`
- cross-timeframe relation standout: `XTF_H4_D1MA40_U_q50`
- transported slower clone: `XTF_TRANS_RET40_Z0`
- additional serious native D1 families: `D1_RANGE40_U_065`, `D1_DRAWDOWN40_U_q65`, `D1_FLOW10_L_q20`

**Output:** family-leader candidate set for orthogonality review.

**Decision rule:** keep the simplest serious representative of each viable family alive unless a close sibling clearly dominates it on both robustness and interpretation.

### Step 10 — Compute orthogonality diagnostics

**Input:** family-leader candidate set.

**Logic:** compute pairwise daily-return correlations among the serious leaders over the scored discovery period.

Load-bearing findings from the supplied run:

- `D1_RET40_Z0` vs `XTF_TRANS_RET40_Z0`: correlation `1.000000` — perfect redundancy
- `H4_RET168_Z0` vs `XTF_H4_D1MA40_U_q50`: correlation `0.907946` — too similar to justify independent leadership
- `H4_RET168_Z0` vs `H4_UPFR48_L_04`: correlation `0.050039` — genuinely orthogonal

**Output:** orthogonality matrix and a keep/drop shortlist ledger.

**Decision rule:** transported slower information does not count as independent fast information unless paired evidence later proves incremental edge. Near-duplicates are pruned early.

### Step 11 — Build the shortlist ledger

**Input:** orthogonality diagnostics and Stage 1 family leaders.

**Logic:** explicitly record every keep/drop decision and the reason.

#### Candidates kept on the shortlist

| candidate                        | cluster                       | type           | spec_summary                                       | reason                                                                                                                             |
|:---------------------------------|:------------------------------|:---------------|:---------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------|
| S1_D1_RET40_Z0                   | simple_slow_trend             | single_native  | Native D1 40-day return > 0                        | Strong simple slower trend representative; broad local plateau around 32-48 days; credible simplest frontier.                      |
| S2_D1_VCL5_20_LT1.0              | simple_slow_vol_regime        | single_native  | Native D1 short/long volatility ratio (5,20) < 1.0 | Strong slower low-volatility regime representative; materially different failure mode versus pure trend.                           |
| S3_H4_RET168_Z0                  | simple_fast_trend             | single_native  | Native H4 168-bar return > 0                       | Strong simple native H4 trend state with broad plateau and better pre-reserve risk-adjusted performance than nearby simple rivals. |
| S4_H4_UPFR48_LT0.4               | simple_fast_timing_sparse     | single_native  | Native H4 up-bar fraction over 48 bars < 0.4       | Genuinely orthogonal sparse timing representative; very low correlation to trend cluster.                                          |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | layered_vol_gate_fast_trend   | layered_and_h4 | D1 low-volatility gate AND H4 trend state          | Best two-layer volatility-gated trend family; broad plateau in nearby cells.                                                       |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | layered_slow_trend_fast_trend | layered_and_h4 | D1 trend gate AND H4 trend state                   | Best two-layer trend-plus-trend family; strong headline pre-reserve metrics but must beat simpler frontier on paired tests.        |

#### Serious candidates dropped before layered comparison

| candidate           | cluster                  | type                         | spec_summary                                              | reason                                                                                                                                            |
|:--------------------|:-------------------------|:-----------------------------|:----------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------|
| XTF_TRANS_RET40_Z0  | transported_slow_clone   | cross_timeframe_transport    | D1 40-day return transported to H4                        | Perfectly redundant with native D1_RET40 representative (daily return correlation 1.00); transport does not add independent information.          |
| XTF_H4_D1MA40_U_q50 | cross_timeframe_relation | cross_timeframe_relationship | H4 close vs D1 MA40 relation, thresholded by train median | Strong discovery metrics but ~0.91 correlation with H4_RET168 trend cluster; not sufficiently orthogonal after paired comparison.                 |
| D1_RANGE40_U_065    | slow_trend_location      | single_native                | D1 range location over 40 bars > 0.65                     | Serious slower trend/location candidate but dominated by simpler D1_RET40 on explanatory clarity and similar unseen behavior.                     |
| D1_DRAWDOWN40_U_q65 | slow_drawdown_pullback   | single_native                | D1 drawdown state over 40 bars in upper train quantile    | Useful evidence that pullback state matters, but not sufficiently distinct from slower trend cluster to keep as separate frontier representative. |
| D1_FLOW10_L_q20     | participation_flow       | single_native                | D1 flow impulse over 10 bars in lower train quantile      | Meaningfully lower correlation to trend than many features, but weaker and less stable than retained short-list representatives.                  |
| H4_CLOSE6_L_035     | fast_candle_filter       | entry_only_confirmation      | H4 close-in-bar over 6 bars < 0.35                        | Entry-only filter improved selectivity in a few cells but generally reduced trade count too far and did not justify a third layer.                |
| H4_BODY6_U_06       | fast_candle_filter       | entry_only_confirmation      | H4 body fraction over 6 bars > 0.6                        | No consistent incremental edge once layered on top of already-strong two-layer cores.                                                             |
| H4_FLOW24_Z0        | fast_flow_filter         | entry_only_confirmation      | H4 flow impulse over 24 bars > 0                          | Third-layer confirmation reduced robustness and added complexity without a clear paired advantage.                                                |

**Output:** `shortlist_ledger.csv`.

**Decision rule:** keep orthogonal representatives and nearest internal rivals; drop perfect transports, near-duplicates, and weaker variants dominated by simpler representatives.

## Stage 3 minimal layered architectures

### Step 12 — Construct two-layer candidate families

**Input:** surviving slow contextual representatives and the native H4 fast trend frontier.

**Logic:** test minimal two-layer systems where a slower state acts as a permission gate and H4 trend acts as the state controller. The supplied run produced three notable layered cores:

- `CORE_VCL_RET168`: D1 low-volatility gate AND H4 168-bar trend state
- `CORE_RET40_RET168`: D1 40-bar trend gate AND H4 168-bar trend state
- `CORE_ATR20_RET168`: D1 ATR-percent gate AND H4 168-bar trend state

The two layered cores that survived into named finalists were:

- `L1_VCL5_20_LT1.0_AND_H4RET168_Z0`
- `L2_D1RET40_Z0_AND_H4RET168_Z0`

**Output:** layered-candidate set.

**Decision rule:** layering is allowed only if it remains within the complexity budget and earns its place through later ablation and paired comparison.

### Step 13 — Test optional entry-only third-layer filters

**Input:** strong two-layer cores and candidate fast entry filters.

**Logic:** add fast H4 filters only at entry, not by default to hold/exit, and measure whether they improve selectivity without destroying robustness.

The supplied run tested the following entry-filter matrix:

| core              | entry_filter    |   sharpe_daily |      cagr |   trade_count |   positive_fold_share |   min_fold_cagr |
|:------------------|:----------------|---------------:|----------:|--------------:|----------------------:|----------------:|
| CORE_VCL_RET168   | (none)          |       1.86025  | 0.978235  |           115 |              0.833333 |     -0.220709   |
| CORE_RET40_RET168 | (none)          |       1.78391  | 1.04565   |            49 |              0.666667 |     -0.337736   |
| CORE_RET40_RET168 | H4_BODY6_U_06   |       1.65047  | 0.75482   |            14 |              0.833333 |     -0.0609164  |
| CORE_RET40_RET168 | H4_CLOSE6_L_035 |       1.47689  | 0.600694  |            15 |              0.666667 |     -0.248334   |
| CORE_RET40_RET168 | H4_FLOW24_Z0    |       1.33022  | 0.591571  |            25 |              0.666667 |     -0.425374   |
| CORE_ATR20_RET168 | (none)          |       1.30342  | 0.479064  |            44 |              1        |      0.0283106  |
| CORE_RET40_RET168 | H4_ATR48_U_q65  |       1.26679  | 0.48423   |            13 |              0.666667 |     -0.155064   |
| CORE_VCL_RET168   | H4_FLOW24_Z0    |       1.26492  | 0.402656  |            47 |              1        |      0.00938611 |
| CORE_VCL_RET168   | H4_BODY6_U_06   |       1.24405  | 0.248459  |            27 |              0.833333 |     -0.167345   |
| CORE_ATR20_RET168 | H4_ATR48_U_q65  |       1.21961  | 0.416022  |            19 |              1        |      0.0196718  |
| CORE_ATR20_RET168 | H4_CLOSE6_L_035 |       1.18468  | 0.32658   |            13 |              0.833333 |     -0.246159   |
| CORE_VCL_RET168   | H4_UPFR48_L_04  |       1.16933  | 0.107438  |             8 |              0.666667 |     -0.0766067  |
| CORE_ATR20_RET168 | H4_UPFR48_L_04  |       1.03908  | 0.103957  |             3 |              0.333333 |     -0.00363388 |
| CORE_ATR20_RET168 | H4_FLOW24_Z0    |       0.910057 | 0.260314  |            21 |              0.833333 |      0          |
| CORE_VCL_RET168   | H4_ATR48_U_q65  |       0.901559 | 0.238928  |            28 |              1        |      0.00809243 |
| CORE_ATR20_RET168 | H4_BODY6_U_06   |       0.802497 | 0.151196  |            12 |              0.666667 |     -0.192818   |
| CORE_VCL_RET168   | H4_CLOSE6_L_035 |       0.677182 | 0.126563  |            26 |              0.666667 |     -0.076772   |
| CORE_RET40_RET168 | H4_UPFR48_L_04  |       0.548417 | 0.0947296 |             8 |              0.5      |     -0.18921    |

Only three entry filters were serious enough to receive explicit drop reasons in the shortlist ledger:

- `H4_CLOSE6_L_035`
- `H4_BODY6_U_06`
- `H4_FLOW24_Z0`

All were dropped because they reduced trade count too far or added complexity without a clear paired advantage.

**Output:** entry-only filter search table.

**Decision rule:** no third layer survives unless it improves the already-robust two-layer core enough to justify the extra complexity. None did.

## Stage 4 coarse search then local refinement

### Step 14 — Refine only around serious families

**Input:** serious simple and layered families from Stages 1–3.

**Logic:** around each serious family, test nearest-grid-equivalent perturbations satisfying the protocol requirement of at least ±20% or nearest tested equivalent on every tunable quantity.

The supplied run exported full refinement grids for:

- D1 return family: 12 cells
- H4 return family: 12 cells
- D1 volatility-cluster family: 15 cells
- H4 up-fraction family: 9 cells
- D1-return gate + H4-return state layered family: 144 cells
- D1-vol-cluster gate + H4-return state layered family: 180 cells

**Output:** six plateau tables.

**Decision rule:** refine only around broad stable regions. The protocol locked a perturbation minimum, not a numeric Sharpe-retention ratio. A plateau is accepted if the neighborhood remains positive after cost and does not collapse into a narrow isolated spike.

### Step 15 — Choose the family representative from the plateau center, not the single highest spike

**Input:** plateau grids.

**Logic:** for each serious family, choose a representative that balances:

- discovery Sharpe after cost
- discovery CAGR after cost
- trade count
- positive-fold share
- minimum fold CAGR
- simplicity
- centrality within a broad plateau

Key local-refinement evidence from the supplied run:

#### D1 return family key cells

|   lookback | mode           |    thr |   sharpe_daily |     cagr |   trade_count |   positive_fold_share |   min_fold_cagr |
|-----------:|:---------------|-------:|---------------:|---------:|--------------:|----------------------:|----------------:|
|         40 | train_quantile |   0.65 |        1.72159 | 0.88475  |            17 |              0.666667 |      -0.0783101 |
|         40 | fixed_zero     | nan    |        1.55674 | 0.907849 |            29 |              0.666667 |      -0.388853  |
|         32 | train_quantile |   0.5  |        1.51038 | 0.82436  |            34 |              0.666667 |      -0.475431  |
|         32 | train_quantile |   0.65 |        1.46977 | 0.659714 |            30 |              0.833333 |      -0.216897  |
|         32 | fixed_zero     | nan    |        1.46176 | 0.8249   |            36 |              0.666667 |      -0.446214  |
|         40 | train_quantile |   0.5  |        1.44551 | 0.785625 |            33 |              0.666667 |      -0.589096  |

Interpretation:

- `lookback = 40`, `fixed_zero` gave discovery Sharpe `1.556736`, discovery CAGR `0.907849`, and 29 trades
- `lookback = 40`, `train_quantile q=0.65` gave higher Sharpe `1.721590` but only 17 trades, failing the 20-trade hard gate for robust candidacy
- the broad defensible slower-trend representative therefore became `S1_D1_RET40_Z0`

#### H4 return family key cells

|   lookback | mode           |    thr |   sharpe_daily |     cagr |   trade_count |   positive_fold_share |   min_fold_cagr |
|-----------:|:---------------|-------:|---------------:|---------:|--------------:|----------------------:|----------------:|
|        168 | train_quantile |   0.5  |        1.63312 | 0.950578 |            94 |              0.666667 |       -0.530549 |
|        168 | fixed_zero     | nan    |        1.63222 | 0.984197 |            82 |              0.666667 |       -0.502287 |
|        168 | train_quantile |   0.65 |        1.57589 | 0.754616 |            64 |              0.666667 |       -0.100136 |
|        202 | fixed_zero     | nan    |        1.54629 | 0.895838 |            72 |              0.666667 |       -0.338842 |
|        202 | train_quantile |   0.5  |        1.50094 | 0.824213 |            80 |              0.666667 |       -0.438695 |
|        202 | train_quantile |   0.65 |        1.47799 | 0.707986 |            73 |              0.666667 |       -0.355008 |
|        202 | train_quantile |   0.35 |        1.22046 | 0.656354 |            77 |              0.666667 |       -0.459336 |
|        168 | train_quantile |   0.35 |        1.17949 | 0.616889 |            91 |              0.666667 |       -0.427859 |

Interpretation:

- `lookback = 168`, `train_quantile q=0.50` had discovery Sharpe `1.633117`
- `lookback = 168`, `fixed_zero` had discovery Sharpe `1.632222` and higher discovery CAGR `0.984197`
- `lookback = 202`, `fixed_zero` stayed strong with Sharpe `1.546287`
- `lookback = 134`, `fixed_zero` stayed positive with Sharpe `1.082488`

The final H4 family representative was `S3_H4_RET168_Z0` because the `168/fixed_zero` cell sat in the center of a broad robust region, gave essentially the same discovery Sharpe as the `q=0.50` tuned variant, produced higher discovery CAGR, and removed foldwise threshold recalibration.

#### D1 volatility-cluster family key cells

| pair    | mode           |   thr |   sharpe_daily |     cagr |   trade_count |   positive_fold_share |   min_fold_cagr |
|:--------|:---------------|------:|---------------:|---------:|--------------:|----------------------:|----------------:|
| (5, 20) | train_quantile |  0.65 |        1.33419 | 0.812205 |           110 |              0.833333 |       -0.479465 |
| (5, 20) | fixed_level    |  1    |        1.31154 | 0.782865 |           108 |              0.833333 |       -0.446426 |
| (6, 24) | train_quantile |  0.5  |        1.2738  | 0.672977 |           104 |              0.833333 |       -0.243446 |
| (6, 24) | train_quantile |  0.65 |        1.18069 | 0.659298 |            97 |              0.666667 |       -0.302362 |
| (6, 24) | fixed_level    |  1    |        1.1689  | 0.641832 |           103 |              0.666667 |       -0.357423 |
| (5, 20) | fixed_level    |  1.2  |        1.11913 | 0.645122 |            75 |              0.833333 |       -0.465753 |

Interpretation:

- the strongest cells clustered around pair `(5,20)` and thresholds near `1.0`
- `train_quantile q=0.65` had slightly better discovery Sharpe
- `fixed_level 1.0` was nearly as strong and materially simpler

The family representative therefore became `S2_D1_VCL5_20_LT1.0`.

#### H4 sparse up-fraction timing family key cells

|   lookback |   thr |   sharpe_daily |       cagr |   trade_count |   positive_fold_share |   min_fold_cagr |
|-----------:|------:|---------------:|-----------:|--------------:|----------------------:|----------------:|
|         48 |  0.4  |       1.58595  |  0.277391  |            62 |              0.833333 |     0           |
|         60 |  0.45 |       0.920685 |  0.215855  |            92 |              0.5      |    -0.318446    |
|         60 |  0.35 |       0.881802 |  0.0460523 |             4 |              0.333333 |     0           |
|         48 |  0.45 |       0.772585 |  0.204243  |           129 |              0.833333 |    -0.500237    |
|         60 |  0.4  |       0.554128 |  0.0404391 |            10 |              0.666667 |    -0.000852148 |
|         36 |  0.35 |       0.331695 |  0.0242638 |            11 |              0.333333 |    -0.0811783   |
|         36 |  0.4  |       0.23352  |  0.0269386 |            91 |              0.5      |    -0.295528    |
|         48 |  0.35 |       0.176651 |  0.0098097 |             4 |              0.333333 |    -0.0125902   |
|         36 |  0.45 |      -0.044918 | -0.109161  |           181 |              0.5      |    -0.486954    |

Interpretation:

- `lookback = 48`, threshold `0.40` was the clear sparse-timing representative
- the family was orthogonal but sparse and lower-growth

The family representative became `S4_H4_UPFR48_LT0.4`.

#### Layered D1-return-gate + H4-return-state key cells

|   slow_lookback | slow_mode      |   slow_thr |   fast_lookback | fast_mode      |   fast_thr |   sharpe_daily |     cagr |   trade_count |
|----------------:|:---------------|-----------:|----------------:|:---------------|-----------:|---------------:|---------:|--------------:|
|              40 | fixed_zero     |     nan    |             168 | train_quantile |       0.5  |        1.9216  | 1.17359  |            51 |
|              40 | train_quantile |       0.5  |             168 | train_quantile |       0.5  |        1.8689  | 1.10915  |            49 |
|              40 | train_quantile |       0.65 |             202 | fixed_zero     |     nan    |        1.86756 | 0.984646 |            17 |
|              40 | train_quantile |       0.65 |             202 | train_quantile |       0.5  |        1.84057 | 0.963976 |            19 |
|              40 | train_quantile |       0.65 |             168 | fixed_zero     |     nan    |        1.80136 | 0.929823 |            29 |
|              40 | fixed_zero     |     nan    |             168 | train_quantile |       0.65 |        1.78533 | 0.889128 |            53 |
|              40 | fixed_zero     |     nan    |             168 | fixed_zero     |     nan    |        1.78391 | 1.04565  |            49 |
|              40 | train_quantile |       0.5  |             168 | train_quantile |       0.65 |        1.76192 | 0.867362 |            50 |
|              40 | train_quantile |       0.35 |             168 | train_quantile |       0.5  |        1.75881 | 1.03372  |            64 |
|              32 | train_quantile |       0.35 |             168 | train_quantile |       0.5  |        1.75443 | 1.04292  |            75 |

Interpretation:

- the best headline layered trend-plus-trend cell was near slow `40`, fast `168`
- the simplest representative of that family was `L2_D1RET40_Z0_AND_H4RET168_Z0`

#### Layered D1-vol-cluster-gate + H4-return-state key cells

| slow_pair   | slow_mode      |   slow_thr |   fast_lookback | fast_mode      |   fast_thr |   sharpe_daily |     cagr |   trade_count |
|:------------|:---------------|-----------:|----------------:|:---------------|-----------:|---------------:|---------:|--------------:|
| (6, 24)     | fixed_level    |       1    |             168 | train_quantile |       0.5  |        1.91738 | 0.945973 |           108 |
| (6, 24)     | train_quantile |       0.65 |             168 | train_quantile |       0.5  |        1.88469 | 0.928674 |           106 |
| (6, 24)     | fixed_level    |       1    |             168 | fixed_zero     |     nan    |        1.87177 | 0.941749 |           107 |
| (5, 20)     | train_quantile |       0.65 |             168 | fixed_zero     |     nan    |        1.86025 | 0.978235 |           115 |
| (5, 20)     | fixed_level    |       1    |             168 | fixed_zero     |     nan    |        1.85543 | 0.969024 |           113 |
| (5, 20)     | train_quantile |       0.65 |             168 | train_quantile |       0.5  |        1.8526  | 0.938974 |           120 |
| (5, 20)     | fixed_level    |       1    |             168 | train_quantile |       0.5  |        1.84786 | 0.929946 |           118 |
| (4, 16)     | train_quantile |       0.65 |             168 | train_quantile |       0.65 |        1.84385 | 0.710313 |            89 |
| (6, 24)     | fixed_level    |       1    |             202 | fixed_zero     |     nan    |        1.83096 | 0.921712 |            94 |
| (6, 24)     | train_quantile |       0.65 |             168 | fixed_zero     |     nan    |        1.81627 | 0.907057 |           105 |

Interpretation:

- the best volatility-gated layered cells clustered around slow pair `(5,20)` or `(6,24)` and fast lookback `168`
- the simplest representative of that family was `L1_VCL5_20_LT1.0_AND_H4RET168_Z0`

**Output:** one representative per serious family cluster.

**Decision rule:** choose the simplest serious representative lying inside a broad plateau, not the highest isolated cell.

## Stage 5 candidate-selection holdout and pre-reserve comparison

### Step 16 — Freeze a comparison set, not just a provisional winner

**Input:** surviving simple and layered representatives after discovery-only work.

**Logic:** before opening reserve/internal, keep the simplest viable representative from each surviving family cluster and the nearest serious internal rivals.

Frozen comparison set in the supplied run:

| candidate                        | cluster                       | type           | reason                                                                                                                                  |
|:---------------------------------|:------------------------------|:---------------|:----------------------------------------------------------------------------------------------------------------------------------------|
| S1_D1_RET40_Z0                   | simple_slow_trend             | single_native  | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| S2_D1_VCL5_20_LT1.0              | simple_slow_vol_regime        | single_native  | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| S3_H4_RET168_Z0                  | simple_fast_trend             | single_native  | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| S4_H4_UPFR48_LT0.4               | simple_fast_timing_sparse     | single_native  | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | layered_vol_gate_fast_trend   | layered_and_h4 | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | layered_slow_trend_fast_trend | layered_and_h4 | Frozen before reserve/internal readout as simplest viable representative of surviving family cluster or nearest serious internal rival. |

**Output:** `frozen_comparison_set_ledger.csv`.

**Decision rule:** the reserve/internal window must still be untouched at this point.

### Step 17 — Evaluate the frozen comparison set on the candidate-selection holdout

**Input:** frozen comparison set and the sealed holdout window `2023-01-01` to `2024-06-30`.

**Logic:** run each frozen candidate unchanged on the holdout under the same next-open execution and 20 bps cost model.

Key supplied-run metrics:

| candidate                        |   disc_sharpe_daily |   disc_cagr |   disc_trade_count |   hold_sharpe_daily |   hold_cagr |   hold_trade_count |   pre_res_sharpe |   pre_res_cagr |
|:---------------------------------|--------------------:|------------:|-------------------:|--------------------:|------------:|-------------------:|-----------------:|---------------:|
| S1_D1_RET40_Z0                   |             1.55674 |    0.907849 |                 29 |            1.94147  |   1.03037   |                 12 |          1.66343 |       0.947797 |
| S2_D1_VCL5_20_LT1.0              |             1.31154 |    0.782865 |                108 |            0.922704 |   0.297448  |                 43 |          1.19483 |       0.603854 |
| S3_H4_RET168_Z0                  |             1.63222 |    0.984197 |                 82 |            1.91476  |   1.00756   |                 52 |          1.7084  |       0.991947 |
| S4_H4_UPFR48_LT0.4               |             1.58595 |    0.277391 |                 62 |            0.780877 |   0.0519325 |                 31 |          1.36921 |       0.197419 |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 |             1.85543 |    0.969024 |                113 |            1.07427  |   0.302316  |                 60 |          1.63342 |       0.715849 |
| L2_D1RET40_Z0_AND_H4RET168_Z0    |             1.78391 |    1.04565  |                 49 |            1.82972  |   0.893368  |                 39 |          1.79292 |       0.993635 |

Load-bearing holdout facts:

- `S3_H4_RET168_Z0` holdout Sharpe `1.914757`, holdout CAGR `1.007564`, holdout trades `52`
- `S1_D1_RET40_Z0` holdout Sharpe `1.941472`, holdout CAGR `1.030375`, holdout trades `12`
- `L2_D1RET40_Z0_AND_H4RET168_Z0` remained a serious pre-reserve rival with pre-reserve Sharpe `1.792915` and pre-reserve CAGR `0.993635`
- all frozen-set candidates cleared the holdout-side minimum trade burden except no candidate fell below 10 holdout trades in the final comparison set

**Output:** holdout metrics inside `validation_summary.csv`.

**Decision rule:** any final leader must be positive after cost on holdout and must have at least 10 holdout trades unless it is intentionally sparse and justified elsewhere.

## Paired bootstrap, ablation, and final pre-reserve selection

### Step 18 — Run component ablation

**Input:** layered finalists and their simpler comparators.

**Logic:** compare each layered system against both its slow-only and fast-only comparators.

Ablation results from the supplied run:

| layered_candidate                | comparator          | comparison_type   |   delta_pre_res_sharpe |   delta_pre_res_cagr | verdict                                                                                                               |
|:---------------------------------|:--------------------|:------------------|-----------------------:|---------------------:|:----------------------------------------------------------------------------------------------------------------------|
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | S2_D1_VCL5_20_LT1.0 | ablate_fast_layer |              0.438587  |           0.111995   | Fast trend layer adds substantial edge to slow low-vol regime core.                                                   |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 | S3_H4_RET168_Z0     | ablate_slow_layer |             -0.0749813 |          -0.276098   | Slow low-vol gate does not improve enough over simple H4 trend frontier to justify leadership.                        |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | S1_D1_RET40_Z0      | ablate_fast_layer |              0.0845148 |           0.0458378  | Fast layer improves headline metrics over slow trend alone.                                                           |
| L2_D1RET40_Z0_AND_H4RET168_Z0    | S3_H4_RET168_Z0     | ablate_slow_layer |              0.0845148 |           0.00168868 | Slow trend gate does not earn enough incremental advantage over simple H4 trend frontier to justify extra complexity. |

Interpretation:

- `L1` gained edge over the slow low-volatility gate alone, so the fast H4 trend layer mattered
- `L2` gained edge over the slow D1 trend gate alone, so the fast H4 trend layer mattered
- neither slow gate earned enough incremental value over the already-strong simple H4 trend frontier `S3`

**Output:** `ablation_table.csv`.

**Decision rule:** every retained layer must earn its place by ablation. A slow gate that does not materially improve over the simple fast frontier cannot claim leadership.

### Step 19 — Run moving-block paired bootstrap on daily return paths

**Input:** daily return paths of the frozen comparison-set candidates.

**Logic:** use moving-block bootstrap on paired daily return paths with:

- block sizes: 5, 10, and 20 calendar days
- resamples per block size: 2,000
- paired resampling: yes
- statistics on each bootstrap path:
  - difference in mean daily return
  - difference in daily-return Sharpe
  - difference in CAGR

Operational null for a more complex-vs-simpler test: the more complex candidate does **not** have a materially positive advantage over the simpler candidate. The exported tables report one-sided probabilities `P(diff > 0)` and 5th/95th percentile intervals. The run treated a more-complex system as having a meaningful paired advantage only if the lower 5% bound stayed above zero across the tested block sizes. That is equivalent to a one-sided 5% significance bar.

**Output:** paired-bootstrap tables.

**Decision rule:** if a more complex candidate does not show a meaningful paired advantage over a simpler nearby rival, the simpler rival wins.

### Step 20 — Eliminate `L2_D1RET40_Z0_AND_H4RET168_Z0`

**Input:** `L2` vs `S3` paired bootstrap, pre-reserve metrics, and complexity budget.

**Logic:** compare the more complex two-layer trend-plus-trend system `L2` against the simpler one-layer H4 trend frontier `S3`.

Exact paired-bootstrap results from the supplied run:

|   block_size |   n_boot |   p_sharpe_gt0 |   p_cagr_gt0 |   mean_diff_sharpe |   ci05_diff_sharpe |   ci95_diff_sharpe |   mean_diff_cagr |   ci05_diff_cagr |   ci95_diff_cagr |
|-------------:|---------:|---------------:|-------------:|-------------------:|-------------------:|-------------------:|-----------------:|-----------------:|-----------------:|
|            5 |     2000 |         0.6575 |       0.501  |          0.0755945 |          -0.206952 |           0.341076 |       -0.0121534 |        -0.305298 |         0.23978  |
|           10 |     2000 |         0.6915 |       0.5065 |          0.0778719 |          -0.205811 |           0.365473 |       -0.0131992 |        -0.327355 |         0.246319 |
|           20 |     2000 |         0.6545 |       0.4695 |          0.065632  |          -0.20759  |           0.33884  |       -0.0252022 |        -0.322608 |         0.219805 |

Exact pre-reserve comparison judgment:

| comparison                                       |   delta_pre_res_sharpe |   delta_pre_res_cagr | paired_p_sharpe_gt0_range   | paired_p_cagr_gt0_range   | verdict                                                                                     |
|:-------------------------------------------------|-----------------------:|---------------------:|:----------------------------|:--------------------------|:--------------------------------------------------------------------------------------------|
| L2_D1RET40_Z0_AND_H4RET168_Z0 vs S3_H4_RET168_Z0 |              0.0845148 |           0.00168868 | 0.654-0.692                 | 0.469-0.506               | No meaningful paired advantage for more complex L2; protocol awards decision to simpler S3. |

Why `L2` was eliminated:

- `L2` had slightly better headline pre-reserve Sharpe by `+0.084515`
- `L2` had essentially tied pre-reserve CAGR advantage by only `+0.001689`
- bootstrap support was weak:
  - `p_sharpe_gt0` only `0.6545` to `0.6915`
  - `p_cagr_gt0` only `0.4695` to `0.5065`
  - the 5th percentile of Sharpe and CAGR differences remained negative at every block size
- under the V6 rule, extra complexity must prove a meaningful paired advantage over the simpler frontier; `L2` did not

**Output:** `L2` removed as final leader, but kept in the frozen comparison set for reserve/internal reporting.

**Decision rule:** the simpler candidate `S3` wins this head-to-head.

### Step 21 — Eliminate `L1_VCL5_20_LT1.0_AND_H4RET168_Z0` as leader

**Input:** `L1` vs `S3` paired bootstrap and pre-reserve metrics.

**Logic:** compare the volatility-gated layered candidate against the simpler H4 trend frontier.

Exact paired-bootstrap results from the supplied run:

|   block_size |   n_boot |   p_sharpe_gt0 |   p_cagr_gt0 |   mean_diff_sharpe |   ci05_diff_sharpe |   ci95_diff_sharpe |   mean_diff_cagr |   ci05_diff_cagr |   ci95_diff_cagr |
|-------------:|---------:|---------------:|-------------:|-------------------:|-------------------:|-------------------:|-----------------:|-----------------:|-----------------:|
|            5 |     2000 |         0.3935 |       0.126  |         -0.0810224 |          -0.586694 |           0.42802  |        -0.30863  |        -0.806184 |         0.122824 |
|           10 |     2000 |         0.4105 |       0.1435 |         -0.0723635 |          -0.596932 |           0.46042  |        -0.302566 |        -0.879262 |         0.152667 |
|           20 |     2000 |         0.429  |       0.1745 |         -0.0549799 |          -0.573979 |           0.468966 |        -0.294315 |        -0.862566 |         0.16517  |

Exact pre-reserve comparison judgment:

| comparison                                          |   delta_pre_res_sharpe |   delta_pre_res_cagr | paired_p_sharpe_gt0_range   | paired_p_cagr_gt0_range   | verdict                                                                       |
|:----------------------------------------------------|-----------------------:|---------------------:|:----------------------------|:--------------------------|:------------------------------------------------------------------------------|
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 vs S3_H4_RET168_Z0 |             -0.0749813 |            -0.276098 | 0.394-0.429                 | 0.126-0.174               | Inferior to S3 on paired bootstrap and pre-reserve growth; dropped as leader. |

Why `L1` was eliminated:

- pre-reserve Sharpe delta versus `S3`: `-0.074981`
- pre-reserve CAGR delta versus `S3`: `-0.276098`
- paired bootstrap favored `S3`, not `L1`

**Output:** `L1` removed as leader.

**Decision rule:** inferior to `S3` on both paired evidence and pre-reserve growth.

### Step 22 — Resolve `S3_H4_RET168_Z0` versus `S1_D1_RET40_Z0`

**Input:** `S3` vs `S1` paired bootstrap, plateau breadth, drawdown, trade count, and pre-reserve metrics.

**Logic:** compare the strongest simple fast frontier against the strongest simple slow frontier.

Exact paired-bootstrap results from the supplied run:

|   block_size |   n_boot |   p_sharpe_gt0 |   p_cagr_gt0 |   mean_diff_sharpe |   ci05_diff_sharpe |   ci95_diff_sharpe |   mean_diff_cagr |   ci05_diff_cagr |   ci95_diff_cagr |
|-------------:|---------:|---------------:|-------------:|-------------------:|-------------------:|-------------------:|-----------------:|-----------------:|-----------------:|
|            5 |     2000 |         0.572  |       0.576  |          0.0462052 |          -0.318195 |           0.418481 |        0.0462766 |        -0.302678 |         0.405115 |
|           10 |     2000 |         0.585  |       0.596  |          0.0538982 |          -0.316457 |           0.430983 |        0.0565172 |        -0.278984 |         0.431712 |
|           20 |     2000 |         0.5715 |       0.5875 |          0.0475409 |          -0.318665 |           0.419642 |        0.0522919 |        -0.285987 |         0.403407 |

Exact pre-reserve comparison judgment:

| comparison                        |   delta_pre_res_sharpe |   delta_pre_res_cagr | paired_p_sharpe_gt0_range   | paired_p_cagr_gt0_range   | verdict                                                                                                                                                          |
|:----------------------------------|-----------------------:|---------------------:|:----------------------------|:--------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| S3_H4_RET168_Z0 vs S1_D1_RET40_Z0 |              0.0449747 |            0.0441491 | 0.572-0.585                 | 0.576-0.596               | Not cleanly separated by paired bootstrap; S3 selected on slightly stronger pre-reserve Sharpe/CAGR, lower drawdown, broader H4 plateau, and higher trade count. |

Why `S3` was selected over `S1` before reserve/internal:

- paired bootstrap did **not** cleanly separate them
- `S3` had slightly better pre-reserve Sharpe and CAGR
- `S3` had lower pre-reserve max drawdown
- `S3` had a broader native H4 plateau
- `S3` produced materially more trades, giving a heavier evidence base inside discovery + holdout

**Output:** final pre-reserve leader `S3_H4_RET168_Z0`.

**Decision rule:** when two simple candidates are not cleanly separated by paired bootstrap, select the one with the stronger combined robustness profile across pre-reserve metrics, plateau breadth, drawdown, and trade burden.

## Stage 6 freeze

### Step 23 — Freeze the exact winner and exact comparison set before reserve/internal

**Input:** all pre-reserve evidence only.

**Logic:** record the exact:

- features and transforms
- lookbacks
- threshold rules
- state machine
- position sizing
- evaluation code path
- frozen comparison set

The frozen winner before reserve/internal was:

- `S3_H4_RET168_Z0`
- native H4
- feature `ret`
- lookback `168`
- threshold mode `fixed_zero`
- threshold `0.0`
- long if feature `> 0`, otherwise flat
- next-open execution
- 100% long or 0% cash

**Output:** `frozen_system.json`, `frozen_system_specification.md`, and `frozen_comparison_set_ledger.csv`.

**Decision rule:** after freeze, no redesign, retuning, or reserve-based tie-breaking is allowed.

## Stage 7 reserve/internal evaluation

### Step 24 — Evaluate the frozen winner and frozen comparison set exactly once on reserve/internal

**Input:** exact frozen comparison set and sealed reserve/internal window.

**Logic:** run each frozen candidate unchanged on `2024-07-01` to dataset end, report reserve/internal separately from discovery and holdout, and do **not** relabel it as clean OOS.

Exact reserve/internal results from the supplied run:

| candidate                        |   res_days |   res_sharpe_daily |   res_cagr |   res_cagr_pct |   res_max_drawdown |   res_trade_count |   res_exposure |   res_net_return |
|:---------------------------------|-----------:|-------------------:|-----------:|---------------:|-------------------:|------------------:|---------------:|-----------------:|
| S1_D1_RET40_Z0                   |        624 |          0.525713  |  0.118734  |       11.8734  |          -0.240051 |                25 |       0.514423 |        0.211284  |
| S2_D1_VCL5_20_LT1.0              |        624 |          0.91281   |  0.272303  |       27.2303  |          -0.211357 |                58 |       0.596154 |        0.508983  |
| S3_H4_RET168_Z0                  |        625 |         -0.0419216 | -0.0575438 |       -5.75438 |          -0.346367 |                76 |       0.519477 |       -0.0964403 |
| S4_H4_UPFR48_LT0.4               |        625 |          0.389713  |  0.0494232 |        4.94232 |          -0.168957 |                35 |       0.046158 |        0.0860502 |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 |        625 |         -0.156174  | -0.0627535 |       -6.27535 |          -0.220798 |                82 |       0.324973 |       -0.10497   |
| L2_D1RET40_Z0_AND_H4RET168_Z0    |        625 |          0.0425135 | -0.0255544 |       -2.55544 |          -0.290908 |                57 |       0.409018 |       -0.0433293 |

Important supplied-run facts:

- frozen winner `S3_H4_RET168_Z0`: reserve CAGR `-0.057544` = `-5.7544%`, reserve Sharpe `-0.041922`, reserve trades `76`
- `S1_D1_RET40_Z0`: reserve CAGR `0.118734` = `11.8734%`
- `S2_D1_VCL5_20_LT1.0`: reserve CAGR `0.272303` = `27.2303%`
- `L2_D1RET40_Z0_AND_H4RET168_Z0`: reserve CAGR `-0.025554`
- `L1_VCL5_20_LT1.0_AND_H4RET168_Z0`: reserve CAGR `-0.062753`

Regime decomposition for the frozen winner:

- pre-reserve:
  - bear: noise-only
  - bull: effective
  - neutral: noise-only
- full internal after reserve:
  - bear: sign-reversed
  - bull: effective
  - neutral: noise-only

Exact frozen-winner regime tables from the supplied run:

Pre-reserve:
| regime   |   days |   active_days |   exposure_mean |   ret_sharpe |   ret_cagr | signal_label   |
|:---------|-------:|--------------:|----------------:|-------------:|-----------:|:---------------|
| bear     |    481 |           153 |        0.265419 |    -0.837877 | -0.0927044 | noise-only     |
| bull     |    829 |           712 |        0.808203 |     2.64537  |  1.02565   | effective      |
| neutral  |    333 |           141 |        0.382883 |     1.34942  |  0.079714  | noise-only     |

Full internal:
| regime   |   days |   active_days |   exposure_mean |   ret_sharpe |   ret_cagr | signal_label   |
|:---------|-------:|--------------:|----------------:|-------------:|-----------:|:---------------|
| bear     |    689 |           221 |        0.259797 |    -1.38728  |  -0.113925 | sign-reversed  |
| bull     |   1100 |           937 |        0.799848 |     2.53346  |   0.899624 | effective      |
| neutral  |    478 |           215 |        0.397838 |     0.323891 |   0.011611 | noise-only     |

**Output:** reserve/internal evaluation, regime decomposition, and updated evidence label.

**Decision rule:** report reserve/internal honestly, but do not redesign.

### Why V6 forbids redesign after reserve/internal

The no-redesign rule is explicit in the protocol:

- Stage 6 freeze locked the exact system and exact comparison set before touching reserve/internal
- Stage 7 allowed exactly one reserve/internal evaluation
- the protocol explicitly forbids redesign, retuning, or reserve-based tie-breaking after reserve/internal is seen

Therefore the reserve/internal weakness of `S3_H4_RET168_Z0` lowers confidence but does **not** retroactively permit a new winner selection from the same file.

## Hard acceptance checklist for the frozen winner

The supplied run recorded the following hard-criteria checklist for `S3_H4_RET168_Z0`:

| criterion                                                    | passed   | evidence                                                                                                        |
|:-------------------------------------------------------------|:---------|:----------------------------------------------------------------------------------------------------------------|
| positive_edge_after_20bps_on_aggregate_discovery_walkforward | True     | disc_cagr=0.984197, disc_net_return=6.815529                                                                    |
| positive_performance_after_cost_on_holdout                   | True     | hold_cagr=1.007564, hold_net_return=1.839743                                                                    |
| at_least_20_discovery_trades                                 | True     | disc_trade_count=82                                                                                             |
| at_least_10_holdout_trades                                   | True     | hold_trade_count=52                                                                                             |
| no_clear_collapse_across_major_regimes_pre_reserve           | True     | bear:noise-only; bull:effective; neutral:noise-only                                                             |
| broad_plateau_around_selected_cell                           | True     | Neighboring H4 return lookbacks 134/168/202 with fixed_zero and q0.50 remain strong; no sharp isolated optimum. |
| no_pre_freeze_contamination                                  | True     | Only prompt and raw CSVs were consulted before freeze.                                                          |

This is why the final evidence label remained `INTERNAL ROBUST CANDIDATE` rather than `NO ROBUST IMPROVEMENT`, even though reserve/internal weakened confidence materially.

## Cost-stress summary for the frozen comparison set

The supplied run repeated discovery and holdout evaluation under a 50 bps round-trip stress test.

| candidate                        |   disc_cagr |   hold_cagr |   disc_cagr_50bps |   disc_sharpe_50bps |   hold_cagr_50bps |   hold_sharpe_50bps |   disc_delta_50bps |   hold_delta_50bps |
|:---------------------------------|------------:|------------:|------------------:|--------------------:|------------------:|--------------------:|-------------------:|-------------------:|
| S1_D1_RET40_Z0                   |    0.907849 |   1.03037   |          0.854317 |             1.49875 |         0.982258  |            1.88256  |         -0.0535323 |         -0.0481168 |
| S2_D1_VCL5_20_LT1.0              |    0.782865 |   0.297448  |          0.601155 |             1.11887 |         0.190203  |            0.673638 |         -0.18171   |         -0.107245  |
| S3_H4_RET168_Z0                  |    0.984197 |   1.00756   |          0.827791 |             1.46228 |         0.80865   |            1.64959  |         -0.156406  |         -0.198914  |
| S4_H4_UPFR48_LT0.4               |    0.277391 |   0.0519325 |          0.200636 |             1.23844 |        -0.0114513 |           -0.139721 |         -0.0767556 |         -0.0633838 |
| L1_VCL5_20_LT1.0_AND_H4RET168_Z0 |    0.969024 |   0.302316  |          0.758386 |             1.57665 |         0.154479  |            0.644794 |         -0.210639  |         -0.147837  |
| L2_D1RET40_Z0_AND_H4RET168_Z0    |    1.04565  |   0.893368  |          0.947645 |             1.67378 |         0.750872  |            1.62171  |         -0.0980017 |         -0.142496  |

Load-bearing cost-stress fact for the winner:

- `S3_H4_RET168_Z0` discovery CAGR fell from `0.984197` to `0.827791`
- `S3_H4_RET168_Z0` holdout CAGR fell from `1.007564` to `0.808650`

The candidate remained positive under stress on discovery and holdout, which supported the pre-reserve robustness case.

## Provenance, software, and deterministic rebuild notes

### Provenance declaration from the supplied run

Before freeze, the supplied run consulted only:

- `RESEARCH_PROMPT_V6.md`
- `data_btcusdt_1d.csv`
- `data_btcusdt_4h.csv`

After freeze, the supplied run consulted its own generated reserve/internal and validation artifacts. No benchmark specification was supplied after reserve, so no benchmark comparison occurred.

### Software versions present in the supplied execution environment

| component   | version   |
|:------------|:----------|
| Python      | 3.13.5    |
| pandas      | 2.2.3     |
| numpy       | 2.3.5     |
| scipy       | 1.17.0    |
| matplotlib  | 3.10.8    |

### Randomness and bootstrap reproducibility

All data processing, feature generation, execution, trade generation, and non-bootstrap metrics are deterministic given the raw CSVs and the rules in this document.

The original artifact bundle does **not** expose the RNG seed used for the bootstrap resamples. That means:

- every deterministic table and the final frozen winner are reproducible exactly
- paired-bootstrap and bootstrap confidence tables are reproducible methodologically, but exact Monte Carlo p-values are not guaranteed to be bit-identical unless the original hidden seed is known

For a fresh deterministic rebuild, set a fixed NumPy generator seed and preserve the versions above. That will produce stable bootstrap tables and the same final qualitative decisions, but not necessarily the exact historical bootstrap row values from the original run.

## Final reconstruction summary

An implementation that follows this document exactly will reproduce the V6 research path:

1. keep the raw bars intact, including the 19 shortened H4 bars, 8 H4 timing gaps, and the 1 duplicate zero-duration H4 row
2. split the data exactly on `open_dt` into context, discovery, holdout, and reserve/internal
3. compute the full Stage 1 feature library from raw H4 and D1 without synthetic bars
4. evaluate all Stage 1 executable states on discovery walk-forward under 20 bps round-trip cost
5. filter serious candidates by positive discovery edge after cost and at least 20 discovery trades
6. shortlist orthogonal family representatives and nearest rivals
7. build minimal layered alternatives and reject unsupported third layers
8. select family representatives from broad plateau centers rather than single-cell spikes
9. compare finalists on holdout, paired bootstrap, ablation, cost resilience, trade burden, and simplicity
10. freeze `S3_H4_RET168_Z0` and the frozen comparison set before reserve/internal
11. report reserve/internal honestly without redesign

The pre-reserve winner is `S3_H4_RET168_Z0`. The reserve/internal readout weakens confidence materially but, under V6, does not permit retuning or replacement inside the same file.
