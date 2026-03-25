# Research Operating Kit v4 (Versioned Systems)

This kit is the operating bundle for one narrow mission:

**Find, freeze, and forward-validate deployable Binance Spot BTC/USDT strategies using only spot OHLCV + taker flow data on 15m, 1h, 4h, and 1d bars.**

## What changed from v3

v4 keeps all of v3's open-mathematical search space and contamination firewall, and adds one fundamental change:

1. **The unit of evidence is a frozen system version, not a "project" or "lineage".**

   v3 treated the entire lineage as one object: one seed discovery, one forward evaluation stream.
   v4 separates three concerns:
   - `constitution_version`: the research rules (this charter)
   - `program_lineage_id`: the research program (a series of versions pursuing the same goal)
   - `system_version_id`: a specific frozen candidate lineup (one champion + up to two challengers, all with immutable signal logic) earning its own OOS evidence

   OOS evidence accrues to a `system_version_id`, not to the program. Redesigning creates a new
   version and resets the evidence clock to zero.

2. **Exploration is explicitly contaminated.**

   v3 implied that the historical snapshot was contaminated but did not model what happens
   when the researcher iterates: learns from forward results, redesigns, freezes again.
   v4 makes this explicit: exploration is free but earns no OOS credit. Only frozen versions
   earn forward evidence, and only on data that arrived after their freeze.

3. **Redesign resets the evidence clock.**

   If you use a forward window to decide what to change, that window is no longer OOS for
   the redesigned version. The new version's clean evidence starts only from data after its
   own `freeze_cutoff_utc`.

**Retained from v3:** open mathematical search space, contamination firewall, state pack handoff,
paired bootstrap, hard constraints, governance review, session boundaries, upload matrix.

## Sandbox vs Mainline

**Sandbox is for learning. Mainline is for proving.**

- **Sandbox** (exploration, discussion): iterate freely on any data. All results are
  hypothesis. No OOS claim. No state pack. Not part of the version lineage.
- **Mainline** (seed_discovery, forward_evaluation, redesign_freeze, governance): only
  frozen versions participate. State packs form the lineage. Redesign is gated.

A candidate discovered in sandbox is only a hypothesis. It becomes a mainline candidate
only after being frozen through a seed_discovery or redesign_freeze chat.

## Core operating model

```
sandbox exploration ──► freeze Vn (mainline) ──► forward evidence for Vn
                                                        │
                                                redesign decision?
                                                        │
                            ┌───── no: continue forward evaluation
                            │
                            └───── yes (trigger + cooldown + dossier):
                                     sandbox exploration ──► freeze Vn+1 ──► forward evidence for Vn+1
```

### Mainline modes

1. **Seed discovery** — mine historical snapshot, freeze as `system_version_id`.
   Each chat freezes the algorithm at the end.

2. **Forward evaluation** — evaluate a frozen version on appended data.
   This is the only mode that creates clean OOS evidence.
   **Must NEVER trigger a redesign.**

3. **Redesign freeze** — create a new `system_version_id` after learning from forward
   evidence. Requires trigger + cooldown + dossier. Resets evidence clock.

4. **Governance review** — review the charter. No strategy search.

## Redesign guardrails (anti-overfix)

Redesign is the highest-cost operation because it resets the evidence clock.
The constitution enforces these guards:

1. **Trigger required** — only 4 allowed triggers (consecutive failure, emergency,
   proven bug, structural deficiency). "Feels bad" is not a trigger.
2. **Cooldown** — 180 days minimum since last freeze (emergency/bug exempt).
3. **Evidence threshold** — >= 180 forward days and >= 6 entries before redesign allowed.
4. **Single hypothesis** — each redesign changes exactly one principal thing.
5. **Change budget** — max 1 logic block, max 3 tunables, max 1 execution change.
   Max 1 major redesign per 180 days.
6. **Redesign dossier** — required gate document. If you can't write it, don't redesign.
7. **Promotion ≠ redesign** — promotion uses existing challengers, redesign creates
   new algorithms. Forward evaluation must never blur into redesign.

## Complexity guardrails (anti-DOF-creep)

Evidence clock reset alone does not prevent adaptive overfitting if each redesign
expands the search space. Additional controls:

1. **Hard complexity caps** — max 3 layers, max 4 tunables, max 4 feature families,
   max 20 configs per redesign.
2. **Minor vs major** — minor redesign (net DOF +0 or +1) stays in mainline.
   Major redesign (DOF >+1, new layer/family) must go through governance or
   start a new lineage.
3. **Complexity tax** — each additional tunable pays 0.03 penalty in ranking.
   More complex must prove more.
4. **Search accounting** — dossier must log how many variants were tried and rejected.
5. **DOF circuit breaker** — if cumulative DOF exceeds 2x initial version, next
   redesign requires governance regardless.

## The self-check principle

> "If I used this window to decide what to change, then this window is no longer OOS
> for the changed version."

This is not required for every iteration. But it is required if you want the iteration
to produce clean OOS evidence for the new version.

Concretely:
- **Iterating to research / think / modify**: does not require new future data.
- **Claiming the new version is better with clean evidence**: requires unseen data for that version.

## What resets the evidence clock (new system_version_id required)

Any change that could alter output on seen data:
- feature formula, threshold, lookback
- entry/exit rule
- position sizing
- cost handling
- warmup semantics
- data cleaning rule
- tie-break logic
- objective function
- bugfix that changes trade log or PnL

## What does NOT reset (same system_version_id)

Changes provably bit-for-bit identical on seen data:
- comments, docstrings, rename
- formatting, packaging
- logging, export format
- validator/test changes
- pure refactor (same logic, different structure)
- bugfix proven to not change any trade or PnL

## Bundle contents

### Core charter and operating documents
- `BUNDLE_MANIFEST.txt`
- `research_constitution_v4.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- `SESSION_BOUNDARIES_EN.md`
- `STATE_PACK_SPEC_v4.0_EN.md`
- `HISTORICAL_SEED_AUDIT_SPEC_EN.md`
- `FORWARD_DECISION_POLICY_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`

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
- `PROMPT_D1b_MEASUREMENT.md`, `PROMPT_D1d_WALK_FORWARD.md`, `PROMPT_D1e_HOLDOUT_RANKING.md`, `PROMPT_D1f_FREEZE_DRAFT.md` — **deprecated first-generation split; do NOT use.** Use D1b1–D1b4, D1d1–D1d3, D1e1–D1e3, D1f1–D1f3 instead. See PROMPT_INDEX for details.

#### Forward evaluation lineage
- `PROMPT_F0_PRECHECK_NEW_SESSION.md`
- `PROMPT_F1_FORWARD_EVALUATION.md`
- `PROMPT_F2_PACKAGE_STATE.md`

#### Redesign freeze lineage
- `PROMPT_R0_PRECHECK_NEW_SESSION.md`
- `PROMPT_R1_REDESIGN_EXECUTION.md`
- `PROMPT_R2_PACKAGE_STATE.md`

#### Governance lineage
- `PROMPT_G0_PRECHECK_NEW_SESSION.md`
- `PROMPT_G1_GOVERNANCE_REVIEW.md`
- `PROMPT_G2_RELEASE_PACKAGE.md`

### Machine-readable templates
- `session_manifest.template.json`
- `candidate_registry.template.json`
- `meta_knowledge_registry.template.json`
- `portfolio_state.template.json`
- `system_version_manifest.template.json`
- `historical_seed_audit.template.csv`
- `forward_evaluation_ledger.template.csv`
- `forward_daily_returns.template.csv`
- `forward_equity_curve.template.csv`
- `contamination_map.template.md`
- `frozen_system_spec.template.md`
- `redesign_dossier.template.md`
- `governance_failure_dossier.template.md`
- `governance_decision.template.md`
- `snapshot_notes.template.md`
- `session_summary.template.md`
- `migration_note_current_to_next_major.template.md`
- `input_hash_manifest.template.txt`
- `constitution_status.template.txt`

### Human guide
- `USER_GUIDE_VI.md`

## Minimum recommended workflow

### Initial seed discovery: do this once per historical snapshot
1. Start a brand-new chat.
2. Upload only the files listed in `UPLOAD_MATRIX_EN.md` for seed discovery.
3. Send `PROMPT_D0_PRECHECK_NEW_SESSION.md`.
4. In the same chat, send prompts D1a through D1f3 in order.
5. In the same chat, send `PROMPT_D2_PACKAGE_STATE.md`.
6. Save `state_pack_v1`. This freeze creates `system_version_id: V1`.
7. Stop the chat.

### Forward evaluation: the normal repeated cycle
1. Wait until the next scheduled review window or an emergency trigger.
2. Start a brand-new chat.
3. Upload only the files listed in `UPLOAD_MATRIX_EN.md` for forward evaluation.
4. Send `PROMPT_F0_PRECHECK_NEW_SESSION.md`.
5. In the same chat, send `PROMPT_F1_FORWARD_EVALUATION.md`.
6. In the same chat, send `PROMPT_F2_PACKAGE_STATE.md`.
7. Save `state_pack_vN+1`.
8. Stop the chat.

### Redesign cycle: when forward evidence motivates changes
1. **Exploration** (discussion-only chat or local work): iterate freely on all available data.
   No state pack produced. All results are contaminated.
2. **Freeze new version**: start a brand-new chat, upload files per `UPLOAD_MATRIX_EN.md` for redesign_freeze.
   Send `PROMPT_R0_PRECHECK_NEW_SESSION.md`, then `PROMPT_R1_REDESIGN_EXECUTION.md`, then `PROMPT_R2_PACKAGE_STATE.md`.
   Creates a new `system_version_id` with `parent_system_version_id` pointing to the previous version.
   Record `freeze_cutoff_utc` = latest data timestamp used. Evidence clock resets to zero.
3. **Forward evaluation for new version**: only data after `freeze_cutoff_utc` counts as
   clean OOS for the new version.

### Governance review: use rarely
1. Prepare `governance_failure_dossier.md` from `template/governance_failure_dossier.template.md`.
   This is a prerequisite artifact, not something created inside the G-sequence execution chat.
2. Start a brand-new chat.
3. Upload only the files listed in `UPLOAD_MATRIX_EN.md` for governance review.
4. Send `PROMPT_G0_PRECHECK_NEW_SESSION.md`.
5. In the same chat, send `PROMPT_G1_GOVERNANCE_REVIEW.md`.
6. In the same chat, send `PROMPT_G2_RELEASE_PACKAGE.md`.
7. Stop the chat.

## Operating environment requirements

**Seed discovery (D1)** requires a persistent filesystem environment.

**Forward evaluation (F1)** can run in an upload-only environment if the operator provides the state pack and appended delta as uploads. However, `input_hash_manifest.txt` must have all hashes completed (no `DEFERRED` entries) before the state pack is used as input to a new session.

**Governance review (G1)** has no filesystem requirement.

## Hard boundary

Do **not** do any of the following:
- discovery and forward evaluation in one chat,
- forward evaluation and governance review in one chat,
- claim OOS evidence from exploration results,
- claim forward window as OOS for a version if that window informed the version's design,
- upload prior winners or prior reports into a blind seed discovery chat,
- skip `system_version_id` assignment when freezing.

## What "best" means here

This kit does not promise a final eternal optimum.
It selects the **best currently deployable mechanism** under:
- the frozen constitution,
- the admitted BTC spot data domain,
- the hard constraints,
- the cumulative forward evidence scoped to each frozen `system_version_id`.

Read `USER_GUIDE_VI.md` before running the first execution chat.
