# 07 — Artifacts and Templates

## 1. Mục tiêu

Tài liệu này gom:
- tree khuyến nghị,
- artifact contracts quan trọng,
- templates thực dụng để đội nghiên cứu điền ngay.

---

## 2. Cây thư mục khuyến nghị

```text
research/x40/
├── README.md
├── PLAN.md
├── SESSION_GUIDE.md
├── BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml
├── baselines/
│   ├── OH0_D1_TREND40/
│   │   ├── source_reference.md
│   │   ├── frozen_spec.md
│   │   ├── frozen_spec.json
│   │   ├── baseline_manifest.json
│   │   └── forward_evaluation_ledger.csv
│   └── PF0_E5_EMA21D1/
│       ├── source_reference.md
│       ├── frozen_spec.md
│       ├── frozen_spec.json
│       ├── baseline_manifest.json
│       └── forward_evaluation_ledger.csv
├── studies/
│   ├── A00_source_parity.md
│   ├── A01_temporal_decay.md
│   ├── A02_alpha_half_life.md
│   ├── A03_capacity_crowding.md
│   ├── A04_entry_exit_attribution.md
│   ├── A05_canary_drift.md
│   ├── A06_bounded_requalification.md
│   └── A07_league_pivot_gate.md
├── runs/
│   └── <run_id>/
│       ├── preflight/
│       ├── parity/
│       ├── qualification/
│       ├── studies/
│       ├── reviews/
│       └── decisions/
└── templates/
```

---

## 3. `baseline_manifest.json` checklist

Tối thiểu phải có:
- `baseline_id`
- `league_id`
- `source_of_truth`
- `source_snapshot_id`
- `source_window_profile_id`
- `qualification_snapshot_id`
- `qualification_window_profile_id`
- `object_type`
- `baseline_level`
- `durability_status`
- `constitution_version`
- `freeze_cutoff_utc`
- `cost_model_id`
- `stress_cost_model_ids`
- `execution_clock`
- `live_start_utc`
- `physical_input_schema_id`
- `physical_input_fields_present`
- `data_surface_used_by_logic`
- `qualification_metric_domain_id`
- `deployment_notional_reference_quote`
- `notes`

### Review questions
- league có đúng với fields dùng bởi logic không?
- physical schema có đang bị nhầm với data surface không?
- metric domain đã là daily UTC common domain chưa?
- cost model đã pin ID chưa?

---

## 4. `forward_evaluation_ledger.csv` schema

Tối thiểu các cột:
- `baseline_id`
- `league_id`
- `eval_block_id`
- `block_start_utc`
- `block_end_utc`
- `data_mode`
- `metric_domain_id`
- `n_native_intervals`
- `n_completed_trades`
- `sharpe`
- `cagr`
- `mdd`
- `expectancy_per_trade`
- `avg_holding_bars`
- `a05_canary_state`
- `durability_status_before`
- `durability_status_after`
- `requalification_action`
- `verdict_path`
- `notes`

### Data mode values
- `historical_seed`
- `appended_shadow`
- `appended_live`
- `realized_execution`

---

## 5. `next_action.md` minimum structure

```markdown
# Next Action

## Decision
- primary_action:
- target_league_id:
- active_baseline_id:
- research_focus:
- open_x37_challenge:
- pivot_recommended:

## Evidence summary
- baseline levels:
- durability states:
- A01 summary:
- A02 summary:
- A03 summary:
- A04 summary:
- A07 summary:

## Why this branch
- ...

## Why not the other branches
- ...

## Immediate tasks
1.
2.
3.

## Stop conditions
- ...

## Sign-off
- research_lead:
- reviewer:
- timestamp_utc:
```

---

## 6. `baseline_review.md` minimum structure

```markdown
# Baseline Review — <baseline_id>

## Identity
- baseline_id:
- league_id:
- object_type:
- baseline_level:
- durability_status:

## Qualification
- hard gates:
- soft evidence:
- freeze_cutoff_utc:
- metric_domain_id:

## Decay
- a01_decay_band:
- key ratios:
- recent era verdict:

## Half-life
- peak_horizon change:
- late_realization_share change:
- compression_warning:
- compression_severe:

## Crowding
- crowding_warning:
- crowding_severe:
- capacity summary:
- cost stress summary:

## Canary
- a05_canary_state:
- notes:

## Interpretation
- ...

## Recommendation
- ...
```

---

## 7. `concept_card.md` minimum structure

```markdown
# Concept Card — <concept_name>

## Type
- entry / exit / filter / characterization

## Motivation
- ...

## Claim
- This concept measures ...

## Non-claim
- This concept does NOT measure ...

## Observable domain
- fields:
- clock:
- event scope:

## Expected signature
- ...

## Counterexample
- ...

## Failure mode
- ...

## Family plan
- variants:
- tunables:
- what must stay invariant:

## Baseline challenge target
- baseline_id:
- what weakness this concept is trying to address:
```

---

## 8. `residual_brief.md` minimum structure

```markdown
# Residual Brief

## Sprint identity
- sprint_id:
- target_league_id:
- active_baseline_id:
- research_focus:

## Inputs from x40
- next_action:
- baseline_manifest:
- durability_summary:
- a04_advice:
- forward_ledger_snapshot:

## Weaknesses to investigate
1.
2.
3.

## Forbidden directions
1.
2.
3.

## Expected output
- concept cards:
- families:
- promotion packages:
```

---

## 9. `challenger_promotion_checklist.md`

```markdown
# Challenger Promotion Checklist

- [ ] concept_card.md exists
- [ ] feature_family.md exists
- [ ] exact formulas pinned
- [ ] robustness grid exists
- [ ] falsification summary exists
- [ ] simplified replay delta vs active baseline exists
- [ ] target role declared (entry/exit/filter/replace/characterization)
- [ ] league_id declared
- [ ] no cross-league leakage
- [ ] no hidden recalibration
```

---

## 10. `source_reference.md` checklist

Phải pin:
- exact source files
- exact authoritative artifacts
- source snapshot coverage
- source window profile
- source metric domain
- parity tolerances
- code entry points
- known outdated docs that are historical only, not authoritative

---

## 11. `run_blockers.md` structure

```markdown
# Run Blockers

## Blocker ID
- ...

## Affected baseline
- ...

## Stage
- parity / qualification / durability / decision

## Severity
- hard / soft

## Description
- ...

## Required fix
- ...

## Owner
- ...

## Opened at
- ...

## Closed at
- ...
```

---

## 12. Quy tắc dùng templates

- Template chỉ là skeleton; không được bỏ trống section critical.
- Nếu một section “không áp dụng”, phải ghi lý do `N/A because ...`, không được để trống.
- Tài liệu review phải link tới exact artifact path, không nói mơ hồ.
