Tiếp nối phân tích exploratory. Bây giờ tôi cho bạn thêm
context: hệ thống EMA crossover đã tạo 226 trades trên dữ
liệu này.

File dữ liệu: /var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv
(Lọc interval == "4h" cho H4, interval == "1d" cho D1)

Code strategy (để reproduce trades):
{{ PATH tới strategy code — e.g. strategies/vtrend_e5_ema21_d1/ }}

Hệ thống entry: EMA_fast(30) crosses above EMA_slow(120)
trên H4 close, trong khi D1 close > D1 EMA(21).

Nhiệm vụ: conditional analysis quanh 226 entries.
Vẫn KHÔNG đề xuất gì. Chỉ mô tả.

1. Chia trades thành hai nhóm
   - Winners: trade return > 0 (sau 50 bps round-trip cost)
   - Losers: trade return ≤ 0
   - Report: bao nhiêu mỗi nhóm, median return mỗi nhóm

2. Volume profile quanh entry
   - Với mỗi nhóm (winners / losers), plot:
     * Median volume từ bar -20 đến bar +10 quanh entry
     * Median taker_buy_ratio từ bar -20 đến bar +10
     * Interquartile range (shaded) cho cả hai
   - Hai nhóm có tách biệt nhau visually không?
   - Tách biệt ở đâu: trước entry, tại entry, hay sau entry?

3. Volatility profile quanh entry
   - Median ATR(20) normalized by price, từ bar -20 đến bar +10
   - Winners entry vào lúc vol cao hay thấp so với losers?

4. Statistical separation
   - Với mỗi feature dưới đây, tính tại bar entry:
     * taker_buy_ratio (đơn bar)
     * mean taker_buy_ratio 5 bars trước entry
     * mean taker_buy_ratio 10 bars trước entry
     * volume / rolling_median_volume(20)
     * ATR(20) / price
   - Mann-Whitney U test giữa winners vs losers
   - Report: p-value, effect size (rank-biserial), direction
   - Bao nhiêu features có p < 0.05?
   - Bao nhiêu features có effect size > 0.2 (small)?

5. VDO tại entry
   - Nếu bạn có code tính VDO: tính VDO tại mỗi entry bar
   - Plot histogram VDO cho winners vs losers
   - Mann-Whitney test: VDO có tách biệt hai nhóm không?
   - Scatter: VDO at entry vs trade return
   - Nếu VDO KHÔNG tách biệt: nói thẳng

6. False entries
   - Nhìn kỹ nhóm losers: có pattern chung nào?
   - Plot 5 worst trades: price + volume + taker_buy_ratio
     từ 20 bars trước đến 20 bars sau entry
   - Có cái gì visible bằng mắt mà signal có thể filter không?
   - Hay chúng trông giống hệt winners tại thời điểm entry?

Với MỖI mục: viết 2-3 câu mô tả cái bạn thấy.
Không interpret, không suggest. Nếu hai nhóm trông
giống nhau: nói "trông giống nhau". Đó là kết quả hợp lệ.
