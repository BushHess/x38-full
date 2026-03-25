# Documentation Index

All project documentation organized by topic. Entry point for agents and contributors.

---

## algorithm/ — Algorithm Specification

| Document | Purpose |
|----------|---------|
| [VTREND_BLUEPRINT.md](algorithm/VTREND_BLUEPRINT.md) | Complete algorithm spec (760 lines) — parameters, indicators, signal flow |
| [LATENCY_TIER_DEPLOYMENT_GUIDE.md](algorithm/LATENCY_TIER_DEPLOYMENT_GUIDE.md) | Latency tier decision matrix (LT1/LT2/LT3), fallback logic, SLA requirements |

## operations/ — Operational Procedures

| Document | Purpose |
|----------|---------|
| [RUNBOOK_C4_C5.md](operations/RUNBOOK_C4_C5.md) | Testnet validation runbook (C4 smoke, C5 replay) |

## validation/ — Validation Framework

| Document | Purpose |
|----------|---------|
| [README.md](validation/README.md) | Validation docs index |
| [decision_policy.md](validation/decision_policy.md) | Gate definitions and PROMOTE/HOLD/REJECT criteria |
| [output_contract.md](validation/output_contract.md) | Required artifacts per validation suite |
| [validation_cli.md](validation/validation_cli.md) | CLI usage for `validate_strategy.py` |
| [pair_review_workflow.md](validation/pair_review_workflow.md) | Human pair-review workflow for strategy decisions |
| [THRESHOLD_GOVERNANCE_POLICY.md](validation/THRESHOLD_GOVERNANCE_POLICY.md) | Threshold change governance |
| [validation_changelog.md](validation/validation_changelog.md) | Validation framework change log |
| [golden_template.yaml](validation/golden_template.yaml) | Regression baseline template |

## research/ — Research Guidelines

| Document | Purpose |
|----------|---------|
| [strategy_versioning.md](research/strategy_versioning.md) | Strategy folder contract and versioning rules |
| [RESEARCH_RULES.md](research/RESEARCH_RULES.md) | Research patterns, v10 API reference, import rules |

## archive/ — Historical Documents

| Document | Purpose |
|----------|---------|
| [Position_Management_Architecture_Memo.md](archive/Position_Management_Architecture_Memo.md) | V8 Apex pyramiding analysis (2026-02-26, pre-VTREND) |

---

## Root-Level Documents

These stay at repo root for standard project conventions:

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quickstart |
| `CLAUDE.md` | AI agent context (always loaded) |
| `CHANGELOG.md` | Release/change history |
| `DEPLOYMENT_CHECKLIST.md` | Component-level deployment reference |
| `STRATEGY_STATUS_MATRIX.md` | All strategy verdicts and status |
