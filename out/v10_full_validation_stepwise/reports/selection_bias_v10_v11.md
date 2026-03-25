# Selection Bias Analysis: V10 + V11 Combined

**Script:** `out_v10_full_validation_stepwise/scripts/selection_bias_v10_v11.py`
**Timestamp:** 2026-02-24 00:12:29 UTC
**Scenario:** harsh (50 bps RT)
**Method 1:** CSCV/PBO (Bailey, Borwein, López de Prado 2017)
**Method 2:** Deflated Sharpe Ratio (Bailey & López de Prado 2014)

---

## 1. Problem Statement

Both V10 (baseline) and V11 (candidate) emerged from a research process that
explored **694+ configurations** across multiple strategy families.
V10 was selected as the best V8-family default; V11 was optimized via WFO from
the V11 cycle_late parameter space. With this many trials, we must quantify the
risk that observed performance is due to **selection bias** rather than genuine skill.

**Questions:**
1. Is V10's baseline Sharpe explainable by lucky selection from many trials?
2. Is V11's improvement over V10 real, or an artifact of multiple testing?
3. If we re-split the data, how often does the IS-best config remain good OOS?

---

## 2. Strategy Universe

| Family | Configs | Grid Axes |
|--------|---------|-----------|
| V10 variants | 27 | trail_atr_mult × vdo_entry_threshold × entry_aggression |
| V11 variants | 27 | cycle_late_aggression × trail_mult × max_exposure |
| **Total** | **54** | |

- V10 default: `V10_3.5_0.004_0.85` (center of V10 grid)
- V11 WFO-optimal: aggr=0.95, trail=2.8, cap=0.90 (trail=2.8 not in grid)
- Full research inventory: **694** configs (89 YAML-named + 477 WFO grid + 54 sensitivity + 72 overlay + 2 reference)
- Blocks: 10 WFO windows (6-month each)
- CSCV combinations: C(10,5) = 252
- Backtests executed: 54 × 10 = 540

---

## 3. CSCV/PBO Results

### 3.1 Full Universe (54 configs)

| Metric | PBO | Mean OOS Rank | Interpretation |
|--------|-----|---------------|----------------|
| IS-best → OOS (score) | **68.7%** | 36.3/54 | High risk |
| IS-best → OOS (return) | **74.6%** | 37.2/54 | Moderate |
| V10 default (score) | **14.3%** | 18.3/54 | Low risk |

### 3.2 V10 Family Only (27 configs)

Tests whether V10 default is genuinely the best within V8-family parameter space.

| Metric | PBO | Default Rank | Interpretation |
|--------|-----|-------------|----------------|
| V10 default (score) | **14.7%** | 6.9/27 | V10 is genuinely good within family |
| V10 default (return) | **13.5%** | — | |

### 3.3 V11 + V10 Baseline (28 configs)

Replicates V11 validation setup for consistency check.

| Metric | PBO | Interpretation |
|--------|-----|----------------|
| IS-best → OOS (score) | **13.9%** | Low risk |
| IS-best → OOS (return) | **13.9%** | |

### 3.4 PBO Interpretation Guide

| PBO Range | Risk Level | V10 Family | Full Universe |
|-----------|-----------|-----------|---------------|
| < 10% | Very low |  |  |
| 10-30% | Low | ← HERE |  |
| 30-50% | Moderate |  |  |
| > 50% | High (coin flip) |  | ← HERE |

---

## 4. Deflated Sharpe Ratio

### 4.1 V10 Baseline

| Parameter | Value |
|-----------|-------|
| Observed Sharpe | 1.1510 |
| Daily observations (T) | 2607 |
| Skewness | 1.3594 |
| Kurtosis | 24.2681 |

| N (trials) | E[max(SR)] | DSR | PASS? |
|-----------|-----------|-----|-------|
| 27 (V10 grid) | 0.1063 | 1.0000 | PASS |
| 54 (combined) | 0.1207 | 1.0000 | PASS |
| 89 (YAML) | 0.1303 | 1.0000 | PASS |
| 200 (200) | 0.1448 | 1.0000 | PASS |
| 400 (400) | 0.1562 | 1.0000 | PASS |
| 694 (full inventory) | 0.1649 | 1.0000 | PASS |

### 4.2 V11 IS-Best

| Parameter | Value |
|-----------|-------|
| Config | V11_0.95_2.7_0.95 |
| Observed Sharpe | 1.1470 |
| Daily observations (T) | 2607 |
| Skewness | 1.4183 |
| Kurtosis | 24.7419 |

| N (trials) | E[max(SR)] | DSR | PASS? |
|-----------|-----------|-----|-------|
| 27 (V11 grid) | 0.1066 | 1.0000 | PASS |
| 54 (combined) | 0.1210 | 1.0000 | PASS |
| 89 (YAML) | 0.1307 | 1.0000 | PASS |
| 200 (200) | 0.1452 | 1.0000 | PASS |
| 400 (400) | 0.1567 | 1.0000 | PASS |
| 694 (full inventory) | 0.1653 | 1.0000 | PASS |

### 4.3 Incremental DSR (V11 vs V10)

Tests whether V11's Sharpe **improvement** (Δ = -0.0040) survives
multiple-testing adjustment.

| N | DSR(Δ) | PASS? |
|---|--------|-------|
| 27 | 0.0340 | FAIL |
| 54 | 0.0178 | FAIL |
| 89 | 0.0112 | FAIL |
| 694 | 0.0016 | FAIL |

**DSR caveat:** DSR tests absolute Sharpe against null of zero. Both V10 and V11
have high absolute Sharpe (>1.0) which trivially survives even N=694. The
incremental test on Δ Sharpe is more informative but uses an approximation
(testing |Δ SR| as if it were an observed SR against null).

---

## 5. Cross-Family Block Analysis

Average score per block for each family:

| Block | Period | V10 Avg | V11 Avg | Δ | Winner |
|-------|--------|---------|---------|---|--------|
| 0 | 2021-01-01→2021-07-01 | +125.97 | +269.55 | +143.58 | V11 |
| 1 | 2021-07-01→2022-01-01 | -15.13 | -9.63 | +5.50 | V11 |
| 2 | 2022-01-01→2022-07-01 | -2.10 | +0.00 | +2.10 | V11 |
| 3 | 2022-07-01→2023-01-01 | +0.00 | +0.00 | +0.00 | TIE |
| 4 | 2023-01-01→2023-07-01 | +17.95 | -23.46 | -41.41 | V10 |
| 5 | 2023-07-01→2024-01-01 | +160.40 | +160.94 | +0.54 | V11 |
| 6 | 2024-01-01→2024-07-01 | +85.25 | +141.74 | +56.50 | V11 |
| 7 | 2024-07-01→2025-01-01 | +168.81 | +151.73 | -17.09 | V10 |
| 8 | 2025-01-01→2025-07-01 | -90.27 | -72.59 | +17.69 | V11 |
| 9 | 2025-07-01→2026-01-01 | -39.72 | -24.22 | +15.50 | V11 |

V11 family wins **7/10** blocks on average.

---

## 6. Quantitative Risk Statement

### V10 (Baseline)

1. **Selection bias risk: LOW**
   - PBO within V10 family = 14.7%
   - V10 default ranks 6.9/27 OOS on average
   - DSR > 0.95 at all N up to 694

2. **V10's absolute Sharpe is genuine** — not an artifact of selection from
   694 trials. The strategy captures a real BTC momentum premium.

3. **V10 ranks 15/54** in the combined 54-config universe,
   confirming it's competitive even against V11 variants.

### V11 (Candidate)

1. **Selection bias within V11 family: LOW** (PBO = 13.9%)
   - Within the V11+V10 universe (28 configs), the IS-best transfers well OOS
   - This matches the V11 validation result exactly

2. **Full universe PBO = 68.7% — but this is misleading for V11:**
   - The full-universe IS-best is `V10_2.8_0.002_0.65` (a V10 edge variant), not a V11 config
   - The high PBO reflects overfitting of the COMBINED 54-config search space, not V11 specifically
   - V11 configs cluster tightly (avg score range 49–65), so they're NOT the source of overfitting

3. **Absolute Sharpe is genuine** — DSR PASS at all N

4. **Incremental Sharpe (Δ = -0.0040) does NOT survive** multiple-testing at N=694
   - V11 IS-best actually has slightly LOWER Sharpe than V10 default (1.147 vs 1.151)
   - The improvement over V10 is effectively zero — pure noise from multiple testing

### Key Insight

Both V10 and V11 have genuine absolute performance (Sharpe > 1.0). The selection
process did not create their edge — it's a real BTC momentum premium. However,
V11 does **not** improve on V10. The Δ Sharpe is -0.004 (negative), and the
incremental DSR confirms this difference is indistinguishable from noise even
at N=27. The CSCV cross-family analysis shows V11 family wins 7/10 blocks on
average score, but the magnitude is driven by a single block (Block 0: +143 pts)
while V10 wins the blocks closest to recent data (Block 7: -17 pts).

---

## 7. Methodology Limitations

1. **Grid ≠ full search space**: 54 configs from 2 grids. Actual development
   tested 694+ configs across multiple strategy families. CSCV can only
   use configs that are backtestable on the same WFO blocks.

2. **V11 WFO-optimal not in grid**: The actual V11 WFO-optimal (trail=2.8)
   falls between grid points [2.7, 3.0]. CSCV uses the grid universe as proxy.

3. **Block size**: 10 blocks of 6 months. Shorter → more noise, longer → fewer
   combinations. S=10 gives C(10,5)=252 which is reasonable but not exhaustive.

4. **Non-independence**: CSCV assumes blocks are independent. In practice,
   strategies carry positions across block boundaries and regime clustering
   creates temporal correlation.

5. **DSR assumes normal null**: Returns are fat-tailed (high kurtosis). The
   DSR formula partially accounts for this but may be misspecified.

6. **Incremental DSR is approximate**: Testing |Δ SR| as an observed Sharpe
   is a heuristic. A paired bootstrap test would be more rigorous.

---

## 8. Combined Verdict

| Test | V10 | V11 |
|------|-----|-----|
| PBO (own family) | 14.7% | 13.9% |
| PBO (full 54-config universe) | 14.3% (V10 default) | 68.7% (IS-best = V10 edge variant) |
| DSR absolute (N=54) | 1.0000 | 1.0000 |
| DSR absolute (N=694) | 1.0000 | 1.0000 |
| Incremental DSR (Δ SR) | — | 0.0016 (FAIL) |
| **Selection bias risk** | **LOW** | **LOW (absolute), N/A (incremental — Δ SR ≤ 0)** |

### Verdict:
1. Both V10 and V11 have **genuine absolute performance** (Sharpe ~1.15, DSR=1.0 at all N).
2. Neither is overfit within their own family (PBO ~14%).
3. V11 does **NOT improve** on V10 — Δ Sharpe = -0.004, incremental DSR = 0.0016.
4. The full-universe PBO (68.7%) reflects overfitting of edge V10 variants, not V11.

---

## 9. Data Files

| File | Description |
|------|-------------|
| `out_v10_full_validation_stepwise/selection_bias_results.json` | Full results (PBO + DSR + perf matrices) |
| `out_v10_full_validation_stepwise/scripts/selection_bias_v10_v11.py` | Reproducible script |
| `out_v10_full_validation_stepwise/reports/selection_bias_v10_v11.md` | This report |
