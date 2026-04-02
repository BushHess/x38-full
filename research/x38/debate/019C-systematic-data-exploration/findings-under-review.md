# Findings Under Review — Systematic Data Exploration

**Topic ID**: X38-T-19C
**Opened**: 2026-04-02
**Author**: human researcher

2 findings about systematic raw data exploration — the catalog of untapped fields,
patterns, and analytical dimensions (DFL-06, 10 analyses) and the methodology
toolkit for executing them (DFL-07, 6 method categories A-F).

Split from Topic 019 (2026-04-02). Original findings at lines 405-1205.

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

## DFL-06: Systematic Raw Data Exploration (Untapped Fields & Patterns)

- **issue_id**: X38-DFL-06
- **classification**: Thiếu sót
- **opened_at**: 2026-03-30
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note**: DFL-06 contains both ARCHITECTURE content (the framework
> should support systematic raw data exploration) and RESEARCH PLAN content (10
> specific analyses to run on btc-spot-dev data). The architecture decision for
> debate is D-12: should the 10 analyses be part of the framework spec (defining
> the METHOD SPACE) or deferred to the first campaign's methodology? The specific
> analyses are evidence for the architecture proposal, not binding implementation.

**Motivation**:

DFL-01 proposes an AI analysis layer. Topic 006 enumerates features from 6 known
families. But neither addresses a fundamental gap: **systematic exploration of raw
data for unknown patterns**. Topic 006 enumerates features humans already designed.
DFL-01 analyzes results humans already produced. No mechanism explores raw data
fields that have never been examined.

Data has 13 fields. Strategies use 5. Three numeric fields (`quote_volume`,
`num_trades`, `taker_buy_quote_vol`) have NEVER been used in any indicator.
Six derivable features have never been computed. Multiple analytical dimensions
have never been explored despite data being available since 2017.

**Data inventory — used vs untapped**:

```
13 fields available:
  USED (5):     open, high, low, close, taker_buy_base_vol
  UNTAPPED (4): quote_volume, num_trades, taker_buy_quote_vol, volume*

  * volume used only as VDO denominator, never analyzed independently

6 derivable features never computed:
  avg_trade_size    = quote_volume / num_trades       (institutional vs retail proxy)
  taker_buy_premium = taker_buy_quote_vol/quote_vol   (price-weighted buy pressure)
                      vs taker_buy_base_vol/volume     (volume-weighted buy pressure)
  volume_per_trade  = volume / num_trades              (participation concentration)
  quote_per_base    = quote_volume / volume            (≈ VWAP, intrabar price level)
  trade_intensity   = num_trades / (high - low)        (trades per unit price move)

3 timeframes available but underexploited:
  15m: 299,755 rows (never used in any strategy or analysis beyond X25 raw EDA)
  H1:  74,953 rows  (never used — strategies run H4 only)
  H4+D1: 96,423 rows (primary, but only D1 used for regime filter)
```

**Proposal**: 10 systematic analyses, all executable with existing data.

### Analysis 1: Microstructure Beyond VDO

**What**: Explore `quote_volume`, `num_trades`, `taker_buy_quote_vol` and derived
features for predictive content and structural patterns.

**Specific tests**:
- Forward-predictive content: each of 6 derived features vs fwd returns at
  t+1, t+6, t+24 (same methodology as X25 TBR analysis)
- Regime conditioning: do derived features behave differently in bull/bear/flat?
- VDO replacement candidates: does `taker_buy_premium` outperform simple
  `taker_buy_ratio` as entry filter?
- `trade_intensity` as volatility proxy: correlation with realized vol, ATR
- `avg_trade_size` regime shifts: do structural breaks in trade size precede
  price regime changes?
- Non-linear feature interactions: after testing individual features, test
  top-N pairwise combinations (e.g., high volume + low trade count = few
  large trades → what happens next?)

**Data required**: Existing 13-field CSV. No new data.

**Prior evidence**: X25 tested TBR forward-predictive content → near-zero.
But TBR is only 1 of 6+ derivable features. The other 5 are unexplored.
X34 tested Q-VDO-RH (volume ratio replacement) → rejected, but used only
`quote_volume` in isolation, not the full derived feature set.

### Analysis 2: Intrabar Patterns

**What**: Use 15m (300K rows) and H1 (75K rows) data to detect sub-H4 patterns
invisible at H4 resolution.

**Specific tests**:
- Intrabar volatility shape: does the distribution of sub-bar returns within
  an H4 bar predict the next H4 bar? (4×H1 or 16×15m per H4 bar)
- Opening vs closing sub-bar: is the first 15m bar of an H4 period more
  informative than the last?
- Intrabar volume profile: does volume concentration (e.g., 80% of H4 volume
  in first H1) predict direction?
- Sub-bar momentum: does H1-level momentum within an H4 bar carry over?
- Volatility term structure: compare 15m vol vs H1 vol vs H4 vol. When
  short-term vol > long-term vol (inverted), is it predictive?

**Data required**: Existing 15m and H1 CSVs. No new data.

**Prior evidence**: No prior analysis of sub-H4 patterns exists in the project.
X27 EDA analyzed H4 bars only. Strategies use H4 as minimum resolution.

### Analysis 3: Regime Transitions

**What**: Analyze WHEN and HOW D1 EMA(21) regime flips occur, and whether
transitions are predictable.

**Specific tests**:
- Transition frequency: how often does close cross EMA(21) on D1? Duration
  per regime (bull/bear)?
- Pre-transition signals: do any H4-level indicators (ATR, volume, VDO)
  shift measurably before D1 regime flips?
- False crossovers: what fraction of regime flips reverse within N bars?
  Is there a "confirmation" filter?
- Transition cost: what is the average P&L impact of being wrong about
  regime during the transition period?
- Predictability: can a simple model (logistic on H4 features) predict
  next-day regime with AUC > 0.55?

**Data required**: Existing H4+D1 data. No new data.

**Prior evidence**: X31-A tested D1 regime exit mid-trade → STOP (selectivity
0.21). But that studied EXIT timing, not ENTRY timing. Regime transition
predictability for entry has never been tested.

### Analysis 4: Time-of-Day / Day-of-Week Effects

**What**: Test whether H1/15m returns, volatility, or volume have systematic
patterns by hour-of-day or day-of-week.

**Specific tests**:
- Hourly return profile: mean return by hour (0-23 UTC) on H1 data
- Hourly volatility profile: |return| by hour — are some hours consistently
  more volatile?
- Day-of-week effects: mean return and volatility by day on D1 data
- Volume by hour: is there a systematic volume pattern? (exchange-driven,
  timezone-driven, or flat?)
- Signal timing: does strategy entry timing correlate with high/low-volume
  hours? Is performance hour-dependent?
- Calendar effects: monthly, quarterly, BTC halving cycle effects on returns
  and volatility. Are there systematic seasonal patterns?

**Data required**: Existing H1 data with `open_time` (timestamp). No new data.

**Prior evidence**: No prior time-of-day analysis exists. Crypto is 24/7 so
the assumption was "no market hours = no intraday pattern." This assumption
has never been tested.

### Analysis 5: Volume Microstructure

**What**: Analyze volume dynamics as a system — not just VDO, but volume
regime structure, non-stationarity, and interaction with returns.

**Specific tests**:
- Volume regime detection: structural breaks in rolling volume level (X27
  noted peak 24K BTC/bar 2022, drop to 3.5K by 2025). How many regimes?
  Change-point detection.
- Volume regime → return regime: does volume regime predict return
  characteristics (volatility, trend persistence)?
- `num_trades` vs `volume` divergence: when trade count is high but volume
  is low (many small trades) vs few large trades — does this predict anything?
- Volume mean-reversion: is volume ratio (current/rolling_mean) predictive
  of future |returns|?
- Non-stationarity correction: can VDO be improved by normalizing for
  volume regime? (VDO currently uses raw EMA ratio without level adjustment)
- Multi-scale VDO divergence: VDO at H1 vs H4 vs D1 — do different scales
  give different signals? When they diverge, is that informative?
  (Note: lead-lag aspect of multi-scale VDO covered in Analysis 8)

**Data required**: Existing data. No new data.

**Prior evidence**: X27 documented volume non-stationarity and found volume
predicts |return| only 1-6 bars (clustering). But no study tested volume
REGIME (structural level) as distinct from volume SIGNAL (bar-to-bar).

### Analysis 6: Higher-Order Statistical Patterns

**What**: Analyze time-varying distributional properties beyond mean and
variance.

**Specific tests**:
- Rolling kurtosis: does excess kurtosis (measured at 20.4 in X27) vary
  systematically? High-kurtosis periods vs low-kurtosis periods.
- Rolling skewness: is skewness time-varying? Does positive skew precede
  or follow trends?
- Tail dependence: are large up-moves and large down-moves clustered
  together (tail dependence) or independent?
- Variance ratio dynamics: Lo-MacKinlay VR was ~1.0 at H4 (X27). Is this
  constant or does it shift? VR > 1 = trending, VR < 1 = mean-reverting.
- Autocorrelation structure shifts: does the ACF of returns change over
  time? (e.g., stronger autocorrelation during trends)
- Shannon entropy of returns: rolling entropy as regime indicator.
  High entropy = random/efficient, low entropy = structured/trending.
  Does entropy regime predict strategy performance?

**Data required**: Existing H4 returns. No new data.

**Prior evidence**: X27 computed static statistics (kurtosis=20.4, Hurst=0.58,
VR≈1.0). No study checked whether these are TIME-VARYING.

### Analysis 7: Signal Saturation & Decay

**What**: Test whether the EMA crossover + VDO signal has degraded over time
as markets evolve.

**Specific tests**:
- Rolling Sharpe by year: is strategy Sharpe declining? (full-sample 1.45,
  but is it 2.0 in 2018 and 0.5 in 2025?)
- Signal alpha decay: regress strategy alpha on time. Slope significantly
  negative?
- Participation rate by year: are fewer trades occurring as market adapts?
- VDO discriminative power by year: does VDO filter's hit rate (% of
  filtered trades that were losers) change over time?
- Market efficiency test: is the variance ratio trending toward 1.0 from
  either direction? (Would imply market becoming more efficient)

**Data required**: Existing data + existing backtest results. No new data.

**Prior evidence**: No temporal decomposition of strategy performance exists.
Full-sample metrics (Sharpe, CAGR, MDD) are reported as single numbers.
WFO tests time-series robustness but reports aggregate win rate, not
per-window trend.

### Analysis 8: Lead-Lag Between Timeframes

**What**: Test whether lower-resolution timeframes predict higher-resolution
returns, or vice versa. Currently D1 is used only as binary regime filter
(close > EMA(21)). But D1 has rich features (volume, range, num_trades)
that may predict H4 behavior.

**Specific tests**:
- Cross-timeframe return correlation: H1 return at t vs H4 return at t+1.
  15m return at t vs H1 return at t+1. Granger-causality tests.
- D1 features → H4 next-day: does D1 volume, D1 range, D1 num_trades,
  D1 taker_buy_ratio predict next-day H4 return characteristics
  (volatility, direction, trend quality)?
- H1 momentum carry-over: does H1-level momentum within an H4 bar
  predict the NEXT H4 bar? (Distinct from Analysis 2 which looks
  at intrabar patterns within the same bar.)
- Multi-scale VDO lead-lag: does VDO at H1 lead VDO at H4? Does VDO
  scale divergence predict returns? (Structural divergence in Analysis 5;
  temporal lead-lag relationship here)
- Volatility cascade: does 15m volatility spike predict H1 volatility
  spike predict H4 volatility spike? What is the typical propagation
  time?

**Data required**: Existing 15m, H1, H4, D1 CSVs. No new data.

**Prior evidence**: No cross-timeframe predictive analysis exists. D1 is
used only as binary filter (close > EMA). X27 analyzed H4 only. The
multi-timeframe relationship is the most obvious untested dimension
given that data at 4 resolutions already exists.

**Differs from Analysis 2**: Analysis 2 looks at sub-bar structure WITHIN
one H4 bar (intrabar patterns). Analysis 8 looks at predictive
relationships ACROSS timeframes (lead-lag dynamics).

### Analysis 9: Conditional / Event-Based Dynamics

**What**: Analyze what happens AFTER specific market events. DFL-06
Analyses 1-8 examine features unconditionally (full-sample averages).
This analysis examines conditional distributions: given event X just
happened, what is the distribution of returns/volatility/volume in the
next N bars?

**Specific events to study**:
- Post-shock recovery: after a >3σ H4 return, what is the typical
  recovery pattern? Mean reversion? Continuation? Duration? Asymmetry
  (up-shocks vs down-shocks)?
- Post-VDO-cross: after VDO crosses zero (positive → negative or vice
  versa), what is the return distribution for 1/6/24 bars? Is this
  already priced into the strategy's entry signal?
- Post-regime-flip: after D1 EMA(21) regime changes, what is the
  typical trajectory? How many bars of uncertainty? What is the false
  flip rate and at what point is a flip "confirmed"?
- Post-volume-spike: after volume exceeds 3x rolling mean, what
  happens? Is the spike informative (trend start) or noise (single
  event liquidation)?
- Post-drawdown: after strategy MDD exceeds X%, what is the recovery
  distribution? Is recovery speed predictable from any features?
- Post-flat: after N consecutive bars with |return| < median, does
  a breakout follow? Probability and timing.

**Data required**: Existing H4+D1 data + existing backtest results for
strategy-conditional events. No new data.

**Prior evidence**: X31-A studied D1 regime exit mid-trade (transition
timing for exits). X27 noted pre-trend behavior (+9.16% cumulative in
20 bars before trend start). But systematic post-event dynamics across
multiple event types have never been studied.

**Differs from Analysis 3**: Analysis 3 focuses specifically on regime
transition predictability. Analysis 9 covers ALL event types (shocks,
VDO crosses, volume spikes, drawdowns, flat periods) and their
post-event dynamics.

### Analysis 10: Liquidity Proxy (Amihud Illiquidity)

**What**: Compute and analyze the Amihud illiquidity ratio — a
well-established measure of price impact per unit volume:

```
amihud = |return| / volume
```

High Amihud = illiquid (large price impact per unit traded).
Low Amihud = liquid (small price impact per unit traded).

**Specific tests**:
- Amihud time series: compute rolling Amihud on H4 data. Structural
  breaks? Trend? Regime-dependent?
- Amihud vs strategy performance: does strategy perform differently in
  high-liquidity vs low-liquidity periods? Split by Amihud tercile.
- Amihud as cost proxy: real trading cost is not constant 50 bps.
  Does Amihud predict realized slippage? If so, can it condition
  position sizing (smaller positions when illiquid)?
- Amihud and MDD: does high Amihud precede or coincide with drawdown
  periods? If predictive, it could serve as a risk management signal.
- Amihud vs VDO: is Amihud correlated with VDO? Or do they capture
  orthogonal dimensions? (VDO = directional flow pressure, Amihud =
  market depth / impact cost)

**Data required**: Existing OHLCV data (close, volume). No new data.

**Prior evidence**: No liquidity analysis exists in the project. X22
(Cost Sensitivity) analyzed strategy performance at different ASSUMED
cost levels (2-100 bps), but never measured actual market liquidity
conditions. Amihud would connect X22's cost analysis to real market
state.

**Differs from Analysis 5 (Volume Microstructure)**: Analysis 5 looks
at volume LEVEL (structural breaks, non-stationarity, regime). Analysis
10 looks at price IMPACT per unit volume — a fundamentally different
dimension. Volume can be high but liquidity low (many small trades
moving price) or volume low but liquidity adequate (few trades, tight
spread, minimal impact).

**→ Extended by DFL-15**: Roll's realized spread estimator proposed as
complementary liquidity measure, but requires tick data (inapplicable at H4).

---

**Open questions**:
- Execution order: should analyses run sequentially (each informing the next)
  or in parallel? Analysis 1 (microstructure) and Analysis 7 (saturation)
  are independent. Analysis 3 (regime transitions) may inform Analysis 4
  (time-of-day). Analysis 8 (lead-lag) is independent. Analysis 9
  (event-based) benefits from Analysis 3 results. Analysis 10 (Amihud)
  is independent.
- Minimum threshold: what constitutes an "interesting" finding from these
  analyses? p < 0.05? Economic significance > X bps?
- Integration with DFL-01: are these 10 analyses a ONE-TIME study or a
  recurring component of the DFL-01 analysis layer?
- Feature promotion path: if Analysis 1 discovers `trade_intensity` is
  predictive, what is the path to: (a) add it to Topic 006 feature
  registry, (b) create a strategy template using it, (c) validate?
  This path MUST respect DFL-03 and DFL-04 contamination rules.
  **→ Addressed by DFL-08** (Feature Candidate Graduation Path, 5 stages).
- SSE-D-02 scope: DFL-06 analyses use non-OHLCV fields (num_trades,
  quote_volume, taker_buy_quote_vol). Does SSE-D-02 hard rule 3 block this?
  **→ Addressed by DFL-09** (scope clarification: analysis ≠ ideation).

---

## DFL-07: Raw Data Analysis Methodology & Techniques

- **issue_id**: X38-DFL-07
- **classification**: Thiếu sót
- **opened_at**: 2026-03-30
- **opened_in_round**: 0
- **current_status**: Open

> **Debate scope note** (2026-03-31, gap audit): DFL-07 contains extensive
> methodology catalogs (6 categories, dozens of techniques) that are reference
> material, not architectural decisions. The actual design question is narrow:
> should the framework SPEC define a mandatory analysis methodology, or defer
> method selection to each campaign's protocol? The catalogs are evidence for
> the proposal, not binding spec content. Debate should focus on the architecture
> question, not on evaluating individual statistical methods.

**Motivation**:

DFL-06 defines WHAT to analyze (10 analyses). This finding defines HOW — the
statistical methods, visualization techniques, and discovery workflow that make
raw data analysis systematic and reproducible rather than ad-hoc.

**Relationship to DFL-01**: DFL-01 proposes an ongoing AI analysis layer.
DFL-07 provides the methodological toolkit that layer would use. If DFL-06's
analyses become recurring (per DFL-06 open question), DFL-07 is the
implementation specification for DFL-01's "data analysis" domain.
If one-time, DFL-07 is a standalone research methodology.

**Relationship to RESEARCH_RULES.md** (docs/research/RESEARCH_RULES.md:55-137 [extra-archive]):
btc-spot-dev already has Pattern A (standalone runner, :57-101) and Pattern B
(CLI integration, :104-137) for research studies. DFL-07's workflow EXTENDS
these patterns, not replaces them:
- Phase 1-2 (SCAN, DEEP DIVE): follow Pattern A (standalone scripts)
- Phase 3 (VALIDATION): follow Pattern B (integration with validation/)
- C2 reproducibility requirements: inherit from docs/research/RESEARCH_RULES.md:55-137 [extra-archive]

**Architecture vs Research Plan boundary**: DFL-07 contains both:
- **Architecture requirements** (what the framework must support):
  sections A-F define the METHOD SPACE the framework must accommodate
- **Research plan** (what to run first):
  specific technique selections, tool choices, hypothesis priorities
When Alpha-Lab is built, architecture requirements become framework
capabilities. Research plan becomes the first campaign's methodology.
These should be read as two layers, not one monolith.

The project's prior EDA (X25, X27) used basic tools (ACF, correlation, summary
stats). Many powerful techniques for structure discovery in financial time series
have never been applied. Without a defined methodology, DFL-06's 10 analyses
risk becoming another collection of scatter plots and p-values instead of a
genuine discovery engine.

---

### A. Statistical & Computational Methods

#### A1. Distributional Analysis

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **KDE (Kernel Density Estimation)** | Non-parametric density estimation. Reveals multi-modality, fat tails, asymmetry that histograms miss | Analysis 1 (derived feature distributions), 6 (higher-order), 9 (post-event return distributions) |
| **QQ-plot (Quantile-Quantile)** | Compare empirical distribution vs theoretical (normal, Student-t). Identifies where tails deviate | Analysis 6 (tail dependence), 7 (saturation — are tails changing?) |
| **ECDF (Empirical CDF)** | Non-parametric CDF comparison between groups (regimes, time periods). More robust than histogram | Analysis 3 (regime transition), 4 (time-of-day), 9 (conditional) |
| **Two-sample KS test** | Formal test: are two distributions different? (e.g., returns in bull vs bear regime) | Analysis 3, 4, 9 — anywhere comparing conditional distributions |
| **Permutation test** | Distribution-free hypothesis testing. Already used in project (X0 component analysis). Apply to new features | Analysis 1 (are derived features predictive?), 8 (is lead-lag real?) |

#### A2. Time Series Structure

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Rolling statistics (mean, std, skew, kurtosis)** | Detect non-stationarity and regime shifts in any metric over time | Analysis 5 (volume), 6 (higher-order), 7 (saturation), 10 (Amihud) |
| **Structural break detection (CUSUM, Bai-Perron)** | Identify change-points in time series level or variance. More rigorous than visual inspection | Analysis 5 (volume regimes), 7 (signal decay breakpoint), 10 (liquidity regime changes) |
| **Granger causality** | Test whether lagged values of X predict Y beyond Y's own lags | Analysis 8 (lead-lag between timeframes), 1 (do derived features Granger-cause returns?) |
| **Cross-correlation function (CCF)** | Measure lead-lag correlation at multiple lags between two series | Analysis 8 (timeframe lead-lag), 5 (volume-return lead-lag) |
| **Variance ratio test (Lo-MacKinlay)** | Test random walk hypothesis at multiple horizons. Already computed once (X27) — now as rolling window | Analysis 6 (variance ratio dynamics), 7 (market efficiency over time) |
| **Autocorrelation function (ACF/PACF)** with rolling window | X27 computed static ACF. Rolling ACF reveals when serial dependence appears/disappears | Analysis 6 (autocorrelation structure shifts) |

#### A3. Dependence & Interaction

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Rank correlation (Spearman, Kendall)** | Non-linear dependence between features. More robust than Pearson for non-normal data | Analysis 1 (derived feature vs returns), 10 (Amihud vs VDO) |
| **Mutual information (MI)** | Captures non-linear dependence that correlation misses. MI > 0 = any dependence | Analysis 1 (feature screening — which derived features carry information about returns?) |
| **Conditional mutual information** | MI between X and Y given Z. Detects redundancy between features | Analysis 1 (pairwise interactions — does feature A add info beyond feature B?) |
| **Copula analysis** | Model dependence structure in tails separately from marginals. Captures tail dependence | Analysis 6 (tail dependence — are extreme up/down moves jointly dependent?) |
| **Information coefficient (IC)** | Rank correlation between feature and forward returns. Standard quant metric. Already used in X21 | Analysis 1 (all derived features), 8 (cross-timeframe predictors) |

#### A4. Classification & Prediction

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Logistic regression** | Binary classification (up/down, regime A/B). Interpretable. Already used in X14 (churn filter) | Analysis 3 (predict regime flip), 9 (predict post-event direction) |
| **Random forest feature importance** | Rank features by predictive contribution. Non-linear, handles interactions | Analysis 1 (which derived features matter most?), 8 (which timeframe features?) |
| **AUC-ROC** | Measure discriminative power of a classifier or score. Already used in X13 (AUC=0.805) | Analysis 3 (regime prediction), 4 (time-of-day predictiveness) |
| **Quantile regression** | Model conditional quantiles (not just conditional mean). Reveals asymmetric effects | Analysis 9 (post-event: median vs tail outcomes), 10 (Amihud effect on drawdown quantiles) |
| **Walk-forward validation** | Already standard in project (WFO). Apply to all predictive claims from DFL-06 | ALL analyses that claim predictive content |

#### A5. Change Detection & Segmentation

| Technique | Purpose | Applies to (DFL-06) |
|-----------|---------|---------------------|
| **Hidden Markov Model (HMM)** | Unsupervised regime detection. Discovers latent states from observed data | Analysis 3 (how many regimes exist beyond bull/bear?), 5 (volume regime count) |
| **PELT (Pruned Exact Linear Time)** | Fast change-point detection in mean/variance. Finds optimal segmentation | Analysis 5 (volume structural breaks), 7 (signal decay change-point) |
| **Ruptures library** | Multiple change-point detection algorithms (PELT, Binseg, BottomUp, Window) | Analysis 5, 7, 10 — anywhere seeking structural breaks |
| **Rolling window Fisher exact test** | Detect when a proportion (e.g., VDO hit rate) shifts significantly | Analysis 7 (VDO discriminative power decay by year) |

---

### B. Visualization Techniques

#### B1. Single-Variable Exploration

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Time series + rolling mean/bands** | Trend, level shifts, volatility clustering | First look at any feature. Rolling mean ± 2σ bands |
| **Histogram + KDE overlay** | Distribution shape, multi-modality, tails | Compare feature distributions across regimes/periods |
| **Box plot by group** | Central tendency + spread + outliers across categories | Time-of-day (24 boxes), day-of-week (7), regime (2-3), year (8) |
| **Violin plot** | Full distribution shape per group (KDE + box plot) | Where box plot hides distribution shape (multi-modal groups) |
| **Cumulative sum (CUSUM) chart** | Detect persistent shifts in mean | Signal decay (Analysis 7), regime transition detection (Analysis 3) |

#### B2. Two-Variable Relationships

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Scatter + regression line + confidence band** | Linear relationship, strength, outliers | Feature vs forward returns (Analysis 1, 8) |
| **Hexbin / 2D KDE** | Dense scatter where points overlap. Shows joint density | Feature vs returns when N > 10K (H4: 20K+ points) |
| **Lagged scatter matrix** | Relationships at multiple lags simultaneously | Lead-lag analysis (Analysis 8): X(t) vs Y(t+1), Y(t+2), ... |
| **Cross-correlogram** | CCF plot with confidence bands. Shows significant lead/lag | Analysis 8 (timeframe lead-lag), 5 (volume-return lag) |
| **Conditional distribution overlay** | KDE of Y given X in different quantiles | Analysis 9: return distribution given event type |

#### B3. Multi-Variable & Structure

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Correlation heatmap (Spearman)** | Pairwise rank-correlation among all features | Analysis 1: screen 6+ derived features for redundancy |
| **Clustermap (hierarchical clustering)** | Group correlated features. Reveals structure in feature space | Analysis 1: which derived features form clusters? |
| **PCA biplot** | Dominant variance directions in multi-feature space | Analysis 1: do 6 derived features reduce to 2-3 principal components? |
| **Pair plot (scatter matrix)** | All pairwise scatter plots + marginal distributions | Analysis 1: initial screening of 6 derived features |
| **Calendar heatmap** | Value by (week × day-of-week) or (hour × day-of-week) | Analysis 4: time-of-day × day-of-week return/volatility patterns |

#### B4. Temporal & Regime Visualization

| Technique | What it reveals | When to use |
|-----------|----------------|-------------|
| **Regime coloring on price chart** | Overlay detected regimes on actual price | Analysis 3: visualize regime transitions on price |
| **Event study plot (mean ± CI)** | Average path around an event with confidence bands | Analysis 9: post-shock, post-VDO-cross, post-regime-flip trajectories |
| **Rolling metric chart** | Time series of rolling Sharpe, IC, AUC, entropy, etc. | Analysis 6, 7: detect when statistical properties shift |
| **Stacked area chart** | Composition over time (e.g., volume by source) | Analysis 5: taker vs maker volume composition over years |
| **Drawdown chart with liquidity overlay** | Strategy drawdown + Amihud illiquidity on same axis | Analysis 10: visual check of liquidity-drawdown relationship |

---

### C. Discovery Workflow

#### C1. Six-Category Discovery Workflow

```
Phase 1: SCAN (broad, automated)
  ├── [A] Statistical screening: IC, MI, Granger vs forward returns
  ├── [B] Visualization: correlation heatmap, pair plot, rolling stats
  ├── [D] Decomposition: FFT spectrum, wavelet scalogram, EMD/STL on
  │       key series (returns, volume, taker_buy_ratio)
  ├── [F] Domain hypotheses: run quick tests for 12 hypotheses (F1-F4)
  ├── Output: ranked feature/pattern list + anomaly flags + hypothesis
  │          confirmation/rejection table
  └── Decision: which features/patterns pass initial screening?

Phase 2: DEEP DIVE (targeted, per promising feature/pattern)
  ├── [A] Full distributional analysis (KDE, QQ, conditional)
  ├── [A5] Structural break detection (PELT, CUSUM, HMM)
  ├── [B4] Event-study and regime visualization
  ├── [D] Decomposition of target feature: wavelet denoising, EMD
  │       component isolation, frequency-domain analysis
  ├── [E] Null model test: surrogate data or GARCH simulation
  │       → pattern survives realistic baseline?
  ├── [F] If domain-driven: deeper theory test, literature comparison
  └── Decision: is the pattern robust AND distinct from known properties?

Phase 3: VALIDATION (rigorous, before any feature enters pipeline)
  ├── Walk-forward test (out-of-sample predictive power)
  ├── [E] Surrogate validation: p_surrogate < 0.05 against realistic null
  ├── Multiple testing correction (Bonferroni/Holm across all Phase 1 tests)
  ├── Economic significance (> X bps after costs?)
  ├── Redundancy check: is this independent of existing features (VDO, EMA)?
  └── Decision: proceed to DFL-03 feedback channel or discard?
```

#### C2. Reproducibility Requirements

- Every analysis produces a **dated artifact** in `research/xNN/` following
  existing patterns (docs/research/RESEARCH_RULES.md:55-137 [extra-archive])
- Code: standalone Python script (Pattern A or B from docs/research/RESEARCH_RULES.md:57-137 [extra-archive])
- Output: markdown report + saved figures (PNG/SVG)
- All random seeds fixed, all parameters documented
- Results must be reproducible with `python research/xNN/script.py`

#### C3. Tool Stack

| Tool | Purpose | Already in project? |
|------|---------|-------------------|
| `numpy`, `pandas` | Data manipulation, rolling stats | Yes |
| `scipy.stats` | Statistical tests (KS, Granger proxy, permutation) | Yes |
| `scipy.signal` | FFT, Welch spectral density, coherence | Yes |
| `statsmodels` | ACF/PACF, variance ratio, Granger causality, quantile regression, STL | Yes |
| `matplotlib`, `seaborn` | Visualization (all B1-B4 techniques) | Yes |
| `scikit-learn` | Random forest, PCA, mutual information, AUC-ROC | Yes |
| `ruptures` | Change-point detection (PELT, Binseg) | **No — needs install** |
| `hmmlearn` | Hidden Markov Models for regime detection | **No — needs install** |
| `arch` | GARCH/GJR-GARCH simulation, variance ratio tests | Check availability |
| `PyWavelets` | Wavelet decomposition (DWT, CWT, scalogram) | **No — needs install** |
| `EMD-signal` | Empirical Mode Decomposition, VMD | **No — needs install** |

#### C4. Contamination Safeguard

Per DFL-04 constraints:
- Phase 1-2 outputs = **process observations** (Type 1 evidence). They
  describe data, not prescribe strategy decisions.
- Phase 3 WFO validation = same methodology as existing project validation.
  No special exemptions.
- If a feature passes Phase 3 and enters DFL-03 feedback:
  - As **new template**: provenance-tracked, NOT results-blind (DFL-03 rule)
  - As **grammar extension**: MUST be results-blind — the primitive must be
    defensible from data structure alone, not from backtested performance
  - As **investigation directive**: no contamination concern

---

### D. Signal Decomposition — Transform Data BEFORE Analysis

Statistical methods (A) analyze data as-is. Decomposition TRANSFORMS data
into components first, creating new representations that reveal hidden
structure (cycles, multi-scale trends, noise) invisible in raw time series.

#### D1. Frequency Domain

| Technique | What it reveals | Applies to (DFL-06) |
|-----------|----------------|---------------------|
| **FFT (Fast Fourier Transform)** | Dominant frequencies / hidden cycles. Power spectrum shows which periodicities carry energy | Analysis 4 (time-of-day: is there a 24h cycle? 168h weekly cycle? 4h cycle in volume?) |
| **Spectral density estimation (Welch)** | Smoothed power spectrum — more robust than raw FFT. Confidence bands on peaks | Analysis 4 (verify cycles are statistically significant, not noise) |
| **Coherence spectrum** | Frequency-domain correlation between two series. At which frequencies are they related? | Analysis 8 (lead-lag: are H1 and H4 returns coherent at specific frequencies?) |

**Limitation**: FFT assumes stationarity over the full window. Financial
data is non-stationary. Use SHORT windows or prefer wavelets (D2).

#### D2. Time-Frequency Domain

| Technique | What it reveals | Applies to (DFL-06) |
|-----------|----------------|---------------------|
| **DWT (Discrete Wavelet Transform)** | Multi-scale decomposition preserving time locality. Separate trend (low-freq) from noise (high-freq) at each time point | Analysis 2 (intrabar: decompose H4 bar into trend + noise using 15m sub-bars), Analysis 6 (rolling higher-order stats on wavelet-denoised series) |
| **CWT (Continuous Wavelet Transform)** | Scalogram — 2D map of power by (time × frequency). Shows WHEN cycles appear/disappear | Analysis 7 (saturation: does the dominant cycle change over time? Signal frequency shifting?) |
| **Wavelet coherence** | Time-varying coherence between two series at multiple scales | Analysis 8 (lead-lag: does H1→H4 lead-lag exist only at certain scales? Only during certain periods?) |

**Key value**: Wavelets reveal that a pattern exists at scale X during
period Y but not period Z. This is invisible to both static FFT and
rolling-window statistical methods.

#### D3. Adaptive Decomposition

| Technique | What it reveals | Applies to (DFL-06) |
|-----------|----------------|---------------------|
| **EMD (Empirical Mode Decomposition)** | Data-driven: decomposes into Intrinsic Mode Functions (IMFs) without pre-chosen basis. Each IMF = one oscillatory component | Analysis 5 (volume: separate structural level from seasonal from noise — each IMF analyzable separately) |
| **STL (Seasonal-Trend-Loess)** | Separates time series into Seasonal + Trend + Residual. Requires specifying period | Analysis 4 (extract 24h seasonal from H1 data, 7-day seasonal from D1), Analysis 5 (volume trend vs seasonal) |
| **Variational Mode Decomposition (VMD)** | Like EMD but more robust to noise and mode mixing. Decomposes into K modes at specified bandwidths | Analysis 3 (regime: decompose price into slow regime component + fast oscillation — regime transitions visible in slow component) |

**Key value for DFL-06**: Decompose volume into structural_level (IMF 1-2)
+ seasonal (IMF 3-4) + noise (IMF 5+). Then Analysis 5 tests structural_level
for regime breaks. Analysis 4 tests seasonal for time-of-day effects. Each
component becomes a SEPARATE input to statistical methods (A).

#### D4. Decomposition → Feature Pipeline

```
Raw H4 bar data (13 fields)
       │
       ├──→ [FFT] ──→ dominant_cycle_period, spectral_peak_power
       ├──→ [DWT] ──→ trend_component, noise_component, detail_coefficients
       ├──→ [EMD] ──→ IMF_1 (trend), IMF_2 (cycle), ..., residual
       └──→ [STL] ──→ seasonal_24h, trend, residual
              │
              ▼
       New derived features (input to Analysis 1-10 and methods A1-A5)
```

Each decomposition output is a NEW time series that can be analyzed with
ALL techniques in sections A and B. This multiplies the discovery surface:
10 analyses × 4 decomposition methods = 40 analysis paths (most won't
yield results, but some may reveal structure invisible in raw data).

---

### E. Null Model / Synthetic Baseline — Distinguish Real vs Artifact

Statistical significance (p-value) answers "is this pattern unlikely under
H0?" But the default H0 (iid normal) is WRONG for financial data. BTC/USDT
has fat tails, volatility clustering, and serial dependence in |returns|.
A pattern that looks "significant" against iid normal may be a trivial
consequence of these known properties.

Null models create REALISTIC synthetic baselines that preserve known
statistical properties, so only GENUINELY NEW patterns pass the test.

#### E1. Surrogate Data Methods

| Technique | What it preserves | What it destroys | Use for |
|-----------|------------------|-----------------|---------|
| **Random shuffle** | Marginal distribution (mean, variance, kurtosis) | ALL temporal structure | Baseline: "is temporal ordering necessary for this pattern?" |
| **Phase randomization (IAAFT)** | Marginal distribution + power spectrum (autocorrelation) | Non-linear dependencies, higher-order temporal structure | Baseline: "does this pattern require non-linear structure, or does linear autocorrelation explain it?" |
| **Block bootstrap** | Local temporal structure within blocks | Long-range dependencies | Baseline: "does this pattern require structure beyond N-bar windows?" Already used in VCBB (research/lib/vcbb.py) |
| **Stationary bootstrap** | Temporal structure with random block lengths | Long-range order with geometric block sampling | More robust than fixed-block bootstrap for non-stationary data |

#### E2. Parametric Null Models

| Model | What it captures | Use for |
|-------|-----------------|---------|
| **GARCH(1,1)** | Volatility clustering + fat tails (conditional heteroskedasticity) | "Does this pattern survive after accounting for vol clustering?" Fit GARCH → simulate 1000 paths → re-run analysis on each → percentile rank real result |
| **GJR-GARCH** | Asymmetric volatility (leverage effect: down-moves increase vol more than up-moves) | Same as GARCH but captures asymmetry. More realistic for BTC |
| **AR(p)-GARCH(1,1)** | Linear return predictability + volatility clustering | "Does the predictive signal survive after removing known autocorrelation + vol dynamics?" |

#### E3. Application to DFL-06 Analyses

| DFL-06 Analysis | Null model to use | What it validates |
|-----------------|------------------|-------------------|
| Analysis 1 (microstructure) | Phase randomization | "Does trade_intensity predict returns, or does any series with same ACF show this?" |
| Analysis 2 (intrabar) | Block bootstrap (H4-aligned) | "Do sub-bar patterns predict next bar, or does local structure explain it?" |
| Analysis 3 (regime transitions) | GARCH simulation | "Are transitions predictable, or does vol clustering create apparent predictability?" |
| Analysis 4 (time-of-day) | Block bootstrap (24h blocks) | "Is hourly pattern real, or artifact of vol clustering within days?" |
| Analysis 5 (volume) | Phase randomization of volume | "Do volume regime breaks predict return regime, or mechanical vol-volume coupling?" |
| Analysis 6 (higher-order) | GARCH simulation | "Is rolling kurtosis time-varying BEYOND what GARCH predicts?" |
| Analysis 7 (signal decay) | Stationary bootstrap | "Is Sharpe declining, or within normal variation of stationary process?" |
| Analysis 8 (lead-lag) | Phase randomization (bivariate) | "Does H1 lead H4, or does any pair with same cross-spectrum show this?" |
| Analysis 9 (event-based) | Conditional block bootstrap | "Is post-shock behavior special, or do GARCH large moves always look like this?" |
| Analysis 10 (Amihud) | Shuffle Amihud vs returns | "Does Amihud predict drawdowns, or mechanical relationship (both driven by vol)?" |

#### E4. Validation Protocol

```
For every pattern P discovered in DFL-06:

1. Define appropriate null model M (choose from E1/E2 based on what
   known property might explain P)
2. Generate N=1000 synthetic datasets from M
3. Compute test statistic T on each synthetic dataset
4. Compute T on real data
5. p_surrogate = fraction of synthetic T ≥ real T
6. Pattern P is REAL only if p_surrogate < 0.05

This is SEPARATE from and IN ADDITION to standard statistical tests (A).
A pattern must pass BOTH:
  - Standard test (A1-A5): significant vs iid null
  - Surrogate test (E): significant vs realistic null
```

---

### F. Domain-Driven Hypothesis Testing — Theory → Data, Not Data → Theory

Sections A-E are DATA-DRIVEN: explore data → find patterns → test them.
Section F is THEORY-DRIVEN: start from financial theory → derive testable
prediction → confirm or reject in BTC/USDT data.

Both directions are necessary. Data-driven finds the unexpected. Theory-driven
finds the expected-but-unverified. Together they cover the full discovery space.

#### F1. Market Microstructure Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Kyle's lambda (price impact)** | Kyle (1985) | Δprice = λ × signed_volume + ε. λ > 0, λ varies over time. High λ = illiquid. | Existing: taker_buy_base_vol as signed flow proxy, close as price. Regression per rolling window |
| **Volume-volatility mixture** | Clark (1973), Tauchen & Pitts (1983) | Volume = proxy for information arrival rate. If true: num_trades should predict realized vol better than raw volume | Existing: num_trades, volume, realized vol from H4 returns |
| **Informed trading detection** | Easley & O'Hara (VPIN, 2012) | Imbalance in taker flow = informed traders acting. Extreme imbalance → larger subsequent |return| | Existing: taker_buy_ratio as VPIN proxy. Test: extreme TBR → higher |fwd_return| |

#### F2. Behavioral Finance Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Momentum life cycle** | Jegadeesh & Titman (1993); Hong & Stein (1999) | Momentum profits: build (underreaction) → peak → decay (overreaction) → reversal. Testable as cross-horizon return autocorrelation profile | Existing: H4/D1 returns at multiple horizons. Compute ACF at lags 1, 6, 24, 72, 144 |
| **Herding / crowded trade** | Banerjee (1992) | When taker_buy_ratio reaches extremes (>0.55 or <0.45), market is one-sided → mean reversion likely | Existing: taker_buy_ratio. Test: conditional return distribution when TBR in top/bottom decile |
| **Disposition effect** | Shefrin & Statman (1985) | Traders sell winners too early, hold losers too long. If present in BTC: volume should spike after price recovers to recent high | Existing: volume + high_watermark derived from close |

#### F3. Market Efficiency Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Adaptive Market Hypothesis** | Lo (2004) | Market efficiency is time-varying. Predictability appears/disappears | Existing: rolling VR + ACF + Sharpe (Analysis 6/7). **Note**: AMH is an interpretive FRAMEWORK, not a single testable prediction. The "test" = Analysis 6/7 results interpreted through AMH lens. Reclassified as interpretive lens, not standalone hypothesis |
| **Fractal Market Hypothesis** | Peters (1994) | Instability when one horizon dominates participation | Existing: multi-timeframe volume data. **Specific testable prediction**: volume concentration at one timeframe → subsequent volatility. FMH as a whole is a framework, but this prediction IS testable |
| **Volatility feedback** | Campbell & Hentschel (1992) | Increased volatility → higher risk premium → lower prices (or higher expected returns). Asymmetric: vol up → price down stronger than vol down → price up | Existing: realized vol vs subsequent returns. Asymmetry test: separate up-vol periods vs down-vol periods |

#### F4. Crypto-Specific Hypotheses

| Hypothesis | Source | Testable prediction | Data needed |
|------------|--------|--------------------|----|
| **Halving cycle** | BTC supply schedule | Returns cluster in post-halving years (scarcity narrative). Testable: returns in months 0-18 post-halving vs other months | Existing: D1 returns + known halving dates (2016-07, 2020-05, 2024-04) |
| **Weekend effect** | Crypto-specific studies | Different return/volatility characteristics on weekends vs weekdays. Unlike TradFi (where weekend = no trading), crypto trades 24/7 but human attention varies | Existing: H1/D1 with timestamps. Analysis 4 partially covers this, but framing as crypto-specific hypothesis adds depth |
| **Funding rate proxy** | Perpetual futures market | When spot market shows strong directional taker flow, perp funding rate is likely extreme → crowded trade → reversal. Taker_buy_ratio as funding proxy | Existing: taker_buy_ratio. Test: does extreme TBR predict reversal with similar timing as known funding rate spikes? |

#### F5. Theory → DFL-06 Analysis Mapping

Each hypothesis can be tested WITHIN an existing DFL-06 analysis:

| Hypothesis | Primary DFL-06 Analysis | Additional test |
|------------|------------------------|-----------------|
| Kyle's lambda | Analysis 10 (Amihud is a simplified Kyle model) | Rolling λ estimation, λ vs strategy MDD |
| Volume-volatility mixture | Analysis 5 (volume microstructure) | num_trades vs realized_vol regression |
| Informed trading (VPIN) | Analysis 1 (microstructure) | TBR extremes → |fwd_return| conditional test |
| Momentum life cycle | Analysis 7 (saturation) | Multi-horizon ACF profile |
| Herding | Analysis 1 (microstructure) + Analysis 9 (event-based) | TBR extreme → conditional return KDE |
| Disposition effect | Analysis 9 (event-based) | Volume spike at high-watermark recovery |
| Adaptive Market | Analysis 6 (higher-order) + Analysis 7 (saturation) | Rolling VR + rolling Sharpe joint analysis |
| Fractal Market | Analysis 8 (lead-lag) | Volume concentration index across timeframes |
| Volatility feedback | Analysis 6 (higher-order) | Asymmetric vol→return regression |
| Halving cycle | Analysis 4 (calendar effects) | Post-halving month dummy variable |
| Weekend effect | Analysis 4 (time-of-day) | Weekend dummy on returns + vol |
| Funding rate proxy | Analysis 1 + Analysis 9 | Extreme TBR → reversal event study |

---

**Open questions**:
- Which Phase 1 screening metric is primary? IC (linear) vs MI (non-linear)?
  Use both and compare, or pick one as gate?
- Phase 2 depth: how many bars of analysis per feature before declaring
  "robust" or "spurious"? Risk of over-analysis (multiple testing).
- Phase 3 significance threshold: p < 0.05 after Holm correction? Or
  economic threshold (> X bps per trade) as primary gate?
- Surrogate method selection: should every DFL-06 analysis use the SAME
  null model (e.g., GARCH for all), or should each analysis use the most
  appropriate model from E1/E2? Latter is more rigorous but requires
  per-analysis judgment.
- Tool installation: `ruptures`, `hmmlearn`, `PyWavelets`, `EMD-signal`
  are not in current venv. Add to `pyproject.toml` or keep as optional
  research dependencies?
- Automation vs manual: should Phase 1 SCAN run automatically when new
  data arrives, or only on human request? (Interacts with DFL-01 trigger
  question.)
- Notebook vs script: DFL-06 analyses are exploratory by nature. Allow
  Jupyter notebooks for Phase 1-2 (exploration), require scripts for
  Phase 3 (validation)?
- Domain hypothesis priority: all 12 hypotheses in parallel, or rank by
  expected value and test sequentially? Kyle's lambda and momentum
  life cycle have strongest literature support for crypto.

---

## Cross-topic tensions

| Topic | Finding | Tension | Resolution path |
|-------|---------|---------|-----------------|
| 018 | SSE-D-02 (rule 3) | OHLCV-only rule vs DFL-06 scan using all 13 fields — analysis != ideation | Resolved by DFL-09 (019A): SSE-D-02 applies to automated ideation only, not to analysis or human templates. Needs debate confirmation |
| 018 | SSE-D-02 (rule 3, spirit) | Depth-2 composition within OHLCV satisfies letter but creates ~460x search space expansion — violates spirit? | DFL-12 (019D) poses the question; debate decides |

---

## Decision summary — what debate must resolve

Debate for Topic 019C must produce a decision on this question:

**Tier 3 — Budget & governance**:

| ID | Decision | Finding | Alternatives |
|----|----------|---------|-------------|
| D-12 | DFL-06/07 scope: architecture or research plan? | DFL-06+07 | Architecture (method space) / Research plan (defer to campaign) / Split |

**Note**: D-12 depends on Tier 1 outcome D-01 (019A) — if DFL-09 scope
clarification is rejected (D-01 = NO, analysis also restricted to OHLCV),
the scope of DFL-06's analyses changes significantly.

---

## Summary table

| Issue ID | Finding | Classification | Status |
|----------|---------|---------------|--------|
| X38-DFL-06 | Systematic raw data exploration (10 analyses) | Thiếu sót | Open |
| X38-DFL-07 | Raw data analysis methodology (6 categories) | Thiếu sót | Open |
