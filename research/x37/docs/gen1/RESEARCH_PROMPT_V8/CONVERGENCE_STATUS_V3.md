# TÌNH TRẠNG HỘI TỤ V3

## Kết luận ngắn gọn

Kết luận thẳng: **có hội tụ ở cấp “luận điểm/family”, nhưng chưa hội tụ ở cấp “winner exact”**.

- Hội tụ thấy rõ nhất là: các tín hiệu **khung chậm D1** liên quan tới **trạng thái/regime** nhiều lần quay lại như ứng viên mạnh.
- Phân kỳ vẫn còn lớn ở cấp hệ cụ thể: các phiên khác nhau đã đóng băng những winner rất khác nhau.
- Vì toàn bộ file hiện tại đã bị chạm ở nhiều vai trò qua nhiều phiên, **không còn clean within-file OOS**.
- Một phiên V8 nữa trên cùng file có thể còn giá trị **kiểm toán hội tụ cuối cùng**, nhưng **không** thể giải quyết dứt điểm bằng chứng khoa học. Muốn giải quyết sạch, phải có **data mới được append sau file hiện tại**.

## Bảng tóm tắt toàn bộ các phiên / vòng đã có

### Chuỗi V4 — các vòng lịch sử nhiều lần tái thiết kế trên cùng file

| Vòng | Winner đóng băng / kết quả cuối | Chỉ số chính còn phục hồi được | Nhận xét thẳng |
|---|---|---|---|
| V4-R1 | Hệ D1 kiểu `trendvol_nearhigh` với `d1_trendvol_10 + d1_dist_high_60`, ngưỡng annual expanding `q80/q60` | Không còn phục hồi đầy đủ bộ Sharpe/CAGR/MDD cuối cùng; verdict còn lưu: **“internally competitive, not clearly superior to frontier benchmark”** | Đây là winner D1 thuần, thiên về regime/trend-location. Có tín hiệu sớm rằng edge có thể nằm ở khung chậm. |
| V4-R2 | `d1_range_pos_60 + h4_trendq_42`, vào `q60/q60`, thoát H4 `q50`, không có D1 exit clause | **Dev Sharpe 1.745, CAGR 71.2%, MDD -25.8%, 75 trades, 4 positive windows** | Đây là winner layered D1+H4 điển hình: D1 làm permission/regime, H4 làm timing/state. |
| V4-R3 | `d1_ret_60` trailing 1095d + `h4_trendq_84`, thêm anti-chase cap | Bộ chỉ số cuối cùng của full frozen system không còn phục hồi trọn; phần còn lưu cho macro channel thắng: **WF Sharpe 1.5884, Holdout Sharpe 0.8772** | Vòng này chuyển trọng tâm sang logic chậm hơn và bắt đầu siết governance, nhưng vẫn còn redesign sau khi đã thấy holdout. |
| V4-R4 | `d1_dist_high_60 + h4_trendq_84`, annual expanding, entry `q70/q70`, hold `q70/q60` | Không còn bộ chỉ số cuối cùng đầy đủ trong artifact còn sống | Tiếp tục ra winner layered D1+H4; cho thấy cấu trúc D1 regime + H4 timing vẫn lặp lại. |
| V4-R5 | `new_final_flow`: `d1_ret_60 + h4_trendq_84` với entry-only filter `h4_buyimb_12` | Không còn full metric table cuối cùng; chỉ còn decision path, shortlist và plateau logic | Đây là vòng tinh chỉnh thực dụng mạnh, thêm filter entry. Giá trị contamination lớn, nhưng giá trị chứng minh sạch thấp. |

### Phiên V5 — Protocol V5, artifact-assisted internal re-derivation

| Phiên | Winner đóng băng | Discovery | Holdout | Reserve/internal | Nhận xét thẳng |
|---|---|---|---|---|---|
| V5 | `SF_EFF40_Q70_STATIC` | **Sharpe 1.24, CAGR 52.7%, MDD -33.3%, 40 trades** | **Sharpe 1.61, CAGR 53.3%, MDD -18.4%, 15 trades** | **Sharpe 0.74, CAGR 15.9%, MDD -31.2%, 17 trades** | Kết quả nhìn đẹp, nhưng phiên này **không phải blind strict re-derivation** vì shortlist/freeze tables được reproduce từ run cũ trước khi validate cuối. Giá trị contamination cao. |

### Phiên V6 — Protocol V6, clean-blind internal re-derivation

| Phiên | Winner đóng băng | Discovery | Holdout | Reserve/internal | Nhận xét thẳng |
|---|---|---|---|---|---|
| V6 | `S3_H4_RET168_Z0` | **Sharpe 1.6322, CAGR 98.42%, MDD -43.55%, 82 trades** | **Sharpe 1.9148, CAGR 100.76%, MDD -22.41%, 52 trades** | **Sharpe -0.0419, CAGR -5.75%, MDD -34.64%, 76 trades** | Pre-reserve cực mạnh, nhưng reserve/internal **gãy rõ**. Quan trọng hơn: trong chính frozen set của V6, hệ `S2_D1_VCL5_20_LT1.0` mới là **best reserve performer**. Đây là dấu hiệu rất mạnh rằng winner exact chưa ổn định. |

### Phiên V7 — Protocol V7, final same-file convergence audit

| Phiên | Winner đóng băng | Discovery | Holdout | Reserve/internal | Nhận xét thẳng |
|---|---|---|---|---|---|
| V7 | `S_D1_VOLCL5_20_LOW_F1` | **Sharpe 1.2668, CAGR 70.84%, MDD -51.62%, 126 trades** | **Sharpe 0.8441, CAGR 26.23%, MDD -36.37%, 32 trades** | **Sharpe 0.9791, CAGR 29.23%, MDD -21.14%, 51 trades** | Đây là phiên blind trước freeze ở mức quy trình, và nó **hội tụ thực chất** với ứng viên D1 vol-cluster từng nổi lên ở V6. Nhưng split vẫn không độc lập sạch về mặt cross-session, nên reserve chỉ là **internal evidence**, không phải clean OOS. |

## Các điểm hội tụ

### 1. Hội tụ ở cấp “ý tưởng nguồn edge”
Điểm này là rõ nhất.

Qua nhiều vòng/phiên, edge thường quay lại quanh một trục chung:

- **D1 chậm** thường mang phần regime/context quan trọng hơn H4 thuần.
- H4 có lúc hữu ích, nhưng thường dưới vai trò **timing / controller / entry refinement**, không phải lúc nào cũng là nguồn edge độc lập bền nhất.
- Khi dùng H4 thuần, kết quả có thể rất đẹp pre-reserve nhưng dễ gãy hơn ở late slice.
- Các lần re-derivation gần đây đều cho thấy **khung chậm D1** là nơi đáng tin hơn để tìm cấu trúc bền.

### 2. Hội tụ ở cấp “governance lesson”
Điểm này coi như đã chốt:

- within-file reserve trên file hiện tại chỉ có thể dùng như **internal stress slice**;
- same-file prompt tightening không tạo ra clean OOS mới;
- blind theo quy trình khác với independent theo dữ liệu;
- redesign sau holdout hoặc sau reserve làm tăng contamination và làm yếu giá trị chứng minh.

### 3. Hội tụ mạnh giữa V6 và V7 ở cấp family
Đây là tín hiệu đáng chú ý nhất hiện nay.

- V6 freeze winner là H4-only `S3_H4_RET168_Z0`, nhưng trong reserve/internal của chính V6 thì `S2_D1_VCL5_20_LT1.0` lại là kẻ thắng rõ hơn.
- V7, chạy blind trước freeze, lại đóng băng đúng một rule **cùng family và gần như cùng hệ**: `S_D1_VOLCL5_20_LOW_F1`.

Nói thẳng: **V7 không xác nhận exact winner của V6; V7 xác nhận “late-session durable thesis” mà V6 đã vô tình làm lộ ra trong reserve.**

## Các điểm phân kỳ

### 1. Exact winner vẫn thay đổi liên tục
Danh sách winner qua các giai đoạn không ổn định:

- V4-R1: D1 trendvol + near-high
- V4-R2: layered D1 range-position + H4 trend-quality
- V4-R3: layered D1 return-state + H4 trend-quality + cap
- V4-R4: layered D1 distance/high-state + H4 trend-quality
- V4-R5: layered D1 return-state + H4 trend-quality + flow filter
- V5: D1-only `SF_EFF40_Q70_STATIC`
- V6: H4-only `S3_H4_RET168_Z0`
- V7: D1-only `S_D1_VOLCL5_20_LOW_F1`

Đây không phải hội tụ exact. Đây là **frontier instability** hoặc **specification sensitivity**.

### 2. Reserve/internal thường làm xáo trộn thứ hạng
V6 là ví dụ rất rõ: winner pre-reserve mạnh nhất lại suy yếu ở reserve; một đối thủ D1 khác mới là best reserve performer.  
V7 thì ngược lại: winner D1 giữ được reserve tốt hơn các rival H4/layered chính.

Điều đó nói gì?  
Nó nói rằng **same-file late slice đang chủ yếu giúp phân loại tính bền nội bộ**, chứ chưa đủ để chứng minh exact winner nào là “đúng”.

### 3. Layered systems chưa thắng dứt điểm
Trong lịch sử V4, layered systems xuất hiện rất nhiều và thường thắng ở discovery/dev. Nhưng ở V7, layered rival mạnh nhất (`L2_VOLCL_RANGE48_Q60`) có Sharpe/MDD đẹp hơn ở pre-reserve mà vẫn **thua về mean daily edge và thua reserve**.

Bài học thẳng: **complexity chưa chứng minh được superiority ổn định**.

## Điều gì hiện nay có vẻ nhất quán, và điều gì thì chưa

### Có vẻ nhất quán
- D1 chậm chứa phần edge regime/context quan trọng.
- H4 native standalone dễ đẹp ở một số giai đoạn nhưng độ bền kém hơn.
- Reserve/internal trên same file chỉ phù hợp để kiểm tra mâu thuẫn nội bộ.
- Simpler systems đáng được ưu tiên nếu candidate phức tạp không chứng minh paired edge rõ ràng.

### Chưa nhất quán
- exact feature / exact transform nào là tốt nhất;
- exact timeframe-role decomposition tốt nhất;
- exact parameterization tốt nhất;
- layered có thật sự vượt simple hay chỉ ăn may ở một lát cắt nào đó;
- liệu exact winner cuối cùng nên là D1-only hay D1+H4.

## Split hiện tại có thật sự độc lập không?

Câu trả lời gọn: **không**.

- V7 blind trước freeze ở cấp quy trình: **có**.
- Nhưng độc lập về split trên toàn bộ lịch sử các session: **không**.
- Union contamination đã chạm toàn bộ file ở nhiều vai trò khác nhau.
- Vì vậy, mọi holdout/reserve trong V8 nếu chạy tiếp cũng chỉ là **internal-only**.

Nói thẳng hơn: **không còn within-file clean OOS để tranh luận nữa**.

## Một phiên thứ năm trên cùng data có khả năng giải quyết phân kỳ không?

**Khả năng giải quyết exact-rule divergence: thấp.**  
**Khả năng làm rõ family-level convergence và khóa governance: có.**

Nếu chạy V8:

- thứ có thể được làm rõ là: một prompt sạch hơn, không mang data-derived specifics, có tiếp tục rediscover lại cùng luận điểm/family như V7 hay không;
- thứ **không** thể được làm rõ sạch là: rule exact nào đúng ngoài mẫu theo nghĩa khoa học mạnh.

Nói cách khác: V8 còn giá trị **kiểm toán hội tụ cuối cùng**, nhưng **không** còn giá trị tạo bằng chứng OOS sạch.

## Có cần data mới để giải quyết sạch không?

**Có. Bắt buộc.**

Muốn có clean resolution, cần:

1. đóng băng một rule cuối cùng;
2. không chỉnh tiếp trên file hiện tại;
3. chờ **data mới được append sau file hiện tại**;
4. chỉ dùng phần append đó làm clean OOS thực sự.

Không có đường tắt nào khác.

## Khuyến nghị trực tiếp giữa 3 lựa chọn

### Lựa chọn 1 — chạy V8 đúng 1 lần như final same-file convergence audit
**Khuyến nghị: Có thể làm, nhưng chỉ đáng làm nếu mục tiêu là đóng quy trình và trả lời câu hỏi hội tụ phương pháp.**

Tôi nghiêng về **có thể chạy V8 đúng 1 lần**, vì:

- V7 đã cho tín hiệu hội tụ family-level đáng kể với phần late evidence của V6;
- vẫn còn giá trị kiểm toán xem một prompt V8 sạch hơn, không mang data-derived specifics, có tái khám phá cùng hướng hay không;
- V8 có thể giúp anh/chị chốt dứt khoát rằng sau đó phải dừng same-file iteration.

Nhưng phải hiểu đúng: **V8 không làm mạnh hơn claim khoa học về OOS**.

### Lựa chọn 2 — dừng same-file iteration ngay bây giờ
**Cũng hoàn toàn hợp lý** nếu mục tiêu chính của anh/chị là thực dụng:

- hiện tại đã đủ rõ rằng exact winner chưa ổn định tuyệt đối;
- không còn within-file clean OOS;
- tiếp tục lặp lại trên cùng file chủ yếu tạo thêm governance noise.

Nếu anh/chị không cần “closure” về mặt phương pháp, dừng ngay bây giờ là quyết định sạch.

### Lựa chọn 3 — chờ data mới trước khi đưa ra claim mạnh hơn
**Đây là bước bắt buộc cho mọi claim mạnh.**

Dù có chạy V8 hay không, muốn nói mạnh hơn về tính đúng đắn của rule cuối cùng thì vẫn phải **đợi data mới**.

## Khuyến nghị cuối cùng của tôi

Khuyến nghị thực tế nhất là:

1. **Nếu anh/chị còn muốn chốt nốt câu hỏi hội tụ trên same file, hãy chạy V8 đúng 1 lần và dừng.**
2. **Nếu mục tiêu là tăng độ tin cậy khoa học của winner, đừng kỳ vọng V8 giải quyết được; phải chờ data mới.**
3. **Bất kỳ same-file iteration nào sau V8 đều không còn năng suất khoa học.**

Nói không vòng vo:  
- **V8 còn đáng làm đúng 1 lần** với tư cách kiểm toán hội tụ cuối cùng.  
- **Sau V8 phải dừng.**  
- **Muốn phân xử sạch, cần dữ liệu mới.**
