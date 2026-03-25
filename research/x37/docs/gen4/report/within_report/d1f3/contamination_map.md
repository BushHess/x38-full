# Contamination Map

## Snapshot identity
- snapshot_id: `snapshot_20260318`
- snapshot_coverage_utc: `2017-08-17` to `2026-03-18`
- freeze_cutoff_utc: `2026-03-18T23:59:59.999000+00:00`
- evidence_clean_since_utc: `2026-03-19T00:00:00+00:00`

## Internal data usage boundaries

### Seed discovery / candidate mining
- Warmup / calibration window: first available historical bars through `2019-12-31` UTC
- Discovery measurement and WFO window: `2020-01-01` through `2023-06-30` UTC
- These data were used for:
  - D1a ingestion and quality validation
  - D1b channel measurement
  - D1c candidate design and config definition
  - D1d discovery walk-forward evaluation
  - D1e bootstrap and ranking inputs

### Holdout (internal, not forward)
- Holdout window: `2023-07-01` through `2024-09-30` UTC
- Used only for internal post-discovery validation in D1e2
- This window is **not** clean forward evidence because it belongs to the same frozen historical snapshot used in seed discovery.

### Reserve internal (internal, not forward)
- Reserve window: `2024-10-01` through `2026-03-18` UTC
- Used only for additional internal evidence and terminal-state construction in D1e2 / D1f2
- This window is **not** clean forward evidence because it also belongs to the same frozen historical snapshot used in seed discovery.

## Clean-evidence status
- No clean forward evidence exists yet.
- Any evidence after `freeze_cutoff_utc` must be accumulated through the forward evaluation process and written to `forward_evaluation_ledger.csv` and `forward_daily_returns.csv`.
- Therefore all currently frozen candidates carry the evidence label `INTERNAL_SEED_CANDIDATE`.

## State pack target
- system_version_id: `V1`
- latest system freeze prepared for packaging: `V1`
- state pack format target: `state_pack_v1`
