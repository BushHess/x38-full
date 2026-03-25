# Prompt Index

This document tells you exactly which prompt sequence belongs to which mode.

## Rule

One execution chat should use exactly one of these sequences.

## Seed discovery sequence

Use these prompts in the **same chat**, in this exact order:
1. `PROMPT_D0_PRECHECK_NEW_SESSION.md` — precheck
2. `PROMPT_D1a_DATA_INGESTION.md` — ingest + quality check
3. `PROMPT_D1b1_PRICE_MOMENTUM.md` — return, momentum, structural features, mean-reversion, gaps
4. `PROMPT_D1b2_VOLATILITY_REGIME.md` — volatility channels, regime structure
5. `PROMPT_D1b3_VOLUME_FLOW.md` — volume, order flow, calendar effects
6. `PROMPT_D1b4_CROSS_TF_RANKING.md` — cross-timeframe, redundancy, integrated channel ranking
7. `PROMPT_D1c_CANDIDATE_DESIGN.md` — design candidates + config matrix
8. `PROMPT_D1d1_IMPLEMENT.md` — implement candidates + smoke test
9. `PROMPT_D1d2_WFO_BATCH.md` — walk-forward batch (all configs × folds × costs)
10. `PROMPT_D1d3_WFO_AGGREGATE.md` — aggregate WFO metrics + summary
11. `PROMPT_D1e1_FILTER_SELECTION.md` — hard constraint filter + representative config + complexity penalty
12. `PROMPT_D1e2_HOLDOUT_RESERVE.md` — holdout + reserve_internal evaluation
13. `PROMPT_D1e3_BOOTSTRAP_RANKING.md` — bootstrap lower-bound check + final ranking
14. `PROMPT_D1f1_FREEZE_SPECS.md` — champion/challenger selection + frozen system specs
15. `PROMPT_D1f2_REGISTRY_STATE.md` — candidate_registry + meta_knowledge_registry + portfolio_state
16. `PROMPT_D1f3_AUDIT_LEDGER_MAP.md` — historical_seed_audit + forward ledger + contamination map
17. `PROMPT_D2_PACKAGE_STATE.md` — hash manifests + package state_pack_v1

D1b1–D1b4 and D1d2 may require re-sending if execution times out (see individual prompts for PARTIAL handling).

Use this sequence:
- once per historical snapshot,
- only for candidate mining,
- never again on the same snapshot after `state_pack_v1` is packaged.

Note: The original `PROMPT_D1_SEED_DISCOVERY.md` is the gen2 monolithic version.
The original `DEPRECATED_PROMPT_D1b/D1d/D1e/D1f` files are the first-generation split (now deprecated; renamed with `DEPRECATED_` prefix).
D1b1–D1b4, D1d1–D1d3, D1e1–D1e3, D1f1–D1f3 are the current split, designed so each
turn handles a single type of work within chat execution limits.

### Split design notes

D1b (measurement) was split into 4 sub-prompts because the original combined 8 measurement
families across 4 timeframes, cross-timeframe analysis, redundancy mapping, and channel
ranking in a single turn. The split groups by channel family (price/momentum, volatility/regime,
volume/flow) with a final integration turn (cross-TF + redundancy + ranking).

D1d (walk-forward) was split into 3 sub-prompts because the original combined implementation,
full WFO execution (up to 1,680 evaluations worst case), and aggregation. The split separates
implementation+verification from batch execution from aggregation.

D1e (holdout/ranking) was split into 3 sub-prompts because the original combined hard constraint
filtering, holdout evaluation, reserve evaluation, bootstrap (9,000 resamples), and ranking.
The split groups by computation type: filtering/selection, evaluation, statistical testing+ranking.

D1f (freeze/draft) was split into 3 sub-prompts because the original generated 8+ output files
with heavy cross-dependencies. The split groups by output type: decision+specs, registry+state,
audit+ledger+map. `input_hash_manifest.txt` was moved to D2 (packaging concern).

D1c (candidate design) was kept as a single prompt. It is borderline but manageable when
producing 1-2 candidates. If sessions routinely produce 3 candidates or approach 60 configs,
consider splitting into D1c1 (mechanism design) and D1c2 (config matrix + compliance).

D1e (ranking) includes two operationalizations not explicitly stated in the original D1:
- **Best-config-per-candidate selection**: the original D1 does not describe how to reduce
  60 configs to 3 candidates. D1e1 selects the highest Calmar_50bps config per candidate_id.
- **Champion holdout fallback**: the original D1 does not address what happens if rank-1
  fails holdout. D1f1 takes the highest-ranked candidate that passes both discovery and holdout.
These are necessary procedural details implied by the original D1 but not stated.

## Forward evaluation sequence

Use these three prompts in the **same chat**, in this exact order:
1. `PROMPT_F0_PRECHECK_NEW_SESSION.md`
2. `PROMPT_F1_FORWARD_EVALUATION.md`
3. `PROMPT_F2_PACKAGE_STATE.md`

Use this sequence:
- after enough appended data has accumulated for the next standard review,
- or when an emergency review trigger fires.

## Governance review sequence

Use these three prompts in the **same chat**, in this exact order:
1. `PROMPT_G0_PRECHECK_NEW_SESSION.md`
2. `PROMPT_G1_GOVERNANCE_REVIEW.md`
3. `PROMPT_G2_RELEASE_PACKAGE.md`

Use this sequence:
- only when the constitution itself may be broken or misaligned.

## Never do this

- D-sequence and F-sequence in one chat
- F-sequence and G-sequence in one chat
- D-sequence more than once for the same historical snapshot
- packaging prompt before the execution prompt
- governance review as a hidden way to restart search

## Human-only reminder

Do not upload this document to execution chats unless necessary for troubleshooting.
