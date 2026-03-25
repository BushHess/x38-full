# PROMPT D1d - Walk-Forward Evaluation (DEPRECATED — use D1d1–D1d3)

> **Note**: This monolithic prompt has been split into 3 sub-prompts for better per-turn execution:
> - `PROMPT_D1d1_IMPLEMENT.md` — implement candidate strategies + smoke test
> - `PROMPT_D1d2_WFO_BATCH.md` — run full walk-forward batch (all configs × folds × costs)
> - `PROMPT_D1d3_WFO_AGGREGATE.md` — aggregate metrics + summary
>
> Use the split version. This file is retained for reference only.

You have completed D1c. Candidate designs and the config matrix are ready.

Your job in this turn is **only** to execute the walk-forward evaluation on the discovery period.
Do **not** use holdout or reserve_internal data.
Do **not** select a champion or challenger.
Do **not** freeze any candidate.

## Constitution walk-forward specification

Type: quarterly expanding (anchored start, expanding training window).

**14 test folds on discovery period (2020-01-01 → 2023-06-30):**

| Fold | Train end (exclusive) | Test start | Test end |
|------|----------------------|------------|----------|
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

Training data for each fold: warmup start → train_end_exclusive.
Test data for each fold: test_start → test_end.

## Execution semantics
- Signal generated at bar close → fill at next bar open (next-open execution).
- UTC alignment for all timestamps.
- No lookahead: the strategy at bar t may only use data up to and including bar t.
- Position sizing: 0% or 100% notional (binary).
- Warmup period data (→ 2019-12-31) is available for indicator initialization but no trades allowed.

## Cost model
Run each config at **two cost levels**:
- 20 bps round-trip (10 bps per side)
- 50 bps round-trip (25 bps per side)

Apply cost at each entry and exit event.

## What to do

### 1. Implement each candidate strategy
Using the exact signal logic from `d1c_candidate_designs.md` and configs from `d1c_config_matrix.csv`, implement each candidate as executable code.

**Performance note**: Prefer vectorized signal generation (e.g., pandas boolean columns and rolling computations) over bar-by-bar loops for speed. If the 15m CSV is too large, consider that many swing-horizon mechanisms primarily use D1 or H4 — but this is not a constraint. Use whatever timeframes D1b measurement supports.

### 2. Run walk-forward for each config
For each config in `d1c_config_matrix.csv`:
- For each of the 14 folds:
  - Initialize strategy with training data (for indicator warmup)
  - Run on test period
  - Record metrics at both cost levels

### 3. Record per-fold metrics
For each config × fold × cost level, record:
- CAGR (annualized)
- Sharpe ratio (annualized, daily returns)
- Max drawdown (as fraction, e.g. 0.35 = 35%)
- Number of entries
- Exposure (fraction of time in position)
- Mean daily return

### 4. Compute aggregate metrics
For each config × cost level, compute across all 14 folds:
- Mean and median of per-fold Sharpe
- Aggregate CAGR over full discovery period
- Aggregate max drawdown over full discovery period
- Total entries over full discovery period
- Average exposure

### 5. Save results
Save to file `d1d_wfo_results.csv` with columns:
- config_id, mechanism_type, candidate_id, fold, cost_bps_rt, cagr, sharpe, max_drawdown, entries, exposure, mean_daily_return

Save aggregate results to `d1d_wfo_aggregate.csv` with columns:
- config_id, mechanism_type, candidate_id, cost_bps_rt, agg_cagr, agg_sharpe, agg_mdd, total_entries, avg_exposure, mean_fold_sharpe, median_fold_sharpe

## Handling execution limits

If you approach execution time limits:
1. Save all results computed so far to the CSV files.
2. Report which configs/folds are completed and which remain.
3. State clearly: "D1d PARTIAL — N of M configs completed. Continue with the next prompt to finish remaining configs."
4. The user will re-send this same prompt to continue from where you stopped.

## Required output sections
1. `Implementation Notes` — any implementation decisions made
2. `Execution Progress` — how many configs × folds completed
3. `WFO Results Summary` — top 10 configs by aggregate Calmar_50bps
4. `Files Saved` — list of output files

## What not to do
- Do not use holdout data (2023-07-01 → 2024-09-30).
- Do not use reserve_internal data (2024-10-01 → snapshot end).
- Do not rank, filter, or select candidates — that is D1e's job.
- Do not freeze any candidate.
- Do not modify the constitution.
