# Exp 16: Hybrid — Gen4 C3 Entry + E5 Exit

## Status: DONE

## Hypothesis
Gen4 C3 has potentially better entry logic (trade surprise + rangepos).
E5 has proven exit logic (robust ATR trail + EMA cross-down).
Gen4 C3's weakness: no trail stop, exits only on rangepos drop.
Combine: use Gen4's entry conditions but E5's exit mechanism.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Hybrid Specification
```python
# Entry (Gen4 C3 style):
#   trade_surprise_168 > 0
#   AND rangepos_168 > entry_thresh
#   AND d1_regime_ok  (keep E5's D1 EMA(21) for regime)

# Exit (E5 style):
#   close < peak - 3.0 * robust_atr
#   OR ema_fast < ema_slow
```

## Parameter sweep
- entry_thresh in [0.50, 0.55, 0.65]
- (3 configs. Trail + EMA exit are fixed from E5.)

## What to measure
Sharpe, CAGR%, MDD%, trades, win rate, exposure%. Delta vs E5 baseline.
Also compare vs pure Gen4 C3 (exp14) and pure E5.

## Implementation notes
- Combines compute from both systems
- trade_surprise_168 needs linear regression fit (causal, first 2000 bars)
- rangepos_168 needs rolling 168-bar high/low
- EMA fast/slow and robust ATR computed as usual for exit
- D1 EMA(21) regime kept from E5 (Gen4 C3 uses D1 trade surprise instead,
  but keeping E5's D1 filter for cleaner comparison)

## Output
- Script: x39/experiments/exp16_hybrid_gen4_e5.py
- Results: x39/results/exp16_results.csv

## Result

**FAIL**: No hybrid config improves Sharpe over E5 baseline.

| config      | sharpe | cagr%  | mdd%   | trades | win_rate | exposure% | d_sharpe | d_cagr | d_mdd |
|-------------|--------|--------|--------|--------|----------|-----------|----------|--------|-------|
| baseline    | 1.3322 | 60.04  | 51.32  | 219    | 41.6%    | 43.0%     | —        | —      | —     |
| thresh=0.50 | 1.1194 | 43.19  | 54.51  | 184    | 40.8%    | 37.8%     | -0.2128  | -16.85 | +3.19 |
| thresh=0.55 | 1.1931 | 47.19  | 52.28  | 175    | 42.3%    | 37.2%     | -0.1391  | -12.85 | +0.96 |
| thresh=0.65 | 1.1244 | 42.19  | 54.85  | 160    | 45.0%    | 34.9%     | -0.2078  | -17.85 | +3.53 |

**Reference**: Gen4 C3 (pure): Sharpe 0.8569, CAGR 30.2%, MDD 41.86%, 110 trades.

### Interpretation
- All 3 hybrid configs degrade BOTH Sharpe AND MDD vs E5 baseline.
- Best hybrid (thresh=0.55) still loses -0.14 Sharpe, -12.9% CAGR, +1.0 pp MDD.
- C3 entry filters reduce trades by 20-27% but cut too many winners.
- E5 exit rescues C3 entry (+0.34 Sharpe vs pure C3), confirming exit > entry in value.
- **Conclusion**: Gen4 C3 entry conditions are strictly inferior to E5's EMA+VDO entry.
  The trade_surprise + rangepos gate adds noise, not signal, on top of E5.
