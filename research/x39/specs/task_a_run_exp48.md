# Task A: Run exp48 — Selectivity Batch Screen

## Session prompt

```
Read /var/www/trading-bots/btc-spot-dev/research/x39/specs/exp48_selectivity_batch_screen.md

This is a self-contained experiment spec. Do exactly what it says:
1. Read the spec completely
2. Read x39/explore.py for reusable helpers (ema, robust_atr, vdo, map_d1_to_h4, compute_features, replay_trades)
3. Write the experiment script to x39/experiments/exp48_selectivity_batch_screen.py
4. Run it
5. Write results back to the spec file under ## Result
6. Update x39/PLAN.md results table row 48 with the verdict

Key context:
- This is the LAST x39 experiment. After this, x39 is CLOSED.
- The purpose is to batch-screen 7 features for SELECTIVITY (blocked WR < baseline WR).
- Only features that pass selectivity in ≥3/4 WFO windows are candidates for future WFO testing.
- Expected outcome: most features will NOT be selective (exp01, exp33, exp51 precedent).
  Vol compression (exp34/42) was the only selective feature found in 51 prior experiments.
- If any feature IS selective: note it as a finding but do NOT run a full WFO — that's a separate task.
```

## Expected duration
~15 minutes (one run, no sweep optimization needed)

## After completion
If exp48 finds NO new selective features → x39 is CLOSED.
If exp48 finds a selective feature → note it, but proceed to Task B regardless.
