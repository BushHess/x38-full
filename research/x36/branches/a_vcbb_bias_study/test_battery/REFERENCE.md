# VCBB Bias & Strategy Comparison — Complete Reference

**Created**: 2026-03-16
**Purpose**: Reusable evaluation framework for testing whether a bootstrap method
biases strategy comparisons, and for understanding *why* one strategy beats another.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Test Catalog](#2-test-catalog)
3. [Methodology](#3-methodology)
4. [Technical Specifications](#4-technical-specifications)
5. [Results Summary](#5-results-summary)
6. [Reproduction](#6-reproduction)
7. [Reuse Guide](#7-reuse-guide)
8. [File Inventory](#8-file-inventory)

---

## 1. Problem Statement

**Claim under test**: "VCBB bootstrap unfairly penalizes strategy V3 by destroying
regime structure that V3's time_stop and cooldown mechanisms exploit."

**Context**: V3 (time_stop=30 bars, cooldown=6) has lower bootstrap Sharpe than
E5+EMA21D1 (no time_stop, no cooldown). An analyst argued this gap is a VCBB artifact,
not a real performance difference.

**Resolution approach**: 6 empirical tests, each targeting a specific causal mechanism.
Tests 1-3 use aggregate statistics. Tests 4-6 use granular path-level and trade-level
data for strictly more powerful analysis.

---

## 2. Test Catalog

### Aggregate Tests (Tests 1-3)

| # | Name | Question | Method | Runtime |
|---|------|----------|--------|---------|
| 1 | Block-Size Sensitivity | Does ranking change with blksz? | VCBB at 5 block sizes × 3 strategies × 500 paths | ~120 min |
| 2 | Regime-Conditioned Bootstrap | Does V3 gain more from regime conditioning? | Novel regime-conditioned bootstrap vs VCBB control | ~40 min |
| 3 | Time-Stop/Cooldown Ablation | Do V3's mechanisms improve E5? | E5 + V3 mechanisms in isolation and combination | ~40 min |

### Granular Tests (Tests 4-6)

| # | Name | Question | Method | Runtime |
|---|------|----------|--------|---------|
| 4 | Paired Path Delta + Wilcoxon | Is E5>V3 statistically significant? | Same-path paired δ at blksz=60 and 360, Wilcoxon signed-rank | ~30 min |
| 5 | δ vs Regime Quality Correlation | Does regime quality help V3? | Spearman/Pearson correlation, tercile decomposition | <1 sec (uses Test 4 data) |
| 6 | Trade-Duration P&L Decomposition | What does V3's time_stop truncate? | Real-data trade analysis by duration bucket | <1 min |

---

## 3. Methodology

### 3.1 Test 1: Block-Size Sensitivity

**Logic**: If VCBB regime destruction biases against V3, then increasing block size
(which preserves more regime structure) should disproportionately improve V3.
The diagnostic is V3/E5 median Sharpe ratio across block sizes.

**Decision rules**:
- Ratio spread < 0.05 → STABLE (no bias)
- Ratio monotonically increasing AND spread ≥ 0.05 → VCBB biases against V3
- Non-monotonic → complex/no clear bias

**Parameters**: blksz ∈ {30, 60, 120, 180, 360}, CTX=90, K=50, 500 paths each.

### 3.2 Test 2: Regime-Conditioned Bootstrap

**Logic**: A novel bootstrap that conditions on regime labels (bull/bear from
D1 EMA(21)). Source blocks are drawn from same-regime segments. If V3 gains more
from regime conditioning than E5 → VCBB regime destruction hurts V3 more.

**Method**:
1. Compute D1 EMA(21) regime labels → map to H4 bars → identify contiguous segments
2. For each segment in original sequence, draw replacement data from random segment
   of SAME regime type (bull→bull, bear→bear)
3. Conditions on: source regime type (bull→bull, bear→bear)
4. Randomizes: which specific within-regime realization is used

**Important caveat**: This method conditions the *source* block regime, but the
*realized* regime on synthetic paths is path-dependent (EMA accumulates over history).
Empirical regime match rate is ~38%, below random baseline ~50%. The method is still
valid as a differential test (both strategies see the same paths) but should be called
"regime-conditioned" not "regime-preserving".

**Decision rules**:
- Differential (V3 gain − E5 gain) > +0.03 → V3 helped more (regime effect)
- Differential < -0.03 → E5 helped more (no V3-specific regime effect)
- |Differential| ≤ 0.03 → no differential effect

### 3.3 Test 3: Time-Stop/Cooldown Ablation

**Logic**: Isolate V3's two distinctive mechanisms by adding them to E5.
If E5+mechanisms > E5_base in bootstrap → mechanisms are valuable.
If E5+mechanisms < E5_base → mechanisms hurt robustness.

**Variants tested**:
- E5_base: unmodified E5+EMA21D1
- E5+TS30: E5 + time_stop=30 bars
- E5+CD6: E5 + cooldown=6 bars
- E5+TS30+CD6: E5 + both
- V3: reference

**Implementation**: `E5Ablation(VTrendE5Ema21D1Strategy)` subclass. Inherits all E5
indicators and entry/exit logic. Adds optional gates:
- Time stop: if bars_since_entry ≥ time_stop_bars → force exit
- Cooldown: if bars_since_last_exit ≤ cooldown_bars → suppress entry

**Components**: full-sample backtest + 500 VCBB paths (blksz=60) + 4-epoch regime
decomposition (Pre-2021, 2021-2022, 2023-2024, 2025+).

### 3.4 Test 4: Paired Path Delta + Wilcoxon

**Logic**: Tests 1-3 compare medians across strategies. But since both strategies
run on the SAME bootstrap path, we can compute paired δ_i = Sharpe(V3) − Sharpe(E5)
for each path. Paired statistics are strictly more powerful.

**Method**:
1. Generate 500 VCBB paths at blksz=60 and blksz=360
2. For each path, run both V3 and E5 → get Sharpe pair
3. Compute δ_i per path
4. Wilcoxon signed-rank test on δ (two-sided)
5. Report: δ median, P(V3>E5), Wilcoxon p-value, δ distribution

**Decision rules**:
- Wilcoxon p < 0.05 → statistically significant difference
- P(V3>E5) at blksz=360 > P(V3>E5) at blksz=60 by >5pp → regime preservation helps V3
- Otherwise → no regime effect

### 3.5 Test 5: δ vs Regime Quality Correlation

**Logic**: The most direct test of the "VCBB destroys regimes V3 needs" hypothesis.
For each bootstrap path, measure "regime quality" (how clean/long the regimes are).
If the hypothesis is correct, δ should correlate positively with regime quality.

**Regime quality metric**: Average contiguous same-regime segment length (D1 bars).
Computed from synthetic H4 close prices:
1. Aggregate to D1 (every 6 H4 bars)
2. Compute D1 EMA(21)
3. Label regime (close > EMA = bull)
4. Count contiguous segments → average length

**Statistics**:
- Spearman rank correlation (non-parametric, robust to outliers)
- Pearson correlation (for comparison)
- Tercile decomposition: split paths into Low/Mid/High regime quality, compare δ medians

**Decision rules**:
- ρ > +0.1, p < 0.05 → regime quality helps V3 (supports analyst)
- ρ < -0.1, p < 0.05 → regime quality hurts V3 (contradicts analyst)
- |ρ| < 0.1 → no relationship

### 3.6 Test 6: Trade-Duration P&L Decomposition

**Logic**: On real data (no bootstrap), show exactly where each strategy's P&L comes
from. If V3's time_stop truncates profitable fat-tail trades, this directly quantifies
the cost.

**Method**:
1. Run E5 and V3 on full 2019-2026 real data
2. For each trade: compute bars_held = days_held × 6 (H4 bars)
3. Bucket trades: ≤10, 11-30, 31-60, 61-120, >120 bars
4. Per bucket: count, P&L contribution %, avg return, max return, win rate
5. Truncation analysis: E5 trades > 30 bars → P&L exposure + actual ablation via E5+TS30

**Key metrics**:
- "P&L exposure (upper bound)" = total P&L from E5 trades > 30 bars, as % of total.
  If >> 100% → short trades are net losers, all profit from fat tails.
- "Actual ablation loss" = run E5 with time_stop=30 (E5+TS30) vs baseline E5.
  Captures partial profit from time-stopped trades + re-entry effects.
  Always ≤ upper bound because time_stop captures partial profit before exit.

---

## 4. Technical Specifications

### 4.1 Common Parameters

```
Data:       bars_btcusdt_2016_now_h1_4h_1d.csv (2017-08 → 2026-02)
Period:     2019-01-01 to 2026-02-20 (with 365-day warmup)
Cost:       20 bps round-trip
Bootstrap:  VCBB (Volatility-Conditioned Block Bootstrap)
VCBB:       blksz=60, CTX=90, K_NN=50 (default)
Paths:      500 per configuration
Seed:       42
Engine:     BacktestEngine, warmup_mode="no_trade", initial_cash=10,000
```

### 4.2 VCBB Bootstrap

The VCBB conditions next-block selection on realized volatility via KNN lookup:
- Preserves: volatility clustering across block boundaries
- Destroys: directional regime persistence > block_size (e.g., 10 days at blksz=60)
- Library: `research/lib/vcbb.py`
- Key functions: `make_ratios()`, `precompute_vcbb()`, `gen_path_vcbb()`
- Synthetic feed timestamps: aligned to source bars via `base_ts=boot_h4[0].open_time`,
  so `report_start_ms` matches the intended evaluation period (not hardcoded BASE_TS).

### 4.3 Regime-Conditioned Bootstrap (Novel, Test 2)

Implemented in `run_tests.py::_gen_regime_path_idx()`:
1. Label each H4 bar as bull/bear using D1 EMA(21)
2. Find contiguous segments: list of (start, length, is_bull)
3. For each original segment, fill with random same-regime donor blocks
4. Build synthetic path using `_build_path_5ch()` from VCBB library

**Limitation**: Source-regime conditioning does NOT guarantee realized-regime
preservation on synthetic paths. EMA is path-dependent — the accumulated history
means a "bull source block" may compute as bear on the synthetic path. Empirical
match rate ~38% (below random ~50%). Valid as differential test but not a true
regime-preserving bootstrap.

### 4.4 E5Ablation Strategy (Test 3)

Implemented in `run_tests.py::E5Ablation(VTrendE5Ema21D1Strategy)`:
- Inherits ALL E5 indicator computation and entry/exit logic
- Adds optional `time_stop_bars` and `cooldown_bars` gates
- Time stop: force exit if position held ≥ N bars
- Cooldown: suppress entry if last exit was ≤ N bars ago
- Tracks `_entry_fill_bar` and `_last_exit_bar` via `on_after_fill()`

### 4.5 Regime Quality Metric (Test 5)

Implemented in `run_deep_tests.py::_regime_quality()`:
- Input: H4 close price array from synthetic path
- Aggregate to D1: take last close of every 6 H4 bars
- Compute EMA(21) on D1 closes
- Label: close > EMA = bull
- Count contiguous same-regime segments
- Return: len(regime_array) / num_segments (avg segment length in D1 bars)

### 4.6 Statistical Tests Used

| Test | Purpose | Implementation |
|------|---------|----------------|
| Wilcoxon signed-rank | Paired non-parametric test for δ ≠ 0 | `scipy.stats.wilcoxon(delta, alternative='two-sided')` |
| Spearman rank correlation | Non-parametric monotonic relationship | `scipy.stats.spearmanr(rq, delta)` |
| Pearson correlation | Linear relationship (comparison) | `scipy.stats.pearsonr(rq, delta)` |

### 4.7 Strategies Compared

| Strategy | Params | Key Mechanisms |
|----------|--------|----------------|
| V3 | slow=120, trail=3.3, trail_confirm=2, cooldown=6, time_stop=30, weak_vdo=0.0065 | Time stop truncates at 30 bars. Cooldown prevents re-entry for 6 bars. Activity filter. |
| V4 | slow=120, trail=2.8, trail_confirm=1, cooldown=3, time_stop=60, lagged_atr | Wider time stop (60 bars). Lagged ATR. |
| E5+EMA21D1 | slow=120, trail=3.0, vdo_thr=0.0, d1_ema=21 | 4 params. No time stop, no cooldown. Trail + EMA cross-down exit. D1 EMA(21) regime filter. |

---

## 5. Results Summary

### 5.1 Aggregate Tests

| Test | V3 Claim | Result |
|------|----------|--------|
| 1. Block-size | Ranking changes with blksz | **NO** — V3/E5 ratio spread 0.045, stable |
| 2. Regime-conditioned | V3 gains more than E5 | **NO** — E5 gains +0.187, V3 gains +0.123 |
| 3. Ablation | V3 mechanisms help E5 | **NO** — E5+TS30+CD6 hurts -0.179 Sharpe |

### 5.2 Granular Tests

| Test | Question | Result |
|------|----------|--------|
| 4. Paired Wilcoxon | E5>V3 significant? | **YES** — p=6.83e-63, P(V3>E5)=15.4% |
| 5. Regime correlation | Regime quality helps V3? | **NO** — ρ=-0.098 (p=0.029), negligible |
| 6. Trade decomposition | What V3 truncates | **183%** P&L exposure (upper bound); **actual ablation loss ~40%** |

### 5.3 Key Quantitative Findings

**Test 4 — Paired paths** (period-aligned):
- blksz=60: δ median=-0.262, P(V3>E5)=15.4%, Wilcoxon p=6.83e-63
- blksz=360: δ median=-0.315, P(V3>E5)=11.2%, Wilcoxon p=2.83e-70
- V3 win rate change -4.2pp with larger blocks → negligible regime effect

**Test 5 — Regime quality terciles**:
- Low (choppy): δ̃=-0.228, P(V3>E5)=16.8%
- Mid: δ̃=-0.250, P(V3>E5)=15.5%
- High (clean): δ̃=-0.293, P(V3>E5)=13.9%
- Monotonically DECREASING: cleaner regimes help E5 more
- Spearman ρ=-0.098, borderline |ρ|<0.1 → negligible relationship

**Test 6 — E5 trade P&L by duration**:
- ≤10 bars: 31 trades, -32.0% of P&L (losers)
- 11-30 bars: 71 trades, -51.1% of P&L (losers)
- 31-60 bars: 54 trades, +40.7% of P&L, 66.7% win rate
- 61-120 bars: 24 trades, +80.7% of P&L, 95.8% win rate
- >120 bars: 6 trades, +61.7% of P&L, 100% win rate
- Trades ≤30 bars (V3's entire range): **-83.1%** net P&L contribution
- Trades >30 bars (P&L exposure, upper bound): **+183.1%** of total P&L
- Actual ablation loss (E5 vs E5+TS30): **~40%** of profit (time_stop captures partial profit + allows re-entry)

---

## 6. Reproduction

### 6.1 Run Tests 1-3 (Aggregate)

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate
PYTHONUNBUFFERED=1 python research/x36/branches/a_vcbb_bias_study/test_battery/run_tests.py
# Runtime: ~200 minutes
# Output: test_battery/results/{test1,test2,test3}_*.json, ANALYSIS.md
# Charts: test_battery/figures/test{1,2,3}_*.png
```

### 6.2 Run Tests 4-6 (Granular)

```bash
cd /var/www/trading-bots/btc-spot-dev
source /var/www/trading-bots/.venv/bin/activate
PYTHONUNBUFFERED=1 python research/x36/branches/a_vcbb_bias_study/test_battery/run_deep_tests.py
# Runtime: ~32 minutes
# Output: test_battery/results/{test4,test5,test6}_*.json, DEEP_ANALYSIS.md
# Charts: test_battery/figures/test{4,5,6}_*.png
```

### 6.3 Verify Results

Key checkpoints for correctness:
- Test 1: V3/E5 ratio at blksz=60 should be ≈0.68-0.73 (±0.03)
- Test 2: E5 regime gain > V3 regime gain
- Test 3: E5+TS30+CD6 bootstrap Sharpe ≈ V3 bootstrap Sharpe (same mechanism, ≈same result)
- Test 4: P(V3>E5) ≈ 15% at blksz=60, ≈11% at blksz=360
- Test 5: ρ should be negative or near-zero (|ρ| < 0.1)
- Test 6: V3 max_bars_held = 30.0 exactly; E5 trades ≤30 bars should be net negative P&L; actual ablation ~40%

### 6.4 Changing Strategies

To compare Strategy A vs Strategy B instead of V3 vs E5:
1. In `run_tests.py`: update `_make_strat()` factory and `STRAT_NAMES_3`
2. In `run_deep_tests.py`: update `_safe_sharpe()` factory
3. In Test 3: create an ablation class for Strategy B's distinctive mechanisms
4. In Test 6: adjust the truncation threshold (30 bars) to match Strategy B's time_stop

---

## 7. Reuse Guide

### 7.1 When to Use This Framework

Use when an analyst claims:
- "Bootstrap method X biases against strategy Y"
- "Strategy Y exploits regime structure that bootstrap destroys"
- "Strategy Y's mechanism is valuable but the evaluation doesn't capture it"

### 7.2 Which Tests to Run

| Situation | Minimum Tests | Full Battery |
|-----------|---------------|-------------|
| "Bootstrap biases ranking" | 1 (block-size sensitivity) | 1, 2, 4 |
| "Regime structure matters" | 2 (regime-conditioned) + 5 (correlation) | 2, 4, 5 |
| "Mechanism X is valuable" | 3 (ablation) | 3, 6 |
| "Strategy A > B, evaluation is wrong" | 4 (paired Wilcoxon) | All 6 |

### 7.3 Adapting Test 2 (Regime-Conditioned Bootstrap)

The regime-conditioned bootstrap can use any regime labeling:
- D1 EMA(N) for trend regimes (current: N=21)
- Volatility percentile for vol regimes
- Hidden Markov Model states
- Any binary or categorical label

Change `_compute_regime_segments()` to use your labeling method.

### 7.4 Adapting Test 5 (Regime Quality Metric)

The quality metric can be replaced with:
- Max contiguous same-regime length (captures "did any long trend survive?")
- Hurst exponent of synthetic path (persistence measure)
- Autocorrelation at lag K of returns
- Any scalar path characteristic that measures "regime cleanness"

### 7.5 Interpreting Negative ρ in Test 5

A negative ρ (as found here: -0.125) means the strategy being tested does WORSE
on paths with better regime quality. This occurs when:
- The strategy's mechanism is not truly regime-adaptive
- The competing strategy benefits MORE from clean regimes (e.g., fat-tail trades
  need long trending periods to materialize)
- The tested strategy's mechanism is actually a drag on regime-dependent alpha

---

## 8. File Inventory

```
research/x36/branches/a_vcbb_bias_study/test_battery/
├── REFERENCE.md                          # This document
├── run_tests.py                          # Tests 1-3 runner (590 lines)
├── run_deep_tests.py                     # Tests 4-6 runner (520 lines)
├── results/
│   ├── ANALYSIS.md                       # Tests 1-3 auto-generated report
│   ├── DEEP_ANALYSIS.md                  # Tests 4-6 auto-generated report
│   ├── test1_blocksize.json              # Block-size sensitivity data
│   ├── test2_regime_boot.json            # Regime-conditioned bootstrap data
│   ├── test3_ablation.json               # Ablation data (full-sample + bootstrap + epochs)
│   ├── test4_paired.json                 # Per-path Sharpe pairs + Wilcoxon stats
│   ├── test5_regime_corr.json            # Correlation stats + tercile decomposition
│   └── test6_trade_decomp.json           # Trade-level P&L decomposition
├── figures/
│   ├── test1_blocksize.png               # Sharpe vs blksz + V3/E5 ratio
│   ├── test2_regime_comparison.png       # VCBB vs regime-conditioned bar chart
│   ├── test3_ablation.png                # Ablation full-sample vs bootstrap + regime
│   ├── test4_paired_delta.png            # δ histogram at blksz=60 and 360
│   ├── test5_regime_correlation.png      # Scatter + tercile box plot
│   └── test6_trade_decomposition.png     # P&L buckets + duration scatter
└── run.log                               # Tests 1-3 execution log
```

### Dependencies

- Python 3.12, numpy, scipy, matplotlib
- `v10.core.*` (BacktestEngine, types, data)
- `strategies/vtrend_e5_ema21_d1/strategy.py`
- `research/x36/branches/a_vcbb_bias_study/v3v4_strategies.py` (V3Strategy, V4Strategy)
- `research/x36/branches/a_vcbb_bias_study/run_comparison.py` (helpers: _fast_load_bars, _build_synthetic_feed, etc.)
- `research/lib/vcbb.py` (VCBB bootstrap)
