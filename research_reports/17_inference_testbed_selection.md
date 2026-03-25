# Report 17 — Inference Testbed Selection

**Date**: 2026-03-03
**Artifacts**: `artifacts/17_inference_testbed_selection.py`, `artifacts/17_inference_testbed_selection.json`
**Purpose**: Choose a negative-control pair and a positive-control pair for
inference-method evaluation.

---

## 1. Pair Matrix

### 1.1 Strategy Universe

Six strategies simulated at matched settings (sp=120, trail=3.0,
ATR(14), harsh cost 50bps RT, 2019-01-01 to 2026-02-20):

| Strategy | Architecture | Sharpe | CAGR | MDD | Trades | In-Rate |
|---|---|---|---|---|---|---|
| **VTREND_A0** | EMA cross + ATR(14) trail + VDO | 1.276 | +52.7% | 41.5% | 189 | 46.9% |
| **VTREND_A1** | EMA cross + ATR(20) trail + VDO | 1.283 | +52.6% | 41.7% | 188 | 46.5% |
| **VBREAK** | Donchian breakout + ATR trail + VDO | 1.179 | +35.2% | 34.0% | 69 | 22.0% |
| **VCUSUM** | CUSUM change-point + ATR trail + VDO | 0.934 | +25.2% | 28.5% | 73 | 20.7% |
| **VTWIN** | EMA + Donchian dual-confirm + ATR trail + VDO | 1.244 | +37.5% | 29.9% | 67 | 21.6% |
| **BUY_HOLD** | Passive 100% from warmup end | 0.972 | +50.3% | 77.0% | 1 | 100.0% |

### 1.2 Full Pair Diagnostics

15 pairs. Columns: return correlation, same-direction rate, exact-return-
equality rate, within-1bp/10bp/50bp rates, exposure-agreement rate,
both-in rate, Sharpe/CAGR differences.

| Pair | Corr | Same-Dir | Exact-Eq | <1bp | <10bp | Exp-Agree | Both-In | ΔSh | ΔCAGR |
|---|---|---|---|---|---|---|---|---|---|
| A0 vs A1 | 0.987 | 99.6% | **98.8%** | 98.9% | 98.9% | 99.2% | 46.3% | -0.006 | +0.1% |
| A0 vs VBREAK | 0.735 | 86.9% | 73.2% | 73.5% | 76.5% | 74.4% | 21.6% | +0.098 | +17.5% |
| A0 vs VCUSUM | **0.525** | 81.5% | **62.7%** | 63.2% | 67.2% | 64.1% | 15.8% | **+0.343** | **+27.5%** |
| A0 vs VTWIN | 0.735 | 86.9% | 73.2% | 73.5% | 76.5% | 74.3% | 21.4% | +0.033 | +15.2% |
| A0 vs BUY_HOLD | 0.638 | 72.7% | 45.7% | 46.3% | 52.7% | 46.9% | 46.9% | +0.304 | +2.4% |
| A1 vs VBREAK | 0.724 | 86.7% | 72.6% | 73.0% | 76.1% | 73.9% | 21.2% | +0.104 | +17.4% |
| A1 vs VCUSUM | 0.524 | 81.6% | 62.8% | 63.2% | 67.3% | 64.1% | 15.7% | +0.349 | +27.4% |
| A1 vs VTWIN | 0.723 | 86.7% | 72.6% | 73.0% | 76.0% | 73.9% | 21.0% | +0.039 | +15.1% |
| A1 vs BUY_HOLD | 0.632 | 72.5% | 45.3% | 45.9% | 52.4% | 46.5% | 46.5% | +0.311 | +2.3% |
| VBREAK vs VCUSUM | 0.639 | 91.4% | 83.0% | 83.2% | 85.0% | 83.6% | 13.2% | +0.245 | +10.0% |
| **VBREAK vs VTWIN** | **0.993** | **99.9%** | **99.6%** | 99.6% | 99.7% | 99.6% | 21.6% | -0.065 | -2.3% |
| VBREAK vs BUY_HOLD | 0.475 | 60.0% | 21.6% | 22.5% | 31.9% | 22.0% | 22.0% | +0.207 | -15.1% |
| VCUSUM vs VTWIN | 0.632 | 91.4% | 82.9% | 83.1% | 84.9% | 83.5% | 12.9% | -0.310 | -12.3% |
| VCUSUM vs BUY_HOLD | 0.462 | 59.3% | 20.3% | 21.3% | 30.6% | 20.7% | 20.7% | -0.038 | -25.1% |
| VTWIN vs BUY_HOLD | 0.472 | 59.8% | 21.2% | 22.2% | 31.6% | 21.6% | 21.6% | +0.271 | -12.8% |

---

## 2. Pair Classification

### 2.1 Classification Criteria

- **Too identical**: exact-equality rate > 80%, or corr > 0.99.
  The differential series is >80% zeros — no inference method can
  extract a signal from this. Useless for method comparison.
- **Near-null / negative control**: true metric differences near zero
  on all dimensions; enough divergent bars to give the method data.
- **Plausible main testbed**: moderate correlation (0.70-0.95), clear
  but not overwhelming metric gap.
- **Positive control**: low correlation (<0.75), or large Sharpe gap
  (|ΔSh| > 0.25), with substantial divergence. If an inference
  method fails to detect this difference, it lacks power.

### 2.2 Classification Table

| Pair | Class | Difference Type |
|---|---|---|
| A0 vs A1 | **Negative control** | Parameter tweak (ATR period 14 → 20) |
| A0 vs VBREAK | Plausible testbed | Different entry, shared exit |
| **A0 vs VCUSUM** | **Positive control** | Different entry, shared exit |
| A0 vs VTWIN | Plausible testbed | Different entry, shared exit |
| A0 vs BUY_HOLD | Positive control | Genuinely different architecture |
| VBREAK vs VTWIN | Exclude (too identical) | Different entry, but 99.6% identical output |
| VBREAK vs VCUSUM | Exclude (too identical) | 83% exact equality from both being OUT |
| VCUSUM vs VTWIN | Exclude (too identical) | 83% exact equality from both being OUT |
| * vs BUY_HOLD | Secondary positive control | Active vs passive |

### 2.3 Why VBREAK/VCUSUM/VTWIN Cross-Pairs Are Useless

VBREAK, VCUSUM, and VTWIN are each in-position only ~21% of the time.
On the ~79% of bars where both are out, both hold cash, producing
exactly identical returns. This creates 80-83% exact equality regardless
of architectural differences. The paired differential is >80% zeros.
These pairs cannot distinguish inference methods.

### 2.4 Why VBREAK vs VTWIN Is a Surprise

Despite genuinely different entry architectures (Donchian-only vs EMA +
Donchian), they produce 99.6% identical bar-level returns. At sp=120,
the EMA cross-up condition is almost always already true when close
breaks above the 120-bar highest high. The Donchian confirmation in
VTWIN is nearly redundant with the EMA condition in VBREAK's trading
range. This is an interesting structural finding but makes the pair
useless for testing.

---

## 3. Recommended Negative-Control Pair

### VTREND_A0 vs VTREND_A1

| Property | Value |
|---|---|
| ΔSharpe | -0.006 |
| ΔCAGR | +0.1% |
| ΔMDD | -0.2% |
| Return correlation | 0.987 |
| Exact-equality rate | 98.8% |
| Exposure agreement | 99.2% |
| Divergent bars | ~188 of 15,647 (1.2%) |
| Difference type | Parameter tweak: ATR period 14 → 20 |

**Why this pair.** The true difference is as close to zero as the repo
offers, on ALL metrics simultaneously (Sharpe, CAGR, MDD). Any
inference method that declares this pair significantly different is
producing a false positive.

**Limitation.** 98.8% of bar returns are identical. This is an easy null
— it tests basic correctness, not resistance to false positives in the
presence of noise. There is no available pair that combines a true-null
outcome with substantial bar-level divergence. The repo's strategy
families are either near-clones or clearly different.

**What it tests.** Whether the inference method avoids false positives
when the differential series is dominated by exact zeros with rare,
small perturbations. A method that fails this test is fatally flawed.
A method that passes this test has demonstrated only the minimum
standard.

---

## 4. Recommended Positive-Control Pair

### VTREND_A0 vs VCUSUM

| Property | Value |
|---|---|
| ΔSharpe | +0.343 |
| ΔCAGR | +27.5% |
| ΔMDD | -13.0% (VCUSUM lower MDD but much less return) |
| Return correlation | 0.525 |
| Exact-equality rate | 62.7% |
| Exposure agreement | 64.1% |
| Divergent bars | ~5,832 of 15,647 (37.3%) |
| Difference type | Different entry architecture (EMA cross vs CUSUM change-point) |

**Why this pair.** Largest Sharpe gap among active-vs-active pairs
(+0.343). Lowest correlation (0.525). Highest divergent-bar rate among
active pairs (37.3%). Genuinely different entry mechanism (EMA momentum
crossover vs statistical change-point detection). Shared exit framework
(ATR trail + secondary signal exit), so the difference is cleanly
attributable to entry quality.

**What it tests.** Whether the inference method can detect a ΔSharpe of
+0.343 with 37% divergent bars and ρ = 0.53. If a method fails here,
it cannot detect any real differences the project might produce.

**Why not BUY_HOLD pairs.** BUY_HOLD has 100% in-position vs ~20-47%
for active strategies, creating a structurally different return
distribution (always-invested vs intermittent). The active-vs-passive
comparison conflates inference-method power with the trivial observation
that active strategies have fewer market-exposed bars. VCUSUM gives a
cleaner same-framework comparison.

---

## 5. Pairs to Exclude

| Pair | Reason |
|---|---|
| VBREAK vs VTWIN | 99.6% identical despite different architecture — functionally the same strategy |
| VBREAK vs VCUSUM | 83% exact equality from shared out-of-market bars — no signal in differential |
| VCUSUM vs VTWIN | 83% exact equality — same problem |
| Any * vs BUY_HOLD | Structurally different exposure profile confounds the comparison |

These pairs are excluded from the inference-method testbed. They may
have other uses (e.g., BUY_HOLD as a passive benchmark) but they cannot
distinguish between inference methods.

---

## 6. Recommended Next Experiment

Use the two selected pairs (A0 vs A1, A0 vs VCUSUM) to evaluate the
existing inference stack:

1. **For the negative control (A0 vs A1):** run the paired block
   bootstrap and subsampling at the standard configuration (2000
   replicates, block sizes 10/20/40, seed 1337). Verify that both
   methods correctly return "no significant difference." Record the
   p-value / bootstrap probability for calibration.

2. **For the positive control (A0 vs VCUSUM):** run the same paired
   block bootstrap and subsampling. Verify that both methods detect
   the ΔSharpe = +0.343 as significant. If they fail, quantify the
   power gap.

3. **Evaluate:** an inference method is adequate if and only if it:
   - Does NOT reject the null for the negative control
   - DOES reject the null for the positive control
   - Produces calibrated confidence intervals in both cases

This two-pair protocol provides a minimum viable evaluation. If both
methods pass, the positive pair can be used to study calibration
(do the CIs cover the observed ΔSharpe?). If either fails, the failure
mode identifies what needs fixing before the methods can be trusted on
novel pairs.

---

*Testbed selection complete. Two pairs identified, exclusions documented.*
