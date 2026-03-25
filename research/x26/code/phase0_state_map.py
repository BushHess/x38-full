"""Phase 0: VTREND State Map — Map in-position vs flat periods.

Produces:
- Fig01: VTREND position state over time (H4 bars)
- Fig02: Distribution of flat-period durations
- Tbl01: Summary statistics of flat vs active periods
- Tbl02: Flat-period return characteristics
"""

import sys
sys.path.insert(0, "/var/www/trading-bots/btc-spot-dev")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path("/var/www/trading-bots/btc-spot-dev/research/beyond_trend_lab")
FIG = OUT / "figures"
TBL = OUT / "tables"

# ── Load data ──────────────────────────────────────────────────────────────
DATA = "/var/www/trading-bots/btc-spot/data/bars_btcusdt_h1_4h_1d.csv"
raw = pd.read_csv(DATA)

h4 = raw[raw["interval"] == "4h"].copy().reset_index(drop=True)
d1 = raw[raw["interval"] == "1d"].copy().reset_index(drop=True)

h4["dt"] = pd.to_datetime(h4["open_time"], unit="ms")
d1["dt"] = pd.to_datetime(d1["open_time"], unit="ms")

# ── Compute indicators (replicating VTREND E5+EMA21D1) ────────────────────
def ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty(len(series))
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out

def robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20):
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr

def vdo(close, high, low, volume, taker_buy, fast=12, slow=28):
    taker_sell = volume - taker_buy
    vdr = np.zeros(len(close))
    mask = volume > 0
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    return ema(vdr, fast) - ema(vdr, slow)

# H4 indicators
cl = h4["close"].values
hi = h4["high"].values
lo = h4["low"].values
vol = h4["volume"].values
tbuy = h4["taker_buy_base_vol"].values

slow_p = 120
fast_p = 30
ema_fast = ema(cl, fast_p)
ema_slow = ema(cl, slow_p)
ratr = robust_atr(hi, lo, cl)
vdo_arr = vdo(cl, hi, lo, vol, tbuy)

# D1 regime filter
d1_close = d1["close"].values
d1_ema21 = ema(d1_close, 21)
d1_regime = d1_close > d1_ema21
d1_ct = d1["close_time"].values

# Map D1 regime to H4
h4_regime = np.zeros(len(h4), dtype=bool)
d1_idx = 0
n_d1 = len(d1)
for i in range(len(h4)):
    h4_ct = h4["close_time"].values[i]
    while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct:
        d1_idx += 1
    if d1_ct[d1_idx] < h4_ct:
        h4_regime[i] = d1_regime[d1_idx]

# ── Simulate VTREND positions ─────────────────────────────────────────────
in_pos = np.zeros(len(h4), dtype=bool)
trades = []
current_trade_start = None
peak_price = 0.0
is_in = False

for i in range(1, len(h4)):
    if np.isnan(ratr[i]) or np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
        continue

    trend_up = ema_fast[i] > ema_slow[i]
    trend_down = ema_fast[i] < ema_slow[i]

    if not is_in:
        if trend_up and vdo_arr[i] > 0.0 and h4_regime[i]:
            is_in = True
            peak_price = cl[i]
            current_trade_start = i
            in_pos[i] = True
    else:
        peak_price = max(peak_price, cl[i])
        trail_stop = peak_price - 3.0 * ratr[i]
        if cl[i] < trail_stop or trend_down:
            reason = "trail" if cl[i] < trail_stop else "ema_cross"
            trades.append({
                "entry_bar": current_trade_start,
                "exit_bar": i,
                "entry_price": cl[current_trade_start],
                "exit_price": cl[i],
                "entry_dt": h4["dt"].iloc[current_trade_start],
                "exit_dt": h4["dt"].iloc[i],
                "ret": cl[i] / cl[current_trade_start] - 1,
                "duration_bars": i - current_trade_start,
                "exit_reason": reason,
            })
            is_in = False
            peak_price = 0.0
        else:
            in_pos[i] = True

# If still in position at end, close it
if is_in and current_trade_start is not None:
    i = len(h4) - 1
    trades.append({
        "entry_bar": current_trade_start,
        "exit_bar": i,
        "entry_price": cl[current_trade_start],
        "exit_price": cl[i],
        "entry_dt": h4["dt"].iloc[current_trade_start],
        "exit_dt": h4["dt"].iloc[i],
        "ret": cl[i] / cl[current_trade_start] - 1,
        "duration_bars": i - current_trade_start,
        "exit_reason": "open",
    })
    in_pos[i] = True

trades_df = pd.DataFrame(trades)
print(f"Total trades: {len(trades_df)}")
print(f"Bars in position: {in_pos.sum()} / {len(in_pos)} ({in_pos.sum()/len(in_pos)*100:.1f}%)")

# ── Identify flat (out-of-position) periods ───────────────────────────────
flat_periods = []
flat_start = None
for i in range(len(in_pos)):
    if not in_pos[i]:
        if flat_start is None:
            flat_start = i
    else:
        if flat_start is not None:
            flat_periods.append({
                "start_bar": flat_start,
                "end_bar": i - 1,
                "start_dt": h4["dt"].iloc[flat_start],
                "end_dt": h4["dt"].iloc[i - 1],
                "duration_bars": i - flat_start,
                "duration_days": (h4["dt"].iloc[i - 1] - h4["dt"].iloc[flat_start]).days,
                "start_price": cl[flat_start],
                "end_price": cl[i - 1],
                "ret": cl[i - 1] / cl[flat_start] - 1,
                "high": hi[flat_start:i].max(),
                "low": lo[flat_start:i].min(),
                "range_pct": (hi[flat_start:i].max() - lo[flat_start:i].min()) / cl[flat_start],
            })
            flat_start = None
# Last flat period
if flat_start is not None:
    i = len(in_pos)
    flat_periods.append({
        "start_bar": flat_start,
        "end_bar": i - 1,
        "start_dt": h4["dt"].iloc[flat_start],
        "end_dt": h4["dt"].iloc[min(i - 1, len(h4) - 1)],
        "duration_bars": i - flat_start,
        "duration_days": (h4["dt"].iloc[min(i - 1, len(h4) - 1)] - h4["dt"].iloc[flat_start]).days,
        "start_price": cl[flat_start],
        "end_price": cl[min(i - 1, len(h4) - 1)],
        "ret": cl[min(i - 1, len(h4) - 1)] / cl[flat_start] - 1,
        "high": hi[flat_start:i].max(),
        "low": lo[flat_start:i].min(),
        "range_pct": (hi[flat_start:i].max() - lo[flat_start:i].min()) / cl[flat_start],
    })

flat_df = pd.DataFrame(flat_periods)
print(f"\nFlat periods: {len(flat_df)}")
print(f"Flat bars: {flat_df['duration_bars'].sum()} ({flat_df['duration_bars'].sum()/len(in_pos)*100:.1f}%)")
print(f"Mean flat duration: {flat_df['duration_bars'].mean():.1f} bars ({flat_df['duration_bars'].mean()*4/24:.1f} days)")
print(f"Median flat duration: {flat_df['duration_bars'].median():.1f} bars ({flat_df['duration_bars'].median()*4/24:.1f} days)")
print(f"Max flat duration: {flat_df['duration_bars'].max()} bars ({flat_df['duration_bars'].max()*4/24:.1f} days)")

# ── Flat period return characteristics ────────────────────────────────────
print("\n=== Flat Period Return Characteristics ===")
print(f"Mean return during flat: {flat_df['ret'].mean()*100:.2f}%")
print(f"Median return during flat: {flat_df['ret'].median()*100:.2f}%")
print(f"Std return during flat: {flat_df['ret'].std()*100:.2f}%")
print(f"% positive return: {(flat_df['ret'] > 0).mean()*100:.1f}%")
print(f"Mean range (H-L)/entry: {flat_df['range_pct'].mean()*100:.2f}%")

# Classify flat periods by duration
short = flat_df[flat_df["duration_bars"] <= 6]  # <= 1 day
medium = flat_df[(flat_df["duration_bars"] > 6) & (flat_df["duration_bars"] <= 42)]  # 1-7 days
long = flat_df[flat_df["duration_bars"] > 42]  # > 7 days

print(f"\nShort (<=1d): {len(short)} periods, mean ret {short['ret'].mean()*100:.2f}%")
print(f"Medium (1-7d): {len(medium)} periods, mean ret {medium['ret'].mean()*100:.2f}%")
print(f"Long (>7d): {len(long)} periods, mean ret {long['ret'].mean()*100:.2f}%")

# ── Compute bar-level returns during flat periods ─────────────────────────
h4_ret = np.diff(np.log(cl))  # log returns
flat_bar_rets = h4_ret[~in_pos[1:]]  # flat period returns
active_bar_rets = h4_ret[in_pos[1:]]  # in-position returns

print(f"\n=== Bar-Level Return Comparison ===")
print(f"Flat bars mean ret: {flat_bar_rets.mean()*10000:.2f} bps/bar")
print(f"Active bars mean ret: {active_bar_rets.mean()*10000:.2f} bps/bar")
print(f"Flat bars std: {flat_bar_rets.std()*10000:.2f} bps/bar")
print(f"Active bars std: {active_bar_rets.std()*10000:.2f} bps/bar")
print(f"Flat bars Sharpe (per bar): {flat_bar_rets.mean()/flat_bar_rets.std():.4f}")
print(f"Active bars Sharpe (per bar): {active_bar_rets.mean()/active_bar_rets.std():.4f}")

# Annualized (6 bars/day × 365 days/year = 2190 bars/year)
bars_per_year = 2190
flat_ann_sharpe = flat_bar_rets.mean() / flat_bar_rets.std() * np.sqrt(bars_per_year)
active_ann_sharpe = active_bar_rets.mean() / active_bar_rets.std() * np.sqrt(bars_per_year)
print(f"Flat annualized Sharpe: {flat_ann_sharpe:.3f}")
print(f"Active annualized Sharpe: {active_ann_sharpe:.3f}")

# ── Autocorrelation in flat period returns ────────────────────────────────
# Check if flat period returns have structure
print(f"\n=== Flat Bar Return Autocorrelation ===")
for lag in [1, 2, 3, 6, 12, 24]:
    if len(flat_bar_rets) > lag:
        ac = np.corrcoef(flat_bar_rets[lag:], flat_bar_rets[:-lag])[0, 1]
        print(f"  Lag {lag:2d} ({lag*4:3d}h): {ac:.4f}")

# ── Fig01: Position state over time ───────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(16, 10), height_ratios=[3, 1, 1])

ax = axes[0]
ax.plot(h4["dt"], cl, color="gray", linewidth=0.5, alpha=0.7)
# Color in-position green, flat red
for _, t in trades_df.iterrows():
    ax.axvspan(t["entry_dt"], t["exit_dt"], alpha=0.15, color="green")
ax.set_ylabel("BTC Price (log)")
ax.set_yscale("log")
ax.set_title("Fig01: VTREND E5+EMA21D1 Position State Map")
ax.legend(["BTC Price", "In Position"], loc="upper left")

ax = axes[1]
ax.fill_between(h4["dt"], in_pos.astype(int), alpha=0.6, color="green", label="In Position")
ax.fill_between(h4["dt"], (~in_pos).astype(int), alpha=0.3, color="red", label="Flat")
ax.set_ylabel("State")
ax.set_yticks([0, 1])
ax.set_yticklabels(["Flat", "Active"])
ax.legend(loc="upper right")

ax = axes[2]
# Cumulative returns: flat vs active
flat_cum = np.zeros(len(h4_ret))
active_cum = np.zeros(len(h4_ret))
for i in range(len(h4_ret)):
    flat_cum[i] = flat_cum[i-1] + (h4_ret[i] if not in_pos[i+1] else 0) if i > 0 else (h4_ret[i] if not in_pos[i+1] else 0)
    active_cum[i] = active_cum[i-1] + (h4_ret[i] if in_pos[i+1] else 0) if i > 0 else (h4_ret[i] if in_pos[i+1] else 0)

ax.plot(h4["dt"].iloc[1:], flat_cum, color="red", linewidth=1, label="Flat cumret")
ax.plot(h4["dt"].iloc[1:], active_cum, color="green", linewidth=1, label="Active cumret")
ax.set_ylabel("Cumulative Log Return")
ax.legend(loc="upper left")
ax.set_xlabel("Date")

plt.tight_layout()
plt.savefig(FIG / "fig01_position_state_map.png", dpi=150)
plt.close()
print(f"\nSaved: {FIG / 'fig01_position_state_map.png'}")

# ── Fig02: Distribution of flat-period durations ─────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

ax = axes[0]
ax.hist(flat_df["duration_bars"] * 4 / 24, bins=50, color="steelblue", edgecolor="white", alpha=0.8)
ax.set_xlabel("Flat Period Duration (days)")
ax.set_ylabel("Count")
ax.set_title("Fig02a: Flat Period Duration Distribution")
ax.axvline(flat_df["duration_bars"].median() * 4 / 24, color="red", linestyle="--", label=f"Median={flat_df['duration_bars'].median()*4/24:.1f}d")
ax.axvline(flat_df["duration_bars"].mean() * 4 / 24, color="orange", linestyle="--", label=f"Mean={flat_df['duration_bars'].mean()*4/24:.1f}d")
ax.legend()

ax = axes[1]
ax.scatter(flat_df["duration_bars"] * 4 / 24, flat_df["ret"] * 100, alpha=0.4, s=15, c="steelblue")
ax.axhline(0, color="gray", linestyle="--", linewidth=0.5)
ax.set_xlabel("Flat Period Duration (days)")
ax.set_ylabel("Return (%)")
ax.set_title("Fig02b: Flat Period Return vs Duration")

plt.tight_layout()
plt.savefig(FIG / "fig02_flat_duration_dist.png", dpi=150)
plt.close()
print(f"Saved: {FIG / 'fig02_flat_duration_dist.png'}")

# ── Tbl01: Save summary statistics ───────────────────────────────────────
summary = {
    "total_h4_bars": len(h4),
    "active_bars": int(in_pos.sum()),
    "flat_bars": int((~in_pos).sum()),
    "exposure_pct": round(in_pos.sum() / len(in_pos) * 100, 1),
    "total_trades": len(trades_df),
    "total_flat_periods": len(flat_df),
    "mean_flat_bars": round(flat_df["duration_bars"].mean(), 1),
    "median_flat_bars": round(float(flat_df["duration_bars"].median()), 1),
    "max_flat_bars": int(flat_df["duration_bars"].max()),
    "mean_flat_days": round(flat_df["duration_bars"].mean() * 4 / 24, 1),
    "median_flat_days": round(float(flat_df["duration_bars"].median()) * 4 / 24, 1),
    "max_flat_days": round(flat_df["duration_bars"].max() * 4 / 24, 1),
    "flat_mean_ret_pct": round(flat_df["ret"].mean() * 100, 2),
    "flat_median_ret_pct": round(float(flat_df["ret"].median()) * 100, 2),
    "flat_pct_positive": round((flat_df["ret"] > 0).mean() * 100, 1),
    "flat_mean_range_pct": round(flat_df["range_pct"].mean() * 100, 2),
    "flat_ann_sharpe": round(flat_ann_sharpe, 3),
    "active_ann_sharpe": round(active_ann_sharpe, 3),
}

pd.Series(summary).to_csv(TBL / "tbl01_summary_stats.csv", header=["value"])
print(f"\nSaved: {TBL / 'tbl01_summary_stats.csv'}")

# ── Tbl02: Flat period details (top 20 longest) ──────────────────────────
flat_top20 = flat_df.nlargest(20, "duration_bars")[
    ["start_dt", "end_dt", "duration_bars", "duration_days", "start_price", "end_price", "ret", "range_pct"]
].copy()
flat_top20["ret_pct"] = (flat_top20["ret"] * 100).round(2)
flat_top20["range_pct"] = (flat_top20["range_pct"] * 100).round(2)
flat_top20.to_csv(TBL / "tbl02_top20_flat_periods.csv", index=False)
print(f"Saved: {TBL / 'tbl02_top20_flat_periods.csv'}")

# ── Tbl03: Flat period return by regime (year) ────────────────────────────
flat_df["year"] = flat_df["start_dt"].dt.year
yearly = flat_df.groupby("year").agg(
    n_periods=("ret", "count"),
    total_bars=("duration_bars", "sum"),
    mean_ret=("ret", "mean"),
    median_ret=("ret", lambda x: float(x.median())),
    mean_range=("range_pct", "mean"),
).round(4)
yearly.to_csv(TBL / "tbl03_flat_by_year.csv")
print(f"Saved: {TBL / 'tbl03_flat_by_year.csv'}")

# ── Save trades and flat periods for later phases ─────────────────────────
trades_df.to_csv(TBL / "trades.csv", index=False)
flat_df.to_csv(TBL / "flat_periods.csv", index=False)
np.save(TBL / "in_position.npy", in_pos)
print(f"Saved: trades.csv, flat_periods.csv, in_position.npy")

print("\n=== DONE ===")
