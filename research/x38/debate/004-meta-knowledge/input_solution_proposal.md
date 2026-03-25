# Solution Proposal: Policy Object Model for Meta-Knowledge Governance

**Proposed by**: Human researcher (2026-03-19)
**Addresses**: MK-04 through MK-15 (§1-§3 refine Group B proposals MK-04–MK-07,
§4-§10 answer Group C operational questions MK-08–MK-15)
**Status**: Input for debate — not yet accepted

---

## Mapping to findings

| Proposal section | Addresses findings | Type |
|-----------------|-------------------|------|
| §1 Observation/Hypothesis/Rule | MK-04 (derivation test), MK-05 (3-tier) | Refines Group B |
| §2 Ontology vs Policy | MK-05 (3-tier), MK-06 (leakage types) | Extends Group B |
| §3 Tiers + basis | MK-05, MK-07 (reconciliation with F-06) | Extends Group B |
| §4 Asymmetric authority | **MK-08** (ai phân loại?) | Answers Group C |
| §5 Challenge mechanism | **MK-09** (challenge process) | Answers Group C |
| §6 Expiry | **MK-10** (expiry mechanism) | Answers Group C |
| §7 Firewall boundary | **MK-14** (boundary with firewall) | Answers Group C |
| §8 Active cap | MK-11 (conflict resolution), MK-12 (confidence) | Answers Group C |
| §9 Migration | **MK-15** (bootstrap problem) | Answers Group C |
| §10 Format | **MK-13** (storage format) | Answers Group C |

---

## Root cause diagnosis

Lỗi gốc của V4→V8: "Layering fail trên BTC/OHLCV" là empirical prior, nhưng
nó được cho đi **sai kênh quyền lực** — từ lesson chuyển thành hard rule trong
protocol. Sai không phải vì lesson đó sai; sai vì nó được nâng cấp quá tay.

**Giải pháp cốt lõi**: đừng mang "lesson" sang campaign sau dưới dạng prose
trong protocol. Mang sang dưới dạng **policy object** có kiểu, có scope, có
expiry, có challenge bundle, và có trần quyền lực.

> Thứ được học từ campaign trước chỉ được phép ảnh hưởng tới **search policy**,
> không được phép âm thầm sửa **search ontology**.

---

## 1. Tách ba lớp: Observation / Hypothesis / Rule

Bắt buộc. Nếu không tách, mọi thứ sẽ lại chảy vào prompt-body như trước.

- **Observation**: điều thực sự đã xảy ra. Ví dụ: "Trên BTC spot OHLCV,
  family multi-layer không beat được simpler baseline và trade count co mạnh."
- **Hypothesis**: giải thích có thể đúng hoặc sai. Ví dụ: "Khi feature surface
  chỉ có OHLCV, thêm layer dễ tăng variance nhanh hơn edge."
- **Rule**: chính sách cho campaign sau. Ví dụ: "Trong scope tương tự,
  multi-layer không được vào frontier mặc định; chỉ vào probe và phải qua
  ablation + paired test để được promote."

Chỉ Rule mới được compile vào campaign. Observation và Hypothesis được lưu,
nhưng không được chạy trực tiếp.

---

## 2. Tách hai mặt phẳng: Ontology vs Policy

**Nguyên tắc governance mạnh nhất — nhưng không phải absolute invariant.**

- **Search ontology** = những family nào được coi là tồn tại và admissible.
- **Search policy** = family nào được ưu tiên, bao nhiêu budget, burden of
  proof là gì.

Empirical memory **không được quyền tự động sửa ontology**. Chỉ được sửa policy.

Nghĩa là:
- Campaign trước **có thể** làm bạn đánh multi-layer muộn hơn, ít budget hơn,
  đòi bằng chứng mạnh hơn.
- Campaign trước **không được phép tự động** xóa multi-layer khỏi search space,
  trừ khi bất khả thi do data surface hoặc vi phạm axiom.

> **Tier 2 tự động không được quyền "ban family". Chỉ được đẩy family từ
> frontier xuống probe.**
>
> Ontology/policy separation là **governance preference defeasible by human
> authority** (§4 Tier 3). Human researcher CÓ THỂ cho phép family exclusion
> khi có lý do explicit — đây là thiết kế cố ý, không phải lỗ hổng. Hệ thống
> tự động bị giới hạn; human là final authority bên trên hệ thống.

---

## 3. Ba tiers + trục basis

Mỗi rule phải có **tier** (quyền lực) và **basis** (bản chất) để tránh trộn
lẫn "khoa học", "an toàn", và "giới hạn vận hành".

| Tier | Nội dung | Có được hard-lock? |
|------|---------|-------------------|
| Tier 1 — Axiom | toán, causality, execution semantics, anti-leakage | Có |
| Tier 2 — Structural Prior | empirical, có tính chuyển giao, còn có thể sai | Không; chỉ order/budget/burden |
| Tier 3 — Session-specific | cục bộ, context-specific, mới, ambiguous | Không; shadow hoặc advisory |

Basis:
- **axiomatic**: suy ra từ toán/logic
- **empirical**: rút từ data, có thể sai khi context đổi
- **operational**: giới hạn vận hành (resource, time), không phải chân lý

Ví dụ:
- "No lookahead" = Tier 1 + axiomatic
- "Layering is a hypothesis" = Tier 2 + empirical
- "Max 3 logical layers" = operational cap, **không phải** lesson đã chứng minh

---

## 4. Ai phân loại? Asymmetric authority

AI được phép **đề xuất**, không được **tự cấp lực**.

- **Search AI** sau campaign: chỉ ghi observation + proposed_rule
- **Policy compiler** (deterministic): validate format, enforce scope ≤ provenance,
  mặc định = Tier 2 hoặc Tier 3
- **Auditor agent** (độc lập): chỉ downgrade hoặc narrow, không upgrade
- **Human** chỉ review 3 việc:
  1. Promote lên Tier 1
  2. Mở rộng scope vượt provenance
  3. Cho phép Tier 2 rule loại hẳn một family

Scale: 95% rules không cần human. Conflict of interest bị chặn vì không agent
nào tự nâng rule của mình.

---

## 5. Challenge mechanism: frontier / probe / shadow

Mỗi Tier 2 rule đi kèm **challenge bundle** định sẵn (không challenge tuỳ hứng).

Ba trạng thái cho mỗi family trong campaign:
- **frontier**: search đầy đủ
- **probe**: search đại diện tối thiểu
- **shadow**: không search, nhưng ghi log vì sao

**Tier 2 chỉ được đẩy family xuống probe, không được đẩy xuống forbidden.**

Budget mặc định (**provisional operational defaults**, không phải design
principle — configurable per campaign, subject to empirical tuning):
- 70% prior-guided search (frontier families)
- 20% mandatory challenge probes (suppressed families)
- 10% open novelty scouts

Minimal probe cho complexity prior (ví dụ multi-layer):
1. 1 đại diện 2-layer hợp lý
2. 1 ablation so với best simpler baseline
3. 1 paired test theo metric chuẩn

**Mandatory challenge triggers**:
- Đổi data surface (OHLCV → order flow)
- Đổi market structure (spot → perp/futures)
- Đổi objective/execution (long-only → long-short)
- Rule suppress family plausible trong campaign mới
- Rule stale (lâu không kiểm chứng)

---

## 6. Expiry: by in-scope opportunities, không by time

- **half_life** = 3 in-scope opportunities
- **archive_after** = 6 in-scope opportunities nếu không refresh
- Immediate review nếu challenge thành công
- Automatic narrowing nếu contradicted ngoài scope gốc
- Human review chỉ khi muốn mở scope hoặc cứu rule đã archive

Dùng **weight decay**, không binary sống/chết:
- Rule mới → weight vừa phải
- Mỗi in-scope campaign không refresh → weight giảm
- Weight < threshold → chuyển shadow/archive

> **Tier 2 không bất tử.**

---

## 7. Contamination firewall boundary

**Không bao giờ đi qua pre-freeze:**
- parameter values, thresholds, chosen cells, tuned ladders
- split changes vì đã thấy kết quả cũ
- winner IDs, benchmark-relative claims
- bất kỳ empirical result nào từ overlapping evaluation data

**Được đi qua (bandwidth thấp):**
- axioms (causality, execution, leakage)
- structural priors (generic, scoped, challengeable)
- attention priors ("nhìn vào đâu trước", "đòi bằng chứng mạnh hơn ở đâu")

**Overlap guard**: nếu campaign mới dùng data overlap với provenance của rule,
mọi Tier 2/Tier 3 empirical rule chuyển **shadow mode** — chỉ tồn tại như
note hậu kiểm, không shape discovery pre-freeze.

> Cùng file / cùng evidence base → lesson empirical cũ không được viết vào
> protocol body. Đó là contamination qua kênh governance.

---

## 8. Active cap chống tích luỹ

50 lessons cùng active = chết vì attention leakage.

- **max_active_tier2 = 8** per campaign (**provisional default**, không phải
  design principle — configurable per campaign)
- Phần còn lại ở shadow
- Selection: scope match, evidence weight, suppression risk, novelty distance

Registry lớn, campaign chỉ mang vài prior thật sự liên quan.

---

## 9. Migration V4→V8 → hệ mới

1. **Bóc lesson cũ** thành: observation + hypothesis + proposed_rule
2. **Mặc định bảo thủ**: tất cả vào Tier 3 hoặc Tier 2-narrow. Không giữ
   hard power cho legacy
3. **Gắn provenance + overlap guard**: campaign/dataset/asset/data_surface/
   objective/execution/date_range
4. **Gắn challenge + expiry** ngay lúc migrate. Rule không có governance
   chưa được activate
5. **3 campaign đầu**: challenge budget 25-30% (cao hơn default 20%) để
   audit legacy và dọn registry

---

## 10. Storage format

- **Authoritative store**: SQLite append-only, versioned
- **Campaign input**: `policy_snapshot.json`
- **Human review**: `policy_diff.md`
- **AI proposal**: `rule_proposals.jsonl`
- **Challenge results**: `challenge_outcomes.jsonl`

Search AI chỉ đọc `policy_snapshot.json`. Governance AI viết proposals.
Policy compiler viết registry chính thức sau validation.

Markdown chỉ để người xem diff, không phải source of truth.

Example policy object:

```json
{
  "rule_id": "R_LAYER_001",
  "statement": "Layered architectures often overfit when only OHLCV is available and added layers are not orthogonal.",
  "tier": "structural_prior",
  "basis": "empirical",
  "force": {
    "mode": "budget_and_burden",
    "can_exclude_family": false,
    "budget_multiplier": 0.3
  },
  "scope": {
    "assets": ["BTC"],
    "market": ["spot"],
    "data_surface": ["OHLCV"],
    "objective": ["long_only"],
    "execution": ["signal_close_fill_next_open"]
  },
  "overlap_guard": "inactive_if_eval_data_overlaps_provenance",
  "challenge": {
    "mandatory_if": ["new_data_surface", "new_asset", "suppresses_plausible_family"],
    "minimal_probe": ["one_2layer_rep", "ablation_vs_simple", "paired_test"]
  },
  "expiry": {
    "half_life_opportunities": 3,
    "archive_after_opportunities": 6
  },
  "authority": {
    "max_auto_tier": "structural_prior",
    "human_required_for": ["tier1_promotion", "scope_expansion", "family_exclusion"]
  }
}
```

---

## 11. V4→V8 example reworked

**Thay vì** (hiện tại):
V4 fail → V6 lesson → V8 hard rule → ETH campaign không dám thử multi-layer

**Phải là**:
- **Observation**: "Trong BTC spot OHLCV, layered families không tạo paired
  advantage ổn định; trade count co mạnh."
- **Hypothesis**: "Trong OHLCV-only trend systems, layered complexity thêm
  variance nhanh hơn orthogonal signal."
- **Rule**: Tier 2, scope hẹp (BTC spot OHLCV long-only H4/D1 next-open).
  Force: layered vào probe, không frontier. Challenge: bắt buộc nếu asset
  khác hoặc có order flow. Overlap guard: không influence pre-freeze trên
  same-file reruns.

Kết quả:
- BTC same-file audit: rule không shape discovery
- BTC future appended clean OOS: rule có thể vào với lực thấp
- ETH + order flow: rule bị challenge bắt buộc, không khoá search

---

## 12. Nếu chỉ làm đúng 4 việc

1. **Cấm** nhét empirical lesson vào protocol prose như hard rule
2. **Mặc định** lesson mới không có hard power; AI không tự cấp lực
3. **Tier 2** chỉ sửa budget/order/burden, không xóa family
4. **Same dataset** → Tier 2/3 empirical chạy shadow-only (MK-17 resolved)

> Thứ từ campaign trước được phép mang sang không phải "kết luận",
> mà là "prior có scope và có quyền lực bị chặn".

---

## 13. V1 scope (đã chốt 2026-03-19)

**V1** (BTC-only, single dataset snapshot):
- Tier 1 axioms active
- Empirical lessons (Tier 2/3) stored for audit only — shadow pre-freeze
- Clean OOS lifecycle với auto-trigger `PENDING_CLEAN_OOS`
- Minimal governance format (JSON files, no database)
- 8-stage pipeline = BTC-v1 baseline (not universal ontology)
- Ontology/policy separation = governance default, defeasible by human

**NOT v1** (deferred to v2+):
- Weighted overlap influence / partial-force governance
- Active cap optimization / rich free-text policy objects pre-freeze
- SQLite governance store
- Multi-asset scope / elaborate authority lattice
- Budget split as architecture (70/20/10 = provisional operational defaults)
- Challenge mechanism / ratchet mitigations (not needed when shadow-only)
