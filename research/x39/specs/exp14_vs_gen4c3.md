# Exp 14: E5-ema21D1 vs Gen4 C3 Head-to-Head

## Status: DONE

## Hypothesis
Gen4 C3 (btcsd_20260318_c3_trade4h15m) is gen4's champion strategy.
It uses completely different features: D1 trade surprise + H4 rangepos + 15m relvol.
Never compared head-to-head with E5-ema21D1 using SAME data and cost model.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Gen4 C3 Specification
From x37/resource/gen4/state_pack_v1:
```
Entry (ALL must be true):
  1. d1_trade_surprise168 > 0  (D1 participation permission)
  2. h4_rangepos168 > entry_thresh  (H4 trend context)
  3. m15_relvol168 > relvol_thresh  (15m activity timing)

Exit:
  h4_rangepos168 < hold_thresh  (H4 range position drops)

Position: 100% long or 100% flat
Cost: 50 bps RT (for comparison)
```

Champion config (cfg_025):
- entry_thresh: 0.55, hold_thresh: 0.35, relvol_thresh: 1.10

## E5-ema21D1 (reference)
Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## What to compare
Run BOTH strategies on same data (2019-01-01 to 2026-02-20, warmup=365).
Same cost (50 bps RT harsh).

Metrics: Sharpe, CAGR, MDD, trades, win rate, exposure, Calmar.
Regime breakdown: bull (2020-2021), bear (2022), recovery (2023-2024), recent (2025-2026).

## Implementation notes
- Gen4 C3 needs 15m data for m15_relvol168. Check if 15m bars are available in dataset.
  If not, this experiment uses H4-only variant (drop 15m timing, use only D1+H4).
- Gen4 C3 trade_surprise needs fitted model. Use same approach as exp04.
- Gen4 C3 has NO trail stop. Exit is purely rangepos < hold_thresh.
  This is a fundamental architectural difference from E5.

## Output
- Script: x39/experiments/exp14_vs_gen4c3.py
- Results: x39/results/exp14_results.csv

## Result

**E5 DOMINATES**: higher Sharpe AND lower MDD. C3 wins only on bear-market drawdown.

### Full-period comparison (2019-01-01 → 2026-02-20, 50 bps RT)

| Metric       | E5-ema21D1 | Gen4 C3 | Delta   | Winner |
|-------------|-----------|---------|---------|--------|
| Sharpe      | 1.40      | 0.86    | -0.54   | E5     |
| CAGR %      | 61.6      | 30.2    | -31.4pp | E5     |
| MDD %       | 40.0      | 41.9    | +1.9pp  | E5     |
| Calmar      | 1.54      | 0.72    | -0.82   | E5     |
| Trades      | 188       | 110     | -78     |        |
| Win Rate %  | 42.0      | 50.0    | +8.0    | C3     |
| Avg Win %   | 10.07     | 9.26    | -0.81   | E5     |
| Avg Loss %  | -3.24     | -4.52   | -1.28   | E5     |
| Exposure %  | 44.5      | 40.7    | -3.8    |        |
| Equity      | $307,876  | $65,811 |         | E5     |

### Regime breakdown

| Regime            | E5 Sharpe | C3 Sharpe | E5 CAGR  | C3 CAGR  | E5 MDD | C3 MDD |
|-------------------|----------|----------|----------|----------|--------|--------|
| Bull 2020-2021    | 2.239    | 1.524    | 181.0%   | 94.4%    | 25.0%  | 37.0%  |
| Bear 2022         | -1.178   | -0.249   | -25.7%   | -7.7%    | 32.6%  | 22.1%  |
| Recovery 2023-24  | 1.495    | 0.843    | 61.8%    | 25.9%    | 31.6%  | 37.5%  |
| Recent 2025-26    | 0.098    | -1.725   | -0.1%    | -28.2%   | 15.6%  | 34.6%  |

### Key observations
1. E5 wins 3/4 regimes on Sharpe. C3 only wins bear 2022 (Sh -0.25 vs -1.18).
2. C3's bear-market advantage (MDD 22% vs 33%) comes from fewer trades and faster exits
   via rangepos dropping. But this same mechanism hurts in trending markets.
3. C3's higher win rate (50% vs 42%) offset by smaller avg win (9.3% vs 10.1%)
   — no trail stop means C3 exits trends earlier via rangepos hold threshold.
4. E5's trail stop is the key differentiator: captures large trend moves that C3 misses.
5. C3's 15m timing layer adds decision frequency but not alpha.
6. Recent regime (2025-26): both struggle, but C3 significantly worse (Sh -1.73 vs +0.10).
