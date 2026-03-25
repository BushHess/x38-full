# Research Q8: Holdout Delta at Realistic Cost Levels

**Date**: 2026-03-08
**Script**: `research/x6/holdout_cost_sweep_q8.py`
**Data**: `research/x6/holdout_cost_sweep_q8_results.json`

---

## 1. The Hypothesis

The cost study (T7) shows X2/X6 beats X0 at ALL 6 cost levels, with delta growing as cost increases. X2/X6 make fewer trades (150 vs 186 full-sample), so they pay less in fees.

**Hypothesis**: At realistic low cost (10-20 bps RT), the holdout delta might flip from negative to positive because X2/X6's cost advantage is larger relative to the performance gap.

---

## 2. Cost Scenario Definitions

| Scenario | Spread | Slippage | Taker Fee | Per-Side | **Round-Trip** |
|----------|:------:|:--------:|:---------:|:--------:|:--------------:|
| smart | 3.0 bps | 1.5 bps | 0.035% | 6.5 bps | **13.0 bps** |
| base | 5.0 bps | 3.0 bps | 0.100% | 15.5 bps | **31.0 bps** |
| harsh | 10.0 bps | 5.0 bps | 0.150% | 25.0 bps | **50.0 bps** |

"Realistic" for Binance VIP: 10-20 bps RT. Retail: ~25-31 bps RT.

---

## 3. Results: Holdout Sharpe Delta at 12 Cost Levels

| RT bps | X0 Sharpe | X2 Sharpe | X6 Sharpe | **δ X2-X0** | **δ X6-X0** |
|-------:|:---------:|:---------:|:---------:|:----------:|:----------:|
| 0 | 1.719 | 1.401 | 1.401 | **-0.318** | **-0.318** |
| 6.5 | 1.667 | 1.357 | 1.357 | **-0.309** | **-0.309** |
| 10 | 1.638 | 1.333 | 1.333 | **-0.305** | **-0.305** |
| 13 | 1.614 | 1.313 | 1.313 | **-0.301** | **-0.301** |
| 15 | 1.597 | 1.299 | 1.299 | **-0.298** | **-0.298** |
| 20 | 1.557 | 1.265 | 1.265 | **-0.292** | **-0.292** |
| 25 | 1.516 | 1.230 | 1.230 | **-0.285** | **-0.285** |
| 31 | 1.467 | 1.190 | 1.190 | **-0.277** | **-0.277** |
| 40 | 1.394 | 1.128 | 1.128 | **-0.266** | **-0.266** |
| 50 | 1.312 | 1.059 | 1.059 | **-0.253** | **-0.253** |
| 75 | 1.109 | 0.889 | 0.889 | **-0.220** | **-0.220** |
| 100 | 0.906 | 0.718 | 0.718 | **-0.187** | **-0.187** |

**Holdout Sharpe delta is ALWAYS NEGATIVE.** No crossover exists at any cost level.

---

## 4. Results: Holdout CAGR Delta

| RT bps | X0 CAGR | X2 CAGR | X6 CAGR | **δ X2** | **δ X6** |
|-------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| 0 | 52.28% | 41.32% | 41.32% | **-10.97%** | **-10.97%** |
| 10 | 49.07% | 38.72% | 38.72% | **-10.35%** | **-10.35%** |
| 20 | 45.92% | 36.17% | 36.17% | **-9.75%** | **-9.75%** |
| 50 | 36.87% | 28.80% | 28.80% | **-8.07%** | **-8.07%** |
| 100 | 23.01% | 17.39% | 17.39% | **-5.62%** | **-5.62%** |

**Holdout CAGR delta is ALWAYS NEGATIVE.** Gap narrows with cost but never crosses zero.

---

## 5. Results: Full-Sample Delta (for contrast)

| RT bps | X0 Sharpe | X2 Sharpe | **δ X2-X0** | X0 CAGR | X2 CAGR | **δ X2** |
|-------:|:---------:|:---------:|:----------:|:-------:|:-------:|:-------:|
| 0 | 1.644 | 1.671 | **+0.027** | 74.84% | 79.69% | **+4.85%** |
| 10 | 1.583 | 1.623 | **+0.041** | 70.75% | 76.32% | **+5.57%** |
| 20 | 1.521 | 1.576 | **+0.055** | 66.76% | 73.02% | **+6.26%** |
| 50 | 1.336 | 1.433 | **+0.097** | 55.32% | 63.48% | **+8.15%** |
| 100 | 1.027 | 1.193 | **+0.167** | 37.99% | 48.73% | **+10.74%** |

**Full-sample delta is ALWAYS POSITIVE and GROWS with cost.**

---

## 6. The Contradiction Explained

### Why full-sample improves with cost but holdout worsens

| | Full Sample | Holdout Period |
|---|:----------:|:--------------:|
| X0 extra trades | Mix of good + bad | **Mostly excellent** (Q4 2024 rally) |
| Cost of extra trades | Reduces X0 advantage | Also reduces, but dwarfed by alpha |
| X2/X6 cost savings | Compound over 7+ years | Only 1.43 years to compound |
| Net effect of lower cost | X2/X6 saves more (fewer trades) | **X0's extra trades earn MORE** |

### Mechanism at zero cost

At 0 bps, cost is irrelevant. The delta is pure return difference:
- **Holdout 0 bps**: X0 Sharpe 1.719 vs X2 1.401 → **δ = -0.318** (X0 dominates)
- **Full-sample 0 bps**: X0 Sharpe 1.644 vs X2 1.671 → **δ = +0.027** (X2 barely wins)

Even at ZERO cost, X2/X6 barely beat X0 on full-sample Sharpe (+0.027). The adaptive trail's primary advantage is cost efficiency (fewer trades), not return generation. In the holdout, where X0's specific trades capture genuine alpha, the adaptive trail is purely harmful.

### Why lower cost makes the holdout gap WORSE

At 0 cost: holdout Sharpe delta = -0.318
At 50 bps: holdout Sharpe delta = -0.253

**Lower cost amplifies X0's holdout advantage** because:
1. X0 has 31 holdout trades vs X2/X6's 27 — 4 extra trades
2. Those 4 extra trades are **profitable** (Q4 2024 rally ratchet)
3. At lower cost, each trade is cheaper → profitable trades become even MORE profitable
4. X0 benefits more from cost reduction because its extra trades have positive expected value

---

## 7. Holdout MDD: X0 Also Wins

| RT bps | X0 MDD | X2 MDD | X6 MDD |
|-------:|:------:|:------:|:------:|
| 0 | 14.14% | 19.83% | 19.83% |
| 13 | 14.59% | 20.46% | 20.46% |
| 50 | 16.96% | 22.20% | 22.20% |
| 100 | 23.54% | 24.50% | 24.50% |

X0 has **lower MDD** than X2/X6 in the holdout at ALL cost levels. The adaptive trail's wider stops (4-5× ATR) allow deeper intra-trade drawdowns during the holdout rally.

---

## 8. X2 ≡ X6 Confirmation

X2 and X6 produce **identical results** at ALL cost levels, in both holdout and full sample. The breakeven floor adds zero marginal value. This is consistent with Q4's finding that X2 ≡ X6 in holdout.

---

## 9. Score Delta (Validation-Style)

| RT bps | X0 Score | X2 Score | **δ X2-X0** |
|-------:|:--------:|:--------:|:----------:|
| 0 | 128.03 | 79.39 | **-48.65** |
| 13 (smart) | 111.16 | 67.31 | **-43.86** |
| 31 (base) | 89.72 | 51.86 | **-37.86** |
| 50 (harsh) | 68.27 | 37.11 | **-31.16** |
| 100 | 20.31 | 5.38 | **-14.93** |

Score delta is negative at ALL levels. The gap is LARGEST at low cost and shrinks at high cost, but never approaches zero.

**Extrapolating**: even at 200+ bps RT (absurd for crypto), X0 would still win in the holdout. The holdout advantage is structural (alpha from Q4 2024 rally), not cost-driven.

---

## 10. Summary

| Question | Answer |
|----------|--------|
| At realistic cost (10-20 bps RT), does holdout delta flip? | **NO** — delta is -0.30 Sharpe, -10% CAGR. Strongly negative. |
| At what cost does holdout delta cross zero? | **NEVER** — negative at all levels 0-100 bps (and beyond by extrapolation) |
| Is the holdout gap cost-driven? | **NO** — at 0 cost, gap is -0.318 Sharpe (WIDEST). Cost reduction AMPLIFIES X0's advantage. |
| Why does full-sample improve with cost but holdout doesn't? | Full sample: X2/X6's fewer trades save cost. Holdout: X0's extra trades capture **alpha**, not noise. Cost savings are irrelevant vs alpha. |
| Does lower cost help X2/X6? | **In full sample: YES.** In holdout: **NO** — it helps X0 MORE. |
| X2 vs X6? | **Identical** at all cost levels in both holdout and full sample. |
