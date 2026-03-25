# E5_EMA21D1 — Research Memo for Performance Improvement

**Date:** 2026-03-14  
**Scope:** cải thiện hiệu suất và độ bền out-of-sample của E5 + EMA21D1  
**Nguyên tắc:** ưu tiên nhánh có xác suất thắng cao, gần với kiến trúc hiện tại, ít overfit, ít tăng độ phức tạp vận hành.

---

## 1. Kết luận điều hành

Nếu mục tiêu là cải thiện hiệu suất của E5 một cách thực dụng, thứ tự ưu tiên nên là:

1. **Bật và xác thực lại `regime_monitor` đã có sẵn**
2. **Bỏ binary all-in / all-out, chuyển sang volatility-targeted sizing**
3. **Nâng D1 regime từ boolean sang regime-strength filter**
4. **Sửa đúng nhánh exit hysteresis: chỉ gate soft exit, không trì hoãn hard stop**
5. **Thêm shock cooldown / re-entry delay sau hard stop hoặc volatility spike**
6. **Bổ sung overlay crowding từ perpetuals (funding + OI + basis + long/short)**
7. **Chỉ sau đó mới cân nhắc nhánh phức tạp như order-book / ML**

Điểm mấu chốt: đừng mất thời gian vặn thêm `vdo_threshold` dương nếu chưa có bằng chứng mới. Kiến trúc hiện tại đang mạnh nhất ở phần trend + risk control; headroom lớn nhất nhiều khả năng nằm ở **sizing, regime-strength, stateful exits và crowding/risk overlays**.

---

## 2. Cái E5 đang làm tốt

Theo spec hiện tại, E5 có ba điểm mạnh rõ ràng:

1. **Trend filter đa tầng nhưng vẫn gọn:** H4 EMA trend + VDO xác nhận + D1 regime
2. **Risk control hợp lý:** Robust ATR trailing stop tránh “nổ stop” vì spike TR cực lớn
3. **Execution model rõ ràng:** close-to-open, warmup dài, harsh cost model, không mập mờ

Nói cách khác, lõi của E5 không yếu. Điểm cần nâng cấp là **chất lượng state management** và **phân bổ rủi ro**, không phải phá đi rồi làm lại từ đầu.

---

## 3. Những điểm đang giới hạn hiệu suất

### 3.1 Binary position sizing đang quá thô

Hiện tại hệ thống hoặc vào 100% NAV, hoặc về 0%. Điều này khiến hệ thống bỏ phí thông tin về mức độ rủi ro theo regime. Khi volatility tăng mạnh, cùng một tín hiệu entry nhưng risk/return trade-off rất khác so với lúc vol thấp.

### 3.2 D1 regime filter còn quá nhị phân

Điều kiện hiện tại chỉ là:

```text
regime_ok = d1_close > d1_ema
```

Vấn đề: “vừa nằm trên EMA một chút” và “bứt rõ ràng, EMA dốc lên mạnh” hiện bị xem như nhau.

### 3.3 Exit logic vẫn còn one-state ở nhánh EMA reversal

Trailing stop là hard risk control tốt. Nhưng nhánh `ema_fast < ema_slow` vẫn là kiểu **flip là thoát**, chưa có persistence / band / context.

### 3.4 Một lớp guard đã được research-promote nhưng đang tắt

`regime_monitor` đã có trong spec và còn được ghi nhận đã PROMOTE, nhưng default vẫn tắt. Đây là cơ hội cải thiện “rẻ” nhất.

### 3.5 Hệ thống chưa đọc tín hiệu crowding từ thị trường perpetuals

BTC spot ngày nay bị chi phối mạnh bởi dòng vị thế và funding ở perpetuals. Một hệ thống spot trend-following mà bỏ qua funding / basis / OI thì đang bỏ qua một lớp state quan trọng của thị trường.

---

## 4. Hướng cải thiện ưu tiên cao

## 4.1 Promote lại `regime_monitor` ngay

### Tại sao nên làm trước

Đây là nhánh ít code nhất và sát với spec nhất. Nếu tài liệu nội bộ ghi đúng, monitor này đã từng cho:

- Sharpe tăng
- chặn được nhiều entry xấu
- hoạt động như một lớp “market health guard” ở D1

### Cách triển khai đúng

Không nên “tin luôn” kết quả cũ. Nên mở một branch xác thực lại với đúng pipeline hiện tại:

- baseline: E5 hiện tại
- variant: E5 + `enable_regime_monitor = true`
- giữ nguyên mọi thứ khác

### Điều cần theo dõi thêm

- trade count giảm bao nhiêu
- tỷ lệ entry bị chặn ở bull vs bear vs chop
- MDD tail có giảm thật hay chỉ là may mắn sample

### Đánh giá

Đây là **đòn bẩy tốt nhất / chi phí thấp nhất**. Nếu branch này không còn giữ được lợi thế trên holdout, mới tính bước kế tiếp.

---

## 4.2 Thêm volatility-targeted sizing

### Luận điểm

Nghiên cứu về volatility-managed portfolios và volatility-scaled momentum cho thấy việc giảm exposure khi volatility gần đây cao có thể cải thiện Sharpe và alpha; trong một số nghiên cứu, Sharpe tăng rất đáng kể so với phiên bản không quản trị volatility. Điều này đặc biệt hợp logic cho một hệ thống trend-following đang dùng trailing stop và vốn nhạy với state volatility.

### Điểm mạnh của nhánh này

- Không cần tìm alpha mới
- Không phá entry / exit logic đang chạy tốt
- Tấn công trực diện vào MDD và Sharpe

### Biến thể đề xuất

#### Variant A — Continuous vol targeting

```text
realized_vol = annualized_std(H4 returns, lookback = 30d equivalent)
target_exposure = clip(target_vol / realized_vol, 0.0, 1.0)
```

Entry/exit giữ nguyên, chỉ thay `target_exposure` từ binary sang continuous.

#### Variant B — 3-bucket sizing

```text
Nếu realized_vol <= vol_low  -> exposure = 1.00
Nếu vol_low < realized_vol <= vol_high -> exposure = 0.50
Nếu realized_vol > vol_high -> exposure = 0.25 hoặc 0
```

Biến thể này dễ audit hơn continuous sizing.

### Gợi ý preregistration

- không quá 2 cách sizing
- lookback vol cố định
- không tối ưu hóa grid rộng

### Nhận định thẳng

Nếu phải chọn **một** hướng có khả năng cải thiện Sharpe cao nhất mà vẫn ít overfit, tôi chọn **volatility-targeted sizing**.

---

## 4.3 Nâng D1 regime từ boolean sang strength-aware filter

### Vấn đề

`d1_close > d1_ema` quá thô. Nhiều false-positive regime sẽ lọt qua chỉ vì giá nằm trên EMA rất mỏng.

### Hướng sửa tốt nhất

Không thay D1 EMA21. Chỉ thêm **độ mạnh của regime**.

#### Variant B1 — D1 EMA slope confirmation

```text
regime_ok = (d1_close > d1_ema) AND (slope(d1_ema, 3) > 0)
```

#### Variant B2 — D1 distance band

```text
dist = (d1_close - d1_ema) / d1_atr
regime_ok = (d1_close > d1_ema) AND (dist > b)
```

#### Variant B3 — slope + distance nhẹ

```text
regime_ok = (d1_close > d1_ema)
            AND (slope(d1_ema, 3) > 0)
            AND (dist > b_small)
```

### Vì sao hợp lý

Trend-following literature xem moving-average cross và time-series momentum là cùng họ tín hiệu; tức mở rộng bằng slope / band là hợp logic, không phải nhảy sang một hệ khác. Đồng thời, nghiên cứu về trend breaks cho thấy turning points là chỗ chiến lược trend-following mất nhiều alpha nhất; thêm regime strength là cách hợp lý để tránh bám vào các trend quá yếu.

### Kỳ vọng thực tế

- Trade count giảm vừa phải
- Win rate có thể tăng
- CAGR có thể giữ nguyên hoặc giảm nhẹ
- Sharpe / MDD có xác suất cải thiện nếu lọc đúng “weak-above-EMA” entries

---

## 4.4 Sửa đúng nhánh exit hysteresis

Nhánh này đã được sửa lại trong `f_exit_hysteresis_PLAN.md`.

### Quan điểm

Muốn giảm whipsaw thì nên làm ở **soft exit**, không đụng hard stop trước.  
Nếu không tôn trọng nguyên tắc đó, mọi cải thiện trade count có thể đổi bằng MDD xấu hơn.

### Thứ tự hợp lý

1. persistence cho EMA exit
2. band hysteresis cho EMA spread
3. thêm Q-VDO-RH level / confidence như confirmation
4. chỉ mở nhánh trailing-stop stateful nếu baseline audit chứng minh stop mới là nguồn whipsaw chính

---

## 4.5 Thêm shock cooldown / re-entry delay

### Tại sao đáng làm

Nghiên cứu về intraday crypto return predictability cho thấy động học momentum / reversal thay đổi rõ quanh các cú jump lớn và thanh khoản. Nói đơn giản: sau cú sốc, thị trường thường ở trạng thái “bẩn”, và việc vào lại ngay dễ thành overtrading.

### Biến thể đơn giản

#### Variant C1 — Cooldown sau hard stop

```text
Nếu exit do hard stop:
  không cho entry mới trong 2 bar H4 tiếp theo
```

#### Variant C2 — Cooldown sau volatility shock

```text
Nếu TR hiện tại > Q99(TR rolling 180d):
  khóa entry trong N bar
```

#### Variant C3 — Cooldown có ngoại lệ theo regime mạnh

```text
cooldown active
nhưng bỏ cooldown nếu D1 slope rất mạnh và VDO bật lại rõ
```

### Nhận định

Đây là nhánh có thể giảm phí và slippage gián tiếp khá tốt, đặc biệt dưới harsh cost model.

---

## 4.6 Thêm overlay crowding từ perpetual futures

### Tại sao rất đáng nghiên cứu

Thị trường BTC spot hiện không thể xem như tách rời perpetuals. Binance công khai sẵn nhiều dữ liệu crowding / leverage state như:

- funding rate history
- open interest hiện tại
- open interest statistics theo nhiều khung thời gian
- basis
- long/short ratio
- top trader long/short ratio
- taker buy/sell volume

Tức là dữ liệu cho một lớp state overlay đã **có sẵn** về mặt hạ tầng.

### Cách dùng đúng

Không dùng làm alpha chính ngay.  
Dùng làm **overlay giảm rủi ro** hoặc **throttle exposure**.

#### Variant D1 — Crowding throttle cho entry

```text
crowding_hot = (funding_z > 2) AND (oi_z > 1.5) AND (basis_z > 1)

Nếu crowding_hot:
  exposure *= 0.5
```

#### Variant D2 — Crowding-aware trail multiplier

```text
Nếu market overcrowded long:
  trail_mult = 2.5 thay vì 3.0
Ngược lại:
  trail_mult = 3.0
```

#### Variant D3 — Panic deleveraging guard

```text
Nếu funding rất âm + OI co mạnh + basis xấu:
  khóa entry mới hoặc ép giảm exposure
```

### Lưu ý rất quan trọng

Một số endpoint lịch sử như open-interest statistics / basis / long-short ratio trên Binance chỉ cung cấp **cửa sổ gần** (ví dụ latest 30 days trên một số endpoint). Nghĩa là nếu muốn backtest dài, bạn phải:

- đã archive dữ liệu từ trước, hoặc
- lấy từ vendor khác, hoặc
- bắt đầu thu thập ngay bây giờ cho forward research

### Nhận định

Đây là nhánh có tiềm năng lớn nhưng phụ thuộc dữ liệu lịch sử.  
Nếu chưa có data archive, nó nên là **medium-term branch**, không phải thứ đốt thời gian trước mắt.

---

## 4.7 Advanced branch: order-flow / order-book driven volatility state

### Khi nào nên xét

Chỉ xét sau khi 5 nhánh trên đã được kiểm chứng. Không làm trước.

### Lý do

Có nghiên cứu cho thấy order flow và limit order book chứa thông tin hữu ích cho dự báo realized volatility ngắn hạn của BTC. Nếu dự báo được short-term volatility state tốt hơn, ta có thể làm dynamic trailing stop tốt hơn.

### Ứng dụng hợp lý

- không dự báo return trực tiếp
- chỉ dự báo **volatility regime** hoặc **liquidity stress**
- từ đó đổi `trail_mult` hoặc giảm exposure

### Ví dụ

```text
predicted_vol_high -> trail_mult rộng hơn + exposure thấp hơn
predicted_vol_low  -> trail_mult chuẩn + exposure bình thường
```

### Cảnh báo

Đây là nhánh nặng data, nặng infra, dễ biến thành project riêng. Không phải ưu tiên số 1.

---

## 5. Những hướng nên hạ ưu tiên hoặc né hẳn

## 5.1 Đừng quay lại positive VDO thresholding nếu chưa có bằng chứng mới

Spec hiện tại dùng `vdo_threshold = 0.0`, và nhánh X34 đã nêu rủi ro over-filtering khi đẩy threshold dương ở entry. Nếu quay lại tune threshold dương ngay bây giờ thì rất dễ tái diễn sai lầm cũ.

## 5.2 Đừng nhảy thẳng sang ML dự báo return của BTC

Một nghiên cứu gần đây cảnh báo rằng trong khung out-of-sample nghiêm ngặt, hầu như không có mô hình ML nào dự báo return/volatility của Bitcoin đủ tin cậy; nhiều kết quả đẹp nằm chủ yếu ở training set. Tức là nhảy sang ML quá sớm có xác suất rất cao chỉ tạo thêm overfit đẹp trên giấy.

## 5.3 Đừng đồng thời sửa quá nhiều lớp

Ví dụ tệ nhất:

- đổi sizing
- đổi entry filter
- đổi D1 regime
- đổi exit hysteresis
- thêm derivatives overlay

cùng lúc.

Làm vậy thì khi performance đổi, bạn sẽ không biết alpha đến từ đâu.

---

## 6. Roadmap thực thi khuyến nghị

## Phase A — Nhánh “thắng nhanh”

1. `A1_regime_monitor_on`
2. `A2_vol_target_sizing`
3. `A3_d1_strength_filter`

## Phase B — Nhánh stateful execution

4. `B1_exit_hysteresis_corrected`
5. `B2_shock_cooldown`

## Phase C — Nhánh market-state ngoài spot OHLCV

6. `C1_perp_crowding_overlay`
7. `C2_orderflow_vol_state`

### Thứ tự ưu tiên nếu chỉ được chọn 3 việc

1. `regime_monitor`
2. `volatility-targeted sizing`
3. `D1 regime-strength filter`

Đó là ba nhánh có tỷ lệ **signal / complexity** tốt nhất.

---

## 7. Bảng chấm điểm nhanh

| Nhánh | Kỳ vọng Sharpe | Kỳ vọng MDD | Độ khó | Rủi ro overfit | Ưu tiên |
|---|---:|---:|---:|---:|---:|
| Regime monitor ON | Trung bình | Tốt | Thấp | Thấp | Rất cao |
| Vol-target sizing | Cao | Tốt | Thấp-Trung bình | Thấp | Rất cao |
| D1 strength filter | Trung bình | Tốt | Trung bình | Trung bình thấp | Cao |
| Exit hysteresis đúng bài | Trung bình | Trung bình | Trung bình | Trung bình | Cao |
| Shock cooldown | Trung bình | Trung bình | Thấp | Trung bình thấp | Khá cao |
| Perp crowding overlay | Có thể cao | Tốt | Trung bình-Cao | Trung bình | Trung bình |
| Order-flow vol state | Chưa rõ | Chưa rõ | Rất cao | Cao | Thấp trước mắt |
| ML return prediction | Không khuyến nghị sớm | Không rõ | Rất cao | Rất cao | Rất thấp |

---

## 8. Kết luận cuối

Muốn nâng E5_EMA21D1, hướng khôn nhất không phải là “thêm indicator cho nhiều”.  
Hướng khôn nhất là:

- **dùng tốt hơn cái đang có**,
- **phân bổ rủi ro thông minh hơn**,
- **làm state machine tốt hơn**,
- và chỉ sau đó mới mở rộng ra dữ liệu phái sinh / order flow.

Nói ngắn gọn:

- **bật regime monitor**
- **thêm vol-target sizing**
- **làm D1 regime mạnh hơn**
- **sửa exit hysteresis cho đúng bài toán**

Bốn việc này thực tế hơn nhiều so với lao vào ML hoặc tune indicator thêm một vòng nữa.

---

## 9. Tài liệu tham chiếu dùng cho memo

### Nội bộ

- `E5_EMA21D1_Spec.md`
- `f_exit_hysteresis_PLAN.md` (bản đã sửa)

### Bên ngoài

- Moreira & Muir — *Volatility Managed Portfolios*
- Kim, Tse & Wald — *Time Series Momentum and Volatility Scaling*
- Levine & Pedersen — *Which Trend Is Your Friend?*
- Goulding, Harvey & Mazzoleni — *Breaking Bad Trends*
- Wen et al. — *Intraday Return Predictability in the Cryptocurrency Markets*
- Liu & Tsyvinski — *Risks and Returns of Cryptocurrency*
- Wang et al. — *The Training Set Delusion*
- Binance Open Platform docs for funding / OI / basis / long-short / taker flow
