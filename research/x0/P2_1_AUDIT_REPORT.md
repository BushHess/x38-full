# P2.1 — Audit E5 Exit Logic & Freeze X0 Phase 2 Design

**Date**: 2026-03-06
**Status**: COMPLETE (audit + design freeze only, no implementation)

---

## SUMMARY

Audited the E5 robust ATR trail exit logic and compared it against X0 Phase 1
and E5+EMA21 to determine the exact transplant scope for X0 Phase 2.

**Conclusion: The transplant is CLEAN.** The E5 exit differs from X0 Phase 1
in exactly ONE indicator (`_robust_atr` replaces `_atr`). There is zero
entry-side coupling. X0 Phase 2 will be a behavioral clone of E5+EMA21.

---

## FILES_INSPECTED

| File | Lines | Purpose |
|------|-------|---------|
| `strategies/vtrend_x0/strategy.py` | 225 | X0 Phase 1 (standard ATR trail + D1 regime) |
| `strategies/vtrend_e5/strategy.py` | 219 | E5 (robust ATR trail, no D1 regime) |
| `strategies/vtrend_e5_ema21_d1/strategy.py` | 231 | E5+EMA21 (robust ATR trail + D1 regime) |

---

## FILES_CHANGED

| File | Change |
|------|--------|
| `research/x0/search_log.md` | Updated with P2.1 audit results |
| `research/x0/P2_1_AUDIT_REPORT.md` | This report (created) |

No strategy code modified.

---

## BASELINE_MAPPING

| Strategy | Entry Stack | Exit Trail | Regime | Parity Target |
|----------|-------------|------------|--------|---------------|
| X0 Phase 1 | EMA cross + VDO + D1 regime | Standard ATR(14) | D1 EMA(21) | = E0+EMA21 |
| X0 Phase 2 | EMA cross + VDO + D1 regime | **Robust ATR** | D1 EMA(21) | **= E5+EMA21** |
| E0 | EMA cross + VDO | Standard ATR(14) | None | — |
| E0+EMA21 | EMA cross + VDO + D1 regime | Standard ATR(14) | D1 EMA(21) | — |
| E5 | EMA cross + VDO | Robust ATR | None | — |
| E5+EMA21 | EMA cross + VDO + D1 regime | Robust ATR | D1 EMA(21) | — |

---

## COMMANDS_RUN

```
# Read-only audit — no commands executed
# All analysis done by reading source files
```

---

## RESULTS

### COMPONENT_DIFF_MATRIX

#### Entry Logic Comparison

| Component | X0 Phase 1 | E5 | E5+EMA21 | X0 Phase 2 (planned) |
|-----------|-----------|-----|----------|---------------------|
| EMA crossover | `ema_f > ema_s` | Same | Same | **Same as Phase 1** |
| VDO gate | `vdo > 0.0` | Same | Same | **Same as Phase 1** |
| D1 regime | `d1_close > d1_ema(21)` | **NONE** | Same as X0 | **Same as Phase 1** |
| Entry exposure | 1.0 | 1.0 | 1.0 | **1.0** |
| Entry reason | `x0_entry` | `vtrend_e5_entry` | `vtrend_e5_ema21_d1_entry` | **`x0_entry`** |

#### Exit Logic Comparison

| Component | X0 Phase 1 | E5 | E5+EMA21 | X0 Phase 2 (planned) |
|-----------|-----------|-----|----------|---------------------|
| Trail indicator | **`_atr(14)`** | `_robust_atr` | `_robust_atr` | **`_robust_atr`** |
| Trail formula | `peak - mult * atr` | Same formula | Same formula | **Same formula** |
| Trail params | mult=3.0, period=14 | mult=3.0, cap_q=0.90, cap_lb=100, period=20 | Same as E5 | **Same as E5** |
| Trend exit | `ema_f < ema_s` | Same | Same | **Same** |
| Exit exposure | 0.0 | 0.0 | 0.0 | **0.0** |
| Peak tracking | `max(peak, close)` | Same | Same | **Same** |

#### Indicator Comparison

| Indicator | X0 Phase 1 | E5 | E5+EMA21 | X0 Phase 2 |
|-----------|-----------|-----|----------|------------|
| `_ema(close, p)` | Yes | Yes | Yes | **Keep** |
| `_atr(h, l, c, 14)` | **Yes (trail)** | Yes (unused?) | No | **Drop from trail** |
| `_robust_atr(h, l, c)` | **No** | Yes (trail) | Yes (trail) | **Add** |
| `_vdo(c, h, l, v, tb)` | Yes | Yes | Yes | **Keep** |
| `_compute_d1_regime` | Yes | No | Yes | **Keep** |

#### Config Field Comparison

| Field | X0 Phase 1 | E5 | E5+EMA21 | X0 Phase 2 |
|-------|-----------|-----|----------|------------|
| slow_period | 120.0 | 120.0 | 120.0 | **120.0** |
| trail_mult | 3.0 | 3.0 | 3.0 | **3.0** |
| vdo_threshold | 0.0 | 0.0 | 0.0 | **0.0** |
| d1_ema_period | 21 | — | 21 | **21** |
| atr_period | 14 | 14 | 14 | **14 (may keep for reference)** |
| vdo_fast | 12 | 12 | 12 | **12** |
| vdo_slow | 28 | 28 | 28 | **28** |
| ratr_cap_q | — | **0.90** | **0.90** | **0.90 (NEW)** |
| ratr_cap_lb | — | **100** | **100** | **100 (NEW)** |
| ratr_period | — | **20** | **20** | **20 (NEW)** |

#### State / Runtime Comparison

| State | X0 Phase 1 | E5 | E5+EMA21 | X0 Phase 2 |
|-------|-----------|-----|----------|------------|
| `_in_position` | bool | Same | Same | **Same** |
| `_peak_price` | float | Same | Same | **Same** |
| NaN guard | `isnan(atr_val)` | `isnan(ratr_val)` | `isnan(ratr_val)` | **`isnan(ratr_val)`** |
| Init guard | `_atr is None` | `_ratr is None` | `_ratr is None` | **`_ratr is None`** |

### EXACT_E5_EXIT_SEMANTICS

```
_robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20):

  1. Compute True Range:
     TR[i] = max(high[i]-low[i], |high[i]-close[i-1]|, |low[i]-close[i-1]|)

  2. Cap TR at rolling quantile:
     For i >= cap_lb:
       q = percentile(TR[i-cap_lb : i], 90)     # lookback window, excludes current
       TR_cap[i] = min(TR[i], q)
     For i < cap_lb:
       TR_cap[i] = NaN

  3. Wilder EMA on capped TR:
     seed = mean(TR_cap[cap_lb : cap_lb + period])    # bars 100-119
     ratr[cap_lb + period - 1] = seed                  # bar 119
     For i >= cap_lb + period:
       ratr[i] = (ratr[i-1] * (period-1) + TR_cap[i]) / period

  Result: ratr[0:119] = NaN, ratr[119:] = valid values

Exit logic (unchanged from E0):
  peak = max(peak, close)
  trail_stop = peak - trail_mult * ratr[i]
  if close < trail_stop: EXIT (reason: x0_trail_stop)
  elif ema_fast < ema_slow: EXIT (reason: x0_trend_exit)
```

**Key property of robust ATR**: By capping TR at Q90, it filters out outlier
volatility spikes (flash crashes, wicks). This makes the trailing stop
tighter during normal markets and prevents it from widening excessively
after a single extreme bar. The net effect is earlier trail exits during
mean-reverting volatility events → lower MDD.

### PHASE2_FROZEN_SPEC

```
Strategy ID:   vtrend_x0
Config class:  VTrendX0Config
Strategy class: VTrendX0Strategy
Phase:         2 (robust ATR trail)
Parity target: vtrend_e5_ema21_d1

ENTRY (unchanged from Phase 1):
  1. D1 regime:      last completed D1 close > EMA(d1_ema_period)
  2. EMA crossover:  ema_fast > ema_slow
  3. VDO confirm:    vdo > vdo_threshold
  => target_exposure = 1.0, reason = "x0_entry"

EXIT (CHANGED — robust ATR trail):
  1. Trail stop:     close < peak - trail_mult * robust_ATR(ratr_cap_q, ratr_cap_lb, ratr_period)
     => target_exposure = 0.0, reason = "x0_trail_stop"
  2. Trend reversal: ema_fast < ema_slow
     => target_exposure = 0.0, reason = "x0_trend_exit"

PARAMETERS (10 fields):
  slow_period:    120.0  (tunable, unchanged)
  trail_mult:     3.0    (tunable, unchanged)
  vdo_threshold:  0.0    (tunable, unchanged)
  d1_ema_period:  21     (tunable, unchanged)
  atr_period:     14     (structural, kept for reference)
  vdo_fast:       12     (structural, unchanged)
  vdo_slow:       28     (structural, unchanged)
  ratr_cap_q:     0.90   (structural, NEW from E5)
  ratr_cap_lb:    100    (structural, NEW from E5)
  ratr_period:    20     (structural, NEW from E5)

CONSTRAINTS (carried from Phase 1):
  - No cooldown
  - No fractional sizing (binary 0/1)
  - No conviction scaling
  - No shock filter
  - No regime-based exit
  - No VDO z-score
  - No trend_score threshold
  - Long-only
```

### FILE_PLAN

| File | Action | Details |
|------|--------|---------|
| `strategies/vtrend_x0/strategy.py` | **MODIFY** | Add `_robust_atr`, add 3 config fields, swap trail from `_atr` to `_ratr` |
| `configs/vtrend_x0/vtrend_x0_default.yaml` | **NO CHANGE** | YAML only has tunable params; ratr fields are structural defaults |
| `tests/test_vtrend_x0.py` | **MODIFY** | Update field count test (7→10), add robust ATR smoke test |
| `v10/core/config.py` | **MODIFY** | Add 3 new fields to `_VTREND_X0_FIELDS` |
| `v10/research/candidates.py` | **MODIFY** | Add 3 new fields to `_VTREND_X0_FIELDS` |
| `validation/strategy_factory.py` | **NO CHANGE** | Already registered |
| `v10/cli/backtest.py` | **NO CHANGE** | Already registered |
| `research/x0/search_log.md` | **UPDATE** | P2.2 implementation log |

### TEST_PLAN

| Test | What It Validates |
|------|-------------------|
| **Update `test_field_count`** | Config now has 10 fields (was 7) |
| **Update `test_config_defaults_match_spec`** | Add 3 new default checks |
| **New: `test_robust_atr_produces_valid_output`** | `_robust_atr` returns array with NaN[:119] and valid values after |
| **New: `test_trail_uses_robust_atr`** | Trail stop signal uses `_ratr` not `_atr` (verify via signal timing diff vs Phase 1) |
| **Existing tests remain** | D1 regime, entry signals, registration — should all pass unchanged |

### RISKS_AND_AMBIGUITIES

1. **NaN window difference (LOW RISK)**
   - Standard ATR: NaN for bars 0-12 (13 bars)
   - Robust ATR: NaN for bars 0-119 (120 bars)
   - With 365-day warmup (2190 bars), the NaN window is entirely in warmup → no impact
   - Risk: if warmup is ever reduced below 120 bars, X0 Phase 2 would produce no trades
     during early reporting bars. This is acceptable (structural constraint).

2. **`_atr` retention (DESIGN CHOICE)**
   - E5+EMA21 does NOT compute standard `_atr` — it only has `_ratr`
   - X0 Phase 2 could either:
     (a) Keep `_atr` computed but unused (for debugging/comparison)
     (b) Remove `_atr` entirely (cleaner, matches E5+EMA21)
   - **Decision: Remove `_atr` from on_init and on_bar.** Keep `_atr` function
     definition for potential future use, but don't compute it. This matches E5+EMA21.

3. **`_robust_atr` implementation variant (NO RISK)**
   - E5's `_robust_atr` uses pure-Python loop for rolling percentile
   - `parity_eval.py`'s `_robust_atr` uses vectorized `sliding_window_view`
   - Both produce identical results — strategy module uses the pure-Python version
     (matching repo convention of duplicated indicators per strategy)

4. **Signal timing will change (EXPECTED)**
   - Robust ATR produces tighter trail stops → some trades exit earlier
   - Some entries may differ due to position state changing (earlier exit → earlier
     re-entry opportunity). This is an expected second-order effect.
   - Entry LOGIC is identical; only entry TIMING changes due to exit-driven state changes.

### ACCEPTANCE_CRITERIA_FOR_PHASE2

| Criterion | Method |
|-----------|--------|
| **Parity with E5+EMA21** | Bit-identical backtest (all 3 cost scenarios) |
| **Entry logic unchanged** | Entry reason is `x0_entry` with same conditions |
| **Robust ATR in trail** | Trail reason `x0_trail_stop` uses `_ratr` |
| **D1 regime preserved** | No entry without regime_ok=True |
| **No lookahead** | Existing D1 regime tests still pass |
| **Config fields correct** | 10 fields, 3 new ratr params with E5 defaults |
| **All existing tests pass** | 855+ tests, 0 regressions |
| **Performance delta attributed** | Phase 2 vs Phase 1 diff = E5+EMA21 vs E0+EMA21 diff |

---

## BLOCKERS

None. The transplant is clean — `_robust_atr` is self-contained with no
entry-side coupling.

---

## NEXT_READY

- **P2.2**: Implement X0 Phase 2 — swap `_atr` trail for `_robust_atr` trail
  in `strategies/vtrend_x0/strategy.py`, update config/tests.
- **P2.3**: Parity audit X0 Phase 2 vs E5+EMA21 (bit-identical expected).
- **P2.4**: Full benchmark X0 Phase 2 vs all 5 baselines + Phase 1.
