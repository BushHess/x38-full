# Nhiệm vụ D: Lookahead & Multi-Timeframe Leakage Sanity Check

**Test file:** `v10/tests/test_no_lookahead_htf.py` (new, 7 tests)
**Existing tests:** `v10/tests/test_mtf_alignment.py` (9 tests, pre-existing)
**Log:** `out_v11_validation_stepwise/lookahead_test.log`

---

## 1. Code Architecture: How D1 Bars Reach V11

```
CSV (H4+D1) → DataFeed → engine.run()
                              │
              ┌───────────────┴───────────────┐
              │ for each H4 bar:              │
              │   d1_idx = max i where        │
              │     d1[i].close_time           │
              │       < bar.close_time   ◄──── STRICT '<' (line 112)
              │                               │
              │   state.d1_index = d1_idx     │
              │   strategy.on_bar(state)      │
              └───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │ V11HybridStrategy.on_bar():   │
              │   d1i = state.d1_index        │
              │   _d1_cycle_phase[d1i]        │
              │   _d1_rsi[d1i]                │
              │   _d1_ema200[d1i]             │
              │   _d1_adx[d1i]               │
              │   _d1_regime[d1i]             │
              │   _d1_vol_ann[d1i]            │
              └───────────────────────────────┘
```

### Critical alignment rule (`v10/core/engine.py:110-113`):

```python
while (
    d1_idx + 1 < len(d1)
    and d1[d1_idx + 1].close_time < bar.close_time  # STRICT '<'
):
    d1_idx += 1
```

This ensures `d1_bars[d1_idx]` is always the **last completed** D1 bar — never the current in-progress one. At the exact boundary (last H4 of day N has `close_time == d1[N].close_time`), the strict `<` prevents day N's D1 from being visible.

### W1 (Weekly) bars: **Not used**

V11 does not use weekly bars. Only H4 (primary) and D1 (higher-timeframe) are used.

---

## 2. V11-Specific D1 Access Audit

All D1 indicator accesses in `v11_hybrid.py`, every one uses `d1i = state.d1_index`:

| Location | Array | Index | Bounds Check | Risk |
|----------|-------|-------|-------------|------|
| Line 432 | `_d1_rsi[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 436 | `_d1_ema200[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 482 | `_d1_adx[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 520 | `_d1_regime[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 581 | `_d1_cycle_phase[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 665 | `_d1_vol_ann[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 702 | `_d1_cycle_phase[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |
| Line 743 | `_d1_cycle_phase[d1i]` | `d1i` | `0 <= d1i < len()` | NONE |

**No D1 access uses `d1i + 1` or any future-looking index.** Confirmed by automated regex scan (Test 5).

---

## 3. Automated Tests

### 3.1 New V11-Specific Tests (`test_no_lookahead_htf.py`)

| # | Test | Type | What it verifies | Result |
|---|------|------|-----------------|--------|
| 1 | `test_cycle_phase_uses_lagged_d1` | Synthetic | V11 cycle phase on 260-day data: every d1.close_time < h4.close_time | **PASS** |
| 2 | `test_indicator_array_bounds` | Synthetic | All V11 features enabled (MR+cycle+ADX): d1_index always within array bounds | **PASS** |
| 3 | `test_d1_always_behind_h4_real_data` | **Real data** | 1 year BTCUSDT (2024): every mtf_map entry has d1_ct < h4_ct | **PASS** |
| 4 | `test_d1_index_never_exceeds_current_day` | **Real data** | 1 year BTCUSDT: V11 strategy's d1_index always points to completed D1 | **PASS** |
| 5 | `test_d1_index_never_decreases` | Synthetic | d1_index monotonically non-decreasing across 600 H4 bars | **PASS** |
| 6 | `test_no_future_d1_access_pattern` | **Static analysis** | Regex scan of v11_hybrid.py: no `d1i+1`, `d1_index+N` patterns in trading methods | **PASS** |
| 7 | `test_all_d1_accesses_use_d1i_from_state` | **Static analysis** | on_bar assigns `d1i = state.d1_index`; helper methods accept `d1i: int` param | **PASS** |

### 3.2 Pre-Existing Engine Tests (`test_mtf_alignment.py`)

| # | Test | Result |
|---|------|--------|
| 1 | Day 0: no D1 available → d1_index = -1 | **PASS** |
| 2 | D1_index=-1 via mtf_map | **PASS** |
| 3 | Last H4 of day N uses D1 of day N-1 | **PASS** |
| 4 | Boundary exact timestamps (close_time equality case) | **PASS** |
| 5 | d1_index sequence across 4 days | **PASS** |
| 6 | mtf_map matches strategy view | **PASS** |
| 7 | mtf_map disabled by default | **PASS** |
| 8 | No D1 bars → graceful handling | **PASS** |
| 9 | Strategy sees lagged D1 close price (not today's) | **PASS** |

### Total: **16/16 PASSED**

---

## 4. Verdict

### **PASS — No look-ahead bias detected**

Evidence:
1. **Engine implementation** is correct: strict `<` comparison at line 112 prevents same-candle D1 access
2. **V11 strategy** uses only `d1i = state.d1_index` from engine — no independent D1 index computation
3. **All 8 D1 array accesses** in V11 are bounds-checked and use the engine-provided index
4. **Static code analysis** confirms no `d1i + N` patterns in trading methods
5. **Real data integration test** on 1 year of BTCUSDT confirms zero violations across ~2,200 H4 bars
6. **Pre-existing engine tests** (9 tests) confirm the MTF alignment mechanism is correct
7. **W1 (weekly) bars are not used** by V11 — no W1 leakage possible

---

## 5. Data Files

| File | Mô tả |
|------|--------|
| `v10/tests/test_no_lookahead_htf.py` | 7 new V11-specific lookahead tests |
| `v10/tests/test_mtf_alignment.py` | 9 pre-existing engine MTF tests |
| `out_v11_validation_stepwise/lookahead_test.log` | pytest output (16/16 passed) |
| `out_v11_validation_stepwise/reports/lookahead_sanity.md` | This report |
