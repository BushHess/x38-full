# Findings Under Review — Protocol Engine

**Topic ID**: X38-T-03
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

1 finding về protocol engine — 8-stage discovery pipeline.

**Lưu ý**: F-14 (state pack) và F-17 (semantic change classification) đã tách
sang Topic 015 (Artifact & Version Management) vì bản chất "records & versioning"
khác với pipeline logic.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate

---

## F-05: Protocol engine — 8 stages

- **issue_id**: X38-D-05
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

8 stages từ V6, codified:

```
Stage 1: Protocol lock → protocol_freeze.json
Stage 2: Data audit → audit_report.json, audit_tables/
Stage 3: Single-feature scan → stage1_registry.parquet (50K+ rows)
Stage 4: Orthogonal pruning → shortlist.json (keep/drop ledger)
Stage 5: Layered architecture → candidates.json
Stage 6: Parameter refinement → plateau_grids/, search_results.parquet
Stage 7: Freeze → frozen_spec.json (IMMUTABLE after this)
Stage 8: Evaluation → holdout_results.json, internal_reserve_results.json, verdict.json
```

Phase gating: stage N+1 runner checks `required_artifacts[N]` exist.
Freeze checkpoint: sau Stage 7, stages 1-6 dirs trở thành read-only.

**Evidence**:
- RESEARCH_PROMPT_V6.md §Stages 1-8 [extra-archive]: definition.
- x37_RULES.md §7.1-7.4 [extra-archive]: gating rules, minimum evidence, checkpoints.
- research/x37/resource/gen1/v8_sd1trebd/spec/spec_1_research_reproduction_v8.md [extra-archive]:
  866-line research reproduction spec uses explicit
  **Input → Logic → Output → Decision Rule** structure for every step.
- research/x37/docs/gen1/RESEARCH_PROMPT_V8/SPEC_REQUEST_PROMPT.md [extra-archive]:
  263-line meta-prompt — pattern:
  meta-prompt generates spec-writing instructions → AI writes spec → checklist verifies.

**Câu hỏi mở**:
- V6 có 8 stages, x37 có 7 phases. Mapping nào đúng?
- Benchmark embargo: giữ mặc định? Ngoại lệ khi nào?
- **V8 pattern**: Nên alpha-lab adopt Input→Logic→Output→Decision cho mỗi stage?
- **Deliverable template**: SPEC_REQUEST_PROMPT pattern thành built-in component?
- Provenance tracking: automatic hay manual?
- WFO fold structure: cố định semiannual hay configurable per campaign?
- **Deferred from Topic 007 D-25**: Ablation gate thresholds for testing
  regime-aware structures — 007 froze the prohibition (no external classifiers,
  no post-freeze switching) but deferred specific thresholds to 003.
- **Scan-phase multiple testing**: Stage 3 scan 50K+ configs → massive multiple
  comparison problem. Workspace hiện có DSR (`research/lib/dsr.py`) và M_eff
  (`research/lib/effective_dof.py`), nhưng cả hai là **post-selection** tools
  (correct bias cho strategy đã chọn, không control false discovery trong scan).
  Stage 3→4 (scan → prune) cần scan-phase correction: FDR (Benjamini-Hochberg)?
  Step-down (Holm)? Hay cascade design (shortlist → holdout) tự nó đã đủ?
  Evidence: V6-V8 dùng cascade nhưng không nêu formal correction rate.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 015 | F-14 | Artifact enumeration (state pack) split from 003 but stage outputs must conform to artifact spec — protocol stages define WHEN, artifact spec defines WHAT | 015 owns artifact spec; 003 consumes it |
| 016 | F-35 | Bounded recalibration may require protocol stages to support mid-campaign parameter updates — incompatible with current freeze-at-Stage-7 design | 016 must CLOSE before 003 debate; 016 owns decision |
| 002 | F-04 | Firewall enforcement gates protocol transitions — if firewall rejects a lesson mid-pipeline, protocol must handle gracefully | 002 owns firewall rules; 003 adapts |
| 007 | D-25 | F-25 regime-aware policy froze prohibition (no external classifiers, no post-freeze switching). Ablation gate thresholds deferred to 003. | 007 CLOSED; 003 owns thresholds. |
| 017 | ESP-01 | Cell-elite archive replaces Stage 4 global pruning. Descriptor tagging adds Stage 3 output. epistemic_delta.json adds Stage 8 mandatory output. Local probes change Stage 5 search strategy. | 003 owns pipeline structure; 017 defines ESP component contracts. 017 must CLOSE before 003 debate. |
| 018 | SSE-D-04 | Breadth-activation blocker at `protocol_lock` — protocol must declare all 7 fields before activation. Routed from Topic 018 (CLOSED 2026-03-27). Routing confirmed. Stage 3 scan-phase multiple-testing routed via SSE-D-09→013. | 003 owns protocol gate; 018 provides 7-field contract (confirmed). |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-05 | Protocol engine — 8 stages | Judgment call | Open |
| X38-SSE-D-04 | Breadth-activation blocker at protocol_lock (từ Topic 018) | Thiếu sót | Open |

---

## Issue routed from Topic 018 — Search-Space Expansion (2026-03-27)

Architecture-level decision from Topic 018 (**CLOSED** 2026-03-27 —
standard 2-agent debate completed, 10 Converged + 1 Judgment call). This issue
represents a confirmed implementation obligation.
Source: `debate/018-search-space-expansion/final-resolution.md` (authoritative).

---

## SSE-D-04: Breadth-activation blocker at protocol_lock

- **issue_id**: X38-SSE-D-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-27
- **opened_in_round**: 0 (routed from Topic 018, SSE-D-04)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): breadth-activation contract requires protocol
to declare all 7 fields at `protocol_lock` before activation is permitted.

The 7 mandatory fields (from SSE-D-04):
1. `identity_vocabulary` — resolved via Topic 008 Decision 4 (SSE-04-IDV)
2. `generation_mode` — routed to Topic 006 (SSE-D-03)
3. `identity_vocabulary` interface — routed to Topic 008 (SSE-04-IDV)
4. `equivalence_axes` + `anomaly_axes` — routed to Topic 013 (SSE-04-THR)
5. `scan_phase_correction_method` — routed to Topic 013 (SSE-09)
6. `contradiction_storage` — routed to Topic 015 (SSE-08)
7. `invalidation_cascade` — routed to Topic 015 (SSE-04-INV)

Topic 003 owns:
1. Protocol gate that enforces 7-field declaration at `protocol_lock`
2. Stage ordering: breadth-activation check must occur before Stage 3 scan
3. Integration with existing 8-stage pipeline (F-05)

Stage 3 scan-phase multiple-testing correction (SSE-D-09) routed via 013, not directly to 003.

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md:355` [within-x38]: SSE-D-04 routing confirmed.
- `debate/018-search-space-expansion/final-resolution.md:42-49` [within-x38]: Cross-topic impact table.
