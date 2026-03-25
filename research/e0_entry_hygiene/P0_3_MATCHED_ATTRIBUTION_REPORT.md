# P0.3 Matched-Trade Attribution

## Scope

- Pairs: `X0 -> X0_CHOP_STRETCH18`, `X0_E5EXIT -> X0E5_CHOP_STRETCH18`
- Source artifact: `p0_1_trade_table.csv` (harsh scenario)
- Direct gate rule: `entry_context == chop and entry_price_to_slow_atr > 1.8`

## Findings

- `X0_CHOP_STRETCH18` vs `X0`: total delta +133022.73 USD, matched +89591.37 USD, direct-gate avoided +36269.82 USD, sequence-removed +4513.33 USD, candidate-only +2648.21 USD
  matched exits: improved=49, worsened=62, earlier=0, same=116, later=0, same_return=116, changed_return=0
- `X0E5_CHOP_STRETCH18` vs `X0_E5EXIT`: total delta +48779.12 USD, matched +43744.27 USD, direct-gate avoided +18140.05 USD, sequence-removed +5910.98 USD, candidate-only -19016.18 USD
  matched exits: improved=53, worsened=68, earlier=0, same=128, later=0, same_return=128, changed_return=0

## Interpretation

- In both pairs, all matched trades have the same exit timestamp and the same return. That means the matched channel is not `better exits`; it is capital-path carry on later shared trades.
- The true root mechanism is: remove a weak over-stretched chop cohort, preserve capital, then compound larger on later trades that both variants still take.
- On `X0`, direct gate removal is economically meaningful and the later capital carry amplifies it.
- On `X0_E5EXIT`, direct gate removal is smaller, but the preserved-capital carry on later shared trades is still large enough to improve the family.
- The next branch should validate whether this capital-path effect survives harsher validation, not add more entry filters.
