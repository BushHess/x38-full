# Research Operating Kit v3 (First-Principles)

This kit is the corrected and tightened operating bundle for one narrow mission:

**Find, freeze, and forward-validate a deployable Binance Spot BTC/USDT strategy using only spot OHLCV + taker flow data on 15m, 1h, 4h, and 1d bars.**

This kit does **not** chase a timeless global optimum.

It assumes:

- the historical snapshot is for **seed discovery only** and may already be contaminated for same-file out-of-sample claims,
- only **genuinely appended data** can create new forward evidence,
- the constitution is a **stable charter**, not a prompt to be revised every session,
- one execution chat should do **one mode only**.

## What changed from v2

v3 keeps all of v2's governance improvements and adds one fundamental change:

1. **Search space is now open mathematical, not archetype-locked.**
   v2 restricted candidates to three named archetypes with predefined TA primitives (EMA, ATR, momentum ROC).
   v3 allows any mathematical function of the admitted data surface as a valid candidate feature,
   constrained only by the complexity budget (max 3 layers, max 4 tunables, max 60 configs).
   This follows the first-principles methodology of gen1 research prompts (V2-V4),
   which produced the strongest known systems by measuring data before choosing mechanism families.

2. **D1b is now true data decomposition, not archetype validation.**
   v2's D1b measured whether predefined TA primitives had signal.
   v3's D1b measures all exploitable channels without pre-filtering by mechanism family.

3. **D1c designs from measurement, not from archetype templates.**
   Candidates emerge from D1b's strongest measured channels, not from a vocabulary of named indicators.

**Retained from v2:** contamination firewall, state pack handoff, forward evaluation policy,
session boundaries, upload matrix, hard constraints, paired bootstrap, governance review.

## Bundle contents

### Core charter and operating documents
- `BUNDLE_MANIFEST.txt`
- `research_constitution_v3.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- `SESSION_BOUNDARIES_EN.md`
- `STATE_PACK_SPEC_v3.0_EN.md`
- `HISTORICAL_SEED_AUDIT_SPEC_EN.md`
- `FORWARD_DECISION_POLICY_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`
- `TIMEFRAME_ALIGNMENT_SPEC_EN.md`

### Prompt set

#### Seed discovery lineage
- `PROMPT_D0_PRECHECK_NEW_SESSION.md`
- `PROMPT_D1a_DATA_INGESTION.md`
- `PROMPT_D1b1_PRICE_MOMENTUM.md` — price/momentum channels
- `PROMPT_D1b2_VOLATILITY_REGIME.md` — volatility/regime channels
- `PROMPT_D1b3_VOLUME_FLOW.md` — volume/order flow channels
- `PROMPT_D1b4_CROSS_TF_RANKING.md` — cross-timeframe + redundancy + ranking
- `PROMPT_D1c_CANDIDATE_DESIGN.md`
- `PROMPT_D1d1_IMPLEMENT.md` — implement + smoke test
- `PROMPT_D1d2_WFO_BATCH.md` — walk-forward batch
- `PROMPT_D1d3_WFO_AGGREGATE.md` — aggregate metrics
- `PROMPT_D1e1_FILTER_SELECTION.md` — hard constraint filter + selection
- `PROMPT_D1e2_HOLDOUT_RESERVE.md` — holdout + reserve evaluation
- `PROMPT_D1e3_BOOTSTRAP_RANKING.md` — bootstrap + final ranking
- `PROMPT_D1f1_FREEZE_SPECS.md` — freeze decision + specs
- `PROMPT_D1f2_REGISTRY_STATE.md` — registry + state files
- `PROMPT_D1f3_AUDIT_LEDGER_MAP.md` — audit + ledger + contamination map
- `PROMPT_D2_PACKAGE_STATE.md`
- `PROMPT_D1_SEED_DISCOVERY.md` — **monolithic reference only; do NOT use for chat execution.**
- `DEPRECATED_PROMPT_D1b_MEASUREMENT.md`, `DEPRECATED_PROMPT_D1d_WALK_FORWARD.md`, `DEPRECATED_PROMPT_D1e_HOLDOUT_RANKING.md`, `DEPRECATED_PROMPT_D1f_FREEZE_DRAFT.md` — **deprecated first-generation split; do NOT use.** Use D1b1–D1b4, D1d1–D1d3, D1e1–D1e3, D1f1–D1f3 instead. See PROMPT_INDEX for details.

#### Forward evaluation lineage
- `PROMPT_F0_PRECHECK_NEW_SESSION.md`
- `PROMPT_F1_FORWARD_EVALUATION.md`
- `PROMPT_F2_PACKAGE_STATE.md`

#### Governance lineage
- `PROMPT_G0_PRECHECK_NEW_SESSION.md`
- `PROMPT_G1_GOVERNANCE_REVIEW.md`
- `PROMPT_G2_RELEASE_PACKAGE.md`

### Machine-readable templates
- `artifact_hash_manifest.template.txt`
- `session_manifest.template.json`
- `candidate_registry.template.json`
- `meta_knowledge_registry.template.json`
- `portfolio_state.template.json`
- `historical_seed_audit.template.csv`
- `forward_daily_returns.template.csv`
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
- the search space philosophy,
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
4. In the same chat, send prompts D1a through D1f3 in order:
   - `PROMPT_D1a_DATA_INGESTION.md` — ingest + quality check
   - `PROMPT_D1b1_PRICE_MOMENTUM.md` through `PROMPT_D1b4_CROSS_TF_RANKING.md` — measurement (4 turns)
   - `PROMPT_D1c_CANDIDATE_DESIGN.md` — design candidates + config matrix
   - `PROMPT_D1d1_IMPLEMENT.md` through `PROMPT_D1d3_WFO_AGGREGATE.md` — walk-forward (3 turns)
   - `PROMPT_D1e1_FILTER_SELECTION.md` through `PROMPT_D1e3_BOOTSTRAP_RANKING.md` — holdout + ranking (3 turns)
   - `PROMPT_D1f1_FREEZE_SPECS.md` through `PROMPT_D1f3_AUDIT_LEDGER_MAP.md` — freeze + draft (3 turns)
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

## Operating environment requirements

**Seed discovery (D1)** requires a persistent filesystem environment. Prompts D1d1, D1d2, D1e2, and D1e3 save and reload implementation files (`d1d_impl_{candidate_id}.py`) and result CSVs across turns. An upload-only chat environment (e.g. ChatGPT web without code interpreter) is **not sufficient** for seed discovery.

**Forward evaluation (F1)** can run in an upload-only environment if the operator provides the state pack and appended delta as uploads, provided: (1) the state pack includes frozen implementation artifacts in `frozen_implementations/` so the AI can reload exact code rather than re-implementing from prose, (2) `state_pack_status` is `"sealed"` (no `DEFERRED` hash entries), and (3) the environment supports code execution. See the DEFERRED clause in D2/F2 and the implementation artifacts section in STATE_PACK_SPEC.

**Governance review (G1)** has no filesystem requirement.

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
