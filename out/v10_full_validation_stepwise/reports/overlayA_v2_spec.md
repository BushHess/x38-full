# OverlayA v2: Escalating Cooldown — Specification

**Date:** 2026-02-24
**Status:** Implemented, pending validation
**Config:** `v10/configs/v10_overlayA_v2_escalating.yaml`

---

## 1. Motivation

C7 blocked winners diagnosis (K=12 flat cooldown) found:

| Group | Count | Exit via trailing_stop | Exit via emergency_dd | Total PnL |
|:------|------:|-----------------------:|----------------------:|----------:|
| Winners | 5 | 5 (100%) | 0 (0%) | $+38,709 |
| Losers | 10 | 2 (20%) | 8 (80%) | $-26,600 |

The flat cooldown treats all emergency_dd exits equally. It cannot distinguish:
- **Isolated ED exits** (single ED → market recovers) — blocking is costly
- **Cascade ED exits** (2+ consecutive EDs in a drawdown episode) — blocking is beneficial

---

## 2. State Machine

```
         ┌──────────────┐
         │   NORMAL     │  cascade_ed_count = 0
         │ (no cooldown)│
         └──────┬───────┘
                │ emergency_dd exit
                │ count → 1
                ▼
     ┌─────────────────────┐
     │  SHORT COOLDOWN     │  remaining = short_cooldown_bars (3)
     │  count = 1          │
     └─────┬─────────┬─────┘
           │         │
    lookback│         │ another ED within lookback_bars (24)
    expires │         │ count → 2 ≥ cascade_trigger_count
    no ED   │         ▼
           │  ┌─────────────────────┐
           │  │  LONG COOLDOWN      │  remaining = long_cooldown_bars (12)
           │  │  count → 0 (reset)  │
           │  └──────────┬──────────┘
           │             │ expires
           ▼             ▼
         ┌──────────────┐
         │   NORMAL     │  back to start
         └──────────────┘
```

### Transitions

| From | Event | Condition | Action | To |
|:-----|:------|:----------|:-------|:---|
| NORMAL | ED exit | — | count=1, record bar_idx, set short cooldown | SHORT_COOLDOWN |
| SHORT_COOLDOWN | ED exit | within lookback | count+=1; if count≥trigger → long cooldown, reset count | LONG_COOLDOWN |
| SHORT_COOLDOWN | bar tick | lookback expired, no ED | reset count=0 | NORMAL |
| SHORT_COOLDOWN | bar tick | cooldown remaining > 0 | decrement remaining | SHORT_COOLDOWN |
| LONG_COOLDOWN | bar tick | cooldown remaining > 0 | decrement remaining | LONG_COOLDOWN |
| LONG_COOLDOWN | bar tick | remaining = 0 | — | NORMAL |

---

## 3. Parameters

| Parameter | Type | Default | Description |
|:----------|:-----|--------:|:------------|
| `escalating_cooldown` | bool | False | Enable v2 (True) or use v1 flat cooldown (False) |
| `short_cooldown_bars` | int | 3 | H4 bars of cooldown after isolated ED exit (12h) |
| `long_cooldown_bars` | int | 12 | H4 bars of cooldown after cascade detected (48h) |
| `escalating_lookback_bars` | int | 24 | Window (H4 bars) to count consecutive ED exits (96h) |
| `cascade_trigger_count` | int | 2 | Number of ED exits within lookback to trigger long cooldown |

### Backward Compatibility

When `escalating_cooldown = False` (default), the original v1 behavior is unchanged:
- `cooldown_after_emergency_dd_bars` controls the flat cooldown
- All v2 state variables exist but are never activated

---

## 4. State Variables

| Variable | Type | Init | Description |
|:---------|:-----|:-----|:------------|
| `_cascade_ed_count` | int | 0 | ED exits counted in current lookback window |
| `_last_emergency_dd_bar_idx` | int | -1 | Bar index of most recent ED exit (just_closed bar) |
| `_active_cooldown_type` | str | "" | `"short_cooldown"` or `"long_cooldown"` (for logging) |
| `_emergency_dd_cooldown_remaining` | int | 0 | Shared with v1 — bars remaining in active cooldown |

---

## 5. Logging

When `escalating_cooldown = True`, `InstrumentedV8Apex._diagnose_block()` returns:

| Cooldown State | `reason` field |
|:---------------|:---------------|
| Short cooldown active | `"short_cooldown"` |
| Long cooldown active | `"long_cooldown"` |
| V1 cooldown active | `"cooldown_after_emergency_dd"` |

---

## 6. Edge Cases

### Edge 1: Isolated ED → short cooldown → recovery trade allowed
```
Bar 100: ED exit #1 → count=1, short_cooldown=3
Bar 101-103: cooldown active (entries blocked)
Bar 104: cooldown expired, count still=1
Bar 128+: lookback expires (100+24=124), count resets to 0
```
Recovery trades entering after bar 103 are allowed.

### Edge 2: Two EDs within lookback → long cooldown
```
Bar 100: ED exit #1 → count=1, short_cooldown=3
Bar 103: short cooldown expires
Bar 110: new trade enters
Bar 115: ED exit #2 (115-100=15 ≤ 24) → count=2 ≥ trigger → long_cooldown=12, count→0
Bar 116-127: long cooldown active
Bar 128: cooldown expires, back to NORMAL
```

### Edge 3: Lookback expires between EDs → treated as new isolated
```
Bar 100: ED exit #1 → count=1
Bar 130: ED exit #2 (130-100=30 > 24) → count=1 (reset, new window)
```
Second ED gets short cooldown, not long.

### Edge 4: Cascade trigger resets counter
```
Bar 100: ED #1 → count=1
Bar 115: ED #2 → count=2 → long cooldown, count→0
Bar 140: ED #3 → count=1 (fresh start after reset)
```
Each cascade trigger starts a new counting window.

### Edge 5: cascade_trigger_count = 3
```
Bar 100: ED #1 → count=1, short cooldown
Bar 110: ED #2 → count=2, short cooldown (still < 3)
Bar 120: ED #3 → count=3 ≥ 3 → long cooldown, count→0
```

### Edge 6: ED exit while in long cooldown (theoretical)
Not possible — long cooldown blocks re-entry, so no position can exist during long cooldown. The counter is already reset to 0 after cascade trigger.

---

## 7. Code Diff Summary

### `v10/strategies/v8_apex.py`

- **V8ApexConfig**: +5 fields (`escalating_cooldown`, `short_cooldown_bars`, `long_cooldown_bars`, `escalating_lookback_bars`, `cascade_trigger_count`)
- **V8ApexStrategy.__init__**: +3 state vars (`_cascade_ed_count`, `_last_emergency_dd_bar_idx`, `_active_cooldown_type`)
- **V8ApexStrategy.on_bar**: `just_closed` block branched on `escalating_cooldown`; lookback reset added after decrement
- **_check_entry**: unchanged (still checks `_emergency_dd_cooldown_remaining > 0`)

### `out_v10_fix_loop/step1_export.py`

- **InstrumentedV8Apex._diagnose_block**: Gate 0 returns `"short_cooldown"` or `"long_cooldown"` when v2 active

---

## 8. Deliverables

| Artifact | Path |
|----------|------|
| Config | `v10/configs/v10_overlayA_v2_escalating.yaml` |
| This spec | `out_v10_full_validation_stepwise/reports/overlayA_v2_spec.md` |
| Unit tests | `v10/tests/test_overlayA_v2_escalating.py` |
| Strategy code | `v10/strategies/v8_apex.py` (modified) |
| Instrumented logging | `out_v10_fix_loop/step1_export.py` (modified) |
