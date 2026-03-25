# Báo Cáo Nghiên Cứu Exit (Đã Cấu Trúc Lại)

Nghiên cứu exit đã được thực hiện lại từ đầu theo đúng phạm vi (scope) được yêu cầu. Dưới đây là kết quả và phân tích chi tiết.

## 1. Kết Luận Chính: Winner Exit Mới

**Chiến lược tốt nhất:**
`trail3.3_close_current_confirm2 + no_trend_exit + cooldown6 + time_stop30`

**Diễn giải chi tiết thuật toán:**
*   **Trailing Stop:** Vẫn giữ nguyên cơ chế trailing stop bảo vệ.
*   **Trend Exit:** Loại bỏ hoàn toàn điều kiện thoát lệnh nương theo xu hướng (EMA30 < EMA120).
*   **Cấu hình Trailing:**
    *   Giá neo (Peak) = Giá Close.
    *   Chỉ báo độ biến động (ATR) = Current robust ATR.
    *   Hệ số nhân (Multiplier) = 3.3.
    *   Xác nhận (Confirm) = Yêu cầu 2 giá Close liên tiếp phá vỡ (breach) ngưỡng trail mới thực hiện exit.
*   **Cooldown:** Sau mọi exit, hệ thống tạm ngừng giao dịch trong 6 nến (6 bars).
*   **Time Stop:** Nếu giao dịch kéo dài đến 30 nến H4 mà chưa hit stop, hệ thống sẽ tự động thoát lệnh.

---

## 2. Hiệu Suất WFO (Walk-Forward Optimization)

So sánh giữa Baseline A (Entry cũ + Base exit) và hệ thống Winner Exit mới:

| Metric | Baseline A | Winner Exit Mới |
| :--- | :--- | :--- |
| **Sharpe Ratio** | 1.374 | **1.804** |
| **Max Drawdown (MDD)** | -27.3% | **-26.0%** |
| **Số lượng giao dịch (Trades)**| 104 | 124 |

*Khẳng định:* Winner dương trên 4/4 folds so với Baseline A.

**Kết quả chi tiết theo Fold (Winner vs Baseline A):**
*   **Fold 1:** 1.691 vs 1.120
*   **Fold 2:** 1.823 vs 1.604
*   **Fold 3:** 2.376 vs 1.875
*   **Fold 4:** 0.896 vs 0.322

---

## 3. Phân Tích Cơ Chế & Lỗ Hổng (Vulnerability)

**Ba điểm mấu chốt ở Exit:**
1.  **Trailing là bắt buộc:** Bỏ trailing system sẽ gãy. Time stop không thể tự gánh vác.
2.  **Trend exit có hại:** Không cần đến và thường làm giảm hiệu suất.
3.  **Lợi thế lớn nhất:** Sự kết hợp giữa Time stop + Cooldown tạo ra edge chủ đạo.

*Tóm tắt vấn đề:* Cốt lõi khiến hệ thống yếu đi không phải do "thiếu volume lúc exit", mà là trạng thái ngâm lệnh quá lâu (overstay) và việc vào lại lệnh liên tục không cần thiết (re-entry churn).

**Kết quả Scan các lỗ hổng (Vulnerabilities) trên Baseline A:**
*   **V1 (ATR flicker cùng-bar):** Xảy ra ở ~3.9% số trade. Không phải vấn đề lớn cần ưu tiên sửa.
*   **V2 (EMA exit churn):** Chỉ ~1.0% số trade vào lại (re-enter) trong <= 6 nến sau trend exit. Tác động yếu.
*   **V3 (Thiếu cooldown - Vấn đề lớn nhất):** Gây ra tình trạng 23.3% số trade vào lại trong <= 3 nến, 38.5% trong <= 6 nến. Đây là lỗ hổng nghiêm trọng nhất.
*   **V4 (Dùng Close thay vì High cho Peak):** Nếu dùng High, 59.2% số trade sẽ bị trigger sớm hơn. Tuy nhiên, khi fix theo hướng này thì hiệu suất OOS lại sụt giảm.

---

## 4. Vai Trò Của Volume Trong Exit

Đã kiểm tra kỹ các hệ thống (non-ML) có sử dụng Volume nhưng kết quả không khả quan:
*   *Best volume continuation:* Sharpe 1.531
*   *Best always-on volume exit:* Sharpe 1.449
*   **Kết luận:** Đều thua xa phương pháp chỉ sử dụng giá (price-only: 1.804). Tín hiệu mạnh nhất ở exit hiện tại là kiểm soát vòng đời giao dịch bằng giá/thời gian, không phải volume.

---

## 5. Đánh Giá Độ Tin Cậy (Validation)

Winner Pass phần lớn các bài test độ tin cậy được yêu cầu:

*   **WFO:** Pass tuyệt đối (4/4 folds).
*   **Bootstrap vs A:** Pass mạnh mẽ. Xác suất P(delta Sharpe > 0) dao động từ 94.5% – 96.2% trên nhiều block lengths.
*   **Cost sweep:** Pass sạch sẽ (Thắng Baseline A ở 9/9 mức chi phí, và >= 3/4 folds ở cả 9 mức).
*   **Exposure trap:** Pass với trạng thái tốt. Cần random cap rất hẹp (29-32 bars) mới bắt kịp được -> Edge nằm thực sự ở khoảng 30 nến, không phải cứ "giao dịch ngắn hơn là mặc nhiên tốt hơn".
*   **Sensitivity:** Pass một phần (Có Caveat).
    *   Trail multiplier ổn định ở mốc 3.0 / 3.3 / 3.6.
    *   Cooldown tốt trong khoảng 6–8 nến.
    *   *Time stop rất nhạy,* nhưng có vùng ridge rõ nét quanh 29-32 bars (tối ưu nhất ở 30).
*   **Regime check:** Có điểm yếu ở pre/post-2021. Hệ thống mới này hoạt động tốt hơn hẳn ở giai đoạn post-2021, nó không phải là một quy luật phổ quát chung cho mọi thời đại. Dù sensitivity bị ảnh hưởng, đây vẫn là một điểm "Ridge" thực sự (29-32) chứ không phải tín hiệu ngẫu nhiên (spike).

---

## 6. Lựa Chọn Thay Thế (Runner-Up)

**Phiên bản đơn giản hơn, ưu tiên cho tương lai nếu cần:**
`trail3.0_close_lagged_confirm1 + no_trend_exit + cooldown3 + time_stop36`

**Thông số:**
*   Sharpe Ratio: **1.759**
*   WFO: 4/4 folds vs Baseline A.

**Nhận xét:**
Tuy Sharpe thấp hơn Winner (1.804) nhưng hệ thống này đơn giản hơn đáng kể, dễ deploy (freeze) và chênh lệch không quá áp đảo.

---

## 7. Hành Động Tiếp Theo (Next Steps)

1.  **Chốt Phương Án:** Xác nhận chọn Winner policy (30 nến) hay Runner-up (36 nến).
2.  Viết Specification (spec) đặc tả kỹ thuật để tái tạo 1:1 cho mã Exit được chọn.
3.  Cung cấp Pseudocode và Acceptance targets.
