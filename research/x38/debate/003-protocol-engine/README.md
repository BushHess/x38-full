# Topic 003 — Protocol Engine

**Topic ID**: X38-T-03
**Opened**: 2026-03-22 (activated from PLANNED)
**Status**: OPEN
**Origin**: F-05 (summary in Topic 000). F-14 + F-17 tách sang Topic 015.

## Scope

Protocol engine: 8-stage discovery pipeline, phase gating, freeze checkpoint,
benchmark embargo, provenance tracking, WFO fold structure, deliverable templates.

**Focused**: Chỉ pipeline logic (F-05). Artifact enumeration (F-14) và change
classification (F-17) đã chuyển sang Topic 015 (Artifact & Version Management).

**Findings**:
- F-05: Protocol engine — 8 stages (từ Topic 000)
- F-36: Multi-asset pipeline adaptation (gap audit 2026-03-31)
- F-37: Offline-first session isolation model (gap audit 2026-03-31)
- SSE-D-04: Breadth-activation blocker at protocol_lock (từ Topic 018)

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate

## Dependencies

- **Upstream**: Topic 001 (campaign model) + Topic 002 (contamination firewall)
  + Topic 004 (CLOSED) + Topic 015 (artifact spec inform stage outputs)
  + Topic 016 (bounded recalibration — phải CLOSED trước 003)
  + Topic 017 (epistemic search policy — cell-elite archive, descriptor tagging,
    epistemic_delta.json ảnh hưởng pipeline stage design; phải CLOSED trước 003)
  + Topic 019 (discovery feedback loop — may add human checkpoints or AI analysis
    hooks to pipeline stages; phải CLOSED trước 003)
- **Downstream**: Topic 014 (execution — cần biết stages trước khi define execution),
  Specs (protocol_spec.md)
- **CRITICAL**: Đây là topic tích hợp — debate SAU CÙNG trong Wave 3

## Debate plan

- Ước lượng: 1-2 rounds (giảm từ 2-3 sau khi tách F-14/F-17)
- Key battles:
  - F-05: 8 vs 7 stages? WFO fold structure? Deliverable template engine?
  - V8 Input→Logic→Output→Decision pattern: adopt cho mỗi stage?
  - Benchmark embargo: giữ mặc định? Ngoại lệ khi nào?
  - Provenance tracking: automatic hay manual?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 015 | F-14 | Artifact enumeration (state pack) split from 003 but stage outputs must conform to artifact spec — protocol stages define WHEN, artifact spec defines WHAT | 015 owns artifact spec; 003 consumes it |
| 016 | F-35 | Bounded recalibration may require protocol stages to support mid-campaign parameter updates — incompatible with current freeze-at-Stage-7 design | 016 must CLOSE before 003 debate; 016 owns decision |
| 002 | F-04 | Firewall enforcement gates protocol transitions — if firewall rejects a lesson mid-pipeline, protocol must handle gracefully | 002 CLOSED; 003 adapts to frozen firewall rules |
| 007 | D-25 | F-25 regime-aware policy: internal conditional logic ALLOWED; external classifiers, post-freeze switching FORBIDDEN. Specific ablation gate thresholds for testing regime-aware structures deferred to 003. | 007 CLOSED; 003 owns ablation gate thresholds |
| 017 | ESP-01 | Cell-elite archive replaces Stage 4 global pruning. Descriptor tagging adds Stage 3 output. epistemic_delta.json adds Stage 8 mandatory output. Local probes change Stage 5 search strategy. | 003 owns pipeline structure; 017 defines ESP component contracts. 017 must CLOSE before 003 debate. |
| 018 | SSE-D-04 | Breadth-activation blocker at `protocol_lock` — protocol must declare all 7 fields before activation. Routed from Topic 018 (CLOSED 2026-03-27). Stage 3 scan-phase multiple-testing routed via SSE-D-09→013. | 003 owns protocol gate; 018 provides 7-field contract (confirmed). |
| 019 | DFL-01/03/10 | Discovery loop may add human-feedback checkpoints or AI analysis hooks between/after pipeline stages. **DFL-10 proposes Stage 2.5** (Data Characterization) between Stages 2-3, or expanding Stage 2 scope. Report interface (DFL-02) may produce artifacts alongside pipeline outputs. | 003 owns pipeline structure and stage count. DFL-10 proposes; 003 decides: accept Stage 2.5, fold into Stage 2, or reject. 019 must CLOSE before 003 debate. |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 4 findings: F-05, F-36, F-37 + SSE-D-04 (from Topic 018) |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
