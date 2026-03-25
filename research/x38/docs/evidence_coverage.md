# Evidence Coverage Tracker — X38

**Purpose**: Theo dõi mức độ khai thác tài liệu x37 cho từng debate topic.
Đảm bảo debate dựa trên evidence đầy đủ, không bỏ sót tài liệu quan trọng.

**Nguyên tắc**: Không cần đọc hết 376 files trong x37. Nhưng mỗi topic phải
đọc đủ evidence trước khi debate. File này track: đã đọc gì, chưa đọc gì,
cần đọc khi nào.

---

## 1. Đã khai thác (tính đến 2026-03-23)

> **⚠️ Tất cả gen1/gen2/gen3/gen4 evidence dưới đây là từ framework ONLINE (AI chat).**
> Alpha-Lab là framework OFFLINE (code pipeline). Xem `docs/online_vs_offline.md`.
> Dùng evidence này để hiểu VẤN ĐỀ, KHÔNG copy giải pháp.

### V8 docs, ONLINE gen1 (đọc toàn bộ 2026-03-19)

| Tài liệu | Kích thước | Dùng cho | Mức độ |
|-----------|-----------|----------|--------|
| V8 protocol (RESEARCH_PROMPT_V8.md) | 643 dòng | Full protocol analysis | **Đọc toàn bộ** |
| V8 handoff (PROMPT_FOR_V8_HANDOFF.md) | 169 dòng | Transfer rules, meta-prompt design | **Đọc toàn bộ** |
| V8 spec request (SPEC_REQUEST_PROMPT.md) | 263 dòng | Meta-prompt cho spec generation — NEW doc type | **Đọc toàn bộ** |
| V8 changelog (CHANGELOG_V7_TO_V8.md) | 22 dòng | 16 changes: 5 FIX, 6 IMPROVE, 3 NEW, 2 REMOVE | **Đọc toàn bộ** |
| V8 convergence status (CONVERGENCE_STATUS_V3.md) | 187 dòng | V4→V7 convergence/divergence patterns | **Đọc toàn bộ** |
| V8 contamination log (CONTAMINATION_LOG_V4.md) | 1692 dòng | 8 rounds contamination accounting | **Đọc cấu trúc + headers** |

### V8 resource specs (đọc toàn bộ 2026-03-19)

| Tài liệu | Kích thước | Dùng cho | Mức độ |
|-----------|-----------|----------|--------|
| spec_1_research_reproduction_v8.md | 866 dòng | Full research reproduction (input→logic→output→decision) | **Đọc toàn bộ** |
| spec_2_system_S_D1_TREND.md | 372 dòng | Bit-level system spec with test vectors | **Đọc toàn bộ** |

### V8 resource artifacts (đọc 2026-03-19)

| Tài liệu | Dùng cho | Mức độ |
|-----------|----------|--------|
| frozen_system.json | Frozen winner S_D1_TREND complete spec | **Đọc toàn bộ** |
| provenance_declaration.json | Independence claims | **Đọc toàn bộ** |
| session_finality_statement.txt | Finality pattern | **Đọc toàn bộ** |
| frozen_system_spec.md | Human-readable frozen spec | **Đọc toàn bộ** |
| frozen_comparison_set_ledger.csv | 7 frozen candidates | **Đọc toàn bộ** |
| validation_results.csv | 7 systems × 3 segments × 2 costs | **Đọc toàn bộ** |
| locked_protocol_settings.json | Protocol settings | Noted (not read in detail) |
| data_audit_summary.json | Data quality audit | Noted |
| shortlist_ledger.csv | 29 candidate decisions | Noted |
| stage1_feature_registry.csv | 1,234 feature scans (1.5MB) | Noted |
| pre_reserve_pairwise_matrix_long.csv | 42 pairwise comparisons | Noted |
| reserve_internal_summary.csv | Reserve metrics all 7 systems | Noted |
| 5 charts (PNG) | Visual artifacts | Noted |

### Gen4 — ONLINE (đọc 2026-03-21)

> **⚠️ Framing**: Gen4 là framework ONLINE (AI chat). Alpha-Lab là OFFLINE (code
> pipeline). Gen4 là evidence về vấn đề, KHÔNG phải template cho giải pháp.
> Xem `docs/online_vs_offline.md`.

| Tài liệu | Dùng cho | Mức độ |
|-----------|----------|--------|
| `core/research_constitution_v4.0.yaml` (36KB) | 3-axis identity, complexity caps, hard constraints, objective, redesign guardrails, semantic change classification | **Đọc toàn bộ** (via agent) |
| `core/STATE_PACK_SPEC_v4.0_EN.md` | 18 required artifacts, handoff spec | **Đọc toàn bộ** (via agent) |
| `core/FORWARD_DECISION_POLICY_EN.md` | Two cumulative scopes, keep/promote/kill rules | **Đọc toàn bộ** (via agent) |
| `core/SESSION_BOUNDARIES_EN.md` | 6 modes: S1/S2/M1/M2/M3/M4, sandbox vs mainline | **Đọc toàn bộ** (via agent) |
| `core/UPLOAD_MATRIX_EN.md` | What to upload per mode | **Đọc toàn bộ** (via agent) |
| `core/README_EN.md` | Kit overview, version lifecycle | **Đọc toàn bộ** (via agent) |
| `core/HISTORICAL_SEED_AUDIT_SPEC_EN.md` | Audit CSV specification | **Đọc toàn bộ** (via agent) |
| `core/FILE_AND_SCHEMA_CONVENTIONS_EN.md` | File naming, schema rules | **Đọc toàn bộ** (via agent) |
| `core/KIT_REVIEW_AND_FIXLOG_EN.md` | Review notes and fixes | **Đọc toàn bộ** (via agent) |
| `prompt_set/PROMPT_D*.md` (D0→D2, 22 files) | Seed discovery prompts | **Đọc toàn bộ** (via agent) |
| `prompt_set/PROMPT_F*.md` (F0→F2) | Forward evaluation prompts | **Đọc toàn bộ** (via agent) |
| `prompt_set/PROMPT_R*.md` (R0→R2) | Redesign freeze prompts | **Đọc toàn bộ** (via agent) |
| `prompt_set/PROMPT_G*.md` (G0→G2) | Governance review prompts | **Đọc toàn bộ** (via agent) |
| `template/*.template.*` (19 files) | State pack templates | **Đọc toàn bộ** (via agent) |

**Output**: 5 findings (F-13→F-17) imported vào Topic 000. Xem `debate/000-framework-proposal/findings-under-review.md`.

### Gen2 — ONLINE (đọc 2026-03-21)

> **⚠️ Framing**: Gen2 là framework ONLINE, THẤT BẠI vì chỉ cho phép TA indicators.

| Tài liệu | Dùng cho | Mức độ |
|-----------|----------|--------|
| `core/README_EN.md` | v2 operating model, 3 modes (seed/forward/governance) | **Đọc toàn bộ** |
| `core/KIT_REVIEW_AND_FIXLOG_EN.md` | 10 fixes from gen1→gen2 | **Đọc toàn bộ** |

**Output**: Context cho F-19. Gen2 FAIL: constitution restricted to TA indicators,
not allowing mathematical analysis from raw data. → Gen3 created to fix this.

### Gen3 + Failure Report — ONLINE (đọc 2026-03-21)

> **⚠️ Framing**: Gen3 là framework ONLINE (AI chat). Failure modes là evidence
> về vấn đề chung (zero-trade trap, MDD cap, etc.) nhưng GIẢI PHÁP gen4 cho những
> vấn đề này là online-specific. Alpha-Lab cần giải pháp offline riêng.

| Tài liệu | Dùng cho | Mức độ |
|-----------|----------|--------|
| `report/governance_failure_dossier.md` | 4 structural gaps in v3 constitution — zero-trade trap, MDD cap, sub-hourly guidance, ablation revision | **Đọc toàn bộ** |
| `report/state_pack_v1/session_summary.md` | V1 outcome: NO_ROBUST_CANDIDATE | **Đọc toàn bộ** |
| `core/KIT_REVIEW_AND_FIXLOG_EN.md` | 18 fixes from v3→v4: seed/forward separation, forward decision law, cumulative evidence, state handoff, schema consistency, review cadence, hard constraint relaxation, upload discipline, packaging, session boundaries, + 8 post-v4 fixes | **Đọc toàn bộ** |
| `core/README_EN.md` | v4 operating model, version lineage, redesign guardrails, complexity caps | **Đọc toàn bộ** |
| `guide/USER_GUIDE_VI.md` | 6 session modes (S1/S2/M1-M4), workflow checklists, decision logic | **Đọc toàn bộ** |

**Output**: 1 new finding (F-19) imported into Topic 000. Gen3→gen4 evolution is the
**only empirical case study** of structured ONLINE framework failure on BTC/USDT.

**Key insights from gen3 failure** (vấn đề chung, giải pháp phải khác cho offline):
1. **Zero-trade trap**: Percentile-rank calibration without minimum-activity constraint → 0 entries OOS.
   Online: AI chọn threshold cao → Offline: exhaustive scan cover ALL thresholds tự động.
2. **MDD cap too tight**: BTC spot swing rejected at 45% cap (ablation 46.3%).
   Domain knowledge, paradigm-independent → Alpha-Lab có thể adopt.
3. **Sub-hourly slot waste**: 15m failed ALL cost levels — WFO survival ≠ measurement significance.
   Online: AI chiếm candidate slot → Offline: scanner quét mọi timeframe, không "chiếm slot."
4. **No ablation revision**: Designs frozen at D1c with no revision path.
   Online: protocol text cấm → Offline: ablation là automatic pipeline stage.

**Key insight from gen3→gen4 evolution**:
- Gen4 added: version lineage model (`system_version_id`), redesign guardrails (trigger + cooldown + dossier), complexity caps (max 3 layers, max 4 tunables), evidence clock reset semantics
- Gen4 fixed: seed/forward evidence separation, cumulative decision basis, MDD cap 35%→45%, entries floor 8→6/yr
- Gen4 kept: open search space, contamination firewall, state pack handoff, paired bootstrap

### Phase 0 evidence — V4 protocol + changelogs + Clean OOS (đọc 2026-03-21)

> **⚠️ Framing**: Tất cả tài liệu dưới đây là từ framework ONLINE (gen1, V4→V7).
> Dùng để hiểu EVOLUTION PATTERN, không copy giải pháp.

| Tài liệu | Kích thước | Dùng cho | Mức độ |
|-----------|-----------|----------|--------|
| V4 protocol (`RESEARCH_PROMPT_V4.md`) | 271 dòng | Gốc triết lý: first-principles, 7 phases, 2-zone split | **Đọc toàn bộ** |
| Clean OOS V1 (`PROMPT_FOR_V[n]_CLEAN_OOS_V1.md`) | 109 dòng | Bản gốc: 4 deliverables, basic archive/append | **Đọc toàn bộ** |
| Clean OOS V2 (`PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`) | 257 dòng | Bản nâng cấp: dynamic boundary, manifest, inconclusive, 11 checks | **Đọc toàn bộ** |
| Changelog V4→V5 (`CHANGELOG_V4_TO_V5.md`) | 30 changes | Critical innovation: 3-zone, evidence labels, search ladder, meta-knowledge | **Đọc toàn bộ** |
| Changelog V5→V6 (`CHANGELOG_V5_TO_V6.md`) | 24 changes | Provenance control + auditability | **Đọc toàn bộ** |
| Changelog V6→V7 (`CHANGELOG_V6_TO_V7.md`) | 22 changes | Convergence audit + finality | **Đọc toàn bộ** |

**Output**: Không có finding mới — 29 findings hiện tại đã cover. Bổ sung evidence
cho F-01, F-03, F-04, F-05, F-12. Key insights ghi tại §2.7→§2.12 bên dưới.
**Phase 0 status: DONE** — evidence cho topic 000 đã đủ.

### Trước đó (2026-03-18)

| Tài liệu | Kích thước | Dùng cho | Mức độ |
|-----------|-----------|----------|--------|
| V6 protocol | 447 dòng | Protocol stages, philosophy | Đọc meta-knowledge section |
| V7 protocol | 586 dòng | Meta-knowledge evolution | Đọc meta-knowledge section |
| V6 handoff | 111 dòng | Transfer rules | Trích dẫn |
| V7 handoff | 176 dòng | Transfer rules | Trích dẫn |
| Convergence V2 | 162 dòng | Divergence evidence | Trích dẫn qua PLAN.md |
| V6 research spec | 1193 dòng | Design patterns | **Phân tích cấu trúc** (via agent) |
| V6 system spec | 608 dòng | Frozen system format | **Phân tích cấu trúc** (via agent) |
| V7 research spec | 746 dòng | Design patterns | **Phân tích cấu trúc** (via agent) |
| V7 system spec | 376 dòng | Frozen system format | **Phân tích cấu trúc** (via agent) |

**Output**: 9 design patterns + 9 gaps → `docs/v6_v7_spec_patterns.md`

---

## 2. Key findings từ V8 resource (2026-03-19)

### 2.1 V8 frozen winner: S_D1_TREND — hoàn toàn khác V7

V8 winner là `D1_MOM_RET(n=40) > 0` — hệ thống đơn giản nhất có thể:
- 1 feature, 1 parameter (n=40), 0 calibration từ data
- Native D1, không cross-timeframe, không layering
- Sign threshold (> 0), không train_quantile

So sánh với V7 winner `S_D1_VOLCL5_20_LOW_F1` (D1 volatility clustering):
- Cùng là D1-only single-feature, nhưng **khác family** hoàn toàn
- V8 = momentum/trend, V7 = volatility clustering
- **Exact winner instability tiếp tục** ngay cả ở V8

**Relevance cho x38**: Xác nhận finding trong CONVERGENCE_STATUS_V3:
"có hội tụ ở cấp family (D1 slow), chưa hội tụ ở cấp exact winner"

### 2.2 Layered systems definitively eliminated

V8's paired bootstrap eliminated ALL layered alternatives:
- `S_D1_TREND` vs `L2_D1_TREND_AND_H4_VOLQUIET`: P=0.985, point diff +0.00114/day
- `S_D1_TREND` vs `L2_D1_VOLHIGH_AND_H4_PULLBACK`: P=0.990, point diff +0.00149/day

Three-layer candidates all dropped: third layer didn't beat two-layer core.
Consistent with V7 and btc-spot-dev X12-X31 findings.

### 2.3 SPEC_REQUEST_PROMPT — new document type

V8 introduces a **meta-prompt for spec generation** (263 lines) not present in V6/V7.
It specifies what the research spec and system spec MUST contain, with:
- Mandatory requirements per section
- Explicit numeric verification targets
- Artifact cross-reference checklist (10 items)

**Relevance cho x38 topic 003 (Protocol Engine)**: This is a reusable pattern —
alpha-lab could have a "deliverable template engine" that generates these meta-prompts
based on what was actually discovered.

### 2.4 spec_1: Input → Logic → Output → Decision structure

V8's research reproduction spec (866 lines) is significantly more structured than V6/V7:
- Every step has explicit Input → Logic → Output → Decision Rule
- 18 numbered steps covering full pipeline
- Exact numeric values for reproduction verification
- Artifact-grounded corrections (e.g., "29 candidates not 30" — correcting prose vs data)

**Relevance cho x38**: This is the most complete example of what a "campaign session
report" should look like. Alpha-lab's Protocol Engine should produce something like this
automatically from the session's artifacts.

### 2.5 Contamination Log V4 structure

8 rounds, 1692 lines. Structure:
1. Strict bottom line (no clean OOS remains)
2. Session-level summary table
3. Exact data-range usage per round
4. Union contamination map
5. Data-derived specifics per round (features, lookbacks, thresholds, winners)
6. Splits and contaminated ranges
7. Final same-file audit guidance vs true OOS
8. Practical conclusion

**Relevance cho x38 topic 002 (Contamination Firewall)**: This is the working template
for what the firewall needs to track. But it's manually written — alpha-lab needs to
automate this tracking.

### 2.6 Convergence Status V3 conclusions

Written in Vietnamese for human researcher. Key conclusions:
- **Family convergence**: D1 slow signals consistently strong across V4→V7
- **Exact divergence**: Each session freezes a different exact winner
- **No clean OOS**: Entire file contaminated after 8 rounds
- **V8 value**: convergence audit only, not scientific proof
- **Resolution requires**: genuinely appended new data

---

### 2.7 V4 protocol — philosophical anchor (Phase 0, 2026-03-21)

V4 (271 dòng) là biểu hiện tinh khiết nhất của triết lý "first principles":
- 7 phases tuần tự, 2-zone split (dev + holdout), 8 mandatory evaluations
- **"Novelty has no intrinsic value. Familiarity has no intrinsic cost."** (line 42-43)
- **"How to Use Prior Research"** (line 209-222): earliest formulation of meta-knowledge
  rules — may use as context, may NOT use as proof/prohibition. Trở thành Fresh
  Re-derivation Rules trong V5+.
- Benchmark appendix embedded trong cùng file (bị remove ở V5 vì anchoring risk)
- Không có: contamination accounting, provenance control, evidence labels, complexity budget

**Relevance cho x38**: V4 là BASELINE. Alpha-Lab phải preserve V4's philosophy
(evidence over novelty, strict evaluation, no post-hoc changes) while adding
governance. Mất V4 philosophy = mất lý do tồn tại.

### 2.8 V4→V5 changelog — critical innovation point (Phase 0, 2026-03-21)

**30 changes** (10 FIX, 9 NEW, 4 IMPROVE, 2 REMOVE) — bước nhảy lớn nhất trong lịch sử.

Core concepts introduced in V5:
- 3-zone split (discovery, selection holdout, reserve) — từ V4's 2-zone
- Evidence labels: CLEAN_OOS_CONFIRMED, INTERNAL_ROBUST_CANDIDATE, NO_ROBUST_IMPROVEMENT
- Search ladder: raw measurement → single-feature → orthogonal shortlist → layered → refinement
- Fresh Re-derivation Rules section (anti-leakage before any priors)
- Meta-knowledge section (principles only, no specifics)
- Complexity budget (layer count + tunable count)
- Candidate-freeze requirement with exact serialization
- Benchmark headline figures REMOVED from prompt (anti-anchoring)

**Relevance cho x38 F-05 (Protocol Engine)**: V5 innovations = MINIMUM feature set
cho Alpha-Lab pipeline. Mỗi V5 concept → automated pipeline stage.

### 2.9 V5→V6 changelog — provenance response (Phase 0, 2026-03-21)

**24 changes**. Triggered by V5 session cho thấy imported artifacts contaminate
"independent" re-derivation.

Key additions:
- Admissible inputs lock: only prompt + raw data before freeze
- Provenance log mandatory (any disallowed access invalidates "clean" status)
- Current-session table generation rule (no reproduced tables from prior sessions)
- Machine-readable Stage 1 registry (exact replay, not reconstruction)
- Stage 3: layering = "hypothesis, not destination" (explicit anti-bias)
- Frozen comparison-set ledger (serialized, not narrative)

**Relevance cho x38 F-04 (Contamination Firewall)**: V6's provenance control is the
closest online analogue to Alpha-Lab's machine-enforced firewall. Key difference:
V6 relies on text instructions → Alpha-Lab enforces via filesystem.

### 2.10 V6→V7 changelog — finality recognition (Phase 0, 2026-03-21)

**22 changes**. V7 repositioned as "final same-file convergence audit."

Key additions:
- **"Later same-file work is not automatically better"** — chronological bias guard
- Session-finality statement + stop condition for methodology iteration
- V7 split declared FINAL for this data file
- Quarterly discovery folds (vs semiannual in V6) — denser unseen slicing
- 3-substage candidate selection (5A/5B/5C: freeze → holdout → pre-reserve)
- Pairwise comparison matrix format (structured, not narrative)
- Anti-pattern: **prompt editing itself as hidden optimization surface**

**Relevance cho x38**: V7's finality concept maps directly to Alpha-Lab's
meta-updater problem. Methodology iteration = search dimension. Alpha-Lab's
meta-updater must also recognize its own iteration as optimization risk.

### 2.11 Clean OOS V1→V2 evolution (Phase 0, 2026-03-21)

**V1** (post-V5, 109 dòng): Basic concept — 4 deliverables, "data after current file
end", 9-item checklist.

**V2** (post-V7, 257 dòng): Significantly more rigorous — adds:
- Dynamic boundary (infer from files, not hardcoded date)
- Package manifest template (filename, role, timeframe, row count, timestamps, hash)
- Explicit verification steps (schema match, timezone, no overlap/gap)
- **INCONCLUSIVE handling** (underpowered reserve → honest label, not overclaim)
- Contamination precautions (no preview, no chart-inspect, no backtest of append data)
- 11-item final checklist (vs 9 in V1)

**Relevance cho x38 F-12, F-21, F-24**: V2's level of rigor is the target for
Alpha-Lab's Clean OOS module. Every V2 check → automated verification step.
F-21 (INCONCLUSIVE) and F-24 (power rules) already capture the key additions.

### 2.12 Governance accumulation pattern — quantitative (Phase 0, 2026-03-21)

| Version | Protocol lines | Changes from prior | FIX+IMPROVE | NEW | REMOVE |
|---------|---------------|-------------------|-------------|-----|--------|
| V4 | 271 | (baseline) | — | — | — |
| V5 | ~400 | 30 | 14 | 9 | 2 |
| V6 | 447 | 24 | 15 | 7 | 1 |
| V7 | 586 | 22 | 11 | 9 | 2 |
| V8 | 643 | 16 | 11 | 3 | 2 |

**Pattern**: Governance monotonically increases. REMOVE is rare (2/30 in V5, 1/24 in
V6, 2/22 in V7, 2/16 in V8). Each version primarily tightens, rarely loosens.

**Direct evidence for MK-02 (topic 004)**: Governance ratchet is quantitatively
observable across all 4 evolution steps. This is the online evidence for the
"implicit disfavor" problem described in PLAN.md §1.4.1.

---

## 3. Chưa khai thác — cần đọc trước debate

### Topic 000 (framework architecture, index) — **SPLIT** (2026-03-22)

Tất cả evidence cần thiết đã đọc (Phase 0 hoàn tất 2026-03-21). Topic 000
đã SPLIT thành 11 sub-topics (2026-03-22). Convergence notes (C-01→C-12) giữ
tại `debate/000-framework-proposal/findings-under-review.md`.

### Topic 004 (meta-knowledge) — **CLOSED** (2026-03-21), 6 rounds, 23/23 resolved

V8 changelog confirms maturity pipeline pattern. No new blocking evidence needed.

**Pre-debate inputs (2026-03-19)**:
- `debate/004-meta-knowledge/input_solution_proposal.md` — Policy Object Model (12 phần, từ human researcher)
- `debate/004-meta-knowledge/input_proposal_critique.md` — 6 vấn đề cần debate (từ claude_code)
- Cả hai là debate input, không phải kết luận.

### Topic 001 (campaign model) — **CLOSED** (2026-03-23, 6 rounds, 3/3 resolved)

| Tài liệu | Kích thước | Tại sao cần | Status |
|-----------|-----------|-------------|--------|
| Convergence V1 | 144 dòng | Divergence V4+V5 | Chưa đọc (archive gap, không blocking sau closure) |
| Convergence V2 | 162 dòng | Divergence V4+V5+V6 | Chưa đọc (archive gap, không blocking sau closure) |
| Convergence V3 | 187 dòng | V4→V7 (mới nhất) | **ĐÃ ĐỌC** (2026-03-19) — đã dùng trong closure context |

**Used in final resolution / closure sync**:
- `docs/design_brief.md:96-118` được dùng để freeze campaign law:
  dataset cố định + protocol cố định + N sessions + convergence analysis +
  meta-knowledge output, và framing rằng same-data campaigns chủ yếu phục vụ
  `convergence_audit` hoặc `corrective_re_run`.
- `PLAN.md:500-506` được dùng để freeze same-data governance: explicit human
  override, mandatory purpose declaration, và rule rằng same-file tightening
  không tạo clean OOS evidence mới.
- `debate/015-artifact-versioning/findings-under-review.md:92-99` được dùng
  làm evidence-class input cho routing contract của D-16 (trade log / PnL /
  signals / ranking / verdict / no-impact).
- Extra-archive evidence thực sự được dùng trong closure context của Topic
  001: `RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` (divergence rationale),
  `PROMPT_FOR_V[n]_CLEAN_OOS_V1.md` + `PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md`
  (future-data boundary), `PROMPT_FOR_V7_HANDOFF.md` (same-file cap và
  reminder rằng same-file tightening không tạo clean OOS mới).

**Residual gaps after closure**:
- `Convergence V1` và `Convergence V2` chưa đọc cho Topic 001. Đây là gap về
  historical coverage, không phải blocking gap, vì `Convergence V3` là artifact
  tổng hợp mới nhất và D-16 đóng bằng Judgment call chứ không bằng empirical
  proof mới.
- Các bất định còn lại sau closure không thuộc evidence gap nội bộ của Topic
  001 nữa mà là cross-topic dependencies đã được owner rõ: 008 (identity
  schema), 003 (protocol content), 013 (numeric thresholds), 015 (evidence
  classes/invalidation scope), 016 (recalibration exceptions).

### Topic 002 (contamination firewall) — **CLOSED** (2026-03-25, Wave 2, 6 rounds)

| Tài liệu | Kích thước | Tại sao cần | Status |
|-----------|-----------|-------------|--------|
| Contamination Log V3 | 1191 dòng | 7 rounds | Chưa đọc |
| Contamination Log V4 | 1692 dòng | 8 rounds (mới nhất) | **Đọc cấu trúc** (2026-03-19) |

### Topic 003 (protocol engine) — **OPEN** (2026-03-22, Wave 3 — chờ 001+002+004)

| Tài liệu | Kích thước | Tại sao cần | Status |
|-----------|-----------|-------------|--------|
| V5 resource spec | 593 dòng | Thiếu serialization → bài học | Chưa đọc |
| V6 SPEC_REQUEST_PROMPT | ? dòng | Evolution baseline (V6→V7→V8 pattern) | Chưa đọc |
| V8 SPEC_REQUEST_PROMPT | 263 dòng | Meta-prompt pattern | **ĐÃ ĐỌC** (2026-03-19) |
| V8 spec_1 | 866 dòng | Best research reproduction spec | **ĐÃ ĐỌC** (2026-03-19) |
| V8 spec_2 | 372 dòng | Best system spec + test vectors | **ĐÃ ĐỌC** (2026-03-19) |

### Topic 005 (core engine design) — **OPEN** (2026-03-22, Wave 2)

Evidence chính là `v10/core/` (code). Không cần đọc thêm x37.

### Topic 006 (feature engine design) — **OPEN** (2026-03-22, Wave 2)

| Tài liệu | Kích thước | Tại sao cần | Status |
|-----------|-----------|-------------|--------|
| V6 feature registry | 2220 dòng | Feature manifest thực tế | Chưa đọc |
| V6 feature manifest JSON | 1382 dòng | Machine-readable version | Chưa đọc |
| V8 stage1_feature_registry.csv | 1.5MB | 1,234 feature configs (V8) | Noted |
| V8 frozen_stage1_feature_manifest.csv | ~200 dòng | 29 families (V8) | Noted |

### Topics 007-012 — 007 **CLOSED** (2026-03-23), 010 **CLOSED** (2026-03-25), 008-009/011-012 OPEN (Wave 2)

Các topic mới từ split. Evidence coverage chưa đánh giá riêng — sử dụng
evidence đã đọc từ Phase 0 (topic 000) làm baseline. Đánh giá bổ sung
khi debate từng topic bắt đầu. Xem `debate/debate-index.md` cho danh sách
findings phân bổ.

### Background (không blocking)

| Tài liệu | Kích thước | Status |
|-----------|-----------|--------|
| V0→V3 protocols | 655 dòng tổng | Chưa đọc |
| V5 protocol | 400 dòng | Chưa đọc |
| V1→V4 resource specs | ~3800 dòng tổng | Chưa đọc |

---

## 4. Insight: V lớn hơn có tốt hơn không?

**Đúng cho protocol design**: V8 > V7 > V6 về governance (lines: 643 > 586 > 447).

**Nhưng cho framework design, evolution pattern quan trọng hơn version cuối cùng**:

- V8 đã "sửa" nhiều vấn đề → nhìn V8 không thấy vấn đề gốc là gì
- **Changelogs** ghi lại: vấn đề gì → sửa bằng gì → kết quả ra sao
- **Contamination logs** ghi nhận: contamination xảy ra ở đâu, cơ chế nào
- **Convergence status** ghi nhận: sessions diverge như thế nào theo thời gian
- **Resource specs** (V6→V7→V8): evolution từ narrative → schema → input/logic/output/decision

Framework cần học từ **cả quá trình**, không chỉ sản phẩm cuối.

**V8 specific insight**: V8 đạt đỉnh governance nhưng winner (`S_D1_TREND`)
vẫn khác V7 (`S_D1_VOLCL5_20_LOW_F1`). Governance tốt hơn KHÔNG đảm bảo
convergence ở exact winner level. Đây là constraint cơ bản, không phải
governance failure.

---

## 5. Update log

| Date | Event |
|------|-------|
| 2026-03-18 | Initial coverage audit. V6/V7 spec patterns analyzed → `v6_v7_spec_patterns.md` |
| 2026-03-19 | Full V8 docs + resource read. 6 key findings documented (§2). Convergence V3 read for topic 001. CONTAMINATION_LOG_V4 structure read for topic 002. V8 spec patterns analyzed for topic 003. |
| 2026-03-21 | Gen4 (Research Operating Kit v4.0) full read via agent. 12 documents covering constitution, lifecycle, state pack, forward policy, redesign guardrails, semantic classification, session modes, upload matrix, and 4 prompt sequences (D/F/R/G). 5 new findings (F-13→F-17) imported into Topic 000. |
| 2026-03-21 | Gen2 README + fixlog read. Gen2 FAIL: TA-only restriction. Gen3 failure report + gen3→gen4 evolution read. F-19 updated with full gen2→gen3→gen4 lineage + self-correcting cycle. |
| 2026-03-21 | **Phase 0 DONE.** 6 docs read: V4 protocol (271 lines), Clean OOS V1 (109), V2 (257), Changelog V4→V5 (30 changes), V5→V6 (24), V6→V7 (22). No new findings — 29 existing cover all concepts. Key insights: V4 = philosophical anchor, V4→V5 = critical innovation point, governance ratchet quantified (271→643 lines, REMOVE rare). Evidence cho topic 000 đã đủ. |
