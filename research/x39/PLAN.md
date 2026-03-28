# x39 — Feature Invention Explorer & Experiment Plan

## Context

x39 started as exploration tools to find what OHLCV features existing indicators
don't capture. After incorporating gen4/gen1 research, the residual scan identified
features that predict returns INDEPENDENTLY of EMA/VDO/D1 regime.

## Key Findings (from explore.py)

| Feature | Sig horizons | Direction | Source |
|---|---|---|---|
| d1_rangevol84_rank365 | 4/5 | + all | Gen4 C1 |
| ret_168 | 4/5 | + all | Gen1 V6 |
| trendq_84 | 3/5 | + med-long | Gen1 V3 |
| rangepos_84 | 3/5 | dual | Gen4 |
| vol_per_range | 3/5 | + med-long | x39 original |
| body_consist_6 | 3/5 | dual | x39 original |
| trade_surprise_168 | 2/5 | dual | Gen4 C3 |
| d1_taker_imbal_12 | 2/5 | - med | Gen4 C2 |
| ratr_pct | 2/5 | + med | x39 original |

Loss anatomy: 0/31 features separate winners from losers at entry (all p > 0.05).

## Baseline

E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Experiments

52 experiments in 17 categories. Each is self-contained with its own spec file.
Run ONE experiment per session. Each session reads its spec, runs the test,
writes results back to the spec file.

| # | Category | Name | Spec file |
|---|----------|------|-----------|
| 01 | A-filter | D1 anti-vol gate | specs/exp01_d1_antivol_gate.md |
| 02 | A-filter | Trend quality gate | specs/exp02_trendq_gate.md |
| 03 | A-filter | Liquidity gate | specs/exp03_liquidity_gate.md |
| 04 | A-filter | Trade surprise gate | specs/exp04_trade_surprise_gate.md |
| 05 | A-filter | D1 taker exhaustion block | specs/exp05_d1_taker_block.md |
| 06 | A-filter | Body consistency block | specs/exp06_body_consist_block.md |
| 07 | B-replace | Replace EMA with ret_168 | specs/exp07_replace_ema_ret168.md |
| 08 | B-replace | Replace EMA with rangepos_168 | specs/exp08_replace_ema_rangepos.md |
| 09 | B-replace | Replace D1 EMA(21) with D1 anti-vol | specs/exp09_replace_d1regime.md |
| 10 | B-replace | Replace VDO with trade_surprise | specs/exp10_replace_vdo.md |
| 11 | C-exit | Anti-vol dynamic trail | specs/exp11_antivol_trail.md |
| 12 | C-exit | Range position exit | specs/exp12_rangepos_exit.md |
| 13 | C-exit | Trend quality exit | specs/exp13_trendq_exit.md |
| 14 | D-compare | E5 vs Gen4 C3 head-to-head | specs/exp14_vs_gen4c3.md |
| 15 | D-compare | E5 vs Gen1 V6 head-to-head | specs/exp15_vs_gen1v6.md |
| 16 | D-compare | Hybrid Gen4 entry + E5 exit | specs/exp16_hybrid_gen4_e5.md |
| 17 | E-ensemble | Vote ensemble (2/3 agree) | specs/exp17_vote_ensemble.md |
| 18 | E-ensemble | OR ensemble (any signal) | specs/exp18_or_ensemble.md |
| 19 | F-stacked  | Stacked supplementary exits | specs/exp19_stacked_exits.md |
| 20 | F-stacked  | Rangepos-adaptive trail | specs/exp20_rangepos_adaptive_trail.md |
| 21 | F-stacked  | ret_168 momentum exit | specs/exp21_ret168_momentum_exit.md |
| 22 | F-stacked  | AND-gated feature interaction exit | specs/exp22_and_gated_exit.md |
| 23 | G-robust   | Rangepos lookback robustness | specs/exp23_rangepos_lookback_robustness.md |
| 24 | F-stacked  | Volume anomaly exit | specs/exp24_volume_anomaly_exit.md |
| 25 | H-validate | AND-gate lookback robustness | specs/exp25_and_gate_lookback_robustness.md |
| 26 | H-validate | AND-gate fine grid | specs/exp26_and_gate_fine_grid.md |
| 27 | H-validate | Multi-lookback rangepos consensus | specs/exp27_multi_lookback_rangepos.md |
| 28 | I-velocity | Rangepos velocity exit | specs/exp28_rangepos_velocity_exit.md |
| 29 | I-velocity | AND-gate trail tightener | specs/exp29_and_gate_trail_tightener.md |
| 30 | H-validate | AND-gate walk-forward validation | specs/exp30_and_gate_walk_forward.md |
| 31 | H-validate | Velocity walk-forward validation | specs/exp31_velocity_walk_forward.md |
| 32 | J-entry    | Pullback-in-trend entry | specs/exp32_pullback_entry.md |
| 33 | J-entry    | Momentum acceleration gate | specs/exp33_momentum_accel_gate.md |
| 34 | J-entry    | Volatility compression entry | specs/exp34_vol_compression_entry.md |
| 35 | J-entry    | D1 EMA slope confirmation | specs/exp35_d1_ema_slope.md |
| 36 | K-regime   | Regime-split trail multiplier | specs/exp36_regime_split_trail.md |
| 37 | K-regime   | Adaptive EMA slow period | specs/exp37_adaptive_ema_period.md |
| 38 | K-regime   | Trend maturity trail decay | specs/exp38_trend_maturity_decay.md |
| 39 | K-regime   | Dual-clock EMA entry | specs/exp39_dual_clock_entry.md |
| 40 | L-wfo      | Maturity decay walk-forward | specs/exp40_maturity_decay_wfo.md |
| 41 | L-wfo      | Accel gate walk-forward | specs/exp41_accel_gate_wfo.md |
| 42 | L-wfo      | Vol compression walk-forward | specs/exp42_vol_compression_wfo.md |
| 43 | M-combo    | Accel gate + maturity decay | specs/exp43_accel_maturity_combo.md |
| 44 | M-combo    | Compression + maturity decay | specs/exp44_compression_maturity_combo.md |
| 45 | M-combo    | Triple stack (accel+comp+decay) | specs/exp45_triple_stack.md |
| 46 | N-next     | Regime-adaptive maturity decay | specs/exp46_regime_adaptive_decay.md |
| 47 | N-next     | Accel-weighted initial trail | specs/exp47_accel_weighted_trail.md |
| 48 | O-screen   | Selectivity batch screen (Cat-A features) | specs/exp48_selectivity_batch_screen.md |
| 49 | P-final    | Compression + maturity decay WFO | specs/exp49_compression_decay_wfo.md |
| 50 | P-final    | Alternative compression measures robustness | specs/exp50_alt_compression_measures.md |
| 51 | Q-newentry | Momentum persistence gate | specs/exp51_momentum_persistence_gate.md |
| 52 | P-final    | Compression at realistic costs | specs/exp52_compression_realistic_costs.md |

## How to run

Each spec file contains everything needed to execute the experiment:
- Exact feature formula
- Parameter sweep values
- Entry/exit logic changes
- Comparison metrics
- Expected output format

```
# In a new session:
# 1. Read the spec file
# 2. Write and run the experiment script
# 3. Write results back to the spec file
# 4. Update this PLAN.md with verdict
```

## Results Summary

| # | Name | Verdict | Sharpe | CAGR | MDD | Trades | Notes |
|---|------|---------|--------|------|-----|--------|-------|
| 01 | D1 anti-vol gate | — | — | — | — | — | — |
| 02 | Trend quality gate | — | — | — | — | — | — |
| 03 | Liquidity gate | — | — | — | — | — | — |
| 04 | Trade surprise gate | — | — | — | — | — | — |
| 05 | D1 taker block | — | — | — | — | — | — |
| 06 | Body consist block | — | — | — | — | — | — |
| 07 | Replace EMA→ret_168 | — | — | — | — | — | — |
| 08 | Replace EMA→rangepos | — | — | — | — | — | — |
| 09 | Replace D1 regime | — | — | — | — | — | — |
| 10 | Replace VDO→trade_surp | — | — | — | — | — | — |
| 11 | Anti-vol trail | — | — | — | — | — | — |
| 12 | Rangepos exit | — | — | — | — | — | — |
| 13 | Trendq exit | FAIL | 1.248 | 53.7% | 47.4% | 294 | Best th=-0.2: MDD -3.9pp but Sharpe -0.049. All thresholds degrade Sharpe. |
| 14 | vs Gen4 C3 | — | — | — | — | — | — |
| 15 | vs Gen1 V6 | — | — | — | — | — | — |
| 16 | Hybrid Gen4+E5 | — | — | — | — | — | — |
| 17 | Vote ensemble | — | — | — | — | — | — |
| 18 | OR ensemble | — | — | — | — | — | — |
| 19 | Stacked exits | — | — | — | — | — | — |
| 20 | Rangepos-adaptive trail | — | — | — | — | — | — |
| 21 | ret_168 momentum exit | — | — | — | — | — | — |
| 22 | AND-gated exit | — | — | — | — | — | — |
| 23 | Rangepos lookback robust | — | — | — | — | — | — |
| 24 | Volume anomaly exit | — | — | — | — | — | — |
| 25 | AND-gate lookback robust | — | — | — | — | — | — |
| 26 | AND-gate fine grid | — | — | — | — | — | — |
| 27 | Multi-lookback rangepos | — | — | — | — | — | — |
| 28 | Rangepos velocity exit | — | — | — | — | — | — |
| 29 | AND-gate trail tightener | — | — | — | — | — | — |
| 30 | AND-gate walk-forward | — | — | — | — | — | — |
| 31 | Velocity walk-forward | — | — | — | — | — | — |
| 32 | Pullback-in-trend entry | FAIL | 1.300 | 51.1 | 43.5 | 167 | MDD improves, CAGR drops all 12 configs |
| 33 | Momentum accel gate | PASS* | 1.448 | 59.7 | 41.0 | 166 | +0.15Sh -10MDD. *WFO FAIL exp41 |
| 34 | Vol compression entry | MIXED | 1.487 | 68.4 | 53.6 | 197 | +0.19Sh. Selective. **WFO PASS exp42** |
| 35 | D1 EMA slope | MARGINAL | 1.346 | 54.4 | 40.3 | 189 | +0.036Sh. Not actionable |
| 36 | Regime-split trail | MARGINAL | 1.316 | 57.6 | 47.0 | 274 | +0.026Sh. Only 1/12 passes |
| 37 | Adaptive EMA period | FAIL | 1.309 | 51.9 | 37.6 | 189 | All 6 lose Sharpe |
| 38 | Trend maturity decay | PASS | +0.150 | +5.41 | -9.82 | 263 | min=1.5/start=60/end=180 |
| 39 | Dual-clock entry | FAIL | 1.295 | 57.0 | 51.3 | 214 | No improvement. ρ=0.92 too correlated |
| 40 | Maturity decay WFO | **FAIL** | — | — | — | — | 2/4 win, d_Sh=-0.16. Bear-only |
| 41 | Accel gate WFO | **FAIL** | — | — | — | — | 1/4 win, d_Sh=-0.24. Hurts everywhere |
| 42 | Vol compression WFO | **PASS** | — | — | — | — | 4/4 win, d_Sh=+0.26. SELECTIVE |
| 43 | Accel + maturity combo | MARGINAL | 1.450 | 49.8 | 37.4 | 177 | Doesn't beat exp38 alone |
| 44 | Compression + maturity | ADDITIVE | 1.543 | 60.8 | 31.5 | 240 | +0.233Sh. Ratio 0.79 |
| 45 | Triple stack | FAIL | 1.387 | 46.2 | 36.9 | 170 | Accel gate is weak link |
| 46 | Regime-adaptive decay | FAIL | — | — | — | — | 0/9 beat fixed decay |
| 47 | Accel-weighted trail | FAIL | — | — | — | — | Zero IC, all configs degrade Sharpe |
| 48 | Selectivity batch screen | **1/7 PROMOTE** | — | — | — | 221 | trendq_84 only: sel 5/5, rgm 3/4. 6 CLOSE |
| 49 | Comp + decay WFO | — | — | — | — | — | — |
| 50 | Alt compression measures | — | — | — | — | — | — |
| 51 | Momentum persistence | — | — | — | — | — | — |
| 52 | Compression costs | — | — | — | — | — | — |

## Formal Validation (2026-03-28)

Formal 5-phase validation of vol compression gate through v10 engine.
Spec: `specs/formal_validation_spec.md`. Task runner: `specs/task_d_multiple_testing_and_verdict.md`.

| Phase | Result | Key Numbers |
|-------|--------|-------------|
| 1: Implementation | COMPLETE | `vtrend_e5_ema21_d1_vc` strategy, 1284 tests pass |
| 2: Reproduction | PASS | d_Sharpe +0.1399 (x39: +0.1901, -26.4%) |
| 3: Pipeline (thr=0.6) | HOLD | Sh 1.594, G4 Wilcoxon p=0.273, 6/7 gates |
| 3: Pipeline (thr=0.7) | HOLD | Sh 1.571, G4 Wilcoxon p=0.191, 6/7 gates |
| 4: DSR (N=52) | PASS | p=1.000 (SR 1.35 >> SR₀ 0.10) |
| 4: WFO Bonferroni | FAIL | p=0.19-0.27 >> α=0.0125 |
| 5: MDD trade-off | RESOLVED | -2.46pp improvement (Issue #2 resolved) |
| **Overall** | **INCONCLUSIVE** | DSR PASS + WFO FAIL (Scenario B) |

**Recommended threshold**: 0.7 (better WFO stability, smaller worst-window loss).
**Recommended next step**: Preserve finding; deploy when WFO power problem resolved.
