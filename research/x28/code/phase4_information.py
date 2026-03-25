"""
Phase 4 — Information Content Analysis
X28 Research: Mutual information & Spearman correlation for 20+ features × 6 forward-return horizons.
Deliverable: Tbl11_information_ranking.csv
"""

import os, time, warnings
import numpy as np
import pandas as pd
from scipy import stats
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

t0 = time.time()

# ── Paths ─────────────────────────────────────────────────────────────
BASE = "/var/www/trading-bots/btc-spot-dev/research/x28"
DATA = "/var/www/trading-bots/btc-spot-dev/data"
TBL_DIR = os.path.join(BASE, "tables")
os.makedirs(TBL_DIR, exist_ok=True)

ANN = 365.25 * 6  # H4 bars per year

# ── Data loading ──────────────────────────────────────────────────────
def load_tf(tf):
    fp = os.path.join(DATA, f"btcusdt_{tf}.csv")
    df = pd.read_csv(fp)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.sort_values("open_time").reset_index(drop=True)
    return df

print("Loading data...")
h4 = load_tf("4h")
d1 = load_tf("1d")
print(f"  H4: {len(h4)} bars, D1: {len(d1)} bars")

closes = h4["close"].values.astype(float)
highs  = h4["high"].values.astype(float)
lows   = h4["low"].values.astype(float)
volumes = h4["volume"].values.astype(float)
n_bars = len(closes)

h4["log_ret"] = np.log(closes / np.roll(closes, 1))
h4["log_ret"].iloc[0] = 0.0
log_rets = h4["log_ret"].values.astype(float)

# ── Indicator helpers ─────────────────────────────────────────────────
def _ema(arr, span):
    return pd.Series(arr).ewm(span=span, adjust=False).mean().values

def _sma(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).mean().values

def _atr(hi, lo, cl, period):
    tr = np.empty(len(cl))
    tr[0] = hi[0] - lo[0]
    tr[1:] = np.maximum(hi[1:] - lo[1:],
              np.maximum(np.abs(hi[1:] - cl[:-1]),
                         np.abs(lo[1:] - cl[:-1])))
    return pd.Series(tr).ewm(span=period, adjust=False).mean().values

def _rolling_std(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).std().values

def _rolling_max(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).max().values

def _rolling_min(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).min().values

# ── Compute features ─────────────────────────────────────────────────
print("Computing features...")
features = {}

# Price-based
features["log_ret_1"] = log_rets
features["ret_5"] = pd.Series(closes).pct_change(5).values
features["ret_10"] = pd.Series(closes).pct_change(10).values
features["ret_20"] = pd.Series(closes).pct_change(20).values

ema_20 = _ema(closes, 20)
ema_50 = _ema(closes, 50)
ema_90 = _ema(closes, 90)
ema_120 = _ema(closes, 120)

features["ema_spread_20"] = (closes / ema_20 - 1)
features["ema_spread_50"] = (closes / ema_50 - 1)
features["ema_spread_90"] = (closes / ema_90 - 1)
features["ema_spread_120"] = (closes / ema_120 - 1)

# ROC
features["roc_10"] = np.where(pd.Series(closes).shift(10).values > 0,
                              (closes / pd.Series(closes).shift(10).values - 1) * 100, 0.0)
features["roc_20"] = np.where(pd.Series(closes).shift(20).values > 0,
                              (closes / pd.Series(closes).shift(20).values - 1) * 100, 0.0)
features["roc_40"] = np.where(pd.Series(closes).shift(40).values > 0,
                              (closes / pd.Series(closes).shift(40).values - 1) * 100, 0.0)

# Breakout position (close relative to N-bar high/low range)
for n in [20, 60]:
    hi_n = _rolling_max(closes, n)
    lo_n = _rolling_min(closes, n)
    rng = hi_n - lo_n
    features[f"breakout_pos_{n}"] = np.where(rng > 0, (closes - lo_n) / rng, 0.5)

# Volume-based
vol_ma20 = _sma(volumes, 20)
features["vdo"] = np.where(vol_ma20 > 0, volumes / vol_ma20 - 1, 0.0)
features["log_volume"] = np.log1p(volumes)

if "taker_buy_base_asset_volume" in h4.columns:
    tbv = h4["taker_buy_base_asset_volume"].values.astype(float)
    features["taker_buy_ratio"] = np.where(volumes > 0, tbv / volumes, 0.5)
    features["volume_delta"] = 2 * tbv - volumes  # buy - sell

# Volatility-based
features["rvol_10"] = _rolling_std(log_rets, 10)
features["rvol_60"] = _rolling_std(log_rets, 60)

atr_14 = _atr(highs, lows, closes, 14)
features["natr_14"] = np.where(closes > 0, atr_14 / closes, 0.0)

rvol_10 = features["rvol_10"]
rvol_60 = features["rvol_60"]
features["vol_ratio"] = np.where(rvol_60 > 0, rvol_10 / rvol_60, 1.0)

# D1 context → H4 (1-day lag)
d1["ema21"] = _ema(d1["close"].values, 21)
d1["ema50"] = _ema(d1["close"].values, 50)
d1["sma200"] = _sma(d1["close"].values, 200)
d1["d1_ema_spread_21"] = d1["close"] / d1["ema21"] - 1
d1["d1_ema_spread_50"] = d1["close"] / d1["ema50"] - 1
d1["regime_ema21"] = (d1["close"] > d1["ema21"]).astype(int)
d1["regime_ema50"] = (d1["close"] > d1["ema50"]).astype(int)

d1_merge = d1[["open_time", "regime_ema21", "regime_ema50",
               "d1_ema_spread_21", "d1_ema_spread_50"]].copy()
d1_merge["merge_time"] = d1_merge["open_time"] + pd.Timedelta(days=1)
h4_sorted = h4[["open_time"]].copy()
h4_sorted["open_time"] = h4_sorted["open_time"].astype("datetime64[us]")
d1_merge["merge_time"] = d1_merge["merge_time"].astype("datetime64[us]")
merged = pd.merge_asof(h4_sorted, d1_merge[["merge_time", "regime_ema21", "regime_ema50",
                                              "d1_ema_spread_21", "d1_ema_spread_50"]],
                       left_on="open_time", right_on="merge_time", direction="backward")

features["d1_regime_ema21"] = merged["regime_ema21"].fillna(0).values.astype(float)
features["d1_regime_ema50"] = merged["regime_ema50"].fillna(0).values.astype(float)
features["d1_ema_spread_21"] = merged["d1_ema_spread_21"].fillna(0).values.astype(float)
features["d1_ema_spread_50"] = merged["d1_ema_spread_50"].fillna(0).values.astype(float)

print(f"  {len(features)} features computed")

# ── Forward returns ──────────────────────────────────────────────────
horizons = [1, 5, 10, 20, 40, 60]
fwd_rets = {}
for k in horizons:
    fwd = np.full(n_bars, np.nan)
    fwd[:n_bars - k] = closes[k:] / closes[:n_bars - k] - 1
    fwd_rets[k] = fwd

# ── Mutual Information (histogram-based) ─────────────────────────────
def mutual_info_binned(x, y, n_bins=30):
    """Estimate MI(X;Y) via histogram binning."""
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 100:
        return np.nan

    # Adaptive binning using quantiles to handle skewed distributions
    try:
        x_edges = np.unique(np.percentile(x, np.linspace(0, 100, n_bins + 1)))
        y_edges = np.unique(np.percentile(y, np.linspace(0, 100, n_bins + 1)))
    except Exception:
        return np.nan

    if len(x_edges) < 3 or len(y_edges) < 3:
        return np.nan

    # Joint histogram
    h_xy, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
    # Marginals
    h_x = h_xy.sum(axis=1)
    h_y = h_xy.sum(axis=0)

    n = h_xy.sum()
    if n == 0:
        return np.nan

    # Convert to probabilities
    p_xy = h_xy / n
    p_x = h_x / n
    p_y = h_y / n

    # MI = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))
    mi = 0.0
    for i in range(len(p_x)):
        for j in range(len(p_y)):
            if p_xy[i, j] > 0 and p_x[i] > 0 and p_y[j] > 0:
                mi += p_xy[i, j] * np.log(p_xy[i, j] / (p_x[i] * p_y[j]))

    # Bias correction (Miller-Madow)
    n_nonzero = np.sum(p_xy > 0)
    n_nonzero_x = np.sum(p_x > 0)
    n_nonzero_y = np.sum(p_y > 0)
    bias = (n_nonzero - n_nonzero_x - n_nonzero_y + 1) / (2 * n)
    mi_corrected = max(mi - bias, 0.0)

    return mi_corrected

# ── Compute information table ─────────────────────────────────────────
print("Computing Spearman correlations and mutual information...")
rows = []
warmup = 200  # skip first 200 bars for indicator warmup

for feat_name, feat_vals in features.items():
    for k in horizons:
        fwd = fwd_rets[k]
        # Valid mask: both feature and forward return are finite, past warmup
        mask = np.isfinite(feat_vals) & np.isfinite(fwd)
        mask[:warmup] = False

        x = feat_vals[mask]
        y = fwd[mask]

        if len(x) < 100:
            rows.append({
                "feature": feat_name, "horizon": k,
                "spearman_r": np.nan, "spearman_p": np.nan,
                "mi_bits": np.nan, "n_obs": len(x)
            })
            continue

        rho, p_val = stats.spearmanr(x, y)
        mi = mutual_info_binned(x, y)
        # Convert MI from nats to bits
        mi_bits = mi / np.log(2) if np.isfinite(mi) else np.nan

        rows.append({
            "feature": feat_name, "horizon": k,
            "spearman_r": rho, "spearman_p": p_val,
            "mi_bits": mi_bits, "n_obs": int(len(x))
        })

df_info = pd.DataFrame(rows)

# ── Rank by max |Spearman r| across horizons ─────────────────────────
feat_max_r = df_info.groupby("feature")["spearman_r"].apply(lambda s: s.abs().max()).sort_values(ascending=False)
feat_max_mi = df_info.groupby("feature")["mi_bits"].max().sort_values(ascending=False)

# Add ranking columns
df_info["abs_spearman"] = df_info["spearman_r"].abs()

# Save full table
out_path = os.path.join(TBL_DIR, "Tbl11_information_ranking.csv")
df_info.to_csv(out_path, index=False)
print(f"  Saved: {out_path}")

# ── Summary: best horizon per feature ────────────────────────────────
print("\n═══ INFORMATION RANKING (by max |Spearman r| across horizons) ═══")
print(f"{'Feature':<22} {'Best k':>6} {'|r|':>8} {'p-value':>10} {'MI(bits)':>10}")
print("─" * 60)

for feat_name in feat_max_r.index:
    sub = df_info[df_info["feature"] == feat_name]
    best_row = sub.loc[sub["abs_spearman"].idxmax()]
    k = int(best_row["horizon"])
    r = best_row["spearman_r"]
    p = best_row["spearman_p"]
    mi = best_row["mi_bits"]
    print(f"  {feat_name:<20} k={k:>3}  |r|={abs(r):.4f}  p={p:.2e}  MI={mi:.4f}")

# ── Summary: aggregate by feature category ───────────────────────────
print("\n═══ CATEGORY SUMMARY ═══")
categories = {
    "Price-based": ["log_ret_1", "ret_5", "ret_10", "ret_20",
                    "ema_spread_20", "ema_spread_50", "ema_spread_90", "ema_spread_120",
                    "roc_10", "roc_20", "roc_40", "breakout_pos_20", "breakout_pos_60"],
    "Volume-based": ["vdo", "log_volume", "taker_buy_ratio", "volume_delta"],
    "Volatility-based": ["rvol_10", "rvol_60", "natr_14", "vol_ratio"],
    "D1 context": ["d1_regime_ema21", "d1_regime_ema50", "d1_ema_spread_21", "d1_ema_spread_50"],
}

for cat, feats in categories.items():
    present = [f for f in feats if f in feat_max_r.index]
    if not present:
        continue
    max_r_cat = max(feat_max_r[f] for f in present)
    best_feat = max(present, key=lambda f: feat_max_r[f])
    print(f"  {cat}: best = {best_feat} (|r|={max_r_cat:.4f})")

# ── Horizon profile: which horizons carry most information? ──────────
print("\n═══ HORIZON PROFILE (mean |Spearman r| across all features) ═══")
for k in horizons:
    sub = df_info[df_info["horizon"] == k]
    mean_r = sub["abs_spearman"].mean()
    mean_mi = sub["mi_bits"].mean()
    print(f"  k={k:>3}: mean |r| = {mean_r:.4f}, mean MI = {mean_mi:.4f} bits")

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.1f}s")
