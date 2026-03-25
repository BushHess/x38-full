# Topic 011 — Deployment Boundary & Research Contract

**Topic ID**: X38-T-11
**Opened**: 2026-03-22
**Status**: OPEN
**Split from**: Topic 000 (cross-cutting)

## Scope

Ranh giới giữa x38 (algorithm research) và deployment layer. Bao gồm:
scope boundary, unit-exposure canonicalization, algo/deploy version split,
và monitoring trigger interface.

**Findings**:
- F-26: Monitoring → re-evaluation trigger interface
- F-27: Deployment layer scope boundary
- F-28: Unit-exposure canonicalization — tách sizing khỏi research object
- F-29: Research contract — algo_version / deploy_version split

**Convergence notes liên quan** (shared reference tại `000-framework-proposal/`):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate
- C-06: Transition-law gap thật (liên quan F-16 → Topic 001)
- C-09: x38 đã có PENDING_CLEAN_OOS; thiếu general trigger router

## Dependencies

- **Upstream**: Topic 007 (philosophy — 3-tier claims define x38 scope),
  Topic 010 (Clean OOS — certification output là input cho deployment)
- **Downstream**: Topic 003 (protocol engine cần biết output format)

## Debate plan

- Ước lượng: 1-2 rounds
- Key battles:
  - F-27: x38 frozen spec include operational ranges hay chỉ frozen defaults?
  - F-28: Sizing nội sinh → canonicalize ra unit-exposure có mất tính toàn vẹn?
  - F-29: algo_version components chính xác? cost_envelope_id bao gồm gì?
  - F-26: Signal format (boolean vs structured)? Threshold pre-registered?

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 010 | F-12 | Clean OOS certification output is input for deployment — but F-27 scope boundary says deployment is outside x38, creating ambiguity about who owns the handoff contract | 010 owns certification verdict; 011 owns the boundary definition |
| 015 | F-17 | F-17 classifies position sizing change as semantic change needing new version, but F-27/F-28 push sizing to deployment layer — contradictory if sizing is in algo_version | shared — F-28 (unit-exposure) resolves; 011 owns boundary, 015 owns classification |

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | 4 findings: F-26, F-27, F-28, F-29 |
| `claude_code/` | Phản biện từ Claude Code |
| `codex/` | Phản biện từ Codex |
