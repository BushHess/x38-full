# Report 20 — Win-Count / Multi-Timescale Control Pair Audit

**Date**: 2026-03-03
**Artifact**: `research_reports/artifacts/20_win_count_control_pair_audit.py`
**Data**: `research_reports/artifacts/20_win_count_control_pair_audit.json`
**Runtime**: 709s (500 VCBB paths x 16 timescales x 4 strategies)

---

## 1. Objective

Audit the multi-timescale win-count / binomial test — the proposed
replacement for CI-based gates that failed in Reports 18-19 — on the
same three control pairs to assess calibration, power, and false-positive
rate.

Control pairs (identical to Reports 18/19):

| Pair | Type | Expected gate |
|------|------|---------------|
| A0 vs A1 | Negative control (ATR 14→20) | FAIL |
| A0 vs VBREAK | Mid positive (EMA cross vs Donchian) | PASS |
| A0 vs VCUSUM | Strong positive (EMA cross vs CUSUM) | PASS |

---

## 2. Existing Win-Count Procedures (Inventory)

Seven scripts in the project contain win-count procedures. Three distinct
variant families:

### Variant 1: Real-data wins (Reports 11/11b)
- `11_e0_e5_scale_fairness.py`, `11b_e0_e5_mechanism_vs_family.py`
- Simulate both strategies at 16 timescales on real data
- Win = strict `>` on Sharpe/CAGR, strict `<` on MDD
- No statistical test on the count itself

### Variant 2: Bootstrap-then-binomial (e5_validation.py)
- `e5_validation.py`, `trail_sweep.py`
- 2000 VCBB paths per timescale
- P(win) = fraction of paths where A beats B
- Timescale win if P(win) > 0.50
- Binomial test: `binomtest(wins, 16, 0.5, alternative='greater')`
- Verdict scale: PROVEN\*\*\* (p<0.001), PROVEN\*\* (<0.01),
  PROVEN\* (<0.025), STRONG (<0.05), MARGINAL (<0.10), NOT SIG

### Variant 3: DOF-corrected binomial (binomial_correction.py)
- Same as V2, plus Nyholt/Li-Ji/Galwey M_eff correction
- Binary win correlation matrix (NOT continuous delta correlation)
- `corrected_binomial(wins, K, corr_matrix)` from `research/lib/effective_dof.py`
- Scales wins proportionally by M_eff/K, tests on M_eff trials

### Canonical timescale grid (all variants)
```
SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
```
16 H4-bar slow periods. Each strategy interprets `slow` as its primary
lookback parameter (EMA period for VTREND, Donchian for VBREAK,
reference window for VCUSUM).

---

## 3. Configuration

- Data: 17,838 H4 bars, warmup idx=2190, trading=15,648 bars
- Period: 2019-01-01 to 2026-02-20
- Cost: 50 bps RT (harsh)
- Bootstrap: 500 VCBB paths, block=60, seed=42
  (canonical is 2000; 500 gives +/-2.2pp precision on P(win))

---

## 4. Variant 1: Real-Data Wins

### 4.1 Results

| Pair | Metric | Wins | Losses | p_binom | Verdict |
|------|--------|------|--------|---------|---------|
| **A0 vs A1** (null) | Sharpe | 10/16 | 6 | 0.227 | NOT SIG |
| | CAGR | **14/16** | 2 | **0.0021** | **PROVEN \*\*** |
| | MDD | 12/16 | 3 | 0.038 | STRONG |
| **A0 vs VBREAK** (mid+) | Sharpe | 9/16 | 7 | 0.402 | NOT SIG |
| | CAGR | 12/16 | 4 | 0.038 | STRONG |
| | MDD | 2/16 | 14 | 1.000 | NOT SIG |
| **A0 vs VCUSUM** (strong+) | Sharpe | 13/16 | 3 | 0.011 | PROVEN \* |
| | CAGR | 13/16 | 3 | 0.011 | PROVEN \* |
| | MDD | 0/16 | 16 | 1.000 | NOT SIG |

### 4.2 Assessment

**False positive on negative control**: CAGR 14/16 (p=0.0021) on the
A0 vs A1 null pair. This is a clear false alarm — A0 and A1 differ
only in ATR trailing stop period (14 vs 20), producing negligible real
performance difference (delta Sharpe = -0.006, delta CAGR = 0.1pp).
The CAGR win count is inflated because small, consistent CAGR
differences in the same direction accumulate across correlated
timescales.

**MDD direction reversal**: A0 has WORSE MDD than VBREAK (41.5% vs
34.0%) and VCUSUM (41.5% vs 28.5%) at most timescales. A0's EMA
crossover stays in the market longer during drawdowns. The win-count
correctly shows 0-2/16 MDD wins for A0 on positive control pairs.
This is not a bug — it reflects a genuine tradeoff: A0 wins on
Sharpe/CAGR but loses on MDD.

---

## 5. Variant 2: Bootstrap-Then-Binomial

### 5.1 Per-timescale P(win) summary

**A0 vs A1 (null)**: P(Sharpe win) ranges from 52.2% to 58.6% across
all 16 timescales. Every timescale shows P > 50%. This 2-8pp bias
above 50% is consistent with noise, but because it is correlated
across timescales, ALL 16 show P > 0.50.

**A0 vs VBREAK (mid+)**: P(Sharpe win) ranges from 14.8% to 52.6%.
A0 LOSES on bootstrap data at most timescales — opposite of real-data
result. VBREAK performs relatively better on synthetic paths because
block-resampled paths preserve trend structure that Donchian breakout
exploits.

**A0 vs VCUSUM (strong+)**: P(Sharpe win) ranges from 22.6% to 57.0%,
increasing with timescale. Only 8/16 timescales show P > 50%.

### 5.2 Aggregate results

| Pair | Metric | Wins | p_binom | Verdict |
|------|--------|------|---------|---------|
| **A0 vs A1** (null) | Sharpe | **16/16** | **1.53e-5** | **PROVEN \*\*\*** |
| | CAGR | **16/16** | **1.53e-5** | **PROVEN \*\*\*** |
| | MDD | 1/16 | 1.000 | NOT SIG |
| **A0 vs VBREAK** (mid+) | Sharpe | 1/16 | 1.000 | NOT SIG |
| | CAGR | 8/16 | 0.598 | NOT SIG |
| | MDD | 0/16 | 1.000 | NOT SIG |
| **A0 vs VCUSUM** (strong+) | Sharpe | 8/16 | 0.598 | NOT SIG |
| | CAGR | 12/16 | 0.038 | STRONG |
| | MDD | 0/16 | 1.000 | NOT SIG |

### 5.3 Assessment

**Critical false positive**: V2 declares A0 vs A1 as PROVEN\*\*\* on
both Sharpe and CAGR. This is a catastrophic miscalibration. The
mechanism: P(win) at each timescale is 52-58% (barely above 50%), but
because adjacent timescales are highly correlated (r=0.79), ALL 16
show the same bias direction. The nominal binomial test treats 16
correlated outcomes as 16 independent coin flips, dramatically
inflating significance.

**Misses positive controls**: V2 fails to detect either positive
control pair on Sharpe (1/16 and 8/16). On CAGR, it barely detects
the strong positive (12/16, p=0.038) and completely misses the mid
positive (8/16).

**V2 without DOF correction scores 0/3** on the control pair scorecard.
It is the worst-performing method tested.

---

## 6. Variant 3: DOF-Corrected Binomial

### 6.1 M_eff estimates (binary win correlation)

| Pair | Metric | Mean adj r | M_eff (conservative) |
|------|--------|-----------|---------------------|
| A0 vs A1 | Sharpe | 0.787 | **2.5** |
| A0 vs A1 | CAGR | 0.789 | **2.5** |
| A0 vs VBREAK | Sharpe | 0.658 | **4.0** |
| A0 vs VBREAK | CAGR | 0.677 | **3.7** |
| A0 vs VCUSUM | Sharpe | 0.676 | **3.9** |
| A0 vs VCUSUM | CAGR | 0.711 | **3.5** |

**The 16 timescales provide only 2.5-4.0 effective independent
observations.** The null pair (A0 vs A1) has the highest correlation
(r=0.79, M_eff=2.5) because both strategies are nearly identical —
their relative performance is almost perfectly correlated across
timescales.

### 6.2 Results

| Pair | Metric | Wins | Nominal p | Corrected p | Verdict |
|------|--------|------|-----------|-------------|---------|
| **A0 vs A1** (null) | Sharpe | 16/16 | 1.53e-5 | **0.250** | **NOT SIG** |
| | CAGR | 16/16 | 1.53e-5 | **0.250** | **NOT SIG** |
| | MDD | 1/16 | 1.000 | 1.000 | NOT SIG |
| **A0 vs VBREAK** (mid+) | Sharpe | 1/16 | 1.000 | 1.000 | NOT SIG |
| | CAGR | 8/16 | 0.598 | 0.688 | NOT SIG |
| | MDD | 0/16 | 1.000 | 1.000 | NOT SIG |
| **A0 vs VCUSUM** (strong+) | Sharpe | 8/16 | 0.598 | 0.688 | NOT SIG |
| | CAGR | 12/16 | 0.038 | **0.125** | **NOT SIG** |
| | MDD | 0/16 | 1.000 | 1.000 | NOT SIG |

### 6.3 Assessment

**DOF correction eliminates the false positive**: A0 vs A1 goes from
PROVEN\*\*\* (p=1.5e-5) to NOT SIG (p=0.25). With M_eff=2.5, the
16/16 nominal wins become ~2.5/2.5 effective wins — binomtest(2, 2,
0.5) = 0.25. The DOF correction is working correctly.

**But eliminates the true positives too**: A0 vs VCUSUM CAGR goes
from STRONG (p=0.038) to NOT SIG (p=0.125). With M_eff=3.5 and
12/16 wins, the scaled result is ~2.6/3.5 effective wins — not
enough for significance.

**V3 correctly rejects all three pairs** from a false-positive
perspective (1/3 on the scorecard — null correct, both positives
missed). This is the same performance as CI-based gates from Report 18.

---

## 7. Timescale Dependence

### 7.1 Binary vs continuous correlation

| Pair | Binary adj r | Continuous adj r | M_eff |
|------|-------------|-----------------|-------|
| A0 vs A1 | 0.787 | 0.931 | 2.5 |
| A0 vs VBREAK | 0.658 | 0.851 | 4.0 |
| A0 vs VCUSUM | 0.676 | 0.870 | 3.9 |

Consistent with binomial_correction.py finding: binary win correlation
(r~0.66-0.79) is LOWER than continuous delta correlation (r~0.85-0.93).
The binomial_correction.py correctly uses binary win correlation for
M_eff input, as it directly governs the effective independence of the
binary outcomes being tested.

### 7.2 Are the 16 timescales close to independent?

**No.** With M_eff = 2.5-4.0 out of 16, the timescales are strongly
dependent. The 16 nominal trials provide only 2.5-4 independent
observations. This is a fundamental limitation:

- Adjacent timescales (e.g., 108 vs 120) share >80% of their data
  points and produce nearly identical signals
- Even distant timescales (e.g., 30 vs 720) share the same market
  structure and VDO/ATR indicators
- The negative control pair (identical entry logic) has the highest
  correlation because the ONLY source of variation is noise

### 7.3 Implications for existing research claims

The existing DOF-corrected claims in binomial_correction.py tested
VDO on/off (same strategy, toggle one filter) and found M_eff~10-11
for binary Sharpe wins. The lower M_eff here (2.5-4.0) is because
cross-strategy comparison has higher correlation than within-strategy
filter toggling. The VDO on/off comparison creates more independent
variation across timescales because VDO's effect varies by market
structure.

---

## 8. Comparison with CI-Based Gates

### 8.1 Full scorecard

| Method | Null (expect FAIL) | Mid+ (expect PASS) | Strong+ (expect PASS) | Score |
|--------|-------------------|--------------------|-----------------------|-------|
| Boot CI (R18) | OK | MISS | MISS | 1/3 |
| Sub CI (R18) | OK | MISS | MISS | 1/3 |
| V1 Sharpe | OK | MISS | OK | 2/3 |
| V1 CAGR | **MISS** | OK | OK | 2/3 |
| V2 Sharpe | **MISS** | MISS | MISS | **0/3** |
| V2 CAGR | **MISS** | MISS | OK | 1/3 |
| V3 Sharpe | OK | MISS | MISS | 1/3 |
| V3 CAGR | OK | MISS | MISS | 1/3 |

### 8.2 Key findings

1. **No method achieves 3/3**. The best score is 2/3 (V1 Sharpe, V1 CAGR).

2. **V2 uncorrected is the worst method tested** (0/3 on Sharpe).
   It produces a catastrophic false positive (PROVEN\*\*\*) on the
   null pair while missing both positive controls.

3. **V3 DOF-corrected ties with CI-based methods** at 1/3. The DOF
   correction fixes the false positive but the residual 2.5-4.0
   effective trials are too few for power.

4. **V1 real-data is the best**, but only because it doesn't bootstrap.
   On real data, the Sharpe/CAGR differences are real (A0 genuinely
   has higher CAGR than A1 at most timescales because ATR(14) is
   slightly better-matched). However, V1 also false-positives on the
   null pair for CAGR (14/16, p=0.002).

5. **The fundamental problem is power, not methodology**. With ~7 years
   of H4 data and M_eff=2.5-4.0 effective timescales, there is
   insufficient statistical information to reliably distinguish mid-
   sized effects (delta Sharpe ~0.1-0.3).

---

## 9. Diagnosis: Why V2 False-Positives on the Null Pair

The mechanism is precise and instructive:

1. A0 and A1 have identical entry logic (EMA crossover + VDO). They
   differ ONLY in the ATR period used for the trailing stop (14 vs 20).

2. On each bootstrap path, A0 and A1 produce very similar returns.
   But A0 has a tiny, noise-level edge: ATR(14) is slightly more
   responsive, producing marginally tighter trailing stops. This gives
   P(A0 wins) ≈ 53-57% per timescale — barely above 50%.

3. Because both strategies use the same EMA signals, this tiny edge is
   **perfectly correlated across timescales**. If A0 slightly outperforms
   A1 on one bootstrap path, it does so at ALL 16 timescales
   simultaneously.

4. The binomial test sees 16/16 wins and computes p=1.5e-5, treating
   each timescale as independent. But with M_eff=2.5, the information
   content is equivalent to ~2.5 coin flips all landing heads — p=0.25.

This is the **worst-case scenario for uncorrected win-count**: a tiny,
noise-level bias that is maximally correlated across timescales. The
VDO on/off comparison in the original research avoids this because
toggling VDO creates genuine differential variation across timescales
(M_eff~10-11 vs 2.5 here).

---

## 10. Conclusions

1. **V2 (uncorrected bootstrap-then-binomial) is not safe for cross-
   strategy comparison.** It produces a PROVEN\*\*\* false positive on
   a null pair where the true effect is near zero. This method should
   NEVER be used without DOF correction.

2. **V3 (DOF-corrected) eliminates the false positive but has no power.**
   With M_eff=2.5-4.0 for cross-strategy comparison, the effective
   sample size is too small to detect even large effects (delta Sharpe
   0.34 for the strong positive control).

3. **The multi-timescale win-count is NOT a viable replacement for CI-
   based gates on cross-strategy comparison.** It scores equal to or
   worse than Boot CI / Subsampling on the control pair scorecard.

4. **The original VDO on/off claims remain valid.** The VDO comparison
   has M_eff~10-11 (binary) because toggling VDO creates genuinely
   independent variation across timescales. The DOF-corrected p-values
   from binomial_correction.py survive because they start from 16/16
   wins and M_eff is high enough.

5. **All available single-timescale inference methods (bootstrap,
   subsampling, DSR) and multi-timescale methods (V1, V2, V3) fail to
   achieve 3/3 on the control pair scorecard.** The fundamental
   constraint is ~7 years of H4 data with ~15 effective independent
   observations (at single-timescale) or ~2.5-4.0 effective
   observations (at multi-timescale cross-strategy).

---

## Appendix: File references

- Script: `research_reports/artifacts/20_win_count_control_pair_audit.py`
- JSON output: `research_reports/artifacts/20_win_count_control_pair_audit.json`
- Win-count source (V1): `research/11_e0_e5_scale_fairness.py`, `research/11b_e0_e5_mechanism_vs_family.py`
- Win-count source (V2): `research/e5_validation.py`, `research/trail_sweep.py`
- Win-count source (V3): `research/binomial_correction.py`
- DOF library: `research/lib/effective_dof.py`
- Reports 18/19 reference: `research_reports/18_current_stack_on_control_pairs.md`, `research_reports/19_same_statistic_control_pair_audit.md`
