# X35 Phase 0 Data Audit

- Study id: `x35_long_horizon_regime`
- Window: `2019-01-01` -> `2026-02-20`
- Warmup days: `365`

## Feed Coverage

| Series | Total bars | Report bars | First close | Last close |
|--------|------------|-------------|-------------|------------|
| H4 | 17838 | 15648 | 2018-01-01 | 2026-02-20 |
| D1 | 2973 | 2608 | 2018-01-01 | 2026-02-20 |
| W1 | 425 | 373 | 2018-01-07 | 2026-02-20 |
| M1 | 98 | 86 | 2018-01-31 | 2026-02-20 |

## Candidate Warmup Audit

| Spec | Clock | Pre-report bars | Required bars | Warmup |
|------|-------|-----------------|---------------|--------|
| `wk_close_above_ema26` | W1 | 52 | 26 | PASS |
| `wk_ema13_above_ema26` | W1 | 52 | 26 | PASS |
| `mo_close_above_ema6` | M1 | 12 | 6 | PASS |
