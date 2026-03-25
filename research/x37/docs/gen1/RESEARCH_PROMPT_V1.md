# Research Prompt: BTC Spot Long-Only Trading System Discovery

## 1. Objective

Design a BTC/USDT spot **long-only** trading system from first principles, then
validate whether it exceeds or matches these benchmarks at 20 bps round-trip cost:

| System | Sharpe | CAGR | MDD | Trades |
|--------|--------|------|-----|--------|
| **Baseline (E0+regime)** | 1.636 | 72.7% | 38.4% | 186 |
| **Best variant (V4)** | 1.830 | 80.4% | 33.6% | 196 |

V4 wins full-sample but **fails bootstrap** (median Sharpe 0.73 vs baseline's 0.77).
The true target is **bootstrap-robust outperformance**, not just full-sample Sharpe.

---

## 2. Data Description

**File**: BTC/USDT spot, Binance, 2017-08 to 2026-02.
**Timeframes**: H4 (4-hour) and D1 (daily) bars, pre-aligned.

**Available columns per bar**:
- `open_time`, `close_time` (epoch ms, UTC)
- `open`, `high`, `low`, `close` (price, USDT)
- `volume` (base asset, BTC)
- `taker_buy_base_vol` (buyer-initiated volume, BTC — enables order flow analysis)
- `quote_volume` (USDT turnover)
- `interval` ("4h" or "1d")

**Key data properties** (measured, not assumed):
- ~18,500 H4 bars, ~3,100 D1 bars
- Taker buy data is REAL (not OHLC proxy) — enables genuine order flow signals
- BTC H4 returns: heavy tails (kurtosis ~8), negative skew (-0.3), strong vol clustering
- Cross-timescale correlation ρ ≈ 0.92 for EMA periods 60-200 (diversification ceiling +3.5%)

---

## 3. Execution Model (non-negotiable)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Direction | **Long-only** | Short-side BTC is negative-EV at ALL timescales (proven, Sharpe -0.64) |
| Resolution | **H4 bars** | Optimal for BTC trend capture; D1 for regime only |
| Signal timing | Signal at bar **close** | No intra-bar decisions |
| Fill model | **Next bar open** | Realistic: cannot trade at the close you just observed |
| Cost | **20 bps round-trip** | Measured median 16.8 bps (X33), padded for safety |
| Cost decomposition | spread=5.0 bps, slippage=2.5 bps, fee=0.05% | Per CostConfig spec |
| Initial capital | $10,000 | Standardized |
| Warmup | 365 days (no-trade) | Indicators fully initialized before first signal |
| Position sizing | Full Kelly fraction or fixed (specify) | Must be stated explicitly |

---

## 4. Research Approach: First Principles

Start from raw data. Do NOT assume trend-following, mean-reversion, or any framework.

### Phase 1: Data Decomposition (understand before designing)

Analyze what exploitable information exists in each channel:

1. **Price structure**: autocorrelation, mean-reversion vs trending at various horizons,
   regime clustering, breakpoint detection
2. **Volume/order flow**: taker buy vs sell imbalance, volume-price divergence,
   exhaustion signals, climactic volume
3. **Volatility**: clustering persistence, realized vs implied (proxy), regime transitions,
   compression → expansion cycles
4. **Cross-timeframe**: H4 vs D1 alignment, higher-timeframe regime as filter
5. **Calendar/time**: intraday patterns, day-of-week, month-of-year seasonality
6. **Any other discoverable structure**: spectral analysis, entropy, fractal dimension,
   information-theoretic measures

For each channel, quantify:
- **Predictive power**: IC (Information Coefficient) out-of-sample, not just in-sample
- **Decay profile**: how quickly does the signal degrade with lag?
- **Regime dependence**: does the signal work in ALL regimes or only some?
- **Independence**: correlation with other channels (avoid redundant signals)

### Phase 2: Mechanism Design (theory before optimization)

Based on Phase 1 findings, design entry/exit/sizing mechanisms with **stated rationale**
for each component. For every design choice, answer:
- What market microstructure or behavioral mechanism does this exploit?
- Why should this persist out-of-sample?
- What is the null hypothesis, and can we reject it?

### Phase 3: Parameter Selection (last, not first)

Grid search is permitted ONLY after mechanism design is complete.
- Search must be on a **coarse grid** first (e.g., 5-10 values per param)
- Winner must sit on a **plateau**: ΔSharpe ≤ 0.05 for ±20% parameter perturbation
- Report the **total number of configurations tested** (needed for DSR correction)

---

## 5. Proven Constraints (from 68 prior studies)

These are hard-won results from extensive research. Violating them wastes time.

### What WORKS (keep or improve)
- **EMA crossover entry**: p=0.0003, survives Bonferroni/Holm/BH correction
- **ATR trailing stop + EMA cross-down exit**: p=0.0003, strictly dominates trail-only
- **VDO filter** (taker buy imbalance): 16/16 timescales, DOF-corrected p=0.031
- **D1 EMA regime filter**: 16/16 ALL metrics, p=1.5e-5, range 15-40d proven
- **Alpha from GENERIC trend-following**: plateau across slow=60-144 EMA periods

### What DOES NOT WORK (do not re-attempt)
| Rejected Approach | Study | Why It Failed |
|-------------------|-------|---------------|
| Short-side BTC | X11 | Negative-EV at ALL timescales (Sh -0.64, MDD 92%) |
| Partial take-profits | X10 | Destroys fat-tail alpha (top 5% trades = 129.5% of profits) |
| Exit geometry (pullback multipliers) | X23 | Increases churn, Sharpe -0.229 vs baseline |
| Trail arming delay | X24 | 53 never-armed entries degrade exits |
| Volume entry filters (beyond VDO) | X25 | All features p > 0.39; VDO is near-optimal |
| Multi-coin portfolio | X20 | Altcoins dilute BTC alpha (median Sh 0.42 vs BTC 0.74) |
| Conviction sizing (variable position) | X21 | Entry features IC = -0.039 — zero predictive power |
| ML churn filters at <30 bps | X22 | Filters HURT below 30 bps (value is cost savings only) |
| WATCH state machine (re-entry) | X16-X17 | Path-specific autocorrelation, not robust |
| Fractional/partial actuators | X19, X30 | Static full-exit strictly dominates |
| D1 regime as EXIT signal | X31-A | Selectivity 0.21 — cuts winners 5x more than losers |
| Re-entry barriers | X31-B | Oracle ceiling +0.033 Sharpe (below +0.08 threshold) |
| Complex strategy (40+ params) | V8/V11 | ZERO value over 3-param VTREND |

### Hard Constraints (proven mathematical limits)
- **Fat-tail alpha**: top 5% of trades = 129.5% of total profits → any mechanism
  that truncates winners must justify itself against this 8:1 payoff asymmetry
- **Cross-timescale ceiling**: ρ=0.92 → maximum diversification gain +3.5%
- **Oracle exit ceiling**: perfect exit knowledge adds only +0.033-0.038 Sharpe
- **10% improvement cap**: even perfect churn classification yields max +0.845 Sharpe
  improvement, and simple filters capture most of it

---

## 6. Validation Protocol (mandatory)

Every candidate system must pass ALL of the following:

### 6.1 Full-Sample Backtest (2019-01-01 to 2026-02-20)
- Report: Sharpe, CAGR, MDD, trades, win rate, profit factor, Sortino, Calmar
- Sharpe annualized from H4 returns: `(mean(r)/std(r, ddof=0)) × √2190`
- MDD: peak-to-trough on mid-mark NAV

### 6.2 Walk-Forward (12 × 6-month non-overlapping windows)
- Each window with 365-day warmup
- Must be **positive Sharpe in ≥10/12 windows**
- Report mean and median Sharpe across windows

### 6.3 VCBB Bootstrap (500 paths, 20 bps)
- Volatility-Conditioned Block Bootstrap (blksz=60, ctx=90, K=50)
- **P(Sharpe > 0) ≥ 95%** (mandatory)
- **Median Sharpe ≥ 0.6** (target)
- Report: median, mean, P5, P95, P(Sharpe>0)

### 6.4 PSR (Probabilistic Sharpe Ratio)
- Bailey & López de Prado (2012), benchmark SR* = 0
- **PSR ≥ 0.95** required

### 6.5 Holdout (2024-01-01 to 2026-02-20)
- Sharpe > 0 required; CAGR, MDD reported
- Single path — not decisive alone, but must not collapse

### 6.6 Cost Sweep (5-50 bps RT)
- Must remain Sharpe > 0 at 50 bps
- Report crossover points vs benchmarks

### 6.7 Regime Stability (4 epochs)
- Pre-2021, 2021-2022, 2023-2024, 2025+
- **No epoch with Sharpe < 0** (absolute requirement)
- **No epoch with Sharpe < 0.3** (strong preference)

### 6.8 Parameter Plateau
- ±20% perturbation on each tunable parameter
- **ΔSharpe ≤ 0.05** across perturbation range
- Sharp peak = overfit → reject regardless of full-sample performance

### 6.9 Trade Analysis
- Report: best/worst trade, avg holding period, churn count (re-entry ≤24h)
- Flag if best trade < 30% (potential fat-tail truncation)
- Flag if churn > 5% of trades

---

## 7. What "Better" Means (ranked)

A new system is considered better if it achieves:

1. **Higher bootstrap median Sharpe** (primary — this is the robustness measure)
2. **Higher P(Sharpe > 0)** in bootstrap
3. **Lower MDD** at comparable or higher CAGR
4. **Wider parameter plateau** (fewer parameters preferred)
5. **Higher full-sample Sharpe** (secondary — subject to bootstrap confirmation)

A system that wins full-sample but loses bootstrap is **NOT better** — it has
path-specific edge that doesn't generalize.

---

## 8. Deliverables

1. **Phase 1 report**: Data decomposition findings, ranked by exploitable information content
2. **Design document**: Mechanism rationale for each component (entry, exit, sizing, filters)
3. **Full evaluation** (all 9 sections from §6), with comparison table vs benchmarks
4. **Verdict**: one of:
   - **SUPERIOR**: beats BOTH benchmarks on bootstrap + passes all gates
   - **COMPETITIVE**: matches benchmarks within bootstrap CI — confirms optimality zone
   - **INFERIOR**: fails to match benchmarks — document why and what was learned
5. **Charts**: equity curves, bootstrap distributions, WFO Sharpe per window,
   cost sensitivity, regime decomposition

---

## 9. Anti-Patterns (will result in immediate rejection)

- Using future data in any form (lookahead)
- Optimizing on full sample then "validating" on the same data
- Reporting full-sample Sharpe as primary evidence (bootstrap is primary)
- Adding complexity without bootstrap-proven benefit
- Ignoring the proven dead-ends listed in §5
- Claiming improvement without quantified statistical evidence
- Using more than 6 tunable parameters without extraordinary justification
