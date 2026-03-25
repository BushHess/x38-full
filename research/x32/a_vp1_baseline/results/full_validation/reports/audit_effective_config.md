# Effective config audit

## Status

- Unknown keys: **PASS**
- Unused fields: **FAIL**

- Candidate unused count: `1`
- Baseline unused count: `0`
- Candidate unused fields: `warmup_days`

## Top diffs (baseline vs candidate)

| param | baseline | candidate | baseline_source | candidate_source |
|---|---:|---:|---|---|
| strategy.atr_period | 14 | 20 | default | default |
| strategy.name | vtrend | vtrend_vp1 | yaml | yaml |
| strategy.slow_period | 120.0 | 140.0 | yaml | yaml |
| strategy.trail_mult | 3.0 | 2.5 | yaml | yaml |
