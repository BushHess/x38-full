# Master Reproducibility Spec

**Classification:** AUTHORITATIVE  
**Status:** COMPLETE / FROZEN  
**Version:** 1.0  
**Date generated:** 2026-03-13  
**Scope:** End-to-end rebuild, replay, audit, implementation, and shadow-mode deployment of the VTREND E5+EMA21D1 project, including the rejected legacy branch and the promoted bounded branch winner.

## 1. Document control

### 1.1 Authoritative artifact bundle used
This master spec was built from the following authoritative bundle plus raw inputs:
- Raw inputs: `E5_EMA21D1_Spec.md`, `data.zip`
- Step 1 authoritative artifacts
- Legacy branch authoritative artifacts (Step 2–4)
- Bounded branch authoritative artifacts (Phase B1–B4)

The full file-level inventory is in `artifact_manifest.csv`.

### 1.2 Normative labels used in this document
- **AUTHORITATIVE**: source-of-truth, mandatory to follow
- **DERIVED**: recomputed deterministically from authoritative artifacts
- **REPORT-ONLY**: informative, not a deployment authority
- **REJECTED-BRANCH**: historical branch retained for audit but non-deployable
- **WINNING-BRANCH**: promoted bounded branch
- **DEPRECATED**: superseded artifact or logic retained for audit trail only

## 2. Executive summary

**Project goal.** Improve the decision taken exactly when the frozen Base strategy's trailing stop fires, without changing entry logic, regime filter, trailing-stop parameters, or base sizing.

**Final reconciled project outcome.**
- **REJECTED-BRANCH:** legacy recursive binary suppress branch
- **WINNING-BRANCH:** bounded one-shot continuation branch
- **Final promoted winner:** `delay_H16_p70`

**Deployable configuration.**
- Score source: frozen full-178 refit of the bounded-branch fixed elastic-net score source
- Mechanism: `DelayExit_H`
- Parameters: `H = 16`, `threshold_percentile = 70`
- Frozen numeric threshold: `0.7576656445740457`

**Explicitly rejected.**
- Legacy recursive binary suppress actuator
- Any indefinite continuation interpretation
- Any recursive rescoring while the same continued trade remains open
- Any alternative model family / feature set / threshold grid / candidate family not frozen in authoritative artifacts

## 3. Glossary and notation

- **H4**: 4-hour bar timeframe used for trading
- **D1**: daily bar timeframe used only for regime state
- **Trail-stop fire**: H4 close where `close < peak - 3.0 * RobustATR`
- **Decision point**: first trail-stop signal close since the most recent full entry fill
- **Continuation start**: scheduled baseline trail-stop exit fill open `j`
- **Forced expiry**: mandatory exit of remaining notional at open of bar `j + H`
- **Trend exit override**: full exit if trend reversal fill open occurs at or before forced expiry open
- **OOS**: out-of-sample
- **WFO**: walk-forward validation over fixed-date windows
- **ECE**: expected calibration error
- **Added-value gate**: gated candidate must beat its matched ungated baseline on aggregate WFO OOS Sharpe @25bps

## 4. Data contract

**AUTHORITATIVE raw inputs**
- `data.zip`
- `E5_EMA21D1_Spec.md`

### 4.1 Raw files
- H4 trading data: `data/btcusdt_4h.csv`
- D1 regime data: `data/btcusdt_1d.csv`

### 4.2 Time range
- Research window: `2017-08` through `2026-02`
- Step 1 froze the sample through `2026-02-28 23:59:59.999 UTC`

### 4.3 Timestamp conventions
- Raw timestamps are Unix epoch milliseconds
- Working timezone convention is UTC
- H4 bars follow the observed raw timeline; gaps are **not imputed**

### 4.4 H4 / D1 mapping rule
**AUTHORITATIVE**
- Each H4 bar inherits the latest completed D1 regime state satisfying `d1_close_time < h4_close_time`

### 4.5 Gap handling
**AUTHORITATIVE**
- Use the observed H4 timeline exactly as supplied
- Do not regularize missing bars
- Do not impute gaps
- Gap-affected windows are flagged for audit / sensitivity, not repaired

### 4.6 Warmup and event ordering
**AUTHORITATIVE**
- Warmup = first 365 calendar days
- Indicators update during warmup
- No trading during warmup
- Signal at H4 close `i` → fill at H4 open `i+1`

## 5. Base strategy spec (1:1)

**Classification:** AUTHORITATIVE

### 5.1 Instrument and position model
- BTC-USDT spot
- H4 trading timeframe
- D1 regime timeframe
- Long-only
- Binary exposure: `100% NAV` or `0%`

### 5.2 Core parameters
- `slow_period = 120`
- `fast_period = max(5, 120 // 4) = 30`
- `trail_mult = 3.0`
- `d1_ema_period = 21`
- `vdo_fast = 12`
- `vdo_slow = 28`
- `ratr_cap_q = 0.90`
- `ratr_cap_lb = 100`
- `ratr_period = 20`

### 5.3 EMA formulas
- `alpha = 2 / (period + 1)`
- `ema[0] = close[0]`
- `ema[i] = alpha * close[i] + (1 - alpha) * ema[i-1]`

### 5.4 Robust ATR formula
1. `TR[i] = max(high-low, |high-close_prev|, |low-close_prev|)`
2. For each bar with sufficient history, cap `TR[i]` at the rolling Q90 of the **prior 100 TR values**
3. Smooth capped TR with Wilder EMA(20)
4. Seed: `rATR[119] = mean(TR_capped[100:120])`

### 5.5 VDO formula
If taker-buy data is present:
- `taker_sell = volume - taker_buy`
- `vdr = (taker_buy - taker_sell) / volume`
- `VDO = EMA12(vdr) - EMA28(vdr)`

### 5.6 D1 regime rule
- `d1_ema21 = EMA(d1_close, 21)`
- `regime_ok = d1_close > d1_ema21`

### 5.7 Entry logic
Enter long only if all are true:
1. flat
2. `ema_fast > ema_slow`
3. `VDO > 0`
4. `regime_ok == True`

### 5.8 Exit logic
Exit checks are ordered:
1. **Trailing stop**
   - update `peak = max(peak, close_t)`
   - `trail_stop = peak - 3.0 * robust_atr_t`
   - exit if `close_t < trail_stop`
2. **Trend reversal**
   - exit if `ema_fast < ema_slow`

### 5.9 Base execution and cost conventions
- Signal at close, fill at next open
- No same-bar fill
- No same-bar flip
- Step 1 evaluation cost = `25 bps` round-trip = `12.5 bps` per fill side
- Step 1 reported metrics are post-warmup only

## 6. Legacy branch spec

**Classification:** REJECTED-BRANCH

### 6.1 Legacy branch label / sample / methodology
- Primary label: `churn_signal20`
- Secondary sensitivity: `churn_fill20`
- Primary sample: all `178` trail-stop episodes
- Temporal split: `119` train / `59` test
- Signal-quality gates:
  - `cv_auc_floor = 0.60`
  - `primary_oos_auc_gate = 0.62`
  - quartile monotonicity: `Q1 <= Q2 <= Q3 <= Q4` and `Q4 - Q1 >= 0.15`

### 6.2 Why classifier signal existed
Legacy Step 4 found that the best classifier had:
- best model family = `elastic_net_logistic_regression`
- OOS AUC above gate
- quartile churn monotonicity pass
- calibration imperfect but usable only through rank-based thresholds

### 6.3 Why the legacy actuator was rejected
The legacy binary recursive suppress actuator was rejected because:
- repeated trail-stop rescoring created recursive closed-loop deployment
- scores saturated near 1.0
- trade-state features drifted outside support
- exposure drifted toward near-always-long behavior

The failure mode was frozen as:
- recursive closed-loop deployment
- score saturation
- trade-state OOD drift
- near-always-hold

### 6.4 Legacy branch deployment status
**Non-deployable.**
Legacy branch artifacts are retained only to document:
- classifier signal existence
- the rejected deployment mechanism
- the exact failure mode that motivated the bounded branch

## 7. Bounded branch methodology

**Classification:** WINNING-BRANCH

### 7.1 Phase B1 axioms
Frozen from Phase B1:
- the signal is best interpreted as a **short-horizon rebound / exit-delay utility proxy**
- one-shot scoring is mandatory
- recursive rescoring is forbidden
- bounded continuation is mandatory
- only two families were admitted:
  - `DelayExit(H)`
  - `Tail(X,H)`

### 7.2 Phase B2 locks
- Score source fixed to the legacy best elastic-net classifier
- No model reselection
- No feature reselection
- Families locked:
  - `DelayExit_H` with `H in [8, 12, 16, 20]`
  - `Tail_X_H` with `X in [0.25, 0.50, 0.75]`, `H in [8, 12, 16, 20]`
- Gated thresholds locked to percentiles `[60, 70, 80]`
- Ungated baselines mandatory
- One-shot decision semantics frozen
- Live feature recomputation frozen

### 7.3 Phase B3 exploratory protocol
- Refit fixed score source on full 178 authoritative episodes
- Compute exploratory thresholds from full-178 score distribution
- Run all locked candidates + ungated baselines at 25 bps
- Rank within family
- Shortlist exactly:
  - `delay_H16_p70`
  - `delay_H16_p60`
  - `tail_X075_H16_p70`
  - `tail_X075_H16_p60`
- Mandatory comparison-only baselines:
  - `delay_H16_all`
  - `tail_X075_H16_all`

### 7.4 Phase B4 validation protocol
Validation candidate set was frozen to the 6 IDs above.
Validation gates:
- WFO pass = at least `3/4` positive folds
- bootstrap pass = `P(ΔSharpe > 0) >= 55%`
- cost pass = beats Base on at least `7/9` cost levels
- exposure trap must pass if triggered
- gated candidates must beat matched ungated baselines on aggregate WFO OOS Sharpe at 25 bps

### 7.5 Final bounded-branch verdict logic
- `PROMOTE_GATED` if a gated candidate passes all gates including added-value
- otherwise `PROMOTE_UNGATED` if an ungated candidate passes all core gates
- otherwise `REJECT`

## 8. Winning mechanism spec

**Classification:** WINNING-BRANCH

- `candidate_id = delay_H16_p70`
- `family = DelayExit_H`
- `H = 16`
- `threshold_percentile = 70`
- `threshold_value = 0.7576656445740457`

### 8.1 Decision semantics
- Decision point = first trail-stop signal close since most recent full entry fill
- `score >= threshold` → `CONTINUE`
- `score < threshold` → `EXIT_BASELINE`
- Direction is frozen: higher score means stronger evidence for short-horizon rebound / delayed-exit utility

### 8.2 Continuation semantics
- Continuation starts at the scheduled baseline trail-stop exit fill open
- Continued notional fraction = `100%`
- No sell fill at continuation start
- Forced expiry = open of bar `j + 16`
- Trend exit override remains active
- Recursive rescoring forbidden
- No new entry while any notional remains open
- Allowed continuation end reasons:
  - `forced_expiry`
  - `trend_exit_during_continuation`

## 9. Score source model freeze

**Classification:** AUTHORITATIVE

- model family: `elastic_net_logistic_regression`
- label: `churn_signal20`
- features in order:
  1. `d1_regime_strength`
  2. `ema_gap_pct`
  3. `holding_bars_to_exit_signal`
  4. `return_from_entry_to_signal`
  5. `peak_runup_from_entry`
  6. `atr_percentile_100`

Frozen hyperparameters:
- `C = 0.1`
- `l1_ratio = 0.25`
- `solver = saga`
- `penalty = elasticnet`
- `fit_intercept = True`
- `class_weight = None`
- `max_iter = 5000`
- `tol = 1e-6`
- `random_state = 20260312`

Scaler:
- `StandardScaler` fit on full 178 authoritative score-source episodes only for deployment freeze

No model reselection.
No feature reselection.
No retuning.
No threshold search.

## 10. Exact live feature definitions

**Classification:** AUTHORITATIVE

### 10.1 d1_regime_strength
- Formula: `(mapped_completed_D1_close - mapped_completed_D1_EMA21) / mapped_completed_D1_close`
- Bar/time anchor: decision signal close
- Causal constraint: latest completed D1 with `d1_close_time < decision_signal_close_time`
- Undefined handling: fail replay / fail shadow review

### 10.2 ema_gap_pct
- Formula: `(ema_fast_30_H4_t - ema_slow_120_H4_t) / ema_slow_120_H4_t`
- Anchor: decision signal close
- Undefined handling: fail replay / fail shadow review

### 10.3 holding_bars_to_exit_signal
- Formula: `decision_signal_bar_index - live_trade_full_entry_fill_bar_index + 1`
- Anchor: decision signal close
- Trade-state anchor: most recent full entry of current live trade
- Undefined handling: fail replay / fail shadow review

### 10.4 return_from_entry_to_signal
- Formula: `decision_signal_close / live_trade_full_entry_fill_price - 1`
- Anchor: decision signal close
- Trade-state anchor: most recent full entry of current live trade
- Undefined handling: fail replay / fail shadow review

### 10.5 peak_runup_from_entry
- Formula: `live_trade_peak_close_through_decision_signal_bar / live_trade_full_entry_fill_price - 1`
- Peak semantics: maximum H4 close from full-entry fill bar through decision signal bar inclusive
- Undefined handling: fail replay / fail shadow review

### 10.6 atr_percentile_100
- Formula: `count(robust_atr_k <= robust_atr_t for k in trailing_100_observed_H4_bars_ending_at_t) / 100`
- Anchor: decision signal close
- Causal constraint: trailing 100 observed H4 bars ending at the decision bar inclusive
- Undefined handling: fail replay / fail shadow review

## 11. Validation protocol freeze

**Classification:** AUTHORITATIVE

### 11.1 Fixed-date WFO windows
- Fold 1:
  - train through `2021-06-30 23:59:59.999 UTC`
  - OOS `2021-07-01 00:00:00 UTC` → `2022-12-31 23:59:59.999 UTC`
- Fold 2:
  - train through `2022-12-31 23:59:59.999 UTC`
  - OOS `2023-01-01 00:00:00 UTC` → `2024-06-30 23:59:59.999 UTC`
- Fold 3:
  - train through `2024-06-30 23:59:59.999 UTC`
  - OOS `2024-07-01 00:00:00 UTC` → `2025-06-30 23:59:59.999 UTC`
- Fold 4:
  - train through `2025-06-30 23:59:59.999 UTC`
  - OOS `2025-07-01 00:00:00 UTC` → `2026-02-28 23:59:59.999 UTC`

### 11.2 Winner validation metrics
- aggregate WFO OOS Sharpe @25bps = `1.1853946679308718`
- aggregate WFO OOS MDD = `-0.3581683945426433`
- WFO positive folds = `3/4`
- bootstrap `P(ΔSharpe > 0)` = `0.742`
- cost levels beaten = `9/9`
- exposure trap passed = `True`
- added-value gate passed = `True`

## 12. Forbidden changes

Any of the following breaks the claim “same strategy / same promoted deployment”:
- changing the base strategy entry logic
- changing the base trailing stop definition
- changing the D1 mapping rule
- changing the warmup rule
- changing execution timing
- changing cost semantics
- changing the label
- changing the 6 selected features
- changing feature formulas
- changing model family
- changing any hyperparameter
- changing scaler semantics
- changing threshold percentile or threshold value
- changing `H`
- changing score-to-action direction
- introducing recursive rescoring
- allowing new entry while any notional remains open
- changing continuation end reasons
- changing WFO / bootstrap / cost / exposure trap / added-value gates
- changing winner selection tie-breaks

## 13. Reproducibility checklist

A new team must confirm all of the following before claiming a 1:1 rebuild:
1. raw input files match the frozen bundle
2. H4/D1 mapping is causal and identical
3. base strategy replay matches frozen Step 1 semantics
4. 178 authoritative score-source episodes are reconstructed exactly
5. the 6 selected live features replay within tolerance
6. the full-178 elastic-net refit reproduces the frozen coefficients / intercept / threshold
7. one-shot decision semantics are preserved
8. recursive rescoring count remains zero
9. continuation expiry semantics match exactly
10. candidate identity is exactly `delay_H16_p70`
11. B4 winner metrics match the frozen validation summary within replay tolerance
12. shadow mode starts only after replay / acceptance tests pass
