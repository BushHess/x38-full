# D1d3 WFO Aggregate & Summary
Annualization basis: 365-day daily-return compounding.
## Completeness Check
- `d1d_wfo_results.csv`: expected 952 rows, found 952; missing 0, extra 0, duplicate keys 0.
- `d1d_wfo_daily_returns.csv`: expected 68 config×cost series, each with 1277 dates from 2020-01-01 to 2023-06-30; all 68 passed exact-date coverage; duplicate keys 0.

## Ablation Results

### btcsd_20260318_c1_av4h (full first config `cfg_001`, Calmar_50bps=1.066)
- ABLATION_FAIL: removing `d1_permission` raises Calmar from 1.066 to 1.645; layer degrades Calmar by 0.579.
- ABLATION_PASS: removing `h4_execution` lowers Calmar from 1.066 to 0.356; layer contributes +0.710 Calmar.

### btcsd_20260318_c2_flow1hpb (full first config `cfg_007`, Calmar_50bps=-0.338)
- ABLATION_FAIL: removing `d1_flow_permission` raises Calmar from -0.338 to -0.313; layer degrades Calmar by 0.025.
- ABLATION_FAIL: removing `h1_execution` raises Calmar from -0.338 to 0.242; layer degrades Calmar by 0.580.
- ABLATION_FAIL: removing `h4_context` raises Calmar from -0.338 to -0.298; layer degrades Calmar by 0.040.

### btcsd_20260318_c3_trade4h15m (full first config `cfg_019`, Calmar_50bps=0.859)
- ABLATION_FAIL: removing `d1_participation_permission` raises Calmar from 0.859 to 1.255; layer degrades Calmar by 0.397.
- ABLATION_PASS: removing `h4_context` lowers Calmar from 0.859 to 0.304; layer contributes +0.555 Calmar.
- ABLATION_FAIL: removing `m15_timing` raises Calmar from 0.859 to 0.931; layer degrades Calmar by 0.072.

## Top 10 Base Configs by Aggregate Calmar_50bps
| Rank | Config | Candidate | Calmar_50bps | Agg CAGR | Agg MDD | Agg Sharpe | Entries | Avg Exposure | Ablation Flag |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `cfg_001` | `btcsd_20260318_c1_av4h` | 1.066 | 0.230 | 0.216 | 0.976 | 22 | 0.183 | ABLATION_FAIL |
| 2 | `cfg_025` | `btcsd_20260318_c3_trade4h15m` | 1.040 | 0.397 | 0.382 | 1.011 | 65 | 0.371 | ABLATION_FAIL |
| 3 | `cfg_026` | `btcsd_20260318_c3_trade4h15m` | 1.004 | 0.378 | 0.376 | 0.978 | 65 | 0.368 | ABLATION_FAIL |
| 4 | `cfg_003` | `btcsd_20260318_c1_av4h` | 0.978 | 0.239 | 0.245 | 0.938 | 26 | 0.228 | ABLATION_FAIL |
| 5 | `cfg_027` | `btcsd_20260318_c3_trade4h15m` | 0.928 | 0.355 | 0.383 | 0.941 | 65 | 0.365 | ABLATION_FAIL |
| 6 | `cfg_022` | `btcsd_20260318_c3_trade4h15m` | 0.886 | 0.354 | 0.399 | 0.945 | 83 | 0.374 | ABLATION_FAIL |
| 7 | `cfg_023` | `btcsd_20260318_c3_trade4h15m` | 0.866 | 0.336 | 0.388 | 0.915 | 83 | 0.371 | ABLATION_FAIL |
| 8 | `cfg_019` | `btcsd_20260318_c3_trade4h15m` | 0.859 | 0.358 | 0.417 | 0.932 | 76 | 0.394 | ABLATION_FAIL |
| 9 | `cfg_020` | `btcsd_20260318_c3_trade4h15m` | 0.841 | 0.342 | 0.407 | 0.906 | 76 | 0.391 | ABLATION_FAIL |
| 10 | `cfg_021` | `btcsd_20260318_c3_trade4h15m` | 0.798 | 0.340 | 0.426 | 0.906 | 75 | 0.386 | ABLATION_FAIL |
