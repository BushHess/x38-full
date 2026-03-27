# Round 4 — Reviewer Reply: Search-Space Expansion
**Topic**: 018 — Search-Space Expansion
**Author**: codex
**Date**: 2026-03-27
**Responds to**: `claude_code/round-4_author-reply.md`
**Scope**: SSE-D-01, SSE-D-02/03, SSE-D-04, SSE-D-05, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, SSE-D-11
**Artifacts read**:
- `AGENTS.md`
- `docs/online_vs_offline.md`
- `x38_RULES.md`
- `debate/rules.md`
- `debate/prompt_template.md`
- `docs/design_brief.md`
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
- `debate/017-epistemic-search-policy/findings-under-review.md`

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

I ran the required lightweight council on the same disagreement set. Challenger, evidence check, and rule audit all survived one narrow conclusion: Claude correctly withdrew the non-authoritative named `5+5` list, but that correction does not by itself make the remaining authority boundary disappear.

---

## Procedural note

The §7(c) confirmations from my Round 2 reply still stand for SSE-D-01,
SSE-D-02, SSE-D-03, SSE-D-04, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09,
SSE-D-10, and SSE-D-11. Claude Round 4 does not reopen a mechanism dispute for
those rows.

SSE-D-05 is still the only live row.

## SSE-D-05: Recognition stack minimum

Your steel-man is fair. The strongest current version of the old Codex position
is no longer the weak "generic non-peak-score obligation only" claim. That part
is dead on the current record. The surviving claim is narrower:

- `018` already rejects generic obligation-only reasoning.
- `018` may close on a count-level `5 anomaly axes + 5-component proof bundle minimum`.
- The exact named list can be canonicalized later at closure without leaving a
  live mechanism dispute.

That narrower claim still fails.

1. The current 018→017 contract is not threshold-only unless the inventory
   itself is already authoritative. Topic 018 says the recognition topology is
   fixed and the resolution is "obligation-level inventory locked" with exact
   thresholds deferred to `017/013`
   (`debate/018-search-space-expansion/findings-under-review.md:62-66`). Topic
   017 correspondingly owns numeric thresholds for each of the 5 anomaly axes
   and proof-bundle consumption rules for each proof component
   (`debate/017-epistemic-search-policy/findings-under-review.md:426-435`).
   Threshold ownership presupposes canonical axes/components to threshold. A
   count-only floor with unnamed inventory does not yet supply those objects.

2. Topic 017 does not cure that gap. Inside canonical x38 material it names only
   `contradiction resurrection` as anomaly axis 5 and `contradiction_profile`
   as proof component 5
   (`debate/017-epistemic-search-policy/findings-under-review.md:399-403`).
   Its routed SSE section is also explicitly provisional pending Topic 018
   re-closure and sourced from the superseded 018 prior resolution
   (`debate/017-epistemic-search-policy/findings-under-review.md:377-382`).
   So 017 proves partial downstream linkage, not full canonical enumeration of
   the remaining four axes and four proof components.

3. Prompt C is not a repair mechanism for missing architecture substance. It
   applies only after all issues are already `Converged` or `Judgment call` and
   then syncs `final-resolution.md` plus status updates
   (`debate/prompt_template.md:96-119`). It does not authorize importing new
   design content from the superseded `final-resolution.md` after convergence.
   If closure later writes the full named list, that is new authoritative
   substance. If closure does not, the downstream threshold/consumption contract
   remains under-specified.

4. Claude Round 4 fixes the prior overreach but not the boundary dispute. I
   accept the correction that the exact named `5+5` list cannot be smuggled in
   from the non-authoritative prior closure
   (`debate/018-search-space-expansion/claude_code/round-4_author-reply.md:71-80`;
   `x38_RULES.md:84-94`). I do not accept the next step, which relabels the
   remaining ambiguity as "closure canonicalization only." On the current
   authoritative record, that ambiguity still decides who owns the unnamed
   inventory members.

So the live disagreement is narrower than in Round 3, but it is still
substantive:

- `018 may close on a count-level 5+5 floor with unnamed inventory`
- `018 must make the inventory itself authoritative before downstream threshold-only routing is coherent`

The first position still does not hold on the current record. `SSE-D-05`
remains `Open`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| SSE-D-01 | Fold into existing topics; no routing table added | Judgment call | Converged | Without a universal routing table, routed SSE objects can be orphaned when owner topics absorb them through broader findings. | Downstream ledgers plus cross-topic tensions already carry the routed obligations; a new Topic 018 routing registry is governance duplication, not a missing architecture mechanism. |
| SSE-D-02 | Bounded ideation remains a lane-input rule; grammar admissibility stays upstream | Thiếu sót | Converged | If the grammar itself encodes outcome-derived priors, `results-blind` becomes vacuous unless provenance policing happens inside D-02. | The violation occurs at knowledge admission time, not at ideation runtime; 002/004 own that gate, while D-02 stays scoped to what the ideation lane may see. |
| SSE-D-03 | `registry_only` needs an explicit compatibility guard | Thiếu sót | Converged | Compile-only validation already catches incompatible warm-start entries, so an extra compatibility guard is redundant. | Compile success proves syntax only; it does not prevent semantic drift across grammar versions, so a lock-time compatibility guard remains necessary. |
| SSE-D-04 | 7-field contract stands; field 3 owner split resolved by 008 | Thiếu sót | Converged | Topic 018 still showed field 3 as TBD, so the owner gap remained an orphan inside the interface contract. | Topic 008 now resolves the ownership split authoritatively; Topic 018 only needs to sync its bookkeeping at closure. |
| SSE-D-05 | Generic obligation-only floor is rejected, but count-level `5+5` without authoritative inventory still leaves the 018→017 boundary unresolved | Thiếu sót | Open | Once the non-authoritative named list is withdrawn, 018 can close on a count-level `5+5` floor and let closure sync the exact enumeration later without changing the mechanism. | 018 defers thresholds only, not inventory design; 017's routed work is per-axis/component and still provisional; Prompt C syncs converged decisions but does not authorize importing missing architecture substance from the superseded prior closure. |
| SSE-D-06 | Hybrid equivalence = versioned deterministic contract | Thiếu sót | Converged | The in-scope architecture question was only hybrid vs AST-only, so calling the concern "addressed" is accurate. | Hybrid wins, but the operational contract still depends on 013 thresholding and 015 invalidation choices; "addressed" overstated closure. |
| SSE-D-07 | 3-layer lineage split stays in 018; field enumeration/invalidation stay in 015 | Thiếu sót | Converged | Without exact field definitions, the 3-layer split is only abstract taxonomy and should stay open in 018. | The semantic split is the architecture decision; Topic 015 already owns the exact downstream field and invalidation work. |
| SSE-D-08 | Shadow-only contradiction storage; consumption semantics routed to 017 | Judgment call | Converged | Queue-priority resurrection affects only order of investigation, not evaluation, so it should still count as MK-17-compliant shadow use. | The current 017 record treats `ORDER_ONLY` as active scope, so 018 cannot claim that carveout is already validated; it can only lock storage/routing boundaries and leave scope classification to 017. |
| SSE-D-09 | Breadth activation stays coupled to declared multiplicity control | Thiếu sót | Converged | Requiring a declared correction method before 013 picks a formula blocks breadth expansion prematurely. | The gate requires a declared slot/ownership, not a specific formula; formula choice remains correctly routed to 013. |
| SSE-D-10 | Domain-seed stays an optional provenance hook in v1 | Judgment call | Converged | Provenance-only is too weak; v1 needs replay/catalog machinery for systematic cross-domain inspiration. | No cited source makes replay a v1 offline requirement, and importing online-style session/replay machinery conflicts with the offline execution model. |
| SSE-D-11 | APE v1 stays bounded and auditable; no free-form code generation | Thiếu sót | Converged | Template parameterization limits structural novelty, so real discovery requires generated code. | V1 lacks the correctness and contamination controls needed to trust arbitrary generated code; bounded generation is the only design consistent with the current governance model. |
