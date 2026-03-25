# P0.2 Stretch Gate Attribution

## Rule

- `entry_context == chop and entry_price_to_slow_atr > 1.8`

## Key Findings

- `X0` blocked cohort: 52 trades, net PnL -32849.77 USD, win rate 25.0%
- `X0` kept cohort: 122 trades, net PnL 269042.51 USD, win rate 46.7%
- `X0_E5EXIT` blocked cohort: 56 trades, net PnL -10549.89 USD, win rate 32.1%
- `X0_E5EXIT` kept cohort: 132 trades, net PnL 308340.36 USD, win rate 46.2%

## Interpretation

- On `X0`, the stretch gate is clearly filtering a weak cohort: blocked trades are negative-PnL, lower quality, and show worse early excursion.
- On `X0_E5EXIT`, the same blocked cohort is only marginally positive, which implies the robust exit already repairs part of the damage from over-stretched chop entries.
- This supports a concrete next question: does the stretch gate still add value after robust exit because it removes a weak residual cohort, or because it changes later trade sequencing?

