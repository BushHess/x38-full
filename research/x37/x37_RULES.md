# X37 — Session Isolation Rules

**Kế thừa**: [`../../CLAUDE.md`](../../CLAUDE.md) →
[`../../docs/research/RESEARCH_RULES.md`](../../docs/research/RESEARCH_RULES.md) →
file này.

---

## 1. Write Zone

Write zone của `x37` là:

```text
research/x37/README.md
research/x37/PLAN.md
research/x37/manifest.json
research/x37/x37_RULES.md
research/x37/shared/**/*
research/x37/sessions/README.md
research/x37/sessions/SESSION_TEMPLATE.md
research/x37/sessions/PROTOCOL_FREEZE_TEMPLATE.json
research/x37/sessions/sNN_*/**/*
research/x37/analysis/**/*
research/x37/code/**/*
research/x37/results/**/*
```

Không có ngoại lệ ra ngoài `research/x37/`.

## 2. Read-Only Subtrees

Các path sau là frozen inputs, **không được sửa**:

```text
research/x37/docs/gen1/**/*
research/x37/resource/gen1/**/*
```

Chỉ session đã đóng mới trở thành read-only:

```text
research/x37/sessions/sNN_*/**/*
```

Session `PLANNED` vẫn writable. Session chỉ bị freeze khi status là `DONE` hoặc
`ABANDONED`.

## 3. Architecture

```text
x37/
├── README.md
├── PLAN.md
├── manifest.json
├── x37_RULES.md
├── docs/
│   ├── gen1/               # frozen prompt history (V0-V8)
│   └── gen2/               # new generation prompts
├── resource/
│   ├── gen1/               # frozen prior discovery runs (v1-v8)
│   └── gen2/               # new generation session outputs
├── shared/                 # reusable infrastructure only
├── sessions/
│   ├── README.md
│   ├── SESSION_TEMPLATE.md
│   ├── PROTOCOL_FREEZE_TEMPLATE.json
│   └── sNN_<descriptor>/
├── analysis/               # derivative work from completed sessions only
├── code/                   # root wrappers only
└── results/                # root index only
```

Rules:

1. `shared/` chỉ chứa infrastructure primitives.
2. `sessions/sNN_*/` tự chứa hypothesis, code, results, verdict của session đó.
3. `analysis/` chỉ chứa derivative comparison từ sessions đã hoàn thành.
4. Root `code/` là wrapper điều phối; root `results/` là index-only.
5. Không đặt loose phase docs hoặc canonical outputs ở root `x37/`.

## 4. Governance for `shared/`

`shared/` chỉ được chứa các primitives dùng lại giữa sessions:

- data loading / quarantine / alignment
- feature primitives
- backtest wrappers
- metrics
- bootstrap
- walk-forward helpers

Không được chứa:

- candidate strategy implementations
- frozen feature sets cho một hypothesis cụ thể
- threshold values hoặc decision logic đặc thù session
- benchmark-specific comparison logic

Khi extend `shared/`:

1. Giữ backward-compatible với API đã tồn tại.
2. Mọi bug fix phải rõ ràng và có test scope-local tương ứng.
3. Nếu logic chỉ có ý nghĩa trong một session, đặt trong session đó.
4. Nếu có nhiều session ACTIVE, session sửa `shared/` phải đọc kỹ thay đổi đang có
   và không ghi đè công việc của session khác.

## 5. Standard Session Layout

```text
sessions/sNN_<descriptor>/
├── PLAN.md
├── phase0_protocol/
│   └── protocol_freeze.json
├── phase1_decomposition/
│   ├── code/run_phase1.py
│   └── results/
│       ├── measurements.csv
│       ├── channel_report.md
│       ├── d1_h4_alignment.json
│       └── figures/
├── phase2_hypotheses/
│   └── hypotheses.md
├── phase3_design/
│   ├── code/
│   │   ├── candidates/
│   │   └── run_phase3.py
│   └── results/
├── phase4_parameters/
│   ├── code/run_phase4.py
│   └── results/
│       ├── search_results.csv
│       └── plateau_test.csv
├── phase5_freeze/
│   ├── frozen_spec.md
│   ├── frozen_spec.json
│   ├── code/run_phase5.py
│   └── results/
│       ├── holdout_results.csv
│       ├── regime_decomposition.csv
│       ├── cost_sensitivity.csv
│       ├── bootstrap_summary.csv
│       ├── trade_distribution.csv
│       └── figures/
├── phase6_benchmark/
│   ├── code/run_phase6.py
│   └── results/
│       ├── benchmark_comparison.csv
│       └── paired_bootstrap.csv
└── verdict/
    ├── final_report.md
    ├── verdict.json
    └── figures/
```

`sessions/README.md` là quick-start. `sessions/SESSION_TEMPLATE.md` là pure PLAN
template. Không nhét quick-start instructions vào chính `PLAN.md` của session.

**Verdict authority**: `verdict/verdict.json` là authoritative (machine-readable).
`verdict/final_report.md` là human-readable companion. Verdict block trong session
`PLAN.md` là mirror — ghi sau khi `verdict/verdict.json` đã có, không ngược lại.

## 6. Session Lifecycle

Status hợp lệ:

```text
PLANNED -> ACTIVE -> DONE | ABANDONED
```

- `PLANNED`: session tree + PLAN.md đã có, chưa chạy phase code.
- `ACTIVE`: đang chạy phases.
- `DONE`: verdict đã phát hành (`SUPERIOR`, `COMPETITIVE`, hoặc `NO_ROBUST_IMPROVEMENT`).
- `ABANDONED`: dừng vì dead-end hoặc protocol constraint.

Mọi session đều phải được đăng ký đồng thời ở:

- root `README.md`
- root `PLAN.md`
- `manifest.json`

`manifest.json` là source of truth. `README.md` và `PLAN.md` chỉ là mirrors.

Root `study_status` chỉ có 2 trạng thái hợp lệ:

- `READY_NO_ACTIVE_SESSIONS`: không có session `ACTIVE`
- `ACTIVE_SESSIONS_PRESENT`: có ít nhất 1 session `ACTIVE`

Mỗi entry trong `manifest.sessions[]` phải có tối thiểu các field:

- `id`
- `path`
- `status`
- `agent`
- `prompt_version`
- `started_at`
- `phase_reached`
- `verdict`
- `notes`

## 7. Phase Gating and Execution Guardrails

### 7.1 Sequential gating

- Chỉ bắt đầu Phase `N+1` khi outputs tối thiểu của Phase `N` đã tồn tại.
- Phase 5 là checkpoint bất khả đảo ngược.
- Appendix A chỉ được coi là unlocked sau khi toàn bộ Phase 5 outputs bắt buộc đã ghi.
- Trong `manifest.json`, mỗi phase phải khai báo tách bạch:
  - `prerequisites`: artifacts phải có trước khi phase chạy
  - `required_artifacts`: outputs canonical mà phase đó phải tạo ra
  - `blocking_artifacts`: artifacts báo hiệu phase này không còn được rerun

### 7.2 Minimum gating evidence

| Phase to run | Prerequisite tối thiểu |
|--------------|------------------------|
| Phase 1 | `phase0_protocol/protocol_freeze.json` hợp lệ |
| Phase 3 | `phase2_hypotheses/hypotheses.md` đã tồn tại |
| Phase 4 | `phase3_design/results/` có artifact ngoài `figures/` |
| Phase 5 | `phase4_parameters/results/search_results.csv` và `plateau_test.csv` đã tồn tại |
| Phase 6 | `phase5_freeze/frozen_spec.md`, `phase5_freeze/frozen_spec.json` + toàn bộ Phase 5 mandatory outputs đã tồn tại |

### 7.3 Root runner semantics

`research/x37/code/run_all.py` phải tuân thủ:

1. Chỉ chạy **session ACTIVE**.
2. Chỉ chạy **một phase được chỉ định rõ** bằng CLI.
3. Không được auto-discover rồi auto-advance qua nhiều phase trong một invocation.
4. Phải chặn Phase 5 nếu freeze artifact đã tồn tại
   (`frozen_spec.md`, `frozen_spec.json`, hoặc holdout artifact).
5. Phải chặn Phase 6 nếu output benchmark hoặc `verdict/verdict.json` đã tồn tại.
6. Nếu Phase 5 hoặc Phase 6 đã bị chạm một phần, root wrapper không có authority để
   “resume”; phải có human review trước khi quyết định can thiệp thủ công.

Lý do: Phase 5/6 có authority đặc biệt; auto-rerun ở đây là lỗi phương pháp luận.

### 7.4 Phase 5 checkpoints

Phase 5 gồm 3 checkpoint tuần tự:

1. `frozen_spec.json` đã ghi.
2. Holdout results đã ghi.
3. Mandatory evals #2, #4, #5, #7a, #8 đã ghi.

Chỉ sau checkpoint 3 thì Appendix A mới được coi là unlocked.

## 8. Session Independence

- Session đang ACTIVE không được đọc results của session ACTIVE khác.
- Import giữa sessions là cấm.
- Session có thể đọc sessions đã `DONE` hoặc `ABANDONED` như weak prior nếu
  và chỉ nếu việc đó được khai báo rõ trong session `PLAN.md`.
- `analysis/` chỉ được dùng như derivative weak prior từ sessions đã hoàn tất;
  nếu dùng, phải ghi rõ trong `PLAN.md`.

## 9. Appendix A Embargo

Appendix A nằm cuối `docs/gen1/RESEARCH_PROMPT_V4.md`. Vì file prompt là frozen input,
agent có thể nhìn thấy benchmark numbers trong context.

Quy tắc bắt buộc:

1. Không dùng benchmark numbers cho Phase 2, 3, 4.
2. Không dùng benchmark architecture để suppress hoặc ưu tiên mechanism trước Phase 5 complete.
3. Nếu agent “đã thấy” benchmark numbers, vẫn phải coi chúng là embargoed cho đến
   khi Phase 5 mandatory outputs hoàn tất.

## 10. Abandon Criteria

Session chuyển sang `ABANDONED` khi gặp ít nhất một điều kiện:

1. Phase 1 cho thấy không có channel nào vượt noise floor trên unseen data.
2. Phase 3 không còn candidate nào survive component ablation.
3. Phase 4 không có broad plateau, chỉ còn sharp spikes.
4. Candidate duy nhất đã fail hard criteria và không còn backup candidate.
5. Tiếp tục chạy sẽ buộc phải vi phạm protocol hoặc post-hoc rationalize.

Khi abandon:

- ghi rõ lý do trong session `PLAN.md`
- ghi `verdict/verdict.json`
- cập nhật root `README.md`, `PLAN.md`, `manifest.json`
- đổi session status thành `ABANDONED`

## 11. D1-H4 Alignment Verification

D1-H4 alignment là nguồn lookahead dễ gặp nhất. Mỗi session phải:

1. Declare `allow_exact_matches` trong `PLAN.md` và `protocol_freeze.json`.
2. Giữ rule align nhất quán trong code.
3. Verify tự động trong Phase 1:
   - nếu `allow_exact_matches=true`: `d1_close_time <= h4_close_time`
   - nếu `allow_exact_matches=false`: `d1_close_time < h4_close_time`
4. Ghi verification result vào `phase1_decomposition/results/d1_h4_alignment.json`.

Artifact bắt buộc: `d1_h4_alignment.json` phải chứa tối thiểu:

```json
{
  "allow_exact_matches": true,
  "rule": "d1_close_time <= h4_close_time",
  "total_bars_checked": 12345,
  "violations": 0,
  "status": "PASS"
}
```

Không có `d1_h4_alignment.json` hợp lệ thì Phase 1 chưa hoàn thành.
Phase 3 trở đi sẽ bị chặn nếu thiếu file này.

## 12. Internal Imports

Ngoài các import chung trong `RESEARCH_RULES.md`, `x37` dùng `shared/` cho
infrastructure primitives dùng lại giữa sessions.

### 12.1 `shared/` là incremental

`shared/` bắt đầu gần như trống. Session đầu tiên tự xây các module cần thiết.
Sessions sau kế thừa và mở rộng. Không có pre-built library sẵn.

Các **category** cho phép trong `shared/`:

| Category | Module name convention | Ví dụ |
|----------|----------------------|-------|
| Data loading & alignment | `data_loader.py` | `load_feed()`, `align_d1_to_h4()` |
| Feature primitives | `features.py` | `rolling_mean()`, `compute_quantile()` |
| Backtest wrappers | `backtest.py` | `run_backtest()` |
| Metrics | `metrics.py` | `compute_metrics()`, `compute_trade_stats()` |
| Bootstrap | `bootstrap.py` | `circular_block_bootstrap()` |
| Walk-forward helpers | `wfo.py` | `run_wfo()` |

### 12.2 Import pattern

```python
# ✓ OK — import shared modules that EXIST (check before using)
from research.x37.shared.data_loader import load_feed
from research.x37.shared.metrics import compute_metrics

# ✓ OK — session-local code
from research.x37.sessions.s01_codex_v4.phase1_decomposition.code.helpers import my_func

# ✗ FORBIDDEN — import giữa sessions
from research.x37.sessions.s02_other.phase3_design.code.strategy import OtherStrategy
```

### 12.3 Xây module mới trong `shared/`

1. Chỉ đặt logic dùng lại được giữa sessions (không strategy-specific).
2. Thêm unit test trong `shared/tests/`.
3. Giữ backward-compatible nếu session khác đang dùng module đó.
4. Không ghi đè module đang có nếu session ACTIVE khác đang dùng nó.

Import giữa sessions là cấm.

## 13. Naming Convention

Session IDs:

```text
sNN_<descriptor>
```

- `NN`: 2 chữ số tăng dần
- `<descriptor>`: snake_case, ngắn, mô tả agent hoặc approach

Ví dụ: `s01_codex_v4`, `s02_claude_opus`, `s03_manual_recheck`

## 14. Anti-Patterns

### 14a. Governance anti-patterns

1. Chạy phase sau khi phase trước chưa có artifact tối thiểu.
2. Dùng Appendix A trước khi Phase 5 complete.
3. Sửa `frozen_spec.*` sau khi holdout đã bị chạm.
4. Để strategy logic trong `shared/`.
5. Đọc session khác đang ACTIVE.
6. Sửa `docs/` hoặc `resource/`.
7. Auto-advance qua nhiều phase bằng root wrapper.
8. Retune candidate dựa trên holdout performance.

### 14b. Methodology anti-patterns

X37 kế thừa toàn bộ 11 anti-patterns của `RESEARCH_PROMPT_V4`.

## 15. Session Open Checklist

- [ ] Chọn `sNN` tiếp theo
- [ ] Tạo session tree đúng chuẩn
- [ ] Viết `PLAN.md` từ `sessions/SESSION_TEMPLATE.md`
- [ ] Tạo `phase0_protocol/protocol_freeze.json` từ template
- [ ] Khai báo `allow_exact_matches` bằng boolean thật, không để `null`
- [ ] Cập nhật root `README.md`, `PLAN.md`, `manifest.json`
- [ ] Nhắc rõ Appendix A embargo trong session `PLAN.md`
- [ ] Xác nhận session không đọc trực tiếp `research/x0/` .. `research/x36/`

## 16. Session Close Checklist

- [ ] `verdict/verdict.json` đã có
- [ ] `verdict/final_report.md` đã có
- [ ] Root registry đã cập nhật
- [ ] Session status trong manifest đã đổi sang `DONE` hoặc `ABANDONED`
- [ ] Session trở thành read-only

## 17. External Read-Only Inputs

Sessions được phép đọc:

- `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- `strategies/vtrend*/strategy.py`
- `configs/vtrend*/`
- `research/x37/resource/gen1/v1_dipD1/`
- `research/x37/resource/gen1/v2_trendvol_d1_only/`
- `research/x37/resource/gen1/v3_macroHyst/`
- `v10/core/`
- `v10/strategies/base.py`
- `research/lib/`

Sessions không được đọc:

- `validation/`
- `results/full_eval_*`
- `research/x0/` .. `research/x36/`
- results của sessions ACTIVE khác
