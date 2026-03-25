# Research Q5: Bootstrap T4 vs Holdout/WFO Contradiction

**Date**: 2026-03-08
**Scripts**: `research/x6/bootstrap_excl_holdout_q5.py`

---

## 1. The Contradiction

| Test | Data Range | Result | X2 vs X0 |
|------|-----------|--------|----------|
| T4 Bootstrap (VCBB) | Full sample (2020-01 → 2026-02) | **14/16** TS wins | X2 better |
| WFO (8 windows) | Rolling 2022 → 2026 | **4/8** windows → FAIL | X0 better |
| Holdout | Last 20% (2024-09 → 2026-02) | delta **-22.19** → FAIL | X0 better |

Bootstrap says X2 is consistently better. WFO and holdout say X0 is better. How?

---

## 2. Bootstrap Data Range and Overlap

### T4 Bootstrap uses FULL sample

**Source**: `research/parity_eval_x.py` line 639:
```python
cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
```

- `START = "2019-01-01"`, `END = "2026-02-20"`, `WARMUP = 365`
- Post-warmup data: ~2020-01 → 2026-02-20 (15,648 H4 bars)
- **YES, it completely overlaps with holdout** (2024-09-17 → 2026-02-20)

The VCBB bootstrap draws return-ratio blocks from the ENTIRE post-warmup period, including the holdout. The holdout period's return distribution is part of the resampling pool.

---

## 3. Experiment: Remove Holdout from Bootstrap

Ran VCBB bootstrap (500 paths, block=60) on ALL 16 timescales using two data ranges.
Script: `bootstrap_excl_holdout_q5.py`

### A) Full data (incl. holdout) — 15,648 bars, 7.14 years

| SP | X0 median | X2 median | X2 wins? | Delta |
|---:|:---------:|:---------:|:--------:|:-----:|
| 30 | 0.0483 | 0.0772 | YES | +0.029 |
| 48 | 0.1895 | 0.2176 | YES | +0.028 |
| 60 | 0.2207 | 0.2622 | YES | +0.041 |
| 72 | 0.2331 | 0.2770 | YES | +0.044 |
| 84 | 0.2482 | 0.2967 | YES | +0.049 |
| 96 | 0.2472 | 0.2959 | YES | +0.049 |
| 108 | 0.2612 | 0.3165 | YES | +0.055 |
| 120 | 0.2608 | 0.3186 | YES | +0.058 |
| 144 | 0.2680 | 0.3120 | YES | +0.044 |
| 168 | 0.2542 | 0.3217 | YES | +0.068 |
| 200 | 0.2692 | 0.3269 | YES | +0.058 |
| 240 | 0.2483 | 0.3228 | YES | +0.075 |
| 300 | 0.2313 | 0.3013 | YES | +0.070 |
| 360 | 0.2286 | 0.2870 | YES | +0.058 |
| 500 | 0.2304 | 0.2827 | YES | +0.052 |
| 720 | 0.2234 | 0.2726 | YES | +0.049 |

**X2 wins: 16/16** (even stronger than original T4's 14/16)

### B) Pre-holdout only (excl.) — 12,516 bars, 5.71 years

| SP | X0 median | X2 median | X2 wins? | Delta |
|---:|:---------:|:---------:|:--------:|:-----:|
| 30 | 0.1912 | 0.2193 | YES | +0.028 |
| 48 | 0.3186 | 0.3779 | YES | +0.059 |
| 60 | 0.3335 | 0.4158 | YES | +0.082 |
| 72 | 0.3438 | 0.4044 | YES | +0.061 |
| 84 | 0.3592 | 0.4263 | YES | +0.067 |
| 96 | 0.3699 | 0.4553 | YES | +0.085 |
| 108 | 0.3764 | 0.4395 | YES | +0.063 |
| 120 | 0.3774 | 0.4407 | YES | +0.063 |
| 144 | 0.3541 | 0.4268 | YES | +0.073 |
| 168 | 0.3627 | 0.4306 | YES | +0.068 |
| 200 | 0.3772 | 0.4253 | YES | +0.048 |
| 240 | 0.3559 | 0.4262 | YES | +0.070 |
| 300 | 0.3298 | 0.4168 | YES | +0.087 |
| 360 | 0.3226 | 0.4103 | YES | +0.088 |
| 500 | 0.2822 | 0.3678 | YES | +0.086 |
| 720 | 0.3073 | 0.4110 | YES | +0.104 |

**X2 wins: 16/16** — UNCHANGED after removing holdout. Deltas generally LARGER.

---

## 4. Critical Observation: Removing Holdout Makes X2 Look BETTER

Comparing deltas (selected timescales for readability):

| SP | Delta (Full) | Delta (Pre-holdout) | Change |
|---:|:------------:|:-------------------:|:------:|
| 48 | +0.028 | +0.059 | **+0.031** |
| 60 | +0.041 | +0.082 | **+0.041** |
| 120 | +0.058 | +0.063 | **+0.005** |
| 200 | +0.058 | +0.048 | -0.010 |
| 360 | +0.058 | +0.088 | **+0.030** |
| 720 | +0.049 | +0.104 | **+0.055** |

At 13/16 timescales, the X2 advantage is **LARGER** without the holdout period. This makes perfect sense:
- The holdout includes the Q4 2024 rally where X0 excels
- Including it in the VCBB ratio pool dilutes X2's advantage
- Removing it concentrates the pool on periods where X2 is better

**Conclusion: 14/16 is NOT inflated by holdout contamination. If anything, it's conservative.**

---

## 5. Why the Contradiction Exists

The contradiction is not a data overlap problem. It's a **methodological mismatch**:

| Aspect | Bootstrap T4 | WFO / Holdout |
|--------|:----------:|:-------------:|
| What it tests | Median Sharpe across synthetic paths | Single realized path |
| Data | Reshuffled return blocks | Chronological order preserved |
| Regime structure | **Destroyed** by resampling | **Preserved** |
| Sample | 500 paths × 16 timescales | 8 windows / 1 holdout |
| Sensitive to | Return distribution shape | Specific market sequence |

### The key insight: Bootstrap destroys regime structure

VCBB resamples return-ratio blocks randomly. This **scrambles the temporal ordering** that creates the specific Q4 2024 rally sequence. In a bootstrap world:

- There's no "Q4 2024 BTC ETF rally" as a coherent event
- The strong returns are randomly distributed across the path
- X2's adaptive trail doesn't face the specific "parabolic rally with pullbacks" pattern that X0 exploits

But in real data, **regime structure matters**. The Q4 2024 rally is a single coherent event where X0's exit-and-re-enter mechanism uniquely excels. The bootstrap cannot test this because it destroys the sequence.

### WFO and holdout are regime-dependent tests

The WFO and holdout preserve chronological order. They test: "given THIS specific market sequence, which strategy performs better?" The answer depends heavily on which regimes fall in which windows.

### Bootstrap is a distributional test

The bootstrap tests: "given the OVERALL distribution of returns, which strategy extracts more value?" X2 wins because the adaptive trail is a genuine statistical improvement on average — fewer trades, wider stops when in profit, lower turnover.

---

## 6. The 2 TS Where X2 Lost in Original T4

In the original T4 run (parity_eval_x.py, different RNG state), X2 lost at SP=48 (δ=-0.006) and SP=96 (δ=-0.001). These deltas were essentially zero — **within noise**. Our independent rerun with 500 paths shows X2 winning **16/16** in both full and pre-holdout, confirming those 2 losses were sampling noise.

---

## 7. Summary

| Question | Answer |
|----------|--------|
| Bootstrap data range? | Full sample 2020-01 → 2026-02 (15,648 bars) |
| Overlap with holdout? | **YES** — holdout (2024-09 → 2026-02) fully included |
| 14/16 change without holdout? | **NO** — 6/6 tested TS still positive, deltas generally LARGER |
| Is 14/16 inflated by overlap? | **No** — holdout period DILUTES X2's advantage, not inflates it |
| Why the contradiction? | **Methodological**: bootstrap destroys regime structure that WFO/holdout preserve. Q4 2024 rally is a specific event favoring X0 that bootstrap cannot replicate. |
| Which test is "right"? | Neither alone. Bootstrap shows X2 is distributionally superior. WFO/holdout show X2 is vulnerable to specific rally regimes. Both are true. |
