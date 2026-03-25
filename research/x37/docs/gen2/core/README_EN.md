# Research Operating Kit v2

This kit is the corrected and tightened operating bundle for one narrow mission:

**Find, freeze, and forward-validate a deployable Binance Spot BTC/USDT strategy using only spot OHLCV + taker flow data on 15m, 1h, 4h, and 1d bars.**

This kit does **not** chase a timeless global optimum.

It assumes:

- the historical snapshot is for **seed discovery only** and may already be contaminated for same-file out-of-sample claims,
- only **genuinely appended data** can create new forward evidence,
- the constitution is a **stable charter**, not a prompt to be revised every session,
- one execution chat should do **one mode only**.

## What changed from the previous bundle

This version fixes several structural problems:

1. **Historical seed audit is separated from forward evaluation ledger.**
   Historical seed evidence is internal candidate-mining evidence only. It is no longer mixed into the forward ledger.

2. **Forward decisions now use an explicit cumulative basis.**
   Standard review windows report both incremental and cumulative metrics, but promote / keep / kill decisions are based on cumulative forward evidence unless an emergency trigger fires.

3. **Promotion and kill rules are explicit.**
   The previous bundle left too much discretion in forward sessions.

4. **Operational handoff is stronger.**
   `portfolio_state.json` now carries enough state to continue exact forward evaluation across sessions even for candidates with open positions or path-dependent exit logic.

5. **Upload discipline is sharper.**
   A dedicated upload matrix now distinguishes human-only documents from AI-input documents.

## Bundle contents

### Core charter and operating documents
- `BUNDLE_MANIFEST.txt`
- `research_constitution_v2.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- `SESSION_BOUNDARIES_EN.md`
- `STATE_PACK_SPEC_v2.0_EN.md`
- `HISTORICAL_SEED_AUDIT_SPEC_EN.md`
- `FORWARD_DECISION_POLICY_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`

### Prompt set

#### Seed discovery lineage
- `PROMPT_D0_PRECHECK_NEW_SESSION.md`
- `PROMPT_D1a_DATA_INGESTION.md`
- `PROMPT_D1b_MEASUREMENT.md`
- `PROMPT_D1c_CANDIDATE_DESIGN.md`
- `PROMPT_D1d_WALK_FORWARD.md`
- `PROMPT_D1e_HOLDOUT_RANKING.md`
- `PROMPT_D1f_FREEZE_DRAFT.md`
- `PROMPT_D2_PACKAGE_STATE.md`
- `PROMPT_D1_SEED_DISCOVERY.md` (monolithic reference — see PROMPT_INDEX for details)

#### Forward evaluation lineage
- `PROMPT_F0_PRECHECK_NEW_SESSION.md`
- `PROMPT_F1_FORWARD_EVALUATION.md`
- `PROMPT_F2_PACKAGE_STATE.md`

#### Governance lineage
- `PROMPT_G0_PRECHECK_NEW_SESSION.md`
- `PROMPT_G1_GOVERNANCE_REVIEW.md`
- `PROMPT_G2_RELEASE_PACKAGE.md`

### Machine-readable templates
- `session_manifest.template.json`
- `candidate_registry.template.json`
- `meta_knowledge_registry.template.json`
- `portfolio_state.template.json`
- `historical_seed_audit.template.csv`
- `forward_evaluation_ledger.template.csv`
- `contamination_map.template.md`
- `governance_failure_dossier.template.md`
- `frozen_system_spec.template.md`
- `snapshot_notes.template.md`
- `input_hash_manifest.template.txt`
- `constitution_status.template.txt`
- `governance_decision.template.md`
- `migration_note_current_to_next_major.template.md`
- `session_summary.template.md`

### Human guide
- `USER_GUIDE_VI.md`

## Core operating model

There are only three lineage modes:

1. **Seed discovery**
   Use one contaminated historical snapshot once to freeze:
   - 1 champion seed
   - up to 2 challenger seeds

2. **Forward evaluation**
   Use only genuinely appended data to decide:
   - keep champion
   - promote challenger
   - kill challenger
   - downgrade label
   - escalate governance concern

3. **Governance review**
   Review the charter itself.
   No strategy search is allowed here.

## What should usually change across sessions

- the appended data delta,
- the latest state pack,
- the evaluation ledger,
- the portfolio state.

## What should usually not change across sessions

- the constitution,
- the archetype ontology,
- the primary objective,
- the paired bootstrap semantics,
- the hard caps.

## Human-only documents vs AI-input documents

### Human-only by default
Do **not** upload these to execution chats unless absolutely necessary:
- `README_EN.md`
- `USER_GUIDE_VI.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`

### AI-input documents depend on mode
Use `UPLOAD_MATRIX_EN.md` for the exact file list per mode.

## Minimum recommended workflow

### Seed discovery: do this once per historical snapshot
1. Start a brand-new chat.
2. Upload only the files listed in `UPLOAD_MATRIX_EN.md` for seed discovery.
3. Send `PROMPT_D0_PRECHECK_NEW_SESSION.md`.
4. In the same chat, send prompts D1a through D1f in order:
   - `PROMPT_D1a_DATA_INGESTION.md` — ingest + quality check
   - `PROMPT_D1b_MEASUREMENT.md` — feature measurement + signal analysis
   - `PROMPT_D1c_CANDIDATE_DESIGN.md` — design candidates + config matrix
   - `PROMPT_D1d_WALK_FORWARD.md` — walk-forward evaluation (14 folds)
   - `PROMPT_D1e_HOLDOUT_RANKING.md` — holdout + reserve + ranking
   - `PROMPT_D1f_FREEZE_DRAFT.md` — freeze champion/challengers + draft output files
5. In the same chat, send `PROMPT_D2_PACKAGE_STATE.md`.
6. Save `state_pack_v1`.
7. Stop the chat.

### Forward evaluation: this should be the normal repeated cycle
1. Wait until the next scheduled review window or an emergency trigger.
2. Start a brand-new chat.
3. Upload only the files listed in `UPLOAD_MATRIX_EN.md` for forward evaluation.
4. Send `PROMPT_F0_PRECHECK_NEW_SESSION.md`.
5. In the same chat, send `PROMPT_F1_FORWARD_EVALUATION.md`.
6. In the same chat, send `PROMPT_F2_PACKAGE_STATE.md`.
7. Save `state_pack_vN+1`.
8. Stop the chat.

### Governance review: use rarely
1. Start a brand-new chat.
2. Upload only the files listed in `UPLOAD_MATRIX_EN.md` for governance review.
3. Send `PROMPT_G0_PRECHECK_NEW_SESSION.md`.
4. In the same chat, send `PROMPT_G1_GOVERNANCE_REVIEW.md`.
5. In the same chat, send `PROMPT_G2_RELEASE_PACKAGE.md`.
6. Stop the chat.

## Hard boundary

Do **not** do any of the following:
- discovery and forward evaluation in one chat,
- forward evaluation and governance review in one chat,
- repeated “improved” seed discovery on the same historical snapshot,
- redesign after packaging,
- same-file optimization masquerading as a new lineage,
- uploading prior winners or prior reports into a blind seed discovery chat.

## What “best” means here

This kit does not promise a final eternal optimum.
It selects the **best currently deployable mechanism** under:
- the frozen constitution,
- the admitted BTC spot data domain,
- the hard constraints,
- the cumulative forward evidence on genuinely appended data.

Read `USER_GUIDE_VI.md` before running the first execution chat.
