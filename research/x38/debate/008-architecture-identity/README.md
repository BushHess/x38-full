# Topic 008 — Architecture Pillars & Identity

**Topic ID**: X38-T-08
**Opened**: 2026-03-22
**Status**: **CLOSED** (2026-03-27)
**Split from**: Topic 000 (cross-cutting)

## Scope

Cấu trúc kiến trúc nền tảng: 3 trụ cột, cấu trúc thư mục vật lý, mô hình
identity/versioning. Quyết định tại đây define "xương sống" vật lý của framework.

**Findings**:
- F-02: Ba trụ cột kiến trúc (Contamination Firewall, Protocol Engine, Meta-Updater)
- F-09: Cấu trúc thư mục target (`/var/www/trading-bots/alpha-lab/`)
- F-13: Three-identity-axis model (protocol versioning từ gen4)
- X38-SSE-04-IDV: Candidate-level identity vocabulary (routed from Topic 018)

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-11: Authority chain: design_brief + PLAN primary, F-04 supporting enforcement

## Dependencies

- **Upstream**: Topic 007 (philosophy — F-01 phải settled trước khi chốt pillars)
- **Downstream**: Topics 001, 002, 005, 006 (cần biết architecture để design chi tiết)

## Debate result

4 rounds (author) / 4 rounds (reviewer). All 4 findings Converged (Round 2).
See `final-resolution.md` for full decisions.

**Key decisions**:
- D-02: 3 pillars sufficient for v1 (ESP folds into Protocol Engine)
- D-09: Directory tree stands; tighten checksum contract in campaign.json
- D-13: Add `protocol_version` to campaign.json; bump taxonomy deferred to 003/015
- SSE-04-IDV: Candidate-level identity contract alongside D-13 (not 4th macro axis)

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 | F-01 | Philosophy (F-01) must settle before pillars (F-02) can be finalized — if 007 redefines framework scope, pillar count or identity may change | 007 owns decision; 008 adapts. **RESOLVED**: 007 CLOSED, F-01 frozen. |
| 010 | D-23 | Pre-existing candidate treatment Scenario 1 deferred to 008 F-13 (identity schema). | 008 owns identity schema; 010 CLOSED, consumes result. |
| 018 | SSE-04-IDV | Candidate-level identity vocabulary routed from 018 (CLOSED 2026-03-27). Routing confirmed. | 008 owns interface; 018 provides substance (confirmed). |

## Files

| File | Mục đích |
|------|----------|
| `final-resolution.md` | Closure record — 4/4 Converged, key design decisions |
| `findings-under-review.md` | 4 findings: F-02, F-09, F-13 + 1 from Topic 018 (SSE-04-IDV) |
| `claude_code/` | Phản biện từ Claude Code (R1-R4) |
| `codex/` | Phản biện từ Codex (R1-R4) |
