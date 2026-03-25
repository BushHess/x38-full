# X35 Transition / Instability Scan

## Baseline

- Strategy: `VTrendE5Ema21D1Strategy`
- Trades: `188`
- Sharpe: `1.4545`
- CAGR %: `61.6`
- MDD %: `40.97`
- Warmup weeks before report: `52`
- Branch verdict: `NO_GO_F4_TRANSITION_FAMILY`

## Spec Summary

| Spec | Unstable % | Flips/yr | Median spell days | Stable trades | Unstable trades | Stable mean % | Unstable mean % | Profit stable % | Loss unstable % | Fold WR % | Promising |
|------|------------|----------|-------------------|---------------|-----------------|---------------|-----------------|-----------------|-----------------|-----------|-----------|
| `wk_mixed_structure_flag` | 34.62 | 4.483 | 42.0 | 133 | 55 | 2.2819 | 2.4773 | 76.69 | 30.48 | 50.0 | False |
| `wk_flip_count_8w_ge_2` | 24.69 | 3.362 | 63.0 | 145 | 43 | 2.7134 | 1.0769 | 88.97 | 15.43 | 100.0 | False |
| `wk_score_range_8w_ge_2` | 11.0 | 2.522 | 35.0 | 168 | 20 | 2.5022 | 0.9688 | 97.7 | 4.8 | 100.0 | False |

## Gate Detail

### `wk_mixed_structure_flag`

- D0_warmup: PASS
- D1_persistence: PASS
- D2_trade_split: PASS
- D3_sign_separation: FAIL
- D4_concentration: FAIL
- D5_stability: FAIL

### `wk_flip_count_8w_ge_2`

- D0_warmup: PASS
- D1_persistence: PASS
- D2_trade_split: PASS
- D3_sign_separation: FAIL
- D4_concentration: FAIL
- D5_stability: FAIL

### `wk_score_range_8w_ge_2`

- D0_warmup: PASS
- D1_persistence: PASS
- D2_trade_split: PASS
- D3_sign_separation: FAIL
- D4_concentration: FAIL
- D5_stability: FAIL

