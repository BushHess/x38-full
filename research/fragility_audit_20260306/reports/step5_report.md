# Step 5 Report — Live Sign-Off Hardening

> **SUPERSEDED (2026-03-09):** Sign-off verdicts below are outdated.
> After framework reform (Wilcoxon WFO, PSR gate, bootstrap CI):
> - **E5+EMA1D21 = PRIMARY** (PROMOTE, PSR=0.9993)
> - **X0 / E0+EMA1D21 = HOLD** (PSR=0.8908 < 0.95)
> See `CHANGELOG.md` (2026-03-09). Stress-test methodology below remains valid.

**Audit**: Trade Structure & Fragility (research/fragility_audit_20260306)
**Date**: 2026-03-06
**Status**: SUPERSEDED — see header note
**Runtime**: 8.4 minutes (505s)

---

## 1. Purpose

Step 5 converts Step 4's deployment recommendations into explicit GO / GO_WITH_GUARDS / HOLD / NO_GO sign-off decisions by stress-testing the remaining 5 candidates (LATCH dropped in Step 4) under exit delay, combined disruptions, and stochastic delay Monte Carlo. This is the live sign-off hardening phase — the final gate before capital deployment.

## 2. Candidates Tested

| Candidate | Type | Variant | Baseline Sharpe (replay) | Step 4 Disposition |
|---|---|---|---|---|
| E0 | binary | E0 | 1.138 | CONDITIONAL_DEPLOY |
| E5 | binary | E5 | 1.230 | CONDITIONAL_DEPLOY |
| SM | vol_target | SM | 0.816 | PRIMARY_DEPLOY (M3) |
| E0_plus_EMA1D21 | binary | E0_plus | 1.175 | PRIMARY_DEPLOY (M2) |
| E5_plus_EMA1D21 | binary | E5_plus | 1.270 | PRIMARY_DEPLOY (M1) |

Note: Replay Sharpe differs from BacktestEngine Sharpe (trade-level vs bar-level computation). Relative rankings are preserved.

## 3. Phase B — Harness Validation

All 5 candidates pass REPLAY_REGRESS:
- Trade count: exact match for all 5
- Entry/exit timestamps: exact match for all 5
- Native terminal: within $1 for all 5
- Exit delay=0 matches baseline: confirmed for all 5

**Verdict**: Harness validated. Exit delay extension does not break baseline fidelity.

## 4. Phase C — Exit Delay Grid

Exit delays of 1-4 H4 bars tested. Key results:

| Candidate | D1 delta Sharpe | D2 delta | D3 delta | D4 delta |
|---|---|---|---|---|
| E0 | -0.168 | -0.091 | -0.176 | -0.243 |
| E5 | -0.113 | -0.125 | -0.149 | -0.251 |
| SM | -0.012 | -0.062 | -0.074 | -0.074 |
| E0_plus | -0.187 | -0.106 | -0.176 | -0.241 |
| E5_plus | -0.126 | -0.129 | -0.161 | -0.247 |

**Finding**: Exit delay is the secondary fragility axis. Binary D4 exit delay causes -0.24 to -0.25 Sharpe loss (~60-70% of entry D4 from Step 3). SM remains robust (max -0.074). Non-monotonic D1>D2 pattern for E0/E0_plus due to delay-dependent trade alignment.

Exit delay MDD impact is moderate: +0.03 to +0.12 for binary candidates at D4, confirming positions stay open longer during delays but without catastrophic drawdown amplification.

## 5. Phase D — Combined Disruptions

7 scenarios combining entry delay, exit delay, and worst-case missed entries:

| Scenario | E0 | E5 | SM | E0_plus | E5_plus |
|---|---|---|---|---|---|
| baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| entry_D2 | -0.200 | -0.297 | +0.012 | -0.202 | -0.310 |
| exit_D2 | -0.091 | -0.125 | -0.062 | -0.106 | -0.129 |
| entry_D2+exit_D1 | **-0.322** | **-0.402** | -0.000 | **-0.318** | **-0.396** |
| entry_D2+exit_D2 | -0.287 | -0.394 | -0.051 | -0.286 | -0.387 |
| entry_D4+exit_D2 | -0.365 | -0.523 | -0.097 | -0.412 | -0.575 |
| full_LT2_sim | -0.322 | -0.402 | -0.000 | -0.318 | -0.396 |

**Finding**: Combined disruptions are the binding constraint for live sign-off. E5/E5_plus exceed -0.35 (GO_WITH_GUARDS threshold) under entry_D2+exit_D1. E0/E0_plus survive within -0.35. SM is barely affected.

**Key insight**: SM's entry_only_D2 IMPROVES Sharpe by +0.012 — entry delay occasionally causes SM to enter at better prices due to its vol-target sizing and breakout confirmation logic.

## 6. Phase E — Stochastic Delay Monte Carlo

1000 draws per candidate per latency tier using empirical delay distributions:
- LT1: entry {0:80%, 1:15%, 2:5%}, exit {0:85%, 1:15%}
- LT2: entry {0:10%, 1:35%, 2:30%, 3:15%, 4:10%}, exit {0:25%, 1:45%, 2:20%, 3:10%}
- LT3: entry {2:10%, 3:20%, 4:30%, 5:25%, 6:15%}, exit {1:20%, 2:35%, 3:25%, 4:20%}

Key stochastic results:

| Candidate | LT1 p50 Sharpe | LT1 p5 | LT2 p50 | LT2 p5 | LT3 p50 | LT3 p5 |
|---|---|---|---|---|---|---|
| E0 | 1.107 | 1.066 | 0.977 | 0.898 | 0.793 | 0.678 |
| E5 | 1.202 | 1.154 | 1.043 | 0.959 | 0.740 | 0.630 |
| SM | 0.820 | 0.798 | 0.797 | 0.751 | 0.713 | 0.652 |
| E0_plus | 1.142 | 1.100 | 1.020 | 0.941 | 0.793 | 0.683 |
| E5_plus | 1.235 | 1.185 | 1.091 | 1.001 | 0.740 | 0.621 |

- **P(CAGR<=0) = 0.0%** for ALL candidates at ALL tiers
- **P(Sharpe>0) = 100%** everywhere
- SM has the narrowest LT1-to-LT3 spread (0.820 → 0.713, -13%) vs E5_plus (1.235 → 0.740, -40%)

## 7. Phase F — Sign-Off Gate Evaluation

Gates applied per tier with tier-appropriate combined scenario filtering (max delay ≤ 2 for LT1, ≤ 4 for LT2, all for LT3):

### Final Sign-Off Matrix

| Candidate | LT1 | LT2 | LT3 |
|---|---|---|---|
| E0 | GO_WITH_GUARDS | HOLD | HOLD |
| E5 | HOLD | HOLD | HOLD |
| SM | **GO** | **GO** | GO_WITH_GUARDS |
| E0_plus | GO_WITH_GUARDS | HOLD | HOLD |
| E5_plus | HOLD | HOLD | HOLD |

### Gate detail for E0_plus at LT1 (GO_WITH_GUARDS):
- p5 delta Sharpe: -0.075 (threshold -0.30) PASS
- P(CAGR<=0): 0.0% (threshold 20%) PASS
- p95 delta MDD frac: -0.197 (threshold +0.50) PASS
- Worst combo delta Sharpe: -0.318 (threshold -0.35) PASS (margin: 0.032)
- Guardrail: worst combined disruption is close to threshold limit

### Gate detail for SM at LT3 (GO_WITH_GUARDS):
- p5 delta Sharpe: -0.164 (threshold -0.30) PASS
- P(CAGR<=0): 0.0% (threshold 20%) PASS
- p95 delta MDD frac: +0.167 (threshold +0.50) PASS
- Worst combo delta Sharpe: -0.097 (threshold -0.35) PASS
- Guardrail: Sharpe degradation p5=-0.164 exceeds GO threshold of -0.15

### Binding constraint analysis:
- E0/E0_plus blocked from GO by worst combined disruption (-0.32 > -0.20)
- E5/E5_plus blocked from GO_WITH_GUARDS by worst combined disruption (-0.40 > -0.35)
- SM blocked from GO at LT3 by p5 delta Sharpe (-0.164 > -0.15)

## 8. How Step 5 Refines Step 4

| Step 4 Recommendation | Step 5 Verdict | Change |
|---|---|---|
| E5_plus PRIMARY_DEPLOY M1/LT1 | HOLD at LT1 | **DOWNGRADE** — compound fragility |
| E0_plus PRIMARY_DEPLOY M2/LT1 | GO_WITH_GUARDS at LT1 | **CONFIRMED** with guardrails |
| E0 CONDITIONAL_DEPLOY LT2 | HOLD at LT2 | Remains conditional; tight margin |
| SM PRIMARY_DEPLOY M3/any | GO at LT1/LT2, GO_WITH_GUARDS at LT3 | **UPGRADED** — quantified robustness |
| E5 CONDITIONAL_DEPLOY | HOLD everywhere | Not deployable for live capital |

**Step 5's decisive contribution**: E5_plus_EMA1D21, which was the highest-Sharpe candidate and Step 4's M1 primary, is NOT safe for live deployment. Its combined disruption sensitivity (-0.40 under entry_D2+exit_D1) exceeds the GO_WITH_GUARDS threshold. E0_plus_EMA1D21 replaces it as the strongest live-deployable binary candidate.

## 9. Pairwise Comparisons

**E0_plus vs E5_plus (live sign-off)**: E0_plus is GO_WITH_GUARDS at LT1; E5_plus is HOLD. Despite E5_plus having +0.095 higher baseline Sharpe, its compound fragility disqualifies it. E0_plus's lower entry delay sensitivity (from Step 3's E0 vs E5 comparison) translates directly into better compound disruption survival.

**E0 vs E0_plus (live sign-off)**: Both are GO_WITH_GUARDS at LT1 with similar margins. E0_plus has slightly better worst-combo delta (-0.318 vs -0.322) and higher baseline. E0_plus remains preferred.

**SM vs all binary (robustness gap)**: SM's worst combined delta is -0.097. The nearest binary candidate (E0_plus) is -0.318. This 3.3x gap in compound resilience is the defining structural difference between vol-target and binary approaches.

## 10. Artifacts Produced

### Root level (10 files):
- `exit_delay_cross_summary.csv` — 5 candidates x 4 exit delays
- `combined_disruption_cross_summary.csv` — 5 candidates x 7 scenarios
- `stochastic_delay_cross_summary.csv` — 5 candidates x 3 tiers
- `signoff_matrix.csv` — 5 candidates x 3 tiers with status and metrics
- `harness_validation_summary.csv` — 5 candidates REPLAY_REGRESS
- `step5_summary.json` — machine-readable summary
- `exit_delay_delta_sharpe.png` — figure
- `combined_disruption_worstcase.png` — figure
- `stochastic_delay_p95_matrix.png` — figure
- `live_signoff_matrix.png` — figure

### Per-candidate (5 files each x 5 candidates = 25 files):
- `harness_validation.json`
- `exit_delay_summary.json`
- `combined_disruption_summary.json`
- `stochastic_delay_summary.json`
- `signoff_gates.json`

### Companion MDs (7 files):
- `final_live_signoff_memo.md`
- `signoff_findings.md`
- `remaining_open_items.md`
- `exit_delay_delta_sharpe.md`
- `combined_disruption_worstcase.md`
- `stochastic_delay_p95_matrix.md`
- `live_signoff_matrix.md`

Total: 42 files.

## 11. Scripts

- `code/step5/run_step5_live_signoff.py` — main simulation script (1000+ lines)
  - Extends Step 3 replay harness with exit delay support
  - Implements Phases B-G per specification
  - Runtime: 8.4 minutes for all 5 candidates
- `code/step5/recompute_signoff.py` — lightweight sign-off recomputation script
  - Recomputes tier-aware signoff gates from existing artifacts
  - No replay needed — pure arithmetic

## 12. Mandatory Questions

**Q: Does exit delay change the candidate ranking?**
A: No. The ranking E5_plus > E0_plus > E5 > E0 > SM (by baseline Sharpe) is preserved under exit delay. But exit delay combined with entry delay changes the DEPLOYABILITY ranking: SM > E0_plus > E0 > E5 > E5_plus.

**Q: Is any candidate more fragile to exit delay than entry delay?**
A: SM is slightly more sensitive to exit delay (D4: -0.074) than entry delay (D4: -0.033 from Step 3). All binary candidates are LESS sensitive to exit delay than entry delay. This is the Step 4-predicted gap: exit delay is the secondary axis.

**Q: Do combined disruptions reveal interaction effects?**
A: Yes. For binary candidates, combined entry+exit delay is approximately additive (entry_D2 + exit_D2 predicted: -0.291 for E0; actual: -0.287). But at higher delay levels, super-additive effects appear. SM shows sub-additive effects (entry+exit is less than sum due to correlated delay effects on vol-target rebalancing).

**Q: Does stochastic MC change any sign-off decision vs deterministic?**
A: The stochastic MC alone would give every binary candidate GO at LT1 (p5 delta Sharpe > -0.15 for all). The binding constraint comes from deterministic combined disruption, not stochastic performance. This means binary candidates are fine under typical delay distributions but have tail risk under compound worst-case scenarios.

## 13. Stop Condition

All phases (B-G) complete. All artifacts written. Sign-off matrix produced. Step 5 refines Step 4 with one material change: E5_plus_EMA1D21 downgraded from PRIMARY_DEPLOY to HOLD; E0_plus_EMA1D21 confirmed as the strongest live-deployable binary candidate with GO_WITH_GUARDS at LT1.

---

**STOPPED AFTER STEP 5**
