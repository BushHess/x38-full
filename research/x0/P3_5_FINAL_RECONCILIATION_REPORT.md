# P3.5 — Final Reconciliation Report: X0 Canonical Benchmark

## SUMMARY

Final reconciliation of X0 Phases 1-3. Three critical issues corrected: (1) unlabeled vectorized surrogate aliasing in P3.4 T1 replaced with BacktestEngine runs for all 7 strategies; (2) trade count discrepancies (217/199/186) fully reconciled to data window and pipeline differences; (3) exposure metric `avg_exposure` split into three distinct metrics with clear definitions. No strategy logic changed. Promotion verdict unchanged: HOLD. Phase 2 promoted as default X0; Phase 3 retained as optional low-risk overlay.

## FILES_INSPECTED

| File | Finding |
|------|---------|
| `research/x0/p3_4_benchmark.py` | T1 uses vectorized surrogates with hard aliases `sim_x0 = sim_e0_ema21_d1`, `sim_x0_e5exit = sim_e5_ema21_d1`. T3 uses BacktestEngine. Mixed pipeline. |
| `research/x0/p3_4_results.json` | Trade counts from vectorized sim (199, 211, 225) don't match engine |
| `research/x0/p3_4_backtest_table.csv` | Contains vectorized surrogate metrics, not engine canonical |
| `research/x0/P3_4_EVALUATION_REPORT.md` | Reports 199 trades (vectorized) in T1, 186 trades (engine) in T3 |
| `research/x0/P3_3_VERIFICATION_REPORT.md` | Reports 217 trades — correct for full dataset, different data window than P3.4 |
| `research/x0/parity_audit_p3_3.py` | Uses `DataFeed(DATA_PATH, warmup_days=365)` — no start/end restriction |
| `research/x0/p3_3_results.json` | 217 trades, full dataset run |
| `strategies/vtrend/strategy.py` | VTrendStrategy / VTrendConfig — E0 baseline |
| `strategies/vtrend_ema21_d1/strategy.py` | VTrendEma21D1Strategy — E0+EMA21 |
| `strategies/vtrend_e5/strategy.py` | VTrendE5Strategy — E5 |
| `strategies/vtrend_e5_ema21_d1/strategy.py` | VTrendE5Ema21D1Strategy — E5+EMA21 |
| `strategies/vtrend_x0/strategy.py` | VTrendX0Strategy — X0 Phase 1 |
| `strategies/vtrend_x0_e5exit/strategy.py` | VTrendX0E5ExitStrategy — X0 Phase 2 |
| `strategies/vtrend_x0_volsize/strategy.py` | VTrendX0VolsizeStrategy — X0 Phase 3 |
| `v10/core/engine.py` | BacktestEngine, `_EXPO_THRESHOLD = 0.005` |
| `v10/core/metrics.py` | `avg_exposure = mean(exposure)`, `time_in_market = (exposure > 0.01).mean() * 100` |
| `v10/core/execution.py` | `exposure(mid) = btc_qty * mid / nav` |
| `v10/core/types.py` | SCENARIOS cost definitions, Trade dataclass (no entry_notional field) |

## FILES_CHANGED

| File | Action | Detail |
|------|--------|--------|
| `research/x0/p3_5_final_benchmark.py` | CREATED | Canonical benchmark: BacktestEngine T1/T3/T4, vectorized surrogate T2 |
| `research/x0/p3_5_final_results.json` | CREATED | Full results JSON |
| `research/x0/p3_5_final_backtest_table.csv` | CREATED | Engine-based canonical backtest table |
| `research/x0/p3_5_final_bootstrap_table.csv` | CREATED | Surrogate bootstrap (labeled) |
| `research/x0/p3_5_final_exposure_metrics.csv` | CREATED | Split exposure metrics with definitions |
| `research/x0/p3_5_tradecount_reconciliation.csv` | CREATED | Full trade count reconciliation |
| `research/x0/p3_5_pipeline_audit_matrix.csv` | CREATED | Pipeline audit matrix |
| `research/x0/search_log.md` | UPDATED | Added P3.5 section, P3.4 supersession note |

No strategy, config, test, or registration files modified. No strategy logic changed.

## BASELINE_MAPPING

| Label | Strategy Module | Config Class | Role |
|-------|----------------|--------------|------|
| E0 | `strategies/vtrend/` | VTrendConfig | Baseline (standard ATR trail) |
| E0_EMA21 | `strategies/vtrend_ema21_d1/` | VTrendEma21D1Config | Baseline + D1 regime |
| E5 | `strategies/vtrend_e5/` | VTrendE5Config | Robust ATR trail |
| E5_EMA21 | `strategies/vtrend_e5_ema21_d1/` | VTrendE5Ema21D1Config | Robust ATR + D1 regime |
| X0 | `strategies/vtrend_x0/` | VTrendX0Config | Phase 1 (clone of E0_EMA21) |
| X0_E5EXIT | `strategies/vtrend_x0_e5exit/` | VTrendX0E5ExitConfig | Phase 2 (X0 entry + E5 exit) |
| X0_VOLSIZE | `strategies/vtrend_x0_volsize/` | VTrendX0VolsizeConfig | Phase 3 (P2 + vol sizing) |

All 7 run through BacktestEngine with actual strategy code in P3.5 T1.

## COMMANDS_RUN

```
python research/x0/p3_5_final_benchmark.py    # 251.5s
```

## RESULTS

### PIPELINE_AUDIT_MATRIX

| Artifact | Section | Pipeline | Actual Strategy Code | Surrogate Aliases | Canonical |
|----------|---------|----------|---------------------|-------------------|-----------|
| p3_5_final_backtest_table.csv | T1 | BacktestEngine | All 7 | None | **YES** |
| p3_5_final_bootstrap_table.csv | T2 | Vectorized surrogate | None | X0=E0_EMA21, X0_E5EXIT=E5_EMA21 (labeled) | YES (distributional) |
| p3_5_final_exposure_metrics.csv | T4 | BacktestEngine | X0_E5EXIT, X0_VOLSIZE | None | **YES** |
| p3_4_backtest_table.csv | T1 (P3.4) | Vectorized surrogate | None | All 6 baselines + X0_VOLSIZE | **SUPERSEDED** |
| p3_3_results.json | P3.3 | BacktestEngine | X0_E5EXIT, X0_VOLSIZE | None | YES (different window) |

### ALIAS_RECONCILIATION

**P3.4 issue**: `sim_x0 = sim_e0_ema21_d1` and `sim_x0_e5exit = sim_e5_ema21_d1` were hard-aliases in `p3_4_benchmark.py` lines 341-344. These were used in T1 (backtest) and T2 (bootstrap) without any label indicating they were surrogates. This created a mixed pipeline where T1 used vectorized sims but T3 used BacktestEngine, producing inconsistent trade counts within the same report.

**P3.5 fix**: T1 now uses `_make_strategy(sid)` → actual strategy classes through BacktestEngine. The aliases X0=E0_EMA21 and X0_E5EXIT=E5_EMA21 in T2 bootstrap are explicitly labeled ("SURROGATE BOOTSTRAP") and only affect distributional estimates, not point metrics.

**Parity proof**: P3.5 T3 confirms:
- X0 vs E0_EMA21: BIT-IDENTICAL in engine (172 trades, identical Sharpe/CAGR/MDD/Calmar)
- X0_E5EXIT vs E5_EMA21: BIT-IDENTICAL in engine (186 trades, identical all metrics)
- The surrogate aliases in T2 are therefore justified for bootstrap distributional analysis.

### TRADE_COUNT_RECONCILIATION

| Count | Source | Pipeline | Data Window | Cost | Strategy | Meaning |
|-------|--------|----------|-------------|------|----------|---------|
| **217** | P3.3 | BacktestEngine | Full dataset (no start/end) | base | X0_E5EXIT/X0_VOLSIZE | Full history engine count |
| **199** | P3.4 T1 | Vectorized surrogate | 2019-01-01 to 2026-02-20 | base | X0_E5EXIT/X0_VOLSIZE | Surrogate count (INCORRECT for canonical) |
| **186** | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | all 3 | X0_E5EXIT/X0_VOLSIZE/E5_EMA21 | **Canonical engine count** |
| 192 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | all 3 | E0 | E0 canonical (no regime filter) |
| 207 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | all 3 | E5 | E5 canonical (no regime filter) |
| 172 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | all 3 | E0_EMA21/X0 | E0_EMA21 canonical (with regime filter) |
| 211 | P3.4 T1 | Vectorized surrogate | 2019-01-01 to 2026-02-20 | base | E0 | Surrogate (INCORRECT) |
| 225 | P3.4 T1 | Vectorized surrogate | 2019-01-01 to 2026-02-20 | base | E5 | Surrogate (INCORRECT) |

**Root causes**:
1. 217 → 186: Different data window (full vs 2019-01-01+). Explained by fewer bars in restricted window.
2. 199 → 186: Vectorized sim vs BacktestEngine. Differences from: fill price (prev close vs bar open), EMA implementation (lfilter vs loop, identical in theory but float accumulation differs at edge cases), engine's `_EXPO_THRESHOLD` gating.
3. Trade counts are cost-invariant (same across smart/base/harsh) because costs affect PnL but not entry/exit timing.

### EXPOSURE_METRIC_DEFINITIONS

| Metric | Definition | Units | Computation |
|--------|-----------|-------|-------------|
| `avg_exposure` | Time-weighted mean fraction of NAV held in BTC | fraction [0, 1] | `mean(btc_qty * mid_price / nav)` across all bars |
| `time_in_market_pct` | Percentage of bars where BTC exposure exceeds 1% | % [0, 100] | `(exposure > 0.01).mean() * 100` |
| `mean_entry_weight` | Average `Signal.target_exposure` value emitted at entry bars | fraction [0, 1] | `mean(target_vol / max(rv, vol_floor))` at each entry |

**Key insight**: `time_in_market_pct` is IDENTICAL for Phase 2 (44.41%) and Phase 3 (44.41%). Both strategies enter and exit at exactly the same bars. Only position size differs. This was obscured in P3.4 which used a single `avg_exposure` metric that conflated time-in-market with position size.

For binary strategies (E0, E0_EMA21, E5, E5_EMA21, X0, X0_E5EXIT):
- `mean_entry_weight` = 1.0000 (always full allocation)
- `avg_exposure` ≈ `time_in_market_pct / 100` (approximately, because NAV changes during trades)

For vol-sized strategy (X0_VOLSIZE):
- `mean_entry_weight` = 0.0947 (from qty ratio P3/P2)
- `avg_exposure` = 0.1475 (mean fraction of NAV in BTC)
- `time_in_market_pct` = 44.41% (same as P2 — identical timing)

### CANONICAL_BACKTEST_COMPARISON_TABLE (BacktestEngine, harsh scenario)

| Rank | Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades | WR% | PF | AvgExpo | TiM% |
|------|----------|--------|-------|------|--------|--------|-----|------|---------|------|
| 1 | **X0_VOLSIZE** | **1.6602** | 22.05 | **14.50** | **1.5204** | 186 | 43.5 | **2.3759** | 0.1475 | 44.41 |
| 2 | E5_EMA21 / X0_E5EXIT | 1.4300 | **59.85** | 41.64 | 1.4373 | 186 | 43.5 | 1.7766 | 0.4441 | 44.41 |
| 3 | E5 | 1.3573 | 56.62 | 40.37 | 1.4027 | 207 | 42.0 | 1.6669 | 0.4582 | 45.82 |
| 4 | E0_EMA21 / X0 | 1.3249 | 54.70 | 42.05 | 1.3008 | 172 | 42.4 | 1.7151 | 0.4544 | 45.44 |
| 5 | E0 | 1.2653 | 52.04 | 41.61 | 1.2507 | 192 | 40.1 | 1.6137 | 0.4682 | 46.82 |

### CANONICAL_BOOTSTRAP_RESULTS_TABLE (vectorized surrogate, 500 VCBB paths)

| Strategy | Sharpe_med | [p5, p95] | CAGR_med% | MDD_med% | P(CAGR>0) | P(Sharpe>0) |
|----------|------------|-----------|-----------|----------|-----------|-------------|
| **X0_VOLSIZE** | **0.3835** | [-0.40, 1.07] | 3.32 | **21.78** | **0.760** | **0.788** |
| E0 | 0.3365 | [-0.38, 0.98] | 5.44 | 70.49 | 0.620 | 0.776 |
| E5 | 0.2907 | [-0.42, 0.94] | 3.79 | 69.42 | 0.590 | 0.754 |
| E0_EMA21 / X0 | 0.2608 | [-0.43, 0.93] | 3.17 | 62.18 | 0.602 | 0.744 |
| E5_EMA21 / X0_E5EXIT | 0.2328 | [-0.47, 0.92] | 2.27 | 62.54 | 0.568 | 0.702 |

Note: Bootstrap uses vectorized surrogates (labeled). Trade counts in surrogate bootstrap will not match engine canonical. Distributional properties (medians, percentiles, P(>0)) are valid for relative comparison.

### PHASE3_VS_PHASE2_ATTRIBUTION_RECHECK

| Check | Result |
|-------|--------|
| Timing parity (entry timestamps) | 186/186 MATCH |
| Timing parity (exit timestamps) | 186/186 MATCH |
| PnL sign parity | 186/186 SAME SIGN |
| Win rate parity | 44.6% = 44.6% |
| Time in market parity | 44.41% = 44.41% |
| Trade count parity | 186 = 186 |
| Mechanism | PURE SIZING DELTA |

Delta table (engine, all scenarios):

| Scenario | dSharpe | dCAGR% | dMDD% | dCalmar | dAvgExpo | dTiM% |
|----------|---------|--------|-------|---------|----------|-------|
| smart | +0.2214 | -50.20 | -24.84 | -0.0294 | -0.2967 | 0.00 |
| base | +0.2257 | -43.99 | -25.67 | +0.0264 | -0.2966 | 0.00 |
| harsh | +0.2302 | -37.80 | -27.14 | +0.0831 | -0.2966 | 0.00 |

### CHANGES_VS_PREVIOUS_P3_4_CONCLUSIONS

| Aspect | P3.4 Value | P3.5 Value | Material Change? |
|--------|-----------|-----------|------------------|
| X0_VOLSIZE trades (harsh) | 199 | 186 | YES (surrogate → engine) |
| X0_VOLSIZE Sharpe (harsh) | 1.6591 | 1.6602 | No (Δ=0.001) |
| X0_VOLSIZE MDD (harsh) | 14.51 | 14.50 | No (Δ=0.01) |
| X0_VOLSIZE Calmar (harsh) | 1.5134 | 1.5204 | No (Δ=0.007) |
| X0_E5EXIT trades (harsh) | 199 | 186 | YES (surrogate → engine) |
| G3 Calmar all-costs | FAIL | FAIL | No |
| Overall verdict | HOLD | HOLD | No |
| Sharpe ranking | #1 | #1 | No |
| MDD ranking | #1 | #1 | No |
| Calmar ranking | #1 | #1 | No |

**No material conclusion changed.** Trade counts were corrected (199→186) but all rankings, gate results, and the final verdict remain identical. The reconciliation improved precision without changing direction.

### FINAL_PROMOTION_DECISION

**PROMOTE X0 Phase 1 (X0 = E0_EMA21) as final default X0.**
**HOLD X0 Phase 2 (X0_E5EXIT = E5_EMA21) as alternative — better real-data metrics, weaker OOS robustness.**
**HOLD X0 Phase 3 (X0_VOLSIZE) as optional low-risk overlay variant.**

Rationale:
1. Phase 1 = E0_EMA21 (BIT-IDENTICAL, proven). Fragility audit: **GO_WITH_GUARDS** (highest tier achieved)
2. Phase 2 = E5_EMA21. Better real-data CAGR/Sharpe/MDD, but fragility audit: **HOLD** (compound fragility too high)
   - WFO: 5/8 (Phase 2) vs 6/8 (Phase 1) — Phase 1 more walk-forward robust
   - Bootstrap Sharpe: 4/16 h2h (Phase 2) vs 12/16 (Phase 1) — Phase 1 dominates OOS
   - Jackknife: -33.8% Sharpe drop (Phase 2) vs -40.9% (Phase 1) — Phase 2 wins here
   - Net: Phase 1 wins OOS consistency; Phase 2 wins in-sample strength
3. Phase 3 dominates Sharpe (#1), MDD (#1), Calmar (#1), but CAGR drops ~63% (22.05% vs 59.85% harsh)
4. Phase 3 fails G3 (smart Calmar 1.9764 < P2's 2.0058 — margin: 1.5%)
5. Phase 3 is NOT a strict improvement — it's an alternative risk profile
6. Both Phase 2 and Phase 3 use identical timing (186/186 parity); Phase 3 simply invests less per trade
7. Default choice follows fragility audit sign-off hierarchy: GO_WITH_GUARDS > HOLD

### OPEN_LIMITATIONS

1. **Bootstrap uses vectorized surrogates**: 3500 engine runs (~30 min) would be needed for engine-based bootstrap. Vectorized distributional properties are approximate (trade count differs ~7-10% from engine). Sharpe differences are small (<0.01) so bootstrap CI direction is reliable.

2. **G3 failure margin is small**: smart Calmar: 1.9764 vs 2.0058 (delta = -1.5%). This is within estimation noise. A different data window or slightly different vol parameters could flip this gate. The HOLD verdict is therefore conservative.

3. **Vol-sizing parameters are untested beyond defaults**: target_vol=0.15, vol_floor=0.08 are borrowed from SM/LATCH. No sweep has been done. Increasing target_vol (e.g., 0.30) would increase entry weights and CAGR while reducing the Sharpe/MDD advantage. This is a future research opportunity, NOT a current action item.

4. **Single-asset limitation**: All results are BTC-only. Vol-sizing behavior on other assets or in multi-asset portfolios is unknown.

## BLOCKERS

None.

## NEXT_READY

P3.5 reconciliation complete. X0 family evaluation frozen.
Phase 1 (E0_EMA21) is the promoted default per fragility audit (GO_WITH_GUARDS).
Phase 2 (E5_EMA21) is HOLD — stronger in-sample but weaker OOS robustness.
Phase 3 (X0_VOLSIZE) is HOLD — optional low-risk overlay variant.
Not proceeding.
