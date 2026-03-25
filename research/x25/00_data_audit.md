# Data Audit — Phase 1

## Schema

Rows: 96,423
Columns: 13

| Column | dtype | nulls | unique |
|--------|-------|-------|--------|
| symbol | str | 0 | 1 |
| interval | str | 0 | 3 |
| open_time | int64 | 0 | 74652 |
| close_time | int64 | 0 | 74651 |
| open | float64 | 0 | 72803 |
| high | float64 | 0 | 66726 |
| low | float64 | 0 | 67363 |
| close | float64 | 0 | 72627 |
| volume | float64 | 0 | 96267 |
| quote_volume | float64 | 0 | 96269 |
| num_trades | int64 | 0 | 74993 |
| taker_buy_base_vol | float64 | 0 | 96259 |
| taker_buy_quote_vol | float64 | 0 | 96269 |

## Interval counts

- 1d: 3,110
- 1h: 74,651
- 4h: 18,662

## Interval: 4h

Rows: 18,662
Time range: 2017-08-17 04:00:00 → 2026-02-21 08:00:00

open_time monotonic increasing: True
close_time monotonic increasing: True
Duplicate open_time: 0
Fully duplicate rows: 0
Expected gap: 4h
Correct gaps: 18,661  |  Anomalous gaps: 0

close_time = open_time + interval - 1ms: OK=18,642, BAD=20

volume: negative=0, zero=17, min=0.000000, max=284711.69, median=5992.40
taker_buy_base_vol: negative=0, zero=17, min=0.000000, max=141232.70, median=2997.07

taker_buy_ratio: min=0.0854, max=0.9240, mean=0.4950, median=0.4961
  >1.0: 0,  <0.0: 0

H4 bars per calendar day: 6 bars=3,109, !=6 bars=2
  First 5 non-6 days: [(datetime.date(2017, 8, 17), 5), (datetime.date(2026, 2, 21), 3)]

## Interval: 1d

Rows: 3,110
Time range: 2017-08-17 00:00:00 → 2026-02-20 00:00:00

open_time monotonic increasing: True
close_time monotonic increasing: True
Duplicate open_time: 0
Fully duplicate rows: 0
Expected gap: 24h
Correct gaps: 3,109  |  Anomalous gaps: 0

close_time = open_time + interval - 1ms: OK=3,110, BAD=0

volume: negative=0, zero=0, min=228.108068, max=760705.36, median=39147.93
taker_buy_base_vol: negative=0, zero=0, min=56.190141, max=374775.57, median=19559.34

taker_buy_ratio: min=0.1745, max=0.8108, mean=0.4953, median=0.4958
  >1.0: 0,  <0.0: 0
