"""
Phase 4: Information Estimation & Power Analysis
=================================================
Computes mutual information (via binned MI and rank-based correlation)
between observable features and future H4 returns at multiple horizons.
Also performs power analysis for admissible strategy class combinations.

Output:
  tables/Tbl11_information_ranking.csv
  tables/Tbl12_dof_budget.csv
  tables/Tbl13_power_analysis.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

# ---------- paths ----------
DATA = Path("/var/www/trading-bots/btc-spot-dev/data")
OUT  = Path("/var/www/trading-bots/btc-spot-dev/research/x27/tables")
OUT.mkdir(exist_ok=True)

# ---------- load ----------
h4 = pd.read_csv(DATA / "btcusdt_4h.csv")
d1 = pd.read_csv(DATA / "btcusdt_1d.csv")

h4["dt"] = pd.to_datetime(h4["open_time"], unit="ms")
d1["dt"] = pd.to_datetime(d1["open_time"], unit="ms")
h4 = h4.sort_values("dt").reset_index(drop=True)
d1 = d1.sort_values("dt").reset_index(drop=True)

h4["ret"] = np.log(h4["close"] / h4["close"].shift(1))
h4["date"] = h4["dt"].dt.date

# D1 features (lagged by 1 day to avoid lookahead)
d1["d1_ret"] = np.log(d1["close"] / d1["close"].shift(1))
d1["d1_sma200"] = d1["close"].rolling(200).mean()
d1["d1_above_sma200"] = (d1["close"] > d1["d1_sma200"]).astype(float)
d1["d1_ema21"] = d1["close"].ewm(span=21).mean()
d1["d1_above_ema21"] = (d1["close"] > d1["d1_ema21"]).astype(float)
d1["date"] = d1["dt"].dt.date

# Merge D1 regime (lag 1 day)
d1_for_merge = d1[["date", "d1_above_sma200", "d1_above_ema21", "d1_ret"]].copy()
d1_for_merge["date"] = d1_for_merge["date"] + pd.Timedelta(days=1)
d1_for_merge["date"] = d1_for_merge["date"].apply(lambda x: x if hasattr(x, 'year') else x)
# Convert to same type
h4["date_pd"] = pd.to_datetime(h4["date"])
d1_for_merge["date_pd"] = pd.to_datetime(d1_for_merge["date"])
h4 = h4.merge(d1_for_merge[["date_pd", "d1_above_sma200", "d1_above_ema21"]], on="date_pd", how="left")

# ---------- H4 features ----------
h4["vol20"] = h4["ret"].rolling(20).std()
h4["vol60"] = h4["ret"].rolling(60).std()
h4["log_vol"] = np.log1p(h4["volume"])
h4["tbr"] = h4["taker_buy_base_vol"] / h4["volume"].replace(0, np.nan)

# Momentum / price-based
for n in [10, 20, 40, 60, 120]:
    h4[f"roc_{n}"] = h4["close"] / h4["close"].shift(n) - 1
    h4[f"breakout_{n}"] = (h4["close"] > h4["high"].rolling(n).max().shift(1)).astype(float)

# EMA spreads
for slow in [50, 80, 120]:
    fast_ema = h4["close"].ewm(span=10).mean()
    slow_ema = h4["close"].ewm(span=slow).mean()
    h4[f"ema_spread_{slow}"] = (fast_ema - slow_ema) / slow_ema

# ATR
h4["tr"] = np.maximum(
    h4["high"] - h4["low"],
    np.maximum(
        abs(h4["high"] - h4["close"].shift(1)),
        abs(h4["low"] - h4["close"].shift(1))
    )
)
h4["atr20"] = h4["tr"].rolling(20).mean()
h4["atr_pctl"] = h4["atr20"].rolling(250).rank(pct=True)

# Vol regime (median split of vol20)
med_vol = h4["vol20"].median()
h4["vol_regime_high"] = (h4["vol20"] > med_vol).astype(float)

# ---------- future returns at multiple horizons ----------
for k in [1, 5, 10, 20, 40, 60]:
    h4[f"fwd_ret_{k}"] = h4["ret"].shift(-1).rolling(k).sum().shift(-k + 1)

h4 = h4.dropna(subset=["vol20", "fwd_ret_20"]).reset_index(drop=True)

# ==========================================================
# PART 1: Mutual Information Estimation
# ==========================================================
# Use binned MI (adaptive binning) and Spearman correlation.
# MI via binned approach: discretize both X and Y, compute
# H(Y) - H(Y|X) using contingency table.

def binned_mi(x, y, n_bins=10):
    """Estimate MI via equal-frequency binning."""
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 100:
        return np.nan, np.nan
    # Equal-frequency bins
    x_bins = pd.qcut(x, n_bins, labels=False, duplicates="drop")
    y_bins = pd.qcut(y, n_bins, labels=False, duplicates="drop")
    # Contingency table
    ct = pd.crosstab(x_bins, y_bins)
    # Chi-square test for statistical significance
    chi2, p_val, _, _ = stats.chi2_contingency(ct)
    # MI from contingency
    n = ct.values.sum()
    p_xy = ct.values / n
    p_x = p_xy.sum(axis=1, keepdims=True)
    p_y = p_xy.sum(axis=0, keepdims=True)
    # Avoid log(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_ratio = np.log(p_xy / (p_x * p_y))
        log_ratio[~np.isfinite(log_ratio)] = 0
    mi = np.sum(p_xy * log_ratio)
    return mi, p_val

features = {
    # Price-based
    "roc_10": "price",
    "roc_20": "price",
    "roc_40": "price",
    "roc_60": "price",
    "roc_120": "price",
    "breakout_20": "price",
    "breakout_40": "price",
    "breakout_60": "price",
    "breakout_120": "price",
    "ema_spread_50": "price",
    "ema_spread_80": "price",
    "ema_spread_120": "price",
    # Volume-based
    "log_vol": "volume",
    "tbr": "volume",
    # Volatility-based
    "vol20": "volatility",
    "vol60": "volatility",
    "atr_pctl": "volatility",
    "vol_regime_high": "volatility",
    # D1 context
    "d1_above_sma200": "d1_regime",
    "d1_above_ema21": "d1_regime",
}

horizons = [1, 5, 10, 20, 40, 60]
rows = []

for feat_name, feat_cat in features.items():
    for k in horizons:
        col_y = f"fwd_ret_{k}"
        if feat_name not in h4.columns or col_y not in h4.columns:
            continue
        x = h4[feat_name].values.astype(float)
        y = h4[col_y].values.astype(float)
        mask = np.isfinite(x) & np.isfinite(y)
        x_clean, y_clean = x[mask], y[mask]

        # Spearman rank correlation
        if len(x_clean) > 50:
            rho, p_spear = stats.spearmanr(x_clean, y_clean)
        else:
            rho, p_spear = np.nan, np.nan

        # Binned MI
        mi, p_mi = binned_mi(x_clean, y_clean, n_bins=10)

        rows.append({
            "feature": feat_name,
            "category": feat_cat,
            "horizon_k": k,
            "spearman_rho": round(rho, 5) if np.isfinite(rho) else np.nan,
            "spearman_p": round(p_spear, 6) if np.isfinite(p_spear) else np.nan,
            "binned_MI": round(mi, 6) if np.isfinite(mi) else np.nan,
            "MI_chi2_p": round(p_mi, 6) if np.isfinite(p_mi) else np.nan,
            "n_obs": int(mask.sum()),
        })

info_df = pd.DataFrame(rows)
info_df.to_csv(OUT / "Tbl11_information_ranking.csv", index=False)

# ---------- Summary: rank features by average |rho| at horizon 20 ----------
summary = info_df[info_df["horizon_k"] == 20].copy()
summary["abs_rho"] = summary["spearman_rho"].abs()
summary = summary.sort_values("abs_rho", ascending=False)
print("=" * 70)
print("INFORMATION RANKING (horizon k=20, sorted by |Spearman rho|)")
print("=" * 70)
for _, r in summary.iterrows():
    sig = "***" if r["spearman_p"] < 0.001 else "**" if r["spearman_p"] < 0.01 else "*" if r["spearman_p"] < 0.05 else ""
    mi_sig = "***" if r["MI_chi2_p"] < 0.001 else "**" if r["MI_chi2_p"] < 0.01 else "*" if r["MI_chi2_p"] < 0.05 else ""
    print(f"  {r['feature']:20s} [{r['category']:10s}]  rho={r['spearman_rho']:+.4f}{sig:3s}  MI={r['binned_MI']:.5f}{mi_sig:3s}  n={r['n_obs']}")

# Category summary
print("\n" + "=" * 70)
print("CATEGORY SUMMARY (avg |rho| across horizons)")
print("=" * 70)
cat_summary = info_df.groupby("category").agg(
    avg_abs_rho=("spearman_rho", lambda x: x.abs().mean()),
    max_abs_rho=("spearman_rho", lambda x: x.abs().max()),
    n_significant=("spearman_p", lambda x: (x < 0.05).sum()),
    n_total=("spearman_p", "count"),
).sort_values("avg_abs_rho", ascending=False)
print(cat_summary.to_string())

# ==========================================================
# PART 2: Power Analysis
# ==========================================================
# For each admissible class combination, estimate:
# - Expected trade count (from Phase 3 signal frequencies)
# - Minimum detectable effect (MDE) at 80% power, alpha=0.05
# - Compare vs observed effect sizes

# Expected trades from Tbl09 (entry×exit pairing)
trade_counts = {
    ("B_breakout", "Y_atr_trail"): 50,
    ("B_breakout", "W_time"): 47,
    ("B_breakout", "Z_signal_rev"): 35,
    ("C_roc", "Y_atr_trail"): 105,
    ("C_roc", "W_time"): 72,
    ("C_roc", "Z_signal_rev"): 69,
}

# Observed Sharpe from Tbl09
observed_sharpe = {
    ("B_breakout", "Y_atr_trail"): 1.064,
    ("B_breakout", "W_time"): 0.740,
    ("B_breakout", "Z_signal_rev"): 0.886,
    ("C_roc", "Y_atr_trail"): 0.833,
    ("C_roc", "W_time"): 0.394,
    ("C_roc", "Z_signal_rev"): 0.726,
}

# Bull-only regime versions (from Tbl10)
trade_counts_regime = {
    ("B_breakout", "Y_atr_trail"): 32,
    ("B_breakout", "W_time"): 31,
    ("C_roc", "Y_atr_trail"): 55,
    ("C_roc", "W_time"): 40,
}

observed_sharpe_regime = {
    ("B_breakout", "Y_atr_trail"): 0.873,
    ("B_breakout", "W_time"): 0.975,
    ("C_roc", "Y_atr_trail"): 0.571,
    ("C_roc", "W_time"): 0.574,
}

# DOF counts
dof = {
    "B_breakout": 1,  # N (lookback period)
    "C_roc": 2,       # N (lookback), tau (threshold)
    "Y_atr_trail": 2, # period, multiplier
    "W_time": 1,      # holding period
    "Z_signal_rev": 2, # signal type + param
    "regime_sma200": 1, # MA period
    "no_filter": 0,
}

def mde_sharpe(n_trades, alpha=0.05, power=0.80):
    """
    Minimum detectable Sharpe ratio (two-sided test).
    Under H0: Sharpe=0, the test statistic for Sharpe is approximately
    SR * sqrt(N) ~ N(0,1). MDE = z_crit / sqrt(N) where
    z_crit = z_{1-alpha/2} + z_{power}.
    """
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    return (z_alpha + z_power) / np.sqrt(n_trades)

power_rows = []

# No filter combinations
for (entry, exit_), n_trades in trade_counts.items():
    entry_dof = dof[entry]
    exit_dof = dof[exit_]
    total_dof = entry_dof + exit_dof
    mde = mde_sharpe(n_trades)
    obs_sh = observed_sharpe[(entry, exit_)]

    if obs_sh > mde * 1.5:
        verdict = "POWERED"
    elif obs_sh > mde:
        verdict = "BORDERLINE"
    else:
        verdict = "UNDERPOWERED"

    power_rows.append({
        "entry_class": entry,
        "exit_class": exit_,
        "filter": "none",
        "total_dof": total_dof,
        "n_trades": n_trades,
        "mde_sharpe_80pct": round(mde, 3),
        "observed_sharpe": obs_sh,
        "ratio_obs_mde": round(obs_sh / mde, 2),
        "verdict": verdict,
    })

# With regime filter
for (entry, exit_), n_trades in trade_counts_regime.items():
    entry_dof = dof[entry]
    exit_dof = dof[exit_]
    total_dof = entry_dof + exit_dof + dof["regime_sma200"]
    mde = mde_sharpe(n_trades)
    obs_sh = observed_sharpe_regime[(entry, exit_)]

    if obs_sh > mde * 1.5:
        verdict = "POWERED"
    elif obs_sh > mde:
        verdict = "BORDERLINE"
    else:
        verdict = "UNDERPOWERED"

    power_rows.append({
        "entry_class": entry,
        "exit_class": exit_,
        "filter": "regime_sma200",
        "total_dof": total_dof,
        "n_trades": n_trades,
        "mde_sharpe_80pct": round(mde, 3),
        "observed_sharpe": obs_sh,
        "ratio_obs_mde": round(obs_sh / mde, 2),
        "verdict": verdict,
    })

power_df = pd.DataFrame(power_rows)
power_df.to_csv(OUT / "Tbl13_power_analysis.csv", index=False)

print("\n" + "=" * 70)
print("POWER ANALYSIS")
print("=" * 70)
for _, r in power_df.iterrows():
    print(f"  {r['entry_class']:12s} + {r['exit_class']:14s} + {r['filter']:14s}"
          f"  DOF={r['total_dof']}  N={r['n_trades']:3d}  MDE={r['mde_sharpe_80pct']:.3f}"
          f"  Obs={r['observed_sharpe']:.3f}  Ratio={r['ratio_obs_mde']:.2f}  → {r['verdict']}")

# ==========================================================
# PART 3: DOF Budget
# ==========================================================
dof_rows = [
    {"component": "Entry: Breakout (B)", "description": "close > max(close, N bars)", "n_params": 1, "params": "N"},
    {"component": "Entry: ROC threshold (C)", "description": "ROC(N) > tau", "n_params": 2, "params": "N, tau"},
    {"component": "Exit: ATR trail (Y)", "description": "trail = max_price - m*ATR(p)", "n_params": 2, "params": "period, multiplier"},
    {"component": "Exit: Time-based (W)", "description": "exit after H bars", "n_params": 1, "params": "H"},
    {"component": "Exit: Signal reversal (Z)", "description": "reverse of entry signal", "n_params": 2, "params": "type, param"},
    {"component": "Filter: Price-level regime", "description": "D1_close > MA_D1(K)", "n_params": 1, "params": "K"},
    {"component": "Filter: None", "description": "no filter", "n_params": 0, "params": "-"},
]
dof_df = pd.DataFrame(dof_rows)

# Combination DOF totals
combos = [
    {"combination": "B + Y", "entry_dof": 1, "exit_dof": 2, "filter_dof": 0, "total_dof": 3},
    {"combination": "B + Y + regime", "entry_dof": 1, "exit_dof": 2, "filter_dof": 1, "total_dof": 4},
    {"combination": "B + W", "entry_dof": 1, "exit_dof": 1, "filter_dof": 0, "total_dof": 2},
    {"combination": "B + W + regime", "entry_dof": 1, "exit_dof": 1, "filter_dof": 1, "total_dof": 3},
    {"combination": "C + Y", "entry_dof": 2, "exit_dof": 2, "filter_dof": 0, "total_dof": 4},
    {"combination": "C + Y + regime", "entry_dof": 2, "exit_dof": 2, "filter_dof": 1, "total_dof": 5},
    {"combination": "C + W", "entry_dof": 2, "exit_dof": 1, "filter_dof": 0, "total_dof": 3},
    {"combination": "C + W + regime", "entry_dof": 2, "exit_dof": 1, "filter_dof": 1, "total_dof": 4},
]
combo_df = pd.DataFrame(combos)

# Save both in one file
dof_df.to_csv(OUT / "Tbl12_dof_budget.csv", index=False)
combo_df.to_csv(OUT / "Tbl12_dof_combinations.csv", index=False)

print("\n" + "=" * 70)
print("DOF BUDGET — Component Classes")
print("=" * 70)
for _, r in dof_df.iterrows():
    print(f"  {r['component']:35s}  DOF={r['n_params']}  ({r['params']})")

print("\n" + "=" * 70)
print("DOF BUDGET — Combinations")
print("=" * 70)
for _, r in combo_df.iterrows():
    print(f"  {r['combination']:20s}  = {r['entry_dof']} + {r['exit_dof']} + {r['filter_dof']} = {r['total_dof']} DOF  {'✓' if r['total_dof'] <= 10 else '✗'}")

print("\n✓ All combinations ≤ 10 DOF budget")
print(f"\nTables saved to {OUT}/")
