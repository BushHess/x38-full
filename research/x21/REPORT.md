# X21: Conviction-Based Position Sizing — REPORT

**Date**: 2026-03-10
**Script**: `research/x21/benchmark.py`
**Verdict**: **CLOSE** — ABORT at T-1 (entry features cannot predict trade returns)

---

## Executive Summary

Entry-time observable features (VDO, EMA spread, ATR percentile, D1 regime strength)
cannot predict trade-level returns with sufficient information coefficient to justify
variable position sizing. Cross-validated IC = -0.039, well below the 0.05 abort
threshold. The study was correctly aborted before any sizing experiments.

**Key finding**: Entry prediction is fundamentally harder than exit prediction.
At entry, only market-state features are available. The churn model (X13-X14)
succeeds at AUC=0.805 because it operates at EXIT time with trade-context features.
Entry features have no predictive power over trade returns.

---

## T-1: IC Measurement (Abort Gate)

### Full-Sample Results

| Feature | IC (Spearman) | p-value |
|---------|---------------|---------|
| vdo_value | 0.083 | 0.247 |
| ema_spread | -0.073 | 0.307 |
| atr_pctl | -0.023 | 0.747 |
| d1_regime_str | 0.035 | 0.625 |
| **Full model** | **0.103** | **0.149** |
| **CV mean** | **-0.039** | — |

### Interpretation

- **No individual feature is statistically significant** (all p > 0.20)
- Full-sample IC = 0.103 looks marginal but p=0.149 (not significant at any standard α)
- **Cross-validated IC = -0.039** — negative, meaning the full-sample IC is entirely
  due to in-sample overfitting
- Top 2 features by |IC|: vdo_value (0.083) and ema_spread (-0.073)
- atr_pctl and d1_regime_str are essentially noise (|IC| < 0.04)

### Why Entry Prediction Fails

1. **Insufficient signal**: VDO > 0 is already used as a binary filter. The continuous
   value above zero carries minimal additional information about trade quality.
2. **EMA spread sign is negative**: Wider spreads (stronger trends) predict *worse*
   trade returns, likely because they enter later in the trend and capture less upside.
3. **ATR percentile is non-predictive**: Volatility regime at entry has no meaningful relationship
   with trade returns (IC = -0.023, not significant).
4. **D1 regime strength is non-predictive**: How far above the D1 EMA doesn't predict trade quality.
5. **Sample size**: 199 trades is marginal for a 4-feature model. CV IC going negative
   confirms overfitting on such a small sample.

### Comparison to Churn Model (X13-X14)

| Property | Churn (X14) | Entry (X21) |
|----------|-------------|-------------|
| Prediction timing | EXIT (trail breach) | ENTRY (signal bar) |
| Features available | 7 (incl. trade context) | 4 (market state only) |
| AUC / IC | 0.805 (p=0.002) | 0.103 (p=0.149) |
| CV performance | Stable | **Negative** (-0.039) |
| Sample per class | ~100 churn, ~100 genuine | 199 continuous targets |
| Task | Binary classification | Continuous regression |

The churn model succeeds because:
- It operates at a **decision point** (trail breach) where the market structure
  has already revealed information about the trade
- It has access to **trade-context features** (bars held, drawdown from peak)
  that are powerful predictors of whether a stop-out is churn

Entry prediction lacks both advantages.

---

## Baseline Performance

The E5+EMA1D21 baseline with f=0.30 fractional sizing:

| Metric | Value |
|--------|-------|
| Sharpe | 1.434 |
| CAGR | 18.16% |
| MDD | 14.80% |
| Trades | 199 |

Note: This uses fractional position sizing (f=0.30 of NAV per trade) rather than
all-in sizing. The Sharpe and CAGR differ from the standard all-in E5+EMA1D21
baseline because fractional sizing reduces both returns and volatility.

---

## Decision

| Gate | Condition | Result | Status |
|------|-----------|--------|--------|
| ABORT | CV IC < 0.05 | CV IC = -0.039 | **ABORT** |

**CLOSE** — Entry features don't predict trade quality. No further tests warranted.

Per the decision matrix: "IC < 0.05 (T-1) → CLOSE — entry features don't predict
trade quality."

---

## Implications

1. **Fixed sizing is optimal**: f=0.30 for all trades remains the correct approach.
   There is no information at entry time to improve sizing.
2. **Alpha source confirmed**: VTREND's alpha comes from the signal (when to enter)
   and the exit mechanism (how to exit), not from entry quality discrimination.
3. **Kelly theorem doesn't apply**: Kelly-like variable sizing requires IC > 0.
   With IC ≈ 0, variable sizing adds noise without improving geometric growth.
4. **DOF saved**: No additional parameters needed for sizing. The strategy remains
   at 4.35 effective DOF.
