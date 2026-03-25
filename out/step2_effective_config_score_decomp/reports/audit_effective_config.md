# Effective config audit

## Status

- Unknown keys: **PASS**
- Unused fields: **FAIL**

- Candidate unused count: `1`
- Baseline unused count: `0`
- Candidate unused fields: `emdd_ref_mode`

## Top diffs (baseline vs candidate)

| param | baseline | candidate | baseline_source | candidate_source |
|---|---:|---:|---|---|
| strategy.emergency_dd_pct | 0.28 | 0.04 | default | yaml |
| strategy.name | v8_apex | v12_emdd_ref_fix | yaml | yaml |
