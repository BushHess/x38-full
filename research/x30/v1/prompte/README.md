# X30: Fractional Actuator — Chuỗi Phase Nghiên Cứu

## Tổng quan

Chuỗi 4 phase nghiên cứu, mỗi phase chạy trong **một phiên riêng biệt**.
Kết quả từ phiên trước được truyền qua **artifact files** (CSV, JSON) mà phiên
sau đọc — không phụ thuộc vào context window.

### Câu hỏi lớn

X29 pilot gợi ý (chưa chứng minh) rằng:
- Churn score có thể mang thông tin về trail-stop outcomes (Q1→Q4 monotonic
  trong full-sample, nhưng chưa test OOS/temporal stability)
- Partial exit (giữ 50% position) có thể thắng Base trong full-sample ở nhiều
  cost levels — nhưng bootstrap VCBB fail (P=37.2%, tệ hơn coin flip)
- MDD giảm ~12pp — chưa rõ từ timing (alpha) hay chỉ vì giảm exposure (trivial)

**Vấn đề cốt lõi**: Pilot results có selection bias (chỉ nghiên cứu vì trông
tốt). Nghiên cứu này phải XÁC MINH HOẶC BÁC BỎ bằng evidence nghiêm ngặt.
Null hypothesis: partial actuator KHÔNG cải thiện Base tại 25 bps.

### Cấu trúc chuỗi

| Phase | Tên | Câu hỏi chính | Gate | STOP nếu fail? |
|-------|-----|---------------|------|----------------|
| 1 | Signal Anatomy | Signal OOS reliable? | G0a: temporal ≥2/3 (P3 bắt buộc), G0b: OOS AUC>0.65 | YES → toàn bộ chuỗi dừng |
| 2 | Actuator Design | Best actuator? | G1: plateau ≥3 values, ΔSh>0.03, ≥7/9 costs | YES → dừng |
| 3 | Validation | Statistical proof? | G2: WFO ≥75%, G3: bootstrap ≥55% | WFO<50%→REJECT, boot<45%→REJECT |
| 4 | Synthesis | Final verdict | — | — |

### Quy tắc chuyển tiếp

1. Mỗi phase tạo artifact (CSV/JSON) trong `/var/www/trading-bots/btc-spot-dev/research/x30/`
2. Phase sau ĐỌC artifact của phase trước — không cần nhớ context
3. Nếu một gate FAIL, phiên đó dừng và ghi lý do vào `x30_results.json`
4. Phase 4 chạy SAU KHI phase 3 hoàn thành (cần kết quả validation)

### Thư mục làm việc

```
/var/www/trading-bots/btc-spot-dev/research/x30/
├── code/
│   ├── x30_signal.py      (phase 1)
│   ├── x30_actuator.py    (phase 2)
│   ├── x30_validate.py    (phase 3)
│   └── x30_synthesis.py   (phase 4)
├── tables/                   (CSV artifacts, truyền giữa phases)
├── figures/
├── x30_report.md          (phase 4 viết)
└── x30_results.json       (phase 4 viết)
```

### Tài nguyên tham khảo (mỗi phase chọn những gì cần)

```
Data:         /var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv
Strategy:     /var/www/trading-bots/btc-spot-dev/strategies/vtrend_e5_ema21_d1/strategy.py
Monitor:      /var/www/trading-bots/btc-spot-dev/monitoring/regime_monitor.py
Churn X14D:   /var/www/trading-bots/btc-spot-dev/research/x14/benchmark.py
Churn X18:    /var/www/trading-bots/btc-spot-dev/research/x18/benchmark.py
Bootstrap:    /var/www/trading-bots/btc-spot-dev/research/lib/vcbb.py
X29 code:  /var/www/trading-bots/btc-spot-dev/research/x29/code/x29_signal_diagnostic.py
X29 report:/var/www/trading-bots/btc-spot-dev/research/x29/x29_report.md
Context:      /var/www/trading-bots/btc-spot-dev/research/x30/prompte/context.md
```
