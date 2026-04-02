# Findings Under Review — Protocol Engine

**Topic ID**: X38-T-03
**Opened**: 2026-03-22 (activated from PLANNED)
**Author**: claude_code (architect)

4 findings về protocol engine — 8-stage discovery pipeline.
F-36 and F-37 added 2026-03-31 (gap audit).

**Lưu ý**: F-14 (state pack) và F-17 (semantic change classification) đã tách
sang Topic 015 (Artifact & Version Management) vì bản chất "records & versioning"
khác với pipeline logic.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-05: Semantic boundary DIAGNOSIS hội tụ; exact boundary cần debate

---

## F-05: Protocol engine — 8 stages

- **issue_id**: X38-D-05
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

8 stages từ V6, codified:

```
Stage 1: Protocol lock → protocol_freeze.json
Stage 2: Data audit → audit_report.json, audit_tables/
Stage 3: Single-feature scan → stage1_registry.parquet (50K+ rows)
Stage 4: Orthogonal pruning → shortlist.json (keep/drop ledger)
Stage 5: Layered architecture → candidates.json
Stage 6: Parameter refinement → plateau_grids/, search_results.parquet
Stage 7: Freeze → frozen_spec.json (IMMUTABLE after this)
Stage 8: Evaluation → holdout_results.json, internal_reserve_results.json, verdict.json
```

Phase gating: stage N+1 runner checks `required_artifacts[N]` exist.
Freeze checkpoint: sau Stage 7, stages 1-6 dirs trở thành read-only.

**Evidence**:
- RESEARCH_PROMPT_V6.md §Stages 1-8 [extra-archive]: definition.
- x37_RULES.md §7.1-7.4 [extra-archive]: gating rules, minimum evidence, checkpoints.
- research/x37/resource/gen1/v8_sd1trebd/spec/spec_1_research_reproduction_v8.md [extra-archive]:
  866-line research reproduction spec uses explicit
  **Input → Logic → Output → Decision Rule** structure for every step.
- research/x37/docs/gen1/RESEARCH_PROMPT_V8/SPEC_REQUEST_PROMPT.md [extra-archive]:
  263-line meta-prompt — pattern:
  meta-prompt generates spec-writing instructions → AI writes spec → checklist verifies.

**Câu hỏi mở**:
- V6 có 8 stages, x37 có 7 phases. Mapping nào đúng?
- Benchmark embargo: giữ mặc định? Ngoại lệ khi nào?
- **V8 pattern**: Nên alpha-lab adopt Input→Logic→Output→Decision cho mỗi stage?
- **Deliverable template**: SPEC_REQUEST_PROMPT pattern thành built-in component?
- Provenance tracking: automatic hay manual?
- WFO fold structure: cố định semiannual hay configurable per campaign?
- **Deferred from Topic 007 D-25**: Ablation gate thresholds for testing
  regime-aware structures — 007 froze the prohibition (no external classifiers,
  no post-freeze switching) but deferred specific thresholds to 003.
- **Scan-phase multiple testing**: Stage 3 scan 50K+ configs → massive multiple
  comparison problem. Workspace hiện có DSR (`research/lib/dsr.py`) và M_eff
  (`research/lib/effective_dof.py`), nhưng cả hai là **post-selection** tools
  (correct bias cho strategy đã chọn, không control false discovery trong scan).
  Stage 3→4 (scan → prune) cần scan-phase correction: FDR (Benjamini-Hochberg)?
  Step-down (Holm)? Hay cascade design (shortlist → holdout) tự nó đã đủ?
  Evidence: V6-V8 dùng cascade nhưng không nêu formal correction rate.

---

## F-36: Multi-asset pipeline adaptation

- **issue_id**: X38-D-36
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0 (gap audit)
- **current_status**: Open

**Chẩn đoán**:

PLAN.md §Phạm vi: "Không chỉ BTC/USDT. Framework phải hoạt động trên bất kỳ
asset nào (crypto, equities, FX)." PLAN.md §2.1 Trụ 2: "8 stages là BTC-v1
protocol baseline — rút từ V6/V7/V8 lineage. KHÔNG phải search ontology phổ quát."

8 stages hiện tại giả định OHLCV data ở H4+D1 resolution. Trên assets khác:
- **Equities**: order flow data (Level 2, trades & quotes) → Stage 3 feature scan
  cần feature families ngoài OHLCV (bid-ask spread, order imbalance, trade size
  distribution). Stage 2 data audit cần schema khác.
- **FX**: tick data, 24h market, no volume → Stage 3 feature families khác,
  cross-timeframe alignment khác (no D1 close).
- **Commodities**: roll dates, contango/backwardation → Stage 2 cần contract
  management, Stage 3 cần term structure features.

**Không finding nào** hiện tại address câu hỏi: pipeline 8 stages adapt thế nào
cho input data khác OHLCV?

**Câu hỏi cần debate**:

| Position | Mô tả | Tradeoff |
|----------|--------|----------|
| A: Fixed 8 stages, asset-specific config | Cùng pipeline, thay đổi config (feature families, data schema, threshold modes) per asset | Đơn giản, nhưng có thể ép fit |
| B: Configurable pipeline template | Stage count và ordering configurable per asset class. BTC-v1 = 1 template | Linh hoạt, nhưng thêm complexity |
| C: v1 = BTC-only, defer multi-asset to v2+ | Ship BTC pipeline, generalize khi có second asset | Fastest v1, nhưng may require rewrite |

**Evidence**:
- PLAN.md §Phạm vi: multi-asset requirement
- PLAN.md §2.1 Trụ 2: "BTC-v1 baseline, không phải search ontology phổ quát"
- Topic 018 SSE-D-02 rule 3: "OHLCV-only" — rule này có apply cho non-OHLCV assets?
- F-08 (Topic 006): feature families hiện tại = OHLCV-derived (trend, vol, location,
  flow, structure, cross_tf). Flow proxy ≠ real order flow.

---

## F-37: Human decision points in offline pipeline

- **issue_id**: X38-D-37
- **classification**: Thiếu sót
- **opened_at**: 2026-03-31
- **opened_in_round**: 0 (gap audit)
- **current_status**: Open

**Chẩn đoán**:

Pipeline được mô tả là "deterministic, no AI in execution" (PLAN.md §TL;DR).
Nhưng nhiều điểm trong pipeline yêu cầu human judgment:

1. **Pre-Stage 1**: Human define search space (feature families, threshold modes,
   lookback grids). Đây là quyết định lớn nhất — search space quyết định mọi thứ
   downstream.
2. **Stage 4→5**: Shortlist → layered search. Human review shortlist trước khi
   invest compute vào layering? Hay fully automatic?
3. **Stage 7**: Freeze comparison set. Human approve freeze hay automatic?
4. **Campaign boundary**: Human quyết định HANDOFF vs STOP vs re-run.
5. **Clean OOS trigger**: Human chọn thời điểm (đã spec trong F-12/F-21).

Nếu pipeline fully automatic (human chỉ ở boundaries), mỗi session chạy hoàn
toàn không cần human input — reproducible, scalable. Nhưng human oversight ở
mid-pipeline có thể catch issues sớm hơn (e.g., Stage 3 scan bỏ qua 1 family
do feature bug → human review Stage 4 shortlist phát hiện).

**Câu hỏi cần debate**:

| Position | Mô tả | Tradeoff |
|----------|--------|----------|
| A: Human at boundaries only | Human: define search space (pre-Stage 1) + approve verdict (post-Stage 8) + campaign decisions. Pipeline stages 1-8 fully automatic | Maximum reproducibility, minimum human bottleneck |
| B: Human gates at critical stages | Human approve: Stage 4 shortlist, Stage 7 freeze. Rest automatic | Catches mid-pipeline issues, but slower, less reproducible |
| C: Human optional review + automatic continue | Pipeline auto-continues by default. Human CAN review at any stage but pipeline doesn't WAIT | Balance: reproducible default, human oversight available |

**Evidence**:
- PLAN.md §TL;DR: "deterministic code pipeline, no AI in execution"
- Topic 001 D-16: campaign guardrails — human at campaign boundary
- Topic 010 F-21: "mandatory human review per trigger" — human at Clean OOS
- F-05: stage gating is artifact-based (automatic), không mention human gates
- V4-V8 [extra-archive]: every stage had human involvement (AI conversation) —
  offline pipeline removes AI but question: also remove human?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 015 | F-14 | Artifact enumeration (state pack) split from 003 but stage outputs must conform to artifact spec — protocol stages define WHEN, artifact spec defines WHAT | 015 owns artifact spec; 003 consumes it |
| 016 | F-35 | Bounded recalibration may require protocol stages to support mid-campaign parameter updates — incompatible with current freeze-at-Stage-7 design | 016 must CLOSE before 003 debate; 016 owns decision |
| 002 | F-04 | Firewall enforcement gates protocol transitions — if firewall rejects a lesson mid-pipeline, protocol must handle gracefully | 002 owns firewall rules; 003 adapts |
| 007 | D-25 | F-25 regime-aware policy froze prohibition (no external classifiers, no post-freeze switching). Ablation gate thresholds deferred to 003. | 007 CLOSED; 003 owns thresholds. |
| 017 | ESP-01 | Cell-elite archive replaces Stage 4 global pruning. Descriptor tagging adds Stage 3 output. epistemic_delta.json adds Stage 8 mandatory output. Local probes change Stage 5 search strategy. | 003 owns pipeline structure; 017 defines ESP component contracts. 017 must CLOSE before 003 debate. |
| 018 | SSE-D-04 | Breadth-activation blocker at `protocol_lock` — protocol must declare all 7 fields before activation. Routed from Topic 018 (CLOSED 2026-03-27). Routing confirmed. Stage 3 scan-phase multiple-testing routed via SSE-D-09→013. | 003 owns protocol gate; 018 provides 7-field contract (confirmed). |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-05 | Protocol engine — 8 stages | Judgment call | Open |
| X38-D-36 | Multi-asset pipeline adaptation | Thiếu sót | Open |
| X38-D-37 | Human decision points in offline pipeline | Thiếu sót | Open |
| X38-SSE-D-04 | Breadth-activation blocker at protocol_lock (từ Topic 018) | Thiếu sót | Open |

---

## Issue routed from Topic 018 — Search-Space Expansion (2026-03-27)

Architecture-level decision from Topic 018 (**CLOSED** 2026-03-27 —
standard 2-agent debate completed, 10 Converged + 1 Judgment call). This issue
represents a confirmed implementation obligation.
Source: `debate/018-search-space-expansion/final-resolution.md` (authoritative).

---

## SSE-D-04: Breadth-activation blocker at protocol_lock

- **issue_id**: X38-SSE-D-04
- **classification**: Thiếu sót
- **opened_at**: 2026-03-27
- **opened_in_round**: 0 (routed from Topic 018, SSE-D-04)
- **current_status**: Open

**Nội dung**:

Topic 018 decided (confirmed 2026-03-27): breadth-activation contract requires protocol
to declare all 7 fields at `protocol_lock` before activation is permitted.

The 7 mandatory fields (from SSE-D-04, canonical source:
`debate/018-search-space-expansion/final-resolution.md:88-96`):
1. `descriptor` — what the candidate looks like (structural identity)
2. `comparison_domain` — which candidates compare against each other
3. `identity_vocabulary` — how to name/hash candidates
4. `equivalence_method` — how to determine if two candidates are "the same"
5. `scan_phase_correction_method` — multiplicity correction for breadth expansion
6. `robustness_bundle` — which proof components required
7. `invalidation_scope` — what gets invalidated when a field changes

Downstream ownership routing (which topics resolve exact values for each field):
- Field 3 `identity_vocabulary`: resolved via Topic 008 Decision 4 (SSE-04-IDV)
- Field 4 `equivalence_method` axes + anomaly thresholds: routed to Topic 013 (SSE-04-THR)
- Field 5 `scan_phase_correction_method`: routed to Topic 013 (SSE-D-09)
- Field 7 `invalidation_scope` cascade rules: routed to Topic 015 (SSE-04-INV)
- `generation_mode` (SSE-D-03, separate decision): routed to Topic 006
- `contradiction_storage` (SSE-D-08, separate decision): routed to Topic 015

Topic 003 owns:
1. Protocol gate that enforces 7-field declaration at `protocol_lock`
2. Stage ordering: breadth-activation check must occur before Stage 3 scan
3. Integration with existing 8-stage pipeline (F-05)

Stage 3 scan-phase multiple-testing correction (SSE-D-09) routed via 013, not directly to 003.

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md:355` [within-x38]: SSE-D-04 routing confirmed.
- `debate/018-search-space-expansion/final-resolution.md:42-49` [within-x38]: Cross-topic impact table.
