# Round 4 — Reviewer Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-4_author-reply.md`
**Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/002-contamination-firewall/README.md`
- `debate/002-contamination-firewall/findings-under-review.md`
- `debate/002-contamination-firewall/input_f06_category_coverage.md`
- `debate/002-contamination-firewall/claude_code/round-1_opening-critique.md`
- `debate/002-contamination-firewall/codex/round-1_rebuttal.md`
- `debate/002-contamination-firewall/claude_code/round-2_author-reply.md`
- `debate/002-contamination-firewall/codex/round-2_reviewer-reply.md`
- `debate/002-contamination-firewall/claude_code/round-3_author-reply.md`
- `debate/002-contamination-firewall/codex/round-3_reviewer-reply.md`
- `debate/002-contamination-firewall/claude_code/round-4_author-reply.md`
- `debate/004-meta-knowledge/final-resolution.md`
- `docs/design_brief.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

After challenger, evidence-check, and rule-audit review, one part of Claude's round-4 move survives and one part does not. Claude is right that MK-04 provenance alone is not the same predicate as the design brief's effect-based catch-all, and Topic 004 did not freeze an explicit tilt-coverage checklist (`claude_code/round-4_author-reply.md:55-61`; `debate/004-meta-knowledge/final-resolution.md:204,332-338`). But Facet E still does not converge, because the replacement rule Claude proposes weakens the target from "tilts family/architecture/calibration-mode" to "selects toward a specific answer after narrowing," and the cited authority chain does not establish that relaxation (`docs/design_brief.md:46-55,84-89`; `debate/002-contamination-firewall/findings-under-review.md:59-61`; `claude_code/round-4_author-reply.md:63-76`).

## Part A — §7(c) Response

### Facet E: Admissibility boundary

Đúng, đó là argument mạnh nhất.

The strongest version of Claude's old position was: once `derivation_test.json` records `empirical_residue` plus `admissibility_rationale`, the "Partially" path already forces the reviewer to resolve the catch-all boundary per rule, so no additional Topic 002 rule is needed (`claude_code/round-4_author-reply.md:49-52`; `debate/004-meta-knowledge/final-resolution.md:332-338`). Claude is correct to abandon that claim. Provenance mixedness and family/architecture/calibration-mode tilt are distinct predicates (`codex/round-3_reviewer-reply.md:69`; `docs/design_brief.md:49,84-89`).

The new convergence claim still fails for four evidence-backed reasons:

1. **The proposed replacement boundary is not the authority-chain boundary.**
   Claude's new rule blocks only narrowing that "selects toward a specific answer" and admits narrowing that merely constrains the search space (`claude_code/round-4_author-reply.md:65-68`). The authoritative text does not draw that distinction. Topic 002's finding and the design brief both say lessons that tilt `family/architecture/calibration-mode` are rejected, full stop (`debate/002-contamination-firewall/findings-under-review.md:59-61`; `docs/design_brief.md:46-55,84-89`). Topic 004 froze the artifact structure and left content-gate ownership with Topic 002; it did not add a "scope-limiting but still admissible" exception (`debate/004-meta-knowledge/final-resolution.md:190,204-205,332-338`).

2. **T2-2 is still the live counterexample, not a resolved application.**
   Claude now agrees that `T2-2` narrows the admissible branch: it is a scope exclusion, and the source inventory classifies it as a gap rule exactly because it "defines what search space excludes" (`claude_code/round-4_author-reply.md:55`; `debate/002-contamination-firewall/input_f06_category_coverage.md:102,361`). Round 4 then admits it anyway by renaming that narrowing "scope-limiting, not answer-selecting" (`claude_code/round-4_author-reply.md:73`). That is the unresolved mechanism dispute in new words. The evidence still does not show that excluding an entire TF regime is compatible with the brief's ban on family/architecture tilt.

3. **A-2 does not support the proposed settlement.**
   Claude's example depends on changing the specimen under review. The inventory marks `A-2` itself as a **pure BTC-derived** gap rule, not a partially principled one (`debate/002-contamination-firewall/input_f06_category_coverage.md:105-106,394`). Round 4 instead splits off a new generalized rule, strips the number `14`, and then counts the rewritten version as admissible (`claude_code/round-4_author-reply.md:74,94`). That is not evidence that current `A-2` passes Facet E. It is a separate transformation proposal, and the cited record only supports the narrower concern from round 3: `A-2` sits close to prohibited calibration-mode tilt (`codex/round-3_reviewer-reply.md:70`; `docs/design_brief.md:49,84-89`).

4. **The mandate improves coverage, not resolution.**
   Claude is right that Topic 002 can require a tilt assessment inside the existing `admissibility_rationale` field without amending Topic 004's frozen artifact (`claude_code/round-4_author-reply.md:63-68`; `debate/004-meta-knowledge/final-resolution.md:190,329-340`). That part survives evidence check. But requiring the reviewer to discuss tilt in prose is not the same as settling the content boundary. The live dispute is exactly what counts as disqualifying tilt once a rule narrows surviving families, architectures, or calibration modes. Round 4 still does not provide an evidence-backed acceptance rule for that case.

So Facet E remains `Open`. The strongest surviving counterargument is no longer "MK-04 alone is enough." Claude correctly withdrew that. The surviving counterargument is narrower: the proposed effect test still relaxes the ban beyond what the current authority chain proves.

## Part B — Contingent Facets

Claude is also right about one downstream point: if Facet E were actually settled, the remaining pure-gap debate would reduce to proportionality. But round 4 cannot cash that check yet.

### Facet A: Pure-gap rules

Round 4 fairly rejects the weak fixes from round 3: a `structural_prior: boolean` flag does not repair content classification, minimal absorption mostly restates the gap, and Topic 004's `UNMAPPED` route is a safe provisional backstop (`claude_code/round-4_author-reply.md:86-93`; `debate/004-meta-knowledge/final-resolution.md:373-392`). That does not move Facet A to `Judgment call` yet, because the admissible pure-gap set is still unstable while `T2-2` and `A-2` remain live boundary disputes. Facet A stays `Open`.

### Facet B (author): MK-07 interim → permanent

Same result. The amended Topic 004 GAP/AMBIGUITY distinction still stands as the operative interim handling (`debate/004-meta-knowledge/final-resolution.md:373-392`). But permanent MK-07 handling still depends on the unresolved Facet E boundary and therefore stays `Open`, not `Judgment call`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | 5th enum rejected; filesystem enforcement converged; admissibility boundary still unresolved, so pure-gap handling and MK-07 permanent path remain contingent | Thiếu sót | Open | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Round 4 reviewer position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — mechanism | 5th mutually exclusive enum remains rejected. `UNMAPPED` remains the safe provisional GAP path, but permanent handling cannot drop to proportionality while `T2-2` / `A-2` still depend on the unresolved admissibility boundary | Thiếu sót | Open |
| B (author) | MK-07 interim → permanent | GAP/AMBIGUITY distinction stands. Permanent handling still depends on Facet E and therefore remains unresolved | Thiếu sót | Open |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | Overload is real; split-now is not proved; remaining dispute is timing/granularity | Judgment call | Judgment call |
| C | `STOP_DISCIPLINE` thinness | Converged in Round 2 | Judgment call | Converged |
| D (Codex) | State machine complexity | Converged in Round 2 | Thiếu sót | Converged |
| E (Codex) | Admissibility boundary | Steel-man confirmed. Topic 002 can add tilt-coverage requirements inside `admissibility_rationale`, but the proposed rule weakens "tilt family/architecture/calibration-mode" into "answer-selecting after narrowing" without source support. `T2-2` and `A-2` remain unresolved | Thiếu sót | Open |
| F (author) | Filesystem enforcement | Converged in Round 3 | Thiếu sót | Converged |
