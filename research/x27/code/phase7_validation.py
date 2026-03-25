#!/usr/bin/env python3
"""
Phase 7: Validation — X27 Study
Implements, backtests, and validates 3 candidates + VTREND benchmark.
All strategies use binary position sizing for fair comparison.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import json
import warnings
warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════
# PATHS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════
ROOT = Path("/var/www/trading-bots/btc-spot-dev/research/x27")
DATA = Path("/var/www/trading-bots/btc-spot-dev/data")
FIGS = ROOT / "figures"; FIGS.mkdir(exist_ok=True)
TBLS = ROOT / "tables";  TBLS.mkdir(exist_ok=True)

COST_BPS = 50
COST_F   = COST_BPS / 10_000   # 0.005 per round-trip
WU       = 200                   # warmup bars
SEED     = 42


# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════
def load_data():
    h4 = pd.read_csv(DATA / "btcusdt_4h.csv")
    d1 = pd.read_csv(DATA / "btcusdt_1d.csv")
    for df in (h4, d1):
        df["dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df.sort_values("open_time", inplace=True)
        df.reset_index(drop=True, inplace=True)
    h4["log_ret"] = np.log(h4["close"] / h4["close"].shift(1))
    h4 = h4.iloc[1:].reset_index(drop=True)
    return h4, d1


# ═══════════════════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════════════════
def _ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty(len(series), dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


def _atr(high, low, close, period=20):
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full(len(tr), np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _robust_atr(high, low, close, period=20, cap_q=0.90, cap_lb=100):
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = tr.copy()
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    out = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        out[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            out[i] = (out[i - 1] * (period - 1) + tr_cap[i]) / period
    return out


def _vdo(close, high, low, volume, taker_buy, fast=12, slow=28):
    n = len(close)
    taker_sell = volume - taker_buy
    vdr = np.zeros(n)
    mask = volume > 0
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    return _ema(vdr, fast) - _ema(vdr, slow)


def _rolling_max(arr, window):
    """Max of preceding `window` bars (excludes current)."""
    return pd.Series(arr).rolling(window).max().shift(1).values


def _map_d1(h4, d1, d1_vals):
    """Map D1-level values to each H4 bar (last completed D1 bar)."""
    idx = np.searchsorted(d1["close_time"].values, h4["open_time"].values,
                          side="right") - 1
    idx = np.clip(idx, 0, len(d1) - 1)
    return d1_vals[idx]


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════
def simulate(can_enter, should_exit, C, lr, cost_f=COST_F, warmup=WU):
    n = len(C)
    trades, bar_ret = [], np.zeros(n)
    in_pos_arr = np.zeros(n, dtype=bool)
    in_pos = False
    entry_bar = -1
    peak_close = 0.0

    for i in range(warmup, n):
        if not in_pos:
            if can_enter(i):
                in_pos = True
                entry_bar = i
                peak_close = C[i]
        else:
            bar_ret[i] = lr[i]
            in_pos_arr[i] = True
            peak_close = max(peak_close, C[i])
            if should_exit(i, peak_close):
                bar_ret[i] -= cost_f
                trades.append({
                    "eb": entry_bar, "xb": i,
                    "ep": C[entry_bar], "xp": C[i],
                    "ret": C[i] / C[entry_bar] - 1 - cost_f,
                    "bars_held": i - entry_bar,
                })
                in_pos = False

    return trades, bar_ret, in_pos_arr


# ═══════════════════════════════════════════════════════════════════════
# STRATEGY BUILDERS
# ═══════════════════════════════════════════════════════════════════════
def build_cand01(C, H, L, lr, h4, d1, N=120, p=20, m=4.0,
                 cost_f=COST_F, warmup=WU):
    """Cand01: Breakout + ATR Trail."""
    rm = _rolling_max(H, N)
    at = _atr(H, L, C, p)
    def can_enter(i):
        return not (np.isnan(rm[i]) or np.isnan(at[i])) and C[i] > rm[i]
    def should_exit(i, pk):
        return np.isnan(at[i]) or C[i] <= pk - m * at[i]
    return simulate(can_enter, should_exit, C, lr, cost_f, warmup)


def build_cand02(C, H, L, lr, h4, d1, N=120, p=20, m=4.0, K=21,
                 cost_f=COST_F, warmup=WU):
    """Cand02: Breakout + ATR Trail + D1 EMA(K) Regime."""
    rm = _rolling_max(H, N)
    at = _atr(H, L, C, p)
    d1c = d1["close"].values.astype(float)
    d1e = _ema(d1c, K)
    reg = _map_d1(h4, d1, (d1c > d1e).astype(float))
    def can_enter(i):
        return (not (np.isnan(rm[i]) or np.isnan(at[i]))
                and C[i] > rm[i] and reg[i] > 0.5)
    def should_exit(i, pk):
        return np.isnan(at[i]) or C[i] <= pk - m * at[i]
    return simulate(can_enter, should_exit, C, lr, cost_f, warmup)


def build_cand03(C, H, L, lr, h4, d1, N_roc=40, tau=0.15, p=20, m=4.0,
                 cost_f=COST_F, warmup=WU):
    """Cand03: ROC Threshold + ATR Trail."""
    at = _atr(H, L, C, p)
    def can_enter(i):
        return (i >= N_roc and not np.isnan(at[i])
                and C[i] / C[i - N_roc] - 1 > tau)
    def should_exit(i, pk):
        return np.isnan(at[i]) or C[i] <= pk - m * at[i]
    return simulate(can_enter, should_exit, C, lr, cost_f, warmup)


def build_benchmark(C, H, L, lr, h4, d1, slow=120, trail_mult=3.0,
                    cost_f=COST_F, warmup=WU):
    """VTREND E5+EMA21D1 (binary sizing)."""
    fast = slow // 4
    Vol = h4["volume"].values.astype(float)
    TB  = h4["taker_buy_base_vol"].values.astype(float)
    ef  = _ema(C, fast)
    es  = _ema(C, slow)
    vd  = _vdo(C, H, L, Vol, TB)
    ra  = _robust_atr(H, L, C, 20)
    d1c = d1["close"].values.astype(float)
    d1e = _ema(d1c, 21)
    reg = _map_d1(h4, d1, (d1c > d1e).astype(float))

    def can_enter(i):
        return (not np.isnan(ra[i])
                and ef[i] > es[i] and vd[i] > 0.0 and reg[i] > 0.5)
    def should_exit(i, pk):
        if np.isnan(ra[i]):
            return True
        if C[i] <= pk - trail_mult * ra[i]:
            return True
        if ef[i] < es[i]:
            return True
        return False
    return simulate(can_enter, should_exit, C, lr, cost_f, warmup)


# ═══════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════
def compute_metrics(trades, bar_ret, in_pos_arr, n_bars, bpy, warmup=WU):
    r = bar_ret[warmup:]
    n_eval = len(r)
    years = n_eval / bpy

    sharpe = (np.mean(r) / np.std(r) * np.sqrt(bpy)
              if np.std(r) > 0 else 0.0)

    eq = np.exp(np.cumsum(r))
    cm = np.maximum.accumulate(eq)
    dd = (cm - eq) / cm
    mdd = float(np.max(dd) * 100) if len(dd) > 0 else 0.0

    fe = float(eq[-1]) if len(eq) > 0 else 1.0
    cagr = (fe ** (1.0 / years) - 1) * 100 if years > 0 and fe > 0 else 0.0
    calmar = cagr / mdd if mdd > 0 else float("inf")

    nt = len(trades)
    if nt > 0:
        rets = np.array([t["ret"] for t in trades])
        win_rate = float(np.mean(rets > 0) * 100)
        w = rets[rets > 0]; l = rets[rets < 0]
        avg_w = float(np.mean(w) * 100) if len(w) > 0 else 0.0
        avg_l = float(np.mean(l) * 100) if len(l) > 0 else 0.0
        pf = float(np.sum(w) / -np.sum(l)) if len(l) > 0 and np.sum(l) != 0 else float("inf")
        # max consecutive losses
        mc, cur = 0, 0
        for x in (rets < 0):
            if x: cur += 1; mc = max(mc, cur)
            else: cur = 0
        avg_hold = float(np.mean([t["bars_held"] for t in trades]))
    else:
        win_rate = avg_w = avg_l = pf = avg_hold = 0.0
        mc = 0

    exposure = float(np.mean(in_pos_arr[warmup:]) * 100)

    return {
        "sharpe": round(sharpe, 4), "cagr": round(cagr, 2),
        "mdd": round(mdd, 2), "calmar": round(calmar, 4),
        "n_trades": nt, "win_rate": round(win_rate, 1),
        "exposure": round(exposure, 1), "avg_hold": round(avg_hold, 1),
        "max_consec_loss": mc, "profit_factor": round(pf, 3),
        "avg_winner": round(avg_w, 2), "avg_loser": round(avg_l, 2),
    }


def metrics_range(bar_ret, bpy, start, end):
    r = bar_ret[start:end]
    if len(r) == 0 or np.std(r) == 0:
        return {"sharpe": 0.0, "cagr": 0.0, "mdd": 0.0}
    sh = np.mean(r) / np.std(r) * np.sqrt(bpy)
    eq = np.exp(np.cumsum(r))
    cm = np.maximum.accumulate(eq)
    mdd = float(np.max((cm - eq) / cm) * 100)
    yrs = len(r) / bpy
    cagr = (eq[-1] ** (1.0 / yrs) - 1) * 100 if yrs > 0 and eq[-1] > 0 else 0
    return {"sharpe": round(sh, 4), "cagr": round(cagr, 2), "mdd": round(mdd, 2)}


# ═══════════════════════════════════════════════════════════════════════
# WALK-FORWARD (4 folds, anchored expanding, fixed params)
# ═══════════════════════════════════════════════════════════════════════
def run_wfo(br_c, br_b, trades_c, nb, bpy, warmup=WU, nf=4):
    n_eval = nb - warmup
    seg = n_eval // (nf + 1)
    rows = []
    for k in range(nf):
        os_s = warmup + (k + 1) * seg
        os_e = warmup + (k + 2) * seg if k < nf - 1 else nb
        is_c = metrics_range(br_c, bpy, warmup, os_s)
        is_b = metrics_range(br_b, bpy, warmup, os_s)
        oo_c = metrics_range(br_c, bpy, os_s, os_e)
        oo_b = metrics_range(br_b, bpy, os_s, os_e)
        oo_trades = sum(1 for t in trades_c if os_s <= t["xb"] < os_e)
        delta = oo_c["sharpe"] - oo_b["sharpe"]
        rows.append({
            "fold": k + 1,
            "is_sh_cand": is_c["sharpe"], "is_sh_bench": is_b["sharpe"],
            "oos_sh_cand": oo_c["sharpe"], "oos_sh_bench": oo_b["sharpe"],
            "oos_delta": round(delta, 4), "oos_trades": oo_trades,
        })
    wr = sum(1 for r in rows if r["oos_delta"] > 0) / len(rows)
    return rows, wr


# ═══════════════════════════════════════════════════════════════════════
# BOOTSTRAP (paired circular block, 2000 paths)
# ═══════════════════════════════════════════════════════════════════════
def bootstrap(rc, rb, bpy, n_paths=2000, blk=None, seed=SEED):
    n = len(rc)
    if blk is None:
        blk = max(10, int(np.sqrt(n)))
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blk))
    ann = np.sqrt(bpy)
    off = np.arange(blk)
    sh_c = np.empty(n_paths)
    sh_b = np.empty(n_paths)

    for p in range(n_paths):
        starts = rng.integers(0, n, size=nb)
        idx = np.concatenate([(s + off) % n for s in starts])[:n]
        pc, pb = rc[idx], rb[idx]
        sc, sb = np.std(pc), np.std(pb)
        sh_c[p] = np.mean(pc) / sc * ann if sc > 0 else 0
        sh_b[p] = np.mean(pb) / sb * ann if sb > 0 else 0

    d = sh_c - sh_b
    return {
        "p_cand_pos": float(np.mean(sh_c > 0)),
        "p_d_pos": float(np.mean(d > 0)),
        "median_d": float(np.median(d)),
        "p5_d": float(np.percentile(d, 5)),
        "p95_d": float(np.percentile(d, 95)),
        "sh_cand": sh_c, "sh_bench": sh_b, "d_sharpe": d,
    }


# ═══════════════════════════════════════════════════════════════════════
# ROBUSTNESS
# ═══════════════════════════════════════════════════════════════════════
def jackknife(bar_ret, bpy, warmup=WU, nf=6):
    r = bar_ret[warmup:]
    n = len(r); seg = n // nf
    rows = []
    for k in range(nf):
        s, e = k * seg, (k + 1) * seg if k < nf - 1 else n
        rk = np.concatenate([r[:s], r[e:]])
        sh = np.mean(rk) / np.std(rk) * np.sqrt(bpy) if np.std(rk) > 0 else 0
        eq = np.exp(np.cumsum(rk))
        cm = np.maximum.accumulate(eq)
        mdd = float(np.max((cm - eq) / cm) * 100)
        yrs = len(rk) / bpy
        cagr = (eq[-1] ** (1.0 / yrs) - 1) * 100 if yrs > 0 and eq[-1] > 0 else 0
        rows.append({"fold": k + 1, "sharpe": round(sh, 4),
                     "cagr": round(cagr, 2), "mdd": round(mdd, 2)})
    return rows


def cost_sweep(C, H, L, lr, h4, d1, fn, name, bpy,
               costs=(15, 30, 50, 75, 100)):
    rows = []
    for c in costs:
        cf = c / 10_000
        tr, br, ip = fn(C, H, L, lr, h4, d1, cost_f=cf, warmup=WU)
        m = compute_metrics(tr, br, ip, len(C), bpy)
        m["cost_bps"] = c; m["strategy"] = name
        rows.append(m)
    return rows


def yearly_perf(bar_ret, h4_dt, bpy, warmup=WU):
    r = bar_ret[warmup:]
    dt = h4_dt[warmup:]
    years = pd.DatetimeIndex(dt).year
    rows = []
    for yr in sorted(years.unique()):
        mask = years == yr
        ry = r[mask]; n = len(ry)
        if n == 0 or np.std(ry) == 0:
            rows.append({"year": yr, "sharpe": 0.0, "cagr": 0.0, "mdd": 0.0})
            continue
        sh = np.mean(ry) / np.std(ry) * np.sqrt(bpy)
        eq = np.exp(np.cumsum(ry))
        cm = np.maximum.accumulate(eq)
        mdd = float(np.max((cm - eq) / cm) * 100)
        yrs = n / bpy
        cagr = (eq[-1] ** (1.0 / yrs) - 1) * 100 if yrs > 0 and eq[-1] > 0 else 0
        rows.append({"year": yr, "sharpe": round(sh, 4),
                     "cagr": round(cagr, 2), "mdd": round(mdd, 2)})
    return rows


def regime_split(bar_ret, d1, h4, bpy, warmup=WU):
    d1c = d1["close"].values.astype(float)
    sma200 = pd.Series(d1c).rolling(200, min_periods=200).mean().values
    bull_d1 = d1c > sma200
    bull_h4 = _map_d1(h4, d1, bull_d1.astype(float)) > 0.5
    r = bar_ret[warmup:]
    bh = bull_h4[warmup:]
    res = {}
    for regime, val in [("bull", True), ("bear", False)]:
        mask = bh == val
        ry = r[mask]
        if len(ry) == 0 or np.std(ry) == 0:
            res[regime] = {"sharpe": 0.0, "mdd": 0.0,
                           "bars": int(mask.sum()), "frac": round(mask.mean()*100, 1)}
            continue
        sh = np.mean(ry) / np.std(ry) * np.sqrt(bpy)
        eq = np.exp(np.cumsum(ry))
        cm = np.maximum.accumulate(eq)
        mdd = float(np.max((cm - eq) / cm) * 100)
        res[regime] = {"sharpe": round(sh, 4), "mdd": round(mdd, 2),
                       "bars": int(mask.sum()), "frac": round(mask.mean()*100, 1)}
    return res


# ═══════════════════════════════════════════════════════════════════════
# CHURN
# ═══════════════════════════════════════════════════════════════════════
def churn_analysis(trades, window=10):
    if len(trades) < 2:
        return {"churn_events": 0, "churn_rate": 0.0, "churn_cost_pct": 0.0,
                "n_trades": len(trades)}
    ch = sum(1 for i in range(1, len(trades))
             if trades[i]["eb"] - trades[i-1]["xb"] <= window)
    return {
        "churn_events": ch,
        "churn_rate": round(ch / (len(trades) - 1) * 100, 1),
        "churn_cost_pct": round(ch * COST_F * 100, 2),
        "n_trades": len(trades),
    }


# ═══════════════════════════════════════════════════════════════════════
# PLOTTING
# ═══════════════════════════════════════════════════════════════════════
CLR = {"Cand01": "#1f77b4", "Cand02": "#ff7f0e",
       "Cand03": "#2ca02c", "Benchmark": "#d62728"}


def plot_equity(res, dt, wu=WU):
    fig, ax = plt.subplots(figsize=(14, 7))
    for nm, d in res.items():
        eq = np.exp(np.cumsum(d["bar_ret"][wu:]))
        ax.plot(dt[wu:], eq, label=nm, color=CLR.get(nm, "gray"), alpha=0.8)
    ax.set_yscale("log"); ax.set_xlabel("Date"); ax.set_ylabel("Equity (log)")
    ax.set_title("Fig14: Equity Curves — Candidates vs Benchmark")
    ax.legend(); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "Fig14_equity_curves.png", dpi=150)
    plt.close(fig)


def plot_drawdown(res, dt, wu=WU):
    fig, ax = plt.subplots(figsize=(14, 5))
    for nm, d in res.items():
        eq = np.exp(np.cumsum(d["bar_ret"][wu:]))
        cm = np.maximum.accumulate(eq)
        dd = (cm - eq) / cm * 100
        ax.fill_between(dt[wu:], -dd, 0, alpha=0.15, color=CLR.get(nm))
        ax.plot(dt[wu:], -dd, label=nm, color=CLR.get(nm), alpha=0.7, lw=0.8)
    ax.set_xlabel("Date"); ax.set_ylabel("Drawdown (%)")
    ax.set_title("Fig15: Drawdown — Candidates vs Benchmark")
    ax.legend(); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "Fig15_drawdown.png", dpi=150)
    plt.close(fig)


def plot_monthly(bar_ret, dt, name, wu=WU):
    r = bar_ret[wu:]; t = dt[wu:]
    df = pd.DataFrame({"dt": t, "ret": r})
    df["year"] = pd.DatetimeIndex(df["dt"]).year
    df["month"] = pd.DatetimeIndex(df["dt"]).month
    m = df.groupby(["year", "month"])["ret"].sum()
    m = (np.exp(m) - 1) * 100
    m = m.unstack(level="month").fillna(0)
    fig, ax = plt.subplots(figsize=(14, 6))
    im = ax.imshow(m.values, cmap="RdYlGn", aspect="auto", vmin=-30, vmax=30)
    ax.set_xticks(range(len(m.columns)))
    ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun",
                        "Jul","Aug","Sep","Oct","Nov","Dec"][:len(m.columns)])
    ax.set_yticks(range(len(m.index)))
    ax.set_yticklabels(m.index)
    plt.colorbar(im, ax=ax, label="Return (%)")
    ax.set_title(f"Fig16: Monthly Returns — {name}")
    fig.tight_layout(); fig.savefig(FIGS / f"Fig16_monthly_{name}.png", dpi=150)
    plt.close(fig)


def plot_trades(res):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for idx, (nm, d) in enumerate(res.items()):
        ax = axes.flat[idx]
        rets = [t["ret"] * 100 for t in d["trades"]]
        if rets:
            ax.hist(rets, bins=30, color=CLR.get(nm), alpha=0.7,
                    edgecolor="black", lw=0.5)
            ax.axvline(0, color="red", ls="--", lw=1)
            ax.axvline(np.mean(rets), color="blue", ls="--", lw=1,
                       label=f"Mean: {np.mean(rets):.1f}%")
        ax.set_title(f"{nm} ({len(rets)} trades)"); ax.set_xlabel("Return (%)")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.suptitle("Fig17: Trade Return Distributions", fontsize=13)
    fig.tight_layout(); fig.savefig(FIGS / "Fig17_trade_distribution.png", dpi=150)
    plt.close(fig)


def plot_wfo(wfo):
    nms = list(wfo.keys())
    nf = len(wfo[nms[0]])
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(nf); w = 0.25
    for j, nm in enumerate(nms):
        ds = [r["oos_delta"] for r in wfo[nm]]
        ax.bar(x + (j - len(nms)/2 + 0.5) * w, ds, w,
               label=nm, color=CLR.get(nm), alpha=0.8)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Fold"); ax.set_ylabel("ΔSharpe (OOS vs Bench)")
    ax.set_title("Fig18: Walk-Forward Per-Fold ΔSharpe")
    ax.set_xticks(x); ax.set_xticklabels([f"Fold {i+1}" for i in range(nf)])
    ax.legend(); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "Fig18_wfo_deltas.png", dpi=150)
    plt.close(fig)


def plot_bootstrap(bs):
    nms = list(bs.keys()); n = len(nms)
    fig, axes = plt.subplots(1, n, figsize=(5*n, 5))
    if n == 1: axes = [axes]
    for j, nm in enumerate(nms):
        ax = axes[j]; d = bs[nm]["d_sharpe"]
        ax.hist(d, bins=50, color=CLR.get(nm), alpha=0.7,
                edgecolor="black", lw=0.5)
        ax.axvline(0, color="red", lw=1.5, ls="--")
        ax.axvline(np.median(d), color="blue", lw=1.5,
                   label=f"Med: {np.median(d):.3f}")
        ax.set_title(f"{nm}\nP(Δ>0) = {np.mean(d>0)*100:.1f}%")
        ax.set_xlabel("ΔSharpe"); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.suptitle("Fig19: Bootstrap ΔSharpe (n=2000)", fontsize=13)
    fig.tight_layout(); fig.savefig(FIGS / "Fig19_bootstrap.png", dpi=150)
    plt.close(fig)


def plot_cost(cs):
    fig, ax = plt.subplots(figsize=(10, 6))
    for nm, data in cs.items():
        costs = [r["cost_bps"] for r in data]
        shs = [r["sharpe"] for r in data]
        ax.plot(costs, shs, "o-", label=nm, color=CLR.get(nm), lw=2, ms=6)
    ax.axhline(0, color="red", ls="--", lw=1, label="Sharpe=0")
    ax.set_xlabel("Cost (bps RT)"); ax.set_ylabel("Sharpe")
    ax.set_title("Fig20: Sharpe vs Transaction Cost")
    ax.legend(); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "Fig20_cost_sensitivity.png", dpi=150)
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════
# REJECTION CRITERIA & VERDICT
# ═══════════════════════════════════════════════════════════════════════
def check_rejection(m, wfo_wr, bs, bench_sh):
    cr = {}
    cr["R1"] = "PASS" if m["sharpe"] >= 0 else "FAIL"
    th2 = bench_sh * 0.80
    cr["R2"] = "PASS" if m["sharpe"] >= th2 else f"FAIL ({m['sharpe']:.3f}<{th2:.3f})"
    cr["R3"] = "PASS" if m["mdd"] <= 75 else f"FAIL (MDD={m['mdd']:.1f}%)"
    cr["R4"] = "PASS" if m["n_trades"] >= 15 else f"FAIL (n={m['n_trades']})"
    cr["R5"] = "PASS" if wfo_wr >= 0.50 else f"FAIL (WR={wfo_wr*100:.0f}%)"
    cr["R6"] = "PASS" if bs["p_cand_pos"] >= 0.60 else f"FAIL (P={bs['p_cand_pos']*100:.1f}%)"
    nf = sum(1 for v in cr.values() if "FAIL" in str(v))
    return cr, nf


def verdict(cr, nf, jk, yr):
    jk_neg = sum(1 for r in jk if r["sharpe"] < 0)
    catastrophic = any(r["cagr"] < -50 for r in yr)
    if nf == 0 and jk_neg <= 1 and not catastrophic:
        return "PROMOTE"
    elif nf <= 2 and jk_neg <= 2 and not catastrophic:
        return "HOLD"
    else:
        return "REJECT"


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("PHASE 7: VALIDATION — X27 Study")
    print("=" * 70)

    # ── Load ──
    print("\n[1] Loading data...")
    h4, d1 = load_data()
    C  = h4["close"].values.astype(float)
    H  = h4["high"].values.astype(float)
    L  = h4["low"].values.astype(float)
    lr = h4["log_ret"].values.astype(float)
    dt = h4["dt"].values
    NB = len(C)
    T_YR = (h4["dt"].iloc[-1] - h4["dt"].iloc[0]).total_seconds() / (365.25 * 86400)
    BPY = NB / T_YR
    print(f"  H4={NB}, D1={len(d1)}, Years={T_YR:.2f}, BPY={BPY:.1f}")

    # ── Full-sample backtests ──
    print("\n[2] Full-sample backtests...")
    builders = {
        "Cand01": build_cand01,
        "Cand02": build_cand02,
        "Cand03": build_cand03,
        "Benchmark": build_benchmark,
    }
    res = {}
    for nm, fn in builders.items():
        tr, br, ip = fn(C, H, L, lr, h4, d1)
        m = compute_metrics(tr, br, ip, NB, BPY)
        res[nm] = {"trades": tr, "bar_ret": br, "in_pos": ip, "metrics": m}
        print(f"  {nm:12s}  Sh={m['sharpe']:.4f}  CAGR={m['cagr']:.1f}%  "
              f"MDD={m['mdd']:.1f}%  N={m['n_trades']}  "
              f"WR={m['win_rate']:.1f}%  Exp={m['exposure']:.1f}%  "
              f"Hold={m['avg_hold']:.0f}  PF={m['profit_factor']:.2f}")
    bench_sh = res["Benchmark"]["metrics"]["sharpe"]

    # ── Sanity checks ──
    print("\n[3] Sanity checks (trade count vs Phase 6 estimate ±30%)...")
    est = {"Cand01": (45, 65), "Cand02": (25, 40), "Cand03": (50, 80)}
    for nm in ["Cand01", "Cand02", "Cand03"]:
        n = res[nm]["metrics"]["n_trades"]
        lo, hi = est[nm]
        ok = int(lo * 0.7) <= n <= int(hi * 1.3)
        print(f"  {nm}: {n} trades (est {lo}-{hi}) → {'OK' if ok else 'WARN'}")

    # ── Full-sample table ──
    print("\n[4] Full-sample comparison table...")
    tbl = pd.DataFrame({nm: d["metrics"] for nm, d in res.items()}).T
    tbl.to_csv(TBLS / "Tbl_full_sample_comparison.csv")
    print(tbl.to_string())

    # ── WFO ──
    print("\n[5] Walk-Forward Optimization (4 folds, anchored expanding)...")
    wfo_res, wfo_wr = {}, {}
    for nm in ["Cand01", "Cand02", "Cand03"]:
        folds, wr = run_wfo(res[nm]["bar_ret"], res["Benchmark"]["bar_ret"],
                            res[nm]["trades"], NB, BPY)
        wfo_res[nm] = folds; wfo_wr[nm] = wr
        wins = sum(1 for f in folds if f["oos_delta"] > 0)
        print(f"  {nm}: WFO WR = {wr*100:.0f}% ({wins}/{len(folds)})")
        for f in folds:
            print(f"    F{f['fold']}: IS={f['is_sh_cand']:.3f}  "
                  f"OOS={f['oos_sh_cand']:.3f}  Δ={f['oos_delta']:+.4f}  "
                  f"trades={f['oos_trades']}")
    wfo_rows = []
    for nm, fl in wfo_res.items():
        for f in fl: wfo_rows.append({**f, "strategy": nm})
    pd.DataFrame(wfo_rows).to_csv(TBLS / "Tbl_wfo_results.csv", index=False)

    # ── Bootstrap ──
    print("\n[6] Bootstrap validation (2000 paths, circular block)...")
    bs_res = {}
    for nm in ["Cand01", "Cand02", "Cand03"]:
        b = bootstrap(res[nm]["bar_ret"][WU:], res["Benchmark"]["bar_ret"][WU:], BPY)
        bs_res[nm] = b
        print(f"  {nm}: P(Sh>0)={b['p_cand_pos']*100:.1f}%  "
              f"P(Δ>0)={b['p_d_pos']*100:.1f}%  "
              f"Med Δ={b['median_d']:.3f}  [{b['p5_d']:.3f}, {b['p95_d']:.3f}]")
    bs_tbl = [{"strategy": nm, "P_sh_pos": round(b["p_cand_pos"], 4),
               "P_delta_pos": round(b["p_d_pos"], 4),
               "median_delta": round(b["median_d"], 4),
               "p5_delta": round(b["p5_d"], 4),
               "p95_delta": round(b["p95_d"], 4)}
              for nm, b in bs_res.items()]
    pd.DataFrame(bs_tbl).to_csv(TBLS / "Tbl_bootstrap_summary.csv", index=False)

    # ── Jackknife ──
    print("\n[7] Jackknife (6 folds, chronological delete-one-block)...")
    jk_res = {}
    for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
        jk = jackknife(res[nm]["bar_ret"], BPY)
        jk_res[nm] = jk
        neg = sum(1 for r in jk if r["sharpe"] < 0)
        print(f"  {nm}: {neg}/6 neg-Sharpe")
        for r in jk:
            print(f"    F{r['fold']}: Sh={r['sharpe']:.4f}  "
                  f"CAGR={r['cagr']:.1f}%  MDD={r['mdd']:.1f}%")
    jk_rows = []
    for nm, fl in jk_res.items():
        for r in fl: jk_rows.append({**r, "strategy": nm})
    pd.DataFrame(jk_rows).to_csv(TBLS / "Tbl_jackknife.csv", index=False)

    # ── Cost sensitivity ──
    print("\n[8] Cost sensitivity (15, 30, 50, 75, 100 bps)...")
    cs_res = {}
    for nm, fn in builders.items():
        cs = cost_sweep(C, H, L, lr, h4, d1, fn, nm, BPY)
        cs_res[nm] = cs
        for r in cs:
            print(f"  {nm:12s} @ {r['cost_bps']:3d}: Sh={r['sharpe']:.4f}  "
                  f"CAGR={r['cagr']:.1f}%  MDD={r['mdd']:.1f}%")
    cs_rows = []
    for nm, data in cs_res.items(): cs_rows.extend(data)
    pd.DataFrame(cs_rows).to_csv(TBLS / "Tbl_cost_sensitivity.csv", index=False)

    # ── Regime split ──
    print("\n[9] Regime split (D1 SMA200 bull/bear)...")
    reg_res = {}
    for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
        rs = regime_split(res[nm]["bar_ret"], d1, h4, BPY)
        reg_res[nm] = rs
        for reg, d in rs.items():
            print(f"  {nm:12s} {reg:5s}: Sh={d['sharpe']:.4f}  "
                  f"MDD={d['mdd']:.1f}%  ({d['frac']:.1f}%)")

    # ── Year-by-year ──
    print("\n[10] Year-by-year performance...")
    yr_res = {}
    for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
        yr = yearly_perf(res[nm]["bar_ret"], dt, BPY)
        yr_res[nm] = yr
    # Print table header
    header = f"  {'Year':>6s}"
    for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
        header += f"  {nm:>12s}"
    print(header)
    all_years = sorted({r["year"] for yl in yr_res.values() for r in yl})
    for y in all_years:
        line = f"  {y:>6d}"
        for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
            yd = [r for r in yr_res[nm] if r["year"] == y]
            line += f"  {yd[0]['sharpe']:>12.3f}" if yd else f"  {'N/A':>12s}"
        print(line)
    yr_rows = []
    for nm, yl in yr_res.items():
        for r in yl: yr_rows.append({**r, "strategy": nm})
    pd.DataFrame(yr_rows).to_csv(TBLS / "Tbl_yearly_performance.csv", index=False)

    # ── Churn ──
    print("\n[11] Churn analysis (window=10 bars)...")
    ch_res = {}
    for nm in ["Cand01", "Cand02", "Cand03", "Benchmark"]:
        ch = churn_analysis(res[nm]["trades"])
        ch_res[nm] = ch
        print(f"  {nm:12s}: {ch['churn_events']}/{ch['n_trades']} trades "
              f"({ch['churn_rate']:.1f}%) cost={ch['churn_cost_pct']:.2f}%")
    pd.DataFrame([{"strategy": k, **v} for k, v in ch_res.items()]).to_csv(
        TBLS / "Tbl_churn_comparison.csv", index=False)

    # ── Plots ──
    print("\n[12] Generating figures...")
    plot_equity(res, dt)
    plot_drawdown(res, dt)
    best = max(["Cand01", "Cand02", "Cand03"],
               key=lambda n: res[n]["metrics"]["sharpe"])
    plot_monthly(res[best]["bar_ret"], dt, best)
    plot_trades(res)
    plot_wfo(wfo_res)
    plot_bootstrap(bs_res)
    plot_cost(cs_res)
    print(f"  7 figures saved to {FIGS}")

    # ── Verdicts ──
    print("\n" + "=" * 70)
    print("VERDICTS")
    print("=" * 70)
    verdicts = {}
    for nm in ["Cand01", "Cand02", "Cand03"]:
        cr, nf = check_rejection(res[nm]["metrics"], wfo_wr[nm],
                                 bs_res[nm], bench_sh)
        v = verdict(cr, nf, jk_res[nm], yr_res[nm])
        jn = sum(1 for r in jk_res[nm] if r["sharpe"] < 0)
        cat = any(r["cagr"] < -50 for r in yr_res[nm])
        verdicts[nm] = {"verdict": v, "criteria": cr, "n_fail": nf,
                        "jk_neg": jn, "catastrophic": cat}
        print(f"\n  {nm}: *** {v} ***")
        for k, val in cr.items():
            print(f"    {k}: {val}")
        print(f"    Jackknife: {jn}/6 neg ({'PASS' if jn <= 1 else 'FAIL'})")
        print(f"    Catastrophic year: {'YES' if cat else 'No'}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n  Benchmark (binary): Sharpe = {bench_sh:.4f}")
    for nm in ["Cand01", "Cand02", "Cand03"]:
        m = res[nm]["metrics"]
        v = verdicts[nm]["verdict"]
        d = m["sharpe"] - bench_sh
        print(f"  {nm}: Sh={m['sharpe']:.4f} (Δ={d:+.4f}), "
              f"CAGR={m['cagr']:.1f}%, MDD={m['mdd']:.1f}% → {v}")

    # ── Save results JSON ──
    summary = {
        "benchmark_binary_sharpe": bench_sh,
        "candidates": {
            nm: {
                "metrics": res[nm]["metrics"],
                "wfo_win_rate": wfo_wr[nm],
                "bootstrap": {k: v for k, v in bs_res[nm].items()
                              if k not in ("sh_cand", "sh_bench", "d_sharpe")},
                "churn": ch_res[nm],
                "verdict": verdicts[nm]["verdict"],
                "rejection_criteria": verdicts[nm]["criteria"],
            }
            for nm in ["Cand01", "Cand02", "Cand03"]
        },
    }
    with open(ROOT / "phase7_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results JSON: {ROOT / 'phase7_results.json'}")
    print(f"  Tables: {len(list(TBLS.glob('Tbl_*')))} files")
    print(f"  Figures: {len(list(FIGS.glob('Fig1[4-9]*')) + list(FIGS.glob('Fig2*')))} files")

    return res, verdicts


if __name__ == "__main__":
    main()
