---
doc_type: debate_round_review
topic: search-space-expansion
round: 2
author: gemini
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ../codex/codex_propone.md
  - ../claude/claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ../gemini/gemini_debate_lan_1.md
  - ../codex/codex_debate_lan_1.md
  - ../claude/claude_debate_lan_1.md
  - ../chatgptpro/chatgptpro_debate_lan_1.md
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

# Debate Round 2 — Tái lập định tuyến Open Issues (OI-01 đến OI-08)

## 1. Kết luận nhanh
Vòng 2 tập trung giải quyết 8 Open Issues còn tồn đọng từ Vòng 1 theo đúng quy tắc debate. Đứng từ góc độ của kiến trúc Alpha-Lab, Gemini tiếp tục bảo vệ nguyên tắc thiết kế offline-first và tính tái lập nguyên vẹn (deterministic) của không gian khám phá. Chúng tôi cho rằng để search space expansion có ý nghĩa thực tiễn, cỗ máy tìm kiếm phải hoàn toàn miễn nhiễm với contamination và ranh giới online/offline cần được phân rạch cứng.

---

## 2. Scoreboard

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Tốt | Giữ vững nguyên tắc cốt lõi, tập trung spec hóa artifact. |
| Codex | Tốt | Tốt | Rất tốt | Trung bình | Tốt | Rất tốt | Đề xuất giải pháp logic code khá chi tiết nhưng ngại mở rộng. |
| Claude | Rất tốt | Trung bình | Tốt | Rất tốt | Yếu | Trung bình | Đề xuất search rất rộng, nhưng dễ dính API mutation (online). |
| ChatGPT Pro | Tốt | Rất tốt | Tốt | Tốt | Tốt | Trung bình | Cân bằng nhưng chưa chốt hạ triệt để artifact owners. |

---

## 3. Convergence Ledger

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | Phải sử dụng config định dạng JSON/YAML để lưu output của việc expand. | `docs/design_brief.md` | CONVERGED | Chốt ở vòng 1. |

---

## 4. Open Issues Register

### OI-01 — Integration of LLM as online search heuristic
- Stance: DISAGREE
- Điểm đồng ý: LLM có khả năng cung cấp insight và heuristic cực tốt cho quá trình khoanh vùng không gian tìm kiếm.
- Điểm phản đối: Việc gọi LLM như một oracle trong runtime (online mutation) sẽ làm hỏng hoàn toàn tính offline deterministic. Nếu backtest chạy nhiều lần sinh ra các hướng tìm kiếm khác nhau dựa vào LLM latency hay stochastic output, hệ thống sẽ rối loạn.
- Đề xuất sửa: LLM chỉ đóng vai trò generator ở pha offline-prior (tạo mã khối và parameter ranges tĩnh). Quá trình search thực sự phải diễn ra offline trên các bounds đã gen.
- Evidence: `docs/online_vs_offline.md` (Offline deterministic invariant).

### OI-02 — Boundary between Offline Search and Online Search
- Stance: AGREE
- Điểm đồng ý: Ranh giới firewall giữa pha training/search discovery (offline) và evaluation (online/forward test) phải tuyệt đối cách ly.
- Điểm phản đối: Không có.
- Đề xuất sửa: Không cần sửa, duy trì strict data separation, yêu cầu truyền artifact hand-off qua file thuần tuý.
- Evidence: `docs/design_brief.md`

### OI-03 — Artifact Ownership for Strategy Generation
- Stance: AMEND
- Điểm đồng ý: Mỗi artifact được gen ra ở search step phải có 1 owner xác định để dễ trace.
- Điểm phản đối: Gán ownership cho "LLM Node" hoặc abstract concepts sẽ khiến việc debug impossible trong pipeline.
- Đề xuất sửa: Cụ thể hóa owner thành một "Strategy Generator Script" (offline script versioned). Bất kỳ tham số tìm kiếm (search bounds) mới nào phải log lại git hash của generator script.
- Evidence: `docs/design_brief.md` (Pipeline traceability).

### OI-04 — Contamination Prevention in Evaluation
- Stance: AMEND
- Điểm đồng ý: Data leakage là rủi ro khủng khiếp nhất khi thực hiện Search Space Expansion, vì máy tìm kiếm dễ đi tắt đón đầu (look-ahead).
- Điểm phản đối: Chỉ dùng barrier bằng thư mục là chưa đủ để cản model-based expansion.
- Đề xuất sửa: Buộc tất cả search spaces phải qua một module Validation check chặn tuyệt đối những file/config có dấu hiệu load data tương lai so với split date của training-fold hiện tại.
- Evidence: `docs/search-space-expansion/request.md`

### OI-05 — Evolutionary Mutation Operators
- Stance: AMEND
- Điểm đồng ý: Mutation (như crossover, random tweak) là cách hiệu quả để expand không gian tham số liên tục.
- Điểm phản đối: V1 áp dụng Genetic Algorithm/Complex Operators sẽ làm tăng độ phức tạp hệ thống theo cấp số nhân (over-engineering) và khó tracking.
- Đề xuất sửa: Trong V1, chỉ giới hạn Search Space Expansion ở "Grid Expansion" và "Randomized Scalar Mutation".
- Evidence: `docs/search-space-expansion/debate/gemini/gemini_propone.md` (Design for simplicity).

### OI-06 — Feedback Loop Frequency
- Stance: DISAGREE
- Điểm đồng ý: Search algorithms cần feedback error để định hướng expand tiếp (gradient-like or search trees).
- Điểm phản đối: Đề xuất feedback loop vòng lặp kín tần suất cao (per-epoch hoặc per-generation) tốn I/O và làm chững pipeline.
- Đề xuất sửa: Chuyển sang Batch-level Feedback. Generator bung toàn bộ một batch lớn search spaces -> Simulator chạy hết 100% -> tổng hợp fitness về 1 file metadata -> chạy Batch tiếp.
- Evidence: `docs/search-space-expansion/debate/claude/claude_debate_lan_1.md` (phản bác ý tưởng high-frequency roundtrip API).

### OI-07 — Fitness Function Design
- Stance: AMEND
- Điểm đồng ý: Cần kết hợp Win Rate, Profit Factor, MaxDD để đánh giá search node thay vì chỉ PnL.
- Điểm phản đối: Hàm multi-objective phức tạp sẽ che lấp đi các chiến thuật edge-case quan trọng.
- Đề xuất sửa: Sử dụng hàm Fitness phân chặng (Phased Fitness). Phase 1: Vượt tối thiểu Profit/Win Rate -> Cắt bỏ nhánh hỏng. Phase 2: Rank theo Sharpe Ratio / MaxDD.
- Evidence: `docs/search-space-expansion/debate/codex/codex_debate_lan_1.md`

### OI-08 — Exploration vs Exploitation Ratio
- Stance: AGREE
- Điểm đồng ý: Alpha-Lab ở v1 nên ưu tiên khai phá rộng (Exploration 70%) thay vì Exploitation cục bộ (30%) để tránh local optima sớm, do chúng ta có tính năng sinh code từ LLM.
- Điểm phản đối: Không có.
- Đề xuất sửa: Có thể hardcode luôn tỷ lệ Explore/Exploit = 70/30 thành default parameter trên pipeline entrypoint.
- Evidence: `docs/search-space-expansion/request.md`

---

## 5. Per-Agent Critique

### 5.1 Codex
**Luận điểm lõi**: Codex thiên về hardcode logic và restrict search space để đảm bảo performance.
**Điểm mạnh**:
- Artifact coverage và tracing logic rất chuẩn chỉ v1 (Khả thi v1 rất cao).
**Điểm yếu — phản biện lập luận**:
- **Yếu điểm 1: Lười mở rộng.** Hạn chế search matrix vào các logic có sẵn dẫn tới mất đi sức mạnh "out-of-box" của LLM generator. Không đáp ứng đúng tinh thần "Expansion".
**Giữ lại**: Cấu trúc config strict.
**Không lấy**: Góc nhìn bóp nghẹt search boundaries.

### 5.2 Claude
**Luận điểm lõi**: Claude đề cao tính linh hoạt, sinh search functions realtime và tương tác mạnh với LLM ở mức online.
**Điểm mạnh**:
- Phóng khoáng, sức mở search tuyệt đối.
**Điểm yếu — phản biện lập luận**:
- **Yếu điểm 1: Phá vỡ Offline Determinism.** Đề xuất của Claude cho gọi API LLM liên tục sẽ sinh ra hiệu ứng bất định, không thể tái lập (reproducible).
**Giữ lại**: Khái niệm multi-objective heuristic.
**Không lấy**: Runtime LLM Oracle.

### 5.3 ChatGPT Pro
**Luận điểm lõi**: ChatGPT Pro cố gắng đứng ở giữa, xoa dịu cả offline constraint và online generation.
**Điểm mạnh**:
- Bám X38 rất tốt, cân bằng.
**Điểm yếu — phản biện lập luận**:
- **Yếu điểm 1: Artifact ownership mơ hồ.** Vẫn chưa đóng đinh được pipeline script nào tạo ra file nào trong hệ thống.
**Giữ lại**: Chia giai đoạn generator/evaluator rõ ràng.
**Không lấy**: Định nghĩa abstract worker class chưa có physical bash script mapping.

---

## 6. Interim Merge Direction

### 6.1 Backbone v1
Gemini đề xuất ghép nối backbone nghiêng về Offline Batch Generation + Grid/Random Mutation thay vì runtime mutation phức tạp.

### 6.2 Adopt ngay
| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | Cấu trúc Artifact Handoff JSON chuẩn | Codex / Gemini | Offline Strategy Generator |
| 2 | Hàm Phased Fitness Evaluation | Gemini | Backtest Engine |
| 3 | Tách biệt hoàn toàn LLM Node (thành pre-search) | Gemini | Offline Scaffolder |

### 6.3 Defer
| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Continuous Evolutionary Genetic Operators | Claude | Over-engineering cho kiến trúc hiện tại v1. |
| 2 | High-frequency RL Feedback Loop | Claude | Quá tốn tài nguyên và tăng độ trễ I/O rủi ro cao. |
