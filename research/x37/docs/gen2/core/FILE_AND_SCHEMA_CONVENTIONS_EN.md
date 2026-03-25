# File and Schema Conventions

## Canonical folder structure

Use one folder per historical snapshot:

```text
snapshot_YYYYMMDD/
  raw/
    spot_btcusdt_15m.csv
    spot_btcusdt_1h.csv
    spot_btcusdt_4h.csv
    spot_btcusdt_1d.csv
  manifest/
    session_manifest.json
    snapshot_notes.md
    input_hash_manifest.txt
```

Use one folder per appended forward delta:

```text
delta_YYYYMMDD_to_YYYYMMDD/
  raw/
    spot_btcusdt_15m.csv
    spot_btcusdt_1h.csv
    spot_btcusdt_4h.csv
    spot_btcusdt_1d.csv
  manifest/
    session_manifest.json
    input_hash_manifest.txt
```

## Canonical CSV schema

All research files must be canonicalized into this exact 13-column schema before any modeling:

1. `symbol`
2. `interval`
3. `open_time`
4. `close_time`
5. `open`
6. `high`
7. `low`
8. `close`
9. `volume`
10. `quote_volume`
11. `num_trades`
12. `taker_buy_base_vol`
13. `taker_buy_quote_vol`

### Type expectations
- `symbol`: string, expected `BTCUSDT`
- `interval`: string, one of `15m`, `1h`, `4h`, `1d`
- `open_time`: integer milliseconds since Unix epoch, UTC
- `close_time`: integer milliseconds since Unix epoch, UTC
- market-value columns: parse as decimal-capable floating-point numbers
- `num_trades`: integer

### Time semantics
- All timestamps are UTC.
- Do not infer local time zones.
- `open_time` is inclusive.
- `close_time` is the exchange-reported close timestamp.

## Canonicalization from raw Binance kline exports

Raw Binance kline exports often carry fields in this order:

```text
open_time, open, high, low, close, volume, close_time,
quote_asset_volume, number_of_trades,
taker_buy_base_asset_volume, taker_buy_quote_asset_volume,
ignore
```

Canonicalization rules:
- inject `symbol`,
- inject `interval`,
- rename quote / taker fields into the canonical schema above,
- drop the unused final `ignore` field if present,
- preserve all rows exactly as supplied except where the active constitution or session protocol explicitly allows a deterministic drop.

## Sorting and uniqueness

Base ordering:
1. sort by `open_time`,
2. if tied, retain stable original file order.

Do not collapse duplicates unless the active protocol explicitly allows one deterministic drop rule.

## Session manifest schema

Each session must carry `session_manifest.json` with these top-level fields:
- `lineage_id`
- `session_id`
- `mode`
- `constitution_file`
- `constitution_version`
- `snapshot_id`
- `state_pack_input`
- `input_files`
- `warmup_buffer_files`
- `appended_delta_window`
- `forbidden_inputs_confirmed_absent`
- `contamination_status`
- `hash_manifest_file`
- `notes`

The provided JSON template uses this exact shape.

## Raw file hygiene

- Keep raw files immutable.
- Never rewrite original raw files after a session.
- If you canonicalize, treat it as a deterministic ingestion step and record it.
- Always record file hash, file size, and line count in `input_hash_manifest.txt` or `snapshot_notes.md`.

## Warmup buffers

Forward evaluation may require warmup history to compute rolling features or reconstruct deterministic state.

Warmup rules:
- warmup data may come from the latest state pack,
- warmup data does not count as new forward evidence,
- warmup data must precede the appended evaluation window,
- warmup data must not trigger redesign.

## Session output naming

Use one folder or archive per completed session:

```text
state_pack_vN/
  research_constitution_version.txt
  lineage_id.txt
  session_summary.md
  candidate_registry.json
  meta_knowledge_registry.json
  portfolio_state.json
  historical_seed_audit.csv
  forward_evaluation_ledger.csv
  contamination_map.md
  input_hash_manifest.txt
  frozen_system_specs/
  warmup_buffers/
```

A zipped form is acceptable:

```text
state_pack_vN.zip
```

## Human-only reminder

`README_EN.md`, `USER_GUIDE_VI.md`, `PROMPT_INDEX_EN.md`, `UPLOAD_MATRIX_EN.md`, and `KIT_REVIEW_AND_FIXLOG_EN.md` are not part of the canonical research input set unless explicitly needed for troubleshooting.
