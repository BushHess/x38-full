# Final Project Report

---

## 1. files_created_or_updated

- `final_project_report.md`
- `final_deployment_freeze_spec.json`
- `final_deployment_freeze_spec.json`
- `final_implementation_spec.md`
- `final_shadow_mode_plan.md`
- `final_artifact_manifest.csv`

---

## 2. final_verdict_reconciliation

### Legacy branch

- **Verdict:** `REJECT`
- **Lý do đóng băng:** classifier signal có tồn tại, nhưng legacy binary recursive suppress actuator fail vì recursive closed-loop deployment, score saturation, trade-state OOD drift.

### Legacy branch

- **Verdict:** `REJECT`
- **Lý do đóng băng:** classifier signal có tồn tại, nhưng legacy binary recursive suppress actuator fail vì recursive closed-loop deployment, score saturation, trade-state OOD drift.

### Final project verdict

- Dự án không kết thúc bằng "mọi thứ đều fail".
- Dự án kết thúc bằng:
  - legacy branch rejected
  - bounded branch promoted
  - final winner = `delay_H16_p70`

---

## 3. deployment_freeze_spec

Deployment freeze đã được khóa deterministic và threshold đã được verify lại từ refit full-178.

### Winner mechanism

- `candidate_id = delay_H16_p70`
- `family = DelayExit_H`
- `H = 16`
- `threshold_percentile = 70`

### Score source

- `model_family = elastic_net_logistic_regression`
- `label = churn_signal20`
- selected features:
  - `d1_regime_strength`
  - `ema_gap_pct`
  - `holding_bars_to_exit_signal`
  - `return_from_entry_to_signal`
  - `peak_runup_from_entry`
  - `atr_percentile_100`
- frozen hyperparameters:
  - `C = 0.1`
  - `l1_ratio = 0.25`
  - `solver = saga`
  - `penalty = elasticnet`
  - `fit_intercept = True`
  - `class_weight = None`
  - `max_iter = 5000`
  - `tol = 1e-6`
  - `random_state = 20260312`
- scaler: `StandardScaler`

### Deployment refit freeze

- authoritative fit scope = full 178 authoritative score-source episodes only
- no model reselection
- no feature reselection
- no hyperparameter tuning
- no threshold tuning

### Frozen numeric threshold

- recomputed deployment `p70 = 0.7576656445740457`
- frozen Phase B3 `p70 = 0.7576656445740457`
- exact match verified

### Live decision semantics

- only first trail-stop signal close since most recent full entry fill may be scored
- `score >= 0.7576656445740457` → `CONTINUE`
- `score < 0.7576656445740457` → `EXIT_BASELINE`
- continuation starts at scheduled baseline trail-stop exit fill open
- continuation keeps `100%` notional
- forced expiry = open of bar `j + 16`
- trend exit override remains active
- recursive rescoring forbidden
- allowed continuation end reasons only:
  - `forced_expiry`
  - `trend_exit_during_continuation`

### Authoritative file

Full frozen numeric parameters, scaler means/scales, coefficients, intercept, replay score hash, support ranges:

- `final_deployment_freeze_spec.json`

---

## 4. implementation_spec

Đã tạo implementation spec ở mức kỹ sư có thể code, gồm:

- state machine
- event order per H4 bar
- decision-time semantics
- continuation-time semantics
- trend-exit override semantics
- forced-expiry semantics
- position / notional semantics
- cost application semantics
- no-entry-while-notional-open semantics
- mandatory logging schema
- full pseudocode cho:
  - score generation
  - decision logic
  - continuation management
  - exit handling
  - accounting updates

**Authoritative file:** `final_implementation_spec.md`

---

## 5. acceptance_test_plan

Đã tạo acceptance test plan với 13 tests, trong đó:

- deployment-gating tests: `AT-001` đến `AT-011`
- regression/parity tests for internal replay harness: `AT-012`, `AT-013`

Các nhóm test bắt buộc gồm:

- feature replay tests trên 178 authoritative episodes
- score replay + threshold freeze tests
- one-shot integrity tests
- accounting / bounds / no-negative-cash tests
- cost application tests
- regression tests vs frozen exploratory / validation semantics

**Authoritative file:** `final_acceptance_test_plan.md`

---

## 6. shadow_mode_plan

Đã tạo shadow / paper-trading plan với:

- no direct live-capital cutover
- duration recommendation:
  - ít nhất `12` first-trail-stop decision events
  - và ít nhất `1` completed continuation via `forced_expiry`
- per-trade logging fields
- daily monitoring metrics
- weekly drift review
- OOD monitoring via frozen support ranges
- score distribution monitoring
- decision frequency monitoring
- exposure monitoring
- continuation end-reason monitoring
- hard kill-switch rules
- review-required triggers

### Hard kill-switch gồm:

- any recursive rescoring
- any noncomputable live feature event
- any negative cash / state-machine / position-bounds violation
- any invalid continuation end reason
- replay / threshold mismatch vs freeze spec

**Authoritative file:** `final_shadow_mode_plan.md`

---

## 7. artifact_manifest_summary

Đã tạo manifest toàn dự án với các cột:

- artifact name
- step / phase
- branch tag
- purpose
- authority status
- implementation-authoritative
- must-keep

### Tóm tắt:

| Branch | Authoritative | Report-only | Deprecated-for-deployment |
|---|---|---|---|
| `shared_baseline` | 4 | — | — |
| `legacy_binary_rejected` | 6 | 9 | 3 |
| `bounded_winner_branch` | 20 | 8 | — |
| `final_deployment_freeze` | 5 | 1 | — |

- implementation-authoritative artifacts tổng cộng: **34**

**Manifest file:** `final_artifact_manifest.csv`

---

## 8. risks_assumptions

- Deployment freeze refit đã được thực hiện đúng trên full 178 authoritative episodes và numeric threshold khớp exact với frozen Phase B3 threshold.
- Runtime deployment nên load frozen numeric parameters từ freeze spec; refit chỉ nên dùng cho replay parity test, không nên để production tự fit lại.
- Shadow-mode review bands được lấy từ validated winner fold ranges; các metric không có frozen numeric band sạch được giữ ở mức `review-required`, không bịa thêm ngưỡng mới.
- Không có backtest, validation, threshold tuning, model search, hay family search mới trong phiên close-out này.

---

## 9. next_action

Research complete. No more experimental phases under current charter. Implementation should begin only via replay tests and shadow mode.

---

## FINAL_PROJECT_RESULTS

```json
{
  "project_status": "COMPLETE",
  "legacy_branch_verdict": "REJECT",
  "winning_branch_verdict": "PROMOTE_GATED",
  "winner_candidate_id": "delay_H16_p70",
  "winner_family": "DelayExit_H",
  "winner_params": {
    "H": 16,
    "X": null,
    "threshold_percentile": 70
  },
  "deployment_score_source": {
    "model_family": "elastic_net_logistic_regression",
    "label": "churn_signal20",
    "selected_features": [
      "d1_regime_strength",
      "ema_gap_pct",
      "holding_bars_to_exit_signal",
      "return_from_entry_to_signal",
      "peak_runup_from_entry",
      "atr_percentile_100"
    ]
  },
  "deployment_threshold_value": 0.7576656445740457,
  "validation_summary": {
    "aggregate_wfo_oos_sharpe_25bps": 1.1853946679308718,
    "aggregate_wfo_oos_mdd": -0.35816839454264326,
    "wfo_positive_folds": 3,
    "bootstrap_p_delta_sharpe_gt_0": 0.742,
    "cost_levels_beaten": 9,
    "exposure_trap_passed": true,
    "added_value_gate_passed": true
  },
  "research_complete": true,
  "implementation_mode_next": "replay_tests_then_shadow_mode",
  "blocking_issues": []
}
```
