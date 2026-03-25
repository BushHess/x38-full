# X12: Why Does E5 Win If It Doesn't Fix Churn?

## Central Question

E5's robust ATR (RATR) was **designed** to fix stop-churn: by capping outlier
true ranges at Q90, the trail stop should be smoother, triggering fewer false
exits during volatile pullbacks. If churn is reduced, short/medium trades
should improve.

**But the evidence says otherwise.** Under common envelope (e5_ema1d21-08),
E5+EMA1D21 still **loses** to E0+EMA1D21 on short/medium trailing-stop net
damage across all 4 shared cells. The churn-repair thesis fails empirically.

Yet E5 still wins on headline metrics: final equity, return, PF, max drawdown,
long-winner financing. The residual edge is +317.18 pp.

**If E5 doesn't fix churn — the thing it was designed to fix — why does it
still win?**

## Independent Prior (vtrend/research/x1)

An independent mechanism decomposition on a separate codebase (22 bps RT,
window 2020-12-31 → 2026-03-08) has already answered this question:

**Verdict: `e5_ema21d1_EDGE_IS_PATH_DEPENDENCE_DRIVEN`**

Key findings:
- Path-state share = **67.21%** of full edge (occupancy 52.51% + same-exit
  capital scaling 14.70%)
- E5 exits **earlier** on 39/45 divergent matched trades (+36,612), later on
  only 6 (-1,573). RATR trail is tighter (Q90 cap lowers ATR), not wider.
- Matched PnL: E5 wins only **47/111** comparisons, median delta **-268.09**.
  Positive mean (+457) driven by tail concentration.
- MFE delta = **-0.49%** — E5 captures LESS peak, not more.
- 27/29 unmatched entries = "other line still LONG" → pure occupancy cascade.
- Top-10 winners = 63.25% of edge. Long-duration = 110.47%.
- All 3 continuity blocks positive but none clean: always needs tail/path-state.

**Implication for H0/H1/H2:**
- H0 (Churn Repair): DEAD — E5 exits sooner, doesn't reduce stop frequency
- H1 (Winner-Tail Capture): WEAK — E5 loses median matched trade, MFE lower
- H2 (Path-Dependence Cascade): CONFIRMED — 67% of edge is path-state

**X12's role = replication + extension**, not discovery:
- Different data window (2019-01-01, adds 2019-2020 period)
- Harsher cost (50 bps vs 22 bps — churn penalised more)
- Direct churn measurement (T0 — not in independent study)
- Timescale robustness (T4 — 16 slow_periods, not in independent study)
- Bootstrap OOS confidence (T5 — 500 VCBB paths, not in independent study)

## Mechanical Difference

The ONLY change between E0 and E5: trail stop ATR calculation.
- E0: `pk - 3.0 * ATR(14)[i]`       — standard Wilder ATR, period 14
- E5: `pk - 3.0 * RATR(20)[i]`      — robust ATR (TR capped at Q90 over 100-bar window), period 20

Entry logic is **identical**: EMA(fast) > EMA(slow) AND VDO > 0 AND D1_regime.
EMA cross-down exit is **identical**. Only the trail stop distance differs.

## Hypotheses

**H0 — Churn Repair (design intent, expected to FAIL):**
RATR reduces false stop-outs on short/medium trades. If true, E5 should show
fewer trail_stop exits, lower churn rate (stop-out followed by re-entry within
N bars), and better short/medium PnL. Prior evidence says this fails — T0
will confirm or refute directly.

**H1 — Winner-Tail Capture (mechanical):**
RATR doesn't fix churn but accidentally helps on the OTHER end: during strong
trends, the capped trail is tighter than standard ATR (which spikes with
volatility), so E5 holds big winners slightly longer before the trend exit
fires. The edge comes from a few long trades capturing more of the right tail.

**H2 — Path-Dependence Cascade (fragile):**
Different exit timing creates different portfolio states. When E5 exits a few
bars before/after E0, the next entry fires at a different price → cascade of
divergent trades. The headline gap comes not from better per-trade outcomes
but from a different SEQUENCE of trades. If true, the edge is
sample-dependent and may not generalise.

## Design

Two vectorised sims (E0+EMA1D21, E5+EMA1D21) on identical data, both logging
full per-trade records. Single parameter set, harsh cost only. No sweep, no
tuning — this is mechanism forensics.

### Parameters (frozen)

| Param           | Value   | Note                        |
|-----------------|---------|-----------------------------|
| slow_period     | 120     | H4 bars (= 20 days)        |
| fast_period     | 30      | slow // 4                   |
| trail_mult      | 3.0     |                             |
| vdo_threshold   | 0.0     |                             |
| d1_ema_period   | 21      |                             |
| atr_period (E0) | 14      | standard Wilder             |
| ratr_period(E5) | 20      | cap_q=0.90, cap_lb=100      |
| cost            | 50 bps  | harsh RT                    |
| data            | 2019-01-01 to 2026-02-20    |
| warmup          | 365 days                     |
| CASH            | 10,000                       |

### Per-Trade Record (both sims)

```
{
  entry_bar:    int,       # bar index of entry
  exit_bar:     int,       # bar index of exit
  entry_px:     float,     # fill price at entry
  exit_px:      float,     # fill price at exit
  peak_px:      float,     # highest close during position
  pnl_usd:      float,     # dollar PnL (after cost)
  ret_pct:      float,     # return % (after cost)
  bars_held:    int,       # exit_bar - entry_bar
  exit_reason:  str,       # "trail_stop" | "trend_exit" | "eod"
  trail_dist:   float,     # trail_mult * ATR/RATR at exit bar (price units)
}
```

### Trade Matching

Match by `entry_bar` (integer index). Since entry logic is identical:
- Trade #1 is ALWAYS matched (both start in cash).
- Matched trades stay matched until **first exit divergence**.
- After divergence: one is flat, other still in position → next entries differ.
- **Re-sync**: both happen to be in cash at the same bar AND enter on same signal.

### Trade Categories

| Category                | Definition                                         |
|-------------------------|----------------------------------------------------|
| **matched-same-exit**   | Same entry_bar AND same exit_bar                   |
| **matched-diff-exit**   | Same entry_bar, different exit_bar                 |
| **seed-event**          | First matched-diff-exit that starts a cascade      |
| **e5-only**             | Trade only E5 takes (path divergence)              |
| **e0-only**             | Trade only E0 takes (path divergence)              |

A **cascade** = seed-event + all subsequent e5-only / e0-only trades until
the next matched entry (re-sync). Cascade depth = number of unique trades
in the chain.

## Test Suite

### T0: Churn Audit (confirm design-intent failure)

**Purpose:** Directly measure whether RATR reduces stop-churn. Expected: NO.

**Definition of churn event:** A trail_stop exit followed by re-entry within
`CHURN_WINDOW` bars (default: 20 bars = ~3.3 days on H4). A churn event is a
false stop-out — the strategy exits then immediately re-enters the same trend.

**Outputs (per strategy):**
- Total trades, trail_stop exits, trend exits
- Churn count: trail_stop exits where re-entry occurs within CHURN_WINDOW
- Churn rate: churn_count / trail_stop_exits
- Churn PnL: sum of PnL on the churn exit trade (usually negative)
- Non-churn trail_stop PnL: sum of PnL on trail_stop exits NOT followed by
  quick re-entry (these are "real" trend endings)
- Short trades (<20 bars): count, mean PnL, sum PnL per strategy
- Medium trades (20-80 bars): count, mean PnL, sum PnL per strategy

**Deltas (E5 - E0):**
- d_churn_rate, d_churn_pnl, d_short_pnl, d_medium_pnl

**Key test:** If d_churn_rate < 0 (E5 churns LESS) → H0 survives.
If d_churn_rate >= 0 → H0 fails, churn repair thesis is dead.

**Artefact:** `x12_churn_audit.csv`

### T1: Divergence Cascade Map

**Purpose:** Census of trade categories + cascade structure.

**Outputs:**
- Count per category (matched-same, matched-diff, e5-only, e0-only)
- PnL per category (sum, mean, median)
- Cascade chain lengths (mean, median, max, distribution)
- Re-sync count and mean bars between re-syncs
- Headline delta: E5_final_nav - E0_final_nav

**Artefact:** `x12_cascade_census.csv`

### T2: Matched-Trade Mechanism

**Purpose:** For matched-diff-exit trades, isolate what the trail difference
actually does (since it's NOT fixing churn).

**Outputs (per matched-diff-exit trade):**
- Who exits first? (E5-first count vs E0-first count)
- Extra holding: bars held by longer-holding strategy
- PnL delta = E5_pnl - E0_pnl, split by:
  - Winner (E0_pnl > 0) vs loser (E0_pnl <= 0) bucket
  - Duration bucket: short (<20 bars), medium (20-80), long (>80)
- Trail distance delta at exit: E5_trail_dist - E0_trail_dist at the bar
  where the FIRST strategy exits
- Aggregate: mean/median PnL delta per sub-bucket

**Artefact:** `x12_matched_mechanism.csv` (one row per matched-diff-exit trade)

**Key question:** Where in the duration/winner-loser space does E5 gain vs
lose? If E5 gains only on long winners → winner-tail capture (H1).

### T3: Cascade Counterfactual

**Purpose:** Definitively decompose headline delta into mechanical vs cascade.

**Method:**
1. PnL-based decomposition:
   ```
   matched_delta  = sum(E5_pnl[t] - E0_pnl[t])  for t in matched trades
   cascade_delta  = sum(E5-only PnL) - sum(E0-only PnL)
   headline_delta = E5_final_nav - E0_final_nav
   residual       = headline_delta - matched_delta - cascade_delta
   ```
   (residual captures compounding / capital-weighting effects)

2. Return-based decomposition (compounding-neutral):
   ```
   matched_ret_delta  = sum(E5_ret[t] - E0_ret[t])  for matched trades
   cascade_ret_delta  = sum(E5-only ret) - sum(E0-only ret)
   ```

3. Cascade fraction:
   ```
   cf_pnl = cascade_delta / headline_delta
   cf_ret = cascade_ret_delta / (matched_ret_delta + cascade_ret_delta)
   ```

**Artefact:** `x12_decomposition.json`

**Verdict metric:** `cf_ret` (return-based, compounding-neutral)

### T4: Timescale Robustness

**Purpose:** Are T0 (churn) + T3 (decomposition) findings stable across
16 slow_periods?

**Method:** Run T0+T1+T3 at each of:
`[30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]`

**Outputs (per timescale):**
- d_churn_rate (E5 - E0)
- headline_delta, matched_delta, cascade_delta, cf_ret
- matched-diff-exit count, e5-only count, e0-only count

**Stability criteria:**
- d_churn_rate direction consistent in >= 12/16 → churn finding robust
- cf_ret direction consistent in >= 12/16 → decomposition finding robust

**Artefact:** `x12_timescale_table.csv`

### T5: Bootstrap Confidence

**Purpose:** OOS confidence intervals for key findings.

**Method:** 500 VCBB paths (block=60, seed=42).
For each path: run both sims, compute churn delta + cf_ret.

**Outputs:**
- d_churn_rate: median, p5, p95
- headline_delta: median, p5, p95
- cf_ret: median, p5, p95
- P(d_churn_rate < 0): fraction where E5 actually reduces churn
- P(cf_ret > 0.5): fraction where cascade dominates
- P(headline_delta > 0): fraction where E5 beats E0

**Artefact:** `x12_bootstrap_table.csv`

### T6: Cost Sweep (reconcile vtrend 22bps vs x12 50bps)

**Purpose:** The independent study (vtrend/x1, 22 bps) found cascade dominates
(cf_ret=0.67). X12 at 50 bps finds mechanical dominates (cf_ret=0.47). T6 maps
cf_ret as a function of cost to find the crossover point.

**Method:** Run T3 decomposition at each of:
`[10, 15, 22, 30, 35, 40, 50, 60, 75]` bps RT.

**Outputs (per cost level):**
- dSharpe, headline_delta, matched_delta, cascade_delta, cf_ret
- d_churn_rate (invariant to cost — same trade sequence)
- Crossover bps: linear interpolation of cf_ret = 0.5

**Key finding:** cf_ret crossover at ~38 bps RT. Below 38 bps cascade dominates;
above 38 bps mechanical dominates. Both studies are correct at their respective
cost levels.

**Why cost shifts dominance:** Cost is a flat per-trade penalty. Higher cost
penalises E5-only/E0-only unmatched trades (smaller, more cost-sensitive) more
than matched-diff-exit trades (same trade, different exit timing). As cost rises,
cascade_delta shrinks faster than matched_delta → cf_ret falls.

**Artefact:** `x12_cost_sweep.csv`

## Verdict Gates

| Gate | Condition | Interpretation |
|------|-----------|----------------|
| **G0** | `d_churn_rate >= 0` (T0) | Churn repair thesis DEAD — RATR doesn't fix what it was designed to fix |
| **G1** | `cf_ret > 0.5` (T3) | Path dependence dominates → E5 edge fragile |
| **G2** | Matched-diff-exit median PnL delta > 0 (T2) | E5 has mechanical per-trade edge |
| **G3** | d_churn_rate + cf_ret direction stable >= 12/16 (T4) | Findings are robust |

### Decision Matrix

| G0 | G1 | G2 | G3 | Verdict |
|----|----|----|----|----|
| T  | F  | T  | T  | **CHURN_FAILS_BUT_TAIL_WINS** — RATR doesn't fix churn but captures winner tails |
| T  | T  | F  | T  | **CHURN_FAILS_CASCADE_ONLY** — RATR doesn't fix churn, edge is path-dependent |
| T  | T  | T  | T  | **CHURN_FAILS_MIXED** — both tail + cascade, neither dominates |
| F  | *  | *  | T  | **CHURN_REPAIRS** — prior evidence was wrong, RATR does reduce churn |
| *  | *  | *  | F  | **INCONCLUSIVE** — findings unstable across timescales |

### What This Does NOT Do

- No parameter sweep or tuning
- No new envelope experiments
- No promotion attempt for E5
- Does not change `KEEP_e0_ema1d21_PRIMARY` decision regardless of outcome

## Output Files

```
x12/
  SPEC.md                      # this file
  benchmark.py                 # single script, all tests T0-T6
  x12_results.json             # nested dict of all results
  x12_churn_audit.csv          # T0 output
  x12_cascade_census.csv       # T1 output
  x12_matched_mechanism.csv    # T2 output (per-trade detail)
  x12_decomposition.json       # T3 output
  x12_timescale_table.csv      # T4 output
  x12_bootstrap_table.csv      # T5 output
  x12_cost_sweep.csv           # T6 output
```

## Dependencies

```python
from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

## Estimated Runtime

- T0+T1+T2+T3: ~5s (two sims + matching + decomposition)
- T4: ~10s (16 timescales × 2 sims)
- T5: ~15s (500 bootstrap paths × 2 sims)
- T6: ~2s (9 cost levels × 2 sims)
- Total: ~28s

## Results (2026-03-09)

**Verdict: `CHURN_FAILS_BUT_TAIL_WINS`**

### Gate Outcomes

| Gate | Result | Evidence |
|------|--------|----------|
| G0 | PASS | d_churn_rate = +0.014 — E5 churns MORE, not less |
| G1 | FAIL | cf_ret = 0.468 at 50 bps — mechanical dominates, not cascade |
| G2 | PASS | Median matched-diff PnL delta = +$177, E5 wins 45/68 |
| G3 | PASS | Churn: 15/16 stable, cf_ret: 12/16 stable |

### Key Findings

1. **H0 DEAD**: RATR does not fix churn. E5 has higher churn rate (+1.4pp), more
   trail_stop exits (183 vs 168), and worse short-trade PnL.

2. **H1 CONFIRMED (at 50 bps)**: E5's mechanical edge comes from matched-diff-exit
   trades. E5 exits earlier on 61/68 divergent trades (tighter RATR trail), wins
   45/68 PnL comparisons. Long-duration bucket contributes +$18,743.

3. **H2 COST-DEPENDENT**: cf_ret crossover at ~38 bps RT. Below 38 bps, cascade
   dominates (consistent with vtrend/x1 at 22 bps finding 67% path-state). Above
   38 bps, mechanical dominates.

4. **OOS WEAK**: P(headline > 0) = 46.4%, P(cf_ret > 0.5) = 35.0%. The E5 edge
   does not survive bootstrap at 50 bps — consistent with prior finding that E5's
   advantage is sample-dependent.

### Reconciliation with vtrend/x1

Both studies compare the same algorithms (E0+EMA1D21 vs E5+EMA1D21) and reach
consistent conclusions when cost is accounted for:
- vtrend/x1 (22 bps): cf_ret > 0.5 → path dependence dominates
- x12 (50 bps): cf_ret < 0.5 → mechanical dominates
- Crossover at ~38 bps explains the apparent contradiction
