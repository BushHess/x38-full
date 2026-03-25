# Stochastic Delay: p5 Sharpe by Candidate x Latency Tier

**File**: `stochastic_delay_p95_matrix.png`

Heatmap of p5 Sharpe (5th percentile from 1000 stochastic draws) across candidates and latency tiers.

Stochastic delay distributions:
- LT1: entry {0:80%, 1:15%, 2:5%}, exit {0:85%, 1:15%}
- LT2: entry {0:10%, 1:35%, 2:30%, 3:15%, 4:10%}, exit {0:25%, 1:45%, 2:20%, 3:10%}
- LT3: entry {2:10%, 3:20%, 4:30%, 5:25%, 6:15%}, exit {1:20%, 2:35%, 3:25%, 4:20%}

Key observations:
- Green cells (high Sharpe): SM across all tiers, E5/E5_plus at LT1
- Red cells (low Sharpe): E5/E5_plus at LT3 (p5 < 0.63)
- SM LT1 p5 = 0.798, SM LT3 p5 = 0.652 — narrow range confirming robustness
- E5_plus LT1 p5 = 1.185 (highest), E5_plus LT3 p5 = 0.621 (largest spread)
- All cells are positive (>0.62) — no candidate goes negative under stochastic delay
