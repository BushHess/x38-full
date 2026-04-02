# Findings Under Review — Data Scope

**Topic ID**: X38-T-19G
**Opened**: 2026-04-02
**Author**: human researcher

2 findings about what data the framework considers in-scope — resolution gaps,
acquisition boundaries, and cross-asset context signals. Split from Topic 019F
(2026-04-02 regrouping). Original findings from Topic 019 (DFL-15, DFL-16).

Theme: "What data do we need? What's in scope?"

DFL-16 depends on DFL-15's scope decision (cross-asset data requires external
data — DFL-15 determines whether that's in framework scope). Natural pair.

These are Tier 4 decisions, INDEPENDENT of the discovery loop architecture
(Tier 1-3). Can be debated in PARALLEL with all other 019 sub-topics.

**Issue ID prefix**: `X38-DFL-` (Discovery Feedback Loop).

**Convergence notes applicable** (full text at `../000-framework-proposal/findings-under-review.md`):
- C-01: MK-17 != primary evidence; firewall = main pillar
- C-02: Shadow-only principle settled
- C-12: Answer priors banned ALWAYS

**Closed topic invariants** (non-negotiable):
- Topic 018 SSE-D-02: Bounded ideation = results-blind, compile-only, OHLCV-only, provenance-tracked
- Topic 018 SSE-D-11: APE v1 = template parameterization only, no code generation
- Topic 018 SSE-D-05: Recognition stack = pre-freeze topology + named working minimum inventory (Judgment call)
- Topic 002 F-04: Contamination firewall typed schema + whitelist
- Topic 004 MK-17: Same-dataset empirical priors = shadow-only
- Topic 007 F-01: "Inherit methodology, not answers"

---

## DFL-15: Resolution Gap Assessment & Data Acquisition Scope Decision

- **issue_id**: X38-DFL-15
- **classification**: Judgment call
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-15 is primarily a SCOPE DECISION — what data the
> framework considers in-scope and out-of-scope, and the explicit rationale.
> The architecture question: should the framework define a data acquisition
> policy, or treat available data as exogenous input?

**Motivation**:

DFL-06 Analyses 1-10 exhaustively explore the existing 13-field CSV at 4
resolutions (15m, H1, H4, D1). But the CSV is a SUBSET of available market data.
The framework currently has no explicit decision about what data is in scope.

**Data resolution hierarchy — what exists vs what's available**:

```
Tick-by-tick (Binance WebSocket)
  |  Content: every individual trade (price, qty, taker side, timestamp_ms)
  |  Volume: ~500K-2M trades/day for BTCUSDT
  |  Status: NEVER acquired. Not in data pipeline.
  |
  +-->  1-second bars (aggregated from ticks)
  |     Status: NEVER acquired
  |
  +-->  1-minute bars (Binance kline API)
  |     Status: NEVER acquired
  |
  +-->  15-minute bars <-- CURRENT FLOOR (299,755 rows)
  |     13 fields including volume, taker_buy, num_trades
  |
  +-->  H1 bars (74,953 rows) <-- Available, UNUSED in strategies
  |
  +-->  H4 bars <-- PRIMARY strategy resolution
  |
  +-->  D1 bars <-- Used only for regime filter
```

**What's invisible at 15m resolution**:

| Pattern | Visible at tick/1s? | Visible at 15m? | Impact |
|---------|--------------------|--------------------|--------|
| Bid-ask spread | Yes (from tick data) | No (OHLC only) | True transaction cost invisible |
| Order flow imbalance within bar | Yes (trade-by-trade) | Partial (taker_buy_ratio is aggregate) | Intrabar flow dynamics lost |
| Trade arrival rate clustering | Yes (inter-trade times) | No (aggregated to num_trades) | Hawkes process, market maker detection invisible |
| Flash crashes / wicks | Partial (1s bars capture) | Partial (high/low capture extremes but not duration) | Sub-bar liquidity events |
| VWAP deviation from close | Yes (trade-weighted) | Partial (quote_volume/volume ~ VWAP) | Price impact asymmetry within bar |

**What's available but not in the CSV at all**:

| Data type | Source | Relevance | Acquisition difficulty |
|-----------|--------|-----------|----------------------|
| Funding rates | Binance Perps API | Crowded trade proxy. F4 hypothesis (DFL-07). Currently only taker_ratio as proxy | Easy — API available, historical data downloadable |
| Open interest | Binance Perps API | Position buildup / unwind. Leverage indicator | Easy — same API |
| Order book snapshots | Binance API (not historical) | Depth, resilience, real spread | Hard — no historical, must collect going forward |
| On-chain metrics | Glassnode / CryptoQuant API | Whale flows, exchange reserves, miner behavior | Medium — paid API, different format |
| Liquidation data | Binance/Bybit API | Forced selling/buying events | Medium — historical availability varies |
| Macro indicators | FRED / Yahoo Finance | DXY, rates, VIX — macro regime context | Easy — free, well-documented APIs |

### The scope decision

This finding does NOT propose acquiring all this data. It proposes that the
framework make an EXPLICIT scope decision — a documented boundary — rather than
operating on an implicit assumption that the 13-field CSV is sufficient.

**Options for debate**:

| Option | Scope | Rationale | Risk |
|--------|-------|-----------|------|
| **A: Current data only** | 13 fields, 4 resolutions (15m/H1/H4/D1) | Simplicity. DFL-06 shows unexploited fields exist. Exhaust current data before adding more | May miss patterns that require finer resolution or different data types |
| **B: Current + funding rates + OI** | 15 fields, same resolutions | Low acquisition cost. Funding + OI are the two most commonly cited crypto-specific signals | Adds complexity. Two new fields may not justify pipeline changes |
| **C: Current + tick data for validation** | 13 fields + tick data for DFL-13 cross-validation and Roll's spread estimation | Tick data validates 15m aggregation accuracy and enables true microstructure tests | Large data volume (100s of GB). Processing infrastructure needed |
| **D: Explicit boundary document** | Whatever data is available when pipeline runs | Framework is data-agnostic — it profiles and analyzes whatever it receives (DFL-10 + DFL-06). No scope restriction in spec | Cleanest architecturally. But no guidance on what to acquire |

**Recommendation toward hybrid**: The framework ARCHITECTURE should be
data-agnostic at the spec level (accept any fields, profile all, analyze all
per DFL-06/10 — Option D). But each CAMPAIGN should declare its data boundary
at protocol lock (Stage 1), including a minimum required field set for that
campaign and explicit justification for any excluded available fields. This is
a two-level design: agnostic architecture, bounded campaign.

### Roll's realized spread estimator

Roll (1984) showed that serial covariance of price changes estimates effective
bid-ask spread: `spread = 2 * sqrt(-Cov(dp_t, dp_{t-1}))` when Cov < 0.

**Resolution dependency**: Roll's model relies on bid-ask bounce — the
negative serial correlation caused by trades alternating between bid and ask
prices. This operates at tick-to-tick frequency (milliseconds). At H4
resolution (~500K-2M trades per bar), the bid-ask component is completely
overwhelmed by genuine price dynamics. The literature (Hasbrouck 2009) shows
Roll's estimator degrades sharply even at 5-minute resolution.

**Implication for DFL-06 Analysis 10**: Roll's spread estimator CANNOT be
meaningfully applied to existing H4 OHLC data. It requires tick or sub-minute
data (consistent with Option C below). If tick data is acquired per Option C,
Roll's estimator becomes viable. Without tick data, Amihud illiquidity
(|return|/volume) remains the only feasible liquidity proxy from existing data.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-06 | Analyses assume 13-field data. DFL-15 asks: is 13 fields enough? |
| DFL-09 | Scope clarification for SSE-D-02. DFL-15 is a different scope question: what data enters the pipeline, not what data enters grammar |
| DFL-10 | Stage 2.5 profiles ALL available fields. DFL-15 determines what's available |
| DFL-13 | Cross-exchange validation needs external data. DFL-15 scopes whether that's in framework |
| SSE-D-02 (018) | OHLCV-only for grammar. DFL-15 is about pipeline input, not grammar input — orthogonal |
| DFL-16 | Cross-asset context signals require external data (altcoin OHLCV, BTC dominance). DFL-15's scope decision determines whether this data enters the pipeline |

**Open questions**:
- Should the framework spec REQUIRE a minimum field set (mandating OHLCV+volume+
  taker at minimum), or be fully agnostic (profile whatever is provided)?
- If Option C (tick data), what is the storage and compute cost? Is it practical
  for the first campaign, or deferred to future campaigns?
- Should the scope decision be per-campaign (each campaign declares its data
  boundary) or framework-level (one boundary for all campaigns)?
- For non-crypto assets (equities, FX), the available data is very different
  (no taker_buy_vol, different microstructure). Does the scope decision need to
  be asset-class-aware?

---

## DFL-16: Cross-Asset Context Signals for Single-Asset Strategy

- **issue_id**: X38-DFL-16
- **classification**: Judgment call
- **opened_at**: 2026-03-31
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: X20 (Cross-Asset Portfolio) tested TRADING multiple
> assets -> CLOSE (BTC alpha dominates). DFL-16 addresses a fundamentally
> different question: does data FROM other assets contain information that
> IMPROVES a BTC-only strategy? This is about SIGNAL, not DIVERSIFICATION.

**Motivation**:

Every DFL-06 analysis examines BTC/USDT in isolation. Yet real crypto markets
are interconnected:

- When altcoins crash first, BTC often follows (or leads)
- When BTC dominance rises, it signals risk-off within crypto
- ETH/BTC ratio tracks crypto-specific risk appetite
- Total crypto market volume indicates sector-wide participation

The EMA(21d) regime filter works because D1 trend CONTEXT improves H4 entries.
The same logic suggests CROSS-ASSET CONTEXT might improve BTC entries — using
other assets' behavior as an information source, not as trading targets.

**Evidence from btc-spot-dev**:

X20 results actually contain relevant evidence for this question, though X20
asked a DIFFERENT question (portfolio construction):

| X20 finding | Implication for DFL-16 |
|-------------|----------------------|
| Mean rho = 0.343 across 14 coins | Moderate correlation -> some shared signal, not redundant |
| All 14 coins pass VDO screen | VDO (taker flow imbalance) is a MARKET-WIDE phenomenon, not BTC-specific |
| Altcoin median Sharpe 0.42 (< BTC 0.735) | Altcoins are noisier but may still carry leading information |
| BTC-only >> any portfolio | BTC is best to TRADE. But is it best to OBSERVE in isolation? |

**Proposal**: Investigate whether cross-asset data improves BTC strategy
performance as CONTEXT SIGNAL, not as trading targets.

### Specific signals to test

| Signal | Derivation | Hypothesis | Data needed |
|--------|-----------|-----------|-------------|
| **BTC dominance** | BTC_mcap / Total_crypto_mcap | Rising dominance = crypto risk-off -> BTC relative strength -> trend more reliable | Total crypto market cap (CoinGecko/CMC API, daily) |
| **Altcoin correlation spike** | Rolling 30d correlation of top-10 altcoins | High correlation = herding / systemic event -> regime change signal | OHLCV for top-10 altcoins (Binance API, H4/D1) |
| **ETH/BTC ratio** | ETH price / BTC price | Ratio declining = capital rotation to BTC (quality flight) -> bullish BTC signal | ETH/USDT price (single pair, easy) |
| **Cross-asset VDO consensus** | Mean VDO across top-5 coins | If taker imbalance is positive across many coins simultaneously -> stronger directional conviction | Taker volume data for 5 coins (Binance API) |
| **Altcoin-leads-BTC** | Granger-causality test: altcoin returns -> BTC returns | Do smaller coins react first to information, with BTC lagging? (less liquid -> faster price discovery in some models) | Return series for 5-10 altcoins |

### Contamination and scope considerations

- Cross-asset signals are EXTERNAL CONTEXT, similar to D1 EMA regime filter
  being temporal context for H4 entries
- They do NOT modify the core strategy (VTREND E5) — they provide an
  additional filtering or sizing dimension
- Grammar integration: cross-asset signals are NOT OHLCV (SSE-D-02 restricted).
  They enter ONLY via human templates (DFL-03 channel 1, DFL-09 scope)
- WFO validation: any cross-asset filter must pass the same 7-gate pipeline
  as any other strategy modification
- Statistical budget (DFL-11): each cross-asset feature formally tested
  consumes 1 budget unit

### Relationship to X20

| Aspect | X20 (done) | DFL-16 (proposed) |
|--------|-----------|-------------------|
| Question | Trade multiple assets? | Use other assets' data for BTC signal? |
| Conclusion | BTC-only wins (Sh 0.735 >> portfolio 0.259) | Unknown — never tested |
| Data overlap | 14 coins OHLCV+VDO | Same coins, but as INPUTS not TARGETS |
| Mechanism | Portfolio diversification (return blending) | Context signal (information enrichment) |
| Budget cost | N/A (closed study) | 1 unit per formally validated signal |

### Dependency on DFL-15

DFL-16's cross-asset signals require external data not in the current CSV
(altcoin OHLCV, BTC dominance from CoinGecko/CMC). DFL-15's scope decision
(D-18) determines whether this data enters the framework pipeline at all.

If D-18 resolves as "current data only" (Option A), DFL-16 is OUT OF SCOPE
by definition — no external data acquisition means no cross-asset signals.
If D-18 permits external data (Options B/C/D), DFL-16 becomes viable.

This dependency is why DFL-15 and DFL-16 are grouped together.

### Interaction with existing findings

| Finding | Interaction |
|---------|------------|
| DFL-11 | Budget: each cross-asset signal formally tested consumes 1 budget unit |
| DFL-15 | Data acquisition scope: cross-asset data (altcoin OHLCV, BTC dominance) requires external data not in current CSV — DFL-15 scopes whether this is in framework |
| DFL-03 | Human templates channel 1: cross-asset signals enter via human template (NOT grammar, per SSE-D-02) |
| DFL-09 | Scope: cross-asset signals are non-OHLCV. Consistent with DFL-09 (analysis can use any data; grammar restricted to OHLCV) |
| DFL-08 | Graduation path: cross-asset features follow same 5-stage path as any other feature |
| X20 | Prior evidence: X20 WFO 1/4 for multi-coin portfolios is circumstantial evidence that cross-asset signals may be temporally unstable. DFL-16 asks a different question (context vs portfolio), but the WFO instability is a relevant prior |

### Practical consideration

This is the LOWEST PRIORITY of the 019 data findings. The expected value is
uncertain — cross-asset signals may add nothing. X20's WFO failure (1/4) is
circumstantial evidence that cross-asset relationships are temporally unstable,
though X20 tested portfolio construction (return blending), not context signals
(information enrichment). The COST of testing is low (data acquisition easy,
follows DFL-06/07 methodology). The main risk is budget consumption (DFL-11).

**Recommendation**: Defer to AFTER DFL-06 analyses exhaust intra-BTC patterns.
If budget remains, test cross-asset signals. If budget is exhausted, skip.
(This recommendation pre-disposes toward deferral — the debate may decide
otherwise.)

**Open questions**:
- Should cross-asset signals be tested within the framework's standard pipeline,
  or as a separate research study (like X20)?
- Data staleness: if using CoinGecko/CMC for BTC dominance, how often is data
  updated? Does daily resolution suffice for H4 strategy?
- If an altcoin delists or structurally changes, does the cross-asset signal
  break? How robust is a signal that depends on other assets' continuity?
- Legal/compliance: for non-crypto applications (equities, FX), cross-asset
  data may have different licensing requirements. Should the framework address
  this, or is it per-campaign configuration?

---

## Cross-topic tensions relevant to 019G

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 3) | OHLCV-only grammar vs cross-asset context signals (DFL-16) | DFL-16 signals enter via human templates only (DFL-03 channel 1), not grammar. Consistent with DFL-09 |
| 019E | DFL-13 | Cross-exchange validation (DFL-13 Category B) requires external data — DFL-15 scopes whether this is in framework | DFL-13 one-time validation vs framework-level acquisition are different questions. 019G scopes the general policy; 019E scopes the specific validation need |
| 019F | DFL-14 | DFL-14 Layer 2 detection quality depends on available data resolution | Higher-resolution data (019G scope decision) improves DGP detection power, but DFL-14 can operate on current resolution |

---

## Decision summary — what debate must resolve

Debate for Topic 019G must produce decisions on these 2 questions. Both are
Tier 4 — independent of discovery loop architecture (Tier 1-3). D-19 depends
on D-18 (if data scope excludes external data, cross-asset is out of scope).

**Tier 4 — Data scope (independent)**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-18 | Data acquisition scope: framework-level or per-campaign? | DFL-15 | Framework-level minimum set / Per-campaign declaration / Data-agnostic (accept whatever) |
| D-19 | Cross-asset context: in-scope for first campaign or deferred? | DFL-16 | After DFL-06 exhausts intra-BTC / In parallel / Out of scope for v1 |

**Note**: D-19 depends on D-18. If D-18 resolves as "current data only", D-19
is automatically OUT OF SCOPE.

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-15 | Resolution gap assessment & data acquisition scope decision | Judgment call | Open |
| X38-DFL-16 | Cross-asset context signals for single-asset strategy | Judgment call | Open |
