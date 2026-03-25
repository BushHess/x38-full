# Review and Fix Log: Changes from Kit v2 to Kit v4

This document records the substantive problems found in the previous bundle and the corrections made here.

## 1. Historical seed evidence was mixed into the forward ledger

**Problem**
The prior bundle initialized `forward_evaluation_ledger.csv` with seed-session rows from the historical snapshot. That blurred the line between contaminated seed evidence and true forward evidence.

**Why it mattered**
This could lead to accidental overstatement of forward confirmation and make later sessions treat historical candidate-mining evidence as if it were appended out-of-sample evidence.

**Fix**
This bundle introduces:
- `historical_seed_audit.csv`
- `HISTORICAL_SEED_AUDIT_SPEC_EN.md`

The forward ledger now begins empty and is reserved for appended forward windows only.

---

## 2. Forward decisions were under-specified

**Problem**
The previous prompts allowed keep / promote / kill decisions but did not define exactly when those decisions were eligible.

**Why it mattered**
Without an explicit decision basis, one session could promote on a single strong window while another would wait, causing hidden policy drift.

**Fix**
This bundle adds an explicit forward decision law in:
- `research_constitution_v4.0.yaml`
- `FORWARD_DECISION_POLICY_EN.md`

Decisions now use:
- standard quarterly review cadence,
- cumulative forward evidence basis,
- minimum evidence thresholds,
- explicit promotion and kill rules,
- emergency review triggers.

---

## 3. Incremental and cumulative forward evidence were not separated

**Problem**
The previous bundle evaluated appended windows but did not clearly separate:
- latest-window metrics,
- cumulative-forward-since-freeze metrics.

**Why it mattered**
Window-local noise could dominate decisions and cause role churn.

**Fix**
The revised forward ledger stores both incremental and cumulative fields.
Promote / kill decisions use cumulative basis except under emergency triggers.

---

## 4. Operational state handoff was too weak

**Problem**
`portfolio_state.json` in the previous bundle did not require enough state to continue exact path-dependent simulation across sessions.

**Why it mattered**
A candidate with an open position, trailing stop anchor, or other path-dependent exit logic could be mis-reconstructed in the next session.

**Fix**
`portfolio_state.json` now requires per-candidate state:
- position state,
- position fraction,
- entry timestamp,
- entry price,
- trailing state,
- last signal timestamp,
- whether warmup-only reconstruction is sufficient.

---

## 5. Session manifest schema was internally inconsistent

**Problem**
The schema document and the template did not agree on where certain fields belonged, especially `input_isolation_checks` (formerly `forbidden_inputs_confirmed_absent`).

**Why it mattered**
Engineers could build the wrong manifest shape and break validation.

**Fix**
The schema document and template now match exactly.
The canonical field name is `program_lineage_id` (matching the constitution identity model and all templates).

---

## 6. Review cadence was missing

**Problem**
The previous bundle implied a new forward session whenever new data existed.

**Why it mattered**
That encourages tiny review windows with poor statistical power and too many chats.

**Fix**
The constitution now sets:
- standard quarterly review cadence,
- minimum 90 calendar days for a standard forward review,
- maximum 180 calendar days before a forced standard review,
- explicit emergency triggers that justify an earlier review.

---

## 7. The original hard constraints were probably too tight for BTC spot swing systems

**Problem**
A 35% max-drawdown hard cap and an 8-entries-per-year floor may reject otherwise deployable BTC spot swing mechanisms and over-favor low-exposure defensive systems.

**Why it mattered**
That is a structural selection bias, not just a cosmetic preference.

**Fix**
The constitution now uses:
- `max_drawdown_50bps_lte: 0.45`
- `entries_per_year_between: [6, 80]`
- `exposure_between: [0.15, 0.90]`

The ranking metric remains `Calmar_50bps`, so drawdown is still penalized continuously.

---

## 8. Upload discipline was not explicit enough

**Problem**
The previous bundle did not clearly distinguish human-only documents from AI-input documents.

**Why it mattered**
Uploading too many explanatory files increases context load and contamination risk.

**Fix**
This bundle adds:
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`

These documents specify exactly which files to upload in each execution chat and which documents should remain human-only.

---

## 9. Packaging requirements were incomplete

**Problem**
The previous state pack spec did not require:
- a hash manifest,
- a snapshot note template,
- a governance failure dossier template,
- a frozen system spec template.

**Why it mattered**
That weakens reproducibility, auditability, and smooth handoff.

**Fix**
This bundle adds:
- `input_hash_manifest.template.txt`
- `snapshot_notes.template.md`
- `governance_failure_dossier.template.md`
- `frozen_system_spec.template.md`

---

## 10. Discussion chats and execution chats were not clearly separated

**Problem**
Long strategy discussion inside an execution chat can silently contaminate the lineage.

**Why it mattered**
The session may drift from execution into redesign without a formal stop.

**Fix**
`SESSION_BOUNDARIES_EN.md` now distinguishes:
- execution chats,
- discussion-only chats.

Discussion-only chats are allowed, but they are not part of the lineage and must not produce state packs.

---

## Bottom line

The revised bundle is stricter where ambiguity causes hidden bias:
- seed vs forward evidence,
- eligibility for role changes,
- packaging completeness,
- operational continuity,
- upload discipline.

The revised bundle is more permissive only where the previous charter was likely over-constraining valid BTC spot swing candidates:
- drawdown hard cap,
- entries-per-year floor,
- exposure floor.

---

## 11. `historical_seed_audit.csv` framing inconsistency (post-v4 review)

**Problem**
The spec and state-pack description called this file "seed-only" / "seed-discovery evidence", but the redesign packaging rule required appending new rows for redesigned candidates. The column `role_after_seed` was semantically incorrect for redesign-produced rows. The prose mismatch made the file's dual origin unclear.

**Why it mattered**
An operator reading the spec literally ("seed-only") would not expect redesign rows in this file, creating confusion about what the file represents and what values to put in `role_after_seed` for a redesigned candidate.

**Fix**
- Reframed `HISTORICAL_SEED_AUDIT_SPEC_EN.md` opening and purpose to acknowledge dual origin (seed discovery + redesign freeze).
- Renamed column `role_after_seed` → `role_at_freeze` in spec, template CSV, `PROMPT_D1f3_AUDIT_LEDGER_MAP.md`, and `PROMPT_D1f_FREEZE_DRAFT.md`.
- Clarified packaging rule: carry-forward candidates retain existing rows (valid because algorithm/parameters are unchanged); only redesigned candidates get new rows.
- Updated `STATE_PACK_SPEC_v4.0_EN.md` item 10 description to match.

---

## 12. `impl/` missing from canonical output structure (post-v4 review)

**Problem**
`FILE_AND_SCHEMA_CONVENTIONS_EN.md` canonical `state_pack_vN/` listing omitted `impl/`, even though the constitution (`required_artifacts_by_mode`), `STATE_PACK_SPEC` (item 17), and all three packaging prompts (D2, F2, R2) reference it.

**Why it mattered**
An operator following the canonical listing to build a state pack would produce a structurally valid pack that is missing an artifact the F1 prompt expects, forcing unnecessary re-implementation from pseudocode.

**Fix**
Added `impl/` to the canonical listing in `FILE_AND_SCHEMA_CONVENTIONS_EN.md`, between `frozen_system_specs/` and `warmup_buffers/`.

---

## 13. `cost_rt_bps` signal-independence invariant was implicit (post-v4 review)

**Problem**
The runner contract passes `cost_rt_bps` as a parameter, but the spec did not explicitly state that cost must not influence signal generation or path-dependent state. This left ambiguity about whether `terminal_state` could diverge across cost levels — which would break the one-state-per-candidate model in `portfolio_state.json`.

**Why it mattered**
If a future candidate implemented cost-conditional signal logic, the state handoff would silently corrupt: `portfolio_state.json` stores one `terminal_state` per candidate, but two cost levels would produce two different terminal states.

**Fix**
Added an explicit invariant to `STATE_PACK_SPEC_v4.0_EN.md` (runner contract) and `PROMPT_D1d1_IMPLEMENT.md`: `cost_rt_bps` is used only for net daily return and metric computation; signal generation, entry/exit decisions, and all path-dependent state must not depend on it.

---

## 14. Audit data flow gap: D1f3 could not populate reproduction-check columns without rerun (post-v4 review)

**Problem**
`historical_seed_audit.csv` requires `exit_count`, `final_position_state`, and `daily_returns_hash` per segment. But D1d2 only saved `entries` (not `exit_count` or `final_position_state`), and D1e2 saved summary metrics without daily return series. D1f3 was forbidden from re-running backtests, creating a data flow dead end.

**Why it mattered**
The F1 reproduction check depends on these columns. Without them, D1f3 could not produce a spec-compliant audit CSV from persisted artifacts alone, forcing reliance on chat context (fragile) or skipping the check entirely (weakens reproducibility guarantee).

**Fix**
- `PROMPT_D1d2_WFO_BATCH.md`: added `exit_count` and `final_position_state` to per-fold metrics and CSV columns.
- `PROMPT_D1e2_HOLDOUT_RESERVE.md`: added `exit_count` and `final_position_state` to holdout/reserve metrics; added `d1e_holdout_daily_returns.csv` and `d1e_reserve_daily_returns.csv` output files.
- `PROMPT_D1f3_AUDIT_LEDGER_MAP.md`: added explicit source references for each reproduction-check column.

---

## 15. R1 redesign lacked sourcing instructions for `portfolio_state.json` candidate_states (post-v4 review)

**Problem**
D1f2 (seed discovery) explicitly names `d1e_terminal_states.json` as the source for per-candidate state. R1 (redesign) only said "draft `portfolio_state.json`" with skeletal top-level instructions, providing no guidance on where to source `candidate_states`, `warmup_requirements`, or carry-forward candidate state.

**Why it mattered**
An operator following R1 would not know where to get per-candidate position state for the redesigned candidate or for carry-forward candidates from the parent version. R2 assumes the file is already complete.

**Fix**
Added explicit sourcing instructions to R1 step 6: redesigned candidate uses terminal state from step 3's internal validation; carry-forward candidates copy verbatim from parent's `portfolio_state.json`; `warmup_requirements` derived from indicator parameters. Also added explicit top-level registry fields to R1's `candidate_registry.json` bullet.

---

## 16. F1 kill-flow did not prune `active_challenger_ids` in `portfolio_state.json` (post-v4 review)

**Problem**
The kill instruction in F1 required moving the candidate to `retired_candidates` and removing it from `candidate_states`, but did not mention updating `active_challenger_ids`. The promotion case and the no-candidate-survives case both explicitly updated this field, but the single-kill case did not.

**Why it mattered**
`STATE_PACK_SPEC` requires `active_challenger_ids` to match `candidate_registry.json`. The missing instruction could cause a desync where a killed candidate's ID remains in `active_challenger_ids`.

**Fix**
Updated the kill instruction in `PROMPT_F1_FORWARD_EVALUATION.md` to explicitly require removing the killed candidate's ID from `active_challenger_ids` (if challenger) or setting `active_champion_id` to `"NO_ROBUST_CANDIDATE"` (if champion).

---

## 17. `cumulative_anchor_utc` format contradiction between schema note and template examples (post-v4 review)

**Problem**
The schema note in `candidate_registry.template.json` said "Format: date-only YYYY-MM-DD", and both D1f2 and F1 prompts used date-only format. But the template placeholder values showed `YYYY-MM-DDTHH:MM:SSZ` (full timestamp), contradicting the schema note.

**Why it mattered**
An operator copying the template placeholder would produce a full timestamp, which could break the date-to-date filtering rule described in the schema note.

**Fix**
Changed template placeholder values from `YYYY-MM-DDTHH:MM:SSZ` to `YYYY-MM-DD` for `cumulative_anchor_utc` fields (lines 44 and 76).

---

## 18. D1f2 checklist omitted required top-level registry fields (post-v4 review)

**Problem**
`PROMPT_D1f2_REGISTRY_STATE.md` Step 1 said "Using the exact schema from `candidate_registry.template.json`" but the explicit checklist only listed `program_lineage_id`, `constitution_version`, `registry_created_in_session`, and `active_champion_id`. It omitted `system_version_id`, `parent_system_version_id`, `freeze_cutoff_utc`, `design_inputs_end_utc`, `evidence_clean_since_utc`, and `version_lineage_summary`.

**Why it mattered**
An operator following the checklist rather than cross-referencing the template could produce an incomplete registry, missing fields that downstream prompts (F1, R1) depend on.

**Fix**
Added all missing top-level fields to the D1f2 Step 1 checklist and added `version_lineage_summary` to the list after `retired_candidates`.
