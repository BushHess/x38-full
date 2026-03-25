# Prompt tự viết cho nghiên cứu BTCUSDT H4 + D1

Bạn đang nghiên cứu BTCUSDT spot long-only từ dữ liệu thô H4 và D1. Mục tiêu không phải là “bịa ra một chiến lược hay”, mà là tìm ra thiết kế có giá trị thực tế cao nhất mà dữ liệu hỗ trợ được, dưới một protocol nghiêm ngặt, leak-free, cost-aware và có thể audit.

## Mục tiêu đúng
- Tìm **ứng viên mạnh nhất và đáng dùng nhất** trong bối cảnh dữ liệu hiện có.
- Không dùng ngôn ngữ tuyệt đối kiểu “tối ưu toàn cục”, “chân lý cuối cùng”, hay “untouched-holdout proof” nếu dữ liệu đó đã bị dùng để định hướng nghiên cứu.
- Tách bạch rõ:
  1. **Bằng chứng** đến từ dữ liệu và kiểm định.
  2. **Suy luận thiết kế** rút ra từ bằng chứng.
  3. **Phán đoán thực chiến** khi phải cân bằng Sharpe, drawdown, turnover, đơn giản và khả năng sống sót out-of-sample.

## Kỷ luật bắt buộc
- Bắt đầu từ dữ liệu thô.
- Khóa protocol trước discovery:
  - split,
  - metric,
  - bootstrap,
  - plateau test,
  - complexity budget,
  - execution model.
- Không thay đổi protocol sau khi đã nhìn thấy kết quả ứng viên.
- Không nhìn trước benchmark specs cho đến khi ứng viên đã được freeze.
- Không có lookahead:
  - signal tại bar close,
  - fill tại next bar open,
  - dùng D1 trên H4 chỉ được nhìn thấy D1 bar đã đóng xong.
- Trading cost cố định: 10 bps mỗi phía.

## Tư duy đúng
- Dữ liệu quyết định cơ chế. Không ép dữ liệu vào một “ý tưởng đẹp”.
- Đầu tiên phải đo xem edge nằm ở đâu:
  - persistence / continuation,
  - mean-reversion,
  - volatility state,
  - location in range,
  - breakout / compression,
  - order flow / taker imbalance,
  - quan hệ chéo H4 ↔ D1,
  - regime dependence,
  - turnover-cost tradeoff.
- Ưu tiên kiến trúc ít thành phần, dễ diễn giải, có plateau, và sống sót qua cost / bootstrap / ablation.
- Nếu một thành phần chỉ làm đẹp in-sample nhưng không cải thiện paired comparison hoặc chỉ tạo peak sắc nhọn, loại bỏ.

## Deliverable bắt buộc
Bạn phải trả ra **hai lớp kết quả**:
1. **Ứng viên khoa học**: ứng viên tốt nhất từ pipeline discovery nghiêm ngặt, không nhồi thêm “mẹo”.
2. **Ứng viên thực chiến cuối**: có thể dùng thêm những hiểu biết tích lũy được trong toàn bộ nghiên cứu để tinh chỉnh vừa đủ, nhưng phải gắn nhãn trung thực rằng đây là sản phẩm của bối cảnh đã bị “contaminated” bởi các vòng nghiên cứu trước.

## Pipeline bắt buộc
### Phase 0 — Data audit
- Đọc protocol.
- Kiểm tra file thô, cột, timezone, duplicate, gap, missing.
- Khóa split và execution assumptions.

### Phase 1 — Data decomposition
- Đo predictive content của từng kênh tín hiệu trên nhiều horizon.
- Báo cáo decay horizon, turnover, sensitivity với cost, và phụ thuộc regime.
- Phân biệt rõ “edge thô” với “edge sau execution”.

### Phase 2 — Mechanism discovery
- Bắt đầu bằng các state machine đơn giản:
  - single-feature state systems,
  - dual-gate systems giữa D1 và H4,
  - entry-only confirmation filters nếu có lý do dữ liệu ủng hộ.
- Không bắt đầu bằng kiến trúc phức tạp.

### Phase 3 — Robustness screening
- Walk-forward dev-only.
- Cost sensitivity.
- Moving-block bootstrap.
- Paired bootstrap giữa các ứng viên gần nhau.
- Ablation để xem thành phần nào là lõi, thành phần nào chỉ “ăn theo”.
- Plateau / perturbation để tránh chọn một peak nhọn.

### Phase 4 — Freeze
- Chọn ứng viên khoa học tốt nhất.
- Sau đó, và chỉ sau đó, mới được dùng hiểu biết tích lũy trong toàn bộ quá trình để làm một bản thực chiến cuối nếu nó thực sự cải thiện chất lượng theo paired comparison và không phá tính đơn giản.

## Nguyên tắc ra quyết định
- Không chọn chiến lược chỉ vì Sharpe full-sample cao nhất.
- Không chọn chiến lược có drawdown nông nhưng edge mỏng / turnover cao vô lý / hit-rate quá tệ.
- Không chọn chiến lược dựa trên peak tham số sắc nhọn.
- Không dùng một thành phần làm exit nếu dữ liệu cho thấy nó chỉ nên làm entry gate.
- Nếu H4 nhanh chỉ tạo flip/chop, hạ vai trò của nó xuống state/timing thay vì alpha carrier.
- Nếu order flow chỉ hữu ích ở thời điểm entry, không ép nó tham gia hold/exit.

## Cách viết kết luận
- Nói thẳng chiến lược nào thắng, vì sao thắng, và vì sao các hướng khác thua.
- Nói rõ mức độ tin cậy:
  - strict scientific,
  - practical but contaminated,
  - không thể kết luận.
- Nếu không có untouched-holdout proof sạch, phải nói rõ. Không được ngụy trang.
