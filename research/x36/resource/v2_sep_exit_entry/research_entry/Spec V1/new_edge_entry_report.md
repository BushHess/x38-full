# Kết quả Nghiên cứu Mới về Entry (WFO OOS)

Xong rồi. Tôi đã làm lại nghiên cứu entry theo đúng chuẩn WFO (Walk-Forward Optimization) OOS (Out-of-Sample), không sử dụng phương pháp cherry-pick kiểu chạy vài biến thể rồi kể chuyện.

## 1. Kết Luận Ngắn Gọn (Cốt Lõi Của Edge Mới)

- **Có edge mới cho entry.**
- Nó không nằm ở việc thay thế VDO bằng một oscillator khác.
- Nó không nằm ở việc massage threshold quanh `VDO = 0`.
- **Nó nằm ở `bounded conditional veto` trên các tín hiệu `weak positive VDO`.**

## 2. Rule Thắng Tốt Nhất (Winner)

Rule thắng tốt nhất trong nghiên cứu này là: `weakvdo_q0.5_activity_and_fresh_imb`

### Logic Cốt Lõi:
- Giữ `VDO > 0` làm core gate.
- Tính `weak_vdo_thr = median` của các giá trị VDO dương trên dải train (train slice), áp dụng chỉ trên các bar thỏa mãn:
  - `EMA30 > EMA120`
  - D1 regime đang hoạt động (ON)

### Chi Tiết Cụ Thể (Khi thị trường flat và core ON):
- **Nếu `VDO <= 0`**: Bỏ qua (không vào lệnh).
- **Nếu `VDO > weak_vdo_thr` (VDO mạnh)**: Vào lệnh bình thường.
- **Nếu `0 < VDO <= weak_vdo_thr` (VDO dương nhưng yếu)**: Chỉ vào lệnh khi thỏa mãn ĐỒNG THỜI hai điều kiện về activity và freshness:
  - `EMA12(vol_surprise_quote_28) >= 1`
  - `EMA28(imbalance_ratio_base) <= 0`

> **Nói một cách thẳng thắn:** VDO mạnh thì cứ tự động cho qua. VDO dương nhưng yếu thì bắt buộc phải có thêm tín hiệu `activity + freshness` mới được vào lệnh.

---

## 3. Kết Quả Out-of-Sample (OOS)

So sánh rule mới với baseline hiện tại (`VDO > 0`):

| Chỉ số | Baseline (`VDO > 0`) | Rule Mới (`weakvdo...`) |
|----------|:---:|:---:|
| **Sharpe** | 1.130760 | **1.374084** |
| **CAGR**   | 0.350303 | **0.427156** |
| **MDD**    | -0.370939| **-0.273367**|
| **Positive folds vs baseline** | N/A | **4/4** |
| **Số lượng Trades (OOS)** | 118 | **104** |

**Điểm quan trọng nhất:** Đây không phải kiểu hack tăng Sharpe bằng cách bóp số lượng trade một cách cực đoan. Nó chỉ loại bỏ bớt 14 trade trên toàn bộ OOS stitched sample.

---

## 4. Tại Sao Có Thể Tin Tưởng Kết Quả Này?

Một control test rất mạnh cho thấy:
- **Áp dụng điều kiện cứng (hard-AND toàn cục):** `VDO > 0 AND activity AND freshness` $\rightarrow$ Sharpe chỉ đạt **1.244475**.
- **Bản `bounded weak-VDO` mới:** $\rightarrow$ Sharpe lên tới **1.374084**.

> **Tức là:** Information phụ là có thật, nhưng cách dùng đúng là *veto có điều kiện (conditional veto)* trong vùng weak-VDO, chứ không phải áp dụng điều kiện cứng (hard-AND) cho toàn cục.

---

## 5. Những Gì Không Thắng?

- **Bounded rescue:** Có tồn tại edge, nhưng lợi ích nhỏ hơn rất nhiều (ví dụ best weak-negative rescue chỉ đạt Sharpe `1.152770`).
- **Train-threshold one-signal ceiling test:** Có một ứng viên aggregate rất cao (`train_veto_ema28_net_quote_norm_28` đạt sharpe `1.373652`), nhưng chỉ có 2/4 folds dương so sánh với baseline. Tức là nhìn giống extractive fit (overfit dữ liệu), không đẹp/tự nhiên bằng winner natural rule.

---

## 6. Mechanism (Cơ Chế Hoạt Động Thực Tế)

So với baseline VDO, winner tạo ra **39 direct veto events** trên tập OOS:
- **10 full vetoes (Loại bỏ hoàn toàn):** Toàn bộ các trade mà baseline vào lệnh ở đó đều thua lỗ.
- **29 delays (Trì hoãn vào lệnh):** Các candidate vào lệnh muộn hơn trung bình 10.6 bars.

**Đọc đúng ý nghĩa của cơ chế này:**
1. Nó chặn được một cụm trades rác (junk trades) thuộc vùng weak-VDO.
2. Nó retime (căn chỉnh lại thời điểm) cho một cụm các lệnh entry vào quá sớm ở thời điểm VDO còn yếu.

Đây chính xác đúng là kiểu mechanism logic mà chúng ta muốn thấy, không phải do "ngẫu nhiên giảm trade rồi làm Sharpe nhảy lên".

---

## 7. Caveat (Lưu Ý Quan Trọng)

Tôi cũng đã kiểm tra phần khó chịu nhưng phải nói sự thật:
- Một *frozen approximation* của rule này với `weak_vdo_thr = 0.006481` **không chiến thắng** được baseline ở giai đoạn kiểm tra cũ (trước năm 2021).

**Kết luận từ Caveat:**
- Phát hiện này nên được đọc là một cải thiện có thật trong giao thức OOS đã khóa.
- Nó mang đậm mùi cấu trúc của thị trường hậu 2021 (post-2021 structure), chứ không phải là một "định luật vĩnh cửu" đúng tuyệt đối với mọi epoch từ 2018.

---

## 8. Tài Liệu Đi Kèm

Các tài liệu tham khảo chi tiết trong Bundle kết quả:
- Báo cáo đầy đủ
- Tóm tắt điều hành
- Spec chi tiết rule thắng
- Bảng tổng hợp toàn bộ natural policies
- Bảng train-threshold ceiling tests
- Phân rã direct veto OOS

---

> **🚀 KẾT LUẬN CHỐT:**
> Entry path tốt nhất hiện tại là **giữ VDO làm core, rồi thêm bounded conditional veto trên vùng weak positive VDO** bằng `activity + freshness`. Đây là hướng đi đúng đắn và hiệu quả hơn hẳn so với việc cố sức "phát minh ra một VDO mới".
