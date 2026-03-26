# Kiến trúc mảng Khám phá (Search Space Expansion) cho Alpha-Lab Framework

*Tài liệu này được sinh ra từ việc phân tích sự kiện "Tai nạn thuật toán VDO", đối chiếu với triết lý Offline Validation của X38 để đưa ra cơ chế khám phá mở rộng không gian tìm kiếm tri thức.*

---

## 1. Cơ sở Thiết kế: Phản biện mô hình Sandbox Online

1. **Tuân thủ triết lý Offline:** Việc xây dựng một "Unbounded Sandbox" cho AI tự do viết code, tự động test và tự báo cáo lặp lại sai lầm của mô hình Online (Gen 2, Gen 3). Cho AI "tự do test data và feedback loop" sẽ phá vỡ hoàn toàn bức tường lửa Contamination Firewall (`002`), dẫn đến Data Snooping. Alpha-Lab đòi hỏi **Tách biệt Tư duy (Hypothesis) và Thực thi (Validation)**.
2. **Khước từ việc tạo Nhiễu chủ đích (Anti-science):** Trong Quant Trading, hàm ngẫu nhiên sinh ra PnL tốt gọi là **Overfitting Hypothesis**. Tai nạn VDO không đến từ sự "ngẫu nhiên rác", mà đến từ việc AI lấy một khái niệm có logic thật sự ở ngành khác (Oscillator / Signal Processing) áp vào giá BTC.
3. **Quản trị Artifact sinh ra giả thuyết:** Sự kiện VDO bị mất dấu là do framework cũ chưa xem Prompt và Semantic Context là một Artifact cần version hóa.

→ **Giải pháp:** Hệ thống hóa các "Tai nạn VDO" thông qua cơ chế mở rộng không gian tìm kiếm tri thức (Epistemology) một cách có kiểm soát ở pha Offline.

---

## 2. Tầng 1: Cơ chế Khám phá - "Orthogonal Cross-Pollination"

Thay vì tự do chạy code, ta đưa "tai nạn" vào giai đoạn lập giả thuyết (Hypothesis Generation) trên văn bản (Text/Spec).

* **Mục đích:** Bắt AI dùng lăng kính của các miền khoa học khác (Vật lý, Xử lý tín hiệu - DSP, Sinh lý học, Thuyết thông tin) để định nghĩa cấu trúc vi mô của hành vi giá thị trường. VDO (Variable Duty Oscillator) chính là một dạng DSP.
* **Cơ chế Pipeline (Offline):**
  1. **Domain Seed Prompting:** Alpha-Lab duy trì một từ điển các "Domain Seeds" (Ví dụ: `["Fluid Dynamics", "Acoustic Resonance", "Thermodynamics", "Information Entropy"]`).
  2. **Hypothesis Synthesis:** Ở bước tạo Feature Spec, API yêu cầu AI: *"Hãy định nghĩa 5 công thức toán học phát hiện sự chuyển pha của BTC, sử dụng hoàn toàn các nguyên lý từ [Acoustic Resonance]"*.
  3. **Mandatory Prompt Serialization:** Trước khi AI sinh ra công thức/code, **chính cái User Prompt chứa seed đó phải được hash và lưu thẳng vào Artifact Registry** (Giải quyết triệt để bài toán mất dấu vết Prompt của VDO cũ).
* **Tích hợp:** Nằm hoàn toàn trong đặc tả của `006-feature-engine` và `017-epistemic-search-policy`. Cơ chế nạp input vào Engine.

---

## 3. Tầng 2: Cơ chế Sàng lọc & Dịch ngược - "Blind Feature Screener & Semantic Recovery"

Sau khi Alpha-Lab chuyển hàng loạt Spec dị biệt thành Code và chạy batch validation (Offline), ta cần nhận diện cái nào là "Alpha xịn".

* **Filter Rule (Screening):** Các thuật toán "lạ" (như VDO) thường không hoạt động giống MA hay RSI. Màng lọc không đánh giá PnL ngay, mà đánh giá mức độ **độc lập thống kê (Orthogonality)**. Nếu một feature `X` sinh ra tín hiệu có `Correlation < 0.1` so với toàn bộ Feature Pool đang có, nhưng lại có Z-Score Predictive Power (IC - Information Coefficient) cao -> Gắn cờ `[Anomaly-Alpha]`.
* **Semantic Recovery (Dịch ngược logic):**
  Khi code chạy offline vượt qua `010-clean-oos-certification`, hệ thống gắp ngược file Spec lên và sinh ra một task cho AI Architect:
  * *"Thuật toán [ID_XYZ] được tạo ra từ prompt [A] về Acoustic Resonance đã chứng minh được Predictive Power. Hãy giải thích bằng ngôn ngữ thị trường (Market Microstructure): Tại sao công thức này lại có tác dụng với Order Book của BTC?"*
  * Quá trình này gán lại "Lý trí" cho một "Tai nạn", biến nó thành Tri thức lõi (Meta-knowledge).

---

## 4. Tích hợp thực thi: Đề xuất Blueprint cho X38 Topics

Dựa trên cấu trúc Plan hiện tại, X38 không cần mở topic thêm một Sandbox Engine (sẽ phá vỡ Offline Rule), mà cần **bổ sung các quy tắc sau vào các topic đang có**:

1. **Bổ sung Debate cho `017-epistemic-search-policy` (Chính sách tìm kiếm tri thức):**
   * *Bổ sung:* Thêm Sub-topic **"Divergent Heuristics"**: Quy định rõ tỷ lệ % lượng Hypothesis trong mỗi Batch được phép "Ảo tưởng có định hướng" (e.g. 20% budget của Protocol Engine dành cho chéo miền Khoa học Kỹ thuật).

2. **Bổ sung Debate cho `004-meta-knowledge` (Lưu trữ và kế thừa):**
   * *Bổ sung:* Yêu cầu thiết kế **"Prompt Ancestry Tree" (Cây phả hệ Prompt)**. Bất cứ một Feature hay Sub-module nào sinh ra đều mang trong Metadata của nó chuỗi Prompt đã kích nạp nó.

3. **Bổ sung Debate cho `006-feature-engine`:**
   * *Bổ sung:* Cơ chế phân quyền **Black-box Hypothesis**. Cho phép duyệt Spec đối với những Feature không có lý thuyết thị trường ngay từ đầu, miễn là độ phức tạp toán học (Big-O) đủ thấp và vượt qua được bài test Orthogonality.
