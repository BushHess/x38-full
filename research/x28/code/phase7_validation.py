"""
Phase 7 — Validation
X28 Research: Implement, backtest, validate each candidate RIGOROUSLY.
Candidates from Phase 6.  Benchmark: A_20_90 + Y_atr3 (no filter).
"""

import os, json, time, warnings
import numpy as np
import pandas as pd
from collections import OrderedDict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

t0_global = time.time()

# ── Paths ─────────────────────────────────────────────────────────────
BASE = "/var/www/trading-bots/btc-spot-dev/research/x28"
DATA = "/var/www/trading-bots/btc-spot-dev/data"
FIG_DIR = os.path.join(BASE, "figures")
TBL_DIR = os.path.join(BASE, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TBL_DIR, exist_ok=True)

ANN = 365.25 * 6   # H4 bars per year
COST_DEFAULT = 50   # bps round-trip

# ══════════════════════════════════════════════════════════════════════
# SECTION 0: DATA LOADING & INDICATORS
# ══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("PHASE 7: VALIDATION")
print("=" * 70)

def load_tf(tf):
    fp = os.path.join(DATA, f"btcusdt_{tf}.csv")
    df = pd.read_csv(fp)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.sort_values("open_time").reset_index(drop=True)
    return df

print("\nLoading data...")
h4 = load_tf("4h")
d1 = load_tf("1d")
print(f"  H4: {len(h4)} bars ({h4['open_time'].iloc[0].date()} → {h4['open_time'].iloc[-1].date()})")
print(f"  D1: {len(d1)} bars")

closes = h4["close"].values.astype(float)
highs  = h4["high"].values.astype(float)
lows   = h4["low"].values.astype(float)
timestamps = h4["open_time"].values
n_bars = len(closes)
n_years = n_bars / ANN

def _ema(arr, span):
    return pd.Series(arr).ewm(span=span, adjust=False).mean().values

def _atr(hi, lo, cl, period):
    tr = np.empty(len(cl))
    tr[0] = hi[0] - lo[0]
    tr[1:] = np.maximum(hi[1:] - lo[1:],
              np.maximum(np.abs(hi[1:] - cl[:-1]),
                         np.abs(lo[1:] - cl[:-1])))
    return pd.Series(tr).ewm(span=period, adjust=False).mean().values

def _rolling_max(arr, period):
    return pd.Series(arr).rolling(period, min_periods=period).max().values

print("Computing indicators...")
ema_20 = _ema(closes, 20)
ema_90 = _ema(closes, 90)
atr_14 = _atr(highs, lows, closes, 14)
rolling_max_60 = _rolling_max(closes, 60)

# D1 EMA(50) and EMA(21) regime → H4 (1-day lag)
d1_close = d1["close"].values.astype(float)
d1["ema50"] = _ema(d1_close, 50)
d1["ema21"] = _ema(d1_close, 21)
d1["regime_ema50"] = (d1["close"] > d1["ema50"]).astype(int)
d1["regime_ema21"] = (d1["close"] > d1["ema21"]).astype(int)

d1_merge = d1[["open_time", "regime_ema50", "regime_ema21"]].copy()
d1_merge["merge_time"] = d1_merge["open_time"] + pd.Timedelta(days=1)
h4_times = h4[["open_time"]].copy()
h4_times["open_time"] = h4_times["open_time"].astype("datetime64[us]")
d1_merge["merge_time"] = d1_merge["merge_time"].astype("datetime64[us]")
merged = pd.merge_asof(h4_times, d1_merge[["merge_time", "regime_ema50", "regime_ema21"]],
                        left_on="open_time", right_on="merge_time", direction="backward")
d1_regime_ema50 = merged["regime_ema50"].fillna(0).astype(int).values
d1_regime_ema21 = merged["regime_ema21"].fillna(0).astype(int).values
d1_filter = d1_regime_ema50.astype(bool)

print(f"  Indicators ready. D1 EMA50 regime: {d1_regime_ema50.sum()} bars ({d1_regime_ema50.mean():.1%})")

# ══════════════════════════════════════════════════════════════════════
# SECTION 1: BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════

def backtest(entry_sig, exit_func, filt=None, cost_bps=50):
    """Full-sample backtest.  Returns equity array + trade list."""
    cost_half = cost_bps / 20_000
    eff = entry_sig & filt if filt is not None else entry_sig.copy()

    equity = np.ones(n_bars)
    trades = []
    in_pos = False
    ep = hwm = 0.0
    eb = 0

    for i in range(1, n_bars):
        if in_pos:
            equity[i] = equity[i-1] * (closes[i] / closes[i-1])
            if closes[i] > hwm:
                hwm = closes[i]
            if exit_func(i, hwm, eb):
                equity[i] *= (1 - cost_half)
                trades.append(dict(entry_bar=eb, exit_bar=i, hold=i-eb,
                    gross_ret=closes[i]/ep - 1,
                    net_ret=closes[i]/ep - 1 - cost_bps/10_000))
                in_pos = False
        else:
            equity[i] = equity[i-1]
            if eff[i]:
                in_pos = True; ep = closes[i]; eb = i; hwm = closes[i]
                equity[i] *= (1 - cost_half)

    if in_pos:
        trades.append(dict(entry_bar=eb, exit_bar=n_bars-1, hold=n_bars-1-eb,
            gross_ret=closes[-1]/ep - 1,
            net_ret=closes[-1]/ep - 1 - cost_bps/10_000))
    return equity, trades


def metrics(equity, trades, n_total=None):
    """Compute comprehensive metrics from equity curve + trades."""
    if n_total is None:
        n_total = len(equity)
    ny = n_total / ANN
    lr = np.diff(np.log(np.maximum(equity, 1e-12)))
    mu = np.mean(lr); sig = np.std(lr, ddof=0)
    sharpe = mu / sig * np.sqrt(ANN) if sig > 0 else 0.0
    cagr = (equity[-1] / equity[0]) ** (1/ny) - 1 if ny > 0 and equity[-1] > 0 else 0.0
    rm = np.maximum.accumulate(equity)
    mdd = float(np.min((equity - rm) / rm))
    calmar = cagr / abs(mdd) if abs(mdd) > 0.001 else 0.0
    nt = len(trades)
    if nt == 0:
        return dict(sharpe=0, cagr=0, mdd=0, calmar=0, n_trades=0, exposure=0,
                    win_rate=0, avg_winner=0, avg_loser=0, profit_factor=0,
                    avg_hold=0, max_consec_loss=0, churn_rate=0)
    nrs = [t["net_ret"] for t in trades]
    w = [r for r in nrs if r > 0]; lo = [r for r in nrs if r <= 0]
    aw = float(np.mean(w)) if w else 0.0
    al = float(np.mean(lo)) if lo else 0.0
    wr = len(w) / nt
    pf = sum(w) / abs(sum(lo)) if lo and sum(lo) != 0 else 99.0
    exp = sum(t["hold"] for t in trades) / n_total
    ah = float(np.mean([t["hold"] for t in trades]))
    mcl = 0; cl = 0
    for r in nrs:
        if r <= 0: cl += 1; mcl = max(mcl, cl)
        else: cl = 0
    churn = sum(1 for k in range(nt-1)
                if trades[k+1]["entry_bar"] - trades[k]["exit_bar"] <= 10) / nt
    return dict(sharpe=sharpe, cagr=cagr, mdd=mdd, calmar=calmar, n_trades=nt,
                exposure=exp, win_rate=wr, avg_winner=aw, avg_loser=al,
                profit_factor=pf, avg_hold=ah, max_consec_loss=mcl, churn_rate=churn)


# ══════════════════════════════════════════════════════════════════════
# SECTION 2: STRATEGY DEFINITIONS
# ══════════════════════════════════════════════════════════════════════
print("\nDefining strategies...")

# --- Entry signals (cross-up, matching Phase 3) ---
ema_above = ema_20 > ema_90
ema_cross = np.zeros(n_bars, dtype=bool)
ema_cross[1:] = ema_above[1:] & ~ema_above[:-1]

prev_max_60 = np.full(n_bars, np.nan)
prev_max_60[60:] = rolling_max_60[59:-1]
brk_level = np.zeros(n_bars, dtype=bool)
valid = ~np.isnan(prev_max_60)
brk_level[valid] = closes[valid] > prev_max_60[valid]
brk_cross = np.zeros(n_bars, dtype=bool)
brk_cross[1:] = brk_level[1:] & ~brk_level[:-1]

# --- Exit functions ---
def exit_trail8(i, hwm, eb):
    return closes[i] < hwm * 0.92

def exit_atr3(i, hwm, eb):
    return closes[i] < hwm - 3.0 * atr_14[i]

def exit_composite(i, hwm, eb):
    return closes[i] < hwm * 0.92 or ema_20[i] < ema_90[i]

# --- Strategies ---
strats = OrderedDict([
    ("Cand01", dict(entry=ema_cross, exit=exit_trail8, filt=d1_filter,
                    desc="EMA(20,90) cross + trail 8% + D1 EMA(50)", dof=4)),
    ("Cand02", dict(entry=ema_cross, exit=exit_composite, filt=d1_filter,
                    desc="EMA(20,90) cross + (trail 8% OR reversal) + D1 EMA(50)", dof=5)),
    ("Cand03", dict(entry=brk_cross, exit=exit_atr3, filt=d1_filter,
                    desc="60-bar breakout + ATR(14)*3.0 trail + D1 EMA(50)", dof=3)),
    ("Benchmark", dict(entry=ema_cross, exit=exit_atr3, filt=None,
                       desc="EMA(20,90) cross + ATR(14)*3.0 trail (no filter)", dof=3)),
])
for nm, s in strats.items():
    print(f"  {nm}: {s['desc']}  (raw signals: {s['entry'].sum()})")

# ══════════════════════════════════════════════════════════════════════
# SECTION 3: FULL-SAMPLE BACKTEST
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 3: FULL-SAMPLE BACKTEST (50 bps RT)")
print("=" * 70)

full_eq = {}; full_tr = {}; full_m = {}
for nm, s in strats.items():
    eq, tr = backtest(s["entry"], s["exit"], s.get("filt"), COST_DEFAULT)
    m = metrics(eq, tr)
    full_eq[nm] = eq; full_tr[nm] = tr; full_m[nm] = m
    print(f"\n  {nm}: {s['desc']}")
    print(f"    Sharpe={m['sharpe']:.3f}  CAGR={m['cagr']:.1%}  MDD={m['mdd']:.1%}  "
          f"Calmar={m['calmar']:.3f}")
    print(f"    Trades={m['n_trades']}  WinRate={m['win_rate']:.1%}  Exposure={m['exposure']:.1%}  "
          f"AvgHold={m['avg_hold']:.1f}")
    print(f"    AvgWinner={m['avg_winner']:.4f}  AvgLoser={m['avg_loser']:.4f}  "
          f"PF={m['profit_factor']:.2f}  MaxConsecLoss={m['max_consec_loss']}")

# Buy-and-hold reference
bh_eq = np.cumprod(np.concatenate([[1.0], closes[1:] / closes[:-1]]))
bh_lr = np.diff(np.log(bh_eq))
bh_sh = np.mean(bh_lr) / np.std(bh_lr, ddof=0) * np.sqrt(ANN)
bh_cagr = (bh_eq[-1]) ** (1/n_years) - 1
bh_mdd = float(np.min((bh_eq - np.maximum.accumulate(bh_eq)) / np.maximum.accumulate(bh_eq)))
print(f"\n  Buy-and-hold: Sharpe={bh_sh:.3f}  CAGR={bh_cagr:.1%}  MDD={bh_mdd:.1%}")

# --- Rejection criteria (from Phase 6 §6) ---
print("\n  --- Rejection Criteria ---")
bench_sh = full_m["Benchmark"]["sharpe"]
rej = {
    "Sharpe < 0":              lambda m: m["sharpe"] < 0,
    "Sharpe < 0.80*bench":     lambda m: m["sharpe"] < bench_sh * 0.80,
    "MDD > 75%":               lambda m: abs(m["mdd"]) > 0.75,
    "Trades < 15":             lambda m: m["n_trades"] < 15,
}
for c in ["Cand01", "Cand02", "Cand03"]:
    fails = [k for k, fn in rej.items() if fn(full_m[c])]
    tag = f"FAIL ({', '.join(fails)})" if fails else "PASS all"
    print(f"    {c}: {tag}")

# Save table
comp_rows = [{"strategy": nm, **full_m[nm]} for nm in strats]
pd.DataFrame(comp_rows).to_csv(os.path.join(TBL_DIR, "Tbl_full_sample_comparison.csv"), index=False)
print("  Saved Tbl_full_sample_comparison")

# ── Sanity: trade count vs Phase 6 estimate ──
p6_est = {"Cand01": 39, "Cand02": 49, "Cand03": 110}
for c, est in p6_est.items():
    actual = full_m[c]["n_trades"]
    dev = abs(actual - est) / est
    flag = " *** >30% deviation" if dev > 0.30 else ""
    print(f"    {c} trade count: actual={actual}, expected={est}, dev={dev:.0%}{flag}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 4: PLOTS (Fig14–Fig17)
# ══════════════════════════════════════════════════════════════════════
print("\nGenerating plots...")
clr = {"Cand01": "tab:blue", "Cand02": "tab:green", "Cand03": "tab:orange", "Benchmark": "gray"}
ti = pd.to_datetime(timestamps)

# Fig14: Equity curves
fig, ax = plt.subplots(figsize=(14, 7))
for nm in ["Benchmark", "Cand01", "Cand02", "Cand03"]:
    ls = "--" if nm == "Benchmark" else "-"
    ax.plot(ti, full_eq[nm], label=f"{nm} (Sh={full_m[nm]['sharpe']:.2f})",
            color=clr[nm], linewidth=1.8, linestyle=ls, alpha=0.85)
ax.plot(ti, bh_eq, label=f"B&H (Sh={bh_sh:.2f})", color="black",
        linewidth=1, linestyle=":", alpha=0.5)
ax.set_yscale("log"); ax.set_ylabel("Equity (log)"); ax.set_xlabel("Date")
ax.set_title("Fig14: Equity Curves — Candidates vs Benchmark (50 bps RT)")
ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "Fig14_equity_curves.png"), dpi=150)
plt.close(fig)

# Fig15: Drawdown
fig, ax = plt.subplots(figsize=(14, 5))
for nm in ["Benchmark", "Cand01", "Cand02", "Cand03"]:
    eq = full_eq[nm]; rm = np.maximum.accumulate(eq)
    dd = (eq - rm) / rm * 100
    ls = "--" if nm == "Benchmark" else "-"
    ax.plot(ti, dd, label=nm, color=clr[nm], linewidth=1.5, linestyle=ls, alpha=0.75)
ax.set_ylabel("Drawdown (%)"); ax.set_xlabel("Date")
ax.set_title("Fig15: Drawdown — Candidates vs Benchmark")
ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "Fig15_drawdown.png"), dpi=150)
plt.close(fig)

# Fig16: Monthly return heatmaps
for cand in ["Cand01", "Cand02", "Cand03"]:
    eq_s = pd.Series(full_eq[cand], index=ti)
    mo = eq_s.resample("ME").last().pct_change().dropna()
    yrs = sorted(mo.index.year.unique()); nm_arr = 12
    heat = np.full((len(yrs), nm_arr), np.nan)
    for idx, val in mo.items():
        heat[yrs.index(idx.year), idx.month - 1] = val * 100
    fig, ax = plt.subplots(figsize=(12, max(3, len(yrs)*0.4)))
    im = ax.imshow(heat, cmap="RdYlGn", aspect="auto", vmin=-30, vmax=30)
    ax.set_xticks(range(12))
    ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"], fontsize=8)
    ax.set_yticks(range(len(yrs))); ax.set_yticklabels(yrs, fontsize=7)
    for r in range(heat.shape[0]):
        for c2 in range(heat.shape[1]):
            if not np.isnan(heat[r, c2]):
                ax.text(c2, r, f"{heat[r,c2]:.0f}", ha="center", va="center", fontsize=5,
                        color="white" if abs(heat[r,c2]) > 15 else "black")
    ax.set_title(f"Fig16: Monthly Returns (%) — {cand}")
    fig.colorbar(im, ax=ax, label="%", shrink=0.7)
    fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, f"Fig16_heatmap_{cand}.png"), dpi=150)
    plt.close(fig)

# Fig17: Trade return distribution
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, cand in zip(axes, ["Cand01", "Cand02", "Cand03"]):
    rets = [t["net_ret"]*100 for t in full_tr[cand]]
    if rets:
        ax.hist(rets, bins=min(30, max(5, len(rets)//2)), color=clr[cand],
                alpha=0.7, edgecolor="k", linewidth=0.5)
        ax.axvline(0, color="k", linewidth=1, linestyle="--")
        ax.axvline(np.mean(rets), color="red", linewidth=1.5,
                   label=f"mean={np.mean(rets):.1f}%")
    ax.set_xlabel("Return/Trade (%)"); ax.set_title(f"{cand} (N={len(rets)})")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
fig.suptitle("Fig17: Trade Return Distribution", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig17_trade_distribution.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("  Saved Fig14–Fig17")

# ══════════════════════════════════════════════════════════════════════
# SECTION 5: CONSTRAINT VERIFICATION
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 5: CONSTRAINT VERIFICATION")
print("=" * 70)

hc = OrderedDict([
    ("HC-1: avg_loser >= -0.08", lambda m: m["avg_loser"] >= -0.08),
    ("HC-2: avg_hold >= 40",     lambda m: m["avg_hold"] >= 40),
    ("HC-3: 30-200 trades",      lambda m: 30 <= m["n_trades"] <= 200),
    ("HC-6: MDD <= 60%",         lambda m: abs(m["mdd"]) <= 0.60),
])

p6_vals = {
    "Cand01": dict(n_trades=39, exposure=0.258, avg_hold=124.3, avg_loser=-0.070,
                   avg_winner=0.309, win_rate=0.462, churn_rate=0.0),
    "Cand02": dict(n_trades=49, exposure=0.198, avg_hold=75.6, avg_loser=-0.043,
                   avg_winner=0.319, win_rate=0.306, churn_rate=0.0),
    "Cand03": dict(n_trades=110, exposure=0.275, avg_hold=47.0, avg_loser=-0.041,
                   avg_winner=0.155, win_rate=0.382, churn_rate=0.0),
}

cv_rows = []
for c in ["Cand01", "Cand02", "Cand03"]:
    m = full_m[c]
    print(f"\n  {c}:")
    for cname, check in hc.items():
        ok = check(m)
        # extract actual value for the constraint
        if "avg_loser" in cname:  val = m["avg_loser"]
        elif "avg_hold" in cname: val = m["avg_hold"]
        elif "trades" in cname:   val = m["n_trades"]
        else:                     val = abs(m["mdd"])
        cv_rows.append(dict(candidate=c, constraint=cname, actual=val,
                            status="PASS" if ok else "FAIL"))
        print(f"    {cname}: {'PASS' if ok else 'FAIL'} (actual={val:.4f})")

    # Phase 6 estimate comparison
    est = p6_vals[c]
    print(f"    --- vs Phase 6 estimates ---")
    for k in ["n_trades", "exposure", "avg_hold", "avg_loser", "avg_winner", "win_rate"]:
        a = m[k]; e = est[k]
        d = abs(a - e) / abs(e) if e != 0 else abs(a - e)
        flag = " *** >30%" if d > 0.30 else ""
        print(f"    {k:15s}: actual={a:9.4f}  expected={e:9.4f}  dev={d:.0%}{flag}")

pd.DataFrame(cv_rows).to_csv(os.path.join(TBL_DIR, "Tbl_constraint_verification.csv"), index=False)
print("  Saved Tbl_constraint_verification")

# ══════════════════════════════════════════════════════════════════════
# SECTION 6: WALK-FORWARD OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 6: WALK-FORWARD OPTIMIZATION (4-fold anchored)")
print("=" * 70)

N_FOLDS = 4
seg = n_bars // (N_FOLDS + 1)

# Pre-compute full-sample log returns per strategy
full_lr = {}
for nm in strats:
    full_lr[nm] = np.diff(np.log(np.maximum(full_eq[nm], 1e-12)))

wfo_rows = []
for fold in range(N_FOLDS):
    is_end = seg * (fold + 1)
    oos_s = is_end
    oos_e = min(seg * (fold + 2), n_bars)
    date_s = pd.Timestamp(timestamps[oos_s]).strftime("%Y-%m")
    date_e = pd.Timestamp(timestamps[min(oos_e-1, n_bars-1)]).strftime("%Y-%m")
    print(f"\n  Fold {fold+1}: IS [0,{is_end}), OOS [{oos_s},{oos_e})  {date_s}→{date_e}")

    for nm in strats:
        lr = full_lr[nm]
        is_lr = lr[:is_end-1]
        oos_lr = lr[oos_s:oos_e-1]
        sh_is = np.mean(is_lr)/np.std(is_lr, ddof=0)*np.sqrt(ANN) if np.std(is_lr, ddof=0)>0 else 0
        sh_oos = np.mean(oos_lr)/np.std(oos_lr, ddof=0)*np.sqrt(ANN) if np.std(oos_lr, ddof=0)>0 else 0
        n_tr = sum(1 for t in full_tr[nm] if oos_s <= t["entry_bar"] < oos_e)
        wfo_rows.append(dict(fold=fold+1, strategy=nm, is_sharpe=sh_is,
                             oos_sharpe=sh_oos, oos_trades=n_tr))

wfo_df = pd.DataFrame(wfo_rows)

# Compute deltas & win rates
print("\n  --- WFO Summary ---")
wfo_deltas = {}  # {cand: [delta_fold1, ...]}
for c in ["Cand01", "Cand02", "Cand03"]:
    ds = []
    for f in range(1, N_FOLDS+1):
        c_sh = wfo_df[(wfo_df.strategy==c)&(wfo_df.fold==f)]["oos_sharpe"].values[0]
        b_sh = wfo_df[(wfo_df.strategy=="Benchmark")&(wfo_df.fold==f)]["oos_sharpe"].values[0]
        ds.append(c_sh - b_sh)
    wfo_deltas[c] = ds
    wr = sum(1 for d in ds if d > 0) / len(ds)
    gate = "PASS" if wr >= 0.50 else "FAIL"
    print(f"    {c}: deltas={[f'{d:+.3f}' for d in ds]}  winrate={wr:.0%}  {gate}")
    for f in range(N_FOLDS):
        row = wfo_df[(wfo_df.strategy==c)&(wfo_df.fold==f+1)].iloc[0]
        print(f"      Fold {f+1}: IS_Sh={row['is_sharpe']:.3f}  OOS_Sh={row['oos_sharpe']:.3f}  "
              f"Δbench={ds[f]:+.3f}  OOS_trades={row['oos_trades']}")

wfo_df.to_csv(os.path.join(TBL_DIR, "Tbl_wfo_results.csv"), index=False)
print("  Saved Tbl_wfo_results")

# Fig18: WFO deltas
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(N_FOLDS); w = 0.25
for i, c in enumerate(["Cand01", "Cand02", "Cand03"]):
    ax.bar(x + i*w, wfo_deltas[c], w, label=c, color=list(clr.values())[i],
           edgecolor="k", linewidth=0.5)
ax.axhline(0, color="k", linewidth=1)
ax.set_xticks(x + w); ax.set_xticklabels([f"Fold {i+1}" for i in range(N_FOLDS)])
ax.set_ylabel("ΔSharpe (Candidate − Benchmark)")
ax.set_title("Fig18: WFO Per-Fold OOS Delta vs Benchmark")
ax.legend(); ax.grid(True, alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "Fig18_wfo_deltas.png"), dpi=150)
plt.close(fig)
print("  Saved Fig18")

# ══════════════════════════════════════════════════════════════════════
# SECTION 7: BOOTSTRAP VALIDATION
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 7: BOOTSTRAP VALIDATION (circular block, 2000 paths)")
print("=" * 70)

np.random.seed(42)
N_PATHS = 2000
BLOCK = int(np.sqrt(n_bars - 1))
print(f"  Block size: {BLOCK}, N paths: {N_PATHS}")

def cbb(cand_lr, bench_lr, block, npaths):
    n = len(cand_lr)
    nblk = int(np.ceil(n / block))
    sh_c = np.empty(npaths); sh_b = np.empty(npaths)
    for p in range(npaths):
        starts = np.random.randint(0, n, size=nblk)
        idx = np.concatenate([np.arange(s, s+block) % n for s in starts])[:n]
        bc = cand_lr[idx]; bb = bench_lr[idx]
        sc = np.std(bc, ddof=0); sb = np.std(bb, ddof=0)
        sh_c[p] = np.mean(bc)/sc*np.sqrt(ANN) if sc > 0 else 0
        sh_b[p] = np.mean(bb)/sb*np.sqrt(ANN) if sb > 0 else 0
    d = sh_c - sh_b
    return dict(sh_cand=sh_c, sh_bench=sh_b, d_sharpe=d,
                p_pos=np.mean(sh_c > 0), p_d_pos=np.mean(d > 0),
                med_d=np.median(d), p5=np.percentile(d, 5), p95=np.percentile(d, 95))

bs_res = {}
bench_lr = full_lr["Benchmark"]
for c in ["Cand01", "Cand02", "Cand03"]:
    t1 = time.time()
    r = cbb(full_lr[c], bench_lr, BLOCK, N_PATHS)
    bs_res[c] = r
    el = time.time() - t1
    gate = "PASS" if r["p_pos"] >= 0.70 else "FAIL"
    print(f"\n  {c} ({el:.1f}s):")
    print(f"    P(Sharpe>0) = {r['p_pos']:.1%}  →  {gate}")
    print(f"    P(ΔSharpe>0) = {r['p_d_pos']:.1%}")
    print(f"    Median ΔSharpe = {r['med_d']:+.3f}  [{r['p5']:+.3f}, {r['p95']:+.3f}]")

bs_rows = [dict(candidate=c, P_sharpe_pos=bs_res[c]["p_pos"],
                P_d_pos=bs_res[c]["p_d_pos"], median_d=bs_res[c]["med_d"],
                pct5=bs_res[c]["p5"], pct95=bs_res[c]["p95"],
                gate=bs_res[c]["p_pos"]>=0.70)
           for c in ["Cand01", "Cand02", "Cand03"]]
pd.DataFrame(bs_rows).to_csv(os.path.join(TBL_DIR, "Tbl_bootstrap_summary.csv"), index=False)
print("  Saved Tbl_bootstrap_summary")

# Fig19: Bootstrap distributions
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, c in zip(axes, ["Cand01", "Cand02", "Cand03"]):
    d = bs_res[c]["d_sharpe"]
    ax.hist(d, bins=50, color=clr[c], alpha=0.7, edgecolor="k", linewidth=0.3)
    ax.axvline(0, color="k", linewidth=1.5, linestyle="--")
    ax.axvline(np.median(d), color="red", linewidth=1.5, label=f"med={np.median(d):+.3f}")
    ax.set_title(f"{c}: P(Δ>0)={np.mean(d>0)*100:.0f}%")
    ax.set_xlabel("ΔSharpe"); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
fig.suptitle("Fig19: Bootstrap ΔSharpe (Candidate − Benchmark)", y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "Fig19_bootstrap.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("  Saved Fig19")

# ══════════════════════════════════════════════════════════════════════
# SECTION 8: ROBUSTNESS CHECKS
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 8: ROBUSTNESS CHECKS")
print("=" * 70)

# ── 8a. Jackknife ────────────────────────────────────────────────────
print("\n  --- 8a. Jackknife (remove 1/6 chronologically) ---")
JK_FOLDS = 6
jk_seg = n_bars // JK_FOLDS
jk_rows = []

for fold in range(JK_FOLDS):
    rs = fold * jk_seg
    re = min((fold + 1) * jk_seg, n_bars)
    for nm in list(strats.keys()):
        lr = full_lr[nm]
        mask = np.ones(len(lr), dtype=bool)
        mask[rs:min(re, len(lr))] = False
        kept = lr[mask]
        s_jk = np.mean(kept)/np.std(kept, ddof=0)*np.sqrt(ANN) if np.std(kept, ddof=0)>0 else 0
        jk_rows.append(dict(fold=fold+1, removed=f"{rs}-{re}", strategy=nm, sharpe=s_jk))

jk_df = pd.DataFrame(jk_rows)
jk_df.to_csv(os.path.join(TBL_DIR, "Tbl_jackknife.csv"), index=False)

for c in ["Cand01", "Cand02", "Cand03"]:
    sub = jk_df[jk_df.strategy == c]
    neg = (sub.sharpe < 0).sum()
    gate = "PASS" if neg <= 1 else "FAIL"
    vals = ", ".join(f"{v:.3f}" for v in sub.sharpe.values)
    print(f"    {c}: [{vals}]  neg={neg}  {gate}")
print("  Saved Tbl_jackknife")

# ── 8b. Cost Sensitivity ─────────────────────────────────────────────
print("\n  --- 8b. Cost Sensitivity ---")
cost_levels = [15, 30, 50, 75, 100]
cost_rows = []
for cost in cost_levels:
    for nm in strats:
        s = strats[nm]
        eq, tr = backtest(s["entry"], s["exit"], s.get("filt"), cost)
        m = metrics(eq, tr)
        cost_rows.append(dict(cost_bps=cost, strategy=nm, sharpe=m["sharpe"],
                              cagr=m["cagr"], mdd=m["mdd"], n_trades=m["n_trades"]))

cost_df = pd.DataFrame(cost_rows)
cost_df.to_csv(os.path.join(TBL_DIR, "Tbl_cost_sensitivity.csv"), index=False)

for c in ["Cand01", "Cand02", "Cand03"]:
    row_str = f"    {c}: "
    for cost in cost_levels:
        sh = cost_df[(cost_df.strategy==c)&(cost_df.cost_bps==cost)]["sharpe"].values[0]
        row_str += f"{cost}bps={sh:.3f}  "
    print(row_str)
    # Breakeven (Sharpe=0)
    for cst in range(5, 300, 5):
        eq2, tr2 = backtest(strats[c]["entry"], strats[c]["exit"], strats[c].get("filt"), cst)
        m2 = metrics(eq2, tr2)
        if m2["sharpe"] <= 0:
            print(f"      breakeven ~ {cst} bps")
            break
    # Crossover vs benchmark
    for cst in cost_levels:
        sh_c = cost_df[(cost_df.strategy==c)&(cost_df.cost_bps==cst)]["sharpe"].values[0]
        sh_b = cost_df[(cost_df.strategy=="Benchmark")&(cost_df.cost_bps==cst)]["sharpe"].values[0]
        if sh_c < sh_b:
            print(f"      loses to benchmark at {cst} bps")
            break
print("  Saved Tbl_cost_sensitivity")

# Fig20: Cost sensitivity
fig, ax = plt.subplots(figsize=(10, 6))
for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
    sub = cost_df[cost_df.strategy == nm]
    ls = "--" if nm == "Benchmark" else "-"
    ax.plot(sub["cost_bps"], sub["sharpe"], marker="o", label=nm,
            color=clr[nm], linewidth=2, linestyle=ls)
ax.axhline(0, color="k", linewidth=1, linestyle=":")
ax.set_xlabel("Cost (bps RT)"); ax.set_ylabel("Sharpe")
ax.set_title("Fig20: Cost Sensitivity")
ax.legend(); ax.grid(True, alpha=0.3)
fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "Fig20_cost_sensitivity.png"), dpi=150)
plt.close(fig)
print("  Saved Fig20")

# ── 8c. Regime Split ─────────────────────────────────────────────────
print("\n  --- 8c. Regime Split (D1 EMA21 bull/bear) ---")
bull = d1_regime_ema21[1:].astype(bool)  # align with lr length
bear = ~bull
regime_rows = []
for rname, rmask in [("Bull", bull), ("Bear", bear)]:
    for nm in strats:
        rlr = full_lr[nm][rmask]
        sh = np.mean(rlr)/np.std(rlr, ddof=0)*np.sqrt(ANN) if len(rlr) > 10 and np.std(rlr, ddof=0)>0 else 0
        regime_rows.append(dict(regime=rname, strategy=nm, sharpe=sh, n_bars=int(rmask.sum())))
        if nm != "Benchmark":
            print(f"    {rname:4s} {nm}: Sharpe={sh:.3f}  ({int(rmask.sum())} bars)")

# ── 8d. Year-by-Year ─────────────────────────────────────────────────
print("\n  --- 8d. Year-by-Year Performance ---")
yr_labels = pd.to_datetime(timestamps[1:]).year
years_uniq = sorted(set(yr_labels))
yearly_rows = []
for year in years_uniq:
    ymask = yr_labels == year
    for nm in strats:
        ylr = full_lr[nm][ymask]
        if len(ylr) < 10:
            continue
        sh = np.mean(ylr)/np.std(ylr, ddof=0)*np.sqrt(ANN) if np.std(ylr, ddof=0)>0 else 0
        # Approximate annual CAGR from log returns
        cum_ret = np.exp(np.sum(ylr)) - 1
        nt = sum(1 for t in full_tr[nm] if pd.Timestamp(timestamps[t["entry_bar"]]).year == year)
        yearly_rows.append(dict(year=year, strategy=nm, sharpe=sh, annual_ret=cum_ret, n_trades=nt))

yearly_df = pd.DataFrame(yearly_rows)
yearly_df.to_csv(os.path.join(TBL_DIR, "Tbl_yearly_performance.csv"), index=False)

for c in ["Cand01", "Cand02", "Cand03"]:
    sub = yearly_df[yearly_df.strategy == c]
    cat = sub[sub.annual_ret < -0.30]
    print(f"    {c}: catastrophic years (ret<-30%): {len(cat)} "
          f"({list(cat['year'].values) if len(cat)>0 else 'none'})")
    for _, r in sub.iterrows():
        print(f"      {r['year']}: Sh={r['sharpe']:.3f}  Ret={r['annual_ret']:.1%}  trades={r['n_trades']}")
print("  Saved Tbl_yearly_performance")

# ══════════════════════════════════════════════════════════════════════
# SECTION 9: SHARPE ATTRIBUTION
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 9: SHARPE ATTRIBUTION")
print("=" * 70)

# OLS betas from Phase 3 Tbl_sharpe_drivers
betas = dict(avg_loser=20.295, avg_hold=0.004, n_trades=-0.002,
             exposure=0.824, win_rate=1.556, churn_rate=-0.089)

attr_rows = []
bm = full_m["Benchmark"]
for c in ["Cand01", "Cand02", "Cand03"]:
    cm = full_m[c]
    dsh = cm["sharpe"] - bm["sharpe"]
    print(f"\n  {c} vs Benchmark: ΔSharpe = {dsh:+.3f}")
    print(f"    {'Property':15s} {'Cand':>10s} {'Bench':>10s} {'Delta':>10s} {'Impact':>10s}")
    total = 0
    for prop, beta in betas.items():
        cv = cm[prop]; bv = bm[prop]; delta = cv - bv; impact = beta * delta
        total += impact
        print(f"    {prop:15s} {cv:10.4f} {bv:10.4f} {delta:+10.4f} {impact:+10.4f}")
        attr_rows.append(dict(candidate=c, property=prop, cand_val=cv,
                              bench_val=bv, delta=delta, est_impact=impact))
    print(f"    {'TOTAL EXPLAINED':15s} {'':>10s} {'':>10s} {'':>10s} {total:+10.4f}")
    print(f"    {'ACTUAL ΔSharpe':15s} {'':>10s} {'':>10s} {'':>10s} {dsh:+10.4f}")
    print(f"    {'RESIDUAL':15s} {'':>10s} {'':>10s} {'':>10s} {dsh-total:+10.4f}")

    # Determine dominant driver
    max_prop = max(betas.keys(), key=lambda p: abs(betas[p] * (cm[p] - bm[p])))
    direction = "better" if betas[max_prop] * (cm[max_prop] - bm[max_prop]) > 0 else "worse"
    print(f"    Conclusion: {c} {'beats' if dsh>0 else 'trails'} benchmark mainly due to {max_prop} ({direction})")

pd.DataFrame(attr_rows).to_csv(os.path.join(TBL_DIR, "Tbl_sharpe_attribution.csv"), index=False)
print("  Saved Tbl_sharpe_attribution")

# ══════════════════════════════════════════════════════════════════════
# SECTION 10: VERDICTS
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SECTION 10: VERDICTS")
print("=" * 70)

verdicts = {}
for c in ["Cand01", "Cand02", "Cand03"]:
    m = full_m[c]; bs = bs_res[c]
    gates = OrderedDict()

    # G1-G4: Full-sample rejection
    gates["G1 Sharpe>0"] = m["sharpe"] > 0
    gates["G2 Sharpe>=0.80*bench"] = m["sharpe"] >= bench_sh * 0.80
    gates["G3 MDD<=75%"] = abs(m["mdd"]) <= 0.75
    gates["G4 Trades>=15"] = m["n_trades"] >= 15

    # G5: WFO win rate >= 50%
    wr = sum(1 for d in wfo_deltas[c] if d > 0) / len(wfo_deltas[c])
    gates["G5 WFO>=50%"] = wr >= 0.50

    # G6: Bootstrap P(Sharpe>0) >= 70%
    gates["G6 Bootstrap>=70%"] = bs["p_pos"] >= 0.70

    # G7: Jackknife <= 1 negative fold
    neg = (jk_df[jk_df.strategy==c]["sharpe"] < 0).sum()
    gates["G7 JK<=1neg"] = neg <= 1

    # G8: No catastrophic year (ret < -30%)
    yc = yearly_df[yearly_df.strategy == c]
    gates["G8 NoCatastrophe"] = (yc["annual_ret"] < -0.30).sum() == 0

    # G9: Phase 5 hard constraints
    gates["G9 Phase5HC"] = all([m["avg_loser"]>=-0.08, m["avg_hold"]>=40,
                                30<=m["n_trades"]<=200, abs(m["mdd"])<=0.60])

    n_pass = sum(gates.values())
    n_total = len(gates)
    if n_pass == n_total:
        verdict = "PROMOTE"
    elif n_pass >= n_total - 2:
        verdict = "HOLD"
    else:
        verdict = "REJECT"
    verdicts[c] = verdict

    print(f"\n  {c}: {n_pass}/{n_total} gates  →  {verdict}")
    for g, ok in gates.items():
        print(f"    {g}: {'PASS' if ok else 'FAIL'}")

# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
elapsed = time.time() - t0_global
print(f"\n{'=' * 70}")
print(f"Phase 7 COMPLETE in {elapsed:.1f}s")
print(f"{'=' * 70}")
print(f"  Cand01: Sharpe={full_m['Cand01']['sharpe']:.3f}  →  {verdicts['Cand01']}")
print(f"  Cand02: Sharpe={full_m['Cand02']['sharpe']:.3f}  →  {verdicts['Cand02']}")
print(f"  Cand03: Sharpe={full_m['Cand03']['sharpe']:.3f}  →  {verdicts['Cand03']}")
print(f"  Benchmark: Sharpe={full_m['Benchmark']['sharpe']:.3f}")
print(f"  Figures: Fig14-Fig20 ({FIG_DIR}/)")
print(f"  Tables: 8 files ({TBL_DIR}/)")
print(f"{'=' * 70}")
