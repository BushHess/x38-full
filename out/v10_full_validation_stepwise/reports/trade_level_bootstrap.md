# Trade-Level Bootstrap Inference: V10 vs V11

**Script:** `out_trade_analysis/bootstrap_paired.py`
**Data:** `out_trade_analysis/matched_trades_{harsh,base}.csv`
**Bootstrap:** 10,000 resamples, seed=20260224 (reproducible)
**Report date:** 2026-02-24

---

## 1. Why Bootstrap at Trade Level?

WFO round-by-round comparison allocates ~96 matched trades across 10 OOS windows
(6 months each). The resulting trades-per-window distribution:

| Window | harsh | base |
|--------|-------|------|
| 2019H1 | 4 | 4 |
| 2019H2 | 10 | 10 |
| 2020H1 | 8 | 8 |
| 2020H2 | 7 | 7 |
| 2021H1 | 7 | 7 |
| 2021H2 | 10 | 10 |
| 2022H1–H2 | 0 | 0 |
| 2023H1 | 4 | 4 |
| 2023H2 | 7 | 7 |
| 2024H1 | 11 | 11 |
| 2024H2 | 10 | 10 |
| 2025H1 | 9 | 9 |
| 2025H2 | 9 | 8 |

**Key problem:** 8 of 12 windows have fewer than 10 trades. The minimum is 4 trades
(2019H1, 2023H1). Two entire windows (2022H1, 2022H2) have zero trades — the bear
market produced no entries. With 4–11 trades per window, a single outlier trade can
swing the window-level mean by thousands of dollars, making window-level statistics
unreliable.

**Solution:** Bootstrap at the trade level, using correlation-aware resampling to
preserve temporal structure while pooling all ~96 matched trades into a single
inference.

---

## 2. Bootstrap Methods

### 2.1 Method A: Cluster Bootstrap by Semi-Annual Window

Resample the 12 semi-annual windows **with replacement**. Each resampled window
contributes all its trades. This preserves:
- Intra-window correlation (trades in the same market regime stay grouped)
- Window-level heterogeneity (some windows are bull, some bear/chop)
- Unequal window sizes (natural)

For each of 10,000 bootstrap samples: draw 12 windows (with replacement) → pool all
trades → compute mean Δ PnL.

### 2.2 Method B: Moving Block Bootstrap

Sort trades by entry timestamp. Resample contiguous **blocks of K trades** with
replacement to preserve local temporal autocorrelation. Sensitivity tested at
K = {5, 8, 12} trades per block.

For each of 10,000 samples: draw ⌈N/K⌉ blocks of K consecutive trades (random start
positions) → truncate to N trades → compute mean Δ PnL.

### 2.3 IID Bootstrap (Reference)

Standard nonparametric bootstrap — resample individual trades with replacement,
assuming independence. Included as a baseline; expected to understate variance if
trades are autocorrelated.

---

## 3. Autocorrelation Diagnostic

| Metric | harsh | base |
|--------|-------|------|
| Lag-1 autocorrelation (Δ PnL) | **0.182** | **0.059** |

Harsh scenario shows mild positive autocorrelation (18.2%) — consecutive trade deltas
tend to share the same sign, likely because V11's cycle_late overlay activates for
clusters of trades during the same regime. Base scenario has near-zero autocorrelation.

This justifies using cluster/block bootstrap rather than naïve IID: the IID method may
underestimate the true standard error in the harsh scenario.

---

## 4. Results

### 4.1 Harsh Scenario (N=96 matched trades)

| Method | P(V11 > V10) | 95% CI (mean Δ PnL) | Boot SE |
|--------|-------------|---------------------|---------|
| **Cluster** | **0.9824** | **[$24, $880]** | $220 |
| Block K=5 | 0.9597 | [-$50, $1,033] | $277 |
| **Block K=8** | **0.9751** | **[$2, $1,023]** | $265 |
| Block K=12 | 0.9928 | [$66, $1,014] | $246 |
| IID (ref) | 0.9635 | [-$29, $941] | $249 |

**Observed:** mean Δ = +$418/trade, total Δ = +$40,136

**Interpretation:** Under harsh costs, V11 shows a statistically meaningful advantage.
The cluster bootstrap 95% CI **excludes zero** [$24, $880], and P(V11 > V10) = 98.2%.
The block bootstrap at K=8 barely excludes zero at 95% [$2, $1,023]. All methods agree
on the direction: V11 wins with >96% probability.

However, the CI is wide — the true mean delta could be anywhere from $24 to $880 per
trade. Over 96 trades, this translates to a total advantage of $2.3k to $84.5k — a 3×
uncertainty range.

### 4.2 Base Scenario (N=95 matched trades)

| Method | P(V11 > V10) | 95% CI (mean Δ PnL) | Boot SE |
|--------|-------------|---------------------|---------|
| **Cluster** | **0.2417** | **[-$1,010, $339]** | $351 |
| Block K=5 | 0.2717 | [-$1,063, $342] | $366 |
| **Block K=8** | **0.3213** | **[-$972, $364]** | $351 |
| Block K=12 | 0.3283 | [-$940, $401] | $348 |
| IID (ref) | 0.2411 | [-$1,032, $287] | $347 |

**Observed:** mean Δ = -$263/trade, total Δ = -$24,945

**Interpretation:** Under base costs, V11 **loses**. The 95% CI comfortably includes
zero in all methods, and P(V11 > V10) = 24% — meaning V10 wins with ~76% probability.
The CI spans [-$1,010, +$339], reflecting the high variance from the single outlier
trade (#43, 2021-09-22, Δ = -$28,359).

### 4.3 Return-Based Bootstrap (Cluster)

| Scenario | P(V11 > V10) | 95% CI (mean Δ return %) |
|----------|-------------|--------------------------|
| harsh | **0.9867** | [+0.03%, +0.87%] |
| base | **0.2186** | [-1.48%, +0.28%] |

Consistent with PnL-based results. Harsh shows a small positive return edge; base
shows V10 winning.

---

## 5. Block Size Sensitivity

The moving block bootstrap was tested at K = 5, 8, 12 to check robustness to the
autocorrelation assumption:

### Harsh

| Block K | P(V11>V10) | CI Lo | CI Hi | Boot SE |
|---------|-----------|-------|-------|---------|
| 5 | 0.960 | -$50 | $1,033 | $277 |
| 8 | 0.975 | $2 | $1,023 | $265 |
| 12 | 0.993 | $66 | $1,014 | $246 |

P(V11 > V10) increases with block size (0.96 → 0.99) because larger blocks better
capture the positive clustering of V11's winning streaks. All three are >95%.

### Base

| Block K | P(V11>V10) | CI Lo | CI Hi | Boot SE |
|---------|-----------|-------|-------|---------|
| 5 | 0.272 | -$1,063 | $342 | $366 |
| 8 | 0.321 | -$972 | $364 | $351 |
| 12 | 0.328 | -$940 | $401 | $348 |

P(V11 > V10) stays well below 50% across all block sizes. The conclusion is robust:
V10 wins under base costs.

---

## 6. Why WFO Round-by-Round Looks Jumpy

### 6.1 Arithmetic of Small Windows

With mean 8.0 trades/window (min 4, max 11), the per-window mean delta has a standard
error of:

```
SE_window = σ_delta / √n_window
```

Where σ_delta ≈ $2,442 (harsh) or $3,369 (base) from the paired analysis. For a
window with 4 trades:

```
SE_4 = $2,442 / √4 = $1,221 per trade
```

This means a window-level mean delta of +$500 has a 95% CI of [-$1,893, +$2,893] —
the signal is completely buried in noise. Even the best window (11 trades) has
SE = $736, still large relative to the $418 mean effect.

### 6.2 Outlier Domination

The paired analysis showed that 3 trades drive 78% of V11's harsh advantage, and 1
trade drives 114% of the base disadvantage. When these outlier trades land in a
particular WFO window, they dominate that window's result. When they don't, the
window shows zero effect. This creates the "jumping" pattern — some windows show
V11 winning big, most show no difference, a few show V10 winning.

### 6.3 Missing Windows

The 2022 bear market produced zero trade entries (long-only strategy in a downturn).
This eliminates 2 of 10 WFO windows entirely, reducing effective degrees of freedom
to 8 and further amplifying the jump-to-jump variance.

### 6.4 Quantified Instability

| Metric | Value |
|--------|-------|
| Windows with <10 trades | 8 / 12 (67%) |
| Empty windows (bear market) | 2 (2022H1, 2022H2) |
| Min trades/window | 4 |
| σ (trade delta, harsh) | $2,442 |
| SE of window mean (4 trades) | $1,221 |
| SE of window mean (8 trades) | $863 |
| True signal (harsh mean delta) | $418 |
| Signal-to-noise (8 trades) | 0.48 |

The signal-to-noise ratio per window is **0.48** — meaning random variation is 2×
the signal. This is why WFO window-level results appear to jump between V11-wins and
V10-wins randomly.

---

## 7. Is the Trade-Level Aggregated Effect Stable?

### 7.1 Within-Scenario: Yes (Conditionally)

Given a fixed cost scenario, the bootstrap distributions are well-behaved:
- Cluster and block methods agree (P values within ±3pp)
- Block size sensitivity is modest (no qualitative change)
- IID results are close, suggesting limited autocorrelation impact

### 7.2 Across Scenarios: No

This is the critical instability:

| Metric | harsh | base | Stable? |
|--------|-------|------|---------|
| Observed mean Δ | +$418 | -$263 | **NO** (sign flips) |
| P(V11 > V10) | 98.2% | 24.2% | **NO** (98% → 24%) |
| 95% CI includes 0? | Barely no | Yes | **NO** |
| Total Δ | +$40,136 | -$24,945 | **NO** (sign flips) |

The effect **reverses direction** when cost assumptions change from 50 bps (harsh) to
31 bps (base). This is not a matter of statistical power — the sign of the effect
literally flips.

**Why it flips:** Under harsh costs, V11's larger positions (+22% mean size ratio)
amplify winners more than losers, because higher costs penalize the numerous small
losing exits proportionally more. Under base costs, the outlier trade #43
(2021-09-22) becomes the dominant factor: V11's larger position hit the emergency DD
threshold earlier, producing a -$28k swing that overwhelms all other gains.

### 7.3 Verdict on Stability

| Test | Result |
|------|--------|
| Bootstrap CI excludes 0 (both scenarios) | **FAIL** (only harsh) |
| P(V11>V10) > 95% (both scenarios) | **FAIL** (only harsh) |
| Effect direction consistent across scenarios | **FAIL** (sign flips) |
| Effect robust to 1-trade removal | **FAIL** (base: ±$28k from 1 trade) |

The trade-level aggregated effect is **not stable**. It passes within the harsh
scenario but fails the critical cross-scenario consistency test.

---

## 8. Answers to Key Questions

### Q: V11 khác biệt có đáng tin không?

**Không.** Bootstrap chứng minh 3 điều:

1. **Harsh: V11 thắng (P=98.2%)** — nhưng CI rất rộng [$24, $880/trade], và chủ yếu
   do 3 outlier trades drive 78% of advantage.

2. **Base: V10 thắng (P=75.8%)** — 1 trade (#43) chiếm 114% total loss, CI chứa 0.

3. **Kết quả đảo chiều giữa scenarios** — không thể kết luận V11 tốt hơn khi thay đổi
   cost assumptions từ 31→50 bps đã đảo hướng.

### Q: Vì sao WFO round-by-round nhìn "nhảy"?

**Signal-to-noise = 0.48 per window.** Với 4–11 trades/window và σ = $2,442/trade,
mỗi window có SE > signal. Outlier trades rơi vào window nào thì window đó "nhảy" —
đây là sampling noise, không phải real regime effect.

### Q: Trade-level aggregated effect có ổn định không?

**Ổn định trong 1 scenario, nhưng không ổn định giữa scenarios.** Harsh cho P=98%;
base cho P=24%. Đây là **scenario fragility**, không phải statistical significance.
Một strategy edge thật phải robust ở cả 2 cost assumptions.

---

## 9. Conclusion

### Bootstrap Summary Table

| | harsh | base |
|---|---|---|
| N matched | 96 | 95 |
| Mean Δ PnL | +$418 | -$263 |
| P(V11>V10) cluster | **98.2%** | **24.2%** |
| P(V11>V10) block-8 | 97.5% | 32.1% |
| 95% CI cluster | [$24, $880] | [-$1,010, $339] |
| Contains 0? | No | Yes |
| Lag-1 autocorr | 0.182 | 0.059 |

### Final Verdict

The bootstrap analysis **does not support promoting V11** over V10:

1. **Within harsh:** V11 shows a statistically meaningful edge (P=98%, CI excludes 0),
   but driven by 3 outlier trades and a +22% sizing amplifier.

2. **Within base:** V10 wins (P=76%), with a single catastrophic trade dominating.

3. **Cross-scenario:** The effect sign flips — this is the disqualifying finding.
   A real edge should persist (possibly shrink) under different cost assumptions,
   not reverse.

4. **WFO jumpiness explained:** 67% of windows have <10 trades, and the per-window
   signal-to-noise ratio is 0.48. Window-level comparison is statistically meaningless
   at this sample size.

**Recommendation:** V10 remains the production baseline. The apparent V11 advantage
under harsh costs is not generalizable. Trade-level bootstrap confirms and quantifies
what the paired analysis found qualitatively: V11's effect is unstable, concentrated,
and scenario-dependent.

---

## 10. Data Files

| File | Description |
|------|-------------|
| `out_trade_analysis/bootstrap_paired.py` | Bootstrap analysis script (reproducible) |
| `out_trade_analysis/bootstrap_trade_level_harsh.csv` | 10,000 bootstrap sample means (3 methods) |
| `out_trade_analysis/bootstrap_trade_level_base.csv` | Same for base scenario |
| `out_trade_analysis/bootstrap_summary.json` | Full results: P, CI, window diagnostics |
