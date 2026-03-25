# Regime-Conditional Trade Comparison: V10 vs V11

**Script:** `out_trade_analysis/regime_comparison.py`
**Data:** `out_trade_analysis/trades_{v10,v11}_{harsh,base}.csv`, `matched_trades_{harsh,base}.csv`
**N_min for confidence:** 10 trades (regimes below this flagged *LC*)
**Report date:** 2026-02-24

---

## 1. Motivation

WFO window-level metrics suffer from 4–11 trades per 6-month window (67% of windows
have <10 trades). Regime-conditional analysis bypasses the window boundary entirely by
grouping trades by **market regime at entry**, pooling across the full 7-year backtest.
This answers: "In which market conditions does V11 differ from V10, and why?"

Two regime labels are analyzed:
- **entry_regime:** D1 regime classification at the bar before trade entry
- **holding_regime_mode:** most common D1 regime during the holding period

---

## 2. Per-Strategy Regime Profile

### 2.1 V10 by Entry Regime (harsh)

| Regime | N | Total PnL | Mean Ret% | Med Ret% | Hit% | MFE% | MAE% | MFE/MAE | Days | Fees |
|--------|---|-----------|-----------|----------|------|------|------|---------|------|------|
| **BULL** | **61** | **$67,048** | 3.07 | 0.34 | 50.8 | 13.23 | 6.75 | **1.96** | 14.3 | $165 |
| NEUTRAL | 21 | $14,105 | 2.37 | -0.39 | 47.6 | 12.21 | 8.41 | 1.45 | 13.0 | $126 |
| CHOP | 14 | $18,163 | 4.44 | 2.23 | 57.1 | 12.10 | 6.60 | 1.83 | 16.7 | $160 |
| TOPPING | 5 *LC* | -$6,060 | -1.54 | -2.92 | 40.0 | 4.76 | 5.18 | 0.92 | 12.0 | $219 |
| SHOCK | 2 *LC* | $770 | -5.31 | -5.31 | 50.0 | 13.67 | 15.75 | 0.87 | 8.8 | $101 |

### 2.2 V11 by Entry Regime (harsh)

| Regime | N | Total PnL | Mean Ret% | Med Ret% | Hit% | MFE% | MAE% | MFE/MAE | Days | Fees |
|--------|---|-----------|-----------|----------|------|------|------|---------|------|------|
| **BULL** | **59** | **$134,231** | **4.45** | 0.43 | 50.8 | 14.57 | 6.78 | **2.15** | 15.1 | $210 |
| NEUTRAL | 20 | -$3,060 | 1.26 | -2.09 | 40.0 | 10.71 | 8.19 | 1.31 | 12.4 | $163 |
| CHOP | 15 | $20,125 | 3.80 | 0.39 | 53.3 | 11.54 | 6.46 | 1.79 | 16.3 | $206 |
| TOPPING | 5 *LC* | -$13,061 | -2.70 | -2.99 | 20.0 | 3.81 | 4.44 | 0.86 | 9.6 | $307 |
| SHOCK | 3 *LC* | -$12,501 | -6.72 | -12.13 | 33.3 | 10.20 | 15.11 | 0.67 | 7.8 | $183 |

### 2.3 Key Observations (Both Strategies)

1. **BULL is the profit engine:** 60–70% of trades, positive total PnL, highest MFE/MAE
   ratio (1.96–2.15). Both V10 and V11 make money here.

2. **TOPPING and SHOCK lose money in both strategies.** TOPPING: MFE/MAE < 1.0 (adverse
   excursion exceeds favorable). SHOCK: extreme MAE (15%+).

3. **CHOP is surprisingly profitable** (hit rate 53–57%, MFE/MAE ~1.8). The VDO-momentum
   filter seems to select favorable chop entries.

4. **NEUTRAL is borderline** — V10 profitable ($14k), V11 negative (-$3k). V11's larger
   sizing amplifies the losers in a mixed-signal regime.

---

## 3. V10 vs V11 Delta by Regime

### 3.1 By Entry Regime — Harsh (total matched Δ = +$40,136)

| Regime | N | Δ Total | Δ Mean | P(V11>) | %Total | Exit Eff | Size Eff | Fee Eff | SR | Conf |
|--------|---|---------|--------|---------|--------|----------|----------|---------|-----|------|
| **BULL** | **56** | **+$37,487** | +$669 | 51.8% | **93.4%** | +$15,735 | +$17,838 | -$2,789 | 1.213 | OK |
| NEUTRAL | 20 | -$165 | -$8 | 40.0% | -0.4% | +$749 | -$1,356 | -$786 | 1.218 | OK |
| CHOP | 14 | +$2,608 | +$186 | 64.3% | 6.5% | -$1,084 | +$4,488 | -$803 | 1.241 | OK |
| TOPPING | 4 | -$1,206 | -$302 | 50.0% | -3.0% | +$1,069 | -$2,833 | -$334 | 1.359 | *LC* |
| SHOCK | 2 | +$1,411 | +$705 | 50.0% | 3.5% | +$1,395 | -$20 | -$9 | 1.042 | *LC* |

### 3.2 By Entry Regime — Base (total matched Δ = -$24,945)

| Regime | N | Δ Total | Δ Mean | P(V11>) | %Total | Exit Eff | Size Eff | Fee Eff | SR | Conf |
|--------|---|---------|--------|---------|--------|----------|----------|---------|-----|------|
| BULL | 55 | +$2,439 | +$44 | 45.5% | -9.8% | -$3,449 | +$4,374 | -$404 | 1.042 | OK |
| **NEUTRAL** | **20** | **-$28,497** | **-$1,425** | 50.0% | **114.2%** | **-$28,702** | -$1,673 | -$97 | 1.056 | OK |
| CHOP | 14 | -$1,062 | -$76 | 64.3% | 4.3% | -$1,517 | +$602 | -$152 | 1.050 | OK |
| TOPPING | 4 | +$683 | +$171 | 50.0% | -2.7% | +$718 | -$417 | -$31 | 1.035 | *LC* |
| SHOCK | 2 | +$1,492 | +$746 | 50.0% | -6.0% | +$1,470 | -$19 | -$6 | 1.042 | *LC* |

*SR = mean V11/V10 size ratio; Exit/Size/Fee Eff = decomposition sums*

### 3.3 By Holding Regime Mode — Harsh (total matched Δ = +$40,136)

| Regime | N | Δ Total | Δ Mean | P(V11>) | %Total | Conf |
|--------|---|---------|--------|---------|--------|------|
| **BULL** | **64** | **+$41,221** | +$644 | 51.6% | **102.7%** | OK |
| NEUTRAL | 17 | -$785 | -$46 | 35.3% | -2.0% | OK |
| CHOP | 11 | +$2,058 | +$187 | 63.6% | 5.1% | OK |
| TOPPING | 3 | -$1,539 | -$513 | 33.3% | -3.8% | *LC* |
| SHOCK | 1 | -$820 | -$820 | 0.0% | -2.0% | *LC* |

### 3.4 By Holding Regime Mode — Base (total matched Δ = -$24,945)

| Regime | N | Δ Total | Δ Mean | P(V11>) | %Total | Conf |
|--------|---|---------|--------|---------|--------|------|
| BULL | 63 | +$2,543 | +$40 | 46.0% | -10.2% | OK |
| **NEUTRAL** | **17** | **-$28,549** | **-$1,679** | 47.1% | **114.4%** | OK |
| CHOP | 11 | -$733 | -$67 | 63.6% | 2.9% | OK |
| TOPPING | 3 | +$320 | +$107 | 33.3% | -1.3% | *LC* |
| SHOCK | 1 | +$1,473 | +$1,473 | 100.0% | -5.9% | *LC* |

---

## 4. Regime-Level Causal Analysis

### 4.1 BULL — The Only Regime That Matters

**Harsh: +$37,487 (93.4% of total delta)**

V11 outperforms V10 in BULL trades through two equal mechanisms:

| Driver | Amount | Explanation |
|--------|--------|-------------|
| Size effect | +$17,838 | V11's mean size ratio = 1.213× (21% larger positions). BULL trades are mostly winners → bigger size amplifies profits |
| Exit effect | +$15,735 | On a few trades, V11's different trail multiplier exits slightly higher. One trade (2023-05-04) converts emergency_dd → trailing_stop (+$11k) |
| Fee drag | -$2,789 | Larger positions → $45/trade more fees on average |

But P(V11 wins) = 51.8% — barely above coin flip. The aggregate advantage comes from
a few large trades where V11's 21% bigger size happened to catch the right exit. The
*median* BULL trade delta is near zero.

**Base: +$2,439 (−9.8% of total delta)**

Under base costs, BULL's advantage collapses from +$37.5k to +$2.4k. The size ratio
drops from 1.213 to 1.042 (only 4% larger), so the sizing amplifier is nearly gone.
The exit effect flips to -$3.4k — V11's exits are slightly worse on average when costs
are lower (trailing stop triggers at marginally different levels).

**Conclusion:** V11's BULL advantage is **cost-regime-dependent** — it requires the harsh
cost scenario's higher penalty structure for V11's sizing to outweigh its occasional
exit degradation.

### 4.2 NEUTRAL — The Regime That Kills V11 (Base)

**Base: -$28,497 (114.2% of total loss)**

This single regime accounts for **more than 100%** of V11's base scenario disadvantage.
The damage is almost entirely exit effect (-$28,702), which traces to one trade:

> **Trade #43 (2021-09-22, NEUTRAL entry):** V10 exited via trailing_stop (locked in
> profits). V11's larger position hit the emergency drawdown threshold earlier →
> emergency_dd exit → -$28,359 swing.

Remove this single trade and NEUTRAL's delta goes from -$28.5k to -$138 (essentially
flat). The remaining 19 NEUTRAL trades split 50/50 between V10 and V11 wins.

**Harsh: -$165 (−0.4% of total delta)**

Under harsh costs, NEUTRAL is approximately flat. The same trade #43 has different
cost dynamics that reduce its outsized impact.

**Conclusion:** NEUTRAL regime is the **vulnerability** — V11's larger sizing occasionally
causes earlier DD exits. With N=20 trades, this is a real sample size, but the result
is dominated by a single outlier.

### 4.3 CHOP — Mild Size Amplification

| | harsh | base |
|---|---|---|
| N | 14 | 14 |
| Δ Total | +$2,608 | -$1,062 |
| Driver | Size effect +$4,488 | Exit effect -$1,517 |

CHOP regime V11 trades are ~24% larger (harsh) / ~5% larger (base). In harsh, the
larger size amplifies the 57% win rate into a positive delta. In base, the sizing
advantage is smaller and exit effect goes negative. **Direction flips between scenarios.**

### 4.4 TOPPING — Deep Dive (N=4–5, *Low Confidence*)

#### 4.4.1 Matched Trade Details

**Harsh (4 matched TOPPING-entry trades):**

| Entry Date | Δ PnL | Exit Eff | Size Eff | V10 Exit | V11 Exit | SR |
|-----------|-------|----------|----------|----------|----------|-----|
| 2023-07-28 | +$482 | +$1,069 | -$947 | trail | trail | 1.363 |
| 2024-06-12 | -$1,224 | $0 | -$1,189 | trail | trail | 1.389 |
| 2025-08-03 | +$454 | $0 | +$310 | trail | trail | 1.343 |
| 2025-08-21 | -$917 | $0 | -$1,008 | trail | trail | 1.342 |

**Base (4 matched TOPPING-entry trades):**

| Entry Date | Δ PnL | Exit Eff | Size Eff | V10 Exit | V11 Exit | SR |
|-----------|-------|----------|----------|----------|----------|-----|
| 2023-07-28 | +$1,418 | +$1,490 | -$117 | trail | trail | 1.033 |
| 2024-06-12 | -$229 | $0 | -$224 | trail | trail | 1.053 |
| 2025-08-03 | +$255 | $0 | +$43 | trail | trail | 1.028 |
| 2025-08-21 | -$760 | -$772 | -$119 | trail | trail | 1.028 |

Plus 1 additional trade entering in CHOP but *holding through TOPPING* (2020-06-29):
both scenarios show +$200–214 delta (size effect from V11 being 6% larger on a winner).

#### 4.4.2 TOPPING Findings

| Question | Answer |
|----------|--------|
| Does V11 change exit reason in TOPPING? | **No.** 0 exit reason changes across 5 trades. Both always trail. |
| Does V11 reduce MAE? | **Marginally.** Δ MAE = -0.19% (harsh), -0.08% (base). Not meaningful. |
| Does V11 reduce tail loss? | **No.** Net delta: -$1,003 harsh, +$897 base. Flips sign. |
| Does V11 achieve "zero damage"? | **No.** V11 TOPPING total PnL: -$13,061 (harsh), -$14,140 (base). V10: -$6,060, -$10,978. V11 loses *more* in TOPPING. |
| Size ratio in TOPPING | **1.30× harsh, 1.04× base.** cycle_late overlay does boost sizing in TOPPING. |
| Why does bigger size hurt? | In TOPPING, most trades are losers (hit rate 20–40%). Bigger size amplifies losses. |

#### 4.4.3 The cycle_late Paradox

V11's `cycle_late_only` overlay activates during identified late-bull/topping phases:
- It increases aggression (0.95 vs ~0.85 base)
- It increases exposure cap (0.90 vs lower base)
- It increases trail multiplier (2.8× vs 3.5× base)

This was designed to be **more aggressive** during late-bull to capture remaining upside
before cycle turns. But the data shows that in TOPPING regime specifically:

1. **Most trades lose** (hit rate 20–40%)
2. **Bigger size amplifies losses** (size effect is negative: -$2,833 harsh)
3. **Exit timing barely changes** (same exit reason 100% of the time)
4. **MFE is low** (3.8–4.8%) while MAE is meaningful (4.4–5.2%)

The overlay **increases risk in the worst regime** rather than protecting against it.
However, with only 4–5 TOPPING trades, this is a directional observation, not a
statistically significant finding.

---

## 5. Regime Contribution Waterfall

### 5.1 Harsh: How V11 Gets to +$40,136

```
BULL     [+$37,487] ████████████████████████████████████████  93.4%
CHOP     [+$2,608]  ███                                       6.5%
SHOCK    [+$1,411]  ██  *LC*                                  3.5%
NEUTRAL  [-$165]    ▏                                        -0.4%
TOPPING  [-$1,206]  █▎  *LC*                                 -3.0%
                    ─────────────────────────────────────────
NET      [+$40,136]                                         100.0%
```

**Story:** V11's advantage is entirely from BULL trades. The cycle_late overlay boosts
position sizing +21% during bull markets, amplifying the ~50.8% win rate's profitable
tail. All other regimes are noise (small absolute values, low trade counts).

### 5.2 Base: How V11 Gets to -$24,945

```
SHOCK    [+$1,492]  ▏  *LC*                                  -6.0%
TOPPING  [+$683]    ▏  *LC*                                  -2.7%
BULL     [+$2,439]  ▏                                        -9.8%
CHOP     [-$1,062]  █▎                                        4.3%
NEUTRAL  [-$28,497] █████████████████████████████████████████ 114.2%
                    ─────────────────────────────────────────
NET      [-$24,945]                                         100.0%
```

**Story:** One catastrophic NEUTRAL trade (#43) accounts for 114% of the total loss.
BULL is mildly positive (+$2.4k) but its sizing amplifier is weaker (SR=1.04 vs 1.21).
Without trade #43, the base scenario would be approximately flat (+$3.5k).

---

## 6. Cross-Scenario Regime Stability

| Regime | harsh Δ | base Δ | Direction stable? | Magnitude stable? |
|--------|---------|--------|-------------------|-------------------|
| **BULL** | +$37,487 | +$2,439 | Yes (both positive) | **NO** (15× difference) |
| NEUTRAL | -$165 | -$28,497 | Yes (both ≈ negative) | **NO** (173× difference) |
| CHOP | +$2,608 | -$1,062 | **NO** (sign flips) | NO |
| TOPPING | -$1,206 | +$683 | **NO** (sign flips) | NO |
| SHOCK | +$1,411 | +$1,492 | Yes | Yes (but N=2, *LC*) |

**No regime shows both stable direction AND stable magnitude.** BULL is directionally
stable but the magnitude collapses 15× from harsh to base. CHOP and TOPPING flip sign.

The instability traces to two factors:
1. **Size ratio is cost-dependent:** harsh SR=1.21, base SR=1.04. Under harsh costs,
   V11's larger sizing amplifies winning trades more; under base, the sizing advantage
   shrinks and the occasional worse exit dominates.
2. **Single outlier in NEUTRAL:** trade #43 exists in both scenarios but its impact
   magnitude varies with cost assumptions.

---

## 7. Small-Sample Warnings

| Regime | N (matched) | Status | Implication |
|--------|-------------|--------|-------------|
| BULL | 55–56 | **OK** | Sufficient for regime-level inference |
| NEUTRAL | 20 | **OK** | Sufficient, but dominated by 1 outlier |
| CHOP | 14 | **Borderline** | Above N_min=10, but just barely. Directional only |
| TOPPING | 4 | ***LOW CONFIDENCE*** | Cannot draw statistical conclusions. 2 wins, 2 losses |
| SHOCK | 2 | ***LOW CONFIDENCE*** | Effectively anecdotal. Long-only in SHOCK is rare |

The only regimes with enough trades for meaningful inference are **BULL** (N=55–56)
and **NEUTRAL** (N=20). All claims about TOPPING and SHOCK are directional hypotheses,
not conclusions.

---

## 8. Answers to Key Questions

### Q: V11 cải thiện ở regime nào?

**Chỉ ở BULL, và chỉ dưới harsh costs.**

| Regime | harsh | base | Verdict |
|--------|-------|------|---------|
| BULL | +$37.5k (OK) | +$2.4k (OK) | Positive but **unstable in magnitude** |
| NEUTRAL | flat | -$28.5k (OK) | V11 **worse** (1 outlier trade) |
| CHOP | +$2.6k (borderline) | -$1.1k (borderline) | **Inconclusive** (sign flips) |
| TOPPING | -$1.2k (*LC*) | +$0.7k (*LC*) | **Inconclusive** (N=4, sign flips) |
| SHOCK | +$1.4k (*LC*) | +$1.5k (*LC*) | **Inconclusive** (N=2) |

V11's BULL advantage mechanism: size ratio 1.21× → bigger positions on the ~51% that
win → larger absolute profits. This is a **leverage effect**, not a strategy improvement.

### Q: V11 có "zero damage" thật không?

**Không.** V11 gây damage nhiều hơn V10 ở 2 regimes:

1. **TOPPING:** V11 tổng PnL = -$13,061 (harsh) vs V10 = -$6,060. V11 thua gấp đôi
   vì sizing 1.30× trên trades mostly thua (hit rate 20%). Cycle_late overlay **tăng
   risk** thay vì giảm.

2. **NEUTRAL (base):** 1 trade outlier (-$28.4k) xảy ra vì V11 position lớn hơn hit
   emergency DD threshold sớm hơn V10.

"Zero damage" claim fails: V11's overlay amplifies losses in losing regimes the same
way it amplifies gains in BULL.

### Q: Nguồn đóng góp chính (regime nào)?

**Harsh:** BULL = 93.4%. Mọi thứ khác là noise.
**Base:** NEUTRAL = 114.2% (1 trade outlier). BULL chỉ +9.8%.

Không có regime nào V11 consistently better across both cost scenarios.

### Q: Vì sao kết quả không ổn định giữa scenarios?

**Size ratio thay đổi:** cycle_late overlay tăng aggression, nhưng aggression effect
phụ thuộc vào cost structure:
- Harsh (50 bps RT): larger sizes giúp nhiều hơn vì fixed costs bị pha loãng
- Base (31 bps RT): larger sizes giúp ít hơn, và occasional DD trigger sớm hơn gây
  thiệt hại lớn

Đây là **cost-regime interaction** — V11's overlay is not regime-adaptive, it's
cost-dependent.

---

## 9. Conclusion

### Regime Contribution Summary

| | BULL | NEUTRAL | CHOP | TOPPING | SHOCK |
|---|---|---|---|---|---|
| N (harsh matched) | 56 | 20 | 14 | 4 *LC* | 2 *LC* |
| harsh Δ | **+$37.5k** | flat | +$2.6k | -$1.2k | +$1.4k |
| base Δ | +$2.4k | **-$28.5k** | -$1.1k | +$0.7k | +$1.5k |
| Driver | Size amplification | 1 outlier trade | Size vs exit | Inconclusive | Inconclusive |
| V11 improves? | Yes (harsh only) | **No** (worse) | Inconclusive | **No** | Inconclusive |
| Stable? | Magnitude unstable | Outlier-dependent | Sign flips | Sign flips | N too small |

### Final Verdict

1. **V11's advantage is a BULL-regime sizing play.** 93.4% of the harsh delta comes
   from BULL trades where V11's 1.21× larger positions amplify the profitable tail.
   This is leverage, not alpha.

2. **V11 does NOT achieve "zero damage" in adverse regimes.** TOPPING PnL is worse
   (-$13k vs -$6k), and NEUTRAL contains a catastrophic outlier where V11's larger
   size triggered early DD exit.

3. **No regime shows stable V11 advantage across cost scenarios.** BULL collapses from
   +$37.5k (harsh) to +$2.4k (base). CHOP and TOPPING flip sign.

4. **The cycle_late overlay's fundamental flaw:** it increases sizing in ALL late-cycle
   regimes (including TOPPING), amplifying both wins and losses symmetrically. A
   genuine risk overlay would reduce sizing or tighten stops in TOPPING — the opposite
   of what cycle_late does.

**Recommendation:** V10 remains the production baseline. If a risk overlay is
pursued, it should:
- **Reduce** (not increase) position sizing when TOPPING is detected
- Use the TOPPING signal as a **defensive** trigger, not an offensive one
- Be tested with ≥20 TOPPING trades before claiming "zero damage"

---

## 10. Data Files

| File | Description |
|------|-------------|
| `out_trade_analysis/regime_comparison.py` | Analysis script |
| `out_trade_analysis/regime_trade_summary_v10_harsh.csv` | V10 per-regime stats (harsh) |
| `out_trade_analysis/regime_trade_summary_v11_harsh.csv` | V11 per-regime stats (harsh) |
| `out_trade_analysis/regime_trade_summary_v10_base.csv` | V10 per-regime stats (base) |
| `out_trade_analysis/regime_trade_summary_v11_base.csv` | V11 per-regime stats (base) |
| `out_trade_analysis/regime_delta_summary_harsh.csv` | V10 vs V11 delta by regime (harsh) |
| `out_trade_analysis/regime_delta_summary_base.csv` | V10 vs V11 delta by regime (base) |
| `out_trade_analysis/regime_topping_deep_dive.json` | TOPPING matched-pair trade details |
