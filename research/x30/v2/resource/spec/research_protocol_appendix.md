# Research Protocol Appendix

**Classification:** AUTHORITATIVE  
This appendix records the research methodology, gates, stop rules, and decision logic for the entire project, without requiring access to chat history.

## 1. Step 1 — Base implementation and verification

### 1.1 Objective
Implement the E5+EMA21D1 base strategy exactly as specified and verify that its 25 bps evaluation-cost performance matches the frozen baseline.

### 1.2 Frozen base verification outputs
- Base Sharpe @25bps: `1.488555692041119`
- Base CAGR @25bps: `0.6222089448228432`
- Base MDD: `-0.3886155944906676`
- Completed trades: `193`
- Trail-stop exits: `178`
- Trend exits: `15`

### 1.3 Methodological constraints
- spec-first implementation
- no indicator or parameter improvisation
- no same-bar fills
- no same-bar flip
- warmup `365` days in `no_trade` mode
- 25 bps RT evaluation cost = 12.5 bps each side

## 2. Step 2 — Descriptive EDA only

### 2.1 Primary and secondary descriptive labels
- Primary descriptive clock: `signal`
- `churn_signal20 = 1` if next entry signal occurs within 20 observed H4 bars
- Secondary sensitivity: `churn_fill20`

### 2.2 Canonical episode table
- One row per trail-stop episode
- Primary sample size: `178`
- Gap-clean sensitivity size: `173`

### 2.3 EDA-only restrictions
- no model fitting
- no CV / AUC
- no threshold search
- no actuator design
- no validation

## 3. Step 3 legacy charter — pre-commit for the rejected branch

### 3.1 Primary label and sample
- primary label = `churn_signal20`
- primary sample = all `178` trail-stop episodes
- gap-clean subset = sensitivity only

### 3.2 Legacy feature pool
Frozen allowed feature pool from Step 3 v3:
- `ema_gap_pct`
- `atr_percentile_100`
- `bar_range_atr`
- `body_atr`
- `close_position`
- `ret_1bar`
- `ret_6bar`
- `ret_24bar`
- `vdo`
- `d1_regime_strength`
- `trail_tightness`
- `overshoot_trail_atr`
- `holding_bars_to_exit_signal`
- `return_from_entry_to_signal`
- `peak_runup_from_entry`
- `giveback_from_peak_to_signal`
- `peak_distance_pct`
- `signal_volume`
- `signal_quote_volume`
- `signal_num_trades`

### 3.3 Legacy model families
- `l2_logistic_regression`
- `elastic_net_logistic_regression`
- `shallow_decision_tree`

### 3.4 Legacy signal-quality gates
- `cv_auc_floor = 0.60`
- `primary_oos_auc_gate = 0.62`
- quartile primary metric = actual churn rate by predicted churn-score quartile
- monotonicity rule = `Q1 <= Q2 <= Q3 <= Q4` and `Q4 - Q1 >= 0.15`

### 3.5 Legacy actuator lock
- binary only
- threshold percentiles = `[50, 55, 60, 65, 70]`
- full-sample exploratory candidate IDs = `binary_p50`, `binary_p55`, `binary_p60`, `binary_p65`, `binary_p70`

### 3.6 Legacy validation gates
- WFO gate: `>= 3/4` positive folds
- bootstrap gate: `P(ΔSharpe > 0) >= 55%`, 500 paths, block size 60
- cost gate: beats Base on `>= 7/9` cost levels
- exposure trap: if MDD improves, candidate must beat Base(reduced_exposure) on Sharpe

## 4. Step 4 legacy branch execution and rejection

### 4.1 What Step 4 established
- classifier signal existed
- best legacy classifier family = `elastic_net_logistic_regression`
- best legacy OOS AUC = `0.8144736842105262`
- quartile monotonicity passed
- ECE exceeded `0.10`, so raw probability interpretation was forbidden

### 4.2 Why the branch was rejected
The actuator, not the classifier, failed:
- recursive closed-loop rescoring
- score saturation
- trade-state OOD drift
- near-always-hold behavior

These findings were frozen and used as the premise for the bounded-branch redesign.

## 5. Phase B1 — utility-aligned redesign EDA

### 5.1 Objective
Reinterpret the surviving signal in a bounded, utility-aligned way, without new model fitting.

### 5.2 Frozen conclusions
- signal is a short-horizon rebound / exit-delay utility proxy
- one-shot scoring is required
- recursive rescoring must be forbidden
- bounded continuation is required

### 5.3 Admitted actuator families for further study
- `DelayExit(H)`
- `Tail(X, H)`

Family `DelayExit(H, L)` with leash was not promoted into the bounded branch charter.

## 6. Phase B2 — bounded branch charter

### 6.1 Fixed score source
- model family = `elastic_net_logistic_regression`
- label = `churn_signal20`
- exactly 6 selected features
- fixed hyperparameters
- `StandardScaler`

### 6.2 One-shot decision lock
- score only the first trail-stop signal close since most recent full entry
- recursive rescoring forbidden

### 6.3 Candidate families
- `DelayExit_H`, `H in [8, 12, 16, 20]`
- `Tail_X_H`, `X in [0.25, 0.50, 0.75]`, `H in [8, 12, 16, 20]`
- gated thresholds = `[60, 70, 80]`
- ungated baselines mandatory

### 6.4 Validation gates for the bounded branch
- WFO gate: `>= 3/4` positive folds
- bootstrap gate: `P(ΔSharpe > 0) >= 55%`
- cost gate: beats Base on `>= 7/9`
- exposure trap gate
- added-value gate for gated candidates vs matched ungated baseline

### 6.5 Verdict logic
- `PROMOTE_GATED`
- `PROMOTE_UNGATED`
- `REJECT`

## 7. Phase B3 — exploratory execution

### 7.1 What B3 was allowed to do
- full-178 deterministic refit of the fixed score source
- compute exploratory thresholds `[60, 70, 80]`
- run all locked candidates and ungated baselines
- rank within family
- shortlist for validation

### 7.2 Shortlist frozen by B3
Promotable shortlist:
- `delay_H16_p70`
- `delay_H16_p60`
- `tail_X075_H16_p70`
- `tail_X075_H16_p60`

Mandatory comparison-only / ungated-verdict baselines:
- `delay_H16_all`
- `tail_X075_H16_all`

## 8. Phase B4 — final validation

### 8.1 Validated set
Exactly 6 validated IDs:
- `delay_H16_p70`
- `delay_H16_p60`
- `tail_X075_H16_p70`
- `tail_X075_H16_p60`
- `delay_H16_all`
- `tail_X075_H16_all`

### 8.2 Fixed validation windows
- Fold 1 OOS: `2021-07-01` → `2022-12-31`
- Fold 2 OOS: `2023-01-01` → `2024-06-30`
- Fold 3 OOS: `2024-07-01` → `2025-06-30`
- Fold 4 OOS: `2025-07-01` → `2026-02-28`

### 8.3 Additional bounded-branch integrity auto-fails
- recursive rescoring
- more than one scored first-trail decision per trade
- continuation beyond allowed expiry
- noncomputable live score features
- negative cash
- position fraction outside `[0, 1]`
- state-machine error
- partial accounting violation

### 8.4 Final winner
- `delay_H16_p70`
- verdict = `PROMOTE_GATED`

## 9. Report-only diagnostics that were not decision authorities

The following were reported but not allowed to open new search dimensions:
- Step 2 descriptive feature rankings
- calibration details beyond frozen consequence rules
- Phase B3 first-shot OOD diagnostics
- Phase B4 fold score diagnostics
- Phase B4 WFO pattern analysis

## 10. Methodology stop rules

Across the entire project:
- no post-hoc gate changes
- no model reselection after lock
- no candidate family expansion after lock
- no final promotion from full-sample exploratory performance alone
- no deployment authority from report-only diagnostics
