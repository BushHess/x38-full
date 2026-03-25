# Critique: Policy Object Model Proposal

**Author**: claude_code (2026-03-19)
**Target**: `input_solution_proposal.md`
**Verdict**: Hướng đúng, 4 điểm mạnh, 6 vấn đề cần giải quyết trước khi thành spec

---

## Điểm mạnh (không cần debate thêm)

| # | Điểm | Tại sao mạnh |
|---|------|-------------|
| S1 | Ontology/Policy separation | Giải đúng lỗi gốc V4→V8. Rule sửa policy (budget, priority), không sửa ontology (family nào tồn tại). Nguyên tắc: "Tier 2 không ban family, chỉ đẩy xuống probe." |
| S2 | Expiry by in-scope opportunities | Tốt hơn hẳn time-based. Rule không test = không expire. Rule test 6 lần không confirm = archive. |
| S3 | Observation/Hypothesis/Rule separation | Buộc explicit epistemological status. Chỉ Rule compile vào campaign. |
| S4 | Basis field (axiomatic/empirical/operational) | Ngăn operational cap giả dạng chân lý. "Max 3 layers" = operational, không phải proven. |

---

## 6 vấn đề cần debate

### C1. Policy compiler KHÔNG deterministic được ở chỗ quan trọng nhất

**Vấn đề**: Proposal nói compiler chạy "deterministic checks" bao gồm "có suy
ra từ toán/causality không?" — nhưng đây là judgment call, KHÔNG phải
deterministic check. Compiler có thể validate format, scope ≤ provenance, etc.
Nhưng **không thể verify epistemological status bằng code**.

**Hệ quả**: AI viết `basis: "axiomatic"` cho rule thực chất empirical → compiler
accept → rule có hard power sai. Lỗ hổng ở chính nơi quan trọng nhất.

**Đề xuất fix**: Compiler chỉ validate format + enforce constraints. Tier
classification **luôn** cần review (auditor hoặc human). Không claim
deterministic cho judgment task.

**Addresses**: MK-04 (derivation test), MK-08 (ai phân loại?)

---

### C2. Auditor agent: ai audit auditor?

**Vấn đề**: Auditor "chỉ downgrade, không upgrade" — nhưng cũng là AI. Hai
failure modes: quá lenient (không downgrade → rules tích lũy như V8) hoặc quá
strict (downgrade mọi thứ → zero meta-knowledge).

Không có cơ chế calibrate auditor. Auditor's criteria là gì? Nếu dùng
derivation test → quay lại C1 (judgment, không deterministic).

**Đề xuất fix**: Bỏ auditor agent riêng biệt. Thay bằng **adversarial
probing**: khi rule proposed, agent khác viết counter-argument. Counter-argument
ghi vào challenge bundle. Human review chỉ khi counter-argument mạnh (scope
mismatch rõ ràng). Đây là cơ chế MK-09 đã gợi ý nhưng proposal chưa kết nối.

**Addresses**: MK-05 (3-tier taxonomy), MK-08 (ai phân loại?), MK-09 (challenge mechanism)

---

### C3. Budget split 70/20/10 arbitrary — và meta-circular

**Vấn đề**: Tại sao 70/20/10 không phải 60/25/15? Không có principled basis.
Tệ hơn: con số này chính nó là operational rule nhưng proposal treat như
hardcoded constant. Governance system encode assumptions mà chính nó không
govern.

**Đề xuất fix**: Budget split = **configurable per campaign** với default hợp
lý. Mỗi campaign declare budget split + lý do. Adaptive: nếu challenge probes
consistently produce nothing → giảm budget. Nếu probes consistently surprise
→ tăng. Adaptive, không fixed.

**Addresses**: MK-12 (confidence scoring — budget là implicit confidence)

---

### C4. Overlap guard quá mạnh

**Vấn đề**: Rule nói "data overlap với provenance → Tier 2/3 chuyển shadow."
Nhưng **hầu hết campaigns trên cùng asset overlap data** — BTC campaigns luôn
dùng 2017-2026. Kết quả: hầu hết Tier 2 rules ở shadow hầu hết thời gian →
framework gần **zero meta-knowledge** cho same-asset research.

Ví dụ: Rule "vol-clustering features tốt ở bear markets" (provenance = BTC
2020-2024). Campaign mới trên BTC 2020-2026 overlap → rule shadow → framework
quên lesson hữu ích.

**Đề xuất fix**: Overlap guard chỉ áp dụng cho **evaluation data overlap**,
không phải all data. Training/warmup overlap = OK. Thêm: nếu campaign mới có
**genuinely new evaluation period** mà provenance không cover → rule vẫn
active cho non-overlapping portion.

**Addresses**: MK-14 (boundary với contamination firewall)

---

### C5. Active cap selection = pre-campaign bias

**Vấn đề**: max_active_tier2=8, selection criteria bao gồm "novelty distance"
— nhưng novelty distance yêu cầu biết campaign hiện tại novel ở đâu, điều mà
chưa bắt đầu thì chưa biết. Selection vào active set trở thành **pre-campaign
bias**.

**Đề xuất fix**: Selection dựa trên **scope match** (automatic, deterministic)
+ **evidence weight** (measurable). Bỏ "novelty distance" (circular). >8 rules
match scope → lấy 8 evidence weight cao nhất. Đơn giản, transparent.

**Addresses**: MK-11 (conflict resolution — active set = implicit conflict
resolution)

---

### C6. Complexity tổng thể quá nhiều cho v1

**Vấn đề**: 3 tiers × 3 bases × 3 search statuses × scope dimensions × expiry
× challenge bundles × authority levels × overlap guards × active caps × budget
× migration × SQLite + JSON + JSONL + Markdown. Alpha-Lab v1 chạy 1 asset
(BTC), 1 dataset. Phần lớn complexity chưa cần.

Over-engineering → implementation chậm → framework chưa chạy campaign nào →
không validate thiết kế → chicken-and-egg.

**Đề xuất fix**: Implement **layered**:
- **v1 (BTC only)**: 3 tiers + basis + ontology/policy separation + overlap
  guard + challenge probes. Format: JSON files, no database.
- **v2 (multi-asset)**: Thêm scope dimensions, active cap, cross-asset
  challenge triggers.
- **v3 (scaled)**: Thêm SQLite, policy compiler, full budget system.

**Addresses**: MK-13 (storage format — start simple)

---

## Mapping critique → findings

| Critique | Addresses findings | Key question for debate |
|----------|-------------------|----------------------|
| C1 | MK-04, MK-08 | Policy compiler: format validator or epistemological gatekeeper? |
| C2 | MK-05, MK-08, MK-09 | Auditor agent vs adversarial probing? |
| C3 | MK-12 | Fixed budget or adaptive budget? |
| C4 | MK-14 | All-data overlap or evaluation-data-only overlap? |
| C5 | MK-11 | Active set selection: novelty distance or evidence weight only? |
| C6 | MK-13 | All-at-once or layered v1/v2/v3? |

---

## Overall verdict

Proposal giải đúng 4 câu hỏi lớn nhất (S1-S4). 6 critiques đều sửa được mà
không phá vỡ kiến trúc. Hướng đi đúng — cần refine, không cần redesign.
