# P3.3 — Verification + Timing Parity Audit Report

## SUMMARY

Four-layer audit of X0 Phase 3 (`vtrend_x0_volsize`) against X0 Phase 2 (`vtrend_x0_e5exit`).
All 4 layers PASS. Signal and trade timestamps are parity-clean against X0 Phase 2;
Phase 3 changes economic exposure only. Zero bugs found. Zero code changes needed.

Key finding: BTC's realized vol (min 0.141 annualized) always exceeds target_vol=0.15
during the reporting window, so all 217 trades have fractional weight (max 0.419, median 0.042).
No trade ever reaches weight=1.0. The rv NaN fallback never triggers.

## FILES_INSPECTED

| File | Purpose | Key Finding |
|------|---------|-------------|
| `strategies/vtrend_x0_e5exit/strategy.py` | Phase 2 baseline | Entry: target_exposure=1.0 |
| `strategies/vtrend_x0_volsize/strategy.py` | Phase 3 implementation | Entry: target_exposure=weight |
| `v10/core/engine.py` | BacktestEngine | `_apply_target_exposure` handles fractional correctly |
| `v10/core/execution.py` | Portfolio | buy/sell scale with qty, fees proportional |
| `research/x0/parity_audit_p3_3.py` | Audit script | 4-layer verification |
| `research/x0/p3_3_results.json` | Audit results | All layers pass |

## FILES_CHANGED

| File | Action | Detail |
|------|--------|--------|
| `research/x0/parity_audit_p3_3.py` | CREATED | 4-layer audit script (~650 lines) |
| `research/x0/p3_3_results.json` | CREATED | JSON results payload |
| `research/x0/search_log.md` | UPDATED | Added P3.3 section (~90 lines) |

No strategy, config, test, or registration files were modified. This is a verification-only phase.

## BASELINE_MAPPING

| Entity | Source | Role in P3.3 |
|--------|--------|-------------|
| X0 Phase 2 (`vtrend_x0_e5exit`) | `strategies/vtrend_x0_e5exit/` | Timing baseline (all timestamps) |
| X0 Phase 3 (`vtrend_x0_volsize`) | `strategies/vtrend_x0_volsize/` | Implementation under test |
| BacktestEngine | `v10/core/engine.py` | Executes both strategies identically |
| base cost scenario | `v10/core/types.py` SCENARIOS | 31 bps RT |

## COMMANDS_RUN

```
python -m pytest tests/test_vtrend_x0_volsize.py tests/test_vtrend_x0_e5exit.py -v   # 34/34 PASS
python research/x0/parity_audit_p3_3.py                                                # ALL CHECKS PASS
```

## RESULTS

### TEST_STATUS_TABLE

| Test Suite | Tests | Status |
|-----------|-------|--------|
| test_vtrend_x0_volsize.py | 17/17 | PASS |
| test_vtrend_x0_e5exit.py | 17/17 | PASS |
| Full suite (python -m pytest) | 889/889 | PASS (from P3.2) |

### RAW_ENTRY_PARITY_RESULT

**CLEAN** — All 9 entry-side indicators BIT-IDENTICAL (18,662 values each):

| Indicator | Comparison | Result |
|-----------|-----------|--------|
| ema_fast (standalone) | P2 vs P3 | BIT-IDENTICAL |
| ema_slow (standalone) | P2 vs P3 | BIT-IDENTICAL |
| vdo (standalone) | P2 vs P3 | BIT-IDENTICAL |
| ratr (standalone) | P2 vs P3 | BIT-IDENTICAL |
| ema_fast (strategy) | P2 vs P3 | BIT-IDENTICAL |
| ema_slow (strategy) | P2 vs P3 | BIT-IDENTICAL |
| ratr (strategy) | P2 vs P3 | BIT-IDENTICAL |
| vdo (strategy) | P2 vs P3 | BIT-IDENTICAL |
| d1_regime_ok | P2 vs P3 | BIT-IDENTICAL |

Entry conditions evaluate identically at every bar. The only difference
is the `target_exposure` value emitted on entry (1.0 vs weight).

### RAW_EXIT_PARITY_RESULT

**CLEAN** — Exit indicators (ratr) are BIT-IDENTICAL. Exit logic path
(`price < peak - trail_mult * ratr` or `ema_f < ema_s`) is identical
in both strategies. The `_in_position` and `_peak_price` state variables
follow the same transitions since entry/exit timing is the same.

### TRADE_TIMESTAMP_PARITY_RESULT

**CLEAN — 0 timestamp diffs across 217 trades.**

| Metric | P2 | P3 | Match |
|--------|-----|-----|-------|
| Trade count | 217 | 217 | YES |
| Fill count | 434 | 434 | YES |
| Entry timestamp match | 217/217 | — | ALL |
| Exit timestamp match | 217/217 | — | ALL |
| Reason match | 217/217 | — | ALL |
| Win rate | 43.78% | 43.78% | YES |
| Avg days held | 6.1 | 6.1 | YES |
| Time in market | 42.55% | 42.55% | YES |

Signal debug window (first 500 bars): 0 timing diffs, 4 exposure-only diffs (expected).
Example: bar[124]: P2=x0_entry(1.0) vs P3=x0_entry(0.181) — same timing, different size.

### EXPOSURE_DISTRIBUTION_SUMMARY

Weight distribution across all 217 entry fills (P3_qty / P2_qty ratio):

| Statistic | Value |
|-----------|-------|
| n | 217 |
| min | 0.0163 |
| p10 | 0.0202 |
| median | 0.0416 |
| mean | 0.0677 |
| p90 | 0.1556 |
| max | 0.4185 |
| At cap (w >= 1.0) | 0 (0.0%) |
| Fractional (0 < w < 1) | 217 (100.0%) |

**All 217 trades are fractional.** BTC's annualized realized vol (min 0.141)
always exceeds target_vol=0.15 in the reporting window. Only 16/18,542 bars (0.1%)
have rv < 0.15, and none coincide with entry signals.

This means:
- The vol-sizing mechanism is always active (never degenerates to Phase 2 behavior)
- Average entry weight is 6.8% of full allocation
- Median entry weight is 4.2% — very conservative sizing given BTC's high vol

### FRACTIONAL_COST_ENGINE_AUDIT

**CLEAN — no side-effects from fractional exposure.**

| Check | Count | Result |
|-------|-------|--------|
| Fee proportionality (fee_ratio = notional_ratio) | 434/434 | PASS |
| Fill price match (same bar → same price) | 434/434 | ALL MATCH |
| Fill timestamp match | 434/434 | ALL MATCH |
| Fill reason match | 434/434 | ALL MATCH |
| Fill side match | 434/434 | ALL MATCH |

Fee totals: P2=$111,888, P3=$3,905 — proportional to notional traded.
Fee drag: P2=5.04%/yr, P3=1.67%/yr — lower drag from smaller positions.

### FIRST_DIFFS_IF_ANY

**None.** Zero timestamp diffs between Phase 2 and Phase 3:
- 0 entry timestamp diffs
- 0 exit timestamp diffs
- 0 reason diffs
- 0 fill timestamp diffs
- 0 fill price diffs

### ROOT_CAUSE_ANALYSIS

**Not applicable** — no diffs found. Timing parity is structurally guaranteed because:

1. Entry conditions (`trend_up AND vdo > threshold AND regime_ok`) are code-identical
2. Exit conditions (`price < trail_stop` or `trend_down`) are code-identical
3. `_in_position` boolean state follows the same transitions
4. The only change is `Signal(target_exposure=weight)` vs `Signal(target_exposure=1.0)`
5. Engine processes both identically — `_apply_target_exposure` converts to buy/sell qty
   but doesn't affect signal timing or state

### FINAL_PHASE3_IMPLEMENTATION_STATUS

**Signal and trade timestamps are parity-clean against X0 Phase 2;
Phase 3 changes economic exposure only.**

| AC # | Criterion | Status |
|------|-----------|--------|
| AC1 | Entry timestamps IDENTICAL to Phase 2 | PASS (217/217) |
| AC2 | Exit timestamps IDENTICAL to Phase 2 | PASS (217/217) |
| AC3 | Trade count IDENTICAL to Phase 2 | PASS (217 = 217) |
| AC4 | Entry reasons IDENTICAL | PASS (217/217, all "x0_entry") |
| AC5 | Exit reasons IDENTICAL | PASS (217/217) |
| AC6 | PnL differences ONLY from size | PASS (same prices, proportional PnL) |
| AC7 | No intratrade signals | PASS (434 fills = 2 * 217 trades) |
| AC8 | rv NaN → weight=1.0 | N/A (never triggered; rv valid from bar 120) |
| AC9 | All Phase 2 tests still pass | PASS (889/889) |
| AC10 | Weight formula correct | PASS (verified per-fill) |

**All 10 acceptance criteria: PASS.**

## BLOCKERS

None.

## NEXT_READY

P3.3 verification complete. Phase 3 implementation is parity-clean and ready for
P3.4 (full benchmark + bootstrap) when authorized. Not proceeding.
