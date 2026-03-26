# Findings Under Review — Architecture Pillars & Identity

**Topic ID**: X38-T-08
**Opened**: 2026-03-22
**Split from**: Topic 000 (X38-T-00)
**Author**: claude_code (architect)

3 findings về cấu trúc kiến trúc nền tảng và mô hình identity/versioning.

**Convergence notes liên quan** (full text tại `../000-framework-proposal/findings-under-review.md`
§Pre-Debate Convergence Notes):
- C-11: Authority chain: design_brief + PLAN primary, F-04 supporting enforcement

---

## F-02: Ba trụ cột kiến trúc

- **issue_id**: X38-D-02
- **classification**: Judgment call
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

Framework được xây trên 3 trụ cột bắt buộc:

1. **Contamination Firewall** — tách cứng meta-knowledge (methodology) khỏi
   data-derived specifics (features, thresholds, winners). Machine-enforced.

2. **Protocol Engine** — V6 protocol (8 stages) biên dịch thành executable
   pipeline với phase gating. Stage N+1 bị chặn cho đến khi stage N artifacts
   tồn tại. Freeze checkpoint tại Stage 7. Benchmark embargo giữ mặc định
   (bảo vệ selection cleanliness, không chỉ chặn AI peek —
   RESEARCH_PROMPT_V6.md line 284-292 [extra-archive]).

3. **Meta-Updater** — sau mỗi campaign chỉ cập nhật 3 loại (per Topic 002
   closure, Facet C — STOP_DISCIPLINE consolidated into ANTI_PATTERN):
   provenance/audit/serialization rules, split hygiene heuristics,
   anti-patterns incl. stop-discipline (methodology-level). KHÔNG BAO GIỜ cập
   nhật priors về đáp án. Mọi lesson làm nghiêng cán cân
   family/architecture/calibration-mode đều bị coi là contamination.

**Evidence**:
- PLAN.md:664 [x38 internal]: "3 thành phần bắt buộc: contamination firewall,
  protocol engine, meta-updater" (expert feedback session, 2026-03-18).
- research/x37/docs/gen1/RESEARCH_PROMPT_V6/PROMPT_FOR_V6_HANDOFF.md:19 [extra-archive]: "Transfer only meta-knowledge [...],
  DO NOT transfer data-derived specifics."
- research/x37/x37_RULES.md §7 [extra-archive]: phase gating đã tồn tại dưới dạng rules, cần codify.

**Câu hỏi mở**: 3 trụ cột có đủ? Có cần trụ thứ 4 (ví dụ: reproducibility
engine, audit trail engine)? Hay 3 trụ đã bao trùm?

---

## F-09: Cấu trúc thư mục target

- **issue_id**: X38-D-09
- **classification**: Thiếu sót
- **opened_at**: 2026-03-18
- **opened_in_round**: 0
- **current_status**: Open

**Nội dung**:

```
/var/www/trading-bots/alpha-lab/
│
├── pyproject.toml              # uv project, venv riêng
├── CLAUDE.md                   # AI context
├── README.md
│
├── src/alpha_lab/
│   ├── core/                   # 6 modules: types, data, engine, cost, metrics, audit
│   ├── features/               # registry, compute, threshold, signal, families/
│   ├── discovery/              # 8 modules: protocol→scanner→pruner→...→evaluator
│   ├── validation/             # wfo, bootstrap, plateau, ablation, regime, gates
│   ├── campaign/               # campaign, session, convergence, contamination, knowledge, oos
│   └── cli/                    # main, run_session, run_campaign, new_campaign, report
│
├── data/btcusdt/               # Data copies (SHA-256), NOT symlinks
│   ├── bars_2017_2026q1.csv
│   └── checksums.json
│
├── campaigns/                  # Campaign outputs
│   ├── c001_btc_2017_2026q1/
│   │   ├── campaign.json       # Protocol, data ref, status, inherits_from
│   │   ├── sessions/s001/...   # Per-session artifacts (immutable after verdict)
│   │   ├── convergence/        # Cross-session analysis
│   │   └── contamination.json  # Union contamination map
│   └── c002_btc_2017_2026q3/   # Next campaign (6 months later)
│
├── knowledge/                  # Accumulated meta-knowledge
│   ├── lessons.json            # Principle-level (no specifics!)
│   ├── lesson_history.json     # When added/updated/retired
│   └── campaigns_summary.json  # High-level campaign verdicts
│
└── tests/
    ├── unit/
    ├── integration/
    └── regression/             # Reproduce v5_sfq70, v6_ret168
```

Nguyên tắc: Code ≠ Data ≠ Results ≠ Knowledge. Khi project phình, chỉ
`campaigns/` phình.

Venv riêng (không share với /var/www/trading-bots/.venv/).
Data là copies (mỗi campaign gắn liền với exact snapshot).

**Evidence**:
- docs/research/RESEARCH_RULES.md [extra-archive]: research self-contained pattern.
- research/x37/README.md [extra-archive]: sessions/, shared/, analysis/ — similar concept.

**Câu hỏi mở**:
- `knowledge/` nên ở root hay trong `src/`?
- `data/` nên tách ra ngoài project (e.g., `/var/www/data/`) hay giữ trong?
- Cần `docs/` trong alpha-lab không? Hay CLAUDE.md + README.md đủ?

---

## F-13: Three-identity-axis model

- **issue_id**: X38-D-13
- **classification**: Thiếu sót
- **opened_at**: 2026-03-21
- **opened_in_round**: 0 (pre-debate, gen4 evidence import)
- **current_status**: Open
- **source**: x37/docs/gen4 — Research Operating Kit v4.0 [extra-archive]

**Nội dung**:

Gen4 tách identity thành 3 trục độc lập:

```
constitution_version    ← phiên bản research rules (v4.0)
program_lineage_id      ← chương trình nghiên cứu (chuỗi versions cùng mục tiêu)
system_version_id       ← phiên bản frozen candidate cụ thể (đơn vị evidence)
```

Mỗi trục thay đổi độc lập:
- Thay đổi constitution → new major version (governance review)
- Mở nhánh nghiên cứu mới → new program_lineage_id
- Freeze candidate mới → new system_version_id (evidence clock reset)

**So sánh với x38**: Alpha-Lab có `campaign` (≈ program_lineage) và `session`
(≈ system_version), nhưng **chưa có trục constitution_version**. Khi debate rules
hoặc protocol thay đổi giữa các campaign, hiện không có cơ chế tracking. Điều này
có nghĩa:
- Campaign C1 (dùng protocol v1) và C3 (dùng protocol v2 sau governance reform)
  không phân biệt được ở cấp metadata
- Convergence analysis giữa campaigns dùng protocol khác nhau có thể so sánh táo
  với cam mà không biết

**Đề xuất**: Thêm trục `protocol_version` vào campaign metadata. Mỗi campaign.json
ghi rõ protocol version nó tuân thủ. Convergence analysis chỉ so sánh campaigns
cùng protocol version (hoặc flag rõ cross-protocol comparison).

**Evidence**:
- research/x37/docs/gen4/core/research_constitution_v4.0.yaml §identity [extra-archive]: "Three identity axes, separated and independent"
- research/x37/docs/gen4/core/README_EN.md [extra-archive]: system version lifecycle overview
- x38 F-03 (Campaign model): chỉ có campaign/session, thiếu protocol versioning

**Câu hỏi mở**:
- Có cần 3 trục đầy đủ hay 2 trục (protocol_version + campaign/session) đủ?
- Protocol version thay đổi khi nào? Chỉ khi debate kết thúc và spec published?
- Cần governance review (như gen4) cho mỗi protocol change, hay lightweight hơn?

---

## X38-SSE-04-IDV: Candidate-level identity vocabulary (routed from Topic 018)

- **issue_id**: X38-SSE-04-IDV
- **classification**: Thiếu sót
- **opened_at**: 2026-03-26
- **opened_in_round**: 0 (routed from Topic 018, REOPENED 2026-03-26 — provisional)
- **current_status**: Open
- **source**: Topic 018 (Search-Space Expansion), SSE-D-04 field 3 + correction note

**Nội dung**:

Topic 018's 7-field breadth-activation interface contract (SSE-D-04) requires
`identity_vocabulary` (field 3) to be declared before breadth activation. The
correction note (`debate/018-search-space-expansion/final-resolution.md:146-150`)
states that candidate-level `identity_vocabulary` ownership is "TBD by synthesis"
because X38-D-13 covers protocol/campaign/session identity axes, not
candidate-equivalence vocabulary.

This topic must determine whether candidate-level equivalence vocabulary
(deterministic structural pre-bucket: descriptor hash, parameter family,
AST-hash as subset) belongs within Topic 008's scope or requires a different
owner topic.

**Evidence**:
- `debate/018-search-space-expansion/final-resolution.md:122-130` [x38 internal]:
  7-field breadth-activation table, field 3 marked UNRESOLVED
- `debate/018-search-space-expansion/final-resolution.md:146-150` [x38 internal]:
  correction note — "TBD by synthesis", X38-D-13 scope insufficient

**Câu hỏi mở**:
- Candidate-level equivalence vocabulary thuộc 008 (identity) hay 013 (convergence)?
- Nếu thuộc 008: X38-D-13 cần mở rộng scope sang candidate-equivalence?
- Nếu thuộc 013: field 3 owner cần cập nhật trong SSE-D-04?

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 007 | F-01 | Philosophy (F-01) must settle before pillars (F-02) can be finalized — if 007 redefines framework scope, pillar count or identity may change | 007 owns decision; 008 adapts. **RESOLVED**: 007 CLOSED, F-01 frozen. |
| 017 | ESP-01→04 | Topic 017 proposes Epistemic Search Policy as sub-component (v1) → pillar (v2). Provides concrete answer to F-02 "3 pillars enough?" question. If 008 decides 3 sufficient, ESP substance folds into Protocol Engine without architectural promotion. | 008 owns pillar decision; 017 provides substance. |
| 010 | D-23 | Pre-existing candidate treatment Scenario 1 (same-family rediscovery) deferred to 008 F-13 — identity schema must support same-family comparison. Two consumption demands on F-13: (a) 010's same-family comparison, (b) 018's candidate equivalence vocabulary (SSE-04-IDV). | 008 owns identity schema; 010 consumes. |
| 018 | SSE-04-IDV | Candidate-level identity vocabulary routed from Topic 018 (REOPENED). SSE-D-04 field 3 requires `identity_vocabulary` declaration. Routing provisional until 018 re-closes under standard 2-agent debate. | 008 owns interface; 018 provides substance (provisional). |

## Bảng tổng hợp

| Issue ID | Finding | Phân loại | Status |
|----------|---------|-----------|--------|
| X38-D-02 | Ba trụ cột kiến trúc | Judgment call | Open |
| X38-D-09 | Cấu trúc thư mục target | Thiếu sót | Open |
| X38-D-13 | Three-identity-axis model (từ gen4) | Thiếu sót | Open |
| X38-SSE-04-IDV | Candidate-level identity vocabulary (from T018) | Thiếu sót | Open |
