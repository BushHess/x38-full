# Findings Under Review — Bounded Recalibration Path

**Topic ID**: X38-T-16
**Opened**: 2026-03-23
**Author**: claude_code (architect)

2 findings về bounded recalibration path — exception boundary, firewall contract,
và integration với campaign model / Clean OOS.

**Issue ID prefix**: `X38-BR-` (Bounded Recalibration).

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-01: MK-17 ≠ primary evidence chống bounded recalibration. Trụ chính = firewall.
- C-04: x38 hiện KHÔNG có bounded recalibration path. Nếu muốn = design change mới.
- C-10: F-01 cần operationalize qua firewall, không standalone.
- C-12: Bounded recalibration prima facie bất tương thích với current firewall.
  Answer priors LUÔN bị cấm. Muốn giữ → argue exception, burden thuộc proposer.

---

## F-34: Bounded recalibration — exception boundary & firewall contract

- **issue_id**: X38-BR-01
- **classification**: Judgment call
- **opened_at**: 2026-03-23
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

x38 hiện tại có một chính sách ngầm: mọi degradation → full re-discovery
(campaign mới, F-03). Không có đường dẫn trung gian cho phép chỉ recalibrate
parameters mà không mở research cycle mới.

Câu hỏi nhị phân đầu tiên: **x38 có nên cung cấp bounded recalibration path
hay không?**

**Argument PRO (bounded recalibration)**:

1. **Proportionality**: Nếu degradation chỉ do drift nhẹ (e.g., optimal trail
   dịch nhẹ), full re-discovery (N sessions × M configs) là
   disproportionate. Cost: weeks of compute + new campaign overhead.
2. **Operational reality**: research/results/trail_sweep/trail_sweep.json [extra-archive]
   (full parameter range, monotonic tradeoff) — recalibrate trail là
   operational choice, không phải algorithm redesign.
3. **Practical precedent**: F-27 (deployment boundary) đã đề xuất tách
   operational levers (sizing, trail profile, cost) ra khỏi x38 scope.
   Recalibration cho deployment-layer parameters ≠ recalibration cho
   algorithm logic.

**Argument CONTRA (no recalibration — status quo)**:

1. **Firewall integrity** (C-12): Bounded recalibration = sử dụng answer priors
   (params từ algorithm đã chạy) để giới hạn search space. Firewall cấm answer
   priors ALWAYS. Bất kỳ exception nào đều tạo precedent cho future leakage.
2. **Slippery slope**: "Chỉ trail thôi" → "trail + VDO threshold" → "trail +
   VDO + slow_period" → de facto re-optimization trên same data.
3. **Clean OOS contamination**: Nếu recalibrate dựa trên post-deployment data,
   nhưng Clean OOS reserve chưa mở → recalibrated params chưa được certified.
   Nếu dùng Clean OOS reserve cho recalibration → reserve bị tiêu tốn.
4. **F-17 classification**: Parameter change = semantic change = system_version
   mới. Recalibrated algorithm ≠ original algorithm. Mọi prior results invalid.

**Sub-question nếu PRO wins**: Exception boundary chính xác là gì?

Đề xuất phân loại 3 tầng:

| Tầng | Loại thay đổi | Recalibration? | Lý do |
|------|---------------|----------------|-------|
| 1 | deploy_version only (sizing, venue, order tactic) | **Không cần x38** — deployment layer tự quyết (F-27, F-29) | Không chạm algorithm logic |
| 2 | Parameter within declared manifold (e.g., trail ∈ [2.0, 5.0]) | **Bounded recalibration** (nếu cho phép) | Cùng algorithm, cùng manifold, khác điểm |
| 3 | Logic / filter / entry / exit / feature | **Full re-discovery** (campaign mới) | Algorithm identity thay đổi |

**Firewall contract nếu Tầng 2 cho phép**:

Firewall cần formal exception:
- **Scope lock**: Chỉ parameters TRONG parameter_manifold_id đã declared
  khi algorithm freeze. Không mở rộng manifold.
- **Method lock**: Recalibration dùng CÙNG objective function, CÙNG cost
  scenario, CÙNG gating. Không thay đổi methodology.
- **Evidence requirement**: Proposer phải show (a) degradation metric đủ
  lớn, (b) new data available (not same-data refit), (c) recalibrated params
  vẫn trong declared range.
- **Version impact**: Recalibration tạo algo_version mới (F-17 applies).
  KHÔNG kế thừa certification cũ — phải qua certification mới (câu hỏi:
  full Clean OOS hay lightweight?).

**Evidence**:
- C-04, C-12: No path exists, prima facie incompatible with firewall
- C-01, C-10: Firewall is primary defense, not MK-17
- F-04 (Topic 002): Typed schema + whitelist — current enforcement mechanism
- F-27 (Topic 011): Deployment boundary — operational levers outside x38
- F-29 (Topic 011): algo_version / deploy_version split
- research/results/trail_sweep/trail_sweep.json [extra-archive]: full parameter range monotonic tradeoff,
  default balanced — trail change is operational, not structural
- research/x22/REPORT.md [extra-archive]: Performance shifts with cost regime,
  cost optimization is deployment concern

**Câu hỏi mở**:
- Binary: cho phép bounded recalibration hay không?
- Nếu cho phép: Tầng 2 boundary đủ chặt chưa? Parameter manifold quá rộng?
- Scope lock: Có nên giới hạn recalibration cho một subset parameters
  (e.g., chỉ trail, không slow_period)?
- New data requirement: bao nhiêu new data đủ cho recalibration?
  (Tương tự Clean OOS power rules F-24)
- Precedent risk: exception cho Tầng 2 có tạo pressure mở rộng sang Tầng 3?

---

## F-35: Recalibration integration — campaign model & Clean OOS interaction

- **issue_id**: X38-BR-02
- **classification**: Thiếu sót
- **opened_at**: 2026-03-23
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

NẾU F-34 kết luận cho phép bounded recalibration (Tầng 2), cần define cách
nó integrate vào campaign model (F-03) và Clean OOS protocol (F-12).

**3 phương án integration**:

**Phương án A: Recalibration = session mới trong campaign hiện tại**

```
Campaign C1:
  Session S1 → winner W1 (params: trail=3.0)
  Session S2 → winner W2 (params: trail=3.0)
  [convergence → Clean OOS → CONFIRMED]
  [deployment → monitoring → degradation signal]
  Session S_recal → winner W1' (params: trail=3.5)  ← recalibration session
  [lightweight certification → re-CONFIRMED?]
```

- Pro: Minimal overhead, reuse existing campaign machinery
- Con: Campaign đã "converged" — thêm session sau convergence vi phạm stop
  conditions (F-31). Contamination risk: S_recal biết W1 → answer prior.

**Phương án B: Recalibration = campaign mới (maintenance campaign)**

```
Campaign C1: [discovery] → winner W1 → CONFIRMED
Campaign C_maint: [bounded scope]
  Input: W1 + parameter manifold + new data
  Session S1 → W1' (recalibrated within manifold)
  [certification → re-CONFIRMED?]
```

- Pro: Clean separation. C_maint has own contamination boundary.
- Con: Full campaign overhead cho thay đổi nhỏ. Overkill nếu chỉ 1 param.

**Phương án C: Recalibration = mechanism riêng, ngoài campaign model**

```
Discovery pipeline: Campaign → CONFIRMED → deploy
Maintenance pipeline: Monitoring → recalibration protocol → re-certify
  (parallel track, different rules, shared firewall)
```

- Pro: Tách rõ discovery vs maintenance. Maintenance rules có thể đơn giản hơn.
- Con: Hai pipeline = hai bộ rules = hai lần debate + implement. Complexity.

**Clean OOS interaction (critical)**:

Bất kể phương án nào, Clean OOS reserve tuân theo Reserve Rollover Invariant
(Topic 010 D-21: attempt N+1 starts strictly after attempt N's `reserve_end_*`;
INCONCLUSIVE triggers new reserve window on strictly new data). Options:

1. **New reserve**: Chờ thêm data accumulate → mở reserve mới cho recalibration.
   Nhưng bao lâu? Power rules (F-24) apply.
2. **Lightweight certification**: Không cần full Clean OOS. Chỉ cần show
   recalibrated params vẫn trong original confidence region (bootstrap CI).
   Nhưng đây có phải "cheap talk"?
3. **No re-certification**: Recalibration trong declared manifold = deployment
   choice (Tầng 1 equivalent). Không cần x38 re-certify.
   Nhưng F-17 nói parameter change = semantic change = version mới.

**Evidence**:
- F-03 (Topic 001): Campaign → Session model
- F-12 (Topic 010): Clean OOS protocol — Reserve Rollover Invariant (D-21: sequential windows, not single-use)
- F-24 (Topic 010): Clean OOS power rules — pre-registered thresholds
- F-16 (Topic 001): Campaign transition guardrails — 5 gen4 guardrails
- F-31 (Topic 013): Stop conditions — adding session after convergence = violation?
- F-17 (Topic 015): Parameter change = semantic change = version mới
- F-29 (Topic 011): algo_version / deploy_version split

**Câu hỏi mở**:
- Phương án A, B, hay C? Hay hybrid?
- Clean OOS re-certification: new reserve, lightweight, hay none?
- Nếu lightweight: metric nào đủ? Bootstrap CI contain original? OOS Sharpe
  within ε of original?
- F-31 stop conditions: recalibration session có violate campaign convergence?
- Nếu Phương án B: maintenance campaign có cần N sessions hay 1 đủ?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | Firewall blocks answer priors (winner, params, family) ALWAYS — recalibration = params change = blocked | F-34 must argue exception or accept no-path |
| 001 | F-16 | Campaign transition guardrails may or may not include "mild degradation" as trigger | F-35 defines whether recalibration is campaign or sub-campaign |
| 010 | F-24 | Clean OOS power rules assume frozen algorithm — recalibration breaks "frozen" assumption | F-35 defines re-certification policy |
| 011 | F-26 | Monitoring trigger scope ambiguous — "full re-discovery or triage?" | within this topic (016 resolves the "triage" branch) |
| 015 | F-17 | Parameter change = semantic change = new version — but recalibration is "same algorithm, different params" | F-34 must reconcile with F-29 algo_version definition |
| 013 | F-31 | Stop conditions: adding session after convergence may violate campaign stop rules | F-35 Phương án A interaction |
| 017A | ESP-04 | If ESP manages search budget, interaction with bounded recalibration: ESP MUST NOT suggest parameter directions (answer-level influence). ESP treats recalibrated algo as new phenotype entry. | Explicit scope exclusion in 017A. 016 and 017A/017B do not depend on each other. |

---

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-BR-01 | Bounded recalibration — exception boundary & firewall contract | Judgment call | Open |
| X38-BR-02 | Recalibration integration — campaign model & Clean OOS interaction | Thiếu sót | Open |
