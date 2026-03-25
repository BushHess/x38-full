# SPEC_EXECUTION.md — Execution Model for BTCUSDT Spot Long-Only Backtest

**Version:** 1.0
**Date:** 2026-02-21
**Scope:** V8 / V9 (and any future version) — canonical execution spec
**Asset:** BTCUSDT Spot, long-only

---

## 1. Timing & Data Convention

| Item | Spec |
|------|------|
| Timezone | **UTC** for all timestamps |
| Signal evaluation | On bar close (H4 close for entry/exit signals, D1 close for regime) |
| Fill timing | **Next bar open** — signal on bar `t`, fill at `open[t+1]` |
| Mid price for fill | `open` of the next bar following the signal bar |
| Data source | Binance BTCUSDT Spot klines (1H / 4H / 1D) |

> **Rationale:** "Fill at current close" introduces look-ahead bias — the signal uses the close price that also determines the fill. Next-open eliminates this.

---

## 2. Cost Formula — Per-Side

Three cost components are applied **at each fill** (buy or sell), independently:

### 2.1 Bid-Ask Spread

```
half_spread = spread_bps / 2 / 10_000

BUY:   ask = mid * (1 + half_spread)
SELL:  bid = mid * (1 - half_spread)
```

### 2.2 Slippage

```
BUY:   fill_px = ask * (1 + slippage_bps / 10_000)
SELL:  fill_px = bid * (1 - slippage_bps / 10_000)
```

### 2.3 Taker Fee

```
fee = (qty * fill_px) * (taker_fee_pct / 100)
```

### 2.4 Total Cash Flow

```
BUY:   total_cost = qty * fill_px + fee        (cash debited)
SELL:  proceeds   = qty * fill_px - fee         (cash credited)
```

### 2.5 Composite Per-Side Cost (in bps)

```
cost_per_side_bps = spread_bps / 2 + slippage_bps + taker_fee_pct * 100

round_trip_bps    = 2 * cost_per_side_bps
```

> All three components are **fixed percentages of price**, not ATR-adaptive.

---

## 3. Cost Scenarios

### 3.1 Definition Table

| Scenario | `spread_bps` | `slippage_bps` | `taker_fee_pct` | Per-Side (bps) | Round-Trip (bps) | Round-Trip (%) |
|----------|-------------|----------------|-----------------|---------------|-----------------|---------------|
| **smart** | 3.0 | 1.5 | 0.035% | 6.5 | 13.0 | **0.13%** |
| **base** | 5.0 | 3.0 | 0.100% | 15.5 | 31.0 | **0.31%** |
| **harsh** | 10.0 | 5.0 | 0.150% | 25.0 | 50.0 | **0.50%** |

### 3.2 Scenario Rationale

| Scenario | When to use |
|----------|-------------|
| **smart** | VIP-2+ fee tier, maker rebate, <$50K notional, low-vol hours |
| **base** | Taker fills on Binance Spot, standard VIP-0, any time of day |
| **harsh** | High-vol events (CPI, FOMC), large orders (>$200K), wide books |

### 3.3 Base Label Mismatch — MUST READ

V9 codebase labels the base scenario as **~0.26% RT**. The actual formula yields **0.31% RT**.

**Root cause:** the label was computed **without the spread component**:

```
Label formula (WRONG):   (slippage_bps + taker_fee_pct * 100) * 2
                        = (3 + 10) * 2 = 26 bps = 0.26% RT   <-- matches label

Correct formula:          (spread_bps/2 + slippage_bps + taker_fee_pct * 100) * 2
                        = (2.5 + 3 + 10) * 2 = 31 bps = 0.31% RT
```

| | Label says | Formula gives | Delta |
|---|-----------|---------------|-------|
| Base RT | 0.26% | 0.31% | **+5 bps** (spread omitted) |

**Resolution — canonical value is 0.31% RT.** All future reports, dashboards, and optimizer outputs must use this value. The label `~0.26%` is deprecated.

---

## 4. Entry Price Tracking (Weighted Average)

When a position accumulates via multiple buys:

```python
# On each new buy fill:
old_value         = btc_qty * entry_price_avg
new_value         = old_value + new_qty * fill_px
entry_price_avg   = new_value / (btc_qty + new_qty)
```

The `entry_price_avg` reflects the volume-weighted average fill price across all entry fills (spread + slippage baked in, fees tracked separately).

---

## 5. Realized PnL

```
cost_basis    = entry_price_avg * sell_qty
realized_pnl  = proceeds - cost_basis
              = (sell_qty * fill_px_sell - fee_sell) - (entry_price_avg * sell_qty)
```

This is a **fully-loaded PnL** — includes spread, slippage, and fees on both sides.

---

## 6. Position Entry NAV (for Emergency DD)

```
position_entry_nav = NAV immediately before the first fill of a new position
```

Implementation (when `entry_nav_pre_cost=True`, the default):

```python
# After fill: cash and btc_qty already updated, so undo to get pre-fill NAV.
position_entry_nav = (cash + total_cost) + (btc_qty - qty) * mid
#                     ^^^ undo cash ^^^     ^^^ undo BTC ^^^
# When entering from flat (btc_qty == qty): simplifies to initial cash.
```

Emergency drawdown is measured from `position_entry_nav`, **not** from all-time equity peak. This prevents the "death spiral" bug where a slow-grinding equity decline triggers emergency exits on every new position.

---

## 7. Cash Constraint

If `total_cost > cash`, the engine reduces `qty` to fit:

```python
max_notional = cash / (1 + taker_fee_pct / 100)
qty           = max_notional / fill_px
```

No margin. No borrowing. Strict spot-only.

---

## 8. Numerical Example — Base Scenario

**Entry:**
```
mid (next open) = $65,000.00
ask             = 65,000 * (1 + 5/20,000) = $65,016.25
fill_px_buy     = 65,016.25 * (1 + 3/10,000) = $65,035.75
notional        = 0.10 BTC * $65,035.75 = $6,503.58
fee             = $6,503.58 * 0.001 = $6.50
total_cost      = $6,503.58 + $6.50 = $6,510.08
```

**Exit:**
```
mid (next open) = $67,000.00
bid             = 67,000 * (1 - 5/20,000) = $66,983.25
fill_px_sell    = 66,983.25 * (1 - 3/10,000) = $66,963.16
notional        = 0.10 BTC * $66,963.16 = $6,696.32
fee             = $6,696.32 * 0.001 = $6.70
proceeds        = $6,696.32 - $6.70 = $6,689.62
```

**PnL:**
```
cost_basis      = $65,035.75 * 0.10 = $6,503.58
realized_pnl    = $6,689.62 - $6,503.58 = +$186.05
return%         = (66,963.16 / 65,035.75 - 1) * 100 = +2.96%
```

---

## 9. Implementation Checklist

- [ ] All timestamps in UTC
- [ ] Fill at `open[t+1]`, never at signal bar close
- [ ] `spread_bps` split symmetrically around mid
- [ ] `slippage_bps` applied on top of bid/ask
- [ ] `taker_fee_pct` applied to notional, deducted from cash
- [ ] Weighted-average entry price across multiple fills
- [ ] Emergency DD from `position_entry_nav`, not equity peak
- [ ] No margin — reduce qty if cash insufficient
- [ ] Base scenario = 0.31% RT (not 0.26%)
