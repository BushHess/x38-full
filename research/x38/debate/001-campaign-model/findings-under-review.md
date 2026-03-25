# Findings Under Review — Campaign Model

**Topic ID**: X38-T-01
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

3 findings về mô hình Campaign → Session, metric scoping, và transition guardrails.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-04: x38 hiện KHÔNG có bounded recalibration path
- C-06: Transition-law gap thật

---

## F-03: Campaign → Session model

- **issue_id**: X38-D-03
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: **Converged** (R2, 2026-03-23)

**Nội dung**:

Tổ chức nghiên cứu theo mô hình phân cấp:

```
Campaign = {
    dataset cố định (SHA-256 verified),
    protocol cố định (locked before discovery),
    N sessions độc lập trên cùng dataset,
    convergence analysis chéo giữa sessions,
    meta-knowledge output cho campaign tiếp theo
}
```

**Hai giai đoạn tách biệt**:

| Giai đoạn | Mục đích | Data | Kết quả |
|-----------|----------|------|---------|
| Nghiên cứu | Tìm và hội tụ winner | Cùng data file, N campaigns HANDOFF | INTERNAL_ROBUST_CANDIDATE hoặc NO_ROBUST_IMPROVEMENT |
| Clean OOS | Phán quyết winner đã chọn | Data mới (chờ phát sinh) | CLEAN_OOS_CONFIRMED hoặc FAIL |

Clean OOS **không phải** một loại campaign chạy song song. Nó là giai đoạn
**sau** khi nghiên cứu kết thúc và winner được công nhận qua HANDOFF convergence.

**Giai đoạn 1: Nghiên cứu**

```
Campaign C1 → N sessions → convergence → meta-lessons L1
    ↓ HANDOFF
Campaign C2 → inherits L1 → N sessions → ...
    ↓ ... (lặp cho đến khi hội tụ hoặc dừng)
    ↓
Winner chính thức hoặc NO_ROBUST_IMPROVEMENT
```

Tất cả campaigns chạy trên **cùng data file**. OOS chỉ là internal.

**Giai đoạn 2: Clean OOS (chỉ khi đã có winner)**

- Chờ data mới (ít nhất 6 tháng, hoặc khi thị trường thay đổi lớn)
- Replay frozen winner trên data mới — không redesign, không retuning
- Reserve chỉ mở **đúng 1 lần** (RESEARCH_PROMPT_V5.md line 347 [extra-archive])
- Boundary: executable timestamp contract

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V1.md line 36-38 [extra-archive]: discovery + holdout trên file cũ,
  reserve trên data mới.
- CONVERGENCE_STATUS_V3.md [extra-archive]: divergence giữa sessions cần convergence analysis.
- x37_RULES.md §6 [extra-archive]: session lifecycle (PLANNED→ACTIVE→DONE|ABANDONED).

**Câu hỏi mở**:
- Campaign model có over-engineering không? Flat sessions đủ chưa?
- Stop conditions: bao nhiêu NO_ROBUST trước khi dừng giai đoạn nghiên cứu?
- N sessions per campaign: fixed hay flexible?
- Minimum data mới cho Clean OOS: 6 tháng? 1 năm?

---

## F-15: Two cumulative scopes — version-scoped vs candidate-scoped

- **issue_id**: X38-D-15
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, gen4 evidence import)
- **current_status**: **Converged** (R2, 2026-03-23)
- **source**: x37/docs/gen4 — Research Operating Kit v4.0 [extra-archive]

**Nội dung**:

Gen4 phân biệt 2 scope tích lũy cho metrics:

**Scope 1 — Version-scoped** (cho eligibility label):
- Anchor: `freeze_cutoff_utc` (thời điểm freeze version)
- Never reset within version
- Dùng cho: "đã tích lũy đủ 180 ngày + 6 entries chưa?" → `FORWARD_CONFIRMED`

**Scope 2 — Candidate-scoped** (cho ranking/decisions):
- Anchor: `cumulative_anchor_utc`
- **Reset khi promote** (challenger thành champion → metrics reset về zero)
- Dùng cho: keep / promote / kill decisions

**So sánh với x38**: Alpha-Lab là offline discovery (không có forward eval), nhưng
tương tự cần phân biệt:
- **Campaign-scoped metrics**: kết quả tích lũy qua N sessions (cho convergence
  analysis — F-03)
- **Session-scoped metrics**: kết quả trong 1 session cụ thể (cho candidate
  ranking within session)
- **Cross-campaign metrics**: so sánh winners giữa campaigns (cho HANDOFF
  decisions)

Nếu không phân biệt, convergence analysis có thể trộn lẫn metrics ở scope khác
nhau → kết luận sai.

**Evidence**:
- gen4/core/FORWARD_DECISION_POLICY_EN.md §2.1 [extra-archive]: "Two cumulative scopes — reconciliation"
- gen4/core/STATE_PACK_SPEC_v4.0_EN.md [extra-archive]: `cumulative_anchor_utc` field in candidate_registry
- x38 F-03: campaign model chưa define metric scoping

**Câu hỏi mở**:
- Alpha-Lab cần bao nhiêu scope? 2 (session + campaign) hay 3 (+ cross-campaign)?
- Convergence analysis dùng scope nào? Campaign-scoped hay cross-campaign?
- Metric reset rules: khi nào metrics reset trong Alpha-Lab context?

---

## F-16: Campaign transition guardrails

- **issue_id**: X38-D-16
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, gen4 evidence import)
- **current_status**: **Judgment call** (§14, R6, 2026-03-23)
- **source**: x37/docs/gen4 — Research Operating Kit v4.0 [extra-archive]

**Nội dung**:

Gen4 formalize 5 guardrails cho redesign (tương đương: khi nào được mở campaign
mới trong Alpha-Lab):

**1. Allowed triggers** (chỉ 1 trong 4):
- 2 consecutive hard constraint failures
- Emergency breach (data integrity, MDD > hard cap)
- Proven bug affecting trade/PnL
- Structural deficiency (challenger > champion consistently)

**2. Cooldown**: ≥ 180 ngày kể từ lần freeze gần nhất (trừ emergency/bug)

**3. Single hypothesis rule**: Mỗi redesign chỉ thay đổi **đúng 1 thứ chính**

**4. Change budget**:
- Max 1 logic block
- Max 3 tunables
- Max 1 execution semantics change
- Max 20 configs per redesign

**5. Redesign dossier** (gate document bắt buộc):
- Parent version ID, failure claim + evidence, hypothesis, proposed fix
- Do-not-touch list, evidence clock reset justification
- Search accounting (variants tried, rejected, selection basis)
- Complexity impact analysis

**So sánh với x38**: F-03 (Campaign model) nói "N campaigns HANDOFF" nhưng
**không có guardrails cho transition**:
- Khi nào được mở campaign mới? (Trigger chưa định nghĩa)
- Được thay đổi bao nhiêu thứ giữa campaigns? (Change budget chưa có)
- Cần evidence gì trước khi mở? (Threshold chưa có)
- Cooldown giữa campaigns? (Chưa đề cập)

**Mapping gen4 → Alpha-Lab**:

| Gen4 concept | Alpha-Lab tương đương | Cần thiết? |
|---|---|---|
| Cooldown 180d | Không áp dụng (offline, không chờ forward data) | **KHÔNG** — nhưng cần "minimum sessions per campaign" thay thế |
| Single hypothesis | Applicable: mỗi campaign HANDOFF chỉ thay đổi methodology, không đáp án | **CÓ** |
| Change budget | Applicable: giới hạn meta-knowledge changes per HANDOFF | **CÓ** |
| Redesign dossier | Applicable: HANDOFF document phải justify changes | **CÓ** |
| Allowed triggers | Partially: "convergence stall" hoặc "methodology flaw found" | **CẦN ADAPT** |

**Evidence**:
- gen4/core/research_constitution_v4.0.yaml §redesign [extra-archive]: trigger list, cooldown,
  single hypothesis, change budget, dossier gate
- x38 F-03: campaign transitions undefined

**Câu hỏi mở**:
- Guardrails cho Alpha-Lab nên strict như gen4 hay lighter?
- "Single hypothesis" áp dụng cho HANDOFF meta-lessons thế nào?
- HANDOFF dossier: format nào? Ai review?
- Minimum sessions per campaign: 3? 5? Flexible?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 (philosophy) | X38-D-01 | F-01 constrains campaign stop conditions: `NO_ROBUST_IMPROVEMENT` must be valid exit | 007 CLOSED; constraint inherited, 001 owns operationalization |
| 002 (firewall) | X38-D-04 | Firewall determines what can flow at HANDOFF — F-16 guardrails constrain WHEN, firewall constrains WHAT | 002 owns firewall rules; 001 owns HANDOFF trigger/budget |
| 003 (protocol-engine) | F-05 | Protocol content definition determines what "protocol identity" means; routing contract references it | 003 owns protocol content; 001 owns routing contract |
| 008 (architecture-identity) | F-13 | Identity/version schema determines how protocol_identity is tracked | 008 owns identity schema; 001 owns one-way invariant that consumes it |
| 010 (clean-oos) | X38-D-12, X38-D-21 | Clean OOS (Phase 2) depends on campaign model defining Phase 1 exit criteria | 010 owns certification; 001 defines campaign-level verdicts |
| 013 (convergence) | F-15 scoping | Metric scoping determines what convergence analysis measures | 013 owns convergence methodology; 001 provides scope definitions |
| 015 (artifact-versioning) | F-17 | Semantic change classifier determines route classification: which code changes preserve vs alter protocol identity. D-16 route classification explicitly deferred to 015 / F-17 | 015 owns classifier; 001 owns structural HANDOFF law (invariant, package, governance) |
| 016 (bounded-recalibration) | C-04, C-12 | Cross-campaign methodology evolution overlaps with bounded recalibration | 016 owns decision; 001 provides HANDOFF mechanism + third scope definition |

---

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-03 | Campaign → Session model | Judgment call | **Converged** (R2) |
| X38-D-15 | Two cumulative scopes: version vs candidate | Thiếu sót | **Converged** (R2) |
| X38-D-16 | Campaign transition guardrails (từ gen4) | Thiếu sót | **Judgment call** (§14, R6) |
