# E1.1 -- Execution-Engineering Research Spec (Frozen)

Date: 2026-03-07
Status: SPEC FREEZE (no implementation yet)
Subject: X0 default (vtrend_x0_e5exit) shadow execution study

## SUMMARY

This spec freezes the design for a shadow execution study comparing X0's baseline
fills (next-bar-open with fixed cost model) against counterfactual TWAP and VWAP
fills derived from M15 intrabar data. The goal is to measure whether execution
timing offers a measurable, broad-based improvement over the naive next-bar-open
assumption before committing to implementation work.

No strategy logic, sizing, or signal changes are made. This is a measurement spec.

## FILES_INSPECTED

| File | Purpose | Key Finding |
|------|---------|-------------|
| `data/bars_btcusdt_2017_now_15m.csv` | M15 intrabar data | 298,605 bars, zero gaps, 2017-08-17 to 2026-02-21 |
| `data/bars_btcusdt_2016_now_h1_4h_1d.csv` | H4 decision bars | 18,662 H4 bars, zero gaps, same range |
| `v10/core/types.py` | CostConfig and SCENARIOS | spread/slip/fee decomposition confirmed |
| `v10/core/execution.py` | ExecutionModel and Portfolio | Fill price = mid + spread/2 + slip; fee separate |
| `v10/core/engine.py` | BacktestEngine | Signal at bar CLOSE, fill at next-bar OPEN |
| `research/next_wave/diagnostics/artifacts/trades_X0_base.csv` | X0 trade ledger | 186 trades, all fills at H4 open_time |

## FILES_CHANGED

| File | Change |
|------|--------|
| `research/next_wave/execution/E1_1_EXECUTION_SPEC.md` | NEW -- this spec |

## BASELINE_MAPPING

No change. X0 = E0+EMA21(D1) (standard ATR(14), NOT robust ATR).
X0-LR = vol-sized overlay (secondary reference only).
Note: E5+EMA21(D1) is the PRIMARY strategy (uses robust ATR Q90-capped);
X0 is the HOLD/fallback strategy. They are NOT the same.

## COMMANDS_RUN

1. M15 data audit: row count (298,605), gap check (0 non-standard intervals),
   NaN check (0), zero-volume count (623 = 0.21%, all pre-2024, none in X0 TWAP windows)
2. H4 data audit: row count (18,662), gap check (0 non-standard open_time intervals),
   close_time anomalies (20 bars = 0.11%, cosmetic only)
3. M15-to-H4 alignment: all 18,661 H4 transitions have 4/4 M15 bars present (100%)
4. X0 trade fill verification: all 186 entries and 186 exits at H4 open_time,
   entry_fill/entry_mid = +5.50 bps (spread/2 + slip), exit_fill/exit_mid = -5.50 bps
5. Zero-volume overlap check: 0/186 entries, 0/186 exits have zero-volume M15 bars
   in their 4-bar TWAP/VWAP window
6. CostConfig decomposition: base per_side = 15.5 bps (2.5 spread/2 + 3.0 slip + 10.0 fee)

## RESULTS

### INTRABAR_ALIGNMENT_AUDIT

**PASS -- M15 data fully supports shadow execution study.**

| Property | Value | Status |
|----------|-------|--------|
| M15 bars | 298,605 | -- |
| M15 gaps | 0 | PASS |
| M15 NaN in OHLCV | 0 | PASS |
| M15 zero-volume bars | 623 (0.21%) | PASS (none in X0 trade windows) |
| H4 bars | 18,662 | -- |
| H4 open_time gaps | 0 | PASS |
| M15-to-H4 alignment (4-bar window) | 18,661/18,661 (100%) | PASS |
| M15 and H4 common start | 2017-08-17 04:00 UTC | PASS |
| X0 entry TWAP windows with zero-vol | 0/186 | PASS |
| X0 exit TWAP windows with zero-vol | 0/186 | PASS |

**H4 close_time anomalies (20 bars, 0.11%):** These bars have non-standard
`close_time - open_time` values. They are cosmetic artifacts from Binance's
kline format (likely from exchange maintenance windows). The `open_time` grid
is perfect and the M15 bars exist for all windows. No impact on the study.

**M15 volume quality:**
- Non-zero bars: median 328 BTC ($9.1M USDT), p95 2,329 BTC ($65.8M)
- Volume is sufficient for VWAP computation at X0's position sizes
- Taker buy ratio: mean 0.495, std 0.099 (balanced, no systematic bias)

**Time coverage alignment:**

| Data | First | Last |
|------|-------|------|
| M15 | 2017-08-17 04:00 | 2026-02-21 15:00 |
| H4 | 2017-08-17 04:00 | 2026-02-21 08:00 |
| X0 trades | 2019-01-05 00:00 | 2026-01-20 20:00 |

M15 data fully covers the X0 trade window. Every X0 entry and exit timestamp
has a valid 4-bar M15 window immediately following it.

### SHADOW_EXECUTION_CANDIDATE_SET

Two candidates, both using the first hour (4 M15 bars) after signal execution:

| ID | Name | Fill Construction | Rationale |
|----|------|-------------------|-----------|
| **A** | TWAP-1h | Simple average of 4 M15 bar closes | Time-weighted, most common execution benchmark |
| **B** | VWAP-1h | Volume-weighted average of 4 M15 bar typical prices | Incorporates liquidity timing |

**Why 1 hour (4 M15 bars)?**
- X0 signals at H4 bar CLOSE. The next-bar-open fill assumption is that the order
  executes instantaneously at the next H4 bar's opening price.
- A realistic execution window for a ~$10K-$100K BTC order is 15-60 minutes.
- 1 hour is a conservative upper bound. Shorter windows (15m, 30m) can be tested
  as sensitivity analysis in E1.2 but are NOT part of the frozen candidate set.
- Using exactly 4 M15 bars gives a clean, unambiguous window.

**Why NOT more candidates?**
- The spec intentionally limits to 2 candidates to avoid overfitting the execution
  dimension. TWAP and VWAP are the two standard institutional benchmarks.
- More exotic approaches (arrival price, implementation shortfall with alpha decay,
  participation-rate algos) require order book data we don't have.

### FILL_CONSTRUCTION_RULES

#### Candidate A: TWAP-1h

**Entry fill (BUY):**
```
Given: H4 decision bar closes at time T (signal fires)
       Next H4 bar opens at time T+1 = T + 14,400,000 ms

TWAP window: 4 M15 bars with open_time in {T+1, T+1+900000, T+1+1800000, T+1+2700000}

twap_entry_price = mean(m15_bar[i].close for i in 0..3)

Fill timestamp: T+1 + 3600000 (= T+1 + 1 hour, end of TWAP window)
```

**Exit fill (SELL):**
```
Given: H4 decision bar closes at time T (exit signal fires)
       Next H4 bar opens at time T+1

TWAP window: same 4 M15 bars

twap_exit_price = mean(m15_bar[i].close for i in 0..3)

Fill timestamp: T+1 + 3600000
```

**Missing M15 bar handling:**
- If any of the 4 M15 bars is missing: use the available bars' mean.
- If all 4 are missing: fall back to baseline (next-bar open). Flag the trade.
- Audit confirmed: 0/186 entries and 0/186 exits have missing bars. This rule
  exists only as a safety specification.

**Zero-volume M15 bar handling:**
- Zero-volume bars are included in TWAP (their close price is still valid).
- Audit confirmed: 0 zero-volume bars appear in any X0 TWAP window.

#### Candidate B: VWAP-1h

**Entry fill (BUY):**
```
VWAP window: same 4 M15 bars as TWAP

typical_price[i] = (m15_bar[i].high + m15_bar[i].low + m15_bar[i].close) / 3
volume[i] = m15_bar[i].volume

vwap_entry_price = sum(typical_price[i] * volume[i]) / sum(volume[i])

Fill timestamp: T+1 + 3600000
```

**Exit fill (SELL):**
```
vwap_exit_price = sum(typical_price[i] * volume[i]) / sum(volume[i])

Fill timestamp: T+1 + 3600000
```

**Missing/zero-volume handling:**
- If a bar has zero volume: exclude from VWAP sum (volume weight = 0).
- If all 4 bars have zero volume: fall back to TWAP, then baseline.
- Audit confirmed: this case does not arise for any X0 trade.

#### Baseline (reference)

**Entry fill:**
```
baseline_entry_mid = H4_bar[T+1].open
baseline_entry_fill = baseline_entry_mid * (1 + spread_bps/20000) * (1 + slippage_bps/10000)

(For base scenario: fill = mid * 1.00055 = mid + 5.50 bps)
```

**Exit fill:**
```
baseline_exit_mid = H4_bar[T+1].open
baseline_exit_fill = baseline_exit_mid * (1 - spread_bps/20000) * (1 - slippage_bps/10000)

(For base scenario: fill = mid * 0.99945 = mid - 5.50 bps)
```

### COST_ACCOUNTING_RULES

**THE CRITICAL ACCOUNTING CONSTRAINT:**

The BacktestEngine's fill_price already includes spread/2 + slippage (5.50 bps for
base). Fee is applied separately on notional. The shadow execution study must NOT
double-count any cost component.

#### Primary comparison path: PRICE-ONLY DELTA (execution-neutral)

```
For each trade t:

  entry_delta_bps[t] = (shadow_entry_price[t] / baseline_entry_mid[t] - 1) * 10000
  exit_delta_bps[t]  = (shadow_exit_price[t] / baseline_exit_mid[t] - 1) * 10000

  For a BUY entry: negative delta = better (filled lower)
  For a SELL exit: positive delta = better (sold higher)

  combined_delta_bps[t] = -entry_delta_bps[t] + exit_delta_bps[t]
  (positive combined_delta = trade improved)
```

This is the PRIMARY metric. It measures raw price improvement from execution timing
relative to the next-bar-open mid price. No spread, no slippage, no fee. Pure
execution-timing alpha.

**Why this works:** Both the shadow fill and the baseline fill happen at the same
exchange with the same fee schedule. The only variable is the execution PRICE.
By comparing shadow price to baseline mid price, we isolate the timing effect.

**What this does NOT include:**
- Spread (the shadow fill might face a different spread than assumed)
- Slippage (the shadow fill might face different market impact)
- Fee (same for both)

These are addressed in the secondary path.

#### Secondary comparison path: FULL SCENARIO RE-PRICING

```
For each trade t:

  shadow_pnl[t] = recompute X0 trade PnL using:
    - entry_fill = shadow_entry_price * (1 + slippage_bps/10000)  [for conservatism]
    - exit_fill  = shadow_exit_price * (1 - slippage_bps/10000)
    - fee = same as baseline (taker_fee_pct)

  scenario_delta[t] = shadow_pnl[t] - baseline_pnl[t]
```

This is the SECONDARY metric. It re-prices the full trade using the shadow fill
price PLUS the canonical slippage and fee assumptions. This answers: "If we had
used TWAP/VWAP timing but still faced the same market impact and fees, how would
PnL change?"

**IMPORTANT:** The secondary path uses slippage_bps applied to the shadow price,
NOT the baseline mid price. This ensures consistent cost accounting:
- Baseline: fill = mid * (1 + spread/2) * (1 + slip) = mid + ~5.5 bps
- Shadow: fill = shadow_price * (1 + slip) = shadow_price + ~3.0 bps
- The spread component (2.5 bps) is implicitly captured in the shadow price
  because the M15 close IS an actual market price (not a mid quote)

**What the secondary path does NOT do:**
- Use smart/harsh scenarios (these are reference points, not study objects)
- Recompute trailing stops or signals (X0 logic is frozen)
- Apply different fee rates

#### What must NOT happen

1. **No adding spread/2 to shadow price.** M15 bar close is already a traded price
   (a last-trade price), not a mid-quote. Adding spread/2 would double-count.

2. **No comparing shadow fill directly to baseline fill_price.** The baseline
   fill_price includes spread/2 + slippage. The shadow price does not include
   these. Comparing them conflates execution timing with cost assumptions.

3. **No mixing primary and secondary paths.** Report both, but do not add them
   or average them. They measure different things.

### EXECUTION_DIAGNOSTICS_PLAN

All diagnostics operate on the 186 X0 base-scenario trades.

#### D1: Implementation Shortfall

```
For each candidate {TWAP, VWAP}:
  total_IS = sum(combined_delta_bps[t] * abs_notional[t]) / sum(abs_notional[t])
```

Report: aggregate IS in bps, aggregate IS in USD, and per-trade distribution.

#### D2: Entry Fill Delta Distribution

```
entry_delta_bps[t] = (shadow_entry / baseline_mid - 1) * 10000
```

Report: mean, median, std, p5, p25, p75, p95, histogram.
Sign convention: negative = shadow bought cheaper (better for buyer).

#### D3: Exit Fill Delta Distribution

```
exit_delta_bps[t] = (shadow_exit / baseline_mid - 1) * 10000
```

Report: mean, median, std, p5, p25, p75, p95, histogram.
Sign convention: positive = shadow sold higher (better for seller).

#### D4: Combined Trade Delta

```
combined_delta_bps[t] = -entry_delta_bps[t] + exit_delta_bps[t]
```

Report: mean, median, std, p5, p95, histogram, fraction of trades improved.

#### D5: Improved vs Worsened Trades

```
improved[t] = combined_delta_bps[t] > 0
```

Report: N improved, N worsened, N neutral (|delta| < 0.5 bps).
Report: mean delta for improved subset, mean delta for worsened subset.

#### D6: Broad-based vs Concentrated Effect

**Temporal:** Are deltas spread across years or concentrated in specific periods?
Report: mean delta by year.

**Trade size:** Do large or small trades benefit more?
Report: correlation between abs_notional and combined_delta.

**Re-entry vs non-re-entry:** Does execution timing differ by trade type?
Report: mean delta for re-entry (80) vs non-re-entry (106).

**Entry vs exit:** Is the effect symmetric?
Report: mean entry_delta vs mean exit_delta.

#### D7: Secondary Path (scenario re-pricing)

For base scenario only:
```
shadow_net_return_pct[t] = recomputed using shadow fills + base fees
baseline_net_return_pct[t] = from trades_X0_base.csv

pnl_delta[t] = shadow_pnl[t] - baseline_pnl[t]
```

Report: total PnL delta (USD), mean per-trade PnL delta, distribution.
Cross-check: is the sign consistent with D4 (combined_delta)?

#### D8: Reference Comparison

Report smart/base/harsh PnL for context. Do NOT use these as inputs to the
shadow execution study. They are reference lines only.

### GO_HOLD_CRITERIA

#### GO: Worth implementing an execution-aware variant

ALL of the following must hold:

1. **Magnitude**: Mean combined_delta_bps (primary path) > 1.0 bps for at least
   one candidate. (1 bps on a $50K trade = $5; across 186 trades = $930 minimum.)

2. **Consistency**: Fraction of improved trades > 55% (not just a few large winners
   dragging the mean).

3. **Broad-based**: Mean delta positive in at least 5 of the 7 years of X0 trading.
   No single year contributes > 50% of total improvement.

4. **Symmetric**: Both entry_delta and exit_delta contribute (not just one side).
   Specifically: |mean_entry_delta| > 0.3 bps AND |mean_exit_delta| > 0.3 bps.

5. **Secondary confirmation**: Scenario re-pricing (D7) shows positive total PnL
   delta. Direction must be consistent with primary path.

6. **Not concentrated**: Correlation between abs_notional and combined_delta must
   be < 0.30 (large trades don't disproportionately benefit).

If ALL 6 hold: **GO** -- proceed to E1.3 (implementation of execution-aware variant).

#### HOLD: Not worth implementing, stop after E1.3

If ANY of the following:

1. Mean combined_delta_bps < 1.0 bps for BOTH candidates.
2. Fraction improved < 55% for BOTH candidates.
3. Positive delta in fewer than 5 of 7 years.
4. One-sided effect (only entry or only exit matters).
5. Secondary path (D7) contradicts primary path direction.

Then: **HOLD** -- execution timing does not justify implementation complexity.
Report the measurement, archive the result, and do NOT build an execution-aware
strategy. Consider the E-series complete.

**Note:** HOLD does not mean execution is unimportant. It means that the specific
TWAP/VWAP-1h timing improvement over next-bar-open is too small to justify the
implementation and maintenance cost. The canonical cost scenarios (smart/base/harsh)
already capture the realistic range of execution quality.

### FILE_PLAN

```
research/next_wave/execution/
  E1_1_EXECUTION_SPEC.md           <- this file (FROZEN)
  E1_2_shadow_execution.py         <- E1.2 deliverable (computes shadow fills + diagnostics)
  E1_2_shadow_execution_report.md  <- E1.2 deliverable (results)
  artifacts/
    shadow_fills_twap.csv           <- 186 rows: trade_id, entry_twap, exit_twap, entry_delta, exit_delta
    shadow_fills_vwap.csv           <- 186 rows: same schema
    shadow_diagnostics.json         <- D1-D8 results
```

### TEST_PLAN

E1.2 must include:

1. **Alignment test**: For a known H4 bar, verify that the 4 M15 bars are correctly
   identified and their TWAP/VWAP matches hand computation.

2. **Identity test**: If M15 closes are all equal to H4 open, TWAP = VWAP = H4 open
   and all deltas should be zero.

3. **Sign test**: Construct a case where TWAP < H4 open (BUY improvement) and verify
   entry_delta_bps < 0 and combined_delta_bps > 0.

4. **Cost accounting test**: Verify that primary path (price-only) and secondary path
   (scenario re-pricing) produce consistent directional results on synthetic data.

5. **No-lookahead test**: Shadow fills use only M15 bars with open_time >= fill_ts_ms.
   No M15 bar from before the execution window is included.

### RISKS_AND_AMBIGUITIES

#### R1: M15 close is not a guaranteed executable price

M15 bar close is the last trade price in that 15-minute window. It is NOT the bid
or ask at the moment of execution. In reality, a market order would fill at the
current ask (buy) or bid (sell), which differs from the last trade price by
approximately half the spread.

**Mitigation:** The secondary path adds slippage_bps to the shadow price, partially
accounting for this. The primary path is an optimistic bound. The truth is between
them.

#### R2: TWAP/VWAP assumes continuous execution

A 1-hour TWAP assumes the order is sliced into equal parts executed every 15 minutes.
In practice, execution might be front-loaded, back-loaded, or opportunistic.

**Mitigation:** This is a measurement study, not an execution algorithm. TWAP/VWAP
represent what a standard execution algo would achieve. The delta is directional —
if the mean of 4 bars is better than the first bar's open, that's information.

#### R3: Market impact is not modeled

TWAP/VWAP assumes zero market impact (our orders don't move the price). For X0's
typical order sizes ($10K-$100K notional), this is reasonable for BTC/USDT (median
M15 quote volume $9.1M), but may not hold during extreme volatility.

**Mitigation:** D6 checks whether large trades benefit disproportionately (which
would suggest market impact is relevant). If correlation > 0.30, flag it.

#### R4: Signal leakage through execution window

If X0 uses a trailing stop that could trigger within the 1-hour execution window
(e.g., stop is very tight), the TWAP/VWAP price might reflect post-stop price action.
In reality, the execution would have been completed or cancelled by then.

**Mitigation:** X0's trailing stop operates on H4 bar closes, not intrabar. The
stop cannot trigger during the M15 TWAP window because the next H4 bar hasn't
closed yet. No leakage.

#### R5: Entry and exit may require different treatment

Entry fills face the ask; exit fills face the bid. The TWAP/VWAP construction is
symmetric (same formula for both). In reality, a BUY TWAP would execute at the
ask each slice, and a SELL TWAP at the bid.

**Mitigation:** The secondary path handles this by applying slippage_bps separately.
The primary path is symmetric by design and represents the price-improvement
opportunity, not the realized fill.

## BLOCKERS

None. M15 data is complete, aligned, and sufficient for the shadow execution study.

## NEXT_READY

E1.2 -- Shadow execution computation and diagnostic report
