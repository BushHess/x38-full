"""Phase 2: Flat-Period Raw EDA.

Characterizes return and price behavior during VTREND FLAT periods.
Descriptive only — no strategy proposals.

Inputs:
- data/bars_btcusdt_2016_now_h1_4h_1d.csv (raw OHLCV)
- tables/state_classification.csv (H4 bar-level FLAT/IN_TRADE from Phase 1)
- tables/trades.csv (217 trades with bar indices)
- tables/Tbl02_flat_durations.csv (218 flat periods)

Deliverables:
- Tbl03: FLAT return distribution statistics
- Tbl04: Variance ratio tests
- Tbl05: Flat-period predictive relationships
- Tbl06: Calendar effect tests
- Fig04–Fig11: See section headers
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


# ══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def compute_acf(x, nlags=50):
    """Standard ACF (biased estimator)."""
    n = len(x)
    xm = x - x.mean()
    c0 = np.dot(xm, xm) / n
    if c0 < 1e-20:
        return np.zeros(nlags + 1)
    acf_out = np.ones(nlags + 1)
    for k in range(1, min(nlags + 1, n)):
        acf_out[k] = np.dot(xm[:n - k], xm[k:]) / (n * c0)
    return acf_out


def gapped_acf(returns, mask, nlags=50):
    """ACF for subset of bars identified by mask, handling temporal gaps.

    For each lag k, uses only pairs (t, t-k) where both t and t-k are
    in mask. Normalizes by overall variance of masked returns.
    """
    mu = returns[mask].mean()
    rc = returns - mu
    var = np.mean(rc[mask] ** 2)
    if var < 1e-20:
        return np.zeros(nlags + 1)
    acf_out = np.ones(nlags + 1)
    n = len(returns)
    for k in range(1, min(nlags + 1, n)):
        valid = mask[k:] & mask[:n - k]
        nv = valid.sum()
        if nv < 10:
            acf_out[k] = np.nan
            continue
        acf_out[k] = np.mean(rc[k:][valid] * rc[:n - k][valid]) / var
    return acf_out


def compute_pacf(acf_vals, nlags=20):
    """PACF via Durbin-Levinson recursion from ACF values."""
    out = np.zeros(nlags + 1)
    out[0] = 1.0
    n = min(nlags, len(acf_vals) - 1)
    if n < 1:
        return out
    a = np.zeros((n + 1, n + 1))
    a[1, 1] = acf_vals[1]
    out[1] = acf_vals[1]
    for k in range(2, n + 1):
        num = acf_vals[k] - sum(a[k - 1, j] * acf_vals[k - j] for j in range(1, k))
        den = 1.0 - sum(a[k - 1, j] * acf_vals[j] for j in range(1, k))
        if abs(den) < 1e-15:
            break
        a[k, k] = num / den
        out[k] = a[k, k]
        for j in range(1, k):
            a[k, j] = a[k - 1, j] - a[k, k] * a[k - 1, k - j]
    return out


def variance_ratio(returns, q):
    """Lo-MacKinlay variance ratio test (homoscedastic & heteroscedastic).

    Returns: (VR, z_homo, p_homo, z_het, p_het)
    """
    T = len(returns)
    if T < 2 * q:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    mu = returns.mean()
    sig1 = np.sum((returns - mu) ** 2) / (T - 1)
    if sig1 < 1e-20:
        return np.nan, np.nan, np.nan, np.nan, np.nan

    # q-period overlapping returns via cumsum
    cs = np.concatenate([[0.0], np.cumsum(returns - mu)])
    rq = cs[q:] - cs[:-q]
    m = len(rq)
    sigq = np.sum(rq ** 2) / (m * q)
    vr = sigq / sig1

    # Homoscedastic z
    theta_homo = 2 * (2 * q - 1) * (q - 1) / (3 * q * T)
    z_homo = (vr - 1) / np.sqrt(theta_homo) if theta_homo > 0 else np.nan

    # Heteroscedastic z
    rsq = (returns - mu) ** 2
    delta = np.zeros(q)
    denom = (np.sum(rsq)) ** 2 / T
    for j in range(1, q):
        num = T * np.sum(rsq[j:] * rsq[:T - j])
        delta[j] = num / denom if denom > 0 else 0
    theta_het = sum((2 * (q - j) / q) ** 2 * delta[j] for j in range(1, q))
    z_het = (vr - 1) / np.sqrt(theta_het) if theta_het > 1e-20 else np.nan

    p_homo = 2 * (1 - sp_stats.norm.cdf(abs(z_homo))) if not np.isnan(z_homo) else np.nan
    p_het = 2 * (1 - sp_stats.norm.cdf(abs(z_het))) if not np.isnan(z_het) else np.nan
    return vr, z_homo, p_homo, z_het, p_het


def hurst_rs(x, min_window=20):
    """Hurst exponent via R/S analysis."""
    n = len(x)
    if n < min_window * 2:
        return np.nan, [], []
    sizes, rs_means = [], []
    for exp in range(int(np.log2(min_window)), int(np.log2(n)) + 1):
        size = 2 ** exp
        if size > n // 2:
            break
        nchunks = n // size
        rs_vals = []
        for i in range(nchunks):
            chunk = x[i * size:(i + 1) * size]
            cm = chunk - chunk.mean()
            cumdev = np.cumsum(cm)
            R = cumdev.max() - cumdev.min()
            S = chunk.std(ddof=0)
            if S > 1e-15:
                rs_vals.append(R / S)
        if len(rs_vals) >= 2:
            sizes.append(size)
            rs_means.append(np.mean(rs_vals))
    if len(sizes) < 2:
        return np.nan, [], []
    log_s = np.log(sizes)
    log_rs = np.log(rs_means)
    H, _ = np.polyfit(log_s, log_rs, 1)
    return H, sizes, rs_means


def max_drawdown_prices(prices):
    """Max drawdown from price series (negative value)."""
    if len(prices) < 2:
        return 0.0
    peak = np.maximum.accumulate(prices)
    dd = (prices - peak) / peak
    return float(dd.min())


def max_runup_prices(prices):
    """Max runup from price series (positive value)."""
    if len(prices) < 2:
        return 0.0
    trough = np.minimum.accumulate(prices)
    mask = trough > 0
    if not mask.any():
        return 0.0
    ru = np.where(mask, (prices - trough) / trough, 0.0)
    return float(ru.max())


def dist_stats(x, label):
    """Compute and print distribution statistics. Returns dict."""
    n = len(x)
    mu = x.mean()
    sd = x.std(ddof=0)
    sk = float(sp_stats.skew(x))
    ku = float(sp_stats.kurtosis(x))  # excess kurtosis
    jb_stat, jb_p = sp_stats.jarque_bera(x)
    med = float(np.median(x))
    q1, q3 = np.percentile(x, [25, 75])
    print(f"\n  {label} (n={n}):")
    print(f"    Mean:     {mu*1e4:.2f} bps")
    print(f"    Median:   {med*1e4:.2f} bps")
    print(f"    Std:      {sd*1e4:.2f} bps")
    print(f"    Skew:     {sk:.4f}")
    print(f"    Kurtosis: {ku:.4f} (excess)")
    print(f"    JB stat:  {jb_stat:.1f}  p={jb_p:.2e}")
    print(f"    [Q1, Q3]: [{q1*1e4:.2f}, {q3*1e4:.2f}] bps")
    print(f"    [Min,Max]: [{x.min()*1e4:.2f}, {x.max()*1e4:.2f}] bps")
    return {"n": n, "mean_bps": round(mu * 1e4, 4), "median_bps": round(med * 1e4, 4),
            "std_bps": round(sd * 1e4, 4), "skew": round(sk, 4), "kurtosis": round(ku, 4),
            "jb_stat": round(float(jb_stat), 2), "jb_p": float(jb_p),
            "q1_bps": round(q1 * 1e4, 4), "q3_bps": round(q3 * 1e4, 4),
            "min_bps": round(x.min() * 1e4, 2), "max_bps": round(x.max() * 1e4, 2)}


# ══════════════════════════════════════════════════════════════════════════
# 0. LOAD DATA
# ══════════════════════════════════════════════════════════════════════════
print("=" * 72)
print("PHASE 2: FLAT-PERIOD RAW EDA")
print("=" * 72)

# Raw OHLCV
raw = pd.read_csv(DATA)
h4_raw = raw[raw["interval"] == "4h"].copy().reset_index(drop=True)
h1_raw = raw[raw["interval"] == "1h"].copy().reset_index(drop=True)
d1_raw = raw[raw["interval"] == "1d"].copy().reset_index(drop=True)
print(f"\nData loaded: H4={len(h4_raw)}, H1={len(h1_raw)}, D1={len(d1_raw)}")

# State classification (Phase 1)
state_df = pd.read_csv(TBL / "state_classification.csv")
assert len(state_df) == len(h4_raw), f"State rows {len(state_df)} != H4 rows {len(h4_raw)}"
is_flat = (state_df["state"].values == "FLAT")
is_trade = ~is_flat
n_h4 = len(h4_raw)

# Trades (Phase 1)
trades_df = pd.read_csv(TBL / "trades.csv")
trades_df = trades_df.dropna(subset=["entry_bar_idx", "exit_bar_idx"]).copy()
trades_df["entry_bar_idx"] = trades_df["entry_bar_idx"].astype(int)
trades_df["exit_bar_idx"] = trades_df["exit_bar_idx"].astype(int)
trades_df = trades_df.sort_values("entry_bar_idx").reset_index(drop=True)
n_trades = len(trades_df)

# Flat periods (Phase 1)
flat_periods_df = pd.read_csv(TBL / "Tbl02_flat_durations.csv")
n_flat_periods = len(flat_periods_df)

# H4 price/volume arrays
h4_close = h4_raw["close"].values.astype(np.float64)
h4_open_time = h4_raw["open_time"].values.astype(np.int64)
h4_volume = h4_raw["volume"].values.astype(np.float64)
h4_high = h4_raw["high"].values.astype(np.float64)
h4_low = h4_raw["low"].values.astype(np.float64)

# H4 log-returns
h4_logret = np.full(n_h4, np.nan)
h4_logret[1:] = np.log(h4_close[1:] / h4_close[:-1])

# Valid mask: exclude bar 0 (no return)
valid = ~np.isnan(h4_logret)

print(f"FLAT bars: {is_flat.sum()} ({is_flat.mean()*100:.1f}%)")
print(f"IN_TRADE bars: {is_trade.sum()} ({is_trade.mean()*100:.1f}%)")
print(f"Trades: {n_trades}, Flat periods: {n_flat_periods}")

flat_ret = h4_logret[is_flat & valid]
trade_ret = h4_logret[is_trade & valid]
full_ret = h4_logret[valid]

# Mask for gapped ACF (exclude bar 0)
flat_mask = is_flat & valid
trade_mask = is_trade & valid

# Annualization: H4 = 6 bars/day, 365 days/year → 2190 bars/year
ANN_FACTOR = np.sqrt(6 * 365)  # ≈ 46.8 for vol


# ══════════════════════════════════════════════════════════════════════════
# 1. FLAT-PERIOD RETURN DISTRIBUTION (H4)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 1: FLAT-Period Return Distribution (H4)")
print(f"{'─'*72}")

s_flat = dist_stats(flat_ret, "FLAT")
s_trade = dist_stats(trade_ret, "IN_TRADE")
s_full = dist_stats(full_ret, "FULL sample")

# Tbl03
tbl03 = pd.DataFrame([s_flat, s_trade, s_full], index=["FLAT", "IN_TRADE", "FULL"])
tbl03.to_csv(TBL / "Tbl03_return_distribution.csv")
print(f"\n  Saved: Tbl03_return_distribution.csv")

# Fig04: Histogram + Q-Q
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 04a: Overlaid histogram
ax = axes[0]
bins = np.linspace(-0.15, 0.15, 120)
ax.hist(flat_ret, bins=bins, alpha=0.5, density=True, color="steelblue",
        label=f"FLAT (n={len(flat_ret)})")
ax.hist(trade_ret, bins=bins, alpha=0.5, density=True, color="green",
        label=f"IN_TRADE (n={len(trade_ret)})")
x_norm = np.linspace(-0.15, 0.15, 200)
ax.plot(x_norm, sp_stats.norm.pdf(x_norm, flat_ret.mean(), flat_ret.std()),
        "k--", alpha=0.5, label="Normal fit (FLAT)")
ax.set_xlabel("H4 Log-Return")
ax.set_ylabel("Density")
ax.set_title("Fig04a: Return Distribution — FLAT vs IN_TRADE")
ax.legend(fontsize=8)
ax.set_xlim(-0.15, 0.15)

# 04b: Zoomed FLAT histogram
ax = axes[1]
bins2 = np.linspace(-0.08, 0.08, 100)
ax.hist(flat_ret, bins=bins2, alpha=0.7, density=True, color="steelblue",
        edgecolor="white", linewidth=0.3)
ax.plot(x_norm, sp_stats.norm.pdf(x_norm, flat_ret.mean(), flat_ret.std()),
        "r-", linewidth=1.5, label="Normal fit")
ax.set_xlabel("H4 Log-Return")
ax.set_ylabel("Density")
ax.set_title(f"Fig04b: FLAT Returns (skew={s_flat['skew']:.3f}, kurt={s_flat['kurtosis']:.1f})")
ax.legend()
ax.set_xlim(-0.08, 0.08)

# 04c: Q-Q plot
ax = axes[2]
(osm, osr), (slope, intercept, r2) = sp_stats.probplot(flat_ret, dist="norm")
ax.scatter(osm, osr, s=2, alpha=0.3, color="steelblue")
ax.plot(osm, slope * osm + intercept, "r-", linewidth=1, label=f"R²={r2:.4f}")
ax.set_xlabel("Theoretical Quantiles (Normal)")
ax.set_ylabel("Sample Quantiles")
ax.set_title("Fig04c: Q-Q Plot — FLAT Returns vs Normal")
ax.legend()

plt.tight_layout()
plt.savefig(FIG / "Fig04_flat_return_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: Fig04_flat_return_distribution.png")


# ══════════════════════════════════════════════════════════════════════════
# 2. AUTOCORRELATION STRUCTURE
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 2: Autocorrelation Structure")
print(f"{'─'*72}")

max_lag = 50
pacf_lag = 20

# Full-sample ACF
acf_full = compute_acf(full_ret, max_lag)
acf_abs_full = compute_acf(np.abs(full_ret), max_lag)

# FLAT-only ACF (gapped — handles non-contiguous bars)
acf_flat = gapped_acf(h4_logret, flat_mask, max_lag)
acf_abs_flat = gapped_acf(np.abs(h4_logret), flat_mask, max_lag)

# PACF
pacf_flat = compute_pacf(acf_flat, pacf_lag)
pacf_full = compute_pacf(acf_full, pacf_lag)

# Significance bounds (approximate 95% CI under white noise)
n_flat_bars = int(flat_mask.sum())
n_full_bars = int(valid.sum())
ci_flat = 1.96 / np.sqrt(n_flat_bars)
ci_full = 1.96 / np.sqrt(n_full_bars)

print(f"\n  ACF significance bounds: FLAT ±{ci_flat:.4f}, FULL ±{ci_full:.4f}")

print(f"\n  Significant FLAT return ACF lags (|acf| > {ci_flat:.4f}):")
sig_lags_ret = []
for k in range(1, max_lag + 1):
    if not np.isnan(acf_flat[k]) and abs(acf_flat[k]) > ci_flat:
        sig_lags_ret.append(k)
        print(f"    Lag {k:2d}: {acf_flat[k]:+.4f}")
if not sig_lags_ret:
    print(f"    None")

print(f"\n  Significant FLAT |return| ACF lags (|acf| > {ci_flat:.4f}):")
sig_lags_abs = []
for k in range(1, max_lag + 1):
    if not np.isnan(acf_abs_flat[k]) and abs(acf_abs_flat[k]) > ci_flat:
        sig_lags_abs.append(k)
        if k <= 15 or len(sig_lags_abs) <= 15:
            print(f"    Lag {k:2d}: {acf_abs_flat[k]:+.4f}")
if len(sig_lags_abs) > 15:
    print(f"    ... and {len(sig_lags_abs) - 15} more lags")
elif not sig_lags_abs:
    print(f"    None")

# ── Variance Ratio Test ──────────────────────────────────────────────
# Approach 1: Full sample (all H4 returns)
print(f"\n  Variance Ratio Tests — FULL sample (n={n_full_bars}):")
vr_full_results = []
for q in [2, 5, 10, 20]:
    vr, zh, ph, zht, pht = variance_ratio(full_ret, q)
    vr_full_results.append({"sample": "FULL", "q": q, "VR": vr,
                             "z_homo": zh, "p_homo": ph,
                             "z_hetero": zht, "p_hetero": pht})
    print(f"    VR({q:2d}) = {vr:.4f}  z_homo={zh:+.3f} p={ph:.4f}  "
          f"z_het={zht:+.3f} p={pht:.4f}")

# Approach 2: Per flat period (correct — no concatenation artifacts)
print(f"\n  Variance Ratio Tests — Per flat period (correct method):")
vr_per_period = {q: [] for q in [2, 5, 10, 20]}
for _, fp in flat_periods_df.iterrows():
    s, e = int(fp["start_bar"]), int(fp["end_bar"])
    dur = e - s + 1
    if dur < 5:
        continue
    # Internal returns only (exclude first bar which crosses boundary)
    internal_rets = h4_logret[s + 1:e + 1]
    internal_rets = internal_rets[~np.isnan(internal_rets)]
    for q in [2, 5, 10, 20]:
        if len(internal_rets) >= 2 * q:
            vr_val, _, _, _, _ = variance_ratio(internal_rets, q)
            if not np.isnan(vr_val):
                vr_per_period[q].append(vr_val)

vr_flat_results = []
for q in [2, 5, 10, 20]:
    vals = vr_per_period[q]
    n_p = len(vals)
    if n_p >= 5:
        mean_vr = np.mean(vals)
        med_vr = np.median(vals)
        tstat, tp = sp_stats.ttest_1samp(vals, 1.0)
        print(f"    VR({q:2d}): n_periods={n_p}, mean={mean_vr:.4f}, "
              f"median={med_vr:.4f}, t={tstat:+.3f}, p={tp:.4f}")
        vr_flat_results.append({"sample": "FLAT_per_period", "q": q,
                                 "VR": mean_vr, "n_periods": n_p,
                                 "t_stat": tstat, "p_value": tp,
                                 "median_VR": med_vr})
    else:
        print(f"    VR({q:2d}): n_periods={n_p} (too few)")
        vr_flat_results.append({"sample": "FLAT_per_period", "q": q,
                                 "VR": np.nan, "n_periods": n_p,
                                 "t_stat": np.nan, "p_value": np.nan,
                                 "median_VR": np.nan})

# Approach 3: Concatenated FLAT returns (pragmatic, noted caveat)
print(f"\n  Variance Ratio Tests — FLAT concatenated (n={len(flat_ret)}, caveat: artificial joins):")
vr_concat_results = []
for q in [2, 5, 10, 20]:
    vr, zh, ph, zht, pht = variance_ratio(flat_ret, q)
    vr_concat_results.append({"sample": "FLAT_concat", "q": q, "VR": vr,
                               "z_homo": zh, "p_homo": ph,
                               "z_hetero": zht, "p_hetero": pht})
    print(f"    VR({q:2d}) = {vr:.4f}  z_homo={zh:+.3f} p={ph:.4f}  "
          f"z_het={zht:+.3f} p={pht:.4f}")

# ── Hurst Exponent ───────────────────────────────────────────────────
H_full, sizes_full, rs_full = hurst_rs(full_ret)
H_flat_concat, sizes_flat_c, rs_flat_c = hurst_rs(flat_ret)

# Also compute on longest flat period
longest_fp = flat_periods_df.loc[flat_periods_df["duration_bars"].idxmax()]
ls, le = int(longest_fp["start_bar"]), int(longest_fp["end_bar"])
longest_rets = h4_logret[ls + 1:le + 1]
longest_rets = longest_rets[~np.isnan(longest_rets)]
H_longest, _, _ = hurst_rs(longest_rets)

print(f"\n  Hurst Exponent (R/S method):")
print(f"    FULL sample:        H = {H_full:.4f}")
print(f"    FLAT concatenated:  H = {H_flat_concat:.4f}")
print(f"    Longest flat period ({int(longest_fp['duration_bars'])} bars): H = {H_longest:.4f}")
print(f"    (H=0.5: random walk, <0.5: mean-reverting, >0.5: persistent)")

# Tbl04: Save all VR results
tbl04_rows = []
for r in vr_full_results:
    tbl04_rows.append(r)
for r in vr_flat_results:
    tbl04_rows.append(r)
for r in vr_concat_results:
    tbl04_rows.append(r)
# Add Hurst
tbl04_rows.append({"sample": "Hurst_FULL", "q": "-", "VR": H_full})
tbl04_rows.append({"sample": "Hurst_FLAT_concat", "q": "-", "VR": H_flat_concat})
tbl04_rows.append({"sample": "Hurst_FLAT_longest", "q": "-", "VR": H_longest})
tbl04 = pd.DataFrame(tbl04_rows)
tbl04.to_csv(TBL / "Tbl04_variance_ratio.csv", index=False)
print(f"\n  Saved: Tbl04_variance_ratio.csv")

# Fig05: ACF Comparison
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

lags = np.arange(1, max_lag + 1)

# 05a: ACF returns
ax = axes[0, 0]
ax.bar(lags - 0.15, acf_flat[1:], width=0.3, alpha=0.7, color="steelblue", label="FLAT")
ax.bar(lags + 0.15, acf_full[1:], width=0.3, alpha=0.7, color="gray", label="FULL")
ax.axhline(ci_flat, color="steelblue", ls="--", alpha=0.5, linewidth=0.7)
ax.axhline(-ci_flat, color="steelblue", ls="--", alpha=0.5, linewidth=0.7)
ax.axhline(0, color="k", linewidth=0.3)
ax.set_xlabel("Lag (H4 bars)")
ax.set_ylabel("ACF")
ax.set_title("Fig05a: ACF of Returns — FLAT vs FULL")
ax.legend(fontsize=8)
ax.set_xlim(0, max_lag + 1)

# 05b: ACF absolute returns
ax = axes[0, 1]
ax.bar(lags - 0.15, acf_abs_flat[1:], width=0.3, alpha=0.7, color="steelblue", label="FLAT")
ax.bar(lags + 0.15, acf_abs_full[1:], width=0.3, alpha=0.7, color="gray", label="FULL")
ax.axhline(ci_flat, color="steelblue", ls="--", alpha=0.5, linewidth=0.7)
ax.axhline(-ci_flat, color="steelblue", ls="--", alpha=0.5, linewidth=0.7)
ax.axhline(0, color="k", linewidth=0.3)
ax.set_xlabel("Lag (H4 bars)")
ax.set_ylabel("ACF")
ax.set_title("Fig05b: ACF of |Returns| (vol clustering) — FLAT vs FULL")
ax.legend(fontsize=8)
ax.set_xlim(0, max_lag + 1)

# 05c: PACF returns
ax = axes[1, 0]
pacf_lags = np.arange(1, pacf_lag + 1)
ax.bar(pacf_lags - 0.15, pacf_flat[1:pacf_lag + 1], width=0.3, alpha=0.7,
       color="steelblue", label="FLAT")
ax.bar(pacf_lags + 0.15, pacf_full[1:pacf_lag + 1], width=0.3, alpha=0.7,
       color="gray", label="FULL")
ax.axhline(ci_flat, color="steelblue", ls="--", alpha=0.5, linewidth=0.7)
ax.axhline(-ci_flat, color="steelblue", ls="--", alpha=0.5, linewidth=0.7)
ax.axhline(0, color="k", linewidth=0.3)
ax.set_xlabel("Lag (H4 bars)")
ax.set_ylabel("PACF")
ax.set_title("Fig05c: PACF of Returns — FLAT vs FULL")
ax.legend(fontsize=8)

# 05d: ACF table (lags 1-10)
ax = axes[1, 1]
ax.axis("off")
cell_text = [["Lag", "FLAT ret", "FULL ret", "FLAT |ret|", "FULL |ret|"]]
for k in range(1, 11):
    cell_text.append([
        str(k),
        f"{acf_flat[k]:.4f}" if not np.isnan(acf_flat[k]) else "NaN",
        f"{acf_full[k]:.4f}",
        f"{acf_abs_flat[k]:.4f}" if not np.isnan(acf_abs_flat[k]) else "NaN",
        f"{acf_abs_full[k]:.4f}",
    ])
table = ax.table(cellText=cell_text, loc="center", cellLoc="center")
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.3)
ax.set_title("Fig05d: ACF Values (lags 1–10)", y=0.95)

plt.tight_layout()
plt.savefig(FIG / "Fig05_acf_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: Fig05_acf_comparison.png")

# Fig06: Variance Ratio + Hurst
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 06a: Variance Ratio
ax = axes[0]
qs = [2, 5, 10, 20]
vr_full_vals = [r["VR"] for r in vr_full_results]
vr_concat_vals = [r["VR"] for r in vr_concat_results]
vr_pp_vals = [r["VR"] for r in vr_flat_results]  # per-period mean
ax.plot(qs, vr_full_vals, "s-", color="gray", label="FULL", markersize=8)
ax.plot(qs, vr_concat_vals, "o--", color="steelblue", label="FLAT (concat)", markersize=8)
vr_pp_valid = [v for v in vr_pp_vals if not np.isnan(v)]
if vr_pp_valid:
    qs_valid = [q for q, v in zip(qs, vr_pp_vals) if not np.isnan(v)]
    ax.plot(qs_valid, vr_pp_valid, "D-", color="darkorange",
            label="FLAT (per-period mean)", markersize=8)
ax.axhline(1.0, color="red", ls=":", alpha=0.5, label="Random Walk (VR=1)")
ax.set_xlabel("Holding Period q (H4 bars)")
ax.set_ylabel("Variance Ratio VR(q)")
ax.set_title("Fig06a: Lo-MacKinlay Variance Ratio")
ax.legend(fontsize=8)
ax.set_xticks(qs)

# 06b: Hurst R/S Plot
ax = axes[1]
if len(sizes_full) >= 2:
    ls_f = np.log(sizes_full)
    lrs_f = np.log(rs_full)
    ax.scatter(ls_f, lrs_f, color="gray", s=60, zorder=5,
               label=f"FULL (H={H_full:.3f})")
    ax.plot(ls_f, H_full * ls_f + np.polyfit(ls_f, lrs_f, 1)[1],
            color="gray", linewidth=1.5)
if len(sizes_flat_c) >= 2:
    ls_fc = np.log(sizes_flat_c)
    lrs_fc = np.log(rs_flat_c)
    ax.scatter(ls_fc, lrs_fc, color="steelblue", s=60, zorder=5,
               label=f"FLAT concat (H={H_flat_concat:.3f})")
    ax.plot(ls_fc, H_flat_concat * ls_fc + np.polyfit(ls_fc, lrs_fc, 1)[1],
            color="steelblue", linewidth=1.5)
# Reference line H=0.5
xl = ax.get_xlim()
x_ref = np.linspace(xl[0], xl[1], 50)
ax.plot(x_ref, 0.5 * x_ref + 0.5, "r:", alpha=0.3, label="H=0.5 (RW)")
ax.set_xlabel("log(window size)")
ax.set_ylabel("log(R/S)")
ax.set_title("Fig06b: R/S Analysis — Hurst Exponent")
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(FIG / "Fig06_variance_ratio_hurst.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: Fig06_variance_ratio_hurst.png")


# ══════════════════════════════════════════════════════════════════════════
# 3. VOLATILITY STRUCTURE
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 3: Volatility Structure")
print(f"{'─'*72}")

# Rolling 20-bar realized vol
win_vol = 20
rvol = pd.Series(h4_logret).rolling(win_vol, min_periods=win_vol).std().values
rvol_valid = ~np.isnan(rvol)

rvol_flat = rvol[is_flat & rvol_valid]
rvol_trade = rvol[is_trade & rvol_valid]
rvol_all = rvol[rvol_valid]

print(f"\n  Realized Vol (20-bar rolling std, annualized x{ANN_FACTOR:.1f}):")
print(f"    FLAT:     mean={rvol_flat.mean()*ANN_FACTOR*100:.1f}%, "
      f"median={np.median(rvol_flat)*ANN_FACTOR*100:.1f}%")
print(f"    IN_TRADE: mean={rvol_trade.mean()*ANN_FACTOR*100:.1f}%, "
      f"median={np.median(rvol_trade)*ANN_FACTOR*100:.1f}%")
print(f"    FULL:     mean={rvol_all.mean()*ANN_FACTOR*100:.1f}%, "
      f"median={np.median(rvol_all)*ANN_FACTOR*100:.1f}%")

# Vol-of-vol
vov = pd.Series(rvol).rolling(win_vol, min_periods=win_vol).std().values
vov_valid = ~np.isnan(vov)
vov_flat = vov[is_flat & vov_valid]
vov_trade = vov[is_trade & vov_valid]
print(f"\n  Vol-of-Vol (rolling std of rvol, annualized):")
print(f"    FLAT:     mean={vov_flat.mean()*ANN_FACTOR*100:.2f}%")
print(f"    IN_TRADE: mean={vov_trade.mean()*ANN_FACTOR*100:.2f}%")

# Vol clustering: ACF of |returns|
print(f"\n  Vol clustering (ACF of |returns|, FLAT-only, key lags):")
for k in [1, 2, 5, 10, 20]:
    v = acf_abs_flat[k]
    sig = " *" if not np.isnan(v) and abs(v) > ci_flat else ""
    print(f"    Lag {k:2d}: {v:.4f}{sig}")

# Volatility by normalized position within flat period
print(f"\n  Volatility by position within flat period (min 5 bars):")
n_bins = 10
pos_bins = np.linspace(0, 1, n_bins + 1)
vol_by_pos = [[] for _ in range(n_bins)]

for _, fp in flat_periods_df.iterrows():
    s, e = int(fp["start_bar"]), int(fp["end_bar"])
    dur = e - s + 1
    if dur < 5:
        continue
    for i in range(s, e + 1):
        if i >= len(rvol) or np.isnan(rvol[i]):
            continue
        rel_pos = (i - s) / max(dur - 1, 1)
        bin_idx = min(int(rel_pos * n_bins), n_bins - 1)
        vol_by_pos[bin_idx].append(rvol[i])

vol_means = [np.mean(v) * ANN_FACTOR * 100 if v else np.nan for v in vol_by_pos]
vol_medians = [np.median(v) * ANN_FACTOR * 100 if v else np.nan for v in vol_by_pos]
vol_counts = [len(v) for v in vol_by_pos]

for i in range(n_bins):
    lo, hi = pos_bins[i], pos_bins[i + 1]
    print(f"    [{lo:.1f}-{hi:.1f}]: mean vol={vol_means[i]:.1f}%, "
          f"median={vol_medians[i]:.1f}%, n={vol_counts[i]}")

# Fig07: Vol structure
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 07a: Vol by position
ax = axes[0]
bin_centers = (pos_bins[:-1] + pos_bins[1:]) / 2
ax.plot(bin_centers, vol_means, "o-", color="steelblue", markersize=8, label="Mean")
ax.plot(bin_centers, vol_medians, "s--", color="orange", markersize=6, label="Median")
ax.set_xlabel("Normalized Position within Flat Period (0=start, 1=end)")
ax.set_ylabel("Annualized Volatility (%)")
ax.set_title("Fig07a: Volatility by Position — Flat Periods (≥5 bars)")
ax.legend()
ax.grid(alpha=0.3)

# 07b: Vol comparison boxplot
ax = axes[1]
data_box = [rvol_flat * ANN_FACTOR * 100, rvol_trade * ANN_FACTOR * 100]
bp = ax.boxplot(data_box, labels=["FLAT", "IN_TRADE"], patch_artist=True,
                showfliers=False, widths=0.5)
bp["boxes"][0].set_facecolor("steelblue")
bp["boxes"][0].set_alpha(0.5)
bp["boxes"][1].set_facecolor("green")
bp["boxes"][1].set_alpha(0.5)
ax.set_ylabel("Annualized Volatility (%)")
ax.set_title("Fig07b: Realized Vol Distribution — FLAT vs IN_TRADE")
ax.grid(alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig(FIG / "Fig07_vol_structure.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  Saved: Fig07_vol_structure.png")


# ══════════════════════════════════════════════════════════════════════════
# 4. FLAT-PERIOD INTERNAL STRUCTURE
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 4: Flat-Period Internal Structure")
print(f"{'─'*72}")

fp_records = []
for idx, fp in flat_periods_df.iterrows():
    s, e = int(fp["start_bar"]), int(fp["end_bar"])
    dur = e - s + 1
    prices = h4_close[s:e + 1]

    if len(prices) < 2:
        total_ret = 0.0
        mdd = 0.0
        mru = 0.0
        vol = 0.0
    else:
        total_ret = np.log(prices[-1] / prices[0])
        mdd = max_drawdown_prices(prices)
        mru = max_runup_prices(prices)
        rets_in = np.diff(np.log(prices))
        vol = float(rets_in.std(ddof=0)) if len(rets_in) > 1 else 0.0

    fp_records.append({
        "flat_idx": idx,
        "start_bar": s,
        "end_bar": e,
        "duration_bars": dur,
        "total_return": total_ret,
        "max_drawdown": mdd,
        "max_runup": mru,
        "volatility": vol,
    })

fp_char = pd.DataFrame(fp_records)

# Link to next trade return
# Flat periods alternate with trades: FLAT[0] → TRADE[0] → FLAT[1] → ...
# So flat[i] is followed by trade[i] for i = 0..n_trades-1
fp_char["next_trade_return"] = np.nan
for i in range(min(len(fp_char), n_trades)):
    fp_char.loc[i, "next_trade_return"] = trades_df.iloc[i]["return_pct"] / 100.0

# Sanity check: verify flat→trade alternation
mismatches = 0
for i in range(min(len(fp_char), n_trades)):
    flat_end = int(fp_char.iloc[i]["end_bar"])
    trade_start = int(trades_df.iloc[i]["entry_bar_idx"])
    gap = trade_start - flat_end
    if gap < 0 or gap > 5:
        mismatches += 1
if mismatches > 0:
    print(f"  WARNING: {mismatches} flat→trade misalignments (>5 bar gap)")
else:
    print(f"  Flat→trade alternation verified (all gaps ≤5 bars)")

print(f"\n  Flat periods: {len(fp_char)}")
print(f"  Duration (bars): mean={fp_char['duration_bars'].mean():.1f}, "
      f"median={fp_char['duration_bars'].median():.0f}")
print(f"  Total return: mean={fp_char['total_return'].mean()*100:.2f}%, "
      f"median={fp_char['total_return'].median()*100:.2f}%")
print(f"  Max drawdown: mean={fp_char['max_drawdown'].mean()*100:.2f}%, "
      f"median={fp_char['max_drawdown'].median()*100:.2f}%")
print(f"  Max runup: mean={fp_char['max_runup'].mean()*100:.2f}%, "
      f"median={fp_char['max_runup'].median()*100:.2f}%")
print(f"  Volatility: mean={fp_char['volatility'].mean()*1e4:.2f} bps/bar, "
      f"median={fp_char['volatility'].median()*1e4:.2f} bps/bar")

# Predictive relationships (Spearman)
print(f"\n  Spearman correlations:")
pairs = [
    ("duration_bars", "total_return", "flat_duration vs flat_total_return"),
    ("duration_bars", "next_trade_return", "flat_duration vs next_trade_return"),
    ("total_return", "next_trade_return", "flat_total_return vs next_trade_return"),
    ("volatility", "next_trade_return", "flat_volatility vs next_trade_return"),
]
tbl05_records = []
for x_col, y_col, label in pairs:
    vld = fp_char[[x_col, y_col]].dropna()
    if len(vld) < 10:
        print(f"    {label}: insufficient data")
        continue
    rho, p = sp_stats.spearmanr(vld[x_col], vld[y_col])
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"    {label}: ρ={rho:+.4f}  p={p:.4f} {sig}")
    tbl05_records.append({"relationship": label, "spearman_rho": round(rho, 4),
                           "p_value": round(p, 6), "n": len(vld),
                           "significant_05": p < 0.05})

tbl05 = pd.DataFrame(tbl05_records)
tbl05.to_csv(TBL / "Tbl05_predictive_relationships.csv", index=False)
fp_char.to_csv(TBL / "flat_period_characteristics.csv", index=False)
print(f"\n  Saved: Tbl05_predictive_relationships.csv")
print(f"  Saved: flat_period_characteristics.csv")

# Fig08: Scatter matrix
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

scatter_cfg = [
    ("duration_bars", "total_return", "Duration (bars)", "Total Return",
     axes[0, 0]),
    ("duration_bars", "next_trade_return", "Duration (bars)",
     "Next Trade Return", axes[0, 1]),
    ("total_return", "next_trade_return", "Flat Total Return",
     "Next Trade Return", axes[1, 0]),
    ("volatility", "next_trade_return", "Flat Volatility (per bar)",
     "Next Trade Return", axes[1, 1]),
]
for x_col, y_col, xlabel, ylabel, ax in scatter_cfg:
    vld = fp_char[[x_col, y_col]].dropna()
    ax.scatter(vld[x_col], vld[y_col], s=15, alpha=0.5, color="steelblue")
    rho, p = sp_stats.spearmanr(vld[x_col], vld[y_col])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"ρ={rho:+.3f}, p={p:.3f}")
    ax.axhline(0, color="gray", ls=":", alpha=0.3)
    ax.grid(alpha=0.2)

fig.suptitle("Fig08: Flat-Period Characteristics vs Next Trade Return",
             fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig(FIG / "Fig08_scatter_matrix.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: Fig08_scatter_matrix.png")


# ══════════════════════════════════════════════════════════════════════════
# 5. TRANSITION DYNAMICS
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 5: Transition Dynamics")
print(f"{'─'*72}")

window = 20

# Pre-entry profiles (20 bars before trade entry)
pre_ret_all, pre_ret_win, pre_ret_lose = [], [], []
pre_vol_all, pre_volume_all = [], []

for _, tr in trades_df.iterrows():
    eidx = int(tr["entry_bar_idx"])
    start = eidx - window
    if start < 0:
        continue
    rets = h4_logret[start:eidx]
    if len(rets) != window or np.any(np.isnan(rets)):
        continue
    cum = np.cumsum(rets)
    pre_ret_all.append(cum)
    pre_vol_all.append(np.abs(rets))
    pre_volume_all.append(h4_volume[start:eidx])
    if tr["return_pct"] > 0:
        pre_ret_win.append(cum)
    else:
        pre_ret_lose.append(cum)

# Post-exit profiles (20 bars after trade exit)
post_ret_all, post_ret_win, post_ret_lose = [], [], []
post_vol_all, post_volume_all = [], []

for _, tr in trades_df.iterrows():
    xidx = int(tr["exit_bar_idx"])
    end = xidx + window
    if end >= n_h4:
        continue
    rets = h4_logret[xidx:xidx + window]
    if len(rets) != window or np.any(np.isnan(rets)):
        continue
    cum = np.cumsum(rets)
    post_ret_all.append(cum)
    post_vol_all.append(np.abs(rets))
    post_volume_all.append(h4_volume[xidx:xidx + window])
    if tr["return_pct"] > 0:
        post_ret_win.append(cum)
    else:
        post_ret_lose.append(cum)

print(f"\n  Pre-entry profiles: {len(pre_ret_all)} "
      f"(win={len(pre_ret_win)}, lose={len(pre_ret_lose)})")
print(f"  Post-exit profiles: {len(post_ret_all)} "
      f"(win={len(post_ret_win)}, lose={len(post_ret_lose)})")

# Print transition summaries
if pre_ret_all:
    avg_pre = np.mean(pre_ret_all, axis=0)
    print(f"\n  Pre-entry cumulative return (bar -20 to bar -1):")
    print(f"    All:     {avg_pre[-1]*100:+.3f}%")
    if pre_ret_win:
        print(f"    Winners: {np.mean(pre_ret_win, axis=0)[-1]*100:+.3f}%")
    if pre_ret_lose:
        print(f"    Losers:  {np.mean(pre_ret_lose, axis=0)[-1]*100:+.3f}%")

if post_ret_all:
    avg_post = np.mean(post_ret_all, axis=0)
    print(f"\n  Post-exit cumulative return (bar 0 to bar +19):")
    print(f"    All:          {avg_post[-1]*100:+.3f}%")
    if post_ret_win:
        print(f"    After winners: {np.mean(post_ret_win, axis=0)[-1]*100:+.3f}%")
    if post_ret_lose:
        print(f"    After losers:  {np.mean(post_ret_lose, axis=0)[-1]*100:+.3f}%")

# Fig09: Transition dynamics (2×3 grid)
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
x_pre = np.arange(-window, 0)
x_post = np.arange(0, window)

# 09a: Pre-entry cumulative return
ax = axes[0, 0]
if pre_ret_all:
    avg = np.mean(pre_ret_all, axis=0)
    se = np.std(pre_ret_all, axis=0) / np.sqrt(len(pre_ret_all))
    ax.plot(x_pre, avg * 100, "b-", linewidth=2, label="All trades")
    ax.fill_between(x_pre, (avg - 1.96 * se) * 100, (avg + 1.96 * se) * 100,
                    alpha=0.2, color="blue")
if pre_ret_win:
    ax.plot(x_pre, np.mean(pre_ret_win, axis=0) * 100, "g--", linewidth=1.5,
            label="Before winners")
if pre_ret_lose:
    ax.plot(x_pre, np.mean(pre_ret_lose, axis=0) * 100, "r--", linewidth=1.5,
            label="Before losers")
ax.axhline(0, color="gray", ls=":", alpha=0.3)
ax.axvline(-0.5, color="k", ls="-", alpha=0.5)
ax.set_xlabel("Bars relative to entry")
ax.set_ylabel("Cumulative Return (%)")
ax.set_title("Fig09a: Pre-Entry Return Profile")
ax.legend(fontsize=8)
ax.grid(alpha=0.2)

# 09b: Post-exit cumulative return
ax = axes[0, 1]
if post_ret_all:
    avg = np.mean(post_ret_all, axis=0)
    se = np.std(post_ret_all, axis=0) / np.sqrt(len(post_ret_all))
    ax.plot(x_post, avg * 100, "b-", linewidth=2, label="All trades")
    ax.fill_between(x_post, (avg - 1.96 * se) * 100, (avg + 1.96 * se) * 100,
                    alpha=0.2, color="blue")
if post_ret_win:
    ax.plot(x_post, np.mean(post_ret_win, axis=0) * 100, "g--", linewidth=1.5,
            label="After winners")
if post_ret_lose:
    ax.plot(x_post, np.mean(post_ret_lose, axis=0) * 100, "r--", linewidth=1.5,
            label="After losers")
ax.axhline(0, color="gray", ls=":", alpha=0.3)
ax.axvline(-0.5, color="k", ls="-", alpha=0.5)
ax.set_xlabel("Bars relative to exit")
ax.set_ylabel("Cumulative Return (%)")
ax.set_title("Fig09b: Post-Exit Return Profile")
ax.legend(fontsize=8)
ax.grid(alpha=0.2)

# 09c: Pre-entry volatility
ax = axes[0, 2]
if pre_vol_all:
    avg_vol = np.mean(pre_vol_all, axis=0) * ANN_FACTOR * 100
    ax.plot(x_pre, avg_vol, "b-", linewidth=2)
ax.axvline(-0.5, color="k", ls="-", alpha=0.5)
ax.set_xlabel("Bars relative to entry")
ax.set_ylabel("Avg |Return| (ann. %)")
ax.set_title("Fig09c: Pre-Entry Volatility")
ax.grid(alpha=0.2)

# 09d: Post-exit volatility
ax = axes[1, 0]
if post_vol_all:
    avg_vol = np.mean(post_vol_all, axis=0) * ANN_FACTOR * 100
    ax.plot(x_post, avg_vol, "b-", linewidth=2)
ax.axvline(-0.5, color="k", ls="-", alpha=0.5)
ax.set_xlabel("Bars relative to exit")
ax.set_ylabel("Avg |Return| (ann. %)")
ax.set_title("Fig09d: Post-Exit Volatility")
ax.grid(alpha=0.2)

# 09e: Pre-entry volume (normalized)
ax = axes[1, 1]
if pre_volume_all:
    avg_v = np.mean(pre_volume_all, axis=0)
    avg_v_norm = avg_v / avg_v.mean() if avg_v.mean() > 0 else avg_v
    ax.plot(x_pre, avg_v_norm, "b-", linewidth=2)
ax.axhline(1.0, color="gray", ls=":", alpha=0.3)
ax.axvline(-0.5, color="k", ls="-", alpha=0.5)
ax.set_xlabel("Bars relative to entry")
ax.set_ylabel("Normalized Volume")
ax.set_title("Fig09e: Pre-Entry Volume Profile")
ax.grid(alpha=0.2)

# 09f: Post-exit volume (normalized)
ax = axes[1, 2]
if post_volume_all:
    avg_v = np.mean(post_volume_all, axis=0)
    avg_v_norm = avg_v / avg_v.mean() if avg_v.mean() > 0 else avg_v
    ax.plot(x_post, avg_v_norm, "b-", linewidth=2)
ax.axhline(1.0, color="gray", ls=":", alpha=0.3)
ax.axvline(-0.5, color="k", ls="-", alpha=0.5)
ax.set_xlabel("Bars relative to exit")
ax.set_ylabel("Normalized Volume")
ax.set_title("Fig09f: Post-Exit Volume Profile")
ax.grid(alpha=0.2)

plt.suptitle("Fig09: Transition Dynamics — FLAT ↔ Trade Boundaries",
             fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig(FIG / "Fig09_transition_dynamics.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  Saved: Fig09_transition_dynamics.png")


# ══════════════════════════════════════════════════════════════════════════
# 6. CROSS-TIMEFRAME CHECK
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 6: Cross-Timeframe Check")
print(f"{'─'*72}")

# Map H4 states to H1 bars
H4_INTERVAL_MS = 4 * 3600 * 1000
h1_open_ms = h1_raw["open_time"].values.astype(np.int64)
h1_close_vals = h1_raw["close"].values.astype(np.float64)

# Create H4 state lookup: open_time -> state
h4_state_map = dict(zip(state_df["open_time"].astype(int), state_df["state"]))

# Map each H1 bar to parent H4 bar
h1_h4_parent = h1_open_ms - (h1_open_ms % H4_INTERVAL_MS)
h1_state = np.array([h4_state_map.get(int(t), "UNKNOWN") for t in h1_h4_parent])
h1_is_flat = (h1_state == "FLAT")
h1_unknown = (h1_state == "UNKNOWN").sum()

n_h1 = len(h1_raw)
h1_logret = np.full(n_h1, np.nan)
h1_logret[1:] = np.log(h1_close_vals[1:] / h1_close_vals[:-1])
h1_valid = ~np.isnan(h1_logret)
h1_flat_mask = h1_is_flat & h1_valid

h1_flat_ret = h1_logret[h1_flat_mask]
h1_full_ret = h1_logret[h1_valid]

print(f"\n  H1 bars: {n_h1} total, {h1_is_flat.sum()} FLAT "
      f"({h1_is_flat.mean()*100:.1f}%), {h1_unknown} UNKNOWN")

# H1 FLAT return distribution
s_h1_flat = dist_stats(h1_flat_ret, "H1 FLAT")
s_h1_full = dist_stats(h1_full_ret, "H1 FULL")

# H1 ACF
acf_h1_flat = gapped_acf(h1_logret, h1_flat_mask, max_lag)
acf_h1_full = compute_acf(h1_full_ret, max_lag)
acf_h1_abs_flat = gapped_acf(np.abs(h1_logret), h1_flat_mask, max_lag)
acf_h1_abs_full = compute_acf(np.abs(h1_full_ret), max_lag)

ci_h1 = 1.96 / np.sqrt(h1_flat_mask.sum())

print(f"\n  H1 ACF significance bound: ±{ci_h1:.4f}")
print(f"  Significant H1 FLAT return ACF lags:")
h1_sig_ret = []
for k in range(1, max_lag + 1):
    if not np.isnan(acf_h1_flat[k]) and abs(acf_h1_flat[k]) > ci_h1:
        h1_sig_ret.append(k)
        if len(h1_sig_ret) <= 10:
            print(f"    Lag {k}: {acf_h1_flat[k]:+.4f}")
if len(h1_sig_ret) > 10:
    print(f"    ... and {len(h1_sig_ret) - 10} more")
elif not h1_sig_ret:
    print(f"    None")

print(f"\n  Significant H1 FLAT |return| ACF lags:")
h1_sig_abs = []
for k in range(1, max_lag + 1):
    if not np.isnan(acf_h1_abs_flat[k]) and abs(acf_h1_abs_flat[k]) > ci_h1:
        h1_sig_abs.append(k)
        if len(h1_sig_abs) <= 10:
            print(f"    Lag {k}: {acf_h1_abs_flat[k]:+.4f}")
if len(h1_sig_abs) > 10:
    print(f"    ... and {len(h1_sig_abs) - 10} more")
elif not h1_sig_abs:
    print(f"    None")

# H1 VR test
print(f"\n  H1 Variance Ratio (FLAT concatenated):")
for q in [2, 5, 10, 20]:
    vr, zh, ph, zht, pht = variance_ratio(h1_flat_ret, q)
    print(f"    VR({q:2d}) = {vr:.4f}  z_het={zht:+.3f} p={pht:.4f}")

# H1 Hurst
H_h1_flat, _, _ = hurst_rs(h1_flat_ret)
H_h1_full, _, _ = hurst_rs(h1_full_ret)
print(f"\n  H1 Hurst: FLAT={H_h1_flat:.4f}, FULL={H_h1_full:.4f}")

# D1 check
D1_INTERVAL_MS = 24 * 3600 * 1000
d1_open_ms = d1_raw["open_time"].values.astype(np.int64)
d1_close_vals = d1_raw["close"].values.astype(np.float64)

d1_flat_frac = []
for d_ot in d1_open_ms:
    mask_day = (h4_open_time >= d_ot) & (h4_open_time < d_ot + D1_INTERVAL_MS)
    if mask_day.sum() == 0:
        d1_flat_frac.append(np.nan)
    else:
        d1_flat_frac.append(is_flat[mask_day].mean())
d1_flat_frac = np.array(d1_flat_frac)

d1_logret = np.full(len(d1_raw), np.nan)
d1_logret[1:] = np.log(d1_close_vals[1:] / d1_close_vals[:-1])

d1_mostly_flat = d1_flat_frac >= 0.75
d1_flat_valid = d1_mostly_flat & ~np.isnan(d1_flat_frac) & ~np.isnan(d1_logret)
d1_flat_ret = d1_logret[d1_flat_valid]
d1_full_ret = d1_logret[~np.isnan(d1_logret)]

print(f"\n  D1 check:")
print(f"    Days with ≥75% FLAT H4: {d1_flat_valid.sum()} / {len(d1_raw)}")
if len(d1_flat_ret) > 10:
    print(f"    D1 FLAT: mean={d1_flat_ret.mean()*1e4:.2f} bps, "
          f"std={d1_flat_ret.std()*1e4:.2f} bps")
    print(f"    D1 FULL: mean={d1_full_ret.mean()*1e4:.2f} bps, "
          f"std={d1_full_ret.std()*1e4:.2f} bps")
    # D1 VR
    for q in [2, 5]:
        vr, _, _, zht, pht = variance_ratio(d1_flat_ret, q)
        print(f"    D1 FLAT VR({q}): {vr:.4f}  z_het={zht:+.3f} p={pht:.4f}")
    H_d1, _, _ = hurst_rs(d1_flat_ret)
    print(f"    D1 FLAT Hurst: {H_d1:.4f}")

# Cross-timeframe comparison summary
print(f"\n  Cross-timeframe summary:")
print(f"    {'Metric':<25} {'H1':>10} {'H4':>10} {'D1':>10}")
print(f"    {'—'*55}")
print(f"    {'Mean return (bps)':<25} {h1_flat_ret.mean()*1e4:>10.2f} "
      f"{flat_ret.mean()*1e4:>10.2f} "
      f"{d1_flat_ret.mean()*1e4 if len(d1_flat_ret)>0 else float('nan'):>10.2f}")
print(f"    {'Std (bps)':<25} {h1_flat_ret.std()*1e4:>10.2f} "
      f"{flat_ret.std()*1e4:>10.2f} "
      f"{d1_flat_ret.std()*1e4 if len(d1_flat_ret)>0 else float('nan'):>10.2f}")
print(f"    {'Skew':<25} {sp_stats.skew(h1_flat_ret):>10.3f} "
      f"{sp_stats.skew(flat_ret):>10.3f} "
      f"{sp_stats.skew(d1_flat_ret) if len(d1_flat_ret)>10 else float('nan'):>10.3f}")
print(f"    {'Kurtosis (excess)':<25} {sp_stats.kurtosis(h1_flat_ret):>10.2f} "
      f"{sp_stats.kurtosis(flat_ret):>10.2f} "
      f"{sp_stats.kurtosis(d1_flat_ret) if len(d1_flat_ret)>10 else float('nan'):>10.2f}")
print(f"    {'Hurst':<25} {H_h1_flat:>10.4f} {H_flat_concat:>10.4f} "
      f"{H_d1 if len(d1_flat_ret)>40 else float('nan'):>10.4f}")

# Fig11: H1 vs H4 ACF comparison
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax = axes[0]
lags = np.arange(1, max_lag + 1)
ax.plot(lags, acf_h1_flat[1:], "o-", markersize=3, color="purple",
        label=f"H1 FLAT (n={h1_flat_mask.sum()})")
ax.plot(lags, acf_flat[1:], "s-", markersize=3, color="steelblue",
        label=f"H4 FLAT (n={n_flat_bars})")
ax.axhline(ci_h1, color="purple", ls="--", alpha=0.4, linewidth=0.7)
ax.axhline(-ci_h1, color="purple", ls="--", alpha=0.4, linewidth=0.7)
ax.axhline(ci_flat, color="steelblue", ls="--", alpha=0.4, linewidth=0.7)
ax.axhline(-ci_flat, color="steelblue", ls="--", alpha=0.4, linewidth=0.7)
ax.axhline(0, color="k", linewidth=0.3)
ax.set_xlabel("Lag")
ax.set_ylabel("ACF")
ax.set_title("Fig11a: ACF of Returns — H1 vs H4 (FLAT only)")
ax.legend(fontsize=8)

ax = axes[1]
ax.plot(lags, acf_h1_abs_flat[1:], "o-", markersize=3, color="purple",
        label="H1 FLAT |ret|")
ax.plot(lags, acf_abs_flat[1:], "s-", markersize=3, color="steelblue",
        label="H4 FLAT |ret|")
ax.axhline(ci_h1, color="purple", ls="--", alpha=0.4, linewidth=0.7)
ax.axhline(-ci_h1, color="purple", ls="--", alpha=0.4, linewidth=0.7)
ax.axhline(0, color="k", linewidth=0.3)
ax.set_xlabel("Lag")
ax.set_ylabel("ACF")
ax.set_title("Fig11b: ACF of |Returns| — H1 vs H4 (FLAT only)")
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(FIG / "Fig11_cross_timeframe_acf.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"\n  Saved: Fig11_cross_timeframe_acf.png")


# ══════════════════════════════════════════════════════════════════════════
# 7. CALENDAR EFFECTS (H1 data, FLAT periods only)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'─'*72}")
print("SECTION 7: Calendar Effects (H1 data, FLAT periods only)")
print(f"{'─'*72}")

h1_dt = pd.to_datetime(h1_open_ms, unit="ms", utc=True)
h1_hour = h1_dt.hour.values
h1_dow = h1_dt.dayofweek.values  # 0=Monday, 6=Sunday

cal_df = pd.DataFrame({
    "return": h1_logret,
    "abs_return": np.abs(h1_logret),
    "hour": h1_hour,
    "dow": h1_dow,
    "is_flat": h1_is_flat,
    "valid": h1_valid,
})
cal_flat = cal_df[cal_df["is_flat"] & cal_df["valid"]].copy()

print(f"\n  FLAT H1 bars for calendar analysis: {len(cal_flat)}")

# By hour
hour_stats = cal_flat.groupby("hour").agg(
    mean_ret=("return", "mean"),
    mean_abs=("abs_return", "mean"),
    n=("return", "count"),
).reset_index()
print(f"\n  Mean return by hour (bps):")
for _, row in hour_stats.iterrows():
    print(f"    {int(row['hour']):02d}:00  mean={row['mean_ret']*1e4:+.2f} bps  "
          f"|ret|={row['mean_abs']*1e4:.2f} bps  n={int(row['n'])}")

# By day of week
dow_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu",
             4: "Fri", 5: "Sat", 6: "Sun"}
dow_stats = cal_flat.groupby("dow").agg(
    mean_ret=("return", "mean"),
    mean_abs=("abs_return", "mean"),
    n=("return", "count"),
).reset_index()
print(f"\n  Mean return by day of week (bps):")
for _, row in dow_stats.iterrows():
    d = int(row["dow"])
    print(f"    {dow_names[d]}  mean={row['mean_ret']*1e4:+.2f} bps  "
          f"|ret|={row['mean_abs']*1e4:.2f} bps  n={int(row['n'])}")

# Kruskal-Wallis tests
print(f"\n  Kruskal-Wallis tests:")
tests = {}

# Return by hour
hour_groups = [cal_flat[cal_flat["hour"] == h]["return"].values for h in range(24)]
hour_groups = [g for g in hour_groups if len(g) > 0]
kw_h_ret, p_h_ret = sp_stats.kruskal(*hour_groups)
tests["ret_by_hour"] = (kw_h_ret, p_h_ret)

# |Return| by hour
hour_abs_groups = [cal_flat[cal_flat["hour"] == h]["abs_return"].values for h in range(24)]
hour_abs_groups = [g for g in hour_abs_groups if len(g) > 0]
kw_h_abs, p_h_abs = sp_stats.kruskal(*hour_abs_groups)
tests["absret_by_hour"] = (kw_h_abs, p_h_abs)

# Return by DoW
dow_groups = [cal_flat[cal_flat["dow"] == d]["return"].values for d in range(7)]
dow_groups = [g for g in dow_groups if len(g) > 0]
kw_d_ret, p_d_ret = sp_stats.kruskal(*dow_groups)
tests["ret_by_dow"] = (kw_d_ret, p_d_ret)

# |Return| by DoW
dow_abs_groups = [cal_flat[cal_flat["dow"] == d]["abs_return"].values for d in range(7)]
dow_abs_groups = [g for g in dow_abs_groups if len(g) > 0]
kw_d_abs, p_d_abs = sp_stats.kruskal(*dow_abs_groups)
tests["absret_by_dow"] = (kw_d_abs, p_d_abs)

print(f"    Return by hour:   KW={kw_h_ret:.2f}  p={p_h_ret:.4f}  "
      f"{'*' if p_h_ret < 0.05 else ''}")
print(f"    |Return| by hour: KW={kw_h_abs:.2f}  p={p_h_abs:.4f}  "
      f"{'*' if p_h_abs < 0.05 else ''}")
print(f"    Return by DoW:    KW={kw_d_ret:.2f}  p={p_d_ret:.4f}  "
      f"{'*' if p_d_ret < 0.05 else ''}")
print(f"    |Return| by DoW:  KW={kw_d_abs:.2f}  p={p_d_abs:.4f}  "
      f"{'*' if p_d_abs < 0.05 else ''}")

# Half-sample stability check for significant effects
sig_effects = []
if p_h_ret < 0.05:
    sig_effects.append(("hour", "return", "Return by hour"))
if p_h_abs < 0.05:
    sig_effects.append(("hour", "abs_return", "|Return| by hour"))
if p_d_ret < 0.05:
    sig_effects.append(("dow", "return", "Return by DoW"))
if p_d_abs < 0.05:
    sig_effects.append(("dow", "abs_return", "|Return| by DoW"))

stability_results = []
if sig_effects:
    print(f"\n  Half-sample stability check for {len(sig_effects)} significant effect(s):")
    mid = len(cal_flat) // 2
    half1 = cal_flat.iloc[:mid]
    half2 = cal_flat.iloc[mid:]
    for groupcol, retcol, label in sig_effects:
        vals = sorted(cal_flat[groupcol].unique())
        g1 = [half1[half1[groupcol] == v][retcol].values for v in vals]
        g1 = [g for g in g1 if len(g) > 0]
        g2 = [half2[half2[groupcol] == v][retcol].values for v in vals]
        g2 = [g for g in g2 if len(g) > 0]
        kw1, p1 = sp_stats.kruskal(*g1) if len(g1) > 1 else (np.nan, np.nan)
        kw2, p2 = sp_stats.kruskal(*g2) if len(g2) > 1 else (np.nan, np.nan)
        stable = "STABLE" if (p1 < 0.05 and p2 < 0.05) else "UNSTABLE"
        print(f"    {label}: half1 p={p1:.4f}, half2 p={p2:.4f} → {stable}")
        stability_results.append({
            "effect": label, "half1_p": p1, "half2_p": p2, "stable": stable
        })
else:
    print(f"\n  No significant effects — stability check not needed.")

# Tbl06
tbl06 = pd.DataFrame({
    "test": ["Return by hour", "|Return| by hour", "Return by DoW", "|Return| by DoW"],
    "KW_statistic": [kw_h_ret, kw_h_abs, kw_d_ret, kw_d_abs],
    "p_value": [p_h_ret, p_h_abs, p_d_ret, p_d_abs],
    "significant_05": [p_h_ret < 0.05, p_h_abs < 0.05,
                        p_d_ret < 0.05, p_d_abs < 0.05],
})
if stability_results:
    stab_df = pd.DataFrame(stability_results)
    tbl06 = tbl06.merge(stab_df.rename(columns={"effect": "test"}),
                         on="test", how="left")
tbl06.to_csv(TBL / "Tbl06_calendar_effects.csv", index=False)
print(f"\n  Saved: Tbl06_calendar_effects.csv")

# Fig10: Calendar effects heatmap
fig, axes = plt.subplots(1, 2, figsize=(18, 6))
dow_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# 10a: Return heatmap (DoW × hour)
heatmap_ret = np.full((7, 24), np.nan)
for (d, h), val in cal_flat.groupby(["dow", "hour"])["return"].mean().items():
    heatmap_ret[int(d), int(h)] = val * 1e4

ax = axes[0]
vmax = np.nanstd(heatmap_ret) * 3
im = ax.imshow(heatmap_ret, aspect="auto", cmap="RdBu_r",
               vmin=-vmax, vmax=vmax, interpolation="nearest")
ax.set_xlabel("Hour (UTC)")
ax.set_ylabel("Day of Week")
ax.set_yticks(range(7))
ax.set_yticklabels(dow_labels)
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)])
ax.set_title("Fig10a: Mean Return (bps) — FLAT H1 Bars")
plt.colorbar(im, ax=ax, label="bps", shrink=0.8)

# 10b: |Return| heatmap (DoW × hour)
heatmap_abs = np.full((7, 24), np.nan)
for (d, h), val in cal_flat.groupby(["dow", "hour"])["abs_return"].mean().items():
    heatmap_abs[int(d), int(h)] = val * 1e4

ax = axes[1]
im = ax.imshow(heatmap_abs, aspect="auto", cmap="YlOrRd", interpolation="nearest")
ax.set_xlabel("Hour (UTC)")
ax.set_ylabel("Day of Week")
ax.set_yticks(range(7))
ax.set_yticklabels(dow_labels)
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)])
ax.set_title("Fig10b: Mean |Return| (bps) — FLAT H1 Bars")
plt.colorbar(im, ax=ax, label="bps", shrink=0.8)

plt.suptitle("Fig10: Calendar Effects — FLAT H1 Bars", fontsize=14, y=1.02)
plt.tight_layout()
plt.savefig(FIG / "Fig10_calendar_effects.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: Fig10_calendar_effects.png")


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 72}")
print("PHASE 2 COMPLETE — ALL SECTIONS DONE")
print(f"{'=' * 72}")

print(f"\nFigures: Fig04–Fig11 (8 figures)")
print(f"Tables:  Tbl03–Tbl06 + flat_period_characteristics.csv")
print(f"\nKey numbers for report:")
print(f"  FLAT mean return:  {flat_ret.mean()*1e4:.2f} bps (H4)")
print(f"  FLAT std:          {flat_ret.std()*1e4:.2f} bps")
print(f"  FLAT skew:         {sp_stats.skew(flat_ret):.4f}")
print(f"  FLAT kurtosis:     {sp_stats.kurtosis(flat_ret):.4f}")
print(f"  IN_TRADE mean:     {trade_ret.mean()*1e4:.2f} bps")
print(f"  Hurst (FLAT):      {H_flat_concat:.4f}")
print(f"  Hurst (FULL):      {H_full:.4f}")
print(f"  VR(2) per-period:  {np.mean(vr_per_period[2]):.4f}" if vr_per_period[2] else "  VR(2): N/A")
print(f"  ACF ret sig lags:  {sig_lags_ret}")
print(f"  ACF |ret| sig:     {len(sig_lags_abs)} lags")
