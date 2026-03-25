# Phase 1 — Canonical Window Autopsy

## All Windows

| Window | Test Period | Valid | Low-trade | Delta Score | Delta Sharpe | Delta CAGR | Delta MDD | Tag |
|---:|---|---|---|---:|---:|---:|---:|---|
| 0 | 2022-01-01 -> 2022-06-30 | True | False | 27.6620 | 0.5654 | 10.74 | -1.52 | positive_window |
| 1 | 2022-07-01 -> 2022-12-31 | True | False | -20.7880 | -0.5824 | -6.92 | 5.48 | candidate_worse_return_and_worse_drawdown |
| 2 | 2023-01-01 -> 2023-06-30 | True | False | -4.9226 | -0.0357 | -1.62 | 0.87 | candidate_worse_return_and_worse_drawdown |
| 3 | 2023-07-01 -> 2023-12-31 | True | False | 30.0936 | 0.2422 | 11.18 | -0.51 | positive_window |
| 4 | 2024-01-01 -> 2024-06-30 | True | False | 54.8324 | 0.4213 | 18.66 | -5.75 | positive_window |
| 5 | 2024-07-01 -> 2024-12-31 | True | False | 14.6290 | 0.1010 | 4.83 | -2.91 | positive_window |
| 6 | 2025-01-01 -> 2025-06-30 | True | False | -13.1920 | -0.1685 | -5.05 | -2.08 | candidate_drawdown_better_but_return_weaker |
| 7 | 2025-07-01 -> 2025-12-31 | True | False | 11.3360 | 0.2499 | 4.10 | -1.81 | positive_window |

## Summary

- Valid windows: `8/8`
- Power windows: `8`
- Low-trade windows: `0`
- Low-power delegation active: `False`
- Wilcoxon p (power-only): `0.125`
- Bootstrap CI (power-only): `[-3.4378, 29.279]`

## Reproduction Check

| Branch window | Source window | Test period | Source delta | Branch delta | Abs diff | Branch valid | Branch low-trade |
|---:|---:|---|---:|---:|---:|---|---|
| 0 | 0 | 2022-01-01 -> 2022-06-30 | 27.6620 | 27.6620 | 0.000000 | True | False |
| 1 | 1 | 2022-07-01 -> 2022-12-31 | -20.7880 | -20.7880 | 0.000000 | True | False |
| 2 | 2 | 2023-01-01 -> 2023-06-30 | -4.9226 | -4.9226 | 0.000000 | True | False |
| 3 | 3 | 2023-07-01 -> 2023-12-31 | 30.0936 | 30.0936 | 0.000000 | True | False |
| 4 | 4 | 2024-01-01 -> 2024-06-30 | 54.8324 | 54.8324 | 0.000000 | True | False |
| 5 | 5 | 2024-07-01 -> 2024-12-31 | 14.6290 | 14.6290 | 0.000000 | True | False |
| 6 | 6 | 2025-01-01 -> 2025-06-30 | -13.1920 | -13.1920 | 0.000000 | True | False |
| 7 | 7 | 2025-07-01 -> 2025-12-31 | 11.3360 | 11.3360 | 0.000000 | True | False |

## Failed Windows

### Window 1 — 2022-07-01 -> 2022-12-31

- Failure tag: `candidate_worse_return_and_worse_drawdown`
- Delta score: `-20.7880`
- Candidate vs baseline Sharpe: `-1.8526` vs `-1.2702`
- Candidate vs baseline CAGR: `-42.74` vs `-35.82`
- Candidate vs baseline MDD: `33.23` vs `27.75`
- Candidate trade profile: `{'count': 14, 'win_rate_pct': 28.57, 'avg_return_pct': -1.9513, 'median_return_pct': -1.8559, 'avg_days_held': 3.5595, 'median_days_held': 3.4167, 'max_return_pct': 2.1877, 'min_return_pct': -6.8134, 'long_hold_count_gt30bars': 3, 'profit_share_long_holds_pct': 58.86}`
- Baseline trade profile: `{'count': 16, 'win_rate_pct': 25.0, 'avg_return_pct': -1.3333, 'median_return_pct': -1.3958, 'avg_days_held': 3.3021, 'median_days_held': 2.8333, 'max_return_pct': 7.0025, 'min_return_pct': -6.9818, 'long_hold_count_gt30bars': 5, 'profit_share_long_holds_pct': 74.23}`

### Window 2 — 2023-01-01 -> 2023-06-30

- Failure tag: `candidate_worse_return_and_worse_drawdown`
- Delta score: `-4.9226`
- Candidate vs baseline Sharpe: `0.5953` vs `0.6310`
- Candidate vs baseline CAGR: `16.11` vs `17.73`
- Candidate vs baseline MDD: `32.28` vs `31.41`
- Candidate trade profile: `{'count': 17, 'win_rate_pct': 29.41, 'avg_return_pct': 0.8162, 'median_return_pct': -2.7918, 'avg_days_held': 5.3039, 'median_days_held': 4.0, 'max_return_pct': 32.3648, 'min_return_pct': -6.3575, 'long_hold_count_gt30bars': 6, 'profit_share_long_holds_pct': 100.0}`
- Baseline trade profile: `{'count': 16, 'win_rate_pct': 31.25, 'avg_return_pct': 0.8741, 'median_return_pct': -3.0189, 'avg_days_held': 5.75, 'median_days_held': 4.0833, 'max_return_pct': 32.3648, 'min_return_pct': -5.6694, 'long_hold_count_gt30bars': 5, 'profit_share_long_holds_pct': 100.0}`

### Window 6 — 2025-01-01 -> 2025-06-30

- Failure tag: `candidate_drawdown_better_but_return_weaker`
- Delta score: `-13.1920`
- Candidate vs baseline Sharpe: `0.5271` vs `0.6956`
- Candidate vs baseline CAGR: `10.91` vs `15.96`
- Candidate vs baseline MDD: `13.76` vs `15.84`
- Candidate trade profile: `{'count': 13, 'win_rate_pct': 38.46, 'avg_return_pct': 0.5483, 'median_return_pct': -0.6024, 'avg_days_held': 5.4615, 'median_days_held': 4.0, 'max_return_pct': 10.4616, 'min_return_pct': -4.6062, 'long_hold_count_gt30bars': 4, 'profit_share_long_holds_pct': 81.53}`
- Baseline trade profile: `{'count': 11, 'win_rate_pct': 36.36, 'avg_return_pct': 0.8879, 'median_return_pct': -1.1185, 'avg_days_held': 6.697, 'median_days_held': 4.0, 'max_return_pct': 12.658, 'min_return_pct': -4.6062, 'long_hold_count_gt30bars': 4, 'profit_share_long_holds_pct': 97.39}`

