# Topic 000 — Framework Architecture (Index)

**Topic ID**: X38-T-00
**Opened**: 2026-03-18
**Status**: SPLIT (2026-03-22) — findings distributed to sub-topics
**Original scope**: Cross-cutting framework architecture decisions

## Lịch sử

Topic 000 ban đầu chứa **29 findings** (F-01→F-29) + **12 convergence notes**
(C-01→C-12) về toàn bộ framework architecture. Ngày 2026-03-22, topic được
chia nhỏ thành 11 sub-topics. Sau đó gap analysis thêm 013 + 014 (4 findings
mới F-30→F-33), rebalance tách F-14/F-17 từ 003 sang 015, và Topic 016
(bounded recalibration) added 2026-03-23. Tổng: 15 OPEN sub-topics + 1 CLOSED (004).

## Phân bổ findings

### Cross-cutting → 6 topics mới (007-012)

| Topic | Slug | Findings | Scope |
|-------|------|----------|-------|
| **007** | `philosophy-mission` | F-01, F-20, F-22, F-25 | Triết lý, 3-tier claims, search space policy |
| **008** | `architecture-identity` | F-02, F-09, F-13 | 3 trụ cột, thư mục, identity model |
| **009** | `data-integrity` | F-10, F-11 | Data copies, session immutability |
| **010** | `clean-oos-certification` | F-12, F-21, F-23, F-24 | Clean OOS protocol, power rules |
| **011** | `deployment-boundary` | F-26, F-27, F-28, F-29 | Scope boundary, research contract |
| **012** | `quality-assurance` | F-18, F-19 | Verification gates, online evolution evidence |

### Specialized → 5 topics đã planned (001-003, 005-006)

| Topic | Slug | Findings | Scope |
|-------|------|----------|-------|
| **001** | `campaign-model` | F-03, F-15, F-16 | Campaign→Session, metric scoping, transition |
| **002** | `contamination-firewall` | F-04 | Machine-enforced firewall |
| **003** | `protocol-engine` | F-05 | 8-stage pipeline (F-14/F-17 tách sang 015) |
| **005** | `core-engine` | F-07 | Rebuild vs vendor, engine design |
| **006** | `feature-engine` | F-08 | Registry pattern, threshold modes |

### Gap analysis + rebalance (2026-03-22)

| Topic | Slug | Findings | Scope |
|-------|------|----------|-------|
| **013** | `convergence-analysis` | F-30, F-31 | Convergence metrics, stop conditions |
| **014** | `execution-resilience` | F-32, F-33 | Compute orchestration, checkpointing, CLI |
| **015** | `artifact-versioning` | F-14, F-17 | State pack, semantic change (split từ 003) |

### Already closed

| Topic | Slug | Findings | Status |
|-------|------|----------|--------|
| **004** | `meta-knowledge` | F-06 → MK-01..MK-17 | **CLOSED** (2026-03-21) |

## Tài liệu giữ lại tại 000

- **`findings-under-review.md`**: Chỉ còn convergence notes (C-01→C-12) làm
  shared reference. Findings đã move sang topic tương ứng.
- **Bảng tổng hợp**: trỏ tới topic mới cho mỗi finding.

## Dependency graph

```
Wave 1:    007 (philosophy)              ← CLOSED (2026-03-23)
               ↓
Wave 2:    018 (search-space expansion)  ← REOPENED (ưu tiên sớm, routes to 6 downstream)
           008, 009, 010✅, 011, 012     ← song song sau 007
           001✅, 002✅, 005, 006        ← song song sau 007
           013 (convergence)              ← song song, soft-dep 001✅
           015 (artifact/version)         ← song song, soft-dep 007✅, 008
               ↓
Wave 2.5:  016 (bounded recalibration)   ← chờ 001✅ + 002✅ + 010✅ + 011 + 015
           017 (epistemic search policy) ← chờ 002✅ + 008 + 010✅ + 013
               ↓
Wave 3:    003 (protocol)                ← chờ 001✅ + 002✅ + 004✅ + 015 + 016 + 017
           014 (execution)               ← chờ 003 + 005
```

## Files

| File | Mục đích |
|------|----------|
| `findings-under-review.md` | Convergence notes (C-01→C-12) + finding index |
| `claude_code/` | (empty — debate diễn ra tại topic con) |
| `codex/` | (empty — debate diễn ra tại topic con) |
