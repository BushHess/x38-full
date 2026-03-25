# Drafts

Bản nháp đặc tả kiến trúc.

**Lifecycle**: SEEDED → DRAFTING → PUBLISHABLE
- **SEEDED**: Sections được tạo/cập nhật khi bất kỳ dependency liên quan CLOSED.
  Nội dung ở mức skeleton — headings, invariants đã chốt, placeholders cho phần chưa debate.
- **DRAFTING**: Soạn nội dung đầy đủ khi đủ dependencies CLOSED để viết coherent spec section.
- **PUBLISHABLE**: Chuyển sang `published/` chỉ khi TẤT CẢ dependencies đã CLOSED (xem bảng dưới).

| Draft | Phụ thuộc topics | Scope | Status |
|-------|-----------------|-------|--------|
| `meta_spec.md` | 002 + 004 + 007 + 008 | Meta-knowledge governance: 3-tier taxonomy, lesson lifecycle, challenge/expiry, storage format. Firewall: content filtering (what passes, what's blocked). Boundary contract between firewall enforcement (architecture_spec) and content rules (this spec). | NOT STARTED |
| `engine_spec.md` | 005 + 008 | Core backtest engine: types, data, engine, cost, metrics, audit. | NOT STARTED |
| `feature_spec.md` | 006 + 008 | Feature registry, families, threshold calibration, cross-TF alignment, exhaustive scan. | NOT STARTED |
| `architecture_spec.md` | 001 + 002 + 004 + 007 + 008 + 009 + 010 + 011 + **013** + **016** | Campaign model, session lifecycle, directory structure, data management, immutability, Clean OOS flow. Firewall: enforcement mechanism (state machine, typed schema, filesystem). Deployment boundary. **Convergence analysis.** **Bounded recalibration path.** | SEEDED (§1 Campaign Model from Topic 001, 2026-03-23) |
| `protocol_spec.md` | 003 + 012 + **014** + **015** | 8-stage pipeline, phase gating, freeze checkpoint, **artifacts, change classification**, deliverable templates, quality gates. **Execution model, checkpointing.** | NOT STARTED |

Quy tắc:
- SEEDED sections được tạo/cập nhật sau khi bất kỳ dependency liên quan CLOSED
- Draft được phép sửa tự do trong quá trình soạn (SEEDED và DRAFTING)
- Chuyển sang `published/` chỉ khi TẤT CẢ topics phụ thuộc đã CLOSED
- Không viết implementation code — chỉ pseudocode, interface, dataclass skeleton

## ⚠️ Contamination Firewall — split giữa hai specs

Firewall logic chia giữa `architecture_spec.md` (enforcement) và `meta_spec.md`
(content rules). Để tránh mâu thuẫn:

1. **Trước khi viết draft**: topics 002 và 004 phải đồng ý **boundary contract**
   (xem MK-14 trong `debate/004-meta-knowledge/findings-under-review.md`)
2. **Interface**: `architecture_spec` export ContaminationCheck API,
   `meta_spec` export LessonSpec schema. Cả hai phải reference cùng contract.
3. **Khi sửa một spec**: kiểm tra spec kia có bị ảnh hưởng không.
