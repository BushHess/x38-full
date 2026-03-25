# Findings Under Review — Clean OOS & Certification

**Topic ID**: X38-T-10
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

4 findings về giai đoạn Clean OOS — certification protocol, verdict states,
power rules, và mối quan hệ với pre-existing candidates.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-01: MK-17 ≠ primary evidence chống bounded recalibration
- C-04: x38 hiện KHÔNG có bounded recalibration path
- C-09: x38 đã có PENDING_CLEAN_OOS; thiếu general trigger router

---

## F-12: Clean OOS via future data

- **issue_id**: X38-D-12
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Converged
- **closed_round**: 6
- **closed_date**: 2026-03-25

**Nội dung**:

Clean OOS là giai đoạn **sau** nghiên cứu, không phải loại campaign song song.

**Chu kỳ đầy đủ**:
1. **Nghiên cứu**: N campaigns HANDOFF trên cùng data → winner chính thức
2. **Chờ data mới** (6+ tháng, hoặc khi thị trường thay đổi lớn)
3. **Clean OOS**: replay frozen winner trên data mới
   - CONFIRMED → kết thúc (winner validated)
   - FAIL → winner bị bác bỏ → sang bước 4
4. **Nghiên cứu lại** (chỉ khi FAIL): campaign mới trên toàn bộ data mở rộng
   (cũ + mới). Search space mở hoàn toàn — winner cũ FAIL trở thành
   historical evidence/provenance (KHÔNG nâng thành anti-pattern —
   PROMPT_FOR_V7_HANDOFF.md line 59 [extra-archive] cấm narrowing priors). Lặp lại từ bước 1.

**Ràng buộc** (từ source protocols):

- Discovery + selection holdout đã xong ở giai đoạn 1, trên data cũ
  (PROMPT_FOR_V[n]_CLEAN_OOS_V1.md line 36-38 [extra-archive])
- Reserve = **chỉ** data mới, chưa ai thấy — không redesign, chỉ replay
- Reserve chỉ mở **đúng 1 lần** (RESEARCH_PROMPT_V5.md line 347 [extra-archive])
- Boundary: executable timestamp contract (bar close_time chính xác từ data
  manifest, không phải date string — BTCUSDT_V6_Research_Reproduction_Spec.md
  line 202 [extra-archive]; H4 và D1 có coverage end khác nhau)

```python
@dataclass
class CleanOOSConfig:
    frozen_winner_spec: str          # Path to frozen spec from research phase
    research_data_file: str          # Data file used in research
    new_data_file: str               # Extended data with new bars
    boundary_h4: datetime            # Last H4 bar close_time in research data
    boundary_d1: datetime            # Last D1 bar close_time in research data
    # Reserve = bars with close_time > boundary (per timeframe)
```

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V1.md line 36-38 [extra-archive]: discovery + holdout trên file cũ,
  reserve trên data mới.
- RESEARCH_PROMPT_V5.md line 347 [extra-archive]: true OOS = chưa bị session nào dùng.
- CONVERGENCE_STATUS_V3.md §6 [extra-archive]: "Muốn phân xử winner → cần dữ liệu mới."

**Đã chốt — mechanism (2026-03-19)**: Clean OOS **auto-trigger** — framework tự
động tạo nghĩa vụ `PENDING_CLEAN_OOS` khi (winner chính thức) AND (đủ data mới).
Human được chọn thời điểm chạy, được defer với lý do explicit + ngày review lại,
nhưng KHÔNG được im lặng trì hoãn vô hạn.

**Chưa chốt — minimum duration**: Floor tạm thời ≥ 6 tháng (dùng trong PLAN.md),
nhưng giá trị chính xác còn mở:
- 6 tháng đủ? 1 năm? Phụ thuộc trade frequency?
- Nếu data mới quá ngắn → verdict nên giữ INTERNAL_ROBUST_CANDIDATE?
- Clean OOS nên là module riêng (chạy 1 lần) hay tích hợp vào pipeline?
- Khi FAIL → nghiên cứu lại: winner cũ FAIL nên được ghi nhận như thế nào
  trong meta-knowledge? (anti-pattern? regime-specific caveat?)

**Xem thêm**: F-21 (CLEAN_OOS_INCONCLUSIVE) và F-24 (power rules) bổ sung
chi tiết cho các câu hỏi mở trên.

---

## F-21: CLEAN_OOS_INCONCLUSIVE — first-class verdict state

- **issue_id**: X38-D-21
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from Claude Code ↔ Codex cross-audit)
- **current_status**: Converged
- **closed_round**: 6
- **closed_date**: 2026-03-25

**Nội dung**:

Clean OOS (F-12) hiện chỉ có hai outcomes: `CLEAN_OOS_CONFIRMED` và
`CLEAN_OOS_FAIL`. Cần thêm outcome thứ ba: `CLEAN_OOS_INCONCLUSIVE`.

Trường hợp INCONCLUSIVE xảy ra khi:
- Reserve quá ngắn (< N tháng, chưa chốt giá trị N)
- Quá ít trades trong reserve window (statistical power không đủ)
- Reserve không sample đủ failure modes quan trọng (regime coverage thấp)
- Metrics nằm trong vùng xám (không đủ mạnh để CONFIRMED, không đủ yếu
  để FAIL)

Khi verdict là INCONCLUSIVE:
- Winner giữ nguyên trạng thái `INTERNAL_ROBUST_CANDIDATE`
- Framework chờ thêm data rồi re-run Clean OOS (không quay lại NV1)
- Khác FAIL: FAIL mở lại NV1 từ đầu; INCONCLUSIVE chỉ chờ thêm data

**Tại sao đây không phải edge case**: pre-existing candidate WFO [extra-archive] đã là "underresolved"
(insufficient power) trên chính internal data. Clean OOS trên
appended data rất có khả năng gặp cùng vấn đề power nếu reserve quá ngắn.

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:76-82 [extra-archive]: "if the clean reserve is too
  short, too sparse, or otherwise underpowered, the session must use an honest
  **inconclusive** label rather than overstating certainty"
- F-12 câu hỏi mở: "Nếu data mới quá ngắn → verdict nên
  giữ INTERNAL_ROBUST_CANDIDATE?"
- btc-spot-dev validation pipeline [extra-archive]: WFO underresolved cho pre-existing candidate là
  precedent thực tế

**Câu hỏi mở**:
- Power rules cụ thể → xem F-24
- INCONCLUSIVE có upper bound không? (Sau bao nhiêu lần INCONCLUSIVE liên
  tiếp thì tự chuyển sang FAIL hoặc cần human judgment?)

---

## F-23: Pre-existing candidates vs x38 winners

- **issue_id**: X38-D-23
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from Claude Code ↔ Codex cross-audit)
- **current_status**: Judgment call
- **closed_round**: 6
- **closed_date**: 2026-03-25

**Nội dung**:

Khi x38 chạy trên dataset đã có candidate từ online process, mối quan hệ
giữa pre-existing candidate và x38 winner cần được định nghĩa rõ.

**Scenarios có thể**:

1. **x38 rediscover cùng family** → convergent evidence across methodologies
   (online + offline). Nâng confidence nhưng vẫn cần Clean OOS.
2. **x38 tìm ra family khác** → contradiction. Cần adjudication mechanism
   (head-to-head trên appended data? Parallel Clean OOS?).
3. **x38 output NO_ROBUST_IMPROVEMENT** → pre-existing candidate không bị bác bỏ,
   nhưng cũng không được xác nhận bởi offline.

**Câu hỏi thiết kế**:

- Pre-existing candidate có được treat as shadow-only prior theo MK-17?
  (Consistent với shadow-only rule trên same dataset)
- Nếu x38 Phase 2 chạy Clean OOS, nó validate x38's OWN frozen winner —
  không mặc định validate pre-existing candidate. Nếu muốn validate pre-existing candidate,
  cần mechanism riêng.
- Có nên chạy pre-existing candidate và x38 winner SONG SONG trên appended data?
  Hay chỉ x38 winner? (Resource tradeoff)

**Evidence**:
- PLAN.md:504-519: Phase 2 replay "frozen winner" (x38's own, không nói pre-existing candidate)
- design_brief.md:112-115: Giai đoạn 2 replay frozen winner
- MK-17 (resolved): same-dataset empirical priors = shadow-only
- Claude Code ↔ Codex cross-audit (2026-03-21): flagged as genuine gap

**Câu hỏi mở**:
- Đây là vấn đề thiết kế CHO x38 hay vấn đề vận hành NGOÀI x38?
- Nếu pre-existing candidate thắng head-to-head nhưng không qua x38 pipeline,
  nó có tư cách certification không?

---

## F-24: Clean OOS power rules

- **issue_id**: X38-D-24
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from Claude Code ↔ Codex cross-audit)
- **current_status**: Converged
- **closed_round**: 3 (confirmed rounds 4-6)
- **closed_date**: 2026-03-25

**Nội dung**:

F-12 và F-21 xác nhận Clean OOS cần `INCONCLUSIVE` path khi reserve
underpowered. Nhưng "underpowered" cần tiêu chí cụ thể — không thể là
judgment call mỗi lần chạy.

**Power dimensions đề xuất**:

| Dimension | Tại sao cần | Tiêu chí sơ bộ |
|-----------|-------------|----------------|
| **Trade count** | Quá ít trades → statistical tests vô nghĩa | ≥ N trades (N cần debate, pre-existing candidate ≈ 188 trades [extra-archive]) |
| **Time coverage** | Reserve quá ngắn → chỉ 1 regime | ≥ M tháng (M cần debate, F-12 nói 6 tháng tạm thời) |
| **Regime coverage** | Reserve chỉ chứa 1 regime → không test robustness | ≥ 2 distinct regimes (trend + chop, hoặc bull + bear) |
| **Exposure hours** | Strategy có thể đúng thời điểm nhưng ít exposure | ≥ P% of reserve hours in-position |
| **Effect size** | Metrics nằm trong vùng xám | Pre-registered thresholds cho CONFIRMED/FAIL/INCONCLUSIVE |

**Approach**: Power rules nên là pre-registered (khai báo trước khi mở
reserve), không phải post-hoc. Nếu reserve không đạt power floor → verdict
tự động là INCONCLUSIVE, không cần phân tích metrics.

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:78-82 [extra-archive]: "honest inconclusive label"
- PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md:166-172 [extra-archive]: power considerations
- btc-spot-dev validation WFO [extra-archive]: pre-existing candidate underresolved
  (precedent cho insufficient power)
- F-12 câu hỏi mở: "6 tháng đủ? 1 năm? Phụ thuộc trade frequency?"

**Workspace evidence gap — formal power analysis**:

Bảng "Power dimensions" trên đề xuất thresholds dạng heuristic (≥ N trades,
≥ M tháng). Nhưng thiếu **a priori power analysis**: cho trước effect size target
(ΔSharpe, ΔReturn) và α/β, tính minimum sample size (trades, months, windows)
cần thiết để detect effect đó.

Precedent trong workspace:
- `validation/thresholds.py`: `WFO_SMALL_SAMPLE_CUTOFF = 5` tagged **UNPROVEN**
- Pre-existing candidate WFO: N=8 windows, Wilcoxon p=0.125 → **underresolved**
  (không đủ power để phân biệt signal vs noise ở effect size thực tế)
- Wilcoxon signed-rank ở N=8: cần W+ ≥ 28/36 để reject — tương đương 7/8 wins,
  rất ít room cho variance

Debate nên address: power analysis method nào phù hợp cho Clean OOS?
(Cohen's d + sample size tables? Simulation-based? Pilot study từ internal data?)
Giá trị cụ thể sẽ follow từ method, không nên chọn ngược.

**Câu hỏi mở**:
- Giá trị cụ thể cho mỗi threshold? (Cần simulation hoặc historical
  calibration)
- Power rules nên cố định cho mọi strategy hay configurable per campaign?
- Regime classification dùng tiêu chí nào? (Volatility? Trend/chop? Manual?)
- **Power analysis method**: formal a priori calculation hay heuristic-based?
  (Xem evidence gap ở trên)

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 003 | F-05 | Clean OOS stages must integrate into 8-stage protocol pipeline — but Clean OOS (Phase 2) runs AFTER research pipeline completes, unclear if same stage gating applies | 003 owns pipeline structure; 010 defines Clean OOS protocol within that structure |
| 016 | C-04 | x38 has no bounded recalibration path — if 016 introduces recalibration, Clean OOS verdict logic (CONFIRMED/FAIL/INCONCLUSIVE) may need to account for recalibrated candidates | 016 owns decision |
| 017 | ESP-03 | Power floors for promotion ladder (ESP-03) reuse Clean OOS power methodology (F-24). If 010 defines strict power rules, 017 consumes them for structural prior promotion decisions. | 010 owns power rules; 017 consumes them. |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-12 | Clean OOS via future data | Judgment call | Converged (round 6) |
| X38-D-21 | CLEAN_OOS_INCONCLUSIVE — first-class verdict state | Thiếu sót | Converged (round 6) |
| X38-D-23 | Pre-existing candidates vs x38 winners | Thiếu sót | Judgment call (round 6) |
| X38-D-24 | Clean OOS power rules | Thiếu sót | Converged (round 3) |
