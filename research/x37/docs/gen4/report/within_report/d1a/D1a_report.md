# D1a Quality Report

## 1. Schema Validation

| File | Result | Notes |
|---|---|---|
| `spot_btcusdt_15m.csv` | **PASS** | Exact 13-column canonical schema already present; no trailing column drop; no symbol/interval injection; timestamps parseable; spacing is a multiple of 15m |
| `spot_btcusdt_1h.csv` | **PASS** | Exact 13-column canonical schema already present; no trailing column drop; no symbol/interval injection; timestamps parseable; spacing is a multiple of 1h |
| `spot_btcusdt_4h.csv` | **PASS** | Exact 13-column canonical schema already present; no trailing column drop; no symbol/interval injection; timestamps parseable; spacing is a multiple of 4h |
| `spot_btcusdt_1d.csv` | **PASS** | Exact 13-column canonical schema already present; no trailing column drop; no symbol/interval injection; timestamps parseable; spacing is a multiple of 1d |

**Canonical order confirmed for all files:**

`symbol, interval, open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol`

## 2. Anomaly Log

- **15m:** 32 gap segments, 561 missing bars out of 301,040 expected (0.186354%). Largest gap: 2018-02-08 00:15 → 2018-02-09 09:45 UTC (133 bars). 61 zero-volume bars.
- **1h:** 28 gap segments, 126 missing bars out of 75,260 expected (0.167420%). Largest gap: 2018-02-08 00:00 → 2018-02-09 09:00 UTC (32 bars). 5 zero-volume bars.
- **4h:** 8 gap segments, 16 missing bars out of 18,815 expected (0.085039%). Largest gap: 2018-02-08 00:00 → 2018-02-09 08:00 UTC (7 bars). 1 zero-volume bar.
- **1d:** none.

Across all four files, the following were **not** found:

- duplicate `open_time`
- NaN/null values
- zero or negative OHLC prices
- `high < low`
- `open` or `close` outside `[low, high]`
- `taker_buy_base_vol > volume`
- `close_time` mismatch against `open_time + interval - 1`
- timeframe-label mismatch

No synthetic repair was performed. No gaps were filled. No rows were modified.

## 3. Summary Statistics

| Timeframe | Total bars | Date range | Expected vs actual | Missing | Price range | Median daily volume | Median daily num_trades | Zero-volume % |
|---|---|---|---|---|---|---|---|---|
| 15m | 300,479 | 2017-08-17 04:00:00 → 2026-03-18 23:59:59.999 UTC | 301,040 vs 300,479 | 561 | 2,817.00 → 126,199.63 | 38,909.221420 | 1,162,109 | 0.020301% |
| 1h | 75,134 | 2017-08-17 04:00:00 → 2026-03-18 23:59:59.999 UTC | 75,260 vs 75,134 | 126 | 2,817.00 → 126,199.63 | 38,909.221420 | 1,162,109 | 0.006655% |
| 4h | 18,799 | 2017-08-17 04:00:00 → 2026-03-18 23:59:59.999 UTC | 18,815 vs 18,799 | 16 | 2,817.00 → 126,199.63 | 38,909.221420 | 1,162,109 | 0.005319% |
| 1d | 3,136 | 2017-08-17 00:00:00 → 2026-03-18 23:59:59.999 UTC | 3,136 vs 3,136 | 0 | 2,817.00 → 126,199.63 | 38,909.221420 | 1,162,109 | 0.000000% |

## 4. Split Coverage

Counts are by `open_time` using constitution-defined UTC splits.

| Timeframe | Warmup | Discovery | Holdout | Reserve internal |
|---|---|---|---|---|
| 15m | 82,807 / 83,216 expected (missing 409) | 122,440 / 122,592 expected (missing 152) | 43,968 / 43,968 expected (missing 0) | 51,264 / 51,264 expected (missing 0) |
| 1h | 20,709 / 20,804 expected (missing 95) | 30,617 / 30,648 expected (missing 31) | 10,992 / 10,992 expected (missing 0) | 12,816 / 12,816 expected (missing 0) |
| 4h | 5,186 / 5,201 expected (missing 15) | 7,661 / 7,662 expected (missing 1) | 2,748 / 2,748 expected (missing 0) | 3,204 / 3,204 expected (missing 0) |
| 1d | 867 / 867 expected (missing 0) | 1,277 / 1,277 expected (missing 0) | 458 / 458 expected (missing 0) | 534 / 534 expected (missing 0) |

**Key observation:** all missing bars are confined to warmup/discovery. Holdout and reserve_internal are complete in all four timeframes.

## 5. Data Quality Verdict

### ✅ PASS

**Reason:**

- schema validation passed for all files
- timestamp and timeframe consistency passed
- missing-bar rates are far below the 5% blocking threshold in every timeframe
- no systemic corruption detected
- anomalies are non-blocking and isolated

**Constraint reminder:** this historical snapshot remains candidate-mining-only. No clean external OOS claim may be made from it.
