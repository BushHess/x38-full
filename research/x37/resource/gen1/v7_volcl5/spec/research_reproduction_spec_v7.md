# Spec 1 — Research Reproduction Spec (Full research process)

## 1. Scope and intended result

This specification rebuilds the entire V7 same-file convergence audit from raw BTC/USDT spot data and nothing else. The target output is the frozen leader `S_D1_VOLCL5_20_LOW_F1`, evidence label `INTERNAL ROBUST CANDIDATE`, with the same comparison set, the same keep/drop ledger, the same reserve/internal contradiction handling, and the same no-redesign-after-freeze discipline.

The admissible quantitative inputs are exactly three files:

1. `RESEARCH_PROMPT_V7.md`
2. raw native H4 CSV
3. raw native D1 CSV

No earlier reports, serialized outputs, frozen JSON files, prior shortlist tables, benchmark specifications, or prior session artifacts are admissible before freeze. The clean-provenance declaration for the original run was:

- clean independent re-derivation before freeze: **True**
- admissible artifacts consulted before freeze: `RESEARCH_PROMPT_V7.md`, `data_btcusdt_4h.csv`, `data_btcusdt_1d.csv`
- disallowed prior artifacts consulted before freeze: **none**
- benchmark specifications consulted: **none supplied; none consulted**
- all candidate-selection tables and metrics were generated inside the session from raw data

## 2. Required raw input files and exact schema

Use two CSV files. Identify them by the `interval` column if filenames differ.

### 2.1 Native H4 CSV

- one row per native 4-hour bar
- expected `interval` value on all rows: `4h`
- raw row count observed in the audited file: **18,791**
- UTC coverage observed in the audited file: `2017-08-17 04:00:00+00:00` through `2026-03-17 15:59:59.999+00:00`

### 2.2 Native D1 CSV

- one row per native 1-day bar
- expected `interval` value on all rows: `1d`
- raw row count observed in the audited file: **3,134**
- UTC coverage observed in the audited file: `2017-08-17 00:00:00+00:00` through `2026-03-16 23:59:59.999+00:00`

### 2.3 Exact column schema for both files

Parse the same 13 columns, in the exact raw market-data surface locked by the prompt:

| column | type | meaning |
|---|---|---|
| `symbol` | string | market identifier; expected `BTCUSDT` |
| `interval` | string | `4h` or `1d` |
| `open_time` | int64 epoch milliseconds UTC | bar open timestamp |
| `close_time` | int64 epoch milliseconds UTC | bar close timestamp |
| `open` | float64 | open price |
| `high` | float64 | high price |
| `low` | float64 | low price |
| `close` | float64 | close price |
| `volume` | float64 | base-asset traded volume |
| `quote_volume` | float64 | quote-asset traded volume |
| `num_trades` | int64 | count of trades in the bar |
| `taker_buy_base_vol` | float64 | taker-buy base volume |
| `taker_buy_quote_vol` | float64 | taker-buy quote volume |

No extra columns may be used to expand the feature surface. If extra columns appear, log them and do not silently use them. In the audited files, no extra columns were present.

## 3. Deterministic data pipeline

Run the pipeline in this exact order and do not reorder it:

1. **Parse UTC**  
   Convert `open_time` and `close_time` from Unix epoch milliseconds to timezone-aware UTC timestamps.

2. **Sort**  
   Sort each timeframe independently in ascending chronological order using `open_time` as the primary key and `close_time` as the secondary key.

3. **Check**  
   Audit each timeframe for:
   - duplicate full rows
   - duplicate `open_time`
   - duplicate `close_time`
   - missing values
   - nonstandard bar durations
   - irregular gaps
   - zero-activity rows
   - impossible OHLC rows
   - `close_time < open_time`
   - `taker_buy_base_vol > volume`
   - `taker_buy_quote_vol > quote_volume`

4. **Reconcile native D1 against day-aggregated native H4**  
   On overlapping complete UTC days with exactly six H4 bars, aggregate the H4 file with:
   - `open` = first open of the day
   - `high` = max high of the day
   - `low` = min low of the day
   - `close` = last close of the day
   - `volume`, `quote_volume`, `num_trades`, `taker_buy_base_vol`, `taker_buy_quote_vol` = daily sums  
   Then compare against the native D1 row for the same UTC day. In the audited run, complete overlapping days matched exactly for OHLC and within floating-point tolerance for summed volume-like fields.

5. **Log**  
   Write:
   - a written audit report,
   - a machine-readable audit summary table,
   - a machine-readable anomaly-disposition register,
   - a machine-readable reconciliation result.

No synthetic repair is permitted. No anomalous row may be silently fixed or silently dropped.

## 4. Exact anomaly handling and dispositions

All anomaly classes were retained exactly as supplied unless the prompt explicitly demanded otherwise. This table is the authoritative disposition register:

| anomaly_class                             | deterministic_rule           | rule_details                                                                                                                                                                                                            | impact_on_scoring             |
|:------------------------------------------|:-----------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:------------------------------|
| extra_columns                             | retained_not_used            | No extra columns present in either raw file. Feature surface locked to prompt schema only.                                                                                                                              | none                          |
| missing_values                            | retained_exactly_as_supplied | No missing values detected.                                                                                                                                                                                             | none                          |
| duplicate_rows                            | retained_exactly_as_supplied | No fully duplicated rows detected.                                                                                                                                                                                      | none                          |
| duplicate_open_time                       | retained_exactly_as_supplied | No duplicate open_time rows detected.                                                                                                                                                                                   | none                          |
| duplicate_close_time_4h                   | retained_exactly_as_supplied | One duplicated H4 close_time pair on 2017-09-06; both rows retained because no duplicate open_time and no synthetic repair allowed. This affects warmup only.                                                           | warmup_only_context           |
| nonstandard_bar_length_4h                 | retained_exactly_as_supplied | 19 H4 rows have close_time not exactly 4 hours after open_time; rows retained and supplied close_time governs slower-feature visibility. No bar repair or synthetic normalization performed.                            | included_in_scoring_and_audit |
| irregular_open_time_gaps_4h               | retained_exactly_as_supplied | 8 H4 rows precede gaps >4h. Missing bars are not invented. Execution uses actual next available open as supplied.                                                                                                       | included_in_scoring_and_audit |
| zero_activity_row_4h                      | retained_exactly_as_supplied | One H4 zero-activity row at 2017-09-06 16:00 UTC retained; it lies in warmup only and is logged.                                                                                                                        | warmup_only_context           |
| impossible_ohlc                           | retained_exactly_as_supplied | No impossible OHLC rows detected.                                                                                                                                                                                       | none                          |
| native_d1_vs_aggregated_h4_reconciliation | complete_days_match          | On overlapping complete UTC days with six H4 bars, native D1 and aggregated native H4 match exactly within floating-point tolerance for OHLCV and trade fields. Incomplete H4 days are logged separately, not repaired. | reconciliation_pass           |

Two practical implications are critical:

- When an H4 row has nonstandard duration, the supplied `close_time` governs when that row becomes visible for any slower-feature or transported-feature alignment.
- When an H4 gap exists, the missing bars are not invented. Any execution that would have occurred during the gap is realized at the next available actual open that exists in the raw file.

The audited summary table for both raw files is:

| timeframe   |   rows | start_open_time_utc       | end_close_time_utc               |   duplicate_rows |   duplicate_open_time |   duplicate_close_time |   missing_values |   nonstandard_duration_rows |   pre_gap_rows |   zero_activity_rows |   impossible_ohlc_rows |
|:------------|-------:|:--------------------------|:---------------------------------|-----------------:|----------------------:|-----------------------:|-----------------:|----------------------------:|---------------:|---------------------:|-----------------------:|
| 4h          |  18791 | 2017-08-17 04:00:00+00:00 | 2026-03-17 15:59:59.999000+00:00 |                0 |                     0 |                      1 |                0 |                          19 |              8 |                    1 |                      0 |
| 1d          |   3134 | 2017-08-17 00:00:00+00:00 | 2026-03-16 23:59:59.999000+00:00 |                0 |                     0 |                      0 |                0 |                           0 |              0 |                    0 |                      0 |

## 5. Data split architecture and temporal seals

Use strict chronological partitions with no overlap and no re-ordering:

- **Context / warmup only:** `2017-08-17` through `2019-12-31`
- **Discovery:** `2020-01-01` through `2023-06-30`
- **Candidate-selection holdout:** `2023-07-01` through `2024-09-30`
- **Reserve/internal:** `2024-10-01` through `2026-03-17` dataset end

Three temporal seals are mandatory:

1. The discovery window is the only zone allowed for feature measurement, family promotion, coarse search, local refinement, and comparison-set freeze.
2. The holdout must remain sealed until the comparison set is frozen from discovery-only evidence.
3. The reserve/internal window must remain sealed until the exact frozen leader and the exact frozen comparison set are recorded.

No redesign, retuning, extra candidate addition, or tie-break redesign is permitted after reserve/internal is opened.

## 6. Walk-forward structure across the full internal horizon

### 6.1 Discovery folds

Use the 14 quarterly, non-overlapping unseen folds required by V7:

- 2020-Q1: test `2020-01-01` to `2020-03-31`, train/calibrate `< 2020-01-01`
- 2020-Q2: test `2020-04-01` to `2020-06-30`, train/calibrate `< 2020-04-01`
- 2020-Q3: test `2020-07-01` to `2020-09-30`, train/calibrate `< 2020-07-01`
- 2020-Q4: test `2020-10-01` to `2020-12-31`, train/calibrate `< 2020-10-01`
- 2021-Q1: test `2021-01-01` to `2021-03-31`, train/calibrate `< 2021-01-01`
- 2021-Q2: test `2021-04-01` to `2021-06-30`, train/calibrate `< 2021-04-01`
- 2021-Q3: test `2021-07-01` to `2021-09-30`, train/calibrate `< 2021-07-01`
- 2021-Q4: test `2021-10-01` to `2021-12-31`, train/calibrate `< 2021-10-01`
- 2022-Q1: test `2022-01-01` to `2022-03-31`, train/calibrate `< 2022-01-01`
- 2022-Q2: test `2022-04-01` to `2022-06-30`, train/calibrate `< 2022-04-01`
- 2022-Q3: test `2022-07-01` to `2022-09-30`, train/calibrate `< 2022-07-01`
- 2022-Q4: test `2022-10-01` to `2022-12-31`, train/calibrate `< 2022-10-01`
- 2023-Q1: test `2023-01-01` to `2023-03-31`, train/calibrate `< 2023-01-01`
- 2023-Q2: test `2023-04-01` to `2023-06-30`, train/calibrate `< 2023-04-01`

### 6.2 Holdout and reserve evaluation folds

Use the same quarterly expansion rule after discovery, because frozen train-quantile candidates still require strictly pre-fold calibration even after the comparison set is frozen.

- Holdout folds: 2023-Q3, 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3
- Reserve/internal folds: 2024-Q4, 2025-Q1, 2025-Q2, 2025-Q3, 2025-Q4, 2026-Q1 partial

For any candidate whose threshold mode is `train_quantile`, compute that threshold separately for every quarter using all non-null feature values strictly before the quarter start. For `fixed_one`, `zero`, `absolute`, and `category` modes, no recalibration occurs because the rule itself is fixed.

Segment-level discovery, holdout, pre-reserve, reserve, and full-internal metrics are produced by stitching together the realized bar-level returns from the quarter-level evaluation path that belongs to that segment.

## 7. Generic execution engine used for every candidate

### 7.1 Bar-level signal timing and execution

For any timeframe `τ` (native D1 or native H4):

- compute the feature on completed bar `t`
- convert the feature to a binary long/flat signal on completed bar `t`
- apply the signal at the next bar open `t+1`
- realize return over the open-to-open interval `[open_(t+1), open_(t+2))`

There are no intrabar fills and no close-to-close proxy returns.

### 7.2 Realized bar return formula

For each scored bar `j`:

- `position_j ∈ {0,1}`
- `gross_return_j = open_(j+1) / open_j - 1`
- `turnover_cost_j = 0.001 * 1[position_j != position_(j-1)]`
- `realized_return_j = position_j * gross_return_j - turnover_cost_j`

This applies 10 bps per side. A round trip costs 20 bps.

Bars with missing `open_(j+1)` are not scoreable and must be excluded from realized-return scoring. This excludes the terminal D1 bar `2026-03-16` and the terminal H4 bar `2026-03-17 12:00 UTC` from realized-return scoring.

### 7.3 Daily aggregation for H4 candidates

Sharpe, bootstrap, and all candidate-to-candidate paired comparisons are computed on daily UTC returns. For H4 strategies:

- aggregate all scored H4 bar returns with the same UTC calendar date,
- `daily_return_d = Π(1 + realized_return_j over all scored H4 bars opened on UTC day d) - 1`

For D1 strategies, one scored bar already equals one UTC daily return.

### 7.4 Segment-local trade metrics

For trade-count and trade-quality diagnostics inside a segment, clip the position path to the segment and count each contiguous run of `position=1` inside the clipped segment as one trade. This means a carry-in long run at the segment start counts as one trade in that segment. This convention matches the saved validation tables, including the holdout trade count of 32 for the final winner even though only 31 new entries occurred during holdout.

### 7.5 Daily Sharpe and CAGR

- daily Sharpe = `sqrt(365.25) * mean(daily_returns) / sample_std(daily_returns, ddof=1)`
- CAGR = `(ending_equity)^(365.25 / scored_days) - 1`
- max drawdown = minimum of `equity / rolling_equity_peak - 1`

## 8. Feature engineering library

### 8.1 Common primitive definitions

Use the following primitives everywhere they are needed:

- `simple_return_1_t = close_t / close_(t-1) - 1`
- `log_return_1_t = ln(close_t / close_(t-1))`
- `rolling_high_n_t = max(high over last n bars ending at t)`
- `rolling_low_n_t = min(low over last n bars ending at t)`
- `TR_t = max(high_t - low_t, |high_t - close_(t-1)|, |low_t - close_(t-1)|)`
- `ATR_n_t = simple rolling mean of TR over the last n bars ending at t`
- `std_n(x)_t = sample standard deviation with `ddof=1` over the last n values ending at t`
- `mean_n(x)_t = simple rolling mean over the last n values ending at t`

When a formula divides by `high-low` and `high==low`, set the single-bar derived value to `NaN` and keep the raw row. In the audited data this only occurred once in H4 warmup and therefore had warmup-only impact.

### 8.2 Native D1 library

| family                   | features                    | formula                                                                                          | lookbacks_or_categories    | threshold_modes_and_grid                                                                 | tails     |
|:-------------------------|:----------------------------|:-------------------------------------------------------------------------------------------------|:---------------------------|:-----------------------------------------------------------------------------------------|:----------|
| directional_persistence  | posfrac_5/10/20/40          | fraction of positive close-to-close returns in last n bars                                       | n ∈ {5,10,20,40}           | absolute {0.25,0.35,0.45,0.55,0.65,0.75}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| directional_continuation | ret_5/10/20/40/80           | n-bar close return close_t/close_{t-n} - 1                                                       | n ∈ {5,10,20,40,80}        | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| trend_quality            | retvol_5/10/20/40/80        | n-bar compounded close return divided by rolling sample std of 1-bar close returns times sqrt(n) | n ∈ {5,10,20,40,80}        | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| range_location           | rangepct_10/20/40/80        | (close - rolling_low_n)/(rolling_high_n - rolling_low_n)                                         | n ∈ {10,20,40,80}          | absolute {0.20,0.30,0.40,0.60,0.70,0.80}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| drawdown_pullback        | drawdown_20/40/80           | close/rolling_high_n - 1                                                                         | n ∈ {20,40,80}             | train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                                           | high, low |
| volatility_level         | atrpct_10/20/40             | ATR_n / close, ATR_n = simple rolling mean of true range                                         | n ∈ {10,20,40}             | train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                                           | high, low |
| volatility_clustering    | volcluster_5_20/10_40/20_80 | sample std of log returns over short window divided by sample std over long window               | (5,20), (10,40), (20,80)   | fixed_one 1.0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                            | high, low |
| participation_volume     | volratio_5/10/20            | quote_volume / rolling_mean_quote_volume_n                                                       | n ∈ {5,10,20}              | fixed_one 1.0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                            | high, low |
| participation_flow       | takeratio_1/5/10            | rolling mean_n of taker_buy_base_vol / volume                                                    | n ∈ {1,5,10}               | absolute {0.40,0.45,0.48,0.52,0.55,0.60}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| candle_body              | bodyfrac_1/3                | rolling mean_n of (close-open)/(high-low)                                                        | n ∈ {1,3}                  | zero 0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                                   | high, low |
| candle_location          | closeloc_1/3                | rolling mean_n of (close-low)/(high-low)                                                         | n ∈ {1,3}                  | absolute {0.20,0.30,0.40,0.60,0.70,0.80}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| calendar_dow             | calendar_dow                | day-of-week category from bar open_time UTC, Monday=0 … Sunday=6                                 | categories {0,1,2,3,4,5,6} | category exact match                                                                     | category  |

The Native D1 scan enumerates **343** executable long/flat state systems. The exact bucket-level count and pass totals were:

| bucket    |   configs_scanned |   configs_pass_gate | how_count_is_reached                                                                                                                                                                                          |
|:----------|------------------:|--------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Native D1 |               343 |                 178 | 4 persistence + 5 continuation + 5 trend-quality + 4 range-location + 3 drawdown + 3 ATR + 3 volcluster + 3 volratio + 3 takeratio + 4 candle + 1 calendar family grids enumerated exactly as specified below |

### 8.3 Native H4 library

| family                   | features                   | formula                                                                                          | lookbacks_or_categories     | threshold_modes_and_grid                                                                 | tails     |
|:-------------------------|:---------------------------|:-------------------------------------------------------------------------------------------------|:----------------------------|:-----------------------------------------------------------------------------------------|:----------|
| directional_persistence  | posfrac_3/6/12/24          | fraction of positive close-to-close returns in last n bars                                       | n ∈ {3,6,12,24}             | absolute {0.25,0.35,0.45,0.55,0.65,0.75}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| directional_continuation | ret_3/6/12/24/48           | n-bar close return close_t/close_{t-n} - 1                                                       | n ∈ {3,6,12,24,48}          | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| trend_quality            | retvol_3/6/12/24/48        | n-bar compounded close return divided by rolling sample std of 1-bar close returns times sqrt(n) | n ∈ {3,6,12,24,48}          | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| range_location           | rangepct_6/12/24/48        | (close - rolling_low_n)/(rolling_high_n - rolling_low_n)                                         | n ∈ {6,12,24,48}            | absolute {0.20,0.30,0.40,0.60,0.70,0.80}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| drawdown_pullback        | drawdown_12/24/48          | close/rolling_high_n - 1                                                                         | n ∈ {12,24,48}              | train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                                           | high, low |
| volatility_level         | atrpct_6/12/24             | ATR_n / close, ATR_n = simple rolling mean of true range                                         | n ∈ {6,12,24}               | train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                                           | high, low |
| volatility_clustering    | volcluster_3_12/6_24/12_48 | sample std of log returns over short window divided by sample std over long window               | (3,12), (6,24), (12,48)     | fixed_one 1.0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                            | high, low |
| participation_volume     | volratio_6/12/24           | quote_volume / rolling_mean_quote_volume_n                                                       | n ∈ {6,12,24}               | fixed_one 1.0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                            | high, low |
| participation_flow       | takeratio_1/3/6            | rolling mean_n of taker_buy_base_vol / volume                                                    | n ∈ {1,3,6}                 | absolute {0.40,0.45,0.48,0.52,0.55,0.60}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| candle_body              | bodyfrac_1/3               | rolling mean_n of (close-open)/(high-low)                                                        | n ∈ {1,3}                   | zero 0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                                   | high, low |
| candle_location          | closeloc_1/3               | rolling mean_n of (close-low)/(high-low)                                                         | n ∈ {1,3}                   | absolute {0.20,0.30,0.40,0.60,0.70,0.80}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| calendar_dow             | calendar_dow               | day-of-week category from bar open_time UTC, Monday=0 … Sunday=6                                 | categories {0,1,2,3,4,5,6}  | category exact match                                                                     | category  |
| calendar_hour            | calendar_hour              | hour-of-day category from bar open_time UTC                                                      | categories {0,4,8,12,16,20} | category exact match                                                                     | category  |

The Native H4 scan enumerates **349** executable long/flat state systems. The exact bucket-level count and pass totals were:

| bucket    |   configs_scanned |   configs_pass_gate | how_count_is_reached                                             |
|:----------|------------------:|--------------------:|:-----------------------------------------------------------------|
| Native H4 |               349 |                  55 | Same family structure scaled to 4h lookbacks, plus calendar_hour |

### 8.4 Cross-timeframe relationship library

For every cross-timeframe feature, join the most recent **completed** D1 value onto H4 bars by backward as-of alignment on **D1 `close_time` to H4 `close_time`**. A D1 row is invisible to an H4 bar until the D1 `close_time` has passed.

The 8 scanned cross-timeframe features are:

| feature                 | formula                                                        | threshold_modes_and_grid                                                                 | tails     |
|:------------------------|:---------------------------------------------------------------|:-----------------------------------------------------------------------------------------|:----------|
| x_rel_d1close_atr       | (h4_close - last_completed_d1_close) / visible_d1_atr_abs      | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| x_rel_d1high_atr        | (h4_close - last_completed_d1_high) / visible_d1_atr_abs       | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| x_rel_d1low_atr         | (h4_close - last_completed_d1_low) / visible_d1_atr_abs        | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| x_in_d1range            | (h4_close - visible_d1_low)/(visible_d1_high - visible_d1_low) | absolute {0.20,0.30,0.40,0.60,0.70,0.80}; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80} | high, low |
| x_h4atr6_vs_d1atr       | h4_atr6_pct / visible_d1_atr20_pct                             | fixed_one 1.0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                            | high, low |
| x_h4volshare_d1         | h4_quote_volume / (visible_d1_quote_volume / 6)                | fixed_one 1.0; train_quantile {0.20,0.30,0.40,0.60,0.70,0.80}                            | high, low |
| x_h4ret6_vs_d1ret20     | h4_ret6 - visible_d1_ret20 / 5                                 | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |
| x_h4rangepct_vs_d1trend | (h4_rangepct24 - 0.5) * sign(visible_d1_ret20)                 | zero 0; train_quantile {0.25,0.35,0.45,0.55,0.65,0.75}                                   | high, low |

The cross-timeframe scan enumerates **68** executable state systems. The exact bucket-level count and pass totals were:

| bucket          |   configs_scanned |   configs_pass_gate | how_count_is_reached                                 |
|:----------------|------------------:|--------------------:|:-----------------------------------------------------|
| Cross-timeframe |                68 |                   6 | 8 relation features with feature-specific mode grids |

### 8.5 Transported D1-on-H4 library

The transported-D1-on-H4 bucket is not a new family library. It is the exact Native D1 library transported to H4 bars as redundancy controls:

- compute the D1 feature natively on the D1 file,
- align the completed D1 feature to H4 bars by backward as-of join on D1 `close_time` to H4 `close_time`,
- evaluate the resulting binary long/flat rule on H4 bars with the same bar-return engine used for native H4 strategies.

Use the same formulas, lookback sets, threshold modes, threshold grids, and tails as the native D1 library, but prefix transported feature names with `transport_`.

The transported scan enumerates **343** executable state systems. The exact bucket-level count and pass totals were:

| bucket               |   configs_scanned |   configs_pass_gate | how_count_is_reached                                      |
|:---------------------|------------------:|--------------------:|:----------------------------------------------------------|
| Transported D1 on H4 |               343 |                 179 | Exact D1 library transported to H4 as redundancy controls |

### 8.6 Exact threshold grids by mode

Use these exact grids and no others:

- `zero`: threshold = `0`
- `fixed_one`: threshold = `1.0`
- `absolute` on `posfrac`: `{0.25, 0.35, 0.45, 0.55, 0.65, 0.75}`
- `absolute` on `rangepct` and `closeloc`: `{0.20, 0.30, 0.40, 0.60, 0.70, 0.80}`
- `absolute` on `takeratio`: `{0.40, 0.45, 0.48, 0.52, 0.55, 0.60}`
- `train_quantile` for bounded or nonnegative families using `{0.20, 0.30, 0.40, 0.60, 0.70, 0.80}`
- `train_quantile` for signed families using `{0.25, 0.35, 0.45, 0.55, 0.65, 0.75}`
- `category`: exact category match on the listed calendar category values

For `train_quantile`, compute the empirical quantile from all feature values in the pre-fold training region only, using linear interpolation on non-null feature values.

### 8.7 Tail semantics

For every numeric feature:

- `high` tail means long when `feature >= threshold`
- `low` tail means long when `feature <= threshold`

For `category` features:

- long when the category of the completed bar equals the tested category value.

## 9. Stage 1 screening gate

A Stage 1 config passes only if all of the following are true on aggregate discovery walk-forward after 20 bps round-trip cost:

1. positive aggregate discovery edge,
2. at least 20 discovery trades across the 14 discovery quarters, unless a sparse-design exception is explicitly documented later,
3. at least 50% of discovery folds nonnegative after cost,
4. no obvious dependence on one isolated quarter,
5. no leakage.

The isolated-quarter filter is implemented by checking how much of the total positive fold profit comes from the single biggest positive fold. Configs dominated by one fold are flagged and rejected from promotion. This is consistent with the saved `isolated_quarter_flag` and `largest_positive_fold_share` columns in the Stage 1 result tables.

## 10. Stage 1 outputs and bucket conclusions

Bucket summary of the full scan:

| bucket               |   configs_scanned |   configs_pass_gate | best_cagr   |   best_sharpe | best_config_id                          |
|:---------------------|------------------:|--------------------:|:------------|--------------:|:----------------------------------------|
| native_d1            |               343 |                 178 | 101.3%      |         1.694 | native_d1|ret_40|high|zero|0            |
| native_h4            |               349 |                  55 | 47.0%       |         1.117 | native_h4|rangepct_48|high|q|0.60       |
| cross_tf             |                68 |                   6 | 43.5%       |         0.872 | cross_tf|x_h4atr6_vs_d1atr|low|fixed|1  |
| transported_d1_on_h4 |               343 |                 179 | 101.3%      |         1.694 | transported_d1_on_h4|ret_40|high|zero|0 |

The bucket conclusions that governed promotion were:

- D1 slower-timeframe volatility-state structure was the strongest slower frontier.
- Genuine native H4 structure was strongest in breakout/location and trend continuation families.
- Cross-timeframe relation features were discovery-positive in a few cases but not robust enough under cost stress to survive.
- Transported D1-on-H4 clones were nearly exact restatements of slower information, not genuinely new fast information.

## 11. Stage 2 shortlist formation

The Stage 2 keep/drop ledger is:

| stage   | item_id                                          | action   | reason                                                                                                                                           |
|:--------|:-------------------------------------------------|:---------|:-------------------------------------------------------------------------------------------------------------------------------------------------|
| stage2  | native_d1|volcluster_5_20|low|fixed|1            | keep     | Strong slower volatility-state representative; discovery CAGR 0.708, Sharpe 1.267, 126 trades, positive holdout later, reserve later positive.   |
| stage2  | native_d1|atrpct_10|high|q|0.60                  | keep     | Simple slower volatility-level rival; strong discovery metrics and independent corroboration of slower volatility regime family.                 |
| stage2  | native_d1|ret_40|high|q|0.75                     | keep     | Best slower directional/trend representative; strong discovery edge despite sparse trade count.                                                  |
| stage2  | native_d1|takeratio_10|low|abs|0.480             | keep     | Orthogonal slower participation/flow representative; lower exposure and distinct failure mode.                                                   |
| stage2  | native_h4|rangepct_48|high|q|0.60                | keep     | Best native H4 range/breakout representative; strong discovery and positive holdout.                                                             |
| stage2  | native_h4|ret_48|high|q|0.55                     | keep     | Simple native H4 momentum representative; broad local plateau and nearest simple rival to H4 range.                                              |
| stage2  | native_h4|takeratio_6|high|abs|0.520             | keep     | Orthogonal H4 participation filter; modest edge and useful as optional entry/filter candidate.                                                   |
| stage2  | native_h4|retvol_48|high|q|0.55                  | drop     | Near-duplicate of native_h4|ret_48|high|q|0.55 with very high daily correlation; ret_48 is simpler.                                              |
| stage2  | cross_tf|x_rel_d1low_atr|high|zero|0             | drop     | Cross-timeframe relation candidate was discovery-positive but failed 50 bps stress and carried high drawdown.                                    |
| stage2  | cross_tf|x_h4rangepct_vs_d1trend|high|zero|0     | drop     | Cross-timeframe relation candidate discovery edge proved cost-fragile and not frontier-worthy.                                                   |
| stage2  | transported_d1_on_h4|volcluster_5_20|low|fixed|1 | drop     | Transported slower-state clone; not independent fast information, daily-return correlation with native D1 clone ≈ 0.9996.                        |
| stage3  | 2L_VOLCL_RANGE48_Q60                             | keep     | Best two-layer family from discovery; D1 volcluster gate + H4 range controller improved Sharpe and drawdown versus H4 controller alone.          |
| stage3  | 2L_VOLCL_RET48_Q55                               | keep     | Nearest two-layer internal rival within same gate family; retained for comparison-set freeze.                                                    |
| stage3  | 2L_TAKER10_RANGE48_ABS060                        | keep     | Orthogonal lower-risk layered alternative with distinct failure mode; retained for frozen comparison set.                                        |
| stage3  | 3L_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052         | drop     | Entry-only confirmation layer shrank trades too severely and degraded discovery, holdout, and reserve performance; layer did not earn its place. |

The 7 single-candidate survivors frozen as family representatives were:

1. `S_D1_VOLCL5_20_LOW_F1`
2. `S_D1_ATR10_HI_Q60`
3. `S_D1_RET40_HI_Q75`
4. `S_D1_TAKER10_LOW_ABS048`
5. `S_H4_RANGE48_HI_Q60`
6. `S_H4_RET48_HI_Q55`
7. `S_H4_TAKER6_HI_ABS052`

Two important Stage 2 judgments were decisive:

- The cross-timeframe relationship bucket did not produce a frontier survivor because its best positives were cost-fragile and did not survive 50 bps round-trip stress strongly enough to justify promotion.
- The transported D1-on-H4 bucket did not produce a frontier survivor because the transported clones were almost exact copies of native slower systems. The locked redundancy audit for the final-family example was `ρ ≈ 0.999638` between the native D1 volcluster leader and its transported H4 clone.

## 12. Stage 3 layered architectures

Construct only minimal layered systems from surviving Stage 2 representatives. Do not brute-force the full cross-product.

### 12.1 Two-layer candidates actually built

- `L2_VOLCL_RANGE48_Q60`  
  Gate: transported D1 `volcluster_5_20 <= 1.0`  
  Controller: native H4 `rangepct_48 >= train_quantile_0.60`  
  State rule: long only when both gate and controller are true on the completed H4 bar; otherwise flat.

- `L2_VOLCL_RET48_Q55`  
  Gate: transported D1 `volcluster_5_20 <= 1.0`  
  Controller: native H4 `ret_48 >= train_quantile_0.55`  
  State rule: long only when both gate and controller are true on the completed H4 bar; otherwise flat.

- `L2_TAKER10_RANGE48_ABS060`  
  Gate: transported D1 `takeratio_10 <= 0.48`  
  Controller: native H4 `rangepct_48 >= 0.60` absolute  
  State rule: long only when both gate and controller are true on the completed H4 bar; otherwise flat.

### 12.2 Three-layer candidate actually built and dropped

- `L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052`  
  Core hold logic: identical to `L2_VOLCL_RANGE48_Q60`  
  Entry filter: when flat and the 2-layer core turns on, require native H4 `takeratio_6 >= 0.52` on that entry bar only  
  Hold rule after entry: ignore the entry-only filter and continue holding as long as the 2-layer core remains long  
  Exit rule: exit when the 2-layer core turns off

This 3-layer candidate was dropped because the extra entry filter collapsed trade count and degraded discovery, holdout, and reserve performance.

The exact candidate formulas used from freeze onward were:

| candidate_id                             | type                         | execution_timeframe                   | exact_rule                                                                                                                                                                         | state_machine                                                  |
|:-----------------------------------------|:-----------------------------|:--------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
| S_D1_VOLCL5_20_LOW_F1                    | single                       | D1                                    | volcluster_5_20 <= 1.0 on previous completed D1 bar                                                                                                                                | 100% long if true, else flat                                   |
| S_D1_ATR10_HI_Q60                        | single                       | D1                                    | atrpct_10 >= expanding-train 0.60 quantile on previous completed D1 bar                                                                                                            | 100% long if true, else flat                                   |
| S_D1_RET40_HI_Q75                        | single                       | D1                                    | ret_40 >= expanding-train 0.75 quantile on previous completed D1 bar                                                                                                               | 100% long if true, else flat                                   |
| S_D1_TAKER10_LOW_ABS048                  | single                       | D1                                    | takeratio_10 <= 0.48 on previous completed D1 bar                                                                                                                                  | 100% long if true, else flat                                   |
| S_H4_RANGE48_HI_Q60                      | single                       | H4                                    | rangepct_48 >= expanding-train 0.60 quantile on previous completed H4 bar                                                                                                          | 100% long if true, else flat                                   |
| S_H4_RET48_HI_Q55                        | single                       | H4                                    | ret_48 >= expanding-train 0.55 quantile on previous completed H4 bar                                                                                                               | 100% long if true, else flat                                   |
| S_H4_TAKER6_HI_ABS052                    | single                       | H4                                    | takeratio_6 >= 0.52 on previous completed H4 bar                                                                                                                                   | 100% long if true, else flat                                   |
| L2_VOLCL_RANGE48_Q60                     | layered2                     | H4 execution with transported D1 gate | transported D1 volcluster_5_20 <= 1.0 gate AND native H4 rangepct_48 >= expanding-train 0.60 quantile controller on previous completed H4 bar                                      | Long only when both gate and controller are true               |
| L2_VOLCL_RET48_Q55                       | layered2                     | H4 execution with transported D1 gate | transported D1 volcluster_5_20 <= 1.0 gate AND native H4 ret_48 >= expanding-train 0.55 quantile controller on previous completed H4 bar                                           | Long only when both gate and controller are true               |
| L2_TAKER10_RANGE48_ABS060                | layered2                     | H4 execution with transported D1 gate | transported D1 takeratio_10 <= 0.48 gate AND native H4 rangepct_48 >= 0.60 absolute controller on previous completed H4 bar                                                        | Long only when both gate and controller are true               |
| L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052 | layered3 tested then dropped | H4 execution with transported D1 gate | Core = L2_VOLCL_RANGE48_Q60. Entry from flat additionally requires native H4 takeratio_6 >= 0.52 on the entry bar only. Once long, holding still depends only on the 2-layer core. | Dropped because trade count collapsed and performance degraded |

## 13. Stage 4 local refinement and plateau analysis

Search broad discrete grids first. Refine only around stable regions. Use the tested-grid neighbors as the plateau neighborhood.

### 13.1 Strict local 80% plateau score

For every serious candidate, define its local neighborhood from the nearest-grid perturbations of every tunable quantity, using at least ±20% or nearest-grid equivalent. A neighborhood cell qualifies if it preserves the same directional story and keeps both discovery CAGR and discovery daily Sharpe at least 80% of the anchor candidate’s discovery values. The strict local 80% plateau score is:

`qualifying_cell_count / local_cell_count`

The saved plateau summary for the serious candidates is:

| candidate_id          |   strict_80pct_plateau_score |   local_cell_count |   qualifying_cell_count |
|:----------------------|-----------------------------:|-------------------:|------------------------:|
| S_D1_VOLCL5_20_LOW_F1 |                         0.33 |                  3 |                       1 |
| S_D1_ATR10_HI_Q60     |                         0.33 |                  3 |                       1 |
| S_H4_RANGE48_HI_Q60   |                         0.33 |                  6 |                       2 |
| S_H4_RET48_HI_Q55     |                         0.75 |                  4 |                       3 |
| L2_VOLCL_RANGE48_Q60  |                         0.75 |                  4 |                       3 |

For the final leader `S_D1_VOLCL5_20_LOW_F1`, the exact neighborhood was the fixed-one low-tail volcluster family cells:

- `volcluster_5_20` low fixed_one 1.0
- `volcluster_10_40` low fixed_one 1.0
- `volcluster_20_80` low fixed_one 1.0

Only the anchor cell itself satisfied the strict 80% test, so the score is `1 / 3 = 0.33`. This is **not** a flat tabletop. The cell was still accepted because:

1. all coarse volatility-clustering perturbations remained directionally positive,
2. the slower volatility-state family was independently corroborated by the D1 ATR family,
3. reserve/internal supported the candidate while the main alternatives broke.

## 14. Stage 5 freeze from internal evidence only

### 14.1 Discovery-only comparison-set freeze

Freeze the comparison set from discovery evidence only. The resulting frozen comparison set and its discovery-only freeze rationale were:

| candidate_id              | type     |   complexity | reason_frozen_from_discovery_only                                                                                                  | discovery_cagr   |   discovery_sharpe |   discovery_trades | discovery_positive_fold_share   |
|:--------------------------|:---------|-------------:|:-----------------------------------------------------------------------------------------------------------------------------------|:-----------------|-------------------:|-------------------:|:--------------------------------|
| S_D1_ATR10_HI_Q60         | single   |            1 | Simple slower volatility-level rival from the same broad family as the final leader; retained despite sparse expected trade count. | 65.1%            |              1.313 |                 32 | 85.7%                           |
| S_D1_VOLCL5_20_LOW_F1     | single   |            1 | Strongest simple slower volatility-state candidate by discovery robustness and later the final frozen leader.                      | 70.8%            |              1.267 |                126 | 78.6%                           |
| S_D1_RET40_HI_Q75         | single   |            1 | Simple slower directional/trend rival with strong discovery edge but sparse behavior.                                              | 45.8%            |              1.263 |                 25 | 85.7%                           |
| S_D1_TAKER10_LOW_ABS048   | single   |            1 | Orthogonal slower flow/participation representative with low exposure and distinct failure mode.                                   | 25.0%            |              1.224 |                 21 | 85.7%                           |
| S_H4_RET48_HI_Q55         | single   |            1 | Simplest viable native H4 momentum representative from the strongest H4 directional family.                                        | 40.2%            |              0.973 |                220 | 71.4%                           |
| S_H4_RANGE48_HI_Q60       | single   |            1 | Best native H4 breakout/location representative and strongest genuine faster frontier rival.                                       | 47.0%            |              1.117 |                219 | 64.3%                           |
| S_H4_TAKER6_HI_ABS052     | single   |            1 | Orthogonal native H4 participation candidate used as stand-alone rival and entry-filter source.                                    | 9.1%             |              0.866 |                 64 | 78.6%                           |
| L2_VOLCL_RET48_Q55        | layered2 |            2 | Nearest serious two-layer rival within the D1-volcluster gate family using H4 momentum controller.                                 | 43.6%            |              1.164 |                201 | 71.4%                           |
| L2_VOLCL_RANGE48_Q60      | layered2 |            2 | Best discovery two-layer candidate and nearest serious complex rival to the final leader.                                          | 59.7%            |              1.588 |                184 | 71.4%                           |
| L2_TAKER10_RANGE48_ABS060 | layered2 |            2 | Orthogonal layered low-exposure alternative retained to avoid one-family tunnel vision.                                            | 9.1%             |              0.816 |                 20 | 92.9%                           |

### 14.2 Holdout opening and pre-reserve leader declaration

After the discovery-only freeze, evaluate only the frozen specifications on the holdout. Do not add new candidates, new features, new thresholds, or new parameter cells.

The stitched segment metrics for the frozen comparison set are:

| candidate_id              | segment     | cagr   |   sharpe_daily | max_drawdown   |   trade_count | exposure   | total_return   |
|:--------------------------|:------------|:-------|---------------:|:---------------|--------------:|:-----------|:---------------|
| S_D1_ATR10_HI_Q60         | discovery   | 65.1%  |          1.313 | -44.6%         |            32 | 28.5%      | 476.8%         |
| S_D1_ATR10_HI_Q60         | holdout     | 3.1%   |          0.245 | -17.3%         |             5 | 12.4%      | 3.9%           |
| S_D1_ATR10_HI_Q60         | reserve     | -1.3%  |          0.069 | -17.2%         |             8 | 11.1%      | -1.9%          |
| S_D1_ATR10_HI_Q60         | pre_reserve | 45.8%  |          1.115 | -44.6%         |            37 | 24.3%      | 499.1%         |
| S_D1_VOLCL5_20_LOW_F1     | discovery   | 70.8%  |          1.267 | -51.6%         |           126 | 60.3%      | 550.5%         |
| S_D1_VOLCL5_20_LOW_F1     | holdout     | 26.2%  |          0.844 | -36.4%         |            32 | 60.3%      | 33.9%          |
| S_D1_VOLCL5_20_LOW_F1     | reserve     | 29.2%  |          0.979 | -21.1%         |            51 | 59.3%      | 45.2%          |
| S_D1_VOLCL5_20_LOW_F1     | pre_reserve | 57.7%  |          1.17  | -51.6%         |           157 | 60.3%      | 771.1%         |
| S_D1_RET40_HI_Q75         | discovery   | 45.8%  |          1.263 | -25.2%         |            25 | 23.4%      | 273.3%         |
| S_D1_RET40_HI_Q75         | holdout     | 31.1%  |          1.166 | -15.2%         |             3 | 18.8%      | 40.4%          |
| S_D1_RET40_HI_Q75         | reserve     | 15.2%  |          0.953 | -8.5%          |             5 | 10.9%      | 22.9%          |
| S_D1_RET40_HI_Q75         | pre_reserve | 41.7%  |          1.234 | -25.2%         |            28 | 22.2%      | 424.0%         |
| S_D1_TAKER10_LOW_ABS048   | discovery   | 25.0%  |          1.224 | -19.2%         |            21 | 9.1%       | 118.5%         |
| S_D1_TAKER10_LOW_ABS048   | holdout     | 5.5%   |          0.391 | -17.7%         |            10 | 15.1%      | 7.0%           |
| S_D1_TAKER10_LOW_ABS048   | reserve     | -4.0%  |          0.013 | -33.4%         |            20 | 34.5%      | -5.8%          |
| S_D1_TAKER10_LOW_ABS048   | pre_reserve | 19.6%  |          1.022 | -19.2%         |            31 | 10.7%      | 133.7%         |
| S_H4_RET48_HI_Q55         | discovery   | 40.2%  |          0.973 | -55.0%         |           220 | 44.7%      | 225.9%         |
| S_H4_RET48_HI_Q55         | holdout     | 8.0%   |          0.393 | -32.9%         |            87 | 45.1%      | 10.1%          |
| S_H4_RET48_HI_Q55         | reserve     | 1.7%   |          0.193 | -27.8%         |            98 | 39.3%      | 2.5%           |
| S_H4_RET48_HI_Q55         | pre_reserve | 30.9%  |          0.844 | -55.0%         |           307 | 44.8%      | 258.7%         |
| S_H4_RANGE48_HI_Q60       | discovery   | 47.0%  |          1.117 | -33.6%         |           219 | 41.0%      | 284.3%         |
| S_H4_RANGE48_HI_Q60       | holdout     | 24.5%  |          0.841 | -21.7%         |            77 | 40.9%      | 31.6%          |
| S_H4_RANGE48_HI_Q60       | reserve     | -20.2% |         -0.692 | -51.4%         |           123 | 37.3%      | -28.1%         |
| S_H4_RANGE48_HI_Q60       | pre_reserve | 40.7%  |          1.051 | -33.6%         |           296 | 40.9%      | 405.8%         |
| S_H4_TAKER6_HI_ABS052     | discovery   | 9.1%   |          0.866 | -7.9%          |            64 | 2.2%       | 35.6%          |
| S_H4_TAKER6_HI_ABS052     | holdout     | 3.6%   |          0.379 | -13.5%         |            39 | 4.0%       | 4.5%           |
| S_H4_TAKER6_HI_ABS052     | reserve     | -29.8% |         -2.883 | -41.0%         |           100 | 7.5%       | -40.3%         |
| S_H4_TAKER6_HI_ABS052     | pre_reserve | 7.6%   |          0.738 | -13.5%         |           103 | 2.7%       | 41.7%          |
| L2_VOLCL_RET48_Q55        | discovery   | 43.6%  |          1.164 | -28.2%         |           201 | 26.0%      | 254.1%         |
| L2_VOLCL_RET48_Q55        | holdout     | -6.6%  |         -0.157 | -32.5%         |            74 | 27.6%      | -8.2%          |
| L2_VOLCL_RET48_Q55        | reserve     | -6.0%  |         -0.214 | -18.4%         |            85 | 23.9%      | -8.7%          |
| L2_VOLCL_RET48_Q55        | pre_reserve | 28.2%  |          0.897 | -32.5%         |           275 | 26.5%      | 224.9%         |
| L2_VOLCL_RANGE48_Q60      | discovery   | 59.7%  |          1.588 | -23.4%         |           184 | 24.7%      | 414.1%         |
| L2_VOLCL_RANGE48_Q60      | holdout     | 15.9%  |          0.757 | -20.3%         |            64 | 24.1%      | 20.3%          |
| L2_VOLCL_RANGE48_Q60      | reserve     | -25.0% |         -1.307 | -40.8%         |           102 | 23.4%      | -34.2%         |
| L2_VOLCL_RANGE48_Q60      | pre_reserve | 46.8%  |          1.407 | -23.4%         |           248 | 24.5%      | 518.4%         |
| L2_TAKER10_RANGE48_ABS060 | discovery   | 9.1%   |          0.816 | -6.7%          |            20 | 3.7%       | 35.8%          |
| L2_TAKER10_RANGE48_ABS060 | holdout     | -4.7%  |         -0.651 | -10.2%         |            17 | 2.0%       | -5.8%          |
| L2_TAKER10_RANGE48_ABS060 | reserve     | 2.2%   |          0.221 | -17.7%         |            37 | 10.6%      | 3.3%           |
| L2_TAKER10_RANGE48_ABS060 | pre_reserve | 5.3%   |          0.543 | -10.3%         |            37 | 3.3%       | 27.8%          |

### 14.3 Paired bootstrap configuration

Use paired moving-block bootstrap on **daily UTC return series**. Use the same resampled day path for both candidates inside each pair.

Locked configuration used by the saved pairwise tables:

- resampling unit: daily UTC returns
- block sizes: `5`, `10`, `20`
- metrics evaluated on the bootstrap difference distribution:
  - mean daily return
  - CAGR
  - daily Sharpe
- paired-comparison segments:
  - discovery
  - pre-reserve

The saved probabilities are consistent with **2,000 resamples per block size**. The original RNG seed was not serialized into the saved outputs, so exact last-decimal bootstrap probabilities require either the original seed or the saved tables themselves as the locked truth. The selection logic, however, is governed by the probability regime, not by an arbitrary seed-specific last decimal.

The pairwise summary among the decisive rivals is:

| candidate_a             | candidate_b               | segment     | blocks   |   p_mean_daily_gt0_mean |   p_mean_daily_gt0_min |   mean_daily_diff_boot_p50_avg |   p_cagr_gt0_mean |   cagr_diff_p50_avg |   p_sharpe_gt0_mean |   sharpe_diff_p50_avg |
|:------------------------|:--------------------------|:------------|:---------|------------------------:|-----------------------:|-------------------------------:|------------------:|--------------------:|--------------------:|----------------------:|
| S_D1_VOLCL5_20_LOW_F1   | S_D1_ATR10_HI_Q60         | discovery   | 5,10,20  |                  0.57   |                 0.551  |                       0.000136 |            0.517  |            0.021286 |              0.4313 |             -0.09148  |
| S_D1_VOLCL5_20_LOW_F1   | S_D1_ATR10_HI_Q60         | pre_reserve | 5,10,20  |                  0.7088 |                 0.7055 |                       0.000295 |            0.6417 |            0.108811 |              0.5388 |              0.038516 |
| S_D1_VOLCL5_20_LOW_F1   | S_D1_RET40_HI_Q75         | discovery   | 5,10,20  |                  0.8    |                 0.778  |                       0.000621 |            0.701  |            0.225607 |              0.4815 |             -0.028824 |
| S_D1_VOLCL5_20_LOW_F1   | S_D1_RET40_HI_Q75         | pre_reserve | 5,10,20  |                  0.7935 |                 0.7865 |                       0.000472 |            0.6882 |            0.15248  |              0.4427 |             -0.067905 |
| S_D1_VOLCL5_20_LOW_F1   | S_H4_RANGE48_HI_Q60       | discovery   | 5,10,20  |                  0.7803 |                 0.771  |                       0.000537 |            0.7105 |            0.218483 |              0.6107 |              0.148279 |
| S_D1_VOLCL5_20_LOW_F1   | S_H4_RANGE48_HI_Q60       | pre_reserve | 5,10,20  |                  0.7902 |                 0.777  |                       0.00044  |            0.7232 |            0.175213 |              0.6248 |              0.143841 |
| S_D1_VOLCL5_20_LOW_F1   | L2_VOLCL_RANGE48_Q60      | discovery   | 5,10,20  |                  0.7578 |                 0.7545 |                       0.000392 |            0.6077 |            0.08945  |              0.1972 |             -0.346316 |
| S_D1_VOLCL5_20_LOW_F1   | L2_VOLCL_RANGE48_Q60      | pre_reserve | 5,10,20  |                  0.8255 |                 0.817  |                       0.00041  |            0.6802 |            0.111653 |              0.271  |             -0.216953 |
| S_H4_RANGE48_HI_Q60     | S_H4_RET48_HI_Q55         | discovery   | 5,10,20  |                  0.6158 |                 0.6105 |                       0.000104 |            0.645  |            0.069085 |              0.688  |              0.147528 |
| S_H4_RANGE48_HI_Q60     | S_H4_RET48_HI_Q55         | pre_reserve | 5,10,20  |                  0.7115 |                 0.703  |                       0.000157 |            0.7338 |            0.089893 |              0.7687 |              0.192242 |
| L2_VOLCL_RANGE48_Q60    | L2_VOLCL_RET48_Q55        | discovery   | 5,10,20  |                  0.8513 |                 0.8375 |                       0.00026  |            0.8838 |            0.163493 |              0.955  |              0.431387 |
| L2_VOLCL_RANGE48_Q60    | L2_VOLCL_RET48_Q55        | pre_reserve | 5,10,20  |                  0.9462 |                 0.9445 |                       0.000331 |            0.9605 |            0.179149 |              0.9862 |              0.49802  |
| L2_VOLCL_RANGE48_Q60    | S_H4_RANGE48_HI_Q60       | discovery   | 5,10,20  |                  0.6468 |                 0.628  |                       0.000164 |            0.7322 |            0.142157 |              0.9178 |              0.493314 |
| L2_VOLCL_RANGE48_Q60    | S_H4_RANGE48_HI_Q60       | pre_reserve | 5,10,20  |                  0.5575 |                 0.54   |                       4.6e-05  |            0.668  |            0.070304 |              0.888  |              0.367159 |
| S_D1_TAKER10_LOW_ABS048 | L2_TAKER10_RANGE48_ABS060 | discovery   | 5,10,20  |                  0.989  |                 0.983  |                       0.000405 |            0.9743 |            0.159007 |              0.8643 |              0.492773 |
| S_D1_TAKER10_LOW_ABS048 | L2_TAKER10_RANGE48_ABS060 | pre_reserve | 5,10,20  |                  0.99   |                 0.987  |                       0.000387 |            0.981  |            0.144453 |              0.918  |              0.545176 |

### 14.4 Meaningful paired-advantage rule actually used

The saved `meaningful_advantage_a_over_b` flags in the pairwise matrix are exactly reproduced by this rule on the **pre-reserve** segment:

- `p_mean_daily_gt0_min >= 0.70`
- and at least one of:
  - `p_cagr_gt0_mean >= 0.70`
  - `p_sharpe_gt0_mean >= 0.70`

If a more complex candidate does not clear that meaningful-advantage rule over a simpler nearby rival, the simpler rival wins.

### 14.5 Candidate eliminations

| eliminated_candidate      | exact_reason                                                                                                                                                                                                                                                                                                                                                                                                                            |
|:--------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L2_VOLCL_RANGE48_Q60      | Discovery Sharpe and drawdown improved versus winner, but mixed paired evidence on pre-reserve. p_mean_daily_gt0_mean=0.8255 and p_mean_daily_gt0_min=0.8170 favored the simple winner on mean return, yet p_sharpe_gt0_mean=0.2710 did not support a meaningful complex advantage. Complexity rule therefore selected the simpler S_D1_VOLCL5_20_LOW_F1. Reserve/internal then turned negative: CAGR -25.0%, Sharpe -1.31, MDD -40.8%. |
| S_H4_RANGE48_HI_Q60       | Best genuine native H4 rival. The simple D1 winner showed a meaningful paired advantage on pre-reserve: p_mean_daily_gt0_min=0.7770, p_cagr_gt0_mean=0.7232, p_sharpe_gt0_mean=0.6248. Reserve/internal then turned negative: CAGR -20.2%, Sharpe -0.69, MDD -51.4%.                                                                                                                                                                    |
| S_H4_RET48_HI_Q55         | Broader plateau than S_H4_RANGE48_HI_Q60 (0.75 vs 0.33) but weaker pre-reserve Sharpe and CAGR. It lost the direct H4-vs-H4 paired comparison: H4 range over H4 ret had p_mean_daily_gt0_min=0.7030, p_cagr_gt0_mean=0.7338, p_sharpe_gt0_mean=0.7687.                                                                                                                                                                                  |
| S_D1_ATR10_HI_Q60         | Same broader slower volatility-state family as the winner, but sparse: 32 discovery trades, 5 holdout trades, 8 reserve trades. Pre-reserve pairwise evidence versus the winner stayed mixed and therefore could not dislodge the simpler fixed-one volcluster cell. Reserve/internal was effectively flat-to-negative: CAGR -1.3%, Sharpe 0.07, total return -1.9%.                                                                    |
| S_D1_RET40_HI_Q75         | Strong discovery and positive holdout, but too sparse to beat the leader as a general-purpose system. The winner kept a higher pre-reserve CAGR and stronger same-family robustness as the broader volatility-state leader.                                                                                                                                                                                                             |
| S_D1_TAKER10_LOW_ABS048   | Useful orthogonal family representative, but weaker growth and reserve/internal negative. It remained in the comparison set to preserve family coverage, not because it was near the leadership frontier.                                                                                                                                                                                                                               |
| S_H4_TAKER6_HI_ABS052     | Useful as an optional participation filter source, but too weak as a stand-alone system and deeply negative on reserve/internal: CAGR -29.8%, Sharpe -2.88, MDD -41.0%.                                                                                                                                                                                                                                                                 |
| L2_VOLCL_RET48_Q55        | Kept only as the nearest internal rival inside the same D1-volcluster-gated layered family. It was materially weaker than L2_VOLCL_RANGE48_Q60 on paired bootstrap and also weaker than the final simple leader on holdout and reserve.                                                                                                                                                                                                 |
| L2_TAKER10_RANGE48_ABS060 | Orthogonal layered low-exposure control. Discovery edge existed, but holdout was negative and reserve advantage was negligible. It could not challenge the leader.                                                                                                                                                                                                                                                                      |

## 15. Stage 6 freeze and Stage 7 reserve/internal evaluation

Before reserve/internal is opened, freeze:

- the exact feature formulas,
- the exact lookbacks,
- the exact threshold modes,
- the exact thresholds or train-quantile rule,
- the exact state machines,
- the exact comparison set,
- the exact anomaly-disposition register,
- the exact pairwise comparison matrix.

Then evaluate the frozen leader and the frozen comparison set exactly once on reserve/internal. No redesign or retuning is permitted after seeing reserve/internal.

The reserve/internal score table for the frozen comparison set is:

| candidate_id              | segment   | cagr   |   sharpe_daily | max_drawdown   |   trade_count | exposure   | total_return   |
|:--------------------------|:----------|:-------|---------------:|:---------------|--------------:|:-----------|:---------------|
| S_D1_ATR10_HI_Q60         | reserve   | -1.3%  |          0.069 | -17.2%         |             8 | 11.1%      | -1.9%          |
| S_D1_VOLCL5_20_LOW_F1     | reserve   | 29.2%  |          0.979 | -21.1%         |            51 | 59.3%      | 45.2%          |
| S_D1_RET40_HI_Q75         | reserve   | 15.2%  |          0.953 | -8.5%          |             5 | 10.9%      | 22.9%          |
| S_D1_TAKER10_LOW_ABS048   | reserve   | -4.0%  |          0.013 | -33.4%         |            20 | 34.5%      | -5.8%          |
| S_H4_RET48_HI_Q55         | reserve   | 1.7%   |          0.193 | -27.8%         |            98 | 39.3%      | 2.5%           |
| S_H4_RANGE48_HI_Q60       | reserve   | -20.2% |         -0.692 | -51.4%         |           123 | 37.3%      | -28.1%         |
| S_H4_TAKER6_HI_ABS052     | reserve   | -29.8% |         -2.883 | -41.0%         |           100 | 7.5%       | -40.3%         |
| L2_VOLCL_RET48_Q55        | reserve   | -6.0%  |         -0.214 | -18.4%         |            85 | 23.9%      | -8.7%          |
| L2_VOLCL_RANGE48_Q60      | reserve   | -25.0% |         -1.307 | -40.8%         |           102 | 23.4%      | -34.2%         |
| L2_TAKER10_RANGE48_ABS060 | reserve   | 2.2%   |          0.221 | -17.7%         |            37 | 10.6%      | 3.3%           |

The critical reserve/internal fact pattern is:

- final winner `S_D1_VOLCL5_20_LOW_F1` stayed positive: CAGR **29.2%**, Sharpe **0.98**, MDD **-21.1%**, 51 trades
- main layered rival `L2_VOLCL_RANGE48_Q60` turned negative: CAGR **-25.0%**, Sharpe **-1.31**, MDD **-40.8%**
- strongest genuine native H4 rival `S_H4_RANGE48_HI_Q60` turned negative: CAGR **-20.2%**, Sharpe **-0.69**, MDD **-51.4%**
- stand-alone H4 participation rival `S_H4_TAKER6_HI_ABS052` collapsed: CAGR **-29.8%**, Sharpe **-2.88**, MDD **-41.0%**

Under V7, reserve/internal is contradiction evidence only. It may confirm or contradict the pre-reserve leader, but it may not trigger redesign, tie-break redesign, or a new search.

## 16. Ablation

The locked ablation family for the main slower-gate plus H4-controller stack is:

| family                  | variant               | candidate_id                             | segment     | cagr   |   sharpe_daily | max_drawdown   |   trade_count | exposure   | total_return   |
|:------------------------|:----------------------|:-----------------------------------------|:------------|:-------|---------------:|:---------------|--------------:|:-----------|:---------------|
| volcluster_range_family | gate_only             | S_D1_VOLCL5_20_LOW_F1                    | discovery   | 70.8%  |          1.267 | -51.6%         |           126 | 60.3%      | 550.5%         |
| volcluster_range_family | gate_only             | S_D1_VOLCL5_20_LOW_F1                    | holdout     | 26.2%  |          0.844 | -36.4%         |            32 | 60.3%      | 33.9%          |
| volcluster_range_family | gate_only             | S_D1_VOLCL5_20_LOW_F1                    | reserve     | 29.2%  |          0.979 | -21.1%         |            51 | 59.3%      | 45.2%          |
| volcluster_range_family | gate_only             | S_D1_VOLCL5_20_LOW_F1                    | pre_reserve | 57.7%  |          1.17  | -51.6%         |           157 | 60.3%      | 771.1%         |
| volcluster_range_family | controller_only       | S_H4_RANGE48_HI_Q60                      | discovery   | 47.0%  |          1.117 | -33.6%         |           219 | 41.0%      | 284.3%         |
| volcluster_range_family | controller_only       | S_H4_RANGE48_HI_Q60                      | holdout     | 24.5%  |          0.841 | -21.7%         |            77 | 40.9%      | 31.6%          |
| volcluster_range_family | controller_only       | S_H4_RANGE48_HI_Q60                      | reserve     | -20.2% |         -0.692 | -51.4%         |           123 | 37.3%      | -28.1%         |
| volcluster_range_family | controller_only       | S_H4_RANGE48_HI_Q60                      | pre_reserve | 40.7%  |          1.051 | -33.6%         |           296 | 40.9%      | 405.8%         |
| volcluster_range_family | layered_2L            | L2_VOLCL_RANGE48_Q60                     | discovery   | 59.7%  |          1.588 | -23.4%         |           184 | 24.7%      | 414.1%         |
| volcluster_range_family | layered_2L            | L2_VOLCL_RANGE48_Q60                     | holdout     | 15.9%  |          0.757 | -20.3%         |            64 | 24.1%      | 20.3%          |
| volcluster_range_family | layered_2L            | L2_VOLCL_RANGE48_Q60                     | reserve     | -25.0% |         -1.307 | -40.8%         |           102 | 23.4%      | -34.2%         |
| volcluster_range_family | layered_2L            | L2_VOLCL_RANGE48_Q60                     | pre_reserve | 46.8%  |          1.407 | -23.4%         |           248 | 24.5%      | 518.4%         |
| volcluster_range_family | layered_3L_with_entry | L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052 | discovery   | 9.2%   |          0.635 | -23.7%         |            25 | 3.8%       | 36.1%          |
| volcluster_range_family | layered_3L_with_entry | L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052 | holdout     | -3.5%  |         -0.354 | -10.9%         |            12 | 4.7%       | -4.3%          |
| volcluster_range_family | layered_3L_with_entry | L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052 | reserve     | -14.9% |         -1.243 | -26.7%         |            27 | 10.0%      | -21.0%         |
| volcluster_range_family | layered_3L_with_entry | L3_VOLCL_RANGE48_Q60_ENTRY_TAKER6_ABS052 | pre_reserve | 5.7%   |          0.459 | -24.2%         |            37 | 4.0%       | 30.2%          |

Interpretation:

- `gate_only` is the final winner and is the strongest all-weather internal result.
- `controller_only` is a real native H4 edge but broke on reserve/internal.
- `layered_2L` improved discovery Sharpe and drawdown but failed the meaningful-advantage complexity test against the simpler winner and then broke on reserve/internal.
- `layered_3L_with_entry` did not earn the extra layer.

## 17. Final frozen result

The exact frozen winner is:

- candidate ID: `S_D1_VOLCL5_20_LOW_F1`
- evidence label: `INTERNAL ROBUST CANDIDATE`
- market: BTC/USDT spot
- side: long-only
- native timeframe: D1
- feature: `volcluster_5_20`
- rule: long if the previous completed D1 bar has `volcluster_5_20 <= 1.0`, else flat
- fill: next D1 open
- position size: 100% notional when long, 0% when flat
- cost: 10 bps per side, 20 bps round-trip

The exact winner-verification table is:

| segment       |   bars |   days |     cagr |   sharpe_daily |   max_drawdown |   trade_count_overlap_segment |   exposure |   total_return |
|:--------------|-------:|-------:|---------:|---------------:|---------------:|------------------------------:|-----------:|---------------:|
| discovery     |   1277 |   1277 | 0.708447 |       1.2668   |      -0.516179 |                           126 |   0.602976 |       5.50474  |
| holdout       |    458 |    458 | 0.262315 |       0.84405  |      -0.363689 |                            32 |   0.60262  |       0.339238 |
| reserve       |    531 |    531 | 0.292342 |       0.979103 |      -0.211357 |                            51 |   0.59322  |       0.451846 |
| pre_reserve   |   1735 |   1735 | 0.57727  |       1.17013  |      -0.516179 |                           157 |   0.602882 |       7.71139  |
| full_internal |   2266 |   2266 | 0.505322 |       1.12298  |      -0.516179 |                           208 |   0.600618 |      11.6476   |

## 18. Benchmark rule and provenance closeout

No benchmark comparison was performed because no benchmark specification was supplied after reserve/internal. Under V7 that is correct behavior.

The admissible-pre-freeze provenance declaration for the original run was clean. That is a locked part of the scientific record for this session.

## 19. Rebuild checklist

An engineer rebuilding from scratch should confirm all of the following before declaring success:

1. audit tables match the anomaly counts and dispositions in this spec,
2. Stage 1 bucket counts are `343 / 349 / 68 / 343`,
3. Stage 1 pass counts are `178 / 55 / 6 / 179`,
4. the Stage 2 keep/drop ledger matches exactly,
5. the frozen comparison set contains the same 10 comparison candidates,
6. discovery and pre-reserve pairwise outcomes support the same eliminations,
7. reserve/internal leaves only `S_D1_VOLCL5_20_LOW_F1` clearly positive among the main frontier rivals,
8. the final evidence label is `INTERNAL ROBUST CANDIDATE`,
9. no benchmark comparison is attempted without separately supplied benchmark specs,
10. no post-freeze redesign occurs for any reason.
