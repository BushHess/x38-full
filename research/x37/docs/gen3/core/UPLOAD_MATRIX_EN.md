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

## A. Seed discovery chat

### Upload
- `research_constitution_v3.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- `TIMEFRAME_ALIGNMENT_SPEC_EN.md`
- raw historical snapshot files:
  - `spot_btcusdt_15m.csv`
  - `spot_btcusdt_1h.csv`
  - `spot_btcusdt_4h.csv`
  - `spot_btcusdt_1d.csv`
- `session_manifest.json`
- `input_hash_manifest.txt`
- optional `snapshot_notes.md`

### Do not upload
- any prior `state_pack_vN`
- prior reports
- prior winners
- prior shortlist tables
- prior benchmark definitions
- prior contamination logs
- prior frozen system specs
- prior evaluation ledgers

---

## B. Forward evaluation chat

### Upload
- `research_constitution_v3.0.yaml`
- latest `state_pack_vN`
- appended delta raw files for the new evaluation window
- required `warmup_buffers/` if the latest state pack does not already carry all needed operational state
- fresh `session_manifest.json`
- `input_hash_manifest.txt`

### Do not upload
- the original full historical snapshot unless it is explicitly needed as warmup
- governance discussion notes
- old seed discovery chat outputs outside the latest state pack
- human guide or README

---

## C. Governance review chat

### Upload
- current `research_constitution_v3.0.yaml`
- latest `state_pack_vN` (extract the files below from it; do not upload separate copies alongside the state pack)
  - `forward_evaluation_ledger.csv`
  - `candidate_registry.json`
  - `meta_knowledge_registry.json`
  - `contamination_map.md`
- `governance_failure_dossier.md`
- fresh `session_manifest.json`

### Do not upload
- raw historical snapshot files unless the dossier explicitly needs them
- blind discovery prompts
- extra narrative documents that are not part of the governance decision

---

## Discussion-only chats

If you want to discuss philosophy, redesign ideas, or possible future constitutions:
- open a separate discussion-only chat,
- do not package outputs from it,
- do not treat it as part of the research lineage,
- do not upload its outputs into a blind execution chat.

---

## Practical rule

If you are unsure whether to upload a document, ask:

**Does this file change execution in the current mode, or is it just explanatory?**

If it is just explanatory, keep it out of the execution chat.
