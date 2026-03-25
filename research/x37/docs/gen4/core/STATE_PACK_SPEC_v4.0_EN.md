# State Pack Specification v4.0

A state pack is the single handoff object from one execution session to the next.
It replaces chat history for lineage purposes.

## Required contents

### 1. `research_constitution_version.txt`
Plain text containing the exact active constitution version, for example:

```text
4.0
```

### 2. `program_lineage_id.txt`
Plain text containing the program lineage id, for example:

```text
btc_spot_mainline_lineage_001
```

### 3. `system_version_id.txt`
Plain text containing the current frozen system version, for example:

```text
V1
```

### 4. `system_version_manifest.json`
Machine-readable version lineage record:

```json
{
  "system_version_id": "V1",
  "parent_system_version_id": null,
  "freeze_cutoff_utc": "2026-03-18T23:59:59Z",
  "design_inputs_end_utc": "2026-03-18T23:59:59Z",
  "reason_for_freeze": "Initial seed discovery freeze",
  "version_history": [
    {
      "system_version_id": "V1",
      "parent_system_version_id": null,
      "freeze_cutoff_utc": "2026-03-18T23:59:59Z",
      "design_inputs_end_utc": "2026-03-18T23:59:59Z",
      "reason_for_freeze": "Initial seed discovery freeze",
      "evidence_clock_start": "2026-03-19T00:00:00Z",
      "evidence_days_accumulated": 0
    }
  ]
}
```

On redesign, a new entry is appended to `version_history` and the top-level fields are updated.

### 5. `session_summary.md`
Human-readable memo with:
- session id,
- mode,
- system_version_id,
- input snapshot or delta window,
- key decisions,
- outputs created,
- warnings,
- next allowed action.

### 6. `candidate_registry.json`
Machine-readable registry of all live and retired candidates.

At minimum it must contain:
- `system_version_id` at the registry level,
- one active champion or `NO_ROBUST_CANDIDATE`,
- zero to two active challengers,
- retired candidates for audit traceability.

### 7. `frozen_system_specs/`
One exact frozen spec per live candidate.

Each spec must include:
- candidate id,
- system_version_id,
- parent_system_version_id,
- freeze_cutoff_utc,
- design_inputs_end_utc,
- mechanism_type,
- signal logic as **unambiguous pseudocode** (not prose — every formula, comparison, and branch must be explicit enough that an independent implementer produces bit-identical output),
- execution logic as **unambiguous pseudocode** (decision timestamp, fill timestamp, entry/exit/hold conditions, cost application formula),
- position sizing as **unambiguous pseudocode**,
- exact cost model,
- exact tunable quantities and fixed values,
- evidence summary,
- provenance.

The `frozen_system_spec.template.md` defines the required format. Specs that use vague prose (e.g., "when trend is up") instead of pseudocode are non-compliant and must be rejected by the packaging step.

### 8. `meta_knowledge_registry.json`
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

### 9. `portfolio_state.json`
Current operational continuation state for every live candidate.

This file, together with any required warmup buffers, must be sufficient to continue exact forward evaluation across sessions.

**Boundary note**: If a signal fires on the last bar of an evaluation window, the corresponding fill has not yet occurred (next-open execution). The next session reconstructs this pending state by replaying warmup bars that overlap the signal bar. The `reconstructable_from_warmup_only` flag per candidate indicates whether warmup replay is sufficient for deterministic state reconstruction, including any pending signals at the window boundary.

Top-level required fields:
- `program_lineage_id`: the research program identifier.
- `constitution_version`: the active constitution version.
- `system_version_id`: the frozen version these candidates belong to.
- `state_pack_version`: the state pack version this file belongs to (e.g. `"v1"`, `"v2"`). Updated in each packaging step.
- `active_champion_id`: the candidate_id of the current champion, or `"NO_ROBUST_CANDIDATE"`. Must match `candidate_registry.json`.
- `active_challenger_ids`: array of candidate_ids for active challengers. Must match `candidate_registry.json`. Empty array if none.
- `current_forward_status`: `"not_started"`, `"in_progress"`, or `"governance_required"`.
- `forward_boundary_utc`: timestamp (ISO 8601 UTC) anchoring the first forward evaluation boundary when `current_forward_status` is `"not_started"`. In seed discovery (V1), this equals the last bar of the reserve_internal segment. In redesign versions (V2+), this equals `freeze_cutoff_utc`.
- `last_evaluated_timestamp_by_timeframe_utc`: per-timeframe last evaluated timestamp (null until first forward evaluation).
- `warmup_requirements`: per-timeframe bar counts required for deterministic state reconstruction (e.g. `{"15m_bars_required": 0, "1h_bars_required": 0, "4h_bars_required": 0, "1d_bars_required": 0}`).
- `candidate_states`: object keyed by candidate_id, containing per-candidate operational state (see below).

For each live candidate in `candidate_states`, it must record:
- current position state (`flat` or `long`),
- current position fraction,
- current entry timestamp if long,
- current entry price if long,
- trailing state if the system uses path-dependent exits,
- custom state (`null` or an opaque JSON object for mechanism-specific state that cannot be expressed via `trail_state` and cannot be reconstructed from warmup replay — e.g., latch flags, cooldown counters). If used, the frozen spec must document the custom_state schema.
- last signal timestamp,
- whether full reconstruction is possible from warmup-only data.

When `reconstructable_from_warmup_only` is `false`, the serialized fields above (including `custom_state` if non-null) are **load-bearing**.

### 10. `historical_seed_audit.csv`
Internal audit recording each frozen candidate's baseline metrics on the constitution's standard segments. Rows originate from seed discovery and from redesign freeze sessions (appended for redesigned candidates; carry-forward candidates retain their existing rows).

This file:
- records discovery / holdout / reserve-internal baseline metrics per candidate at freeze time,
- serves as the benchmark for the F1 reproduction check,
- supports reproducibility,
- does **not** count as forward evidence.

### 11. `forward_evaluation_ledger.csv`
Append-only ledger for appended forward windows only.

This file must:
- never mix in seed-snapshot rows,
- include `system_version_id` per row,
- include `evidence_clean_for_version` flag per row (true only if window start > version's freeze_cutoff_utc),
- contain both incremental and cumulative fields,
- support keep / promote / kill / downgrade decisions,
- remain append-only across forward sessions within the same `system_version_id`.

When a new `system_version_id` is created via redesign, the new state pack contains this file with the header row only. Parent version rows must be archived into the parent state pack before sealing the new one.

### 12. `contamination_map.md`
Human-readable contamination and provenance summary:
- which snapshot was used for seed discovery,
- system version lineage (version id, parent, freeze_cutoff_utc per version),
- which windows were used only for forward evaluation,
- which windows are clean for which system_version_id,
- which artifacts were withheld from blind discovery,
- any overlap caveats,
- latest state pack version.

### 13. `input_hash_manifest.txt`
Hash or file fingerprint record for the exact files admitted in the session.

### 14. `warmup_buffers/`
Optional. Include only if needed for deterministic reconstruction.

Warmup rules:
- warmup data is not new evidence,
- warmup data must precede the appended evaluation window,
- warmup buffers should be as small as practical.

### 15. `forward_daily_returns.csv`
Append-only file of per-candidate daily UTC returns across all forward windows for the active `system_version_id`.

The stored file retains the full version-scoped series since the version's `freeze_cutoff_utc`.
Candidate-scoped cumulative metrics anchored at `cumulative_anchor_utc` are derived by filtering
this retained series at evaluation time; promotion must **not** truncate the stored file for live candidates.

This file enables correct recomputation of cumulative forward Sharpe, MDD, and paired bootstrap across multi-window forward evaluation. Without the raw daily return series, these metrics cannot be derived from summary statistics alone.

Required columns: `system_version_id`, `candidate_id`, `date_utc`, `daily_return`, `cost_rt_bps`, `session_id`.

Rules:
- append-only across forward sessions within the same `system_version_id` (never remove prior rows within a version),
- one row per candidate per trading day per cost scenario,
- `system_version_id` must be present on every row,
- candidate-scoped cumulative metrics for ranking / promote / kill may be computed from the subset
  of rows where `date_utc >= cumulative_anchor_utc`, but this is a reporting view, not a storage boundary,
- **retention rule**: for any live candidate (champion or challenger), all rows since the version's `freeze_cutoff_utc` must be retained in the active file as long as the `system_version_id` is active. This is required for version-scoped `FORWARD_CONFIRMED` checks, which recompute cumulative metrics from the full daily series (see FORWARD_DECISION_POLICY). Rows for a candidate may only be removed after the candidate is moved to `retired_candidates` AND either (a) the version has achieved `FORWARD_CONFIRMED` or (b) the version is superseded by a redesign,
- seed-snapshot returns must not appear in this file.

When a new `system_version_id` is created via redesign, the new state pack contains this file with the header row only. Parent version rows must be archived into the parent state pack before sealing the new one.

In `state_pack_v1` (created by seed discovery), this file contains the header row only — no forward data exists yet.

### 16. `forward_equity_curve.csv` (optional, recommended)
Append-only file of per-candidate daily equity values.

Required columns: `system_version_id`, `candidate_id`, `date_utc`, `equity`, `cost_rt_bps`, `session_id`.

This file enables correct recomputation of cumulative MDD and equity-path-dependent diagnostics without floating-point drift from daily returns.

### 17. `impl/` (required in newly created seed_discovery and redesign_freeze state packs; carried forward in forward evaluation packs)
Implementation source files for each live candidate (e.g., `impl/{candidate_id}.py`).

Including executable code alongside the frozen specs strengthens cross-session reproducibility. The frozen spec (pseudocode) remains the authoritative definition; the implementation is a convenience artifact that allows forward evaluation sessions to skip re-implementation and reduces the risk of semantic drift.

Minimal runner contract for each candidate file:
- export `run_candidate(data_by_timeframe, config, cost_rt_bps, start_utc=None, end_utc=None, initial_state=None)`
  or an equivalent class method with the same arguments,
- `data_by_timeframe` supplies the admitted bars by timeframe,
- `cost_rt_bps` is used **only for computing net daily returns and derived metrics** (CAGR, Sharpe, MDD).
  Signal generation, entry/exit decisions, and all path-dependent state (position, trail, custom state)
  **must not** depend on `cost_rt_bps`. This invariant ensures that `terminal_state` is identical across
  cost levels and that a single `terminal_state` per candidate is sufficient for state handoff.
- `initial_state` is `null` when warmup-only replay is sufficient, otherwise it carries the serialized
  candidate state from `portfolio_state.json`,
- return at minimum:
  - `daily_returns`
  - `trade_log`
  - `terminal_state` with fields compatible with `portfolio_state.json`
    (`position_state`, `position_fraction`, `entry_time_utc`, `entry_price`, `trail_state`,
    `custom_state`, `last_signal_time_utc`, `reconstructable_from_warmup_only`).

Rules:
- Created during seed discovery (from `d1d_impl_{candidate_id}.py`) or redesign freeze.
- Carried forward unchanged in forward evaluation state packs.
- If `impl/` is absent in a legacy or non-compliant state pack, the forward evaluation session must
  re-implement from the frozen spec pseudocode and pass the reproduction check (step 3 in F1).
- If `impl/` is present and the frozen spec has been updated (redesign), the implementation must be regenerated to match.

### 18. `redesign_dossier.md` (conditional)
Include only in state packs produced by `redesign_freeze` sessions.

This is the dossier that was validated in R0 and used as the gate for the redesign. It records:
- the redesign trigger,
- the failure claim and hypothesis,
- the proposed fix and its scope,
- search accounting (variants explored, rejected, selection basis),
- complexity impact and DOF analysis,
- evidence clock reset justification.

Including the dossier in the state pack ensures that future sessions can audit why a redesign occurred without relying on the original chat. The `system_version_manifest.json` field `redesign_dossier_ref` should point to this file when present.

State packs produced by seed discovery or forward evaluation do not include this file.

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

## What must enter a redesign_freeze chat

A redesign_freeze chat should receive:
- the latest state pack (including forward evidence from parent version),
- the active constitution,
- the full data set (historical + all appended data),
- a fresh session manifest with mode = "redesign_freeze".

The redesign_freeze chat must:
- create a new `system_version_id`,
- set `freeze_cutoff_utc` to the latest data timestamp,
- mark all prior data as seen for the new version,
- reset the evidence clock to zero.

## State pack lifecycle

- `state_pack_v1` is created by seed discovery. Contains `system_version_id: V1`.
- `state_pack_v2` is created by the first forward evaluation session for V1.
- `state_pack_v3` might be created by a redesign_freeze, containing `system_version_id: V2`.
- `state_pack_v4` is created by the first forward evaluation session for V2.
- and so on.

The latest state pack is the only intended machine handoff between execution sessions.
The state pack version counter is monotonic and independent of system_version_id.
