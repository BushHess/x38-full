# Report 34c: VTREND-SM Canonical Design Contract

> **Phase**: 4 — Algorithm intent validation + canonical design contract
> **Date**: 2026-03-04
> **Status**: Complete — awaiting review before Prompt 5
> **Prerequisite reports**: 34 (survey), 34b (pre-integration audit)
>
> **Note (2026-03-14)**: This contract describes VTREND-SM design. The VDO
> OHLC fallback mentioned here has since been removed from ALL strategies
> (E0, E5, E5_ema21D1, V8Apex, V11Hybrid, V12, V13, X7). VDO now raises
> RuntimeError without real taker data across the entire codebase.

---

## 1. Scope

This report extracts the **algorithmic intent** of VTREND-SM from multiple evidence sources, identifies where sources contradict each other, separates core algorithm identity from source implementation artifacts, and produces a **canonical design contract** — a specification precise enough for Prompt 5 to implement without guesswork.

**Critical framing**: The source code (`Latch/research/vtrend_variants.py`) is an evidence source, not an infallible oracle. Where the source's behavior appears accidental, under-tested, or conflicting with its own specification, this report names it and makes a deliberate decision.

**Constraints of this prompt**:
- No source code changes
- No strategy registration
- No test creation
- Only file created: this report

---

## 2. Evidence Hierarchy

Sources ranked by trustworthiness for determining **algorithmic intent**:

| Rank | Source | Justification | Weakness |
|------|--------|---------------|----------|
| 1 | **Source spec** (`VTREND_SPEC_AND_GUIDE.md`) | Declares the author's INTENDED behavior. Written as a design document, not generated from code. | May lag behind code changes. Sparse on edge cases. |
| 2 | **Source tests** (`test_vtrend_variants.py`) | Tests encode what the author VERIFIES. A tested behavior is intentional. An untested edge case is ambiguous. | Only 6 tests for VTREND-SM. Many edge cases untested. |
| 3 | **Source code** (`vtrend_variants.py`) | Defines ACTUAL behavior, including edge cases. | May contain accidental choices, separation-of-concern artifacts, or behaviors the author didn't intend. |
| 4 | **Framework constraints** (btc-spot-dev engine, types, base class) | Hard architectural constraints. Cannot be violated without engine changes. | May force adaptations that change behavior semantics. |
| 5 | **Audit report** (34b) | Systematic analysis, but performed by automated assistant. | May have reasoning errors. Not primary evidence. |
| 6 | **Implementation draft** (`strategies/vtrend_sm/strategy.py`) | Premature artifact. Created before survey phase. | Untrusted. Not evidence of correct design. |

**Ruling principle**: When sources conflict, spec and tests reveal **intent**; code reveals **accidental behavior**; framework reveals **hard constraints**.

---

## 3. Contradiction Matrix

### 3.1 Cross-Source Contradictions

| # | Issue | Source Code | Source Tests | Source Spec | Framework | Preliminary Assessment |
|---|-------|-------------|-------------|-------------|-----------|----------------------|
| C1 | **BARS_PER_YEAR_4H value** | `365.0 * 6.0 = 2190.0` (`vtrend_variants.py:43`) | Not tested directly | Not specified | `metrics.py:19` uses `(24/4)*365 = 2190.0`. MEMORY.md says `6.0 * 365.25 = 2191.5`. | **Internal btc-spot-dev contradiction.** metrics.py (2190.0) contradicts MEMORY.md (2191.5). Source uses 2190.0. |
| C2 | **Entry when weight=0 after clip** | Enters LONG regardless, weight=0 recorded (`vtrend_variants.py:689-691, 700-702`). Execution engine sells to flat via crossing_zero (`vtrend_variants.py:510`). | `test_small_entry_weight_still_executes_buy` — uses `target_vol=1e-4` with default `min_weight=0.0`. Weight > 0, so test does NOT cover weight=0 case. | Spec §3.2: entry conditions listed (regime, breakout, VDO). Sizing listed separately: "weight = min(1.0, target_vol / realized_vol) when active." No mention of weight=0 entry. | No constraint. Engine accepts any target_exposure in [0, 1]. | **Untested edge case.** Spec separates entry from sizing, suggesting source's behavior (enter regardless) is intentional structure. But weight=0 entry produces incoherent state: LONG with no position. Author likely assumed weight > 0 with default params. |
| C3 | **Rebalance gating ownership** | Strategy emits `target_weight_signal[i]` every active bar. Execution engine `_execute_target_weights()` gates rebalance at open price (`vtrend_variants.py:504-511`). | `test_rebalance_threshold_reduces_trade_events` — tests that higher threshold = fewer trades. Does NOT test WHERE gating occurs. | Spec §5: "trade only if weight change >= min_rebalance_weight_delta". Does NOT specify whether strategy or engine gates. | Engine has `_EXPO_THRESHOLD = 0.005` (`engine.py:28`). No configurable rebalance threshold. Strategy `on_bar()` returns Signal or None. | **Framework forces adaptation.** btc-spot-dev engine has no mechanism for strategy-specific rebalance threshold. Strategy must gate internally. |
| C4 | **Rebalance comparison basis** | Open-price actual weight: `current_w = _position_weight(units, open_price[i], equity_open)` (`vtrend_variants.py:507`). | Not tested (comparison basis is internal implementation). | Not specified. | `state.exposure` is computed at bar close: `Portfolio.exposure(bar.close)` (`engine.py:219`). Strategy only sees close-price exposure. | **Framework forces adaptation.** Strategy cannot access next-bar open price. Must use close-price exposure as proxy. |
| C5 | **VDO when taker data missing** | `validate_market_frame(require_vdo_columns=True)` raises ValueError (`vtrend_variants.py:241-244`). No OHLC proxy. | `test_optional_vdo_filter_requires_columns` — explicitly tests that missing VDO columns raises ValueError. | Spec §6.1: "optional VDO columns (when enabled): volume, taker_buy_base_volume". | `Bar` type always has `taker_buy_base_vol: float`. Data always present. Existing `_vdo()` in VTREND E0 has OHLC proxy fallback. | **Test confirms source intent: error on missing columns.** But btc-spot-dev Bar always provides data. Proxy fallback only fires if ALL taker_buy values are 0. |
| C6 | **Config frozen attribute** | `@dataclass(frozen=True)` (`vtrend_variants.py:77`). | No test on immutability. | Not specified. | `strategy_factory.py:46` uses `setattr(cfg, k, v)` for config overrides. Requires mutable dataclass. VTREND E0 uses `@dataclass` (mutable). | **Framework forces adaptation.** frozen=True is incompatible with config override pattern. |
| C7 | **Validation timing** | `slope_lookback` validated in `resolved()` (`vtrend_variants.py:110`). Construction succeeds with invalid params; `resolved()` raises. | No test on construction with invalid slope_lookback. | Not specified. | No framework standard. VTREND E0 has no validation at all. | **Source artifact.** Validation in resolved() is not a design choice; it's where the author happened to put the check. |
| C8 | **VDO NaN handling in entry check** | `bool(vdo_loop[i] > threshold)` — NaN comparison returns False, entry blocked. Bar processing continues; exit/rebalance/state all still run. (`vtrend_variants.py:684`) | Not tested. | Not specified. | No constraint. | **Source artifact.** `bool(NaN > x) = False` is a Python behavior, not an explicit NaN policy. |
| C9 | **EMA span validation** | `if span <= 0: raise ValueError` (`vtrend_variants.py:272`). | Not tested directly. | Not specified. | No constraint. Auto-derivation guarantees `fast_period >= 5`. | **Defensive code for unreachable case** (when called through config). |

### 3.2 Internal btc-spot-dev Contradiction

| Issue | metrics.py | MEMORY.md |
|-------|------------|-----------|
| BARS_PER_YEAR_4H | `(24.0/4.0) * 365.0 = 2190.0` (line 19) | `6.0 * 365.25 = 2191.5` ("Annualization: sqrt(6.0 * 365.25) for H4 bars (NOT sqrt(2190.0))") |

MEMORY.md explicitly says "NOT sqrt(2190.0)". But `metrics.py` uses exactly 2190.0 for Sharpe/Sortino computation. This is an unresolved internal inconsistency. The MEMORY.md convention likely refers to research scripts, not the v10 engine core.

---

## 4. Core Algorithm Identity

### 4.1 Component Classification

| # | Component | Classification | Evidence |
|---|-----------|----------------|----------|
| A1 | **Binary state machine** (FLAT / LONG, no intermediate states) | `CORE_MUST_PRESERVE` | Spec §3.2: "Entry when flat", "Exit when long". Source: `active = False/True` (`vtrend_variants.py:674`). Tests: entry/exit tests assume binary state. |
| A2 | **Regime qualification**: `ema_fast > ema_slow AND ema_slow > ema_slow.shift(slope_lookback)` | `CORE_MUST_PRESERVE` | Spec §3.2: "Regime: ema_fast > ema_slow and ema_slow > ema_slow.shift(slope_lookback)". Code: `vtrend_variants.py:680`. Test: `test_slope_lookback_affects_signals` verifies slope component. |
| A3 | **Breakout entry**: `close > rolling_high(high.shift(1), entry_n)` | `CORE_MUST_PRESERVE` | Spec §3.2: "close > rolling_high(high.shift(1), entry_n)". Code: `vtrend_variants.py:681`. Test: `test_entry_signal_executes_at_next_open` implicitly requires breakout. |
| A4 | **Adaptive floor exit**: `close < max(rolling_low(low.shift(1), exit_n), ema_slow - atr_mult * ATR)` | `CORE_MUST_PRESERVE` | Spec §3.2: "close < max(rolling_low(low.shift(1), exit_n), ema_slow - atr_mult * ATR)". Code: `vtrend_variants.py:686, 693`. This is the distinguishing feature vs VTREND E0's trailing-stop. |
| A5 | **Optional VDO filter**: `vdo > threshold` when `use_vdo_filter=True` (default: False) | `CORE_MUST_PRESERVE` | Spec §3.3: "use_vdo_filter=False by default (VDO is optional, not mandatory)". Code: `vtrend_variants.py:682-684`. Test: `test_optional_vdo_filter_requires_columns`. |
| A6 | **Optional regime-break exit**: `exit_on_regime_break=True` forces flat on regime loss | `CORE_MUST_PRESERVE` | Spec §3.3: "exit_on_regime_break=False matches the pure adaptive-floor exit specification". Code: `vtrend_variants.py:694`. |
| A7 | **Vol-targeted fractional sizing**: `weight = clip(target_vol / max(rv, EPS), min_weight)` | `CORE_MUST_PRESERVE` | Spec §5: "target weight scales with target_vol / realized_vol, then clipped to [0, 1]". Code: `vtrend_variants.py:701`. Test: `test_target_weights_are_bounded`. |
| A8 | **Signal timing**: signal at bar close → execute at next-bar open | `CORE_MUST_PRESERVE` | Spec §5: "signal formed on close of bar i, order executed on open of bar i+1". Code: `vtrend_variants.py:503-505`. Test: `test_entry_signal_executes_at_next_open` (BUY at bar_index = entry + 1). |
| A9 | **Rebalance threshold semantics**: trade only when weight change exceeds `min_rebalance_weight_delta` | `CORE_MUST_PRESERVE` | Spec §5: "trade only if weight change >= min_rebalance_weight_delta". Code: `vtrend_variants.py:508-511`. Test: `test_rebalance_threshold_reduces_trade_events`. |
| A10 | **Warmup**: no signals before all indicators converge to finite values | `CORE_MUST_PRESERVE` | Code: `_warmup_start()` (`vtrend_variants.py:424-429`), warmup loop (`vtrend_variants.py:676-678`). Not explicitly in spec but fundamental to correctness. |
| A11 | **Indicator set**: EMA, ATR (Wilder), rolling_high_shifted, rolling_low_shifted, realized_vol, VDO | `CORE_MUST_PRESERVE` | All indicators named in spec §6.2 and implemented in code. Mathematical formulas are the algorithm's analytical core. |
| A12 | **Auto-derived parameters**: fast_period, entry_n, exit_n, vol_lookback from slow_period | `CORE_MUST_PRESERVE` | Code: `resolved()` (`vtrend_variants.py:109-122`). Spec: §3.1 references VTrendStateMachineParams docstring. Tests: various tests explicitly set these (implying None-auto behavior is default). |
| A13 | **_clip_weight gate**: NaN→0, clamp [0,1], below min_weight→0 | `CORE_MUST_PRESERVE` | Code: `_clip_weight()` (`vtrend_variants.py:415-421`). This defines the vol-target to position-size mapping. |
| A14 | **Crossing-zero always trades**: entry/exit always execute regardless of rebalance threshold | `CORE_MUST_PRESERVE` | Code: `crossing_zero = (target_w <= 1e-12) != (current_w <= 1e-12); should_trade = ... or crossing_zero` (`vtrend_variants.py:510-511`). Test: `test_small_entry_weight_still_executes_buy` shows small entry weight BUY executes. |
| A15 | **frozen dataclass** | `LIKELY_SOURCE_ARTIFACT` | No test verifies immutability. Not in spec. Python safety measure, not algorithm semantics. btc-spot-dev framework requires mutable configs. |
| A16 | **Validation in resolved()** | `LIKELY_SOURCE_ARTIFACT` | No test on validation timing. Not in spec. Implementation convenience, not design intent. |
| A17 | **EMA span <= 0 validation** | `LIKELY_SOURCE_ARTIFACT` | Defensive code for unreachable case (auto-derivation guarantees span >= 5). |
| A18 | **validate_market_frame** | `LIKELY_SOURCE_ARTIFACT` | Data validation is a source-module concern. btc-spot-dev DataFeed handles OHLCV validation at load time. |
| A19 | **Rebalance gating in execution engine** | `FRAMEWORK_ADAPTATION_ALLOWED` | The SEMANTICS (threshold gating) are core. The LOCATION (engine vs strategy) is architectural. btc-spot-dev engine has no configurable threshold mechanism, forcing strategy-side gating. |
| A20 | **Rebalance comparison at open price** | `FRAMEWORK_ADAPTATION_ALLOWED` | Source compares at open because its engine executes at open. btc-spot-dev strategy only sees close-price exposure. The difference is second-order for H4 bars (close-to-open typically < 1-2%, threshold = 5%). |
| A21 | **VDO OHLC proxy fallback** | `FRAMEWORK_ADAPTATION_ALLOWED` | Source has no fallback (errors on missing columns). btc-spot-dev Bar always provides `taker_buy_base_vol`; proxy only fires if ALL values are 0.0. This is a safety net, not a semantic change. |
| A22 | **Entry with weight=0 creates LONG-with-no-position** | `REQUIRES_EXPERIMENT` — downgraded to `FRAMEWORK_ADAPTATION_ALLOWED` after analysis below | See §5 decision D2 for full analysis. |

### 4.2 What Makes VTREND-SM "VTREND-SM"

The algorithm's identity is defined by the conjunction of:

1. **Regime + breakout + optional VDO** entry gate (distinguishes from VTREND E0's simple EMA crossover + mandatory VDO)
2. **Adaptive floor exit** = max(structural support, EMA-based floor) (distinguishes from VTREND E0's trailing-stop-from-peak)
3. **Vol-targeted fractional sizing** (distinguishes from VTREND E0's binary 0/1)
4. **Binary state machine** with per-bar regime evaluation (no hysteresis, no intermediate states)

Any implementation that preserves these four properties IS VTREND-SM. Everything else is negotiable.

---

## 5. Decision Table for Disputed Behaviors

### D1: BARS_PER_YEAR_4H / Annualization Constant

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `365.0 * 6.0 = 2190.0` (`vtrend_variants.py:43`). Used in `annualized_realized_vol()` (`vtrend_variants.py:305, 644`). |
| **Evidence from test/spec** | Not tested directly. Spec does not specify value. |
| **Framework implications** | `metrics.py:19`: `PERIODS_PER_YEAR_4H = (24/4) * 365 = 2190.0`. MEMORY.md: `6.0 * 365.25 = 2191.5`. Internal contradiction. |
| **Assessment** | `365.0 * 6.0 = 2190` is the actual number of 4H bars in a 365-day year. `6.0 * 365.25 = 2191.5` accounts for leap years but is inconsistent with `metrics.py`. Both are defensible; neither is "correct" (the true value fluctuates yearly). |
| **Canonical decision** | **KEEP** source value: `2190.0` |
| **Canonical behavior** | `BARS_PER_YEAR_4H = 365.0 * 6.0` used in `_realized_vol()`. |
| **Rationale** | (1) Matches source exactly. (2) Matches btc-spot-dev `metrics.py`. (3) Vol-targeting and Sharpe use the SAME annualization base, ensuring internal consistency. (4) The 0.034% sizing difference from 2191.5 is within numerical noise. |
| **Risk if wrong** | Negligible. 0.034% position-size difference. No impact on signal generation or state transitions. |

### D2: Entry When Conditions Met But Weight After Clip = 0.0

| Aspect | Detail |
|--------|--------|
| **Source behavior** | Enter LONG regardless: `active = True; entry_signal[i] = True` (`vtrend_variants.py:689-691`). Weight computed separately: `target_weight_signal[i] = _clip_weight(...)` which may be 0.0 (`vtrend_variants.py:700-701`). Execution engine then sees target=0 with current=0 → `crossing_zero = False` → `should_trade = False` → no fill. State is LONG with no position. Next bar: if weight recovers, execution engine sees target>0 with current=0 → `crossing_zero = True` → BUY. |
| **Evidence from test/spec** | Test `test_small_entry_weight_still_executes_buy`: target_vol=1e-4, min_weight=0.0 (default). Weight ≈ 0.0002 > 0, test passes. Test does NOT cover weight=0 after clip (only reachable with non-default `min_weight > 0`). Spec separates entry conditions from sizing: "Entry when FLAT: regime_ok and breakout_ok and VDO" then "Sizing: weight = min(1.0, target_vol/rv) when active." |
| **Framework implications** | No constraint. Engine accepts `target_exposure=0.0` (triggers sell-to-flat if holding). |
| **Assessment** | The spec's separation of entry from sizing suggests the source behavior (enter regardless) is **structurally intentional**. However, the specific consequence (LONG with no position, no fill, waiting for vol to normalize) is **untested** and **likely unconsidered** by the author. With default `min_weight=0.0`, the edge case is unreachable — `_clip_weight(positive, 0.0)` always returns positive. The test only covers small-but-positive weights. |
| **Canonical decision** | **ADAPT** — require `weight > 0.0` before entering LONG |
| **Canonical behavior** | When FLAT and all conditions met (regime_ok AND breakout_ok AND vdo_ok): compute weight via `_clip_weight()`. If weight > 0.0: enter LONG, emit `Signal(target_exposure=weight)`. If weight = 0.0: stay FLAT, emit nothing. |
| **Rationale** | (1) With default `min_weight=0.0`, behavior is IDENTICAL to source (weight always > 0). (2) Avoids incoherent state (LONG with no position, exposed to false exit signals). (3) If user sets `min_weight > 0`, they explicitly request "no positions below X%". Entering LONG with 0% contradicts this intent. (4) Entry means "take a position." Weight=0 means "don't take a position." These are contradictory. |
| **Risk if wrong** | With non-default `min_weight > 0`: if vol temporarily spikes during breakout, we miss the entry. Later, vol normalizes but breakout condition may no longer hold → missed trade. Mitigation: `min_weight` is a power-user parameter. Users who set it accept this tradeoff. Source behavior (enter at 0, wait for vol) is also defensible — if this proves suboptimal, it can be changed later without affecting default-param behavior. |

### D3: Rebalance Gating Ownership (Strategy vs Engine)

| Aspect | Detail |
|--------|--------|
| **Source behavior** | Strategy sets `target_weight_signal[i]` on EVERY active bar (`vtrend_variants.py:700-702`). Execution engine `_execute_target_weights()` gates rebalance: `delta_w >= threshold or crossing_zero` (`vtrend_variants.py:508-511`). |
| **Evidence from test/spec** | Test `test_rebalance_threshold_reduces_trade_events` verifies EFFECT (fewer trades with higher threshold) but not LOCATION (who does the gating). Spec §5: "trade only if weight change >= min_rebalance_weight_delta" — no location specified. |
| **Framework implications** | btc-spot-dev engine has `_EXPO_THRESHOLD = 0.005` (0.5%) (`engine.py:28`). No configurable per-strategy threshold. Engine does not support "strategy emits every bar, engine gates at 5%." To match source, would need engine modification (out of scope). |
| **Assessment** | The rebalance SEMANTICS (threshold gating) are algorithm core. The LOCATION is an implementation concern forced by framework. |
| **Canonical decision** | **ADAPT** — strategy gates rebalance internally |
| **Canonical behavior** | Strategy computes `new_weight` on every active bar. If `abs(new_weight - state.exposure) >= min_rebalance_weight_delta - 1e-12`: emit `Signal(target_exposure=new_weight, reason="vtrend_sm_rebalance")`. Otherwise: emit nothing. Entry/exit always emit (crossing zero handled by separate code paths). |
| **Rationale** | (1) Framework has no configurable threshold. (2) Strategy-side gating is the only option without engine modification. (3) Existing btc-spot-dev engine `_EXPO_THRESHOLD=0.005` is a secondary guard that never blocks signals passing the strategy's 5% gate. (4) Rebalance semantics (threshold, crossing-zero) are preserved. |
| **Risk if wrong** | Strategy-side gating means some signals are never emitted, reducing engine's visibility. This is benign — engine has no use for suppressed signals. The real risk is D4 below (comparison basis). |

### D4: Rebalance Comparison Basis (Close-Price vs Open-Price)

| Aspect | Detail |
|--------|--------|
| **Source behavior** | At bar `i+1` open: `current_w = _position_weight(units, open_price[i+1], equity_open)`. Compare `target_w` (from bar `i` close) vs `current_w` at open price. (`vtrend_variants.py:506-508`) |
| **Evidence from test/spec** | Not tested. Spec says "trade only if weight change >= threshold" — does not specify reference price. |
| **Framework implications** | Strategy `on_bar()` receives `state.exposure` computed at bar CLOSE: `Portfolio.exposure(bar.close)` (`engine.py:219`). Strategy has no access to next-bar open price. |
| **Assessment** | Source uses open-price because its execution engine operates at open. Strategy cannot replicate this — it doesn't know the next bar's open. Close-price exposure is the best available proxy. For H4 bars, typical close-to-open price change is small (< 1-2%). The 5% default threshold absorbs this difference. |
| **Canonical decision** | **ADAPT** — use close-price exposure as comparison basis |
| **Canonical behavior** | `delta = abs(new_weight - state.exposure)` where `state.exposure` is at bar close. `if delta >= min_rebalance_weight_delta - 1e-12`: emit rebalance signal. |
| **Rationale** | (1) Strategy cannot access next-bar open price. (2) Close-to-open difference for H4 bars typically < 1-2%, well below 5% threshold. (3) Edge cases: if close-to-open move is exceptionally large (e.g., 3%+), a rebalance might be emitted/suppressed differently vs source. This is a tail event on H4 data. |
| **Risk if wrong** | Occasional extra or missed rebalance trade near the threshold boundary. Empirically quantifiable in cross-validation (Prompt 5 Phase 4). Expected impact: < 1-2 extra/missed trades per year. |

### D5: VDO Behavior When Taker Data Missing

| Aspect | Detail |
|--------|--------|
| **Source behavior** | When `use_vdo_filter=True`: `validate_market_frame(require_vdo_columns=True)` raises ValueError if `volume` or `taker_buy_base_volume` columns missing (`vtrend_variants.py:241-244, 620-621`). No OHLC proxy. |
| **Evidence from test/spec** | Test `test_optional_vdo_filter_requires_columns` explicitly verifies ValueError on missing columns. This is TESTED and INTENTIONAL. |
| **Framework implications** | btc-spot-dev `Bar` always has `taker_buy_base_vol: float` (`types.py:37`). Data is always present. Existing `_vdo()` in VTREND E0 (`strategies/vtrend/strategy.py:159-177`) has OHLC proxy fallback for zero taker data. This is a btc-spot-dev convention. |
| **Assessment** | Source's "error on missing columns" is tested and intentional. But the scenario "missing columns" cannot occur in btc-spot-dev (Bar always has the field). The actual question is: what if `taker_buy_base_vol` is 0 for all bars? Source: irrelevant (would have raised on missing column). btc-spot-dev: OHLC proxy fires. |
| **Canonical decision** | **ADAPT** — keep OHLC proxy fallback per btc-spot-dev convention |
| **Canonical behavior** | `_vdo()` checks `np.any(taker_buy > 0)`. If True: use taker-based VDR. If False: use OHLC proxy `(close - low) / (high - low) * 2 - 1`. VDO is off by default (`use_vdo_filter=False`), so this only matters when explicitly enabled. |
| **Rationale** | (1) btc-spot-dev Bar always has taker data. "Missing columns" is impossible. (2) OHLC proxy handles the edge case of zero taker values (possible in synthetic data or data gaps). (3) Follows existing btc-spot-dev convention from VTREND E0. (4) VDO is off by default. |
| **Risk if wrong** | When `use_vdo_filter=True` with zero taker data: OHLC proxy produces different VDO values than taker-based VDO. This is a known limitation of the proxy. User should verify data quality when enabling VDO. |

### D6: VDO NaN Handling During Entry Check

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `bool(vdo_loop[i] > threshold)` → NaN comparison returns False → entry blocked. Bar processing continues normally (state recording, exit checks, rebalance all still run). (`vtrend_variants.py:684`) |
| **Evidence from test/spec** | Not tested. Not specified. |
| **Framework implications** | No constraint. |
| **Assessment** | Source's NaN handling is a Python side effect (`bool(NaN > x) == False`), not an explicit NaN policy. The author likely didn't consider VDO=NaN during post-warmup bars (warmup ensures all indicators finite). VDO NaN post-warmup would indicate data corruption. |
| **Canonical decision** | **ADAPT** — explicit NaN check, return None |
| **Canonical behavior** | When `use_vdo_filter=True` and `vdo_val` is not finite: `return None` (skip bar entirely). |
| **Rationale** | (1) Explicit NaN handling is clearer than relying on Python comparison semantics. (2) VDO NaN post-warmup indicates data corruption; skipping the bar is safer than partially processing it. (3) In FLAT state, both behaviors block entry. In LONG state (unreachable in this code path since VDO check is inside FLAT branch), no difference. |
| **Risk if wrong** | None. VDO NaN post-warmup is pathological. Both behaviors block entry. |

### D7: min_weight Semantics

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `_clip_weight(weight, min_weight)`: if `weight < min_weight` → return 0.0. Applied both at entry sizing and on every active bar. (`vtrend_variants.py:415-421, 701`) |
| **Evidence from test/spec** | Not directly tested for min_weight > 0 edge case. Spec §5: "target weight scales with target_vol / realized_vol, then clipped to [0, 1]". Does not mention min_weight explicitly. |
| **Framework implications** | No constraint. |
| **Assessment** | `_clip_weight` is a pure function with clear semantics. Its behavior is well-defined and unambiguous. |
| **Canonical decision** | **KEEP** — preserve _clip_weight exactly |
| **Canonical behavior** | `_clip_weight(weight, min_weight)`: if not finite → 0.0; clamp to [0, 1]; if below min_weight → 0.0. Character-identical to source. |
| **Rationale** | No reason to change. Function is simple, correct, and well-defined. |
| **Risk if wrong** | N/A — keeping source behavior. |

### D8: Config Mutability / Frozen

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `@dataclass(frozen=True)` (`vtrend_variants.py:77`). |
| **Evidence from test/spec** | No test on immutability. Not in spec. |
| **Framework implications** | `strategy_factory.py:43-46` uses `setattr(cfg, k, v)`. Requires mutable. VTREND E0 uses `@dataclass` (mutable, `strategies/vtrend/strategy.py:29`). |
| **Assessment** | frozen=True is a Python safety measure, not algorithm semantics. Framework requires mutable. |
| **Canonical decision** | **ADAPT** — use mutable `@dataclass` |
| **Canonical behavior** | `@dataclass` without frozen. |
| **Rationale** | Framework compatibility. No behavioral impact. All existing btc-spot-dev strategies use mutable @dataclass. |
| **Risk if wrong** | Accidental mutation during research. Mitigated by convention (strategy creates `resolved()` dict at init time). |

### D9: Validation Timing

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `slope_lookback <= 0` validated inside `resolved()` (`vtrend_variants.py:110-111`). `VTrendStateMachineParams(slope_lookback=0)` succeeds; `params.resolved()` raises. |
| **Evidence from test/spec** | Not tested. Not in spec. |
| **Framework implications** | No standard. VTREND E0 has no validation. |
| **Assessment** | Source's timing is an artifact of where the check was placed. __post_init__ is more Pythonic (fail-fast). |
| **Canonical decision** | **ADAPT** — validate in `__post_init__` |
| **Canonical behavior** | `VTrendSMConfig.__post_init__()` raises ValueError for `slope_lookback <= 0`. |
| **Rationale** | Fail-fast is better. Prevents invalid objects from existing. |
| **Risk if wrong** | None. Same validation, earlier timing. |

### D10: Warmup Semantics

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `_warmup_start()`: vectorized scan for first index where ALL indicator arrays are finite (`vtrend_variants.py:424-429`). During warmup: `signal_state[i] = active; continue` — state preserved, no entry/exit logic (`vtrend_variants.py:676-678`). |
| **Evidence from test/spec** | Not directly tested. Implicit in all tests (entry occurs after indicators converge). |
| **Framework implications** | Engine has separate warmup (365 days). In `no_trade` mode, signals discarded during warmup. Strategy warmup is additive. |
| **Assessment** | Warmup logic is straightforward and correct. The two warmup systems (strategy internal + engine external) compose safely because engine warmup >> strategy warmup. |
| **Canonical decision** | **KEEP** — preserve source warmup semantics in strategy |
| **Canonical behavior** | `_compute_warmup()`: find first index where all indicators are finite. Return None before warmup completes. |
| **Rationale** | Correct and safe. No reason to change. |
| **Risk if wrong** | N/A — keeping source behavior. |

### D11: Execution vs Strategy Responsibility Boundary

| Aspect | Detail |
|--------|--------|
| **Source behavior** | Clear separation: strategy → target_weight_signal array → execution engine handles cost, cash, rebalance gating, trade recording. |
| **Evidence from test/spec** | Spec §5: lists execution model properties. |
| **Framework implications** | btc-spot-dev: strategy → Signal → engine handles cost, cash. Rebalance gating must be in strategy (see D3). |
| **Assessment** | Consequence of D3. Strategy takes on rebalance gating responsibility. All other execution concerns remain in engine. |
| **Canonical decision** | **ADAPT** — strategy handles rebalance gating; engine handles everything else |
| **Canonical behavior** | Strategy: entry signals, exit signals, rebalance gating + signals. Engine: cost computation, cash constraints, fill execution, portfolio updates. |
| **Rationale** | Framework constraint. See D3. |
| **Risk if wrong** | See D3 and D4. |

### D12: Cost Model Responsibility

| Aspect | Detail |
|--------|--------|
| **Source behavior** | CostModel with one_way_rate applied in _execute_target_weights(). Strategy does not touch costs. |
| **Evidence from test/spec** | Spec §5: "Cost model on traded notional". |
| **Framework implications** | btc-spot-dev engine handles costs via ExecutionModel + Portfolio. Strategy only emits target_exposure. |
| **Assessment** | Both architectures keep costs out of strategy. Compatible. |
| **Canonical decision** | **KEEP** — strategy does not handle costs |
| **Canonical behavior** | Strategy emits `Signal(target_exposure=X)`. Engine computes fill price, fees, cash constraints. |
| **Rationale** | Fundamental architectural principle. No reason to change. |
| **Risk if wrong** | N/A. |

### D13: Signal Timing

| Aspect | Detail |
|--------|--------|
| **Source behavior** | Signal at bar `i` close → execute at bar `i+1` open. (`vtrend_variants.py:503-505`) |
| **Evidence from test/spec** | Spec §5: "signal formed on close of bar i, order executed on open of bar i+1". Test: `test_entry_signal_executes_at_next_open` (entry_signal at bar X, BUY at bar X+1). |
| **Framework implications** | btc-spot-dev engine: `on_bar()` called at bar close, pending signal executed at next bar open (`engine.py:141-175`). |
| **Assessment** | Source, spec, test, and framework all agree. This is an invariant. |
| **Canonical decision** | **KEEP** — signal at close, execute at next open |
| **Canonical behavior** | `on_bar()` returns Signal at bar close. Engine stores as pending. Executes at next bar open. |
| **Rationale** | Universal agreement across all sources. Framework enforces it. |
| **Risk if wrong** | Lookahead bias if timing changed. Not acceptable. |

### D14: Rebalance When Weight Drops to 0 While LONG

| Aspect | Detail |
|--------|--------|
| **Source behavior** | `target_weight_signal[i] = 0.0` (from _clip_weight returning 0 while active). Execution engine: `target_w=0, current_w>0 → crossing_zero=True → should_trade=True → SELL to flat`. State remains LONG (`active=True`). Next bars: if weight recovers → `crossing_zero=True → BUY`. If weight stays 0 → no trade (already flat). (`vtrend_variants.py:700-702, 510-511, 531-540`) |
| **Evidence from test/spec** | Not tested. Not specified. |
| **Framework implications** | btc-spot-dev engine: `target_exposure=0.0 → sell all if btc_qty > 0` (`engine.py:296-302`). Strategy state remains active. |
| **Assessment** | This is a CONSEQUENCE of the source architecture (strategy always emits weight, engine always executes). In the btc-spot-dev adaptation where strategy gates rebalance, the same behavior emerges naturally: `new_weight=0.0, delta=|0-exposure|=exposure, if exposure > threshold → emit Signal(target_exposure=0.0, reason="rebalance")`. Engine sells to flat. State stays LONG. |
| **Canonical decision** | **KEEP** (emerges naturally from the adapted architecture) |
| **Canonical behavior** | When LONG: compute `new_weight = _clip_weight(target_vol / max(rv, EPS), min_weight)`. If `new_weight = 0.0` and `abs(0.0 - state.exposure) >= threshold`: emit `Signal(target_exposure=0.0, reason="vtrend_sm_rebalance")`. Engine sells to flat. `_active` remains True. Next bar: exit logic checked first; if no exit, rebalance with new weight (may be 0 again → no trade since already flat, or positive → BUY). |
| **Rationale** | This preserves the source's semantic: "I've detected a trend (LONG), but vol-target says reduce to 0. Sell, but remember the trend. If vol normalizes, re-enter without needing new breakout." The btc-spot-dev adaptation produces the same outcome through a different mechanism (strategy-side gating vs engine-side crossing_zero). |
| **Risk if wrong** | With non-default min_weight > 0 and high vol: position is sold to flat while "LONG". If vol normalizes and weight > 0, rebalance logic emits BUY (since delta = |weight - 0| > threshold). This matches source. Risk is acceptable. |

### D15: Config Field Ordering

| Aspect | Detail |
|--------|--------|
| **Source behavior** | Fields 7-9: `target_vol, vol_lookback, slope_lookback` (`vtrend_variants.py:98-100`) |
| **Draft behavior** | Fields 7-9: `slope_lookback, target_vol, vol_lookback` (`strategy.py:53-55`) |
| **Canonical decision** | **ADAPT** — match source ordering for auditability |
| **Canonical behavior** | Field order matches source: `slow_period, fast_period, atr_period, atr_mult, entry_n, exit_n, target_vol, vol_lookback, slope_lookback, use_vdo_filter, vdo_threshold, vdo_fast, vdo_slow, exit_on_regime_break, min_rebalance_weight_delta, min_weight` |
| **Rationale** | No behavioral impact (fields accessed by name). But matching source order enables line-by-line comparison and reduces audit confusion. |
| **Risk if wrong** | None. Cosmetic. |

### Summary Counts

| Decision | Count | Items |
|----------|-------|-------|
| **KEEP** | 8 | D1 (BARS_PER_YEAR), D7 (min_weight), D10 (warmup), D12 (cost), D13 (timing), D14 (rebalance-to-0), D15 (field order) + all A1-A14 core components |
| **ADAPT** | 9 | D2 (entry weight>0), D3 (rebalance location), D4 (rebalance basis), D5 (VDO fallback), D6 (VDO NaN), D8 (frozen), D9 (validation), D11 (boundary), D15 (field order) |
| **DROP** | 0 | — |
| **REQUIRE_EXPERIMENT** | 0 | — (cross-validation is Phase 5 work, not a design blocker) |

---

## 6. Canonical Design Contract

### 6.1 Canonical Algorithm Definition

#### 6.1.1 State Model

Binary state machine with two states:
- **FLAT** (`_active = False`): no position intended. Check entry conditions each bar.
- **LONG** (`_active = True`): trend detected. Check exit conditions and rebalance each bar.

No intermediate states. No hysteresis. No regime memory across bars.

Initial state: FLAT.

#### 6.1.2 Entry Logic (FLAT → LONG)

On each bar where `_active = False` and warmup complete:

```
regime_ok = (ema_fast[i] > ema_slow[i]) AND (ema_slow[i] > ema_slow[i - slope_lookback])
breakout_ok = (close[i] > rolling_high_shifted[i])
vdo_ok = True
IF use_vdo_filter:
    IF vdo[i] is not finite: RETURN None (skip bar)
    vdo_ok = (vdo[i] > vdo_threshold)

IF regime_ok AND breakout_ok AND vdo_ok:
    weight = _clip_weight(target_vol / max(rv[i], EPS), min_weight)
    IF weight > 0.0:                           # ← ADAPTATION D2
        _active = True
        RETURN Signal(target_exposure=weight, reason="vtrend_sm_entry")
```

#### 6.1.3 Exit Logic (LONG → FLAT)

On each bar where `_active = True`:

```
exit_floor = max(rolling_low_shifted[i], ema_slow[i] - atr_mult * atr[i])
floor_break = (close[i] < exit_floor)
regime_break = exit_on_regime_break AND NOT regime_ok

IF floor_break OR regime_break:
    _active = False
    reason = "vtrend_sm_floor_exit" if floor_break else "vtrend_sm_regime_exit"
    RETURN Signal(target_exposure=0.0, reason=reason)
```

`regime_ok` is computed the same way as in entry (per-bar, no memory).

#### 6.1.4 Adaptive Floor Definition

```
exit_floor = max(
    rolling_low_shifted(low, exit_n)[i],    # structural support
    ema_slow[i] - atr_mult * atr[i]         # EMA-based floor
)
```

Two components:
1. **Rolling low**: `min(low[i-exit_n], ..., low[i-1])` — structural support from recent lows
2. **EMA floor**: `ema_slow - atr_mult * ATR` — trend-adjusted floor (tightens in low-vol, loosens in high-vol)

The `max()` of both floors gives the more conservative (higher) exit trigger.

#### 6.1.5 Regime Logic

```
regime_ok = (ema_fast[i] > ema_slow[i]) AND (ema_slow[i] > ema_slow[i - slope_lookback])
```

Two conditions:
1. Fast EMA above slow EMA (trend direction)
2. Slow EMA increasing (trend strength/momentum)

Per-bar evaluation with no memory. Regime can flip on any bar.

#### 6.1.6 VDO / Filter Semantics

VDO is **optional** (`use_vdo_filter=False` by default).

When enabled:
- VDO = `EMA(vdr, vdo_fast) - EMA(vdr, vdo_slow)`
- VDR (taker path) = `(2 * taker_buy - volume) / volume`
- VDR (OHLC proxy, when all taker_buy = 0) = `(close - low) / (high - low) * 2 - 1`
- Entry requires `vdo[i] > vdo_threshold`
- VDO does NOT affect exit logic
- VDO NaN during post-warmup → skip bar entirely (`return None`)

#### 6.1.7 Position Sizing

Vol-targeted fractional sizing:

```
raw_weight = target_vol / max(rv[i], EPS)
weight = _clip_weight(raw_weight, min_weight)

def _clip_weight(weight, min_weight=0.0):
    if not isfinite(weight): return 0.0
    w = min(1.0, max(0.0, weight))
    if w < min_weight: return 0.0
    return w
```

Produces continuous values in `(0.0, 1.0]` when active (with default min_weight=0.0).

#### 6.1.8 Rebalance Semantics

When LONG and no exit triggered:

```
new_weight = _clip_weight(target_vol / max(rv[i], EPS), min_weight)
delta = abs(new_weight - state.exposure)          # close-price basis (ADAPTATION D4)
IF delta >= min_rebalance_weight_delta - 1e-12:
    RETURN Signal(target_exposure=new_weight, reason="vtrend_sm_rebalance")
```

Notes:
- Rebalance gating is in the strategy (ADAPTATION D3)
- Comparison uses close-price exposure (ADAPTATION D4)
- Entry and exit bypass the threshold (separate code paths always emit)
- When `new_weight = 0.0` (vol-target says "reduce to nothing"): rebalance signal with `target_exposure=0.0` is emitted if delta exceeds threshold. Engine sells to flat. `_active` stays True (see D14).

#### 6.1.9 Signal Timing

- `on_bar()` called at bar close
- Returns Signal (or None)
- Engine stores Signal as pending
- Engine executes pending at next bar open
- **Invariant**: signal at close(i) → fill at open(i+1)

#### 6.1.10 Warmup

`_compute_warmup()`: scan from index 0, return first index where ALL of the following are finite:
- `ema_fast[i]`, `ema_slow[i]`, `ema_slow_slope_ref[i]`
- `atr[i]`, `hh_entry[i]`, `ll_exit[i]`, `rv[i]`
- `vdo[i]` (only when `use_vdo_filter=True`)

Before warmup completes: `on_bar()` returns None.

#### 6.1.11 Data Dependencies

Required from `h4_bars`:
- `bar.close` (EMA, realized vol, breakout, floor check)
- `bar.high` (ATR, rolling high, VDO OHLC proxy)
- `bar.low` (ATR, rolling low, VDO OHLC proxy)
- `bar.volume` (VDO, when enabled)
- `bar.taker_buy_base_vol` (VDO, when enabled)

Not used: `bar.open`, `bar.open_time`, `bar.close_time`, `bar.interval`, `d1_bars`.

#### 6.1.12 Missing-Data / NaN Behavior

| Scenario | Behavior |
|----------|----------|
| Any core indicator NaN post-warmup | Return None (skip bar). `_active` state preserved. |
| VDO NaN when `use_vdo_filter=True` | Return None (skip bar). |
| `rv` = 0 or near-zero | `target_vol / max(rv, EPS)` → very large → `_clip_weight` clamps to 1.0. |
| All `taker_buy` = 0 | `_vdo()` uses OHLC proxy fallback. |
| Empty `h4_bars` | `on_init()` returns early. `on_bar()` returns None (indicators not set). |

#### 6.1.13 Execution Assumptions

The strategy assumes the engine:
1. Calls `on_init(h4_bars, d1_bars)` before the first `on_bar()`
2. Calls `on_bar(state)` once per H4 bar at bar close
3. Provides `state.bar_index` as the index into the same `h4_bars` array given to `on_init()`
4. Provides `state.exposure` as the current portfolio exposure at bar close price
5. Executes returned Signal at the next bar's open price
6. Handles cost computation, cash constraints, fill pricing
7. Clamps `target_exposure` to [0, 1] (`engine.py:291`)
8. Has its own minimum exposure threshold (`_EXPO_THRESHOLD = 0.005`)

### 6.2 Parameter Contract

#### 6.2.1 Parameters Kept From Source

All 16 parameters from `VTrendStateMachineParams` are preserved with identical names and defaults:

| # | Parameter | Type | Default | Source line |
|---|-----------|------|---------|-------------|
| 1 | `slow_period` | `int` | `120` | `vtrend_variants.py:92` |
| 2 | `fast_period` | `int \| None` | `None` | `vtrend_variants.py:93` |
| 3 | `atr_period` | `int` | `14` | `vtrend_variants.py:94` |
| 4 | `atr_mult` | `float` | `3.0` | `vtrend_variants.py:95` |
| 5 | `entry_n` | `int \| None` | `None` | `vtrend_variants.py:96` |
| 6 | `exit_n` | `int \| None` | `None` | `vtrend_variants.py:97` |
| 7 | `target_vol` | `float` | `0.15` | `vtrend_variants.py:98` |
| 8 | `vol_lookback` | `int \| None` | `None` | `vtrend_variants.py:99` |
| 9 | `slope_lookback` | `int` | `6` | `vtrend_variants.py:100` |
| 10 | `use_vdo_filter` | `bool` | `False` | `vtrend_variants.py:101` |
| 11 | `vdo_threshold` | `float` | `0.0` | `vtrend_variants.py:102` |
| 12 | `vdo_fast` | `int` | `12` | `vtrend_variants.py:103` |
| 13 | `vdo_slow` | `int` | `28` | `vtrend_variants.py:104` |
| 14 | `exit_on_regime_break` | `bool` | `False` | `vtrend_variants.py:105` |
| 15 | `min_rebalance_weight_delta` | `float` | `0.05` | `vtrend_variants.py:106` |
| 16 | `min_weight` | `float` | `0.0` | `vtrend_variants.py:107` |

Field ordering matches source (positions 7-9: target_vol, vol_lookback, slope_lookback).

#### 6.2.2 Auto-Derived Parameters

All four auto-derivation formulas preserved exactly:

| Parameter | Formula | Source line |
|-----------|---------|-------------|
| `fast_period` | `max(5, slow_period // 4)` | `vtrend_variants.py:112` |
| `entry_n` | `max(24, slow_period // 2)` | `vtrend_variants.py:113` |
| `exit_n` | `max(12, slow_period // 4)` | `vtrend_variants.py:114` |
| `vol_lookback` | `slow_period` | `vtrend_variants.py:115` |

Computed in `resolved()` method. Input `None` → auto-derive. Explicit value → use as-is.

#### 6.2.3 Implementation Semantics Changes

| Parameter | Source Semantics | Canonical Semantics | Change |
|-----------|------------------|---------------------|--------|
| All 16 | frozen (immutable after construction) | mutable @dataclass | Mutation allowed but not expected during backtest |
| `slope_lookback` | validated in `resolved()` | validated in `__post_init__` | Fail-fast: invalid config cannot exist |

No parameter **names** or **default values** are changed. No parameter has its **meaning** redefined.

### 6.3 Project-Native Adaptation Contract

#### 6.3.1 Adaptations PERMITTED

| # | Adaptation | Rationale | Constraint |
|---|-----------|-----------|------------|
| P1 | Mutable `@dataclass` (not frozen) | Framework requires `setattr()` for config overrides | Config should NOT be mutated after strategy construction |
| P2 | `__post_init__` validation | Fail-fast is safer | Must validate same conditions as source `resolved()` |
| P3 | Rebalance gating in strategy | Engine has no configurable threshold | Must preserve threshold semantics and crossing-zero behavior |
| P4 | Close-price exposure for rebalance | Strategy cannot access next-bar open | Close-price is the best available proxy |
| P5 | OHLC proxy in `_vdo()` | btc-spot-dev data always has taker field, proxy for zero values | Follows existing VTREND E0 convention |
| P6 | Entry requires weight > 0 | Prevents incoherent LONG-with-no-position state | With default min_weight=0.0, identical to source |
| P7 | Explicit NaN check in VDO entry | Clearer than implicit `bool(NaN > x)` | Only affects pathological case |
| P8 | numpy indicators (not pandas) | btc-spot-dev convention | Mathematical equivalence required (verified in 34b audit) |
| P9 | No EMA span validation | Unreachable via config auto-derivation | _ema() assumes valid period |
| P10 | Separate exit reasons | "vtrend_sm_floor_exit" vs "vtrend_sm_regime_exit" | Additive information, no behavioral change |

#### 6.3.2 Adaptations NOT PERMITTED

| # | Prohibition | Reason |
|---|------------|--------|
| N1 | Changing entry conditions (regime, breakout, VDO conjunction) | Core algorithm identity |
| N2 | Changing exit conditions (adaptive floor, optional regime break) | Core algorithm identity |
| N3 | Changing adaptive floor formula | Core algorithm identity |
| N4 | Changing vol-target sizing formula | Core algorithm identity |
| N5 | Changing `_clip_weight` behavior | Core mapping function |
| N6 | Changing auto-derivation formulas | Parameter contract |
| N7 | Changing signal timing (close → next open) | Universal invariant |
| N8 | Changing BARS_PER_YEAR_4H from 2190.0 | Decision D1 |
| N9 | Adding indicator hysteresis or state memory | Not VTREND-SM (would be LATCH) |
| N10 | Adding cost handling in strategy | Engine responsibility |
| N11 | Changing EPS from 1e-12 | Numerical constant |

#### 6.3.3 Adaptations Requiring Verification

| # | Item | Verification Method |
|---|------|-------------------|
| V1 | Close-price rebalance vs open-price rebalance | Cross-validation in Phase 5: count rebalance trades, expect < 5% difference vs source standalone |
| V2 | Entry weight > 0 guard | Verify with default params: zero divergence from source. Verify with min_weight > 0: document trade count difference. |

---

## 7. Acceptance Criteria for Prompt 5

### 7.1 Invariants (Must Hold In Any Implementation)

| # | Invariant | Verification |
|---|-----------|-------------|
| I1 | Signal timing: signal at bar close → fill at next bar open | Test: entry_signal at bar X → fill at bar X+1 |
| I2 | Target exposure range: `[0.0, 1.0]` | Test: no Signal with target_exposure outside range |
| I3 | State machine: exactly two states (FLAT, LONG) | Code review: only `_active = True/False` |
| I4 | Entry requires ALL of: regime_ok AND breakout_ok AND vdo_ok (when enabled) AND weight > 0 | Test: entry only when all conditions met |
| I5 | Exit requires ANY of: floor_break OR regime_break (when enabled) | Test: exit on floor break alone; exit on regime break alone (when enabled) |
| I6 | Adaptive floor = `max(rolling_low, ema_slow - atr_mult * ATR)` | Test: numerical verification against known values |
| I7 | Regime = `(ema_fast > ema_slow) AND (ema_slow > ema_slow.shift(slope_lookback))` | Test: slope_lookback affects signals (per source test) |
| I8 | Breakout = `close > rolling_high(high.shift(1), entry_n)` | Numerical test |
| I9 | Vol-target sizing = `_clip_weight(target_vol / max(rv, EPS), min_weight)` | Test: weight bounded [0, 1]; high vol → small weight; low vol → weight ≈ 1.0 |
| I10 | Warmup: no signals before all indicators converge | Test: first N bars return None |
| I11 | `_clip_weight`: NaN→0, clamp [0,1], below min_weight→0 | Unit test of function |
| I12 | No cost handling in strategy | Code review: no reference to CostConfig, ExecutionModel, fee, spread |
| I13 | `on_after_fill` is no-op | Code review: pass |
| I14 | `BARS_PER_YEAR_4H = 365.0 * 6.0 = 2190.0` | Code review + test |
| I15 | Config defaults match source (all 16 values) | Test: `VTrendSMConfig()` matches `VTrendStateMachineParams()` |
| I16 | Auto-derivation formulas match source (all 4) | Test: `resolved()` output matches source `resolved()` output |

### 7.2 Behaviors That Must Match Source Near-Exactly

| # | Behavior | Tolerance | Verification |
|---|----------|-----------|-------------|
| B1 | `_ema(series, period)` output | Exact (float64 precision) | Numerical test vs pandas `ewm(span=N, adjust=False).mean()` |
| B2 | `_atr(high, low, close, period)` output | Exact (float64 precision) | Numerical test vs source `atr_wilder()` |
| B3 | `_rolling_high_shifted(high, lookback)` output | Exact | Numerical test: specific known values |
| B4 | `_rolling_low_shifted(low, lookback)` output | Exact | Numerical test: specific known values |
| B5 | `_realized_vol(close, lookback, bars_per_year)` output | Exact (float64 precision) | Numerical test vs source `annualized_realized_vol()` |
| B6 | `_vdo()` output (taker path) | Exact (float64 precision) | Numerical test vs source `compute_vdo_base()` |
| B7 | `_clip_weight()` output | Character-identical function | Unit test of all branches |
| B8 | State transitions (with default params) | Exact | Test: same synthetic data → same entry/exit bar indices |
| B9 | Target weights (with default params) | Exact (float64 precision) | Test: same synthetic data → same weight values |

### 7.3 Behaviors Permitted to Differ From Source

| # | Behavior | Reason | Expected Magnitude |
|---|----------|--------|-------------------|
| E1 | Rebalance trade count | Close-price vs open-price comparison basis (D4) | < 5% difference in trade count |
| E2 | Rebalance bar indices | Same as E1 | Off by 0-1 bars at boundary cases |
| E3 | Entry blocked when weight=0 after clip with min_weight > 0 | Adaptation D2 | Only with non-default min_weight. Default params: zero divergence. |
| E4 | VDO values with zero taker data | OHLC proxy fallback (D5) | Only with atypical data. Normal data: zero divergence. |
| E5 | Config construction fails on slope_lookback=0 | __post_init__ validation (D9) | Earlier error, same message |

### 7.4 Minimum Test Cases

| # | Test Case | Covers |
|---|-----------|--------|
| T1 | Config defaults match source | I15 |
| T2 | Config `resolved()` auto-derivation | I16 |
| T3 | `_ema` numerical correctness | B1 |
| T4 | `_atr` numerical correctness | B2 |
| T5 | `_rolling_high_shifted` numerical correctness | B3 |
| T6 | `_rolling_low_shifted` numerical correctness | B4 |
| T7 | `_realized_vol` numerical correctness | B5 |
| T8 | `_clip_weight` all branches (finite, NaN, inf, below min_weight) | B7, I11 |
| T9 | Entry signal when regime+breakout conditions met | I4, B8 |
| T10 | No entry during warmup | I10 |
| T11 | Exit on floor break | I5 |
| T12 | Exit on regime break (when enabled) | I5, I6 |
| T13 | No exit on regime break (when disabled) | A6 |
| T14 | Vol-targeted sizing: weight = target_vol / rv | I9, B9 |
| T15 | Rebalance threshold: small changes suppressed | A9 |
| T16 | Rebalance threshold: large changes produce signal | A9 |
| T17 | Weights bounded [0, 1] | I2, I9 |
| T18 | VDO filter blocks entry when negative (if enabled) | A5 |
| T19 | slope_lookback affects signals | A2, I7 |
| T20 | Engine integration smoke test (no crash, produces equity) | All |
| T21 | BARS_PER_YEAR_4H = 2190.0 | I14 |

### 7.5 Residual Uncertainties (Post-Implementation Monitoring)

| # | Uncertainty | How to Monitor |
|---|-----------|----------------|
| U1 | Close-price vs open-price rebalance difference magnitude | Cross-validation: count rebalance trades, compare vs Latch standalone |
| U2 | OHLC proxy VDO fidelity | Only relevant when VDO enabled with suspect data. Compare taker-based vs proxy on real data. |
| U3 | Entry weight>0 guard impact with non-default min_weight | Run parameter sweep with min_weight ∈ {0.0, 0.05, 0.1}: count missed entries |

---

## 8. Open Questions / Required Experiments

### 8.1 Experiments Not Required Before Implementation

All design decisions in §5 have sufficient evidence to make canonical choices. No experiment blocks implementation.

### 8.2 Experiments Required After Implementation (Phase 5)

| # | Experiment | Purpose | Smallest Viable Design |
|---|-----------|---------|----------------------|
| X1 | **Cross-validation vs Latch standalone** | Verify that btc-spot-dev VTREND-SM produces comparable metrics on the same data | Run both on `data/bars_btcusdt_2016_now_h1_4h_1d.csv` with matching cost params. Compare CAGR, Sharpe, MDD, trade count. Expected tolerance: CAGR within 2%, Sharpe within 0.05, trade count within 5%. |
| X2 | **Rebalance trade count comparison** | Quantify D4 (close-price vs open-price) impact | From X1: count rebalance trades in both. Expected: < 5% difference. |
| X3 | **min_weight > 0 behavior audit** | Verify D2 (entry weight>0 guard) for non-default params | Run with `min_weight=0.1, target_vol=0.05` on high-vol period. Count entries in btc-spot-dev vs Latch. Document divergence. |

---

## 9. Readiness Verdict

### 9.1 Is the Design Sufficiently Clear to Code?

**YES.** The canonical design contract in §6 specifies every component of the algorithm with exact formulas, edge case handling, and NaN behavior. Every disputed behavior has a decision with rationale. No ambiguity remains.

### 9.2 Remaining Blockers

**None.** All 15 decision items resolved. Zero REQUIRE_EXPERIMENT items.

### 9.3 Implementation Checklist for Prompt 5

| # | Task | Status |
|---|------|--------|
| 1 | Rewrite `strategies/vtrend_sm/strategy.py` per §6 contract | To do |
| 2 | Fix `BARS_PER_YEAR_4H` to `365.0 * 6.0` | To do (was 6.0 * 365.25 in draft) |
| 3 | Fix config field ordering to match source | To do (draft reordered positions 7-9) |
| 4 | Add entry weight > 0 guard (D2) | To do (already in draft, source doesn't have it — now canonically required) |
| 5 | Remove NaN-path differences (VDO check returns None vs continuing) | To do (draft already does this — now canonical) |
| 6 | Register in 4 files (config.py, candidates.py, strategy_factory.py, cli/backtest.py) | To do |
| 7 | Write `tests/test_vtrend_sm.py` with T1-T21 | To do |
| 8 | Integration smoke test with BacktestEngine | To do |
| 9 | Cross-validation experiment X1 | Post-implementation |

### 9.4 What Changed From Prompt 3's Recommendations

| Prompt 3 Said | Prompt 4 Says | Why |
|--------------|---------------|-----|
| F1: Change BARS_PER_YEAR_4H from 2191.5 to 2190.0 | **Confirmed** (D1: KEEP source value) | Source AND metrics.py agree on 2190.0 |
| F2: Remove weight > 0 entry guard | **Reversed** — keep the guard (D2: ADAPT) | Guard prevents incoherent state. Source behavior is untested edge case. Default params: identical. |
| M3/M4: Accept rebalance in strategy as pragmatic | **Confirmed** (D3/D4: ADAPT) | Framework forces this. Close-price is best available. |
| M5: Accept VDO proxy | **Confirmed** (D5: ADAPT) | btc-spot-dev convention. Bar always has data. |
| M7: Field ordering cosmetic | **Specified**: match source ordering (D15) | Enables line-by-line audit |
| M8: Mutable OK | **Confirmed** (D8: ADAPT) | Framework requirement. |

---

## Appendix: Evidence Index

| Evidence | File | Lines | Used In |
|----------|------|-------|---------|
| BARS_PER_YEAR_4H = 2190.0 | `Latch/research/vtrend_variants.py` | 43 | D1 |
| PERIODS_PER_YEAR_4H = 2190.0 | `btc-spot-dev/v10/core/metrics.py` | 19 | D1, C1 |
| MEMORY.md 2191.5 convention | `memory/MEMORY.md` | Conventions section | C1 |
| VTrendStateMachineParams (16 fields) | `Latch/research/vtrend_variants.py` | 77-122 | §6.2, C6, C7 |
| run_vtrend_state_machine signal loop | `Latch/research/vtrend_variants.py` | 674-704 | §6.1, C2, D2 |
| _execute_target_weights rebalance | `Latch/research/vtrend_variants.py` | 504-511 | C3, C4, D3, D4 |
| _clip_weight | `Latch/research/vtrend_variants.py` | 415-421 | D7 |
| _warmup_start | `Latch/research/vtrend_variants.py` | 424-429 | D10 |
| validate_market_frame | `Latch/research/vtrend_variants.py` | 236-268 | C5, D5 |
| compute_vdo_base (no proxy) | `Latch/research/vtrend_variants.py` | 321-333 | C5, D5 |
| test_entry_signal_executes_at_next_open | `Latch/research/test_vtrend_variants.py` | 41-60 | A8, D13 |
| test_small_entry_weight_still_executes_buy | `Latch/research/test_vtrend_variants.py` | 119-138 | C2, D2 |
| test_optional_vdo_filter_requires_columns | `Latch/research/test_vtrend_variants.py` | 62-73 | C5, D5 |
| test_rebalance_threshold_reduces_trade_events | `Latch/research/test_vtrend_variants.py` | 75-99 | A9, D3 |
| test_slope_lookback_affects_signals | `Latch/research/test_vtrend_variants.py` | 140-168 | A2 |
| Spec §3.2 (entry/exit) | `Latch/research/VTREND_SPEC_AND_GUIDE.md` | 38-46 | A1-A6, C2 |
| Spec §5 (execution model) | `Latch/research/VTREND_SPEC_AND_GUIDE.md` | 77-91 | A8, A9, D3, D13 |
| Strategy base class | `btc-spot-dev/v10/strategies/base.py` | 17-49 | §6.1.13 |
| BacktestEngine bar loop | `btc-spot-dev/v10/core/engine.py` | 121-175 | D13, C3, C4 |
| _apply_target_exposure | `btc-spot-dev/v10/core/engine.py` | 279-322 | D3, D4, D14 |
| _EXPO_THRESHOLD | `btc-spot-dev/v10/core/engine.py` | 28 | D3 |
| MarketState.exposure | `btc-spot-dev/v10/core/engine.py` | 219 | C4, D4 |
| Bar type (taker_buy_base_vol) | `btc-spot-dev/v10/core/types.py` | 37 | C5, D5 |
| strategy_factory setattr | `btc-spot-dev/validation/strategy_factory.py` | 43-46 | C6, D8 |
| VTREND E0 _vdo (OHLC proxy) | `btc-spot-dev/strategies/vtrend/strategy.py` | 159-177 | D5 |
| VTREND E0 @dataclass (mutable) | `btc-spot-dev/strategies/vtrend/strategy.py` | 29 | D8 |
