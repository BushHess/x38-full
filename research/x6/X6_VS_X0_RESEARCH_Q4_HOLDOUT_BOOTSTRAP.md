# Research Q4: Holdout Bootstrap — Sharpe Difference CI

**Date**: 2026-03-08
**Script**: `research/x6/holdout_bootstrap_q4.py`
**Results**: `research/x6/holdout_bootstrap_q4_results.json`

---

## 1. Setup

- **Holdout period**: 2024-09-17 → 2026-02-20 (3,132 H4 bars = 1.43 years)
- **Cost model**: harsh (50 bps RT)
- **Bootstrap**: 1,000 circular block bootstrap paths
- **Block sizes**: 21, 42, 84 bars (~3.5d, ~7d, ~14d)
- **Sharpe annualization**: √(6 × 365.25) = √2190, ddof=0

## 2. Trade Counts (Engine-Based)

| Strategy | Holdout Trades | Full Sample Trades |
|----------|:--------------:|:------------------:|
| X0 | 31 | 172 |
| X2 | 27 | 138 |
| X6 | 26 | 135 |

## 3. Point Estimates (Vectorized Surrogate on Holdout)

| Strategy | Sharpe | CAGR% | MDD% |
|----------|:------:|:-----:|:----:|
| X0 | 0.9058 | 23.01 | 23.54 |
| X2 | 0.7184 | 17.39 | 24.50 |
| X6 | 0.7184 | 17.39 | 24.50 |

Note: X2 and X6 produce **identical** results in the vectorized sim — the BE floor has zero marginal effect in the surrogate execution model. Engine-based results show slight differences (X6 Sharpe 0.859 vs X2 0.818) due to fill-price timing.

### Sharpe differences (point estimates)

| Pair | dSharpe |
|------|:-------:|
| X2 − X0 | **-0.1873** |
| X6 − X0 | **-0.1873** |
| X6 − X2 | 0.0000 |

---

## 4. Bootstrap Results (1,000 Paths)

### Per-Strategy Sharpe CI

| Strategy | Block | Median | Mean | 95% CI | 90% CI |
|----------|:-----:|:------:|:----:|:------:|:------:|
| X0 | 21 | 0.923 | 0.916 | [-0.96, +2.73] | [-0.66, +2.45] |
| X0 | 42 | 0.916 | 0.898 | [-0.98, +2.61] | [-0.59, +2.32] |
| X0 | 84 | 0.849 | 0.842 | [-1.01, +2.64] | [-0.69, +2.38] |
| X2/X6 | 21 | 0.736 | 0.732 | [-1.23, +2.59] | [-0.93, +2.34] |
| X2/X6 | 42 | 0.730 | 0.710 | [-1.23, +2.45] | [-0.83, +2.20] |
| X2/X6 | 84 | 0.674 | 0.658 | [-1.14, +2.39] | [-0.91, +2.16] |

**Individual Sharpe CIs span ~3.7 Sharpe units** — enormous uncertainty from only 1.43 years of data.

### Pairwise: X0 vs X2/X6 Sharpe Difference

| Block | Mean Δ | Median Δ | 95% CI | P(X0 > X2/X6) |
|:-----:|:------:|:--------:|:------:|:--------------:|
| 21 | -0.185 | -0.158 | [-0.72, +0.22] | **79.4%** |
| 42 | -0.188 | -0.167 | [-0.72, +0.23] | **77.3%** |
| 84 | -0.184 | -0.165 | [-0.65, +0.24] | **77.4%** |

**95% CI crosses zero at ALL block sizes → NOT statistically significant.**

---

## 5. Key Findings

### Finding 1: CI is enormous — sample too small for significance

The 95% CI for the Sharpe difference is approximately [-0.7, +0.2] — spanning nearly 1.0 Sharpe units. With only 31 trades (X0) or 26-27 trades (X2/X6) in 1.43 years of holdout data, **there is insufficient statistical power to distinguish X0 from X2/X6**.

### Finding 2: X0 wins ~77-79% of paths — directional but not conclusive

X0 beats X2/X6 in roughly 4 out of 5 bootstrap paths. This is directionally consistent but far from the 95% or 97.5% threshold needed for statistical significance. A one-sided p-value of ~0.21-0.23 is not meaningful.

### Finding 3: X2 ≡ X6 in holdout (zero marginal BE value)

The breakeven floor has zero measurable effect in the holdout period. X2 and X6 are identical across all 1,000 bootstrap paths. The BE stop mechanism simply doesn't activate differently from X2's adaptive trail in this market.

### Finding 4: Block size doesn't matter

Results are remarkably stable across block sizes (21, 42, 84 bars). This suggests the conclusion is robust to autocorrelation structure assumptions.

### Finding 5: Context — the CI width problem

For reference, to achieve a significant Sharpe difference of 0.19 at p<0.05 with N=31 trades, you'd need approximately:

```
Required sample size ≈ (1.96 × σ_diff / 0.19)²
```

With σ_diff ≈ 0.24 (from the bootstrap), you'd need about 6× more data (~9 years of holdout) to have 80% power. **The holdout period is fundamentally too short to be a reliable discriminator.**

---

## 6. Comparison with Engine-Based Results

| Metric | Vec Surrogate | Engine (eval harness) |
|--------|:------------:|:--------------------:|
| X0 Sharpe | 0.906 | 1.050 |
| X2 Sharpe | 0.718 | 0.818 |
| X6 Sharpe | 0.718 | 0.859 |
| X0-X6 delta | 0.187 | 0.191 |

The vectorized surrogate slightly underestimates absolute Sharpe (simpler execution model) but the **delta is consistent** (0.187 vs 0.191).

---

## 7. Summary Table

| Question | Answer |
|----------|--------|
| Sharpe diff CI (X0-X6)? | 95% CI: [-0.72, +0.22] — **crosses zero** |
| P(X0 > X6) in holdout? | **~78%** (77-79% across block sizes) |
| Statistically significant? | **NO** — p ≈ 0.21 (one-sided) |
| P(X0 > X2) in holdout? | **~78%** (same — X2 ≡ X6 in holdout) |
| X6 vs X2 marginal value? | **Zero** in holdout (identical paths) |
| Why so wide CI? | 1.43 years, 26-31 trades — **fundamentally insufficient sample** |
