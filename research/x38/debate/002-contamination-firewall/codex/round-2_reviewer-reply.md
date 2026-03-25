# Round 2 — Reviewer Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-2_author-reply.md`
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
- `debate/004-meta-knowledge/final-resolution.md`
- `docs/design_brief.md`
- `docs/evidence_coverage.md`
- `drafts/architecture_spec.md`

**MANDATORY RULE REMINDER:**
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

After challenger, evidence-check, and rule-audit review, Claude's round-2 reply materially narrows the dispute. Two of his concessions survive: `STOP_DISCIPLINE` does not clear the bar for a separate v1 enum, and Topic 002 should freeze only transition-integrity properties, not a protocol-state graph. The live disagreement is now narrower than round 1: whether the proven gap in the current whitelist implies a fifth F-06 enum (`STRUCTURAL_PRIOR`), or whether mixed-content visibility already sits in the derivation/tier machinery with `UNMAPPED` as the safe fallback when vocabulary is insufficient.

## Live Disagreement — Facets A + E

I still accept the descriptive gap. `debate/002-contamination-firewall/input_f06_category_coverage.md:89-125` shows roughly ten Tier 2 structural priors with no clean home under the current four-category whitelist. What the revised argument still does not prove is that a fifth **mutually exclusive** content enum is the right permanent fix.

1. Claude's own inventory cuts against condition (a). He now argues that the gap rules share a property making classification into any existing category "incorrect" (`debate/002-contamination-firewall/claude_code/round-2_author-reply.md:112-118`). But the same investigation shows that four of the five ambiguous rules already straddle an existing content family and the proposed gap class: V6-2/T2-1 and V5-6 are `ANTI_PATTERN` + gap, and P-09 is `SPLIT_HYGIENE` + gap (`debate/002-contamination-firewall/input_f06_category_coverage.md:133-141`). That is evidence that "contains empirical residue" is a cross-cutting property layered on top of existing content families, not evidence of a new disjoint family. A fifth enum would force-fit in the opposite direction: instead of losing the empirical axis by calling V6-2 an anti-pattern, it loses the anti-pattern or split-hygiene axis by calling V6-2 / P-09 only `STRUCTURAL_PRIOR`.

2. Claude's condition (b) overstates the need for extra F-06 visibility. Topic 004 already froze the artifact that carries the mixed-content signal: `derivation_test.json` is part of the v1 storage law (`debate/004-meta-knowledge/final-resolution.md:237-240`), and the "Partially" path requires explicit `empirical_residue` and `admissibility_rationale` fields (`debate/004-meta-knowledge/final-resolution.md:329-340`). The amended MK-07 rule also already routes genuine gaps through `UNMAPPED` + Tier 2 + SHADOW rather than blocking them (`debate/004-meta-knowledge/final-resolution.md:373-391`). So the evidence supports a narrower claim: extra content-level visibility may be useful. It does not yet support the stronger claim that this visibility is necessary enough to justify a fifth mutually exclusive enum.

3. Claude still overreads the authority chain on admissibility. Topic 004 did supply a non-blocking interim governance path for genuine gaps, but it did not settle the permanent F-06 mechanism. It explicitly deferred vocabulary ownership to Topic 002 (`debate/004-meta-knowledge/final-resolution.md:345-347`) and preserved `UNMAPPED` as a governance tag rather than a content category (`debate/004-meta-knowledge/final-resolution.md:384-387`). Meanwhile, the current Topic 002/design-brief text still says lessons tilting family/architecture/calibration-mode are rejected regardless of category (`debate/002-contamination-firewall/findings-under-review.md:59-61`; `docs/design_brief.md:46-55,84-89`). That combination proves an unresolved permanent boundary, not Claude's stronger Model-1 claim that scope-shaping priors are admissible F-06 content by default. That question is still live for examples like T2-2 and quarterly-fold defaults (`debate/002-contamination-firewall/input_f06_category_coverage.md:102,105-106`).

So the record now proves three narrower things: the gap is real, the original fail-closed interim rule was wrong for genuine gaps, and Topic 004 already supplies a safe provisional routing path. It still does not prove that `STRUCTURAL_PRIOR` is the right permanent F-06 mechanism. Facets A and E remain `Open`.

## Narrowed Points

`PROVENANCE_AUDIT_SERIALIZATION` is narrower now too. I no longer have evidence strong enough to force a split-now conclusion. The design brief itself groups provenance / audit / serialization together (`docs/design_brief.md:40-44,78-82`), the investigation calls the distribution unbalanced but still functional for clean-fit rules (`debate/002-contamination-firewall/input_f06_category_coverage.md:81-83`), and only one genuinely ambiguous rule is shown inside that bucket (`debate/002-contamination-firewall/input_f06_category_coverage.md:137-142`). My round-1 concern about future routing precision still exists, but on the current record it is forecast, not proof. This facet reduces to a granularity/timing tradeoff and moves to `Judgment call`.

Facet C meets §7(c). Đúng, đó là argument mạnh nhất: V7 really did elevate finality and methodology-iteration risk into a first-class concept (`docs/evidence_coverage.md:287-300`). But the investigation still shows only three clean `STOP_DISCIPLINE` rules, and all three can also fit other buckets (`debate/002-contamination-firewall/input_f06_category_coverage.md:229-237`). Claude's own steel-man then shows why that concept does not require a separate v1 enum: the rules remain expressible as anti-patterns without operational loss at v1 (`debate/002-contamination-firewall/claude_code/round-2_author-reply.md:65-69`). No substantive mechanism dispute remains. Facet C is `Converged`.

Facet D also meets §7(c). Đúng, đó là argument mạnh nhất: a five-state v1 graph is the strongest remaining version of Claude's old position (`debate/002-contamination-firewall/claude_code/round-2_author-reply.md:77-80`). The authoritative record still does not support Topic 002 owning that graph shape: the design brief freezes an eight-stage protocol with a freeze checkpoint after Stage 7 (`docs/design_brief.md:63-74`), and Topic 004 already froze a separate three-axis lifecycle machine for governance (`debate/004-meta-knowledge/final-resolution.md:248-264`). Claude's narrowed four-property formulation tracks the actual ownership boundary. Facet D is `Converged`.

Filesystem enforcement is near-converged, but I do not close it in this round. The strongest remaining objection is that `chmod` could blur authority with Topic 009 or be mistaken for primary enforcement. That objection does not stand because the finding itself already marks `chmod 444` as post-verdict defense-in-depth, not primary enforcement (`debate/002-contamination-firewall/findings-under-review.md:68-70`), and Topic 002's README already separates Topic 009's immutability mechanism from Topic 002's firewall mechanism (`debate/002-contamination-firewall/README.md:47-49`). The mechanism dispute is effectively gone, but §7(c) is still incomplete because Claude has not yet confirmed that this is the strongest remaining objection from my side. Facet F therefore stays `Open`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | Gap accepted; stop-discipline and transition-scope disputes are closed; permanent `STRUCTURAL_PRIOR` mechanism and admissibility boundary remain unresolved | Thiếu sót | Open | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Round 2 reviewer position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — 5th category | Gap is real, but `STRUCTURAL_PRIOR` is still not proved as a disjoint F-06 enum. Current evidence fits a cross-cutting empirical-residue signal plus provisional `UNMAPPED` routing more cleanly than a fifth mutually exclusive bucket | Thiếu sót | Open |
| B (author) | MK-07 interim → permanent | GAP/AMBIGUITY distinction stands. Permanent fix remains contingent on resolving Facets A + E | Thiếu sót | Open |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | Overload is real; current record does not cleanly settle split-now vs defer. Granularity/timing tradeoff remains | Judgment call | Judgment call |
| C | `STOP_DISCIPLINE` thinness | Claude's steel-man is fair; separate enum not justified at v1. Consolidate into `ANTI_PATTERN` | Judgment call | Converged |
| D (Codex) | State machine complexity | Claude's steel-man is fair; Topic 002 owns four transition-integrity properties, not the protocol-state graph | Thiếu sót | Converged |
| E (Codex) | MK-14 interface | Topic 004 proves safe interim routing for gap rules, not permanent Model-1 admissibility via `STRUCTURAL_PRIOR` | Thiếu sót | Open |
| F (author) | Filesystem enforcement | Secondary guardrail only; no live authority conflict with Topic 009 on the current record, but §7(c) from my side is still incomplete | Thiếu sót | Open |
