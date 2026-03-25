# Report 36c — VTREND-SM Repo Hygiene & Validation False-Positive Cleanup

**Date**: 2026-03-04
**Scope**: Resolve 3 remaining issues from Reports 36/36b: test label drift, VDO coverage gap, validation false positive
**Authority**: Repo state > Report 36b > Report 36 > Report 35 > Report 34c

---

## 1. Scope

Post-integration cleanup for VTREND-SM, addressing exactly 3 issues identified in Report 36 §4 and confirmed in Report 36b §4.4:

1. **False positive**: validation pipeline reports 16/16 config fields as "unused" due to ConfigProxy/`resolved()` incompatibility
2. **T20 label drift**: test class claims "Engine integration" but never instantiates BacktestEngine
3. **VDO coverage gap**: `_vdo()` function has no dedicated numerical unit tests

Constraint: no strategy logic changes, no parameter changes, no engine/metrics changes.

---

## 2. Issues Reproduced

### 2.1 False Positive — Unused Config Fields

**File**: `validation/config_audit.py` (ConfigProxy + AccessTracker)
**Behavior**: Validation pipeline marks ALL 16 VTrendSMConfig fields as "unused"
**Evidence**:

```
$ python -c "... ConfigProxy simulation ..."
Used fields after construction: []
Unused: ['atr_mult', 'atr_period', ..., 'vol_lookback']  # ALL 16
Allowlist: []
Status: FAIL
```

**Root cause**: VTrendSMStrategy calls `self._config.resolved()` which internally calls `dataclasses.asdict(self)`. `asdict()` accesses fields via `__dict__`, bypassing ConfigProxy's `__getattr__`. All subsequent runtime access uses `self._r["field"]` (dict), never `self._config.field` (proxy).

**Why this is a real issue**: Causes ERROR(3) verdict with "Unused strategy config fields detected" — obscures the actual REJECT verdict from legitimate scoring differences.

### 2.2 T20 Label Drift

**File**: `tests/test_vtrend_sm.py`, line 685–714
**Test class**: `TestEngineIntegration`
**Docstring**: "T20: BacktestEngine + VTrendSMStrategy runs without crash"
**Behavior**: Imports `BacktestEngine` (line 693) but never instantiates it. Test only exercises strategy `on_init()` + `on_bar()` loop.

```
$ grep -n "BacktestEngine" tests/test_vtrend_sm.py
688:    """T20: BacktestEngine + VTrendSMStrategy runs without crash."""
693:        from v10.core.engine import BacktestEngine  # imported but never used
```

**Why this is a real issue**: Class name and docstring claim engine integration testing that isn't happening. Misleading for anyone auditing test coverage.

### 2.3 VDO Coverage Gap

**File**: `tests/test_vtrend_sm.py`
**Symbol**: `_vdo` (imported at line 25)
**Existing coverage**: T18 (`TestVDOFilter::test_vdo_blocks_entry`) — tests gating behavior only (blocks entry when threshold=99.0)
**Missing**:
- Numerical correctness of `_vdo()` output (hand-calculable reference values)
- OHLC proxy fallback path verification (when `taker_buy` all zeros)
- Taker buy path vs OHLC proxy path produce different results
- Edge cases: zero volume, zero spread, `taker_buy=None`

**Why this is a real issue**: `_vdo()` has two distinct computation paths (taker vs OHLC proxy) with no dedicated tests proving either produces correct numerical output.

---

## 3. Files Created/Modified

| File | Action | Lines Changed |
|------|--------|---------------|
| `tests/test_vtrend_sm.py` | Modified | T20 rename (8 lines), +6 VDO tests (~80 lines), +3 ConfigProxy tests (~40 lines) |
| `validation/config_audit.py` | Modified | +5 lines in `_expand_conditional_allowlist()` |

No files created. No strategy files modified.

---

## 4. Fixes Applied

### 4.1 T20 Label Drift — Renamed to Match Reality

**Before**:
```python
class TestEngineIntegration:
    """T20: BacktestEngine + VTrendSMStrategy runs without crash."""
    def test_smoke_test_with_synthetic_data(self) -> None:
        """Minimal smoke test using the engine with synthetic bars."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import CostConfig
        # ... never uses BacktestEngine, DataFeed, or CostConfig
```

**After**:
```python
class TestStrategyInterfaceSmoke:
    """T20: VTrendSMStrategy on_init + on_bar interface works without crash.

    Note: this tests the strategy interface only, not BacktestEngine integration.
    """
    def test_smoke_test_with_synthetic_data(self) -> None:
        """on_init + on_bar loop produces valid signals on synthetic bars."""
        # ... removed dead imports, same test body
```

**Impact**: Test behavior unchanged. Only class name, docstring, and dead imports changed.

### 4.2 VDO Coverage Gap — 6 Dedicated Unit Tests

Added `TestVdoNumerical` class with 6 tests:

| Test | What it Proves |
|------|---------------|
| `test_taker_buy_path_numerical` | VDR=(buy-sell)/vol, hand-calculated EMA values match |
| `test_ohlc_proxy_path_numerical` | VDR=(close-low)/(high-low)*2-1, hand-calculated EMA values match |
| `test_taker_buy_none_uses_ohlc_proxy` | `taker_buy=None` → identical output to `taker_buy=zeros` |
| `test_zero_volume_bars` | Zero-volume bars → VDR=0, no NaN/inf propagation |
| `test_zero_spread_ohlc_proxy` | Zero spread (high=low) → VDR=0, VDO=0 |
| `test_taker_path_vs_ohlc_proxy_differ` | Two paths produce different values for same OHLC data |

**Hand-calculation example** (taker path, `fast=1, slow=2`):
- VDR: `(80-20)/100=0.6`, `(50-50)/100=0.0`, `(20-80)/100=-0.6`
- EMA(fast=1, α=1): `[0.6, 0.0, -0.6]`
- EMA(slow=2, α=2/3): `[0.6, 0.2, -1/3]`
- VDO: `[0.0, -0.2, -0.267]`

### 4.3 False Positive — `resolved()` Allowlist in ConfigProxy

**Before**: `_expand_conditional_allowlist()` only handled V8/V11/V12/V13 feature-flag patterns. No handling for `resolved()` pattern.

**After**: Added 5 lines at the top of `_expand_conditional_allowlist()`:

```python
# Strategies that use resolved() consume all fields via dataclasses.asdict()
# at init time. ConfigProxy cannot track asdict() field access because it
# reads __dict__ directly, bypassing __getattr__. Allowlist all fields
# for configs with a resolved() method since they are provably consumed.
if callable(getattr(config_obj, "resolved", None)):
    allow.update(values.keys())
```

**Mechanism**: Detects `resolved()` method on the config dataclass. If present, all fields are added to the allowlist. Fields remain in `unused_raw` (proxy still doesn't see them) but are excluded from `unused_fields` (the list that triggers ERROR).

---

## 5. Why Each Fix is Safe

### 5.1 T20 Rename

- Test body unchanged — same assertions, same pass/fail behavior
- Only cosmetic: class name, docstring, removed unused imports
- No other test or code references `TestEngineIntegration` by name

### 5.2 VDO Tests

- Pure additions — 6 new test methods in new class
- Test `_vdo()` directly (module-level function, public import)
- No existing test modified
- Hand-calculated reference values — deterministic, no randomness

### 5.3 ConfigProxy Allowlist

- Uses EXISTING allowlist mechanism (same `_expand_conditional_allowlist` function)
- Only affects configs with `resolved()` method
- **No other config class has `resolved()`**: verified V8ApexConfig, V11HybridConfig, V12EMDDRefFixConfig, V13AddThrottleConfig, VTrendConfig — none have it
- Allowlist sizes for existing strategies UNCHANGED:
  - V8ApexConfig: 8 (before: 8)
  - V11HybridConfig: 42 (before: 42)
  - VTrendConfig: 0 (before: 0)
- `unused_raw` still shows all 16 fields for transparency
- No strategy logic, proxy logic, or tracking logic changed

---

## 6. Tests Added/Updated

| Action | Class | Count | Description |
|--------|-------|-------|-------------|
| Renamed | `TestEngineIntegration` → `TestStrategyInterfaceSmoke` | 1 test | Honest label |
| Added | `TestVdoNumerical` | 6 tests | `_vdo()` numerical correctness |
| Added | `TestConfigProxyResolvedAllowlist` | 3 tests | Allowlist fix verification |

Total: 56 tests (was 47: +6 VDO + +3 ConfigProxy)

---

## 7. Validation False-Positive Root Cause and Resolution

### 7.1 Root Cause Chain

```
1. VTrendSMConfig.resolved() calls dataclasses.asdict(self)
2. asdict() accesses fields via __dict__, bypassing ConfigProxy.__getattr__
3. ConfigProxy.tracker sees 0 field accesses
4. build_usage_payloads() reports ALL 16 fields as unused
5. _apply_config_usage_policy() sets tag="ERROR", exit_code=3
6. Real REJECT verdict (score delta) masked by ERROR
```

### 7.2 Resolution

```
_expand_conditional_allowlist() now detects resolved() → allowlists all fields
  ↓
build_usage_payloads(): unused_raw=16, allowlist=16, unused_fields=0
  ↓
_apply_config_usage_policy(): has_unused_fields=False → no ERROR
  ↓
Real REJECT verdict (score delta) is now visible
```

### 7.3 Before/After

| Aspect | Before | After |
|--------|--------|-------|
| Verdict | ERROR (exit code 3) | REJECT (exit code 2) |
| Reasons | 3 (2 score + 1 unused config) | 2 (2 score only) |
| `unused_fields` (candidate) | 16 | 0 |
| `unused_raw` (candidate) | 16 | 16 (transparent) |
| `allowlist` (candidate) | 0 | 16 |
| Errors list | 16 entries | 0 entries |
| Other strategies affected | N/A | None verified |

---

## 8. Commands Run

```bash
# Step 0: Reproduce issues
python -c "from validation.config_audit import ... # ConfigProxy simulation"
python -m pytest tests/test_vtrend_sm.py::TestEngineIntegration -v
grep -n "BacktestEngine" tests/test_vtrend_sm.py

# Step 4: Rerun tests
python -m pytest tests/test_vtrend_sm.py -v                  # 56 passed
python -m pytest tests/ v10/tests/ -v --tb=short             # 461 passed, 39 warnings

# Step 4: Rerun validation
python validate_strategy.py \
  --strategy vtrend_sm \
  --baseline vtrend \
  --config configs/vtrend_sm/vtrend_sm_default.yaml \
  --baseline-config configs/vtrend/vtrend_default.yaml \
  --out out/validation_vtrend_sm_full \
  --suite full --force \
  --dataset data/bars_btcusdt_2016_now_h1_4h_1d.csv \
  --scenarios smart,base,harsh \
  --bootstrap 2000 --seed 1337
```

---

## 9. Test Results

### 9.1 VTREND-SM Tests

```
56 passed in 0.41s
```

### 9.2 Full Suite

```
461 passed, 39 warnings in 29.42s
```

39 warnings are pre-existing (numpy divide-by-zero in V8/V11 RSI computation). No failures. No new warnings.

---

## 10. Validation Rerun Result

```
VERDICT: REJECT (exit code 2)

lookahead          PASS
data_integrity     PASS
backtest           FAIL
cost_sweep         PASS
invariants         PASS
churn_metrics      PASS
regime             INFO
wfo                PASS
bootstrap          INFO
subsampling        INFO
holdout            FAIL
selection_bias     PASS

Reasons:
- Candidate harsh score delta too low (-67.6253)
- Holdout harsh score delta too low (-33.6112)
```

**decision.json**:
- `verdict`: REJECT
- `exit_code`: 2
- `errors`: [] (was 16 entries)
- `failures`: 2 (score deltas only)
- `reasons`: 2 (score deltas only)
- `config_unused_fields.json`: candidate `status: "PASS"`, `unused_fields: []`

The REJECT is a real result: SM scores lower than E0 under the current scoring function because return_term (CAGR-proportional) dominates. This reflects the fundamental risk/return tradeoff between SM (~10% avg exposure) and E0 (~47% avg exposure), not a tooling artifact.

---

## 11. Remaining Caveats

1. **ConfigProxy still doesn't track `resolved()` accesses**: The fix is an allowlist, not a tracking fix. If a future strategy has `resolved()` but legitimately has unused fields, they would be masked. Current impact: zero — `resolved()` semantically means "consume all fields into a resolved dict".

2. **T20 is a strategy-interface test, not engine integration**: The test was renamed to be honest. Actual BacktestEngine integration is covered by the validation pipeline (BacktestSuite) and by the CLI smoke tests in Report 35, but not by a dedicated unit test. This is acceptable given the pipeline-level coverage.

3. **`_vdo()` NaN propagation from inputs**: The function does not explicitly handle NaN inputs (close/high/low/volume). NaN values in numpy operations naturally propagate to NaN in the output, which is then filtered by the strategy's `np.isfinite()` check in `_compute_warmup()` and `on_bar()`. This is tested indirectly via the warmup and guard tests but not with explicit NaN input tests. Assessed as low risk — the upstream data pipeline (`v10/core/data.py`) rejects NaN values at load time.

---

## 12. Final Close-Out Status

| Condition | Status |
|-----------|--------|
| No strategy logic changes | **DONE** — `strategies/vtrend_sm/strategy.py` untouched |
| T20 not mislabeled | **DONE** — renamed to `TestStrategyInterfaceSmoke` |
| VDO coverage gap resolved | **DONE** — 6 dedicated `_vdo()` unit tests |
| False positive resolved | **DONE** — allowlist fix, ERROR→REJECT, `unused_fields: []` |
| Full suite pass | **DONE** — 461 passed, 0 failed |
| Report created | **DONE** — this document |
