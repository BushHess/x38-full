# Live Sign-Off Matrix: Candidate x Latency Tier

**File**: `live_signoff_matrix.png`

Categorical heatmap showing sign-off status (GO / GO_WITH_GUARDS / HOLD / NO_GO) for each candidate at each latency tier.

Sign-off gates (all must pass for each status):
- GO: p5 delta Sharpe >= -0.15, P(CAGR<=0) <= 10%, p95 delta MDD <= +25% baseline, worst combo delta Sharpe > -0.20
- GO_WITH_GUARDS: p5 delta Sharpe >= -0.30, P(CAGR<=0) <= 20%, p95 delta MDD <= +50% baseline, worst combo delta Sharpe > -0.35
- HOLD: positive median CAGR but fails GO_WITH_GUARDS
- NO_GO: otherwise

Key observations:
- SM is the only candidate with GO status (green) at any tier
- E0/E0_plus get GO_WITH_GUARDS (orange) at LT1 only
- E5/E5_plus are HOLD (yellow) everywhere — compound disruption sensitivity too high
- No candidate receives NO_GO (red) — all have positive stochastic CAGR
- The binding constraint for E5/E5_plus is worst combined disruption, not stochastic performance
