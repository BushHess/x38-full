# State Pack Specification v2.0

A state pack is the single handoff object from one execution session to the next.
It replaces chat history for lineage purposes.

## Required contents

### 1. `research_constitution_version.txt`
Plain text containing the exact active constitution version, for example:

```text
2.0
```

### 2. `lineage_id.txt`
Plain text containing the lineage id, for example:

```text
btc_spot_mainline_lineage_001
```

### 3. `session_summary.md`
Human-readable memo with:
- session id,
- mode,
- input snapshot or delta window,
- key decisions,
- outputs created,
- warnings,
- next allowed action.

### 4. `candidate_registry.json`
Machine-readable registry of all live and retired candidates.

At minimum it must contain:
- one active champion or `NO_ROBUST_CANDIDATE`,
- zero to two active challengers,
- retired candidates for audit traceability.

### 5. `frozen_system_specs/`
One exact frozen spec per live candidate.

Each spec must include:
- candidate id,
- archetype,
- exact signal logic,
- exact execution logic,
- exact cost model,
- exact tunable quantities and fixed values,
- evidence summary,
- provenance.

### 6. `meta_knowledge_registry.json`
Registry of Tier 1, Tier 2, and Tier 3 rules with:
- statement,
- tier,
- basis,
- scope,
- authority,
- provenance,
- overlap guard,
- challenge rule,
- expiry,
- status.

### 7. `portfolio_state.json`
Current operational continuation state for every live candidate.

This file must be sufficient to continue exact forward evaluation across sessions.
At minimum, for each live candidate it must record:
- current position state (`flat` or `long`),
- current position fraction,
- current entry timestamp if long,
- current entry price if long,
- trailing state if the system uses path-dependent exits,
- last signal timestamp,
- whether full reconstruction is possible from warmup-only data.

### 8. `historical_seed_audit.csv`
Seed-only internal audit extracted from the historical snapshot.

This file:
- records discovery / holdout / reserve-internal seed metrics,
- supports reproducibility,
- does **not** count as forward evidence.

### 9. `forward_evaluation_ledger.csv`
Append-only ledger for appended forward windows only.

This file must:
- never mix in seed-snapshot rows,
- contain both incremental and cumulative fields,
- support keep / promote / kill / downgrade decisions,
- remain append-only across forward sessions.

### 10. `contamination_map.md`
Human-readable contamination and provenance summary:
- which snapshot was used for seed discovery,
- which windows were used only for forward evaluation,
- which artifacts were withheld from blind discovery,
- any overlap caveats,
- latest state pack version.

### 11. `input_hash_manifest.txt`
Hash or file fingerprint record for the exact files admitted in the session.

### 12. `warmup_buffers/`
Optional. Include only if needed for deterministic reconstruction.

Warmup rules:
- warmup data is not new evidence,
- warmup data must precede the appended evaluation window,
- warmup buffers should be as small as practical.

## Optional contents

- `charts/`
- `audit/`
- `governance/`

## What must not enter a blind seed discovery chat

A blind seed discovery chat must not receive:
- a prior state pack from another lineage,
- prior winners,
- prior reports,
- prior shortlist tables,
- prior precomputed system metrics.

## What must enter a forward evaluation chat

A forward evaluation chat should receive:
- the latest state pack only,
- the active constitution,
- the appended delta,
- any required warmup buffer,
- a fresh session manifest.

## State pack lifecycle

- `state_pack_v1` is created by seed discovery.
- `state_pack_v2` is created by the first forward evaluation session.
- `state_pack_v3` is created by the next forward evaluation session.
- and so on.

The latest state pack is the only intended machine handoff between execution sessions.
