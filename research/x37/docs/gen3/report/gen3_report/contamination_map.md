# Contamination Map

- **snapshot_id**: `snapshot_20260318`
- **lineage_id**: `btc_spot_mainline_lineage_001`
- **session_id**: `session_20260319_seed_001`
- **constitution_version**: `3.0`
- **latest_state_pack_version**: `v1`
- **state_pack_status**: `draft`
- **historical snapshot date range**: `2017-08-17` → `2026-03-18` UTC
- **reserve_internal_end_utc**: `2026-03-18T23:59:59.999Z`

## Seed-discovery data usage boundaries

### Candidate-mining / seed-discovery data
- **warmup**: first available historical bar → `2019-12-31T23:59:59.999Z`
- **discovery**: `2020-01-01T00:00:00Z` → `2023-06-30T23:59:59.999Z`
- Use in session: data ingestion and quality checks, channel measurements, candidate design, discovery walk-forward, hard-constraint filtering.
- Status: **internal historical snapshot usage only**. Not admissible as clean external out-of-sample evidence.

### Holdout data (internal only, not forward)
- **holdout**: `2023-07-01T00:00:00Z` → `2024-09-30T23:59:59.999Z`
- Constitutional role: internal post-discovery check inside the same frozen snapshot.
- Session outcome: no holdout runs were executed because zero configs survived D1e1 hard constraints.
- Status: remains **contaminated for clean OOS claims** because it is part of the same historical snapshot.

### Reserve-internal data (internal only, not forward)
- **reserve_internal**: `2024-10-01T00:00:00Z` → `2026-03-18T23:59:59.999Z`
- Constitutional role: additional internal evidence inside the same frozen snapshot.
- Session outcome: no reserve_internal runs were executed because zero configs survived D1e1 hard constraints.
- Status: remains **contaminated for clean OOS claims** because it is part of the same historical snapshot.

## Forward-evidence boundary

No clean forward evidence exists yet.

There is no appended post-freeze delta window, no forward evaluation ledger rows, and no forward daily returns. Any future clean evidence must come from genuinely appended market data **after** `2026-03-18T23:59:59.999Z` and be recorded in the forward evaluation ledger.
