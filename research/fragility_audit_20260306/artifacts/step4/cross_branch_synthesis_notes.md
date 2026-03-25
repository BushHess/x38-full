# Cross-Branch Synthesis Notes

> **SUPERSEDED (2026-03-09):** PRIMARY_DEPLOY recommendations below are outdated.
> E5+EMA1D21 = PRIMARY, X0 = HOLD after framework reform. See `CHANGELOG.md`.

## Branch Structure

Two research branches converge in Step 4:

1. **Old portfolio branch** (Studies #41-43, parity evaluation 2026-03-05/06)
   - Source: `results/parity_20260305/`, `results/parity_20260306/`
   - Scope: Tier 1 validation (13 suites), Tier 2 research (T1-T7), matched-risk comparison
   - Key output: per-candidate verdicts (PROMOTE/HOLD/REJECT), WFO pass rates, bootstrap robustness

2. **New trade-structure / fragility branch** (Steps 0-3, 2026-03-06)
   - Source: `research/fragility_audit_20260306/`
   - Scope: trade-level structure, home-run dependence, replay-dependent operational fragility
   - Key output: style labels, cliff-edge behavior, delay sensitivity, operational regimes

## Evidence Conflicts

**No material conflicts found.** The two branches ask different questions and their answers are complementary:

- **Old branch**: "Which candidates beat E0 as a CAGR-weighted composite?" Answer: E0_plus_EMA1D21 (PROMOTE), E5_plus_EMA1D21 (PROMOTE), others HOLD/REJECT.
- **New branch**: "How operationally fragile are these candidates?" Answer: binary class is delay-fragile; vol-target class is operationally robust but low-CAGR.

The old-branch REJECT for SM/LATCH was correct under CAGR-weighted scoring. It does NOT conflict with Step 3's finding that SM/LATCH are operationally robust — the old branch was not testing operational fragility.

## Resolution of Old-Branch Verdicts

| Candidate | Old Verdict | Step 4 Verdict | Change Justified? |
|-----------|------------|----------------|-------------------|
| E0 | HOLD | CONDITIONAL_DEPLOY | Yes — Step 3 shows E0 is least delay-fragile binary, earning LT2 fallback role |
| E5 | HOLD | CONDITIONAL_DEPLOY | Yes — beats E0 at all cost levels, serves as LT2 alt for E5_plus |
| SM | REJECT | PRIMARY_DEPLOY (M3) | Yes — REJECT was CAGR-weighted; SM is the only viable candidate under LT3 |
| LATCH | REJECT | DROP_REDUNDANT | No change in spirit — still not recommended; now dropped for redundancy with SM |
| E0_plus_EMA1D21 | PROMOTE | PRIMARY_DEPLOY (M2) | Confirmed and sharpened — now specifically M2/LT1 primary |
| E5_plus_EMA1D21 | PROMOTE | PRIMARY_DEPLOY (M1) | Confirmed and sharpened — now specifically M1/LT1 primary with LT1-only constraint |

## Key Synthesis Insight

The old branch treated all candidates as competing for a single deployment slot with a CAGR-weighted score. The new branch reveals that the correct framework is mandate x latency, where:
- Binary strategies win on raw performance but require reliable automated execution
- Vol-target strategies win on operational robustness but sacrifice CAGR
- EMA overlays sharpen the latency requirement within the binary class

This is not a disagreement with the old branch — it is a refinement that maps the same evidence onto a more decision-useful framework.

## Bootstrap Sharpe Concern

One tension between branches: the old-branch bootstrap shows E0_plus Sharpe_med = 0.562 (lowest binary) and E0_plus MDD wins 16/16 vs E0. The new branch confirms E0_plus dominates on real-data metrics. The bootstrap Sharpe concern means E0_plus may have weaker OOS consistency than E0 despite stronger in-sample metrics. This is noted but does not change the Step 4 recommendation because:
1. All binary candidates have bootstrap P(CAGR>0) > 84%
2. The WFO 6/8 for E0_plus is stronger validation than bootstrap alone
3. E0 is retained as the LT2 fallback precisely because of this concern
