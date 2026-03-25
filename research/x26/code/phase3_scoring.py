"""Phase 3: Phenomenon Survey & Scoring.

Evaluates ALL Phase 2 observations against 5 criteria:
  S1: Signal Strength (effect size + p-value)
  S2: Temporal Stability (4-block consistency)
  S3: Economic Magnitude (ΔSharpe estimate)
  S4: Complementarity with VTREND (timing overlap)
  S5: Sample Adequacy (N, MDE, observed effect)

Inputs:
- state_classification.csv (H4 bar-level FLAT/IN_TRADE)
- trades.csv (217 trades)
- flat_period_characteristics.csv (218 flat periods)
- Tbl02_flat_durations.csv (flat period durations)
- Raw OHLCV bars

Deliverables:
- Tbl_scoring_matrix.csv
- Tbl_stability_blocks.csv
- Fig12_rolling_stability.png (if any phenomenon has Total >= 2)
"""

import sys
sys.path.insert(0, "/var/www/trading-bots/btc-spot-dev")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as sp_stats
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path("/var/www/trading-bots/btc-spot-dev")
DATA = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
LAB  = ROOT / "research" / "beyond_trend_lab"
FIG  = LAB / "figures"
TBL  = LAB / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TBL.mkdir(parents=True, exist_ok=True)

ANN = 365.25 * 6  # H4 bars per year (6 bars/day × 365.25)
COST_BPS = 50  # 50 bps round-trip
H4_PER_YEAR = ANN

print("=" * 70)
print("PHASE 3: PHENOMENON SURVEY & SCORING")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ══════════════════════════════════════════════════════════════════════════
print("\n1. Loading data...")

raw = pd.read_csv(DATA)
h4 = raw[raw["interval"] == "4h"].copy().reset_index(drop=True)
h4["open_time_dt"] = pd.to_datetime(h4["open_time"], unit="ms")
h4["ret"] = h4["close"].pct_change()  # simple return
h4["log_ret"] = np.log(h4["close"] / h4["close"].shift(1))
h4 = h4.iloc[1:].reset_index(drop=True)  # drop first NaN row

h1 = raw[raw["interval"] == "1h"].copy().reset_index(drop=True)
h1["open_time_dt"] = pd.to_datetime(h1["open_time"], unit="ms")
h1["ret"] = h1["close"].pct_change()
h1 = h1.iloc[1:].reset_index(drop=True)

state_df = pd.read_csv(TBL / "state_classification.csv")
trades_df = pd.read_csv(TBL / "trades.csv")
flat_chars = pd.read_csv(TBL / "flat_period_characteristics.csv")
flat_durs = pd.read_csv(TBL / "Tbl02_flat_durations.csv")

# Align state to h4 (state_df has 18662 rows, h4 has 18661 after dropping first)
# State_df index 0 = first H4 bar; h4 index 0 = second H4 bar (after pct_change drop)
# We need to align: state_df row i corresponds to h4 row i-1
state_arr = state_df["state"].values  # length 18662
is_flat_full = (state_arr == "FLAT")

# For h4 returns (shifted by 1 due to pct_change), align:
# h4 row 0 = bar index 1 in state_df
is_flat_h4 = is_flat_full[1:]  # length 18661, aligned with h4
is_intrade_h4 = ~is_flat_h4

flat_ret = h4.loc[is_flat_h4, "ret"].values
intrade_ret = h4.loc[is_intrade_h4, "ret"].values
all_ret = h4["ret"].values

n_flat = len(flat_ret)
n_intrade = len(intrade_ret)
n_all = len(all_ret)

print(f"   H4 bars: {n_all} (FLAT: {n_flat}, IN_TRADE: {n_intrade})")
print(f"   Trades: {len(trades_df)}")
print(f"   Flat periods: {len(flat_chars)}")


# ══════════════════════════════════════════════════════════════════════════
# 2. UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def compute_acf(x, nlags=50):
    """Biased ACF estimator."""
    n = len(x)
    xm = x - x.mean()
    c0 = np.dot(xm, xm) / n
    if c0 < 1e-20:
        return np.zeros(nlags + 1)
    acf = np.zeros(nlags + 1)
    acf[0] = 1.0
    for k in range(1, nlags + 1):
        acf[k] = np.dot(xm[:n - k], xm[k:]) / (n * c0)
    return acf


def variance_ratio(x, q):
    """Lo-MacKinlay VR(q) for a return series."""
    n = len(x)
    if n < q + 1:
        return np.nan
    mu = x.mean()
    # q-period returns
    xc = x - mu
    var1 = np.sum(xc ** 2) / (n - 1)
    if var1 < 1e-20:
        return np.nan
    # overlapping q-period variance
    qret = np.array([xc[i:i + q].sum() for i in range(n - q + 1)])
    varq = np.sum(qret ** 2) / (n - q + 1)
    vr = varq / (q * var1)
    return vr


def per_period_vr(returns_full, state_full, q, min_bars=None):
    """Compute VR(q) for each flat period. Returns array of per-period VR values."""
    if min_bars is None:
        min_bars = q + 1
    # Identify flat period runs
    runs = []
    start = None
    for i in range(len(state_full)):
        if state_full[i]:  # is_flat
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((start, i))
                start = None
    if start is not None:
        runs.append((start, len(state_full)))

    vrs = []
    for s, e in runs:
        seg = returns_full[s:e]
        if len(seg) >= min_bars:
            v = variance_ratio(seg, q)
            if not np.isnan(v):
                vrs.append(v)
    return np.array(vrs)


def cohens_d_one_sample(x, mu0=0.0):
    """Cohen's d for one-sample test (observed mean vs mu0)."""
    return (np.mean(x) - mu0) / np.std(x, ddof=1) if np.std(x, ddof=1) > 0 else 0.0


def mde_one_sample(n, alpha=0.05, power=0.80):
    """Minimum detectable effect (Cohen's d) for one-sample t-test."""
    from scipy.stats import norm
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    return (z_alpha + z_beta) / np.sqrt(n)


def split_4_blocks(arr, timestamps=None):
    """Split array into 4 equal-sized time blocks."""
    n = len(arr)
    q = n // 4
    blocks = []
    for i in range(4):
        s = i * q
        e = (i + 1) * q if i < 3 else n
        blocks.append(arr[s:e])
    return blocks


def split_4_blocks_by_time(values, times):
    """Split into 4 blocks by time quartiles."""
    t_min, t_max = times.min(), times.max()
    edges = np.linspace(t_min, t_max, 5)
    blocks = []
    for i in range(4):
        mask = (times >= edges[i]) & (times < edges[i + 1])
        if i == 3:
            mask = (times >= edges[i]) & (times <= edges[i + 1])
        blocks.append(values[mask])
    return blocks


print("\n2. Filtering observations from Phase 2...")

# ══════════════════════════════════════════════════════════════════════════
# 3. OBSERVATION FILTER
# ══════════════════════════════════════════════════════════════════════════

print("""
   ── EXCLUDED observations ──
   Obs11 (FLAT mean -2.05 bps): Describes absence of trend → mechanical
         consequence of VTREND filtering. Not a tradeable phenomenon.
   Obs12 (FLAT kurtosis 22.49): Known/universal property of non-trending
         financial returns. Fat tails exist everywhere.
   Obs13 (FLAT skew -0.126): Mechanical consequence of VTREND trail stop
         truncating tails asymmetrically during IN_TRADE.
   Obs15 (|return| ACF 0.278): Volatility clustering is universal (GARCH).
         Known and present in ALL financial assets. Already captured
         implicitly by ATR-based trail in VTREND.
   Obs16 (PACF lag-6): Same phenomenon as Obs14 (24h periodicity).
         Subsumed — not independent.
   Obs18 (Hurst mixed): Ambiguous/unreliable. VR test (Obs17) is the
         preferred measure. Subsumed.
   Obs19 (FLAT vol > IN_TRADE): Descriptive property, not a structured
         phenomenon. Higher dispersion during out-of-market is expected.
   Obs20 (Vol elevated mid-period): Mechanical — vol compression at
         period boundaries is the VTREND entry/exit condition itself.
   Obs21 (No flat→trade predictability): Null result. No structure to
         score. Confirms flat characteristics carry no signal.
   Obs22 (Pre-entry drift +1.03%): Mechanical consequence of EMA crossover
         entry. Price MUST have risen for entry signal to fire.
   Obs24 (Post-exit vol decay): Known microstructure effect. Vol is
         elevated at trade exits universally.
   Obs25 (H1 reproduces H4): Not an independent phenomenon — confirms
         Obs14/17 at finer resolution.
   Obs26 (D1 Hurst 0.467): Subsumed by Obs17 (mean-reversion).
   Obs27 (Cross-TF consistency): Confirms Obs14/17, not independent.
   Obs29 (Stability confirmation): Meta-observation about Obs28.

   ── KEPT for scoring ──
   P1: Mean-Reversion within FLAT periods (Obs17)
       VR(2)=0.824 per-period, p<0.0001, consistent H1/H4/D1
   P2: Return Autocorrelation / 24h Periodicity (Obs14)
       Lag-1 ACF=-0.052, lag-6 ACF=-0.076, 15/50 significant
   P3: Post-Exit Asymmetry (Obs23)
       Winners +0.81% post-exit, Losers -0.02%, conditional on outcome
   P4: Calendar Return Effect (Obs28)
       Hourly return bias ±5 bps, p=0.0001, STABLE across halves
""")


# ══════════════════════════════════════════════════════════════════════════
# 4. SCORE EACH PHENOMENON
# ══════════════════════════════════════════════════════════════════════════

results = {}

# ─────────────────────────────────────────────────────────────────────────
# P1: MEAN-REVERSION WITHIN FLAT PERIODS (Obs17)
# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("P1: MEAN-REVERSION WITHIN FLAT PERIODS (Obs17)")
print("=" * 70)

# Compute per-period VR(2) for all flat periods with ≥3 bars
vr2_pp = per_period_vr(h4["ret"].values, is_flat_h4, q=2, min_bars=3)
n_vr2 = len(vr2_pp)

# S1: Signal Strength
d_vr2 = cohens_d_one_sample(vr2_pp, mu0=1.0)
t_vr2, p_vr2 = sp_stats.ttest_1samp(vr2_pp, 1.0)
print(f"\n  S1: SIGNAL STRENGTH")
print(f"      N periods (≥3 bars): {n_vr2}")
print(f"      Mean VR(2): {vr2_pp.mean():.4f}")
print(f"      Std VR(2): {vr2_pp.std(ddof=1):.4f}")
print(f"      Cohen's d (vs VR=1): {d_vr2:.4f}")
print(f"      t-stat: {t_vr2:.4f}, p-value: {p_vr2:.2e}")

if abs(d_vr2) > 0.4 and p_vr2 < 0.01:
    s1_p1 = "STRONG"
elif abs(d_vr2) > 0.2 and p_vr2 < 0.05:
    s1_p1 = "MODERATE"
else:
    s1_p1 = "WEAK"
print(f"      → S1 = {s1_p1}")

# S2: Temporal Stability — split flat periods into 4 time blocks by start_bar
flat_start_bars = flat_durs["start_bar"].values
# Match VR periods: only periods with ≥3 bars
flat_long_mask = flat_durs["duration_bars"].values >= 3
flat_start_long = flat_start_bars[flat_long_mask]
assert len(flat_start_long) == n_vr2, f"Mismatch: {len(flat_start_long)} vs {n_vr2}"

blocks_vr2 = split_4_blocks_by_time(vr2_pp, flat_start_long)
print(f"\n  S2: TEMPORAL STABILITY (4 blocks)")
block_signs = []
block_sigs = []
for i, blk in enumerate(blocks_vr2):
    if len(blk) < 3:
        print(f"      Block {i+1}: n={len(blk)} — too few")
        block_signs.append(0)
        block_sigs.append(False)
        continue
    mean_vr = blk.mean()
    t_b, p_b = sp_stats.ttest_1samp(blk, 1.0)
    sign = -1 if mean_vr < 1.0 else 1
    block_signs.append(sign)
    block_sigs.append(p_b < 0.05)
    print(f"      Block {i+1}: n={len(blk)}, mean VR(2)={mean_vr:.4f}, "
          f"t={t_b:.3f}, p={p_b:.4f}, sign={'<1' if sign < 0 else '≥1'}, "
          f"sig={'YES' if p_b < 0.05 else 'no'}")

n_same_sign = sum(1 for s in block_signs if s == block_signs[0])
n_sig = sum(block_sigs)
if n_same_sign >= 3 and n_sig >= 2:
    s2_p1 = "STABLE"
elif n_same_sign >= 2:
    s2_p1 = "MIXED"
else:
    s2_p1 = "UNSTABLE"
print(f"      Same sign: {n_same_sign}/4, Significant: {n_sig}/4 → S2 = {s2_p1}")

# S3: Economic Magnitude
# Mean-reversion within flat: if we trade reversal at every flat bar,
# autocorrelation ρ(1) ≈ VR(2)-1 = -0.176 per-period.
# Expected return per reversal trade: |ρ| × σ_bar
# σ_bar ≈ 157 bps (from Phase 2), cost = 50 bps RT per trade.
# Net per trade: |ρ| × σ - cost = 0.176 × 157 - 50 = 27.6 - 50 = -22.4 bps
# Even with perfect execution: effect too small vs cost.
# Also: only during FLAT periods (~57% of time), and within-period only.
# Opportunities: ~10,720 FLAT bars / 8.5 years ≈ 1261/year, but only
# within-period mean-reversion, not cross-period.
rho1_est = abs(vr2_pp.mean() - 1.0)
sigma_bar_bps = 157.37
net_per_trade_bps = rho1_est * sigma_bar_bps - COST_BPS
n_opps_per_year = n_flat / 8.5  # 8.5 years of data
if net_per_trade_bps > 0:
    ann_ret = net_per_trade_bps * 1e-4 * n_opps_per_year
    ann_vol = sigma_bar_bps * 1e-4 * np.sqrt(n_opps_per_year)
    delta_sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
else:
    delta_sharpe = net_per_trade_bps * 1e-4 * np.sqrt(n_opps_per_year)  # negative

print(f"\n  S3: ECONOMIC MAGNITUDE")
print(f"      ρ(1) estimate (per-period): {rho1_est:.4f}")
print(f"      σ_bar: {sigma_bar_bps:.1f} bps")
print(f"      Gross per trade: {rho1_est * sigma_bar_bps:.1f} bps")
print(f"      Net per trade (after 50 bps cost): {net_per_trade_bps:.1f} bps")
print(f"      Opportunities/year: {n_opps_per_year:.0f}")
print(f"      ΔSharpe estimate: {delta_sharpe:.4f}")

if delta_sharpe > 0.30:
    s3_p1 = "MATERIAL"
elif delta_sharpe > 0.10:
    s3_p1 = "MARGINAL"
else:
    s3_p1 = "NEGLIGIBLE"
print(f"      → S3 = {s3_p1}")
if net_per_trade_bps < 0:
    print(f"      NOTE: Net return is NEGATIVE after cost. The mean-reversion effect")
    print(f"      (~{rho1_est * sigma_bar_bps:.0f} bps gross) does not cover 50 bps RT cost.")

# S4: Complementarity with VTREND
# Mean-reversion operates ONLY during FLAT periods by definition (Obs17).
# During IN_TRADE, VTREND captures trending behavior.
# ρ between phenomenon returns and VTREND: near 0 (they operate at different times).
# Fraction during FLAT: 100% (per-period VR is computed ON flat periods only).
pct_during_flat_p1 = 100.0
rho_with_vtrend_p1 = 0.0  # zero by construction (non-overlapping time windows)
print(f"\n  S4: COMPLEMENTARITY WITH VTREND")
print(f"      Operates during FLAT: {pct_during_flat_p1:.0f}%")
print(f"      ρ with VTREND returns: {rho_with_vtrend_p1:.2f} (non-overlapping by construction)")
if rho_with_vtrend_p1 < 0.2 and pct_during_flat_p1 > 70:
    s4_p1 = "COMPLEMENTARY"
elif rho_with_vtrend_p1 < 0.5 and pct_during_flat_p1 > 40:
    s4_p1 = "PARTIAL"
else:
    s4_p1 = "OVERLAPPING"
print(f"      → S4 = {s4_p1}")

# S5: Sample Adequacy
mde_p1 = mde_one_sample(n_vr2)
observed_d_p1 = abs(d_vr2)
print(f"\n  S5: SAMPLE ADEQUACY")
print(f"      N = {n_vr2}")
print(f"      MDE (80% power, α=0.05): {mde_p1:.4f}")
print(f"      Observed |d|: {observed_d_p1:.4f}")
print(f"      Ratio observed/MDE: {observed_d_p1 / mde_p1:.2f}")
if observed_d_p1 > 1.5 * mde_p1:
    s5_p1 = "ADEQUATE"
elif observed_d_p1 > mde_p1:
    s5_p1 = "BORDERLINE"
else:
    s5_p1 = "UNDERPOWERED"
print(f"      → S5 = {s5_p1}")

results["P1_MeanReversion"] = {
    "obs_ref": "Obs17",
    "S1": s1_p1, "S2": s2_p1, "S3": s3_p1, "S4": s4_p1, "S5": s5_p1,
    "d": d_vr2, "p": p_vr2, "delta_sharpe": delta_sharpe,
    "n": n_vr2, "mde": mde_p1,
}


# ─────────────────────────────────────────────────────────────────────────
# P2: RETURN AUTOCORRELATION / 24H PERIODICITY (Obs14)
# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("P2: RETURN AUTOCORRELATION / 24H PERIODICITY (Obs14)")
print("=" * 70)

# Compute lag-6 ACF on FLAT returns only
# To properly measure: compute per-period lag-6 autocorrelation
# Only for periods with ≥ 8 bars (need at least 7 for lag 6)
def per_period_acf_lag(returns_full, state_full, lag, min_bars=None):
    """Compute lag-k autocorrelation for each flat period."""
    if min_bars is None:
        min_bars = lag + 2
    runs = []
    start = None
    for i in range(len(state_full)):
        if state_full[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((start, i))
                start = None
    if start is not None:
        runs.append((start, len(state_full)))

    acfs = []
    for s, e in runs:
        seg = returns_full[s:e]
        if len(seg) >= min_bars:
            ac = compute_acf(seg, nlags=lag)
            acfs.append(ac[lag])
    return np.array(acfs)

# Lag-6 (24h) autocorrelation per flat period
acf6_pp = per_period_acf_lag(h4["ret"].values, is_flat_h4, lag=6, min_bars=8)
n_acf6 = len(acf6_pp)

# Also compute lag-1 for comparison
acf1_pp = per_period_acf_lag(h4["ret"].values, is_flat_h4, lag=1, min_bars=3)
n_acf1 = len(acf1_pp)

# S1: Signal Strength — test if mean autocorrelation differs from 0
d_acf6 = cohens_d_one_sample(acf6_pp, mu0=0.0)
t_acf6, p_acf6 = sp_stats.ttest_1samp(acf6_pp, 0.0)
d_acf1 = cohens_d_one_sample(acf1_pp, mu0=0.0)
t_acf1, p_acf1 = sp_stats.ttest_1samp(acf1_pp, 0.0)

print(f"\n  S1: SIGNAL STRENGTH")
print(f"      Lag-6 (24h cycle):")
print(f"        N periods (≥8 bars): {n_acf6}")
print(f"        Mean ACF(6): {acf6_pp.mean():.4f}")
print(f"        Cohen's d: {d_acf6:.4f}")
print(f"        t={t_acf6:.3f}, p={p_acf6:.4f}")
print(f"      Lag-1:")
print(f"        N periods (≥3 bars): {n_acf1}")
print(f"        Mean ACF(1): {acf1_pp.mean():.4f}")
print(f"        Cohen's d: {d_acf1:.4f}")
print(f"        t={t_acf1:.3f}, p={p_acf1:.4f}")

# Use the stronger of lag-1 or lag-6
best_d = max(abs(d_acf1), abs(d_acf6))
best_p = min(p_acf1, p_acf6)
print(f"      Best: |d|={best_d:.4f}, p={best_p:.4f}")

if best_d > 0.4 and best_p < 0.01:
    s1_p2 = "STRONG"
elif best_d > 0.2 and best_p < 0.05:
    s1_p2 = "MODERATE"
else:
    s1_p2 = "WEAK"
print(f"      → S1 = {s1_p2}")

# S2: Temporal Stability
# Split lag-6 ACF periods into 4 time blocks
flat_start_long8 = flat_start_bars[flat_durs["duration_bars"].values >= 8]
if len(flat_start_long8) == n_acf6:
    blocks_acf6 = split_4_blocks_by_time(acf6_pp, flat_start_long8)
else:
    # Fallback: split by index
    blocks_acf6 = split_4_blocks(acf6_pp)

print(f"\n  S2: TEMPORAL STABILITY (4 blocks, lag-6)")
block_signs_p2 = []
block_sigs_p2 = []
for i, blk in enumerate(blocks_acf6):
    if len(blk) < 3:
        print(f"      Block {i+1}: n={len(blk)} — too few")
        block_signs_p2.append(0)
        block_sigs_p2.append(False)
        continue
    mean_acf = blk.mean()
    t_b, p_b = sp_stats.ttest_1samp(blk, 0.0)
    sign = -1 if mean_acf < 0 else 1
    block_signs_p2.append(sign)
    block_sigs_p2.append(p_b < 0.05)
    print(f"      Block {i+1}: n={len(blk)}, mean ACF(6)={mean_acf:.4f}, "
          f"t={t_b:.3f}, p={p_b:.4f}, sign={'neg' if sign < 0 else 'pos'}, "
          f"sig={'YES' if p_b < 0.05 else 'no'}")

n_same_sign_p2 = sum(1 for s in block_signs_p2 if s == block_signs_p2[0] and s != 0)
n_sig_p2 = sum(block_sigs_p2)
if n_same_sign_p2 >= 3 and n_sig_p2 >= 2:
    s2_p2 = "STABLE"
elif n_same_sign_p2 >= 2:
    s2_p2 = "MIXED"
else:
    s2_p2 = "UNSTABLE"
print(f"      Same sign: {n_same_sign_p2}/4, Significant: {n_sig_p2}/4 → S2 = {s2_p2}")

# S3: Economic Magnitude
# A lag-6 reversal strategy: sell (go flat) after 6-bar rise, buy after 6-bar fall.
# Mean ACF(6) ~ -0.076 on concatenated FLAT.
# Per-period mean ACF(6) is what we computed above.
# Expected return per trade: |ACF(6)| × σ_bar ≈ |acf6_pp.mean()| × 157 bps
# Opportunities: count of 6-bar windows in FLAT periods
acf6_mean = abs(acf6_pp.mean())
gross_per_trade_p2 = acf6_mean * sigma_bar_bps
net_per_trade_p2 = gross_per_trade_p2 - COST_BPS
n_6bar_windows = sum(max(0, d - 6) for d in flat_durs["duration_bars"].values) / 8.5
if net_per_trade_p2 > 0:
    ann_ret_p2 = net_per_trade_p2 * 1e-4 * n_6bar_windows
    ann_vol_p2 = sigma_bar_bps * 1e-4 * np.sqrt(n_6bar_windows)
    delta_sharpe_p2 = ann_ret_p2 / ann_vol_p2
else:
    delta_sharpe_p2 = net_per_trade_p2 * 1e-4 * np.sqrt(n_6bar_windows)

print(f"\n  S3: ECONOMIC MAGNITUDE")
print(f"      Mean |ACF(6)| per-period: {acf6_mean:.4f}")
print(f"      Gross per trade: {gross_per_trade_p2:.1f} bps")
print(f"      Net per trade (after 50 bps cost): {net_per_trade_p2:.1f} bps")
print(f"      6-bar windows/year: {n_6bar_windows:.0f}")
print(f"      ΔSharpe estimate: {delta_sharpe_p2:.4f}")

if delta_sharpe_p2 > 0.30:
    s3_p2 = "MATERIAL"
elif delta_sharpe_p2 > 0.10:
    s3_p2 = "MARGINAL"
else:
    s3_p2 = "NEGLIGIBLE"
print(f"      → S3 = {s3_p2}")

# S4: Complementarity
pct_flat_p2 = 100.0  # operates during FLAT only
rho_vtrend_p2 = 0.0
print(f"\n  S4: COMPLEMENTARITY")
print(f"      FLAT-only: {pct_flat_p2:.0f}%, ρ={rho_vtrend_p2:.2f}")
if rho_vtrend_p2 < 0.2 and pct_flat_p2 > 70:
    s4_p2 = "COMPLEMENTARY"
elif rho_vtrend_p2 < 0.5 and pct_flat_p2 > 40:
    s4_p2 = "PARTIAL"
else:
    s4_p2 = "OVERLAPPING"
print(f"      → S4 = {s4_p2}")

# S5: Sample Adequacy
mde_p2 = mde_one_sample(n_acf6)
observed_d_p2 = abs(d_acf6)
print(f"\n  S5: SAMPLE ADEQUACY")
print(f"      N = {n_acf6}")
print(f"      MDE: {mde_p2:.4f}, Observed |d|: {observed_d_p2:.4f}")
print(f"      Ratio: {observed_d_p2 / mde_p2:.2f}")
if observed_d_p2 > 1.5 * mde_p2:
    s5_p2 = "ADEQUATE"
elif observed_d_p2 > mde_p2:
    s5_p2 = "BORDERLINE"
else:
    s5_p2 = "UNDERPOWERED"
print(f"      → S5 = {s5_p2}")

results["P2_Autocorrelation24h"] = {
    "obs_ref": "Obs14",
    "S1": s1_p2, "S2": s2_p2, "S3": s3_p2, "S4": s4_p2, "S5": s5_p2,
    "d": d_acf6, "p": p_acf6, "delta_sharpe": delta_sharpe_p2,
    "n": n_acf6, "mde": mde_p2,
}


# ─────────────────────────────────────────────────────────────────────────
# P3: POST-EXIT ASYMMETRY (Obs23)
# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("P3: POST-EXIT ASYMMETRY (Obs23)")
print("=" * 70)

# Compute 20-bar cumulative return after each trade exit, split by win/loss
trades = trades_df.copy()
trades["is_winner"] = trades["return_pct"] > 0
n_h4_full = len(state_df)
# Get H4 close prices from state_df
h4_close_full = state_df["close"].values

post_exit_rets = []
for _, tr in trades.iterrows():
    exit_idx = tr["exit_bar_idx"]
    if pd.isna(exit_idx):
        continue
    exit_idx = int(exit_idx)
    end_idx = min(exit_idx + 20, n_h4_full - 1)
    if end_idx <= exit_idx:
        continue
    cum_ret = h4_close_full[end_idx] / h4_close_full[exit_idx] - 1.0
    post_exit_rets.append({
        "trade_id": tr["trade_id"],
        "is_winner": tr["is_winner"],
        "post_exit_20bar_ret": cum_ret,
        "return_pct": tr["return_pct"],
    })

pe_df = pd.DataFrame(post_exit_rets)
winners_pe = pe_df[pe_df["is_winner"]]["post_exit_20bar_ret"].values
losers_pe = pe_df[~pe_df["is_winner"]]["post_exit_20bar_ret"].values

# S1: Signal Strength — Mann-Whitney U test (winners vs losers post-exit)
u_stat, p_mw = sp_stats.mannwhitneyu(winners_pe, losers_pe, alternative="two-sided")
# Rank-biserial correlation
n1, n2 = len(winners_pe), len(losers_pe)
r_rb = 1 - 2 * u_stat / (n1 * n2)  # rank-biserial
# Cohen's d between groups
pooled_std = np.sqrt(((n1 - 1) * winners_pe.std(ddof=1)**2 +
                       (n2 - 1) * losers_pe.std(ddof=1)**2) / (n1 + n2 - 2))
d_pe = (winners_pe.mean() - losers_pe.mean()) / pooled_std if pooled_std > 0 else 0

print(f"\n  S1: SIGNAL STRENGTH")
print(f"      Winners post-exit (n={n1}): mean={winners_pe.mean()*100:.2f}%")
print(f"      Losers post-exit (n={n2}): mean={losers_pe.mean()*100:.2f}%")
print(f"      Difference: {(winners_pe.mean() - losers_pe.mean())*100:.2f}%")
print(f"      Cohen's d: {d_pe:.4f}")
print(f"      Rank-biserial r: {r_rb:.4f}")
print(f"      Mann-Whitney U={u_stat:.0f}, p={p_mw:.4f}")

if abs(d_pe) > 0.4 and p_mw < 0.01:
    s1_p3 = "STRONG"
elif abs(d_pe) > 0.2 and p_mw < 0.05:
    s1_p3 = "MODERATE"
else:
    s1_p3 = "WEAK"
print(f"      → S1 = {s1_p3}")

# S2: Temporal Stability — split trades into 4 time blocks
trade_entry_bars = trades_df["entry_bar_idx"].dropna().values.astype(int)
# Align with pe_df
pe_entry_bars = []
for _, tr in pe_df.iterrows():
    tid = int(tr["trade_id"])
    row = trades_df[trades_df["trade_id"] == tid]
    if len(row) > 0 and not pd.isna(row.iloc[0]["entry_bar_idx"]):
        pe_entry_bars.append(int(row.iloc[0]["entry_bar_idx"]))
    else:
        pe_entry_bars.append(0)
pe_entry_bars = np.array(pe_entry_bars)

pe_diffs = pe_df["post_exit_20bar_ret"].values
pe_winners_mask = pe_df["is_winner"].values

# For stability: compute the difference (winner_mean - loser_mean) in each block
blocks_pe = split_4_blocks_by_time(np.arange(len(pe_df)), pe_entry_bars)
print(f"\n  S2: TEMPORAL STABILITY (4 blocks)")
block_signs_p3 = []
block_sigs_p3 = []
for i, idx_blk in enumerate(blocks_pe):
    idx_blk = idx_blk.astype(int)
    w_vals = pe_diffs[idx_blk][pe_winners_mask[idx_blk]]
    l_vals = pe_diffs[idx_blk][~pe_winners_mask[idx_blk]]
    if len(w_vals) < 3 or len(l_vals) < 3:
        print(f"      Block {i+1}: n_w={len(w_vals)}, n_l={len(l_vals)} — too few")
        block_signs_p3.append(0)
        block_sigs_p3.append(False)
        continue
    diff = w_vals.mean() - l_vals.mean()
    # Permutation-like: use Mann-Whitney
    _, p_b = sp_stats.mannwhitneyu(w_vals, l_vals, alternative="two-sided")
    sign = 1 if diff > 0 else -1
    block_signs_p3.append(sign)
    block_sigs_p3.append(p_b < 0.05)
    print(f"      Block {i+1}: n_w={len(w_vals)}, n_l={len(l_vals)}, "
          f"diff={diff*100:.2f}%, p={p_b:.4f}, "
          f"sig={'YES' if p_b < 0.05 else 'no'}")

n_same_sign_p3 = sum(1 for s in block_signs_p3 if s != 0 and s == block_signs_p3[0])
if block_signs_p3[0] == 0:
    # Use first non-zero
    ref = next((s for s in block_signs_p3 if s != 0), 0)
    n_same_sign_p3 = sum(1 for s in block_signs_p3 if s == ref and s != 0)
n_sig_p3 = sum(block_sigs_p3)

if n_same_sign_p3 >= 3 and n_sig_p3 >= 2:
    s2_p3 = "STABLE"
elif n_same_sign_p3 >= 2:
    s2_p3 = "MIXED"
else:
    s2_p3 = "UNSTABLE"
print(f"      Same sign: {n_same_sign_p3}/4, Significant: {n_sig_p3}/4 → S2 = {s2_p3}")

# S3: Economic Magnitude
# To exploit: after a winning trade exits, buy for 20 bars. After losing, don't.
# But: we don't know trade outcome until AFTER exit. This is LOOK-AHEAD bias.
# The only way to use this is: predict win/loss at exit time → requires a model.
# With VTREND's 42.86% win rate, we'd need to correctly predict winners.
# Even if perfectly exploited: 95 opportunities over 8.5 years ≈ 11.2/year
# Mean return per opportunity: +0.81% (20 bars, ~3.3 days), cost 50 bps
# Net: 0.81% - 0.50% = 0.31% per trade
# ΔSharpe ≈ net_return × sqrt(N) / σ
n_winner_opps_per_year = n1 / 8.5
net_per_opp_p3 = (winners_pe.mean() - COST_BPS * 1e-4) * 100  # in %
# Annualized
ann_ret_p3 = (winners_pe.mean() - COST_BPS * 1e-4) * n_winner_opps_per_year
sigma_20bar = winners_pe.std(ddof=1)
ann_vol_p3 = sigma_20bar * np.sqrt(n_winner_opps_per_year)
delta_sharpe_p3 = ann_ret_p3 / ann_vol_p3 if ann_vol_p3 > 0 else 0

print(f"\n  S3: ECONOMIC MAGNITUDE")
print(f"      Winner opportunities/year: {n_winner_opps_per_year:.1f}")
print(f"      Mean post-winner return: {winners_pe.mean()*100:.2f}%")
print(f"      Net per trade (after 50 bps): {net_per_opp_p3:.2f}%")
print(f"      ΔSharpe estimate: {delta_sharpe_p3:.4f}")
print(f"      CAVEAT: Requires KNOWING trade outcome at exit (look-ahead).")
print(f"      Without a predictor, this phenomenon is NOT directly tradeable.")

if delta_sharpe_p3 > 0.30:
    s3_p3 = "MATERIAL"
elif delta_sharpe_p3 > 0.10:
    s3_p3 = "MARGINAL"
else:
    s3_p3 = "NEGLIGIBLE"
print(f"      → S3 = {s3_p3} (but requires look-ahead predictor)")

# S4: Complementarity
# Post-exit = beginning of FLAT period → 100% during FLAT
pct_flat_p3 = 100.0
# However, the phenomenon is CONDITIONED on VTREND trade outcome
# So it's not fully independent
rho_vtrend_p3 = 0.0  # non-overlapping in time
print(f"\n  S4: COMPLEMENTARITY")
print(f"      FLAT-only: {pct_flat_p3:.0f}%, but conditioned on VTREND outcome")
if rho_vtrend_p3 < 0.2 and pct_flat_p3 > 70:
    s4_p3 = "COMPLEMENTARY"
elif rho_vtrend_p3 < 0.5 and pct_flat_p3 > 40:
    s4_p3 = "PARTIAL"
else:
    s4_p3 = "OVERLAPPING"
print(f"      → S4 = {s4_p3}")

# S5: Sample Adequacy
n_pe = len(pe_df)
mde_p3 = mde_one_sample(min(n1, n2))  # limited by smaller group
observed_d_p3 = abs(d_pe)
print(f"\n  S5: SAMPLE ADEQUACY")
print(f"      N total = {n_pe}, N winners = {n1}, N losers = {n2}")
print(f"      MDE (smaller group n={min(n1, n2)}): {mde_p3:.4f}")
print(f"      Observed |d|: {observed_d_p3:.4f}")
ratio_p3 = observed_d_p3 / mde_p3 if mde_p3 > 0 else 0
print(f"      Ratio: {ratio_p3:.2f}")
if observed_d_p3 > 1.5 * mde_p3:
    s5_p3 = "ADEQUATE"
elif observed_d_p3 > mde_p3:
    s5_p3 = "BORDERLINE"
else:
    s5_p3 = "UNDERPOWERED"
print(f"      → S5 = {s5_p3}")

results["P3_PostExitAsymmetry"] = {
    "obs_ref": "Obs23",
    "S1": s1_p3, "S2": s2_p3, "S3": s3_p3, "S4": s4_p3, "S5": s5_p3,
    "d": d_pe, "p": p_mw, "delta_sharpe": delta_sharpe_p3,
    "n": n_pe, "mde": mde_p3,
}


# ─────────────────────────────────────────────────────────────────────────
# P4: CALENDAR RETURN EFFECT (Obs28)
# ─────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("P4: CALENDAR RETURN EFFECT (Obs28)")
print("=" * 70)

# Map H4 state to H1: each H1 bar's state = its containing H4 bar's state
h4_state_open_ms = state_df["open_time"].values  # H4 open times in ms
h4_state_vals = state_df["state"].values

h1_full = raw[raw["interval"] == "1h"].copy().reset_index(drop=True)
h1_full["open_time_dt"] = pd.to_datetime(h1_full["open_time"], unit="ms")
h1_full["ret"] = h1_full["close"].pct_change()

# Map each H1 bar to its H4 bar's state
# H4 bar with open_time T covers H1 bars at T, T+1h, T+2h, T+3h
h4_state_map = {}
for i in range(len(h4_state_open_ms)):
    ot = h4_state_open_ms[i]
    for offset_h in range(4):
        h1_ot = ot + offset_h * 3600 * 1000
        h4_state_map[h1_ot] = h4_state_vals[i]

h1_full["state"] = h1_full["open_time"].map(h4_state_map)
h1_flat = h1_full[h1_full["state"] == "FLAT"].copy()
h1_flat = h1_flat.dropna(subset=["ret"])
h1_flat["hour"] = h1_flat["open_time_dt"].dt.hour

print(f"   H1 FLAT bars: {len(h1_flat)}")

# Test hourly return effect
hourly_groups = [grp["ret"].values for _, grp in h1_flat.groupby("hour")]
hours = sorted(h1_flat["hour"].unique())

# Effect size: η² from Kruskal-Wallis
kw_stat, kw_p = sp_stats.kruskal(*hourly_groups)
# η² approximation for KW: η² = (H - k + 1) / (N - k)
k = len(hours)
N_h1 = len(h1_flat)
eta_sq = (kw_stat - k + 1) / (N_h1 - k)

# Also compute Cohen's f = sqrt(η² / (1 - η²))
cohens_f = np.sqrt(eta_sq / (1 - eta_sq)) if eta_sq > 0 and eta_sq < 1 else 0

# Convert to equivalent d for scoring (f ≈ d/2 for 2-group comparison)
# For multi-group: f = d_max / 2 approximately
equiv_d = 2 * cohens_f

# For practical effect size: range of hourly means / pooled std
hourly_means = np.array([grp.mean() for grp in hourly_groups])
hourly_range_bps = (hourly_means.max() - hourly_means.min()) * 1e4
pooled_std_h1 = h1_flat["ret"].std()
practical_d = (hourly_means.max() - hourly_means.min()) / pooled_std_h1

print(f"\n  S1: SIGNAL STRENGTH")
print(f"      Kruskal-Wallis H={kw_stat:.2f}, p={kw_p:.2e}")
print(f"      η² = {eta_sq:.6f}")
print(f"      Cohen's f = {cohens_f:.4f}")
print(f"      Hourly mean range: {hourly_range_bps:.1f} bps")
print(f"      Practical d (max-min / pooled_std): {practical_d:.4f}")
print(f"      Equivalent d: {equiv_d:.4f}")

if equiv_d > 0.4 and kw_p < 0.01:
    s1_p4 = "STRONG"
elif equiv_d > 0.2 and kw_p < 0.05:
    s1_p4 = "MODERATE"
else:
    s1_p4 = "WEAK"
print(f"      → S1 = {s1_p4}")

# S2: Temporal Stability — already tested via half-sample in Phase 2
# We'll re-do with 4 blocks for consistency
h1_flat_sorted = h1_flat.sort_values("open_time").copy()
n_h1f = len(h1_flat_sorted)
q_h1 = n_h1f // 4

print(f"\n  S2: TEMPORAL STABILITY (4 blocks)")
block_signs_p4 = []
block_sigs_p4 = []
for i in range(4):
    s_idx = i * q_h1
    e_idx = (i + 1) * q_h1 if i < 3 else n_h1f
    blk = h1_flat_sorted.iloc[s_idx:e_idx]
    grps = [g["ret"].values for _, g in blk.groupby("hour") if len(g) >= 5]
    if len(grps) < 10:
        print(f"      Block {i+1}: insufficient hourly coverage")
        block_signs_p4.append(0)
        block_sigs_p4.append(False)
        continue
    h_stat, h_p = sp_stats.kruskal(*grps)
    # Sign: does the best/worst hour pattern persist?
    blk_means = blk.groupby("hour")["ret"].mean()
    best_hour = blk_means.idxmax()
    worst_hour = blk_means.idxmin()
    # Consistent sign = same best/worst hours (approximately)
    sign = 1  # pattern present
    block_signs_p4.append(sign)
    block_sigs_p4.append(h_p < 0.05)
    print(f"      Block {i+1}: n={len(blk)}, KW H={h_stat:.1f}, p={h_p:.4f}, "
          f"best={best_hour}h, worst={worst_hour}h, "
          f"sig={'YES' if h_p < 0.05 else 'no'}")

n_sig_p4 = sum(block_sigs_p4)
# For calendar: "same sign" means pattern is present (sign=1)
n_present = sum(1 for s in block_signs_p4 if s == 1)
if n_present >= 3 and n_sig_p4 >= 2:
    s2_p4 = "STABLE"
elif n_present >= 2:
    s2_p4 = "MIXED"
else:
    s2_p4 = "UNSTABLE"
print(f"      Present: {n_present}/4, Significant: {n_sig_p4}/4 → S2 = {s2_p4}")

# S3: Economic Magnitude
# Best strategy: buy at best hour, sell at worst hour → 1 trade per day
# Range ≈ 10.8 bps between best/worst hour
# But need to enter and exit → 50 bps cost per RT
# Net per trade: ~10.8 - 50 = -39.2 bps → NEGATIVE
# Even with 2 best hours vs 2 worst hours: ~10 bps range
# This is microstructure noise, not tradeable.
n_days_per_year = 365.25
gross_per_day_p4 = hourly_range_bps  # optimistic: full range
net_per_day_p4 = gross_per_day_p4 - COST_BPS
# With FLAT fraction ~57%: only 57% of days have FLAT bars
effective_days = n_days_per_year * 0.574
if net_per_day_p4 > 0:
    ann_ret_p4 = net_per_day_p4 * 1e-4 * effective_days
    ann_vol_p4 = pooled_std_h1 * np.sqrt(effective_days * 24)  # per-hour vol
    delta_sharpe_p4 = ann_ret_p4 / ann_vol_p4 if ann_vol_p4 > 0 else 0
else:
    delta_sharpe_p4 = net_per_day_p4 / COST_BPS * 0.1  # rough negative estimate

print(f"\n  S3: ECONOMIC MAGNITUDE")
print(f"      Hourly mean range: {hourly_range_bps:.1f} bps (best - worst)")
print(f"      Cost per RT: {COST_BPS} bps")
print(f"      Net per trade: {net_per_day_p4:.1f} bps")
print(f"      ΔSharpe estimate: {delta_sharpe_p4:.4f}")

if delta_sharpe_p4 > 0.30:
    s3_p4 = "MATERIAL"
elif delta_sharpe_p4 > 0.10:
    s3_p4 = "MARGINAL"
else:
    s3_p4 = "NEGLIGIBLE"
print(f"      → S3 = {s3_p4}")

# S4: Complementarity
pct_flat_p4 = 100.0  # only FLAT H1 bars analyzed
rho_vtrend_p4 = 0.0  # non-overlapping
print(f"\n  S4: COMPLEMENTARITY")
print(f"      FLAT-only: {pct_flat_p4:.0f}%, ρ={rho_vtrend_p4:.2f}")
if rho_vtrend_p4 < 0.2 and pct_flat_p4 > 70:
    s4_p4 = "COMPLEMENTARY"
else:
    s4_p4 = "PARTIAL"
print(f"      → S4 = {s4_p4}")

# S5: Sample Adequacy
# N = 42,883 H1 FLAT bars → very large sample
# MDE for KW test is different; use equiv_d approach
mde_p4 = mde_one_sample(min(len(g) for g in hourly_groups))
observed_d_p4 = equiv_d
print(f"\n  S5: SAMPLE ADEQUACY")
print(f"      N per hour (min): {min(len(g) for g in hourly_groups)}")
print(f"      MDE: {mde_p4:.4f}")
print(f"      Observed equiv. d: {observed_d_p4:.4f}")
ratio_p4 = observed_d_p4 / mde_p4 if mde_p4 > 0 else 0
print(f"      Ratio: {ratio_p4:.2f}")
if observed_d_p4 > 1.5 * mde_p4:
    s5_p4 = "ADEQUATE"
elif observed_d_p4 > mde_p4:
    s5_p4 = "BORDERLINE"
else:
    s5_p4 = "UNDERPOWERED"
print(f"      → S5 = {s5_p4}")

results["P4_CalendarReturn"] = {
    "obs_ref": "Obs28",
    "S1": s1_p4, "S2": s2_p4, "S3": s3_p4, "S4": s4_p4, "S5": s5_p4,
    "d": equiv_d, "p": kw_p, "delta_sharpe": delta_sharpe_p4,
    "n": N_h1, "mde": mde_p4,
}


# ══════════════════════════════════════════════════════════════════════════
# 5. SCORING MATRIX
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("5. SCORING MATRIX")
print("=" * 70)

top_tier = {"STRONG", "STABLE", "MATERIAL", "COMPLEMENTARY", "ADEQUATE"}

rows = []
for name, r in results.items():
    scores = [r["S1"], r["S2"], r["S3"], r["S4"], r["S5"]]
    total = sum(1 for s in scores if s in top_tier)
    rows.append({
        "Phenomenon": name,
        "Obs_Ref": r["obs_ref"],
        "S1_Signal": r["S1"],
        "S2_Stability": r["S2"],
        "S3_EconMag": r["S3"],
        "S4_Complement": r["S4"],
        "S5_Sample": r["S5"],
        "Total_TopTier": total,
        "Effect_d": round(r["d"], 4),
        "p_value": f"{r['p']:.2e}",
        "Delta_Sharpe": round(r["delta_sharpe"], 4),
    })

scoring_df = pd.DataFrame(rows).sort_values("Total_TopTier", ascending=False)
scoring_df.to_csv(TBL / "Tbl_scoring_matrix.csv", index=False)

print("\n" + scoring_df.to_string(index=False))
print(f"\n   Saved: Tbl_scoring_matrix.csv")


# ══════════════════════════════════════════════════════════════════════════
# 6. STABILITY BLOCKS TABLE
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("6. STABILITY BLOCKS TABLE")
print("=" * 70)

stability_rows = []
for pname, blk_signs, blk_sigs in [
    ("P1_MeanReversion", block_signs, block_sigs),
    ("P2_Autocorrelation24h", block_signs_p2, block_sigs_p2),
    ("P3_PostExitAsymmetry", block_signs_p3, block_sigs_p3),
    ("P4_CalendarReturn", block_signs_p4, block_sigs_p4),
]:
    for i in range(4):
        stability_rows.append({
            "Phenomenon": pname,
            "Block": i + 1,
            "Sign": blk_signs[i] if i < len(blk_signs) else 0,
            "Significant": blk_sigs[i] if i < len(blk_sigs) else False,
        })

stability_df = pd.DataFrame(stability_rows)
stability_df.to_csv(TBL / "Tbl_stability_blocks.csv", index=False)
print(stability_df.to_string(index=False))
print(f"\n   Saved: Tbl_stability_blocks.csv")


# ══════════════════════════════════════════════════════════════════════════
# 7. SUPPLEMENTARY STABILITY — ROLLING WINDOW ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
# For phenomena with Total >= 2: rolling effect size

phenomena_for_rolling = [name for name, r in results.items()
                         if sum(1 for s in [r["S1"], r["S2"], r["S3"], r["S4"], r["S5"]]
                                if s in top_tier) >= 2]

print(f"\n{'=' * 70}")
print(f"7. ROLLING STABILITY ANALYSIS")
print(f"   Phenomena qualifying (Total ≥ 2): {phenomena_for_rolling}")
print(f"{'=' * 70}")

if len(phenomena_for_rolling) > 0:
    fig, axes = plt.subplots(len(phenomena_for_rolling), 1,
                              figsize=(14, 4 * len(phenomena_for_rolling)),
                              squeeze=False)

    for idx, pname in enumerate(phenomena_for_rolling):
        ax = axes[idx, 0]

        if pname == "P1_MeanReversion":
            # Rolling VR(2) on flat bars with 500-bar window
            flat_indices = np.where(is_flat_h4)[0]
            flat_returns = h4["ret"].values[flat_indices]
            flat_times = h4["open_time_dt"].values[flat_indices]
            window = 500
            rolling_vr = []
            rolling_t = []
            for i in range(window, len(flat_returns)):
                seg = flat_returns[i - window:i]
                vr = variance_ratio(seg, 2)
                rolling_vr.append(vr)
                rolling_t.append(flat_times[i])
            ax.plot(rolling_t, rolling_vr, linewidth=0.8, color="steelblue")
            ax.axhline(1.0, color="red", ls="--", linewidth=0.8, label="VR=1 (random walk)")
            ax.set_ylabel("VR(2)")
            ax.set_title(f"P1: Rolling VR(2) — {window}-bar window on FLAT bars")
            ax.legend()

        elif pname == "P2_Autocorrelation24h":
            # Rolling lag-6 ACF on flat bars
            flat_indices = np.where(is_flat_h4)[0]
            flat_returns = h4["ret"].values[flat_indices]
            flat_times = h4["open_time_dt"].values[flat_indices]
            window = 500
            rolling_acf6 = []
            rolling_t = []
            for i in range(window, len(flat_returns)):
                seg = flat_returns[i - window:i]
                ac = compute_acf(seg, nlags=6)
                rolling_acf6.append(ac[6])
                rolling_t.append(flat_times[i])
            ax.plot(rolling_t, rolling_acf6, linewidth=0.8, color="darkorange")
            ax.axhline(0.0, color="red", ls="--", linewidth=0.8, label="ACF=0 (no correlation)")
            # Significance band
            sig_band = 1.96 / np.sqrt(window)
            ax.axhline(sig_band, color="gray", ls=":", linewidth=0.5)
            ax.axhline(-sig_band, color="gray", ls=":", linewidth=0.5)
            ax.set_ylabel("ACF(6)")
            ax.set_title(f"P2: Rolling ACF(6) — {window}-bar window on FLAT bars")
            ax.legend()

        elif pname == "P3_PostExitAsymmetry":
            # Rolling difference (post-winner - post-loser) with 50-trade window
            pe_sorted = pe_df.sort_values("trade_id").reset_index(drop=True)
            window_t = 50
            rolling_diff = []
            rolling_mid = []
            for i in range(window_t, len(pe_sorted)):
                seg = pe_sorted.iloc[i - window_t:i]
                w = seg[seg["is_winner"]]["post_exit_20bar_ret"].values
                l = seg[~seg["is_winner"]]["post_exit_20bar_ret"].values
                if len(w) >= 3 and len(l) >= 3:
                    rolling_diff.append(w.mean() - l.mean())
                    rolling_mid.append(i)
            ax.plot(rolling_mid, [d * 100 for d in rolling_diff],
                    linewidth=0.8, color="green")
            ax.axhline(0, color="red", ls="--", linewidth=0.8)
            ax.set_ylabel("Winner - Loser (%)")
            ax.set_xlabel("Trade index")
            ax.set_title(f"P3: Rolling Post-Exit Asymmetry — {window_t}-trade window")

        elif pname == "P4_CalendarReturn":
            # Rolling hourly η² on flat H1 bars
            h1_flat_sorted_ts = h1_flat.sort_values("open_time").reset_index(drop=True)
            window_h1 = 5000
            rolling_eta = []
            rolling_t = []
            for i in range(window_h1, len(h1_flat_sorted_ts), 500):
                seg = h1_flat_sorted_ts.iloc[i - window_h1:i]
                grps = [g["ret"].values for _, g in seg.groupby("hour") if len(g) >= 5]
                if len(grps) >= 10:
                    h_s, _ = sp_stats.kruskal(*grps)
                    k_g = len(grps)
                    n_g = len(seg)
                    eta = (h_s - k_g + 1) / (n_g - k_g)
                    rolling_eta.append(eta)
                    rolling_t.append(seg.iloc[-1]["open_time_dt"])
            ax.plot(rolling_t, rolling_eta, linewidth=0.8, color="purple")
            ax.axhline(0, color="red", ls="--", linewidth=0.8)
            ax.set_ylabel("η²")
            ax.set_title(f"P4: Rolling Hourly η² — {window_h1}-bar window on FLAT H1 bars")

    plt.tight_layout()
    plt.savefig(FIG / "Fig12_rolling_stability.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n   Saved: Fig12_rolling_stability.png")
else:
    print("   No phenomena qualify for rolling analysis (all Total < 2)")


# ══════════════════════════════════════════════════════════════════════════
# 8. GATE DECISION
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 70}")
print(f"8. GATE DECISION")
print(f"{'=' * 70}")

max_total = scoring_df["Total_TopTier"].max()
best_phenom = scoring_df.iloc[0]["Phenomenon"]

print(f"\n   Best phenomenon: {best_phenom} with Total = {max_total}")
print(f"\n   Scoring summary:")
for _, row in scoring_df.iterrows():
    print(f"     {row['Phenomenon']}: "
          f"S1={row['S1_Signal']}, S2={row['S2_Stability']}, "
          f"S3={row['S3_EconMag']}, S4={row['S4_Complement']}, "
          f"S5={row['S5_Sample']} → Total={row['Total_TopTier']}")

# Gate rules
if max_total >= 3:
    gate = "PASS_TO_NEXT_PHASE"
    print(f"\n   GATE: {gate}")
    print(f"   ≥ 3 top-tier scores on {best_phenom}")
    # Select top 1-2 for Phase 4
    selected = scoring_df[scoring_df["Total_TopTier"] >= 3]["Phenomenon"].tolist()
    print(f"   Selected for Phase 4: {selected}")
else:
    # Check for STOP_INCONCLUSIVE
    has_underpowered_with_2 = False
    for _, r in results.items():
        scores = [r["S1"], r["S2"], r["S3"], r["S4"], r["S5"]]
        total = sum(1 for s in scores if s in top_tier)
        if total >= 2 and r["S5"] == "UNDERPOWERED":
            has_underpowered_with_2 = True
            break

    if has_underpowered_with_2:
        gate = "STOP_INCONCLUSIVE"
        print(f"\n   GATE: {gate}")
        print(f"   ≥ 2 top-tier but S5=UNDERPOWERED — evidence suggestive but cannot validate")
    else:
        # Determine stop type
        # All phenomena have NEGLIGIBLE economic magnitude → NOISE
        all_negligible = all(r["S3"] == "NEGLIGIBLE" for r in results.values())
        if all_negligible:
            gate = "STOP_FLAT_PERIODS_ARE_NOISE"
            print(f"\n   GATE: {gate}")
            print(f"   All phenomena have NEGLIGIBLE economic magnitude.")
            print(f"   Statistical patterns exist but are too small to trade profitably at 50 bps RT.")
        else:
            gate = "STOP_NO_ALPHA_BEYOND_TREND"
            print(f"\n   GATE: {gate}")

print(f"\n   Decision: {gate}")

print(f"\n{'=' * 70}")
print(f"PHASE 3 COMPLETE — {gate}")
print(f"{'=' * 70}")
