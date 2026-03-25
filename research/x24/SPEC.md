# X24 SPEC: Trail Arming Isolation

## 1. Study ID & Metadata

| Field | Value |
|-------|-------|
| Study ID | X24 |
| Title | Trail Arming Isolation |
| Location | `research/x24/` |
| Baseline | E5+EMA1D21 (trail=3.0, robust ATR) |
| Data | `data/bars_btcusdt_2016_now_h1_4h_1d.csv` |
| Period | 2019-01-01 to 2026-02-20, warmup 365 days |
| Cost | 50 bps RT (harsh scenario) |
| DOF budget | 0 tuned params (k preset by mathematical argument) |
| Prerequisite | X23 (pullback distribution data), trail_sweep (monotonic tradeoff) |


## 2. Mathematical Foundation

### 2.1. Problem statement

Trail sweep (`trail_sweep.py`) tested trail multiplier m in [2.0, 5.0] and found
a monotonic return/risk tradeoff: lower m increases CAGR but worsens MDD. No m
dominates m=3.0 on all metrics.

Trail arming delays trail activation until MFE >= k * rATR_entry. The question:
is this merely an obfuscated form of trail sweep, or is it a structurally
different intervention?

If trail arming is equivalent to some trail multiplier m', there is no reason
to pursue X24 — trail_sweep already covered the space. This section proves
the two are not equivalent.

### 2.2. Formal definitions

**Trail sweep E5(m)**: At every in-position bar t:

    S_t = peak_t - m * rATR_t
    exit if cl_t < S_t

**Trail arming E5+ARM(k, m)**: At every in-position bar t:

    MFE_t = peak_t - entry_px
    armed_t = 1{MFE_t >= k * rATR_entry}

    if armed_t:
        S_t = peak_t - m * rATR_t
        exit if cl_t < S_t
    else:
        no trail check (only trend exit active)

All other logic (entry, trend exit, indicators) identical.

### 2.3. Proposition

For any k > 0 and m > 0, there exists no m' >= 0 such that E5(m') and
E5+ARM(k, m) produce identical trade sequences on all price paths.

### 2.4. Proof

We construct two price paths from the same entry at price E with rATR = A
(constant for clarity). Take ε = 0.1A (any small positive value works).

**Path 1** (low MFE): price rises to E + (k - ε), establishing
peak P₁ = E + (k - ε). Then price drops to P₁ - (m + ε).

- ARM(k, m): MFE = (k - ε) < k·A → trail NOT armed → no trail exit.
- E5(m'): trail = P₁ - m'·A. Exit iff price < trail, i.e., m' < m + ε.
- For E5(m') to match ARM (no exit): require m' >= m + ε.

**Path 2** (high MFE): price rises to E + (k + ε), establishing
peak P₂ = E + (k + ε) and arming the trail. Then price drops to
P₂ - (m + ε).

- ARM(k, m): trail armed (MFE = k + ε >= k). Trail = P₂ - m·A.
  Price = P₂ - (m + ε) < P₂ - m = trail. EXIT.
- E5(m'): trail = P₂ - m'·A. Exit iff price < trail, i.e., m' < m + ε.
- For E5(m') to match ARM (exit): require m' < m + ε.

Combining: Path 1 requires m' >= m + ε, Path 2 requires m' < m + ε.
Contradiction. ∎

### 2.5. Operational interpretation

Trail arming creates a **path-dependent binary regime** within each trade:

- **Phase 1** (MFE < k·A_E): no trail stop. Trade can only exit via
  EMA cross-down. The trail exists conceptually but is not evaluated.
  Equivalent locally to m = ∞.

- **Phase 2** (MFE >= k·A_E): standard trail at m·rATR. Equivalent
  locally to E5(m).

No single m' can replicate m = ∞ in Phase 1 and m = 3.0 in Phase 2
simultaneously. This is the structural difference from trail sweep.

Trail sweep is **stateless**: same m at all bars. Trail arming is
**trade-phase-dependent**: the effective m depends on the trade's history.

### 2.6. What X23 pullback data tells us

X23 T2 measured healthy pullback depths on E5 baseline trades:

    State   Q50    Q75    Q90
    normal  0.753  1.587  2.270
    strong  0.914  1.673  2.375

The current trail at m=3.0 sits beyond Q90 of healthy pullbacks. This means
fewer than 10% of healthy pullbacks are deep enough to trigger the trail.

Yet E5 has 183 trail stop exits with 64.5% churn rate (118 churn exits).
This apparent contradiction has two possible explanations:

(a) **Churn is drift-driven**: BTC's upward drift causes recovery after
    nearly any trail stop, regardless of whether the stop was "correct."
    Trail arming cannot fix this — it's structural to the asset.

(b) **Early-phase trail stops are noise-driven**: trades with low MFE
    (price hasn't moved far from entry) have the trail at approximately
    entry - m·A, and normal noise can push price through. These stops
    are disproportionately churn.

If (b) holds, trail arming targets the right subset. X24's pre-flight
diagnostic (T0) tests this directly.

### 2.7. Choice of k

The preset arming threshold is:

    k = m / 2 = 1.5

Justification: at MFE = m/2, the trail stop is at:

    trail = peak - m·A ≈ (entry + m/2·A) - m·A = entry - m/2·A

This is the point where trail protection covers a loss of m/2 rATR units
below entry — exactly half the trail width. It is a scale-invariant choice
(k/m = 0.5 regardless of m) that does not require fitting.

Alternative values k ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0} are tested in a
characterization sweep (T2) but do NOT contribute to gate decisions.


## 3. Hypothesis

**H₀**: E5+ARM(k=1.5, m=3.0) produces identical risk-adjusted returns to E5(m=3.0).

**H₁**: Delaying trail activation until MFE >= 1.5·rATR_entry improves
risk-adjusted returns by eliminating noise-driven trail stops in the
early phase of trades, without introducing compensating drawdown.


## 4. File Layout

```
research/x24/
├── SPEC.md              # This document
├── benchmark.py         # Main benchmark script
├── x24_results.json     # Machine-readable results (generated)
└── x24_report.md        # Human-readable report (generated)
```


## 5. Constants

```python
# === Data & Period ===
DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

# === Indicator parameters (frozen from E5+EMA1D21) ===
SLOW = 120
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
D1_EMA_P = 21

# === ATR parameters ===
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

# === Trail ===
TRAIL = 3.0                             # E5 trail multiplier (unchanged)

# === X24 arming parameter (PRESET, ZERO TUNED) ===
ARM_K = 1.5                             # trail arms when MFE >= ARM_K * rATR_entry

# === k-sweep (characterization only, no gate) ===
K_SWEEP = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# === Churn ===
CHURN_WINDOW = 20

# === Cost ===
CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

# === Validation ===
WFO_FOLDS = [
    ("2021-12-31", "2022-01-01", "2022-12-31"),
    ("2022-12-31", "2023-01-01", "2023-12-31"),
    ("2023-12-31", "2024-01-01", "2024-12-31"),
    ("2024-12-31", "2025-01-01", "2026-02-20"),
]
JK_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
N_BOOT = 500
BLKSZ = 60
SEED = 42
E0_EFFECTIVE_DOF = 4.35
```


## 6. Indicator Functions

All indicator functions identical to X23/X18. Copied verbatim:

- `_ema(series, period)` — lfilter-based EMA
- `_robust_atr(high, low, close, ...)` — cap TR at rolling Q90, Wilder EMA
- `_vdo(close, high, low, volume, taker_buy, fast, slow)` — volume delta oscillator
- `_compute_indicators(cl, hi, lo, vo, tb)` — returns (ef, es, vd) [no standard ATR needed]
- `_compute_ratr(hi, lo, cl)` — convenience wrapper for robust ATR
- `_compute_d1_regime(h4_ct, d1_cl, d1_ct)` — boolean D1 regime mapped to H4
- `_compute_d1_regime_str(...)` — not needed (no score model)

Note: X24 does NOT use the logistic score model. No standard ATR, no features,
no model training. This eliminates a major source of complexity from X23.


## 7. E5 Baseline Sim: `_run_sim_e5()`

Identical to X23 Section 8 / X18's `_run_sim_e0()` with robust ATR.

```python
def _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
    # Entry: ef > es AND vd > VDO_THR AND regime_h4
    # Exit:  cl < peak - trail_mult * ratr  OR  ef < es
    # Returns (nav, trades)
```

Trade dict fields (unchanged from X23):
```python
{
    "entry_bar": int,
    "exit_bar": int,
    "entry_px": float,
    "exit_px": float,
    "peak_px": float,
    "peak_bar": int,
    "pnl_usd": float,
    "ret_pct": float,
    "bars_held": int,
    "exit_reason": str,     # "trail_stop" | "trend_exit" | "end_of_data"
}
```


## 8. E5+ARM Sim: `_run_sim_e5_arm()` — Core New Code

### 8.1. Function signature

```python
def _run_sim_e5_arm(cl, ef, es, vd, ratr, regime_h4, wi,
                     trail_mult=TRAIL, arm_k=ARM_K, cps=CPS_HARSH):
    """
    E5 + trail arming: trail only active after MFE >= arm_k * rATR_entry.
    No hard stop. No state conditioning. No score model.

    Returns (nav, trades, stats).
    """
```

### 8.2. Additional state variables (beyond E5)

```python
# At entry:
entry_ratr = 0.0            # rATR at signal bar (ratr[i-1])
trail_armed = False
trail_arm_bar = -1

# Running:
# peak already tracked in E5; reused for MFE = peak - entry_px
```

### 8.3. Entry logic (UNCHANGED from E5)

```
if FLAT and ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
    → pending entry
```

At fill (next bar):
```python
entry_px = cl[i-1]              # fill price
entry_ratr = ratr[i-1]          # rATR at signal bar
trail_armed = False
trail_arm_bar = -1
peak = cl[i]
```

### 8.4. Per-bar logic (in position)

```python
# Update peak (same as E5)
peak = max(peak, p)
if p >= peak:
    peak_bar = i

# Update MFE and trail arming
mfe = peak - entry_px
if not trail_armed and not np.isnan(entry_ratr) and entry_ratr > 0:
    if mfe >= arm_k * entry_ratr:
        trail_armed = True
        trail_arm_bar = i
        stats["n_arm_events"] += 1

# EXIT CHECK 1: Trend failure (always active)
if ef[i] < es[i]:
    exit_reason = "trend_exit"
    pending_exit = True
    continue

# EXIT CHECK 2: Trail stop (only when armed)
if trail_armed:
    trail_level = peak - trail_mult * ratr[i]
    if p < trail_level:
        exit_reason = "trail_stop"
        pending_exit = True
```

Key differences from E5:
- No hard stop (removed from X23)
- No state conditioning (removed from X23)
- Trail check gated by `trail_armed` flag
- Trend exit checked BEFORE trail (same priority, but irrelevant since
  they're independent conditions)

Key difference from X23:
- No hard stop at all. Phase 1 has only trend exit as protection.
- No score model. No feature extraction. No state bucketing.

### 8.5. Exit priority

1. Trend failure (always active, checked first)
2. Trail stop (only when armed, checked second)

Only one exit per bar. First matching condition wins.

Note: trend exit is checked FIRST because it is always active. If both
trend and trail fire on the same bar, trend takes priority. This is
semantically correct: trend reversal is a stronger signal than trail breach.

### 8.6. Stats dict

```python
stats = {
    "n_trades": int,
    "n_trail_stop": int,
    "n_trend_exit": int,
    "n_end_of_data": int,
    "n_arm_events": int,
    "n_never_armed": int,       # trades that exited before trail armed
}
```

### 8.7. Extended trade dict

```python
{
    # Standard fields (same as E5)
    "entry_bar", "exit_bar", "entry_px", "exit_px",
    "peak_px", "peak_bar", "pnl_usd", "ret_pct",
    "bars_held", "exit_reason",

    # X24-specific fields
    "trail_armed": bool,        # was trail armed before exit?
    "trail_arm_bar": int,       # bar where trail armed (-1 if never)
    "mfe_atr": float,           # MFE / rATR_entry at exit
}
```

### 8.8. Complete pseudocode

```python
for i in range(n):
    p = cl[i]

    if i > 0:
        fp = cl[i - 1]
        if pending_entry:
            pending_entry = False
            entry_px = fp
            entry_bar = i
            entry_ratr = ratr[i - 1]
            bq = cash / (fp * (1 + cps))
            entry_cost = bq * fp * (1 + cps)
            cash = 0.0
            in_position = True
            trail_armed = False
            trail_arm_bar = -1
            peak = p
            peak_bar = i

        elif pending_exit:
            pending_exit = False
            received = bq * fp * (1 - cps)
            pnl = received - entry_cost
            mfe_at_exit = (peak - entry_px) / entry_ratr \
                if entry_ratr > 1e-12 else 0.0
            if not trail_armed:
                stats["n_never_armed"] += 1
            trades.append({
                "entry_bar": entry_bar, "exit_bar": i,
                "entry_px": entry_px, "exit_px": fp,
                "peak_px": peak, "peak_bar": peak_bar,
                "pnl_usd": pnl,
                "ret_pct": (received / entry_cost - 1) * 100,
                "bars_held": i - entry_bar,
                "exit_reason": exit_reason,
                "trail_armed": trail_armed,
                "trail_arm_bar": trail_arm_bar,
                "mfe_atr": mfe_at_exit,
            })
            cash = received
            bq = 0.0
            in_position = False

    nav[i] = cash + bq * p
    a_val = ratr[i]
    if np.isnan(a_val) or np.isnan(ef[i]) or np.isnan(es[i]):
        continue

    if not in_position:
        if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
            pending_entry = True
    else:
        peak = max(peak, p)
        if p >= peak:
            peak_bar = i

        mfe = peak - entry_px
        if not trail_armed and not np.isnan(entry_ratr) \
           and entry_ratr > 1e-12:
            if mfe >= arm_k * entry_ratr:
                trail_armed = True
                trail_arm_bar = i
                stats["n_arm_events"] += 1

        # EXIT 1: Trend failure (always active)
        if ef[i] < es[i]:
            exit_reason = "trend_exit"
            pending_exit = True
            stats["n_trend_exit"] += 1
            continue

        # EXIT 2: Trail stop (only when armed)
        if trail_armed:
            trail_level = peak - trail_mult * a_val
            if p < trail_level:
                exit_reason = "trail_stop"
                pending_exit = True
                stats["n_trail_stop"] += 1

# End-of-data handling: same as E5
```


## 9. Benchmark Tests

### T0: Phase Diagnostic (Pre-flight)

**Purpose**: Determine whether early-phase trail stops in E5 are
disproportionately churn. This is the empirical test of hypothesis (b)
from Section 2.6.

**Procedure**:
1. Run E5 baseline → `trades_e5`
2. For each trail_stop exit, compute:
   - `mfe_atr = (peak_px - entry_px) / rATR_entry`
   - `is_churn`: re-entry within CHURN_WINDOW bars
3. Split trail stops into two groups:
   - **Early**: `mfe_atr < ARM_K` (would be prevented by arming)
   - **Late**: `mfe_atr >= ARM_K` (NOT prevented by arming)
4. Report:

```
| Phase | N | Churn | Rate | Avg PnL | Avg bars |
|-------|---|-------|------|---------|----------|
| Early |   |       |      |         |          |
| Late  |   |       |      |         |          |
| All   |   |       |      |         |          |
```

5. Compute `mfe_atr` at trail exit for each E5 trade, report percentile
   distribution (Q10, Q25, Q50, Q75, Q90) to show where arming threshold
   sits relative to the population.

**Interpretation** (diagnostic, no gate):
- If churn_rate(early) > churn_rate(late) + 10pp: supports H₁
- If churn_rate(early) ≈ churn_rate(late): arming targets wrong subset,
  churn is drift-driven not phase-driven. H₁ is likely false but
  continue to T1 for empirical test.
- If n_early < 5: arming threshold too low to matter, consider higher k


### T1: Full-Sample Comparison

**Purpose**: Compare E5 vs E5+ARM(k=1.5) on full dataset.

**Procedure**:
1. Run `_run_sim_e5()` → E5 baseline
2. Run `_run_sim_e5_arm(arm_k=1.5)` → E5+ARM
3. Compute metrics, exposure, churn for both

**Output table**:
```
| Strategy   | Sharpe | CAGR%  | MDD%   | Trades | Exp%  |
|------------|--------|--------|--------|--------|-------|
| E5         |        |        |        |        |       |
| E5+ARM(1.5)|        |        |        |        |       |
```

**Exit anatomy**:
```
| Strategy    | Total | Trail | Trend | Never-Armed | Churn/Trail% |
|-------------|-------|-------|-------|-------------|--------------|
| E5          |       |       |       |     -       |              |
| E5+ARM(1.5) |       |       |       |             |              |
```

**Gate G0**: `d_sharpe(E5+ARM, E5) > 0`


### T2: k-Sweep Characterization

**Purpose**: Show how arming threshold k affects outcomes across
the range [0.5, 3.0]. This is characterization, not optimization.

**Procedure**: For each k in K_SWEEP:
1. Run `_run_sim_e5_arm(arm_k=k)` on full data
2. Record metrics, churn rate, n_never_armed

**Output table**:
```
| k    | Sharpe | CAGR%  | MDD%   | Trades | N.Armed% | Churn/Tr% |
|------|--------|--------|--------|--------|----------|-----------|
| 0.5  |        |        |        |        |          |           |
| 1.0  |        |        |        |        |          |           |
| 1.5  |        |        |        |        |          |           |
| 2.0  |        |        |        |        |          |           |
| 2.5  |        |        |        |        |          |           |
| 3.0  |        |        |        |        |          |           |
| E5   |        |        |        |        |   100    |           |
```

No gate on this test. It is a characterization of the k-response surface.

**Expected behavior if arming has value**:
- Sharpe should increase from k=0 (E5) to some k*, then decrease
- MDD may increase with k (less protection in Phase 1)
- Trade count should decrease with k (fewer trail exits)
- If curve is monotonic (no peak), arming is equivalent in practice
  to trail sweep (despite being structurally different)


### T3: Walk-Forward Optimization (4 folds)

**Purpose**: Primary out-of-sample validation at fixed k=1.5.

**Procedure** (per fold):

1. **Apply** (full data, no training needed — k is preset):
   a. Run `_run_sim_e5()` on full data → E5 baseline NAV
   b. Run `_run_sim_e5_arm(arm_k=1.5)` on full data → E5+ARM NAV

2. **Measure** (test window only):
   a. Compute metrics on [test_start, test_end]
   b. Record `d_sharpe = ARM_sharpe - E5_sharpe`

Note: unlike X23, there is NO model training and NO parameter estimation
per fold. The ARM_K is a global preset. WFO here tests temporal stability
of the intervention, not parameter selection.

**Gate G1**: `win_rate >= 3/4` AND `mean_d_sharpe > 0`


### T4: Bootstrap (500 VCBB paths)

**Purpose**: Statistical confidence under synthetic data.

**Procedure**: For each of 500 VCBB paths:
1. Generate synthetic H4 bars
2. Compute indicators (ef, es, vd, ratr)
3. Borrow regime from real data (positional match)
4. Run E5 sim → baseline metrics
5. Run E5+ARM(k=1.5) sim → ARM metrics
6. Record `d_sharpe`, `d_cagr`, `d_mdd`

Note: no model training per path (unlike X23/X18). Each path just runs
two deterministic sims. This is much faster.

**Gate G2**: `P(d_sharpe > 0) > 0.55`

**Gate G3**: `median_d_mdd <= +5.0 pp`


### T5: Jackknife (leave-year-out)

**Purpose**: Temporal stability.

**Procedure** (identical structure to X23 T5):
1. Run E5 and E5+ARM on full data
2. For each year Y: exclude bars in Y, recompute metrics, record d_sharpe

**Gate G4**: at most 2/6 folds have `d_sharpe < 0`


### T6: PSR with DOF Correction

**Purpose**: Selection bias adjustment.

**Procedure**:
1. Compute annualized Sharpe of E5+ARM from T1
2. Compute PSR using `benchmark_sr0(E0_EFFECTIVE_DOF, n_returns)` as SR0

**Gate G5**: `PSR > 0.95`


### T7: Summary Table & Verdict

```
| Gate | Test | Criterion           | Result | Pass? |
|------|------|---------------------|--------|-------|
| G0   | T1   | d_sharpe > 0 vs E5  |        |       |
| G1   | T3   | WFO >= 3/4, d > 0   |        |       |
| G2   | T4   | P(d_sh > 0) > 0.55  |        |       |
| G3   | T4   | med d_mdd <= +5pp   |        |       |
| G4   | T5   | JK neg <= 2/6       |        |       |
| G5   | T6   | PSR > 0.95          |        |       |
```

**Verdict**:
- **PROMOTE**: ALL 6 gates pass
- **HOLD**: 4-5 gates pass
- **REJECT**: <= 3 gates pass


## 10. Validation Gates Summary

| Gate | Source | Criterion | Rationale |
|------|--------|-----------|-----------|
| G0 | T1 full-sample | d_sharpe > 0 vs E5 | Basic sanity |
| G1 | T3 WFO | win_rate >= 75%, mean d > 0 | OOS stability |
| G2 | T4 bootstrap | P(d_sharpe > 0) > 55% | Statistical robustness |
| G3 | T4 bootstrap | median d_mdd <= +5.0 pp | MDD not catastrophically worse |
| G4 | T5 jackknife | neg folds <= 2/6 | Temporal stability |
| G5 | T6 PSR | PSR > 0.95 | Selection bias correction |


## 11. Implementation Notes

### 11.1. Simplicity

X24 is deliberately simpler than X23. No score model, no feature extraction,
no state bucketing, no hard stop, no pullback calibration. The only change
from E5 is a boolean gate on the trail check.

Expected LOC: ~600 (vs X23's ~1200). Bootstrap is faster (no model
training per path).

### 11.2. rATR NaN handling

Same as X23. `entry_ratr = ratr[signal_bar]`. If NaN (shouldn't happen with
WARMUP=365), set arm threshold to +inf (trail never arms, only trend exit).

### 11.3. Fill convention

Same as X18/X23. Signal at bar t → fill at bar t+1 at cl[t].

### 11.4. Peak anchor

Highest close since entry (same as X23/E5). Not highest high.

### 11.5. No optimization over k

ARM_K = 1.5 is PRESET. Not optimized on training data. The k-sweep (T2)
is characterization only and does not influence gate decisions.

### 11.6. Comparison to E5

All delta metrics (d_sharpe, d_cagr, d_mdd) are computed vs E5 baseline,
consistent with X23.


## 12. Relationship to Prior Work

### 12.1. vs trail_sweep

Trail sweep tests m ∈ [2.0, 5.0] with constant m across all bars.
X24 tests phase-dependent trail activation with constant m=3.0.

The proof in Section 2 shows these are not equivalent. Trail sweep
explores the return/risk frontier along a single dimension (stop width).
X24 explores a different dimension (stop activation timing).

If T2 k-sweep produces a monotonic curve (Sharpe increases with k,
no inflection), the practical conclusion is that arming behaves like
a "soft" trail widening and offers no advantage over trail sweep.
This is a valid negative result.

### 12.2. vs X23

X23 tested arming + hard stop + state conditioning simultaneously.
All three components were confounded. X23's failure (REJECT, 2/6 gates)
cannot be attributed to any single component.

X24 isolates the arming component by removing hard stop and state
conditioning entirely. This is a clean test of one hypothesis.

X23's hard stop (entry - 2.5·rATR) was TIGHTER than E5's initial trail
(entry - 3.0·rATR), creating more early exits. X24 goes in the opposite
direction: Phase 1 has NO trail stop at all (only trend exit).

### 12.3. vs X14/X18 (churn filters)

X14/X18 suppress trail exits post-trigger. X24 prevents trail exits
from triggering in Phase 1. Both aim to reduce churn but by different
mechanisms:

- X14/X18: stop fires, then decide whether to act on it
- X24: stop does not fire at all in Phase 1

X24 has zero model complexity and zero fitting. If it captures similar
or more churn reduction than X14/X18, it would be preferred on parsimony.

### 12.4. Implications if REJECT

If X24 fails, combined with:
- X12-X19: post-trigger churn filters capture ≤17% of oracle ceiling
- X23: exit geometry redesign fails (REJECT)
- X24: trail arming isolation fails

The conclusion would be: **the exit mechanism is not the bottleneck**.
The remaining churn oracle ceiling (~0.845 Sharpe) is driven by BTC's
structural upward drift causing recovery after nearly any exit, and is
not capturable by stop design modifications.

This would close the exit-side research program definitively.


## 13. Output Artifacts

### 13.1. `x24_results.json`

```json
{
    "study_id": "X24",
    "timestamp": "ISO-8601",
    "constants": { "ARM_K": 1.5, "TRAIL": 3.0, ... },
    "t0_diagnostic": { ... },
    "t1_fullsample": {
        "e5": { "sharpe": ..., "cagr": ..., "mdd": ..., "trades": ... },
        "arm": { ... },
        "d_sharpe": ...
    },
    "t2_sweep": [ { "k": ..., "sharpe": ..., ... }, ... ],
    "t3_wfo": { "folds": [...], "win_rate": ..., "mean_d": ... },
    "t4_bootstrap": { "P_d_sharpe_gt_0": ..., "median_d_sharpe": ..., ... },
    "t5_jackknife": { "folds": [...], "n_negative": ... },
    "t6_psr": { "sharpe": ..., "psr": ... },
    "gates": { "G0": ..., "G1": ..., ... },
    "verdict": "PROMOTE" | "HOLD" | "REJECT"
}
```

### 13.2. `x24_report.md`

Human-readable markdown report with all tables and gate results.


## 14. Execution Plan

### Phase 1: Implement benchmark.py

1. Copy indicator functions from X23 (verbatim, minus standard ATR and score model)
2. Copy E5 sim from X23 (verbatim)
3. Implement `_run_sim_e5_arm()` (Section 8)
4. Implement T0 through T7
5. Implement `main()` orchestrator

### Phase 2: Run & Analyze

1. Run `python research/x24/benchmark.py`
2. Review T0 diagnostic (is churn phase-dependent?)
3. Review T1 (does d_sharpe > 0?)
4. Review T2 k-sweep (monotonic or inflection?)
5. If G0 fails: report results, no further action needed
6. If G0 passes: T3-T6 results determine verdict
