# 06 — X40 Monthly / Quarterly Operations Manual

## 1. Mục tiêu

Sau first cycle, x40 phải trở thành một hệ thống vận hành định kỳ, không phải một báo cáo một lần.

Mục tiêu của manual này là:
- giữ `forward_evaluation_ledger.csv` sống,
- phát hiện decay/crowding sớm,
- quản lý đường đi từ `B1` sang `B2`,
- mở requalification đúng lúc,
- không cho baseline drift âm thầm.

---

## 2. Cadence mặc định

## 2.1 PF0_E5_EMA21D1
Cadence: **monthly**

Lý do:
- execution clock H4,
- signal frequency dày hơn,
- public-flow league dễ nhạy với structural change/crowding hơn.

## 2.2 OH0_D1_TREND40
Cadence: **quarterly**

Lý do:
- native D1,
- trade frequency thấp hơn,
- A05 low-power nếu ép monthly.

---

## 3. Monthly block process (PF0)

Mỗi block monthly phải làm:

1. pin `eval_block_id`
2. pin `block_start_utc`, `block_end_utc`
3. ingest appended data
4. chạy replay frozen baseline trên block
5. update `forward_evaluation_ledger.csv`
6. chạy A05 canary
7. cập nhật `durability_status_after`
8. phát hành `monthly_baseline_review.md`

### Minimum outputs
- `a05_canary_state.json`
- `a05_canary_history.csv`
- `monthly_baseline_review.md`
- new row trong `forward_evaluation_ledger.csv`

---

## 4. Quarterly process (OH0 + PF0 tổng hợp)

Mỗi quarter phải làm:

- rerun A01 trên data mở rộng
- rerun A02 trên data mở rộng
- rerun A03 trên data mở rộng
- aggregate durability lại
- xem A06 có trigger không
- nếu cần, cập nhật `next_action`

### Minimum outputs
- `quarterly_durability_review.md`
- updated `a01_decay_summary.json`
- updated `a02_half_life_summary.json`
- updated `a03_crowding_summary.json`
- updated `durability_summary.json`

---

## 5. A05 incident response

## 5.1 Nếu A05 = NOT_RUN
- không làm gì thêm
- aggregation dùng A01/A02/A03

## 5.2 Nếu A05 = OK
- update ledger
- giữ cadence bình thường

## 5.3 Nếu A05 = TRIGGERED một lần
- escalates to `WATCH` nếu chưa đủ `DECAYING`
- tạo `a05_trigger_report.md`
- review block anomalies
- **không** tự retune baseline

## 5.4 Nếu A05 = TRIGGERED hai block liên tiếp
- follow aggregation policy
- có thể dẫn đến `BROKEN`
- bắt buộc chạy A06 review

---

## 6. A06 bounded requalification process

Khi A06 chạy, allowed responses chỉ gồm:

1. no action
2. watch mode
3. profile switch đã pre-qualified
4. offline requalification session
5. league pivot recommendation

### Forbidden
- live retune
- threshold change âm thầm
- winner rescue
- redesign ngay trong verdict của appended block

---

## 7. B1 -> B2 progression

Một baseline chỉ được lên `B2_CLEAN_CONFIRMED` khi:
- có ít nhất 180 ngày calendar appended data sau `freeze_cutoff_utc`,
- có ít nhất một appended evaluation block,
- có non-zero executed exposure hoặc ít nhất một completed round trip,
- không vi phạm hard blockers trong appended evidence.

Nếu chưa đủ floor này:
- baseline giữ `B1` hoặc `B0`,
- chỉ cập nhật durability.

---

## 8. Review pack định kỳ

## 8.1 Monthly review pack
- block summary
- A05 state
- expectancy delta
- MAE delta
- hold duration delta
- action/no-action decision

## 8.2 Quarterly review pack
- all monthly review pack items
- A01 decay update
- A02 half-life compression update
- A03 crowding update
- A06 review if needed
- refreshed `next_action` only if branch change is warranted

---

## 9. Khi nào phải sửa `next_action`

Chỉ sửa `next_action` nếu có ít nhất một trong các điều kiện:
- durability status đổi cấp (`WATCH -> DECAYING`, `DECAYING -> BROKEN`, etc.),
- league comparison đảo chiều,
- A04 direction mới mâu thuẫn với sprint direction hiện tại,
- A07 đổi từ no-pivot sang pivot,
- x39/x37 sinh ra challenger đủ mạnh.

Nếu không có các điều này, giữ nguyên `next_action`.

---

## 10. Records phải giữ

Per active baseline:
- `baseline_manifest.json`
- `forward_evaluation_ledger.csv`
- all latest A01/A02/A03/A05 summaries
- latest `durability_summary.json`
- latest review pack
- current `next_action.md`

---

## 11. Manual override policy

Con người có thể:
- dừng trading/shadow,
- tăng mức review,
- mở x37,
- chốt pivot.

Con người **không** được:
- sửa baseline threshold âm thầm rồi gọi đó là “same baseline”,
- bỏ qua hard gate fail,
- tuyên bố `B2` khi chưa đủ appended floor.

---

## 12. Quy tắc một câu

Vận hành x40 đúng nghĩa là:
- baseline không bị lãng quên,
- decay không bị phát hiện quá muộn,
- và mọi thay đổi lớn đều đi qua artifact + decision path rõ ràng.
