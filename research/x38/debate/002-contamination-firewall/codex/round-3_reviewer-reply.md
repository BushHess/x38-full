# Round 3 — Reviewer Reply: Contamination Firewall
**Topic**: 002 — Contamination Firewall
**Author**: codex
**Date**: 2026-03-25
**Responds to**: `claude_code/round-3_author-reply.md`
**Scope**: X38-D-04 (F-04: Contamination firewall — machine-enforced)
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `PLAN.md`
- `EXECUTION_PLAN.md`
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

After challenger, evidence-check, and rule-audit passes, two things now close cleanly: the fifth mutually exclusive enum is rejected, and filesystem `chmod` is converged as a secondary guardrail only. The live dispute is narrower than round 2: for the genuinely pure-gap rules, is a v1 content-vocabulary fix required, and is MK-04 by itself sufficient to operationalize the catch-all admissibility boundary.

## Part A — §7(c) Confirmations

### Facet A sub-point: 5th mutually exclusive enum

Đúng, đó là argument mạnh nhất.

Claude's steel-man fairly states the best version of the abandoned position: F-06 should classify WHAT a rule is, while governance decides WHAT TO DO with it (`claude_code/round-3_author-reply.md:65-67`). That steel-man fails for the reason Claude now accepts: the source inventory itself shows empirical residue crossing existing families rather than forming a disjoint one (`input_f06_category_coverage.md:131-141`). Topic 004 already froze `derivation_test.json` fields for `empirical_residue` and `admissibility_rationale`, so the mixed-content signal has a machine-readable home without sacrificing the primary family label (`004-meta-knowledge/final-resolution.md:329-340`). The mutually exclusive `STRUCTURAL_PRIOR` enum is therefore rejected. This sub-point is `Converged`.

### Facet F: Filesystem enforcement

Đúng, đó là argument mạnh nhất.

The only live objection from my side was authority blur or mistaken primacy (`codex/round-2_reviewer-reply.md:54`). That objection fails because F-04 already marks `chmod 444` as defense-in-depth rather than primary enforcement (`findings-under-review.md:68-70`), and Topic 002's README separates Topic 009 immutability from Topic 002 firewall ownership (`README.md:47-49`). No mechanism dispute remains. Facet F is `Converged`.

## Part B — Live Disagreement

### Facet A (remainder): Pure-gap rules

Claude has correctly narrowed the dispute to five genuinely homeless rules: `V5-3`, `V5-4`, `T2-2`, `CS-6`, and `A-2` (`input_f06_category_coverage.md:93-106,129-142`; `claude_code/round-3_author-reply.md:89-108`). The current reply still does not prove that Topic 002 must change the v1 content vocabulary now.

1. Option 3 does not solve the problem it names. An optional `structural_prior: boolean` field re-labels the same cross-cutting property already carried by `empirical_residue`; it still does not tell the implementer whether a rule is a scope exclusion (`T2-2`), a price-structure observation (`V5-3`/`V5-4`), an empirical summary (`CS-6`), or a calibration default (`A-2`) (`claude_code/round-3_author-reply.md:93-106`; `004-meta-knowledge/final-resolution.md:332-338`). If the claimed defect is "F-06 no longer says WHAT this rule is," a single boolean does not repair it.
2. Option 2 is explicitly a stretch path, not evidence that the whitelist is wrong. The source inventory's own diagnosis is that these rules fit no existing category without stretching (`input_f06_category_coverage.md:97-106,121-125`). That can support a later human judgment about draft ergonomics; it does not yet carry the burden of proof for changing F-04's content vocabulary.
3. Option 1 already has a safe provisional route, and the record has not shown a concrete failure from that route. Topic 004 froze `UNMAPPED` + Tier 2 + SHADOW precisely to avoid blocking genuine gaps while vocabulary remains unsettled (`004-meta-knowledge/final-resolution.md:373-392`). That does not prove permanent `UNMAPPED` is ideal; it does mean the case for additional v1 vocabulary must be proportional and evidence-backed, not inferred from incompleteness alone.

So the remaining question is narrower than "can F-06 tolerate a permanent gap on its highest-risk input class." First Topic 002 must settle which of these pure-gap rules are admissible F-06 content at all. Until that boundary is fixed, the size and composition of the permanent gap remain unstable. Facet A stays `Open`.

### Facet E: Admissibility boundary

Claude's revised argument is now the right target: not "admissible by default," but "MK-04 is the permanent criterion that operationalizes the catch-all ban per rule" (`claude_code/round-3_author-reply.md:112-141`). That still overstates what the authority chain currently proves.

1. MK-04 is an admissibility lens, but Topic 004 did not authorize it to replace Topic 002's content boundary by itself. The same final-resolution file both freezes `derivation_test.json` and keeps content-gate ownership with Topic 002, while deferring the final F-06 fix back to this topic (`004-meta-knowledge/final-resolution.md:190,203-205,329-340,345-392`).
2. The design brief still carries two live constraints that are not identical: structural leakage is bounded via Tier 2 metadata, and lessons that tilt family/architecture/calibration-mode are contamination (`docs/design_brief.md:46-55,84-89`; `findings-under-review.md:59-61`). A `Partially` derivable rule can satisfy the first statement and still violate the second. Provenance mixedness and search-space tilt are related, but they are not the same predicate.
3. Claude's own examples show the gap. `T2-2` excludes microstructure from the mainline swing horizon; that is not merely a provenance fact, it narrows the architecture/search branch allowed to survive (`input_f06_category_coverage.md:102`; `claude_code/round-3_author-reply.md:136`). `A-2` hard-codes a numeric discovery default, which sits uncomfortably close to the brief's ban on calibration-mode tilt (`input_f06_category_coverage.md:105-106`; `docs/design_brief.md:49,84-89`; `claude_code/round-3_author-reply.md:137`). MK-04 can show these rules are partially derived; it does not by itself answer whether their empirical residue still tilts the search enough to remain blocked.

So my position is narrower than round 2 but unchanged in substance: MK-04 is necessary input to the content gate, not yet proved sufficient to replace the current catch-all boundary. Topic 002 still owes an explicit rule for when partial derivability is not enough because the residue remains family/architecture/calibration-mode steering. Facet E stays `Open`.

### Facet B (Codex): `PROVENANCE_AUDIT_SERIALIZATION`

Claude now accepts the same narrowed record I do: overload is real, split-now is not proved, and the remaining disagreement is timing/granularity (`claude_code/round-3_author-reply.md:153-157`; `input_f06_category_coverage.md:81-83,137-142`; `docs/design_brief.md:40-44,78-82`). That is a `Judgment call`, not an open mechanism defect.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| X38-D-04 | 5th mutually exclusive enum rejected; filesystem enforcement converged; pure-gap handling remains contingent on unresolved admissibility boundary | Thiếu sót | Open | — | — |

### Facet tracking (internal to X38-D-04)

| Facet | Subject | Round 3 reviewer position | Phân loại | Trạng thái |
|---|---|---|---|---|
| A | Category gap — mechanism | Sub-point `5th mutually exclusive enum` is Converged and rejected. Remaining pure-gap mechanism is not yet settled: `UNMAPPED` is safe provisionally, annotation does not supply the claimed content-type signal, and the admissible pure-gap set still depends on Facet E | Thiếu sót | Open |
| B (author) | MK-07 interim → permanent | GAP/AMBIGUITY distinction stands. Permanent handling tracks Facets A + E | Thiếu sót | Open (contingent) |
| B (Codex) | `PROVENANCE_AUDIT_SERIALIZATION` overload | Overload is real; split-now is not proved; remaining tradeoff is timing/granularity | Judgment call | **Judgment call** |
| C | `STOP_DISCIPLINE` thinness | Separate v1 enum not justified; consolidate into `ANTI_PATTERN` | Judgment call | **Converged** |
| D (Codex) | State machine complexity | Topic 002 owns transition-integrity properties, not the protocol-state graph | Thiếu sót | **Converged** |
| E (Codex) | Admissibility boundary | MK-04 is necessary input but not yet sufficient to replace the current catch-all ban on family/architecture/calibration-mode tilt | Thiếu sót | Open |
| F (author) | Filesystem enforcement | `chmod` remains a secondary guardrail only; no live authority conflict with Topic 009 | Thiếu sót | **Converged** |
