# P3.2 — Implementation Report: X0 Phase 3 (Frozen Vol Sizing)

## SUMMARY

Implemented X0 Phase 3 = X0 Phase 2 + frozen entry-time volatility sizing.
Created new module `strategies/vtrend_x0_volsize/` with 13-field config (Phase 2's 10 + 3 new).
Entry timing identical to Phase 2; only position size changes via `target_vol / max(rv, vol_floor)`.
Weight frozen from entry to exit. rv NaN fallback to weight=1.0 guarantees timing parity.
17/17 new tests pass. 889/889 full suite pass. Zero baseline modifications.

## FILES_CHANGED

| File | Action | Detail |
|------|--------|--------|
| `strategies/vtrend_x0_volsize/__init__.py` | CREATED | Empty init |
| `strategies/vtrend_x0_volsize/strategy.py` | CREATED | 290 lines: config, strategy, 5 helpers |
| `configs/vtrend_x0_volsize/vtrend_x0_volsize_default.yaml` | CREATED | 13 strategy params + engine + risk |
| `tests/test_vtrend_x0_volsize.py` | CREATED | 17 tests across 8 test classes |
| `v10/core/config.py` | EDITED | +import, +_FIELDS, +_KNOWN_STRATEGIES, +validation |
| `validation/strategy_factory.py` | EDITED | +import, +STRATEGY_REGISTRY entry |
| `v10/cli/backtest.py` | EDITED | +import, +STRATEGY_REGISTRY entry |
| `v10/research/candidates.py` | EDITED | +import, +_FIELDS, +load_candidates, +build_strategy |
| `research/x0/search_log.md` | UPDATED | Added P3.2 section (~80 lines) |

## IMPLEMENTATION_DETAILS

### Strategy Structure (strategy.py)

Copy of Phase 2 (`vtrend_x0_e5exit`) with these additions:

1. **3 new config fields**: `target_vol=0.15`, `vol_lookback=120`, `vol_floor=0.08`
2. **1 new indicator**: `self._rv = _realized_vol(close, vol_lookback, BARS_PER_YEAR_4H)` in `on_init`
3. **1 new helper**: `_realized_vol(close, lookback, bars_per_year)` — copied from SM/LATCH
4. **Entry modification (lines 160-170)**:
   ```python
   rv_val = self._rv[i] if self._rv is not None else float('nan')
   if math.isnan(rv_val):
       weight = 1.0  # fallback: Phase 2 behavior
   else:
       weight = self._c.target_vol / max(rv_val, self._c.vol_floor)
       weight = max(0.0, min(1.0, weight))
   return Signal(target_exposure=weight, reason="x0_entry")
   ```

### What Did NOT Change (vs Phase 2)
- Entry conditions (trend_up AND vdo > threshold AND regime_ok)
- Exit logic (trail stop OR trend reversal)
- All indicator functions (_ema, _robust_atr, _vdo)
- D1 regime computation
- State variables (_in_position, _peak_price)
- Signal reasons (x0_entry, x0_trail_stop, x0_trend_exit)

## COMMANDS_RUN

```
python -m pytest tests/test_vtrend_x0_volsize.py -v    # 17/17 PASS
python -m pytest                                        # 889/889 PASS (40 warnings)
```

## RESULTS

### Test Results
- **Phase 3 tests**: 17/17 PASS (0.38s)
- **Full suite**: 889/889 PASS (86.79s, 40 warnings)
- **Warning delta**: +1 (RuntimeWarning from `np.log` in `_realized_vol` for bar 0 — expected, bar 0 has no prior close)

### Test Coverage by Acceptance Criteria (from P3.1)

| AC | Criterion | Test | Status |
|----|-----------|------|--------|
| AC1 | Entry timestamps identical to Phase 2 | TestEntryTimingParity | PASS |
| AC5 | Exit reasons identical | TestNoRebalance (checks signal sequence) | PASS |
| AC7 | No intratrade signals | TestNoRebalance | PASS |
| AC8 | rv NaN → weight=1.0 | TestRvNaNFallback | PASS |
| AC9 | Phase 2 tests still pass | Full suite 889/889 | PASS |
| AC10 | Weight formula correct | TestFractionalExposure, TestVolFloor | PASS |

### Remaining ACs (require engine-based backtest, deferred to P3.3)
| AC | Criterion | Needs |
|----|-----------|-------|
| AC2 | Exit timestamps identical | Engine-based comparison on real data |
| AC3 | Trade count identical | Engine-based comparison on real data |
| AC4 | Entry reasons identical | Engine-based comparison on real data |
| AC6 | PnL differences only from size | Engine-based trade matching |

## DEVIATION_FROM_SPEC

None. Implementation follows P3.1 frozen spec exactly:
- 13 config fields (10 inherited + 3 new)
- Entry timing identical (tested)
- rv NaN → weight=1.0 (tested)
- No rebalance (tested)
- _realized_vol from SM/LATCH (identical formula)
- All defaults match P3.1 frozen values

## NAMING

- P3.1 spec used `vtrend_x0_volsize`
- User suggested `vtrend_x0_volfreeze` as alternative
- Implementation uses `vtrend_x0_volsize` (matching P3.1 spec and directories)
- Mapping: `vtrend_x0_volsize` ≡ `vtrend_x0_volfreeze` (same strategy, just name)

## BLOCKERS

None.

## NEXT_READY

P3.2 implementation complete. Ready for P3.3 (parity verification + benchmark) when authorized.
Not proceeding.
