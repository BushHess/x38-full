# Branch A: V4 macroHystB vs E5_ema21D1 — Fair Head-to-Head Comparison

**Status**: DONE
**Created**: 2026-03-17
**Deviation note**: This branch uses x36-style `branches/` layout (not x37's native
`sessions/sNN_*` pattern). Authorized by researcher for a focused comparison task.

---

## 1. Objective

Fair, apples-to-apples comparison of **V4_macroHystB** (`new_final_flow`) vs
**E5_ema21D1** through **identical validation techniques** at **standardized cost**
(20 bps RT, per V4 spec).

**Why this matters**: Previous comparisons were unfair — V4 was tested at 20 bps RT,
E5 at 50 bps RT ("harsh"). V4 reported Sharpe 1.839 vs E5 Sharpe 1.455 — but the
cost asymmetry inflates V4's apparent advantage. This branch eliminates that asymmetry
and applies the full validation suite (19 techniques) to both strategies identically.

**Non-goals**:
- NOT discovering new algorithms
- NOT modifying V4 or E5 logic
- NOT running the official `validate_strategy.py` pipeline (self-contained branch)
- NOT modifying any files outside this branch
- NOT proposing deployment decisions

---

## 2. Protocol Freeze

### 2.1 Cost Scenarios

**Primary** (V4 standard): 20 bps RT = 10 bps per side.

```python
from v10.core.types import CostConfig, SCENARIOS

COST_FAIR = CostConfig(spread_bps=4.0, slippage_bps=2.0, taker_fee_pct=0.06)
# per_side = 4/2 + 2 + 0.06*100 = 2+2+6 = 10 bps → RT = 20 bps

COST_HARSH = SCENARIOS["harsh"]  # RT = 50 bps (for reference only)
```

**Secondary** (for cost sweep): 10, 15, 20, 25, 30, 50, 100 bps RT.

### 2.2 Data

```
Files   : research/x37/data/data_btcusdt_4h.csv + data_btcusdt_1d.csv
          (combined at runtime into results/_combined_data.csv for DataFeed)
TF      : H4 + D1
Range   : 2017-08-17 → 2026-02-20
```

### 2.3 Period Split

| Period | Start | End | Purpose |
|--------|-------|-----|---------|
| Warmup context | 2017-08-17 | 2019-12-31 | Indicator warmup + V4 threshold calibration seed |
| Development | 2020-01-01 | 2023-12-31 | 4 years, primary backtest |
| Holdout | 2024-01-01 | 2026-02-20 | ~2 years, locked out-of-sample |
| Full | 2020-01-01 | 2026-02-20 | Dev + Holdout combined |

### 2.4 WFO Configuration

```
Mode            : rolling
Train           : 24 months
Test            : 6 months
Slide           : 6 months
Windows         : 8
Wilcoxon α      : 0.10 (one-sided, H_a: median Δ > 0)
Bootstrap CI α  : 0.05 (10,000 resamples, percentile method)
Low-power cutoff: 5 trades per window
```

**Window Schedule**:

| Win | Train Start | Train End | Test Start | Test End |
|-----|-------------|-----------|------------|----------|
| 0 | 2020-01-01 | 2021-12-31 | 2022-01-01 | 2022-06-30 |
| 1 | 2020-07-01 | 2022-06-30 | 2022-07-01 | 2022-12-31 |
| 2 | 2021-01-01 | 2022-12-31 | 2023-01-01 | 2023-06-30 |
| 3 | 2021-07-01 | 2023-06-30 | 2023-07-01 | 2023-12-31 |
| 4 | 2022-01-01 | 2023-12-31 | 2024-01-01 | 2024-06-30 |
| 5 | 2022-07-01 | 2024-06-30 | 2024-07-01 | 2024-12-31 |
| 6 | 2023-01-01 | 2024-12-31 | 2025-01-01 | 2025-06-30 |
| 7 | 2023-07-01 | 2025-06-30 | 2025-07-01 | 2025-12-31 |

### 2.5 Warmup Days

- **V4**: `warmup_days=3000` — ensures DataFeed loads from ~2017 for ALL WFO windows.
  V4 needs full history from 2019-01-01 for expanding threshold calibration.
  With 3000 days warmup, even the latest window (test 2025-07-01) loads from ~2017.
- **E5**: `warmup_days=365` — sufficient for EMA(120) convergence + VDO warmup.

For WFO fairness, both use their own required warmup (results identical regardless
of extra warmup bars — only the reporting window counts).

### 2.6 D1-H4 Alignment

**V4 uses exact-spec `<=` rule**: `d1_close_time <= h4_close_time`.
This reproduces `resource/gen1/v4_macroHystB` exactly.

**E5 uses strict `<` rule**: `d1_close_time < h4_close_time`.
This preserves the current strategy implementation used elsewhere in the repo.

### 2.7 Objective Score Formula

Same formula as validation pipeline, for gate comparability:

```python
def objective_score(summary: dict) -> float:
    cagr = summary["cagr_pct"]
    max_dd = summary["max_drawdown_mid_pct"]
    sharpe = summary["sharpe"]
    pf = min(summary["profit_factor"], 3.0)
    n_trades = summary["trades"]
    return (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0, sharpe)
        + 5.0 * max(0, pf - 1)
        + min(n_trades / 50, 1) * 5.0
    )
```

### 2.8 Baseline

**Primary comparison**: V4 vs E5 (head-to-head).
**WFO mode**: direct V4-vs-E5 head-to-head on the same windows.

---

## 3. V4 Strategy Specification

Source: `resource/gen1/v4_macroHystB/Spec2_System_Specification_new_final_flow.md`
Frozen params: `resource/gen1/v4_macroHystB/research/final_practical_system.json`

### 3.1 Features

| Feature | Formula | TF | Notes |
|---------|---------|-----|-------|
| `d1_ret_60` | `d1_close / d1_close.shift(60) - 1` | D1 | 60-day return |
| `h4_trendq_84` | `(h4_close/h4_close.shift(84) - 1) / (rolling_std(h4_logret_1, 84, ddof=1) * sqrt(84))` | H4 | Trend quality (risk-adjusted) |
| `h4_buyimb_12` | `2 * (rolling_sum(taker_buy_base_vol, 12) / rolling_sum(volume, 12)) - 1` | H4 | Buy imbalance [-1, +1] |

where `h4_logret_1 = log(h4_close / h4_close.shift(1))`.

**Critical**: `rolling_std` must use `ddof=1` (Bessel correction). No clipping/winsorization.

### 3.2 D1→H4 Feature Alignment

Map D1 features to H4 bars: for each H4 bar at index `i`, find the most recent
D1 bar whose `close_time <= h4_bars[i].close_time` (exact-spec `<=`).

```python
# In on_init():
d1_idx = 0
for i in range(n_h4):
    h4_ct = h4_bars[i].close_time
    while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] <= h4_ct:
        d1_idx += 1
    if d1_close_times[d1_idx] <= h4_ct:
        h4_d1_ret_60[i] = d1_ret_60_arr[d1_idx]
    # else: NaN (no completed D1 bar yet)
```

### 3.3 Yearly Threshold Calibration

For each year `Y` with bars in the loaded data range:

```python
# Expanding window: all H4 bars where open_time in [2019-01-01, Y-01-01)
# (computed on the H4 merged frame, so D1 features appear repeated)

macro_thr[Y]  = quantile(expanding_d1_ret_60,      0.50)   # expanding
entry_thr[Y]  = quantile(expanding_h4_trendq_84,   0.60)   # expanding
hold_thr[Y]   = quantile(expanding_h4_trendq_84,   0.50)   # expanding
flow_thr[Y]   = quantile(trailing_365d_h4_buyimb_12, 0.55) # trailing 365 days
```

**Trailing 365d**: bars where `open_time in [(Y-01-01 - 365 days), Y-01-01)`.

**CRITICAL**: Quantiles computed on the **H4 merged frame** — D1 features are
broadcast to all H4 bars in each D1 period. Use pandas-default quantile
interpolation (linear). This matches V4 spec exactly.

### 3.4 Frozen Yearly Thresholds (Acceptance Test Targets)

| Year | macro_q50 | entry_q60 | hold_q50 | flow_q55 |
|------|-----------|-----------|----------|----------|
| 2020 | 0.01733118 | 0.44456083 | 0.18495011 | 0.03494195 |
| 2021 | 0.11701675 | 0.59767632 | 0.37280954 | -0.02210511 |
| 2022 | 0.16551381 | 0.53271889 | 0.27334110 | -0.01170659 |
| 2023 | 0.02476320 | 0.39796868 | 0.12118843 | -0.00430096 |
| 2024 | 0.07826335 | 0.41624702 | 0.15029781 | -0.01361452 |
| 2025 | 0.07915294 | 0.43110899 | 0.15856132 | -0.00484446 |
| 2026 | 0.06139221 | 0.39132836 | 0.12691468 | -0.03080399 |

Acceptance target: exact threshold recovery under `allow_exact_matches=true`.

### 3.5 State Machine

```
State: {FLAT, LONG}

At each H4 bar close (bar index i):
  year = utc_year(bar.open_time)

  # Feature checks (NaN → False)
  macro_on = (h4_d1_ret_60[i] is not NaN) and (h4_d1_ret_60[i] > macro_thr[year])
  entry_on = (h4_trendq_84[i] is not NaN) and (h4_trendq_84[i] > entry_thr[year])
  flow_on  = (h4_buyimb_12[i] is not NaN) and (h4_buyimb_12[i] > flow_thr[year])
  hold_on  = (h4_trendq_84[i] is not NaN) and (h4_trendq_84[i] > hold_thr[year])

  if state == FLAT:
      if macro_on AND entry_on AND flow_on:
          → LONG (Signal target_exposure=1.0)
  elif state == LONG:
      if NOT hold_on:
          → FLAT (Signal target_exposure=0.0)

  # D1 macro deliberately NOT used as exit (ablation-proven)
  # No-trade before 2020-01-01 (warmup)
```

### 3.6 Config Dataclass

```python
@dataclass
class V4MacroHystBConfig:
    # Feature lookbacks
    d1_ret_lookback: int = 60
    h4_trend_lookback: int = 84
    h4_buyimb_lookback: int = 12

    # Quantile levels
    macro_quantile: float = 0.50
    entry_quantile: float = 0.60
    hold_quantile: float = 0.50
    flow_quantile: float = 0.55

    # Calibration modes
    flow_mode: str = "trailing_365"   # "expanding" or "trailing_365"
    calibration_start: str = "2019-01-01"  # expanding window anchor

    # Trade start (no trades before this date)
    trade_start: str = "2020-01-01"
```

**Parameter count**: ~10 (3 lookbacks + 4 quantile levels + 2 modes + 1 anchor).
Compare E5: 4 tunable params.

### 3.7 Frozen Spec Performance (V4, at 20 bps RT)

| Period | Sharpe | CAGR | MDD | Trades |
|--------|--------|------|-----|--------|
| Dev 2020-2023 | 1.8338 | 73.4% | 22.7% | 35 |
| Holdout 2024-2026 | 1.8359 | 53.2% | 11.3% | 16 |
| Full 2020-2026 | 1.8395 | 67.1% | 22.7% | 51 |

### 3.8 Trade Distribution (acceptance targets)

| Metric | Value |
|--------|-------|
| Trades | 51 |
| Win rate | 58.8% |
| Avg net return | 7.51% |
| Median net return | 0.36% |
| Avg hold days | 11.0 |
| Top 5 trades sum | 2.598 |
| Bottom 5 trades sum | -0.304 |

---

## 4. E5 Strategy Reference

Source: `strategies/vtrend_e5_ema21_d1/strategy.py` (import directly, no rebuild).

### 4.1 Parameters

```python
from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Strategy, VTrendE5Ema21D1Config
)

config = VTrendE5Ema21D1Config(
    slow_period=120.0,
    trail_mult=3.0,
    vdo_threshold=0.0,
    d1_ema_period=21,
)
```

### 4.2 Known E5 Performance at Various Costs

From X22 cost sensitivity study (reference, not acceptance targets):

| Cost (RT bps) | Sharpe | CAGR | Trades |
|---------------|--------|------|--------|
| 15 | ~1.670 | ~75% | ~188 |
| 20 | ~1.60 | ~70% | ~188 |
| 50 (harsh) | 1.455 | 61.6% | 188 |

E5 trade count is cost-insensitive (signals don't depend on cost).

---

## 5. Implementation Phases

### Phase 1: V4 Strategy Rebuild

**Deliverable**: `code/v4_strategy.py` (~250 lines)

Implement `V4MacroHystBStrategy(Strategy)`:

1. `__init__(config)` — store config, init state to FLAT
2. `on_init(h4_bars, d1_bars)`:
   - Extract numpy arrays: close, high, low, volume, taker_buy from h4_bars
   - Extract close, close_time from d1_bars
   - Compute `d1_ret_60` array from D1 close prices
   - Compute `h4_logret_1` and `h4_trendq_84` array (with `ddof=1`)
   - Compute `h4_buyimb_12` array from taker_buy and volume
   - Build D1→H4 alignment map (strict `<` on close_time)
   - Create `h4_d1_ret_60` mapped array
   - Determine available years from data
   - Compute yearly thresholds using expanding/trailing quantiles
   - Store all arrays and threshold dict
3. `on_bar(state)`:
   - Lookup features at `state.bar_index`
   - Convert `state.bar.open_time` (epoch ms) to UTC year
   - Lookup thresholds for year (fall back to most recent if year not calibrated)
   - Evaluate state machine
   - Return Signal or None
4. `on_after_fill(state, fill)` — no-op
5. `name()` → `"v4_macro_hystb"`

**Key implementation details**:

```python
# Year extraction from epoch ms
import datetime as dt
year = dt.datetime.fromtimestamp(state.bar.open_time / 1000, tz=dt.timezone.utc).year

# Feature: h4_trendq_84
ret_84 = close[i] / close[i - 84] - 1
logret = np.log(close[1:] / close[:-1])  # h4_logret_1
# rolling std with ddof=1 over 84 bars
std_84 = rolling_std(logret, 84, ddof=1)  # need custom or numpy impl
trendq = ret_84 / (std_84 * np.sqrt(84))

# Feature: h4_buyimb_12
buyimb = 2 * (rolling_sum(taker_buy, 12) / rolling_sum(volume, 12)) - 1

# Threshold calibration: expanding quantile
# bars where open_time in [calibration_start_ms, year_start_ms)
mask = (open_times >= cal_start_ms) & (open_times < year_start_ms)
macro_thr = np.nanquantile(h4_d1_ret_60[mask], 0.50)
```

### Phase 2: Acceptance Test

**Deliverable**: `code/run_rebuild_acceptance.py`
**Output**: `results/acceptance_test.json`

Run V4 on full data at 20 bps RT. Compare against spec:

| Check | Target | Tolerance |
|-------|--------|-----------|
| Trade count | 51 | ±3 (alignment change) |
| Full Sharpe | 1.8395 | ±0.10 |
| Full CAGR | 67.1% | ±5% |
| Full MDD | 22.7% | ±3% |
| Win rate | 58.8% | ±5% |
| Yearly thresholds | Frozen table §3.4 | |delta| < 0.01 |

**If acceptance test fails** (trade count diff > 3):
1. Implement V4 with BOTH alignment rules (`<` and `<=`)
2. Compare outputs, document exact signal differences
3. Proceed with strict `<` for the fair comparison
4. Note the alignment delta in the final report

### Phase 3: Full Validation Suite

**Deliverables**: `code/run_full_validation.py` + `code/helpers.py`
**Outputs**: 20+ files in `results/`

Implement and run these validation techniques for **both** V4 and E5:

#### 3a. Full Backtest

Run both strategies on dev/holdout/full periods at 20 bps RT.
Also run at 50 bps RT for reference.

**Output**: `results/v4_backtest.json`, `results/e5_backtest.json`

Fields per period: sharpe, cagr_pct, max_drawdown_mid_pct, trades, profit_factor,
avg_trade_return, exposure, objective_score.

#### 3b. WFO Robustness (8 windows)

For each of 8 windows × each strategy:
1. Create DataFeed(path, start=test_start, end=test_end, warmup_days=warmup)
2. Create fresh strategy instance
3. Create BacktestEngine(feed, strategy, cost=COST_FAIR, initial_cash=10000)
4. Run engine → summary
5. Also run BuyAndHold for same window → summary
6. Compute score delta: strategy_score - buyandhold_score

Aggregate:
- Wilcoxon signed-rank test (one-sided, n=8 deltas)
- Bootstrap CI (percentile, 10,000 resamples) on mean delta

**Output**: `results/v4_wfo_results.csv`, `results/e5_wfo_results.csv`,
`results/wfo_summary.json`

**BuyAndHold implementation**: simple strategy that enters on first bar and holds.
Import from `v10/strategies/` if available, or implement inline (~20 lines).

#### 3c. Holdout Evaluation

Both strategies on locked holdout (2024-01-01 → 2026-02-20) at 20 bps.
Compare score vs BuyAndHold.

**Output**: `results/v4_holdout.json`, `results/e5_holdout.json`

#### 3d. Paired Bootstrap (V4 vs E5)

Paired block bootstrap on daily returns (V4 - E5) over dev/holdout/full.
Block sizes: 10, 20, 40 days. Resamples: 2,000.
Report: P(V4 > E5), median delta Sharpe, 95% CI of delta.

**Output**: `results/paired_bootstrap.csv`

#### 3e. Trade-Level Analysis

Export full trade lists for both. Compute:
- Distribution: count, win_rate, avg/median return, avg/median hold_days
- Tail concentration: top 5 / bottom 5 trade sum
- Matched trade comparison (if overlapping signals)

**Output**: `results/v4_trades.csv`, `results/e5_trades.csv`,
`results/trade_comparison.json`

#### 3f. Cost Sweep

Both strategies × 7 cost levels (10, 15, 20, 25, 30, 50, 100 bps RT) on full period.

```python
COST_SWEEP = [
    CostConfig(spread_bps=0, slippage_bps=0, taker_fee_pct=c/200)
    for c in [10, 15, 20, 25, 30, 50, 100]
]
```

Report: Sharpe, CAGR, MDD, trades for each combo.
Find **crossover cost**: at which cost does V4 start losing to E5 (or vice versa)?

**Output**: `results/cost_sweep.csv`

#### 3g. Regime Decomposition

Classify each bar into regime (using D1 EMA(200) trend + volatility percentile):
- TREND_UP, TREND_DOWN, CHOP, HIGH_VOL

Report strategy performance per regime.

**Output**: `results/regime_decomposition.csv`

#### 3h. Sensitivity / Plateau Test

**V4**: Perturb quantile levels ±0.05 and lookbacks ±10%.
Grid: macro_q × entry_q × hold_q (3×3×3 = 27 combos minimum).

**E5**: Perturb slow_period (90/120/150) × trail_mult (2.5/3.0/3.5) ×
d1_ema_period (15/21/30) = 27 combos.

Report: Sharpe spread (max-min across grid). Wider = more robust.

**Output**: `results/v4_sensitivity.csv`, `results/e5_sensitivity.csv`

#### 3i. Selection Bias (PSR)

Probabilistic Sharpe Ratio for both strategies (using `research/lib/dsr.py`).

**Output**: `results/selection_bias.json`

#### 3j. DD Episodes

Drawdown episode analysis: timing, depth, duration, recovery for both.

**Output**: `results/dd_episodes.csv`

#### 3k. Yearly + Monthly Metrics

Year-by-year (2020-2026) and month-by-month (2024-01 to 2026-02) metrics.

**Output**: `results/yearly_comparison.csv`, `results/monthly_comparison.csv`

#### 3l. Lookahead Verification

For V4: verify that on_bar(state) at bar_index `i` only accesses:
- `h4_bars[j]` for `j <= i` (precomputed arrays OK if built from all bars in on_init)
- D1 features only from completed D1 bars

This is inherently satisfied by the precompute-in-on_init pattern (same as E5).
Document in results.

**Output**: `results/lookahead_check.json`

### Phase 4: Fair Comparison & Verdict

**Deliverable**: `code/run_comparison_report.py`
**Outputs**: `results/comparison_report.md`, `results/verdict.json`

Generate structured comparison:

1. **Summary Table**: all metrics side-by-side (dev/holdout/full × 20bps + 50bps)
2. **Gate-by-Gate**: which strategy passes each of the 7 validation gates
3. **WFO Head-to-Head**: V4 vs E5 per window (who wins more?)
4. **Trade Quality**: distribution comparison
5. **Robustness**: plateau spread, regime consistency
6. **Cost Sensitivity**: crossover analysis
7. **Complexity**: parameter count, recalibration requirements
8. **Verdict**: structured conclusion

**Verdict Categories**:

| Verdict | Criteria |
|---------|----------|
| `V4_SUPERIOR` | V4 wins Sharpe + MDD + WFO + paired bootstrap P>0.75 |
| `E5_SUPERIOR` | E5 wins on all major metrics at 20 bps |
| `V4_COMPETITIVE` | V4 better on some metrics but not strictly dominant |
| `E5_COMPETITIVE` | E5 better on some metrics but not strictly dominant |
| `TRADEOFF` | Each wins on different metrics (e.g., V4 MDD vs E5 CAGR) |
| `INCONCLUSIVE` | Differences within statistical noise |

---

## 6. Files to Create

### Strategy Implementation

```
code/v4_strategy.py               # V4MacroHystBStrategy + V4MacroHystBConfig
                                   # ~250 lines
```

### Runner Scripts

```
code/run_rebuild_acceptance.py     # Phase 2: V4 rebuild + acceptance test
                                   # ~150 lines

code/run_full_validation.py        # Phase 3: all validation techniques
                                   # ~600 lines (main orchestrator)

code/run_comparison_report.py      # Phase 4: comparison analysis + verdict
                                   # ~300 lines
```

### Helper Module

```
code/helpers.py                    # WFO engine, bootstrap, metrics, regime, I/O
                                   # ~500 lines
```

Key functions in helpers.py:
```python
# Data
def load_data_feed(start, end, warmup_days) -> DataFeed

# Backtest
def run_backtest(strategy_factory, feed, cost) -> BacktestResult
def compute_metrics(result) -> dict
def objective_score(summary) -> float

# WFO
def run_wfo_head_to_head() -> dict
def wilcoxon_signed_rank(deltas) -> tuple[float, float]  # W+, p-value
def bootstrap_ci(deltas, n_boot=10000, alpha=0.05) -> tuple[float, float]

# Paired comparison
def paired_block_bootstrap(daily_ret_a, daily_ret_b, blocks, n_boot) -> dict
def compute_sharpe_from_returns(daily_returns) -> float

# Trade analysis
def trade_distribution(trades) -> dict
def matched_trade_analysis(trades_a, trades_b) -> dict

# Regime
def classify_regime(d1_bars) -> np.ndarray
def regime_decomposition(result, regime_labels) -> dict

# I/O
def save_json(path, data) -> None
def save_csv(path, rows, headers) -> None
```

### Expected Output Files

```
results/
├── acceptance_test.json             # V4 rebuild verification
├── v4_backtest.json                 # V4 full backtest (20 + 50 bps)
├── e5_backtest.json                 # E5 full backtest (20 + 50 bps)
├── v4_wfo_results.csv               # V4 WFO 8 windows
├── e5_wfo_results.csv               # E5 WFO 8 windows
├── wfo_summary.json                 # WFO stats for both + head-to-head
├── v4_holdout.json                  # V4 holdout evaluation
├── e5_holdout.json                  # E5 holdout evaluation
├── paired_bootstrap.csv             # V4 vs E5 paired bootstrap
├── v4_trades.csv                    # V4 trade list
├── e5_trades.csv                    # E5 trade list
├── trade_comparison.json            # Trade quality side-by-side
├── cost_sweep.csv                   # Both × 7 costs
├── regime_decomposition.csv         # Both × regime breakdown
├── v4_sensitivity.csv               # V4 parameter plateau
├── e5_sensitivity.csv               # E5 parameter plateau
├── selection_bias.json              # PSR for both
├── dd_episodes.csv                  # Drawdown episodes
├── yearly_comparison.csv            # Year-by-year metrics
├── monthly_comparison.csv           # Month-by-month 2024-2026
├── lookahead_check.json             # Lookahead verification
├── comparison_report.md             # Final analysis narrative
└── verdict.json                     # Structured verdict
```

---

## 7. Import Pattern

```python
import sys
from pathlib import Path

# Insert repo root for v10 imports
ROOT = Path(__file__).resolve().parents[4]  # btc-spot-dev/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# v10 engine
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import CostConfig, SCENARIOS, Bar, MarketState, Signal
from v10.strategies.base import Strategy

# E5 strategy (read-only import)
from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Strategy, VTrendE5Ema21D1Config
)

# Research libs (read-only)
from research.lib.dsr import deflated_sharpe_ratio  # if needed

# Branch-local
from code.v4_strategy import V4MacroHystBStrategy, V4MacroHystBConfig
from code.helpers import (
    load_data_feed, run_backtest, paired_block_bootstrap, ...
)
```

---

## 8. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| D1-H4 alignment `<` vs `<=` | Wrong alignment breaks V4 rebuild fidelity | Implement both modes; acceptance must match archived trade path exactly |
| V4 warmup in late WFO windows | Threshold calibration needs 2017-2019 data | warmup_days=3000 ensures full history |
| V4 low trade count (51 at 20bps) | WFO windows may have 2-3 trades → low power | Mark low-power windows; report both powered and all |
| V4 narrow plateau | Sensitivity test reveals fragility | Include plateau comparison; document honestly |
| taker_buy_base_vol availability | VDO and buyimb fail without taker data | DataFeed loads taker data; verify in Phase 1 |
| WFO direct comparison underpowered | V4 windows often have 1-4 trades | Report valid vs power-only windows separately and avoid overclaiming significance |
| E5 trade count at 20 bps | Should match 50 bps (188) since signals cost-independent | Verify in Phase 3; document any difference |

---

## 9. Execution Checklist

- [ ] **Phase 1**: Implement V4MacroHystBStrategy in `code/v4_strategy.py`
- [ ] **Phase 2**: Run acceptance test (`code/run_rebuild_acceptance.py`)
  - [ ] Verify trade count within tolerance
  - [ ] Verify yearly thresholds within tolerance
  - [ ] Verify Sharpe/CAGR/MDD within tolerance
  - [ ] Verify archived trade path matches exactly
  - [ ] If fails: inspect alignment mode before trusting any comparison
- [ ] **Phase 3**: Run full validation suite (`code/run_full_validation.py`)
  - [ ] Full backtest (both × 2 costs × 3 periods)
  - [ ] WFO head-to-head (V4 vs E5 × 8 windows)
  - [ ] Holdout evaluation (both)
  - [ ] Paired bootstrap (V4 vs E5, 3 block sizes)
  - [ ] Trade-level analysis (both)
  - [ ] Cost sweep (both × 7 costs)
  - [ ] Regime decomposition (both)
  - [ ] Sensitivity/plateau (both × 27 combos)
  - [ ] Selection-bias advisory (DSR on H4 returns)
  - [ ] DD episodes (both)
  - [ ] Yearly + monthly metrics
  - [ ] Lookahead verification (V4)
- [ ] **Phase 4**: Generate comparison report (`code/run_comparison_report.py`)
  - [ ] Summary table
  - [ ] Gate-by-gate comparison
  - [ ] Verdict with confidence

---

## 10. Read-Only Dependencies

```
data/bars_btcusdt_2016_now_h1_4h_1d.csv           # Market data
strategies/vtrend_e5_ema21_d1/strategy.py          # E5 implementation
v10/core/engine.py                                 # BacktestEngine
v10/core/types.py                                  # Bar, Signal, CostConfig, etc.
v10/core/data.py                                   # DataFeed
v10/core/metrics.py                                # compute_metrics()
v10/strategies/base.py                             # Strategy ABC
research/lib/dsr.py                                # Deflated Sharpe Ratio
research/x37/resource/gen1/v4_macroHystB/               # V4 spec + frozen artifacts
```

**NOT reading** (per x37 rules §17): `validation/`, `results/full_eval_*`,
`research/x0/` .. `research/x36/`.

---

## 11. Pre-existing Knowledge Summary

Key facts informing expectations (from prior research, NOT used for tuning):

- E5 at 15 bps: Sh ~1.670, CAGR ~75%. E5 at 50 bps: Sh 1.455, CAGR 61.6%.
- V4 at 20 bps: Sh 1.839, CAGR 67.1%, MDD 22.7% (per spec, pre-alignment change).
- E5 has 188 trades (cost-insensitive); V4 has 51 trades (much fewer).
- E5 plateau spread: 0.017 (very wide). V4 plateau: ±30% swing (narrow).
- E5 WFO at 50 bps: p=0.125 (FAIL). V4 has NO prior WFO test — this is the key unknown.
- V4 has ~8 effective parameters with yearly recalibration; E5 has 4 fixed parameters.
- Cross-timescale ρ=0.92 for E5 family — diversification ceiling +3.5%.
- X22 finding: churn filters (like V4's flow gate) HURT below ~30 bps RT.
  V4's flow gate at 20 bps might reduce trades without net benefit.

**The central question**: Does V4's higher apparent Sharpe (1.84 vs ~1.60 at 20 bps)
survive WFO robustness testing, or is it an artifact of narrow plateau + low trade count
+ yearly recalibration overfitting?
