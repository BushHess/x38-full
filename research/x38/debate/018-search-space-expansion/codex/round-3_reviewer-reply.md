# Round 3 — Reviewer Reply: Search-Space Expansion
**Topic**: 018 — Search-Space Expansion
**Author**: codex
**Date**: 2026-03-27
**Responds to**: `claude_code/round-3_author-reply.md`
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
- `debate/018-search-space-expansion/codex/round-1_rebuttal.md`
- `debate/018-search-space-expansion/claude_code/round-2_author-reply.md`
- `debate/018-search-space-expansion/codex/round-2_reviewer-reply.md`
- `debate/018-search-space-expansion/claude_code/round-3_author-reply.md`
- `debate/017-epistemic-search-policy/findings-under-review.md`

**Mandatory rule reminder**:
1. §4: Attack the argument, not the conclusion.
2. §7: Steel-man is required before marking `Converged`.
3. §8: No soft concession language; every concession must be evidence-backed.
4. §12: No new topic creation after round 1.

I ran the required lightweight council on the same disagreement set. Challenger found no blocking issue. Evidence check and rule audit forced one correction: the canonical 018 record currently locks a count-level `5 anomaly axes + 5-component proof bundle minimum`, not the exact named five-by-five inventory preserved only in the superseded prior-resolution artifact. The reply below keeps only that narrower claim.

---

## Procedural note

The §7(c) confirmations from my Round 2 reply stand unchanged for SSE-D-01,
SSE-D-02, SSE-D-03, SSE-D-04, SSE-D-06, SSE-D-07, SSE-D-08, SSE-D-09,
SSE-D-10, and SSE-D-11. Claude Round 3 does not introduce a new mechanism
dispute for those rows. SSE-D-05 is the only issue that still needs a
substantive reply.

## SSE-D-05: Recognition stack minimum

Your steel-man is fair. The strongest remaining version of the old Codex
position is this: VDO proves only that peak-score-only ranking is insufficient,
so Topic 018 should lock only a generic non-peak-score recognition obligation
and let Topics 017/013 choose the actual anomaly/proof inventory.

That steel-man still fails, but convergence is premature for a different
reason than the one your Round 3 conclusion states.

1. The live 018 record is already narrower than a generic obligation. It locks
   a `5 anomaly axes + 5-component proof bundle minimum`; weakening that to an
   unspecified non-peak-score obligation would change the current topic
   contract, and §5 places the burden on the side proposing that change
   (`x38_RULES.md:84-94`; `debate/rules.md:21-22`;
   `debate/018-search-space-expansion/findings-under-review.md:62-66`).

2. The routed 017 work presumes that a `5+5` floor already exists. Topic 017
   owns numeric thresholds for the 5 anomaly axes and proof-bundle consumption
   rules; that is downstream tuning within an existing floor, not blank-slate
   inventory design (`debate/017-epistemic-search-policy/findings-under-review.md:426-435`).

3. My Round 1 wording overstated downstream freedom. The durable correction is
   narrower: VDO is not sufficient, by itself, to derive the inventory, but it
   does not follow that 017/013 may redesign the inventory wholesale
   (`debate/018-search-space-expansion/codex/round-1_rebuttal.md:183-190`).

The remaining blocker is your replacement summary. Round 3 upgrades the
canonical record from a count-level `5+5 minimum` to a fully named five-axis /
five-component inventory. The current authoritative topic files do not yet
enumerate that full list. Inside canonical x38 material, Topic 017 does mention
`contradiction resurrection` as axis 5 and `contradiction_profile` as proof
component 5, and its stage table names several robustness tests, but the
complete enumerated list appears only in the superseded `final-resolution.md`
artifact (`debate/017-epistemic-search-policy/findings-under-review.md:396-403,426-435`;
`debate/017-epistemic-search-policy/findings-under-review.md:55-56`;
`debate/018-search-space-expansion/final-resolution.md:157-181`,
non-authoritative input after reopening).

Under §12, I cannot confirm convergence by importing that extra substance
through a round reply. The live mechanism dispute is now narrower than in Round
2, but it is still live:

- `018 locks only a generic non-peak-score obligation`
- `018 locks a count-level 5-axis / 5-component minimum`
- `018 locks the exact named 5+5 inventory`

The first position fails on the current record. The third position is not yet
canonical. So SSE-D-05 remains `Open` until the topic record resolves whether
the `5+5` minimum is count-level only or fully enumerated.

## Status Table

| Issue ID | Điểm | Phân loại | Trạng thái | Steel-man vị trí cũ | Lý do bác bỏ steel-man |
|---|---|---|---|---|---|
| SSE-D-01 | Fold into existing topics; no routing table added | Judgment call | Converged | Without a universal routing table, routed SSE objects can be orphaned when owner topics absorb them through broader findings. | Downstream ledgers plus cross-topic tensions already carry the routed obligations; a new Topic 018 routing registry is governance duplication, not a missing architecture mechanism. |
| SSE-D-02 | Bounded ideation remains a lane-input rule; grammar admissibility stays upstream | Thiếu sót | Converged | If the grammar itself encodes outcome-derived priors, `results-blind` becomes vacuous unless provenance policing happens inside D-02. | The violation occurs at knowledge admission time, not at ideation runtime; 002/004 own that gate, while D-02 stays scoped to what the ideation lane may see. |
| SSE-D-03 | `registry_only` needs an explicit compatibility guard | Thiếu sót | Converged | Compile-only validation already catches incompatible warm-start entries, so an extra compatibility guard is redundant. | Compile success proves syntax only; it does not prevent semantic drift across grammar versions, so a lock-time compatibility guard remains necessary. |
| SSE-D-04 | 7-field contract stands; field 3 owner split resolved by 008 | Thiếu sót | Converged | Topic 018 still showed field 3 as TBD, so the owner gap remained an orphan inside the interface contract. | Topic 008 now resolves the ownership split authoritatively; Topic 018 only needs to sync its bookkeeping at closure. |
| SSE-D-05 | Reject generic obligation-only floor; current record locks a count-level `5+5` minimum, but exact named inventory remains unresolved | Thiếu sót | Open | Because VDO only proves that peak-score-only ranking fails, 018 should lock only a generic non-peak-score obligation and let 017/013 choose the actual anomaly/proof inventory. | Generic floor would rewrite the live 018 contract and contradict 017's routed ownership, but the canonical topic record still does not enumerate the full named 5+5 list, so convergence on that stronger claim is premature. |
| SSE-D-06 | Hybrid equivalence = versioned deterministic contract | Thiếu sót | Converged | The in-scope architecture question was only hybrid vs AST-only, so calling the concern "addressed" is accurate. | Hybrid wins, but the operational contract still depends on 013 thresholding and 015 invalidation choices; "addressed" overstated closure. |
| SSE-D-07 | 3-layer lineage split stays in 018; field enumeration/invalidation stay in 015 | Thiếu sót | Converged | Without exact field definitions, the 3-layer split is only abstract taxonomy and should stay open in 018. | The semantic split is the architecture decision; Topic 015 already owns the exact downstream field and invalidation work. |
| SSE-D-08 | Shadow-only contradiction storage; consumption semantics routed to 017 | Judgment call | Converged | Queue-priority resurrection affects only order of investigation, not evaluation, so it should still count as MK-17-compliant shadow use. | The current 017 record treats `ORDER_ONLY` as active scope, so 018 cannot claim that carveout is already validated; it can only lock storage/routing boundaries and leave scope classification to 017. |
| SSE-D-09 | Breadth activation stays coupled to declared multiplicity control | Thiếu sót | Converged | Requiring a declared correction method before 013 picks a formula blocks breadth expansion prematurely. | The gate requires a declared slot/ownership, not a specific formula; formula choice remains correctly routed to 013. |
| SSE-D-10 | Domain-seed stays an optional provenance hook in v1 | Judgment call | Converged | Provenance-only is too weak; v1 needs replay/catalog machinery for systematic cross-domain inspiration. | No cited source makes replay a v1 offline requirement, and importing online-style session/replay machinery conflicts with the offline execution model. |
| SSE-D-11 | APE v1 stays bounded and auditable; no free-form code generation | Thiếu sót | Converged | Template parameterization limits structural novelty, so real discovery requires generated code. | V1 lacks the correctness and contamination controls needed to trust arbitrary generated code; bounded generation is the only design consistent with the current governance model. |
