# X10 — Multi-TP Ladder for E5+EMA21D1

**Date**: 2026-03-09
**Registry**: Study #47
**Verdict**: **REJECTED**

---

## Hypothesis

Partial take-profit exits at fixed R-multiples (1.5R, 2.2R, 3.0R) lock profit
earlier, reducing MDD without destroying returns.

**Counter-hypothesis**: Trend-following profits come from fat right tails.
Fixed TPs cut winners — the top 5% of trades = 129.5% of total profit.

## Variants

| Variant | Description |
|---------|-------------|
| FULL | E5+EMA21D1 baseline (no TP) |
| TP2 | 50/50 split: exit half at 1.5R |
| TP3 | 30/30/20/20 split at 1.5R/2.2R/3.0R |

## Results (harsh cost, 50 bps RT)

| Variant | Sharpe | CAGR | MDD |
|---------|--------|------|-----|
| FULL (baseline) | 1.432 | 60.0% | 41.6% |
| TP2 | 1.291 (-0.141) | 42.3% | 44.2% |
| TP3 | 1.057 (-0.375) | 31.4% | 48.3% |

## Conclusion

TPs destroy trend-following alpha. Counter-hypothesis confirmed.
Both TP2 and TP3 are worse on ALL metrics — lower Sharpe, lower CAGR,
AND higher MDD. Fat-tail alpha concentration makes any fixed TP destructive.

## Artifacts

- `benchmark.py` — study code
- `x10_results.json` — full results
- `x10_bootstrap_table.csv`, `x10_factorial_table.csv`, `x10_tp_sweep.csv`, `x10_timescale_table.csv`
