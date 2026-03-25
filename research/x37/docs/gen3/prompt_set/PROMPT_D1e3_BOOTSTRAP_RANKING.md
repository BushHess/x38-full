# PROMPT D1e3 - Bootstrap & Final Ranking (Use this after D1e2 in the same chat)

You have completed D1e2. Input files available:
- `d1e_surviving_candidates.csv` — candidate_id, mechanism_type, config values, full discovery metrics (CAGR, Sharpe, MDD, entries, exposure), Calmar_50bps, complexity penalty, adjusted_preference (from D1e1)
- `d1e_holdout_results.csv` — holdout metrics per candidate (from D1e2)
- `d1e_reserve_results.csv` — reserve metrics per candidate (from D1e2)

Your job in this turn is to run the bootstrap lower-bound check, produce the final ranking, and save consolidated results.
Do **not** freeze any candidate — that is D1f's job.

**Guard**: If D1e1 reported zero surviving candidates, save empty `d1e_final_ranking.csv` (header only), then state: "No candidates to rank. Proceed to D1f."

## Step 1: Bootstrap lower-bound check

For each surviving candidate (using the implementation from `d1d_impl_{candidate_id}.py`), on the **full discovery period** (2020-01-01 → 2023-06-30):
1. Compute daily returns series (or reload from `d1d_wfo_daily_returns.csv` if available for this config).
2. Run moving block bootstrap with parameters from the constitution:
   - block sizes: [5, 10, 20] days
   - resamples per block size: 3000
   - random seed: 20260319
   - paired common indices: true (when comparing two candidates)
3. For each block size, compute 5th percentile of resampled mean daily return.
4. LB5 = the 5th percentile from the median block size (10 days).
5. Hard constraint: bootstrap_lb5_mean_daily_return > 0.

Eliminate candidates that fail this check.

## Step 2: Final ranking

Rank all surviving candidates by **adjusted_preference** (Calmar_50bps minus complexity penalty, from D1e1).

**Tie-break order** (from constitution, apply sequentially if adjusted_preference is tied):
1. Meaningful paired advantage over current champion (when applicable)
2. Higher bootstrap lower bound of cumulative mean daily return
3. Higher cost resilience from 20 bps to 50 bps
4. Lower logical complexity
5. Broader parameter plateau
6. Higher trade count at similar utility
7. Lexical candidate_id

Record for each:
- Rank
- candidate_id, mechanism_type, config values
- Discovery: Calmar_50bps, CAGR, Sharpe, MDD, entries, exposure
- Holdout: same metrics (from D1e2)
- Reserve: same metrics (from D1e2)
- Bootstrap LB5
- Complexity: layers, tunables, penalty
- Adjusted preference

## Step 3: Save results

Save to file:
- `d1e_final_ranking.csv` — ranked candidates with all metrics

## Required output sections
1. `Bootstrap Check` — LB5 per candidate, pass/fail
2. `Final Ranking` — ranked table with adjusted preference, all metrics
3. `Files Saved` — list of output files

## What not to do
- Do not re-run the walk-forward.
- Do not change candidate designs.
- Do not freeze or select champion/challengers — that is D1f.
- Do not draft output files — that is D1f.
- Do not modify the constitution.
