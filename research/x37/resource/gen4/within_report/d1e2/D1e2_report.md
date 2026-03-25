# D1e2 Report — Holdout & Reserve Evaluation

## Holdout Results

**Holdout window:** 2023-07-01 → 2024-09-30

| Candidate | Config | Cost RT | CAGR | Sharpe | MDD | Entries | Exits | Final state | Exposure | Mean daily | Holdout 50bps constraints |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `btcsd_20260318_c1_av4h` | cfg_001 | 20 | 18.25% | 1.220 | 6.19% | 3 | 3 | flat | 10.77% | 0.0488% | n/a |
| `btcsd_20260318_c1_av4h` | cfg_001 | 50 | 17.40% | 1.169 | 6.75% | 3 | 3 | flat | 10.77% | 0.0468% | FAIL: entries/year, exposure |
| `btcsd_20260318_c3_trade4h15m` | cfg_025 | 20 | 44.82% | 1.332 | 27.77% | 34 | 33 | long | 44.42% | 0.1149% | n/a |
| `btcsd_20260318_c3_trade4h15m` | cfg_025 | 50 | 33.65% | 1.075 | 29.70% | 34 | 33 | long | 44.42% | 0.0930% | PASS |

**Holdout hard-constraint readout at 50 bps:**

- **`btcsd_20260318_c1_av4h`:** CAGR>0 pass, MDD<=0.45 pass, entries/year in [6,80] **fail**, exposure in [0.15,0.90] **fail**
- **`btcsd_20260318_c3_trade4h15m`:** all four holdout hard constraints **pass**

## Reserve Results

**Reserve window:** 2024-10-01 → 2026-03-18

| Candidate | Config | Cost RT | CAGR | Sharpe | MDD | Entries | Exits | Final state | Exposure | Mean daily |
|---|---|---|---|---|---|---|---|---|---|---|
| `btcsd_20260318_c1_av4h` | cfg_001 | 20 | 15.40% | 0.759 | 18.64% | 11 | 11 | flat | 26.16% | 0.0458% |
| `btcsd_20260318_c1_av4h` | cfg_001 | 50 | 12.82% | 0.656 | 21.17% | 11 | 11 | flat | 26.16% | 0.0396% |
| `btcsd_20260318_c3_trade4h15m` | cfg_025 | 20 | -4.42% | -0.052 | 37.81% | 38 | 38 | flat | 31.96% | -0.0036% |
| `btcsd_20260318_c3_trade4h15m` | cfg_025 | 50 | -11.60% | -0.355 | 43.94% | 38 | 38 | flat | 31.96% | -0.0249% |

Reserve là internal evidence only, không phải clean forward evidence.

**Lưu ý về terminal state:**

- `d1e_terminal_states.json` phản ánh terminal state của reserve segment theo đúng setup prompt: warmup bằng toàn bộ dữ liệu đến 2024-09-30, rồi chạy segment 2024-10-01 → snapshot end
- terminal state cuối reserve của cả 2 candidate đều là **flat**

## Files Saved

- `d1e_holdout_results.csv`
- `d1e_reserve_results.csv`
- `d1e_holdout_daily_returns.csv`
- `d1e_reserve_daily_returns.csv`
- `d1e_terminal_states.json`
