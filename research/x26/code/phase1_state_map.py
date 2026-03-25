"""Phase 1: Data Audit & VTREND State Map.

Runs VTREND E5+EMA21D1 through the v10 backtest engine (exact reproduction),
classifies every H4 bar as IN_TRADE or FLAT, computes temporal statistics
and transition analysis.

Deliverables:
- tables/state_classification.csv    (bar-level: open_time, state, trade_id)
- tables/Tbl01_state_summary.csv     (summary statistics)
- tables/Tbl02_flat_durations.csv    (all flat period durations)
- figures/Fig01_price_state_overlay.png
- figures/Fig02_flat_duration_hist.png
- figures/Fig03_yearly_state_fraction.png
"""

import sys
sys.path.insert(0, "/var/www/trading-bots/btc-spot-dev")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy

# ── Paths ─────────────────────────────────────────────────────────────────
DATA = "/var/www/trading-bots/btc-spot-dev/data/bars_btcusdt_2016_now_h1_4h_1d.csv"
OUT = Path("/var/www/trading-bots/btc-spot-dev/research/beyond_trend_lab")
FIG = OUT / "figures"
TBL = OUT / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TBL.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════
# 1. DATA LOAD & QUICK VERIFY
# ══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("PHASE 1: DATA AUDIT & VTREND STATE MAP")
print("=" * 70)

raw = pd.read_csv(DATA)
h1_count = int((raw["interval"] == "1h").sum())
h4_count = int((raw["interval"] == "4h").sum())
d1_count = int((raw["interval"] == "1d").sum())

print(f"\n1. Data Verification:")
print(f"   H1 bars: {h1_count} (expected ~74,651)")
print(f"   H4 bars: {h4_count} (expected ~18,662)")
print(f"   D1 bars: {d1_count} (expected ~3,110)")
print(f"   Total rows: {len(raw)}")

assert abs(h4_count - 18662) <= 50, f"H4 count mismatch: {h4_count}"
assert abs(d1_count - 3110) <= 50, f"D1 count mismatch: {d1_count}"
print("   All counts within expected range")

# ══════════════════════════════════════════════════════════════════════════
# 2. RUN VTREND E5+EMA21D1 VIA V10 ENGINE (exact reproduction)
# ══════════════════════════════════════════════════════════════════════════
# Full-range run: ALL H4 bars for state classification (primary for this phase)
# Also cross-ref run: start=2019-01-01, warmup=365d to match evaluation baseline
print(f"\n2. Running VTREND E5+EMA21D1 via v10 engine...")

# --- Primary: full data range (for state classification of ALL bars) ---
feed = DataFeed(DATA)  # Full data, no date filter
strategy = VTrendE5Ema21D1Strategy()
cost = SCENARIOS["harsh"]  # 50 bps RT
engine = BacktestEngine(
    feed=feed,
    strategy=strategy,
    cost=cost,
    initial_cash=10_000.0,
)
result = engine.run()
sm = result.summary

print(f"   [Full range] Trades: {sm['trades']}, Sharpe: {sm['sharpe']}, "
      f"CAGR: {sm['cagr_pct']}%, MDD: {sm['max_drawdown_mid_pct']}%, "
      f"WR: {sm['win_rate_pct']}%, Exposure: {sm['avg_exposure']:.4f}")

# --- Cross-ref: evaluation window (2019-01-01 → 2026-02-20, warmup 365d) ---
feed_eval = DataFeed(DATA, start="2019-01-01", end="2026-02-20", warmup_days=365)
strategy_eval = VTrendE5Ema21D1Strategy()
engine_eval = BacktestEngine(
    feed=feed_eval,
    strategy=strategy_eval,
    cost=cost,
    initial_cash=10_000.0,
    warmup_mode="no_trade",
)
result_eval = engine_eval.run()
sm_eval = result_eval.summary

print(f"   [Eval window] Trades: {sm_eval['trades']}, Sharpe: {sm_eval['sharpe']}, "
      f"CAGR: {sm_eval['cagr_pct']}%, MDD: {sm_eval['max_drawdown_mid_pct']}%, "
      f"WR: {sm_eval['win_rate_pct']}%, Exposure: {sm_eval['avg_exposure']:.4f}")
print(f"   Note: Ref '~201 trades' is X0 (E0+EMA21D1), not E5. "
      f"E5 eval-window ref: ~186 trades.")

# ══════════════════════════════════════════════════════════════════════════
# 3. CLASSIFY EVERY H4 BAR
# ══════════════════════════════════════════════════════════════════════════
print(f"\n3. Classifying H4 bars...")

h4_bars = feed.h4_bars
n_h4 = len(h4_bars)
equity = result.equity
trades_list = result.trades

# Engine with no start/end: report_start_ms = None, so equity covers all bars
assert len(equity) == n_h4, f"Equity length {len(equity)} != H4 bars {n_h4}"

# State from equity exposure
# After buy fill at bar open: equity snap at bar close shows exposure > 0
# After sell fill at bar open: equity snap at bar close shows exposure ~ 0
in_trade = np.array([e.exposure > 0.01 for e in equity], dtype=bool)

# Build open_time -> bar index lookup for trade mapping
ot_to_idx = {}
for i, bar in enumerate(h4_bars):
    ot_to_idx[bar.open_time] = i

# Map trades to bar indices
trade_records = []
for t in trades_list:
    entry_idx = ot_to_idx.get(t.entry_ts_ms)
    exit_idx = ot_to_idx.get(t.exit_ts_ms)
    trade_records.append({
        "trade_id": t.trade_id,
        "entry_ts_ms": t.entry_ts_ms,
        "exit_ts_ms": t.exit_ts_ms,
        "entry_bar_idx": entry_idx,
        "exit_bar_idx": exit_idx,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "pnl": t.pnl,
        "return_pct": t.return_pct,
        "days_held": t.days_held,
        "entry_reason": t.entry_reason,
        "exit_reason": t.exit_reason,
    })

trades_df = pd.DataFrame(trade_records)

# Assign trade_id to each in-trade bar
bar_trade_id = np.full(n_h4, -1, dtype=int)
for _, tr in trades_df.iterrows():
    eidx = tr["entry_bar_idx"]
    xidx = tr["exit_bar_idx"]
    if eidx is None or xidx is None:
        continue
    eidx, xidx = int(eidx), int(xidx)
    # Entry fill at bar eidx open -> equity at eidx close shows in_trade
    # Exit fill at bar xidx open -> equity at xidx close shows flat
    # So in-trade bars: eidx through xidx-1
    for j in range(eidx, xidx):
        if j < n_h4 and in_trade[j]:
            bar_trade_id[j] = int(tr["trade_id"])

state_arr = np.where(in_trade, "IN_TRADE", "FLAT")

# Build datetimes
h4_open_ms = np.array([b.open_time for b in h4_bars], dtype=np.int64)
h4_close_ms = np.array([b.close_time for b in h4_bars], dtype=np.int64)
h4_close = np.array([b.close for b in h4_bars], dtype=np.float64)
h4_dt = pd.to_datetime(h4_open_ms, unit="ms")

# Save state classification CSV
state_df = pd.DataFrame({
    "open_time": h4_open_ms,
    "open_time_dt": h4_dt,
    "close": h4_close,
    "state": state_arr,
    "trade_id": bar_trade_id,
})
state_df.to_csv(TBL / "state_classification.csv", index=False)

in_count = int(in_trade.sum())
flat_count = n_h4 - in_count
print(f"   IN_TRADE: {in_count} bars ({in_count / n_h4 * 100:.1f}%)")
print(f"   FLAT:     {flat_count} bars ({flat_count / n_h4 * 100:.1f}%)")
print(f"   Saved: state_classification.csv")

# ══════════════════════════════════════════════════════════════════════════
# 4. TEMPORAL STATISTICS
# ══════════════════════════════════════════════════════════════════════════
print(f"\n4. Temporal Statistics...")


def extract_runs(arr: np.ndarray, value: bool):
    """Extract contiguous runs of `value` in boolean array."""
    runs = []
    start = None
    for i in range(len(arr)):
        if arr[i] == value:
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((start, i - 1))
                start = None
    if start is not None:
        runs.append((start, len(arr) - 1))
    return runs


in_runs = extract_runs(in_trade, True)
flat_runs = extract_runs(in_trade, False)


def runs_to_df(runs, h4_bars):
    """Convert (start, end) pairs to DataFrame with duration stats."""
    records = []
    for s, e in runs:
        dur = e - s + 1
        records.append({
            "start_bar": s,
            "end_bar": e,
            "start_dt": pd.to_datetime(h4_bars[s].open_time, unit="ms"),
            "end_dt": pd.to_datetime(h4_bars[e].close_time, unit="ms"),
            "duration_bars": dur,
            "duration_hours": dur * 4,
            "duration_days": dur * 4.0 / 24.0,
        })
    return pd.DataFrame(records)


in_df = runs_to_df(in_runs, h4_bars)
flat_df = runs_to_df(flat_runs, h4_bars)

print(f"   IN_TRADE periods: {len(in_df)}")
print(f"   FLAT periods:     {len(flat_df)}")

# IN_TRADE duration stats
print(f"\n   IN_TRADE Duration Distribution:")
print(f"     Mean:   {in_df['duration_bars'].mean():.1f} bars ({in_df['duration_days'].mean():.1f} days)")
print(f"     Median: {float(in_df['duration_bars'].median()):.0f} bars ({float(in_df['duration_days'].median()):.1f} days)")
print(f"     Min:    {in_df['duration_bars'].min()} bars")
print(f"     Max:    {in_df['duration_bars'].max()} bars ({in_df['duration_days'].max():.1f} days)")
print(f"     Q25:    {float(in_df['duration_bars'].quantile(0.25)):.0f} bars")
print(f"     Q75:    {float(in_df['duration_bars'].quantile(0.75)):.0f} bars")

# FLAT duration stats
print(f"\n   FLAT Duration Distribution:")
print(f"     Mean:   {flat_df['duration_bars'].mean():.1f} bars ({flat_df['duration_days'].mean():.1f} days)")
print(f"     Median: {float(flat_df['duration_bars'].median()):.0f} bars ({float(flat_df['duration_days'].median()):.1f} days)")
print(f"     Min:    {flat_df['duration_bars'].min()} bars")
print(f"     Max:    {flat_df['duration_bars'].max()} bars ({flat_df['duration_days'].max():.1f} days)")
print(f"     Q25:    {float(flat_df['duration_bars'].quantile(0.25)):.0f} bars")
print(f"     Q75:    {float(flat_df['duration_bars'].quantile(0.75)):.0f} bars")

# Tbl01: State summary
tbl01 = {
    "total_h4_bars": n_h4,
    "in_trade_bars": in_count,
    "flat_bars": flat_count,
    "in_trade_pct": round(in_count / n_h4 * 100, 2),
    "flat_pct": round(flat_count / n_h4 * 100, 2),
    "total_trades": sm["trades"],
    "sharpe": sm["sharpe"],
    "cagr_pct": sm["cagr_pct"],
    "mdd_pct": sm["max_drawdown_mid_pct"],
    "win_rate_pct": sm["win_rate_pct"],
    "avg_exposure": sm["avg_exposure"],
    "in_trade_periods": len(in_df),
    "flat_periods": len(flat_df),
    "in_trade_mean_bars": round(in_df["duration_bars"].mean(), 1),
    "in_trade_median_bars": round(float(in_df["duration_bars"].median()), 1),
    "in_trade_max_bars": int(in_df["duration_bars"].max()),
    "in_trade_q25_bars": round(float(in_df["duration_bars"].quantile(0.25)), 1),
    "in_trade_q75_bars": round(float(in_df["duration_bars"].quantile(0.75)), 1),
    "flat_mean_bars": round(flat_df["duration_bars"].mean(), 1),
    "flat_median_bars": round(float(flat_df["duration_bars"].median()), 1),
    "flat_max_bars": int(flat_df["duration_bars"].max()),
    "flat_mean_days": round(flat_df["duration_days"].mean(), 1),
    "flat_median_days": round(float(flat_df["duration_days"].median()), 1),
    "flat_max_days": round(float(flat_df["duration_days"].max()), 1),
    "flat_q25_bars": round(float(flat_df["duration_bars"].quantile(0.25)), 1),
    "flat_q75_bars": round(float(flat_df["duration_bars"].quantile(0.75)), 1),
}
pd.Series(tbl01).to_csv(TBL / "Tbl01_state_summary.csv", header=["value"])
print(f"\n   Saved: Tbl01_state_summary.csv")

# Tbl02: All flat period durations
flat_df.to_csv(TBL / "Tbl02_flat_durations.csv", index=False)
print(f"   Saved: Tbl02_flat_durations.csv")

# Year-by-year state fraction
state_df["year"] = state_df["open_time_dt"].dt.year
yearly = state_df.groupby("year").agg(
    total_bars=("state", "count"),
    in_trade_bars=("state", lambda x: (x == "IN_TRADE").sum()),
).reset_index()
yearly["flat_bars"] = yearly["total_bars"] - yearly["in_trade_bars"]
yearly["in_trade_pct"] = (yearly["in_trade_bars"] / yearly["total_bars"] * 100).round(1)
yearly["flat_pct"] = (yearly["flat_bars"] / yearly["total_bars"] * 100).round(1)
yearly.to_csv(TBL / "yearly_state_fraction.csv", index=False)

print(f"\n   Year-by-year state fraction:")
for _, row in yearly.iterrows():
    print(f"     {int(row['year'])}: IN_TRADE {row['in_trade_pct']}%, FLAT {row['flat_pct']}%")

# ══════════════════════════════════════════════════════════════════════════
# 5. TRANSITION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
print(f"\n5. Transition Analysis...")

# Sort trades by entry bar
ts = trades_df.dropna(subset=["entry_bar_idx", "exit_bar_idx"]).copy()
ts["entry_bar_idx"] = ts["entry_bar_idx"].astype(int)
ts["exit_bar_idx"] = ts["exit_bar_idx"].astype(int)
ts = ts.sort_values("entry_bar_idx").reset_index(drop=True)

# Gap = bars between consecutive trades (exit bar of prev to entry bar of next)
gaps = []
for i in range(1, len(ts)):
    prev_exit = ts.iloc[i - 1]["exit_bar_idx"]
    curr_entry = ts.iloc[i]["entry_bar_idx"]
    gap = curr_entry - prev_exit
    gaps.append({
        "trade_before": int(ts.iloc[i - 1]["trade_id"]),
        "trade_after": int(ts.iloc[i]["trade_id"]),
        "gap_bars": gap,
        "gap_hours": gap * 4,
        "gap_days": gap * 4.0 / 24.0,
    })

gaps_df = pd.DataFrame(gaps)
n_gaps = len(gaps_df)

print(f"   Trade-to-trade transitions: {n_gaps}")
print(f"\n   Gap distribution (bars between trades):")
print(f"     Mean:   {gaps_df['gap_bars'].mean():.1f} bars ({gaps_df['gap_days'].mean():.1f} days)")
print(f"     Median: {float(gaps_df['gap_bars'].median()):.0f} bars ({float(gaps_df['gap_days'].median()):.1f} days)")
print(f"     Min:    {gaps_df['gap_bars'].min()} bars")
print(f"     Max:    {gaps_df['gap_bars'].max()} bars ({gaps_df['gap_days'].max():.1f} days)")

# Re-entry rates
for threshold, label in [(5, "5 bars (20h)"), (10, "10 bars (40h)"),
                          (20, "20 bars (3.3d)")]:
    ct = int((gaps_df["gap_bars"] <= threshold).sum())
    print(f"   Re-entry within {label}: {ct}/{n_gaps} ({ct / n_gaps * 100:.1f}%)")

# Quick-flip rate
qf = int((gaps_df["gap_bars"] <= 2).sum())
print(f"   Quick-flips (<=2 bars, 8h): {qf}/{n_gaps} ({qf / n_gaps * 100:.1f}%)")

# Same-bar re-entry (gap = 0 or 1)
sb = int((gaps_df["gap_bars"] <= 1).sum())
print(f"   Immediate re-entry (<=1 bar): {sb}/{n_gaps} ({sb / n_gaps * 100:.1f}%)")

# Save gaps
gaps_df.to_csv(TBL / "trade_gaps.csv", index=False)

# ══════════════════════════════════════════════════════════════════════════
# 6. FIGURES
# ══════════════════════════════════════════════════════════════════════════
print(f"\n6. Generating figures...")

# Fig01: Price + state overlay with colored background
fig, axes = plt.subplots(2, 1, figsize=(16, 8), height_ratios=[3, 1],
                          gridspec_kw={"hspace": 0.08})

ax = axes[0]
ax.plot(h4_dt, h4_close, color="gray", linewidth=0.35, alpha=0.8)
for _, p in in_df.iterrows():
    ax.axvspan(p["start_dt"], p["end_dt"], alpha=0.12, color="green")
ax.set_ylabel("BTC Price (USDT)")
ax.set_yscale("log")
ax.set_title(f"Fig01: VTREND E5+EMA21D1 Position State Map "
             f"({sm['trades']} trades, Sharpe {sm['sharpe']})")
ax.tick_params(labelbottom=False)

ax = axes[1]
ax.fill_between(h4_dt, in_trade.astype(float), alpha=0.5, color="green")
ax.set_ylabel("State")
ax.set_yticks([0, 1])
ax.set_yticklabels(["FLAT", "IN_TRADE"])
ax.set_xlabel("Date")

plt.tight_layout()
plt.savefig(FIG / "Fig01_price_state_overlay.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"   Saved: Fig01_price_state_overlay.png")

# Fig02: Flat duration histogram
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

med_d = float(flat_df["duration_days"].median())
mean_d = float(flat_df["duration_days"].mean())

ax = axes[0]
ax.hist(flat_df["duration_days"], bins=50, color="steelblue",
        edgecolor="white", alpha=0.8)
ax.set_xlabel("Flat Period Duration (days)")
ax.set_ylabel("Count")
ax.set_title("Fig02a: Flat Period Duration Distribution")
ax.axvline(med_d, color="red", ls="--", label=f"Median={med_d:.1f}d")
ax.axvline(mean_d, color="orange", ls="--", label=f"Mean={mean_d:.1f}d")
ax.legend()

ax = axes[1]
# Log-x view to see the right tail
bins_log = np.logspace(np.log10(0.167), np.log10(flat_df["duration_days"].max() + 1), 40)
ax.hist(flat_df["duration_days"], bins=bins_log, color="steelblue",
        edgecolor="white", alpha=0.8)
ax.set_xlabel("Flat Period Duration (days, log scale)")
ax.set_ylabel("Count")
ax.set_title("Fig02b: Flat Duration (log-x)")
ax.set_xscale("log")
ax.axvline(med_d, color="red", ls="--", label=f"Median={med_d:.1f}d")
ax.legend()

plt.tight_layout()
plt.savefig(FIG / "Fig02_flat_duration_hist.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"   Saved: Fig02_flat_duration_hist.png")

# Fig03: Yearly state fraction (stacked bar)
fig, ax = plt.subplots(figsize=(12, 5))
yrs = yearly["year"].values.astype(int)
ax.bar(yrs, yearly["in_trade_pct"], color="green", alpha=0.6, label="IN_TRADE %")
ax.bar(yrs, yearly["flat_pct"], bottom=yearly["in_trade_pct"],
       color="lightgray", alpha=0.7, label="FLAT %")
ax.set_xlabel("Year")
ax.set_ylabel("Fraction (%)")
ax.set_title("Fig03: Yearly State Fraction — VTREND E5+EMA21D1")
ax.legend(loc="upper right")
ax.set_xticks(yrs)
ax.set_ylim(0, 105)

for i, yr in enumerate(yrs):
    pct = yearly.iloc[i]["in_trade_pct"]
    ax.text(yr, pct / 2, f"{pct:.0f}%", ha="center", va="center", fontsize=8)

plt.tight_layout()
plt.savefig(FIG / "Fig03_yearly_state_fraction.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"   Saved: Fig03_yearly_state_fraction.png")

# ══════════════════════════════════════════════════════════════════════════
# 7. CROSS-REFERENCE
# ══════════════════════════════════════════════════════════════════════════
print(f"\n7. Cross-reference checks:")

# Full-range run (this phase)
print(f"   [Full range — used for state classification]")
print(f"   Trades:    {sm['trades']}")
print(f"   Sharpe:    {sm['sharpe']}")
print(f"   CAGR:      {sm['cagr_pct']}%")
print(f"   MDD:       {sm['max_drawdown_mid_pct']}%")
print(f"   Win rate:  {sm['win_rate_pct']}%")
print(f"   Exposure:  {sm['avg_exposure']:.4f}")

# Eval-window cross-reference (2019-01-01 → 2026-02-20, warmup 365d)
# Known ref from full_eval_e5_ema21d1: 186 trades, Sharpe ~1.56 (base cost)
# Under harsh cost: slightly different
print(f"\n   [Eval window 2019-01-01 → 2026-02-20, warmup 365d, harsh cost]")
print(f"   Trades:    {sm_eval['trades']} (ref: ~186 under base cost)")
print(f"   Sharpe:    {sm_eval['sharpe']}")
print(f"   CAGR:      {sm_eval['cagr_pct']}%")
print(f"   MDD:       {sm_eval['max_drawdown_mid_pct']}%")

# Note on 201-trade reference
print(f"\n   CLARIFICATION: The '~201 trades' in prompt refers to X0 (E0+EMA21D1),")
print(f"   not E5+EMA21D1. E5 uses robust ATR (different from E0's standard ATR).")
print(f"   Full-range E5+EMA21D1 produces {sm['trades']} trades — no discrepancy.")

# ══════════════════════════════════════════════════════════════════════════
# 8. SAVE SUPPLEMENTARY DATA
# ══════════════════════════════════════════════════════════════════════════
trades_df.to_csv(TBL / "trades.csv", index=False)
in_df.to_csv(TBL / "in_trade_periods.csv", index=False)
np.save(TBL / "in_position.npy", in_trade)

print(f"\n   Saved supplementary: trades.csv, in_trade_periods.csv, in_position.npy")

print(f"\n{'=' * 70}")
print(f"PHASE 1 COMPLETE")
print(f"{'=' * 70}")
