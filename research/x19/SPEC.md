# X19: Alternative Actuators for Churn Score — Feasibility Study

## Context

X14 D and X18 PROMOTE static suppress: at trail breach, if churn score > threshold,
hold through (ignore trail). Two validated filters at different return/risk frontiers:

| Filter | Sharpe | CAGR | MDD | Bootstrap P(d>0) |
|--------|--------|------|-----|-------------------|
| X18 (α=40%) | 1.482 | 66.6% | 41.8% | 62.6% |
| X14 D (P>0.5) | 1.428 | 64.0% | 36.7% | 65.0% |

External analyst proposes: the 7-feature churn SCORE correctly ranks continuation
utility, but the ACTUATOR (hold-through) may be suboptimal. Two alternative
actuator policies deserve testing:

- **Branch A**: Exit at trail, arm contingent re-entry for high-score episodes
- **Branch B**: Partial exit at trail, keep small runner for high-score episodes

## Central Question

Can a different action policy for high-churn-score trail breaches outperform
static suppress (hold-through) on Sharpe, MDD, or risk-adjusted return?

## Pre-Analysis: Feasibility Assessment

### Quantitative grounding from X18 T0

Q5 (top-scoring 36 trail-stop episodes, α=30%):
- Mean ΔU = +1.56%, Median ΔU = +0.34%, P10 ΔU = -3.77%
- **Both mean AND median are positive** (not a lottery profile as hypothesized)
- >50% of Q5 episodes benefit from suppression

### Cost arithmetic for Branch A (exit + re-enter)

Static suppress at trail breach: zero extra cost, 100% exposure retained.

Branch A at trail breach (per episode):
- Exit: 50 bps (same as E0, not incremental vs E0)
- Conditional re-entry: +50 bps entry on reduced position (f_A of full)
- Final exit from re-entered trade: +50 bps on f_A position
- **Incremental cost vs static suppress**: exit (50 bps on 100%) + re-entry (50 bps on f_A) + final exit (50 bps on f_A) = 50 + 100×f_A bps

At f_A=0.50: 100 bps incremental cost per episode.
At f_A=0.25: 75 bps incremental cost per episode.

Meanwhile, maximum capture is f_A × continuation (vs 100% for static suppress).

### Branch A can only win on MDD, not returns

For episodes where ΔU > 0 (continuation exists):
- Static suppress captures 100% of ΔU at zero cost
- Branch A captures f_A × ΔU minus incremental costs
- **Static suppress strictly dominates on positive-ΔU episodes**

For episodes where ΔU < 0 (false suppress, price continues down):
- Static suppress holds through the loss
- Branch A exits, avoids the loss (or re-entry doesn't trigger)
- **Branch A wins only on negative-ΔU episodes**

Therefore: Branch A trades RETURN for RISK REDUCTION. It cannot beat X18 on
Sharpe/CAGR. It can potentially beat X14 D on MDD if the loss avoidance on
bad episodes is large enough.

### Branch B arithmetic

Partial runner keeps f_B exposure, exits (1-f_B):
- Cost: exit (1-f_B) at trail (50 bps on (1-f_B) of position)
- Runner continues at f_B with hard stop
- **Incremental cost vs static suppress**: exit 50 bps on (1-f_B)

At f_B=0.25: 37.5 bps incremental cost.
At f_B=0.10: 45 bps incremental cost.

Branch B captures: f_B × ΔU for continuation, limits loss to f_B × hard_stop_distance
for false suppress. Also has add-back mechanism to recover full exposure on reclaim.

**Branch B is more efficient than A** because:
1. No re-entry cost (runner already in)
2. Add-back on reclaim recovers full exposure
3. Hard stop limits tail risk on runner

### Feasibility verdict

Branch A: LOW probability of beating X18 on returns. POSSIBLE improvement on
MDD vs X14 D, but X14 D already achieves MDD 36.7% through selective suppression.
The mechanism is redundant — different α values already control the return/risk
tradeoff.

Branch B: MODERATE probability. The partial runner + add-back preserves more of
the continuation while reducing peak drawdown. Lower incremental cost. Hard stop
caps worst case.

**Decision: test both, but Branch B is the more promising hypothesis.**

## Architecture

### Branch A: Exit + Contingent Re-entry

```
At trail breach where model score > α-percentile threshold:
1. EXIT normally (schedule exit at next bar close)
2. ARM re-entry state with context:
   - breach_trail_level = pk - trail_mult * ATR[breach_bar]
   - breach_bar = i (the bar where trail fired)
   - armed_size = f_A (fraction of full position)
   - armed_bars_remaining = H_max
3. While armed (each subsequent bar):
   a. Decrement armed_bars_remaining
   b. If close > breach_trail_level:
      ENTER at f_A fraction, relaxed gates (skip VDO, keep EMA+regime)
      Disarm. New trade with normal trail tracking.
   c. If armed_bars_remaining == 0: disarm, no re-entry
4. Normal E0 entry logic runs in parallel (full-size entries unaffected)
```

**Entry gate relaxation**: Armed re-entries skip VDO filter (VDO may be
temporarily negative during whipsaw). Require EMA fast > slow AND D1 regime
to avoid entering against trend.

**No scale-up**: Adding scale-up adds DOF and complexity. Test base mechanism
first. If f_A trade is open and a normal full-size entry signal fires, close
the f_A trade and enter at full size (normal E0 behavior takes priority).

### Branch B: Partial Runner

```
At trail breach where model score > α-percentile threshold:
1. PARTIAL EXIT: sell (1 - f_B) of position at next bar close
2. KEEP f_B as runner with:
   - runner_stop = breach_trail_level - hard_mult * trail_mult * ATR[breach_bar]
   - runner continues normal trail tracking from same peak
3. Runner exit conditions:
   a. close < runner_stop → hard exit
   b. EMA fast < slow → trend exit (same as E0)
   c. RECLAIM: close > breach_trail_level for R consecutive bars →
      add back to 100% position at next bar close
4. If runner exits (stop or trend), disarm. Normal E0 entry logic resumes.
5. If add-back triggers, trade continues at full size with same peak tracking.
```

**Cost**: partial exit costs 50 bps on (1-f_B) fraction. Add-back costs 50 bps
on (1-f_B) fraction. Hard exit costs 50 bps on f_B fraction.

### Position State Machine

```
States: OUT → FULL → ARMED (Branch A only) → PARTIAL (Branch B only) → OUT
         ↑      |
         +------+ (normal entry/exit)

Branch A: OUT → FULL → [trail+score] → OUT/ARMED → [trigger] → PARTIAL_REENTRY → ...
Branch B: OUT → FULL → [trail+score] → PARTIAL → [reclaim] → FULL
                                         → [stop/trend] → OUT
```

## Parameter Grid

### Fixed parameters (not tuned, reduce DOF)
- H_max = 20 bars (matches CHURN_WINDOW = 20, the churn labeling window)
- hard_mult = 2.0 (runner hard stop at 2× trail distance below trail level)
- R = 2 bars (reclaim confirmation: 2 consecutive closes above trail level)
- Trigger = close > breach_trail_level (simplest observable event)

### Tuned parameters
```
α ∈ {5, 10, 15, 20%}        — selective (targeting Q5 episodes)
f_A ∈ {0.25, 0.50}          — re-entry size (Branch A)
f_B ∈ {0.10, 0.25}          — runner fraction (Branch B)
```

### Total configurations
- Branch A: 4 α × 2 f_A = 8
- Branch B: 4 α × 2 f_B = 8
- Total: 16 configurations

### DOF
- E0 base: 4.35
- Branch A: +1 (α) + 1 (f_A) = 6.35
- Branch B: +1 (α) + 1 (f_B) = 6.35

## Test Suite

### T-1: Oracle Ceiling (pre-test, abort gate)

Before running the full suite, estimate the theoretical maximum for each branch
using the X18 per-episode ΔU data.

**Method:**
1. For each Q5 trail-stop episode in E0, we know the ΔU from X18 static suppress
2. For Branch A: ceiling ΔU_A = f_A × max(0, ΔU) − cost_A for episodes where
   price rebounds above trail level within H_max bars (check price data)
3. For Branch B: ceiling ΔU_B = f_B × ΔU + (1-f_B) × 0 for all episodes
   (runner captures f_B of continuation, exited portion captures nothing)
4. Sum across episodes and compare to X18's total ΔU

**Abort gate**: If ceiling(best_branch) < 50% of X18's total ΔU benefit on
same episodes → ABORT (the mechanism cannot reach competitiveness even with
perfect parameter choice).

### T0: ΔU Diagnostic

Per-episode ΔU by score quintile for the best configuration of each branch.
Report: mean, median, P10, CVaR10 per quintile.

**Gate G0**: Q5 median ΔU > 0 (same as X18).

### T1: Nested Walk-Forward Validation (4 folds)

Same fold structure as X18. Each fold:
1. Train model on training portion
2. Compute α threshold from training scores
3. For each (α, f) combination: run branch sim, measure training Sharpe
4. Select best (α, f) by training Sharpe
5. Measure test Sharpe and MDD
6. d_sharpe = test_branch_sharpe - test_e0_sharpe
7. d_mdd = test_branch_mdd - test_e0_mdd

**Gate G1**: win_rate >= 3/4 AND mean d_sharpe > 0

### T2: Bootstrap (500 VCBB)

Using consensus parameters from T1.

**Gate G2**: P(d_sharpe > 0) > 60%
**Gate G3**: median d_mdd ≤ +5.0 pp

### T3: Jackknife (leave-year-out)

**Gate G4**: ≤ 2 negative folds

### T4: PSR with DOF Correction

DOF: 6.35 (E0 4.35 + 2 branch params)

**Gate G5**: PSR > 0.95

### T5: Comparison Table

E0, X19_A, X19_B, X18 (α=40%), X14_D (P>0.5).

Additional metrics beyond standard: mean ΔU, median ΔU, P10 ΔU, CVaR10 ΔU
for Q5 episodes.

## Verdict Gates

| Gate | Test | Condition |
|------|------|-----------|
| ABORT | T-1 | Ceiling < 50% of X18 benefit → abort |
| G0 | T0 | Q5 median ΔU > 0 |
| G1 | T1 | WFO ≥ 75%, mean d > 0 |
| G2 | T2 | P(d_sharpe > 0) > 60% |
| G3 | T2 | Median d_mdd ≤ +5pp |
| G4 | T3 | ≤ 2 negative jackknife |
| G5 | T4 | PSR > 0.95 |

## Decision Matrix

| Outcome | Action |
|---------|--------|
| T-1 ABORT | CLOSE — alternative actuators have insufficient ceiling |
| Any branch: all G0-G5 pass, beats X18 Sharpe | PROMOTE branch — replace X18 |
| Any branch: all pass, beats X14 D MDD | PROMOTE branch — new risk profile |
| Any branch: all pass, but ≤ X18 AND ≤ X14 D | CLOSE — no improvement over existing |
| Both branches fail any gate | CLOSE — static suppress is optimal actuator |

**One-more-round commitment**: This is the FINAL churn actuator study.
If neither branch passes → close churn research entirely. Static suppress
(X18/X14_D) confirmed as optimal, no further actuator variants.

## Implementation Notes

### Fractional position sim

The existing `_run_sim_mask` is binary (fully in/out). X19 requires:
- `exposure` float (0.0 to 1.0) replacing boolean `inp`
- `bq` tracks actual quantity (can be fractional)
- Partial exit: sell (1-f) × bq, keep f × bq, cash += sell proceeds
- Add-back: buy more bq to reach full position from cash
- NAV always = cash + bq × price (unchanged)

### Cost tracking

Each leg pays its own cost:
- Partial exit: `received = sell_qty * price * (1 - cps)`
- Re-entry: `cost = buy_qty * price * (1 + cps)`
- Full trade record tracks all legs for PnL attribution

### Trade records

Extend trade dict with:
- `n_legs`: number of entry/exit legs
- `reentry_bar`, `reentry_px` (Branch A)
- `partial_exit_bar`, `addback_bar` (Branch B)
- `exit_reason`: "trail_stop" | "runner_stop" | "trend_exit" | "reclaim+trend" | etc.

## Estimated Runtime

- T-1 (ceiling): ~2s (reuse X18 data + price lookups)
- T0 (ΔU): ~5s (16 configs × 1 sim each)
- T1 (WFO): ~10s (4 folds × 16 configs)
- T2 (bootstrap): ~180s (500 paths, model retrain per path)
- T3 (jackknife): ~3s
- T4 (PSR): ~1s
- T5 (comparison): ~1s
- Total: ~3.5 min (if not aborted at T-1)

## Output Files

```
x19/
  SPEC.md
  benchmark.py
  x19_results.json
  x19_ceiling.csv       (T-1)
  x19_delta_u.csv       (T0)
  x19_wfo.csv           (T1)
  x19_bootstrap.csv     (T2)
  x19_jackknife.csv     (T3)
  x19_comparison.csv    (T5)
```
