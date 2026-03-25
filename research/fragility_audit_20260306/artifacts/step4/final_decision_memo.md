# Final Decision Memo — VTREND 6-Strategy Candidate Set

**To**: PM / Research Lead
**From**: Trade Structure & Fragility Audit (Steps 0-4)
**Date**: 2026-03-06
**Status**: Research conclusion READY. No further analysis needed for candidate ranking.

---

## What to Deploy

**Under reliable automated execution (<4h latency):**

- **Return-seeking (M1)**: Deploy **E5_plus_EMA1D21**. Sharpe 1.430, CAGR 59.9%. Highest raw performer. Requires strict automation — performance collapses beyond 8h delay.
- **Balanced (M2)**: Deploy **E0_plus_EMA1D21**. Sharpe 1.325, CAGR 54.7%. Only strategy to pass ALL validation gates. WFO 6/8. Most defensible deployment story.
- **Both**: E0_plus is the safer default. E5_plus is the upside play if execution infrastructure is battle-tested.

**Under degraded automated execution (4-16h):**

- Deploy **E0**. Simplest implementation. Least delay-fragile binary (D4: -29.5% Sharpe loss vs -31.7% to -40.7% for EMA-overlaid variants). Still loses meaningful performance — accept this tradeoff or fall back to SM.

**Under manual/semi-manual execution (>16h or frequent operator delay):**

- Deploy **SM** only. It is the only candidate that survives manual execution (4% Sharpe loss at 16h delay vs 29-41% for binary candidates). CAGR 16% is the accepted price of operational robustness.

## What Not to Deploy

- **LATCH**: Drop immediately. Near-duplicate of SM at every level of analysis (Steps 2 and 3). Hysteresis mechanism adds ~5 parameters with zero measurable benefit. SM is the preferred vol-target representative.
- **Any binary candidate under LT3**: No binary strategy (E0/E5/E0_plus/E5_plus) is viable for manual or semi-manual execution. Hard constraint, not a preference.

## What to Stop Spending Time On

- **SM vs LATCH comparisons**: Settled. SM wins on simplicity. LATCH is redundant.
- **New candidate discovery**: The existing 5-candidate set (after dropping LATCH) covers all viable mandate x latency cells. No gap exists that a new variant would fill.
- **Weighted scalar scoring**: The old exposure-biased composite score gave SM/LATCH "REJECT" because it was CAGR-weighted. Steps 1-3 show SM has genuine, decision-relevant value under M3/LT2-3. The mandate x latency matrix replaces the scalar score.

## What Step 5 Would and Would Not Change

**Would not change**: Candidate ranking. The relative ordering (E5_plus > E0_plus > E5 > E0 at LT1; SM only at LT3) is robust across all evidence layers. Step 5 could only refine confidence bounds, not flip any recommendation.

**Would change**: Deployment confidence. Step 5 would validate the standalone replay harness against the live BacktestEngine, test combined disruptions (simultaneous miss + delay), and test exit-delay scenarios. These are deployment-safety checks, not research questions.

**Recommendation**: Step 5 is optional for the research conclusion. It is recommended for live sign-off if the system will handle real capital.
