# Review and Fix Log for Research Operating Kit v2

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
- `research_constitution_v2.0.yaml`
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
The schema document and the template did not agree on where certain fields belonged, especially `forbidden_inputs_confirmed_absent`.

**Why it mattered**
Engineers could build the wrong manifest shape and break validation.

**Fix**
The schema document and template now match exactly.
A new `lineage_id` field is also required for stronger audit traceability.

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
