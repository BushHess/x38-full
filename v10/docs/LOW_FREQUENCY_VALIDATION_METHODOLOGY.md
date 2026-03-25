# Validation Methodology for Low-Frequency Strategies

**Scope:** Any systematic strategy producing fewer than ~25 trades per WFO window
(6-month OOS period), making window-level comparison statistically underpowered.

**Derived from:** V10/V11 validation campaign (2019-01 → 2026-02, BTC-USDT H4 bars).

**Intended use:** Reference document for all future strategy validation — to be applied
by human or AI analyst when comparing a candidate strategy against a baseline.

---

## Part 1: The Problem with WFO on Low-Frequency Strategies

### 1.1 Why WFO Breaks Down

Walk-Forward Optimization uses fixed-length windows (typically 6 months OOS) to
evaluate strategy performance out-of-sample. For high-frequency strategies (hundreds of
trades per window), each window's summary statistics are well-estimated. For
low-frequency strategies, they are not.

The core issue is **statistical power**: the ability to detect a real effect amid noise.
Power depends on three quantities:

```
SNR_window = |μ| / (σ / √N)
```

Where:
- μ = true mean per-trade effect (e.g., mean Δ PnL between candidate and baseline)
- σ = per-trade standard deviation of the effect
- N = trades per window

When SNR < 1, noise exceeds signal and the window metric is uninformative.

### 1.2 Empirical Evidence (V10/V11)

The V10/V11 validation provides concrete numbers:

| Parameter | harsh scenario | base scenario |
|-----------|---------------|---------------|
| True mean effect (μ) | $418/trade | -$263/trade |
| Per-trade σ | $2,442 | $3,369 |
| Trades per window (median) | 9 | 8 |
| SE per window | $814 | $1,123 |
| **SNR per window** | **0.48** | **0.23** |
| Windows with CI containing 0 | 7 of 8 | 7 of 8 |
| Windows dominated by 1–2 tail trades | 7–8 of 8 | 8 of 8 |

At SNR = 0.48, a single window observation is essentially a coin flip. The
"jumpiness" in WFO round-by-round results is not regime instability — it is
sampling noise from small N compounded by fat-tailed trade PnL distributions.

### 1.3 Minimum Trade Frequency for Viable WFO

For WFO window-level comparison to detect a strategy difference with standard
confidence (SNR ≥ 2.0), the required trades per window is:

```
N_min = (z × σ / μ)²
```

where z = 2.0 for ~95% confidence of correct sign detection. This yields a
**strategy-specific threshold** — you must estimate σ and μ from data, not assume a
universal constant.

**Practical rule of thumb:** compute σ/|μ| (the coefficient of variation of the
per-trade effect). Then:

| σ / |μ| | N_min per window (SNR ≥ 2) | Assessment |
|---------|---------------------------|------------|
| < 3 | < 36 | WFO may work with 6-month windows |
| 3–6 | 36–144 | WFO underpowered; trade-level methods needed |
| 6–10 | 144–400 | WFO impractical; trade-level is primary |
| > 10 | > 400 | Effect likely not real or not measurable |

For V10/V11: σ/|μ| = 2442/418 = 5.8 (harsh) and 3369/263 = 12.8 (base). Both fall
firmly in the "WFO underpowered" or "impractical" zone.

### 1.4 Three Specific Failure Modes

**Failure 1: Information destruction.** Compressing N trades into one window metric
(score, return, Sharpe) destroys the per-trade resolution needed to identify mechanisms.
In V10/V11, 96 trades compressed to 8 active windows (12:1 compression ratio) made it
impossible to identify that the effect was entirely from BULL-regime sizing.

**Failure 2: Data waste.** WFO OOS windows cover only a portion of the backtest period.
Trades outside OOS windows (e.g., the first 2 years of warmup/training) are excluded
from comparison. In V10/V11, 29 of 96 matched trades (30%) fell before the first WFO
window and were lost.

**Failure 3: Equal-weighting bias.** WFO gives each window equal weight regardless of
trade count. A 4-trade window receives the same influence as an 11-trade window,
inflating the contribution of noise-dominated small windows. In V10/V11, WFO SE was
38–61% larger than trade-level SE as a direct result.

---

## Part 2: The Three Replacement Methods

When WFO is underpowered, use the following three methods as the primary validation
framework. They are listed in order of importance.

### Method 1: Trade-Level Paired Analysis + Bootstrap (Primary)

#### What it measures

The per-trade difference between candidate and baseline, aggregated across the full
backtest with proper uncertainty quantification.

#### When to use

Always. This is the primary method for any A-vs-B strategy comparison where both
strategies share similar entry logic (and thus produce matchable trades).

#### Procedure

**Step 1 — Trade matching.** Match candidate trades to baseline trades by entry
timestamp. Use a two-pass algorithm:
1. Exact match on entry_ts
2. Tolerance match (±1 bar) for near-misses caused by exit-timing differences

Report match rate. If match rate is below 80%, the strategies have diverged too much
for paired comparison — they are effectively different strategies and should be
evaluated independently (not differentially).

**Step 2 — Per-trade deltas.** For each matched pair, compute:
- delta_net_pnl, delta_return_pct, delta_fees
- size_ratio (candidate_qty / baseline_qty)
- same_exit_reason (boolean)

**Step 3 — Decomposition.** Decompose each pair's delta_net_pnl into orthogonal
components using first-order Taylor expansion:

| Component | Formula | Measures |
|-----------|---------|----------|
| Exit effect | baseline_qty × (candidate_exit − baseline_exit) | Exit timing/quality change |
| Size effect | (candidate_qty − baseline_qty) × (baseline_exit − baseline_entry) | Position sizing change |
| Fee effect | −(candidate_fees − baseline_fees) | Cost of different sizing |
| Interaction | residual | Cross-term (simultaneous size + exit change) |

This decomposition answers "does the candidate win by better exits, bigger size, or
both?" — critical for understanding whether the improvement is alpha (exit effect) or
leverage (size effect).

**Step 4 — Bootstrap inference.** Run at least two bootstrap methods:

1. **Cluster bootstrap** (semi-annual windows): resample 6-month windows with
   replacement, preserving intra-window trade correlation. Each resampled window
   contributes all its trades.

2. **Moving block bootstrap** (contiguous trade blocks): resample blocks of K
   consecutive trades to preserve temporal autocorrelation. Test multiple block sizes
   (e.g., K = 5, 8, 12) for robustness.

From each bootstrap distribution (≥10,000 samples), report:
- P(candidate > baseline) based on mean delta
- 95% confidence interval of mean delta
- Whether CI excludes zero

**Step 5 — Concentration analysis.** Sort trades by |delta_pnl| and compute:
- What fraction of total delta comes from the top 3, 5, 10 trades?
- Is the median delta near zero?
- Is P(delta > 0) near 50%?

High concentration (top 3 trades > 70% of total) signals that the aggregate result
depends on a few lucky/unlucky trades, not a systematic edge.

#### Pass/fail guidance

The analyst should determine specific thresholds from data context, but these
principles apply:

- **Consistent sign across bootstrap methods** is necessary. If cluster, block, and IID
  bootstrap disagree on direction, the result is too fragile to act on.
- **High concentration with median ≈ 0** means the aggregate looks good but the
  per-trade improvement is absent. This is a warning, not an automatic fail.
- **P(candidate > baseline) near 50%** means individual trades split evenly —
  aggregate advantage comes from tail, not from systematic improvement.
- The exact P-value threshold and CI width that constitute "convincing" depend on the
  decision cost: promoting a marginally better strategy has low cost; replacing
  infrastructure has high cost.

---

### Method 2: Regime-Conditional Decomposition (Mechanism)

#### What it measures

Which market regimes contribute the candidate's advantage (or disadvantage), and
through what mechanism (sizing vs exit quality vs fee structure).

#### When to use

Always, as a complement to Method 1. Method 1 tells you "how much" the candidate
differs; Method 2 tells you "why" and "where."

#### Procedure

**Step 1 — Regime labeling.** Each trade gets four regime labels:
- entry_regime: D1 regime at trade entry
- exit_regime: D1 regime at trade exit
- holding_regime_mode: most common D1 regime during holding period
- worst_regime: highest-severity regime encountered (ranked SHOCK > BEAR > CHOP >
  TOPPING > NEUTRAL > BULL)

Use entry_regime as the primary grouping (it determines the market context the
strategy chose to enter). Use holding_regime_mode as a secondary check.

**Step 2 — Per-regime stats for each strategy.** Group trades by entry_regime and
compute: N, total PnL, mean/median return, hit rate, mean MFE, mean MAE, MFE/MAE
ratio, mean duration, mean fees.

**Step 3 — Per-regime delta from matched pairs.** Group matched pairs by the
baseline's entry_regime and compute: delta_total_pnl, delta_mean_return, P(V_cand >
V_base), and the decomposition sums (exit effect, size effect, fee effect) per regime.

**Step 4 — Contribution waterfall.** Express each regime's delta_total_pnl as a
percentage of the overall total delta. This identifies the "source regimes" — where
the candidate's advantage actually comes from.

**Step 5 — Small-sample flagging.** Any regime with fewer than N_min trades must be
flagged as "low confidence." N_min should be set based on the context; 10 is a
reasonable starting point for exploratory analysis, but claims about a regime with
<20 trades should be treated as hypotheses, not conclusions.

**Step 6 — Deep dive on regimes of interest.** If the candidate was designed to
improve a specific regime (e.g., TOPPING), examine matched trades in that regime
individually: did exit reason change? Did MAE decrease? Did tail losses reduce?

#### Pass/fail guidance

- **Single regime dominance** (>80% of total delta) means the candidate is a
  one-regime play. This is not inherently bad, but it must be disclosed — the
  candidate does not "generally" improve the strategy, it improves it under specific
  market conditions.
- **The candidate should not degrade high-confidence regimes.** If a candidate designed
  for TOPPING improvement causes measurable damage in BULL (the bread-and-butter
  regime), that is a strong negative signal regardless of TOPPING performance.
- **"Zero damage" claims require evidence:** if the candidate claims no harm outside
  its target regime, verify by checking that non-target regime deltas are both small
  in magnitude and have CIs containing zero. A claim of "zero damage" is falsified if
  the candidate loses money in a non-target regime with sufficient sample size.

---

### Method 3: Cross-Scenario Stability Test (Robustness)

#### What it measures

Whether the candidate's advantage persists, shrinks, or reverses when cost assumptions
change.

#### When to use

Always. This is the critical robustness check that WFO cannot perform (WFO runs one
scenario at a time and cannot test cross-scenario consistency).

#### Procedure

**Step 1 — Run Methods 1 and 2 under at least two cost scenarios.** Use the
strategy's standard cost tiers (e.g., base and harsh, or optimistic and pessimistic).
The scenarios should differ meaningfully — if they are too similar, the test has no
discriminating power.

**Step 2 — Compare direction and magnitude across scenarios.**

Key questions:
- Does the sign of the total delta change between scenarios?
- Does the sign of P(candidate > baseline) − 0.5 change?
- Does the dominant regime shift?
- Does the decomposition (exit vs size) rebalance?

**Step 3 — Classify the result.**

| Pattern | Interpretation |
|---------|---------------|
| Same sign, similar magnitude | **Robust** — effect persists across costs |
| Same sign, shrinking magnitude | **Conditionally robust** — effect real but cost-sensitive |
| **Sign reversal** | **Fragile** — effect is an artifact of cost structure, not strategy alpha |
| Same sign, but different mechanism | **Unstable mechanism** — effect exists but for different reasons |

#### Pass/fail guidance

- **Sign reversal is the strongest possible negative signal.** A strategy improvement
  that helps under harsh costs but hurts under base costs (or vice versa) is not a
  real improvement — it is a cost-regime interaction masquerading as alpha. In V10/V11,
  harsh showed +$40k while base showed -$25k, definitively disqualifying V11.
- **Magnitude shrinkage** is expected and acceptable. Higher costs naturally compress
  advantages. The key is that the direction holds.
- **Mechanism stability matters.** If the harsh advantage comes from exit effect but
  the base advantage comes from size effect, the candidate's benefit is fragile even
  if the total sign is stable — different drivers could diverge under future
  conditions.

---

## Part 3: The New Role of WFO

### 3.1 WFO as Supplementary Check

WFO is not abandoned — it is demoted from primary verdict to supplementary diagnostic.

**What WFO still does well:**

1. **Detecting zero-trade periods.** A window with zero trades confirms that the
   strategy's regime gate correctly avoids adverse markets (e.g., 2022 bear for
   long-only BTC). This is valuable safety information that trade-level analysis
   cannot directly provide.

2. **Monitoring regime composition over time.** WFO windows show which regimes dominate
   each half-year, revealing whether the backtest period is regime-representative. A
   period with no TOPPING or no SHOCK exposure means regime-conditional results for
   those regimes are untested.

3. **Catching catastrophic windows.** If any OOS window shows extreme MDD or loss
   beyond strategy tolerance, WFO surfaces it immediately. Trade-level analysis might
   dilute this signal across many trades.

4. **Sanity check on adaptive strategies.** For strategies with per-window parameter
   optimization (unlike V10, which has fixed params), WFO validates that the
   optimization does not overfit each training window. This use case remains valid
   regardless of trade frequency.

### 3.2 When to Ignore WFO Results

Ignore WFO window-level comparison (Δ score, Δ return between strategies) when:

- **More than half of active windows have fewer than N_min trades** (N_min derived from
  σ/|μ| as in Section 1.3). The window-level delta is noise.
- **The scoring function rejects most windows** (e.g., <10 trades → sentinel score).
  When 60%+ of windows are rejected, the "scored rounds" sample is too small and
  biased toward the most active windows.
- **The candidate and baseline produce identical results in most windows.** If
  Δ score = 0 in 80%+ of windows, WFO is not detecting any difference — the 1–2
  non-zero windows are driven by tail trades, not strategy improvement.

In all these cases, report WFO metrics for transparency but base the verdict on
Methods 1–3.

### 3.3 When WFO Results Add Value

Trust WFO window-level metrics when:

- **Median trades per window exceeds the SNR threshold** (from Section 1.3). At this
  point, each window is a meaningful mini-evaluation.
- **Multiple consecutive windows show the same directional effect.** Consistent
  improvement across 4+ independent windows is harder to dismiss as tail-trade noise,
  even with moderate N per window.
- **The strategy has per-window adaptation.** Here, WFO's purpose is overfitting
  detection, not effect-size estimation. Even with low N, observing that adapted
  parameters produce worse OOS results than fixed parameters is diagnostic.

---

## Part 4: Decision Framework

### 4.1 Method Priority

When the three methods give conflicting signals, prioritize as follows:

```
1. Cross-scenario stability  (Method 3)  — highest priority
2. Trade-level bootstrap     (Method 1)  — primary effect estimate
3. Regime decomposition      (Method 2)  — mechanism explanation
4. WFO window-level          (demoted)   — supplementary only
```

**Rationale:** A strategy change that reverses direction under different cost
assumptions (Method 3 fail) cannot be trusted, regardless of how favorable the
bootstrap looks under a single scenario (Method 1). Cost assumptions are inherently
uncertain in live trading — if the effect is not robust to this uncertainty, it is
not actionable.

Within a single scenario, trade-level bootstrap (Method 1) takes priority over regime
decomposition (Method 2) because Method 1 measures the aggregate effect with proper
uncertainty, while Method 2 explains mechanisms that may or may not be statistically
significant.

### 4.2 Conflict Resolution Principles

**Principle 1: Stability over magnitude.** A small, stable improvement across
scenarios and regimes is more valuable than a large improvement that depends on one
scenario or one regime. Prefer consistency over peak performance.

**Principle 2: Mechanism over aggregate.** If the aggregate effect is positive but
the regime decomposition shows it comes entirely from a sizing amplifier (leverage)
rather than better entries or exits (alpha), disclose this clearly. A leverage play
has different risk implications than an alpha improvement — it amplifies both upside
and downside.

**Principle 3: Concentration is a warning.** If >70% of the aggregate advantage comes
from fewer than 5% of trades, the result is fragile. It may be real (some strategies
genuinely produce rare, large wins), but it requires additional evidence before acting
on it — specifically, evidence that the winning pattern is repeatable, not a historical
accident.

**Principle 4: Low-confidence regimes cannot override high-confidence regimes.** A
candidate that improves 4 trades in TOPPING (*LC*) but degrades 56 trades in BULL is
a net negative. The TOPPING improvement is a hypothesis (insufficient data); the BULL
degradation is a finding (sufficient data).

**Principle 5: Burden of proof is on the candidate.** The baseline strategy is in
production. The candidate must demonstrate improvement that is:
- Directionally consistent across cost scenarios
- Not concentrated in a handful of trades
- Not purely a leverage/sizing artifact
- Not harmful to the baseline's strongest regime

If any of these conditions fails, the baseline stays. Doing nothing is always an option
and is often the correct one.

### 4.3 Decision Table

| Method 1 (Bootstrap) | Method 3 (Cross-scenario) | Method 2 (Regime) | Decision |
|----------------------|--------------------------|-------------------|----------|
| P > 90%, CI excl. 0 | Sign stable | Broad-based improvement | **Promote candidate** |
| P > 90%, CI excl. 0 | Sign stable | Single-regime, low concentration | **Promote with caveat** |
| P > 90%, CI excl. 0 | Sign stable | Single-regime, high concentration | **Hold — fragile edge** |
| P > 90%, CI excl. 0 | **Sign reversal** | Any | **Reject candidate** |
| P = 50–90% | Sign stable | Clear mechanism | **Hold — monitor with live data** |
| P = 50–90% | Sign reversal | Any | **Reject candidate** |
| P < 50% | Any | Any | **Reject candidate** |

This table is illustrative, not prescriptive. The analyst should adapt thresholds to
the specific decision context (cost of wrong promotion vs cost of missed improvement).

### 4.4 Reporting Checklist

Every validation report should contain:

- [ ] Match rate and matching method
- [ ] Per-trade delta distribution: mean, median, P(>0), concentration (top-3 share)
- [ ] Decomposition: exit effect vs size effect vs fee effect (with sums and %)
- [ ] Bootstrap: P(candidate > baseline) and 95% CI, for at least 2 methods
- [ ] Regime waterfall: which regimes contribute what % of total delta
- [ ] Small-sample flags for all regimes below N_min
- [ ] Cross-scenario table: sign, magnitude, mechanism stability
- [ ] WFO trade count per window and SNR assessment
- [ ] Deep-dive on any regime the candidate was specifically designed to improve
- [ ] Explicit verdict with supporting evidence from each method

---

## Appendix A: Empirical Basis

All quantitative thresholds and principles in this document derive from the V10/V11
validation campaign. Key reference numbers:

| Parameter | Value | Source |
|-----------|-------|--------|
| V10 trade frequency | ~14 trades/year (103 in 7 years) | trades_v10_harsh.csv |
| WFO window trades (median) | 9 | wfo_trade_level_bridge.py |
| Per-trade σ(Δ PnL) | $2,442 (harsh), $3,369 (base) | paired_analysis.py |
| Per-trade mean(Δ PnL) | +$418 (harsh), -$263 (base) | paired_analysis.py |
| Window SNR | 0.48 (harsh), 0.23 (base) | wfo_trade_level_bridge.py |
| N needed for SNR=2 | 136 (harsh), 656 (base) | derived |
| Match rate | 93.2% (harsh), 95.0% (base) | paired_analysis.py |
| Top-3 trade concentration | 78% of harsh total delta | paired_analysis.py |
| Median per-trade delta | ~$0 | paired_analysis.py |
| P(V11 > V10 per trade) | ~50% | paired_analysis.py |
| Cross-scenario sign | Reversal (+$40k harsh, -$25k base) | paired_analysis.py |
| BULL regime share of delta | 93.4% (harsh) | regime_comparison.py |
| WFO SE / trade SE ratio | 1.38–1.61× | wfo_trade_level_bridge.py |
| Pre-WFO data waste | 30% of matched trades excluded | wfo_trade_level_bridge.py |

## Appendix B: Script Inventory

| Script | Purpose |
|--------|---------|
| `out_trade_analysis/export_trades.py` | Generate per-trade CSVs with regime/MFE/MAE |
| `out_trade_analysis/paired_analysis.py` | Match trades, decompose deltas, export pairs |
| `out_trade_analysis/bootstrap_paired.py` | Cluster + block + IID bootstrap inference |
| `out_trade_analysis/regime_comparison.py` | Per-regime stats + delta + TOPPING deep-dive |
| `out_trade_analysis/wfo_trade_level_bridge.py` | Map trades to WFO windows, prove noise |

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **SNR** | Signal-to-noise ratio: |μ| / SE. Values <1 mean noise exceeds signal |
| **Cluster bootstrap** | Resample groups (windows) with replacement, preserving within-group correlation |
| **Block bootstrap** | Resample contiguous blocks of observations to preserve autocorrelation |
| **Exit effect** | PnL change attributable to different exit prices, holding position size constant |
| **Size effect** | PnL change attributable to different position sizes, holding exit constant |
| **Concentration** | Fraction of total delta attributable to the top-N largest trades |
| **Match rate** | Fraction of baseline trades that pair with a candidate trade by entry time |
| **N_min** | Minimum sample size below which a regime or window is flagged "low confidence" |
| **Low confidence (LC)** | Regime or window with fewer than N_min trades — directional only, not conclusive |
| **Cross-scenario stability** | Whether the candidate's advantage holds (same sign) across different cost assumptions |
