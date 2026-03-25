# Decision Report

**Generated:** 2026-02-23T21:25:01.546511+00:00
**Git:** c74c650
**Scenarios:** base, harsh, smart

## 1. Worst-Case Across Scenarios

| Candidate | Tag | Min Score | Min CAGR% | Max MDD% | Fee Drag%/yr | Trades |
|-----------|-----|-----------|-----------|----------|--------------|--------|
| v10_baseline | **PROMOTE** | 88.94 | 37.26 | 36.28 | 3.94 | 100 |
| v11_disabled | **PROMOTE** | 88.94 | 37.26 | 36.28 | 3.94 | 100 |

## 2. Regime Analysis (TOPPING + SHOCK)

| Candidate | TOPPING Return% | TOPPING MDD% | SHOCK Return% | SHOCK MDD% |
|-----------|-----------------|--------------|---------------|------------|
| v10_baseline | -17.49 | 26.08 | -14.10 | 27.11 |
| v11_disabled | -17.49 | 26.08 | -14.10 | 27.11 |

## 3. Top 5 Drawdown Episodes

### v10_baseline

| # | DD% | Peak Date | Trough Date | Recovery Date | Days to Recovery |
|---|-----|-----------|-------------|---------------|------------------|
| 1 | 34.78 | 2024-05-20T23:59:59Z | 2024-08-07T19:59:59Z | 2024-11-22T03:59:59Z | 185.20 |
| 2 | 33.22 | 2019-06-26T19:59:59Z | 2020-07-05T15:59:59Z | 2020-11-12T07:59:59Z | 504.50 |
| 3 | 31.31 | 2021-11-09T03:59:59Z | 2023-06-15T15:59:59Z | 2023-12-04T19:59:59Z | 755.70 |
| 4 | 30.86 | 2025-01-20T11:59:59Z | 2025-03-31T03:59:59Z | ongoing | N/A |
| 5 | 24.62 | 2021-05-03T07:59:59Z | 2021-09-28T23:59:59Z | 2021-10-06T19:59:59Z | 156.50 |

### v11_disabled

| # | DD% | Peak Date | Trough Date | Recovery Date | Days to Recovery |
|---|-----|-----------|-------------|---------------|------------------|
| 1 | 34.78 | 2024-05-20T23:59:59Z | 2024-08-07T19:59:59Z | 2024-11-22T03:59:59Z | 185.20 |
| 2 | 33.22 | 2019-06-26T19:59:59Z | 2020-07-05T15:59:59Z | 2020-11-12T07:59:59Z | 504.50 |
| 3 | 31.31 | 2021-11-09T03:59:59Z | 2023-06-15T15:59:59Z | 2023-12-04T19:59:59Z | 755.70 |
| 4 | 30.86 | 2025-01-20T11:59:59Z | 2025-03-31T03:59:59Z | ongoing | N/A |
| 5 | 24.62 | 2021-05-03T07:59:59Z | 2021-09-28T23:59:59Z | 2021-10-06T19:59:59Z | 156.50 |

## 4. Decision

**Selected:** `v10_baseline`

- **v10_baseline** [PROMOTE]
  - harsh score >= baseline
  - TOPPING return >= baseline
  - turnover 26.1x <= 1.2 * baseline 26.1x
- **v11_disabled** [PROMOTE]
  - harsh score >= baseline
  - TOPPING return >= baseline
  - turnover 26.1x <= 1.2 * baseline 26.1x
