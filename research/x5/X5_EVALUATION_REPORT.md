# X5 Evaluation Report: Partial Profit-Taking

**Date**: 2026-03-08
**Status**: EVALUATED — tradeoff, not strict improvement

## 1. Hypothesis

X0 (E0+EMA21 D1) relies entirely on trailing stop (3×ATR) for exits. Trades that gain +10%+ often give back profit as the trail catches up. X5 adds partial profit-taking to lock in gains:

- **TP1**: unrealized >= +10% → sell 25%, move stop to breakeven
- **TP2**: unrealized >= +20% → sell another 25%, widen trail to 5×ATR

## 2. Strategy Design

**State machine** (4 states):

| State | Exposure | Trail Stop | Transition |
|-------|----------|------------|------------|
| FLAT | 0.0 | — | Entry conditions met → LONG_FULL |
| LONG_FULL | 1.0 | peak - 3×ATR | Unrealized >= 10% → LONG_T1 |
| LONG_T1 | 0.75 | max(entry_price, peak - 3×ATR) | Unrealized >= 20% → LONG_T2 |
| LONG_T2 | 0.50 | peak - 5×ATR | Trail/trend exit → FLAT |

Entry conditions identical to X0: EMA crossover + VDO > 0 + D1 regime.
Exit: trail stop or trend reversal (EMA cross-down) from any LONG state.

**Parameters** (beyond X0 base):
- `tp1_pct=0.10`, `tp2_pct=0.20`
- `tp1_sell_frac=0.25`, `tp2_sell_frac=0.25`
- `trail_mult_tp2=5.0`

## 3. T1: Backtest Results

Period: 2019-01-01 to 2026-02-20 (warmup=365d), initial cash=$10,000.

| Metric | X0 smart | X0 base | X0 harsh | X5 smart | X5 base | X5 harsh |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| Sharpe | 1.5572 | 1.4443 | 1.3249 | 1.5196 | 1.4046 | 1.2831 |
| CAGR% | 69.12 | 61.94 | 54.70 | 52.01 | 46.77 | 41.44 |
| MDD% | 39.42 | 40.71 | 42.05 | 33.02 | 36.07 | 39.14 |
| Calmar | 1.7535 | 1.5214 | 1.3008 | 1.5751 | 1.2968 | 1.0588 |
| Trades | 172 | 172 | 172 | 141 | 141 | 141 |
| Win Rate% | 44.2 | 43.6 | 42.4 | 44.0 | 43.3 | 42.5 |
| Profit Factor | 1.8964 | 1.8108 | 1.7151 | 1.8869 | 1.8080 | 1.7176 |
| Avg Exposure | 0.4544 | 0.4544 | 0.4544 | 0.3781 | 0.3781 | 0.3782 |
| Fills | 344 | 344 | 344 | 329 | 329 | 329 |

### Delta (X5 − X0)

| Scenario | dSharpe | dCAGR% | dMDD% | dTrades | dExpo |
|----------|:---:|:---:|:---:|:---:|:---:|
| smart | -0.0376 | -17.11 | **-6.40** | -31 | -0.0763 |
| base | -0.0397 | -15.17 | **-4.64** | -31 | -0.0763 |
| harsh | -0.0418 | -13.26 | **-2.91** | -31 | -0.0762 |

## 4. T2: Bootstrap VCBB (500 paths, block=60)

| Metric | X0 median [p5, p95] | X5 median [p5, p95] |
|--------|-----|-----|
| Sharpe | 0.2608 [-0.43, 0.93] | 0.2438 [-0.44, 0.94] |
| CAGR% | 3.17 [-16.30, 31.27] | 2.89 [-16.21, 26.58] |
| MDD% | 62.18 [43.14, 84.90] | 58.79 [40.13, 83.75] |
| P(CAGR>0) | 0.602 | 0.594 |

### Head-to-Head (X5 − X0, 500 paths)

| Metric | X5 wins | Mean delta |
|--------|:---:|:---:|
| Sharpe | 190/500 (38.0%) | -0.0263 |
| CAGR | 198/500 (39.6%) | -1.10% |
| **MDD** | **418/500 (83.6%)** | **-3.41%** |

## 5. T3: Parity Check

| Strategy | Engine trades | Vec trades | Sharpe diff |
|----------|:---:|:---:|:---:|
| X0 | 172 | 186 | 0.0090 |
| X5 | 141 | 157 | 0.0004 |

Trade count difference is expected: vectorized surrogate uses close-as-proxy for next-open fill, creating slight timing divergence. Sharpe diff < 0.01 — acceptable for bootstrap.

## 6. T4: Trade-Level Analysis (harsh)

### X0 baseline
- 172 trades, 25 exited >10%, 12 exited >20%
- Total PnL: $243,441
- 158 trail stops, 14 trend exits

### X5 exit breakdown
- 141 trades, Total PnL: $123,315
- **111 trail stops** (78.7%) — avg return +3.89%, WR 41.4%
- **13 breakeven stops** (9.2%) — avg return **+7.07%**, WR **100.0%**
- **17 trend exits** (12.1%) — avg return -2.02%, WR 11.8%

The breakeven stop mechanism works as designed: all 13 trades that triggered TP1 then hit the breakeven stop were profitable (100% WR, avg +7.07%). These are trades where X0 would have given back more profit via the trailing stop.

## 7. Verdict: TRADEOFF, NOT STRICT IMPROVEMENT

**What X5 does well:**
- MDD reduction: -2.9% to -6.4% across cost scenarios
- Bootstrap MDD: wins 83.6% of paths (statistically significant)
- Breakeven stop: 100% WR on 13 trades, locking real profit
- Lower exposure (37.8% vs 45.4%) → less capital at risk

**What X5 sacrifices:**
- CAGR: -13.3% to -17.1% — massive return reduction
- Sharpe: -0.04 (small but consistent)
- Total PnL: $123K vs $243K (roughly halved)
- Bootstrap Sharpe/CAGR: X0 wins ~60% of paths

**Root cause of underperformance:**
Trend-following alpha is fat-tailed — a few big winners drive most of the total return. Selling 25-50% of position early caps the upside of exactly those trades. The profit "locked in" by TP1/TP2 is less than the profit "left on the table" by reducing position size during the strongest trends.

**Classification**: Valid alternative risk/return profile (lower MDD, lower CAGR), NOT a replacement for X0. Same structural conclusion as SM and LATCH variants.

## 8. Files

| File | Description |
|------|-------------|
| `strategies/vtrend_x5/strategy.py` | Strategy implementation (4-state machine) |
| `configs/vtrend_x5/vtrend_x5_default.yaml` | Default configuration |
| `research/x5/benchmark.py` | Full benchmark (T1-T4) |
| `research/x5/test_x5.py` | 27 unit tests (all pass) |
| `research/x5/x5_results.json` | Complete results |
| `research/x5/x5_backtest_table.csv` | Backtest comparison table |
| `research/x5/x5_bootstrap_table.csv` | Bootstrap statistics |
| `research/x5/x5_delta_table.csv` | Delta table (X5 − X0) |
