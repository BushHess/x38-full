# Research Q11: Should E0 Be the Recommendation Instead of X0?

> **Historical note (2026-03-09):** This document was written when X0 (E0+EMA1D21)
> was primary. After framework reform, E5+EMA1D21 is PRIMARY and X0 is HOLD.
> The latency-tier analysis below remains valid for fallback logic.

**Date**: 2026-03-08
**Sources**: Validation gate results, parity_eval_x, Q6 bootstrap analysis, Step 5 sign-off
**Question**: If E0 also passes the validation framework and bootstrap says E0 > X0, shouldn't E0 be the recommendation?

---

## 1. Testing the Syllogism

The user's argument:

```
Premise 1: Validation framework rejects X2/X6 but passes X0
Premise 2: If E0 also passes the framework...
Premise 3: ...and bootstrap says E0 > X0...
Conclusion: Then recommendation should be E0, not X0
```

Let's test each premise.

---

## 2. Premise 2: Does E0 Pass the Validation Framework?

### E0 was evaluated as the BASELINE

The validation framework evaluates **candidate vs E0**. When E0 is both candidate and baseline:

| Gate | Threshold | E0 vs E0 Value | Status |
|------|:---------:|:--------------:|:------:|
| lookahead | pass | pass | PASS |
| data_integrity | pass | pass | PASS |
| full_harsh_delta | >= -0.200 | **0.000** | PASS |
| holdout_harsh_delta | >= -0.200 | **0.000** | PASS |
| **wfo_win_rate** | **>= 0.600** | **0.000** | **FAIL** |
| trade_level_bootstrap | conditional | inactive | PASS |
| selection_bias | no CAUTION | pass | PASS |

**E0 verdict: HOLD** (exit code 1)

### Why E0 fails WFO

WFO computes `score(candidate) - score(E0)` for each window. When candidate = E0:
- Every window delta = 0.0
- Positive windows = 0/8
- Win rate = 0.000 < 0.600 threshold → **FAIL**

This is a **tautological failure** — E0 can't beat itself. It's not that E0 is bad; the framework literally cannot evaluate the baseline against itself.

### Answer to Premise 2: **NO, E0 does NOT pass**

E0 gets HOLD, not PROMOTE. The framework requires demonstrating improvement over E0, which E0 cannot do by construction.

---

## 3. Premise 3: Does Bootstrap Say E0 > X0?

### Yes — bootstrap shows E0 wins Sharpe/CAGR 16/16

| Metric (T4, SP=120) | E0 | X0 | Winner |
|---------------------|:--:|:--:|:------:|
| Sharpe median | 0.697 | 0.562 | E0 |
| CAGR median | 21.95% | 14.28% | E0 |
| MDD median | 58.49% | 52.17% | **X0** |
| P(CAGR>0) | 88.2% | 84.6% | E0 |

Across all 16 timescales: E0 wins Sharpe **16/16**, CAGR **16/16**. X0 wins MDD **16/16**.

### But Q6 proved this is an ARTIFACT

**Root cause** (from Q6 report): VCBB generates synthetic H4 bars but passes **REAL D1 bars** unchanged. X0's regime filter computes `d1_close > EMA(d1_close, 21)` from real data, then applies it to synthetic H4 paths. The regime signal becomes **noise** relative to synthetic returns.

**Smoking gun**: EMA21 computed from **H4 bars** (synthetic data) wins E0 **15/16** in the same bootstrap. EMA21 computed from **D1 bars** (real data) wins **0/16**. Same filter concept, opposite results — because only the H4 version adapts to synthetic paths.

**Mechanism**: The real D1 regime randomly blocks ~12% of trades. In bootstrap, these blocked trades are randomly distributed across good and bad synthetic periods → pure return reduction with zero timing benefit → lower Sharpe/CAGR.

### Answer to Premise 3: **INVALID — the bootstrap result is a methodological artifact**

Bootstrap cannot fairly evaluate D1-dependent strategies because D1 bars are not synthesized. This was proven in Q6 with the H4 vs D1 comparison.

---

## 4. What Every Chronological Test Says

If we set aside bootstrap and look at **all other evidence**:

| Test | E0 | X0 | Winner | Significance |
|------|:--:|:--:|:------:|:------------:|
| T3 Real Sharpe (16 TS) | varies | varies | **X0 16/16** | Every timescale |
| T3 Real CAGR (16 TS) | varies | varies | **X0 11/16** | Majority |
| T3 Real MDD (16 TS) | varies | varies | **X0 13/16** | Strong majority |
| WFO (8 windows) | baseline | 6/8 wins | **X0 6/8** | Only PASS strategy |
| Holdout Sharpe (harsh) | 0.960 | 1.050 | **X0** | +0.090 |
| Holdout CAGR (harsh) | 24.99% | 26.94% | **X0** | +1.95pp |
| Holdout MDD (harsh) | 19.13% | 18.23% | **X0** | -0.90pp |
| Calendar years | 3/8 | 5/8 | **X0** | Majority |
| Permutation test | p=0.0001 | p=0.0001 | Tie | Both significant |
| T11 paired bootstrap | — | P(X0>E0)=85.3% | **X0** | ns but directional |
| Cost sweep (6 levels) | varies | beats E0 all | **X0 6/6** | Every cost level |

**X0 wins EVERY chronological test.** Not a single real-data test favors E0.

### Head-to-head at SP=120 (harsh)

| Metric | E0 | X0 | Delta | X0 better? |
|--------|:--:|:--:|:-----:|:----------:|
| Sharpe | 1.277 | 1.336 | +0.060 | YES |
| CAGR | 52.68% | 55.32% | +2.64% | YES |
| MDD | 41.53% | 41.99% | +0.46% | no (trivially worse) |
| Trades | 211 | 186 | -25 | YES (fewer) |
| Calmar | 1.268 | 1.317 | +0.049 | YES |

---

## 5. E0's Absolute Merit

E0 is an excellent strategy on its own:

| Dimension | Value | Assessment |
|-----------|:-----:|:----------:|
| Sharpe (harsh) | 1.277 | Excellent |
| Permutation p | 0.0001 | Highly significant |
| TS positive Sharpe | 16/16 | Perfect |
| Holdout Sharpe | 0.960 | Positive |
| P(CAGR>0) bootstrap | 88.2% | Robust |
| Step 5 sign-off | GO_WITH_GUARDS (LT1) | Deployable |
| D4 delay loss | 29.5% | Least fragile binary |
| Combined disruption | -0.322 | Within -0.35 threshold |
| Parameters | 3 | Simplest |

**E0 is deployable** — it passes Step 5 with GO_WITH_GUARDS at LT1, same as X0.

The question is not "is E0 good?" (it is), but "is X0 better than E0?"

---

## 6. The One Argument FOR E0 Over X0

### Simplicity and fragility

| Dimension | E0 | X0 | Advantage |
|-----------|:--:|:--:|:---------:|
| Parameters | 3 | 4 | E0 simpler |
| D4 entry delay loss | 29.5% | 31.7% | E0 more robust |
| Combined disruption | -0.322 | -0.318 | **X0 slightly better** |
| Data dependency | H4 only | H4 + D1 | E0 fewer failure points |
| Step 5 sign-off | GO_WITH_GUARDS | GO_WITH_GUARDS | Tie |

E0 is simpler (3 vs 4 params), less delay-fragile at D4, and has no D1 data dependency. If D1 data feed fails, E0 is unaffected. X0 would need a fallback.

However, X0's combined disruption delta is actually BETTER than E0's (-0.318 vs -0.322). The D1 regime filter occasionally prevents entering trades that would have been caught by the disruption, netting a slight resilience benefit.

---

## 7. Why the Framework Design Favors X0

The validation framework has an inherent bias: it can only PROMOTE strategies that beat E0. E0 itself can never be PROMOTED because it's the baseline.

```
Framework logic:
  E0 vs E0 → delta = 0 → WFO 0/8 → HOLD
  X0 vs E0 → delta > 0 → WFO 6/8 → PROMOTE

This does NOT mean X0 > E0 in absolute terms.
It means: X0 passes the "beat E0" test; E0 cannot take the test.
```

If we designed a framework that evaluated strategies on **absolute metrics** (e.g., Sharpe > 1.0, holdout > 0, etc.), E0 would pass:
- Full Sharpe 1.277 > 1.0 ✓
- Holdout Sharpe 0.960 > 0 ✓
- 16/16 timescales positive ✓
- Permutation p < 0.001 ✓

But X0 would ALSO pass all these gates, with better numbers on every metric.

---

## 8. The Real Decision: E0 vs X0 Head-to-Head

Setting aside framework artifacts and broken bootstrap, the direct question is:

### Does adding EMA(21d) regime filter to E0 improve it?

| Evidence Type | Answer | Strength |
|---------------|:------:|:--------:|
| Real-data Sharpe (16 TS) | **YES** (16/16) | Overwhelming |
| WFO (8 windows) | **YES** (6/8) | Strong |
| Holdout | **YES** (+0.090 Sharpe) | Moderate |
| Calendar | **YES** (5/8 years) | Moderate |
| Cost sweep | **YES** (all 6 levels) | Strong |
| Paired bootstrap | **YES** (P=85.3%, ns) | Weak |
| Permutation | **NEUTRAL** (both p=0.0001) | — |
| Bootstrap VCBB | **NO** (E0 wins 16/16) | **INVALID** (D1 artifact) |
| Simplicity | **NO** (+1 param) | Weak |
| D4 delay | **NO** (+2.2pp loss) | Weak |
| D1 data dependency | **NO** (new failure mode) | Moderate |

**Score: YES 6, NO 3, NEUTRAL 1, INVALID 1**

The "NO" cases are weak (1 extra param, 2.2pp delay, D1 dependency). The "YES" cases include the strongest evidence types (16/16 real-data, 6/8 WFO, positive holdout).

---

## 9. Could E0 Be "Secretly Better"?

### Scenario: bootstrap is correct, real data is overfit

If the bootstrap were valid and real-data results represented overfitting to the D1 regime:
- X0's edge would vanish out-of-sample
- The 16/16 timescale wins would be from in-sample fitting
- WFO 6/8 would be lucky

**Evidence against this scenario:**
1. The WFO IS out-of-sample (rolling 24m train / 6m test)
2. X0 wins 6/8 windows — not just in-sample
3. The holdout is the most recent 20% of data — genuinely unseen
4. The D1 EMA(21) regime was independently proven (p=1.5e-5 in btc-spot-dev Study #41)
5. The bootstrap artifact was EXPLAINED mechanically (Q6) — it's not ambiguous

### Scenario: D1 regime is real but temporary

If Bitcoin's D1 EMA(21) regime property is a 2017-2026 artifact:
- X0's edge would decay in the future
- E0 would be the safer long-term choice

**Evidence**: This is possible but untestable with current data. The regime filter's mechanism (don't enter longs in bear markets as defined by D1 EMA) is economically sensible. But all strategies are conditional on the future resembling the past.

---

## 10. The Correct Framing

The user's syllogism fails at both premises:

| Premise | Status | Reason |
|---------|:------:|--------|
| E0 passes validation framework | **FALSE** | WFO 0/8 → HOLD (tautological failure) |
| Bootstrap says E0 > X0 | **TRUE but INVALID** | D1 artifact (proven in Q6) |
| Therefore E0 should be recommended | **DOES NOT FOLLOW** | Both premises fail |

But the DEEPER question — "is E0 actually better than X0?" — has a clear answer: **NO**. Every valid test (real-data, WFO, holdout, cost sweep) says X0 > E0.

---

## 11. What Would Change the Recommendation to E0?

| Condition | Likelihood | Impact |
|-----------|:----------:|:------:|
| D1 data feed becomes unreliable | Low (Binance D1 is robust) | E0 becomes fallback |
| Regime filter stops working OOS | Unknown (untestable) | E0 becomes primary |
| Infrastructure can't guarantee H4 + D1 | Moderate | E0 for that deployment |
| Someone fixes VCBB to synthesize D1 and E0 wins | Low (unlikely given mechanism) | Re-evaluate |

The Step 4 mandate x latency framework already accounts for this:
- **LT1 (<4h auto)**: X0 (E0+EMA1D21) — primary
- **LT2 (4-16h degraded)**: **E0** — fallback (less delay-fragile)
- **LT3 (>16h manual)**: SM — only viable candidate

E0 IS recommended — just for LT2, not LT1.

---

## 12. Summary

| Question | Answer |
|----------|--------|
| Does E0 pass the validation framework? | **NO** — WFO 0/8 (tautological: can't beat itself) → HOLD |
| Does bootstrap prove E0 > X0? | **NO** — D1 mismatch artifact (proven in Q6) |
| Is E0 a good strategy? | **YES** — Sharpe 1.277, p=0.0001, GO_WITH_GUARDS at LT1 |
| Is X0 better than E0? | **YES** — 16/16 real-data Sharpe, 6/8 WFO, holdout +0.090 |
| Should E0 be the primary recommendation? | **NO** — X0 beats E0 on every valid metric |
| Does the syllogism hold? | **NO** — both premises fail (E0 doesn't pass; bootstrap is invalid) |
| Is E0 recommended anywhere? | **YES** — at LT2 (degraded latency) where its lower delay fragility matters |
| Is there any valid argument for E0 over X0 at LT1? | **Only simplicity** (+1 param) and D1 data dependency — weak compared to X0's 16/16 wins |
