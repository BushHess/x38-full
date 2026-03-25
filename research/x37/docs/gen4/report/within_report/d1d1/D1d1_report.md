# D1d1 Report — Smoke Test

## 1. Implementation Notes

- Mỗi candidate base được viết thành module tự chạy được, có `run_candidate(data_by_timeframe, config, cost_rt_bps, start_utc=None, end_utc=None, initial_state=None)`.
- Signal layer được tính vectorized; chỉ phần hysteresis/position state là loop theo bar.
- Slow timeframe được align bằng `merge_asof(..., direction="backward")` trên `close_time`, nên bar nhanh chỉ thấy bar chậm đã đóng hoàn toàn.
- Rolling/shift đều gap-aware theo segment liên tục của `open_time`; không fill bar, không repair bar, không bắc cầu feature qua đoạn gap.
- Execution là next-open thật: quyết định ở bar close, khớp ở next bar open, PnL đánh dấu theo open-to-open của interval bắt đầu tại thời điểm khớp.
- `cost_rt_bps` chỉ đi vào net interval/daily return; signal path, entry/exit timestamp và state machine không phụ thuộc cost.
- Candidate 3 fit mô hình daily trade-surprise chỉ trên dữ liệu có `close_time < start_utc` khi có test window, đúng causal train/test split.
- Smoke test chỉ chạy fold 1 discovery: 2020-01-01 → 2020-03-31, 50 bps RT, không dùng holdout hoặc reserve_internal.

## 2. Implementation Files

**Base candidates:**

- `d1d_impl_btcsd_20260318_c1_av4h.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m.py`

## 3. Smoke Test Results

| Candidate | Config tested | Entries | Exposure | Gross return | Net return @ 50 bps RT | Next-open check | Cost-invariant path |
|---|---|---|---|---|---|---|---|
| `btcsd_20260318_c1_av4h` | cfg_001 | 1 | 23.8532% | 8.1410% | 7.6001% | PASS | PASS |
| `btcsd_20260318_c2_flow1hpb` | cfg_007 | 1 | 0.6431% | -0.4332% | -0.6825% | PASS | PASS |
| `btcsd_20260318_c3_trade4h15m` | cfg_019 | 4 | 33.7088% | 13.7388% | 11.4833% | PASS | PASS |

**Chi tiết config smoke:**

- **cfg_001:** `q_d1_antivol_rank=0.35`, `q_h4_rangepos_entry=0.55`, `q_h4_rangepos_hold=0.45`
- **cfg_007:** `q_h4_rangepos_min=0.30`, `theta_h1_ret168_entry=-0.04`, `theta_h1_ret168_hold=0.01`
- **cfg_019:** `q_h4_rangepos_entry=0.55`, `q_h4_rangepos_hold=0.35`, `rho_m15_relvol_min=1.10`

**Ghi chú quan trọng:**

- `c2_flow1hpb` kết thúc fold 1 vẫn còn mở vị thế long. Terminal state đã lưu đúng để D1d2 hoặc bước tiếp theo có thể tái dựng.
- Check cost-invariant được xác nhận bằng cách chạy cùng config ở 0 bps và 50 bps: trade timestamps giống hệt nhau, chỉ net return thay đổi.
- Check next-open được xác nhận bằng đối chiếu `trade_log.entry_time_utc` với đúng `exec_time` của interval sau bar phát tín hiệu.

## 4. Ablation Variants

Các ablation file đã tạo xong, và đều được pin vào first config của candidate tương ứng theo yêu cầu governance patch:

**C1:**

- `d1d_impl_btcsd_20260318_c1_av4h_no_d1_permission.py`
- `d1d_impl_btcsd_20260318_c1_av4h_no_h4_execution.py`

**C2:**

- `d1d_impl_btcsd_20260318_c2_flow1hpb_no_d1_flow_permission.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb_no_h4_context.py`
- `d1d_impl_btcsd_20260318_c2_flow1hpb_no_h1_execution.py`

**C3:**

- `d1d_impl_btcsd_20260318_c3_trade4h15m_no_d1_participation_permission.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m_no_h4_context.py`
- `d1d_impl_btcsd_20260318_c3_trade4h15m_no_m15_timing.py`

## 5. Readiness Confirmation

All 3 candidates implemented, saved, and smoke-tested. All 8 required ablation variants saved and import-checked. **Ready for D1d2.**
