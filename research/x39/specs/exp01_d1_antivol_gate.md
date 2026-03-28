# Exp 01: D1 Anti-Vol Entry Gate

## Status: DONE

## Hypothesis
Low D1 volatility (orderly market) predicts higher returns at ALL horizons
(x39 residual: 4/5 horizons significant, rho +0.03 to +0.09).
Adding a D1 anti-vol gate to E5-ema21D1 entry should filter out entries
during chaotic high-vol periods and improve risk-adjusted returns.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
d1_range_pct[i] = (d1_high[i] - d1_low[i]) / d1_close[i]
d1_rangevol_84[i] = rolling_mean(d1_range_pct, 84)
d1_rangevol84_rank365[i] = percentile_rank(d1_rangevol_84[i], within trailing 365 D1 bars)
```
Low rank = low volatility relative to recent history = orderly market.

## Modification to E5-ema21D1
Entry condition ADDS one gate:
```python
# Original: ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok
# Modified: ema_fast > ema_slow AND vdo > 0 AND d1_regime_ok AND d1_rangevol84_rank365 < threshold
```
Exit logic UNCHANGED.

## Parameter sweep
- threshold in [0.30, 0.40, 0.50, 0.60, 0.70]
- (5 configs total)

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, avg win, avg loss, exposure %
- Delta vs baseline for Sharpe, CAGR, MDD

## Implementation notes
- Use x39/explore.py's compute_features() to get d1_rangevol84_rank365 array
- Modify replay_trades() to add the gate
- Map D1 feature to H4 using map_d1_to_h4() (already in explore.py)
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: skip first 365 D1 bars (rank needs 365 history)

## Output
- Script: x39/experiments/exp01_d1_antivol_gate.py
- Results table: print to terminal + save to x39/results/exp01_results.csv
- Write verdict back to this file

## Result

**Verdict: MIXED — marginal Sharpe gain, large CAGR cost.**

Warmup bar 2195 (first valid rank365). Baseline from same warmup window.

| threshold | Sharpe | CAGR% | MDD% | trades | win_rate | exposure% | d_Sharpe | d_CAGR | d_MDD |
|-----------|--------|-------|------|--------|----------|-----------|----------|--------|-------|
| baseline  | 1.3100 | 52.72 | 41.01| 197    | 40.6%    | 43.5%     | —        | —      | —     |
| 0.30      | 0.8771 | 19.27 | 35.05| 95     | 37.9%    | 20.8%     | -0.433   | -33.45 | -5.96 |
| 0.40      | 0.9595 | 22.77 | 33.07| 108    | 37.0%    | 23.7%     | -0.351   | -29.95 | -7.94 |
| 0.50      | 0.9253 | 23.14 | 33.07| 124    | 37.9%    | 26.7%     | -0.385   | -29.58 | -7.94 |
| 0.60      | 1.1001 | 30.71 | 33.07| 134    | 38.1%    | 29.4%     | -0.210   | -22.01 | -7.94 |
| 0.70      | 1.3481 | 43.25 | 33.07| 147    | 38.8%    | 33.1%     | +0.038   | -9.47  | -7.94 |

**Key observations:**
1. MDD improves at ALL thresholds (~-8 pp), confirming the anti-vol hypothesis for drawdown.
2. Sharpe only improves at threshold=0.70 (+0.038), marginal.
3. CAGR drops sharply at all thresholds (−9 to −33 pp) — the gate removes too much exposure.
4. Win rate does not improve — the gate blocks entries indiscriminately (winners and losers).
5. Classic filter pattern: reduces exposure → helps MDD mechanically, but no alpha improvement.

**Conclusion:** D1 anti-vol gate is a risk-reduction tool (MDD), not an alpha tool (Sharpe/CAGR).
The +0.038 Sharpe at threshold=0.70 is too small to warrant adding a parameter.
Not recommended for E5-ema21D1.
