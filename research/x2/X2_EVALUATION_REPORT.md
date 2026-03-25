# X2 Research: Adaptive Trailing Stop

## Hypothesis

3×ATR trailing stop is too tight for crypto in trending markets — normal pullbacks
whipsaw out profitable positions. Adapting the multiplier based on unrealized gain
lets winners run while still protecting capital on fresh entries.

```
unrealized_gain = (close - entry_price) / entry_price

if unrealized_gain < 0.05:   trail_mult = 3.0   # tight — protect capital early
elif unrealized_gain < 0.15: trail_mult = 4.0   # mid — loosen as buffer grows
else:                        trail_mult = 5.0   # wide — ride strong trends
```

## Design

- **Entry**: identical to E0+EMA21(D1) baseline (EMA cross + VDO + D1 regime)
- **Exit**: adaptive trail stop OR EMA cross-down (same exit types as E0)
- **Parameters**: 7 tunable (slow_period, trail_tight/mid/wide, gain_tier1/tier2, vdo_threshold, d1_ema_period)
- **Defaults**: slow=120, tiers at 3.0/4.0/5.0, gain thresholds 5%/15%

## T1: Backtest Results (2019-01-01 → 2026-02-20, warmup=365d)

| Metric | Baseline (E0+EMA21) | X2 Adaptive | Delta |
|--------|---------------------|-------------|-------|
| **Sharpe (harsh)** | 1.3249 | **1.4227** | **+0.098** |
| **CAGR% (harsh)** | 54.70% | **62.87%** | **+8.17%** |
| **MDD% (harsh)** | 42.05% | **40.28%** | **-1.77%** |
| Calmar (harsh) | 1.3008 | 1.5609 | +0.260 |
| Trades | 172 | 138 | -34 |
| Win Rate | 42.4% | 42.8% | +0.3% |
| Avg Days Held | 6.9 | 8.9 | +2.0 |
| Profit Factor | 1.7151 | 1.9012 | +0.186 |
| Avg Exposure | 45.4% | 46.9% | +1.5% |

### All cost scenarios

| Scenario | dSharpe | dCAGR | dMDD | dTrades |
|----------|---------|-------|------|---------|
| smart | +0.046 | +5.83% | -3.04% | -34 |
| base | +0.071 | +7.03% | -3.09% | -34 |
| harsh | +0.098 | +8.17% | -1.77% | -34 |

X2 improves across ALL 3 cost scenarios on Sharpe, CAGR, and MDD.
Delta grows with cost harshness (fewer trades → lower friction penalty).

### Exit reason breakdown (harsh)

| Strategy | Trail stops | Trend exits |
|----------|------------|-------------|
| Baseline | 158 | 14 |
| X2 | 123 | 15 |

35 fewer trail stop exits — wider stops let profitable trades survive pullbacks.

## T2: Bootstrap VCBB (500 paths, block=60)

| Metric | Baseline | X2 |
|--------|----------|-----|
| Sharpe median | 0.2608 | **0.3186** |
| Sharpe [5%, 95%] | [-0.43, 0.93] | [-0.38, 1.04] |
| CAGR median | 3.17% | **4.99%** |
| CAGR [5%, 95%] | [-16.3, 31.3] | [-16.5, 39.2] |
| MDD median | 62.18% | 63.50% |
| P(CAGR>0) | 60.2% | **66.0%** |

### Head-to-head (paired bootstrap)

| Metric | X2 win rate | Mean delta |
|--------|-------------|------------|
| **Sharpe** | **342/500 (68.4%)** | +0.060 |
| **CAGR** | **340/500 (68.0%)** | +2.41% |
| MDD | 205/500 (41.0%) | +0.41% |

X2 wins Sharpe and CAGR on ~68% of bootstrap paths.
MDD is roughly neutral (41% win rate, +0.41% mean delta — not worse, not better).

## T3: Parity Check (engine vs vectorized surrogate)

| Strategy | Engine trades | Vec trades | Sharpe diff |
|----------|-------------|------------|-------------|
| Baseline | 172 | 186 | 0.009 |
| X2 | 138 | 150 | 0.008 |

~8% trade count difference due to execution timing (fill-at-open vs close-of-bar).
Sharpe diff < 0.01 — acceptable for bootstrap use.

## T4: Trail Tier Distribution (harsh scenario)

| Tier | Count | % | Avg Return | Avg Days | Win Rate | Total PnL |
|------|-------|---|------------|----------|----------|-----------|
| Tight (<5%) | 112 | 81.2% | -1.56% | 4.4 | 30.4% | -$286,595 |
| Mid (5-15%) | 12 | 8.7% | +10.69% | 17.5 | 100.0% | +$201,484 |
| Wide (≥15%) | 14 | 10.1% | +38.78% | 36.9 | 100.0% | +$433,455 |

Key insight: **19% of trades (mid+wide tiers) generate ALL the profit**.
These are the trades that benefit from the wider stop — without it,
many would have been stopped out prematurely by the fixed 3×ATR trail.

## Assessment

### Strengths
- Wins ALL metrics at ALL cost levels on real data
- Bootstrap h2h: 68% Sharpe/CAGR win rate — consistent, not lucky
- Mechanistically sound: wider stop when trend proven, tight when not
- Fewer trades (-34) → lower turnover → better under high costs
- Avg hold time increases (6.9→8.9 days) — lets winners run

### Weaknesses
- Bootstrap MDD neutral (41% win rate) — no MDD improvement OOS
- 7 parameters vs 4 for baseline (3 extra: trail_mid, trail_wide, gain thresholds)
- Tier thresholds (5%, 15%) are discretionary — not optimized or proven robust
- Real-data MDD improvement (-1.77%) is small and may not survive OOS

### Open questions for further research
1. **Tier robustness**: sweep gain_tier1 ∈ [0.03, 0.10] and gain_tier2 ∈ [0.10, 0.25] — is the plateau broad?
2. **Continuous vs stepped**: replace 3 discrete tiers with linear interpolation trail_mult = f(unrealized_gain)?
3. **WFO validation**: does adaptive trail survive walk-forward? (risk: overfitting to BTC's big trends)
4. **Parameter count concern**: 7 params vs 4 — DSR/deflated Sharpe penalty for extra degrees of freedom

## Files

- Strategy: `strategies/vtrend_x2/strategy.py`
- Benchmark: `research/x2/benchmark.py`
- Tests: `research/x2/test_x2.py` (24/24 pass)
- Results: `research/x2/x2_results.json`
- Tables: `research/x2/x2_backtest_table.csv`, `x2_bootstrap_table.csv`, `x2_delta_table.csv`
