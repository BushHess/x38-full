# Pairwise Replay Judgment Notes

**Step 3 — Replay-Dependent Fragility Audit**
**Date**: 2026-03-06

---

## Pair 1: SM vs LATCH — OPERATIONALLY IDENTICAL

SM and LATCH produce indistinguishable operational fragility profiles across all three disruption classes:

- **Random miss**: CV 1.51% vs 1.48% (delta 0.03 pp — within sampling noise)
- **Outage 168h worst**: 0.739 vs 0.750 (delta +0.010 — within sampling noise)
- **Delay D4**: -0.033 vs -0.033 (delta 0.000 — identical)

This confirms Step 2's finding that the hysteresis mechanism in LATCH produces no measurable structural or operational differentiation from SM's state machine. The strategies are functionally interchangeable from an operational fragility perspective.

LATCH has a marginally higher baseline Sharpe (+0.009) and marginally better worst-case outage (+0.010), but these differences are smaller than the stochastic variation in any single Monte Carlo run.

**Verdict**: No operational basis to prefer one over the other.

---

## Pair 2: E0 vs E0_plus_EMA1D21 — EMA OVERLAY ADDS DELAY FRAGILITY BUT DOMINATES ON ABSOLUTE SHARPE

The EMA(21d) regime filter increases E0's baseline Sharpe by +0.037 (from 1.138 to 1.175) while introducing modestly higher delay sensitivity:

- **D1 delta**: -0.031 (E0) vs -0.047 (E0_plus) — E0_plus 1.5x more sensitive
- **D4 delta**: -0.336 (E0) vs -0.372 (E0_plus) — E0_plus 1.1x more sensitive

However, E0_plus has higher absolute Sharpe at every stress level tested:
- Baseline: 1.175 > 1.138
- Outage 168h worst: 1.109 > 1.074
- D4: 0.803 > 0.802

The EMA filter narrows the entry window (only enters when D1 close > D1 EMA(21)), so a delayed fill is more likely to miss the window and forgo the entry entirely. This explains the faster percentage degradation.

**Verdict**: E0_plus dominates at all tested latency levels. The higher delay sensitivity is a relative weakness that does not overcome the absolute Sharpe advantage.

---

## Pair 3: E5 vs E5_plus_EMA1D21 — SAME PATTERN, AMPLIFIED; CROSSOVER AT HIGH DELAY

Same structural pattern as the E0 pair but with larger magnitudes:

- E5_plus baseline advantage: +0.040 Sharpe (1.270 vs 1.230)
- E5_plus D4 delta: -0.517 vs -0.453 — 0.064 worse
- E5_plus D4 absolute Sharpe: 0.753 vs 0.776 — E5 WINS at D4

Unlike the E0 pair, there is a **crossover**: E5_plus has higher absolute Sharpe at D0-D2, but at D3-D4, E5 overtakes it. At D4, E5's Sharpe (0.776) is higher than E5_plus's (0.753).

This means the EMA filter's performance advantage evaporates under high-latency conditions. If operational latency regularly exceeds 8-12 hours (D2-D3), E5 is the better choice. For sub-4h operations (the expected case), E5_plus is optimal.

**Verdict**: E5_plus for low-latency operations (<4h). E5 for degraded operations (>8h). The crossover occurs around D2-D3.

---

## Cross-Pair Synthesis

1. **Vol-target vs binary**: SM/LATCH are operationally robust but produce 40-60% lower Sharpe. The fragility advantage of vol-targeting is real but comes at a steep performance cost.

2. **EMA overlay tradeoff**: The D1 EMA(21) regime filter consistently increases both baseline performance and delay sensitivity. The net effect is positive for automated systems with <4h latency. For the E5 pair, the tradeoff is sharper — the crossover at D3-D4 means the filter can be net negative under degraded conditions.

3. **Performance-fragility ordering**: Across all 4 binary candidates, baseline Sharpe and delay fragility are perfectly inversely correlated. There is no free lunch — higher performance requires more precise entry timing.
