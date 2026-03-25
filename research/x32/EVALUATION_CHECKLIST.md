# X32 Evaluation Checklist

Standard evaluation protocol for all VP1 family strategies.
Every variant MUST complete ALL items before reporting results.

## Pipeline Command Template

```bash
python validate_strategy.py \
  --strategy STRATEGY_NAME \
  --baseline vtrend \
  --config configs/STRATEGY_NAME/STRATEGY_NAME_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out research/x32/BRANCH/results/STRATEGY_NAME_validation \
  --suite all \
  --harsh-cost-bps 50 \
  --wfo-windows 8 \
  --bootstrap 2000 \
  --force
```

## 17 Validation Suites (--suite all)

| # | Suite | Description | Gate |
|---|-------|-------------|------|
| 1 | data_integrity | Missing bars, gaps, warmup coverage | Hard |
| 2 | lookahead | Config access audit (no future data) | Hard |
| 3 | backtest | Full-history 3 scenarios (smart/base/harsh) | Core |
| 4 | wfo | Walk-forward 8-fold rolling, Wilcoxon signed-rank | G1: ≥50% win |
| 5 | bootstrap | VCBB paired equity bootstrap (N=2000, blocks 10/20/40) | G2: P(d>0) ≥ 55% |
| 6 | holdout | 20% holdout split, delta direction | Soft |
| 7 | subsampling | Jackknife stability (leave-one-year-out) | Soft |
| 8 | sensitivity | Parameter perturbation ±10% around defaults | Soft |
| 9 | selection_bias | Deflated Sharpe Ratio (PSR) | G3: PSR ≥ 0.95 |
| 10 | trade_level | Trade-level block bootstrap (N=10000) | Info |
| 11 | dd_episodes | Drawdown episode analysis | Info |
| 12 | regime | Bull/bear/sideways performance decomposition | Info |
| 13 | cost_sweep | Performance across 0-100 bps cost range | Info |
| 14 | invariants | Deterministic invariant checks | Hard |
| 15 | overlay | Overlay/conditional test | Info |
| 16 | churn_metrics | Fee drag, cascade analysis | Info |
| 17 | regression_guard | Golden file comparison (if golden exists) | Conditional |

## Hard Gates (must ALL pass for PROMOTE)

| Gate | Condition | Source |
|------|-----------|--------|
| G0 | Full-sample Δ(Sharpe) > 0 vs baseline (harsh) | backtest |
| G1 | WFO win rate ≥ 50% | wfo |
| G2 | Bootstrap P(d_sharpe > 0) ≥ 55% | bootstrap |
| G3 | PSR ≥ 0.95 (DOF-corrected) | selection_bias |

## Soft Gates (reported, not blocking)

| Gate | Condition | Source |
|------|-----------|--------|
| S1 | Holdout Δ(Sharpe) > 0 | holdout |
| S2 | JK stability: 0/N negative folds | subsampling |
| S3 | Sensitivity: ≥80% grid cells positive | sensitivity |
| S4 | Trade count ≥ low_trade_threshold | backtest |

## Verdict Rules

| Outcome | Condition |
|---------|-----------|
| PROMOTE | ALL hard gates PASS |
| HOLD | At least 1 hard gate FAIL, but direction positive |
| REJECT | Direction negative or multiple failures |

## Additional Analysis (per-variant)

Beyond the automated pipeline, each variant report should include:

### From Branch A baseline results
- [x] Acceptance tests (VP1 only — spec §13)
- [x] 3-scenario backtest table (smart/base/harsh)
- [x] Bootstrap CI table (Sharpe, CAGR, MDD with 95% CI)
- [x] Trade structure (win/loss count, avg winner/loser, top-5 concentration)
- [x] Exit type breakdown (trailing stop vs trend reversal %)
- [x] Average exposure and holding period

### From full validation pipeline (--suite all)
- [ ] WFO fold-by-fold results with Wilcoxon p-value
- [ ] Holdout split results
- [ ] PSR value (DOF-corrected)
- [ ] Bootstrap P(d>0) for Sharpe, CAGR, MDD
- [ ] Jackknife LOYO stability
- [ ] Regime decomposition (bull/bear/sideways Sharpe)
- [ ] Cost sweep table (breakeven cost)
- [ ] Churn metrics (fee drag %, cascade distribution)
- [ ] Trade-level bootstrap (N=10000)
- [ ] Drawdown episode analysis

### For comparison (Branch C)
- [ ] Side-by-side table: VP1 vs VP1-E5exit vs VP1-FULL vs E5+EMA1D21
- [ ] Delta decomposition: which changes contribute how much
- [ ] Paired bootstrap between variants
- [ ] Decision matrix with all gates

## Strategy Registry

| Name | Config Location | Key Changes vs VP1 |
|------|----------------|-------------------|
| vtrend_vp1 | configs/vtrend_vp1/ | Baseline (frozen spec v1.1) |
| vtrend_vp1_e5exit | configs/vtrend_vp1_e5exit/ | RATR exit only |
| vtrend_vp1_full | configs/vtrend_vp1_full/ | RATR + slow=120 + trail=3.0 + d1_ema=21 |
| vtrend_e5_ema21_d1 | configs/vtrend_e5_ema21_d1/ | Reference (current primary) |
| vtrend | configs/vtrend/ | E0 baseline (shared baseline for all) |
