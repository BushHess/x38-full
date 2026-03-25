# X35 Phase 1 Regime Decomposition

## Baseline

- Strategy: `VTrendE5Ema21D1Strategy`
- Trades: `188`
- Sharpe: `1.4545`
- CAGR %: `61.6`
- MDD %: `40.97`
- Study verdict: `NO_GO_CURRENT_MENU`

## Candidate Summary

| Spec | Risk-on % | Flips/yr | Median spell days | On trades | Off trades | On mean % | Off mean % | Profit on % | Loss off % | Fold WR % | Advance |
|------|-----------|----------|-------------------|-----------|------------|-----------|------------|-------------|------------|-----------|---------|
| `wk_ema13_above_ema26` | 68.98 | 1.401 | 131.0 | 133 | 55 | 2.5062 | 1.9348 | 81.57 | 28.25 | 33.33 | False |
| `wk_close_above_ema26` | 63.34 | 3.923 | 49.0 | 139 | 49 | 2.5747 | 1.6707 | 80.06 | 22.97 | 57.14 | False |
| `mo_close_above_ema6` | 65.34 | 2.802 | 83.0 | 131 | 57 | 2.2579 | 2.5257 | 75.07 | 24.5 | 28.57 | False |

## Gate Detail

### `wk_ema13_above_ema26`

- D0_warmup: PASS
- D1_persistence: PASS
- D2_trade_split: PASS
- D3_sign_separation: FAIL
- D4_concentration: FAIL
- D5_stability: FAIL

### `wk_close_above_ema26`

- D0_warmup: PASS
- D1_persistence: PASS
- D2_trade_split: PASS
- D3_sign_separation: FAIL
- D4_concentration: FAIL
- D5_stability: FAIL

### `mo_close_above_ema6`

- D0_warmup: PASS
- D1_persistence: PASS
- D2_trade_split: PASS
- D3_sign_separation: FAIL
- D4_concentration: FAIL
- D5_stability: FAIL

