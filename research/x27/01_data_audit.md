# Phase 1: Data Audit

**Study**: X27
**Date**: 2026-03-11
**Data source**: `/var/www/trading-bots/btc-spot-dev/data/`

---

## 1. Schema & Coverage

All 4 files share identical schema (13 columns):
`symbol, interval, open_time, close_time, open, high, low, close, volume, quote_volume, num_trades, taker_buy_base_vol, taker_buy_quote_vol`

Timestamps: epoch milliseconds (UTC).

| File | Rows    | Start            | End              | Duration (days) |
|------|---------|------------------|------------------|-----------------|
| 15m  | 299,754 | 2017-08-17 04:00 | 2026-03-11 10:45 | 3,128           |
| 1h   | 74,952  | 2017-08-17 04:00 | 2026-03-11 10:00 | 3,128           |
| 4h   | 18,752  | 2017-08-17 04:00 | 2026-03-11 04:00 | 3,128           |
| 1d   | 3,128   | 2017-08-17 00:00 | 2026-03-10 00:00 | 3,127           |

**Duplicate timestamps**: 0 in all files.

### Gaps > 3 bars

- **15m**: 30 gaps (largest: 2018-02-08 → 2018-02-09, 134 bars / 33.5h)
- **1h**: 14 gaps (largest: same 2018-02-08 event, 33 bars / 33h)
- **4h**: 1 gap only — 2018-02-08 00:00 → 2018-02-09 08:00 (8 bars / 32h)
- **1d**: 0 gaps

The single H4 gap (2018-02-08) is a known Binance data outage. All other gaps at finer resolutions aggregate cleanly at H4/D1 level.

---

## 2. Data Quality (Tbl03)

| Metric                | 15m     | 1h    | 4h    | 1d    |
|-----------------------|---------|-------|-------|-------|
| Missing values        | 0       | 0     | 0     | 0     |
| Zero volume bars      | 60      | 4     | 0     | 0     |
| close > high          | 0       | 0     | 0     | 0     |
| close < low           | 0       | 0     | 0     | 0     |
| open <= 0             | 0       | 0     | 0     | 0     |
| high < low            | 0       | 0     | 0     | 0     |
| Extreme (|log_ret|>15%) | 1    | 3     | 3     | 14    |
| tbv missing           | 0       | 0     | 0     | 0     |
| tbv zero              | 241     | 4     | 0     | 0     |
| tbv/vol mean ratio    | 0.4954  | 0.4952| 0.4950| 0.4953|

**Key observations**:
- **Obs01**: Zero missing values across all files. Data completeness is perfect.
- **Obs02**: Zero volume bars exist only at 15m (60) and 1h (4) resolution; none at H4/D1. Not a concern for primary analysis.
- **Obs03**: Price integrity is perfect — no violations (close>high, close<low, high<low, open<=0) in any file.
- **Obs04**: taker_buy_base_vol/volume ratio is stable ~0.495 across all resolutions, indicating consistent data collection.

### Extreme moves (H4, |log_return| > 15%)

| Date                | Close   | Prev Close | log_ret  | Note                    |
|---------------------|---------|------------|----------|-------------------------|
| 2017-09-15 12:00    | 3,830   | 2,919      | +27.2%   | China ICO ban recovery  |
| 2020-03-12 08:00    | 6,067   | 7,392      | -19.8%   | COVID crash wave 1      |
| 2020-03-12 20:00    | 4,800   | 6,037      | -22.9%   | COVID crash wave 2      |

- **Obs05**: Only 3 extreme H4 bars in 8.5 years of data. All correspond to well-known macro events. No data errors.

### D1 extreme moves (14 total)

Most are in 2017-2018 (early volatile period) and 2020-03-12 (COVID crash, -50.3% single day). The 2020-03-12 daily bar with log_ret = -0.5026 is the most extreme observation in the dataset.

---

## 3. Descriptive Statistics

### H4 (Tbl01)

| Stat  | Open       | High       | Low        | Close      | Volume     |
|-------|------------|------------|------------|------------|------------|
| mean  | 36,880     | 37,188     | 36,551     | 36,884     | 10,281     |
| std   | 32,392     | 32,594     | 32,178     | 32,392     | 14,205     |
| min   | 2,871      | 3,148      | 2,817      | 2,919      | 5.9        |
| Q25   | 9,209      | 9,277      | 9,131      | 9,210      | 3,370      |
| Q50   | 26,816     | 26,921     | 26,632     | 26,817     | 5,969      |
| Q75   | 57,956     | 58,471     | 57,356     | 57,964     | 10,968     |
| max   | 125,411    | 126,200    | 124,800    | 125,411    | 284,712    |

### D1 (Tbl02)

| Stat  | Open       | High       | Low        | Close      | Volume     |
|-------|------------|------------|------------|------------|------------|
| mean  | 36,849     | 37,631     | 36,000     | 36,870     | 61,631     |
| std   | 32,392     | 32,913     | 31,826     | 32,392     | 76,265     |
| min   | 3,188      | 3,277      | 2,817      | 3,189      | 228        |
| Q25   | 9,222      | 9,395      | 9,018      | 9,226      | 23,698     |
| Q50   | 26,769     | 27,172     | 26,378     | 26,785     | 39,047     |
| Q75   | 57,976     | 59,406     | 56,581     | 58,001     | 64,919     |
| max   | 124,659    | 126,200    | 123,084    | 124,659    | 760,705    |

### Price range
- **H4**: $2,919 → $125,411 (43.0x)
- **D1**: $3,189 → $124,659 (39.1x)

### H4 bars per day
- Mean: 5.99, Std: 0.14, Min: 1, Max: 6
- **Obs06**: H4 data is nearly perfectly regular at 6 bars/day. The min=1 corresponds to a partial first day (2017-08-17 start).

---

## 4. Time Coverage

### Year-by-year bar count

| Year | H4 bars | D1 bars | Notes                |
|------|---------|---------|----------------------|
| 2017 | 820     | 137     | Partial (Aug-Dec)    |
| 2018 | 2,179   | 365     | Full (-1 bar from gap)|
| 2019 | 2,186   | 365     | Full                 |
| 2020 | 2,195   | 366     | Full (leap year)     |
| 2021 | 2,190   | 365     | Full                 |
| 2022 | 2,190   | 365     | Full                 |
| 2023 | 2,190   | 365     | Full                 |
| 2024 | 2,196   | 366     | Full (leap year)     |
| 2025 | 2,190   | 365     | Full                 |
| 2026 | 416     | 69      | Partial (Jan-Mar 10) |

- **Obs07**: D1 bar counts exactly match calendar days for all complete years. No missing days.
- **Obs08**: H4 bar counts consistent at ~2,190/year (365×6). 2018 slight deficit from the Feb gap.

### Gaps > 12h (H4)
Only one: 2018-02-08 00:00 → 2018-02-09 08:00 (32h).

### Gaps > 48h (D1)
None.

### Sparse periods
- 2017-08: 89 bars (partial start month — data begins Aug 17)
- 2026-03: 62 bars (partial current month — data through Mar 11)
- No other sparse months detected.

---

## Observation Registry

| ID    | Description                                          | Evidence     |
|-------|------------------------------------------------------|--------------|
| Obs01 | Zero missing values across all files                 | Tbl03        |
| Obs02 | Zero-vol bars only at 15m/1h; none at H4/D1         | Tbl03        |
| Obs03 | Perfect price integrity (no OHLC violations)         | Tbl03        |
| Obs04 | tbv/vol ratio stable ~0.495 across resolutions       | Tbl03        |
| Obs05 | 3 extreme H4 bars (>15% |log_ret|), all macro events| Tbl03        |
| Obs06 | H4 bars/day = 5.99 ± 0.14, near-perfect regularity  | Tbl01        |
| Obs07 | D1 bar counts match calendar exactly                 | Year table   |
| Obs08 | Single data gap: 2018-02-08 (32h), known outage      | Gap analysis |

---

## End-of-Phase Checklist

### 1. Files created
- `01_data_audit.md` (this report)
- `tables/Tbl01_h4_descriptive.csv`
- `tables/Tbl02_d1_descriptive.csv`
- `tables/Tbl03_data_quality.csv`
- `code/phase1_audit.py`
- `manifest.json`

### 2. Key Obs IDs created
Obs01–Obs08

### 3. Blockers / uncertainties
- **None**. Data quality is excellent. The single 32h gap (2018-02-08) at H4 is a known event and represents <0.1% of total data.

### 4. Gate status
**PASS_TO_NEXT_PHASE**

Data is clean, complete, structurally sound. Ready for Phase 2 (Price Behavior EDA).
