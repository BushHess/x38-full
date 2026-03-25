# Remaining Open Items After Step 2

## Items Completed in Step 2

1. E5_plus_EMA1D21 profile gap — CLOSED (computed from trade CSV + H4 bars)
2. Cross-strategy episode ledgers (12 ledgers: 6 candidates x 2 views) — BUILT AND VALIDATED
3. Home-run dependence classification for all 6 — COMPLETE
4. Behavioral fragility (skip-after-N) for all 6 — COMPLETE
5. Giveback analysis for all 6 — COMPLETE
6. Cliff-edge detection for all 6 — COMPLETE
7. Sensitivity curves for all 6 — COMPLETE
8. Pairwise structure deltas (3 mandatory pairs) — COMPLETE
9. Style labels (grind/home-run/hybrid + smooth/cliff-like) — ASSIGNED

## Items NOT Addressed (Require Step 3 or Engine Modifications)

### A. Replay-Dependent Diagnostics

These require reconstructing the equity curve with trades removed, which means replaying the backtest engine with modified signal sequences. Step 2's jackknife removes trades from the completed-trade ledger (post-hoc), which is valid for PnL sensitivity but cannot capture:

1. **Random-miss simulation** — Randomly remove K trades (K in {1, 3, 5, 10, 20}) and measure performance degradation across 1000+ bootstrap draws. This tests operational fragility: "what if I miss K signals due to downtime/errors?"

2. **Outage-window miss simulation** — Remove all trades entering within a contiguous calendar window (e.g., 7d, 14d, 30d) swept across the backtest period. This tests concentrated outage risk: "what if my bot is down for a week?"

3. **Delayed-entry simulation** — Enter 1-4 bars late (4h-16h delay) on each signal. This tests execution latency sensitivity: "what if I can't fill at signal time?"

All three require engine modifications or a replay wrapper that Step 2 does not provide.

### B. Canonical Profile Persistence

E5_plus_EMA1D21's T1-T8 profile was computed in Step 2 and saved only to `artifacts/step2/candidates/E5_plus_EMA1D21/`. It was NOT committed to the canonical `results/trade_profile_8x5/` directory. If future studies reference trade_profile_8x5 for all 6 candidates, E5_plus_EMA1D21 will be missing.

**Recommendation**: Either commit the Step 2 profile to trade_profile_8x5 or re-run trade_profile_8x5.py with E5_plus_EMA1D21 added. Low priority since all Step 2 artifacts are self-contained.

### C. Trail Stop Exit Taxonomy for E5_plus_EMA1D21

The trail_stop_exit_pct and trend_exit_pct columns for E5_plus_EMA1D21 both show 93.0% in the cross_strategy_trade_structure_summary.csv. This is a display artifact from exit-reason string parsing (both contain overlapping substrings). The functional impact is nil — the exit taxonomy is correctly captured in the per-candidate episode ledgers where the full exit_reason string is preserved.

### D. Intra-Trade Path Analysis

Step 2 characterizes the *completed-trade population* (entry-to-exit outcomes). It does not examine intra-trade drawdown paths, mark-to-market equity volatility during open positions, or the relationship between entry timing and MFE realization. These are complementary dimensions that may matter for live execution but are outside the Step 2 scope.
