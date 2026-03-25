# X38 — Quy Tắc Nghiên Cứu

**Kế thừa**: [`CLAUDE.md`](../../CLAUDE.md) →
[`RESEARCH_RULES.md`](../../docs/research/RESEARCH_RULES.md) → file này.

---

## 1. Mục tiêu

X38 là nghiên cứu thiết kế — sản phẩm cuối cùng là **bản thiết kế kiến trúc**
(blueprint) cho framework offline nghiên cứu thuật toán, không phải code.

Sản phẩm chính: tài liệu đặc tả kiến trúc trong `published/`, được sản xuất
sau khi các tranh luận trong `debate/` đã hội tụ.

X38 **không viết code chạy được**. Code thuộc về project `alpha-lab` và chỉ bắt
đầu sau khi blueprint được xuất bản.

---

## 2. Write zone

```text
research/x38/**/*
```

Không ngoại lệ. X38 không sửa bất kỳ file nào ngoài `research/x38/`.

---

## 3. Cấu trúc thư mục

```text
research/x38/
├── AGENTS.md                   ← hướng dẫn bắt đầu cho agent mới
├── PLAN.md                     ← master plan + topic registry
├── x38_RULES.md                ← file này
├── docs/                       ← tài liệu tham khảo nội bộ (input cho debate)
│   ├── online_vs_offline.md    ← phân biệt Online (gen1-4) vs Offline (Alpha-Lab) — BẮT BUỘC đọc trước
│   ├── design_brief.md         ← tóm tắt thiết kế đã thống nhất sơ bộ
│   ├── evidence_coverage.md    ← tracker: x37 docs đã đọc vs chưa đọc per topic
│   └── v6_v7_spec_patterns.md  ← 9 patterns + 9 gaps từ V6/V7/V8 specs
├── debate/                     ← tranh luận kiến trúc
│   ├── README.md
│   ├── rules.md                ← quy tắc tranh luận (kế thừa + sửa từ x34)
│   ├── prompt_template.md      ← mẫu prompt cho các vòng
│   ├── debate-index.md         ← chỉ mục toàn cục
│   └── NNN-slug/               ← mỗi topic một thư mục
│       ├── README.md
│       ├── findings-under-review.md
│       ├── input_*.md            ← pre-debate input (solution proposals, critiques)
│       ├── final-resolution.md   ← tạo khi mọi issue đã chốt
│       ├── codex/round-N_*.md
│       └── claude_code/round-N_*.md
├── drafts/                     ← bản nháp spec (trước khi publish)
│   └── README.md
└── published/                  ← đặc tả chính thức (sau khi debate chốt)
    └── README.md
```

---

## 4. Workflow

```text
       docs/design_brief.md (input)
                │
                ▼
    debate/NNN-slug/ (tranh luận từng topic)
                │
                ▼  (khi topic hội tụ)
       drafts/ (soạn spec section)
                │
                ▼  (khi tất cả topics xong)
     published/ (xuất bản đặc tả chính thức)
```

**Quy tắc xuất bản**:
- Chỉ chuyển từ `drafts/` sang `published/` khi TẤT CẢ debate topics liên quan
  đã có status `CLOSED` (mọi issue Converged hoặc Judgment call).
- `published/` là read-only sau khi xuất bản. Sửa đổi phải mở topic mới.
- Bản nháp trong `drafts/` được phép sửa tự do trong quá trình debate.

### Source of truth precedence

| Tầng | Tài liệu | Authority |
|------|-----------|-----------|
| 1 (cao nhất) | `published/` | Spec chính thức cuối cùng. Read-only sau xuất bản. |
| 2 | `debate/NNN-slug/` (topic dir) | Authoritative cho topic đã tách. Thắng PLAN.md và design_brief cho topic tương ứng. |
| 3 | `docs/design_brief.md` | Authoritative input cho debate. Thắng PLAN.md nếu mâu thuẫn. Không phải final spec. |
| 4 | `PLAN.md` | Orchestration, context, narrative. Subordinate to design_brief + debate findings. |

Khi chưa có gì trong `published/`, authority cao nhất là topic dir (nếu topic đã tách)
hoặc design_brief (nếu chưa tách).

---

## 5. Participants

| Agent | Vai trò | Thế mạnh |
|-------|---------|----------|
| `claude_code` | Architect + opening critic | Đã thiết kế sơ bộ; hiểu btc-spot-dev sâu |
| `codex` | Reviewer + adversarial critic | Fresh perspective; phản biện thiết kế |

Cả hai đều có quyền truy cập read-only vào:
- `research/x37/` (x37 resource, docs, rules — frozen research)
- `research/x34/` (mẫu debate)
- `docs/research/RESEARCH_RULES.md`
- `v10/core/` (reference cho engine design)
- `CLAUDE.md`

---

## 6. Quy tắc tranh luận

Kế thừa toàn bộ `debate/rules.md` (adapted từ x34 cho context kiến trúc).

Bổ sung riêng cho x38:

1. **Evidence type mở rộng**: Ngoài empirical evidence từ project, chấp nhận:
   - Software engineering principles (SOLID, separation of concerns, ...)
   - Prior art từ quantitative finance frameworks
   - Lessons learned từ V4→V8/x37 (principle-level, không specifics)
   - Mathematical argument về contamination/independence

2. **No code in debate**: Debate dùng pseudocode hoặc interface description.
   Không viết implementation code — đó là việc của alpha-lab project.

3. **Topic scope**: Mỗi topic tương ứng một **quyết định kiến trúc** cụ thể.
   Không tranh luận feature names, lookbacks, hay trading specifics.

4. **Decision owner mặc định**: human researcher (người duy trì project).

5. **Nhãn `extra-archive`**: Evidence pointer trỏ tới file ngoài `research/x38/`
   phải gắn nhãn `[extra-archive]`. Xem `debate/rules.md` §18 cho chi tiết.

---

## 7. Tài liệu tham khảo (read-only inputs)

| Tài liệu | Path | Dùng cho |
|-----------|------|----------|
| V4 protocol | `x37/docs/gen1/RESEARCH_PROMPT_V4.md` | Base protocol |
| V6 protocol | `x37/docs/gen1/RESEARCH_PROMPT_V6/RESEARCH_PROMPT_V6.md` | Protocol stages |
| V6 handoff | `x37/docs/gen1/RESEARCH_PROMPT_V6/PROMPT_FOR_V6_HANDOFF.md` | Meta-knowledge transfer |
| V6 convergence | `x37/docs/gen1/RESEARCH_PROMPT_V6/CONVERGENCE_STATUS.md` | Divergence evidence (V4+V5) |
| V6 contamination | `x37/docs/gen1/RESEARCH_PROMPT_V6/CONTAMINATION_LOG_V2.md` | Contamination patterns (6 rounds) |
| V7 protocol | `x37/docs/gen1/RESEARCH_PROMPT_V7/RESEARCH_PROMPT_V7.md` | Final same-file convergence audit |
| V7 handoff | `x37/docs/gen1/RESEARCH_PROMPT_V7/PROMPT_FOR_V7_HANDOFF.md` | Contamination isolation |
| V7 convergence | `x37/docs/gen1/RESEARCH_PROMPT_V7/CONVERGENCE_STATUS_V2.md` | Divergence evidence (V4+V5+V6) |
| V7 contamination | `x37/docs/gen1/RESEARCH_PROMPT_V7/CONTAMINATION_LOG_V3.md` | Contamination patterns (7 rounds) |
| V7 changelog | `x37/docs/gen1/RESEARCH_PROMPT_V7/CHANGELOG_V6_TO_V7.md` | V6→V7 changes |
| Clean OOS V1 | `x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V1.md` | Future data handling (original) |
| Clean OOS V2 | `x37/docs/gen1/RESEARCH_PROMPT_V[n]/PROMPT_FOR_V[n]_CLEAN_OOS_V2[en].md` | Future data handling (latest) |
| X37 rules | `x37/x37_RULES.md` | Session isolation model |
| V8 protocol | `x37/docs/gen1/RESEARCH_PROMPT_V8/RESEARCH_PROMPT_V8.md` | Most refined protocol (643 lines) |
| V8 handoff | `x37/docs/gen1/RESEARCH_PROMPT_V8/PROMPT_FOR_V8_HANDOFF.md` | Handoff + isolation rules |
| V8 convergence | `x37/docs/gen1/RESEARCH_PROMPT_V8/CONVERGENCE_STATUS_V3.md` | Divergence (V4+V5+V6+V7) |
| V8 contamination | `x37/docs/gen1/RESEARCH_PROMPT_V8/CONTAMINATION_LOG_V4.md` | Contamination patterns (8 rounds) |
| Changelogs | `x37/docs/gen1/RESEARCH_PROMPT_V*/CHANGELOG_*.md` | Evolution V4→V5→V6→V7→V8 |
| V5 resource | `x37/resource/gen1/v5_sfq70/` | Frozen research example (thiếu serialization) |
| V6 resource spec | `x37/resource/gen1/v6_ret168/spec/` | Frozen spec (narrative-driven) |
| V6 resource data | `x37/resource/gen1/v6_ret168/research/` | Feature registry 2220 rows, outputs |
| V7 resource spec | `x37/resource/gen1/v7_volcl5/spec/` | Frozen spec (schema-first, audit-driven) |
| V7 resource data | `x37/resource/gen1/v7_volcl5/research/` | Feature manifest, audit tables |
| Spec request V6 | `x37/docs/gen1/RESEARCH_PROMPT_V6/SPEC_REQUEST_PROMPT.md` | Deliverable format (V6, baseline) |
| Spec request V7 | `x37/docs/gen1/RESEARCH_PROMPT_V7/SPEC_REQUEST_PROMPT.md` | Deliverable format (V7) |
| Spec request V8 | `x37/docs/gen1/RESEARCH_PROMPT_V8/SPEC_REQUEST_PROMPT.md` | Deliverable format (V8, latest, 263 lines) |
| V8 resource spec_1 | `x37/resource/gen1/v8_sd1trebd/spec/spec_1_research_reproduction_v8.md` | Best research reproduction spec (866 lines, Input→Logic→Output→Decision) |
| V8 resource spec_2 | `x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md` | Bit-level system spec + test vectors (372 lines) |
| V8 frozen system | `x37/resource/gen1/v8_sd1trebd/research/config/frozen_system.json` | Frozen winner S_D1_TREND complete spec |
| V8 provenance | `x37/resource/gen1/v8_sd1trebd/research/config/provenance_declaration.json` | Independence claims pattern |
| V8 feature registry | `x37/resource/gen1/v8_sd1trebd/research/data/stage1_feature_registry.csv` | 1,234 feature configs |
| Gen2 README | `x37/docs/gen2/core/README_EN.md` | v2 operating model (TA-only, FAILED) |
| Gen2 fixlog | `x37/docs/gen2/core/KIT_REVIEW_AND_FIXLOG_EN.md` | 10 fixes gen1→gen2 |
| Gen3 constitution | `x37/docs/gen3/core/research_constitution_v3.0.yaml` | Framework v3 rules |
| Gen3 failure dossier | `x37/docs/gen3/report/governance_failure_dossier.md` | 4 structural gaps (empirical) |
| Gen3 session summary | `x37/docs/gen3/report/state_pack_v1/session_summary.md` | NO_ROBUST_CANDIDATE outcome |
| Gen3 report artifacts | `x37/docs/gen3/report/gen3_report/` | WFO, measurements, candidates |
| Gen3→Gen4 fixlog | `x37/docs/gen4/core/KIT_REVIEW_AND_FIXLOG_EN.md` | 18 fixes (v3→v4 evolution) |
| Gen4 README | `x37/docs/gen4/core/README_EN.md` | v4 operating model + guardrails |
| Gen4 user guide | `x37/docs/gen4/guide/USER_GUIDE_VI.md` | Workflow + session modes |
| X34 debate | `x34/debate/` | Debate structure reference |
| **Spec patterns** | **`x38/docs/v6_v7_spec_patterns.md`** | **9 patterns + 9 gaps from V6/V7 specs** |
| **Evidence coverage** | **`x38/docs/evidence_coverage.md`** | **Tracks which x37 docs read vs unread per topic** |

---

## 8. Checklist

- [ ] Mọi file chỉ nằm trong `research/x38/`
- [ ] Debate tuân thủ `debate/rules.md`
- [ ] Không viết implementation code (chỉ pseudocode/interface)
- [ ] Debate không đề cập feature names, lookbacks, thresholds cụ thể
- [ ] Mỗi topic có `findings-under-review.md` trước khi debate sâu
- [ ] Draft chỉ chuyển sang published khi debate topics liên quan đã CLOSED
