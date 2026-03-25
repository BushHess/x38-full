# D1a Quality Report

Scope: ingestion, canonicalization, and validation of the admitted historical snapshot only. Candidate-mining-only; no clean external OOS claim is made from this snapshot.

No synthetic bar repair, gap filling, or data modification was performed.

## 1. Schema Validation

Required canonical order: `symbol, interval, open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol`.

All four files already arrived in canonical 13-column form. No final unused column was present; no symbol/interval injection was needed; no field renaming was needed.

| timeframe   | file                 | rows    |   original_columns | canonical_actions        | schema_pass   | symbol_ok   | interval_ok   | timestamps_ok   | dominant_delta_ms   | expected_step_ms   |   close_time_offset_bad_rows |
|:------------|:---------------------|:--------|-------------------:|:-------------------------|:--------------|:------------|:--------------|:----------------|:--------------------|:-------------------|-----------------------------:|
| 15m         | spot_btcusdt_15m.csv | 300,479 |                 13 | none (already canonical) | PASS          | PASS        | PASS          | PASS            | 900,000             | 900,000            |                            0 |
| 1h          | spot_btcusdt_1h.csv  | 75,134  |                 13 | none (already canonical) | PASS          | PASS        | PASS          | PASS            | 3,600,000           | 3,600,000          |                            0 |
| 4h          | spot_btcusdt_4h.csv  | 18,799  |                 13 | none (already canonical) | PASS          | PASS        | PASS          | PASS            | 14,400,000          | 14,400,000         |                            0 |
| 1d          | spot_btcusdt_1d.csv  | 3,136   |                 13 | none (already canonical) | PASS          | PASS        | PASS          | PASS            | 86,400,000          | 86,400,000         |                            0 |

## 2. Anomaly Log

Summary counts by timeframe:

| timeframe   |   missing_bars |   missing_gap_segments |   duplicate_rows |   zero_or_negative_price_rows |   zero_volume_rows |   nan_or_null_rows |   high_lt_low_rows |   open_outside_range_rows |   close_outside_range_rows |   taker_gt_volume_rows |   non_multiple_gap_intervals |   close_time_offset_bad_rows |
|:------------|---------------:|-----------------------:|-----------------:|------------------------------:|-------------------:|-------------------:|-------------------:|--------------------------:|---------------------------:|-----------------------:|-----------------------------:|-----------------------------:|
| 15m         |            561 |                     32 |                0 |                             0 |                 61 |                  0 |                  0 |                         0 |                          0 |                      0 |                            0 |                            0 |
| 1h          |            126 |                     28 |                0 |                             0 |                  5 |                  0 |                  0 |                         0 |                          0 |                      0 |                            0 |                            0 |
| 4h          |             16 |                      8 |                0 |                             0 |                  1 |                  0 |                  0 |                         0 |                          0 |                      0 |                            0 |                            0 |
| 1d          |              0 |                      0 |                0 |                             0 |                  0 |                  0 |                  0 |                         0 |                          0 |                      0 |                            0 |                            0 |

### 15m

- Missing bars: 561 (0.1864%) across 32 gap segments.
- Zero-volume bars: 61.
- Duplicate `open_time` rows: 0.
- NaN/null rows: 0.
- Invalid price rows (zero/negative, `high < low`, `open/close` outside range): 0 total; each underlying check individually = 0.
- `taker_buy_base_vol > volume`: 0.
- Non-multiple gap intervals: 0.
- Bad `close_time - open_time` offset rows: 0.
- Largest gap segments:
  - 133 missing bars between `2018-02-08 00:15:00 UTC` and `2018-02-09 09:45:00 UTC` (missing window `2018-02-08 00:30:00 UTC` → `2018-02-09 09:30:00 UTC`).
  - 40 missing bars between `2019-05-15 02:45:00 UTC` and `2019-05-15 13:00:00 UTC` (missing window `2019-05-15 03:00:00 UTC` → `2019-05-15 12:45:00 UTC`).
  - 40 missing bars between `2018-06-26 01:45:00 UTC` and `2018-06-26 12:00:00 UTC` (missing window `2018-06-26 02:00:00 UTC` → `2018-06-26 11:45:00 UTC`).
  - 32 missing bars between `2019-08-15 01:45:00 UTC` and `2019-08-15 10:00:00 UTC` (missing window `2019-08-15 02:00:00 UTC` → `2019-08-15 09:45:00 UTC`).
  - 30 missing bars between `2018-07-04 00:15:00 UTC` and `2018-07-04 08:00:00 UTC` (missing window `2018-07-04 00:30:00 UTC` → `2018-07-04 07:45:00 UTC`).

### 1h

- Missing bars: 126 (0.1674%) across 28 gap segments.
- Zero-volume bars: 5.
- Duplicate `open_time` rows: 0.
- NaN/null rows: 0.
- Invalid price rows (zero/negative, `high < low`, `open/close` outside range): 0 total; each underlying check individually = 0.
- `taker_buy_base_vol > volume`: 0.
- Non-multiple gap intervals: 0.
- Bad `close_time - open_time` offset rows: 0.
- Largest gap segments:
  - 32 missing bars between `2018-02-08 00:00:00 UTC` and `2018-02-09 09:00:00 UTC` (missing window `2018-02-08 01:00:00 UTC` → `2018-02-09 08:00:00 UTC`).
  - 10 missing bars between `2019-05-15 02:00:00 UTC` and `2019-05-15 13:00:00 UTC` (missing window `2019-05-15 03:00:00 UTC` → `2019-05-15 12:00:00 UTC`).
  - 10 missing bars between `2018-06-26 01:00:00 UTC` and `2018-06-26 12:00:00 UTC` (missing window `2018-06-26 02:00:00 UTC` → `2018-06-26 11:00:00 UTC`).
  - 8 missing bars between `2019-08-15 01:00:00 UTC` and `2019-08-15 10:00:00 UTC` (missing window `2019-08-15 02:00:00 UTC` → `2019-08-15 09:00:00 UTC`).
  - 7 missing bars between `2018-11-14 01:00:00 UTC` and `2018-11-14 09:00:00 UTC` (missing window `2018-11-14 02:00:00 UTC` → `2018-11-14 08:00:00 UTC`).

### 4h

- Missing bars: 16 (0.0850%) across 8 gap segments.
- Zero-volume bars: 1.
- Duplicate `open_time` rows: 0.
- NaN/null rows: 0.
- Invalid price rows (zero/negative, `high < low`, `open/close` outside range): 0 total; each underlying check individually = 0.
- `taker_buy_base_vol > volume`: 0.
- Non-multiple gap intervals: 0.
- Bad `close_time - open_time` offset rows: 0.
- Largest gap segments:
  - 7 missing bars between `2018-02-08 00:00:00 UTC` and `2018-02-09 08:00:00 UTC` (missing window `2018-02-08 04:00:00 UTC` → `2018-02-09 04:00:00 UTC`).
  - 2 missing bars between `2019-05-15 00:00:00 UTC` and `2019-05-15 12:00:00 UTC` (missing window `2019-05-15 04:00:00 UTC` → `2019-05-15 08:00:00 UTC`).
  - 2 missing bars between `2018-06-26 00:00:00 UTC` and `2018-06-26 12:00:00 UTC` (missing window `2018-06-26 04:00:00 UTC` → `2018-06-26 08:00:00 UTC`).
  - 1 missing bars between `2020-02-19 08:00:00 UTC` and `2020-02-19 16:00:00 UTC` (missing window `2020-02-19 12:00:00 UTC` → `2020-02-19 12:00:00 UTC`).
  - 1 missing bars between `2019-08-15 00:00:00 UTC` and `2019-08-15 08:00:00 UTC` (missing window `2019-08-15 04:00:00 UTC` → `2019-08-15 04:00:00 UTC`).

### 1d

No anomalies detected.

Observation: all missing bars are confined to warmup/discovery. Holdout and reserve_internal have zero missing bars across all four timeframes.

## 3. Summary Statistics

| timeframe   | total_bars   | first_bar_open_utc      | last_bar_open_utc       | last_bar_close_utc      | expected_bars   | unique_open_times   |   missing_bars | missing_pct_expected   |   duplicate_open_time_rows | duplicate_pct_rows   | min_low   | max_high   | median_daily_volume   | median_daily_num_trades   | zero_volume_pct   |
|:------------|:-------------|:------------------------|:------------------------|:------------------------|:----------------|:--------------------|---------------:|:-----------------------|---------------------------:|:---------------------|:----------|:-----------|:----------------------|:--------------------------|:------------------|
| 15m         | 300,479      | 2017-08-17 04:00:00 UTC | 2026-03-18 23:45:00 UTC | 2026-03-18 23:59:59 UTC | 301,040         | 300,479             |            561 | 0.1864%                |                          0 | 0.0000%              | 2,817.00  | 126,199.63 | 38,909.221420         | 1,162,109                 | 0.020301%         |
| 1h          | 75,134       | 2017-08-17 04:00:00 UTC | 2026-03-18 23:00:00 UTC | 2026-03-18 23:59:59 UTC | 75,260          | 75,134              |            126 | 0.1674%                |                          0 | 0.0000%              | 2,817.00  | 126,199.63 | 38,909.221420         | 1,162,109                 | 0.006655%         |
| 4h          | 18,799       | 2017-08-17 04:00:00 UTC | 2026-03-18 20:00:00 UTC | 2026-03-18 23:59:59 UTC | 18,815          | 18,799              |             16 | 0.0850%                |                          0 | 0.0000%              | 2,817.00  | 126,199.63 | 38,909.221420         | 1,162,109                 | 0.005319%         |
| 1d          | 3,136        | 2017-08-17 00:00:00 UTC | 2026-03-18 00:00:00 UTC | 2026-03-18 23:59:59 UTC | 3,136           | 3,136               |              0 | 0.0000%                |                          0 | 0.0000%              | 2,817.00  | 126,199.63 | 38,909.221420         | 1,162,109                 | 0.000000%         |

## 4. Split Coverage

Counts are based on `open_time` UTC date. Constitution windows:
- warmup: first available bar → 2019-12-31
- discovery: 2020-01-01 → 2023-06-30
- holdout: 2023-07-01 → 2024-09-30
- reserve_internal: 2024-10-01 → snapshot end

| timeframe   | split            | actual_bars   | expected_bars_in_range   |   missing_bars_in_split |
|:------------|:-----------------|:--------------|:-------------------------|------------------------:|
| 15m         | warmup           | 82,807        | 83,216                   |                     409 |
| 15m         | discovery        | 122,440       | 122,592                  |                     152 |
| 15m         | holdout          | 43,968        | 43,968                   |                       0 |
| 15m         | reserve_internal | 51,264        | 51,264                   |                       0 |
| 1h          | warmup           | 20,709        | 20,804                   |                      95 |
| 1h          | discovery        | 30,617        | 30,648                   |                      31 |
| 1h          | holdout          | 10,992        | 10,992                   |                       0 |
| 1h          | reserve_internal | 12,816        | 12,816                   |                       0 |
| 4h          | warmup           | 5,186         | 5,201                    |                      15 |
| 4h          | discovery        | 7,661         | 7,662                    |                       1 |
| 4h          | holdout          | 2,748         | 2,748                    |                       0 |
| 4h          | reserve_internal | 3,204         | 3,204                    |                       0 |
| 1d          | warmup           | 867           | 867                      |                       0 |
| 1d          | discovery        | 1,277         | 1,277                    |                       0 |
| 1d          | holdout          | 458           | 458                      |                       0 |
| 1d          | reserve_internal | 534           | 534                      |                       0 |

## 5. Data Quality Verdict

**PASS**

Rationale:
- Schema validation passed for all four files.
- Dominant bar spacing matches the declared timeframe in every file.
- Missing bars are isolated and well below the 5% blocking threshold in every timeframe.
- No duplicates, nulls, invalid OHLC range relationships, or impossible taker-buy volume rows were found.
- No repairs were performed; anomalies are logged only.

Operational note for later turns: the snapshot remains candidate-mining-only and cannot support a clean external OOS claim.