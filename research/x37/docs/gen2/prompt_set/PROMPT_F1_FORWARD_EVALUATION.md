# PROMPT F1 - Forward Evaluation Execution (Use this after F0 in the same chat)

Proceed with forward evaluation on the appended data window only.

## Mission

Evaluate the frozen champion and all frozen challengers on the newly appended evaluation window.

Then make only the allowed decisions:
- keep champion
- promote challenger
- kill challenger
- downgrade evidence label
- escalate a governance concern

## Hard instructions
- Do not redesign any candidate.
- Do not add new feature families.
- Do not search for new candidates.
- Do not rewrite the constitution.
- Use warmup buffers only for rolling-context computation or deterministic state reconstruction.
- Count only the appended evaluation window as new evidence.
- Report both incremental window metrics and cumulative forward metrics.
- Use cumulative forward basis for promote / keep / kill unless an emergency trigger applies.

## Required procedure
1. Load the frozen candidate specs from the incoming state pack.
2. Reconstruct candidate state from `portfolio_state.json` and any admitted warmup buffers.
3. Evaluate all live candidates on the appended window at both 20 bps and 50 bps round-trip costs.
4. Update cumulative forward metrics since freeze or last promotion.
5. Apply the constitution hard constraints on the cumulative forward basis if the minimum decision threshold is met.
6. Rank surviving candidates under the constitution objective.
7. Run the paired daily-return bootstrap where required for promotion decisions.
8. Decide:
   - champion stays or changes,
   - challengers remain alive or are killed,
   - evidence labels are updated,
   - governance concern is raised or not.
9. Draft updates for:
   - `candidate_registry.json`
   - `portfolio_state.json`
   - `forward_evaluation_ledger.csv`
   - `contamination_map.md`
   - `session_summary.md`
   - `meta_knowledge_registry.json` only if a new Tier 3 note or governance-relevant rule status change is justified; otherwise carry it forward unchanged

## Required output sections
1. `Forward Window Summary`
2. `Incremental Candidate Results`
3. `Cumulative Forward Candidate Results`
4. `Champion-Challenger Decision`
5. `Evidence Labels After Window`
6. `Governance Escalation`
7. `Files Prepared For Packaging`

## Important

Stop after preparing the outputs.
Do not package yet. Packaging is the next prompt.
