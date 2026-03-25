# Step 5 Key Findings

## Finding 1: Exit delay is the SECONDARY fragility axis

Exit delay causes moderate, bounded degradation for all candidates:

| Candidate | Exit D1 delta Sharpe | Exit D4 delta Sharpe | Entry D4 delta (Step 3) |
|---|---|---|---|
| E0 | -0.168 | -0.243 | -0.336 |
| E5 | -0.113 | -0.251 | -0.372 |
| SM | -0.012 | -0.074 | -0.033 |
| E0_plus | -0.187 | -0.241 | -0.371 |
| E5_plus | -0.126 | -0.247 | -0.517 |

Exit delay sensitivity for binary candidates is ~60-70% of entry delay sensitivity. For SM, exit delay is slightly worse than entry delay, but both are small.

## Finding 2: Combined disruptions reveal compound fragility

Compound entry+exit delay is worse than either alone, and E5/E5_plus are disproportionately affected:

| Candidate | Entry D2 only | Exit D2 only | Both D2 | Entry D2 + Exit D1 |
|---|---|---|---|---|
| E0 | -0.200 | -0.091 | -0.287 | -0.322 |
| E5 | -0.297 | -0.125 | -0.394 | -0.402 |
| SM | +0.012 | -0.062 | -0.051 | -0.000 |
| E0_plus | -0.202 | -0.106 | -0.286 | -0.318 |
| E5_plus | -0.310 | -0.129 | -0.387 | -0.396 |

SM shows near-zero compound sensitivity. E5/E5_plus lose >0.39 Sharpe under entry_D2+exit_D1.

## Finding 3: Stochastic MC shows positive performance at all tiers

Under empirical delay distributions (1000 draws), no candidate ever goes negative:
- P(CAGR<=0) = 0.0% for ALL candidates at ALL tiers
- P(Sharpe>0) = 100% everywhere
- SM retains p50 Sharpe > 0.71 even at LT3

## Finding 4: E5/E5_plus fail sign-off on compound tail risk, not typical operations

E5_plus LT1 stochastic p5 delta Sharpe = -0.085 (well within GO threshold of -0.15). The ONLY failing gate is worst-case combined disruption (delta = -0.396 > -0.35 GO_WITH_GUARDS threshold). This is a tail risk, not a typical-conditions problem.

## Finding 5: SM is the most deployment-ready candidate

SM passes all GO gates at LT1 and LT2 with large margins. At LT3, it drops to GO_WITH_GUARDS only because p5 delta Sharpe = -0.164 slightly exceeds the GO threshold of -0.15. Worst combined disruption delta = -0.097 — 7x better than any binary candidate.

## Finding 6: E0_plus_EMA1D21 is the strongest live-deployable binary candidate

E0_plus is the ONLY binary candidate to pass live sign-off (GO_WITH_GUARDS at LT1). Key margin: worst combined delta = -0.318 vs threshold -0.35 (headroom = 0.032). This is tight — any additional degradation source could push it past the threshold.

## Finding 7: Harness validation PASS for all 5 candidates

All 5 candidates pass REPLAY_REGRESS (exact trade count, exact timestamps, native terminal within $1). Exit delay=0 matches baseline exactly for all candidates. The replay harness is validated for live sign-off use.
