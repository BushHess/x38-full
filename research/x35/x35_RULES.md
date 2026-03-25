# X35 — Quy Định Riêng

**Kế thừa**: [`CLAUDE.md`](../../CLAUDE.md) → [`RESEARCH_RULES.md`](../../docs/research/RESEARCH_RULES.md) → file này.

---

## 1. Write zone

```
research/x35/**/*          ← toàn bộ code, docs, branch results, tests
```

Không có ngoại lệ ra ngoài `research/x35/`.

Mọi đầu ra phát sinh trong quá trình nghiên cứu đều phải nằm trong write zone này:

- code
- tài liệu program-level
- branch `PLAN.md`
- branch reports
- notes / diagnostic markdown
- test helpers nội bộ study

Không được để output trôi ra ngoài `x35/`.

## 2. Kiến trúc nghiên cứu

`x35` theo pattern:

```
x35/
├── README.md               ← study index
├── PLAN.md                 ← program index / dependency graph
├── manifest.json           ← machine-readable status
├── x35_RULES.md            ← file này
├── program/                ← numbered phase docs 01..07
├── shared/                 ← calendar aggregation + frozen state definitions
├── branches/a_...          ← diagnostic branch
├── branches/b_...          ← gated validation branch
├── code/                   ← wrapper tối thiểu, không chứa canonical logic
└── results/                ← root index only
```

Nguyên tắc:

1. `shared/` là source duy nhất cho logic outer-state dùng lại.
2. `branches/*/code/` chứa runner branch-local.
3. `branches/*/results/` là nơi ghi kết quả canonical.
4. Root `code/` chỉ làm wrapper điều phối, không chứa analysis logic chính.
5. Root `x35/` chỉ chứa index/control files và top-level directories; không đặt loose phase docs hoặc ad-hoc notes ở root.
6. Program-level numbered docs `01..07` phải nằm trong `program/`.
7. Nếu tạo tài liệu mới:
   - program-level theory / decision docs → `program/`
   - branch-specific prereg / report → `branches/<branch>/`
   - root-level index/status only → `README.md`, `PLAN.md`, `manifest.json`, `x35_RULES.md`, `results/README.md`

## 3. Import nội bộ x35

Ngoài import chung trong `RESEARCH_RULES.md`, `x35` dùng:

```python
from research.x35.shared.common import load_feed, bars_to_frame
from research.x35.shared.state_definitions import FROZEN_SPECS, build_state_series
```

Import giữa các branch được phép nhưng không khuyến khích. Nếu có thể, dùng `shared/`.

## 4. Branch structure chuẩn

```
branches/<branch_name>/
├── PLAN.md
├── code/
│   ├── __init__.py
│   ├── run_<branch>.py
│   └── [phase_*.py]
└── results/
```

## 5. Scope freeze của x35

Trong current program:

- chỉ BTC spot OHLCV;
- chỉ outer-state weekly/monthly;
- không slow-daily replacement;
- không threshold sweep;
- không consensus state sau khi nhìn kết quả.

Action-class freeze:

- validation class đầu tiên luôn là `entry_prevention_only`;
- `FORCE_FLAT` không được mở như validation branch ngay từ đầu;
- `FORCE_FLAT` chỉ admissible như **diagnostic falsification pass** sau khi Class A survey đã chạy xong và root-level go/no-go cho phép kiểm tra continuation Class B;
- nếu current program đã chốt `NO_GO_MID_TRADE_HAZARD_FAMILY`, không được hồi sinh Class B bằng cách thêm spec post-hoc trong cùng scope.

## 6. Branch gating

- `a_state_diagnostic` là **pilot heuristic probe**, không phải verdict cuối cho toàn bộ `x35`.
- `a_state_diagnostic` PASS toàn bộ diagnostic gates là một đường nhanh để mở `b_entry_overlay`, nhưng FAIL của `a_` chỉ có nghĩa `NO_GO_CURRENT_MENU`.
- `b_entry_overlay` chỉ được mở sau khi root-level Phase 1–4 xác nhận có đủ evidence ở level program.
- Nếu muốn thử candidate menu mới, phải mở branch mới hoặc cập nhật prereg rõ ràng; không được sửa retroactive kết quả của `a_`.

## 7. Mandatory Program Docs

`x35` phải duy trì các tài liệu program-level sau trong `program/`:

- `program/01_problem_statement.md`
- `program/02_phenomenon_survey.md`
- `program/03_formalization.md`
- `program/04_go_no_go.md`
- `program/05_design.md`
- `program/06_validation.md`
- `program/07_final_report.md`

## 8. Root Hygiene

Không được tái phạm các lỗi tổ chức sau:

- đặt `01_*.md`, `02_*.md`, ... trực tiếp ở root `x35/`
- để ghi chú tạm / post-hoc note loose ở root
- ghi report canonical ra root thay vì `branches/<branch>/results/`
- để docs/code/results nằm sai lớp kiến trúc

Khi review `x35`, root phải nhìn như sau:

- `README.md`
- `PLAN.md`
- `manifest.json`
- `x35_RULES.md`
- `program/`
- `shared/`
- `branches/`
- `code/`
- `results/`

## 9. Testing Hygiene

Nếu test nội bộ của `x35` cần path bootstrap cho namespace `research`, chỉ được xử lý
theo scope local của study, ví dụ:

- `shared/tests/conftest.py`

Không dùng cách sửa framework-wide hoặc phụ thuộc vào việc caller phải set
`PYTHONPATH` thủ công.
