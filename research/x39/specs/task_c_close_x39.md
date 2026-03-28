# Task C: Close x39 — Final Report

## Prerequisites
- Task A (exp48) completed
- Task B (port + validation) completed

## Session prompt

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/task_c_close_x39.md

After completing Tasks A and B, close x39 with a final conclusion.

1. Read all spec files to confirm status of all 52 experiments
2. Read Task B validation results from results/full_eval_e5_ema21d1_vc/
3. Write a conclusion report: x39/CONCLUSION.md
4. Update x39/PLAN.md — mark experiment plan as CLOSED
5. Update project memory with final x39 outcome
```

## CONCLUSION.md structure

```markdown
# x39 — Feature Invention Explorer: Conclusion

## Summary
52 experiments, 17 categories, ~500 configs.
Timeline: [start date] → [end date].

## The One Finding: Vol Compression Entry Gate
- Feature: vol_ratio_5_20 = rolling_std(close, 5) / rolling_std(close, 20)
- Gate: enter only when vol_ratio_5_20 < 0.7
- x39 exp42 WFO: 4/4 windows, mean d_Sharpe +0.25 (simplified replay)
- v10 validation: [EXIT CODE] — [VERDICT]
- Cost-independent: works at 10-50 bps (exp52)
- Fragile: only vol_ratio_5_20 selective, 0/4 alternatives (exp50)

## Fundamental Constraints Proven
1. Fat-tail alpha concentration (top 5% = 129.5%)
2. Cross-timescale ρ=0.92 (diversification ceiling +3.5%)
3. Entry features IC=0 (cannot predict trade quality)
4. Regime-dependent mechanisms fail WFO (bear-only = not robust)

## Methodological Findings
1. Selectivity (blocked WR < baseline WR) predicts WFO success
2. Unconditional residual scan misses conditional signals
3. Full-sample PASS ≠ robust (3 mechanisms passed full-sample, failed WFO)

## Exhausted Directions
[List all categories with brief one-line verdicts]

## Recommendation
[Based on Task B validation result]
```

## What to update in project memory

Update `/root/.claude/projects/-var-www-trading-bots/memory/MEMORY.md` with:
- x39 final status: CLOSED
- Vol compression finding + v10 validation result
- If PROMOTE: new primary candidate strategy name
- If HOLD: same situation as E5-ema21D1, both underresolved
