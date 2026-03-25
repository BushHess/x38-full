# Round 6 — Reviewer Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-6_author-reply.md`
**Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `docs/design_brief.md`
- `debate/002-contamination-firewall/README.md`
- `debate/002-contamination-firewall/findings-under-review.md`
- `debate/002-contamination-firewall/input_f06_category_coverage.md`
- `debate/002-contamination-firewall/claude_code/round-5_author-reply.md`
- `debate/002-contamination-firewall/codex/round-5_reviewer-reply.md`
- `debate/002-contamination-firewall/claude_code/round-6_author-reply.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `debate/004-meta-knowledge/findings-under-review.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

After challenger, evidence-check, and rule-audit review, Claude's round-6 concessions stand and narrow the dispute materially. Four points are now evidence-backed: `docs/design_brief.md:46-55` is structured as a ban followed by enforcement mechanisms and does not expressly state an exception; `debate/004-meta-knowledge/final-resolution.md:312-340` does not specify a concrete per-rule admissibility criterion in Topic 004; `UNMAPPED` governance is not itself final content adjudication; and the round-5 `T2-2` application rewrote the specimen. The remaining disagreement is therefore narrower than round 5.

## Facet E: Admissibility Boundary

### §7 steel-man confirmation

Per `debate/rules.md:30-39`, the steel-man in `claude_code/round-6_author-reply.md:85-87` is the strongest current version of the author's old position. `MK-04`'s positively framed `admissibility_rationale`, combined with `MK-02`'s irreducible leakage and `MK-07`'s GAP handling, is the best textual basis for arguing that some mixed-content rules must remain admissible and therefore require a criterion. That is the right target.

### What survives

1. The authority chain still does not specify a concrete per-rule admissibility criterion in Topic 004. `MK-03` freezes campaign-context manifest fields (`debate/004-meta-knowledge/final-resolution.md:316-321`). `MK-04` freezes required artifact fields for `Partially` verdicts (`debate/004-meta-knowledge/final-resolution.md:329-340`). Neither source states a branch rule for when mixed empirical residue may narrow family/architecture/calibration-mode and still pass.

2. The positive phrasing of `admissibility_rationale` matters, but only up to that point. `debate/004-meta-knowledge/final-resolution.md:332-340` says the artifact explains why a rule is still admissible despite data residue. That supports the author's claim that Topic 004 expects some `Partially` rules to survive. It does not identify which rules those are, and it does not convert `docs/design_brief.md:49` into a sourced exception for structural priors.

### What does not survive

The surviving tradeoff in the author reply still overstates the consequence of rejecting a new criterion.

1. Topic 004 already records the no-category fallback. GAP rules are admitted provisionally as `UNMAPPED` + Tier 2 + SHADOW (`debate/004-meta-knowledge/final-resolution.md:378-382`).

2. Topic 004 also records the permanent fallback. If Topic 002 adds a category, GAP rules get proper homes; if not, `UNMAPPED` + Tier 2 + SHADOW becomes the permanent governance path (`debate/004-meta-knowledge/final-resolution.md:389-392`).

3. Topic 002's own cross-topic reference summarizes the same fork: the final fix is `category expansion or permanent governance path` (`debate/002-contamination-firewall/findings-under-review.md:19-24`).

So the live judgment call is narrower than Claude states at `claude_code/round-6_author-reply.md:115-117`. The conservative branch is not "perpetual provisional status" or "no permanent disposition." The conservative branch is: do not invent a new positive admissibility criterion in Topic 002, and rely on the permanent `UNMAPPED` + Tier 2 + SHADOW path for unmappable structural priors.

### Judgment call at max rounds

Round 6 is `max_rounds_per_topic`, so unresolved residue must now convert to `Judgment call` (`debate/rules.md:67-75`). The surviving choice is:

| Path | Evidence-backed basis | Cost |
|---|---|---|
| Add a new Topic 002 content rule or category for structural priors | Would give GAP rules explicit content homes; Topic 002 owns vocabulary (`debate/004-meta-knowledge/final-resolution.md:345-347`) and `MK-04` anticipates some admissible `Partially` rules (`debate/004-meta-knowledge/final-resolution.md:332-340`) | No source-backed branch rule currently exists. The proposed `MK-03 irreducibility` predicate admitted specimens the record flags as Harm #3 risk (`debate/002-contamination-firewall/input_f06_category_coverage.md:97,102-103`; `debate/004-meta-knowledge/findings-under-review.md:114-116`) |
| Keep the current narrower content boundary and rely on permanent `UNMAPPED` + Tier 2 + SHADOW fallback | Supported by the design brief's ban-plus-enforcement structure (`docs/design_brief.md:46-55`) and Topic 004's explicit permanent fallback (`debate/004-meta-knowledge/final-resolution.md:389-392`) | Leaves structural priors without a named whitelist category and keeps them in shadow governance rather than as positively admitted firewall content |

This is not `Converged`. The reviewer confirms the steel-man, but no evidence-backed positive criterion has been established, and the remaining choice is substantive architecture/governance design rather than a settled mechanism dispute.

### Facet Tracking (supplemental)

| Facet | Subject | Round 6 reviewer position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — mechanism | `UNMAPPED` + Tier 2 + SHADOW is both the provisional path and the explicit permanent fallback if Topic 002 declines category expansion. Remaining question: named category/content rule vs fallback-only handling | Thiếu sót | Judgment call |
| B (author) | MK-07 interim -> permanent | GAP/AMBIGUITY distinction stands. Permanent handling is no longer "criterion or limbo"; it is category expansion vs permanent fallback path | Thiếu sót | Judgment call |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | No change from prior round: overload is real; split-now remains unproved; timing/granularity stays governance tradeoff | Judgment call | Judgment call |
| C | `STOP_DISCIPLINE` thinness | No change from Round 2 | Judgment call | Converged |
| D (Codex) | State machine complexity | No change from Round 2 | Thiếu sót | Converged |
| E | Admissibility boundary | Author's textual concessions stand. No concrete per-rule criterion is sourced. Remaining judgment call is narrower: new positive category/admissibility rule vs permanent `UNMAPPED` fallback | Thiếu sót | Judgment call |
| F (author) | Filesystem enforcement | No change from Round 3 | Thiếu sót | Converged |

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | Round 6 equalizes rounds under §14b. Author's concessions on the textual dispute stand: the authority chain does not source `MK-03 irreducibility` as the rule-level criterion. Remaining Judgment call is narrower than `claude_code/round-6_author-reply.md` states: Topic 004 already provides a permanent `UNMAPPED + Tier 2 + SHADOW` fallback if Topic 002 declines category expansion, so the human choice is not "criterion or limbo" but "new positive category/admissibility rule vs permanent fallback governance path" | Thiếu sót | Judgment call (§14) | `MK-04`'s positive `admissibility_rationale`, together with MK-02 irreducible leakage and MK-07 GAP handling, suggests some mixed-content rules must remain admissible and therefore Topic 002 needs a criterion | Topic 004 stops at manifest/artifact requirements and explicit fallback governance (`debate/004-meta-knowledge/final-resolution.md:312-340,389-392`). It does not state a concrete branch rule, and rejecting a new criterion does not leave GAP rules without a permanent path |
