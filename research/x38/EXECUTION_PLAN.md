# X38 Execution Plan

**Mục đích**: Kế hoạch thực thi cụ thể đưa x38 từ trạng thái hiện tại (56 rounds done —
topic 004, 007, 001, 002, 010, 018 CLOSED; 12 topics còn lại: 12 OPEN + 1 SPLIT) đến sản phẩm cuối (5-6 published specs). File này là tài liệu tham chiếu cho
MỌI agent tham gia debate — đọc file này để hiểu mình đang ở đâu trong quy trình.

**Cập nhật lần cuối**: 2026-03-26

---

## 1. Trạng thái hiện tại

| Hạng mục | Trạng thái |
|----------|------------|
| PLAN.md (tầm nhìn, 1049 dòng) | DONE |
| Design brief (`docs/design_brief.md`) | DONE |
| Evidence coverage | **100% cho topic 000** — Phase 0 DONE (2026-03-21). Gen3 failure report ĐÃ ĐỌC. |
| Topic 000 findings | **SPLIT** (2026-03-22) — 29 findings phân bổ vào 11 sub-topics. Convergence notes (C-01→C-12) giữ tại 000. |
| Pre-debate review convergence | **DONE** — 12 hội tụ, 2 proposals (→F-28/F-29), 5 mở. Condensed summary tại `debate/000-framework-proposal/findings-under-review.md` §Pre-Debate Convergence Notes. |
| Gen4 V1 seed discovery | **IN PROGRESS** — kết quả sắp có, sẽ là evidence cho debate |
| Topic 004 | **CLOSED** (2026-03-21). 6 rounds, 23/23 resolved. Xem `debate/004-meta-knowledge/final-resolution.md`. |
| Topic 000 split | **DONE** (2026-03-22). 11 sub-topics created: 001-003, 005-012. Xem `debate/debate-index.md`. |
| Gap analysis | **DONE** (2026-03-22). 2 topics mới (013-014), 4 findings (F-30→F-33). |
| Rebalance | **DONE** (2026-03-22). 003 split: F-14/F-17 → Topic 015. 003 giảm từ 3→1 finding. |
| Topic 016 | **OPEN** (2026-03-23). Bounded recalibration path. Wave 2.5. 2 findings (BR-01, BR-02). |
| Topic 007 | **CLOSED** (2026-03-23). 4 rounds, 4/4 Converged. Xem `debate/007-philosophy-mission/final-resolution.md`. |
| Topic 001 | **CLOSED** (2026-03-23). 6 rounds, 3/3 resolved (2 Converged + 1 Judgment call). Xem `debate/001-campaign-model/final-resolution.md`. |
| Topic 017 | **OPEN** (2026-03-24). Epistemic search policy. Wave 2.5. 4 findings (ESP-01→ESP-04). |
| Topic 002 | **CLOSED** (2026-03-25). 6 rounds, 7/7 resolved (3 Converged + 4 Judgment call). Xem `debate/002-contamination-firewall/final-resolution.md`. |
| Topic 010 | **CLOSED** (2026-03-25). 6 rounds, 4/4 resolved (3 Converged + 1 Judgment call). Xem `debate/010-clean-oos-certification/final-resolution.md`. |
| Topic 018 | **CLOSED** (2026-03-26). 7 rounds, 4 agents, 10/10 resolved (7 Converged + 3 Defer). Search-space expansion. Xem `debate/018-search-space-expansion/final-resolution.md`. |
| Debate rounds thực hiện | **56** (topic 004: 6, topic 007: 4, topic 001: 6, topic 002: 6, topic 010: 6, topic 018: 28 = 4 agents × 7 rounds). 12 topics remaining (12 OPEN + 1 SPLIT). |
| Specs drafted | SEEDED (1): `architecture_spec.md` seeded from 001/002/004/007/010 closures. §6 Clean OOS Flow filled. Formal drafting not started. |
| Specs published | ZERO |

---

## 2. Critical Path (updated 2026-03-22)

```
Phase 0 (evidence) ──→ Phase 1 (topic 004) ──→ DONE
                   ──→ Topic 000 SPLIT (2026-03-22)
                   ──→ Gap analysis → Topics 013, 014 (2026-03-22)
                   ──→ Rebalance → Topic 015 split from 003 (2026-03-22)
                   ──→ Topic 016 added (2026-03-23, bounded recalibration)
                   ──→ Topic 017 added (2026-03-24, epistemic search policy)
                           ↓
Wave 1:    007 (philosophy)              ← CLOSED (2026-03-23)
               ↓
Wave 2:    008, 009, 010, 011, 012       ← song song
           001, 002, 005, 006             ← song song
           013 (convergence)              ← song song, soft-dep 001
           015 (artifact/version)         ← song song, soft-dep 007, 008
               ↓
Wave 2.5:  016 (bounded recalibration)   ← chờ 001 + 002 + 010 + 011 + 015
           017 (epistemic search policy) ← chờ 002 + 008 + 010 + 013
               ↓
Wave 3:    003 (protocol)                ← chờ 001 + 002 + 004(closed) + 015 + 016 + 017
           014 (execution)               ← chờ 003 + 005
               ↓
Phase 4:   Specs (5-6 documents)
               ↓
Phase 5:   Publication
```

**Tóm tắt**: Topic 004 DONE. Topic 000 SPLIT thành 11 sub-topics. Gap analysis
thêm 013 (convergence) + 014 (execution). Topic 003 rebalanced: F-14/F-17 tách
sang 015 (artifact/version) → 003 focused vào pipeline stages, 015 debate sớm
hơn (Wave 2). Topic 016 (bounded recalibration) added 2026-03-23, Wave 2.5 —
cross-cutting decision chạm 5 Wave 2 topics, phải close trước 003.
Topic 017 (epistemic search policy) added 2026-03-24, Wave 2.5 —
cross-cutting decision chạm 4 Wave 2 topics (002, 008, 010, 013),
phải close trước 003. Song song với 016. Topic 007
(philosophy) là bottleneck duy nhất. Sau 007, 10 remaining Wave 2 topics song song →
016 + 017 (Wave 2.5, song song) → 003 + 014 (Wave 3) cuối cùng.

---

## 3. Các Phase chi tiết

### Phase 0 — Đọc nốt evidence (prerequisite cho topic 000)

**Trạng thái**: ✅ DONE (2026-03-21)

6 tài liệu đã đọc toàn bộ: V4 protocol (271 dòng), Clean OOS V1 (109), V2 (257),
Changelog V4→V5 (30 changes), V5→V6 (24), V6→V7 (22).

**Đầu ra**:
- `docs/evidence_coverage.md` cập nhật: §2.7→§2.12 (key insights), §3 topic 000 = ĐÃ ĐỦ
- Không có finding mới — 29 findings hiện tại đã cover hết khái niệm
- Key insights: V4 = philosophical anchor, V4→V5 = critical innovation (30 changes),
  governance ratchet quantified (271→643 lines), Clean OOS V1→V2 evolution mapped

---

### Phase 1 — Debate Topic 004: Meta-Knowledge Governance

**Trạng thái**: ✅ **DONE** (2026-03-21). 6 rounds completed (max_rounds_per_topic). 23/23 issues resolved: 16 Converged + 5 Decided + 2 pre-debate Resolved. Xem `debate/004-meta-knowledge/final-resolution.md`.
**Phụ thuộc**: Không — evidence đã đủ
**Chạy song song với**: Phase 0, Phase 2
**Pre-resolved**: MK-17 (same-dataset priors) đã RESOLVED trước debate chính thức
(2026-03-19, converged: claude_code + codex + human researcher → Position A: shadow-only).
MK-16 mitigations cũng đã converged (v2+ scope). Debate bắt đầu với 15/17 issues Open.

**Tại sao đây là #1**: Meta-knowledge governance quyết định framework có giá trị
lâu dài hay chỉ hoạt động tốt cho campaign đầu tiên. Nếu structural leakage
không được giải quyết, mọi component khác hoạt động đúng nhưng không tạo tiến bộ.
(Xem PLAN.md §1.4.1 cho evidence đầy đủ.)

**17 findings chia 3 stage debate**:

#### Stage 1A — Mô hình nền tảng (Rounds 1-2)

Scope: MK-01→MK-07 + critique C1, C2

| Finding | Nội dung | Key battle |
|---------|----------|------------|
| MK-01→MK-03 | Chẩn đoán vấn đề (5 hại, fundamental tradeoff) | Chẩn đoán có đúng không? |
| MK-04 | Derivation Test (classify rules) | Có operational không? |
| MK-05 | 3-Tier Taxonomy (Axiom/Prior/Session) | 3 tiers đúng số lượng không? |
| MK-06 | Ontology/Policy separation | Có giữ được dưới áp lực không? |
| MK-07 | Overlap guard | Quá mạnh hay quá yếu? |
| C1 | Compiler determinism | Derivation test quá chủ quan? |
| C2 | Auditor circularity | AI tự audit rules của mình? |

Round 1: Claude Code opening critique → tổng hợp tất cả Group A+B vào argued positions
Round 2: Codex rebuttal → tấn công arguments, không tấn công conclusions

#### Stage 1B — Thiết kế vận hành (Rounds 3-4)

Scope: MK-08→MK-17 + critique C3-C6

| Finding | Nội dung | Key battle |
|---------|----------|------------|
| MK-08 | Lifecycle (promote/demote/retire) | Quá nhiều states? |
| MK-09 | Challenge mechanism | Ai được challenge? Khi nào? |
| MK-10 | Expiry mechanism | Time-based hay evidence-based? |
| MK-11 | Conflict resolution | Khi 2 rules mâu thuẫn? |
| MK-12 | Confidence tracking | Numeric hay qualitative? |
| MK-13 | Storage format | JSON vs YAML vs custom? |
| MK-14 | Firewall boundary (meta ↔ architecture) | Ranh giới ở đâu? |
| MK-15 | Bootstrap (cold start) | Bắt đầu từ zero hay pre-seed? |
| ~~MK-16~~ | ~~Ratchet risk~~ | ~~Mitigations converged (v2+ scope, pre-debate)~~ |
| ~~MK-17~~ | ~~Central question: same-dataset priors~~ | ~~RESOLVED pre-debate: Position A (shadow-only on same dataset)~~ |
| C3 | Budget allocation arbitrary | Budget có cơ sở không? |
| C4 | Overlap guard quá mạnh | T2 rules đều shadow trên same-asset? |
| C5 | Active cap bias | Cap số rules tạo selection bias? |
| C6 | Complexity cho v1 | Quá phức tạp cho version đầu? |

> **MK-17 đã RESOLVED pre-debate** (2026-03-19): Position A — shadow-only on
> same dataset. Xem `findings-under-review.md` MK-17 cho rationale đầy đủ.
> Hệ quả: overlap guard, challenge policy, active cap, budget split đều
> simplified cho v1 (same-dataset mode). MK-16 mitigations converged cho v2+.

Round 3: Claude Code author-reply kết hợp Stage 1A resolution + opening cho 1B
Round 4: Codex reviewer-reply trên operational design

#### Stage 1C — Consolidation (Rounds 5-6, nếu cần)

Round 5: Steel-man checks bắt buộc (rules.md §7) + final positions
Round 6: Resolution. Issues còn Open → Judgment call (human quyết định)

**Ước lượng**: 4-5 rounds (có thể 4 nếu Stage 1A hội tụ nhanh, tối đa 6)

**Cần human approval**:
- Approve mở Round 1 (BLOCKING)
- Mediate: gửi output Round 1 cho Codex
- ~~Judgment calls cuối phase: MK-03, MK-12, MK-15~~ → **Thực tế**: 5 Decided (§14): MK-03, MK-04, MK-07, C1, C2. MK-12 và MK-15 đã Converged.

**Đầu ra**:
- 4-6 round files trong `claude_code/` và `codex/`
- Cập nhật `findings-under-review.md` với status per finding
- `final-resolution.md` khi tất cả 17 issues resolved (2 đã pre-resolved: MK-16, MK-17)

---

### Phase 2 — Debate 15 Topics (Wave-based, 2026-03-22/24)

**Trạng thái**: PARTIALLY EXECUTED — Wave 1 CLOSED (007), Topics 001, 002, 010 closed in Wave 2;
broad Wave 2 tranche still awaiting human approval for remaining topics.
**Phụ thuộc**: Phase 0 (DONE), Phase 1 (DONE)

Topic 000 đã SPLIT (2026-03-22) thành 11 sub-topics. Gap analysis thêm 013 + 014.
Rebalance tách 003 → 015. Topic 016 added (2026-03-23). Topic 017 added (2026-03-24).
Tổng: 16 topics mới (không kể 000 SPLIT và 004 đã CLOSED trước split). Debate theo 4 waves:

#### Wave 1 — Topic 007: Philosophy & Mission Claims (CLOSED)

**Topic 007** — `007-philosophy-mission/` — **CLOSED** (2026-03-23)
- Findings: F-01, F-20, F-22, F-25 (4 findings) — 4/4 Converged
- Rounds used: 4 (of 6 max)
- Xem `debate/007-philosophy-mission/final-resolution.md`
- **Wave 2 is now unblocked**

#### Wave 2 — 11 Topics song song (sau 007 closed)

| Topic | Slug | Findings | Ước lượng | Notes |
|-------|------|----------|-----------|-------|
| **008** | architecture-identity | F-02, F-09, F-13 | 1-2 rounds | 3 pillars, directory, identity |
| **009** | data-integrity | F-10, F-11 | 1 round | Data copies, session immutability |
| **010** | clean-oos-certification | F-12, F-21, F-23, F-24 | ~~1-2 rounds~~ **CLOSED** (6 rounds) | Clean OOS protocol, verdict taxonomy, power rules, pre-existing candidates. 3 Converged + 1 Judgment call |
| **011** | deployment-boundary | F-26, F-27, F-28, F-29 | 1-2 rounds | Scope boundary, research contract |
| **012** | quality-assurance | F-18, F-19 | 1 round | Verification gates, online evolution |
| **001** | campaign-model | F-03, F-15, F-16 | ~~1-2 rounds~~ **CLOSED** (6 rounds) | Campaign→Session, transition |
| **002** | contamination-firewall | F-04 | ~~1-2 rounds~~ **CLOSED** (6 rounds) | Typed schema, state machine. 3 categories permanent (STOP_DISCIPLINE → ANTI_PATTERN), UNMAPPED governance |
| **005** | core-engine | F-07 | 1 round | Rebuild vs vendor |
| **006** | feature-engine | F-08 | 1 round | Registry pattern |
| **013** | convergence-analysis | F-30, F-31 | 1-2 rounds | Convergence metrics, stop conditions |
| **015** | artifact-versioning | F-14, F-17 | 1-2 rounds | State pack, semantic change |

> **Note**: 11 topics CÓ THỂ debate song song. Dependencies giữa chúng là
> soft — debate tiến hành bình thường, minor adjustments sau nếu cần.
> Mediation workflow: human gửi opening critique cho nhiều topics cùng lúc.
>
> **Closure sync for 001**: Final resolution của Topic 001 dựa trên authority
> `design_brief.md` (campaign law), `PLAN.md:500-506` (same-data governance),
> và Topic 015's change-impact table. Extra-archive evidence thực sự dùng:
> Convergence V3, Clean OOS V1/V2, và V7 handoff same-file constraint. Residual
> archive-only gap: Convergence V1/V2 chưa đọc; không blocking cho spec draft
> vì V3 đã là bản tổng hợp mới nhất và D-16 đóng bằng Judgment call.

#### Wave 2.5 — Topics 016 + 017 (sau Wave 2 prerequisites)

**Topic 016** — `016-bounded-recalibration-path/`
- Findings: BR-01, BR-02 (2 findings)
- Key: Bounded recalibration path — cross-cutting decision chạm 5 Wave 2 topics
- Ước lượng: 1-2 rounds
- Phụ thuộc: 001✅ + 002✅ + 010✅ + 011 + 015 (3/5 satisfied)
- **Phải close TRƯỚC 003**: nếu 016 cho phép recalibration, protocol pipeline
  cần thêm branch. Nếu close sau 003, protocol có thể phải reopen.

**Topic 017** — `017-epistemic-search-policy/`
- Findings: ESP-01, ESP-02, ESP-03, ESP-04 (4 findings)
- Key: Epistemic search policy — intra-campaign illumination, phenotype/structural
  prior contracts, promotion ladder, budget governor
- Ước lượng: 2-3 rounds
- Phụ thuộc: 002✅ + 008 + 010✅ + 013 (2/4 satisfied)
- **Phải close TRƯỚC 003**: cell-elite archive, descriptor tagging, và
  epistemic_delta.json ảnh hưởng protocol pipeline stage design.
- 016 và 017 KHÔNG depend lẫn nhau — debate song song trong Wave 2.5.

#### Wave 3 — Topics 003 + 014 (sau upstream closed)

**Topic 003** — `003-protocol-engine/`
- Findings: F-05 (1 finding — F-14/F-17 tách sang 015)
- Key: 8 stages, phase gating, provenance, WFO
- Ước lượng: 1-2 rounds (giảm sau khi tách F-14/F-17)
- Phụ thuộc: 001 + 002 + 004(closed) + 015 + 016 + 017 (tất cả phải CLOSED)
- Rủi ro: nếu upstream decisions thay đổi muộn, 003 phải redo

**Topic 014** — `014-execution-resilience/`
- Findings: F-32, F-33 (2 findings)
- Key: Compute orchestration, checkpointing, CLI
- Ước lượng: 1-2 rounds
- Phụ thuộc: 003 + 005 (cần biết stages + engine)

#### Ước lượng tổng

| Wave | Topics | Rounds/topic | Total rounds (sequential) |
|------|--------|-------------|--------------------------|
| Wave 1 | 1 | 1-2 | 1-2 |
| Wave 2 | 11 (song song) | 1-2 | 1-2 (song song!) |
| Wave 2.5 | 2 (song song) | 1-3 | 1-3 (song song!) |
| Wave 3 | 2 | 2-3 | 2-3 |
| **Tổng** | **16** (OPEN) | — | **6-10 rounds** (vs 20-28 trước split) |

**Cải thiện**: Nhờ parallelism ở Wave 2, tổng thời gian giảm ~75%.

---

### Phase 4 — Soạn Specs

5 specification documents, thứ tự theo dependency (có thể thêm 6th nếu
execution/operational concerns cần spec riêng — quyết định sau debate):

| # | Spec | Phụ thuộc topics | Effort | Nội dung |
|---|------|-------------------|--------|----------|
| 1 | `meta_spec.md` | 002 + 004 + 007 + 008 | 1-2 sessions | 3-tier taxonomy, lifecycle, challenge/expiry, storage, firewall content rules |
| 2 | `engine_spec.md` | 005 + 008 | 1 session | Core backtest types, data, engine, cost, metrics, audit |
| 3 | `feature_spec.md` | 006 + 008 | 1 session | Feature registry, families, calibration, scan strategy |
| 4 | `architecture_spec.md` | 001 + 002 + 004 + 007 + 008 + 009 + 010 + 011 + **013** + **016** + **017** | 2-3 sessions | Campaign model, session lifecycle, directory, data, immutability, Clean OOS, firewall enforcement, deployment boundary, **convergence analysis**, **bounded recalibration path**, **epistemic search policy (phenotype contracts, promotion ladder)** |
| 5 | `protocol_spec.md` | 003 + 012 + **014** + **015** + **017** | 2 sessions | 8-stage pipeline, gating, freeze, **artifacts, change classification**, deliverable templates, quality gates, **execution model, checkpointing**, **cell-elite archive, epistemic_delta.json** |

**Constraint quan trọng**: Contamination Firewall logic chia giữa `architecture_spec`
(enforcement mechanism) và `meta_spec` (content rules). MK-14 (firewall boundary)
PHẢI resolve trước khi bắt đầu draft cả hai. Xem `drafts/README.md`.

**Mỗi spec đi qua**: draft → human review → revision → publish.

---

### Phase 5 — Publication

Chuyển specs từ `drafts/` → `published/`. Human approval bắt buộc cho từng spec.

Thứ tự publication: specs độc lập trước (engine, feature), rồi dependent specs
(meta, architecture), cuối cùng integration spec (protocol). Nhưng mỗi spec
có thể publish độc lập khi ready.

**Đầu ra cuối cùng**:
- 5-6 published specs trong `published/`
- `debate-index.md` cập nhật tất cả topics CLOSED
- `PLAN.md` status cập nhật

---

## 4. Tổng ước lượng (updated 2026-03-22)

| Metric | Trước split | Sau split |
|--------|-------------|-----------|
| Debate topics | 7 (sequential) | 16 OPEN (4 waves, parallel) |
| Rounds sequential | 20-28 | **6-10** (nhờ Wave 2 + 2.5 parallel) |
| Agent invocations | ~40-56 | ~18-28 sequential |
| Human judgment calls | ~10-13 | ~9-13 |
| Specs phải viết | 5 | 5 |
| Specs phải review + publish | 5 | 5 |

---

## 5. Rủi ro & Giảm thiểu

| # | Rủi ro | Xác suất | Giảm thiểu |
|---|--------|----------|------------|
| R1 | Topic 004 deadlock trên MK-03 (bias-variance tradeoff là irreducible) | MEDIUM | Cap 6 rounds. MK-03 → Judgment call. Solution proposal đã cho operating point cụ thể. |
| R2 | Overlap guard (C4) deadlock — quá mạnh = zero meta-knowledge cho BTC, quá yếu = contamination leak | MEDIUM | Critique đã đề xuất: overlap guard chỉ trên evaluation data, không phải all data. Test against V4→V8 evidence. |
| R3 | Topic 003 bottleneck (phụ thuộc 4 upstream topics) | MEDIUM | Giảm từ HIGH sau rebalance: 003 giờ chỉ 1 finding (F-05). F-14/F-17 đã tách sang 015 (Wave 2). 003 focused vào pipeline stages. |
| R4 | ~~Topics 001-003 chưa có findings document~~ | ~~LOW~~ | **RESOLVED** (2026-03-22): Tất cả topics đã có findings-under-review.md. |
| R5 | Firewall boundary conflict giữa meta_spec và architecture_spec | MEDIUM | MK-14 phải resolve TRƯỚC khi bất kỳ draft nào bắt đầu. Ghi constraint này vào Phase 4 checklist. |
| R6 | Human researcher bottleneck (nhiều judgment calls) | LOW-MEDIUM | Batch judgment calls: thu thập sau mỗi phase, trình một lượt. Ước lượng ~3-5 calls mỗi batch. |

---

## 6. Human Researcher Decision Points

| Phase | Cần human quyết định gì | Khi nào |
|-------|--------------------------|---------|
| ~~Phase 1 start~~ | ~~Approve mở debate Topic 004 Round 1~~ | **DONE** (2026-03-21) |
| ~~Phase 1 end~~ | ~~Judgment calls: MK-03, MK-12, MK-15~~ | **DONE** (2026-03-21) |
| ~~Topic 000 split~~ | ~~Approve tách topics~~ | **DONE** (2026-03-22) |
| ~~Wave 1 start~~ | ~~Approve mở debate Topic 007 Round 1~~ | **DONE** (2026-03-23) |
| ~~Wave 1 end~~ | ~~Judgment calls cho F-01, F-20, F-22, F-25~~ | **DONE** (2026-03-23) — all Converged, no judgment calls needed |
| Wave 2 start | Approve mở debate cho 10 remaining Wave 2 topics (001 already closed) | Sau Wave 1 |
| Wave 2 | Mediate debate, judgment calls per topic | Rolling |
| Wave 2.5 start | Approve mở Topics 016 (bounded recalibration) + 017 (epistemic search policy) | Sau Wave 2 prerequisites |
| Wave 3 | Approve mở Topics 003 + 014 sau upstream closed | Sau Wave 2.5 |
| Phase 4 | Review draft specs; resolve cross-spec inconsistencies | Rolling |
| Phase 5 | Final publication approval per spec | Cuối |

---

## 7. Hành động tiếp theo ngay bây giờ

~~**Bước 1** (cần human approve): Mở debate Topic 004 Round 1~~ → **APPROVED** (2026-03-21)
~~**Bước 2** (autonomous, song song): Đọc 6 evidence documents cho Phase 0~~ → **DONE** (2026-03-21)
~~**Bước 3** (sau approve): Claude Code viết opening critique cho Topic 004~~ → **DONE** (2026-03-21)
~~**Bước 4** (cần human mediate): Gửi Round 1 cho Codex~~ → **DONE** (2026-03-21)
~~**Bước 5**: Claude Code viết Round 2 author-reply~~ → **DONE** (2026-03-21)
~~**Bước 6** (cần human mediate): Gửi Round 2 cho Codex~~ → **DONE** (2026-03-21)
~~**Bước 7**: Claude Code viết Round 3 §7(c) confirmations~~ → **DONE** (2026-03-21) — Stage 1A CLOSED, 9/9 resolved (4 Converged + 5 Decided §14)
~~**Bước 8** (cần human approve): Mở Stage 1B~~ → **DONE** (2026-03-21)
~~**Bước 9**: Codex viết opening critique Stage 1B~~ → **DONE** (`codex/round-3_opening-critique.md`)
~~**Bước 10**: Claude Code author-reply Stage 1B~~ → **DONE** (`claude_code/round-4_author-reply.md`)
~~**Bước 11** (cần human mediate): Gửi Round 4 author-reply cho Codex~~ → **DONE** (`codex/round-4_reviewer-reply.md`)
~~**Bước 12**: Claude Code author-reply Round 5~~ → **DONE** (`claude_code/round-5_author-reply.md`)
~~**Bước 13** (cần human mediate): Gửi Round 5 cho Codex~~ → **DONE** (`codex/round-5_reviewer-reply.md`)
~~**Bước 14**: Claude Code author-reply Round 6~~ → **DONE** (`claude_code/round-6_author-reply.md`)
~~**Bước 15** (cần human mediate): Gửi Round 6 cho Codex~~ → **DONE** (`codex/round-6_reviewer-reply.md`)
~~**Bước 16**: Human judgment calls (5 issues)~~ → **DONE** (`judgment-call-deliberation.md`)
~~**Bước 17**: Tạo final-resolution.md~~ → **DONE** (`final-resolution.md`, 2026-03-21)

**Topic 004 CLOSED.** Topic 000 SPLIT (2026-03-22) thành 11 sub-topics.
Tiếp theo: mở debate **Topic 007** (philosophy-mission) Round 1 (Wave 1).

~~**Bước 18** (cần human approve): Mở debate Topic 007 Round 1~~ → **DONE** (2026-03-23)
~~**Bước 19** (autonomous): Claude Code viết opening critique cho Topic 007~~ → **DONE** (`claude_code/round-1_opening-critique.md`)
~~**Bước 20** (cần human mediate): Gửi Round 1 cho Codex~~ → **DONE** (`codex/round-1_rebuttal.md`)
~~**Bước 21**: Codex viết rebuttal~~ → **DONE** (4 rounds total: R1-R4)
~~**Bước 22**: Resolve + final-resolution.md cho Topic 007~~ → **DONE** (`final-resolution.md`, 2026-03-23, 4/4 Converged)

**Topic 007 CLOSED.** Wave 2 is now unblocked.

**Topic 001 CLOSED** (2026-03-23, 6 rounds, 3/3 resolved). Debated early in Wave 2
before formal Wave 2 opening approval. `architecture_spec.md` seeded from 001/004/007.

**Bước 23** (cần human approve): Mở Wave 2 — 10 remaining topics song song (001 already closed)
**Bước 24-34**: Debate remaining Wave 2 topics (song song, human mediate mỗi round)
**Bước 35** (cần human approve): Mở Wave 2.5 — Topics 016 (bounded recalibration) + 017 (epistemic search policy)
**Bước 36-38**: Debate Topics 016 (1-2 rounds) + 017 (2-3 rounds) — song song
**Bước 38** (cần human approve): Mở Wave 3 — Topics 003 + 014
**Bước 39-41**: Debate Topics 003 + 014 (1-2 rounds mỗi topic)

---

## 8. Quy ước cho agent tham gia

- **Đọc file này trước mọi round debate** — để biết mình đang ở phase nào
- **Cập nhật trạng thái** trong file này sau mỗi round hoàn tất
- **Không vượt scope** — mỗi round chỉ giải quyết findings trong stage hiện tại
- **Tham chiếu PLAN.md** cho context sâu, file này cho quy trình
- **Tham chiếu `debate/rules.md`** cho quy tắc debate
