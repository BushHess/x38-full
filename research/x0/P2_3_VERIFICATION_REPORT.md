# P2.3 — X0 Phase 2 Verification & Differential Audit Report

## SUMMARY

Three-layer differential audit confirms X0 Phase 2 implementation is correct:
- **Entry parity**: BIT-IDENTICAL to X0 Phase 1 (7/7 indicators, 18,662 values each)
- **Exit delta**: 74/180 matched trades exit differently (expected — different ATR)
- **E5 transplant**: BIT-IDENTICAL to E5+EMA21 (217/217 trades, all metrics match)

Zero bugs found. Zero code changes needed. Zero deviations from spec.

## FILES_INSPECTED

| File | Purpose |
|------|---------|
| `strategies/vtrend_x0/strategy.py` | X0 Phase 1 — entry parity source |
| `strategies/vtrend_x0_e5exit/strategy.py` | X0 Phase 2 — audit target |
| `strategies/vtrend_e5/strategy.py` | E5 — _robust_atr source |
| `strategies/vtrend_e5_ema21_d1/strategy.py` | E5+EMA21 — parity target |
| `v10/core/types.py` | Trade/Fill dataclass fields |
| `research/x0/parity_audit_p1_3.py` | P1.3 audit script (pattern reference) |

## FILES_CHANGED

| File | Action | Lines |
|------|--------|-------|
| `research/x0/parity_audit_p2_3.py` | CREATED | ~310 |
| `research/x0/p2_3_results.json` | CREATED (output) | ~30 |
| `research/x0/search_log.md` | UPDATED | +40 lines (P2.3 section) |

No strategy, config, or registration files were modified.

## BASELINE_MAPPING

| Audit Layer | Comparison Pair | Expected Outcome |
|-------------|-----------------|------------------|
| A (entry) | X0 Phase 2 vs X0 Phase 1 | IDENTICAL |
| B (executed) | X0 Phase 2 vs X0 Phase 1 | DIFFERENT (exit ATR changed) |
| C (exit) | Matched-entry trades | EXIT TIMES DIFFER |
| E5 transplant | X0 Phase 2 vs E5+EMA21 | IDENTICAL |

## COMMANDS_RUN

```
# Phase 1 + Phase 2 tests
python -m pytest tests/test_vtrend_x0_e5exit.py tests/test_vtrend_x0.py -v --tb=short
# Result: 34/34 PASS

# P2.3 parity audit
python research/x0/parity_audit_p2_3.py
# Result: ALL CHECKS PASS
```

## RESULTS

### TEST_STATUS_TABLE

| Test Suite | Tests | Status |
|-----------|-------|--------|
| tests/test_vtrend_x0.py | 17 | PASS |
| tests/test_vtrend_x0_e5exit.py | 17 | PASS |
| Full suite (python -m pytest) | 872 | PASS (39 pre-existing warnings) |

### RAW_ENTRY_PARITY_RESULT

**Raw entry logic is parity-clean against X0 Phase 1.**

| Indicator | Values | Result |
|-----------|--------|--------|
| ema_fast (standalone) | 18,662 | BIT-IDENTICAL |
| ema_slow (standalone) | 18,662 | BIT-IDENTICAL |
| vdo (standalone) | 18,662 | BIT-IDENTICAL |
| ema_fast (strategy) | 18,662 | BIT-IDENTICAL |
| ema_slow (strategy) | 18,662 | BIT-IDENTICAL |
| vdo (strategy) | 18,662 | BIT-IDENTICAL |
| d1_regime_ok | 18,662 | BIT-IDENTICAL |

ATR vs rATR confirmation: max_diff=1321.43, mean_diff=60.30, 0 identical values.
This confirms the ONLY indicator difference is the exit-side ATR computation.

### EXECUTED_TRADE_DIFF_SUMMARY

| Metric | P1 (X0) | P2 (X0-E5) | Delta |
|--------|---------|------------|-------|
| Trades | 201 | 217 | +16 |
| Sharpe | 1.270 | 1.422 | +0.152 |
| CAGR% | 56.51 | 65.25 | +8.74 |
| MDD% | 54.63 | 46.08 | -8.55 |
| Calmar | 1.034 | 1.416 | +0.382 |
| Win rate% | 42.29 | 43.78 | +1.49 |
| Profit factor | 1.792 | 1.878 | +0.085 |
| Avg trade PnL | 2377.62 | 3528.54 | +1150.92 |
| Avg exposure | 0.437 | 0.426 | -0.012 |
| Turnover/yr | 47.01 | 50.43 | +3.42 |

Debug window (first 500 bars): 14 signal differences, all from exit-timing cascade.
First diff at bar 87: P1 enters (standard ATR-14 valid at bar 13), P2 skips (rATR NaN until bar 119).

### MATCHED_ENTRY_EXIT_DELTA_AUDIT

| Metric | Value |
|--------|-------|
| P1 trades | 201 |
| P2 trades | 217 |
| Matched by entry_ts | 180 |
| Same exit timestamp | 106 (58.9%) |
| Different exit | 74 (41.1%) |
| P1-only entries | 21 |
| P2-only entries | 37 |

Exit diff statistics (P2 - P1, on 74 differing trades):
| Statistic | Hold period (hours) | Return (%) |
|-----------|-------------------|------------|
| Mean | -41.9 | -0.421 |
| Median | -12.0 | +0.487 |
| Min | -320.0 | -51.129 |
| Max | +108.0 | +15.677 |

Exit reason breakdown (74 diffs):
- P1: trail_stop=73, trend_exit=1
- P2: trail_stop=74

Interpretation: robust ATR trail is tighter on average → shorter holds, but catches more
of the move before reversal (positive median return delta despite shorter hold).

### E5_EXIT_TRANSPLANT_VALIDATION

| Check | Result |
|-------|--------|
| `_robust_atr` function output | BIT-IDENTICAL (18,543 valid values) |
| ema_fast (strategy) | BIT-IDENTICAL |
| ema_slow (strategy) | BIT-IDENTICAL |
| ratr (strategy) | BIT-IDENTICAL |
| vdo (strategy) | BIT-IDENTICAL |
| d1_regime_ok (strategy) | BIT-IDENTICAL |
| Trade count | 217 vs 217 (SAME) |
| Trade-by-trade | 217/217 BIT-IDENTICAL |
| Sharpe | 1.4221 vs 1.4221 (MATCH) |
| CAGR% | 65.25 vs 65.25 (MATCH) |
| MDD% | 46.08 vs 46.08 (MATCH) |

**X0 Phase 2 is parity-clean against E5+EMA21.**

### FIRST_DIFFS_IF_ANY

First signal diff in debug window:
- **Bar 87**: P1 emits `x0_entry(1.0)`, P2 emits `None`
- Root cause: standard ATR(14) is valid at bar 13; robust ATR(cap_lb=100, period=20) is NaN until bar 119
- At bar 87, P1 has valid ATR → entry guard passes; P2 has NaN rATR → NaN guard returns None
- This is correct behavior: rATR requires 120 bars of history before first valid value

All subsequent diffs cascade from this first divergence point.

### ROOT_CAUSE_ANALYSIS

No bugs found. All differences are expected and explained by the single design change:
replacing `_atr(period=14)` with `_robust_atr(cap_lb=100, period=20)`.

**Causal chain:**
1. rATR has longer warmup (119 bars vs 13 bars) → P2 skips early entries that P1 takes
2. Different ATR values → different trail stop levels → different exit timing on 74/180 matched trades
3. Different exit timing → different re-entry timing → 21 P1-only entries, 37 P2-only entries
4. Net effect: +16 trades, +0.152 Sharpe, +8.74% CAGR, -8.55% MDD

No entry-side logic drift. No indicator contamination. No state management bugs.

### FINAL_PHASE2_IMPLEMENTATION_STATUS

| Gate | Status |
|------|--------|
| Entry parity vs Phase 1 | PASS (BIT-IDENTICAL, 7/7 indicators) |
| Exit uses robust ATR (not standard) | PASS (confirmed different) |
| Full parity vs E5+EMA21 | PASS (BIT-IDENTICAL, 217/217 trades) |
| Tests | PASS (34/34 X0 tests, 872/872 full suite) |
| No bugs found | PASS |
| No code changes needed | PASS |
| No baseline files modified | PASS |
| No deviations from spec | PASS |

**Phase 2 implementation is verified and clean.**

## BLOCKERS

None.

## NEXT_READY

P2.3 audit complete. Ready for P2.4 (full benchmark + bootstrap of X0 Phase 2)
when authorized. Not proceeding.
