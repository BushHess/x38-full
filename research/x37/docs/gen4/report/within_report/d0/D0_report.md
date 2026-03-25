# D0 Report

## 1. Mode Confirmation

- Seed discovery session confirmed. `mode = seed_discovery`, `lineage_type = mainline`, `state_pack_input = null`, `system_version_id = null`. Precheck only; no strategy search or scoring has been run. *(session_manifest.json:L4-L11)*
- Constitution file is readable and present as `research_constitution_v4.0.yaml`; manifest points to version 4.0, and the hash manifest records the file in the bundle. *(session_manifest.json:L6-L7; input_hash_manifest.txt:L11-L13)*
- Snapshot confirmed: `snapshot_id = snapshot_20260318`. Admitted raw inputs are BTCUSDT 15m, 1h, 4h, 1d. Declared snapshot coverage is 2017-08-17 to 2026-03-18 UTC, consistent with `snapshot_id` semantics. *(session_manifest.json:L10-L16,L40; FILE_AND_SCHEMA_CONVENTIONS_EN.md:L52-L64,L115-L124; input_hash_manifest.txt:L3-L17)*
- Historical-seed protocol windows are fixed as: warmup through 2019-12-31, discovery 2020-01-01 to 2023-06-30, holdout 2023-07-01 to 2024-09-30, reserve internal 2024-10-01 to snapshot_end. *(research_constitution_v4.0.yaml:L447-L484)*

## 2. Admissible Input Audit

**Used:**

- `research_constitution_v4.0.yaml`
- `FILE_AND_SCHEMA_CONVENTIONS_EN.md`
- `session_manifest.json`
- `input_hash_manifest.txt`
- `spot_btcusdt_15m.csv`
- `spot_btcusdt_1h.csv`
- `spot_btcusdt_4h.csv`
- `spot_btcusdt_1d.csv`

**Present but inadmissible for blind discovery:**

- None detected inside the uploaded bundle.

**Optional admissible file status:**

- `snapshot_notes.md` not present.

**Schema check:**

- Canonical 13-column CSV schema is the required format, and the bundle declares all four raw files under that convention. *(FILE_AND_SCHEMA_CONVENTIONS_EN.md:L34-L64; session_manifest.json:L12-L16,L40; input_hash_manifest.txt:L14-L17)*

## 3. Contamination Status

- The historical snapshot is candidate-mining-only. *(research_constitution_v4.0.yaml:L447-L454)*
- No clean external OOS claim may be made from this snapshot.
- Internal holdout and reserve windows remain contaminated for discovery purposes.
- Clean OOS evidence can only come from appended data strictly after a frozen version's `freeze_cutoff_utc`. *(research_constitution_v4.0.yaml:L633-L636; research_constitution_v4.0.yaml:L707-L711)*

## 4. Execution Boundaries

### Search-space philosophy

- Open mathematical, measurement-first, raw-data-first.
- No predefined indicator vocabulary or fixed architecture.
- Any causal scalar function of the admitted data surface is allowed, subject to the complexity budget and no-lookahead rule. *(research_constitution_v4.0.yaml:L563-L603)*

### Hard caps

| Parameter | Limit |
|---|---|
| max live seeds after discovery | 3 |
| max challengers | 2 |
| max logical layers per candidate | 3 |
| max tunable quantities per candidate | 4 |
| max discovery configs per candidate | 20 |
| max total seed configs | 60 |

*(research_constitution_v4.0.yaml:L604-L619)*

### Hard constraints

**Causal/data:** no lookahead, no incomplete higher-TF leakage, no non-admitted data, no tick/order-book dependence, no discovery-period ML weights. *(research_constitution_v4.0.yaml:L589-L593; research_constitution_v4.0.yaml:L715-L721)*

**Execution:** spot long-only or long-flat; binary 0% / 100% notional; no leverage; no pyramiding; no regime-specific parameter sets; no discretionary overrides. *(research_constitution_v4.0.yaml:L541-L561)*

**Objective gates:**

| Gate | Threshold |
|---|---|
| CAGR_50bps | > 0 |
| MDD_50bps | ≤ 0.45 |
| entries/year | [6, 80] |
| exposure | [0.15, 0.90] |
| bootstrap LB5 mean daily return | > 0 |

*(research_constitution_v4.0.yaml:L486-L505)*

### Required outputs

- one champion seed or `NO_ROBUST_CANDIDATE`
- up to two challengers only if a champion exists
- `system_version_id`
- frozen system specs
- candidate registry
- meta-knowledge registry
- portfolio state
- `historical_seed_audit.csv`
- empty `forward_evaluation_ledger.csv`
- contamination map
- packaged `state_pack_v1`

*(research_constitution_v4.0.yaml:L621-L636; research_constitution_v4.0.yaml:L758-L760)*

## 5. Go / No-Go

### ✅ GO FOR D1

**Basis:**

- admissible inputs are present and sufficient
- constitution is readable
- manifest is coherent with seed discovery mode
- canonical raw files exist for all four required timeframes
- no inadmissible blind-discovery artifacts were found in the uploaded bundle

*(session_manifest.json:L4-L40; FILE_AND_SCHEMA_CONVENTIONS_EN.md:L92-L124; input_hash_manifest.txt:L11-L17)*
