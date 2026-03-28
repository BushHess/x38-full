# X40 Clean Restart Documentation Pack v2

## Status
**Normative pack — clean rewrite, corrected after full QA pass.**

This pack supersedes earlier x40 packs generated in this conversation.
Treat this pack as the current source package for any future `research/x40/` implementation work.

## Why v2 exists
A full review of the earlier clean-restart pack exposed several load-bearing defects:

1. no explicit rule forcing **same cost profile + same metric domain** in headline comparisons,
2. promised template files that were not actually included,
3. challenger routing fields that mixed x40 actions with Tier-3 deployment routes,
4. one registry convention in some docs and another registry convention in others.

This v2 pack fixes those issues directly.

## Design stance
This pack is built around these commitments:

- **x37** is the blank-slate discovery arena.
- **x39** is the residual / feature-invention lab.
- **x40** is the operational control layer for baseline qualification, durability measurement, tracked challengers and next-branch selection.
- **x38** remains downstream architecture/governance consumption.

## Reading order
| Order | File | Role |
|---|---|---|
| 0 | `README.md` | Short orientation |
| 1 | `01_X40_CLEAN_RESTART_SYSTEM_SPEC.md` | Master architecture and normative behavior |
| 2 | `02_BASELINE_QUALIFICATION_CONSTITUTION.md` | Exact rules for baseline qualification and comparison discipline |
| 3 | `03_TRACKED_CHALLENGER_AND_LOW_POWER_ADJUDICATION.md` | Challenger lane and low-power HOLD handling |
| 4 | `04_FIRST_CYCLE_IMPLEMENTATION_RUNBOOK.md` | What to do immediately after code exists |
| 5 | `05_OPERATIONAL_DECISION_TREE.md` | Branch logic after first-cycle evidence exists |
| 6 | `06_X39_RESIDUAL_DISCOVERY_PLAYBOOK.md` | How to run residual/feature-invention work correctly |
| 7 | `07_X37_BLANK_SLATE_ESCALATION_PLAYBOOK.md` | When and how to open a blank-slate challenge |
| 8 | `08_RICHER_DATA_LEAGUE_BOOTSTRAP.md` | How to pivot beyond OHLCV/public-flow leagues |
| 9 | `09_MONTHLY_QUARTERLY_OPERATIONS.md` | Ongoing operations after first launch |
| 10 | `10_ARTIFACT_SCHEMA_AND_TEMPLATES.md` | Artifact contracts and file-level expectations |
| 11 | `11_SOURCE_ALIGNMENT_NOTES.md` | Repo facts vs x40 policy choices |
| 12 | `12_QA_REVIEW.md` | What was checked and what was fixed |

## Initial active objects encoded by this pack
| Object | Type | League | Initial role |
|---|---|---|---|
| `OH0_D1_TREND40` | Baseline | `OHLCV_ONLY` | Control baseline |
| `PF0_E5_EMA21D1` | Baseline | `PUBLIC_FLOW` | Practical incumbent |
| `PF1_E5_VC07` | Challenger | `PUBLIC_FLOW` | Tracked challenger from formal x39 validation |

## Comparison discipline summary
All headline comparisons in x40 must use:

- **common daily UTC metric domain**, and
- **the same comparison profile**.

Default headline profile:
- `CP_PRIMARY_50_DAILYUTC` = 50 bps round-trip, daily UTC mark-to-market equity domain.

Optional sensitivity profile:
- `CP_SENS_20_DAILYUTC` = 20 bps round-trip, daily UTC mark-to-market equity domain.

Source-native parity may still use source-native reporting conventions, but headline x40 claims may not.

## Included templates
This pack now includes an actual `templates/` directory containing:

- `baseline_manifest_template.yaml`
- `challenger_manifest_template.yaml`
- `comparison_profiles_template.yaml`
- `concept_card_template.md`
- `family_pack_template.md`
- `challenger_review_template.md`
- `next_action_template.md`
- `forward_evaluation_ledger_template.csv`

## Target repo mapping
If this pack is ported into the repo, the intended landing zone is:

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
└── templates/
```

## Rule of precedence
If any later discussion tries to reintroduce older patched language or mixed-profile comparisons, this pack wins unless an explicit future revision says otherwise.
