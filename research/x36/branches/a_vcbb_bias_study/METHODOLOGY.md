# Methodology: Comprehensive Strategy Evaluation Framework

**Version**: 2.0 | **Date**: 2026-03-15 | **First applied**: X36 (V3 vs V4 vs E5+EMA21D1)

This document specifies the complete evaluation methodology for comparing BTC spot
long-only strategies. Follow this protocol to produce a report with identical structure
and rigor as X36's `results/CONCLUSIONS.md`.

> Status note (2026-03-17):
> - This file mixes branch-local legacy comparison methods with reference notes about
>   the repo validation stack.
> - Current repo authority for validation semantics is `validation/` plus
>   `docs/validation/decision_policy.md`, not this document.
> - In particular: PSR is now diagnostic/info-only, bootstrap is diagnostic-only,
>   and authoritative WFO inference uses candidate-vs-baseline deltas with
>   `valid_window` / `low_trade_window` handling and possible delegation to
>   `trade_level_bootstrap`.
> - Section 4's branch-local WFO is descriptive only and its final window
>   `2025-01-01 -> 2026-02-20` is 416 days, so it should not be interpreted as a
>   literal uniform `12 × 6-month` test.
> - The branch-local holdout `2024-01-01 -> 2026-02-20` overlaps later WFO windows,
>   so those two evidence layers are not independent here.

---

## Table of Contents

**Part I — Core Evaluation (9 Sections, run in X36)**
1. [Overview & Philosophy](#1-overview--philosophy)
2. [Prerequisites](#2-prerequisites)
3. [Data Pipeline](#3-data-pipeline)
4. [Section 1: Full-Sample Backtest](#4-section-1-full-sample-backtest)
5. [Section 2: Probabilistic Sharpe Ratio (PSR)](#5-section-2-probabilistic-sharpe-ratio-psr)
6. [Section 3: Holdout Evaluation](#6-section-3-holdout-evaluation)
7. [Section 4: Walk-Forward (WFO)](#7-section-4-walk-forward-wfo)
8. [Section 5: Cost Sweep](#8-section-5-cost-sweep)
9. [Section 6: Regime/Epoch Decomposition](#9-section-6-regimeepoch-decomposition)
10. [Section 7: Trade-Level Statistics](#10-section-7-trade-level-statistics)
11. [Section 8: VCBB Bootstrap](#11-section-8-vcbb-bootstrap)
12. [Section 9: Visualization](#12-section-9-visualization)

**Part II — Advanced Techniques (from validation pipeline & research libs)**
13. [Lookahead Detection](#13-lookahead-detection)
14. [Data Integrity Checks](#14-data-integrity-checks)
15. [Invariant Checks](#15-invariant-checks)
16. [Deflated Sharpe Ratio (DSR)](#16-deflated-sharpe-ratio-dsr)
17. [Effective DOF / Nyholt M_eff](#17-effective-dof--nyholt-m_eff)
18. [WFO Statistical Tests (Wilcoxon + Bootstrap CI)](#18-wfo-statistical-tests-wilcoxon--bootstrap-ci)
19. [Trade-Level Matched-Pair Bootstrap](#19-trade-level-matched-pair-bootstrap)
20. [Subsampling (Politis-Romano-Wolf)](#20-subsampling-politis-romano-wolf)
21. [Drawdown Episode Analysis](#21-drawdown-episode-analysis)
22. [Sensitivity / Parameter Sweep](#22-sensitivity--parameter-sweep)
23. [Holdout/WFO Overlap Detection](#23-holdoutwfo-overlap-detection)
24. [Pair Diagnostic](#24-pair-diagnostic)
25. [Churn Metrics (Detailed)](#25-churn-metrics-detailed)
26. [Regression Guard](#26-regression-guard)

**Part III — Decision & Reporting**
27. [Multi-Layer Verdict Framework](#27-multi-layer-verdict-framework)
28. [Interpretation Guidelines](#28-interpretation-guidelines)
29. [Implementation Template](#29-implementation-template)
30. [Checklist](#30-checklist)

---

## 1. Overview & Philosophy

### Core Principle

No single metric or test can validate a trading strategy. This framework evaluates
strategies across **7 independent evidence layers**, each testing a different facet
of robustness. A strategy must demonstrate strength across MULTIPLE layers to be
considered superior.

### Evidence Layers

**Core (Part I — always run):**

| # | Layer | What It Tests | Authority Level |
|---|-------|---------------|-----------------|
| 1 | Full-sample | Absolute performance on observed data | Medium (single path) |
| 2 | PSR | Statistical significance of Sharpe > 0 | High (accounts for non-normality) |
| 3 | Holdout | Out-of-sample performance | Medium (single path, short window) |
| 4 | WFO | Temporal stability across regimes | High (12 independent windows) |
| 5 | Cost sweep | Sensitivity to transaction costs | Medium (structural property) |
| 6 | Regime decomp | Epoch-specific behavior | Medium (4 sub-samples) |
| 7 | Bootstrap (VCBB) | Generalization to DGP | **Highest** (500 resampled paths) |

**Advanced (Part II — from validation pipeline, add when needed):**

| # | Layer | What It Tests | Authority Level |
|---|-------|---------------|-----------------|
| 8 | Lookahead | No future data leakage | **Hard gate** (pass/fail) |
| 9 | Data integrity | Input data quality | **Hard gate** (pass/fail) |
| 10 | Invariants | Engine logic correctness | **Hard gate** (pass/fail) |
| 11 | DSR | Selection bias from N trials | Advisory (diagnostic) |
| 12 | Effective DOF | Correlated multiple tests | Correction factor |
| 13 | WFO Wilcoxon + CI | Formal WFO hypothesis test | High (binding gate) |
| 14 | Trade-level bootstrap | Per-trade matched comparison | High (conditional gate) |
| 15 | Subsampling | Deterministic non-parametric | Medium (confirmation) |
| 16 | Drawdown episodes | Crash forensics | Diagnostic |
| 17 | Sensitivity sweep | Parameter robustness | Medium (overfit detector) |
| 18 | Pair diagnostic | Equity similarity classification | Diagnostic |
| 19 | Churn metrics | Fee drag & cascade analysis | Diagnostic |
| 20 | Regression guard | Golden snapshot comparison | **Hard gate** (pass/fail) |

### Why Bootstrap Has Highest Authority

Full-sample, holdout, and WFO are all computed on **one observed path**. The market
could have taken a different path consistent with the same data-generating process (DGP).
Bootstrap resamples 500 paths from the DGP, testing whether the strategy's edge
generalizes beyond the specific sequence of events we happened to observe.

A strategy that ranks #1 in full-sample but #2 in bootstrap has a **path-specific**
edge — likely exploiting autocorrelation patterns unique to the observed sample.

---

## 2. Prerequisites

### System Requirements

```python
# Environment
Python       : 3.12+
Venv         : /var/www/trading-bots/.venv
Repo root    : /var/www/trading-bots/btc-spot-dev
Pkg manager  : uv

# Key imports
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import Bar, CostConfig, SCENARIOS
from v10.core.metrics import PERIODS_PER_YEAR_4H  # = 2190
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
```

### Data

Primary data file: `data/bars_btcusdt_2016_now_h1_4h_1d.csv`
- H4 + D1 bars, 2017-08 to latest
- Required columns: open_time, open, high, low, close, volume, close_time,
  taker_buy_base_vol, interval, quote_volume

### Strategy Interface

Every strategy under test must implement the `Strategy` ABC:

```python
from v10.strategies.base import Strategy
from v10.core.types import MarketState, Signal, Fill

class MyStrategy(Strategy):
    def name(self) -> str: ...
    def on_init(self, h4_bars: list, d1_bars: list) -> None: ...
    def on_bar(self, state: MarketState) -> Signal | None: ...
    def on_after_fill(self, state: MarketState, fill: Fill) -> None: ...
```

---

## 3. Data Pipeline

### 3.1 Fast Loading (recommended over DataFeed for research)

```python
def _fast_load_bars(path: Path) -> tuple[list[Bar], list[Bar]]:
    """Load CSV → (h4_bars, d1_bars) using itertuples (~10x faster)."""
    df = pd.read_csv(path)
    h4_df = df[df["interval"] == "4h"].sort_values("open_time")
    d1_df = df[df["interval"] == "1d"].sort_values("open_time")
    # Convert to Bar objects using itertuples (NOT iterrows)
    ...
```

### 3.2 Sub-Feed Construction

To run backtests on date ranges (holdout, WFO, epochs), construct `PreloadedFeed`
objects from pre-loaded bar lists:

```python
class PreloadedFeed:
    """DataFeed-compatible object built from pre-filtered bar lists."""
    def __init__(self, h4, d1, report_start_ms=None):
        self.h4_bars = h4
        self.d1_bars = d1
        self.report_start_ms = report_start_ms

def make_sub_feed(all_h4, all_d1, start, end, warmup=365):
    """Filter bars to [start - warmup, end] with report_start_ms = start."""
    start_ms = _date_ms(start)
    end_ms = _date_ms(end) + 86_400_000 - 1
    load_ms = start_ms - warmup * 86_400_000
    h4 = [b for b in all_h4 if load_ms <= b.open_time <= end_ms]
    d1 = [b for b in all_d1 if load_ms <= b.open_time <= end_ms]
    return PreloadedFeed(h4, d1, start_ms)
```

**Key**: `warmup=365` days included BEFORE `start` so indicators (EMA, ATR) are
fully initialized. BacktestEngine's `warmup_mode="no_trade"` suppresses trades
during warmup but runs indicators.

### 3.3 Cost Configuration

```python
def make_cost(rt_bps: float) -> CostConfig:
    """Decompose round-trip bps into spread + slippage + fee."""
    ps = rt_bps / 2.0  # per-side bps
    return CostConfig(
        spread_bps=ps * 0.5,       # 25% of RT
        slippage_bps=ps * 0.25,    # 12.5% of RT
        taker_fee_pct=ps * 0.005,  # 12.5% of RT (in pct, not bps)
    )
```

Standard decomposition: spread 50%, slippage 25%, fee 25% of per-side cost.
This is a simplification; for precise cost modeling see X33 results.

### 3.4 Running a Single Backtest

```python
def run_one(feed, strategy_factory, cost=COST_20):
    s = strategy_factory()
    e = BacktestEngine(
        feed=feed, strategy=s, cost=cost,
        initial_cash=10_000.0, warmup_mode="no_trade",
    )
    return e.run()
```

**BacktestEngine contract**:
- Event-driven loop over H4 bars
- Signal at bar close → fill at **next bar open** (next-open fill model)
- `result.summary` → dict of metrics from `compute_metrics()`
- `result.equity` → list of `EquitySnap` (per-bar NAV)
- `result.trades` → list of `Trade` objects

---

## 4. Section 1: Full-Sample Backtest

### Purpose
Establish absolute performance of each strategy on the complete observed data.

### Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Start | 2019-01-01 | Post-warmup period start |
| End | 2026-02-20 | Latest available data |
| Warmup | 365 days | Indicators fully initialized |
| Cost | 20 bps RT | Measured median cost (X33) |
| Initial cash | $10,000 | Standardized |

### Metrics Extracted

| Metric | Key | Formula / Source |
|--------|-----|------------------|
| Sharpe | `sharpe` | `(mean(r) / std(r, ddof=0)) × sqrt(2190)`, r = 4H returns |
| CAGR (%) | `cagr_pct` | `(final_nav / report_start_nav)^(1/years) - 1` |
| Max Drawdown (%) | `max_drawdown_mid_pct` | `max(1 - nav / peak_nav) × 100` |
| Trades | `trades` | Count of round-trip trades |
| Win Rate (%) | `win_rate_pct` | `wins / trades × 100` |
| Profit Factor | `profit_factor` | `gross_profit / abs(gross_loss)` |
| Avg Exposure | `avg_exposure` | Mean of per-bar position fraction |
| Sortino | `sortino` | `(mean(r) / std(r_neg, ddof=0)) × sqrt(2190)` |
| Calmar | `calmar` | `CAGR / max_drawdown_mid_pct` |
| Final NAV | `final_nav_mid` | Mark-to-market NAV at last bar |

### Key Formulas

**Sharpe Ratio** (annualized from H4 bars):
```
r_i = (NAV_i - NAV_{i-1}) / NAV_{i-1}     for each H4 bar
SR = mean(r) / std(r, ddof=0) × √2190
```
- `ddof=0` = population standard deviation (not sample)
- `2190 = (24/4) × 365` = H4 bars per year
- No risk-free rate subtracted (crypto convention)

**CAGR** (compound annual growth rate):
```
CAGR = (final_nav / initial_nav)^(1/years) - 1
years = (last_close_time - first_close_time) / (365.25 × 24 × 3600 × 1000)
```

**Maximum Drawdown**:
```
peak_i = max(NAV_0, NAV_1, ..., NAV_i)
dd_i = 1 - NAV_i / peak_i
MDD = max(dd_i) × 100%
```

**Sortino**: Same as Sharpe but denominator uses only negative returns:
```
Sortino = mean(r) / std(r[r<0], ddof=0) × √2190
```

**Calmar**: `CAGR / MDD`

### Output
- Table: rows = metrics, columns = strategies
- CSV: `results/full_sample_metrics.csv`

---

## 5. Section 2: Probabilistic Sharpe Ratio (PSR)

### Purpose
Test whether the observed Sharpe ratio is statistically significantly greater than
zero, accounting for non-normal return distributions (skewness, kurtosis).

### Formula (Bailey & López de Prado, 2012)

```
PSR(SR*) = Φ(z)
z = (SR_obs - SR*) × √(n-1) / √(1 - γ₃·SR + (γ₄-1)/4 · SR²)
```

Where:
- `SR_obs` = observed Sharpe ratio (annualized)
- `SR*` = benchmark Sharpe (typically 0)
- `n` = number of return observations (H4 bars)
- `γ₃` = skewness of returns
- `γ₄` = excess kurtosis + 3 (raw kurtosis)
- `Φ` = standard normal CDF

### Implementation

```python
def compute_psr(navs: np.ndarray, sr_bench: float = 0.0) -> float:
    rets = np.diff(navs) / navs[:-1]
    n = len(rets)
    sr = (rets.mean() / rets.std(ddof=0)) * math.sqrt(PERIODS_PER_YEAR_4H)
    skew = pd.Series(rets).skew()
    kurt = pd.Series(rets).kurtosis() + 3  # raw kurtosis
    denom_sq = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2
    z = (sr - sr_bench) * math.sqrt(n - 1) / math.sqrt(denom_sq)
    return float(norm.cdf(z))
```

### Interpretation
- PSR ≥ 0.95 → strong evidence that true Sharpe > 0
- PSR < 0.95 → insufficient evidence (used as gate in validation pipeline)
- PSR is computed from full equity curve (including all H4 bars)

### Output
- JSON: `results/psr.json`

---

## 6. Section 3: Holdout Evaluation

### Purpose
Out-of-sample test on the most recent data, never used in strategy development
or parameter selection.

### Parameters

| Parameter | Value |
|-----------|-------|
| Holdout start | 2024-01-01 |
| Holdout end | 2026-02-20 (= dataset end) |
| Warmup | 365 days before holdout start |
| Cost | Same as full-sample (20 bps) |

### Metrics
Same as full-sample (Sharpe, CAGR, MDD, Trades, Win Rate, Profit Factor).

### Caveats
- Single path → limited statistical power
- Short window (~2 years) → regime-dependent
- Do NOT use holdout as sole evidence; combine with bootstrap

### Output
- CSV: `results/holdout_metrics.csv`

---

## 7. Section 4: Walk-Forward (WFO)

### Purpose
Test temporal stability — does the strategy maintain positive performance across
different market regimes? WFO splits the timeline into non-overlapping 6-month
windows and runs independent backtests on each.

### Windows

```python
WFO_WINDOWS = [
    ("2019-07-01", "2019-12-31"),
    ("2020-01-01", "2020-06-30"),
    ("2020-07-01", "2020-12-31"),
    ("2021-01-01", "2021-06-30"),
    ("2021-07-01", "2021-12-31"),
    ("2022-01-01", "2022-06-30"),
    ("2022-07-01", "2022-12-31"),
    ("2023-01-01", "2023-06-30"),
    ("2023-07-01", "2023-12-31"),
    ("2024-01-01", "2024-06-30"),
    ("2024-07-01", "2024-12-31"),
    ("2025-01-01", "2026-02-20"),
]
```

12 windows, each with 365-day warmup before window start.

### Summary Metrics
- **Windows positive**: count of windows where Sharpe > 0
- **Mean Sharpe**: arithmetic mean across all windows
- **Median Sharpe**: median across all windows (robust to outliers)

### Interpretation
- 10+/12 positive → temporally stable
- Mean ≫ Median → skewed by one extreme window (investigate)
- Mean ≪ Median → one bad window dragging mean (identify regime)

### Output
- CSV: `results/wfo_results.csv` (columns: window, strategy, sharpe, cagr_pct, ...)

---

## 8. Section 5: Cost Sweep

### Purpose
Test sensitivity to transaction costs. Identifies strategies that degrade rapidly
at higher costs (high-frequency signals) vs those that are cost-resilient.

### Cost Levels

```python
COST_LEVELS = [5, 10, 15, 20, 25, 30, 40, 50]  # round-trip bps
```

Each level uses `make_cost(rt_bps)` to decompose into spread + slippage + fee.

### Analysis
- Plot Sharpe vs cost for each strategy
- Compute **degradation slope**: `(Sharpe_5 - Sharpe_50) / 45`
- Steeper slope = more cost-sensitive = more trades or shorter holding period
- **Crossover point**: cost level where ranking between two strategies flips

### Interpretation
- Strategy with flattest slope has best **cost resilience**
- If Strategy A > B at 5 bps but B > A at 50 bps → the crossover cost determines
  which is better for your actual execution environment
- Pair with X33 measured costs (median 16.8 bps RT) to identify production-relevant level

### Output
- CSV: `results/cost_sweep.csv`

---

## 9. Section 6: Regime/Epoch Decomposition

### Purpose
Identify regime-dependent performance. A robust strategy should be positive in
ALL regimes, though magnitude may vary.

### Epochs

```python
EPOCHS = [
    ("Pre-2021",   "2019-01-01", "2020-12-31"),  # BTC pre-institutional
    ("2021-2022",  "2021-01-01", "2022-12-31"),  # Bull → bear (Luna, FTX)
    ("2023-2024",  "2023-01-01", "2024-12-31"),  # Recovery → ETF → ATH
    ("2025+",      "2025-01-01", "2026-02-20"),  # Most recent (short)
]
```

Each epoch gets a full backtest with 365-day warmup.

### Analysis
- Which strategy wins each epoch?
- Is any strategy consistently #1? Consistently last?
- Near-zero Sharpe in recent epoch = forward risk flag

### Output
- CSV: `results/regime_decomposition.csv`

---

## 10. Section 7: Trade-Level Statistics

### Purpose
Characterize the micro-structure of each strategy's trades. Reveals WHY strategies
differ, not just that they do.

### Metrics

| Metric | What It Reveals |
|--------|-----------------|
| Trade count | Signal frequency |
| Win rate | Hit rate (higher ≠ better for trend-following) |
| Avg return | Mean per-trade return |
| Median return | Typical trade (robust to outliers) |
| Avg/median days held | Holding period |
| Best/worst trade | Tail capture (critical for trend-following) |
| Churn ≤12h/≤24h | Re-entry within N hours (whipsaw indicator) |

### Key Diagnostic: Fat-Tail Alpha

For trend-following strategies, the **best trade** metric is critical:
- If Strategy A best = 63% and Strategy B best = 22%, then B is truncating
  winning trades (e.g., via time stop, tighter trail, or forced exit)
- Top 5% of trades often account for 100%+ of total profits
- Any mechanism that truncates winners MUST be evaluated against its cost

### Churn Calculation

```python
entry_times = sorted(t.entry_ts_ms for t in trades)
gaps = [(entry_times[i] - entry_times[i-1]) / (3600*1000) for i in range(1, len(entry_times))]
churn_12h = sum(1 for g in gaps if g <= 12)
churn_24h = sum(1 for g in gaps if g <= 24)
```

### Output
- CSV: `results/trade_stats.csv`

---

## 11. Section 8: VCBB Bootstrap

### Purpose
**Most important section.** Test whether each strategy's edge generalizes to the
data-generating process (DGP), not just the one observed price path.

### Method: Volatility-Conditioned Block Bootstrap (VCBB)

Standard block bootstrap draws blocks uniformly, destroying 84% of BTC's volatility
clustering at block boundaries. VCBB conditions next-block selection on realized
volatility via K-nearest-neighbor lookup, preserving cross-block vol continuity.

### Algorithm

```
Input: H4 close/high/low/volume/taker_buy arrays
Parameters: blksz=60, ctx=90, K=50, N_BOOT=500, seed=1337

1. Compute multiplicative ratios:
   cr[i] = close[i+1] / close[i]  (similarly for high, low)
   vol, tb are shifted copies

2. Precompute vol lookup:
   rvol[i] = std(log(cr[i-ctx+1 : i+1]))  (rolling realized vol)
   Sort valid block starts by rvol for binary search

3. For each bootstrap path p = 1..500:
   a. Select blocks via vol-conditioning:
      - First block: uniform random
      - Subsequent: compute rvol from SYNTHETIC path's accumulated returns,
        find K=50 nearest neighbors in original data's rvol, select uniformly
   b. Build flat index array from selected blocks
   c. Reconstruct 5-channel price path (close, high, low, volume, taker_buy)
   d. Aggregate D1 bars from H4 (every 6 bars)
   e. Build PreloadedFeed with synthetic bars
   f. Run backtest for each strategy under test
   g. Extract metrics (Sharpe, CAGR, MDD)
```

### Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `blksz` | 60 bars (10 days H4) | Preserves intra-block autocorrelation |
| `ctx` | 90 bars | Window for realized vol computation |
| `K` | 50 | KNN neighbors for vol matching |
| `N_BOOT` | 500 | Statistical adequacy for median/CI |
| `seed` | 1337 | Reproducibility |
| Cost | Same as full-sample | Fair comparison |

### Synthetic Bar Construction

```python
def _build_synthetic_feed(c, h, l, v, tb, qv, warmup_days=WARMUP, base_ts=None):
    """Build DataFeed-compatible object from VCBB arrays."""
    ts0 = base_ts if base_ts is not None else BASE_TS
    n = len(c)
    h4_bars = []
    for i in range(n):
        ot = ts0 + i * H4_MS
        ct = ot + H4_MS - 1
        op = c[i-1] if i > 0 else c[0]
        h4_bars.append(Bar(
            open_time=ot, open=op, high=h[i], low=l[i], close=c[i],
            volume=v[i], close_time=ct, taker_buy_base_vol=tb[i],
            interval="4h", quote_volume=qv[i],
        ))
    # D1: aggregate every 6 H4 bars
    d1_bars = [_aggregate_6bars(h4_bars[j:j+6]) for j in range(0, n, 6)]
    report_start_ms = ts0 + warmup_days * D1_MS
    return PreloadedFeed(h4_bars, d1_bars, report_start_ms)
```

### Summary Statistics

For each strategy, compute over 500 paths:
- **Median Sharpe** (central tendency, robust to outliers)
- **Mean Sharpe** (for comparison)
- **P5/P95 Sharpe** (90% confidence interval)
- **Median CAGR**, **Median MDD**
- **P(Sharpe > 0)** = fraction of paths with positive Sharpe

### Interpretation Guidelines

| Metric | Strong | Acceptable | Weak |
|--------|--------|------------|------|
| P(Sharpe > 0) | ≥ 95% | 85-95% | < 85% |
| P5 Sharpe | > 0 | > -0.2 | < -0.2 |
| Median Sharpe | > 0.6 | 0.3-0.6 | < 0.3 |

### Critical Check: Full-Sample vs Bootstrap Rank Reversal

If **full-sample ranking ≠ bootstrap ranking**, the full-sample winner has
path-specific edge. This is the single most important diagnostic in the
entire framework. Document which features cause the reversal and why.

### Output
- JSON: `results/bootstrap_summary.json`

---

## 12. Section 9: Visualization

### 5 Required Charts

#### 1. Equity & Drawdown (2-panel)
- Top: log-scale NAV curves for all strategies
- Bottom: drawdown (%) with fill_between
- Shared x-axis (time)
- Color-coded by strategy

#### 2. Bootstrap Distributions (3-panel)
- Sharpe histogram (density), CAGR histogram, MDD histogram
- All strategies overlaid with alpha transparency
- Legend shows median value per strategy
- Title includes N_BOOT and cost

#### 3. WFO Sharpe (grouped bar)
- X-axis: 6-month windows
- Grouped bars: one per strategy per window
- Horizontal line at Sharpe = 0
- Rotated x-labels for readability

#### 4. Cost Sensitivity (line)
- X-axis: round-trip cost (bps)
- Y-axis: Sharpe ratio
- One line per strategy with markers
- Crossover points visible

#### 5. Regime Decomposition (grouped bar)
- X-axis: epochs
- Grouped bars: one per strategy per epoch
- Shows which strategy dominates each regime

### Chart Configuration

```python
COLORS = {
    "Strategy_A": "#e63946",  # red
    "Strategy_B": "#457b9d",  # blue
    "Strategy_C": "#2a9d8f",  # teal
    # Add more as needed
}
# Save: fig.savefig(path, dpi=150)
# Backend: matplotlib.use("Agg")
```

### Output
- PNG: `figures/equity_drawdown.png`, `figures/bootstrap_distributions.png`,
  `figures/wfo_sharpe.png`, `figures/cost_sensitivity.png`,
  `figures/regime_decomposition.png`

---

---

# Part II — Advanced Techniques

These techniques are implemented in the formal `validation/` pipeline and `research/lib/`
libraries. They were applied to E0/E5/E5+EMA21D1 during the algorithm discovery phase.
Include them when the evaluation warrants formal rigor beyond the 9 core sections.

---

## 13. Lookahead Detection

### Purpose
**Hard gate.** Verify the strategy cannot see future data — the single most critical
integrity check. Any lookahead violation invalidates ALL backtest results.

### Method
Run pytest on dedicated no-lookahead test files that verify:
- Strategy signals at bar `i` use only data from bars `0..i`
- No high-timeframe (D1) data leaks into H4 decisions before the D1 bar closes
- Multi-timeframe alignment is correct (D1 bar available only after 6th H4 bar)

### Implementation
```python
# validation/suites/lookahead.py
# Runs: pytest -q v10/tests/test_no_lookahead_htf.py
#                  v10/tests/test_v10_no_lookahead_htf.py
#                  v10/tests/test_mtf_alignment.py
# PASS: 0 test failures. FAIL: any test fails → hard REJECT.
```

### Threshold
- **Zero violations required** — no tolerance
- Gate type: **hard** — failure → REJECT (exit code 2)

### When to Use
Always. Every new strategy must pass lookahead detection before any other evaluation.

---

## 14. Data Integrity Checks

### Purpose
Pre-backtest sanity checks on bar data to ensure the input is clean.

### Checks Performed
| Check | Description | Severity |
|-------|-------------|----------|
| OHLC ordering | `low ≤ open,close ≤ high` | hard-fail |
| Duplicate timestamps | Same `open_time` appears twice | hard-fail |
| Gap detection | Missing bars beyond expected schedule | warning |
| Price consistency | Extreme moves (>50% per bar) | warning |
| Volume sanity | Zero or negative volume | warning |

### Implementation
```python
# validation/suites/data_integrity.py → DataIntegritySuite
# Output: data_integrity.json, data_integrity_issues.csv
# Hard-fail flag: if hard_fail=true → abort all remaining suites (ERROR, exit 3)
```

### When to Use
Always, as the first suite. Data quality issues propagate to ALL downstream results.

---

## 15. Invariant Checks

### Purpose
Logic consistency verification during backtest execution. Catches bugs in strategy
implementation or engine interaction.

### Invariants Verified
| Invariant | Formula | Tolerance |
|-----------|---------|-----------|
| Exposure bounds | `0 ≤ exposure ≤ max_exposure` | ε = 0.005 |
| Cost accuracy | `Σ(trade_costs) = total_fees` | ε = 1e-9 |
| P&L accounting | `final_nav = initial + Σ(pnl) - Σ(fees)` | ε = 1e-9 |
| Fill timing | Signal at bar `i` → fill at bar `i+1` open | exact |

### Implementation
```python
# validation/suites/invariants.py → InvariantsSuite
# Re-runs backtest with inline checks. Max 200 violations reported.
# Any violation → ERROR (exit code 3)
```

### When to Use
Always for new strategies. Optional for well-tested strategies being compared.

---

## 16. Deflated Sharpe Ratio (DSR)

### Purpose
Correct observed Sharpe for **multiple testing bias** — if you tested N strategy
variants, the best one's Sharpe is inflated by selection.

### Formula (Bailey & López de Prado, 2014)

```
SR₀ = [(1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))] · √(1/(n-1))
DSR = (SR - SR₀) · √(n-1) / √[1 - γ₃·SR + ((γ₄-1)/4)·SR²]
p   = Φ(DSR)
```

Where:
- `γ` = 0.5772... (Euler-Mascheroni constant)
- `N` = number of strategy variants tested
- `n` = number of return observations
- `γ₃` = skewness, `γ₄` = raw kurtosis

### Key Distinction: DSR vs PSR
| | DSR | PSR |
|---|-----|-----|
| Question | "Does SR beat random noise from N trials?" | "Does candidate SR beat baseline SR?" |
| Benchmark | SR₀ (expected max under null) | Baseline strategy's SR |
| Use case | Absolute: is there any signal? | Relative: is A better than B? |
| Status | Advisory (trivially passed for SR > 1) | Binding gate (PSR ≥ 0.95) |

### Implementation
```python
from research.lib.dsr import compute_dsr, benchmark_sr0
result = compute_dsr(returns, num_trials=245)  # 245 = total strategies explored
# result['dsr_pvalue'] → probability SR is genuine (> SR₀)
```

### When to Use
When reporting how many strategy variants were tested. Critical for honest reporting.
Advisory in validation pipeline (PSR is the binding gate).

---

## 17. Effective DOF / Nyholt M_eff

### Purpose
Correct p-values when testing across **correlated timescales or parameters**.
16 timescales with ρ ≈ 0.8 are NOT 16 independent tests.

### Three Methods

| Method | Formula | Character |
|--------|---------|-----------|
| **Nyholt (2004)** | `M_eff = 1 + (K-1)(1 - Var(λ)/K)` | Conservative |
| **Li-Ji (2005)** | `M_eff = Σ f(λ_i)`, f counts eigenvalues ≥1 + fractions | Moderate |
| **Galwey (2009)** | `M_eff = (Σλ)² / Σλ²` | Most intuitive |

Where `λ_i` are eigenvalues of the K×K correlation matrix.

### Example
16 timescales (slow_period 60-200), cross-timescale ρ ≈ 0.8:
- Nyholt M_eff ≈ 4.35 → effectively 4.35 independent tests, not 16
- 16/16 wins nominal p = 1.5e-5 → corrected p ≈ 0.031 (still significant)

### Implementation
```python
from research.lib.effective_dof import compute_meff, corrected_binomial
meff = compute_meff(corr_matrix)  # dict: nyholt, li_ji, galwey, conservative
result = corrected_binomial(wins=16, K=16, corr_matrix=corr_matrix)
# result['corrected']['nyholt']['p_value']
```

### When to Use
Whenever claiming a result holds "across N timescales/parameters" and those
parameters are correlated. Essential for honest multiple-testing correction.

---

## 18. WFO Statistical Tests (Wilcoxon + Bootstrap CI)

### Purpose
The validation pipeline's WFO gate uses formal statistical tests on the per-window
deltas, not just a win count. More rigorous than Section 4's simple summary.

### Method 1: Wilcoxon Signed-Rank Test
```
H₀: median(Δ_score) = 0
H₁: median(Δ_score) > 0  (one-sided)
α = 0.10 (for small N ≈ 8 windows)
```
At N=8, minimum achievable p-value = 1/256 ≈ 0.004. Power at α=0.05 is poor.

### Method 2: Bootstrap CI on Mean Delta
```
10,000 bootstrap resamples of per-window deltas
95% CI (percentile method)
PASS iff lower bound > 0
```

### Gate Logic
**PASS if EITHER test confirms:** Wilcoxon p ≤ 0.10 OR Bootstrap CI excludes 0.
This OR-gate prevents false negatives when one test lacks power.

### Implementation
```python
# validation/suites/wfo.py — computed within WFOSuite.run()
# Thresholds from validation/thresholds.py:
WFO_WILCOXON_ALPHA = 0.10
WFO_BOOTSTRAP_N_RESAMPLES = 10_000
WFO_BOOTSTRAP_CI_ALPHA = 0.05
```

### When to Use
When comparing a candidate against a baseline (paired WFO deltas available).
Not applicable for standalone strategy evaluation (use Section 4 instead).

---

## 19. Trade-Level Matched-Pair Bootstrap

### Purpose
Per-trade granular analysis. Matches trades between candidate and baseline by
entry timestamp, then bootstraps the return differences.

### Method
1. **Deterministic matching**: match trades by `(entry_ts_ms, entry_price)`
2. **Return differences**: `Δ_return[i] = candidate_return[i] - baseline_return[i]`
3. **Block bootstrap** on Δ_return (block sizes 42, 84, 168 bars)
4. **10,000 resamples** → 95% CI, P(Δ > 0)
5. **Entry risk classification**: low_non_chop, medium_chop, high_chop_stretch

### Gate Logic (conditional)
Only activated when WFO is low-power (< 3 power windows or > 50% low-trade windows).
When active: FAIL if CI crosses zero AND mean_diff ≤ 0.0002 (0.02 bps).

### Implementation
```python
# validation/suites/trade_level.py → TradeLevelSuite
# Output: matched_trades.csv, bootstrap_return_diff.json
# Constants:
BOOTSTRAP_BLOCK_LENGTHS = (42, 84, 168)
BOOTSTRAP_RESAMPLES = 10_000
SMALL_MEAN_IMPROVEMENT_THRESHOLD = 0.0002
```

### When to Use
When WFO has insufficient statistical power. Also useful as diagnostic even
when WFO is sufficient — reveals per-trade mechanism differences.

---

## 20. Subsampling (Politis-Romano-Wolf)

### Purpose
**Deterministic** non-parametric inference (no random seed needed). Uses
overlapping sub-blocks of the original equity path for confidence intervals.

### Method
- Paired block subsampling: candidate vs baseline equity paths
- Overlapping blocks (unlike bootstrap which resamples with replacement)
- Computes CI, p-value, and support ratio per cost scenario
- Multiple block sizes tested → aggregated via `summarize_block_grid()`

### Key Advantage
Deterministic → identical results every run. No seed sensitivity.

### Implementation
```python
# validation/suites/subsampling.py → SubsamplingSuite
# Calls v10.research.subsampling.paired_block_subsampling()
# Parameters: ci_level=0.95, max_blocks, p_threshold=0.05
```

### When to Use
As complement to bootstrap — provides a second non-parametric inference method
that doesn't depend on random seed. Good for confirmation.

---

## 21. Drawdown Episode Analysis

### Purpose
Identify and rank individual drawdown episodes (peak-to-trough segments) for
forensic analysis. Reveals WHEN and HOW drawdowns occur.

### Method
1. Detect all drawdown episodes with depth ≥ 5%
2. For each episode record: peak date, trough date, recovery date, depth %,
   bars to trough, days to recovery
3. Rank by depth (largest first)
4. Compare candidate vs baseline episode profiles

### Implementation
```python
# validation/suites/dd_episodes.py → DDEpisodesSuite
# Calls v10.research.drawdown.detect_drawdown_episodes(min_dd_pct=5.0)
# Output: dd_episodes_candidate.csv, dd_episodes_baseline.csv
```

### When to Use
When MDD is a key concern or when strategies have similar Sharpe but
different drawdown profiles. Reveals whether one strategy avoids specific
crash events better than another.

---

## 22. Sensitivity / Parameter Sweep

### Purpose
Test whether performance is robust to small parameter perturbations.
A strategy that collapses with ±10% parameter change is over-optimized.

### Method
- Define parameter grid: e.g., `trail_mult: [2.5, 3.0, 3.5]`
- For each combination, build strategy and run full backtest
- Output Sharpe, CAGR, MDD per parameter combo
- Look for: flat plateau (robust) vs sharp peak (overfit)

### Implementation
```python
# validation/suites/sensitivity.py → SensitivitySuite
# Config: validation_config.sensitivity_grid = {param: [values]}
# Output: sensitivity_grid.csv
```

### When to Use
For any strategy being considered for production. Essential to distinguish
genuine edge from parameter overfit. VTREND's plateau (slow=60-144,
spread 0.017 Sharpe) is the gold standard.

---

## 23. Holdout/WFO Overlap Detection

### Purpose
Check whether holdout period overlaps with WFO test windows. If they overlap,
holdout and WFO gates are NOT statistically independent — failing both is
less damning than failing two independent tests.

### Method
```
For each WFO window:
  overlap_days = max(0, min(holdout_end, wfo_end) - max(holdout_start, wfo_start))
If max_overlap > 30 days AND both gates fail AND overlap > 50%:
  → WFO failure downgraded from soft-fail to correlated advisory
  → Not double-counted against the strategy
```

### Implementation
```python
# validation/decision.py → _compute_holdout_wfo_overlap()
# Automatically computed during evaluate_decision()
```

### When to Use
Always (computed automatically in the validation pipeline). When doing manual
evaluation (as in X36), check if your holdout period includes WFO windows
and note the correlation.

---

## 24. Pair Diagnostic

### Purpose
Automated comparison of two strategy equity paths. Classifies the relationship
(near-identical, borderline, distinct) without making a judgment.

### Method
- Tolerance-based equality: 1 bp and 10 bp per-bar thresholds
- Return correlation analysis
- Classification: `near_identical` (ρ > 0.97), `borderline`, `distinct`
- Suggests review route (no_action, inconclusive, escalate)
- **Zero decision authority** — diagnostic only

### Classification Thresholds
| Threshold | Value |
|-----------|-------|
| Near-identical (1bp match rate) | ≥ 95% |
| Near-identical (correlation) | ≥ 0.97 |
| Borderline (1bp match rate) | ≥ 80% |
| Borderline (correlation) | ≥ 0.90 |

### Implementation
```python
from research.lib.pair_diagnostic import run_pair_diagnostic
diag = run_pair_diagnostic(equity_a, equity_b, "StratA", "StratB")
# diag.classification → "near_identical" / "borderline" / "distinct"
```

### When to Use
When two strategies produce suspiciously similar equity curves — determines
whether they're genuinely different algorithms or cosmetic variants.

---

## 25. Churn Metrics (Detailed)

### Purpose
Comprehensive trade churn diagnostics beyond the basic Section 7 analysis.

### Metrics

| Metric | Formula | Warning Threshold |
|--------|---------|-------------------|
| Trades/month | `n_trades / months` | — |
| Entries/week | `n_entries / weeks` | — |
| Avg hold (bars) | `mean(exit_bar - entry_bar)` | — |
| Cascade ≤3 bars | `count(hold ≤ 3) / n_trades` | > 30% |
| Cascade ≤6 bars | `count(hold ≤ 6) / n_trades` | — |
| Fee drag (%) | `total_fees / gross_profit × 100` | > 20% |
| Exit reason distribution | Count per reason category | — |

### Implementation
```python
# validation/suites/churn_metrics.py → ChurnMetricsSuite
# Output: churn_metrics.csv
# Warns if fee_drag > 20% or cascade_leq3 > 30%
```

### When to Use
When a strategy has high trade count or short holding periods. Diagnoses
whether the strategy is capturing alpha or just generating churn.

---

## 26. Regression Guard

### Purpose
Compare current backtest against a "golden snapshot" — a previously validated
and promoted strategy's metrics. Detects regressions from code changes.

### Method
- Load YAML golden snapshot (canonical metrics for promoted strategy)
- Run current backtest with same parameters
- Compare deltas for: CAGR, MDD, trades, Sharpe, turnover, fees
- Flag regressions if delta exceeds ±5% relative change

### Implementation
```python
# validation/suites/regression_guard.py → RegressionGuardSuite
# Config: validation_config.regression_guard_path → YAML file
# Output: regression_guard.json
# Failure → ERROR (exit code 3)
```

### When to Use
After any code change to v10/ engine, strategy implementations, or data pipeline.
Ensures the promoted strategy's metrics haven't regressed.

---

# Part III — Decision & Reporting

## 27. Multi-Layer Verdict Framework

### How to Determine the Winner

**DO NOT use a single metric.** Evaluate across all 7 evidence layers:

| Layer | Metric | How to Rank |
|-------|--------|-------------|
| Full-sample | Sharpe (primary), CAGR, MDD | Highest Sharpe wins |
| PSR | PSR value | All ≥ 0.95 → pass; < 0.95 → flag |
| Holdout | Sharpe | Highest wins, but single-path caveat |
| WFO | Mean/Median Sharpe, positive count | Most stable wins |
| Cost sweep | Degradation slope, Sharpe at target cost | Relevant at your actual cost |
| Regime | Epoch Sharpes | Most consistent across epochs wins |
| **Bootstrap** | **Median Sharpe, P(Sh>0)** | **Highest authority** |

### Decision Rules

1. **Bootstrap agreement with full-sample**: Both rank same winner → strong consensus.
   Different ranking → full-sample winner has path-specific edge → bootstrap winner
   is the safer choice.

2. **Full-sample dominance with bootstrap weakness**: Strategy wins full-sample but
   has lower bootstrap P(Sh>0) → the edge exploits specific sequences that don't
   generalize. NOT recommended for forward deployment.

3. **WFO + regime consistency**: Strategy wins most WFO windows AND most epochs →
   temporally stable. Combine with bootstrap for final verdict.

4. **Cost-conditioned decisions**: If strategies swap ranking at different cost levels,
   the relevant comparison is at YOUR measured cost (e.g., 20 bps from X33).

5. **Simplicity tiebreaker**: When two strategies have statistically indistinguishable
   bootstrap performance, prefer the simpler one (fewer parameters, fewer mechanisms).
   Complexity without bootstrap-proven benefit is overfit.

### Reporting Template

For the CONCLUSIONS document, structure the verdict as:

```markdown
### Ranking by Evidence Layer

| Evidence Layer | Winner | Rationale |
|----------------|--------|-----------|
| Full-sample    | ...    | ...       |
| Bootstrap      | ...    | ...       |
| WFO            | ...    | ...       |
| Holdout        | ...    | ...       |
| Regime         | ...    | ...       |
| Cost           | ...    | ...       |
| Simplicity     | ...    | ...       |

### Final Verdict
[1-2 paragraph synthesis explaining which strategy wins and WHY,
grounded in multi-layer evidence. Explicitly address any rank reversals.]
```

---

## 28. Interpretation Guidelines

### Common Patterns and What They Mean

| Pattern | Likely Cause | Action |
|---------|-------------|--------|
| Full-sample > bootstrap | Path-specific edge | Prefer bootstrap winner |
| High win rate + low avg return | Time stop truncating winners | Check best trade vs competitor |
| Low win rate + high avg return | Trend-following signature | Normal; verify via bootstrap |
| Bootstrap P(Sh>0) < 90% | Weak or absent edge | REJECT strategy |
| Regime near-zero in recent epoch | Forward deployment risk | Flag prominently |
| Flat cost sensitivity slope | Few trades or large avg return | Desirable if returns are real |
| Steep cost sensitivity slope | Many trades or small avg return | Vulnerable to cost estimates |
| WFO positive but bootstrap weak | Over-adaptation to regime | Bootstrap is authority |
| Churn > 5 trades at ≤24h | Entry signal whipsawing | Consider cooldown or filter |

### Statistical Pitfalls to Avoid

1. **P(d>0) ≠ p-value**: Bootstrap P(Sharpe>0) is not a hypothesis test p-value.
   It's a probability estimate. Don't compare to 0.05.

2. **Underpowered ≠ noise**: If bootstrap CI is wide [-0.2, +1.4], the edge MAY exist
   but we can't confirm it. This is different from "edge doesn't exist."

3. **No single-gate veto**: Don't reject a strategy because ONE metric is slightly
   below threshold. Evaluate the full evidence stack.

4. **Economic evidence is independent**: A strategy's value at specific cost levels
   is a separate evidence layer from statistical significance.

5. **Holdout is ONE path**: Holdout Sharpe 2.0 vs 1.3 could easily reverse on a
   different 2-year window. Bootstrap is the proper robustness test.

---

## 29. Implementation Template

### File Structure

```
research/xNN/tmp/
├── README.md                  # Index with quick summary
├── METHODOLOGY.md             # This document (copy or reference)
├── run_comparison.py          # Main experiment runner
├── custom_strategies.py       # Strategy implementations under test
├── regen_report.py            # Report regenerator from saved data
├── results/
│   ├── CONCLUSIONS.md         # Full experimental conclusions
│   ├── comparison_report.md   # Formatted comparison tables
│   ├── full_sample_metrics.csv
│   ├── holdout_metrics.csv
│   ├── wfo_results.csv
│   ├── cost_sweep.csv
│   ├── regime_decomposition.csv
│   ├── trade_stats.csv
│   ├── bootstrap_summary.json
│   └── psr.json
└── figures/
    ├── equity_drawdown.png
    ├── bootstrap_distributions.png
    ├── wfo_sharpe.png
    ├── cost_sensitivity.png
    └── regime_decomposition.png
```

### Constants to Customize

```python
# ── Adapt these for each experiment ──────────────────────────
STRAT_NAMES = ["StratA", "StratB", "Baseline"]   # strategy display names
COLORS = {"StratA": "#e63946", "StratB": "#457b9d", "Baseline": "#2a9d8f"}

START = "2019-01-01"          # backtest start (after warmup)
END = "2026-02-20"            # backtest end
WARMUP = 365                  # warmup days
COST_RT_BPS = 20              # primary cost level

N_BOOT = 500                  # bootstrap paths (≥500 for stable medians)
BLKSZ = 60                    # VCBB block size (H4 bars; 10 days)
CTX = 90                      # VCBB context window
K_NN = 50                     # VCBB nearest neighbors
SEED = 1337                   # reproducibility

HOLDOUT_START = "2024-01-01"  # holdout period start
COST_LEVELS = [5, 10, 15, 20, 25, 30, 40, 50]

# WFO windows (12 × 6-month; adjust if date range changes)
WFO_WINDOWS = [...]

# Epochs (adjust to match dataset coverage and market regimes)
EPOCHS = [...]
```

### Execution

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate
PYTHONUNBUFFERED=1 python research/xNN/tmp/run_comparison.py
```

**Expected runtime**: ~25 minutes (bootstrap is 90%+ of runtime).
Sections 1-7 complete in ~2-3 minutes; bootstrap takes ~20 minutes for 500 paths × 3 strategies.

### Performance Tips

- Use `_fast_load_bars()` with `itertuples`, NOT `DataFeed` with `iterrows`
- Pre-load all bars once, construct sub-feeds by filtering
- Use `PYTHONUNBUFFERED=1` to see real-time progress
- Print progress every 50 bootstrap paths
- Save intermediate results (CSVs/JSONs) BEFORE charts/report → if chart code
  crashes, data is preserved

---

## 30. Checklist

### Part I — Core Evaluation (required)

- [ ] All strategies implement the same `Strategy` ABC
- [ ] Same data file, same date range, same warmup for all strategies
- [ ] Same cost configuration for all strategies (per section)
- [ ] Full-sample metrics table has all 10 metrics
- [ ] PSR computed and reported
- [ ] Holdout uses non-overlapping future data only
- [ ] WFO covers 12 windows with no gaps
- [ ] Cost sweep covers at least 5-50 bps range
- [ ] Regime decomposition covers all major market phases
- [ ] Trade stats include churn analysis
- [ ] Bootstrap uses ≥500 paths with VCBB (not uniform block bootstrap)
- [ ] Bootstrap summary includes P(Sharpe>0), median Sharpe, P5/P95
- [ ] Full-sample vs bootstrap rank reversal explicitly discussed
- [ ] All 5 charts generated and correctly labeled
- [ ] CONCLUSIONS.md has multi-layer verdict table
- [ ] All CSVs/JSONs saved for future re-analysis
- [ ] Code is self-contained and reproducible

### Part II — Advanced Techniques (recommended for formal validation)

- [ ] Lookahead detection passes (zero violations)
- [ ] Data integrity checks pass (no hard-fail triggers)
- [ ] Invariant checks pass (no portfolio/cost/P&L violations)
- [ ] DSR computed with honest N (number of strategies tested)
- [ ] Effective DOF reported if claiming cross-timescale results
- [ ] WFO Wilcoxon + Bootstrap CI computed (when comparing candidate vs baseline)
- [ ] Trade-level matched-pair bootstrap (when WFO is low-power)
- [ ] Subsampling confirms bootstrap direction (deterministic confirmation)
- [ ] Drawdown episodes listed and compared
- [ ] Sensitivity sweep shows parameter plateau (not sharp peak)
- [ ] Holdout/WFO overlap checked and noted
- [ ] Churn metrics reviewed (fee drag < 20%, cascade ≤3 < 30%)
- [ ] Regression guard passes (if golden snapshot exists)

---

## Appendix A: Formal Validation Pipeline (7 Gates)

When running the formal `validation/runner.py` (as opposed to the standalone
research comparison), the decision is computed by `validation/decision.py`
using this gate structure:

| Gate | Type | Threshold | Source |
|------|------|-----------|--------|
| `lookahead` | **hard** | 0 pytest failures | `validation/suites/lookahead.py` |
| `full_harsh_delta` | **hard** | ΔScore ≥ -0.2 @ harsh cost | `validation/suites/backtest.py` |
| `holdout_harsh_delta` | **hard** | ΔScore ≥ -0.2 @ holdout | `validation/suites/holdout.py` |
| `wfo_robustness` | soft | Wilcoxon p ≤ 0.10 OR Bootstrap CI > 0 | `validation/suites/wfo.py` |
| `trade_level_bootstrap` | soft | Conditional (low-power WFO) | `validation/suites/trade_level.py` |
| `selection_bias` (PSR) | soft | PSR ≥ 0.95 | `validation/suites/selection_bias.py` |
| `bootstrap` | info | Diagnostic only (no veto) | `validation/suites/bootstrap.py` |

**Exit codes**: 0=PROMOTE, 1=HOLD, 2=REJECT, 3=ERROR

**Invocation**:
```bash
python validate_strategy.py \
  --strategy NAME --baseline NAME \
  --config FILE --baseline-config FILE \
  --out DIR --suite {basic|full|all}
```

**Score function** (objective decomposition):
Weighted composite of CAGR, MDD, Sharpe, and Profit Factor at harsh cost.
Delta = candidate_score - baseline_score. See `validation/suites/backtest.py`.

---

## Appendix B: Reference Implementation

The canonical implementation is at:
```
/var/www/trading-bots/btc-spot-dev/research/x36/branches/a_vcbb_bias_study/run_comparison.py
```

This file is the authoritative reference for:
- Data loading and sub-feed construction
- BacktestEngine invocation pattern
- PSR computation
- Bootstrap path generation and Bar construction
- Chart generation code
- Report generation code

Copy and adapt for new experiments. The strategy-specific code is in
`v3v4_strategies.py` — replace with your own strategy implementations.

## Appendix C: Key Library References

| Library | Path | Purpose |
|---------|------|---------|
| VCBB | `research/lib/vcbb.py` | Vol-conditioned block bootstrap |
| DSR | `research/lib/dsr.py` | Deflated Sharpe Ratio, PSR |
| Effective DOF | `research/lib/effective_dof.py` | Nyholt/Li-Ji/Galwey M_eff |
| Pair Diagnostic | `research/lib/pair_diagnostic.py` | Equity path comparison |
| BacktestEngine | `v10/core/engine.py` | Event-driven backtest |
| Metrics | `v10/core/metrics.py` | compute_metrics() |
| Types | `v10/core/types.py` | Bar, CostConfig, Signal, etc. |
| Strategy ABC | `v10/strategies/base.py` | Strategy interface |
| DataFeed | `v10/core/data.py` | CSV loader (slow; use _fast_load_bars) |

## Appendix D: Validation Suite Inventory

| Suite | File | Gate Type |
|-------|------|-----------|
| Backtest | `validation/suites/backtest.py` | Hard (score delta) |
| WFO | `validation/suites/wfo.py` | Soft (Wilcoxon/CI) |
| Bootstrap | `validation/suites/bootstrap.py` | Info (diagnostic) |
| Holdout | `validation/suites/holdout.py` | Hard (score delta) |
| Selection Bias | `validation/suites/selection_bias.py` | Soft (PSR) |
| Trade Level | `validation/suites/trade_level.py` | Soft (conditional) |
| Regime | `validation/suites/regime.py` | — (diagnostic) |
| DD Episodes | `validation/suites/dd_episodes.py` | — (diagnostic) |
| Data Integrity | `validation/suites/data_integrity.py` | Hard (pre-check) |
| Invariants | `validation/suites/invariants.py` | Hard (logic check) |
| Cost Sweep | `validation/suites/cost_sweep.py` | — (diagnostic) |
| Sensitivity | `validation/suites/sensitivity.py` | — (diagnostic) |
| Regression Guard | `validation/suites/regression_guard.py` | Hard (regression) |
| Lookahead | `validation/suites/lookahead.py` | Hard (pytest) |
| Subsampling | `validation/suites/subsampling.py` | — (diagnostic) |
| Churn Metrics | `validation/suites/churn_metrics.py` | — (diagnostic) |
| Overlay | `validation/suites/overlay.py` | — (diagnostic) |
