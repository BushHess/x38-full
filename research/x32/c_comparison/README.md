# Branch C — VP1 Family vs E5+EMA1D21 Final Comparison

## Status: COMPLETE (2026-03-12)

**Decision: E5+EMA1D21 remains PRIMARY. No VP1 variant achieves PROMOTE.**

## Results Summary

| Strategy | Sharpe | CAGR % | MDD % | Trades | Verdict | Failure |
|----------|--------|--------|-------|--------|---------|---------|
| VP1 | 1.452 | 61.7 | 40.5 | 194 | ERROR | Holdout FAIL |
| VP1-E5exit | 1.488 | 62.5 | 36.6 | 213 | ERROR | Holdout FAIL |
| VP1-FULL | 1.461 | 62.0 | 41.0 | 187 | ERROR | WFO FAIL |
| E5+EMA1D21 | 1.430 | 59.9 | 41.6 | 186 | **PROMOTE** | — |

All metrics: harsh (50 bps RT), validation window 2019-01 → 2026-02.

## Key Findings

1. **VP1 variants beat E5+EMA1D21 on full-sample** but fail OOS validation
2. **RATR is the most valuable single change**: VP1-E5exit gets -3.88 pp MDD, +0.036 Sharpe
3. **VP1 parameter set (slow=140, trail=2.5, d1_ema=28) overfits earlier regimes**
4. **E5 parameter set (slow=120, trail=3.0, d1_ema=21) more robust OOS**
5. **VP1 structural features (prevday D1, per-bar VDO) add genuine value** but not enough to overcome parameter fragility

## Evaluation Protocol
1. Same data window (2019-01 → 2026-02, warmup 365d)
2. Same cost assumptions (50 bps RT harsh)
3. All evaluated against common E0 (vtrend) baseline
4. Full validation pipeline (17 suites, --suite all)
5. WFO 8-fold rolling, Wilcoxon signed-rank
6. Bootstrap (VCBB N=2000), paired equity
7. Holdout 20%, PSR, regime, cost sweep, trade-level

## Decision Framework
- VP1 variant PROMOTES only if it passes ALL gates vs E0 baseline
- If no VP1 variant beats E5+EMA1D21 → E5+EMA1D21 remains primary
- Result: **E5+EMA1D21 is the only PROMOTE**

## Detailed Report
See `results/comparison_report.md` for full analysis including:
- Delta decomposition (structure vs parameters)
- WFO window-by-window analysis
- Regime decomposition
- Cost sensitivity
- Holdout analysis
