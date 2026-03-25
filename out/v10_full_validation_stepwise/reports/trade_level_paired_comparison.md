# Trade-Level Paired Comparison: V10 vs V11

**Script:** `out_trade_analysis/paired_analysis.py`
**Data:** `out_trade_analysis/trades_v10_*.csv`, `out_trade_analysis/trades_v11_*.csv`
**Scenarios:** harsh (50 bps RT), base (31 bps RT)
**Report date:** 2026-02-24

---

## 1. Motivation

WFO round-by-round analysis suffers from low trade counts per 6-month window (60%
rejection rate at <10 trades). This trade-level paired analysis bypasses WFO windows
entirely by matching individual trades between V10 and V11, then decomposing per-trade
PnL differences into **exit effect** vs **size effect**.

V10 and V11 share the same core entry logic (VDO-momentum), so most trades enter at the
same bar. V11's cycle_late_only overlay modifies risk parameters (aggression, trail
multiplier, exposure cap) during late-bull phases, creating measurable per-trade deltas.

---

## 2. Matching Results

### 2.1 Match Rate

| Metric | harsh | base |
|--------|-------|------|
| V10 trades | 103 | 100 |
| V11 trades | 102 | 102 |
| **Matched** | **96 (93.2%)** | **95 (95.0%)** |
| V10-only | 7 | 5 |
| V11-only | 6 | 7 |
| **PASS** (≥80%) | **YES** | **YES** |

**Matching method:** Exact `entry_ts` match (pass 1), then ±1 H4 bar (4h) tolerance
(pass 2). Tolerance catches cases where V11's different exit timing shifts the next
trade's entry by one bar.

### 2.2 Unmatched Trades Explained

Unmatched trades occur when V11's cycle_late modifies exit timing enough to shift a
subsequent entry by >1 bar, creating a different trade sequence. In all cases, the V10
and V11 unmatched trades are near-neighbors in time (typically 3-6 bars apart) — they
represent the same market move captured at slightly different timestamps.

| Scenario | V10-only PnL | V11-only PnL | Δ (V11 − V10) |
|----------|-------------|-------------|----------------|
| harsh | +$11,509 | +$3,083 | **-$8,426** (V10 wins unmatched) |
| base | -$9,130 | +$8,525 | **+$17,656** (V11 wins unmatched) |

---

## 3. Per-Trade Delta Distribution

### 3.1 Delta Net PnL (matched trades)

| Statistic | harsh | base |
|-----------|-------|------|
| N | 96 | 95 |
| **Sum** | **+$40,136** | **-$24,945** |
| Mean | +$418 | -$263 |
| **Median** | **+$0.96** | **$0.00** |
| Std | $2,442 | $3,369 |
| P10 | -$1,418 | -$878 |
| P90 | +$2,610 | +$897 |
| Min | -$4,092 | -$28,359 |
| Max | +$12,945 | +$7,221 |

### 3.2 Key Observation: Median ≈ 0

The **median delta is effectively zero** in both scenarios. V11's advantage (when it
exists) comes from the tails — a few large winners pulling the mean, not a consistent
per-trade improvement. This confirms the WFO finding that V11 is not systematically
better than V10.

### 3.3 P(Δ PnL > 0)

| Scenario | P(Δ > 0) | N positive | N negative | N zero |
|----------|----------|------------|------------|--------|
| harsh | **51.0%** | 49 | 45 | 2 |
| base | **49.5%** | 47 | 46 | 2 |

V11 wins approximately half of matched trades. No systematic edge.

### 3.4 Size Ratio (V11/V10 notional)

| Statistic | harsh | base |
|-----------|-------|------|
| Mean | **1.221** | **1.046** |
| Median | 1.146 | 1.037 |
| P10 | 0.998 | 0.995 |
| P90 | 1.448 | 1.109 |

V11 takes **larger positions** on average (22% larger in harsh, 5% in base). This is
because V11's `cycle_late_aggression=0.95` is higher than V10's base aggression in some
regimes, and the cycle_late overlay boosts sizing during identified late-bull windows.

### 3.5 Exit Reason Consistency

| Metric | harsh | base |
|--------|-------|------|
| Same exit reason | **96.9%** | **95.8%** |
| Different exit reason | 3.1% (3 trades) | 4.2% (4 trades) |

V10 and V11 almost always exit for the same reason. The cycle_late overlay rarely
changes the exit mechanism.

**Exit transitions (harsh):**

| V10 → V11 | Count |
|-----------|-------|
| trailing_stop → trailing_stop | 60 |
| emergency_dd → emergency_dd | 31 |
| fixed_stop → fixed_stop | 2 |
| emergency_dd → trailing_stop | 1 |
| trailing_stop → emergency_dd | 1 |
| fixed_stop → emergency_dd | 1 |

---

## 4. Decomposition

### 4.1 Method

For each matched pair (V10 trade, V11 trade), decompose delta_net_pnl into 4 components:

| Component | Formula | Interpretation |
|-----------|---------|----------------|
| **Exit effect** | V10_qty × (V11_exit_price − V10_exit_price) | What if V10 kept its size but got V11's exit? |
| **Size effect** | (V11_qty − V10_qty) × (V10_exit_price − V10_entry_price) | What if V11 traded the same as V10 but bigger/smaller? |
| **Fee effect** | −(V11_fees − V10_fees) | Cost of larger notional |
| **Interaction** | residual: total − exit − size − fee | Cross-term (bigger size × different exit) |

This is a **first-order Taylor decomposition** (exact for linear, approximate for
nonlinear). The interaction term captures the cross-effect of simultaneously changing
both size and exit.

### 4.2 Results

| Component | harsh | harsh % | base | base % |
|-----------|-------|---------|------|--------|
| **Total Δ** | **+$40,136** | 100% | **-$24,945** | 100% |
| Exit effect | +$17,863 | 44.5% | -$31,479 | 126.2% |
| Size effect | +$18,117 | 45.1% | +$2,866 | -11.5% |
| Fee effect | -$4,722 | -11.8% | -$692 | 2.8% |
| Interaction | +$8,877 | 22.1% | +$4,360 | -17.5% |

### 4.3 Interpretation

**Harsh scenario (V11 wins +$40k):**
- Exit effect (+$17.9k, 45%) and size effect (+$18.1k, 45%) contribute roughly equally
- V11's larger positions (+22% mean) amplify winning trades
- V11's different exit timing occasionally converts emergency_dd → trailing_stop (trade #53: +$11.7k)
- Fee drag (-$4.7k) partially offsets the larger-size gains

**Base scenario (V11 loses -$25k):**
- Exit effect dominates: **-$31.5k** (126% of total loss)
- Size effect is slightly positive (+$2.9k) — larger positions help on average
- **One outlier trade (#43, 2021-09-22) accounts for -$28.4k** of the exit effect
  - V10: trailing_stop exit (locked in profit)
  - V11: emergency_dd exit (position too large → hit DD threshold earlier)
  - Without this single trade, base scenario would be approximately flat

### 4.4 Critical Finding: Scenario Instability

| Question | harsh | base |
|----------|-------|------|
| V11 wins? | +$40k | -$25k |
| Main driver | Size + exit (equal) | 1 outlier trade |
| Consistent? | **NO** | **NO** |

V11's advantage **reverses between cost scenarios**. This is because:
1. Higher costs (harsh) amplify V11's sizing advantage on winners
2. Lower costs (base) make V10's exits more profitable (trailing_stop triggers matter more)
3. A single outlier trade at lower costs dominates the result

---

## 5. Regime Breakdown

### 5.1 Delta by Entry Regime (harsh)

| Regime | N | Sum Δ PnL | Mean Δ | N+ | N− |
|--------|---|-----------|--------|----|----|
| **BULL** | 56 | **+$37,487** | +$669 | 29 | 27 |
| CHOP | 14 | +$2,608 | +$186 | 9 | 5 |
| NEUTRAL | 20 | -$165 | -$8 | 8 | 10 |
| SHOCK | 2 | +$1,411 | +$705 | 1 | 1 |
| TOPPING | 4 | -$1,206 | -$302 | 2 | 2 |

### 5.2 Delta by Entry Regime (base)

| Regime | N | Sum Δ PnL | Mean Δ | N+ | N− |
|--------|---|-----------|--------|----|----|
| BULL | 55 | +$2,440 | +$44 | 25 | 30 |
| CHOP | 14 | -$1,062 | -$76 | 9 | 5 |
| **NEUTRAL** | 20 | **-$28,497** | **-$1,425** | 10 | 8 |
| SHOCK | 2 | +$1,492 | +$746 | 1 | 1 |
| TOPPING | 4 | +$683 | +$171 | 2 | 2 |

V11's advantage is concentrated in **BULL regime** trades (harsh: +$37.5k of +$40.1k
total). In base scenario, the NEUTRAL regime outlier (-$28.5k from trade #43) erases
all BULL gains.

---

## 6. Top 10 Trades by Impact

### 6.1 Largest Positive Deltas (V11 wins, harsh)

| # | Entry Date | Δ PnL | Exit Effect | Size Effect | V10 Exit | V11 Exit | Regime |
|---|-----------|-------|-------------|-------------|----------|----------|--------|
| 1 | 2024-11-04 | +$12,945 | $0 | +$12,003 | trail | trail | BULL |
| 2 | 2023-05-04 | +$11,658 | +$11,034 | -$782 | **emerg_dd** | **trail** | BULL |
| 3 | 2024-02-25 | +$6,795 | $0 | +$6,018 | trail | trail | BULL |
| 4 | 2024-01-23 | +$6,562 | $0 | +$6,608 | trail | trail | CHOP |
| 5 | 2024-10-11 | +$5,563 | +$2,821 | +$1,516 | trail | trail | BULL |

**Pattern:** 4 of top 5 are **pure size effect** (exit_effect ≈ 0, same exit reason).
V11's larger positions amplify winning trailing_stop exits. Trade #2 is the exception:
V11 avoided emergency_dd and rode the trade to trailing_stop (+$11k exit effect).

### 6.2 Largest Negative Deltas (V10 wins, harsh)

| # | Entry Date | Δ PnL | Exit Effect | Size Effect | V10 Exit | V11 Exit | Regime |
|---|-----------|-------|-------------|-------------|----------|----------|--------|
| 1 | 2025-02-04 | -$4,092 | $0 | -$4,030 | emerg_dd | emerg_dd | CHOP |
| 2 | 2025-01-24 | -$3,295 | $0 | -$3,228 | emerg_dd | emerg_dd | CHOP |
| 3 | 2024-08-20 | -$2,734 | -$2,125 | +$551 | trail | trail | BULL |
| 4 | 2025-10-19 | -$2,480 | -$1,999 | +$183 | trail | trail | NEUTRAL |
| 5 | 2025-02-26 | -$2,467 | $0 | -$2,482 | emerg_dd | emerg_dd | BULL |

**Pattern:** Top losers are **pure size effect** — V11's larger positions amplify
emergency_dd losses. Trades #1-2 are during the 2025-Q1 correction where V11's
bigger size made the emergency_dd exits more expensive.

---

## 7. Concentration Analysis

### 7.1 How Many Trades Drive the Delta?

**Harsh scenario (total: +$40,136):**

| Top N trades | Sum Δ | % of total | Trades |
|-------------|-------|-----------|--------|
| Top 1 | +$12,945 | 32.3% | 2024-11-04 (size) |
| Top 3 | +$31,397 | 78.2% | + 2023-05-04, 2024-02-25 |
| Top 5 | +$43,759 | 109.0% | + 2024-01-23, 2024-10-11 |
| Top 10 | +$61,123 | 152.3% | (offset by bottom trades) |
| Bottom 5 | -$14,588 | -36.3% | Losers partially offset |

The top 3 trades alone contribute 78% of the total advantage. Remove them and the
delta would be +$8.7k (a 78% reduction).

**Base scenario (total: -$24,945):**

| Top N trades | Sum Δ | % of total |
|-------------|-------|-----------|
| Bottom 1 | -$28,359 | 113.7% | 2021-09-22 (1 trade!) |

A single trade (#43) accounts for **113.7%** of the entire base scenario loss. Without
it, V11 would be +$3.4k ahead.

### 7.2 Verdict on Concentration

V11's advantage is **extremely concentrated**: 3 trades in harsh, 1 outlier in base.
This is not a systematic edge — it's a few lucky/unlucky trade outcomes that happen to
align differently between the two strategies.

---

## 8. Answers to Key Questions

### Q: V11 thắng do cái gì — exit hay size?

**Both, in roughly equal measure (harsh), but unstable across scenarios:**

| Scenario | Exit Effect | Size Effect | Dominant |
|----------|-------------|-------------|----------|
| harsh | +$17.9k (45%) | +$18.1k (45%) | 50/50 |
| base | -$31.5k (126%) | +$2.9k (-12%) | Exit dominates (negative) |

In harsh: the larger positions (size_ratio = 1.22) amplify winners and the occasional
exit improvement (emergency_dd→trailing_stop) contributes equally.

In base: one catastrophic exit change (trailing_stop→emergency_dd on trade #43) wipes
out all gains.

### Q: Vài trade hay toàn bộ?

**A few trades.** P(Δ>0) ≈ 50% — the strategy wins half its trades relative to V10.
The aggregate advantage comes from 3-5 large trades where V11's sizing or exit timing
happened to be better. This is indistinguishable from noise.

### Q: Is V11 systematically better?

**No.** Evidence:
1. Median delta = 0 (no consistent per-trade improvement)
2. P(Δ>0) = 50% (coin flip)
3. Result reverses between scenarios (+$40k harsh, -$25k base)
4. 3 trades drive 78% of the harsh advantage
5. 1 trade drives 114% of the base disadvantage
6. Same exit reason 96% of the time (cycle_late rarely changes exits)

---

## 9. Conclusion

### Decomposition Summary

| Component | harsh | base | Stable? |
|-----------|-------|------|---------|
| Exit effect | +$17.9k | -$31.5k | **NO** (sign flips) |
| Size effect | +$18.1k | +$2.9k | Directionally positive but small in base |
| Fee effect | -$4.7k | -$0.7k | Always negative (larger size → more fees) |
| Net delta | +$40.1k | -$24.9k | **NO** (sign flips) |

### Final Verdict

V11 cycle_late_only provides **no reliable improvement** over V10. The trade-level
paired analysis confirms and strengthens the WFO finding:

1. **Per-trade median delta = 0** — no systematic edge
2. **Win rate = 50%** — coin flip on individual trades
3. **Aggregate result driven by 3-5 outlier trades** — not generalizable
4. **Result reverses between cost scenarios** — not robust
5. **Same exit reason 96% of the time** — cycle_late rarely activates

The V11 overlay's primary effect is **larger position sizing** (mean ratio 1.22× in
harsh), which amplifies both wins and losses without changing the strategy's fundamental
behavior. The occasional exit improvement is offset by occasional exit degradation.

**Recommendation:** V10 remains the production baseline. V11 cycle_late_only should
not be promoted.

---

## 10. Data Files

| File | Description |
|------|-------------|
| `out_trade_analysis/matched_trades_harsh.csv` | 96 matched pairs with deltas + decomposition |
| `out_trade_analysis/matched_trades_base.csv` | 95 matched pairs with deltas + decomposition |
| `out_trade_analysis/match_summary_harsh.json` | Full summary: stats, top-10, regime breakdown |
| `out_trade_analysis/match_summary_base.json` | Same for base scenario |
| `out_trade_analysis/paired_analysis.py` | Reproducible analysis script |
| `out_trade_analysis/schema.md` | Trade CSV schema reference |
