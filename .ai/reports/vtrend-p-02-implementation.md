# VTREND-P Implementation Report

**Date**: 2026-03-05
**Status**: COMPLETE
**Prerequisite**: vtrend-p-01-audit-discovery.md (READY_FOR_VTRENDP_IMPLEMENT_AS_IS)

---

## 1. Implementation Summary

Ported `run_vtrend_p()` from `Latch/research/vtrend_variants.py` (lines 735–848) into
`btc-spot-dev` as a standalone strategy module, following the SM reference pattern.

**Key characteristics**: Price-first trend follower. 10 params (vs SM's 16). No fast EMA,
no VDO filter, no regime-break exit. Entry uses `close > ema_slow` for regime check
(not `ema_fast > ema_slow`). Default `atr_mult=1.5` (vs SM's 3.0), `target_vol=0.12`
(vs SM's 0.15).

## 2. Files Created

| File | Lines | Description |
|---|---|---|
| `strategies/vtrend_p/__init__.py` | 13 | Package exports (STRATEGY_ID, VTrendPConfig, VTrendPStrategy) |
| `strategies/vtrend_p/strategy.py` | 298 | Full strategy + config + duplicated indicators |
| `configs/vtrend_p/vtrend_p_default.yaml` | 21 | Default validation config |
| `tests/test_vtrend_p.py` | 467 | 51 tests (config, indicators, logic, registration, proxy) |

## 3. Files Modified

| File | Change |
|---|---|
| `v10/core/config.py` | Import VTrendPConfig; add `_VTREND_P_FIELDS`; add `"vtrend_p"` to `_KNOWN_STRATEGIES`; add to `strategy_fields_by_name`; add validation branch |
| `v10/cli/backtest.py` | Import VTrendPStrategy; add to `STRATEGY_REGISTRY` |
| `validation/strategy_factory.py` | Import VTrendPConfig/VTrendPStrategy; add to `STRATEGY_REGISTRY` |
| `v10/research/candidates.py` | Import VTrendPConfig/VTrendPStrategy; add `_VTREND_P_FIELDS`; add routing in `load_candidates()` and `build_strategy()` |

## 4. Algorithm Specification (Ported As-Is)

### Entry (FLAT → LONG)
```
regime_ok   = close > ema_slow
slope_ok    = ema_slow > ema_slow[i - slope_lookback]
breakout_ok = close > rolling_high_shifted(high, entry_n)
weight      = clip(target_vol / max(rv, EPS), min_weight, 1.0)
IF regime_ok AND slope_ok AND breakout_ok AND weight > 0 → ENTER(weight)
```

### Exit (LONG → FLAT)
```
exit_floor  = max(rolling_low_shifted(low, exit_n), ema_slow - atr_mult * ATR)
IF close < exit_floor → EXIT(0.0)
```

### Rebalance (LONG → LONG, different weight)
```
new_weight = clip(target_vol / max(rv, EPS), min_weight, 1.0)
IF |new_weight - current_exposure| >= min_rebalance_weight_delta → REBALANCE(new_weight)
```

### Parameters (10)
| Param | Default | Auto-derived |
|---|---|---|
| slow_period | 120 | — |
| atr_period | 14 | — |
| atr_mult | 1.5 | — |
| target_vol | 0.12 | — |
| entry_n | None | max(24, slow_period // 2) |
| exit_n | None | max(12, slow_period // 4) |
| vol_lookback | None | slow_period |
| slope_lookback | 6 | — |
| min_rebalance_weight_delta | 0.05 | — |
| min_weight | 0.0 | — |

## 5. SM → P Transformation Summary

| Feature | SM | P |
|---|---|---|
| Regime check | ema_fast > ema_slow + slope | close > ema_slow + slope |
| VDO filter | Optional (use_vdo_filter) | Removed |
| Regime-break exit | Optional (exit_on_regime_break) | Removed |
| atr_mult default | 3.0 | 1.5 |
| target_vol default | 0.15 | 0.12 |
| Config fields | 16 | 10 |

## 6. Indicator Duplication

Per codebase convention (frozen research artifacts), indicators are duplicated:
- `_ema`, `_atr`, `_rolling_high_shifted`, `_rolling_low_shifted`, `_realized_vol`, `_clip_weight`
- Copied from `strategies/vtrend_sm/strategy.py` (identical implementations)
- NO `_vdo` (not needed by P)

## 7. Test Results

### Unit Tests (51/51 PASS)
```
tests/test_vtrend_p.py — 51 passed in 0.43s
```

| Category | Count |
|---|---|
| Config defaults + resolved() | 6 |
| Indicator numerics (_ema, _atr, _rolling_*, _realized_vol) | 7 |
| _clip_weight branches | 10 |
| Entry/exit/rebalance logic | 10 |
| P-specific differentiation from SM | 3 |
| Registration (4 integration points) | 5 |
| Invariants (on_after_fill, EPS, empty bars) | 3 |
| ConfigProxy resolved() allowlist | 2 |
| Strategy interface smoke | 1 |
| BARS_PER_YEAR_4H constant | 1 |
| min_weight entry guard | 2 |
| slope_lookback parametric | 1 |

### Full Suite (766/766 PASS, 39 warnings)
```
python -m pytest — 766 passed, 39 warnings in 70.98s
```
Baseline 715 + 51 new = 766. All 39 warnings are pre-existing (v8/v11 divide-by-zero).

## 8. Validation Pipeline

```
python validate_strategy.py \
  --strategy vtrend_p --baseline buy_and_hold \
  --config configs/vtrend_p/vtrend_p_default.yaml \
  --baseline-config configs/frozen/v10_baseline.yaml \
  --out out/validation_vtrend_p --suite basic --bootstrap 0 --force
```

| Check | Status |
|---|---|
| lookahead | PASS |
| data_integrity | PASS |
| invariants | PASS |
| config_unused_fields | PASS (all 10 fields allowlisted via resolved()) |
| churn_metrics | PASS |
| cost_sweep | PASS |
| regime | INFO |
| backtest | FAIL (score delta vs baseline) |
| wfo | FAIL (robustness threshold) |

**Verdict**: REJECT — expected, as this is a first-pass integration test comparing P
against v10_baseline (v8_apex). The backtest FAIL and WFO FAIL reflect the
candidate-vs-baseline comparison, not a strategy bug.

## 9. Real-Data Backtest Metrics (Base Scenario, 2019-01 → 2026-02)

| Metric | Value |
|---|---|
| CAGR | 13.24% |
| Max Drawdown | 11.96% |
| Sharpe | 1.4633 |
| Sortino | 1.3448 |
| Trades | 77 |
| Avg Exposure | 10.34% |
| Turnover/yr | 6.39x |
| Fee Drag | 0.64%/yr |

### Cross-Scenario Comparison
| Scenario | CAGR | MDD | Sharpe |
|---|---|---|---|
| Smart (16 bps RT) | 13.88% | 11.28% | 1.5279 |
| Base (31 bps RT) | 13.24% | 11.96% | 1.4633 |
| Harsh (50 bps RT) | 12.58% | 12.68% | 1.3966 |

## 10. Remaining Work

- **Parity cross-validation**: Compare against Latch standalone `run_vtrend_p()` output.
  Expected tolerance: within 2–3% due to annualization constant (2190.0 vs 2191.5)
  and minor cost model differences.
- **PairDiagnostic**: Run pair comparison vs E0 (VTREND) to characterize
  correlation, diversification potential, and dominance regions.
- **Full bootstrap**: Run with `--bootstrap 2000` for confidence intervals.

---

**Implementation Status**: COMPLETE — all integration points wired, 51/51 tests pass,
766/766 full suite pass, validation pipeline executes cleanly.
