# V10 Score Definition & Cost Model Reference

## 1. Composite Score Formula

**Source:** `v10/research/objective.py:15-38`

```
score = 2.5 * cagr_pct
      - 0.60 * max_drawdown_mid_pct
      + 8.0 * max(0, sharpe)
      + 5.0 * max(0, min(profit_factor, 3.0) - 1.0)
      + min(n_trades / 50, 1.0) * 5.0
```

**Rejection gate:** if `n_trades < 10` → score = -1,000,000 (line 21-22).

### Components & Weights

| # | Component | Weight | Input key | Bounded? | Purpose |
|---|-----------|--------|-----------|----------|---------|
| 1 | CAGR (%) | +2.5 | `cagr_pct` | No | Reward absolute return |
| 2 | Max DD (%) | -0.60 | `max_drawdown_mid_pct` | No | Penalize drawdown |
| 3 | Sharpe | +8.0 | `sharpe` | floor(0) | Reward risk-adjusted return |
| 4 | Profit Factor | +5.0 | `profit_factor` | cap(3.0), floor(1.0) | Reward win/loss ratio, capped |
| 5 | Trade count | +5.0 | `trades` | saturates at 50 | Penalize too-few-trades |

### Interpretation

- **CAGR dominates** at high returns: +2.5 per 1% CAGR
- **Drawdown penalty** is moderate: -0.60 per 1% MDD (so a 30% MDD costs 18 points)
- **Sharpe bonus** is significant: +8 per 1.0 Sharpe unit (floored at 0, no penalty for negative)
- **Profit Factor** contributes 0-10 points (PF capped at 3.0, shifted by -1.0)
- **Trade count** contributes 0-5 points (linear ramp to 50 trades, then saturates)

---

## 2. Input Metrics — Where They Are Computed

### 2a. `cagr_pct` — Compound Annual Growth Rate

**Source:** `v10/core/metrics.py:62-68`

```python
years = (last_t - first_t) / (365.25 * 24 * 3600 * 1000)   # line 58
cagr = (pow(final_nav / initial_nav, 1.0 / years) - 1.0) * 100.0  # line 65
```

- `initial_nav` = `report_start_nav` (NAV at first reporting bar, line 52)
- `final_nav` = last `nav_mid` in equity curve (line 53)
- Time span computed from epoch-ms of first/last equity snapshots

### 2b. `max_drawdown_mid_pct` — Peak-to-Trough Drawdown

**Source:** `v10/core/metrics.py:159-165`

```python
peak = np.maximum.accumulate(navs)
dd = 1.0 - navs / peak
max_dd = float(dd.max()) * 100.0
```

- Uses `nav_mid` (mark-to-market at bar close, no liquidation cost)

### 2c. `sharpe` — Annualized Sharpe Ratio

**Source:** `v10/core/metrics.py:168-181`

```python
returns = np.diff(navs) / navs[:-1]           # 4H pct returns, line 175
mu = float(returns.mean())                     # line 176
sigma = float(returns.std(ddof=0))             # population std, line 177
sharpe = (mu / sigma) * sqrt(2190)             # annualize, line 181
```

- Annualization factor: `PERIODS_PER_YEAR_4H = (24/4) * 365 = 2190` (line 19)
- No risk-free rate subtraction (Rf = 0)
- Uses `ddof=0` (population std, not sample)

### 2d. `profit_factor`

**Source:** `v10/core/metrics.py:88-95`

```python
gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
profit_factor = gross_profit / gross_loss
```

- Capped at 3.0 in score formula (objective.py line 35)
- `"inf"` string → treated as 3.0 (objective.py line 29)

### 2e. `trades` — Trade Count

**Source:** `v10/core/metrics.py:83`

```python
n_trades = len(trades)
```

- A "trade" = full round-trip (flat → position → flat)
- Partial sells that don't close position don't create a Trade record

---

## 3. Cost Model — "50 bps harsh" Explained

**Source:** `v10/core/types.py:46-77`

### What "50 bps harsh" means in the pipeline

The **harsh** scenario models worst-case execution costs for a retail trader on
Binance Spot with no VIP tier and adverse market conditions:

```python
CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.150)
```

**Per-side cost breakdown** (applied at every fill):

| Component | Value | Meaning |
|-----------|-------|---------|
| Half-spread | 10.0 / 2 = **5.0 bps** | Bid-ask spread cost (you cross the spread) |
| Slippage | **5.0 bps** | Market impact / adverse price movement during fill |
| Taker fee | 0.150% = **15.0 bps** | Exchange taker fee (non-VIP tier) |
| **Per-side total** | **25.0 bps** | |
| **Round-trip total** | **50.0 bps (0.50%)** | Entry + exit combined |

### How costs are applied (execution model)

**Source:** `v10/core/execution.py:1-48`

For each fill, the engine computes an effective fill price that embeds
spread + slippage, then adds the fee on top:

**BUY** (execution.py lines 35-38):
```
ask = mid * (1 + spread_bps / 20000)      # half-spread above mid
fill_px = ask * (1 + slippage_bps / 10000) # + slippage
fee = qty * fill_px * (taker_fee_pct / 100)
total_cost = qty * fill_px + fee
```

**SELL** (execution.py lines 40-43):
```
bid = mid * (1 - spread_bps / 20000)      # half-spread below mid
fill_px = bid * (1 - slippage_bps / 10000) # - slippage
fee = qty * fill_px * (taker_fee_pct / 100)
proceeds = qty * fill_px - fee
```

### All three scenarios

| Scenario | spread | slippage | fee | Per-side | Round-trip | Round-trip % |
|----------|--------|----------|-----|----------|------------|--------------|
| **smart** | 3.0 bps | 1.5 bps | 0.035% | 6.5 bps | 13.0 bps | 0.13% |
| **base** | 5.0 bps | 3.0 bps | 0.100% | 15.5 bps | 31.0 bps | 0.31% |
| **harsh** | 10.0 bps | 5.0 bps | 0.150% | 25.0 bps | 50.0 bps | 0.50% |

**Formula:** `per_side = spread/2 + slippage + fee_pct*100` (all in bps)

Source: `v10/core/types.py:53-55` (property `per_side_bps`)

---

## 4. Engine Pipeline: Bar Loop → Metrics → Score

```
DataFeed (data.py)
  ↓ H4 bars + D1 bars
BacktestEngine.run() (engine.py:83-176)
  ↓ for each H4 bar:
  ↓   1. Execute pending signal at bar OPEN → Portfolio.buy()/sell()
  ↓   2. Record EquitySnap at bar CLOSE
  ↓   3. Call strategy.on_bar() at bar CLOSE
  ↓   4. Store signal for next bar
  ↓
compute_metrics(equity, trades, fills) (metrics.py:22-152)
  ↓ returns dict with cagr_pct, max_drawdown_mid_pct, sharpe, profit_factor, trades, ...
  ↓
compute_objective(summary) (objective.py:15-38)
  → scalar score
```

### Key determinism guarantees

- **No randomness** in engine, strategy, or metrics computation
- DataFeed loads CSV with pandas (deterministic row order)
- All floating-point ops use Python/NumPy defaults (IEEE 754)
- Strategy `V8ApexStrategy` uses no random seed, no sampling
- Two runs with identical (code, data, config) → bit-identical results

---

## 5. File Reference Index

| File | Lines | Content |
|------|-------|---------|
| `v10/research/objective.py` | 15-38 | `compute_objective()` — score formula |
| `v10/core/metrics.py` | 22-152 | `compute_metrics()` — CAGR, Sharpe, MDD, PF, etc. |
| `v10/core/metrics.py` | 159-165 | `_max_drawdown_pct()` |
| `v10/core/metrics.py` | 168-190 | `_sharpe_sortino()` |
| `v10/core/types.py` | 46-77 | `CostConfig`, `SCENARIOS` dict |
| `v10/core/execution.py` | 22-48 | `ExecutionModel` — fill price + fee calc |
| `v10/core/execution.py` | 51-231 | `Portfolio` — cash, holdings, fills, trades |
| `v10/core/engine.py` | 30-259 | `BacktestEngine` — bar loop |
| `v10/core/data.py` | 38+ | `DataFeed` — CSV loader |
| `v10/strategies/v8_apex.py` | all | `V8ApexStrategy` + `V8ApexConfig` |
