Đây là dữ liệu BTC H4 từ 2017-08 đến 2026-02.
File: /var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv
Lọc rows có interval == "4h" để lấy H4 data (18,662 bars).
Lọc rows có interval == "1d" nếu cần D1 (3,110 bars).

Columns: symbol, interval, open_time, close_time, open, high,
low, close, volume, quote_volume, num_trades,
taker_buy_base_vol, taker_buy_quote_vol

Nhiệm vụ: phân tích exploratory. KHÔNG đề xuất gì.
Chỉ mô tả những gì bạn thấy.

Viết code Python, chạy, và báo cáo kết quả cho từng mục:

1. Taker buy ratio
   - Định nghĩa: taker_buy_ratio = taker_buy_volume / total_volume
   - Plot time series trên toàn bộ giai đoạn, overlay với price (dual axis)
   - Plot phân phối (histogram) theo từng năm — shape có thay đổi không?
   - Có giai đoạn nào ratio gần 0.5 liên tục (= vô nghĩa) không?

2. Volume theo loại bar
   - Chia bars thành 3 nhóm: up mạnh (return > +2%), down mạnh (< -2%), sideway
   - So sánh phân phối volume và taker_buy_ratio giữa 3 nhóm
   - Dùng Mann-Whitney test cho từng cặp
   - Report p-value và effect size (rank-biserial correlation)

3. Autocorrelation
   - ACF của taker_buy_ratio ở lag 1 đến 20
   - ACF của volume ở lag 1 đến 20
   - So sánh với ACF của close returns — cái nào persistent hơn?

4. Predictive content thô
   - Scatter plot: taker_buy_ratio tại bar t vs forward return
     ở bar t+1, t+6, t+24
   - Tính Spearman correlation cho mỗi horizon
   - Report correlation ± confidence interval
   - Nếu correlation gần 0: nói thẳng là gần 0

5. Regime dependency
   - Chia dữ liệu theo regime đơn giản: price > EMA(126) vs price < EMA(126)
   - Lặp lại mục 4 cho từng regime riêng
   - Predictive content có khác nhau giữa bull vs bear không?

6. Stationarity
   - Rolling Spearman correlation (window 500 bars) giữa
     taker_buy_ratio và forward 6-bar return
   - Plot time series của rolling correlation
   - Correlation có stable không hay drift theo thời gian?

Với MỖI mục: viết 2-3 câu mô tả CÁI BẠN THẤY trong kết quả.
Không interpret, không suggest, không theorize.
Câu dạng "điều này gợi ý rằng ta nên..." là CẤM.
Câu dạng "correlation là 0.03, không có ý nghĩa thống kê" là ĐÚNG.
