# Cross-Strategy Findings — Step 2

## 1. All 6 Candidates Are Home-Run Dependent in Unit-Size View

Every candidate shows home-run dependence in the unit-size (exposure-neutral) view. The CAGR zero-cross occurs within 6-14 trades removed (6-10% of trades) for all 6. This confirms that trend-following on BTC with any variant of the VTREND family is structurally dependent on capturing rare, large moves.

## 2. Native View Separates Two Groups

In native (deploy-reality) view:

| Group | Candidates | Native Style | Zero-Cross | Cliff |
|-------|-----------|-------------|------------|-------|
| **Strong home-run** | E0, E0_plus_EMA1D21 | home-run | 3-4% | cliff-like |
| **Hybrid** | E5, SM, LATCH, E5_plus_EMA1D21 | hybrid | 4-11% | mixed |

E0 and E0_plus_EMA1D21 are the most concentrated: top-5 trades = 83-90% of net PnL. SM and LATCH are more resilient natively (zero-cross at 10.8%) because their vol-targeted sizing produces smaller absolute PnL dispersion.

## 3. SM and LATCH Are Near-Duplicates

SM and LATCH are structurally indistinguishable at the trade level:
- Same trade count (65), same median hold (9.83 days), same zero-cross points
- Win rate within 1.5 pp, profit factor within 0.07, identical giveback medians
- Both smooth in native view, cliff-like in unit-size view
- The hysteresis in LATCH produces no measurable structural differentiation vs SM's state machine

**Judgment: near-duplicate** at the trade-structure layer. Any differences are in the equity curve path, not in the trade population.

## 4. EMA Overlay Preserves Structure, Alters Selectivity

Adding the D1 EMA(21) regime filter to E0 or E5:
- Reduces trade count by ~10% (192→172 for E0, 207→186 for E5)
- Increases win rate by ~1-2 pp
- Slightly improves profit factor (+0.10)
- Slightly reduces top-5 concentration (90%→83% for E0, 79%→74% for E5)
- Marginally improves the zero-cross index (+1 trade before collapse)
- Does NOT change the style label or cliff behavior

The EMA overlay acts as a selectivity filter that removes some losing trades but preserves the fundamental payoff structure. It does not transform a home-run strategy into a grinder.

## 5. Behavioral Fragility Is Universal

All 6 candidates are classified as high behavioral fragility (worst skip-after-N delta Sharpe < -0.15):

| Candidate | Worst Skip dS | At N |
|-----------|-------------|------|
| E0 | -0.263 | 2 |
| E5 | -0.213 | 2 |
| E5_plus_EMA1D21 | -0.252 | 2 |
| E0_plus_EMA1D21 | -0.195 | 2 |
| SM | -0.175 | 2 |
| LATCH | -0.159 | 2 |

E0 is the most fragile, LATCH the least. But all are meaningfully harmed by skipping after 2 consecutive losses. This is a universal property of trend-following: big wins follow unpredictable loss sequences.

## 6. Giveback Is Consistent Across Variants

Median giveback ranges from 1.05 (E5_plus_EMA1D21) to 1.31 (SM/LATCH). The EMA-overlaid variants consistently have lower giveback (1.05-1.09) than their base versions (1.12-1.21), suggesting the regime filter preferentially removes trades that would have been quickly stopped out.

Long-hold trades (14d+) give back 0.31-0.50x across all candidates — the trail stop consistently captures most of the sustained move.

## 7. Cliff-Edge Geography

| Candidate | Native CAGR Cliff Score | Unit-Size CAGR Cliff Score |
|-----------|------------------------|--------------------------|
| E5 | 25.29 (highest) | 4.97 |
| E0_plus_EMA1D21 | 23.06 | 4.94 |
| E5_plus_EMA1D21 | 21.61 | 4.34 |
| E0 | 17.36 | 5.64 |
| LATCH | 1.23 (smooth) | 2.81 (smooth) |
| SM | 1.19 (smooth) | 2.76 (smooth) |

SM and LATCH are the only candidates with smooth native decay (no cliff detected). This is because their vol-targeted sizing compresses the dollar-denominated dispersion. In unit-size view, even SM/LATCH show cliff-like terminal damage from their single largest return trade.
