# Báo cáo Đánh giá Hệ thống: Combo 1

## Tóm tắt nội dung
**Combo 1** là một cải tiến có thực trong regime (chu kỳ thị trường) giai đoạn hậu 2021, và rất có thể chỉ hiệu quả trong regime này. 
- Không đúng khi gọi đây là "noise fit vớ vẩn" vì hệ thống đã vượt qua các lớp kiểm định OOS/robustness nghiêm ngặt.
- Nhưng cũng sai lầm nếu coi đây là "phiên bản tốt hơn cho mọi thời kỳ".

**Kết luận:** Combo 1 là một **current-regime upgrade** (cải tiến cho chu kỳ hiện tại), không phải là một **timeless upgrade** (cải tiến vượt thời gian).

---

## 1. Tại sao Combo 1 là "cải tiến có thật", không phải noise fit?

Hệ thống đã chứng minh được hiệu quả không chỉ nhờ "ăn may" trong sample, mà đã vượt qua chuỗi kiểm định khắt khe trong protocol OOS (Out-of-Sample) chính thức. Cụ thể, trong cửa sổ OOS:

- **WFO (Walk-Forward Optimization):** Thắng baseline `freeze-entry` + `base-exit` ở 4/4 folds.
- **Bootstrap:** Xác suất $P(\Delta \text{Sharpe} > 0)$ đạt khoảng 94.7% – 98.2%.
- **Cost Sweep:** Chiến thắng ở 9/9 điểm kiểm tra.
- **Exposure Trap:** Pass (Vượt qua).
- **Churn:** Churn với entry mới bằng 0%.
- **Permutation:** Timing-permutation p-value khoảng 0.00083 (rất thấp).

> **Nguồn:** `validation scorecard`, `end-to-end report`, `bootstrap summary`, `cost sweep`, `churn summary`, `permutation summary`. 
> 
> Một hệ thống chỉ “ăn may trong sample” thường không đi qua được cả cụm test này cùng lúc. Những test này khẳng định edge (lợi thế) trong cửa sổ OOS của dự án là có thật.

---

## 2. Vì sao Combo 1 mang tính "Regime-Specific" (đặc thù chu kỳ)?

Điểm then chốt cần lưu ý: 4 folds OOS của dự án đều nằm trong giai đoạn **01/07/2021 đến 28/02/2026**. Toàn bộ bằng chứng WFO chính thức đều là **post-2021** *(Nguồn: `combo 1 full-system spec`)*.

Khi tách hiệu suất pre-2021 và post-2021, sự đảo cực diễn ra rất rõ ràng:

| Giai đoạn | Combo 1 Sharpe | Combo 3 Sharpe | Combo 4 Sharpe |
|-----------|----------------|----------------|----------------|
| **pre-2021**  | 0.972          | 1.787          | **1.951**          |
| **post-2021** | **1.795**          | 1.331          | 1.122          |

> **Nguồn:** `pre/post-2021 diagnostic`. 
> Đây không phải nhiễu nhỏ, mà là **đổi thứ hạng hoàn toàn**.

### Phân tích chi tiết: Đóng góp của Entry và Exit
Sự phân hóa theo regime bộc lộ rõ nhất khi đánh giá riêng lẻ từng thành phần:

* **Entry mới (So sánh Combo 3 vs Combo 4, giữ Base Exit):**
  - **Pre-2021:** Entry mới kém hơn entry gốc ($\Delta \text{Sharpe} \approx -0.164$)
  - **Post-2021:** Entry mới tốt hơn entry gốc ($\Delta \text{Sharpe} \approx +0.209$)
  - $\rightarrow$ *Kết luận:* Entry mới đã có tính định hướng regime nhất định.

* **Exit mới (So sánh Combo 1 vs Combo 3, giữ Freeze Entry):**
  - **Pre-2021:** Exit mới tệ hơn **rất mạnh** ($\Delta \text{Sharpe} \approx -0.815$)
  - **Post-2021:** Exit mới tốt hơn rõ rệt ($\Delta \text{Sharpe} \approx +0.464$)
  - $\rightarrow$ *Kết luận:* Exit mới chịu ảnh hưởng của regime (regime-specific) **mạnh hơn rất nhiều** so với entry mới. 

> Nói thẳng: Phần "đổi dấu theo regime" lớn nhất nằm ở thành phần **Exit**. Entry mới đã có tính chọn regime, nhưng **Exit mới** mới là nhân tố làm hệ thống nghiêng hẳn hiệu suất sang giai đoạn hậu 2021. *(Nguồn: `pre/post-2021 diagnostic`, `exit regime diagnostic`)*

---

## 3. Hiệu suất trên toàn lịch sử liên tục (Full-period continuous)

Khi chạy liên tục toàn bộ dữ liệu từ 2018–2026 (không chia fold):

- **Combo 1:** Final equity 18.38x, Sharpe 1.342
- **Combo 3:** Final equity 33.44x, Sharpe 1.489
- **Combo 4:** Final equity **35.84x**, Sharpe 1.461

> **Nguồn:** `full-period summary`, `full-period report`. 

Đây là bằng chứng rất mạnh cho thấy: nếu đặt câu hỏi "Trên toàn lịch sử 2018–2026 hệ mới có tốt hơn không?", thì câu trả lời chắc chắn là **KHÔNG**. Nó thua cả baseline (`freeze-entry/base-exit`) lẫn hệ thống gốc khi nhìn vào kết quả compounding toàn kỳ.

---

## 4. Kết luận chuẩn xác nhất

Kết luận trung thực nhất về hệ thống lúc này là:

1. **KHÔNG CÓ overfit kiểu ngẫu nhiên (noise-fit):** Vì nó đã sống sót qua mọi kiểm định (WFO, bootstrap, cost sweep, exposure trap, permutation) trong cửa sổ OOS chính thức.
2. **CÓ fit vào một regime cụ thể:** Cụ thể, mô hình được cấu trúc vừa khít với thị trường hậu 2021 (post-2021 structural regime fit).
3. **KHÔNG ĐƯỢC gọi là "cải tiến tổng quát":** Cách gọi này là sai sự thật.
4. **ĐƯỢC PHÉP gọi là "cải tiến triển khai cho regime hiện tại"**, với các điều kiện:
   - Nói rõ nó được chứng minh là tốt trong OOS post-2021.
   - Thừa nhận hệ thống KHÔNG thắng trên lịch sử đầy đủ.
   - Cảnh báo rủi ro có thật nếu cấu trúc thị trường quay lại kiểu pre-2021.

> **Tóm gọn bằng một câu:** *Entry + exit mới là cải tiến có thật trong regime hậu 2021, nhưng không phải cải tiến phổ quát; bản chất của nó là **regime-conditional improvement**, không phải universal upgrade.*

---

## 5. Hệ quả vận hành và Khuyến nghị Triển khai

Nếu phải ra quyết định nghiêm túc từ những dữ kiện đang có, quy trình vận hành nên là:

1. **KHÔNG hủy Combo 1**, vì bằng chứng OOS hiện tại thực sự quá mạnh để bỏ lỡ.
2. **KHÔNG thần thánh hóa** Combo 1 như một hệ "tốt hơn hẳn" cho mọi thời đại.
3. **Triển khai thực tế:** Hãy áp dụng nó như một *hypothesis* cho current regime, kèm theo hoạt động **giám sát chặt chẽ (monitoring)** và kịch bản **dự phòng (fallback)** rất rõ ràng.
4. **Tài liệu hóa:** Mọi spec/tài liệu liên quan phải ghi chú in đậm caveat: 
   > **"Post-2021 favorable, not history-invariant"**.

---
**Tài liệu tham khảo chéo để kiểm chứng:** 
`end-to-end report`, `pre/post-2021 diagnostic`, `full-period continuous report`, `combo aggregate summary`.
