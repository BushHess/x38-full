# Design Patterns from V6/V7 Research Specs

**Purpose**: Tài liệu tham khảo cho debate — tổng hợp design patterns đã proven
từ V6 (ret168) và V7 (volcl5) research specs. Đây là evidence base, không phải
findings cần debate.

**Source files** (read-only, trong `research/x37/resource/gen1/`):
- V6: `v6_ret168/spec/BTCUSDT_V6_Research_Reproduction_Spec.md` (1193 dòng)
- V6: `v6_ret168/spec/BTCUSDT_S3_H4_RET168_Z0_System_Spec.md` (608 dòng)
- V7: `v7_volcl5/spec/research_reproduction_spec_v7.md` (746 dòng)
- V7: `v7_volcl5/spec/system_spec_S_D1_VOLCL5_20_LOW_F1.md` (376 dòng)

**Note**: V8 spec đã phát hành (2026-03-19):
- `v8_sd1trebd/spec/spec_1_research_reproduction_v8.md` (866 dòng)
- `v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md` (372 dòng)
- V8 spec patterns đã được phân tích trong `evidence_coverage.md` §2.

---

## 1. Tổng quan evolution V6 → V7

| Khía cạnh | V6 (ret168) | V7 (volcl5) | Hướng tiến hóa |
|-----------|-------------|-------------|-----------------|
| Tổ chức | Narrative-driven (prose mô tả bước) | Schema-first, audit-driven (bảng cấu trúc, gates số) | Narrative → Schema |
| Feature manifest | Inline markdown, per-family grids | Explicit table schema per bucket, centralized threshold-grid | Embedded → Centralized |
| Discovery folds | 6 semiannual | 14 quarterly | Coarse → Granular |
| Anomaly handling | Narrative per anomaly | Disposition register table | Prose → Structured table |
| Decision rules | "Materially positive advantage" | `p_mean_daily_gt0_min >= 0.70` | Qualitative → Numeric |
| Rebuild checklist | 7-item prose | 10-item with exact numeric gates | Prose → Verifiable |
| Redundancy audit | Cross-timeframe relationships | + Transported clone ρ audit | Partial → Complete |
| Freeze timing | After holdout | After discovery + holdout, before reserve | Late → Early |

**Kết luận**: V7 đi từ "document AI phải tuân thủ" → "specification máy có thể verify".
Alpha-lab cần tiếp tục hướng này: spec → executable code.

---

## 2. Nine design patterns

### P-01: Anomaly Disposition Register

**Source**: V7 §4
**Relevant cho**: Topic 000 (cross-cutting), Topic 003 (protocol engine)

V6 mô tả anomaly handling bằng prose rải rác. V7 tạo bảng cấu trúc:

```
anomaly_class          | deterministic_rule        | rule_details              | impact_on_scoring
nonstandard_bar_length | retained_exactly_supplied | raw-feed fidelity         | included_in_scoring
h4_timing_gap          | retained_exactly_supplied | native raw bars only      | included_in_scoring
duplicate_zero_dur     | retained_exactly_supplied | deleting changes alignment| included_in_audit
```

**Tại sao quan trọng**: Anomaly handling ẩn giấu là nguồn contamination — nếu
không có register, hai sessions có thể xử lý anomaly khác nhau mà không ai biết.

**Alpha-lab learning**: Framework cần tạo anomaly register tự động từ data audit
(Stage 2), locked trước Stage 3. Register là artifact bắt buộc cho phase gating.

---

### P-02: Feature Library Schema

**Source**: V7 §8
**Relevant cho**: Topic 006 (feature engine)

V6 mô tả features bằng prose tables inline. V7 dùng schema cố định per bucket:

```
Columns per bucket: feature_name | formula | lookbacks | threshold_modes_and_grid | tails
```

V7 tách threshold-grid ra centralized spec (§8.6) thay vì embed trong mỗi family:
```
Bounded families: {0.20, 0.30, 0.40, 0.60, 0.70, 0.80}
Unbounded families: fixed_zero only
```

V7 định nghĩa tail semantics: "high tail = long when feature >= threshold".

**Alpha-lab learning**: Feature engine cần:
- Schema cố định per bucket (không cho phép ad-hoc columns)
- Centralized threshold-grid (tách khỏi family definitions)
- Explicit tail semantics (machine-parseable, không prose)

---

### P-03: Bucket Summary Table

**Source**: V7 §10
**Relevant cho**: Topic 006 (feature engine)

Sau Stage 1 scan, V7 tạo summary per bucket:

```
bucket           | configs_scanned | configs_pass_gate | best_cagr | best_sharpe | best_config_id
native_d1        | 343             | 178               | ...       | ...         | ...
native_h4        | 349             | 55                | ...       | ...         | ...
cross_tf         | 68              | 6                 | ...       | ...         | ...
transported_d1h4 | 343             | 179               | ...       | ...         | ...
```

**Alpha-lab learning**: Bucket summary là artifact bắt buộc sau Stage 1 — cho
phép audit nhanh mà không cần đọc toàn bộ registry.

---

### P-04: Rebuild Checklist with Numeric Gates

**Source**: V7 §19
**Relevant cho**: Topic 003 (protocol engine), Topic 005 (core engine)

V6 rebuild checklist (7 items, prose):
- "Verify the discovery screening gate passes for the frozen system"

V7 rebuild checklist (10 items, numeric):
- "Stage 1 bucket pass counts are exactly 178/55/6/179"
- "Frozen comparison set contains exactly 10 candidates"
- "Holdout trade count for winner is exactly N"

**Alpha-lab learning**: Mọi checklist gate phải có expected numeric value.
Framework tự compute actual value và so sánh — pass/fail tự động.

---

### P-05: Numeric Meaningful-Advantage Rule

**Source**: V7 §14.4
**Relevant cho**: Topic 003 (protocol engine)

V6 decision rule: "if a more complex candidate does not show a **materially
positive** advantage over a simpler nearby rival, the simpler rival wins."

V7 codified: `p_mean_daily_gt0_min >= 0.70 AND (p_cagr_gt0_mean >= 0.70 OR
p_sharpe_gt0_mean >= 0.70)`.

**Tại sao quan trọng**: "Materially positive" là judgment call mỗi session.
`p >= 0.70` là gate máy có thể verify. Hai sessions dùng cùng rule → cùng
kết quả → reproducibility.

**Alpha-lab learning**: Mọi decision rule trong protocol phải có numeric
threshold. Prose descriptions chỉ là documentation, không phải enforcement.

---

### P-06: Freeze-Before-Reserve Discipline

**Source**: V7 §14-15
**Relevant cho**: Topic 003 (protocol engine)

**V6 sequence**: discovery → holdout → freeze → reserve
(Freeze sau khi đã thấy holdout results)

**V7 sequence**: discovery → freeze comparison set → holdout ranking →
pre-reserve leader declaration → reserve
(Freeze từ discovery only, holdout chỉ ranking, complexity rule chọn winner
trước reserve)

V7 nghiêm ngặt hơn: winner được chọn **trước** khi mở reserve. Reserve chỉ
là contradiction testing, không phải tie-breaking.

**Kết quả thực tế**: V6 frozen winner (S3_H4_RET168_Z0) trở thành negative
trên reserve (-5.75% CAGR, -0.042 Sharpe). Protocol cấm redesign → label vẫn
"INTERNAL ROBUST CANDIDATE" nhưng với contradiction evidence.

V7 frozen winner (S_D1_VOLCL5_20_LOW_F1) giữ positive trên reserve (+29.2%
CAGR, +0.979 Sharpe). Rival phức tạp hơn (L2_VOLCL_RANGE48_Q60) collapse
(-25.0% CAGR, -1.31 Sharpe) → vindicate complexity rule.

**Alpha-lab learning**: Freeze phải xảy ra **trước** reserve. Reserve chỉ để
confirm/contradict, KHÔNG để tie-break hay redesign. Nếu reserve contradicts,
record contradiction nhưng không thay winner.

---

### P-07: Cross-Timeframe Redundancy Audit

**Source**: V7 §9
**Relevant cho**: Topic 006 (feature engine)

V7 thêm "transported" bucket: clone toàn bộ D1 feature library sang H4 bars
(via backward as-of alignment), chạy Stage 1 scan, rồi tính correlation với
native D1 versions.

Ví dụ: V7 phát hiện ρ ≈ 0.999638 giữa native D1 volcluster và transported
clone → transported version KHÔNG thêm thông tin mới.

**Tại sao quan trọng**: Nếu không có redundancy audit, một feature "nhanh"
(H4) có thể trông mới nhưng thực ra chỉ là shadow của feature "chậm" (D1).
Session có thể nhầm redundancy thành genuine faster-timeframe information.

**Alpha-lab learning**: Feature engine phải tự động:
1. Clone slower-TF library sang faster-TF
2. Scan cả hai
3. Tính correlation matrix (native slower vs transported)
4. Flag high-ρ pairs as redundancy, not new information

---

### P-08: Clean Provenance Declaration

**Source**: V6 §24, V7 §1
**Relevant cho**: Topic 002 (contamination firewall), Topic 003 (protocol engine)

Cả V6 và V7 đều có explicit provenance declaration:

```
Admissible inputs before freeze:
  - RESEARCH_PROMPT_V[N].md
  - raw H4 CSV
  - raw D1 CSV

Forbidden before freeze:
  - prior reports
  - prior session logs
  - prior system specifications
  - prior JSON outputs
  - prior shortlist tables
  - benchmark specifications
  - any precomputed tables from earlier sessions

After freeze:
  - only own generated artifacts
```

V7 thêm: software versions (Python 3.13.5, pandas 2.2.3, numpy 2.3.5, scipy
1.17.0, matplotlib 3.10.8).

**Alpha-lab learning**: Framework cần:
- Tự động generate provenance declaration ở Stage 1 (protocol lock)
- Lock admissible input list trước discovery
- Record software versions (pip freeze output) vào protocol_freeze.json
- Verify at runtime: nếu code cố đọc file ngoài admissible list → fail

---

### P-09: Quarterly Fold Alignment

**Source**: V7 vs V6 fold structures
**Relevant cho**: Topic 003 (protocol engine)

V6: 6 semiannual folds (discovery) + 18-month holdout + 20-month reserve.

V7: 14 quarterly folds (discovery) + 5-quarter holdout + 6-quarter reserve.
Tất cả aligned theo quarters.

**Tại sao V7 tốt hơn**:
- Quarterly captures seasonal effects (BTC có seasonality rõ)
- Nhiều folds hơn → ít phụ thuộc vào 1 fold
- Isolation-quarter filter: reject configs dominated by 1 fold (column
  `largest_positive_fold_share` trong registry)
- Holdout/reserve cũng quarterly → consistent reporting

**Alpha-lab learning**: Fold structure nên configurable per campaign, nhưng
default = quarterly alignment. Isolation-quarter filter nên là default gate.

---

## 3. Gaps và thiếu sót phát hiện từ spec analysis

Những thứ V6/V7 specs **chưa có** mà alpha-lab cần bổ sung:

### G-01: Stochastic seed serialization

V6 ghi nhận: "RNG seed not serialized, so bootstrap p-values reproducible
methodologically but not bit-identical."

V7 không cải thiện điểm này.

V8 protocol (dòng 503) yêu cầu: "Every stochastic procedure that influences
selection must have its seed and configuration serialized."

**Gap**: Không spec nào thực sự implement seed serialization. Alpha-lab cần
enforce: seed frozen trước khi chạy bootstrap, lưu vào protocol_freeze.json.

### G-02: Machine-readable frozen spec

V6 xuất `frozen_system.json` (38 dòng) — tốt.
V7 KHÔNG xuất JSON tương đương — frozen spec nằm rải rác trong markdown.

**Gap**: Alpha-lab cần frozen_spec.json bắt buộc, machine-parseable, đủ để
replay system mà không cần đọc markdown.

### G-03: Pairwise comparison matrix format

V7 xuất `pairwise_comparison_matrix.csv` (17 dòng) — tốt nhưng format không
specified trước. Mỗi session có thể xuất format khác nhau.

**Gap**: Alpha-lab cần schema cố định cho pairwise matrix (columns, metrics,
p-value conventions). Locked trong protocol_freeze.json.

### G-04: Common daily-return alignment convention

V8 protocol (dòng 500-501) yêu cầu: "All candidate-to-candidate paired tests
must be performed on a common daily UTC return domain."

Nhưng V6 và V7 specs không describe cách align mixed-timeframe returns.

**Gap**: Alpha-lab cần explicit function: given H4 strategy returns + D1
strategy returns → aligned daily UTC returns for paired comparison.

### G-05: Segment trade-count convention

V8 protocol (dòng 502): "The segment trade-count convention must be locked
before scoring."

V6 và V7 không define: khi tính trades per segment (fold/holdout/reserve),
count bằng entry date hay exit date? Trades spanning segment boundaries?

**Gap**: Alpha-lab cần deterministic rule: trade counted in segment where
entry occurs (hoặc exit, hoặc proportional — nhưng phải locked trước scoring).

### G-06: Evidence label taxonomy

V6 label: "INTERNAL ROBUST CANDIDATE" (nhưng defined ad-hoc trong spec).
V7 label: same term, same ad-hoc definition.
V8 protocol formalizes 3 labels: CLEAN_OOS_CONFIRMED, INTERNAL_ROBUST_CANDIDATE,
NO_ROBUST_IMPROVEMENT.

**Gap**: V6/V7 specs không use V8's formal taxonomy. Alpha-lab cần enforce:
verdict.json phải chứa exactly one of 3 labels, machine-verifiable.

### G-07: Benchmark embargo enforcement

V6 §24: "No benchmark specification was supplied."
V7 §18: same.
V8 protocol (dòng 457-464): benchmark specs chỉ consult sau reserve evaluation.

**Gap**: Hiện tại benchmark embargo là prose rule. Alpha-lab cần: benchmark
specs physically inaccessible (chmod/path isolation) until after reserve
artifact exists.

### G-08: Cross-session convergence analysis

V6 và V7 specs mỗi cái là **independent session** — không có section nào
so sánh với sessions trước.

Convergence analysis chỉ tồn tại trong separate documents
(CONVERGENCE_STATUS.md, CONVERGENCE_STATUS_V2.md) viết bởi handoff prompt,
không phải bởi session.

**Gap**: Alpha-lab cần convergence analysis tự động: sau N sessions trong cùng
campaign, framework tự so sánh frozen winners, tính divergence metrics, và
output convergence_report.json.

### G-09: Meta-knowledge extraction

V6 và V7 specs không chứa section "lessons learned" hay "meta-knowledge output".
Meta-knowledge chỉ được trích xuất qua handoff prompts (human-mediated).

**Gap**: Alpha-lab cần: sau mỗi session close, framework auto-propose lessons
(dạng structured candidates), human review và approve. Xem Topic 004 (MK-08)
cho lifecycle design.

---

## 4. Cross-reference: patterns → debate topics

| Pattern/Gap | Topic 000 | Topic 001 | Topic 002 | Topic 003 | Topic 004 | Topic 005 | Topic 006 |
|-------------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| P-01 Anomaly register | x | | | x | | | |
| P-02 Feature schema | | | | | | | x |
| P-03 Bucket summary | | | | | | | x |
| P-04 Numeric rebuild gates | | | | x | | x | |
| P-05 Numeric advantage rule | | | | x | | | |
| P-06 Freeze-before-reserve | | | | x | | | |
| P-07 Redundancy audit | | | | | | | x |
| P-08 Provenance declaration | | | x | x | | | |
| P-09 Quarterly folds | | | | x | | | |
| G-01 Seed serialization | | | | x | | x | |
| G-02 Machine-readable frozen spec | | | | x | | x | |
| G-03 Pairwise matrix format | | | | x | | | |
| G-04 Daily-return alignment | | | | x | | x | |
| G-05 Trade-count convention | | | | x | | x | |
| G-06 Evidence label taxonomy | | | | x | | | |
| G-07 Benchmark embargo | | | x | x | | | |
| G-08 Convergence analysis | | x | | | | | |
| G-09 Meta-knowledge extraction | | | | | x | | |
