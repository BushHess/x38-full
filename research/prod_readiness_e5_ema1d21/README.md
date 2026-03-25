# prod_readiness_e5_ema1d21 — Production Readiness Evaluation

## Purpose

Evaluate production-readiness of E5+EMA1D21 (robust ATR trail + D1 EMA(21) regime
filter) through three complementary studies:

1. **Regime Monitor** — MDD-based runtime bear-market detector overlay
2. **E5S Validation** — can we simplify E5 robust ATR to standard ATR(20)?
3. **DOF Correction** — how statistically significant is E5 vs X0 after
   correcting for correlated timescales?

## Date

2026-03-09 (studies run 2026-03-08 to 2026-03-09)

## Results Summary

| Study | Verdict | Key Finding |
|-------|---------|-------------|
| Regime Monitor V1 | **REJECTED** | Raw ATR structurally broken (71.6% false RED rate) |
| Regime Monitor V2 | **PROMOTED** | MDD-only, Sharpe +0.118, CAGR +5.3%, 2022 bear detected, ≤2 false RED |
| E5S Validation | **KEEP E5** | E5S loses 0.088 Sharpe vs E5; does not qualify as simplification |
| DOF Correction | **SUGGESTIVE** | E5 vs X0: Nyholt p=0.063, effect +0.089 Sharpe at ALL 16 timescales |

## File Map

### Final (production-quality)

| File | Purpose |
|------|---------|
| `regime_monitor_v2.py` | MDD-only regime monitor — **PROMOTED to `monitoring/regime_monitor.py`** |
| `e5s_validation.py` | E5S simplification study (conclusive: E5 wins) |
| `e5_dof_correction.py` | Effective DOF correction for 16-timescale binomial tests |
| `test_x0a.py` | Unit tests for regime monitor V1 helpers (rolling MDD, classify, episodes) |
| `test_e5s.py` | Unit tests for E5S validation |

### Rejected

| File | Reason |
|------|--------|
| `rejected/regime_monitor_v1_REJECTED.py` | Raw ATR channel structurally broken; replaced by V2. Kept for audit trail and V2 helper imports. |

### Output artifacts

| File | Content |
|------|---------|
| `X0A_REGIME_MONITOR_REPORT.md` | V1 diagnostic report (documents why V1 failed) |
| `X0A_REGIME_MONITOR_V2_REPORT.md` | V2 evaluation report |
| `E5S_VALIDATION_REPORT.md` | E5S vs E5 comparison report |
| `E5_DOF_CORRECTION_REPORT.md` | M_eff DOF correction analysis |
| `x0a_results.json` | V1 raw results |
| `x0a_v2_results.json` | V2 raw results |
| `e5s_validation_results.json` | E5S raw results |
| `x0a_episode_summary.csv` | Episode timeline data |
| `x0a_monitor_signals.csv` | Daily monitor signal values |

## Dependencies

- `v10.core.data.DataFeed`, `v10.core.types.SCENARIOS`
- `research.lib.effective_dof` (M_eff corrections)
- `research.lib.vcbb` (bootstrap)
- `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (project root)
