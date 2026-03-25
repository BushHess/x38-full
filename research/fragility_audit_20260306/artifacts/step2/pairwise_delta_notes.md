# Pairwise Structure Delta Notes — Step 2

## Pair 1: SM vs LATCH

**Verdict: NEAR-DUPLICATE**

SM and LATCH are structurally indistinguishable at the trade-structure layer. Every metric is within noise:

- Same trade count (65), same median hold (9.83d), same zero-cross indices (native 7, unit 6)
- Win rate: 40.0% vs 41.5% (1.5 pp)
- Profit factor: 2.641 vs 2.713 (0.07 delta)
- Giveback median: identical (1.313)
- Top-5 share: 81.9% vs 81.5% (0.4 pp)
- Cliff scores: both smooth natively (1.19, 1.23), both cliff-like in unit-size (2.76, 2.81)
- Style labels: identical (hybrid/home-run/hybrid)
- Skip-after-N worst delta Sharpe: -0.175 vs -0.159 (SM slightly more fragile)

The LATCH hysteresis produces no measurable structural differentiation from SM's state-machine entry. These are the same strategy for all practical purposes at the trade-population level. Any differences between them live in the equity-curve path (intra-trade timing), not in the completed-trade distribution.

**Implication**: Carrying both SM and LATCH in a portfolio provides zero diversification at the trade level. Choose one based on implementation preference or intra-trade path properties, not on trade-structure grounds.

---

## Pair 2: E0 vs E0_plus_EMA1D21

**Verdict: MODESTLY DIFFERENTIATED**

The D1 EMA(21) regime filter applied to E0 produces a consistent but modest improvement across all fragility dimensions:

- Trade count: 192 vs 172 (10.4% reduction — the filter removes ~20 trades)
- Win rate: 41.7% vs 43.6% (+1.9 pp)
- Profit factor: 1.614 vs 1.715 (+0.10)
- Top-5 share: 90.2% vs 83.4% (6.8 pp lower concentration)
- Native zero-cross: 3.1% vs 4.1% (1 trade more resilient)
- Unit-size zero-cross: 5.7% vs 7.0% (1 trade more resilient)
- Skip-after-N worst dS: -0.263 vs -0.195 (25.9% less fragile at N=2)
- Giveback median: 1.21 vs 1.09 (9.3% lower — fewer whipsawed entries)
- Trail stop exit pct: 83.9% vs 91.9% (filter removes more trend-exit trades)

However, the native cliff score is *higher* for E0_plus (23.06 vs 17.36) because the reduced trade count makes the surviving top trades a larger share of a smaller total PnL pool. The cliff geography shifts but does not disappear.

**Style labels remain identical**: home-run / home-run / home-run, cliff-like in both views.

The EMA overlay acts as a **selectivity filter** that preferentially removes losing/whipsawed trades. It does not change the strategy's fundamental dependence on rare large winners. The improvement is real (25% less behavioral fragility, 7 pp lower concentration) but structural — the home-run nature is preserved.

**Implication**: E0_plus_EMA1D21 is strictly preferred over E0 on trade-structure grounds. The filter removes ~20 trades that were disproportionately small losers, improving every fragility metric while preserving the payoff structure.

---

## Pair 3: E5 vs E5_plus_EMA1D21

**Verdict: MODESTLY DIFFERENTIATED**

The D1 EMA(21) regime filter applied to E5 produces the same pattern as E0 vs E0_plus:

- Trade count: 207 vs 186 (10.1% reduction)
- Win rate: 43.5% vs 44.6% (+1.1 pp)
- Profit factor: 1.667 vs 1.777 (+0.11)
- Top-5 share: 79.0% vs 73.8% (5.2 pp lower concentration — E5_plus is the *least concentrated* of all 6)
- Native zero-cross: 3.9% vs 4.3% (same index 8, but higher percentage due to smaller N)
- Unit-size zero-cross: 6.3% vs 7.5% (1 trade more resilient)
- Giveback median: 1.12 vs 1.05 (6.5% lower)
- Trail stop exit pct: 84.5% vs 93.0% (same pattern — filter removes trend-exit trades)

**Anomaly**: Skip-after-N worst delta Sharpe is *worse* for E5_plus (-0.252) than E5 (-0.213). This is the only case where the EMA overlay increases behavioral fragility. The filter removes trades that break loss streaks, making the remaining loss clusters more damaging. This suggests the EMA filter's trade-removal pattern interacts differently with E5's loss-streak structure than with E0's.

Both share the same style labels: hybrid / home-run / hybrid. The native cliff score decreases (25.3 vs 21.6), unlike the E0 pair.

**Implication**: E5_plus_EMA1D21 is preferred on concentration and giveback grounds. However, the increased skip-after-N fragility is a meaningful difference from the E0 pair pattern. A trader running E5_plus must be *more* disciplined about taking every signal, not less, despite the improved overall profile.
