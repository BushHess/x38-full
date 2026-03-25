# data/ — Flat sample for quick-start

This directory contains a flat example of session inputs for convenience.

For actual execution, use the canonical layout defined in `FILE_AND_SCHEMA_CONVENTIONS_EN.md`:

```text
snapshot_YYYYMMDD/
  raw/
    spot_btcusdt_15m.csv
    spot_btcusdt_1h.csv
    spot_btcusdt_4h.csv
    spot_btcusdt_1d.csv
  manifest/
    session_manifest.json
    input_hash_manifest.txt
    snapshot_notes.md
```
