# 01 — Post-Implementation Master Runbook

## 1. Mục tiêu của runbook này

Sau khi mã x40 đã dựng xong, nhiệm vụ đầu tiên **không** phải là tìm strategy mới.  
Nhiệm vụ đầu tiên là chạy **vòng chứng cứ đầu tiên** để biết:

- baseline nào thực sự replay đúng source,
- baseline nào đủ tư cách làm chuẩn tham chiếu,
- baseline nào đang durable / watch / decaying / broken,
- bước nghiên cứu tiếp theo phải là x39 residual, x37 blank-slate, hay pivot dữ liệu.

Runbook này mô tả toàn bộ vòng đó.

---

## 2. Vai trò và trách nhiệm

### 2.1 Research Lead
Quyết định:
- scope của vòng chạy,
- snapshot sử dụng,
- baseline nào được phép qualify,
- ký `next_action.md`.

### 2.2 X40 Operator
Chạy:
- A00,
- BQC-v1,
- A01/A02/A03/A05,
- tổng hợp artifacts,
- sinh `durability_summary.json`,
- sinh `next_action_draft.md`.

### 2.3 Independent Reviewer
Rà:
- source parity,
- field admissibility,
- hidden calibration,
- consistency giữa artifacts và verdict.

### 2.4 X39 Sprint Owner
Chỉ được vào cuộc sau khi:
- baseline league đã có ít nhất `B1_QUALIFIED` hoặc `B0_INCUMBENT` đủ rõ,
- `next_action.md` cho phép residual sprint.

### 2.5 X37 Session Owner
Chỉ được vào cuộc khi:
- decision tree bật `open_x37_challenge = true`,
- hoặc pivot sang league mới cần discovery from scratch.

---

## 3. Cấu trúc vòng vận hành đầu tiên

```text
R0 preflight
R1 source parity
R2 qualification replay
R3 durability suite
R4 decision conference
R5 branch execution
R6 forward evidence activation
R7 production/x38 handoff
```

---

## 4. R0 — Preflight

## 4.1 Mục tiêu
Bảo đảm hệ thống có đủ điều kiện tối thiểu để chạy vòng chứng cứ đầu tiên.

## 4.2 Việc phải có trước
- x40 tree đã scaffold xong.
- `BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml` đã freeze.
- Có source pack cho:
  - `OH0_D1_TREND40`
  - `PF0_E5_EMA21D1`
- Canonical raw snapshot đã được pin.
- Canonical replay engine đã có unit tests cơ bản.
- Cost models đã pin ID rõ ràng.
- Metric domain `daily_utc_common_domain` đã được implement đúng.

## 4.3 Output bắt buộc
- `run_context.json`
- `snapshot_reference.md`
- `operator_preflight_checklist.md`

## 4.4 Stop conditions
Dừng ngay nếu:
- source pack chưa hoàn chỉnh,
- baseline replay chưa deterministic,
- metric domain chưa khóa,
- schema raw chưa pass.

---

## 5. R1 — Source Parity (A00)

## 5.1 Mục tiêu
Chứng minh rằng baseline port mới **khớp source** trước khi x40 tự cấp bất kỳ verdict qualification nào.

## 5.2 Thứ tự chạy
1. `OH0_D1_TREND40`
2. `PF0_E5_EMA21D1`

Làm theo thứ tự này vì `OH0` đơn giản hơn nhiều và đóng vai trò control baseline.

## 5.3 Khuyến nghị interface chuẩn
Các lệnh dưới đây là **canonical CLI contract được khuyến nghị** sau khi implementation xong:

```bash
python -m research.x40.cli.parity \
  --baseline OH0_D1_TREND40 \
  --source-pack research/x40/baselines/OH0_D1_TREND40/source_reference.md \
  --out research/x40/runs/<run_id>/parity/oh0/

python -m research.x40.cli.parity \
  --baseline PF0_E5_EMA21D1 \
  --source-pack research/x40/baselines/PF0_E5_EMA21D1/source_reference.md \
  --out research/x40/runs/<run_id>/parity/pf0/
```

## 5.4 Kiểm cái gì
Phải kiểm tối thiểu:
- schema input,
- row counts source,
- timestamps / ordering / timezone,
- exact state transitions,
- exact entry/exit timestamps,
- completed trade counts,
- source metric domain parity,
- return series parity nếu source series có sẵn.

## 5.5 Output bắt buộc
- `a00_source_pack_checklist.md`
- `source_parity_summary.json`
- `replay_parity.json`
- `a00_parity_diff_report.md`

## 5.6 Rule cực cứng
- A00 FAIL => baseline port attempt = `B_FAIL`
- Không được sang R2 nếu A00 chưa PASS.

## 5.7 Quyết định sau R1
- Nếu `OH0` fail parity: dừng toàn bộ first-cycle, sửa replay engine trước.
- Nếu `OH0` pass mà `PF0` fail: vẫn được tiếp tục qualification cho `OH0`, nhưng `PF0` bị chặn tới khi parity xong.
- Nếu cả hai pass: sang R2 cho cả hai.

---

## 6. R2 — Qualification Replay (BQC-v1)

## 6.1 Mục tiêu
Đưa baseline từ trạng thái “khớp source” sang trạng thái “đủ tư cách làm chuẩn tham chiếu dưới constitution hiện tại”.

## 6.2 Phân biệt cực quan trọng
- `SOURCE_PARITY_REPLAY` = trung thành với source cũ
- `X40_QUALIFICATION_REPLAY` = replay dưới constitution x40 hiện tại, metric domain thống nhất, cost stress thống nhất, artifact contract thống nhất

Hai cái này **không phải một**.

## 6.3 Khuyến nghị CLI
```bash
python -m research.x40.cli.qualify \
  --baseline OH0_D1_TREND40 \
  --snapshot <active_snapshot_id> \
  --constitution research/x40/BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml \
  --out research/x40/runs/<run_id>/qualification/oh0/

python -m research.x40.cli.qualify \
  --baseline PF0_E5_EMA21D1 \
  --snapshot <active_snapshot_id> \
  --constitution research/x40/BASELINE_QUALIFICATION_CONSTITUTION_V1.yaml \
  --out research/x40/runs/<run_id>/qualification/pf0/
```

## 6.4 Phải sinh ra các artifact gì
Per baseline:
- `baseline_manifest.json`
- `frozen_spec.md`
- `frozen_spec.json`
- `return_series_native.csv`
- `return_series_daily_utc.csv`
- `metric_domain_summary.json`
- `qualification_summary.json`
- `soft_gate_assessment.json`
- `hard_gate_assessment.json`
- `forward_evaluation_ledger.csv` (khởi tạo)

## 6.5 Rule gán baseline level
- hard gate fail => `B_FAIL`
- soft evidence `ACCEPTABLE` => `B1_QUALIFIED`
- soft evidence `UNDERRESOLVED` => `B0_INCUMBENT`
- soft evidence `NEGATIVE_CONFIRMED` => `B_FAIL`

## 6.6 Cách hiểu thực dụng ở vòng đầu
- `OH0` nhiều khả năng là baseline control đủ sạch để target `B1_QUALIFIED`.
- `PF0` có thể kết thúc ở `B0_INCUMBENT` hoặc `B1_QUALIFIED` tùy active qualification replay, nhưng **không** được phép mặc định “đương nhiên qualified”.

## 6.7 Stop conditions
Dừng và sửa nếu:
- `baseline_manifest.json` thiếu field,
- metric domain mismatch,
- cost models không khớp declared IDs,
- hidden calibration bị phát hiện,
- `forward_evaluation_ledger.csv` chưa được tạo.

---

## 7. R3 — Durability Suite

## 7.1 Mục tiêu
Biến nỗi lo “market structure changed / AI-bot crowding / alpha decay” thành verdict có số liệu.

## 7.2 Thứ phải chạy
- `A01_temporal_decay`
- `A02_alpha_half_life`
- `A03_capacity_crowding`
- `A05_canary_drift`  
  (nếu chưa có appended block thì A05 = `NOT_RUN`, coi là neutral)

## 7.3 Khuyến nghị CLI
```bash
python -m research.x40.cli.audit_decay --baseline <baseline_id> --out ...
python -m research.x40.cli.audit_half_life --baseline <baseline_id> --out ...
python -m research.x40.cli.audit_capacity --baseline <baseline_id> --out ...
python -m research.x40.cli.audit_canary --baseline <baseline_id> --out ...
python -m research.x40.cli.aggregate_durability --baseline <baseline_id> --out ...
```

## 7.4 Phải sinh ra gì
Per baseline:
- `a01_era_metrics.csv`
- `a01_rolling_metrics.csv`
- `a01_decay_summary.json`
- `a02_forward_curve_by_era.csv`
- `a02_half_life_summary.json`
- `a03_capacity_curve.csv`
- `a03_cost_sensitivity.csv`
- `a03_entry_liquidity_summary.csv`
- `a03_crowding_summary.json`
- `a05_canary_state.json`
- `durability_summary.json`

## 7.5 Điều phải đọc ra từ R3
Phải trả lời được:
- recent-era alpha còn dương không?
- Sharpe/expectancy đang co lại bao nhiêu?
- edge đang realize sớm hơn trước không?
- crowding proxies đang xấu đi không?
- canary có trigger không?

## 7.6 Output tổng hợp
Per baseline cần có:
- `baseline_review.md`
- `durability_summary.json`
- cập nhật row mới vào `forward_evaluation_ledger.csv`

---

## 8. R4 — Decision Conference

## 8.1 Mục tiêu
Ép hệ thống ra **một next action duy nhất** thay vì để research drift.

## 8.2 Input của conference
- baseline levels cho `OH0`, `PF0`
- durability statuses
- A01/A02/A03 summaries
- A04 nếu đã chạy
- A07 pivot evaluation
- availability của richer-data league

## 8.3 Phải sinh ra
- `next_action.md`
- `next_action.json`

## 8.4 Primary action chỉ được là một trong ba loại
1. `CONTINUE_SAME_LEAGUE_RESIDUAL`
2. `SHIFT_TO_EXIT_FOCUSED`
3. `PIVOT_TO_RICHER_DATA`

Ngoài ra có thêm flag:
- `open_x37_challenge = true/false`

## 8.5 Tuyệt đối không được viết
- “cần suy nghĩ thêm”
- “tạm thời cứ scan thêm”
- “mở đồng thời cả x37, x39, pivot”
- “chưa rõ nên cứ tiếp tục test thêm một ít”

Conference phải chốt đúng một primary action.

---

## 9. R5 — Branch Execution

## 9.1 Nếu action = CONTINUE_SAME_LEAGUE_RESIDUAL
- mở x39 residual sprint trong league tương ứng,
- baseline active trong league đó trở thành incumbent để challenge,
- output của sprint phải đi qua promotion package quay về x40.

## 9.2 Nếu action = SHIFT_TO_EXIT_FOCUSED
- x39 sprint phải ưu tiên exit/path-quality/de-risking,
- không mở thêm entry filter sprint trước khi exit sprint xong.

## 9.3 Nếu action = PIVOT_TO_RICHER_DATA
- đóng residual sprint trong league cũ,
- lập data-admission brief cho league mới,
- nếu cần discovery từ gốc trắng thì bật `open_x37_challenge = true`.

## 9.4 Nếu escalation flag `open_x37_challenge = true`
- mở x37 session mới theo playbook ở tài liệu 05,
- không dùng x39 để thay thế blank-slate challenge.

---

## 10. R6 — Forward Evidence Activation

## 10.1 Mục tiêu
Bắt đầu con đường đi từ same-file evidence sang appended-data evidence.

## 10.2 Việc phải làm ngay sau first cycle
- pin `freeze_cutoff_utc`,
- tạo `eval_block_id` convention,
- lịch append data theo cadence,
- update `forward_evaluation_ledger.csv` định kỳ.

## 10.3 Cadence mặc định
- `PF0_E5_EMA21D1`: monthly
- `OH0_D1_TREND40`: quarterly

## 10.4 Tuyệt đối cấm
- redesign baseline sau khi đã mở appended evaluation block,
- runner-up rescue,
- silent threshold changes.

---

## 11. R7 — Production và x38 handoff

## 11.1 Production
Sau x40, nếu có nhu cầu deploy/shadow:
- baseline/challenger phải đi qua production validation riêng,
- machine verdict vẫn là `PROMOTE/HOLD/REJECT`,
- con người mới ra quyết định deploy.

## 11.2 x38
x38 chỉ consume:
- survivor đã qua x40,
- challenge winner đã có artifact package đầy đủ,
- không consume raw x39 idea,
- không consume x37 session ở trạng thái chưa qualify.

---

## 12. Checklist kết thúc vòng đầu

Một first-cycle chỉ được coi là hoàn tất nếu:
- `OH0` có parity replay và qualification replay rõ ràng,
- `PF0` có parity replay và qualification replay rõ ràng hoặc bị chặn có lý do minh bạch,
- durability suite đã chạy,
- `next_action.md` đã phát hành,
- `forward_evaluation_ledger.csv` tồn tại cho baseline active,
- x39 hoặc x37 hoặc richer-data pivot đã được chỉ định rõ ràng.

---

## 13. Quy tắc nền

Nếu có nghi ngờ giữa:
- “baseline tốt nhất tuyệt đối”
và
- “baseline đủ chuẩn để làm chuẩn tham chiếu”,

luôn chọn vế thứ hai.

Nền móng đúng của hệ thống không phải là một winner bất tử.  
Nền móng đúng là **một constitution + runbook đủ chặt để biết winner nào đang còn đáng tin và winner nào đã hết hạn**.
