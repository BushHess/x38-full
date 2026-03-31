# Findings Under Review — Quality Assurance & Implementation Evidence

**Topic ID**: X38-T-12
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

2 findings (1 demoted) + 1 new finding về quality assurance.
F-19 demoted to supporting evidence (2026-03-31 gap audit).

---

## F-18: Continuous verification — module-level review gates

- **issue_id**: X38-D-18
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, human researcher input)
- **current_status**: Open

**Nội dung**:

Thiết kế hiện tại có stage gating cho **research protocol** (F-05: 8 stages, phase
gating, freeze checkpoint) và immutability cho **session artifacts** (F-11). Nhưng
chưa address: khi **framework code** được viết, làm sao đảm bảo mỗi module đạt
độ chính xác cao trước khi module phụ thuộc bắt đầu?

Đây không phải quy trình team — đây là **constraint kiến trúc**. Lý do:

1. **Cascading invalidation**: F-17 chứng minh code change ở tầng thấp (engine,
   data alignment, cost model) invalidate toàn bộ sessions phía trên. Bug trong
   module nền tảng phát hiện muộn → chi phí re-work nhân bản theo số module
   phụ thuộc.

2. **Thực tế btc-spot-dev** [extra-archive]: D1→H4 MTF mapping bug (`<=` → `<`) phát hiện muộn
   → re-run 195 scripts. Nếu bug được phát hiện tại module engine trước khi
   strategies và validation được viết, chi phí = 0.

3. **Module dependency graph có thứ tự tự nhiên**: types → data → engine → cost →
   metrics → audit → features → protocol → firewall → meta. Mỗi tầng phụ thuộc
   tầng dưới. Review gate giữa các tầng ngăn bug lan truyền lên.

**Đề xuất**: Alpha-Lab implementation phải enforce quy trình writer + reviewer
theo từng module:

- **Writer** (Claude Code): viết implementation code cho module
- **Reviewer** (Codex): review correctness, type safety, edge cases, test coverage
- **Gate**: module chỉ được đánh dấu VERIFIED khi reviewer xác nhận. Module phụ
  thuộc chỉ bắt đầu khi dependencies đã VERIFIED.
- **Scope**: review theo module (không batch toàn bộ cuối cùng), mỗi module đủ
  nhỏ để review có chất lượng.

```
Module dependency (implementation order):
  types ──→ data ──→ engine ──→ cost ──→ metrics ──→ audit
                                                       ↓
  features ←─────────────────────────────────────── registry
                                                       ↓
  protocol_engine ──→ firewall ──→ meta_updater ──→ CLI/orchestrator
```

Mỗi mũi tên = review gate. Module bên phải chỉ bắt đầu khi module bên trái
đã qua VERIFIED.

**Tương tự với F-05**: F-05 nói research stages có gating (Stage N+1 blocked
cho đến khi Stage N hoàn tất). F-18 áp dụng cùng nguyên tắc cho implementation:
Module N+1 blocked cho đến khi Module N đã VERIFIED.

**Evidence**:
- x38 F-05: stage gating trong research protocol — cùng nguyên tắc, domain khác
- x38 F-17: semantic change classification — chứng minh code changes cascade
- btc-spot-dev MEMORY.md [extra-archive]: D1→H4 fix invalidated 195 scripts (chi phí bug muộn)
- Boehm (1981): cost of defect removal increases 10-100x from design → deployment
- x38 F-07: core engine rebuild — HOW to build cần quality constraint, không chỉ
  WHAT to build

**Câu hỏi mở**:
- Review gate nên là formal (checklist + sign-off) hay lightweight (reviewer
  approve/reject)?
- Test coverage threshold nào cho mỗi module? (100% line coverage cho core
  types/engine? Lower cho CLI?)
- Khi reviewer phát hiện bug ở module đã VERIFIED: rollback dependent modules
  hay hotfix tại chỗ?
- Module granularity: 10 modules như trên hay coarser (5 tầng)?
- Review artifacts lưu ở đâu? (Trong alpha-lab repo hay tách riêng?)

---

## F-19: Online framework evolution — gen2→gen3→gen4 failure modes

> **DEMOTED TO SUPPORTING EVIDENCE** (2026-03-31, gap audit): F-19 is a historical
> evidence inventory — it has no design question, no stated alternatives, and no
> decision to make. The evidence it contains is valuable input for Topics 003, 005,
> and 007, but it does not itself require a debate resolution. Retained as reference
> material. Does NOT count toward Topic 012's active finding tally.

- **issue_id**: X38-D-19
- **classification**: ~~Thiếu sót~~ Supporting Evidence (demoted — not a finding)
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate)
- **current_status**: Demoted

**Bối cảnh quan trọng — Online vs Offline**:

Gen1 (V1-V8), gen2, gen3, gen4 đều là framework **online** — chạy trong AI chat
session, AI thực hiện phân tích/code/đo lường theo protocol, kết quả non-deterministic.
Alpha-Lab (x38 đang thiết kế) là framework **offline** — deterministic code pipeline,
không có AI conversation trong execution, machine-enforced governance.

Hai paradigm chia sẻ **cùng vấn đề** (contamination, divergence, constitution gaps)
nhưng cần **giải pháp khác nhau**. Gen2/gen3/gen4 là evidence về VẤN ĐỀ gì xảy ra,
KHÔNG phải template cho giải pháp offline. Xem `docs/online_vs_offline.md` cho
bảng phân biệt đầy đủ.

**Nội dung**:

**Gen2**: THẤT BẠI vì constitution chỉ cho phép xây
dựng chiến lược bằng Technical Analysis (TA indicators) — không cho phép phân tích
toán học từ gốc dữ liệu (math-from-data).
→ Gen3 ra đời: mở search space cho math-from-data thay vì TA-only.

**Gen3**: Sửa gen2 nhưng THẤT BẠI giữa chừng do hiến pháp có lỗi cấu trúc.
4 structural gaps: zero-trade trap, MDD cap quá chặt, sub-hourly slot waste,
no ablation revision.
→ Gen4 ra đời: chạy G0+G1 trong gen3 để sửa hiến pháp (18 fixes).

**Gen4**: Sửa gen3 qua governance review (G0→G1).
Gen4 V1 status: đang trong quá trình seed discovery (online).

**Relevance cho x38 — evidence về vấn đề, KHÔNG phải template cho giải pháp**:

| x38 Topic | Evidence từ gen3/gen4 (online) | Alpha-Lab phải giải quyết khác (offline) |
|-----------|-------------------------------|------------------------------------------|
| F-01 (triết lý) | NO_ROBUST_CANDIDATE là verdict thực tế | Cùng triết lý, khác enforcement (code vs prompt) |
| F-03 (campaign) | Gen3 chỉ có 1 session, không campaign | Offline: N independent deterministic sessions + statistical convergence |
| F-04 (firewall) | `contamination_map.md` ghi nhận leakage | Offline: filesystem chmod + data snapshot copy (machine-enforced) |
| F-05 (protocol) | D1a→D1f3 pipeline = AI-interpreted stages | Offline: deterministic code pipeline, stage gating bằng filesystem |
| F-07 (engine) | AI chat thực hiện backtest inline | Offline: standalone engine, reproducible (same input = same output) |
| F-16 (transition) | Redesign guardrails = prompt-based rules | Offline: campaign isolation by construction, meta-updater code |
| Topic 004 (MK) | `meta_knowledge_registry.json` = AI-maintained | Offline: machine-validated, regex-checked MK storage |

**Câu hỏi mở**:
- Gen3 failure modes (zero-trade trap, MDD cap, sub-hourly, ablation revision) có xuất
  hiện trong offline pipeline không? Nếu có thì dưới dạng nào?
- Gen4 V1 results (sắp có) sẽ cho evidence: gen3→gen4 online fixes có đủ không?
- Gen3's governance_failure_dossier PATTERN (chẩn đoán → gaps → fixes → re-run) có
  giá trị cho Alpha-Lab không? Pattern này paradigm-independent.
- Offline pipeline giải quyết Gap 1 (zero-trade) bằng cách nào? Exhaustive scan tự
  động cover ALL thresholds → không có "AI tự nhiên chọn threshold cao nhất."

---

---

## F-39: Framework testing strategy — automated correctness assurance

- **issue_id**: X38-D-39
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0 (gap audit)
- **current_status**: Open

**Chẩn đoán**:

F-18 covers module-level **human review gates** during build. But the framework
also needs an **automated testing strategy** — tests that run continuously, catch
regressions, and validate the determinism guarantee.

Hiện tại, chỉ F-18 (review gates) và F-11 (session immutability) address quality.
Không finding nào address:

1. **Unit testing per module**: core types, engine math, cost model, feature
   computation — mỗi module cần test suite riêng. Đặc biệt engine math (fill
   logic, PnL calculation, metrics) cần **test vectors** — fixed input → expected
   output, verified by hand.

2. **Determinism regression**: Framework claim "deterministic" (PLAN.md §1.3).
   Cần test suite chạy cùng input + seed → assert bit-identical output. Phát hiện
   ngay khi code change phá determinism.

3. **Pipeline integration tests**: 8-stage pipeline chạy end-to-end trên small
   synthetic dataset. Verify: stage gating works, artifacts produced correctly,
   freeze checkpoint enforced, verdict.json valid.

4. **Contamination firewall tests**: Automated tests verifying firewall blocks
   parameter leakage — unit tests cho typed schema validation, state machine
   transitions, category whitelist enforcement.

**Câu hỏi cần debate**:

| Position | Mô tả | Tradeoff |
|----------|--------|----------|
| A: Test-first (TDD) | Viết test trước implementation cho mỗi module | Chậm hơn ban đầu, ít bug hơn |
| B: Test-after per module | Viết code → review → test → gate | Nhanh hơn, nhưng test quality phụ thuộc discipline |
| C: Minimal + property-based | Ít unit tests, nhiều property-based tests (determinism, monotonicity, boundary) | Ít maintenance, nhưng miss specific bugs |

**Evidence**:
- F-18: module-level review gates (human process, not automated)
- F-11: session immutability (filesystem enforcement, not testing)
- btc-spot-dev/v10/tests/ [extra-archive]: ~370 tests trong v10 — precedent cho engine testing
- btc-spot-dev/validation/tests/ [extra-archive]: 22 test modules cho validation pipeline
- V8 spec_2 [extra-archive]: bit-level system spec với test vectors — pattern cho engine testing
- PLAN.md §1.3: "deterministic" claim cần automated verification

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 005 | F-07 | Engine design (vectorized vs event-loop) determines testing strategy — vectorized engines are easier to test with array assertions, event-loop engines need state-machine testing | 005 owns engine design; 012 adapts testing strategy |
| 003 | F-05 | Pipeline integration tests need stage definitions finalized | 003 owns stages; 012 designs integration tests against stage contracts |
| 002 | F-04 | Firewall testing needs typed schema spec finalized | 002 CLOSED; 012 tests against 002's confirmed contracts |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-18 | Continuous verification — module-level review gates | Thiếu sót | Open |
| X38-D-19 | Online framework evolution (DEMOTED — supporting evidence) | Supporting Evidence | Demoted |
| X38-D-39 | Framework testing strategy — automated correctness assurance | Thiếu sót | Open |
