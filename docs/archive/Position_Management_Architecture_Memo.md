# Position Management Architecture Memo

**System:** V10 BTC Spot Trend-Follower (V8 Apex core)
**Author:** Portfolio Risk Manager
**Date:** 2026-02-26
**Data:** 103 trades, harsh scenario (50 bps RT), 2019-01 → 2025-11
**Source files:** `out_v10_fix_loop/v10_baseline_trades_harsh.csv`, `v10_baseline_events_harsh.csv` (8,177 events, 576 buy fills)

---

## Executive Summary

V10's entry signal (VDO) is sound — non-emergency-DD trades produce +$208,663 net with a positive per-trade expectancy. The system is structurally broken at the **position management layer**: it pyramids aggressively into falling positions, creating a self-reinforcing cascade where emergency-DD exits are immediately followed by full-size re-entries into the same declining market. 9 cascade chains (23 trades, 22% of total) destroy **$77,093 — equivalent to 82% of the strategy's total net PnL** being given back. The fix must target WHEN and HOW MUCH the system adds to existing positions.

---

## Phase 1: Data Diagnosis — Pyramiding Attribution

### 1.1 Loss Attribution by Fill Order (All 36 Emergency-DD Trades)

Across all 36 trades that exited via emergency_dd, the 576 buy fills decompose as follows:

| Fill Order | Count | Mean PnL | Total PnL | % of Trade Loss |
|:-----------|------:|---------:|----------:|----------------:|
| **Fill 0 (INITIAL)** | 36 | -$1,278 | **-$45,995** | **44.8%** |
| Fill 1 (ADD 1) | 34 | -$886 | -$30,114 | 29.4% |
| Fill 2 (ADD 2) | 31 | -$609 | -$18,870 | 18.2% |
| Fill 3 (ADD 3) | 24 | -$349 | -$8,372 | 9.5% |
| Fill 4 (ADD 4) | 18 | -$262 | -$4,722 | 6.6% |
| Fill 5+ (ADD 5–8) | 24 | -$159 | -$3,826 | ~3.5% ea |
| **TOTAL** | **167** | | **-$111,898** | |

**Key finding:** The initial entry contributes only **41.1%** of gross losses in ED trades. The remaining **58.9% ($65,903) comes from ADDs** — positions the system built into declining markets.

The per-fill loss attribution for a "typical" cascade trade (averaging across 36 ED trades):

- **INITIAL entry:** 44.8% of trade loss
- **1st ADD:** 29.4% of trade loss
- **2nd ADD:** 18.2% of trade loss
- **Subsequent ADDs (3rd+):** ~7.6% of trade loss combined (smaller because size caps kick in)

The damage is concentrated in ADDs 1 and 2. By the time the strategy reaches its 3rd add, the per-fill contribution drops because `max_add_per_bar=0.35` and the exposure ceiling limit the remaining gap. But the first two ADDs, which collectively account for **47.6% of ED trade losses**, execute at nearly the worst possible time: 12-24 hours after an entry that is already declining.

### 1.2 Thought Experiment: "Add Size = 0"

| Metric | ADD_SIZE=0 | Current (V10) | Delta |
|:-------|----------:|-------------:|------:|
| ED trades: gross PnL | -$45,995 (initial fill only) | -$111,898 | +$65,903 saved |
| Non-ED trades: gross PnL | $72,888 (initial fill only) | $214,135 | -$141,247 lost |
| **All trades: gross PnL** | **$26,893** | **$102,237** | **-$75,344** |
| Approximate net PnL | ~$15,000–20,000 | $94,026 | **~-$75,000** |

**Interpretation:** Eliminating pyramiding entirely would:

- **Save ~$65,903** in ED-trade losses (reduce ED damage by 59%)
- **Lose ~$141,247** in non-ED-trade gains (reduce winning trade gains by 66%)
- **Net impact: -$75,344 drop in gross PnL** — catastrophic (~74% gross PnL destruction)

This confirms that **blanket ADD suppression is not viable.** Pyramiding is the strategy's profit engine: 73.7% of all gross PnL comes from ADDs. The target is not to eliminate pyramiding but to make it **conditional** — pyramid on strength, refuse to pyramid into weakness.

### 1.3 The Asymmetry Problem

| Category | Avg Buy Fills | Avg Exit Exposure | Gross PnL from ADDs |
|:---------|-------------:|------------------:|--------------------:|
| ED trades (36) | 4.6 | 0.84 | -$65,903 |
| Non-ED trades (67) | 6.1 | 0.86 | +$141,247 |

Non-ED trades actually pyramid **more** (6.1 vs 4.6 fills) and reach comparable exposure (0.86 vs 0.84). The difference is not *how much* the system pyramids — it's *WHERE* it pyramids. In winning trades, adds confirm a rising trend. In ED trades, adds amplify a falling position.

### 1.4 Cascade Chain Anatomy

The 9 identified cascade chains (≥2 consecutive emergency_dd exits):

| Chain | Trades | Period | Total PnL | Avg Fills/Trade | Root Cause |
|------:|:------:|:------:|----------:|----------------:|:-----------|
| **7** | #69–74 | 2024-05 → 2024-08 | **-$26,686** | 4.7 | 6 consecutive ED exits; D1 BULL never flips |
| **8** | #86–88 | 2025-01 → 2025-02 | **-$21,689** | 6.3 | CHOP regime, VDO stays positive |
| 5 | #46–47 | 2021-11 → 2021-12 | -$9,490 | 5.0 | Late-bull correction |
| 9 | #97–98 | 2025-08 → 2025-09 | -$5,954 | 5.0 | Topping → re-enter in BULL |
| 6 | #55–56 | 2023-07 → 2023-08 | -$5,169 | 6.0 | BULL-to-TOPPING transition |
| Others (4) | 2 ea | Various | -$1.6K to -$2.4K ea | 3.5–5.5 | Shorter cascades |
| **TOTAL** | **23** | | **-$77,093** | | **82% of net PnL destroyed** |

**Chain #7 drill-down (6 trades, $26,686 total loss):**

Each trade in this chain follows the same pattern:
1. Enter at market open (exposure = 0)
2. Pyramid 2-7 ADDs over 10-109 bars, reaching 0.66–0.95 exposure
3. Hit emergency_dd at 28% drawdown from entry NAV
4. Flat for 3 bars (exit_cooldown)
5. VDO still positive + D1 still BULL → re-enter immediately
6. Repeat

The strategy cannot distinguish "VDO is positive because momentum is recovering" from "VDO is positive because the oscillator hasn't fully decayed yet." During corrections within BULL regimes, VDO lags by 12-28 bars (the fast/slow EMA periods), creating a 48-112 hour window where the signal looks bullish while prices are falling.

### 1.5 Prior Fix Attempts (Failed)

| Attempt | Mechanism | Result | Why It Failed |
|:--------|:----------|:-------|:-------------|
| Overlay A v1 | Flat 12-bar post-ED cooldown | -$1,416 net (rejected) | 77% benefit concentrated in 1 episode; hurts other periods |
| Overlay A v2 | Escalating cooldown (3/12 bars) | -$11,728 net (rejected) | Short cooldown trivially matches existing exit_cooldown; long cooldown too aggressive |
| V13 P1 Add-Throttle | ATH-based DD scales max_add_per_bar | 0/9 grid cells pass | Equity peak DD is too persistent; throttle becomes permanent position cap |

---

## Phase 2: Human Trader Translation

A professional Portfolio Manager running a BTC-long trend strategy does three things that V10 does not:

### Rule 1: "Scale-In on Strength Only" (Unrealized Profit Gate)

**What a human does:** After opening a position, a human PM will only add to it once the position shows a profit. If BTC is bought at $100K and immediately drops to $97K, the PM waits. They add only when the position is showing green — e.g., price is above their average entry by at least 1-2 ATR. The logic: "I add to winners, I cut losers."

**What V10 does:** The only add gate is `entry_cooldown_bars=3` (12 hours). After 3 bars, if VDO > threshold and price > HMA (or RSI < 30), V10 adds regardless of whether the existing position is at +5% or -5%. The position's own health is never consulted.

**Where V10 is blind:** `_check_entry()` has zero visibility into `state.entry_price_avg` vs `mid`. The unrealized PnL of the current position is never referenced before deciding to add.

### Rule 2: "Portfolio Heat Budget" (Aggregate Drawdown Exposure Cap)

**What a human does:** A PM tracks "portfolio heat" — the total risk budget currently deployed. If the portfolio is already in a 10% drawdown from its equity curve peak, a human PM does NOT load up on the same position. They may even reduce. The idea: "The portfolio is stressed; stop adding fuel until we recover."

**What V10 does:** V10 has `enable_dd_adaptive` (disabled by default for Apex), and the failed V13 P1 add-throttle tried this with ATH-based DD. But no currently-active mechanism links portfolio-level drawdown to add sizing. The strategy scales into positions identically whether NAV is at an all-time high or 20% below peak.

**Why prior attempts failed:** V13's throttle used all-time equity peak as reference. Because BTC is trending and volatile, the equity curve can spend 60-70% of the time below its ATH. This made the throttle permanently active, cutting CAGR by 18-27pp. The reference must be **rolling** (e.g., trailing N-day high) not absolute.

### Rule 3: "Post-Loss Cooling Period" (State-Dependent Re-Entry Delay)

**What a human does:** After being stopped out at a loss, especially a large one, a human PM does not immediately re-enter. They wait for the dust to settle — not a fixed time, but until market conditions visibly change: a new higher low forms, volatility compresses, or the signal refreshes from a genuinely new momentum impulse.

**What V10 does:** `exit_cooldown_bars=3` — a flat 12-hour wait after any exit, regardless of severity. The V8 Apex Overlay A adds `cooldown_after_emergency_dd_bars=12` (48 hours) specifically after emergency_dd exits. But this was tested and rejected because the fixed duration doesn't align with when conditions actually change.

**What's missing:** No condition-based re-entry gate that asks "has the market structure that caused the last stop actually resolved?" The cooldown is purely time-based, not state-based. A structural gate (e.g., "wait for VDO to cross below 0 and then back above threshold") would be state-sensitive but would touch the VDO signal logic, violating constraints. The alternative: gate on the position's own PnL trajectory after re-entry, which doesn't touch VDO.

---

## Phase 3: Structural Proposals

### Proposal A: Unrealized PnL Gate for Adds

**Core Logic:** Block all pyramiding adds unless the current open position shows unrealized profit above a minimum threshold (expressed in ATR units).

**Mechanism Change:** Intervenes at **Entry → Add** boundary. Specifically: insert a new gate at the top of `_check_entry()` that fires only when `state.exposure > 0.01` (existing position). If `mid < entry_price_avg + gate_atr_mult * ATR`, return None (block the add). Initial entries (exposure ≈ 0) are never blocked.

**The 1 Parameter:**
- `add_profit_gate_atr`: float, range **[0.25, 1.5]**
  - At 0.5: requires price to be 0.5× ATR above average entry before adding
  - At 1.0: requires 1× ATR profit before adding
  - The parameter unit is ATR (H4 fast ATR, period=14), which self-scales with volatility

**Failure Mode:** In **V-shaped reversals** — when BTC drops sharply but then recovers within a few bars. The gate would block adds during the early recovery phase (position still underwater), causing the strategy to miss the best pyramiding opportunity. This is precisely the scenario where V10's current "always add" behavior works well. Impact: slower position-building in the early phase of trend continuation after a dip, reducing CAGR by an estimated 2-5pp on strong trend trades.

**Why it's structural (not parameter tuning):** V10 currently has zero mechanisms that condition adds on the existing position's profitability. This introduces a fundamentally new concept: **the position must justify itself before it earns the right to grow.**

---

### Proposal B: Rolling-Window Equity Drawdown Brake

**Core Logic:** When the portfolio NAV is below its trailing N-bar high by more than a threshold, reduce `max_add_per_bar` to a fraction of its normal value. Unlike V13's failed ATH-based throttle, the rolling window ensures the brake self-resets as the equity curve progresses.

**Mechanism Change:** Intervenes at **Add → sizing**. Specifically: at the end of `_check_entry()`, after `sz` is computed but before the final `min(sz, max_add_per_bar, gap)` clamp. Compute `rolling_dd = 1 - NAV / max(NAV over last N bars)`. If `rolling_dd > brake_threshold`, replace `max_add_per_bar` with `max_add_per_bar * 0.0` (complete add block — not size reduction, which was shown to be ineffective in V13 grid).

**The 1 Parameter:**
- `rolling_brake_window_bars`: integer, range **[30, 120]** (5–20 days in H4 bars)
  - At 36 bars (6 days): short memory, resets quickly after V-bottoms
  - At 90 bars (15 days): captures multi-week drawdown regimes
  - The brake threshold is **hardcoded at the strategy's own `emergency_dd_pct / 2`** (i.e., 14% for the default 28% emergency_dd), which makes it proportional to the existing risk framework without adding a second parameter

**Failure Mode:** In **prolonged slow grinds** — if BTC slowly trends down over 3-4 weeks then reverses sharply upward, the rolling window may still show elevated DD when the recovery is already underway, blocking adds during the first 1-2 weeks of the new uptrend. This is less severe than V13's ATH problem because the window eventually rolls forward, but the cost is delayed participation in new trends following extended corrections.

**Why it's structural (not parameter tuning):** V10 currently has no mechanism that links portfolio-level equity health to pyramiding permission. The V13 attempt used the correct concept but the wrong reference (ATH). A rolling window is the standard institutional risk management tool — hedge funds use "trailing N-day VaR" not "VaR from inception." This fixes the reference frame.

---

### Proposal C: Post-Exit "Proof-of-Recovery" Gate

**Core Logic:** After any position exit (emergency_dd, trailing_stop, or fixed_stop), require the first N bars of the new position to show non-negative unrealized PnL before allowing any ADDs. If the new position is immediately underwater, freeze adds until it recovers (but keep the position open — no forced exit).

**Mechanism Change:** Intervenes at **Exit → Entry → Add** boundary. Specifically: when `just_opened` fires in `on_bar()`, set a flag `_proof_period_active = True`. While this flag is active, block all adds. Clear the flag when either: (a) `bars_since_entry >= proof_bars` AND `mid >= entry_price_avg`, or (b) `bars_since_entry >= 2 * proof_bars` (hard time limit to prevent permanent freeze). This creates a probationary period where the new position must earn the right to grow.

**The 1 Parameter:**
- `proof_recovery_bars`: integer, range **[3, 12]** (12–48 hours)
  - At 3: minimal delay — just ensure the first 12h are not immediately negative
  - At 8: standard — 32 hours of observation; if position is still underwater after 32h, wait until it recovers or until 64h pass
  - The compound condition (time + PnL) means this is not purely a time-based cooldown like the failed Overlay A; it's a state-sensitive gate

**Failure Mode:** In **gap-up recoveries** — if the exit was a trailing_stop at a moderate profit (not a loss), and the next entry immediately catches a strong VDO signal with a clean gap-up, the proof-of-recovery gate imposes an unnecessary drag. The strategy would scale in slowly even though conditions are ideal. Winning re-entries after trailing stops would be most affected, costing an estimated 1-3pp of CAGR on the best trades.

**Why it's structural (not parameter tuning):** V10 currently treats every new position identically regardless of whether the prior trade was a devastating emergency_dd cascade or a clean trailing_stop profit-take. This introduces the concept of **positional probation** — a new position born from a losing exit must demonstrate viability before compound scaling begins.

---

## Structural Soundness Assessment

| Criterion | Proposal A (PnL Gate) | Proposal B (Rolling Brake) | Proposal C (Proof Gate) |
|:----------|:---------------------:|:--------------------------:|:-----------------------:|
| Directly addresses cascade chains | **Yes** — blocks adds into falling entries | Partially — reduces add size during DD | **Yes** — blocks cascade re-entry adds |
| Protects BULL-trend pyramiding | **Yes** — profitable positions still add freely | Yes — no brake when equity healthy | Partially — brief delay on all entries |
| Self-scaling with volatility | **Yes** — ATR-denominated gate | Partially — fixed bar window | No — time-based |
| Risk of permanent activation | **None** — gate resets per-trade | Low — rolling window resets | **None** — hard time limit |
| Prior-art failure risk | None — genuinely new in V10 | Medium — conceptually similar to V13 | Low — related to Overlay A but fundamentally different |
| Implementation complexity | Trivial (3 lines in `_check_entry`) | Moderate (rolling NAV buffer) | Moderate (state machine) |
| Single-parameter clarity | **High** — ATR multiplier is intuitive | High — window length in bars | Medium — compound condition |

### Recommendation

**Proposal A (Unrealized PnL Gate for Adds) is structurally the soundest.**

Rationale:

1. **It attacks the exact root cause.** The data shows 58.9% of ED-trade losses come from ADDs into losing positions. Proposal A directly blocks this: no adds unless the position is green. Proposals B and C address the problem indirectly (B throttles all adds during portfolio stress; C delays adds after exits).

2. **It preserves the profit engine.** Non-ED trades (the winners) have positive unrealized PnL when pyramiding — the gate would rarely activate on winning trades. The asymmetry is clean: on winning trades, the gate opens quickly; on losing trades, it stays shut.

3. **It has no "memory problem."** V13's ATH-based throttle failed because the reference frame (equity peak since inception) was permanently elevated. Proposal A's reference frame is the current position's own entry price — it resets on every new trade. No stale state.

4. **It self-scales with market conditions.** Using ATR as the denominator means the gate automatically tightens in low-volatility (where small moves signal trouble) and loosens in high-volatility (where fluctuation is normal). This is inherently regime-adaptive without requiring regime detection parameters.

5. **The failure mode is tolerable.** V-shaped recoveries where the gate blocks adds are a real cost, but they represent the exact tradeoff we want: slightly slower builds on dip-recoveries in exchange for complete protection against building into falling knives. The cascade chains (#7: -$26,686, #8: -$21,689) would be dramatically reduced because the position would stay at ~30-35% initial exposure instead of ramping to 85-95%.

**Await approval before implementing.**

---

## Appendix A: Data Files Referenced

| File | Description |
|:-----|:------------|
| `out_v10_fix_loop/v10_baseline_trades_harsh.csv` | 103 trades, V10 baseline, harsh scenario |
| `out_v10_fix_loop/v10_baseline_events_harsh.csv` | 8,177 events (576 buy fills) |
| `out_v10_full_validation_stepwise/reports/step2_cascade_kpis.md` | Cascade chain analysis (9 chains) |
| `out_overlayA_conditional/decision.json` | Overlay A rejection decision |
| `reports/p1_add_throttle_acceptance.md` | V13 P1 grid rejection |
| `reports/spec_p1_add_throttle.md` | V13 mechanism design spec |

---

## Appendix B: Pre-Implementation Stress Testing

*Added 2025-02-25. All traces use static fill analysis: blocked fills are treated as permanently lost (upper bound on cost). In a live backtest, VDO may refire later and the add happens at a different price — the true cost would be lower.*

*ATR approximation: H4 ATR ≈ 2% of BTC price (historical average). This is used for Proposal A's gate threshold only.*

### Question 1: Trace Proposal A Through the 5 Largest Winning Trades

**Setup:** Proposal A with `gate_atr_mult = 0.5` (require 0.5× ATR profit before allowing ADDs). Traced fill-by-fill through the 5 largest winners by `net_pnl`.

#### T#81: PnL = $26,247 | 9 fills | 2024-11-04 → exit @$95,806

| Fill | Type | Price | Avg Entry | Unrealized | ATR dist | Gate |
|:-----|:-----|------:|----------:|-----------:|---------:|:-----|
| 0 | INITIAL | 69,117 | 69,117 | — | — | ALLOWED |
| 1 | ADD 1 | 68,715 | 69,117 | −0.58% | −0.29 | **BLOCKED** |
| 2 | ADD 2 | 68,311 | 68,951 | −0.93% | −0.47 | **BLOCKED** |
| 3 | ADD 3 | 69,710 | 68,856 | +1.24% | +0.61 | ALLOWED |
| 4 | ADD 4 | 74,423 | 68,954 | +7.93% | +3.67 | ALLOWED |
| 5–8 | ADD 5–8 | 78,911–86,188 | — | +14% to +23% | +6 to +9 | ALLOWED |

**Gate impact:** 2 adds blocked. These fills at 68,715 and 68,311 were *below* the initial entry (69,117) — the position was genuinely underwater. Price recovered 12 hours later (Fill 3 at 69,710). The blocked fills' contribution to final PnL = **$10,686**.

**Key observation:** This is a textbook **V-shaped recovery**. BTC dipped ~1.2% below entry, VDO fired two adds into the dip, then price rallied to 95,806 (+38.6%). The dip-adds were the cheapest fills in the trade. Blocking them would reduce PnL from $26,247 to ~$15,711 (−40%).

#### T#31: PnL = $21,618 | 3 fills | 2020-12-12 → exit @$34,338

| Fill | Type | Price | Avg Entry | Unrealized | ATR dist | Gate |
|:-----|:-----|------:|----------:|-----------:|---------:|:-----|
| 0 | INITIAL | 18,300 | 18,300 | — | — | ALLOWED |
| 1 | ADD 1 | 18,417 | 18,300 | +0.64% | +0.32 | **BLOCKED** |
| 2 | ADD 2 | 18,803 | 18,359 | +2.42% | +1.18 | ALLOWED |

**Gate impact:** 1 add blocked. Fill 1 was actually *above* entry (green) but below the 0.5 ATR threshold — a marginal block. Cost: **$8,064** in forgone PnL. Would reduce trade from $21,618 to $13,625 (−37%).

#### T#64: PnL = $18,002 | 9 fills | 2024-02-25 → exit @$69,346

All 9 fills were at progressively higher prices (first add at +2.36%). **0 adds blocked.** Gate has zero cost on this clean trend.

#### T#44: PnL = $17,000 | 9 fills | 2021-09-30 → exit @$62,131

All adds at +2.9% to +25% above entry. **0 adds blocked.** Zero cost.

#### T#63: PnL = $16,733 | 5 fills | 2024-01-23 → exit @$50,693

| Fill | Type | Price | Avg Entry | Unrealized | ATR dist | Gate |
|:-----|:-----|------:|----------:|-----------:|---------:|:-----|
| 0 | INITIAL | 39,243 | 39,243 | — | — | ALLOWED |
| 1 | ADD 1 | 40,021 | 39,243 | +1.98% | +0.97 | ALLOWED |
| 2 | ADD 2 | 39,843 | 39,630 | +0.54% | +0.27 | **BLOCKED** |
| 3 | ADD 3 | 40,001 | 39,678 | +0.81% | +0.40 | **BLOCKED** |
| 4 | ADD 4 | 41,464 | 39,686 | +4.48% | +2.14 | ALLOWED |

**Gate impact:** 2 adds blocked (both marginally below 0.5 ATR threshold — position was green but not "green enough"). Cost: **$4,056**.

#### Question 1 Summary

| Trade | Fills | Blocked | Was position temporarily red? | Gate duration | PnL cost |
|:------|------:|--------:|:------------------------------|:-------------|:---------|
| T#81 | 9 | 2 | **Yes** — down 0.6−0.9% for ~12h | 12 hours | $10,686 (−40%) |
| T#31 | 3 | 1 | No — marginally green (+0.3 ATR) | 12 hours | $8,064 (−37%) |
| T#64 | 9 | 0 | No | — | $0 |
| T#44 | 9 | 0 | No | — | $0 |
| T#63 | 5 | 2 | No — marginally green (+0.3 ATR) | 16 hours | $4,056 (−24%) |
| **Total** | **35** | **5** | | | **$22,806 (−22.3%)** |

**Verdict:** 3 of 5 top winners are affected. Two trades (T#64, T#44) are completely unaffected because adds always occurred well above entry (clean trend continuation). One trade (T#81) had genuinely underwater adds — a V-shaped recovery where dip-buying was the optimal behavior. Two trades (T#31, T#63) had marginally-below-threshold adds that could be recovered by lowering the gate to 0.25 ATR.

**The V-shape problem is real but concentrated.** T#81 alone accounts for 47% of the total cost ($10,686 of $22,806). Whether this trade's V-shaped pattern recurs frequently is the key question for parameter selection.

---

### Question 2: Trace Proposal A Through Cascade Chain #7

**Chain #7** = Trades #69–74 (2024-05-27 → 2024-08-03), 6 consecutive emergency_dd exits, total loss $26,686.

#### Fill-by-fill trace with Proposal A (gate = 0.5 ATR)

**T#69:** PnL = −$3,516 | 5 fills | entry 2024-05-27

| Fill | Price | Avg Entry | ATR dist | Gate | Exit@65,553 |
|:-----|------:|----------:|---------:|:-----|:------------|
| 0 INITIAL | 70,444 | 70,444 | — | ALLOWED | |
| 1 ADD | 68,210 | 70,444 | −1.64 | **BLOCKED** | saves loss |
| 2 ADD | 68,976 | 69,641 | −0.48 | **BLOCKED** | saves loss |
| 3 ADD | 69,273 | 69,474 | −0.14 | **BLOCKED** | saves loss |
| 4 ADD | 71,772 | 69,456 | +1.61 | ALLOWED | |

Gate blocks **3/4 adds**. Trade PnL improves from −$3,516 to −$2,204 (saves $1,312).

**T#70:** PnL = −$3,142 | 3 fills | entry 2024-06-12

| Fill | Price | Avg Entry | ATR dist | Gate |
|:-----|------:|----------:|---------:|:-----|
| 0 INITIAL | 69,804 | 69,804 | — | ALLOWED |
| 1 ADD | 67,793 | 69,804 | −1.48 | **BLOCKED** |
| 2 ADD | 66,744 | 69,145 | −1.80 | **BLOCKED** |

Gate blocks **2/2 adds**. Position stays at initial size only. PnL: −$3,142 → −$2,160 (saves $982).

**T#71:** PnL = −$4,984 | 4 fills | entry 2024-06-20

All 3 adds blocked (fills at −1.0 to −0.6 ATR below entry). PnL: −$4,984 → −$2,094 (saves **$2,890**).

**T#72:** PnL = −$6,100 | 5 fills | entry 2024-06-26

All 4 adds blocked. Fills 3 and 4 at +0.30 and +0.27 ATR — green but below gate threshold. PnL: −$6,100 → −$2,068 (saves **$4,032**). This is the most impactful trade — the gate prevents 4 additions to a position that ultimately collapses.

**T#73:** PnL = −$2,689 | 3 fills | entry 2024-07-06

ADD 1 at +0.56 ATR — ALLOWED (just above gate). ADD 2 at −0.67 ATR — BLOCKED. PnL: −$2,689 → −$2,179 (saves $510).

**T#74:** PnL = −$6,255 | 8 fills | entry 2024-07-16

**0 adds blocked.** All 7 adds were made while position was green (+0.6 to +4.6 ATR above entry). The trade started well, pyramided heavily while profitable, then price collapsed from peak to emergency_dd. **Proposal A cannot protect against this pattern** — it only blocks adds into falling positions, not profitable positions that later reverse.

#### Chain #7 Summary (Proposal A)

| Trade | Fills | Blocked | Actual PnL | PnL with gate | Savings |
|:------|------:|--------:|-----------:|--------------:|--------:|
| T#69 | 5 | 3/4 | −$3,516 | −$2,204 | +$1,312 |
| T#70 | 3 | 2/2 | −$3,142 | −$2,160 | +$982 |
| T#71 | 4 | 3/3 | −$4,984 | −$2,094 | +$2,890 |
| T#72 | 5 | 4/4 | −$6,100 | −$2,068 | +$4,032 |
| T#73 | 3 | 1/2 | −$2,689 | −$2,179 | +$510 |
| T#74 | 8 | **0/7** | −$6,255 | −$6,155 | +$100 |
| **Total** | **28** | **13/22** | **−$26,686** | **−$16,860** | **+$9,827 (37%)** |

**Key finding:** Proposal A saves $9,827 = 37% of chain #7's total loss. But **T#74 is the blind spot** — a $6,255 loss where the gate has zero effect because all adds were legitimately profitable at the time. T#74 represents the "profitable-then-crash" failure mode that no position-level PnL gate can detect.

---

### Question 3: A vs B vs C Comparison on Both Trace Sets

#### Trace Set 1: Top 5 Winners (cost = PnL forfeited by blocking profitable adds)

| Trade | Actual PnL | Proposal A (Δ) | Proposal B (Δ) | Proposal C (Δ) |
|:------|:-----------|:---------------|:---------------|:---------------|
| T#81 | $26,247 | $-10,536 (−40%) | $+149 (0%) | $-10,536 (−40%) |
| T#31 | $21,618 | $-7,993 (−37%) | $+70 (0%) | $-13,454 (−62%) |
| T#64 | $18,002 | $+134 (0%) | $+134 (0%) | $+134 (0%) |
| T#44 | $17,000 | $+104 (0%) | $-6,445 (−38%) | $-8,002 (−47%) |
| T#63 | $16,733 | $-3,939 (−24%) | $+117 (0%) | $-9,609 (−57%) |
| **Total** | **$99,600** | **$-22,231 (−22%)** | **$-5,975 (−6%)** | **$-41,467 (−42%)** |

**Winner: Proposal B.** Only 6% cost to top winners, vs 22% for A and 42% for C.

- **Proposal B** barely fires on winners because portfolio NAV is near its rolling high during trends. The 14% DD threshold is never breached during T#81, T#31, T#64, T#63. Only T#44 is affected (preceded by T#43 emergency_dd which depressed NAV).
- **Proposal A** costs 22% because it blocks dip-adds in V-shaped recoveries endemic to BTC trend starts.
- **Proposal C** costs 42% because the 8-bar proof period blocks adds on EVERY trade's first 32 hours, regardless of conditions.

#### Trace Set 2: Chain #7 (savings = loss avoided by blocking doomed adds)

| Trade | Actual PnL | Proposal A (Δ) | Proposal B (Δ) | Proposal C (Δ) |
|:------|:-----------|:---------------|:---------------|:---------------|
| T#69 | −$3,516 | +$1,312 | +$122 | +$122 |
| T#70 | −$3,142 | +$982 | +$91 | +$673 |
| T#71 | −$4,984 | +$2,890 | +$120 | +$2,714 |
| T#72 | −$6,100 | +$4,032 | +$3,562 | +$3,562 |
| T#73 | −$2,689 | +$510 | +$1,565 | +$1,565 |
| T#74 | −$6,255 | +$100 | +$100 | +$896 |
| **Total** | **−$26,686** | **+$9,827 (37%)** | **+$5,559 (21%)** | **+$9,532 (36%)** |

**Winner on chain #7: Proposal A** (37% savings), closely followed by C (36%). B only saves 21%.

- **Proposal A** excels on T#69–T#72 (where adds were into falling positions) but fails completely on T#74 (adds were green).
- **Proposal B** only kicks in at T#72 (rolling DD finally crosses 14% after 3 consecutive ED trades). Too slow for the early chain trades where NAV DD is still small (0.2% → 6% → 9%).
- **Proposal C** matches A's performance closely because the proof period catches the same early adds. But the 8-bar blanket delay costs more on winners.

#### Full-Portfolio Static Analysis (all 103 trades)

**THIS IS THE CRITICAL TABLE. It reverses the original recommendation.**

| Proposal & Parameter | ED Savings | Non-ED Cost | NET | Verdict |
|:---------------------|:-----------|:------------|:----|:--------|
| **A** (gate=0.00) | $38,505 | $55,789 | **−$17,284** | ✗ net negative |
| **A** (gate=0.25) | $43,540 | $64,238 | **−$20,698** | ✗ net negative |
| **A** (gate=0.50) | $47,684 | $87,723 | **−$40,038** | ✗ net negative |
| **A** (gate=0.75) | $53,408 | $96,680 | **−$43,272** | ✗ net negative |
| **A** (gate=1.00) | $60,660 | $106,588 | **−$45,928** | ✗ net negative |
| **B** (w=36, t=14%) | $4,001 | $160 | **+$3,841** | ✓ net positive |
| **B** (w=60, t=14%) | $8,923 | $2,962 | **+$5,961** | ✓ net positive |
| **B** (w=90, t=14%) | $12,277 | $5,453 | **+$6,824** | ✓ net positive |
| **B** (w=60, t=10%) | $12,368 | $12,940 | −$573 | ~ breakeven |
| **B** (w=60, t=18%) | $3,502 | — | +$5,360 | ✓ net positive |
| **C** (proof=3) | $8,068 | $17,665 | **−$9,597** | ✗ net negative |
| **C** (proof=5) | $26,732 | $53,441 | **−$26,709** | ✗ net negative |
| **C** (proof=8) | $36,467 | $83,112 | **−$46,646** | ✗ net negative |
| **C** (proof=12) | $43,902 | $96,338 | **−$52,437** | ✗ net negative |

#### Why the Full-Portfolio Numbers Reverse the Recommendation

**Proposal A is net-negative at every gate level** because BTC trend-following inherently involves V-shaped dip-and-rally patterns on winning trades. The gate blocks adds during these dips — and those dip-adds are the highest-PnL fills because they have the lowest entry prices in eventually-large winners. Across 67 non-ED trades, 123 adds are blocked at gate=0.5, costing $87.7K in forgone PnL — nearly twice the $47.7K saved from ED trades.

**Proposal C is also net-negative** for the same reason amplified: the blanket proof period blocks ALL early adds on every new trade, not just the losing ones. The 81 blocked non-ED adds (proof=8) forfeit $83K.

**Proposal B is the only net-positive approach** because portfolio-level DD is a narrow, targeted discriminator. The 14% rolling DD brake activates only during genuine cascade regimes (when the equity curve is actually damaged), not during individual trade dips. Across all 103 trades, B (w=90, t=14%) blocks only 17 total adds — but those 17 are disproportionately concentrated in the worst cascade sequences.

#### Honesty Caveat: Limitations of This Static Analysis

1. **Upper bound on cost.** Blocked fills are treated as permanently lost. In reality, VDO may re-fire on a later bar when the gate/brake clears, and the add happens at a (higher) price. The true cost is the *price difference* between the original fill and the delayed fill — not the entire fill's PnL contribution. A live backtest would show lower costs for all proposals.

2. **Single-backtest path.** All numbers come from one 7-year backtest. The 2 V-shaped winners (T#81, T#31) that dominate Proposal A's cost may or may not represent recurring BTC behavior. A block-bootstrap or walk-forward analysis would test stability.

3. **Proposal A + B combo not tested.** A position-level PnL gate (A) combined with a portfolio-level DD brake (B) might capture the best of both: A's surgical blocking during normal markets plus B's cascade prevention during drawdown regimes. The combination could be net-positive if A's cost is reduced by only activating A when B is NOT active (i.e., A only fires during healthy equity periods, and B takes over during drawdowns).

---

### Revised Recommendation

The original recommendation (Proposal A) was based on Phase 1 attribution showing ADDs contribute 58.9% of ED losses. That attribution is correct — but it omits the symmetric cost: ADDs also contribute ~42% of non-ED trade PnL. The net-negative static analysis forces a revision.

**Primary recommendation: Proposal B (Rolling-Window Equity DD Brake)**

Parameters: `rolling_brake_window_bars = 90`, `brake_dd_threshold = emergency_dd_pct / 2` (14%)

Rationale:
1. **Only net-positive proposal** across all parameter sweeps (+$6,824 at best config)
2. **Minimal winner damage** — 6% cost to top 5 winners vs 22% (A) or 42% (C)
3. **Activates when needed** — 14% rolling DD is a high bar that's only breached during genuine cascade regimes
4. **Why it differs from V13's failure:** V13 used ATH-based equity peak (permanent reference). B uses rolling N-bar peak (self-resetting reference). The rolling window means the brake resets after ~15 days of flat/up equity, preventing permanent activation

**Secondary option: Proposal A + B composite**

If the portfolio manager wants both per-trade and portfolio-level protection, implement B first (net-positive), then conditionally add A only when portfolio is in a healthy equity state (rolling DD < 5%). This would give A's surgical blocking during normal markets while B's cascade brake handles drawdown regimes — avoiding A's worst failure mode (blocking dip-adds during trends that happen to follow mild equity dips).

**Await approval before implementing.**

---

## Appendix C: Proposal B Pre-Implementation Validation

*Added 2026-02-26. Answers two gating questions before prototyping.*

### C.1 Concentration Check

**Question:** Does the +$6,824 net at (w=90, t=14%) come from a broad set of episodes, or is it driven by 1–2 trades (Overlay A pattern)?

#### Per-trade decomposition (w=90, t=14%)

| Rank | T# | Exit reason | Period | Blocked | Net contrib | Cum% |
|:-----|:---|:------------|:-------|--------:|------------:|-----:|
| 1 | 44 | trailing_stop | 2021-09→2021-10 | 1 | −$6,549 | −96% |
| 2 | 89 | trailing_stop | 2025-02→2025-03 | 3 | +$3,748 | −41% |
| 3 | 72 | emergency_dd | 2024-06→2024-07 | 2 | +$3,446 | +9% |
| 4 | 74 | emergency_dd | 2024-07→2024-08 | 3 | +$3,354 | +59% |
| 5 | 28 | trailing_stop | 2020-09→2020-10 | 4 | −$2,275 | +25% |
| 6 | 90 | emergency_dd | 2025-03 | 3 | +$2,027 | +55% |
| 7 | 88 | emergency_dd | 2025-02 | 2 | +$1,975 | +84% |
| 8 | 73 | emergency_dd | 2024-07 | 2 | +$1,475 | +106% |
| 9 | 75 | trailing_stop | 2024-08 | 1 | −$212 | +102% |
| 10 | 27 | trailing_stop | 2020-09 | 4 | −$160 | +100% |
| 11 | 57 | trailing_stop | 2023-08 | 2 | −$3 | +100% |
| | **Total** | | | **27** | **+$6,824** | |

**Positive contributors (gate helped):** 6 trades, total +$16,024
- 5 emergency_dd trades (T#72, 73, 74, 88, 90) = +$12,277 from Chain #7 and Chain #8
- 1 trailing_stop (T#89) = +$3,748 — this is a short trade that exited profitably but *would have lost more* if adds continued during the DD regime

**Negative contributors (gate hurt):** 5 trades, total −$9,200
- T#44 alone = −$6,549 (71% of total cost). This is the 2021-Sep BTC rally that followed a period where rolling DD was at 15.2%. The gate blocked 1 add that turned out to be the cheapest fill in a +$17K winner.
- T#28 = −$2,275 (similar pattern: 2020-Sep rally emerging from depressed NAV)
- T#75, 27, 57 = −$375 combined (negligible)

**Concentration metrics:**

| Metric | Value | Interpretation |
|:-------|:------|:---------------|
| Trades affected | 11 / 103 | Gate only fires on 11% of trades |
| Herfindahl-Hirschman Index | 0.1501 | Moderately concentrated |
| Effective N (1/HHI) | 6.7 trades | Not a 1–2 trade story |
| Top-2 absolute share | 41% | Below 70% threshold |
| Positive contributors | 6 trades across 3 episodes | Dispersed across 2024-Q2, 2025-Q1, and one standalone |
| Negative contributors | 5 trades across 3 episodes | T#44 dominates cost side |

#### Concentration verdict: **CONDITIONAL PASS**

The +$6.8K net is NOT a 1–2 episode story — the savings come from 6 trades across 3 distinct time periods (Chain #7: 2024-May–Aug, Chain #8: 2025-Jan–Feb, standalone T#89). Top-2 absolute share = 41%, well below the 70% flag threshold.

**However, there is a cost-concentration warning:** T#44 alone contributes −$6,549 = 71% of total cost. If we remove T#44 (an Oct 2021 rally during BTC's final bull run), the net jumps from +$6,824 to +$13,373 — nearly 2×. This means the gate's economics are sensitive to whether BTC produces a strong trend immediately after a 15%+ equity drawdown. That specific pattern (deep DD → instant V-recovery → large winner) happened exactly once in 7 years. **If it recurs, gate cost doubles. If it doesn't, gate value doubles.**

This is the exact same outlier sensitivity that the cascade analysis (Appendix B, Step 2, §3.2) flagged from the other side: single large trades dominate both the cascade losses AND the gate costs. The system is inherently fat-tailed. The gate does not eliminate this — it merely shifts which tail dominates.

---

### C.2 Sensitivity Analysis: w × t Grid

Static fill analysis across w ∈ {60, 90, 120} bars × t ∈ {10%, 14%, 18%}.

#### Net impact (ED savings − non-ED cost)

| | t = 10% | t = 14% | t = 18% |
|:-----|--------:|--------:|--------:|
| **w = 60** | −$573 | **+$5,961** | **+$5,360** |
| **w = 90** | −$2,215 | **+$6,824** | **+$5,360** |
| **w = 120** | −$2,328 | **+$6,182** | **+$8,263** |

#### Trades affected / adds blocked

| | t = 10% | t = 14% | t = 18% |
|:-----|--------:|--------:|--------:|
| **w = 60** | 22 trades / 56 adds | 7 / 17 | 3 / 7 |
| **w = 90** | 29 / 81 | 11 / 27 | 3 / 7 |
| **w = 120** | 29 / 86 | 13 / 38 | 6 / 20 |

#### Effective N (concentration)

| | t = 10% | t = 14% | t = 18% |
|:-----|--------:|--------:|--------:|
| **w = 60** | 9.1 | 4.8 | 3.0 |
| **w = 90** | 14.2 | 6.7 | 3.0 |
| **w = 120** | 14.2 | 7.6 | 4.2 |

#### Plateau analysis

**Row-wise (fix t, vary w):**
- t = 10%: **all negative.** Gate fires too often (56–86 adds blocked), catches too many winners.
- t = 14%: **all positive** (+$5,961 to +$6,824). Robust across all three windows.
- t = 18%: **all positive** (+$5,360 to +$8,263). Fewer trades but all in deep-DD episodes.

**Column-wise (fix w, vary t):**
- No single window is all-positive across all thresholds. t = 10% breaks every window.

**The t = 14% column is a genuine plateau.** NET is positive for all three windows, ranging from +$5,961 to +$6,824 (±7% variation). This is not a single-point optimum — the mechanism works because 14% is exactly the right severity threshold that separates cascade regimes from normal dips.

**The (w=120, t=18%) cell is the single-path maximum** at +$8,263. But it only affects 6 trades — approaching the concentration danger zone (Effective N = 4.2). It's higher-variance and more likely to lose its edge out-of-sample.

#### Sensitivity verdict: **PASS**

The t = 14% column forms a clear plateau (3/3 cells positive, <7% internal variation). This is the structural signature of a mechanism that works for the right reason — the threshold aligns with the strategy's own risk framework (emergency_dd_pct / 2) rather than being an arbitrary fit.

**Recommended prototype parameters:** `w = 90`, `t = emergency_dd_pct / 2` (14% for current config).

Rationale for w = 90 over 60 or 120:
- w = 60: nearly identical NET (+$5,961 vs +$6,824) but fewer trades affected (7 vs 11) — shorter memory misses some cascade buildup
- w = 120: slightly lower NET (+$6,182) and 38 adds blocked (more collateral damage on winning trades)
- w = 90: best NET in the t=14% row, moderate intervention (27 adds), Effective N = 6.7 (healthiest concentration)

---

### C.3 Implementation Spec: Rolling-Window Equity Drawdown Brake

*Both gating questions passed. Below is the implementation spec for prototyping. No code — only specification.*

#### 1. Mechanism Summary

**Name:** Rolling Equity Brake (overlay_equity_brake)

**One-sentence description:** When portfolio NAV is ≥ `brake_dd_threshold` below its rolling `brake_window_bars`-bar peak, block ALL pyramiding adds (exposure > 0.01). Initial entries (exposure ≈ 0) are never blocked.

#### 2. Parameters

| Parameter | Type | Default | Range for grid | Description |
|:----------|:-----|:--------|:---------------|:------------|
| `enable_equity_brake` | bool | `False` | {True} | Master switch |
| `brake_window_bars` | int | 90 | [60, 120] | Rolling lookback window in H4 bars |
| `brake_dd_threshold` | float | *derived* | [0.10, 0.20] | DD level that triggers brake. Default = `emergency_dd_pct / 2` |

**Derived default:** `brake_dd_threshold = emergency_dd_pct / 2`. For the current V10 config where `emergency_dd_pct = 0.28`, this yields 0.14. The threshold is computed once at config load, not dynamically. This ties the brake to the strategy's own risk framework without adding a free parameter to the grid.

**Not a parameter:** The brake action is binary (block all adds), not a multiplier. V13 P1 showed that fractional throttles (mult=0.20) are too weak to prevent cascades and too indiscriminate to preserve CAGR. Binary "block or don't block" is cleaner and was validated in the static analysis.

#### 3. State Machine

```
States: NORMAL, BRAKING

Transitions:

  NORMAL → BRAKING:
    Condition: rolling_dd ≥ brake_dd_threshold
    Effect: set max_add_per_bar_effective = 0.0

  BRAKING → NORMAL:
    Condition: rolling_dd < brake_dd_threshold
    Effect: restore max_add_per_bar_effective = cfg.max_add_per_bar

Rolling DD is recomputed every bar:
  rolling_dd = 1.0 - (current_NAV / max(NAV over last brake_window_bars bars))
```

The state machine has **zero hysteresis** by design. The brake activates and deactivates purely based on the rolling DD crossing the threshold. No counters, no delay, no memory beyond the NAV buffer. This is intentional — the rolling window already provides smoothing (a single good bar cannot flip a 90-bar window), and adding hysteresis would introduce a second implicit parameter.

#### 4. Required State Variables

| Variable | Type | Scope | Description |
|:---------|:-----|:------|:------------|
| `_nav_ring_buffer` | `collections.deque[float]` | Strategy instance | Circular buffer of length `brake_window_bars`. Stores NAV at bar close. |
| `_equity_brake_active` | `bool` | Strategy instance | Current state: True if BRAKING |

**Buffer initialization:** Fill with `initial_cash` (the starting NAV) during warm-up. This ensures the brake cannot accidentally fire during early bars when the buffer is partially filled.

#### 5. Gate Placement in Code Flow

**File:** `v10/strategies/v8_apex.py`

**Location:** Inside `_check_entry()`, after Gate 0 (Overlay A cooldown) and before Gate 1 (Regime), insert new gate:

```
_check_entry(self, state, idx, mid, regime):
    Gate 0: Overlay A cooldown check          ← existing (line ~447)
  → Gate 0.5: EQUITY BRAKE                   ← NEW INSERT POINT
    Gate 1: Regime RISK_OFF check              ← existing (line ~451)
    Gate 2: Cooldowns                          ← existing (line ~453)
    Gate 3: VDO threshold                      ← existing (line ~457)
    ...
    sz = min(sz, max_add_per_bar, gap)         ← existing (line ~532)
```

**Gate 0.5 pseudocode:**
```
if cfg.enable_equity_brake and state.exposure > 0.01:
    if self._equity_brake_active:
        return None  # block add
```

**Buffer update location:** Inside `on_bar()`, before calling `_check_entry()` or `_check_exit()`. The NAV must be appended to the ring buffer at every bar, regardless of position state:

```
on_bar(self, state):
    # Update equity brake buffer (every bar, unconditionally)
    if cfg.enable_equity_brake:
        self._nav_ring_buffer.append(state.nav)
        peak = max(self._nav_ring_buffer)
        rolling_dd = 1.0 - state.nav / peak if peak > 0 else 0.0
        self._equity_brake_active = rolling_dd >= cfg.brake_dd_threshold

    # ... rest of on_bar logic (existing)
```

**Why Gate 0.5 (not later):** The brake must fire before any other entry logic — including regime checks, VDO thresholds, and cooldowns. If it fires later (e.g., at the sizing stage), the strategy would still emit add_signal events for blocked bars, polluting the event log with signals that were algorithmically valid but risk-management-blocked. Gate position 0.5 makes the brake invisible to downstream logic.

**Why `state.exposure > 0.01` guard:** The brake must NEVER block initial entries (exposure ≈ 0). The strategy needs to re-enter after emergency_dd exits — preventing re-entry would degrade CAGR catastrophically. The brake only prevents position *growth* during drawdown, not position *creation*.

#### 6. Config Integration

Add to `V8ApexConfig` dataclass (in `v8_apex.py`):

```
@dataclass
class V8ApexConfig:
    ...existing fields...

    # Equity Brake overlay
    enable_equity_brake: bool = False
    brake_window_bars: int = 90
    brake_dd_threshold: float | None = None  # None → auto = emergency_dd_pct / 2
```

In the config post-init or the strategy `on_init()`:
```
if cfg.brake_dd_threshold is None:
    cfg.brake_dd_threshold = cfg.emergency_dd_pct / 2
```

The `None` sentinel with auto-derivation ensures the brake threshold is always proportional to the existing risk framework, even when `emergency_dd_pct` is changed during grid search.

#### 7. Event Logging

Add a new event type `add_brake_blocked` to the event log when the brake fires. Fields:

| Field | Value |
|:------|:------|
| `event_type` | `"add_brake_blocked"` |
| `reason` | `"equity_brake"` |
| `nav` | current NAV |
| `rolling_dd` | computed rolling DD |
| `peak_nav` | max of ring buffer |
| `exposure_before` | state.exposure |

This enables post-hoc analysis of brake activation frequency, false positive rate, and overlap with regime labels.

#### 8. Grid Search Plan

| Parameter | Values | Notes |
|:----------|:-------|:------|
| `enable_equity_brake` | {True} | Fixed — we're testing the mechanism |
| `brake_window_bars` | {60, 90, 120} | 3 values from sensitivity grid |
| `brake_dd_threshold` | {auto} | Fixed at `emergency_dd_pct / 2` — NOT a grid axis |

**Grid size: 3 cells** (window only). The threshold is derived, not searched. This is deliberate — the sensitivity analysis showed t=14% is a plateau that works for structural reasons (half of emergency DD). Searching over t would find the same plateau and waste compute.

**Acceptance criteria:**
1. NET impact > 0 (saves more ED loss than it costs in winner PnL)
2. Effective N ≥ 4 (not driven by 1–2 trades)
3. CAGR degradation < 3pp vs baseline
4. No new maximum drawdown regime (MDD must not increase)

#### 9. Failure Modes and Monitoring

| Failure mode | Detection | Mitigation |
|:-------------|:----------|:-----------|
| **Brake stays on too long** — prolonged mild drawdown keeps rolling DD near threshold | Count consecutive bars where brake is active; flag if > 2× window | Consider adding hard timeout (break after 2× window bars regardless) — NOT in v1 prototype |
| **V-recovery blocked** — brake is active during sharp reversal from cascade | Compare brake-on bars with subsequent price trajectory | Accept as known cost — this is the tradeoff we analyzed |
| **Buffer initialization bias** — early bars with `initial_cash` fill cause artificially low DD | First `window` bars always show DD ≈ 0 | Non-issue: the strategy can't have equity DD in the first few bars anyway |
| **Regime interaction** — brake fires during RISK_OFF (regime already blocks entries) | Check overlap between brake-active and RISK_OFF bars | No harm — both block adds, no conflicting behavior |

#### 10. What This Spec Does NOT Cover

- **Proposal A (PnL Gate):** Deferred. The full-portfolio static analysis showed it's net-negative standalone. May be revisited as A+B composite after B prototype validates.
- **Hysteresis / cooldown-after-brake:** Intentionally omitted for v1. The rolling window provides natural smoothing. If backtests show rapid on/off oscillation near the threshold, add a 3-bar debounce in v2.
- **Block initial entries during brake:** Explicitly excluded. Only ADDs are blocked. Re-entry after emergency_dd must remain allowed.

**Spec complete. Ready for implementation upon approval.**
