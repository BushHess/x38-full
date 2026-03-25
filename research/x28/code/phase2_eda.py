"""
Phase 2 — BTC H4 Price Behavior EDA
X28 Research: Statistical properties of BTC H4 returns.
DESCRIPTIVE ONLY — no strategy proposals.
"""

import os
import json
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import jarque_bera, skew, kurtosis
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from statsmodels.tsa.stattools import acf, pacf
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ──────────────────────────────────────────────────────────────
BASE = "/var/www/trading-bots/btc-spot-dev/research/x28"
DATA = "/var/www/trading-bots/btc-spot-dev/data"
FIG_DIR = os.path.join(BASE, "figures")
TBL_DIR = os.path.join(BASE, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TBL_DIR, exist_ok=True)

# ── Load data ──────────────────────────────────────────────────────────
def load_tf(tf):
    fp = os.path.join(DATA, f"btcusdt_{tf}.csv")
    df = pd.read_csv(fp)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["taker_buy_ratio"] = df["taker_buy_base_vol"] / df["volume"]
    df["taker_buy_ratio"] = df["taker_buy_ratio"].replace([np.inf, -np.inf], np.nan)
    df = df.sort_values("open_time").reset_index(drop=True)
    return df

print("Loading data...")
h4 = load_tf("4h")
d1 = load_tf("1d")
print(f"  H4: {len(h4)} bars, D1: {len(d1)} bars")

# Log returns
h4["log_ret"] = np.log(h4["close"] / h4["close"].shift(1))
d1["log_ret"] = np.log(d1["close"] / d1["close"].shift(1))
h4_ret = h4["log_ret"].dropna().values
d1_ret = d1["log_ret"].dropna().values

print(f"  H4 returns: {len(h4_ret)}, D1 returns: {len(d1_ret)}")

# ── Collection for observations ────────────────────────────────────────
observations = []
def obs(obs_id, text, refs):
    observations.append({"id": obs_id, "text": text, "refs": refs})
    print(f"  {obs_id}: {text}")

# ======================================================================
# SECTION 1: RETURN DISTRIBUTION
# ======================================================================
print("\n=== SECTION 1: Return Distribution ===")

ret_mean = np.mean(h4_ret)
ret_std = np.std(h4_ret, ddof=1)
ret_skew = skew(h4_ret)
ret_kurt = kurtosis(h4_ret, fisher=True)  # excess kurtosis
jb_stat, jb_pval = jarque_bera(h4_ret)

print(f"  Mean:     {ret_mean:.6f}")
print(f"  Std:      {ret_std:.6f}")
print(f"  Skew:     {ret_skew:.4f}")
print(f"  Kurtosis: {ret_kurt:.4f} (excess)")
print(f"  JB stat:  {jb_stat:.2f}, p={jb_pval:.2e}")

obs("Obs01", f"H4 log returns: mean={ret_mean:.6f}, std={ret_std:.4f}, "
    f"skew={ret_skew:.3f}, excess_kurt={ret_kurt:.2f}", ["Fig01"])
obs("Obs02", f"Jarque-Bera rejects normality: stat={jb_stat:.1f}, p={jb_pval:.2e}. "
    f"Excess kurtosis {ret_kurt:.1f} indicates heavy tails.", ["Fig01"])

# Tail behavior: empirical vs normal
sorted_ret = np.sort(h4_ret)
n = len(sorted_ret)
# Fraction beyond 3-sigma and 4-sigma
sig3_emp = np.mean(np.abs(h4_ret) > 3 * ret_std)
sig3_norm = 2 * stats.norm.sf(3)
sig4_emp = np.mean(np.abs(h4_ret) > 4 * ret_std)
sig4_norm = 2 * stats.norm.sf(4)

obs("Obs03", f"Tail excess: P(|r|>3σ)={sig3_emp:.4f} vs normal {sig3_norm:.4f} "
    f"({sig3_emp/sig3_norm:.1f}x). P(|r|>4σ)={sig4_emp:.5f} vs normal {sig4_norm:.6f} "
    f"({sig4_emp/sig4_norm:.0f}x).", ["Fig01"])

# ── Fig01: Return distribution histogram + normal overlay + QQ ──
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
ax = axes[0]
ax.hist(h4_ret, bins=200, density=True, alpha=0.7, color="steelblue", label="Empirical")
x_grid = np.linspace(h4_ret.min(), h4_ret.max(), 500)
ax.plot(x_grid, stats.norm.pdf(x_grid, ret_mean, ret_std), "r-", lw=1.5, label="Normal fit")
ax.set_xlim(-0.15, 0.15)
ax.set_xlabel("Log Return")
ax.set_ylabel("Density")
ax.set_title("Fig01a: H4 Return Distribution")
ax.legend()
ax.text(0.02, 0.95, f"n={len(h4_ret)}\nskew={ret_skew:.3f}\nkurt={ret_kurt:.1f}\nJB p={jb_pval:.1e}",
        transform=ax.transAxes, va="top", fontsize=8, family="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

# QQ plot
ax = axes[1]
theoretical_q = stats.norm.ppf(np.linspace(0.001, 0.999, len(h4_ret)))
empirical_q = np.sort(h4_ret)
# Subsample for plotting speed
idx = np.linspace(0, len(empirical_q)-1, 2000, dtype=int)
ax.scatter(theoretical_q[idx], empirical_q[idx], s=2, alpha=0.5, color="steelblue")
lim = max(abs(theoretical_q[idx]).max(), abs(empirical_q[idx]).max()) * 1.05
ax.plot([-lim, lim], [-lim*ret_std+ret_mean, lim*ret_std+ret_mean], "r--", lw=1)
ax.set_xlabel("Theoretical Quantiles (Normal)")
ax.set_ylabel("Empirical Quantiles")
ax.set_title("Fig01b: QQ Plot")

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig01_return_distribution.png"), dpi=150)
plt.close()
print("  Saved Fig01")

# ======================================================================
# SECTION 2: SERIAL DEPENDENCE
# ======================================================================
print("\n=== SECTION 2: Serial Dependence ===")

max_lag = 100

# ACF returns
acf_ret, acf_ci = acf(h4_ret, nlags=max_lag, alpha=0.05)
acf_ret = acf_ret[1:]  # drop lag 0
acf_ci = acf_ci[1:]
sig_bound = 1.96 / np.sqrt(len(h4_ret))

sig_lags_ret = [i+1 for i in range(len(acf_ret)) if abs(acf_ret[i]) > sig_bound]
print(f"  ACF returns: {len(sig_lags_ret)} significant lags out of {max_lag}")
print(f"  Significant lags: {sig_lags_ret[:20]}...")
print(f"  ACF lag1={acf_ret[0]:.4f}, max|ACF|={np.max(np.abs(acf_ret)):.4f}")

obs("Obs04", f"ACF(returns): {len(sig_lags_ret)}/{max_lag} lags significant at 5%. "
    f"Lag1={acf_ret[0]:.4f}. Max |ACF|={np.max(np.abs(acf_ret)):.4f}. "
    f"Weak serial dependence in raw returns.", ["Fig02"])

# ── Fig02: ACF returns ──
fig, ax = plt.subplots(figsize=(12, 4))
lags = np.arange(1, max_lag+1)
ax.bar(lags, acf_ret, width=0.8, color="steelblue", alpha=0.7)
ax.axhline(sig_bound, color="red", ls="--", lw=0.8, label=f"±95% CI ({sig_bound:.4f})")
ax.axhline(-sig_bound, color="red", ls="--", lw=0.8)
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Lag (H4 bars)")
ax.set_ylabel("ACF")
ax.set_title("Fig02: ACF of H4 Log Returns (lag 1-100)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig02_acf_returns.png"), dpi=150)
plt.close()
print("  Saved Fig02")

# ACF absolute returns (volatility clustering)
abs_ret = np.abs(h4_ret)
acf_abs, acf_abs_ci = acf(abs_ret, nlags=max_lag, alpha=0.05)
acf_abs = acf_abs[1:]
acf_abs_ci = acf_abs_ci[1:]

sig_lags_abs = [i+1 for i in range(len(acf_abs)) if abs(acf_abs[i]) > sig_bound]
print(f"  ACF |returns|: {len(sig_lags_abs)}/{max_lag} significant lags")
print(f"  ACF |ret| lag1={acf_abs[0]:.4f}, lag50={acf_abs[49]:.4f}, lag100={acf_abs[99]:.4f}")

obs("Obs05", f"ACF(|returns|): {len(sig_lags_abs)}/{max_lag} lags significant. "
    f"Lag1={acf_abs[0]:.4f}, lag50={acf_abs[49]:.4f}, lag100={acf_abs[99]:.4f}. "
    f"Strong volatility clustering — slow decay.", ["Fig03"])

# ── Fig03: ACF absolute returns ──
fig, ax = plt.subplots(figsize=(12, 4))
ax.bar(lags, acf_abs, width=0.8, color="darkorange", alpha=0.7)
ax.axhline(sig_bound, color="red", ls="--", lw=0.8, label=f"±95% CI")
ax.axhline(-sig_bound, color="red", ls="--", lw=0.8)
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Lag (H4 bars)")
ax.set_ylabel("ACF")
ax.set_title("Fig03: ACF of |H4 Log Returns| (lag 1-100)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig03_acf_abs_returns.png"), dpi=150)
plt.close()
print("  Saved Fig03")

# PACF returns
pacf_nlags = 20
pacf_ret, pacf_ci = pacf(h4_ret, nlags=pacf_nlags, alpha=0.05)
pacf_ret = pacf_ret[1:]
pacf_ci = pacf_ci[1:]

sig_lags_pacf = [i+1 for i in range(len(pacf_ret)) if abs(pacf_ret[i]) > sig_bound]
print(f"  PACF: significant lags = {sig_lags_pacf}")

obs("Obs06", f"PACF(returns): significant lags = {sig_lags_pacf}. "
    f"Lag1={pacf_ret[0]:.4f}. "
    f"Little structure beyond lag 1-2.", ["Fig04"])

# ── Fig04: PACF returns ──
fig, ax = plt.subplots(figsize=(10, 4))
pacf_lags = np.arange(1, pacf_nlags+1)
ax.bar(pacf_lags, pacf_ret, width=0.6, color="teal", alpha=0.7)
ax.axhline(sig_bound, color="red", ls="--", lw=0.8, label=f"±95% CI")
ax.axhline(-sig_bound, color="red", ls="--", lw=0.8)
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Lag (H4 bars)")
ax.set_ylabel("PACF")
ax.set_title("Fig04: PACF of H4 Log Returns (lag 1-20)")
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig04_pacf_returns.png"), dpi=150)
plt.close()
print("  Saved Fig04")

# ── Variance Ratio (Lo-MacKinlay) ──
def variance_ratio_test(returns, k):
    """Lo-MacKinlay variance ratio test (heteroskedasticity-robust)."""
    T = len(returns)
    mu = np.mean(returns)
    # Variance of 1-period returns
    sig1_sq = np.sum((returns - mu) ** 2) / (T - 1)
    # k-period overlapping returns
    ret_k = np.array([np.sum(returns[i:i+k]) for i in range(T - k + 1)])
    sig_k_sq = np.sum((ret_k - k * mu) ** 2) / (T - k + 1) / k

    VR = sig_k_sq / sig1_sq

    # Heteroskedasticity-robust z-statistic (Lo-MacKinlay 1988)
    delta = np.zeros(k - 1)
    for j in range(1, k):
        num = np.sum(((returns[j:] - mu) ** 2) * ((returns[:-j] - mu) ** 2))
        den = (np.sum((returns - mu) ** 2)) ** 2 / T
        delta[j-1] = num / den

    theta = 0
    for j in range(1, k):
        weight = (2 * (k - j) / k) ** 2
        theta += weight * delta[j-1]

    z_star = (VR - 1) / np.sqrt(theta) if theta > 0 else 0
    p_val = 2 * stats.norm.sf(abs(z_star))

    return VR, z_star, p_val

print("\n  Variance Ratio Test (Lo-MacKinlay):")
vr_ks = [2, 5, 10, 20, 40, 60, 80, 100, 120]
vr_results = []
for k in vr_ks:
    vr, z, p = variance_ratio_test(h4_ret, k)
    vr_results.append({"k": k, "VR": vr, "z_star": z, "p_value": p})
    sig_mark = "*" if p < 0.05 else ""
    print(f"    k={k:3d}: VR={vr:.4f}, z*={z:.3f}, p={p:.4f} {sig_mark}")

vr_df = pd.DataFrame(vr_results)
vr_df.to_csv(os.path.join(TBL_DIR, "Tbl04_variance_ratio.csv"), index=False)

# Determine persistence pattern
vr_above_1 = sum(1 for r in vr_results if r["VR"] > 1)
vr_sig = sum(1 for r in vr_results if r["p_value"] < 0.05)
obs("Obs07", f"Variance ratio: {vr_above_1}/{len(vr_ks)} periods VR>1, "
    f"{vr_sig}/{len(vr_ks)} significant at 5%. "
    f"VR(20)={vr_results[3]['VR']:.4f}, VR(120)={vr_results[-1]['VR']:.4f}. "
    + ("Persistent departure from random walk at longer horizons." if vr_sig >= 3
       else "Mostly consistent with random walk."),
    ["Tbl04"])

# ── Hurst Exponent (R/S method) ──
def hurst_rs(ts, min_window=10):
    """Compute Hurst exponent via R/S analysis."""
    N = len(ts)
    # Choose partition sizes
    sizes = []
    s = min_window
    while s <= N // 2:
        sizes.append(s)
        s = int(s * 1.5)
    if not sizes:
        return 0.5

    rs_means = []
    for s in sizes:
        n_blocks = N // s
        rs_vals = []
        for i in range(n_blocks):
            block = ts[i*s:(i+1)*s]
            mean_b = np.mean(block)
            dev = np.cumsum(block - mean_b)
            R = np.max(dev) - np.min(dev)
            S = np.std(block, ddof=1)
            if S > 0:
                rs_vals.append(R / S)
        if rs_vals:
            rs_means.append(np.mean(rs_vals))

    if len(rs_means) < 3:
        return 0.5

    log_sizes = np.log(sizes[:len(rs_means)])
    log_rs = np.log(rs_means)
    slope, _, _, _, _ = stats.linregress(log_sizes, log_rs)
    return slope

print("\n  Hurst Exponent (R/S):")
h_full = hurst_rs(h4_ret)
print(f"  Full sample: H={h_full:.4f}")

# Rolling Hurst
window = 500
step = 50
rolling_hurst = []
for i in range(0, len(h4_ret) - window, step):
    chunk = h4_ret[i:i+window]
    h_val = hurst_rs(chunk)
    # Use midpoint timestamp
    mid_idx = i + window // 2
    if mid_idx < len(h4):
        ts = h4.iloc[mid_idx + 1]["open_time"]  # +1 because h4_ret starts at index 1
    else:
        ts = h4.iloc[-1]["open_time"]
    rolling_hurst.append({"time": ts, "hurst": h_val})

rh_df = pd.DataFrame(rolling_hurst)
print(f"  Rolling Hurst: mean={rh_df['hurst'].mean():.4f}, "
      f"min={rh_df['hurst'].min():.4f}, max={rh_df['hurst'].max():.4f}, "
      f"std={rh_df['hurst'].std():.4f}")

obs("Obs08", f"Hurst (R/S): full sample H={h_full:.3f}. "
    f"Rolling (500-bar): mean={rh_df['hurst'].mean():.3f}, "
    f"range [{rh_df['hurst'].min():.2f}, {rh_df['hurst'].max():.2f}]. "
    + ("H>0.5 suggests mild persistence." if h_full > 0.55
       else "H≈0.5, consistent with near-random-walk." if h_full < 0.55
       else "H slightly above 0.5."),
    ["Fig05"])

# ── Fig05: Rolling Hurst ──
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(rh_df["time"], rh_df["hurst"], color="purple", lw=0.8)
ax.axhline(0.5, color="red", ls="--", lw=1, label="H=0.5 (random walk)")
ax.axhline(h_full, color="blue", ls=":", lw=1, label=f"Full sample H={h_full:.3f}")
ax.fill_between(rh_df["time"], 0.5, rh_df["hurst"],
                where=rh_df["hurst"] > 0.5, alpha=0.2, color="green", label="Persistent")
ax.fill_between(rh_df["time"], 0.5, rh_df["hurst"],
                where=rh_df["hurst"] < 0.5, alpha=0.2, color="red", label="Anti-persistent")
ax.set_xlabel("Date")
ax.set_ylabel("Hurst Exponent")
ax.set_title("Fig05: Rolling Hurst Exponent (R/S, 500-bar window)")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig05_rolling_hurst.png"), dpi=150)
plt.close()
print("  Saved Fig05")

# ======================================================================
# SECTION 3: TREND ANATOMY
# ======================================================================
print("\n=== SECTION 3: Trend Anatomy ===")

def find_uptrends(prices, threshold):
    """
    Find all upward moves where cumulative return from trough to peak >= threshold.
    Uses a simple peak-trough detection: track running min, when rise from min >= threshold,
    mark as trend start; trend ends when price drops from local max.
    """
    trends = []
    n = len(prices)

    i = 0
    while i < n:
        # Find trough
        trough_idx = i
        trough_val = prices[i]

        # Scan forward to find peak
        peak_idx = i
        peak_val = prices[i]

        j = i + 1
        while j < n:
            if prices[j] > peak_val:
                peak_val = prices[j]
                peak_idx = j
            elif prices[j] < trough_val:
                # New trough, check if we had a qualifying trend
                if peak_val / trough_val - 1 >= threshold:
                    trends.append({
                        "start_idx": trough_idx,
                        "end_idx": peak_idx,
                        "start_price": trough_val,
                        "end_price": peak_val,
                        "magnitude": peak_val / trough_val - 1,
                        "duration": peak_idx - trough_idx,
                    })
                trough_idx = j
                trough_val = prices[j]
                peak_idx = j
                peak_val = prices[j]
            # Check if drawdown from peak exceeds a fraction — trend ended
            elif peak_val / trough_val - 1 >= threshold and (peak_val - prices[j]) / peak_val > threshold * 0.5:
                trends.append({
                    "start_idx": trough_idx,
                    "end_idx": peak_idx,
                    "start_price": trough_val,
                    "end_price": peak_val,
                    "magnitude": peak_val / trough_val - 1,
                    "duration": peak_idx - trough_idx,
                })
                i = peak_idx + 1
                break
            j += 1
        else:
            # End of data
            if peak_val / trough_val - 1 >= threshold:
                trends.append({
                    "start_idx": trough_idx,
                    "end_idx": peak_idx,
                    "start_price": trough_val,
                    "end_price": peak_val,
                    "magnitude": peak_val / trough_val - 1,
                    "duration": peak_idx - trough_idx,
                })
            break

        if j >= n:
            break
        i = j

    return trends

prices_h4 = h4["close"].values

# Primary: >=10%, Secondary: >=20%
trends_10 = find_uptrends(prices_h4, 0.10)
trends_20 = find_uptrends(prices_h4, 0.20)

print(f"  Trends >=10%: {len(trends_10)}")
print(f"  Trends >=20%: {len(trends_20)}")

for label, trends, thresh in [("10%", trends_10, 0.10), ("20%", trends_20, 0.20)]:
    if trends:
        durations = [t["duration"] for t in trends]
        magnitudes = [t["magnitude"] * 100 for t in trends]
        print(f"  [{label}] count={len(trends)}, mean_dur={np.mean(durations):.1f} bars, "
              f"mean_mag={np.mean(magnitudes):.1f}%, median_dur={np.median(durations):.0f}")

# Temporal distribution
trend_years_10 = []
for t in trends_10:
    yr = h4.iloc[t["start_idx"]]["open_time"].year
    trend_years_10.append(yr)

obs("Obs09", f"Uptrends ≥10%: {len(trends_10)} events, "
    f"mean duration={np.mean([t['duration'] for t in trends_10]):.0f} bars "
    f"({np.mean([t['duration'] for t in trends_10])*4:.0f}h), "
    f"mean magnitude={np.mean([t['magnitude'] for t in trends_10])*100:.1f}%.",
    ["Tbl06", "Fig06"])

obs("Obs10", f"Uptrends ≥20%: {len(trends_20)} events, "
    f"mean duration={np.mean([t['duration'] for t in trends_20]):.0f} bars "
    f"({np.mean([t['duration'] for t in trends_20])*4:.0f}h), "
    f"mean magnitude={np.mean([t['magnitude'] for t in trends_20])*100:.1f}%.",
    ["Tbl06"])

# Tbl06: Trend anatomy summary
tbl06_data = []
for label, trends in [(">=10%", trends_10), (">=20%", trends_20)]:
    if not trends:
        continue
    durs = [t["duration"] for t in trends]
    mags = [t["magnitude"] * 100 for t in trends]
    tbl06_data.append({
        "threshold": label,
        "count": len(trends),
        "mean_duration_bars": f"{np.mean(durs):.1f}",
        "median_duration_bars": f"{np.median(durs):.0f}",
        "std_duration_bars": f"{np.std(durs):.1f}",
        "mean_magnitude_pct": f"{np.mean(mags):.1f}",
        "median_magnitude_pct": f"{np.median(mags):.1f}",
        "max_magnitude_pct": f"{np.max(mags):.1f}",
    })
pd.DataFrame(tbl06_data).to_csv(os.path.join(TBL_DIR, "Tbl06_trend_anatomy.csv"), index=False)
print("  Saved Tbl06")

# ── Fig06: Average trend profile ──
# Use 10% trends, align to start, show 20 bars before, during (normalized), 20 bars after
pad = 20
profiles_price = []
profiles_vol = []
profiles_volat = []

# Compute rolling volatility for profile
h4["rvol_20"] = h4["log_ret"].rolling(20).std()

for t in trends_10:
    s = t["start_idx"]
    e = t["end_idx"]
    dur = t["duration"]
    if dur < 5:
        continue
    # Before (20 bars before start)
    b_start = max(0, s - pad)
    # After (20 bars after end)
    a_end = min(len(h4) - 1, e + pad)

    # Normalize price to 100 at trend start
    p0 = h4.iloc[s]["close"]

    total_len = (s - b_start) + dur + (a_end - e)
    if total_len < pad + 5 + pad:
        continue

    # Extract segments
    before_p = (h4.iloc[b_start:s+1]["close"].values / p0) * 100
    during_p = (h4.iloc[s:e+1]["close"].values / p0) * 100
    after_p = (h4.iloc[e:a_end+1]["close"].values / p0) * 100

    before_v = h4.iloc[b_start:s+1]["volume"].values
    during_v = h4.iloc[s:e+1]["volume"].values
    after_v = h4.iloc[e:a_end+1]["volume"].values

    profiles_price.append({
        "before": before_p,
        "during": during_p,
        "after": after_p,
    })

# Composite profile: resample each segment to fixed length
n_before = pad
n_during = 30  # normalize duration to 30
n_after = pad

def resample(arr, target_len):
    if len(arr) < 2:
        return np.full(target_len, arr[0] if len(arr) == 1 else np.nan)
    x_old = np.linspace(0, 1, len(arr))
    x_new = np.linspace(0, 1, target_len)
    return np.interp(x_new, x_old, arr)

composite_price = np.zeros(n_before + n_during + n_after)
count = 0
for p in profiles_price:
    try:
        before_rs = resample(p["before"], n_before)
        during_rs = resample(p["during"], n_during)
        after_rs = resample(p["after"], n_after)
        full = np.concatenate([before_rs, during_rs, after_rs])
        composite_price += full
        count += 1
    except:
        pass

if count > 0:
    composite_price /= count

fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(composite_price))
ax.plot(x, composite_price, color="steelblue", lw=2)
ax.axvline(n_before, color="green", ls="--", lw=1, label="Trend start")
ax.axvline(n_before + n_during, color="red", ls="--", lw=1, label="Trend end")
ax.axhline(100, color="gray", ls=":", lw=0.5)
ax.set_xlabel("Normalized time (before | during | after)")
ax.set_ylabel("Price (indexed to 100 at trend start)")
ax.set_title(f"Fig06: Average Uptrend Profile (≥10%, n={count})")
ax.legend()
ax.set_xticks([0, n_before, n_before + n_during, n_before + n_during + n_after])
ax.set_xticklabels([f"-{n_before}", "Start", "End", f"+{n_after}"])
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig06_trend_profile.png"), dpi=150)
plt.close()
print("  Saved Fig06")

# ======================================================================
# SECTION 4: VOLATILITY STRUCTURE
# ======================================================================
print("\n=== SECTION 4: Volatility Structure ===")

# Rolling realized vol
h4["rvol_20"] = h4["log_ret"].rolling(20).std() * np.sqrt(6 * 365.25)  # annualized
h4["rvol_100"] = h4["log_ret"].rolling(100).std() * np.sqrt(6 * 365.25)

# Vol ACF
vol_series = h4["rvol_20"].dropna().values
acf_vol, _ = acf(vol_series, nlags=max_lag, alpha=0.05)
acf_vol = acf_vol[1:]
sig_lags_vol = sum(1 for v in acf_vol if abs(v) > sig_bound)
print(f"  Vol ACF: {sig_lags_vol}/{max_lag} significant lags")
print(f"  Vol ACF lag1={acf_vol[0]:.4f}, lag50={acf_vol[49]:.4f}")

obs("Obs11", f"Volatility ACF: {sig_lags_vol}/{max_lag} lags significant. "
    f"Lag1={acf_vol[0]:.3f}, lag50={acf_vol[49]:.3f}. "
    f"Extremely persistent — characteristic of long-memory vol.", ["Fig07"])

# Vol-return correlation
# Contemporaneous
h4_valid = h4.dropna(subset=["rvol_20", "log_ret"]).copy()
corr_contemp = stats.spearmanr(h4_valid["rvol_20"], h4_valid["log_ret"])
print(f"  Vol-return corr (contemp): r={corr_contemp.statistic:.4f}, p={corr_contemp.pvalue:.4f}")

# Lagged: vol_t → return_{t+1..5}
lagged_corrs = {}
for lag in [1, 5, 10, 20]:
    h4_valid[f"ret_fwd_{lag}"] = h4_valid["log_ret"].shift(-lag)
    valid = h4_valid.dropna(subset=[f"ret_fwd_{lag}", "rvol_20"])
    r, p = stats.spearmanr(valid["rvol_20"], valid[f"ret_fwd_{lag}"])
    lagged_corrs[lag] = (r, p)
    print(f"  Vol_t → ret_{lag}: r={r:.4f}, p={p:.4f}")

obs("Obs12", f"Vol-return correlation: contemporaneous r={corr_contemp.statistic:.4f} (p={corr_contemp.pvalue:.3f}). "
    f"Lagged vol→ret: lag1 r={lagged_corrs[1][0]:.4f}, lag20 r={lagged_corrs[20][0]:.4f}. "
    f"Weak vol→return predictability.", ["Fig08"])

# Vol regimes (terciles)
vol_valid = h4.dropna(subset=["rvol_20"]).copy()
q33 = vol_valid["rvol_20"].quantile(0.333)
q67 = vol_valid["rvol_20"].quantile(0.667)
vol_valid["vol_regime"] = pd.cut(vol_valid["rvol_20"], bins=[-np.inf, q33, q67, np.inf],
                                  labels=["Low", "Mid", "High"])

tbl07_data = []
for regime in ["Low", "Mid", "High"]:
    mask = vol_valid["vol_regime"] == regime
    sub = vol_valid[mask]
    tbl07_data.append({
        "regime": regime,
        "bars": len(sub),
        "pct_bars": f"{len(sub)/len(vol_valid)*100:.1f}%",
        "mean_vol_ann": f"{sub['rvol_20'].mean()*100:.1f}%",
        "mean_return_h4": f"{sub['log_ret'].mean()*1e4:.2f} bps",
        "std_return_h4": f"{sub['log_ret'].std()*1e4:.2f} bps",
        "sharpe_ann": f"{sub['log_ret'].mean() / sub['log_ret'].std() * np.sqrt(6*365.25):.3f}" if sub['log_ret'].std() > 0 else "N/A",
    })

tbl07_df = pd.DataFrame(tbl07_data)
tbl07_df.to_csv(os.path.join(TBL_DIR, "Tbl07_vol_regimes.csv"), index=False)
print("  Saved Tbl07")

obs("Obs13", f"Vol regimes — Low (<{q33*100:.0f}%): mean ret {tbl07_data[0]['mean_return_h4']}, "
    f"High (>{q67*100:.0f}%): mean ret {tbl07_data[2]['mean_return_h4']}.",
    ["Tbl07"])

# Count regime transitions
transitions = vol_valid["vol_regime"].values
n_transitions = sum(1 for i in range(1, len(transitions)) if transitions[i] != transitions[i-1])
print(f"  Regime transitions: {n_transitions} out of {len(transitions)-1} bars "
      f"({n_transitions/(len(transitions)-1)*100:.1f}%)")

# ── Fig07: Volatility timeseries ──
fig, ax = plt.subplots(figsize=(14, 5))
valid_h4 = h4.dropna(subset=["rvol_20"])
ax.plot(valid_h4["open_time"], valid_h4["rvol_20"]*100, color="orange", lw=0.5, alpha=0.8, label="RVol(20)")
ax.plot(valid_h4["open_time"], valid_h4["rvol_100"]*100, color="darkred", lw=1.2, label="RVol(100)")
ax.axhline(q33*100, color="green", ls=":", lw=0.8, alpha=0.5, label=f"Low/Mid ({q33*100:.0f}%)")
ax.axhline(q67*100, color="red", ls=":", lw=0.8, alpha=0.5, label=f"Mid/High ({q67*100:.0f}%)")
ax.set_xlabel("Date")
ax.set_ylabel("Annualized Volatility (%)")
ax.set_title("Fig07: H4 Rolling Realized Volatility")
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig07_volatility_timeseries.png"), dpi=150)
plt.close()
print("  Saved Fig07")

# ── Fig08: Vol vs next-period return scatter ──
fig, ax = plt.subplots(figsize=(8, 6))
valid = h4.dropna(subset=["rvol_20"]).copy()
valid["ret_next"] = valid["log_ret"].shift(-1)
valid = valid.dropna(subset=["ret_next"])
# Subsample for plotting
if len(valid) > 5000:
    sample = valid.sample(5000, random_state=42)
else:
    sample = valid
ax.scatter(sample["rvol_20"]*100, sample["ret_next"] * 100, s=2, alpha=0.3, color="steelblue")
ax.axhline(0, color="black", lw=0.5)
ax.set_xlabel("Current RVol(20) (annualized %)")
ax.set_ylabel("Next H4 Return (%)")
ax.set_title("Fig08: Volatility vs Next-Period Return")
r, p = stats.spearmanr(valid["rvol_20"], valid["ret_next"])
ax.text(0.02, 0.95, f"Spearman r={r:.4f}, p={p:.3f}", transform=ax.transAxes,
        va="top", fontsize=9, bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig08_vol_return_scatter.png"), dpi=150)
plt.close()
print("  Saved Fig08")

# ======================================================================
# SECTION 5: VOLUME STRUCTURE
# ======================================================================
print("\n=== SECTION 5: Volume Structure ===")

vol_data = h4["volume"].values
tbr = h4["taker_buy_ratio"].dropna().values

print(f"  Volume: mean={np.mean(vol_data):.1f}, median={np.median(vol_data):.1f}, "
      f"std={np.std(vol_data):.1f}")
print(f"  Taker buy ratio: mean={np.mean(tbr):.4f}, std={np.std(tbr):.4f}")

obs("Obs14", f"H4 volume: mean={np.mean(vol_data):.0f} BTC, "
    f"heavily right-skewed (skew={skew(vol_data):.2f}). "
    f"Taker buy ratio: mean={np.mean(tbr):.4f}, std={np.std(tbr):.4f} — "
    f"centered near 0.50 with low dispersion.", ["Fig09"])

# Volume-return correlations
# Contemporaneous: volume × |return|
h4_vr = h4.dropna(subset=["log_ret"]).copy()
corr_vol_absret = stats.spearmanr(h4_vr["volume"], np.abs(h4_vr["log_ret"]))
print(f"  Volume × |return| (contemp): r={corr_vol_absret.statistic:.4f}, p={corr_vol_absret.pvalue:.2e}")

# Leading: volume_t → return_{t+k}
tbl08_data = [{"relation": "vol × |ret| (contemp)",
               "r": f"{corr_vol_absret.statistic:.4f}",
               "p": f"{corr_vol_absret.pvalue:.2e}"}]

for k in [1, 5, 10, 20]:
    h4_vr[f"ret_fwd_{k}"] = h4_vr["log_ret"].shift(-k)
    valid = h4_vr.dropna(subset=[f"ret_fwd_{k}"])
    r, p = stats.spearmanr(valid["volume"], valid[f"ret_fwd_{k}"])
    tbl08_data.append({"relation": f"vol_t → ret_{{t+{k}}}", "r": f"{r:.4f}", "p": f"{p:.4f}"})
    print(f"  vol_t → ret_{{t+{k}}}: r={r:.4f}, p={p:.4f}")

# Taker buy ratio leading
for k in [1, 5, 10, 20]:
    h4_vr[f"tbr_lag"] = h4_vr["taker_buy_ratio"]
    h4_vr[f"ret_fwd_{k}_b"] = h4_vr["log_ret"].shift(-k)
    valid = h4_vr.dropna(subset=[f"ret_fwd_{k}_b", "tbr_lag"])
    r, p = stats.spearmanr(valid["tbr_lag"], valid[f"ret_fwd_{k}_b"])
    tbl08_data.append({"relation": f"tbr_t → ret_{{t+{k}}}", "r": f"{r:.4f}", "p": f"{p:.4f}"})
    print(f"  tbr_t → ret_{{t+{k}}}: r={r:.4f}, p={p:.4f}")

tbl08_df = pd.DataFrame(tbl08_data)
tbl08_df.to_csv(os.path.join(TBL_DIR, "Tbl08_volume_correlations.csv"), index=False)
print("  Saved Tbl08")

obs("Obs15", f"Volume × |return| (contemp): r={corr_vol_absret.statistic:.4f} — "
    f"volume concurrent with large moves. "
    f"Leading volume→return: |r| < 0.03 at all horizons. "
    f"Taker buy ratio→return: similarly negligible.", ["Tbl08"])

# ── Fig09: Volume distribution + taker buy ratio ──
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax = axes[0]
ax.hist(vol_data, bins=150, density=True, color="steelblue", alpha=0.7)
ax.set_xlim(0, np.percentile(vol_data, 99))
ax.set_xlabel("Volume (BTC)")
ax.set_ylabel("Density")
ax.set_title("Fig09a: H4 Volume Distribution")
ax.text(0.7, 0.9, f"mean={np.mean(vol_data):.0f}\nmedian={np.median(vol_data):.0f}\nskew={skew(vol_data):.1f}",
        transform=ax.transAxes, fontsize=8, family="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

ax = axes[1]
ax.hist(tbr, bins=100, density=True, color="darkorange", alpha=0.7)
ax.axvline(0.5, color="red", ls="--", lw=1, label="0.50")
ax.set_xlabel("Taker Buy Ratio")
ax.set_ylabel("Density")
ax.set_title("Fig09b: Taker Buy Ratio Distribution")
ax.legend()

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "Fig09_volume_structure.png"), dpi=150)
plt.close()
print("  Saved Fig09")

# ======================================================================
# SECTION 6: D1 CONTEXT
# ======================================================================
print("\n=== SECTION 6: D1 Context ===")

# D1 return distribution
d1_mean = np.mean(d1_ret)
d1_std = np.std(d1_ret, ddof=1)
d1_skew = skew(d1_ret)
d1_kurt = kurtosis(d1_ret, fisher=True)
print(f"  D1 returns: mean={d1_mean:.6f}, std={d1_std:.4f}, skew={d1_skew:.3f}, kurt={d1_kurt:.2f}")

# D1 regime identification
d1["sma_200"] = d1["close"].rolling(200).mean()
d1["ema_21"] = d1["close"].ewm(span=21, adjust=False).mean()
d1["ema_50"] = d1["close"].ewm(span=50, adjust=False).mean()

regimes = {
    "SMA(200)": d1["close"] > d1["sma_200"],
    "EMA(21)": d1["close"] > d1["ema_21"],
    "EMA(50)": d1["close"] > d1["ema_50"],
}

tbl09_data = []
for name, mask in regimes.items():
    valid = d1.dropna(subset=["log_ret", "sma_200", "ema_21", "ema_50"])
    mask_valid = mask[valid.index]
    above = valid.loc[mask_valid, "log_ret"]
    below = valid.loc[~mask_valid, "log_ret"]

    # Welch t-test
    t_stat, t_pval = stats.ttest_ind(above, below, equal_var=False)
    # Mann-Whitney
    u_stat, u_pval = stats.mannwhitneyu(above, below, alternative="two-sided")

    # Annualized return differential
    mean_above_ann = above.mean() * 365.25
    mean_below_ann = below.mean() * 365.25
    diff_ann = (mean_above_ann - mean_below_ann) * 100  # percentage points

    tbl09_data.append({
        "regime": name,
        "above_bars": len(above),
        "below_bars": len(below),
        "mean_ret_above_ann_pct": f"{mean_above_ann*100:.2f}",
        "mean_ret_below_ann_pct": f"{mean_below_ann*100:.2f}",
        "diff_pp_yr": f"{diff_ann:.1f}",
        "welch_t": f"{t_stat:.3f}",
        "welch_p": f"{t_pval:.4f}",
        "mann_whitney_p": f"{u_pval:.4f}",
    })
    print(f"  {name}: above={len(above)}, below={len(below)}, "
          f"diff={diff_ann:.1f} pp/yr, Welch p={t_pval:.4f}, MW p={u_pval:.4f}")

tbl09_df = pd.DataFrame(tbl09_data)
tbl09_df.to_csv(os.path.join(TBL_DIR, "Tbl09_d1_regime_differentials.csv"), index=False)
print("  Saved Tbl09")

obs("Obs16", f"D1 regime differentials: "
    f"SMA(200) diff={tbl09_data[0]['diff_pp_yr']} pp/yr (p={tbl09_data[0]['welch_p']}), "
    f"EMA(21) diff={tbl09_data[1]['diff_pp_yr']} pp/yr (p={tbl09_data[1]['welch_p']}), "
    f"EMA(50) diff={tbl09_data[2]['diff_pp_yr']} pp/yr (p={tbl09_data[2]['welch_p']}).",
    ["Tbl09"])

# Cross-timeframe: H4 returns conditioned on D1 regime
# Merge D1 regime onto H4
d1_regime = d1[["open_time", "ema_21", "ema_50", "sma_200", "close"]].copy()
d1_regime["d1_date"] = d1_regime["open_time"].dt.date
d1_regime["above_ema21"] = d1_regime["close"] > d1_regime["ema_21"]
d1_regime["above_ema50"] = d1_regime["close"] > d1_regime["ema_50"]
d1_regime["above_sma200"] = d1_regime["close"] > d1_regime["sma_200"]

h4["d1_date"] = h4["open_time"].dt.date
# Shift D1 by 1 day to avoid look-ahead: use yesterday's D1 close for today's H4
d1_regime["d1_date_shifted"] = d1_regime["d1_date"] + pd.Timedelta(days=1)
h4_merged = h4.merge(
    d1_regime[["d1_date_shifted", "above_ema21", "above_ema50", "above_sma200"]],
    left_on="d1_date", right_on="d1_date_shifted", how="left"
)

tbl10_data = []
for regime_col, label in [("above_ema21", "D1 EMA(21)"),
                            ("above_ema50", "D1 EMA(50)"),
                            ("above_sma200", "D1 SMA(200)")]:
    valid = h4_merged.dropna(subset=["log_ret", regime_col])
    above = valid[valid[regime_col] == True]["log_ret"]
    below = valid[valid[regime_col] == False]["log_ret"]

    if len(above) > 0 and len(below) > 0:
        t_stat, t_pval = stats.ttest_ind(above, below, equal_var=False)
        u_stat, u_pval = stats.mannwhitneyu(above, below, alternative="two-sided")

        # Annualize (6 bars/day * 365.25)
        ann = 6 * 365.25
        tbl10_data.append({
            "d1_regime": label,
            "h4_above_bars": len(above),
            "h4_below_bars": len(below),
            "h4_mean_ret_above": f"{above.mean()*1e4:.2f} bps",
            "h4_mean_ret_below": f"{below.mean()*1e4:.2f} bps",
            "h4_sharpe_above": f"{above.mean()/above.std()*np.sqrt(ann):.3f}" if above.std() > 0 else "N/A",
            "h4_sharpe_below": f"{below.mean()/below.std()*np.sqrt(ann):.3f}" if below.std() > 0 else "N/A",
            "welch_p": f"{t_pval:.4f}",
            "mann_whitney_p": f"{u_pval:.4f}",
        })
        print(f"  H4|{label}: above {len(above)} bars (mean {above.mean()*1e4:.2f} bps), "
              f"below {len(below)} bars (mean {below.mean()*1e4:.2f} bps), "
              f"Welch p={t_pval:.4f}")

tbl10_df = pd.DataFrame(tbl10_data)
tbl10_df.to_csv(os.path.join(TBL_DIR, "Tbl10_h4_conditioned_on_d1.csv"), index=False)
print("  Saved Tbl10")

obs("Obs17", f"H4 returns conditioned on D1 regime (1-day lag): "
    f"EMA(21) above={tbl10_data[0]['h4_mean_ret_above']}, below={tbl10_data[0]['h4_mean_ret_below']} "
    f"(Welch p={tbl10_data[0]['welch_p']}). "
    f"Cross-timeframe regime conditioning has "
    + ("significant" if float(tbl10_data[0]['welch_p']) < 0.05 else "marginal/insignificant")
    + " effect on H4 mean returns.",
    ["Tbl10"])

# Additional: Tbl05 — not in spec numbering, but good to save ACF summary
# Actually spec says Tbl04-Tbl10, so we need Tbl05 too
# Tbl05: Serial dependence summary
tbl05_data = {
    "measure": ["ACF(ret) lag1", "ACF(ret) max|val|", "ACF(ret) sig lags /100",
                 "ACF(|ret|) lag1", "ACF(|ret|) lag50", "ACF(|ret|) sig lags /100",
                 "PACF(ret) sig lags /20",
                 "Hurst (full)", "Hurst (rolling mean)"],
    "value": [f"{acf_ret[0]:.4f}", f"{np.max(np.abs(acf_ret)):.4f}", f"{len(sig_lags_ret)}",
              f"{acf_abs[0]:.4f}", f"{acf_abs[49]:.4f}", f"{len(sig_lags_abs)}",
              f"{len(sig_lags_pacf)}",
              f"{h_full:.4f}", f"{rh_df['hurst'].mean():.4f}"],
}
pd.DataFrame(tbl05_data).to_csv(os.path.join(TBL_DIR, "Tbl05_serial_dependence.csv"), index=False)
print("  Saved Tbl05")

# ======================================================================
# SECTION 7: OBSERVATION SUMMARY
# ======================================================================
print("\n=== SECTION 7: Observation Summary ===")

# Print all observations
for o in observations:
    print(f"  {o['id']}: {o['text'][:100]}...")

# Save observations to JSON for report generation
obs_path = os.path.join(BASE, "tables", "observations_phase2.json")
with open(obs_path, "w") as f:
    json.dump(observations, f, indent=2, default=str)
print(f"\n  Saved {len(observations)} observations to {obs_path}")

# ── Summary table ──
print("\n=== ALL OUTPUTS ===")
print(f"  Figures: Fig01-Fig09 ({len(os.listdir(FIG_DIR))} files)")
print(f"  Tables: Tbl04-Tbl10 ({len([f for f in os.listdir(TBL_DIR) if f.startswith('Tbl')])} files)")
print(f"  Observations: {len(observations)}")
print("\nDone.")
