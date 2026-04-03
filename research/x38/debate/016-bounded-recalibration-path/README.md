# Topic 016 — Bounded Recalibration Path

**Topic ID**: X38-T-16
**Opened**: 2026-03-23
**Status**: OPEN (backlog — activate after Wave 2 prerequisites close)
**Origin**: Orphaned cross-cutting question identified via C-04 + C-12 convergence
notes. No existing topic owns this decision despite touching 5+ topics.

## Architectural decision

x38 có cho phép bounded recalibration path không? Nếu có, exception boundary
và contract với firewall / campaign / Clean OOS / versioning là gì?

## Scope

Quyết định duy nhất: liệu x38 framework có nên cung cấp một đường dẫn cho phép
**recalibrate parameters** (không thay đổi algorithm logic) sau khi monitoring phát
hiện degradation — hay buộc full re-discovery cho MỌI loại degradation.

Nếu cho phép, topic này phải define:
- **Exception boundary**: chính xác loại thay đổi nào được phép (parameter-only?
  threshold-only?) và loại nào KHÔNG bao giờ được phép (logic, filter, entry/exit)
- **Firewall contract**: bounded recalibration tương tác với contamination firewall
  thế nào — exception nào cần, burden of proof thuộc ai
- **Campaign integration**: recalibration là session mới trong campaign hiện tại,
  campaign mới, hay mechanism riêng ngoài campaign model?
- **Clean OOS impact**: recalibrated algorithm cần clean OOS mới hay kế thừa
  certification cũ? Nếu kế thừa, điều kiện gì?
- **Versioning**: recalibration tạo algo_version mới hay deploy_version mới?
  (F-17 / F-29 interaction)

Scope KHÔNG bao gồm:
- Full re-discovery (đã covered bởi Topic 001 campaign model)
- Deployment-layer operational tuning (đã covered bởi Topic 011 F-27)
- Monitoring signal design (đã covered bởi Topic 011 F-26)

## Evidence base

**Convergence notes** (shared reference tại `000-framework-proposal/`):
- **C-04**: x38 hiện KHÔNG có bounded recalibration path. Nếu muốn = design
  change mới.
- **C-12**: Bounded recalibration **prima facie bất tương thích** với current
  firewall. Answer priors (winner, params, family) bị cấm LUÔN; methodology
  priors (Tier 2) = shadow same-data, activate new-data. Muốn giữ → argue
  exception, burden thuộc proposer.
- **C-01**: MK-17 ≠ primary evidence chống bounded recalibration. Trụ chính =
  contamination firewall.
- **C-10**: F-01 cần operationalize qua firewall, không standalone.

**Cross-topic references** (câu hỏi mở đang rải ở các topics khác):
- Topic 011 F-26 (line 73): *"Re-evaluation scope: luôn full re-discovery hay
  triage (parameter-only recalibration nếu degradation nhẹ)?"*
- Topic 001 F-16: Campaign transition guardrails — khi nào mở campaign mới?
  Recalibration có phải trigger hợp lệ?
- Topic 010 F-24: Clean OOS power rules — recalibrated algorithm cần re-certify?
- Topic 015 F-17: Semantic change classification — parameter change = version mới?
- Topic 002 F-04: Firewall typed schema + whitelist — recalibration exception
  cần gì để pass?

**Precedent pattern**: F-17 ↔ F-27 tension → F-28 + F-29 (interface findings).
Topic 016 follows cùng pattern: biến xung đột giữa kỹ thuật thành quyết định
interface rõ ràng, không tranh luận mơ hồ về "compatibility".

**Findings**:
- F-34: Bounded recalibration — exception boundary & firewall contract
- F-35: Recalibration integration — campaign model & Clean OOS interaction

## Dependencies

- **Hard upstream** (phải close trước khi 016 debate):
  - Topic 001 (campaign model) — cần biết campaign structure
  - Topic 002 (contamination firewall) — cần biết firewall rules
  - Topic 010 (Clean OOS) — cần biết certification protocol
  - Topic 011 (deployment boundary) — cần biết scope boundary + F-26 trigger
  - Topic 015 (artifact/versioning) — cần biết semantic change rules + version split
- **Hard downstream** (016 phải close trước):
  - Topic 003 (protocol engine) — pipeline cần biết có recalibration branch không

## Wave assignment

**Wave 2.5**: Chạy sau khi hard upstream (001, 002, 010, 011, 015) close,
trước khi Topic 003 (protocol engine) finalize. Nếu 016 close SAU 003, protocol
có thể phải reopen — tốn thêm rounds không cần thiết.

## Pre-debate burden of proof framework

**Purpose**: Topic 016 is the most burden-heavy topic — proposer must argue
an exception to the firewall (C-12: prima facie incompatible). This framework
ensures debate starts with CLEAR evidence obligations, not open-ended discussion.

### Decision tree (strict ordering)

```
Step 1: BINARY — Allow bounded recalibration? (F-34)
  ├── NO → Topic CLOSES. Status quo: all degradation → full re-discovery.
  │         Outcome: F-34=CONTRA, F-35=MOOT.
  └── YES → Step 2 (ONLY if Step 1 = YES)
               ↓
Step 2: Exception boundary — what exactly is allowed? (F-34)
  - Tầng 2 boundary: parameter-only within declared manifold
  - Scope lock: which parameters? All or subset?
  - Firewall contract: formal exception definition
               ↓
Step 3: Integration model — how? (F-35)
  - Phương án A (session in current campaign) / B (maintenance campaign) / C (separate pipeline)
  - Clean OOS re-certification policy
```

**Debaters MUST establish Step 1 (YES/NO) BEFORE finalizing Steps 2/3.** However,
debaters MAY discuss Step 2/3 scenarios in Step 1 arguments if conditional (e.g.,
"YES, provided Step 2 = Phương án C"). This preserves Step 1 priority while
allowing full-context reasoning. If Step 1 = NO, Steps 2 and 3 are not debated.

### Burden allocation

**Proposer (PRO recalibration) MUST provide**:

1. **Firewall exception justification**: How does Tầng 2 recalibration NOT
   violate C-12 (answer priors banned ALWAYS)? The fact that recalibrated
   params are "within manifold" does not automatically exempt them from the
   firewall. Proposer must argue why parameter reuse from same algorithm is
   categorically different from answer priors.

2. **Slippery slope defense**: Concrete, enforceable mechanism that prevents
   Tầng 2 exception from expanding to Tầng 3 (logic changes). "We'll be
   disciplined" is not sufficient — must be structural enforcement.

3. **Cost-benefit analysis**: Quantify the cost of full re-discovery (compute,
   time) vs the risk of firewall exception (contamination, precedent).
   Use evidence from project: Gen3 V1 cost (4 structural gaps, FAILED),
   Gen4 expected cost.

4. **Real-world scenario**: At least one concrete scenario where recalibration
   is clearly superior to full re-discovery. Must include specific degradation
   metric, specific parameter change, and demonstration that full re-discovery
   would likely arrive at the same answer at much higher cost.

**Defender (CONTRA, status quo) has**:

- C-12 (answer priors banned ALWAYS) — prima facie case
- C-04 (no path exists) — design intent
- F-17 (parameter change = semantic change = new version) — versioning argument
- F-04 (firewall typed schema + whitelist) — enforcement mechanism
- rules.md §5: burden on proposer of change

**Burden evaluation**: Proposer must establish preponderance of evidence across
the 4 dimensions. If proposer presents strong cases on 3/4 AND can steel-man the
4th, the decision is Judgment call per rules.md §14 — not automatic NO. If
proposer fails on 2+ requirements, Step 1 = NO by default.

**NOTE**: F-34 is classified as "Judgment call" (cả hai phía có lý). The 4
requirements structure the debate, not pre-decide the outcome. rules.md §5
(burden on proposer of change) is operationalized here, but §5 specifies burden
allocation, not numerical unanimity. Topic 011 F-26 also questions whether "no
triage path" is itself a design gap — proposer may cite this as upstream evidence.

### Round budget

- Round 1: F-34 binary decision (Step 1). Proposer presents case, defender responds.
- Round 2: If Step 1 = YES → exception boundary (Step 2). If NO → closure.
- Round 3 (if needed): Integration model (Step 3) + Clean OOS interaction.

## Debate plan

- Ước lượng: 1-3 rounds (depends on Step 1 outcome — may close in 1 round)
- Key battles:
  - F-34: Có cho phép bounded recalibration hay không? (binary decision trước)
    Nếu có: exception boundary chính xác là gì? Firewall contract ra sao?
  - F-35: Recalibration tạo session/campaign mới hay mechanism riêng? Clean OOS
    re-certification policy?
- Burden of proof: thuộc bên ĐỀ XUẤT recalibration (per C-12: current design
  = no path, proposer must argue exception)

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 002 | F-04 | Firewall blocks answer priors (winner, params, family) ALWAYS — recalibration = params change = blocked | F-34 must argue exception or accept no-path |
| 001 | F-16 | Campaign transition guardrails may or may not include "mild degradation" as trigger | F-35 defines whether recalibration is campaign or sub-campaign |
| 010 | F-24 | Clean OOS power rules assume frozen algorithm — recalibration breaks "frozen" assumption | F-35 defines re-certification policy |
| 011 | F-26 | Monitoring trigger scope ambiguous — "full re-discovery or triage?" | 016 resolves the "triage" branch |
| 015 | F-17 | Parameter change = semantic change = new version — but recalibration is "same algorithm, different params" | F-34 must reconcile with F-29 algo_version definition |
| 013 | F-31 | Stop conditions: adding session after convergence may violate campaign stop rules | F-35 Phương án A interaction |

## Files

| File | Purpose |
|------|---------|
| `findings-under-review.md` | 2 findings: F-34, F-35 |
| `claude_code/` | Critique from Claude Code |
| `codex/` | Critique from Codex |
