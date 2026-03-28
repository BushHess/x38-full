# Topic 013 — Convergence Analysis

**Topic ID**: X38-T-13
**Opened**: 2026-03-22
**Status**: **CLOSED** (2026-03-28)
**Origin**: Gap analysis — convergence algorithm chưa có topic riêng

## Scope

Framework toán học/thống kê để đo convergence giữa N sessions trong một campaign,
xác định stop conditions, và phát hiện diminishing returns.

Topic 001 (Campaign Model) định nghĩa **cấu trúc** Campaign → Session.
Topic 013 định nghĩa **thuật toán** xác định khi nào sessions đã hội tụ
(hoặc nên dừng).

**Findings**:
- F-30: Convergence measurement framework (distance metrics, statistical tests)
- F-31: Stop conditions & diminishing returns detection
- SSE-09: Scan-phase correction law default (từ Topic 018)
- SSE-04-THR: Equivalence + anomaly thresholds (từ Topic 018)

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-04: x38 hiện KHÔNG có bounded recalibration path

## Dependencies

- **Upstream**: Topic 007 (philosophy — framework scope phải settled trước),
  Topic 001 (campaign model — cần biết cấu trúc campaign/session)
- **Downstream**: Topic 003 (protocol engine — convergence analysis là input
  cho pipeline stop logic)

## Debate plan

- Ước lượng: 1-2 rounds
- Key battles:
  - F-30: Distance metric nào? Family-level vs param-level vs Sharpe-distribution?
    Statistical test nào (bootstrap, permutation, voting)?
  - F-31: Bao nhiêu sessions "đủ"? Cách detect diminishing returns mà không
    premature stop?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 017 | ESP-01, ESP-04 | Coverage metrics overlap. Budget governor interacts with stop conditions. | 013 owns convergence/stop; 017 defines coverage obligations. |
| 018 | SSE-09, SSE-04-THR | Scan-phase correction law + equivalence/anomaly thresholds routed from Topic 018 (CLOSED 2026-03-27). Routing confirmed. | 013 owns implementation; 018 provides context (confirmed). |
| 008 | SSE-04-IDV | 013's equivalence thresholds (SSE-04-THR) must be compatible with 008's identity vocabulary (SSE-04-IDV) — both from SSE-D-04 contract. | 008 owns identity interface; 013 owns semantic rules. |

## Closure note

**CLOSED 2026-03-28** (6 rounds canonical + 12 rounds 3-agent JC-debate).
4/4 issues resolved as Judgment call. Human researcher ratified 3-agent consensus.

Key decisions:
- CA-01: Hybrid C convergence framework (Kendall's W, multi-level categories,
  convergence-side prerequisite semantics)
- CA-02: Bootstrap defaults with 5-tier provenance model (ship provisional,
  recalibrate after first offline campaign)
- SSE-09: Holm at alpha_FWER=0.05, BH upgrade path contingent on Topic 017
- SSE-04-THR: Freeze items 1-2 + methodology, defer numerics to 013x017 integration

Unblocks: Topic 017 (epistemic search policy) — hard-dep on 013 NOW SATISFIED.

See `final-resolution.md` for authoritative decisions.

## Files

| File | Mục đích |
|------|----------|
| `final-resolution.md` | Authoritative closure document |
| `judgment-call-decisions.md` | Binding input (ratified JC decisions) |
| `findings-under-review.md` | 4 findings: F-30, F-31 + 2 from Topic 018 (SSE-09, SSE-04-THR) |
| `claude_code/` | Phản biện từ Claude Code (6 rounds) |
| `codex/` | Phản biện từ Codex (6 rounds + judgment-call-memo.md audit) |
