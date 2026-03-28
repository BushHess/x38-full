# 02 — First-Cycle Execution Checklist

## 1. Mục tiêu

Checklist này để chạy **vòng đầu tiên** sau khi x40 code đã dựng xong.  
Mục tiêu không phải tìm alpha mới. Mục tiêu là:

- qualify `OH0_D1_TREND40`,
- qualify hoặc chặn rõ ràng `PF0_E5_EMA21D1`,
- đo decay / half-life / crowding,
- ra `next_action`.

---

## 2. Cấu trúc run ID

Khuyến nghị:
```text
x40_<YYYYMMDD>_<snapshot_id>_first_cycle
```

Ví dụ:
```text
x40_20260328_snapshot_20260318_first_cycle
```

---

## 3. Preflight Checklist

- [ ] `research/x40/` tree tồn tại đúng.
- [ ] `BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml` đã freeze.
- [ ] `OH0_D1_TREND40/source_reference.md` đầy đủ.
- [ ] `PF0_E5_EMA21D1/source_reference.md` đầy đủ.
- [ ] canonical raw snapshot đã pin ID.
- [ ] replay engine deterministic trên cùng seed và cùng inputs.
- [ ] metric domain `daily_utc_common_domain` đã unit test.
- [ ] cost model IDs đã pin.
- [ ] path output cho run ID mới đã tạo.
- [ ] reviewer đã được chỉ định.

Nếu thiếu bất kỳ mục nào => không bắt đầu cycle.

---

## 4. Step-by-step

## Step 1 — A00 parity cho OH0
- [ ] chạy parity
- [ ] review `replay_parity.json`
- [ ] review `a00_parity_diff_report.md`
- [ ] reviewer sign-off

### Pass nếu:
- [ ] integer counts khớp
- [ ] transitions khớp
- [ ] source metrics trong tolerance
- [ ] không có alignment mismatch

### Nếu fail:
- [ ] gắn `OH0` = blocked
- [ ] dừng toàn cycle
- [ ] sửa replay engine
- [ ] không sang Step 2

---

## Step 2 — A00 parity cho PF0
- [ ] chạy parity
- [ ] review `replay_parity.json`
- [ ] review data-surface usage (`taker_buy_base_vol` phải được khai báo)
- [ ] reviewer sign-off

### Pass nếu:
- [ ] VDO logic dùng public-flow fields đúng source
- [ ] không dùng fallback OHLC
- [ ] metric domain source khớp

### Nếu fail:
- [ ] gắn `PF0` = blocked
- [ ] vẫn được phép tiếp tục cycle cho `OH0`
- [ ] ghi rõ trong `run_blockers.md`

---

## Step 3 — Qualification replay cho OH0
- [ ] chạy BQC-v1
- [ ] sinh `baseline_manifest.json`
- [ ] sinh `return_series_native.csv`
- [ ] sinh `return_series_daily_utc.csv`
- [ ] sinh `forward_evaluation_ledger.csv`

### Review tối thiểu
- [ ] `league_id = OHLCV_ONLY`
- [ ] `data_surface_used_by_logic = ["close"]`
- [ ] `object_type = baseline`
- [ ] `metric_domain_id = daily_utc_common_domain`
- [ ] không hidden calibration

### Output expected
- [ ] `hard_gate_assessment.json`
- [ ] `soft_gate_assessment.json`
- [ ] baseline level gán rõ (`B1_QUALIFIED`, `B0_INCUMBENT`, hoặc `B_FAIL`)

---

## Step 4 — Qualification replay cho PF0
- [ ] chạy BQC-v1
- [ ] sinh full artifact set

### Review tối thiểu
- [ ] `league_id = PUBLIC_FLOW`
- [ ] `data_surface_used_by_logic` có `taker_buy_base_vol` hoặc equivalent public-flow field
- [ ] không cross-league confusion với `OHLCV_ONLY`
- [ ] WFO/soft evidence được ghi trung thực

### Output expected
- [ ] baseline level gán rõ

---

## Step 5 — A01 decay cho OH0 và PF0
- [ ] era splits tính xong
- [ ] rolling windows tính xong
- [ ] `a01_decay_summary.json` tồn tại cho từng baseline
- [ ] `a01_decay_band` gán rõ

---

## Step 6 — A02 half-life cho OH0 và PF0
- [ ] forward curves theo era tính xong
- [ ] `peak_horizon` đã so với reference era
- [ ] `late_realization_share` đã tính
- [ ] `compression_warning` / `compression_severe` gán rõ

---

## Step 7 — A03 capacity/crowding cho OH0 và PF0
- [ ] cost sweep xong
- [ ] execution-bar volume summaries xong
- [ ] participation proxy tables xong
- [ ] `crowding_warning` / `crowding_severe` gán rõ

---

## Step 8 — A05 canary cho cả hai
- [ ] nếu chưa có appended blocks: emit `NOT_RUN`
- [ ] nếu có appended blocks: state phải là `OK` hoặc `TRIGGERED`
- [ ] `a05_canary_history.csv` tồn tại

---

## Step 9 — Aggregate durability
- [ ] chạy aggregation policy
- [ ] sinh `durability_summary.json` cho từng baseline
- [ ] cập nhật `forward_evaluation_ledger.csv`

### Kết quả cần có
- [ ] `OH0` có durability status
- [ ] `PF0` có durability status hoặc blocked state được ghi rõ

---

## Step 10 — A04 entry vs exit attribution
- [ ] chạy A04 trên baseline active league
- [ ] xác định `entry_null / exit_helpful / mixed / insufficient`

### Nếu A04 cho thấy:
- entry residuals null nhiều lần,
- exit overlays cải thiện trade quality,

thì `next_action` phải ưu tiên `SHIFT_TO_EXIT_FOCUSED`.

---

## Step 11 — A07 league pivot gate
- [ ] chạy A07 hoặc ít nhất phát hành `a07_pivot_summary.json`
- [ ] xác định có cần pivot hay không
- [ ] xác nhận richer-data league có sẵn hay chỉ là ý tưởng chưa có data-admission plan

### Output expected
- [ ] `a07_pivot_summary.json`
- [ ] `a07_go_no_go.md`

---

## Step 12 — Decision conference
- [ ] tạo `next_action_draft.md`
- [ ] reviewer comment
- [ ] research lead ký `next_action.md`
- [ ] generate `next_action.json`

---

## 5. Cây output tối thiểu của first cycle

```text
research/x40/runs/<run_id>/
├── preflight/
├── parity/
│   ├── oh0/
│   └── pf0/
├── qualification/
│   ├── oh0/
│   └── pf0/
├── studies/
│   ├── a01/
│   ├── a02/
│   ├── a03/
│   ├── a04/
│   ├── a05/
│   └── a07/
├── reviews/
│   ├── oh0_baseline_review.md
│   ├── pf0_baseline_review.md
│   └── reviewer_notes.md
└── decisions/
    ├── next_action.md
    └── next_action.json
```

Ngoài run tree này, mỗi baseline root phải có persistent artifacts:
```text
research/x40/baselines/<baseline_id>/
├── source_reference.md
├── frozen_spec.md
├── frozen_spec.json
├── baseline_manifest.json
└── forward_evaluation_ledger.csv
```

---

## 6. Hard stop rules

## Stop rule A
Nếu `OH0` chưa pass A00 parity -> dừng.

## Stop rule B
Nếu cả `OH0` và `PF0` đều `B_FAIL` ở qualification -> không mở x39. Chỉ được:
- mở x37 challenge, hoặc
- sửa constitution / implementation bug nếu lỗi là operational.

## Stop rule C
Nếu `next_action.md` chưa tồn tại -> cycle chưa hoàn tất.

## Stop rule D
Nếu `forward_evaluation_ledger.csv` chưa tồn tại cho baseline active -> cycle chưa hoàn tất.

---

## 7. Kết quả cuối cùng bắt buộc

Sau cycle đầu tiên phải trả lời được 7 câu hỏi này:

1. `OH0` có replay đúng source không?
2. `PF0` có replay đúng source không?
3. `OH0` là `B1`, `B0`, hay `B_FAIL`?
4. `PF0` là `B1`, `B0`, hay `B_FAIL`?
5. Mỗi baseline đang `DURABLE/WATCH/DECAYING/BROKEN` thế nào?
6. Residual research tiếp theo nên ưu tiên entry hay exit hay dừng cùng league?
7. Có cần bật `open_x37_challenge` hoặc `pivot richer-data` hay không?

Nếu chưa trả lời được đủ 7 câu này, cycle coi như chưa xong.
