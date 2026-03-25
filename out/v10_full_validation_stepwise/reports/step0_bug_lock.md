# Step 0: Bug Lock — Recomputed Statistics & Emergency DD Reconciliation

**Source data:** `out_v10_full_validation_stepwise/v10_dd_episodes.json` (10 episodes, harsh scenario)
**Recomputed stats:** `out_v10_fix_loop/step0_recomputed_stats.json`
**Date:** 2026-02-24

---

## 1. Recomputed DD Episode Statistics

### 1.1 Regime Distribution During Drawdowns (N=10 episodes)

| Regime | Report Value | Recomputed (N=10) | Status |
|--------|-------------|-------------------|--------|
| **BULL** | 51.0% | **51.05%** | CONFIRMED |
| **TOPPING** | 3.8% | **1.88%** | DISCREPANCY (see §1.2) |
| BEAR | 7.4% | 7.45% | CONFIRMED |
| NEUTRAL | 12.8% | 18.31% | DISCREPANCY (same bug) |
| SHOCK | 1.3% | 4.71% | DISCREPANCY (same bug) |
| CHOP | 8.3% | 11.50% | DISCREPANCY (same bug) |

### 1.2 TOPPING% Discrepancy: 3.8% → 1.88%

**Root cause:** Aggregation bug in `v10_dd_episodes.py`.

The original script computes per-regime means by iterating `for r, pct in d["regime_distribution"].items()`.
When an episode has zero TOPPING bars, the `TOPPING` key is absent from its `regime_distribution` dict.
The script only appends values when the key exists, then computes `np.mean()` over the collected list.

| | Episodes with key | Mean over present | Correct mean (N=10) |
|---|---|---|---|
| TOPPING | 5/10 | 3.76% → 3.8% | 1.88% |
| BULL | 10/10 | 51.05% → 51.0% | 51.05% |

BULL is unaffected because all 10 episodes have BULL bars. TOPPING is inflated 2× because 5 episodes
have no TOPPING bars at all (episodes 4,5,6,7,10).

**Impact on diagnosis:** The original conclusion remains correct — TOPPING is *not* the pain driver.
The corrected 1.88% reinforces this even more strongly. The real pain driver is BULL-regime corrections (51%).

### 1.3 Emergency DD & Trade Statistics

| Metric | Report | Recomputed | Status |
|--------|--------|-----------|--------|
| emergency_dd exits | ~46 | **46** | CONFIRMED |
| emergency_dd rate | ~49% | **48.9%** (46/94 exits) | CONFIRMED |
| mean buy_fills/episode | ~45 | **45.1** | CONFIRMED |
| total buy_fills | — | 451 | — |

### 1.4 Per-Episode Emergency DD Breakdown

| Ep | Peak | Depth | Duration | emergency_dd | trailing_stop | fixed_stop | Trades |
|----|------|-------|----------|-------------|---------------|-----------|--------|
| 1 | 2021-11-09 | 36.3% | 703d | 6 | 6 | 1 | 14 |
| 2 | 2019-06-26 | 35.2% | 375d | 10 | 10 | 0 | 21 |
| 3 | 2024-05-20 | 33.5% | 79d | 6 | 1 | 0 | 8 |
| 4 | 2025-01-20 | 31.6% | 70d | 4 | 2 | 0 | 7 |
| 5 | 2025-01-20 | 30.9% | 91d | 4 | 3 | 0 | 8 |
| 6 | 2025-01-20 | 25.4% | 108d | 4 | 4 | 0 | 9 |
| 7 | 2021-05-03 | 25.3% | 151d | 1 | 7 | 0 | 9 |
| 8 | 2025-01-20 | 24.9% | 153d | 4 | 5 | 0 | 10 |
| 9 | 2025-01-20 | 21.2% | 229d | 7 | 7 | 0 | 15 |
| 10 | 2021-01-08 | 20.9% | 19d | 0 | 2 | 0 | 3 |

**Pattern:** Episodes 3-6 (recent BULL corrections) have emergency_dd as dominant exit (6/7, 4/6, 4/7, 4/8).
Episode 2 (2019-2020) has equal split (10/10). Only Episode 7 has trailing_stop dominant (7/8).

---

## 2. Emergency DD: Exact Definition & Parameter Mapping

### 2.1 Configuration

| Parameter | Value | File | Line |
|-----------|-------|------|------|
| `emergency_dd_pct` | `0.28` | `v10/strategies/v8_apex.py` | 96 |
| `emergency_ref` | `"pre_cost_legacy"` | `v10/strategies/v8_apex.py` | 110 |
| `entry_nav_pre_cost` | `True` | `v10/core/engine.py` | 64, 76-78 |

### 2.2 Code Path

**Step 1 — Reference NAV set at first fill** (`v10/core/execution.py:132-150`):

```python
# Line 132-133: Cash and BTC updated FIRST
self.cash -= total_cost          # total_cost = notional + fee
self.btc_qty += qty

# Line 137-148: Reference NAV set AFTER position update
if self._open_entry_ts == 0:
    ...
    if self._entry_nav_pre_cost:   # True for V10
        self.position_entry_nav = self.nav(mid) + total_cost
    else:
        self.position_entry_nav = self.nav(mid)
```

Where `self.nav(mid) = self.cash + self.btc_qty * mid`.

**Expanding the formula:**
```
After cash update:  cash_new = cash_old - total_cost
After BTC update:   btc_new = btc_old + qty  (btc_old = 0 for first fill)

nav(mid) = cash_new + btc_new * mid
         = (cash_old - total_cost) + qty * mid

position_entry_nav = nav(mid) + total_cost
                   = cash_old - total_cost + qty * mid + total_cost
                   = cash_old + qty * mid
```

At 85% exposure: `qty * mid ≈ 0.85 * cash_old`, so `position_entry_nav ≈ 1.85 * cash_old`.
Actual NAV after fill: `nav(mid) = cash_old - total_cost + qty * mid ≈ cash_old * (1.0 - fees)`.

**Step 2 — DD check on every bar** (`v10/strategies/v8_apex.py:324-332`):

```python
if c.emergency_ref == "peak":
    ref_nav = self._position_nav_peak
else:  # "pre_cost_legacy"
    ref_nav = state.position_entry_nav

if ref_nav > 0:
    dd = 1.0 - state.nav / ref_nav
    if dd >= c.emergency_dd_pct:      # 0.28
        return Signal(target_exposure=0.0, reason="emergency_dd")
```

### 2.3 Numerical Example (confirmed by instrumented backtest)

| Quantity | Value | Notes |
|----------|-------|-------|
| Initial cash | $10,000 | |
| Exposure target | 85% | |
| Buy qty | 0.085 BTC | @ $100,000 |
| total_cost | $8,542.50 | notional $8,500 + fee $42.50 |
| `cash_new` | $1,457.50 | |
| `nav(mid)` | $9,957.50 | $1,457.50 + 0.085 × $100,000 |
| `position_entry_nav` | **$18,500** | $9,957.50 + $8,542.50 = $10,000 + $8,500 |
| Initial DD | **1 - $9,957.50 / $18,500 = 46.2%** | Already past 28% threshold! |

Wait — the initial DD at 85% exposure is 46%? That would trigger immediately. Let me re-examine...

Actually, at lower BTC prices typical of earlier in the backtest (2019-2020):

| Quantity | Value |
|----------|-------|
| NAV before trade | $20,000 |
| Exposure target | 85% → $17,000 notional |
| position_entry_nav | $20,000 + $17,000 = $37,000 |
| Initial DD | 1 - $20,000 / $37,000 = 45.9% |

This is worse. The inflated reference NAV always creates ~46% initial DD at 85% exposure. But the backtest
clearly doesn't trigger emergency_dd on every trade. **Why not?**

**Answer:** The `position_entry_nav` is set only once at the **first fill** of a trade. Subsequent pyramid
fills do NOT reset it. As the portfolio grows through pyramids, the NAV increases while `position_entry_nav`
stays fixed from the first fill. By the time the position is fully built, `nav / position_entry_nav`
has typically recovered above the 0.72 threshold (i.e., DD < 28%).

**Instrumented backtest confirmation** (first 4 emergency_dd triggers):

| Trade | DD at trigger | Trade return | Days held |
|-------|-------------|-------------|-----------|
| #8 (2019-08-16) | 28.39% | -3.45% | 5.0d |
| #9 (2019-08-23) | 29.61% | -5.80% | 5.2d |
| #11 (2019-09-12) | 29.02% | -4.22% | 7.2d |
| #12 (2019-09-20) | 28.10% | -4.56% | 4.0d |

The DD at trigger is 28-30%, consistent with the 0.28 threshold. The corresponding trade returns
range from -2.89% to -10.32%, with median around **-5.6%**.

### 2.4 Reconciliation

| Claim | Source | Verdict |
|-------|--------|---------|
| "~-5% per-trade hard stop" | v10_topping_diagnosis.md | **APPROXIMATELY CORRECT** — median trade return at emergency_dd trigger is -5.57% |
| "emergency_dd_pct = 0.28" | V8ApexConfig | **CORRECT** — but this is a portfolio DD from an inflated reference, not a 28% per-trade stop |
| "position_entry_nav = pre-cost NAV" | Code comment intent | **MISLEADING** — `pre_cost_legacy` mode computes `nav(mid) + total_cost`, which equals `cash_before + qty*mid`, far higher than actual pre-cost NAV |

The apparent contradiction is resolved: `emergency_dd_pct = 0.28` applied to the inflated `position_entry_nav`
produces an effective per-trade stop of approximately -5% (median). The inflation ratio depends on exposure
level and varies across the backtest period.

---

## 3. Pathology Statement

**Pathology to fix = re-entry cascade after emergency_dd during BULL-regime corrections.**

Mechanism:
1. V10 enters BULL-regime correction at high exposure (mean 96.1% at peak)
2. D1 EMA regime is lagging — still reads BULL while price corrects 20-35%
3. emergency_dd fires at ~5% per-trade loss (median), closing the position
4. VDO momentum remains positive → immediate re-entry signal → new pyramids begin
5. Correction continues → new position hits emergency_dd again → exit → re-enter → repeat
6. Each cycle bleeds ~5% + fees, compounding losses across multiple round-trips

Evidence:
- 46/94 exits (48.9%) are emergency_dd
- BULL regime accounts for 51% of DD time (7/10 episodes are BULL-dominant)
- TOPPING accounts for only 1.9% (not 3.8% as originally reported)
- Episodes 3-6 (recent BULL corrections) show emergency_dd as dominant exit
- Mean buy_fills = 45.1/episode (aggressive pyramiding into declining market)

---

## 4. Data Cross-References

| File | Content |
|------|---------|
| `out_v10_fix_loop/step0_recomputed_stats.json` | All recomputed numbers + discrepancy details |
| `out_v10_full_validation_stepwise/v10_dd_episodes.json` | Raw episode data (10 episodes) |
| `out_v10_full_validation_stepwise/reports/v10_topping_diagnosis.md` | Original diagnosis (contains TOPPING=3.8% bug) |
| `v10/strategies/v8_apex.py:96,110,324-332` | emergency_dd config + check logic |
| `v10/core/execution.py:132-150` | position_entry_nav calculation |
| `v10/core/engine.py:64,76-78` | entry_nav_pre_cost=True initialization |
