"""Q13: Step 5 threshold sensitivity analysis.

Shows how the sign-off verdict changes as the combined disruption
threshold varies from -0.20 to -0.60.
"""

# ── Actual combined disruption deltas from Step 5 ──
# Source: step5_report.md Section 5 (entry_D2+exit_D1 scenario)
CANDIDATES = {
    "SM":           -0.000,
    "E0":           -0.322,
    "E0_plus":      -0.318,
    "E5":           -0.402,
    "E5_plus":      -0.396,
}

# ── Step 5 threshold values (hardcoded in run_step5_live_signoff.py) ──
GO_THRESHOLD = -0.20
GWG_THRESHOLD = -0.35  # GO_WITH_GUARDS

print("=" * 85)
print("SECTION 1: Current sign-off at threshold = -0.35")
print("=" * 85)

for name, delta in sorted(CANDIDATES.items(), key=lambda x: x[1], reverse=True):
    go = "GO" if delta > GO_THRESHOLD else ""
    gwg = "GO_WITH_GUARDS" if delta > GWG_THRESHOLD else ""
    status = go or gwg or "HOLD"
    margin = delta - GWG_THRESHOLD
    print(f"  {name:<15} delta={delta:+.3f}  status={status:<18} margin={margin:+.3f}")

print("\n" + "=" * 85)
print("SECTION 2: Threshold sensitivity — who passes at each level?")
print("=" * 85)

thresholds = [-0.20, -0.25, -0.30, -0.32, -0.35, -0.38, -0.40, -0.45, -0.50, -0.60]

print(f"\n{'Threshold':>10}  ", end="")
for name in ["SM", "E0_plus", "E0", "E5_plus", "E5"]:
    print(f"{name:>12}", end="")
print()
print("-" * 72)

for t in thresholds:
    marker = " ← current" if t == -0.35 else ""
    print(f"{t:>10.2f}  ", end="")
    for name in ["SM", "E0_plus", "E0", "E5_plus", "E5"]:
        delta = CANDIDATES[name]
        if delta > -0.20:
            status = "GO"
        elif delta > t:
            status = "GWG"
        else:
            status = "HOLD"
        print(f"{status:>12}", end="")
    print(marker)

print("\n" + "=" * 85)
print("SECTION 3: Critical threshold values (where verdicts flip)")
print("=" * 85)

flips = []
for name, delta in sorted(CANDIDATES.items(), key=lambda x: x[1]):
    flips.append((delta, name))

print(f"\n  Threshold range       E0_plus     E5_plus     Who benefits?")
print(f"  ─────────────────     ────────    ────────    ─────────────")
print(f"  > -0.318              GO_WITH_G   GO_WITH_G   Both pass")
print(f"  -0.318 to -0.396      HOLD       GO_WITH_G   Only E5_plus passes (current roles reversed!)")
print(f"  -0.396 to -0.402      HOLD        HOLD       Neither passes")
print(f"  < -0.402              HOLD        HOLD       All binary HOLD")
print(f"")
print(f"  CURRENT (-0.35):      GO_WITH_G    HOLD       Only E0_plus passes")
print(f"  At -0.40:             HOLD         HOLD       Both fail → SM only viable")
print(f"  At -0.32:             GO_WITH_G   GO_WITH_G   Both pass")

print("\n" + "=" * 85)
print("SECTION 4: The two arbitrary thresholds in series")
print("=" * 85)

print("""
The recommendation chain depends on TWO unproven thresholds:

  THRESHOLD 1: WFO win_rate >= 0.60
  ─────────────────────────────────
  Source: validation/thresholds.py (hardcoded default)
  Provenance: Report 32 H04 — "UNPROVEN"
  Statistical basis: For N=8 windows, P(≥5/8 | H₀) = 0.363
                     This is NOT a standard significance level
  Impact: E0 gets 0/8 (tautological), X0 gets 6/8 (PASS), X2/X6 get 4/8 (FAIL)

  THRESHOLD 2: worst_combo_delta_sharpe > -0.35
  ──────────────────────────────────────────────
  Source: run_step5_live_signoff.py line 89 (hardcoded constant)
  Provenance: NONE — not in Report 32 inventory, not in any research report
  Statistical basis: NONE — no simulation, derivation, or literature reference
  Impact: E0_plus passes at -0.318 (margin 0.032), E5_plus fails at -0.396 (over by 0.046)

  COMBINED EFFECT:
  ────────────────
  X2/X6 rejected by threshold 1 (WFO 4/8 < 60%)
  E5_plus rejected by threshold 2 (combined -0.396 < -0.35)
  Only X0 (E0_plus) survives both arbitrary gates
""")

print("=" * 85)
print("SECTION 5: What standard statistical thresholds would look like")
print("=" * 85)

from scipy import stats  # type: ignore

# WFO: Binomial test P(k >= observed | H0: p=0.5)
for name, wins, n in [("X0 (E0_plus)", 6, 8), ("E5_plus", 5, 8), ("X2/X6", 4, 8)]:
    p = 1 - stats.binom.cdf(wins - 1, n, 0.5)
    print(f"  {name:<15}  WFO {wins}/{n}  Binomial P(>={wins}/{n} | H0) = {p:.4f}  {'PASS α=0.05' if p < 0.05 else 'FAIL α=0.05' if p > 0.05 else ''}")

print(f"""
  At α=0.05 (one-sided): need P < 0.05 → need ≥7/8 wins
  At α=0.10: need P < 0.10 → need ≥7/8 wins
  At α=0.20: need P < 0.20 → need ≥6/8 wins
  At α=0.35: need P < 0.35 → need ≥5/8 wins  ← E5_plus passes here

  The current 60% threshold (5/8) corresponds to α ≈ 0.363 — far above
  any standard significance level. Even the 6/8 (X0) corresponds to α=0.145.

  NONE of the WFO results are statistically significant at α=0.05.
""")

print("=" * 85)
print("SECTION 6: Summary of arbitrary threshold chain")
print("=" * 85)

print("""
FINDING: The final recommendation (X0 over E5+EMA1D21) rests on
TWO arbitrary thresholds applied in series:

  1. WFO 60% — UNPROVEN (Report 32 H04)
     → Rejects X2/X6 (4/8) but passes X0 (6/8) and E5+ (5/8)

  2. Combined disruption -0.35 — ZERO PROVENANCE (not even audited)
     → Rejects E5+ (-0.396) but passes X0 (-0.318)
     → Margin of decision: 0.078 Sharpe units
     → If threshold were -0.40: both fail → recommendation becomes SM
     → If threshold were -0.32: both pass → E5+ would be recommended

  Neither threshold has:
  ✗ Statistical derivation
  ✗ Simulation calibration
  ✗ Literature reference
  ✗ Sensitivity analysis
  ✗ Provenance documentation

  The entire decision path from "E5+EMA1D21 is the best strategy" to
  "X0 is the recommendation" hangs on 0.078 Sharpe units of margin
  split across two undocumented thresholds.
""")
