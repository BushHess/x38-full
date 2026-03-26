---
doc_type: debate_round_review
topic: search-space-expansion
round: 2
author: claude_code
date: 2026-03-26
status: OPEN
sources:
  - ../../request.md
  - ../gemini/gemini_propone.md
  - ../codex/codex_propone.md
  - ./claude_propone.md
  - ../chatgptpro/chatgptpro_propone.md
  - ../gemini/gemini_debate_lan_1.md
  - ../codex/codex_debate_lan_1.md
  - ./claude_debate_lan_1.md
  - ../chatgptpro/chatgptpro_debate_lan_1.md
  - ../../../online_vs_offline.md
  - ../../../design_brief.md
  - ../../../../debate/rules.md
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

# Debate Round 2 — Concessions, Residual Gaps, and the "Who Writes VDO?" Pressure Test

## 1. Kết luận nhanh

Vòng 1 cho thấy hội tụ mạnh ở infrastructure (lineage, cell-elite, gate split, shadow-only ceiling) nhưng phân rẽ ở **generation mechanism**. Codex + ChatGPT Pro được chọn làm backbone bởi cả 4 bên — tôi chấp nhận. Tôi rút lại Topic 018 bundle và SSS như subsystem chính thức. Nhưng tôi giữ nguyên áp lực: **backbone v1 hiện tại không trả lời được "ai/cái gì tạo ra features mới khi registry trống"**. GFS depth-1 là câu trả lời tối thiểu cần có. Vòng này tập trung vào 3 việc: (1) chốt concession chính thức cho các điểm tôi rút, (2) defend GFS depth-1 như minimum generation mechanism, (3) đóng các OI đã đủ chín.

---

## 2. Scoreboard (cập nhật)

| Agent | Bám yêu cầu | Bám X38 | Khả thi v1 | Sức mở search | Kỷ luật contamination | Độ rõ artifact | Verdict ngắn |
|-------|-------------|---------|------------|---------------|----------------------|----------------|--------------|
| Gemini | Trung bình | Tốt | Tốt | Trung bình | Tốt | Yếu | Giữ offline-first + provenance phụ; thiếu engine |
| Codex | Rất tốt | Rất tốt | Tốt | Rất tốt | Tốt | Rất tốt | Backbone artifact/lineage mạnh nhất |
| Claude | Tốt | Trung bình→Tốt | Trung bình→Tốt | Rất tốt | Trung bình→Tốt | Tốt | Sau concession: scope hẹp hơn, contamination risk giảm |
| ChatGPT Pro | Rất tốt | Rất tốt | Rất tốt | Tốt | Rất tốt | Tốt | Co-baseline v1 vững; vẫn thiếu generation answer |

**Thay đổi so với vòng 1:**
- **Claude (self)**: Bám X38 tăng (rút SSS/Topic 018 bundle, sửa contamination risk). Khả thi v1 tăng (scope hẹp hơn). Kỷ luật contamination tăng (SSS OHLCV-only hoặc defer).
- Các agent khác: giữ nguyên — chưa có evidence mới để thay đổi.

---

## 3. Convergence Ledger (cập nhật — thêm mục mới từ round 1)

> Import các điểm đã đủ chắc từ round 1 cross-agent review.

| ID | Kết luận hội tụ | Basis | Status | Ghi chú |
|----|----------------|-------|--------|---------|
| CL-01 | X38 mạnh validation, yếu discovery — cần bổ sung cơ chế khám phá | 4/4 proposal + 4/4 debate round 1 | CONVERGED | Chẩn đoán nền, không bàn lại |
| CL-02 | Tách Tầng 1 (exploration) và Tầng 2 (recognition/systematization) | Yêu cầu gốc + 4/4 proposal | CONVERGED | Cơ chế cụ thể từng tầng còn OPEN |
| CL-03 | Post-lock execution phải deterministic offline; AI không được evaluate/rank/select trong runtime | 4/4 proposal + `online_vs_offline.md` | CONVERGED | Mọi ý tưởng mới phải tuân invariant này |
| CL-04 | Discovery artifact phải machine-readable; prompt/transcript là provenance phụ, không phải canonical lineage | 4/4 round 1: Codex OI-04, ChatGPT Pro OI-04, Claude self-critique, Gemini CL-01 | CONVERGED | Canonical = operator/candidate genealogy trong offline runner |
| CL-05 | Cell-elite archive thay global top-K để giữ diversity | 4/4 proposal + ESP-01 + Codex E3 | CONVERGED | Chi tiết cell dimensions còn OPEN (→ OI-08) |
| CL-06 | Discovery gates ≠ certification/deployment gates — hai inventory khác nhau | ChatGPT Pro (gate split) + Codex OI-03 + Claude round 1 + Gemini CL-04 | CONVERGED | Inventory cụ thể còn OPEN |
| CL-07 | Same-dataset learned priors shadow-only; activation chỉ sau context distance thật | MK-17 + design brief + 4/4 round 1 | CONVERGED | v1 chỉ build OBSERVED/REPLICATED_SHADOW storage |
| CL-08 | Freeze giữ comparison set + coverage/phenotype evidence, không chỉ winner đơn lẻ | Codex + ChatGPT Pro + ESP-01/02 | CONVERGED | Schema còn OPEN |
| CL-09 | Recognition phải chấm **consistency motif** (cross-timescale/cross-resolution), không chỉ peak score | ChatGPT Pro insight + VDO evidence (16/16 timescales, DOF p=0.031) [extra-archive: `../../../../../../STRATEGY_STATUS_MATRIX.md`; `../../../design_brief.md:59-74`] | CONVERGED | VDO sẽ chết nếu nhìn cục bộ — bài học trực tiếp từ btc-spot-dev |
| CL-10 | Backbone v1 nên là Codex + ChatGPT Pro (lineage + cell-elite + gate split + artifact contract) | 3/4 round 1 chọn direction này; Claude self-critique xác nhận over-scope | CONVERGED | Generation mechanism trên backbone này còn OPEN |

---

## 4. Open Issues Register — Phản hồi vòng 2

> Tôi dùng OI numbering của ChatGPT Pro (8 OIs, comprehensive nhất) làm trục chính,
> bổ sung Codex OI-06 (breadth vs multiplicity). Mapping sang numbering của các agent khác
> được ghi trong mỗi OI.

---

### OI-01 — Có nên mở Topic 018 hay fold vào topics hiện có?

*Mapping: ChatGPT Pro OI-01 / Codex OI-01 / Gemini implicit / Claude D1*

- **Stance**: AMEND — rút Topic 018 bundle, giữ boundary observation

- **Điểm đồng ý**:
  - ChatGPT Pro đúng: mở umbrella topic khi 017 chưa close sẽ nổ scope và chậm critical path (`../chatgptpro/chatgptpro_debate_lan_1.md:126-128`).
  - Codex đúng: chưa đủ burden of proof để commit owner mới ở v1 (`../codex/codex_debate_lan_1.md:100-101`).
  - 017 đã own search policy và có scope cho coverage, cell-elite, budget governor.

- **Điểm phản đối (steel-man cho vị trí cũ của tôi)**:
  - Argument mạnh nhất cho Topic 018: 017 README tự giới hạn scope vào "intra-campaign illumination, phenotype contracts, promotion ladder, budget governor" (`../../../../debate/017-epistemic-search-policy/README.md:25-32`). Pre-lock generation (ai/cái gì tạo features mới) thực sự nằm NGOÀI scope 017 đã tự khai báo.
  - **Tại sao steel-man này không đủ**: Boundary observation đúng, nhưng **nhảy từ "cần owner" sang "cần Topic 018 gộp GFS+APE+SSS+CDAP"** là bước nhảy quá lớn. Owner có thể là contract hẹp trong 006 (generation mechanism) + 017 (policy/budget), không cần topic mới. Burden of proof thuộc bên đề xuất topic mới (rules.md §5), và tôi chưa chứng minh 006+017 không gánh nổi.

- **Đề xuất sửa**:
  - v1: fold pre-lock generation contract vào 006 (operator grammar + generation mechanism) và 017 (policy/budget/coverage obligation).
  - Mở topic mới CHỈ KHI: sau khi 006 và 017 close, ownership thật sự bị tràn và gây mâu thuẫn interface. Đây là điều kiện cụ thể, testable.
  - Ghi rõ trong 006 findings: "006 owns generation mechanism (how features get created), 017 owns search policy (which features get explored and how)".

- **Evidence**: `../../../../debate/017-epistemic-search-policy/README.md:25-32,43-46`; `../codex/codex_debate_lan_1.md:97-101`; `../chatgptpro/chatgptpro_debate_lan_1.md:118-128`

- **Trạng thái**: PARTIAL → hướng tới fold. Điều kiện mở topic mới đã nêu rõ.

---

### OI-02 — Creative AI session: SSS hay bounded ideation lane?

*Mapping: ChatGPT Pro OI-02 / Codex OI-01 (partial) / Gemini OI-03*

- **Stance**: AMEND — rút SSS như subsystem chính thức, chấp nhận bounded ideation lane

- **Điểm đồng ý**:
  - ChatGPT Pro đúng khi bác bỏ SSS như first-class subsystem ở v1 (`../chatgptpro/chatgptpro_debate_lan_1.md:147-152`). 4 hard rules của ChatGPT Pro là đúng:
    1. Output canonical = manifest/spec, không phải transcript.
    2. AI không evaluate/select/rank/verdict.
    3. AI không nhìn prior answer-level results trên cùng dataset.
    4. Mọi thứ phải compile thành machine-readable artifact trước pipeline.
  - Codex đúng: SSS chạm campaign-transition law và firewall mạnh hơn tôi đã thừa nhận (`../codex/codex_debate_lan_1.md:278`).
  - Tự phản biện round 1 của tôi đã đúng: SSS KHÔNG NÊN xem current registry vì gián tiếp leak "campaign trước thử gì" (`./claude_debate_lan_1.md:176-181`).

- **Điểm phản đối (steel-man cho SSS)**:
  - SSS trực tiếp tái tạo origin story của VDO: AI session + loose prompt + OHLCV data → novel feature idea. Không mechanism nào khác thực sự tái tạo "happy accident" ở mức này.
  - **Tại sao steel-man không đủ**: "Tái tạo origin story" là hindsight reasoning. VDO hữu ích không phải VÌ nó ra từ AI session, mà vì `volume × direction` là một meaningful composition. GFS depth-1 grammar cover composition này mà không cần online session. Và nếu feature hữu ích KHÔNG phải composition (mà là conceptual insight), thì bounded ideation lane (AI đề xuất spec, human review, compile thành registry) đủ mà không cần SSS infrastructure.

- **Đề xuất sửa**:
  - v1: **bounded ideation lane** với 4 hard rules của ChatGPT Pro + 1 rule bổ sung: AI input = OHLCV schema + operator library only, KHÔNG nhìn current registry hay prior results. Dedup xảy ra post-hoc khi compile spec vào registry.
  - Output: `proposal_spec.yaml` hoặc `candidate_grammar.json`.
  - Owner: 006 (compilation vào registry) + 017 (budget cho ideation vs scan).
  - SSS infrastructure (prompt templates, session protocols, transcript logs) → DEFER v2.

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_1.md:147-158`; `../codex/codex_debate_lan_1.md:276-282`; `./claude_debate_lan_1.md:174-181`; `../../../online_vs_offline.md:29-43`

- **Trạng thái**: PARTIAL → hướng tới bounded ideation lane. Schema output cần chốt.

---

### OI-03 — Minimum viable discovery engine cho v1

*Mapping: ChatGPT Pro OI-03 / Codex OI-02 (backbone) / Claude D2*

- **Stance**: AMEND — chấp nhận Codex + ChatGPT Pro backbone, nhưng **thêm GFS depth-1 là bắt buộc**

- **Điểm đồng ý**:
  - v1 backbone đúng: discovery lineage + descriptor taxonomy + coverage map + cell-elite archive + operator grammar + local probes + surprise queue + equivalence audit + proof bundle + freeze comparison set + phenotype pack + shadow-only prior. Tôi chấp nhận danh sách của ChatGPT Pro (`../chatgptpro/chatgptpro_debate_lan_1.md:177-184`).
  - Defer đúng: CDAP, full EPC lifecycle, GFS depth 2/3, SSS infrastructure, activation ladder vượt shadow.

- **Điểm phản đối**:
  - ChatGPT Pro liệt kê "GFS depth 2/3 ở quy mô lớn" trong phần defer, nhưng **không nói gì về GFS depth-1** (`../chatgptpro/chatgptpro_debate_lan_1.md:188`). Codex nêu "v1 có cần GFS depth-1 không, hay grammar+local probes là đủ?" như câu hỏi mở (`../chatgptpro/chatgptpro_debate_lan_1.md:199`).
  - **Đây là lỗ hổng lớn nhất của backbone hiện tại.** Tôi đặt pressure test:

    > **Pressure test**: Cho Alpha-Lab một asset mới (ví dụ: ETH/USDT), data OHLCV sẵn, operator grammar sẵn. v1 backbone không có GFS depth-1. Hỏi: Feature Engine registry chứa gì?

    Trả lời: **Trống**. Operator grammar chỉ định nghĩa "operators nào hợp lệ". Local probes chỉ đào quanh survivors hiện có. Cell-elite archive chỉ giữ diversity từ features đã tồn tại. Coverage map chỉ tag features đã có. **Không mechanism nào trong backbone tạo ra features.**

    ChatGPT Pro đã nhận diện yếu điểm này ở chính proposal gốc nhưng chỉ đề xuất "AI proposal sandbox, nhưng chỉ ở tầng spec" mà không chốt cơ chế cụ thể (`../chatgptpro/chatgptpro_propone.md:19`). Codex đề xuất E1 (manifest-first transform grammar) nhưng chưa khai báo grammar cụ thể (`./claude_debate_lan_1.md:117-123`).

  - **GFS depth-1 là câu trả lời tối thiểu nhất:**
    - Depth-1 = primitive × single operator × lookback = ~500-2,000 features. Scale hoàn toàn khả thi cho v1.
    - Deterministic: cùng grammar + cùng OHLCV schema = cùng feature set. Không có AI judgment. Hoàn toàn offline.
    - Dedup threshold |r| > 0.95 loại bỏ duplicates.
    - Mỗi feature có lineage machine-readable: `gfs_{operator}_{primitive}_{lookback}`.
    - VDO depth-2, nhưng nhiều useful features là depth-1: `ema(close, 20)`, `zscore(volume, 60)`, `rolling_std(log_return, 40)`, v.v.
    - Compute cost thấp: 2,000 features × Stage 3 scan ≈ vài giờ trên single machine.

  - **Không có GFS depth-1, "tai nạn tốt" vẫn phụ thuộc vào human hoặc AI viết features bằng tay** — chính xác failure mode mà request.md muốn giải quyết.

- **Đề xuất sửa**:
  - v1 = Codex + ChatGPT Pro backbone **+ GFS depth-1** (bắt buộc).
  - GFS depth-1 chạy trước protocol lock (Phase A position) hoặc đầu Stage 3 (Phase B position). Owner: 006.
  - GFS depth-2+ → DEFER, chỉ khi depth-1 yield NO_ROBUST_IMPROVEMENT.
  - Bounded ideation lane → bổ sung (optional), không thay thế GFS depth-1.

- **Evidence**: `./claude_propone.md:75-137`; `../chatgptpro/chatgptpro_debate_lan_1.md:177-199`; `../codex/codex_debate_lan_1.md:114-131`; `../../request.md:13` ("hiện tại không có quy trình nào chủ động tạo ra những lần 'vô tình' như vậy")

- **Trạng thái**: OPEN — GFS depth-1 bắt buộc hay optional cho v1 là tranh chấp thực chất.

---

### OI-04 — Canonical lineage schema

*Mapping: ChatGPT Pro OI-04 / Codex OI-04*

- **Stance**: AGREE

- **Điểm đồng ý**:
  - Canonical lineage = machine-readable structural lineage (Codex schema). Prompt ancestry = provenance phụ.
  - Schema tối thiểu đã hội tụ: raw channel, operator chain, parent candidate(s), role assignment, threshold mode, timeframe binding, protocol hash, data snapshot hash.
  - Prompt hash, transcript ref, domain hint, AI model metadata = optional supplementary provenance.

- **Điểm phản đối**: Không còn.

- **Đề xuất sửa**:
  - Tách `feature_lineage` (cho individual features) và `candidate_lineage` (cho strategy-level candidates) thành 2 sub-schemas sharing common fields. Lý do: features có operator chain đơn giản (depth 1-3), candidates có genealogy phức tạp hơn (base template + mutations + feature composition).
  - Prompt hash nên nằm trong **supplementary provenance**, không trong canonical schema. Canonical schema phải replay-able bởi code; prompt hash thì không.

- **Evidence**: `../codex/codex_propone.md:67-80`; `../chatgptpro/chatgptpro_debate_lan_1.md:212-225`; `../codex/codex_debate_lan_1.md:158-177`

- **Trạng thái**: PARTIAL → gần CONVERGED. Chốt vòng sau: feature vs candidate sub-schema.

---

### OI-05 — Recognition stack chuẩn + vai trò human

*Mapping: ChatGPT Pro OI-05 / Codex OI-03*

- **Stance**: AGREE với amendment nhỏ

- **Điểm đồng ý**:
  - Recognition stack v1: `surprise_queue → equivalence_audit → proof_bundle → freeze_comparison_set → candidate_phenotype → prior_registry (shadow-only)`.
  - ChatGPT Pro đúng: SDL criteria từ proposal Claude nên là INPUT cho `surprise_queue`, không phải subsystem riêng (`../chatgptpro/chatgptpro_debate_lan_1.md:239-253`).
  - Human chỉ ở 2 điểm: (1) ambiguity/reconstruction-risk/semantic interpretation, (2) deployment authority. Không chen sâu vào early triage.
  - Consistency motif scoring là mandatory recognition criterion (CL-09).

- **Điểm phản đối**:
  - Rút bỏ Step 3 "human causal story" từ proposal gốc của tôi. Codex đúng: machine-verifiable phải chốt trước; causal story là explanatory layer sau evidence, giống semantic recovery của Gemini (`../codex/codex_debate_lan_1.md:147`).

- **Đề xuất sửa**:
  - Surprise criteria tối thiểu v1 (rút từ SDL, simplified):
    1. **Decorrelation outlier**: max |corr| với all cell-elite survivors < 0.3
    2. **Risk-profile outlier**: Sharpe < cell median BUT MDD < cell-best × 0.7
    3. **Plateau champion**: plateau width > 2× cell median
    4. **Consistency champion**: cross-timescale/cross-resolution win rate > threshold (từ CL-09)
  - Bỏ "regime specialist" và "behavioral anomaly" cho v1 (quá complex, threshold unclear).
  - Equivalence metric: **daily paired returns** trên common evaluation domain là practical nhất cho v1. Descriptor-bundle distance có thể bổ sung sau.

- **Evidence**: `./claude_propone.md:365-421`; `../chatgptpro/chatgptpro_debate_lan_1.md:237-263`; `../codex/codex_debate_lan_1.md:136-154`

- **Trạng thái**: PARTIAL → gần CONVERGED. Chốt vòng sau: surprise criteria thresholds cụ thể.

---

### OI-06 — Negative evidence / weak-signal memory

*Mapping: ChatGPT Pro OI-06 / Codex OI-05*

- **Stance**: AGREE

- **Điểm đồng ý**:
  - v1 nên có negative evidence tối thiểu ở descriptor-level shadow-only.
  - Không full EPC lifecycle cho v1 (tôi rút concession chính thức từ self-critique round 1).
  - ChatGPT Pro đúng: lưu descriptor/cell + failure mode + contradiction type + robustness weakness. Không lưu answer-level threshold, winner prior, parameter direction (`../chatgptpro/chatgptpro_debate_lan_1.md:276-286`).

- **Điểm phản đối**: Không còn tranh chấp thực chất.

- **Đề xuất sửa**:
  - Tên artifact: `contradiction_registry.json` (preferred over `negative_evidence_registry` — tránh nhầm "negative evidence" = evidence chống lại candidate, trong khi thực tế là "evidence about what failed and why").
  - Weak signal → "shadow note" local-to-campaign ở v1. Chỉ khi data mới thì mới có cơ hội promotion. Đúng MK-17 ceiling.
  - EPC lifecycle → DEFER v2 (sau khi có ≥2 campaigns để tích lũy evidence).

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_1.md:276-292`; `../codex/codex_debate_lan_1.md:189-200`; `../../../design_brief.md:84-89`

- **Trạng thái**: PARTIAL → gần CONVERGED. Chốt vòng sau: schema cụ thể.

---

### OI-07 — Cross-domain / domain-seed priority

*Mapping: ChatGPT Pro OI-07*

- **Stance**: AGREE

- **Điểm đồng ý**:
  - Cross-domain/domain-seed = optional input source, không phải core v1.
  - ChatGPT Pro đúng: trục thiếu nặng nhất không phải "thiếu cảm hứng" mà là thiếu lineage/coverage/archive/proof/gate inventory (`../chatgptpro/chatgptpro_debate_lan_1.md:309-310`).
  - CDAP → DEFER v2. Xây domain catalog trong v1 nếu muốn, nhưng không phải blocker.

- **Điểm phản đối**: Không còn.

- **Đề xuất sửa**:
  - Reserve hook trong lineage schema: field `domain_hint: Optional[str]` trong supplementary provenance. Zero cost, forward-compatible.
  - Hook nằm ở proposal provenance (supplementary), không ở operator grammar (canonical).

- **Evidence**: `../chatgptpro/chatgptpro_debate_lan_1.md:296-316`; `./claude_propone.md:210-268` (CDAP design — giữ làm v2 reference)

- **Trạng thái**: PARTIAL → gần CONVERGED. Chỉ cần xác nhận hook field.

---

### OI-08 — Descriptor taxonomy + equivalence metric ownership

*Mapping: ChatGPT Pro OI-08 / Codex OI-06 (breadth vs multiplicity coupling)*

- **Stance**: AGREE với amendment

- **Điểm đồng ý**:
  - Split: 006 = feature-level taxonomy, 017 = strategy phenotype descriptors, 008+013 = equivalence/distance metrics.
  - Codex đúng: breadth-expansion và multiplicity/identity control là coupled design — không tách rời (`../codex/codex_debate_lan_1.md:212-216`). v1 không nên freeze breadth mà bỏ trống correction/equivalence contract.
  - ChatGPT Pro đúng: equivalence nên có metric cụ thể, không chỉ khung.

- **Điểm phản đối**:
  - Câu hỏi "cell dimensions tối thiểu" chưa có ai trả lời cụ thể. Tôi đề xuất starter set.

- **Đề xuất sửa**:
  - **Cell dimensions tối thiểu v1** (đề xuất, cần debate):
    1. **mechanism**: trend / volatility / flow / structure / composite (5 values)
    2. **complexity**: primitive / compound / complex (3 values — maps to GFS depth 1/2/3)
    3. **turnover**: low / medium / high (3 values — estimated signal flip frequency)
    4. **timeframe_primary**: H4 / D1 / multi-TF (3 values)
    → 5 × 3 × 3 × 3 = **135 cells tối đa**. Nhiều cells sẽ trống → actual cells ~30-50. Quản lý được cho v1.
  - **Equivalence metric v1**: Pearson correlation trên daily paired returns (common evaluation domain). Threshold ≥ 0.85 = "same thing in disguise". Simple, auditable, compute-cheap.
  - **Scan-phase correction**: Holm step-down cho Stage 3→4 khi scan >1000 configs. Rationale: Holm strictly more powerful than Bonferroni, less assumptions than FDR. Evidence: đã dùng thành công trong btc-spot-dev research [extra-archive: VDO proof dùng Bonferroni/Holm/BH].

- **Evidence**: `../codex/codex_debate_lan_1.md:204-224`; `../chatgptpro/chatgptpro_debate_lan_1.md:320-342`; `../codex/codex_propone.md:183-191`

- **Trạng thái**: OPEN — cell dimensions và equivalence threshold cần debate cụ thể.

---

### NEW-01 — APE scope cho v1: template parameterization only, không code generation

*Lý do mở: OI-03 bàn minimum v1 scope, nhưng chưa agent nào chốt rõ APE nên ở dạng nào cho v1. Tôi đã self-critique issue này ở round 1 nhưng chưa ai respond.*

- **Vấn đề**: APE (Architecture Perturbation Engine) trong proposal gốc đề xuất "generate strategy.py code". Đây là rủi ro v1:
  - Code generation errors → smoke test pass nhưng logic sai → false negatives
  - Mỗi variant cần review code → scale không feasible
  - (`./claude_debate_lan_1.md:183-190`)

- **Đề xuất**:
  - v1 APE = **template parameterization only**: thay đổi config (lookback, threshold, cost), không thay đổi code. Ví dụ: VTREND E0 config với slow_period=[20,40,60,80,...,200] = 10 variants, zero code generation.
  - v2+ APE = code generation khi có proven template engine + automated test harness.
  - Lý do: VDO-type discoveries ở v1 nên đến từ GFS (new features) chứ không từ APE (strategy mutations). APE mutations (ENTRY_SWAP, EXIT_SWAP) đòi hỏi code generation quality mà v1 chưa có.

- **Evidence**: `./claude_debate_lan_1.md:183-190`; `./claude_propone.md:146-200`

- **Trạng thái**: OPEN

---

## 5. Interim Merge Direction (cập nhật)

### 5.1 Backbone v1 (updated)

Codex + ChatGPT Pro backbone + **GFS depth-1** + **bounded ideation lane**.

Pipeline:
```
[Bounded ideation lane] ─── proposal_spec.yaml ───┐
                                                    ├──► 006 registry compilation
[GFS depth-1 enumeration] ─ gfs_manifest.json ────┘
                                                    │
                            ┌───────────────────────┘
                            ▼
Protocol Lock ──► Stage 3 scan (deterministic, offline)
    ──► Stage 4 cell-elite archive + surprise slots
    ──► Stage 5-6 layered search + probes
    ──► Stage 7 freeze comparison set + proof bundles
    ──► Stage 8 holdout/reserve + epistemic_delta + contradiction_registry
```

### 5.2 Adopt ngay (updated — thêm items)

| # | Artifact / Mechanism | Nguồn | Owner đề xuất |
|---|---------------------|-------|---------------|
| 1 | `discovery_lineage.json` + `candidate_genealogy.json` | Codex | 015 + 006 |
| 2 | Descriptor taxonomy + `coverage_map` + `epistemic_delta.json` | ChatGPT Pro + ESP-01 | 017 |
| 3 | Cell-elite archive + surprise slots + local probes | Codex + ChatGPT Pro + ESP-01 | 017 + 003 |
| 4 | `surprise_queue` + `proof_bundle` + `frozen_comparison_set` | Codex + ChatGPT Pro | 017 + 015 + 003 |
| 5 | Equivalence/redundancy audit (daily paired returns) | Codex + ChatGPT Pro | 008 + 013 |
| 6 | v1 memory ceiling: OBSERVED/REPLICATED_SHADOW only | ChatGPT Pro + Codex + MK-17 | 017 + 004 + 002 |
| 7 | **GFS depth-1 grammar + enumeration engine** | Claude | **006** |
| 8 | **Bounded ideation lane contract** (4+1 hard rules) | ChatGPT Pro + Claude | **006 + 017** |
| 9 | **`contradiction_registry.json`** (descriptor-level shadow) | ChatGPT Pro + Codex | 017 |
| 10 | **SDL surprise criteria (4 simplified)** | Claude (adapted) | 017 |
| 11 | **Consistency motif scoring** | ChatGPT Pro | 017 |
| 12 | **Discovery gate inventory** (separated from certification) | ChatGPT Pro | 003 + 017 |

### 5.3 Defer (updated)

| # | Artifact / Mechanism | Nguồn | Lý do defer |
|---|---------------------|-------|-------------|
| 1 | Topic 018 umbrella | Claude | Rút — fold vào 006 + 017 cho v1 |
| 2 | SSS infrastructure | Claude | Rút — bounded ideation lane thay thế |
| 3 | CDAP / domain catalog | Claude + Gemini | v2 — không phải v1 blocker |
| 4 | EPC full lifecycle | Claude | v2 — cần ≥2 campaigns |
| 5 | GFS depth 2/3 | Claude | Chỉ khi depth-1 yield NO_ROBUST_IMPROVEMENT |
| 6 | APE code generation | Claude | v2 — v1 chỉ template parameterization |
| 7 | Activation ladder vượt REPLICATED_SHADOW | Codex + ESP-03 | v1 benefit ≈ 0 trên same dataset |
| 8 | Prompt ancestry tree làm canonical lineage | Gemini | Supplementary provenance only |
| 9 | Semantic recovery | Gemini | Post-evidence explanatory layer, không phải gating |

### 5.4 Ownership tạm (updated)

| Topic | Gánh gì |
|-------|---------|
| 006 | Feature-level taxonomy, operator grammar, **GFS depth-1 engine**, registry contract, bounded ideation compilation |
| 017 | Coverage obligations, cell-elite/archive law, surprise triage semantics, SDL criteria, consistency motif, contradiction_registry, budget governor, epistemic_delta, v1 memory ceiling |
| 015 | Lineage/artifact enumeration, discovery_lineage schema, invalidation rules khi taxonomy đổi |
| 013 | Descriptor-space convergence, equivalence metric (daily paired returns), diminishing-returns stop logic |
| 008 | Identity relations: family / architecture / phenotype / equivalence cluster |
| 003 | Stage integration, discovery gate inventory, wiring cell-elite + probes + freeze vào Stage 3-8 |

---

## 6. Agenda vòng sau

Chỉ bàn các OI còn OPEN hoặc PARTIAL:

| OI | Trạng thái | Câu hỏi cần chốt |
|----|-----------|-------------------|
| OI-01 | PARTIAL | Fold conditions testable? Mọi bên đồng ý? |
| OI-02 | PARTIAL | Bounded ideation lane output schema cụ thể? |
| OI-03 | **OPEN** | **GFS depth-1 bắt buộc hay optional cho v1?** (tranh chấp lớn nhất) |
| OI-04 | PARTIAL | Feature vs candidate sub-schema split |
| OI-05 | PARTIAL | Surprise criteria thresholds cụ thể |
| OI-06 | PARTIAL | contradiction_registry.json schema |
| OI-07 | PARTIAL | domain_hint hook field xác nhận |
| OI-08 | **OPEN** | Cell dimensions, equivalence threshold, scan-phase correction law |
| NEW-01 | **OPEN** | APE v1 = parameterization only? |

**Trọng tâm vòng 3**: OI-03 (GFS depth-1) và OI-08 (cell dimensions + equivalence + correction). Đây là 2 điểm có tranh chấp thực chất.

---

## 7. Change Log

| Vòng | Ngày | Agent | Tóm tắt thay đổi |
|------|------|-------|-------------------|
| 1 | 2026-03-25 | claude_code | Round mở đầu: phản biện 4 proposals, tự phản biện, nêu 5 debate points (D1-D5), bảng so sánh tổng hợp |
| 2 | 2026-03-26 | claude_code | **Concessions chính thức**: rút Topic 018 bundle, rút SSS, rút EPC v1, rút APE code-gen v1. **Giữ**: GFS depth-1 bắt buộc, bounded ideation lane. **Thêm**: CL-09 (consistency motif), CL-10 (Codex+ChatGPT Pro backbone), NEW-01 (APE scope). Unified OI numbering theo ChatGPT Pro. Respond 8 OIs + 1 NEW. |
