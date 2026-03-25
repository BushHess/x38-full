# Đánh giá và kết luận để xây dựng Q-VDO-RH

## 1) Đánh giá tổng quát

Đánh giá thẳng: bản phân tích này **mạnh hơn AVFC gốc**, và kết luận chiến lược lớn là đúng: **ship bản đơn giản, sửa đúng lỗi cấu trúc trước; research bản phức tạp sau**.

Nhưng nó vẫn chưa phải bản cuối, vì còn hai chỗ xử chưa tới:

1. AVFC bị phạt hơi quá tay ở vài điểm.
2. WVDO lại được cho qua mà chưa mổ kỹ một lỗi kỹ thuật quan trọng của chính nó.

Về dữ liệu đầu vào, Binance futures kline thực sự đã cho sẵn `quote asset volume` và `taker buy quote asset volume`, nên signed notional flow làm được trực tiếp, không cần reconstruct vòng vo từ base volume. Về mặt microstructure, OFI ở order book có giá trị giải thích biến động ngắn hạn tốt hơn trade volume, nhưng nếu đem raw L2 vào crypto thì phải đối mặt với spoofing rất nặng. Còn BVC trong literature thì **không có verdict tuyệt đối** mà thay đổi theo market, mức noise và cách calibration.

---

## 2) Những điểm đồng ý mạnh

### 2.1 Tiêu chuẩn bằng chứng

Điểm mạnh nhất của lập luận là **tiêu chuẩn bằng chứng**.

AVFC không thể dùng checklist kiểu:
- walk-forward
- effect size
- regime stability
- turnover sau phí
- long/short symmetry
- OOS degradation

...để hạ VDO, rồi đến lượt mình lại xin miễn trừ vì “thiết kế hợp lý về mặt lý thuyết”.

Phần đó là đúng. Nếu đòi hỏi VDO phải vượt qua tiêu chuẩn thực chứng cao, thì AVFC cũng phải chịu đúng tiêu chuẩn đó.

### 2.2 Price acceptance bằng bar-VWAP là quá yếu

Phê AVFC ở chỗ dùng `A = tanh((Close - VWAP)/ATR)` là chính xác.

Với bar dài như 1H hay 4H:
- `VWAP = quoteVolume / volume` chỉ là average price của cả bar
- nó không đủ sắc để kết luận absorption ở cuối bar
- trong trend mạnh, close thường cùng phía với VWAP nên component này dễ thành redundant

Nói gọn: với kline data, bar-VWAP không phải một proxy đủ mạnh cho “acceptance” hay “absorption”.

### 2.3 OFI đúng về lý thuyết, nhưng crypto L2 không sạch

OFI ở order book đúng là giàu thông tin hơn trade volume trong lý thuyết microstructure. Nhưng trong crypto CEX, raw L2 không phải “miễn phí alpha”.

Điểm cần nhấn mạnh là:
- AVFC đúng ở tầng lý thuyết khi nhắc OFI / order-book imbalance
- nhưng nếu đem nguyên book imbalance thô vào production trên crypto thì rất dễ tự lừa mình do spoofing, quote stuffing, liquidity rút/đẩy giả

Cho nên: nói “VDO thua OFI” ở trên giấy là đúng; nhưng nói “hãy dùng raw OFI thay VDO trên crypto” thì lại thiếu thực dụng.

### 2.4 BVC fallback: đúng hướng, nhưng phải nói đủ

BVC là fallback hợp lệ hơn close-in-range, nhưng không được thần thánh hóa.

Điểm đúng là:
- standardized return làm proxy buy/sell flow hợp lý hơn candle geometry
- nhưng không nên khóa cứng vào normal CDF
- trong market fat-tail như crypto, Student-t CDF hoặc empirical CDF hợp lý hơn

Cách diễn đạt chuẩn là:
- BVC là **proxy có điều kiện**
- không phải “truth machine”
- phải de-rate confidence khi chạy fallback mode

---

## 3) Điểm chưa ổn trong kết luận trước: WVDO vẫn còn một lỗi kỹ thuật lớn

Đây là chỗ quan trọng nhất.

Nếu dùng:

```text
raw_t = (2 * takerBuyQuote_t - quoteVolume_t) / EMA(quoteVolume_t, N)
WVDO_t = VWMA(raw, fast) - VWMA(raw, slow)
```

thì đang **bơm volume hai lần**.

Lý do:
- `raw_t` đã mang signed notional flow, tức đã chứa participation theo notional
- sau đó lại dùng `VWMA(...)`, tức lại weight theo volume thêm một lần nữa

Về mặt toán học:

```text
VWMA(raw)_t = sum(q_i * raw_i) / sum(q_i)
            = sum(q_i * DeltaDollar_i / EMA(q_i)) / sum(q_i)
```

với `DeltaDollar_i = 2 * takerBuyQuote_i - quoteVolume_i`.

Nói ngắn gọn:
- raw đã mang volume/notional participation
- VWMA lại reweight theo volume
- kết quả là bar lớn bị nhấn quá mức

Đây chính là kiểu reweighting mà trước đó bị phê ở AVFC dưới nhãn “double-counting risk”.

### Kết luận phụ ở đây

**Không nên chọn WVDO theo kiểu “raw notional + VWMA”.**

---

## 4) Hai nhánh cần tách rõ: R-WVDO và Q-VDO

Để tránh nhập nhằng, nên tách thành hai loại hoàn toàn khác nhau.

### 4.1 R-WVDO

Giữ input là ratio bounded:

```text
r_t = (2 * takerBuyQuote_t - quoteVolume_t) / quoteVolume_t
```

Khi đó:

```text
R-WVDO_t = VWMA(r, fast) - VWMA(r, slow)
```

Đặc tính:
- volume-weighted ở tầng smoothing
- không giữ magnitude tuyệt đối
- ít rủi ro double-counting hơn kiểu raw-notional + VWMA

### 4.2 Q-VDO

Dùng input là signed notional đã normalize theo hoạt động bình thường:

```text
x_t = (2 * takerBuyQuote_t - quoteVolume_t) / (EMA(quoteVolume_t, slow) + eps)
Q-VDO_t = EMA(x, fast) - EMA(x, slow)
```

Đặc tính:
- giữ magnitude tương đối theo regime volume
- không cần VWMA nữa
- sửa đúng lỗi “mất magnitude” của VDO gốc mà không bị volume reweight hai lần

### Kết luận chọn hướng

Nếu mục tiêu là tối ưu VDO theo hướng thực dụng, bản nên chọn là **Q-VDO**, không phải WVDO kiểu “notional + VWMA”.

---

## 5) Những chỉnh sửa cần làm trong phần phán quyết

### 5.1 Không được chuyển trực tiếp bằng chứng của VDO gốc sang WVDO / Q-VDO

Một điểm cần siết lại:

Câu “prototype đã test thắng system chưa test” là đúng khi nói về **VDO gốc**, nhưng **không được chuyển nguyên xi sang WVDO hay Q-VDO**.

Một khi đã:
- đổi input từ ratio sang signed notional
- đổi threshold từ 0 sang adaptive
- đổi kernel smoothing

...thì đó đã là **indicator mới**.

Cho nên:
- `p = 0.031` của VDO gốc, nếu có, chỉ là bằng chứng gợi ý rằng order-flow style signal có thể có ích
- nó **không phải** bằng chứng trực tiếp cho WVDO hay Q-VDO

### 5.2 Chỉ đếm số parameter là chưa đủ

Phê AVFC vì complexity là đúng hướng, nhưng cách chốt tốt hơn không phải chỉ nói “parameter tăng theo cấp số nhân”.

Cái cần nhìn là:
- bao nhiêu parameter thực sự được tune
- bao nhiêu cái được khóa theo prior
- bao nhiêu quyết định được chọn sau khi đã nhìn backtest

Tức là phải nhìn **effective degrees of freedom**, không chỉ đếm số ký hiệu trong công thức.

### 5.3 Minimal AVFC không “trùng” WVDO

Nói minimal AVFC “gần như trùng WVDO” là hơi quá.

Nó vẫn khác ở hai điểm vật lý:
1. nó dùng signed notional normalized flow, không phải ratio weighted oscillator
2. nó có thêm level state tách khỏi momentum trigger

Điểm nên chốt không phải là “hai cái giống nhau”, mà là:

> full AVFC chưa chứng minh được rằng các lớp phức tạp thêm vào đáng giá hơn stripped core của chính nó.

### 5.4 `L > 0 AND M > Theta` không sai, nhưng chưa đáng hard gate ở v1

Cần công bằng ở đây.

Nếu AVFC được dùng như **entry engine**, thì hard gate kiểu:

```text
L > 0 AND M > Theta
```

...đúng là dễ trễ.

Nhưng nếu chỉ dùng như **confirmation filter**, thì trade-off precision cao hơn, recall thấp hơn là chuyện chấp nhận được.

Vấn đề thật sự không phải là “logic này sai”, mà là:

> logic này chưa được chứng minh là đáng cái giá mất early signal.

Cách thực dụng nhất ở v1 là:
- không dùng `L` làm điều kiện AND cứng
- dùng `L` làm context / confidence
- còn trigger chính vẫn để cho momentum signal đảm nhiệm

---

## 6) Thuật toán nên ship trước: Q-VDO-RH

`Q` = quote-notional normalized  
`RH` = robust threshold + hysteresis

Đây là bản practical tốt nhất ở thời điểm hiện tại.

Không phải full AVFC.  
Không phải WVDO kiểu volume-weighted trên raw notional.  
Mà là:

> **signed notional theo quote volume + EMA oscillator + robust adaptive threshold + hysteresis + level chỉ làm context**

---

## 7) Q-VDO-RH — Mode A: Có taker data

### 7.1 Công thức

Dùng trực tiếp dữ liệu quote volume và taker buy quote volume:

```text
DeltaQuote_t = 2 * takerBuyQuote_t - quoteVolume_t
```

Normalize theo activity bình thường:

```text
x_t = DeltaQuote_t / (EMA(quoteVolume_t, slow) + eps)
```

Tách momentum và level:

```text
m_t = EMA(x_t, fast) - EMA(x_t, slow)
l_t = EMA(x_t, slow)
```

Dùng robust scale thay vì EWSTD thuần để đỡ nhạy với fat-tail và liquidation spikes:

```text
scale_t = EMA(abs(m_t - EMA(m_t, slow)), slow) + eps
theta_t = k * scale_t
```

### 7.2 Rule thực dụng

```text
Long trigger  khi m_t >  theta_t
Short trigger khi m_t < -theta_t
```

Context / confidence:

```text
High confidence nếu sign(l_t) == sign(m_t)
Low confidence  nếu sign(l_t) != sign(m_t)
```

Hysteresis để tránh flip liên tục:

```text
Giữ long  cho tới khi m_t <  0.5 * theta_t
Giữ short cho tới khi m_t > -0.5 * theta_t
```

### 7.3 Vì sao bản này đáng ship

Bản này sửa đúng các lỗi cấu trúc chính:
- sửa lỗi mất magnitude của VDO ratio-based
- không over-engineer như full AVFC
- không volume reweight hai lần như WVDO kiểu raw-notional + VWMA
- số tunable thực sự có thể ép còn rất ít

Cách khóa parameter để giữ đơn giản:
- `N_vol = slow`
- `N_scale = slow`
- hysteresis ratio cố định = `0.5`

Khi đó tunable thực sự chỉ còn:
- `fast`
- `slow`
- `k`

---

## 8) Q-VDO-RH — Mode B: Không có taker data

Fallback mode không được giả vờ là cùng chất lượng với taker mode.

### 8.1 Công thức proxy

```text
r_t = log(C_t / C_{t-1})
```

Standardize bằng robust scale:

```text
z_t = r_t / (EMA(abs(r_t - EMA(r_t, slow)), slow) + eps)
```

Thay vì ép dùng normal CDF, dùng phân phối nặng đuôi hơn hoặc empirical mapping:

```text
p_t = F(z_t)
```

Trong đó `F` là một trong hai lựa chọn tốt hơn:
- Student-t CDF
- rolling empirical CDF

Sau đó dựng proxy normalized flow:

```text
x_t = gamma * (2 * p_t - 1) * quoteVolume_t / (EMA(quoteVolume_t, slow) + eps)
```

### 8.2 Nguyên tắc vận hành fallback

Fallback mode cần bị **de-rate confidence**.

Nói cách khác:
- có thể dùng cùng pipeline với Mode A
- nhưng phải tăng threshold hoặc giảm confidence
- không được coi fallback proxy là “tương đương taker truth”

---

## 9) Pseudocode triển khai Q-VDO-RH

### 9.1 Mode A — Có taker data

```python
def q_vdo_rh_with_taker(taker_buy_quote, quote_volume, fast, slow, k, eps=1e-12):
    delta_quote = 2.0 * taker_buy_quote - quote_volume
    x = delta_quote / (ema(quote_volume, slow) + eps)

    m = ema(x, fast) - ema(x, slow)
    l = ema(x, slow)

    scale = ema(abs(m - ema(m, slow)), slow) + eps
    theta = k * scale

    long_trigger  = m >  theta
    short_trigger = m < -theta

    long_hold  = m >  0.5 * theta
    short_hold = m < -0.5 * theta

    high_conf = sign(l) == sign(m)

    return {
        "x": x,
        "momentum": m,
        "level": l,
        "scale": scale,
        "theta": theta,
        "long_trigger": long_trigger,
        "short_trigger": short_trigger,
        "long_hold": long_hold,
        "short_hold": short_hold,
        "high_confidence": high_conf,
    }
```

### 9.2 Mode B — Không có taker data

```python
def q_vdo_rh_fallback(close, quote_volume, fast, slow, k, gamma=0.5, eps=1e-12):
    r = log(close / shift(close, 1))
    z = r / (ema(abs(r - ema(r, slow)), slow) + eps)

    # F có thể là student_t_cdf(z, df) hoặc empirical_cdf(z)
    p = F(z)

    x = gamma * (2.0 * p - 1.0) * quote_volume / (ema(quote_volume, slow) + eps)

    m = ema(x, fast) - ema(x, slow)
    l = ema(x, slow)

    scale = ema(abs(m - ema(m, slow)), slow) + eps
    theta = k * scale

    long_trigger  = m >  theta
    short_trigger = m < -theta

    long_hold  = m >  0.5 * theta
    short_hold = m < -0.5 * theta

    high_conf = sign(l) == sign(m)

    return {
        "x": x,
        "momentum": m,
        "level": l,
        "scale": scale,
        "theta": theta,
        "long_trigger": long_trigger,
        "short_trigger": short_trigger,
        "long_hold": long_hold,
        "short_hold": short_hold,
        "high_confidence": high_conf,
    }
```

---

## 10) Roadmap nghiên cứu sau production

Thứ tự nên đi như sau:

1. **Ablation 1:** Q-VDO-RH vs VDO gốc  
2. **Ablation 2:** thêm soft level context  
3. **Ablation 3:** proxy fallback Student-t / empirical CDF  
4. **Ablation 4:** volume surprise, nhưng cho nó đi vào threshold hoặc confidence, không nhân thẳng vào signal  
5. **Ablation 5:** chỉ khi có L2/L3 đủ sạch mới nghiên cứu spoof-robust OFI  

Đây là thứ tự đúng nếu muốn vừa thực dụng vừa kiểm soát overfitting.

---

## 11) Kết luận cuối cùng

Phán quyết cuối:

- Phần phản biện AVFC: **đúng, sắc, đáng giữ**.
- Phần kết luận “WVDO + adaptive threshold là đích đến”: **đúng hướng nhưng chưa chốt chuẩn**.
- Bản nên đưa vào production v1 **không phải full AVFC**, cũng **không phải WVDO như công thức raw-notional + VWMA**.

Bản practical tốt nhất hiện giờ là:

> **Q-VDO-RH = signed notional theo quote volume + EMA oscillator + robust adaptive threshold + hysteresis + level chỉ làm context**

Nói ngắn gọn nhất:

> **Phản biện AVFC là đúng, nhưng vẫn còn nương tay với WVDO. Bản practical tốt nhất hiện giờ là Q-VDO-RH, không phải full AVFC, và cũng không phải WVDO volume-weighted trên raw notional.**

---

## 12) Tài liệu tham khảo

1. Binance Futures API - Kline/Candlestick Data  
   https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data

2. Cont, Kukanov, Stoikov - *The Price Impact of Order Book Events*  
   https://arxiv.org/abs/1011.6402

3. Easley, Lopez de Prado, O’Hara - *Bulk Classification of Trading Activity*  
   https://www.academia.edu/20057247/Bulk_Classification_of_Trading_Activity

4. Panayides et al. / related empirical discussion on BVC calibration and comparison  
   https://www.sciencedirect.com/science/article/abs/pii/S0304405X16000246
