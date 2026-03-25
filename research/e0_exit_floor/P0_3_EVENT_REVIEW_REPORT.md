# P0.3 Exit-Floor Event Review

## Scope

- Pair: `X0_E5EXIT -> X0E5_FLOOR_LATCH`
- Source artifact: `p0_1_trade_table.csv` (harsh scenario)

## Findings

- Total PnL delta: `-4325.93 USD`
- Matched-trade delta: `-90337.06 USD`
- Reference-only sequencing delta: `-17.62 USD`
- Candidate-only sequencing delta: `+86028.75 USD`
- Matched trades improved / worsened / same: `88` / `83` / `16`
- Candidate earlier / later / same exit: `23` / `0` / `164`
- Floor-exit matched improvements / worsens: `33` / `19`
- Top 5 positive matched contributors explain `-559.00%` of total delta

## Interpretation

- The main uplift does not come from better matched exits. Matched-trade delta is negative, while candidate-only sequencing is strongly positive.
- Economically, this means the candidate gives up money on many shared trades, then earns it back through altered capital path and later re-entries.
- Positive attribution is not overly concentrated across events.
- The candidate mostly differs by exiting earlier, which is consistent with the intended floor-exit mechanism.
- Read together with weak WFO breadth, this pattern supports `research-only`, not promotion.
