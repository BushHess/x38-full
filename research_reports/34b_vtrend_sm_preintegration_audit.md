# Report 34b: VTREND-SM Pre-Integration Audit

> **Phase**: 3 — Pre-integration audit (READ-ONLY, no code changes)
> **Date**: 2026-03-04
> **Status**: Complete — awaiting review before Prompt 4
>
> **Note (2026-03-14)**: References to VDO OHLC fallback in this report are
> now outdated. The fallback has been removed from ALL strategies — E0, E5,
> E5_ema21D1, V8Apex, V11Hybrid, V12, V13, X7 (P0 fix). VDO now raises
> RuntimeError without real taker data. See `tests/test_vdo_semantic.py`.

---

## 1. Scope

This report audits the implementation draft at `strategies/vtrend_sm/strategy.py` (364 lines) against the source-of-truth `Latch/research/vtrend_variants.py` function `run_vtrend_state_machine()` (lines 588–727) and supporting code (lines 43–580).

**Constraint**: No source code was modified in this prompt. Only this report file was created.

---

## 2. Files Audited

| # | File | Role |
|---|------|------|
| 1 | `Latch/research/vtrend_variants.py` (896 lines) | Source-of-truth |
| 2 | `Latch/research/test_vtrend_variants.py` (253 lines) | Source test suite |
| 3 | `Latch/research/VTREND_SPEC_AND_GUIDE.md` (284 lines) | Source specification |
| 4 | `btc-spot-dev/research_reports/34_vtrend_sm_survey.md` | Survey report to cross-audit |
| 5 | `btc-spot-dev/strategies/vtrend_sm/__init__.py` (13 lines) | Draft module init |
| 6 | `btc-spot-dev/strategies/vtrend_sm/strategy.py` (364 lines) | Draft implementation |

---

## 3. Exactness Matrix

### 3.1 Config Structure

| Item | Verdict | Evidence |
|------|---------|----------|
| **Field names** | `EXACT_MATCH` | All 16 field names identical. Source: `VTrendStateMachineParams` (`vtrend_variants.py:92-107`). Draft: `VTrendSMConfig` (`strategy.py:47-62`). |
| **Default values** | `EXACT_MATCH` | All 16 defaults identical. `slow_period=120`, `fast_period=None`, `atr_period=14`, `atr_mult=3.0`, `entry_n=None`, `exit_n=None`, `target_vol=0.15`, `vol_lookback=None`, `slope_lookback=6`, `use_vdo_filter=False`, `vdo_threshold=0.0`, `vdo_fast=12`, `vdo_slow=28`, `exit_on_regime_break=False`, `min_rebalance_weight_delta=0.05`, `min_weight=0.0`. |
| **Field ordering** | `MISMATCH` | Source order (positions 7-9): `target_vol`, `vol_lookback`, `slope_lookback` (`vtrend_variants.py:98-100`). Draft order (positions 7-9): `slope_lookback`, `target_vol`, `vol_lookback` (`strategy.py:53-55`). Three fields are reordered. Does not affect behavior (fields accessed by name) but is a deviation from source. |
| **Frozen attribute** | `MISMATCH` | Source uses `@dataclass(frozen=True)` (`vtrend_variants.py:77`). Draft uses `@dataclass` without `frozen` (`strategy.py:45`). Source instances are immutable; draft instances are mutable. Reason: btc-spot-dev framework uses `setattr()` for config overrides (see `validation/strategy_factory.py:43-46`). This is a deliberate adaptation for framework compatibility, but it is a factual deviation from source. |
| **Auto-derivation logic** | `EXACT_MATCH` | All 4 auto-derivation formulas identical: `fast_period = max(5, slow_period // 4)`, `entry_n = max(24, slow_period // 2)`, `exit_n = max(12, slow_period // 4)`, `vol_lookback = slow_period`. Source: `vtrend_variants.py:112-115`. Draft: `strategy.py:70-89`. |
| **Validation timing** | `MISMATCH` | Source validates `slope_lookback <= 0` inside `resolved()` (`vtrend_variants.py:110-111`). Draft validates in `__post_init__()` (`strategy.py:64-66`). Source: `VTrendStateMachineParams(slope_lookback=0)` succeeds; `params.resolved()` raises. Draft: `VTrendSMConfig(slope_lookback=0)` raises immediately. Different failure point for the same invalid input. |

### 3.2 Indicators

| Item | Verdict | Evidence |
|------|---------|----------|
| **EMA formula** | `SEMANTIC_MATCH` | Source: `series.ewm(span=N, adjust=False).mean()` (pandas, `vtrend_variants.py:274-275`). Draft: recursive `alpha * x[i] + (1-alpha) * ema[i-1]` with `alpha = 2/(period+1)` (numpy, `strategy.py:103-108`). Mathematically identical — pandas `ewm(adjust=False)` implements exactly this recursion. |
| **EMA input validation** | `MISMATCH` | Source: `if span <= 0: raise ValueError` (`vtrend_variants.py:272-273`). Draft: no validation in `_ema()` (`strategy.py:101-108`). Draft relies on config-level constraints (auto-derivation ensures period >= 5). |
| **ATR formula** | `SEMANTIC_MATCH` | Source: `prev_close = close.shift(1).fillna(close.iloc[0])`, then Wilder RMA (`vtrend_variants.py:283-298`). Draft: `np.concatenate([[high[0]], close[:-1]])` and `[[low[0]], close[:-1]]` for prev_close stand-in, then same Wilder RMA (`strategy.py:114-126`). At index 0, source uses `close[0]` as prev_close; draft uses `high[0]` and `low[0]`. However, TR[0] = max(H-L, |H-prevC|, |L-prevC|) is always H[0]-L[0] regardless, because H-L >= |H-close| and H-L >= |close-L| for any close in [L,H]. So final TR[0] and all subsequent ATR values are identical. |
| **rolling_high_shifted** | `EXACT_MATCH` | Source: `high.shift(1).rolling(window=N, min_periods=N).max()` (`vtrend_variants.py:312`). Draft: `for i in range(lookback, n): out[i] = np.max(high[i-lookback:i])` (`strategy.py:158-159`). Both produce NaN before index `lookback`, then `max(high[i-lookback..i-1])` at index i. Verified with concrete example: lookback=3, high=[10,20,30,40,50] → both produce [NaN, NaN, NaN, 30, 40]. |
| **rolling_low_shifted** | `EXACT_MATCH` | Symmetric to rolling_high_shifted. Source: `strategy.py:163-173` vs `vtrend_variants.py:318`. Same NaN pattern, same window. |
| **realized_vol formula** | `EXACT_MATCH` | Both compute `std(log_returns, ddof=0) * sqrt(bars_per_year)` over a rolling window of `lookback` log-return values. Source: `vtrend_variants.py:305`. Draft: `strategy.py:196-198`. Window alignment verified: at index `lookback`, source uses `log_returns[1:lookback+1]` (lookback values), draft uses `lr[1:lookback+1]` (same). |
| **realized_vol annualization constant** | `MISMATCH` | Source passes `bars_per_year` from function arg, default `BARS_PER_YEAR_4H = 365.0 * 6.0 = 2190.0` (`vtrend_variants.py:43, 592, 644`). Draft hardcodes `BARS_PER_YEAR_4H = 6.0 * 365.25 = 2191.5` (`strategy.py:39, 265`). These produce different `sqrt()` factors: `sqrt(2190) ≈ 46.7974` vs `sqrt(2191.5) ≈ 46.8134`. The 0.034% difference in the annualization factor directly affects every realized_vol value and therefore every vol-targeted position size. This is a **deviation from source**, not a negligible rounding difference. |
| **VDO formula (taker path)** | `EXACT_MATCH` | Source: `vdr = (2*buy - vol) / vol` (`vtrend_variants.py:326-331`). Draft: `vdr = (buy - sell) / vol` where `sell = vol - buy` (`strategy.py:137-140`). Algebraically identical: `(buy - (vol-buy)) / vol = (2*buy - vol) / vol`. |
| **VDO OHLC proxy fallback** | `MISMATCH` | Source `compute_vdo_base()` has NO OHLC fallback — it requires volume columns when VDO is enabled, validated by `validate_market_frame(require_vdo_columns=True)` (`vtrend_variants.py:241-244`). Draft `_vdo()` has an OHLC proxy fallback: `(close-low)/(high-low)*2-1` when taker data is absent (`strategy.py:141-145`). When `use_vdo_filter=True` and taker data is missing: source raises `ValueError`, draft silently uses proxy. |

### 3.3 Constants and Warmup

| Item | Verdict | Evidence |
|------|---------|----------|
| **BARS_PER_YEAR_4H** | `MISMATCH` | Source: `365.0 * 6.0 = 2190.0` (`vtrend_variants.py:43`). Draft: `6.0 * 365.25 = 2191.5` (`strategy.py:39`). Numerical difference: 1.5 bars/year, 0.068%. |
| **EPS** | `EXACT_MATCH` | Both: `1e-12`. Source: `vtrend_variants.py:44`. Draft: `strategy.py:40`. |
| **Warmup computation** | `SEMANTIC_MATCH` | Source: `_warmup_start()` finds first index where all indicator arrays are finite using vectorized `np.isfinite` AND-mask (`vtrend_variants.py:424-429`). Draft: `_compute_warmup()` iterates per-index with `all(np.isfinite(a[i]) for a in arrays)` (`strategy.py:276-287`). Same result, different implementation. Same set of arrays checked (7 core + optional VDO). |

### 3.4 Signal Logic

| Item | Verdict | Evidence |
|------|---------|----------|
| **Binary state semantics** | `EXACT_MATCH` | Source: `active = False` (`vtrend_variants.py:674`). Draft: `self._active = False` (`strategy.py:230`). Both binary (True=LONG, False=FLAT), no intermediate states. |
| **Regime check** | `EXACT_MATCH` | Source: `regime_ok = (ema_fast > ema_slow) and (ema_slow > ema_slow_slope_ref)` (`vtrend_variants.py:680`). Draft: `regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)` (`strategy.py:315`). |
| **Breakout check** | `EXACT_MATCH` | Source: `breakout_ok = close > hh_entry` (`vtrend_variants.py:681`). Draft: `breakout_ok = close_val > hh` (`strategy.py:319`). |
| **Entry logic (conditions)** | `EXACT_MATCH` | Both: `regime_ok AND breakout_ok AND vdo_ok` → set active=True. Source: `vtrend_variants.py:688-691`. Draft: `strategy.py:327-332`. |
| **Entry logic (weight guard)** | `MISMATCH` | Source: enters unconditionally when conditions met — sets `active=True`, `entry_signal=True`, then computes weight separately (may be 0.0 after clipping) (`vtrend_variants.py:689-691, 700-701`). Draft: computes weight FIRST, only enters if `weight > 0.0` (`strategy.py:328-332`). When `min_weight > 0` and `target_vol / rv < min_weight`: source enters with weight=0.0 (stuck in LONG with no position); draft stays FLAT. Different state machine behavior. |
| **Exit logic** | `SEMANTIC_MATCH` | Source: `floor_break or regime_break → active=False, exit_signal=True` (`vtrend_variants.py:693-697`). Draft: same conditions → `self._active=False, Signal(target_exposure=0.0)` (`strategy.py:339-348`). Draft additionally differentiates exit reason ("vtrend_sm_floor_exit" vs "vtrend_sm_regime_exit"), which is additive and does not change behavior. |
| **Adaptive floor** | `EXACT_MATCH` | Source: `max(ll_exit, ema_slow - atr_mult * atr)` (`vtrend_variants.py:686`). Draft: `max(ll, ema_s - atr_mult * atr_val)` (`strategy.py:338`). |
| **Regime break option** | `SEMANTIC_MATCH` | Source: `bool(resolved["exit_on_regime_break"] and (not regime_ok))` (`vtrend_variants.py:694`). Draft: `r["exit_on_regime_break"] and (not regime_ok)` (`strategy.py:340`). Trivial difference: source wraps in `bool()`, Python truthiness gives same result. |
| **VDO filter (NaN handling)** | `MISMATCH` | Source: `bool(vdo_loop[i] > threshold)` returns False for NaN → blocks entry, continues bar processing (`vtrend_variants.py:684`). Draft: `if not np.isfinite(vdo_val): return None` → returns None, skipping all remaining bar logic (`strategy.py:323-324`). Outcome: both block entry on NaN VDO, but draft also skips rebalance/exit checks for that bar (irrelevant when FLAT, but structurally different). |
| **Position sizing formula** | `EXACT_MATCH` | Both: `_clip_weight(target_vol / max(rv, EPS), min_weight)`. Source: `vtrend_variants.py:701`. Draft: `strategy.py:328-329`. `_clip_weight` functions are character-identical: `strategy.py:202-209` vs `vtrend_variants.py:415-421`. |

### 3.5 Rebalance and Execution

| Item | Verdict | Evidence |
|------|---------|----------|
| **Rebalance gating location** | `MISMATCH` | Source: strategy sets `target_weight_signal[i]` on EVERY active bar. Rebalance gating happens in `_execute_target_weights()` at execution time, comparing `target_weight_signal[i-1]` vs `current_weight_at_open(i)` (`vtrend_variants.py:504-511`). Draft: strategy gates rebalance in `on_bar()`, only emits Signal when `abs(new_weight - state.exposure) >= threshold` (`strategy.py:351-358`). If gate doesn't pass, no signal is emitted, engine does nothing. |
| **Rebalance comparison basis** | `MISMATCH` | Source: compares target weight vs **actual weight at bar open** (open price, actual portfolio units) (`vtrend_variants.py:506-508`). Draft: compares new weight vs **`state.exposure` at bar close** (close price, actual portfolio exposure) (`strategy.py:354`). Between bar close and next bar open, price can change, so close-time exposure and open-time weight differ. This means: (a) draft may emit a rebalance signal that source wouldn't (if close-to-open price move narrows the delta below threshold); (b) draft may NOT emit a signal that source would (if close-to-open price move widens the delta above threshold). |
| **Rebalance crossing_zero** | `SEMANTIC_MATCH` | Source execution engine has explicit `crossing_zero = (target_w <= 1e-12) != (current_w <= 1e-12)` check (`vtrend_variants.py:510`). Draft handles crossing-zero through separate entry/exit code paths: entry emits Signal(target_exposure=weight>0), exit emits Signal(target_exposure=0.0). Both allow trades that cross zero regardless of threshold. |
| **Signal timing** | `SEMANTIC_MATCH` | Source: `target_weight_signal[i]` set at bar i close → execution engine reads `target_weight_signal[i-1]` at bar i open (`vtrend_variants.py:504-505`). Draft: `on_bar()` called at bar close → Signal stored as pending → executed at next bar open (`v10/core/engine.py:170-175, 141-145`). Same semantic: signal at close(i) → execute at open(i+1). |
| **Execution vs strategy boundary** | `MISMATCH` | Source: strategy produces target_weight_signal array; execution engine handles rebalance gating, cost computation, cash constraints, trade recording. Clear separation. Draft: strategy handles rebalance gating internally; engine handles cost computation, cash constraints. Rebalance responsibility shifted from engine to strategy. |

### 3.6 Summary Counts

| Verdict | Count |
|---------|-------|
| EXACT_MATCH | 14 |
| SEMANTIC_MATCH | 9 |
| MISMATCH | 12 |
| NOT_IMPLEMENTED | 0 |
| UNVERIFIED | 0 |

---

## 4. Survey Report Audit

Cross-audit of `research_reports/34_vtrend_sm_survey.md` claims.

### 4.1 Accurate Claims

| Section | Claim | Status |
|---------|-------|--------|
| §1.1 | "run_vtrend_state_machine() is entirely self-contained within vtrend_variants.py" | **CORRECT** — verified, no imports from Latch/ subpackage |
| §1.1 | "VTREND-SM uses a simple binary active=True/False flag with per-bar regime evaluation" | **CORRECT** — source `vtrend_variants.py:674, 680` |
| §2.2 | Parameter defaults table | **CORRECT** — all 16 values match source `vtrend_variants.py:92-107` |
| §2.4 | Signal logic pseudocode | **CORRECT** — faithful representation of source `vtrend_variants.py:674-704` |
| §2.8 | "BARS_PER_YEAR_4H = 365.0 * 6.0 = 2190.0" for Latch | **CORRECT** |
| §3.1 | Structural differences table (VTREND E0 vs VTREND-SM) | **CORRECT** |
| §3.4 | "VTREND-SM is a fundamentally different algorithm" | **CORRECT** |
| §5.2 | "The strategy does NOT handle costs. The engine handles..." | **CORRECT** |
| §5.6 | Rolling window equivalence analysis | **CORRECT** — verified with concrete example |
| §5.7 | Realized vol window alignment analysis | **CORRECT** — verified numerically |
| §5.8 | Pre-existing vtrend registration inconsistency | **CORRECT** |

### 4.2 Claims Softened Beyond What Evidence Supports

| Section | Claim | Problem |
|---------|-------|---------|
| §5.1 | "The 0.07% difference (2191.5 vs 2190.0) affects Sharpe/Sortino computation but is **negligible** for practical purposes" | **SOFTENED**. The implementation draft uses `BARS_PER_YEAR_4H = 2191.5` while source uses `2190.0`. This is a **deviation from source**. The report dismisses it as "negligible" and "LOW risk, no action needed". The difference propagates through `sqrt(bars_per_year)` into every `_realized_vol()` value, which determines every position size. Should be stated plainly as: "Implementation uses 2191.5, source uses 2190.0. This is a deviation." |
| §5.1 | "The two constants serve different purposes: strategy uses 2191.5 for vol-targeting, metrics.py uses 2190.0 for Sharpe. Both are defensible." | **SOFTENED**. This frames a source deviation as an intentional design choice. The source uses 2190.0 for vol-targeting. The draft changed it to 2191.5. Whether the change is "defensible" is a separate question from whether it matches the source. |
| §5.3 | "The double-gating is redundant but harmless. Strategy signals that pass the 5% gate will always pass the 0.5% engine gate." | **INCOMPLETE**. This is true for the threshold magnitude, but misses the critical issue that the two gates use **different reference points** (close-price exposure vs open-price weight). The draft's rebalance gate operates at a different price point than the source's gate. |
| §6.2 | "16 parameters match VTrendStateMachineParams **exactly**" | **INACCURATE**. Field order differs (positions 7-9 swapped). `frozen` attribute differs. Should say "16 parameter names and defaults match, field order and frozen attribute differ." |
| §6.2 | "resolved() method mirrors Latch's auto-derivation logic" | **INCOMPLETE**. Auto-derivation formulas are identical, but validation was moved from `resolved()` to `__post_init__()`. Should note the validation timing difference. |
| §6.2 | "on_bar() logic follows the source algorithm **faithfully**" | **INACCURATE**. Three behavioral mismatches exist: (1) entry weight>0 guard not in source, (2) rebalance gating moved to strategy-side, (3) rebalance comparison uses close-price exposure instead of open-price weight. |

### 4.3 Claims Needing Wording Correction

| Section | Current wording | Corrected wording |
|---------|----------------|-------------------|
| §1.1 | "8 tests for VTREND-SM" | Should be "6 tests for VTREND-SM" — `TestVTrendStateMachine` has 6 tests (`test_vtrend_variants.py:41-168`). `TestVTrendP` (3 tests) and `TestValidation` (2 tests) are separate. |
| §5.5 | "NONE when taker data is available" | Should add: "When `use_vdo_filter=True` and taker data is missing: source raises ValueError, draft silently uses OHLC proxy. This is a behavioral MISMATCH in the non-default VDO-enabled path." |

### 4.4 Claims Based on Implementation Draft (Circular Evidence)

The following survey conclusions reference the implementation draft as evidence for correctness, which is circular since the draft is the untrusted artifact:

| Section | Claim | Issue |
|---------|-------|-------|
| §6.2 | Lists implementation status claims (config matches, resolved mirrors, on_bar follows faithfully) | All based on visual inspection of the draft, not verified against source. This audit reveals 12 mismatches. |
| §Appendix A | Symbol cross-reference table with specific line numbers in draft | Line numbers are accurate but the cross-reference implicitly treats the draft as correct. |

---

## 5. Mismatch Register

Full list of all mismatches found, ordered by severity (behavioral impact).

### 5.1 Behavioral Mismatches (affect signal output)

| # | Item | Source | Draft | Impact |
|---|------|--------|-------|--------|
| M1 | **BARS_PER_YEAR_4H** | `365.0 * 6.0 = 2190.0` (`vtrend_variants.py:43`) | `6.0 * 365.25 = 2191.5` (`strategy.py:39`) | Every `_realized_vol()` value is scaled by `sqrt(2191.5)` instead of `sqrt(2190.0)`. Factor: 46.8134/46.7974 = 1.000342. Every vol-targeted position size is 0.034% different from source. |
| M2 | **Entry weight>0 guard** | Enter unconditionally when conditions met, weight computed separately (may be 0.0) (`vtrend_variants.py:689-691, 700-701`) | Only enter if `weight > 0.0` (`strategy.py:331-332`) | When `min_weight > 0` and `target_vol/rv < min_weight`: source enters with weight=0 (stuck in LONG with no position), draft stays FLAT. Different state trajectories. Default `min_weight=0.0` makes this unreachable in practice. |
| M3 | **Rebalance gating location** | In execution engine `_execute_target_weights()`, target_weight set every active bar (`vtrend_variants.py:700-702, 504-511`) | In strategy `on_bar()`, only emits signal when gate passes (`strategy.py:351-358`) | Different architectural responsibility. Source engine sees fresh target every bar; draft engine only sees targets when strategy decides to emit. |
| M4 | **Rebalance comparison basis** | Compares target vs actual weight at **open price** (`vtrend_variants.py:506-508`) | Compares target vs `state.exposure` at **close price** (`strategy.py:354`) | Close-to-open price movement causes different rebalance decisions. Draft may trade when source wouldn't (if close delta > threshold but open delta < threshold), and vice versa. |
| M5 | **VDO OHLC proxy fallback** | No fallback — raises ValueError when VDO columns missing and `use_vdo_filter=True` (`vtrend_variants.py:241-244`) | Has OHLC proxy fallback: `(close-low)/(high-low)*2-1` (`strategy.py:141-145`) | When `use_vdo_filter=True` (non-default) without taker data: source errors, draft silently uses proxy. Different VDO values → different entry decisions. |
| M6 | **VDO NaN handling** | `bool(vdo > threshold)` returns False for NaN → entry blocked, bar processing continues (`vtrend_variants.py:684`) | `if not np.isfinite(vdo_val): return None` → skips remaining bar logic (`strategy.py:323-324`) | When FLAT and VDO is NaN: both block entry. But draft returns None immediately, skipping state recording. No practical impact in FLAT state. |

### 5.2 Structural Mismatches (no behavioral impact with default params)

| # | Item | Source | Draft | Impact |
|---|------|--------|-------|--------|
| M7 | **Config field ordering** | `target_vol`, `vol_lookback`, `slope_lookback` at positions 7-9 (`vtrend_variants.py:98-100`) | `slope_lookback`, `target_vol`, `vol_lookback` at positions 7-9 (`strategy.py:53-55`) | No behavioral impact — fields accessed by name. Affects `asdict()` key order. |
| M8 | **Config frozen attribute** | `@dataclass(frozen=True)` (`vtrend_variants.py:77`) | `@dataclass` (mutable) (`strategy.py:45`) | No behavioral impact on algorithm. Required for btc-spot-dev framework `setattr()` pattern. |
| M9 | **Validation timing** | `slope_lookback` validated in `resolved()` (`vtrend_variants.py:110-111`) | Validated in `__post_init__()` (`strategy.py:64-66`) | Different failure point: source fails at `resolved()` call; draft fails at construction. Same error for same invalid input, different timing. |
| M10 | **EMA input validation** | `if span <= 0: raise ValueError` (`vtrend_variants.py:272-273`) | No validation (`strategy.py:101-108`) | Auto-derivation ensures `fast_period >= 5`, so zero/negative span is unreachable in practice. But direct `_ema(arr, 0)` call would produce division-by-zero in draft vs ValueError in source. |
| M11 | **ATR prev_close at index 0** | `close.shift(1).fillna(close.iloc[0])` → `prev_close[0] = close[0]` (`vtrend_variants.py:283`) | `np.concatenate([[high[0]], close[:-1]])` → `prev_close[0] = high[0]` for one component, `low[0]` for other (`strategy.py:117-118`) | No impact on TR[0]: `max(H-L, |H-close[0]|, |L-close[0]|) = H-L` always, and `max(H-L, |H-high[0]|=0, |L-low[0]|=0) = H-L` always. Intermediate values differ but TR[0] is identical. |
| M12 | **Execution vs strategy boundary** | Strategy produces weight array; engine gates rebalance | Strategy gates rebalance; engine executes | Architectural difference. Related to M3/M4 above. |

---

## 6. Readiness Verdict for Prompt 4

### 6.1 Is the draft usable as a base for Prompt 4?

**YES, with mandatory fixes.** The draft is structurally sound and captures the core algorithm correctly. 14 items are EXACT_MATCH, 9 are SEMANTIC_MATCH. The 12 mismatches break down as:

- **1 mandatory fix** (M1): BARS_PER_YEAR_4H must be changed from `2191.5` to `2190.0` to match source. This affects every position size.
- **1 recommended fix** (M2): Remove the `weight > 0.0` guard on entry to match source behavior. While the default `min_weight=0.0` makes this unreachable, it changes the state machine contract.
- **2 architectural decisions** (M3, M4): Rebalance gating moved to strategy-side with close-price comparison instead of source's execution-engine-side with open-price comparison. This is the most consequential deviation. Two options:
  - **Option A**: Accept as-is (btc-spot-dev convention — strategy owns its gating logic).
  - **Option B**: Have strategy emit target_weight on every active bar and let engine's `_EXPO_THRESHOLD` handle gating. Requires changing `_EXPO_THRESHOLD` from 0.005 to 0.05 or adding strategy-specific threshold support to engine.
  - Recommendation: Option A is pragmatic. The close-vs-open price delta effect is second-order for 4H bars (typical 4H close-to-open difference << 5% rebalance threshold).
- **2 conditional mismatches** (M5, M6): Only affect non-default VDO-enabled path. Acceptable if VDO remains disabled by default.
- **6 structural mismatches** (M7-M12): No behavioral impact with default parameters. Acceptable.

### 6.2 Mandatory Fixes Before Prompt 4

| # | Fix | File | Line | Change |
|---|-----|------|------|--------|
| F1 | Change `BARS_PER_YEAR_4H` from `6.0 * 365.25` to `365.0 * 6.0` | `strategies/vtrend_sm/strategy.py` | 39 | `BARS_PER_YEAR_4H: float = 365.0 * 6.0` |
| F2 | Remove `weight > 0.0` guard on entry | `strategies/vtrend_sm/strategy.py` | 331-335 | Enter when conditions met regardless of weight value (match source) |

### 6.3 Items for Prompt 4 Integration (Mechanical)

Assuming fixes F1-F2 are applied, the remaining work for Prompt 4 is:

1. Register `vtrend_sm` in 4 files (config.py, candidates.py, strategy_factory.py, cli/backtest.py)
2. Write `tests/test_vtrend_sm.py` covering: config defaults, indicator correctness, entry/exit logic, rebalance threshold, VDO filter, warmup
3. Integration smoke test with BacktestEngine

### 6.4 Acknowledged Deviations (Accepted)

The following deviations from source are accepted as btc-spot-dev adaptations:

- M3/M4: Rebalance gating in strategy (close-price basis) instead of execution engine (open-price basis)
- M5: OHLC proxy fallback in `_vdo()` (inherited from VTREND E0 codebase convention)
- M7: Config field ordering (cosmetic)
- M8: Mutable dataclass (framework requirement)
- M9: Validation in `__post_init__` (Python convention for dataclass validation)
- M10: No EMA validation (unreachable via config)
- M11: ATR index-0 intermediate values (no impact on output)
- M12: Boundary between strategy and engine (architectural choice)

---

## 7. Repo State Snapshot

```
$ cd /var/www/trading-bots/btc-spot-dev && git status --short
fatal: not a git repository (or any of the parent directories): .git
```

**Git is unavailable** — btc-spot-dev is not a git repository.

**Source code changes in this prompt: NONE.** Only this report file was created:
- Created: `research_reports/34b_vtrend_sm_preintegration_audit.md`
