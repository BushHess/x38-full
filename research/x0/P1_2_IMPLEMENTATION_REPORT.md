# P1.2 — X0 Phase 1 Core Anchor Implementation

**Date**: 2026-03-06
**Status**: COMPLETE

---

## SUMMARY

Implemented X0 Phase 1 as a behavioral clone of E0+EMA21 (`vtrend_ema21_d1`)
under its own identity (`vtrend_x0`). The strategy is fully integrated into the
repo with 17 dedicated tests, all passing. Full suite (855 tests) shows zero
regressions.

A normalized diff confirms the only differences from E0+EMA21 are docstrings,
comments, and signal reason strings — all logic is identical.

---

## FILES_INSPECTED

| File | Purpose |
|------|---------|
| `strategies/vtrend_ema21_d1/strategy.py` | E0+EMA21 baseline (clone source) |
| `strategies/vtrend_ema21_d1/__init__.py` | Package init pattern |
| `v10/core/engine.py` | Execution semantics, D1 alignment |
| `v10/core/config.py` | Config loader, known strategies |
| `validation/strategy_factory.py` | Strategy registry |
| `v10/cli/backtest.py` | CLI registry |
| `v10/research/candidates.py` | Candidate runner registry |

---

## FILES_CHANGED

### Created (5 files)

| File | Lines | Description |
|------|-------|-------------|
| `strategies/vtrend_x0/__init__.py` | 9 | Package init, exports VTrendX0Config + VTrendX0Strategy |
| `strategies/vtrend_x0/strategy.py` | 225 | Strategy + config + indicators (_ema, _atr, _vdo) |
| `configs/vtrend_x0/vtrend_x0_default.yaml` | 22 | Default YAML config |
| `tests/test_vtrend_x0.py` | 394 | 17 tests across 4 classes |
| `research/x0/search_log.md` | 67 | Implementation decision log |

### Modified (4 files, additions only)

| File | Change |
|------|--------|
| `v10/core/config.py` | +import, +`_VTREND_X0_FIELDS`, +`"vtrend_x0"` in `_KNOWN_STRATEGIES`, +validation block, +entry in `strategy_fields_by_name` |
| `validation/strategy_factory.py` | +import, +`"vtrend_x0"` in `STRATEGY_REGISTRY` |
| `v10/cli/backtest.py` | +import, +`"vtrend_x0"` in `STRATEGY_REGISTRY` |
| `v10/research/candidates.py` | +import, +`_VTREND_X0_FIELDS`, +case in `load_candidates`, +case in `build_strategy`, +in error messages |

### NOT Modified (baselines preserved)

- `strategies/vtrend/strategy.py` (E0)
- `strategies/vtrend_ema21_d1/strategy.py` (E0+EMA21)
- `strategies/vtrend_e5/strategy.py` (E5)
- `strategies/vtrend_e5_ema21_d1/strategy.py` (E5+EMA21)
- `v10/core/engine.py`

---

## BASELINE_MAPPING

X0 Phase 1 is a line-for-line behavioral clone of `vtrend_ema21_d1`.

### Normalized Diff Result
```
sed substitutions: vtrend_x0 -> vtrend_ema21_d1, VTrendX0 -> VTrendEma21D1,
                   x0_entry -> vtrend_ema21_d1_entry, etc.

Result: ONLY docstring/comment differences. Zero logic differences.
```

### Indicator Identity
| Function | X0 lines | E0+EMA21 lines | Status |
|----------|----------|----------------|--------|
| `_ema(series, period)` | 180-186 | 169-175 | IDENTICAL |
| `_atr(high, low, close, period)` | 189-203 | 178-192 | IDENTICAL |
| `_vdo(close, high, low, vol, tb, fast, slow)` | 206-224 | 195-213 | IDENTICAL |

### D1 Regime Mapping Identity
| Aspect | X0 | E0+EMA21 |
|--------|-----|----------|
| Boundary check | `d1_close_times[d1_idx + 1] <= h4_ct` | Same |
| Initial d1_idx | 0 | Same |
| No-D1 fallback | `np.zeros(n_h4, dtype=np.bool_)` | Same |
| Regime condition | `d1_close > d1_ema` (strict >) | Same |

### Entry/Exit Logic Identity
| Aspect | X0 | E0+EMA21 |
|--------|-----|----------|
| Entry guard | `i < 1` returns None | Same |
| NaN guard | `isnan(atr) or isnan(ema_f) or isnan(ema_s)` | Same |
| trend_up | `ema_f > ema_s` | Same |
| trend_down | `ema_f < ema_s` | Same |
| Entry condition | `trend_up and vdo > threshold and regime_ok` | Same |
| Entry exposure | 1.0 | Same |
| Peak tracking | `max(peak, price)` | Same |
| Trail stop | `peak - trail_mult * atr` | Same |
| Trail exposure | 0.0 | Same |
| Trend exit | `trend_down` | Same |
| Trend exposure | 0.0 | Same |

---

## COMMANDS_RUN

```bash
# X0 dedicated tests
python -m pytest tests/test_vtrend_x0.py -v --tb=short
# Result: 17/17 PASSED in 0.28s

# Full test suite
python -m pytest --tb=short -q
# Result: 855 passed, 39 warnings in 86.83s

# Normalized diff (behavioral identity check)
diff <(sed -e 's/vtrend_x0/vtrend_ema21_d1/g' ... strategies/vtrend_x0/strategy.py) \
     strategies/vtrend_ema21_d1/strategy.py
# Result: only docstring/comment diffs

# Registration grep (4 files)
grep vtrend_x0 v10/core/config.py validation/strategy_factory.py \
     v10/cli/backtest.py v10/research/candidates.py
# Result: all 4 have correct entries
```

---

## RESULTS

### STRATEGY_ID_AND_CONFIG_NAMES

| Item | Value |
|------|-------|
| STRATEGY_ID | `"vtrend_x0"` |
| Config class | `VTrendX0Config` |
| Strategy class | `VTrendX0Strategy` |
| Module | `strategies.vtrend_x0.strategy` |
| Signal: entry | `"x0_entry"` |
| Signal: trail stop | `"x0_trail_stop"` |
| Signal: trend exit | `"x0_trend_exit"` |

### EXACT_IMPLEMENTATION_NOTES

1. **Behavioral clone**: All logic paths are identical to `vtrend_ema21_d1`.
   The only differences are:
   - Class/config names (VTrendX0* vs VTrendEma21D1*)
   - Signal reason strings (x0_* vs vtrend_ema21_d1_*)
   - STRATEGY_ID defined as module constant (vs inline string in E0+EMA21)
   - Docstrings and comments

2. **Indicator duplication**: `_ema`, `_atr`, `_vdo` are duplicated per repo
   convention. Each strategy is a frozen research artifact.

3. **D1 regime boundary**: Uses `<=` (inclusive), matching E0+EMA21. The engine
   uses `<` (strict) for its own D1 index tracking, but this does not affect
   the strategy's internal regime computation.

4. **fast_period derivation**: `max(5, slow_period // 4)` — computed at runtime,
   not stored in config. With default slow=120, fast=30.

5. **Registration**: Added to all 4 integration points following exact patterns
   of existing strategies. NOT added to `v10/cli/paper.py` (consistent with
   vtrend_sm, latch, etc. which are also research-only).

### TESTS_ADDED

17 tests across 4 classes in `tests/test_vtrend_x0.py`:

| Class | # | Tests |
|-------|---|-------|
| `TestD1RegimeNoLookahead` | 3 | `test_regime_uses_completed_d1_only`, `test_no_d1_bars_yields_all_false`, `test_future_d1_not_visible` |
| `TestConfigLoad` | 5 | `test_config_loads_from_yaml`, `test_config_defaults_match_spec`, `test_strategy_id`, `test_subclass_of_strategy`, `test_field_count` |
| `TestSmokeSignals` | 6 | `test_entry_signal_during_uptrend`, `test_exit_signal_after_crash`, `test_no_signal_without_regime`, `test_signal_reasons_correct`, `test_empty_bars_no_crash`, `test_on_init_not_called_no_crash` |
| `TestRegistration` | 3 | `test_strategy_factory_registry`, `test_config_known_strategies`, `test_cli_backtest_registry` |

Spec requirement coverage:
- D1 regime no-lookahead: **3 tests** (spec requires >= 1)
- Config/smoke test: **5 tests** (spec requires >= 1)
- Signal production on sample data: **6 tests** (spec requires >= 1)

### DEFAULT_PARAMS

| Parameter | Value | Type | Category |
|-----------|-------|------|----------|
| `slow_period` | 120.0 | float | Tunable |
| `trail_mult` | 3.0 | float | Tunable |
| `vdo_threshold` | 0.0 | float | Tunable |
| `d1_ema_period` | 21 | int | Tunable |
| `atr_period` | 14 | int | Structural |
| `vdo_fast` | 12 | int | Structural |
| `vdo_slow` | 28 | int | Structural |
| *fast_period* | *30 (derived)* | *int* | *Not stored* |

### DEVIATIONS_FROM_SPEC

**None.** Implementation matches spec exactly:

| Spec Requirement | Status |
|------------------|--------|
| H4 signal, D1 regime, long-only | MATCH |
| Entry: regime_ok AND ema_fast > ema_slow AND vdo > 0 => exposure=1.0 | MATCH |
| Exit: trail_stop OR trend_reversal => exposure=0.0 | MATCH |
| slow=120, trail=3.0, atr=14, vdo_thresh=0.0, d1_ema=21 | MATCH |
| No cooldown | MATCH |
| No fractional sizing | MATCH |
| No conviction scaling | MATCH |
| No shock filter | MATCH |
| No regime-based exit | MATCH |
| No VDO z-score | MATCH |
| No trend_score threshold | MATCH |
| No new fallback logic | MATCH |
| No lookahead in D1 regime | MATCH (3 tests) |
| No baseline modifications | MATCH (verified) |
| Indicator duplication per repo convention | MATCH |

### GIT_DIFF_SUMMARY

Not git-tracked (repo has no git). File inventory:

```
NEW  strategies/vtrend_x0/__init__.py        (9 lines)
NEW  strategies/vtrend_x0/strategy.py        (225 lines)
NEW  configs/vtrend_x0/vtrend_x0_default.yaml (22 lines)
NEW  tests/test_vtrend_x0.py                 (394 lines)
NEW  research/x0/search_log.md               (67 lines)
NEW  research/x0/P1_1_AUDIT_REPORT.md        (report)
MOD  v10/core/config.py                      (+7 lines: import, fields, known, validation, fields_by_name)
MOD  validation/strategy_factory.py           (+4 lines: import, registry)
MOD  v10/cli/backtest.py                     (+2 lines: import, registry)
MOD  v10/research/candidates.py              (+12 lines: import, fields, load, build, error msgs)
```

---

## BLOCKERS

None.

---

## NEXT_READY

- **P1.3**: Run bit-identical parity test on real data — backtest X0 vs E0+EMA21
  with `data/bars_btcusdt_2016_now_h1_4h_1d.csv`, confirm identical trade count,
  equity curve, and summary metrics (CAGR, Sharpe, MDD).
- **P2.x**: Begin X0 Phase 2 modifications (to be specified separately).
