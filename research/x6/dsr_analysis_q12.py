"""Q12: DSR Analysis — Why DSR=1.0 for all strategies and what it actually measures.

Demonstrates:
1. DSR formula mechanics with actual project numbers
2. How many trials needed to bring DSR below 0.95
3. What DSR actually tests vs what selection bias actually means for this project
"""

import math
import sys
from statistics import NormalDist

GAMMA = 0.5772156649015329  # Euler-Mascheroni


def deflated_sharpe(sr_observed, n_trials, t_samples, skew, kurt):
    """Replicate validation/suites/selection_bias.py calling convention."""
    z = NormalDist()
    variance = (
        1.0 - skew * sr_observed + ((kurt - 1.0) / 4.0) * sr_observed**2
    ) / max(t_samples, 1)
    std = math.sqrt(max(variance, 1e-12))

    if n_trials <= 1:
        expected_max_sr = 0.0
    else:
        z1 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / n_trials))
        z2 = z.inv_cdf(max(1e-12, 1.0 - 1.0 / (n_trials * math.e)))
        expected_max_sr = std * ((1.0 - GAMMA) * z1 + GAMMA * z2)

    zscore = (sr_observed - expected_max_sr) / std
    dsr_pvalue = float(z.cdf(zscore))
    return dsr_pvalue, expected_max_sr, std, zscore


# ─── Actual values from selection_bias.json outputs ───
strategies = {
    "E0":           {"sr": 1.2653, "skew": 0.874119, "kurt": 14.910651, "T": 2607},
    "X0":           {"sr": 1.3249, "skew": 0.883616, "kurt": 15.312714, "T": 2607},
    "X2":           {"sr": 1.4227, "skew": 0.813499, "kurt": 15.350609, "T": 2607},
    "E5+EMA21":     {"sr": 1.4320, "skew": 0.850000, "kurt": 15.100000, "T": 2607},  # approx
}

print("=" * 90)
print("SECTION 1: DSR with actual project parameters")
print("=" * 90)

for name, p in strategies.items():
    print(f"\n--- {name} (SR_obs = {p['sr']:.4f}, T = {p['T']}) ---")
    for trials in [6, 27, 100, 700, 10000, 100000]:
        pval, sr0, std, z = deflated_sharpe(p["sr"], trials, p["T"], p["skew"], p["kurt"])
        print(f"  N={trials:>6d}: SR₀={sr0:.4f}  z={z:>8.1f}  DSR_p={pval:.6f}")

print("\n" + "=" * 90)
print("SECTION 2: How many trials to bring DSR < 0.95?")
print("=" * 90)

# Binary search for critical N where DSR drops below 0.95
for name, p in strategies.items():
    lo, hi = 2, 10**300
    # First check if even 10^300 trials can bring DSR below 0.95
    pval, sr0, std, z = deflated_sharpe(p["sr"], 10**15, p["T"], p["skew"], p["kurt"])
    if pval >= 0.95:
        # Need to find where z < 1.645 (95th percentile)
        # z = (SR - SR₀) / std
        # SR₀ = std * Gumbel_factor(N)
        # Need: (SR - std * G(N)) / std < 1.645
        # SR/std - G(N) < 1.645
        # G(N) > SR/std - 1.645
        target_gumbel = p["sr"] / std - 1.645
        print(f"\n{name}: Need Gumbel factor > {target_gumbel:.1f}")
        print(f"  SR/std = {p['sr']/std:.1f}")
        print(f"  At N=10^15: SR₀={sr0:.4f}, z={z:.1f}, DSR={pval:.6f}")

        # Gumbel factor ≈ sqrt(2 * ln(N)) for large N
        # So need: sqrt(2*ln(N)) > target_gumbel
        # 2*ln(N) > target_gumbel^2
        # N > exp(target_gumbel^2 / 2)
        log_n_critical = target_gumbel**2 / 2
        print(f"  Approximate N_critical = exp({log_n_critical:.1f})")
        print(f"  That's 10^{log_n_critical / math.log(10):.0f}")
        print(f"  (i.e., you'd need to test ~10^{log_n_critical / math.log(10):.0f} strategies)")
    else:
        print(f"\n{name}: DSR < 0.95 at N=10^15")

print("\n" + "=" * 90)
print("SECTION 3: What DSR ACTUALLY tests")
print("=" * 90)

print("""
DSR asks: "Could an observed Sharpe of X have been produced by chance
           if all N tested strategies had TRUE Sharpe = 0?"

NULL HYPOTHESIS: All strategies are random (true SR = 0)
ALTERNATIVE:     At least one strategy has genuine alpha

For this project:
  - Observed SR ≈ 1.3 (annualized, harsh cost)
  - T ≈ 2607 daily observations
  - SR standard error ≈ 0.048

Even with N = 700 trials, expected max SR₀ ≈ 0.15
The observed SR (1.3) is 24 SIGMA above SR₀.
DSR trivially = 1.0 because 1.3 >> 0.15.

DSR would require ~10^150 trials before SR₀ reaches 1.3.
This is not a useful test for this dataset.
""")

print("=" * 90)
print("SECTION 4: What DSR does NOT test (the actual selection bias concern)")
print("=" * 90)

print("""
The REAL selection bias concern for this project:

  "We tested 6 strategies and picked the best one.
   Is the best one GENUINELY better, or just the luckiest of 6?"

This is a RELATIVE RANKING question:
  - E0 Sharpe = 1.277
  - X0 Sharpe = 1.336
  - X2 Sharpe = 1.433
  - E5+EMA21 Sharpe = 1.432

Question: Is the gap X0 → E0 (+0.060) real, or just noise?

DSR CANNOT answer this. DSR tests "is 1.336 > 0 after selection?"
Answer: trivially yes, because 1.336 >> 0.

The correct tool for RELATIVE selection bias is:
  1. WFO (out-of-sample score comparison) → X0 6/8 wins
  2. Holdout (unseen data) → X0 +0.090 Sharpe over E0
  3. Paired bootstrap (T11) → P(X0>E0)=85.3% (ns, Holm-adjusted)
  4. Permutation test → both p=0.0001 (absolute significance)

The validation framework already handles this through WFO + holdout,
NOT through the selection_bias suite.
""")

print("=" * 90)
print("SECTION 5: The hardcoded trial set — what it means")
print("=" * 90)

print("""
The selection_bias suite uses:
  trial_set = [27, 54, 100, 200, 500, 700]

These are NOT the actual number of strategies tested.
They are STRESS TEST levels: "would this Sharpe survive
even if we had tested 27/54/.../700 random strategies?"

The actual number of strategies tested in this project:
  - 6 named strategies (E0, E5, X0, X2, X6, E5+EMA21)
  - ~16 timescale variants each
  - ~5 trail multiplier values tested
  - ~3 VDO thresholds tested
  - Conservative estimate: ~50-200 configurations
  - Aggressive estimate: 16 × 5 × 3 × 6 = 1440 configurations

But even at N=1440, DSR would still be 1.0 because SR >> SR₀.
The gap between observed SR (1.3) and null SR₀ (<0.2) is too large.
""")

# Verify with N=1440
for name in ["X0"]:
    p = strategies[name]
    pval, sr0, std, z = deflated_sharpe(p["sr"], 1440, p["T"], p["skew"], p["kurt"])
    print(f"  X0 at N=1440: SR₀={sr0:.4f}, z={z:.1f}, DSR={pval:.6f}")

print()
print("=" * 90)
print("SECTION 6: Summary")
print("=" * 90)

print("""
1. DSR IS computing correctly per Bailey & López de Prado (2014)
2. DSR = 1.000 because observed Sharpe (~1.3) is ~24σ above null SR₀ (~0.15)
3. The trial_set [27-700] is hardcoded, NOT the actual strategies tested
4. Even with the TRUE trial count (~200+), DSR would still be 1.000
5. You'd need ~10^150 trials before DSR drops below 0.95 — MEANINGLESS
6. DSR tests "is Sharpe > 0 after selection?" — WRONG QUESTION for this project
7. The RIGHT question: "is the RANKING among real strategies genuine?"
8. That question is answered by WFO + holdout, NOT by DSR
9. DSR as implemented is a VACUOUS gate — it can never fail for any strategy
   with Sharpe > 0.5 on this dataset
""")
