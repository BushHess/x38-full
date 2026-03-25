# X35 Mid-Trade Hazard Scan

## Baseline

- Strategy: `VTrendE5Ema21D1Strategy`
- Trades: `188`
- Sharpe: `1.4545`
- CAGR %: `61.6`
- MDD %: `40.97`
- Branch verdict: `NO_GO_MID_TRADE_HAZARD_FAMILY`

## Spec Summary

| Spec | Eligible | Hits | Coverage % | Median bars saved | Loser mean edge % | Winner mean edge % | Selectivity | Top20 hits | Promising |
|------|----------|------|------------|-------------------|-------------------|--------------------|-------------|------------|-----------|
| `wk_mixed_structure_flag` | 133 | 3 | 1.6 | 37.0 | 3.251 | -2.4057 | 1.3514 | 1 | False |
| `wk_flip_count_8w_ge_2` | 145 | 5 | 2.66 | 10.0 | 4.3713 | 0.7773 | 0.0 | 1 | False |
| `wk_score_range_8w_ge_2` | 168 | 3 | 1.6 | 12.0 | 0.0 | 5.4336 | 0.0 | 1 | False |

## Gate Detail

### `wk_mixed_structure_flag`

- G1_coverage: FAIL
- G2_timing: PASS
- G3_loser_benefit: PASS
- G4_winner_cost: PASS
- G5_selectivity: FAIL
- G6_top20_damage: PASS

### `wk_flip_count_8w_ge_2`

- G1_coverage: FAIL
- G2_timing: PASS
- G3_loser_benefit: PASS
- G4_winner_cost: FAIL
- G5_selectivity: FAIL
- G6_top20_damage: PASS

### `wk_score_range_8w_ge_2`

- G1_coverage: FAIL
- G2_timing: PASS
- G3_loser_benefit: FAIL
- G4_winner_cost: FAIL
- G5_selectivity: FAIL
- G6_top20_damage: PASS

