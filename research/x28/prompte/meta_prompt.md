# META-PROMPT — X28

---

Dữ liệu BTC spot (OHLCV + taker_buy_volume) nằm tại:
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_15m.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_1h.csv
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_4h.csv  (PRIMARY)
- /var/www/trading-bots/btc-spot-dev/data/btcusdt_1d.csv  (CONTEXT)

Thư mục làm việc:
- /var/www/trading-bots/btc-spot-dev/research/x28/

Hãy thiết kế và thực hiện một chương trình nghiên cứu nhiều phase để tìm ra
thuật toán trading tốt nhất cho BTC spot, H4, long-only.

## Quy trình nghiên cứu bắt buộc

Bạn là nhà nghiên cứu. Quy trình:
EDA trước → formalize sau → candidate sau nữa → code cuối cùng.

Chuỗi phase bắt buộc:
1. **Data audit** — verify dữ liệu, chưa phân tích
2. **Price behavior EDA** — mô tả statistical properties. CHỈ MÔ TẢ.
3. **Signal landscape EDA** — sweep TOÀN BỘ không gian entry × exit × filter,
   bao gồm composite signals. Đo IMPACT lên target metric. KHÔNG chọn winner.
4. **Formalization** — derive admissible function classes. Power analysis.
5. **Go/No-Go** — đủ evidence thì design, không thì STOP.
6. **Design** — candidates từ TOP-N của Phase 3, trace về evidence.
7. **Validation** — backtest, WFO, bootstrap, robustness. Pre-committed criteria.
8. **Final report** — honest conclusion.

## Constraints cố định

- BTC spot (không futures/perps)
- H4 primary, D1 cho context
- Long-only
- Cost: 50 bps round-trip

## Objective — RÕ RÀNG VÀ DUY NHẤT

**Maximize Sharpe ratio.**
Constraint: MDD ≤ 60%.
Tổng DOF ≤ 10.

Report tất cả metrics nhưng OPTIMIZE cho Sharpe.
Mọi quyết định design phải được justify bằng impact lên Sharpe.

## Mở — được thay đổi hoàn toàn

- Entry trigger: BẤT KỲ
- Exit mechanism: BẤT KỲ, bao gồm composite (ví dụ: exit A OR exit B)
- Filters: BẤT KỲ
- Combinations: BẤT KỲ

## Prior research — BẢNG SỐ, KHÔNG NARRATIVE

56 studies trước đó trên cùng dataset đo được các giá trị sau.
Đây là DATA POINTS để tham khảo, không phải vấn đề cần giải quyết.
Bạn KHÔNG BỊ YÊU CẦU improve, fix, hay address bất kỳ metric nào dưới đây.
Chỉ dùng để so sánh kết quả của bạn.

| Strategy | Sharpe | CAGR | MDD | Trades | Exposure | Churn% | AvgWin | AvgLoss | DOF |
|----------|--------|------|-----|--------|----------|--------|--------|---------|-----|
| EMA cross + dual exit + VDO + D1 regime | 1.08 | 58% | 53% | 219 | 43% | 49% | 10.9% | -3.7% | 5 |
| EMA cross + trail only | 0.63 | — | — | — | — | — | — | — | 3 |
| Breakout + trail | 0.91 | 39% | 41% | 70 | 28% | 0% | 18.0% | -5.5% | 3 |
| Breakout + trail + D1 regime | 0.92 | 39% | 42% | 68 | 28% | 0% | 18.4% | -5.5% | 4 |
| ROC threshold + trail | 0.45 | 18% | 54% | 55 | 21% | 2% | 17.7% | -7.7% | 4 |
| Buy-and-hold | ~0.60 | ~35% | ~83% | 1 | 100% | 0% | — | — | 0 |

Observations từ prior research (FACTS, không interpretation):
- Return autocorrelation: |ρ| < 0.05 ở mọi lag, nhưng Hurst ≈ 0.58
- Volatility clustering: |return| ACF significant ở 100/100 lags
- Volume tại entry: correlation với trade outcome |r| < 0.03
- D1 regime (close > EMA21): return differential +167 pp/yr (p = 0.0004)
- Cost sensitivity: 50→15 bps tăng Sharpe từ 1.08→1.32

## Quy tắc methodology

- **Observation before interpretation**: EDA chỉ mô tả
- **Candidate moratorium**: trước Phase 6, KHÔNG nêu indicator/strategy name
- **Derive before propose**: Cand## ← Prop## ← Obs## ← Fig##
- **Anti-post-hoc**: không nhớ indicator rồi bọc bằng toán
- **Honest stopping**: "không tìm được gì tốt hơn" là kết luận hợp lệ
- **Provenance tags**: Fig##, Tbl##, Obs##, Prop##, Cand##, Test##

## Cách thực hiện

Chạy trong Claude Code CLI. Code viết vào x28/code/, chạy bằng Bash tool.
Plots lưu vào x28/figures/, tables vào x28/tables/, reports (.md) vào x28/.

Sau khi tạo plan, thực hiện Phase 1 ngay.
Sau mỗi phase, dừng lại và chờ tôi cho phép tiếp tục.
