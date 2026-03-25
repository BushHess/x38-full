# PROMPT D1e - Holdout, Reserve & Ranking (Use this after D1d in the same chat)

You have completed D1d. Walk-forward results are available in `d1d_wfo_aggregate.csv`.

Your job in this turn is to apply hard constraints, run holdout and reserve evaluation, and rank candidates.
Do **not** freeze any candidate — that is D1f's job.
Do **not** draft output files yet.

## Step 1: Apply hard constraints on discovery WFO aggregate

Using `d1d_wfo_aggregate.csv`, filter configs at **50 bps RT cost**:

| Constraint | Rule |
|-----------|------|
| CAGR_50bps | > 0 |
| Max drawdown_50bps | ≤ 0.45 |
| Entries per year | ∈ [6, 80] (total_entries / discovery_years) |
| Exposure | ∈ [0.15, 0.90] |

Eliminate all configs that fail any hard constraint.

If **zero configs survive**, report this clearly and stop. The seed discovery produces `NO_ROBUST_CANDIDATE`.

## Step 2: Select best config per candidate

For configs that survive hard constraints:
- Group by candidate_id
- Within each candidate, select the config with the highest **Calmar_50bps**
  - Calmar_50bps = CAGR_50bps / max(abs(MDD_50bps), 0.15)
- This is the representative config for that candidate going forward

## Step 3: Apply complexity penalty

For each surviving candidate's representative config:
- logical_layer_penalty = 0.02 per layer
- tunable_quantity_penalty = 0.03 per tunable
- adjusted_preference = Calmar_50bps - (layers × 0.02) - (tunables × 0.03)

Use adjusted_preference for ranking only. Hard constraints use raw metrics.

## Step 4: Run holdout evaluation

**Holdout period: 2023-07-01 → 2024-09-30**

For each surviving candidate (using its representative config):
1. Initialize strategy with all data up to 2023-06-30 (warmup + discovery) for indicator warmup.
2. Run on holdout period.
3. Record at both 20 bps and 50 bps RT:
   - CAGR, Sharpe, max drawdown, entries, exposure, mean daily return

4. Check hard constraints on holdout at 50 bps:
   - CAGR_50bps > 0
   - MDD_50bps ≤ 0.45
   - If a candidate fails holdout hard constraints, flag it but do not eliminate yet — record the failure.

## Step 5: Run reserve_internal evaluation

**Reserve internal period: 2024-10-01 → snapshot end**

For each surviving candidate:
1. Initialize with all data up to 2024-09-30.
2. Run on reserve_internal period.
3. Record same metrics as holdout.
4. This is additional internal evidence, not clean forward evidence.

## Step 6: Bootstrap lower-bound check

For each surviving candidate, on the **full discovery period** (2020-01-01 → 2023-06-30):
1. Compute daily returns series.
2. Run moving block bootstrap with parameters from the constitution:
   - block sizes: [5, 10, 20] days
   - resamples per block size: 3000
   - random seed: 20260318
   - paired common indices: true (when comparing two candidates)
3. For each block size, compute 5th percentile of resampled mean daily return.
4. LB5 = the 5th percentile from the median block size (10 days).
5. Hard constraint: bootstrap_lb5_mean_daily_return > 0.

Eliminate candidates that fail this check.

## Step 7: Final ranking

Rank all surviving candidates by **adjusted_preference** (Calmar_50bps minus complexity penalty).

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
- candidate_id, archetype, config values
- Discovery: Calmar_50bps, CAGR, Sharpe, MDD, entries, exposure
- Holdout: same metrics
- Reserve: same metrics
- Bootstrap LB5
- Complexity: layers, tunables, penalty
- Adjusted preference

## Step 8: Save results

Save to files:
- `d1e_hard_constraint_filter.csv` — all configs with pass/fail per constraint
- `d1e_holdout_results.csv` — holdout metrics per surviving candidate
- `d1e_reserve_results.csv` — reserve metrics per surviving candidate
- `d1e_final_ranking.csv` — ranked candidates with all metrics

## Required output sections
1. `Hard Constraint Filter` — N configs in → N survived → N eliminated (with reasons)
2. `Holdout Results` — table of holdout metrics per candidate
3. `Reserve Results` — table of reserve metrics per candidate
4. `Bootstrap Check` — LB5 per candidate, pass/fail
5. `Final Ranking` — ranked table with adjusted preference
6. `Files Saved` — list of output files

## What not to do
- Do not re-run the walk-forward.
- Do not change candidate designs.
- Do not freeze or select champion/challengers — that is D1f.
- Do not draft output files — that is D1f.
- Do not modify the constitution.
