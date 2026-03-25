# X18: α-Percentile Static Mask — Nested WFO Validation

## Context

X14 Design D (static 7-feature logistic mask, P>0.5 threshold) is the ONLY
churn filter that passes all validation gates including bootstrap (P(d>0)=65%).
X16/X17 showed WATCH (hold-through) fails at every G: too short = no-op,
too long = path-specific.

External review proposed methodological improvements: α-percentile threshold,
nested WFO, ΔU diagnostic. X17 applied these to WATCH and confirmed the
G dilemma. This study applies them to the PROVEN static mask approach.

## Key Idea

Combine X14's proven mechanism with the analyst's methodological framework:

| Component | X14 D | X18 |
|-----------|-------|-----|
| Policy | Static suppress | Static suppress (same) |
| Threshold | P(churn) > 0.5 | α-percentile (rank-based) |
| Tuning | Full-sample | Nested WFO only |
| Free params | 0 | 1 (α) |
| Features | 7 market-state | 7 market-state (same) |
| Validation | WFO+Bootstrap+JK | WFO+Bootstrap+JK+PSR+ΔU |

## Architecture

### Static Suppress with α-Percentile Threshold

```
1. Train L2-penalized logistic on training trail stops (7 features)
2. Compute P(churn) scores for all training trail-stop episodes
3. Set alpha_threshold = percentile(training_scores, 100 - α)
4. In sim, at EACH bar where trail would fire:
   a. Compute 7 market-state features
   b. If score > alpha_threshold: SUPPRESS (ignore trail, trade continues)
   c. Else: exit at trail stop (normal E0 behavior)
```

No WATCH state. No G parameter. No deeper stop.
Trade continues with normal trail tracking after suppression.
Trail may fire again on next bar — model re-evaluated each bar.

### Why This Should Work

1. Static suppress avoids the G dilemma entirely
2. 7 market-state features avoid X15's feedback loop (no trade-context features)
3. Model re-evaluated each bar → conditions change → eventually allows exit
4. α-percentile is stable across training windows (rank-based, not calibration-dependent)
5. Single parameter (α) minimizes overfit risk

### Why This Might Differ from X14 D

X14 D uses fixed P>0.5 threshold. This corresponds to suppressing ~60-70% of
trail-stop episodes (since churn rate is 63%). α-percentile allows testing
different suppression budgets:
- α=10%: suppress only top 10% (very selective) → closer to E0
- α=50%: suppress half (similar to X14 D)
- α=70%: suppress most trail stops → fewer trades, longer holds

## Parameter Grid

```
α ∈ {5, 10, 15, 20, 25, 30, 40, 50, 60, 70%}  (10 values)
```

Total: 10 configurations. One parameter.

## Test Suite

### T0: ΔU Diagnostic (Static Suppress)

Per-episode ΔU for static suppress is more complex than WATCH ΔU because the
"suppress" outcome spans the entire remaining trade. Approximation:

For each trail-stop episode in E0, find the MATCHED trade in the filtered sim
(same entry). ΔU = difference in trade PnL between filtered and E0.

**Method:**
1. Train model on full data, compute scores
2. For each α: run filtered sim, match trades with E0
3. For matched trail-stop episodes, compute ΔU = log(filtered_exit_px / e0_exit_px)
4. Report ΔU by score quintile

**Gate G0:** Top 2 quintiles have median ΔU > 0 at best α.

### T1: Nested Walk-Forward Validation (primary test)

4 expanding folds. Each fold trains model, computes scores, sweeps α.

**Method:** For each fold:
1. Train model on training portion
2. Compute training scores → α_threshold for each α
3. For each α: run sim on full data, measure training-window Sharpe
4. Select best α by training Sharpe
5. Measure test-window Sharpe
6. d_sharpe = test_filter_sharpe - test_e0_sharpe

**Gate G1:** win_rate >= 3/4 AND mean d_sharpe > 0

### T2: Bootstrap (500 VCBB)

**Gate G2:** P(d_sharpe > 0) > 0.60
**Gate G3:** median d_mdd ≤ +5.0 pp

### T3: Jackknife (leave-year-out)

**Gate G4:** ≤ 2 negative folds

### T4: PSR with DOF Correction

DOF: E0 (4.35) + 1 (α) = 5.35

**Gate G5:** PSR > 0.95

### T5: Comparison Table

E0, X18, X14_D, X16_E, X17.

## Verdict Gates

| Gate | Test | Condition |
|------|------|-----------|
| G0 | T0 | Top 2 quintiles median ΔU > 0 |
| G1 | T1 | WFO ≥ 75%, mean d > 0 |
| G2 | T2 | P(d_sharpe > 0) > 60% |
| G3 | T2 | Median d_mdd ≤ +5pp |
| G4 | T3 | ≤ 2 negative jackknife |
| G5 | T4 | PSR > 0.95 |

## Decision Matrix

| Outcome | Action |
|---------|--------|
| All pass, X18 > X14 D | PROMOTE X18 — replaces X14 D |
| All pass, X18 ≈ X14 D | VALIDATE — confirms X14 D with better methodology |
| G1 fails | REVERT — α-percentile + nested WFO doesn't help static mask |
| G2 fails | CONFIRM_X14 — static mask works but α tuning doesn't add value |

## Estimated Runtime

- T0 (ΔU): ~5s (10 α values × 1 sim each)
- T1 (WFO): ~5s (4 folds × 10 α values)
- T2 (bootstrap): ~120s (500 paths)
- T3 (jackknife): ~2s
- T4 (PSR): ~1s
- T5 (comparison): ~1s
- Total: ~2.5 min

## Output Files

```
x18/
  SPEC.md
  benchmark.py
  x18_results.json
  x18_delta_u.csv
  x18_wfo.csv
  x18_bootstrap.csv
  x18_jackknife.csv
  x18_comparison.csv
```
