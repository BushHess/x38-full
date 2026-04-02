# Findings Index & Shared Convergence Notes — Framework Proposal

**Topic ID**: X38-T-00
**Status**: SPLIT (2026-03-22)
**Author**: claude_code (architect, conversation 2026-03-18)

> **NOTE**: Topic 000 đã được chia thành 11 sub-topics (2026-03-22). File này
> chỉ còn giữ lại: (1) Pre-Debate Convergence Notes làm shared reference cho
> debate, và (2) Finding index trỏ tới topic mới.

---

## Pre-Debate Convergence Notes (2026-03-21)

Chuỗi pre-debate review (claude_code ↔ codex, 7 tệp, 4 vòng) đã hội tụ 12 điểm
dưới đây. **Đây KHÔNG phải archive closure** — tất cả findings vẫn Open cho debate
chính thức. Đây là baseline để debate không lặp lại câu hỏi đã settle giữa hai bên.

Chi tiết hội tụ: bảng C-01→C-12 bên dưới là **condensed summary** từ 4 vòng
pre-debate review (claude_code ↔ codex). Bảng dưới đây + F-28/F-29 +
O-01→O-05 (debate-index.md) giữ lại toàn bộ substance.

| ID | Convergence point | Findings liên quan | Áp dụng |
|---|---|---|---|
| C-01 | MK-17 ≠ primary evidence chống bounded recalibration. Trụ chính = contamination firewall (design_brief:46-49,84-89; PLAN:362-373) | F-01, F-04, F-12, MK-17 | Khi debate bounded refit, dùng firewall, không dùng MK-17 |
| C-02 | Nguyên lý shadow-only đã được đề cập đúng (PLAN:423-431; design_brief:84-89) | MK-17 | Không xem đây là gap |
| C-03 | Evidence ngoài archive x38 phải gắn nhãn `extra-archive` | Tất cả | rules.md §18 (codified) |
| C-04 | x38 hiện KHÔNG có bounded recalibration path | F-03, F-12 | Nếu muốn = design change mới |
| C-05 | Semantic boundary DIAGNOSIS: trail/exec/cost/sizing ≠ deployment-only (resolution chưa hội tụ) | F-17, F-27, **F-28**, **F-29** | Diagnosis hội tụ; exact boundary cần debate |
| C-06 | Transition-law gap thật | F-16 | Cần debate riêng, độc lập bounded refit |
| C-07 | "Full rediscovery automated" = aspiration, chưa fact | — | Không dùng như fact |
| C-08 | 3-tier claim DIAGNOSIS: cần tách Mission/Campaign/Certification (naming chưa hội tụ) | F-20 | Diagnosis hội tụ; naming cần debate |
| C-09 | x38 đã có PENDING_CLEAN_OOS; thiếu general trigger router | F-12, F-26 | Nói "thiếu router", không "zero-trigger" |
| C-10 | F-01 cần operationalize qua firewall, không standalone | F-01, F-04 | Cite chain: F-01 → firewall → incompatibility |
| C-11 | Authority chain: design_brief + PLAN primary, F-04 supporting enforcement | F-04 | Cite-discipline, không đảo x38_RULES.md ladder |
| C-12 | Bounded recalibration **prima facie bất tương thích** với current firewall. Answer priors (winner, params, family) bị cấm LUÔN; methodology priors (Tier 2) = shadow same-data, activate new-data. Framing: không "CẤM" (chưa published law), không "trung lập" (bỏ qua firewall) | F-01, F-04, F-17, MK-17 | Muốn giữ → argue exception, burden thuộc proposer |

**Hai proposals mạnh** (valued by both sides, đã thành findings):
- **P-01 → F-28**: Unit-exposure canonicalization → Topic 011
- **P-02 → F-29**: Algo_version / deploy_version split → Topic 011

---

## Finding Index — Trỏ tới topic mới

| Issue ID | Finding | Topic mới | Phân loại | Status |
|----------|---------|-----------|-----------|--------|
| X38-D-01 | Triết lý: kế thừa methodology, không đáp án | **007** (philosophy-mission) | Judgment call | **CLOSED** |
| X38-D-02 | Ba trụ cột kiến trúc | **008** (architecture-identity) | Judgment call | **CLOSED** |
| X38-D-03 | Campaign → Session model | **001** (campaign-model) | Judgment call | **CLOSED** |
| X38-D-04 | Contamination firewall — machine-enforced | **002** (contamination-firewall) | Thiếu sót | **CLOSED** |
| X38-D-05 | Protocol engine — 8 stages | **003** (protocol-engine) | Judgment call | Open |
| X38-D-06 | Meta-knowledge inheritance | **004** (meta-knowledge) | Thiếu sót | **CLOSED** |
| X38-D-07 | Core engine — rebuild từ đầu | **005** (core-engine) | Judgment call | Open |
| X38-D-08 | Feature engine — registry pattern | **006** (feature-engine) | Thiếu sót | Open |
| X38-D-09 | Cấu trúc thư mục target | **008** (architecture-identity) | Thiếu sót | **CLOSED** |
| X38-D-10 | Data management — data-pipeline output + SHA-256 checksum | **009** (data-integrity) | Judgment call | Open |
| X38-D-11 | Session immutability — filesystem-level | **009** (data-integrity) | Thiếu sót | Open |
| X38-D-12 | Clean OOS via future data | **010** (clean-oos-certification) | Judgment call | **CLOSED** |
| X38-D-13 | Three-identity-axis model (từ gen4) | **008** (architecture-identity) | Thiếu sót | **CLOSED** |
| X38-D-14 | State pack specification (từ gen4) | **015** (artifact-versioning) | Thiếu sót | Open |
| X38-D-15 | Two cumulative scopes (từ gen4) | **001** (campaign-model) | Judgment call | **CLOSED** |
| X38-D-16 | Campaign transition guardrails (từ gen4) | **001** (campaign-model) | Thiếu sót | **CLOSED** |
| X38-D-17 | Semantic change classification (từ gen4) | **015** (artifact-versioning) | Thiếu sót | Open |
| X38-D-18 | Continuous verification — module-level review gates | **012** (quality-assurance) | Thiếu sót | Open |
| X38-D-19 | Online framework evolution — failure modes | **012** (quality-assurance) | Thiếu sót | Open |
| X38-D-20 | 3-tier claim separation: Mission/Campaign/Certification | **007** (philosophy-mission) | Thiếu sót | **CLOSED** |
| X38-D-21 | CLEAN_OOS_INCONCLUSIVE — first-class verdict state | **010** (clean-oos-certification) | Thiếu sót | Open |
| X38-D-22 | Phase 1 value classification on exhausted archives | **007** (philosophy-mission) | Judgment call | **CLOSED** |
| X38-D-23 | Pre-existing candidates vs x38 winners | **010** (clean-oos-certification) | Thiếu sót | Open |
| X38-D-24 | Clean OOS power rules | **010** (clean-oos-certification) | Thiếu sót | Open |
| X38-D-25 | Regime-aware policy structure | **007** (philosophy-mission) | Judgment call | **CLOSED** |
| X38-D-26 | Monitoring → re-evaluation trigger interface | **011** (deployment-boundary) | Thiếu sót | Open |
| X38-D-27 | Deployment layer scope boundary | **011** (deployment-boundary) | Judgment call | Open |
| X38-D-28 | Unit-exposure canonicalization | **011** (deployment-boundary) | Judgment call | Open |
| X38-D-29 | Research contract — algo/deploy version split | **011** (deployment-boundary) | Thiếu sót | Open |
| X38-ESP-01 | Intra-campaign illumination (Stages 3-8) | **017** (epistemic-search-policy) | Thiếu sót | Open |
| X38-ESP-02 | CandidatePhenotype & StructuralPrior contracts | **017** (epistemic-search-policy) | Thiếu sót | Open |
| X38-ESP-03 | Inter-campaign promotion ladder | **017** (epistemic-search-policy) | Judgment call | Open |
| X38-ESP-04 | Budget governor & anti-ratchet | **017** (epistemic-search-policy) | Thiếu sót | Open |
| X38-DFL-01 | AI result analysis & pattern surfacing | **019B** (ai-analysis-reporting) | Thiếu sót | Open |
| X38-DFL-02 | Human-facing report contract | **019B** (ai-analysis-reporting) | Thiếu sót | Open |
| X38-DFL-03 | Human feedback capture & grammar evolution | **019B** (ai-analysis-reporting) | Judgment call | Open |
| X38-DFL-04 | Contamination boundary for the discovery loop | **019A** (discovery-foundations) | Thiếu sót | Open |
| X38-DFL-05 | Deliberation-gated code authoring | **019A** (discovery-foundations) | Judgment call | Open |
| X38-DFL-06 | Systematic raw data exploration (10 analyses) | **019C** (systematic-data-exploration) | Thiếu sót | Open |
| X38-DFL-07 | Raw data analysis methodology (6 categories) | **019C** (systematic-data-exploration) | Thiếu sót | Open |
| X38-DFL-08 | Feature candidate graduation path (5 stages) | **019D1** (pipeline-structure) | Thiếu sót | Open |
| X38-DFL-09 | SSE-D-02 scope clarification for systematic scan | **019A** (discovery-foundations) | Thiếu sót | Open |
| X38-DFL-10 | Pipeline integration: Stage 2.5 data characterization | **019D1** (pipeline-structure) | Thiếu sót | Open |
| X38-DFL-11 | Statistical budget accounting (two-tier screening) | **019D2** (statistical-budget) | Thiếu sót | Open |
| X38-DFL-12 | Grammar depth-2 composition (search space expansion) | **019D3** (grammar-expansion) | Thiếu sót | Open |
| X38-DFL-13 | Data trustworthiness & cross-source validation | **019E** (data-quality-validation) | Thiếu sót | Open |
| X38-DFL-14 | Non-stationarity protocol — DGP change detection | **019F** (regime-dynamics) | Thiếu sót | Open |
| X38-DFL-15 | Resolution gap assessment & data acquisition scope | **019G** (data-scope) | Judgment call | Open |
| X38-DFL-16 | Cross-asset context signals for single-asset strategy | **019G** (data-scope) | Judgment call | Open |
| X38-DFL-17 | Pipeline validation via synthetic known-signal injection | **019E** (data-quality-validation) | Thiếu sót | Open |
| X38-DFL-18 | Systematic feature regime-conditional profiling | **019F** (regime-dynamics) | Thiếu sót | Open |
