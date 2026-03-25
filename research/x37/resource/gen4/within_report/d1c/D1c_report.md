# D1c Report — Candidate Designs

## Candidate 1

**ID:** `btcsd_20260318_c1_av4h`

### Cơ chế

Khai thác continuation trên 4h nhưng chỉ khi nền 1d đang "orderly":

- daily range-vol 84 ngày đang ở trạng thái thấp tương đối
- daily price không nằm ở nửa dưới rolling range 168 ngày

Đây là thiết kế tối giản nhất bám sát D1b: D1 anti-vol là slow filter mạnh nhất, còn 4h rangepos_168 là directional engine sạch nhất.

**Timeframe:** 1d, 4h

### Feature formulas

```
d1_range1_t = (high_t - low_t) / close_t
d1_rangevol84_t = mean(d1_range1_{t-83:t})
d1_rangevol84_rank365_t = pct_rank(d1_rangevol84_t within trailing 365 closed D1 bars)
d1_rangepos168_t = (close_t - rolling_low_168) / (rolling_high_168 - rolling_low_168)
h4_rangepos168_t = (close_t - rolling_low_168) / (rolling_high_168 - rolling_low_168)
```

### Signal logic

**Entry khi flat:**
- `d1_rangevol84_rank365_t <= q_d1_antivol_rank`
- `d1_rangepos168_t >= 0.50`
- `h4_rangepos168_t >= q_h4_rangepos_entry`

**Hold khi long:**
- các điều kiện daily giữ nguyên
- `h4_rangepos168_t >= q_h4_rangepos_hold`

**Exit:** còn lại

### Calibration

- daily anti-vol: trailing percentile rank
- daily trend permission: fixed midpoint 0.50
- 4h trend: raw rangepos threshold + hysteresis

### Tunables

| Parameter | Values |
|---|---|
| `q_d1_antivol_rank` | {0.35, 0.50, 0.65} |
| `q_h4_rangepos_entry` | {0.55, 0.65} |
| `q_h4_rangepos_hold` | {0.35, 0.45} |

### Fixed

- D1 range-vol window 84
- D1 rangepos window 168
- H4 rangepos window 168

**Layers:** 2

### Viability gate

Config permissive nhất chạy trên năm 2020:

- `q_d1_antivol_rank=0.65`
- `q_h4_rangepos_entry=0.55`
- `q_h4_rangepos_hold=0.35`

Kết quả: **7 entries / năm, đạt ngưỡng.**

---

## Candidate 2

**ID:** `btcsd_20260318_c2_flow1hpb`

### Cơ chế

Khai thác hồi phục sau pullback 1h, nhưng chỉ khi:

- daily taker-flow đã nguội xuống mức không dương
- bối cảnh 4h vẫn mang tính bullish

Đây là candidate pullback/recovery, không phải trend-chasing. Nó dùng block độc lập D1 flow exhaustion và block bổ sung 1h ret_168 reversal.

**Timeframe:** 1d, 4h, 1h

### Feature formulas

```
d1_flow12_t = 2 * sum(taker_buy_base_vol_{t-11:t}) / sum(volume_{t-11:t}) - 1
h4_rangepos168_t = (close_t - rolling_low_168) / (rolling_high_168 - rolling_low_168)
h1_ret168_t = close_t / close_{t-168} - 1
```

### Signal logic

**Entry khi flat:**
- `d1_flow12_t <= 0.0`
- `h4_rangepos168_t >= q_h4_rangepos_min`
- `h1_ret168_t <= theta_h1_ret168_entry`

**Hold khi long:**
- giữ 2 điều kiện chậm như trên
- `h1_ret168_t <= theta_h1_ret168_hold`

**Exit:** còn lại

### Calibration

- daily flow dùng fixed sign split 0.0
- 4h trend dùng raw rangepos threshold
- 1h pullback dùng raw ret_168 threshold với hysteresis

### Tunables

| Parameter | Values |
|---|---|
| `q_h4_rangepos_min` | {0.30, 0.45, 0.60} |
| `theta_h1_ret168_entry` | {-0.04, -0.01} |
| `theta_h1_ret168_hold` | {0.01, 0.04} |

### Fixed

- D1 flow window 12
- H4 rangepos window 168
- H1 pullback lookback 168

**Layers:** 3

### Viability gate

Config permissive nhất trên năm 2020:

- `q_h4_rangepos_min=0.30`
- `theta_h1_ret168_entry=-0.01`
- `theta_h1_ret168_hold=0.04`

Kết quả: **30 entries / năm, đạt ngưỡng.**

---

## Candidate 3

**ID:** `btcsd_20260318_c3_trade4h15m`

### Cơ chế

Khai thác continuation 4h trong trạng thái daily participation thuận lợi, rồi dùng burst activity ở 15m để timing entry.

**Điểm quan trọng:** đây không phải candidate 15m-primary. Directional engine vẫn nằm ở D1 + 4h; 15m chỉ là timing refinement.

**Timeframe:** 1d, 4h, 15m

### Feature formulas

Base model chỉ fit trên warmup hoặc train-window:

```
log1p(num_trades_t) = alpha + beta * log1p(volume_t) + eps_t
d1_trade_surprise168_t = eps_t - mean(eps_{t-167:t})
```

Execution features:

```
h4_rangepos168_t = (close_t - rolling_low_168) / (rolling_high_168 - rolling_low_168)
m15_relvol168_t = volume_t / mean(volume_{t-167:t})
```

### Signal logic

**Entry khi flat:**
- `d1_trade_surprise168_t > 0.0`
- `h4_rangepos168_t >= q_h4_rangepos_entry`
- `m15_relvol168_t >= rho_m15_relvol_min`

**Hold khi long:**
- `d1_trade_surprise168_t > 0.0`
- `h4_rangepos168_t >= q_h4_rangepos_hold`

**Exit:** còn lại

### Calibration

- alpha, beta fit chỉ từ dữ liệu train có sẵn
- daily trade-surprise dùng sign split 0.0
- 4h rangepos dùng hysteresis
- 15m timing dùng raw relative-volume threshold

### Tunables

| Parameter | Values |
|---|---|
| `q_h4_rangepos_entry` | {0.55, 0.65} |
| `q_h4_rangepos_hold` | {0.35, 0.45} |
| `rho_m15_relvol_min` | {1.10, 1.30, 1.50} |

### Fixed

- D1 trade-surprise window 168
- H4 rangepos window 168
- M15 relvol window 168

**Layers:** 3

### Viability gate

Config permissive nhất trên năm 2020:

- `q_h4_rangepos_entry=0.55`
- `q_h4_rangepos_hold=0.35`
- `rho_m15_relvol_min=1.10`

Kết quả: **26 entries / năm, đạt ngưỡng.**

**Lưu ý rủi ro:** Đây là candidate nhạy chi phí nhất trong 3 cái vì có layer timing 15m. Tôi giữ nó chỉ như timing-refined mechanism, không xem như default template.

---

## Config Matrix Summary

| Candidate | Configs |
|---|---|
| `btcsd_20260318_c1_av4h` | 6 |
| `btcsd_20260318_c2_flow1hpb` | 12 |
| `btcsd_20260318_c3_trade4h15m` | 12 |
| **Tổng** | **30** |

Config matrix machine-readable đã lưu ở `d1c_config_matrix.csv`.

## Hard Cap Compliance Check

| Check | Result |
|---|---|
| Candidates ≤ 3 | **PASS** |
| Layers mỗi candidate ≤ 3 | **PASS** (C1 = 2, C2 = 3, C3 = 3) |
| Tunables mỗi candidate ≤ 4 | **PASS** (cả 3 candidate đều có 3 tunables) |
| Configs mỗi candidate ≤ 20 | **PASS** |
| Tổng configs ≤ 60 | **PASS** (tổng = 30) |
| Binary sizing only | **PASS** |
| Không leverage / pyramiding / discretionary overrides | **PASS** |
| Chỉ dùng admitted data surface | **PASS** |
| Không dùng holdout / reserve_internal | **PASS** |
| Không lookahead từ bar chậm chưa đóng | **PASS** |
| Next-open fill, UTC alignment | **PASS** |

## Design Rationale

Tôi chọn đúng 3 mechanism này vì chúng bám chặt các block mạnh nhưng không đếm trùng edge:

- **C1** là continuation tối giản nhất: D1 anti-vol + 4h trend
- **C2** là recovery mechanism thật sự khác block với C1: D1 flow exhaustion + 1h pullback, có 4h trend làm permission
- **C3** là cơ chế duy nhất dùng timing block độc lập: D1 trade surprise + 15m activity, nhưng vẫn giữ engine ở 4h

**Những thứ tôi không nâng thành candidate riêng:**

- daily gaps: nhiễu
- calendar direction: yếu
- generic compression breakout: bị D1b bác bỏ
- standalone 1h fast continuation: quá redundant
- standalone 15m ret_42: cost-sensitive hơn, WFO risk cao hơn, và D1b4 cho thấy blind stacking từ 1h xuống 15m là chỗ dễ tự lừa mình nhất
- lower-TF flow variants: phần lớn chỉ là hậu duệ của cùng một slow flow-exhaustion block

---

Bước tiếp theo hợp lý là D1d chạy WFO đúng trên 30 config này, với calibration hoàn toàn causal theo từng fold.
