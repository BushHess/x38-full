# LATCH Audit & Discovery Report

**Date**: 2026-03-05
**Prerequisite**: vtrend-p-03-harden.md (COMPLETE)

---

## 1. STATUS: READY_FOR_LATCH_IMPLEMENT_AS_IS

No blocking bugs, ambiguities, or design conflicts found. The algorithm is fully
specified with a normative spec (`LATCH_ALGORITHM_SPEC.md`), cleanly implemented
in source with 12 tests, and maps directly onto the existing btc-spot-dev Strategy
pattern. Two new concepts (hysteretic regime, 3-state machine) are self-contained
and do not require engine changes.

---

## 2. Source Location & File Map

Package: `/var/www/trading-bots/Latch/research/Latch/` (7 source files + 2 doc files)

| File | LOC | Role |
|---|---|---|
| `config.py` | 154 | `LatchParams` (13 core fields) + `VDOOverlayParams` (16 fields) + `CostModel` |
| `state_machine.py` | 78 | `LatchState` enum (OFF/ARMED/LONG) + `compute_hysteretic_regime()` |
| `indicators.py` | 114 | `ema`, `atr_wilder`, `annualized_realized_vol`, `rolling_high_shifted`, `rolling_low_shifted`, `compute_vdo_base`, `validate_market_frame` |
| `strategy.py` | 219 | `run_latch()` main function + `_warmup_start`, `_clip_weight` |
| `backtest.py` | 351 | `execute_target_weights()`, `BacktestResult`, `TradeRecord`, `compute_metrics` |
| `overlays.py` | 77 | `compute_vdo_diagnostics()`, `apply_vdo_overlay()` (size_mod, throttle, ranker) |
| `__init__.py` | 28 | Public API re-exports |
| `LATCH_ALGORITHM_SPEC.md` | 399 | Normative reconstruction-grade specification |
| `README.md` | 50 | Usage example + core design summary |

Test file: `/var/www/trading-bots/Latch/research/test_latch.py` (12 tests)

---

## 3. Executable Specification

### 3.1 Algorithm Identity

- **Name**: LATCH (renamed from research identifier VTREND-HX)
- **Domain**: BTC/ETH spot, long-only, H4 or Daily timeframe
- **Philosophy**: Price-first trend engine. Hysteretic regime reduces whipsaw. VDO excluded from core alpha.
- **Key distinction from SM/P**: 3-state machine with ARMED state + hysteretic regime with memory

### 3.2 Core Indicators (6)

All indicators use close-of-bar data only (no look-ahead):

| Indicator | Formula | Source Function |
|---|---|---|
| ema_fast | `EMA(close, fast)` | `indicators.ema()` |
| ema_slow | `EMA(close, slow)` | `indicators.ema()` |
| hh_entry | `max(high[i-entry_n : i])` (excludes current bar) | `indicators.rolling_high_shifted()` |
| ll_exit | `min(low[i-exit_n : i])` (excludes current bar) | `indicators.rolling_low_shifted()` |
| atr | Wilder ATR with SMA seed | `indicators.atr_wilder()` |
| rv | `rolling_std(log_returns, vol_lookback, ddof=0) * sqrt(bpy)` | `indicators.annualized_realized_vol()` |

Slope reference: `ema_slow_slope_ref = ema_slow.shift(slope_n)`

### 3.3 Hysteretic Regime (the "Latch")

This is the core differentiator from SM/P. The regime has **memory** — it stays in
its previous state until an explicit trigger fires.

**Triggers:**
- ON trigger: `ema_fast > ema_slow AND ema_slow > ema_slow_slope_ref`
- OFF trigger: `ema_fast < ema_slow AND ema_slow < ema_slow_slope_ref`

**State update:**
```
if regime_prev == OFF and ON_trigger → regime = ON
if regime_prev == ON  and OFF_trigger → regime = OFF
otherwise → regime = regime_prev  (HYSTERESIS)
```

**Critical invariant**: `regime_off ≠ NOT regime_on`. The regime can be in an
intermediate zone where neither trigger fires, and it holds its last state.

**Derived arrays** (precomputed on full bar arrays):
- `regime_on[i]`: current regime state (bool)
- `on_trigger[i]`: instantaneous ON condition (bool)
- `off_trigger[i]`: instantaneous OFF condition (bool)
- `flip_on[i]`: transition event ON→ (bool)
- `flip_off[i]`: transition event →OFF (bool)

**NaN handling**: During NaN indicator bars, regime state is frozen at its last
value (preserves hysteresis).

### 3.4 State Machine (3 states)

```
States: OFF (0), ARMED (1), LONG (2)

OFF:
  if regime_on AND breakout_ok → LONG (entry_signal)
  elif regime_on              → ARMED
  else                        → stay OFF

ARMED:
  if regime_off_trigger       → OFF
  elif regime_on AND breakout → LONG (entry_signal)
  else                        → stay ARMED

LONG:
  if floor_break OR regime_flip_off → OFF (exit_signal)
  else                              → stay LONG
```

Where:
- `breakout_ok = close > hh_entry` (strict >)
- `adaptive_floor = max(ll_exit, ema_slow - atr_mult * ATR)`
- `floor_break = close < adaptive_floor` (strict <)

**ARMED semantics**: Regime is ON but no breakout yet. Provides "latching" — the
strategy remembers that conditions were favorable and is ready to enter on breakout,
even if the ON trigger no longer fires on that specific bar (hysteresis holds
regime ON).

### 3.5 Sizing

When LONG:
```
rv_i = max(rv, vol_floor, EPS)
raw_weight = target_vol / rv_i
weight = clip(raw_weight, 0, max_pos)
if weight < min_weight: weight = 0
```

When FLAT (OFF or ARMED):
```
weight = 0
```

### 3.6 Rebalance Gate

Signal at close(i), execution at open(i+1). Rebalance fires when:
- `|target_weight - current_weight| >= min_rebalance_weight_delta`
- OR zero-crossing (entering/exiting position)

### 3.7 VDO Overlay (Optional, Default OFF)

The VDO overlay is applied AFTER vol-targeted sizing, only when LONG. It does NOT
gate entry. Default mode is "none" (no effect).

Three modes:
- **size_mod**: 4-tier z-score interpolation → multiplier on base weight
- **throttle**: 2-tier z-score reduction when VDO is strongly negative
- **ranker**: passthrough (reserved for multi-coin cross-sectional ranking)

Z-score computation: `(vdo - rolling_mean(vdo, z_lookback)) / max(rolling_std(vdo, z_lookback), EPS)`

### 3.8 Parameters (13 core + 16 VDO overlay)

**Core parameters (LatchParams):**

| Field | H4 Default | Daily Default | Description |
|---|---|---|---|
| slow | 120 | 50 | EMA slow period |
| fast | 30 | 12 | EMA fast period |
| slope_n | 6 | 6 | Slope lookback for regime |
| entry_n | 60 | 20 | Rolling high lookback |
| exit_n | 30 | 10 | Rolling low lookback |
| atr_period | 14 | 14 | Wilder ATR period |
| atr_mult | 2.0 | 2.0 | ATR multiplier for exit floor |
| vol_lookback | 120 | 30 | Realized vol lookback |
| target_vol | 0.12 | 0.12 | Annualized vol target |
| vol_floor | 0.08 | 0.08 | Min vol for sizing denominator |
| max_pos | 1.0 | 1.0 | Maximum position weight |
| min_weight | 0.0 | 0.0 | Minimum weight threshold |
| min_rebalance_weight_delta | 0.05 | 0.05 | Rebalance threshold |

**VDO overlay parameters (VDOOverlayParams):**

| Field | Default | Description |
|---|---|---|
| mode | "none" | Overlay mode: none/size_mod/throttle/ranker |
| diagnostics_enabled | True | Log VDO diagnostics (source-only, skip in port) |
| z_lookback | 120 | Rolling window for z-score |
| vdo_fast | 12 | VDO fast EMA period |
| vdo_slow | 28 | VDO slow EMA period |
| strong_pos_z | 1.0 | Z-score threshold: strong positive |
| neutral_z | 0.0 | Z-score threshold: neutral |
| mild_neg_z | -0.5 | Z-score threshold: mild negative |
| strong_neg_z | -1.0 | Z-score threshold: strong negative |
| size_mult_strong_pos | 1.00 | size_mod multiplier: strong positive |
| size_mult_neutral | 0.80 | size_mod multiplier: neutral |
| size_mult_mild_neg | 0.55 | size_mod multiplier: mild negative |
| size_mult_strong_neg | 0.25 | size_mod multiplier: strong negative |
| throttle_mult_mild_neg | 0.75 | throttle multiplier: mild negative |
| throttle_mult_strong_neg | 0.50 | throttle multiplier: strong negative |

**Note**: All parameters are explicit — no auto-derivation (unlike SM/P).

---

## 4. Comparison: LATCH vs SM vs P

| Feature | SM | P | LATCH |
|---|---|---|---|
| **State model** | Binary (active/flat) | Binary (active/flat) | 3-state (OFF/ARMED/LONG) |
| **Regime** | Instantaneous per-bar check | close > ema_slow (price-only) | Hysteretic with memory |
| **Regime ON** | fast > slow AND slow > slope_ref | close > ema_slow AND ema_slow > slope_ref | fast > slow AND slow > slope_ref (with hysteresis) |
| **Regime OFF** | NOT regime_on (instantaneous) | NOT regime_ok (instantaneous) | fast < slow AND slow < slope_ref (explicit trigger, hysteretic) |
| **Fast EMA** | Yes (auto: max(5, slow//4)) | No | Yes (explicit: fast=30) |
| **Entry** | regime_ok AND breakout AND vdo_ok | regime_ok AND slope_ok AND breakout | regime_on AND breakout |
| **Exit: floor** | close < max(ll, ema_s - mult*ATR) | close < max(ll, ema_s - mult*ATR) | close < max(ll, ema_s - mult*ATR) |
| **Exit: regime** | Optional (exit_on_regime_break) | None | Always active (regime_flip_off kill-switch) |
| **VDO in core** | Optional entry filter | None | None (overlay only, default OFF) |
| **Sizing denominator** | max(rv, EPS) | max(rv, EPS) | max(rv, vol_floor, EPS) |
| **Position cap** | Hardcoded 1.0 | Hardcoded 1.0 | Configurable max_pos (default 1.0) |
| **Auto-derivation** | entry_n, exit_n, fast, vol_lookback | entry_n, exit_n, vol_lookback | None (all explicit) |
| **atr_mult default** | 3.0 | 1.5 | 2.0 |
| **target_vol default** | 0.15 | 0.12 | 0.12 |
| **Param count** | 16 | 10 | 13 core + 15 VDO overlay |

### Key algorithmic differences requiring new code:

1. **Hysteretic regime computation** — new function, not in SM/P
2. **3-state machine** — ARMED state tracking, new transition logic
3. **vol_floor parameter** — new sizing floor (SM/P use only EPS)
4. **max_pos parameter** — configurable position cap (SM/P hardcode 1.0)
5. **VDO overlay system** — 16-param overlay with z-score tiers (SM has simple boolean filter)

### Code reusable from SM/P (frozen artifact convention):

1. `_ema()` — identical
2. `_atr()` — identical (D2 bar-0 divergence shared)
3. `_rolling_high_shifted()` — identical
4. `_rolling_low_shifted()` — identical
5. `_realized_vol()` — identical
6. `_vdo()` — copy from SM (needed for VDO overlay)

---

## 5. Bug / Ambiguity / Warning Audit

### Bugs Found: 0

No bugs identified in the LATCH source implementation. All code paths are
consistent with the normative spec.

### Ambiguities Found: 0

The normative spec (`LATCH_ALGORITHM_SPEC.md` Section 2.4) explicitly addresses
the one potential ambiguity — whether ARMED→OFF uses `off_trigger` vs `flip_off`:

> "Sự kiện 'regime chuyển OFF đã xác nhận' có thể được biểu diễn bởi:
> `regime OFF trigger` khi trước đó đang ON, hoặc `regime_flip_off`.
> Hai biểu diễn trên là tương đương."

This is provably correct: ARMED and LONG are only entered when regime is ON.
The first `off_trigger` while regime is ON always produces `flip_off = True`.
So the representations are equivalent in context.

The source code uses:
- ARMED → OFF: `regime_off_trigger` (instantaneous condition)
- LONG → OFF: `regime_flip_off` (transition event)

Both are correct. The port should replicate the source exactly.

### Warnings (non-blocking):

| # | Warning | Impact | Shared with SM/P |
|---|---|---|---|
| W1 | BARS_PER_YEAR_4H = 2190.0 (365.0 * 6.0) vs btc-spot-dev convention 2191.5 (365.25 * 6.0) | < 0.07% difference in rv and Sharpe | Yes |
| W2 | ATR bar-0 prev_close: source uses `close[0]`; target numpy _atr uses `high[0]`/`low[0]` | Zero effect on real data (high-low dominates at bar 0) | Yes |
| W3 | `diagnostics_enabled` field has no target equivalent (btc-spot-dev strategies return Signals only, no diagnostic columns) | Skip field in port | No |
| W4 | Source `_clip_weight` in strategy.py uses `np.clip`; backtest.py uses `min/max` — functionally identical | No behavioral difference | No |
| W5 | Backtest engine `execute_target_weights` re-clips to max_pos=1.0 hardcoded — redundant with strategy clip since max_pos ∈ (0, 1] | Not ported (btc-spot-dev engine handles execution) | N/A |

---

## 6. Transformation Matrix

### 6.1 New Files to Create

| File | Description |
|---|---|
| `strategies/latch/__init__.py` | Exports STRATEGY_ID, LatchConfig, LatchStrategy |
| `strategies/latch/strategy.py` | Config + indicators + hysteretic regime + strategy class |
| `configs/latch/latch_default.yaml` | Default YAML config for validation pipeline |
| `tests/test_latch.py` | Unit + integration tests |

### 6.2 Files to Modify (5 integration touchpoints)

| File | Change | Pattern |
|---|---|---|
| `v10/core/config.py` | Import LatchConfig, add `_LATCH_FIELDS`, add `"latch"` to `_KNOWN_STRATEGIES`, add field mapping in `strategy_fields_by_name`, add validation branch | Identical to SM/P |
| `v10/cli/backtest.py` | Import LatchStrategy, add `"latch"` to STRATEGY_REGISTRY | Identical to SM/P |
| `validation/strategy_factory.py` | Import LatchConfig + LatchStrategy, add `"latch"` to STRATEGY_REGISTRY | Identical to SM/P |
| `v10/research/candidates.py` | Import LatchConfig + LatchStrategy, add `_LATCH_FIELDS`, add branches in `load_candidates()` and `build_strategy()` | Identical to SM/P |
| `validation/config_audit.py` | Add VDO conditional allowlist in `_expand_conditional_allowlist()` (when vdo_mode == "none", allowlist all vdo_* fields) | New pattern — follows existing `add_when_disabled` convention |

### 6.3 Config Design: Flattening VDOOverlayParams

The source uses a nested `VDOOverlayParams` dataclass inside `LatchParams`. The
btc-spot-dev target requires flat config for:
- YAML loading (no nested strategy params)
- ConfigProxy field access tracking
- `_expand_conditional_allowlist` conditional field handling

**Decision**: Flatten all VDO overlay fields with `vdo_` prefix. Skip
`diagnostics_enabled` (no target mechanism).

Resulting `LatchConfig` will have 28 fields (13 core + 15 VDO overlay).

The `_expand_conditional_allowlist` should be updated with:
```python
if values.get("vdo_mode") == "none":
    allow.update({key for key in values if key.startswith("vdo_")})
```

### 6.4 Config Field Mapping

| Source (LatchParams) | Target (LatchConfig) | Rename Rationale |
|---|---|---|
| `slow` | `slow_period` | Consistency with SM/P naming |
| `fast` | `fast_period` | Consistency with SM/P naming |
| `slope_n` | `slope_lookback` | Consistency with SM/P naming |
| `entry_n` | `entry_n` | — |
| `exit_n` | `exit_n` | — |
| `atr_period` | `atr_period` | — |
| `atr_mult` | `atr_mult` | — |
| `vol_lookback` | `vol_lookback` | — |
| `target_vol` | `target_vol` | — |
| `vol_floor` | `vol_floor` | NEW field (not in SM/P) |
| `max_pos` | `max_pos` | NEW field (not in SM/P) |
| `min_weight` | `min_weight` | — |
| `min_rebalance_weight_delta` | `min_rebalance_weight_delta` | — |
| `vdo_overlay.mode` | `vdo_mode` | Flatten |
| `vdo_overlay.z_lookback` | `vdo_z_lookback` | Flatten |
| `vdo_overlay.vdo_fast` | `vdo_fast` | Flatten |
| `vdo_overlay.vdo_slow` | `vdo_slow` | Flatten |
| `vdo_overlay.strong_pos_z` | `vdo_strong_pos_z` | Flatten |
| `vdo_overlay.neutral_z` | `vdo_neutral_z` | Flatten |
| `vdo_overlay.mild_neg_z` | `vdo_mild_neg_z` | Flatten |
| `vdo_overlay.strong_neg_z` | `vdo_strong_neg_z` | Flatten |
| `vdo_overlay.size_mult_strong_pos` | `vdo_size_mult_strong_pos` | Flatten |
| `vdo_overlay.size_mult_neutral` | `vdo_size_mult_neutral` | Flatten |
| `vdo_overlay.size_mult_mild_neg` | `vdo_size_mult_mild_neg` | Flatten |
| `vdo_overlay.size_mult_strong_neg` | `vdo_size_mult_strong_neg` | Flatten |
| `vdo_overlay.throttle_mult_mild_neg` | `vdo_throttle_mult_mild_neg` | Flatten |
| `vdo_overlay.throttle_mult_strong_neg` | `vdo_throttle_mult_strong_neg` | Flatten |
| `vdo_overlay.diagnostics_enabled` | *(skipped)* | No target mechanism |

### 6.5 Indicator Mapping

| Source (indicators.py) | Target (strategy.py) | Source |
|---|---|---|
| `ema(values, span)` — pandas | `_ema(series, period)` — numpy | Copy from SM/P |
| `atr_wilder(h, l, c, period)` — pandas | `_atr(h, l, c, period)` — numpy | Copy from SM/P |
| `rolling_high_shifted(h, lookback)` — pandas | `_rolling_high_shifted(h, lookback)` — numpy | Copy from SM/P |
| `rolling_low_shifted(l, lookback)` — pandas | `_rolling_low_shifted(l, lookback)` — numpy | Copy from SM/P |
| `annualized_realized_vol(lr, lb, bpy)` — pandas | `_realized_vol(close, lb, bpy)` — numpy | Copy from SM/P |
| `compute_vdo_base(vol, taker, fast, slow)` — pandas | `_vdo(close, h, l, vol, taker, fast, slow)` — numpy | Copy from SM |
| `compute_hysteretic_regime(fast, slow, slope_n)` — pandas+numpy | `_compute_hysteretic_regime(ema_fast, ema_slow, slope_ref)` — numpy | **NEW** |
| `apply_vdo_overlay(base_weight, vdo_zscore, params)` | `_apply_vdo_overlay(base_weight, vdo_z, config)` | **NEW** (inline in on_bar) |
| `validate_market_frame(df)` | *(not needed)* | Engine handles validation |

### 6.6 Strategy Class Mapping

| Source Concept | Target Implementation |
|---|---|
| `LatchState` enum | Private constants or IntEnum in strategy.py |
| `compute_hysteretic_regime()` precomputation | Call in `on_init()`, store result arrays |
| Main loop state machine | `on_bar()` with `self._state` field (3 values) |
| `_warmup_start()` | `_compute_warmup()` — same pattern as SM/P |
| `_clip_weight(w, max_pos, min_weight)` | `_clip_weight(w, max_pos, min_weight)` — add max_pos param |
| `target_weight_signal[i]` → `execute_target_weights()` | Return `Signal(target_exposure=weight)` |

### 6.7 `_clip_weight` Modification

SM/P: `_clip_weight(weight, min_weight) → clip to [0, 1]`
LATCH: `_clip_weight(weight, max_pos, min_weight) → clip to [0, max_pos]`

The LATCH version is a strict generalization. Keep `_clip_weight` local to
`strategies/latch/strategy.py` with the `max_pos` parameter.

### 6.8 `resolved()` Method

LATCH has no auto-derivation (all params explicit), but `resolved()` is still
needed for ConfigProxy allowlist compatibility. Implementation:

```python
def resolved(self) -> dict[str, Any]:
    return asdict(self)
```

---

## 7. New Concepts Requiring New Code

### 7.1 Hysteretic Regime Computation

**Source**: `state_machine.py:compute_hysteretic_regime()` (50 lines)

This function takes EMA fast/slow arrays and slope_n, computes the hysteretic
regime state with memory, and returns 5 boolean arrays + slope_ref.

**Target implementation**: A numpy-only `_compute_hysteretic_regime()` function
in `strategies/latch/strategy.py`. Called once in `on_init()`. The function takes
numpy arrays (not pandas Series) and returns the 5 boolean arrays.

The loop structure is causal (bar-by-bar forward pass, no look-ahead) and
cannot be vectorized. This is the same constraint as the source.

### 7.2 3-State Machine in on_bar()

The `on_bar()` method needs a `self._state` field with 3 values (OFF=0, ARMED=1,
LONG=2) instead of SM/P's binary `self._active`.

Key difference: SM/P compute regime_ok per-bar from raw indicators. LATCH reads
from precomputed `regime_on`, `off_trigger`, and `flip_off` arrays. This means
`on_init()` stores 5 additional arrays (or 3 — only `regime_on`, `off_trigger`,
`flip_off` are used in the state machine loop).

### 7.3 VDO Overlay in on_bar()

When `vdo_mode != "none"`, the strategy must:
1. Precompute VDO + z-score arrays in `on_init()` (using `_vdo()` + rolling z-score)
2. In `on_bar()` LONG branch, apply overlay to base weight before returning Signal

The overlay logic (size_mod interpolation, throttle tiers) is ~30 lines of
if/elif logic, translated from `overlays.py:apply_vdo_overlay()`.

### 7.4 vol_floor in Sizing

Simple addition to sizing formula:
```python
rv_i = max(rv, self._r["vol_floor"], EPS)  # vs SM/P: max(rv, EPS)
```

---

## 8. Known Non-Blocking Divergences (Port Decisions)

| # | Divergence | Decision | Rationale |
|---|---|---|---|
| D1 | ATR bar-0 prev_close: source `close[0]`, target `high[0]`/`low[0]` | Accept (shared with SM/P) | Zero effect on real data, washes out by bar 14 |
| D2 | BARS_PER_YEAR_4H: source 2190.0, btc-spot-dev sometimes uses 2191.5 | Use 2190.0 (match source, consistent with SM/P) | < 0.07% difference |
| D3 | Weight > 0 guard on entry | Add (shared with SM/P) | Prevents entering with weight=0. More correct than source. |
| D4 | Rebalance epsilon: target uses `- 1e-12` tolerance | Add (shared with SM/P) | Defensive against FP rounding |
| D5 | `diagnostics_enabled` field not ported | Skip | No target mechanism for diagnostic columns |

---

## 9. Parity-Validation Plan

### 9.1 Unit Tests (per indicator)

| Test | Description | Verification |
|---|---|---|
| T1: Config defaults | LatchConfig() matches LatchParams H4 defaults | Field-by-field comparison |
| T2: resolved() | Returns full dict with all fields | asdict(config) == config.resolved() |
| T3: _ema | vs pandas ewm(span, adjust=False) | rtol=1e-12 |
| T4: _atr | vs pandas atr_wilder | rtol=1e-10 |
| T5: _rolling_high_shifted | vs pandas high.shift(1).rolling().max() | exact (equal_nan) |
| T6: _rolling_low_shifted | vs pandas low.shift(1).rolling().min() | exact (equal_nan) |
| T7: _realized_vol | vs pandas log_returns.rolling().std(ddof=0) * sqrt(bpy) | rtol=1e-10 |
| T8: _clip_weight | 10+ edge cases (NaN, inf, 0, max_pos, min_weight) | exact |
| T9: _vdo | vs pandas VDO computation | rtol=1e-10 |

### 9.2 Hysteretic Regime Tests

| Test | Description |
|---|---|
| T10: Regime memory | Regime stays ON when neither trigger fires (verify hysteresis) |
| T11: ON trigger | Regime transitions OFF→ON when ON conditions met |
| T12: OFF trigger | Regime transitions ON→OFF when OFF conditions met |
| T13: NaN preservation | Regime freezes state during NaN bars |
| T14: flip_on/flip_off | Transition events fire only on actual state changes |

### 9.3 State Machine Tests

| Test | Description |
|---|---|
| T15: OFF→ARMED | Regime ON + no breakout → ARMED state |
| T16: OFF→LONG | Regime ON + breakout on same bar → LONG (entry signal) |
| T17: ARMED→LONG | Breakout while ARMED → LONG (entry signal) |
| T18: ARMED→OFF | Regime OFF trigger while ARMED → OFF |
| T19: LONG→OFF (floor) | close < adaptive_floor → OFF (exit signal, reason="latch_floor_exit") |
| T20: LONG→OFF (regime) | regime_flip_off → OFF (exit signal, reason="latch_regime_exit") |
| T21: Re-entry cycle | entry → exit → re-entry works correctly (no stuck state) |
| T22: Exit before rebalance | Exit fires before rebalance check when floor breached |

### 9.4 Sizing Tests

| Test | Description |
|---|---|
| T23: Vol-targeted sizing | weight = target_vol / max(rv, vol_floor, EPS) |
| T24: max_pos clipping | weight capped at max_pos (test with max_pos < 1.0) |
| T25: min_weight gate | weight < min_weight → 0.0 |
| T26: vol_floor effect | When rv < vol_floor, sizing uses vol_floor |

### 9.5 VDO Overlay Tests

| Test | Description |
|---|---|
| T27: mode=none | Overlay has no effect on weight |
| T28: size_mod tiers | Correct multiplier for each z-score tier |
| T29: size_mod interpolation | Smooth blending between mild_neg and strong_neg |
| T30: throttle tiers | Correct reduction for negative z-score |
| T31: ranker passthrough | Weight unchanged in ranker mode |
| T32: Re-clip after overlay | Weight re-clipped to [0, max_pos] after overlay |

### 9.6 Integration Tests

| Test | Description |
|---|---|
| T33: Registration in config.py | "latch" in _KNOWN_STRATEGIES, _LATCH_FIELDS correct |
| T34: Registration in backtest.py | "latch" in STRATEGY_REGISTRY |
| T35: Registration in strategy_factory.py | "latch" in STRATEGY_REGISTRY |
| T36: Registration in candidates.py | load_candidates and build_strategy work |
| T37: ConfigProxy allowlist | resolved() allowlists all fields |
| T38: VDO conditional allowlist | vdo_mode="none" allowlists all vdo_* fields |
| T39: Warmup correctness | No signals during warmup period |
| T40: Engine smoke test | BacktestEngine + LatchStrategy runs without crash |
| T41: P-vs-LATCH differences | Different atr_mult, fast_period, vol_floor produce different behavior |

### 9.7 Validation Pipeline

| Check | Description |
|---|---|
| lookahead | Verify no future data leakage |
| data_integrity | OHLC consistency |
| invariants | on_init + on_bar contract |
| config_unused_fields | All config fields consumed (via ConfigProxy) |
| churn_metrics | Trade frequency within bounds |
| cost_sweep | Performance under smart/base/harsh costs |

### 9.8 Cross-Validation Against Source

Run both source `run_latch()` and target `LatchStrategy` on identical data.
Compare state arrays, entry/exit signals, and target weights.

Expected tolerance:
- State arrays: exact match (after accounting for warmup difference)
- Target weights: rtol=1e-10 (FP rounding only)
- Metrics: within 1% (different execution engines, cost models)

---

## 10. Conformance Checklist (from LATCH_ALGORITHM_SPEC.md Section 11)

The port MUST satisfy all 10 conformance requirements:

| # | Requirement | Port Plan |
|---|---|---|
| 1 | Core indicator set (6 indicators, no extras) | Copy from SM/P + _compute_hysteretic_regime |
| 2 | Regime hysteresis with memory | New _compute_hysteretic_regime() in on_init |
| 3 | State machine OFF/ARMED/LONG with correct transitions | New on_bar() with self._state |
| 4 | Entry: regime ON + breakout, no extra hard gates | Faithful to source |
| 5 | Exit: adaptive floor + confirmed regime-OFF kill-switch | Both conditions in on_bar LONG branch |
| 6 | Sizing: realized-vol targeting with vol_floor | target_vol / max(rv, vol_floor, EPS) |
| 7 | Execution at next-open, no lookahead | Engine handles (no strategy changes needed) |
| 8 | Cost model: fee + spread + slippage | Engine handles (CostConfig) |
| 9 | Weight in [0, max_pos], long-only | _clip_weight with max_pos parameter |
| 10 | VDO not in core alpha (overlay only, default OFF) | vdo_mode="none" default, overlay applied post-sizing |

---

## 11. Handoff Notes for Prompt 5

1. **LATCH is fully audited and ready for implementation.** No bugs, no ambiguities.
   The normative spec confirms all design decisions in the source code.

2. **Two new concepts** to implement beyond SM/P pattern:
   - Hysteretic regime computation (~30 lines numpy loop, precomputed in on_init)
   - 3-state machine in on_bar (OFF/ARMED/LONG vs binary active/flat)

3. **Config flattening** required: 28 fields (13 core + 15 VDO overlay). The nested
   VDOOverlayParams must be flattened with `vdo_` prefix for YAML/ConfigProxy
   compatibility.

4. **5 integration touchpoints** — identical pattern to SM/P.

5. **6 indicators reusable** from SM/P (frozen artifact copies). 2 new functions
   needed: `_compute_hysteretic_regime()` and `_apply_vdo_overlay()`.

6. **41 tests planned** covering indicators, regime, state machine, sizing, VDO
   overlay, integration, and cross-validation.

7. **Source reference files** (read-only):
   - `Latch/research/Latch/config.py` (LatchParams, VDOOverlayParams)
   - `Latch/research/Latch/state_machine.py` (LatchState, compute_hysteretic_regime)
   - `Latch/research/Latch/indicators.py` (all indicator functions)
   - `Latch/research/Latch/strategy.py` (run_latch main function)
   - `Latch/research/Latch/overlays.py` (VDO overlay logic)
   - `Latch/research/Latch/LATCH_ALGORITHM_SPEC.md` (normative spec)
