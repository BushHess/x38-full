# Deployment Decision — E5_ema21D1

**Date**: 2026-03-17
**Authority**: Tier 3 (Human Researcher)
**Machine verdict**: AUTO_HOLD (Tier 2, `decision.json`)
**This document**: Final deployment authority per 3-tier model

---

## Section 1: Machine Evidence Summary

### Tier 2 — Production Pipeline (`full_eval_e5_ema21d1_20260317`)

| Gate | Type | Result | Detail |
|------|------|--------|--------|
| lookahead | hard | PASS | Zero violations |
| data_integrity | hard | PASS | Clean data |
| full_harsh_delta | hard | PASS | +26.53 (threshold ≥ -0.2) |
| holdout_harsh_delta | hard | PASS | +5.58 (threshold ≥ -0.2) |
| invariants | hard | PASS | Zero violations |
| **wfo_robustness** | **soft** | **FAIL** | Wilcoxon p=0.125 > 0.10; CI [-3.44, 29.28] crosses zero |
| selection_bias | soft | PASS | Method OK, PBO OK |
| bootstrap | info | — | P(E5>E0)=97.2%, CI [-0.006, +0.398] |
| PSR | info | — | 1.000 (diagnostic only) |

**Machine verdict**: AUTO_HOLD — single soft gate failure (wfo_robustness).

### WFO Underresolution Analysis

| Evidence | Value | Interpretation |
|----------|-------|----------------|
| Wilcoxon p (greater) | 0.125 | 1 rank step from passing (W+=27, need 28) |
| Mean OOS delta | +12.46 | Positive (candidate better on average) |
| Positive windows | 5/8 (62.5%) | Majority positive |
| Bootstrap CI lower | -3.44 | Slightly negative, crosses zero |
| Alternative WFO designs | 2/3 pass (x36) | Fail is design-sensitive, not robust |

**Classification**: Underresolved (insufficient OOS power), not negative-confirmed.

### Full Performance Profile (harsh, 50 bps RT)

| Metric | E5_ema21D1 | E0 Baseline | Delta |
|--------|------------|-------------|-------|
| Sharpe | 1.4545 | 1.2653 | +0.189 |
| CAGR | 61.60% | 52.04% | +9.56pp |
| MDD | 40.97% | 41.61% | -0.64pp |
| Trades | 188 | 192 | -4 |
| Win Rate | 42.02% | 38.02% | +4.00pp |
| Profit Factor | 1.652 | 1.506 | +0.146 |

### At Measured Cost (17 bps RT, X33)

| Metric | Value |
|--------|-------|
| Sharpe | ~1.67 |
| CAGR | ~75% |
| Churn filter needed? | No (crossover ~35 bps > measured 17 bps) |
| Breakeven cost | >999 bps RT |

### Tier 1 — Research Candidates (for context)

| Strategy | Authority | Verdict | Sharpe | Note |
|----------|-----------|---------|--------|------|
| X14_D | Research | SCREEN_PASS_D | 1.530 | Overlay on E0. Cost crossover ~70 bps. Skip at 17 bps. |
| X18 α=50% | Research | SCREEN_PASS | 1.548 | Overlay on E0. Cost crossover ~35 bps. Skip at 17 bps. |
| X28 Cand01 | Research | SCREEN_PASS | 1.251 | From-scratch. Inferior to E5 on all metrics. |

None of these are production-validated. X18 is the only candidate worth
future productionization (if cost rises above 35 bps).

---

## Section 2: Human Review Note

**Decision**: DEPLOY (with guardrails)

**Reasoning**:

E5_ema21D1 should deploy because the evidence overwhelmingly favors it, the single
soft gate failure is a statistical power problem, and the alternative (doing nothing)
has no evidential basis.

1. **Directional evidence is unambiguous.** Bootstrap P(E5>E0) = 97.2% across
   2000 resampled paths (Section 1, line 23). Holdout delta = +5.58 (line 19).
   PSR = 1.000 (line 24). Trade-level bootstrap P(delta>0) = 95.0%. All point
   the same direction — E5 is better than E0 — with no contradictory signal.

2. **WFO FAIL is a power issue, not a signal issue.** Wilcoxon p=0.125 with
   W+=27 (need 28) — one rank step short. Mean OOS delta = +12.46 (positive).
   5/8 windows positive. x36 shows 2/3 alternative WFO designs pass — the fail
   is design-sensitive. With n=8 and ΔSharpe ~0.19, the exact Wilcoxon test has
   low power: it cannot confirm, but it also provides zero evidence against.

3. **No better alternative exists.** 71 studies exhaustively searched. X28
   from-scratch discovery (Sh 1.251) < E5 (Sh 1.455). All 22+ rejected
   alternatives are strictly worse. Churn filters (X14/X18) hurt at measured
   cost of 17 bps. DEFER means running E0 (Sh 1.265), losing +0.189 Sharpe
   with no evidential justification.

4. **E5 dominates E0 across all regimes.** Regime decomposition (comprehensive
   report Section 2.5): E5 wins all 6 regimes including BEAR (+1.538 vs +1.506)
   and SHOCK (-2.251 vs -2.677). There is no regime where E0 is preferred.

5. **Cost robustness is extreme.** Breakeven >999 bps RT. At measured 17 bps:
   Sharpe ~1.67, CAGR ~75%. Strategy remains profitable at costs 50x higher
   than measured.

**Risk assessment**:

| Risk | Severity | Mitigation |
|------|----------|------------|
| MDD 40.97% (harsh) | High | Position sizing f=0.30 (vol-target 15%). Real MDD lower at 17 bps. Drawdown kill switch at 55%. |
| WFO underresolution later proves negative | Low | No evidence of negative signal. 5/8 positive, mean delta positive. Would require future data to flip 3+ windows negative simultaneously. |
| Regime Monitor V2 unstable (WFO 2/8) | Medium | Monitor is entry-prevention only (not exit-forcing). Conservative: activate at lower thresholds or disable entirely. Does not affect core E5 logic. |
| Cost spike during drawdown shocks | Medium | X33 measured P75 = 19 bps even during volatility. If cost consistently > 35 bps, arm X18. Cost monitors in execution layer. |
| Execution slippage above backtest model | Low | Median measured 16.8 bps vs 50 bps harsh assumption. 3x safety margin. |

**Conditions / guardrails**:

1. **Kill switch**: Flatten and halt if live equity drawdown exceeds 55% from
   peak (above backtest MDD of 40.97% by ~14pp margin).
2. **Position sizing**: f=0.30 (vol-target 15%), no leverage. Max exposure
   per `RiskConfig.max_total_exposure`.
3. **Cost monitoring**: Track per-trade execution cost. If 30-day median
   exceeds 35 bps RT, arm X18 churn filter per X33 decision.
4. **Regime monitor**: Run V2 in advisory mode (log, don't block). Status
   UNCERTAIN — do not give it veto power until WFO instability is resolved.
5. **LT1 SLA**: ≤4h restart SLA required (per LATENCY_TIER_DEPLOYMENT_GUIDE).
   If SLA cannot be met, fall back to E0_ema21D1 (LT2).
6. **Review cadence**: Re-evaluate after 6 months of live data (≈1 additional
   WFO window). If live performance inconsistent with backtest, trigger
   full pair review.

**Unresolved concerns**:

1. **WFO reform (x36)**: Pending. Would add `evidence_state: underresolved`
   field. Semantic fix — does not change thresholds or verdict logic.
   Low priority since Tier 3 decision supersedes Tier 2 for deployment.
2. **Regime Monitor V2**: Status UNCERTAIN (WFO 2/8 instability). Promising
   mechanism but temporally unstable. Run advisory-only, not blocking.
3. **X18 productionization**: Not needed at 17 bps. If cost rises, would
   need: port to `strategies/`, register in STRATEGY_REGISTRY, rebase on
   E5 (not E0), run production pipeline. Estimate: 1-2 days integration work.
4. **Live vs backtest divergence**: Backtest uses next-open fill assumption.
   First 20 trades should be manually verified against fill prices.

---

## Decision Options

| Decision | Meaning |
|----------|---------|
| **DEPLOY** | Run live with specified guardrails. E5_ema21D1 is the best available strategy. |
| **SHADOW** | Run in shadow mode (paper trade alongside manual). Collect live data for future WFO resolution. |
| **DEFER** | Wait for specific condition (e.g., WFO reform, more OOS data, X18 productionization). |
| **REJECT** | Do not deploy. Specific reason required. |

---

*Template version: 2026-03-17 | Per 3-tier authority model (STRATEGY_STATUS_MATRIX.md)*
