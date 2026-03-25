#!/usr/bin/env python3
"""
Phase 3: Signal Landscape EDA — X27 Research
Survey entry and exit signal TYPES across parameter sweeps.
Measure average metrics per type. Describe landscape, do NOT recommend.
"""
import json, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from itertools import product

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────
DATA = Path("/var/www/trading-bots/btc-spot-dev/data")
OUT  = Path("/var/www/trading-bots/btc-spot-dev/research/x27")
FIG  = OUT / "figures"; FIG.mkdir(exist_ok=True)
TBL  = OUT / "tables";  TBL.mkdir(exist_ok=True)

# ── Load ──────────────────────────────────────────────────────
print("Loading data...")
h4 = pd.read_csv(DATA / "btcusdt_4h.csv").sort_values("open_time").reset_index(drop=True)
h4["dt"] = pd.to_datetime(h4["open_time"], unit="ms", utc=True)
d1 = pd.read_csv(DATA / "btcusdt_1d.csv").sort_values("open_time").reset_index(drop=True)
d1["dt"] = pd.to_datetime(d1["open_time"], unit="ms", utc=True)

C = h4["close"].values.astype(float)
Hi = h4["high"].values.astype(float)
Lo = h4["low"].values.astype(float)
NB = len(C)
T_YR = (h4["dt"].iloc[-1] - h4["dt"].iloc[0]).total_seconds() / (365.25 * 86400)
BPY = NB / T_YR
WU = 200
COST_BPS = 50
COST_F = COST_BPS / 10000
print(f"H4: {NB} bars, {T_YR:.2f}yr, {BPY:.0f} bars/yr")

# ── Observation logger ────────────────────────────────────────
obs_log = []; _oid = [40]
def obs(txt, ev):
    o = f"Obs{_oid[0]:02d}"; _oid[0] += 1
    obs_log.append({"id": o, "text": txt, "evidence": ev})
    print(f"  {o}: {txt[:150]}"); return o

# ── Precompute ────────────────────────────────────────────────
print("\nPrecomputing indicators...")
lr = np.zeros(NB); lr[1:] = np.log(C[1:] / C[:-1])

# EMA cache
Ec = {}
for s in [5, 10, 20, 30, 50, 80, 120, 160, 200]:
    Ec[s] = pd.Series(C).ewm(span=s, adjust=False).mean().values

# Rolling max of high (previous N bars, excluding current)
RMX = {}
for n in [20, 40, 60, 80, 120, 160]:
    RMX[n] = pd.Series(Hi).shift(1).rolling(n, min_periods=n).max().values

# Rolling min of low (previous N bars)
RMN = {}
for n in [20, 40, 60, 80]:
    RMN[n] = pd.Series(Lo).shift(1).rolling(n, min_periods=n).min().values

# ROC cache
ROCc = {}
for n in [10, 20, 40, 60]:
    r = np.full(NB, np.nan); r[n:] = C[n:] / C[:-n] - 1; ROCc[n] = r

# SMA cache
SMAc = {}
for n in [20, 40, 60, 200]:
    SMAc[n] = pd.Series(C).rolling(n, min_periods=n).mean().values

# ATR (Wilder smoothing)
def _atr(h, l, c, p):
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    tr = np.concatenate([[h[0] - l[0]], tr])
    a = np.full_like(tr, np.nan); a[p - 1] = np.mean(tr[:p])
    for i in range(p, len(tr)):
        a[i] = (a[i - 1] * (p - 1) + tr[i]) / p
    return a

ATRc = {}
for p in [14, 20, 30, 40, 60]:
    ATRc[p] = _atr(Hi, Lo, C, p)

# Realized volatility
RV20 = pd.Series(lr).rolling(20, min_periods=20).std().values
RV100 = pd.Series(RV20).rolling(100, min_periods=50).mean().values

# D1 regime → H4 mapping
d1c = d1["close"].values.astype(float)
d1s200 = pd.Series(d1c).rolling(200, min_periods=200).mean().values
d1_bull = d1c > d1s200
d1_ot = d1["open_time"].values; h4_ot = h4["open_time"].values
DAY_MS = 86400 * 1000
d1i = np.searchsorted(d1_ot, h4_ot - DAY_MS, side="right") - 1
d1i_c = np.clip(d1i, 0, len(d1_bull) - 1)
REG = np.where((d1i >= 0) & (d1i < len(d1_bull)) & (~np.isnan(d1s200[d1i_c])),
               d1_bull[d1i_c].astype(int), -1)
print(f"  D1 regime mapped: Bull={np.sum(REG == 1)}, Bear={np.sum(REG == 0)}, Undef={np.sum(REG == -1)}")
print("  Precomputation complete.")


# ═══════════════════════════════════════════════════════════════
# 1. TARGET EVENT DEFINITION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. TARGET EVENT DEFINITION")
print("=" * 70)

def find_trends(px, thr_pct):
    """Find upward trends exceeding threshold (Phase 2 algorithm)."""
    lp = np.log(px); n = len(lp); out = []; i = 0
    while i < n - 1:
        s = i; tr = lp[s]; pk = tr; pi = s
        for j in range(s + 1, n):
            if lp[j] > pk: pk = lp[j]; pi = j
            cr = pk - tr; dd = pk - lp[j]
            if cr >= np.log(1 + thr_pct / 100):
                out.append({"start": s, "peak": pi, "dur": pi - s,
                            "mag": (np.exp(cr) - 1) * 100})
                i = pi + 1; break
            if dd > cr * 0.5 and cr > 0.01:
                i = j; break
        else:
            break
        if i == s: i += 1
    return out

evts = find_trends(C, 10)
print(f"Target events (≥10% upward move): {len(evts)}")
print(f"  Durations: mean={np.mean([e['dur'] for e in evts]):.1f}, "
      f"median={np.median([e['dur'] for e in evts]):.0f} bars")
print(f"  Magnitudes: mean={np.mean([e['mag'] for e in evts]):.1f}%, "
      f"median={np.median([e['mag'] for e in evts]):.1f}%")

# Target mask: bars that are within a target event
tmask = np.zeros(NB, dtype=bool)
for e in evts:
    tmask[e["start"]:e["peak"] + 1] = True

# Distribution over 4 time blocks
bb = np.linspace(0, NB, 5, dtype=int)
for b in range(4):
    be = [e for e in evts if bb[b] <= e["start"] < bb[b + 1]]
    d0 = h4["dt"].iloc[bb[b]].strftime("%Y-%m")
    d1x = h4["dt"].iloc[min(bb[b + 1] - 1, NB - 1)].strftime("%Y-%m")
    print(f"  Block {b + 1} ({d0} → {d1x}): {len(be)} events")

obs(f"Target events: {len(evts)} upward moves ≥10% in {T_YR:.1f}yr "
    f"({len(evts) / T_YR:.1f}/yr). Median dur={np.median([e['dur'] for e in evts]):.0f} bars, "
    f"median mag={np.median([e['mag'] for e in evts]):.1f}%.", "Tbl06")


# ═══════════════════════════════════════════════════════════════
# PART A: ENTRY SIGNAL LANDSCAPE
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PART A: ENTRY SIGNAL LANDSCAPE")
print("=" * 70)


def gen_A(f, sl):
    """Type A: EMA crossover — fast crosses above slow."""
    d = Ec[f] - Ec[sl]
    s = np.zeros(NB, dtype=bool)
    s[1:] = (d[1:] > 0) & (d[:-1] <= 0)
    s[:WU] = False
    return s


def gen_B(lb):
    """Type B: Breakout — close breaks above N-bar high."""
    rm = RMX[lb]
    ab = np.zeros(NB, dtype=bool)
    v = ~np.isnan(rm); ab[v] = C[v] > rm[v]
    s = np.zeros(NB, dtype=bool)
    s[1:] = ab[1:] & ~ab[:-1]
    s[:WU] = False
    return s


def gen_C(n, t):
    """Type C: ROC crosses above threshold."""
    roc = ROCc[n]
    thr = t / 100.0
    ab = np.zeros(NB, dtype=bool)
    v = ~np.isnan(roc); ab[v] = roc[v] > thr
    s = np.zeros(NB, dtype=bool)
    s[1:] = ab[1:] & ~ab[:-1]
    s[:WU] = False
    return s


def gen_D(lb, w):
    """Type D: Volatility breakout — close > SMA + width*ATR."""
    upper = SMAc[lb] + w * ATRc[lb]
    ab = np.zeros(NB, dtype=bool)
    v = ~np.isnan(upper); ab[v] = C[v] > upper[v]
    s = np.zeros(NB, dtype=bool)
    s[1:] = ab[1:] & ~ab[:-1]
    s[:WU] = False
    return s


def eval_entry(sigs):
    """Evaluate entry signals against target events."""
    sb = np.where(sigs)[0]
    ns = len(sb)
    if ns == 0:
        return {"det": 0.0, "fp": 1.0, "lag": np.nan, "slip": np.nan, "freq": 0.0}
    detected = 0; lags = []; slips = []
    for e in evts:
        iw = sb[(sb >= e["start"]) & (sb <= e["peak"])]
        if len(iw) > 0:
            detected += 1
            first = iw[0]
            lags.append(first - e["start"])
            slips.append((C[first] / C[e["start"]] - 1) * 100)
    fp_count = np.sum(~tmask[sb])
    return {
        "det": round(detected / len(evts), 4),
        "fp": round(fp_count / ns, 4),
        "lag": round(np.mean(lags), 2) if lags else np.nan,
        "slip": round(np.mean(slips), 2) if slips else np.nan,
        "freq": round(ns / T_YR, 2),
    }


# Sweep all entry types
erows = []
eargs = {}  # (type, param_name) -> generation args

print("  Sweeping Type A (EMA crossover)...")
for f, sl in product([5, 10, 20, 30], [50, 80, 120, 160, 200]):
    sigs = gen_A(f, sl)
    m = eval_entry(sigs)
    pn = f"f{f}_s{sl}"
    erows.append({"type": "A", "p": pn, **m})
    eargs[("A", pn)] = {"f": f, "sl": sl}

print("  Sweeping Type B (Breakout)...")
for lb in [20, 40, 60, 80, 120, 160]:
    sigs = gen_B(lb)
    m = eval_entry(sigs)
    pn = f"N{lb}"
    erows.append({"type": "B", "p": pn, **m})
    eargs[("B", pn)] = {"lb": lb}

print("  Sweeping Type C (ROC threshold)...")
for n, t in product([10, 20, 40, 60], [5, 10, 15, 20]):
    sigs = gen_C(n, t)
    m = eval_entry(sigs)
    pn = f"N{n}_t{t}"
    erows.append({"type": "C", "p": pn, **m})
    eargs[("C", pn)] = {"n": n, "t": t}

print("  Sweeping Type D (Volatility breakout)...")
for lb, w in product([20, 40, 60], [1.5, 2.0, 2.5, 3.0]):
    sigs = gen_D(lb, w)
    m = eval_entry(sigs)
    pn = f"lb{lb}_w{w}"
    erows.append({"type": "D", "p": pn, **m})
    eargs[("D", pn)] = {"lb": lb, "w": w}

print("  Type E (Volume-confirmed): SKIPPED — Phase 2 Obs30 confirmed H_prior_5")

edf = pd.DataFrame(erows)

# Summary by type
print("\n  Entry summary (type averages):")
esumm = edf.groupby("type")[["det", "fp", "lag", "slip", "freq"]].mean()
print(esumm.round(4).to_string())
esumm.round(4).to_csv(TBL / "Tbl07_entry_signals.csv")
edf.to_csv(TBL / "Tbl07_entry_detail.csv", index=False)
print("  Saved: Tbl07_entry_signals.csv, Tbl07_entry_detail.csv")

for t in ["A", "B", "C", "D"]:
    r = esumm.loc[t]
    obs(f"Entry Type {t}: det={r['det']:.3f}, FP={r['fp']:.3f}, lag={r['lag']:.1f}bars, "
        f"slip={r['slip']:.1f}%, freq={r['freq']:.0f}/yr",
        "Tbl07")

# ── Fig10: Entry Efficiency Frontier ──────────────────────────
print("\n  Plotting Fig10: Entry efficiency frontier...")
fig, ax = plt.subplots(figsize=(10, 7))
ecm = {"A": "tab:blue", "B": "tab:orange", "C": "tab:green", "D": "tab:red"}
enames = {"A": "EMA crossover", "B": "Breakout", "C": "ROC threshold", "D": "Vol breakout"}
for t in ["A", "B", "C", "D"]:
    sub = edf[edf["type"] == t]
    ax.scatter(sub["lag"], sub["fp"], c=ecm[t], label=f"Type {t}: {enames[t]}",
               alpha=0.6, s=50, edgecolors="k", lw=0.3)
# Type averages as large star markers
for t in ["A", "B", "C", "D"]:
    r = esumm.loc[t]
    ax.scatter(r["lag"], r["fp"], c=ecm[t], s=250, marker="*",
               edgecolors="k", lw=1, zorder=10)
ax.set_xlabel("Average Lag (H4 bars)", fontsize=12)
ax.set_ylabel("False Positive Rate", fontsize=12)
ax.set_title("Fig10: Entry Signal Efficiency Frontier\n(lower-left = better: low lag AND low false positives)", fontsize=13)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "Fig10_entry_efficiency_frontier.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: Fig10_entry_efficiency_frontier.png")

# ── Entry Robustness (4 time blocks) ─────────────────────────
print("\n  Entry robustness (4 time blocks)...")
rob_rows = []
for b in range(4):
    b_evts = [e for e in evts if bb[b] <= e["start"] < bb[b + 1]]
    b_mask = np.zeros(NB, dtype=bool)
    for e in b_evts:
        b_mask[e["start"]:e["peak"] + 1] = True
    if len(b_evts) == 0:
        continue

    for t, gen_fn, params_list in [
        ("A", gen_A, list(product([5, 10, 20, 30], [50, 80, 120, 160, 200]))),
        ("B", gen_B, [(lb,) for lb in [20, 40, 60, 80, 120, 160]]),
        ("C", gen_C, list(product([10, 20, 40, 60], [5, 10, 15, 20]))),
        ("D", gen_D, list(product([20, 40, 60], [1.5, 2.0, 2.5, 3.0]))),
    ]:
        dets, fps = [], []
        for params in params_list:
            sigs = gen_fn(*params)
            block_sigs = sigs.copy()
            block_sigs[:bb[b]] = False
            block_sigs[bb[b + 1]:] = False
            sb = np.where(block_sigs)[0]
            if len(sb) == 0:
                continue
            det_count = sum(1 for e in b_evts if np.any((sb >= e["start"]) & (sb <= e["peak"])))
            dets.append(det_count / len(b_evts))
            fps.append(np.sum(~b_mask[sb]) / len(sb))
        if dets:
            rob_rows.append({"type": t, "block": b + 1,
                             "det_mean": np.mean(dets), "fp_mean": np.mean(fps)})

rob_df = pd.DataFrame(rob_rows)
if len(rob_df) > 0:
    rob_pivot = rob_df.pivot_table(index="type", columns="block",
                                   values=["det_mean", "fp_mean"], aggfunc="mean")
    rob_std = rob_df.groupby("type").agg(
        det_std=("det_mean", "std"),
        fp_std=("fp_mean", "std"),
    ).round(4)
    print("  Robustness (std of detection rate across 4 blocks):")
    print(rob_std.to_string())
    most_stable = rob_std["det_std"].idxmin()
    least_stable = rob_std["det_std"].idxmax()
    obs(f"Entry robustness: Type {most_stable} most stable (det_std={rob_std.loc[most_stable, 'det_std']:.3f}), "
        f"Type {least_stable} least stable (det_std={rob_std.loc[least_stable, 'det_std']:.3f}).",
        "Tbl07, robustness analysis")


# ═══════════════════════════════════════════════════════════════
# PART B: EXIT SIGNAL LANDSCAPE
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PART B: EXIT SIGNAL LANDSCAPE")
print("=" * 70)

MAX_HOLD = 300


def sim_exit(ev, etype, ep):
    """Simulate exit on a single target event. Returns metrics dict or None."""
    s, pk = ev["start"], ev["peak"]
    ep_ = C[s]; pkp = C[pk]
    if pkp <= ep_ * 1.001:
        return None  # degenerate event

    rpk = ep_; mdd = 0.0; xbar = None
    lim = min(s + MAX_HOLD, NB)

    for i in range(s + 1, lim):
        if C[i] > rpk:
            rpk = C[i]
        dd = (rpk - C[i]) / rpk if rpk > 0 else 0
        if dd > mdd:
            mdd = dd

        hit = False
        if etype == "X":
            hit = C[i] < rpk * (1 - ep["trail"] / 100)
        elif etype == "Y":
            a = ATRc[ep["atr_p"]][i]
            if not np.isnan(a):
                hit = C[i] < rpk - ep["mult"] * a
        elif etype == "ZA":
            ef, es = Ec[ep["f"]], Ec[ep["sl"]]
            if i >= 1:
                hit = ef[i] < es[i] and ef[i - 1] >= es[i - 1]
        elif etype == "ZB":
            rm = RMN[ep["lb"]][i]
            if not np.isnan(rm):
                hit = C[i] < rm
        elif etype == "ZC":
            rv = ROCc[ep["n"]][i]
            if not np.isnan(rv):
                hit = rv < ep["thr"] / 100
        elif etype == "ZD":
            sv = SMAc[ep["lb"]][i]
            av = ATRc[ep["lb"]][i]
            if not np.isnan(sv) and not np.isnan(av):
                hit = C[i] < sv - ep["w"] * av
        elif etype == "W":
            hit = (i - s) >= ep["hold"]
        elif etype == "V":
            if not np.isnan(RV20[i]) and not np.isnan(RV100[i]) and RV100[i] > 0:
                if ep.get("mode") == "spike":
                    hit = RV20[i] > ep["K"] * RV100[i]
                else:
                    hit = RV20[i] < ep["K"] * RV100[i]

        if hit:
            xbar = i
            break

    if xbar is None:
        xbar = lim - 1

    xp = C[xbar]
    cap = (xp - ep_) / (pkp - ep_) if pkp != ep_ else 0
    hold = xbar - s
    ret = (xp / ep_ - 1 - COST_F) * 100

    # Churn: price exceeds exit price within 10 bars
    ce = min(xbar + 11, NB)
    churn = bool(ce > xbar + 1 and np.max(C[xbar + 1:ce]) > xp)

    return {"cap": cap, "churn": churn, "hold": hold, "ret": ret, "mdd": mdd * 100}


# Define exit parameter grid
exit_grid = []  # list of (type, param_name, params_dict)

# Type X: Fixed trailing stop
for tr in [3, 5, 8, 12, 15, 20]:
    exit_grid.append(("X", f"trail{tr}", {"trail": tr}))

# Type Y: ATR trailing stop
for ap, m in product([14, 20, 30], [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]):
    exit_grid.append(("Y", f"atr{ap}_m{m}", {"atr_p": ap, "mult": m}))

# Type ZA: EMA cross-down
for f, sl in product([10, 20, 30], [50, 80, 120]):
    exit_grid.append(("ZA", f"ema_f{f}_s{sl}", {"f": f, "sl": sl}))

# Type ZB: Break below N-bar low
for lb in [20, 40, 60, 80]:
    exit_grid.append(("ZB", f"low{lb}", {"lb": lb}))

# Type ZC: ROC drops below negative threshold
for n, t in product([10, 20, 40], [-5, -10, -15]):
    exit_grid.append(("ZC", f"roc{n}_t{t}", {"n": n, "thr": t}))

# Type ZD: Price below lower vol channel
for lb, w in product([20, 40, 60], [1.5, 2.0, 2.5]):
    exit_grid.append(("ZD", f"ch{lb}_w{w}", {"lb": lb, "w": w}))

# Type W: Time-based
for h in [20, 40, 60, 80, 120, 160, 200]:
    exit_grid.append(("W", f"hold{h}", {"hold": h}))

# Type V: Volatility-based
for K in [1.5, 2.0, 2.5, 3.0]:
    exit_grid.append(("V", f"spike_{K}", {"K": K, "mode": "spike"}))
for K in [0.3, 0.5]:
    exit_grid.append(("V", f"compress_{K}", {"K": K, "mode": "compress"}))

print(f"  Exit parameter grid: {len(exit_grid)} combos")

# Store exit params for Part C lookup
exit_params_map = {(et, pn): ep for et, pn, ep in exit_grid}

xrows = []
for etype, pname, ep in exit_grid:
    caps, churns, holds, rets, mdds = [], [], [], [], []
    for ev in evts:
        r = sim_exit(ev, etype, ep)
        if r is None:
            continue
        caps.append(r["cap"]); churns.append(r["churn"])
        holds.append(r["hold"]); rets.append(r["ret"])
        mdds.append(r["mdd"])
    if len(caps) == 0:
        continue
    xrows.append({
        "type": etype, "p": pname,
        "cap": round(np.mean(caps), 4),
        "churn": round(np.mean(churns), 4),
        "hold": round(np.mean(holds), 1),
        "ret": round(np.mean(rets), 2),
        "mdd": round(np.mean(mdds), 2),
    })

xdf = pd.DataFrame(xrows)
xdf["type_grp"] = xdf["type"].map(lambda t: "Z" if t.startswith("Z") else t)

print("\n  Exit summary (type-group averages):")
xsumm = xdf.groupby("type_grp")[["cap", "churn", "hold", "ret", "mdd"]].mean()
print(xsumm.round(4).to_string())
xsumm.round(4).to_csv(TBL / "Tbl08_exit_signals.csv")
xdf.to_csv(TBL / "Tbl08_exit_detail.csv", index=False)
print("  Saved: Tbl08_exit_signals.csv, Tbl08_exit_detail.csv")

for t in xsumm.index:
    r = xsumm.loc[t]
    obs(f"Exit Type {t}: cap={r['cap']:.3f}, churn={r['churn']:.3f}, "
        f"hold={r['hold']:.0f}bars, ret/trade={r['ret']:.1f}%, mdd={r['mdd']:.1f}%",
        "Tbl08")

# ── Fig11: Exit capture vs churn ──────────────────────────────
print("\n  Plotting Fig11: Exit capture vs churn...")
fig, ax = plt.subplots(figsize=(10, 7))
xcm = {"X": "tab:blue", "Y": "tab:orange", "Z": "tab:green", "W": "tab:red", "V": "tab:purple"}
xnames = {"X": "Fixed trail", "Y": "ATR trail", "Z": "Signal reversal",
          "W": "Time-based", "V": "Volatility-based"}
for tg in ["X", "Y", "Z", "W", "V"]:
    sub = xdf[xdf["type_grp"] == tg]
    if len(sub) > 0:
        ax.scatter(sub["cap"], sub["churn"], c=xcm[tg],
                   label=f"Type {tg}: {xnames[tg]}", alpha=0.6, s=50,
                   edgecolors="k", lw=0.3)
# Type averages as stars
for tg in xsumm.index:
    r = xsumm.loc[tg]
    ax.scatter(r["cap"], r["churn"], c=xcm[tg], s=250, marker="*",
               edgecolors="k", lw=1, zorder=10)
ax.set_xlabel("Capture Ratio (mean)", fontsize=12)
ax.set_ylabel("Churn Rate (mean)", fontsize=12)
ax.set_title("Fig11: Exit Efficiency Frontier — Capture vs Churn\n"
             "(upper-left = better: high capture AND low churn)", fontsize=13)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "Fig11_exit_capture_vs_churn.png", dpi=150, bbox_inches="tight")
plt.close()

# ── Fig12: Exit capture vs max drawdown ───────────────────────
print("  Plotting Fig12: Exit capture vs drawdown...")
fig, ax = plt.subplots(figsize=(10, 7))
for tg in ["X", "Y", "Z", "W", "V"]:
    sub = xdf[xdf["type_grp"] == tg]
    if len(sub) > 0:
        ax.scatter(sub["cap"], sub["mdd"], c=xcm[tg],
                   label=f"Type {tg}: {xnames[tg]}", alpha=0.6, s=50,
                   edgecolors="k", lw=0.3)
for tg in xsumm.index:
    r = xsumm.loc[tg]
    ax.scatter(r["cap"], r["mdd"], c=xcm[tg], s=250, marker="*",
               edgecolors="k", lw=1, zorder=10)
ax.set_xlabel("Capture Ratio (mean)", fontsize=12)
ax.set_ylabel("Max Drawdown during Hold (%, mean)", fontsize=12)
ax.set_title("Fig12: Exit Efficiency Frontier — Capture vs Drawdown\n"
             "(upper-left = better: high capture AND low drawdown)", fontsize=13)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(FIG / "Fig12_exit_capture_vs_drawdown.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: Fig11, Fig12")


# ═══════════════════════════════════════════════════════════════
# PART C: ENTRY × EXIT INTERACTION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PART C: ENTRY × EXIT INTERACTION")
print("=" * 70)

# Select best representative per entry type (highest det - fp)
entry_reps = {}
for t in ["A", "B", "C", "D"]:
    sub = edf[edf["type"] == t].copy()
    sub["score"] = sub["det"] - sub["fp"]
    best_idx = sub["score"].idxmax()
    best_p = sub.loc[best_idx, "p"]
    entry_reps[t] = best_p
    print(f"  Entry rep {t}: {best_p} (det={sub.loc[best_idx, 'det']:.3f}, "
          f"fp={sub.loc[best_idx, 'fp']:.3f})")

# Select best representative per exit type-group (highest cap - churn)
exit_reps = {}
for tg in ["X", "Y", "Z", "W", "V"]:
    sub = xdf[xdf["type_grp"] == tg].copy()
    if len(sub) == 0:
        continue
    sub["score"] = sub["cap"] - sub["churn"]
    best_idx = sub["score"].idxmax()
    best_type = sub.loc[best_idx, "type"]
    best_p = sub.loc[best_idx, "p"]
    exit_reps[tg] = (best_type, best_p)
    print(f"  Exit rep {tg}: {best_type}/{best_p} (cap={sub.loc[best_idx, 'cap']:.3f}, "
          f"churn={sub.loc[best_idx, 'churn']:.3f})")


def regen_entry(t, pn):
    """Regenerate entry signals from stored args."""
    a = eargs[(t, pn)]
    if t == "A": return gen_A(a["f"], a["sl"])
    elif t == "B": return gen_B(a["lb"])
    elif t == "C": return gen_C(a["n"], a["t"])
    elif t == "D": return gen_D(a["lb"], a["w"])


def check_exit(etype, ep, ebar, i, rpk):
    """Check exit condition at bar i."""
    if etype == "X":
        return C[i] < rpk * (1 - ep["trail"] / 100)
    elif etype == "Y":
        a = ATRc[ep["atr_p"]][i]
        return False if np.isnan(a) else C[i] < rpk - ep["mult"] * a
    elif etype == "ZA":
        ef, es = Ec[ep["f"]], Ec[ep["sl"]]
        return i >= 1 and ef[i] < es[i] and ef[i - 1] >= es[i - 1]
    elif etype == "ZB":
        rm = RMN[ep["lb"]][i]
        return False if np.isnan(rm) else C[i] < rm
    elif etype == "ZC":
        rv = ROCc[ep["n"]][i]
        return False if np.isnan(rv) else rv < ep["thr"] / 100
    elif etype == "ZD":
        sv = SMAc[ep["lb"]][i]
        av = ATRc[ep["lb"]][i]
        if np.isnan(sv) or np.isnan(av): return False
        return C[i] < sv - ep["w"] * av
    elif etype == "W":
        return (i - ebar) >= ep["hold"]
    elif etype == "V":
        if np.isnan(RV20[i]) or np.isnan(RV100[i]) or RV100[i] <= 0: return False
        if ep.get("mode") == "spike":
            return RV20[i] > ep["K"] * RV100[i]
        else:
            return RV20[i] < ep["K"] * RV100[i]
    return False


def run_strategy(entry_sigs, etype, ep, regime_filter=None):
    """Run full long-only strategy simulation.

    regime_filter: None (no filter), 1 (bull only), 0 (bear only)
    """
    trades = []
    in_trade = False
    ebar = 0; eprice = 0.0; rpk = 0.0

    for i in range(WU, NB):
        if not in_trade:
            if entry_sigs[i]:
                if regime_filter is not None and REG[i] != regime_filter:
                    continue
                in_trade = True
                ebar = i; eprice = C[i]; rpk = C[i]
        else:
            if C[i] > rpk:
                rpk = C[i]
            if check_exit(etype, ep, ebar, i, rpk):
                trades.append({
                    "eb": ebar, "xb": i,
                    "ret": C[i] / eprice - 1 - COST_F,
                    "hold": i - ebar,
                })
                in_trade = False

    return trades


def compute_metrics(trades):
    """Compute strategy metrics from trade list."""
    if len(trades) == 0:
        return {"sharpe": np.nan, "cagr": np.nan, "mdd": np.nan,
                "n": 0, "churn": 0, "exp": 0.0}

    # Build bar-level log returns
    bar_ret = np.zeros(NB)
    in_pos = np.zeros(NB, dtype=bool)
    for t in trades:
        for i in range(t["eb"] + 1, t["xb"] + 1):
            bar_ret[i] = lr[i]
            in_pos[i] = True
        bar_ret[t["xb"]] -= COST_F

    # Equity from warmup onwards
    eq = np.exp(np.cumsum(bar_ret[WU:]))
    r = bar_ret[WU:]
    yr = T_YR * (NB - WU) / NB

    # Sharpe
    sh = np.mean(r) / np.std(r) * np.sqrt(BPY) if np.std(r) > 0 else 0

    # CAGR
    cagr = (eq[-1] ** (1 / yr) - 1) * 100 if eq[-1] > 0 else -100

    # Max drawdown
    cm = np.maximum.accumulate(eq)
    dd = (cm - eq) / cm
    mdd = np.max(dd) * 100

    # Churn: re-entry within 10 bars
    churn = sum(1 for j in range(1, len(trades))
                if trades[j]["eb"] - trades[j - 1]["xb"] <= 10)

    # Exposure
    exp = np.mean(in_pos[WU:]) * 100

    return {
        "sharpe": round(sh, 4), "cagr": round(cagr, 2), "mdd": round(mdd, 2),
        "n": len(trades), "churn": churn, "exp": round(exp, 2),
    }


# ── 9. Pairing Analysis ──────────────────────────────────────
print("\n  9. Running entry × exit pairings...")
pair_rows = []
for et in ["A", "B", "C", "D"]:
    entry_sigs = regen_entry(et, entry_reps[et])
    for xtg in ["X", "Y", "Z", "W", "V"]:
        if xtg not in exit_reps:
            continue
        xtype, xpn = exit_reps[xtg]
        xparams = exit_params_map[(xtype, xpn)]
        trades = run_strategy(entry_sigs, xtype, xparams)
        m = compute_metrics(trades)
        pair_rows.append({"entry": et, "exit": xtg, **m})
        print(f"    {et}+{xtg}: Sharpe={m['sharpe']}, CAGR={m['cagr']}%, "
              f"MDD={m['mdd']}%, N={m['n']}, Churn={m['churn']}, Exp={m['exp']}%")

pair_df = pd.DataFrame(pair_rows)
pair_df.to_csv(TBL / "Tbl09_entry_exit_pairing.csv", index=False)
print("  Saved: Tbl09_entry_exit_pairing.csv")

# Sharpe heatmap pivot
if len(pair_df) > 0:
    sharpe_pivot = pair_df.pivot(index="entry", columns="exit", values="sharpe")
    print("\n  Sharpe heatmap (entry × exit):")
    print(sharpe_pivot.round(3).to_string())

    obs(f"Entry×Exit pairing: best Sharpe={pair_df['sharpe'].max():.3f} "
        f"({pair_df.loc[pair_df['sharpe'].idxmax(), 'entry']}+"
        f"{pair_df.loc[pair_df['sharpe'].idxmax(), 'exit']}), "
        f"worst={pair_df['sharpe'].min():.3f}. "
        f"Range={pair_df['sharpe'].max() - pair_df['sharpe'].min():.3f}.",
        "Tbl09, Fig13")

# ── Fig13: Entry × Exit Heatmap ──────────────────────────────
print("\n  Plotting Fig13: Entry × exit Sharpe heatmap...")
if len(pair_df) > 0:
    fig, ax = plt.subplots(figsize=(8, 6))
    sp = sharpe_pivot.values
    im = ax.imshow(sp, cmap="RdYlGn", aspect="auto",
                   vmin=np.nanmin(sp) - 0.1, vmax=np.nanmax(sp) + 0.1)
    ax.set_xticks(range(len(sharpe_pivot.columns)))
    ax.set_xticklabels([f"Exit {c}" for c in sharpe_pivot.columns], fontsize=11)
    ax.set_yticks(range(len(sharpe_pivot.index)))
    ax.set_yticklabels([f"Entry {r}" for r in sharpe_pivot.index], fontsize=11)
    # Annotate cells
    for i in range(sp.shape[0]):
        for j in range(sp.shape[1]):
            if not np.isnan(sp[i, j]):
                ax.text(j, i, f"{sp[i, j]:.3f}", ha="center", va="center",
                        fontsize=10, fontweight="bold",
                        color="white" if sp[i, j] < (np.nanmin(sp) + np.nanmax(sp)) / 2 else "black")
    plt.colorbar(im, ax=ax, label="Sharpe Ratio")
    ax.set_title("Fig13: Entry × Exit Pairing — Sharpe Ratio\n(50 bps RT cost)", fontsize=13)
    plt.tight_layout()
    plt.savefig(FIG / "Fig13_entry_exit_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  Saved: Fig13_entry_exit_heatmap.png")

# Additional heatmaps for CAGR and MDD
if len(pair_df) > 0:
    cagr_pivot = pair_df.pivot(index="entry", columns="exit", values="cagr")
    mdd_pivot = pair_df.pivot(index="entry", columns="exit", values="mdd")
    exp_pivot = pair_df.pivot(index="entry", columns="exit", values="exp")
    print("\n  CAGR heatmap:")
    print(cagr_pivot.round(1).to_string())
    print("\n  MDD heatmap:")
    print(mdd_pivot.round(1).to_string())
    print("\n  Exposure heatmap:")
    print(exp_pivot.round(1).to_string())


# ── 10. Regime Conditioning ───────────────────────────────────
print("\n  10. Regime conditioning (D1 SMA200)...")
regime_rows = []
for et in ["A", "B", "C", "D"]:
    entry_sigs = regen_entry(et, entry_reps[et])
    for xtg in ["X", "Y", "Z", "W", "V"]:
        if xtg not in exit_reps:
            continue
        xtype, xpn = exit_reps[xtg]
        xparams = exit_params_map[(xtype, xpn)]

        # No filter (baseline)
        trades_all = run_strategy(entry_sigs, xtype, xparams, regime_filter=None)
        m_all = compute_metrics(trades_all)

        # Bull only
        trades_bull = run_strategy(entry_sigs, xtype, xparams, regime_filter=1)
        m_bull = compute_metrics(trades_bull)

        regime_rows.append({
            "entry": et, "exit": xtg, "regime": "all",
            **{k: m_all[k] for k in ["sharpe", "cagr", "mdd", "n", "exp"]},
        })
        regime_rows.append({
            "entry": et, "exit": xtg, "regime": "bull",
            **{k: m_bull[k] for k in ["sharpe", "cagr", "mdd", "n", "exp"]},
        })

regime_df = pd.DataFrame(regime_rows)
regime_df.to_csv(TBL / "Tbl10_regime_conditioning.csv", index=False)
print("  Saved: Tbl10_regime_conditioning.csv")

# Compare regime effect
if len(regime_df) > 0:
    reg_all = regime_df[regime_df["regime"] == "all"].set_index(["entry", "exit"])
    reg_bull = regime_df[regime_df["regime"] == "bull"].set_index(["entry", "exit"])

    sharpe_diff = reg_bull["sharpe"] - reg_all["sharpe"]
    n_improved = (sharpe_diff > 0).sum()
    n_total = len(sharpe_diff)
    avg_diff = sharpe_diff.mean()

    print(f"\n  Regime filter effect: {n_improved}/{n_total} pairs improved Sharpe")
    print(f"  Average Sharpe change: {avg_diff:+.4f}")

    # Find best improvements
    if len(sharpe_diff) > 0:
        best_pair = sharpe_diff.idxmax()
        worst_pair = sharpe_diff.idxmin()
        print(f"  Best improvement: {best_pair} ({sharpe_diff[best_pair]:+.4f})")
        print(f"  Worst change: {worst_pair} ({sharpe_diff[worst_pair]:+.4f})")

    obs(f"Regime filter (bull-only): {n_improved}/{n_total} pairs show improved Sharpe. "
        f"Average ΔSharpe={avg_diff:+.4f}.",
        "Tbl10")


# ═══════════════════════════════════════════════════════════════
# HYPOTHESIS VERIFICATION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("HYPOTHESIS VERIFICATION")
print("=" * 70)

# H_prior_3: Entry lag
print("\n  H_prior_3 (entry lag):")
print("  Question: Any type with lag < 20 bars AND false positive < 50%?")
for t in ["A", "B", "C", "D"]:
    r = esumm.loc[t]
    flag = "✓" if r["lag"] < 20 and r["fp"] < 0.50 else "✗"
    print(f"    Type {t}: lag={r['lag']:.1f}, FP={r['fp']:.3f} → {flag}")
low_lag_types = [t for t in ["A", "B", "C", "D"]
                 if esumm.loc[t, "lag"] < 20 and esumm.loc[t, "fp"] < 0.50]
# Also check individual parameter combos
low_lag_combos = edf[(edf["lag"] < 20) & (edf["fp"] < 0.50)]
obs(f"H_prior_3 verification: {len(low_lag_types)} type averages achieve lag<20 & FP<50%. "
    f"{len(low_lag_combos)} individual combos achieve it.",
    "Tbl07")

# H_prior_4: Exit churn
print("\n  H_prior_4 (exit churn):")
print("  Question: Any exit type with churn < 10% AND capture > 60%?")
for tg in xsumm.index:
    r = xsumm.loc[tg]
    flag = "✓" if r["churn"] < 0.10 and r["cap"] > 0.60 else "✗"
    print(f"    Type {tg}: churn={r['churn']:.3f}, cap={r['cap']:.3f} → {flag}")
low_churn_types = [t for t in xsumm.index
                   if xsumm.loc[t, "churn"] < 0.10 and xsumm.loc[t, "cap"] > 0.60]
low_churn_combos = xdf[(xdf["churn"] < 0.10) & (xdf["cap"] > 0.60)]
obs(f"H_prior_4 verification: {len(low_churn_types)} type averages achieve churn<10% & cap>60%. "
    f"{len(low_churn_combos)} individual combos achieve it.",
    "Tbl08")

# H_prior_7: Low exposure
print("\n  H_prior_7 (low exposure):")
print("  Question: Any entry×exit pair with exposure > 60%?")
if len(pair_df) > 0:
    high_exp = pair_df[pair_df["exp"] > 60]
    print(f"  Pairs with exposure > 60%: {len(high_exp)}")
    if len(high_exp) > 0:
        print(high_exp[["entry", "exit", "exp"]].to_string(index=False))
    else:
        print("  None. Maximum exposure: "
              f"{pair_df['exp'].max():.1f}% ({pair_df.loc[pair_df['exp'].idxmax(), 'entry']}+"
              f"{pair_df.loc[pair_df['exp'].idxmax(), 'exit']})")
    obs(f"H_prior_7 verification: {len(high_exp)} pairs have exposure>60%. "
        f"Max exposure={pair_df['exp'].max():.1f}%.",
        "Tbl09")

# H_prior_10: Complexity ceiling
print("\n  H_prior_10 (complexity ceiling):")
print("  Question: gap between simplest and most complex signals?")
if len(pair_df) > 0:
    # Simplest: Type B entry (1 param) + Type X exit (1 param) = 2 DOF
    # Most complex: Type A entry (2 params) + Type Y exit (2 params) = 4 DOF
    # Or just look at the range across all pairs
    sh_range = pair_df["sharpe"].max() - pair_df["sharpe"].min()
    sh_std = pair_df["sharpe"].std()
    print(f"  Sharpe range across all pairs: {sh_range:.3f}")
    print(f"  Sharpe std across all pairs: {sh_std:.3f}")
    obs(f"H_prior_10 verification: Sharpe range across 4×5 entry×exit pairs = {sh_range:.3f}, "
        f"std = {sh_std:.3f}.",
        "Tbl09")


# ═══════════════════════════════════════════════════════════════
# SAVE OBSERVATIONS AND MANIFEST
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SAVING OUTPUTS")
print("=" * 70)

# Save observations
obs_df = pd.DataFrame(obs_log)
obs_df.to_csv(TBL / "phase3_observations.csv", index=False)
print(f"  Saved {len(obs_log)} observations to phase3_observations.csv")

# Update manifest
manifest = {
    "study": "X27",
    "phase": 3,
    "phase_name": "Signal Landscape EDA",
    "date": "2026-03-11",
    "artifacts": {
        "reports": ["01_data_audit.md", "02_price_behavior_eda.md", "03_signal_landscape_eda.md"],
        "tables": [
            "tables/Tbl01_h4_descriptive.csv", "tables/Tbl02_d1_descriptive.csv",
            "tables/Tbl03_data_quality.csv", "tables/Tbl04_ret_dist.csv",
            "tables/Tbl04_variance_ratio.csv", "tables/Tbl05_hurst.csv",
            "tables/Tbl06_trend_anatomy.csv", "tables/Tbl07_vol_regimes.csv",
            "tables/Tbl08_volume_corrs.csv", "tables/Tbl09_d1_returns.csv",
            "tables/Tbl10_cross_timeframe.csv", "tables/phase2_observations.csv",
            "tables/Tbl07_entry_signals.csv", "tables/Tbl07_entry_detail.csv",
            "tables/Tbl08_exit_signals.csv", "tables/Tbl08_exit_detail.csv",
            "tables/Tbl09_entry_exit_pairing.csv", "tables/Tbl10_regime_conditioning.csv",
            "tables/phase3_observations.csv",
        ],
        "code": ["code/phase1_audit.py", "code/phase2_eda.py", "code/phase3_signal_landscape.py"],
        "figures": [
            "figures/Fig01_return_distribution.png", "figures/Fig02_acf_returns.png",
            "figures/Fig03_acf_abs_returns.png", "figures/Fig04_pacf_returns.png",
            "figures/Fig05_rolling_hurst.png", "figures/Fig06_trend_profiles.png",
            "figures/Fig07_volatility_timeseries.png", "figures/Fig08_vol_return_scatter.png",
            "figures/Fig09_volume_distribution.png",
            "figures/Fig10_entry_efficiency_frontier.png",
            "figures/Fig11_exit_capture_vs_churn.png",
            "figures/Fig12_exit_capture_vs_drawdown.png",
            "figures/Fig13_entry_exit_heatmap.png",
        ],
    },
    "observations": f"Obs40-Obs{_oid[0] - 1:02d}",
    "hypothesis_verification": {
        "H_prior_3_entry_lag": "see Obs",
        "H_prior_4_exit_churn": "see Obs",
        "H_prior_7_low_exposure": "see Obs",
        "H_prior_10_complexity_ceiling": "see Obs",
    },
    "gate_status": "PASS_TO_NEXT_PHASE",
}
with open(OUT / "manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
print("  Saved: manifest.json")

print("\n" + "=" * 70)
print("PHASE 3 COMPLETE")
print("=" * 70)
print(f"  Observations: Obs40–Obs{_oid[0] - 1:02d} ({_oid[0] - 40} total)")
print(f"  Tables: Tbl07–Tbl10 (6 files)")
print(f"  Figures: Fig10–Fig13 (4 plots)")
print("  Gate status: PASS_TO_NEXT_PHASE (pending report review)")
