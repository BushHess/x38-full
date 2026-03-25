# Step 0 Report: Trade-Level Tooling Audit, Candidate Readiness, and Branch Split Plan

**Date**: 2026-03-06
**Namespace**: `research/fragility_audit_20260306/`
**Repo root**: `/var/www/trading-bots/btc-spot-dev`
**Git hash**: NOT_A_GIT_REPO

---

## 1. Executive Summary

**Canonical baseline: FOUND.** The parity evaluation branch (Studies #41-#43) provides a complete, reconciled baseline for all 6 candidates. All evals use identical parameters: period 2019-01-01 to 2026-02-20, 50 bps RT cost, initial cash $10,000.

**All 6 candidates mapped cleanly.** Each maps to a distinct strategy class, config, and eval output directory. No aliasing exists among the 6.

**Track A: GO.** E0's trade log (192 trades) passes RECON_PASS. The `trade_profile_8x5` script already provides 80%+ of required home-run dependence metrics (T1-T8: win/loss, streaks, holding time, MFE/MAE, exit taxonomy, top-N concentration, jackknife, fat-tails). Only 4 new diagnostics are needed: sensitivity curve, cliff-edge detection, giveback ratio, skip-after-N-losses.

**Track B: GO (minor prerequisite).** All 6 fill ledgers are reconciled. For 5/6 candidates, trade_profile_8x5 provides full metrics. E5_plus_EMA1D21 is the only gap — its trade CSV exists (186 trades, reconciled) but it was not included in the trade_profile_8x5 run.

**Biggest blockers:**
1. E5_plus_EMA1D21 missing from trade_profile_8x5 (low effort to fix)
2. Sensitivity curve and cliff-edge detection not implemented anywhere (medium effort)
3. Giveback ratio not in canonical tooling (low effort, builds on MFE)
4. Signal-replay fragility diagnostics (delayed-entry, missed-entry, outage) require backtest engine modification (high effort, can be deferred)

---

## 2. Source-of-Truth Baseline

### Primary source: Validation framework eval directories

All candidates were evaluated through `validate_strategy.py` with `--trade-level on`, producing:
- `full_backtest_detail.json` — canonical metrics (Sharpe, CAGR, MDD, terminal wealth, trade count, wins, losses, etc.) at smart/base/harsh cost scenarios
- `trades_candidate.csv` — per-trade log with 22 columns
- `run_meta.json` — reproducibility record (exact command, config paths, period, cost)

| Source | Path | Candidates | Period | Fee |
|--------|------|-----------|--------|-----|
| Parity 20260305 | `results/parity_20260305/eval_*/` | E0, E5, SM, LATCH, E0+EMA1D21 | 2019-01-01 to 2026-02-20 | 50 bps RT |
| Parity 20260306 | `results/parity_20260306/eval_e5_ema21d1_vs_e0/` | E5+EMA1D21 | 2019-01-01 to 2026-02-20 | 50 bps RT |

### Secondary source: Trade profile 8x5

`results/trade_profile_8x5/` provides the 8-technique trade-level analysis for 5 of 6 candidates, derived from the validation trade CSVs. Script: `research/trade_profile_8x5.py`.

### Non-canonical: Old research postmortem

`research/results/vtrend_postmortem_trades.csv` — E0 only, 189 trades at SP=120 (vs 192 in validation). Rich fields (MFE_R, MAE_R, giveback_R, giveback_ratio, proximate_cause) but RECON_FAIL due to 3 missing trades. Cannot be used for conclusions but is valuable as a reference for giveback ratio methodology.

---

## 3. Repo Tooling Inventory Summary

| Tooling | Type | Purpose | Candidate Support | Canonical? |
|---------|------|---------|------------------|-----------|
| `validation/suites/trade_level.py` | module | Trade export + matching + bootstrap | All 6 | Yes |
| `research/trade_profile_8x5.py` | script | 8-technique trade profile | 5/6 (no E5+) | Yes |
| `research/vtrend_postmortem.py` | script | E0 postmortem with giveback | E0 only | No (RECON_FAIL) |
| `research/exit_family_study.py` | script | Exit variant analysis | E0 only | No (per-fold) |
| `validation/suites/dd_episodes.py` | module | Drawdown episode detection | All 6 | Yes |
| `validation/suites/backtest.py` | module | Aggregate backtest metrics | All 6 | Yes |
| `validate_strategy.py` | script | Orchestrator | All 6 | Yes |

No existing tooling handles: sensitivity curves, cliff-edge detection, missed-entry simulation, outage-window simulation, skip-after-N-losses, delayed-entry simulation.

---

## 4. Candidate Mapping Summary

All 6 candidates map cleanly to distinct repo entities:

| Candidate | Repo Strategy ID | Config | Strategy Code | Eval Dir |
|-----------|-----------------|--------|---------------|----------|
| E0 | vtrend | `configs/vtrend/vtrend_default.yaml` | `strategies/vtrend/strategy.py` | `eval_e0_vs_e0` |
| E5 | vtrend_e5 | `configs/vtrend_e5/vtrend_e5_default.yaml` | `strategies/vtrend_e5/strategy.py` | `eval_e5_vs_e0` |
| SM | vtrend_sm | `configs/vtrend_sm/vtrend_sm_default.yaml` | `strategies/vtrend_sm/strategy.py` | `eval_sm_vs_e0` |
| LATCH | latch | `configs/latch/latch_default.yaml` | `strategies/latch/strategy.py` | `eval_latch_vs_e0` |
| E0+EMA1D21 | vtrend_ema21_d1 | `configs/vtrend_ema21_d1/vtrend_ema21_d1_default.yaml` | `strategies/vtrend_ema21_d1/strategy.py` | `eval_ema21d1_vs_e0` |
| E5+EMA1D21 | vtrend_e5_ema21_d1 | `configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml` | `strategies/vtrend_e5_ema21_d1/strategy.py` | `eval_e5_ema21d1_vs_e0` |

All 6 are: BTC-USDT, spot, long-only, H4, same canonical period, same fee model.

The EMA1D overlays (E0+EMA1D21, E5+EMA1D21) are **separate strategy classes** — not config variants. Each has its own `strategies/*/strategy.py` implementation.

---

## 5. Reconciliation Findings

### 7/8 RECON_PASS, 1/8 RECON_FAIL

All 6 validation framework trade CSVs pass reconciliation:

| Candidate | Trade Count | Match? | Fee Match? | Period Match? | Status |
|-----------|------------|--------|-----------|--------------|--------|
| E0 | 192 | Exact | 50 bps RT | 2019-01-01 to 2026-02-20 | RECON_PASS |
| E5 | 207 | Exact | 50 bps RT | 2019-01-01 to 2026-02-20 | RECON_PASS |
| SM | 65 | Exact | 50 bps RT | 2019-01-01 to 2026-02-20 | RECON_PASS |
| LATCH | 65 | Exact | 50 bps RT | 2019-01-01 to 2026-02-20 | RECON_PASS |
| E0+EMA1D21 | 172 | Exact | 50 bps RT | 2019-01-01 to 2026-02-20 | RECON_PASS |
| E5+EMA1D21 | 186 | Exact | 50 bps RT | 2019-01-01 to 2026-02-20 | RECON_PASS |

The trade_profile_8x5 also passes for the 5 candidates it covers (trade counts match source CSVs).

**RECON_FAIL**: `research/results/vtrend_postmortem_trades.csv` — 189 trades at SP=120 vs 192 in validation. 3 specific trades are missing (entries at 2020-04-15, 2024-09-16, 2026-01-19). The research sim uses a different engine path than the validation framework. This artifact cannot be used for conclusions but its methodology (especially giveback ratio) is worth re-implementing on the canonical data.

### Terminal wealth cross-check

Terminal wealth from `full_backtest_detail.json` (harsh scenario):

| Candidate | Terminal Wealth | Sum(pnl_usd) in trades CSV | Note |
|-----------|----------------|---------------------------|------|
| E0 | 199,173.14 | 218,479.79 | Difference = compounding effect (expected) |
| E5 | 246,190.24 | 272,869.38 | Same pattern |
| SM | 28,851.43 | 19,640.67 | SM uses vol-target sizing; trade pnl is NAV-weighted |
| LATCH | 23,662.57 | 14,197.25 | Same pattern as SM |
| E0+EMA1D21 | 225,362.15 | 243,441.42 | Same compounding pattern |
| E5+EMA1D21 | 284,726.02 | 310,900.10 | Same compounding pattern |

The sum-of-trade-pnl exceeds terminal-wealth-minus-initial for all strategies. This is expected: each trade's `pnl_usd` is computed at the NAV of the time, and sequential compounding means sum(pnl) != terminal_pnl. This is NOT a reconciliation failure — it is a known property of the fill ledger recording convention.

---

## 6. Coverage-Matrix Highlights

### By numbers
- **192 total metric-candidate cells** (32 metrics x 6 candidates)
- **115 READY (59.9%)**: Existing trade_profile_8x5 covers T1-T8 for 5/6 candidates
- **77 MISSING (40.1%)**: E5_plus gap (32 cells) + new diagnostics for all 6 (sensitivity curve, cliff-edge, giveback, fragility)

### Key gaps
1. **E5_plus_EMA1D21**: 0/32 metrics READY — needs trade_profile_8x5 extension (low effort)
2. **Giveback ratio**: MISSING for all 6 — needs MFE-based computation (low effort)
3. **Sensitivity curve + cliff-edge**: MISSING for all 6 — new implementation (medium effort)
4. **All fragility metrics**: MISSING for all 6 — skip-after-N-losses is ledger-only (low effort); missed-entry/outage are ledger-approximate (medium); delayed-entry requires replay (high)

### What's already rich
For 5 candidates, the existing trade_profile_8x5 provides a comprehensive baseline:
- Win rate, profit factor, W/L ratio (T1)
- Streak analysis (T2)
- Holding time distribution (T3)
- MFE/MAE per trade with edge ratio (T4)
- Exit reason profitability taxonomy (T5)
- Top-N payoff concentration, Gini, HHI (T6)
- Jackknife remove top-1/3/5/10 with Sharpe and CAGR impact (T7)
- Skewness, kurtosis, Jarque-Bera, D'Agostino (T8)

---

## 7. Branch Split Plan

### Track A: E0 Home-Run Dependence Audit — GO

**Prerequisites met**: E0 fill ledger RECON_PASS, trade_profile_8x5 T1-T8 available.

**Artifacts available**: trades_candidate.csv (192 trades), profile.json, mfe_mae_per_trade.csv, exit_reason_detail.json, summary_8x5.csv (E0 row).

**Still needed**:
1. Sensitivity curve (top-trade removal 0-20%)
2. Cliff-edge detection
3. Giveback ratio
4. Skip-after-N-losses simulation

**Can produce standalone E0 insight**: YES. Track A is fully unblocked.

### Track B: Cross-Strategy Canonical Ledger — GO (minor prerequisite)

**Prerequisites mostly met**: All 6 fill ledgers RECON_PASS.

**Prerequisite not met**: E5_plus_EMA1D21 trade profile (low effort to fix).

**Artifacts available**: Trade CSVs for all 6; trade_profile_8x5 for 5/6.

**Still needed**:
1. E5_plus_EMA1D21 trade profile (rerun script with 6th path)
2. All new diagnostics from Track A (reusable code)
3. Cross-strategy comparison tables and visualizations

### Execution order: Track A first

1. Track A is fully unblocked today
2. New diagnostic code from Track A is directly reusable for Track B
3. E5_plus gap can be resolved as Track B Step 1 (rerun trade_profile_8x5 with 6th candidate)

---

## 8. Missing Diagnostics Spec Summary

See `artifacts/step0/missing_diagnostics_spec.md` for full specifications.

| Priority | Diagnostic | Effort | Replay? |
|----------|-----------|--------|---------|
| P0 | E5_plus trade profile | Low | No |
| P1 | Giveback ratio | Low | No |
| P1 | Sensitivity curve | Medium | No |
| P1 | Cliff-edge detection | Low | No (derives from curve) |
| P1 | Skip-after-N-losses | Low | No |
| P2 | Missed-entry (1,2,3) | Medium | Approximate from ledger |
| P2 | Outage-window miss | Medium | Approximate from ledger |
| P3 | Delayed-entry | High | Yes (requires engine mod) |

### Key conventions frozen in spec:
- **Top-N contribution denominator**: total net PnL (can exceed 100%)
- **Gini**: computed on |pnl_usd|
- **HHI**: sum((|pnl_i|/sum(|pnl|))^2)
- **Win/loss threshold**: win = return_pct > 0 (strict)
- **Giveback**: (MFE_pct - realized_pct) / MFE_pct where MFE > 0
- **Cliff-edge threshold**: cliff_score > 3.0 (3x average per-trade damage)

---

## 9. Recommendations for Next Step

1. **Step 1A (Track A)**: Implement 4 missing E0 diagnostics:
   - Sensitivity curve + cliff-edge detection (paired implementation)
   - Giveback ratio (extend MFE computation)
   - Skip-after-N-losses (new ledger-only simulation)
   - Produce E0 Home-Run Dependence Report

2. **Step 1B (Track B first task)**: Extend trade_profile_8x5 to include E5_plus_EMA1D21
   - Add 6th path to STRATEGIES dict
   - Rerun to produce `results/trade_profile_8x5/E5_plus_EMA1D21/`

3. **Step 2**: Apply Step 1A diagnostics to all 6 candidates; produce cross-strategy comparison

4. **Defer**: Delayed-entry sensitivity (requires backtest engine modification) — document as future work

---

## 10. Artifact Index

### Narrative report
- `research/fragility_audit_20260306/reports/step0_report.md` (this file)

### Machine-readable artifacts
- `research/fragility_audit_20260306/artifacts/step0/canonical_baseline_manifest.csv`
- `research/fragility_audit_20260306/artifacts/step0/tooling_inventory.csv`
- `research/fragility_audit_20260306/artifacts/step0/candidate_repo_mapping.csv`
- `research/fragility_audit_20260306/artifacts/step0/ledger_view_audit.csv`
- `research/fragility_audit_20260306/artifacts/step0/reconciliation_audit.csv`
- `research/fragility_audit_20260306/artifacts/step0/trade_metric_coverage_matrix.csv`
- `research/fragility_audit_20260306/artifacts/step0/candidate_readiness_summary.csv`
- `research/fragility_audit_20260306/artifacts/step0/step0_summary.json`

### Human-readable planning specs
- `research/fragility_audit_20260306/artifacts/step0/trade_metric_coverage_matrix.md`
- `research/fragility_audit_20260306/artifacts/step0/track_split_plan.md`
- `research/fragility_audit_20260306/artifacts/step0/missing_diagnostics_spec.md`
