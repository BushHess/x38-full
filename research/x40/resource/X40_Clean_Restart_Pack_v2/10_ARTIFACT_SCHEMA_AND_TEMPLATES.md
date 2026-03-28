# Artifact Schema and Templates

## 1. Purpose

This file defines the expected artifact layout for x40.

---

## 2. Core directory layout

```text
research/x40/
├── README.md
├── SYSTEM_SPEC.md
├── BASELINE_QUALIFICATION_CONSTITUTION.md
├── TRACKED_CHALLENGER_AND_LOW_POWER_ADJUDICATION.md
├── FIRST_CYCLE_IMPLEMENTATION_RUNBOOK.md
├── OPERATIONAL_DECISION_TREE.md
├── X39_RESIDUAL_DISCOVERY_PLAYBOOK.md
├── X37_BLANK_SLATE_ESCALATION_PLAYBOOK.md
├── RICHER_DATA_LEAGUE_BOOTSTRAP.md
├── MONTHLY_QUARTERLY_OPERATIONS.md
├── ARTIFACT_SCHEMA_AND_TEMPLATES.md
├── SOURCE_ALIGNMENT_NOTES.md
├── registry/
│   ├── leagues.yaml
│   ├── baselines.yaml
│   ├── challengers.yaml
│   └── comparison_profiles.yaml
├── runs/
│   ├── OH0_D1_TREND40/
│   ├── PF0_E5_EMA21D1/
│   └── PF1_E5_VC07/
├── reports/
└── templates/
```

---

## 3. Baseline artifact contract

Each baseline run directory must eventually contain:

```text
runs/<baseline_id>/
├── a00/
│   ├── parity_report.md
│   ├── parity_metrics.json
│   ├── equity_source.csv
│   ├── equity_x40.csv
│   └── delta_summary.json
├── a01/
│   ├── baseline_manifest.yaml
│   ├── frozen_system_spec.md
│   ├── qualification_report.md
│   ├── qualification_state.json
│   ├── qualification_decision.md
│   ├── metrics_CP_PRIMARY_50_DAILYUTC.json
│   ├── metrics_CP_SENS_20_DAILYUTC.json
│   ├── comparison_header.json
│   ├── regime_decomposition.csv
│   ├── cost_sensitivity.csv
│   └── forward_evaluation_ledger.csv
├── a02/
├── a03/
├── a04/
├── a05/
├── a07/
└── aggregate/
    ├── durability_state.json
    └── baseline_summary.md
```

---

## 4. Challenger artifact contract

```text
runs/<challenger_id>/
├── intake/
│   ├── challenger_manifest.yaml
│   ├── source_evidence_index.md
│   └── mechanism_summary.md
├── a06/
│   ├── challenger_review.md
│   ├── challenger_decision.json
│   ├── pair_metrics_CP_PRIMARY_50_DAILYUTC.json
│   ├── pair_metrics_CP_SENS_20_DAILYUTC.json
│   └── route_decision.md
└── archive/
```

---

## 5. Required registry fields

### 5.1 Baseline registry
- `baseline_id`
- `league`
- `active`
- `qualification_state`
- `durability_state`
- `freeze_cutoff_utc`
- `primary_comparison_profile_id`
- `manifest_path`
- `supersedes`
- `notes`

### 5.2 Challenger registry
- `challenger_id`
- `league`
- `target_baseline_id`
- `promotion_stage`
- `research_state`
- `formal_state`
- `x40_route`
- `tier3_route`
- `tracking_status`
- `primary_comparison_profile_id`
- `manifest_path`
- `expiry_policy`

### 5.3 Comparison-profile registry
- `comparison_profile_id`
- `round_trip_cost_bps`
- `metric_domain`
- `execution_assumptions`
- `headline_allowed`
- `notes`

---

## 6. Template summary

Actual template files live in `templates/`:

- `baseline_manifest_template.yaml`
- `challenger_manifest_template.yaml`
- `comparison_profiles_template.yaml`
- `concept_card_template.md`
- `family_pack_template.md`
- `challenger_review_template.md`
- `next_action_template.md`
- `forward_evaluation_ledger_template.csv`

---

## 7. `next_action.md` contract

Every next-action file must contain:

- generation timestamp,
- baseline state table,
- challenger state table,
- primary next action,
- optional secondary next action,
- evidence summary,
- comparison profile ID,
- blocked actions,
- owner,
- planned review date.

No free-form memo is enough.

---

## 8. File naming rules

### Baselines
`<league-prefix><number>_<short_name>`
Examples:
- `OH0_D1_TREND40`
- `PF0_E5_EMA21D1`

### Challengers
`<league-prefix><number>_<short_name>`
Examples:
- `PF1_E5_VC07`

### Reports
- `<study>_<object>_report.md`
- `<study>_<object>_state.json`

### Templates
Must end in `_template` except CSV template files, which must still clearly indicate template role in the filename.

---

## 9. Artifact immutability rules

- `baseline_manifest.yaml` is immutable after baseline qualification, except for registry metadata fields that explicitly track supersession.
- `challenger_review.md` is append-only once signed.
- `forward_evaluation_ledger.csv` is append-only.

---

## 10. Minimal validation rules for artifacts

Before any report is accepted:
1. required fields must exist,
2. referenced files must exist,
3. registry entries must resolve to files,
4. states must be valid enum members,
5. timestamps must be UTC ISO-8601 or integer ms where declared,
6. every comparative artifact must declare `comparison_profile_id`.

---

## 11. Relationship to production artifacts

x40 artifacts are research-control artifacts.  
They do not replace production validation outputs such as:
- `decision.json`
- deployment reports
- live strategy registry entries

They sit upstream of those.

---

## 12. What should be versioned

Version at minimum:
- constitution version,
- baseline manifest version,
- challenger manifest version,
- comparison profile version,
- template version,
- next-action schema version.
