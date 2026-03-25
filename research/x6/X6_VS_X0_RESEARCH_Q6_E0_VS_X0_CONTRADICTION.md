# Research Q6: E0 vs X0 Bootstrap Contradiction

**Date**: 2026-03-08
**Scripts**: `research/parity_eval_x.py` (T3, T4)
**Data**: `research/results/parity_eval_x/parity_eval_x_results.json`

---

## 1. The Contradiction

| Test | E0 vs X0 | Winner |
|------|----------|--------|
| T4 Bootstrap Sharpe | E0 wins **16/16** timescales | E0 |
| T4 Bootstrap CAGR | E0 wins **16/16** timescales | E0 |
| T4 Bootstrap MDD | X0 wins **16/16** timescales | X0 |
| T3 Real-data Sharpe | X0 wins **16/16** timescales | X0 |
| T3 Real-data CAGR | X0 wins **11/16** timescales | X0 |
| T3 Real-data MDD | X0 wins **13/16** timescales | X0 |
| T8 Calendar (by year) | X0 wins **5/8** years | X0 |
| WFO (vs E0 baseline) | X0: **6/8**, E0: 0/8 | X0 |
| Holdout (harsh) | X0 Sharpe 1.050 vs E0 0.960 | X0 |

Bootstrap says E0 is strictly better (except MDD). Every chronological test says X0 is better. Yet X0 = E0 + D1 EMA(21) regime filter.

---

## 2. Root Cause: D1 Data Is NOT Bootstrapped

**Source**: `research/parity_eval_x.py` line 663-665:
```python
bnav, _ = run_strategy(sid, bcl_full, bhi_full, blo_full, bvo_full, btb_full,
                       wi, slow_period=sp,
                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
```

The VCBB bootstrap generates **synthetic H4 bars** (bcl_full, bhi_full, ...) but passes **REAL D1 bars** (d1_cl, d1_ct). For X0/X2/X6, the sim computes:

```python
d1_ema = _ema(d1_cl, d1_ema_period)    # REAL D1 prices
d1_regime = d1_cl > d1_ema              # REAL regime signal
```

Then maps this real regime onto synthetic H4 timestamps. The synthetic H4 prices are completely decoupled from the real D1 regime signal.

### What this means mechanically

| Component | Data source | In bootstrap |
|-----------|-------------|-------------|
| EMA crossover (entry) | Synthetic H4 | Correctly bootstrapped |
| VDO filter | Synthetic H4 | Correctly bootstrapped |
| ATR trail (exit) | Synthetic H4 | Correctly bootstrapped |
| **D1 EMA(21) regime** | **REAL D1** | **Misaligned with synthetic** |

In real data, D1 EMA(21) says "bearish" when prices are actually falling. In bootstrap, D1 EMA(21) says "bearish" when synthetic prices might be doing anything — the regime signal becomes **noise** relative to synthetic returns.

---

## 3. Smoking Gun: EMA21(H4) vs EMA21-D1

The parity evaluation tested both H4 and D1 versions of the same regime filter concept:

| Strategy | Filter source | T4 Bootstrap vs E0 (Sharpe) |
|----------|--------------|----------------------------|
| EMA21 (H4 bars) | Synthetic H4 data | **15/16 wins** |
| EMA21-D1 (X0) | Real D1 data | **0/16 wins** |

Same concept. Same EMA period (≈21 D1 bars). Opposite bootstrap results.

**Why?** EMA21(H4) computes `ema(h4_close, 126)` from the synthetic H4 bars. The filter adapts to the synthetic returns. EMA21-D1 computes `ema(d1_close, 21)` from real data. The filter cannot adapt to synthetic paths.

This proves the bootstrap degradation of X0 is a **methodological artifact** of not synthesizing D1 bars.

---

## 4. Quantifying the Bootstrap Bias

### T4 Bootstrap at SP=120

| Metric | E0 | X0 | Delta | Interpretation |
|--------|:--:|:--:|:-----:|:---:|
| Sharpe median | 0.697 | 0.562 | **-0.135** | Filter costs 19% Sharpe |
| CAGR median | 21.95% | 14.28% | **-7.67%** | Filter costs 35% CAGR |
| MDD median | 58.49% | 52.17% | **-6.32%** | Filter saves 11% MDD |
| P(CAGR>0) | 88.2% | 84.6% | **-3.6%** | Lower survival |
| Trades | 211 | 186 | **-25** | 12% fewer trades |

The filter removes ~12% of trades. In bootstrap, those removed trades are **randomly distributed** across good and bad synthetic periods — pure return reduction with no timing benefit. The only remaining value is lower exposure → lower MDD.

### Average across all 16 timescales

| Metric | Average Delta (X0 − E0) |
|--------|:-----------------------:|
| Sharpe | **-0.112** |
| CAGR | **-6.67%** |
| MDD | **-5.12%** (X0 better) |
| P(CAGR>0) | **-3.9%** |

---

## 5. Why Chronological Tests Show the Opposite

### T3 Real-Data at SP=120

| Metric | E0 | X0 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 1.277 | 1.336 | **+0.060** |
| CAGR | 52.68% | 55.32% | **+2.64%** |
| MDD | 41.53% | 41.99% | +0.46% |
| Trades | 211 | 186 | -25 |

In real data, D1 EMA(21) filters out 25 bear-regime trades. These trades have **negative expected value** — they are entries during bear markets that the EMA cross eventually signals but the regime filter blocks. Removing them improves returns and Sharpe.

### Full Sharpe comparison (T3, all 16 timescales)

| SP | E0 | X0 | Delta | X0 wins? |
|---:|:--:|:--:|:-----:|:--------:|
| 30 | 0.673 | 0.955 | +0.283 | YES |
| 48 | 0.654 | 0.930 | +0.276 | YES |
| 60 | 0.797 | 1.044 | +0.248 | YES |
| 72 | 0.993 | 1.140 | +0.146 | YES |
| 84 | 1.129 | 1.175 | +0.047 | YES |
| 96 | 1.077 | 1.182 | +0.105 | YES |
| 108 | 1.209 | 1.263 | +0.054 | YES |
| 120 | 1.277 | 1.336 | +0.060 | YES |
| 144 | 1.328 | 1.341 | +0.013 | YES |
| 168 | 1.193 | 1.212 | +0.018 | YES |
| 200 | 1.432 | 1.477 | +0.045 | YES |
| 240 | 1.227 | 1.321 | +0.094 | YES |
| 300 | 1.017 | 1.219 | +0.202 | YES |
| 360 | 1.114 | 1.184 | +0.070 | YES |
| 500 | 1.074 | 1.100 | +0.025 | YES |
| 720 | 0.838 | 0.976 | +0.138 | YES |

**X0 wins 16/16.** The D1 regime filter adds value at EVERY timescale on real data.

### WFO comparison (EMA21-D1 vs E0 baseline)

| Window | Period | X0 Score | E0 Score | Delta |
|--------|--------|:--------:|:--------:|:-----:|
| W0 | 2022H1 | -25.23 | -43.28 | **+18.05** |
| W1 | 2022H2 | -103.05 | -104.20 | **+1.16** |
| W2 | 2023H1 | 55.98 | 35.42 | **+20.55** |
| W3 | 2023H2 | 209.50 | 225.49 | -15.99 |
| W4 | 2024H1 | 70.73 | 46.48 | **+24.25** |
| W5 | 2024H2 | 325.18 | 274.31 | **+50.88** |
| W6 | 2025H1 | 23.25 | 30.47 | -7.22 |
| W7 | 2025H2 | -24.00 | -30.71 | **+6.71** |

**X0 wins 6/8 WFO windows vs E0.** (Note: the EMA21(H4) version also wins 5/8.)

### Holdout

| Metric | X0 | E0 | Delta |
|--------|:--:|:--:|:-----:|
| Sharpe | 1.050 | 0.960 | **+0.090** |
| CAGR | 26.94% | 24.99% | **+1.95%** |
| MDD | 18.23% | 19.13% | **-0.90%** |
| Trades | 31 | 35 | -4 |

X0 beats E0 on ALL holdout metrics.

---

## 6. Why Bootstrap Shows X0 Winning MDD 16/16

Even with the D1 mismatch, the regime filter reduces MDD at all timescales. This is because:

1. **Lower exposure = lower drawdown** regardless of timing quality
2. X0 enters ~12-25% fewer trades across all timescales
3. During bootstrap paths, fewer entries mechanically reduce peak-to-trough drawdown
4. This is a **structural** benefit (fewer trades → lower MDD) not a **timing** benefit

The timing-dependent benefits (Sharpe, CAGR) are lost because timing requires regime alignment. The exposure-dependent benefits (MDD) survive because they only require fewer trades.

---

## 7. Why X0 Is Still the Right Recommendation

### The bootstrap result should be DISCOUNTED for X0

| Reason | Detail |
|--------|--------|
| D1 data not bootstrapped | Fatal mismatch between regime signal and synthetic returns |
| Proven by H4 comparison | EMA21(H4) wins E0 15/16 in same bootstrap; EMA21-D1 wins 0/16 |
| Methodological limitation | VCBB only synthesizes H4 bars; D1-dependent strategies cannot be fairly tested |
| Not a general problem | E0's bootstrap is correct (no external data references) |

### Every chronological test confirms X0 > E0

| Test | Result | Direction |
|------|--------|-----------|
| T3 Sharpe 16 TS | **16/16** | X0 better |
| T3 CAGR 16 TS | **11/16** | X0 better |
| T3 MDD 16 TS | **13/16** | X0 better |
| T8 Calendar | **5/8 years** | X0 better |
| WFO | **6/8** (only PASS) | X0 better |
| Holdout | **+0.090 Sharpe** | X0 better |
| T11 Paired boot | P(X0>E0)=85.3% | X0 better (ns) |

### The regime filter has a proven mechanism

The D1 EMA(21) regime filter was proven in the parity evaluation:
- Permutation test: p=0.0001 — alpha is REAL
- Timescale robustness: 16/16 positive Sharpe
- WFO: 6/8 — ONLY strategy to pass all validation gates
- Holdout: beats E0 on all metrics

---

## 8. Implications for X2/X6 Bootstrap

This same D1 mismatch affects X2 and X6 in T4 bootstrap. All three (X0, X2, X6) use the D1 EMA(21) regime filter, so all three are penalized by the same methodological artifact.

When comparing X2 vs X0 or X6 vs X0 in T4 bootstrap, the D1 mismatch **cancels out** because both sides have the same filter. The relative comparison (X2 wins X0 Sharpe 14-16/16) is still valid — it measures the adaptive trail's value above and beyond X0, not the absolute bootstrap level.

This is why Q5's finding (X2 wins X0 in bootstrap) is not contradicted by Q6. The D1 artifact affects the **absolute** bootstrap Sharpe of X0/X2/X6 equally, but not the **relative** comparison between them.

---

## 9. Summary

| Question | Answer |
|----------|--------|
| Why E0 wins X0 in bootstrap? | **D1 bars are NOT bootstrapped** — regime signal uses real data, misaligned with synthetic H4 prices |
| Is this a real E0 advantage? | **NO** — it's a methodological artifact proven by H4 vs D1 comparison |
| Why is X0 recommended? | **16/16 real-data Sharpe, 6/8 WFO, positive holdout delta** — every chronological test confirms X0 > E0 |
| Should bootstrap be trusted for X0? | **NO** — T4 bootstrap is INVALID for strategies with D1 references. Only relative comparisons (X2 vs X0) are meaningful |
| Can bootstrap be fixed? | Would require synthesizing D1 bars consistently with H4 paths (non-trivial — needs cross-timeframe VCBB) |
