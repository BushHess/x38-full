# SPEC_METRICS.md — Performance Metrics for BTCUSDT Spot Long-Only Backtest

**Version:** 1.0
**Date:** 2026-02-21
**Scope:** V8 / V9 (and any future version) — canonical metrics spec
**Depends on:** `SPEC_EXECUTION.md` (cost model, fill logic)

---

## 1. NAV Computation

NAV is the single source of truth. Computed at every bar close:

```
NAV(t) = cash + btc_qty * mid(t)
```

Where `mid(t)` = latest H4 bar close price at time `t`.

Two flavors tracked in the equity curve:

| Field | Definition | Use |
|-------|-----------|-----|
| `nav_mid` | cash + qty * mid | Primary — all metrics use this |
| `nav_liq` | cash + qty * bid | Conservative — worst-case liquidation value |

---

## 2. Return Metrics

### 2.1 Total Return

```
total_return_pct = (final_nav / initial_nav - 1) * 100
```

### 2.2 CAGR (Compound Annual Growth Rate)

```
years = (last_timestamp - first_timestamp) / (365.25 * 24 * 3600 * 1000)
cagr  = (pow(final_nav / initial_nav, 1 / years) - 1) * 100
```

- Timestamps in milliseconds (epoch UTC).
- `365.25` accounts for leap years.
- `initial_nav` = cash at start (default $10,000). `final_nav` = NAV at last bar.

### 2.3 Per-Trade Return

```
return_pct = (exit_fill_px / entry_price_avg - 1) * 100
```

> This is a **price return** (spread + slippage embedded in fill prices). Fees are reflected in `realized_pnl` but not directly in `return_pct`.

---

## 3. Risk Metrics

### 3.1 Max Drawdown

```python
peak    = nav_series.expanding().max()
dd      = 1 - nav_series / peak
max_dd  = dd.max() * 100      # as percentage
```

Reported for both `nav_mid` and `nav_liq`:

| Field | Source |
|-------|--------|
| `max_drawdown_mid_pct` | Drawdown on mid-price NAV |
| `max_drawdown_liq_pct` | Drawdown on liquidation NAV |

### 3.2 Sharpe Ratio (Annualized, 4H returns)

```python
returns          = nav_mid.pct_change().dropna()
mu               = returns.mean()
sigma            = returns.std(ddof=0)         # population std
periods_per_year = (24 / 4) * 365              # = 2190 (4H bars/year)

sharpe = (mu / sigma) * sqrt(periods_per_year)
```

- Uses **population std** (`ddof=0`), not sample std.
- **No risk-free rate subtracted** — hence labeled `sharpe_like` in code.
- Return undefined if `sigma < 1e-12`.

### 3.3 Sortino Ratio (Annualized, 4H returns)

```python
downside_returns = returns[returns < 0]
down_sigma       = downside_returns.std(ddof=0)

sortino = (mu / down_sigma) * sqrt(periods_per_year)
```

- Same `mu` as Sharpe (full return mean), divided by downside deviation only.
- Return undefined if `down_sigma < 1e-12` or no negative returns exist.

### 3.4 Calmar Ratio (if reported)

```
calmar = cagr / max_drawdown_mid_pct
```

Not computed in V8 core. Present in V9. Include in any cross-version dashboard.

---

## 4. Trade-Level Metrics

### 4.1 Win/Loss Counts

```
win   = realized_pnl > 0
loss  = realized_pnl <= 0
```

### 4.2 Win Rate

```
win_rate_pct = (wins / n_trades) * 100
```

### 4.3 Profit Factor

```
gross_profit  = sum(realized_pnl) where realized_pnl > 0
gross_loss    = abs(sum(realized_pnl)) where realized_pnl < 0

profit_factor = gross_profit / gross_loss
```

- Returns `inf` if `gross_loss == 0` and `gross_profit > 0`.
- Returns `0` if both are zero.

### 4.4 Average Trade PnL

```
avg_trade_pnl = mean(realized_pnl)    # in USD
```

### 4.5 Average Days Held

```
avg_days_held = mean(days_held)
days_held     = (exit_ts - entry_ts) / 86_400_000    # ms → days
```

### 4.6 Average Win / Average Loss

```
avg_win  = mean(realized_pnl) where realized_pnl > 0
avg_loss = mean(realized_pnl) where realized_pnl < 0
```

### 4.7 Expectancy

```
expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
```

Or equivalently: `avg_trade_pnl` if all trades weighted equally.

---

## 5. Exposure Metrics

### 5.1 Average Exposure

```
exposure(t)  = (btc_qty * mid(t)) / NAV(t)    # fraction of NAV in BTC
avg_exposure = mean(exposure) over all bars
```

Range: `[0.0, max_total_exposure]` (capped at 1.0 for long-only spot).

### 5.2 Time in Market

```
time_in_market_pct = count(exposure > 0.01) / total_bars * 100
```

Threshold of 1% avoids counting dust positions.

---

## 6. Cost & Turnover Metrics

### 6.1 Total Fees

```
fees_total = sum(fee_quote) across all fills (buy + sell)
```

### 6.2 Turnover (Notional)

```
turnover_notional = sum(qty * fill_px) across all fills
```

### 6.3 Fee Drag Per Year

```
fee_drag_per_year = (fees_total / years) / avg_nav * 100    # as %
```

### 6.4 Turnover Per Year

```
turnover_per_year = turnover_notional / (avg_nav * years)   # as multiple
```

### 6.5 Fill Count

```
fills = count of all individual buy + sell executions
```

Distinct from `trades` — a single trade may have multiple fills (scale-in buys + 1 exit sell).

---

## 7. Scenario Sensitivity Table

All metrics must be reported across the 3 cost scenarios defined in `SPEC_EXECUTION.md`:

| Metric | smart (13 bps RT) | base (31 bps RT) | harsh (50 bps RT) |
|--------|-------------------|-------------------|---------------------|
| CAGR | | | |
| Max DD | | | |
| Sharpe | | | |
| Sortino | | | |
| Profit Factor | | | |
| Win Rate | | | |
| Avg Trade PnL | | | |
| Fees Total | | | |
| Trades | (same) | (same) | (same) |

> Trade count should be identical across scenarios if signal logic is price-independent. If it differs, investigate — cost-dependent sizing may cause qty < min threshold.

---

## 8. Optimizer Objective Function

```python
score = 2.5 * cagr
      - 0.60 * max_dd
      + 8.0  * max(0, sharpe)
      + 5.0  * max(0, min(pf, 3.0) - 1.0)    # PF capped at 3.0
      + min(n_trades / 50, 1.0) * 5.0          # trade count bonus, max 5

# Reject if n_trades < 10
if n_trades < 10:
    score = -1_000_000
```

**Design notes:**
- PF capped at 3.0 to prevent PF-farming (few large winners).
- Trade count bonus saturates at 50 trades — avoids rewarding churn.
- MDD penalty at 0.60x keeps drawdown in check without dominating.

---

## 9. Output Artifacts

Each backtest run produces:

| File | Content |
|------|---------|
| `summary.json` | All metrics from sections 2-6 as flat key-value |
| `equity.csv` | Per-bar: `close_time, nav_mid, nav_liq, exposure, cash, btc_qty` |
| `trades.csv` | Per-trade: `entry/exit times, prices, qty, pnl, return%, days, reasons` |
| `fills.csv` | Per-fill: `ts, side, qty, price, fee, notional, reason` |

---

## 10. Metric Reference Card

| Metric | Key in `summary.json` | Unit | Annualized? |
|--------|----------------------|------|-------------|
| Total Return | `total_return_pct_mid` | % | No |
| CAGR | `cagr_pct_mid` | % | Yes |
| Max Drawdown (mid) | `max_drawdown_mid_pct` | % | No |
| Max Drawdown (liq) | `max_drawdown_liq_pct` | % | No |
| Sharpe | `sharpe_like` | ratio | Yes (4H) |
| Sortino | `sortino_like` | ratio | Yes (4H) |
| Trades | `trades` | count | No |
| Wins | `wins` | count | No |
| Losses | `losses` | count | No |
| Win Rate | `win_rate_pct` | % | No |
| Profit Factor | `profit_factor` | ratio | No |
| Avg Trade PnL | `avg_trade_pnl` | USD | No |
| Avg Days Held | `avg_days_held` | days | No |
| Avg Exposure | `avg_exposure` | fraction | No |
| Time in Market | `time_in_market_pct` | % | No |
| Total Fees | `fees_total` | USD | No |
| Turnover | `turnover_notional` | USD | No |
| Fills | `fills` | count | No |
