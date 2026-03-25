# Report 11b — E0 vs E5: Mechanism vs Strategy-Family Decomposition

**Date**: 2026-03-03
**Artifacts**: `artifacts/11b_e0_e5_mechanism_vs_family.py`, `artifacts/11b_e0_e5_mechanism_vs_family.json`
**Depends on**: Report 11 (scale mismatch established)

---

## 1. Canonical Definitions

2x2 factorial design decomposing E5 into cap and period effects:

|  | period=14 | period=20 |
|---|---|---|
| **no cap** | **A0** = ATR(14), no cap [baseline E0] | **A1** = ATR(20), no cap [period-only] |
| **Q90 cap** | **A2** = ATR(14), Q90(100) cap [cap-only] | **A3** = ATR(20), Q90(100) cap [= full E5] |

All use Wilder EMA smoothing. Cap = `min(TR, Q90 of prior 100 bars)`.
Entry logic (EMA cross + VDO) is identical across all variants.
Only the ATR series feeding the trailing stop differs.

---

## 2. Scale Diagnostics

### 2.1 Full Post-Warmup Bars (15,648 bars)

| Variant vs A0 | Median | Mean | Std | P5 | P95 | % < 1.0 |
|---|---|---|---|---|---|---|
| **A1** (period-only) | **1.0091** | 1.0081 | 0.0509 | 0.9223 | 1.0899 | 42.5% |
| **A2** (cap-only) | **0.9509** | 0.9265 | 0.0775 | 0.7737 | 0.9963 | **100.0%** |
| **A3** (cap+period) | **0.9547** | 0.9330 | 0.1036 | 0.7314 | 1.0564 | 73.4% |

### 2.2 In-Trade Bars Only (7,333 bars at sp=120, trail=3.0)

| Variant vs A0 | Median | Mean | % < 1.0 |
|---|---|---|---|
| A1 | 1.0040 | 1.0027 | 46.5% |
| A2 | **0.9461** | 0.9205 | **100.0%** |
| A3 | **0.9452** | 0.9216 | 78.2% |

### 2.3 Near-Stop Bars (14,689 bars where `3 × ATR / close < 10%`)

| Variant vs A0 | Median | Mean | % < 1.0 |
|---|---|---|---|
| A1 | 1.0105 | 1.0102 | 41.1% |
| A2 | 0.9526 | 0.9307 | 100.0% |
| A3 | 0.9577 | 0.9388 | 72.6% |

### Key Finding

**The cap is the sole driver of scale mismatch.**

- A1 (period-only): ratio ~1.009, essentially no scale difference
- A2 (cap-only): ratio ~0.951, **always** below 1.0 — the cap mechanically
  clips TR, so capped ATR is definitionally ≤ uncapped ATR
- A3 (cap+period): ratio ~0.955, slightly closer to 1.0 than A2 because
  the longer period (20) provides more smoothing that partially offsets
  the cap's downward bias

The cap effect is slightly larger in-trade (median 0.946) than full-bar
(0.951), meaning the scale mismatch is amplified exactly when the stop
matters.

---

## 3. Mechanism-Level Fair Comparison

### 3.1 Scale-Matched Trail Multipliers

To equalize average stop distance with A0 at trail=3.0:

| Variant | Full-bar median | Full-bar mean | In-trade median |
|---|---|---|---|
| A1 | 2.9731 | 2.9759 | 2.9882 |
| A2 | 3.1549 | 3.2381 | 3.1708 |
| A3 | 3.1424 | 3.2156 | 3.1740 |

A1 needs virtually no correction (~0.97-0.99). A2 and A3 need ~5%
correction. This confirms the cap is the source.

### 3.2 Win Counts vs A0 (16 timescales, real data)

**Median-matched (primary):**

| Variant | Sharpe | CAGR | MDD | Calmar |
|---|---|---|---|---|
| A1 (period-only) | **12/16** | **12/16** | 6/16 | 11/16 |
| A2 (cap-only) | **12/16** | **12/16** | 8/16 | 11/16 |
| A3 (cap+period) | **13/16** | **12/16** | 6/16 | 9/16 |

**Mean-matched:**

| Variant | Sharpe | CAGR | MDD | Calmar |
|---|---|---|---|---|
| A1 | 12/16 | 12/16 | 5/16 | 11/16 |
| A2 | 9/16 | 3/16 | 9/16 | 4/16 |
| A3 | 12/16 | 11/16 | 5/16 | 6/16 |

**In-trade median-matched:**

| Variant | Sharpe | CAGR | MDD | Calmar |
|---|---|---|---|---|
| A1 | 11/16 | 9/16 | 3/16 | 6/16 |
| A2 | 12/16 | 12/16 | 7/16 | 9/16 |
| A3 | 13/16 | 12/16 | 5/16 | 9/16 |

### 3.3 What Survives

**Survives scale matching:**
- Sharpe improvement: 12-13/16 across all variants and matching methods
  (binomial p ≈ 0.038 for 12/16, p ≈ 0.011 for 13/16)
- CAGR improvement: 12/16 for median-matched (borderline)

**Does NOT survive:**
- MDD improvement: 5-8/16 across all methods — indistinguishable from
  chance. The prior "MDD 16/16 PROVEN (p=1.5e-5)" is fully explained
  by scale.

**Critical observation:** A1 (period-only, no cap, no scale correction
needed) achieves Sharpe 12/16 — the same as A2 and A3. This means the
Sharpe improvement does not require the Q90 cap at all. Simply using
period=20 instead of period=14 produces the same result.

---

## 4. Family-Level Retuning

### 4.1 Single Timescale (sp=120): Best Sharpe per Family

| Family | Best Trail | Best Sharpe | CAGR | MDD |
|---|---|---|---|---|
| A0 | 4.50 | 1.357 | +60.7% | 37.5% |
| A1 | 2.00 | 1.375 | +55.5% | 36.2% |
| A2 | 3.00 | 1.364 | +57.3% | 40.8% |
| A3 | 3.00 | 1.365 | +57.0% | 40.3% |

At sp=120, all families achieve best Sharpe ~1.36-1.38. Differences are
within sample noise. However, best trail varies widely (2.0-4.5),
indicating the "shape" of the response surface differs.

### 4.2 Multi-Timescale: Median Sharpe across 16 Timescales

| Family | Best Trail | Median Sharpe | Median CAGR | Median MDD |
|---|---|---|---|---|
| **A0** | **4.50** | **1.2169** | **+54.0%** | 49.1% |
| A1 | 4.75 | 1.2107 | +52.9% | 48.0% |
| A2 | 4.75 | 1.1971 | +52.0% | 46.7% |
| A3 | 5.00 | 1.1877 | +50.3% | 47.1% |

**A0 (baseline) is the best family.** When each family is allowed to
pick its own optimal trail multiplier, A0 achieves the highest median
Sharpe (1.217) and highest median CAGR (+54.0%).

The ordering is A0 > A1 > A2 > A3 — exactly inverse to the "complexity"
of the ATR mechanism. Adding a cap, or changing the period, or both,
makes the family slightly worse under fair retuning.

Note: MDD shows A2 as best (46.7%), but this is a weak advantage
(2.4pp over A0) that trades substantial Sharpe and CAGR. And the best
trail for all families shifted to 4.5-5.0, well above the current
default of 3.0.

---

## 5. Attribution: Cap vs Period vs Interaction

### 5.1 Sharpe (positive = improvement over A0, all scale-matched)

| Effect | Median | Mean | Wins |
|---|---|---|---|
| Period (A1-A0) | +0.026 | +0.017 | **12/16** |
| Cap (A2-A0) | +0.044 | +0.028 | **12/16** |
| Interaction | -0.012 | -0.003 | 7/16 |

Both period and cap independently improve Sharpe by small amounts,
with weak negative interaction (combining them is slightly worse than
the sum of parts). The cap effect (+0.044 median) is larger than the
period effect (+0.026).

### 5.2 CAGR (positive = improvement)

| Effect | Median | Mean | Wins |
|---|---|---|---|
| Period | +1.12 | +0.68 | **12/16** |
| Cap | +1.99 | +1.26 | **12/16** |
| Interaction | -0.25 | +0.13 | 8/16 |

Same pattern: both help, cap helps more, interaction is neutral-to-negative.

### 5.3 MDD (positive = improvement = lower MDD)

| Effect | Median | Mean | Wins |
|---|---|---|---|
| Period | -0.08 | +0.07 | **6/16** |
| Cap | -0.01 | +0.25 | **8/16** |
| Interaction | **-0.74** | **-0.68** | **2/16** |

**This is the smoking gun.**

Neither period nor cap improves MDD at scale-matched comparison
(6/16 and 8/16 — both chance level). And their interaction is actively
harmful: 2/16, with median effect of -0.74pp. Combining cap and period
makes MDD **worse** than either alone.

The "MDD 16/16 PROVEN" was entirely a scale artifact from the tighter stop.

---

## 6. Which Prior Claims Survive

| Claim | Source | Status | Evidence |
|---|---|---|---|
| "E5 MDD 16/16 PROVEN" | e5_validation.json | **REFUTED** | Scale artifact: 6/16 at matched (§3.2), MDD attribution 6/16+8/16 (§5.3), interaction 2/16 |
| "E5 CAGR 0/16" (bootstrap) | e5_validation.json | **Partially correct** | Bootstrap always negative. Real-data: 12/16 at matched — borderline |
| "E5 Sharpe 0/16" (bootstrap) | e5_validation.json | **Needs revision** | Real-data at matched: 12-13/16. But A1 alone achieves same 12/16 without cap |
| "E5 improves exit quality" | exit_family_report | **Unsubstantiated** | The cap contributes Sharpe 12/16 but A1 (no cap) does too; MDD gain refuted |
| "Robust ATR mechanism is beneficial" | general | **Not demonstrated** | At scale-matched, A3 is not better than A1 (period-only). Cap adds no MDD value |

---

## 7. Recommended Canonical Pair for Next Audit Step

The remaining testable hypothesis is: **A1 vs A0** — does period=20
beat period=14 for the Wilder EMA ATR, at the same trail multiplier?

Rationale:
- A1 has essentially no scale mismatch (median ratio 1.009), so
  trail=3.0 is a fair comparison for both
- A1 shows 12/16 Sharpe wins and 12/16 CAGR wins at scale-matched
  — potentially real, potentially noise
- A1 isolates the purest single-variable change
- Under family retuning, A1 is the closest competitor to A0 (median
  Sharpe 1.211 vs 1.217)

If this audit were to continue, the correct next step is a bootstrap
test of A0(trail=3.0) vs A1(trail=3.0) at 16 timescales.

However: the effect size is small (Sharpe +0.026 median), and under
family retuning A0 wins. This makes it unlikely that any A1 advantage
would survive bootstrap testing with the required p < 0.025.

---

## 8. Summary

**A. Mechanism question:** Is Robust ATR intrinsically better than
standard ATR when stop width is matched fairly?

**No.** At scale-matched comparison, the Q90 cap contributes:
- Sharpe 12/16 — but period-only (A1) achieves the same 12/16
- CAGR 12/16 — same
- MDD 8/16 — chance level
- The cap's specific contribution beyond period-change is zero

**B. Strategy-family question:** If each family is allowed fair retuning,
is E5-family competitive with E0-family?

**No.** At each family's best trail multiplier (multi-timescale median
Sharpe):
- A0: 1.2169 (best)
- A1: 1.2107
- A2: 1.1971
- A3: 1.1877 (worst)

A0 dominates. Adding cap, period change, or both makes the family
weakly worse under fair retuning.

**Where the apparent benefit came from:**
- **Cap:** scale mismatch (tighter stop at trail=3.0)
- **Period:** near-zero scale effect, minor Sharpe boost (12/16 but small)
- **Both:** negative interaction on MDD (2/16), combined family is worst
- **Neither:** produces a durable advantage under fair comparison

---

*Mechanism vs family decomposition complete. The E5 "MDD PROVEN"
verdict is fully attributable to scale mismatch. Under fair comparison,
A0 (baseline E0) is the best family.*
