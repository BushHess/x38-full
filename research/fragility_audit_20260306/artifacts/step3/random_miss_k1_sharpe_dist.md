# Random Miss K=1 Sharpe Distribution

**Figure**: `random_miss_k1_sharpe_dist.png`

## What it shows

Sharpe ratio distributions from 2000 Monte Carlo draws where 1 random entry is skipped per draw, for all 6 candidates. Each candidate's distribution is shown as a violin/box plot.

## Key observations

- All distributions are extremely tight. Binary strategies (E0, E5, E0_plus, E5_plus) have CV = 0.32-0.38%.
- SM/LATCH show wider distributions (CV = 1.48-1.51%) due to smaller trade count (65 vs 172-207).
- 100% of draws remain Sharpe-positive for every candidate.
- Mean Sharpe is indistinguishable from baseline Sharpe in all cases.

## Interpretation

Missing a single random entry is operationally harmless. The strategy's performance is not concentrated in any single entry point enough to cause material damage from a random miss.
