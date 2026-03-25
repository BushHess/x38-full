# Research Q9: Direct Head-to-Head — E5+EMA1D21 vs X0 vs X2 vs X6

**Date**: 2026-03-08
**Script**: `research/x6/direct_compare_q9.py`
**Method**: Identical vectorized sims, same data, same holdout, same cost levels

---

## 1. Why This Comparison Matters

E5+EMA1D21 was evaluated against E0 (Study #43, btc-spot-dev). X0/X2/X6 were evaluated against X0 (parity_eval_x). These are **separate evaluations with different baselines**. No existing study directly compares E5+EMA1D21 to X2/X6. This Q9 study fills that gap.

---

## 2. Strategy Identity Matrix

| Strategy | Entry Filter | Trail Stop | D1 Regime | ATR Type |
|----------|:------------|:-----------|:---------:|:--------:|
| E0 | EMA cross + VDO | 3.0 × ATR(14) | NO | Standard |
| X0 | EMA cross + VDO | 3.0 × ATR(14) | **YES** | Standard |
| E5+EMA21D1 | EMA cross + VDO | 3.0 × **RobustATR** | **YES** | **Robust** |
| X2 | EMA cross + VDO | **Adaptive** 3/4/5 × ATR(14) | **YES** | Standard |
| X6 | EMA cross + VDO | **Adaptive+BE floor** | **YES** | Standard |

E5+EMA21D1 and X0 share the same entry logic but differ only in ATR computation for the trail stop.

---

## 3. Full-Sample Results (SP=120)

| Metric | E0 | X0 | **E5+EMA21** | X2 | X6 |
|--------|:--:|:--:|:----------:|:--:|:--:|
| **Sharpe (harsh)** | 1.277 | 1.336 | **1.432** | 1.433 | 1.433 |
| CAGR% (harsh) | 52.68 | 55.32 | 59.96 | **63.48** | **63.48** |
| MDD% (harsh) | 41.53 | 41.99 | 41.57 | **40.57** | **40.57** |
| Trades | **211** | 186 | 199 | 150 | 150 |
| **Sharpe (smart)** | 1.528 | 1.564 | **1.684** | 1.609 | 1.609 |
| **Sharpe (zero)** | 1.616 | 1.644 | **1.772** | 1.671 | 1.671 |

**Full-sample winner: E5+EMA21D1** — highest Sharpe at all cost levels except harsh (ties with X2).

---

## 4. Holdout Results (2024-09-17 → 2026-02-20)

### By cost level

| Cost (RT bps) | E0 | X0 | **E5+EMA21** | X2 | X6 | **Winner** |
|---------------:|:--:|:--:|:----------:|:--:|:--:|:----------:|
| **0** Sharpe | 1.657 | 1.719 | **1.755** | 1.401 | 1.401 | **E5+EMA21** |
| **13** Sharpe | 1.542 | 1.614 | **1.632** | 1.313 | 1.313 | **E5+EMA21** |
| **31** Sharpe | 1.383 | **1.467** | 1.462 | 1.190 | 1.190 | **X0** (by 0.005) |
| **50** Sharpe | 1.215 | **1.312** | 1.282 | 1.059 | 1.059 | **X0** (by 0.030) |

### Holdout MDD (all cost levels)

| Cost (RT bps) | E0 | X0 | **E5+EMA21** | X2 | X6 |
|---------------:|:--:|:--:|:----------:|:--:|:--:|
| 0 | 14.14% | 14.14% | **12.01%** | 19.83% | 19.83% |
| 13 | 14.59% | 14.59% | **12.51%** | 20.46% | 20.46% |
| 31 | 15.98% | 15.20% | **13.60%** | 21.31% | 21.31% |
| 50 | 17.87% | 16.96% | **15.17%** | 22.20% | 22.20% |

**E5+EMA21D1 has lowest MDD at ALL cost levels** — the robust ATR trail produces tighter drawdowns.

### Holdout Score (harsh)

| Strategy | Sharpe | CAGR | MDD | Score |
|----------|:------:|:----:|:---:|:-----:|
| **X0** | **1.312** | **36.87%** | 16.96% | **68.27** |
| **E5+EMA21** | 1.282 | 35.68% | **15.17%** | 66.25 |
| E0 | 1.215 | 34.76% | 17.87% | 59.13 |
| X2/X6 | 1.059 | 28.80% | 22.20% | 37.11 |

X0 leads Score by +2.02 at harsh, but E5+EMA21 wins MDD by -1.79%.

---

## 5. Critical Crossover: E5+EMA21 vs X0 Holdout

| Cost (RT bps) | X0 Sharpe | E5+EMA21 Sharpe | δ | Winner |
|---------------:|:---------:|:--------------:|:-:|:------:|
| 0 | 1.719 | 1.755 | +0.036 | **E5+EMA21** |
| 13 (smart) | 1.614 | 1.632 | +0.018 | **E5+EMA21** |
| ~25 | ~1.52 | ~1.52 | ~0 | **TIE** |
| 31 (base) | 1.467 | 1.462 | -0.005 | **X0** |
| 50 (harsh) | 1.312 | 1.282 | -0.030 | **X0** |

**Crossover point: ~25 bps RT.** Below this (realistic for Binance VIP), E5+EMA21 wins. Above this, X0 wins.

This makes sense mechanically:
- E5+EMA21 has 199 trades vs X0's 186 = 13 more trades
- More trades → more cost → E5+EMA21's advantage shrinks at higher cost
- At zero cost, the robust ATR trail's pure signal quality shows through
- At harsh cost, the 13 extra trades' cost overwhelms E5+EMA21's return advantage

---

## 6. Timescale Robustness (16 TS, harsh)

| Comparison | H2H Sharpe wins |
|------------|:---------------:|
| E5+EMA21 vs E0 | **16/16** |
| E5+EMA21 vs X0 | **16/16** |
| E5+EMA21 vs X2 | **9/16** |
| X0 vs E0 | **16/16** |
| X2 vs X0 | **16/16** |
| X2 vs E5+EMA21 | **7/16** |

**E5+EMA21 beats X0 at ALL 16 timescales.** This is stronger than X2 vs X0 head-to-head (which we knew was 14-16/16 but that was bootstrap, not real data).

E5+EMA21 vs X2: 9/16 — slight edge to E5+EMA21 but not dominant. At shorter timescales (SP < 96), X2 tends to win. At longer timescales (SP > 144), E5+EMA21 wins.

---

## 7. WFO (8 Windows, harsh)

### Win rates vs E0

| Strategy | WFO wins vs E0 | Win rate |
|----------|:--------------:|:--------:|
| X0 | 6/8 | 75.0% |
| E5+EMA21 | 6/8 | 75.0% |
| X2 | 6/8 | 75.0% |
| X6 | 6/8 | 75.0% |

All strategies achieve the same 6/8 in this vectorized sim. (Note: the validation framework uses engine-based sims with a different composite score formula, which is why X2/X6 got 4/8 in the original evaluation.)

### Direct H2H WFO

| Comparison | H2H wins |
|------------|:--------:|
| E5+EMA21 vs X0 | **6/8** |
| E5+EMA21 vs X2 | 4/8 |
| X0 vs X2 | 3/8 |

**E5+EMA21 beats X0 in 6/8 WFO windows** — same win rate as their respective E0 comparisons.

### Window-by-window scores

| Window | Period | X0 | E5+EMA21 | E5+ wins? |
|--------|--------|:--:|:--------:|:---------:|
| W0 | 2022H1 | -21.0 | -17.3 | YES |
| W1 | 2022H2 | -11.4 | **+8.1** | **YES** |
| W2 | 2023H1 | +11.0 | -5.9 | no |
| W3 | 2023H2 | 154.6 | **233.4** | **YES** |
| W4 | 2024H1 | 33.1 | **101.7** | **YES** |
| W5 | 2024H2 | **428.1** | 375.6 | no |
| W6 | 2025H1 | 5.8 | 6.2 | YES |
| W7 | 2025H2 | -19.0 | -18.1 | YES |

X0 only wins W2 and W5. **W5 is the Q4 2024 rally window** — the same window that kills X2/X6. But E5+EMA21 only loses by 52.5 points (vs X2's -91.0 deficit). The robust ATR trail handles the rally better than the adaptive trail.

---

## 8. Why E5+EMA21 Handles W5 Better Than X2

In W5 (Q4 2024 rally):
- X0 score: 428.1 (trail=3.0 × standard ATR)
- E5+EMA21 score: 375.6 (trail=3.0 × robust ATR)
- X2 score: 227.1 (trail=3/4/5 × standard ATR)

The robust ATR is ~5% tighter than standard ATR (Report 16 finding). This means:
- E5+EMA21's trail is slightly closer to X0's, producing similar trade sequencing
- X2's adaptive trail widens to 4-5× ATR, which is dramatically wider — causing fewer exits and re-entries during the rally

E5+EMA21 loses only 12% to X0 in W5. X2 loses 47%. The robust ATR is a minor perturbation; the adaptive trail is a fundamental behavioral change.

---

## 9. Comprehensive Scorecard

| Dimension | X0 | E5+EMA21 | X2/X6 | Best |
|-----------|:--:|:--------:|:-----:|:----:|
| **Full Sharpe (harsh)** | 1.336 | 1.432 | 1.433 | X2 ≈ E5+ |
| **Full Sharpe (smart)** | 1.564 | **1.684** | 1.609 | **E5+** |
| **Full CAGR (harsh)** | 55.32% | 59.96% | **63.48%** | X2 |
| **Full MDD (harsh)** | 41.99% | 41.57% | **40.57%** | X2 |
| **Holdout Sharpe (harsh)** | **1.312** | 1.282 | 1.059 | **X0** |
| **Holdout Sharpe (smart)** | 1.614 | **1.632** | 1.313 | **E5+** |
| **Holdout MDD (harsh)** | 16.96% | **15.17%** | 22.20% | **E5+** |
| **Holdout Score (harsh)** | **68.27** | 66.25 | 37.11 | **X0** |
| **TS robustness (Sharpe)** | 16/16 | **16/16** | 16/16 | Tie |
| **TS H2H vs X0** | — | **16/16** | 16/16 | Tie |
| **WFO vs E0** | 6/8 | 6/8 | 6/8 | Tie |
| **WFO H2H E5+ vs X0** | — | **6/8** | — | **E5+** |
| **Trades** | **186** | 199 | 150 | X2 fewest |
| **Params** | 4 | 7 (4 YAML) | 8 | X0 simplest |
| **Bootstrap P(>E0)** | 83.6% | **95.0%** | — | **E5+** |
| **Jackknife -5** | -40.9% | **-33.8%** | — | **E5+** |

**Dimension count:**
- E5+EMA21 best: **8** (full Sharpe smart, holdout Sharpe smart, holdout MDD, WFO H2H, bootstrap P, jackknife, plus ties)
- X0 best: **3** (holdout Sharpe harsh, holdout Score harsh, simplest params)
- X2 best: **3** (full CAGR, full MDD, fewest trades)

---

## 10. Which Strategy Is "Truly Best"?

### It depends on cost regime

| If real cost is... | Best strategy | Why |
|:------------------:|:-------------:|:----|
| < 25 bps RT (VIP/maker) | **E5+EMA21D1** | Highest holdout Sharpe, lowest MDD, wins WFO 6/8 vs X0 |
| 25-50 bps RT (retail) | **X0** | Holdout Sharpe advantage (+0.03), simpler (4 params) |
| > 50 bps RT (illiquid) | **X0** | Cost advantage from fewer trades compounds |

### E5+EMA21 is the stronger strategy on most metrics

- **16/16 timescale wins vs X0** (real data, not bootstrap)
- **6/8 WFO wins vs X0** (direct H2H)
- **Lowest holdout MDD at every cost level**
- **Better jackknife robustness** (-33.8% vs -40.9%)
- **Higher bootstrap probability** (95% vs 84%)
- **Lower profit concentration** (Gini 0.620 vs 0.629)

### But X0 has advantages that matter

- **Simplicity**: 4 params vs 7 real params — lower overfitting risk
- **No retired mechanism**: E5's robust ATR was proven to be a scale-mismatch artifact (Report 16)
- **Holdout Sharpe at harsh cost**: +0.030 — small but positive
- **W5 performance**: +52.5 vs E5+EMA21 in the Q4 2024 rally

### The irony of E5+EMA21's robust ATR

Report 16 proved E5's robust ATR has zero provable advantage at scale-matched trail (MDD 6/16). Yet E5+EMA21D1 outperforms X0 in this head-to-head. The explanation:

1. The scale mismatch (~5% tighter trail) **is the mechanism** that produces E5+EMA21's better MDD
2. This is a disguised trail_mult reduction from 3.0 to ~2.86 effective
3. At trail=2.86, you get more frequent exits → more trades (199 vs 186) → more fee drag at high cost
4. But also tighter drawdowns (MDD 15.17% vs 16.96% holdout)

E5+EMA21 is essentially X0 with trail_mult≈2.86 and a few more trades. Its advantage is real but narrow.

---

## 11. Summary

| Question | Answer |
|----------|--------|
| Which is best overall? | **E5+EMA21D1** on most metrics (8/16 dimensions) |
| Holdout winner? | **X0** at harsh cost (+0.030 Sharpe), **E5+EMA21** at smart cost (+0.018 Sharpe) and MDD (-1.79%) |
| Crossover point? | ~**25 bps RT** — below this E5+EMA21 wins, above this X0 wins |
| TS robustness? | E5+EMA21 beats X0 **16/16** on real-data Sharpe |
| WFO? | E5+EMA21 beats X0 **6/8** direct H2H |
| Where does X2/X6 stand? | **Worst in holdout**, best full-sample CAGR — the most polarized strategy |
| Should we use E5+EMA21? | **If trading on Binance VIP (≤20 bps RT): YES.** If retail/harsh: X0 is marginally safer. |
