# Remaining Open Items After Step 5

## Resolved by Step 5

1. **Exit delay not tested** (Step 4 risk #1) — RESOLVED. Exit delay tested at 1-4 H4 bars for all 5 candidates. Exit delay is the secondary fragility axis (~60-70% of entry delay sensitivity for binary candidates).

2. **Combined disruption not tested** (Step 4 risk #2) — RESOLVED. 7 combined scenarios tested. Compound disruptions worse than sum of parts for binary candidates but not for SM.

3. **Replay harness not validated against live engine** (Step 4 recommendation) — PARTIALLY RESOLVED. Harness validated via REPLAY_REGRESS (trade count, timestamps, terminal NAV). Full engine-vs-harness comparison under disruption not performed (would require BacktestEngine modifications).

## Still Open

1. **BacktestEngine disruption replay**: The standalone harness is validated for baseline fidelity but not proven equivalent to BacktestEngine under disruption scenarios. This is a fidelity concern, not a research gap — the harness correctly implements the signal-flow semantics.

2. **E0_plus margin tightness**: E0_plus_EMA1D21 passes GO_WITH_GUARDS at LT1 with only 0.032 Sharpe units of headroom on the worst combined disruption gate. Any additional degradation source (data feed delay, exchange outage, order execution failure) could push it past the threshold. Recommend monitoring this gate metric in live operation.

3. **OOS consistency**: Step 5 does not address the bootstrap/WFO gap from Step 4 (E5_plus WFO 5/8 vs E0_plus 6/8). The HOLD verdict for E5_plus is driven by compound fragility, not OOS consistency — these are independent concerns.

4. **Regime-conditional disruption**: All disruptions tested are regime-independent. If execution delays concentrate in high-volatility regimes (which is empirically plausible), the impact could be asymmetric. Not tested.

5. **Multi-strategy portfolio disruption**: If deploying E0_plus + SM as a portfolio, their combined disruption profile may differ from the sum of individual profiles due to correlated entry/exit timing. Not tested.

## Items That Do Not Need Further Work

- SM vs LATCH: LATCH was dropped in Step 4. No Step 5 testing needed.
- Stochastic delay model: Completed with 1000 draws x 3 tiers x 5 candidates. Sufficient for p5/p95 estimation.
- Entry delay (already tested in Step 3): Reconfirmed through combined disruption scenarios.
- Random miss (already tested in Step 3): Folded into combined disruptions via worst-case miss.
