# Report 01 -- Strategy and Engine Inventory (Code-Truth)

**Date**: 2026-03-05
**Namespace**: `research/eval_vtrend_latch_20260305/`
**Phase**: Step 1 -- Code-truth inventory, no backtests, no conclusions

---

## 0. Objective

Build an exact, auditable map of strategy semantics, engine semantics, existing evaluation sources, and confounders. All claims traced to code paths and line numbers. Where docs and code conflict, code wins.

## 0.1 Inputs Inspected

All files listed in the step instructions were read. Full dependency map in `artifacts/file_dependency_map.csv`. Key additional files discovered and read:

- `v10/research/objective.py` -- scoring function
- `validation/decision.py` -- decision policy (REJECT/PROMOTE)
- `validation/thresholds.py` -- `HARSH_SCORE_TOLERANCE = 0.2`
- `validation/suites/backtest.py` -- BacktestSuite
- `v10/strategies/base.py` -- Strategy ABC

## 0.2 Report 00 Read Confirmation

Report 00 (`reports/00_setup_and_scope.md`) read in full. All 6 research questions, 7 prohibitions, and 5 confounders noted.

---

## 1. Assumption Delta

### Assumptions from Report 00 that REMAIN VALID

1. **No git** -- repo is not git-initialized. Logical namespace created. VALID.
2. **All btc-spot-dev strategies share the same BacktestEngine** -- VALID. Confirmed at `v10/core/engine.py`. All strategies subclass `Strategy` from `v10/strategies/base.py` and run through the same `BacktestEngine.run()`.
3. **LATCH standalone has its own engine** -- VALID. `Latch/research/Latch/backtest.py:234` (`execute_target_weights`).
4. **LATCH was REJECTED** -- VALID. `results/eval_latch_vs_e0_full/reports/decision.json` verdict=REJECT, exit_code=2.
5. **Exposure mismatch ~5x** -- VALID. E0=0.4682, LATCH=0.0948 (harsh scenario).
6. **Fee drag difference** -- VALID. E0=7.84%/yr, LATCH=0.84%/yr (harsh scenario).

### Assumptions from Report 00 that NEED CORRECTION

7. **"LATCH Sharpe is HIGHER than E0 (1.44 vs 1.27)"** -- VALID numerically but **misleading**. These Sharpe ratios are computed on equity curves with fundamentally different exposure levels. A strategy at 9.5% exposure has lower equity curve volatility by construction, inflating Sharpe. Sharpe is NOT exposure-normalized here. CORRECTED: the comparison is not informative without exposure normalization.

8. **"SM vs E0 (run)"** -- Report 00 listed SM and P verdicts as "(run)" suggesting only LATCH was evaluated. CORRECTED: all three ran with full results in `results/eval_*_vs_e0_full/`. All three show the same structural pattern (candidate score << baseline score due to CAGR gap).

9. **"VTREND-SM ... Vol-targeted fractional ... 11.8%"** -- Exposure figure is correct but Report 00 implied SM uses "state machine" in its name. CORRECTED: SM's code has **NO hysteresis and NO state machine** despite its name. See Section 3.2 below. The code comment at `strategies/vtrend_sm/strategy.py:314` explicitly says "per-bar, no hysteresis -- faithful to source".

10. **"LATCH has 28 params"** -- Report 00 said "13 + 15 VDO". CORRECTED: 28 total fields in `LatchConfig`, but the 15 VDO params are inert at default (mode="none"). Effective tunable params at defaults = 13 core only.

### Assumptions that are UNVERIFIED_STATICALLY

11. **Engine equivalence** -- The two engines differ in fill-price computation, cost application, and rebalance thresholds. The exact magnitude of the difference on real data is UNVERIFIED_STATICALLY. Requires parity test.
12. **Indicator parity** -- Both integrated and standalone LATCH implementations appear to use identical indicator formulas, but bitwise equivalence is UNVERIFIED_STATICALLY.
13. **Standalone vtrend_variants.py vs integrated SM/P** -- Report 00 noted these exist. Whether they produce identical signals is UNVERIFIED_STATICALLY.

---

## 2. Strategy-to-Engine Mapping

| Strategy | Engine | Config Source | Entry Point |
|----------|--------|--------------|-------------|
| VTREND (E0) | `v10/core/engine.py` BacktestEngine | `configs/vtrend/vtrend_default.yaml` | `VTrendStrategy.on_bar()` |
| VTREND-SM | `v10/core/engine.py` BacktestEngine | `configs/vtrend_sm/vtrend_sm_default.yaml` | `VTrendSMStrategy.on_bar()` |
| VTREND-P | `v10/core/engine.py` BacktestEngine | `configs/vtrend_p/vtrend_p_default.yaml` | `VTrendPStrategy.on_bar()` |
| LATCH (integrated) | `v10/core/engine.py` BacktestEngine | `configs/latch/latch_default.yaml` | `LatchStrategy.on_bar()` |
| LATCH (standalone) | `Latch/research/Latch/backtest.py` execute_target_weights | `Latch/research/Latch/config.py` LatchParams() | `run_latch()` |
| SM (standalone) | `Latch/research/vtrend_variants.py` (own backtest loop) | inline VTrendStateMachineParams | `run_vtrend_state_machine()` |
| P (standalone) | `Latch/research/vtrend_variants.py` (own backtest loop) | inline VTrendPParams | `run_vtrend_p()` |

---

## 3. Per-Strategy Semantic Inventory

### 3.1 VTREND (E0) -- `strategies/vtrend/strategy.py`

**Signal Logic**
- Entry: `ema_fast > ema_slow AND vdo > vdo_threshold` (line 105)
- Exit: `price < peak_price - trail_mult * atr` (trail stop, line 115) OR `ema_fast < ema_slow` (trend reversal, line 120)
- State: binary `_in_position` flag. No ARMED state.
- Regime: instantaneous EMA crossover, no hysteresis.
- Peak tracking: `_peak_price = max(_peak_price, close)` updated each bar while long (line 111).
- **VDO is a HARD entry gate** -- required `vdo > 0.0` at default.

**Sizing**
- Binary: `target_exposure=1.0` on entry, `target_exposure=0.0` on exit.
- No fractional sizing, no vol-targeting, no rebalancing.
- Engine applies `_EXPO_THRESHOLD=0.005` (engine.py:28) but with binary 0/1 signals this is irrelevant.

**Execution**
- Signal at bar[i] close → fill at bar[i+1] open via v10 BacktestEngine.
- Fill price: `ask = open * (1 + spread/20000)`, `fill = ask * (1 + slip/10000)` (execution.py:36-38).
- Fee: `qty * fill_px * (fee_pct/100)` (execution.py:117).

**Default Params** (from config YAML)
- slow_period=120.0, trail_mult=3.0, vdo_threshold=0.0
- atr_period=14, vdo_fast=12, vdo_slow=28

**Required Data**: close, high, low, volume, taker_buy_base_vol (for VDO)

---

### 3.2 VTREND-SM -- `strategies/vtrend_sm/strategy.py`

**Signal Logic**
- Entry: `regime_ok AND close > hh_entry` (lines 315-327). Optional VDO filter (default OFF).
- Exit: `close < max(ll_exit, ema_slow - atr_mult * atr)` (floor break, line 339). Optional regime_break exit (default OFF, line 340).
- State: binary `_active` flag. **NO state machine despite name.** No ARMED state.
- **Regime: INSTANTANEOUS, NO HYSTERESIS** -- `regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)` (line 315). Comment says "per-bar, no hysteresis -- faithful to source".

**DOC-CODE MISMATCH**: The name "State Machine" and Report 00's description imply a state machine. Code truth: SM has a **simple binary flag** (`_active`), not a state machine. This is materially different from LATCH's 3-state hysteretic machine.

**Sizing**
- Vol-targeted: `weight = target_vol / max(rv, EPS)` clipped to [0, 1] (line 329).
- Rebalance: checks `delta >= min_rebalance_weight_delta - 1e-12` against `state.exposure` (lines 354-355).
- Sizing is recomputed EVERY bar while long and rebalance is sent if delta exceeds threshold.
- No vol_floor -- uses only EPS (1e-12) as minimum divisor.

**Execution**
- Same v10 BacktestEngine. Signal → target_exposure → engine computes buy/sell.
- Engine's `_EXPO_THRESHOLD=0.005` acts as additional minimum delta.

**Default Params** (from config YAML)
- slow_period=120, atr_mult=3.0, target_vol=0.15
- entry_n=auto(60), exit_n=auto(30), slope_lookback=6
- use_vdo_filter=False, exit_on_regime_break=False

**Required Data**: close, high, low (no volume needed at defaults)

---

### 3.3 VTREND-P -- `strategies/vtrend_p/strategy.py`

**Signal Logic**
- Entry: `close > ema_slow AND ema_slow > slope_ref AND close > hh_entry` (lines 262-266).
- Exit: `close < max(ll_exit, ema_slow - atr_mult * atr)` (floor break, line 278). NO regime break exit.
- State: binary `_active` flag. No state machine.
- **Regime: PRICE-DIRECT, NO HYSTERESIS** -- uses `close > ema_slow` instead of `ema_fast > ema_slow`. No EMA fast computed.

**Sizing** -- identical structure to SM: `target_vol / max(rv, EPS)`, clipped [0, 1], rebalance with threshold. No vol_floor.

**Default Params**
- slow_period=120, atr_mult=1.5, target_vol=0.12
- entry_n=auto(60), exit_n=auto(30), slope_lookback=6

**Key Difference from SM**: lower atr_mult (1.5 vs 3.0) = tighter exit floor, and price-based regime (close > ema_slow) instead of crossover (ema_fast > ema_slow).

**Required Data**: close, high, low

---

### 3.4 LATCH (integrated) -- `strategies/latch/strategy.py`

**Signal Logic**
- Entry: `regime_on (hysteretic) AND close > hh_entry` (lines 479-489).
- Exit: `close < adaptive_floor OR regime_flip_off` (lines 504-513). Regime flip-off ALWAYS triggers exit.
- State: **3-state machine** `_LatchState` (OFF=0, ARMED=1, LONG=2) (lines 47-50).
  - OFF → ARMED: regime ON, no breakout (line 489)
  - OFF → LONG: regime ON AND breakout (line 484)
  - ARMED → OFF: off_trigger fires (line 493)
  - ARMED → LONG: regime ON AND breakout (lines 494-500)
  - LONG → OFF: floor_break OR flip_off (lines 507-508)

**Regime: HYSTERETIC WITH MEMORY** (`_compute_hysteretic_regime`, lines 233-274):
- ON trigger: `fast > slow AND slow > slope_ref`
- OFF trigger: `fast < slow AND slow < slope_ref`
- If neither trigger fires: **hold previous state** (line 266-269)
- This is the fundamental difference from SM: regime state persists across bars.

**Sizing**
- Vol-targeted with floor: `weight = target_vol / max(rv, vol_floor, EPS)` (line 437-438).
- Clipped to [0, max_pos] (default max_pos=1.0) (line 439).
- VDO overlay applied AFTER base sizing if mode != "none" (lines 441-444). Default: mode="none".
- Rebalance: checks delta >= min_rebalance_weight_delta while LONG (lines 516-521).

**Execution** -- same v10 BacktestEngine.

**Default Params** (from config YAML)
- slow_period=120, fast_period=30, atr_mult=2.0, target_vol=0.12, vol_floor=0.08
- entry_n=60, exit_n=30, slope_lookback=6
- vdo_mode="none", max_pos=1.0, min_rebalance_weight_delta=0.05

**Required Data**: close, high, low (volume + taker_buy only if VDO mode enabled)

---

### 3.5 LATCH (standalone) -- `Latch/research/Latch/strategy.py`

**Signal Logic** -- functionally identical to integrated LATCH. Same hysteretic regime via `compute_hysteretic_regime()` in `state_machine.py`. Same 3-state machine. Same entry/exit logic.

**Sizing** -- identical formula: `target_vol / max(rv, vol_floor, EPS)`.

**Default Params** -- `LatchParams()` in `config.py`: slow=120, fast=30, atr_mult=2.0, target_vol=0.12, vol_floor=0.08. Identical to integrated defaults.

**Engine Differences** (vs v10):
1. Starting capital: **1.0** (normalized) vs 10000.
2. Fill price: **raw `open_price[i]`** with NO spread/slippage adjustment to price (backtest.py:286-305).
3. Cost: lump `cost_rate = (fee_bps + half_spread_bps + slippage_bps) / 10_000` on notional (backtest.py:263, config.py:22-23).
4. No engine-level rebalance threshold (engine accepts all weight deltas from strategy).
5. CAGR: bar-count based `(ending_equity^(1/years) - 1)` where `years = (len-1) / bars_per_year` (backtest.py:131-136).
6. MDD: fraction 0-1, not percent 0-100 (backtest.py:129).

---

## 4. Engine Semantics Comparison

Full matrix in `artifacts/engine_semantics_matrix.csv`. Critical differences:

### 4.1 Fill Price (MATERIAL DIFFERENCE)

**v10 engine** (`execution.py:35-43`):
```
BUY:  fill_px = mid * (1 + spread/20000) * (1 + slip/10000)
SELL: fill_px = mid * (1 - spread/20000) * (1 - slip/10000)
Fee:  qty * fill_px * (fee_pct/100)
```
Price impact is multiplicative. For harsh (spread=10, slip=5, fee=0.15%):
- BUY fill_px ≈ open * 1.001 (10 bps price impact)
- Fee ≈ 0.15% on inflated notional
- Effective per-side cost ≈ 25 bps

**Standalone engine** (`backtest.py:286-305`):
```
BUY:  units += buy_notional / open_price[i]
      fee = buy_notional * cost_rate
SELL: units -= sell_notional / open_price[i]
      fee = sell_notional * cost_rate
```
Fill at **raw open price**. Cost applied as flat rate on notional.
For default (fee=25bps, spread=0, slip=0): cost_rate = 0.0025 (25 bps).

**Impact**: At equivalent total RT cost (50 bps), the v10 engine gives slightly worse fill prices (multiplicative penalty on units received/sold) while standalone applies cost purely as cash drain. The difference is second-order (~0.01% per trade) but accumulates over hundreds of trades.

### 4.2 Engine Rebalance Threshold (MATERIAL DIFFERENCE)

**v10 engine** (`engine.py:28`): `_EXPO_THRESHOLD = 0.005` hardcoded. Any `target_exposure` within 0.5% of current exposure is silently ignored (engine.py:296, 303, 313).

**Standalone engine**: No engine-level threshold. Only strategy's `min_rebalance_weight_delta` (5%) applies (backtest.py:272-274).

**Impact**: For fractional-sizing strategies, v10's 0.5% floor is far below the strategy's 5% threshold, so this is likely non-binding. But if a strategy sends a 0.4% rebalance signal, v10 ignores it while standalone would execute it.

### 4.3 Starting Capital (COSMETIC DIFFERENCE)

v10: 10000 USD. Standalone: 1.0 (normalized). Affects absolute notional values but not percentage returns or Sharpe.

---

## 5. Existing Evaluation Pipeline Trace

### 5.1 Entry Point

`validate_strategy.py` → `validation/runner.py` → `validation/suites/backtest.py` BacktestSuite.

### 5.2 Scoring Formula

**File**: `v10/research/objective.py:45-93`

```
score = 2.5 * cagr_pct
      - 0.60 * max_drawdown_mid_pct
      + 8.0 * max(0, sharpe)
      + 5.0 * max(0, min(profit_factor, 3.0) - 1.0)
      + min(n_trades / 50, 1.0) * 5.0
```

If `n_trades < 10`: score = -1,000,000 (rejected).

### 5.3 Decision Rule

**File**: `validation/decision.py:278-307`

Hard gate: `harsh_score_delta >= -HARSH_SCORE_TOLERANCE` where `HARSH_SCORE_TOLERANCE = 0.2` (thresholds.py:21).

For LATCH vs E0: delta = 50.41 - 123.32 = **-72.91**. Required: >= -0.2. Result: **REJECT**.

### 5.4 Score Breakdown (LATCH vs E0, Harsh)

| Component | LATCH | E0 | Delta | % of total delta |
|-----------|------:|---:|------:|:----------------:|
| return_term (2.5×CAGR) | 32.05 | 130.10 | -98.05 | **134.4%** |
| mdd_penalty (-0.6×MDD) | -6.74 | -24.97 | +18.22 | -25.0% |
| sharpe_term (8×Sharpe) | 11.54 | 10.12 | +1.42 | -1.9% |
| profit_factor_term | 8.56 | 3.07 | +5.50 | -7.5% |
| trade_count_term | 5.00 | 5.00 | 0.00 | 0.0% |
| **TOTAL** | **50.41** | **123.32** | **-72.91** | |

**The return_term (2.5×CAGR) accounts for 134% of the total score delta.** LATCH's advantages in MDD, Sharpe, and profit_factor are overwhelmed by the CAGR gap caused by 5x lower exposure.

### 5.5 Does the Scoring Function Mechanically Favor High-Exposure Systems?

**YES.** The `return_term = 2.5 * cagr_pct` is linear in CAGR. CAGR scales approximately linearly with average exposure for trend strategies. A strategy with 5x exposure has ~5x CAGR, giving ~5x return_term, which dominates all other terms. The scoring function has no exposure-normalization step.

### 5.6 Result Files Producing Cited Numbers

All traced in `artifacts/existing_eval_metric_sources.csv`. Primary source:
- `results/eval_latch_vs_e0_full/results/full_backtest_summary.csv`
- `results/eval_latch_vs_e0_full/results/score_breakdown_full.csv`
- Run metadata: `results/eval_latch_vs_e0_full/run_meta.json`

---

## 6. Special Questions

### A. Engine Separation

**Q: Are v10/core/engine.py and Latch/backtest.py conceptually the same?**

**A: No. They are materially different.**

- v10 is **event-driven**: the engine iterates bars, calls strategy.on_bar(), receives Signal, converts to buy/sell via Portfolio. The engine owns execution.
- Standalone is **target-weight based**: the strategy produces a complete `target_weight_signal` array, then `execute_target_weights()` iterates bars and executes the pre-computed signals. The strategy pre-computes all decisions.

**Where could differences change metrics?**
1. **Fill price**: v10 applies spread+slip multiplicatively to fill price; standalone fills at raw open. For harsh costs, v10 gives ~10 bps worse fill per side. Over 192 trades (E0), this is ~19.2% cumulative price impact difference. For LATCH's 65 trades, ~6.5%.
2. **Rebalance threshold**: v10 has engine-level 0.5% floor; standalone has none. Likely non-binding given 5% strategy threshold.
3. **CAGR computation**: v10 uses calendar time; standalone uses bar-count. Small difference.
4. **Interaction between strategy and engine**: in v10, `state.exposure` (used for rebalance decisions) comes from the engine's portfolio at mid price. In standalone, `current_w` is computed from `units * open_price / equity_open`. These can diverge slightly because v10's `state.exposure` is computed at bar close, but the signal is applied at next bar open.

### B. LATCH Semantics

**Q: Does LATCH use dynamic vol targeting?**
**A: YES.** `target_vol / max(rv, vol_floor, EPS)` recomputed every bar while LONG (integrated: line 437-438, standalone: strategy.py:160-162).

**Q: Does it rebalance while in position?**
**A: YES.** Both integrated (lines 516-521) and standalone (via execute_target_weights backtest.py:271-274) check rebalance threshold each bar.

**Q: Hysteretic regime distinct from SM?**
**A: YES, fundamentally.** LATCH uses `_compute_hysteretic_regime` (lines 233-274) with explicit state memory: regime holds previous value when neither ON nor OFF trigger fires. SM uses instantaneous per-bar check (line 315): `regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)` -- recomputed independently each bar with no memory.

**Q: VDO overlay default?**
**A: Default OFF.** `vdo_mode="none"` in both integrated (LatchConfig line 73) and standalone (VDOOverlayParams line 38).

### C. VTREND / SM / P Semantics

**Q: Does E0 own both signal and sizing?**
**A: YES.** E0 emits `target_exposure=1.0` or `0.0`. No fractional sizing. The strategy owns the sizing decision (always 100% or 0%).

**Q: Are SM and P only signal variants?**
**A: NO. They also alter sizing/rebalancing semantics materially.** SM and P introduce:
- Vol-targeted fractional sizing (not binary)
- Continuous rebalancing while long
- `min_rebalance_weight_delta` threshold
- Different exit mechanics (no peak-tracking trail stop; use adaptive floor instead)

**Q: Hidden exposure control?**
**A: YES, in the engine.** `_EXPO_THRESHOLD = 0.005` in engine.py:28. This is invisible to the strategy but prevents tiny position changes.

### D. Existing Evaluation Pipeline

**Q: Which file computes the verdict?**
**A:** `validation/decision.py:119` (`evaluate_decision()`).

**Q: Exact scoring formula?**
**A:** `v10/research/objective.py:65-69`. See Section 5.2.

**Q: Does the rule favor high-exposure, high-CAGR systems?**
**A: YES, decisively.** The `return_term = 2.5 * cagr` is the dominant component. At 5x exposure difference, CAGR gap is ~40 pct-points, creating a return_term delta of ~100 score points. The tolerance is 0.2 score points. No risk-adjustment or exposure-normalization exists in the scoring formula.

**Q: Which files produced the cited numbers?**
**A:** See `artifacts/existing_eval_metric_sources.csv`. All numbers traced to `results/eval_latch_vs_e0_full/results/full_backtest_summary.csv` which is written by `validation/suites/backtest.py:143`.

### E. Confounders

Full registry in `artifacts/confounder_registry.csv` (20 entries). Top 5 by severity:

| ID | Confounder | Severity |
|----|-----------|----------|
| C01 | Binary vs fractional sizing | CRITICAL |
| C02 | 5x exposure mismatch | CRITICAL |
| C13 | Scoring formula's 2.5×CAGR bias | CRITICAL |
| C07 | Regime hysteresis vs instantaneous | HIGH |
| C08 | Regime exit default (on vs off) | HIGH |

---

## 7. Key Discoveries Not in Report 00

### 7.1 SM Has No Hysteresis (Name is Misleading)

`strategies/vtrend_sm/strategy.py:314-315`:
```python
# Regime check (per-bar, no hysteresis — faithful to source)
regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)
```
Despite being called "State Machine", SM checks regime independently each bar. LATCH uses true hysteretic regime with state memory. This is a **genuine algorithmic difference**, not just a naming convention.

### 7.2 E0 Uses Peak-Tracking Trail; Others Use Adaptive Floor

E0 (`vtrend/strategy.py:111-115`):
```python
self._peak_price = max(self._peak_price, price)
trail_stop = self._peak_price - self._c.trail_mult * atr_val
```
The trail stop is anchored to the **highest close since entry**. This creates a ratcheting effect.

SM/P/LATCH use an **adaptive floor**:
```python
exit_floor = max(ll_exit, ema_slow - atr_mult * atr)
```
This floor is anchored to the **rolling low of recent bars** and the **current EMA level**. It can move DOWN as well as up.

These are fundamentally different exit dynamics. The peak-tracking trail only ratchets up; the adaptive floor follows the market.

### 7.3 VDO Role Differs Across Strategies

- **E0**: VDO is a **hard entry gate** (line 105: `vdo_val > self._c.vdo_threshold`). Required for every entry.
- **SM**: VDO is **optional hard filter** (default OFF, line 321: `use_vdo_filter`).
- **LATCH**: VDO is **optional soft overlay** (default OFF, line 441: `vdo_mode != "none"`). When enabled, it multiplies base weight (never vetoes).

At defaults, E0 uses VDO for entry while SM/P/LATCH ignore it entirely.

### 7.4 Default atr_mult Creates Different Risk Profiles

| Strategy | atr_mult | Effect |
|----------|:--------:|--------|
| E0 | 3.0 | Wider trail → later exits → higher MDD, higher CAGR |
| SM | 3.0 | Same as E0 but applied to adaptive floor |
| P | 1.5 | Tight floor → earlier exits → lower MDD, lower CAGR |
| LATCH | 2.0 | Middle ground |

### 7.5 Vol Floor Unique to LATCH

LATCH uses `vol_floor=0.08` in sizing: `target_vol / max(rv, vol_floor, EPS)` (line 437-438).
SM and P use only `max(rv, EPS)` (line 329 SM, line 268 P).

When realized vol drops below 8%, LATCH caps position size at `0.12/0.08 = 1.5x` (then clipped to max_pos=1.0). SM and P would compute `0.15/0.01 = 15.0` (clipped to 1.0) -- reaching max faster in low-vol regimes.

### 7.6 Standalone CostModel Default Differs from Harsh

Standalone `CostModel()` defaults: fee_bps=25.0, half_spread=0.0, slippage=0.0 → cost_rate=0.0025 (25 bps one-way, 50 bps RT).

V10 harsh: spread=10 bps, slip=5 bps, fee=0.15% → RT ~50 bps.

The RT total is similar (50 bps) but the composition differs. Standalone has no price impact (fills at raw open), while v10 harsh has ~10 bps price impact per side. This means v10 harsh gives fewer units per dollar spent and fewer dollars per unit sold.

---

## 8. Open Uncertainties

| # | Question | Status | How to Resolve |
|---|----------|--------|----------------|
| U1 | Do integrated and standalone LATCH produce identical signal sequences on the same data? | UNVERIFIED_STATICALLY | Run both on same H4 data, compare target_weight arrays |
| U2 | What is the equity curve divergence between v10 engine and standalone engine for identical signals? | UNVERIFIED_STATICALLY | Feed identical signal array to both engines, compare equity |
| U3 | Does v10's multiplicative fill-price differ materially from standalone's flat cost on real data? | UNVERIFIED_STATICALLY | Compare fill prices and cumulative cost for same trades |
| U4 | Is SM's instantaneous regime check practically different from LATCH's hysteresis on BTC H4 data? | UNVERIFIED_STATICALLY | Compare regime_on arrays side-by-side |
| U5 | Would LATCH outperform E0 under identical binary (100%) sizing? | UNVERIFIED_STATICALLY | Requires harness with factorial sizing |
| U6 | Is the standalone vtrend_variants.py SM identical to integrated SM? | UNVERIFIED_STATICALLY | Compare signal arrays |

---

## 9. Recommended Next Step

**Step 2: Parity and Signal Extraction.**

Before any comparative analysis, establish:
1. Signal parity: integrated LATCH vs standalone LATCH (same data, same params).
2. Engine parity: same signal stream through both engines.
3. Signal concordance: extract binary in/out signals from all strategies on same data.

This must precede any sizing decomposition or fair comparison, because without confirmed parity, we cannot distinguish signal differences from engine differences.

---

## 10. Artifacts Produced

| File | Contents |
|------|----------|
| `artifacts/strategy_manifest.json` | Structured per-strategy metadata |
| `artifacts/engine_semantics_matrix.csv` | Dimension-by-dimension engine comparison |
| `artifacts/confounder_registry.csv` | 20 confounders with severity and neutralization |
| `artifacts/file_dependency_map.csv` | All files and their dependencies |
| `artifacts/existing_eval_metric_sources.csv` | Every cited metric traced to source file and computation |

---

*End of Report 01. No harness code written. No backtests run. No performance conclusions drawn. All claims traced to code paths.*
