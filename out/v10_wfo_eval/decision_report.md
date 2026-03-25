# Decision Report

**Generated:** 2026-02-22T16:12:36.983876+00:00
**Git:** c74c650
**Scenarios:** base, harsh, smart

## 1. Worst-Case Across Scenarios

| Candidate | Tag | Min Score | Min CAGR% | Max MDD% | Fee Drag%/yr | Trades |
|-----------|-----|-----------|-----------|----------|--------------|--------|
| baseline_legacy | **PROMOTE** | 83.48 | 34.35 | 33.88 | 3.90 | 103 |
| v9_like | **HOLD** | 77.45 | 33.05 | 36.30 | 3.89 | 101 |

## 2. Regime Analysis (TOPPING + SHOCK)

| Candidate | TOPPING Return% | TOPPING MDD% | SHOCK Return% | SHOCK MDD% |
|-----------|-----------------|--------------|---------------|------------|
| baseline_legacy | -21.99 | 26.35 | -18.37 | 29.18 |
| v9_like | -17.49 | 26.08 | -17.10 | 31.77 |

## 3. Top 5 Drawdown Episodes

### baseline_legacy

| # | DD% | Peak Date | Trough Date | Recovery Date | Days to Recovery |
|---|-----|-----------|-------------|---------------|------------------|
| 1 | 33.88 | 2024-03-04T23:59:59Z | 2024-08-07T19:59:59Z | 2024-11-13T15:59:59Z | 253.70 |
| 2 | 33.31 | 2021-11-09T03:59:59Z | 2023-10-12T15:59:59Z | 2024-02-11T03:59:59Z | 824.00 |
| 3 | 29.52 | 2019-06-26T19:59:59Z | 2020-07-05T15:59:59Z | 2020-11-05T15:59:59Z | 497.80 |
| 4 | 27.50 | 2025-01-20T11:59:59Z | 2025-04-03T19:59:59Z | 2025-07-14T07:59:59Z | 174.80 |
| 5 | 25.03 | 2021-05-03T07:59:59Z | 2021-09-28T23:59:59Z | 2021-10-10T07:59:59Z | 160.00 |

### v9_like

| # | DD% | Peak Date | Trough Date | Recovery Date | Days to Recovery |
|---|-----|-----------|-------------|---------------|------------------|
| 1 | 36.30 | 2024-03-04T23:59:59Z | 2024-08-07T19:59:59Z | 2024-12-05T03:59:59Z | 275.20 |
| 2 | 32.74 | 2019-06-26T19:59:59Z | 2020-07-05T15:59:59Z | 2020-11-09T11:59:59Z | 501.70 |
| 3 | 31.31 | 2021-11-09T03:59:59Z | 2023-06-15T15:59:59Z | 2023-12-04T19:59:59Z | 755.70 |
| 4 | 30.86 | 2025-01-20T11:59:59Z | 2025-03-31T03:59:59Z | ongoing | N/A |
| 5 | 24.62 | 2021-05-03T07:59:59Z | 2021-09-28T23:59:59Z | 2021-10-06T19:59:59Z | 156.50 |

## 4. Decision

**Selected:** `baseline_legacy`

- **baseline_legacy** [PROMOTE]
  - harsh score >= baseline
  - TOPPING return >= baseline
  - turnover 25.8x <= 1.2 * baseline 25.8x
- **v9_like** [HOLD]
  - harsh score 77.45 < baseline 83.5
