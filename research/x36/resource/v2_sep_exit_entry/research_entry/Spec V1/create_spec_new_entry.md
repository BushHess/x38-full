# Tài liệu Spec Độc Lập: `entry_winner_weakvdo_spec.md`

Tài liệu spec này được thiết kế self-contained (đầy đủ và độc lập) nhằm cung cấp đủ thông tin cho kỹ sư có thể dựng lại chính xác 1:1.

## 1. Nội dung đã được "khóa" (Chốt hạ)
Tài liệu đã bao gồm đầy đủ các cấu phần sau:

* **Công thức cốt lõi:** Các bước tính toán đầy đủ từ file raw CSV sang `VDO`, `activity_support`, và `freshness_support`.
* **Quy ước kỹ thuật:** Các chuẩn (`conventions`) về EMA và quy tắc ánh xạ (mapping rule) cho khung thời gian D1.
* **Cơ chế vận hành (Semantics):** Khoảng thời gian `warmup`, và nguyên tắc `signal-at-close` / `fill-at-open`.
* **Chiến lược Walk-Forward (WFO):** Thiết lập 4 fold WFO, bao gồm ngày (dates) `train/OOS`, và các vùng `bar-index`.
* **Logic tối ưu:** Cách tính ngưỡng `weak_vdo_thr` dựa trên tập dữ liệu train (train slice).
* **Quyết định vào lệnh:** Cung cấp mã giả (pseudocode) cho quy trình ra quyết định Entry.
* **Tiêu chí nghiệm thu (Acceptance targets):** Các mốc kiểm tra để đảm bảo kỹ sư lập trình (implementation) đúng chuẩn.
* **Các lưu ý (Caveats):**
  * Những biến đổi về cấu trúc thị trường giai đoạn hậu 2021 (post-2021 structure).
  * Rủi ro `churn` / `double-counting` nếu thuật toán Exit sau này sử dụng chung một họ tín hiệu (signal family).

## 2. Các điểm chốt (Key Takeaways) của Spec
Dưới đây là các định nghĩa quan trọng nhất:

* **Tiêu chí Winner hợp lệ:** Là ranh giới `train-median weak-VDO` mang tính thích ứng theo từng fold (fold-adaptive).
  * ❌ *Không phải* là một ngưỡng cố định toàn cục (fixed global threshold).
  * ❌ *Không phải* logic gộp cứng nhắc loại: Global `VDO` AND `activity` AND `freshness`.
* **Vai trò của Support Signals:** Chỉ được sử dụng với vai trò "phủ quyết có điều kiện trong một giới hạn" (bounded conditional veto), kích hoạt riêng trong vùng $0 < VDO \le weak\_vdo\_thr\_fold$.

---
**Đề xuất bước tiếp theo:**
Nếu cần thiết, tôi có thể sử dụng chính spec này để dựng ngay một bản *implementation reference* tối giản. Bản tham chiếu này sẽ đóng vai trò làm **“golden test”** chuẩn mực cho kỹ sư đối chiếu khi hoàn thiện code.
