# X11 — Short-Side Complement for E5+EMA21D1

**Date**: 2026-03-09
**Registry**: Study #48
**Verdict**: **REJECTED**

---

## Hypothesis

Short during D1 EMA regime OFF (bearish) generates independent alpha,
complementing the long-only strategy with a short-side hedge.

## Results (harsh cost, 50 bps RT)

| Metric | Long-only | Short-only | Combined |
|--------|-----------|------------|----------|
| Sharpe | 1.432 | -0.640 | 1.254 |
| CAGR | 60.0% | -24.6% | — |
| MDD | 41.6% | 92.1% | — |

- Short-only negative at ALL 16 timescales
- Combined (long+short): Sharpe 1.254 vs long-only 1.432 — WORSE
- Bootstrap: Sharpe win 0%, CAGR win 0.4%, MDD win 63.2%
- Correlation: Pearson rho=0.001 (uncorrelated but negative-EV)
- No breakeven funding rate exists (negative at 0 bps)

## Conclusion

BTC's persistent upward drift makes trend-following shorts negative-EV.
Even with zero transaction costs, short-side alpha is negative.
The MDD improvement (63.2% bootstrap) does not compensate for catastrophic
return destruction.

## Artifacts

- `benchmark.py` — study code
- `x11_results.json` — full results
- `x11_bootstrap_table.csv`, `x11_funding_sweep.csv`, `x11_short_factorial.csv`, `x11_timescale_table.csv`
