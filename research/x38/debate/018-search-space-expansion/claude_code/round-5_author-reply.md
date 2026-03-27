# Round 5 — Author Reply: Search-Space Expansion
**Topic**: 018 — Search-Space Expansion
**Author**: claude_code
**Date**: 2026-03-27
**Responds to**: `codex/round-4_reviewer-reply.md`
**Scope**: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `debate/018-search-space-expansion/README.md`
- `debate/018-search-space-expansion/findings-under-review.md`
- `debate/018-search-space-expansion/final-resolution.md` (non-authoritative input after reopening)
- `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md`
- `debate/018-search-space-expansion/claude_code/round-2_author-reply.md`
- `debate/018-search-space-expansion/claude_code/round-3_author-reply.md`
- `debate/018-search-space-expansion/claude_code/round-4_author-reply.md`
- `debate/018-search-space-expansion/codex/round-1_rebuttal.md`
- `debate/018-search-space-expansion/codex/round-2_reviewer-reply.md`
- `debate/018-search-space-expansion/codex/round-3_reviewer-reply.md`
- `debate/018-search-space-expansion/codex/round-4_reviewer-reply.md`
- `debate/017-epistemic-search-policy/findings-under-review.md`

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

---

## Procedural note

Codex R4 confirms all 10 previously Converged issues (SSE-D-01, D-02, D-03,
D-04, D-06, D-07, D-08, D-09, D-10, D-11) as unchanged. SSE-D-05 remains the
sole Open issue. This reply addresses Codex's R4 argument that a count-level
`5+5` floor without named inventory leaves the 018→017 threshold routing
incoherent.

---

## PART A — STEEL-MAN ATTEMPT

### SSE-D-05: Recognition stack minimum

**Steel-man for Codex's position** (count-level closure leaves the 018→017
contract structurally incomplete):

Topic 017's canonical `findings-under-review.md:432-434` specifies per-item
downstream work: "Numeric thresholds for each of the 5 anomaly axes" and "Proof
bundle consumption rules (what constitutes 'passing' a proof component)." The
word "each" requires identifiable target objects, not just a cardinality
constraint. A count-level floor (5+5) tells 017 how many objects exist but not
which objects to threshold. Prompt C's synthesis step converts converged
decisions into spec sections (`debate/prompt_template.md:126-127`), but if the
converged decision is count-level only, there is insufficient substance to
produce a named list without importing from the superseded
`final-resolution.md` — which both sides agree is procedurally unsound. The
authority gap is therefore structural: it determines whether 017 can begin
per-axis threshold work or must first wait for 018 to name the axes. This is
not a bookkeeping question but an ownership boundary question with downstream
binding impact.

**Why the steel-man partially holds — leading to an amended convergence text**:

1. **The threshold presupposition argument is valid.** Codex R4 point 1
   correctly identifies that 017's per-item threshold work presupposes named
   objects. I was wrong to characterize this as "a closure canonicalization
   task" in R4 — the gap is not about where a list is written but about whether
   the 018→017 routing contract has sufficient content for 017 to act on. A
   count-level floor without named inventory is structurally incomplete as an
   interface contract. This concession is based on the specific evidence at
   `debate/017-epistemic-search-policy/findings-under-review.md:431-434`:
   017's routed work is per-axis and per-component, which requires axis/component
   identity.

2. **However, the remedy is to name the inventory within the converged text,
   not to keep SSE-D-05 Open.** Codex R4 frames two competing positions:
   - "018 may close on a count-level 5+5 floor with unnamed inventory"
   - "018 must make the inventory itself authoritative before downstream
     threshold-only routing is coherent"

   I now accept the second position's **requirement** (the inventory must be
   authoritative) while proposing that it be satisfied **within this round's
   convergence text**, not through further mechanism debate. The reason: there
   is no mechanism dispute about the inventory's composition. No debater has
   proposed an alternative axis or component in 11 rounds of debate (7 prior
   4-agent rounds + 4 standard 2-agent rounds). The axes and components
   describe architectural detection categories derived from the project's
   empirical evidence (VDO discovery, cross-study robustness, cost analysis).
   They are substantively uncontested.

3. **My R4 error was about sourcing, not content.** In R3 I named the full
   inventory citing `final-resolution.md:157-181` (non-authoritative). In R4 I
   withdrew the named list because the source was procedurally unsound. Codex
   accepted the withdrawal (R4:88-90). The correction was about the
   **provenance chain**, not about the **substance** of the named items. The
   substance remains uncontested. I can now name the inventory sourced from the
   uncontested debate record itself — the 11 rounds in which these categories
   were discussed, endorsed, and never challenged — rather than from a specific
   non-authoritative document.

4. **Codex's four R4 points are resolved by naming the inventory:**

   - **Point 1** (threshold presupposes objects): Resolved. The amended text
     names all 10 objects. 017 has canonical targets to threshold.
   - **Point 2** (017 only partially names the inventory): Resolved. 017 names
     axis 5 and component 5 (`findings-under-review.md:402-403`); the amended
     018 text names all 10, completing the enumeration at the source.
   - **Point 3** (Prompt C cannot import new substance): Moot. The names are
     in the converged text, not deferred to Prompt C. Closure syncs what is
     already converged.
   - **Point 4** (ambiguity about who owns unnamed members): Dissolved. There
     are no unnamed members. 018 owns the composition; 017/013 own thresholds
     and consumption rules within that composition.

**Conclusion**: Codex is correct that count-level closure is structurally
insufficient for the 018→017 routing contract. I amend the converged mechanism
to include the named inventory, sourced from the uncontested debate record. The
amended convergence text:

> **018 locks a named `5 anomaly axes + 5-component proof bundle` minimum
> floor.**
>
> **5 anomaly axes** (surprise queue admission requires ≥1 non-peak-score):
> 1. Decorrelation outlier
> 2. Plateau width champion
> 3. Cost stability
> 4. Cross-resolution consistency
> 5. Contradiction resurrection
>
> **5-component proof bundle minimum**:
> 1. `nearest_rival_audit`
> 2. `plateau_stability_extract`
> 3. `cost_sensitivity_test`
> 4. `ablation_or_perturbation_test`
> 5. `contradiction_profile`
>
> **Recognition topology** (fixed):
> `surprise_queue → equivalence_audit → proof_bundle →
> freeze_comparison_set → candidate_phenotype → contradiction_registry`
>
> **Downstream authority**: Topics 017/013 receive tuning-only authority —
> numeric thresholds for each named axis, consumption rules for each named
> component. They do not add, remove, or replace axes or components.

This text is self-contained: the 018→017 contract now supplies named objects
for 017's per-item threshold work. It preserves the R4 procedural correction
(no sourcing from non-authoritative `final-resolution.md`). The names are
stated as architectural definitions within the converged mechanism, not
imported from an external document.

**Proposed status**: Converged — waiting for Codex to confirm (§7c).

---

## PART B — CONTINUED DEBATE

No issues remain in continued debate. All 11 issues have completed the
steel-man cycle (10 confirmed Converged, 1 pending §7c with amended text).

---

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| SSE-D-01 | Fold into existing topics; no routing table added | Judgment call | Converged | Without a universal routing table, routed SSE objects can be orphaned when owner topics absorb them through broader findings. | Downstream ledgers plus cross-topic tensions already carry the routed obligations; a new Topic 018 routing registry is governance duplication, not a missing architecture mechanism. |
| SSE-D-02 | Bounded ideation remains a lane-input rule; grammar admissibility stays upstream | Thiếu sót | Converged | If the grammar itself encodes outcome-derived priors, `results-blind` becomes vacuous unless provenance policing happens inside D-02. | The violation occurs at knowledge admission time, not at ideation runtime; 002/004 own that gate, while D-02 stays scoped to what the ideation lane may see. |
| SSE-D-03 | `registry_only` needs an explicit compatibility guard | Thiếu sót | Converged | Compile-only validation already catches incompatible warm-start entries, so an extra compatibility guard is redundant. | Compile success proves syntax only; it does not prevent semantic drift across grammar versions, so a lock-time compatibility guard remains necessary. |
| SSE-D-04 | 7-field contract stands; field 3 owner split resolved by 008 | Thiếu sót | Converged | Topic 018 still showed field 3 as TBD, so the owner gap remained an orphan inside the interface contract. | Topic 008 now resolves the ownership split authoritatively; Topic 018 only needs to sync its bookkeeping at closure. |
| SSE-D-05 | Named `5+5` inventory with topology; downstream tunes thresholds/consumption within named composition | Thiếu sót | Converged — pending §7c | Count-level closure leaves 018→017 routing incomplete: 017 specifies per-item threshold work (`findings-under-review.md:432-434`) presupposing named objects; Prompt C cannot synthesize named list from count-only converged text without importing non-authoritative material. | Threshold presupposition is valid (conceded). Fix: name the inventory in the converged text, sourced from the uncontested debate record (11 rounds, zero challenges to composition). No mechanism dispute remains — both sides endorse the same architecture; the gap was specification completeness, now resolved by the amended text. |
| SSE-D-06 | Hybrid equivalence = versioned deterministic contract | Thiếu sót | Converged | The in-scope architecture question was only hybrid vs AST-only, so calling the concern "addressed" is accurate. | Hybrid wins, but the operational contract still depends on 013 thresholding and 015 invalidation choices; "addressed" overstated closure. |
| SSE-D-07 | 3-layer lineage split stays in 018; field enumeration/invalidation stay in 015 | Thiếu sót | Converged | Without exact field definitions, the 3-layer split is only abstract taxonomy and should stay open in 018. | The semantic split is the architecture decision; Topic 015 already owns the exact downstream field and invalidation work. |
| SSE-D-08 | Shadow-only contradiction storage; consumption semantics routed to 017 | Judgment call | Converged | Queue-priority resurrection affects only order of investigation, not evaluation, so it should still count as MK-17-compliant shadow use. | The current 017 record treats `ORDER_ONLY` as active scope, so 018 cannot claim that carveout is already validated; it can only lock storage/routing boundaries and leave scope classification to 017. |
| SSE-D-09 | Breadth activation stays coupled to declared multiplicity control | Thiếu sót | Converged | Requiring a declared correction method before 013 picks a formula blocks breadth expansion prematurely. | The gate requires a declared slot/ownership, not a specific formula; formula choice remains correctly routed to 013. |
| SSE-D-10 | Domain-seed stays an optional provenance hook in v1 | Judgment call | Converged | Provenance-only is too weak; v1 needs replay/catalog machinery for systematic cross-domain inspiration. | No cited source makes replay a v1 offline requirement, and importing online-style session/replay machinery conflicts with the offline execution model. |
| SSE-D-11 | APE v1 stays bounded and auditable; no free-form code generation | Thiếu sót | Converged | Template parameterization limits structural novelty, so real discovery requires generated code. | V1 lacks the correctness and contamination controls needed to trust arbitrary generated code; bounded generation is the only design consistent with the current governance model. |
