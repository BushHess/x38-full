# D1a Data Ingestion & Quality Check

Generated from the admitted raw historical snapshot and constitution only.

## Scope and constraints

- Mode remains `seed_discovery`; the historical snapshot is **candidate-mining-only**.
- No clean external OOS claim is made from this snapshot.
- All four raw CSVs were loaded; no synthetic bar repair, gap filling, or data modification was performed.

Files loaded:
- `spot_btcusdt_15m.csv`
- `spot_btcusdt_1h.csv`
- `spot_btcusdt_4h.csv`
- `spot_btcusdt_1d.csv`

Canonical schema target:

`symbol, interval, open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol`

## 1. Schema Validation

| timeframe | raw cols | extra trailing col dropped | symbol injected | interval injected | exact 13-col order | symbol=BTCUSDT | interval matches file | open_time int ms | close_time int ms | bar duration exact | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15m | 13 | no | no | no | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 1h | 13 | no | no | no | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 4h | 13 | no | no | no | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 1d | 13 | no | no | no | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

Notes:
- All four raw files already arrived in canonical 13-column form; no symbol/interval injection was needed and no unused final Binance column was present.
- Canonical order, UTC millisecond timestamps, and exact bar durations all validated.

## 2. Anomaly Log

| timeframe | gap events | missing bars | duplicate open_time rows | zero-volume bars | null cells | zero/negative price bars | high<low | open outside [low,high] | close outside [low,high] | taker_buy_base_vol > volume |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15m | 32 | 561 | 0 | 61 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1h | 28 | 126 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4h | 8 | 16 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1d | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

### Gap distribution by split
| timeframe | warmup gaps / missing | discovery gaps / missing | holdout gaps / missing | reserve_internal gaps / missing |
| --- | --- | --- | --- | --- |
| 15m | 17 / 409 | 15 / 152 | 0 / 0 | 0 / 0 |
| 1h | 13 / 95 | 15 / 31 | 0 / 0 | 0 / 0 |
| 4h | 7 / 15 | 1 / 1 | 0 / 0 | 0 / 0 |
| 1d | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Observation: all detected open-time gaps are confined to `warmup` and `discovery`; none appear in `holdout` or `reserve_internal`.

### 15m

- Missing-bar gaps: **32** gap events, **561** missing bars total.
- First gap: 2017-09-06 16:00:00 UTC → 2017-09-06 23:00:00 UTC (27 missing, split=warmup).
- Last gap: 2023-03-24 12:30:00 UTC → 2023-03-24 14:00:00 UTC (5 missing, split=discovery).

| prev open_time UTC | next open_time UTC | missing bars | split |
| --- | --- | --- | --- |
| 2017-09-06 16:00:00 UTC | 2017-09-06 23:00:00 UTC | 27 | warmup |
| 2017-12-18 12:15:00 UTC | 2017-12-18 13:30:00 UTC | 4 | warmup |
| 2018-01-04 03:00:00 UTC | 2018-01-04 05:00:00 UTC | 7 | warmup |
| 2018-02-08 00:15:00 UTC | 2018-02-09 09:45:00 UTC | 133 | warmup |
| 2018-02-10 05:45:00 UTC | 2018-02-10 06:15:00 UTC | 1 | warmup |
| 2018-02-11 04:00:00 UTC | 2018-02-11 04:30:00 UTC | 1 | warmup |
| 2018-06-26 01:45:00 UTC | 2018-06-26 12:00:00 UTC | 40 | warmup |
| 2018-06-27 12:45:00 UTC | 2018-06-27 14:45:00 UTC | 7 | warmup |
| 2018-07-04 00:15:00 UTC | 2018-07-04 08:00:00 UTC | 30 | warmup |
| 2018-10-19 05:45:00 UTC | 2018-10-19 09:30:00 UTC | 14 | warmup |
| 2018-11-14 01:45:00 UTC | 2018-11-14 09:00:00 UTC | 28 | warmup |
| 2019-03-12 01:45:00 UTC | 2019-03-12 08:00:00 UTC | 24 | warmup |
| 2019-05-15 02:45:00 UTC | 2019-05-15 13:00:00 UTC | 40 | warmup |
| 2019-06-07 21:00:00 UTC | 2019-06-07 22:15:00 UTC | 4 | warmup |
| 2019-08-15 01:45:00 UTC | 2019-08-15 10:00:00 UTC | 32 | warmup |
| 2019-11-13 01:45:00 UTC | 2019-11-13 04:15:00 UTC | 9 | warmup |
| 2019-11-25 01:45:00 UTC | 2019-11-25 04:00:00 UTC | 8 | warmup |
| 2020-02-09 01:45:00 UTC | 2020-02-09 03:00:00 UTC | 4 | discovery |
| 2020-02-19 11:30:00 UTC | 2020-02-19 17:30:00 UTC | 23 | discovery |
| 2020-03-04 09:15:00 UTC | 2020-03-04 11:30:00 UTC | 8 | discovery |
| 2020-04-25 01:45:00 UTC | 2020-04-25 04:30:00 UTC | 10 | discovery |
| 2020-06-28 01:45:00 UTC | 2020-06-28 05:30:00 UTC | 14 | discovery |
| 2020-11-30 05:45:00 UTC | 2020-11-30 07:00:00 UTC | 4 | discovery |
| 2020-12-21 14:00:00 UTC | 2020-12-21 18:00:00 UTC | 15 | discovery |
| 2020-12-25 01:45:00 UTC | 2020-12-25 03:00:00 UTC | 4 | discovery |
| 2021-02-11 03:30:00 UTC | 2021-02-11 05:00:00 UTC | 5 | discovery |
| 2021-03-06 01:45:00 UTC | 2021-03-06 03:30:00 UTC | 6 | discovery |
| 2021-04-20 01:45:00 UTC | 2021-04-20 04:30:00 UTC | 10 | discovery |
| 2021-04-25 04:00:00 UTC | 2021-04-25 08:45:00 UTC | 18 | discovery |
| 2021-08-13 01:45:00 UTC | 2021-08-13 06:30:00 UTC | 18 | discovery |
| 2021-09-29 06:45:00 UTC | 2021-09-29 09:00:00 UTC | 8 | discovery |
| 2023-03-24 12:30:00 UTC | 2023-03-24 14:00:00 UTC | 5 | discovery |

- Zero-volume bars: **61**.
- First zero-volume bar: 2017-08-19 23:30:00 UTC.
- Last zero-volume bar: 2023-03-24 12:30:00 UTC.
- Zero-volume timestamps shown below (20 of 61):
  - 2017-08-19 23:30:00 UTC
  - 2017-08-20 03:00:00 UTC
  - 2017-08-20 03:30:00 UTC
  - 2017-08-20 04:00:00 UTC
  - 2017-08-20 09:15:00 UTC
  - 2017-08-20 10:00:00 UTC
  - 2017-08-20 10:15:00 UTC
  - 2017-08-20 14:45:00 UTC
  - 2017-08-21 10:45:00 UTC
  - 2017-08-21 16:45:00 UTC
  - 2017-08-22 06:00:00 UTC
  - 2017-08-25 10:00:00 UTC
  - 2017-08-25 19:15:00 UTC
  - 2017-08-26 01:00:00 UTC
  - 2017-08-26 04:15:00 UTC
  - 2017-08-26 07:15:00 UTC
  - 2017-08-26 08:45:00 UTC
  - 2017-08-26 09:45:00 UTC
  - 2017-08-26 10:15:00 UTC
  - 2017-08-26 14:15:00 UTC
  - ... 41 additional zero-volume timestamps not expanded inline

- Other checks: duplicate open_time: 0; null cells: 0; zero/negative prices: 0; high < low: 0; open outside [low, high]: 0; close outside [low, high]: 0; taker_buy_base_vol > volume: 0; bar duration mismatch: 0; symbol mismatch: 0; interval mismatch: 0.

### 1h

- Missing-bar gaps: **28** gap events, **126** missing bars total.
- First gap: 2017-09-06 16:00:00 UTC → 2017-09-06 23:00:00 UTC (6 missing, split=warmup).
- Last gap: 2023-03-24 12:00:00 UTC → 2023-03-24 14:00:00 UTC (1 missing, split=discovery).

| prev open_time UTC | next open_time UTC | missing bars | split |
| --- | --- | --- | --- |
| 2017-09-06 16:00:00 UTC | 2017-09-06 23:00:00 UTC | 6 | warmup |
| 2018-01-04 03:00:00 UTC | 2018-01-04 05:00:00 UTC | 1 | warmup |
| 2018-02-08 00:00:00 UTC | 2018-02-09 09:00:00 UTC | 32 | warmup |
| 2018-06-26 01:00:00 UTC | 2018-06-26 12:00:00 UTC | 10 | warmup |
| 2018-06-27 12:00:00 UTC | 2018-06-27 14:00:00 UTC | 1 | warmup |
| 2018-07-04 00:00:00 UTC | 2018-07-04 08:00:00 UTC | 7 | warmup |
| 2018-10-19 05:00:00 UTC | 2018-10-19 09:00:00 UTC | 3 | warmup |
| 2018-11-14 01:00:00 UTC | 2018-11-14 09:00:00 UTC | 7 | warmup |
| 2019-03-12 01:00:00 UTC | 2019-03-12 08:00:00 UTC | 6 | warmup |
| 2019-05-15 02:00:00 UTC | 2019-05-15 13:00:00 UTC | 10 | warmup |
| 2019-08-15 01:00:00 UTC | 2019-08-15 10:00:00 UTC | 8 | warmup |
| 2019-11-13 01:00:00 UTC | 2019-11-13 04:00:00 UTC | 2 | warmup |
| 2019-11-25 01:00:00 UTC | 2019-11-25 04:00:00 UTC | 2 | warmup |
| 2020-02-09 01:00:00 UTC | 2020-02-09 03:00:00 UTC | 1 | discovery |
| 2020-02-19 11:00:00 UTC | 2020-02-19 17:00:00 UTC | 5 | discovery |
| 2020-03-04 09:00:00 UTC | 2020-03-04 11:00:00 UTC | 1 | discovery |
| 2020-04-25 01:00:00 UTC | 2020-04-25 04:00:00 UTC | 2 | discovery |
| 2020-06-28 01:00:00 UTC | 2020-06-28 05:00:00 UTC | 3 | discovery |
| 2020-11-30 05:00:00 UTC | 2020-11-30 07:00:00 UTC | 1 | discovery |
| 2020-12-21 14:00:00 UTC | 2020-12-21 18:00:00 UTC | 3 | discovery |
| 2020-12-25 01:00:00 UTC | 2020-12-25 03:00:00 UTC | 1 | discovery |
| 2021-02-11 03:00:00 UTC | 2021-02-11 05:00:00 UTC | 1 | discovery |
| 2021-03-06 01:00:00 UTC | 2021-03-06 03:00:00 UTC | 1 | discovery |
| 2021-04-20 01:00:00 UTC | 2021-04-20 04:00:00 UTC | 2 | discovery |
| 2021-04-25 04:00:00 UTC | 2021-04-25 08:00:00 UTC | 3 | discovery |
| 2021-08-13 01:00:00 UTC | 2021-08-13 06:00:00 UTC | 4 | discovery |
| 2021-09-29 06:00:00 UTC | 2021-09-29 09:00:00 UTC | 2 | discovery |
| 2023-03-24 12:00:00 UTC | 2023-03-24 14:00:00 UTC | 1 | discovery |

- Zero-volume bars: **5**.
- First zero-volume bar: 2017-09-06 16:00:00 UTC.
- Last zero-volume bar: 2023-03-24 12:00:00 UTC.
- Zero-volume timestamps shown below (5 of 5):
  - 2017-09-06 16:00:00 UTC
  - 2019-06-07 21:00:00 UTC
  - 2020-12-21 14:00:00 UTC
  - 2021-02-11 03:00:00 UTC
  - 2023-03-24 12:00:00 UTC

- Other checks: duplicate open_time: 0; null cells: 0; zero/negative prices: 0; high < low: 0; open outside [low, high]: 0; close outside [low, high]: 0; taker_buy_base_vol > volume: 0; bar duration mismatch: 0; symbol mismatch: 0; interval mismatch: 0.

### 4h

- Missing-bar gaps: **8** gap events, **16** missing bars total.
- First gap: 2018-02-08 00:00:00 UTC → 2018-02-09 08:00:00 UTC (7 missing, split=warmup).
- Last gap: 2020-02-19 08:00:00 UTC → 2020-02-19 16:00:00 UTC (1 missing, split=discovery).

| prev open_time UTC | next open_time UTC | missing bars | split |
| --- | --- | --- | --- |
| 2018-02-08 00:00:00 UTC | 2018-02-09 08:00:00 UTC | 7 | warmup |
| 2018-06-26 00:00:00 UTC | 2018-06-26 12:00:00 UTC | 2 | warmup |
| 2018-07-04 00:00:00 UTC | 2018-07-04 08:00:00 UTC | 1 | warmup |
| 2018-11-14 00:00:00 UTC | 2018-11-14 08:00:00 UTC | 1 | warmup |
| 2019-03-12 00:00:00 UTC | 2019-03-12 08:00:00 UTC | 1 | warmup |
| 2019-05-15 00:00:00 UTC | 2019-05-15 12:00:00 UTC | 2 | warmup |
| 2019-08-15 00:00:00 UTC | 2019-08-15 08:00:00 UTC | 1 | warmup |
| 2020-02-19 08:00:00 UTC | 2020-02-19 16:00:00 UTC | 1 | discovery |

- Zero-volume bars: **1**.
- First zero-volume bar: 2017-09-06 16:00:00 UTC.
- Last zero-volume bar: 2017-09-06 16:00:00 UTC.
- Zero-volume timestamps shown below (1 of 1):
  - 2017-09-06 16:00:00 UTC

- Other checks: duplicate open_time: 0; null cells: 0; zero/negative prices: 0; high < low: 0; open outside [low, high]: 0; close outside [low, high]: 0; taker_buy_base_vol > volume: 0; bar duration mismatch: 0; symbol mismatch: 0; interval mismatch: 0.

### 1d

- No anomalies detected under the requested checks.

## 3. Summary Statistics

| timeframe | total bars | date range | expected bars | actual bars | actual-expected | min low | max high | median daily volume | median daily num_trades | zero-volume % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15m | 300,479 | 2017-08-17 04:00:00 UTC → 2026-03-18 23:59:59 UTC | 301,040 | 300,479 | -561 | 2,817.00 | 126,199.63 | 38,909.22142 | 1,162,109 | 0.0203% |
| 1h | 75,134 | 2017-08-17 04:00:00 UTC → 2026-03-18 23:59:59 UTC | 75,260 | 75,134 | -126 | 2,817.00 | 126,199.63 | 38,909.22142 | 1,162,109 | 0.0067% |
| 4h | 18,799 | 2017-08-17 04:00:00 UTC → 2026-03-18 23:59:59 UTC | 18,815 | 18,799 | -16 | 2,817.00 | 126,199.63 | 38,909.22142 | 1,162,109 | 0.0053% |
| 1d | 3,136 | 2017-08-17 00:00:00 UTC → 2026-03-18 23:59:59 UTC | 3,136 | 3,136 | 0 | 2,817.00 | 126,199.63 | 38,909.22142 | 1,162,109 | 0.0000% |

Notes:
- `expected bars` is computed from the first observed `open_time` to the last observed `open_time`, inclusive, on the native timeframe grid.
- `actual-expected` is negative exactly where gaps exist; no bar repair was applied.
- Daily medians are computed after aggregating each timeframe to UTC calendar-day totals.

## 4. Split Coverage

Constitution split boundaries applied:

- `warmup`: first available bar → 2019-12-31
- `discovery`: 2020-01-01 → 2023-06-30
- `holdout`: 2023-07-01 → 2024-09-30
- `reserve_internal`: 2024-10-01 → snapshot end

| timeframe | warmup bars | discovery bars | holdout bars | reserve_internal bars | unassigned |
| --- | --- | --- | --- | --- | --- |
| 15m | 82,807 | 122,440 | 43,968 | 51,264 | 0 |
| 1h | 20,709 | 30,617 | 10,992 | 12,816 | 0 |
| 4h | 5,186 | 7,661 | 2,748 | 3,204 | 0 |
| 1d | 867 | 1,277 | 458 | 534 | 0 |

Split check result: all bars were assigned to exactly one constitution split (`unassigned = 0` for every timeframe).

## 5. Data Quality Verdict

**PASS (data usable)**

Rationale:
- Schema integrity passed for all four files.
- No nulls, no duplicate `open_time`, no impossible price geometry, no `taker_buy_base_vol > volume`, and no timestamp-duration mismatch were found.
- Blocking issue threshold was not met; anomalies are limited to observed open-time gaps and sparse zero-volume bars.
- Caveat: intraday continuity is imperfect in `15m`, `1h`, and `4h` (including one `4h` discovery gap on 2020-02-19). Any later feature engineering or backtesting must respect the raw gaps and must not synthesize missing bars.
- Additional caveat: this historical snapshot remains candidate-mining-only and cannot support a clean external OOS claim.
