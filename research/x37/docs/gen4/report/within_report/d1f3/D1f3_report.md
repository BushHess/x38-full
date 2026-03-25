# D1f3 Report — Audit, Contamination Map & Packaging Readiness

## Seed Discovery Summary

- **D1a** validated the admitted snapshot and canonicalized all 4 raw BTCUSDT timeframes. Data quality passed; gaps were small and confined to warmup/discovery, while holdout and reserve_internal were complete.
- **D1b** measured channels before mechanism design. The strongest independent blocks were slow trend / anti-vol structure on 1d + 4h, plus activity/timing on 15m. Daily gaps were noise; blind 1h → 15m continuation stacking was weak.
- **D1c** produced 3 candidates / 30 configs within all hard caps.
- **D1d** ran full quarterly expanding WFO on discovery plus ablation diagnostics. `btcsd_20260318_c1_av4h` and `btcsd_20260318_c3_trade4h15m` survived discovery hard constraints; `btcsd_20260318_c2_flow1hpb` did not.
- **D1e** selected the final ranking, ran holdout / reserve / bootstrap, then **D1f** froze:
  - **Champion:** `btcsd_20260318_c3_trade4h15m`
  - **Challenger:** `btcsd_20260318_c1_av4h`
  - `btcsd_20260318_c2_flow1hpb` retired pre-freeze
- No clean forward evidence exists yet. Both live candidates remain labeled `INTERNAL_SEED_CANDIDATE`.

## Historical Seed Audit

Created: `historical_seed_audit.csv`

**Audit coverage:**

- 12 rows
- 2 live candidates × 3 segments × 2 cost levels
- Segments covered:
  - discovery — 2020-01-01 to 2023-06-30
  - holdout — 2023-07-01 to 2024-09-30
  - reserve_internal — 2024-10-01 to 2026-03-18
- Costs covered: 20 and 50 bps RT

**Included fields:**

- segment metrics: cagr, sharpe, max_drawdown, entries, exit_count, final_position_state, exposure
- daily_returns_hash
- bootstrap_lb5_mean_daily_return for discovery rows
- selected_in_state_pack

**Hash method used:**

- round each daily return to 8 decimals
- write one value per line, newline-separated
- SHA-256 of the resulting string

**Scope note:**

- The audit covers the two frozen live candidates.
- `btcsd_20260318_c2_flow1hpb` is documented in `candidate_registry.json` as retired pre-freeze, but it is not in the per-segment state-pack audit because it had no frozen representative config and was not selected into the state pack.

**Also created:**

- `forward_evaluation_ledger.csv` — header only, no data rows yet

## Contamination Map

Created: `contamination_map.md`

**Summary:**

| Field | Value |
|---|---|
| `snapshot_id` | snapshot_20260318 |
| Snapshot coverage | 2017-08-17 to 2026-03-18 UTC |

**Seed discovery / candidate mining used:**

- warmup through 2019-12-31
- discovery through 2023-06-30

**Holdout used:**

- 2023-07-01 to 2024-09-30
- internal validation only, not clean forward evidence

**Reserve_internal used:**

- 2024-10-01 to 2026-03-18
- internal evidence / terminal-state construction only, not clean forward evidence

**Explicit status:**

- No clean forward evidence exists yet
- next clean evidence begins only after `freeze_cutoff_utc = 2026-03-18T23:59:59.999000+00:00`

**Current frozen system version prepared for packaging:**

- `system_version_id` = V1
- state pack format target: `state_pack_v1`

## Complete File Inventory

**Ready from D1f1–D1f3:**

- `frozen_system_specs/btcsd_20260318_c3_trade4h15m.md`
- `frozen_system_specs/btcsd_20260318_c1_av4h.md`
- `candidate_registry.json`
- `meta_knowledge_registry.json`
- `portfolio_state.json`
- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `contamination_map.md`

**Earlier D1 files that D2 should package as implementations:**

- `d1d_impl_btcsd_20260318_c3_trade4h15m.py` → package as `impl/btcsd_20260318_c3_trade4h15m.py`
- `d1d_impl_btcsd_20260318_c1_av4h.py` → package as `impl/btcsd_20260318_c1_av4h.py`

**Files D2 will generate during packaging, not created here:**

- `research_constitution_version.txt`
- `program_lineage_id.txt`
- `system_version_id.txt`
- `system_version_manifest.json`
- `session_summary.md`
- `forward_daily_returns.csv` (header only at packaging time)
- `input_hash_manifest.txt`
- `warmup_buffers/` (if needed per `portfolio_state.json` warmup requirements)

## Files Created

- `historical_seed_audit.csv`
- `forward_evaluation_ledger.csv`
- `contamination_map.md`

---

D1f3 complete. **Ready for D2.**
