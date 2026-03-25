# Step 3: Overlay A Specification — Post-Emergency-DD Cooldown

**Date:** 2026-02-24
**Scope:** V8ApexStrategy only, BTCUSDT, H4 timeframe
**Constraint:** Zero changes to entry alpha logic (VDO/HMA/accel/RSI unchanged)

---

## 1. Problem Statement

Step 2 showed that 58% of emergency_dd exits are followed by re-entry within 12 H4 bars (2 days).
These quick re-entries have negative median PnL at every K threshold, 43-53% end in another
emergency_dd, and 9 cascade chains destroy $77,093 (82% of strategy PnL).

The existing `exit_cooldown_bars=3` (12 hours) is the only brake. It is insufficient because
the D1 regime remains RISK_ON and VDO remains positive during BULL corrections — all entry
gates pass, and the strategy re-enters the same declining market.

**Overlay A is a risk wrapper, not an alpha change.** It extends the cooldown specifically after
emergency_dd exits, giving the market time to stabilize before re-entry is permitted.

---

## 2. State Machine

### 2.1 States

```
┌─────────────┐     exit_reason == "emergency_dd"     ┌────────────────────────┐
│   NORMAL    │ ──────────────────────────────────────▶│  COOLDOWN_ACTIVE       │
│             │                                        │  bars_remaining = K    │
│ entry gates │◀───────────────────────────────────────│  bars_remaining -= 1   │
│ as baseline │       bars_remaining == 0              │  per on_bar() call     │
└─────────────┘                                        └────────────────────────┘
```

Two states:
- **NORMAL** — all entry/add gates operate as baseline V8Apex
- **COOLDOWN_ACTIVE** — all entries and adds are blocked; exits and reductions are unaffected

### 2.2 Transitions

| From | To | Trigger | Action |
|------|----|---------|--------|
| NORMAL | COOLDOWN_ACTIVE | `just_closed` AND last exit reason was `emergency_dd` | Set `bars_remaining = cooldown_after_emergency_dd_bars` |
| COOLDOWN_ACTIVE | COOLDOWN_ACTIVE | `bars_remaining > 0` | Decrement `bars_remaining -= 1` |
| COOLDOWN_ACTIVE | NORMAL | `bars_remaining == 0` | Clear state |

### 2.3 Effect When COOLDOWN_ACTIVE

| Action | Blocked? | Reason |
|--------|----------|--------|
| New entry from flat | **YES** | Risk wrapper prevents cascade |
| Add/pyramid to existing position | **YES** | Prevents size accumulation during correction |
| Exit (any reason) | NO | Exits must never be blocked by entry overlays |
| Exit cooldown (existing 3-bar) | NO | Operates independently |
| Indicator updates (VDO, HMA, etc.) | NO | All indicators continue updating |

### 2.4 Precedence

The overlay A gate is checked **before** all other entry gates, immediately inside `_check_entry`:

```
_check_entry(state, idx, mid, regime):
    ┌─ Gate 0: Overlay A cooldown          ← NEW (if cooldown_active: return None)
    ├─ Gate 1: Regime (RISK_OFF → block)
    ├─ Gate 2a: entry_cooldown_bars
    ├─ Gate 2b: exit_cooldown_bars
    ├─ Gate 3: VDO threshold
    ├─ Gate 4: Trend confirmation (HMA/RSI)
    ├─ Gate 5: Exposure gap
    └─ Gate 6: Size minimum
```

Why Gate 0 (before regime): Even if the regime flips to RISK_OFF during the cooldown, the overlay
counter continues decrementing. When cooldown expires, the regime gate takes over. This avoids
counter confusion when regime and cooldown interact.

---

## 3. Parameter

| Parameter | Type | Default | Range | Unit |
|-----------|------|---------|-------|------|
| `cooldown_after_emergency_dd_bars` | int | **12** | [0, 72] | H4 bars |

### 3.1 Default Justification (K=12)

| Criterion | K=6 (1d) | **K=12 (2d)** | K=18 (3d) |
|-----------|----------|---------------|-----------|
| Post-ED re-entries blocked | 20% | **60%** | 80% |
| Median PnL of blocked | -$630 | **-$742** | -$122 |
| Re-emergency rate of blocked | 43% | **48%** | 39% |
| Matches median reentry latency | No | **Yes** (12 = median) | No |

K=12 blocks 60% of cascade re-entries, matches the empirical median re-entry latency,
and avoids over-blocking (K=18 starts blocking trades with positive median PnL in the
"passed" group).

### 3.2 Candidate Sweep

For backtesting, sweep K ∈ {0, 6, 12, 18, 24, 36}:
- K=0: baseline (overlay disabled)
- K=6: minimal (1 day)
- K=12: default (2 days)
- K=18: moderate (3 days)
- K=24: aggressive (4 days)
- K=36: very aggressive (6 days)

### 3.3 Timeframe

All bar counts refer to **H4 bars** (4 hours each):

| Bars | Hours | Days |
|------|-------|------|
| 6 | 24 | 1.0 |
| 12 | 48 | 2.0 |
| 18 | 72 | 3.0 |
| 24 | 96 | 4.0 |
| 36 | 144 | 6.0 |

If the engine is ever ported to a different timeframe, the parameter value must be scaled
proportionally (e.g., for 1H bars: multiply by 4).

---

## 4. Scope

| Dimension | Scope | Rationale |
|-----------|-------|-----------|
| Asset | Single (BTCUSDT) | V10 is a single-asset strategy |
| Strategy | V8ApexStrategy instance-level | Cooldown state lives on the strategy instance |
| Multi-instance | Independent | If multiple V8Apex instances run, each has its own counter |

No cross-symbol or cross-strategy coordination is needed.

---

## 5. Implementation Plan

### 5.1 Config Change (`v8_apex.py`, V8ApexConfig)

Add one field:

```python
# Overlay A: post-emergency-DD cooldown
cooldown_after_emergency_dd_bars: int = 12
```

### 5.2 State Variables (`v8_apex.py`, V8ApexStrategy.__init__)

Add two instance variables:

```python
self._emergency_dd_cooldown_remaining: int = 0
self._last_exit_reason: str = ""
```

### 5.3 on_bar Modification (`v8_apex.py`, on_bar)

After `just_closed` detection (line ~285):

```python
if just_closed:
    self._last_exit_idx = idx
    # ... existing reset logic ...

    # Overlay A: activate cooldown if last exit was emergency_dd
    if self._last_exit_reason == "emergency_dd":
        self._emergency_dd_cooldown_remaining = c.cooldown_after_emergency_dd_bars
```

Before calling `_check_entry` (or as first gate inside `_check_entry`):

```python
# Overlay A: decrement and check cooldown
if self._emergency_dd_cooldown_remaining > 0:
    self._emergency_dd_cooldown_remaining -= 1
    # Note: decrement happens every bar (in-position or flat)
```

### 5.4 _check_entry Gate 0

```python
def _check_entry(self, state, idx, mid, regime):
    # Gate 0: Overlay A post-emergency-DD cooldown
    if self._emergency_dd_cooldown_remaining > 0:
        return None

    # Gate 1: Regime (existing)
    ...
```

### 5.5 Exit Reason Tracking

The strategy doesn't currently track exit reason. The Signal returned by `_check_exit` contains
the reason. We need to capture it.

Option A (minimal): Save the reason from the Signal before returning it:

```python
if in_pos:
    sig = self._check_exit(state, idx, mid, regime)
    if sig is not None:
        self._last_exit_reason = sig.reason  # NEW
        return sig
```

This captures the reason at signal time (bar close). The actual exit fill happens at next bar open,
and `just_closed` fires on the bar after that. This 1-bar delay is acceptable because the cooldown
activates when `just_closed` is detected, which is the correct timing.

Option B: Reset `_last_exit_reason = ""` on `just_opened` to avoid stale state.

**Recommended: Option A + B** (save on exit signal, clear on open).

---

## 6. Edge Cases

### 6.1 Emergency_dd during warmup

If an emergency_dd exit occurs during the warmup period, the cooldown counter activates and
decrements during warmup bars. By the time reporting starts, the counter may already be zero.
**No special handling needed** — the counter is just an integer that decrements per bar.

### 6.2 cooldown_after_emergency_dd_bars = 0

Overlay A is disabled. Behavior identical to baseline V10. The Gate 0 check
(`if self._emergency_dd_cooldown_remaining > 0`) passes immediately because
the counter is never set to a positive value (0 → no activation).

Wait — the activation sets `_emergency_dd_cooldown_remaining = c.cooldown_after_emergency_dd_bars`.
If that's 0, the counter is set to 0, and Gate 0 never blocks. **Correct: K=0 disables the overlay.**

### 6.3 Two emergency_dd exits in sequence

If trade A exits via emergency_dd, cooldown activates with K bars. If cooldown expires, a new
trade B enters and also hits emergency_dd, the cooldown resets to K bars. Each emergency_dd
independently triggers a fresh cooldown. **No stacking or accumulation.**

### 6.4 Emergency_dd followed by regime flip to RISK_OFF

The cooldown counter decrements every bar regardless of regime. If regime is RISK_OFF during
the cooldown, both Gate 0 (overlay) and Gate 1 (regime) would block. When cooldown expires,
Gate 1 still blocks. When regime flips back to RISK_ON, Gate 0 is already clear.
**No interaction issue.**

### 6.5 Cooldown counter and _last_exit_idx interaction

The existing `exit_cooldown_bars=3` uses `idx - self._last_exit_idx < 3`. Overlay A uses a
separate counter `_emergency_dd_cooldown_remaining`. They are independent:

- `exit_cooldown_bars=3` blocks for 3 bars after ANY exit
- `cooldown_after_emergency_dd_bars=12` blocks for 12 bars after emergency_dd only

Since Overlay A (Gate 0) is checked before the existing cooldown (Gate 2b), and K > 3 always,
the effective cooldown after emergency_dd is always K (not K+3). The existing 3-bar cooldown
is subsumed by the longer overlay cooldown.

### 6.6 Position still open at counter > 0

Impossible in normal flow: the cooldown only activates on `just_closed` (flat). The counter
decrements every bar. If somehow a position opens during cooldown (shouldn't happen since
entries are blocked), the counter still decrements and exits are unaffected.

### 6.7 Counter decrement: every bar vs only when flat

The counter decrements on **every bar** (in `on_bar`, before the in_pos/flat branch). This means:
- If the strategy somehow opens a position during cooldown (impossible per Gate 0), the counter
  still counts down
- The cooldown is strictly time-based, not conditional on market state

This is intentional: the cooldown represents "wait for N bars of market data to pass," regardless
of position state.

---

## 7. Logging

When Gate 0 blocks an entry, the InstrumentedV8Apex (from step 1) should log:

```
event_type = "entry_blocked"
reason = "cooldown_after_emergency_dd"
```

This is already handled by step 1's `_diagnose_block` method — add a new check before the
existing gate checks:

```python
def _diagnose_block(self, state, idx, mid, regime):
    if self._emergency_dd_cooldown_remaining > 0:
        return "cooldown_after_emergency_dd"
    # ... existing gate checks ...
```

The event log row will contain: `ts`, `bar_index`, `price`, `nav`, `exposure`, `regime_label`,
`regime_d1_analytical` — sufficient for post-hoc analysis.

---

## 8. Verification Plan

After implementation, re-run step 1 + step 2 with Overlay A enabled (K=12):

1. **Trade count should decrease** — some cascade entries are blocked
2. **emergency_dd count should decrease** — fewer cascade → fewer re-stop-outs
3. **Cascade rate at K≤6 should be 0%** — all quick re-entries blocked
4. **New event_type `cooldown_after_emergency_dd` should appear** in events CSV
5. **Total PnL should improve** — removing negative-expectancy cascade trades
6. **Baseline entries unaffected** — entries after trailing_stop or fixed_stop exits are not blocked
