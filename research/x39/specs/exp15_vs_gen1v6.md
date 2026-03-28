# Exp 15: E5-ema21D1 vs Gen1 V6 Head-to-Head

## Status: DONE

## Hypothesis
Gen1 V6 (S3_H4_RET168_Z0) is gen1's frozen winner. Extremely simple:
ret_168 > 0 → long, else flat. One feature, one threshold.
Compare with E5-ema21D1 on same data, same cost.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Gen1 V6 Specification
From x37/resource/gen1/v6_ret168/spec:
```
Feature: ret168 = close_t / close_(t-168) - 1
Signal:  long if ret168 > 0, else flat
Entry:   signal changes 0→1 at close → buy at next open
Exit:    signal changes 1→0 at close → sell at next open
Position: 100% long or 100% flat
Cost: 20 bps RT (gen1 default) — BUT run at 50 bps for fair comparison
```
No trail stop. No VDO. No D1 regime. Just one momentum quantity.

## E5-ema21D1 (reference)
Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## What to compare
Run BOTH on same data (2019-01-01 to 2026-02-20, warmup=365).
Same cost (50 bps RT).

Metrics: Sharpe, CAGR, MDD, trades, win rate, exposure, Calmar.
Regime breakdown.

Gen1 V6 caveat: reserve CAGR was -5.75% in gen1's own test.
This experiment re-runs on full data to see current picture.

## Implementation notes
- Trivially simple to implement
- ret_168 needs 168 H4 bars warmup
- No trail stop = potentially much worse drawdowns
- Fewer parameters = less overfitting risk

## Output
- Script: x39/experiments/exp15_vs_gen1v6.py
- Results: x39/results/exp15_results.csv

## Result

**E5 DOMINATES**: higher Sharpe AND lower MDD. V6's simplicity does not compensate.

### Full-period comparison (2019-01-01 → 2026-02-20, 50 bps RT)

| Metric       | E5-ema21D1 | Gen1 V6 | Delta    | Winner |
|-------------|-----------|---------|----------|--------|
| Sharpe      | 1.40      | 1.04    | -0.36    | E5     |
| CAGR %      | 61.6      | 45.3    | -16.3pp  | E5     |
| MDD %       | 40.0      | 59.7    | +19.8pp  | E5     |
| Calmar      | 1.54      | 0.76    | -0.78    | E5     |
| Trades      | 188       | 243     | +55      |        |
| Win Rate %  | 42.0      | 25.5    | -16.5    | E5     |
| Avg Win %   | 10.07     | 13.80   | +3.73    | V6     |
| Avg Loss %  | -3.24     | -2.08   | +1.16    | V6     |
| Exposure %  | 44.5      | 56.1    | +11.6    |        |
| Equity      | $307,876  | $144,129|          | E5     |

### Regime breakdown

| Regime            | E5 Sharpe | V6 Sharpe | E5 CAGR  | V6 CAGR  | E5 MDD | V6 MDD |
|-------------------|----------|----------|----------|----------|--------|--------|
| Bull 2020-2021    | 2.239    | 2.450    | 181.0%   | 232.0%   | 25.0%  | 32.4%  |
| Bear 2022         | -1.178   | -1.487   | -25.7%   | -43.6%   | 32.6%  | 45.3%  |
| Recovery 2023-24  | 1.495    | 1.345    | 61.8%    | 59.8%    | 31.6%  | 50.8%  |
| Recent 2025-26    | 0.098    | -1.121   | -0.1%    | -27.0%   | 15.6%  | 31.7%  |

### Key observations
1. E5 wins 3/4 regimes on Sharpe. V6 only wins bull 2020-2021 (Sh 2.45 vs 2.24, CAGR 232% vs 181%).
2. V6's MDD is catastrophic: 59.7% vs 40.0%. No trail stop = rides drawdowns all the way down.
3. V6 has 56% exposure vs E5's 44.5% — longer time in market, more drawdown exposure.
4. V6 win rate 25.5% vs 42.0% — 3/4 trades lose. Avg win is larger (13.8% vs 10.1%) but not enough.
5. V6's simplicity (1 param vs 4) does NOT translate to better robustness — just worse risk management.
6. Bear 2022: V6 much worse (Sh -1.49, MDD 45%) — ret_168 stays positive too long during crashes.
7. V6 gen1 reserve CAGR was -5.75%; full-sample here looks better but still dominated by E5.
