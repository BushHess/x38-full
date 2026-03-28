# x39 Formal Validation Spec — Vol Compression Gate

## Status: PENDING

## Context

52 x39 experiments yielded exactly ONE WFO-validated mechanism: **vol compression
entry gate** (exp34/42/52). Before concluding that E5-ema21D1 + vol compression
is a genuine improvement, 4 unresolved issues must be addressed:

| # | Issue | Risk | Source |
|---|-------|------|--------|
| 1 | x39 used simplified replay, not formal v10 engine | Results may not reproduce with proper fill/cost model | exp34/42/52 |
| 2 | MDD worsens at thr=0.6 (+2.27pp) | Sharpe gain may come at unacceptable risk cost | exp34 |
| 3 | 52 experiments = selection pressure | 1/52 winner may be false positive (multiple testing) | x39 overall |
| 4 | Formal validation pipeline (7 gates) never ran | No Tier-2 machine verdict exists | — |

This spec defines 5 phases to resolve ALL issues in a single study.

---

## Phase 1: Strategy Implementation

### Goal
Create `vtrend_e5_ema21_d1_vc` as a proper v10 Strategy subclass.

### Design
Fork `strategies/vtrend_e5_ema21_d1/strategy.py`. Changes:

1. **Config**: add `compression_threshold: float = 0.6` to dataclass.
   Add `compression_fast: int = 5` and `compression_slow: int = 20` (structural,
   not tunable — document as fixed).

2. **on_init()**: compute `vol_ratio_5_20` array:
   ```python
   std_fast = _rolling_std(close, self._c.compression_fast)
   std_slow = _rolling_std(close, self._c.compression_slow)
   self._vol_ratio = std_fast / np.where(std_slow > 1e-10, std_slow, np.nan)
   ```
   Use `numpy` rolling std matching `pd.Series.rolling(k, min_periods=k).std()`.

3. **on_bar() entry**: add gate after existing conditions:
   ```python
   # Existing: trend_up AND vdo > threshold AND regime_ok AND not monitor_red
   # Add:      AND vol_ratio < compression_threshold
   vol_r = self._vol_ratio[i]
   if math.isnan(vol_r) or vol_r >= self._c.compression_threshold:
       return None  # compression gate blocks entry
   ```

4. **Exit logic**: UNCHANGED (trail stop + EMA cross-down).

5. **reason strings**: `"vtrend_e5_ema21_d1_vc_entry"`, `"..._trail_stop"`, `"..._trend_exit"`.

### Artifacts
- `strategies/vtrend_e5_ema21_d1_vc/strategy.py`
- `strategies/vtrend_e5_ema21_d1_vc/__init__.py`
- `configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml`
  (copy E5-ema21D1 config, add `compression_threshold: 0.6`)
- Register in `validation/strategy_factory.py` STRATEGY_REGISTRY

### Validation
- `python -m pytest` passes (no regressions)
- Backtest runs without errors on full data

---

## Phase 2: Reproduction Check

### Goal
Quantify discrepancy between x39 simplified replay and formal v10 engine.
If discrepancy > 10% on any primary metric, diagnose root cause.

### Known x39-vs-v10 differences

| Aspect | x39 Replay | v10 Engine | Expected Impact |
|--------|-----------|------------|-----------------|
| Fill timing | Bar close | Next-bar open | ~4h shift, small |
| Cost model | Flat bps symmetric | CostConfig scenario | Comparable at 50 bps |
| Sharpe annualization | `sqrt(252)` daily | `sqrt(bars_per_year)` H4 | Denominator differs |
| Position at window end | Force-close | Carries forward | WFO window edges |
| MTF alignment | Manual loop | Strict `<` check | Fixed in 2026-03-16 |
| Warmup | Hard +120 bars | DataFeed report_start_ms | Edge effects |

### Procedure

**Step 2a — Baseline reproduction**:
1. Run E5-ema21D1 through v10 engine (harsh, full period 2019-01 to 2026-02,
   warmup 365 days). Record: Sharpe, CAGR, MDD, trades, exposure.
2. Compare with x39 baseline: Sharpe ~1.30, trades ~221.
   Note: x39 baseline differs from formal E5-ema21D1 (Sharpe 1.4545) due to
   simplified replay. The DELTA should be comparable, not the absolute level.

**Step 2b — Compression reproduction**:
1. Run `vtrend_e5_ema21_d1_vc` (thr=0.6) through v10 engine, same conditions.
2. Compute d_Sharpe vs Step 2a baseline.
3. Compare with x39 d_Sharpe: +0.1901 (exp34), +0.2625 mean WFO (exp42).

**Step 2c — Discrepancy analysis**:

| Metric | x39 Value | v10 Value | Delta | Acceptable? |
|--------|-----------|-----------|-------|-------------|
| d_Sharpe (full) | +0.1901 | ? | ? | Within ±30% |
| d_MDD (full) | +2.27pp | ? | ? | Same sign |
| d_Trades | -24 | ? | ? | Within ±5 |
| Blocked WR gap | ~7pp | ? | ? | Same sign |

**Acceptable discrepancy**: d_Sharpe within ±30% of x39 value AND same sign on
all deltas. If outside range, diagnose before proceeding.

**Root cause diagnostic** (if discrepancy > threshold):
- Compare trade-by-trade: entry bar, exit bar, net return per trade
- Identify which trades differ (fill timing vs cost model vs MTF alignment)
- Report specific bars where x39 and v10 diverge

---

## Phase 3: Formal Validation Pipeline (7 Gates)

### Goal
Run the Tier-2 machine validation pipeline for `vtrend_e5_ema21_d1_vc`
against baseline `vtrend_e5_ema21_d1`. Obtain PROMOTE/HOLD/REJECT verdict.

### Configuration

**Candidate**: `vtrend_e5_ema21_d1_vc` with `compression_threshold: 0.6`
**Baseline**: `vtrend_e5_ema21_d1` (current primary, HOLD status)
**Suite**: `all` (full suite — all 7 gates)
**Cost**: harsh (50 bps RT)

```bash
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1_vc \
  --baseline vtrend_e5_ema21_d1 \
  --config configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_default.yaml \
  --baseline-config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --out results/full_eval_e5_ema21d1_vc_06 \
  --suite all
```

### Expected gate outcomes (predictions based on x39 evidence)

| Gate | Type | Prediction | Reasoning |
|------|------|------------|-----------|
| G1: Lookahead | Hard | PASS | No future data used (rolling std on past bars only) |
| G2: Full harsh delta | Hard | PASS | d_Sharpe >> -0.2 (expect ~+0.19) |
| G3: Holdout harsh delta | Hard | PASS | exp42 W4 (2024-07→2026-02) showed +0.19 d_Sharpe |
| G4: WFO robustness | Soft | **UNCERTAIN** | x39 WFO 4/4 BUT v10 uses Wilcoxon p ≤ 0.10 on N=8 windows. Power concern: at N=8, min p ≈ 0.004, but magnitude of d_Sharpe varies. |
| G5: Trade-level bootstrap | Soft | Conditional | Only active if G4 low-power. Expect P(E5vc > E5) high. |
| G6: Selection bias | Soft | **KEY GATE** | See Phase 4 below. DSR with N=52 trials. |
| G7: Bootstrap info | Info | No veto | Diagnostic only. |

### Critical: G4 WFO Robustness

v10's WFO uses **8 anchored windows** (not x39's 4). The Wilcoxon signed-rank test
requires sufficient non-zero pairs. At N=8, need W+ >= 28/36 for p <= 0.10.

x39's evidence (4/4 windows, mean d_Sharpe +0.26, all positive) is encouraging but
not directly transferable to v10's 8-window WFO. The question is whether the
d_Sharpe remains consistently positive across ALL 8 windows.

If G4 FAILS (Wilcoxon p > 0.10): same situation as E5-ema21D1's current HOLD
(underresolved WFO). In this case, G5 trade-level bootstrap becomes binding.

### Secondary run: thr=0.7

After thr=0.6, repeat with `compression_threshold: 0.7`:

```bash
python validate_strategy.py \
  --strategy vtrend_e5_ema21_d1_vc \
  --baseline vtrend_e5_ema21_d1 \
  --config configs/vtrend_e5_ema21_d1_vc/vtrend_e5_ema21_d1_vc_07.yaml \
  --baseline-config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \
  --out results/full_eval_e5_ema21d1_vc_07 \
  --suite all
```

### Comparison table (fill after runs)

| Metric | thr=0.6 | thr=0.7 | Winner |
|--------|---------|---------|--------|
| Pipeline verdict | ? | ? | ? |
| G4 Wilcoxon p | ? | ? | ? |
| Full d_Sharpe | ? | ? | ? |
| Full d_MDD | ? | ? | ? |
| Holdout d_Sharpe | ? | ? | ? |
| DSR p-value | ? | ? | ? |

---

## Phase 4: Multiple Testing Correction (Selection Bias)

### Problem

52 experiments explored → 1 winner found. Classic multiple comparisons problem.
Even if each experiment has p=0.05 false positive rate, P(at least 1 false
positive in 52 trials) = 1 - (0.95)^52 = 93%.

However, the situation is more nuanced:
1. WFO validation (exp42) is OUT-OF-SAMPLE — partially addresses selection bias
2. Not all 52 experiments are independent (many share features/mechanisms)
3. The validation pipeline's Gate 6 already computes DSR/PBO

### Approach: Three-layer correction

**Layer 1: DSR (Deflated Sharpe Ratio)**

Use `research/lib/dsr.py` to compute the deflated Sharpe accounting for 52 trials.

```python
from research.lib.dsr import compute_dsr

# Use the v10 backtest returns from Phase 3
result = compute_dsr(
    returns=candidate_returns,       # daily/bar-level returns
    num_trials=52,                   # full x39 trial count
    bars_per_year=6 * 365.25,        # H4 bars per year
)
# Key output: result["dsr_pvalue"]
# If dsr_pvalue < 0.05: survives multiple testing correction
```

**Expected outcome**: At Sharpe ~1.49 with 52 trials and ~16,000 H4 bars,
SR₀ (expected max under null) ≈ 0.35-0.45 annualized. Candidate SR is ~1.49,
so DSR should comfortably pass. But this needs confirmation with real numbers.

**Layer 2: Effective DOF correction**

Not all 52 experiments are independent. Many share:
- Same baseline (E5-ema21D1)
- Same features (rangepos, trendq, vol_ratio used across multiple experiments)
- Sequential design (exp42 builds on exp34, exp49 builds on exp44)

Use `research/lib/effective_dof.py` to estimate M_eff < 52:

Procedure:
1. Construct 52×52 correlation matrix of experiment d_Sharpe vectors
   (where experiments share WFO windows, compute correlation of per-window deltas).
2. For experiments without WFO data, use binary outcome correlation
   (PASS=1, FAIL=0) as proxy.
3. Compute M_eff via Nyholt/Li-Ji/Galwey methods.
4. Re-run DSR with `num_trials=M_eff` (conservative estimate).

Expected: M_eff ≈ 15-25 (many experiments are clustered: exit variants exp19-31,
entry timing exp32-39, combos exp43-47). This strengthens the DSR result.

**Layer 3: WFO as independent validation**

The strongest argument against selection bias: exp42's WFO was designed to test
a SPECIFIC mechanism (vol compression) on HELD-OUT temporal windows. The 4/4
result is not part of the 52-experiment selection — it's an independent test.

However, analyst degrees of freedom exist:
- Window definitions chosen by analyst
- threshold options (0.5-1.0) optimized in-sample
- Decision to test vol compression (not another feature) was informed by exp34

To quantify analyst DOF:
- Count: how many features COULD have been selected after explore.py scan? → 9
- Count: how many were submitted to WFO? → 4 (exp30 AND-gate, exp31 velocity,
  exp41 accel, exp42 compression)
- Effective WFO trials: 4 (not 52)
- Bonferroni-corrected α for WFO: 0.05 / 4 = 0.0125

At 4/4 windows (all positive), the probability of this under H₀ (random, p=0.5
per window) is (0.5)^4 = 0.0625. With Bonferroni correction for 4 WFO tests:
p_corrected = 4 × 0.0625 = 0.25. **This does NOT survive Bonferroni at α=0.05.**

BUT: v10's formal WFO uses 8 windows with Wilcoxon test (not binary win count).
If 8/8 positive: p = (0.5)^8 = 0.0039, Bonferroni-corrected = 4 × 0.0039 = 0.016.
**This WOULD survive.**

### Decision matrix

| Scenario | DSR | WFO (v10 G4) | Conclusion |
|----------|-----|--------------|------------|
| DSR PASS, WFO PASS | Strong | Strong | **PROMOTE** — multiple testing survived |
| DSR PASS, WFO FAIL | Strong | Weak | **HOLD** — same as current E5, WFO underresolved |
| DSR FAIL, WFO PASS | Weak | Strong | **HOLD** — in-sample inflated, but OOS is real |
| DSR FAIL, WFO FAIL | Weak | Weak | **REJECT** — likely false positive from 52 trials |

### Output
- `results/full_eval_e5_ema21d1_vc_06/x39_multiple_testing.json`:
  ```json
  {
    "n_experiments": 52,
    "m_eff_nyholt": null,
    "m_eff_liji": null,
    "m_eff_galwey": null,
    "dsr_pvalue": null,
    "dsr_sr0_annualized": null,
    "wfo_tests_submitted": 4,
    "wfo_bonferroni_alpha": 0.0125,
    "analyst_dof_assessment": "..."
  }
  ```

---

## Phase 5: MDD Trade-Off Analysis

### Problem
At thr=0.6: d_Sharpe = +0.19, d_MDD = +2.27pp (worse)
At thr=0.7: d_Sharpe = +0.18, d_MDD = +0.42pp (nearly neutral)

Is the MDD degradation acceptable?

### Analysis (using v10 formal backtest results from Phase 3)

**5a. MDD context**:
- Baseline MDD: ~41% (E5-ema21D1 formal). Adding +2.27pp → ~43%.
- Is 43% vs 41% MDD meaningful? Need confidence interval.
- Bootstrap MDD distribution from VCBB: if MDD CI already spans ±5pp,
  then +2.27pp is within noise.

**5b. Risk-adjusted comparison**:
- Calmar ratio = CAGR / MDD
  - thr=0.6: CAGR ~68.4% / MDD ~43.2% = Calmar ~1.58
  - thr=0.7: CAGR ~68.2% / MDD ~41.4% = Calmar ~1.65
  - Baseline: CAGR ~61.6% / MDD ~41.0% = Calmar ~1.50
- Both thresholds improve Calmar over baseline. thr=0.7 has better Calmar.

**5c. MDD regime decomposition**:
- Which WFO windows contribute to MDD increase?
- If MDD increase is concentrated in 1 window (e.g., 2022 bear), it may be
  an artifact of that specific period, not a structural issue.

**5d. Cost-adjusted recommendation**:
From exp52, at realistic costs (15-25 bps):
- d_Sharpe is ~91% of 50-bps value → genuine
- d_MDD pattern likely similar but should be verified with v10

### Decision criteria

| Criterion | thr=0.6 preferred | thr=0.7 preferred |
|-----------|-------------------|-------------------|
| Max Sharpe | Yes (+0.01) | |
| Min MDD | | Yes (-1.85pp) |
| Best Calmar | | Yes (+0.07) |
| Parameter safety | | Yes (less aggressive) |
| WFO consistency | Similar | Similar |

**Default recommendation**: thr=0.7 unless Phase 3 shows thr=0.6 passing G4
and thr=0.7 failing G4.

---

## Execution Order

```
Phase 1 (implementation)     ← prerequisite for all
  ↓
Phase 2 (reproduction check) ← validates implementation correctness
  ↓
Phase 3a (formal validation thr=0.6) ─┬─ can run in parallel
Phase 3b (formal validation thr=0.7) ─┘
  ↓
Phase 4 (multiple testing)   ← uses Phase 3 outputs
  ↓
Phase 5 (MDD analysis)       ← uses Phase 3 outputs
  ↓
Final verdict
```

**Estimated effort**: Phase 1 (~30 min), Phase 2 (~20 min), Phase 3 (~40 min
× 2 runs), Phase 4 (~30 min), Phase 5 (~20 min). Total: ~3 hours.

---

## Final Verdict Criteria

After all 5 phases complete, the conclusion is:

### CONCLUDE (vol compression IS a genuine improvement) if ALL:
1. Phase 2: d_Sharpe reproduces within ±30% of x39 value, same sign on all deltas
2. Phase 3: at least ONE threshold (0.6 or 0.7) achieves PROMOTE (exit 0) or
   HOLD with only G4 failing (same as current E5-ema21D1 status)
3. Phase 4: DSR p < 0.05 (layer 1), AND [M_eff-corrected DSR also < 0.05 OR
   v10 WFO Wilcoxon p < 0.0125 (Bonferroni-corrected for 4 WFO tests)]
4. Phase 5: Calmar ratio improves over baseline for chosen threshold

### REJECT (vol compression is a false positive) if ANY:
1. Phase 2: d_Sharpe reverses sign (negative) in v10 engine
2. Phase 3: REJECT verdict (hard gate failure)
3. Phase 4: DSR p > 0.10 AND v10 WFO FAIL — both layers fail
4. Phase 5: Calmar ratio degrades (MDD increase outweighs Sharpe gain)

### INCONCLUSIVE (need more data/research) if:
1. Phase 3: HOLD verdict with underresolved WFO (same as current E5)
2. Phase 4: DSR PASS but WFO FAIL — selection bias cleared but temporal
   stability unconfirmed
3. Compression improves the strategy but the strategy itself remains HOLD

In the INCONCLUSIVE case, the compression finding is PRESERVED as the next
mechanism to deploy when the WFO power problem is resolved (more OOS data,
or alternative validation method).

---

## Appendix A: vol_ratio_5_20 Feature Specification

```
Input:   close[0..N-1] — H4 close prices
Output:  vol_ratio[0..N-1]

std_fast[i] = sample_std(close[i-4:i+1])          # 5-bar window, min_periods=5
std_slow[i] = sample_std(close[i-19:i+1])         # 20-bar window, min_periods=20
vol_ratio[i] = std_fast[i] / std_slow[i]          # NaN if std_slow ≤ 1e-10

Interpretation:
  < 0.5  — strong compression (recent vol < 50% of medium-term)
  0.5-0.7 — moderate compression (entry zone for thr=0.6/0.7)
  0.7-1.0 — normal volatility
  > 1.0  — expansion (recent vol > medium-term — breakout or spike)

Gate logic:
  ALLOW entry when vol_ratio < compression_threshold
  BLOCK entry when vol_ratio >= compression_threshold OR NaN
```

## Appendix B: _rolling_std Implementation

Must match pandas `rolling(k, min_periods=k).std()` (ddof=1, sample std):

```python
def _rolling_std(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample standard deviation matching pandas default (ddof=1)."""
    n = len(series)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        chunk = series[i - window + 1 : i + 1]
        out[i] = np.std(chunk, ddof=1)
    return out
```

Optimize with cumulative sum if needed, but correctness first.

## Appendix C: Existing x39 Evidence Summary

| Experiment | Type | d_Sharpe | WFO | Key Finding |
|-----------|------|----------|-----|-------------|
| exp34 | Full-sample sweep | +0.1901 (thr=0.6) | — | Selectivity confirmed |
| exp42 | WFO (4 windows) | +0.2625 mean | 4/4 | Temporal stability |
| exp50 | Alt measures | — | — | Only vol_ratio_5_20 works |
| exp52 | Cost sweep | +0.173 (15bps) | — | Cost-independent |
