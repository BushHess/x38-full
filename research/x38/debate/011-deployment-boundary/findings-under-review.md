# Findings Under Review — Deployment Boundary & Research Contract

**Topic ID**: X38-T-11
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

4 findings về ranh giới x38 ↔ deployment layer và research output contract.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate
- C-06: Transition-law gap thật (liên quan F-16 → Topic 001)
- C-09: x38 đã có PENDING_CLEAN_OOS; thiếu general trigger router

---

## F-26: Monitoring → re-evaluation trigger interface

- **issue_id**: X38-D-26
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from optimization scope analysis)
- **current_status**: Open

**Nội dung**:

x38 mô tả "vòng lặp vô hạn" NV1 → NV2 → (FAIL) → NV1 lại (PLAN.md:76-77),
và auto-trigger `PENDING_CLEAN_OOS` khi winner + data mới đủ (F-12).

Nhưng vòng lặp thiếu MỘT trigger: **khi nào phát hiện algorithm đang
degradation trong production để khởi động re-evaluation?**

Hiện tại:
- `monitoring/regime_monitor.py` [extra-archive] tồn tại trong btc-spot-dev (status UNCERTAIN,
  WFO 2/8 instability)
- x38 không specify interface nào cho monitoring signal
- Human researcher phải tự quyết định khi nào re-evaluate → dễ bỏ sót hoặc
  trì hoãn

**Đề xuất**: x38 specify một **interface** (không implement) cho monitoring
→ re-evaluation trigger:

```
Monitoring layer (ngoài x38)
    ↓ signal: DEGRADATION_DETECTED
x38 framework
    ↓ tạo nghĩa vụ: PENDING_RE_EVALUATION
    ↓ human approve/defer (giống PENDING_CLEAN_OOS)
    ↓ re-run Clean OOS trên latest data, hoặc full re-discovery
```

Tương tự `PENDING_CLEAN_OOS`: framework tạo nghĩa vụ, human chọn thời điểm,
nhưng KHÔNG được im lặng trì hoãn vô hạn.

**x38 KHÔNG implement monitoring** — monitoring là deployment concern, nằm
ngoài scope (xem F-27). x38 chỉ specify: "nếu nhận signal X thì tạo nghĩa
vụ Y."

**Evidence**:
- PLAN.md:79-80: vòng lặp vô hạn NV1→NV2
- F-12: PENDING_CLEAN_OOS auto-trigger pattern (same pattern, different trigger)
- btc-spot-dev monitoring/regime_monitor.py [extra-archive]: precedent thực tế (RED khi 6m MDD
  > 55% hoặc 12m MDD > 70%)
- X22 (Cost Sensitivity): performance thay đổi lớn theo cost → monitoring
  cần track realized cost, không chỉ algorithm metrics

**Câu hỏi mở**:
- Signal format: single boolean (DEGRADATION_DETECTED) hay structured
  (degradation_type, severity, confidence)?
- Threshold: x38 pre-register degradation thresholds hay để monitoring
  layer tự quyết?
- Re-evaluation scope: luôn full re-discovery hay triage (parameter-only
  recalibration nếu degradation nhẹ)?

---

## F-27: Deployment layer scope boundary

- **issue_id**: X38-D-27
- **classification**: Judgment call
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from optimization scope analysis)
- **current_status**: Open

**Nội dung**:

x38 scope là **algorithm research**: discovery → freeze → clean OOS.

Sau khi algorithm được CONFIRMED, còn nhiều quyết định ảnh hưởng lớn đến
performance nhưng KHÔNG thay đổi algorithm logic:

| Operational lever | Impact | Thuộc x38? |
|---|---|---|
| Position sizing (f) | Trực tiếp quyết định CAGR/MDD tradeoff | **Không** |
| Cost optimization (exchange, fee tier) | +0.4 Sharpe (X22: 50bps → 15bps) | **Không** |
| Trail parameter profile (risk appetite) | Monotonic return/risk tradeoff | **Không** |
| Execution strategy (market/limit) | Ảnh hưởng realized cost | **Không** |
| Monitoring + alerting | Phát hiện degradation | **Không** (chỉ interface, xem F-26) |

**Tại sao cần ghi rõ scope boundary**: Nếu không, x38 dễ bị scope creep —
thêm position sizing, thêm execution, thêm monitoring — và trở thành
"everything framework" thay vì "algorithm research framework." Mỗi mở rộng
thêm complexity, thêm debate topics, thêm thời gian build.

**Đề xuất**: x38 blueprint ghi rõ:

> x38 output là frozen algorithm spec + certification verdict.
> Operational optimization (sizing, cost, execution) và continuous
> monitoring là deployment concerns — thiết kế riêng, ngoài x38 scope.
> x38 chỉ specify interface cho monitoring trigger (F-26).

**Evidence**:
- Cost sensitivity study [extra-archive]: cost optimization impact lớn hơn hầu hết
  algorithm improvements — operational lever, không phải research output
- Trail sweep study [extra-archive]: trail parameter changes là operational choice,
  không phải algorithm discovery
- Position sizing [extra-archive]: vol-target sizing chưa optimize riêng —
  deployment concern
- PLAN.md:86-90: x38 scope nói "không chỉ BTC" nhưng không nói về deployment

**Câu hỏi mở**:
- Deployment layer nên là project riêng hay module trong alpha-lab?
- x38 frozen spec có nên include recommended operational ranges (ví dụ:
  "trail ∈ [2.5, 4.5], f ∈ [0.20, 0.40]") hay chỉ frozen defaults?
- Nếu deployment layer tìm ra operational setting tốt hơn, đó có phải
  feedback cho x38 (ví dụ: "cost < 30 bps → skip churn filter")?

---

## F-28: Unit-exposure canonicalization — tách sizing khỏi research object

- **issue_id**: X38-D-28
- **classification**: Judgment call
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from pre-debate review convergence)
- **current_status**: Open
- **source**: Pre-debate review convergence P-01

**Nội dung**:

Đề xuất: x38-core đánh giá **unit-exposure return stream** cho long/flat signal
logic, đẩy capital fraction và bankroll utility ra deployment layer.

Hiện tại, research object bao gồm cả sizing (pre-existing candidate spec [extra-archive] bao gồm sizing parameter).
Nếu canonicalize research object thành unit-exposure:
- Signal edge và entry/exit schedule = **đối tượng khoa học** (algorithm core)
- Capital fraction và bankroll utility = **deployment choice** (ngoài x38)

**Tại sao cần**: Giải quyết tension giữa F-17 và F-27:
- F-17 xếp position sizing change vào semantic changes cần version mới
- F-27 đẩy position sizing ra deployment layer
- Nếu research object là unit-exposure (không bao gồm sizing), mâu thuẫn biến
  mất: sizing change = deploy_version change, KHÔNG invalidate research results

**Điều kiện**: Chỉ khi sizing KHÔNG phải logic nội sinh của chiến lược. Nếu
sizing là phần nội sinh (ví dụ: conviction sizing, kelly-optimal integrated
into signal logic), sizing phải ở lại algorithm core.

**Evidence**:
- F-17 (X38-D-17): position sizing change = semantic change
- F-27 (X38-D-27): position sizing = deployment concern
- Tension giữa F-17 và F-27 chưa có resolution trong archive
- Pre-existing candidate sizing [extra-archive] hiện nằm trong algorithm spec
  (btc-spot-dev [extra-archive], không thuộc x38 authority)

**Câu hỏi mở**:
- Chiến lược có sizing nội sinh (conviction sizing, volatility targeting
  tích hợp trong logic) → canonicalize ra unit exposure có mất tính toàn vẹn?
- Unit-exposure return stream nên được define thế nào? (fully invested khi
  có signal, 0 khi không?)
- F-17 nên sửa thành: "position sizing change cần version mới CHỈ KHI sizing
  là logic nội sinh"?

---

## F-29: Research contract — algo_version / deploy_version split

- **issue_id**: X38-D-29
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, from pre-debate review convergence)
- **current_status**: Open
- **source**: Pre-debate review convergence P-02
- **related**: F-17 (semantic change), F-27 (deployment boundary), F-28
  (unit-exposure)

**Nội dung**:

Đề xuất formalize hai lớp version identity cho x38 output:

```
algo_version =
    logic_hash
  + parameter_manifold_id
  + execution_semantics_id
  + cost_envelope_id
  + engine_version

deploy_version =
    sizing_policy_id
  + venue_id
  + order_tactic_id
  + portfolio_overlay_id
```

**Quy tắc**:
- Đổi logic/filter/entry/exit → algo_version mới
- Đổi threshold/lookback/trail thuộc logic → algo_version mới
- Đổi execution semantics (market ↔ limit, fill model) → algo_version mới
- Đổi cost model vượt envelope → algo_version mới
- Đổi sizing policy → deploy_version mới (nếu sizing đã canonicalize ra
  unit-exposure theo F-28)
- Chọn fee tier/venue trong envelope đã test → deploy_version mới, không
  cần đổi algo
- Ra ngoài envelope → quay lại x38 maintenance / revalidation

**Tại sao cần**: F-17 phân loại semantic changes nhưng chưa formalize thành
version identity. F-27 đề xuất deployment boundary nhưng chưa có contract.
F-29 nối hai finding thành interface design rõ ràng.

**Evidence**:
- F-17 (X38-D-17): classification table (CẦN version mới vs KHÔNG CẦN)
- F-27 (X38-D-27): deployment levers chưa có boundary contract
- X22 cost sensitivity [extra-archive] cho thấy cost optimization impact
  lớn hơn hầu hết algorithm improvements (btc-spot-dev [extra-archive], không thuộc x38
  authority)

**Câu hỏi mở**:
- `parameter_manifold_id` chưa có spec — Stage 6 plateau output cần define
  manifold format trước khi field này có nghĩa
- `execution_semantics_id` bao gồm gì chính xác? (fill model, slippage
  model, order type?)
- `cost_envelope_id`: envelope = range [min, max] bps? Hay phức tạp hơn
  (fee schedule, maker/taker split)?
- Phụ thuộc F-28: nếu sizing chưa canonicalize ra unit-exposure, sizing
  nằm trong algo_version hay deploy_version?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 010 | F-12 | Clean OOS certification output is input for deployment — but F-27 scope boundary says deployment is outside x38, creating ambiguity about who owns the handoff contract | 010 owns certification verdict; 011 owns the boundary definition |
| 015 | F-17 | F-17 classifies position sizing change as semantic change needing new version, but F-27/F-28 push sizing to deployment layer — contradictory if sizing is in algo_version | shared — F-28 (unit-exposure) resolves; 011 owns boundary, 015 owns classification |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-26 | Monitoring → re-evaluation trigger interface | Thiếu sót | Open |
| X38-D-27 | Deployment layer scope boundary | Judgment call | Open |
| X38-D-28 | Unit-exposure canonicalization | Judgment call | Open |
| X38-D-29 | Research contract — algo/deploy version split | Thiếu sót | Open |
