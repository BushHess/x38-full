# Delay Sharpe Degradation

**Figure**: `delay_sharpe_degradation.png`

## What it shows

Sharpe ratio as a function of entry delay (0 to 4 H4 bars), for all 6 candidates overlaid.

## Key observations

- Two distinct groups: binary strategies (E0, E5, E0_plus, E5_plus) degrade steeply and convexly; vol-target strategies (SM, LATCH) remain nearly flat.
- E5_plus_EMA1D21 has the steepest decline: from 1.270 (D0) to 0.753 (D4), losing 40.7% of Sharpe.
- E0 is the most delay-resilient binary strategy: from 1.138 (D0) to 0.802 (D4), losing 29.5%.
- SM/LATCH show a slight improvement at D1 (+0.033), then degrade linearly to -0.033 at D4.
- Binary candidates lose 13-17% of trades at D4; SM/LATCH lose zero trades.

## Interpretation

Entry timing is the dominant operational fragility axis for binary strategies. The convex shape means that the first bar of delay costs little, but each additional bar costs disproportionately more. Higher-performing binary variants are more delay-sensitive (perfect inverse correlation between baseline Sharpe and delay robustness).
