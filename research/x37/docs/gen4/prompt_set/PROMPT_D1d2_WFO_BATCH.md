# PROMPT D1d2 - Walk-Forward Batch Execution (Use this after D1d1 in the same chat)

You have completed D1d1. All candidate strategies are implemented, saved to `d1d_impl_{candidate_id}.py` files, and smoke-tested.

**Guard**: If any `d1d_impl_{candidate_id}.py` file is missing (e.g., due to context loss), reload them from disk before proceeding.

Your job in this turn is **only** to run the full walk-forward evaluation across all configs and folds, and save per-fold results.
Do **not** compute aggregate metrics — that is D1d3.
Do **not** use holdout or reserve_internal data.
Do **not** select a champion or challenger.

## Walk-forward specification

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

## Cost model
Run each config at **two cost levels**:
- 20 bps round-trip (10 bps per side)
- 50 bps round-trip (25 bps per side)

## What to do

### 1. Run walk-forward for each config
For each config in `d1c_config_matrix.csv`:
- For each of the 14 folds:
  - Initialize strategy with training data (for indicator warmup)
  - Run on test period
  - Record metrics at both cost levels

### 1b. Run walk-forward for ablation variants (governance patch v4.0.1)

If D1d1 created ablation variant files (`d1d_impl_{candidate_id}_no_{layer_name}.py`),
run each ablation variant through the same 14 folds at **50 bps only** (single cost level
is sufficient for ablation diagnostics). Use the parent candidate's first config parameters.

Record the same per-fold metrics and daily returns as main configs. Use the ablation
variant filename (e.g., `H4Trend_H1Flow_no_flow1h`) as the config_id in both CSV files.

If no ablation variants exist, skip this step.

### 2. Record per-fold metrics
For each config × fold × cost level, record:
- CAGR (annualized)
- Sharpe ratio (annualized, daily returns)
- Max drawdown (as fraction, e.g. 0.35 = 35%)
- Number of entries
- Number of exits
- Final position state (`flat` or `long` at fold end)
- Exposure (fraction of time in position)
- Mean daily return

### 3. Record daily returns
For each config × cost level, record the **daily return series** across all folds (one row per trading day). This is essential for D1d3 to compute true full-period aggregate metrics (CAGR, MDD, Sharpe) that cannot be recovered from per-fold summaries alone (MDD can span fold boundaries; CAGR requires chained equity; Sharpe requires full daily series).

### 4. Save results
Save two files:

**`d1d_wfo_results.csv`** — per-fold summary metrics, with columns:
- config_id, mechanism_type, candidate_id, fold, cost_bps_rt, cagr, sharpe, max_drawdown, entries, exit_count, final_position_state, exposure, mean_daily_return

**`d1d_wfo_daily_returns.csv`** — daily return series, with columns:
- config_id, candidate_id, cost_bps_rt, date, daily_return

This file concatenates daily returns across all 14 folds for each config. Days outside test periods (warmup, training-only) are excluded. The date column is ISO 8601 (YYYY-MM-DD).

## Handling execution limits

If you approach execution time limits:
1. Save all results computed so far to `d1d_wfo_results.csv` and `d1d_wfo_daily_returns.csv`.
2. Report which configs/folds are completed and which remain.
3. State clearly: "D1d2 PARTIAL — N of M config×fold combinations completed. Continue with the next prompt re-send."
4. The user will re-send this same prompt to continue from where you stopped.

When resuming after PARTIAL:
- Reload `d1d_wfo_results.csv` to see which config×fold×cost rows already exist.
- Reload `d1d_wfo_daily_returns.csv` to see which config×cost dates already exist.
- Skip completed combinations.
- Append new results to both CSVs.

## Required output sections
1. `Execution Progress` — how many configs × folds × costs completed (e.g., "840 of 1,680")
2. `Files Saved` — confirm `d1d_wfo_results.csv` and `d1d_wfo_daily_returns.csv` saved with row counts

## What not to do
- Do not compute aggregate metrics (mean/median across folds). That is D1d3.
- Do not use holdout data (2023-07-01 → 2024-09-30).
- Do not use reserve_internal data (2024-10-01 → snapshot end).
- Do not rank, filter, or select candidates — that is D1e's job.
- Do not freeze any candidate.
- Do not modify the constitution.
