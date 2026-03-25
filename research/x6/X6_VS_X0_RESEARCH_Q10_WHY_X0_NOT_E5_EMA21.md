# Research Q10: Why X0 Is Recommended Over E5+EMA1D21

**Date**: 2026-03-08
**Sources**: Step 4 report, Step 5 report, Study #43, fragility audit artifacts
**Question**: E5+EMA1D21 has better holdout delta (+9.54 vs +5.98) and passes all gates. Why is X0 (E0+EMA1D21) the final recommendation?

---

## 1. Timeline of Decisions

| Date | Event | Winner | Basis |
|------|-------|--------|-------|
| 2026-03-05 | Study #41 (Parity) | X0 (E0+EMA1D21) | Only strategy passing ALL Tier 1 gates |
| 2026-03-06 | Study #43 (E5+EMA21 eval) | **E5+EMA1D21** | Wins 16/20 dimensions, higher holdout delta |
| 2026-03-06 | Step 4 (Synthesis) | **E5+EMA1D21** | PRIMARY_DEPLOY for M1/LT1 (return-seeking) |
| 2026-03-06 | **Step 5 (Live sign-off)** | **X0 (E0+EMA1D21)** | E5+EMA1D21 fails compound disruption threshold |

**The recommendation flipped in Step 5** — the final gate before capital deployment.

---

## 2. What Step 5 Tested

Step 5 tested **operational fragility** — what happens when real-world execution problems compound:

1. **Exit delay**: Stop-loss executes 1-4 bars late (4-16h delay)
2. **Combined disruptions**: Entry delay + exit delay simultaneously
3. **Stochastic Monte Carlo**: 1000 draws per candidate with empirical delay distributions

This is NOT about strategy quality. It's about **survival under infrastructure failure**.

---

## 3. The Decisive Test: Combined Disruptions

Entry D2 (8h delay) + Exit D1 (4h delay) — a realistic compound failure scenario:

| Candidate | Baseline Sharpe | Combined Delta | After Disruption | Status |
|-----------|:-:|:-:|:-:|:-:|
| SM | 0.816 | -0.000 | 0.816 | **GO** |
| **X0 (E0_plus)** | 1.175 | **-0.318** | 0.857 | **GO_WITH_GUARDS** |
| E0 | 1.138 | -0.322 | 0.816 | GO_WITH_GUARDS |
| E5_plus | 1.270 | **-0.396** | 0.874 | **HOLD** |
| E5 | 1.230 | -0.402 | 0.828 | HOLD |

**Threshold: -0.35** for GO_WITH_GUARDS sign-off.

- X0: -0.318 → **PASSES** (margin: 0.032)
- E5+EMA1D21: -0.396 → **FAILS** (exceeds by 0.046)

---

## 4. Why E5+EMA1D21 Is More Fragile

### Entry delay sensitivity (Step 3, D4 = 16h)

| Candidate | D1 delta | D2 delta | D4 delta | D4 Sharpe loss |
|-----------|:--------:|:--------:|:--------:|:-:|
| E0 | -0.031 | -0.200 | -0.336 | 29.5% |
| X0 (E0_plus) | -0.047 | -0.202 | -0.372 | 31.7% |
| E5 | -0.052 | -0.297 | -0.453 | 36.9% |
| **E5_plus** | **-0.081** | **-0.309** | **-0.517** | **40.7%** |

**E5+EMA1D21 loses 40.7% of Sharpe at D4 entry delay vs X0's 31.7%.** This 9% gap is the fundamental performance-fragility tradeoff.

### The mechanism

E5+EMA1D21's robust ATR trail is ~5% tighter than standard ATR (Report 16). This means:
- **More frequent exits** → more re-entries needed (199 trades vs X0's 186)
- **Each re-entry is a delay vulnerability** — if entry is delayed, the tighter trail already exited
- **Compound effect**: More exits × more delay-sensitive entries × tighter trail = amplified fragility

The same mechanism that gives E5+EMA1D21 lower MDD (tighter stops) also makes it more sensitive to execution delays.

---

## 5. The Complete Sign-Off Matrix

| Candidate | LT1 (<4h) | LT2 (4-16h) | LT3 (>16h) |
|-----------|:-:|:-:|:-:|
| SM | **GO** | **GO** | GO_WITH_GUARDS |
| **X0 (E0_plus)** | **GO_WITH_GUARDS** | HOLD | HOLD |
| E0 | GO_WITH_GUARDS | HOLD | HOLD |
| E5_plus | **HOLD** | HOLD | HOLD |
| E5 | HOLD | HOLD | HOLD |

**E5+EMA1D21 gets HOLD at every latency tier.** It is not deployable for live capital under any operational condition.

X0 (E0+EMA1D21) is the **strongest live-deployable binary candidate** at LT1.

---

## 6. Step-by-Step Decision Logic

### Step 4 said E5+EMA1D21 was best...

Step 4's recommendation matrix:
- **M1/LT1 (return-seeking)**: E5+EMA1D21 as PRIMARY_DEPLOY
- **M2/LT1 (balanced)**: X0 (E0+EMA1D21) as PRIMARY_DEPLOY

Step 4 also said: "Step 5 is not needed for research conclusion" and "could not realistically change candidate ranking."

### ...but Step 4 was wrong about Step 5

Step 5 DID change the ranking by testing combined disruptions — something Step 4 acknowledged as an untested gap:
> "Exit delay not tested. Step 3 tested entry delay only. Exit delays could differentially affect candidates and may be more damaging. This is the largest remaining gap." — Step 4, Limitation #4

Combined disruptions revealed **super-additive fragility** for E5+EMA1D21:
- Entry D2 alone: -0.310
- Exit D1 alone: -0.126
- Sum: -0.436 (predicted if additive)
- Actual combined: -0.396 (sub-additive, but still over threshold)

For X0:
- Entry D2: -0.202
- Exit D1: -0.187
- Sum: -0.389 (predicted)
- Actual: -0.318 (more sub-additive, under threshold)

---

## 7. Could E5+EMA1D21 Be Rescued?

### Option A: Guarantee LT1 (<4h execution)

Even at LT1, E5+EMA1D21 gets HOLD. The stochastic Monte Carlo with LT1 delay distribution (80% on-time, 15% D1, 5% D2) gives:
- E5+EMA1D21 p50 Sharpe: 1.235, p5: 1.185
- X0 p50 Sharpe: 1.142, p5: 1.100

E5+EMA1D21 has better stochastic performance. But the **deterministic combined worst-case** (-0.396) is the binding constraint, not the stochastic distribution. The sign-off framework requires surviving the worst plausible compound failure, not just the median case.

### Option B: Relax the threshold

The -0.35 threshold is a research convention, not a mathematical constant. At -0.40, E5+EMA1D21 would pass. But:
- X0 passes at -0.35 with 0.032 margin
- E5+EMA1D21 fails at -0.35 by 0.046
- Moving the threshold to accommodate E5+EMA1D21 would be outcome-driven, undermining the framework

### Option C: Remove the robust ATR (make it X0)

If E5+EMA1D21's fragility comes from the tighter trail, removing the robust ATR makes it... X0. This is circular.

---

## 8. The Fundamental Tradeoff

```
Higher Sharpe ←→ Higher Fragility

E5_plus: Sharpe 1.430, D4 loss 40.7%, combined -0.396 → HOLD
X0:      Sharpe 1.325, D4 loss 31.7%, combined -0.318 → GO_WITH_GUARDS
E0:      Sharpe 1.265, D4 loss 29.5%, combined -0.322 → GO_WITH_GUARDS
```

Step 3 found this is **perfectly inversely correlated** with baseline Sharpe — higher Sharpe strategies are systematically more delay-fragile. This is not an accident: strategies that react faster to signals also suffer more when signals arrive late.

---

## 9. Is This Fair?

### Arguments that E5+EMA1D21 was treated fairly

1. **Same framework applied to all**: Every candidate faces the same combined disruption test
2. **Same threshold for all**: -0.35 is uniform across all binary candidates
3. **E5+EMA1D21 fails by a meaningful margin** (0.046 over threshold, not borderline)
4. **The fragility is REAL** — compound execution delays are inevitable in production

### Arguments that E5+EMA1D21 was treated unfairly

1. **Stochastic performance is better**: At LT1 p5, E5+EMA1D21 still has Sharpe 1.185 (better than X0's 1.100)
2. **P(Sharpe>0) = 100% everywhere**: No scenario produces a losing strategy
3. **The deterministic worst-case is artificial**: entry_D2+exit_D1 simultaneously assumes both entry AND exit infrastructure fail — how likely is this?
4. **Step 5 contradicted Step 4's own prediction** that it "could not change candidate ranking"
5. **The -0.35 threshold is arbitrary**: there's no mathematical derivation for why -0.35 is the right cutoff

### Verdict on fairness

The framework is **internally consistent** — same rules applied to all. But the framework's design (binding constraint = deterministic worst-case rather than stochastic quantile) heavily penalizes higher-frequency strategies. If the sign-off used p5 stochastic instead of deterministic worst-case, E5+EMA1D21 would pass.

This is a **conservatism choice**, not a mathematical necessity.

---

## 10. What Changes If We Use E5+EMA1D21 Anyway?

| Dimension | X0 (current rec) | E5+EMA1D21 (alternative) | Difference |
|-----------|:-:|:-:|:-:|
| Baseline Sharpe | 1.325 | 1.430 | **+0.105 in favor of E5+** |
| Holdout delta | +5.98 | +9.54 | **+3.56 in favor of E5+** |
| WFO | 6/8 | 5/8 | **+1 in favor of X0** |
| MDD (holdout, harsh) | 16.96% | 15.17% | **-1.79% in favor of E5+** |
| D4 entry delay loss | 31.7% | 40.7% | **+9% risk for E5+** |
| Combined worst case | -0.318 | -0.396 | **+0.078 risk for E5+** |
| Stochastic LT1 p5 | 1.100 | 1.185 | **+0.085 in favor of E5+** |
| Live sign-off | GO_WITH_GUARDS | HOLD | **E5+ not approved** |

If you guarantee LT1 infrastructure AND accept compound failure risk, E5+EMA1D21 gives +0.105 Sharpe. If your infrastructure ever degrades to D2 entry + D1 exit simultaneously, you lose 0.078 more Sharpe than X0.

---

## 11. Summary

| Question | Answer |
|----------|--------|
| Why X0 over E5+EMA1D21? | **Fragility audit Step 5**: E5+EMA1D21 fails combined disruption threshold (-0.396 > -0.35) |
| What's the binding constraint? | Entry D2 + Exit D1 compound disruption scenario |
| Was E5+EMA1D21 ever recommended? | **YES** — Step 4 made it PRIMARY_DEPLOY M1/LT1 (before Step 5) |
| What changed? | Step 5 tested combined disruptions, found E5+EMA1D21 fails by 0.046 |
| Is this a paper vs live split? | **YES** — on paper E5+EMA1D21 wins (16/20 dimensions). For live capital, X0 is safer. |
| Margin of decision? | X0 passes by 0.032; E5+EMA1D21 fails by 0.046 — total gap 0.078 |
| Is the threshold arbitrary? | **Partially** — -0.35 is a research convention, not derived from first principles |
| Could E5+EMA1D21 be rescued? | Only by relaxing the threshold or guaranteeing zero compound failures |
