# P3.1 — Audit Sizing Primitive & Freeze Spec for X0 Phase 3

## SUMMARY

Audited repo for sizing primitives, engine fractional support, and X0 Phase 2 baseline.
Found 3 implementations of the same vol-target formula across 5+ files. Chose SM/LATCH's
`_realized_vol` + LATCH's `vol_floor` as the canonical primitive. Engine natively supports
fractional `target_exposure` — SM and LATCH already use it in production. Froze minimal
spec for Phase 3: 3 new config fields, 1 new indicator, zero new signals, guaranteed
timing parity with Phase 2.

## FILES_INSPECTED

| File | Purpose | Key Finding |
|------|---------|-------------|
| `strategies/vtrend_x0_e5exit/strategy.py` | X0 Phase 2 strategy | `target_exposure=1.0` hardcoded at L169 |
| `strategies/vtrend_sm/strategy.py` | SM strategy (sizing source) | `_realized_vol` + `target_vol/max(rv, EPS)`, `_clip_weight` |
| `strategies/latch/strategy.py` | LATCH strategy (sizing source) | Same `_realized_vol` + `vol_floor=0.08` safety |
| `v10/core/types.py` | Signal dataclass | `target_exposure: float \| None` supports 0.0-1.0 |
| `v10/core/engine.py` | BacktestEngine | `_apply_target_exposure` handles fractional natively |
| `v10/core/execution.py` | Portfolio + ExecutionModel | `buy/sell` work with any qty, fees correct |
| `research/position_sizing.py` | Vol-target study | `compute_rolling_vol(cl, window=60)`, `sim_sized`, validated |
| `research/results/position_sizing.json` | Study results | target_vol=0.15: avg_frac=0.34, Sharpe=1.527, Calmar=1.609 |
| `research/signal_vs_sizing.py` | Factorial: signal x sizing | 5 signals x 3 sizings, confirms vol-target improves Sharpe |
| `research/regime_sizing.py` | Regime-conditional sizing | Same vol-target pattern |
| `research/x0/p2_4_benchmark.py` | Phase 2 vectorized sim | 100% allocation, no fractional support |

## FILES_CHANGED

| File | Action | Detail |
|------|--------|--------|
| `research/x0/search_log.md` | UPDATED | Added P3.1 section (~80 lines) |

No strategy, config, or registration files were modified. This is an audit-only phase.

## BASELINE_MAPPING

| Entity | Source | Role in Phase 3 |
|--------|--------|-----------------|
| X0 Phase 2 (`vtrend_x0_e5exit`) | `strategies/vtrend_x0_e5exit/` | Timing baseline (entry/exit timestamps) |
| SM `_realized_vol` | `strategies/vtrend_sm/strategy.py:176-199` | Vol estimator (copy) |
| SM `_clip_weight` | `strategies/vtrend_sm/strategy.py:202-209` | Weight clipping (copy) |
| LATCH `vol_floor` | `strategies/latch/strategy.py:69` | Safety parameter (default 0.08) |
| SM `target_vol` | `strategies/vtrend_sm/strategy.py:53` | Default 0.15 |
| SM `vol_lookback` | `strategies/vtrend_sm/strategy.py:54,88` | Default 120 (= slow_period) |

## COMMANDS_RUN

```
# No commands — pure audit via file inspection.
# All findings from Read/Grep of existing files.
```

## RESULTS

### SIZING_PRIMITIVE_AUDIT

Three implementations of the vol-target formula exist in the repo:

**1. SM `_realized_vol` (strategies/vtrend_sm/strategy.py:176-209)**
```python
def _realized_vol(close, lookback, bars_per_year):
    # Rolling std(ddof=0) of log returns * sqrt(bars_per_year)
    # Loop-based, precomputed on full array in on_init
    # First valid output at index `lookback` (= 120)
```
- Sizing: `target_vol / max(rv, EPS)`, `_clip_weight(w, min_weight=0.0)` → [0, 1]
- Defaults: `target_vol=0.15`, `vol_lookback=120` (= slow_period)
- Also has intratrade rebalance (SM-specific, NOT wanted)

**2. LATCH `_realized_vol` (strategies/latch/strategy.py:175-197)**
- IDENTICAL function body to SM's version
- Sizing: `target_vol / max(rv, vol_floor, EPS)`, `_clip_weight(w, max_pos, min_weight)` → [0, max_pos]
- Defaults: `target_vol=0.12`, `vol_lookback=120`, `vol_floor=0.08`, `max_pos=1.0`
- Also has intratrade rebalance (LATCH-specific, NOT wanted)

**3. position_sizing.py `compute_rolling_vol` (research/position_sizing.py:138-161)**
- Vectorized cumsum implementation (faster than loop)
- Same formula: population std × sqrt(6 × 365.25)
- Defaults: `VOL_WIN=60` (different from SM/LATCH)
- Sizing: `min(1.0, vol_target / rv)`, NaN guard: skip entry if rv NaN or <1e-8
- Validated in A3: target_vol=0.15 → Sharpe 1.527, Calmar 1.609, avg_frac=0.34

**All three are mathematically equivalent.** Same formula, same annualization. Only
differences: lookback window (60 vs 120), implementation (loop vs vectorized), and
whether vol_floor is used.

### FRACTIONAL_ENGINE_SUPPORT

**Status: FULLY SUPPORTED. No blockers.**

| Component | Support Level | Evidence |
|-----------|--------------|---------|
| `Signal.target_exposure` | 0.0-1.0 float | `v10/core/types.py:132` |
| `Engine._apply_target_exposure` | Full | Clamps to [0,1], computes delta, buys/sells. L279-322. |
| `Portfolio.buy` | Full | Handles any qty, cash-constrained clamp. L106-160. |
| `Portfolio.sell` | Full | Caps at holdings, records Trade when flat. L162-196. |
| Fee calculation | Correct | `qty * fill_px * fee_rate` — scales with qty. L117, L174. |
| Trade recording | Correct | Tracks weighted-avg entry, qty, PnL. L200-230. |
| `_EXPO_THRESHOLD` | 0.005 | Min weight 0.15/3.0=0.05 >> 0.005. No risk of skipped entry. |

SM and LATCH **already use fractional signals** in production via this exact path.
Both pass all tests (56/56 SM, 71/71 LATCH as of last audit).

**Vectorized sim caveat**: Current X0 benchmark sims (`p2_4_benchmark.py`) use 100%
allocation. Phase 3 vectorized sim needs modification: `invest = weight * cash` at
entry, keep remaining cash. This is a well-understood pattern (see `position_sizing.py:sim_sized`
lines 293-301).

### PHASE3_FROZEN_SPEC

**Strategy name**: `vtrend_x0_volsize`
**STRATEGY_ID**: `"vtrend_x0_volsize"`

**Config (13 fields = Phase 2's 10 + 3 new):**

| # | Field | Type | Default | Source | New? |
|---|-------|------|---------|--------|------|
| 1 | slow_period | float | 120.0 | Phase 2 | |
| 2 | trail_mult | float | 3.0 | Phase 2 | |
| 3 | vdo_threshold | float | 0.0 | Phase 2 | |
| 4 | d1_ema_period | int | 21 | Phase 2 | |
| 5 | atr_period | int | 14 | Phase 2 | |
| 6 | vdo_fast | int | 12 | Phase 2 | |
| 7 | vdo_slow | int | 28 | Phase 2 | |
| 8 | ratr_cap_q | float | 0.90 | Phase 2 | |
| 9 | ratr_cap_lb | int | 100 | Phase 2 | |
| 10 | ratr_period | int | 20 | Phase 2 | |
| 11 | target_vol | float | 0.15 | SM | NEW |
| 12 | vol_lookback | int | 120 | SM | NEW |
| 13 | vol_floor | float | 0.08 | LATCH | NEW |

**Indicators (same as Phase 2 + 1 new):**

| Indicator | Source | Changed? |
|-----------|--------|----------|
| ema_fast | Phase 2 | No |
| ema_slow | Phase 2 | No |
| ratr | Phase 2 | No |
| vdo | Phase 2 | No |
| d1_regime_ok | Phase 2 | No |
| realized_vol | SM/LATCH `_realized_vol` | NEW |

**Entry logic (timing IDENTICAL to Phase 2, only size changes):**
```
if flat AND trend_up AND vdo > threshold AND regime_ok:
    rv = realized_vol[i]
    if isnan(rv):
        weight = 1.0  # fallback: Phase 2 behavior
    else:
        weight = target_vol / max(rv, vol_floor)
        weight = clip(weight, 0.0, 1.0)
    in_position = True
    peak_price = price
    return Signal(target_exposure=weight, reason="x0_entry")
```

**Exit logic (IDENTICAL to Phase 2):**
```
if long:
    peak = max(peak, price)
    if price < peak - trail_mult * ratr:
        return Signal(target_exposure=0.0, reason="x0_trail_stop")
    if trend_down:
        return Signal(target_exposure=0.0, reason="x0_trend_exit")
```

**Critical design decision — rv NaN fallback:**
If `realized_vol[i]` is NaN at an entry bar, weight defaults to 1.0 (Phase 2 behavior).
This guarantees entry TIMING parity with Phase 2 in all edge cases. In practice, rv is
valid from bar 120, and the first possible entry in the reporting window is at bar 2190+,
so the fallback will never trigger during normal operation.

**No rebalance.** Weight is frozen from entry to exit. The `_in_position` boolean
prevents any mid-trade signals (same as Phase 2). No `state.exposure` is consulted.

### DEFAULTS_SOURCE

| Parameter | Value | Source | Validation |
|-----------|-------|--------|------------|
| target_vol | 0.15 | `VTrendSMConfig.target_vol` (SM default) | MEMORY.md "vol-target 15%"; position_sizing.py A3: Sharpe 1.527 |
| vol_lookback | 120 | `VTrendSMConfig.vol_lookback` (= slow_period) | SM convention; matches trend timescale |
| vol_floor | 0.08 | `LatchConfig.vol_floor` (LATCH default) | Structural safety; max weight = 0.15/0.08 = 1.875 → clipped to 1.0 |

**No tuning, no sweep.** All defaults come from existing modules with documented provenance.
If the repo had no suitable primitive, this section would state fallback spec. But all 3
defaults have clear, auditable sources.

### FILE_PLAN

| # | File | Action | Lines (est) |
|---|------|--------|-------------|
| 1 | `strategies/vtrend_x0_volsize/__init__.py` | CREATE | 0 (empty) |
| 2 | `strategies/vtrend_x0_volsize/strategy.py` | CREATE | ~290 |
| 3 | `configs/vtrend_x0_volsize/vtrend_x0_volsize_default.yaml` | CREATE | ~20 |
| 4 | `tests/test_vtrend_x0_volsize.py` | CREATE | ~280 |
| 5 | `v10/core/config.py` | EDIT | +~15 (fields, validation, registry) |
| 6 | `validation/strategy_factory.py` | EDIT | +1 (STRATEGY_REGISTRY) |
| 7 | `v10/cli/backtest.py` | EDIT | +1 (STRATEGY_REGISTRY) |
| 8 | `v10/research/candidates.py` | EDIT | +~10 (fields, load, build) |

**strategy.py structure** (copy Phase 2 + add `_realized_vol` from SM + modify entry):
- Docstring with Phase 3 description
- `VTrendX0VolsizeConfig` dataclass (13 fields)
- `VTrendX0VolsizeStrategy` class
  - `on_init`: precompute all Phase 2 indicators + `_rv = _realized_vol(...)`
  - `on_bar`: Phase 2 logic, entry emits `Signal(target_exposure=weight)` instead of `1.0`
  - `on_after_fill`: pass (same as Phase 2)
- Helper functions: `_ema`, `_robust_atr`, `_vdo`, `_realized_vol` (all copied)

### TEST_PLAN

| # | Test Class | Tests | Description |
|---|-----------|-------|-------------|
| 1 | TestEntryTimingParity | 1 | Entry timestamps match Phase 2 (engine-based, 5000+ bar window) |
| 2 | TestExitTimingParity | 1 | Exit timestamps match Phase 2 |
| 3 | TestTradeCountParity | 1 | Same number of trades as Phase 2 |
| 4 | TestFractionalExposure | 2 | When rv > target_vol, entry exposure < 1.0; verify expected weight |
| 5 | TestFullExposure | 1 | When rv very low, weight clipped to 1.0 |
| 6 | TestNoRebalance | 1 | No signals emitted between entry and exit |
| 7 | TestVolFloor | 1 | Weight bounded: target_vol/vol_floor when rv < vol_floor |
| 8 | TestRvNaNFallback | 1 | If rv NaN at entry, weight = 1.0 (timing parity) |
| 9 | TestConfigLoad | 5 | All 13 fields, field_count, defaults, edge values |
| 10 | TestD1RegimeNoLookahead | 2 | Inherited from Phase 2 |
| 11 | TestRegistration | 3 | Strategy in all 4 registries |
| Total | | ~19 | |

### RISKS_AND_AMBIGUITIES

| Risk | Severity | Mitigation |
|------|----------|------------|
| rv NaN at entry bar during reporting | LOW | Fallback to weight=1.0 (guaranteed timing parity). rv valid from bar 120, reporting starts at bar 2190. |
| `_EXPO_THRESHOLD` skipping small weight | NEGLIGIBLE | Min practical weight = 0.15/3.0 = 0.05 >> 0.005. BTC annualized vol never exceeds ~200%. |
| Vectorized sim for Phase 3 benchmark needs new sim function | EXPECTED | Pattern exists in position_sizing.py:sim_sized (lines 293-301). Straightforward adaptation. |
| Portfolio `return_pct` is per-BTC, not per-NAV | KNOWN | Same as Phase 2. Per-NAV return computed from equity curve. Not a bug. |
| 1-bar rv warmup gap (bar 119 ratr valid, bar 120 rv valid) | NEGLIGIBLE | Fallback to weight=1.0 covers it. Never triggers during reporting period. |

### ACCEPTANCE_CRITERIA_FOR_PHASE3

| # | Criterion | Test Method |
|---|-----------|-------------|
| AC1 | Entry timestamps IDENTICAL to Phase 2 | Engine-based: compare entry_ts_ms of all trades |
| AC2 | Exit timestamps IDENTICAL to Phase 2 | Engine-based: compare exit_ts_ms of all trades |
| AC3 | Trade count IDENTICAL to Phase 2 | len(trades) match |
| AC4 | Entry reasons IDENTICAL | All entry_reason == "x0_entry" |
| AC5 | Exit reasons IDENTICAL | All exit_reason in {"x0_trail_stop", "x0_trend_exit"}, matching Phase 2 |
| AC6 | PnL differences ONLY from size | For each matched trade: if weight=1.0, PnL identical; if weight<1.0, PnL proportionally smaller |
| AC7 | No intratrade signals | Between entry fill and exit fill, no other fills exist |
| AC8 | rv NaN → weight=1.0 | If rv NaN at any entry bar, entry still occurs with full allocation |
| AC9 | All Phase 2 tests still pass | 17/17 Phase 2 tests + 872/872 full suite |
| AC10 | Weight formula correct | `target_vol / max(rv, vol_floor)` clipped to [0, 1], verified per-trade |

**Phase 3 is CLEAN if and only if AC1-AC10 all pass.**

If fractional engine semantics cause ANY timestamp divergence from Phase 2
(different entry bar, different exit bar), that is a BLOCKER — not an acceptable tradeoff.

## BLOCKERS

None. All prerequisites verified:
- Sizing primitive exists and is proven (SM/LATCH `_realized_vol`)
- Engine supports fractional exposure natively (SM/LATCH use it)
- Defaults have documented provenance (no fabrication)
- Timing parity is structurally guaranteed (rv NaN fallback + boolean `_in_position` guard)

## NEXT_READY

P3.1 audit and spec freeze complete. Ready for P3.2 (implementation) when authorized.
Not proceeding.
