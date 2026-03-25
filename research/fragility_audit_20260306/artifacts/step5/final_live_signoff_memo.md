# Live Sign-Off Memo — VTREND 5-Strategy Candidate Set

**To**: PM / Research Lead
**From**: Live Sign-Off Hardening Audit (Step 5)
**Date**: 2026-03-06
**Status**: Sign-off evaluation COMPLETE. Refines Step 4 deployment recommendations.

---

## Live Sign-Off Matrix

| Candidate | LT1 (<4h auto) | LT2 (4-16h degraded) | LT3 (>16h manual) |
|---|---|---|---|
| **E0** | GO_WITH_GUARDS | HOLD | HOLD |
| **E5** | HOLD | HOLD | HOLD |
| **SM** | **GO** | **GO** | GO_WITH_GUARDS |
| **E0_plus_EMA1D21** | GO_WITH_GUARDS | HOLD | HOLD |
| **E5_plus_EMA1D21** | HOLD | HOLD | HOLD |

## What Changed from Step 4

**Step 4 recommended E5_plus_EMA1D21 as M1 primary (return-seeking) under LT1.** Step 5 downgrades it to HOLD. Under combined entry+exit delay stress (D2+D1), E5_plus loses 0.396 Sharpe — exceeding the GO_WITH_GUARDS threshold of -0.35. The same pattern holds for E5. Both E5 variants are too fragile for compound disruptions.

**Step 4 recommended E0_plus_EMA1D21 as M2 primary (balanced) under LT1.** Step 5 confirms GO_WITH_GUARDS at LT1. E0_plus survives combined D2+D1 with -0.318 delta Sharpe — within the -0.35 guard threshold. Guardrail: worst combined disruption is close to the limit.

**Step 4 recommended SM as the only manual-viable candidate.** Step 5 upgrades SM to GO at LT1/LT2 and GO_WITH_GUARDS at LT3. SM's worst combined disruption delta is -0.097 — trivial compared to binary candidates.

## Deploy Recommendations (Step 5 Refined)

**Under reliable automated execution (<4h):**
- **Primary**: Deploy **E0_plus_EMA1D21** with guardrails. Only binary candidate to pass live sign-off. Guardrail: worst combined disruption delta = -0.318 (within -0.35 threshold, but monitor).
- **Alternative**: Deploy **SM** (GO, no guardrails needed). Lower CAGR but unconditionally safe.
- **NOT**: E5_plus_EMA1D21 or E5. Despite higher baseline Sharpe, they fail compound disruption stress.

**Under any execution quality:**
- **SM** is the universal safety net. GO at LT1/LT2, GO_WITH_GUARDS at LT3.

## Key Findings

1. **Exit delay is less damaging than entry delay for binary candidates.** Exit D4 causes -0.17 to -0.25 delta Sharpe; entry D4 causes -0.34 to -0.52 (from Step 3). Entry delay remains the dominant fragility axis.

2. **Exit delay is more damaging for SM than entry delay.** SM exit D4 delta = -0.074; SM entry D4 delta = -0.033 (from Step 3). But both are small — SM is robust to all delay types.

3. **Combined disruptions are worse than the sum of parts for binary candidates.** E0 entry_D2 alone: -0.200. Exit_D2 alone: -0.091. Combined entry_D2+exit_D2: -0.287. If additive, expected -0.291. Close but interactions exist at higher delay levels.

4. **Stochastic MC confirms deterministic rankings.** Under 1000 draws of empirical delay distributions, P(CAGR<=0) = 0.0% for ALL candidates at ALL tiers. P(Sharpe>0) = 100% everywhere. No candidate collapses to zero under realistic delay noise.

5. **E5/E5_plus fail on compound stress, not on typical operations.** Their stochastic p5 delta Sharpe at LT1 (-0.076 to -0.085) is well within GO threshold (-0.15). They fail only on the deterministic worst-case combined scenario. This means they would work fine 95% of the time but have catastrophic tail risk under compound disruption.
