# Đề cương nghiên cứu: Gia cố lớp exit cơ sở

**Phân loại:** BẢN NHÁP
**Phạm vi:** Chỉ sửa các điểm yếu mang tính cấu trúc trong lớp exit cơ sở. Không thay đổi logic vào lệnh, bộ lọc chế độ thị trường...

## 1. Mục tiêu

Xác định và khắc phục các điểm yếu mang tính xác định trong cơ chế trail-stop và thoát theo xu hướng ở lớp cơ sở đang gây thất thoát chi phí không cần thiết, nhưng không làm thay đổi logic vào lệnh.

## 2. Các điểm yếu đã xác định

### V1 — Trail-stop nhấp nháy theo ATR

- `trail_stop = peak - 3.0 * robust_atr_t`
- `peak` chỉ đi lên, nhưng `robust_atr_t` thay đổi ở mỗi bar
- ATR giảm đột ngột → trail-stop nhảy lên → kích hoạt exit giả dù giá không giảm
- ATR tăng → trail-stop bị nới xuống → trail-stop mất tính ratchet

### V2 — EMA dùng chung cho vào lệnh và exit

- Điều kiện vào lệnh: `ema_fast > ema_slow`
- Điều kiện thoát theo xu hướng: `ema_fast < ema_slow`
- Cùng một tín hiệu đảo chiều → thoát ở bar `i`, vào lại ở bar `i+1` nếu EMA cross lại
- Vùng EMA xoắn → churn liên tục, mỗi lần mất 25bps

### V3 — Không có thời gian chờ sau exit

- Sau cả trail-stop và thoát theo xu hướng, hệ thống kiểm tra vào lệnh ngay ở bar kế tiếp
- Kết hợp với V2 → chuỗi giao dịch ngắn liên tiếp ăn mòn lợi nhuận qua chi phí

### V4 — Đỉnh dùng `close` thay vì `high`

- `peak = max(peak, close_t)` bỏ qua high intra-bar
- Trail-stop không phản ánh đỉnh giá thật

### V5 — Thứ tự kiểm tra exit tạo ra ưu tiên ngầm (nếu có ML overlay)

- Trail-stop được kiểm tra trước thoát theo xu hướng
- Trên cùng một bar, nếu cả hai điều kiện đều đúng → ghi nhận là trail-stop exit
- Ảnh hưởng đến phân loại của ML overlay vì ML chỉ chấm điểm các trail-stop exit
