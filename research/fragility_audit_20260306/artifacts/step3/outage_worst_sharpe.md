# Outage Worst-Case Sharpe

**Figure**: `outage_worst_sharpe.png`

## What it shows

Worst-case Sharpe ratio from the outage-window sweep at {24, 72, 168} hour durations, for all 6 candidates.

## Key observations

- Binary strategies (E0, E5, E0_plus, E5_plus) have worst-case Sharpe > 1.0 even at 168h. Their absolute performance remains strong under worst-case outage.
- SM/LATCH have worst-case Sharpe of 0.739/0.750 at 168h, a 9.1-9.4% degradation from baseline.
- E5 and E5_plus show identical worst-case at 72h and 168h (1.160 and 1.199), suggesting the same critical entry window drives both.
- Degradation scales sub-linearly with window duration: going from 24h to 168h (7x wider) only doubles the degradation.

## Interpretation

Single-week outages cause moderate but bounded degradation. No candidate drops below Sharpe 0.7 in any scenario. The outage impact is much smaller than the delay impact, confirming that missing entries entirely is less damaging than entering late (because late entries capture adverse momentum that erodes returns).
