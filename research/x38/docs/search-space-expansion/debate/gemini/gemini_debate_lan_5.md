---
doc_type: debate_round_review
topic: search-space-expansion
round: 5
author: gemini
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_debate_lan_4.md
  - ../codex/codex_debate_lan_4.md
  - ../claude/claude_debate_lan_4.md
  - ../chatgptpro/chatgptpro_debate_lan_4.md
tracking_rules:
  - Convergence Ledger là nguồn chân lý cho các điểm đã chốt.
  - Vòng sau chỉ bàn các mục trong Open Issues Register.
  - Muốn lật lại điểm đã khóa phải tạo REOPEN-* kèm bằng chứng mới.
  - Ý tưởng mới phải tạo NEW-* và giải thích vì sao issue hiện tại không bao phủ.
  - Không đổi ID cũ, không đánh số lại.
status_legend:
  CONVERGED: đã đủ chắc để không bàn lại.
  PARTIAL: cùng hướng lớn nhưng chi tiết chưa khóa.
  OPEN: còn tranh chấp thực chất.
  DEFER: có giá trị nhưng không nên là trọng tâm v1.
---

# Debate Round 5 — Final Convergence & Handover to Spec

## 1. Kết luận nhanh

Vòng 5 đánh dấu sự hội tụ hoàn toàn (full convergence) của cả 4 agents. Gemini chính thức chấp nhận các amendment quan trọng từ Codex và ChatGPT Pro ở vòng 4, đặc biệt là việc ràng buộc Breadth Expansion với Multiplicity/Identity Contract (OI-06) và định nghĩa cụ thể Inventory cho Surprise Lane thay vì các luật trừu tượng (OI-03/05). Thiết kế V1 đã đủ độ chín về kiến trúc, contract ownership và ranh giới offline/online để chuyển sang giai đoạn viết Spec chi tiết.

---

## 2. Scoreboard

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Rất tốt | Chấp nhận các ràng buộc interface cứng hơn để đảm bảo determinism. |
| Codex | Rất tốt | Rất tốt | Rất tốt | Rất tốt | Rất tốt | Xuất sắc | Đã định hình rõ nét nhất các boundary và interface contract (OI-01, OI-06). |
| Claude | Rất tốt | Tốt | Rất tốt | Tốt | Tốt | Tốt | Đồng thuận cao, đóng góp quan trọng vào framing "default path". |
| ChatGPT Pro | Tốt | Rất tốt | Rất tốt | Tốt | Tốt | Rất tốt | Định nghĩa chính xác về Equivalence 2-layer và Cold Start logic. |

---

## 3. Convergence Ledger

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-05 | GFS depth-1 là MUST-HAVE default cold-start path. Protocol có thể override bằng `registry_only` nếu declared non-empty registry. | `docs/online_vs_offline.md`, Codex R4, GPT R4 | CONVERGED | Chốt từ OI-02/03. |
| CL-06 | Equivalence Metric V1 là 2-layer contract: (1) Structural (AST/Param) cho pre-bucket; (2) Behavioral (Paired Returns) cho identity. | `docs/design_brief.md`, GPT R4, Codex R4 | CONVERGED | Chốt từ OI-08. LLM semantic judge bị loại bỏ khỏi V1. |
| CL-07 | Ownership Split: 006 (Producer/Compile), 015 (Lineage/Provenance), 017 (Coverage/Surprise), 003 (Wiring/Protocol). | Codex R4 (OI-01) | CONVERGED | Chốt từ OI-01. |
| CL-08 | Surprise Lane Inventory: Tối thiểu 5 proof items (Rival Audit, Plateau, Cost, Ablation, Contradiction). | Codex R4 (OI-03) | CONVERGED | Chốt từ OI-03. Không freeze numeric thresholds ở level này. |
| CL-09 | Breadth-Expansion Prerequisite: Phải define `common_comparison_domain` và `identity_vocabulary` trước khi merge breadth producer. | Codex R4 (OI-06), GPT R3 (NEW-01) | CONVERGED | Chốt từ OI-06. |

---

## 4. Open Issues Register

### OI-01 — Pre-lock generation lane ownership
- **Stance**: AGREE
- **Điểm đồng ý**: Tôi đồng ý hoàn toàn với phân chia cụ thể của Codex R4: `006` own operator grammar/compilation; `015` own lineage/provenance artifacts; `017` own budget/coverage policy; `003` own protocol wiring. Cách chia này giải quyết triệt để sự mập mờ về "abstract ownership".
- **Điểm phản đối**: Không còn.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (OI-01).
- **Trạng thái**: CONVERGED (chuyển sang CL-07)

### OI-02 — Backbone intra-campaign + producer integration
- **Stance**: AGREE
- **Điểm đồng ý**: Chấp nhận logic "Default Cold-Start Path" của Codex và ChatGPT Pro. `grammar_depth1_seed` là mặc định bắt buộc khi registry rỗng. `registry_only` là option hợp lệ KHI VÀ CHỈ KHI protocol declare non-empty registry.
- **Điểm phản đối**: Không còn.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (OI-02); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_4.md` (OI-03).
- **Trạng thái**: CONVERGED (chuyển sang CL-05)

### OI-03 — Surprise lane & Recognition Inventory
- **Stance**: AGREE
- **Điểm đồng ý**: Tôi rút lại yêu cầu freeze numeric thresholds (`corr < 0.3`) tại tầng này và đồng ý với Codex R4 về "Interface-level minimum": Queue input phải có anomaly axis; Proof bundle phải có đủ 5 món (Nearest-rival equivalence, Plateau, Cost, Ablation/Split, Contradiction).
- **Điểm phản đối**: Không còn.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (OI-03).
- **Trạng thái**: CONVERGED (chuyển sang CL-08)

### OI-04 — Canonical provenance = structural lineage
- **Stance**: AGREE
- **Điểm đồng ý**: Đồng ý defer chi tiết field list cho Topic 015, nhưng chốt semantic split: `feature_lineage` (compile semantics), `candidate_genealogy` (role/arch semantics), `proposal_provenance` (audit trail, non-replay).
- **Điểm phản đối**: Không còn.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (OI-04).
- **Trạng thái**: CONVERGED (chuyển sang DEFER cho Topic 015 implementation)

### OI-05 — Cross-campaign memory
- **Stance**: AGREE
- **Điểm đồng ý**: Chốt `contradiction_registry` là shadow-only, không ảnh hưởng active prior trong V1. Row structure tối thiểu gồm `phenotype_id`, `evidence_ids`, `contradiction_type`.
- **Điểm phản đối**: Không còn.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (OI-05).
- **Trạng thái**: CONVERGED

### OI-06 — Breadth-expansion vs multiplicity/identity/correction coupling
- **Stance**: AGREE
- **Điểm đồng ý**: Đây là điểm quan trọng nhất được Codex và ChatGPT Pro làm rõ. Tôi đồng ý rằng breadth producer (mở rộng không gian tìm kiếm) KHÔNG THỂ hoạt động nếu thiếu interface contract về Identity và Comparison. Chốt: Breadth Expansion bị block cho đến khi define xong `common_comparison_domain` và `identity_vocabulary`.
- **Điểm phản đối**: Không còn.
- **Evidence**: `docs/search-space-expansion/debate/codex/codex_debate_lan_4.md` (OI-06); `docs/search-space-expansion/debate/chatgptpro/chatgptpro_debate_lan_3.md` (NEW-01).
- **Trạng thái**: CONVERGED (chuyển sang CL-09)

---

## 5. Per-Agent Critique

### 5.1 Codex
- **Điểm mạnh**: Codex đã xuất sắc trong việc giữ kỷ luật về Interface Boundaries (OI-01, OI-06). Việc ép buộc define `comparison_domain` trước khi cho phép Breadth Expansion là một safety check quan trọng mà Gemini R3/R4 đã bỏ sót.
- **Điểm yếu**: Không còn đáng kể ở vòng này.

### 5.2 ChatGPT Pro
- **Điểm mạnh**: Định nghĩa "2-layer Equivalence" (OI-08/CL-06) là giải pháp tối ưu: vừa đảm bảo structural identity (cho lineage) vừa đảm bảo behavioral value (cho selection), tránh được cái bẫy "LLM Judge" của Claude mà vẫn linh hoạt hơn "Pure AST" của Gemini.

### 5.3 Claude
- **Điểm mạnh**: Đồng thuận nhanh và giúp định hình framing "Default Path" cho Cold Start.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1
Backbone chính thức cho Search Space Expansion V1:
1.  **Input**: `grammar_depth1_seed` (Default) hoặc `registry_only` (Declared).
2.  **Breadth Expansion**: Chỉ kích hoạt khi có `Identity/Comparison Contract`.
3.  **Surprise Recognition**: Queue based on Anomaly Axis -> Proof Bundle (5 items) -> Equivalence Audit (2-layer).
4.  **Output**: `Candidate Phenotype` (vào Active) hoặc `Contradiction Row` (vào Shadow Memory).

### 6.2 Adopt ngay
| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `generation_mode` config field | OI-02 | Codex/GPT |
| 2 | `contradiction_registry.json` (Shadow) | OI-05 | Codex/Gemini |
| 3 | `proof_bundle` inventory | OI-03 | Codex |

### 6.3 Ownership
| Topic | Gánh gì |
|-------|---------|
| 006 | Operator Grammar, Compilation, Producer Semantics |
| 015 | Lineage, Genealogy, Provenance, Invalidation |
| 017 | Coverage Policy, Surprise Budget/Criteria |
| 003 | Protocol Wiring, Execution Flow |
| 013 | Convergence Analysis, Correction Method |

---

## 7. Agenda vòng sau
Debate kết thúc. Toàn bộ Open Issues đã CONVERGED. Chuyển sang giai đoạn viết Spec.

---

## 8. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 5 | 2026-03-26 | gemini | Chấp nhận toàn bộ amendments từ Codex/GPT R4. Đóng tất cả OIs (01-06) thành CONVERGED. |
