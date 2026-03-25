# V10 Lookahead / Leakage Sanity Check

**Test file:** `v10/tests/test_v10_no_lookahead_htf.py`
**Engine tests:** `v10/tests/test_mtf_alignment.py`
**Log:** `out_v10_full_validation_stepwise/v10_lookahead_test.log`
**Result:** **PASS** — 20/20 tests pass, zero lookahead detected

---

## 1. V10 HTF Access Pattern

V8ApexStrategy uses D1 (daily) data in exactly **2 places**, both in `on_bar()`:

| D1 Array | File:Line | Purpose | Guard |
|----------|-----------|---------|-------|
| `_d1_regime[d1i]` | `v8_apex.py:306` | Regime gating (RISK_ON/RISK_OFF/CAUTION) | `0 <= d1i < len(self._d1_regime)` |
| `_d1_vol_ann[d1i]` | `v8_apex.py:412` | Annualized volatility for position sizing | `0 <= d1i < len(self._d1_vol_ann)` |

Both arrays are **pre-computed in `on_init()`** from complete D1 bars (lines 234-244). The index `d1i = state.d1_index` comes exclusively from the engine's alignment logic.

---

## 2. Engine Alignment Mechanism

`BacktestEngine.run()` at `engine.py:110-114`:

```python
while (
    d1_idx + 1 < len(d1)
    and d1[d1_idx + 1].close_time < bar.close_time   # STRICT <
):
    d1_idx += 1
```

**Key guarantee:** Strict `<` (not `<=`). Since the last H4 bar of day N and D1 of day N share the same `close_time`, the strict comparison ensures day N's H4 bars **never** see day N's D1 — only day N-1's.

---

## 3. Test Suite

### 3.1 V10-Specific Tests (11 tests)

| # | Test | Type | What it verifies |
|---|------|------|-----------------|
| 1 | `TestV10RegimeNoLookahead::test_regime_uses_lagged_d1` | Synthetic | V10 sees D1[N-1] on day N, never D1[N] |
| 2 | `TestV10IndicatorIndexing::test_indicator_array_bounds` | Synthetic | d1_index always within `_d1_regime` and `_d1_vol_ann` bounds |
| 3 | `TestV10RealDataTimestampAlignment::test_d1_always_behind_h4_real_data` | Integration | Real BTCUSDT 2024: `d1.close_time < h4.close_time` ∀ bars |
| 4 | `TestV10RealDataTimestampAlignment::test_d1_index_tracks_correctly_real_data` | Integration | Real data: D1 bar used by V10 always closed before H4 bar |
| 5 | `TestV10D1IndexMonotonicity::test_d1_index_never_decreases` | Synthetic | d1_index is monotonically non-decreasing |
| 6 | `TestV10CodeAuditNoBeyondD1Index::test_no_future_d1_access_pattern` | Static | No `d1i + 1`, `d1_index + N` patterns in v8_apex.py |
| 7 | `TestV10CodeAuditNoBeyondD1Index::test_d1i_comes_from_state` | Static | `d1i = state.d1_index` in on_bar |
| 8 | `TestV10CodeAuditNoBeyondD1Index::test_d1_arrays_exactly_two` | Static | V8Apex has exactly 2 D1 arrays (catches new additions) |
| 9 | `TestV10CodeAuditNoBeyondD1Index::test_all_d1_access_is_bounds_checked` | Static | Every D1 array access has `0 <= d1i < len(...)` guard |
| 10 | `TestV10BoundaryRegime::test_last_h4_uses_previous_day_regime` | Synthetic | Last H4 of day N with price crash does NOT see crash regime |
| 11 | `TestV10D1LagMatters::test_removing_d1_changes_behavior` | Integration | Removing D1 changes V10 behavior → D1 alignment matters |

### 3.2 Engine-Level MTF Alignment Tests (9 tests)

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | `TestNoD1BeforeFirstClose::test_day0_all_slots` | No D1 available on day 0 |
| 2 | `TestNoD1BeforeFirstClose::test_d1_index_is_minus_one` | d1_index = -1 for day-0 bars |
| 3 | `TestDayBoundaryNoLookahead::test_last_h4_uses_previous_day_d1` | Last H4 of day N sees D1 of day N-1 (price verified) |
| 4 | `TestDayBoundaryNoLookahead::test_boundary_exact_timestamps` | Exact timestamp comparison at boundary |
| 5 | `TestD1IndexMapping::test_expected_d1_index_sequence` | Correct d1_index sequence: [-1]*6, [0]*6, [1]*6, [2]*6 |
| 6 | `TestMtfMapOutput::test_mtf_map_matches_strategy_view` | Engine mtf_map matches what strategy observes |
| 7 | `TestMtfMapOutput::test_mtf_map_disabled_by_default` | mtf_map empty when not requested |
| 8 | `TestNoD1Bars::test_no_d1_bars` | Graceful handling with no D1 data |
| 9 | `TestLookaheadSensitiveStrategy::test_strategy_sees_lagged_d1_close` | Price value test: sees 10k (yesterday), not 20k (today) |

---

## 4. Results

```
v10/tests/test_v10_no_lookahead_htf.py   11 passed   1.68s
v10/tests/test_mtf_alignment.py           9 passed   0.27s
──────────────────────────────────────────────────────
TOTAL                                    20 passed   1.95s
```

---

## 5. Conclusion

### VERDICT: **PASS — No lookahead / leakage detected**

1. **Design**: Engine uses strict `<` timestamp comparison for D1→H4 alignment (engine.py:112)
2. **Implementation**: V8Apex accesses exactly 2 D1 arrays, both bounds-checked, both indexed by `state.d1_index` from engine
3. **Static audit**: No forward-indexing patterns (`d1i + N`) found in v8_apex.py
4. **Synthetic tests**: Day boundary, monotonicity, regime lag all verified
5. **Integration tests**: Real BTCUSDT data (2024-01-01 to 2025-01-01) — zero violations across all H4 bars
6. **D1 materiality**: Removing D1 regime gating changes V10 behavior, confirming the alignment matters

V10's D1 feature usage is identical in architecture to V11's — both use the same engine alignment mechanism. The test coverage is comprehensive: synthetic boundary cases, real data integration, static code audit, and behavioral verification.
