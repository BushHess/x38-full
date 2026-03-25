# Báo cáo Lựa chọn Hướng đi cho Entry Spec (WEAK_VDO_THR)

**Trạng thái:** Đã xong.

## 1. Kết Luận Chốt
- **Hướng được chọn:** Hướng A — **Frozen Approximation**
- **Giá trị:** `WEAK_VDO_THR = 0.0065`
- **Hướng bị loại:** Không chọn Hướng B.

## 2. Lý Do Chọn Hướng A (0.0065)
Đây là bản freeze tốt nhất dựa trên sự cân bằng (trade-off) giữa các yếu tố: 
- Causal anchoring 
- OOS (Out-of-Sample) performance 
- Robustness 
- Simplicity

Giá trị `0.0065` là bản làm tròn 4 chữ số của pre-live causal estimate:
- **First-train median:** `0.00648105072393846`
- **Freeze triển khai:** `0.0065`

*Lưu ý:* Trên sample nghiên cứu, `0.0065` là decision-equivalent (tương đương về mặt quyết định) với first-train exact median.

## 3. Hệ Quả và Điểm Quan Trọng
Giá trị `0.0065` bám rất sát với kết quả *research winner*:
- Có **101 / 104** timestamps entry trùng khớp hoàn toàn.
- Chỉ có **3** entry bị retime.
- Điều này có nghĩa là freeze cost rất nhỏ, trong khi độ phức tạp (complexity) giảm mạnh.

---

## 4. Kết Quả Chính
So sánh hiệu suất giữa Hướng A và Hướng B (tốt nhất tìm được).

### Hướng A: Fixed `0.0065` (Selected)
- **Sharpe:** 1.340410
- **CAGR:** 0.412714
- **MDD (Max Drawdown):** -0.285618
- **Số lượng trades:** 104
- **Positive folds vs baseline:** 3 / 4

### Hướng B (Best Found): Trailing median của 2000 positive-core bars gần nhất
- **Sharpe:** 1.265291
- **CAGR:** 0.386799
- **MDD:** -0.317859
- **Số lượng trades:** 106
- **Positive folds vs baseline:** 3 / 4

---

## 5. Đánh Giá Độ Bền (Robustness)

**Kiểm tra Bootstrap & Cost Sweep:**
- **Bootstrap, A vs baseline:** Xác suất (prob(delta Sharpe > 0)) dao động khoảng **92.6% – 95.9%**
- **Bootstrap, B vs baseline:** Xác suất dao động khoảng **82.3% – 87.4%**
- **Bootstrap trực tiếp A vs B:** A thắng trong khoảng **78.6% – 82.4%** số lần resamples.
- **Cost sweep (0 đến 100 bps/side):** A luôn thắng baseline, và **delta Sharpe của A luôn lớn hơn B**.

**Kiểm tra lựa chọn fixed khác:**
- Giá trị `0.0060` có 4/4 folds dương nhưng **không được chọn**.
- Lý do: Đây là *ex-post approximation*, có Sharpe thấp hơn (1.225367), bootstrap yếu hơn và không có causal anchor sạch như `0.0065`.

---

## 6. Tài Liệu và Đặc Tả (Spec Bundle)
Bao gồm các nội dung đã được chốt và khóa chặt để kỹ sư có thể dựng lại mã từ raw data 1:1:
- [x] Freeze-form selection report
- [x] Spec tái dựng 1:1 cho entry freeze
- [x] Bảng so sánh A vs B
- [x] Bootstrap summary
- [x] Cost sweep
- [x] Threshold path summary
- [x] Tóm tắt so sánh entry timestamps với research winner
- [x] Bundle đầy đủ

### Các Yêu Cầu Kỹ Thuật (Spec) Được Khóa:
1. Xác định column raw.
2. EMA conventions.
3. D1 mapping.
4. Công thức cho `imbalance_ratio_base`, `VDO`, `activity_support`, `freshness_support`.
5. Giá trị hard-coded: `WEAK_VDO_THR = 0.0065`.
6. Pseudocode cho entry.
7. WFO fold dates.
8. Acceptance targets.
9. *Caveat:* Biến động sau 2021 (post-2021).
10. *Caveat:* Exit coupling / churn (Lưu ý nếu trong tương lai tính năng exit dùng chung họ tín hiệu).

> **Kết luận cuối cùng:** Khóa (freeze) entry bằng fixed 0.0065, không sử dụng hệ thống tái ước lượng nhân quả trực tuyến (causal online re-estimation).
