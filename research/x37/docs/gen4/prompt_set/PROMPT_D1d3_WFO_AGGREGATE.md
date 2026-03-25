# PROMPT D1d3 - Walk-Forward Aggregate & Summary (Use this after D1d2 in the same chat)

You have completed D1d2. Results are saved in `d1d_wfo_results.csv` (per-fold summaries) and `d1d_wfo_daily_returns.csv` (daily return series).

**Guard**: If D1d2 reported PARTIAL, stop here and report: "D1d2 incomplete — re-send D1d2 to finish remaining configs before aggregating." Do not continue.

Your job in this turn is **only** to compute aggregate metrics and produce the WFO summary.
Do **not** use holdout or reserve_internal data.
Do **not** select a champion or challenger.

## What to do

### 1. Load results
Load both files:
- `d1d_wfo_results.csv` — verify all expected config×fold×cost rows are present.
- `d1d_wfo_daily_returns.csv` — verify daily returns cover the full discovery period for each config×cost.

### 2. Compute aggregate metrics
For each config × cost level:

**From `d1d_wfo_daily_returns.csv`** (true full-period metrics):
- **Aggregate CAGR**: chain daily returns across all folds to compute true full-period compound return, then annualize.
- **Aggregate max drawdown**: build the full equity curve from daily returns, compute the maximum peak-to-trough drawdown. This correctly captures drawdowns that span fold boundaries.
- **Aggregate Sharpe**: compute mean and std of daily returns across the full discovery period, annualize.

**From `d1d_wfo_results.csv`** (per-fold diagnostics):
- Mean and median of per-fold Sharpe
- Total entries over full discovery period (sum across folds)
- Average exposure (weighted average across folds by fold duration)

### 2b. Ablation validation (multi-layer candidates only) — governance patch v4.0.1

For each multi-layer candidate, compare the **full candidate's aggregate metrics**
(first config, 50 bps) against each ablated variant's aggregate metrics:

- If removing a layer **improves** aggregate Calmar_50bps, that layer does not earn
  its place. Flag: `ABLATION_FAIL: layer {layer_name} degrades Calmar by {delta}`.
- If removing a layer **reduces** Calmar_50bps, the layer contributes.
  Report: `ABLATION_PASS: layer {layer_name} contributes +{delta} Calmar`.

A candidate with any `ABLATION_FAIL` is flagged for review in D1e.
This does not automatically eliminate the candidate — D1e decides disposition.

If no multi-layer candidates exist, report "N/A — all candidates single-layer."

### 3. Save aggregate results
Save to `d1d_wfo_aggregate.csv` with columns:
- config_id, mechanism_type, candidate_id, cost_bps_rt, agg_cagr, agg_sharpe, agg_mdd, total_entries, avg_exposure, mean_fold_sharpe, median_fold_sharpe

### 4. Produce summary
Rank configs by aggregate Calmar_50bps = agg_cagr / max(abs(agg_mdd), 0.15) at 50 bps cost. Show top 10.

## Required output sections
1. `Completeness Check` — confirm all expected rows present in per-fold CSV
2. `Ablation Results` — per multi-layer candidate: PASS/FAIL per layer with Calmar deltas, or "N/A"
3. `WFO Results Summary` — top 10 configs by aggregate Calmar_50bps (flag any with ABLATION_FAIL)
4. `Files Saved` — list of output files

## What not to do
- Do not re-run any walk-forward evaluation.
- Do not use holdout data (2023-07-01 → 2024-09-30).
- Do not use reserve_internal data (2024-10-01 → snapshot end).
- Do not rank, filter, or select candidates — that is D1e's job.
- Do not freeze any candidate.
- Do not modify the constitution.
