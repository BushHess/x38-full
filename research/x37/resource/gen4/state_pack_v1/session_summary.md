# Session Summary

- session_id: `session_20260319_seed_001`
- mode: `seed_discovery`
- program_lineage_id: `btc_spot_mainline_lineage_001`
- constitution_version: `4.0`
- system_version_id: `V1`
- snapshot_id: `snapshot_20260318`
- freeze_cutoff_utc: `2026-03-18T23:59:59.999000+00:00`
- design_inputs_end_utc: `2026-03-18T23:59:59.999000+00:00`
- evidence_clean_since_utc: `2026-03-19T00:00:00+00:00`

## Frozen live set

- champion: `btcsd_20260318_c3_trade4h15m`
- challengers: `btcsd_20260318_c1_av4h`

## Candidate outcomes

- `btcsd_20260318_c3_trade4h15m`: champion; passed discovery hard constraints, passed holdout hard constraints, bootstrap LB5 > 0.
- `btcsd_20260318_c1_av4h`: challenger; passed discovery hard constraints, failed holdout activity/exposure hard constraints, retained as challenger only.
- `btcsd_20260318_c2_flow1hpb`: retired pre-freeze; no representative config survived discovery hard constraints and no eligible post-ablation simplification passed constraints.

## Evidence status

- All frozen candidates carry evidence label `INTERNAL_SEED_CANDIDATE`.
- Holdout and reserve_internal are internal validation only; no clean forward evidence exists yet.
- The first clean forward bar for V1 is the bar immediately after the freeze cutoff.

## Packaging notes

- `input_hash_manifest.txt` is copied unchanged from the admitted session input bundle.
- `warmup_buffers/` is included because live candidates are reconstructable from warmup only and require nonzero rolling-history buffers.
- `impl/` contains convenience implementation artifacts; frozen specs remain authoritative.
