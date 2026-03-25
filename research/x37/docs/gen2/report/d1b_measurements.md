# D1b - Feature Measurement & Signal Analysis

Measurement only. No strategy design, no backtests, no candidate proposal. Holdout and reserve_internal were not used. The historical snapshot remains candidate-mining-only; no clean external OOS claim may be made from it.

## Measurement Scope

- Calibration window: first available bar -> 2019-12-31 UTC
- Measurement window: 2020-01-01 -> 2023-06-30 UTC
- Raw data used as validated in D1a; no bar repair, no synthetic fills.

### Proxy definitions used for measurement

- D1: EMA spans 10/21/50/100/200; ROC lookbacks 5/10/21/50/100/200; close position inside rolling high/low windows 20/50/100/200.
- H4: ATR14 normalized by close; breakout proxy = close above prior 20-bar high; reclaim proxy = close back above EMA21 after >=2 bars below EMA21 and prior 10-bar min drawdown <= warmup median 20-bar drawdown; compression proxies use warmup 20th-percentile thresholds on ATR, 12-bar range, and 12-bar median candle body.
- 1h: local-range breakout proxies use prior 24-bar high and prior 8-bar high; reclaim proxy = close back above EMA20 after >=2 bars below EMA20; participation proxy = volume and num_trades both above warmup 75th percentile of their 24h-relative ratios.

## 1. D1 Timeframe Summary

Key read-through: D1 trend state is persistent and not random. Discovery bars spent 54.03% above EMA50 and 58.26% above EMA200; the bullish EMA stack held 45.42% of the time. ROC persistence is real but partly mechanically amplified by overlapping windows, so the more relevant result is that D1 permission states also improve forward returns and H4 entry quality.

### D1 EMA spread statistics

| EMA pair   | mean spread   | std    | q10     | median   | q90    |   ac1 |   ac5 |   sign persistence |
|:-----------|:--------------|:-------|:--------|:---------|:-------|------:|------:|-------------------:|
| 10/21      | 0.44%         | 3.87%  | -4.08%  | 0.25%    | 5.25%  | 0.992 | 0.869 |              0.966 |
| 21/50      | 1.05%         | 7.06%  | -8.62%  | 0.67%    | 9.49%  | 0.998 | 0.969 |              0.985 |
| 50/100     | 1.37%         | 8.65%  | -8.88%  | 2.39%    | 13.29% | 1     | 0.993 |              0.995 |
| 100/200    | 2.33%         | 12.35% | -15.80% | 2.62%    | 22.27% | 1     | 0.998 |              0.996 |

### D1 ROC statistics

|   ROC days | mean   | std     | q10     | median   | q90     |   ac1 |   ac5 |   sign persistence | pct positive   |
|-----------:|:-------|:--------|:--------|:---------|:--------|------:|------:|-------------------:|:---------------|
|          5 | 0.90%  | 8.13%   | -8.32%  | 0.66%    | 10.84%  | 0.794 | 0.043 |              0.769 | 54.42%         |
|         10 | 1.83%  | 11.91%  | -11.42% | 1.19%    | 16.44%  | 0.9   | 0.535 |              0.85  | 55.52%         |
|         21 | 3.89%  | 18.57%  | -16.75% | 1.67%    | 27.22%  | 0.954 | 0.777 |              0.891 | 55.83%         |
|         50 | 9.78%  | 32.45%  | -28.71% | 4.77%    | 52.85%  | 0.982 | 0.915 |              0.943 | 55.44%         |
|        100 | 22.33% | 62.39%  | -35.28% | 7.91%    | 89.91%  | 0.993 | 0.965 |              0.968 | 57.87%         |
|        200 | 47.12% | 119.13% | -50.91% | 10.29%   | 247.37% | 0.997 | 0.985 |              0.96  | 60.38%         |

### D1 close position vs rolling high/low

|   window days |   mean close position |   std |   q10 |   median |   q90 | pct >= 0.8   | pct <= 0.2   |
|--------------:|----------------------:|------:|------:|---------:|------:|:-------------|:-------------|
|            20 |                 0.552 | 0.289 | 0.158 |    0.556 | 0.924 | 29.21%       | 14.17%       |
|            50 |                 0.549 | 0.303 | 0.161 |    0.566 | 0.934 | 31.56%       | 16.29%       |
|           100 |                 0.556 | 0.307 | 0.133 |    0.601 | 0.934 | 30.85%       | 19.81%       |
|           200 |                 0.541 | 0.323 | 0.083 |    0.559 | 0.936 | 31.95%       | 24.04%       |

### D1 trend persistence

|   EMA | pct above   | pct below   |   longest above run (days) |   longest below run (days) |
|------:|:------------|:------------|---------------------------:|---------------------------:|
|    10 | 52.94%      | 47.06%      |                         49 |                         26 |
|    21 | 53.72%      | 46.28%      |                         63 |                         38 |
|    50 | 54.03%      | 45.97%      |                        193 |                        111 |
|   100 | 55.68%      | 44.32%      |                        213 |                        212 |
|   200 | 58.26%      | 41.74%      |                        385 |                        285 |

### D1 state -> own forward-return lift (on minus off)

| D1 state           |   horizon days | mean fwd return lift (on-off)   | hit-rate lift   |
|:-------------------|---------------:|:--------------------------------|:----------------|
| close_above_ema50  |              5 | 1.27%                           | 1.20%           |
| close_above_ema50  |             10 | 1.87%                           | 2.78%           |
| close_above_ema50  |             20 | 3.21%                           | 2.63%           |
| roc50_positive     |              5 | 0.98%                           | 1.91%           |
| roc50_positive     |             10 | 1.50%                           | 4.09%           |
| roc50_positive     |             20 | 1.58%                           | -1.05%          |
| ema_stack_bull     |              5 | 1.01%                           | 1.50%           |
| ema_stack_bull     |             10 | 1.61%                           | 1.62%           |
| ema_stack_bull     |             20 | 3.16%                           | 1.03%           |
| close_pos100_upper |              5 | 1.27%                           | 0.03%           |
| close_pos100_upper |             10 | 2.08%                           | 2.81%           |
| close_pos100_upper |             20 | 3.53%                           | 3.92%           |

## 2. H4 Timeframe Summary

Key read-through: raw H4 bar-direction runs are short, but volatility state and pullback state are highly structured. ATR14/close has ac1 0.994 and ac24 0.738; full compression episodes cover 11.17% of discovery H4 bars with median duration 3.5 bars. Drawdown recovery time is strongly depth-dependent.

### H4 consecutive same-direction run lengths

| direction   | count   |   mean run |   median |   p90 |   max |
|:------------|:--------|-----------:|---------:|------:|------:|
| up          | 2,101   |       1.88 |        1 |     3 |    10 |
| down        | 2,102   |       1.77 |        1 |     3 |     9 |

### H4 ATR14/close distribution and persistence

| mean ATR14/close   | std   | p10   | median   | p80   | p90   |   ac1 |   ac6 |   ac24 |
|:-------------------|:------|:------|:---------|:------|:------|------:|------:|-------:|
| 2.09%              | 1.08% | 1.08% | 1.87%    | 2.61% | 3.27% | 0.994 | 0.937 |  0.738 |

### H4 absolute-return autocorrelation

|   abs-ret ac1 |   ac3 |   ac6 |   ac12 |   ac24 |
|--------------:|------:|------:|-------:|-------:|
|         0.217 | 0.187 |  0.16 |  0.149 |  0.148 |

### H4 compression-state frequency and duration

| state             | pct bars   |   episodes |   median duration bars |   p90 duration bars |   max duration bars |
|:------------------|:-----------|-----------:|-----------------------:|--------------------:|--------------------:|
| low_atr           | 21.19%     |         91 |                    4   |                35   |                 175 |
| low_range12       | 22.33%     |        176 |                    5   |                24   |                 126 |
| low_body12        | 18.98%     |        197 |                    3   |                17   |                 126 |
| compression_combo | 11.17%     |         94 |                    3.5 |                22   |                 125 |
| high_atr          | 8.65%      |         28 |                    6.5 |                67.8 |                 177 |

### H4 drawdown from prior rolling high

|   rolling-high bars | mean drawdown   | median drawdown   | p10 depth   | p25 depth   | p50 depth   | p75 depth   | p90 depth   | pct bars in drawdown   |
|--------------------:|:----------------|:------------------|:------------|:------------|:------------|:------------|:------------|:-----------------------|
|                  21 | -4.65%          | -3.33%            | -10.14%     | -6.19%      | -3.33%      | -1.79%      | -0.94%      | 94.79%                 |
|                  42 | -6.25%          | -4.65%            | -13.33%     | -8.27%      | -4.65%      | -2.38%      | -1.25%      | 96.25%                 |
|                 126 | -10.25%         | -7.80%            | -21.54%     | -14.85%     | -7.80%      | -3.69%      | -1.90%      | 97.44%                 |

### H4 completed drawdown episode recovery by depth bucket (42-bar rolling-high reference)

| depth bucket     |   count |   median bars to recover |   mean bars to recover |   max bars |
|:-----------------|--------:|-------------------------:|-----------------------:|-----------:|
| deep_>10%        |      36 |                    105   |                 120.47 |        267 |
| mod_5_10%        |      36 |                     42.5 |                  49.06 |        125 |
| shallow_2_5%     |      52 |                     12.5 |                  17.31 |         75 |
| very_shallow_<2% |      81 |                      3   |                   4.04 |         28 |

## 3. 1h Timeframe Summary

Key read-through: 1h breakout events exist frequently enough to study, but standalone breakout signal is only modest. The cleaner structure is conditional: participation and prior H4 compression improve follow-through; a generic 1h anchor reclaim does not.

- 24h-range upside breakout frequency: 2.93% of discovery 1h bars (898 events).
- 8h short-consolidation upside breakout frequency: 5.32% of discovery 1h bars (1,629 events).
- Generic 1h EMA20 reclaim events: 1,466.

### 1h 24-bar range breakout follow-through

|   horizon 1h bars |   count | mean fwd return   | median   | hit rate   |
|------------------:|--------:|:------------------|:---------|:-----------|
|                 3 |     898 | 0.02%             | -0.10%   | 45.10%     |
|                 6 |     898 | 0.04%             | -0.11%   | 45.10%     |
|                12 |     898 | 0.14%             | -0.11%   | 46.99%     |
|                24 |     898 | 0.34%             | -0.00%   | 49.89%     |

### 1h 8-bar short-consolidation breakout follow-through

|   horizon 1h bars | count   | mean fwd return   | median   | hit rate   |
|------------------:|:--------|:------------------|:---------|:-----------|
|                 3 | 1,629   | 0.01%             | -0.10%   | 44.75%     |
|                 6 | 1,629   | 0.04%             | -0.12%   | 45.30%     |
|                12 | 1,629   | 0.10%             | -0.03%   | 48.86%     |
|                24 | 1,628   | 0.21%             | -0.04%   | 49.08%     |

### 1h reclaim-above-EMA20 follow-through

|   horizon 1h bars | count   | mean fwd return   | median   | hit rate   |
|------------------:|:--------|:------------------|:---------|:-----------|
|                 3 | 1,466   | 0.02%             | -0.04%   | 46.79%     |
|                 6 | 1,466   | -0.01%            | -0.04%   | 48.57%     |
|                12 | 1,466   | 0.03%             | 0.01%    | 50.27%     |
|                24 | 1,466   | 0.11%             | 0.07%    | 52.05%     |

### 1h participation around H4 breakout / reclaim events (next 6h after H4 signal close)

| H4 event      |   n events |   mean next-6h volume ratio | volume ratio lift   |   mean next-6h trades ratio | trades ratio lift   |   mean next-6h taker buy ratio | taker ratio delta   | mean next-6h return   | median next-6h return   |
|:--------------|-----------:|----------------------------:|:--------------------|----------------------------:|:--------------------|-------------------------------:|:--------------------|:----------------------|:------------------------|
| h4_breakout20 |        291 |                       1.434 | 15.77%              |                       1.318 | 14.27%              |                          0.493 | 0.09%               | 0.04%                 | -0.09%                  |
| h4_reclaim    |        248 |                       1.249 | 0.82%               |                       1.18  | 2.24%               |                          0.497 | 0.51%               | 0.01%                 | -0.13%                  |

## 4. Cross-Timeframe Relationships

### D1 trend filter -> H4 state alignment

| D1 state              | n on   | n off   | H4 above EMA21 when on   | H4 above EMA21 when off   |   lift pp |
|:----------------------|:-------|:--------|:-------------------------|:--------------------------|----------:|
| d1_close_above_ema50  | 4,133  | 3,528   | 64.48%                   | 40.19%                    |     24.29 |
| d1_roc50_positive     | 4,241  | 3,420   | 60.06%                   | 44.91%                    |     15.14 |
| d1_ema_stack_bull     | 3,473  | 4,188   | 57.41%                   | 49.88%                    |      7.53 |
| d1_close_pos100_upper | 4,361  | 3,300   | 59.99%                   | 44.45%                    |     15.53 |

### D1 permission on/off -> H4 breakout and reclaim quality

| H4 event      | D1 filter             |   horizon H4 bars |   count on |   count off | mean on   | mean off   | mean lift   | hit on   | hit off   |   hit lift pp |
|:--------------|:----------------------|------------------:|-----------:|------------:|:----------|:-----------|:------------|:---------|:----------|--------------:|
| H4 breakout20 | D1 close>EMA50        |                 6 |        192 |         101 | 0.56%     | 0.18%      | 0.38%       | 50.00%   | 49.50%    |          0.5  |
| H4 breakout20 | D1 close>EMA50        |                12 |        192 |         101 | 0.42%     | -0.04%     | 0.45%       | 50.00%   | 47.52%    |          2.48 |
| H4 breakout20 | D1 ROC50>0            |                 6 |        184 |         109 | 0.49%     | 0.31%      | 0.18%       | 51.09%   | 47.71%    |          3.38 |
| H4 breakout20 | D1 ROC50>0            |                12 |        184 |         109 | 0.40%     | 0.03%      | 0.38%       | 51.63%   | 44.95%    |          6.68 |
| H4 breakout20 | D1 EMA21>EMA50>EMA200 |                 6 |        154 |         139 | 0.55%     | 0.29%      | 0.26%       | 52.60%   | 46.76%    |          5.83 |
| H4 breakout20 | D1 EMA21>EMA50>EMA200 |                12 |        154 |         139 | 0.20%     | 0.33%      | -0.13%      | 48.70%   | 49.64%    |         -0.94 |
| H4 reclaim    | D1 close>EMA50        |                 6 |        100 |         149 | 0.58%     | 0.15%      | 0.42%       | 50.00%   | 48.32%    |          1.68 |
| H4 reclaim    | D1 close>EMA50        |                12 |        100 |         149 | 1.18%     | 0.28%      | 0.90%       | 57.00%   | 48.99%    |          8.01 |
| H4 reclaim    | D1 ROC50>0            |                 6 |        122 |         127 | 0.32%     | 0.33%      | -0.01%      | 49.18%   | 48.82%    |          0.36 |
| H4 reclaim    | D1 ROC50>0            |                12 |        122 |         127 | 0.69%     | 0.60%      | 0.10%       | 52.46%   | 51.97%    |          0.49 |
| H4 reclaim    | D1 EMA21>EMA50>EMA200 |                 6 |        102 |         147 | 0.44%     | 0.24%      | 0.20%       | 50.98%   | 47.62%    |          3.36 |
| H4 reclaim    | D1 EMA21>EMA50>EMA200 |                12 |        102 |         147 | 0.60%     | 0.68%      | -0.08%      | 51.96%   | 52.38%    |         -0.42 |

### H4 compression state -> 1h breakout 24h follow-through

| conditioning state                     |   horizon 1h bars |   count on |   count off | mean on   | mean off   | mean lift   | hit on   | hit off   |   hit lift pp |
|:---------------------------------------|------------------:|-----------:|------------:|:----------|:-----------|:------------|:---------|:----------|--------------:|
| H4 compression combo                   |                24 |        109 |         789 | 0.91%     | 0.26%      | 0.65%       | 55.05%   | 49.18%    |          5.87 |
| H4 low ATR                             |                24 |        199 |         699 | 0.70%     | 0.23%      | 0.47%       | 50.75%   | 49.64%    |          1.11 |
| H4 low range                           |                24 |        227 |         671 | 0.53%     | 0.27%      | 0.27%       | 50.22%   | 49.78%    |          0.44 |
| H4 low body                            |                24 |        178 |         720 | 0.70%     | 0.25%      | 0.46%       | 53.37%   | 49.03%    |          4.34 |
| H4 compression + high 1h participation |                24 |         97 |         801 | 0.97%     | 0.26%      | 0.71%       | 55.67%   | 49.19%    |          6.48 |

Notable interaction: 1h 24-bar breakouts have baseline 24h mean follow-through 0.34%; that rises to 0.38% with high 1h participation, 0.91% after H4 compression, and 0.97% when both H4 compression and high 1h participation are present.

## 5. Taker Flow Analysis

Key read-through: taker-buy ratio is stable in distribution but weak as a standalone directional predictor on intraday horizons. The only visible structure is mild and horizon-dependent: 4h has a small positive medium-horizon tendency; daily shows short/medium-horizon support but reverses at longer horizon.

### Taker-buy ratio distribution by timeframe (discovery only)

| TF   |   mean |    std |   median |    p10 |    p90 |    ac1 |    ac5 |
|:-----|-------:|-------:|---------:|-------:|-------:|-------:|-------:|
| 15m  | 0.4914 | 0.0617 |   0.4926 | 0.4156 | 0.5643 | 0.1426 | 0.0558 |
| 1h   | 0.4918 | 0.0398 |   0.4932 | 0.4423 | 0.5386 | 0.1938 | 0.0485 |
| 4h   | 0.4921 | 0.0267 |   0.4939 | 0.4587 | 0.5233 | 0.2056 | 0.0786 |
| 1d   | 0.4925 | 0.0157 |   0.4945 | 0.4716 | 0.5104 | 0.2223 | 0.1287 |

### Taker imbalance vs forward returns: correlations

| TF   |   horizon bars |   pearson |   spearman |
|:-----|---------------:|----------:|-----------:|
| 15m  |              1 |    0.0022 |    -0.0288 |
| 15m  |              4 |   -0.0077 |    -0.031  |
| 15m  |             16 |   -0.0041 |    -0.0215 |
| 15m  |             96 |   -0.0009 |    -0.0082 |
| 1h   |              1 |   -0.0015 |    -0.0362 |
| 1h   |              6 |   -0.0032 |    -0.0308 |
| 1h   |             12 |    0.0058 |    -0.0165 |
| 1h   |             24 |    0.0005 |    -0.014  |
| 4h   |              1 |   -0.0109 |    -0.0544 |
| 4h   |              3 |    0.008  |    -0.0244 |
| 4h   |              6 |    0.002  |    -0.0243 |
| 4h   |             12 |    0.0147 |    -0.0016 |
| 1d   |              1 |   -0.0202 |    -0.0541 |
| 1d   |              3 |    0.0056 |    -0.0142 |
| 1d   |              5 |    0.0112 |    -0.029  |
| 1d   |             10 |   -0.0615 |    -0.0543 |

### Strongest correlation horizon by timeframe

| TF   |   best horizon bars |   best pearson |   spearman at same horizon |
|:-----|--------------------:|---------------:|---------------------------:|
| 15m  |                   4 |        -0.0077 |                    -0.031  |
| 1h   |                  12 |         0.0058 |                    -0.0165 |
| 4h   |                  12 |         0.0147 |                    -0.0016 |
| 1d   |                  10 |        -0.0615 |                    -0.0543 |

### Largest top-decile minus bottom-decile spread by timeframe

| TF   |   best horizon bars | top-bottom spread   | top hit   | bottom hit   |
|:-----|--------------------:|:--------------------|:----------|:-------------|
| 15m  |                   4 | -0.02%              | 47.94%    | 54.44%       |
| 1h   |                  12 | 0.05%               | 50.10%    | 54.15%       |
| 4h   |                  12 | 0.26%               | 55.48%    | 52.61%       |
| 1d   |                  10 | -2.84%              | 54.33%    | 64.06%       |

Interpretation:

- 15m and 1h taker imbalance: effectively noise as a standalone predictor.
- 4h taker imbalance: weak positive signal at longer horizons, still small in magnitude.
- 1d taker imbalance: positive at 3–5 day horizons, but reversal at 10 days dominates the strongest absolute effect; this looks more like crowding/exhaustion than a clean continuation signal.

## 6. Primitives Signal Assessment

| Archetype   | Primitive                                       | Assessment      | Evidence                                                                                                                  |
|:------------|:------------------------------------------------|:----------------|:--------------------------------------------------------------------------------------------------------------------------|
| A           | D1 momentum (ROC / trend permission)            | YES             | Positive D1 momentum states lift 10–20d D1 forward returns and improve H4 breakout quality under D1 permission.           |
| A           | D1 EMA slope / spread                           | YES             | EMA spreads are highly persistent; bullish EMA stack lifts 20d D1 forward return by ~3.16pp vs off-state.                 |
| A           | D1 close vs rolling anchor                      | YES             | Close in upper half of 100d range lifts 10–20d D1 forward return materially vs lower half.                                |
| A           | H4 trend persistence / state                    | YES             | H4 close>EMA21 occurs much more often when D1 trend filters are on; alignment lift ranges ~7.5pp to ~24.3pp.              |
| A           | H4 volatility quiet / expansion as regime state | YES (context)   | ATR14/close is strongly clustered (ac1 ~0.994, ac24 ~0.738); regime state is measurable but not directional by itself.    |
| A           | Exit: permission off / state deterioration      | YES             | H4 breakout and reclaim follow-through degrades materially when D1 permission states are off.                             |
| A           | Exit: ATR-style trailing                        | WEAK            | ATR is stable enough for risk-state tracking, but taker/volatility measures alone do not provide strong directional edge. |
| B           | H4 drawdown from rolling high                   | YES             | Recovery time scales sharply with depth: shallow 2–5% median ~12.5 bars, 5–10% ~42.5, >10% ~105.                          |
| B           | H4 distance from MA / anchor reclaim            | YES             | H4 reclaim above EMA21 after pullback is stronger when D1 permission is on, especially over 48h.                          |
| B           | H4 range position                               | WEAK            | Range-position structure exists, but isolated incremental signal was not clearly separated from drawdown/anchor effects.  |
| B           | 1h reclaim above local anchor                   | WEAK/NO         | Generic 1h EMA20 reclaim has flat to weak follow-through and does not improve with high participation.                    |
| B           | 1h short-consolidation break                    | YES             | 8h local breakout with high participation materially outperforms low-participation breaks.                                |
| B           | 1h participation confirmation                   | YES             | High 1h volume/trades lifts 24h breakout follow-through vs low-participation events.                                      |
| C           | D1 non-bearish / neutral-positive permission    | YES             | Same D1 trend filters used for A/B improve H4 entry quality and H4 alignment.                                             |
| C           | H4 low ATR compression                          | YES             | 1h breakout follow-through is stronger after H4 low-ATR states than after non-low-ATR states.                             |
| C           | H4 range compression                            | YES             | Low H4 range compression improves subsequent 1h breakout returns, though effect is smaller than full compression combo.   |
| C           | H4 body compression                             | YES             | Low-body regimes improve 24h 1h breakout follow-through and hit rate vs non-compressed regimes.                           |
| C           | 1h breakout above local range                   | WEAK standalone | 24h mean follow-through is positive but median is near flat without conditioning.                                         |
| C           | 1h volume / trades participation rise           | YES             | Participation is the cleanest 1h confirmation variable; strongest when combined with H4 compression.                      |
| C           | 1h taker-flow participation rise                | WEAK            | Taker-buy ratio alone has near-zero linear correlation with forward returns on intraday horizons.                         |

## Notable Structural Features / Caveats

- Snapshot gaps logged in D1a were not repaired. All measurements use raw bars as-is.
- EMA spread and multi-day ROC persistence are inflated by overlap mechanics, so forward-return conditioning and cross-timeframe event studies matter more than raw autocorrelation alone.
- Compression and participation effects are materially cleaner than taker-flow-only effects.
- Generic 1h anchor reclaim is measurably weaker than breakout-with-confirmation constructs.
- No holdout or reserve_internal data was touched.
