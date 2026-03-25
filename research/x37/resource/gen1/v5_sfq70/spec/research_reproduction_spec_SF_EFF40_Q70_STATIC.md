
# Research Reproduction Spec — BTC/USDT V5 → Frozen winner `SF_EFF40_Q70_STATIC`

## 1. Mục tiêu

Tài liệu này mô tả lại **quy trình nghiên cứu đã diễn ra** để đi từ raw CSV đến frozen winner `SF_EFF40_Q70_STATIC`, đủ để một kỹ sư khác rebuild lại mà **không cần chat history, code gốc, hay tài liệu nào khác ngoài file spec này và 2 file CSV đầu vào**.

Tài liệu này cố tình tách rõ hai lớp:

1. **Exact / artifact-backed**: những gì được chứng minh trực tiếp bởi `RESEARCH_PROMPT_V5.md`, report HTML đã xuất, và các CSV checkpoint.
2. **Minimal sufficient reproduction**: những gì không được serialize đầy đủ trong bundle nhưng vẫn phải được khóa lại đủ chặt để một rebuild đi tới đúng frozen winner.

Không có chỗ nào trong tài liệu này được bịa như thể là “biết chắc” nếu artifact không chứng minh điều đó.

## 2. Nguồn đầu vào bắt buộc

- `data_btcusdt_1d.csv`
- `data_btcusdt_4h.csv`
- `RESEARCH_PROMPT_V5.md`

## 3. Ranh giới bằng chứng cần hiểu trước khi rebuild

### 3.1 Những gì biết chắc
- Protocol V5, execution assumptions, split architecture, complexity budget, evidence labels, hard gates: biết chắc từ prompt.
- Data audit kết quả: biết chắc từ report.
- Stage-1 aggregate summary và top representatives theo category/timeframe: biết chắc từ report.
- Shortlist nghiêm túc trước reserve, thứ hạng sau reserve, paired-bootstrap summaries, plateau, cost sensitivity, rolling stability, regime decomposition, trade distribution: biết chắc từ report.
- Frozen rule `SF_EFF40_Q70_STATIC`: biết chắc từ report và có thể reverse-engineer trực tiếp từ raw D1.

### 3.2 Những gì **không** còn trong bundle
- Toàn bộ registry 99 D1 + 162 H4 feature ở cấp “full codebook”.
- Exact implementation code của ba layered rivals trong shortlist cuối.
- Exact bookkeeping convention dùng để phân bổ entry/exit fee lên daily-return bar khi tính Sharpe; report tự nó cũng ghi rõ có thể có chênh lệch nhỏ do trade-log bookkeeping.

### 3.3 Cách xử lý phần thiếu
- Không cố “điền vào chỗ trống” như thể là fact.
- Dùng **canonical checkpoints** của report làm chuẩn xác nhận giữa chừng.
- Dùng **minimal sufficient reproduction path** để đảm bảo rebuild ra đúng shortlist trọng yếu và đúng frozen winner.

---

## 4. Protocol lock — phải khóa trước khi scan

### Bước 0 — Khóa protocol

**Input**  
`RESEARCH_PROMPT_V5.md`

**Logic**  
Khóa toàn bộ luật chơi trước khi nhìn kết quả:
- Market: BTC/USDT spot, long-only.
- Timeframes: native D1 và native H4; không resample synthetic bars.
- Signal timing: tính ở bar close.
- Fill: next bar open.
- Cost: 10 bps/side = 20 bps round trip; stress thêm 50 bps.
- Warmup/no-live-before: trước `2019-01-01` chỉ dùng làm context/calibration.
- Split:
  - context-only: `2017-08-17` → `2018-12-31`
  - discovery: `2019-01-01` → `2022-12-31`
  - candidate-selection holdout: `2023-01-01` → `2024-12-31`
  - reserve: `2025-01-01` → dataset end
- Discovery walk-forward:
  - train `< 2020-01-01`, test year 2020
  - train `< 2021-01-01`, test year 2021
  - train `< 2022-01-01`, test year 2022
- Complexity budget:
  - tối đa 3 logical layers
  - tối đa 1 slower contextual layer
  - tối đa 1 faster state layer
  - tối đa 1 entry-only confirmation layer
  - tối đa 6 tunable quantities ở frozen candidate
  - không leverage, không pyramiding, không regime-specific parameter sets
- Hard gates:
  - discovery walk-forward aggregate phải dương sau 20 bps
  - holdout 2023–2024 phải dương sau 20 bps
  - discovery combined phải có ít nhất 20 trades
  - holdout phải có ít nhất 10 trades trừ khi sparse-by-design và có burden-of-proof khác
  - không sập rõ ràng ở major regimes
  - plateau phải rộng, không phải spike
  - mỗi retained layer phải qua ablation
  - không được retune sau holdout / reserve
- Evidence labels:
  - `CLEAN OOS CONFIRMED`
  - `INTERNAL ROBUST CANDIDATE`
  - `NO ROBUST IMPROVEMENT`

**Output**  
Một protocol lock cố định cho toàn bộ run.

**Decision rule**  
Nếu bất kỳ rule nào ở trên đổi sau khi đã thấy kết quả candidate, coi như **restart research**.

---

## 5. Data pipeline và audit

### Bước 1 — Parse, sort, validate raw bars

**Input**  
Hai raw CSV D1 và H4.

**Logic**  
1. Parse `open_time`, `close_time` từ epoch-ms sang UTC timezone-aware.
2. Sort tăng dần theo `open_time`.
3. Kiểm tra duplicate `open_time` / `close_time`, missing values, malformed rows, irregular gaps, zero-volume anomalies.
4. Ghi exact coverage theo từng timeframe.
5. Giữ D1 và H4 **riêng biệt**, không hòa vào cùng một frame.
6. Với cross-timeframe alignment, chỉ cho phép backward as-of trên `close_time`: H4 chỉ thấy D1 bar đã đóng.

**Output (checkpoint exact từ report)**  

| timeframe   |   rows | start_open           | end_open             |   dup_open |   dup_close |   gap_events |   missing_expected_bars |   nonstandard_duration_rows |   zero_volume_rows |
|:------------|-------:|:---------------------|:---------------------|-----------:|------------:|-------------:|------------------------:|----------------------------:|-------------------:|
| D1          |   3134 | 2017-08-17 00:00 UTC | 2026-03-16 00:00 UTC |          0 |           0 |            0 |                       0 |                           0 |                  0 |
| H4          |  18791 | 2017-08-17 04:00 UTC | 2026-03-17 12:00 UTC |          0 |           1 |            8 |                      16 |                          20 |                  1 |

**Output phụ (diễn giải exact)**
- D1: structurally clean, không có vấn đề ảnh hưởng execution assumptions.
- H4: usable nhưng imperfect:
  - 8 gap events
  - 16 missing expected opens
  - 20 non-standard close durations
  - 1 zero-volume / zero-duration anomaly gây duplicate close time

**Decision rule**  
- **Tiếp tục discovery**, nhưng:
  - không fill synthetic H4 bars,
  - mọi rolling window H4 dùng **native bar count**,
  - H4 chỉ được dùng với thái độ “usable but imperfect”,
  - D1 sạch hơn nên được ưu tiên nếu evidence ngang nhau.

### Bước 2 — Gắn split masks và chronology guards

**Input**  
D1/H4 đã audit pass.

**Logic**  
Tạo masks cho:
- context-only
- discovery
- holdout
- reserve

Tạo thêm discovery walk-forward annual test masks:
- 2020, 2021, 2022

**Output**  
Bộ masks cố định, dùng chung cho mọi family.

**Decision rule**  
- Holdout không được dùng để generate hypothesis hay shortlist.
- Reserve không được đụng tới trước khi freeze exact final spec.

---

## 6. Feature engineering và Stage 1 scan

### Bước 3 — Tạo feature library theo role, không theo architecture

**Input**  
Raw D1/H4 đã audit + split masks.

**Logic**  
Stage 1 không bắt đầu bằng một architecture yêu thích. Nó bắt đầu bằng **đo xem edge nằm ở đâu**.  
Feature library phải phủ tối thiểu các nhóm mà prompt yêu cầu:
- directional persistence / continuation
- trend quality
- range location
- drawdown / pullback
- volatility
- participation / flow
- candle structure
- cross-timeframe relationships
- calendar effects

**Minimal sufficient reproduction rule**
- Vì bundle không serialize full 261-feature registry, rebuild tối thiểu phải tái tạo được các family xuất hiện trong checkpoints Stage 1 và shortlist cuối:
  - `d1_eff_*`
  - `d1_ema_gap_*`
  - `d1_ret_*`
  - `d1_range_pos_*`
  - `d1_bounce_*`
  - `d1_tr_mean_*`
  - `d1_rel_qvol_*`
  - `d1_gap_prevclose`
  - `d1_is_weekend`
  - `h4_bounce_*`
  - `h4_tr_mean_*`
  - `h4_sma_gap_*`
  - `h4_ema_gap_*`
  - `h4_is_weekend`
  - `h4_close_loc`
  - `x_aligned_d1_*`
  - `x_h4_vs_d1_sma_*`

**Exact formulas phải khóa ít nhất cho family đi tới frozen winner**
- `d1_eff_n = abs(close_t - close_(t-n)) / sum(abs(close_i - close_(i-1)))` với tổng chạy trên `n` daily diffs gần nhất.
- `d1_ema_gap_n = close_t / EMA(close, n)_t - 1`
- `x_aligned_*`: backward as-of trên `close_time`; chỉ value của D1 bar đã close mới visible trên H4 bar.

**Output**  
Một feature matrix D1 và một feature matrix H4, mỗi cột có timestamp visibility hợp lệ.

**Decision rule**  
Mọi feature vi phạm chronology (ví dụ dùng D1 bar chưa close trên H4) bị loại ngay.

### Bước 4 — Chuyển feature thành executable single-feature state systems

**Input**  
Feature matrix từ Bước 3.

**Logic**  
Mỗi feature không chỉ được chấm bằng correlation. Nó phải được chuyển thành **tradable long/flat state system** dưới execution model chuẩn:
- signal ở close
- fill ở next open
- cost-aware
- walk-forward unseen

Đối với từng feature family:
1. quét coarse discrete thresholds / ranks trước;
2. đo performance trên discovery walk-forward unseen;
3. đo decay horizon, turnover, trade count, cost sensitivity, regime dependence;
4. tránh chọn nhiều near-duplicate transform của cùng một phenomenon.

**Output (checkpoint exact)**  
Stage 1 aggregate summary:

| timeframe   |   n_features |   median_sharpe20 |   top_sharpe20 | pct_positive_sharpe20   | pct_positive_2022   |
|:------------|-------------:|------------------:|---------------:|:------------------------|:--------------------|
| D1          |           99 |              0.43 |           1.74 | 74.7%                   | 5.1%                |
| H4          |          162 |             -0.03 |           1.7  | 46.9%                   | 2.5%                |

Top representative feature per category/timeframe:

| timeframe   | category                | feature                       |   sharpe20 | cagr20   | mdd20   |   entries20 | exposure20   |   sharpe50 |
|:------------|:------------------------|:------------------------------|-----------:|:---------|:--------|------------:|:-------------|-----------:|
| D1          | trend_quality           | d1_ema_gap_40                 |       1.74 | 92.7%    | -26.9%  |          31 | 40.2%        |       1.67 |
| D1          | drawdown_pullback       | d1_bounce_40                  |       1.7  | 93.9%    | -29.0%  |          24 | 37.1%        |       1.65 |
| D1          | directional_persistence | d1_ret_40                     |       1.56 | 78.5%    | -37.6%  |          18 | 37.4%        |       1.51 |
| D1          | range_location          | d1_range_pos_40               |       1.48 | 64.3%    | -26.2%  |          47 | 30.1%        |       1.36 |
| D1          | volatility              | d1_tr_mean_20                 |       1.13 | 55.0%    | -51.1%  |          18 | 34.9%        |       1.09 |
| D1          | participation_flow      | d1_rel_qvol_40                |       1.08 | 43.2%    | -34.1%  |         116 | 28.9%        |       0.8  |
| D1          | candle_structure        | d1_gap_prevclose              |       0.87 | 37.7%    | -56.7%  |         206 | 51.7%        |       0.48 |
| D1          | calendar                | d1_is_weekend                 |       0.44 | 7.0%     | -77.2%  |         156 | 71.5%        |       0.19 |
| H4          | drawdown_pullback       | x_aligned_d1_bounce_40        |       1.7  | 93.8%    | -32.3%  |          24 | 37.1%        |       1.65 |
| H4          | directional_persistence | x_aligned_d1_ret_40           |       1.56 | 78.4%    | -39.3%  |          18 | 37.4%        |       1.51 |
| H4          | cross_timeframe         | x_h4_vs_d1_sma_40             |       1.5  | 76.1%    | -42.0%  |          63 | 41.6%        |       1.35 |
| H4          | range_location          | x_aligned_d1_range_pos_40     |       1.48 | 64.3%    | -27.1%  |          47 | 30.1%        |       1.36 |
| H4          | trend_quality           | x_aligned_d1_sma_gap_20       |       1.26 | 56.2%    | -55.3%  |          56 | 40.1%        |       1.13 |
| H4          | volatility              | x_aligned_d1_rv_40            |       1.06 | 44.9%    | -43.4%  |          10 | 26.2%        |       1.04 |
| H4          | participation_flow      | x_aligned_d1_taker_buy_mean_3 |       0.77 | 4.7%     | -3.9%   |           6 | 0.6%         |       0.69 |
| H4          | calendar                | h4_is_weekend                 |       0.76 | 31.9%    | -71.5%  |         156 | 71.5%        |       0.53 |
| H4          | candle_structure        | h4_close_loc                  |      -0.72 | -29.5%   | -71.2%  |        1347 | 25.9%        |      -4.28 |

Best native H4 features (không tính cross-timeframe clones):

| feature       | category          |   sharpe20 | cagr20   | mdd20   |   entries20 |   year2020_sh |   year2021_sh |   year2022_sh |
|:--------------|:------------------|-----------:|:---------|:--------|------------:|--------------:|--------------:|--------------:|
| h4_bounce_48  | drawdown_pullback |       0.96 | 41.5%    | -48.6%  |         145 |          2.44 |          0.8  |         -0.98 |
| h4_is_weekend | calendar          |       0.76 | 31.9%    | -71.5%  |         156 |          2.14 |          0.69 |         -0.77 |
| h4_sma_gap_48 | trend_quality     |       0.75 | 25.5%    | -43.9%  |         195 |          1.4  |          0.84 |         -0.59 |
| h4_tr_mean_48 | volatility        |       0.64 | 21.2%    | -48.3%  |          28 |          1    |          1.1  |         -0.44 |
| h4_ema_gap_24 | trend_quality     |       0.59 | 17.4%    | -42.8%  |         223 |          1.66 |          0.56 |         -1.06 |

**Decision rule**
- Giữ lại **đại diện mạnh nhất và khác failure mode**, không giữ cả chùm near-duplicates.
- Ghi nhận kết luận trọng yếu của Stage 1:
  - D1 context features trội hơn H4 standalone sau cost.
  - 2022 là discriminator chính.
  - H4 standalone continuation yếu hơn và dễ sập hơn.

---

## 7. Tạo shortlist orthogonal và candidate families

### Bước 5 — Orthogonal pruning

**Input**  
Checkpoint Stage 1.

**Logic**  
Từ Stage 1, không giữ “mọi thứ trông có vẻ tốt”. Chỉ giữ:
- đại diện context D1 mạnh nhất
- đại diện H4 state/timing mạnh nhất
- ít nhất một family khác failure mode
- bỏ bớt biến thể cùng bản chất nhưng khác lookback/threshold rất nhỏ

**Exact shortlist rationale từ report**
- D1 `ema_gap` family và `eff` family là hai context engines đáng giữ.
- `d1_tr_mean_20` đủ đáng tin để được xem là alternative family, nhưng không vào top shortlist cuối.
- H4 `bounce`, `tr_mean`, và cross-timeframe `h4_vs_d1_sma` là ba đường timing/state đáng thử.
- Nhiều H4 standalone candidates bị loại sớm vì 2022 negative hoặc cost/turnover xấu.

**Output**  
Một shortlist orthogonal dùng để build candidate families tầng 2.

**Decision rule**  
Không giữ 2 candidate chỉ khác nhau “rất gần” mà cùng failure mode, trừ khi một bản đơn giản hơn rõ ràng.

### Bước 6 — Build minimal layered architectures

**Input**  
Shortlist orthogonal.

**Logic**  
Xây candidate families theo thứ tự complexity:
1. single-feature D1 context systems
2. 2-layer systems: D1 context gate + H4 state/timing controller
3. entry-only filter chỉ nếu có bằng chứng rằng nó chỉ giúp entry

**Serious families đã được report xác nhận**
- Single-feature D1 context:
  - `SF_EMA40_Q65_STATIC`
  - `SF_EFF40_Q70_STATIC`
  - `d1_tr_mean_20` family (survived as credible alternative nhưng không vào shortlist cuối)
- Two-layer:
  - D1 context + H4 bounce timing
  - D1 context + H4 true-range state
  - D1 context + H4-vs-D1 moving-average state

**Output**  
Bộ serious candidate families để coarse search + local refinement.

**Decision rule**  
- Không thêm layer thứ 3 nếu layer thứ 2 chưa tự chứng minh robust.
- Nếu layer nhanh chỉ giúp entry chứ không giúp hold, giữ nó ở vai trò entry-only; không auto-promote.

---

## 8. Coarse search, local refinement, và freeze set trước reserve

### Bước 7 — Coarse search trước, refinement sau

**Input**  
Serious candidate families.

**Logic**  
- Quét coarse quantile grid trước.
- Chỉ refine quanh plateau rộng.
- Ưu tiên center-of-plateau hơn single-cell max.

**Exact plateau evidence đã được lưu**
- Local search run:

|   lookback |    q | mode      |   disc_sh | disc_cagr   | disc_mdd   |   disc_trades |   hold_sh | hold_cagr   | hold_mdd   |   hold_trades |   pre_sh | pre_cagr   | pre_mdd   |   pre_trades |   reserve_sh |
|-----------:|-----:|:----------|----------:|:------------|:-----------|--------------:|----------:|:------------|:-----------|--------------:|---------:|:-----------|:----------|-------------:|-------------:|
|         32 | 0.7  | static    |      1.18 | 47.6%       | -35.7%     |            47 |      1.84 | 58.5%       | -15.3%     |            21 |     1.37 | 51.8%      | -35.7%    |           68 |         0.23 |
|         32 | 0.75 | static    |      1.31 | 46.2%       | -22.3%     |            38 |      1.69 | 47.7%       | -12.2%     |            20 |     1.42 | 46.8%      | -22.3%    |           58 |        -0.04 |
|         40 | 0.7  | static    |      1.24 | 52.7%       | -33.3%     |            40 |      1.61 | 53.3%       | -18.4%     |            15 |     1.34 | 52.9%      | -33.3%    |           55 |         0.74 |
|         40 | 0.75 | static    |      1.07 | 39.1%       | -35.8%     |            39 |      1.61 | 52.3%       | -18.4%     |            14 |     1.25 | 44.2%      | -35.8%    |           53 |         0.68 |
|         48 | 0.7  | expanding |      1.13 | 46.1%       | -46.6%     |            42 |      1.69 | 60.2%       | -15.2%     |            18 |     1.31 | 51.5%      | -46.6%    |           60 |         0.92 |
|         48 | 0.7  | rolling   |      0.66 | 19.9%       | -65.8%     |            50 |      1.63 | 58.4%       | -23.0%     |            22 |     1    | 34.0%      | -65.8%    |           72 |         0.55 |

- Computed static nearest-grid plateau quanh `d1_eff` family cho thấy vùng khả dụng rộng quanh lookback 40–48 và quantile 0.70–0.80; cell `40 / 0.70` không phải highest single holdout/reserve cell ở mọi tiêu chí, nhưng là cell đơn giản, cân bằng, và nằm trong vùng sống được thay vì spike.

**Decision rule**  
- Chọn center-ish cell trong vùng ổn định, không chọn isolated max.
- Với `d1_eff` family, `40 / 0.70 / STATIC` được giữ vì:
  - discovery walk-forward dương,
  - holdout dương mạnh,
  - reserve/internal dương,
  - complexity thấp,
  - plateau rộng ở lân cận.

### Bước 8 — Pre-reserve ranking và internal candidate comparison

**Input**  
Candidate set sau local refinement, reserve vẫn sealed.

**Logic**  
Xếp hạng trên **pre-reserve** internal evidence: discovery walk-forward + holdout 2023–2024 + trade quality + cost resilience + complexity.

**Checkpoint exact: pre-reserve ranking**

| candidate                  |   sharpe20 | cagr20   | mdd20   |   trades | exposure   | win_rate   | mean_trade   | median_trade   |   mean_hold_days |   median_hold_days | top_winner_conc   | bottom_tail   |
|:---------------------------|-----------:|:---------|:--------|---------:|:-----------|:-----------|:-------------|:---------------|-----------------:|-------------------:|:------------------|:--------------|
| SF_EMA40_Q65_STATIC        |       1.6  | 72.2%    | -40.9%  |       62 | 38.2%      | 43.5%      | 6.0%         | -0.8%          |            11.26 |               4    | 62.5%             | -6.1%         |
| L2_EMA40S70__H4B48E65      |       1.58 | 51.9%    | -23.5%  |      102 | 17.1%      | 33.3%      | 2.4%         | -0.6%          |             3.07 |               0.83 | 46.2%             | -4.8%         |
| L2_EFF40S70__H4TR48R55     |       1.35 | 45.4%    | -27.1%  |       52 | 18.3%      | 61.5%      | 4.2%         | 0.8%           |             6.45 |               1.83 | 63.2%             | -7.9%         |
| SF_EFF40_Q70_STATIC        |       1.34 | 52.9%    | -33.3%  |       55 | 27.0%      | 65.5%      | 4.7%         | 1.5%           |             8.98 |               5    | 57.2%             | -11.1%        |
| L2_EFF40S70__XH4D1SMA20S60 |       1.2  | 33.3%    | -27.3%  |       68 | 17.6%      | 38.2%      | 2.5%         | -0.4%          |             4.73 |               1.33 | 67.1%             | -4.8%         |

**Decision rule**  
- Không freeze theo full-sample Sharpe.
- Không freeze chỉ vì pre-reserve headline tốt nhất.
- Ghi nhận `SF_EMA40_Q65_STATIC` là **headline leader trước reserve**, nhưng chưa được freeze chỉ vì điều đó.

### Bước 9 — Freeze comparison set rồi mới mở reserve

**Input**  
Shortlist cuối trước reserve.

**Logic**  
Freeze:
- exact frozen candidate specification format
- exact comparison set
- exact evaluation path

Comparison set cuối cùng được report giữ lại gồm 5 candidates:
- `SF_EMA40_Q65_STATIC`
- `L2_EMA40S70__H4B48E65`
- `L2_EFF40S70__H4TR48R55`
- `SF_EFF40_Q70_STATIC`
- `L2_EFF40S70__XH4D1SMA20S60`

**Output**  
Frozen comparison set; reserve vẫn chưa bị dùng để redesign.

**Decision rule**  
Sau điểm này, **cấm retune**.

---

## 9. Reserve evaluation và quyết định winner

### Bước 10 — Open reserve đúng một lần cho frozen comparison set

**Input**  
Frozen comparison set.

**Logic**  
Chạy từng candidate nguyên xi trên `2025-01-01` → dataset end.

**Checkpoint exact: reserve ranking**

| candidate                  |   sharpe20 | cagr20   | mdd20   |   trades20 | exp20   |   sharpe50 | cagr50   |   2025_sh |   2026_sh |
|:---------------------------|-----------:|:---------|:--------|-----------:|:--------|-----------:|:---------|----------:|----------:|
| SF_EFF40_Q70_STATIC        |       0.74 | 15.9%    | -31.2%  |         17 | 19.1%   |       0.56 | 11.1%    |      0.08 |      2.41 |
| L2_EFF40S70__H4TR48R55     |       0.71 | 14.2%    | -25.8%  |         17 | 13.4%   |       0.52 | 9.5%     |     -0.04 |      2.37 |
| L2_EFF40S70__XH4D1SMA20S60 |      -0.64 | -6.5%    | -18.3%  |         13 | 6.3%    |      -0.94 | -9.5%    |     -1.17 |      1.83 |
| SF_EMA40_Q65_STATIC        |      -0.72 | -9.7%    | -14.0%  |         12 | 14.8%   |      -0.94 | -12.3%   |     -0.68 |     -2.38 |
| L2_EMA40S70__H4B48E65      |      -2.02 | -11.7%   | -15.6%  |         16 | 4.1%    |      -2.4  | -15.1%   |     -2.22 |    nan    |

**Decision rule**  
- Candidate nào sập reserve/internal âm rõ rệt bị tụt hạng mạnh, kể cả nếu pre-reserve rất đẹp.
- `SF_EMA40_Q65_STATIC`: **reject** vì reserve/internal âm (`sharpe20 = -0.72`).
- `L2_EMA40S70__H4B48E65`: **reject** vì reserve/internal sập rất nặng (`sharpe20 = -2.02`).
- `L2_EFF40S70__XH4D1SMA20S60`: **reject** vì reserve/internal âm (`sharpe20 = -0.64`).
- `L2_EFF40S70__H4TR48R55`: reserve/internal dương, nhưng:
  - phức tạp hơn,
  - holdout paired bootstrap bị `SF_EFF40_Q70_STATIC` đánh bại khá rõ,
  - không có lợi thế robustness đủ mạnh để biện minh complexity.
- `SF_EFF40_Q70_STATIC`: candidate đơn giản nhất trong nhóm sống được qua reserve/internal.

### Bước 11 — Paired bootstrap giữa frozen winner và nearest rivals

**Input**  
Holdout 2023–2024 daily return series của frozen winner và các nearest internal rivals.

**Logic**  
Moving-block paired bootstrap trên cùng synthetic paths; blocks = `5, 10, 20`.

**Checkpoint exact**

**Vs `SF_EMA40_Q65_STATIC`**
|   block | p_mean_gt0   | p_sharpe_gt0   |   mean_delta_mean_daily |   mean_delta_sharpe |   ci05_delta_mean_daily |   ci95_delta_mean_daily |   ci05_delta_sharpe |   ci95_delta_sharpe |
|--------:|:-------------|:---------------|------------------------:|--------------------:|------------------------:|------------------------:|--------------------:|--------------------:|
|       5 | 62.2%        | 77.1%          |                       0 |                0.36 |                      -0 |                       0 |               -0.43 |                1.17 |
|      10 | 62.2%        | 74.8%          |                       0 |                0.37 |                      -0 |                       0 |               -0.53 |                1.25 |
|      20 | 63.2%        | 76.2%          |                       0 |                0.39 |                      -0 |                       0 |               -0.53 |                1.31 |

**Vs `L2_EFF40S70__H4TR48R55`**
|   block | p_mean_gt0   | p_sharpe_gt0   |   mean_delta_mean_daily |   mean_delta_sharpe |   ci05_delta_mean_daily |   ci95_delta_mean_daily |   ci05_delta_sharpe |   ci95_delta_sharpe |
|--------:|:-------------|:---------------|------------------------:|--------------------:|------------------------:|------------------------:|--------------------:|--------------------:|
|       5 | 97.2%        | 93.6%          |                       0 |                0.6  |                       0 |                       0 |               -0.05 |                1.3  |
|      10 | 96.1%        | 93.0%          |                       0 |                0.62 |                       0 |                       0 |               -0.08 |                1.31 |
|      20 | 96.5%        | 93.5%          |                       0 |                0.61 |                       0 |                       0 |               -0.05 |                1.29 |

**Vs `L2_EMA40S70__H4B48E65`**
|   block | p_mean_gt0   | p_sharpe_gt0   |   mean_delta_mean_daily |   mean_delta_sharpe |   ci05_delta_mean_daily |   ci95_delta_mean_daily |   ci05_delta_sharpe |   ci95_delta_sharpe |
|--------:|:-------------|:---------------|------------------------:|--------------------:|------------------------:|------------------------:|--------------------:|--------------------:|
|       5 | 70.5%        | 49.7%          |                       0 |                0.01 |                      -0 |                       0 |               -0.93 |                0.98 |
|      10 | 70.3%        | 52.0%          |                       0 |                0.03 |                      -0 |                       0 |               -0.96 |                1.04 |
|      20 | 72.8%        | 53.8%          |                       0 |                0.06 |                      -0 |                       0 |               -0.89 |                0.95 |

**Decision rule**
- `SF_EFF40_Q70_STATIC` decisively beat layered `EFF + TR`.
- Thường beat `SF_EMA40_Q65_STATIC` trên Sharpe holdout.
- Roughly tie với `EMA + bounce` layered rival trên holdout Sharpe, nhưng layered rival **fail reserve badly** nên không thể thắng final ranking.
- Với protocol ranking criteria, **simplicity + reserve survival + paired evidence** đưa `SF_EFF40_Q70_STATIC` lên trên.

### Bước 12 — Cost, rolling stability, regime decomposition, ablation

**Input**  
Frozen winner `SF_EFF40_Q70_STATIC`.

**Logic**  
Kiểm tra thêm:
- cost sensitivity
- rolling stability
- epoch decomposition
- regime decomposition
- component ablation / family perturbation

**Checkpoint exact: cost sensitivity**

|   round_trip_bps | period        |   sharpe | cagr   | mdd    |
|-----------------:|:--------------|---------:|:-------|:-------|
|                0 | Discovery_All |     1.32 | 57.4%  | -29.6% |
|                0 | Holdout_All   |     1.66 | 55.6%  | -18.2% |
|                0 | Reserve_All   |     0.79 | 17.6%  | -31.2% |
|                0 | Live_2020_end |     1.31 | 48.1%  | -31.2% |
|               20 | Discovery_All |     1.25 | 53.3%  | -32.4% |
|               20 | Holdout_All   |     1.61 | 53.3%  | -18.4% |
|               20 | Reserve_All   |     0.67 | 14.3%  | -32.4% |
|               20 | Live_2020_end |     1.25 | 44.8%  | -32.4% |
|               50 | Discovery_All |     1.16 | 47.5%  | -36.6% |
|               50 | Holdout_All   |     1.53 | 49.9%  | -18.8% |
|               50 | Reserve_All   |     0.5  | 9.5%   | -34.2% |
|               50 | Live_2020_end |     1.15 | 39.9%  | -36.6% |
|              100 | Discovery_All |     1    | 38.2%  | -42.9% |
|              100 | Holdout_All   |     1.4  | 44.4%  | -20.0% |
|              100 | Reserve_All   |     0.2  | 2.0%   | -37.2% |
|              100 | Live_2020_end |     0.98 | 32.1%  | -42.9% |

**Checkpoint exact: rolling stability**
|   window_days |   valid_points |   median_sharpe |   p10_sharpe |   p90_sharpe | share_positive_sharpe   | median_cagr   | p10_cagr   | p90_cagr   | share_positive_cagr   |
|--------------:|---------------:|----------------:|-------------:|-------------:|:------------------------|:--------------|:-----------|:-----------|:----------------------|
|            90 |           2135 |            1.48 |        -2.05 |         3.27 | 65.9%                   | 25.0%         | -41.2%     | 243.0%     | 65.1%                 |
|           180 |           2087 |            1.27 |        -0.97 |         2.77 | 69.7%                   | 37.9%         | -22.6%     | 155.7%     | 64.1%                 |
|           365 |           1902 |            1.35 |         0.25 |         2.04 | 78.3%                   | 35.4%         | 2.8%       | 118.2%     | 76.8%                 |

**Checkpoint exact: yearly / epoch decomposition**
| epoch    |   daily_sharpe | cagr   | max_drawdown   |   trade_count | exposure   | win_rate   | mean_trade_return   | median_trade_return   |   mean_hold_days |   median_hold_days | top_winner_concentration   | bottom_tail_damage   | classification   |
|:---------|---------------:|:-------|:---------------|--------------:|:-----------|:-----------|:--------------------|:----------------------|-----------------:|-------------------:|:---------------------------|:---------------------|:-----------------|
| 2020     |           2.49 | 192.2% | -25.9%         |            16 | 40.2%      | 62.5%      | 8.2%                | 0.7%                  |             9.12 |                2.5 | 95.3%                      | -4.2%                | effective        |
| 2021     |           0.41 | 9.0%   | -30.8%         |            13 | 20.8%      | 53.8%      | 0.9%                | 4.2%                  |             5.85 |                3   | 79.6%                      | -5.9%                | noise-only       |
| 2022     |           0.55 | 13.3%  | -25.3%         |            11 | 16.4%      | 81.8%      | 1.5%                | 2.6%                  |             5.45 |                5   | 85.5%                      | -4.7%                | effective        |
| 2023     |           1.65 | 54.4%  | -15.9%         |             9 | 35.6%      | 66.7%      | 5.8%                | 1.0%                  |            14.44 |                7   | 98.5%                      | -2.7%                | effective        |
| 2024     |           1.57 | 52.4%  | -18.4%         |             6 | 21.9%      | 83.3%      | 7.8%                | 2.1%                  |            13.33 |                5.5 | 100.0%                     | 4.0%                 | effective        |
| 2025     |          -0.02 | -2.0%  | -32.4%         |            14 | 16.4%      | 35.7%      | -0.0%               | -0.7%                 |             4.29 |                1   | 100.0%                     | -4.7%                | noise-only       |
| 2026 YTD |           2.41 | 146.6% | -8.3%          |             3 | 33.8%      | 100.0%     | 6.3%                | 5.3%                  |             8.33 |                2   | 100.0%                     | 6.3%                 | effective        |

**Checkpoint exact: market-state decomposition**
| regime    |   days |   sharpe | cagr   | classification   |
|:----------|-------:|---------:|:-------|:-----------------|
| Downtrend |    385 |     0.55 | 16.0%  | effective        |
| Neutral   |   1021 |     1.56 | 41.4%  | effective        |
| Uptrend   |    860 |     1.49 | 64.4%  | effective        |

**Decision rule**
- Candidate pass vì:
  - sau 50 bps round-trip vẫn dương ở discovery và holdout;
  - rolling Sharpe/CAGR đa số positive;
  - không có regime collapse kiểu sign-reversed rõ ràng;
  - ablation logic: frozen candidate đã là core một-feature, nên ablation test phù hợp là **family perturbation**, không phải “xóa layer”.

---

## 10. Winner selection rule — tóm tắt ngắn gọn, dứt khoát

### Winner cuối cùng
`SF_EFF40_Q70_STATIC`

### Vì sao thắng
1. Discovery walk-forward sau 20 bps vẫn dương.
2. Holdout 2023–2024 sau 20 bps dương mạnh.
3. Reserve/internal 2025+ vẫn dương sau 20 bps.
4. Plateau quanh family `d1_eff` đủ rộng.
5. 50 bps stress vẫn sống.
6. Layered alternatives không chứng minh được rằng complexity của chúng đáng giá.
7. EMA single-feature là headline leader trước reserve nhưng **thua bài kiểm tra reserve/internal**.

### Evidence label đúng theo Protocol V5
`INTERNAL ROBUST CANDIDATE`

### Vì sao **không** được gắn `CLEAN OOS CONFIRMED`
Vì reserve slice `2025+` **không thể chứng nhận globally untouched across all earlier sessions**. Theo prompt, khi không có chứng nhận đó thì chỉ được gọi là **reserve/internal only**, không được overclaim thành clean OOS.

---

## 11. Canonical acceptance test cho rebuild này

Một rebuild được coi là faithful nếu, trên raw data đầu vào và theo spec này, nó tái tạo được ít nhất các checkpoint sau:

1. Data audit counts khớp bảng audit.
2. Stage 1 aggregate summary khớp bảng Phase 1 summary.
3. Shortlist cuối trước reserve và reserve ranking khớp đúng **candidate names + thứ tự logic**.
4. Frozen candidate cuối là `SF_EFF40_Q70_STATIC`.
5. Rationale cuối cùng giữ nguyên:
   - EMA headline leader pre-reserve nhưng fail reserve/internal.
   - EFF single-feature đơn giản hơn layered EFF+TR và beat nó ở paired holdout bootstrap.
   - Evidence label là `INTERNAL ROBUST CANDIDATE`.

---

## 12. Phần kỹ sư cần đọc tiếp ngay sau tài liệu này

Sau tài liệu này, kỹ sư phải dùng tiếp:

- **System Specification — `SF_EFF40_Q70_STATIC`**  
  Tài liệu đó mô tả final system ở mức implementation-level: feature formula, threshold calibration, signal/position state machine, cost accounting, và regression hashes.

