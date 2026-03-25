# V4 macroHystB vs E5_ema21D1 — Fair Comparison Report

**Verdict: V4_COMPETITIVE**
**Cost: 20 bps RT (primary), 50 bps RT (reference)**

## 1. Performance Summary (20 bps RT)

| Metric | V4 Dev | E5 Dev | V4 Holdout | E5 Holdout | V4 Full | E5 Full |
|--------|--------|--------|------------|------------|---------|---------|
| sharpe | 1.8493 | 1.7128 | 1.9649 | 1.2848 | 1.865 | 1.6073 |
| cagr_pct | 73.26 | 84.28 | 56.11 | 38.88 | 67.07 | 68.95 |
| max_drawdown_mid_pct | 23.87 | 35.41 | 12.15 | 21.55 | 23.87 | 35.41 |
| trades | 35 | 105 | 16 | 57 | 51 | 162 |
| profit_factor | 3.7537 | 1.8146 | 11.7485 | 1.8804 | 6.2705 | 1.8984 |
| objective_score | 197.1224 | 212.2294 | 160.3042 | 103.9504 | 183.273 | 173.4794 |

## 2. Validation + Diagnostic Summary

| Gate | V4 | E5 | Winner |
|------|----|----|--------|
| Lookahead | PASS | PASS | TIE |
| WFO head-to-head | valid wins=5 | valid wins=2 | TIE (underpowered) |
| Holdout (Δscore) | 122.7 | 66.4 | V4 |
| DSR advisory (H4 returns) | 0.9967 | 0.7578 | V4 |
| Sensitivity spread | 0.5354 | 0.4128 | E5 (narrower) |

## 3. WFO Window Details

Valid-window deltas (V4 - E5): [11.744, 211.0658, -117.0446, 231.0275, -46.3592, 30.724, 27.4214]
Power-only deltas (V4 - E5): [211.0658, -117.0446, 231.0275]
Wilcoxon W+=nan, p=1.0000, sufficient=False
Bootstrap CI: [-117.0446, 231.0275]

## 4. Paired Bootstrap (V4 vs E5)

| Period | Block | P(V4>E5) | Median Δ Sharpe | 95% CI |
|--------|-------|----------|-----------------|--------|
| dev | 10 | 0.783 | 0.2571 | [-0.423, 0.9234] |
| dev | 20 | 0.8065 | 0.2911 | [-0.3494, 0.8829] |
| dev | 40 | 0.8415 | 0.3285 | [-0.2974, 0.9668] |
| holdout | 10 | 0.9315 | 0.6322 | [-0.203, 1.4616] |
| holdout | 20 | 0.962 | 0.699 | [-0.063, 1.4072] |
| holdout | 40 | 0.985 | 0.7128 | [0.0694, 1.3762] |
| full | 10 | 0.895 | 0.3592 | [-0.1861, 0.867] |
| full | 20 | 0.936 | 0.3648 | [-0.1007, 0.8772] |
| full | 40 | 0.9325 | 0.3899 | [-0.1035, 0.8581] |

## 5. Trade Quality Comparison

| Metric | V4 | E5 |
|--------|----|----|
| trades | 51 | 162 |
| win_rate | 0.5882 | 0.4444 |
| avg_return | 0.075134 | 0.024516 |
| median_return | 0.00365 | -0.005272 |
| avg_hold_days | 11.05 | 6.17 |
| top5_pnl_sum | 155133.99 | 162434.19 |
| bottom5_pnl_sum | -20660.51 | -49917.02 |

## 6. Cost Sensitivity

| Cost (bps RT) | V4 Sharpe | E5 Sharpe | V4 CAGR | E5 CAGR |
|---------------|-----------|-----------|---------|---------|
| 10 | 1.8928 | 1.679 | 68.47% | 73.46% |
| 15 | 1.8789 | 1.6432 | 67.77% | 71.19% |
| 20 | 1.865 | 1.6073 | 67.07% | 68.95% |
| 25 | 1.851 | 1.5714 | 66.38% | 66.73% |
| 30 | 1.8371 | 1.5355 | 65.69% | 64.55% |
| 50 | 1.7812 | 1.3917 | 62.96% | 56.09% |
| 100 | 1.6404 | 1.0318 | 56.33% | 36.8% |

Cost crossover (E5 >= V4): None found

## 7. Regime Decomposition

| Strategy | Regime | Trades | Win Rate | Avg Return |
|----------|--------|--------|----------|------------|
| v4 | HIGH_VOL | 12 | 0.5833 | 0.090018 |
| v4 | TREND_DOWN | 2 | 1.0 | 0.1798 |
| v4 | TREND_UP | 37 | 0.5676 | 0.064649 |
| e5 | CHOP | 13 | 0.3846 | 0.036584 |
| e5 | HIGH_VOL | 31 | 0.6129 | 0.043483 |
| e5 | TREND_DOWN | 26 | 0.5385 | 0.024367 |
| e5 | TREND_UP | 92 | 0.3696 | 0.016461 |

## 8. Complexity Comparison

| Aspect | V4 | E5 |
|--------|----|----|
| Parameters | ~10 (3 lookbacks + 4 quantiles + 2 modes + 1 anchor) | 4 (slow_period, trail_mult, vdo_threshold, d1_ema_period) |
| Recalibration | Yearly (expanding + trailing quantiles) | None (fixed params) |
| Feature sources | D1 return + H4 trend quality + H4 order flow | H4 EMA crossover + VDO + D1 EMA regime |
| State machine | 2-state hysteresis (entry/hold thresholds) | 2-state with trailing stop + trend exit |
| Exit mechanism | Single hold threshold | ATR trail stop + EMA cross-down |

## 9. Verdict

**V4_COMPETITIVE** (V4 wins 3, E5 wins 0)

### Key Findings

1. **Sharpe**: V4 (1.8650) > E5 (1.6073) at 20 bps RT
2. **MDD**: V4 (23.9%) < E5 (35.4%) — V4 draws down less
3. **WFO**: valid wins V4=5 vs E5=2; power-only wins V4=2 vs E5=1 (basis=power_only, raw_winner=V4, supported=False, Wilcoxon p=1.000)
4. **Paired bootstrap**: P(V4>E5) = 0.936 (full period, block=20)
5. **Plateau**: V4 spread 0.5354 vs E5 0.4128 — V4 more fragile
6. **Trades**: V4 has 51 vs E5 has 162
7. **DSR advisory**: V4 p=0.9967 (10 trials) vs E5 p=0.7578 (245 trials) on H4 returns
8. **Cost**: V4 dominates E5 at all tested cost levels (no crossover found)

### Caveats

1. V4 has ~10 effective parameters vs E5's 4 — higher DOF
2. V4 yearly recalibration introduces implicit in-sample dependence
3. V4's 51 trades provide less statistical power than E5's 162
4. WFO is evaluated head-to-head with power-only inference; low-trade windows remain underpowered
5. V4 plateau spread is wider — performance more sensitive to parameter choice
6. V4 uses order-flow data (taker buy imbalance) which may not be available in all markets
