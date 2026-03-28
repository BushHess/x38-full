# Exp 23: Rangepos Lookback Robustness

## Status: DONE

## Hypothesis
Exp12 used rangepos_84 with threshold 0.25 as supplementary exit and achieved
+0.046 Sharpe, −6.37 pp MDD. But why 84 bars specifically?

The 84-bar lookback (= 14 days on H4) was inherited from the Gen4 research
where rangepos_84 showed the strongest continuation signal (t=12.54). However,
that was for ENTRY prediction. For EXIT timing, the optimal lookback could be
different — shorter lookbacks react faster (catching drops sooner but more noise),
longer lookbacks are smoother (fewer false alarms but slower to react).

This experiment tests exp12's rangepos exit across multiple lookback windows
to determine:
1. Is 84 optimal or was it arbitrary? (local peak vs plateau)
2. If a plateau exists across lookbacks → the mechanism is robust
3. If 84 is a sharp peak → the mechanism is fragile / overfit to that window

This is a ROBUSTNESS CHECK, not a new mechanism. It validates the foundation
before exp19/exp20/exp22 build on rangepos.

## Baseline
E5-ema21D1: Sharpe 1.4545, CAGR 61.60%, MDD 40.97%, 188 trades, 50 bps RT.

## Feature
```
# Parameterized lookback:
rolling_high_L[i] = max(high[i-L+1:i+1])
rolling_low_L[i]  = min(low[i-L+1:i+1])
rangepos_L[i] = (close[i] - rolling_low_L[i]) / (rolling_high_L[i] - rolling_low_L[i])

# L values to test:
# 42  = 7 days  (fast, responsive)
# 63  = 10.5 days
# 84  = 14 days (exp12 value)
# 126 = 21 days
# 168 = 28 days (slow, smooth)
```

## Modification to E5-ema21D1
Entry logic UNCHANGED.
Exit — ADD rangepos_L condition (same as exp12, varying L):
```python
# Original: close < trail_stop OR ema_fast < ema_slow
# Modified: close < trail_stop OR ema_fast < ema_slow OR rangepos_L < threshold
```

## Parameter sweep
Two-dimensional sweep: lookback × threshold.

- lookback L in [42, 63, 84, 126, 168]
- threshold in [0.15, 0.20, 0.25, 0.30]

Total: 5 × 4 = 20 configs + 1 baseline = 21 runs.

Note: L=84, threshold=0.25 is the exp12 optimum — results should reproduce.

## What to measure
For each config AND baseline:
- Sharpe, CAGR%, MDD%, trade count, win rate, exposure%
- Delta vs baseline for Sharpe, CAGR, MDD
- Exit count triggered by rangepos (how reactive is each lookback?)

Key analysis (AFTER collecting all results):
1. **Lookback sensitivity**: at fixed threshold=0.25, plot Sharpe vs L.
   - Plateau (L=63-126 similar) → robust mechanism
   - Sharp peak at L=84 → fragile, possibly overfit
2. **Threshold sensitivity per lookback**: does optimal threshold shift with L?
   - Shorter L → lower threshold needed (more volatile rangepos)
   - If threshold scales predictably with L → systematic relationship
3. **Best overall config**: which (L, threshold) pair maximizes Sharpe?
   Does it differ from (84, 0.25)?

## Implementation notes
- Compute rangepos for each lookback separately (not from explore.py which
  only computes L=84 and L=168). Add L=42, 63, 126 on the fly.
- rolling_high and rolling_low use pandas rolling or manual loop
- For L=42 and L=63, rangepos will be more volatile — expect more exit triggers
  and potentially more churn (lower threshold may be needed to compensate)
- Data: bars_btcusdt_2016_now_h1_4h_1d.csv
- Cost: 50 bps RT (harsh)
- Warmup: 365 days

## Output
- Script: x39/experiments/exp23_rangepos_lookback_robustness.py
- Results: x39/results/exp23_results.csv

## Result

**Verdict: FRAGILE** — rangepos exit performance depends heavily on lookback choice.
L=84 is a sharp peak, not part of a plateau.

### Exp12 reproduction
L=84, thr=0.25: Sharpe 1.3427 (+0.0462), MDD 44.95% (-6.37 pp) — **confirmed**.

### Lookback sensitivity at threshold=0.25
| L   | Sharpe | d_Sharpe | MDD%  | d_MDD  | RP exits |
|-----|--------|----------|-------|--------|----------|
| 42  | 1.1902 | -0.1063  | 49.94 | -1.38  | 156      |
| 63  | 1.2716 | -0.0249  | 49.09 | -2.23  | 90       |
| 84  | 1.3427 | +0.0462  | 44.95 | -6.37  | 35       |
| 126 | 1.2771 | -0.0194  | 54.78 | +3.46  | 13       |
| 168 | 1.2766 | -0.0199  | 52.69 | +1.37  | 8        |

Sharpe range = 0.1525 across lookbacks — far above 0.05 plateau threshold.
Only L=84 beats baseline on Sharpe. L=126/168 barely trigger (<15 exits).

### Best overall configs
- **Best Sharpe**: L=84, thr=0.25 → Sh 1.3427 (+0.0462), MDD 44.95% (-6.37)
- **Best MDD**: L=84, thr=0.20 → MDD 44.24% (-7.08), Sh 1.3390 (+0.0425)
- 5/20 configs improve BOTH Sharpe AND MDD (all at L=63 or L=84)

### Threshold sensitivity per lookback
| L   | Best thr | Best Sh | Worst Sh | Sh range |
|-----|----------|---------|----------|----------|
| 42  | 0.15     | 1.2910  | 1.0998   | 0.1912   |
| 63  | 0.15     | 1.3274  | 1.1454   | 0.1820   |
| 84  | 0.25     | 1.3427  | 1.2559   | 0.0868   |
| 126 | 0.20     | 1.2954  | 1.2336   | 0.0618   |
| 168 | 0.20     | 1.2847  | 1.2766   | 0.0081   |

Shorter lookbacks are MORE sensitive to threshold (higher Sh range).
Optimal threshold shifts: L=42/63 prefer thr=0.15, L=84 prefers 0.25, L=126/168 prefer 0.20.

### Key findings
1. **L=84 is a sharp optimum, not a plateau.** Moving to L=63 or L=126 at thr=0.25
   loses all Sharpe improvement. This is a fragility signal.
2. **Shorter lookbacks (42, 63) trigger too many exits** — L=42 at thr=0.30 fires 211
   rangepos exits (56% of all exits), destroying trend-following alpha via churn.
3. **Longer lookbacks (126, 168) are near-inert** — too few triggers to matter
   (1-14 exits). Rangepos becomes decoration, not mechanism.
4. **L=84 sweet spot**: enough triggers to help (9-68 exits), not so many as to churn.
   This is likely because 84 bars = 14 days ≈ half a typical BTC swing cycle.
5. **L=84, thr=0.20 is arguably better** than thr=0.25: slightly lower Sharpe
   (1.3390 vs 1.3427) but better MDD (44.24% vs 44.95%). Tradeoff, not dominance.
