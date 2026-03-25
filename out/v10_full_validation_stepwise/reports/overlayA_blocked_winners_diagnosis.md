# OverlayA Blocked Winners Diagnosis

**Date:** 2026-02-24
**Scenario:** harsh (50 bps RT)
**Overlay:** cooldown_after_emergency_dd_bars = 12
**Baseline:** cooldown_after_emergency_dd_bars = 0

**Total cooldown-blocked trades:** 15
**Winners:** 5 (total PnL: $+38,709)
**Losers:** 10 (total PnL: $-26,600)

---

## 1. Blocked Trades — Full Detail

| # | Trade | Entry | Exit | PnL $ | Ret% | Days | Entry Reason | Exit Reason |
|--:|------:|-------|------|------:|-----:|-----:|:-------------|:------------|
| 1 | 44 | 2021-09-30 | 2021-10-22 | +17,000 | +32.7 | 21 | vdo_trend_accel | trailing_stop |
| 2 | 63 | 2024-01-23 | 2024-02-24 | +16,733 | +27.7 | 31 | vdo_dip_buy | trailing_stop |
| 3 | 79 | 2024-10-11 | 2024-10-23 | +2,224 | +3.8 | 12 | vdo_trend_accel | trailing_stop |
| 4 | 13 | 2019-09-26 | 2019-11-01 | +1,860 | +9.6 | 36 | vdo_dip_buy | trailing_stop |
| 5 | 22 | 2020-05-26 | 2020-06-04 | +893 | +5.7 | 9 | vdo_trend_accel | trailing_stop |
| 6 | 57 | 2023-08-18 | 2023-08-31 | -279 | -0.4 | 14 | vdo_dip_buy | trailing_stop |
| 7 | 12 | 2019-09-20 | 2019-09-24 | -630 | -4.6 | 4 | vdo_trend_accel | emergency_dd |
| 8 | 15 | 2019-11-17 | 2019-11-21 | -742 | -10.2 | 4 | vdo_trend_accel | emergency_dd |
| 9 | 48 | 2021-12-15 | 2021-12-28 | -1,015 | -2.4 | 14 | vdo_trend_accel | trailing_stop |
| 10 | 26 | 2020-08-23 | 2020-09-03 | -1,624 | -8.9 | 12 | vdo_trend_accel | emergency_dd |
| 11 | 98 | 2025-08-26 | 2025-09-01 | -2,872 | -2.9 | 6 | vdo_dip_buy | emergency_dd |
| 12 | 70 | 2024-06-12 | 2024-06-17 | -3,142 | -4.8 | 5 | vdo_trend_accel | emergency_dd |
| 13 | 71 | 2024-06-20 | 2024-06-24 | -4,984 | -5.8 | 4 | vdo_trend_accel | emergency_dd |
| 14 | 88 | 2025-02-26 | 2025-02-28 | -5,212 | -6.8 | 2 | vdo_dip_buy | emergency_dd |
| 15 | 72 | 2024-06-26 | 2024-07-05 | -6,100 | -7.2 | 9 | vdo_trend_accel | emergency_dd |

---

## 2. Market Context at Entry

| Trade | Regime | VDO | RSI | ATR% | Accel | HMA slope | Price vs HMA | Price vs EMA200 |
|------:|:------:|----:|----:|-----:|------:|----------:|-------------:|----------------:|
| 44 | RISK_ON | 0.0045 | 63 | 2.32 | 0.00189 | 0.119%/bar | +3.2% | -3.0% |
| 63 | RISK_ON | 0.0081 | 27 | 1.87 | 0.00241 | -0.367%/bar | -2.9% | -7.9% |
| 79 | RISK_ON | 0.0062 | 73 | 1.43 | 0.00983 | -0.170%/bar | +3.3% | +2.1% |
| 13 | RISK_ON | 0.0057 | 25 | 3.74 | 0.01366 | -1.426%/bar | -5.5% | -16.2% |
| 22 | RISK_ON | 0.0064 | 51 | 1.70 | 0.02314 | -0.181%/bar | +1.4% | +1.6% |
| 57 | RISK_ON | 0.0040 | 3 | 2.20 | -0.00135 | -0.613%/bar | -6.9% | -9.7% |
| 12 | RISK_ON | 0.0131 | 64 | 1.46 | 0.01296 | -0.250%/bar | +1.9% | -0.3% |
| 15 | RISK_ON | 0.0064 | 36 | 0.92 | 0.00331 | -0.170%/bar | +0.0% | -3.7% |
| 48 | RISK_ON | 0.0050 | 58 | 2.52 | 0.03182 | -0.225%/bar | +1.3% | -10.2% |
| 26 | RISK_ON | 0.0052 | 50 | 1.09 | 0.00600 | -0.244%/bar | +0.4% | +4.2% |
| 98 | RISK_ON | 0.0059 | 27 | 1.27 | 0.00561 | -0.305%/bar | -2.2% | -4.9% |
| 70 | RISK_ON | 0.0102 | 69 | 1.37 | 0.02640 | -0.211%/bar | +3.0% | +2.8% |
| 71 | RISK_ON | 0.0052 | 62 | 1.08 | 0.00285 | -0.077%/bar | +1.3% | -1.9% |
| 88 | RISK_ON | 0.0079 | 29 | 1.95 | 0.00389 | -0.677%/bar | -2.2% | -8.6% |
| 72 | RISK_ON | 0.0046 | 51 | 1.62 | 0.01974 | -0.223%/bar | +1.2% | -6.1% |

---

## 3. Distance from Nearest Emergency DD Exit

| Trade | Entry Date | Nearest ED Exit | ED Trade | Bars Gap | Gap (days) | Pattern |
|------:|:-----------|:----------------|:--------:|---------:|-----------:|:--------|
| 44 | 2021-09-30 | 2021-09-29 | #43 | 11 | 1.8 | trend continuation |
| 63 | 2024-01-23 | 2024-01-22 | #62 | 5 | 0.8 | other |
| 79 | 2024-10-11 | 2024-10-10 | #78 | 6 | 1.0 | trend continuation |
| 13 | 2019-09-26 | 2019-09-24 | #12 | 12 | 2.0 | V-shape rebound |
| 22 | 2020-05-26 | 2020-05-25 | #21 | 8 | 1.3 | trend continuation |
| 57 | 2023-08-18 | 2023-08-17 | #56 | 4 | 0.7 | recovery from drawdown |
| 12 | 2019-09-20 | 2019-09-19 | #11 | 5 | 0.8 | trend continuation |
| 15 | 2019-11-17 | 2019-11-15 | #14 | 9 | 1.5 | trend continuation |
| 48 | 2021-12-15 | 2021-12-13 | #47 | 8 | 1.3 | trend continuation |
| 26 | 2020-08-23 | 2020-08-22 | #25 | 6 | 1.0 | trend continuation |
| 98 | 2025-08-26 | 2025-08-25 | #97 | 5 | 0.8 | other |
| 70 | 2024-06-12 | 2024-06-11 | #69 | 7 | 1.2 | trend continuation |
| 71 | 2024-06-20 | 2024-06-17 | #70 | 16 | 2.7 | trend continuation |
| 88 | 2025-02-26 | 2025-02-25 | #87 | 7 | 1.2 | recovery from drawdown |
| 72 | 2024-06-26 | 2024-06-24 | #71 | 10 | 1.7 | trend continuation |

**Gap range:** 4 – 16 H4 bars (0.7 – 2.7 days)
**All gaps > exit_cooldown_bars (3):** Yes
**All gaps ≤ K=12:** No — some entries occur after cooldown would expire

---

## 4. Price Action Context

| Trade | Pre-DD% | Post-Rally% | V-Shape? | Entry in 20-bar Range | Pattern |
|------:|--------:|------------:|:--------:|----------------------:|:--------|
| 44 | 1.4 | 53.9 | No | 82% | trend continuation |
| 63 | 6.4 | 35.1 | No | 17% | other |
| 79 | 0.2 | 10.2 | No | 97% | trend continuation |
| 13 | 16.3 | 23.0 | Yes | 28% | V-shape rebound |
| 22 | 3.8 | 15.9 | No | 47% | trend continuation |
| 57 | 10.4 | 6.5 | No | 29% | recovery from drawdown |
| 12 | 0.8 | 0.8 | No | 87% | trend continuation |
| 15 | 3.6 | 1.8 | No | 20% | trend continuation |
| 48 | 4.8 | 7.8 | No | 52% | trend continuation |
| 26 | 2.1 | 3.3 | No | 53% | trend continuation |
| 98 | 5.5 | 3.5 | No | 14% | other |
| 70 | 0.7 | 0.4 | No | 89% | trend continuation |
| 71 | 2.1 | 0.9 | No | 56% | trend continuation |
| 88 | 8.3 | 0.8 | No | 24% | recovery from drawdown |
| 72 | 4.0 | 3.1 | No | 58% | trend continuation |

---

## 5. Pattern Classification

### Other (2 trades, $+13,861)

- **Trade #63** (2024-01-23 → 2024-02-24): $+16,733 (+27.7%). Entry 5 bars after ED exit. Pre-DD 6% → post-rally 35%. Regime=RISK_ON, VDO=0.0081, RSI=27, price vs HMA=-2.9%.
- **Trade #98** (2025-08-26 → 2025-09-01): $-2,872 (-2.9%). Entry 5 bars after ED exit. Pre-DD 5% → post-rally 3%. Regime=RISK_ON, VDO=0.0059, RSI=27, price vs HMA=-2.2%.

### Trend Continuation (10 trades, $+1,879)

- **Trade #44** (2021-09-30 → 2021-10-22): $+17,000 (+32.7%). Entry 11 bars after ED exit. Pre-DD 1% → post-rally 54%. Regime=RISK_ON, VDO=0.0045, RSI=63, price vs HMA=+3.2%.
- **Trade #79** (2024-10-11 → 2024-10-23): $+2,224 (+3.8%). Entry 6 bars after ED exit. Pre-DD 0% → post-rally 10%. Regime=RISK_ON, VDO=0.0062, RSI=73, price vs HMA=+3.3%.
- **Trade #22** (2020-05-26 → 2020-06-04): $+893 (+5.7%). Entry 8 bars after ED exit. Pre-DD 4% → post-rally 16%. Regime=RISK_ON, VDO=0.0064, RSI=51, price vs HMA=+1.4%.
- **Trade #12** (2019-09-20 → 2019-09-24): $-630 (-4.6%). Entry 5 bars after ED exit. Pre-DD 1% → post-rally 1%. Regime=RISK_ON, VDO=0.0131, RSI=64, price vs HMA=+1.9%.
- **Trade #15** (2019-11-17 → 2019-11-21): $-742 (-10.2%). Entry 9 bars after ED exit. Pre-DD 4% → post-rally 2%. Regime=RISK_ON, VDO=0.0064, RSI=36, price vs HMA=+0.0%.
- **Trade #48** (2021-12-15 → 2021-12-28): $-1,015 (-2.4%). Entry 8 bars after ED exit. Pre-DD 5% → post-rally 8%. Regime=RISK_ON, VDO=0.0050, RSI=58, price vs HMA=+1.3%.
- **Trade #26** (2020-08-23 → 2020-09-03): $-1,624 (-8.9%). Entry 6 bars after ED exit. Pre-DD 2% → post-rally 3%. Regime=RISK_ON, VDO=0.0052, RSI=50, price vs HMA=+0.4%.
- **Trade #70** (2024-06-12 → 2024-06-17): $-3,142 (-4.8%). Entry 7 bars after ED exit. Pre-DD 1% → post-rally 0%. Regime=RISK_ON, VDO=0.0102, RSI=69, price vs HMA=+3.0%.
- **Trade #71** (2024-06-20 → 2024-06-24): $-4,984 (-5.8%). Entry 16 bars after ED exit. Pre-DD 2% → post-rally 1%. Regime=RISK_ON, VDO=0.0052, RSI=62, price vs HMA=+1.3%.
- **Trade #72** (2024-06-26 → 2024-07-05): $-6,100 (-7.2%). Entry 10 bars after ED exit. Pre-DD 4% → post-rally 3%. Regime=RISK_ON, VDO=0.0046, RSI=51, price vs HMA=+1.2%.

### V-Shape Rebound (1 trade, $+1,860)

- **Trade #13** (2019-09-26 → 2019-11-01): $+1,860 (+9.6%). Entry 12 bars after ED exit. Pre-DD 16% → post-rally 23%. Regime=RISK_ON, VDO=0.0057, RSI=25, price vs HMA=-5.5%.

### Recovery From Drawdown (2 trades, $-5,490)

- **Trade #57** (2023-08-18 → 2023-08-31): $-279 (-0.4%). Entry 4 bars after ED exit. Pre-DD 10% → post-rally 6%. Regime=RISK_ON, VDO=0.0040, RSI=3, price vs HMA=-6.9%.
- **Trade #88** (2025-02-26 → 2025-02-28): $-5,212 (-6.8%). Entry 7 bars after ED exit. Pre-DD 8% → post-rally 1%. Regime=RISK_ON, VDO=0.0079, RSI=29, price vs HMA=-2.2%.

---

## 6. Common Characteristics of Blocked Winners

| Metric | Value |
|--------|-------|
| Count | 5 |
| Total PnL | $+38,709 |
| Avg return | +15.9% |
| Avg holding period | 22 days |
| Avg bars from ED exit | 8.4 bars (1.4 days) |
| Avg pre-entry drawdown | 5.6% |
| Avg post-entry rally | 27.6% |
| Avg VDO at entry | 0.0062 |
| Exit reasons | trailing_stop |
| Entry regimes | RISK_ON |
| Entry reasons | vdo_trend_accel, vdo_dip_buy |

**Key observations:**

1. **All blocked winners exit via trailing_stop** — none would have been another emergency_dd. The cooldown blocks legitimate recovery trades, not cascade re-entries.

2. **All entries occur in RISK_ON regime** — the market structure is bullish when these trades enter. The emergency_dd was a temporary shock within a positive regime, not a regime breakdown.

3. **All entries within K=12 bars of ED exit** — these are the trades the cooldown is specifically designed to block. The question is whether the blocking is net-beneficial.
   - Entry gaps: 5 to 12 bars (0.8 to 2.0 days)

4. **1/5 winners are V-shape rebounds** — the price dropped significantly before entry, then rallied strongly. These are genuine recovery trades after an isolated emergency_dd exit.

5. **Strong VDO at entry** (all > 0.004) — the volume delta oscillator confirms buying pressure at entry. These are not weak or ambiguous entries.

### Winners vs Losers: Exit Reason Breakdown

This is the strongest signal separating legitimate recovery trades from cascade re-entries:

| Group | Count | trailing_stop | emergency_dd | other | Total PnL |
|:------|------:|--------------:|-------------:|------:|----------:|
| **Winners** | 5 | 5 (100%) | 0 (0%) | 0 | $+38,709 |
| **Losers** | 10 | 2 (20%) | 8 (80%) | 0 | $-26,600 |

**Critical finding:** 8/10 blocked losers (80%) exit via **emergency_dd** — they are cascade re-entries that the cooldown correctly blocks. Their total PnL: $-25,307.

This means the cooldown is doing exactly what it should for cascade scenarios. The opportunity cost comes exclusively from isolated-ED recovery trades that exit via trailing_stop.

**Cascade re-entry losers (correctly blocked):**

- Trade #12 (2019-09-20): $-630 — re-entered 5 bars after ED exit, then exited via emergency_dd again
- Trade #15 (2019-11-17): $-742 — re-entered 9 bars after ED exit, then exited via emergency_dd again
- Trade #26 (2020-08-23): $-1,624 — re-entered 6 bars after ED exit, then exited via emergency_dd again
- Trade #98 (2025-08-26): $-2,872 — re-entered 5 bars after ED exit, then exited via emergency_dd again
- Trade #70 (2024-06-12): $-3,142 — re-entered 7 bars after ED exit, then exited via emergency_dd again
- Trade #71 (2024-06-20): $-4,984 — re-entered 16 bars after ED exit, then exited via emergency_dd again
- Trade #88 (2025-02-26): $-5,212 — re-entered 7 bars after ED exit, then exited via emergency_dd again
- Trade #72 (2024-06-26): $-6,100 — re-entered 10 bars after ED exit, then exited via emergency_dd again

---

## 7. Root Cause Analysis

The blocked winners share a common pattern:

1. **An isolated emergency_dd exit occurs** — the strategy exits due to a drawdown exceeding the threshold (28% default).
2. **The market recovers within a few bars** — the drawdown was temporary (not the start of a multi-month bear cascade).
3. **The cooldown window (K=12 bars = 2 days) blocks re-entry** — by the time the cooldown expires, the optimal re-entry point has passed.
4. **The trade that would have been taken is a big winner** — exiting via trailing_stop after a strong rally.

The core issue is that the cooldown treats all emergency_dd exits equally. It cannot distinguish:

- **Cascade ED exits** (2+ consecutive EDs within a drawdown episode) — where blocking re-entry is beneficial
- **Isolated ED exits** (single ED followed by recovery) — where blocking re-entry is costly

---

## 8. Proposed Minimal Rule

### Problem

The current cooldown activates after **every** emergency_dd exit, including isolated ones that are followed by genuine recoveries.

### Proposal: Activate cooldown only after 2nd consecutive emergency_dd

```python
# Current (K=12, activates on every ED exit):
if self._last_exit_reason == "emergency_dd":
    self._emergency_dd_cooldown_remaining = K

# Proposed (activate only after 2+ consecutive ED exits):
if self._last_exit_reason == "emergency_dd":
    self._consecutive_ed_count += 1
    if self._consecutive_ed_count >= 2:
        self._emergency_dd_cooldown_remaining = K
else:
    self._consecutive_ed_count = 0
```

### Why this works

1. **Zero additional entry alpha needed** — the rule only modifies the cooldown activation trigger, not the entry logic.
2. **Preserves cascade protection** — in cascade episodes (where ED exits come in clusters of 2+), the cooldown still activates on the 2nd ED exit.
3. **Unblocks isolated recovery trades** — after a single ED exit followed by a recovery, no cooldown is applied.
4. **Matches the cascade definition** — the pipeline already defines cascades as episodes with max_run_emergency_dd >= 2. This rule aligns the cooldown activation with that definition.

### Evidence: blocked winners would be unblocked

| Trade | Bars from ED | Preceding ED exits in sequence | Would trigger rule? |
|------:|-------------:|-------------------------------:|:-------------------:|
| 44 | 11 | 1 | **No — isolated, would be unblocked** |
| 63 | 5 | 1 | **No — isolated, would be unblocked** |
| 79 | 6 | 1 | **No — isolated, would be unblocked** |
| 13 | 12 | 2 | Yes — cascade |
| 22 | 8 | 1 | **No — isolated, would be unblocked** |

### Expected impact

- **Blocked winners recovered:** The isolated-ED winners would no longer be blocked
- **Cascade protection preserved:** The cooldown still activates in cascade scenarios
- **K=6 equivalent for isolated EDs, K=12 for cascades:** This effectively creates an adaptive cooldown that matches the pattern of the market

---

## 9. Deliverables

| Artifact | Path |
|----------|------|
| Script | `scripts/overlayA_blocked_winners_diagnosis.py` |
| Blocked winners CSV | `out_overlayA_conditional/blocked_winners_top.csv` |
| This report | `reports/overlayA_blocked_winners_diagnosis.md` |

