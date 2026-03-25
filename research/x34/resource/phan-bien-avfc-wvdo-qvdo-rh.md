# Phản biện AVFC & WVDO — Đề xuất Q-VDO-RH

## Đánh giá tổng quan

Bản viết mạnh hơn AVFC gốc, và kết luận chiến lược lớn là đúng: **ship bản đơn giản, sửa đúng lỗi cấu trúc trước; research bản phức tạp sau.** Nhưng vẫn chưa phải bản cuối, vì còn hai chỗ xử chưa tới:

1. Phạt AVFC hơi quá tay ở vài điểm.
2. Cho WVDO đi qua mà chưa mổ kỹ một lỗi kỹ thuật quan trọng của chính nó.

Binance futures kline thực sự đã cho sẵn **quote asset volume** và **taker buy quote asset volume**, nên signed notional flow làm được trực tiếp. Cont–Kukanov–Stoikov cũng cho thấy ở horizon ngắn, price change gắn với order flow imbalance mạnh hơn trade volume. Còn BVC trong literature thì không có verdict tuyệt đối mà thay đổi theo market, mức noise và cách calibration.

---

## Điểm đồng ý mạnh nhất: Tiêu chuẩn bằng chứng

Chỗ này đánh rất trúng: AVFC không thể dùng checklist kiểu "walk-forward, effect size, regime stability, turnover sau phí" để hạ VDO, rồi đến lượt mình lại xin miễn trừ vì "thiết kế hợp lý về mặt lý thuyết". **Phần đó đúng.**

Cũng đồng ý rằng **price acceptance bằng bar-VWAP trên kline là quá yếu**: với bar dài như 1H hay 4H, `quoteVolume / volume` chỉ là average price của cả bar, không đủ sắc để kết luận absorption cuối bar. Ở điểm này, phê AVFC là chính xác.

---

## OFI vs Crypto L2

Phần OFI vs crypto L2 phải được nói cho đầy đủ. Về lý thuyết, OFI ở order book là biến giàu thông tin hơn trade volume; Cont và đồng tác giả nói rất rõ price changes ngắn hạn chủ yếu gắn với OFI và quan hệ với trade volume thì nhiễu hơn.

**Nhưng** trên crypto CEX, raw L2 không phải "miễn phí alpha"; một paper 2025 về spoofing trên crypto CEX dùng dữ liệu Level-3 còn báo rằng trong sample ngắn của họ, **31% large orders có thể spoof được market**. Nghĩa là AVFC đúng ở tầng lý thuyết, nhưng nếu đem nguyên book imbalance thô vào production trên crypto thì rất dễ tự lừa mình.

---

## BVC Fallback — Sửa chi tiết quan trọng

Phần BVC fallback đúng hướng, nhưng cần sửa: **đừng đóng khung BVC vào normal CDF.**

Chính Easley–Lopez de Prado–O'Hara 2016 mô tả BVC là dùng standardized price change trên short time/volume intervals để xấp xỉ buy/sell flow, và họ nói luôn việc tick rule hay BVC tốt hơn còn tùy mức noise trong dữ liệu. Sau đó, literature cho kết quả lẫn lộn:

- **Chakrabarty et al.** tìm thấy BVC kém hơn tick rule trên NASDAQ INET.
- **Panayides et al.** lại thấy trong sample LSE 2017, BVC có thể là cái chính xác nhất; cùng paper này còn ghi nhận **calibration theo Student-t cải thiện so với normal**.

> Ý đúng không phải "BVC tệ vì crypto fat-tail", mà là: **BVC là fallback hợp lệ nhưng phải dùng phân phối nặng đuôi hoặc empirical CDF, và phải xem nó như proxy có điều kiện, không phải truth machine.**

---

## Lỗ hổng lớn nhất: WVDO bơm volume hai lần

Chỗ không cho qua: phê AVFC xong, lại cho WVDO miễn kiểm tra kỹ thuật ở một điểm rất đáng ngại.

Nếu dùng:

$$
raw_t = \frac{2 \cdot takerBuyQuote_t - quoteVolume_t}{EMA(quoteVolume_t, N)}
$$

rồi lại tính:

$$
WVDO_t = VWMA(raw, fast) - VWMA(raw, slow)
$$

thì đang **bơm volume hai lần**. Vì:

$$
VWMA(raw)_t = \frac{\sum q_i \cdot raw_i}{\sum q_i} = \frac{\sum q_i \cdot \Delta_i^{\$} / EMA(q_i)}{\sum q_i}
$$

mà $|\Delta_i^{\$}| \leq q_i$, nên contribution cực đại của bar lớn về bản chất scale gần kiểu $q_i^2 / EMA(q_i)$.

**Nói gọn:** `raw` đã mang notional participation rồi, VWMA lại weight theo volume thêm lần nữa. Đó chính là kiểu reweighting mà đang bị phê ở AVFC dưới nhãn "double-counting risk". **Chỗ này là lỗ hổng lớn nhất trong verdict hiện tại.**

---

## Đề xuất: Tách thành hai nhánh rõ ràng

### R-WVDO — Giữ input là ratio bounded

$$
r_t = \frac{2 \cdot takerBuyQuote_t - quoteVolume_t}{quoteVolume_t} \in [-1, 1]
$$

Rồi mới làm `VWMA(r, fast) - VWMA(r, slow)`.

Bản này volume-weighted ở tầng smoothing, nhưng **không giữ magnitude tuyệt đối**.

### Q-VDO — Dùng input là signed notional normalized by normal activity

$$
x_t = \frac{2 \cdot takerBuyQuote_t - quoteVolume_t}{EMA(quoteVolume_t, slow) + \varepsilon}
$$

Rồi làm `EMA(x, fast) - EMA(x, slow)`.

Bản này **giữ magnitude tương đối theo regime volume**, nên không cần VWMA nữa.

> **Muốn tối ưu VDO theo hướng thực dụng → chọn Q-VDO, không phải WVDO kiểu "notional + VWMA".**

---

## Những điểm cần siết lại

### "Prototype đã test thắng system chưa test"

Đúng khi nói về VDO gốc, nhưng **không được chuyển nguyên xi sang WVDO/Q-VDO**. Một khi đổi input từ ratio sang signed notional, đổi threshold từ 0 sang adaptive, thậm chí đổi kernel smoothing, thì đó đã là indicator mới. `p = 0.031` của VDO gốc, nếu có, chỉ là bằng chứng gợi ý rằng "order-flow style signal có thể có ích"; nó không phải bằng chứng trực tiếp cho WVDO hay Q-VDO.

### Parameter count

Đúng khi xem complexity là red flag. Nhưng câu "risk overfitting tăng theo cấp số nhân" là khẩu khí đúng hướng, chưa phải cách chốt kỹ thuật tốt nhất. Cái cần đếm không phải chỉ là số symbol trong công thức, mà là **effective degrees of freedom**: bao nhiêu cái thực sự được tune, bao nhiêu cái được khóa theo prior, và bao nhiêu quyết định được chọn sau khi nhìn backtest.

> Full AVFC đúng là quá nhiều tầng cho production v1; nhưng không phải cứ nhiều parameter là auto-thua. Cách phán chuẩn hơn là: **full AVFC không có quyền claim superiority trước khi ablation từng module.**

### "Minimal AVFC gần như trùng WVDO"

Hơi quá. Nó **không trùng**. Minimal AVFC vẫn khác ở 2 điểm vật lý:

1. Nó dùng signed notional normalized flow, không phải ratio weighted oscillator.
2. Nó có thêm level state tách khỏi trigger momentum.

Điểm nên nói không phải "hai cái gần như một", mà là: **full AVFC chưa chứng minh được 4 lớp phức tạp thêm vào đáng giá hơn chính stripped core của nó.** Đó là đòn mạnh và công bằng hơn.

### L > 0 AND M > Θ

Không hoàn toàn đồng ý với việc bác bỏ luôn. Nếu AVFC được dùng như entry engine, đúng, hard gate đó dễ trễ. Nhưng nếu nó chỉ là **confirmation filter**, trade-off recall lấy precision lại là chuyện chấp nhận được.

> Vấn đề không phải "logic này sai", mà là "logic này chưa được chứng minh đáng cái giá mất early signal". Cách thực dụng nhất: **không đưa L vào điều kiện AND cứng ở v1; dùng nó làm context/confidence, không dùng làm hard veto.**

---

## Bản chốt: Q-VDO-RH

- **Q** = quote-notional normalized
- **RH** = robust threshold + hysteresis

### Mode A — Có taker data

Binance futures kline đã có `quote asset volume` và `taker buy quote asset volume`, nên dùng trực tiếp, khỏi reconstruct từ `base * VWAP`.

**Signed notional delta:**

$$
\Delta_t^{\$} = 2 \cdot takerBuyQuote_t - quoteVolume_t
$$

**Normalized flow:**

$$
x_t = \frac{\Delta_t^{\$}}{EMA(quoteVolume_t, slow) + \varepsilon}
$$

**Momentum & Level:**

$$
m_t = EMA(x_t, fast) - EMA(x_t, slow)
$$

$$
\ell_t = EMA(x_t, slow)
$$

**Robust scale** (tránh EWSTD vì crypto có fat-tail và liquidation spikes):

$$
scale_t = EMA\big(|m_t - EMA(m_t, slow)|,\; slow\big) + \varepsilon
$$

$$
\theta_t = k \cdot scale_t
$$

**Rule:**

| Condition | Action |
|---|---|
| $m_t > \theta_t$ | Trigger long |
| $m_t < -\theta_t$ | Trigger short |
| $\ell_t$ cùng dấu với $m_t$ | Confidence cao |
| $\ell_t$ ngược dấu với $m_t$ | Confidence thấp |

**Nếu cần stateful filter (hysteresis):**

- Giữ long cho tới khi $m_t < 0.5\theta_t$
- Giữ short cho tới khi $m_t > -0.5\theta_t$

**Điểm hay của bản này:**

- Sửa đúng lỗi mất magnitude của VDO.
- Không rơi vào overengineering như AVFC full.
- Không mắc lỗi volume reweight hai lần như WVDO kiểu "raw notional + VWMA".
- Số tunable thực sự có thể ép còn **3 cái: `fast`, `slow`, `k`**.
  `N_vol = slow`, `N_scale = slow`, hysteresis ratio cố định.

### Mode B — Không có taker data

> **Không được giả vờ đây là cùng chất lượng với taker mode.**

Dùng proxy kiểu BVC nhưng **không Gaussian cứng:**

$$
r_t = \log(C_t / C_{t-1})
$$

$$
z_t = \frac{r_t}{EMA\big(|r_t - EMA(r_t, slow)|,\; slow\big) + \varepsilon}
$$

$$
p_t = F(z_t)
$$

trong đó $F$ là **Student-t CDF** hoặc **rolling empirical CDF**, không phải standard normal mặc định. Easley et al. và các paper follow-up đều đặt BVC trong logic probabilistic classification từ standardized price changes; Panayides còn ghi nhận Student-t cho kết quả tốt hơn normal ở triển khai của họ.

Sau đó:

$$
x_t = \gamma \cdot (2p_t - 1) \cdot \frac{quoteVolume_t}{EMA(quoteVolume_t, slow) + \varepsilon}
$$

với $\gamma < 1$ hoặc đơn giản hơn: giữ cùng pipeline nhưng **tăng threshold ở proxy mode**.

> Nói nôm na: fallback được dùng, nhưng phải **de-rate confidence**.

---

## Phán quyết cuối

| Phần | Đánh giá |
|---|---|
| Phản biện AVFC | Tốt, sắc, đáng giữ |
| Kết luận "WVDO + adaptive threshold là đích đến" | Đúng hướng, nhưng chưa chốt chuẩn |
| **Bản nên ship production v1** | **Q-VDO-RH** — signed notional by quote volume + EMA oscillator + robust adaptive threshold + hysteresis + level chỉ làm context |

---

## Roadmap nghiên cứu sau production

| Thứ tự | Ablation |
|---|---|
| 1 | Q-VDO-RH vs VDO gốc |
| 2 | Thêm soft level context |
| 3 | Proxy fallback Student-t / empirical CDF |
| 4 | Volume surprise — cho vào threshold/confidence, **không nhân thẳng vào signal** |
| 5 | Chỉ khi có L2/L3 sạch mới nghiên cứu spoof-robust OFI |

---

## Tóm tắt một dòng

> **Phản biện AVFC đúng, nhưng vẫn còn nương tay với WVDO. Bản practical tốt nhất hiện giờ là Q-VDO-RH, không phải full AVFC, và cũng không phải WVDO volume-weighted trên raw notional.**
