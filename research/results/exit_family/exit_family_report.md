# Exit Family Study — Final Report

## Part 1 — Executive Summary


### slow_period = 120

- **E1** vs E0: dSharpe=+0.0058 (P=51.8%), dMDD=+1.67pp (P=61.2%), dCAGR=-1.73pp (P=42.8%), dMAR=+0.0152 (P=51.5%)
- **E2** vs E0: dSharpe=+0.0100 (P=52.9%), dMDD=+2.14pp (P=63.7%), dCAGR=-1.85pp (P=43.2%), dMAR=+0.0270 (P=53.4%)
- **E3** vs E0: dSharpe=-0.0064 (P=45.5%), dMDD=+9.90pp (P=100.0%), dCAGR=-15.26pp (P=2.1%), dMAR=-0.0993 (P=28.5%)
- **E4** vs E0: dSharpe=-0.0942 (P=28.9%), dMDD=+7.16pp (P=84.1%), dCAGR=-18.18pp (P=4.5%), dMAR=-0.2465 (P=25.3%)
- **E5** vs E0: dSharpe=+0.0825 (P=87.6%), dMDD=+2.42pp (P=77.0%), dCAGR=+4.48pp (P=84.6%), dMAR=+0.1774 (P=85.2%)

### slow_period = 144

- **E1** vs E0: dSharpe=-0.0646 (P=33.7%), dMDD=-0.00pp (P=52.0%), dCAGR=-5.90pp (P=26.8%), dMAR=-0.1219 (P=36.2%)
- **E2** vs E0: dSharpe=+0.0170 (P=54.8%), dMDD=+2.97pp (P=67.6%), dCAGR=-1.43pp (P=45.2%), dMAR=+0.0706 (P=57.2%)
- **E3** vs E0: dSharpe=-0.0388 (P=22.8%), dMDD=+9.25pp (P=100.0%), dCAGR=-17.52pp (P=0.9%), dMAR=-0.1623 (P=16.4%)
- **E4** vs E0: dSharpe=-0.1864 (P=14.8%), dMDD=+4.62pp (P=73.6%), dCAGR=-22.77pp (P=1.9%), dMAR=-0.4126 (P=13.0%)
- **E5** vs E0: dSharpe=+0.0971 (P=91.6%), dMDD=+2.65pp (P=79.9%), dCAGR=+5.65pp (P=89.3%), dMAR=+0.2219 (P=89.6%)

## Part 2 — Implementation Audit

### Data & Assumptions
- Data: `bars_btcusdt_2016_now_h1_4h_1d.csv` — BTC/USDT H4 bars, 2019-01-01 to 2026-02-20
- Warmup: 365 days before 2019-01-01
- Cost: harsh scenario (50 bps RT = 25.0 bps/side)
- Fill: signal at bar close, fill at previous close (proxy for next-bar open)
- Initial capital: $10,000
- Position sizing: fully invested (100% NAV in BTC at entry)
- Single-market confirmation only (no ETH/altcoin data available)

### CRITICAL DISCLOSURE: Trail Anchor
The proposal specified E0 uses `peak_high_since_entry` as trail anchor.
The actual VTREND code (strategy.py:111) uses `peak_close_since_entry`:
```python
self._peak_price = max(self._peak_price, price)  # price = bar.close
```
Per rule 1.1 ('exact current reference implementation'), ALL branches
use peak_close as anchor. E5's 'close anchor' isolation is moot.
E5 tests ONLY the robust ATR effect, not the anchor change.

### Unchanged from Baseline
- Entry: EMA_fast > EMA_slow AND VDO > 0
- EMA fast = slow // 4 (standard alpha=2/(p+1))
- ATR: Wilder period=14
- VDO: EMA(VDR, 12) - EMA(VDR, 28), threshold=0.0
- Position sizing: 100% NAV at entry, flat at exit
- No regime gates, no PE, no chop filters

## Part 3 — Exact Branch Definitions

### E0
Baseline: trail_mult=3.0, anchor=peak_close, ATR=standard, no partial.

### E1
Threshold ratchet: MFE_R<1→3.0, [1,2)→2.0, >=2→1.5. No partial.

### E2
Dynamic trail: trail_mult = clip(3.0 - 0.75*MFE_R, 1.5, 3.0). No partial.

### E3
Partial only: sell 1/3 at MFE_R>=1.0, residual uses E0 exit (trail=3.0).

### E4
Partial + ratchet: sell 1/3 at MFE_R>=1.0, residual uses E1 ratchet.

### E5
Robust ATR: capped TR at Q90(100 bars), Wilder EMA(20). Anchor=peak_close. No partial.


## Part 3B — Actual Outcomes (Final Equity & Net Profit)

These are the outcomes a trader would actually receive — final equity from $10k.

**When proxy metrics (per-trade realized_R, fold-median Sharpe) conflict with actual outcomes (final NAV, total profit), the actual outcome takes priority.**


### slow_period = 120

| Branch | Final NAV | vs E0 | Full CAGR | OOS Mult | Trades | Cost | Net Profit |
|--------|-----------|-------|-----------|----------|--------|------|------------|
| E0 | $138,023 | baseline | +38.1% | 20.52x | 211 | $66,627 | $128,023 |
| E1 | $154,235 (+11.7%) | +11.7% | +40.0% | 19.00x | 315 | $116,223 | $144,235 |
| E2 | $162,066 (+17.4%) | +17.4% | +40.8% | 18.92x | 325 | $128,009 | $152,066 |
| E3 | $77,806 (-43.6%) | -43.6% | +28.7% | 10.30x | 211 | $43,296 | $67,806 |
| E4 | $75,639 (-45.2%) | -45.2% | +28.2% | 8.79x | 315 | $68,505 | $65,639 |
| E5 | $181,479 (+31.5%) | +31.5% | +42.8% | 25.09x | 225 | $90,222 | $171,479 |

### slow_period = 144

| Branch | Final NAV | vs E0 | Full CAGR | OOS Mult | Trades | Cost | Net Profit |
|--------|-----------|-------|-----------|----------|--------|------|------------|
| E0 | $140,257 | baseline | +38.3% | 23.78x | 199 | $62,002 | $130,257 |
| E1 | $128,404 (-8.5%) | -8.5% | +36.8% | 18.14x | 301 | $95,025 | $118,404 |
| E2 | $154,654 (+10.3%) | +10.3% | +40.0% | 22.41x | 307 | $110,696 | $144,654 |
| E3 | $68,653 (-51.1%) | -51.1% | +26.7% | 10.82x | 199 | $35,876 | $58,653 |
| E4 | $59,207 (-57.8%) | -57.8% | +24.4% | 8.16x | 301 | $54,241 | $49,207 |
| E5 | $193,345 (+37.9%) | +37.9% | +43.9% | 30.47x | 212 | $88,052 | $183,345 |

## Part 4 — OOS Portfolio Results (Fold-Level Proxy Metrics)


### slow_period = 120

#### Per-Fold Table

| Fold | E0 MAR | E1 MAR | E2 MAR | E3 MAR | E4 MAR | E5 MAR |
|------|------|------|------|------|------|------|
| 0 | 2.3839 | 0.7807 | 1.2229 | 3.5168 | 0.3624 | 2.8150 |
| 1 | 1.6699 | -0.7889 | -0.8687 | 1.6601 | -0.7337 | 1.8926 |
| 2 | 6.9389 | 10.2238 | 9.9483 | 4.8167 | 8.7520 | 7.8168 |
| 3 | 2.0185 | 6.6541 | 8.1500 | 1.9181 | 5.1928 | 2.7546 |
| 4 | -1.0001 | 0.7053 | 0.7053 | -0.7602 | 0.9846 | -0.8372 |
| 5 | -1.7483 | -1.7623 | -1.7772 | -1.7943 | -1.5934 | -1.7581 |
| 6 | -1.4683 | -1.2023 | -1.3179 | -1.2997 | -1.1268 | -1.4359 |
| 7 | 0.1710 | 0.0933 | 0.1529 | 0.0900 | -0.0196 | -0.2197 |
| 8 | 0.5348 | 0.1142 | 0.1147 | 0.6802 | 0.2043 | 0.2930 |
| 9 | -1.1926 | -1.3327 | -1.3813 | -1.0978 | -1.3373 | -0.8135 |
| 10 | 5.6062 | 4.9867 | 4.7604 | 6.1777 | 5.5771 | 9.5366 |
| 11 | 8.9386 | 18.8875 | 14.5950 | 7.8649 | 15.5763 | 14.2217 |
| 12 | 0.4643 | 1.4254 | 0.8421 | 0.4106 | 0.8159 | 1.1365 |
| 13 | -0.7946 | -0.9395 | -1.1417 | -0.4785 | -0.8384 | -0.8979 |
| 14 | 7.7226 | 10.0944 | 9.8015 | 5.8882 | 7.0424 | 7.7633 |
| 15 | 5.7844 | 5.9045 | 5.7379 | 5.8828 | 5.1865 | 5.6509 |
| 16 | 1.1541 | -0.1510 | -0.4635 | 1.3330 | 0.1797 | 1.3366 |
| 17 | 3.7828 | 1.7548 | 1.3942 | 3.8662 | 0.6546 | 3.0624 |
| 18 | -0.7244 | -1.0708 | -0.9291 | -0.8925 | -1.3321 | -0.6169 |
| 19 | -1.6161 | -1.3676 | -1.0087 | -1.7953 | -1.6689 | -1.4416 |

#### Aggregated OOS (median across folds)

| Branch | med CAGR | med Sharpe | med MDD | med MAR | med Sortino |
|--------|----------|------------|---------|---------|-------------|
| E0 | +16.37% | 0.6499 | 17.33% | 0.8444 | 0.5761 |
| E1 | +4.95% | 0.3639 | 15.96% | 0.4098 | 0.2474 |
| E2 | +5.14% | 0.3654 | 15.93% | 0.4291 | 0.2649 |
| E3 | +15.65% | 0.7388 | 14.27% | 1.0066 | 0.6228 |
| E4 | +5.92% | 0.3916 | 13.18% | 0.2833 | 0.3061 |
| E5 | +21.44% | 0.7370 | 16.93% | 1.2366 | 0.5841 |

### slow_period = 144

#### Per-Fold Table

| Fold | E0 MAR | E1 MAR | E2 MAR | E3 MAR | E4 MAR | E5 MAR |
|------|------|------|------|------|------|------|
| 0 | 1.6034 | 0.8910 | 1.6951 | 1.4264 | 0.0914 | 2.6024 |
| 1 | -0.2080 | -1.2512 | -1.2780 | -0.3347 | -1.1551 | -0.0690 |
| 2 | 4.8906 | 6.4306 | 6.4326 | 4.1366 | 6.0529 | 5.6255 |
| 3 | 1.2278 | 2.9480 | 4.4971 | 0.5807 | 1.7429 | 1.7379 |
| 4 | -1.3070 | -0.3306 | -0.0866 | -1.3260 | -0.4879 | -1.2522 |
| 5 | -1.7579 | -1.5493 | -1.7605 | -1.5553 | -1.2193 | -1.7674 |
| 6 | -1.3702 | -1.0516 | -1.1610 | -1.0337 | -0.8250 | -1.3811 |
| 7 | 1.3207 | 1.4766 | 1.5041 | 1.2908 | 1.3267 | 0.5845 |
| 8 | 1.9608 | 0.8891 | 1.4339 | 1.8190 | 0.6141 | 1.4830 |
| 9 | -1.2822 | -1.4023 | -1.3900 | -1.3277 | -1.4543 | -1.1160 |
| 10 | 4.5708 | 4.3114 | 4.3622 | 4.7737 | 4.4850 | 7.3251 |
| 11 | 11.8273 | 25.0439 | 18.6253 | 10.4714 | 20.9272 | 18.3892 |
| 12 | 2.0845 | 3.7526 | 2.7576 | 2.1896 | 2.8459 | 3.6159 |
| 13 | -0.5311 | -0.9685 | -0.8897 | -0.5554 | -1.0152 | -0.6040 |
| 14 | 6.3278 | 7.7902 | 8.7906 | 4.6583 | 5.6254 | 5.7030 |
| 15 | 4.5424 | 3.4152 | 4.5068 | 4.7571 | 3.2471 | 4.3384 |
| 16 | 0.8747 | -0.4789 | -0.4576 | 1.0224 | -0.3932 | 0.9781 |
| 17 | 3.2750 | 1.6254 | 1.2652 | 3.3111 | 0.4182 | 2.5755 |
| 18 | -0.4414 | -0.9872 | -0.8100 | -0.7142 | -1.2906 | -0.3459 |
| 19 | -1.4877 | -1.1831 | -0.5654 | -1.7104 | -1.5658 | -1.2121 |

#### Aggregated OOS (median across folds)

| Branch | med CAGR | med Sharpe | med MDD | med MAR | med Sortino |
|--------|----------|------------|---------|---------|-------------|
| E0 | +31.72% | 0.9717 | 17.99% | 1.2743 | 0.8024 |
| E1 | +20.14% | 0.7145 | 18.12% | 0.8901 | 0.6620 |
| E2 | +21.53% | 0.7765 | 17.46% | 1.3496 | 0.7564 |
| E3 | +18.51% | 0.8034 | 14.06% | 1.1566 | 0.7064 |
| E4 | +4.56% | 0.3629 | 15.05% | 0.2548 | 0.3195 |
| E5 | +22.01% | 0.7887 | 18.07% | 1.2305 | 0.6946 |

## Part 5 — Matched-Trade Exit Analysis


### slow_period = 120

| Branch | med realized_R | med giveback_R | med giveback_ratio | med bars_held |
|--------|----------------|----------------|--------------------|---------------|
| E0 | -0.5716 | 3.8680 | 1.2877 | 29.0 |
| E1 | -0.3464 | 2.8582 | 1.1381 | 17.0 |
| E2 | -0.3987 | 2.8631 | 1.1735 | 17.0 |
| E3 | -0.2551 | 3.4891 | 1.0973 | 29.0 |
| E4 | -0.0556 | 2.8215 | 1.0276 | 17.0 |
| E5 | -0.4688 | 3.7797 | 1.2522 | 25.0 |

### slow_period = 144

| Branch | med realized_R | med giveback_R | med giveback_ratio | med bars_held |
|--------|----------------|----------------|--------------------|---------------|
| E0 | -0.6010 | 3.7636 | 1.2862 | 29.5 |
| E1 | -0.3563 | 2.8217 | 1.1692 | 17.5 |
| E2 | -0.3563 | 2.8217 | 1.1692 | 17.5 |
| E3 | -0.2481 | 3.4878 | 1.0868 | 29.5 |
| E4 | -0.0940 | 2.8383 | 1.0533 | 17.5 |
| E5 | -0.5687 | 3.6921 | 1.2711 | 26.0 |

#### Matched-Trade Bootstrap (sp=120)

| Branch | d_realized_R | P(better) | d_giveback | P(lower) |
|--------|-------------|-----------|------------|----------|
| E1 | -0.7873 | 0.7% | +0.1455 | 100.0% |
| E2 | -0.9098 | 0.3% | +0.1503 | 99.6% |
| E3 | -0.5501 | 0.0% | +0.1340 | 100.0% |
| E4 | -1.0844 | 0.1% | +0.2364 | 100.0% |
| E5 | -0.0298 | 42.1% | +0.1075 | 100.0% |

#### Matched-Trade Bootstrap (sp=144)

| Branch | d_realized_R | P(better) | d_giveback | P(lower) |
|--------|-------------|-----------|------------|----------|
| E1 | -0.8706 | 0.5% | +0.1004 | 99.9% |
| E2 | -0.8604 | 0.6% | +0.1684 | 100.0% |
| E3 | -0.5955 | 0.0% | +0.1170 | 100.0% |
| E4 | -1.1835 | 0.0% | +0.1891 | 100.0% |
| E5 | -0.0794 | 26.7% | +0.0831 | 100.0% |

## Part 6 — Partial-Exit Evaluation


### slow_period = 120

**E3**: 162/211 trades triggered partial (76.8%)
  - Extra cost from partials: $5694.02
  - Top 10% PnL contribution: E3=203.0% vs E0=229.4%

**E4**: 240/315 trades triggered partial (76.2%)
  - Extra cost from partials: $8815.12
  - Top 10% PnL contribution: E4=224.5% vs E0=229.4%


### slow_period = 144

**E3**: 148/199 trades triggered partial (74.4%)
  - Extra cost from partials: $4522.36
  - Top 10% PnL contribution: E3=189.3% vs E0=203.3%

**E4**: 228/301 trades triggered partial (75.7%)
  - Extra cost from partials: $6865.04
  - Top 10% PnL contribution: E4=239.7% vs E0=203.3%


## Part 7 — Robust ATR / Close-Anchor Evaluation

E5 uses robust ATR (capped TR at Q90, Wilder EMA period=20).
Since baseline already uses peak_close anchor, E5 isolates ONLY the robust ATR effect.

### sp=120: E5 vs E0
- dSharpe=+0.0825 (P=87.6%)
- dMDD=+2.42pp (P=77.0%)
- dMAR=+0.1774 (P=85.2%)

### sp=144: E5 vs E0
- dSharpe=+0.0971 (P=91.6%)
- dMDD=+2.65pp (P=79.9%)
- dMAR=+0.2219 (P=89.6%)

## Part 8 — Context Stratification


### slow_period = 120

| Branch | ER30 Bin | Trades | WinRate | Expectancy | med GB ratio |
|--------|----------|--------|---------|------------|--------------|
| E0 | <0.10 | 81 | 35.8% | $105.12 | 1.3136 |
| E0 | 0.10-0.15 | 23 | 47.8% | $1785.03 | 1.0331 |
| E0 | 0.15-0.20 | 24 | 16.7% | $19.59 | 1.4144 |
| E0 | 0.20-0.25 | 19 | 31.6% | $1127.30 | 1.5864 |
| E0 | >=0.25 | 64 | 42.2% | $883.81 | 1.1843 |
| E1 | <0.10 | 112 | 44.6% | $630.59 | 1.1313 |
| E1 | 0.10-0.15 | 38 | 42.1% | $479.69 | 1.1352 |
| E1 | 0.15-0.20 | 36 | 33.3% | $-144.38 | 1.4169 |
| E1 | 0.20-0.25 | 23 | 52.2% | $1056.02 | 0.9790 |
| E1 | >=0.25 | 106 | 44.3% | $342.36 | 1.1355 |
| E2 | <0.10 | 117 | 44.4% | $799.69 | 1.1328 |
| E2 | 0.10-0.15 | 39 | 41.0% | $436.21 | 1.5453 |
| E2 | 0.15-0.20 | 37 | 35.1% | $-22.08 | 1.3685 |
| E2 | 0.20-0.25 | 24 | 50.0% | $956.96 | 1.0720 |
| E2 | >=0.25 | 108 | 41.7% | $179.08 | 1.1808 |
| E3 | <0.10 | 81 | 39.5% | $84.43 | 1.1710 |
| E3 | 0.10-0.15 | 23 | 56.5% | $796.06 | 0.9138 |
| E3 | 0.15-0.20 | 24 | 20.8% | $22.10 | 1.2004 |
| E3 | 0.20-0.25 | 19 | 36.8% | $603.12 | 1.3040 |
| E3 | >=0.25 | 64 | 48.4% | $479.18 | 1.0349 |
| E4 | <0.10 | 112 | 52.7% | $235.10 | 0.9474 |
| E4 | 0.10-0.15 | 38 | 47.4% | $215.74 | 1.0743 |
| E4 | 0.15-0.20 | 36 | 44.4% | $6.98 | 1.2390 |
| E4 | 0.20-0.25 | 23 | 56.5% | $557.21 | 0.8204 |
| E4 | >=0.25 | 106 | 50.0% | $170.21 | 1.0117 |
| E5 | <0.10 | 81 | 39.5% | $208.66 | 1.2522 |
| E5 | 0.10-0.15 | 28 | 42.9% | $1712.26 | 1.1216 |
| E5 | 0.15-0.20 | 27 | 18.5% | $-144.65 | 1.4075 |
| E5 | 0.20-0.25 | 18 | 38.9% | $1261.76 | 1.5231 |
| E5 | >=0.25 | 71 | 43.7% | $1237.01 | 1.0947 |

### slow_period = 144

| Branch | ER30 Bin | Trades | WinRate | Expectancy | med GB ratio |
|--------|----------|--------|---------|------------|--------------|
| E0 | <0.10 | 66 | 36.4% | $416.94 | 1.3090 |
| E0 | 0.10-0.15 | 21 | 47.6% | $599.69 | 1.2051 |
| E0 | 0.15-0.20 | 22 | 27.3% | $360.68 | 1.4390 |
| E0 | 0.20-0.25 | 24 | 25.0% | $713.83 | 1.5276 |
| E0 | >=0.25 | 66 | 43.9% | $986.05 | 1.1225 |
| E1 | <0.10 | 99 | 47.5% | $659.99 | 1.0649 |
| E1 | 0.10-0.15 | 35 | 42.9% | $425.48 | 1.2804 |
| E1 | 0.15-0.20 | 29 | 37.9% | $-139.30 | 1.4264 |
| E1 | 0.20-0.25 | 30 | 46.7% | $558.25 | 1.1762 |
| E1 | >=0.25 | 108 | 46.3% | $235.79 | 1.0969 |
| E2 | <0.10 | 104 | 47.1% | $803.48 | 1.0709 |
| E2 | 0.10-0.15 | 34 | 38.2% | $429.17 | 1.7486 |
| E2 | 0.15-0.20 | 31 | 38.7% | $96.84 | 1.0656 |
| E2 | 0.20-0.25 | 30 | 46.7% | $492.53 | 1.1762 |
| E2 | >=0.25 | 108 | 45.4% | $265.95 | 1.0969 |
| E3 | <0.10 | 66 | 37.9% | $180.08 | 1.1585 |
| E3 | 0.10-0.15 | 21 | 47.6% | $174.01 | 1.1175 |
| E3 | 0.15-0.20 | 22 | 31.8% | $219.35 | 1.2004 |
| E3 | 0.20-0.25 | 24 | 33.3% | $424.79 | 1.4206 |
| E3 | >=0.25 | 66 | 50.0% | $425.65 | 1.0139 |
| E4 | <0.10 | 99 | 54.5% | $228.18 | 0.9381 |
| E4 | 0.10-0.15 | 35 | 45.7% | $143.17 | 1.0748 |
| E4 | 0.15-0.20 | 29 | 48.3% | $21.48 | 1.1592 |
| E4 | 0.20-0.25 | 30 | 53.3% | $305.94 | 0.9400 |
| E4 | >=0.25 | 108 | 50.0% | $109.30 | 0.9910 |
| E5 | <0.10 | 68 | 39.7% | $604.30 | 1.2711 |
| E5 | 0.10-0.15 | 25 | 44.0% | $332.05 | 1.4414 |
| E5 | 0.15-0.20 | 23 | 26.1% | $-352.14 | 1.4213 |
| E5 | 0.20-0.25 | 23 | 30.4% | $796.10 | 1.4598 |
| E5 | >=0.25 | 73 | 46.6% | $1695.07 | 1.0816 |

## Part 9 — Bootstrap and Significance


### slow_period = 120

#### Raw P-values (fraction of 10k resamples where branch beats E0)

| Branch | P(Sharpe+) | P(MDD-) | P(CAGR+) | P(MAR+) |
|--------|------------|---------|----------|---------|
| E1 | 51.8% | 61.2% | 42.8% | 51.5% |
| E2 | 52.9% | 63.7% | 43.2% | 53.4% |
| E3 | 45.5% | 100.0% | 2.1% | 28.5% |
| E4 | 28.9% | 84.1% | 4.5% | 25.3% |
| E5 | 87.6% | 77.0% | 84.6% | 85.2% |

#### Holm-Adjusted P-values

| Branch | Raw best P | Holm-adjusted |
|--------|-----------|---------------|
| E1 | 61.2% | 27.3% |
| E2 | 63.7% | 27.3% |
| E3 | 100.0% | 99.8% |
| E4 | 84.1% | 50.6% |
| E5 | 87.6% | 50.6% |

### slow_period = 144

#### Raw P-values (fraction of 10k resamples where branch beats E0)

| Branch | P(Sharpe+) | P(MDD-) | P(CAGR+) | P(MAR+) |
|--------|------------|---------|----------|---------|
| E1 | 33.7% | 52.0% | 26.8% | 36.2% |
| E2 | 54.8% | 67.6% | 45.2% | 57.2% |
| E3 | 22.8% | 100.0% | 0.9% | 16.4% |
| E4 | 14.8% | 73.6% | 1.9% | 13.0% |
| E5 | 91.6% | 79.9% | 89.3% | 89.6% |

#### Holm-Adjusted P-values

| Branch | Raw best P | Holm-adjusted |
|--------|-----------|---------------|
| E1 | 52.0% | 20.8% |
| E2 | 67.6% | 20.8% |
| E3 | 100.0% | 99.9% |
| E4 | 73.6% | 20.8% |
| E5 | 91.6% | 66.4% |

## Part 10 — Local Sensitivity


### E3

| Variant | CAGR | Sharpe | MDD | MAR | Trades |
|---------|------|--------|-----|-----|--------|
| partial_trigger=0.75 | +36.19% | 1.1812 | 31.10% | 1.1636 | 189 |
| partial_trigger=1.25 | +37.59% | 1.1845 | 34.51% | 1.0893 | 189 |
| partial_frac=0.25 | +42.31% | 1.2361 | 34.82% | 1.2151 | 189 |
| partial_frac=0.50 | +31.05% | 1.2020 | 29.63% | 1.0482 | 189 |
| partial_trigger=0.75 | +39.21% | 1.2441 | 29.52% | 1.3282 | 180 |
| partial_trigger=1.25 | +38.59% | 1.1973 | 32.01% | 1.2056 | 180 |
| partial_frac=0.25 | +43.79% | 1.2576 | 33.13% | 1.3218 | 180 |
| partial_frac=0.50 | +31.02% | 1.1871 | 27.16% | 1.1422 | 180 |

### E2

| Variant | CAGR | Sharpe | MDD | MAR | Trades |
|---------|------|--------|-----|-----|--------|
| e2_slope=0.50 | +50.39% | 1.2299 | 37.75% | 1.3350 | 280 |
| e2_slope=1.00 | +54.65% | 1.3186 | 33.68% | 1.6225 | 305 |
| e2_floor=1.25 | +54.98% | 1.3194 | 37.03% | 1.4847 | 312 |
| e2_floor=1.75 | +47.43% | 1.1823 | 37.47% | 1.2656 | 283 |
| e2_slope=0.50 | +55.56% | 1.3085 | 37.26% | 1.4910 | 266 |
| e2_slope=1.00 | +57.54% | 1.3561 | 31.57% | 1.8227 | 292 |
| e2_floor=1.25 | +59.01% | 1.3746 | 36.33% | 1.6244 | 298 |
| e2_floor=1.75 | +51.94% | 1.2507 | 36.99% | 1.4042 | 268 |

### E5

| Variant | CAGR | Sharpe | MDD | MAR | Trades |
|---------|------|--------|-----|-----|--------|
| cap_q=0.85 | +53.47% | 1.2591 | 38.80% | 1.3782 | 212 |
| cap_q=0.95 | +56.57% | 1.3142 | 42.05% | 1.3452 | 198 |
| cap_lb=50 | +57.02% | 1.3234 | 39.98% | 1.4261 | 203 |
| cap_lb=200 | +58.42% | 1.3420 | 40.41% | 1.4457 | 203 |
| cap_q=0.85 | +57.12% | 1.3089 | 37.78% | 1.5120 | 203 |
| cap_q=0.95 | +58.93% | 1.3433 | 40.82% | 1.4436 | 190 |
| cap_lb=50 | +59.11% | 1.3479 | 41.03% | 1.4405 | 195 |
| cap_lb=200 | +62.62% | 1.3979 | 38.83% | 1.6124 | 194 |

## Part 11 — Final Recommendation (Dual-Level Acceptance)

**Framework**: Outcome-first. Proxy metrics (per-trade realized_R, fold-median Sharpe/MAR) are diagnostics. When proxy conflicts with actual outcome (final NAV, total net profit), outcome takes priority.

A conclusion of 'variant X is better' must hold on BOTH levels:

1. **Level 1 — Actual Outcome**: final NAV, total net profit, bootstrap P(CAGR+)

2. **Level 2 — Per-Trade Quality**: matched-trade exit quality, giveback, tail preservation

Verdicts: **PROVEN** (both levels pass, ≥97.5%), **SUPPORTED** (outcome passes, quality consistent, 80-97.5%), **INCONCLUSIVE** (levels conflict or borderline), **REJECTED** (outcome worse or quality catastrophic)


### E1

**Level 1 — Actual Outcome:**

- sp=120: final NAV $154,235 vs E0 $138,023 (+11.7%), net profit $144,235 vs E0 $128,023
- sp=144: final NAV $128,404 vs E0 $140,257 (-8.5%), net profit $118,404 vs E0 $130,257
- sp=120: bootstrap P(CAGR+)=42.8%, P(Sharpe+)=51.8%, P(MAR+)=51.5%
- sp=144: bootstrap P(CAGR+)=26.8%, P(Sharpe+)=33.7%, P(MAR+)=36.2%

**Level 1 verdict**: INCONSISTENT — better at one sp, worse at other

**Level 2 — Per-Trade Quality:**

- sp=120 matched-trade: d_realized_R=-0.7873 P(better)=0.7%, d_giveback_ratio=+0.1455 P(lower)=100.0%
- sp=144 matched-trade: d_realized_R=-0.8706 P(better)=0.5%, d_giveback_ratio=+0.1004 P(lower)=99.9%
- sp=120 top-10% PnL: E1=$324,264 vs E0=$277,411 (+16.9%)
- sp=144 top-10% PnL: E1=$266,224 vs E0=$259,422 (+2.6%)
- sp=120 fold consistency: E1 beats E0 in 9/20 folds on MAR
- sp=144 fold consistency: E1 beats E0 in 10/20 folds on MAR

**Level 2 verdict**: FAIL
  - sp=120: per-trade quality significantly WORSE (P=0.7%)
  - sp=144: per-trade quality significantly WORSE (P=0.5%)

**Combined verdict: INCONCLUSIVE**


### E2

**Level 1 — Actual Outcome:**

- sp=120: final NAV $162,066 vs E0 $138,023 (+17.4%), net profit $152,066 vs E0 $128,023
- sp=144: final NAV $154,654 vs E0 $140,257 (+10.3%), net profit $144,654 vs E0 $130,257
- sp=120: bootstrap P(CAGR+)=43.2%, P(Sharpe+)=52.9%, P(MAR+)=53.4%
- sp=144: bootstrap P(CAGR+)=45.2%, P(Sharpe+)=54.8%, P(MAR+)=57.2%

**Level 1 verdict**: WEAK — outcome better in data but bootstrap only 43.2% (not robust)

**Level 2 — Per-Trade Quality:**

- sp=120 matched-trade: d_realized_R=-0.9098 P(better)=0.3%, d_giveback_ratio=+0.1503 P(lower)=99.6%
- sp=144 matched-trade: d_realized_R=-0.8604 P(better)=0.6%, d_giveback_ratio=+0.1684 P(lower)=100.0%
- sp=120 top-10% PnL: E2=$353,497 vs E0=$277,411 (+27.4%)
- sp=144 top-10% PnL: E2=$304,088 vs E0=$259,422 (+17.2%)
- sp=120 fold consistency: E2 beats E0 in 8/20 folds on MAR
- sp=144 fold consistency: E2 beats E0 in 10/20 folds on MAR

**Level 2 verdict**: FAIL
  - sp=120: per-trade quality significantly WORSE (P=0.3%)
  - sp=144: per-trade quality significantly WORSE (P=0.6%)

**Combined verdict: INCONCLUSIVE**


### E3

**Level 1 — Actual Outcome:**

- sp=120: final NAV $77,806 vs E0 $138,023 (-43.6%), net profit $67,806 vs E0 $128,023
- sp=144: final NAV $68,653 vs E0 $140,257 (-51.1%), net profit $58,653 vs E0 $130,257
- sp=120: bootstrap P(CAGR+)=2.1%, P(Sharpe+)=45.5%, P(MAR+)=28.5%
- sp=144: bootstrap P(CAGR+)=0.9%, P(Sharpe+)=22.8%, P(MAR+)=16.4%

**Level 1 verdict**: FAIL — outcome WORSE at both sp's

**Level 2 — Per-Trade Quality:**

- sp=120 matched-trade: d_realized_R=-0.5501 P(better)=0.0%, d_giveback_ratio=+0.1340 P(lower)=100.0%
- sp=144 matched-trade: d_realized_R=-0.5955 P(better)=0.0%, d_giveback_ratio=+0.1170 P(lower)=100.0%
- sp=120 top-10% PnL: E3=$129,326 vs E0=$277,411 (-53.4%)
- sp=144 top-10% PnL: E3=$108,976 vs E0=$259,422 (-58.0%)
- sp=120 partial cost: extra=$5,575, net PnL benefit=E3$70,255 - E0$131,296 = $-61,042
- sp=144 partial cost: extra=$4,442, net PnL benefit=E3$62,306 - E0$134,359 = $-72,053
- sp=120 fold consistency: E3 beats E0 in 10/20 folds on MAR
- sp=144 fold consistency: E3 beats E0 in 7/20 folds on MAR

**Level 2 verdict**: FAIL
  - sp=120: per-trade quality significantly WORSE (P=0.0%)
  - sp=144: per-trade quality significantly WORSE (P=0.0%)
  - sp=120: top-10% PnL dropped -53.4% (limit -20%)
  - sp=144: top-10% PnL dropped -58.0% (limit -20%)
  - sp=120: partial exits cost more than they save (net PnL $-61,042)
  - sp=144: partial exits cost more than they save (net PnL $-72,053)

**Combined verdict: REJECTED**


### E4

**Level 1 — Actual Outcome:**

- sp=120: final NAV $75,639 vs E0 $138,023 (-45.2%), net profit $65,639 vs E0 $128,023
- sp=144: final NAV $59,207 vs E0 $140,257 (-57.8%), net profit $49,207 vs E0 $130,257
- sp=120: bootstrap P(CAGR+)=4.5%, P(Sharpe+)=28.9%, P(MAR+)=25.3%
- sp=144: bootstrap P(CAGR+)=1.9%, P(Sharpe+)=14.8%, P(MAR+)=13.0%

**Level 1 verdict**: FAIL — outcome WORSE at both sp's

**Level 2 — Per-Trade Quality:**

- sp=120 matched-trade: d_realized_R=-1.0844 P(better)=0.1%, d_giveback_ratio=+0.2364 P(lower)=100.0%
- sp=144 matched-trade: d_realized_R=-1.1835 P(better)=0.0%, d_giveback_ratio=+0.1891 P(lower)=100.0%
- sp=120 top-10% PnL: E4=$139,159 vs E0=$277,411 (-49.8%)
- sp=144 top-10% PnL: E4=$111,020 vs E0=$259,422 (-57.2%)
- sp=120 partial cost: extra=$8,629, net PnL benefit=E4$67,037 - E0$131,296 = $-64,259
- sp=144 partial cost: extra=$6,727, net PnL benefit=E4$51,948 - E0$134,359 = $-82,411
- sp=120 fold consistency: E4 beats E0 in 7/20 folds on MAR
- sp=144 fold consistency: E4 beats E0 in 8/20 folds on MAR

**Level 2 verdict**: FAIL
  - sp=120: per-trade quality significantly WORSE (P=0.1%)
  - sp=144: per-trade quality significantly WORSE (P=0.0%)
  - sp=120: top-10% PnL dropped -49.8% (limit -20%)
  - sp=144: top-10% PnL dropped -57.2% (limit -20%)
  - sp=120: partial exits cost more than they save (net PnL $-64,259)
  - sp=144: partial exits cost more than they save (net PnL $-82,411)

**Combined verdict: REJECTED**


### E5

**Level 1 — Actual Outcome:**

- sp=120: final NAV $181,479 vs E0 $138,023 (+31.5%), net profit $171,479 vs E0 $128,023
- sp=144: final NAV $193,345 vs E0 $140,257 (+37.9%), net profit $183,345 vs E0 $130,257
- sp=120: bootstrap P(CAGR+)=84.6%, P(Sharpe+)=87.6%, P(MAR+)=85.2%
- sp=144: bootstrap P(CAGR+)=89.3%, P(Sharpe+)=91.6%, P(MAR+)=89.6%

**Level 1 verdict**: PASS — outcome better at both sp's, bootstrap 84.6% → directionally supported

**Level 2 — Per-Trade Quality:**

- sp=120 matched-trade: d_realized_R=-0.0298 P(better)=42.1%, d_giveback_ratio=+0.1075 P(lower)=100.0%
- sp=144 matched-trade: d_realized_R=-0.0794 P(better)=26.7%, d_giveback_ratio=+0.0831 P(lower)=100.0%
- sp=120 top-10% PnL: E5=$340,355 vs E0=$277,411 (+22.7%)
- sp=144 top-10% PnL: E5=$327,480 vs E0=$259,422 (+26.2%)
- sp=120 fold consistency: E5 beats E0 in 14/20 folds on MAR
- sp=144 fold consistency: E5 beats E0 in 12/20 folds on MAR

**Level 2 verdict**: PASS — per-trade quality consistent with outcome

**Combined verdict: SUPPORTED**


### Summary Table

| Branch | Verdict | NAV vs E0 (sp=120) | NAV vs E0 (sp=144) | Boot P(CAGR+) | Per-Trade | Conflict? |
|--------|---------|--------------------|--------------------|---------------|----------|-----------|
| E1 | **INCONCLUSIVE** | +11.7% | -8.5% | 43%/27% | FAIL | no |
| E2 | **INCONCLUSIVE** | +17.4% | +10.3% | 43%/45% | FAIL | no |
| E3 | **REJECTED** | -43.6% | -51.1% | 2%/1% | FAIL | no |
| E4 | **REJECTED** | -45.2% | -57.8% | 4%/2% | FAIL | no |
| E5 | **SUPPORTED** | +31.5% | +37.9% | 85%/89% | PASS | no |

### Final Verdict

- **No branch reaches PROVEN (≥97.5% significance).**
- **SUPPORTED**: E5 — actual outcome +34.7% avg NAV improvement
- **Recommendation**: E0 remains default. Supported branches warrant further validation (cross-market, forward OOS).
- **Inconclusive**: E1, E2
- **Rejected**: E3, E4
- **Partial exits**: do NOT implement

### Research Questions Answered

1. **Does exit redesign improve net MAR / Sharpe / MDD vs baseline?** — See Parts 3B (outcome), 4 (fold-level proxy), 9 (bootstrap).
2. **Are improvements durable OOS?** — See Part 4 fold tables.
3. **Do improvements come from reduced giveback vs destroying right-tail winners?** — See Parts 5, 6.
4. **Are partial exits worth the extra cost?** — See Part 6 and per-branch Level 2.
5. **Does robust ATR improve exit quality?** — See Part 7 and E5 dual-level analysis.
6. **Is ratcheting significant?** — See E1/E4 Level 1 (outcome).
7. **Is dynamic trail significant?** — See E2 Level 1 (outcome).
8. **Are results consistent across slow_period 120 and 144?** — See Part 3B.
9. **Do context regimes (ER30) affect branch ranking?** — See Part 8.
10. **Does sensitivity show plateau or razor-edge?** — See Part 10.
11. **Which branch should replace E0, if any?** — See Final Verdict above.
12. **Single-market (BTC) confirmation only** — no ETH/altcoin data available.