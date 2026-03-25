# V10 Parameter Optimization Research

**Date:** 2026-02-22 → 2026-02-23
**Git:** c74c650
**Data:** data/bars_btcusdt_2016_now_h1_4h_1d.csv (2019-01-01 → 2026-02-20, warmup 365d)
**Strategy:** V8 Apex (VDO Absorption-Momentum), H4 bar frequency
**Initial cash:** $10,000

---

## 1. Bối cảnh & Mục tiêu

V10 đã có research pipeline hoàn chỉnh (candidate matrix × 3 cost scenarios → WFO →
decision gate → block bootstrap) nhưng một số kết quả nghiên cứu chưa được áp dụng
vào code production (`v8_apex.py` V8ApexConfig defaults).

**Mục tiêu:** Rà soát toàn bộ nghiên cứu V10, xác định thay đổi nào có bằng chứng
đủ mạnh để áp dụng, và tìm kiếm cải tiến mới thông qua nghiên cứu cô lập từng biến.

---

## 2. Phương pháp luận

### 2.1 Decision Gate (3 điều kiện PROMOTE)

Mọi candidate phải thỏa **cả 3 điều kiện** so với baseline để được PROMOTE:

1. **Harsh score ≥ baseline** — đảm bảo hiệu quả dưới chi phí xấu nhất
2. **TOPPING return ≥ baseline** — không được làm xấu hành vi trong thị trường sideway
3. **Turnover ≤ 1.2× baseline** — kiểm soát chi phí giao dịch

Nếu vi phạm bất kỳ điều kiện nào → **HOLD**. Nếu harsh MDD > baseline + 5% → **REJECT**.

### 2.2 Objective Scoring Formula

```
score = 2.5 × cagr
      - 0.60 × max_dd
      + 8.0  × max(0, sharpe)
      + 5.0  × max(0, min(pf, 3.0) - 1.0)
      + min(n_trades / 50, 1.0) × 5.0
```

### 2.3 Cost Scenarios

| Scenario | Spread | Slippage | Taker Fee | Round-trip |
|----------|:------:|:--------:|:---------:|:----------:|
| Smart    | 5 bps  | 2 bps    | 0.06%     | ~13 bps    |
| Base     | 5 bps  | 3 bps    | 0.10%     | ~31 bps    |
| Harsh    | 10 bps | 5 bps    | 0.15%     | ~50 bps    |

### 2.4 Thiết kế thí nghiệm

**Nguyên tắc cô lập biến:** Mỗi candidate chỉ thay đổi **đúng 1 parameter** so với
baseline → kết quả cho biết chính xác ảnh hưởng của parameter đó. Tránh confounding
(lỗi của gate study cũ: thay đổi `rsi_method` + `emergency_ref` đồng thời).

---

## 3. Nghiên cứu tiền nhiệm (Pre-existing)

### 3.1 Gate Study — `out_v10_full_eval` (2026-02-22)

**Câu hỏi:** So sánh 5 variant architecture: baseline_legacy, v9_like, peak_emergency,
peak_cooldown, peak_dd_adaptive.

| Candidate | Config | Harsh Score | CAGR% | MDD% | Tag |
|-----------|--------|:---:|:---:|:---:|:---:|
| baseline_legacy | pre_cost_legacy + wilder | 83.48 | 34.35 | 33.88 | **PROMOTE** |
| v9_like | post_cost + ewm_span | 77.45 | 33.05 | 36.30 | HOLD |
| peak_emergency | peak + wilder | 31.28 | 20.52 | 54.14 | REJECT |
| peak_cooldown | peak + wilder + cd=6 | 31.68 | 20.50 | 54.17 | REJECT |
| peak_dd_adaptive | peak + wilder + dd_adaptive | 22.95 | 13.90 | 40.41 | REJECT |

**Kết luận:** baseline_legacy (pre_cost_legacy + wilder) là variant tốt nhất. Tuy nhiên,
study này có **confounding**: baseline_legacy khác v9_like ở 2 biến cùng lúc
(rsi_method VÀ emergency_ref), nên không rõ biến nào tạo khác biệt.

### 3.2 Trail Tighten Study — `out_v10_trail_tighten` (2026-02-22)

**Câu hỏi:** Tối ưu `trail_tighten_profit_pct` (ngưỡng profit để siết trailing stop
từ 3.5×ATR xuống 2.5×ATR).

| Candidate | trail_tighten | Harsh Score | Base CAGR% | MDD% | Tag |
|-----------|:---:|:---:|:---:|:---:|:---:|
| baseline_legacy | 0.20 | 83.48 | 38.55 | 33.88 | PROMOTE |
| tighten_025 | 0.25 | 94.81 | 42.76 | 33.88 | **PROMOTE** |
| tighten_030 | 0.30 | 96.39 | 43.21 | 33.31 | PROMOTE |
| tighten_wfo | WFO best | 83.48 | 38.55 | 33.88 | PROMOTE |

**Lưu ý:** Tất cả candidates trong study này dùng `rsi_method: wilder` (không phải
default ewm_span), vì kế thừa config từ gate study baseline_legacy.

**Bằng chứng bổ sung cho tighten_025:**
- Paired block bootstrap: P(ΔSharpe > 0) = 99.6%, 95% CI [+0.009, +0.212]
- WFO: 100% OOS pass rate (5/5 windows)

**Lý do chọn 0.25 thay vì 0.30:**
- tighten_030 bootstrap: P = 89.6% (< 95% threshold)
- tighten_030 WFO: chỉ 75% pass rate (3/4 windows)
- DECISIONS.md ghi nhận chọn 0.25

### 3.3 Net Impact Analysis — `out_v10_trail_tighten/net_impact_analysis`

**Câu hỏi:** Định lượng thiệt hại thực tế từ false exits do tightened trailing stop.

| Metric | Giá trị |
|--------|---------|
| Fisher exact test p-value | 0.8042 (not significant) |
| Tightened false exit rate | 42.9% (vs non-tightened 33.3%) |
| Total forgone profit | 179.3% |
| Total recaptured via re-entry | 14.0% (recovery rate 7.8%) |
| Net dollar damage | $16,172 = 16.56% of total PnL |
| Profit protection ratio | 6.6× captured per 1 forgone |
| Verdict | MILD_ISSUE |

**Kết luận:** Tightening gây mất ~16.6% PnL qua false exits, nhưng bảo vệ 6.6× profit
nhiều hơn. Raise threshold giảm tightened exits mà không giảm protection.

### 3.4 Double Compression Analysis — `out_v10_trail_tighten/double_compression_analysis`

**Câu hỏi:** "Double compression" (ATR contraction + multiplier tightening cùng lúc)
có phải nguyên nhân chính của false exits không?

| Compression Type | Exits | False Exits | False Rate |
|:---|:---:|:---:|:---:|
| DOUBLE (ATR + mult) | 3 | 0 | **0.0%** |
| MULT_ONLY (tightened) | 11 | 6 | 54.55% |
| ATR_ONLY | 22 | 6 | 27.27% |
| NONE (normal) | 29 | 11 | 37.93% |
| **Overall** | 65 | 23 | 35.38% |

**Kết luận:** Double compression **KHÔNG phải vấn đề** (chỉ 3 lần, 0% false).
MULT_ONLY có false rate cao nhất (54.55%) — đây là lý do chính đáng để raise threshold.

### 3.5 Damage Analysis — `out_v10_trail_tighten/damage_analysis`

**Câu hỏi:** So sánh PnL thực tế giữa các threshold trên toàn bộ backtest.

| Candidate | Trades | Trail Exits | Total PnL | Avg Return% | Tightened Exits |
|-----------|:---:|:---:|---:|:---:|:---:|
| baseline_020 | 103 | 65 | $97,654 | 2.63% | 13 |
| tighten_025 | 101 | 63 | $123,031 | 2.96% | 12 |
| tighten_030 | 101 | 63 | $125,872 | 3.01% | 10 |

**Kết luận:** Raise threshold từ 0.20→0.25 tăng PnL 26% ($97.6K→$123K) với ít trades
hơn và ít tightened exits hơn. Từ 0.25→0.30 chỉ thêm 2.3% ($123K→$125.9K).

### 3.6 WFO Best Params — `out_v10_wfo_eval`

**Câu hỏi:** Walk-forward optimization tìm tham số tối ưu cho nhiều params cùng lúc.

| Parameter | Code Default | WFO Best | Windows |
|-----------|:---:|:---:|:---:|
| trail_atr_mult | 3.5 | **3.0** | 2 pass |
| entry_cooldown_bars | 3 | **2** | 2 pass |
| fixed_stop_pct | 0.15 | **0.18** | 2 pass |
| emergency_dd_pct | 0.28 | 0.28 | — |

**Hạn chế:** Chỉ 2 WFO windows pass — dữ liệu quá ít để kết luận.

---

## 4. Nghiên cứu mới (2026-02-23)

### 4.1 Vòng 1 — Cô lập từng biến (`out_v10_isolate`)

**Câu hỏi:** Mỗi thay đổi đơn lẻ (so với baseline mới, trail_tighten=0.25)
ảnh hưởng thế nào? Khắc phục confounding của gate study cũ.

**Baseline mới:** V8ApexConfig defaults + `trail_tighten_profit_pct: 0.25`
(rsi_method=ewm_span, emergency_ref=pre_cost_legacy)

#### Kết quả đầy đủ 3 scenarios:

| Candidate | Smart Score | Smart CAGR% | Base Score | Base CAGR% | Harsh Score | Harsh CAGR% | Harsh MDD% |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **baseline** | **121.37** | **48.56** | **112.74** | **45.55** | **88.94** | **37.26** | **36.28** |
| rsi_wilder | 114.84 | 45.75 | 105.94 | 42.76 | 94.81 | 38.50 | 33.07 |
| trail_atr_30 | 111.58 | 45.94 | 103.12 | 42.96 | 80.29 | 34.80 | 39.02 |
| fstop_018 | 119.43 | 47.87 | 110.85 | 44.88 | 86.51 | 36.61 | 37.26 |
| cooldown_2 | 122.94 | 49.74 | 107.30 | 44.21 | 97.55 | 40.81 | 37.26 |

#### Regime Analysis:

| Candidate | TOPPING Return% | TOPPING MDD% | SHOCK Return% | SHOCK MDD% |
|-----------|:---:|:---:|:---:|:---:|
| **baseline** | **-17.49** | **26.08** | **-14.10** | **27.11** |
| rsi_wilder | -21.99 | 26.35 | -18.29 | 29.18 |
| trail_atr_30 | -16.09 | 24.12 | -13.68 | 26.61 |
| fstop_018 | -17.49 | 26.08 | -13.75 | 27.11 |
| cooldown_2 | -21.50 | 26.86 | -16.83 | 28.28 |

#### Decision Gate:

| Candidate | Tag | Lý do HOLD/REJECT |
|-----------|:---:|---|
| **baseline** | **PROMOTE** | Thỏa cả 3 điều kiện |
| rsi_wilder | HOLD | TOPPING return -22.0% < baseline -17.5% |
| trail_atr_30 | HOLD | harsh score 80.29 < baseline 88.9 |
| fstop_018 | HOLD | harsh score 86.51 < baseline 88.9 |
| cooldown_2 | HOLD | TOPPING return -21.5% < baseline -17.5% |

#### Phát hiện quan trọng:

1. **`rsi_method: ewm_span` thực sự tốt hơn `wilder` cho TOPPING** (-17.5% vs -22.0%).
   Gate study cũ kết luận `wilder` thắng là do confounding với `emergency_ref`.

2. **`cooldown_2` có harsh score cao nhất** (97.55) nhưng hại TOPPING (-21.5%).
   Trade-off: +8.6 harsh score vs -4% TOPPING.

3. **`trail_atr_30` có TOPPING tốt nhất** (-16.1%) nhưng harsh score tệ (80.29).
   Trailing stop rộng hơn giúp giữ vị thế qua pullback trong TOPPING nhưng giảm
   profit capture trong harsh scenarios.

4. **`fstop_018` gần như neutral** — cùng TOPPING, harsh thấp hơn chút. Không có lợi.

### 4.2 Vòng 2 — Kết hợp bù trừ (`out_v10_combos`)

**Giả thuyết:** rsi_wilder/cooldown_2 tăng harsh nhưng giảm TOPPING. trail_atr_30
tăng TOPPING nhưng giảm harsh. Kết hợp có thể bù trừ điểm yếu.

| Candidate | Params thay đổi | Harsh Score | TOPPING% | Tag |
|-----------|---|:---:|:---:|:---:|
| **baseline** | — | **88.94** | **-17.5%** | **PROMOTE** |
| combo_wilder_trail30 | rsi_method=wilder, trail_atr=3.0 | 84.61 | -20.7% | HOLD |
| combo_cd2_trail30 | cooldown=2, trail_atr=3.0 | 86.11 | -20.0% | HOLD |
| combo_wilder_cd2 | rsi_method=wilder, cooldown=2 | 92.91 | -25.7% | HOLD |
| combo_triple | wilder + cooldown=2 + trail_atr=3.0 | 82.41 | -24.2% | HOLD |

**Kết luận:** Giả thuyết bù trừ **KHÔNG thành công**. Các biến không tương tác tuyến
tính — kết hợp thường tạo kết quả xấu hơn cả hai biến riêng lẻ. Đặc biệt
`combo_wilder_cd2` có TOPPING -25.7% (tồi hơn cả wilder -22.0% và cooldown -21.5%
đơn lẻ). Điều này cho thấy tác động tiêu cực lên TOPPING là **cộng dồn**, không triệt tiêu.

### 4.3 Vòng 3 — Nhắm vào TOPPING (`out_v10_topping`)

**Giả thuyết:** Thay đổi trực tiếp các parameter ảnh hưởng hành vi trong TOPPING
(regime switching, sizing, RSI gating) có thể cải thiện TOPPING mà không hại harsh.

| Candidate | Params thay đổi | Harsh Score | TOPPING% | MDD% | Tag |
|-----------|---|:---:|:---:|:---:|:---:|
| **baseline** | — | **88.94** | **-17.5%** | **36.28** | **PROMOTE** |
| fast_regime_off | d1_regime_off_bars: 4→2 | 72.36 | -17.0% | 38.97 | HOLD |
| cautious_030 | caution_mult: 0.50→0.30 | 85.95 | -17.7% | 36.49 | HOLD |
| rsi_ob_70 | rsi_overbought: 75→70 | 69.65 | -18.8% | 43.17 | **REJECT** |
| topping_defense | 3 thay đổi cùng lúc | 56.34 | -18.6% | 46.25 | **REJECT** |

**Phân tích từng candidate:**

- **fast_regime_off** (regime off nhanh hơn): TOPPING cải thiện rất nhỏ (-17.0% vs
  -17.5%) nhưng harsh score giảm 16.6 điểm. Regime switching nhanh gây whipsaw trong
  BULL, giảm capture trend chính.

- **cautious_030** (sizing thận trọng hơn trong CAUTION): Candidate **gần nhất** với
  baseline. Harsh score 85.95 (chỉ kém 3.0), TOPPING -17.7% (chỉ kém 0.2%). Tuy nhiên
  cả hai metric đều kém → không đạt gate.

- **rsi_ob_70** (RSI overbought thấp hơn): **REJECT**. Tighter RSI gating chặn quá
  nhiều entry, đặc biệt trong BULL runs. MDD 43.17% vượt ngưỡng reject (>baseline+5%).

- **topping_defense** (kết hợp cả 3): **REJECT**. MDD 46.25%, harsh score 56.34.
  Nhiều thay đổi "phòng thủ" cùng lúc phá hủy khả năng capture trend.

---

## 5. Tổng hợp so sánh toàn bộ 20 configurations

### Top 10 theo Harsh Score:

| # | Candidate | Study | Harsh Score | Harsh CAGR% | Harsh MDD% | TOPPING% | Gate |
|:-:|-----------|-------|:---:|:---:|:---:|:---:|:---:|
| 1 | cooldown_2 | isolate | 97.55 | 40.81 | 37.26 | -21.50 | HOLD |
| 2 | combo_wilder_cd2 | combos | 92.91 | 39.27 | 38.40 | -25.70 | HOLD |
| 3 | **baseline** | **all** | **88.94** | **37.26** | **36.28** | **-17.49** | **PROMOTE** |
| 4 | fstop_018 | isolate | 86.51 | 36.61 | 37.26 | -17.49 | HOLD |
| 5 | combo_cd2_trail30 | combos | 86.11 | 37.07 | 39.02 | -20.00 | HOLD |
| 6 | cautious_030 | topping | 85.95 | 36.19 | 36.49 | -17.74 | HOLD |
| 7 | combo_wilder_trail30 | combos | 84.61 | 35.69 | 36.44 | -20.70 | HOLD |
| 8 | combo_triple | combos | 82.41 | 35.42 | 37.83 | -24.25 | HOLD |
| 9 | trail_atr_30 | isolate | 80.29 | 34.80 | 39.02 | -16.09 | HOLD |
| 10 | fast_regime_off | topping | 72.36 | 31.93 | 38.97 | -16.96 | HOLD |

### Quan sát:

- Baseline đứng **#3** theo harsh score, nhưng là **#1 duy nhất** thỏa tất cả
  điều kiện gate (bao gồm TOPPING).
- Không có candidate nào vừa harsh score cao hơn baseline VÀ TOPPING tốt hơn baseline.
- Đây là Pareto frontier: baseline nằm trên đường biên hiệu quả giữa harsh và TOPPING.

---

## 6. Thay đổi đã áp dụng vào code

### `trail_tighten_profit_pct: 0.20 → 0.25`

**File:** `v10/strategies/v8_apex.py`, line 89
**Ngày áp dụng:** 2026-02-23

**Bằng chứng:**
- Decision gate: PROMOTE (harsh score 94.81 > baseline 83.48)
- Paired block bootstrap: P(ΔSharpe > 0) = 99.6%, 95% CI [+0.009, +0.212]
- WFO: 100% OOS pass rate (5/5 windows)
- Damage analysis: PnL tăng 26% ($97.6K → $123K)
- Net impact: giảm tightened exits (13→12), giảm false exit damage

**Tác động sau áp dụng (baseline mới):**

| Metric | Trước (0.20) | Sau (0.25) | Thay đổi |
|--------|:---:|:---:|:---:|
| Harsh Score | 83.48 | 88.94 | **+5.46** |
| Base CAGR% | 38.55 | 45.55 | **+7.00** |
| Smart CAGR% | — | 48.56 | — |
| Harsh MDD% | 33.88 | 36.28 | +2.40 |
| TOPPING% | -21.99 | -17.49 | **+4.50** |
| Trades | 103 | 100 | -3 |

**Lưu ý quan trọng:** Cải thiện TOPPING từ -22.0% → -17.5% là do thay đổi baseline
từ `rsi_method: wilder` (gate study) sang `ewm_span` (code default), KHÔNG phải do
trail_tighten. Trail_tighten cải thiện harsh score và CAGR.

---

## 7. Thay đổi KHÔNG áp dụng (và lý do)

### 7.1 `rsi_method: ewm_span → wilder`

**Lý do KHÔNG áp dụng:** Gate study cũ bị confounding (thay 2 biến cùng lúc). Khi test
cô lập, `wilder` có harsh score tốt hơn (+5.87 điểm) nhưng TOPPING xấu hơn đáng kể
(-22.0% vs -17.5%). Decision gate: **HOLD**.

### 7.2 `entry_cooldown_bars: 3 → 2`

**Lý do KHÔNG áp dụng:** Harsh score tốt nhất trong toàn bộ study (97.55) nhưng TOPPING
-21.5% (kém 4% so với baseline). Decision gate: **HOLD**.

### 7.3 `trail_atr_mult: 3.5 → 3.0`

**Lý do KHÔNG áp dụng:** TOPPING tốt nhất (-16.1%) nhưng harsh score quá thấp (80.29,
kém 8.65 điểm). Decision gate: **HOLD**.

### 7.4 `fixed_stop_pct: 0.15 → 0.18`

**Lý do KHÔNG áp dụng:** Gần như neutral — cùng TOPPING, harsh thấp hơn 2.43 điểm.
Không có lợi ích rõ ràng. Decision gate: **HOLD**.

### 7.5 `caution_mult: 0.50 → 0.30`

**Lý do KHÔNG áp dụng:** Candidate gần nhất (harsh -3.0, TOPPING -0.2%) nhưng vẫn
kém ở cả hai metric. Decision gate: **HOLD**.

### 7.6 `d1_regime_off_bars: 4 → 2`

**Lý do KHÔNG áp dụng:** Harsh score giảm 16.6 điểm. Regime switching nhanh gây whipsaw.
Decision gate: **HOLD**.

### 7.7 `rsi_overbought: 75 → 70`

**Lý do KHÔNG áp dụng:** MDD 43.17% → vượt ngưỡng reject. Chặn quá nhiều entry BULL.
Decision gate: **REJECT**.

### 7.8 Tất cả combinations

**Lý do KHÔNG áp dụng:** Các biến không bù trừ tuyến tính. Tác động tiêu cực TOPPING
cộng dồn khi kết hợp (wilder+cd2 → TOPPING -25.7%, tệ hơn cả hai riêng lẻ).

### 7.9 `peak_emergency`, `peak_cooldown`, `peak_dd_adaptive`

**Lý do KHÔNG áp dụng:** MDD 40-54% → tất cả **REJECT**. Peak-referenced emergency DD
gây holding through massive drawdowns.

### 7.10 `v9_like` (post_cost + ewm_span)

**Lý do KHÔNG áp dụng:** Harsh score 77.45 < baseline 83.48. Decision gate: **HOLD**.

---

## 8. Kết luận

### 8.1 Trạng thái hiện tại

V8ApexConfig defaults sau optimization:

```python
trail_tighten_profit_pct: float = 0.25   # ← ĐÃ CẬP NHẬT (từ 0.20)
rsi_method: str = "ewm_span"             # giữ nguyên — tốt hơn wilder cho TOPPING
emergency_ref: str = "pre_cost_legacy"    # giữ nguyên
trail_atr_mult: float = 3.5              # giữ nguyên
entry_cooldown_bars: int = 3             # giữ nguyên
fixed_stop_pct: float = 0.15            # giữ nguyên
```

### 8.2 Performance (baseline mới, base scenario)

| Metric | Giá trị |
|--------|---------|
| CAGR | 45.55% |
| Max Drawdown | 34.78% |
| Sharpe | 1.32 |
| Sortino | ~2.0 |
| Profit Factor | 1.83 |
| Win Rate | 52% |
| Trades | 100 |
| Fee Drag | 3.94%/yr |
| Score | 112.74 |

### 8.3 Structural Limitation

Điểm yếu TOPPING (-17.5% trong base scenario) là **cấu trúc** của chiến lược
trend-following. Mọi nỗ lực giảm TOPPING loss đều phá hủy BULL capture hoặc harsh
robustness. V9 MDD analysis đã kết luận đúng: *"Baseline at point of good equilibrium.
Any further optimization needs full pipeline proof."*

### 8.4 Hướng nghiên cứu tiếp theo (nếu có)

1. **Regime-conditional trailing stop:** Dùng trail_atr_mult khác nhau theo regime
   (ví dụ: 3.0 trong CAUTION, 3.5 trong RISK_ON). Cần thêm logic mới vào strategy.

2. **Adaptive caution_mult:** Thay vì fixed 0.50, dùng sliding scale theo volatility.

3. **Re-entry filter:** Giảm cost từ false exit → re-entry cycles (hiện recovery
   rate chỉ 7.8%).

4. **Out-of-sample validation:** Chạy lại toàn bộ study khi có thêm 6+ tháng data mới
   để xác nhận robustness.

---

## 9. Artifacts

| Directory | Nội dung |
|-----------|----------|
| `out_v10_full_eval/` | Gate study — 5 architecture variants |
| `out_v10_wfo_eval/` | WFO optimization — trail_atr, fixed_stop, cooldown |
| `out_v10_trail_tighten/` | Trail tighten study + net impact + compression + damage |
| `out_v10_isolate/` | Cô lập 4 biến đơn lẻ (mới) |
| `out_v10_combos/` | Kết hợp 4 combos (mới) |
| `out_v10_topping/` | Nhắm TOPPING — 4 candidates (mới) |
| `candidates_v10_gate.yaml` | Config gate study |
| `candidates_v10_trail_tighten.yaml` | Config trail tighten study |
| `candidates_v10_wfo.yaml` | Config WFO study |
| `candidates_v10_isolate.yaml` | Config isolated variable study (mới) |
| `candidates_v10_combos.yaml` | Config combo study (mới) |
| `candidates_v10_topping.yaml` | Config TOPPING study (mới) |
