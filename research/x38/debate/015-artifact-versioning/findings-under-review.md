# Findings Under Review — Artifact & Version Management

**Topic ID**: X38-T-15
**Opened**: 2026-03-22
**Author**: claude_code (architect)
**Split from**: Topic 003 (Protocol Engine) — F-14 và F-17 tách ra vì bản chất
"records & versioning" khác với F-05 (pipeline logic).

2 findings về session artifacts và semantic change classification.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate
- C-12: Bounded recalibration prima facie bất tương thích (liên quan F-17)

---

## F-14: State pack specification — session artifact enumeration

- **issue_id**: X38-D-14
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, gen4 evidence import)
- **current_status**: Open
- **source**: research/x37/docs/gen4/core/STATE_PACK_SPEC_v4.0_EN.md [extra-archive]

**Nội dung**:

Gen4 định nghĩa chính xác **18 artifacts bắt buộc** trong mỗi state pack.

Mapping gợi ý (gen4 → Alpha-Lab):
- `frozen_system_specs/` → `frozen_spec.json` (đã có trong F-05 Stage 7)
- `historical_seed_audit.csv` → session evaluation artifacts
- `contamination_map.md` → `contamination.json` (đã có trong F-09)
- `candidate_registry.json` → session verdict + candidate registry
- `impl/` → strategy source code snapshot
- `session_summary.md` → auto-generated session report

Artifacts gen4 **không cần** trong Alpha-Lab offline:
- `portfolio_state.json` (no live state)
- `forward_evaluation_ledger.csv` (no forward eval in discovery)
- `forward_daily_returns.csv`, `forward_equity_curve.csv` (same)

**Evidence**:
- research/x37/docs/gen4/core/STATE_PACK_SPEC_v4.0_EN.md [extra-archive]: 18 required files
- research/x37/docs/gen4/core/FORWARD_DECISION_POLICY_EN.md [extra-archive]: how artifacts are used in decisions
- x38 F-09: directory structure shows `sessions/s001/...` without enumeration

**Câu hỏi mở**:
- Artifact manifest nên là phần của `protocol_spec` hay `architecture_spec`?
- Artifacts nào là mandatory vs optional cho Alpha-Lab sessions?
- `session_summary.md`: auto-generated từ artifacts hay human-written?
- Hash manifest per-session: cần không?

---

## F-17: Semantic change classification

- **issue_id**: X38-D-17
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, gen4 evidence import)
- **current_status**: Open
- **source**: research/x37/docs/gen4/core/research_constitution_v4.0.yaml §semantic_change [extra-archive]

**Nội dung**:

Gen4 phân loại thay đổi nào cần new `system_version_id` (= invalidate kết quả):

**CẦN version mới** (invalidate results):
- Feature formula, threshold, lookback/window, entry/exit rule change
- Position sizing, cost handling, warmup semantics change
- Data cleaning rule, tie-break logic, objective function change
- Bugfix affecting trade log or PnL on seen data

**KHÔNG CẦN version mới** (results vẫn valid):
- Comments, docstrings, rename, formatting, packaging
- Logging, export format, validator/test changes
- Pure refactor (provably bit-identical output)
- Bugfix proven to not change trades/PnL

**Classification test**: Chạy frozen algorithm trên cùng data trước và sau change.
Nếu trade log hoặc PnL path khác **1 bit** → cần version mới.

Alpha-Lab cần classification tương tự:

| Thay đổi loại | Ảnh hưởng | Action |
|---|---|---|
| Engine code (data alignment, fill logic) | Thay đổi trade log | Invalidate ALL sessions dùng engine cũ |
| Cost model | Thay đổi PnL | Invalidate sessions dùng cost cũ |
| Feature computation | Thay đổi signals | Invalidate sessions dùng feature cũ |
| Metrics computation | Thay đổi ranking | Invalidate sessions dùng metrics cũ |
| Protocol logic (gating, selection) | Thay đổi verdict | Case-by-case |
| Logging, formatting, CLI | Không ảnh hưởng results | No invalidation |

**Evidence**:
- research/x37/docs/gen4/core/research_constitution_v4.0.yaml §semantic_change [extra-archive]: full classification + bit-identical test
- x38 F-11: covers session immutability but not framework code changes

**Câu hỏi mở**:
- Bit-identical trade log test khả thi cho Alpha-Lab?
- Khi engine change invalidates old sessions: re-run tự động hay manual trigger?
- Invalidation scope: toàn bộ sessions hay chỉ affected?
- Cần engine_version field trong session metadata?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Protocol stages define WHEN artifacts are produced; F-14 defines WHAT is produced — if 003 changes stage boundaries, artifact enumeration may need updating | 003 owns stage structure; 015 adapts artifact spec |
| 011 | F-28 | **B-02 CONTRADICTION (HIGH)**: F-17 (this topic) says sizing change = semantic change = new algo_version. F-28 (Topic 011) says sizing = deployment concern = deploy_version, NOT algo_version. Direct contradiction. F-28 proposes unit-exposure canonicalization as resolution — if adopted, F-17 classification table MUST be amended to exclude sizing from semantic changes. **REQUIRES JOINT DECISION with Topic 011.** | 011 debates F-28 first (boundary decision); 015 amends F-17 accordingly. Cannot close 015 F-17 independently until 011 F-28 decided. |
| 016 | C-12 | Bounded recalibration (if adopted) may create semantic changes mid-campaign that F-17 must classify — current classification assumes freeze-once model | 016 owns decision |
| 017A/017B | ESP-01 (017A), ESP-02 (017B) | Topics 017A+017B introduce 5+ new mandatory artifacts: epistemic_delta.json (Stage 8, 017A), coverage_map (Stages 3/7, 017A), phenotype_pack (Stage 7, 017B), comparison_set (Stage 7, 017B), prior_registry (inter-campaign, 017B). F-14 must enumerate these in state pack; F-17 must classify when ESP artifact changes invalidate prior results. | 017A/017B define artifact contracts; 015 owns enumeration + invalidation rules |
| 018 | SSE-07, SSE-08, SSE-04-INV | Discovery lineage, contradiction registry, and invalidation cascade details routed from Topic 018 (CLOSED 2026-03-27). Routing confirmed. | 015 owns implementation; 018 provides architectural context (confirmed). |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-14 | State pack specification — 18 artifacts (từ gen4) | Thiếu sót | Open |
| X38-D-17 | Semantic change classification (từ gen4) | Thiếu sót | Open |
| X38-SSE-07 | Discovery lineage field enumeration + invalidation (từ Topic 018) | Thiếu sót | Open |
| X38-SSE-08 | Contradiction row schema + retention (từ Topic 018) | Thiếu sót | Open |
| X38-SSE-04-INV | Invalidation cascade details (từ Topic 018) | Thiếu sót | Open |

---

## Issues routed from Topic 018 — Search-Space Expansion (2026-03-26)

Architecture-level decisions from Topic 018 (**CLOSED** 2026-03-27 —
standard 2-agent debate completed, 10 Converged + 1 Judgment call). These issues
represent confirmed implementation obligations.
Source: `debate/018-search-space-expansion/final-resolution.md` (authoritative).

---

## SSE-D-07: Discovery lineage field enumeration + invalidation matrix

- **issue_id**: X38-SSE-07
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, OI-04)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): discovery lineage splits into 3 layers with
different invalidation semantics: `feature_lineage`, `candidate_genealogy`,
`proposal_provenance` (SSE-D-07).

Topic 015 owns:
1. Exact field enumeration for each of the 3 layers
2. Invalidation matrix: which artifact changes trigger which lineage invalidations
3. Raw lineage preservation rule (raw always preserved; derived artifacts invalidated)

**Constraint (decided by Topic 018, confirmed 2026-03-27)**: Derived artifacts (`coverage_map`, `cell_id`,
`equivalence_clusters`) are invalidated when taxonomy/domain/cost-model changes.
Raw lineage preserved unconditionally.

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-07
- `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` CL-13
- `docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` OI-04

**Câu hỏi mở**:
- How do `feature_lineage` fields differ from `candidate_genealogy` fields?
- What invalidation triggers apply to each layer independently?
- Relationship to F-14 state pack (enumeration) and F-17 semantic change (invalidation)?

---

## SSE-D-08: Contradiction row schema + retention + reconstruction-risk

- **issue_id**: X38-SSE-08
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, OI-05)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): contradiction registry is descriptor-level, shadow-only (MK-17
ceiling). Cross-campaign memory in v1 limited to shadow storage (SSE-D-08).

Topic 015 owns:
1. Row schema for contradiction entries
2. Retention policy (how long entries persist, what triggers purge)
3. Reconstruction-risk handling for phenotype layer

**Shared with 017B**: Topic 017B owns contradiction consumption semantics (how
surprise queue and proof bundle reference entries — SSE-08-CON). Topic 015 owns storage contract.

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-08
- `docs/search-space-expansion/debate/claude/claude_debate_lan_5.md` CL-14
- `docs/search-space-expansion/debate/codex/codex_debate_lan_5.md` OI-05

**Câu hỏi mở**:
- What fields constitute a contradiction entry (candidate_id, descriptor, evidence_hash, ...)?
- Time-based retention or evidence-based (purge when superseded by new data)?
- How does reconstruction-risk gate interact with F-17 classification?

---

## SSE-D-04/7: Invalidation cascade details

- **issue_id**: X38-SSE-04-INV
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (deferred from Topic 018, SSE-D-04 field 7)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): taxonomy/domain/cost-model change invalidates `coverage_map`,
`cell_id`, `equivalence_clusters`, `contradiction_registry`. Raw lineage preserved.

Topic 015 owns: exact invalidation targets, cascade ordering, and relationship
to F-17 semantic change classification.

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md` SSE-D-04 field 7
- `docs/search-space-expansion/debate/claude/claude_debate_lan_6.md` CL-19 field 7

**Câu hỏi mở**:
- Does invalidation cascade in order or is it parallel (all at once)?
- Which F-17 semantic change categories trigger which specific invalidations?
