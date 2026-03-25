# X35 Phase 5 — Candidate Design Rules

**Status**: SKIPPED (no admissible candidate)  
**Gate**: requires positive evidence from Phase 2–4.

This document remains as a historical design rule set only.
No candidate entered Phase 5 before the study was closed.

---

## 1. Candidate Budget

When `x35` reaches design, freeze at most:

- 3 candidates total

Ordered by action complexity:

1. Entry-permission only
2. Risk-off flat
3. Exposure-mode candidate

## 2. DOF Budget

- Preferred: 0–1 new tunable DOF
- Maximum: 2 new tunable DOF per candidate
- Candidate families must be justified by prior observations, not free search

## 3. Design Priority

If the evidence is only about entry quality:

- only design Class A (`entry_prevention_only`)

If the evidence clearly concerns mid-trade hazard:

- Class B may be admitted

If the evidence is weak or mixed:

- do not escalate to sizing/exposure modes

## 4. Negative Criteria

A candidate should be rejected at design time if it mainly:

- mimics a slower daily EMA replacement;
- blocks too many trades;
- improves only MDD;
- or requires post-hoc combination of multiple weak states.
