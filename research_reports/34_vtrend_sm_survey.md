# Report 34: VTREND-SM Porting Survey

> **Phase**: 2 — Survey and Report (READ-ONLY)
> **Date**: 2026-03-04
> **Status**: Complete — awaiting review before Phase 3

---

## 1. Scope and Evidence Sources

### 1.1 Source Repository (Read-Only)

| Item | Path |
|------|------|
| Primary algorithm | `Latch/research/vtrend_variants.py` (896 lines) |
| Primary function | `run_vtrend_state_machine()` (lines 588–727) |
| Config dataclass | `VTrendStateMachineParams` (lines 77–122) |
| Indicator functions | `ema()`, `atr_wilder()`, `rolling_high_shifted()`, `rolling_low_shifted()`, `annualized_realized_vol()`, `compute_vdo_base()` (lines 271–333) |
| Internal helpers | `_clip_weight()`, `_warmup_start()`, `_position_weight()` (lines 415–435) |
| Execution engine | `_execute_target_weights()` (lines 476–579) |
| Metrics | `compute_metrics()` (lines 341–407) |
| Result type | `BacktestResult`, `TradeRecord` (lines 160–224) |
| Cost model | `CostModel` (lines 52–74) |
| Test suite | `Latch/research/test_vtrend_variants.py` (253 lines, 8 tests for VTREND-SM) |
| Spec document | `Latch/research/VTREND_SPEC_AND_GUIDE.md` (284 lines) |

**Critical clarification**: `run_vtrend_state_machine()` is entirely self-contained within `vtrend_variants.py`. It does NOT import from the `Latch/research/Latch/` subpackage. The `Latch/` subpackage implements a *separate* algorithm called LATCH, which uses hysteretic 3-state regime (`LatchState.OFF/ARMED/LONG` via `compute_hysteretic_regime()` in `Latch/state_machine.py:37-78`). VTREND-SM uses a simple binary `active=True/False` flag with per-bar regime evaluation — no regime memory, no hysteresis.

### 1.2 Target Repository

| Item | Path |
|------|------|
| Strategy base class | `v10/strategies/base.py` (49 lines) |
| Existing VTREND (E0) | `strategies/vtrend/strategy.py` (178 lines) |
| Engine | `v10/core/engine.py` (338 lines) |
| Execution model | `v10/core/execution.py` (231 lines) |
| Types | `v10/core/types.py` (185 lines) |
| Metrics | `v10/core/metrics.py` (191 lines) |
| Data feed | `v10/core/data.py` (101 lines) |
| Config / registration | `v10/core/config.py` (247 lines) |
| Candidate factory | `v10/research/candidates.py` (323 lines) |
| Validation factory | `validation/strategy_factory.py` (94 lines) |
| CLI backtest | `v10/cli/backtest.py` (308 lines) |
| Blueprint | `VTREND_BLUEPRINT.md` (658 lines) |

### 1.3 Premature Files (Created Before This Survey)

Two files were created in a prior session before this survey phase was defined:

| File | Status |
|------|--------|
| `strategies/vtrend_sm/__init__.py` (13 lines) | Exists — exports `STRATEGY_ID`, `VTrendSMConfig`, `VTrendSMStrategy` |
| `strategies/vtrend_sm/strategy.py` (364 lines) | Exists — full implementation, needs verification in Phase 3 |

These files will be audited for correctness against the source in Phase 3.

---

## 2. VTREND-SM Architecture in Latch

### 2.1 Algorithm Overview

VTREND-SM is a trend-following strategy for BTC/USDT spot on the H4 timeframe. It differs from the original VTREND by replacing the trailing-stop exit with an adaptive floor exit and adding a breakout entry gate.

**State**: Binary `active` flag (True = LONG, False = FLAT). No intermediate states.

**Signal flow**: Signal formed at bar `i` close → executed at bar `i+1` open.

### 2.2 Parameters

Source: `VTrendStateMachineParams` (`vtrend_variants.py:77-122`)

| Parameter | Default | Auto-derivation |
|-----------|---------|----------------|
| `slow_period` | 120 | — |
| `fast_period` | None | `max(5, slow_period // 4)` → 30 |
| `atr_period` | 14 | — |
| `atr_mult` | 3.0 | — |
| `entry_n` | None | `max(24, slow_period // 2)` → 60 |
| `exit_n` | None | `max(12, slow_period // 4)` → 30 |
| `target_vol` | 0.15 | — |
| `vol_lookback` | None | `slow_period` → 120 |
| `slope_lookback` | 6 | — |
| `use_vdo_filter` | False | — |
| `vdo_threshold` | 0.0 | — |
| `vdo_fast` | 12 | — |
| `vdo_slow` | 28 | — |
| `exit_on_regime_break` | False | — |
| `min_rebalance_weight_delta` | 0.05 | — |
| `min_weight` | 0.0 | — |

### 2.3 Indicators

Source: `vtrend_variants.py:271-333`

| Indicator | Function | Formula |
|-----------|----------|---------|
| EMA fast/slow | `ema()` | `ewm(span=N, adjust=False).mean()` |
| EMA slow slope ref | `ema_slow.shift(slope_lookback)` | Pandas shift |
| ATR | `atr_wilder()` | Wilder's RMA: `(prev * (p-1) + TR) / p` |
| Breakout level | `rolling_high_shifted()` | `high.shift(1).rolling(entry_n).max()` |
| Exit floor level | `rolling_low_shifted()` | `low.shift(1).rolling(exit_n).min()` |
| Realized vol | `annualized_realized_vol()` | `std(log_returns, ddof=0) * sqrt(bars_per_year)` |
| VDO | `compute_vdo_base()` | `EMA(vdr, fast) - EMA(vdr, slow)` where `vdr = (2*buy - vol) / vol` |

### 2.4 Signal Logic

Source: `vtrend_variants.py:674-704`

```
regime_ok = (ema_fast > ema_slow) AND (ema_slow > ema_slow_shifted)

IF FLAT:
    breakout_ok = (close > rolling_high_shifted)
    vdo_ok = True  (or vdo > threshold if use_vdo_filter)
    IF regime_ok AND breakout_ok AND vdo_ok:
        → active = True, entry_signal[i] = True

IF LONG:
    exit_floor = max(rolling_low_shifted, ema_slow - atr_mult * ATR)
    floor_break = (close < exit_floor)
    regime_break = exit_on_regime_break AND (NOT regime_ok)
    IF floor_break OR regime_break:
        → active = False, exit_signal[i] = True

IF active:
    weight = clip(target_vol / max(rv, EPS), min_weight)
ELSE:
    weight = 0.0
```

### 2.5 Sizing

Vol-targeted fractional sizing: `weight = min(1.0, target_vol / realized_vol)`, clipped to `[0, 1]` with `min_weight` gate. This produces continuous values in `(0, 1]` when LONG.

### 2.6 Execution Model

Source: `_execute_target_weights()` (`vtrend_variants.py:476-579`)

- Signal at bar `i` close → execute at bar `i+1` open
- Rebalance gate: trade only when `|target_w - current_w| >= threshold` OR crossing zero
- Cost: flat `one_way_rate` applied to traded notional
- Cash constraint: buy notional capped at `cash / (1 + cost_rate)`
- Initial equity: 1.0 (normalized)

### 2.7 Cost Model

Source: `CostModel` (`vtrend_variants.py:52-74`)

```python
one_way_rate = (fee_bps + half_spread_bps + slippage_bps) / 10_000
# Default: fee_bps=25 → one_way_rate = 0.0025 (25 bps)
```

### 2.8 Constants

```python
BARS_PER_YEAR_4H = 365.0 * 6.0  # = 2190.0
EPS = 1e-12
```

### 2.9 Warmup

`_warmup_start()` (`vtrend_variants.py:424-429`): finds first index where ALL indicator arrays have finite values. During warmup, the `active` flag state is preserved but no entry/exit logic runs.

---

## 3. Comparison with Existing VTREND in btc-spot-dev

### 3.1 Structural Differences

| Aspect | VTREND (E0) | VTREND-SM |
|--------|-------------|-----------|
| **Source** | `strategies/vtrend/strategy.py` | `Latch/research/vtrend_variants.py:588-727` |
| **Entry condition** | `ema_fast > ema_slow AND vdo > threshold` | `regime_ok AND close > rolling_high AND (optional VDO)` |
| **Regime definition** | Simple EMA crossover | EMA crossover + EMA slow positive slope |
| **Exit mechanism** | Trailing stop from peak OR trend reversal | Adaptive floor = max(rolling_low, ema_slow - atr*ATR) OR optional regime break |
| **Sizing** | Binary: 0 or 1.0 | Vol-targeted: `min(1, target_vol/rv)` ∈ (0, 1] |
| **Rebalance** | N/A (binary) | Threshold-gated: `|delta| >= min_rebalance_weight_delta` |
| **Parameters** | 3 tunable + 3 structural = 6 | 4 tunable + 12 structural/auto = 16 |
| **Indicators** | `_ema`, `_atr`, `_vdo` | `_ema`, `_atr`, `_vdo`, `_rolling_high_shifted`, `_rolling_low_shifted`, `_realized_vol` |
| **VDO role** | Required for entry | Optional filter (default: off) |
| **State** | `_in_position` bool + `_peak_price` float | `_active` bool only |

### 3.2 Shared Components

Both strategies share identical implementations for:
- `_ema()` — EMA with `alpha = 2/(period+1)`, recursive
- `_atr()` — Wilder's ATR with initial SMA seed
- `_vdo()` — Volume Delta Oscillator (MACD-style on VDR)

The btc-spot-dev implementations (`strategies/vtrend/strategy.py:133-177`) are numpy-only, while the Latch implementations (`vtrend_variants.py:271-333`) use pandas. The mathematical formulas are identical.

### 3.3 New Indicators Required

VTREND-SM needs 3 indicators not present in existing VTREND:

1. **`_rolling_high_shifted(high, lookback)`** — `max(high[i-lookback..i-1])`, NaN for insufficient data
2. **`_rolling_low_shifted(low, lookback)`** — `min(low[i-lookback..i-1])`, NaN for insufficient data
3. **`_realized_vol(close, lookback, bars_per_year)`** — `std(log_returns[i-lookback+1..i], ddof=0) * sqrt(bars_per_year)`

### 3.4 Key Algorithmic Distinction

VTREND-SM is a **fundamentally different algorithm**, not a parameter variation of VTREND:
- Different entry mechanism (breakout vs. crossover)
- Different exit mechanism (adaptive floor vs. trailing stop from peak)
- Different sizing (continuous vol-target vs. binary)
- Different state tracking (no peak price tracking)

This justifies a separate strategy module `strategies/vtrend_sm/`.

---

## 4. Integration Plan

### 4.1 Files to Create

| File | Purpose |
|------|---------|
| `strategies/vtrend_sm/__init__.py` | Module exports (already exists) |
| `strategies/vtrend_sm/strategy.py` | `VTrendSMConfig`, `VTrendSMStrategy` (already exists, needs audit) |
| `tests/test_vtrend_sm.py` | Unit and integration tests |

### 4.2 Files to Modify (Registration)

4 registration points must be updated:

| File | Change | Evidence |
|------|--------|----------|
| `v10/core/config.py` | Add `VTrendSMConfig` import, `_VTREND_SM_FIELDS`, add `"vtrend_sm"` to `_KNOWN_STRATEGIES`, add to `strategy_fields_by_name`, add validation branch | Lines 22-41, 147-153, 196-215 — pattern for vtrend, v12, v13 |
| `v10/research/candidates.py` | Add `VTrendSMConfig`, `VTrendSMStrategy` import, add `_VTREND_SM_FIELDS`, add `"vtrend_sm"` branch in `load_candidates()` and `build_strategy()` | Lines 61-64, 93-105, 152-176 — pattern for v8, v11, v12 |
| `validation/strategy_factory.py` | Add import, add `"vtrend_sm": (VTrendSMStrategy, VTrendSMConfig)` to `STRATEGY_REGISTRY` | Lines 14-30 — pattern for v12, v13 |
| `v10/cli/backtest.py` | Add import, add `"vtrend_sm": VTrendSMStrategy` to `STRATEGY_REGISTRY` | Lines 37-49 — pattern for buy_and_hold, v8, v11 |

### 4.3 Registration Precedent

Existing registration pattern varies by strategy:

| Strategy | config.py | candidates.py | strategy_factory.py | cli/backtest.py |
|----------|-----------|---------------|--------------------|-----------------|
| v8_apex | YES | YES | YES | YES |
| v11_hybrid | YES | YES | YES | YES |
| v12_emdd_ref_fix | YES | YES | YES | NO |
| v13_add_throttle | YES | NO | YES | NO |
| vtrend | YES | NO | NO | NO |
| buy_and_hold | YES | YES | YES | YES |

**Observation**: `vtrend` is only registered in `config.py` — not in the other 3 files. This is a pre-existing inconsistency. VTREND-SM should follow the full pattern (all 4 files) for completeness.

### 4.4 Strategy Interface Mapping

The `Strategy` base class (`v10/strategies/base.py:10-48`) defines:

```python
class Strategy(ABC):
    def on_init(self, h4_bars: list, d1_bars: list) -> None  # precompute
    def on_bar(self, state: MarketState) -> Signal | None     # per-bar decision
    def on_after_fill(self, state: MarketState, fill: Fill)   # post-fill hook
    def name(self) -> str                                     # identifier
```

VTREND-SM mapping:
- **`on_init()`**: Precompute all indicator arrays from `h4_bars` (close, high, low, volume, taker_buy). Compute warmup index.
- **`on_bar()`**: Binary state machine — flat/long checks, return `Signal(target_exposure=weight)` for entry/rebalance, `Signal(target_exposure=0.0)` for exit.
- **`on_after_fill()`**: No-op (strategy state is purely signal-driven).
- **`name()`**: Return `"vtrend_sm"`.

### 4.5 Signal Interface

`Signal` (`v10/core/types.py`):
- `target_exposure: float | None` — fractional NAV exposure [0.0, 1.0]
- `reason: str` — human-readable label

VTREND-SM will use `target_exposure` for all signals:
- Entry: `Signal(target_exposure=weight, reason="vtrend_sm_entry")`
- Exit: `Signal(target_exposure=0.0, reason="vtrend_sm_floor_exit" | "vtrend_sm_regime_exit")`
- Rebalance: `Signal(target_exposure=new_weight, reason="vtrend_sm_rebalance")`

---

## 5. Risks and Compatibility Issues

### 5.1 Annualization Constant

| System | Value | Formula |
|--------|-------|---------|
| Latch | 2190.0 | `365.0 * 6.0` |
| btc-spot-dev | 2191.5 | `6.0 * 365.25` (MEMORY.md: sqrt convention) |
| btc-spot-dev metrics.py | 2190.0 | `(24.0 / 4.0) * 365.0` (line 19) |

**Issue**: btc-spot-dev's `metrics.py:19` uses `PERIODS_PER_YEAR_4H = (24.0/4.0) * 365.0 = 2190.0`, which matches Latch. But the MEMORY.md convention says `6.0 * 365.25 = 2191.5`.

**Impact**: The 0.07% difference (2191.5 vs 2190.0) affects Sharpe/Sortino computation but is negligible for practical purposes. The strategy module (`strategies/vtrend_sm/strategy.py`) uses `BARS_PER_YEAR_4H = 6.0 * 365.25` for realized vol calculation. The engine's metrics computation (`v10/core/metrics.py`) uses `2190.0`. This is consistent with VTREND E0 which does no annualization internally. Sharpe comes from the engine metrics, so the strategy's annualization constant only affects vol-targeting sizing — and the 0.07% difference is within noise.

**Risk**: LOW. No action needed. The two constants serve different purposes: strategy uses 2191.5 for vol-targeting, metrics.py uses 2190.0 for Sharpe. Both are defensible.

### 5.2 Cost Model Structural Difference

| System | Model | Default RT |
|--------|-------|-----------|
| Latch | `CostModel(fee_bps=25)` → flat `one_way_rate=0.0025` | 50 bps |
| btc-spot-dev | `CostConfig(spread_bps, slippage_bps, taker_fee_pct)` → spread + slippage + fee | varies by scenario |

**Impact**: The strategy does NOT handle costs. The engine (`v10/core/engine.py`) handles all cost computation via `ExecutionModel` (`v10/core/execution.py`). The strategy only emits `Signal(target_exposure=X)` and the engine handles fill pricing, fees, and cash constraints.

**Risk**: NONE for strategy code. Cross-validation (Latch standalone vs btc-spot-dev engine) will show metric differences due to different cost models. This is expected and acceptable.

### 5.3 Rebalance Threshold Interaction with Engine

Latch handles the rebalance threshold in its own execution engine (`_execute_target_weights():508-511`). In btc-spot-dev, the engine has a separate `_EXPO_THRESHOLD = 0.005` (`engine.py:28`).

**Interaction**: VTREND-SM implements a 5% (`min_rebalance_weight_delta=0.05`) rebalance gate in the strategy's `on_bar()` method. The engine additionally applies its own `_EXPO_THRESHOLD = 0.005` (0.5%) gate. Since the strategy gate (5%) is much wider than the engine gate (0.5%), the strategy gate dominates — the engine gate will never block a signal that the strategy already approved.

**Risk**: LOW. The double-gating is redundant but harmless. Strategy signals that pass the 5% gate will always pass the 0.5% engine gate.

### 5.4 Exposure State for Rebalance

VTREND-SM's rebalance check requires knowing current exposure: `|new_weight - state.exposure| >= threshold` (`strategies/vtrend_sm/strategy.py:354`).

The `MarketState.exposure` field (`v10/core/types.py`) is computed by `Portfolio.exposure(mid)` at bar close (`engine.py:219`). This uses close price as mid, so `state.exposure` at bar `i` reflects the exposure at bar `i`'s close — which is what the strategy needs.

**Risk**: LOW. The exposure value is correct for rebalance decisions.

### 5.5 VDO Formula Difference

Latch's `compute_vdo_base()` (`vtrend_variants.py:321-333`) uses:
```python
vdr = (2 * taker_buy - volume) / volume  # equivalently: (buy - sell) / volume
```

btc-spot-dev's `_vdo()` (`strategies/vtrend/strategy.py:159-177`) uses the same formula when `taker_buy > 0`:
```python
vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
```
where `taker_sell = volume - taker_buy`, so `(buy - sell) / vol = (2*buy - vol) / vol`. Algebraically identical.

When taker data is unavailable, btc-spot-dev raises RuntimeError (OHLC fallback removed 2026-03-14, P0). Latch similarly requires VDO columns when filter is enabled.

**Risk**: NONE when taker data is available (standard case). Without taker data, strategy fails closed — no silent degradation.

### 5.6 Rolling Window Implementation

Latch uses pandas: `high.shift(1).rolling(window=N, min_periods=N).max()`.

The premature btc-spot-dev implementation uses numpy loops:
```python
for i in range(lookback, n):
    out[i] = np.max(high[i - lookback:i])  # excludes current bar
```

**Correctness check**: At index `i`, Latch computes `max(high[i-N], ..., high[i-1])` (via `.shift(1)` then `.rolling(N).max()`). The numpy version computes `max(high[i-lookback:i])` = `max(high[i-lookback], ..., high[i-1])`. These are equivalent when `lookback = N`.

**Risk**: LOW. Must verify the edge case: pandas `.shift(1)` starts NaN at index 0, then rolling requires `min_periods=N` full non-NaN values. The numpy version starts producing values at index `lookback` (NaN before). These should align. Phase 3 tests should include explicit numerical verification.

### 5.7 Realized Vol Window Alignment

Latch (`vtrend_variants.py:302-306`):
```python
rv = log_returns.rolling(window=lookback, min_periods=lookback).std(ddof=0) * sqrt(bars_per_year)
```
where `log_returns[0] = NaN` (from `close.shift(1)`), so the first finite `rv` value appears at index `lookback` (not `lookback + 1`).

The premature btc-spot-dev implementation (`strategies/vtrend_sm/strategy.py:176-199`):
```python
for i in range(lookback, n):
    window = lr[i - lookback + 1:i + 1]  # lookback values
```
At index `i = lookback`, window = `lr[1:lookback+1]` = `lookback` log-return values (indices 1 through lookback). This matches the pandas rolling window alignment.

**Risk**: LOW. The window selection appears correct. Phase 3 tests should include numerical cross-verification against pandas reference.

### 5.8 Pre-existing Registration Inconsistency

`vtrend` (the original VTREND E0) is registered in `v10/core/config.py` but NOT in:
- `v10/research/candidates.py` (line 102: only v8, v11, v12, buy_and_hold)
- `validation/strategy_factory.py` (line 24: only v8, v11, v12, v13, buy_and_hold)
- `v10/cli/backtest.py` (line 45: only buy_and_hold, v8, v11)

This is a pre-existing inconsistency unrelated to VTREND-SM. It means VTREND E0 can be referenced in YAML configs (config.py validates it) but cannot be instantiated via candidates.py, strategy_factory.py, or CLI.

**Risk**: NONE for VTREND-SM. Documenting for awareness. VTREND-SM should register in all 4 files.

### 5.9 Engine Warmup Interaction

The engine's warmup system (`engine.py:119-175`) uses `warmup_mode="no_trade"` by default: `strategy.on_bar()` is called during warmup (so indicators update), but signals are discarded. The strategy also has its own internal warmup (`_warmup_end`) computed from indicator convergence.

**Interaction**: Engine warmup (365 days ≈ 2190 H4 bars) >> strategy indicator warmup (~120 bars for slow EMA + slope_lookback). Both are additive (engine discards signals during its warmup window, strategy returns `None` during its indicator warmup). This is safe.

**Risk**: NONE. Engine warmup dominates.

---

## 6. Readiness Conclusion

### 6.1 Feasibility Assessment

VTREND-SM is **fully portable** to btc-spot-dev. The architecture is compatible:

- **Strategy interface**: `on_init()` / `on_bar()` / `on_after_fill()` maps cleanly to VTREND-SM's precompute + binary state machine pattern. Existing VTREND E0 (`strategies/vtrend/strategy.py`) demonstrates the exact same pattern.
- **Signal interface**: `Signal(target_exposure=float)` handles VTREND-SM's fractional vol-targeted sizing natively. Engine's `_apply_target_exposure()` (`engine.py:279-322`) correctly handles both buy (delta > 0.5%) and sell (delta < -0.5%) with cash constraints.
- **Data interface**: `MarketState` provides `bar.close`, `bar.high`, `bar.low`, `bar.volume`, `bar.taker_buy_base_vol`, `h4_bars`, and `bar_index` — everything VTREND-SM needs.
- **Indicator pattern**: Precompute in `on_init()`, index in `on_bar()` — identical to VTREND E0.

### 6.2 Existing Implementation Status

The premature `strategies/vtrend_sm/strategy.py` (364 lines) appears structurally correct based on visual inspection:
- `VTrendSMConfig`: 16 parameters match `VTrendStateMachineParams` exactly
- `resolved()` method mirrors Latch's auto-derivation logic
- Indicator helpers `_ema`, `_atr`, `_vdo` match VTREND E0 copies
- New helpers `_rolling_high_shifted`, `_rolling_low_shifted`, `_realized_vol` implement correct formulas
- `on_bar()` logic follows the source algorithm faithfully

**However**: This file was created before the survey and has NOT been rigorously verified. Phase 3 must include:
1. Line-by-line audit against `vtrend_variants.py:588-727`
2. Numerical cross-verification on synthetic data
3. Integration smoke test with BacktestEngine

### 6.3 Scope of Phase 3 Work

| Task | Estimate |
|------|----------|
| Audit/fix `strategies/vtrend_sm/strategy.py` | Small — file exists, needs verification |
| Register in 4 files | Small — mechanical additions |
| Write `tests/test_vtrend_sm.py` | Medium — 8-10 test cases |
| Integration smoke test | Small — run with BacktestEngine |

### 6.4 No Blockers

No architectural incompatibilities, missing interfaces, or design conflicts were found. The port is a clean addition that requires no changes to the engine, base class, types, or existing strategies.

---

## Appendix A: Symbol Cross-Reference

### Source → Target Mapping

| Latch Symbol | btc-spot-dev Symbol | Location |
|-------------|--------------------|---------|
| `VTrendStateMachineParams` | `VTrendSMConfig` | `strategies/vtrend_sm/strategy.py:46` |
| `run_vtrend_state_machine()` | `VTrendSMStrategy.on_bar()` | `strategies/vtrend_sm/strategy.py:291` |
| `ema()` (pandas) | `_ema()` (numpy) | `strategies/vtrend_sm/strategy.py:101` |
| `atr_wilder()` (pandas) | `_atr()` (numpy) | `strategies/vtrend_sm/strategy.py:111` |
| `rolling_high_shifted()` (pandas) | `_rolling_high_shifted()` (numpy) | `strategies/vtrend_sm/strategy.py:150` |
| `rolling_low_shifted()` (pandas) | `_rolling_low_shifted()` (numpy) | `strategies/vtrend_sm/strategy.py:163` |
| `annualized_realized_vol()` (pandas) | `_realized_vol()` (numpy) | `strategies/vtrend_sm/strategy.py:176` |
| `compute_vdo_base()` (pandas) | `_vdo()` (numpy) | `strategies/vtrend_sm/strategy.py:129` |
| `_clip_weight()` | `_clip_weight()` | `strategies/vtrend_sm/strategy.py:202` |
| `_warmup_start()` | `_compute_warmup()` | `strategies/vtrend_sm/strategy.py:276` |
| `BacktestResult` | N/A (engine handles) | `v10/core/types.py:BacktestResult` |
| `CostModel` | N/A (engine handles) | `v10/core/types.py:CostConfig` |
| `_execute_target_weights()` | N/A (engine handles) | `v10/core/engine.py:BacktestEngine` |

### Registration Points

| Registration File | Symbol to Add | Pattern File/Line |
|-------------------|--------------|-------------------|
| `v10/core/config.py` | `_VTREND_SM_FIELDS`, `"vtrend_sm"` in `_KNOWN_STRATEGIES` | `config.py:33-41` (vtrend pattern) |
| `v10/research/candidates.py` | `_VTREND_SM_FIELDS`, branches in `load_candidates()` + `build_strategy()` | `candidates.py:93-105, 152-176` |
| `validation/strategy_factory.py` | `(VTrendSMStrategy, VTrendSMConfig)` in `STRATEGY_REGISTRY` | `strategy_factory.py:24-30` |
| `v10/cli/backtest.py` | `VTrendSMStrategy` in `STRATEGY_REGISTRY` | `backtest.py:45-49` |
