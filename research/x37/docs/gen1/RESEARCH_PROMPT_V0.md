# Research Prompt V0: Cải Tiến Giao Dịch BTC-USDT Spot

**1. Dữ liệu Đầu vào**
- **Cặp giao dịch:** BTC-USDT Spot
- **Khung thời gian:** H4 và D1
- **Giai đoạn:** 2017 đến 2026

**2. Benchmark Hiện Tại (tại mức phí 20 bps Round-Trip)**
- **Hệ thống gốc (E5+EMA21D1):** Sharpe 1.638 | CAGR 72.8% | MDD -38.5%
- **Biến thể full-sample mạnh nhất (V4):** Sharpe 1.830 | CAGR 80.4% | MDD -33.6%
  - *Đặc điểm:* Thắng full-sample trên 3 metric chính, nhưng benchmark gốc vẫn robust hơn trong bootstrap.

**3. Mục tiêu Nghiên cứu**
- Tìm kiếm hệ thống giao dịch tốt hơn các benchmark hiện tại hoặc xác nhận rằng hệ thống cải tiến đã nằm trong vùng tối ưu.

**4. Phương pháp tiếp cận (First Principles)**
- **Không giả định trước:** Bắt đầu hoàn toàn từ dữ liệu thô, không áp đặt bất kỳ cấu trúc định sẵn nào.
- **Nguyên lý cốt lõi:**
  - Phân rã tận gốc, đo lường từng thành phần riêng biệt.
  - Hiểu cơ chế thị trường đằng sau biến động trước khi thiết kế bất kỳ logic nào.
- **Khai thác Đặc tính:** Phân tích dữ liệu để tìm ra các thông tin có thể khai thác như *trend, momentum, volume, volatility, regime*, v.v.
- **Thiết kế Hệ thống:** Dựa vào các thông tin đã khai thác để thiết kế quy trình rõ ràng cho quyết định: *Entry, Quản lý Position, và Exit*.
- **Hạn chế Grid Search:** Grid search chỉ được sử dụng để tinh chỉnh tham số **sau khi** đã có thiết kế dựa trên sự thấu hiểu từ First Principles.

**5. Giả định Giao dịch & Mô phỏng**
- **Chi phí giao dịch:** 10 bps mỗi chiều (20 bps Round-trip).
- **Khớp lệnh (Execution):** Tín hiệu (Signal) phát ra tại đóng cửa (Close), khớp lệnh (Fill) tại mở cửa (Open) của thanh nến (Bar) kế tiếp.

**6. Yêu cầu Bắt buộc đối với Hệ Thống Mới**
- **Độ ổn định:** Cấu hình tốt nhất (Winner) bắt buộc phải nằm trên một parameter plateau rộng.
- **Kiểm chứng:** Bắt buộc được xác nhận qua Walk-Forward Validation trên dữ liệu chưa từng quan sát.
- **Độ bền bỉ:** Không được "gãy" (thua lỗ nặng ngoài kiểm soát) ở bất kỳ giai đoạn cấu trúc thị trường nào trong lịch sử.
