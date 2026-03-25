# D1d3 Report — WFO Summary & Ablation

## Completeness Check

**`d1d_wfo_results.csv`:**

- expected rows: 952
  - base configs: 30 × 14 × 2 = 840
  - ablations: 8 × 14 × 1 = 112
- found: 952
- missing keys: 0
- extra keys: 0
- duplicate `(config_id, fold, cost_bps_rt)` keys: 0

**`d1d_wfo_daily_returns.csv`:**

- expected config×cost series: 68
  - base: 30 × 2 = 60
  - ablations: 8 × 1 = 8
- all 68/68 series have exact date coverage:
  - start: 2020-01-01
  - end: 2023-06-30
  - days per series: 1277
- duplicate `(config_id, candidate_id, cost_bps_rt, date)` keys: 0

Aggregate metrics were annualized on a 365-day basis from the chained daily-return path.

## Ablation Results

Reference config for each candidate is its first config at 50 bps RT.

### `btcsd_20260318_c1_av4h` — full cfg_001, Calmar_50bps = 1.066

| Layer | Result | Detail |
|---|---|---|
| d1_permission | **ABLATION_FAIL** | Removing the layer raises Calmar from 1.066 to 1.645. Layer degrades Calmar by 0.579. |
| h4_execution | **ABLATION_PASS** | Removing the layer drops Calmar from 1.066 to 0.356. Layer contributes +0.710 Calmar. |

### `btcsd_20260318_c2_flow1hpb` — full cfg_007, Calmar_50bps = -0.338

| Layer | Result | Detail |
|---|---|---|
| d1_flow_permission | **ABLATION_FAIL** | Removing the layer raises Calmar from -0.338 to -0.313. Layer degrades Calmar by 0.025. |
| h4_context | **ABLATION_FAIL** | Removing the layer raises Calmar from -0.338 to -0.298. Layer degrades Calmar by 0.040. |
| h1_execution | **ABLATION_FAIL** | Removing the layer raises Calmar from -0.338 to 0.242. Layer degrades Calmar by 0.580. |

### `btcsd_20260318_c3_trade4h15m` — full cfg_019, Calmar_50bps = 0.859

| Layer | Result | Detail |
|---|---|---|
| d1_participation_permission | **ABLATION_FAIL** | Removing the layer raises Calmar from 0.859 to 1.255. Layer degrades Calmar by 0.397. |
| h4_context | **ABLATION_PASS** | Removing the layer drops Calmar from 0.859 to 0.304. Layer contributes +0.555 Calmar. |
| m15_timing | **ABLATION_FAIL** | Removing the layer raises Calmar from 0.859 to 0.931. Layer degrades Calmar by 0.072. |

**Result:** all 3 candidates are flagged for review in D1e because each has at least one ABLATION_FAIL.

## WFO Results Summary

Top 10 below is limited to base configs from `d1c_config_matrix.csv`.
Ablation variants are included in the aggregate CSV as diagnostics, but excluded from this ranking.

| Rank | Config | Candidate | Calmar_50bps | Agg CAGR | Agg MDD | Agg Sharpe | Entries | Avg Exposure | Flag |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cfg_001 | `btcsd_20260318_c1_av4h` | 1.066 | 22.99% | 21.57% | 0.976 | 22 | 18.28% | ABLATION_FAIL |
| 2 | cfg_025 | `btcsd_20260318_c3_trade4h15m` | 1.040 | 39.73% | 38.22% | 1.011 | 65 | 37.08% | ABLATION_FAIL |
| 3 | cfg_026 | `btcsd_20260318_c3_trade4h15m` | 1.004 | 37.77% | 37.63% | 0.978 | 65 | 36.80% | ABLATION_FAIL |
| 4 | cfg_003 | `btcsd_20260318_c1_av4h` | 0.978 | 23.95% | 24.49% | 0.938 | 26 | 22.76% | ABLATION_FAIL |
| 5 | cfg_027 | `btcsd_20260318_c3_trade4h15m` | 0.928 | 35.52% | 38.26% | 0.941 | 65 | 36.51% | ABLATION_FAIL |
| 6 | cfg_022 | `btcsd_20260318_c3_trade4h15m` | 0.886 | 35.38% | 39.92% | 0.945 | 83 | 37.41% | ABLATION_FAIL |
| 7 | cfg_023 | `btcsd_20260318_c3_trade4h15m` | 0.866 | 33.62% | 38.83% | 0.915 | 83 | 37.12% | ABLATION_FAIL |
| 8 | cfg_019 | `btcsd_20260318_c3_trade4h15m` | 0.859 | 35.82% | 41.72% | 0.932 | 76 | 39.43% | ABLATION_FAIL |
| 9 | cfg_020 | `btcsd_20260318_c3_trade4h15m` | 0.841 | 34.20% | 40.65% | 0.906 | 76 | 39.14% | ABLATION_FAIL |
| 10 | cfg_021 | `btcsd_20260318_c3_trade4h15m` | 0.798 | 33.98% | 42.56% | 0.906 | 75 | 38.63% | ABLATION_FAIL |

**Một điểm đáng chú ý:** nếu xếp hạng cả ablation diagnostics, thì hai biến thể ablation sẽ đứng trên cfg_001. Đó là dấu hiệu rõ ràng cho thấy D1e không được bỏ qua phần review layer contribution.

## Files Saved

- `d1d_wfo_aggregate.csv`
- `d1d3_wfo_summary.md`
