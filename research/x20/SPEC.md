# X20: Cross-Asset VTREND Portfolio — Breadth Expansion

## Context

VTREND E5+EMA21D1 is validated on BTC only (Sharpe 1.48, 53 studies). Single-asset,
single-strategy. Cross-timescale ρ=0.92 caps intra-BTC diversification at +3.5%.

Fundamental Law of Active Management: IR = IC × √BR. IC (signal quality) is near
ceiling after 53 studies. The only mathematically guaranteed path to higher portfolio
Sharpe is increasing BR (breadth = number of independent bets).

**Portfolio Sharpe theorem**: S_portfolio ≥ max(S_i) when adding uncorrelated return
streams. Strictly better when ρ < 1 and S_new > 0.

### Prior Multi-Coin Evidence

| Study | Finding |
|-------|---------|
| #30 (multicoin_ema_regime) | EMA(21d) helps 11/14 coins. Proven 16/16 TS, p=1.5e-5 |
| #31 (multicoin_diversification) | 8/14 coins positive Sharpe at default params (E0) |
| #32 (multicoin_exit_variants) | E5 wins 3/14 coins only (BTC, ETH, BCH marginal) |
| Q16 (X6 research) | E5+EMA1D21 does NOT generalize multi-coin. E0+EMA1D21 preferred for non-BTC |

### Key Gap

Prior studies validated individual coins but did NOT:
1. Run E0+EMA1D21 per coin (only estimated additively in Q16)
2. Compute per-coin WFO validation
3. Construct and validate a multi-asset portfolio
4. Bootstrap portfolio-level Sharpe improvement

This study fills ALL four gaps.

## Central Question

Does a multi-asset VTREND portfolio achieve statistically higher Sharpe than
BTC-only, using per-asset validated strategies with independent capital allocation?

## Architecture

### Asset-Specific Strategy Assignment

E5's tight trail (Q90-capped ATR) catastrophically fails on high-vol assets.
Strategy assignment is NOT a free parameter — it's determined by prior evidence:

```
BTC  → E5+EMA1D21  (validated: Study #43, PROMOTED)
ETH  → E5+EMA1D21  (Q16: E5 helps ETH, +0.098 Sharpe. Needs actual validation)
ALL OTHERS → E0+EMA1D21  (Q16: E5 damages altcoins, E0+EMA generalizes)
```

### Asset Selection Protocol

**Candidate pool**: 14 coins from data-pipeline cache (BTCUSDT, ETHUSDT, BNBUSDT,
SOLUSDT, XRPUSDT, LTCUSDT, ADAUSDT, DOGEUSDT, TRXUSDT, AVAXUSDT, LINKUSDT,
BCHUSDT, HBARUSDT, XLMUSDT).

**Selection criteria** (sequential, each screen reduces pool):
1. **Liquidity**: Top 10 by average daily volume (drop illiquid tails)
2. **Full-sample screen**: Sharpe > 0.0 with assigned strategy at default params (N=120)
3. **Plateau check**: spread < 0.10 across slow=60-200 (avoid curve-fit coins)
4. **WFO screen**: ≥ 2/4 folds positive d_sharpe vs buy-and-hold

Assets failing any screen are EXCLUDED from portfolio. Minimum 3 assets required
(including BTC) for portfolio to proceed.

### Portfolio Construction

**No optimization** — zero additional DOF:

1. **Equal weight (EW)**: w_i = 1/K for K selected assets
2. **Inverse-variance (IV)**: w_i ∝ 1/σ²_i, estimated from training returns
3. **BTC-capped (BC)**: Equal weight but cap BTC at 40%, redistribute remainder equally

All three are analytical (no optimization), no parameters to tune.

**Rebalancing**: Monthly at month-end. Each asset runs independently within
its allocation. Rebalance = reallocate capital to target weights.

**No leverage**: Σ w_i = 1.0. Cash drag from unused allocation (asset in OUT state)
is real and included.

### Capital and Cost

- Per-asset: CASH × w_i at start, monthly rebalance
- Cost: 50 bps RT per asset (harsh, same as all BTC studies)
- No cross-asset cost (each runs independently)

## Data

### Source
- Data pipeline: `/var/www/trading-bots/data-pipeline/.cache_binance_vision`
- Fetch at runtime (same as multicoin_diversification.py)
- Timeframes: H4 (primary) + D1 (EMA regime filter)
- D1 bars: aggregate from H4 (4 bars per day)

### Alignment
- Common period: determined by latest coin start date + 365d warmup
- Study #31 alignment: 2021-09-22 to 2026-02-28 (~4.4 years)
- BTC full period: 2017-08 to 2026-02 (~8.5 years, for BTC-only comparison)

### History Requirements per Asset
- Minimum: 3 years of H4 data after warmup
- Maximum: all available data

## Parameter Grid

### Per-asset parameters (frozen, NOT tuned in this study)
```
slow_period = 120     (default, proven plateau)
fast_period = 30      (slow // 4)
trail_mult = 3.0      (default)
vdo_threshold = 0.0   (default)
d1_ema_period = 21    (PROVEN, 15-40d range)
atr_period = 14       (E0) or ratr_period=20 (E5)
```

### Portfolio parameters (analytical, NOT tuned)
```
Weighting: {EW, IV, BTC-capped}    — 3 schemes, all deterministic
Rebalance: monthly                  — fixed
```

### DOF
- Per-asset: 0 (frozen params from prior studies)
- Portfolio: 0 (no optimization)
- Total additional DOF beyond BTC-only: **0**

This is critical: portfolio improvement (if any) comes ENTIRELY from diversification,
not from parameter tuning. There is nothing to overfit.

## Test Suite

### T0: Per-Asset Full-Sample Backtest (screen)

For each of 14 coins, run assigned strategy with default params.

**Report per coin**:
- Sharpe, CAGR, MDD, Calmar, trades, avg_exposure
- Strategy used (E5+EMA1D21 or E0+EMA1D21)
- Plateau: spread across slow=60-200

**Gate G0**: ≥ 3 coins (incl. BTC) pass all 3 screens (Sharpe > 0, plateau, WFO ≥ 2/4).

### T1: Cross-Asset Correlation Matrix

Using per-asset daily returns (from H4 equity curves):

1. **Full-sample Pearson correlation** matrix (K × K)
2. **Rolling 180-day correlation** to check stability
3. **Drawdown correlation** (correlation during top-5 drawdown episodes)

No gate — informational for portfolio construction.

**Key concern**: Crypto correlations spike during crashes (correlation 1 when it
matters most). Drawdown correlation ≥ 0.7 is expected and must be documented.

### T2: Portfolio Backtest (primary test)

For each weighting scheme {EW, IV, BC}:
1. Allocate capital per weights
2. Run each asset independently
3. Monthly rebalance to target weights
4. Compute portfolio equity curve = Σ(asset_equity_i)
5. Measure: Sharpe, CAGR, MDD, Calmar

**Gate G1**: Best portfolio Sharpe > BTC-only Sharpe (S_portfolio > S_BTC)

### T3: Walk-Forward Validation (4 folds)

Same fold structure as BTC studies. For each fold:
1. Training: compute per-asset IV weights from training returns
2. Test: run portfolio with training weights, measure test Sharpe
3. d_sharpe = portfolio_test_sharpe - btc_only_test_sharpe

**Gate G2**: WFO win rate ≥ 3/4 AND mean d_sharpe > 0

### T4: Portfolio Bootstrap (500 VCBB)

Block bootstrap on JOINT daily returns (preserve cross-asset correlation):
1. Sample 500 block-bootstrap paths of JOINT daily returns
2. For each path: run portfolio and BTC-only
3. d_sharpe(path) = portfolio_sharpe - btc_sharpe

**Gate G3**: P(d_sharpe > 0) > 60%
**Gate G4**: median d_mdd ≤ +5.0 pp (portfolio MDD not much worse)

### T5: Drawdown Analysis

1. Portfolio MDD vs BTC-only MDD
2. Maximum simultaneous drawdown (all assets in drawdown)
3. Diversification ratio = σ_portfolio / Σ(w_i × σ_i)
4. Timeline of worst drawdown episodes

No gate — informational.

### T6: Comparison Table

| Strategy | Sharpe | CAGR | MDD | Trades | Assets |
|----------|--------|------|-----|--------|--------|
| BTC-only E5+EMA1D21 | ... | ... | ... | ... | 1 |
| Portfolio EW | ... | ... | ... | ... | K |
| Portfolio IV | ... | ... | ... | ... | K |
| Portfolio BC | ... | ... | ... | ... | K |

## Verdict Gates

| Gate | Test | Condition |
|------|------|-----------|
| G0 | T0 | ≥ 3 coins pass screens |
| G1 | T2 | Best portfolio Sharpe > BTC-only |
| G2 | T3 | WFO ≥ 75%, mean d > 0 |
| G3 | T4 | P(d_sharpe > 0) > 60% |
| G4 | T4 | Median d_mdd ≤ +5pp |

## Decision Matrix

| Outcome | Action |
|---------|--------|
| G0 fail (< 3 coins viable) | CLOSE — VTREND is BTC-specific |
| G0 pass, G1 fail | CLOSE — diversification doesn't improve Sharpe (ρ too high) |
| G1+G2+G3+G4 all pass | **PROMOTE** — multi-asset portfolio superior |
| G1+G2 pass, G3 or G4 fail | **HOLD** — directionally correct but not robust |

## Implementation Notes

### Multi-coin data loading
```python
# Reuse data-pipeline cache (same as multicoin_diversification.py)
from data_pipeline import load_h4_bars  # or equivalent
```

### D1 bar aggregation
```python
# Aggregate H4 → D1 for regime filter
d1_close = h4_close[::6][-1]  # last H4 close per day
# Or proper OHLCV aggregation: O=first, H=max, L=min, C=last, V=sum
```

### Joint bootstrap
The bootstrap must preserve cross-asset correlation:
```python
# Block-sample DATE INDICES, then extract all assets for those dates
block_indices = sample_block_indices(n_days, block_size=60, seed=seed)
for asset in assets:
    asset_returns_boot = asset_daily_returns[block_indices]
```

### NAV computation
Per-asset NAV runs independently. Portfolio NAV = sum of per-asset NAVs.
Rebalance at month-end: transfer capital between asset accounts to match
target weights based on current total NAV.

## Estimated Runtime

- T0 (per-asset screen): ~30s (14 coins × 1 backtest + plateau)
- T1 (correlation): ~5s
- T2 (portfolio backtest): ~10s (3 weighting schemes)
- T3 (WFO): ~30s (4 folds × K assets × 3 schemes)
- T4 (bootstrap): ~300s (500 paths × K assets)
- T5 (drawdown): ~5s
- T6 (comparison): ~1s
- Total: ~6-7 min

## Output Files

```
x20/
  SPEC.md
  benchmark.py
  x20_results.json
  x20_per_asset.csv        (T0)
  x20_correlation.csv      (T1)
  x20_portfolio.csv        (T2)
  x20_wfo.csv              (T3)
  x20_bootstrap.csv        (T4)
  x20_drawdown.csv         (T5)
  x20_comparison.csv       (T6)
  REPORT.md
```
