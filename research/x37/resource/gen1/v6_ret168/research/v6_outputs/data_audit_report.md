# Data audit report

## Coverage
- H4 rows: 18,791; open_time 2017-08-17 04:00:00+00:00 to 2026-03-17 12:00:00+00:00 UTC.
- D1 rows: 3,134; open_time 2017-08-17 00:00:00+00:00 to 2026-03-16 00:00:00+00:00 UTC.

## Integrity checks on raw supplied columns
- H4 duplicates: open_time=0, close_time=1.
- D1 duplicates: open_time=0, close_time=0.
- Missing values on raw supplied columns: H4=0, D1=0.
- D1 irregular gaps: 0.
- D1 nonstandard durations: 0.
- H4 irregular gaps: 8.
- H4 nonstandard durations: 19.
- Zero-volume or zero-trade rows: D1=0, H4=1.

## Interpretation
The raw feed is usable under the V6 execution assumptions. The only material raw-structure issues are a small number of H4 shortened bars, 8 H4 open-time gaps, and one H4 duplicate close_time caused by a zero-duration zero-activity row on 2017-09-06 16:00 UTC. Those rows were retained exactly as supplied and logged explicitly rather than silently repaired. Native D1 and day-aggregated H4 OHLC reconcile exactly across overlapping dates; volume differences are only floating-point noise.

## Files
See:
- `tables/audit_summary.csv`
- `tables/audit_h4_irregular_gaps.csv`
- `tables/audit_h4_nonstandard_durations.csv`
- `tables/audit_d1_h4_reconciliation_summary.csv`
