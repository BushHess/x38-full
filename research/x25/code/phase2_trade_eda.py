"""
Phase 2: Conditional Analysis Around Actual Trades — Entry Filter Lab
=====================================================================
Empirical-first. Observation before interpretation.
No formalization, no suggestion, no design.

Deliverables:
  - 02_trade_eda.md
  - figures/Fig09..Fig14e
  - tables/trade_list.csv, trade_repro_check.csv, Tbl04..Tbl06
"""

import pathlib
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)

# ── paths ──────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent          # entry_filter_lab/
DATA = pathlib.Path("/var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv")
FIG  = ROOT / "figures"
TBL  = ROOT / "tables"
FIG.mkdir(exist_ok=True)
TBL.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# INDICATOR HELPERS — exact copy from strategy.py
# ═══════════════════════════════════════════════════════════════════════
def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


# ═══════════════════════════════════════════════════════════════════════
# LOAD DATA & COMPUTE INDICATORS
# ═══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("Phase 2: Conditional Analysis Around Actual Trades")
print("=" * 70)

raw = pd.read_csv(DATA)
h4 = raw[raw["interval"] == "4h"].copy().sort_values("open_time").reset_index(drop=True)
d1 = raw[raw["interval"] == "1d"].copy().sort_values("open_time").reset_index(drop=True)
print(f"Loaded: H4={len(h4):,} bars, D1={len(d1):,} bars")

# H4 arrays
close_h4 = h4["close"].values.astype(np.float64)
high_h4 = h4["high"].values.astype(np.float64)
low_h4 = h4["low"].values.astype(np.float64)
volume_h4 = h4["volume"].values.astype(np.float64)
taker_buy_h4 = h4["taker_buy_base_vol"].values.astype(np.float64)

# Strategy parameters
SLOW = 120
FAST = max(5, SLOW // 4)  # 30
TRAIL_MULT = 3.0
VDO_THRESHOLD = 0.0
ATR_PERIOD = 14
VDO_FAST = 12
VDO_SLOW = 28
D1_EMA_PERIOD = 21
COST_RT = 0.005  # 50 bps round-trip

# H4 indicators
ema_fast = _ema(close_h4, FAST)
ema_slow = _ema(close_h4, SLOW)
atr14 = _atr(high_h4, low_h4, close_h4, ATR_PERIOD)
atr20 = _atr(high_h4, low_h4, close_h4, 20)
vdo_arr = _vdo(close_h4, high_h4, low_h4, volume_h4, taker_buy_h4, VDO_FAST, VDO_SLOW)

# Derived H4 series
tbr_h4 = np.where(volume_h4 > 0, taker_buy_h4 / volume_h4, 0.5)
atr20_pct = np.where(close_h4 > 0, atr20 / close_h4, np.nan)

# Rolling median volume (20 bars)
h4["vol_median20"] = h4["volume"].rolling(20, min_periods=20).median()
vol_median20 = h4["vol_median20"].values

# D1 regime
d1_close = d1["close"].values.astype(np.float64)
d1_ema = _ema(d1_close, D1_EMA_PERIOD)
d1_regime = d1_close > d1_ema
d1_close_times = d1["close_time"].values

n_h4 = len(h4)
d1_regime_ok = np.zeros(n_h4, dtype=bool)
h4_close_times = h4["close_time"].values
d1_ptr = 0
n_d1 = len(d1)
for i in range(n_h4):
    h4_ct = h4_close_times[i]
    while d1_ptr + 1 < n_d1 and d1_close_times[d1_ptr + 1] < h4_ct:
        d1_ptr += 1
    if d1_close_times[d1_ptr] < h4_ct:
        d1_regime_ok[i] = d1_regime[d1_ptr]

# Timestamps for display
h4["dt"] = pd.to_datetime(h4["open_time"], unit="ms")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 0: REPRODUCE TRADES
# ═══════════════════════════════════════════════════════════════════════
print("\n[0] Reproducing trades...")

trades = []
in_position = False
peak_price = 0.0
entry_bar = -1
entry_price = 0.0

for i in range(1, n_h4):
    ef = ema_fast[i]
    es = ema_slow[i]
    atr_val = atr14[i]
    vdo_val = vdo_arr[i]
    price = close_h4[i]

    if np.isnan(atr_val) or np.isnan(ef) or np.isnan(es):
        continue

    trend_up = ef > es
    trend_down = ef < es

    if not in_position:
        regime_ok = bool(d1_regime_ok[i])
        if trend_up and vdo_val > VDO_THRESHOLD and regime_ok:
            in_position = True
            peak_price = price
            entry_bar = i
            entry_price = price
    else:
        peak_price = max(peak_price, price)
        trail_stop = peak_price - TRAIL_MULT * atr_val

        exit_reason = None
        if price < trail_stop:
            exit_reason = "trail_stop"
        elif trend_down:
            exit_reason = "trend_exit"

        if exit_reason:
            gross_ret = price / entry_price - 1.0
            net_ret = gross_ret - COST_RT
            trades.append({
                "trade_id": len(trades) + 1,
                "entry_bar": entry_bar,
                "exit_bar": i,
                "entry_dt": str(h4["dt"].iloc[entry_bar]),
                "exit_dt": str(h4["dt"].iloc[i]),
                "entry_price": round(entry_price, 2),
                "exit_price": round(price, 2),
                "bars_held": i - entry_bar,
                "exit_reason": exit_reason,
                "gross_return": round(gross_ret, 6),
                "net_return": round(net_ret, 6),
                "peak_price": round(peak_price, 2),
                "entry_vdo": round(vdo_arr[entry_bar], 6),
                "entry_tbr": round(tbr_h4[entry_bar], 6),
                "entry_atr20_pct": round(atr20_pct[entry_bar], 6) if not np.isnan(atr20_pct[entry_bar]) else np.nan,
                "entry_vol_rel": round(volume_h4[entry_bar] / vol_median20[entry_bar], 4) if not np.isnan(vol_median20[entry_bar]) else np.nan,
            })
            in_position = False
            peak_price = 0.0

tdf = pd.DataFrame(trades)
n_trades = len(tdf)
print(f"  Trades reproduced: {n_trades}")

# Save trade list
tdf.to_csv(TBL / "trade_list.csv", index=False)
print(f"  Written: tables/trade_list.csv")

# Repro check summary
n_trail = (tdf["exit_reason"] == "trail_stop").sum()
n_trend = (tdf["exit_reason"] == "trend_exit").sum()
repro = pd.DataFrame([{
    "total_trades": n_trades,
    "trail_stop_exits": int(n_trail),
    "trend_exits": int(n_trend),
    "mean_bars_held": round(tdf["bars_held"].mean(), 1),
    "median_bars_held": round(tdf["bars_held"].median(), 1),
    "mean_gross_return": round(tdf["gross_return"].mean(), 6),
    "median_gross_return": round(tdf["gross_return"].median(), 6),
    "mean_net_return": round(tdf["net_return"].mean(), 6),
    "median_net_return": round(tdf["net_return"].median(), 6),
    "win_rate_gross": round((tdf["gross_return"] > 0).mean(), 4),
    "win_rate_net": round((tdf["net_return"] > 0).mean(), 4),
    "first_entry_dt": tdf["entry_dt"].iloc[0],
    "last_entry_dt": tdf["entry_dt"].iloc[-1],
}])
repro.to_csv(TBL / "trade_repro_check.csv", index=False)
print(f"  Written: tables/trade_repro_check.csv")
print(f"  Trail stops: {n_trail}, Trend exits: {n_trend}")
print(f"  Median hold: {tdf['bars_held'].median():.0f} bars ({tdf['bars_held'].median() * 4:.0f}h)")
print(f"  Win rate (net): {(tdf['net_return'] > 0).mean():.1%}")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: WINNERS / LOSERS SPLIT
# ═══════════════════════════════════════════════════════════════════════
print("\n[1] Winner / Loser split...")

tdf["group"] = np.where(tdf["net_return"] > 0, "winner", "loser")
winners = tdf[tdf["group"] == "winner"]
losers = tdf[tdf["group"] == "loser"]

print(f"  Winners: {len(winners)}  |  Losers: {len(losers)}")
print(f"  Winner median net return: {winners['net_return'].median():.4f}")
print(f"  Loser  median net return: {losers['net_return'].median():.4f}")
print(f"  Winner median hold: {winners['bars_held'].median():.0f} bars")
print(f"  Loser  median hold: {losers['bars_held'].median():.0f} bars")

# Tbl04
tbl04_rows = []
for grp_name, grp_df in [("winner", winners), ("loser", losers)]:
    tbl04_rows.append({
        "group": grp_name,
        "count": len(grp_df),
        "median_net_return": round(grp_df["net_return"].median(), 6),
        "mean_net_return": round(grp_df["net_return"].mean(), 6),
        "median_gross_return": round(grp_df["gross_return"].median(), 6),
        "median_bars_held": round(grp_df["bars_held"].median(), 1),
        "mean_bars_held": round(grp_df["bars_held"].mean(), 1),
        "median_hold_hours": round(grp_df["bars_held"].median() * 4, 0),
        "trail_stop_pct": round((grp_df["exit_reason"] == "trail_stop").mean(), 4),
        "trend_exit_pct": round((grp_df["exit_reason"] == "trend_exit").mean(), 4),
    })
tbl04 = pd.DataFrame(tbl04_rows)
tbl04.to_csv(TBL / "Tbl04_trade_groups.csv", index=False)
print(f"  Written: tables/Tbl04_trade_groups.csv")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: VOLUME / TBR PROFILES AROUND ENTRY
# ═══════════════════════════════════════════════════════════════════════
print("\n[2] Volume / TBR profiles around entry...")

PRE = 20   # bars before entry
POST = 10  # bars after entry
offsets = np.arange(-PRE, POST + 1)  # -20 to +10


def extract_profiles(trade_rows, array, pre=PRE, post=POST):
    """Extract array values around entry for each trade. Returns (n_trades, n_offsets)."""
    n_off = pre + post + 1
    profiles = []
    for _, row in trade_rows.iterrows():
        eb = row["entry_bar"]
        start = eb - pre
        end = eb + post + 1
        if start < 0 or end > len(array):
            continue
        profiles.append(array[start:end])
    if not profiles:
        return np.full((0, n_off), np.nan)
    return np.array(profiles)


def extract_normalized_vol_profiles(trade_rows, vol_array, pre=PRE, post=POST):
    """Volume normalized by median of bars [-20, -1] for each trade."""
    n_off = pre + post + 1
    profiles = []
    for _, row in trade_rows.iterrows():
        eb = row["entry_bar"]
        start = eb - pre
        end = eb + post + 1
        if start < 0 or end > len(vol_array):
            continue
        window = vol_array[start:end].copy()
        # Normalize by pre-entry median (offsets -20 to -1)
        pre_median = np.median(window[:pre])
        if pre_median > 0:
            window = window / pre_median
        else:
            continue
        profiles.append(window)
    if not profiles:
        return np.full((0, n_off), np.nan)
    return np.array(profiles)


def plot_profile(win_profiles, los_profiles, offsets, ylabel, title, figname,
                 hline=None, ylim=None):
    """Plot median + IQR shaded for winners and losers."""
    fig, ax = plt.subplots(figsize=(12, 5))

    for profiles, label, color in [
        (win_profiles, f"Winners (n={len(win_profiles)})", "forestgreen"),
        (los_profiles, f"Losers (n={len(los_profiles)})", "firebrick"),
    ]:
        if len(profiles) == 0:
            continue
        med = np.median(profiles, axis=0)
        q25 = np.percentile(profiles, 25, axis=0)
        q75 = np.percentile(profiles, 75, axis=0)
        ax.plot(offsets, med, color=color, linewidth=1.5, label=label)
        ax.fill_between(offsets, q25, q75, color=color, alpha=0.15)

    ax.axvline(0, color="black", linewidth=1.0, linestyle="--", alpha=0.6, label="entry bar")
    if hline is not None:
        ax.axhline(hline, color="gray", linewidth=0.7, linestyle=":", alpha=0.5)
    if ylim:
        ax.set_ylim(ylim)
    ax.set_xlabel("Bars relative to entry (H4)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.set_xticks(offsets[::5])
    plt.tight_layout()
    fig.savefig(FIG / figname, dpi=150)
    plt.close(fig)
    print(f"  Written: figures/{figname}")


# Fig09: Normalized volume profile
win_vol = extract_normalized_vol_profiles(winners, volume_h4)
los_vol = extract_normalized_vol_profiles(losers, volume_h4)
plot_profile(win_vol, los_vol, offsets,
             ylabel="Volume / pre-entry median",
             title="Fig09: Normalized Volume Profile Around Entry",
             figname="Fig09_volume_profile.png",
             hline=1.0)

# Fig10: Taker buy ratio profile
win_tbr = extract_profiles(winners, tbr_h4)
los_tbr = extract_profiles(losers, tbr_h4)
plot_profile(win_tbr, los_tbr, offsets,
             ylabel="Taker Buy Ratio",
             title="Fig10: Taker Buy Ratio Profile Around Entry",
             figname="Fig10_tbr_profile.png",
             hline=0.5)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: VOLATILITY PROFILE AROUND ENTRY
# ═══════════════════════════════════════════════════════════════════════
print("\n[3] Volatility profile around entry...")

# Fig11: ATR(20)/price profile
win_atr = extract_profiles(winners, atr20_pct)
los_atr = extract_profiles(losers, atr20_pct)
plot_profile(win_atr, los_atr, offsets,
             ylabel="ATR(20) / Price",
             title="Fig11: Volatility Profile Around Entry (ATR(20)/Price)",
             figname="Fig11_volatility_profile.png")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: STATISTICAL SEPARATION AT ENTRY BAR
# ═══════════════════════════════════════════════════════════════════════
print("\n[4] Statistical separation at entry bar...")

# Compute features at entry bar for each trade
features_at_entry = []
for _, row in tdf.iterrows():
    eb = int(row["entry_bar"])
    f = {"trade_id": row["trade_id"], "group": row["group"]}

    # 1. TBR single bar
    f["tbr_entry"] = tbr_h4[eb]

    # 2. Mean TBR 5 bars before
    if eb >= 5:
        f["tbr_mean5"] = np.mean(tbr_h4[eb - 5:eb])
    else:
        f["tbr_mean5"] = np.nan

    # 3. Mean TBR 10 bars before
    if eb >= 10:
        f["tbr_mean10"] = np.mean(tbr_h4[eb - 10:eb])
    else:
        f["tbr_mean10"] = np.nan

    # 4. Volume / rolling median volume(20)
    if not np.isnan(vol_median20[eb]) and vol_median20[eb] > 0:
        f["vol_rel"] = volume_h4[eb] / vol_median20[eb]
    else:
        f["vol_rel"] = np.nan

    # 5. ATR(20) / price
    f["atr20_pct"] = atr20_pct[eb] if not np.isnan(atr20_pct[eb]) else np.nan

    features_at_entry.append(f)

feat_df = pd.DataFrame(features_at_entry)

# Mann-Whitney tests
feature_cols = [
    ("tbr_entry", "taker_buy_ratio (single bar)"),
    ("tbr_mean5", "mean TBR 5 bars before entry"),
    ("tbr_mean10", "mean TBR 10 bars before entry"),
    ("vol_rel", "volume / rolling_median_volume(20)"),
    ("atr20_pct", "ATR(20) / price"),
]

test_results = []
for col, desc in feature_cols:
    win_vals = feat_df[feat_df["group"] == "winner"][col].dropna().values
    los_vals = feat_df[feat_df["group"] == "loser"][col].dropna().values

    if len(win_vals) < 5 or len(los_vals) < 5:
        test_results.append({
            "feature": desc, "column": col,
            "n_winners": len(win_vals), "n_losers": len(los_vals),
            "median_winners": np.nan, "median_losers": np.nan,
            "U": np.nan, "p_value": np.nan, "rank_biserial": np.nan,
            "direction": "insufficient_data",
        })
        continue

    u_stat, p_val = stats.mannwhitneyu(win_vals, los_vals, alternative="two-sided")
    n1, n2 = len(win_vals), len(los_vals)
    r_rb = 1.0 - (2.0 * u_stat) / (n1 * n2)

    med_w = np.median(win_vals)
    med_l = np.median(los_vals)
    direction = "winners_higher" if med_w > med_l else "losers_higher" if med_l > med_w else "equal"

    test_results.append({
        "feature": desc,
        "column": col,
        "n_winners": n1,
        "n_losers": n2,
        "median_winners": round(med_w, 6),
        "median_losers": round(med_l, 6),
        "U": u_stat,
        "p_value": p_val,
        "rank_biserial": round(r_rb, 4),
        "direction": direction,
    })

tbl05 = pd.DataFrame(test_results)
tbl05.to_csv(TBL / "Tbl05_entry_separation.csv", index=False)
print(f"  Written: tables/Tbl05_entry_separation.csv")
print(tbl05[["feature", "median_winners", "median_losers", "p_value", "rank_biserial", "direction"]].to_string(index=False))


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: VDO AT ENTRY
# ═══════════════════════════════════════════════════════════════════════
print("\n[5] VDO at entry...")

win_vdo = tdf[tdf["group"] == "winner"]["entry_vdo"].values
los_vdo = tdf[tdf["group"] == "loser"]["entry_vdo"].values

# Fig12: Histogram winners vs losers
fig, ax = plt.subplots(figsize=(10, 5))
bins = np.linspace(
    min(tdf["entry_vdo"].min(), -0.1),
    max(tdf["entry_vdo"].max(), 0.3),
    40,
)
ax.hist(win_vdo, bins=bins, alpha=0.6, color="forestgreen", density=True,
        label=f"Winners (n={len(win_vdo)})")
ax.hist(los_vdo, bins=bins, alpha=0.6, color="firebrick", density=True,
        label=f"Losers (n={len(los_vdo)})")
ax.axvline(0.0, color="black", linewidth=0.8, linestyle="--", alpha=0.5, label="VDO=0")
ax.set_xlabel("VDO at entry")
ax.set_ylabel("Density")
ax.set_title("Fig12: VDO at Entry — Winners vs Losers")
ax.legend()
plt.tight_layout()
fig.savefig(FIG / "Fig12_vdo_histogram.png", dpi=150)
plt.close(fig)
print("  Written: figures/Fig12_vdo_histogram.png")

# Fig13: Scatter VDO vs trade return
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(tdf[tdf["group"] == "winner"]["entry_vdo"],
           tdf[tdf["group"] == "winner"]["net_return"],
           alpha=0.5, s=15, color="forestgreen", label="Winners")
ax.scatter(tdf[tdf["group"] == "loser"]["entry_vdo"],
           tdf[tdf["group"] == "loser"]["net_return"],
           alpha=0.5, s=15, color="firebrick", label="Losers")
ax.axhline(0, color="gray", linewidth=0.5)
ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")
# Spearman correlation
rho, p = stats.spearmanr(tdf["entry_vdo"].values, tdf["net_return"].values)
ax.set_xlabel("VDO at entry")
ax.set_ylabel("Net trade return")
ax.set_title(f"Fig13: VDO at Entry vs Net Return (Spearman r={rho:.4f}, p={p:.4f})")
ax.legend()
plt.tight_layout()
fig.savefig(FIG / "Fig13_vdo_scatter.png", dpi=150)
plt.close(fig)
print("  Written: figures/Fig13_vdo_scatter.png")

# Mann-Whitney test on VDO
u_vdo, p_vdo = stats.mannwhitneyu(win_vdo, los_vdo, alternative="two-sided")
r_rb_vdo = 1.0 - (2.0 * u_vdo) / (len(win_vdo) * len(los_vdo))
rho_vdo, p_rho_vdo = stats.spearmanr(tdf["entry_vdo"].values, tdf["net_return"].values)

tbl06 = pd.DataFrame([{
    "metric": "VDO at entry",
    "n_winners": len(win_vdo),
    "n_losers": len(los_vdo),
    "median_winners": round(np.median(win_vdo), 6),
    "median_losers": round(np.median(los_vdo), 6),
    "mean_winners": round(np.mean(win_vdo), 6),
    "mean_losers": round(np.mean(los_vdo), 6),
    "U_statistic": u_vdo,
    "MW_p_value": p_vdo,
    "rank_biserial": round(r_rb_vdo, 4),
    "spearman_rho_vs_return": round(rho_vdo, 4),
    "spearman_p_vs_return": p_rho_vdo,
    "direction": "winners_higher" if np.median(win_vdo) > np.median(los_vdo) else "losers_higher",
}])
tbl06.to_csv(TBL / "Tbl06_vdo_entry_stats.csv", index=False)
print(f"  Written: tables/Tbl06_vdo_entry_stats.csv")
print(f"  VDO MW: U={u_vdo:.0f}, p={p_vdo:.4f}, r_rb={r_rb_vdo:.4f}")
print(f"  VDO vs return: Spearman r={rho_vdo:.4f}, p={p_rho_vdo:.4f}")
print(f"  Median VDO — winners: {np.median(win_vdo):.4f}, losers: {np.median(los_vdo):.4f}")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: FALSE ENTRIES (5 WORST LOSERS)
# ═══════════════════════════════════════════════════════════════════════
print("\n[6] False entries — 5 worst losers...")

CONTEXT = 20  # bars before and after entry
worst5 = tdf.nsmallest(5, "net_return")

for rank, (idx, row) in enumerate(worst5.iterrows()):
    fig_label = chr(ord('a') + rank)  # a, b, c, d, e
    eb = int(row["entry_bar"])
    start = max(0, eb - CONTEXT)
    end = min(n_h4, eb + CONTEXT + 1)
    rel_offsets = np.arange(start - eb, end - eb)

    price_window = close_h4[start:end]
    vol_window = volume_h4[start:end]
    tbr_window = tbr_h4[start:end]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9), sharex=True,
                                          gridspec_kw={"height_ratios": [2, 1, 1]})

    # Price
    ax1.plot(rel_offsets, price_window, color="black", linewidth=1.2)
    ax1.axvline(0, color="red", linewidth=1.5, linestyle="--", alpha=0.7, label="entry")
    exit_rel = int(row["exit_bar"]) - eb
    if start <= row["exit_bar"] < end:
        ax1.axvline(exit_rel, color="blue", linewidth=1.5, linestyle="--", alpha=0.7, label="exit")
    ax1.set_ylabel("Price (USDT)")
    ax1.set_title(f"Fig14{fig_label}: Worst Loser #{rank+1} — "
                  f"Return={row['net_return']:.2%}, "
                  f"Entry={row['entry_dt'][:10]}, "
                  f"Hold={row['bars_held']} bars, "
                  f"Exit={row['exit_reason']}")
    ax1.legend(fontsize=8)

    # Volume
    ax2.bar(rel_offsets, vol_window, color="steelblue", alpha=0.7, width=0.8)
    ax2.axvline(0, color="red", linewidth=1.0, linestyle="--", alpha=0.5)
    if start <= row["exit_bar"] < end:
        ax2.axvline(exit_rel, color="blue", linewidth=1.0, linestyle="--", alpha=0.5)
    ax2.set_ylabel("Volume (BTC)")

    # TBR
    ax3.plot(rel_offsets, tbr_window, color="darkorange", linewidth=1.0)
    ax3.axhline(0.5, color="gray", linewidth=0.7, linestyle=":")
    ax3.axvline(0, color="red", linewidth=1.0, linestyle="--", alpha=0.5)
    if start <= row["exit_bar"] < end:
        ax3.axvline(exit_rel, color="blue", linewidth=1.0, linestyle="--", alpha=0.5)
    ax3.set_ylabel("Taker Buy Ratio")
    ax3.set_xlabel("Bars relative to entry (H4)")

    plt.tight_layout()
    figname = f"Fig14{fig_label}_worst_loser_{rank+1}.png"
    fig.savefig(FIG / figname, dpi=150)
    plt.close(fig)
    print(f"  Written: figures/{figname}")
    print(f"    Trade #{int(row['trade_id'])}: entry={row['entry_dt'][:10]}, "
          f"net_ret={row['net_return']:.4f}, hold={row['bars_held']} bars, "
          f"reason={row['exit_reason']}")


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("Phase 2 script complete.")
print(f"  Trades: {n_trades}")
print(f"  Winners: {len(winners)} | Losers: {len(losers)}")
print(f"  Figures: Fig09..Fig14e")
print(f"  Tables: trade_list.csv, trade_repro_check.csv, Tbl04..Tbl06")
print("=" * 70)
