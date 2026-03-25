# Research Q2: WFO Threshold — Where, Why, and Statistical Validity

**Date**: 2026-03-08

---

## 1. Where is the threshold hardcoded?

**Single source of truth**: `validation/thresholds.py:27`

```python
WFO_WIN_RATE_THRESHOLD: float = 0.60
```

### How it's applied

**`validation/suites/wfo.py:526-531`** — the evaluation harness:

```python
threshold_windows = (
    max(n_windows - 1, 0)
    if n_windows <= WFO_SMALL_SAMPLE_CUTOFF     # ≤ 5 windows: require N-1
    else int((WFO_WIN_RATE_THRESHOLD * n_windows) + 0.999999)  # > 5: ceil(0.60 × N)
)
status = "pass" if positive_delta_windows >= threshold_windows else "fail"
```

For N=8: `ceil(0.60 × 8) = 5`, so **5/8 required to pass**.

**`validation/decision.py:370-373`** — the decision gate:

```python
required_ratio = policy.wfo_win_rate_threshold
passed = win_rate >= required_ratio
```

Gate severity: **soft** (causes HOLD, not REJECT). But in X6's case, combined with holdout failure (hard gate), the overall verdict is REJECT.

---

## 2. Is there documentation for why 60%?

### Report 32: Threshold Provenance & Heuristic Governance Audit

Provenance class: **UNPROVEN (H04)**

From `thresholds.py` comments (lines 24-26):
> "60% does not correspond to a standard significance level for typical window counts.
> Future calibration recommended (Report 32 section 11.2 item 5)."

From Report 32 section 3.4:
> "Bare default on DecisionPolicy. For N=8 windows, 60% requires 5/8 positive.
> Under H₀ (fair coin), P(≥5/8) = 0.363 — this does NOT correspond to any
> standard significance level."

**Bottom line**: No formal derivation exists. It was a design choice, not a statistical result. Report 32 explicitly recommends future calibration via simulation with known-null and known-positive strategy pairs.

---

## 3. Binomial Analysis: What does 4/8 vs 5/8 actually mean?

### Under H₀ (true win probability = 0.5, i.e., strategy is coin-flip vs baseline)

| k/8 | P(X ≥ k) | Interpretation |
|:---:|:--------:|----------------|
| 4/8 | 0.6367 | X6 observed — **cannot reject H₀** |
| 5/8 | 0.3633 | Current PASS threshold — **still cannot reject H₀** |
| 6/8 | 0.1445 | Stricter — still p > 0.10 |
| 7/8 | 0.0352 | First level that's p < 0.05 |
| 8/8 | 0.0039 | Only level that's p < 0.01 |

**Neither 4/8 nor 5/8 is statistically significant.** The threshold distinguishes between p=0.64 and p=0.36 under H₀ — neither is meaningful.

### 95% Clopper-Pearson Confidence Intervals

| Observed | Point Est. | 95% CI | 90% CI |
|:--------:|:----------:|:------:|:------:|
| 4/8 | 50.0% | [15.7%, 84.3%] | [19.3%, 80.7%] |
| 5/8 | 62.5% | [24.5%, 91.5%] | [28.9%, 88.9%] |

The 95% CIs **massively overlap**: [15.7%, 84.3%] vs [24.5%, 91.5%]. The distinction between 4/8 and 5/8 carries **almost zero statistical information** about the true win rate.

### Power Analysis: P(pass at 5/8 threshold | true win probability)

| True p | P(≥ 5/8) | Interpretation |
|:------:|:--------:|----------------|
| 0.50 | 36.3% | False positive rate under H₀ |
| 0.55 | 47.7% | Barely better than coin flip |
| 0.60 | 59.4% | At the nominal threshold — only 59% power |
| 0.65 | 70.6% | Reasonable true advantage — 30% false negative |
| 0.70 | 80.6% | Strong advantage — still 19% false negative |
| 0.75 | 88.6% | Very strong advantage |
| 0.80 | 94.4% | Dominant strategy |

Even if X6 truly wins 65% of windows, there's a **29.4% chance** it fails the 5/8 gate — nearly 1 in 3 false negatives.

---

## 4. The 1-Window Knife-Edge Problem

With N=8 windows, the entire PASS/FAIL decision hinges on **a single window**:

```
4/8 = 50.0% → FAIL
5/8 = 62.5% → PASS
```

**This is a ±12.5 percentage point swing from 1 window.** The binary gate treats this as a categorical distinction, but the underlying data cannot support that precision.

### Minimum k for statistical significance (N=8)

| Significance level | Required k | Win rate | Achievable? |
|:------------------:|:----------:|:--------:|:-----------:|
| α = 0.10 | 7/8 | 87.5% | Very hard |
| α = 0.05 | 7/8 | 87.5% | Very hard |
| α = 0.01 | 8/8 | 100% | Essentially impossible |

**With only 8 windows, you fundamentally cannot distinguish signal from noise at any reasonable significance level unless the strategy wins nearly every window.**

---

## 5. Implications for X6

X6's WFO result of 4/8 is treated as categorical FAIL, but:

1. **The threshold itself is unproven** — no statistical basis for 60% vs 55% vs 65%
2. **4/8 vs 5/8 is statistically indistinguishable** — CIs overlap by ~60 percentage points
3. **The test has no power** — even 5/8 PASS has p=0.36 under H₀ (not significant)
4. **X6's 4 winning windows have much larger magnitude** — mean delta when positive is +48.9 vs mean delta when negative is -29.0
5. **The WFO gate is soft** — Report 32 found it caused ZERO verdict flips across 12 counterfactual scenarios on 38 archived runs

### Alternative evaluation approaches for N=8

Rather than a binary win-rate gate, more informative approaches include:
- **Signed-rank test** on delta magnitudes (accounts for effect size, not just sign)
- **Mean/median delta** with bootstrap CI (already computed: mean +9.94, median +4.64)
- **Weighted win rate** by window quality/length
- **Leave-one-out sensitivity** (how many single-window removals flip the verdict?)

---

## 6. Summary

| Question | Answer |
|----------|--------|
| Where hardcoded? | `validation/thresholds.py:27`, used in `suites/wfo.py:526-531` and `decision.py:370-373` |
| Why 60%? | **No statistical derivation.** Bare design choice, explicitly flagged as UNPROVEN (Report 32, H04) |
| 4/8 vs 5/8 CI? | 95% CIs: [15.7%, 84.3%] vs [24.5%, 91.5%] — **massive overlap, indistinguishable** |
| Statistical power? | At true p=0.65, power is only 70.6% — **1 in 3 false negatives** |
| Gate severity? | Soft (HOLD, not REJECT) — but combined with holdout hard-fail, contributes to REJECT |
