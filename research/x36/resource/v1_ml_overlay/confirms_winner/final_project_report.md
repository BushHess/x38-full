# Final Project Report

## 1. Final verdict reconciliation

### 1.1 Legacy branch result
Legacy binary recursive suppress branch:
- classifier signal existed
- actuator verdict = `REJECT`
- failure mode = recursive closed-loop deployment, score saturation, trade-state OOD drift

### 1.2 New bounded branch result
Bounded branch:
- verdict = `PROMOTE_GATED`
- winner candidate = `delay_H16_p70`
- family = `DelayExit_H`
- parameters = `H=16`, `threshold_percentile=70`

### 1.3 Final project verdict
The project does **not** end in universal failure.
The project ends with:
- legacy branch rejected
- bounded branch promoted
- final winner = `delay_H16_p70`

## 2. Why the legacy branch was rejected

Key frozen facts:
- classifier signal quality existed on baseline trail-stop episodes
- the legacy binary recursive suppress actuator failed because deployment semantics were wrong for the signal
- frozen failure mode:
  - recursive closed-loop deployment
  - score saturation
  - trade-state OOD drift
  - near-always-hold behavior

## 3. Why the bounded branch was promoted

Winner:
- `candidate_id = delay_H16_p70`
- `family = DelayExit_H`
- `H = 16`
- `threshold_percentile = 70`

Frozen validation summary:
- aggregate WFO OOS Sharpe @25bps = `1.185394667931`
- aggregate WFO OOS MDD = `-0.358168394543`
- WFO positive folds = `3/4`
- bootstrap `P(ΔSharpe > 0)` = `0.742`
- cost levels beaten = `9/9`
- exposure trap passed = `True`
- added-value gate passed = `True`

## 4. Deterministic deployment freeze

### 4.1 Winner mechanism
- candidate_id = `delay_H16_p70`
- family = `DelayExit_H`
- continuation keeps 100% notional
- forced expiry = open of bar `j + 16`
- trend exit override remains active
- recursive rescoring forbidden

### 4.2 Frozen deployment threshold
- percentile method = `numpy.quantile(..., method="linear")`
- frozen deployment threshold value = `0.7576656445740457`

Threshold reconciliation:
- recomputed deployment p70 = `0.7576656445740457`
- frozen Phase B3 p70 = `0.7576656445740457`
- exact match within tolerance `<= 1e-15` = `True`

### 4.3 Frozen score source
- model family = `elastic_net_logistic_regression`
- label = `churn_signal20`
- features = `d1_regime_strength, ema_gap_pct, holding_bars_to_exit_signal, return_from_entry_to_signal, peak_runup_from_entry, atr_percentile_100`
- hyperparameters fixed exactly as frozen
- scaler = `StandardScaler`
- runtime scoring formula frozen numerically in `final_deployment_freeze_spec.json`

## 5. Implementation and operational next steps

Implementation should begin only through:
1. deterministic replay tests
2. shadow / paper trading

No further experimental phases are authorized under the current charter.
