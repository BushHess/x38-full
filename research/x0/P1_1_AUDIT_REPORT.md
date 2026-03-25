# P1.1 — Audit Repo & Freeze X0 Phase 1 Design

**Date**: 2026-03-06
**Status**: COMPLETE (P1.2 already implemented; this audit validates the existing implementation)

---

## 1. SUMMARY

Audited the btc-spot-dev repo to freeze the technical spec for X0 Phase 1. P1.2 was
already implemented in a prior session. This audit confirms the implementation is correct,
complete, and consistent with the frozen spec below.

Key findings:
- X0 Phase 1 (`vtrend_x0`) is a behavioral clone of E0+EMA21 (`vtrend_ema21_d1`)
- All 4 integration points registered correctly
- 17/17 dedicated tests pass
- 855/855 full suite tests pass (no regressions)
- D1 regime boundary convention (`<=`) matches E0+EMA21 exactly
- No baseline code was modified

---

## 2. FILES_INSPECTED

### Baselines (READ ONLY — not modified)
| File | Purpose |
|------|---------|
| `strategies/vtrend/strategy.py` | E0 baseline (3-param) |
| `strategies/vtrend_ema21_d1/strategy.py` | E0+EMA21 baseline (4-param, D1 regime) |
| `strategies/vtrend_e5/strategy.py` | E5 baseline (robust ATR) |
| `strategies/vtrend_e5_ema21_d1/strategy.py` | E5+EMA21 baseline |

### Engine & Infrastructure (READ ONLY)
| File | Purpose |
|------|---------|
| `v10/core/engine.py` | Backtest engine — execution semantics, D1 alignment |
| `v10/core/types.py` | Bar, MarketState, Signal, Fill types |
| `v10/strategies/base.py` | Strategy ABC |
| `research/lib/vcbb.py` | Bootstrap library |
| `research/lib/dsr.py` | Deflated Sharpe Ratio |
| `research/lib/effective_dof.py` | DOF correction |
| `research/lib/pair_diagnostic.py` | Pair comparison |

### X0 Implementation (created in P1.2, validated here)
| File | Purpose |
|------|---------|
| `strategies/vtrend_x0/__init__.py` | Package init |
| `strategies/vtrend_x0/strategy.py` | Strategy + config (225 lines) |
| `configs/vtrend_x0/vtrend_x0_default.yaml` | Default YAML config |
| `tests/test_vtrend_x0.py` | 17 tests |

### Registration Points (modified in P1.2, validated here)
| File | Change |
|------|--------|
| `v10/core/config.py` | `_VTREND_X0_FIELDS`, `_KNOWN_STRATEGIES`, validation block |
| `validation/strategy_factory.py` | `STRATEGY_REGISTRY` entry |
| `v10/cli/backtest.py` | `STRATEGY_REGISTRY` entry |
| `v10/research/candidates.py` | Fields, `load_candidates`, `build_strategy` |

---

## 3. FILES_CHANGED

None in this audit. P1.2 already created/modified the following (validated here):

**Created:**
- `strategies/vtrend_x0/__init__.py`
- `strategies/vtrend_x0/strategy.py`
- `configs/vtrend_x0/vtrend_x0_default.yaml`
- `tests/test_vtrend_x0.py`
- `research/x0/search_log.md`

**Modified (additions only):**
- `v10/core/config.py` — 4 additions (import, fields, known set, validation)
- `validation/strategy_factory.py` — import + registry entry
- `v10/cli/backtest.py` — import + registry entry
- `v10/research/candidates.py` — import, fields, 2 case branches

---

## 4. BASELINE_MAPPING

X0 Phase 1 is a line-for-line behavioral clone of `vtrend_ema21_d1`.

### Indicator Parity
| Indicator | X0 (`strategy.py`) | E0+EMA21 (`strategy.py`) | Match |
|-----------|---------------------|--------------------------|-------|
| `_ema` | Lines 180-186 | Lines 169-175 | IDENTICAL |
| `_atr` | Lines 189-203 | Lines 178-192 | IDENTICAL |
| `_vdo` | Lines 206-224 | Lines 195-213 | IDENTICAL |

### D1 Regime Parity
| Aspect | X0 | E0+EMA21 | Match |
|--------|-----|----------|-------|
| Method | `_compute_d1_regime` | `_compute_d1_regime` | IDENTICAL |
| Boundary | `d1_close_times[d1_idx + 1] <= h4_ct` | Same | YES |
| No-D1 fallback | `np.zeros(n_h4, dtype=np.bool_)` | Same | YES |

### Entry/Exit Logic Parity
| Aspect | X0 | E0+EMA21 | Match |
|--------|-----|----------|-------|
| Entry condition | `trend_up AND vdo > threshold AND regime_ok` | Same | YES |
| Entry exposure | 1.0 | 1.0 | YES |
| Trail stop | `price < peak - trail_mult * atr` | Same | YES |
| Trend exit | `ema_fast < ema_slow` | Same | YES |
| Exit exposure | 0.0 | 0.0 | YES |
| Signal reasons | `x0_entry`, `x0_trail_stop`, `x0_trend_exit` | `ema21d1_entry`, etc. | DIFFERENT (by design) |

### Config Parity
| Field | X0 Default | E0+EMA21 Default | Match |
|-------|-----------|-------------------|-------|
| slow_period | 120.0 | 120.0 | YES |
| trail_mult | 3.0 | 3.0 | YES |
| vdo_threshold | 0.0 | 0.0 | YES |
| d1_ema_period | 21 | 21 | YES |
| atr_period | 14 | 14 | YES |
| vdo_fast | 12 | 12 | YES |
| vdo_slow | 28 | 28 | YES |

---

## 5. COMMANDS_RUN

```
python -m pytest tests/test_vtrend_x0.py -v --tb=short    # 17/17 PASS
python -m pytest --tb=short -q                              # 855/855 PASS, 39 warnings
```

---

## 6. RESULTS

### PHASE1_FROZEN_SPEC

```
Strategy ID:   vtrend_x0
Config class:  VTrendX0Config
Strategy class: VTrendX0Strategy
Base:          Behavioral clone of vtrend_ema21_d1 (E0+EMA21)

ENTRY (when flat):
  1. D1 regime:      last completed D1 close > EMA(d1_ema_period) on D1 closes
  2. EMA crossover:  ema(close, fast_p) > ema(close, slow_p)
                     where fast_p = max(5, slow_p // 4)
  3. VDO confirm:    vdo > vdo_threshold
  => target_exposure = 1.0, reason = "x0_entry"

EXIT (when long):
  1. Trail stop:     close < peak_price - trail_mult * ATR(atr_period)
     => target_exposure = 0.0, reason = "x0_trail_stop"
  2. Trend reversal: ema_fast < ema_slow
     => target_exposure = 0.0, reason = "x0_trend_exit"

PARAMETERS (7 fields):
  slow_period:    120.0  (tunable)
  trail_mult:     3.0    (tunable)
  vdo_threshold:  0.0    (tunable)
  d1_ema_period:  21     (tunable)
  atr_period:     14     (structural)
  vdo_fast:       12     (structural)
  vdo_slow:       28     (structural)

CONSTRAINTS (Phase 1 only):
  - No cooldown
  - No fractional sizing (binary 0/1 exposure)
  - No conviction scaling
  - No shock filter
  - No regime-based exit
  - No VDO z-score
  - No trend_score threshold
  - Long-only
```

### FILE_PLAN

| File | Action | Status |
|------|--------|--------|
| `strategies/vtrend_x0/__init__.py` | CREATE | DONE |
| `strategies/vtrend_x0/strategy.py` | CREATE (225 lines) | DONE |
| `configs/vtrend_x0/vtrend_x0_default.yaml` | CREATE | DONE |
| `tests/test_vtrend_x0.py` | CREATE (17 tests) | DONE |
| `v10/core/config.py` | ADD import, fields, known set, validation | DONE |
| `validation/strategy_factory.py` | ADD import, registry entry | DONE |
| `v10/cli/backtest.py` | ADD import, registry entry | DONE |
| `v10/research/candidates.py` | ADD import, fields, 2 case branches | DONE |
| `research/x0/search_log.md` | CREATE (experiment log) | DONE |

### TEST_PLAN

| Test Class | Test | What It Validates |
|------------|------|-------------------|
| `TestD1RegimeNoLookahead` | `test_regime_uses_completed_d1_only` | H4 bars before D1 close don't see that D1's regime |
| | `test_no_d1_bars_yields_all_false` | Empty D1 → all regime=False |
| | `test_future_d1_not_visible` | Uncompleted D1 bar invisible |
| `TestConfigLoad` | `test_config_loads_from_yaml` | YAML round-trip, correct param values |
| | `test_config_defaults_match_spec` | 7 defaults match frozen spec |
| | `test_strategy_id` | `STRATEGY_ID == "vtrend_x0"` |
| | `test_subclass_of_strategy` | Inherits `Strategy` ABC |
| | `test_field_count` | Exactly 7 config fields |
| `TestSmokeSignals` | `test_entry_signal_during_uptrend` | Entry fires with regime ON + trend up + VDO > 0 |
| | `test_exit_signal_after_crash` | Trail stop or trend exit fires after crash |
| | `test_no_signal_without_regime` | Zero entries when D1 regime is OFF |
| | `test_signal_reasons_correct` | All reasons start with `x0_` |
| | `test_empty_bars_no_crash` | Empty input doesn't crash |
| | `test_on_init_not_called_no_crash` | Calling on_bar without on_init returns None |
| `TestRegistration` | `test_strategy_factory_registry` | In validation/strategy_factory.py STRATEGY_REGISTRY |
| | `test_config_known_strategies` | In v10/core/config.py _KNOWN_STRATEGIES |
| | `test_cli_backtest_registry` | In v10/cli/backtest.py STRATEGY_REGISTRY |

### PARITY_EXPECTATION

Running X0 with default params on the same data as E0+EMA21 (`vtrend_ema21_d1`)
MUST produce **bit-identical** results:
- Same number of trades
- Same entry/exit bar indices
- Same equity curve (to floating-point precision)
- Same CAGR, Sharpe, MDD

The ONLY differences should be:
- Signal reason strings (`x0_*` vs `ema21d1_*`)
- Strategy name in metadata (`vtrend_x0` vs `vtrend_ema21_d1`)

**This parity test should be run as a separate P1.3 step** using the backtest CLI
on real data with `data/bars_btcusdt_2016_now_h1_4h_1d.csv`.

### RISKS_AND_AMBIGUITIES

1. **D1 boundary convention (LOW RISK)**
   - Engine uses strict `<`: `d1[d1_idx + 1].close_time < bar.close_time`
   - Strategy uses inclusive `<=`: `d1_close_times[d1_idx + 1] <= h4_ct`
   - Both X0 and E0+EMA21 use `<=` — parity is maintained
   - In practice, H4 and D1 close times never exactly coincide (H4 at xx:59:59.999,
     D1 at 23:59:59.999 on different boundaries), so the `<` vs `<=` difference
     is academic for real Binance data

2. **Indicator duplication (ACCEPTED RISK)**
   - `_ema`, `_atr`, `_vdo` are copy-pasted per strategy module
   - This is the repo convention — each strategy is a frozen artifact
   - If a bug is found in indicators, it must be fixed in ALL copies
   - Acceptable because X0 indicators are proven identical to E0+EMA21

3. **Paper trading registry (NO ACTION)**
   - `v10/cli/paper.py` only has v8_apex and buy_and_hold
   - X0 is NOT registered there (consistent with vtrend_sm, latch, etc.)
   - Will need registration when/if X0 goes to paper trading

4. **No parity test on real data yet (DEFERRED)**
   - Smoke tests use synthetic data — sufficient for logic validation
   - Bit-identical parity with E0+EMA21 on real data not yet verified
   - Should be done in P1.3

---

## 7. BLOCKERS

None. All files created, all tests passing, all registrations complete.

---

## 8. NEXT_READY

- **P1.3**: Run bit-identical parity test — backtest X0 vs E0+EMA21 on real data,
  confirm identical trade count, equity, and metrics.
- **P2.x**: Begin X0 Phase 2 — first modification to diverge from E0+EMA21
  (to be specified in a separate prompt).
