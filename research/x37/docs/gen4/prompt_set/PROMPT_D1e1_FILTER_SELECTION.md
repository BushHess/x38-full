# PROMPT D1e1 - Hard Constraint Filter & Representative Selection (Use this after D1d3 in the same chat)

You have completed D1d3. Walk-forward aggregate results are available in `d1d_wfo_aggregate.csv`.

Your job in this turn is **only** to apply hard constraints, select the best config per candidate, and compute the complexity penalty.
Do **not** run holdout or reserve evaluation — that is D1e2.
Do **not** run bootstrap — that is D1e3.
Do **not** freeze any candidate — that is D1f's job.

## Step 1: Apply hard constraints on discovery WFO aggregate

Using `d1d_wfo_aggregate.csv`, filter configs at **50 bps RT cost**:

| Constraint | Rule |
|-----------|------|
| CAGR_50bps | > 0 |
| Max drawdown_50bps | ≤ 0.45 |
| Entries per year | ∈ [6, 80] (total_entries / discovery_years) |
| Exposure | ∈ [0.15, 0.90] |

Eliminate all configs that fail any hard constraint.

If **zero configs survive**, report this clearly. Still save `d1e_hard_constraint_filter.csv` (showing all configs failed). Then state: "No configs survive hard constraints. D1e2 and D1e3 will operate on empty sets. Proceed to D1e2."

## Step 1b: Post-ablation simplification (governance patch v4.0.1)

This step applies **only when** ALL of the following are true:
- A multi-layer candidate has **zero main configs** surviving Step 1, AND
- That candidate has an `ABLATION_FAIL` flag from D1d3, AND
- The corresponding ablation variant (simpler, with the failing layer removed)
  **passes all hard constraints** in Step 1.

When triggered:
1. The ablation variant is **promoted as a replacement candidate**, inheriting the
   parent's candidate slot. It is a strictly simpler mechanism (fewer layers, fewer
   or equal tunables).
2. Assign it a new candidate_id: `{parent_id}_simplified`.
3. Flag it with `post_ablation_revision: true` in all downstream artifacts.
4. The replacement uses the ablation variant's aggregate metrics from D1d3
   (already computed from the full WFO run).
5. **Maximum one replacement per parent candidate.** If multiple layers failed
   ablation, use the variant that removes the layer whose removal most improves
   Calmar_50bps.

This is the "one tightly bounded post-ablation simplification path" from governance
review. It does NOT allow new parameter search or re-design — only the strict removal
of a layer that was proven to hurt.

If no ablation promotion is triggered, skip this step.

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

## Step 4: Save results

Save to file:
- `d1e_hard_constraint_filter.csv` — all configs with pass/fail per constraint
- `d1e_surviving_candidates.csv` — surviving candidates with: candidate_id, mechanism_type, representative config_id, config values, agg_cagr_50bps, agg_sharpe_50bps, agg_mdd_50bps, total_entries, avg_exposure, Calmar_50bps, layers, tunables, complexity_penalty, adjusted_preference

  Include `mechanism_type` and full discovery aggregate metrics (from `d1d_wfo_aggregate.csv`) so that downstream prompts (D1e2, D1e3) do not need to re-read the WFO aggregate file.

## Required output sections
1. `Hard Constraint Filter` — N configs in → N survived → N eliminated (with reasons)
2. `Ablation Promotion` — per multi-layer candidate with ABLATION_FAIL: promoted or not, with reason. Or "N/A — no ablation promotion triggered"
3. `Representative Configs` — table of best config per surviving candidate (including any promoted ablation variants)
4. `Complexity Penalty` — layers, tunables, penalty, adjusted_preference per candidate
5. `Files Saved` — list of output files

## What not to do
- Do not re-run the walk-forward.
- Do not change candidate designs.
- Do not run holdout or reserve evaluation — that is D1e2.
- Do not run bootstrap — that is D1e3.
- Do not freeze or select champion/challengers — that is D1f.
- Do not modify the constitution.
