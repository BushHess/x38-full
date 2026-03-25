# Upload Matrix

This document tells you exactly what to upload to each execution chat.

## General rule

Upload the minimum input set needed for the current mode.
Do **not** upload the entire bundle by default.

## Human-only documents

Normally **do not upload** these to execution chats:
- `README_EN.md`
- `USER_GUIDE_VI.md`
- `KIT_REVIEW_AND_FIXLOG_EN.md`
- `PROMPT_INDEX_EN.md`
- `UPLOAD_MATRIX_EN.md`

---

## Sandbox modes

### S1. Exploration chat
No prescribed upload set. Use whatever data and files you need.
- No state pack produced.
- No outputs enter the mainline lineage.
- Any results are hypothesis-only.

### S2. Discussion chat
No prescribed upload set.
- No state pack produced.
- No candidates are frozen.

---

## Mainline modes

### A. Seed discovery chat

#### Upload
- `research_constitution_v4.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- raw historical snapshot files:
  - `spot_btcusdt_15m.csv`
  - `spot_btcusdt_1h.csv`
  - `spot_btcusdt_4h.csv`
  - `spot_btcusdt_1d.csv`
- `session_manifest.json`
- `input_hash_manifest.txt`
- optional `snapshot_notes.md`

#### Do not upload
- any prior `state_pack_vN`
- prior reports
- prior winners
- prior shortlist tables
- prior benchmark definitions
- prior contamination logs
- prior frozen system specs
- prior evaluation ledgers

---

### B. Forward evaluation chat

#### Upload
- `research_constitution_v4.0.yaml`
- latest `state_pack_vN`
- appended delta raw files for the new evaluation window
- required `warmup_buffers/` if the latest state pack does not already carry all needed operational state
- fresh `session_manifest.json`
- `input_hash_manifest.txt`
- optional: original historical snapshot raw files (for F1 reproduction check — see F1 step 3). If omitted, F1 skips the reproduction check and notes it in the report.

#### Do not upload
- governance discussion notes
- old seed discovery chat outputs outside the latest state pack
- human guide or README
- redesign dossier (forward evaluation must NOT trigger redesign)

---

### C. Redesign freeze chat

#### Upload
- `research_constitution_v4.0.yaml`
- latest `state_pack_vN` (including forward evidence from parent version)
- full data set (historical + all appended data)
- `redesign_dossier.md` (required gate)
- fresh `session_manifest.json` with mode = "redesign_freeze"
- `input_hash_manifest.txt`

#### Do not upload
- old seed discovery chat outputs outside the latest state pack
- human guide or README

---

### D. Governance review chat

#### Upload
- current `research_constitution_v4.0.yaml`
- latest `state_pack_vN` (extract the files below from it)
  - `forward_evaluation_ledger.csv`
  - `candidate_registry.json`
  - `meta_knowledge_registry.json`
  - `contamination_map.md`
- `governance_failure_dossier.md` (prepare this first from `template/governance_failure_dossier.template.md` before opening the governance chat)
- fresh `session_manifest.json`

#### Do not upload
- raw historical snapshot files unless the dossier explicitly needs them
- blind discovery prompts
- extra narrative documents that are not part of the governance decision

---

## Practical rule

If you are unsure whether to upload a document, ask:

**Does this file change execution in the current mode, or is it just explanatory?**

If it is just explanatory, keep it out of the execution chat.
