# Research Q12: DSR Selection Bias — Is It Computing Correctly?

**Date**: 2026-03-08
**Script**: `research/x6/dsr_analysis_q12.py`
**Sources**: `validation/suites/selection_bias.py`, `research/lib/dsr.py`, selection_bias.json outputs
**Question**: DSR=1.000 for all strategies. Is it counting the right number of strategies? Or just testing each strategy vs random?

---

## 1. What DSR Actually Computes

The Deflated Sharpe Ratio (Bailey & López de Prado, 2014) tests:

> **"Could an observed Sharpe of X have been produced by chance if ALL N tested strategies had TRUE Sharpe = 0?"**

Formula:
```
SR₀ = [(1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))] · std
DSR_z = (SR_observed - SR₀) / std
DSR_p = Φ(DSR_z)
```

Where:
- `N` = number of strategies tested (trial count)
- `std` = standard error of SR, corrected for skewness and kurtosis
- `SR₀` = expected maximum Sharpe from N zero-alpha strategies (Gumbel approximation)

**Null hypothesis**: All strategies are random (true SR = 0)
**Alternative**: At least one strategy has genuine alpha

---

## 2. The Implementation

From `validation/suites/selection_bias.py` (line 110):

```python
trial_set = [27, 54, 100, 200, 500, 700]
for trials in trial_set:
    dsr, expected_max_sr, sr_std = _deflated_sharpe(
        sr_observed=observed_sharpe,
        n_trials=trials,
        t_samples=t_samples,
        skew=skew,
        kurt=kurt,
    )
    passed = dsr > 0.95
```

**Key finding**: The trial_set `[27, 54, 100, 200, 500, 700]` is **HARDCODED**. It is NOT the actual number of strategies tested. It does not know about E0/E5/X0/X2/X6/E5+EMA21. It's a stress test: "would this Sharpe survive even if we had tested 27/54/.../700 random strategies?"

---

## 3. Why DSR = 1.000 for ALL Strategies at ALL Trial Counts

### Actual values from selection_bias.json

| Strategy | SR_obs | T (days) | SR_std | SR₀ at N=700 | z-score | DSR |
|----------|:------:|:--------:|:------:|:------------:|:-------:|:---:|
| E0 | 1.265 | 2607 | 0.0458 | 0.144 | 24.5 | **1.000** |
| X0 | 1.325 | 2607 | 0.0484 | 0.153 | 24.2 | **1.000** |
| X2 | 1.423 | 2607 | 0.0522 | 0.165 | 24.1 | **1.000** |
| E5+EMA21 | 1.432 | 2607 | ~0.052 | ~0.164 | ~24.5 | **1.000** |

The observed Sharpe (~1.3) is **24 standard errors** above the expected max from 700 random strategies (~0.15). Φ(24) ≈ 1.0 to machine precision.

### Even at the ACTUAL trial count (N=6), DSR is still 1.0

| Strategy | N=6 SR₀ | z-score | DSR |
|----------|:-------:|:-------:|:---:|
| E0 | 0.060 | 26.3 | 1.000 |
| X0 | 0.063 | 26.1 | 1.000 |
| X2 | 0.068 | 26.0 | 1.000 |

With only 6 strategies, the expected max Sharpe by chance is ~0.06. Still 26σ below observed.

### Even at N=100,000 trials: still 1.000

| Strategy | N=100K SR₀ | z-score | DSR |
|----------|:----------:|:-------:|:---:|
| E0 | 0.201 | 23.3 | 1.000 |
| X0 | 0.213 | 23.0 | 1.000 |

---

## 4. How Many Trials Would Break DSR?

To bring DSR below 0.95 (z < 1.645), SR₀ must approach SR_observed.

| Strategy | N_critical (approx) |
|----------|:-------------------:|
| E0 | **10^147** |
| X0 | **10^144** |
| X2 | **10^142** |
| E5+EMA21 | **10^146** |

You would need to test approximately **10^144 to 10^147 strategies** before DSR drops below 0.95. For context, there are ~10^80 atoms in the observable universe.

**DSR is a vacuous gate for this dataset.** Any strategy with Sharpe > ~0.5 on 2607 daily observations will produce DSR = 1.000 regardless of trial count.

---

## 5. Answer to the User's Question

### "Does DSR count the actual number of strategies tried?"

**NO.** The trial_set is hardcoded `[27, 54, 100, 200, 500, 700]`. It has no knowledge of the actual strategies tested (E0, E5, X0, X2, X6, E5+EMA21 = 6). It doesn't even attempt to estimate the real trial count.

### "Or does it just test each strategy vs random?"

**YES — exactly this.** DSR tests each strategy INDEPENDENTLY against a null of random strategies with zero true Sharpe. It asks: "Is this particular Sharpe real, or could it have appeared by chance among N zero-alpha strategies?"

For strategies with Sharpe > 1.0 on ~2600 daily observations, the answer is trivially "real" at any reasonable N.

---

## 6. What DSR Does NOT Test

The **actual selection bias concern** for this project is:

> "We tested 6 strategies on the same data and picked the 'best' one. Is the ranking genuine, or is the winner just the luckiest of 6?"

This is a **RELATIVE ranking** question:

```
E0:       Sharpe 1.277
X0:       Sharpe 1.336  (delta +0.060 vs E0)
X2:       Sharpe 1.433  (delta +0.097 vs X0)
E5+EMA21: Sharpe 1.432  (delta +0.096 vs X0)
```

**DSR cannot distinguish these.** All four get DSR = 1.000. DSR says "1.277 is real" and "1.433 is real" but says NOTHING about whether the 0.156 gap between them is real or noise.

### The right tools for relative selection bias

| Tool | Tests | This Project |
|------|-------|:------------:|
| **WFO** | OOS ranking stability | X0 6/8, X2 4/8 |
| **Holdout** | Unseen-data performance | X0 +0.090 vs E0 |
| **Paired bootstrap (T11)** | P(A>B) with multiple testing | All pairs ns (Holm) |
| **Permutation test** | Absolute significance | All p=0.0001 |
| **DSR** | Is Sharpe > 0 after selection? | **Trivially yes for all** |

The validation framework **already handles** relative selection bias through WFO + holdout. The DSR gate is redundant for this purpose.

---

## 7. Is This a Framework Bug?

### Not exactly — it's a design limitation

DSR was designed for a different regime: hedge funds testing thousands of low-Sharpe strategies on short datasets. In that world:
- Observed Sharpe ≈ 0.3-0.8
- N trials ≈ 100-1000
- T ≈ 500-1000 daily observations
- SR₀ at N=500, T=500: ≈ 0.30 → can approach observed SR → DSR is informative

In THIS project:
- Observed Sharpe ≈ 1.0-1.4 (BTC trend-following is genuinely strong)
- N trials ≈ 6-200
- T ≈ 2607 daily observations (7+ years)
- SR₀ at N=700, T=2607: ≈ 0.15 → 10× smaller than observed → DSR is vacuous

### The suite knows this

Report 21, §3 classifies DSR as **"advisory only"** with no decision authority:
> "DSR is a single-strategy advisory, not a paired gate."

The gate's PASS/FAIL has no veto power. It's informational. The framework designers recognized it couldn't drive decisions.

---

## 8. What a PROPER Selection Bias Test Would Look Like

For this project, the correct selection bias question is: "Given 6+ strategies tested on the same data, is the gap between the winner and runner-up genuine?"

### Method 1: Stepdown multiple comparison (Romano-Wolf)

Test all pairwise strategy differences simultaneously with family-wise error control. The T11 paired bootstrap with Holm adjustment already approximates this — and finds **all pairs non-significant** at α=0.05.

### Method 2: Combinatorial PBO (Probability of Backtest Overfitting)

Split data into S subsets, train on S-1, test on 1. Count how often the in-sample winner is the OOS loser. The selection_bias suite has a PBO proxy (negative_delta_ratio from WFO windows):

| Strategy | PBO proxy (negative_delta_ratio) |
|----------|:------:|
| E0 | 0.000 |
| X0 | 0.250 |
| X2 | 0.250 |

This is more informative than DSR — X0 has 2/8 windows where it underperforms E0 baseline.

### Method 3: Proper multiple-hypothesis framework

The strongest evidence against selection bias in this project comes from:
1. **Permutation test p=0.0001** for ALL strategies — alpha is real, not selected
2. **WFO OOS consistency** — the ranking survives out-of-sample
3. **Holdout on unseen data** — X0 beats E0 on genuinely new data
4. **16/16 timescale robustness** — not cherry-picked to one slow_period

---

## 9. Is Selection Bias a Real Problem Here?

### For absolute alpha: NO

All 6 strategies have permutation p=0.0001. The alpha is real — trend-following on BTC works. Selection bias cannot create a Sharpe of 1.3 from nothing.

### For relative ranking: PARTIALLY

The **gaps between strategies** (0.06-0.16 Sharpe) are small relative to estimation uncertainty. T11 finds all pairs Holm-nonsignificant. This means:
- We're confident ALL strategies have genuine alpha
- We're NOT confident about which one is best
- The ranking E5+EMA21 > X2 > X0 > E0 could be noise at the margin

This is exactly what WFO and holdout are designed to resolve — and they consistently point to X0 as the best validated choice (6/8 WFO, positive holdout).

---

## 10. Summary

| Question | Answer |
|----------|--------|
| Is DSR computing correctly? | **YES** — formula matches Bailey & López de Prado (2014) exactly |
| Does DSR use the actual trial count? | **NO** — hardcoded [27, 54, 100, 200, 500, 700], not the real N=6+ |
| Does it test each strategy vs random? | **YES** — null is "all strategies have SR=0" |
| Why is DSR=1.000 for everything? | Observed SR (~1.3) is **24σ** above SR₀ (~0.15). Would need **10^144+** trials to fail. |
| Is DSR useful for this dataset? | **NO** — vacuous gate, can never fail for SR > 0.5 on 2600+ days |
| Is this a bug? | **No** — design limitation. DSR was built for low-SR, high-trial-count regimes. |
| Does the framework handle selection bias? | **Yes, through WFO + holdout** — not through DSR. DSR is advisory-only (Report 21). |
| Is selection bias a real concern? | **For absolute alpha: NO** (p=0.0001). **For relative ranking: PARTIALLY** (all pairs Holm-ns). |
| What would fix DSR? | Replace with proper multiple-comparison testing (Romano-Wolf stepdown) or full combinatorial PBO. |
