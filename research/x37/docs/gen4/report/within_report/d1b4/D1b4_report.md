# D1b4 Report — Measurements: Cross-TF & Ranking

## 1. Cross-Timeframe Conditioning

**Điểm mạnh nhất:**

- **D1 anti-vol → 4h trend:** đây là permission state sạch nhất.
  - 4h ret_168 đi từ 613.3 bp spread vô điều kiện lên 901.1 bp trong trạng thái D1 anti-vol thuận lợi; Spearman tăng từ 0.177 lên 0.268.
- **D1 trend → 4h trend:** có tác dụng thật, không phải trùng lặp giả.
  - Với D1 trend thuận: 4h ret_168 còn 690.6 bp.
  - Với D1 trend nghịch: nó lật âm còn -168.9 bp.
- **4h trend → 1h:** cải thiện cả continuation lẫn recovery.
  - 1h ret_12: 11.4 bp → 15.1 bp khi 4h trend thuận.
  - 1h ret_168 reversal: 48.7 bp → 101.4 bp khi 4h trend thuận.
- **4h high-vol → 1h ret_12:** không phải permission tốt.
  - 1h ret_12 yếu đi trong nền 4h high-vol: 7.5 bp so với 16.1 bp trong nền 4h low-vol.
- **1h trend → 15m ret_42:** stacking cùng chiều bị "đuối".
  - 15m ret_42 giảm từ 11.6 bp xuống 1.4 bp khi 1h trend đã dương rõ.
- **1h long-reversal state → 15m ret_42:** hợp pha hơn.
  - 15m ret_42 tăng từ 10.1 bp lên 13.3 bp khi 1h đang ở trạng thái hồi phục/pullback.

**Kết luận gọn:**

- D1 → 4h và 4h → 1h có permission thật.
- 1h → 15m không ủng hộ kiểu chồng continuation một cách mù quáng.

## 2. Redundancy Map

**Các cặp trùng lặp mạnh nhất:**

| Cặp | rho |
|---|---|
| 1h fast continuation vs 15m fast continuation | 0.908 |
| D1 flow exhaustion vs 4h flow exhaustion | 0.870 |
| 1h flow exhaustion vs 15m flow exhaustion | 0.856 |
| 4h trend vs 4h ret trend | 0.828 |
| 1h trade surprise vs 15m trade surprise | 0.704 |

**Các cặp mạnh nhưng khá độc lập:**

| Cặp | rho |
|---|---|
| D1 anti-vol vs D1 flow exhaustion | -0.039 |
| D1 anti-vol vs D1 trade surprise | -0.038 |
| 4h trend vs 4h flow exhaustion | -0.103 |
| 15m medium continuation vs 15m activity | -0.021 |

**Cấu trúc block sau khi gom họ tín hiệu:**

- **Slow trend block:** D1 trend, 4h trend, 4h ret trend
- **Flow exhaustion block:** D1/4h/1h/15m taker reversal
- **Activity / participation block:** relvol, intraday trade surprise, phần lớn calendar magnitude
- **Fast continuation block:** 1h ret_12, 15m ret_42
- **Pullback / recovery block:** 1h long reversal, 15m drawdown rebound
- **Volatility state:** không cùng dấu theo scale; D1 anti-vol và 4h pro-vol không được gộp chung

**Một điểm quan trọng:** block flow exhaustion gần như one-sided trong discovery so với baseline warmup. Tỷ lệ thời gian ở phía thuận lợi:

| Scale | Tỷ lệ thời gian thuận lợi |
|---|---|
| D1 | 100.00% |
| 4h | 100.00% |
| 1h | 99.57% |
| 15m | 99.68% |

Nghĩa là nó mạnh như background state, nhưng không phải binary gate đẹp trong discovery.

## 3. Channel Ranking

**Top tín hiệu độc lập mạnh nhất sau khi trừ trùng lặp:**

1. D1 anti-vol
2. D1 flow exhaustion
3. 4h trend
4. D1 trend
5. 15m activity state
6. D1 trade surprise
7. 15m medium continuation (ret_42)
8. 1h long reversal (ret_168)
9. 4h pro-vol directional state
10. 15m deep-drawdown rebound

**Đọc đúng bảng xếp hạng này:**

- **Slow directional core:** D1 anti-vol + D1 flow exhaustion + 4h trend
- **Fast directional core:** 15m ret_42, nhưng chỉ tốt khi đúng pha
- **Recovery core:** 1h long reversal
- **Timing / magnitude core:** 15m activity

**Những thứ không nên đếm hai lần:**

- nhiều biến thể flow exhaustion đa khung
- cả 1h fast continuation và 15m fast continuation
- activity + calendar magnitude như thể là hai nguồn edge độc lập

## 4. Consolidated Summary

Bức tranh D1b hoàn chỉnh sau D1b4 là:

- **Trend chậm** có thật, mạnh nhất ở 4h và D1
- **Volatility** là state variable, nhưng dấu hiệu directional đổi theo scale
- **Taker imbalance** chủ đạo là exhaustion / reversal, không phải continuation mặc định
- **Relative volume** là timing/magnitude channel xuất sắc, không nên nhầm với directional engine
- **1h → 15m continuation stacking** là chỗ dễ tự lừa mình nhất; dữ liệu không ủng hộ nó
- **Calendar** chủ yếu là magnitude seasonality và phần lớn alias cho activity block

**Những thứ bị loại khỏi nhóm tín hiệu chính:**

- daily gaps
- calendar direction
- raw trade residual chưa de-drift
- generic intraday compression breakout
- giả định "taker flow luôn là continuation"

---

Toàn bộ bước này vẫn là candidate-mining-only trên historical snapshot; không có clean external OOS claim.
