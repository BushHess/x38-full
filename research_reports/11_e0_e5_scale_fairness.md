# Report 11 — E0 vs E5 Scale Fairness Audit

**Date**: 2026-03-03
**Artifacts**: `artifacts/11_e0_e5_scale_fairness.py`, `artifacts/11_e0_e5_scale_fairness.json`
**Prior claims under audit**: `research/results/e5_validation/e5_validation.json`, MEMORY.md ("E5: MDD 16/16 PROVEN")

---

## 1. Question

Is the E0 vs E5 comparison scale-fair, or does Robust ATR's lower scale make
the trailing stop mechanically tighter — confounding every metric?

## 2. The Two ATR Definitions

| Property | E0 (standard ATR) | E5 (robust ATR) |
|---|---|---|
| True Range input | raw TR | min(TR, Q90 of past 100 bars) |
| Smoothing | Wilder EMA, period 14 | Wilder EMA, period 20 |
| Trail stop | `peak - 3.0 × ATR_std` | `peak - 3.0 × ATR_rob` |

The Q90 cap removes extreme TR values before smoothing. By design, this
produces a lower ATR whenever recent TR exceeds the 90th percentile of
the prior 100 bars — which on BTC H4 data is most of the time.

## 3. Empirical Scale Comparison

Computed over 15,648 post-warmup H4 bars (2019-01-01 to 2026-02-20):

| Statistic | ATR_robust / ATR_standard |
|---|---|
| Mean | 0.9330 |
| Median | 0.9547 |
| Std | 0.1037 |
| P5 | 0.7314 |
| P25 | 0.8874 |
| P75 | 1.0029 |
| P95 | 1.0564 |
| % of bars where robust < standard | **73.4%** |

**The robust ATR is systematically smaller.** At the median, it is 4.5%
lower. At the mean, 6.7% lower. This ratio is stable across years
(2019-2026 annual medians range 0.941-0.964).

The mean stop distance confirms:
- E0: 2,116 USD
- E5: 1,944 USD
- **E5 stop is 8.1% tighter on average**

## 4. Scale-Matched Multiplier

To make E5's average stop distance equal to E0's:

```
trail_matched = 3.0 / median_ratio = 3.0 / 0.9547 = 3.1424
trail_matched = 3.0 / mean_ratio   = 3.0 / 0.9330 = 3.2156
```

Equivalently: **E5 at trail=3.0 has the same effective stop width as
E0 at trail=2.86.** The comparison is not apples-to-apples.

## 5. Results: Original vs Scale-Matched

### 5.1 Win Counts on Real Data (16 timescales)

| Comparison | Sharpe | CAGR | MDD | Calmar | NAV |
|---|---|---|---|---|---|
| E5(3.0) vs E0 | **16/16** | **16/16** | **15/16** | **16/16** | **16/16** |
| E5(3.14) vs E0 | 13/16 | 12/16 | **6/16** | 9/16 | 14/16 |

The MDD advantage collapses from 15/16 to 6/16 — **below chance level.**
CAGR drops from 16/16 to 12/16. Sharpe drops from 16/16 to 13/16.

### 5.2 Canonical Timescale (sp=120) Detail

| Variant | Sharpe | CAGR | MDD | Trades | Avg Hold |
|---|---|---|---|---|---|
| E0 (trail=3.0) | 1.276 | 52.7% | 41.5% | 211 | 38 bars |
| E5 (trail=3.0) | 1.365 | 57.0% | 40.3% | 225 | 34 bars |
| E5 (trail=3.14, matched) | 1.326 | 55.0% | 45.7% | 216 | 36 bars |
| E5 (trail=3.22, matched) | 1.291 | 52.9% | 46.0% | 215 | 37 bars |

At the mean-matched multiplier (3.22), E5 produces Sharpe +0.015 and
CAGR +0.3% over E0 — within noise — while MDD is 4.5pp **worse**.

### 5.3 Trade Count Confirms Mechanism

E5(3.0) consistently makes 5-8% more trades than E0 at every timescale,
with 2-4 bars shorter holding periods. This is the direct signature of
a tighter stop: more frequent exits, shorter trades.

Scale-matching reduces the trade surplus from ~6.5% to ~2.5%.

### 5.4 Sensitivity Sweep (sp=120, E5 with varying trail)

| Trail | Sharpe | CAGR | MDD | vs E0 Sharpe | vs E0 MDD |
|---|---|---|---|---|---|
| 2.50 | 1.313 | +53.0% | 36.5% | +0.037 | +5.0% |
| 3.00 (original) | 1.365 | +57.0% | 40.3% | +0.088 | +1.3% |
| 3.14 (matched median) | 1.326 | +55.0% | 45.7% | +0.049 | -4.2% |
| 3.22 (matched mean) | 1.291 | +52.9% | 46.0% | +0.015 | -4.5% |
| 3.50 | 1.179 | +46.9% | 44.7% | -0.098 | -3.2% |

The MDD advantage sign-flips at trail ~3.04.  The Sharpe advantage
crosses zero at trail ~3.25.  Both crossovers are near the scale-matched
multiplier range (3.14-3.22), confirming that the original advantage is
explained by the scale difference.

### 5.5 Trade-Count Matching

At trail=3.3, E5 matches E0's trade count (211 trades). Under
trade-count matching, E5 yields Sharpe 1.257 vs E0's 1.276 — E5 is
**worse**. This is the strongest evidence that the advantage is mechanical.

## 6. Crossover Analysis (sp=120)

| Metric | Crossover trail_mult (E5 = E0) |
|---|---|
| Sharpe | ~3.25 |
| CAGR | ~3.22 |
| MDD | ~3.04 |

All crossovers cluster near the scale-matched multiplier. Below these
thresholds E5 beats E0; above them E5 loses. The "sweet spot" at trail=3.0
is exactly where the scale mismatch maximally favors E5.

## 7. Why Robust ATR is Systematically Smaller

Two independent effects combine:

1. **Q90 cap removes the upper tail of TR.** By construction,
   `TR_capped = min(TR, Q90(100))` clips the top ~10% of recent
   true-range values. On BTC — where extreme bars are frequent — this
   removes substantial mass from the ATR input.

2. **Period 20 vs 14.** The longer Wilder EMA period means robust ATR
   responds more slowly to volatility spikes. After a spike, robust ATR
   remains depressed for longer. This is a secondary effect but
   contributes to the mean scale difference.

These are design choices, not bugs — but they create a confound when
both variants use the same trail multiplier.

## 8. What E5 Actually Tests (and What It Doesn't)

The original E5 hypothesis: "Robust ATR produces better exit decisions
by being less distorted by extreme bars."

What the comparison actually tests at trail=3.0: "Is a ~5% tighter
trailing stop beneficial?"

**The comparison conflates two effects:**
- The robust ATR mechanism (smoother, less spike-reactive)
- The reduced scale (mechanically tighter stop)

To isolate the robust-ATR mechanism, you need scale-matched comparison.
At scale-matched, E5's advantage is negligible on Sharpe/CAGR and MDD
actually worsens.

## 9. Implications for Current Verdicts

### E5 Validation Study (e5_validation.json)

- **"MDD 16/16 PROVEN (p=1.5e-5)"**: CONFOUNDED. The MDD improvement
  is primarily from the tighter stop, not from robust ATR quality.
  Scale-matched: 6/16 (indistinguishable from chance).

- **"CAGR 0/16"**: On bootstrap paths E5 actually loses CAGR.  On real
  data E5 wins 16/16, but scale-matched drops to 12/16.  The real-data
  CAGR advantage is partially explained by tighter stops capturing gains
  in the specific BTC bull-to-bear sequences of 2019-2026.

- **"Sharpe 0/16"**: Also confounded. Scale-matched real-data: 13/16.
  The fact that original E5 loses Sharpe on bootstrap but wins on real
  data is suspicious — consistent with the tighter stop overfitting to
  the specific sample's trend structure.

### MEMORY.md Entry

Current: "E5: MDD 16/16 PROVEN but Sharpe/CAGR 0/16 — MDD-only insufficient"

Should become: "E5: CONFOUNDED by ATR scale mismatch. At scale-matched
trail, MDD 6/16, Sharpe 13/16, CAGR 12/16 — no provable advantage."

## 10. Conclusion

**The E0 vs E5 comparison is NOT scale-fair.**

The robust ATR is 4.5-6.7% smaller than standard ATR at every timescale
and in every calendar year. At the same trail multiplier (3.0), this
creates a mechanically tighter stop that:

1. Inflates trade frequency by 5-8%
2. Shortens holding periods by 2-4 bars
3. Creates artificial MDD improvement from more frequent exits
4. Produces spurious CAGR improvement on the specific real-data sample

When corrected for scale (trail=3.14-3.22 for E5), the MDD advantage
collapses from PROVEN (16/16) to chance level (6/16), and the CAGR/Sharpe
advantages shrink to within noise.

**The current E5 verdict ("MDD 16/16 PROVEN") is confounded by scale
mismatch and cannot be relied upon as evidence for the robust ATR
mechanism.**

---

*Scale-fairness audit complete. No claims about E5 superiority survive
scale correction.*
