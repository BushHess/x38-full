# META-PROMPT — Gửi prompt này trong Claude Code CLI

---

Dữ liệu BTC spot (OHLCV + taker_buy_volume) nằm tại:
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_15m.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_1h.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_4h.csv  (PRIMARY)
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_1d.csv  (CONTEXT)

Thư mục làm việc (lưu code, figures, tables, reports):
- /var/www/trading-bots/btc-spot-dev/research/x27/

Hãy thiết kế và thực hiện một chương trình nghiên cứu nhiều phase để tìm ra thuật toán trading tốt nhất cho BTC spot, H4, long-only.

## Quy trình nghiên cứu bắt buộc

Bạn là nhà nghiên cứu, không phải máy bắn indicator. Quy trình:
EDA trước → formalize sau → candidate sau nữa → code cuối cùng.

Trước khi bắt đầu, hãy tạo một chuỗi prompt/plan nhiều phase cho chính mình, theo cấu trúc tối thiểu:

1. **Data audit** — verify dữ liệu, chưa phân tích
2. **Price behavior EDA** — mô tả statistical properties của BTC H4 (returns, autocorrelation, Hurst, volatility structure, volume, D1 regime). CHỈ MÔ TẢ, không interpret.
3. **Signal landscape EDA** — sweep nhiều LOẠI entry signal (momentum, breakout, crossover, vol-breakout) và exit signal (trailing stop, reversal, time-based), đo: detection rate, false positive rate, lag, churn rate, capture ratio. Vẽ efficiency frontier. KHÔNG chọn winner.
4. **Formalization** — từ evidence, derive admissible function classes cho entry + exit. Power analysis.
5. **Go/No-Go** — đủ evidence thì design, không đủ thì STOP (kết luận hợp lệ).
6. **Design** — candidate algorithms, mỗi cái phải trace ngược về evidence.
7. **Validation** — backtest, WFO, bootstrap, cost sensitivity. Pre-committed rejection criteria.
8. **Final report** — honest conclusion.

## Constraints cố định

- BTC spot (không futures/perps)
- H4 primary, D1 cho context
- Long-only
- Cost: 50 bps round-trip

## Mở — được thay đổi hoàn toàn

- Entry trigger, exit mechanism, filters: BẤT KỲ, miễn evidence support
- Tổng DOF ≤ 10, không giới hạn từng component

## Prior research — GIẢ THUYẾT để verify, KHÔNG phải constraints

56 studies trước đó trên cùng data tìm ra những điều sau. Treat chúng là hypotheses — verify hoặc refute bằng EDA của bạn. Nếu evidence của bạn mâu thuẫn, ƯU TIÊN evidence của bạn.

1. **Trend persistence**: BTC H4 có positive autocorrelation ở lag 30-120 bars. Trend-following có alpha.
2. **Cross-scale redundancy**: Thay đổi EMA slow 60-144 cho kết quả gần nhau (ρ=0.92). Alpha từ MỘT underlying phenomenon.
3. **Entry lag**: EMA(30/120) crossover fires ~30 bars trễ. Giảm lag → tăng false signals. *CÂU HỎI MỞ: có cách giảm lag mà không tăng false signals?*
4. **Exit churn**: ATR trail stop gây chu kỳ thoát→vào lại→thoát, tốn kém. Predictable (AUC=0.805) nhưng ceiling sửa ~10%. *CÂU HỎI MỞ: có exit mechanism nào ít churn hơn?*
5. **Volume info ≈ 0 tại entry**: Volume/TBR không phân biệt trade tốt/xấu. *CÂU HỎI MỞ: volume có info ở chỗ khác (regime, exit)?*
6. **D1 regime filter**: D1 close > D1 EMA(21) cải thiện metrics (p=1.5e-5). *CÂU HỎI MỞ: có regime ID tốt hơn?*
7. **Low exposure ~45%**: 55% idle time. *CÂU HỎI MỞ: idle time có exploitable structure?*
8. **Short-side negative EV**: BTC short negative EV mọi timescale. Xác nhận long-only.
9. **Cost dominance**: Cost 50→15 bps tăng Sharpe 1.19→1.67. Cost > mọi algorithm change.
10. **Complexity ceiling**: 40+ params = zero value over 3 params. *NHƯNG: 3 params hiện tại chưa chắc là 3 params tối ưu.*

## Benchmark (để so sánh, KHÔNG phải để bắt chước)

VTREND: EMA(30/120) entry + VDO(12,28) filter + D1 EMA(21) regime + ATR trail(×3.0) exit.
Sharpe 1.19, CAGR 52.6%, MDD 61.4%, 201 trades, exposure 45%, cost 50 bps RT.
Vấn đề: mua trễ, bán sớm, churn, 55% idle.

## Quy tắc methodology

- **Observation before interpretation**: khi EDA nói "chỉ mô tả" thì chỉ mô tả.
- **Candidate moratorium**: trước phase design, KHÔNG được nêu indicator/strategy name.
- **Derive before propose**: mọi candidate phải trace về Figure → Observation → Proposition.
- **Anti-post-hoc**: không nhớ indicator rồi bọc bằng toán. Derive từ data.
- **Honest stopping**: "không tìm được gì tốt hơn" là kết luận hợp lệ.
- **Provenance tags**: Fig##, Tbl##, Obs##, Prop##, Cand##, Test## — claim không có tag = UNSUPPORTED.

## Cách thực hiện

Chạy trong Claude Code CLI. Code viết vào x27/code/, chạy bằng Bash tool.
Plots lưu vào x27/figures/, tables vào x27/tables/, reports (.md) vào x27/.

Sau khi tạo plan, thực hiện Phase 1 (data audit) ngay.
Sau mỗi phase, dừng lại, trình bày kết quả, và chờ tôi cho phép tiếp tục phase kế.
Tôi sẽ review mỗi phase trước khi bạn chuyển sang phase tiếp theo.
