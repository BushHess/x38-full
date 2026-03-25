# VTREND-P Audit & Discovery Report

**Date**: 2026-03-05
**Phase**: Algorithm audit + integration discovery. No implementation.

---

## 1. STATUS: `READY_FOR_VTRENDP_IMPLEMENT_AS_IS`

No confirmed bugs found. No ambiguities that block porting. All non-blocking warnings are documented below.

---

## 2. Executive Summary

**Source**: `Latch/research/vtrend_variants.py`, function `run_vtrend_p()` (lines 735–848), params `VTrendPParams` (lines 125–157).

**VTREND-P** is a price-first trend follower: binary FLAT/LONG state machine with vol-targeted sizing. It is strictly simpler than VTrend-SM (10 params vs 17, no fast EMA, no VDO, no regime-break exit).

**Audit result**: The algorithm is correct. No undefined variables, no dead branches, no off-by-one errors, no look-ahead, no NaN propagation issues in normal operation. Three non-blocking warnings documented (parameter validation gaps, `max(NaN, EPS)` argument-order fragility).

**Integration path**: Mechanical — follow the VTrend-SM transformation matrix. 4 files to create, 4 files to modify.

---

## 3. Reconstructed Executable Spec for Source VTREND-P

### 3.1 Inputs

| Input | Type | Required | Notes |
|-------|------|----------|-------|
| `market` | `pd.DataFrame` | Yes | Must have columns: `open`, `high`, `low`, `close` |
| `params` | `VTrendPParams` | No | Defaults to `VTrendPParams()` |
| `costs` | `CostModel` | No | Defaults to `CostModel(fee_bps=25.0)` |
| `bars_per_year` | `float` | No | Defaults to `2190.0` (365 × 6, H4 bars) |

VDO columns (`volume`, `taker_buy_base_volume`) are **not required** — P calls `validate_market_frame(market, require_vdo_columns=False)`.

### 3.2 Parameters & Defaults

```python
@dataclass(frozen=True)
class VTrendPParams:
    slow_period: int = 120
    atr_period: int = 14
    atr_mult: float = 1.5
    target_vol: float = 0.12
    entry_n: int | None = None       # auto: max(24, slow_period // 2) → 60
    exit_n: int | None = None        # auto: max(12, slow_period // 4) → 30
    vol_lookback: int | None = None  # auto: slow_period → 120
    slope_lookback: int = 6
    min_rebalance_weight_delta: float = 0.05
    min_weight: float = 0.0
```

`resolved()` returns a dict with auto-derived params filled in. Validates `slope_lookback > 0`.

### 3.3 Indicators

| Indicator | Formula | First finite at |
|-----------|---------|-----------------|
| `ema_slow` | `EMA(close, slow_period)`, `adjust=False` | Bar 0 |
| `ema_slow_slope_ref` | `ema_slow.shift(slope_lookback)` | Bar `slope_lookback` |
| `atr` | Wilder's ATR: SMA seed then EMA smoothing | Bar `atr_period - 1` |
| `hh_entry` | `high.shift(1).rolling(entry_n).max()` | Bar `entry_n` |
| `ll_exit` | `low.shift(1).rolling(exit_n).min()` | Bar `exit_n` |
| `rv` | `log_returns.rolling(vol_lookback).std(ddof=0) * sqrt(bars_per_year)` | Bar `vol_lookback` |

All indicators use current-bar close for their values. `hh_entry` and `ll_exit` use `shift(1)` to exclude the current bar (no look-ahead).

### 3.4 Warmup

`warmup = _warmup_start(ema_slow, slope_ref, atr, hh_entry, ll_exit, rv)` — first bar index `i` where ALL six indicator arrays are finite. With defaults, dominated by `vol_lookback = 120`.

Bars `0..warmup-1`: `signal_state[i] = False` (FLAT), `target_weight_signal[i] = 0.0`, no entry/exit evaluation.

### 3.5 State Transitions

Two states: **FLAT** (`active=False`) and **LONG** (`active=True`). Initial state: FLAT.

```
FLAT → LONG:  regime_ok AND slope_ok AND breakout_ok
LONG → FLAT:  close < exit_floor
```

No flip (simultaneous exit+re-entry on same bar). The `if/else` branch structure makes this impossible — only one branch evaluates per bar.

### 3.6 Entry Logic (when FLAT, bar i close)

```python
regime_ok  = close[i] > ema_slow[i]           # strict >
slope_ok   = ema_slow[i] > ema_slow_slope_ref[i]  # strict >
breakout_ok = close[i] > hh_entry[i]           # strict >

if regime_ok and slope_ok and breakout_ok:
    active = True
    entry_signal[i] = True
    weight = clip(target_vol / max(rv[i], EPS), min_weight)
    target_weight_signal[i] = weight
```

### 3.7 Exit Logic (when LONG, bar i close)

```python
exit_floor = max(ll_exit[i], ema_slow[i] - atr_mult * atr[i])

if close[i] < exit_floor:                     # strict <
    active = False
    exit_signal[i] = True
    target_weight_signal[i] = 0.0
```

No stop-loss, no take-profit, no trailing stop beyond the adaptive floor. No regime-break exit (unlike SM's optional `exit_on_regime_break`).

### 3.8 Sizing (when LONG, no entry/exit this bar)

```python
weight = clip(target_vol / max(rv[i], EPS), min_weight)
target_weight_signal[i] = weight
```

Weight is continuously updated while LONG. The execution engine (`_execute_target_weights`) handles rebalance threshold filtering.

### 3.9 Execution Model

- Signal formed at bar `i` close → order at bar `i+1` open
- Long-only BTC spot, target weight in `[0, 1]`
- Rebalance only when `|target_w - current_w| >= min_rebalance_weight_delta` OR zero-crossing
- Cost: `(fee_bps + half_spread_bps + slippage_bps) / 10000` per side on traded notional

### 3.10 Same-Bar Conflict Resolution

Not applicable. The `if not active / else` structure ensures exactly one branch evaluates per bar. Entry and exit cannot fire on the same bar. Verified empirically: `np.any(entry_signal & exit_signal) == False`.

### 3.11 Multi-Timeframe / Lookback

P is **single-timeframe** (H4 only). No D1 bars used (unlike E0 which uses D1 for EMA regime filter). All indicators computed on the same time series.

---

## 4. Algorithm Audit Findings

### 4.1 Confirmed Bugs

**None found.**

Checked:
- All variables defined before use ✓
- No dead branches or unreachable conditions ✓
- No off-by-one in indicator indexing ✓
- No look-ahead or repainting (all shifted indicators use `shift(1)`) ✓
- No NaN propagation past warmup ✓
- Comments match code behavior ✓
- No state-reset defects ✓
- Helper implementations match their documented intent ✓

### 4.2 Ambiguities Requiring Decision

**None found.**

The algorithm is fully specified by the source code. No conditional paths depend on unspecified behavior. No parameter combinations produce ambiguous results.

### 4.3 Non-Blocking Suspicions/Warnings

**W1: `max(rv_loop[i], EPS)` argument-order fragility**

```python
weight = _clip_weight(resolved["target_vol"] / max(rv_loop[i], EPS), ...)
```

If `rv_loop[i]` is NaN (which cannot happen post-warmup): `max(NaN, EPS)` returns NaN in Python (first-argument bias). Then `target_vol / NaN = NaN`, then `_clip_weight(NaN) → 0.0`. Safe outcome but fragile reasoning. The target SM already uses the same pattern.

**Verified empirically**: `max(float('nan'), 1e-12) → nan`, `max(1e-12, float('nan')) → 1e-12`.

**Impact**: None in practice (warmup prevents NaN from reaching this code). No fix needed for port.

**W2: Missing parameter validation in `resolved()`**

- `vol_lookback=1` passes `resolved()` but `annualized_realized_vol()` raises `ValueError("vol_lookback must be > 1")`
- `slow_period=-1` passes `resolved()` but `ema()` raises `ValueError("EMA span must be > 0")`
- `atr_period=0` passes `resolved()` but `atr_wilder()` raises `ValueError("ATR period must be > 0")`

These are caught at runtime by helper functions, not at config time. The target SM has the same gap. Not a porting blocker — any reasonable parameter choice works.

**W3: `exit_floor` computed unconditionally**

Line 812: `exit_floor = max(ll_exit_loop[i], ...)` is computed on every bar, including when FLAT. The value is unused in the FLAT branch. Harmless wasted computation, not a bug.

**W4: Docstring says "target_vol ≈ 12% to 15%"**

The default is `0.12` (12%). The "to 15%" is a range suggestion in the docstring, not a contradiction with the code default. Port uses the code default `0.12`.

---

## 5. Source-to-Target Transformation Matrix for VTrend-SM

### 5.1 File Layout

| Source (Latch) | Target (btc-spot-dev) |
|----------------|----------------------|
| `research/vtrend_variants.py` (all-in-one) | `strategies/vtrend_sm/strategy.py` (standalone module) |
| (none) | `strategies/vtrend_sm/__init__.py` (re-exports) |
| (none) | `configs/vtrend_sm/vtrend_sm_default.yaml` |
| `research/test_vtrend_variants.py` | `tests/test_vtrend_sm.py` (56 tests, greatly expanded) |

### 5.2 Naming Convention

| Form | SM example |
|------|------------|
| Module | `strategies.vtrend_sm.strategy` |
| Registry key | `"vtrend_sm"` |
| Strategy class | `VTrendSMStrategy(Strategy)` |
| Config class | `VTrendSMConfig` (mutable dataclass) |
| STRATEGY_ID | `"vtrend_sm"` |
| Signal reasons | `"vtrend_sm_entry"`, `"vtrend_sm_floor_exit"`, `"vtrend_sm_regime_exit"`, `"vtrend_sm_rebalance"` |

### 5.3 Config Schema

Source: `frozen=True` dataclass with `resolved()` → dict.
Target: mutable dataclass (needed for factory `setattr`), `resolved()` preserved, `__post_init__` added for early validation.

### 5.4 Indicator Duplication (Frozen Artifact Pattern)

Source module-level helpers duplicated as private functions in target:
`ema()` → `_ema()`, `atr_wilder()` → `_atr()`, etc.
Rationale: strategies are frozen research artifacts, fully independent. No cross-strategy imports.

### 5.5 Strategy Interface Transformation

| Source (procedural) | Target (class-based) |
|---------------------|---------------------|
| Precompute all indicators before loop | `on_init(h4_bars, d1_bars)` |
| `_warmup_start(...)` → int | `_compute_warmup(n)` → int |
| `active` local var | `self._active` instance var |
| `for i in range(n)` loop body | `on_bar(state: MarketState) → Signal \| None` |
| `_execute_target_weights(...)` | Handled by `BacktestEngine` |
| Rebalance: execution engine filters | `on_bar()` checks `delta >= threshold` before emitting Signal |
| `on_after_fill()` | No-op (`pass`) |

### 5.6 Integration Points (5 wiring locations)

| # | File | What SM added |
|---|------|---------------|
| 1 | `strategies/vtrend_sm/strategy.py` + `__init__.py` | Strategy + Config + re-exports |
| 2 | `v10/core/config.py` | Import, `_VTREND_SM_FIELDS`, `_KNOWN_STRATEGIES` entry, `validate_config()` branch |
| 3 | `v10/cli/backtest.py` | Import, `STRATEGY_REGISTRY["vtrend_sm"]` |
| 4 | `validation/strategy_factory.py` | Import, `STRATEGY_REGISTRY["vtrend_sm"]` tuple |
| 5 | `v10/research/candidates.py` | Import, `_VTREND_SM_FIELDS`, `load_candidates()` routing, `build_strategy()` routing |

---

## 6. Exact VTREND-P Touch-List

### Files to CREATE (4)

| File | Purpose | Est. lines |
|------|---------|------------|
| `strategies/vtrend_p/strategy.py` | VTrendPConfig + indicators + VTrendPStrategy | ~280 |
| `strategies/vtrend_p/__init__.py` | Re-exports: STRATEGY_ID, VTrendPConfig, VTrendPStrategy | ~12 |
| `configs/vtrend_p/vtrend_p_default.yaml` | Default YAML for validation pipeline | ~15 |
| `tests/test_vtrend_p.py` | Test suite (SM pattern, minus VDO/regime-break tests) | ~700 |

### Files to MODIFY (4)

| File | Change |
|------|--------|
| `v10/core/config.py` | +import, +`_VTREND_P_FIELDS`, +`_KNOWN_STRATEGIES` entry, +`validate_config()` branch |
| `v10/cli/backtest.py` | +import, +`STRATEGY_REGISTRY["vtrend_p"]` |
| `validation/strategy_factory.py` | +import, +`STRATEGY_REGISTRY["vtrend_p"]` tuple |
| `v10/research/candidates.py` | +import, +`_VTREND_P_FIELDS`, +routing in `load_candidates()` and `build_strategy()` |

### Key Differences from SM in Target

| SM code | P equivalent |
|---------|-------------|
| `self._ema_fast` + `ema_fast > ema_slow` regime | **Remove** — P uses `close > ema_slow` |
| `use_vdo_filter` / `_vdo_arr` / `_vdo()` | **Remove entirely** |
| `exit_on_regime_break` option | **Remove entirely** |
| `fast_period` field + auto-derive | **Remove entirely** |
| `vdo_threshold`, `vdo_fast`, `vdo_slow` fields | **Remove entirely** |
| `atr_mult = 3.0` | `atr_mult = 1.5` |
| `target_vol = 0.15` | `target_vol = 0.12` |
| `regime_ok = (ema_f > ema_s) and (ema_s > slope_ref)` | `regime_ok = close > ema_s` + separate `slope_ok = ema_s > slope_ref` |
| Reason prefix `"vtrend_sm_"` | `"vtrend_p_"` |
| Warmup includes `ema_fast`, possibly `vdo` | Warmup: 5 arrays only (ema_slow, slope_ref, atr, hh, ll, rv) |

---

## 7. Required Helper Reuse vs Helper Porting

### Indicators — DUPLICATE (frozen artifact pattern)

| Helper | In source | In SM target | P action |
|--------|-----------|-------------|----------|
| `ema()` | ✓ | `_ema()` | Duplicate into P |
| `atr_wilder()` | ✓ | `_atr()` | Duplicate into P |
| `rolling_high_shifted()` | ✓ | `_rolling_high_shifted()` | Duplicate into P |
| `rolling_low_shifted()` | ✓ | `_rolling_low_shifted()` | Duplicate into P |
| `annualized_realized_vol()` | ✓ | `_realized_vol()` | Duplicate into P |
| `_clip_weight()` | ✓ | `_clip_weight()` | Duplicate into P |

### NOT needed by P

| Helper | Reason |
|--------|--------|
| `_vdo()` / `compute_vdo_base()` | P has no VDO filter |
| `ema_fast` computation | P uses `close > ema_slow`, not `ema_fast > ema_slow` |

### Framework types — IMPORT

`Signal`, `MarketState`, `Fill` from `v10.core.types`. `Strategy` from `v10.strategies.base`.

### New helpers required: **NONE**

---

## 8. Parity-Validation Plan for Prompt 2

### 8.1 Deterministic Candle-by-Candle Trace Cases

**TC-TRACE-1: Entry fires on first eligible bar**

Create 30-bar fixture with params `slow_period=8, atr_period=3, entry_n=5, exit_n=3, vol_lookback=10, slope_lookback=2`. Construct prices so that on bar 10 (first post-warmup bar), `close > ema_slow AND ema_slow > slope_ref AND close > hh`. Verify entry signal on bar 10 and trade on bar 11 open.

**TC-TRACE-2: Exit fires correctly**

Extend TC-TRACE-1 with a price drop on bar 15 below `exit_floor`. Verify exit signal on bar 15 and sell on bar 16 open.

**TC-TRACE-3: Rebalance threshold**

While LONG, construct `rv` change large enough to shift weight by >0.05 (default threshold). Verify rebalance Signal emitted. Then construct a change <0.05 — verify no Signal.

### 8.2 Edge-Case Fixtures

| Test ID | Scenario | Expected behavior |
|---------|----------|-------------------|
| EC-1 | `close == ema_slow` exactly | `regime_ok = False` (strict `>`), no entry |
| EC-2 | `close == hh_entry` exactly | `breakout_ok = False` (strict `>`), no entry |
| EC-3 | `close == exit_floor` exactly | No exit (strict `<`) |
| EC-4 | `rv = 0.0` (zero volatility) | `target_vol / EPS → 1.2e11`, clipped to `1.0` |
| EC-5 | Empty bars (`n=0`) | `on_init` returns immediately, `on_bar` never called |
| EC-6 | All-NaN scenario (warmup = n) | `on_bar` returns `None` for all bars |
| EC-7 | Entry, then immediate exit on next bar | Valid: entry bar i, exit bar i+1 |
| EC-8 | `min_weight=0.1`, weight=0.05 | `_clip_weight(0.05, 0.1) → 0.0`, no entry (weight below gate) |
| EC-9 | Weight delta exactly at threshold boundary | `delta >= threshold - 1e-12` → rebalance fires |

### 8.3 Config Defaults Parity

Test that `VTrendPConfig` defaults match source `VTrendPParams`:

| Field | Source default | Target must match |
|-------|---------------|-------------------|
| `slow_period` | 120 | 120 |
| `atr_period` | 14 | 14 |
| `atr_mult` | 1.5 | 1.5 |
| `target_vol` | 0.12 | 0.12 |
| `entry_n` | None (auto: 60) | None (auto: 60) |
| `exit_n` | None (auto: 30) | None (auto: 30) |
| `vol_lookback` | None (auto: 120) | None (auto: 120) |
| `slope_lookback` | 6 | 6 |
| `min_rebalance_weight_delta` | 0.05 | 0.05 |
| `min_weight` | 0.0 | 0.0 |

### 8.4 Registration Parity (5 integration points)

For each of these, write a test that imports and verifies the registry entry:
1. `strategies.vtrend_p` package exports `STRATEGY_ID`, `VTrendPConfig`, `VTrendPStrategy`
2. `v10.core.config._KNOWN_STRATEGIES` contains `"vtrend_p"`
3. `v10.cli.backtest.STRATEGY_REGISTRY["vtrend_p"]` resolves to `VTrendPStrategy`
4. `validation.strategy_factory.STRATEGY_REGISTRY["vtrend_p"]` resolves to `(VTrendPStrategy, VTrendPConfig)`
5. `v10.research.candidates` handles `"vtrend_p"` in `load_candidates()` and `build_strategy()`

---

## 9. Expected Validation Commands

```bash
# P-specific tests only
python -m pytest tests/test_vtrend_p.py -v

# Full suite (must remain green, 715 + N new tests)
python -m pytest

# Validation pipeline
python validate_strategy.py \
  --config configs/vtrend_p/vtrend_p_default.yaml \
  --outdir out/validation_vtrend_p_full

# SM tests still pass (no SM code modified)
python -m pytest tests/test_vtrend_sm.py -v
```

---

## 10. Recommended Implementation Order

1. `strategies/vtrend_p/strategy.py` — Config + indicators + strategy class
2. `strategies/vtrend_p/__init__.py` — Package exports
3. `tests/test_vtrend_p.py` — Test suite (run and verify before wiring)
4. `v10/core/config.py` — Config validation wiring
5. `v10/cli/backtest.py` — CLI registry
6. `validation/strategy_factory.py` — Factory registry
7. `v10/research/candidates.py` — Candidate builder routing
8. `configs/vtrend_p/vtrend_p_default.yaml` — Validation YAML
9. Full test suite run + validation pipeline run

Steps 4–7 are mechanical (copy SM pattern, change names). The real work is in steps 1 and 3.

---

## 11. Handoff Notes for Prompt 2

### Outcome: `READY_FOR_VTRENDP_IMPLEMENT_AS_IS`

No confirmed bugs. No fixes needed. Port the algorithm exactly as specified in the source.

### What to implement

VTREND-P is SM minus the optional features. Copy SM's target structure, then:
- Remove: `ema_fast`, `_vdo()`, `use_vdo_filter`, `exit_on_regime_break`, `fast_period`, `vdo_*` fields
- Change: regime from `ema_f > ema_s` to `close > ema_s` (separate `slope_ok` check)
- Change: defaults `atr_mult=1.5`, `target_vol=0.12`
- Change: signal reasons from `"vtrend_sm_*"` to `"vtrend_p_*"`

### Indicator functions to duplicate

Copy byte-for-byte from SM target: `_ema`, `_atr`, `_rolling_high_shifted`, `_rolling_low_shifted`, `_realized_vol`, `_clip_weight`. Do NOT copy `_vdo`.

### Test pattern to follow

Copy `test_vtrend_sm.py` structure. Remove VDO tests, regime-break tests, fast EMA tests. Adapt entry/exit tests for P's simpler regime. Keep all registration, invariant, edge-case, and ConfigProxy tests.

### Do NOT change

Any existing code: `strategies/vtrend_sm/`, `strategies/vtrend/`, `validation/config_audit.py`, `validation/runner.py`, `pytest.ini`.

### Confirmed fixes allowed: **NONE** (status is AS_IS)

---

*End of VTREND-P Audit & Discovery Report.*
