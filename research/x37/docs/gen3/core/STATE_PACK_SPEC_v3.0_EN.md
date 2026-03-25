# State Pack Specification v3.0

A state pack is the single handoff object from one execution session to the next.
It replaces chat history for lineage purposes.

## State pack status

Every state pack has a machine-readable status stored in `portfolio_state.json` field `state_pack_status`:

- `"draft"` — the state pack was created but contains unresolved `DEFERRED` entries in `input_hash_manifest.txt` or `artifact_hash_manifest.txt`. A draft state pack must NOT be used as input to a new session until the operator resolves all DEFERRED entries and sets the status to `"sealed"`.
- `"sealed"` — all hashes are resolved, all required contents are present, and the state pack is valid for use as input.

Only a `"sealed"` state pack may be used as input to a forward evaluation or governance review session.

## Required contents

### 1. `research_constitution_version.txt`
Plain text containing the exact active constitution version, for example:

```text
3.0
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
- mechanism_type,
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

This file, together with any required warmup buffers, must be sufficient to continue exact forward evaluation across sessions.

**Boundary note**: If a signal fires on the last bar of an evaluation window, the corresponding fill has not yet occurred (next-open execution). The next session reconstructs this pending state by replaying warmup bars that overlap the signal bar. The `reconstructable_from_warmup_only` flag per candidate indicates whether warmup replay is sufficient for deterministic state reconstruction, including any pending signals at the window boundary.

Top-level required fields:
- `reserve_internal_end_utc`: last bar timestamp of the reserve_internal segment (ISO 8601 UTC). Anchors the first forward evaluation boundary when `current_forward_status` is `"not_started"`.
- `current_forward_status`: `"not_started"`, `"in_progress"`, or `"governance_required"`. The value `"governance_required"` indicates that all live candidates were eliminated during forward evaluation and a governance review must occur before any further forward evaluation or seed discovery can proceed.
- `last_evaluated_timestamp_by_timeframe_utc`: per-timeframe last evaluated timestamp (null until first forward evaluation).

At minimum, for each live candidate it must record:
- current position state (`flat` or `long`),
- current position fraction,
- current entry timestamp if long,
- current entry price if long,
- trailing state if the system uses path-dependent exits,
- last signal timestamp,
- whether full reconstruction is possible from warmup-only data,
- `additional_state`: a generic object (or `null`) for any mechanism-specific internal state that does not fit the standard fields above (e.g., pending signal, hysteresis state, cooldown counter, adaptive threshold state, serialized feature state). When present, this object is load-bearing and must be preserved exactly across sessions.

When `reconstructable_from_warmup_only` is `false`, the serialized fields above (position state, entry price, trail state, additional_state, etc.) are **load-bearing** — they carry boundary state that warmup replay alone cannot reconstruct. In this case, the packaging prompt must ensure that all non-reconstructable state is fully captured in these fields before the state pack is sealed.

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

### 13. `forward_daily_returns.csv`
Append-only file of per-candidate daily UTC returns across all forward windows since each candidate's `cumulative_anchor_utc`.

This file enables correct recomputation of cumulative forward Sharpe, MDD, and paired bootstrap across multi-window forward evaluation. Without the raw daily return series, these metrics cannot be derived from summary statistics alone (Sharpe is a ratio of mean to std; MDD requires the full equity path; bootstrap requires the raw series).

Required columns: `candidate_id`, `date_utc`, `daily_return`, `cost_rt_bps`, `session_id`.

Rules:
- append-only across forward sessions (never remove prior rows),
- one row per candidate per trading day per cost scenario,
- when a candidate is promoted, its rows prior to the new `cumulative_anchor_utc` may be archived but must not be deleted from the active file until the next state pack is sealed,
- seed-snapshot returns must not appear in this file.

In `state_pack_v1` (created by seed discovery), this file contains the header row only — no forward data exists yet.

### 14. `frozen_implementations/`

One executable implementation file per live candidate, named `d1d_impl_{candidate_id}.py` (or equivalent DSL).

These files:
- are the exact code used during walk-forward evaluation in seed discovery,
- are frozen alongside the system specs,
- enable deterministic re-execution without re-implementation from prose,
- must be hashed in `artifact_hash_manifest.txt`.

If the state pack is used in a forward evaluation session, the implementation must be loaded from these files — not re-implemented from the frozen system spec. The frozen system spec remains the human-readable authoritative description; the implementation file is the machine-executable counterpart.

### 15. `artifact_hash_manifest.txt`

Hash or file fingerprint record for frozen output artifacts (all files in `frozen_system_specs/` and `frozen_implementations/`). This is separate from `input_hash_manifest.txt` (which records admitted inputs) because inputs and outputs serve different audit purposes.

## Optional contents

- `charts/`
- `audit/`
- `governance/`

## What must not enter a blind seed discovery chat

A blind seed discovery chat must not receive:
- a prior state pack,
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
