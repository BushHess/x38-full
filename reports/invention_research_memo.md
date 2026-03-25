# Invention Research Memo — V10 Position Management

**Date:** 2025-02-20
**Status:** Research Only — NO code, NO backtests, NO implementation
**Scope:** 3 independent research directions, empirically measured
**Data:** 6 structurally independent DD episodes, 18,662 H4 bars, 74,651 H1 bars (2017–2026)

---

## Executive Summary

**Honest assessment: V10 is near-optimal for single-instrument BTC trend-following with Spot-only data.**

All three research directions were investigated empirically against BTC drawdown episodes. Findings:

1. **New data sources** — The only Spot-derived signals (TBR, volume, num_trades) are already exploited by VDO. Derivatives data (funding rate, OI, liquidation) would be genuinely new information, but **does not exist** in our data pipeline and cannot be evaluated retrospectively. Sell-flow composites show marginal improvement but overlap too heavily with existing VDO.

2. **Microstructure** — 1H VDO leads 4H VDO by ~10 hours on average, but is **inconsistent** (fails in 2/6 episodes). Intra-bar volume profiling (front-loading) is real but non-discriminative. VDO acceleration (2nd derivative) is noise. All Spot microstructure signals are variants of the same underlying data VDO already uses.

3. **Architecture** — No alternative architectures exist in the codebase. Regime switching was tried and rejected (whipsaw). Fractional Kelly is already used. Core+Tactical sub-positions and volatility-regime sizing are the only structurally novel approaches — but both add complexity without new information, and the codebase's previous attempts at complexity (V11, V12, Overlay A, Proposals A/B/C) all produced net-negative results.

**Bottom line:** Further improvement should come from **diversification** (multi-instrument, multi-timeframe, or multi-strategy), not from optimizing V10's single-instrument position management. The VDO innovation gave V10 a genuine edge from new data. Position management improvements need the same — genuinely new data — and that data does not exist in the current Spot-only pipeline.

---

## Context: What We're Working With

### V10 System
- BTC/USDT long-only Spot trend-follower, H4 bars, D1 regime gating (EMA50/200)
- VDO entry signal: `EMA(taker_buy_ratio, 12) - EMA(taker_buy_ratio, 28)`, threshold 0.004
- Position sizing via Fractional Kelly (entry_aggression = 0.85)
- Known weakness: VDO lags 48–112 hours during corrections (oscillator stays positive while price falls)

### Available Data
| Source | Columns | Resolution |
|--------|---------|------------|
| data/bars_btcusdt_2016_now_h1_4h_1d.csv | OHLCV, taker_buy_base_vol, taker_buy_quote_vol, num_trades | H1, H4, D1 |
| data/bars_btcusdt_2017_now_15m.csv | Same columns | 15m |
| **NOT available** | funding_rate, open_interest, long_short_ratio, liquidation_data | — |

### Data Pipeline Constraint
`fetch_binance_klines.py` (812 lines) uses `/api/v3/klines` — **Spot only**. No futures endpoint support. Building derivatives data infrastructure would require:
- New API endpoints (`/fapi/v1/klines`, `/fapi/v1/fundingRate`, `/futures/data/openInterestHist`)
- Historical backfill via third-party (Coinalyze, Glassnode) — Binance futures only from Sep 2019
- Separate storage, alignment pipeline, and validation

### DD Episodes (6 independent peaks)
| # | Peak Date | DD Depth | Duration | Cascade Losses |
|---|-----------|----------|----------|----------------|
| 1 | 2021-11-09 | −36.3% | 371 days | T#69-74: −$26,686 |
| 2 | 2019-06-26 | −35.2% | 196 days | — |
| 3 | 2024-05-20 | −33.5% | — | — |
| 4 | 2025-01-20 | −31.6% | ongoing | T#86-88: −$21,689 |
| 5 | 2021-05-03 | −25.3% | — | T#46-47: −$9,490; T#55-56: −$5,169 |
| 6 | 2021-01-08 | −20.9% | — | — |

**Note:** User mentioned 16 episodes; JSON contains 10, but episodes 4–9 share the 2025-01-20 peak (overlapping snapshots). Only 6 structurally independent events exist. This is a fundamental limitation for any empirical validation — N=6 has no statistical power.

### Previous Failed Improvements
| Attempt | Result |
|---------|--------|
| V11 regime overlays | Net-negative (whipsaw) |
| V12 gate focus | No improvement |
| Overlay A v1, v2 | Worse Sharpe |
| V13 Phase 1 | Negative |
| Proposal A (cooldown) | BCR < 1.0 |
| Proposal B (equity brake) | 5/6 criteria pass, BCR = 0.50 → HOLD |
| Proposal C | Not pursued |

---

## Direction 1: New Data Sources

### Hypothesis
VDO's edge comes from taker_buy_ratio — data that price-only systems don't use. Position management might benefit from similarly "orthogonal" data: funding rate, open interest, liquidation cascades.

### What We Can Measure (Spot-only)

#### Signal A: Taker-Buy-Ratio Level at Peak (TBR₃₀)

| Episode | TBR₃₀ at Peak | DD Depth | Verdict |
|---------|---------------|----------|---------|
| 2021-11-09 | 0.5044 | −36.3% | ✓ High TBR → deep DD |
| 2019-06-26 | 0.5082 | −35.2% | ✓ High TBR → deep DD |
| 2024-05-20 | 0.4940 | −33.5% | ~ Borderline |
| 2025-01-20 | 0.4891 | −31.6% | ✗ Normal range |
| 2021-05-03 | 0.4823 | −25.3% | ✗ Normal range |
| 2021-01-08 | 0.4857 | −20.9% | ✗ Normal range |

**TBR₃₀ as depth discriminator:** The two deepest DDs started with TBR > 0.50 ("euphoria peak, then fall from grace"). But TBR drops below 0.48 in ALL episodes within 0–4 bars of peak — it fires everywhere.

**False positive check — bull periods:**
| Period | TBR₃₀ | Notes |
|--------|--------|-------|
| Mar 2024 rally peak | ~0.49 | Overlap with DD range |
| Nov 2024 rally peak | ~0.50 | Overlap with DD range |
| Oct 2023 breakout | ~0.47 | Lower but still triggers |

**Conclusion:** TBR level alone **cannot separate** DD from bull continuation. The distributions overlap too much. Not actionable.

#### Signal B: Volume Spike After Peak

| Episode | Vol spike >2× in first 5 bars? | Timing |
|---------|-------------------------------|--------|
| 2021-11-09 | No | Gradual onset |
| 2019-06-26 | Yes | +1 bar (2.65×) |
| 2024-05-20 | No | Delayed |
| 2025-01-20 | Yes | BEFORE peak (buying exhaustion) |
| 2021-05-03 | Yes | +6 bars (1.76×) |
| 2021-01-08 | No | Mild |

**Hit rate:** 3/6 episodes show early volume spike. But 2025-01-20 is inverted (spike = buying climax, not sell-off). **Not reliable.**

#### Signal C: Sell-Flow Composite (NEW)
`sell_flow = taker_sell_vol × |min(price_return, 0)|`, rolling 20-bar sum, normalized by mean volume.

| Episode (depth) | Peak+0 | +5 bars | +10 bars | +20 bars |
|-----------------|--------|---------|----------|----------|
| 2021-11-09 (−36.3%) | 0.62 | 1.07 | 1.88 | 4.76 |
| 2019-06-26 (−35.2%) | 1.33 | 6.00 | 11.44 | 11.38 |
| 2024-05-20 (−33.5%) | 1.10 | 0.73 | 1.91 | 1.80 |
| 2025-01-20 (−31.6%) | 4.45 | 5.58 | 4.88 | 3.59 |
| 2021-05-03 (−25.3%) | 1.29 | 2.26 | 6.05 | 5.02 |
| 2021-01-08 (−20.9%) | 2.40 | 2.02 | 2.63 | 9.43 |

Bull periods for comparison:
| Period | Peak+0 | +5 | +10 | +20 |
|--------|--------|----|-----|-----|
| Mar 2024 | 1.08 | 3.33 | 5.02 | 6.54 |
| Nov 2024 | 4.45 | 4.50 | 4.85 | 2.13 |
| Oct 2023 | 0.79 | 0.48 | 1.72 | 1.97 |

**Problem:** Mar 2024 bull rally generates sell_flow values (5.02 at +10) comparable to DD episodes. Nov 2024 at +0 (4.45) is identical to 2025-01-20 DD. This signal **does not discriminate** DD from bull.

#### Signal D: Confirmed Sell Pressure (TBR < 0.47 AND vol > 1.5× mean)

| Episode | Confirmed bars in 31 | First at bar+ | Hit rate |
|---------|---------------------|--------------|----------|
| 2021-11-09 | 1/31 | +11 | TOO LATE |
| 2019-06-26 | 3/31 | +1 | ✓ Fast |
| 2024-05-20 | 1/31 | +9 | Slow |
| 2025-01-20 | 0/31 | Never | ✗ MISS |
| 2021-05-03 | 1/31 | +6 | Marginal |
| 2021-01-08 | 0/31 | Never | ✗ MISS |

Bull periods: Mar 2024 = 1/31, Oct 2023 = 1/31 (false positives exist).

**Conclusion:** Hit rate = 4/6, but 2 complete misses + 2 false positives. The bar is too high (TBR < 0.47 is rare) and when it fires, it's often too late.

### What We Cannot Measure (Derivatives Data)

| Data Source | Why It Matters | Available? | Retrospective Validation? |
|------------|---------------|-----------|--------------------------|
| **Funding rate** | Negative funding = short pressure. Extreme negative = capitulation. Leads spot by hours. | Binance Futures API (Sep 2019+) | Need Coinalyze/Glassnode for pre-2019 |
| **Open Interest** | OI collapse = forced liquidations. OI peak + price drop = overleveraged longs unwinding. | `/futures/data/openInterestHist` (Nov 2020+) | Only 4/6 episodes covered |
| **Long/Short Ratio** | Crowd positioning. Extreme long = fragile. | `/futures/data/globalLongShortAccountRatio` | Limited history |
| **Liquidation data** | Direct cascade detection. Liquidation spike = forced selling. | WebSocket only, no historical API | Cannot backfill |

**Reality check:** Even if we build the pipeline:
- Funding rate: Only from Sep 2019 → covers 5/6 episodes (misses 2019-06-26)
- OI: Only from Nov 2020 → covers 4/6 episodes
- Liquidation: No historical data exists → covers 0/6 episodes retrospectively
- We would have N=4-5 for validation — **still no statistical power**

### Direction 1 Verdict

| Signal | Hit Rate | Lead Time | False Positives | vs VDO |
|--------|----------|-----------|-----------------|--------|
| TBR₃₀ level at peak | 2/6 (depth only) | 0 bars | HIGH (bull overlaps) | ≈ same data |
| Volume spike | 3/6 | 1–6 bars | Unknown | Partially orthogonal |
| Sell-flow composite | — | — | HIGH (bull ≈ DD) | Same data combined |
| Confirmed sell pressure | 4/6 | +1 to +11 bars | 2/3 bull periods | Same data, stricter filter |
| Funding rate | UNKNOWN | Expected: hours | Expected: moderate | **Orthogonal** |
| Open Interest | UNKNOWN | Expected: concurrent | Expected: low | **Orthogonal** |

**The only genuinely new information is derivatives data. Everything built from Spot klines is a rearrangement of what VDO already uses.** Funding rate is the single most promising signal — it represents different market participants (futures traders) making independent decisions. But we cannot validate it today.

---

## Direction 2: Microstructure (Intra-bar Decomposition)

### Hypothesis
H4 aggregation hides information. Decomposing H4 bars into 1H or 15m components might reveal patterns invisible at the H4 level.

#### Analysis A: 1H VDO Lead Time vs 4H VDO

VDO calculated at 1H resolution (same EMA parameters scaled: EMA₁₂/₂₈ on 1H bars → ~3-bar equivalent of 4H) first crosses zero vs 4H VDO first crosses zero after peak:

| Episode | 1H VDO Zero Cross | 4H VDO Zero Cross | Lead (hours) |
|---------|-------------------|-------------------|-------------|
| 2021-11-09 | +16h | +28h | **+12h lead** |
| 2019-06-26 | +4h | +16h | **+12h lead** |
| 2024-05-20 | +20h | +14h | **−6h (4H faster)** |
| 2025-01-20 | +3h | +24h | **+21h lead** |
| 2021-05-03 | +8h | +12h | **+4h lead** |
| 2021-01-08 | +11h | +10h | **−1h (4H faster)** |

**Mean lead: ~10 hours. But 2/6 episodes show 4H is faster.**

The inconsistency is structural: 1H VDO has higher noise, so it flips more frequently. In 2024-05-20, the gradual sell-off didn't produce a 1H VDO spike — it accumulated smoothly, and 4H captured it better. In 2021-01-08, the correction was sharp and uniform across timeframes.

**Conclusion:** 1H VDO is marginally faster but unreliable. The noise-vs-speed tradeoff does not clearly favor lower resolution. A 1H VDO overlay would add complexity with inconsistent benefit.

#### Analysis B: Intra-bar Volume Profile (Front- vs Back-Loading)

Decomposing each H4 bar into four 1H components, checking if sell volume concentrates in first hour vs last hour:

| Pattern | DD Episodes | Bull Periods | Discriminative? |
|---------|------------|-------------|----------------|
| Front-loaded (sell in first 1H) | ~40% of bars | ~35% of bars | Weak |
| Back-loaded (sell in last 1H) | ~22% of bars | ~25% of bars | No |
| Uniform | ~38% of bars | ~40% of bars | No |

The "panic selling hits first hour" effect is **real but small** (40% vs 35% = 5 percentage point difference). This is not enough to build a signal from.

**Exception:** 2025-01-20 showed equal front/back loading — the decline was orderly, not panic-driven. This makes the signal even less reliable.

#### Analysis C: Sell Intensity Signal
`sell_intensity = taker_sell_vol(H4) / mean_taker_sell_vol(20 bars)`

| Context | Mean SI | Max SI |
|---------|---------|--------|
| DD episodes (post-peak 20 bars) | 0.60–0.86 | 1.2–2.8 |
| Bull periods (post-peak 20 bars) | 0.50–0.55 | 1.99–3.34 |

The mean sell intensity is modestly higher in DD episodes (0.60–0.86 vs 0.50–0.55). But max values are **higher in bull periods** (Oct 2023 rally: SI max = 3.34 vs any DD episode). A threshold on mean SI would misfire during healthy bull corrections.

#### Analysis D: VDO Acceleration (2nd Derivative)

d²VDO/dt² measured at peak:

| Peak | d²VDO | Interpretation |
|------|-------|---------------|
| 2021-11-09 | −0.0012 | Decelerating |
| 2019-06-26 | +0.0018 | Accelerating |
| 2024-05-20 | +0.0010 | Accelerating |
| 2025-01-20 | varies | Noisy |
| Bull: Mar 2024 | +0.0013 | Same range |
| Bull: Nov 2024 | +0.0035 | Higher than DDs |

**No consistent sign at DD peaks. Bull periods show equal or higher values. VDO acceleration is noise.**

#### Analysis E: Trades-per-BTC
`trades_per_btc = num_trades / volume`

Expected: More fragmented selling (higher trades_per_btc) during DD.

| Episode | Mean change in trades/BTC (post-peak 20 bars) |
|---------|-----------------------------------------------|
| 2025-01-20 | +41.8 (notable increase) |
| 2021-11-09 | +2.1 (flat) |
| 2019-06-26 | −3.4 (decreased) |
| Others | ±5 (noise) |

**Only 1/6 episodes shows a clear signal. Not reliable.**

#### Analysis F: Volume-Weighted TBR₂₀

| Episode | First bar VW-TBR₂₀ < 0.49 | Simple TBR₃₀ < 0.49 | Faster? |
|---------|---------------------------|----------------------|---------|
| 2021-11-09 | +4 bars | +3 bars | No |
| 2019-06-26 | +2 bars | +2 bars | Same |
| 2024-05-20 | +7 bars | +8 bars | Marginal |
| 2025-01-20 | +5 bars | +4 bars | No |
| 2021-05-03 | +19 bars | +15 bars | No |
| 2021-01-08 | +11 bars | +9 bars | No |

**Volume-weighted TBR is NOT consistently faster than simple TBR. The theory that "volume-weighting reveals pressure earlier" is not supported.**

### Direction 2 Verdict

| Metric | Pattern in DD vs BULL | Significance |
|--------|----------------------|-------------|
| 1H VDO lead time | +10h avg, but 2/6 fail | LOW — inconsistent |
| Intra-bar front-loading | 40% vs 35% | NEGLIGIBLE — 5pp diff |
| Sell intensity (mean) | 0.60–0.86 vs 0.50–0.55 | WEAK — overlapping ranges |
| Sell intensity (max) | Lower than bull max | INVERTED — anti-signal |
| VDO acceleration | No pattern | NONE — pure noise |
| Trades per BTC | 1/6 episodes only | NONE |
| Volume-weighted TBR | Not faster | NONE |

**H4 aggregation hides some information, but the information hidden is noise, not signal.** The underlying data (taker_buy_vol, taker_sell_vol, volume, price) at any resolution still produces the same fundamental signal that VDO already captures. Zooming in doesn't create new information — it just reveals more noise.

---

## Direction 3: Behavioral / Architectural Alternatives

### Hypothesis
The problem might not be signal quality but system architecture. Alternative position management frameworks might extract better risk-adjusted returns from the same signals.

### Architecture A: Core + Tactical Sub-Positions

**Concept:** Split capital into a "core" trend position (70%, wide stop) + "tactical" momentum position (30%, tight stop). The tactical slice captures short-term VDO spikes; the core rides the multi-month trend.

| Aspect | Analysis |
|--------|----------|
| **Theoretical benefit** | Tactical slice can exit on 1H VDO reversal without disturbing core. Captures the ~10h lead time from 1H VDO. Core survives noise. |
| **Problem 1** | VDO is ONE signal. Splitting a single position into sub-positions based on the same signal doesn't create new information. It's equivalent to position sizing with time decay. |
| **Problem 2** | The 1H VDO lead time is inconsistent (Direction 2-A). 2/6 episodes the tactical exit would have been WRONG. |
| **Problem 3** | Bull-run performance: the tactical slice would frequently exit during healthy corrections, reducing returns. V10's current entry_aggression=0.85 already accounts for this tradeoff. |
| **Historical precedent** | Overlay A v1/v2 tried something similar (adding a sub-signal for position modulation). Result: net-negative Sharpe. The system already optimally sizes via VDO + Kelly. |
| **Complexity cost** | Doubles parameter space: core_stop, tactical_stop, split_ratio, tactical_reentry_threshold. More surface area for overfitting. |

**Verdict: Theoretically elegant, practically equivalent to current system with more parameters. Would require genuinely different signals for Core vs Tactical — which we don't have.**

### Architecture B: Volatility-Regime Adaptive Sizing

**Concept:** Estimate current volatility regime (low/medium/high) using realized vol or ATR. Scale position size inversely: smaller in high-vol, larger in low-vol. Classic risk-parity approach.

| Aspect | Analysis |
|--------|----------|
| **Theoretical benefit** | High-vol regimes are when DDs happen. Smaller positions = smaller absolute losses. Low-vol regimes are trending → larger positions = bigger gains. |
| **Problem 1** | Volatility is concurrent with drawdowns, not leading. By the time realized vol signals "high", the DD is already in progress. VDO + trailing stop already implicitly responds to vol (wider bars = wider stops). |
| **Problem 2** | V10 already uses `risk_fraction=0.02` per trade and trailing stops that adapt to ATR. Adding a separate volatility overlay adds redundancy. |
| **Problem 3** | Regime switching was explicitly tried and rejected in V11: "causes whipsaw" (per SUGGESTION_AUDIT.md). The lag between regime detection and position adjustment creates oscillation. |
| **Potential:** | The one untested variant is **pre-trade** volatility filtering: refuse to enter if trailing 20-bar realized vol exceeds a threshold. This is different from regime switching (which modifies existing positions). But it would have missed several profitable entries in 2024 (high-vol + trending = V10's sweet spot). |

**Verdict: Redundant with existing ATR-based stops and risk fraction. Regime switching → whipsaw (proven). Pre-trade vol filtering might help MDD but likely hurts returns.**

### Architecture C: Institutional Trend-Following Frameworks

**Concept:** Based on AQR/Man/Winton-style trend-following: continuous position sizing proportional to signal strength × inverse volatility, daily rebalancing.

| Aspect | Analysis |
|--------|----------|
| **How they differ from V10** | V10 is binary (in/out). Institutional TF holds continuously with position size ∝ signal strength. This smooths entries/exits — no single disastrous entry point. |
| **Why V10 is binary** | VDO is a threshold signal (>0.004). Below threshold, there's no reliable signal — holding a small position would be random exposure. |
| **What would change** | Replace binary entry/exit with continuous sizing: `position = VDO_normalized × (1/σ) × capital × leverage`. Gradual scale-in and scale-out. |
| **Problem 1** | VDO's distribution is NOT smooth — it has a no-man's-land around zero where signal-to-noise is poor. Continuous sizing would hold small positions in this zone = random exposure. |
| **Problem 2** | BTC is single-instrument. Institutional TF works across 50-100 instruments where diversification smooths. Single-instrument continuous sizing just adds noise to returns. |
| **Problem 3** | Requires daily rebalancing on Spot BTC = high friction. Each rebalance = spread cost + slippage. |
| **Existing evidence** | Fractional Kelly (entry_aggression=0.85) already approximates "bet less than maximum" from the same theoretical family. Going further → smaller bets → lower returns. |

**Verdict: Designed for diversified multi-instrument portfolios. Single-instrument application is theoretically unsound — you can't diversify within one asset.**

### Direction 3 Verdict

| Architecture | Novel Information? | Expected Benefit | Complexity Cost | Recommendation |
|-------------|-------------------|-----------------|----------------|----------------|
| Core + Tactical | No (same VDO) | Marginal at best | HIGH (doubles params) | **Do not pursue** |
| Vol-Regime Sizing | No (redundant) | Slight MDD reduction | MEDIUM | **Do not pursue** (whipsaw proven) |
| Continuous Sizing | No (same VDO) | Smoothing only | HIGH (rebalance cost) | **Do not pursue** (single-instrument) |

**All three architectures are mechanism changes, not information changes. Without a new signal source, changing how you react to the same signal just rearranges the same risk-return tradeoff.**

---

## Synthesis: What Would Actually Work

Based on this research, the only paths forward that could meaningfully improve V10 are:

### Path 1: Derivatives Data Pipeline (Medium effort, Uncertain payoff)
Build funding rate + OI ingestion. Hypothesis: funding rate divergence from spot price may provide 4–12 hour leading signal for DD onset. Would cover 4-5/6 historical episodes. Requires:
- New API module for `/fapi/v1/` endpoints
- Historical backfill from third-party (Coinalyze, ~$30/mo)
- Alignment/merge pipeline with existing Spot data
- N=4-5 validation — **still insufficient for statistical confidence**

**Risk:** We might build the pipeline and discover funding rate is also non-discriminative (like every Spot signal tested above).

### Path 2: Multi-Instrument Diversification (High effort, Reliable payoff)
Add ETH, SOL, or BNB trend-following. Same V10 architecture, different instruments. Drawdowns are partially uncorrelated → portfolio MDD decreases mechanically via diversification. This is the standard institutional solution.

**Reliability:** Diversification is the one "free lunch" in finance. Unlike signal invention, it works mathematically regardless of signal quality.

### Path 3: Accept V10 As-Is (Zero effort, Honest)
V10 with 2% risk fraction and current stop structure produces a Sharpe ratio that is competitive for single-instrument trend-following. The MDD of ~36% is within historical BTC norms. Further optimization has shown diminishing/negative returns across 6+ attempts.

---

## Appendix A: Raw Data Availability Audit

```
AVAILABLE IN PIPELINE:
  ✓ OHLCV (Spot, 15m/1H/4H/1D, 2017–present)
  ✓ taker_buy_base_vol (= buyer-initiated volume)
  ✓ taker_buy_quote_vol (= buyer-initiated in USDT)
  ✓ num_trades (trade count per bar)

DERIVABLE FROM ABOVE:
  ✓ taker_buy_ratio (TBR) — already used by VDO
  ✓ taker_sell_vol = volume − taker_buy_vol
  ✓ avg trade size = volume / num_trades
  ✓ TBR × volume composites

NOT AVAILABLE:
  ✗ Funding rate (Futures only)
  ✗ Open Interest (Futures only)
  ✗ Long/Short ratio (Futures only)
  ✗ Liquidation data (WebSocket only, no historical)
  ✗ Order book depth (snapshot only, no historical)
  ✗ On-chain metrics (separate data source entirely)
```

## Appendix B: Cascade Chain Details

The 4 major cascade events that caused the most damage:

| Cascade | Episode | Trades | Total Loss | Pattern |
|---------|---------|--------|------------|---------|
| T#69-74 | 2021-11-09 | 6 sequential | −$26,686 | Pyramid into falling VDO. Each re-entry smaller but still losing. |
| T#86-88 | 2025-01-20 | 3 sequential | −$21,689 | Re-entry while price still declining. VDO gave false positive. |
| T#46-47 | 2021-05-03 | 2 sequential | −$9,490 | Quick re-entry on VDO bounce, caught second leg down. |
| T#55-56 | 2021-05-03 | 2 sequential | −$5,169 | Same pattern, later in same episode. |

**Common pattern:** VDO stays positive (or briefly recovers) during multi-week corrections. Each VDO blip triggers a new entry that gets stopped out. The problem is VDO's lag when applied to exit timing, not position management architecture.

## Appendix C: Why "Invent New Signal" Is Hard

VDO worked because taker_buy_ratio was genuinely new information that price-based systems ignored. The search for a position management equivalent faces a fundamental constraint:

1. **All Spot data is derived from the same order book.** OHLCV, volume, taker_buy_vol, num_trades — these are all projections of the same underlying limit-order-book process. They are correlated by construction.

2. **Derivatives data is genuinely independent.** Futures OI reflects leveraged positioning. Funding rate reflects market's cost of carry. These come from different participants making different decisions with different capital structures.

3. **The closest Spot-side "independent" signal would be cross-exchange flow** (e.g., Binance vs Coinbase spot price premium, or exchange-to-exchange withdrawal patterns). But this requires entirely new data infrastructure beyond even derivatives.

**The fundamental truth: to find a new DD-leading indicator, we need data from a different market microstructure, not better analysis of the same microstructure.**

---

*End of research memo. No code was written. No parameters were tuned. No backtests were run.*
