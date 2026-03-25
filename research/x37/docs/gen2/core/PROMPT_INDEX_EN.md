# Prompt Index

This document tells you exactly which prompt sequence belongs to which mode.

## Rule

One execution chat should use exactly one of these sequences.

## Seed discovery sequence

Use these prompts in the **same chat**, in this exact order:
1. `PROMPT_D0_PRECHECK_NEW_SESSION.md` — precheck
2. `PROMPT_D1a_DATA_INGESTION.md` — ingest + quality check
3. `PROMPT_D1b_MEASUREMENT.md` — feature measurement + signal analysis
4. `PROMPT_D1c_CANDIDATE_DESIGN.md` — design candidates + config matrix
5. `PROMPT_D1d_WALK_FORWARD.md` — walk-forward evaluation (14 folds)
6. `PROMPT_D1e_HOLDOUT_RANKING.md` — holdout + reserve + ranking
7. `PROMPT_D1f_FREEZE_DRAFT.md` — freeze champion/challengers + draft output files
8. `PROMPT_D2_PACKAGE_STATE.md` — package state_pack_v1

D1d may require re-sending if execution times out (see prompt for details).

Use this sequence:
- once per historical snapshot,
- only for candidate mining,
- never again on the same snapshot after `state_pack_v1` is packaged.

Note: The original `PROMPT_D1_SEED_DISCOVERY.md` is the monolithic version.
D1a–D1f are the split version designed for online chat execution within turn limits.

### Split design notes

D1b (measurement) is an **intentional addition** not present in the original monolithic D1.
Rationale: the original D1 jumps from data quality to archetype search in one step.
For online chat execution, the AI needs a dedicated measurement turn to understand
signal properties before designing candidates. This does not change the logic — it
adds an explicit analysis step that was implicit in the monolithic version.

D1e (ranking) includes two operationalizations not explicitly stated in the original D1:
- **Best-config-per-candidate selection**: the original D1 does not describe how to reduce
  60 configs to 3 candidates. D1e selects the highest Calmar_50bps config per candidate_id.
- **Champion holdout fallback**: the original D1 does not address what happens if rank-1
  fails holdout. D1f takes the highest-ranked candidate that passes both discovery and holdout.
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
