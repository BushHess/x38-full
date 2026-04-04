# X38 —   Framework Architecture Design

---

## Sứ mệnh (từ human researcher)

> **Tìm cho bằng được thuật toán trading tốt nhất.**

Alpha-Lab thực hiện **hai nhiệm vụ tuần tự**:

### Nhiệm vụ 1 — Tìm thuật toán tốt nhất (trên dữ liệu hiện có)

Liên tục **làm lại từ gốc trắng** (re-derivation from blank slate) trên cùng
bộ dữ liệu — giống cách V1→V8 đã làm, nhưng framework phải giải quyết được
các bất cập mà quá trình online đã bộc lộ:

- **Kế thừa tri thức**: mang methodology qua campaigns mà không leak data
  conclusions, không khoá search space (§1.4.1)
- **Nhiễm bẩn kết quả**: mỗi vòng touch toàn bộ data → toàn file contaminated
  → clean OOS không còn. Framework cần machine-enforced isolation (§2.1 trụ 1)
- **Thu hẹp search space ngầm**: search space trên danh nghĩa vẫn mở (V8 dòng
  626: "Treat the search space as open"), nhưng structural rules tích lũy qua
  các vòng **implicit disfavor** một số hướng khám phá. Ví dụ: "layering is a
  hypothesis, not a default" không cấm layered strategies — nhưng yêu cầu
  paired ablation evidence, nâng bar để survive. Mỗi rule hợp lý riêng lẻ
  nhưng tổng thể: governance ngày càng chặt → strategies phức tạp khó survive
  hơn → mỗi session tìm ra winner khác nhau mà không hội tụ ở exact level.
  (V4→V8: 5 sessions, 5 exact winners khác family/architecture. V6 winner
  reserve Sharpe -0.04, V8 winner reserve Sharpe 0.87 — không phải "kém đi"
  mà là **không ổn định**.)
  Đây là hệ quả trực tiếp của implicit data leakage qua structural rules
  (§1.4.1, MK-02 harm #3). Framework cần cơ chế để governance không vô tình
  thu hẹp search space.

Mỗi session trong campaign bắt đầu **từ gốc trắng** — chỉ nhận raw data +
methodology rules, không nhận bất kỳ kết quả cụ thể nào từ sessions trước.
Kết quả campaign: `INTERNAL_ROBUST_CANDIDATE` hoặc `NO_ROBUST_IMPROVEMENT`.

**Câu hỏi mở — stop condition cho NV1**: Khi nào "tìm ra được thuật toán tốt
nhất" kết thúc? V4→V8 cho thấy 5 sessions không hội tụ exact. Tiêu chí có thể
là: convergence across N sessions, specific metric threshold, hoặc human
judgment call. CONVERGENCE_STATUS_V3 hiện để human researcher quyết định.
Framework cần formalize tiêu chí này. → Debate tại topic 001 (Campaign model).

**Câu hỏi mở — "tốt nhất" so với gì?** F-01 nói "tốt nhất TRONG search space
đã khai báo." Sứ mệnh nói "tốt nhất" (tuyệt đối). Hai cái này khác nhau:
search space có thể mở rộng liên tục. Framework cần quy định rõ: "tốt nhất"
= tốt nhất trong search space hiện tại, với khả năng mở rộng search space
khi cần. → Debate tại topic 000 (F-01).

### Nhiệm vụ 2 — Xác nhận bằng dữ liệu mới (Clean OOS)

Sau khi Nhiệm vụ 1 tìm ra thuật toán tốt nhất → **đóng băng** → **chờ dữ
liệu mới** phát sinh → replay frozen winner trên dữ liệu mới:

- **Xác nhận thành công** (`CLEAN_OOS_CONFIRMED`): thuật toán validated
- **Chưa đủ bằng chứng** (`CLEAN_OOS_INCONCLUSIVE`): reserve quá ngắn, quá ít
  trades, hoặc không đủ regime coverage để kết luận → giữ nguyên
  `INTERNAL_ROBUST_CANDIDATE`, chờ thêm data (xem F-21, F-24)
- **Không xác nhận được** (`CLEAN_OOS_FAIL`): **quay lại Nhiệm vụ 1 từ đầu**
  trên toàn bộ dữ liệu mở rộng (cũ + mới), search space mở hoàn toàn

Kiến trúc Clean OOS (từ PROMPT_FOR_V[n]_CLEAN_OOS_V2):
- **Historical archive**: toàn bộ data hiện có → dùng cho discovery, holdout,
  internal stress test. KHÔNG eligible cho clean OOS.
- **Fresh appended reserve (clean reserve)**: chỉ data có timestamp **sau**
  archive end → dùng **duy nhất** cho clean OOS evaluation. Thuật ngữ "clean
  reserve" phân biệt với "internal reserve" (Stage 8 trong pipeline nghiên cứu,
  trên cùng data file).
- Không redesign, không retuning, không winner switching sau khi mở reserve.
- FAIL phải báo cáo trung thực — không rescue bằng runner-up.

**Lưu ý thuật ngữ "reserve"**: Trong bộ x38, "reserve" xuất hiện ở hai ngữ
cảnh khác nhau. **Internal reserve** (Stage 8) = phần data giữ lại từ cùng
file để evaluation nội bộ — đã bị contaminate qua các sessions. **Clean
reserve** (Clean OOS) = data mới chưa tồn tại tại thời điểm nghiên cứu — là
OOS thực sự. Hai khái niệm KHÔNG thay thế cho nhau.

Hai nhiệm vụ tạo thành **vòng lặp vô hạn**: Tìm → Xác nhận → (nếu FAIL)
→ Tìm lại → Xác nhận → ... cho đến khi tìm được thuật toán thực sự bền vững.

### Mâu thuẫn cốt lõi

Framework phải giải quyết: kế thừa tri thức từ các vòng nghiên cứu trước
(để không lặp sai lầm) nhưng không khoá chết hướng tìm kiếm mới (để không
chỉ xác nhận kết luận cũ). Đây là vấn đề số 1 — mọi thiết kế khác phục vụ
constraint này. Chi tiết tại §1.4.1.

### Phạm vi

Không chỉ BTC/USDT. Framework phải hoạt động trên bất kỳ asset nào (crypto,
equities, FX) với bất kỳ dataset nào. BTC/USDT là use case đầu tiên, không
phải use case duy nhất.

---

## TL;DR cho agent mới tham gia

X38 thiết kế bản vẽ kiến trúc cho **Alpha-Lab** — một framework **OFFLINE** tự động
tìm thuật toán trading, chạy liên tục qua nhiều campaigns trên nhiều assets.
Framework thay thế quy trình **ONLINE** (AI conversation) hiện tại bằng pipeline
deterministic (cho data processing, feature generation, execution; bootstrap
reproducible khi seed frozen), với machine-enforced contamination isolation.

**⚠️ PHÂN BIỆT QUAN TRỌNG — ĐỌC TRƯỚC KHI DEBATE**:
- **Online** (gen1 V1-V8, gen2, gen3, gen4): AI chat sessions, prompt-based governance,
  non-deterministic. Đây là quy trình HIỆN TẠI đang chạy song song.
- **Offline** (Alpha-Lab, x38 đang thiết kế): Deterministic code pipeline, no AI
  in execution, machine-enforced governance.
- Hai paradigm chia sẻ **cùng vấn đề** nhưng cần **giải pháp khác nhau**.
- Gen1/gen2/gen3/gen4 là evidence về VẤN ĐỀ, KHÔNG phải template cho giải pháp offline.
- **Đọc [`docs/online_vs_offline.md`](docs/online_vs_offline.md) cho bảng đầy đủ.**

**Mục tiêu cuối cùng**: tìm thuật toán tốt nhất — không dừng ở "final audit".
**Vấn đề số 1**: kế thừa tri thức qua campaigns mà không leak data conclusions.
**Sản phẩm của x38**: đặc tả kiến trúc (blueprint), KHÔNG phải code.
**Phương pháp**: tranh luận giữa Claude Code ↔ Codex → thống nhất → xuất bản spec.
**Nơi code sẽ sống**: `/var/www/trading-bots/alpha-lab/` (project riêng, bên ngoài
btc-spot-dev).

---

## Phần 1 — Vì sao x38 tồn tại

### 1.1 Bối cảnh: Quy trình nghiên cứu hiện tại

Project btc-spot-dev đã trải qua nhiều vòng nghiên cứu thuật toán BTC/USDT
spot long-only. Quy trình hiện tại hoạt động **online** — mỗi vòng là một cuộc
hội thoại với AI. Gen1 gồm 8 sessions (V1→V8), trong đó V4→V8 có đầy đủ
convergence tracking:

```
V1–V3 (conversation) → frozen winners (early-stage, không có convergence tracking đầy đủ)
V4 (conversation, 5 rounds) → frozen winner: layered D1+H4 systems (mỗi round khác nhau)
V5 (conversation) → frozen winner: SF_EFF40_Q70_STATIC (D1 efficiency)
V6 (conversation) → frozen winner: S3_H4_RET168_Z0 (H4 momentum)
V7 (conversation) → frozen winner: S_D1_VOLCL5_20_LOW_F1 (D1 volatility clustering)
V8 (conversation) → frozen winner: S_D1_TREND (D1 momentum n=40)  ← simplest possible
```

**V4→V8: 5 sessions, 5 winners khác nhau** — không chỉ khác tham số mà khác
**family/architecture**. V8 governance là tốt nhất (643 dòng protocol),
nhưng winner vẫn khác V7. Exact winner instability là constraint cơ bản
của same-file research, không phải governance failure.

Mỗi vòng tuân theo một **research prompt** (V4→V8) ngày càng tinh vi hơn,
mô tả quy trình khám phá thuật toán từ đầu: đo lường data → đặt giả thuyết →
thiết kế hệ thống → tối ưu tham số → đóng băng → đánh giá holdout/reserve.

Giữa các vòng, có **handoff** (bàn giao): vòng cũ tạo ra prompt mới cho vòng
tiếp theo, chuyển giao **phương pháp** (meta-knowledge) nhưng cấm chuyển giao
**đáp án** (feature names, lookbacks, thresholds).

### 1.2 Vấn đề của quy trình online

5 sessions online (V4, V5, V6, V7, V8 — trong đó V4 có 5 rounds nội bộ;
CONTAMINATION_LOG_V4 ghi nhận 8 rounds qua V4-V7, V8 tự nó là round thứ 9)
đã bộc lộ
các giới hạn cấu trúc:

**A. Không reproducible.**
Cùng prompt, cùng data, nhưng AI khác hoặc ngày khác → kết quả khác. Không có
cách nào replay chính xác quá trình discovery.

**B. Search space bị giới hạn bởi context window.**
V6 scan 2,219 feature configs; V8 scan 1,234 configs — đã là nhiều cho một
conversation, nhưng search space thực tế có thể >50,000 configs. AI phải chọn
lọc bằng trực giác thay vì quét toàn bộ.

**C. Contamination tracking phụ thuộc kỷ luật AI.**
Handoff docs yêu cầu: "không chuyển feature names, thresholds" — nhưng enforcement
là lời hứa, không phải code. CONTAMINATION_LOG_V4.md (8 rounds) cho thấy mỗi
round đều touch toàn bộ data file → không còn clean OOS trong file hiện tại.

**D. Sessions diverge ở level kiến trúc.**
CONVERGENCE_STATUS_V3.md kết luận: 5 sessions hoàn tất (V4 5 rounds, V5, V6, V7,
V8) cho ra winners khác nhau không chỉ ở tham số mà ở **family/architecture**.
Hội tụ ở cấp family (D1 slow), phân kỳ ở cấp exact winner. Clean OOS cần data mới.

**E. Meta-knowledge transfer bị lossy.**
Handoff qua natural language prompt: V5 prompt → V6 prompt → V7 prompt. Mỗi
bước mất thông tin hoặc thêm noise. Không có structured format cho lessons.

**F. Full serialization thiếu.**
V5 resource thiếu full scan universe, phải dùng "minimal sufficient reproduction"
thay vì exact replay
(`x37/resource/gen1/v5_sfq70/spec/research_reproduction_spec_SF_EFF40_Q70_STATIC.md`
line 30). V6 tốt hơn (2,219
rows exported) nhưng vẫn thiếu so với lý tưởng.

### 1.3 Mục tiêu của framework mới

Giải quyết 6 vấn đề trên bằng cách biên dịch quy trình online thành pipeline
offline tự động, đồng thời mở rộng scope:

| Vấn đề online | Giải pháp offline |
|----------------|-------------------|
| Không reproducible | Pipeline deterministic cho data processing, feature generation, execution và non-bootstrap metrics; bootstrap reproducible khi seed + library versions được freeze |
| Search space giới hạn | Exhaustive scan (50K+ configs), parallel compute |
| Contamination by honor | Machine-enforced firewall (typed schema + whitelist categories + state machine; filesystem read-only là guardrail phụ) |
| Divergence trên cùng data | Campaign model: N sessions + convergence analysis |
| Lossy meta-knowledge | Structured lessons (JSON), machine-validated, với governance (classify/challenge/expire) |
| Thiếu serialization | Mọi intermediate result persisted (parquet/JSON) |
| Chỉ BTC/USDT | **Multi-asset design**: framework agnostic về asset, BTC là use case đầu tiên |
| Dừng sau "final audit" | **Infinite research cycles**: không có hard stop mặc định, chạy đến khi tìm được |

### 1.4 Triết lý cốt lõi

> **Kế thừa cách nghiên cứu, không kế thừa đáp án.**

Cụ thể:
- Framework **KHÔNG hứa** "cho ra thuật toán tốt nhất"
- Framework **hứa**: tìm candidate mạnh nhất TRONG search space đã khai báo,
  hoặc trung thực kết luận `NO_ROBUST_IMPROVEMENT` nếu data không đủ
- `NO_ROBUST_IMPROVEMENT` là output hợp lệ — không phải failure
- "Tốt hơn online" = rộng hơn, reproducible hơn, ít contamination hơn,
  audit tốt hơn, sẵn sàng nói "không tìm thấy gì" khi cần

Điều này trực tiếp từ V6 protocol (RESEARCH_PROMPT_V6.md line 7-13):
> "The target is not a claim of global optimum. The target is the best candidate
> found inside a declared search space, with honest evidence labeling."

### 1.4.1 Central design constraint — Meta-knowledge governance

> **Vấn đề số 1 của framework: làm sao kế thừa tri thức tích lũy từ các vòng
> nghiên cứu trước mà không làm rò rỉ kết luận data-specific, không mất cơ chế
> tự sửa sai, và không thu hẹp không gian tìm kiếm một cách vô hình.**

#### Tại sao đây là vấn đề số 1 — không phải một trong nhiều

Contamination firewall chặn **parameter leakage** (feature names, lookbacks,
thresholds) — loại leakage dễ nhận biết. Protocol engine enforce methodology.
Cả hai đều cần thiết nhưng **không đủ**, vì còn một loại leakage mà firewall
KHÔNG chặn được: **structural leakage**.

Chuỗi nhân quả:

```
Lesson rút từ data cụ thể (BTC)
  → trông giống methodology chung ("layering is a hypothesis")
  → pass qua firewall (vì không chứa feature name hay threshold)
  → trở thành binding rule trong protocol
  → AI vòng sau implicit disfavor layered strategies
  → search space thu hẹp mà không ai nhận ra
  → winner mỗi session khác nhau nhưng không hội tụ
  → framework chạy nhiều campaigns nhưng không tiến bộ
```

Đây chính là hiện tượng đã xảy ra với V4→V8: governance tốt nhất (V8 =
643 dòng protocol) nhưng 5 sessions cho 5 winners khác family. Nếu framework
không giải quyết structural leakage, mọi component khác — firewall, protocol,
campaign model — đều **hoạt động đúng nhưng không tạo ra tiến bộ thực sự**:
firewall chặn parameter leakage (✓) nhưng structural leakage vẫn đi qua;
protocol enforce methodology (✓) nhưng methodology encode biases;
campaign model chạy N sessions (✓) nhưng sessions converge đến cùng biases.

Meta-knowledge governance là component quyết định framework có giá trị **lâu
dài** hay chỉ hoạt động tốt cho campaign đầu tiên rồi dần mất khả năng
khám phá.

#### Bằng chứng từ V4→V8

Phân tích V6→V7→V8 cho thấy mô hình "maturity pipeline" hiện tại (lesson →
meta-knowledge section → absorbed into protocol body) có **5 hại**:

1. **Mất provenance** — rule nói "phải làm gì" nhưng không nói "tại sao".
   AI tuân thủ máy móc, không suy luận đúng ở edge cases.
2. **Protocol phình** — 447→586→643 dòng. Governance tốt hơn nhưng compliance
   cost tăng, discovery space bị thu hẹp.
3. **Implicit data leakage** — lessons rút từ BTC data trở thành rules trông
   như methodology chung. Ví dụ: "layering is a hypothesis" đúng cho BTC
   (V4→V8 layered systems đều thua simple) nhưng có thể sai cho assets khác
   (equities với order flow data). Rule này **pass qua firewall** vì không
   chứa feature name — nhưng nó encode kết luận data-specific dưới dạng
   "universal methodology" (dạng "laundering").
4. **Không có unwind** — protocol chỉ thêm rules, không bao giờ bỏ. Nếu
   lesson từ V6 sai (context-specific), nó đã hardcode vào V7 rồi V8.
5. **Diminishing returns** — mỗi constraint mới có marginal value giảm
   nhưng compliance cost tăng tuyến tính.

Evidence cụ thể:

| Version | Protocol lines | Meta-knowledge lessons | Winner | Reserve Sharpe |
|---------|---------------|----------------------|--------|---------------|
| V6 | 447 | 8 (new) | S3_H4_RET168_Z0 (H4 momentum) | -0.04 |
| V7 | 586 | 4 (V6's 8 absorbed) | S_D1_VOLCL5_20_LOW_F1 (D1 vol-cluster) | 0.98 |
| V8 | 643 | 5 (V7's 4 absorbed) | S_D1_TREND (D1 momentum n=40) | 0.87 |

Governance tốt hơn (protocol lines tăng) KHÔNG dẫn đến winner convergence.
Meta-knowledge sections reset mỗi version (chỉ chứa bài mới), bài cũ bị
hấp thụ vào protocol body → protocol phình → structural leakage tích lũy.

#### Fundamental constraint

Đây là **bias-variance tradeoff ở meta-level** — không thể triệt tiêu hoàn
toàn:

- Nhiều meta-knowledge → ít sai lầm lặp lại nhưng search space bị thu hẹp
- Zero meta-knowledge → lặp lại sai lầm cũ
- Maximum meta-knowledge → session mới chỉ xác nhận kết luận cũ

Framework cần tìm **điểm cân bằng tối ưu**, không phải cực đại hay cực tiểu.

#### Hướng giải quyết đã đề xuất

**Derivation Test**: phân loại mỗi rule bằng câu hỏi "có thể suy ra từ
toán/logic thuần túy mà không cần thấy bất kỳ backtest result nào không?"

**3-Tier Rule Taxonomy**:
- **Tier 1 — Axioms**: suy ra từ toán/logic (no lookahead, serialize seeds).
  Không chứa data leakage. Tích lũy vĩnh viễn.
- **Tier 2 — Structural Priors**: empirical, conviction đến từ data nhưng có
  first-principles basis. Bắt buộc: provenance, adversarial challenge, expiry
  condition, leakage grade. **Challengeable** — AI mới được phép question.
- **Tier 3 — Session-specific**: chỉ valid cho session/dataset hiện tại.
  Tự expire khi chuyển context.

Chi tiết tại topic 004 (`debate/004-meta-knowledge/`) — 17 findings, 6 câu
hỏi operational chưa giải quyết.

#### Tiêu chí thành công

Framework được coi là giải quyết tốt constraint này khi:
- Tier 2 rules có provenance, adversarial challenge, và expiry mechanism
- Implicit data leakage được explicit và bounded (không triệt tiêu — impossible)
- Protocol size có steady-state bound (không phình vô hạn qua campaigns)
- Agent mới có permission + context để challenge rules khi evidence nói ngược
- **Search space không thu hẹp** qua campaigns — đo lường bằng: (a) số lượng
  strategy families explored không giảm monotonically qua sessions, VÀ (b)
  effective budget per family không bị bóp ngầm qua thay đổi ladder depth,
  threshold grid, hoặc burden-of-proof. Metric (a) đơn lẻ không đủ — có thể
  giữ family count nhưng thu hẹp search space thực tế bằng cách bóp budget

### 1.5 Vì sao nhánh x38 — không phải viết code luôn

Framework này là kiến trúc phức tạp với nhiều quyết định thiết kế có tradeoffs.
Viết code trước khi thống nhất thiết kế → phải refactor nhiều lần → lãng phí.

X38 dùng **tranh luận có cấu trúc** (Claude Code ↔ Codex) để:
1. Phản biện mỗi quyết định thiết kế từ nhiều góc nhìn
2. Phát hiện lỗ hổng trước khi chúng trở thành code
3. Tạo đặc tả đủ chặt để implementation không cần đoán
4. Ghi lại lý do đằng sau mỗi quyết định (audit trail)

Mô hình debate đã được chứng minh hiệu quả trong x34 (10 issues, 8 converged,
2 judgment calls — xem `research/x34/debate/001-x34-findings/`).

---

## Phần 2 — Framework sẽ hoạt động như thế nào

> **Source of truth**: `docs/design_brief.md` là input chính thức cho debate.
> Phần 2 mở rộng design_brief với evidence, context, và câu hỏi mở.
> Nếu hai file mâu thuẫn, design_brief + debate findings là authoritative.

### 2.1 Ba trụ cột

#### Trụ 1: Contamination Firewall

Tách cứng hai tầng knowledge bằng code, không bằng lời hứa:

| ĐƯỢC kế thừa giữa campaigns | BỊ CẤM kế thừa |
|------------------------------|-----------------|
| Provenance / audit rules | Feature names |
| Serialization requirements | Lookback values |
| Split hygiene heuristics | Threshold values |
| Stop-discipline conditions | Winner identity |
| Anti-patterns (methodology) | Shortlist / family / architecture priors |

**Lưu ý**: mọi lesson làm nghiêng cán cân family/architecture/calibration-mode
đều bị coi là contamination, không phải meta-knowledge. Ví dụ: "scan rộng hơn
phát hiện candidates mới" = methodology (OK); nhưng "single-feature thắng
layered trên reserve" = answer prior (CẤM).

Enforcement: typed schema với whitelist category + state machine ký hash cho
protocol transitions. Filesystem read-only (chmod) là guardrail phụ, không
phải bằng chứng isolation chính. Lưu ý: "machine-enforced" ở đây có nghĩa
**metadata-level enforcement** (validate category, tier, scope, format) — không
phải semantic-level enforcement. Firewall chặn được parameter leakage (feature
names, thresholds) qua typed schema. Structural/semantic leakage (rule trông
giống methodology nhưng encode data conclusions) được **bounded** qua Tier 2
metadata (leakage grade, provenance, challenge), không triệt tiêu. Đây là
residual risk chấp nhận có ý thức (xem MK-03, MK-13 topic 004).

**Evidence**:
- PROMPT_FOR_V7_HANDOFF.md line 48: "V7 must NOT include any specific features,
  lookbacks, thresholds, parameter values [...]"
- PROMPT_FOR_V7_HANDOFF.md line 56: "The new session must not assume any prior
  result is more correct than the others."
Framework codify quy tắc này thành machine-enforced check.

#### Trụ 2: Protocol Engine

V6 protocol (RESEARCH_PROMPT_V6.md) định nghĩa 8 stages. Framework biên dịch
thành executable pipeline với phase gating (stage N+1 bị chặn cho đến khi
stage N artifacts tồn tại).

**Lưu ý**: 8 stages dưới đây là **BTC-v1 protocol baseline** — rút từ lineage
V6/V7/V8 trên BTC/OHLCV. Chúng KHÔNG phải search ontology phổ quát. Trên
assets khác (equities với order flow, FX với tick data), pipeline có thể cần
cấu trúc khác. Topic 003 sẽ debate xem nên giữ nguyên, biến thành configurable
pipeline template, hay thiết kế khác.

```
1. Protocol lock → protocol_freeze.json
2. Data audit → audit_report.json
3. Single-feature scan (exhaustive) → stage1_registry.parquet
4. Orthogonal pruning → shortlist.json
5. Layered architecture search → candidates.json
6. Parameter refinement + plateau → plateau_grids/
7. Freeze comparison set → frozen_spec.json (IMMUTABLE)
8. Holdout + Internal Reserve → verdict.json
```

**Evidence**: x37_RULES.md §7: "Chỉ bắt đầu Phase N+1 khi outputs tối thiểu
của Phase N đã tồn tại."

#### Trụ 3: Meta-Updater

Sau mỗi campaign, chỉ cập nhật 4 loại thông tin:
1. Provenance / audit / serialization rules
2. Split hygiene heuristics
3. Stop-discipline conditions
4. Anti-patterns (methodology-level)

**KHÔNG BAO GIỜ** cập nhật priors về đáp án. Mọi lesson làm nghiêng cán cân
family, architecture, hoặc calibration-mode đều bị coi là contamination.

> **✅ Đã chốt (MK-17, 2026-03-19)**: Trên cùng exact dataset snapshot, mọi
> empirical cross-campaign priors (Tier 2/3) là **shadow-only** trước freeze.
> Tier 1 axioms vẫn active. Empirical lessons được lưu và audit nhưng KHÔNG
> shape discovery pre-freeze trên cùng data. Lý do: governance trên cùng data
> = governance contamination (chính xác failure mode x38 được tạo ra để giải
> quyết). Empirical priors chỉ activate trên genuinely new datasets (v2+).
> Hệ quả: overlap guard trivially resolved (same snapshot = shadow-only),
> challenge/budget/active cap không cần cho v1.

**Evidence**: PROMPT_FOR_V6_HANDOFF.md line 19:
> "Transfer only meta-knowledge (lessons about methodology and structure),
> DO NOT transfer data-derived specifics."

> **Topic 008 CLOSED (2026-03-27)**: Architecture pillars, directory structure,
> identity model, and candidate-level identity vocabulary frozen. 8 rounds, 4/4
> Converged. Key decisions: 3 pillars sufficient for v1 (ESP folds into Protocol
> Engine), directory tree confirmed with tighter checksum contract,
> `protocol_version` added to `campaign.json` (bump taxonomy deferred to
> 003/015), candidate-level identity contract alongside D-13 (008 interface,
> 013 semantics, 017 consumption). See
> `debate/008-architecture-identity/final-resolution.md`. Dependencies:
> 003 (`protocol_version` feeds pipeline), 013 (candidate identity semantics),
> 015 (change-trigger taxonomy), 017 (ESP pillar assignment + consumption).

### 2.2 Campaign → Session Model

```
Campaign = {
    dataset cố định (SHA-256 verified),
    protocol cố định (locked before discovery),
    N sessions độc lập trên cùng dataset,
    convergence analysis chéo giữa sessions,
    meta-knowledge output cho campaign tiếp theo
}
```

**Nghiên cứu là bắt buộc. Clean OOS là bắt buộc về mặt triết lý nhưng
conditional về mặt vận hành** — nó chỉ có thể chạy khi có đủ data mới,
nên framework không chờ nó để sản xuất kết quả nghiên cứu.

| Giai đoạn | Tính chất | Mục đích | Data | Kết quả |
|-----------|-----------|----------|------|---------|
| **Nghiên cứu** | Bắt buộc, chạy ngay | Tìm và hội tụ winner | Cùng data file, N vòng HANDOFF | INTERNAL_ROBUST_CANDIDATE hoặc NO_ROBUST_IMPROVEMENT |
| **Clean OOS** | Bắt buộc, conditional (chờ data mới) | Phán quyết winner đã chọn | Data mới (chờ phát sinh) | CLEAN_OOS_CONFIRMED, INCONCLUSIVE (F-21), hoặc FAIL |

Clean OOS là **Nhiệm vụ 2 trong vòng lặp cốt lõi** (xem §Sứ mệnh) — không
phải "nice-to-have". Framework **tự động tạo nghĩa vụ** `PENDING_CLEAN_OOS`
khi hai điều kiện đủ:
- Winner đã được công nhận chính thức qua HANDOFF convergence
- Có đủ data mới phát sinh (floor tạm thời ≥ 6 tháng — giá trị chính xác
  còn mở, xem F-12 câu hỏi mở)

Khi `PENDING_CLEAN_OOS` được tạo:
- Human researcher được chọn **thời điểm** chạy trong cửa sổ hợp lý
- Human được **defer** nếu có lý do explicit kèm ngày review lại
- Human **KHÔNG được** im lặng trì hoãn vô hạn — defer không có ngày review
  = violation

Trong khi chờ data mới, framework sản xuất verdict cao nhất là
`INTERNAL_ROBUST_CANDIDATE`. Đây là output hợp lệ — nhưng chưa phải
`CLEAN_OOS_CONFIRMED`.

**Giai đoạn 1: Nghiên cứu (campaigns, không cần data mới)**

```
Campaign C1 → N sessions → convergence → meta-lessons L1
    ↓ HANDOFF (kế thừa methodology, không đáp án)
Campaign C2 → inherits L1 (shadow-only on same dataset, xem MK-17) → N sessions → convergence → meta-lessons L2
    ↓ HANDOFF (hoặc STOP — xem hard stop governance)
Campaign C3 (nếu chưa dừng) → ...
    ↓
Winner chính thức hoặc NO_ROBUST_IMPROVEMENT

LƯU Ý same-data campaigns: MK-17 shadow-only nghĩa là trên cùng dataset, C2 ≈
thêm batch sessions cho C1. Đây là by design — same-data campaigns chủ yếu phục
vụ convergence audit hoặc corrective re-run. Meta-learning thực sự phát huy khi
campaigns chạy trên genuinely new data (Giai đoạn 2 → Giai đoạn 3 → Giai đoạn 1).
```

**Hard stop governance cho same-dataset mode**
(PROMPT_FOR_V7_HANDOFF.md line 62: same-file iteration có giới hạn):

- Same-file campaigns có trần mặc định. V4→V8 đã chạy 5 sessions (vượt trần
  4 ban đầu — V8 được approve như final convergence audit).
- Vượt trần phải có **explicit human override** kèm lý do cụ thể (ví dụ:
  "protocol có bug nghiêm trọng cần fix rồi re-run").
- Mỗi campaign đều phải khai báo: đây là convergence audit hay corrective re-run?
- Same-file methodological tightening cải thiện governance, KHÔNG tạo clean
  OOS evidence mới (PROMPT_FOR_V7_HANDOFF.md line 63).

Tất cả campaigns trong giai đoạn này chạy trên **cùng data file**. Mỗi
campaign có thể dùng splits khác nhau nhưng OOS chỉ là internal.
Verdict cao nhất: `INTERNAL_ROBUST_CANDIDATE`.

> **Topic 001 CLOSED (2026-03-23)**: Campaign model, metric scopes, and
> transition guardrails frozen. Transition-routing contract (5-row matrix with
> burden-of-proof default to HANDOFF) in
> `debate/001-campaign-model/final-resolution.md`. Dependencies: 008 (identity
> schema), 003 (protocol content), 013 (numeric thresholds), 015 (evidence
> classes), 016 (recalibration exceptions).

> **Topic 010 CLOSED (2026-03-25)**: Clean OOS protocol, verdict taxonomy,
> power rules, and pre-existing candidate treatment frozen. 6 rounds, 4/4
> resolved (3 Converged + 1 Judgment call). Key decisions: Phase 2 lifecycle,
> stateless PENDING_CLEAN_OOS trigger with Reserve Rollover Invariant,
> 3-verdict taxonomy (CONFIRMED/INCONCLUSIVE/FAIL), method-first power rules,
> Scenario 1 answered by Topic 008 (CLOSED 2026-03-27: `inherits_from` +
> SSE-04-IDV). See `debate/010-clean-oos-certification/final-resolution.md`.
> Dependencies: 008✅ (identity schema), 003 (pipeline integration),
> 016 (recalibration/certification interaction), 017 (power-floor consumption).

**Giai đoạn 2: Clean OOS (chỉ khi đã có winner, chờ data mới)**

```
Winner frozen → chờ 6 tháng (hoặc khi thị trường thay đổi lớn)
    ↓ download data mới
Clean OOS evaluation: replay frozen winner trên data mới
    ↓
    ├── CLEAN_OOS_CONFIRMED → kết thúc (winner validated)
    ├── INCONCLUSIVE → giữ INTERNAL_ROBUST_CANDIDATE, chờ thêm data (F-21)
    └── FAIL → Giai đoạn 3
```

Clean OOS evaluation:
- Discovery + selection holdout: hoàn toàn trên data cũ (đã xong ở giai đoạn 1)
- Clean reserve: **chỉ** data mới, chưa ai thấy (PROMPT_FOR_V[n]_CLEAN_OOS_V1.md line 36-38)
- Không redesign, không retuning — chỉ replay frozen spec
- Reserve chỉ mở **đúng 1 lần** (x37/docs/gen1/RESEARCH_PROMPT_V5/RESEARCH_PROMPT_V5.md line 347)

**Clean OOS boundary**: executable timestamp contract (bar close_time chính xác
trong data manifest), không chỉ date string — vì H4 và D1 có coverage end
khác nhau (x37/resource/gen1/v6_ret168/spec/BTCUSDT_V6_Research_Reproduction_Spec.md line 202).

**Khi nào chạy Clean OOS**:
- Sau khi winner được công nhận chính thức qua HANDOFF convergence
- Khi có đủ data mới (floor tạm thời ≥ 6 tháng — chưa chốt, xem F-12)
- Khi thị trường thay đổi lớn → cần re-validate

**Giai đoạn 3: Nghiên cứu lại (chỉ khi Clean OOS FAIL)**

```
Clean OOS FAIL → winner cũ bị bác bỏ
    ↓
Mở campaign nghiên cứu mới trên toàn bộ data mở rộng (cũ + mới)
    - Search space mở hoàn toàn (không bị khóa vào winner cũ)
    - Winner cũ FAIL lưu ở historical evidence/provenance
      (KHÔNG nâng thành anti-pattern — PROMPT_FOR_V7_HANDOFF.md line 59
      cấm import prior decision outcomes làm narrowing priors)
    - Data mở rộng cho phép discovery mạnh hơn (thêm regimes mới)
    ↓
Lặp lại: Giai đoạn 1 → hội tụ → Giai đoạn 2 → ...
```

FAIL không phải kết thúc — nó là tín hiệu thị trường đã thay đổi và cần
thuật toán mới. Framework phải hỗ trợ chu kỳ đầy đủ:
**nghiên cứu → clean OOS → (nếu FAIL) → nghiên cứu lại → ...**

**Evidence**:
- PROMPT_FOR_V[n]_CLEAN_OOS_V1.md line 36-38: "Discovery + selection holdout: use
  ONLY data from the CURRENT file [...] Reserve window [...] ONLY new data."
- x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md line 234-252: discovery → selection holdout → freeze → reserve.
- x37/docs/gen1/RESEARCH_PROMPT_V5/RESEARCH_PROMPT_V5.md line 347: true OOS = chưa bị session nào dùng.

### 2.3 Cấu trúc thư mục target

```
/var/www/trading-bots/alpha-lab/
├── src/alpha_lab/
│   ├── core/           # Engine: types, data, engine, cost, metrics, audit
│   ├── features/       # Feature engine: registry, families, thresholds
│   ├── discovery/      # 8-stage pipeline
│   ├── validation/     # WFO, bootstrap, plateau, ablation, gates
│   ├── campaign/       # Campaign lifecycle, session, convergence, meta
│   └── cli/            # Command-line interface
├── data/               # Refs to data-pipeline output + SHA-256 manifest
├── campaigns/          # Campaign outputs (grow over time, immutable after close)
├── knowledge/          # Accumulated meta-knowledge (principles only)
└── tests/              # Unit, integration, regression (engine math + artifact conformance)
```

**Nguyên tắc**: Code ≠ Data ≠ Results ≠ Knowledge. Khi project "phình", chỉ
`campaigns/` phình — phần còn lại ổn định.

---

## Phần 3 — Siêu kiến thức từ các vòng nghiên cứu trước

Đây là những bài học **principle-level** (không chứa specifics) rút ra từ 5
sessions online (V4, V5, V6, V7, V8 — trong đó V4 có 5 rounds nội bộ;
CONTAMINATION_LOG_V4 covers 8 rounds V4-V7, V8 là round thứ 9), là input
quan trọng cho thiết kế framework.

### Từ V4 protocol (RESEARCH_PROMPT_V4.md)
- Start from raw data measurement, không pre-filter by mechanism family
- Lock protocol trước discovery, không thay đổi rules sau khi thấy results
- Novelty has no intrinsic value; familiarity has no intrinsic cost

### Từ V5 session (resource/gen1/v5_sfq70)
- **Bài học tiêu cực**: thiếu full serialized scan universe → reproduction
  phải dùng "minimal sufficient" thay vì exact replay
  (`x37/resource/gen1/v5_sfq70/spec/research_reproduction_spec_SF_EFF40_Q70_STATIC.md`
  line 30)
- Full serialization là yêu cầu bắt buộc cho framework mới

### Từ V6 session (resource/gen1/v6_ret168)
- Broader scan phát hiện candidates mà scan hẹp hơn bỏ lỡ
- Reserve/internal evaluation có thể reverse pre-reserve rankings
- Full serialization (registry + comparison specs + test vectors) cho phép
  exact reproduction

### Từ V7 session (resource/gen1/v7_volcl5)
- V7 winner `S_D1_VOLCL5_20_LOW_F1` hội tụ family-level với V6's late-session
  best reserve performer (cùng D1 vol-cluster family)
- Quarterly folds (14 folds) thay cho semiannual (V6) → denser evaluation
- First session to declare "final same-file convergence audit" as framing
- Paired bootstrap on common daily UTC domain — new comparison methodology

### Từ V8 session (resource/gen1/v8_sd1trebd)
- V8 winner `S_D1_TREND` (`D1_MOM_RET(n=40) > 0`) — **đơn giản nhất** trong
  lịch sử: 1 feature, 1 parameter, 0 calibration, sign threshold
- **Khác V7 hoàn toàn** ở family (momentum vs volatility clustering)
- Layered systems definitively eliminated bằng paired bootstrap (P>0.98)
- Introduced **SPEC_REQUEST_PROMPT** — meta-prompt cho spec generation (mới)
- spec_1 dùng **Input→Logic→Output→Decision Rule** cho mỗi step (866 dòng)
- CONTAMINATION_LOG_V4 (1692 dòng, 8 rounds V4-V7): xác nhận KHÔNG còn clean OOS
- Session finality: "stronger claims require appended future data"
- **Governance tốt nhất (643 dòng protocol) nhưng winner vẫn khác V7** → exact
  winner instability là constraint cơ bản, không phải governance failure

### Từ V6→V8 handoffs
- Transfer methodology, NOT answers
- 10-item checklist (PROMPT_FOR_V7_HANDOFF.md line 143-175) để verify không leak specifics
- Divergence giữa sessions là thông tin, không phải lỗi
- Same-data re-derivation có giới hạn → cần new data cho clean OOS
- V8 handoff tightened: no same-file iteration beyond V8

### Từ Convergence Status V3 (CONVERGENCE_STATUS_V3.md)
- 5 sessions hoàn tất (V4 5 rounds, V5, V6, V7, V8) → winners khác nhau ở
  **family/architecture** level
- **Hội tụ ở cấp family**: D1 slow signals consistently strong
- **Phân kỳ ở cấp exact**: mỗi session freeze winner khác nhau
- Thêm sessions trên cùng data "chủ yếu trả lời câu hỏi quy trình nhạy
  tới đâu" hơn là "hệ nào đúng hơn ngoài mẫu"
- Clean OOS proof cần data mới, không phải thêm sessions

### Từ expert feedback (2026-03-18, 2026-03-19)
- 3 thành phần bắt buộc: contamination firewall, protocol engine, meta-updater
- V6 ≈ 80% của framework — gap là biên dịch "document AI must follow" thành
  "code that self-enforces"
- Human researcher intent: "tìm cho bằng được thuật toán tốt nhất" — framework
  KHÔNG dừng ở final audit mà chạy liên tục qua nhiều campaigns, nhiều assets
- Meta-knowledge governance là vấn đề số 1 — mọi thiết kế khác phục vụ nó
- Kế thừa tri thức: phải giải quyết bias-variance tradeoff ở meta-level

---

## Phần 4 — Cách x38 hoạt động

### 4.1 Workflow

```
docs/design_brief.md (thiết kế sơ bộ, input)
         │
         ▼
debate/NNN-slug/ (tranh luận từng quyết định kiến trúc)
  ├── Claude Code: opening critique
  ├── Codex: rebuttal
  ├── Claude Code: author-reply
  └── ... (max 6 rounds per topic)
         │
         ▼  (khi topic hội tụ hoặc judgment call)
drafts/ (soạn spec section tương ứng)
         │
         ▼  (khi TẤT CẢ topics liên quan xong)
published/ (xuất bản đặc tả chính thức)
```

### 4.2 Debate structure

Kế thừa từ x34 (`research/x34/debate/`), điều chỉnh cho context kiến trúc.

**Quy tắc chính** (đầy đủ trong `debate/rules.md`):
- Tìm đáp án đúng nhất, không tìm đồng thuận
- Mọi claim phải có evidence pointer
- Steel-man bắt buộc trước khi đánh dấu hội tụ
- Cấm ngôn ngữ nhượng bộ mềm
- Max 6 rounds per topic
- Issue chưa resolved sau max rounds → Judgment call

**Phân loại issue**:
- `Sai thiết kế`: vi phạm nguyên tắc (contamination leak, lookahead, ...) → phải sửa
- `Thiếu sót`: bỏ qua edge case hoặc yêu cầu → nên bổ sung
- `Judgment call`: cả hai phía có lý → ghi tradeoff, decision owner quyết định

**Participants**:

| Agent | Vai trò |
|-------|---------|
| `claude_code` | Architect (thiết kế sơ bộ) + critic |
| `codex` | Reviewer + adversarial critic |

### 4.3 Topic organization

**Topic 000** = **hub tổng quan + debate arena cho cross-cutting issues**.

Vai trò kép:
1. **Debate arena** cho những quyết định ảnh hưởng toàn framework mà không
   thuộc riêng topic chuyên sâu nào:
   - F-01: Triết lý cốt lõi
   - F-02: Ba trụ cột kiến trúc
   - F-09: Cấu trúc thư mục
   - F-10: Data management
   - F-11: Session immutability
   - F-12: Clean OOS via future data
2. **Summary hub** cho 6 specialized findings (F-03→F-08) — mỗi finding giữ
   bản đầy đủ trong 000 cho đến khi nó **phình** (có sub-findings phức tạp),
   lúc đó mới tách ra topic riêng. Finding đã tách chỉ giữ summary + pointer
   trong 000.

**Topics 001-012** = debate arena cho **specialized issues**:

> **Cập nhật 2026-03-22**: Topic 000 đã SPLIT thành 11 sub-topics. Gap analysis
> thêm 013 + 014. Rebalance tách 003 → 015. Bảng dưới đây đã được đồng bộ với
> `debate/debate-index.md` (authoritative). Xem debate-index.md cho wave order
> và dependency graph đầy đủ.

| # | Topic | Nguồn | Status |
|---|-------|-------|--------|
| 000 | Framework architecture (index) | — | **SPLIT** (2026-03-22) → 11 sub-topics |
| 001 | Campaign model | F-03, F-15, F-16 | **CLOSED** (2026-03-23, 6 rounds, 3/3 resolved) |
| 002 | Contamination firewall | F-04 | **CLOSED** (2026-03-25, 6 rounds, 3 Converged + 4 Judgment call) |
| 003 | Protocol engine | F-05, F-36, F-37 + SSE-D-04 | **OPEN** (2026-03-22, Wave 3 — chờ 001+002+004+015+016+017A+019A+019D1) |
| 004 | Meta-knowledge governance | F-06 | **CLOSED** (2026-03-21, 6 rounds, 23/23 resolved) |
| 005 | Core engine design | F-07 | **OPEN** (2026-03-22, Wave 2) |
| 006 | Feature engine design | F-08, F-38 + SSE-D-03 | **OPEN** (2026-03-22, Wave 2) |
| 007 | Philosophy & mission claims | F-01, F-20, F-22, F-25 | **CLOSED** (2026-03-23, 4/4 Converged) |

> **Topic 007 closure** (2026-03-23, 4 rounds, 4/4 Converged):
> F-01: bounded promise (inherit methodology, not answers). F-20: 3-tier claim
> model (Mission/Campaign/Certification). F-22: 3-type evidence taxonomy on
> exhausted archives. F-25: internal regime logic allowed, per-regime tables
> forbidden. Dependencies: all downstream topics inherit. See
> `debate/007-philosophy-mission/final-resolution.md`.

| 008 | Architecture & identity | F-02, F-09, F-13, SSE-04-IDV | **CLOSED** (2026-03-27) |
| 009 | Data integrity | F-10, F-11 | **OPEN** (2026-03-22, Wave 2) |
| 010 | Clean OOS & certification | F-12, F-21, F-23, F-24 | **CLOSED** (2026-03-25) |
| 011 | Deployment boundary | F-26, F-27, F-28, F-29 | **OPEN** (2026-03-22, Wave 2) |
| 012 | Quality assurance | F-18, F-39 (active) + F-19 (demoted) | **OPEN** (2026-03-22, Wave 2) |
| 013 | Convergence analysis | F-30, F-31 + SSE-09, SSE-04-THR | **CLOSED** (2026-03-28) |
| 014 | Execution & resilience | F-32, F-33, F-40/ER-03 | **OPEN** (2026-03-22, Wave 3 — chờ 003+005) |
| 015 | Artifact & version management | F-14, F-17 + SSE-07, SSE-08, SSE-04-INV | **OPEN** (2026-03-22, Wave 2) |
| 016 | Bounded recalibration path | BR-01, BR-02 | **OPEN** (2026-03-23, Wave 2.5 — chờ 001+002+010+011+015) |
| 017 | Epistemic search policy **(SPLIT)** | → 017A (ESP-01, ESP-04, SSE-04-CELL) + 017B (ESP-02, ESP-03, SSE-08-CON) | **SPLIT** (2026-04-03, Wave 2.5 — deps satisfied: 002✅+008✅+010✅+013✅). 003 only needs 017A |
| 018 | Search-space expansion | SSE-D-01→D-11 | **CLOSED** (2026-03-27, 6 rounds, 10 Converged + 1 Judgment call) |
| 019 | Discovery feedback loop **(SPLIT)** | → 9 sub-topics: 019A-G, 019D1-D3 (18 findings, 21 decisions) | **SPLIT** (2026-04-02, Wave 2.5 — deps satisfied: 018✅+002✅+004✅). 003 only needs 019A+019D1 |

**Dependencies** (synced with `debate/debate-index.md`):

```
007 (philosophy) ← foundation for all — Wave 1, debate ĐẦU TIÊN
    ↓
008, 009, 010, 011, 012       ← soft-dep from 007 — Wave 2, song song
001, 002, 005, 006, 013, 015  ← soft-dep from 007 — Wave 2, song song
    ↓
016 (bounded-recal) ← HARD-dep from 001 + 002 + 010 + 011 + 015 — Wave 2.5
017A (intra-ESP)    ← HARD-dep from 002 + 008 + 010 + 013 + 018 — Wave 2.5, ALL DEPS SATISFIED
019A (foundations)   ← HARD-dep from 018 + 002 + 004 — Wave 2.5, ALL DEPS SATISFIED (Tier 1 blocker)
019E/F/G (indep.)   ← HARD-dep from 018 + 002 + 004 — Wave 2.5, song song với 019A
019B/C → 019D1/D2 → 019D3 (internal waves, after 019A)
017B (inter-ESP)    ← HARD-dep from 017A (sequential)
    ↓
003 (protocol) ← HARD-dep from 001 + 002 + 004(closed) + 015 + 016 + 017A + 019A + 019D1 — Wave 3
014 (execution) ← soft-dep from 003 + 005 — Wave 3
```

**Bắt đầu từ đâu**:
1. ~~Topic **004**~~ — **CLOSED** (2026-03-21). 6 rounds, 23/23 resolved.
2. ~~Topic **000**~~ — **SPLIT** (2026-03-22). 29 findings → 11 sub-topics.
3. ~~Topic **007**~~ — **CLOSED** (2026-03-23). 4 rounds, 4/4 Converged.
4. Wave 2 (11 topics, 3 CLOSED: ~~001~~, ~~002~~, ~~010~~; 8 remaining) — song song, 007 đã closed.
5. Wave 2.5: Topic **016** (bounded recalibration) + **017A/B** (epistemic search policy, SPLIT) + **019A-G/D1-D3** (discovery feedback loop, SPLIT) — song song, sau Wave 2 prerequisites.
6. Wave 3: Topic **003** (protocol) + **014** (execution) — cuối cùng.
7. Topic **018** — **CLOSED** (2026-03-27). 6 rounds (standard 2-agent). 10 Converged + 1 Judgment call (SSE-D-05). Discovery mechanisms distributed to 006/015/017/013/008/003. Downstream routings confirmed.

> **Closed 2026-03-27** — 6 rounds (standard 2-agent). 10 Converged +
> 1 Judgment call (SSE-D-05). Discovery mechanisms distributed to
> 006/015/017/013/008/003. Downstream routings confirmed.

Chi tiết từng topic — xem Phần 5.

---

## Phần 5 — Chi tiết Debate Topics

> **Source of truth**: Khi topic đã có thư mục riêng (`debate/NNN-slug/`), thư
> mục đó là authoritative. Phần dưới giữ chi tiết cho topics PLANNED (chưa có
> thư mục). Topics OPEN chỉ giữ summary + pointer.

### 001 — Campaign Model

**Câu hỏi**: Tổ chức nghiên cứu theo Campaign → Session model hay mô hình khác?

**Bối cảnh**: Hiện tại x37 dùng flat sessions (`s01`, `s02`, ...) không có
hierarchical grouping. Thiết kế sơ bộ đề xuất Campaign model nơi mỗi campaign
gom N sessions trên cùng dataset. Cần tranh luận xem đây có phải abstraction
đúng không.

**Các vị trí cần tranh luận**:
- Campaign = fixed dataset + N sessions → convergence → meta-lessons
- Flat sessions (giống x37 hiện tại) vs hierarchical campaigns
- Campaign = dataset + protocol: quá thô? V7 cho phép rewrite search ladder
  và decision gates giữa campaigns (PROMPT_FOR_V7_HANDOFF.md line 31-33) —
  cần tách DatasetSnapshot / ProtocolSpec / ResearchRun?
- Hai giai đoạn: nghiên cứu (HANDOFF campaigns) → Clean OOS (bắt buộc conditional, sau winner + data mới)
- Stop conditions: khi nào giai đoạn nghiên cứu nên dừng?
- `NO_ROBUST_IMPROVEMENT` như first-class verdict (không phải failure)

**Evidence base**:
- `x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` — divergence giữa sessions V4→V7 (latest)
- `x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md` — future data handling
- `x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` — iteration model (latest)
- `x37/resource/gen1/v8_sd1trebd/research/config/session_finality_statement.txt` — finality pattern
- `x37/x37_RULES.md` — session isolation patterns hiện tại

**Closure sync (2026-03-23)**:
- Final resolution thực tế freeze Topic 001 bằng authority nội bộ
  `docs/design_brief.md:96-118`, same-data governance ở `PLAN.md:500-506`, và
  Topic 015 classification table (`debate/015-artifact-versioning/findings-under-review.md:92-99`).
- Extra-archive evidence đã thực sự được dùng trong closure context: Convergence
  V3 (divergence rationale), Clean OOS V1/V2 (future-data boundary), và V7
  handoff rule cho same-file cap / no-new-clean-OOS.
- Residual evidence gap không blocking: Convergence V1/V2 chưa đọc riêng cho
  Topic 001; chấp nhận được vì V3 là bản tổng hợp mới nhất và D-16 đóng bằng
  Judgment call, không cần thêm empirical tie-break trong chính topic này.

---

### 002 — Contamination Firewall

> **CLOSED** (2026-03-25). 6 rounds, 7/7 resolved (3 Converged + 4 Judgment call).
> Xem `debate/002-contamination-firewall/final-resolution.md`.
> Key decisions: 3 F-06 categories permanent (STOP_DISCIPLINE consolidated into ANTI_PATTERN; no expansion), state machine hash-signing,
> chmod defense-in-depth, permanent `UNMAPPED + Tier 2 + SHADOW` for ~10 gap rules
> (Topic 004 second fork), GAP/AMBIGUITY distinction permanent,
> PROVENANCE_AUDIT_SERIALIZATION split deferred.
> Dependencies resolved for: 016, 017 (firewall boundary input), 003 (via 016/017).

**Câu hỏi**: Thiết kế machine-enforced isolation như thế nào?

**Bối cảnh**: Hiện tại, contamination isolation phụ thuộc vào AI tự tuân thủ
quy tắc trong prompt ("DO NOT include specifics"). 8 rounds đã contaminate
toàn bộ data file. Framework cần enforcement bằng code.

**Các vị trí cần tranh luận**:
- Typed lesson schema: category enum + whitelist enforcement
- Sealed specifics store: format và access control
- State machine cho protocol transitions: complexity vs correctness
- Filesystem read-only (chmod) như guardrail phụ: khi nào áp dụng?
- Contamination log timing: chỉ readable sau freeze?

**Evidence base**:
- `x37/docs/gen1/RESEARCH_PROMPT_V8/CONTAMINATION_LOG_V4.md` — contamination thực tế (8 rounds, latest)
- `x37/resource/gen1/v8_sd1trebd/research/config/provenance_declaration.json` — independence claims pattern
- `x37/docs/gen1/RESEARCH_PROMPT_V6/PROMPT_FOR_V6_HANDOFF.md` §E — isolation rules
- `x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` — transfer rules (latest)
- `x37/resource/gen1/v5_sfq70/` — thiếu full serialization, bài học

---

### 003 — Protocol Engine

> **Source of truth**: `debate/003-protocol-engine/`
> **Rebalanced (2026-03-22)**: F-14/F-17 tách sang Topic 015. Chỉ còn F-05.

**Câu hỏi**: Biên dịch V6 protocol thành executable pipeline như thế nào?

**Bối cảnh**: RESEARCH_PROMPT_V6.md định nghĩa 8 stages chi tiết. x37_RULES.md
thêm phase gating rules. Cần chuyển từ "document mà AI phải tuân thủ" thành
"code tự enforce". Nhưng offline pipeline khác online conversation — một số
quy tắc có thể cần điều chỉnh. Artifact enumeration (F-14) và change
classification (F-17) đã tách sang Topic 015.

**Các vị trí cần tranh luận**:
- 8 stages giữ nguyên hay gộp/tách? (V6 có 8, x37 có 7 phases)
- Phase gating: kiểm tra filesystem artifacts (file exists?) vs state machine
  (track transitions?) vs hybrid
- Freeze checkpoint: chmod read-only vs immutable flag vs hash verification
- Provenance tracking: tự động (pipeline log mọi thứ) vs manual
- WFO fold structure: configurable (user chọn) vs fixed (semiannual from V6)
- Benchmark embargo: giữ như protocol rule mặc định (bảo vệ selection
  cleanliness, không chỉ chặn AI peek — RESEARCH_PROMPT_V6.md line 284-292).
  Chỉ cho phép ngoại lệ nếu có lý do phương pháp luận rất rõ ràng.

**Evidence base**:
- `x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md` — 8 stages
- `x37/x37_RULES.md` §7 — phase gating
- `x37/docs/gen1/RESEARCH_PROMPT_V6/SPEC_REQUEST_PROMPT.md` — deliverable format (V6)
- `x37/docs/gen1/RESEARCH_PROMPT_V8/SPEC_REQUEST_PROMPT.md` — deliverable format (V8, latest, 263 lines)
- `x37/resource/gen1/v5_sfq70/spec/` vs `x37/resource/gen1/v6_ret168/spec/` vs `x37/resource/gen1/v8_sd1trebd/spec/` — evolution

---

### 004 — Meta-Knowledge Governance

> **Source of truth**: `debate/004-meta-knowledge/` — README, findings,
> solution proposal, critique. Phần dưới là summary; chi tiết tại topic dir.

**Câu hỏi**: Làm sao classify, inherit, challenge, và retire meta-knowledge
qua campaigns — mà không leak data conclusions ngầm dưới dạng "universal
methodology"?

**Status**: **CLOSED** (2026-03-21). 6 rounds completed, 23/23 issues resolved
(16 Converged + 5 Decided + 2 pre-debate Resolved). Xem `debate/004-meta-knowledge/final-resolution.md`.

**Key files**:
- `debate/004-meta-knowledge/findings-under-review.md` — 17 findings, 3 groups
- `debate/004-meta-knowledge/input_solution_proposal.md` — Policy Object Model
- `debate/004-meta-knowledge/input_proposal_critique.md` — 6 critiques
- `debate/004-meta-knowledge/README.md` — scope, evidence base, debate status

---

### 005 — Core Engine Design

**Câu hỏi**: Xây engine từ đầu, vendor từ v10, hay hybrid?

**Bối cảnh**: v10/core/ là production engine đã chạy 40+ strategies, hàng trăm
backtests. Nhưng nó phục vụ nhiều mục đích (live trading, paper, research).
Framework chỉ cần long/flat backtest. Thiết kế sơ bộ đề xuất rebuild.

**Các vị trí cần tranh luận**:
- Full rebuild (clean, API tối ưu) vs vendor 5-8 files (fast, proven)
  vs hybrid (vendor core types, rebuild engine)
- Interface design: minimize surface area vs match v10 API (easier migration)
- Data loader: audit tích hợp (load + audit = 1 step) vs tách module
- Cost model: pure function `apply_cost(price, bps)` vs configurable object
- Performance: numpy vectorized (fast cho sweeps) vs event-loop (flexible)
- Test: regression kiểm tra engine math, D1↔H4 alignment, cost handling,
  frozen-spec replay, artifact conformance — KHÔNG bắt discovery pipeline
  phải chọn lại winner cũ (V5 thiếu full scan universe nên exact reproduction
  không khả thi)

**Evidence base**:
- `v10/core/` — engine.py, data.py, types.py, metrics.py, execution.py
- `docs/research/RESEARCH_RULES.md` — Pattern A (engine) vs Pattern B (vectorized)
- `x37/resource/gen1/v5_sfq70/spec/` — test vectors
- `x37/resource/gen1/v6_ret168/spec/` — test vectors

---

### 006 — Feature Engine Design

**Câu hỏi**: Thiết kế feature engine extensible và exhaustive như thế nào?

**Bối cảnh**: V5 scan 261 features (8 categories). V6 scan 2,219 configs.
Contamination log (8 rounds, CONTAMINATION_LOG_V4) liệt kê hàng trăm features đã thử. Framework
cần engine có thể scan 50K+ configs tự động, extensible để thêm features
mới mà không sửa pipeline.

**Các vị trí cần tranh luận**:
- Registry pattern (@decorator trên function) vs config-driven (YAML/JSON
  define features)
- Feature families: 1 file = 1 family (trend.py chứa 6 features) vs
  1 file = 1 feature (ret.py, trendq.py, ...)
- Threshold calibration modes: bao nhiêu modes? V5 dùng static calendar-year;
  V6 dùng fixed zero, expanding, rolling. Cần tất cả? Thêm?
- Cross-timeframe alignment: engine-level (data loader tự align D1→H4) vs
  feature-level (mỗi cross-TF feature tự align)
- Exhaustive scan: enumerate tất cả feature × lookback × threshold × mode
  combos, hay intelligent pruning (skip combos dựa trên correlation)?
- Serialization: parquet (compact, typed) vs CSV (human-readable) vs
  HDF5 (fast random access) cho stage1 registry 50K+ rows
- Cache: memoize computed features (RAM) vs recompute mỗi lần (disk I/O)?

**Evidence base**:
- `x37/resource/gen1/v5_sfq70/spec/research_reproduction_spec_SF_EFF40_Q70_STATIC.md`
  — 12-step protocol, 261 features, 8 role categories
- `x37/resource/gen1/v6_ret168/spec/BTCUSDT_V6_Research_Reproduction_Spec.md`
  — 2,219 configs, feature manifest format
- `x37/docs/gen1/RESEARCH_PROMPT_V8/CONTAMINATION_LOG_V4.md` — full feature inventories (8 rounds, latest)
- `x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md` §Stage 1 — scan requirements
- `x37/resource/gen1/v8_sd1trebd/research/data/stage1_feature_registry.csv` — 1,234 V8 feature configs
- `x37/resource/gen1/v8_sd1trebd/research/data/frozen_stage1_feature_manifest.csv` — 29 V8 feature families

### 013 — Convergence Analysis

> **Source of truth**: `debate/013-convergence-analysis/`

> Topic 013 CLOSED 2026-03-28 (6 rounds canonical + 12 rounds JC-debate). Hybrid C convergence framework,
> bootstrap defaults with 5-tier provenance, Holm correction law,
> equivalence thresholds. Unblocks Topic 017.

**Câu hỏi**: Framework toán học/thống kê nào để đo convergence giữa N sessions
và xác định stop conditions?

**Bối cảnh**: F-03 (Campaign Model) nói "convergence analysis chéo giữa sessions"
nhưng không định nghĩa thuật toán. V4→V8 cho thấy 5 sessions, 5 winners khác
family — kết luận convergence dựa trên human judgment, không phải metric.
Topic 001 định nghĩa **cấu trúc** (what is a campaign), topic 013 định nghĩa
**thuật toán** (how to measure convergence).

**Các vị trí cần tranh luận**:
- Granularity: family-level vs architecture-level vs parameter-level vs performance-level
- Distance metric: winner voting, Sharpe distribution overlap, top-K Jaccard, rank ρ
- Statistical test: bootstrap, permutation, majority voting
- Partial convergence: converge family nhưng diverge params → đủ cho Clean OOS?
- Stop conditions: diminishing returns detection, same-data ceiling, exhaustion
- Interaction với MK-17 (shadow-only): same-data campaigns diminish faster

**Evidence base**:
- `x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` — V4→V8 divergence
- `x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` line 62 — same-file iteration limits
- x38 F-03: "convergence analysis" mentioned nhưng không defined
- x38 F-15: metric scoping ảnh hưởng cách đo convergence
- Topic 004 MK-17: shadow-only trên same dataset

---

### 014 — Execution & Resilience

> **Source of truth**: `debate/014-execution-resilience/`

**Câu hỏi**: Mô hình thực thi pipeline: compute orchestration, checkpointing,
crash recovery, và human interaction model (CLI)?

**Bối cảnh**: PLAN.md §1.3 nói "50K+ configs, parallel compute" nhưng không có
thiết kế. Pipeline 8 stages chạy hàng giờ → crash là inevitable → cần
checkpointing. Topic 003 định nghĩa **logic** các stages (what), topic 014
định nghĩa **cách chúng chạy** đáng tin cậy (how).

**Các vị trí cần tranh luận**:
- Local multiprocessing vs distributed (Dask/Ray) vs hybrid
- Data sharing: shared memory vs copy-per-worker vs feature caching
- Checkpoint granularity: per-stage vs per-batch vs per-config
- Idempotency: resume sau crash cho kết quả giống chạy liền?
- State tracking: state file vs artifact-existence-based
- Partial artifact policy: delete-and-rerun vs validate-and-resume
- CLI interaction: run/resume/status/validate commands

**Evidence base**:
- PLAN.md §1.3: "Exhaustive scan (50K+ configs), parallel compute"
- PLAN.md §2.3: target directory, `campaigns/` immutable after close
- `x37/x37_RULES.md` §7: phase gating = natural checkpoint points
- `docs/research/RESEARCH_RULES.md`: Pattern A (engine) vs Pattern B (vectorized)
- v10 backtest engine: ~3.6s per run (research script estimates)

---

### 015 — Artifact & Version Management

> **Source of truth**: `debate/015-artifact-versioning/`
> **Split from Topic 003** (2026-03-22): F-14/F-17 có bản chất "records &
> versioning", khác với F-05 (pipeline logic).

**Câu hỏi**: Session artifacts gồm những gì? Khi nào code changes invalidate
kết quả cũ?

**Bối cảnh**: Gen4 định nghĩa 18 artifacts bắt buộc và semantic change
classification. Alpha-Lab cần tương tự nhưng adapted cho offline discovery.
F-14 (what gets recorded) và F-17 (when results become invalid) cùng concern:
**artifact lifecycle**. Tách từ 003 để debate sớm hơn (Wave 2).

**Các vị trí cần tranh luận**:
- Artifact manifest: mandatory vs optional? Hash manifest per-session?
- Auto-generated session summary hay human-written?
- Bit-identical trade log test khả thi cho Alpha-Lab?
- Invalidation scope: toàn bộ sessions hay chỉ affected?
- Auto re-run khi engine change hay manual trigger?
- engine_version field trong session metadata?

**Evidence base**:
- `x37/docs/gen4/core/STATE_PACK_SPEC_v4.0_EN.md` — 18 required files
- `x37/docs/gen4/core/research_constitution_v4.0.yaml` §semantic_change — classification + bit-identical test
- btc-spot-dev: D1→H4 fix invalidated 195 scripts (real example of semantic change)

---

## Phần 6 — Status & Logistics

### Current Status (cập nhật 2026-03-29)

| Phase | Status | Mô tả |
|-------|--------|-------|
| Design brief | DONE | `docs/design_brief.md` |
| V8 online results | DONE | V8 session hoàn tất, resource published |
| Evidence coverage | DONE | `docs/evidence_coverage.md` — Phase 0 DONE (2026-03-21) |
| Debate topics defined | DONE | 20 topics (000 SPLIT + 004/007/001/002/010/008/018/013 CLOSED + 11 OPEN). Xem `debate/debate-index.md`. |
| Debate findings collected | DONE | 81 findings distributed (per-topic counts in `debate/debate-index.md`; excludes Topic 004 MK-series and Topic 000 convergence notes C-01→C-12). |
| Debate execution | IN PROGRESS | 8 topics CLOSED: 004, 007, 001, 002, 010, 008, 018, 013. 88 debate rounds done. 11 topics remaining (all OPEN; Topic 000 SPLIT into sub-topics). |
| Drafts | SEEDED (1) + DRAFTING (3) | `meta_spec.md` SEEDED from 002/004/007/008 closures (eligible for DRAFTING). `architecture_spec.md` DRAFTING from 001/002/004/007/008/010/013/018 closures (§14 proposal from 019). `discovery_spec.md` DRAFTING from 018 closure (§6-§11 proposals from 019). `methodology_spec.md` DRAFTING from 013 closure. Publication gated on ALL dependencies CLOSED. |
| Publication | NOT STARTED | Sau drafts |

**V8 online results đã có** — không còn lý do chờ V8.

**Evidence đã đủ** — Phase 0 DONE (2026-03-21). V4 protocol, Clean OOS
V1/V2, 3 changelogs đã đọc toàn bộ. Xem `docs/evidence_coverage.md` §3.

**Topic SPLIT**:
- **000** (framework architecture): SPLIT (2026-03-22) — 29 findings phân bổ vào 11 sub-topics. File `debate/000-framework-proposal/findings-under-review.md` giữ lại index + convergence notes C-01→C-12.

**Topics CLOSED** (8):
- **004** (meta-knowledge): CLOSED (2026-03-21). 6 rounds, 23/23 resolved. Xem `debate/004-meta-knowledge/final-resolution.md`.
- **007** (philosophy-mission): CLOSED (2026-03-23). 4 rounds, 4/4 Converged. Xem `debate/007-philosophy-mission/final-resolution.md`.
- **001** (campaign-model): CLOSED (2026-03-23). 6 rounds, 3/3 resolved (2 Converged + 1 Judgment call). Xem `debate/001-campaign-model/final-resolution.md`.
- **002** (contamination-firewall): CLOSED (2026-03-25). 6 rounds, 7/7 resolved (3 Converged + 4 Judgment call). Xem `debate/002-contamination-firewall/final-resolution.md`.
- **010** (clean-oos-certification): CLOSED (2026-03-25). 6 rounds, 4/4 resolved (3 Converged + 1 Judgment call). Xem `debate/010-clean-oos-certification/final-resolution.md`.
- **008** (architecture-identity): CLOSED (2026-03-27). 8 rounds, 4/4 Converged. Xem `debate/008-architecture-identity/final-resolution.md`.
- **018** (search-space-expansion): CLOSED (2026-03-27). 6 rounds (standard 2-agent). 10 Converged + 1 Judgment call (SSE-D-05). Downstream routings confirmed. Xem `debate/018-search-space-expansion/final-resolution.md`.
- **013** (convergence-analysis): CLOSED (2026-03-28). 6+12 rounds, 4/4 Judgment call. Hybrid C convergence framework. Unblocks 017. Xem `debate/013-convergence-analysis/final-resolution.md`.

**Topics OPEN** (11 topics, 3 waves):
- **Wave 2** (6 topics song song): 005, 006, 009, 011, 012, 015
- **Wave 2.5** (12 debatable sub-topics): 016 (bounded-recalibration) — chờ 001✅ + 002✅ + 010✅ + 011 + 015; 017A (intra-campaign ESP) — ALL DEPS SATISFIED; 019A (discovery foundations, Tier 1 blocker) + 019E/F/G (independent, song song) — ALL DEPS SATISFIED. Internal waves: 019A→019B/C→019D1/D2→019D3. 017B after 017A. 003 chỉ cần 017A + 019A + 019D1
- **Wave 3**: 003 (protocol-engine) — chờ 001✅ + 002✅ + 004✅ + 015 + 016 + 017A + 019A + 019D1; 014 (execution) — chờ 003 + 005

> **Topic 019 OPENED 2026-03-29** — Discovery feedback loop. Gap identified during
> Topic 018 closure audit: framework designed validation infrastructure but missed
> the discovery mechanism. 100% of project alpha came from human intuition informed
> by data analysis, not grammar enumeration. Topic 019 designs the Human-AI
> collaborative loop: AI analysis layer (data + results), human-facing reporting,
> feedback capture, contamination boundary, deliberation-gated code authoring.
> 18 findings (DFL-01→DFL-18). Wave 2.5, all deps satisfied, song song với 017.
> DFL-06/07 (2026-03-30): raw data exploration + methodology.
> DFL-08/09 (2026-03-31): feature graduation path + SSE-D-02 scope clarification.
> DFL-10 (2026-03-31): pipeline integration — Stage 2.5 Data Characterization.
> **Topic 019 SPLIT 2026-04-02** — 9 sub-topics: 019A (foundations, Tier 1 blocker),
> 019B (AI analysis), 019C (data exploration), 019D1 (pipeline structure),
> 019D2 (budget), 019D3 (grammar), 019E (data quality), 019F (regime dynamics),
> 019G (data scope). Internal waves: 019A→B/C→D1/D2→D3. E/F/G independent, song song.
> **Topic 017 SPLIT 2026-04-03** — 017A (intra-campaign ESP: ESP-01+ESP-04+SSE-04-CELL)
> + 017B (inter-campaign ESP: ESP-02+ESP-03+SSE-08-CON). 003 only needs 017A.

**Ưu tiên debate**: ~~007 (Wave 1)~~ CLOSED → ~~018~~ CLOSED (routings confirmed) + 6 remaining Wave 2 topics song song (001/002/008/010/013 CLOSED) → 016 + 017A + 019A + 019E/F/G (Wave 2.5, song song) → 019B/C → 019D1/D2 → 019D3 + 017B → 003 + 014 (Wave 3) cuối cùng.

### Execution Plan

> **Kế hoạch thực thi chi tiết**: xem `EXECUTION_PLAN.md` — 5 phases, critical path,
> ước lượng 4-7 debate rounds (sequential, nhờ wave-parallel), 5-6 published specs. Agent tham gia debate PHẢI đọc
> file đó để biết mình đang ở phase nào.

### Deliverables

| Artifact | Mô tả | Vị trí |
|----------|-------|--------|
| Design brief | Input cho debate | `docs/` |
| Debate artifacts | Mỗi topic: findings, rounds, resolution | `debate/NNN-slug/` |
| `architecture_spec.md` | Campaign model, session lifecycle, data management, Clean OOS flow, convergence analysis. Firewall: enforcement mechanism | `drafts/` → `published/` |
| `protocol_spec.md` | 8-stage pipeline + gates, artifacts, change classification, execution model | `drafts/` → `published/` |
| `engine_spec.md` | Core engine design | `drafts/` → `published/` |
| `feature_spec.md` | Feature engine + registry | `drafts/` → `published/` |
| `meta_spec.md` | Meta-knowledge governance, lesson lifecycle. Firewall: content rules | `drafts/` → `published/` |
| `discovery_spec.md` | Discovery mechanisms: bounded ideation, recognition stack, APE v1, domain-seed hook, hybrid equivalence | `drafts/` → `published/` |

### Isolation Rules

- X38 KHÔNG sửa files ngoài `research/x38/`
- X38 KHÔNG viết implementation code (chỉ pseudocode/interface)
- Debate KHÔNG đề cập feature names, lookbacks, thresholds cụ thể
- Read-only access to: `x37/`, `x34/debate/`, `v10/core/`, `docs/`, `CLAUDE.md`

---

## Appendix A — Tham khảo nhanh cho agent mới

### Đường dẫn quan trọng

**Bảng đầy đủ tất cả tài liệu tham khảo (read-only)**: xem `x38_RULES.md` §7.

Dưới đây là đường dẫn nội bộ x38:

| Tài liệu | Path |
|-----------|------|
| **Execution plan** | `research/x38/EXECUTION_PLAN.md` |
| **X38 rules** | `research/x38/x38_RULES.md` |
| **Debate rules** | `research/x38/debate/rules.md` |
| **Debate index** | `research/x38/debate/debate-index.md` |
| **Prompt templates** | `research/x38/debate/prompt_template.md` |
| **Design brief** | `research/x38/docs/design_brief.md` |
| **Evidence coverage** | `research/x38/docs/evidence_coverage.md` |
| **Spec patterns** | `research/x38/docs/v6_v7_spec_patterns.md` |

### Thuật ngữ

| Thuật ngữ | Nghĩa |
|-----------|-------|
| **Campaign** | Nhóm N sessions chạy trên cùng dataset |
| **Session** | Một lần chạy discovery pipeline end-to-end |
| **Freeze** | Thời điểm frozen_spec.json được ghi, không cho sửa |
| **Contamination** | Data-derived specifics (features, thresholds) leak vào session mới |
| **Meta-knowledge** | Methodology lessons (principle-level, không specifics) |
| **Clean OOS** | Out-of-sample trên data thật sự mới (chưa ai thấy) |
| **Clean reserve** | Data mới dùng cho Clean OOS — chưa tồn tại khi nghiên cứu chạy |
| **Internal reserve** | Phần data giữ lại từ cùng file cho Stage 8 — đã contaminate qua sessions |
| **Internal OOS** | Out-of-sample trên cùng file (đã bị contaminate cross-session) |
| **NO_ROBUST_IMPROVEMENT** | Không tìm được candidate qua hard gates — valid outcome |

### Quy tắc vàng cho agent tham gia debate

1. **Đọc `docs/online_vs_offline.md`** — **BẮT BUỘC** — phân biệt online/offline
2. **Đọc `x38_RULES.md`** — quy tắc và phạm vi
3. **Đọc `PLAN.md` (file này)** — master plan + bối cảnh đầy đủ
4. **Đọc `docs/design_brief.md`** — input chính thức cho debate (authoritative nếu mâu thuẫn với PLAN.md)
5. **Đọc `EXECUTION_PLAN.md`** — trạng thái hiện tại + phase đang chạy
6. **Đọc `debate/rules.md`** — quy tắc tranh luận
7. **Đọc topic `findings-under-review.md`** — nắm các điểm đang tranh luận
8. **Đọc evidence base** (tài liệu tham khảo ghi trong topic) trước khi phản biện
7. **KHÔNG** đề cập feature names, lookbacks, thresholds cụ thể
8. **KHÔNG** viết implementation code — chỉ pseudocode/interface
9. **KHÔNG** tìm đồng thuận — tìm đáp án đúng nhất theo bằng chứng

---

## Appendix B — Online Results Embargo

**V8 đã được incorporate** (2026-03-19): toàn bộ V8 docs + resource đã đọc,
findings đã cập nhật. Xem `docs/evidence_coverage.md` §2 cho chi tiết.

Quy trình cho **V9+ nếu có** (tương lai):
1. Đọc và phân tích tài liệu vòng mới, ghi vào `docs/evidence_coverage.md`
2. Review convergence status mới (hội tụ hay diverge tiếp?)
3. Cập nhật debate topics nếu vòng mới reveal issues mới
4. KHÔNG sửa `findings-under-review.md` đang open vì online results — mở issue mới nếu cần
