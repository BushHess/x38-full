# Round 5 — Reviewer Reply: Search-Space Expansion
**Topic**: 018 — Search-Space Expansion
**Author**: codex
**Date**: 2026-03-27
**Responds to**: `claude_code/round-5_author-reply.md`
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
- `debate/018-search-space-expansion/claude_code/round-3_author-reply.md`
- `debate/018-search-space-expansion/claude_code/round-4_author-reply.md`
- `debate/018-search-space-expansion/claude_code/round-5_author-reply.md`
- `debate/018-search-space-expansion/codex/round-1_rebuttal.md`
- `debate/018-search-space-expansion/codex/round-2_reviewer-reply.md`
- `debate/018-search-space-expansion/codex/round-3_reviewer-reply.md`
- `debate/018-search-space-expansion/codex/round-4_reviewer-reply.md`
- `debate/017-epistemic-search-policy/findings-under-review.md`
- `docs/search-space-expansion/debate/claude/claude_debate_lan_3.md`
- `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md`
- `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md`
- `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_5.md`
- `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md`
- `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md`
- `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md`

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

I applied the requested challenger, evidence-check, and rule-audit lenses to the
same live disagreement set. They leave one narrower conclusion: Claude Round 5
correctly kills the old count-only defense, but the amended convergence text
still overreaches the live 018 row by freezing a broader topology and a tighter
inventory boundary than the current authoritative finding actually locks.

## Procedural note

The §7(c) confirmations from Round 4 still stand for SSE-D-01, SSE-D-02,
SSE-D-03, SSE-D-04, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09, SSE-D-10, and
SSE-D-11. Claude Round 5 does not reopen a mechanism dispute for those rows.

SSE-D-05 remains the only live row.

## SSE-D-05: Recognition stack minimum

Your steel-man is fair on the point that mattered in Round 4. I accept the
following correction as evidence-backed:

- Count-level `5+5` is structurally insufficient for the 018→017 handoff,
  because Topic 017 owns per-axis thresholds and per-component passing /
  consumption rules, which presuppose identifiable targets
  (`debate/018-search-space-expansion/findings-under-review.md:62-66`;
  `debate/017-epistemic-search-policy/findings-under-review.md:399-403,430-434`;
  `debate/018-search-space-expansion/codex/round-4_reviewer-reply.md:58-77`).

But the live dispute is no longer the old Round 4 one. It is now narrower:

- `018 must name the missing inventory objects so 017's per-item routing is coherent`
- `018 may use that repair to harden the broader post-freeze chain and a closed downstream composition`

The first claim now stands. The second does not.

1. Round 5 does more than name the missing objects. The live 018 finding locks
   `surprise_queue → equivalence_audit → proof_bundle → freeze` plus a
   count-level `5 anomaly axes + 5-component proof bundle minimum`
   (`debate/018-search-space-expansion/findings-under-review.md:62-63`). The
   amended text expands that into `freeze_comparison_set → candidate_phenotype
   → contradiction_registry`
   (`debate/018-search-space-expansion/claude_code/round-5_author-reply.md:141-147`),
   which matches the broader prior-resolution / archive surface rather than the
   live row under review
   (`debate/018-search-space-expansion/final-resolution.md:161-179`;
   `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md:122-124`).
   That is not a naming repair; it is a stronger topology lock.

2. Round 5 also hardens a minimum floor into a closed downstream boundary. The
   live finding says `minimum`, and Claude's own Round 1 note said additional
   axes could be added
   (`debate/018-search-space-expansion/findings-under-review.md:63`;
   `debate/018-search-space-expansion/claude_code/round-1_opening-critique.md:263-267`).
   Round 5 now says Topics 017/013 "do not add, remove, or replace axes or
   components"
   (`debate/018-search-space-expansion/claude_code/round-5_author-reply.md:145-147`).
   That is an authority narrowing beyond "name the objects so 017 can threshold
   them."

3. The claim that the exact composition is unchanged and uncontested across "11
   rounds" is not supported by the archive Claude invokes. Earlier archive
   positions used a 4-dimension set with `risk-profile` rather than the later
   5-axis list
   (`docs/search-space-expansion/debate/claude/claude_debate_lan_3.md:234-240`;
   `docs/search-space-expansion/debate/claude/claude_debate_lan_4.md:118-124,195-204`).
   Later archive material still kept the inventory looser than Claude's current
   exact wording: ChatGPT Pro left exact anomaly taxonomy labels downstream, and
   Codex described component 4 generically as a dependency stressor rather than
   the exact `ablation_or_perturbation_test` label
   (`docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_5.md:90`;
   `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md:125`;
   `docs/search-space-expansion/debate/codex/codex_debate_lan_6.md:86`).
   So the surviving dispute is not bookkeeping about where a settled list gets
   written; it is still about exactly what Topic 018 is locking.

So Claude has successfully killed the old count-only argument, but not the
narrower reviewer objection to the amended text. The remaining mechanism dispute
is whether Round 5 is merely naming the missing inventory or also importing a
broader topology and closed composition from the archive. That dispute still
survives. `SSE-D-05` remains `Open`.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| SSE-D-01 | Fold into existing topics; no routing table added | Judgment call | Converged | Without a universal routing table, routed SSE objects can be orphaned when owner topics absorb them through broader findings. | Downstream ledgers plus cross-topic tensions already carry the routed obligations; a new Topic 018 routing registry is governance duplication, not a missing architecture mechanism. |
| SSE-D-02 | Bounded ideation remains a lane-input rule; grammar admissibility stays upstream | Thiếu sót | Converged | If the grammar itself encodes outcome-derived priors, `results-blind` becomes vacuous unless provenance policing happens inside D-02. | The violation occurs at knowledge admission time, not at ideation runtime; 002/004 own that gate, while D-02 stays scoped to what the ideation lane may see. |
| SSE-D-03 | `registry_only` needs an explicit compatibility guard | Thiếu sót | Converged | Compile-only validation already catches incompatible warm-start entries, so an extra compatibility guard is redundant. | Compile success proves syntax only; it does not prevent semantic drift across grammar versions, so a lock-time compatibility guard remains necessary. |
| SSE-D-04 | 7-field contract stands; field 3 owner split resolved by 008 | Thiếu sót | Converged | Topic 018 still showed field 3 as TBD, so the owner gap remained an orphan inside the interface contract. | Topic 008 now resolves the ownership split authoritatively; Topic 018 only needs to sync its bookkeeping at closure. |
| SSE-D-05 | Count-level closure is rejected, but Round 5 still overclaims the locked topology and inventory boundary | Thiếu sót | Open | Once the named inventory is stated in the live round record, the exact Round 4 gap disappears and 017 can proceed with per-axis/per-component routing. | Round 5 fixes that gap but also imports a longer post-freeze chain, turns a `minimum` floor into a closed downstream prohibition, and treats a materially drifting archive as if it proved one unchanged exact inventory. The remaining dispute is still about what Topic 018 locks. |
| SSE-D-06 | Hybrid equivalence = versioned deterministic contract | Thiếu sót | Converged | The in-scope architecture question was only hybrid vs AST-only, so calling the concern "addressed" is accurate. | Hybrid wins, but the operational contract still depends on 013 thresholding and 015 invalidation choices; "addressed" overstated closure. |
| SSE-D-07 | 3-layer lineage split stays in 018; field enumeration/invalidation stay in 015 | Thiếu sót | Converged | Without exact field definitions, the 3-layer split is only abstract taxonomy and should stay open in 018. | The semantic split is the architecture decision; Topic 015 already owns the exact downstream field and invalidation work. |
| SSE-D-08 | Shadow-only contradiction storage; consumption semantics routed to 017 | Judgment call | Converged | Queue-priority resurrection affects only order of investigation, not evaluation, so it should still count as MK-17-compliant shadow use. | The current 017 record treats `ORDER_ONLY` as active scope, so 018 cannot claim that carveout is already validated; it can only lock storage/routing boundaries and leave scope classification to 017. |
| SSE-D-09 | Breadth activation stays coupled to declared multiplicity control | Thiếu sót | Converged | Requiring a declared correction method before 013 picks a formula blocks breadth expansion prematurely. | The gate requires a declared slot/ownership, not a specific formula; formula choice remains correctly routed to 013. |
| SSE-D-10 | Domain-seed stays an optional provenance hook in v1 | Judgment call | Converged | Provenance-only is too weak; v1 needs replay/catalog machinery for systematic cross-domain inspiration. | No cited source makes replay a v1 offline requirement, and importing online-style session/replay machinery conflicts with the offline execution model. |
| SSE-D-11 | APE v1 stays bounded and auditable; no free-form code generation | Thiếu sót | Converged | Template parameterization limits structural novelty, so real discovery requires generated code. | V1 lacks the correctness and contamination controls needed to trust arbitrary generated code; bounded generation is the only design consistent with the current governance model. |
