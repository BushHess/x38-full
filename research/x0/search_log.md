# X0 Research Search Log

## P1.2 — Phase 1 Core Anchor Implementation (2026-03-06)

### Decision: Strategy Identity
- Strategy name: `vtrend_x0`
- Config class: `VTrendX0Config`
- Strategy class: `VTrendX0Strategy`
- STRATEGY_ID: `"vtrend_x0"`
- Signal reasons: `x0_entry`, `x0_trail_stop`, `x0_trend_exit`

### Decision: Behavioral Clone of E0+EMA21(D1)
- X0 Phase 1 is behaviorally identical to `vtrend_ema21_d1` (E0+EMA21)
- Same indicator logic: `_ema`, `_atr`, `_vdo` — duplicated from E0+EMA21 to avoid coupling
- Same D1 regime mapping logic: uses completed D1 bars only (no lookahead)
- Same entry/exit logic: EMA crossover + VDO + D1 regime for entry; trail stop OR trend reversal for exit

### Decision: No Shared Helper Reuse
- Indicator functions (_ema, _atr, _vdo) are duplicated per strategy module in this repo
- This is the established convention (vtrend, vtrend_ema21_d1, vtrend_e5, etc. all have their own copies)
- Rationale: each strategy is a frozen research artifact; coupling would break baselines

### Default Parameters
| Parameter | Value | Source |
|-----------|-------|--------|
| slow_period | 120.0 | E0+EMA21 default |
| trail_mult | 3.0 | E0+EMA21 default |
| vdo_threshold | 0.0 | E0+EMA21 default |
| d1_ema_period | 21 | E0+EMA21 default |
| atr_period | 14 | Structural (Wilder) |
| vdo_fast | 12 | Structural |
| vdo_slow | 28 | Structural |
| fast_period | max(5, slow_period // 4) = 30 | Derived, not stored |

### Constraints Applied (per spec)
- No regime-based exit
- No cooldown
- No fractional sizing (target_exposure = 1.0 or 0.0)
- No conviction scaling
- No shock filter
- No trend_score threshold
- No VDO z-score
- No fallback logic beyond E0 family

### Registration Points
- `v10/core/config.py`: _VTREND_X0_FIELDS, _KNOWN_STRATEGIES, validation block
- `validation/strategy_factory.py`: STRATEGY_REGISTRY entry
- `v10/cli/backtest.py`: STRATEGY_REGISTRY entry
- `v10/research/candidates.py`: _VTREND_X0_FIELDS, load_candidates, build_strategy
- `v10/cli/paper.py`: NOT registered (consistent with other research strategies)

### Tests Added (17 total)
- TestD1RegimeNoLookahead: 3 tests (completed D1 only, no D1 → all False, future D1 invisible)
- TestConfigLoad: 5 tests (YAML load, defaults, strategy_id, subclass, field count)
- TestSmokeSignals: 6 tests (entry, exit, no regime → no entry, reason prefix, empty bars, no init)
- TestRegistration: 3 tests (strategy_factory, config, cli_backtest)

### Variants Tried: None
- This is Phase 1 core anchor — no parameter exploration yet

### P1.2 Validation (re-verified 2026-03-06)
- Normalized diff (X0 vs E0+EMA21 with names substituted): ONLY docstring/comment differences
- All logic paths identical: entry, exit, D1 regime mapping, indicators
- 17/17 X0 tests PASS
- 855/855 full suite PASS (39 pre-existing warnings)
- No baseline files modified

## P1.3 — Parity Audit (2026-03-06)

### Scope
- Data: `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (18,662 H4 bars, 3,110 D1 bars)
- Cost: base scenario, $10k initial, no_trade warmup
- Debug window: first 500 bars (signal-by-signal)
- Full window: all 18,662 bars (trade-by-trade, metrics)

### Results: BIT-IDENTICAL
- **Indicators**: ema_fast, ema_slow, atr, vdo, d1_regime_ok — all 18,662 values identical
- **Signals**: 0 differences in 500-bar debug window
- **Trades**: 201/201 trades, all bit-identical (entry_ts, exit_ts, entry_px, exit_px, qty, pnl)
- **Fills**: 402/402 fills matched
- **Equity**: max NAV diff = 0.0000000000
- **Metrics**: all 15 metrics identical (CAGR 56.51%, Sharpe 1.27, MDD 54.63%, 201 trades)

### Verdict
Phase 1 is parity-clean against vtrend_ema21_d1 within tested scope.

### Script
- `research/x0/parity_audit_p1_3.py`

## P1.4 — Full Benchmark + Bootstrap (2026-03-06)

### Pipeline
- Canonical `parity_eval.py` pattern: vectorized sims, lfilter indicators, same `_metrics()`
- Script: `research/x0/p1_4_benchmark.py`

### Configuration
- Data: 2019-01-01 to 2026-02-20, warmup 365d, reporting from bar 2190
- 17,838 H4 bars total, 15,648 reporting
- Cost: smart (13 bps), base (31 bps), harsh (50 bps) per side
- Bootstrap: VCBB, 500 paths, block=60, seed=42, shared paths
- Slow=120, trail=3.0, vdo_thr=0.0, d1_ema=21

### Backtest Results (harsh scenario)
| Strategy | Sharpe | CAGR% | MDD% | Trades |
|----------|--------|-------|------|--------|
| E5_EMA21 | 1.432 | 59.96 | 41.57 | 199 |
| E5 | 1.365 | 57.04 | 40.26 | 225 |
| E0_EMA21 | 1.336 | 55.32 | 41.99 | 186 |
| X0 | 1.336 | 55.32 | 41.99 | 186 |
| E0 | 1.277 | 52.68 | 41.53 | 211 |

### Bootstrap Results (VCBB, 500 paths)
| Strategy | Sharpe med | CAGR med | MDD med | P(CAGR>0) |
|----------|-----------|----------|---------|-----------|
| E0 | 0.337 | 5.44% | 70.49% | 0.620 |
| E5 | 0.291 | 3.79% | 69.42% | 0.590 |
| E0_EMA21 | 0.261 | 3.17% | 62.18% | 0.602 |
| X0 | 0.261 | 3.17% | 62.18% | 0.602 |
| E5_EMA21 | 0.233 | 2.27% | 62.54% | 0.568 |

### Parity Verification
- X0 vs E0_EMA21 backtest: BIT-IDENTICAL (all 3 scenarios)
- X0 vs E0_EMA21 bootstrap: BIT-IDENTICAL (all 12 statistics)

### Outputs
- `research/x0/p1_4_results.json` — full results payload
- `research/x0/p1_4_backtest_table.csv` — backtest comparison
- `research/x0/p1_4_bootstrap_table.csv` — bootstrap comparison
- `research/x0/phase1_evaluation.md` — full report

## P2.1 — Audit E5 Exit Logic & Freeze Phase 2 Design (2026-03-06)

### Phase 2 Objective
Transplant E5-style robust ATR trail into X0 while preserving X0 Phase 1 entry stack.
Single hypothesis: does robust ATR trail improve X0's exit quality?

### Audited Files
- `strategies/vtrend_x0/strategy.py` (X0 Phase 1 — standard ATR trail)
- `strategies/vtrend_e5/strategy.py` (E5 — robust ATR trail, no D1 regime)
- `strategies/vtrend_e5_ema21_d1/strategy.py` (E5+EMA21 — robust ATR trail + D1 regime)

### Transplant Analysis: CLEAN
The E5 exit differs from E0/X0 in exactly ONE indicator: `_robust_atr` replaces `_atr`.
- `_robust_atr` is self-contained: inputs are (high, low, close), no side effects
- Trail stop formula is identical: `peak - trail_mult * atr_val`
- State variables identical: `_in_position`, `_peak_price`
- No entry-side coupling: robust ATR is only used in the exit path
- NaN guard changes: `ratr_val` instead of `atr_val`, but functional form same

### What Gets Ported (from E5)
1. `_robust_atr(high, low, close, cap_q, cap_lb, period)` function
2. 3 config fields: `ratr_cap_q=0.90`, `ratr_cap_lb=100`, `ratr_period=20`
3. `self._ratr` computation in `on_init`
4. Trail stop uses `self._ratr[i]` instead of `self._atr[i]`
5. NaN guard uses `ratr_val` instead of `atr_val`

### What Does NOT Change
- Entry: EMA crossover + VDO + D1 regime (identical to Phase 1)
- D1 regime mapping (identical)
- EMA/VDO indicators (identical)
- State variables (identical)
- Trend exit (ema_f < ema_s — identical)
- No cooldown, no fractional, no conviction, no shock, no regime exit

### Frozen Scope
- X0 Phase 2 = E5+EMA21 behavioral clone (expected parity target)
- If parity confirmed, X0 Phase 2 absorbs the robust ATR improvement
- Standard `_atr` may be dropped or kept for reference

### Excluded from Phase 2
- Parameter exploration on ratr_cap_q / ratr_cap_lb / ratr_period
- Any entry modifications
- VDO z-score, trend_score, conviction scaling
- Fractional sizing, cooldown, shock filter

## P2.2 — Phase 2 Implementation: X0 Entry + E5 Robust ATR Exit (2026-03-06)

### Decision: Separate Module (not in-place modification)
- Created NEW module `strategies/vtrend_x0_e5exit/` instead of modifying Phase 1
- Rationale: Phase 1 (`vtrend_x0`) is the anchor baseline; modifying it would lose the comparison target
- Strategy name: `vtrend_x0_e5exit`
- Config class: `VTrendX0E5ExitConfig`
- Strategy class: `VTrendX0E5ExitStrategy`
- STRATEGY_ID: `"vtrend_x0_e5exit"`
- Signal reasons: `x0_entry`, `x0_trail_stop`, `x0_trend_exit` (unchanged from Phase 1)

### Ported from E5 (exit side only)
1. `_robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20)` — full function
2. 3 new config fields: `ratr_cap_q`, `ratr_cap_lb`, `ratr_period`
3. `self._ratr` replaces `self._atr` in `on_init`
4. Trail stop uses `self._ratr[i]` instead of `self._atr[i]`
5. NaN guard checks `ratr_val` instead of `atr_val`

### Frozen from X0 Phase 1 (entry side)
- `_ema`, `_vdo` indicator functions (identical)
- `_compute_d1_regime` (identical)
- Entry logic: EMA crossover + VDO > threshold + D1 regime (identical)
- Trend exit: `ema_f < ema_s` (identical)
- State variables: `_in_position`, `_peak_price` (identical)

### Config (10 fields total = 7 from Phase 1 + 3 from E5)
| Parameter | Value | Source |
|-----------|-------|--------|
| slow_period | 120.0 | Phase 1 |
| trail_mult | 3.0 | Phase 1 |
| vdo_threshold | 0.0 | Phase 1 |
| d1_ema_period | 21 | Phase 1 |
| atr_period | 14 | Phase 1 (kept for reference, not used in trail) |
| vdo_fast | 12 | Phase 1 |
| vdo_slow | 28 | Phase 1 |
| ratr_cap_q | 0.90 | E5 |
| ratr_cap_lb | 100 | E5 |
| ratr_period | 20 | E5 |

### Registration Points (same 4 as Phase 1)
- `v10/core/config.py`: _VTREND_X0_E5EXIT_FIELDS, _KNOWN_STRATEGIES, validation
- `validation/strategy_factory.py`: STRATEGY_REGISTRY
- `v10/cli/backtest.py`: STRATEGY_REGISTRY
- `v10/research/candidates.py`: fields, load_candidates, build_strategy

### Tests Added (17 total)
- TestD1RegimeNoLookahead: 2 tests
- TestConfigLoad: 5 tests (includes 3 ratr params, field_count=10)
- TestEntryParity: 3 tests
- TestRobustATRExit: 4 tests (robust_atr output, _ratr not _atr, exit after crash, empty bars)
- TestRegistration: 3 tests

### Validation
- Phase 2 tests: 17/17 PASS
- Full suite: 872/872 PASS (39 pre-existing warnings)
- Zero baseline files modified
- Zero deviations from P2.1 frozen spec

## P2.3 — Phase 2 Verification & Differential Audit (2026-03-06)

### Layer A: Raw Entry Parity
- 7 entry-side indicators compared (standalone + strategy-level): ALL BIT-IDENTICAL
- ema_fast, ema_slow, vdo, d1_regime_ok: 18,662 values each, zero diffs
- ATR vs rATR: CONFIRMED DIFFERENT (max_diff=1321.43, mean_diff=60.30, 0 identical)
- Verdict: **Raw entry logic is parity-clean against X0 Phase 1**

### Layer B: Executed Strategy Delta
- Debug window (500 bars): 14 signal differences — all caused by different ATR exit timing
  - First diff at bar 87: P1 enters (ATR valid), P2 skips (rATR still NaN at bar 87 < 119)
  - Cascade: different exit timing → different re-entry timing → state divergence
- Full backtest: P1=201 trades, P2=217 trades (+16)
- Metrics delta (P2 - P1): Sharpe +0.152, CAGR +8.74%, MDD -8.55%, trades +16

### Layer C: Exit-Focused Delta (matched entries)
- 180 trades share same entry timestamp
- 106/180 (58.9%) have identical exit timestamp
- 74/180 (41.1%) differ on exit timing
- Hold period delta: mean -41.9h, median -12.0h (P2 exits faster on average)
- Return delta: mean -0.42%, median +0.49%
- Exit reasons: 73/74 P1 diffs = trail_stop, 74/74 P2 diffs = trail_stop
- 21 P1-only entries, 37 P2-only entries (cascade from different exit timing)

### E5 Exit Transplant Validation
- `_robust_atr` function output: BIT-IDENTICAL (18,543 valid values)
- All 5 strategy indicators: BIT-IDENTICAL vs E5+EMA21
- Trade-level: 217/217 trades BIT-IDENTICAL vs E5+EMA21
- Metrics: Sharpe, CAGR, MDD, trades — ALL MATCH
- Verdict: **X0 Phase 2 is parity-clean against E5+EMA21**

### No Bugs Found
- Zero code changes needed
- Zero deviations from spec

### Script & Outputs
- `research/x0/parity_audit_p2_3.py`
- `research/x0/p2_3_results.json`

## P2.4 — Full Benchmark + Bootstrap + Attribution (2026-03-06)

### Evaluation Pipeline
- Script: `research/x0/p2_4_benchmark.py` — extends P1.4 canonical pattern
- Identical to P1.4: data, warmup, cost scenarios, VCBB seed, block size, bootstrap count
- Added: X0_E5EXIT (6th strategy), attribution analysis (T3)

### Configuration (identical to P1.4)
- Data: 2019-01-01 to 2026-02-20, warmup 365d, reporting from bar 2190
- 17,838 H4 bars, 2,973 D1 bars
- Cost: smart (13 bps), base (31 bps), harsh (50 bps) per side
- Bootstrap: VCBB, 500 paths, block=60, seed=42
- Params: slow=120, trail=3.0, vdo_thr=0.0, d1_ema=21

### Parity Verification
- X0 vs E0_EMA21: BIT-IDENTICAL (3/3 scenarios + bootstrap)
- X0_E5EXIT vs E5_EMA21: BIT-IDENTICAL (3/3 scenarios + bootstrap)

### Backtest Rankings (harsh scenario)
| Rank | Strategy | Sharpe | CAGR% | MDD% |
|------|----------|--------|-------|------|
| 1 | E5_EMA21 / X0_E5EXIT | 1.432 | 59.96 | 41.57 |
| 2 | E5 | 1.365 | 57.04 | 40.26 |
| 3 | E0_EMA21 / X0 | 1.336 | 55.32 | 41.99 |
| 4 | E0 | 1.277 | 52.68 | 41.53 |

### Phase 2 Delta (P2 - P1, vectorized sim, all scenarios positive)
| Scenario | dSharpe | dCAGR% | dMDD% | dTrades |
|----------|---------|--------|-------|---------|
| smart | +0.120 | +6.33 | -1.55 | +13 |
| base | +0.108 | +5.47 | -1.40 | +13 |
| harsh | +0.096 | +4.64 | -0.42 | +13 |

### Attribution (base scenario)
- 157 matched entries, 95 same exit, 62 differ
- Improved: 73, Worsened: 81 (by trade count)
- Mean PnL delta: +$337 (positive from large wins offsetting many small losses)
- Total matched PnL delta: +$52,933
- Top 3 contribution: 29.2% of total — moderately concentrated
- P2-only trades: +$43,411 (29 trades), P1-only: -$4,086 (15 trades)
- Primary mechanism: robust ATR exits faster (56/157 shorter), cuts losers better
- Uplift is broad-based: both matched trades AND unmatched trade timing benefit

### Bootstrap Results
| Strategy | Sharpe med [5,95] | CAGR med [5,95] | MDD med [5,95] | P(CAGR>0) |
|----------|-------------------|------------------|----------------|-----------|
| E0 | 0.337 [-0.38, 0.98] | 5.44 [-19.87, 38.44] | 70.49 [49.21, 89.40] | 0.620 |
| E0_EMA21 / X0 | 0.261 [-0.43, 0.93] | 3.17 [-16.30, 31.27] | 62.18 [43.14, 84.90] | 0.602 |
| E5 | 0.291 [-0.42, 0.94] | 3.79 [-20.40, 36.12] | 69.42 [49.03, 89.38] | 0.590 |
| E5_EMA21 / X0_E5EXIT | 0.233 [-0.47, 0.92] | 2.27 [-17.87, 30.96] | 62.54 [42.97, 85.84] | 0.568 |

### Script & Outputs
- `research/x0/p2_4_benchmark.py`
- `research/x0/p2_4_results.json`
- `research/x0/p2_4_backtest_table.csv`
- `research/x0/p2_4_bootstrap_table.csv`
- `research/x0/p2_4_delta_table.csv`

## P3.0 — Reconcile Phase 2 Reporting Discrepancy (2026-03-06)

### Discrepancy 1: p_sharpe_gt0 in phase2_evaluation.md
- **Found**: Bootstrap table P(Sharpe>0) values were wrong
- **Markdown had**: E0=0.632, E0_EMA21=0.612, E5=0.606, E5_EMA21=0.580
- **Correct (JSON+CSV)**: E0=0.776, E0_EMA21=0.744, E5=0.754, E5_EMA21=0.702
- **Root cause**: Values were hallucinated during markdown report generation (not copied from JSON)
- **Source of truth**: `p2_4_results.json` (computed by `p2_4_benchmark.py`)
- **Fix**: Replaced all 4 values in phase2_evaluation.md

### Discrepancy 2: Delta table mixed pipelines
- **Found**: PHASE2_DELTA_TABLE showed absolute values from vectorized sim but deltas from BacktestEngine
- **Vectorized deltas**: smart dSharpe=+0.120, base=+0.108, harsh=+0.096, dTrades=+13
- **Engine deltas**: smart dSharpe=+0.129, base=+0.117, harsh=+0.105, dTrades=+14
- **Root cause**: T1 (backtest) uses vectorized sim; T3 (attribution) uses BacktestEngine for Trade objects. Different warmup handling → different trade counts (186/199 vs 172/186)
- **Fix**: Replaced deltas with vectorized-derived values (consistent with absolute values shown). Added footnote explaining two pipelines and that `p2_4_delta_table.csv` contains engine-based deltas. Updated search_log.md delta table.

### Impact on Phase 2 Conclusions
- **None**: All conclusions remain valid. Directional uplift confirmed by both pipelines. Magnitude slightly smaller with vectorized deltas but still positive across all metrics and cost levels.

### Source of Truth Going Forward
- `p2_4_results.json`: authoritative for all computed values
- `p2_4_backtest_table.csv` / `p2_4_bootstrap_table.csv`: derived from JSON, consistent
- `p2_4_delta_table.csv`: BacktestEngine-based (valid for attribution, not for vectorized comparison)
- `phase2_evaluation.md`: now corrected and internally consistent

## P3.1 — Audit Sizing Primitive & Freeze Phase 3 Spec (2026-03-06)

### Phase Objective
Audit repo for sizing primitives, freeze minimal spec for X0 Phase 3:
volatility-targeted position sizing, frozen at entry, no rebalance.

### Audited Files (sizing primitives)
| File | Primitive | Default Params |
|------|-----------|---------------|
| `strategies/vtrend_sm/strategy.py` | `_realized_vol` + `target_vol/max(rv, EPS)` | target_vol=0.15, vol_lookback=120 |
| `strategies/latch/strategy.py` | `_realized_vol` + `target_vol/max(rv, vol_floor, EPS)` | target_vol=0.12, vol_lookback=120, vol_floor=0.08 |
| `research/position_sizing.py` | `compute_rolling_vol` + `min(1, vol_target/rv)` | vol_target=[0.10-0.50], vol_win=60 |
| `research/signal_vs_sizing.py` | Same as position_sizing.py | vol_target=0.15 |
| `research/regime_sizing.py` | Same pattern | — |

### Audited Files (engine fractional support)
| File | Finding |
|------|---------|
| `v10/core/types.py` | `Signal(target_exposure=float)` supports 0.0-1.0 |
| `v10/core/engine.py` | `_apply_target_exposure` handles fractional natively, EXPO_THRESHOLD=0.005 |
| `v10/core/execution.py` | `Portfolio.buy/sell` work with any qty, fees correct |
| `strategies/vtrend_sm/strategy.py` | Successfully uses fractional signals (proven) |
| `strategies/latch/strategy.py` | Successfully uses fractional signals (proven) |

### Audited Files (X0 Phase 2 current sizing)
| File | Finding |
|------|---------|
| `strategies/vtrend_x0_e5exit/strategy.py` L169 | `target_exposure=1.0` (hardcoded full allocation) |
| `strategies/vtrend_x0_e5exit/strategy.py` L178,183 | `target_exposure=0.0` (full exit) |

### Chosen Sizing Primitive
**SM/LATCH `_realized_vol`** + LATCH's `vol_floor` safety net.

Formula: `weight = target_vol / max(realized_vol, vol_floor)`, clipped to [0, 1].

Reasons for choice:
1. `_realized_vol` is identical in SM and LATCH — proven, tested, canonical
2. LATCH's `vol_floor` prevents degenerate weights in low-vol (structural safety)
3. `target_vol=0.15` matches SM default AND MEMORY.md "vol-target 15%"
4. `vol_lookback=120` = slow_period (SM convention, same timescale as trend signal)
5. position_sizing.py validates the formula works but uses VOL_WIN=60 (noisier)
6. SM/LATCH's `_realized_vol` is loop-based (matches strategy-module pattern for `on_init`)

### Excluded Alternatives
- `compute_rolling_vol` from position_sizing.py: vectorized (faster), but different interface than strategy pattern; vol_win=60 is noisier than 120. May use in benchmark sim for speed.
- Kelly fraction (position_sizing.py): empirical_kelly=2.0, too aggressive, requires per-trade stats
- Fixed fraction (position_sizing.py): doesn't adapt to vol, ignores the hypothesis
- SM rebalance logic: explicitly excluded per spec (no intratrade rebalance)
- LATCH VDO overlay: explicitly excluded per spec (no conviction scaling)

### Frozen Scope
- Entry timing: IDENTICAL to Phase 2
- Exit timing: IDENTICAL to Phase 2
- Entry size: `target_vol / max(rv, vol_floor)`, frozen at entry bar close
- No rebalance. No partial exit. No regime-dependent sizing.
- New config fields: 3 (target_vol, vol_lookback, vol_floor)
- New indicator: 1 (_realized_vol precomputed in on_init)

### Frozen Defaults
| Parameter | Value | Source |
|-----------|-------|--------|
| target_vol | 0.15 | SM default, MEMORY.md "vol-target 15%" |
| vol_lookback | 120 | SM convention (= slow_period) |
| vol_floor | 0.08 | LATCH default (structural safety) |

### File Plan
| File | Action |
|------|--------|
| `strategies/vtrend_x0_volsize/__init__.py` | CREATE (empty) |
| `strategies/vtrend_x0_volsize/strategy.py` | CREATE (~280 lines) |
| `configs/vtrend_x0_volsize/vtrend_x0_volsize_default.yaml` | CREATE |
| `tests/test_vtrend_x0_volsize.py` | CREATE (~250 lines) |
| `v10/core/config.py` | EDIT (registration) |
| `validation/strategy_factory.py` | EDIT (registration) |
| `v10/cli/backtest.py` | EDIT (registration) |
| `v10/research/candidates.py` | EDIT (registration) |

### Acceptance Criteria
1. Entry timestamps IDENTICAL to Phase 2 (same bar indices)
2. Exit timestamps IDENTICAL to Phase 2 (same bar indices)
3. Trade count IDENTICAL to Phase 2
4. PnL differences solely from position size (weight < 1.0)
5. No intratrade signals (entry → exit, no signals in between)
6. If rv is NaN at any entry bar during reporting period → BLOCKER

## P3.2 — Phase 3 Implementation: X0 Phase 2 + Frozen Vol Sizing (2026-03-06)

### Decision: Separate Module
- Created NEW module `strategies/vtrend_x0_volsize/` (not modifying Phase 2)
- Strategy name: `vtrend_x0_volsize`
- Config class: `VTrendX0VolsizeConfig`
- Strategy class: `VTrendX0VolsizeStrategy`
- STRATEGY_ID: `"vtrend_x0_volsize"`
- Signal reasons: `x0_entry`, `x0_trail_stop`, `x0_trend_exit` (unchanged)

### Ported from SM/LATCH (sizing only)
1. `_realized_vol(close, lookback, bars_per_year)` — from SM, identical formula
2. 3 new config fields: `target_vol=0.15`, `vol_lookback=120`, `vol_floor=0.08`
3. `self._rv` indicator computed in `on_init`
4. Entry weight: `target_vol / max(rv, vol_floor)`, clipped [0, 1]
5. rv NaN fallback: weight = 1.0 (Phase 2 behavior preserved)

### Frozen from X0 Phase 2 (everything except entry size)
- `_ema`, `_robust_atr`, `_vdo` indicator functions (identical)
- `_compute_d1_regime` (identical)
- Entry timing: EMA crossover + VDO > threshold + D1 regime (identical conditions)
- Exit timing: robust-ATR trail stop OR trend reversal (identical)
- State variables: `_in_position`, `_peak_price` (identical)
- No rebalance: weight frozen from entry to exit

### Config (13 fields = Phase 2's 10 + 3 new)
| Parameter | Value | Source |
|-----------|-------|--------|
| slow_period | 120.0 | Phase 2 |
| trail_mult | 3.0 | Phase 2 |
| vdo_threshold | 0.0 | Phase 2 |
| d1_ema_period | 21 | Phase 2 |
| atr_period | 14 | Phase 2 |
| vdo_fast | 12 | Phase 2 |
| vdo_slow | 28 | Phase 2 |
| ratr_cap_q | 0.90 | Phase 2 |
| ratr_cap_lb | 100 | Phase 2 |
| ratr_period | 20 | Phase 2 |
| target_vol | 0.15 | SM (NEW) |
| vol_lookback | 120 | SM (NEW) |
| vol_floor | 0.08 | LATCH (NEW) |

### Registration Points (same 4)
- `v10/core/config.py`: _VTREND_X0_VOLSIZE_FIELDS, _KNOWN_STRATEGIES, validation
- `validation/strategy_factory.py`: STRATEGY_REGISTRY
- `v10/cli/backtest.py`: STRATEGY_REGISTRY
- `v10/research/candidates.py`: fields, load_candidates, build_strategy

### Tests Added (17 total)
- TestEntryTimingParity: 1 test (entry bars identical to Phase 2)
- TestFractionalExposure: 2 tests (fractional when rv high, full when rv low)
- TestVolFloor: 2 tests (caps weight, prevents extreme)
- TestRvNaNFallback: 1 test (NaN rv → weight=1.0)
- TestNoRebalance: 1 test (no mid-trade signals)
- TestConfigLoad: 5 tests (YAML, defaults, id, subclass, field_count=13)
- TestRealizedVol: 2 tests (shape/NaN prefix, positive values)
- TestRegistration: 3 tests (factory, config, cli)

### Validation
- Phase 3 tests: 17/17 PASS
- Full suite: 889/889 PASS (40 warnings, 1 new: RuntimeWarning from log in _realized_vol — expected for bar 0)
- Zero baseline files modified
- Zero deviations from P3.1 frozen spec

## P3.3 — Verification + Timing Parity Audit (2026-03-06)

### Audit Scope
- Data: `data/bars_btcusdt_2016_now_h1_4h_1d.csv` (18,662 H4 bars, 3,110 D1 bars)
- Cost: base scenario (31 bps RT), $10k initial, warmup 365d, no_trade warmup
- Comparison: X0 Phase 2 (`vtrend_x0_e5exit`) vs X0 Phase 3 (`vtrend_x0_volsize`)
- Script: `research/x0/parity_audit_p3_3.py`

### Layer A: Raw Rule Parity
- 9 indicator comparisons (standalone + strategy-level): ALL BIT-IDENTICAL
  - ema_fast, ema_slow, vdo, ratr (4 standalone): 18,662 values each, zero diffs
  - ema_fast, ema_slow, ratr, vdo, d1_regime_ok (5 strategy): 18,662 values each, zero diffs
- New indicator `realized_vol`: 18,542 valid values (120 NaN prefix), min=0.141, median=0.551, max=2.051
- **RAW ENTRY PARITY: CLEAN**
- **RAW EXIT PARITY: CLEAN**

### Layer B: Trade Timestamp Parity
- Debug window (500 bars): 0 timing diffs, 4 exposure-only diffs (expected: entries have weight < 1.0)
- Full backtest:
  - Trade count: 217 = 217 (IDENTICAL)
  - Fill count: 434 = 434 (IDENTICAL)
  - Entry timestamp match: 217/217 (ALL MATCH)
  - Exit timestamp match: 217/217 (ALL MATCH)
  - Reason match: 217/217
- Win rate: 43.78% = 43.78% (IDENTICAL — timing determines wins/losses, not sizing)
- Avg days held: 6.1 = 6.1 (IDENTICAL)
- Time in market: 42.55% = 42.55% (IDENTICAL)
- **TRADE TIMESTAMP PARITY: CLEAN — 0 diffs**

### Layer C: Exposure Distribution
- Weight distribution (P3_qty / P2_qty proxy):
  - min=0.016, p10=0.020, median=0.042, mean=0.068, p90=0.156, max=0.419
  - At cap (w≥0.999): 0 trades (0.0%)
  - Fractional (0<w<1): 217 trades (100.0%)
- ALL 217 trades are fractional — BTC's realized vol (min 0.141) always exceeds target_vol=0.15
- Only 16/18,542 bars (0.1%) have rv < target_vol — these would clip to 1.0, but none coincide with entry signals
- rv NaN fallback: never triggered during reporting (rv valid from bar 120, first entry well after)
- PnL impact: P2 total=$765,694, P3 total=$42,431 (proportional to lower exposure)
- Avg exposure: P2=0.4255, P3=0.1347

### Layer D: Cost/Engine Audit
- Fee proportionality: 434/434 pass (fee_ratio = notional_ratio for every fill)
- Fill price match: 434/434 (ALL MATCH — same bar, same fill price regardless of qty)
- Fill timestamp match: 434/434 (ALL MATCH)
- Fill reason match: 434/434 (ALL MATCH)
- Fill side match: 434/434 (ALL MATCH)
- Total fees: P2=$111,888, P3=$3,905 (proportional to notional traded)
- **COST/ENGINE: CLEAN — no side-effects from fractional exposure**

### Metrics Delta (P3 - P2, base scenario)
| Metric | P2 (E5exit) | P3 (volsize) | Delta |
|--------|-------------|--------------|-------|
| Sharpe | 1.4221 | 1.6417 | +0.2196 |
| CAGR% | 65.25 | 20.95 | -44.30 |
| MDD% | 46.08 | 13.67 | -32.41 |
| Calmar | 1.416 | 1.533 | +0.117 |
| Trades | 217 | 217 | 0 |
| Win% | 43.78 | 43.78 | 0 |
| PF | 1.878 | 2.439 | +0.562 |
| AvgExpo | 0.4255 | 0.1347 | -0.291 |
| FeeDrag%/yr | 5.04 | 1.67 | -3.37 |

### Verdict
**Signal and trade timestamps are parity-clean against X0 Phase 2; Phase 3 changes economic exposure only.**

All 4 layers PASS. Zero bugs found. Zero code changes needed.

### Outputs
- `research/x0/parity_audit_p3_3.py`
- `research/x0/p3_3_results.json`

---

## P3.4 — Full Benchmark + Bootstrap + Risk-Overlay Attribution (2026-03-06)

### Objective
Full 7-strategy evaluation of X0 Phase 3 (vol-sized entry) against Phase 2 and all baselines. VCBB bootstrap, attribution analysis, exposure stats, vol bucket analysis, and promotion decision.

### Script
`research/x0/p3_4_benchmark.py` — extends P2.4 canonical pipeline with:
- 7th strategy X0_VOLSIZE = Phase 2 timing + `weight = target_vol / max(rv, vol_floor)`
- `_realized_vol` vectorized indicator
- T1 (backtest 3 cost scenarios) + T2 (500 VCBB bootstrap) + T3 (engine attribution P3 vs P2) + T4 (exposure + vol buckets)
- Automated 7-gate promotion decision

### Settings
Same as P2.4: START=2019-01-01, END=2026-02-20, WARMUP=365, CASH=10000, SLOW=120, TRAIL=3.0, N_BOOT=500, BLKSZ=60, SEED=42.
Phase 3 additions: target_vol=0.15, vol_lookback=120, vol_floor=0.08.

### T1 Results — Backtest (harsh scenario)

| Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades |
|----------|--------|-------|------|--------|--------|
| E0 | 1.2765 | 52.68 | 41.53 | 1.2684 | 211 |
| E0_EMA21 | 1.3360 | 55.32 | 41.99 | 1.3175 | 186 |
| E5 | 1.3647 | 57.04 | 40.26 | 1.4166 | 225 |
| E5_EMA21 | 1.4320 | 59.96 | 41.57 | 1.4422 | 199 |
| X0 | 1.3360 | 55.32 | 41.99 | 1.3175 | 186 |
| X0_E5EXIT | 1.4320 | 59.96 | 41.57 | 1.4422 | 199 |
| **X0_VOLSIZE** | **1.6591** | **21.97** | **14.51** | **1.5134** | **199** |

Rankings (harsh): Sharpe #1, MDD #1, Calmar #1, CAGR #7 (expected).

### T2 Results — Bootstrap VCBB (500 paths)

| Strategy | Sharpe_med [p5,p95] | CAGR_med% [p5,p95] | MDD_med% [p5,p95] | P(CAGR>0) |
|----------|---------------------|---------------------|---------------------|-----------|
| E0 | 0.3365 [-0.38,0.98] | 5.44 [-19.9,38.4] | 70.49 [49.2,89.4] | 0.620 |
| E0_EMA21 | 0.2608 [-0.43,0.93] | 3.17 [-16.3,31.3] | 62.18 [43.1,84.9] | 0.602 |
| E5 | 0.2907 [-0.42,0.94] | 3.79 [-20.4,36.1] | 69.42 [49.0,89.4] | 0.590 |
| E5_EMA21 | 0.2328 [-0.47,0.92] | 2.27 [-17.9,31.0] | 62.54 [43.0,85.8] | 0.568 |
| X0 | 0.2608 [-0.43,0.93] | 3.17 [-16.3,31.3] | 62.18 [43.1,84.9] | 0.602 |
| X0_E5EXIT | 0.2328 [-0.47,0.92] | 2.27 [-17.9,31.0] | 62.54 [43.0,85.8] | 0.568 |
| **X0_VOLSIZE** | **0.3835** [-0.40,1.07] | **3.32** [-3.7,11.4] | **21.78** [14.2,38.9] | **0.760** |

X0_VOLSIZE: best Sharpe median, best MDD median (21.78% vs next 62.18%), highest P(CAGR>0) (76%).

### T3 Results — Attribution (P3 vs P2)

- Timing parity: CONFIRMED (186/186 entry+exit timestamps identical)
- PnL sign parity: 186/186 same sign
- Win rate parity: 44.6% = 44.6%
- Mechanism: PURE SIZING DELTA
- PnL ratio (P3/P2): mean 0.0947, median 0.0600
- Delta table (harsh): dSharpe +0.2302, dCAGR -37.80, dMDD -27.14, dCalmar +0.0831

### T4 Results — Exposure & Vol Bucket Analysis

**Weight distribution:**
| Stat | Value |
|------|-------|
| Min | 0.0951 |
| P25 | 0.2250 |
| Median | 0.2896 |
| Mean | 0.3109 |
| P75 | 0.3834 |
| Max | 0.9055 |
| Std | 0.1223 |

**RV at entry:** min=0.166, median=0.518, max=1.577. All 199 entries have rv > target_vol. Zero entries below vol_floor.

**Vol buckets:**
| Bucket | RV range | N | Avg_Wt | P2_PnL | P3_PnL | Ratio |
|--------|----------|---|--------|--------|--------|-------|
| low | [0.00, 0.30) | 15 | 0.575 | -$12,179 | -$413 | 0.034 |
| medium | [0.30, 0.60) | 113 | 0.348 | $345,327 | $26,880 | 0.078 |
| high | [0.60, 1.00) | 60 | 0.209 | $53,060 | $10,702 | 0.202 |
| crisis | [1.00, inf) | 11 | 0.129 | $40,147 | $921 | 0.023 |

Key insight: medium-vol regime (0.30-0.60) dominates with 113/199 trades and majority of P2 PnL. Vol-sizing correctly scales down crisis exposure (weight 0.129) but also reduces profitable medium-vol exposure.

### Promotion Decision (7 gates)

| Gate | Criterion | Result |
|------|-----------|--------|
| G1 | Sharpe > P2 (all costs) | PASS |
| G2 | MDD < P2 (all costs) | PASS |
| G3 | Calmar > P2 (all costs) | **FAIL** |
| G4 | Boot P(CAGR>0) >= 0.70 | PASS (0.760) |
| G5 | Boot P(Sharpe>0) >= 0.70 | PASS (0.788) |
| G6 | Trade count = P2 | PASS |
| G7 | Boot MDD med < P2 | PASS (21.78% vs 62.54%) |

G3 failure: smart scenario Calmar 1.9639 < P2's 2.0066. Base (+0.0264) and harsh (+0.0831) pass.
Root cause: at lowest cost, P2's higher CAGR outweighs its higher MDD in Calmar ratio.

### Verdict
**HOLD** — 6/7 gates pass, G3 (Calmar all-costs) fails on smart scenario by 2.1%.

Phase 3 represents a genuine ALTERNATIVE RISK PROFILE, not a strict improvement:
- Dominant: Sharpe, MDD, bootstrap robustness
- Tradeoff: CAGR reduced ~63% (21.97% vs 59.96% harsh)
- Nature: risk-overlay (exposure averaging ~31%) on top of proven alpha

Phase 3 is NOT a Phase 2 replacement but a valid low-risk variant for allocation purposes.

### Outputs
- `research/x0/p3_4_benchmark.py`
- `research/x0/p3_4_results.json`
- `research/x0/p3_4_backtest_table.csv`
- `research/x0/p3_4_bootstrap_table.csv`
- `research/x0/p3_4_delta_table.csv`
- `research/x0/p3_4_exposure_stats.csv`
- `research/x0/p3_4_vol_buckets.csv`

**NOTE**: P3.4 results are SUPERSEDED by P3.5 below. P3.4 T1 used vectorized surrogates with unlabeled hard-aliases (X0=sim_e0_ema21_d1, X0_E5EXIT=sim_e5_ema21_d1) that produced different trade counts (199) than actual BacktestEngine runs (186).

---

## P3.5 — Final Reconciliation, Canonical Benchmark, and Promotion Decision (2026-03-06)

### Objective
Eliminate benchmark/reporting ambiguity, reconcile trade counts, split exposure metrics, establish canonical source of truth, produce final X0 decision.

### Script
`research/x0/p3_5_final_benchmark.py` — canonical benchmark using BacktestEngine for all 7 strategies (no surrogates in T1/T3/T4). Vectorized sims used ONLY for T2 bootstrap, clearly labeled.

### Inconsistencies Found and Corrected

**1. Vectorized surrogate aliasing (CORRECTED)**
P3.4 T1 used `sim_x0 = sim_e0_ema21_d1` and `sim_x0_e5exit = sim_e5_ema21_d1` as unlabeled hard-aliases. These vectorized sims use lfilter-based EMA and fill at prev close, producing different trade counts than actual BacktestEngine runs:

| Strategy | Engine trades | Vec trades | Sharpe diff |
|----------|--------------|------------|-------------|
| E0 | 192 | 211 | 0.0092 |
| E0_EMA21 | 172 | 186 | 0.0090 |
| E5 | 207 | 225 | 0.0053 |
| E5_EMA21 | 186 | 199 | 0.0002 |
| X0 | 172 | 186 | 0.0090 |
| X0_E5EXIT | 186 | 199 | 0.0002 |
| X0_VOLSIZE | 186 | 199 | 0.0025 |

Root cause: vectorized sims use close[i-1] as fill price and lfilter EMA (float accumulation differs from loop EMA). Engine uses actual bar open prices and has _EXPO_THRESHOLD gating.

P3.5 fix: T1 now uses BacktestEngine with actual strategy code for all 7 strategies. No surrogates in canonical metrics.

**2. Trade count reconciliation (RESOLVED)**

| Count | Source | Pipeline | Data window | Meaning |
|-------|--------|----------|-------------|---------|
| 217 | P3.3 | BacktestEngine | full dataset (no start/end) | Canonical count for full history |
| 199 | P3.4 T1 | vectorized surrogate | 2019-01-01 to 2026-02-20 | Surrogate count (WRONG for canonical) |
| 186 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | **Canonical count for restricted window** |
| 192 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | E0 canonical (no regime filter) |
| 207 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | E5 canonical (no regime filter) |
| 172 | P3.5 T1 | BacktestEngine | 2019-01-01 to 2026-02-20 | E0_EMA21 / X0 canonical |

All differences reconciled. 217→186 = data window. 199→186 = surrogate vs engine.

**3. Exposure metric definitions (FIXED)**

| Metric | Definition | Units | P2 value | P3 value |
|--------|-----------|-------|----------|----------|
| avg_exposure | mean(btc_value / nav) across all bars | fraction | 0.4441 | 0.1475 |
| time_in_market_pct | % of bars with exposure > 1% | % | 44.41 | 44.41 |
| mean_entry_weight | mean of target_exposure at entry | fraction | 1.0000 | 0.0947 |

Key insight: time_in_market is IDENTICAL (44.41%) for P2 and P3 — both are in the market at the same times. Only the position size differs. P3.4 incorrectly used a "time with non-zero returns" heuristic that conflated these.

### Canonical T1 Results — BacktestEngine (harsh scenario)

| Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades | WR% | PF | AvgExpo | TiM% |
|----------|--------|-------|------|--------|--------|-----|-----|---------|------|
| E0 | 1.2653 | 52.04 | 41.61 | 1.2507 | 192 | 40.1 | 1.614 | 0.4682 | 46.82 |
| E0_EMA21 | 1.3249 | 54.70 | 42.05 | 1.3008 | 172 | 42.4 | 1.715 | 0.4544 | 45.44 |
| E5 | 1.3573 | 56.62 | 40.37 | 1.4027 | 207 | 42.0 | 1.667 | 0.4582 | 45.82 |
| E5_EMA21 | 1.4300 | 59.85 | 41.64 | 1.4373 | 186 | 43.5 | 1.777 | 0.4441 | 44.41 |
| X0 | 1.3249 | 54.70 | 42.05 | 1.3008 | 172 | 42.4 | 1.715 | 0.4544 | 45.44 |
| X0_E5EXIT | 1.4300 | 59.85 | 41.64 | 1.4373 | 186 | 43.5 | 1.777 | 0.4441 | 44.41 |
| **X0_VOLSIZE** | **1.6602** | **22.05** | **14.50** | **1.5204** | **186** | 43.5 | 2.376 | 0.1475 | 44.41 |

### Canonical Parity Confirmation (engine)
- X0 vs E0_EMA21: BIT-IDENTICAL (172 trades, all metrics match)
- X0_E5EXIT vs E5_EMA21: BIT-IDENTICAL (186 trades, all metrics match)
- X0_VOLSIZE timing parity: 186/186 entry+exit timestamps identical to X0_E5EXIT

### Changes vs P3.4 Conclusions

| Metric | P3.4 (vectorized) | P3.5 (engine) | Changed? |
|--------|-------------------|---------------|----------|
| X0_VOLSIZE Sharpe (harsh) | 1.6591 | 1.6602 | Trivial (+0.001) |
| X0_VOLSIZE MDD (harsh) | 14.51 | 14.50 | Trivial |
| X0_VOLSIZE Calmar (harsh) | 1.5134 | 1.5204 | Trivial (+0.007) |
| X0_VOLSIZE trades | 199 | 186 | YES (surrogate artifact) |
| X0_E5EXIT trades | 199 | 186 | YES (surrogate artifact) |
| G3 (Calmar all-costs) | FAIL | FAIL | Same |
| Verdict | HOLD | HOLD | Same |

No material conclusion changes. Trade counts corrected but Sharpe/MDD/Calmar rankings identical.

### Promotion Decision (7 gates, canonical engine)

| Gate | Result | Detail |
|------|--------|--------|
| G1 Sharpe > P2 (all costs) | PASS | +0.22 all scenarios |
| G2 MDD < P2 (all costs) | PASS | -25 to -27 pp |
| G3 Calmar > P2 (all costs) | **FAIL** | smart: 1.9764 < 2.0058 |
| G4 Boot P(CAGR>0) >= 70% | PASS | 76.0% |
| G5 Boot P(Sharpe>0) >= 70% | PASS | 78.8% |
| G6 Trade count = P2 | PASS | 186 = 186 |
| G7 Boot MDD med < P2 | PASS | 21.78% < 62.54% |

### Final Verdict (Post-Reconciliation)
**HOLD** — 6/7 gates pass. G3 fails on smart Calmar by 1.5%.

**FINAL PROMOTION DECISION (corrected — aligned with fragility audit):**
- **PROMOTE X0 Phase 1 (X0 = E0_EMA21) as final default X0** — fragility audit: GO_WITH_GUARDS, WFO 6/8, bootstrap Sharpe 12/16 h2h
- **HOLD X0 Phase 2 (X0_E5EXIT = E5_EMA21) as alternative** — better real-data CAGR/Sharpe/MDD, but fragility audit: HOLD (WFO 5/8, bootstrap Sharpe 4/16, compound fragility)
- **HOLD X0 Phase 3 (X0_VOLSIZE) as optional low-risk overlay variant** — valid alternative risk profile, not a replacement
- Phase 3 is a risk-overlay on identical timing: same trades, same timing, ~14.7% avg exposure instead of ~44.4%

### Canonical Source of Truth
P3.5 artifacts supersede P3.4 for all canonical numbers. P3.4 artifacts remain as historical record.
The canonical pipeline is: `p3_5_final_benchmark.py` → BacktestEngine for T1/T3/T4, vectorized surrogate for T2 (labeled).

### Outputs
- `research/x0/p3_5_final_benchmark.py`
- `research/x0/p3_5_final_results.json`
- `research/x0/p3_5_final_backtest_table.csv`
- `research/x0/p3_5_final_bootstrap_table.csv`
- `research/x0/p3_5_final_exposure_metrics.csv`
- `research/x0/p3_5_tradecount_reconciliation.csv`
- `research/x0/p3_5_pipeline_audit_matrix.csv`
