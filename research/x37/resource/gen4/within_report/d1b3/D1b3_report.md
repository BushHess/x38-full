# D1b3 Report — Measurements: Volume & Flow

## 1. Volume & Flow Channels

**Điểm chính:**

- Volume clustering rất mạnh ở cả 4 timeframe. Log-volume ACF lag 1 nằm trong khoảng 0.83–0.87; lag 24 vẫn còn 0.58–0.69.
- Taker imbalance có persistence thấp hơn nhiều. ACF lag 1 chỉ khoảng 0.14–0.22 và tắt nhanh.
- Relative volume là kênh dự báo biên độ rõ rệt hơn nhiều so với dự báo hướng.
- Taker flow không phải continuation signal thuần. Nó có pocket continuation ở 15m/1h, nhưng hiệu ứng trội là long-horizon reversal.
- Trade count beyond volume chỉ có ý nghĩa sau khi khử drift. Raw residual bị lệch cấu trúc quá mạnh trong discovery.

**Các tín hiệu nổi bật theo timeframe:**

| TF | Relative volume — hướng | Relative volume — biên độ | Taker flow — continuation pocket | Taker flow — reversal pocket |
|---|---|---|---|---|
| 15m | W=168, H=84, t=7.44 | W=168, H=1, t=43.17 | W=84, H=12, t=4.10 | W=168, H=168, t=-9.97 |
| 1h | W=84, H=24, t=4.34 | W=168, H=1, t=22.33 | W=84, H=84, t=5.19 | W=84, H=168, t=-9.01 |
| 4h | W=12, H=6, t=2.36 | W=168, H=1, t=13.07 | W=84, H=24, t=2.70 | W=168, H=168, t=-11.86 |
| 1d | W=168, H=84, t=2.03 | W=168, H=3, t=4.99 | W=12, H=6, t=1.56 | W=12, H=168, t=-15.85 |

**Kết luận thẳng:**

- Relative volume dùng tốt để đo "sắp có biến động mạnh hay không", đặc biệt ở 15m/1h/4h.
- Taker buy pressure dương không đồng nghĩa giá sẽ tiếp tục đi lên. Trên horizon dài, đặc biệt 4h/1d, nó thường đi kèm underperformance về sau.
- Ở 15m/1h, order flow có hai mặt: continuation ở horizon trung bình, nhưng nếu kéo dài ra thì chuyển thành reversal.
- Với `num_trades`, mô hình warmup `log1p(num_trades) ~ log1p(volume)` đã giải thích gần hết biến thiên: correlation khoảng 0.95–0.97. Raw residual vì thế không sạch; phải de-drift rồi mới đo được tín hiệu.

**Về volume spike:**

- Spike chủ yếu là phản ứng sau move, không phải tín hiệu breakout thuần.
- Tỷ lệ độ mạnh thống kê giữa past-move và future-move nằm khoảng 1.95x–2.63x ở cả 4 timeframe.
- Tuy vậy, intraday vẫn có hiệu ứng dự báo future magnitude rất ngắn hạn ngay sau spike:
  - 15m: W=168, H=1, t=31.68
  - 1h: W=168, H=1, t=14.88
  - 4h: W=168, H=1, t=8.74
- Riêng 1d thì volume spike lớn lại giống dấu hiệu late-event exhaustion hơn là chuẩn bị bùng nổ tiếp.

## 2. Calendar Effects

**Kết luận ngắn gọn:**

- Calendar direction phần lớn là yếu hoặc nhiễu.
- Calendar magnitude thì có tín hiệu lặp lại khá rõ.

**Các hiệu ứng nổi bật:**

| TF | Weekday direction | Hour direction | Weekday magnitude | Hour magnitude |
|---|---|---|---|---|
| 15m | Fri vs Thu, t=0.69 | 21 vs 02 UTC, t=2.21 | Fri vs Sat, t=17.01 | 15 vs 03 UTC, t=11.23 |
| 1h | Fri vs Thu, t=1.38 | 21 vs 02 UTC, t=1.75 | Fri vs Sat, t=10.94 | 23 vs 17 UTC, t=4.70 |
| 4h | Fri vs Sat, t=0.93 | 12 vs 20 UTC, t=0.64 | Fri vs Sat, t=6.32 | 08 vs 00 UTC, t=7.53 |
| 1d | Thu vs Wed, t=0.46 | — | Wed vs Fri, t=4.61 | — |

**Nói gọn:**

- Không có weekday/hour edge mạnh theo hướng giá đủ sạch để coi là kênh directional độc lập.
- Nhưng seasonality của activity/biên độ thì có thật, nhất là ở 15m/1h.

## 3. Volume/Flow Channel Summary

**Các tín hiệu directional mạnh nhất:**

1. 1d taker-flow reversal — W=12, H=168, t=-15.85
2. 4h taker-flow reversal — W=168, H=168, t=-11.86
3. 15m taker-flow reversal — W=168, H=168, t=-9.97
4. 1d de-drifted trade surprise — W=168, H=168, t=9.14
5. 1h taker-flow reversal — W=84, H=168, t=-9.01
6. 15m de-drifted trade surprise — W=168, H=84, t=-7.80
7. 1h de-drifted trade surprise — W=168, H=168, t=-7.49
8. 15m relative volume — W=168, H=84, t=7.44

**Các tín hiệu magnitude mạnh nhất:**

1. 15m relative volume — W=168, H=1, t=43.17
2. 15m future magnitude after volume spike — W=168, H=1, t=31.68
3. 15m de-drifted trade surprise — W=168, H=1, t=-31.52
4. 1h relative volume — W=168, H=1, t=22.33
5. 1d taker-flow magnitude split — W=42, H=168, t=-20.61
6. 4h taker-flow magnitude split — W=84, H=168, t=-20.44
7. 15m weekday magnitude — Fri vs Sat, t=17.01
8. 1h de-drifted trade surprise — W=168, H=1, t=-16.88

**Phán quyết kỹ thuật:**

- Có tín hiệu thật ở volume/flow/calendar, nhưng chúng không cùng bản chất.
- **Volume** chủ yếu là magnitude state variable.
- **Taker flow** chủ yếu là reversal state variable ở horizon dài, không phải continuation mặc định.
- **Trade count** chỉ hữu dụng sau khi khử drift cấu trúc.
- **Calendar** hữu ích hơn cho biên độ/kỳ vọng activity hơn là cho hướng giá.

---

Đây vẫn là đo lường trên historical snapshot candidate-mining-only, không phải clean external OOS.
