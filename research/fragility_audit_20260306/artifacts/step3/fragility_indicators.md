# Fragility Indicators Dashboard

**Figure**: `fragility_indicators.png`

## What it shows

Multi-panel composite dashboard showing all three fragility dimensions for all 6 candidates:
- Random miss K=1 Sharpe CV (%)
- Outage 168h worst-case Sharpe
- Delay D4 delta Sharpe

## Key observations

- **Random miss**: SM/LATCH have ~5x higher CV than binary strategies. All are low in absolute terms.
- **Outage**: Binary strategies cluster at 1.07-1.20 worst Sharpe; SM/LATCH cluster at 0.74-0.75.
- **Delay**: The dominant differentiator. Binary strategies range -0.336 to -0.517; SM/LATCH are at -0.033.
- E5_plus has the best random-miss and outage metrics but the worst delay metric.
- SM and LATCH are nearly identical on all three dimensions.

## Interpretation

The three fragility axes expose a fundamental tradeoff: binary strategies with higher baseline performance are more sensitive to entry timing, while vol-target strategies with lower baseline performance are operationally robust across all dimensions. No candidate dominates all three axes simultaneously.
