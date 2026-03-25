# X23 SPEC: State-Conditioned Exit Geometry Redesign

## 1. Study ID & Metadata

| Field | Value |
|-------|-------|
| Study ID | X23 |
| Title | State-Conditioned Exit Geometry |
| Location | `research/x23/` |
| Baseline | E5+EMA1D21 (primary comparison), E0+EMA1D21 (reference for churn continuity) |
| Data | `data/bars_btcusdt_2016_now_h1_4h_1d.csv` |
| Period | 2019-01-01 to 2026-02-20, warmup 365 days |
| Cost | 50 bps RT (harsh scenario) |
| DOF budget | 0 tuned params (all values preset by spec) |


## 2. Motivation

The current E5+EMA1D21 exit uses a single trailing stop (`peak - 3.0 * rATR`)
that simultaneously serves as catastrophe protection, profit protection, and
trend-failure detection. Empirical analysis on E0+EMA1D21 shows 63% of trail
stops are churn (re-entry within 20 bars), with oracle ceiling of +0.845 Sharpe.

Post-trigger churn filters (X14, X18) capture only ~10-17% of the oracle
ceiling because the fundamental problem is not "predicting churn after stop
triggers" but "stop triggers in healthy pullbacks that should not trigger."

X23 redesigns exit geometry ex ante:
- Separate hard invalidation stop from continuation stop
- Delay trail arming until trade has sufficient MFE
- Condition trail width on exogenous market state (wider in strong state)
- All logic deterministic, preset parameters, zero tuned DOF


## 3. File Layout

```
research/x23/
├── SPEC.md              # This document
├── benchmark.py         # Main benchmark script (~1000 lines)
├── x23_results.json     # Machine-readable results (generated)
└── x23_report.md        # Human-readable report (generated)
```


## 4. Constants

```python
# === Data & Period ===
DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)          # annualization factor for H4
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365                            # days

# === Indicator parameters (frozen from E5+EMA1D21) ===
SLOW = 120                              # EMA slow period
VDO_F = 12                              # VDO fast
VDO_S = 28                              # VDO slow
VDO_THR = 0.0                           # VDO entry threshold
D1_EMA_P = 21                           # D1 regime EMA period

# === ATR parameters ===
ATR_P = 14                              # standard ATR (for score model features)
RATR_CAP_Q = 0.90                       # robust ATR quantile cap
RATR_CAP_LB = 100                       # robust ATR lookback
RATR_PERIOD = 20                        # robust ATR Wilder period

# === Trail baseline ===
TRAIL = 3.0                             # E0/E5 trail multiplier (baseline)

# === X23 architecture parameters (ALL PRESET, ZERO TUNED) ===
HARD_MULT = 2.5                         # hard stop: E - HARD_MULT * rATR_entry
ARM_MULT = 1.5                          # trail arms when MFE >= ARM_MULT * rATR_entry
SCORE_Q_LO = 15                         # score percentile for weak/normal boundary
SCORE_Q_HI = 85                         # score percentile for normal/strong boundary
M_WEAK = 2.25                           # trail mult in weak state
M_NORMAL = 3.0                          # trail mult in normal state
M_STRONG = 4.25                         # trail mult in strong state

# === Score model (reused from X18) ===
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]  # L2 regularization grid
CHURN_WINDOW = 20                       # bars for churn label

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
E0_EFFECTIVE_DOF = 4.35                 # Nyholt M_eff

# === Feature names (7 market-state features, matches X18) ===
FEATURE_NAMES_7 = [
    "ema_ratio", "atr_pctl", "bar_range_atr", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

# === Pullback calibration quantiles (fixed by spec) ===
PB_Q_WEAK = 0.75                        # pullback quantile for weak state
PB_Q_NORMAL = 0.85                      # pullback quantile for normal state
PB_Q_STRONG = 0.90                      # pullback quantile for strong state
```


## 5. Indicator Functions

All indicator functions are **identical** to X14/X18 implementations. Copied
verbatim into `benchmark.py` for self-containment (no cross-study imports).

### 5.1. `_ema(series, period) -> np.ndarray`

Exponential moving average using `scipy.signal.lfilter`. Alpha = 2/(period+1).
Identical to X18.

### 5.2. `_atr(high, low, close, period=ATR_P) -> np.ndarray`

Standard Wilder ATR(14). Used **only** for score model features (f2, f3, f7).
Not used for trail stop computation.

### 5.3. `_robust_atr(high, low, close, cap_q, cap_lb, period) -> np.ndarray`

Robust ATR: cap TR at rolling Q90 (100-bar lookback), then Wilder EMA(20).
Identical to X14's implementation. Used for:
- Hard stop computation (A_E = rATR at entry)
- Trail stop computation (A_t = current rATR)
- MFE threshold (1.5 * A_E)
- Pullback depth normalization (PB_t / A_t)

First valid index: `cap_lb + period - 1 = 119` (i.e. `ratr[119]`).

### 5.4. `_vdo(close, high, low, volume, taker_buy, fast, slow) -> np.ndarray`

Volume Delta Oscillator. Identical to X18.

### 5.5. `_compute_indicators(cl, hi, lo, vo, tb, slow_period=SLOW) -> tuple`

Returns `(ef, es, vd, at_std)` where:
- `ef` = EMA(fast), fast = max(5, slow // 4) = 30
- `es` = EMA(slow) = EMA(120)
- `vd` = VDO(12, 28)
- `at_std` = standard ATR(14)

### 5.6. `_compute_ratr(hi, lo, cl) -> np.ndarray`

Convenience wrapper: `_robust_atr(hi, lo, cl, RATR_CAP_Q, RATR_CAP_LB, RATR_PERIOD)`.
Called separately from `_compute_indicators`.

### 5.7. `_compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P) -> np.ndarray`

Boolean array mapped to H4 grid: True when D1 close > D1 EMA(21).
Identical to X18.

### 5.8. `_compute_d1_regime_str(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P) -> np.ndarray`

Float array mapped to H4 grid: (D1_close - D1_EMA) / D1_close.
Identical to X18.


## 6. Market-State Score Model

The 7-feature L2-logistic model from X18 is reused as a **market-state
indicator**. It is NOT used for churn prediction. It is used to rank bars by
continuation strength.

### 6.1. Training procedure (per fold)

1. Run E0 baseline sim on training data → get `trades_train`
2. Label trail-stop exits as churn/not-churn using `_label_churn(trades_train)`
3. Extract 7 features at each trail-stop bar using `_extract_features_7()`
4. Grid-search L2 penalty C via 5-fold CV AUC
5. Fit final model on all training trail-stop instances
6. Return `(w, mu, std, C, n_samples)`

### 6.2. `_extract_features_7(i, cl, hi, lo, at_std, ef, es, vd, d1_str_h4, trail_mult=TRAIL) -> np.ndarray`

**Critical design choice**: uses `at_std` (standard ATR-14), NOT robust ATR.

Rationale:
- The model's role is to **rank** market states by continuation strength.
  It does not need to match the ATR variant used for the actual trail.
- Features f2 (atr_pctl), f3 (bar_range_atr), f7 (trail_tightness) use ATR as
  a normalizer. Standard ATR(14) is well-validated from X14/X18.
- The model is retrained per WFO fold, so it adapts to the feature distribution.
- Keeping standard ATR for features isolates the ATR choice from the score
  model, making it easier to reason about each component independently.

Alternative: use robust ATR for features. This is valid and would make the
feature space internally consistent with the trail. If standard ATR features
show poor model AUC in T0, consider switching.

```
f1 = ef[i] / es[i]                     # ema_ratio
f2 = percentile_rank(at_std[i], at_std[max(0,i-99):i+1])  # atr_pctl
f3 = (hi[i] - lo[i]) / at_std[i]       # bar_range_atr
f4 = (cl[i] - lo[i]) / (hi[i] - lo[i]) # close_position
f5 = vd[i]                             # vdo_at_exit
f6 = d1_str_h4[i]                      # d1_regime_str
f7 = trail_mult * at_std[i] / cl[i]    # trail_tightness
```

### 6.3. `_predict_score(feat, w, mu, std) -> float`

Standardize features, apply logistic: `sigmoid(feat_std @ w[:7] + w[7])`.
Returns score in [0, 1]. Higher score = stronger continuation state.

### 6.4. `_precompute_scores(cl, hi, lo, at_std, ef, es, vd, d1_str_h4, model_w, model_mu, model_std) -> np.ndarray`

Precompute scores for ALL bars (not just trail-stop bars). Returns array of
length n. Bars with NaN indicators get NaN score.

```python
def _precompute_scores(cl, hi, lo, at_std, ef, es, vd, d1_str_h4,
                       model_w, model_mu, model_std, trail_mult=TRAIL):
    n = len(cl)
    scores = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(at_std[i]) or np.isnan(ef[i]) or np.isnan(es[i]):
            continue
        feat = _extract_features_7(i, cl, hi, lo, at_std, ef, es, vd,
                                   d1_str_h4, trail_mult)
        scores[i] = _predict_score(feat, model_w, model_mu, model_std)
    return scores
```

### 6.5. Score bucketing

**Quantile estimation domain**: `score_q15` and `score_q85` are estimated from
scores at ALL valid bars in the training period, not just in-position bars.
Rationale: (a) larger sample is more stable, (b) the score is a market-state
indicator that is meaningful at any bar, (c) in-position bars are a biased
subset (selected by entry conditions).

Given `score_q15` and `score_q85` (estimated on training fold scores):

```
state_t = "weak"   if score_t < score_q15
state_t = "normal" if score_q15 <= score_t < score_q85
state_t = "strong" if score_t >= score_q85
```

The multiplier lookup:
```
m_t = M_WEAK   if state_t == "weak"     # 2.25
m_t = M_NORMAL if state_t == "normal"   # 3.0
m_t = M_STRONG if state_t == "strong"   # 4.25
```


## 7. E0 Baseline Sim: `_run_sim_e0()`

Identical to X18's `_run_sim_e0()`. Uses standard ATR(14) for trail.

```python
def _run_sim_e0(cl, ef, es, vd, at_std, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
    # Returns (nav, trades)
    # Entry: ef > es AND vd > VDO_THR AND regime_h4
    # Exit:  cl < peak - trail_mult * at_std  OR  ef < es
    # Fill at next bar's close (cl[i-1] proxy)
```

**Trade dict fields** (unchanged from X18):
```python
{
    "entry_bar": int,      # execution bar (signal bar + 1)
    "exit_bar": int,       # execution bar
    "entry_px": float,     # fill price (cl[signal_bar])
    "exit_px": float,      # fill price
    "peak_px": float,      # highest close during trade
    "peak_bar": int,       # bar of peak
    "pnl_usd": float,
    "ret_pct": float,
    "bars_held": int,
    "exit_reason": str,    # "trail_stop" | "trend_exit" | "end_of_data"
}
```


## 8. E5 Baseline Sim: `_run_sim_e5()`

Identical to E0 except uses `ratr` (robust ATR) instead of `at_std` for trail.

```python
def _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
    # Returns (nav, trades)
    # Entry: ef > es AND vd > VDO_THR AND regime_h4
    # Exit:  cl < peak - trail_mult * ratr  OR  ef < es
```


## 9. X23 Sim: `_run_sim_x23()` — Core New Code

### 9.1. Function signature

```python
def _run_sim_x23(cl, ef, es, vd, ratr, regime_h4, wi, scores,
                 score_q15, score_q85,
                 m_weak=M_WEAK, m_normal=M_NORMAL, m_strong=M_STRONG,
                 hard_mult=HARD_MULT, arm_mult=ARM_MULT,
                 cps=CPS_HARSH):
    """
    X23 exit geometry: hard stop + delayed trail arm + state-conditioned trail.

    Parameters
    ----------
    cl, ef, es, vd, ratr : np.ndarray
        H4 close, EMA fast, EMA slow, VDO, robust ATR arrays.
    regime_h4 : np.ndarray[bool]
        D1 EMA(21) regime mapped to H4.
    wi : int
        Warmup index (first reporting bar).
    scores : np.ndarray
        Precomputed logistic scores for all bars (from _precompute_scores).
    score_q15, score_q85 : float
        Score percentile thresholds for state bucketing.
    m_weak, m_normal, m_strong : float
        Trail multipliers per state.
    hard_mult : float
        Hard stop multiplier (from entry).
    arm_mult : float
        MFE threshold for trail arming (in rATR units from entry).
    cps : float
        Cost per side (fraction).

    Returns
    -------
    nav : np.ndarray
        NAV curve.
    trades : list[dict]
        Trade records.
    stats : dict
        Diagnostic statistics.
    """
```

### 9.2. Additional state variables (beyond E0)

```python
# At entry:
entry_ratr = 0.0            # rATR at entry bar (A_E)
hard_stop = 0.0             # E - hard_mult * A_E (fixed for trade lifetime)
trail_armed = False          # becomes True when MFE >= arm_mult * A_E
trail_arm_bar = -1           # bar when trail was armed

# Running:
mfe = 0.0                   # max(peak - entry_px, 0) in price units
```

### 9.3. Entry logic (UNCHANGED from E0/E5)

```
if FLAT and ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
    → pending entry
```

At fill (next bar):
```python
entry_px = cl[i-1]          # fill price
entry_ratr = ratr[i-1]      # rATR at signal bar (bar before fill)
hard_stop = entry_px - hard_mult * entry_ratr
trail_armed = False
trail_arm_bar = -1
peak = cl[i]                # first close after entry
mfe = max(0, peak - entry_px)
```

**Note on `entry_ratr`**: We use `ratr[i-1]` (the signal bar's rATR), not
`ratr[i]` (the fill bar's rATR). This matches the convention that the decision
to enter is made at bar i-1, and the hard stop should be based on conditions
known at decision time.

### 9.4. Hard invalidation stop

Active from entry until exit. Never moves.

```python
S_hard = entry_px - hard_mult * entry_ratr
# Check: cl[i] < S_hard → exit
```

Purpose: protects against "entry was fundamentally wrong." Not for profit
management. Using `entry_ratr` (not current rATR) because:
- Hard stop reflects entry-time conditions
- Avoids widening during volatility expansion post-entry
- Fixed level is simplest (zero state to track)

### 9.5. Trail arming

Trail activates only after sufficient MFE:

```python
mfe = peak - entry_px      # peak is tracked continuously
if mfe >= arm_mult * entry_ratr:
    trail_armed = True
    trail_arm_bar = i       # record for diagnostics
```

Before arming:
- Only hard stop and trend-failure exit are active
- Trail stop is **not evaluated at all**

After arming:
- Trail stop becomes active (in addition to hard stop and trend-failure)
- Arming is **permanent** for the trade (never un-arms)

### 9.6. State bucketing

At each in-position bar (when trail is armed):

```python
s = scores[i]
if np.isnan(s):
    state = "normal"        # fallback for NaN scores
    m_t = m_normal
elif s < score_q15:
    state = "weak"
    m_t = m_weak            # 2.25 — tighter stop
elif s >= score_q85:
    state = "strong"
    m_t = m_strong           # 4.25 — wider stop
else:
    state = "normal"
    m_t = m_normal           # 3.0 — baseline
```

### 9.6b. `_get_state()` helper

Used at exit time to record state for diagnostics (when trail check is skipped):

```python
def _get_state(score, q15, q85):
    if np.isnan(score):
        return "normal"
    if score < q15:
        return "weak"
    if score >= q85:
        return "strong"
    return "normal"
```

### 9.7. State-conditioned continuation stop

```python
S_trail = peak - m_t * ratr[i]
# Check: trail_armed and cl[i] < S_trail → exit
```

Key properties:
- Peak anchor: highest close since entry (not highest high)
- Trail width: `m_t * ratr[i]` varies with both state and current volatility
- In strong state: stop is ~42% wider than E0 (4.25 vs 3.0)
- In weak state: stop is ~25% tighter than E0 (2.25 vs 3.0)

### 9.8. Trend-failure exit

Unchanged from E0/E5:

```python
if ef[i] < es[i]:
    → exit (trend reversal)
```

Active at all times (before and after trail arming).

### 9.9. Complete per-bar logic (pseudocode)

```python
# --- Variable initialization ---
cash = CASH
bq = 0.0
in_position = False
pending_entry = False
pending_exit = False
peak = 0.0
peak_bar = 0
entry_bar = 0
entry_px = 0.0
entry_cost = 0.0
entry_ratr = 0.0
hard_stop = 0.0
trail_armed = False
trail_arm_bar = -1
exit_reason = ""
state_at_exit = ""
nav = np.zeros(n)
trades = []
stats = {
    "n_trades": 0, "n_hard_stop": 0, "n_trail_stop": 0,
    "n_trend_exit": 0, "n_end_of_data": 0, "n_arm_events": 0,
    "n_never_armed": 0,
    "n_trail_by_state": {"weak": 0, "normal": 0, "strong": 0},
}

for i in range(n):
    p = cl[i]

    # --- Fill pending signals at bar open ---
    if i > 0:
        fp = cl[i - 1]     # fill price proxy

        if pending_entry:
            pending_entry = False
            # Record entry state
            entry_px = fp
            entry_bar = i
            entry_ratr = ratr[i - 1]   # signal bar's rATR
            hard_stop = entry_px - hard_mult * entry_ratr
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
            ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
            if not trail_armed:
                stats["n_never_armed"] += 1
            trades.append({
                "entry_bar": entry_bar, "exit_bar": i,
                "entry_px": entry_px, "exit_px": fp,
                "peak_px": peak, "peak_bar": peak_bar,
                "pnl_usd": pnl, "ret_pct": ret_pct,
                "bars_held": i - entry_bar,
                "exit_reason": exit_reason,
                "trail_armed": trail_armed,
                "trail_arm_bar": trail_arm_bar,
                "hard_stop_level": hard_stop,
                "state_at_exit": state_at_exit,
            })
            cash = received
            bq = 0.0
            in_position = False

    # --- NAV snapshot ---
    nav[i] = cash + bq * p

    # --- Skip invalid bars ---
    a_val = ratr[i]
    if np.isnan(a_val) or np.isnan(ef[i]) or np.isnan(es[i]):
        continue

    # --- Decision logic ---
    if not in_position:
        # ENTRY (unchanged)
        if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
            pending_entry = True

    else:
        # Update peak
        peak = max(peak, p)
        if p >= peak:
            peak_bar = i

        # Update MFE and trail arming
        mfe = peak - entry_px
        if not trail_armed and mfe >= arm_mult * entry_ratr:
            trail_armed = True
            trail_arm_bar = i
            stats["n_arm_events"] += 1

        # EXIT CHECK 1: Hard stop (always active)
        if p < hard_stop:
            exit_reason = "hard_stop"
            state_at_exit = _get_state(scores[i], score_q15, score_q85)
            pending_exit = True
            stats["n_hard_stop"] += 1
            continue

        # EXIT CHECK 2: Trend failure (always active)
        if ef[i] < es[i]:
            exit_reason = "trend_exit"
            state_at_exit = _get_state(scores[i], score_q15, score_q85)
            pending_exit = True
            stats["n_trend_exit"] += 1
            continue

        # EXIT CHECK 3: Trail stop (only when armed)
        if trail_armed:
            # Determine state and multiplier
            s = scores[i]
            if np.isnan(s):
                m_t = m_normal
                cur_state = "normal"
            elif s < score_q15:
                m_t = m_weak
                cur_state = "weak"
            elif s >= score_q85:
                m_t = m_strong
                cur_state = "strong"
            else:
                m_t = m_normal
                cur_state = "normal"

            trail_level = peak - m_t * a_val
            if p < trail_level:
                exit_reason = "trail_stop"
                state_at_exit = cur_state
                pending_exit = True
                stats["n_trail_stop"] += 1
                stats["n_trail_by_state"][cur_state] += 1

# --- Handle open position at end of data ---
if in_position and bq > 0:
    received = bq * cl[-1] * (1 - cps)
    pnl = received - entry_cost
    ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
    trades.append({
        "entry_bar": entry_bar, "exit_bar": n - 1,
        "entry_px": entry_px, "exit_px": cl[-1],
        "peak_px": peak, "peak_bar": peak_bar,
        "pnl_usd": pnl, "ret_pct": ret_pct,
        "bars_held": n - 1 - entry_bar,
        "exit_reason": "end_of_data",
        "trail_armed": trail_armed,
        "trail_arm_bar": trail_arm_bar,
        "hard_stop_level": hard_stop,
        "state_at_exit": "n/a",
    })
```

### 9.10. Stats dict returned by `_run_sim_x23()`

```python
stats = {
    "n_trades": int,
    "n_hard_stop": int,
    "n_trail_stop": int,
    "n_trend_exit": int,
    "n_end_of_data": int,
    "n_arm_events": int,
    "n_never_armed": int,       # trades that exited before trail armed
    "n_trail_by_state": {
        "weak": int,
        "normal": int,
        "strong": int,
    },
}
```

### 9.11. Trade dict fields (extended from E0)

```python
{
    # Standard fields (same as E0)
    "entry_bar": int,
    "exit_bar": int,
    "entry_px": float,
    "exit_px": float,
    "peak_px": float,
    "peak_bar": int,
    "pnl_usd": float,
    "ret_pct": float,
    "bars_held": int,
    "exit_reason": str,         # "hard_stop" | "trail_stop" | "trend_exit" | "end_of_data"

    # X23-specific fields
    "trail_armed": bool,        # was trail armed before exit?
    "trail_arm_bar": int,       # bar where trail armed (-1 if never)
    "hard_stop_level": float,   # hard stop price for this trade
    "state_at_exit": str,       # "weak" | "normal" | "strong" | "n/a"
}
```


## 10. Pullback Calibration Algorithm

This is a **diagnostic** procedure that validates whether the preset multipliers
(M_WEAK, M_NORMAL, M_STRONG) are consistent with empirical healthy pullback
distributions. It also provides data-driven multipliers for the WFO variant.

### 10.1. Continuation instance detection

For every in-position bar `t` in an E5 baseline sim (using robust ATR):

```python
# Stopping times (computed forward from bar t)
tau_next_peak = first u > t where cl[u] > peak_t
tau_fail = first u > t where (cl[u] < hard_stop_t) or (ef[u] < es[u])

# Classification
if tau_next_peak < tau_fail:
    → continuation instance
elif tau_fail < tau_next_peak:
    → failure instance
else:
    → censored (end of data)
```

Where `peak_t = max(cl[entry_bar:t+1])` is the running peak at bar t, and
`hard_stop_t = entry_px - HARD_MULT * entry_ratr` is the hard stop level.

### 10.2. Pullback depth measurement

For each continuation instance at bar t:

```python
# Minimum close between t and next peak
min_close = min(cl[u] for u in range(t, tau_next_peak + 1))

# Pullback depth in rATR units
PB_t = (peak_t - min_close) / ratr[t]
```

This measures "how deep was the healthy pullback before price made a new peak?"

### 10.3. Per-state quantile estimation

Group continuation instances by state (using score buckets):

```python
for state in ["weak", "normal", "strong"]:
    pb_values = [PB_t for t in continuation_instances if state_t == state]

    if len(pb_values) >= 20:
        m_calibrated[state] = np.percentile(pb_values, PB_Q[state] * 100)
    else:
        # Shrinkage: blend with global quantile
        global_pb = [PB_t for t in all_continuation_instances]
        global_q = np.percentile(global_pb, PB_Q[state] * 100)
        if len(pb_values) >= 5:
            local_q = np.percentile(pb_values, PB_Q[state] * 100)
            weight = len(pb_values) / 20.0
            m_calibrated[state] = weight * local_q + (1 - weight) * global_q
        else:
            m_calibrated[state] = global_q
```

Quantile levels (fixed by spec):
- weak: Q75 (75th percentile of pullback depth)
- normal: Q85 (85th percentile)
- strong: Q90 (90th percentile)

Interpretation: the trail multiplier should be set so that X% of healthy
pullbacks do NOT trigger the stop. Higher quantile = fewer false triggers.

### 10.4. Monotonicity constraint

After calibration, enforce:

```python
m_calibrated["weak"] = min(m_calibrated["weak"], m_calibrated["normal"])
m_calibrated["strong"] = max(m_calibrated["strong"], m_calibrated["normal"])
# If still violated (shouldn't happen with correct quantiles):
if m_calibrated["weak"] > m_calibrated["normal"]:
    m_calibrated["weak"] = m_calibrated["normal"]
```

### 10.5. `_calibrate_pullback()` function signature

```python
def _calibrate_pullback(cl, ef, es, ratr, scores,
                        score_q15, score_q85,
                        trades_baseline,
                        hard_mult=HARD_MULT,
                        q_weak=PB_Q_WEAK, q_normal=PB_Q_NORMAL,
                        q_strong=PB_Q_STRONG):
    """
    Estimate data-driven trail multipliers from healthy pullback distribution.

    Parameters
    ----------
    cl, ef, es, ratr : np.ndarray
        Price and indicator arrays (full length).
    scores : np.ndarray
        Precomputed logistic scores for all bars.
    score_q15, score_q85 : float
        Score percentile thresholds for state bucketing.
    trades_baseline : list[dict]
        Trade list from an E5 baseline sim. Used to identify which bars
        are in-position, and to get entry_px / entry_ratr per trade.
        Each trade must have: entry_bar, exit_bar, entry_px, peak_px.
    hard_mult : float
        Hard stop multiplier (for failure condition in calibration).
    q_weak, q_normal, q_strong : float
        Quantile levels for pullback depth per state.

    Returns
    -------
    multipliers : dict
        {"weak": float, "normal": float, "strong": float}
    diagnostic : dict
        Per-state sample counts, raw quantiles, shrinkage flags, pullback
        distribution summary statistics.
    """
```

**Algorithm sketch** (inside the function):
```python
all_pb = {"weak": [], "normal": [], "strong": []}

for trade in trades_baseline:
    eb = trade["entry_bar"]     # fill bar
    xb = trade["exit_bar"]
    epx = trade["entry_px"]    # cl[signal_bar] = cl[eb-1]
    entry_ratr_val = ratr[eb - 1]  # rATR at signal bar
    if np.isnan(entry_ratr_val):
        continue
    hard_stop_level = epx - hard_mult * entry_ratr_val

    # Reconstruct running peak for each in-position bar.
    # In the sim, pk starts at cl[fill_bar] (not at entry_px = cl[signal_bar]).
    # Match that: start peak at cl[eb].
    peak = cl[eb]
    for t in range(eb, xb):
        peak = max(peak, cl[t])
        state = _get_state(scores[t], score_q15, score_q85)

        # Find tau_next_peak: first u > t where cl[u] > peak
        tau_peak = None
        for u in range(t + 1, xb + 1):
            if u >= len(cl):
                break
            if cl[u] > peak:
                tau_peak = u
                break

        # Find tau_fail: first u > t where hard_stop or trend_exit
        tau_fail = None
        for u in range(t + 1, len(cl)):
            if cl[u] < hard_stop_level or ef[u] < es[u]:
                tau_fail = u
                break

        if tau_peak is not None and (tau_fail is None or tau_peak < tau_fail):
            # Continuation instance — measure pullback depth
            min_cl = min(cl[v] for v in range(t, tau_peak + 1))
            ratr_t = ratr[t]
            if not np.isnan(ratr_t) and ratr_t > 1e-12:
                pb = (peak - min_cl) / ratr_t
                all_pb[state].append(pb)
```

Note: this inner loop is O(trades × bars_held × lookahead), which can be slow
for long trades. An optimized version can precompute `tau_next_peak` and
`tau_fail` arrays once, then look them up per bar. See implementation notes.

### 10.6. Usage in WFO

In each WFO fold:
1. Train logistic model on training E0 trades
2. Precompute scores on training data
3. Estimate score_q15, score_q85 from training scores
4. Run `_calibrate_pullback()` on training data → get calibrated multipliers
5. Freeze: model weights, score quantiles, multipliers
6. Run `_run_sim_x23()` on FULL data with frozen parameters
7. Measure OOS metrics

Two variants are tested per fold:
- **X23-fixed**: uses preset multipliers (2.25, 3.0, 4.25)
- **X23-cal**: uses fold-calibrated multipliers

Both use the same frozen model and score quantiles per fold.


## 11. Benchmark Tests

### T0: Full-Sample Comparison

**Purpose**: Compare X23 to E0 and E5 baselines on full dataset.

**Procedure**:
1. Train logistic model on ALL E0 trades (full-sample, for diagnostic only)
2. Precompute scores on all bars
3. Estimate score_q15, score_q85 from full-sample scores
4. Run `_run_sim_e0()` → baseline metrics
5. Run `_run_sim_e5()` → E5 baseline metrics
6. Run `_run_sim_x23()` with preset multipliers → X23-fixed metrics
7. Run `_calibrate_pullback()` → calibrated multipliers (diagnostic)
8. Run `_run_sim_x23()` with calibrated multipliers → X23-cal metrics

**Output table**:
```
| Strategy   | Sharpe | CAGR%  | MDD%   | Trades | Exposure% |
|------------|--------|--------|--------|--------|-----------|
| E0         |        |        |        |        |           |
| E5         |        |        |        |        |           |
| X23-fixed  |        |        |        |        |           |
| X23-cal    |        |        |        |        |           |
```

**Exposure% computation** (not part of `_metrics()`, computed separately):
```python
total_bars_held = sum(t["bars_held"] for t in trades)
total_reporting_bars = len(nav) - wi
exposure_pct = total_bars_held / total_reporting_bars * 100
```

**Gate G0**: X23-fixed `d_sharpe > 0` vs E5 baseline.


### T1: Exit Anatomy & Churn Diagnostic

**Purpose**: Verify that X23's exit architecture reduces churn compared to
E0 and E5.

**Procedure**:
For each of {E0, E5, X23-fixed, X23-cal}, compute:
1. Exit breakdown: count by exit_reason
2. Churn rate: for trail_stop exits, what fraction is followed by re-entry
   within CHURN_WINDOW bars?
3. Arm statistics (X23 only): trades that never armed, arm bar distribution

**Churn labeling**:

Note: X18 only labeled `trail_stop` exits. X23 introduces `hard_stop` as a new
exit type. Churn is reported **separately** per exit type, plus a combined rate
for all non-trend exits, so the reader can see exactly where churn reduction
comes from.

```python
def _label_churn_x23(trades, all_entry_bars, churn_window=CHURN_WINDOW):
    """Label churn for trail_stop and hard_stop exits separately."""
    results = []
    for t in trades:
        if t["exit_reason"] not in ("trail_stop", "hard_stop"):
            continue
        eb = t["exit_bar"]
        is_churn = any(eb < e <= eb + churn_window for e in all_entry_bars)
        results.append((t, 1 if is_churn else 0))
    return results
```

**Output table**:
```
| Strategy  | Total | Trail | Hard | Trend | Churn/Trail | Churn/Total |
|-----------|-------|-------|------|-------|-------------|-------------|
| E0        |       |       |  -   |       |             |             |
| E5        |       |       |  -   |       |             |             |
| X23-fixed |       |       |      |       |             |             |
| X23-cal   |       |       |      |       |             |             |
```

**Expected outcome**: X23 should show:
- Fewer trail stops (some absorbed by hard stop before arming)
- Lower churn rate among trail stops (wider stops in strong state)
- Non-trivial hard stop count (new category)


### T2: Pullback Calibration Report

**Purpose**: Diagnostic showing whether preset multipliers match pullback
distributions.

**Procedure**:
1. Run `_calibrate_pullback()` on full dataset
2. Report per-state pullback distributions:
   - N instances per state
   - Pullback depth: mean, std, Q25, Q50, Q75, Q90, Q95
3. Compare calibrated multipliers to preset values
4. Plot pullback distribution histograms (if matplotlib available, else skip)

**Output**:
```
| State  | N    | Mean | Std  | Q25  | Q50  | Q75  | Q90  | Cal.Mult | Preset |
|--------|------|------|------|------|------|------|------|----------|--------|
| weak   |      |      |      |      |      |      |      |          | 2.25   |
| normal |      |      |      |      |      |      |      |          | 3.0    |
| strong |      |      |      |      |      |      |      |          | 4.25   |
```

No gate on this test. It is purely diagnostic.


### T3: Walk-Forward Optimization (4 folds, nested calibration)

**Purpose**: Primary out-of-sample validation.

**Procedure** (per fold):

1. **Train** (bars wi to train_end):
   a. Run E0 sim on training bars → `trades_e0_train` (for model training)
   b. Train logistic model on `trades_e0_train` → `(w, mu, std)`
   c. Precompute scores on training bars → `scores_train`
   d. Estimate `score_q15 = percentile(scores_train[valid], SCORE_Q_LO)`
   e. Estimate `score_q85 = percentile(scores_train[valid], SCORE_Q_HI)`
   f. Run E5 sim on training bars → `trades_e5_train` (for pullback calibration)
   g. Run `_calibrate_pullback(trades_baseline=trades_e5_train)` on training bars
      → `m_cal_weak, m_cal_normal, m_cal_strong`

2. **Apply** (full data with frozen params):
   a. Precompute scores on full data using frozen `(w, mu, std)`
   b. Run `_run_sim_e5()` on full data → E5 baseline NAV
   c. Run `_run_sim_x23()` on full data with preset multipliers and frozen score quantiles → X23-fixed NAV
   d. Run `_run_sim_x23()` on full data with calibrated multipliers and frozen score quantiles → X23-cal NAV

3. **Measure** (test window only):
   a. For each variant, compute metrics on `[test_start, test_end]` window
   b. Record `d_sharpe = X23_sharpe - E5_sharpe` for the test window

**Fold metrics per variant**:
```python
{
    "fold": int,
    "train_end": str,
    "test_start": str,
    "test_end": str,
    "e5_sharpe": float,
    "x23_fixed_sharpe": float,
    "x23_cal_sharpe": float,
    "d_sharpe_fixed": float,
    "d_sharpe_cal": float,
    "cal_multipliers": {"weak": float, "normal": float, "strong": float},
    "score_q15": float,
    "score_q85": float,
}
```

**Aggregate**:
- Win rate (fixed): fraction of folds where `d_sharpe_fixed > 0`
- Win rate (cal): fraction of folds where `d_sharpe_cal > 0`
- Mean d_sharpe for each variant

**Gate G1**: X23-fixed has `win_rate >= 3/4` AND `mean_d_sharpe > 0`.

X23-cal results are reported as supplementary diagnostic only and do NOT
contribute to gate decisions. Testing both and picking the best would add
implicit selection bias. If X23-fixed fails G1 but X23-cal passes, this
is noted as a signal that calibrated multipliers may help, but the verdict
remains based on X23-fixed.


### T4: Bootstrap (500 VCBB paths)

**Purpose**: Statistical confidence under synthetic data.

**Procedure**:
For each of 500 VCBB paths:
1. Generate synthetic H4 bars using `gen_path_vcbb()`
2. Compute indicators (ef, es, vd, at_std, ratr)
3. Use shuffled regime and d1_str arrays from real data (matched by position)
4. Train logistic model on first 60% of synthetic path
5. Precompute scores, estimate score quantiles on first 60%
6. Run E5 sim on full synthetic path
7. Run X23-fixed sim on full synthetic path with frozen params
8. Record `d_sharpe`, `d_cagr`, `d_mdd`

**Aggregate**:
```python
{
    "P_d_sharpe_gt_0": float,    # fraction of paths where X23 Sharpe > E5 Sharpe
    "median_d_sharpe": float,
    "mean_d_sharpe": float,
    "P_d_mdd_le_0": float,       # fraction where X23 MDD ≤ E5 MDD
    "median_d_mdd": float,
    "median_sharpe_x23": float,
    "median_sharpe_e5": float,
}
```

**Gate G2**: `P(d_sharpe > 0) > 0.55`.

**Gate G3**: `median_d_mdd <= +5.0 pp` (MDD does not worsen by more than 5pp
at median).

Note: G2 threshold is 0.55, not 0.60 as in X18. X23 adds structural complexity
(3 exit paths instead of 1), so we accept slightly lower bootstrap confidence
as long as WFO compensates.


### T5: Jackknife (leave-year-out)

**Purpose**: Stability across time periods.

**Procedure** (matches X18's approach exactly):

1. Run E5 sim on FULL data → `nav_e5_full`, `trades_e5_full`
2. Run X23-fixed sim on FULL data (using full-sample model & score quantiles) →
   `nav_x23_full`, `trades_x23_full`
3. For each year Y in JK_YEARS:
   a. Identify bar range `[ys, ye]` for year Y
   b. Build `kept` index array = all reporting bars NOT in `[ys, ye]`
   c. Filter trades: exclude trades with `entry_bar` in `[ys, ye]`
   d. Compute `m_e5_jk = _metrics(nav_e5_full[kept], 0, n_trades_e5_kept)`
   e. Compute `m_x23_jk = _metrics(nav_x23_full[kept], 0, n_trades_x23_kept)`
   f. Record `d_sharpe = m_x23_jk.sharpe - m_e5_jk.sharpe`

**Key**: no retraining per fold. Full-sample model is used throughout.
The jackknife tests whether the improvement is concentrated in one year
(which would cause d_sharpe to flip sign when that year is removed).

**Gate G4**: At most 2 out of 6 leave-out folds have `d_sharpe < 0`.


### T6: PSR with DOF Correction

**Purpose**: Selection bias adjustment.

**Procedure**:
1. Compute annualized Sharpe of X23-fixed from full-sample T0
2. Compute number of H4 returns in reporting window
3. Compute PSR using E0_EFFECTIVE_DOF as benchmark SR0:
   ```python
   from research.lib.dsr import benchmark_sr0
   sr0 = benchmark_sr0(E0_EFFECTIVE_DOF)
   psr = _psr(sharpe_x23, n_returns, sr0)
   ```

**Gate G5**: `PSR > 0.95`.


### T7: Summary Table & Verdict

Collect all gate results and print summary:

```
| Gate | Test | Criterion           | Result | Pass? |
|------|------|---------------------|--------|-------|
| G0   | T0   | d_sharpe > 0 vs E5  |        |       |
| G1   | T3   | X23-fixed WFO>=3/4  |        |       |
| G2   | T4   | P(d_sh > 0) > 0.55  |        |       |
| G3   | T4   | med d_mdd <= +5pp   |        |       |
| G4   | T5   | JK neg <= 2/6       |        |       |
| G5   | T6   | PSR > 0.95          |        |       |
```

**Verdict**:
- **PROMOTE**: ALL 6 gates pass → X23 is a proven improvement
- **HOLD**: 4-5 gates pass → promising but insufficient evidence
- **REJECT**: <= 3 gates pass → architecture does not improve over E5


## 12. Validation Gates Summary

| Gate | Source | Criterion | Rationale |
|------|--------|-----------|-----------|
| G0 | T0 full-sample | d_sharpe(X23-fixed, E5) > 0 | Basic sanity |
| G1 | T3 WFO | X23-fixed: win_rate >= 75%, mean d > 0 | OOS stability |
| G2 | T4 bootstrap | P(d_sharpe > 0) > 55% | Statistical robustness |
| G3 | T4 bootstrap | median d_mdd <= +5.0 pp | MDD not catastrophically worse |
| G4 | T5 jackknife | neg folds <= 2/6 | Temporal stability |
| G5 | T6 PSR | PSR > 0.95 | Selection bias correction |


## 13. Optional V2 Extension: Peak Age Decay

Only implemented AFTER V1 (core X23) passes at least G0+G1.

### 13.1. Rule

If peak_age >= 10 bars, reduce trail multiplier by 0.5:

```python
peak_age = i - peak_bar
if peak_age >= PEAK_AGE_THRESHOLD:   # PEAK_AGE_THRESHOLD = 10
    m_t = max(m_t - 0.5, M_WEAK)    # floor at M_WEAK to prevent over-tightening
```

### 13.2. Additional constants

```python
PEAK_AGE_THRESHOLD = 10              # bars since peak before decay
PEAK_AGE_DECAY = 0.5                 # multiplier reduction
```

### 13.3. Floor discussion

**Deviation from đề cương**: The đề cương specifies `m_t := m_t - 0.5` without
a floor. This spec adds `max(..., M_WEAK)` which means peak_age has **no effect
in weak state** (2.25 - 0.5 = 1.75, floored back to 2.25).

This is a conservative choice. Alternatives to consider if V2 shows no effect:
- Lower floor to 1.5 (allows weak to tighten to 1.75)
- No floor at all (allows weak to reach 1.75, strong to reach 3.75)
- The đề cương's raw formula (m_t - 0.5 unclamped)

### 13.4. DOF impact

+2 preset params (threshold=10, decay=0.5). Still zero tuned DOF.

### 13.5. Implementation

Add to `_run_sim_x23()` as a flag:
```python
def _run_sim_x23(..., enable_peak_age=False,
                 peak_age_threshold=10, peak_age_decay=0.5):
```


## 14. Optional V3 Extension: Strong-State Hysteresis

Only implemented AFTER V2 results are available.

### 14.1. Rule

In strong state, require 2 consecutive closes below trail for exit:

```python
# Reset on new peak (BEFORE trail check)
if p >= peak:
    prev_trail_breach = False

if cur_state == "strong":
    trail_breach = (p < trail_level)
    if trail_breach and prev_trail_breach:
        → exit
    prev_trail_breach = trail_breach
else:
    if p < trail_level:
        → exit
    prev_trail_breach = False
```

### 14.2. Additional state

```python
prev_trail_breach = False   # reset on entry AND on new peak (see code above)
```

### 14.3. DOF impact

+0 new params (the "2 consecutive closes" is a binary structural choice).


## 15. Output Artifacts

### 15.1. `x23_results.json`

```json
{
    "study_id": "X23",
    "timestamp": "ISO-8601",
    "constants": { ... },
    "t0_fullsample": {
        "e0": {"sharpe": ..., "cagr": ..., "mdd": ..., "trades": ...},
        "e5": { ... },
        "x23_fixed": { ... },
        "x23_cal": { ... },
        "calibrated_multipliers": {"weak": ..., "normal": ..., "strong": ...}
    },
    "t1_churn": {
        "e0": {"trail": ..., "churn_trail": ..., "churn_rate": ...},
        "e5": { ... },
        "x23_fixed": { ... }
    },
    "t2_pullback": {
        "weak": {"n": ..., "mean": ..., "q75": ..., "q90": ...},
        "normal": { ... },
        "strong": { ... }
    },
    "t3_wfo": {
        "folds": [...],
        "win_rate_fixed": ...,
        "win_rate_cal": ...,
        "mean_d_fixed": ...,
        "mean_d_cal": ...
    },
    "t4_bootstrap": {
        "P_d_sharpe_gt_0": ...,
        "median_d_sharpe": ...,
        "median_d_mdd": ...
    },
    "t5_jackknife": {
        "years": [...],
        "n_negative": ...
    },
    "t6_psr": {
        "sharpe": ...,
        "psr": ...,
        "sr0": ...
    },
    "gates": {
        "G0": {"pass": bool, "value": ...},
        "G1": {"pass": bool, "value": ...},
        "G2": {"pass": bool, "value": ...},
        "G3": {"pass": bool, "value": ...},
        "G4": {"pass": bool, "value": ...},
        "G5": {"pass": bool, "value": ...}
    },
    "verdict": "PROMOTE" | "HOLD" | "REJECT"
}
```

### 15.2. `x23_report.md`

Human-readable markdown report with all tables and gate results.
Generated by `benchmark.py` at the end of execution.


## 16. Execution Plan

### Phase 1: Implement benchmark.py

1. Copy indicator functions from X18 (verbatim)
2. Copy model functions from X18 (verbatim)
3. Copy E0 sim from X18 (verbatim)
4. Implement E5 sim (E0 + robust ATR swap)
5. Implement `_precompute_scores()`
6. Implement `_run_sim_x23()` (Section 9)
7. Implement `_calibrate_pullback()` (Section 10)
8. Implement T0 through T7
9. Implement `main()` orchestrator

### Phase 2: Run & Analyze

1. Run `python research/x23/benchmark.py`
2. Review T0 (does d_sharpe > 0?)
3. Review T1 (does churn actually decrease?)
4. Review T2 (are calibrated multipliers close to presets?)
5. If G0 fails: STOP. Exit geometry hypothesis is wrong.
6. If G0 passes: continue to T3-T6

### Phase 3: V2 Extension (conditional)

Only if V1 passes G0+G1:
1. Enable peak_age flag
2. Re-run benchmark
3. Compare V1 vs V2

### Phase 4: V3 Extension (conditional)

Only if V2 results available:
1. Enable strong hysteresis
2. Re-run benchmark
3. Compare V1 vs V2 vs V3


## 17. Critical Implementation Notes

### 17.1. rATR NaN handling

Robust ATR has NaN for first 119 indices (0..118), valid from index 119. All checks
must guard against NaN:
```python
if np.isnan(ratr[i]):
    continue  # skip bar
```

The hard stop uses `entry_ratr = ratr[signal_bar]`. If signal_bar < 120,
entry_ratr could be NaN. Guard:
```python
if np.isnan(entry_ratr):
    hard_stop = -np.inf       # effectively disabled
    arm_threshold = np.inf    # trail never arms → only trend exit works
```

In practice, with WARMUP=365 days (~2190 H4 bars), this should never occur.

### 17.2. Fill convention

Signals at bar t → fill at bar t+1 using `cl[t]` as price proxy (same as
X18 convention). The `entry_bar` / `exit_bar` in trade dicts are the FILL bars
(t+1), not the SIGNAL bars (t).

### 17.3. Indicator computation on bootstrap paths

For bootstrap (T4), indicators are recomputed on each synthetic path:
```python
ef, es, vd, at_std = _compute_indicators(bcl, bhi, blo, bvo, btb)
bratr = _compute_ratr(bhi, blo, bcl)
```

Regime and d1_str are borrowed from real data (positionally matched):
```python
breg = regime_pw[:n_b]
bd1str = d1_str_pw[:n_b]
```

This is identical to X18's approach.

### 17.4. WFO training data slicing

When training on `cl[:train_end+1]`, all indicator arrays must be sliced
to the same length. The E0 sim is run on sliced arrays. The model is trained
on trades from this sliced sim.

Score quantiles are estimated from scores computed on the training slice only:
```python
train_scores = scores[:train_end+1]
valid_scores = train_scores[~np.isnan(train_scores)]
score_q15 = np.percentile(valid_scores, SCORE_Q_LO)
score_q85 = np.percentile(valid_scores, SCORE_Q_HI)
```

### 17.5. No optimization over X23 parameters

All X23 parameters (HARD_MULT, ARM_MULT, M_WEAK, M_NORMAL, M_STRONG,
SCORE_Q_LO, SCORE_Q_HI) are PRESET by this spec. They are NOT optimized
on training data. This is the key DOF control.

The only "fitted" component is the logistic model, which is retrained per
fold (same as X18). The score quantiles are data-dependent but use fixed
percentile levels (15th, 85th).

The calibrated multiplier variant (X23-cal) does fit multipliers to training
data, but using fixed quantile levels (Q75, Q85, Q90). The actual multiplier
values are deterministic functions of the training pullback distribution.

### 17.6. Comparison to E5, not E0

Previous X-series studies compared to E0 (standard ATR). X23 compares to
**E5** (robust ATR) because:
- X23 uses robust ATR for its trail
- E5 is the current production candidate
- Comparing to E0 would conflate the ATR improvement with the exit geometry
  improvement

E0 is still computed for reference and churn analysis continuity.

### 17.7. Peak anchor assumption

Peak anchor throughout this spec is **highest close** since entry, not highest
high. This follows the đề cương: "phải test highest close trước khi thử highest
high. Highest close thường ít nhạy hơn với spike/wick."

**If peak anchor is changed to highest high**, ALL of the following must be
redone from scratch:
- Pullback calibration (Section 10) — pullback depth changes
- Preset multiplier values — no longer valid
- All validation results

Do NOT reuse V1 multipliers with a different peak definition.

### 17.8. Exit priority

When multiple exit conditions trigger on the same bar, priority is:
1. Hard stop (checked first)
2. Trend failure (checked second)
3. Trail stop (checked third, only if armed)

Only one exit fires per bar. The first matching condition wins.
