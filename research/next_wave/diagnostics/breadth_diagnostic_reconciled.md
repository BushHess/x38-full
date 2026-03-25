# D1.4R — Reconciled Breadth Diagnostic (True D1 EMA(21))

Date: 2026-03-07
Source: H4-to-D1 resampled breadth (not H4 EMA(126) proxy)
Script: `breadth_reconcile.py`

## Construction Change

| Metric | OLD (D1.4) | NEW (D1.4R) |
|--------|-----------|------------|
| EMA basis | H4 EMA(126) | True D1 EMA(21) from resampled D1 closes |
| D1 close source | N/A (approximated) | Last H4 bar close per UTC day |
| Update frequency | Every H4 bar (6x/day) | Once per day (D1 close) |
| No-lookahead rule | H4 close_time <= T | D1 close_time < T |

## Outcome Separation (full sample)

| Metric | OLD | NEW |
|--------|-----|-----|
| MWU p | 0.390 | 0.344 |
| Spearman r | -0.054 | -0.052 |
| Spearman p | 0.460 | 0.485 |

**No change in conclusion.** Full-sample breadth remains non-significant.

## Quintile Expectancy

| Q | Range | N | WR | MeanRet% | PnL |
|---|-------|---|----|----------|-----|
| Q0 | 0.00-0.38 | 52 | 48.1% | +3.24% | +$168,462 |
| Q1 | 0.45-0.54 | 26 | 50.0% | +2.70% | +$40,944 |
| Q2 | 0.55-0.77 | 38 | 52.6% | +2.42% | +$160,381 |
| Q3 | 0.82-0.92 | 38 | 34.2% | +3.99% | +$31,792 |
| Q4 | 1.00-1.00 | 32 | 43.8% | +0.68% | +$24,775 |

All quintiles positive. Non-monotonic. Same structure as proxy.

## Paper Veto (full sample, low breadth)

All low-breadth vetoes HURT: -$18K to -$169K. Same as proxy.

## Re-entry Subset

MWU p = 0.088 (was 0.068 with proxy). Slightly weaker. Still non-significant.

## Paper Rule: re2_breadth > 0.80

| Metric | OLD | NEW |
|--------|-----|-----|
| Blocked | 15 | 22 |
| Losers | 12 | 16 |
| Winners | 3 | 6 |
| L/W ratio | 4.0 | 2.7 |
| Net PnL | +$24K | +$36K |

PnL effect is stronger but L/W ratio degrades. Threshold sensitivity increases
(7 trades change classification). Not robust to metric construction.

## Verdict: CLEAN_WEAK

The exact breadth construction confirms the proxy-based conclusions:
- No full-sample signal
- Paper vetoes hurt
- Re-entry subset is marginal
- Paper rule is fragile and threshold-sensitive
