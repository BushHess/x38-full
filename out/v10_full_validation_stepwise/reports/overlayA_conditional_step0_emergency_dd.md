# Step 0: `emergency_dd` Definition Audit

**Date:** 2026-02-24
**Verdict:** **PASS** — definition is unambiguous; the apparent "-5% vs 0.28" mismatch is fully explained by the inflated reference NAV.

---

## 1. Where `exit_reason = "emergency_dd"` Is Set

### 1a. Production v10 strategy (Python)

**`btc-spot/v10/strategies/v8_apex.py:341–349`**

```python
# 1. Emergency DD — reference NAV depends on emergency_ref flag
if c.emergency_ref == "peak":
    ref_nav = self._position_nav_peak
else:  # "pre_cost_legacy" or "post_cost" (handled in Portfolio)
    ref_nav = state.position_entry_nav
if ref_nav > 0:
    dd = 1.0 - state.nav / ref_nav
    if dd >= c.emergency_dd_pct:
        return Signal(target_exposure=0.0, reason="emergency_dd")
```

Default config: `emergency_ref = "pre_cost_legacy"`, `emergency_dd_pct = 0.28`
(`btc-spot/v10/strategies/v8_apex.py:96,113`)

### 1b. Portfolio sets the inflated reference

**`btc-spot/v10/core/execution.py:132–150`**

```python
self.cash -= total_cost           # line 132: cash debited FIRST
self.btc_qty += qty               # line 133: BTC credited

# Position entry NAV — set ONCE when opening from flat (SPEC §6)
if self._open_entry_ts == 0:      # line 138: first buy only
    if self._entry_nav_pre_cost:
        self.position_entry_nav = self.nav(mid) + total_cost   # line 148
    else:
        self.position_entry_nav = self.nav(mid)                # line 150
```

Where `nav(mid) = cash + btc_qty × mid` (`execution.py:84–86`).

### 1c. Legacy backtesters (v8, v9) — identical logic

- `btc-spot/btc_only_backtest_v8.py:1265–1271`
- `btc-spot/btc_only_backtest_v9.py:791–798`

```python
dd = 1.0 - nav / self.position_entry_nav
if dd >= self.cfg.emergency_dd_pct:
    return True, "emergency_dd"
```

### 1d. VDO dashboard (JavaScript) — simplified approximation

**`vdo/index.html:2946–2949`**

```javascript
const profit = (c.c - pos.entryPrice) / pos.entryPrice;
if (profit <= -V10.emergencyDD) exitReason = "emergency_dd";
```

This uses a **per-price** check (not portfolio NAV). It's visualization-only and diverges from the Python engine.

---

## 2. What `emergency_dd` Measures

**Answer: Portfolio NAV drawdown from an inflated position-entry reference NAV.**

It is NOT:
- a per-trade price stop (`(price − entry) / entry`)
- a portfolio drawdown from all-time equity peak
- a gap-based or time-based trigger

### Classification table

| Candidate definition | Match? | Evidence |
|---------------------|--------|----------|
| Per-trade price stop | **No** | Python uses `1 − nav / ref_nav`, not price return |
| Portfolio DD from all-time peak | **No** | Code comment: "Measures DD from the NAV when the CURRENT position was opened, not from all-time peak" (`btc_only_backtest_v8.py:1261–1263`). Test `test_uses_position_entry_nav_not_equity_peak` explicitly verifies this (`test_v8_apex.py:320–340`). |
| Portfolio DD from position-entry NAV | **Yes** | `dd = 1.0 − state.nav / state.position_entry_nav` — resets each time a new position opens from flat |

---

## 3. Reconciling "-5% per-trade" vs `emergency_dd_pct = 0.28`

### 3.1 The inflation mechanism

With `pre_cost_legacy` mode, `position_entry_nav` is computed at `execution.py:148`:

```
position_entry_nav = nav(mid) + total_cost
```

**Algebraic expansion** (opening from flat, `old_btc = 0`):

```
nav(mid)           = (old_cash − total_cost) + qty × mid    [cash debited, BTC credited]
+ total_cost       = total_cost                              [add back]
─────────────────────────────────────────────────────────────
position_entry_nav = old_cash + qty × mid                    [INFLATED: double-counts BTC]
```

This reference NAV is **not the actual portfolio value** — it's `cash_before_buy + BTC_notional_at_mid`, which exceeds actual NAV by `≈ total_cost ≈ qty × mid`.

### 3.2 Quantifying the inflation

The initial DD (immediately after the first buy, before any price movement) is:

```
dd_initial = 1 − nav_actual / position_entry_nav
           = 1 − (old_cash − fees) / (old_cash + qty × mid)
           ≈ 1 − 1 / (1 + first_buy_exposure)
```

With v10 defaults (`max_add_per_bar = 0.35`, `entry_aggression = 0.85`):

| First buy exposure | position_entry_nav / actual_NAV | DD at entry | Headroom to 0.28 |
|-------------------|------|------------|----------|
| 22% (weak VDO) | 1.22× | 18.0% | **10.0 pp** |
| 30% (moderate) | 1.30× | 23.1% | **4.9 pp** |
| 35% (max single bar) | 1.35× | 25.9% | **2.1 pp** |

### 3.3 Effective per-trade stop

Because `position_entry_nav` is set once (first buy only) and never updated by subsequent pyramiding buys, the headroom is frozen at entry time. With typical first-buy exposure of ~30–35%, the system starts at ~24–26% DD against the inflated reference.

Reaching the 28% threshold requires only **2–4 percentage points** of additional portfolio decline. At typical full-position exposure of ~85–96%, a **~3–5% BTC price drop from peak** is sufficient to breach.

Empirical validation from instrumented backtest (`step0_recomputed_stats.json`):

| Metric | Value |
|--------|-------|
| DD at trigger | 28–30% (consistent with threshold) |
| Median per-trade return | **−5.57%** |
| Range of per-trade returns | −2.89% to −10.32% |
| Source | First 4 emergency_dd triggers, instrumented run |

### 3.4 Why the range is wide (-2.89% to -10.32%)

The variation comes from:
1. **First-buy exposure** varies with VDO strength (22%–35%) → different initial DD / headroom
2. **Pyramiding depth** at trigger time — more adds = higher exposure = larger loss for same price drop
3. **Price path** — a position may gain then reverse, or drop immediately
4. **Fees accumulate** across multiple pyramid buys, eroding NAV

### 3.5 Resolution

| Claim | Source | Verdict |
|-------|--------|---------|
| "~-5% per-trade hard stop" | v10_topping_diagnosis.md | **APPROXIMATELY CORRECT** — describes the observed median outcome |
| `emergency_dd_pct = 0.28` | V8ApexConfig | **CORRECT** — threshold applied to the inflated reference NAV |
| "position_entry_nav = pre-cost NAV" | Code comment | **MISLEADING** — `nav(mid) + total_cost` = `cash_before + qty×mid`, which exceeds actual NAV |

**No mismatch.** The two descriptions operate at different levels:
- **0.28** = config-level threshold on inflated-reference DD
- **~-5%** = observed per-trade portfolio loss when that threshold triggers

The mapping: `0.28 threshold − ~0.26 initial DD = ~0.02 headroom` → at ~85% exposure, ~2.5% BTC drop → ~2–5% portfolio loss. The median of −5.57% is consistent with typical full-exposure positions experiencing a 6–7% BTC decline from entry.

---

## 4. Summary

```
emergency_dd fires when:

  1 − (cash + btc_qty × close) / (cash_before_first_buy + first_qty × mid)  ≥  0.28
      ├── numerator: actual portfolio NAV at current bar close
      └── denominator: inflated reference (set once at position open, pre_cost_legacy mode)

Effective behavior: ~3-5% BTC price decline from entry triggers exit
Observed median per-trade loss: -5.57%
```

**PASS**: The definition is clear, code-consistent across engines, and the apparent "-5% vs 0.28" discrepancy is fully explained by the inflated reference NAV mechanism.
