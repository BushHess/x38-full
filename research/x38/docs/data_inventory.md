# Data Inventory — Dữ liệu sẵn có cho Alpha-Lab framework

**Tại sao file này tồn tại**: Agents tham gia debate x38 cần hiểu rõ dữ liệu mà
Alpha-Lab framework sẽ sử dụng để nghiên cứu — cấu trúc, thành phần, độ chi tiết,
kích thước, khoảng thời gian, và giới hạn — mà KHÔNG cần đọc toàn bộ data-pipeline.

**Nguồn dữ liệu**: `/var/www/trading-bots/data-pipeline/output/`
**Cập nhật**: 2026-04-02. Dữ liệu cập nhật đến 2026-03-11.
**Tổng kích thước**: ~80 GB (99% là aggtrades tick-level).

---

## 1. Tổng quan — 6 Dataset

| # | Dataset | Đường dẫn | Coins | Bắt đầu | Kết thúc | Rows | Size |
|---|---------|-----------|-------|---------|---------|------|------|
| 1 | **Spot Klines** | `spot_klines/BTCUSDT/{15m,1h,4h,1d}.parquet` | BTC | 2017-08 | 2026-03 | 396K | 26 MB |
| 2 | **Futures Metrics** | `futures_metrics/BTCUSDT/{5m,15m,1h,4h,1d}.parquet` | BTC | 2020-09 | 2026-03 | 836K | 42 MB |
| 3 | **Futures Premium Index** | `futures_premiumIndexKlines/BTCUSDT/{15m,1h,4h,1d}.parquet` | BTC | 2020-01 | 2026-03 | 287K | 6 MB |
| 4 | **Funding Rate** | `futures_fundingRate/BTCUSDT.parquet` | BTC | 2019-09 | 2026-02 | 7K | 97 KB |
| 5 | **AggTrades** | `aggtrades_bulk/BTCUSDT/BTCUSDT-aggTrades-YYYY-MM-DD.parquet` | BTC | 2017-08 | 2026-03 | ~1.5B | 80 GB |
| 6 | **Multi-coin 4h** | `bars_multi_4h.parquet` | 14 coins | 2017-08 | 2026-03 | 224K | 14 MB |

**Tất cả file đều là Parquet (Zstandard compression). Timestamp dạng UTC milliseconds.**

### Timeline

```
2017-08 ├──── Spot Klines + AggTrades ─────────────────────────────┤ 2026-03
        │                                                          │
2019-09 │     ├── Funding Rate ────────────────────────────────────┤
        │     │                                                    │
2020-01 │     │  ├── Premium Index ────────────────────────────────┤
        │     │  │                                                 │
2020-09 │     │  │  ├── Futures Metrics ───────────────────────────┤
        │     │  │  │                                              │
        ▼     ▼  ▼  ▼                                              ▼
```

Giai đoạn 2017-08 → 2019-08 chỉ có spot data (klines + aggtrades). Futures data bắt
đầu từ 2019-09 (funding rate) và 2020-01 (premium). Metrics (OI, L/S) từ 2020-09.

### Quy mô BTC qua thời gian

Thị trường BTC thay đổi CĂN BẢN qua 8 năm data. Agent cần nhận thức điều này
khi thiết kế feature hoặc đặt threshold:

| Giai đoạn | Giá BTC (USDT) | Volume 4h (BTC) | Trades 4h | Đặc điểm |
|-----------|---------------|-----------------|-----------|----------|
| 2017-2018 | 2,900 – 19,500 | 1,000 – 5,000 | 10K – 50K | Nascent, thin liquidity |
| 2019-2020 | 3,200 – 29,000 | 3,000 – 15,000 | 50K – 200K | Futures launched, institutional entry |
| 2021-2022 | 17,000 – 69,000 | 5,000 – 40,000 | 150K – 500K | Peak mania, crash, Terra/FTX |
| 2023-2024 | 16,000 – 73,000 | 3,000 – 20,000 | 100K – 400K | Recovery, ETF approval |
| 2025-2026 | 73,000 – 125,000 | 2,000 – 10,000 | 500K – 1.5M | All-time-high phase |

Giá tối thiểu: **2,919 USDT** (2017-09). Giá tối đa: **125,411 USDT** (2025-10).
Volume (BTC) giảm theo thời gian vì giá tăng, nhưng quote_volume (USDT) tăng.
Số trades tăng liên tục (market microstructure phức tạp hơn).

---

## 1b. Domain Glossary — Thuật ngữ cho agents

> Agents không có trading background cần đọc section này TRƯỚC khi đọc
> chi tiết từng dataset. Nếu đã quen với crypto trading, có thể bỏ qua.

### Candle bar (nến OHLCV)

Mỗi bar tổng hợp tất cả trades trong 1 khoảng thời gian (15m, 1h, 4h, 1d):
- **Open**: Giá trade đầu tiên trong bar
- **High/Low**: Giá cao/thấp nhất trong bar
- **Close**: Giá trade cuối cùng trong bar
- **Volume**: Tổng lượng BTC giao dịch trong bar

Tất cả strategy backtesting dựa trên chuỗi bars. Giá giữa các bars là unknown
(trừ khi dùng aggtrades tick-level).

### Taker vs Maker

- **Maker**: Người đặt lệnh chờ (limit order) trên order book. Lệnh nằm đó
  cho đến khi ai đó match. Maker "tạo" thanh khoản.
- **Taker**: Người gửi lệnh match ngay với lệnh chờ trên book (market order
  hoặc aggressive limit). Taker "lấy" thanh khoản.
- **Taker volume = aggressive volume**: Khi taker MUA → giá có xu hướng tăng
  (buy pressure). Khi taker BÁN → giá có xu hướng giảm (sell pressure).
- **Taker buy ratio ≈ 0.50**: Cân bằng. >0.50 = net buy pressure, <0.50 = net sell.
  Thực tế mean = 0.4949, std = 0.048 → phần lớn thời gian gần cân bằng.

### Open Interest (OI)

Tổng số hợp đồng futures chưa đóng. Mỗi position có 1 long + 1 short.
- **OI tăng**: Tiền mới chảy vào thị trường (cả long lẫn short mở position)
- **OI giảm**: Tiền rút ra (positions đóng)
- **OI + giá**: OI tăng + giá tăng = long mới (bullish). OI tăng + giá giảm = short mới (bearish).
  OI giảm + giá di chuyển = liquidation/closing.
- **Quy mô**: Median OI = 82,410 BTC (~$5-8B USDT tùy giá). Range: 0 – 169,790 BTC.

### Long/Short Ratio

Tỉ lệ số lượng/giá trị position long vs short trên Binance Futures.
- `ls_ratio = 1.0`: Cân bằng
- `ls_ratio > 1.0`: Nhiều long hơn (crowd bullish)
- **Thực tế**: Mean = 1.61, range 0.43 – 5.63. Thị trường BTC thường lean long
  (vì BTC có long-term uptrend). Extreme readings (>3.0 hoặc <0.7) thường
  là contrarian signal.

### Funding Rate

Cơ chế giữ giá perpetual futures gần spot:
1. Mỗi 8h (00:00, 08:00, 16:00 UTC), Binance tính funding rate
2. Rate > 0: **long trả short** (thị trường quá bullish, phạt long)
3. Rate < 0: **short trả long** (thị trường quá bearish, phạt short)
4. Cơ chế tự điều chỉnh: funding cao → giữ long đắt → một số long đóng → giá futures hạ → funding giảm
- **Thực tế**: Mean = +0.011% mỗi 8h. Dương 86.8% thời gian (long-biased market).
  Range: -0.3% → +0.3%. Giá trị ±0.01% là bình thường, ±0.1%+ là extreme.

### Premium Index (Basis)

Chênh lệch giá giữa futures perpetual và spot index, tính theo tỉ lệ:
`premium = (futures_price - spot_index) / spot_index`
- **Premium > 0**: Futures đắt hơn spot (bullish expectation)
- **Premium < 0**: Futures rẻ hơn spot (bearish hoặc hedging pressure)
- **Thực tế**: Mean = -0.011%, P5/P95 = -0.067% / +0.103%. Biên độ rất nhỏ
  (contango/backwardation thường < 0.1%). Bull market premium lớn hơn (2021: +0.1%+),
  bear market premium âm (2022: -0.04%).

### Aggregated Trade

Binance gom nhiều raw trades xảy ra cùng giá + cùng thời điểm thành 1 record
(aggregated trade). Mỗi agg trade ghi: price, total quantity, thời gian, ai là maker.
- **Khác raw trade**: Raw có 1 trade = 1 fill. AggTrade gom fill cùng giá.
- **Frequency**: 2025 → ~17 agg trades/giây (trung bình), ~1.5M agg trades/ngày.
- **Dùng cho**: Microstructure analysis, order flow, volume profile, tick-by-tick patterns.

---

## 2. Spot Klines — OHLCV cơ bản

**Mục đích**: Dữ liệu nến spot BTCUSDT — nền tảng cho backtesting.

```
spot_klines/BTCUSDT/
├── 15m.parquet   (299,710 rows, 17.7 MB)
├── 1h.parquet    (74,941 rows, 5.8 MB)
├── 4h.parquet    (18,750 rows, 1.3 MB)    ← resolution chính của E5-ema21D1
└── 1d.parquet    (3,128 rows, 0.2 MB)     ← D1 regime filter
```

### Schema (11 columns)

| Column | Type | Mô tả |
|--------|------|--------|
| `open_time` | datetime64[ms, UTC] | Thời điểm mở nến |
| `close_time` | datetime64[ms, UTC] | Thời điểm đóng nến |
| `open` | float64 | Giá mở (USDT) |
| `high` | float64 | Giá cao nhất |
| `low` | float64 | Giá thấp nhất |
| `close` | float64 | Giá đóng |
| `volume` | float64 | Khối lượng BTC |
| `quote_volume` | float64 | Khối lượng USDT |
| `num_trades` | int32 | Số lượng trades trong nến |
| `taker_buy_base_vol` | float64 | Volume mua chủ động (BTC) |
| `taker_buy_quote_vol` | float64 | Volume mua chủ động (USDT) |

### Thành phần quan trọng cho nghiên cứu

- **OHLCV**: Cơ bản cho mọi strategy. Close price cho signal, High/Low cho ATR.
- **Taker volume**: `taker_buy_base_vol / volume` = tỉ lệ mua chủ động. Đây là
  thành phần VDO (Volume Delta Oscillator) trong E5-ema21D1.
- **Num trades**: Proxy cho market activity / participation.

### Sample rows (4h)

```
          2018-01-01         2021-04-15         2025-12-15
O/H/L/C:  13,716/13,716/     62,960/63,491/     88,172/90,053/
          13,155/13,410       62,334/63,057      88,074/89,283
volume:   1,676 BTC           8,402 BTC          2,700 BTC
USDT vol: 22.5M USDT         528.9M USDT        240.5M USDT
trades:   19,438              274,881            990,956
taker%:   44.1%               49.1%              50.1%
```

**Quan sát**: Giá ×6.5 (13K→89K). BTC volume giảm (1,676→2,700) nhưng USDT volume
tăng 10× (22M→240M). Trades tăng 50× (19K→990K). Taker ratio luôn quanh 50%.

### Statistical profile (4h, toàn bộ period)

| Metric | Median | P5 | P95 |
|--------|--------|-----|-----|
| Volume (BTC) | 5,970 | 1,017 | 35,654 |
| Quote volume (USDT) | 171.9M | — | — |
| Num trades | 174,290 | — | — |
| Taker buy ratio | 0.495 | — | — |

### Quan hệ với hệ thống hiện tại

File `data/bars_btcusdt_2016_now_h1_4h_1d.csv` trong btc-spot-dev là bản CSV
chuyển đổi từ spot_klines (H4 + D1), bổ sung warmup period. Spot klines parquet
là nguồn gốc, CSV là bản dẫn xuất.

---

## 3. Futures Metrics — Cấu trúc thị trường

**Mục đích**: Open interest, long/short ratio, taker volume ratio. Chỉ số
sentiment và positioning của thị trường futures.

```
futures_metrics/BTCUSDT/
├── 5m.parquet    (580,256 rows, 27 MB)    ← NATIVE resolution
├── 15m.parquet   (193,490 rows, 11 MB)    ← resampled (mean)
├── 1h.parquet    (48,387 rows, 3.1 MB)
├── 4h.parquet    (12,101 rows, 709 KB)
└── 1d.parquet    (2,018 rows, 117 KB)
```

### Schema (8 columns)

| Column | Type | Aggregation | Mô tả |
|--------|------|-------------|--------|
| `open_time` | datetime64[ms, UTC] | — | Thời điểm bắt đầu bar |
| `close_time` | datetime64[ms, UTC] | — | Thời điểm kết thúc bar |
| `open_interest` | float64 | **last** | Tổng OI (BTC notional) — snapshot cuối bar |
| `open_interest_value` | float64 | **last** | Tổng OI (USDT) — snapshot cuối bar |
| `toptrader_ls_ratio_accounts` | float64 | **mean** | L/S ratio top traders (by account count) |
| `toptrader_ls_ratio_positions` | float64 | **mean** | L/S ratio top traders (by position size) |
| `ls_ratio_accounts` | float64 | **mean** | L/S ratio toàn bộ tài khoản |
| `taker_ls_vol_ratio` | float64 | **mean** | Taker buy/sell volume ratio |

### Cách đọc

- **L/S ratio > 1.0**: Long nhiều hơn short (bullish positioning)
- **L/S ratio < 1.0**: Short nhiều hơn long (bearish positioning)
- **Taker ratio > 1.0**: Mua chủ động nhiều hơn (bullish pressure)
- **OI tăng + giá tăng**: New money vào long → confirm trend
- **OI tăng + giá giảm**: New money vào short → bearish conviction

### Cảnh báo: NaN gaps

| Column | NaN % | Giai đoạn |
|--------|-------|-----------|
| `toptrader_ls_ratio_accounts` | 15.9% | 2021-05 → 2025-07 |
| `toptrader_ls_ratio_positions` | 15.9% | 2021-05 → 2025-07 |
| `ls_ratio_accounts` | 1.0% | 2021-05 → 2025-07 |
| `taker_ls_vol_ratio` | 6.4% | 2020-09 → 2022-09 |

NaN là từ Binance source (thiếu data), không phải lỗi pipeline. Strategy phải
xử lý NaN — không được forward-fill mà không ghi chú rõ ràng.

### Sample rows (4h)

```
          2021-01-01          2023-06-15          2025-12-15
OI:       36,145 BTC          106,156 BTC         88,104 BTC
OI value: 1.06B USDT          2.66B USDT          7.86B USDT
top L/S:  1.54 / 1.21         2.72 / 1.20         2.79 / 2.22
L/S all:  1.60                3.08                 2.46
taker:    1.14                1.11                 1.11
```

**Quan sát**: OI value tăng 7× (1B→7.8B) dù OI (BTC) tương đương — do giá tăng.
L/S ratio tăng đáng kể (1.6→2.5) → thị trường ngày càng long-biased.
Taker ratio ổn định quanh 1.1 (slight buy dominance).

### Statistical profile

| Metric | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| OI (BTC) | — | — | 0 | 169,790 |
| OI value (USDT) | — | — | 0 | 12.8B |
| Top L/S (accounts) | 1.61 | 0.67 | 0.54 | 5.19 |
| L/S (all accounts) | 1.61 | 0.68 | 0.43 | 5.63 |
| Taker L/S vol | 1.11 | 0.12 | 0.74 | 2.46 |

---

## 4. Futures Premium Index — Basis futures-spot

**Mục đích**: Chênh lệch giá giữa futures perpetual và spot index.
`premium = (futures_price - spot_index) / spot_index`.

```
futures_premiumIndexKlines/BTCUSDT/
├── 15m.parquet   (216,952 rows, ~4.5 MB)
├── 1h.parquet    (54,239 rows, ~1.1 MB)
├── 4h.parquet    (13,560 rows, ~280 KB)
└── 1d.parquet    (2,260 rows, ~45 KB)
```

### Schema (7 columns)

| Column | Type | Mô tả |
|--------|------|--------|
| `open_time` | datetime64[ms, UTC] | Thời điểm mở bar |
| `close_time` | datetime64[ms, UTC] | Thời điểm đóng bar |
| `premium_open` | float64 | Premium lúc mở (decimal, 0.01 = +1%) |
| `premium_high` | float64 | Premium cao nhất trong bar |
| `premium_low` | float64 | Premium thấp nhất trong bar |
| `premium_close` | float64 | Premium lúc đóng |
| `num_trades` | int32 | Số 1m candles hợp thành |

### Cách đọc

- **Premium > 0**: Futures > Spot → market kỳ vọng giá lên
- **Premium < 0**: Futures < Spot → market kỳ vọng giá xuống
- **Biên độ bình thường**: ±2%. Biên độ cực đoan: ±5%+
- Premium thường dương trong bull market, âm hoặc gần 0 trong bear market

### Sample rows (4h)

```
Bull (2021-02):  O/H/L/C = +0.0011 / +0.0041 / -0.0080 / +0.0013
Bear (2022-06):  O/H/L/C = -0.0004 / +0.0007 / -0.0022 / -0.0004
Late (2025-12):  O/H/L/C = -0.0004 / +0.0002 / -0.0011 / -0.0004
```

**Quan sát**: Biên độ rất nhỏ (thường < 0.1%). Bull market có premium dương
lớn hơn và volatile hơn. Bear/late market premium âm nhẹ (mild backwardation).

| Metric | Value |
|--------|-------|
| Mean | -0.011% |
| Std | 0.058% |
| P5 / P95 | -0.067% / +0.103% |
| Min / Max | -1.059% / +0.423% |

### Mối quan hệ với funding rate

`funding_rate ≈ clamp(premium, ±0.05%)` mỗi 8h. Premium là tín hiệu liên tục,
funding rate là kết quả thanh toán rời rạc. Premium có information content cao
hơn funding rate (higher frequency, OHLC thay vì single point).

---

## 5. Funding Rate — Thanh toán 8h

**Mục đích**: Funding rate thanh toán thực tế giữa long/short trên Binance Futures.

```
futures_fundingRate/
├── BTCUSDT.parquet   (7,091 rows, 97 KB)
└── _catalog.json
```

### Schema (3 columns)

| Column | Type | Mô tả |
|--------|------|--------|
| `timestamp` | datetime64[ms, UTC] | Thời điểm thanh toán (00:00, 08:00, 16:00 UTC) |
| `funding_rate` | float64 | Rate dạng decimal (0.0001 = 0.01%) |
| `funding_interval_hours` | int8 | Luôn = 8 |

### Đặc điểm

- 3 lần/ngày cố định: 00:00, 08:00, 16:00 UTC
- Rate dương: Long trả Short. Rate âm: Short trả Long.
- Không forward-fill — chỉ chứa actual settlement points.
- Giá trị điển hình: ±0.01%. Cực đoan: ±0.3%.
- Mean = +0.011% mỗi 8h (≈ +0.5%/ngày annualized). Dương 86.8% thời gian.
- **Ý nghĩa kinh tế**: Funding rate dương bền vững = chi phí ẩn cho long futures.
  Spot strategy (như E5-ema21D1) không chịu chi phí này — lợi thế so với futures.

---

## 6. AggTrades — Dữ liệu tick-level

**Mục đích**: Mỗi aggregated trade riêng lẻ. Độ phân giải sub-second.
Dùng cho phân tích microstructure, volume profile, order flow.

```
aggtrades_bulk/BTCUSDT/
├── BTCUSDT-aggTrades-2017-08-17.parquet   (3,089 trades)
├── BTCUSDT-aggTrades-2017-08-18.parquet
├── ...                                     (3,128 file, mỗi ngày 1 file)
└── BTCUSDT-aggTrades-2026-03-10.parquet   (1,558,993 trades)
```

**Tổng**: ~80 GB, ~1.5 tỉ trades, 3,128 file.

### Schema (7 columns)

| Column | Type | Mô tả |
|--------|------|--------|
| `agg_trade_id` | int64 | ID trade tổng hợp |
| `price` | float64 | Giá giao dịch (USDT) |
| `quantity` | float64 | Số lượng BTC |
| `first_trade_id` | int64 | ID trade đầu tiên trong nhóm |
| `last_trade_id` | int64 | ID trade cuối cùng trong nhóm |
| `transact_time` | int64 | Timestamp microsecond (Unix × 1e6) |
| `is_buyer_maker` | bool | True = seller là taker (bán chủ động) |

### Kích thước theo thời gian

| Giai đoạn | Trades/ngày điển hình |
|-----------|----------------------|
| 2017-2018 | 3K – 50K |
| 2019-2020 | 50K – 500K |
| 2021-2023 | 500K – 2M |
| 2024-2026 | 1M – 3M |

### Sample (2025-12-15, 1 ngày)

```
Trades: 1,479,934 (17.1 trades/giây trung bình)
Price range: 85,147 – 90,053 USDT (biên độ 5.8%)
Median qty: 0.0006 BTC (~$53)    ← phần lớn trades rất nhỏ
Mean qty:   0.0134 BTC (~$1,186)  ← skewed bởi large trades
Total: 19,779 BTC (~$1.76B USDT)
Buyer maker %: 48.5% (gần cân bằng)
```

**Quan sát**: Phân phối quantity cực kỳ right-skewed — median gấp 22× nhỏ hơn mean.
Phần lớn trades là retail-size, nhưng volume dominated bởi large block trades.

### Lưu ý sử dụng

- **KHÔNG load toàn bộ 80 GB vào RAM**. Xử lý từng ngày hoặc theo batch.
- `is_buyer_maker=True` nghĩa là **seller là taker** (aggressor bán).
  Tức là trade này là **sell** pressure. Ngược trực giác với tên field.
- `transact_time` là microsecond, KHÔNG phải millisecond. Chia 1000 để
  có millisecond tương thích với các dataset khác.

---

## 7. Multi-coin 4h — 14 coins trong 1 file

**Mục đích**: Dữ liệu 4h OHLCV cho 14 coin chính. Dùng cho nghiên cứu
portfolio, correlation, cross-asset analysis.

```
bars_multi_4h.parquet   (224,035 rows, 14 MB)
```

### 14 coins

```
ADAUSDT   AVAXUSDT  BCHUSDT   BNBUSDT   BTCUSDT   DOGEUSDT  ETHUSDT
HBARUSDT  LINKUSDT  LTCUSDT   SOLUSDT   TRXUSDT   XLMUSDT   XRPUSDT
```

### Schema (13 columns)

Giống spot klines (§2) về OHLCV columns, nhưng có 2 khác biệt:

| Column | Type | Mô tả |
|--------|------|--------|
| `symbol` | string | Trading pair (vd: "BTCUSDT") |
| `interval` | string | Luôn = "4h" |
| `open_time` | **int64** | **Khác spot klines** — Unix ms, không phải datetime64 |
| `close_time` | **int64** | **Khác spot klines** — Unix ms, không phải datetime64 |
| _(+ 9 columns OHLCV giống spot klines)_ | | |

### Lưu ý

- **Timestamp format khác spot klines**: `open_time` và `close_time` là int64
  (milliseconds since epoch), không phải datetime64[ms, UTC]. Cần convert:
  `df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)`
- Mỗi coin có ngày bắt đầu khác nhau:

  | Coin | Bắt đầu | Bars |  | Coin | Bắt đầu | Bars |
  |------|---------|------|--|------|---------|------|
  | BTCUSDT | 2017-08 | 18,711 |  | ETHUSDT | 2017-08 | 18,711 |
  | BNBUSDT | 2017-11 | 18,226 |  | LTCUSDT | 2017-12 | 18,004 |
  | ADAUSDT | 2018-04 | 17,253 |  | XRPUSDT | 2018-05 | 17,150 |
  | XLMUSDT | 2018-05 | 16,988 |  | TRXUSDT | 2018-06 | 16,922 |
  | LINKUSDT | 2019-01 | 15,608 |  | DOGEUSDT | 2019-07 | 14,587 |
  | HBARUSDT | 2019-09 | 14,073 |  | BCHUSDT | 2019-11 | 13,712 |
  | SOLUSDT | 2020-08 | 12,171 |  | AVAXUSDT | 2020-09 | 11,919 |
- Filter theo `symbol` trước khi phân tích.
- Đây là convenience file — source gốc là Binance Vision cho từng coin.

---

## 8. Cách ghép dữ liệu

Tất cả dataset đều dùng `open_time` (UTC milliseconds) làm key.

```python
import pandas as pd

# Load cùng resolution
spot = pd.read_parquet("output/spot_klines/BTCUSDT/4h.parquet")
metrics = pd.read_parquet("output/futures_metrics/BTCUSDT/4h.parquet")
premium = pd.read_parquet("output/futures_premiumIndexKlines/BTCUSDT/4h.parquet")

# Merge
merged = (spot
    .merge(metrics, on="open_time", how="left", suffixes=("", "_metrics"))
    .merge(premium, on="open_time", how="left", suffixes=("", "_premium")))

# NaN xảy ra khi:
# - metrics: trước 2020-09 (chưa có data)
# - premium: trước 2020-01 (chưa có data)
# - metrics NaN gaps: xem §3 bảng NaN
```

### Funding rate (point-in-time) → merge khác

```python
funding = pd.read_parquet("output/futures_fundingRate/BTCUSDT.parquet")

# Funding là point-in-time (3x/ngày), KHÔNG phải bar.
# Reindex vào bar time bằng asof merge hoặc resample:
merged["funding_rate"] = pd.merge_asof(
    merged[["open_time"]],
    funding.rename(columns={"timestamp": "open_time"}),
    on="open_time", direction="backward"
)["funding_rate"]
```

---

## 9. Giới hạn và lưu ý cho nghiên cứu

### 9.1. Coverage không đồng nhất

| Giai đoạn | Spot | Futures metrics | Premium | Funding |
|-----------|------|----------------|---------|---------|
| 2017-08 → 2019-08 | ✓ | ✗ | ✗ | ✗ |
| 2019-09 → 2019-12 | ✓ | ✗ | ✗ | ✓ |
| 2020-01 → 2020-08 | ✓ | ✗ | ✓ | ✓ |
| 2020-09 → 2026-03 | ✓ | ✓ | ✓ | ✓ |

Feature nào dùng futures data sẽ thiếu ~3 năm đầu (2017-2020). Strategy phải
xử lý missing data period — hoặc giới hạn backtest window, hoặc fallback.

### 9.2. Single-exchange bias

Toàn bộ data từ Binance. Không có:
- OKX, Bybit, CME, Deribit data
- Cross-exchange arbitrage signals
- Market share shifts giữa sàn

### 9.3. Survival bias

14 coins trong bars_multi_4h là coins vẫn còn active trên Binance. Coins đã
delist (LUNA, FTT...) không có mặt. Portfolio research cần nhận thức giới hạn này.

### 9.4. Spot-only strategy constraint

E5-ema21D1 là spot long-only. Futures data (metrics, premium, funding) chỉ dùng
làm **signal input** (feature), KHÔNG dùng cho execution. Strategy không trade
futures, không dùng leverage, không short.

### 9.5. Freshness

Data pipeline chạy thủ công. Data mới nhất tùy thuộc lần fetch cuối.
Hiện tại: 2026-03-10/11. Xem `_catalog.json` trong mỗi thư mục để biết
chính xác thời điểm fetch.

---

## 10. Ý nghĩa cho x38 debate topics

### Topic 019 (DFL) — Discovery Feedback Loop

DFL-06 và DFL-07 đề xuất 10 phân tích dữ liệu hệ thống. Dữ liệu sẵn có:

| DFL Analysis | Dataset cần | Sẵn có? |
|-------------|------------|---------|
| Microstructure (tick patterns) | aggtrades_bulk | ✓ (80 GB) |
| Intrabar volume profile | aggtrades_bulk | ✓ |
| Regime transitions | spot_klines 4h/1d | ✓ |
| Time-of-day effects | spot_klines 15m/1h | ✓ |
| Volume dynamics | spot_klines + futures_metrics | ✓ (OI, L/S, taker) |
| Higher-order statistics | spot_klines | ✓ |
| Signal saturation | spot_klines + metrics | ✓ |
| Lead-lag (futures→spot) | premium + spot_klines | ✓ |
| Conditional dynamics | all datasets merged | ✓ |
| Liquidity (Amihud) | spot_klines (quote_volume) | ✓ (hoặc aggtrades) |

**Kết luận**: Toàn bộ 10 phân tích DFL-06 đều có data. Không cần thêm data source.

### Topic 006 (Feature Engine) — Feature families

6 feature families trong DFL-08 và khả năng tính toán:

| Family | Ví dụ | Data source |
|--------|-------|------------|
| Price-based | EMA, ATR, Bollinger | spot_klines OHLC |
| Volume-based | VDO, OBV, VWAP | spot_klines taker_vol |
| Microstructure | Trade imbalance, tick intensity | aggtrades_bulk |
| Futures-derived | OI change, L/S momentum, basis | futures_metrics + premium |
| Cross-asset | BTC-ETH correlation, altcoin momentum | bars_multi_4h |
| Composite | Regime score (price + volume + futures) | merged datasets |

### Topic 009 (Data Integrity)

Data quality issues cần giải quyết:
- Futures metrics NaN gaps (§3) → strategy phải handle
- Premium index duplicate cleanup đã xong (trong pipeline)
- Aggtrades `is_buyer_maker` semantics cần document rõ (§6)
- Cross-dataset timestamp alignment (ms vs μs) cần cẩn thận

### Topic 005 (Core Engine)

Hiện tại btc-spot-dev engine (`v10/core/data.py`) dùng CSV. Nếu Alpha-Lab engine
dùng Parquet trực tiếp, cần DataFeed mới. Spot klines schema tương thích — chỉ
cần rename columns (vd: `open` → `Open` nếu engine yêu cầu).

---

## 11. Catalog files

Mỗi dataset (trừ aggtrades và bars_multi_4h) có `_catalog.json` ghi metadata:
- Source (Binance Vision ZIP + REST API)
- Row count gốc, số duplicate removed
- Validation status (OK / WARN)
- Date range per source

Đọc catalog khi cần xác nhận data provenance hoặc quality status.

---

## Appendix: Quick Reference

### Load data nhanh (Python)

```python
import pandas as pd

# Spot 4h (primary)
spot_4h = pd.read_parquet("/var/www/trading-bots/data-pipeline/output/spot_klines/BTCUSDT/4h.parquet")

# Futures metrics 4h
metrics_4h = pd.read_parquet("/var/www/trading-bots/data-pipeline/output/futures_metrics/BTCUSDT/4h.parquet")

# Premium 4h
premium_4h = pd.read_parquet("/var/www/trading-bots/data-pipeline/output/futures_premiumIndexKlines/BTCUSDT/4h.parquet")

# Funding rate (point-in-time)
funding = pd.read_parquet("/var/www/trading-bots/data-pipeline/output/futures_fundingRate/BTCUSDT.parquet")

# Multi-coin
multi = pd.read_parquet("/var/www/trading-bots/data-pipeline/output/bars_multi_4h.parquet")
btc_4h = multi[multi["symbol"] == "BTCUSDT"]

# AggTrades (1 ngày)
day = pd.read_parquet("/var/www/trading-bots/data-pipeline/output/aggtrades_bulk/BTCUSDT/BTCUSDT-aggTrades-2026-03-10.parquet")
```

### File tree

```
/var/www/trading-bots/data-pipeline/output/
├── aggtrades_bulk/BTCUSDT/                          80 GB   3,128 files  2017-08 → 2026-03
│   └── BTCUSDT-aggTrades-YYYY-MM-DD.parquet                 ~1.5B trades
├── bars_multi_4h.parquet                            14 MB   224K rows    14 coins
├── futures_fundingRate/
│   ├── BTCUSDT.parquet                              97 KB   7K rows      2019-09 → 2026-02
│   └── _catalog.json
├── futures_metrics/BTCUSDT/                         42 MB   836K rows    2020-09 → 2026-03
│   ├── {5m,15m,1h,4h,1d}.parquet
│   └── _catalog.json
├── futures_premiumIndexKlines/BTCUSDT/               6 MB   287K rows    2020-01 → 2026-03
│   ├── {15m,1h,4h,1d}.parquet
│   └── _catalog.json
└── spot_klines/BTCUSDT/                             26 MB   396K rows    2017-08 → 2026-03
    ├── {15m,1h,4h,1d}.parquet
    └── _catalog.json
```
