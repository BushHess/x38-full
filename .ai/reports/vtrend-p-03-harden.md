# VTREND-P Hardening Report

**Date**: 2026-03-05
**Prerequisite**: vtrend-p-02-implementation.md (COMPLETE)

---

## 1. STATUS: READY_FOR_LATCH_DISCOVERY

No blocking issues found. All integration points verified, all sensitive paths
stressed, full regression passes (768/768, 0 failures).

---

## 2. Executive Summary

Line-by-line re-comparison of source `run_vtrend_p()` (Latch lines 735–848) vs
target `strategies/vtrend_p/strategy.py` confirms behavioral parity. All 6
indicator functions verified numerically against pandas reference implementations.
All 5 integration touchpoints match the SM reference pattern exactly. Two
hardening tests added (re-entry cycle, exit priority). No code changes to the
strategy implementation were required.

---

## 3. Additional Fixes Made in This Hardening Phase

| # | Fix | File | Rationale |
|---|---|---|---|
| 1 | Added `TestReentryAfterExit` (H1) | tests/test_vtrend_p.py | Tests entry→exit→re-entry cycle (no stuck state) |
| 2 | Added `TestExitBeforeRebalance` (H2) | tests/test_vtrend_p.py | Verifies exit fires with correct reason when floor breached |

**No behavioral changes to strategy code.** The two additions are test-only.

---

## 4. Parity Check Results: Source VTREND-P vs Target VTREND-P

### Config Parity (10/10 fields)

| Field | Source Default | Target Default | Match |
|---|---|---|---|
| slow_period | 120 | 120 | ✓ |
| atr_period | 14 | 14 | ✓ |
| atr_mult | 1.5 | 1.5 | ✓ |
| target_vol | 0.12 | 0.12 | ✓ |
| entry_n | None | None | ✓ |
| exit_n | None | None | ✓ |
| vol_lookback | None | None | ✓ |
| slope_lookback | 6 | 6 | ✓ |
| min_rebalance_weight_delta | 0.05 | 0.05 | ✓ |
| min_weight | 0.0 | 0.0 | ✓ |

### Auto-Derivation Parity

| Expression | Source | Target | Match |
|---|---|---|---|
| entry_n auto | max(24, slow_period // 2) | max(24, self.slow_period // 2) | ✓ |
| exit_n auto | max(12, slow_period // 4) | max(12, self.slow_period // 4) | ✓ |
| vol_lookback auto | slow_period | self.slow_period | ✓ |

### Entry Logic Parity

| Condition | Source (line 809–816) | Target (line 262–274) | Match |
|---|---|---|---|
| regime_ok | `close > ema_slow` (strict >) | `close_val > ema_s` | ✓ |
| slope_ok | `ema_slow > ema_slow_slope_ref` | `ema_s > ema_s_ref` | ✓ |
| breakout_ok | `close > hh_entry` | `close_val > hh` | ✓ |
| sizing | `_clip_weight(target_vol / max(rv, EPS), min_weight)` | identical | ✓ |

### Exit Logic Parity

| Condition | Source (line 812, 818–821) | Target (line 277–282) | Match |
|---|---|---|---|
| exit_floor | `max(ll_exit, ema_slow - atr_mult * atr)` | `max(ll, ema_s - atr_mult * atr_val)` | ✓ |
| floor_break | `close < exit_floor` (strict <) | `close_val < exit_floor` | ✓ |

### Indicator Parity (all verified numerically vs pandas)

| Indicator | Source Function | Target Function | Numerical Match |
|---|---|---|---|
| EMA | `ewm(span, adjust=False).mean()` | `_ema()` | exact (rtol=1e-12) |
| ATR (Wilder) | `atr_wilder()` | `_atr()` | exact* |
| Rolling High Shifted | `high.shift(1).rolling().max()` | `_rolling_high_shifted()` | exact (equal_nan) |
| Rolling Low Shifted | `low.shift(1).rolling().min()` | `_rolling_low_shifted()` | exact (equal_nan) |
| Realized Vol | `log_returns.rolling().std(ddof=0) * sqrt(bpy)` | `_realized_vol()` | exact (rtol=1e-10) |
| clip_weight | `_clip_weight()` | `_clip_weight()` | identical code |

*ATR bar-0 note: Target uses `high[0]`/`low[0]` as prev_close fallback for bar 0,
source uses `close[0]`. Difference is zero when `high-low` dominates (always true for
real BTC data where close ∈ [low, high]). Shared with SM. Non-blocking.

### Known Non-Blocking Divergences

| # | Divergence | Impact | Shared with SM |
|---|---|---|---|
| D1 | Weight > 0 guard on entry | Target prevents entering with weight=0 (source would set active=True with weight=0). More correct. | Yes |
| D2 | ATR bar-0 prev_close | high[0] vs close[0] — washes out by bar 14 via Wilder smoothing. Zero effect on real data. | Yes |
| D3 | Rebalance epsilon | Target uses `- 1e-12` tolerance in threshold comparison. Defensive against FP rounding. | Yes |

All three divergences are shared conventions with SM, not P-specific issues.

---

## 5. Sensitive-Path Audit Results

### 5a. Warmup and Initial-State Behavior

| Check | Result |
|---|---|
| `_active = False` at init | ✓ Verified |
| `_warmup_end` computed from all 6 indicator arrays | ✓ Verified |
| No signals during warmup (0..warmup_end-1) | ✓ Tested (T10) |
| Empty bars → on_init returns early, on_bar returns None | ✓ Tested (Invariants) |
| on_init not called → `self._ema_slow is None` guard | ✓ Verified (line 242) |
| Default warmup_end=120 with default params | ✓ Verified (rv is bottleneck) |

### 5b. Bar Indexing and Look-Ahead Safety

| Indicator | Access Pattern | Look-Ahead? |
|---|---|---|
| _ema | Causal (recursive from bar 0) | No |
| _atr | Causal (Wilder from bar 0) | No |
| _rolling_high_shifted | `high[i-lookback:i]` excludes current bar | No |
| _rolling_low_shifted | `low[i-lookback:i]` excludes current bar | No |
| _realized_vol | `lr[i-lookback+1:i+1]` includes current bar's log return (available at bar close) | No |
| ema_slow_slope_ref | `ema_slow[:-sl]` shifted right by `sl` bars | No |

All indicators are causal. No look-ahead.

### 5c. Stop-Loss / Exit Ordering

- Exit check runs BEFORE rebalance check in the LONG branch (lines 276–292)
- If `close < exit_floor`, Signal(target_exposure=0.0, reason="vtrend_p_exit") is returned immediately
- Rebalance code is unreachable on that bar
- Verified by H2 test: exit fires with reason "vtrend_p_exit", never "vtrend_p_rebalance"

### 5d. Flip / Re-Entry Behavior

- Entry and exit are in mutually exclusive branches (`if not self._active` vs `else`)
- No same-bar entry+exit possible by construction
- After exit (`self._active = False`), `return Signal(...)` exits on_bar immediately
- Next bar: flat branch is evaluated, re-entry possible if conditions met
- Verified by H1 test: entry → exit → re-entry cycle works correctly

### 5e. NaN / Missing-Data / Zero-Denominator Handling

| Scenario | Handling | Verified |
|---|---|---|
| Any indicator NaN at bar i | Explicit `np.isfinite()` check → return None | ✓ (line 253–258) |
| rv = 0 (constant price) | `max(rv, EPS)` → weight = target_vol / 1e-12 → clipped to 1.0 | ✓ stress test |
| close = 0 in data | `_realized_vol` uses `where=close[:-1] > 0.0` → NaN log return → NaN rv → skipped | ✓ stress test |
| NaN/inf weight | `_clip_weight` returns 0.0 | ✓ (T8: 10 tests) |
| `max(NaN, X)` in exit_floor | Returns NaN → caught by NaN guard before reaching exit check (target only computes when LONG, all indicators already verified finite) | ✓ verified |

---

## 6. Parity Check Results: Target VTREND-P vs Target VTrend-SM Integration Pattern

### Module Structure

| Item | SM | P | Match |
|---|---|---|---|
| `__init__.py` exports | STRATEGY_ID, Config, Strategy | STRATEGY_ID, Config, Strategy | ✓ |
| `__all__` list | 3 items | 3 items | ✓ |
| `strategy.py` structure | Config → indicators → Strategy class | Config → indicators → Strategy class | ✓ |
| STRATEGY_ID constant | "vtrend_sm" | "vtrend_p" | ✓ |
| BARS_PER_YEAR_4H | 365.0 * 6.0 = 2190.0 | 365.0 * 6.0 = 2190.0 | ✓ |
| EPS constant | 1e-12 | 1e-12 | ✓ |

### Integration Touchpoints (5/5)

| Location | SM | P | Match |
|---|---|---|---|
| `v10/core/config.py` — import | ✓ VTrendSMConfig | ✓ VTrendPConfig | ✓ |
| `v10/core/config.py` — _FIELDS | ✓ _VTREND_SM_FIELDS | ✓ _VTREND_P_FIELDS | ✓ |
| `v10/core/config.py` — _KNOWN_STRATEGIES | ✓ "vtrend_sm" | ✓ "vtrend_p" | ✓ |
| `v10/core/config.py` — strategy_fields_by_name | ✓ | ✓ | ✓ |
| `v10/core/config.py` — validate_config() | ✓ | ✓ | ✓ |
| `v10/cli/backtest.py` — STRATEGY_REGISTRY | ✓ | ✓ | ✓ |
| `validation/strategy_factory.py` — STRATEGY_REGISTRY | ✓ (Strategy, Config) | ✓ (Strategy, Config) | ✓ |
| `v10/research/candidates.py` — _FIELDS | ✓ | ✓ | ✓ |
| `v10/research/candidates.py` — load_candidates() | ✓ | ✓ | ✓ |
| `v10/research/candidates.py` — build_strategy() | ✓ | ✓ | ✓ |

### Convention Parity

| Convention | SM | P | Match |
|---|---|---|---|
| Config stored as `self._config` (private) | ✓ | ✓ | ✓ |
| `resolved()` method with auto-derivation | ✓ | ✓ | ✓ |
| `__post_init__` for validation | ✓ (slope_lookback) | ✓ (slope_lookback) | ✓ |
| Indicator duplication (frozen artifact) | ✓ | ✓ | ✓ |
| `_compute_warmup()` all-finite check | ✓ | ✓ | ✓ |
| `on_after_fill` is no-op | ✓ | ✓ | ✓ |
| Signal reasons: `{strategy_id}_{action}` | ✓ | ✓ | ✓ |
| ConfigProxy resolved() allowlist | ✓ | ✓ | ✓ |
| YAML config in `configs/{name}/` | ✓ | ✓ | ✓ |

---

## 7. Regression and Validation Results

### Unit Tests

```
python -m pytest — 768 passed, 39 warnings in 82.82s
```

| Suite | Count | Status |
|---|---|---|
| Baseline (pre-existing) | 715 | PASS |
| VTREND-P (Prompt 2) | 51 | PASS |
| VTREND-P hardening (H1, H2) | 2 | PASS |
| **Total** | **768** | **PASS** |

39 warnings are pre-existing (v8/v11 divide-by-zero in RSI computation).

### VTREND-SM Regression

SM tests are included in the 768 total. All 56 SM tests pass. No SM regressions
from the P integration.

### Validation Pipeline (from Prompt 2, unchanged)

| Check | Status |
|---|---|
| lookahead | PASS |
| data_integrity | PASS |
| invariants | PASS |
| config_unused_fields | PASS |
| churn_metrics | PASS |
| cost_sweep | PASS |

No re-run needed — no strategy code was changed in this hardening phase.

---

## 8. Remaining Non-Blocking Warnings

| # | Warning | Severity | Notes |
|---|---|---|---|
| W1 | ATR bar-0 fallback uses high[0]/low[0] vs source close[0] | Info | Shared with SM. Zero effect on real data. |
| W2 | Weight > 0 guard on entry is stricter than source | Info | Prevents entering with 0 weight. More correct than source. |
| W3 | BARS_PER_YEAR_4H = 2190.0 (matches source 365.0 * 6.0) vs btc-spot-dev convention 365.25 * 6.0 = 2191.5 | Info | Deliberate parity with source. < 0.07% difference. |

None require action.

---

## 9. Handoff Notes for Prompt 4

1. **VTREND-P is fully hardened.** Strategy code, config, tests, and all 5 integration
   touchpoints are verified. 768/768 tests pass.

2. **No behavioral changes** were made to the strategy implementation in this
   hardening phase. Only 2 test additions (H1: re-entry cycle, H2: exit priority).

3. **Parity status**: Target matches source with 3 non-blocking divergences (D1–D3),
   all shared with SM and all deliberate.

4. **Ready for Latch discovery.** The btc-spot-dev integration of VTREND-P is
   complete and can be used as a reference for any Latch-side work.

5. **Files touched in this phase**: `tests/test_vtrend_p.py` only (2 test classes added).
