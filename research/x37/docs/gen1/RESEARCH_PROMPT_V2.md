# BTC Spot Long-Only Trading System — Open Research

## Dữ liệu

BTC/USDT spot, Binance, H4 và D1, 2017-08 đến 2026-02.
Columns: open_time, close_time, open, high, low, close, volume,
taker_buy_base_vol (real order flow — not OHLC proxy), quote_volume, interval.

## Execution Model

- Long-only. Short BTC là negative-EV ở mọi timescale (Sharpe -0.64, đã chứng minh).
- Signal tại bar close, fill tại open bar kế tiếp.
- Chi phí: 20 bps round-trip (spread 5 + slippage 2.5 + fee 5 bps mỗi lượt).
- Vốn khởi điểm: $10,000.
- Warmup: 365 ngày không giao dịch (indicator initialization).

## Benchmarks

Hai hệ thống từ 68 nghiên cứu trước, đo tại 20 bps RT:

| | Baseline (E0+regime) | Best Variant (V4) |
|---|---|---|
| Sharpe | 1.636 | 1.830 |
| CAGR | 72.7% | 80.4% |
| MDD | -38.4% | -33.6% |
| Bootstrap Median Sharpe | 0.766 | 0.733 |
| Bootstrap P(Sharpe>0) | 96.8% | 96.6% |
| Trades | 186 | 196 |
| Tunable params | 3 | 6+ |

V4 thắng full-sample nhưng **thua bootstrap** (median 0.73 vs baseline 0.77)
và fragile trên dữ liệu gần nhất (2025+, Sharpe ~0.15).

Mục tiêu: **Tìm hệ thống tốt hơn, hoặc xác nhận đây đã là vùng tối ưu.**

## Tiếp cận

Từ dữ liệu thô, không giả định trước framework (trend, mean-reversion, hay bất kỳ cấu trúc nào).

**First principles**: phân rã dữ liệu, đo lường từng kênh thông tin (price, volume,
order flow, volatility, cross-timeframe, calendar, hoặc bất kỳ cấu trúc nào phát hiện
được), hiểu cơ chế thị trường đằng sau, rồi thiết kế entry/exit/sizing dựa trên hiểu biết.

Grid search CHỈ được dùng ở bước cuối để tinh chỉnh tham số đã có rationale rõ ràng.
Report tổng số configurations đã thử (cần cho multiple-testing correction).

## Proven Constraints (from 68 prior studies)

### What WORKS (đã chứng minh, có thể dùng hoặc cải tiến)
- **EMA crossover entry**: p=0.0003, survives Bonferroni/Holm/BH correction
- **ATR trailing stop + EMA cross-down exit**: p=0.0003, strictly dominates trail-only
- **VDO filter** (taker buy imbalance): 16/16 timescales, DOF-corrected p=0.031
- **D1 EMA regime filter**: 16/16 ALL metrics, p=1.5e-5, range 15-40d proven
- **Alpha from GENERIC trend-following**: plateau across slow=60-144 EMA periods

### What DOES NOT WORK (đã thử nghiệm kỹ, không lặp lại)

| Đã thử | Study | Kết quả | Tại sao |
|--------|-------|---------|---------|
| Short-side BTC | X11 | Sharpe -0.64, MDD 92% | Negative-EV mọi timescale |
| Partial take-profits | X10 | Phá fat-tail alpha | Top 5% trades = 129.5% tổng lợi nhuận |
| Exit geometry (pullback multipliers) | X23 | Sharpe -0.229 vs baseline | Tăng churn |
| Trail arming delay | X24 | 53 entries không bao giờ arm | Degrades exits |
| Volume entry filters (ngoài VDO) | X25 | Mọi feature p > 0.39 | VDO đã near-optimal |
| Multi-coin portfolio | X20 | Altcoin median Sharpe 0.42 | Pha loãng BTC alpha |
| Conviction/variable sizing | X21 | Entry IC = -0.039 | Zero predictive power cho size |
| ML churn filters tại < 30 bps | X22 | Filters HẠI dưới 30 bps | Chỉ có giá trị ở cost cao |
| WATCH state machine (re-entry) | X16-X17 | Path-specific | Không robust khi resample |
| Fractional/partial actuators | X19, X30 | Static full-exit thắng | Thêm complexity, không thêm alpha |
| D1 regime làm EXIT signal | X31-A | Selectivity 0.21 | Cắt winner 5x nhiều hơn loser |
| Re-entry barriers | X31-B | Oracle ceiling +0.033 Sharpe | Dưới ngưỡng cải thiện có ý nghĩa |
| Complex system 40+ params | V8/V11 | Zero value vs 3-param base | Overfitting |

### Hard Constraints (đo được, không phải ý kiến)

- **Fat-tail**: top 5% trades = 129.5% tổng profits → cơ chế nào cắt winner phải
  justify được bằng evidence, không bằng "ổn định hơn".
- **Cross-timescale ceiling**: ρ = 0.92 giữa EMA 60-200 → max diversification gain +3.5%.
- **Oracle exit ceiling**: perfect exit knowledge chỉ thêm +0.033-0.038 Sharpe.
- **10% improvement cap**: perfect churn filter chỉ thêm tối đa +0.845 Sharpe.

## Validation — Bắt buộc

Mọi candidate system phải pass TẤT CẢ các tests sau. Không có exception.

### V1. Full-Sample Backtest (2019-01-01 đến 2026-02-20)
- Report: Sharpe, CAGR, MDD, trades, win rate, profit factor, Sortino, Calmar.
- Sharpe annualized: `(mean(r) / std(r, ddof=0)) × √2190` (H4 bars/year).

### V2. Walk-Forward Validation (12 windows × 6 tháng, non-overlapping)
- Mỗi window có 365-ngày warmup.
- **Positive Sharpe trong ≥ 10/12 windows** (hard gate).
- Report: Sharpe từng window + mean + median.
- Report: **trend Sharpe theo thời gian** (cải thiện hay suy thoái?).

### V3. Bootstrap Robustness (500 paths, 20 bps)
- VCBB: block size 60, context 90, K=50.
- **P(Sharpe > 0) ≥ 95%** (hard gate).
- **Median Sharpe ≥ 0.6** (target).
- Report: median, mean, P5, P95, P(Sharpe>0).

### V4. Holdout (2024-01-01 đến 2026-02-20)
- **Sharpe > 0** (hard gate).
- Report: Sharpe, CAGR, MDD.

### V5. Regime Stability (4 epochs)
- Pre-2021 | 2021-2022 | 2023-2024 | 2025+
- **Không epoch nào Sharpe < 0** (hard gate).
- Report: Sharpe, CAGR, MDD từng epoch.

### V6. Cost Sensitivity (5 đến 50 bps RT)
- **Sharpe > 0 tại 50 bps** (hard gate).
- Report: Sharpe tại mỗi mức cost, slope of degradation.

### V7. Parameter Plateau
- ±20% perturbation trên từng tham số.
- **ΔSharpe ≤ 0.05** (hard gate — sharp peak = overfit = reject).

### V8. Trade Analysis
- Report: best/worst trade, avg hold, churn count (re-entry ≤ 24h).
- **Best trade ≥ 25% total profit** (fat-tail preservation check).
- **Churn < 5% of trades**.

### V9. PSR (Probabilistic Sharpe Ratio)
- Bailey & López de Prado (2012), benchmark SR* = 0.
- **PSR ≥ 0.95** (hard gate).

### V10. Block-Size Sensitivity (diagnostic — không phải gate)
- Chạy VCBB bootstrap với blksz = [30, 60, 120, 180] trên candidate system.
- Report: median Sharpe và P(Sharpe>0) tại mỗi block size.
- **Không thay đổi pass/fail** — mục đích là thêm context để interpret V3 bootstrap.
- Nếu median Sharpe tăng monotonic với blksz → bootstrap ở blksz=60 có thể
  underestimate system (regime structure bị phá ở block nhỏ).
- Nếu median Sharpe plateau hoặc giảm → kết quả blksz=60 đáng tin.
- Report kết quả dưới dạng bảng, để người dùng tự đánh giá.

## "Tốt hơn" nghĩa là gì — ranked

Một system mới được coi là tốt hơn nếu cải thiện theo thứ tự ưu tiên:

1. **Bootstrap median Sharpe cao hơn** — đo robustness trên nhiều paths.
2. **P(Sharpe > 0) cao hơn** — xác suất hệ thống có lời.
3. **WFO consistency tốt hơn** — nhiều windows dương hơn, mean cao hơn.
4. **MDD thấp hơn tại CAGR tương đương** — risk-adjusted quality.
5. **Regime stability tốt hơn** — ít epoch yếu hơn.
6. **Ít tham số hơn** tại performance tương đương — simpler = more likely real.
7. **Full-sample Sharpe cao hơn** — informative nhưng không decisive một mình.

**Nguyên tắc**: System thắng full-sample nhưng thua bootstrap là KHÔNG tốt hơn.
System thắng bootstrap nhưng gãy ở 2025+ cần được flag rõ ràng (vẫn pass nếu
Sharpe > 0, nhưng context quan trọng).

## Deliverables

1. **Data decomposition**: Thông tin khai thác được từ mỗi kênh, ranked by IC.
2. **Design rationale**: Mỗi component (entry, exit, filter, sizing) → cơ chế nào,
   tại sao nên persist out-of-sample.
3. **Full validation** (V1–V10) với comparison table vs benchmarks.
4. **Verdict**:
   - **SUPERIOR**: Thắng cả hai benchmarks trên bootstrap + pass mọi gate.
   - **COMPETITIVE**: Nằm trong bootstrap CI — xác nhận vùng tối ưu.
   - **INFERIOR**: Thua benchmarks — document tại sao và học được gì.
5. **Charts**: Equity curves, bootstrap distributions, WFO per window,
   cost sensitivity, regime decomposition, block-size sensitivity.

## Anti-Patterns

- Lookahead (dùng dữ liệu tương lai dưới bất kỳ hình thức nào).
- Optimize trên full sample rồi "validate" trên cùng data.
- Lấy full-sample Sharpe làm bằng chứng chính (bootstrap là primary).
- Thêm complexity mà không có bootstrap-proven benefit.
- Lặp lại dead-ends ở bảng trên.
- Claim improvement mà không có statistical evidence.
- Dùng quá 6 tham số mà không có justification đặc biệt.
