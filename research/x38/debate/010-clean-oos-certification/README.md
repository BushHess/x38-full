# Topic 010 — Clean OOS & Certification

**Topic ID**: X38-T-10
**Opened**: 2026-03-22
**Closed**: 2026-03-25
**Status**: **CLOSED** (6 rounds, 4/4 resolved: 3 Converged + 1 Judgment call)
**Split from**: Topic 000 (cross-cutting)

## Scope

Giai đoạn Clean OOS (giai đoạn 2 — sau nghiên cứu): protocol, verdict states,
power rules, và mối quan hệ với pre-existing candidates từ online process.

**Findings**:
- F-12: Clean OOS via future data — protocol thiết kế
- F-21: CLEAN_OOS_INCONCLUSIVE — first-class verdict state
- F-23: Pre-existing candidates vs x38 winners
- F-24: Clean OOS power rules

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-01: MK-17 ≠ primary evidence chống bounded recalibration
- C-04: x38 hiện KHÔNG có bounded recalibration path
- C-09: x38 đã có PENDING_CLEAN_OOS; thiếu general trigger router

## Dependencies

- **Upstream**: Topic 007 (philosophy — 3-tier claims define certification tầng)
- **Downstream**: Topic 003 (protocol engine cần biết Clean OOS stages)

## Debate plan

- Ước lượng: 1-2 rounds
- Key battles:
  - F-12: Minimum duration cho reserve? 6 tháng? 1 năm?
  - F-21: INCONCLUSIVE upper bound? Bao nhiêu lần trước khi FAIL?
  - F-23: Pre-existing candidates được treat thế nào?
  - F-24: Power rules pre-registered hay per-campaign?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Clean OOS stages must integrate into 8-stage protocol pipeline — but Clean OOS (Phase 2) runs AFTER research pipeline completes, unclear if same stage gating applies | 003 owns pipeline structure; 010 defines Clean OOS protocol within that structure |
| 016 | C-04 | x38 has no bounded recalibration path — if 016 introduces recalibration, Clean OOS verdict logic (CONFIRMED/FAIL/INCONCLUSIVE) may need to account for recalibrated candidates | 016 owns decision |
| 017 | ESP-03 | Power floors for promotion ladder (ESP-03) reuse Clean OOS power methodology (F-24). If 010 defines strict power rules, 017 consumes them for structural prior promotion decisions | 010 owns power rules; 017 consumes them |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 4 findings: F-12, F-21, F-23, F-24 |
| `final-resolution.md` | Closure decisions (2026-03-25) |
| `judgment-call-deliberation.md` | D-23 judgment call (human researcher) |
| `claude_code/` | Phản biện từ Claude Code (6 rounds) |
| `codex/` | Phản biện từ Codex (6 rounds + judgment-call-memo) |
