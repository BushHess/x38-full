ĐỀ CƯƠNG NGHIÊN CỨU: THIẾT KẾ LẠI STOP/EXIT CHO BTC SPOT H4 TREND-FOLLOWING

1. Mục tiêu và phạm vi

Mở một lab branch mới trong /var/www/trading-bots/btc-spot-dev/research. Core implementation phải được tổ chức như một strategy mới, không phải một chuỗi patch nối tiếp Stage.

Mục tiêu của branch này không phải là xây thêm một policy “cứu” trail stop sau khi stop đã bị hit. Mục tiêu là thiết kế lại exit geometry ngay từ đầu, để stop phân biệt tốt hơn giữa:

- healthy pullback trong một xu hướng còn tiếp diễn; và
- genuine trend failure, tức trạng thái mà vị thế thực sự nên bị đóng.

Nói thẳng: stop tốt hơn từ đầu quan trọng hơn rất nhiều so với churn filter tốt hơn sau khi stop đã breach.

Chi tiết toán học của các indicator hiện tại giữ nguyên như bản gốc: EMA_fast(30), EMA_slow(120), robust ATR(Q90, lb=100, p=20), VDO(12, 28), và D1 EMA(21) regime.


2. Bối cảnh hệ thống hiện tại

2.1. Dữ liệu và tín hiệu

Hệ thống hiện tại giao dịch BTC spot trên H4 với các đầu vào:

- H4 OHLCV
- H4 taker_buy
- D1 OHLCV

Các đại lượng precompute hiện tại:

- EMA_fast(30), EMA_slow(120) trên H4 close
- robust ATR, ký hiệu rATR_t, trên H4 HLC
- VDO(12, 28) trên H4 OHLCV + taker_buy
- D1 EMA(21) regime, map xuống H4

2.2. Logic giao dịch hiện tại

Entry:

- Nếu FLAT và trend_up và VDO_t > 0 và d1_regime_t = 1, vào LONG 100%.

Exit:

- Nếu IN POSITION và close_t < peak_t - 3 \cdot rATR_t, thoát theo trailing stop.
- Nếu IN POSITION và EMA_fast_t < EMA_slow_t, thoát theo trend reversal.

2.3. Validation stack hiện tại

Hệ thống đã được validate bằng:

- VCBB bootstrap, 500 paths
- walk-forward
- jackknife

Điểm này quan trọng vì nó đặt ra chuẩn rất rõ cho branch mới: low-DOF, chống overfit, và phải sống được qua validation chứ không chỉ đẹp trong backtest in-sample.


3. Chẩn đoán thực nghiệm: vấn đề nằm ở đâu

Phân tích trên 186 trades trong giai đoạn 2017-2026, với transaction cost 50 bps round-trip, cho kết quả:

- 168/186 exits là trail stop
- 18/186 exits là trend reversal
- 106/168 trail stops, tương đương khoảng 63%, là churn exits

Định nghĩa churn exit ở đây là:

- stop bị hit; và
- trong 20 bars sau exit, giá phục hồi vượt peak cũ

Điểm quan trọng nhất là:

- các churn exits này vẫn có tổng PnL dương, khoảng +$329K

Nghĩa là hệ thống không thua vì các exits đó. Hệ thống thua vì các exits đó đóng vị thế quá sớm và bỏ lại phần lớn movement phía sau.

Oracle ceiling cho thấy mức trần lý thuyết là rất lớn:

- nếu suppress hoàn hảo toàn bộ churn exits,
- Sharpe tăng từ 1.34 lên 2.18, tức tăng khoảng +0.845 theo số đo gốc
- MDD giảm từ 42% xuống 29%

Kết luận thực nghiệm rất rõ:

- alpha còn lại ở exit là có thật;
- nhưng bản chất vấn đề không phải là “dự đoán churn sau khi stop đã hit”;
- bản chất vấn đề là stop hiện tại đang nằm quá sâu bên trong phân phối healthy pullback của continuation trend.


4. Những gì đã thử và kết luận rút ra

4.1. Những gì đã cho tín hiệu tích cực, nhưng chỉ một phần

Static logistic filter, dùng 7 market-state features, train L2-logistic trên các trail-stop exits, rồi suppress khi P(churn) > 0.5.

Do constraint của pipeline hiện tại, 3 trade-context features mạnh nhất:

- bars_held
- dd_from_peak
- bars_since_peak

bị zero do mask được tính trước khi simulation chạy. Vì vậy model thực tế chỉ dùng được 7 features thuộc market state.

Kết quả:

- Sharpe: 1.34 -> 1.43, tức +0.09
- MDD: 42% -> 37%
- 133 trades
- WFO pass 3/4 folds
- bootstrap P(dSharpe > 0) = 65%
- jackknife: 0/6 negative

Diễn giải đúng của kết quả này là:

- static market-state score có giá trị;
- nhưng vai trò hợp lý nhất của nó là làm biến trạng thái ngoại sinh để điều chỉnh stop ex ante;
- nó không đủ để trở thành một post-trigger suppressor mạnh.

Mức capture chỉ khoảng 10.9% oracle ceiling, tức 0.09 / 0.845.

4.2. Những gì đã thất bại rõ ràng

Dynamic logistic filter, đánh giá model ngay tại trail-stop trigger với đầy đủ trade context, gồm:

- bars_held
- dd_from_peak
- bars_since_peak
- và các features khác

Kết quả:

- suppress 15,020 / 15,027 trail stops
- hệ thống chỉ còn 7 trades
- MDD tăng lên 77%

Đây không phải là một lỗi threshold nhỏ. Đây là một failure có tính cấu trúc.

Lý do:

- khi model thấy bars_held lớn và dd_from_peak nhỏ,
- nó đúng khi dự đoán rằng “trail stop này có khả năng sẽ được follow by recovery”;
- nhưng trong dữ liệu BTC với upward drift, điều đó lại đúng cho gần như toàn bộ trail stops.

Nói gọn hơn: model học đúng pattern, nhưng học đúng câu hỏi sai.

Các thử nghiệm khác cũng không đáng đào thêm ở giai đoạn này:

- threshold đơn giản trên ema_ratio: fail bootstrap
- threshold kép ema_ratio + d1_regime_strength: fail WFO
- take-profit ladders: phá alpha kiểu trend-following
- short-side complement: negative EV do BTC có upward drift dài hạn


5. Vì sao post-trigger churn prediction là abstraction sai

Đây là điểm cần chốt dứt khoát.

Giả sử tại thời điểm t, trail stop vừa trigger. Gọi \mathcal{F}_t là toàn bộ thông tin khả dụng tại bar đó.

Một churn classifier nhị phân đang cố ước lượng một xác suất dạng:

\[
Y_t = \mathbf{1}\{\tau_t^{\text{new peak}} < \tau_t^{\text{failure}}\},
\]

tức là:

- sau trigger hiện tại, liệu giá có quay lại làm new peak trước khi xảy ra failure hay không.

Model khi đó học:

\[
p_t = \mathbb{P}(Y_t = 1 \mid \mathcal{F}_t).
\]

Nhưng quyết định đúng về mặt kinh tế lại không phải là “xác suất recovery có lớn hơn 0.5 hay không”. Quyết định đúng là:

\[
\text{suppress stop tại } t
\iff
\mathbb{E}[\Delta U_t \mid \mathcal{F}_t] > 0,
\]

trong đó \Delta U_t là giá trị gia tăng ròng của việc tiếp tục hold thay vì exit ngay tại t.

Nói cách khác, object đúng là:

- upside kỳ vọng còn lại
- trừ đi downside bổ sung
- trừ đi cost và path risk phát sinh do tiếp tục hold

Một binary churn label không mang đủ thông tin đó. Nó bỏ qua:

- magnitude của movement còn lại
- magnitude của adverse move bổ sung
- thời gian hold thêm
- path dependency của drawdown

Vì vậy, một model có thể rất giỏi trong việc dự đoán “sẽ có recovery hay không”, nhưng vẫn cực kỳ tệ trong việc ra quyết định suppress hay không suppress.

Đây chính xác là điều đã xảy ra với dynamic logistic filter:

- trade-context features như bars_held, dd_from_peak, bars_since_peak không hề “sai”;
- chúng chỉ dự đoán một target không khớp với objective trading.

Từ đây có hai hệ quả:

1. Non-linear threshold, calibrated cutoff, hay cost-sensitive learning chỉ có thể dịch operating point một chút; chúng không sửa được target mismatch. Khi p_t gần 1 trên gần như toàn bộ support, đổi cutoff từ 0.5 sang 0.8 chỉ chữa triệu chứng.

2. Về mặt lý thuyết, regression trên expected remaining movement hoặc trực tiếp trên \Delta U_t là đúng hướng hơn binary churn classification. Nhưng với sample hiện tại và mức độ tự do của policy, cách đó rất dễ overfit. Vì vậy, nó chưa phải là bước đầu tiên cho branch mới.

Kết luận thiết kế:

- không tiếp tục tối ưu post-trigger suppressor ở vòng đầu;
- thay vào đó, redesign stop ex ante bằng một policy deterministic, low-DOF, dùng state ngoại sinh trước khi breach xảy ra.


6. Nguyên tắc thiết kế cho branch mới

6.1. Một line không được làm ba việc cùng lúc

Trailing stop hiện tại:

\[
S_t^{\text{trail, old}} = peak_t - 3 \cdot rATR_t
\]

đang bị ép làm đồng thời ba vai trò:

- catastrophe stop: entry sai từ gốc
- profit-protection stop: bảo vệ open PnL
- trend-failure stop: xác nhận xu hướng đã hỏng

Một đường stop duy nhất mà phải gánh cả ba nhiệm vụ thì churn gần như là hệ quả tất yếu.

Thiết kế đúng là tách ba vai trò ra:

- hard invalidation stop
- continuation stop
- trend-failure exit

6.2. Stop width phải được điều chỉnh trước khi breach xảy ra

Ý tưởng cốt lõi là:

- state càng mạnh, continuation pullback bình thường càng sâu;
- vì vậy stop phải tự looser từ trước trong strong state;
- như vậy nhiều churn sẽ không còn là “stop bị hit rồi phải cứu”, mà đơn giản là “stop không bị hit sai nữa”.

6.3. Chỉ thêm đúng một lớp lifecycle, và lifecycle đó phải deterministic

Không dùng learned policy dựa trên bars_held, dd_from_peak, bars_since_peak.

Nếu thêm lifecycle, chỉ thêm các rule đơn giản, ít bậc tự do, và được định nghĩa hoàn toàn bởi thông tin có sẵn tại bar hiện tại.

6.4. Mọi calibration phải đi từ phân phối healthy pullback, không đi từ intuition mơ hồ

Không đoán multiplier. Không fitting theo cảm tính. Không tuning sau trigger.

Phải ước lượng trực tiếp độ sâu pullback “vẫn khỏe” theo từng state, rồi đặt stop ra ngoài vùng pullback bình thường đó.

6.5. Low-DOF là ràng buộc cứng, không phải sở thích

Branch này phải được thiết kế để:

- đi qua WFO
- đi qua bootstrap
- không sụp dưới jackknife

Vì vậy, mọi thứ có quá nhiều tham số hoặc quá nhiều degrees of freedom sẽ bị loại khỏi vòng đầu.


7. Ký hiệu toán học cho stop architecture mới

Tất cả điều kiện được đánh giá trên close của bar H4.

Ký hiệu:

- C_t: close của bar H4 tại thời điểm t
- E: giá entry của trade hiện tại
- \tau_{\text{entry}}: bar entry
- A_t = rATR_t
- A_E = A_{\tau_{\text{entry}}}
- P_t^\star: peak anchor kể từ entry
- MFE_t: maximum favorable excursion kể từ entry
- peak\_age_t: số bars kể từ lần gần nhất tạo peak
- s_t: static market-state score từ 7 features đã pass bootstrap

Định nghĩa cụ thể:

\[
P_t^\star = \max_{\tau_{\text{entry}} \le u \le t} C_u
\]

tức peak anchor mặc định là highest close since entry.

Lưu ý: phải test highest close trước khi thử highest high. Highest close thường ít nhạy hơn với spike/wick và phù hợp hơn với logic exit theo close.

\[
MFE_t = P_t^\star - E
\]

\[
peak\_age_t
=
t - \arg\max_{\tau_{\text{entry}} \le u \le t} C_u
\]


8. Kiến trúc stop/exit đề xuất

8.1. Hard invalidation stop

Hard stop dùng cho tình huống “entry này sai từ gốc”, không dùng để quản lý continuation.

Phiên bản mặc định:

\[
S^{\text{hard}} = E - 2.5 \cdot A_E
\]

Biến thể có cấu trúc hơn, để test sau nếu cần:

\[
S^{\text{hard}} = L_{\text{swing}} - 0.5 \cdot A_E
\]

trong đó L_{\text{swing}} là last confirmed swing low trước entry.

Nguyên tắc:

- hard stop là hàng rào an toàn;
- không cần tối ưu quá mức;
- không dùng hard stop để làm profit-protection.

8.2. State-conditioned continuation stop

Gọi s_t là static score từ 7 market-state features.

Trên mỗi training fold, ước lượng các percentile:

\[
q_{15}, q_{85}
\]

rồi bucket hóa state:

\[
state_t =
\begin{cases}
\text{weak}, & s_t < q_{15}, \\
\text{normal}, & q_{15} \le s_t < q_{85}, \\
\text{strong}, & s_t \ge q_{85}.
\end{cases}
\]

Map state sang trail multiplier:

\[
m_t =
\begin{cases}
2.25 \text{ đến } 2.5, & state_t = \text{weak}, \\
3.0, & state_t = \text{normal}, \\
4.0 \text{ đến } 4.5, & state_t = \text{strong}.
\end{cases}
\]

Continuation stop tại bar t là:

\[
S_t^{\text{trail}} = P_t^\star - m_t \cdot A_t
\]

Ý nghĩa:

- weak state: stop sát hơn
- normal state: stop trung tính
- strong state: stop rộng hơn rõ rệt, để continuation trend có không gian thở

8.3. Lifecycle rule 1: trail chỉ arm sau khi trade đã có lời đủ lớn

Không cho trail ratchet ngay từ đầu.

Định nghĩa:

\[
trail\_armed_t
=
\mathbf{1}\{MFE_t \ge 1.5 \cdot A_E\}
\]

Trước khi trail được arm:

- chỉ hard stop hoạt động
- EMA reversal vẫn hoạt động

Sau khi trail được arm:

- continuation stop mới bắt đầu có hiệu lực

Lý do rất đơn giản:

- nhiều trade trend-following cần một pha “escape velocity” trước khi trailing stop trở nên có ý nghĩa;
- nếu trail ratchet quá sớm, hệ thống tự stop-out trong vùng nhiễu quanh entry.

8.4. Lifecycle rule 2, tùy chọn: peak già thì siết stop lại

Một trend vừa tạo peak mới thường cần leash rộng hơn. Một trend không tạo peak mới trong thời gian dài thì nên leash chặt hơn.

Phiên bản tối giản:

\[
m_t = m(state_t) - 0.5 \cdot \mathbf{1}\{peak\_age_t \ge 10\}
\]

Rule này là optional. Chỉ test sau khi phiên bản core đã hoàn tất.

Quan trọng: đây không phải learned policy. Đây chỉ là một lớp hysteresis/lifecycle deterministic rất ít bậc tự do.

8.5. Trend-failure exit

Giữ EMA reversal như exit chậm hơn nhưng đáng tin hơn:

\[
EMA\_fast_t < EMA\_slow_t \;\Rightarrow\; \text{exit}
\]

D1 regime off có thể được xem là một biến thể để test sau, nhưng không phải thành phần bắt buộc của prototype đầu tiên.

8.6. Logic exit hoàn chỉnh

Exit nếu xảy ra ít nhất một trong ba điều kiện sau:

- \( C_t < S^{\text{hard}} \)
- \( EMA\_fast_t < EMA\_slow_t \)
- \( trail\_armed_t = 1 \) và \( C_t < S_t^{\text{trail}} \)

Không suppress.
Không WATCH.
Không re-entry đặc biệt.
Không runner.
Không add-back.

Toàn bộ logic phải được quyết định trước khi breach xảy ra, không sửa quyết định sau khi breach đã xuất hiện.


9. Hiệu chuẩn multiplier từ healthy pullback distribution

Đây là phần quan trọng nhất của toàn bộ branch.

9.1. Dataset calibration

Không chỉ lấy exit bars. Phải lấy mọi bar mà hệ thống đang in-position.

Với mỗi bar t đang in-position trên training fold, ghi nhận:

- state_t
- P_t^\star
- A_t

Sau đó định nghĩa các stopping times:

\[
\tau_t^{\text{next peak}}
=
\inf \{ u > t : C_u > P_t^\star \}
\]

\[
\tau_t^{\text{fail}}
=
\inf \{ u > t : (C_u < S^{\text{hard}}) \;\text{hoặc}\; (EMA\_fast_u < EMA\_slow_u) \}
\]

Nếu:

\[
\tau_t^{\text{next peak}} < \tau_t^{\text{fail}},
\]

thì bar t được xem là một continuation instance.

Trên các continuation instances đó, đo độ sâu pullback khỏe theo ATR units:

\[
PB_t
=
\frac{
P_t^\star - \min_{t \le u \le \tau_t^{\text{next peak}}} C_u
}{
A_t
}
\]

Diễn giải:

- PB_t là mức drawdown lớn nhất từ peak hiện tại xuống đáy pullback, trước khi giá quay lại làm new peak;
- và được chuẩn hóa bởi volatility hiện tại A_t.

9.2. Ước lượng multiplier theo state

Với mỗi state r \in \{\text{weak}, \text{normal}, \text{strong}\}, ước lượng:

\[
m_r
=
Q_{p_r}
\left(
PB_t
\mid
state_t = r,\;
\tau_t^{\text{next peak}} < \tau_t^{\text{fail}}
\right)
\]

Gợi ý quantile ban đầu:

- weak: \( p_r \in \{0.70, 0.75\} \)
- normal: \( p_r \in \{0.80, 0.85\} \)
- strong: \( p_r \in \{0.85, 0.90\} \)

Nguyên lý là:

- state càng mạnh, stop càng phải nằm ngoài phần lớn healthy pullback của continuation;
- state càng yếu, stop được phép sát hơn.

9.3. Ràng buộc ổn định

Sau khi ước lượng, áp ràng buộc đơn điệu:

\[
m_{\text{weak}} \le m_{\text{normal}} \le m_{\text{strong}}
\]

Nếu một bucket có quá ít continuation samples trong một fold, dùng shrinkage về global quantile thay vì chấp nhận một multiplier cực đoan.

Lưu ý quan trọng:

- mọi percentile và quantile đều phải được ước lượng trên training segment của từng WFO fold;
- out-of-sample chỉ được dùng frozen thresholds;
- nếu đổi peak anchor từ highest close sang highest high, phải hiệu chuẩn lại từ đầu; không được tái sử dụng multiplier cũ.


10. Thứ tự thí nghiệm

10.1. Core redesign: đây là test quan trọng nhất

Chạy đúng bộ sau:

- hard stop cố định
- trail arm sau MFE threshold
- trail width theo 3 state từ static score
- EMA reversal giữ nguyên

Đây là phiên bản cần được ưu tiên vì nó kiểm tra trực tiếp giả thuyết cốt lõi:

- churn đến từ exit geometry sai;
- và exit geometry có thể sửa bằng state-conditioned stop width trước khi breach xảy ra.

10.2. Chỉ sau đó mới thêm peak_age

Phiên bản kế tiếp:

- thêm rule \( peak\_age_t \ge N \Rightarrow m_t := m_t - 0.5 \)

Rule này phải được giữ tối giản. Không spline. Không continuous function nhiều tham số.

10.3. Sau nữa mới test hysteresis nhẹ cho strong state

Biến thể hợp lý duy nhất ở giai đoạn này:

- strong state cần 2 consecutive closes dưới trail mới exit
- weak/normal vẫn chỉ cần 1 close

Về mặt toán học, nếu dùng xác nhận 2 closes cho strong state:

\[
\text{exit on trail tại } t
\iff
(C_t < S_t^{\text{trail}})
\land
(C_{t-1} < S_{t-1}^{\text{trail}})
\]

Rule này là một dạng confirmation/hysteresis nhẹ. Nó không phải WATCH policy.

10.4. Những gì không test ở giai đoạn này

Loại khỏi vòng đầu:

- learned dynamic stop controller
- continuous stop function với nhiều tham số
- re-entry / runner / add-back
- regression trực tiếp trên \Delta U để điều khiển exit
- mọi post-trigger suppressor có tính policy

Lý do rất thực dụng:

- sample hiện tại không đủ lớn để nuôi các policy có DOF cao;
- branch này phải ưu tiên độ tin cậy dưới WFO/bootstrap/jackknife hơn là độ “thông minh” trên giấy.


11. Prototype đủ tốt để mở nhánh mới ngay

Nếu phải chọn đúng một cấu hình để implement trước, chọn cấu hình sau:

11.1. Hard stop

\[
S^{\text{hard}} = E - 2.5 \cdot A_E
\]

11.2. Trail arming

\[
trail\_armed_t
=
\mathbf{1}\{MFE_t \ge 1.5 \cdot A_E\}
\]

11.3. State buckets

- bottom 15% của s_t -> weak
- middle 70% của s_t -> normal
- top 15% của s_t -> strong

11.4. Multipliers

- weak = 2.25
- normal = 3.0
- strong = 4.25

11.5. Peak anchor

\[
P_t^\star = \max_{\tau_{\text{entry}} \le u \le t} C_u
\]

tức highest close since entry.

11.6. Optional v2 only

Nếu:

\[
peak\_age_t \ge 10
\]

thì:

\[
m_t := m_t - 0.5
\]

11.7. Exit conditions

Exit nếu:

- \( C_t < S^{\text{hard}} \), hoặc
- \( EMA\_fast_t < EMA\_slow_t \), hoặc
- \( trail\_armed_t = 1 \) và \( C_t < S_t^{\text{trail}} \)

11.8. Pseudocode tối giản

At entry:
- E = C_t
- A_E = A_t
- P^\star = C_t
- trail_armed = 0

On each subsequent bar t:
- P_t^\star = \max(P_{t-1}^\star, C_t)
- MFE_t = P_t^\star - E
- if MFE_t \ge 1.5 \cdot A_E: trail_armed = 1
- state_t = bucket(s_t)
- m_t = {2.25, 3.0, 4.25}[state_t]
- optional v2: if peak\_age_t \ge 10 then m_t = m_t - 0.5
- S^{hard} = E - 2.5 \cdot A_E
- S_t^{trail} = P_t^\star - m_t \cdot A_t
- exit if:
  - C_t < S^{hard}, or
  - EMA_fast_t < EMA_slow_t, or
  - trail_armed = 1 and C_t < S_t^{trail}

Đây là một stop architecture mới đúng nghĩa:

- không cứu chữa sau breach
- không tạo thêm vòng cost
- dùng static market-state score đúng chỗ
- low-DOF
- phù hợp với WFO/bootstrap hơn bất kỳ learned policy phức tạp nào


12. Tiêu chí đánh giá branch mới

Tôi sẽ đánh giá branch này bằng ba câu hỏi rất thực dụng.

12.1. Trail breaches và churn count có giảm rõ rệt không?

Nếu không giảm rõ, stop mới không giải quyết đúng bài toán.

12.2. Trade count có bị co lại quá mạnh không?

Nếu Sharpe tăng chủ yếu vì hệ thống giao dịch ít đi một cách cực đoan, đó thường là optimization noise chứ không phải exit tốt hơn.

12.3. Hiệu quả có sống được qua validation stack không?

Cụ thể:

- VCBB bootstrap không được xấu đi
- WFO phải giữ được tín hiệu dương ổn định
- jackknife không được lộ ra một failure mode mới
- MDD phải giữ nguyên hoặc giảm; nếu MDD tăng mạnh thì stop mới chỉ đang delay pain chứ không tạo edge

Nếu branch mới không beat được baseline một cách ổn định, kết luận hợp lý sẽ là:

- exit geometry hiện tại đã khá gần practical optimum;
- phần alpha lớn hơn nằm ở entry, regime filter, hoặc sizing;
- stop không còn là bottleneck lớn nhất.


13. Kết luận

Luận điểm trung tâm của branch này là:

- churn không nên được giải quyết chủ yếu bằng cách “đoán xem stop vừa hit có đáng bị cứu hay không”;
- churn nên được giải quyết bằng cách đặt stop đúng hơn ngay từ đầu.

Thiết kế stop tốt hơn từ đầu, trong ngữ cảnh này, có dạng:

- hard stop riêng cho invalidation
- continuation stop riêng cho pullback trong xu hướng
- trend-failure exit riêng cho reversal
- trail chỉ arm khi trade đã có đủ MFE
- trail width được điều kiện hóa bởi state ngoại sinh
- mọi thứ đều deterministic, low-DOF, và được hiệu chuẩn từ healthy pullback distribution

Tóm gọn một câu:

Stop tốt hơn từ đầu = state-conditioned stop width + delayed trail arming + separate hard stop + separate trend-failure exit.

Đừng cố cứu stop sau khi nó đã hit.
Hãy thiết kế để nó đừng hit sai ngay từ đầu.
