# CONVERGENCE_STATUS_V2

## Kết luận ngắn gọn

- **Về phương pháp:** đang đi đúng hướng.
- **Về bằng chứng:** chưa đủ sạch để kết luận hệ nào là “đúng thật” cho triển khai nghiêm túc.
- **Về hội tụ:** các session **chưa hội tụ** ở mức chiến lược cuối cùng.
- **Về hành động:** nếu còn chạy nữa thì chỉ nên chạy **đúng 1 vòng V7** như **final same-file convergence audit**. Sau đó dừng. Muốn phân xử thật sự thì cần **dữ liệu mới được append sau cuối file hiện tại**.

---

## 1) Tóm tắt toàn bộ chuỗi nghiên cứu đến nay

### 1.1. Chuỗi V4 lịch sử (5 vòng nội bộ trên cùng file)

| Vòng | Frozen winner / kết quả chính | Metric còn phục hồi được | Nhận xét thẳng |
|---|---|---|---|
| V4-R1 | `trendvol_10 + dist_high_60` | Không còn đủ artifact để khôi phục chính xác toàn bộ bộ metric cuối cùng | Winner thiên về D1 trend-quality + near-high state |
| V4-R2 | `d1_range_pos_60 + h4_trendq_42` | Dev Sharpe `1.745`, CAGR `71.2%`, MDD `-25.8%`, `75` trades | Winner layered D1 + H4 |
| V4-R3 | `d1_ret_60 + h4_trendq_84` | Không còn đủ artifact để khôi phục chính xác full headline metric cuối cùng | Vòng root-cause redesign; winner đổi tiếp |
| V4-R4 | `d1_dist_high_60 + h4_trendq_84` | Không còn đủ artifact để khôi phục chính xác full headline metric cuối cùng | Fresh-start nhưng vẫn không quay về winner trước đó |
| V4-R5 | `new_final_flow` | Không còn đủ artifact để khôi phục đầy đủ headline metric cuối cùng từ log còn sống | Kết quả thực dụng cuối chuỗi V4: multi-layer hơn, thêm entry-only flow |

### 1.2. Session V5

| Session | Frozen winner | Discovery | Holdout | Reserve/internal | Nhận xét thẳng |
|---|---|---|---|---|---|
| V5 | `SF_EFF40_Q70_STATIC` | Sharpe `1.24`, CAGR `52.7%`, MDD `-33.3%`, `40` trades | Sharpe `1.61`, CAGR `53.3%`, MDD `-18.4%`, `15` trades | Sharpe `0.74`, CAGR `15.9%`, MDD `-31.2%`, `17` trades | Đơn giản, giữ dương ở reserve/internal; nhưng session này không phải blind re-derivation sạch vì có artifact-assisted shortlist/freeze |

### 1.3. Session V6

| Session | Frozen winner | Discovery | Holdout | Reserve/internal | Nhận xét thẳng |
|---|---|---|---|---|---|
| V6 | `S3_H4_RET168_Z0` | Sharpe `1.63`, CAGR `98.4%`, MDD `-43.6%`, `82` trades | Sharpe `1.91`, CAGR `100.8%`, MDD `-22.4%`, `52` trades | Sharpe `-0.04`, CAGR `-5.8%`, MDD `-34.6%`, `76` trades | Pre-reserve rất mạnh nhưng reserve/internal hỏng; full internal có sign-reversal ở bear regime |

---

## 2) Các điểm có hội tụ

Có hội tụ, nhưng chỉ ở **mức motif** và **mức triết lý chọn hệ**, chưa hội tụ ở mức spec cuối cùng.

### Những thứ lặp lại qua nhiều vòng

- Các họ tín hiệu mang tính **trend / persistence / state** liên tục xuất hiện trong nhóm mạnh.
- **Long-only state system** đơn giản thường sống dai hơn các kiến trúc phức tạp nếu layer thêm không chứng minh được thông tin tăng thêm.
- **H4 có giá trị**, nhưng vai trò của H4 không ổn định: có lúc là timing layer, có lúc là core state, có lúc không cần.
- **Layering không mặc định tốt hơn**. Nhiều vòng cho thấy thêm layer chỉ hợp lệ khi nó mang incremental information thực sự.
- **Reserve/internal có thể đảo bảng xếp hạng** so với pre-reserve.
- Càng về sau, quy trình càng nghiêng đúng về **governance, auditability, provenance, plateau, paired comparison và honesty of evidence**, thay vì chỉ chase headline backtest.

---

## 3) Các điểm còn phân kỳ

Đây là vấn đề chính.

### Những thứ chưa nhất quán

- **Winner cuối cùng khác nhau ở cấp session:**
  - chuỗi V4 kết thúc ở `new_final_flow`
  - V5 kết thúc ở `SF_EFF40_Q70_STATIC`
  - V6 kết thúc ở `S3_H4_RET168_Z0`
- **Khung thời gian trội khác nhau:** có vòng D1 là lõi, có vòng D1+H4 layered, có vòng H4-native là winner.
- **Số layer tối ưu khác nhau:** có vòng 1 layer thắng, có vòng 2 layer thắng, có vòng 3 layer được thêm vì mục tiêu thực dụng.
- **Kiểu calibration / thresholding thắng khác nhau.**
- **Hành vi reserve/internal không đồng nhất:** V5 vẫn dương, V6 âm, chuỗi V4 thì đổi winner nhiều lần trên cùng file.

Nói ngắn gọn: **edge tổng quát có thể tồn tại, nhưng spec tối ưu chưa ổn định**.

---

## 4) Mức độ độc lập và ý nghĩa khoa học của các session

Phải nói thẳng:

- Đây **không phải** là ba bằng chứng độc lập sạch theo chuẩn khoa học mạnh.
- V5 là **artifact-assisted**.
- V6 thì blind trước contamination log trước freeze, nhưng vẫn chạy trên **cùng file đã bị chạm qua nhiều session trước**.
- Toàn bộ within-file range từ `2017-08-17` đến cuối file hiện tại đã bị chạm ở ít nhất một vai trò nghiên cứu, nên **không còn clean within-file OOS**.

Hệ quả:

- Divergence hiện tại là divergence của **same-file internal evidence**.
- Nó rất hữu ích để đánh giá **độ ổn định của frontier** và **độ tốt của quy trình**.
- Nó **không đủ** để kết luận session nào đã “thắng thật” theo nghĩa deployable scientific proof.

---

## 5) V7 có còn đáng chạy không?

### Có, nhưng chỉ trong một điều kiện rất rõ

Chỉ đáng chạy nếu bạn xem nó là:

- **một vòng audit hội tụ cuối cùng trên cùng file**, và
- **chấp nhận stop rule trước khi chạy**: bất kể V7 ra gì thì sau đó cũng dừng same-file iteration.

### V7 không đáng chạy nếu mục tiêu thực sự là

- chứng minh clean OOS,
- chọn winner cuối cùng để deploy với độ tin cậy khoa học mạnh,
- hoặc hy vọng “vòng sau sẽ tự động tốt hơn vòng trước”.

Nếu mục tiêu của bạn là một trong ba ý trên, **đừng kỳ vọng V7 giải quyết được**.

---

## 6) Đánh giá ba lựa chọn hành động

### Lựa chọn 1 — Chạy V7 đúng 1 lần

**Khi nào nên chọn:**
- bạn muốn biết quy trình chặt hơn có làm kết quả hội tụ hơn không;
- bạn muốn audit xem divergence đến từ prompt/governance hay từ chính frontier của dữ liệu;
- bạn sẵn sàng dừng sau V7, không mở thêm V8/V9 trên cùng file.

**Lợi ích:**
- thêm một điểm dữ liệu về hội tụ quy trình;
- tăng độ rõ ràng về governance;
- nếu V7 vẫn diverge, bạn có cơ sở mạnh để kết luận same-file iteration đã hết giá trị.

**Giới hạn:**
- không tạo clean OOS;
- không giải quyết được tận gốc câu hỏi “hệ nào đúng thật”.

### Lựa chọn 2 — Dừng same-file iteration ngay bây giờ

**Khi nào nên chọn:**
- bạn đã đủ bằng chứng rằng file này không còn tạo ra proof sạch;
- bạn coi chi phí thêm một vòng prompt là không đáng so với lợi ích biên;
- bạn muốn tránh biến prompt-editing thành hidden optimization.

**Đánh giá:**
- đây là lựa chọn hoàn toàn hợp lý;
- đặc biệt hợp lý nếu mục tiêu cuối cùng là quyết định trading thật chứ không phải audit quy trình.

### Lựa chọn 3 — Chờ dữ liệu mới rồi mới kết luận mạnh hơn

**Khi nào nên chọn:**
- bạn muốn phân xử winner một cách khoa học hơn;
- bạn muốn biết candidate nào còn sống trên dữ liệu chưa từng xuất hiện trong bất kỳ session nào;
- bạn muốn có clean OOS thật sự.

**Đánh giá:**
- đây là con đường đúng nhất nếu mục tiêu là “sự thật”, không phải “thêm một vòng tối ưu”.

---

## 7) Khuyến nghị cuối cùng

### Khuyến nghị thực dụng nhất

- **Nếu mục tiêu của bạn là audit quy trình:** chạy **đúng 1 vòng V7** như **final same-file convergence audit**, rồi dừng.
- **Nếu mục tiêu của bạn là ra quyết định nghiêm túc cho deployment:** dừng same-file iteration và chờ **dữ liệu mới được append**.

### Khuyến nghị dứt khoát

- **Same-file iteration beyond V7: không còn đáng làm về mặt khoa học.**
- **Muốn giải quyết divergence một cách sạch hơn: cần dữ liệu mới.**
- **Meta-knowledge đã giúp quy trình tốt hơn, nhưng không thể thay thế new data.**

Nói gọn: **V7 còn có thể đáng chạy một lần cuối để audit hội tụ. Sau đó phải dừng. Nếu muốn biết hệ nào thật sự đáng tin nhất, cần dữ liệu mới.**
