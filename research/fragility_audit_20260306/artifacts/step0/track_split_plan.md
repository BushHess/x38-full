# Track Split Plan — Step 0

## Track A: E0 Home-Run Dependence Audit

### Status: GO

### Rationale
An existing E0 trade log (192 trades, `trades_candidate.csv`) passes RECON_PASS against `full_backtest_detail.json` (exact trade count match, period 2019-01-01 to 2026-02-20, 50 bps RT, terminal wealth 199173.14). The `trade_profile_8x5` already computes T1-T8 diagnostics for E0 including top-N concentration, jackknife, Gini/HHI, skew/kurtosis, and MFE/MAE.

### Prerequisites (all met)
1. E0 fill ledger reconciled: RECON_PASS
2. trade_profile_8x5 E0 results available: T1-T8 all present
3. MFE/MAE per-trade CSV: `results/trade_profile_8x5/E0/mfe_mae_per_trade.csv` (192 trades)

### Artifacts Already Available
- `results/parity_20260305/eval_e0_vs_e0/results/trades_candidate.csv` (192 trades, 22 columns)
- `results/trade_profile_8x5/E0/profile.json` (full T1-T8 in JSON)
- `results/trade_profile_8x5/E0/mfe_mae_per_trade.csv` (per-trade MFE/MAE)
- `results/trade_profile_8x5/E0/exit_reason_detail.json` (exit reason breakdown)
- `results/trade_profile_8x5/summary_8x5.csv` (cross-strategy summary row for E0)

### Artifacts Still Missing
1. **Sensitivity curve** (top-trade removal 0-20% vs remaining wealth/CAGR)
2. **Cliff-edge detection** from sensitivity curve
3. **Giveback ratio** (exists in old postmortem but NON_CANONICAL; needs re-derivation)
4. **Skip-after-N-losses** simulation
5. **Formal home-run dependence report** synthesizing all metrics

### Can Track A Create Standalone E0 Insight Before Track B?
**YES.** Track A has enough reconciled data to produce a complete E0 home-run dependence audit immediately. The existing trade_profile_8x5 provides 80%+ of the required metrics. Only the sensitivity curve, cliff-edge detection, giveback, and skip-after-N-losses need new code.

---

## Track B: Cross-Strategy Canonical Episode Ledger Build

### Status: GO (with one minor prerequisite)

### Rationale
All 6 candidate fill ledgers are reconciled (RECON_PASS). For 5/6 candidates, trade_profile_8x5 provides full T1-T8 metrics. E5_plus_EMA1D21 has a reconciled trade CSV but is not yet included in trade_profile_8x5.

### Prerequisites
1. All 6 fill ledgers reconciled: **MET** (all RECON_PASS)
2. Canonical episode definition frozen: **MET** (each trade = one flat->long->flat episode, n_buy_fills=1, n_sell_fills=1 for all strategies)
3. E5_plus_EMA1D21 trade profile: **NOT MET** — must either rerun trade_profile_8x5.py with 6th candidate added, or compute metrics separately

### Blocker
**Minor**: E5_plus_EMA1D21 needs trade_profile_8x5 metrics (MFE/MAE, concentration, jackknife, fat-tails). The trade CSV exists and is reconciled; only the profile computation is missing.

### Artifacts Already Available (per candidate)
| Candidate | Fill Ledger | Native Episode | MFE/MAE | T1-T8 Profile |
|-----------|-------------|----------------|---------|---------------|
| E0 | READY | READY | READY | READY |
| E5 | READY | READY | READY | READY |
| SM | READY | READY | READY | READY |
| LATCH | READY | READY | READY | READY |
| E0_plus_EMA1D21 | READY | READY | READY | READY |
| E5_plus_EMA1D21 | READY | READY | MISSING | MISSING |

### Artifacts Still Missing (Track B scope)
1. **E5_plus_EMA1D21 trade profile** (T1-T8 metrics, MFE/MAE)
2. **Unit-Size Episode Ledger** formal view for all 6 (return_pct column exists but normalized Sharpe/CAGR recomputation needed)
3. **Giveback ratio** for all 6 candidates
4. **Sensitivity curve** for all 6
5. **Cliff-edge detection** for all 6
6. **Skip-after-N-losses** for all 6
7. **Missed-entry / outage / delayed-entry** (requires signal replay for all 6)

---

## Execution Order Recommendation

**Track A first, then Track B.**

Rationale:
1. Track A is fully unblocked — all E0 data is reconciled and 80%+ metrics exist.
2. Track A's new diagnostic code (sensitivity curve, cliff-edge, giveback, skip-N-losses) will be reusable for Track B.
3. Track B's minor blocker (E5_plus_EMA1D21 profile) can be resolved in parallel or as Track B's first step.
4. Track A's standalone E0 insight is valuable even if Track B takes longer.
5. The fragility metrics requiring signal replay (missed-entry, outage, delayed-entry) should be deferred to a later step after Track A and core Track B are complete.

### Suggested Step 1 Scope
- **Step 1A**: Implement sensitivity curve + cliff-edge + giveback + skip-N-losses for E0; produce E0 home-run dependence report
- **Step 1B**: Extend trade_profile_8x5 to include E5_plus_EMA1D21; run same diagnostics for all 6; produce cross-strategy comparison
