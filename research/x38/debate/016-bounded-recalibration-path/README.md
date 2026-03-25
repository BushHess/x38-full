# Topic 016 — Bounded Recalibration Path

**Topic ID**: X38-T-16
**Opened**: 2026-03-23
**Status**: OPEN (backlog — activate after Wave 2 prerequisites close)
**Origin**: Orphaned cross-cutting question identified via C-04 + C-12 convergence
notes. No existing topic owns this decision despite touching 5+ topics.

## Architectural decision

x38 có cho phép bounded recalibration path không? Nếu có, exception boundary
và contract với firewall / campaign / Clean OOS / versioning là gì?

## Scope

Quyết định duy nhất: liệu x38 framework có nên cung cấp một đường dẫn cho phép
**recalibrate parameters** (không thay đổi algorithm logic) sau khi monitoring phát
hiện degradation — hay buộc full re-discovery cho MỌI loại degradation.

Nếu cho phép, topic này phải define:
- **Exception boundary**: chính xác loại thay đổi nào được phép (parameter-only?
  threshold-only?) và loại nào KHÔNG bao giờ được phép (logic, filter, entry/exit)
- **Firewall contract**: bounded recalibration tương tác với contamination firewall
  thế nào — exception nào cần, burden of proof thuộc ai
- **Campaign integration**: recalibration là session mới trong campaign hiện tại,
  campaign mới, hay mechanism riêng ngoài campaign model?
- **Clean OOS impact**: recalibrated algorithm cần clean OOS mới hay kế thừa
  certification cũ? Nếu kế thừa, điều kiện gì?
- **Versioning**: recalibration tạo algo_version mới hay deploy_version mới?
  (F-17 / F-29 interaction)

Scope KHÔNG bao gồm:
- Full re-discovery (đã covered bởi Topic 001 campaign model)
- Deployment-layer operational tuning (đã covered bởi Topic 011 F-27)
- Monitoring signal design (đã covered bởi Topic 011 F-26)

## Evidence base

**Convergence notes** (shared reference tại `000-framework-proposal/`):
- **C-04**: x38 hiện KHÔNG có bounded recalibration path. Nếu muốn = design
  change mới.
- **C-12**: Bounded recalibration **prima facie bất tương thích** với current
  firewall. Answer priors (winner, params, family) bị cấm LUÔN; methodology
  priors (Tier 2) = shadow same-data, activate new-data. Muốn giữ → argue
  exception, burden thuộc proposer.
- **C-01**: MK-17 ≠ primary evidence chống bounded recalibration. Trụ chính =
  contamination firewall.
- **C-10**: F-01 cần operationalize qua firewall, không standalone.

**Cross-topic references** (câu hỏi mở đang rải ở các topics khác):
- Topic 011 F-26 (line 73): *"Re-evaluation scope: luôn full re-discovery hay
  triage (parameter-only recalibration nếu degradation nhẹ)?"*
- Topic 001 F-16: Campaign transition guardrails — khi nào mở campaign mới?
  Recalibration có phải trigger hợp lệ?
- Topic 010 F-24: Clean OOS power rules — recalibrated algorithm cần re-certify?
- Topic 015 F-17: Semantic change classification — parameter change = version mới?
- Topic 002 F-04: Firewall typed schema + whitelist — recalibration exception
  cần gì để pass?

**Precedent pattern**: F-17 ↔ F-27 tension → F-28 + F-29 (interface findings).
Topic 016 follows cùng pattern: biến xung đột giữa kỹ thuật thành quyết định
interface rõ ràng, không tranh luận mơ hồ về "compatibility".

**Findings**:
- F-34: Bounded recalibration — exception boundary & firewall contract
- F-35: Recalibration integration — campaign model & Clean OOS interaction

## Dependencies

- **Hard upstream** (phải close trước khi 016 debate):
  - Topic 001 (campaign model) — cần biết campaign structure
  - Topic 002 (contamination firewall) — cần biết firewall rules
  - Topic 010 (Clean OOS) — cần biết certification protocol
  - Topic 011 (deployment boundary) — cần biết scope boundary + F-26 trigger
  - Topic 015 (artifact/versioning) — cần biết semantic change rules + version split
- **Hard downstream** (016 phải close trước):
  - Topic 003 (protocol engine) — pipeline cần biết có recalibration branch không

## Wave assignment

**Wave 2.5**: Chạy sau khi hard upstream (001, 002, 010, 011, 015) close,
trước khi Topic 003 (protocol engine) finalize. Nếu 016 close SAU 003, protocol
có thể phải reopen — tốn thêm rounds không cần thiết.

## Debate plan

- Ước lượng: 2-3 rounds (nhiều tensions cần resolve)
- Key battles:
  - F-34: Có cho phép bounded recalibration hay không? (binary decision trước)
    Nếu có: exception boundary chính xác là gì? Firewall contract ra sao?
  - F-35: Recalibration tạo session/campaign mới hay mechanism riêng? Clean OOS
    re-certification policy?
- Burden of proof: thuộc bên ĐỀ XUẤT recalibration (per C-12: current design
  = no path, proposer must argue exception)

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | Firewall blocks answer priors (winner, params, family) ALWAYS — recalibration = params change = blocked | F-34 must argue exception or accept no-path |
| 001 | F-16 | Campaign transition guardrails may or may not include "mild degradation" as trigger | F-35 defines whether recalibration is campaign or sub-campaign |
| 010 | F-24 | Clean OOS power rules assume frozen algorithm — recalibration breaks "frozen" assumption | F-35 defines re-certification policy |
| 011 | F-26 | Monitoring trigger scope ambiguous — "full re-discovery or triage?" | 016 resolves the "triage" branch |
| 015 | F-17 | Parameter change = semantic change = new version — but recalibration is "same algorithm, different params" | F-34 must reconcile with F-29 algo_version definition |
| 013 | F-31 | Stop conditions: adding session after convergence may violate campaign stop rules | F-35 Phương án A interaction |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings: F-34, F-35 |
| `claude_code/` | Critique from Claude Code |
| `codex/` | Critique from Codex |
